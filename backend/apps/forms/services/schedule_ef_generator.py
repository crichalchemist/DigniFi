"""
Schedule E/F (Creditors With Unsecured Claims) Generator Service.

Generates Official Bankruptcy Form 106E/F: Creditors Who Have Unsecured Claims.

Part 1: Priority unsecured claims (taxes, child support, wages owed)
Part 2: Nonpriority unsecured claims (credit cards, medical bills, etc.)

The consumer vs business debt percentage determines whether the means test
applies under 11 U.S.C. section 707(b):
  - >50% consumer debts -> means test applies
  - >50% business debts -> means test does NOT apply

Official form: form_b106ef.pdf
"""

from decimal import Decimal, ROUND_HALF_UP
from functools import reduce
from typing import Any, Dict, List

from apps.intake.models import DebtInfo, IntakeSession


# -- Pure helper functions (no side effects) --

def _format_creditor(debt: DebtInfo) -> Dict[str, Any]:
    """Transform a DebtInfo record into the Schedule E/F creditor format."""
    return {
        'creditor_name': debt.creditor_name,
        'creditor_address': getattr(debt, 'creditor_address', ''),
        'account_number': debt.account_number or '',
        'amount_owed': debt.amount_owed,
        'date_incurred': str(debt.date_incurred) if debt.date_incurred else '',
        'debt_type': debt.consumer_business_classification,
        'contingent': debt.is_contingent,
        'unliquidated': debt.is_unliquidated,
        'disputed': debt.is_disputed,
    }


def _sum_amounts(debts: List[DebtInfo]) -> Decimal:
    """Sum amount_owed across debts using functools.reduce."""
    return reduce(
        lambda acc, d: acc + d.amount_owed,
        debts,
        Decimal('0.00'),
    )


def _calculate_percentage(part: Decimal, whole: Decimal) -> Decimal:
    """Calculate percentage with zero-division guard, rounded to 2 decimal places."""
    if whole == Decimal('0.00'):
        return Decimal('0.00')
    return ((part / whole) * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _partition(predicate, items: list) -> tuple[list, list]:
    """Split items into (true_group, false_group) based on predicate."""
    true_group = [item for item in items if predicate(item)]
    false_group = [item for item in items if not predicate(item)]
    return true_group, false_group


def _build_schedule_ef_data(
    priority_debts: List[DebtInfo],
    nonpriority_debts: List[DebtInfo],
) -> Dict[str, Any]:
    """
    Build the complete Schedule E/F data structure from pre-partitioned debts.

    Consumer vs business percentages are calculated from ALL unsecured debts
    (both priority and nonpriority), matching the official form's methodology.
    """
    priority_creditors = [_format_creditor(d) for d in priority_debts]
    nonpriority_creditors = [_format_creditor(d) for d in nonpriority_debts]

    total_priority = _sum_amounts(priority_debts)
    total_nonpriority = _sum_amounts(nonpriority_debts)
    total_unsecured = total_priority + total_nonpriority

    all_unsecured = priority_debts + nonpriority_debts
    consumer_debts, business_debts = _partition(
        lambda d: d.consumer_business_classification == 'consumer',
        all_unsecured,
    )
    consumer_total = _sum_amounts(consumer_debts)
    business_total = _sum_amounts(business_debts)

    return {
        # Part 1: Priority unsecured
        'priority_creditors': priority_creditors,
        'total_priority_claims': total_priority,

        # Part 2: Nonpriority unsecured
        'nonpriority_creditors': nonpriority_creditors,
        'total_nonpriority_claims': total_nonpriority,

        # Consumer vs Business breakdown (11 U.S.C. section 707(b))
        'consumer_debt_total': consumer_total,
        'business_debt_total': business_total,
        'consumer_debt_percentage': _calculate_percentage(consumer_total, total_unsecured),
        'business_debt_percentage': _calculate_percentage(business_total, total_unsecured),

        # Totals
        'total_unsecured_claims': total_unsecured,
        'number_of_unsecured_claims': len(all_unsecured),
    }


class ScheduleEFGenerator:
    """
    Generate Schedule E/F (Creditors With Unsecured Claims).

    Part 1: Priority unsecured claims
    Part 2: Nonpriority unsecured claims

    Official form: form_b106ef.pdf
    """

    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Schedule E/F data structure.

        Filters unsecured debts, partitions by priority, and calculates
        consumer vs business debt percentages for means test applicability.
        """
        unsecured_debts = list(
            self.session.debts.filter(is_secured=False)
        )

        priority_debts, nonpriority_debts = _partition(
            lambda d: d.is_priority,
            unsecured_debts,
        )

        return _build_schedule_ef_data(priority_debts, nonpriority_debts)

    def preview(self) -> Dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()
