"""What Complete and the forms refuse on the Assets step (3b spec §7).

Business intent: a filer is never sent to court with a Schedule A/B that says nothing about a
line, says Yes with nothing under it, or prints a "0%" share the filer never gave. A filer with
no property who answered No to every line has finished the step. A value the filer doesn't know,
or typed as $0, is an answer; only a blank is not.
"""

from decimal import Decimal

import pytest

from apps.districts.models import District
from apps.intake.asset_lines import LINE_BY_KEY, asset_step_gaps
from apps.intake.models import AssetInfo, AssetLineAnswers, IntakeSession
from apps.intake.tests.builders import answer_asset_lines
from apps.users.models import User


@pytest.fixture
def session(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    return IntakeSession.objects.create(user=user, district=district)


def _gaps(session) -> list[str]:
    return [str(gap) for gap in asset_step_gaps(IntakeSession.objects.get(pk=session.pk))]


def _row(session, line, description="", value="100.00", entire=None, **details):
    row = AssetInfo(
        session=session,
        ab_line=line,
        description=description,
        current_value=None if value is None else Decimal(value),
        entire_value=None if entire is None else Decimal(entire),
    )
    row.set_details(details)
    row.save()
    return row


def _answer(session, *yes):
    """Yes on the named lines, No on every other line shown."""
    answer_asset_lines(session, yes)


def test_an_old_row_is_refused_by_its_description(session):
    _answer(session)
    _row(session, None, "Grandma's ring")

    assert _gaps(session) == ['Pick a line on the Assets step for "Grandma\'s ring".']


def test_an_unanswered_shown_line_is_refused(session):
    AssetLineAnswers.objects.create(session=session, answers='{"1": "no"}')

    gaps = _gaps(session)

    assert gaps[0] == "Line 3 on the Assets step needs a Yes or No."
    assert len(gaps) == 34


def test_a_session_with_no_answers_has_every_shown_line_unanswered(session):
    assert len(_gaps(session)) == 35


def test_a_hidden_line_needs_no_answer(session):
    # Lines 38-44 and 47-51 sit under gates answered No; a filer with no property is finished.
    _answer(session)

    assert _gaps(session) == []


def test_yes_with_no_row_is_refused(session):
    _answer(session, "7")

    assert _gaps(session) == ["Line 7 says Yes. Add what you have, or change it to No."]


def test_no_with_a_row_is_refused(session):
    _answer(session)
    _row(session, "7", "Laptop")

    assert _gaps(session) == [
        "Line 7 says No, but it still lists something. Remove it, or change the answer to Yes."
    ]


def test_a_row_under_a_gate_answered_no_is_refused(session):
    _answer(session)
    _row(session, "38", "Pallets")

    assert _gaps(session) == [
        "Line 38 is under line 37, which isn't answered Yes. "
        "Remove what line 38 lists, or answer line 37 Yes."
    ]


def test_a_row_under_an_unanswered_gate_names_the_gate_not_a_no(session):
    # The filer cannot reach line 38 to change its answer; the sentence points at line 37.
    AssetLineAnswers.objects.create(session=session, answers="{}")
    _row(session, "47", "Pallets")

    assert (
        "Line 47 is under line 46, which isn't answered Yes. "
        "Remove what line 47 lists, or answer line 46 Yes."
    ) in _gaps(session)


def test_line_43_yes_with_no_value_is_refused_until_the_value_or_its_flag(session):
    # A sworn Yes must not print with a blank amount nobody marked unknown.
    _answer(session, "37", "43")
    row = _row(session, "43", "Names and SSNs", None, has_personal_info=True)

    assert _gaps(session) == ['Line 43 needs more about "Names and SSNs" on the Assets step.']

    row.set_details({"has_personal_info": True, "value_unknown": True})
    row.save()

    assert _gaps(session) == []


def test_yes_to_a_gate_with_every_line_under_it_no_is_refused(session):
    _answer(session, "37")

    assert _gaps(session) == [
        "Line 37 says Yes, but every line under it says No. Change one of them."
    ]


def test_a_gate_with_one_line_under_it_yes_is_finished(session):
    _answer(session, "37", "38")
    _row(session, "38", "Pallets")

    assert _gaps(session) == []


@pytest.mark.parametrize("gate", ["37", "46"])
def test_a_row_on_a_gate_is_refused_in_the_gates_own_words(session, gate):
    # A gate only asks Yes or No; the API lets a row through, so Complete names it.
    under = next(line.key for line in LINE_BY_KEY.values() if line.gate == gate)
    _answer(session, gate, under)
    _row(session, under, "Pallets")
    _row(session, gate, "Stray row")

    assert _gaps(session) == [f"Line {gate} takes no items. Remove what it lists."]


COMPLETE_PLACE = {"street": "12 Elm St", "property_kinds": ["condo"], "who": "only_you"}

INCOMPLETE = [
    # line, details, description, value, entire
    ("1", {**COMPLETE_PLACE, "street": " "}, "", "1.00", "1.00"),
    ("1", {**COMPLETE_PLACE, "property_kinds": []}, "", "1.00", "1.00"),
    ("1", {**COMPLETE_PLACE, "property_kinds": ["other"]}, "", "1.00", "1.00"),
    ("1", {**COMPLETE_PLACE, "who": None}, "", "1.00", "1.00"),
    ("1", COMPLETE_PLACE, "", None, "1.00"),
    ("1", COMPLETE_PLACE, "", "1.00", None),
    ("3", {"who": "only_you"}, "", "1.00", "1.00"),
    ("3", {"make": "Honda"}, "", "1.00", "1.00"),
    ("3", {"make": "Honda", "who": "only_you"}, "", "1.00", None),
    ("4", {"make": "Trailer", "who": "only_you"}, "", None, "1.00"),
    ("6", {}, "", "5.00", None),
    ("6", {}, "Sofa", None, None),
    ("16", {}, "", None, None),
    ("17", {}, "Chase", "5.00", None),
    ("17", {"kind": "checking"}, "", "5.00", None),
    ("28", {}, "Refund", "5.00", None),
    ("53", {}, "", "5.00", None),
    ("19", {}, "Acme Co", "5.00", None),
    ("19", {"percent": "50"}, "", "5.00", None),
    ("31", {}, "", "5.00", None),
    ("43", {}, "", "5.00", None),
    ("43", {"has_personal_info": True}, "", "5.00", None),
    ("43", {"has_personal_info": False}, "", None, None),
    ("43", {"has_personal_info": True}, "Names and SSNs", None, None),
]


@pytest.mark.parametrize("line, details, description, value, entire", INCOMPLETE)
def test_a_row_missing_what_its_shape_requires_is_refused(
    session, line, details, description, value, entire
):
    gate = LINE_BY_KEY[line].gate
    _answer(session, line, *([gate] if gate else []))
    _row(session, line, description, value, entire, **details)
    street = details.get("street", "").strip()
    name = description or street or details.get("make") or "one item"

    assert _gaps(session) == [f'Line {line} needs more about "{name}" on the Assets step.']


def test_an_old_row_with_no_description_still_gets_a_name_the_filer_can_read(session):
    # A sentence ending in for "" tells the filer nothing about which row it means.
    _answer(session)
    _row(session, None, "   ")

    assert _gaps(session) == ['Pick a line on the Assets step for "one item".']


def test_a_place_with_no_description_is_named_by_its_street(session):
    # Line 1 has no description box, so the street is the only thing the filer typed to know it by.
    _answer(session, "1")
    _row(session, "1", "", "1.00", None, **COMPLETE_PLACE)

    assert _gaps(session) == ['Line 1 needs more about "12 Elm St" on the Assets step.']


def test_insurance_needs_no_beneficiary(session):
    # The step marks the beneficiary optional, so Complete must not hold a filer back over it.
    _answer(session, "31")
    _row(session, "31", "Millbrook Mutual Life", "0.00")

    assert _gaps(session) == []


def test_a_no_to_line_43_needs_its_value_but_no_describe(session):
    # The form's Describe box sits under line 43's Yes; its amount is asked either way.
    _answer(session, "37", "43")
    _row(session, "43", "", "5.00", None, has_personal_info=False)

    assert _gaps(session) == []


def test_a_row_on_a_line_answered_no_is_named_once_not_also_as_unfinished(session):
    # The fix is to remove it or change the answer, so what the row lacks is no use to the filer.
    _answer(session)
    _row(session, "7", "", None)

    assert _gaps(session) == [
        "Line 7 says No, but it still lists something. Remove it, or change the answer to Yes."
    ]


def test_an_unknown_value_counts_as_given(session):
    _answer(session, "6")
    _row(session, "6", "Sofa", None, value_unknown=True)

    assert _gaps(session) == []


def test_an_unknown_entire_value_counts_as_given(session):
    _answer(session, "3")
    _row(session, "3", "", "1.00", None, make="Honda", who="only_you", entire_unknown=True)

    assert _gaps(session) == []


def test_zero_counts_as_given(session):
    # A leased car typed as $0 and $0 is answered, not blank.
    _answer(session, "3")
    _row(session, "3", "", "0.00", "0.00", make="Corolla", who="only_you")

    assert _gaps(session) == []


def test_cash_needs_no_text(session):
    _answer(session, "16")
    _row(session, "16", "", "40.00")

    assert _gaps(session) == []


def test_a_share_is_required_because_a_blank_prints_the_template_s_zero_percent(session):
    _answer(session, "19")
    _row(session, "19", "Acme Co", "5.00")

    assert _gaps(session) == ['Line 19 needs more about "Acme Co" on the Assets step.']

    row = AssetInfo.objects.get()
    row.set_details({"percent": "0"})
    row.save()

    assert _gaps(session) == []


def test_a_vehicle_needs_no_model_year_or_mileage(session):
    _answer(session, "3")
    _row(session, "3", "", "1.00", "1.00", make="Trailer", who="with_someone")

    assert _gaps(session) == []


def test_gaps_come_in_the_form_s_order(session):
    _answer(session, "6", "9")
    _row(session, "9", "", "1.00")
    _row(session, "7", "Laptop")
    _row(session, None, "Old ring")

    assert _gaps(session) == [
        'Pick a line on the Assets step for "Old ring".',
        "Line 6 says Yes. Add what you have, or change it to No.",
        "Line 7 says No, but it still lists something. Remove it, or change the answer to Yes.",
        'Line 9 needs more about "one item" on the Assets step.',
    ]
