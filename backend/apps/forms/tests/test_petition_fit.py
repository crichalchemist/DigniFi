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
from apps.forms.services.answer_records import PETITION_STEP_OF_KEY
from apps.forms.services.fill_resolver import resolve_parts
from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
from apps.forms.services.petition_fit import too_long
from apps.intake.models import DebtorInfo, IntakeSession, PetitionAnswers
from apps.intake.petition import CELL_LABELS, DETAIL_TOO_LONG, petition_step_gaps

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
    label = DETAIL_TOO_LONG.format(label=CELL_LABELS[list_key][attr])
    listed = label in _too_long_lines(session)
    assert listed == (refusal is not None), (list_key, attr, position, text, refusal)
    if refusal is not None:
        assert refusal.step == "debtor_info"
    assert len(_too_long_lines(session)) == int(listed)


def test_a_row_cell_too_wide_lists_something_on_a_slot_and_on_the_sheet(session):
    # The parity above could hold with nothing listed: a district of wide capitals is refused in
    # row 1's tagged box and on the sheet's District column alike, and so it is listed.
    label = DETAIL_TOO_LONG.format(label=CELL_LABELS["prior_cases"]["district"])
    for position in (1, 4):
        rows = [{} for _ in range(position - 1)] + [{"district": "W" * 40}]
        _answer(session, {"prior_bankruptcy_answer": "yes", "prior_cases": rows})
        assert _too_long_lines(session) == [label], position
        # Each refusal is held by the form whose box refused it, so a second form that prints
        # the cell (Task 10's 103B) can never be named for Form 101's box, or the reverse.
        refused = too_long(session, ["prior_cases"])
        assert refused == {("prior_cases", "district"): frozenset({"form_101"})}, position


def test_a_row_cell_under_its_lists_no_is_not_listed(session):
    # Rows stay stored under a No and print nothing, so a line about their width would be false.
    rows = [{"district": "W" * 40}]
    _answer(session, {"prior_bankruptcy_answer": "no", "prior_cases": rows})
    assert _too_long_lines(session) == []
    _answer(session, {"prior_cases": rows})
    assert _too_long_lines(session) == []


def test_one_line_per_cell_however_many_rows_are_too_wide(session):
    rows = [{"district": "W" * 40} for _ in range(5)]
    _answer(session, {"prior_bankruptcy_answer": "yes", "prior_cases": rows})
    label = DETAIL_TOO_LONG.format(label=CELL_LABELS["prior_cases"]["district"])
    assert _too_long_lines(session) == [label]
