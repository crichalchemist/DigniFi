"""
Read a drawn PDF back box by box, the way a person reads the printed page (spec §8).

Every value prints in Helvetica and every tick is the template's ZapfDingbats check
mark, while the templates print their own words in Arial, Wingdings and Times. A
character belongs to a widget when its centre lies inside the widget's rect from the
field index: two pairs of boxes overlap by about 2 pt, and a glyph merely touching a
rect would put a neighbour's tick in it. A copy of an extra page is read as the template
page it copies, found through the form's parts.
"""

from dataclasses import dataclass, replace
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pymupdf
import pypdf
from django.conf import settings
from pypdf.generic import ArrayObject, NameObject

from apps.forms.schema import load_schema
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
    of an extra page follows that page, its widgets read with their copy number. A text
    box that prints exactly what the blank form prints there reads as "": nothing the
    template prints passes for a value, so a value equal to that box's blank text reads
    blank too.

    Raises:
        ValueError: a page still has a widget. MuPDF reads an unbaked widget's appearance
            as text, and a viewer may rebuild it from the field's one value, so only a
            baked page shows what prints. Not an assertion, so a listed defect's xfail
            never takes a missing bake for that defect. Also when the PDF has a page
            count other than the template's and its copies', so no copy is read as
            another page.
    """
    template = load_schema(form_type).template_filename
    blank = _blank(template)
    document = pymupdf.open("pdf", pdf_bytes)
    unbaked = [page.number + 1 for page in document if page.first_widget]
    if unbaked:
        raise ValueError(f"the PDF still has widgets on pages {unbaked}: it was never baked")
    pages = _pages(template, parts or [])
    if len(document) != len(pages):
        raise ValueError(f"the PDF has {len(document)} pages, but its parts print {len(pages)}")
    return [
        replace(w, value="") if w.value and blank.get((w.page, w.tag)) == w.value else w
        for w in _read(template, document, pages)
    ]
