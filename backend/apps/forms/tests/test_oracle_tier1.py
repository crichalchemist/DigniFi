"""
Oracle tier 1: every binding lands in exactly the widget it names (spec §6).

Each text and combo binding gets a unique sentinel, the real engine draws it on the
real template, and every widget is read back from the printed page (3a2 spec §8): the
sentinel prints in every widget of its name and in no other. A tick is the template's own check mark printed inside the box; /V alone proves nothing
(DIG-68). Only the widgets the engine draws are read: a print button and the second
widget of a stacked pair never print. The engine check gives each widget of a shared
name a sentinel of its own, through its own key, and reads each back; it ticks each
widget of a shared box name alone, one round per position. Only test_every_claims_binding_reads_the_row_it_names uses a
database, because it resolves claims. bindings on a session.
"""

import json
import re
from decimal import Decimal
from functools import cache
from itertools import islice, product
from pathlib import Path
from string import ascii_uppercase
from types import SimpleNamespace

import pypdf
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.field_index import export_state, index_path
from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import _key, resolve_binding
from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
from apps.forms.services.widgets import template_widgets
from apps.forms.tests.oracle import case_param
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.asset_lines import PROPERTY_KINDS
from apps.intake.models import AssetInfo, IntakeSession
from apps.intake.tests.builders import (
    complete_codebtor,
    complete_contract,
    complete_debt,
    linked_loan,
    linked_row,
)

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
    """A binding's values key → its sentinel: unique on the form, and as short as its box needs."""
    sentinels = {}
    short = iter(_SHORT)
    for i, f in enumerate(_fields(form_type, ("text", "choice"))):
        key = _key(f)
        if f.type == "choice":
            sentinels[key] = _option(form_type, f.pdf_field)
        elif _fits(form_type, key, f"Q{i:03d}"):
            sentinels[key] = f"Q{i:03d}"
        else:
            sentinels[key] = next(s for s in short if _fits(form_type, key, s))
    return sentinels


def _target(form_type, key):
    """The binding a values key names: its schema field (R17: a tagged binding is its own case)."""
    return next(f for f in load_schema(form_type).fields if _key(f) == key)


def _widgets_of(form_type, key):
    """(name, page, tag) of each drawn widget a key fills: one for a tagged key, else all."""
    f = _target(form_type, key)
    return {
        (w.full_name, w.page, w.tag)
        for w in template_widgets(load_schema(form_type).template_filename)
        if w.drawn
        and w.full_name == f.pdf_field
        and (f.tag is None or (w.page, w.tag) == (f.page, f.tag))
    }


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
            values[_key(f)] = f.choices[keys[position]]
    return values, _drawn(form_type, values)


def _stray(form_type, drawn, values):
    """(name, page, tag) of each box that prints a tick no key in values asked for."""
    asked = {at: state for key, state in values.items() for at in _widgets_of(form_type, key)}
    return sorted(
        (w.full_name, w.page, w.tag)
        for w in drawn
        if w.state not in ("", "/Off") and asked.get((w.full_name, w.page, w.tag)) != w.state
    )


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
            yield case_param(form_type, _key(f), TIER, "")


def _widget_cases(kinds):
    for form_type in get_all_form_types():
        for name in _shared_names(form_type, kinds):
            yield case_param(form_type, name, TIER, "each_widget")


def _box_cases():
    for form_type in get_all_form_types():
        for f in _fields(form_type, ("checkbox", "radio")):
            for key in sorted(f.choices or {}):
                yield case_param(form_type, _key(f), TIER, key)


TEXT_CASES = list(_text_cases())
BOX_CASES = list(_box_cases())
WIDGET_TEXT_CASES = list(_widget_cases(_TEXT_KINDS))
WIDGET_BOX_CASES = list(_widget_cases(_BOX_KINDS))
WIDGET_CASES = WIDGET_TEXT_CASES + WIDGET_BOX_CASES
SPLIT_FORMS = [
    form_type
    for form_type in get_all_form_types()
    if len(_fields(form_type, ("checkbox", "radio"))) >= 2
]


@pytest.mark.slow
@pytest.mark.parametrize("form_type,pdf_field,case", TEXT_CASES)
def test_value_lands_only_in_the_box_it_names(form_type, pdf_field, case):
    # pdf_field is the binding's values key: its name, or name@page:tag for one widget (R17).
    sentinels, widgets = _text_fill(form_type)
    wanted = _widgets_of(form_type, pdf_field)
    landed = {(w.full_name, w.page, w.tag) for w in widgets if w.value == sentinels[pdf_field]}
    assert landed, "no_widget: the value landed nowhere"
    assert landed <= wanted, f"spill: the value also landed in {sorted(landed - wanted)}"
    # The value prints in every widget the key fills, one page header on each page.
    assert (
        landed == wanted
    ), f"no_widget: the value is missing from widgets {sorted(wanted - landed)}"


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.slow
@pytest.mark.parametrize("form_type,pdf_field,case", BOX_CASES)
def test_checkbox_ticks_only_the_widgets_for_its_answer(form_type, pdf_field, case):
    # pdf_field is the binding's values key (R17): a tagged binding reads its own widget alone.
    field = _target(form_type, pdf_field)
    state = field.choices[case]
    template = load_schema(form_type).template_filename
    mine = _widgets_of(form_type, pdf_field)
    expected = sum(
        1
        for w in template_widgets(template)
        if (w.full_name, w.page, w.tag) in mine and state in w.states
    )
    values, drawn = _box_fill(form_type, sorted(field.choices).index(case))
    own = [w for w in drawn if (w.full_name, w.page, w.tag) in mine]
    ticked = [w for w in own if w.state == state]
    assert len(ticked) == expected, f"no_widget: {len(ticked)} of {expected} widgets show {state}"
    assert all(w.state == "/Off" for w in own if w.state != state), "spill: another option is on"
    # The check mark appears only in the widgets of the choices drawn (spec §8);
    # test_a_tick_never_spills_into_a_box_the_filer_left_blank separates the boxes drawn
    # together here.
    stray = _stray(form_type, drawn, values)
    assert stray == [], f"spill: a tick also prints in {stray}"


@pytest.mark.slow
@pytest.mark.parametrize("form_type", SPLIT_FORMS)
def test_a_tick_never_spills_into_a_box_the_filer_left_blank(form_type):
    # _box_fill ticks every single box at once, so a tick spilling from one into another
    # reads as the other's own answer. Split the boxes by each bit of their index: every
    # pair is then drawn once with one ticked and the other left blank (spec §8).
    fields = sorted(_fields(form_type, ("checkbox", "radio")), key=_key)
    stray = []
    for p in range(max(len(f.choices or {}) for f in fields)):
        boxes = [f for f in fields if len(f.choices or {}) > p]
        if len(boxes) < 2:
            continue
        for k in range((len(boxes) - 1).bit_length()):
            for side in (1, 0):
                values = {
                    _key(f): f.choices[sorted(f.choices)[p]]
                    for i, f in enumerate(boxes)
                    if (i >> k) & 1 == side
                }
                stray += [
                    (p, k, side, *at) for at in _stray(form_type, _drawn(form_type, values), values)
                ]
    assert stray == [], (
        "spill: a tick prints in a box left blank, as (position, bit, side, name, page, tag):"
        f" {stray}"
    )


_ASSET_BINDING = re.compile(r"assets\.line_(\d+)(?:_(\w+))?\[\]\.(\w+)")


def _schedule_a_b_slots():
    return [
        f for f in load_schema("schedule_a_b").fields if (f.binding or "").startswith("assets.")
    ]


def _schedule_a_b_bindings():
    schema = load_schema("schedule_a_b")
    columns = (
        binding
        for group in schema.groups.values()
        for column in group.sheet.columns
        for binding in (column.binding, *(column.covers or ()))
    )
    return sorted({*(f.binding for f in _schedule_a_b_slots()), *columns})


@pytest.mark.parametrize("binding", _schedule_a_b_bindings())
def test_every_schedule_a_b_binding_reads_the_row_it_names(binding):
    # The sentinels above reach the filler without resolving a binding, and the startup check
    # looks only at a binding's namespace, so a binding spelled wrong would first show at
    # Generate. Each must read a filled-in row of its own line, and print something for it.
    key, kind, _ = _ASSET_BINDING.fullmatch(binding).groups()
    row = AssetInfo(
        ab_line=key,
        description="Words",
        current_value=Decimal("1.00"),
        entire_value=Decimal("2.00"),
        details=json.dumps(
            {
                **dict.fromkeys(
                    (
                        "street",
                        "street_2",
                        "city",
                        "state",
                        "zip",
                        "county",
                        "other_kind",
                        "nature",
                        "other_info",
                        "make",
                        "model",
                        "year",
                        "mileage",
                        "percent",
                        "beneficiary",
                    ),
                    "Words",
                ),
                "kind": kind,
                "who": "only_you",
                "community": True,
                "has_personal_info": True,
                "property_kinds": list(PROPERTY_KINDS),
            }
        ),
    )
    session = SimpleNamespace(pk=None, assets=SimpleNamespace(all=lambda: [row]))
    (cell,) = resolve_binding(binding, session)
    assert cell


def _claims_bindings():
    return sorted(
        {
            f.binding
            for form_type in get_all_form_types()
            for f in load_schema(form_type).fields
            if f.binding and f.binding.startswith("claims.")
        }
    )


@pytest.fixture
def claims_session(db):
    user = get_user_model().objects.create_user(username="tier1claims", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    party = {
        "name": "Demo Notice Party",
        "street_address": "9 Demo Street",
        "street_2": "",
        "city": "Demoville",
        "state": "IL",
        "zip_code": "60601",
        "outside_us": False,
        "last_4": "",
    }
    row = linked_row(session, "3", lives_here=None)
    secured = linked_loan(session, row, "100", notice_parties=[party])
    unsecured = complete_debt(session, notice_parties=[party])
    contract = complete_contract(session)
    complete_codebtor(
        session,
        links=[
            {"kind": "debt", "id": secured.pk},
            {"kind": "debt", "id": unsecured.pk},
            {"kind": "contract", "id": contract.pk},
        ],
    )
    return session


@pytest.mark.parametrize("binding", _claims_bindings())
def test_every_claims_binding_reads_the_row_it_names(binding, claims_session):
    # A binding spelled wrong passes the startup check, which reads only its namespace, and
    # would first fail at Generate. Each must read a complete row of its own list. A box cell
    # may be blank on a complete row (who_debtor_1 under a codebtor link, other_type on a
    # student loan), so only the name, the city and a claim's amount must print something.
    (cell,) = resolve_binding(binding, claims_session)
    attr = binding.rpartition(".")[2]
    if attr in ("name", "city", "amount"):
        assert cell


def test_every_schedule_a_b_slot_binds_the_line_and_row_its_box_is_on():
    # The template's names mislead (3.2's Make box is "If you own or have more than one describe
    # here"), so a box is held to the line and row the index read from the page. A line whose
    # kind picks the row, or whose rows the index doesn't number, is held to its line alone.
    index = json.loads((settings.FORM_INDEX_DIRECTORY / "form_b106ab.index.json").read_text())
    lines = {}
    for row in index:
        lines.setdefault(row["full_name"], set()).add(row["line"].rstrip("."))
    wrong = []
    for f in _schedule_a_b_slots():
        key, kind, _ = _ASSET_BINDING.fullmatch(f.binding).groups()
        for line in lines[f.pdf_field]:
            on_line, _, row = line.partition(".")
            if on_line != key or (row and not kind and int(row) != f.row):
                wrong.append((f.pdf_field, line, f.binding, f.row))
    assert wrong == []


_DEBT_STATUS = "As of the date you file, the claim is: Check all that apply."
_LIEN = "Nature of lien. Check all that apply."
_WHO = {"debtor_1": "Debtor 1 only", "another": "At least one of the debtors and another"}
_D_COMMUNITY = "Check if this claim relates to a community debt"
_EF_COMMUNITY = "Check if this claim is for a community debt"
_ADDRESS = {"city": ("City", None), "state": ("State", None), "zip": ("ZIP Code", None)}
_H_COLUMN_2 = "Check all schedules that apply: Schedule "
# Each claims cell's column as the index read it from the page: the box's label, less its
# parentheticals and the index's notes, and for a tick the words beside each box an answer ticks.
_CLAIMS_COLUMNS = {
    "d_part_1": {
        "amount": ("Amount of claim", None),
        "value": ("Value of collateral that supports this claim", None),
        "unsecured": ("Unsecured portion", None),
        "name": ("Creditor's Name", None),
        "street": ("Number Street", None),
        "street_2": ("Creditor address, second line", None),
        **_ADDRESS,
        "property": ("Describe the property that secures the claim:", None),
        "contingent": (_DEBT_STATUS, {"true": "Contingent"}),
        "unliquidated": (_DEBT_STATUS, {"true": "Unliquidated"}),
        "disputed": (_DEBT_STATUS, {"true": "Disputed"}),
        "lien_agreement": (
            _LIEN,
            {"true": "An agreement you made (such as mortgage or secured car loan)"},
        ),
        "lien_statutory": (_LIEN, {"true": "Statutory lien (such as tax lien, mechanic's lien)"}),
        "lien_judgment": (_LIEN, {"true": "Judgment lien from a lawsuit"}),
        "lien_other": (_LIEN, {"true": "Other (including a right to offset)"}),
        "lien_other_text": ("Other: specify", None),
        "community": (_D_COMMUNITY, {"true": _D_COMMUNITY}),
        "date": ("Date debt was incurred", None),
        "last_4": ("Last 4 digits of account number", None),
        "who": ("Who owes the debt? Check one.", _WHO),
        "who_debtor_1": ("Who owes the debt? Check one.", {"true": _WHO["debtor_1"]}),
        "who_another": ("Who owes the debt? Check one.", {"true": _WHO["another"]}),
    },
    "d_part_2": {
        "name": ("Name", None),
        "street": ("Number Street", None),
        "street_2": ("Address, second line", None),
        **_ADDRESS,
        "line": ("On which line in Part 1 did you enter the creditor?", None),
        "last_4": ("Last 4 digits of account number.", None),
    },
    "ef_part_2": {
        "name": ("Nonpriority Creditor's Name", None),
        "last_4": ("Last 4 digits of account number", None),
        "amount": ("Total claim", None),
        "date": ("When was the debt incurred?", None),
        "street_joined": ("Number Street", None),
        **_ADDRESS,
        "contingent": (_DEBT_STATUS, {"true": "Contingent"}),
        "unliquidated": (_DEBT_STATUS, {"true": "Unliquidated"}),
        "disputed": (_DEBT_STATUS, {"true": "Disputed"}),
        "who": ("Who incurred the debt? Check one.", _WHO),
        "student_loans": ("Type of NONPRIORITY unsecured claim:", {"true": "Student loans"}),
        "other_type": ("Type of NONPRIORITY unsecured claim:", {"true": "Other. Specify"}),
        "other_type_words": ("Other. Specify ____", None),
        "community": (_EF_COMMUNITY, {"true": _EF_COMMUNITY}),
        "offset": ("Is the claim subject to offset?", {"no": "No", "yes": "Yes"}),
    },
    "ef_part_3": {
        "name": ("Name", None),
        "street": ("Number Street", None),
        "street_2": ("Address, second line", None),
        **_ADDRESS,
        "line": (
            "On which entry in Part 1 or Part 2 did you list the original creditor? Line ____",
            None,
        ),
        "part": ("Line ____ of:", {"2": "Part 2: Creditors with Nonpriority Unsecured Claims"}),
        "last_4": ("Last 4 digits of account number", None),
    },
    "g": {
        "name": ("Name", None),
        # page 1 and page 2 word the column differently
        "purpose": (
            ("State what the contract or lease is for", "What the contract or lease is for"),
            None,
        ),
        "street_joined": ("Number Street", None),
        **_ADDRESS,
    },
    "h": {
        "name": ("Name", None),
        "street_joined": ("Number Street", None),
        **_ADDRESS,
        "on_d": (_H_COLUMN_2 + "D", {"true": "Schedule D, line"}),
        "d_lines": ("Schedule D, line ____", None),
        "on_ef": (_H_COLUMN_2 + "E/F", {"true": "Schedule E/F, line"}),
        "ef_lines": ("Schedule E/F, line ____", None),
        "on_g": (_H_COLUMN_2 + "G", {"true": "Schedule G, line"}),
        "g_lines": ("Schedule G, line ____", None),
    },
}
# The rows each group's first page numbers before its additional page, whose rows the index
# counts from 1 ("Additional Page row 1" is D's 2.3).
_ROWS_BEFORE_THE_ADDITIONAL_PAGE = {"d_part_1": 2, "ef_part_2": 3, "g": 5, "h": 3}
_ROW_IN_LABEL = re.compile(r"\([^()]*\b(Page row|entry) (\d+)\b")


def _column_words(label):
    words = re.sub(r"\s*\([^)]*\)", "", label)
    return re.split(r" (?:Template defect|Field name)\b", words)[0].strip()


def _row_on_template(group, widget):
    """The row the index read from the page: its numbered line, or the row its label names."""
    row = widget["line"].partition(".")[2]
    if row:
        return int(row)
    match = _ROW_IN_LABEL.search(widget["label"])
    if match is None:
        return None
    kind, n = match.groups()
    return int(n) + (_ROWS_BEFORE_THE_ADDITIONAL_PAGE[group] if kind == "Page row" else 0)


def test_every_claims_slot_binds_the_row_and_column_its_box_is_on():
    # The generator's tables place each cell by name, and every other test reads those same
    # tables, so a swapped pair of boxes (row 2.4's Columns B and C, or two Part 2 line boxes)
    # would print one row's figure in another's box. Each slot is held to the index instead: its
    # column, the row the index numbers, and, since many of those labels were read by pattern, its
    # boxes' place on the page, every row of a page wholly below the row before.
    wrong = []
    for form_type in ("schedule_d", "schedule_e_f", "schedule_g", "schedule_h"):
        schema = load_schema(form_type)
        index = json.loads(index_path(schema.template_filename).read_text())
        rects = {}  # (group, page) -> {row: [rect, ...]}, rects from the page's top left
        for f in schema.fields:
            if not (f.binding or "").startswith("claims."):
                continue
            attr = f.binding.rpartition(".")[2]
            words, options = _CLAIMS_COLUMNS[f.repeat][attr]
            accepted = words if isinstance(words, tuple) else (words,)
            widgets = [
                w
                for w in index
                if w["full_name"] == f.pdf_field
                and w["page"] == f.page
                and f.tag in (None, w["tag"])
            ]
            if not widgets:
                wrong.append((f.pdf_field, f.tag, f.binding, "no widget"))
            for w in widgets:
                if _column_words(w["label"]) not in accepted:
                    wrong.append((f.pdf_field, w["tag"], f.binding, w["label"]))
                if _row_on_template(f.repeat, w) != f.row:
                    wrong.append((f.pdf_field, w["tag"], f.binding, f.row, w["line"], w["label"]))
                rects.setdefault((f.repeat, w["page"]), {}).setdefault(f.row, []).append(w["rect"])
            for answer, state in (f.choices or {}).items():
                beside = {
                    w["option_text"]
                    for w in widgets
                    if w["on_state"] and export_state(w["on_state"]) == state
                }
                if beside != {options[answer]}:
                    wrong.append((f.pdf_field, f.binding, answer, beside))
        for (group, page), rows in rects.items():
            bottom = None
            for row in sorted(rows):
                if bottom is not None and min(r[1] for r in rows[row]) <= bottom:
                    wrong.append(("band", form_type, group, page, row))
                bottom = max(r[3] for r in rows[row])
    assert wrong == []


def test_every_checkbox_binding_maps_its_answers_to_a_box():
    # A box bound with empty choices prints nothing, whatever the filer answers.
    unmapped = [
        (form_type, f.pdf_field)
        for form_type in get_all_form_types()
        for f in _fields(form_type, ("checkbox", "radio"))
        if not f.choices
    ]
    assert unmapped == [], f"unmapped_choice: no answer value maps to a box yet: {unmapped}"
