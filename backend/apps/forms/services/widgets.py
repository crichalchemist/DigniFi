"""
Template widgets: every widget of an AO template, addressed by page and tag.

The field index (apps.forms.field_index) gives each widget a tag that is unique
on its page and its rectangle, but its rows are not in the PDF's widget order.
template_widgets() therefore matches each /Widget annotation to its index row
by page and rectangle, and records what drawing the widget needs: whether it
prints, whether it is the second of a stacked pair, and its text layout as
pypdf's TextStreamAppearance.from_text_annotation reads it.

A key in the resolved values is a full name, which fills every drawn widget of
that name, or "<full name>@<page>:<tag>", which fills that one widget.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import pypdf
from django.conf import settings
from pypdf.generic import DictionaryObject

from apps.forms.field_index import IndexWidget, load_index

# The index rounds rects to 0.1 pt; Schedule D's stacked pairs sit 0.62 pt apart.
_TOLERANCE = 0.6
_PRINT = 1 << 2  # annotation flag bit 3
_MULTILINE = 1 << 12  # field flag bit 13
_COMB = 1 << 24  # field flag bit 25
_ADDRESS = re.compile(r"([0-9]+):(T[0-9]+)")  # "<page>:<tag>" after a key's "@"


class TemplateMismatch(Exception):
    """A template's widgets and its index rows don't match one-to-one."""

    def __init__(self, template_filename: str, page: int):
        self.template_filename = template_filename
        self.page = page
        super().__init__(
            f"{template_filename} page {page}: the widgets don't match the field index one-to-one"
        )


@dataclass(frozen=True)
class TemplateWidget:
    """One widget of a template: its index address, and what pypdf reads to draw it."""

    full_name: str
    page: int  # 1-based
    tag: str  # the index tag, unique on its page
    rect: tuple[float, float, float, float]  # the index rect, from the page's top left
    width: float  # of the PDF /Rect, as pypdf measures it
    height: float
    kind: str  # the index type: Text | CheckBox | RadioButton | ComboBox | Button
    printed: bool  # the annotation's Print flag
    stacked: bool  # the second widget of a stacked same-name pair
    states: tuple[str, ...]  # a box's on-states, as pypdf names them ("/Chapter 7")
    options: tuple[str, ...]  # a combo's /Opt
    font: str  # the /DA font name ("/Helv"); "" for a box
    size: float  # the /DA font size; 0 = auto
    # The template's alignment (0 left, 1 centre, 2 right): the widget's own /Q, else its
    # field's. pypdf reads only the field's, so the drawing hands this one over.
    align: int
    comb: bool
    multiline: bool
    max_len: int | None  # /MaxLen, on the widget or inherited from its parents
    margin: float  # pypdf's border margin

    @property
    def drawn(self) -> bool:
        """A value bound to this widget's name prints here."""
        return self.printed and not self.stacked

    @property
    def key(self) -> str:
        """This widget's own key in the resolved values."""
        return f"{self.full_name}@{self.page}:{self.tag}"


def qualified_name(field: DictionaryObject) -> str:
    """The field's full name: every /T up the /Parent chain, joined with dots."""
    parts = []
    node = field
    while node is not None:
        if "/T" in node:
            parts.append(str(node["/T"]))
        parent = node.get("/Parent")
        node = parent.get_object() if parent is not None else None
    return ".".join(reversed(parts))


def field_of(widget: DictionaryObject) -> DictionaryObject:
    """The field a widget belongs to: the widget itself when it carries /T, else its parent."""
    return widget if "/T" in widget else widget["/Parent"].get_object()


def parse_key(key: str) -> tuple[str, int | None, str | None]:
    """
    Split a values key: "name" → ("name", None, None); "name@2:T37" → ("name", 2, "T37").

    Raises:
        ValueError: the key has no name, or its address isn't "<page>:T<number>".
    """
    name, at, address = key.partition("@")
    match = _ADDRESS.fullmatch(address)
    if not name or (at and match is None):
        raise ValueError(f"{key!r} is neither a full name nor <full name>@<page>:<tag>")
    if not at:
        return key, None, None
    return name, int(match[1]), match[2]


def _top_left(annotation: DictionaryObject, page_top: float) -> tuple[float, ...]:
    """An annotation's /Rect in the index's coordinates: y measured down from the page's top."""
    x0, y0, x1, y1 = (float(v) for v in annotation["/Rect"])
    return (min(x0, x1), page_top - max(y0, y1), max(x0, x1), page_top - min(y0, y1))


def _same_rect(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return all(abs(p - q) <= _TOLERANCE for p, q in zip(a, b, strict=True))


def _area(rect: tuple[float, ...]) -> float:
    return max(rect[2] - rect[0], 0) * max(rect[3] - rect[1], 0)


def _stacked(rows: list[IndexWidget]) -> set[tuple[int, str]]:
    """
    (page, tag) of the second widget of each stacked pair: two widgets with one full
    name on one page whose overlap is more than half the smaller one's area.
    """
    by_name: dict[tuple[int, str], list[IndexWidget]] = {}
    for row in rows:
        by_name.setdefault((row.page, row.full_name), []).append(row)
    stacked = set()
    for group in by_name.values():
        for a, b in combinations(group, 2):
            overlap = (
                max(a.rect[0], b.rect[0]),
                max(a.rect[1], b.rect[1]),
                min(a.rect[2], b.rect[2]),
                min(a.rect[3], b.rect[3]),
            )
            if _area(overlap) > min(_area(a.rect), _area(b.rect)) / 2:
                second = max(a, b, key=lambda row: int(row.tag[1:]))
                stacked.add((second.page, second.tag))
    return stacked


def _template_widget(
    row: IndexWidget, annotation: DictionaryObject, acro_form: DictionaryObject, stacked: bool
) -> TemplateWidget:
    """A widget from its index row and its annotation, read where pypdf reads it but /Q."""
    field = field_of(annotation)
    font, size = "", 0.0
    if row.type in ("Text", "ComboBox"):
        appearance = annotation.get_inherited("/DA", acro_form.get("/DA"))
        da = str(appearance.get_object()) if appearance else "/Helv 0 Tf 0 g"
        parts = da.split()
        tf = parts.index("Tf")
        font, size = parts[tf - 2], float(parts[tf - 1])
    states: tuple[str, ...] = ()
    if row.type in ("CheckBox", "RadioButton"):
        states = tuple(str(state) for state in annotation["/AP"]["/N"] if state != "/Off")
    options: tuple[str, ...] = ()
    if row.type == "ComboBox":
        options = tuple(str(option) for option in field.get_inherited("/Opt", []))
    # pypdf reads /Ff, /Q and /BS from the field, never inherited or from a kid widget.
    # Three A/B widgets set /Q on the kid alone, so align takes the widget's own first.
    flags = int(field.get("/Ff", 0))
    border = field["/BS"] if "/BS" in field else DictionaryObject()
    factor = 2 if border.get("/S", "/S") in ("/B", "/I") else 1
    max_len = annotation.get_inherited("/MaxLen")
    x0, y0, x1, y1 = (float(v) for v in annotation["/Rect"])
    return TemplateWidget(
        full_name=row.full_name,
        page=row.page,
        tag=row.tag,
        rect=row.rect,
        width=abs(x1 - x0),
        height=abs(y1 - y0),
        kind=row.type,
        printed=bool(int(annotation.get("/F", 0)) & _PRINT),
        stacked=stacked,
        states=states,
        options=options,
        font=font,
        size=size,
        align=int(annotation.get("/Q", field.get("/Q", 0))),
        comb=bool(flags & _COMB),
        multiline=bool(flags & _MULTILINE),
        max_len=None if max_len is None else int(max_len),
        margin=max(float(border.get("/W", 1)) * factor, 1.0),
    )


@lru_cache(maxsize=32)
def template_widgets(template_filename: str) -> tuple[TemplateWidget, ...]:
    """
    Every widget of a template, ordered by page then tag number.

    Each /Widget annotation is matched to the index row on its page whose rect
    agrees with its /Rect within 0.6 pt, y measured down from the page's mediabox top.

    Raises:
        TemplateMismatch: on some page the widgets and the index rows don't
            match one-to-one.
    """
    rows_by_page: dict[int, list[IndexWidget]] = {}
    for rows in load_index(template_filename).values():
        for row in rows:
            rows_by_page.setdefault(row.page, []).append(row)
    stacked = _stacked([row for rows in rows_by_page.values() for row in rows])

    reader = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template_filename)
    root = reader.root_object
    acro_form = root["/AcroForm"] if "/AcroForm" in root else DictionaryObject()
    for number in rows_by_page:
        if number > len(reader.pages):
            raise TemplateMismatch(template_filename, number)

    widgets = []
    for number, page in enumerate(reader.pages, start=1):
        rows = rows_by_page.get(number, [])
        top = float(page.mediabox.top)
        matched = []
        for annot in page.get("/Annots") or []:
            annotation = annot.get_object()
            if annotation.get("/Subtype") != "/Widget":
                continue
            rect = _top_left(annotation, top)
            hits = [row for row in rows if _same_rect(rect, row.rect)]
            if len(hits) != 1:
                raise TemplateMismatch(template_filename, number)
            matched.append((hits[0], annotation))
        if len(matched) != len(rows) or {r.tag for r, _ in matched} != {r.tag for r in rows}:
            raise TemplateMismatch(template_filename, number)
        widgets += [
            _template_widget(row, annotation, acro_form, (row.page, row.tag) in stacked)
            for row, annotation in matched
        ]
    return tuple(sorted(widgets, key=lambda w: (w.page, int(w.tag[1:]))))


@lru_cache(maxsize=32)
def page_count(template_filename: str) -> int:
    """How many pages the template has."""
    return len(pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template_filename).pages)


def widget_for(
    template_filename: str, page: int, annotation: DictionaryObject, page_top: float
) -> TemplateWidget:
    """
    The template widget an annotation on `page` of a copy of the template is: the
    one whose rect matches the annotation's /Rect within 0.6 pt. `page_top` is the
    page's mediabox top (`float(page.mediabox.top)`).

    Raises:
        TemplateMismatch: no widget on that page matches, or more than one does.
    """
    rect = _top_left(annotation, page_top)
    hits = [
        w
        for w in template_widgets(template_filename)
        if w.page == page and _same_rect(rect, w.rect)
    ]
    if len(hits) != 1:
        raise TemplateMismatch(template_filename, page)
    return hits[0]
