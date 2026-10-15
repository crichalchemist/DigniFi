"""
Factual/clerical derivations (DERIVATIONS) and section-applicability
predicates (PREDICATES) for the fill engine.

UPL boundary: these encode ONLY facts and clerical transforms. A rule may
apply a comparison the form itself spells out (122A-1 line 14: line 12b
against line 13), but no rule may choose exemptions, decide priority, or
answer anything the form leaves to the filer — those are ``asked`` +
``legal_review`` in the schema.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from functools import reduce

from apps.eligibility.cmi import IncomeNotSplit, current_monthly_income, is_above_median
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


def _income_amounts(session: IntakeSession, *fields: str) -> str:
    """The sum of these Income step amounts, or blank when the filer gave none of them.

    An amount left empty counts as zero once another one was given (step 2 spec §6.1, B2).
    """
    income_info = getattr(session, "income_info", None)
    if income_info is None:
        return ""
    given = [getattr(income_info, f) for f in fields if getattr(income_info, f) is not None]
    if not given:
        return ""
    return _fmt(sum(given, _ZERO))


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


def _total_nonpriority_unsecured(session: IntakeSession) -> str:
    from apps.intake.models import DebtInfo

    qs = DebtInfo.objects.filter(session=session, is_secured=False, is_priority=False)
    return _fmt(_sum_encrypted(qs, "amount_owed"))


def _total_debts(session: IntakeSession) -> str:
    from apps.intake.models import DebtInfo

    qs = DebtInfo.objects.filter(session=session)
    return _fmt(_sum_encrypted(qs, "amount_owed"))


def _total_other_assets(session: IntakeSession) -> str:
    from apps.intake.models import AssetInfo

    qs = AssetInfo.objects.filter(session=session, asset_type="other")
    return _fmt(_sum_encrypted(qs, "current_value"))


def _cmi(session: IntakeSession) -> str:
    from apps.intake.models import IncomeInfo

    try:
        income_info = session.income_info
    except IncomeInfo.DoesNotExist:
        # No income at all is income not entered by source.
        raise IncomeNotSplit() from None
    return _fmt(current_monthly_income(income_info))


def _total_monthly_expenses(session: IntakeSession) -> str:
    from apps.intake.models import ExpenseInfo

    try:
        expense_info = session.expense_info
    except ExpenseInfo.DoesNotExist:
        return "0.00"
    return _fmt(Decimal(str(expense_info.calculate_total_monthly_expenses())))


# ---------------------------------------------------------------------------
# Schedule A/B part totals, line 53, and the section questions of A/B, G and H
# ---------------------------------------------------------------------------


def _total_vehicles(session: IntakeSession) -> str:
    from apps.intake.models import AssetInfo

    qs = AssetInfo.objects.filter(session=session, asset_type="vehicle")
    return _fmt(_sum_encrypted(qs, "current_value"))


def _total_household_items(session: IntakeSession) -> str:
    from apps.intake.models import AssetInfo

    qs = AssetInfo.objects.filter(session=session, asset_type="personal_property")
    return _fmt(_sum_encrypted(qs, "current_value"))


def _total_financial_assets(session: IntakeSession) -> str:
    """Part 4, line 36: deposits (17) and retirement accounts (21), the only lines asked."""
    from apps.intake.models import AssetInfo

    qs = AssetInfo.objects.filter(
        session=session, asset_type__in=("bank_account", "retirement_account")
    )
    return _fmt(_sum_encrypted(qs, "current_value"))


def _other_asset_descriptions(session: IntakeSession) -> str:
    """Line 53: the "Other" assets in the order the filer listed them (DIG-164)."""
    from apps.intake.models import AssetInfo

    # The model orders by encrypted value, so the filer's order is the id's.
    qs = AssetInfo.objects.filter(session=session, asset_type="other").order_by("id")
    return "; ".join(qs.values_list("description", flat=True))


def _yes_if_any(rows) -> str:
    """A section's Yes/No question (owner Q8): "yes" when the filer listed one, else "no"."""
    return "yes" if rows.exists() else "no"


# ---------------------------------------------------------------------------
# Form 101 lines 18-20: estimated creditors, assets and liabilities
# ---------------------------------------------------------------------------

# (a range's top, its lowest figure). Each box's choices map the lowest figure to that
# box's own spelling of the range, which differs between lines 19 and 20.
_CREDITOR_RANGES = (
    (49, "1"),
    (99, "50"),
    (199, "100"),
    (999, "200"),
    (5000, "1000"),
    (10000, "5001"),
    (25000, "10001"),
    (50000, "25001"),
    (100000, "50001"),
)
_AMOUNT_RANGES = (
    (50000, "0"),
    (100000, "50001"),
    (500000, "100001"),
    (1000000, "500001"),
    (10000000, "1000001"),
    (50000000, "10000001"),
    (100000000, "50000001"),
    (500000000, "100000001"),
    (1000000000, "500000001"),
    (10000000000, "1000000001"),
    (50000000000, "10000000001"),
)


def _range(figure, ranges) -> str:
    """
    The lowest figure of the first range whose top `figure` doesn't pass, or "more".

    Comparing with each range's top puts cents between two ranges in the higher one.
    """
    for top, lowest in ranges:
        if figure <= top:
            return lowest
    return "more"


def _creditor_count_range(session: IntakeSession) -> str:
    from apps.intake.models import DebtInfo

    count = DebtInfo.objects.filter(session=session).count()
    return _range(count, _CREDITOR_RANGES) if count else ""


def _total_assets_range(session: IntakeSession) -> str:
    # No assets is the $0-$50,000 range, not a blank line.
    return _range(Decimal(_total_assets(session)), _AMOUNT_RANGES)


def _total_debts_range(session: IntakeSession) -> str:
    return _range(Decimal(_total_debts(session)), _AMOUNT_RANGES)


# ---------------------------------------------------------------------------
# Form 122A-1 means test derivations
# ---------------------------------------------------------------------------


def _line1_wages(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_gross_wages", "monthly_tips", "monthly_overtime")


def _line3_alimony(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_alimony")


def _line3_real_property_income(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_rental_income")


def _line5a_pension_retirement(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_pension")


def _line6a_unemployment(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_unemployment")


def _line6b_child_support_alimony(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_child_support")


def _line7_other_income(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_other_income")


def _other_income_label(session: IntakeSession) -> str:
    """What the other income is, on 122A-1 line 10 and Schedule I 8h: named only above $0."""
    income_info = getattr(session, "income_info", None)
    other = None if income_info is None else income_info.monthly_other_income
    return "Other income" if other is not None and other > 0 else ""


def _line11_annualized_income(session: IntakeSession) -> str:
    cmi = Decimal(_cmi(session))
    return _fmt(cmi * Decimal("12"))


def _line12b_annualized_cmi(session: IntakeSession) -> str:
    return _line11_annualized_income(session)


def _line13a_median_income(session: IntakeSession) -> str:
    """Line 13: the median the means test compared against (DIG-51), blank before it runs."""
    means_test = getattr(session, "means_test", None)
    if means_test is None:
        return ""
    return _fmt(means_test.median_income_threshold)


def _median_comparison(session: IntakeSession) -> str:
    """
    Line 14 and the page-1 result: line 12b against line 13, as the form says to compare.

    The packet's comparison (exactly the median is below it, DIG-136), so the ticks always
    agree with whether Form 122A-2 is filed. Blank before the means test runs.
    """
    means_test = getattr(session, "means_test", None)
    if means_test is None:
        return ""
    if is_above_median(means_test.calculated_cmi, means_test.median_income_threshold):
        return "above"
    return "below"


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
    """Line 2: the take-home pay the filer typed, blank if they never gave it (B2)."""
    fw = getattr(session, "fee_waiver", None)
    if fw is None or fw.monthly_take_home_pay is None:
        return ""
    return _fmt(Decimal(str(fw.monthly_take_home_pay)))


def _fee_waiver_noncash_assistance(session: IntakeSession) -> str:
    """Line 3: the filer's own yes or no, blank until they answer (DIG-193)."""
    fw = getattr(session, "fee_waiver", None)
    answer = None if fw is None else fw.receives_noncash_assistance
    if answer is True:
        return "yes"
    if answer is False:
        return "no"
    return ""


def _fee_waiver_benefit_types(session: IntakeSession) -> str:
    """Line 3's "Describe": the kinds of help, joined as the fee-waiver page shows them."""
    fw = getattr(session, "fee_waiver", None)
    if fw is None or fw.receives_noncash_assistance is not True:
        return ""
    return ", ".join(fw.benefit_types)


# ---------------------------------------------------------------------------
# Schedule I income line item derivations
# ---------------------------------------------------------------------------


def _schedule_i_occupation_debtor1(session: IntakeSession) -> str:
    return _safe_debtor_attr(session, "occupation", "")


def _schedule_i_employer_debtor1(session: IntakeSession) -> str:
    return _safe_debtor_attr(session, "employer_name", "")


def _schedule_i_net_wages_debtor1(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_gross_wages", "monthly_tips")


def _schedule_i_overtime_debtor1(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_overtime")


def _schedule_i_gross_income_debtor1(session: IntakeSession) -> str:
    """Line 4, line 2 + line 3, and line 7 until payroll deductions are asked (step 3)."""
    return _income_amounts(session, "monthly_gross_wages", "monthly_tips", "monthly_overtime")


def _schedule_i_unemployment_debtor1(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_unemployment")


def _schedule_i_social_security_debtor1(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_social_security")


def _schedule_i_pension_debtor1(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_pension")


def _schedule_i_child_support_debtor1(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_child_support", "monthly_alimony")


def _schedule_i_rental_debtor1(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_rental_income")


def _schedule_i_other_income_debtor1(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_other_income")


def _schedule_i_other_income_total_debtor1(session: IntakeSession) -> str:
    """Line 9, 8a through 8h: interest (8b) and other assistance (8f) are never asked."""
    return _income_amounts(
        session,
        "monthly_rental_income",
        "monthly_child_support",
        "monthly_alimony",
        "monthly_unemployment",
        "monthly_social_security",
        "monthly_pension",
        "monthly_other_income",
    )


def _schedule_i_income_total(session: IntakeSession) -> str:
    """
    Schedule I lines 10 and 12: all ten sources, Social Security included (C1), unlike CMI.

    Line 10's spouse column and line 11 are never asked and count as zero (step 2 spec §6.1).
    """
    from apps.intake.models import IncomeInfo

    return _income_amounts(session, *IncomeInfo.SOURCE_FIELDS)


# ---------------------------------------------------------------------------
# Schedule J expense line item derivations
# ---------------------------------------------------------------------------


def _expense_amount(session: IntakeSession, field: str) -> Decimal:
    """An Expenses step amount, or $0 when the step was never saved."""
    expense_info = getattr(session, "expense_info", None)
    return _ZERO if expense_info is None else Decimal(str(getattr(expense_info, field)))


def _expense_line(session: IntakeSession, field: str) -> str:
    """
    An expense line prints only above $0 (step 2 spec §6.1, 6c option A).

    An expense left empty is stored as $0, so $0 can't be told from "left blank".
    """
    amount = _expense_amount(session, field)
    return _fmt(amount) if amount > 0 else ""


def _expense_label(session: IntakeSession, field: str, label: str) -> str:
    """An "Other. Specify:" line's text, printed only when its amount prints (Q4)."""
    return label if _expense_amount(session, field) > 0 else ""


def _schedule_j_total_expenses(session: IntakeSession) -> str:

    try:
        return _fmt(Decimal(str(session.expense_info.calculate_total_monthly_expenses())))
    except Exception:
        return "0.00"


def _schedule_j_monthly_net_income(session: IntakeSession) -> str:
    """
    Line 23c, 23a - 23b: blank while 23a is, and below zero when expenses pass income.

    23a is Schedule I line 12 and 23b is line 22c, so 23c is computed from those rules.
    """
    income = _schedule_i_income_total(session)
    if income == "":
        return ""
    return _fmt(Decimal(income) - Decimal(_schedule_j_total_expenses(session)))


def _schedule_j_joint_case(session: IntakeSession) -> str:
    """
    Line 1: "no" for an individual filing, blank for a joint one (DIG-177).

    A joint filer still gets a single filer's packet, so line 1 says nothing for them.
    """
    debtor_info = getattr(session, "debtor_info", None)
    if debtor_info is not None and debtor_info.filing_type == "individual":
        return "no"
    return ""


def _means_test_disposable_income(session: IntakeSession) -> str:
    try:
        mt = session.means_test
        return _fmt(mt.disposable_income)
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
    "ssn_formatted": _ssn_formatted,
    "no_ssn_check": lambda s: "" if _has_ssn(s) else "true",
    "joint_filer_check": lambda s: (
        "true" if _form_answer_predicate(s, "joint_filer_gate") else ""
    ),
    "total_real_property": _total_real_property,
    "total_personal_property": _total_personal_property,
    "total_assets": _total_assets,
    "total_secured_debts": _total_secured_debts,
    "total_nonpriority_unsecured": _total_nonpriority_unsecured,
    "total_debts": _total_debts,
    "total_other_assets": _total_other_assets,
    "total_secured_claims": _total_secured_debts,
    "joint_filer_name": _full_name,
    "cmi": _cmi,
    "total_monthly_expenses": _total_monthly_expenses,
    # Schedule A/B part totals, line 53, and the section questions of A/B, G and H
    "total_vehicles": _total_vehicles,
    "total_household_items": _total_household_items,
    "total_financial_assets": _total_financial_assets,
    "other_asset_descriptions": _other_asset_descriptions,
    "has_real_property": lambda s: _yes_if_any(s.assets.filter(asset_type="real_property")),
    "has_vehicles": lambda s: _yes_if_any(s.assets.filter(asset_type="vehicle")),
    "has_bank_accounts": lambda s: _yes_if_any(s.assets.filter(asset_type="bank_account")),
    "has_retirement_accounts": lambda s: _yes_if_any(
        s.assets.filter(asset_type="retirement_account")
    ),
    "has_other_assets": lambda s: _yes_if_any(s.assets.filter(asset_type="other")),
    "has_executory_contracts": lambda s: _yes_if_any(s.executory_contracts.all()),
    "has_codebtors": lambda s: _yes_if_any(s.codebtors.all()),
    # Form 101 lines 18-20
    "creditor_count_range": _creditor_count_range,
    "total_assets_range": _total_assets_range,
    "total_debts_range": _total_debts_range,
    # Form 122A-1 means test derivations
    "line1_wages": _line1_wages,
    "line3_alimony": _line3_alimony,
    "line3_real_property_income": _line3_real_property_income,
    "line5a_pension_retirement": _line5a_pension_retirement,
    "line6a_unemployment": _line6a_unemployment,
    "line6b_child_support_alimony": _line6b_child_support_alimony,
    "line7_other_income": _line7_other_income,
    "other_income_label": _other_income_label,
    "line12b_annualized_cmi": _line12b_annualized_cmi,
    "line13a_median_income": _line13a_median_income,
    "median_comparison": _median_comparison,
    # Form 103B fee waiver derivations
    "fee_waiver_household_size": _fee_waiver_household_size,
    "fee_waiver_monthly_income": _fee_waiver_monthly_income,
    # Line 6 is Schedule J line 22c: one figure on both forms
    "fee_waiver_monthly_expenses": _schedule_j_total_expenses,
    "fee_waiver_noncash_assistance": _fee_waiver_noncash_assistance,
    "fee_waiver_benefit_types": _fee_waiver_benefit_types,
    # Schedule I income line item derivations
    "schedule_i_occupation_debtor1": _schedule_i_occupation_debtor1,
    "schedule_i_employer_debtor1": _schedule_i_employer_debtor1,
    "schedule_i_employer_street_debtor1": lambda s: _safe_debtor_attr(s, "employer_street", ""),
    "schedule_i_employer_city_debtor1": lambda s: _safe_debtor_attr(s, "employer_city", ""),
    "schedule_i_employer_state_debtor1": lambda s: _safe_debtor_attr(s, "employer_state", ""),
    "schedule_i_employer_zip_debtor1": lambda s: _safe_debtor_attr(s, "employer_zip", ""),
    "schedule_i_net_wages_debtor1": _schedule_i_net_wages_debtor1,
    "schedule_i_overtime_debtor1": _schedule_i_overtime_debtor1,
    "schedule_i_gross_income_debtor1": _schedule_i_gross_income_debtor1,
    "schedule_i_unemployment_debtor1": _schedule_i_unemployment_debtor1,
    "schedule_i_social_security_debtor1": _schedule_i_social_security_debtor1,
    "schedule_i_pension_debtor1": _schedule_i_pension_debtor1,
    "schedule_i_child_support_debtor1": _schedule_i_child_support_debtor1,
    "schedule_i_rental_debtor1": _schedule_i_rental_debtor1,
    "schedule_i_other_income_debtor1": _schedule_i_other_income_debtor1,
    "schedule_i_other_income_total_debtor1": _schedule_i_other_income_total_debtor1,
    "schedule_i_income_total": _schedule_i_income_total,
    # Schedule J expense line item derivations
    "schedule_j_rent_or_mortgage": lambda s: _expense_line(s, "rent_or_mortgage"),
    "schedule_j_utilities": lambda s: _expense_line(s, "utilities"),
    "schedule_j_utilities_label": lambda s: _expense_label(s, "utilities", "Utilities (combined)"),
    "schedule_j_home_maintenance": lambda s: _expense_line(s, "home_maintenance"),
    "schedule_j_food_and_groceries": lambda s: _expense_line(s, "food_and_groceries"),
    "schedule_j_childcare": lambda s: _expense_line(s, "childcare"),
    "schedule_j_clothing": lambda s: _expense_line(s, "clothing"),
    "schedule_j_medical_expenses": lambda s: _expense_line(s, "medical_expenses"),
    "schedule_j_vehicle_maintenance": lambda s: _expense_line(s, "vehicle_maintenance"),
    "schedule_j_vehicle_payment": lambda s: _expense_line(s, "vehicle_payment"),
    "schedule_j_vehicle_insurance": lambda s: _expense_line(s, "vehicle_insurance"),
    "schedule_j_insurance_not_deducted": lambda s: _expense_line(s, "insurance_not_deducted"),
    "schedule_j_insurance_label": lambda s: _expense_label(
        s, "insurance_not_deducted", "Insurance (combined)"
    ),
    "schedule_j_support_paid": lambda s: _expense_line(s, "child_support_paid"),
    "schedule_j_other_expenses": lambda s: _expense_line(s, "other_expenses"),
    "schedule_j_total_expenses": _schedule_j_total_expenses,
    # Line 23a is Schedule I line 12: one figure on both forms
    "schedule_j_total_income": _schedule_i_income_total,
    "schedule_j_monthly_net_income": _schedule_j_monthly_net_income,
    "schedule_j_joint_case": _schedule_j_joint_case,
    # Form 122A-2 means test expense deduction derivations
    "means_test_disposable_income": _means_test_disposable_income,
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
