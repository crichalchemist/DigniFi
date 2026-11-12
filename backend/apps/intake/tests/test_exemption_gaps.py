"""
Every gap Schedule C's page leaves, in page order (3g1 §5.5, P6, P14).

Business intent: a filer is told, one sentence at a time and in the order the page asks, what
Schedule C still needs from them. No answer is guessed for them.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.services.exemption_items import exemption_items
from apps.intake import exemptions as words
from apps.intake.exemptions import exemption_gaps, ordered_claims
from apps.intake.models import AssetInfo, ExemptionAnswers, ExemptionClaim, IntakeSession

User = get_user_model()

LAWS = {"il_735_5_12_1001_c", "il_735_5_12_1001_b"}
LAW = "il_735_5_12_1001_c"
GOODS = "Bed, couch, table, kitchenware (secondhand)"


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="exemptiongaps", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def _row(session, line, description="", value="100", **details):
    row = AssetInfo.objects.create(
        session=session, ab_line=line, description=description, current_value=Decimal(value)
    )
    row.set_details(details)
    row.save()
    return row


def _car(session):
    return _row(session, "3", make="Honda", model="Civic", year="2015")


def _checking(session):
    return _row(session, "17", description="JPMorgan Chase", kind="checking")


def _claim(session, asset, **fields):
    return ExemptionClaim.objects.create(session=session, asset=asset, **fields)


def _finished(session, asset, **fields):
    values = {"law": LAW, "amount_kind": "dollars", "amount": Decimal("100.00")}
    return _claim(session, asset, **{**values, **fields})


def _answer(session, **fields):
    values = {"line_1": "state_and_federal", "line_3": "no"}
    ExemptionAnswers.objects.update_or_create(session=session, defaults={**values, **fields})


def _gaps(session):
    session = IntakeSession.objects.get(pk=session.pk)
    return exemption_gaps(session, exemption_items(session), LAWS)


def test_an_unanswered_page_asks_line_1_first(session):
    _car(session)

    gaps = _gaps(session)

    assert gaps[0] == words.EXEMPTION_GAP_LINE_1
    assert gaps[1] == words.EXEMPTION_GAP_NO_CLAIMS
    assert gaps[-1] == words.EXEMPTION_GAP_LINE_3


def test_the_gaps_come_line_1_then_each_claims_first_gap_then_line_3(session):
    car = _car(session)
    _claim(session, car)

    assert _gaps(session) == [
        words.EXEMPTION_GAP_LINE_1,
        words.EXEMPTION_GAP_LAW.format(name="Honda Civic 2015"),
        words.EXEMPTION_GAP_LINE_3,
    ]


def test_with_no_property_only_the_not_claiming_button_is_named(session):
    _answer(session)

    gaps = _gaps(session)

    assert words.EXEMPTION_GAP_NO_ITEMS in gaps
    assert words.EXEMPTION_GAP_NO_CLAIMS not in gaps


def test_not_claiming_answers_the_claims(session):
    _car(session)
    _answer(session, no_claims=True)

    assert _gaps(session) == []


def test_each_claims_first_gap_comes_in_ab_order(session):
    car = _car(session)
    checking = _checking(session)
    _claim(session, checking)
    _claim(session, car)
    _answer(session)

    gaps = _gaps(session)

    named = [g for g in gaps if g.startswith("Choose the law for")]
    assert named == ["Choose the law for Honda Civic 2015.", "Choose the law for JPMorgan Chase."]


def test_ordered_claims_puts_a_claim_with_no_live_item_last(session):
    car = _car(session)
    checking = _checking(session)
    gone = _claim(session, None)
    second = _claim(session, checking)
    first = _claim(session, car)
    session = IntakeSession.objects.get(pk=session.pk)

    ordered = ordered_claims(session.exemption_claims.all(), exemption_items(session))

    assert [c.pk for c in ordered] == [first.pk, second.pk, gone.pk]


def test_two_claims_on_one_item_keep_the_order_they_were_first_saved_whatever_order_they_come():
    # P14: claim id breaks the tie, so the order never depends on how the rows were read.
    item = SimpleNamespace(id=1)
    later = SimpleNamespace(asset_id=1, pk=8)
    earlier = SimpleNamespace(asset_id=1, pk=3)
    gone = SimpleNamespace(asset_id=None, pk=1)

    assert ordered_claims([later, gone, earlier], [item]) == [earlier, later, gone]


def test_a_claim_whose_property_left_ab_is_named_without_a_name(session):
    car = _car(session)
    _finished(session, car)
    _answer(session)
    car.delete()

    assert words.EXEMPTION_GAP_ITEM_GONE in _gaps(session)


def test_a_claim_for_a_row_of_another_intake_is_no_live_claim(session):
    other = IntakeSession.objects.create(user=session.user, district=session.district)
    foreign = _car(other)
    _car(session)
    _finished(session, foreign)
    _answer(session)

    assert words.EXEMPTION_GAP_ITEM_GONE in _gaps(session)


def test_a_law_not_in_the_list_in_force_asks_for_a_law_again(session):
    car = _car(session)
    _finished(session, car, law="il_735_5_12_1001_j")
    _answer(session)

    assert _gaps(session) == [words.EXEMPTION_GAP_LAW_CHANGED.format(name="Honda Civic 2015")]


def test_a_blank_typed_law_counts_as_no_law(session):
    car = _car(session)
    claim = _finished(session, car, law=None, other_law="   ")
    _answer(session)

    assert _gaps(session) == [words.EXEMPTION_GAP_LAW.format(name="Honda Civic 2015")]

    claim.other_law = "Demo Statute 1"
    claim.save()
    assert _gaps(session) == []


def test_a_claim_with_no_kind_of_amount_names_both_kinds(session):
    car = _car(session)
    _finished(session, car, amount_kind=None, amount=None)
    _answer(session)

    assert _gaps(session) == [words.EXEMPTION_GAP_AMOUNT_KIND.format(name="Honda Civic 2015")]


def test_dollars_with_no_amount_asks_for_it_and_a_zero_amount_is_an_amount(session):
    car = _car(session)
    claim = _finished(session, car, amount=None)
    _answer(session)

    assert _gaps(session) == [words.EXEMPTION_GAP_AMOUNT.format(name="Honda Civic 2015")]

    claim.amount = Decimal("0.00")
    claim.save()
    assert _gaps(session) == []


def test_a_name_that_does_not_fit_needs_a_shorter_description(session):
    goods = _row(session, "6", description=GOODS)
    claim = _finished(session, goods)
    _answer(session)

    assert _gaps(session) == [words.EXEMPTION_GAP_DESCRIPTION.format(name=GOODS)]

    claim.short_description = "Bed, couch, table, kitchenware"
    claim.save()
    assert _gaps(session) == []


def test_line_3_yes_asks_its_second_part_and_no_needs_none(session):
    _answer(session, no_claims=True, line_3=None)
    assert _gaps(session) == [words.EXEMPTION_GAP_LINE_3]

    _answer(session, line_3="yes")
    assert _gaps(session) == [words.EXEMPTION_GAP_LINE_3_1]

    _answer(session, line_3="yes", line_3_1="no")
    assert _gaps(session) == []

    _answer(session, line_3="no", line_3_1=None)
    assert _gaps(session) == []


def test_a_finished_page_has_no_gap(session):
    car = _car(session)
    _finished(session, car)
    _finished(session, car, law="il_735_5_12_1001_b", amount_kind="fair_market_value", amount=None)
    _answer(session)

    assert _gaps(session) == []
