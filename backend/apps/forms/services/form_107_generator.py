"""
Form 107 (Statement of Financial Affairs for Individuals) Generator.

Implements a structured 25-question output for the Statement of Financial
Affairs, which covers the debtor's financial history over the past 1-3 years.
Populates from existing intake models where possible; returns structured
placeholders for historical data not yet tracked in the system.

Official form: b_107_0425-form.pdf
"""

from decimal import Decimal, ROUND_HALF_UP
from functools import reduce
from typing import Any, Dict, List, Optional, Tuple

from apps.intake.models import (
    DebtInfo,
    DebtorInfo,
    IncomeInfo,
    IntakeSession,
)


# -- Constants --

ZERO = Decimal('0.00')
TWELVE = Decimal('12')
TOTAL_QUESTIONS = 25

# Lookback periods (in years) per official form instructions
LOOKBACK_INCOME = 2
LOOKBACK_CREDITOR_PAYMENTS = 90  # days, not years
LOOKBACK_GIFTS = 2
LOOKBACK_LOSSES = 1
LOOKBACK_INSIDER_TRANSFERS = 2
LOOKBACK_OTHER_TRANSFERS = 2
LOOKBACK_CLOSED_ACCOUNTS = 1
LOOKBACK_SAFE_DEPOSIT = 1
LOOKBACK_PREVIOUS_ADDRESS = 3

# Question text from official Form 107 (informational, verbatim from form)
QUESTION_TEXTS: Dict[int, str] = {
    1: (
        "Within 2 years before you filed for bankruptcy, did you have any income "
        "from employment or from operating a business?"
    ),
    2: (
        "Within 2 years before you filed for bankruptcy, did you receive any income "
        "other than from employment or operating a business?"
    ),
    3: (
        "Within 90 days before you filed for bankruptcy, did you make any payments "
        "on loans, installment purchases, or other debts totaling more than $600 "
        "to any single creditor?"
    ),
    4: (
        "Within 1 year before you filed for bankruptcy, were any of your debts "
        "the subject of a lawsuit, garnishment, attachment, or other legal action?"
    ),
    5: (
        "Within 1 year before you filed for bankruptcy, was any of your property "
        "repossessed by a creditor, sold at a foreclosure sale, transferred through "
        "a deed in lieu of foreclosure, or returned to the seller?"
    ),
    6: (
        "Within 1 year before you filed for bankruptcy, were any of your assets "
        "assigned for the benefit of creditors, or was a receiver, custodian, or "
        "other court-appointed official put in charge of any of your assets?"
    ),
    7: (
        "Within 2 years before you filed for bankruptcy, did you give any gifts "
        "with a total value of more than $600 per person, or any charitable "
        "contributions of more than $600?"
    ),
    8: (
        "Within 1 year before you filed for bankruptcy, did you have any losses "
        "from fire, theft, other casualty, or gambling?"
    ),
    9: (
        "Within 2 years before you filed for bankruptcy, did you make any "
        "transfers of property to, or for the benefit of, any insider (including "
        "family members, or a business insider)?"
    ),
    10: (
        "Within 2 years before you filed for bankruptcy, did you transfer any "
        "other property outside the ordinary course of your business or financial "
        "affairs?"
    ),
    11: (
        "Within 90 days before you filed for bankruptcy, did any creditor, "
        "including a bank or financial institution, set off or take any amount "
        "from your accounts?"
    ),
    12: (
        "Within 1 year before you filed for bankruptcy, did you close any "
        "financial accounts (checking, savings, money market, or other)?"
    ),
    13: (
        "Within 1 year before you filed for bankruptcy, did you have a safe "
        "deposit box or did you use a storage unit?"
    ),
    14: (
        "Are you holding or controlling any property that belongs to someone else?"
    ),
    15: (
        "Within 3 years before you filed for bankruptcy, did you live anywhere "
        "other than where you live now?"
    ),
    16: (
        "Do you own or have any interest in any business, or have you within "
        "6 years before you filed for bankruptcy?"
    ),
    17: (
        "Within 2 years before you filed for bankruptcy, did you consult "
        "with anyone, including an attorney, about filing for bankruptcy or "
        "an alternative to bankruptcy?"
    ),
    18: (
        "Within 1 year before you filed for bankruptcy, did you transfer any "
        "property to anyone who consults with you about bankruptcy or who "
        "prepared your petition?"
    ),
    19: (
        "Have any books, records, or financial statements relating to your debts, "
        "income, assets, and financial affairs been prepared for you or for any "
        "business you owned?"
    ),
    20: (
        "Have you filed any tax returns within 2 years before you filed for "
        "bankruptcy?"
    ),
    21: (
        "Within 2 years before you filed for bankruptcy, were you a party to "
        "any lawsuit, court action, or administrative proceeding?"
    ),
    22: (
        "Have you made any gifts or charitable contributions of more than $600 "
        "to any recipient within 2 years before you filed for bankruptcy?"
    ),
    23: (
        "Do you have any property that is being held by someone else, including "
        "a storage facility?"
    ),
    24: (
        "Within 1 year before you filed for bankruptcy, did you make any "
        "payments relating to tax debts?"
    ),
    25: (
        "Within 1 year before you filed for bankruptcy, did you make any "
        "payments or transfers of property to anyone who you consulted about "
        "filing for bankruptcy or who prepared your bankruptcy documents?"
    ),
}


# -- Pure helper functions (no side effects) --


def _build_question(
    question_number: int,
    has_data: bool,
    response: str,
    details: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build a single question dict for the Form 107 output.

    Pure function: deterministic output from given inputs.
    """
    return {
        'question_number': question_number,
        'question_text': QUESTION_TEXTS.get(question_number, ''),
        'has_data': has_data,
        'response': response,
        'details': details if details is not None else [],
    }


def _compute_annual_income_from_monthly(monthly_income: List) -> Decimal:
    """
    Compute annualized income from 6-month income array.

    CMI (average of 6 months) * 12 = annualized.
    """
    if not monthly_income:
        return ZERO

    total = reduce(
        lambda acc, amount: acc + Decimal(str(amount)),
        monthly_income,
        ZERO,
    )
    month_count = Decimal(str(len(monthly_income)))
    cmi = (total / month_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return (cmi * TWELVE).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _compute_total_monthly_income(monthly_income: List) -> Decimal:
    """Compute average monthly income from the 6-month array."""
    if not monthly_income:
        return ZERO

    total = reduce(
        lambda acc, amount: acc + Decimal(str(amount)),
        monthly_income,
        ZERO,
    )
    month_count = Decimal(str(len(monthly_income)))
    return (total / month_count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _extract_creditor_payments(debts: List[DebtInfo]) -> List[Dict[str, Any]]:
    """
    Extract creditor payment details for Q3 (payments in last 90 days).

    Uses debts with a non-null monthly_payment as proxy for recent payments.
    Cannot determine exact payment dates from current model, so includes
    all debts with active monthly payments.
    """
    return [
        {
            'creditor_name': debt.creditor_name,
            'amount': debt.monthly_payment,
            'debt_type': debt.debt_type,
            'account_number_last4': (
                debt.account_number[-4:]
                if debt.account_number and len(debt.account_number) >= 4
                else debt.account_number or ''
            ),
        }
        for debt in debts
        if debt.monthly_payment is not None and debt.monthly_payment > ZERO
    ]


def _build_income_question(monthly_income: List) -> Dict[str, Any]:
    """Build Q1: Employment/business income from IncomeInfo."""
    annual = _compute_annual_income_from_monthly(monthly_income)
    monthly_avg = _compute_total_monthly_income(monthly_income)
    has_income = annual > ZERO

    details = (
        [{
            'source': 'Employment/self-employment',
            'monthly_average': str(monthly_avg),
            'annualized': str(annual),
            'months_reported': len(monthly_income),
        }]
        if has_income
        else []
    )

    return _build_question(
        question_number=1,
        has_data=True,
        response='Yes' if has_income else 'No',
        details=details,
    )


def _build_creditor_payments_question(
    debts: List[DebtInfo],
) -> Dict[str, Any]:
    """Build Q3: Payments to creditors in last 90 days."""
    payments = _extract_creditor_payments(debts)
    has_payments = len(payments) > 0

    serialized = [
        {
            'creditor_name': p['creditor_name'],
            'amount': str(p['amount']),
            'debt_type': p['debt_type'],
            'account_number_last4': p['account_number_last4'],
        }
        for p in payments
    ]

    return _build_question(
        question_number=3,
        has_data=True,
        response='Yes' if has_payments else 'No',
        details=serialized,
    )


def _build_placeholder_question(question_number: int) -> Dict[str, Any]:
    """Build a placeholder question where data is not yet tracked."""
    return _build_question(
        question_number=question_number,
        has_data=False,
        response='N/A',
        details=[],
    )


def _build_debtor_name(debtor_info: Optional[DebtorInfo]) -> str:
    """Build full debtor name from DebtorInfo, or empty string if missing."""
    if debtor_info is None:
        return ''

    parts = [debtor_info.first_name]
    if debtor_info.middle_name:
        parts.append(debtor_info.middle_name)
    parts.append(debtor_info.last_name)
    return ' '.join(parts)


def _build_all_questions(
    monthly_income: List,
    debts: List[DebtInfo],
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Build all 25 questions for Form 107.

    Returns (questions_list, questions_with_data_count, questions_needing_input_count).
    Questions 1 and 3 are populated from existing models; the rest are placeholders.
    """
    # Questions populated from existing data
    populated_questions = {
        1: _build_income_question(monthly_income),
        3: _build_creditor_payments_question(debts),
    }

    # Build all 25 questions in order
    questions: List[Dict[str, Any]] = []
    for q_num in range(1, TOTAL_QUESTIONS + 1):
        if q_num in populated_questions:
            questions.append(populated_questions[q_num])
        else:
            questions.append(_build_placeholder_question(q_num))

    questions_with_data = sum(1 for q in questions if q['has_data'])
    questions_needing_input = TOTAL_QUESTIONS - questions_with_data

    return questions, questions_with_data, questions_needing_input


def _build_form_107_data(
    debtor_name: str,
    monthly_income: List,
    debts: List[DebtInfo],
) -> Dict[str, Any]:
    """
    Build the complete Form 107 output from pre-computed components.

    Pure function: deterministic output from given inputs.
    """
    questions, with_data, needing_input = _build_all_questions(
        monthly_income=monthly_income,
        debts=debts,
    )

    return {
        'form_type': 'form_107',
        'debtor_name': debtor_name,
        'case_number': '',  # Assigned by court at filing
        'questions': questions,
        'total_questions': TOTAL_QUESTIONS,
        'questions_with_data': with_data,
        'questions_needing_input': needing_input,
    }


class Form107Generator:
    """
    Generate Form 107: Statement of Financial Affairs for Individuals.

    Produces a structured 25-question output covering the debtor's financial
    history. Populates questions from existing intake models where possible,
    and returns structured placeholders for data not yet tracked.

    Official form: b_107_0425-form.pdf
    """

    def __init__(self, intake_session: IntakeSession) -> None:
        self.session = intake_session

    def generate(self) -> Dict[str, Any]:
        """
        Generate Form 107 data structure.

        Extracts debtor name, income, and debt data from the intake session
        to populate applicable questions.
        """
        # Extract debtor name (graceful degradation if missing)
        try:
            debtor_info: DebtorInfo = self.session.debtor_info
        except DebtorInfo.DoesNotExist:
            debtor_info = None

        debtor_name = _build_debtor_name(debtor_info)

        # Extract income data (graceful degradation if missing)
        try:
            income_info: IncomeInfo = self.session.income_info
            monthly_income = list(income_info.monthly_income)
        except IncomeInfo.DoesNotExist:
            monthly_income = []

        # Extract debt data
        debts = list(self.session.debts.all())

        return _build_form_107_data(
            debtor_name=debtor_name,
            monthly_income=monthly_income,
            debts=debts,
        )

    def preview(self) -> Dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()
