"""
PDFFormFiller — draws resolved field values on an AO court PDF template.

Values are a parts document (registry.build_parts) or {key: value} alone (parts_of).
A key is a full name from the field index (apps.forms.field_index), or
"<full name>@<page>:<tag>" for one widget (widgets.parse_key). A full name fills only
the drawn widgets whose qualified name equals it exactly, never a widget the template
doesn't print or the second of a stacked pair; a drawn widget's own key fills that
widget, and a key that names no drawn widget is refused (UnknownField).
A copy part's keys fill only widgets on its page. pypdf's
update_page_form_field_values also matches a parent's partial /T, which put
the filer's name and dates in Debtor 2 boxes (DIG-63), so the filler walks the
widgets itself.

check() plans what each widget a values dict fills will print, and at what size,
without drawing. It refuses a letter a box's font can't print and a value too long
for its box even in small print, naming the box and where the filer fixes the value.

fill() draws that plan: pypdf builds each planned widget's own appearance, and
PyMuPDF bakes every widget into the page, so the PDF has no fillable field left.

Usage:
    pdf_bytes = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
    plan = PDFFormFiller().check("form_121", {"Debtor1.First name": "Maria"})
"""

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from io import BytesIO
from pathlib import Path

import pymupdf
import pypdf
from django.conf import settings

# pypdf.generic._appearance_stream is a pypdf internal, pinned with pypdf==6.13.1;
# test_pdf_filler.py fails if it moves.
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    TextStringObject,
)
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.forms.field_index import load_index
from apps.forms.schema import FormSchema, load_schema
from apps.forms.services.fill_resolver import fix_for
from apps.forms.services.text_fit import fit, font_for, printable
from apps.forms.services.widgets import (
    TemplateWidget,
    field_of,
    parse_key,
    template_widgets,
    widget_for,
)

_BOXES = ("CheckBox", "RadioButton")
# pypdf draws each character of a comb box as its own string, which these break (R33).
_COMB_BREAKERS = "()\\"
# The first text move in pypdf's appearance stream: "<x> <y> Td", before any string.
_FIRST_MOVE = re.compile(rb"^(\S+) (\S+) Td$", re.MULTILINE)


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


def parts_of(values: dict) -> list[dict]:
    """
    The parts a form's values hold: a parts document's own, {"version": 2, "parts": [...]}
    (3a2 spec §6), or any other dict, such as a form filed before 3a2, as one form part.
    """
    if values.get("version") == 2:
        return values["parts"]
    return [{"kind": "form", "values": values}]


def _source(schema: FormSchema, key: str, widget: TemplateWidget) -> tuple[str, dict[str, str]]:
    """
    The box's label and where the filer fixes its value, from the binding that produced
    the key. A key no binding produced (a test's, the oracle's) gets the index row's
    label and no fix; a binding with an empty label, the index row's label and its fix.
    """
    name, page, tag = parse_key(key)
    fix: dict[str, str] = {}
    for field in schema.fields:
        if field.pdf_field == name and field.tag == tag and (tag is None or field.page == page):
            if field.label:
                return field.label, fix_for(field)
            fix = fix_for(field)
            break
    row = next(
        row
        for row in load_index(schema.template_filename)[name]
        if (row.page, row.tag) == (widget.page, widget.tag)
    )
    return row.label, fix


def _as_printed(text: str) -> str:
    """
    The text composed (NFC), so a letter typed as a base letter and a combining mark, such
    as e and U+0301, is the one letter é the font prints; then with every space (a tab, or
    any Unicode space separator) as a plain space, and format characters such as a soft
    hyphen left out: the template's font has no glyph for them, and draws U+00A0 as €
    (R34, R36).
    """
    return "".join(
        " " if letter == "\t" or unicodedata.category(letter) == "Zs" else letter
        for letter in unicodedata.normalize("NFC", text)
        if unicodedata.category(letter) != "Cf"
    )


def _refused_letter(text: str, prints: Callable[[str], bool], comb: bool = False) -> str | None:
    """
    The first character a box can't print: one its font can't encode (`prints` says which
    it can), a control character, or in a comb box ( ) or \\. Line breaks aren't letters
    (G15). An attached sheet's cells are checked the same way (apps.forms.services.sheets).
    """
    for letter in "".join(text.splitlines()):
        if (
            not prints(letter)
            or unicodedata.category(letter) == "Cc"
            or (comb and letter in _COMB_BREAKERS)
        ):
            return letter
    return None


def _lower_first_line(appearance: TextStreamAppearance, by: float) -> None:
    """
    Move a multi-line box's first line down by `by` points. pypdf hangs line 1 from the
    font's bounding box top at the box's height plus its margin, so the box cuts off a
    capital's mark; 2 × margin lower, that top sits at the clip's top (R35). A stream
    with no line (an empty value) is left as it is.
    """
    data = appearance.get_data()
    move = _FIRST_MOVE.search(data)
    if move is None:
        return
    y = float(move[2]) - by
    appearance.set_data(data[: move.start(2)] + str(y).encode() + data[move.end(2) :])


def _draw(
    writer: pypdf.PdfWriter,
    page: pypdf.PageObject,
    acro_form: DictionaryObject,
    annotation: DictionaryObject,
    planned: Planned,
) -> None:
    """Give one widget its planned value: a box its state, a text or combo box its appearance."""
    widget = planned.widget
    field = field_of(annotation)
    if widget.kind in _BOXES:
        # The template's own check mark prints from /AS; /V keeps the state ticked.
        if planned.value != "/Off":
            field[NameObject("/V")] = NameObject(planned.value)
        annotation[NameObject("/AS")] = NameObject(planned.value)
        return
    if "/I" in field:  # a combo's stale selected index would override /V
        del field["/I"]
    # A widget's own /DR lacks the template's encoding: pypdf would encode with it and
    # print "?" for letters the AcroForm font draws (R32).
    if "/DR" in annotation:
        del annotation["/DR"]
    # pypdf reads a comb box's cell count from the widget alone (R4).
    if widget.comb and widget.max_len is not None and "/MaxLen" not in annotation:
        annotation[NameObject("/MaxLen")] = NumberObject(widget.max_len)
    # pypdf reads the value and the alignment from the field, which a widget may share
    # with its siblings, so both are this widget's own just before it is built (R8, R26).
    original = field.get("/V")
    field[NameObject("/V")] = TextStringObject(planned.value)
    field[NameObject("/Q")] = NumberObject(widget.align)
    # pypdf internals, pinned: build the text appearance at the planned size, and add it.
    appearance = TextStreamAppearance.from_text_annotation(
        writer, page, False, acro_form, field, annotation, user_font_size=planned.size
    )
    if widget.multiline:
        _lower_first_line(appearance, 2 * widget.margin)
    annotation[NameObject("/AP")] = DictionaryObject(
        {NameObject("/N"): writer._add_object(appearance)}
    )
    # The bake builds an appearance from the field's /V for a sibling that has none of
    # its own, so the field keeps the value it had: this one prints only here (R42).
    if original is None:
        del field["/V"]
    else:
        field[NameObject("/V")] = original


def _clone(form_type: str, template: str) -> pypdf.PdfWriter:
    """A fresh copy of the template to draw on."""
    writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
    if "/AcroForm" not in writer.root_object:
        raise TemplateHasNoForm(form_type)
    return writer


def _baked(
    writer: pypdf.PdfWriter, template: str, widgets: tuple[Planned, ...], only: int | None = None
) -> pymupdf.Document:
    """
    Draw the planned widgets on a clone of the template, and bake every page, or with
    `only`, that one page alone: the widgets that don't print are removed, each planned
    widget gets its own appearance, and PyMuPDF bakes every widget left into its page.
    """
    planned = {(p.widget.page, p.widget.tag): p for p in widgets}
    acro_form = writer.root_object["/AcroForm"].get_object()

    for number, page in enumerate(writer.pages, start=1):
        if "/Annots" not in page or (only is not None and number != only):
            continue
        kept = ArrayObject()
        for annot in page["/Annots"]:
            annotation = annot.get_object()
            if annotation.get("/Subtype") == "/Widget":
                widget = widget_for(template, number, annotation, float(page.mediabox.top))
                if not widget.drawn:
                    continue
                if (number, widget.tag) in planned:
                    _draw(writer, page, acro_form, annotation, planned[(number, widget.tag)])
            kept.append(annot)
        page[NameObject("/Annots")] = kept

    buffer = BytesIO()
    writer.write(buffer)
    document = pymupdf.open("pdf", buffer.getvalue())
    if only is not None:
        document.select([only - 1])
    document.bake(annots=False, widgets=True)
    return document


class PDFFormFiller:
    """Fill AO court PDF templates with field values and return bytes."""

    def check(self, form_type: str, values: dict) -> tuple[PlannedPart, ...]:
        """
        Plan what each widget the values fill prints, without drawing.

        Args:
            form_type: a registered form type; its schema names the template.
            values: a parts document, {"version": 2, "parts": [...]}, or {key: value}
                alone (parts_of). A form part's {key: value} fills the form's own pages;
                a copy part's fills only the widgets on its extra `page`. A key is a full
                name, which fills every drawn widget of that name, or
                "<full name>@<page>:<tag>", which fills that one widget and wins over
                the full name there. A value is text, a combo's option, or a box's
                export state such as "/Chapter 7". A sheet part's rows print on an
                attached sheet under the title and columns the part stores, never the
                schema's (R63; sheets.plan_sheet checks them).

        Returns:
            One planned part per part, each holding every widget a key fills in page
            and tag order: a text or combo box with its text as drawn and its size, a
            box with its state or "/Off". A sheet part fills no widget.

        Raises:
            UnknownField: a key names no drawn widget (on a copy's page, for a copy), or
                is neither form of key.
            InvalidFieldValue: a box state or combo option the template lacks.
            UnprintableLetter: a letter the box, or the sheet, can't print.
            ValueTooLong: a value too long for its box even at 6 pt, or for its sheet.
            ValueError: a part of a kind other than "form", "copy" and "sheet", or a sheet
                row's line that doesn't print whole on one line of the line column
                (sheets.plan_sheet).
        """
        from apps.forms.services.sheets import plan_sheet, sheet_spec  # here: they import this

        planned = []
        for part in parts_of(values):
            if part["kind"] == "form":
                widgets = self._plan(form_type, part["values"])
            elif part["kind"] == "copy":
                widgets = self._plan(form_type, part["values"], page=part["page"])
            elif part["kind"] == "sheet":
                plan_sheet(form_type, sheet_spec(part), part)
                widgets = ()
            else:
                raise ValueError(f"{form_type}: no part of kind {part['kind']!r}")
            planned.append(PlannedPart(part, widgets))
        return tuple(planned)

    def _plan(self, form_type: str, values: dict, page: int | None = None) -> tuple[Planned, ...]:
        """
        What each widget one part's {key: value} fills prints, as check() describes: on
        any page of the form, or with `page`, on that page alone.
        """
        schema = load_schema(form_type)
        by_name: dict[str, list[TemplateWidget]] = {}
        for widget in template_widgets(schema.template_filename):
            if widget.drawn and (page is None or widget.page == page):
                by_name.setdefault(widget.full_name, []).append(widget)

        reached: dict[str, list[TemplateWidget]] = {}
        unknown = []
        for key in values:
            try:
                name, at, tag = parse_key(key)
            except ValueError:
                unknown.append(key)
                continue
            reached[key] = [
                widget
                for widget in by_name.get(name, ())
                if tag is None or (widget.page, widget.tag) == (at, tag)
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
            letter = _refused_letter(text, partial(printable, font), widget.comb)
            if letter is not None:
                raise UnprintableLetter(form_type, letter, *_source(schema, key, widget))
            fitted = fit(widget, schema.template_filename, text)
            if fitted is None:
                raise ValueTooLong(form_type, *_source(schema, key, widget))
            planned.append(Planned(widget, *fitted))
        return tuple(planned)

    def fill(self, form_type: str, values: dict) -> bytes:
        """
        Draw the values on the form's template and return a PDF with no fillable field.

        check() plans every widget first. pypdf then builds each planned widget's own
        appearance at its planned size; the widgets the template doesn't print and the
        second widget of each stacked pair are removed; and PyMuPDF bakes every other
        widget into its page. An unfilled widget prints as the blank form shows it. Each
        copy of an extra page is drawn alone, on a clone of the template of its own, and
        goes in right after that page, or after the copy of it before (3a2 spec §5.2).
        Each attached sheet follows the form's pages and copies (3a2 spec §5.3).

        Args:
            form_type: a registered form type; its schema names the template.
            values: as check() takes them.

        Raises:
            TemplateHasNoForm: the template has no /AcroForm.
            UnknownField, InvalidFieldValue, UnprintableLetter, ValueTooLong, ValueError:
                as check().
        """
        from apps.forms.services.sheets import draw_sheet, sheet_spec  # here: they import this

        schema = load_schema(form_type)
        template = schema.template_filename
        writer = _clone(form_type, template)
        planned = self.check(form_type, values)
        form = tuple(p for part in planned if part.part["kind"] == "form" for p in part.widgets)
        document = _baked(writer, template, form)
        shown = list(range(1, len(document) + 1))  # the template page each page shows
        for part in planned:
            if part.part["kind"] != "copy":
                continue
            page = part.part["page"]
            copy = _baked(_clone(form_type, template), template, part.widgets, page)
            at = max(i for i, template_page in enumerate(shown) if template_page == page) + 1
            document.insert_pdf(copy, start_at=at)
            shown.insert(at, page)
        for part in planned:
            if part.part["kind"] == "sheet":
                sheet = draw_sheet(sheet_spec(part.part), part.part)
                document.insert_pdf(pymupdf.open("pdf", sheet))
        document.xref_set_key(document.pdf_catalog(), "AcroForm", "null")
        return document.tobytes()
