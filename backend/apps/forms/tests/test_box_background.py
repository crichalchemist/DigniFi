"""
A box the template gives a background hides what the page prints under it.

Every district box but Form 101's sits on the page's own "__________ District of
__________", and 15 of Schedule C's boxes on ruled lines. A viewer paints the box's
/MK /BG over them. Text read-back can't see a line showing through, so these tests judge
pixels.
"""

from pathlib import Path

import pymupdf
import pytest
from django.conf import settings

from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller

DISTRICT = "Bankruptcy District Information"
# Short, so most of the box stays empty and what shows through can't hide behind the name.
SHORT_DISTRICT = "District of Guam"
FORMS_WITH_WORDS_UNDER_THE_DISTRICT = [
    "form_103b",
    "form_106dec",
    "form_106sum",
    "form_107",
    "form_121",
    "form_122a1",
    "form_122a1_supp",
    "form_122a2",
    "schedule_a_b",
    "schedule_c",
    "schedule_d",
    "schedule_e_f",
    "schedule_g",
    "schedule_h",
    "schedule_i",
    "schedule_j",
]


def _template(form_type: str) -> pymupdf.Document:
    return pymupdf.open(
        Path(settings.PDF_FORMS_DIRECTORY) / load_schema(form_type).template_filename
    )


def _rects(form_type: str, name: str) -> list[tuple[int, pymupdf.Rect]]:
    return [
        (page.number, widget.rect)
        for page in _template(form_type)
        for widget in page.widgets() or []
        if widget.field_name == name
    ]


def _ink_past(document, number: int, rect: pymupdf.Rect, text: str) -> int:
    """Dark pixels in the box to the right of where its own text ends."""
    page = document[number]
    drawn = page.search_for(text, clip=rect)
    assert drawn, f"{text!r} did not print in the box"
    clip = pymupdf.Rect(max(hit.x1 for hit in drawn) + 2, rect.y0 + 1, rect.x1 - 1, rect.y1 - 1)
    pixels = page.get_pixmap(dpi=144, clip=clip, colorspace=pymupdf.csGRAY)
    return sum(1 for value in pixels.samples if value < 200)


@pytest.mark.parametrize("form_type", FORMS_WITH_WORDS_UNDER_THE_DISTRICT)
def test_the_court_name_prints_clean_over_the_forms_own_district_line(form_type):
    document = pymupdf.open("pdf", PDFFormFiller().fill(form_type, {DISTRICT: SHORT_DISTRICT}))
    rects = _rects(form_type, DISTRICT)
    assert rects
    for number, rect in rects:
        assert _ink_past(document, number, rect, "Guam") == 0, f"page {number + 1}"


def test_a_schedule_c_box_prints_clean_over_the_forms_ruled_lines():
    document = pymupdf.open("pdf", PDFFormFiller().fill("schedule_c", {"2.1": "Car"}))
    ((number, rect),) = _rects("schedule_c", "2.1")
    assert _ink_past(document, number, rect, "Car") == 0


def test_a_box_with_no_background_leaves_the_forms_own_line_showing():
    """Most boxes have none, and the line a filer's answer sits on stays on the page."""
    template = _template("schedule_a_b")
    page = template[0]
    widget = next(
        widget
        for widget in page.widgets()
        if widget.field_type_string == "Text"
        and "/BG" not in template.xref_get_key(widget.xref, "MK")[1]
        and "____" in page.get_text("text", clip=widget.rect)
    )
    document = pymupdf.open("pdf", PDFFormFiller().fill("schedule_a_b", {widget.field_name: "Q"}))
    assert _ink_past(document, page.number, widget.rect, "Q") > 0
