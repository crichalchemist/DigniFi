"""Form 122A-2's schema: line 1 copies 122A-1's monthly income, every one of the form's 198
widgets is bound to its calculator line or blank on purpose, and only the filer's own answers
carry legal review (3h3 plan R1, R2, R15, R21)."""

import json
from decimal import Decimal

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.cmi import IncomeNotSplit
from apps.eligibility.means_lines import LINE_KEYS
from apps.forms.field_index import export_state
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.tests.test_derivations import TEN_SOURCES
from apps.intake.models import IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household

User = get_user_model()

# R15: the 12 names (20 widgets) no binding fills, a judgment the app doesn't make or a line
# for wet ink: Debtor 2, the case number on every page, the amended-filing box, the signatures
# and dates, line 10's housing adjustment, and each vehicle description's second box (H25).
BLANK_ON_PURPOSE = {
    "Debtor2.Name",
    "Case number1",
    "CheckBox2",
    "Debtor1.sig",
    "Debtor2.sig",
    "Debtor1.Date signed",
    "Debtor2.Date signed",
    "Quest10",
    "Explain 1",
    "Explain 2",
    "Describe Vehicle 1 2",
    "Describe Vehicle 2 2",
}
# R21: the LINE_KEYS entries with no widget of their own.
UNPRINTED_LINE_KEYS = {"33d", "25_answer"}
# R21, R25: a line printed by a name shared with another line, which binds once on its first page.
COPIED_BY_SHARED_NAME = {"39a": "4", "33a": "9b", "33b": "13b", "33c": "13e", "39b": "38"}
# R1: the filer's own answers, every widget of §10's asked units (3, 9b, 11, 13b, 13e, 15–23,
# 25–31, 33d, 34, 36, 43) with their totals and line 36's figures, except the creditor, property
# and vehicle-description cells, which Amounts Owed and the Assets step hold.
LEGAL_REVIEW = {
    "CheckBox5",
    "Quest3A",
    "Quest3A1",
    "Quest3B",
    "Quest3B1",
    "Quest3C",
    "Quest3C1",
    "Quest3",
    "Quest9B creditor amount1",
    "Quest9B creditor amount2",
    "Quest9B creditor amount3",
    "Quest9B total amount",
    "CheckBox6",
    "Quest13B amount for vehicle 1-1",
    "Quest13B amount for vehicle 1-2",
    "Quest13B Total amount for vehicle 1",
    "Quest13E.Monthly1",
    "Quest13E.Monthly2",
    "Quest13E.TotalMonthly",
    "Quest15",
    "undefined_48",
    "undefined_49",
    "undefined_50",
    "undefined_51",
    "undefined_52",
    "undefined_53",
    "undefined_54",
    "undefined_55",
    "undefined_57",
    "undefined_58",
    "1_2",
    "2_2",
    "CheckBox7",
    "undefined_59",
    "undefined_61",
    "undefined_62",
    "undefined_63",
    "undefined_64",
    "undefined_65",
    "undefined_66",
    "CheckBox8",
    "undefined_73",
    "CheckBox9",
    "undefined_76",
    "CheckBox10",
    "undefined_79",
    "CheckBox11",
    "undefined_82",
    "undefined_83",
    "undefined_86",
    "undefined_87",
    "undefined_90",
    "undefined_91",
    "undefined_92",
    "CheckBox13",
    "undefined_97",
    "x",
    "undefined_98",
    "CheckBox16",
    "undefined_113",
    "undefined_114",
    "undefined_115",
    "undefined_116",
    "undefined_117",
    "undefined_118",
    "undefined_119",
    "undefined_120",
}
# R2: the keys each box's reader can return, mapped by the schema to the index's states.
READER_KEYS = {
    "CheckBox1": {"no_presumption", "presumption"},
    "CheckBox6": {"0", "1", "2_or_more"},
    "CheckBox14": {"1", "2", "between"},
}
YES_NO = {"yes", "no"}


def _index():
    path = settings.FORM_INDEX_DIRECTORY / "b_122a-2_0425-form.index.json"
    return json.loads(path.read_text())


def _fields():
    return load_schema("form_122a2").fields


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema122a2", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def test_line_1_copies_the_monthly_income_from_122a1_line_11(session):
    # Line 1 says "Copy line 11 from Official Form 122A-1 here": current monthly income,
    # which leaves Social Security out (C1), never an expense or deduction total.
    IncomeInfo.objects.create(session=session, **TEN_SOURCES)
    answer_household(session)

    printed = resolve(load_schema("form_122a2"), session)

    # Every source but Social Security's 32.00: 1023.00 - 32.00.
    assert printed.get("Quest1") == "991.00"
    # line 11's total, Column A + Column B, which line 1 copies
    assert printed.get("Quest1") == resolve(load_schema("form_122a1"), session)["Quest11"]


@pytest.mark.parametrize("form_type", ["form_106sum", "form_122a1", "form_122a2"])
def test_empty_session_is_asked_for_income_by_source(session, form_type):
    # 106Sum line 8, 122A-1 lines 11 to 13 and 122A-2 line 1 are CMI, and a filer who
    # gave no income has none to print (spec §5.5).
    with pytest.raises(IncomeNotSplit):
        resolve(load_schema(form_type), session)


def test_every_122a2_widget_is_bound_or_blank_on_purpose():
    # 198 = 178 bound + 20 blank on purpose, proven by widget (R15): a tool that leaves line
    # 38's three copy boxes out binds 175 and fails here, and so does one that binds a
    # blank-on-purpose box.
    widgets = [w for w in _index() if w["type"] != "Button"]
    assert len(widgets) == 198
    bound = {f.pdf_field for f in _fields()}

    assert bound & BLANK_ON_PURPOSE == set()
    assert {w["full_name"] for w in widgets} == bound | BLANK_ON_PURPOSE
    assert sum(w["full_name"] in bound for w in widgets) == 178
    assert sum(w["full_name"] in BLANK_ON_PURPOSE for w in widgets) == 20


def test_every_calculator_line_prints_or_is_listed():
    # Every line the calculator works out reaches the page (R21): in a box of its own, through a
    # name another line shares, through Quest1's cmi rule, or on the list of keys with no widget.
    # Only the scalar bindings count: a list cell never stands in for a dropped total, and line
    # 43's eight form rows are the form's own, with no calculator line behind them.
    scalars = [
        f
        for f in _fields()
        if f.binding and f.repeat is None and not f.binding.startswith("means.line_43_")
    ]
    bound = {f.binding.removeprefix("means.").removeprefix("line_"): f.pdf_field for f in scalars}
    lines = {}
    for w in _index():
        lines.setdefault(w["full_name"], set()).add(w["line"])

    for key in LINE_KEYS:
        if key in bound or key in UNPRINTED_LINE_KEYS or key == "1":
            continue
        other = COPIED_BY_SHARED_NAME[key]
        # the other line's box is drawn again on a widget the index puts on this line
        assert key in lines[bound[other]], key
    assert set(bound) <= set(LINE_KEYS)
    assert "1" not in bound  # Quest1 keeps its cmi rule


def test_the_filers_answers_carry_legal_review_and_nothing_else_does():
    # Every means. field is asked (R1): the UPL guard would keep a derived legal_review box
    # blank for everyone. legal_review marks the filer's own answers, field by field.
    fields = _fields()
    for f in fields:
        if f.binding:
            assert f.binding.startswith("means."), f.pdf_field
            assert (f.source, f.rule) == ("asked", None), f.pdf_field
        else:
            assert f.source == "derived", f.pdf_field
            assert f.rule in ("full_name", "district_name", "cmi"), f.pdf_field
        assert f.legal_review is (f.pdf_field in LEGAL_REVIEW), f.pdf_field
    assert LEGAL_REVIEW <= {f.pdf_field for f in fields}


def test_every_checkbox_maps_the_readers_keys_to_the_indexs_states():
    # A box's choices keys are exactly what means_value can return for it (R2), and its values
    # the index's export states (E005 checks the values; a missing key would print nothing).
    states = {}
    for w in _index():
        if w["on_state"]:
            states.setdefault(w["full_name"], set()).add(export_state(w["on_state"]))
    boxes = [f for f in _fields() if f.type == "checkbox"]

    assert len(boxes) == 15
    for f in boxes:
        assert set(f.choices) == READER_KEYS.get(f.pdf_field, YES_NO), f.pdf_field
        assert set(f.choices.values()) == states[f.pdf_field], f.pdf_field


def test_each_33d_slot_keeps_its_own_choices_map():
    # Row 3's Yes is /On where rows 1 and 2 tick /Yes, so each slot carries its own map and the
    # sheet reads row 1's through option_text (R14).
    boxes = {f.pdf_field: f for f in _fields() if f.repeat == "means_line_33d" and f.choices}

    assert {name: f.choices for name, f in boxes.items()} == {
        "CheckBox8": {"no": "/No", "yes": "/Yes"},
        "CheckBox9": {"no": "/No", "yes": "/Yes"},
        "CheckBox10": {"no": "/No", "yes": "/On"},
    }
    assert [boxes[name].row for name in ("CheckBox8", "CheckBox9", "CheckBox10")] == [1, 2, 3]
