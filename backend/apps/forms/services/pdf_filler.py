"""
PDFFormFiller — fills an AO court PDF template with resolved field values.

Keys are index full names (apps.forms.field_index). A key fills only the
widgets whose qualified name equals it exactly. pypdf's
update_page_form_field_values also matches a parent's partial /T, which put
the filer's name and dates in Debtor 2 boxes (DIG-63), so the filler walks the
widgets itself.

check() plans what each widget a values dict fills will print, and at what size,
without drawing. It refuses a letter a box's font can't print and a value too long
for its box even in small print, naming the box and where the filer fixes the value.

Usage:
    pdf_bytes = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
    plan = PDFFormFiller().check("form_121", {"Debtor1.First name": "Maria"})
"""

import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pypdf
from django.conf import settings

# pypdf._font and pypdf.generic._appearance_stream are pypdf internals, pinned with
# pypdf==6.13.1; test_pdf_filler.py fails if they move.
from pypdf._font import Font
from pypdf.generic import DictionaryObject, NameObject, TextStringObject
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.forms.field_index import load_index
from apps.forms.schema import FormSchema, load_schema
from apps.forms.services.fill_resolver import fix_for
from apps.forms.services.text_fit import fit, font_for, printable
from apps.forms.services.widgets import (
    TemplateWidget,
    field_of,
    parse_key,
    qualified_name,
    template_widgets,
)

_BOXES = ("CheckBox", "RadioButton")
# pypdf draws each character of a comb box as its own string, which these break (R33).
_COMB_BREAKERS = "()\\"


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


class UnprintableLetter(Exception):
    """A value has a letter its box can't print: pypdf would draw "?" or another glyph."""

    def __init__(self, form_type: str, letter: str, label: str, fix: dict[str, str]):
        self.form_type = form_type
        self.letter = letter
        self.label = label
        self.step = fix.get("step")
        self.page = fix.get("page")
        super().__init__(
            f"The court form can't print the letter “{letter}” in “{label}”. "
            "Change it to a letter without the mark."
        )


class ValueTooLong(Exception):
    """A value doesn't fit its box even at the smallest size, 6 pt."""

    def __init__(self, form_type: str, label: str, fix: dict[str, str]):
        self.form_type = form_type
        self.label = label
        self.step = fix.get("step")
        self.page = fix.get("page")
        super().__init__(
            f"“{label}” is too long to fit on the court form, even in small print. Shorten it."
        )


@dataclass(frozen=True)
class Planned:
    """What one widget prints."""

    widget: TemplateWidget
    # Text as drawn (a multi-line box's lines joined by "\n"), a box's state or "/Off",
    # or a combo's option.
    value: str
    size: float | None  # None for a box


@dataclass(frozen=True)
class PlannedPart:
    """One part of a form's values, and what each widget it fills prints."""

    part: dict  # the part as given: {"kind": "form", "values": {...}}
    widgets: tuple[Planned, ...]


def _source(schema: FormSchema, key: str, widget: TemplateWidget) -> tuple[str, dict[str, str]]:
    """
    The box's label and where the filer fixes its value, from the binding that produced
    the key. A key no binding produced (a test's, the oracle's) gets the index row's
    label and no fix.
    """
    name, page, tag = parse_key(key)
    for field in schema.fields:
        if field.pdf_field == name and field.tag == tag and (tag is None or field.page == page):
            return field.label, fix_for(field)
    row = next(
        row
        for row in load_index(schema.template_filename)[name]
        if (row.page, row.tag) == (widget.page, widget.tag)
    )
    return row.label, {}


def _as_printed(text: str) -> str:
    """
    The text with every space (a tab, or any Unicode space separator) as a plain space,
    and format characters such as a soft hyphen left out: the template's font has no
    glyph for them, and draws U+00A0 as € (R34, R36).
    """
    return "".join(
        " " if letter == "\t" or unicodedata.category(letter) == "Zs" else letter
        for letter in text
        if unicodedata.category(letter) != "Cf"
    )


def _refused_letter(widget: TemplateWidget, font: Font, text: str) -> str | None:
    """
    The first character the box can't print: one its font can't encode, a control
    character, or in a comb box ( ) or \\. Line breaks aren't letters (G15).
    """
    for letter in "".join(text.splitlines()):
        if (
            not printable(font, letter)
            or unicodedata.category(letter) == "Cc"
            or (widget.comb and letter in _COMB_BREAKERS)
        ):
            return letter
    return None


class PDFFormFiller:
    """Fill AO court PDF templates with field values and return bytes."""

    def check(self, form_type: str, values: dict) -> tuple[PlannedPart, ...]:
        """
        Plan what each widget the values fill prints, without drawing.

        Args:
            form_type: a registered form type; its schema names the template.
            values: {key: value}. A key is a full name, which fills every drawn widget
                of that name, or "<full name>@<page>:<tag>", which fills that one
                widget and wins over the full name there. A value is text, a combo's
                option, or a box's export state such as "/Chapter 7".

        Returns:
            One part, holding every widget a key fills in page and tag order: a text
            or combo box with its text as drawn and its size, a box with its state or
            "/Off".

        Raises:
            UnknownField: a key names no drawn widget, or is neither form of key.
            InvalidFieldValue: a box state or combo option the template lacks.
            UnprintableLetter: a letter the box can't print.
            ValueTooLong: a value too long for its box even at 6 pt.
        """
        schema = load_schema(form_type)
        by_name: dict[str, list[TemplateWidget]] = {}
        for widget in template_widgets(schema.template_filename):
            if widget.drawn:
                by_name.setdefault(widget.full_name, []).append(widget)

        reached: dict[str, list[TemplateWidget]] = {}
        unknown = []
        for key in values:
            try:
                name, page, tag = parse_key(key)
            except ValueError:
                unknown.append(key)
                continue
            reached[key] = [
                widget
                for widget in by_name.get(name, ())
                if tag is None or (widget.page, widget.tag) == (page, tag)
            ]
            if not reached[key]:
                unknown.append(key)
        if unknown:
            raise UnknownField(form_type, sorted(unknown))

        for key, widgets in reached.items():
            if widgets[0].kind in _BOXES and not any(values[key] in w.states for w in widgets):
                raise InvalidFieldValue(form_type, widgets[0].full_name)

        # Full names first, so a widget's own key overrides its name's.
        filled_by: dict[TemplateWidget, str] = {}
        for key in sorted(reached, key=lambda key: "@" in key):
            for widget in reached[key]:
                filled_by[widget] = key

        planned = []
        for widget in sorted(filled_by, key=lambda w: (w.page, int(w.tag[1:]))):
            key = filled_by[widget]
            value = values[key]
            if widget.kind in _BOXES:
                planned.append(Planned(widget, value if value in widget.states else "/Off", None))
                continue
            if widget.kind == "ComboBox" and value not in widget.options:
                raise InvalidFieldValue(form_type, widget.full_name)
            font = font_for(schema.template_filename, widget.font)
            text = _as_printed(value)
            letter = _refused_letter(widget, font, text)
            if letter is not None:
                raise UnprintableLetter(form_type, letter, *_source(schema, key, widget))
            fitted = fit(widget, font, text)
            if fitted is None:
                raise ValueTooLong(form_type, *_source(schema, key, widget))
            planned.append(Planned(widget, *fitted))
        return (PlannedPart({"kind": "form", "values": values}, tuple(planned)),)

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
