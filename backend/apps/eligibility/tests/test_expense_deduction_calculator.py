"""Tests for ExpenseDeductionCalculator."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.services.expense_deduction_calculator import ExpenseDeductionCalculator
from apps.intake.models import DebtInfo, ExpenseInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session_with_expenses(db):
    user = User.objects.create_user(username="deductcalc", password="pass")
    district = District.objects.create(
        code="ILND",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    ExpenseInfo.objects.create(
        session=session,
        rent_or_mortgage=Decimal("1200"),
        utilities=Decimal("200"),
        food_and_groceries=Decimal("500"),
        vehicle_payment=Decimal("400"),
    )
    DebtInfo.objects.create(
        session=session,
        creditor_name="IRS",
        amount_owed=Decimal("5000"),
        is_secured=False,
        is_priority=True,
        debt_type="taxes",
        monthly_payment=Decimal("200"),
    )
    return session


@pytest.mark.django_db
class TestExpenseDeductionCalculator:
    def test_calculator_returns_allowable_expenses(self, session_with_expenses):
        calc = ExpenseDeductionCalculator(session_with_expenses)
        result = calc.calculate()
        assert result.allowable_expenses > Decimal("0")
        assert result.disposable_income is not None

    def test_calculator_uses_lesser_of_actual_vs_standard(self, session_with_expenses):
        calc = ExpenseDeductionCalculator(session_with_expenses)
        result = calc.calculate()
        # Food actual ($500) vs national standard for size 1 ($713)
        assert result.national_food_allowance == Decimal("500.00")

    def test_calculator_includes_priority_debts(self, session_with_expenses):
        calc = ExpenseDeductionCalculator(session_with_expenses)
        result = calc.calculate()
        assert result.priority_debts_monthly > Decimal("0")

    def test_empty_session(self, db):
        user = User.objects.create_user(username="emptycalc", password="pass")
        district = District.objects.create(
            code="ILND",
            name="Northern District of Illinois",
            state="IL",
            court_name="U.S. Bankruptcy Court",
            filing_fee_chapter_7=Decimal("338"),
        )
        session = IntakeSession.objects.create(user=user, district=district)
        calc = ExpenseDeductionCalculator(session)
        result = calc.calculate()
        assert result.allowable_expenses >= Decimal("0")
        assert result.disposable_income >= Decimal("0")
