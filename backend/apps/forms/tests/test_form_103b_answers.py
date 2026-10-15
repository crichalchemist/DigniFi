"""
Form 103B prints the fee-waiver page's answers on the lines that ask them (step 2 spec §3
Q10 and Q11, §6.4, Appendix A.2).

Business intent: the fee-waiver application is sworn, and the court decides the waiver from
it. Line 2 is the filer's take-home pay, which they typed on the fee-waiver page; line 3 is
their own Yes or No about non-cash help, with what kind; line 6 is the same monthly expense
total as Schedule J line 22c. A figure or answer the filer never gave prints blank, never
0.00 or a No, and the boxes the old bindings misused (line 4's and line 5's explanations,
Part 3's other assets) stay blank.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.derivations import DERIVATIONS
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_widgets
from apps.intake.models import (
    DebtInfo,
    DebtorInfo,
    ExpenseInfo,
    FeeWaiverApplication,
    IntakeSession,
)

User = get_user_model()

# Line 2's boxes the take-home figure prints in: You, Subtotal and the family's net income.
TAKE_HOME_BOXES = ("undefined_2", "undefined_4", "undefined_6")


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
    return session


def _apply(session, **answers):
    """The filer's application. The old columns hold figures no box may print any more."""
    page_answers = {
        "monthly_take_home_pay": Decimal("2800.00"),
        "receives_noncash_assistance": False,
        "benefit_types": [],
        **answers,
    }
    return FeeWaiverApplication.objects.create(
        session=session,
        household_size=2,
        monthly_income=Decimal("3200.00"),
        monthly_expenses=Decimal("2560.00"),
        **page_answers,
    )


def _filled(session):
    """Box → what a viewer sees in it once the form is filled: the ticked states, or the text."""
    shows = {}
    for widget in _widgets(session):
        seen = shows.setdefault(widget.full_name, set())
        if widget.state is not None:
            if widget.state != "/Off":
                seen.add(widget.state)
        elif widget.value:
            seen.add(widget.value)
    return shows


def _widgets(session):
    values = resolve(load_schema("form_103b"), session)
    return read_widgets(PDFFormFiller().fill("form_103b", values))


def test_line_2_prints_take_home_pay_for_you_the_subtotal_and_the_family_total(session):
    _apply(session)
    filled = _filled(session)

    assert [filled.get(box) for box in TAKE_HOME_BOXES] == [{"2800.00"}] * 3
    # Nobody else's income and no non-cash subtraction is asked, and line 4 is an explanation.
    assert [filled.get(box) for box in ("undefined_3", "undefined_5", "4 type")] == [set()] * 3


def test_take_home_pay_never_given_prints_blank_not_zero(session):
    # An application saved before the page asked take-home pay.
    _apply(session, monthly_take_home_pay=None)
    filled = _filled(session)

    assert [filled.get(box) for box in TAKE_HOME_BOXES] == [set()] * 3


def test_take_home_pay_typed_as_zero_prints_zero(session):
    _apply(session, monthly_take_home_pay=Decimal("0.00"))
    filled = _filled(session)

    assert [filled.get(box) for box in TAKE_HOME_BOXES] == [{"0.00"}] * 3


@pytest.mark.parametrize(
    ("answer", "kinds", "ticked", "what_kind"),
    [
        (
            True,
            ["SNAP (food stamps)", "Housing subsidy"],
            {"/yes"},
            {"SNAP (food stamps), Housing subsidy"},
        ),
        # A kind stored beside a sworn No never prints under it.
        (False, ["SNAP (food stamps)"], {"/no"}, set()),
        # Saved before the page asked: no sworn answer either way, so no kind prints either.
        (None, ["SNAP (food stamps)"], set(), set()),
    ],
)
def test_line_3_prints_the_filers_own_answer_about_non_cash_help(
    session, answer, kinds, ticked, what_kind
):
    _apply(session, receives_noncash_assistance=answer, benefit_types=kinds)
    filled = _filled(session)

    assert (filled.get("check 3"), filled.get("3 type")) == (ticked, what_kind)


def test_line_6_is_the_monthly_expense_total_schedule_j_prints(session):
    _apply(session)
    filled = _filled(session)

    # $1,200.00 rent and $400.50 food, the only expenses entered.
    assert filled.get("undefined_7") == {"1600.50"}
    assert DERIVATIONS["schedule_j_total_expenses"](session) == "1600.50"
    # Line 5 explains why installments won't work, which no page asks yet.
    assert filled.get("5 Type") == set()


def test_line_1_counts_the_filer(session):
    _apply(session)

    assert _filled(session).get("You") == {"/On"}


def test_pages_2_and_3_are_headed_with_the_filers_name(session):
    _apply(session)

    assert {
        widget.page: widget.value
        for widget in _widgets(session)
        if widget.full_name == "Debtor.Name1"
    } == {2: "Jane Doe", 3: "Jane Doe"}


def test_part_3_stays_blank_because_schedule_a_b_is_attached(session):
    # The form says to attach Schedule A/B instead, and every packet has it (OQ-17).
    _apply(session)

    assert _filled(session).get("Amount you owe") == set()
