"""
Review names a Form 101 answer too wide for its box exactly when Generate would refuse it
(forms step 4b-ii, Rulings PF2-1, PF2-10 a and d, PF2-4).

Business intent: Form 101's caps count characters at digit width (Ruling T4-caps), so an answer
under its cap typed in capitals or wide letters can still be too wide for its box. If Review said
"Nothing is missing." and Generate All then refused it, the fix would reopen the filer's intake.
So the too-long line on Review must be listed exactly when check() refuses the box, no sooner (a
false line about an answer that prints) and no later (a refusal Review never warned of).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services import petition_fit
from apps.forms.services.answer_records import PETITION_STEP_OF_KEY
from apps.forms.services.fill_resolver import resolve_parts
from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter, ValueTooLong
from apps.forms.services.petition_fit import too_long
from apps.intake.models import DebtorInfo, IntakeSession, PetitionAnswers
from apps.intake.petition import (
    CELL_LABELS,
    DETAIL_TOO_LONG,
    DETAIL_TOO_LONG_ROW,
    petition_step_gaps,
)

User = get_user_model()

# The answers that show each block's boxes.
GATES = {
    "mailing": {"mailing_answer": "yes"},
    "business": {"sole_proprietor_answer": "yes"},
    "hazard": {"hazard_answer": "yes"},
    "venue": {"venue_choice": "other"},
}
# The text keys steps 1 and 5 ask, each measured on Review (the 18 PF2-3 names).
MEASURED_KEYS = sorted(
    key
    for key in PetitionAnswers.TEXT_LIMITS
    if PETITION_STEP_OF_KEY.get(key) in ("debtor_info", "assets")
)
CAPITALS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="fit101", password="pass")
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
        middle_name="Q",
        last_name="Filer",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="demo@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


def _answer(session, answers):
    record, _ = PetitionAnswers.objects.get_or_create(session=session)
    record.answers = "{}"
    record.merge(answers)
    record.save()
    session.refresh_from_db()


def _refusal(session):
    """check()'s ValueTooLong for the whole Form 101 as Generate resolves it, else None."""
    try:
        PDFFormFiller().check("form_101", resolve_parts(load_schema("form_101"), session))
    except ValueTooLong as refused:
        return refused
    return None


def _too_long_lines(session):
    return [str(g) for g in petition_step_gaps(session) if "too long" in str(g)]


def _texts_at_cap(key):
    """Words at the key's cap: wide capitals, digits, the alphabet's capitals in turn, and for a
    street a long Number (PF2-10d), for the venue reason wide words that wrap."""
    cap = PetitionAnswers.TEXT_LIMITS[key]
    texts = ["W" * cap, "0" * cap, (CAPITALS * 10)[:cap], "o" * cap]
    if key.endswith("_street"):
        texts += ["1" * (cap - 3) + " St", "12 " + "W" * (cap - 3), "1" * 12 + " Main St"]
    if key == "venue_reason":
        texts.append(("WWWWWWWWW " * 20)[:cap].strip())
    return texts


PARITY_CASES = [(key, text) for key in MEASURED_KEYS for text in _texts_at_cap(key)]


def _boxes_of(key):
    """The labels of the boxes that print `key`: bound to it, or a rule built from it."""
    rules = {key}
    if key.endswith("_street"):
        rules.add(key.replace("_street", "_number"))
    return {
        f.label
        for f in load_schema("form_101").fields
        if f.binding == f"petition.{key}"
        or f.rule in rules
        or (f.rule or "").startswith(f"{key}_line_")
    }


def test_the_base_form_prints_without_refusal(session):
    # Without this, a refusal from some other box would make every parity case agree by luck.
    _answer(session, {})
    assert _refusal(session) is None


def test_the_cell_labels_are_the_records_own():
    # One public name beside TEXT_LIMITS and TEXT_LABELS, so the gaps never read the model
    # module's private copy of form_101.limits.json.
    assert CELL_LABELS is PetitionAnswers.CELL_LABELS


def test_eighteen_keys_are_measured():
    assert len(MEASURED_KEYS) == 18


@pytest.mark.parametrize("key,text", PARITY_CASES)
def test_a_text_at_its_cap_is_listed_exactly_when_check_refuses_it(session, key, text):
    assert len(text) <= PetitionAnswers.TEXT_LIMITS[key]
    _answer(session, {**GATES.get(key.partition("_")[0], {}), key: text})
    refusal = _refusal(session)
    label = PetitionAnswers.TEXT_LABELS[key]
    listed = DETAIL_TOO_LONG.format(label=label) in _too_long_lines(session)
    assert listed == (refusal is not None), (key, text, refusal)
    if refusal is not None:
        assert (refusal.step, refusal.page) == (PETITION_STEP_OF_KEY[key], None)
        assert refusal.label in _boxes_of(key)
    # Never two lines for one key.
    assert len(_too_long_lines(session)) == int(listed)


def test_capitals_at_a_cap_are_listed_and_digits_in_a_zip_or_state_are_not(session):
    # The parity above could hold with nothing ever listed; these pin that it lists something.
    for key in MEASURED_KEYS:
        label = DETAIL_TOO_LONG.format(label=PetitionAnswers.TEXT_LABELS[key])
        cap = PetitionAnswers.TEXT_LIMITS[key]
        gate = GATES.get(key.partition("_")[0], {})
        exact = "0" if key.endswith("_zip") else "W" if key.endswith("_state") else None
        _answer(session, {**gate, key: (exact or "W") * cap})
        assert (label in _too_long_lines(session)) is (exact is None), key


def test_a_street_whose_number_is_too_wide_for_the_number_box_is_listed(session):
    # PF2-10d: no cap on the Number box; the street's own detail names it instead.
    _answer(session, {"mailing_answer": "yes", "mailing_street": "1" * 20 + " Main St"})
    refusal = _refusal(session)
    assert refusal is not None and refusal.label in _boxes_of("mailing_street")
    label = DETAIL_TOO_LONG.format(label=PetitionAnswers.TEXT_LABELS["mailing_street"])
    assert _too_long_lines(session) == [label]


def test_a_zip_plus_4_with_a_hyphen_is_listed_and_refused_and_nine_digits_are_neither(session):
    # Owner ruling Q1: a ZIP+4 is nine digits with no hyphen; "60201-1234" doesn't fit at 6 pt.
    label = DETAIL_TOO_LONG.format(label=PetitionAnswers.TEXT_LABELS["mailing_zip"])
    _answer(session, {"mailing_answer": "yes", "mailing_zip": "60201-1234"})
    refusal = _refusal(session)
    assert refusal is not None and refusal.step == "debtor_info"
    assert _too_long_lines(session) == [label]
    _answer(session, {"mailing_answer": "yes", "mailing_zip": "602011234"})
    assert _refusal(session) is None
    assert _too_long_lines(session) == []


# Each list with its gate, the rows its slots hold, and the row past them on the sheet.
LISTS = {
    "other_names": ({"other_names_answer": "yes"}, 2),
    "other_business_names": ({"other_names_answer": "yes"}, 2),
    "prior_cases": ({"prior_bankruptcy_answer": "yes"}, 3),
    "pending_cases": ({"pending_case_answer": "yes"}, 2),
}
# What a row is called in its line's sentence (owner ruling Q5): line 2's are names, 9's and
# 10's are cases.
NOUNS = {"other_names": "name", "other_business_names": "name"}


def _row_line(list_key, attr, n):
    noun = NOUNS.get(list_key, "case")
    return DETAIL_TOO_LONG_ROW.format(label=CELL_LABELS[list_key][attr], noun=noun, n=n)


CELL_TEXTS = ["W" * 40, "W" * 25, "Central District of California", "12/31/2020"]
CELL_CASES = [
    (list_key, attr, position, text)
    for list_key, (_, capacity) in LISTS.items()
    for attr in CELL_LABELS[list_key]
    for position in (1, capacity, capacity + 1)
    for text in CELL_TEXTS
    if (attr == "filed_on") == (text == "12/31/2020")
]


@pytest.mark.parametrize("list_key,attr,position,text", CELL_CASES)
def test_a_row_cell_is_listed_exactly_when_its_box_or_sheet_refuses_it(
    session, list_key, attr, position, text
):
    # PF2-10a: a slot row in its own box at 6 pt, a row past the slots by the sheet's column.
    gate, _ = LISTS[list_key]
    rows = [{} for _ in range(position - 1)] + [{attr: text}]
    _answer(session, {**gate, list_key: rows})
    refusal = _refusal(session)
    listed = _row_line(list_key, attr, position) in _too_long_lines(session)
    assert listed == (refusal is not None), (list_key, attr, position, text, refusal)
    if refusal is not None:
        assert refusal.step == "debtor_info"
    assert len(_too_long_lines(session)) == int(listed)


def test_a_row_cell_too_wide_lists_something_on_a_slot_and_on_the_sheet(session):
    # The parity above could hold with nothing listed: a district of wide capitals is refused in
    # row 1's tagged box and on the sheet's District column alike, and so it is listed.
    for position in (1, 4):
        rows = [{} for _ in range(position - 1)] + [{"district": "W" * 40}]
        _answer(session, {"prior_bankruptcy_answer": "yes", "prior_cases": rows})
        assert _too_long_lines(session) == [_row_line("prior_cases", "district", position)]
        # Each refusal is held by the form whose box refused it, so a second form that prints
        # the cell (Task 10's 103B) can never be named for Form 101's box, or the reverse.
        refused = too_long(session, ["prior_cases"])
        assert refused == {("prior_cases", "district", position): frozenset({"form_101"})}


def test_a_slot_rows_too_long_line_names_its_case_in_the_owners_words(session):
    # Owner ruling Q5: with three earlier cases on the form, "line 9's district" alone doesn't
    # say which one to shorten; the sentence names the row.
    rows = [{"district": "Northern District of Illinois"}, {"district": "W" * 40}]
    _answer(session, {"prior_bankruptcy_answer": "yes", "prior_cases": rows})
    assert _too_long_lines(session) == [
        "Your answer for line 9's district, in case 2, is too long to fit on Form 101."
    ]


def test_a_sheet_rows_too_long_line_names_its_row_by_its_place_in_the_list(session):
    # The fourth case prints on the attached sheet, and the filer counts it as case 4.
    rows = [{}, {}, {}, {"case_number": "W" * 40}]
    _answer(session, {"prior_bankruptcy_answer": "yes", "prior_cases": rows})
    assert _too_long_lines(session) == [
        "Your answer for line 9's case number, in case 4, is too long to fit on Form 101."
    ]


def test_an_other_names_row_is_called_a_name(session):
    rows = [{"first": "Demo"}, {"last": "W" * 60}]
    _answer(session, {"other_names_answer": "yes", "other_names": rows})
    assert _too_long_lines(session) == [
        "Your answer for line 2's other last name, in name 2, is too long to fit on Form 101."
    ]


def test_a_sheet_label_refused_again_after_its_cell_is_blank_ends_the_measure(session, monkeypatch):
    # A refusal naming a column whose cell is already blank can't be that cell's (say the
    # filer's name in the header, under a label equal to a column's): measuring the row again
    # would be refused the same way for ever, so the measure stops there.
    calls = []

    class AlwaysRefused:
        def check(self, form_type, values):
            parts = values.get("parts", []) if isinstance(values, dict) else []
            if any(part.get("kind") == "sheet" for part in parts):
                calls.append(1)
                if len(calls) > 50:
                    raise AssertionError("looped")
                raise ValueTooLong(form_type, "Case number", {"step": "debtor_info"})

    monkeypatch.setattr(petition_fit, "PDFFormFiller", AlwaysRefused)
    rows = [{}, {}, {}, {"case_number": "W" * 40}]
    _answer(session, {"prior_bankruptcy_answer": "yes", "prior_cases": rows})

    refused = too_long(session, ["prior_cases"])

    assert refused == {("prior_cases", "case_number", 4): frozenset({"form_101"})}
    assert len(calls) == 2


def test_a_row_cell_under_its_lists_no_is_not_listed(session):
    # Rows stay stored under a No and print nothing, so a line about their width would be false.
    rows = [{"district": "W" * 40}]
    _answer(session, {"prior_bankruptcy_answer": "no", "prior_cases": rows})
    assert _too_long_lines(session) == []
    _answer(session, {"prior_cases": rows})
    assert _too_long_lines(session) == []


def test_one_line_per_row_too_wide_each_naming_its_row(session):
    # Owner ruling Q5: once per (list, cell, row), so each case the filer must shorten is named,
    # on the form's slots (1 to 3) and on the sheet (4 and 5) alike.
    rows = [{"district": "W" * 40} for _ in range(5)]
    _answer(session, {"prior_bankruptcy_answer": "yes", "prior_cases": rows})
    assert _too_long_lines(session) == [
        _row_line("prior_cases", "district", n) for n in range(1, 6)
    ]


def test_a_list_names_its_rows_in_order_then_each_rows_cells_in_the_lines_order(session):
    # Row by row, as the filer reads the cases down the form; within a row, the line's columns.
    rows = [{"case_number": "W" * 40}, {"district": "W" * 40, "case_number": "W" * 40}]
    _answer(session, {"prior_bankruptcy_answer": "yes", "prior_cases": rows})
    assert _too_long_lines(session) == [
        _row_line("prior_cases", "case_number", 1),
        _row_line("prior_cases", "district", 2),
        _row_line("prior_cases", "case_number", 2),
    ]


def test_two_cells_too_wide_in_one_sheet_row_are_both_listed(session):
    # A sheet refusal names one column; if Review stopped there, the filer would fix the debtor,
    # come back, and only then be told the case number doesn't fit either.
    rows = [{}, {}, {"debtor": "W" * 40, "case_number": "W" * 40}]
    _answer(session, {"pending_case_answer": "yes", "pending_cases": rows})
    assert _too_long_lines(session) == [
        _row_line("pending_cases", "debtor", 3),
        _row_line("pending_cases", "case_number", 3),
    ]


# A letter Form 101's font can't print: Generate refuses it in its own sentence, never as too long.
UNPRINTABLE = "北"  # a CJK letter, outside the /Helv encoding


def _letter_refused(session):
    try:
        PDFFormFiller().check("form_101", resolve_parts(load_schema("form_101"), session))
    except UnprintableLetter:
        return True
    return False


def test_an_unprintable_letter_in_a_text_leaves_review_standing_and_says_nothing_of_length(
    session,
):
    # Once the petition gaps feed Complete and every forms call, a raise here would answer the
    # filer with a server error instead of Generate's own sentence about the letter.
    _answer(session, {"mailing_answer": "yes", "mailing_city": f"Demo {UNPRINTABLE}"})
    assert _letter_refused(session)
    assert _too_long_lines(session) == []


def test_an_unprintable_letter_in_a_slot_cell_leaves_review_standing(session):
    rows = [{"district": f"Demo {UNPRINTABLE}"}]
    _answer(session, {"prior_bankruptcy_answer": "yes", "prior_cases": rows})
    assert _letter_refused(session)
    assert _too_long_lines(session) == []


def test_an_unprintable_letter_on_the_sheet_still_lets_a_wide_cell_beside_it_be_listed(session):
    # The sheet checks its columns in order: the letter in District is refused first, and the
    # Case number too wide in the same row must still be found, while District is not called long.
    rows = [{}, {}, {}, {"district": f"Demo {UNPRINTABLE}", "case_number": "W" * 40}]
    _answer(session, {"prior_bankruptcy_answer": "yes", "prior_cases": rows})
    assert _letter_refused(session)
    assert _too_long_lines(session) == [_row_line("prior_cases", "case_number", 4)]
