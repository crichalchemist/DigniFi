"""
Read a drawn PDF back box by box, the way a person reads the printed page (spec §8).

Every value prints in Helvetica and every tick is the template's ZapfDingbats check
mark, while the templates print their own words in Arial, Wingdings and Times. A
character belongs to a widget when its centre lies inside the widget's rect from the
field index: two pairs of boxes overlap by about 2 pt, and a glyph merely touching a
rect would put a neighbour's tick in it. A copy of an extra page is read as the template
page it copies, found through the form's parts. An attached sheet has no widget: its
pages are read line by line under its columns (read_sheets).
"""

from dataclasses import dataclass, replace
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pymupdf
import pypdf
from django.conf import settings
from pypdf.generic import ArrayObject, NameObject

from apps.forms.schema import SheetSpec, load_schema
from apps.forms.services.sheets import LINE_WIDTH, MARGIN
from apps.forms.services.widgets import TemplateWidget, page_count, template_widgets, widget_for

_BOXES = ("CheckBox", "RadioButton")
_TEXT_FONT = "Helvetica"
_TICK_FONT = "ZapfDingbats"


@dataclass(frozen=True)
class DrawnWidget:
    full_name: str
    page: int
    tag: str
    value: str  # the Helvetica text inside the widget's rect; "" when none
    state: str  # a box: its on-state when a check mark is inside, else "/Off"; "" for text
    copy: int | None = None  # on a copy of an extra page, its number; None on the form's own


@dataclass(frozen=True)
class _Character:
    text: str
    font: str
    centre: tuple[float, float]
    line: tuple[int, int]  # MuPDF's (block, line) on the page
    baseline: float
    box: tuple[float, float, float, float]


def _characters(page: pymupdf.Page) -> list[_Character]:
    """Every Helvetica or ZapfDingbats character on the page, with its position."""
    characters = []
    for b, block in enumerate(page.get_text("rawdict")["blocks"]):
        for n, line in enumerate(block.get("lines", [])):
            for span in line["spans"]:
                if span["font"] not in (_TEXT_FONT, _TICK_FONT):
                    continue
                for char in span["chars"]:
                    x0, y0, x1, y1 = char["bbox"]
                    characters.append(
                        _Character(
                            char["c"],
                            span["font"],
                            ((x0 + x1) / 2, (y0 + y1) / 2),
                            (b, n),
                            char["origin"][1],
                            (x0, y0, x1, y1),
                        )
                    )
    return characters


def _inside(character: _Character, rect: tuple[float, ...]) -> bool:
    x, y = character.centre
    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


def _text(widget: TemplateWidget, characters: list[_Character]) -> str:
    """The Helvetica characters inside the widget, line by line from the top."""
    lines: dict[tuple[int, int], list[_Character]] = {}
    for character in characters:
        if character.font == _TEXT_FONT and _inside(character, widget.rect):
            lines.setdefault(character.line, []).append(character)
    ordered = sorted(lines.values(), key=lambda line: (round(line[0].baseline, 1), line[0].centre))
    text = " ".join(joined for line in ordered if (joined := "".join(c.text for c in line).strip()))
    # A comb box draws each character in its own cell; MuPDF reads the gaps as spaces.
    return "".join(text.split()) if widget.comb else text


def _read(
    template: str, document: pymupdf.Document, pages: list[tuple[int, int | None]]
) -> list[DrawnWidget]:
    """Each page's widgets, read as those of the template page and copy `pages` names for it."""
    widgets: dict[int, list[TemplateWidget]] = {}
    for widget in template_widgets(template):
        widgets.setdefault(widget.page, []).append(widget)
    drawn = []
    for output, (page, copy) in zip(document, pages, strict=True):
        on_page = _characters(output)
        for widget in widgets.get(page, []):
            if widget.kind in _BOXES:
                ticked = any(c.font == _TICK_FONT and _inside(c, widget.rect) for c in on_page)
                value, state = "", widget.states[0] if ticked else "/Off"
            else:
                value, state = _text(widget, on_page), ""
            drawn.append(DrawnWidget(widget.full_name, widget.page, widget.tag, value, state, copy))
    return drawn


def _pages(template: str, parts: list[dict]) -> list[tuple[int, int | None]]:
    """
    The template page, and the copy number, each page of the drawn form shows: the
    template's pages in order, and each copy right after its extra page or the copy of
    it before.
    """
    pages: list[tuple[int, int | None]] = [(p, None) for p in range(1, page_count(template) + 1)]
    for part in parts:
        if part["kind"] == "copy":
            at = max(i for i, (page, _) in enumerate(pages) if page == part["page"]) + 1
            pages.insert(at, (part["page"], part["number"]))
    return pages


@lru_cache(maxsize=32)
def _blank(template: str) -> dict[tuple[int, str], str]:
    """
    (page, tag) → the text the blank template prints in a box: a district combo's
    "__________ District of __________", a default page number or "0%". Built here,
    apart from the engine, the way it prints a box it draws nothing in: the template
    less the widgets that never print, baked. (PyMuPDF baking the template file as it
    stands prints each district placeholder twice.)
    """
    writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
    for number, page in enumerate(writer.pages, start=1):
        if "/Annots" not in page:
            continue
        page[NameObject("/Annots")] = ArrayObject(
            annot
            for annot in page["/Annots"]
            if annot.get_object().get("/Subtype") != "/Widget"
            or widget_for(template, number, annot.get_object(), float(page.mediabox.top)).drawn
        )
    buffer = BytesIO()
    writer.write(buffer)
    document = pymupdf.open("pdf", buffer.getvalue())
    document.bake(annots=False, widgets=True)
    pages = [(page, None) for page in range(1, len(document) + 1)]
    return {(w.page, w.tag): w.value for w in _read(template, document, pages) if w.value}


def read_drawn(
    form_type: str, pdf_bytes: bytes, parts: list[dict] | None = None
) -> list[DrawnWidget]:
    """
    What the drawn form prints in each widget of its template, one entry per index row
    in page and tag order. With `parts`, the parts it was drawn from (spec §6), each copy
    of an extra page follows that page, its widgets read with their copy number, and the
    pages of its attached sheets, which come last, are left to read_sheets(). A text
    box that prints exactly what the blank form prints there reads as "": nothing the
    template prints passes for a value, so a value equal to that box's blank text reads
    blank too.

    Raises:
        ValueError: a page still has a widget. MuPDF reads an unbaked widget's appearance
            as text, and a viewer may rebuild it from the field's one value, so only a
            baked page shows what prints. Not an assertion, so a listed defect's xfail
            never takes a missing bake for that defect. Also when the PDF's pages aren't
            the template's and its copies', then at least one attached sheet page per
            sheet part and nothing else, so no copy or sheet is read as another page.
    """
    template = load_schema(form_type).template_filename
    blank = _blank(template)
    document = pymupdf.open("pdf", pdf_bytes)
    unbaked = [page.number + 1 for page in document if page.first_widget]
    if unbaked:
        raise ValueError(f"the PDF still has widgets on pages {unbaked}: it was never baked")
    pages = _pages(template, parts or [])
    # An attached sheet's pages come after the form's pages and copies, each headed by its
    # title "… (attached sheet)" (spec §5.3); they hold no widget, so they aren't read here.
    sheets = sum(part["kind"] == "sheet" for part in parts or [])
    form, after = list(document)[: len(pages)], list(document)[len(pages) :]
    if (
        len(form) != len(pages)
        or any(_is_sheet(page) for page in form)
        or not all(_is_sheet(page) for page in after)
        or len(after) < sheets
        or (after and not sheets)
    ):
        raise ValueError(
            f"the PDF has {len(document)} pages, but its parts print {len(pages)}"
            + (f" and {sheets} attached sheet(s)" if sheets else "")
        )
    return [
        replace(w, value="") if w.value and blank.get((w.page, w.tag)) == w.value else w
        for w in _read(template, form, pages)
    ]


_SHEET_TITLE = "(attached sheet)"


def _is_sheet(page: pymupdf.Page) -> bool:
    """Whether the page is an attached sheet's: its header's title says so."""
    return _SHEET_TITLE in " ".join(page.get_text().split())


@dataclass(frozen=True)
class SheetPage:
    """One page of an attached sheet, read the way a person reads it."""

    header: tuple[str, ...]  # its lines down to "Case number (if known)", top to bottom
    labels: tuple[str, ...]  # each column's label, the line column's ("") first
    rows: tuple[tuple[str, ...], ...]  # each row: its line, then its cells, column by column
    lines: tuple[tuple[tuple[str, ...], ...], ...]  # each row's cells, each as its lines
    ink: tuple[float, float, float, float]  # the box every character of the page lies in
    # Below the header, each character not inside its column. A space is left out: it
    # prints nothing, and MuPDF reads the gap between two cells' text as one.
    crossing: tuple[str, ...]
    overlapping: tuple[str, ...]  # each line whose characters reach into the next line's


def read_sheets(pdf_bytes: bytes, spec: SheetSpec) -> list[SheetPage]:
    """
    Each attached sheet page of a drawn form, read under the columns of `spec`: the line
    column's 36 pt from the left margin (0.75 in), then the group's columns, each as wide
    as declared. A character belongs to the column its centre lies in, and to the line of
    its baseline. A row starts at each line that prints a line number, and takes every line
    down to the next; a cell's lines, like a label's, are joined with spaces in `rows` and
    kept apart in `lines`. A character's box is MuPDF's, from its font's ascender to its
    descender.
    """
    edges = [MARGIN, MARGIN + LINE_WIDTH]
    for column in spec.columns:
        edges.append(edges[-1] + column.width)
    pages = []
    for page in pymupdf.open("pdf", pdf_bytes):
        if not _is_sheet(page):
            continue
        characters = [c for c in _characters(page) if c.font == _TEXT_FONT]
        baselines: dict[float, list[_Character]] = {}
        for character in characters:
            baselines.setdefault(round(character.baseline, 1), []).append(character)
        texts, lines, columns = [], [], []  # each line's text, its cells, its characters' columns
        for baseline in sorted(baselines):
            ordered = sorted(baselines[baseline], key=lambda c: c.centre[0])
            texts.append("".join(c.text for c in ordered).strip())
            cells = [""] * (len(edges) - 1)
            for character in ordered:
                column = max(
                    (i for i, edge in enumerate(edges[:-1]) if edge <= character.centre[0]),
                    default=0,
                )
                cells[column] += character.text
                columns.append((character, column))
            lines.append([cell.strip() for cell in cells])
        case_number = next(i for i, text in enumerate(texts) if text.startswith("Case number"))
        header = texts[: case_number + 1]
        below = sorted(baselines)[case_number + 1 :]
        crossing = tuple(
            c.text
            for c, i in columns
            if round(c.baseline, 1) in below
            and not c.text.isspace()
            and not (edges[i] - 0.01 <= c.box[0] and c.box[2] <= edges[i + 1] + 0.01)
        )
        extents = [
            (texts[n], min(c.box[1] for c in baselines[b]), max(c.box[3] for c in baselines[b]))
            for n, b in enumerate(sorted(baselines))
        ]
        overlapping = tuple(
            text
            for (text, _, bottom), (_, top, _) in zip(extents, extents[1:], strict=False)
            if bottom > top + 0.01
        )
        body = lines[case_number + 1 :]
        starts = [i for i, line in enumerate(body) if line[0]] + [len(body)]
        labels = _joined(body[: starts[0]], len(edges) - 1)
        spans = list(zip(starts, starts[1:], strict=False))
        rows = [_joined(body[a:b], len(edges) - 1) for a, b in spans]
        lines_of = [
            tuple(tuple(line[i] for line in body[a:b] if line[i]) for i in range(len(edges) - 1))
            for a, b in spans
        ]
        boxes = [c.box for c in characters]
        ink = (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )
        pages.append(
            SheetPage(
                tuple(header), labels, tuple(rows), tuple(lines_of), ink, crossing, overlapping
            )
        )
    return pages


def _joined(lines: list[list[str]], columns: int) -> tuple[str, ...]:
    """Each column's text over several lines, its non-empty lines joined with spaces."""
    return tuple(" ".join(line[i] for line in lines if line[i]) for i in range(columns))
