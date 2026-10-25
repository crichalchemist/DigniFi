"""The household's CMI and the gaps the Income step can leave (3e1 spec §5.3, §9.1).

Business intent: a filer living with their spouse is compared with the median on both incomes,
since 122A-1 adds the spouse's column under that answer; under any other answer a spouse's
stored figures stop counting but are kept. Complete and the forms refuse an Income step left
unfinished in plain words, one sentence for each gap, judging the household list against the
marriage answer only on what the filer has answered, so a half-answered list gives one
sentence, not two.
"""

from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.districts.models import District
from apps.eligibility.cmi import (
    IncomeNotSplit,
    IncomeStepGap,
    counted_spouse_income,
    household_cmi,
    household_members,
    income_step_gaps,
    spouse_monthly_income,
)
from apps.intake.models import IncomeInfo, IntakeSession, SpouseIncome
from apps.intake.tests.builders import answer_household
from apps.users.models import User

MARRIAGE = "Answer the question about marriage on the Income step."
SPOUSE_FILING = (
    "DigniFi prepares forms for one person filing alone. "
    "Check your answer about marriage on the Income step."
)
LIST = (
    "List the people in your home and the people you support on the Income step, "
    "or tell us no one does."
)
ROW = "Answer every question for each person on your household list on the Income step."
MISMATCH = (
    "Your household list and your answer about marriage don't match. "
    "Check both on the Income step."
)
INCOME_BY_SOURCE = "Enter your income by source on the Income step."
SPOUSE_INCOME = (
    "Enter your spouse's income by source on the Income step. "
    "If your spouse has no income, enter $0 in one box."
)
SPOUSE_AT_HOME = {
    "relationship": "spouse",
    "age": 45,
    "lives_with_you": True,
    "claimed_or_supported": True,
    "spouse_is_dependent": False,
}
SON = {"relationship": "son", "age": 7, "lives_with_you": True, "claimed_or_supported": True}


@pytest.fixture
def session(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    user = User.objects.create_user(username="filer", password="pw")
    return IntakeSession.objects.create(user=user, district=District.objects.get(code="ilnd"))


def _answered(session, wages="12000.00", **answers):
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal(wages))
    return answer_household(session, **answers)


def _spouse(wages):
    """As the personas type it: wages, and $0 in the other nine boxes."""
    return {
        **dict.fromkeys(SpouseIncome.SOURCE_FIELDS, Decimal("0.00")),
        "monthly_gross_wages": Decimal(wages),
    }


def _messages(session):
    return [str(gap) for gap in income_step_gaps(session)]


@pytest.mark.parametrize(
    "wages, spouse, cmi",
    [("12000.00", "1800.00", "13800.00"), ("3500.00", "1000.00", "4500.00")],
    ids=["priya", "deshawn"],
)
def test_a_filer_living_with_their_spouse_is_compared_on_both_incomes(session, wages, spouse, cmi):
    _answered(
        session,
        wages,
        marital_status="married_together",
        members=[SPOUSE_AT_HOME],
        spouse_income=_spouse(spouse),
    )
    fresh = IntakeSession.objects.get(pk=session.pk)  # read back through the encrypted columns
    assert spouse_monthly_income(fresh) == Decimal(spouse)
    assert household_cmi(fresh) == Decimal(cmi)
    assert income_step_gaps(fresh) == []


@pytest.mark.parametrize("spouse_income", [None, {}], ids=["no_spouse_row", "all_ten_boxes_empty"])
def test_a_spouse_with_no_amounts_refuses_in_the_spouses_words(session, spouse_income):
    _answered(
        session,
        marital_status="married_together",
        members=[SPOUSE_AT_HOME],
        spouse_income=spouse_income,
    )
    for work_out in (spouse_monthly_income, household_cmi):
        with pytest.raises(IncomeStepGap) as refusal:
            work_out(session)
        assert str(refusal.value) == SPOUSE_INCOME
        assert refusal.value.step == "income_info"
    assert _messages(session) == [SPOUSE_INCOME]


@pytest.mark.parametrize(
    "marital_status", ["married_separately", "not_married", "married_spouse_filing", None]
)
def test_a_spouses_figures_stop_counting_when_the_answer_moves_away_from_living_together(
    session, marital_status
):
    _answered(session, marital_status=marital_status, spouse_income=_spouse("1800.00"))
    assert counted_spouse_income(session) is None
    assert spouse_monthly_income(session) is None
    assert household_cmi(session) == Decimal("12000.00")
    assert SpouseIncome.objects.filter(session=session).exists()  # kept (§5.1)


def test_no_income_row_counts_no_spouse_and_never_raises(session):
    SpouseIncome.objects.create(session=session, monthly_gross_wages=Decimal("1800.00"))
    assert counted_spouse_income(session) is None
    assert spouse_monthly_income(session) is None
    with pytest.raises(IncomeNotSplit) as refusal:
        household_cmi(session)
    assert str(refusal.value) == INCOME_BY_SOURCE  # the filer's own refusal


@pytest.mark.parametrize("stored", ["unanswered", "an_old_tax_status"])
def test_a_bare_session_has_the_marriage_list_and_income_gaps_in_that_order(session, stored):
    if stored == "an_old_tax_status":
        # An old value written straight to the table, past the serializer.
        IncomeInfo.objects.create(session=session, marital_status="single")
    assert _messages(session) == [MARRIAGE, LIST, INCOME_BY_SOURCE]


def test_an_empty_list_counts_only_when_the_filer_said_no_one(session):
    _answered(session, members=[])
    assert household_members(session) == []
    assert _messages(session) == []

    answer_household(session, members=None)
    with pytest.raises(IncomeStepGap) as refusal:
        household_members(session)
    assert str(refusal.value) == LIST
    assert _messages(session) == [LIST]


def test_a_separated_spouse_at_home_is_no_mismatch(session):
    _answered(session, marital_status="married_separately", members=[SPOUSE_AT_HOME])
    assert _messages(session) == []


def test_a_spouse_row_under_not_married_is_a_mismatch(session):
    _answered(session, marital_status="not_married", members=[SPOUSE_AT_HOME])
    assert _messages(session) == [MISMATCH]


@pytest.mark.parametrize(
    "members",
    [[], [{**SPOUSE_AT_HOME, "lives_with_you": False}], [dict(SON) for _ in range(20)]],
    ids=["no_one", "spouse_lives_elsewhere", "twenty_rows_no_spouse"],
)
def test_living_together_with_no_spouse_at_home_is_a_mismatch(session, members):
    _answered(
        session,
        marital_status="married_together",
        members=members,
        spouse_income=_spouse("1800.00"),
    )
    assert _messages(session) == [MISMATCH]


@pytest.mark.parametrize(
    "members",
    [[{**SPOUSE_AT_HOME, "lives_with_you": None}], [{**SON, "relationship": None}]],
    ids=["spouse_at_home_unanswered", "relationship_unanswered"],
)
def test_a_spouse_row_not_yet_answered_gives_one_sentence_not_two(session, members):
    # Either row may yet be the spouse at home (P5, P15), so only the row gap is named.
    _answered(
        session,
        marital_status="married_together",
        members=members,
        spouse_income=_spouse("1800.00"),
    )
    assert _messages(session) == [ROW]


def test_a_row_with_no_relationship_living_elsewhere_cant_be_the_spouse_at_home(session):
    # It may yet be the spouse, but not the spouse at home, so the mismatch stands (P15).
    _answered(
        session,
        marital_status="married_together",
        members=[{**SON, "relationship": None, "lives_with_you": False}],
        spouse_income=_spouse("1800.00"),
    )
    assert _messages(session) == [ROW, MISMATCH]


def test_missing_amounts_for_both_the_filer_and_the_spouse_are_both_named(session):
    IncomeInfo.objects.create(session=session)
    answer_household(session, marital_status="married_together", members=[SPOUSE_AT_HOME])
    assert _messages(session) == [INCOME_BY_SOURCE, SPOUSE_INCOME]


def _nothing_stored(session):
    pass


def _spouse_filing_with_a_row_and_no_income(session):
    IncomeInfo.objects.create(session=session)
    answer_household(
        session, marital_status="married_spouse_filing", members=[{**SON, "age": None}]
    )


def _living_together_with_no_one(session):
    _answered(session, marital_status="married_together")


@pytest.mark.parametrize(
    "store, messages",
    [
        (_nothing_stored, [MARRIAGE, LIST, INCOME_BY_SOURCE]),
        (_spouse_filing_with_a_row_and_no_income, [SPOUSE_FILING, ROW, INCOME_BY_SOURCE]),
        (_living_together_with_no_one, [MISMATCH, SPOUSE_INCOME]),
    ],
    ids=["nothing_stored", "spouse_filing", "living_together"],
)
def test_every_income_step_gap_is_an_income_not_split(session, store, messages):
    store(session)
    gaps = income_step_gaps(session)
    assert [str(gap) for gap in gaps] == messages
    for gap in gaps:
        assert isinstance(gap, IncomeStepGap)
        assert isinstance(gap, IncomeNotSplit)
        assert gap.step == "income_info"


def test_the_shared_builder_makes_a_session_with_no_income_step_gap(session):
    _answered(session)
    fresh = IntakeSession.objects.get(pk=session.pk)
    assert fresh.income_info.marital_status == "not_married"
    assert fresh.household.county == "Cook"
    assert fresh.household.get_members() == []
    assert _messages(fresh) == []
