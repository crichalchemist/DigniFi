"""
Form 106Sum (Summary of Assets and Liabilities) Generator Service.

Aggregates data from Schedules A/B, D, E/F, I, and J into a single
statistical summary required by the bankruptcy court and trustee.

Data sources:
- Schedule A/B (assets): IntakeSession.assets → AssetInfo.current_value
- Schedule D (secured debts): IntakeSession.debts.filter(is_secured=True)
- Schedule E/F (unsecured debts): IntakeSession.debts.filter(is_secured=False)
- Schedule I (income): IntakeSession.income_info → 6-month CMI average
- Schedule J (expenses): IntakeSession.expense_info → total monthly expenses

Official form: form_b106sum.pdf
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from functools import reduce

from apps.intake.models import IntakeSession, IncomeInfo, ExpenseInfo


# Precision for financial calculations per court requirements
_TWO_PLACES = Decimal('0.01')
_ZERO = Decimal('0.00')
_SIX_MONTHS = Decimal('6')


def _sum_field(queryset, field_name: str) -> Decimal:
    """Sum a field across queryset using reduce (encrypted fields cannot use DB aggregate)."""
    return reduce(
        lambda acc, obj: acc + (getattr(obj, field_name) or _ZERO),
        queryset,
        _ZERO,
    )


def _compute_cmi(monthly_income_array: list) -> Decimal:
    """
    Compute Current Monthly Income (CMI) as 6-month average.

    Per 11 U.S.C. § 101(10A), CMI is average monthly income over
    the 6-month period preceding the filing date.
    """
    if not monthly_income_array:
        return _ZERO

    total = reduce(
        lambda acc, val: acc + Decimal(str(val)),
        monthly_income_array,
        _ZERO,
    )
    return (total / _SIX_MONTHS).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


class Form106SumGenerator:
    """
    Generate Form 106Sum (Summary of Assets and Liabilities).

    Aggregates data from Schedules A/B, C, D, E/F, I, J into a
    court-ready summary with asset totals, liability totals,
    income/expense figures, and statistical counts.

    Official form: form_b106sum.pdf
    """

    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> dict[str, Any]:
        """
        Generate Form 106Sum data aggregating all schedule sources.

        Returns dict with total_assets, total_secured_debts,
        total_unsecured_debts, total_debts, current_monthly_income,
        current_monthly_expenses, monthly_net_income,
        number_of_creditors, number_of_assets.
        """
        # Schedule A/B: Assets
        assets = self.session.assets.all()
        total_assets = _sum_field(assets, 'current_value')

        # Schedule D: Secured debts
        secured_debts = self.session.debts.filter(is_secured=True)
        total_secured = _sum_field(secured_debts, 'amount_owed')

        # Schedule E/F: Unsecured debts (priority + nonpriority)
        unsecured_debts = self.session.debts.filter(is_secured=False)
        total_unsecured = _sum_field(unsecured_debts, 'amount_owed')

        # Schedule I: Income (CMI from 6-month array)
        monthly_income = self._compute_monthly_income()

        # Schedule J: Expenses
        monthly_expenses = self._compute_monthly_expenses()

        return {
            'total_assets': total_assets,
            'total_secured_debts': total_secured,
            'total_unsecured_debts': total_unsecured,
            'total_debts': total_secured + total_unsecured,
            'current_monthly_income': monthly_income,
            'current_monthly_expenses': monthly_expenses,
            'monthly_net_income': monthly_income - monthly_expenses,
            'number_of_creditors': secured_debts.count() + unsecured_debts.count(),
            'number_of_assets': assets.count(),
        }

    def preview(self) -> dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()

    def _compute_monthly_income(self) -> Decimal:
        """Extract monthly income from IncomeInfo's 6-month array as CMI."""
        try:
            income_info = self.session.income_info
        except IncomeInfo.DoesNotExist:
            return _ZERO

        monthly_income_array = getattr(income_info, 'monthly_income', None)
        if monthly_income_array is None:
            return _ZERO

        return _compute_cmi(monthly_income_array)

    def _compute_monthly_expenses(self) -> Decimal:
        """Extract total monthly expenses from ExpenseInfo."""
        try:
            expense_info = self.session.expense_info
        except ExpenseInfo.DoesNotExist:
            return _ZERO

        return Decimal(str(expense_info.calculate_total_monthly_expenses()))
