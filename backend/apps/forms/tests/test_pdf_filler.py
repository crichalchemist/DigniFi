"""
PDFFormFiller fills exactly the widget a key names, the way a viewer will draw it.

The old filler matched a key against a parent's partial /T, so "Name" filled
both Debtor 1 and Debtor 2 (DIG-63), and it never ticked a checkbox (DIG-68).
"""

import json
from io import BytesIO

import pypdf
import pytest

from apps.forms.services.pdf_filler import (
    InvalidFieldValue,
    PDFFormFiller,
    TemplateHasNoForm,
    UnknownField,
)
from apps.forms.tests.pdf_readback import read_widgets


def _values(pdf_bytes, full_name):
    return [w.value for w in read_widgets(pdf_bytes) if w.full_name == full_name]


def test_filled_form_is_a_pdf():
    result = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
    assert result[:4] == b"%PDF"


def test_debtor_1_name_never_lands_in_debtor_2_box():
    pdf = PDFFormFiller().fill("form_122a1", {"Debtor1.Name": "Maria Torres"})
    assert set(_values(pdf, "Debtor1.Name")) == {"Maria Torres"}
    assert _values(pdf, "Debtor2.Name") == [None]


def test_text_prints_from_a_stored_appearance():
    """pypdf 6.13.1 internals build and install the appearance; this pins them."""
    assert pypdf.__version__ == "6.13.1"
    pdf = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
    reader = pypdf.PdfReader(BytesIO(pdf))
    # A BooleanObject is always truthy; its .value is the flag.
    assert reader.trailer["/Root"]["/AcroForm"]["/NeedAppearances"].value is False
    widget = next(
        a.get_object()
        for a in reader.pages[0]["/Annots"]
        if a.get_object().get("/T") == "First name"
        and a.get_object()["/Parent"].get("/T") == "Debtor1"
    )
    assert b"Maria" in widget["/AP"]["/N"].get_data()


def test_checkbox_ticks_only_the_widgets_for_its_state():
    pdf = PDFFormFiller().fill("form_101", {"Check Box1": "/Chapter 7"})
    states = [w.state for w in read_widgets(pdf) if w.full_name == "Check Box1"]
    # Chapter 7 is printed on pages 1 and 3; the other six options stay off.
    assert states.count("/Chapter 7") == 2
    assert states.count("/Off") == len(states) - 2


def test_state_the_template_lacks_raises_instead_of_printing_nothing():
    with pytest.raises(InvalidFieldValue):
        PDFFormFiller().fill("form_101", {"Check Box1": "/Chapter 9"})


def test_district_must_be_one_of_the_templates_options():
    district = "Bankruptcy District Information"
    pdf = PDFFormFiller().fill("form_121", {district: "Northern District of Illinois"})
    assert _values(pdf, district) == ["Northern District of Illinois"]
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
