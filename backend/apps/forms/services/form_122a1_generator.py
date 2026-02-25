"""
Form 122A-1 (Chapter 7 Statement of Your Current Monthly Income) Generator.

Implements the means test for Chapter 7 eligibility per 11 U.S.C. section 707(b).
Compares Current Monthly Income (CMI) against state median income thresholds.

Logic:
  1. If >50% of debts are business debts, means test is NOT applicable
  2. Otherwise, compute CMI as the 6-month average of reported income
  3. Annualize CMI and compare against state median for household size
  4. Below median -> passes (no presumption of abuse)
  5. At or above median -> fails (Form 122A-2 required for full analysis)

Official form: b_122a-1.pdf
"""

from decimal import Decimal, ROUND_HALF_UP
from functools import reduce
from typing import Any, Dict, List

from apps.districts.models import MedianIncome
from apps.intake.models import DebtInfo, IncomeInfo, IntakeSession


# -- Constants --

ZERO = Decimal('0.00')
HUNDRED = Decimal('100')
TWELVE = Decimal('12')
SIX_MONTH_ZEROS: List[int] = [0, 0, 0, 0, 0, 0]
FIFTY_PERCENT = Decimal('50.00')

# UPL-compliant result messages (information only, never advice)
MSG_PASS_BELOW_MEDIAN = (
    "Based on the information provided, your annualized current monthly income "
    "is below the median family income for your state and household size. "
    "The means test does not indicate a presumption of abuse."
)
MSG_NOT_APPLICABLE = (
    "Based on the information provided, your debts are primarily business debts. "
    "The means test under 11 U.S.C. \u00a7 707(b) does not apply."
)
MSG_FAIL_ABOVE_MEDIAN = (
    "Based on the information provided, your annualized current monthly income "
    "exceeds the median family income. Additional analysis may be required "
    "(Form 122A-2)."
)


# -- Pure helper functions (no side effects) --

def _compute_cmi(monthly_income: List) -> Decimal:
    """
    Compute Current Monthly Income per 11 U.S.C. section 101(10A).

    CMI = sum of 6-month income history / number of months.
    Guards against empty lists; rounds to 2 decimal places.
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


def _calculate_percentage(part: Decimal, whole: Decimal) -> Decimal:
    """Calculate percentage with zero-division guard, rounded to 2 places."""
    if whole == ZERO:
        return ZERO
    return ((part / whole) * HUNDRED).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _compute_debt_classification(debts: List[DebtInfo]) -> Dict[str, Decimal]:
    """
    Compute consumer vs business debt totals and percentages.

    Considers ALL debts (secured and unsecured) for the 707(b) threshold,
    matching the official Form 122A-1 methodology.
    """
    consumer_total = reduce(
        lambda acc, d: acc + d.amount_owed,
        [d for d in debts if d.consumer_business_classification == 'consumer'],
        ZERO,
    )
    business_total = reduce(
        lambda acc, d: acc + d.amount_owed,
        [d for d in debts if d.consumer_business_classification == 'business'],
        ZERO,
    )
    grand_total = consumer_total + business_total

    return {
        'consumer_total': consumer_total,
        'business_total': business_total,
        'grand_total': grand_total,
        'consumer_percentage': _calculate_percentage(consumer_total, grand_total),
        'business_percentage': _calculate_percentage(business_total, grand_total),
    }


def _determine_household_size(session: IntakeSession) -> int:
    """
    Derive household size from IncomeInfo: 1 (debtor) + spouse if married + dependents.

    Falls back to 1 if IncomeInfo is missing.
    """
    try:
        income_info: IncomeInfo = session.income_info
        size = 1 + income_info.number_of_dependents
        if income_info.marital_status in ('married_joint', 'married_separate'):
            size += 1
        return size
    except IncomeInfo.DoesNotExist:
        return 1


def _get_median_income(session: IntakeSession, household_size: int) -> Decimal:
    """
    Retrieve the most recent median income for the session's district and household size.

    Returns ZERO if no MedianIncome record exists (graceful degradation).
    """
    median = (
        MedianIncome.objects
        .filter(district=session.district)
        .order_by('-effective_date')
        .first()
    )
    if median is None:
        return ZERO
    return median.get_median_income(household_size)


def _build_form_122a1_data(
    debt_classification: Dict[str, Decimal],
    monthly_income: List,
    household_size: int,
    median_income_annual: Decimal,
) -> Dict[str, Any]:
    """
    Build the complete Form 122A-1 output from pre-computed components.

    Pure function: deterministic output from given inputs.
    """
    consumer_pct = debt_classification['consumer_percentage']
    business_pct = debt_classification['business_percentage']
    is_applicable = consumer_pct > FIFTY_PERCENT

    cmi = _compute_cmi(monthly_income)
    annualized = (cmi * TWELVE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    median_monthly = (
        (median_income_annual / TWELVE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if median_income_annual > ZERO
        else ZERO
    )
    below_median = annualized < median_income_annual

    # Determine overall pass/fail
    if not is_applicable:
        passes = True
        result_message = MSG_NOT_APPLICABLE
    elif below_median:
        passes = True
        result_message = MSG_PASS_BELOW_MEDIAN
    else:
        passes = False
        result_message = MSG_FAIL_ABOVE_MEDIAN

    return {
        # Part 1: Means test applicability
        'is_applicable': is_applicable,
        'consumer_debt_percentage': consumer_pct,
        'business_debt_percentage': business_pct,

        # Part 2: Current Monthly Income
        'monthly_income_history': monthly_income,
        'current_monthly_income': cmi,
        'annualized_income': annualized,

        # Part 3: Median income comparison
        'household_size': household_size,
        'median_income_annual': median_income_annual,
        'median_income_monthly': median_monthly,
        'below_median': below_median,

        # Part 4: Result
        'passes_means_test': passes,
        'result_message': result_message,
    }


class Form122A1Generator:
    """
    Generate Form 122A-1: Chapter 7 Statement of Your Current Monthly Income.

    Implements the means test per 11 U.S.C. section 707(b). Compares the
    debtor's annualized CMI against the state median family income for
    the applicable household size. If CMI is below median, there is no
    presumption of abuse and the debtor passes the means test.

    Official form: b_122a-1.pdf
    """

    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Form 122A-1 data structure.

        Computes debt classification, CMI, and median comparison
        to determine means test outcome.
        """
        debts = list(self.session.debts.all())
        debt_classification = _compute_debt_classification(debts)

        try:
            income_info: IncomeInfo = self.session.income_info
            monthly_income = list(income_info.monthly_income)
        except IncomeInfo.DoesNotExist:
            monthly_income = list(SIX_MONTH_ZEROS)

        household_size = _determine_household_size(self.session)
        median_income_annual = _get_median_income(self.session, household_size)

        return _build_form_122a1_data(
            debt_classification=debt_classification,
            monthly_income=monthly_income,
            household_size=household_size,
            median_income_annual=median_income_annual,
        )

    def preview(self) -> Dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()
