"""
PDFFormFiller — fills an AO court PDF template with resolved field values.

Keys are index full names (apps.forms.field_index). A key fills only the
widgets whose qualified name equals it exactly. pypdf's
update_page_form_field_values also matches a parent's partial /T, which put
the filer's name and dates in Debtor 2 boxes (DIG-63), so the filler walks the
widgets itself.

Usage:
    pdf_bytes = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
"""

from io import BytesIO
from pathlib import Path

import pypdf
from django.conf import settings
from pypdf.generic import DictionaryObject, NameObject, TextStringObject

# pypdf internal, pinned with pypdf==6.13.1; test_pdf_filler.py fails if it moves.
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.forms.schema import load_schema
from apps.forms.services.widgets import field_of, qualified_name


class UnknownField(Exception):
    """A key names no widget in the template."""

    def __init__(self, form_type: str, names: list[str]):
        self.form_type = form_type
        self.names = names
        super().__init__(f"{form_type}: no widget named {names}")


class TemplateHasNoForm(Exception):
    """The template PDF has no /AcroForm, so nothing can be filled."""

    def __init__(self, form_type: str):
        self.form_type = form_type
        super().__init__(f"{form_type}: the template has no fillable form")


class InvalidFieldValue(Exception):
    """A button value is no widget's appearance state, or a combo value is not in /Opt."""

    def __init__(self, form_type: str, name: str):
        self.form_type = form_type
        self.name = name
        super().__init__(f"{form_type}: {name!r} can't take this value")


class PDFFormFiller:
    """Fill AO court PDF templates with field values and return bytes."""

    def fill(self, form_type: str, field_values: dict[str, str]) -> bytes:
        """
        Fill the form's template with field_values and return the PDF bytes.

        Args:
            form_type: a registered form type; its schema names the template.
            field_values: {full_name: value}. A value is text, an /Opt entry for
                a combo box, or an export state such as "/Chapter 7" for a button.

        Raises:
            UnknownField: a key names no widget.
            TemplateHasNoForm: the template has no /AcroForm.
            InvalidFieldValue: a button state or combo option the template lacks.
        """
        schema = load_schema(form_type)
        template_path = Path(settings.PDF_FORMS_DIRECTORY) / schema.template_filename
        writer = pypdf.PdfWriter(clone_from=str(template_path))
        if "/AcroForm" not in writer.root_object:
            raise TemplateHasNoForm(form_type)
        acro_form = writer.root_object["/AcroForm"].get_object()
        # Viewers draw the appearance streams written here, not their own.
        writer.set_need_appearances_writer(False)

        filled: set[str] = set()
        buttons: set[str] = set()
        ticked: set[str] = set()
        for page in writer.pages:
            for annot in page.get("/Annots") or []:
                widget = annot.get_object()
                if widget.get("/Subtype") != "/Widget":
                    continue
                field = field_of(widget)
                name = qualified_name(field)
                if name not in field_values:
                    continue
                filled.add(name)
                value = field_values[name]

                if field.get_inherited("/FT") == "/Btn":
                    buttons.add(name)
                    field[NameObject("/V")] = NameObject(value)
                    if value in widget["/AP"]["/N"]:
                        widget[NameObject("/AS")] = NameObject(value)
                        ticked.add(name)
                    else:
                        widget[NameObject("/AS")] = NameObject("/Off")
                    continue

                if field.get_inherited("/FT") == "/Ch":
                    options = [str(o) for o in field.get_inherited("/Opt", [])]
                    if value not in options:
                        raise InvalidFieldValue(form_type, name)
                    if "/I" in field:  # a stale selected index would override /V
                        del field["/I"]
                field[NameObject("/V")] = TextStringObject(value)
                # pypdf internal, pinned: builds the text appearance from /DA and /V.
                appearance = TextStreamAppearance.from_text_annotation(
                    writer, page, False, acro_form, field, widget
                )
                widget[NameObject("/AP")] = DictionaryObject(
                    {NameObject("/N"): writer._add_object(appearance)}
                )

        unknown = sorted(set(field_values) - filled)
        if unknown:
            raise UnknownField(form_type, unknown)
        for name in sorted(buttons - ticked):
            raise InvalidFieldValue(form_type, name)

        buf = BytesIO()
        writer.write(buf)
        return buf.getvalue()
