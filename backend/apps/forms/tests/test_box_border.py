"""
A filled box keeps the border its template draws.

pypdf's appearance for a filled text box has no border, so the court's black box around
a List of Creditors entry vanished once the entry was filled. A viewer strokes /MK /BC
over the text. Text read-back can't see a border, so these tests judge pixels.
"""

from pathlib import Path

import pymupdf
from django.conf import settings

from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller

ENTRY = "Demo Card Services\n1 Demo Way\nChicago, IL 60601"


def _template(form_type: str) -> pymupdf.Document:
    return pymupdf.open(
        Path(settings.PDF_FORMS_DIRECTORY) / load_schema(form_type).template_filename
    )


def _widget(form_type: str, name: str) -> pymupdf.Widget:
    for page in _template(form_type):
        for widget in page.widgets() or []:
            if widget.field_name == name:
                return widget
    raise AssertionError(name)


def _page(pdf: bytes) -> pymupdf.Page:
    return pymupdf.open("pdf", pdf)[0]


def _edges(rect: pymupdf.Rect) -> list[pymupdf.Rect]:
    """A 1 pt strip inside each of the box's four sides (the border is 1 pt wide)."""
    return [
        pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + 1),
        pymupdf.Rect(rect.x0, rect.y1 - 1, rect.x1, rect.y1),
        pymupdf.Rect(rect.x0, rect.y0, rect.x0 + 1, rect.y1),
        pymupdf.Rect(rect.x1 - 1, rect.y0, rect.x1, rect.y1),
    ]


def _ink(page: pymupdf.Page, clip: pymupdf.Rect) -> int:
    pixels = page.get_pixmap(dpi=144, clip=clip, colorspace=pymupdf.csGRAY)
    return sum(1 for value in pixels.samples if value < 200)


def _fill(form_type: str, values: dict) -> bytes:
    return PDFFormFiller().fill(form_type, values)


def test_a_filled_creditor_box_keeps_its_border():
    # R10: on paper every cell keeps the court's black box, filled or empty.
    rect = _widget("list_of_creditors", "creditor1.0.0").rect
    filled = _page(_fill("list_of_creditors", {"creditor1.0.0": ENTRY}))
    blank = _page(_fill("list_of_creditors", {}))
    for edge in _edges(rect):
        assert _ink(filled, edge) == _ink(blank, edge) > 0


def test_a_box_with_no_border_colour_gains_none():
    template = _template("form_101")
    page = template[0]
    widget = next(
        widget
        for widget in page.widgets()
        if widget.field_type_string == "Text"
        and "/BC" not in template.xref_get_key(widget.xref, "MK")[1]
        and _ink(page, widget.rect) == 0
    )
    filled = _page(_fill("form_101", {widget.field_name: "Q"}))
    blank = _page(_fill("form_101", {}))
    for edge in _edges(widget.rect):
        assert _ink(filled, edge) == _ink(blank, edge)


def _bands(rect: pymupdf.Rect) -> list[pymupdf.Rect]:
    """A strip 1.1 to 2.6 pt inside the right and the bottom edge, past the border's width."""
    return [
        pymupdf.Rect(rect.x1 - 2.6, rect.y0, rect.x1 - 1.1, rect.y1),
        pymupdf.Rect(rect.x0, rect.y1 - 2.6, rect.x1, rect.y1 - 1.1),
    ]


def _fine_ink(page: pymupdf.Page, clip: pymupdf.Rect) -> int:
    pixels = page.get_pixmap(dpi=288, clip=clip, colorspace=pymupdf.csGRAY)
    return sum(1 for value in pixels.samples if value < 200)


def test_a_filled_creditor_box_draws_no_second_rule_inside_its_border():
    # pypdf's stream ends with an open clip path (`re W`, no `n`); a stroke appended after
    # it also strokes that clip rectangle, a second rule inside the court's box.
    rect = _widget("list_of_creditors", "creditor1.0.0").rect
    filled = _page(_fill("list_of_creditors", {"creditor1.0.0": "Demo Co\n1 Way\nChicago"}))
    blank = _page(_fill("list_of_creditors", {}))
    for band in _bands(rect):
        assert _fine_ink(filled, band) == _fine_ink(blank, band)
