"""
PDFFormFiller draws exactly the widget a key names, and the page shows what it drew.

The old filler matched a key against a parent's partial /T, so "Name" filled
both Debtor 1 and Debtor 2 (DIG-63), and it never ticked a checkbox (DIG-68).
Since 3a2 each widget is drawn with its own value and baked into the page, so these
tests read the printed page (pdf_readback.read_drawn), not the fields' /V.
"""

import json
import logging
from io import BytesIO

import pymupdf
import pypdf
import pytest
from pypdf._font import Font
from pypdf.generic import NullObject
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import (
    InvalidFieldValue,
    PDFFormFiller,
    TemplateHasNoForm,
    UnknownField,
)
from apps.forms.services.text_fit import font_for
from apps.forms.services.widgets import parse_key, template_widgets
from apps.forms.tests.pdf_readback import read_drawn

EMAIL = "Debtor1.Email address_2"  # Form 101 page 9, 10 pt
OTHER_PROPERTY = "53 Examples Season tickets country club membership"  # A/B line 53, multi-line
# Helvetica's FontBBox top, per 1000 em: the highest mark a capital carries (Å).
_HELVETICA_TOP = 931


def _values(form_type, pdf_bytes, full_name):
    return [w.value for w in read_drawn(form_type, pdf_bytes) if w.full_name == full_name]


def _widget(form_type, full_name):
    template = load_schema(form_type).template_filename
    (widget,) = [w for w in template_widgets(template) if w.full_name == full_name and w.drawn]
    return widget


def _helvetica_in(pdf_bytes, widget):
    """Every Helvetica character drawn inside the widget's rect: (character, origin y, size)."""
    page = pymupdf.open("pdf", pdf_bytes)[widget.page - 1]
    x0, y0, x1, y1 = widget.rect
    return [
        (char["c"], char["origin"][1], span["size"])
        for block in page.get_text("rawdict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
        if span["font"] == "Helvetica"
        for char in span["chars"]
        if x0 <= (char["bbox"][0] + char["bbox"][2]) / 2 <= x1
        and y0 <= (char["bbox"][1] + char["bbox"][3]) / 2 <= y1
    ]


def test_filled_form_is_a_pdf():
    result = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
    assert result[:4] == b"%PDF"


def test_debtor_1_name_never_lands_in_debtor_2_box():
    pdf = PDFFormFiller().fill("form_122a1", {"Debtor1.Name": "Maria Torres"})
    assert set(_values("form_122a1", pdf, "Debtor1.Name")) == {"Maria Torres"}
    assert _values("form_122a1", pdf, "Debtor2.Name") == [""]


def test_the_drawn_form_has_no_fillable_field_left():
    """
    pypdf 6.13.1 builds each widget's appearance and adds it to the PDF (the internals
    TextStreamAppearance and PdfWriter._add_object), and PyMuPDF 1.27.2.3 bakes it into
    the page; this pins them. The value is page content now, so the PDF has no field a
    viewer could fill in.
    """
    assert pypdf.__version__ == "6.13.1"
    assert callable(TextStreamAppearance.from_text_annotation)
    assert callable(pypdf.PdfWriter._add_object)
    assert pymupdf.__version__ == "1.27.2.3"
    pdf = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
    reader = pypdf.PdfReader(BytesIO(pdf))
    # pypdf's own get_fields() can't read a null /AcroForm, so the root is read directly.
    assert isinstance(reader.trailer["/Root"]["/AcroForm"], NullObject)
    assert [
        a
        for page in reader.pages
        for a in page.get("/Annots") or []
        if a.get_object().get("/Subtype") == "/Widget"
    ] == []
    assert "Maria" in pymupdf.open("pdf", pdf)[0].get_text()


def test_text_is_measured_with_pinned_pypdf_font_internals():
    """check() measures and encodes with pypdf 6.13.1's Font, as the drawing does; this pins it."""
    assert pypdf.__version__ == "6.13.1"
    font = font_for("form_b121.pdf", "/Helv")  # Font.from_font_resource
    assert isinstance(font, Font)
    reverse_cmap, _ = font._get_typographic_maps()
    assert font.get_text_width(reverse_cmap["W"]) == 944  # Helvetica's W
    assert font.can_encode("é") and not font.can_encode("ą")
    bbox = font.font_descriptor.bbox
    assert (bbox[1], bbox[3]) == (-225, 931)  # its line spacing


def test_checkbox_ticks_only_the_widgets_for_its_state():
    pdf = PDFFormFiller().fill("form_101", {"Check Box1": "/Chapter 7"})
    states = [w.state for w in read_drawn("form_101", pdf) if w.full_name == "Check Box1"]
    # Chapter 7 is printed on pages 1 and 3; the other six options stay off.
    assert states.count("/Chapter 7") == 2
    assert states.count("/Off") == len(states) - 2


def test_state_the_template_lacks_raises_instead_of_printing_nothing():
    with pytest.raises(InvalidFieldValue):
        PDFFormFiller().fill("form_101", {"Check Box1": "/Chapter 9"})


def test_district_must_be_one_of_the_templates_options():
    district = "Bankruptcy District Information"
    pdf = PDFFormFiller().fill("form_121", {district: "Northern District of Illinois"})
    assert _values("form_121", pdf, district) == ["Northern District of Illinois"]
    with pytest.raises(InvalidFieldValue):
        PDFFormFiller().fill("form_121", {district: "District of Nowhere"})


def test_short_name_no_longer_fills_anything():
    with pytest.raises(UnknownField):
        PDFFormFiller().fill("form_122a1", {"Name": "Maria Torres"})


def test_unknown_form_type_raises():
    with pytest.raises(FileNotFoundError):
        PDFFormFiller().fill("form_does_not_exist", {})


def test_template_without_a_form_raises(tmp_path, settings):
    # Form 122B's template has no AcroForm (DIG-125).
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    schema = {
        "form_type": "form_no_acroform",
        "template_filename": "form_b122b.pdf",
        "template_version": "x",
        "fields": [],
    }
    (tmp_path / "form_no_acroform.json").write_text(json.dumps(schema))
    with pytest.raises(TemplateHasNoForm):
        PDFFormFiller().fill("form_no_acroform", {})


# ── What the drawing prints ───────────────────────────────────────────

# An invented name: Ł and ’ are outside Latin-1, yet in the template font's encoding.
_NAME = "Łukasz O’Brien"


def test_a_letter_outside_latin_1_prints_on_every_box():
    # A/B's page-1 header and these three bound boxes carry a /DR of their own whose font
    # lacks the template's encoding, so pypdf used to print "?" in them (R32).
    pdf = PDFFormFiller().fill("schedule_a_b", {"Debtor 1": _NAME})
    headers = {
        w.page: w.value for w in read_drawn("schedule_a_b", pdf) if w.full_name == "Debtor 1"
    }
    assert headers[1] == headers[2] == _NAME
    for form_type, full_name, value in [
        # 122A-2's two such boxes are amounts 38.5 pt wide: the whole name won't fit.
        ("form_122a2", "undefined_51", "Ł. O’Brien"),  # page 5
        ("schedule_c", "2.2", _NAME),  # page 1, multi-line
        ("schedule_d", "undefined_24", _NAME),  # page 2
    ]:
        pdf = PDFFormFiller().fill(form_type, {full_name: value})
        assert _values(form_type, pdf, full_name) == [value], form_type


@pytest.mark.parametrize(
    "form_type,full_name",
    [
        ("schedule_i", "Assistance 8f"),
        ("schedule_a_b", "24.1 Interest in an education IRA"),
    ],
)
def test_shared_name_boxes_print_their_own_values(form_type, full_name):
    template = load_schema(form_type).template_filename
    first, second = [w for w in template_widgets(template) if w.full_name == full_name]
    pdf = PDFFormFiller().fill(form_type, {first.key: "Nadrova 1", second.key: "Nadrova 2"})
    printed = {(w.page, w.tag): w.value for w in read_drawn(form_type, pdf)}
    assert printed[(first.page, first.tag)] == "Nadrova 1"
    assert printed[(second.page, second.tag)] == "Nadrova 2"


@pytest.mark.parametrize(
    "form_type,key,value",
    [
        ("form_107", "Debtor 1@1:T1", "Nadrova Okafor"),  # one header of 12, a page each
        ("schedule_i", "Time employed Debtor 1@1:T28", "3 years"),  # T29 beside it
        ("schedule_d", "account number@1:T32", "4417"),  # page 3's T33 shares the name
    ],
)
def test_a_tagged_value_prints_only_in_its_own_box(form_type, key, value):
    # Its siblings have no appearance of their own in the template, and one built at the
    # bake from the field's shared value would print this value in all of them (R42).
    name, page, tag = parse_key(key)
    pdf = PDFFormFiller().fill(form_type, {key: value})
    printed = {(w.page, w.tag): w.value for w in read_drawn(form_type, pdf) if w.full_name == name}
    assert printed.pop((page, tag)) == value
    assert printed and set(printed.values()) == {""}


@pytest.mark.parametrize(
    "form_type,full_name,ticked,neighbour",
    [
        # Each pair's rects overlap by about 2 pt: a tick in either box must not read as
        # a tick in the other.
        ("form_101", "Check Box1", (1, "T7"), (1, "T6")),  # Chapter 13, Chapter 12
        ("form_101", "Check Box1", (1, "T6"), (1, "T7")),
        ("schedule_d", "check 4", (2, "T28"), (2, "T27")),  # with another; Debtor 1 and 2
        ("schedule_d", "check 4", (2, "T27"), (2, "T28")),
    ],
)
def test_a_tick_reads_back_only_in_its_own_box(form_type, full_name, ticked, neighbour):
    template = load_schema(form_type).template_filename
    (widget,) = [w for w in template_widgets(template) if (w.page, w.tag) == ticked]
    pdf = PDFFormFiller().fill(form_type, {widget.key: widget.states[0]})
    printed = {(w.page, w.tag): w.state for w in read_drawn(form_type, pdf)}
    assert printed[ticked] == widget.states[0]
    assert printed[neighbour] == "/Off"


@pytest.mark.parametrize("form_type", get_all_form_types())
def test_nothing_the_blank_template_prints_reads_as_a_value(form_type):
    # A blank form still prints the template's own defaults: a district combo's
    # "__________ District of __________", a page number, A/B's "0%". None of them is a
    # value the filer gave, so none may pass for one.
    drawn = read_drawn(form_type, PDFFormFiller().fill(form_type, {}))
    assert [(w.full_name, w.value) for w in drawn if w.value] == []
    assert {w.state for w in drawn} <= {"", "/Off"}


def test_a_shrunk_value_prints_at_its_planned_size():
    # The bake keeps pypdf's appearance as built; an appearance rebuilt at the box's own
    # 10 pt would cut the address off (R39).
    email = "kestrel.wanamaker.okonkwo@example.org"
    box = _widget("form_101", EMAIL)
    ((planned,),) = [part.widgets for part in PDFFormFiller().check("form_101", {EMAIL: email})]
    assert planned.size < box.size
    drawn = _helvetica_in(PDFFormFiller().fill("form_101", {EMAIL: email}), box)
    assert "".join(c for c, _, _ in drawn) == email
    assert all(abs(size - planned.size) <= 0.05 for _, _, size in drawn)


def test_a_multi_line_boxs_first_line_keeps_its_capitals_marks():
    # pypdf hangs line 1 from the font's top at the box's height plus its margin, so the
    # box cut Å's ring off; the drawing lowers that line by 2 × margin (R35). MuPDF reads a
    # partly hidden glyph whole, so the line is judged by where it sits, not by its text.
    box = _widget("schedule_a_b", OTHER_PROPERTY)
    pdf = PDFFormFiller().fill("schedule_a_b", {OTHER_PROPERTY: "Åsa Éclair\nÇedric"})
    assert _values("schedule_a_b", pdf, OTHER_PROPERTY) == ["Åsa Éclair Çedric"]
    drawn = _helvetica_in(pdf, box)
    first_baseline = min(y for _, y, _ in drawn)
    size = next(s for _, y, s in drawn if y == first_baseline)
    top = first_baseline - _HELVETICA_TOP / 1000 * size
    assert top >= box.rect[1]
    # pypdf put that top a margin above the box; lowered by 2 × margin, it is a margin below.
    assert top == pytest.approx(box.rect[1] + box.margin, abs=0.06)


def test_an_empty_multi_line_box_prints_nothing():
    # pypdf's appearance for an empty value has no line, so there is none to lower.
    pdf = PDFFormFiller().fill("schedule_a_b", {OTHER_PROPERTY: ""})
    assert _values("schedule_a_b", pdf, OTHER_PROPERTY) == [""]


def test_drawing_never_logs_the_filers_text(caplog):
    # These boxes' own /DR made pypdf log a warning quoting the whole value (DIG-105).
    # check() now refuses whatever pypdf would still warn about, so nothing is logged.
    values = {
        "Debtor 1": _NAME,
        OTHER_PROPERTY: "Season tickets – “box 4”\n€120 • yearly",
    }
    with caplog.at_level(logging.DEBUG):
        PDFFormFiller().fill("schedule_a_b", values)
    pieces = [_NAME, "Season tickets – “box 4”", "€120 • yearly"]
    assert [
        r.getMessage() for r in caplog.records if any(p in r.getMessage() for p in pieces)
    ] == []
