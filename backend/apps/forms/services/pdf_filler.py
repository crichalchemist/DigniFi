"""
PDFFormFiller — fills AO court PDF templates with field values.

Uses pypdf to load a fillable PDF template, write values into form fields,
and return the filled PDF as bytes. Unknown field names are silently ignored.

Usage:
    filler = PDFFormFiller()
    pdf_bytes = filler.fill("form_121", {"Debtor1.First name": "Maria"})
"""

from io import BytesIO
from pathlib import Path

import pypdf
from django.conf import settings

# Maps form_type key → filename under PDF_FORMS_DIRECTORY
FORM_TEMPLATES: dict[str, str] = {
    "form_101": "form_b_101_0624_fillable_clean.pdf",
    "form_103b": "form_b103b.pdf",
    "form_106dec": "form_b106dec.pdf",
    "form_106sum": "form_b106sum.pdf",
    "form_107": "b_107_0425-form.pdf",
    "form_121": "form_b121.pdf",
    "form_122a1": "b_122a-1.pdf",
    "form_122a2": "b_122a-2_0425-form.pdf",
    "form_122a1_supp": "form_b122a-1supp.pdf",
    "form_122b": "form_b122b.pdf",
    "schedule_a_b": "form_b106ab.pdf",
    "schedule_c": "b_106c_0425-form.pdf",
    "schedule_d": "form_b106d.pdf",
    "schedule_e_f": "form_b106ef.pdf",
    "schedule_g": "form_b106g.pdf",
    "schedule_h": "form_b106h.pdf",
    "schedule_i": "form_b106i.pdf",
    "schedule_j": "form_b106j.pdf",
}


class PDFFormFiller:
    """Fill AO court PDF templates with field values and return bytes."""

    def fill(self, form_type: str, field_map: dict[str, str]) -> bytes:
        """
        Load template for form_type, write field_map into every page, return PDF bytes.

        Args:
            form_type: One of the keys in FORM_TEMPLATES (e.g. "form_101").
            field_map: {pdf_field_name: value_string}. Unknown field names are
                       silently ignored. Checkbox fields expect "/Yes" or "/Off".

        Raises:
            KeyError: form_type not in FORM_TEMPLATES.
            FileNotFoundError: template PDF missing from PDF_FORMS_DIRECTORY.
        """
        filename = FORM_TEMPLATES[form_type]  # KeyError if unknown
        template_path = Path(settings.PDF_FORMS_DIRECTORY) / filename

        reader = pypdf.PdfReader(str(template_path))
        writer = pypdf.PdfWriter()
        writer.append(reader)

        # update_page_form_field_values fills matching fields on one page at a time.
        # auto_regenerate=False keeps visual appearance stable across viewers.
        for page in writer.pages:
            writer.update_page_form_field_values(page, field_map, auto_regenerate=False)

        buf = BytesIO()
        writer.write(buf)
        return buf.getvalue()
