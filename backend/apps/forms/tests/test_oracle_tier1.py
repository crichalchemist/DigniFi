"""
Oracle tier 1: every binding lands in exactly the widget it names (spec §6).

Each text and combo binding gets a unique marker, the real filler fills the
real template, and every widget is read back. A checkbox state is set and read
from /AS, which is what a viewer draws; /V alone proves nothing (DIG-68).
No database is needed.
"""

from functools import cache
from pathlib import Path

import pypdf
import pytest
from django.conf import settings

from apps.forms.field_index import export_state, load_index
from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.oracle import case_param
from apps.forms.tests.pdf_readback import read_widgets

TIER = "1"


def _fields(form_type, types):
    return [f for f in load_schema(form_type).fields if f.type in types]


def _first_option(form_type, pdf_field):
    template = Path(settings.PDF_FORMS_DIRECTORY) / load_schema(form_type).template_filename
    return str(pypdf.PdfReader(template).get_fields()[pdf_field]["/Opt"][0])


@cache
def _text_landing(form_type):
    """pdf_field → the full names its marker was read back from."""
    markers = {
        f.pdf_field: (_first_option(form_type, f.pdf_field) if f.type == "choice" else f"Q{i:03d}")
        for i, f in enumerate(_fields(form_type, ("text", "choice")))
    }
    widgets = read_widgets(PDFFormFiller().fill(form_type, markers))
    return {
        name: {w.full_name for w in widgets if w.value == marker}
        for name, marker in markers.items()
    }


@cache
def _box_fill(form_type, position):
    """Fill the position-th choice of every mapped box at once; boxes share no widgets."""
    values = {}
    for f in _fields(form_type, ("checkbox", "radio")):
        keys = sorted(f.choices or {})
        if position < len(keys):
            values[f.pdf_field] = f.choices[keys[position]]
    return read_widgets(PDFFormFiller().fill(form_type, values))


def _text_cases():
    for form_type in get_all_form_types():
        for f in _fields(form_type, ("text", "choice")):
            yield case_param(form_type, f.pdf_field, TIER, "")


def _box_cases():
    for form_type in get_all_form_types():
        for f in _fields(form_type, ("checkbox", "radio")):
            for key in sorted(f.choices or {}):
                yield case_param(form_type, f.pdf_field, TIER, key)


TEXT_CASES = list(_text_cases())
BOX_CASES = list(_box_cases())


@pytest.mark.parametrize("form_type,pdf_field,case", TEXT_CASES)
def test_value_lands_only_in_the_box_it_names(form_type, pdf_field, case):
    landed = _text_landing(form_type)[pdf_field]
    assert landed, "no_widget: the value landed nowhere"
    assert landed == {pdf_field}, f"spill: the value also landed in {sorted(landed - {pdf_field})}"


@pytest.mark.parametrize("form_type,pdf_field,case", BOX_CASES)
def test_checkbox_ticks_only_the_widgets_for_its_answer(form_type, pdf_field, case):
    field = next(f for f in load_schema(form_type).fields if f.pdf_field == pdf_field)
    state = field.choices[case]
    template = load_schema(form_type).template_filename
    expected = sum(
        1
        for w in load_index(template)[pdf_field]
        if w.on_state and export_state(w.on_state) == state
    )
    own = [
        w
        for w in _box_fill(form_type, sorted(field.choices).index(case))
        if w.full_name == pdf_field
    ]
    ticked = [w for w in own if w.state == state]
    assert len(ticked) == expected, f"no_widget: {len(ticked)} of {expected} widgets show {state}"
    assert all(w.state == "/Off" for w in own if w.state != state), "spill: another option is on"


def test_every_checkbox_binding_maps_its_answers_to_a_box():
    # A box bound with empty choices prints nothing, whatever the filer answers.
    unmapped = [
        (form_type, f.pdf_field)
        for form_type in get_all_form_types()
        for f in _fields(form_type, ("checkbox", "radio"))
        if not f.choices
    ]
    assert unmapped == [], f"unmapped_choice: no answer value maps to a box yet: {unmapped}"
