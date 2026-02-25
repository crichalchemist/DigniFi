"""
Form 103B Generator Service.

Generates Official Bankruptcy Form 103B: Application to Have the
Chapter 7 Filing Fee Waived. This is the fee waiver application
filed under 28 U.S.C. § 1930(f).

Qualification paths:
  1. Income below 150% of federal poverty guidelines → qualifies
  2. Receives means-tested public benefits (SSI, SNAP, TANF) → qualifies
  3. Cannot pay in full or installments → may qualify (court discretion)

Official form: form_b103b.pdf
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from functools import reduce
from typing import Any

from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    FeeWaiverApplication,
    IntakeSession,
)


# -- Constants --

_ZERO = Decimal('0.00')
_TWO_PLACES = Decimal('0.01')
BANK_ACCOUNT_TYPE = 'bank_account'

# Qualification basis identifiers
BASIS_INCOME = 'income'
BASIS_BENEFITS = 'benefits'
BASIS_NONE = 'none'

# UPL-compliant result messages (information, never advice)
MSG_QUALIFIES_INCOME = (
    "Based on the information provided, your monthly income is below "
    "150% of the federal poverty guidelines for your household size. "
    "You may be eligible to have the filing fee waived."
)
MSG_QUALIFIES_BENEFITS = (
    "Based on the information provided, you receive means-tested "
    "government assistance. You may be eligible to have the filing "
    "fee waived."
)
MSG_DOES_NOT_QUALIFY = (
    "Based on the information provided, your income exceeds 150% of "
    "the federal poverty guidelines. The filing fee of ${fee} applies. "
    "You may still apply for installment payments."
)


# -- Pure helper functions (no side effects) --


def _build_debtor_name(debtor_info: DebtorInfo) -> str:
    """Assemble a legal full name, collapsing empty middle names."""
    parts = (debtor_info.first_name, debtor_info.middle_name, debtor_info.last_name)
    return ' '.join(p for p in parts if p)


def _compute_cash_and_bank_balances(assets: list[AssetInfo]) -> Decimal:
    """Sum current_value of bank_account-type assets only."""
    return reduce(
        lambda acc, asset: acc + (asset.current_value or _ZERO),
        (a for a in assets if a.asset_type == BANK_ACCOUNT_TYPE),
        _ZERO,
    ).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _compute_total_property_value(assets: list[AssetInfo]) -> Decimal:
    """Sum current_value across all assets using reduce (encrypted fields)."""
    return reduce(
        lambda acc, asset: acc + (asset.current_value or _ZERO),
        assets,
        _ZERO,
    ).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _compute_total_debt(debts: list[DebtInfo]) -> Decimal:
    """Sum amount_owed across all debts using reduce (encrypted fields)."""
    return reduce(
        lambda acc, debt: acc + (debt.amount_owed or _ZERO),
        debts,
        _ZERO,
    ).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _determine_qualification_basis(fee_waiver: FeeWaiverApplication) -> str:
    """
    Determine which path qualifies the applicant for a fee waiver.

    Returns BASIS_BENEFITS if public benefits, BASIS_INCOME if income
    is below 150% poverty line, or BASIS_NONE if neither applies.
    Benefits check takes precedence (strongest qualification path).
    """
    if fee_waiver.receives_public_benefits:
        return BASIS_BENEFITS
    if fee_waiver.monthly_income < fee_waiver.get_poverty_threshold():
        return BASIS_INCOME
    return BASIS_NONE


def _get_result_message(basis: str, filing_fee: Decimal) -> str:
    """Return UPL-compliant result message based on qualification basis."""
    match basis:
        case 'income':
            return MSG_QUALIFIES_INCOME
        case 'benefits':
            return MSG_QUALIFIES_BENEFITS
        case _:
            return MSG_DOES_NOT_QUALIFY.replace(
                '${fee}', str(filing_fee.quantize(_TWO_PLACES))
            )


def _build_form_103b_data(
    *,
    debtor_name: str,
    household_size: int,
    monthly_income: Decimal,
    monthly_expenses: Decimal,
    cash_and_bank_balances: Decimal,
    total_property_value: Decimal,
    total_debt: Decimal,
    owns_property: bool,
    receives_benefits_or_disability: bool,
    receives_public_benefits: bool,
    benefit_types: list[str],
    qualifies_for_waiver: bool,
    qualification_basis: str,
    poverty_threshold_monthly: Decimal,
    filing_fee: Decimal,
    result_message: str,
    signature_date: str,
) -> dict[str, Any]:
    """
    Build complete Form 103B data structure.

    Pure function: deterministic output from given inputs.
    All monetary values are Decimal with 2 decimal places.
    """
    net_monthly_income = (monthly_income - monthly_expenses).quantize(
        _TWO_PLACES, rounding=ROUND_HALF_UP
    )

    return {
        'form_type': 'form_103b',
        'debtor_name': debtor_name,
        'case_number': '',  # Assigned by the court after filing

        # Part A: Family and income
        'household_size': household_size,
        'monthly_income': monthly_income.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP),
        'monthly_expenses': monthly_expenses.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP),
        'net_monthly_income': net_monthly_income,

        # Part C: Property and debts
        'cash_and_bank_balances': cash_and_bank_balances,
        'total_property_value': total_property_value,
        'total_debt': total_debt,

        # Part D: Additional questions
        'received_money_6_months': False,  # Placeholder for future intake step
        'owns_property': owns_property,
        'receives_benefits_or_disability': receives_benefits_or_disability,

        # Part E: Public benefits
        'receives_public_benefits': receives_public_benefits,
        'benefit_types': list(benefit_types),

        # Part F: Certification
        'penalty_of_perjury': True,
        'signature_date': signature_date,

        # Qualification result
        'qualifies_for_waiver': qualifies_for_waiver,
        'qualification_basis': qualification_basis,
        'poverty_threshold_monthly': poverty_threshold_monthly.quantize(
            _TWO_PLACES, rounding=ROUND_HALF_UP
        ),
        'filing_fee': filing_fee.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP),

        # UPL-compliant result message
        'result_message': result_message,
    }


# -- Exception --


class Form103BGenerationError(Exception):
    """Raised when Form 103B generation cannot proceed."""


# -- Generator class (thin wrapper over pure functions) --


class Form103BGenerator:
    """
    Generate Form 103B — Application to Have the Chapter 7 Filing Fee Waived.

    Requires a FeeWaiverApplication linked to the IntakeSession.
    Aggregates data from debtor info, assets, debts, and the fee waiver
    model to produce a court-ready fee waiver application.

    Official form: form_b103b.pdf
    28 U.S.C. § 1930(f)
    """

    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def _get_fee_waiver(self) -> FeeWaiverApplication:
        """Retrieve the FeeWaiverApplication or raise."""
        try:
            return self.session.fee_waiver
        except FeeWaiverApplication.DoesNotExist:
            raise Form103BGenerationError(
                'FeeWaiverApplication is required to generate Form 103B. '
                'Please complete the fee waiver information step first.'
            )

    def _get_debtor_name(self) -> str:
        """Extract debtor name, returning empty string if absent."""
        try:
            return _build_debtor_name(self.session.debtor_info)
        except DebtorInfo.DoesNotExist:
            return ''

    def _get_filing_fee(self) -> Decimal:
        """Retrieve Chapter 7 filing fee from the district model."""
        return self.session.district.filing_fee_chapter_7

    def generate(self) -> dict[str, Any]:
        """
        Generate complete Form 103B data for court filing.

        Raises:
            Form103BGenerationError: If FeeWaiverApplication is missing.
        """
        fee_waiver = self._get_fee_waiver()
        assets = list(self.session.assets.all())
        debts = list(self.session.debts.all())

        debtor_name = self._get_debtor_name()
        filing_fee = self._get_filing_fee()

        qualification_basis = _determine_qualification_basis(fee_waiver)

        return _build_form_103b_data(
            debtor_name=debtor_name,
            household_size=fee_waiver.household_size,
            monthly_income=fee_waiver.monthly_income,
            monthly_expenses=fee_waiver.monthly_expenses,
            cash_and_bank_balances=_compute_cash_and_bank_balances(assets),
            total_property_value=_compute_total_property_value(assets),
            total_debt=_compute_total_debt(debts),
            owns_property=len(assets) > 0,
            receives_benefits_or_disability=fee_waiver.receives_public_benefits,
            receives_public_benefits=fee_waiver.receives_public_benefits,
            benefit_types=fee_waiver.benefit_types,
            qualifies_for_waiver=fee_waiver.qualifies_for_waiver(),
            qualification_basis=qualification_basis,
            poverty_threshold_monthly=fee_waiver.get_poverty_threshold(),
            filing_fee=filing_fee,
            result_message=_get_result_message(qualification_basis, filing_fee),
            signature_date=date.today().isoformat(),
        )

    def preview(self) -> dict[str, Any]:
        """
        Generate a preview of Form 103B data.

        Returns the same structure as generate() wrapped with
        form metadata and UPL disclaimer. Suitable for on-screen
        review before filing.

        Raises:
            Form103BGenerationError: If FeeWaiverApplication is missing.
        """
        data = self.generate()

        return {
            'form_type': 'form_103b',
            'form_name': 'Application to Have the Chapter 7 Filing Fee Waived',
            'preview': True,
            'data': data,
            'upl_disclaimer': (
                'This is a preview of your fee waiver application. '
                'This information is provided to help you understand '
                'the filing fee waiver process. It is not legal advice. '
                'The court will make the final determination on your '
                'fee waiver application.'
            ),
        }
