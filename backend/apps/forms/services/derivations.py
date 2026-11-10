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

from apps.eligibility.cmi import (
    IncomeNotSplit,
    counted_spouse_income,
    current_monthly_income,
    household_cmi,
    household_members,
    is_above_median,
    spouse_monthly_income,
)
from apps.intake.asset_lines import (
    LINE_BY_KEY,
    LINES,
    ordered_assets,
    part_total,
    printed_answer,
    rows_on,
    rows_under_gate,
)
from apps.intake.claim_rows import community_answers
from apps.intake.claims import linked_payments, total_monthly_expenses
from apps.intake.household import count_family_size, dependents
from apps.intake.income import (
    floored_net,
    kind_sums,
    schedule_i_field,
    schedule_i_line4,
    uses_current,
)
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
    """122A-1's line: the sum of these Income step amounts, 0.00 when none was given (§9.6, Q27).

    Blank with no Income step row. An amount left empty counts as zero.
    """
    return _asked_amounts(_column(session, False), fields)


def _spouse_amounts(session: IntakeSession, *fields: str) -> str:
    """_income_amounts over the spouse's row: blank unless a spouse at home counts (3e1 spec §10)."""
    return _asked_amounts(_column(session, True), fields)


def _given_amounts(row, fields: tuple[str, ...]) -> str:
    if row is None:
        return ""
    given = [getattr(row, f) for f in fields if getattr(row, f) is not None]
    if not given:
        return ""
    return _fmt(sum(given, _ZERO))


def _asked_amounts(row, fields: tuple[str, ...]) -> str:
    """A line Schedule I or 122A-1 asks: blank with no row, 0.00 when none of these was given (§9.6, Q27)."""
    if row is None:
        return ""
    return _given_amounts(row, fields) or _fmt(_ZERO)


def _column(session: IntakeSession, spouse: bool):
    """The row Schedule I's column reads: the filer's, or the spouse's for a spouse at home."""
    return counted_spouse_income(session) if spouse else getattr(session, "income_info", None)


def _schedule_i_amounts(row, *fields: str) -> str:
    """_asked_amounts over the figures Schedule I uses: the current ones while "now different"."""
    if row is None:
        return ""
    return _asked_amounts(row, tuple(schedule_i_field(row, f) for f in fields))


def _figure(row, *fields: str) -> Decimal:
    """The sum of Schedule I's figures for these sources, a blank counting as 0."""
    return sum(
        (getattr(row, schedule_i_field(row, f)) or _ZERO for f in fields),
        _ZERO,
    )


def _deductions_total(row) -> Decimal:
    return sum((getattr(row, f) or _ZERO for f in row.DEDUCTION_FIELDS), _ZERO)


def _business_rental_net(row) -> Decimal:
    """8a: the floored business net plus the floored rental net on Schedule I's figures (C-12)."""
    entries = row.get_entries()
    current = uses_current(row)
    return floored_net(entries, "business", current=current) + floored_net(
        entries, "rental", current=current
    )


def _assistance(row) -> Decimal | None:
    """8f: the cash amount plus the known non-cash value under Yes, None when neither is known."""
    if row.assistance_answer != "yes":
        return _ZERO
    given = [v for v in (row.cash_assistance_amount, row.noncash_assistance_value) if v is not None]
    return sum(given, _ZERO) if given else None


def _line9(row) -> Decimal:
    """Line 9: 8a through 8h as each prints, a blank counting as zero."""
    return (
        _business_rental_net(row)
        + _figure(row, "monthly_interest_and_dividends")
        + _figure(row, "monthly_child_support", "monthly_alimony")
        + _figure(row, "monthly_unemployment")
        + _figure(row, "monthly_social_security")
        + (_assistance(row) or _ZERO)
        + _figure(row, "monthly_pension")
        + _figure(row, "monthly_other_income")
    )


def _line7(row) -> Decimal:
    """Line 7: line 4 less line 6. Below zero when the deductions are larger."""
    return schedule_i_line4(row) - _deductions_total(row)


def _spouse_rule(*fields: str) -> Callable[[IntakeSession], str]:
    """A spouse-column rule that adds up the same sources as its filer twin."""
    return lambda session: _spouse_amounts(session, *fields)


# ---------------------------------------------------------------------------
# Form 106Sum aggregation derivations
# ---------------------------------------------------------------------------


def _parts_total(session: IntakeSession, first: int, last: int) -> str:
    """The sum of the portions on Schedule A/B's Parts first to last (a null counts as zero)."""
    rows = ordered_assets(session)
    return _fmt(sum((part_total(rows, part) for part in range(first, last + 1)), Decimal(0)))


def _total_real_property(session: IntakeSession) -> str:
    return _parts_total(session, 1, 1)


def _total_personal_property(session: IntakeSession) -> str:
    return _parts_total(session, 2, 7)


def _total_assets(session: IntakeSession) -> str:
    return _parts_total(session, 1, 7)


def _total_secured_debts(session: IntakeSession) -> str:
    from apps.intake.models import DebtInfo

    qs = DebtInfo.objects.confirmed().filter(session=session, is_secured=True)
    return _fmt(_sum_encrypted(qs, "amount_owed"))


def _total_nonpriority_unsecured(session: IntakeSession) -> str:
    """
    E/F line 6j and 106Sum 3b: every unsecured debt.

    Which debts have priority is never asked (OQ-3), and a rule may not decide it, so
    every unsecured debt counts as nonpriority and the priority lines stay blank
    (step 2 spec §6.1 B5).
    """
    from apps.intake.models import DebtInfo

    qs = DebtInfo.objects.confirmed().filter(session=session, is_secured=False)
    return _fmt(_sum_encrypted(qs, "amount_owed"))


def _total_debts(session: IntakeSession) -> str:
    from apps.intake.models import DebtInfo

    qs = DebtInfo.objects.confirmed().filter(session=session)
    return _fmt(_sum_encrypted(qs, "amount_owed"))


def _total_other_assets(session: IntakeSession) -> str:
    return _parts_total(session, 7, 7)


def _cmi(session: IntakeSession) -> str:
    """The household's CMI (3e1 spec §5.3); no income at all is income not entered by source."""
    return _fmt(household_cmi(session))


def _total_monthly_expenses(session: IntakeSession) -> str:
    """Schedule J line 22c, which 22a, 23b, 106Sum line 5 and 103B line 6 copy: 0.00 with no Expenses row."""
    from apps.intake.models import ExpenseInfo

    try:
        return _fmt(total_monthly_expenses(session))
    except ExpenseInfo.DoesNotExist:
        return "0.00"


# ---------------------------------------------------------------------------
# Schedule A/B part totals, line 53 and each line's Yes or No, and the section questions of G and H
# ---------------------------------------------------------------------------


def _total_vehicles(session: IntakeSession) -> str:
    """Line 5, the total of Part 2."""
    return _parts_total(session, 2, 2)


def _total_household_items(session: IntakeSession) -> str:
    """Line 15, the total of Part 3."""
    return _parts_total(session, 3, 3)


def _total_financial_assets(session: IntakeSession) -> str:
    """Line 36, the total of Part 4."""
    return _parts_total(session, 4, 4)


def _total_business_property(session: IntakeSession) -> str:
    """Line 45, the total of Part 5."""
    return _parts_total(session, 5, 5)


def _total_farm_property(session: IntakeSession) -> str:
    """Line 52, the total of Part 6."""
    return _parts_total(session, 6, 6)


def _ab_line_2(session: IntakeSession) -> str:
    """Line 2: blank under line 1's "No. Go to Part 2", though line 55 still prints (§8.1)."""
    return _total_real_property(session) if rows_on(ordered_assets(session), "1") else ""


def _ab_line_45(session: IntakeSession) -> str:
    """Line 45: blank under line 37's "No. Go to Part 6", though line 59 still prints (§8.1)."""
    return (
        _total_business_property(session) if rows_under_gate(ordered_assets(session), "37") else ""
    )


def _ab_line_52(session: IntakeSession) -> str:
    """Line 52: blank under line 46's "No. Go to Part 7", though line 60 still prints (§8.1)."""
    return _total_farm_property(session) if rows_under_gate(ordered_assets(session), "46") else ""


def _ab_answer(key: str) -> Callable[[IntakeSession], str]:
    """A line's Yes/No box."""
    return lambda session: printed_answer(ordered_assets(session), key)


def _ab_shared_text(key: str, first: int | None = None) -> Callable[[IntakeSession], str]:
    """A line's one text box: its rows' words in order, or only its first rows' (3b spec §5)."""

    def rule(session: IntakeSession) -> str:
        rows = rows_on(ordered_assets(session), key)[:first]
        return "; ".join(row.description for row in rows if row.description)

    return rule


def _ab_kind_total(key: str, kind: str) -> Callable[[IntakeSession], str]:
    """A kind's one amount on 28 or 29: its rows' known values added, blank when none is known."""

    def rule(session: IntakeSession) -> str:
        rows = rows_on(ordered_assets(session), key, kind)
        known = [row.current_value for row in rows if row.current_value is not None]
        return money_or_blank(sum(known) if known else None)

    return rule


def _yes_if_any(rows) -> str:
    """A section's Yes/No question (owner Q8): "yes" when the filer listed one, else "no"."""
    return "yes" if rows.exists() else "no"


# ---------------------------------------------------------------------------
# Schedule E/F line 6 totals
# ---------------------------------------------------------------------------


def _total_student_loans(session: IntakeSession) -> str:
    """
    E/F line 6f and 106Sum 9d: the unsecured student loans.

    A student loan saved as secured is on Schedule D, not E/F (Ruling T16-a).
    """
    from apps.intake.models import DebtInfo

    qs = DebtInfo.objects.confirmed().filter(
        session=session, is_secured=False, debt_type="student_loan"
    )
    return _fmt(_sum_encrypted(qs, "amount_owed"))


def _total_other_nonpriority(session: IntakeSession) -> str:
    """E/F line 6i, 6j - 6f: lines 6g and 6h are never asked, so 6i holds the rest."""
    return _fmt(
        Decimal(_total_nonpriority_unsecured(session)) - Decimal(_total_student_loans(session))
    )


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

    count = DebtInfo.objects.confirmed().filter(session=session).count()
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


def _line5a_pension_retirement(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_pension")


def _line6a_unemployment(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_unemployment")


def _line6b_child_support_alimony(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_child_support")


def _line7_other_income(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_other_income")


def _line7_interest_and_dividends(session: IntakeSession) -> str:
    return _income_amounts(session, "monthly_interest_and_dividends")


def _kind_line(session: IntakeSession, spouse: bool, kind: str, part: str) -> str:
    """One of a kind's three 122A-1 figures on the six-month averages, never the current ones.

    `gross` and `expenses` are the summed entries, not floored; `net` is floored at $0.00
    (owner answer 1, §4.2). Blank with no row, 0.00 for an empty or unanswered list.
    """
    row = _column(session, spouse)
    if row is None:
        return ""
    entries = row.get_entries()
    if part == "net":
        return _fmt(floored_net(entries, kind))
    gross, expenses = kind_sums(entries, kind)
    return _fmt(gross if part == "gross" else expenses)


def _kind_rules(kind: str, line: str) -> dict[str, Callable[[IntakeSession], str]]:
    """The six rules, filer and spouse, for one 122A-1 line of business or rental figures."""
    rules = {}
    for part in ("gross", "expenses", "net"):
        name = f"line{line}_{kind}_{part}"
        rules[name] = lambda session, p=part: _kind_line(session, False, kind, p)
        rules[f"{name}_spouse"] = lambda session, p=part: _kind_line(session, True, kind, p)
    return rules


def _other_income_label(session: IntakeSession) -> str:
    """What the other income is, on 122A-1 line 10 (the averages): named only above $0.

    Schedule I 8h uses `schedule_i_other_income_label`.

    Either column's other income names it; the spouse's counts only for a spouse at home.
    """
    for row in (getattr(session, "income_info", None), counted_spouse_income(session)):
        other = None if row is None else row.monthly_other_income
        if other is not None and other > 0:
            return "Other income"
    return ""


def _line1_marital_status(session: IntakeSession) -> str:
    """Line 1's stored answer; each answer is a box state in the schema's choices."""
    return getattr(getattr(session, "income_info", None), "marital_status", None) or ""


def _line1_spouse_household(session: IntakeSession) -> str:
    """Line 1's second question, for a spouse who is not filing."""
    answer = _line1_marital_status(session)
    return {"married_together": "together", "married_separately": "separately"}.get(answer, "")


def _filer_cmi(session: IntakeSession) -> str:
    """Line 11, Column A: the filer's own CMI. No income row is income not entered by source."""
    income_info = getattr(session, "income_info", None)
    if income_info is None:
        raise IncomeNotSplit()
    return _fmt(current_monthly_income(income_info))


def _spouse_cmi(session: IntakeSession) -> str:
    """Line 11, Column B: the spouse's CMI, blank unless the filer lives with their spouse."""
    spouse = spouse_monthly_income(session)
    return "" if spouse is None else _fmt(spouse)


def _line11_annualized_income(session: IntakeSession) -> str:
    cmi = Decimal(_cmi(session))
    return _fmt(cmi * Decimal("12"))


def _line12b_annualized_cmi(session: IntakeSession) -> str:
    return _line11_annualized_income(session)


def _family_size(session: IntakeSession) -> str:
    """Line 13: the filer and everyone living with them, the count the means test sizes by."""
    return str(count_family_size(household_members(session)))


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


def _fee_waiver_family(session: IntakeSession):
    # fee_waiver reads Schedule I's rules from this module, so it is imported here, not at the top
    from apps.forms.services.fee_waiver import fee_waiver_family

    return fee_waiver_family(session)


def _fee_waiver_income(session: IntakeSession):
    # fee_waiver reads Schedule I's rules from this module, so it is imported here, not at the top
    from apps.forms.services.fee_waiver import fee_waiver_income

    return fee_waiver_income(session)


def _fee_waiver_noncash(session: IntakeSession):
    # fee_waiver reads Schedule I's rules from this module, so it is imported here, not at the top
    from apps.forms.services.fee_waiver import fee_waiver_noncash

    return fee_waiver_noncash(session)


def _count_or_blank(n: int) -> str:
    return str(n) if n > 0 else ""


def money_or_blank(amount: Decimal | None) -> str:
    return "" if amount is None else _fmt(amount)


def _yes_tick(answer: str) -> str:
    """A single box's answer: "true" for Yes, blank for No or unanswered."""
    return "true" if answer == "yes" else ""


def _spouse_street(answers: dict) -> str:
    return ", ".join(filter(None, (answers["spouse_street"], answers["spouse_street_2"])))


# ---------------------------------------------------------------------------
# Form 101 line 8 and Form 103B lines 4–9: the filing-fee page's answers
# ---------------------------------------------------------------------------


def _filing_fee(session: IntakeSession):
    return getattr(session, "filing_fee", None)


def _fee_answer(name: str) -> Callable[[IntakeSession], str]:
    """The stored answer, or "" while it is unanswered or there is no FilingFee row."""

    def rule(session: IntakeSession) -> str:
        fee = _filing_fee(session)
        return (getattr(fee, name) or "") if fee is not None else ""

    return rule


def _fee_text(name: str, under: str | None = None) -> Callable[[IntakeSession], str]:
    """
    The text, stripped. With under, only while that yes/no answer is "yes": a text kept
    after the answer moved to No stays stored and prints nothing.
    """

    def rule(session: IntakeSession) -> str:
        fee = _filing_fee(session)
        if fee is None or (under is not None and getattr(fee, under) != "yes"):
            return ""
        return (getattr(fee, name) or "").strip()

    return rule


# ---------------------------------------------------------------------------
# Schedule I income line item derivations
# ---------------------------------------------------------------------------


def _schedule_i_occupation_debtor1(session: IntakeSession) -> str:
    return _safe_debtor_attr(session, "occupation", "")


def _schedule_i_employer_debtor1(session: IntakeSession) -> str:
    return _safe_debtor_attr(session, "employer_name", "")


def _on_row(session: IntakeSession, spouse: bool, rule: Callable) -> str:
    """One Schedule I figure for one column: blank with no row, else the row rule's."""
    row = _column(session, spouse)
    return "" if row is None else rule(row)


def _money(figure: Callable) -> Callable:
    """A row rule that prints a figure, through _fmt."""
    return lambda row: _fmt(figure(row))


def _line10(row) -> Decimal:
    """Line 10, one column: line 7 + line 9, Social Security included (C1), unlike CMI."""
    return _line7(row) + _line9(row)


def _payroll_other_specify(session: IntakeSession) -> str:
    """5h's Specify: each counted person's words, kept only while their 5h is above 0."""
    words = []
    for spouse in (False, True):
        row = _column(session, spouse)
        if row is not None and (row.payroll_other or _ZERO) > 0:
            words.append((row.payroll_other_specify or "").strip())
    return "; ".join(w for w in words if w)


def _assistance_specify(session: IntakeSession) -> str:
    """8f's Specify: each counted person's cash then non-cash kind, only while they answered Yes."""
    words = []
    for spouse in (False, True):
        row = _column(session, spouse)
        if row is not None and row.assistance_answer == "yes":
            words += [(row.cash_assistance_kind or "").strip()]
            words += [(row.noncash_assistance_kind or "").strip()]
    return "; ".join(w for w in words if w)


def _schedule_i_other_income_label(session: IntakeSession) -> str:
    """8h's words follow the 8h figure Schedule I uses, named only above $0 (either column)."""
    for spouse in (False, True):
        row = _column(session, spouse)
        if row is not None and _figure(row, "monthly_other_income") > 0:
            return "Other income"
    return ""


def _schedule_i_income_total(session: IntakeSession) -> str:
    """
    Schedule I lines 10 and 12: both columns, Social Security included (C1), unlike CMI.

    The spouse's column counts only for a filer living with their spouse (3e1 spec §10.2). A
    blank column counts as zero, and the total is blank only when both are. Line 11 is never
    asked and counts as zero (step 2 spec §6.1).
    """
    columns = (
        _on_row(session, False, _money(_line10)),
        _on_row(session, True, _money(_line10)),
    )
    if columns == ("", ""):
        return ""
    return _fmt(sum((Decimal(column or "0") for column in columns), _ZERO))


# Each Schedule I line, one column: (rule name, the row's rule). A _debtor1 and a _spouse twin
# of each go into DERIVATIONS.
_DEDUCTION_LINES = {
    "payroll_tax": "payroll_tax",
    "payroll_mandatory_retirement": "payroll_mandatory_retirement",
    "payroll_voluntary_retirement": "payroll_voluntary_retirement",
    "payroll_retirement_loan": "payroll_retirement_loan",
    "payroll_insurance": "payroll_insurance",
    "payroll_support": "payroll_support",
    "payroll_union_dues": "payroll_union_dues",
    "payroll_other": "payroll_other",
}
SCHEDULE_I_LINES: dict[str, Callable] = {
    "net_wages": lambda row: _schedule_i_amounts(row, "monthly_gross_wages", "monthly_tips"),
    "overtime": lambda row: _schedule_i_amounts(row, "monthly_overtime"),
    "gross_income": lambda row: _schedule_i_amounts(
        row, "monthly_gross_wages", "monthly_tips", "monthly_overtime"
    ),
    **{
        name: (lambda row, field=field: _asked_amounts(row, (field,)))
        for name, field in _DEDUCTION_LINES.items()
    },
    "total_deductions": lambda row: _asked_amounts(row, tuple(row.DEDUCTION_FIELDS)),
    "take_home_pay": _money(_line7),
    "business_rental_net": _money(_business_rental_net),
    "interest": lambda row: _schedule_i_amounts(row, "monthly_interest_and_dividends"),
    "child_support": lambda row: _schedule_i_amounts(
        row, "monthly_child_support", "monthly_alimony"
    ),
    "unemployment": lambda row: _schedule_i_amounts(row, "monthly_unemployment"),
    "social_security": lambda row: _schedule_i_amounts(row, "monthly_social_security"),
    "assistance": lambda row: "" if _assistance(row) is None else _fmt(_assistance(row)),
    "pension": lambda row: _schedule_i_amounts(row, "monthly_pension"),
    "other_income": lambda row: _schedule_i_amounts(row, "monthly_other_income"),
    "other_income_total": _money(_line9),
    "income_total": _money(_line10),
}


def _schedule_i_twins() -> dict[str, Callable[[IntakeSession], str]]:
    rules = {}
    for name, rule in SCHEDULE_I_LINES.items():
        rules[f"schedule_i_{name}_debtor1"] = lambda s, rule=rule: _on_row(s, False, rule)
        rules[f"schedule_i_{name}_spouse"] = lambda s, rule=rule: _on_row(s, True, rule)
    return rules


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


def _linked_amount(amount: Decimal) -> str:
    """A linked payment prints only above $0, as every Schedule J line does (3c4 §8.1)."""
    return _fmt(amount) if amount > 0 else ""


def _schedule_j_rent_or_mortgage(session: IntakeSession) -> str:
    """J 4: the typed rent, a first mortgage and a vehicle lease on the home (3c4 R3)."""
    linked = linked_payments(session)
    return _linked_amount(
        _expense_amount(session, "rent_or_mortgage") + linked.first_mortgage + linked.home_lease
    )


def _schedule_j_installment_words(session: IntakeSession, line: str) -> str:
    """17c's and 17d's fixed words, printed only beside the line's amount (B45)."""
    linked = linked_payments(session)
    return linked.j17_words[line] if linked.j17[line] > 0 else ""


def _expense_label(session: IntakeSession, field: str, label: str) -> str:
    """An "Other. Specify:" line's text, printed only when its amount prints (Q4)."""
    return label if _expense_amount(session, field) > 0 else ""


def _expense_text(session: IntakeSession, field: str, text_field: str) -> str:
    """A "Specify" box's text, the filer's own, printed only when its amount prints."""
    if _expense_amount(session, field) <= 0:
        return ""
    return (getattr(session.expense_info, text_field) or "").strip()


def _schedule_j_expenses_include_others(session: IntakeSession) -> str:
    """Line 3 is the filer's own answer; with no row or no answer it stays blank."""
    expense_info = getattr(session, "expense_info", None)
    return "" if expense_info is None else (expense_info.expenses_include_others or "")


def _schedule_j_monthly_net_income(session: IntakeSession) -> str:
    """
    Line 23c, 23a - 23b: blank while 23a is, and below zero when expenses pass income.

    23a is Schedule I line 12 and 23b is line 22c, so 23c is computed from those rules.
    """
    income = _schedule_i_income_total(session)
    if income == "":
        return ""
    return _fmt(Decimal(income) - Decimal(_total_monthly_expenses(session)))


def _schedule_j_joint_case(session: IntakeSession) -> str:
    """
    Line 1: "no" for every session.

    No step offers joint filing and Complete refuses a case the spouse files too (3e1 spec
    §7, DIG-177), so `filing_type` has no reader left.
    """
    return "no"


def _schedule_j_has_dependents(session: IntakeSession) -> str:
    """
    Line 2's "Do you have dependents?": "yes" when the rows below it list anyone.

    An unanswered list raises IncomeStepGap (from household_members) rather than swear to
    a No the filer never gave.
    """
    return "yes" if dependents(household_members(session)) else "no"


def _county(session: IntakeSession) -> str:
    household = getattr(session, "household", None)
    return (household.county if household else "") or ""


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
    "family_size": _family_size,
    "first_name": lambda s: _safe_debtor_attr(s, "first_name"),
    "middle_name": lambda s: _safe_debtor_attr(s, "middle_name"),
    "last_name": lambda s: _safe_debtor_attr(s, "last_name"),
    "ssn_last_4": lambda s: (_safe_debtor_attr(s, "ssn"))[-4:],
    "street_address": lambda s: _safe_debtor_attr(s, "street_address"),
    "city": lambda s: _safe_debtor_attr(s, "city"),
    "state": lambda s: _safe_debtor_attr(s, "state"),
    "zip_code": lambda s: _safe_debtor_attr(s, "zip_code"),
    "county": _county,
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
    # Schedule A/B part totals, line 53 and each line's Yes or No, and the section questions of G
    # and H
    "total_vehicles": _total_vehicles,
    "total_household_items": _total_household_items,
    "total_financial_assets": _total_financial_assets,
    "total_business_property": _total_business_property,
    "total_farm_property": _total_farm_property,
    "ab_line_2": _ab_line_2,
    "ab_line_45": _ab_line_45,
    "ab_line_52": _ab_line_52,
    **{f"ab_has_{line.key}": _ab_answer(line.key) for line in LINES},
    "ab_line_28_text": _ab_shared_text("28"),
    "ab_line_29_text": _ab_shared_text("29"),
    "ab_line_53_text": _ab_shared_text("53", LINE_BY_KEY["53"].capacity),
    **{
        f"ab_line_{key}_{kind}": _ab_kind_total(key, kind)
        for key in ("28", "29")
        for kind, _ in LINE_BY_KEY[key].kinds
    },
    "has_executory_contracts": lambda s: _yes_if_any(s.executory_contracts.all()),
    "has_codebtors": lambda s: _yes_if_any(s.codebtors.all()),
    # Schedules D and E/F: the section questions and E/F's line 6 totals
    "has_secured_debts": lambda s: _yes_if_any(s.debts.confirmed().filter(is_secured=True)),
    # Every unsecured debt is nonpriority until priority is asked (OQ-3), as on line 6j.
    "has_nonpriority_debts": lambda s: _yes_if_any(s.debts.confirmed().filter(is_secured=False)),
    "total_student_loans": _total_student_loans,
    "total_other_nonpriority": _total_other_nonpriority,
    # Form 101 lines 18-20
    "creditor_count_range": _creditor_count_range,
    "total_assets_range": _total_assets_range,
    "total_debts_range": _total_debts_range,
    # Form 122A-1 means test derivations
    "line1_wages": _line1_wages,
    "line3_alimony": _line3_alimony,
    "line5a_pension_retirement": _line5a_pension_retirement,
    "line6a_unemployment": _line6a_unemployment,
    "line6b_child_support_alimony": _line6b_child_support_alimony,
    "line7_other_income": _line7_other_income,
    "line7_interest_and_dividends": _line7_interest_and_dividends,
    **_kind_rules("business", "5"),
    **_kind_rules("rental", "6"),
    "line1_marital_status": _line1_marital_status,
    "line1_spouse_household": _line1_spouse_household,
    "filer_cmi": _filer_cmi,
    "spouse_cmi": _spouse_cmi,
    "line1_wages_spouse": _spouse_rule("monthly_gross_wages", "monthly_tips", "monthly_overtime"),
    "line3_alimony_spouse": _spouse_rule("monthly_alimony"),
    "line6b_child_support_alimony_spouse": _spouse_rule("monthly_child_support"),
    "line7_interest_and_dividends_spouse": _spouse_rule("monthly_interest_and_dividends"),
    "line6a_unemployment_spouse": _spouse_rule("monthly_unemployment"),
    "line5a_pension_retirement_spouse": _spouse_rule("monthly_pension"),
    "line7_other_income_spouse": _spouse_rule("monthly_other_income"),
    "other_income_label": _other_income_label,
    "line12b_annualized_cmi": _line12b_annualized_cmi,
    "line13a_median_income": _line13a_median_income,
    "median_comparison": _median_comparison,
    # Form 103B lines 1-3: the household list, Schedule I line 10 and 8f (3f spec §8.2)
    "fee_waiver_family_size": lambda s: str(_fee_waiver_family(s).total),
    "fee_waiver_spouse_counted": lambda s: "true" if _fee_waiver_family(s).spouse_counted else "",
    "fee_waiver_has_dependents": lambda s: "true" if _fee_waiver_family(s).dependents > 0 else "",
    "fee_waiver_dependents_count": lambda s: _count_or_blank(_fee_waiver_family(s).dependents),
    "fee_waiver_income_you": lambda s: _fmt(_fee_waiver_income(s).you),
    "fee_waiver_income_spouse": lambda s: money_or_blank(_fee_waiver_income(s).spouse),
    "fee_waiver_income_subtotal": lambda s: _fmt(_fee_waiver_income(s).subtotal),
    "fee_waiver_income_noncash": lambda s: money_or_blank(_fee_waiver_income(s).noncash),
    "fee_waiver_income_total": lambda s: _fmt(_fee_waiver_income(s).total),
    "fee_waiver_noncash_answer": lambda s: _fee_waiver_noncash(s)[0],
    "fee_waiver_noncash_kinds": lambda s: _fee_waiver_noncash(s)[1],
    # Form 101 line 8 and 103B lines 4, 5, 7 and 9 (3f spec §8)
    "fee_payment_choice": _fee_answer("payment_choice"),
    "fee_waiver_income_change": _fee_answer("income_change_answer"),
    "fee_waiver_income_change_explanation": _fee_text(
        "income_change_explanation", under="income_change_answer"
    ),
    "fee_waiver_installments_explanation": _fee_text("installments_explanation"),
    "fee_waiver_others_covered": _fee_answer("others_covered_answer"),
    "fee_waiver_others_covered_who": _fee_text("others_covered_who", under="others_covered_answer"),
    "fee_waiver_expense_change": _fee_answer("expense_change_answer"),
    "fee_waiver_expense_change_explanation": _fee_text(
        "expense_change_explanation", under="expense_change_answer"
    ),
    # Line 6 is Schedule J line 22c: one figure on both forms
    "fee_waiver_monthly_expenses": _total_monthly_expenses,
    # Schedule I income line item derivations
    "schedule_i_occupation_debtor1": _schedule_i_occupation_debtor1,
    "schedule_i_employer_debtor1": _schedule_i_employer_debtor1,
    "schedule_i_employer_street_debtor1": lambda s: _safe_debtor_attr(s, "employer_street", ""),
    "schedule_i_employer_city_debtor1": lambda s: _safe_debtor_attr(s, "employer_city", ""),
    "schedule_i_employer_state_debtor1": lambda s: _safe_debtor_attr(s, "employer_state", ""),
    "schedule_i_employer_zip_debtor1": lambda s: _safe_debtor_attr(s, "employer_zip", ""),
    **_schedule_i_twins(),
    "schedule_i_income_total": _schedule_i_income_total,
    "schedule_i_payroll_other_specify": _payroll_other_specify,
    "schedule_i_assistance_specify": _assistance_specify,
    "schedule_i_other_income_label": _schedule_i_other_income_label,
    # Schedule J expense line item derivations
    "schedule_j_rent_or_mortgage": _schedule_j_rent_or_mortgage,
    "schedule_j_additional_mortgage": lambda s: _linked_amount(
        linked_payments(s).additional_mortgage
    ),
    "schedule_j_utilities": lambda s: _expense_line(s, "utilities"),
    "schedule_j_utilities_label": lambda s: _expense_label(s, "utilities", "Utilities (combined)"),
    "schedule_j_home_maintenance": lambda s: _expense_line(s, "home_maintenance"),
    "schedule_j_food_and_groceries": lambda s: _expense_line(s, "food_and_groceries"),
    "schedule_j_childcare": lambda s: _expense_line(s, "childcare"),
    "schedule_j_clothing": lambda s: _expense_line(s, "clothing"),
    "schedule_j_medical_expenses": lambda s: _expense_line(s, "medical_expenses"),
    "schedule_j_vehicle_maintenance": lambda s: _expense_line(s, "vehicle_maintenance"),
    "schedule_j_vehicle_payment": lambda s: _linked_amount(linked_payments(s).j17["17a"]),
    "schedule_j_vehicle_2_payment": lambda s: _linked_amount(linked_payments(s).j17["17b"]),
    "schedule_j_installment_c": lambda s: _linked_amount(linked_payments(s).j17["17c"]),
    "schedule_j_installment_d": lambda s: _linked_amount(linked_payments(s).j17["17d"]),
    "schedule_j_installment_c_words": lambda s: _schedule_j_installment_words(s, "17c"),
    "schedule_j_installment_d_words": lambda s: _schedule_j_installment_words(s, "17d"),
    "schedule_j_vehicle_insurance": lambda s: _expense_line(s, "vehicle_insurance"),
    "schedule_j_insurance_not_deducted": lambda s: _expense_line(s, "insurance_not_deducted"),
    "schedule_j_insurance_label": lambda s: _expense_label(
        s, "insurance_not_deducted", "Insurance (combined)"
    ),
    "schedule_j_support_paid": lambda s: _expense_line(s, "child_support_paid"),
    "schedule_j_other_expenses": lambda s: _expense_line(s, "other_expenses"),
    "schedule_j_expenses_include_others": _schedule_j_expenses_include_others,
    "schedule_j_real_estate_taxes": lambda s: _expense_line(s, "real_estate_taxes"),
    "schedule_j_home_insurance": lambda s: _expense_line(s, "home_insurance"),
    "schedule_j_hoa_dues": lambda s: _expense_line(s, "hoa_dues"),
    "schedule_j_personal_care": lambda s: _expense_line(s, "personal_care"),
    "schedule_j_entertainment": lambda s: _expense_line(s, "entertainment"),
    "schedule_j_charitable_contributions": lambda s: _expense_line(s, "charitable_contributions"),
    "schedule_j_taxes_not_deducted": lambda s: _expense_line(s, "taxes_not_deducted"),
    "schedule_j_taxes_label": lambda s: _expense_text(s, "taxes_not_deducted", "taxes_specify"),
    "schedule_j_support_others": lambda s: _expense_line(s, "support_others"),
    "schedule_j_support_others_label": lambda s: _expense_text(
        s, "support_others", "support_others_specify"
    ),
    "schedule_j_other_property_mortgages": lambda s: _linked_amount(
        linked_payments(s).other_real_property
    ),
    "schedule_j_other_property_taxes": lambda s: _expense_line(s, "other_property_taxes"),
    "schedule_j_other_property_insurance": lambda s: _expense_line(s, "other_property_insurance"),
    "schedule_j_other_property_upkeep": lambda s: _expense_line(s, "other_property_upkeep"),
    "schedule_j_other_property_hoa_dues": lambda s: _expense_line(s, "other_property_hoa_dues"),
    "schedule_j_other_expenses_label": lambda s: _expense_text(
        s, "other_expenses", "other_expenses_specify"
    ),
    "schedule_j_total_expenses": _total_monthly_expenses,
    # Line 23a is Schedule I line 12: one figure on both forms
    "schedule_j_total_income": _schedule_i_income_total,
    "schedule_j_monthly_net_income": _schedule_j_monthly_net_income,
    "schedule_j_joint_case": _schedule_j_joint_case,
    "schedule_j_has_dependents": _schedule_j_has_dependents,
    # Form 122A-2 means test expense deduction derivations
    "means_test_disposable_income": _means_test_disposable_income,
    # Schedule H line 2 (3c5): the community property answers, as the claims step asks them
    "schedule_h_community_lived": lambda s: _yes_tick(community_answers(s)["lived"]),
    "schedule_h_spouse_lived_with": lambda s: _yes_tick(community_answers(s)["spouse_lived_with"]),
    "schedule_h_community_state": lambda s: community_answers(s)["state"],
    "schedule_h_spouse_name": lambda s: community_answers(s)["spouse_name"],
    "schedule_h_spouse_street": lambda s: _spouse_street(community_answers(s)),
    "schedule_h_spouse_city": lambda s: community_answers(s)["spouse_city"],
    "schedule_h_spouse_state": lambda s: community_answers(s)["spouse_state"],
    "schedule_h_spouse_zip": lambda s: community_answers(s)["spouse_zip"],
}


# ---------------------------------------------------------------------------
# RULE_FIXES — where the filer changes what a rule prints (3a2 spec §4.5)
# ---------------------------------------------------------------------------

# Every rule bound to a text or choice box, with where a refusal of its value (a letter
# the form can't print, a value too long for its box) sends the filer: the wizard step
# ({"step": <a WIZARD_STEPS key>}) or page ({"page": <path>}) that holds the rule's input.
# {} links nowhere: no filer edits the input. test_rule_fixes.py fails on a bound rule
# missing here.
RULE_FIXES: dict[str, dict[str, str]] = {
    # Your Information
    "full_name": {"step": "debtor_info"},
    "first_name": {"step": "debtor_info"},
    "middle_name": {"step": "debtor_info"},
    "last_name": {"step": "debtor_info"},
    "street_address": {"step": "debtor_info"},
    "city": {"step": "debtor_info"},
    "state": {"step": "debtor_info"},
    "zip_code": {"step": "debtor_info"},
    "county": {"step": "debtor_info"},
    "phone": {"step": "debtor_info"},
    "email": {"step": "debtor_info"},
    "ssn_last_4": {"step": "debtor_info"},
    "ssn_formatted": {"step": "debtor_info"},
    # Income
    "family_size": {"step": "income_info"},
    "cmi": {"step": "income_info"},
    "line12b_annualized_cmi": {"step": "income_info"},
    "line1_wages": {"step": "income_info"},
    "line3_alimony": {"step": "income_info"},
    "line7_interest_and_dividends": {"step": "income_info"},
    "line5a_pension_retirement": {"step": "income_info"},
    "line6a_unemployment": {"step": "income_info"},
    "line6b_child_support_alimony": {"step": "income_info"},
    "line7_other_income": {"step": "income_info"},
    "filer_cmi": {"step": "income_info"},
    "spouse_cmi": {"step": "income_info"},
    "line1_wages_spouse": {"step": "income_info"},
    "line3_alimony_spouse": {"step": "income_info"},
    "line6b_child_support_alimony_spouse": {"step": "income_info"},
    "line7_interest_and_dividends_spouse": {"step": "income_info"},
    "line5_business_gross": {"step": "income_info"},
    "line5_business_gross_spouse": {"step": "income_info"},
    "line5_business_expenses": {"step": "income_info"},
    "line5_business_expenses_spouse": {"step": "income_info"},
    "line5_business_net": {"step": "income_info"},
    "line5_business_net_spouse": {"step": "income_info"},
    "line6_rental_gross": {"step": "income_info"},
    "line6_rental_gross_spouse": {"step": "income_info"},
    "line6_rental_expenses": {"step": "income_info"},
    "line6_rental_expenses_spouse": {"step": "income_info"},
    "line6_rental_net": {"step": "income_info"},
    "line6_rental_net_spouse": {"step": "income_info"},
    "line6a_unemployment_spouse": {"step": "income_info"},
    "line5a_pension_retirement_spouse": {"step": "income_info"},
    "line7_other_income_spouse": {"step": "income_info"},
    "other_income_label": {"step": "income_info"},
    "schedule_i_net_wages_debtor1": {"step": "income_info"},
    "schedule_i_overtime_debtor1": {"step": "income_info"},
    "schedule_i_gross_income_debtor1": {"step": "income_info"},
    "schedule_i_unemployment_debtor1": {"step": "income_info"},
    "schedule_i_social_security_debtor1": {"step": "income_info"},
    "schedule_i_pension_debtor1": {"step": "income_info"},
    "schedule_i_child_support_debtor1": {"step": "income_info"},
    "schedule_i_other_income_debtor1": {"step": "income_info"},
    "schedule_i_other_income_total_debtor1": {"step": "income_info"},
    "schedule_i_income_total": {"step": "income_info"},
    "schedule_i_income_total_debtor1": {"step": "income_info"},
    "schedule_i_net_wages_spouse": {"step": "income_info"},
    "schedule_i_overtime_spouse": {"step": "income_info"},
    "schedule_i_gross_income_spouse": {"step": "income_info"},
    "schedule_i_child_support_spouse": {"step": "income_info"},
    "schedule_i_unemployment_spouse": {"step": "income_info"},
    "schedule_i_social_security_spouse": {"step": "income_info"},
    "schedule_i_pension_spouse": {"step": "income_info"},
    "schedule_i_other_income_spouse": {"step": "income_info"},
    "schedule_i_other_income_total_spouse": {"step": "income_info"},
    "schedule_i_income_total_spouse": {"step": "income_info"},
    # 103B lines 1-3 read the household list, Schedule I line 10 and 8f
    "fee_waiver_family_size": {"step": "income_info"},
    "fee_waiver_dependents_count": {"step": "income_info"},
    "fee_waiver_income_you": {"step": "income_info"},
    "fee_waiver_income_spouse": {"step": "income_info"},
    "fee_waiver_income_subtotal": {"step": "income_info"},
    "fee_waiver_income_noncash": {"step": "income_info"},
    "fee_waiver_income_total": {"step": "income_info"},
    "fee_waiver_noncash_kinds": {"step": "income_info"},
    # Lines that read both the Income step and Take-home pay link to the earlier one (§17 Call 33)
    "schedule_i_take_home_pay_debtor1": {"step": "income_info"},
    "schedule_i_take_home_pay_spouse": {"step": "income_info"},
    "schedule_i_business_rental_net_debtor1": {"step": "income_info"},
    "schedule_i_business_rental_net_spouse": {"step": "income_info"},
    "schedule_i_interest_debtor1": {"step": "income_info"},
    "schedule_i_interest_spouse": {"step": "income_info"},
    "schedule_i_assistance_debtor1": {"step": "income_info"},
    "schedule_i_assistance_spouse": {"step": "income_info"},
    "schedule_i_assistance_specify": {"step": "income_info"},
    "schedule_i_other_income_label": {"step": "income_info"},
    # Payroll deductions: asked on the Take-home pay step
    **{
        f"schedule_i_{name}_{column}": {"step": "take_home_pay"}
        for name in (*_DEDUCTION_LINES, "total_deductions")
        for column in ("debtor1", "spouse")
    },
    "schedule_i_payroll_other_specify": {"step": "take_home_pay"},
    "schedule_j_total_income": {"step": "income_info"},
    # Income less expenses: the earlier of its two steps
    "schedule_j_monthly_net_income": {"step": "income_info"},
    # Expenses
    "schedule_j_rent_or_mortgage": {"step": "debts"},
    "schedule_j_additional_mortgage": {"step": "debts"},
    "schedule_j_utilities": {"step": "expense_info"},
    "schedule_j_utilities_label": {"step": "expense_info"},
    "schedule_j_home_maintenance": {"step": "expense_info"},
    "schedule_j_food_and_groceries": {"step": "expense_info"},
    "schedule_j_childcare": {"step": "expense_info"},
    "schedule_j_clothing": {"step": "expense_info"},
    "schedule_j_medical_expenses": {"step": "expense_info"},
    "schedule_j_vehicle_maintenance": {"step": "expense_info"},
    "schedule_j_vehicle_payment": {"step": "debts"},
    "schedule_j_vehicle_2_payment": {"step": "debts"},
    "schedule_j_installment_c": {"step": "debts"},
    "schedule_j_installment_d": {"step": "debts"},
    "schedule_j_installment_c_words": {"step": "debts"},
    "schedule_j_installment_d_words": {"step": "debts"},
    "schedule_j_vehicle_insurance": {"step": "expense_info"},
    "schedule_j_insurance_not_deducted": {"step": "expense_info"},
    "schedule_j_insurance_label": {"step": "expense_info"},
    "schedule_j_support_paid": {"step": "expense_info"},
    "schedule_j_other_expenses": {"step": "expense_info"},
    "schedule_j_expenses_include_others": {"step": "expense_info"},
    "schedule_j_real_estate_taxes": {"step": "expense_info"},
    "schedule_j_home_insurance": {"step": "expense_info"},
    "schedule_j_hoa_dues": {"step": "expense_info"},
    "schedule_j_personal_care": {"step": "expense_info"},
    "schedule_j_entertainment": {"step": "expense_info"},
    "schedule_j_charitable_contributions": {"step": "expense_info"},
    "schedule_j_taxes_not_deducted": {"step": "expense_info"},
    "schedule_j_support_others": {"step": "expense_info"},
    "schedule_j_other_property_mortgages": {"step": "debts"},
    "schedule_j_other_property_taxes": {"step": "expense_info"},
    "schedule_j_other_property_insurance": {"step": "expense_info"},
    "schedule_j_other_property_upkeep": {"step": "expense_info"},
    "schedule_j_other_property_hoa_dues": {"step": "expense_info"},
    "schedule_j_taxes_label": {"step": "expense_info"},
    "schedule_j_support_others_label": {"step": "expense_info"},
    "schedule_j_other_expenses_label": {"step": "expense_info"},
    "schedule_j_total_expenses": {"step": "expense_info"},
    "total_monthly_expenses": {"step": "expense_info"},
    # 103B line 6 is Schedule J line 22c, from the Expenses step
    "fee_waiver_monthly_expenses": {"step": "expense_info"},
    # Assets
    "total_real_property": {"step": "assets"},
    "total_personal_property": {"step": "assets"},
    "total_assets": {"step": "assets"},
    "total_other_assets": {"step": "assets"},
    "total_vehicles": {"step": "assets"},
    "total_household_items": {"step": "assets"},
    "total_financial_assets": {"step": "assets"},
    "total_business_property": {"step": "assets"},
    "total_farm_property": {"step": "assets"},
    "ab_line_2": {"step": "assets"},
    "ab_line_45": {"step": "assets"},
    "ab_line_52": {"step": "assets"},
    **{f"ab_has_{line.key}": {"step": "assets"} for line in LINES},
    "ab_line_28_text": {"step": "assets"},
    "ab_line_29_text": {"step": "assets"},
    "ab_line_53_text": {"step": "assets"},
    **{
        f"ab_line_{key}_{kind}": {"step": "assets"}
        for key in ("28", "29")
        for kind, _ in LINE_BY_KEY[key].kinds
    },
    # Amounts Owed
    "total_secured_debts": {"step": "debts"},
    "total_secured_claims": {"step": "debts"},
    "total_debts": {"step": "debts"},
    "total_nonpriority_unsecured": {"step": "debts"},
    "total_student_loans": {"step": "debts"},
    "total_other_nonpriority": {"step": "debts"},
    # The filing-fee page (3f spec §7)
    "fee_waiver_income_change_explanation": {"page": "/filing-fee"},
    "fee_waiver_installments_explanation": {"page": "/filing-fee"},
    "fee_waiver_others_covered_who": {"page": "/filing-fee"},
    "fee_waiver_expense_change_explanation": {"page": "/filing-fee"},
    # No link. The district and its median income table come from DigniFi's own data.
    # The Schedule I occupation and employer address read fields no model has, so they
    # always print blank.
    "district_name": {},
    "line13a_median_income": {},
    "schedule_i_occupation_debtor1": {},
    "schedule_i_employer_street_debtor1": {},
    "schedule_i_employer_city_debtor1": {},
    "schedule_i_employer_state_debtor1": {},
    "schedule_i_employer_zip_debtor1": {},
    # Schedule H line 2: the spouse's name and address are entered on the Codebtors step
    "schedule_h_community_state": {"step": "codebtors"},
    "schedule_h_spouse_name": {"step": "codebtors"},
    "schedule_h_spouse_street": {"step": "codebtors"},
    "schedule_h_spouse_city": {"step": "codebtors"},
    "schedule_h_spouse_state": {"step": "codebtors"},
    "schedule_h_spouse_zip": {"step": "codebtors"},
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
