"""
Schedule I (Current Income of Individual Debtor(s)) Generator Service.

Generates Official Bankruptcy Form 106I: Your Income, listing all income
sources for the debtor. Handles the special $0 income case common among
Chapter 7 filers who have lost employment.

Current Monthly Income (CMI) is defined by 11 U.S.C. section 101(10A)
as the average monthly income received during the 6-month period
preceding the filing date.

Official form: form_b106i.pdf
"""

from decimal import Decimal, ROUND_HALF_UP
from functools import reduce
from typing import Any, Dict, List

from apps.intake.models import IncomeInfo, IntakeSession


# -- Constants --

ZERO = Decimal('0.00')
SIX_MONTH_ZEROS: List[int] = [0, 0, 0, 0, 0, 0]
DEFAULT_MARITAL_STATUS = 'single'
DEFAULT_DEPENDENTS = 0


# -- Pure helper functions (no side effects) --

def _compute_cmi(monthly_income: List) -> Decimal:
    """
    Compute Current Monthly Income per 11 U.S.C. section 101(10A).

    CMI = sum of 6-month income history / number of months.
    Returns Decimal rounded to 2 places; guards against empty lists.
    """
    if not monthly_income:
        return ZERO

    total = reduce(
        lambda acc, amount: acc + Decimal(str(amount)),
        monthly_income,
        ZERO,
    )
    month_count = Decimal(str(len(monthly_income)))
    return (total / month_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _extract_income_data(session: IntakeSession) -> Dict[str, Any]:
    """
    Extract income-related fields from session, handling missing IncomeInfo.

    Returns a dict of raw values suitable for building the schedule data.
    """
    try:
        income_info: IncomeInfo = session.income_info
        return {
            'marital_status': income_info.marital_status,
            'number_of_dependents': income_info.number_of_dependents,
            'monthly_income': list(income_info.monthly_income),
        }
    except IncomeInfo.DoesNotExist:
        return {
            'marital_status': DEFAULT_MARITAL_STATUS,
            'number_of_dependents': DEFAULT_DEPENDENTS,
            'monthly_income': list(SIX_MONTH_ZEROS),
        }


def _build_schedule_i_data(
    marital_status: str,
    number_of_dependents: int,
    monthly_income: List,
) -> Dict[str, Any]:
    """
    Build the complete Schedule I data structure from extracted values.

    Pure function: deterministic output from given inputs.
    """
    cmi = _compute_cmi(monthly_income)
    has_no_income = cmi == ZERO

    return {
        'marital_status': marital_status,
        'number_of_dependents': number_of_dependents,
        'monthly_income_history': monthly_income,
        'current_monthly_income': cmi,
        'has_no_income': has_no_income,
        'total_monthly_income': cmi,
    }


class ScheduleIGenerator:
    """
    Generate Schedule I (Current Income of Individual Debtor(s)).

    Lists all income sources and computes Current Monthly Income (CMI)
    from the 6-month income history. Handles the $0 income case that
    is common among unemployed Chapter 7 filers.

    Official form: form_b106i.pdf
    """

    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Schedule I data structure.

        Extracts income data from the session's IncomeInfo, computes CMI
        as the average of the 6-month income array, and flags the $0
        income case for downstream form population.
        """
        raw = _extract_income_data(self.session)
        return _build_schedule_i_data(**raw)

    def preview(self) -> Dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()
