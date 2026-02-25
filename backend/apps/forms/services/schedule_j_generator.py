"""
Schedule J (Expenses) Generator Service.

Generates Official Bankruptcy Form 106J: Your Expenses.

Lists all monthly living expenses and calculates net monthly income
(Schedule I income minus Schedule J expenses). A negative net indicates
a monthly deficit -- common for filers with $0 income.

Official form: form_b106j.pdf
"""

from decimal import Decimal, ROUND_HALF_UP
from functools import reduce
from typing import Any, Dict, Sequence

from apps.intake.models import ExpenseInfo, IntakeSession


# -- Named constants --

ZERO = Decimal('0.00')

EXPENSE_FIELDS: tuple[str, ...] = (
    'rent_or_mortgage',
    'utilities',
    'home_maintenance',
    'vehicle_payment',
    'vehicle_insurance',
    'vehicle_maintenance',
    'food_and_groceries',
    'clothing',
    'medical_expenses',
    'childcare',
    'child_support_paid',
    'insurance_not_deducted',
    'other_expenses',
)

HOUSING_FIELDS = ('rent_or_mortgage', 'utilities', 'home_maintenance')
TRANSPORTATION_FIELDS = ('vehicle_payment', 'vehicle_insurance', 'vehicle_maintenance')
LIVING_FIELDS = ('food_and_groceries', 'clothing', 'medical_expenses')
OTHER_FIELDS = ('childcare', 'child_support_paid', 'insurance_not_deducted', 'other_expenses')


# -- Pure helper functions (no side effects) --

def _extract_expense_values(expense_info: ExpenseInfo) -> Dict[str, Decimal]:
    """Extract all expense field values as a field_name -> Decimal mapping."""
    return {
        field: Decimal(str(getattr(expense_info, field)))
        for field in EXPENSE_FIELDS
    }


def _sum_fields(values: Dict[str, Decimal], fields: Sequence[str]) -> Decimal:
    """Sum specific fields from the values dict."""
    return reduce(
        lambda acc, field: acc + values.get(field, ZERO),
        fields,
        ZERO,
    )


def _calculate_cmi(monthly_income_array: list) -> Decimal:
    """
    Calculate Current Monthly Income from 6-month income array.

    CMI = sum(monthly_income) / len(monthly_income), rounded to cents.
    Returns ZERO when array is empty or missing.
    """
    if not monthly_income_array:
        return ZERO
    total = reduce(
        lambda acc, val: acc + Decimal(str(val)),
        monthly_income_array,
        ZERO,
    )
    return (total / len(monthly_income_array)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP,
    )


def _build_empty_expenses() -> Dict[str, Decimal]:
    """Return zeroed-out expense dict for sessions without ExpenseInfo."""
    return {field: ZERO for field in EXPENSE_FIELDS}


def _build_schedule_j_data(
    expense_values: Dict[str, Decimal],
    total_income: Decimal,
) -> Dict[str, Any]:
    """
    Assemble the complete Schedule J output from expense values and income.

    Net monthly income can be negative (deficit), which is typical for
    low-income pro se filers -- this is expected behavior, not an error.
    """
    total_expenses = _sum_fields(expense_values, EXPENSE_FIELDS)
    net_monthly_income = total_income - total_expenses

    return {
        # Individual expense lines
        **expense_values,

        # Totals
        'total_expenses': total_expenses,
        'total_income': total_income,
        'net_monthly_income': net_monthly_income,
    }


class ScheduleJGenerator:
    """
    Generate Schedule J (Your Expenses).

    Maps ExpenseInfo model fields to Official Form 106J and calculates
    net monthly income (Schedule I income - Schedule J expenses).

    Official form: form_b106j.pdf
    """

    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def _get_expense_values(self) -> Dict[str, Decimal]:
        """Safely extract expense values, defaulting to zeros if missing."""
        try:
            expense_info = self.session.expense_info
            return _extract_expense_values(expense_info)
        except ExpenseInfo.DoesNotExist:
            return _build_empty_expenses()

    def _get_total_income(self) -> Decimal:
        """
        Retrieve CMI from IncomeInfo's 6-month array.

        Returns ZERO when IncomeInfo is absent or income array is empty.
        """
        try:
            income_info = self.session.income_info
            return _calculate_cmi(income_info.monthly_income)
        except Exception:
            return ZERO

    def generate(self) -> Dict[str, Any]:
        """
        Generate Schedule J data structure.

        Reads expense fields from ExpenseInfo and income from IncomeInfo,
        then calculates net monthly income (can be negative for deficit).
        """
        expense_values = self._get_expense_values()
        total_income = self._get_total_income()
        return _build_schedule_j_data(expense_values, total_income)

    def preview(self) -> Dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()
