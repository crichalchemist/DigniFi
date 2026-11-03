"""
Form 103B lines 1-3 print what the wizard already asked (3f spec §8.2), and line 6 the
monthly expense total.

Business intent: the court decides a fee waiver from 103B's family size and income, and the
filer swears to them. Line 1 counts the household list as § 820.20(a)(3) reads it through
count_fee_waiver_household: the filer, a spouse at home, and the dependents. Line 2 is
Schedule I line 10 for each person counted, as 103B's own line 2 says, so the two sworn forms
can't differ; the non-cash help line 10 includes is taken out again on the subtract line.
Line 3 reads the 8f answer. Nothing is typed twice. A gap on the Income step refuses the form
rather than print a guessed family of 1 (DIG-223), and a box with nothing to say prints
blank, never 0.00 (103B has no "write $0" instruction).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.cmi import HOUSEHOLD_UNANSWERED, NOW_DIFFERENT_UNANSWERED, IncomeStepGap
from apps.forms.schema import load_schema
from apps.forms.services.derivations import DERIVATIONS, RULE_FIXES
from apps.forms.services.fee_waiver import (
    FeeWaiverFamily,
    FeeWaiverIncome,
    fee_waiver_family,
    fee_waiver_income,
    fee_waiver_noncash,
)
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.household import count_fee_waiver_household, fee_waiver_spouse_counted
from apps.intake.models import DebtInfo, DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household

User = get_user_model()

CHILDREN = [
    {"relationship": "son", "age": 8, "lives_with_you": True, "claimed_or_supported": True},
    {"relationship": "daughter", "age": 5, "lives_with_you": True, "claimed_or_supported": True},
]
SPOUSE_AT_HOME = {
    "relationship": "spouse",
    "age": 44,
    "lives_with_you": True,
    "claimed_or_supported": True,
    "spouse_is_dependent": False,
}
SPOUSE_AWAY = {**SPOUSE_AT_HOME, "lives_with_you": False, "claimed_or_supported": False}
SPOUSE_WAGES = {"monthly_gross_wages": Decimal("885.00")}
LINE_1 = ("You", "Your spouse", "Your dependents", "How many dependents", "Total number of people")
LINE_2 = ("undefined_2", "undefined_3", "undefined_4", "undefined_5", "undefined_6")
LINE_3 = ("check 3", "3 type")


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="filer_103b", password="pass")
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
        first_name="Jane",
        middle_name="",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    ExpenseInfo.objects.create(
        session=session, rent_or_mortgage=Decimal("1200.00"), food_and_groceries=Decimal("400.50")
    )
    DebtInfo.objects.create(
        session=session,
        creditor_name="First Bank",
        debt_type="credit_card",
        amount_owed=Decimal("5000.00"),
    )
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3200.00"))
    answer_household(session)  # not married, no one else, every 3e2 answer No or none
    return session


def _filled(session):
    """Box → what the drawn form prints in it: the ticked states, or the text."""
    shows = {}
    for widget in _widgets(session):
        seen = shows.setdefault(widget.full_name, set())
        if widget.state:
            if widget.state != "/Off":
                seen.add(widget.state)
        elif widget.value:
            seen.add(widget.value)
    return shows


def _widgets(session):
    values = resolve(load_schema("form_103b"), session)
    return read_drawn("form_103b", PDFFormFiller().fill("form_103b", values))


def _non_cash(row, kind="SNAP (food stamps)", value=Decimal("350.00")):
    """The 8f answer Yes with non-cash help, on a filer's or a spouse's income row."""
    row.assistance_answer = "yes"
    row.noncash_assistance_kind = kind
    row.noncash_assistance_value = value
    row.save()


def _lines(session, boxes):
    filled = _filled(session)
    return [filled.get(box) for box in boxes]


@pytest.fixture
def with_children_and_snap(session):
    # $3,200 wages, $400 payroll tax, SNAP worth $350: Schedule I line 10 is 3,150.
    answer_household(session, members=CHILDREN, payroll_tax=Decimal("400.00"))
    _non_cash(session.income_info)
    return session


def test_line_1_counts_the_filer_and_the_children_they_support(with_children_and_snap):
    assert _lines(with_children_and_snap, LINE_1) == [{"/On"}, set(), {"/On"}, {"2"}, {"3"}]


def test_line_2_is_schedule_i_line_10_less_the_non_cash_help_it_includes(with_children_and_snap):
    # 3,150 less the 350 of SNAP line 10 counts: 2,800 (persona targets V8).
    assert DERIVATIONS["schedule_i_income_total_debtor1"](with_children_and_snap) == "3150.00"
    assert _lines(with_children_and_snap, LINE_2) == [
        {"3150.00"},
        set(),
        {"3150.00"},
        {"350.00"},
        {"2800.00"},
    ]


def test_line_3_names_the_non_cash_help_from_the_income_step(with_children_and_snap):
    assert _lines(with_children_and_snap, LINE_3) == [{"/yes"}, {"SNAP (food stamps)"}]


def test_the_figures_the_filing_fee_page_reads_are_the_ones_103b_prints(with_children_and_snap):
    assert fee_waiver_family(with_children_and_snap) == FeeWaiverFamily(
        total=3, spouse_counted=False, dependents=2
    )
    assert fee_waiver_income(with_children_and_snap) == FeeWaiverIncome(
        you=Decimal("3150.00"),
        spouse=None,
        subtotal=Decimal("3150.00"),
        noncash=Decimal("350.00"),
        total=Decimal("2800.00"),
    )
    assert fee_waiver_noncash(with_children_and_snap) == ("yes", "SNAP (food stamps)")


def test_the_spouse_is_counted_by_one_rule_in_the_size_and_the_checkbox():
    for answer in (*IncomeInfo.MARITAL_ANSWERS, None):
        assert fee_waiver_spouse_counted(answer) is (count_fee_waiver_household([], answer) == 2)


def test_a_filer_alone_with_no_help_prints_blank_spouse_dependents_and_subtract_lines(session):
    assert _lines(session, LINE_1) == [{"/On"}, set(), set(), set(), {"1"}]
    assert _lines(session, LINE_2) == [{"3200.00"}, set(), {"3200.00"}, set(), {"3200.00"}]
    assert _lines(session, LINE_3) == [{"/no"}, set()]


def test_a_spouse_at_home_is_counted_once_with_their_own_line_10(session):
    answer_household(
        session,
        marital_status="married_together",
        members=[SPOUSE_AT_HOME],
        spouse_income=SPOUSE_WAGES,
    )
    assert _lines(session, LINE_1) == [{"/On"}, {"/On"}, set(), set(), {"2"}]
    assert _lines(session, LINE_2) == [{"3200.00"}, {"885.00"}, {"4085.00"}, set(), {"4085.00"}]
    assert _lines(session, LINE_3) == [{"/no"}, set()]


def test_each_counted_persons_non_cash_help_is_named_and_subtracted(session):
    answer_household(
        session,
        marital_status="married_together",
        members=[SPOUSE_AT_HOME],
        spouse_income=SPOUSE_WAGES,
    )
    _non_cash(session.income_info)
    _non_cash(session.spouse_income, kind="LIHEAP energy help", value=Decimal("40.00"))
    assert _lines(session, LINE_2) == [
        {"3550.00"},
        {"925.00"},
        {"4475.00"},
        {"390.00"},
        {"4085.00"},
    ]
    assert _lines(session, LINE_3) == [
        {"/yes"},
        {"SNAP (food stamps); Spouse: LIHEAP energy help"},
    ]


def test_only_the_spouses_non_cash_help_is_named_as_the_spouses(session):
    answer_household(
        session,
        marital_status="married_together",
        members=[SPOUSE_AT_HOME],
        spouse_income=SPOUSE_WAGES,
    )
    _non_cash(session.spouse_income, kind="LIHEAP energy help", value=Decimal("40.00"))
    assert _lines(session, LINE_3) == [{"/yes"}, {"Spouse: LIHEAP energy help"}]


def test_a_spouses_non_cash_help_with_no_known_value_is_named_but_subtracts_nothing(session):
    answer_household(
        session,
        marital_status="married_together",
        members=[SPOUSE_AT_HOME],
        spouse_income=SPOUSE_WAGES,
    )
    _non_cash(session.spouse_income, kind="LIHEAP energy help", value=None)
    assert _lines(session, LINE_2) == [{"3200.00"}, {"885.00"}, {"4085.00"}, set(), {"4085.00"}]
    assert _lines(session, LINE_3) == [{"/yes"}, {"Spouse: LIHEAP energy help"}]


def test_a_spouse_living_apart_adds_nothing_to_line_1_line_2_or_line_3(session):
    answer_household(
        session,
        marital_status="married_separately",
        members=[SPOUSE_AWAY],
        spouse_income=SPOUSE_WAGES,
    )
    _non_cash(session.spouse_income)  # stored, but the spouse isn't counted
    assert _lines(session, LINE_1) == [{"/On"}, set(), set(), set(), {"1"}]
    assert _lines(session, LINE_2) == [{"3200.00"}, set(), {"3200.00"}, set(), {"3200.00"}]
    assert _lines(session, LINE_3) == [{"/no"}, set()]


def test_a_spouse_living_apart_the_filer_supports_counts_only_as_a_dependent(session):
    answer_household(
        session,
        marital_status="married_separately",
        members=[{**SPOUSE_AWAY, "spouse_is_dependent": True}],
    )
    assert _lines(session, LINE_1) == [{"/On"}, set(), {"/On"}, {"1"}, {"2"}]


def test_cash_help_is_not_subtracted_and_is_no_non_cash_help(session):
    row = session.income_info
    row.assistance_answer = "yes"
    row.cash_assistance_kind = "TANF"
    row.cash_assistance_amount = Decimal("200.00")
    row.save()
    assert _lines(session, LINE_2) == [{"3400.00"}, set(), {"3400.00"}, set(), {"3400.00"}]
    assert _lines(session, LINE_3) == [{"/no"}, set()]


def test_non_cash_help_with_no_known_value_is_named_but_subtracts_nothing(session):
    _non_cash(session.income_info, value=None)
    assert _lines(session, LINE_2) == [{"3200.00"}, set(), {"3200.00"}, set(), {"3200.00"}]
    assert _lines(session, LINE_3) == [{"/yes"}, {"SNAP (food stamps)"}]


def test_line_1_is_refused_until_the_household_list_is_answered_never_guessed_as_1(session):
    answer_household(session, members=None)
    with pytest.raises(IncomeStepGap) as refused:
        resolve(load_schema("form_103b"), session)
    assert str(refused.value) == HOUSEHOLD_UNANSWERED


@pytest.mark.parametrize(
    "rule",
    [
        "fee_waiver_family_size",
        "fee_waiver_spouse_counted",
        "fee_waiver_has_dependents",
        "fee_waiver_dependents_count",
        "fee_waiver_income_you",
        "fee_waiver_income_spouse",
        "fee_waiver_income_subtotal",
        "fee_waiver_income_noncash",
        "fee_waiver_income_total",
    ],
)
def test_any_income_step_gap_refuses_lines_1_and_2_in_its_own_words(session, rule):
    answer_household(session, income_now_different=None)
    with pytest.raises(IncomeStepGap) as refused:
        DERIVATIONS[rule](session)
    assert str(refused.value) == NOW_DIFFERENT_UNANSWERED


@pytest.mark.parametrize(
    "rule",
    [
        "fee_waiver_family_size",
        "fee_waiver_dependents_count",
        "fee_waiver_income_you",
        "fee_waiver_income_spouse",
        "fee_waiver_income_subtotal",
        "fee_waiver_income_noncash",
        "fee_waiver_income_total",
        "fee_waiver_noncash_kinds",
    ],
)
def test_a_refused_line_1_to_3_value_links_to_the_income_step(rule):
    assert RULE_FIXES[rule] == {"step": "income_info"}


def test_no_rule_reads_the_fee_waiver_pages_typed_answers():
    gone = {
        "fee_waiver_household_size",
        "fee_waiver_monthly_income",
        "fee_waiver_noncash_assistance",
        "fee_waiver_benefit_types",
    }
    assert gone & (DERIVATIONS.keys() | RULE_FIXES.keys()) == set()


def test_line_6_is_the_monthly_expense_total_schedule_j_prints(session):
    filled = _filled(session)

    # $1,200.00 rent and $400.50 food, the only expenses entered.
    assert filled.get("undefined_7") == {"1600.50"}
    assert DERIVATIONS["schedule_j_total_expenses"](session) == "1600.50"
    # Line 5 explains why installments won't work, which no page asks yet.
    assert filled.get("5 Type") == set()


def test_pages_2_and_3_are_headed_with_the_filers_name(session):
    assert {
        widget.page: widget.value
        for widget in _widgets(session)
        if widget.full_name == "Debtor.Name1"
    } == {2: "Jane Doe", 3: "Jane Doe"}


def test_part_3_stays_blank_because_schedule_a_b_is_attached(session):
    # The form says to attach Schedule A/B instead, and every packet has it (OQ-17).
    assert _filled(session).get("Amount you owe") == set()
