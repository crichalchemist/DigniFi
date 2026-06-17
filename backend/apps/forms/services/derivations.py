"""
Factual/clerical derivations (DERIVATIONS) and section-applicability
predicates (PREDICATES) for the fill engine.

UPL boundary: these encode ONLY facts and clerical transforms. No legal
conclusion (exemption-statute choice, debt priority, means-test verdict) may
live here — those are ``asked`` + ``legal_review`` in the schema.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal
from functools import reduce

from apps.intake.models import IntakeSession

_ZERO = Decimal("0.00")
_TWO_PLACES = Decimal("0.01")


# ---------------------------------------------------------------------------
# Safe accessor helpers
# ---------------------------------------------------------------------------


def _safe_debtor_attr(session: IntakeSession, attr: str, default: str = "") -> str:
    try:
        val = getattr(session.debtor_info, attr)
        return str(val) if val is not None else default
    except Exception:
        return default


def _full_name(session: IntakeSession) -> str:
    try:
        di = session.debtor_info
    except Exception:
        return ""
    return f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()


def _has_ssn(session: IntakeSession) -> bool:
    try:
        return bool(session.debtor_info.ssn)
    except Exception:
        return False


def _ssn_formatted(session: IntakeSession) -> str:
    try:
        raw = session.debtor_info.ssn or ""
    except Exception:
        return ""
    cleaned = raw.strip().replace("-", "")
    if len(cleaned) == 9 and cleaned.isdigit():
        return f"{cleaned[:3]}-{cleaned[3:5]}-{cleaned[5:]}"
    if "-" in raw and len(raw) == 11:
        return raw
    return ""


def _fmt(d: Decimal) -> str:
    return str(d.quantize(_TWO_PLACES))


def _sum_encrypted(queryset, field_name: str) -> Decimal:
    return reduce(lambda acc, obj: acc + (getattr(obj, field_name) or _ZERO), queryset, _ZERO)


# ---------------------------------------------------------------------------
# Form 106Sum aggregation derivations
# ---------------------------------------------------------------------------


def _total_real_property(session: IntakeSession) -> str:
    from apps.intake.models import AssetInfo

    qs = AssetInfo.objects.filter(session=session, asset_type="real_property")
    return _fmt(_sum_encrypted(qs, "current_value"))


def _total_personal_property(session: IntakeSession) -> str:
    from apps.intake.models import AssetInfo

    qs = AssetInfo.objects.filter(session=session).exclude(asset_type="real_property")
    return _fmt(_sum_encrypted(qs, "current_value"))


def _total_assets(session: IntakeSession) -> str:
    from apps.intake.models import AssetInfo

    qs = AssetInfo.objects.filter(session=session)
    return _fmt(_sum_encrypted(qs, "current_value"))


def _total_secured_debts(session: IntakeSession) -> str:
    from apps.intake.models import DebtInfo

    qs = DebtInfo.objects.filter(session=session, is_secured=True)
    return _fmt(_sum_encrypted(qs, "amount_owed"))


def _total_priority_unsecured(session: IntakeSession) -> str:
    from apps.intake.models import DebtInfo

    qs = DebtInfo.objects.filter(session=session, is_secured=False, is_priority=True)
    return _fmt(_sum_encrypted(qs, "amount_owed"))


def _total_nonpriority_unsecured(session: IntakeSession) -> str:
    from apps.intake.models import DebtInfo

    qs = DebtInfo.objects.filter(session=session, is_secured=False, is_priority=False)
    return _fmt(_sum_encrypted(qs, "amount_owed"))


def _total_unsecured_debts(session: IntakeSession) -> str:
    from apps.intake.models import DebtInfo

    qs = DebtInfo.objects.filter(session=session, is_secured=False)
    return _fmt(_sum_encrypted(qs, "amount_owed"))


def _total_debts(session: IntakeSession) -> str:
    from apps.intake.models import DebtInfo

    qs = DebtInfo.objects.filter(session=session)
    return _fmt(_sum_encrypted(qs, "amount_owed"))


def _cmi(session: IntakeSession) -> str:
    from apps.intake.models import IncomeInfo

    try:
        income_info = session.income_info
    except IncomeInfo.DoesNotExist:
        return "0.00"
    monthly = getattr(income_info, "monthly_income", None) or []
    if not monthly:
        return "0.00"
    total = reduce(lambda acc, v: acc + Decimal(str(v)), monthly, _ZERO)
    return _fmt(total / Decimal("6"))


def _total_monthly_expenses(session: IntakeSession) -> str:
    from apps.intake.models import ExpenseInfo

    try:
        expense_info = session.expense_info
    except ExpenseInfo.DoesNotExist:
        return "0.00"
    return _fmt(Decimal(str(expense_info.calculate_total_monthly_expenses())))


# ---------------------------------------------------------------------------
# Form 122A-1 means test derivations
# ---------------------------------------------------------------------------


def _get_income_field(session: IntakeSession, field: str) -> Decimal:
    try:
        income_info = session.income_info
        val = getattr(income_info, field, None)
        if val is None:
            return _ZERO
        if isinstance(val, list):
            return sum((Decimal(str(v)) for v in val), _ZERO) / Decimal(str(len(val)))
        return Decimal(str(val))
    except Exception:
        return _ZERO


def _line1_wages(session: IntakeSession) -> str:
    return _fmt(_get_income_field(session, "wages_salaries_tips"))


def _line2_business_income(session: IntakeSession) -> str:
    return _fmt(_get_income_field(session, "business_income"))


def _line3_real_property_income(session: IntakeSession) -> str:
    return _fmt(_get_income_field(session, "real_property_income"))


def _line4_interest_dividends(session: IntakeSession) -> str:
    return _fmt(_get_income_field(session, "interest_dividends"))


def _line5a_pension_retirement(session: IntakeSession) -> str:
    return _fmt(_get_income_field(session, "pension_retirement"))


def _line5b_social_security(session: IntakeSession) -> str:
    return _fmt(_get_income_field(session, "social_security"))


def _line6a_unemployment(session: IntakeSession) -> str:
    return _fmt(_get_income_field(session, "unemployment_compensation"))


def _line6b_child_support_alimony(session: IntakeSession) -> str:
    return _fmt(_get_income_field(session, "child_support_alimony"))


def _line7_other_income(session: IntakeSession) -> str:
    return _fmt(_get_income_field(session, "other_income"))


def _line8a_total_gross_income(session: IntakeSession) -> str:
    total = sum(
        (
            _get_income_field(session, "wages_salaries_tips"),
            _get_income_field(session, "business_income"),
            _get_income_field(session, "real_property_income"),
            _get_income_field(session, "interest_dividends"),
            _get_income_field(session, "pension_retirement"),
            _get_income_field(session, "social_security"),
            _get_income_field(session, "unemployment_compensation"),
            _get_income_field(session, "child_support_alimony"),
            _get_income_field(session, "other_income"),
        ),
        _ZERO,
    )
    return _fmt(total)


def _line10a_deductions(session: IntakeSession) -> str:
    return _fmt(_get_income_field(session, "deductions"))


def _line10b_total_deductions(session: IntakeSession) -> str:
    return _fmt(_get_income_field(session, "total_deductions"))


def _line10c_net_income(session: IntakeSession) -> str:
    gross = Decimal(_line8a_total_gross_income(session))
    deductions = Decimal(_line10b_total_deductions(session))
    return _fmt(gross - deductions)


def _line11_annualized_income(session: IntakeSession) -> str:
    cmi = Decimal(_cmi(session))
    return _fmt(cmi * Decimal("12"))


def _line12b_annualized_cmi(session: IntakeSession) -> str:
    return _line11_annualized_income(session)


def _line13a_median_income(session: IntakeSession) -> str:
    from apps.districts.models import MedianIncome

    try:
        income_info = session.income_info
        size = 1 + income_info.number_of_dependents
        if income_info.marital_status in ("married_joint", "married_separate"):
            size += 1
    except Exception:
        size = 1
    median = (
        MedianIncome.objects.filter(district=session.district).order_by("-effective_date").first()
    )
    if median is None:
        return "0.00"
    return _fmt(median.get_median_income(size))


def _line13b_annualized_income(session: IntakeSession) -> str:
    return _line11_annualized_income(session)


def _line13c_difference(session: IntakeSession) -> str:
    annualized = Decimal(_line11_annualized_income(session))
    median = Decimal(_line13a_median_income(session))
    return _fmt(annualized - median)


# ---------------------------------------------------------------------------
# Form 103B fee waiver derivations
# ---------------------------------------------------------------------------


def _fee_waiver_household_size(session: IntakeSession) -> str:

    try:
        fw = session.fee_waiver
        return str(fw.household_size)
    except Exception:
        return "1"


def _fee_waiver_monthly_income(session: IntakeSession) -> str:

    try:
        fw = session.fee_waiver
        return _fmt(Decimal(str(fw.monthly_income)))
    except Exception:
        return "0.00"


def _fee_waiver_monthly_expenses(session: IntakeSession) -> str:

    try:
        fw = session.fee_waiver
        return _fmt(Decimal(str(fw.monthly_expenses)))
    except Exception:
        return "0.00"


# ---------------------------------------------------------------------------
# DERIVATIONS dict (all referenced functions must be defined above)
# ---------------------------------------------------------------------------

DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
    "full_name": _full_name,
    "family_size": lambda s: _safe_debtor_attr(s, "household_size", "1"),
    "first_name": lambda s: _safe_debtor_attr(s, "first_name"),
    "middle_name": lambda s: _safe_debtor_attr(s, "middle_name"),
    "last_name": lambda s: _safe_debtor_attr(s, "last_name"),
    "ssn_last_4": lambda s: (_safe_debtor_attr(s, "ssn"))[-4:],
    "street_address": lambda s: _safe_debtor_attr(s, "street_address"),
    "city": lambda s: _safe_debtor_attr(s, "city"),
    "state": lambda s: _safe_debtor_attr(s, "state"),
    "zip_code": lambda s: _safe_debtor_attr(s, "zip_code"),
    "phone": lambda s: _safe_debtor_attr(s, "phone"),
    "email": lambda s: _safe_debtor_attr(s, "email"),
    "chapter": lambda s: "7",
    "debtor_type": lambda s: "Individual",
    "district_name": lambda s: s.district.name,
    "today_iso": lambda s: date.today().isoformat(),
    "ssn_formatted": _ssn_formatted,
    "has_ssn_check": lambda s: "true" if _has_ssn(s) else "",
    "no_ssn_check": lambda s: "" if _has_ssn(s) else "true",
    "joint_filer_check": lambda s: (
        "true" if _form_answer_predicate(s, "joint_filer_gate") else ""
    ),
    "total_real_property": _total_real_property,
    "total_personal_property": _total_personal_property,
    "total_assets": _total_assets,
    "total_secured_debts": _total_secured_debts,
    "total_priority_unsecured": _total_priority_unsecured,
    "total_nonpriority_unsecured": _total_nonpriority_unsecured,
    "total_unsecured_debts": _total_unsecured_debts,
    "total_debts": _total_debts,
    "cmi": _cmi,
    "total_monthly_expenses": _total_monthly_expenses,
    # Form 122A-1 means test derivations
    "line1_wages": _line1_wages,
    "line2_business_income": _line2_business_income,
    "line3_real_property_income": _line3_real_property_income,
    "line4_interest_dividends": _line4_interest_dividends,
    "line5a_pension_retirement": _line5a_pension_retirement,
    "line5b_social_security": _line5b_social_security,
    "line6a_unemployment": _line6a_unemployment,
    "line6b_child_support_alimony": _line6b_child_support_alimony,
    "line7_other_income": _line7_other_income,
    "line8a_total_gross_income": _line8a_total_gross_income,
    "line10a_deductions": _line10a_deductions,
    "line10b_total_deductions": _line10b_total_deductions,
    "line10c_net_income": _line10c_net_income,
    "line11_annualized_income": _line11_annualized_income,
    "line12b_annualized_cmi": _line12b_annualized_cmi,
    "line13a_median_income": _line13a_median_income,
    "line13b_annualized_income": _line13b_annualized_income,
    "line13c_difference": _line13c_difference,
    # Form 103B fee waiver derivations
    "fee_waiver_household_size": _fee_waiver_household_size,
    "fee_waiver_monthly_income": _fee_waiver_monthly_income,
    "fee_waiver_monthly_expenses": _fee_waiver_monthly_expenses,
}


# ---------------------------------------------------------------------------
# PREDICATES — section-applicability checks
# ---------------------------------------------------------------------------


def _has_business(session: IntakeSession, answer_cache: dict | None = None) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_business)


def _has_creditor_payments(session: IntakeSession, answer_cache: dict | None = None) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_creditor_payments)


def _has_prior_income(session: IntakeSession, answer_cache: dict | None = None) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_prior_income)


def _form_answer_predicate(
    session: IntakeSession, key: str, answer_cache: dict | None = None
) -> bool:
    if answer_cache is not None:
        ans = answer_cache.get(key)
        return bool(ans and ans.value and ans.value.lower() in ("yes", "y", "true", "1"))

    from apps.intake.models import FormAnswer

    ans = FormAnswer.objects.filter(session=session, field_key=key).first()
    return bool(ans and ans.value and ans.value.lower() in ("yes", "y", "true", "1"))


PREDICATES: dict[str, Callable[[IntakeSession], bool]] = {
    "has_business": _has_business,
    "has_creditor_payments": _has_creditor_payments,
    "has_prior_income": _has_prior_income,
    "has_insider_payments": lambda s, answer_cache=None: _form_answer_predicate(
        s, "insider_payments_gate", answer_cache
    ),
    "has_legal_actions": lambda s, answer_cache=None: _form_answer_predicate(
        s, "legal_actions_gate", answer_cache
    ),
    "has_financial_accounts": lambda s, answer_cache=None: _form_answer_predicate(
        s, "financial_accounts_gate", answer_cache
    ),
    "has_property_loss": lambda s, answer_cache=None: _form_answer_predicate(
        s, "property_loss_gate", answer_cache
    ),
    "has_property_transfers": lambda s, answer_cache=None: _form_answer_predicate(
        s, "property_transfers_gate", answer_cache
    ),
    "has_closed_accounts": lambda s, answer_cache=None: _form_answer_predicate(
        s, "closed_accounts_gate", answer_cache
    ),
    "has_safe_deposit": lambda s, answer_cache=None: _form_answer_predicate(
        s, "safe_deposit_gate", answer_cache
    ),
    "has_environmental": lambda s, answer_cache=None: _form_answer_predicate(
        s, "environmental_gate", answer_cache
    ),
    "has_prior_bankruptcy": lambda s, answer_cache=None: _form_answer_predicate(
        s, "prior_bankruptcy_gate", answer_cache
    ),
    "has_accountant": lambda s, answer_cache=None: _form_answer_predicate(
        s, "accountant_gate", answer_cache
    ),
    "has_joint_filer": lambda s, answer_cache=None: _form_answer_predicate(
        s, "joint_filer_gate", answer_cache
    ),
    "has_address_history": lambda s, answer_cache=None: _form_answer_predicate(
        s, "address_history_gate", answer_cache
    ),
    "has_attorney": lambda s, answer_cache=None: _form_answer_predicate(
        s, "attorney_gate", answer_cache
    ),
}
