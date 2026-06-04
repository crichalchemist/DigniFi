"""
Tests for the PDFFormFiller service.

Covers:
  - fill() returns valid PDF bytes
  - fill() writes text field values into the returned PDF
  - fill() raises KeyError for unknown form_type
  - fill() silently ignores fields not present in the template
"""

from io import BytesIO

import pypdf
import pytest

from apps.forms.services.pdf_filler import PDFFormFiller


def test_fill_returns_valid_pdf_bytes(settings):
    """fill() returns bytes that start with the PDF magic number."""
    filler = PDFFormFiller()
    result = filler.fill(
        "form_121",
        {
            "Debtor1.First name": "Maria",
            "Debtor1.Last name": "Torres",
        },
    )
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_fill_writes_text_field(settings):
    """fill() writes a text field value into the returned PDF."""
    filler = PDFFormFiller()
    result = filler.fill("form_121", {"Debtor1.First name": "Maria"})
    reader = pypdf.PdfReader(BytesIO(result))
    fields = reader.get_fields() or {}
    field = fields.get("Debtor1.First name")
    assert field is not None
    assert field.get("/V") == "Maria"


def test_fill_unknown_form_type_raises():
    """fill() raises KeyError for an unrecognised form_type."""
    filler = PDFFormFiller()
    with pytest.raises(KeyError):
        filler.fill("form_does_not_exist", {})


def test_fill_ignores_unknown_fields(settings):
    """fill() silently ignores field names not present in the template."""
    filler = PDFFormFiller()
    result = filler.fill("form_121", {"nonexistent_field_xyz": "value"})
    assert result[:4] == b"%PDF"
