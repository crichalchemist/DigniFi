"""
Oracle tier 1: every binding lands in exactly the widget it names (spec §6).

Each text and combo binding gets a unique sentinel, the real engine draws it on the
real template, and every widget is read back from the printed page (3a2 spec §8): the
sentinel prints in every widget of its name and in no other. A tick is the template's own check mark printed inside the box; /V alone proves nothing
(DIG-68). Only the widgets the engine draws are read: a print button and the second
widget of a stacked pair never print. The engine check gives each widget of a shared
name a sentinel of its own, through its own key, and reads each back; it ticks each
widget of a shared box name alone, one round per position. No database is needed.
"""

from functools import cache
from itertools import islice, product
from pathlib import Path
from string import ascii_uppercase

import pypdf
import pytest
from django.conf import settings

from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
from apps.forms.services.widgets import template_widgets
from apps.forms.tests.oracle import case_param
from apps.forms.tests.pdf_readback import read_drawn

TIER = "1"


def _fields(form_type, types):
    return [f for f in load_schema(form_type).fields if f.type in types]


def _fits(form_type, pdf_field, value):
    try:
        PDFFormFiller().check(form_type, {pdf_field: value})
    except ValueTooLong:
        return False
    return True


def _option(form_type, pdf_field, nth=0):
    """
    A combo's first (or nth) option that prints and fits: not a blank one, and not the
    template's own default, which the blank form prints already.
    """
    template = Path(settings.PDF_FORMS_DIRECTORY) / load_schema(form_type).template_filename
    field = pypdf.PdfReader(template).get_fields()[pdf_field]
    options = (
        str(option)
        for option in field["/Opt"]
        if str(option).strip()
        and str(option) != str(field.get("/V"))
        and _fits(form_type, pdf_field, str(option))
    )
    return next(islice(options, nth, None))


# Shorter sentinels for boxes too small for "Q001": two letters, then one. Letters only,
# so none equals a box's own blank text ("2", "0%").
_SHORT = ["".join(pair) for pair in product(ascii_uppercase, repeat=2)] + list(ascii_uppercase)


def _sentinels(form_type):
    """pdf_field → its sentinel: unique on the form, and as short as its box needs."""
    sentinels = {}
    short = iter(_SHORT)
    for i, f in enumerate(_fields(form_type, ("text", "choice"))):
        if f.type == "choice":
            sentinels[f.pdf_field] = _option(form_type, f.pdf_field)
        elif _fits(form_type, f.pdf_field, f"Q{i:03d}"):
            sentinels[f.pdf_field] = f"Q{i:03d}"
        else:
            sentinels[f.pdf_field] = next(s for s in short if _fits(form_type, f.pdf_field, s))
    return sentinels


def _drawn(form_type, values):
    """What the drawn form prints in each widget the engine draws."""
    template = load_schema(form_type).template_filename
    drawn = {(w.page, w.tag) for w in template_widgets(template) if w.drawn}
    return [
        w
        for w in read_drawn(form_type, PDFFormFiller().fill(form_type, values))
        if (w.page, w.tag) in drawn
    ]


@cache
def _text_fill(form_type):
    """Every text and combo binding's sentinel, and what each drawn widget prints with all of them."""
    sentinels = _sentinels(form_type)
    return sentinels, _drawn(form_type, sentinels)


@cache
def _box_fill(form_type, position):
    """
    Fill the position-th choice of every mapped box at once; boxes share no widgets.
    Returns the values drawn, and what each drawn widget prints with them.
    """
    values = {}
    for f in _fields(form_type, ("checkbox", "radio")):
        keys = sorted(f.choices or {})
        if position < len(keys):
            values[f.pdf_field] = f.choices[keys[position]]
    return values, _drawn(form_type, values)


_TEXT_KINDS = ("Text", "ComboBox")
_BOX_KINDS = ("CheckBox", "RadioButton")


def _shared_names(form_type, kinds):
    """Full name → its drawn widgets of those kinds, for each name more than one widget has."""
    widgets = {}
    for w in template_widgets(load_schema(form_type).template_filename):
        if w.drawn and w.kind in kinds:
            widgets.setdefault(w.full_name, []).append(w)
    return {name: named for name, named in widgets.items() if len(named) > 1}


@cache
def _widget_fill(form_type):
    """
    A sentinel for each widget of every shared name, given through the widget's own key
    (name@page:tag), and what each drawn widget prints with all of them, read once the
    form has no widget left.
    """
    sentinels = {}
    short = iter(_SHORT)
    for name, widgets in _shared_names(form_type, _TEXT_KINDS).items():
        for k, w in enumerate(widgets):
            sentinel = f"W{len(sentinels):03d}"
            if w.kind == "ComboBox":  # 103B's two district boxes: a district each
                sentinel = _option(form_type, name, nth=k)
            elif not _fits(form_type, w.key, sentinel):
                sentinel = next(s for s in short if _fits(form_type, w.key, s))
            sentinels[w.key] = sentinel
    return sentinels, _drawn(form_type, sentinels)


@cache
def _widget_box_fill(form_type, k):
    """Tick the k-th widget of every shared box name through its own key, in one draw."""
    return _drawn(
        form_type,
        {
            widgets[k].key: widgets[k].states[0]
            for widgets in _shared_names(form_type, _BOX_KINDS).values()
            if k < len(widgets)
        },
    )


def _text_cases():
    for form_type in get_all_form_types():
        for f in _fields(form_type, ("text", "choice")):
            yield case_param(form_type, f.pdf_field, TIER, "")


def _widget_cases(kinds):
    for form_type in get_all_form_types():
        for name in _shared_names(form_type, kinds):
            yield case_param(form_type, name, TIER, "each_widget")


def _box_cases():
    for form_type in get_all_form_types():
        for f in _fields(form_type, ("checkbox", "radio")):
            for key in sorted(f.choices or {}):
                yield case_param(form_type, f.pdf_field, TIER, key)


TEXT_CASES = list(_text_cases())
BOX_CASES = list(_box_cases())
WIDGET_TEXT_CASES = list(_widget_cases(_TEXT_KINDS))
WIDGET_BOX_CASES = list(_widget_cases(_BOX_KINDS))
WIDGET_CASES = WIDGET_TEXT_CASES + WIDGET_BOX_CASES


@pytest.mark.parametrize("form_type,pdf_field,case", TEXT_CASES)
def test_value_lands_only_in_the_box_it_names(form_type, pdf_field, case):
    sentinels, widgets = _text_fill(form_type)
    landed = {w.full_name for w in widgets if w.value == sentinels[pdf_field]}
    assert landed, "no_widget: the value landed nowhere"
    assert landed == {pdf_field}, f"spill: the value also landed in {sorted(landed - {pdf_field})}"
    # The value prints in every widget its name has, one page header on each page.
    missed = [
        (w.page, w.tag)
        for w in widgets
        if w.full_name == pdf_field and w.value != sentinels[pdf_field]
    ]
    assert missed == [], f"no_widget: the value is missing from widgets {missed}"


@pytest.mark.parametrize("form_type,pdf_field,case", WIDGET_TEXT_CASES)
def test_each_widget_of_a_shared_name_prints_its_own_value(form_type, pdf_field, case):
    # Widgets that share a name (page headers, Schedule D's account boxes, A/B's 24.1) can
    # each take a value of their own through their own key (3a2 spec §4.2, §8): each must
    # print its own, not its sibling's, and not nothing.
    sentinels, widgets = _widget_fill(form_type)
    printed = {(w.page, w.tag): w.value for w in widgets if w.full_name == pdf_field}
    own = {
        (w.page, w.tag): sentinels[w.key] for w in _shared_names(form_type, _TEXT_KINDS)[pdf_field]
    }
    blank = sorted(at for at, value in printed.items() if not value)
    assert blank == [], f"no_widget: widgets {blank} print nothing"
    crossed = {at: value for at, value in printed.items() if value != own[at]}
    assert crossed == {}, f"collision: widgets print another widget's value: {crossed}"


@pytest.mark.parametrize("form_type,pdf_field,case", WIDGET_BOX_CASES)
def test_each_widget_of_a_shared_box_name_ticks_alone(form_type, pdf_field, case):
    # A box carries no value of its own, so each widget of a shared box name (the options
    # of one question, Form 101's twelve "Check Box22") is ticked alone through its own key,
    # one round per position (R50): it prints its tick, and no sibling prints one.
    for k, widget in enumerate(_shared_names(form_type, _BOX_KINDS)[pdf_field]):
        at = (widget.page, widget.tag)
        printed = {
            (w.page, w.tag): w.state
            for w in _widget_box_fill(form_type, k)
            if w.full_name == pdf_field
        }
        assert printed[at] == widget.states[0], f"no_widget: widget {at} prints no tick"
        spilled = sorted(
            other for other, state in printed.items() if other != at and state != "/Off"
        )
        assert spilled == [], f"collision: ticking widget {at} also ticks {spilled}"


@pytest.mark.parametrize("form_type,pdf_field,case", BOX_CASES)
def test_checkbox_ticks_only_the_widgets_for_its_answer(form_type, pdf_field, case):
    field = next(f for f in load_schema(form_type).fields if f.pdf_field == pdf_field)
    state = field.choices[case]
    template = load_schema(form_type).template_filename
    expected = sum(
        1
        for w in template_widgets(template)
        if w.full_name == pdf_field and w.drawn and state in w.states
    )
    values, drawn = _box_fill(form_type, sorted(field.choices).index(case))
    own = [w for w in drawn if w.full_name == pdf_field]
    ticked = [w for w in own if w.state == state]
    assert len(ticked) == expected, f"no_widget: {len(ticked)} of {expected} widgets show {state}"
    assert all(w.state == "/Off" for w in own if w.state != state), "spill: another option is on"
    # The check mark appears only in the widgets of the choices drawn (spec §8), never in a
    # widget of another name.
    stray = sorted(
        (w.full_name, w.page, w.tag)
        for w in drawn
        if w.state not in ("", "/Off") and values.get(w.full_name) != w.state
    )
    assert stray == [], f"spill: a tick also prints in {stray}"


def test_every_checkbox_binding_maps_its_answers_to_a_box():
    # A box bound with empty choices prints nothing, whatever the filer answers.
    unmapped = [
        (form_type, f.pdf_field)
        for form_type in get_all_form_types()
        for f in _fields(form_type, ("checkbox", "radio"))
        if not f.choices
    ]
    assert unmapped == [], f"unmapped_choice: no answer value maps to a box yet: {unmapped}"
