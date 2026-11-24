"""
Form 122A-1Supp prints line 1 and Part 2 exactly as the form routes them (forms step 4d, 4d-R7,
4d-R8, 4d-R9, 4d-R26).

Business intent: the Supp is a sworn statement that a filer is exempt from, or excluded from, the
presumption of abuse. A box the form's routing skips must print blank, never a No the filer didn't
give and never an answer the form doesn't reach: line 1's one answer ticks one box, Part 2 prints
only under consumer debts, line 2 Yes to both questions skips line 3 (R-D2), each follow-up prints
only under its own Yes, and a date prints only under its own category, only as MM/DD/YYYY. "None of
these categories applies to me" (D9) claims nothing, so no category box ticks.
"""

import itertools
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.field_index import load_index
from apps.forms.schema import load_schema
from apps.forms.services.derivations import ANSWER_BOX_RULES, PREDICATES
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import DebtorInfo, IntakeSession
from apps.intake.petition import _SUPP_SHOWN
from apps.intake.tests.builders import answer_petition

User = get_user_model()

FORM = "form_122a1_supp"
LINE_3_BOXES = ("CheckBox5", "CheckBox6", "CheckBox7", "Date1", "Date2")
PART_2_BOXES = ("CheckBox3", "CheckBox4", *LINE_3_BOXES)

# Every Part 2 answer Yes, a category with both dates: a stored answer the form doesn't reach.
EVERY_YES = {
    "disabled_veteran": "yes",
    "debts_on_duty": "yes",
    "reservist": "yes",
    "called_to_duty": "yes",
    "duty_category": "2",
    "duty_released_on": "03/14/2026",
    "duty_ended_on": "03/14/2026",
}
# Line 2 settled No, line 3 reached and its follow-up Yes: the categories show.
TO_THE_CATEGORIES = {
    "debt_nature": "consumer",
    "disabled_veteran": "no",
    "reservist": "yes",
    "called_to_duty": "yes",
}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="supp_filer", password="pw")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtorInfo.objects.create(
        session=session,
        first_name="Demo",
        last_name="Filer",
        ssn="900-11-2222",
        date_of_birth=date(1990, 1, 15),
        street_address="1 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


def _printed(session):
    return resolve(load_schema(FORM), session)


def _boxes(values, names):
    """The values printed in any of the named boxes, by box key."""
    return {key: value for key, value in values.items() if key.partition("@")[0] in names}


# Line 1 asks Form 101 line 16a again: the filer's own line 16 answer ticks exactly one of its two
# boxes (R-D6), and an unanswered line 16 ticks neither.
LINE_1_TICKED = {
    "consumer": {"T7": "/Yes"},
    "business": {"T6": "/no"},
    "neither": {"T6": "/no"},
    None: {},
}


@pytest.mark.slow
@pytest.mark.parametrize("answer", LINE_1_TICKED)
def test_the_supps_line_1_ticks_exactly_one_box(session, answer):
    answer_petition(session, debt_nature=answer)
    if answer is None:
        assert "debt_nature" not in session.petition_answers.get_answers()
    widgets = read_drawn(FORM, PDFFormFiller().fill(FORM, _printed(session)))
    line_1 = [w for w in widgets if w.full_name == "CheckBox2"]
    assert sorted(w.tag for w in line_1) == ["T6", "T7"]
    ticked = {w.tag: w.state for w in line_1 if w.state not in ("", "/Off")}
    assert ticked == LINE_1_TICKED[answer]


def test_line_2_yes_yes_prints_no_line_3_box(session):
    # R-D2: line 2's Yes to both questions sends the filer to Form 122A-1's box 1, so line 3 is
    # never reached, whatever line 3 answers are stored.
    answer_petition(session, debt_nature="consumer", **EVERY_YES)

    values = _printed(session)

    assert _boxes(values, ("CheckBox3", "CheckBox4")) == {"CheckBox3": "/Yes", "CheckBox4": "/Yes"}
    assert _boxes(values, LINE_3_BOXES) == {}


@pytest.mark.parametrize(
    "gate,follow_up,stored,box,printed",
    [
        ("disabled_veteran", "debts_on_duty", "no", "CheckBox4", "/no"),
        ("reservist", "called_to_duty", "no", "CheckBox6", "/no"),
        ("called_to_duty", "duty_category", "3", "CheckBox7", "/3"),
    ],
)
def test_each_follow_up_prints_only_under_its_own_yes(
    session, gate, follow_up, stored, box, printed
):
    base = {**TO_THE_CATEGORIES, follow_up: stored}

    answer_petition(session, **{**base, gate: "no"})
    assert box not in _printed(session)

    answer_petition(session, **{**base, gate: "yes"})
    assert _printed(session)[box] == printed


@pytest.mark.parametrize("answer", ["business", "neither", None])
def test_part_2_prints_nothing_under_business_or_neither(session, answer):
    # Line 1's No sends the filer to Form 122A-1 box 1: Part 2 is never reached, and an
    # unanswered line 1 reaches nothing either.
    answer_petition(session, debt_nature=answer, **EVERY_YES)
    if answer is None:
        # Ruling E: the case really has line 16 unanswered, not a default's consumer
        assert "debt_nature" not in session.petition_answers.get_answers()

    assert _boxes(_printed(session), PART_2_BOXES) == {}


@pytest.mark.parametrize(
    "category,released,ended,printed",
    [
        ("2", "03/14/2026", "03/14/2026", {"Date1": "03/14/2026"}),
        ("4", "03/14/2026", "03/14/2026", {"Date2": "03/14/2026"}),
        ("2", "13/45/20", "03/14/2026", {}),
        ("4", "03/14/2026", "13/45/20", {}),
        ("1", "03/14/2026", "03/14/2026", {}),
        ("3", "03/14/2026", "03/14/2026", {}),
    ],
)
def test_a_date_prints_only_under_its_category_and_only_as_mm_dd_yyyy(
    session, category, released, ended, printed
):
    answer_petition(
        session,
        **TO_THE_CATEGORIES,
        duty_category=category,
        duty_released_on=released,
        duty_ended_on=ended,
    )

    assert _boxes(_printed(session), ("Date1", "Date2")) == printed
    # A date the form can't read prints blank; the stored value stays as typed.
    stored = session.petition_answers.get_answers()
    assert (stored["duty_released_on"], stored["duty_ended_on"]) == (released, ended)


def test_none_applies_ticks_no_category(session):
    # D9: "None of these categories applies to me" is an answer that claims no exclusion, so no
    # category box ticks, no date prints and nothing is refused as an unmapped choice.
    answer_petition(
        session,
        **TO_THE_CATEGORIES,
        duty_category="none",
        duty_released_on="03/14/2026",
        duty_ended_on="03/14/2026",
    )

    values = _printed(session)

    assert values["CheckBox6"] == "/Yes"
    assert _boxes(values, ("CheckBox7", "Date1", "Date2")) == {}


@pytest.mark.parametrize("category", ["1", "2", "3", "4"])
def test_the_category_box_ticks_only_the_filers_own_category(session, category):
    # 4d-R26: the category prints through a rule that returns only the filer's own stored
    # category, so the UPL guard lets the legal_review box through.
    (box,) = [f for f in load_schema(FORM).fields if f.pdf_field == "CheckBox7"]
    assert (box.source, box.rule, box.legal_review) == ("derived", "supp_duty_category", True)
    assert box.rule in ANSWER_BOX_RULES

    answer_petition(session, **TO_THE_CATEGORIES, duty_category=category)

    assert _printed(session)["CheckBox7"] == f"/{category}"


def test_the_amended_box_debtor_2_and_case_number_stay_unbound():
    # DigniFi files no amended form, has no Debtor 2 and knows no case number before filing.
    bound = {f.pdf_field for f in load_schema(FORM).fields}
    assert bound.isdisjoint({"CheckBox1", "Debtor2.Name", "Case number1"})


def test_every_box_the_tool_binds_is_on_the_index():
    schema = load_schema(FORM)
    index = load_index(schema.template_filename)
    for field in schema.fields:
        widgets = [w for w in index[field.pdf_field] if field.tag in (None, w.tag)]
        assert widgets, (field.pdf_field, field.tag)
        assert all(w.page == field.page for w in widgets), field.pdf_field
        if field.choices:
            states = {f"/{w.on_state}" for w in widgets}
            assert set(field.choices.values()) == states, (field.pdf_field, field.tag)


# Ruling T2-H1: Complete's gaps ask a military question exactly where the Supp prints it, so the
# gap reach (petition._SUPP_SHOWN) and the print reach (each box's conditional_on) can't drift.
SHOWN_AND_PRINTED = [
    ("disabled_veteran", "CheckBox3", "petition_debt_nature_consumer"),
    ("debts_on_duty", "CheckBox4", "supp_line_2_follow_up"),
    ("reservist", "CheckBox5", "supp_line_3"),
    ("called_to_duty", "CheckBox6", "supp_line_3_follow_up"),
    ("duty_category", "CheckBox7", "supp_categories"),
    ("duty_released_on", "Date1", "supp_date_1"),
    ("duty_ended_on", "Date2", "supp_date_2"),
]
WALK = itertools.product(
    ("consumer", "business", "neither", None),
    ("yes", "no", None),
    ("yes", "no", None),
    ("yes", "no", None),
    ("yes", "no", None),
    ("1", "2", "3", "4", "none", None),
)
KEYS = (
    "debt_nature",
    "disabled_veteran",
    "debts_on_duty",
    "reservist",
    "called_to_duty",
    "duty_category",
)
STATES = [{k: v for k, v in zip(KEYS, values, strict=True) if v is not None} for values in WALK]


def _stand_in(answers):
    return SimpleNamespace(petition_answers=SimpleNamespace(get_answers=lambda: answers))


@pytest.mark.parametrize("key,box,predicate", SHOWN_AND_PRINTED)
def test_each_military_question_prints_exactly_where_complete_asks_it(key, box, predicate):
    # The key's own box carries the predicate, so two boxes swapping theirs can't pass
    (field,) = [f for f in load_schema(FORM).fields if f.pdf_field == box]
    assert field.conditional_on == predicate
    for answers in STATES:
        shown = _SUPP_SHOWN[key](answers)
        assert PREDICATES[predicate](_stand_in(answers)) == shown, (key, answers)
