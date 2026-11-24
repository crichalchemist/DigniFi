"""
Factual/clerical derivations (DERIVATIONS) and section-applicability
predicates (PREDICATES) for the fill engine.

UPL boundary: these encode ONLY facts and clerical transforms. A rule may
apply a comparison the form itself spells out (122A-1 line 14: line 12b
against line 13), but no rule may choose exemptions, decide priority, or
answer anything the form leaves to the filer — those are ``asked`` +
``legal_review`` in the schema. The one exception is ANSWER_BOX_RULES: a
``legal_review`` box a rule ticks only for the filer's own stored choice.
"""

from __future__ import annotations

import re
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
from apps.eligibility.means_lines import (
    MILITARY_EXCLUSION,
    SUPP_OUTCOMES,
    supp_line_3_reached,
)
from apps.forms.services.answer_records import PETITION_STEP_OF_KEY, is_itin, record_value
from apps.intake.asset_lines import (
    LINE_BY_KEY,
    LINES,
    ordered_assets,
    part_total,
    printed_answer,
    rows_on,
    rows_under_gate,
)
from apps.intake.claim_rows import claim_rows, community_answers
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
from apps.intake.schedule_i import married_together

_ZERO = Decimal("0.00")
_TWO_PLACES = Decimal("0.01")


# ---------------------------------------------------------------------------
# Safe accessor helpers
# ---------------------------------------------------------------------------


def _debtor_text(session: IntakeSession, attr: str) -> str:
    """A DebtorInfo column as text, "" for None. A session with no DebtorInfo raises: Complete
    refuses one, so a form reaching it is DigniFi's defect, never a blank identity (4c-R11)."""
    value = getattr(session.debtor_info, attr)
    return "" if value is None else str(value)


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
    E/F line 6j and 106Sum 3b: the debts in Part 2.

    Part 2 holds the confirmed unsecured debts the filer answered "No" or "Not sure" to, or
    has not answered; the filer's own answer moves a debt to Part 1, and no rule decides it
    (3d spec §6).
    """
    return _fmt(sum((row.debt.amount_owed for row in claim_rows(session).unsecured), Decimal("0")))


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
    E/F line 6f and 106Sum 9d: the student loans in Part 2.

    A student loan saved as secured is on Schedule D, not E/F (Ruling T16-a), and one the
    filer answered with a kind is in Part 1, so it leaves 6f.
    """
    return _fmt(
        sum(
            (
                row.debt.amount_owed
                for row in claim_rows(session).unsecured
                if row.debt.debt_type == "student_loan"
            ),
            Decimal("0"),
        )
    )


def _total_other_nonpriority(session: IntakeSession) -> str:
    """E/F line 6i, 6j - 6f: lines 6g and 6h are never asked, so 6i holds the rest of Part 2."""
    return _fmt(
        Decimal(_total_nonpriority_unsecured(session)) - Decimal(_total_student_loans(session))
    )


def _total_priority(kind: str | None) -> Callable[[IntakeSession], str]:
    """
    A line's sum of Part 1's Total claim (B13) over the debts answered `kind`, all of them
    for None, "0.00" with none: E/F 6a-6e and 106Sum 3a and 9a-9c.
    """

    def rule(session: IntakeSession) -> str:
        return _fmt(
            sum(
                (
                    row.debt.amount_owed
                    for row in claim_rows(session).priority
                    if kind is None or row.debt.priority_answer == kind
                ),
                Decimal("0"),
            )
        )

    return rule


def _has_priority_debts(session: IntakeSession) -> str:
    """E/F line 1: Yes when Part 1 holds a debt, as check7 follows Part 2 (R2)."""
    return "yes" if claim_rows(session).priority else "no"


def _total_summary_line_9(session: IntakeSession) -> str:
    """
    106Sum 9g: 9a + 9b + 9c + 9d, which is E/F 6a + 6b + 6c + 6f (B14).

    Line 9 copies 6a, 6b, 6c and 6f; 9e and 9f are never asked and count as zero, and 6d is
    not on the line.
    """
    return _fmt(
        sum(
            (
                Decimal(_total_priority(kind)(session))
                for kind in ("domestic_support", "taxes", "intoxicated")
            ),
            Decimal(_total_student_loans(session)),
        )
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


def _means_result_box(session: IntakeSession) -> str:
    """
    Page 1's result box (4d-R5), from the stored means test's route (R-ROUTE): box 1 for debts
    not primarily consumer debts or the disabled veteran's exemption, box 3 for a line 3
    exclusion (D1, B33), else line 12b against line 13 as line 14 says (box 2 above the median,
    exactly when Form 122A-2 is in the packet). Blank before the means test runs.
    """
    means_test = getattr(session, "means_test", None)
    if means_test is None:
        return ""
    if means_test.outcome == MILITARY_EXCLUSION:
        return "box_3"
    if means_test.outcome in SUPP_OUTCOMES:
        return "box_1"
    return "box_2" if _median_comparison(session) == "above" else "box_1"


def _means_parts_1_and_2_print(session: IntakeSession, answer_cache=None) -> bool:
    """122A-1's Parts 1-2 print unless the stored means test routed the filer to a Supp outcome,
    whose boxes say to leave the rest of the form blank (4d-R6). With no means test they print."""
    means_test = getattr(session, "means_test", None)
    return means_test is None or means_test.outcome not in SUPP_OUTCOMES


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
    Schedule I line 10's total: both columns, Social Security included (C1), unlike CMI.

    The spouse's column counts only for a filer living with their spouse (3e1 spec §10.2). A
    blank column counts as zero, and the total is blank only when both are.
    """
    columns = (
        _on_row(session, False, _money(_line10)),
        _on_row(session, True, _money(_line10)),
    )
    if columns == ("", ""):
        return ""
    return _fmt(sum((Decimal(column or "0") for column in columns), _ZERO))


def _line_11_typed(session: IntakeSession) -> str:
    """Line 11's typed amount while the answer is Yes, stripped; "" otherwise or with none."""
    if _schedule_i(session, "line_11_answer") != "yes":
        return ""
    return _schedule_i(session, "line_11_amount").strip()


def _schedule_i_line_11_amount(session: IntakeSession) -> str:
    """
    Line 11's amount (4c-R3): 0.00 under No, as the form says to write $0 for a line asked;
    under Yes the typed amount, a typed 0 as 0.00 and none blank; blank while unanswered.
    """
    if _schedule_i(session, "line_11_answer") == "no":
        return _fmt(_ZERO)
    typed = _line_11_typed(session)
    return _fmt(Decimal(typed)) if typed else ""


def _fee_waiver_line_8_amount(session: IntakeSession) -> str:
    """103B line 8's "How much": line 11's typed amount under Yes, as 103B says to copy line 11's
    total; blank otherwise, since 103B ticks its own No box (4c-R3)."""
    typed = _line_11_typed(session)
    return _fmt(Decimal(typed)) if typed else ""


def _schedule_i_line_12(session: IntakeSession) -> str:
    """
    Line 12: line 10's total plus what line 11 adds, the typed amount under Yes (4c-R3).

    Blank only while line 10 is blank and line 11 adds nothing; otherwise a blank line 10
    counts as zero.
    """
    line_10 = _schedule_i_income_total(session)
    typed = _line_11_typed(session)
    adds = Decimal(typed) if typed else _ZERO
    if line_10 == "" and adds == 0:
        return ""
    return _fmt(Decimal(line_10 or "0") + adds)


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
    income = _schedule_i_line_12(session)
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


# ---------------------------------------------------------------------------
# Form 101 (11/26): one answer in several boxes, one box per choice (step 4b)
# ---------------------------------------------------------------------------


def digits(value: str) -> str:
    """The digits of what the filer typed: "900-70-1234" and "900701234" read the same.

    Only 0-9 count: other scripts' digits, which a "\\d" pattern would keep, can't print on the
    forms.
    """
    return re.sub(r"[^0-9]", "", value or "")


def nine_digit_slice(value, start: int, stop: int) -> str:
    """digits(value)[start:stop], or "" unless the value has exactly nine digits."""
    found = digits(value)
    return found[start:stop] if len(found) == 9 else ""


_NUMBER_STREET = re.compile(r"(\d+(?:-\d+|[A-Za-z])?)\s+(\S.*)")


def split_number_street(street: str) -> tuple[str, str]:
    """
    A street line as the form's two boxes, Number and Street (B56). A leading run of digits is
    the Number, with a trailing letter or a hyphenated range kept in it, and the rest is the
    Street:
      "1234 Main St"        -> ("1234", "Main St")
      "1234A Main St"       -> ("1234A", "Main St")
      "12-14 Main St"       -> ("12-14", "Main St")
      "Rural Route 2"       -> ("", "Rural Route 2")  no leading digits, so no Number
      "1234 Main St Apt 3"  -> ("1234", "Main St Apt 3")
    """
    street = (street or "").strip()
    match = _NUMBER_STREET.fullmatch(street)
    return (match[1], match[2]) if match else ("", street)


def split_district_name(name: str) -> tuple[str, str]:
    """
    "Northern District of Illinois" as ("Northern", "Illinois"); a name without " District of "
    is ("", name).
    """
    district, found, state = name.partition(" District of ")
    return (district, state) if found else ("", name)


def _petition(session: IntakeSession, key: str) -> str:
    return record_value(session, f"petition.{key}")


def _schedule_i(session: IntakeSession, key: str) -> str:
    """A ScheduleIAnswers key as text; "" when unanswered or the session has no record (4c)."""
    return record_value(session, f"schedule_i.{key}")


def _valid_itin(session: IntakeSession) -> str:
    """The stored ITIN only when it is nine digits starting with 9, else blank (PF2-U2)."""
    value = _petition(session, "itin")
    return value if is_itin(value) else ""


def _asked(key: str) -> Callable[[IntakeSession], str]:
    return lambda s: _petition(s, key)


def _is(reader: Callable[[IntakeSession], str], value: str) -> Callable[[IntakeSession], str]:
    """A single box's rule: "true" when the reader gives the value, "" otherwise."""
    return lambda s: "true" if reader(s) == value else ""


def _is_one_of(
    reader: Callable[[IntakeSession], str], values: tuple[str, ...]
) -> Callable[[IntakeSession], str]:
    return lambda s: "true" if reader(s) in values else ""


def _under_value(
    gate_key: str, gate_value: str, reader: Callable[[IntakeSession], str]
) -> Callable[[IntakeSession], str]:
    """The reader's value only while the gate answer is the gate value; stored rows stay."""
    return lambda s: reader(s) if _petition(s, gate_key) == gate_value else ""


def _under(gate_key: str, reader: Callable[[IntakeSession], str]) -> Callable[[IntakeSession], str]:
    """The reader's value only while the yes/no gate answer is "yes"."""
    return _under_value(gate_key, "yes", reader)


# The explain box (line 6, "the other reason", Debtor 1) the four venue lines are measured by.
_VENUE_REASON_TEMPLATE = "form_b101.pdf"
_VENUE_REASON_BOX = "See 28 USC  1408 1"
_VENUE_REASON_LINES = 4


def _venue_reason_lines(text: str) -> list[str]:
    """
    The venue reason broken at spaces into the four one-line boxes at 6 pt. Past four lines the
    fourth carries the rest, and a word wider than a box leaves the whole text on the first, so
    check() refuses that box as ValueTooLong and names it.
    """
    from apps.forms.services.pdf_filler import _as_printed
    from apps.forms.services.text_fit import MIN_SIZE, font_for, reverse_cmap_for, wrap
    from apps.forms.services.widgets import template_widgets

    # Measured as the filler prints it: composed (NFC) and without format characters.
    text = " ".join(_as_printed(text or "").split())
    lines = [""] * _VENUE_REASON_LINES
    if not text:
        return lines
    widget = next(
        (w for w in template_widgets(_VENUE_REASON_TEMPLATE) if w.full_name == _VENUE_REASON_BOX),
        None,
    )
    if widget is None:
        # A renamed box must fail loudly (a logged 500), never measure nothing.
        raise LookupError(f"{_VENUE_REASON_TEMPLATE} has no box {_VENUE_REASON_BOX!r}")
    wrapped = wrap(
        font_for(_VENUE_REASON_TEMPLATE, widget.font),
        reverse_cmap_for(_VENUE_REASON_TEMPLATE, widget.font),
        text,
        MIN_SIZE,
        widget.width - 4 * widget.margin,
    )
    if wrapped is None:
        wrapped = [text]
    if len(wrapped) > _VENUE_REASON_LINES:
        wrapped = [
            *wrapped[: _VENUE_REASON_LINES - 1],
            " ".join(wrapped[_VENUE_REASON_LINES - 1 :]),
        ]
    lines[: len(wrapped)] = wrapped
    return lines


def _step_of(key: str) -> dict[str, str]:
    return {"step": PETITION_STEP_OF_KEY[key]}


_PETITION_DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {}
_PETITION_FIXES: dict[str, dict[str, str]] = {}


def _register(name: str, rule: Callable[[IntakeSession], str], fix: dict[str, str]) -> None:
    _PETITION_DERIVATIONS[name] = rule
    _PETITION_FIXES[name] = fix


def _register_digits(prefix: str, reader, start: int, count: int, fix: dict[str, str]) -> None:
    """One rule a box: `<prefix>_<n>` reads count digits of the nine, from start."""
    for n in range(1, count + 1):
        _register(
            f"{prefix}_{n}",
            lambda s, n=n: nine_digit_slice(reader(s), start + n - 1, start + n),
            fix,
        )


_register_digits("ssn_last4_digit", lambda s: _debtor_text(s, "ssn"), 5, 4, {"step": "debtor_info"})
_register_digits("itin_last4_digit", _valid_itin, 5, 4, _step_of("itin"))


def _dashed(found: str, *sizes: int) -> str:
    """The digits in groups of `sizes`, joined by dashes; "" for no digits."""
    groups, start = [], 0
    for size in sizes:
        groups.append(found[start : start + size])
        start += size
    return "-".join(groups) if found else ""


# Form 121's number boxes are combs, one cell a character (PF2-T10-1). The ITIN's box follows a
# printed 9 and has ten cells, so it takes the eight digits after that 9 as NN-NN-NNNN; the other
# Social Security number's box has eleven, NNN-NN-NNNN, as ssn_formatted prints line 2's first.
_register(
    "itin_whole",
    lambda s: _dashed(nine_digit_slice(_valid_itin(s), 1, 9), 2, 2, 4),
    _step_of("itin"),
)
_register(
    "other_ssn_whole",
    lambda s: _dashed(nine_digit_slice(_petition(s, "other_ssn"), 0, 9), 3, 2, 4),
    _step_of("other_ssn"),
)
_register("ein_prefix", lambda s: nine_digit_slice(_petition(s, "ein"), 0, 2), _step_of("ein"))
_register("ein_suffix", lambda s: nine_digit_slice(_petition(s, "ein"), 2, 9), _step_of("ein"))

_register("court_district", lambda s: split_district_name(s.district.name)[0], {})
_register("court_state", lambda s: split_district_name(s.district.name)[1], {})

# Each street splits into Number and Street; the three detail addresses print under their Yes.
for _prefix, _reader, _fix in (
    ("home", lambda s: _debtor_text(s, "street_address"), {"step": "debtor_info"}),
    (
        "mailing",
        _under("mailing_answer", _asked("mailing_street")),
        _step_of("mailing_street"),
    ),
    (
        "business",
        _under("sole_proprietor_answer", _asked("business_street")),
        _step_of("business_street"),
    ),
    ("hazard", _under("hazard_answer", _asked("hazard_street")), _step_of("hazard_street")),
):
    _register(f"{_prefix}_number", lambda s, r=_reader: split_number_street(r(s))[0], _fix)
    _register(f"{_prefix}_street", lambda s, r=_reader: split_number_street(r(s))[1], _fix)

_register("venue_lived_here", _is(_asked("venue_choice"), "lived_here"), _step_of("venue_choice"))
_register("venue_other", _is(_asked("venue_choice"), "other"), _step_of("venue_choice"))
for _n in range(1, _VENUE_REASON_LINES + 1):
    _register(
        f"venue_reason_line_{_n}",
        lambda s, n=_n: _venue_reason_lines(_petition(s, "venue_reason"))[n - 1],
        _step_of("venue_reason"),
    )

for _value in ("pay_in_full", "installments", "waiver"):
    _register(
        f"fee_choice_{_value}",
        _is(_fee_answer("payment_choice"), _value),
        {"page": "/filing-fee"},
    )

for _value in ("no", "yes"):
    _register(
        f"eviction_{_value}",
        _is(_under("rents_residence", _asked("eviction_judgment")), _value),
        _step_of("eviction_judgment"),
    )
    _register(
        f"sole_proprietor_{_value}",
        _is(_asked("sole_proprietor_answer"), _value),
        _step_of("sole_proprietor_answer"),
    )
    _register(
        f"paid_preparer_{_value}", _is(_asked("paid_preparer"), _value), _step_of("paid_preparer")
    )

for _value in ("health_care", "single_asset", "stockbroker", "commodity_broker", "none"):
    _register(
        f"business_kind_{_value}",
        _is(_under("sole_proprietor_answer", _asked("business_kind")), _value),
        _step_of("business_kind"),
    )

for _value in ("certificate", "no_certificate", "exigent", "not_required"):
    _register(
        f"credit_counseling_{_value}",
        _is(_asked("credit_counseling"), _value),
        _step_of("credit_counseling"),
    )
for _value in ("incapacity", "disability", "active_duty"):
    _register(
        f"not_required_{_value}",
        _is(
            _under_value("credit_counseling", "not_required", _asked("not_required_reason")),
            _value,
        ),
        _step_of("not_required_reason"),
    )

# Line 16a asks "primarily consumer debts"; 16b, only when it is No, asks "primarily business".
_register("debt_nature_16a_yes", _is(_asked("debt_nature"), "consumer"), _step_of("debt_nature"))
_register(
    "debt_nature_16a_no",
    _is_one_of(_asked("debt_nature"), ("business", "neither")),
    _step_of("debt_nature"),
)
_register("debt_nature_16b_yes", _is(_asked("debt_nature"), "business"), _step_of("debt_nature"))
_register("debt_nature_16b_no", _is(_asked("debt_nature"), "neither"), _step_of("debt_nature"))
# 106Sum line 7 and Form 107 line 6 ask line 16a's question again, one box an answer (4d-R7):
# each box's binding key names its meaning, as schedule_j_total_income names line 12's rule.
_register(
    "debt_nature_consumer", _PETITION_DERIVATIONS["debt_nature_16a_yes"], _step_of("debt_nature")
)
_register(
    "debt_nature_not_consumer",
    _PETITION_DERIVATIONS["debt_nature_16a_no"],
    _step_of("debt_nature"),
)
_register("itin_answer_no", _is(_asked("itin_answer"), "no"), _step_of("itin_answer"))


# Form 122A-1Supp line 3's category (4d-R26): the filer's own stored category, and blank for "none"
# (D9, which claims no exclusion), so the box never ticks a category the filer didn't choose.
def _supp_duty_category(session: IntakeSession) -> str:
    category = _petition(session, "duty_category")
    return category if category in ("1", "2", "3", "4") else ""


_register("supp_duty_category", _supp_duty_category, _step_of("duty_category"))

# The derived rules a legal_review box may print through (Ruling T4-legalreview): each ticks its
# box only when the filer's own stored answer is exactly that box's choice, so it infers nothing.
# fill_resolver's UPL guard keeps every other derived legal_review box blank.
ANSWER_BOX_RULES = frozenset(
    {
        "credit_counseling_certificate",
        "credit_counseling_no_certificate",
        "credit_counseling_exigent",
        "credit_counseling_not_required",
        "not_required_incapacity",
        "not_required_disability",
        "not_required_active_duty",
        "debt_nature_16a_yes",
        "debt_nature_consumer",
        "supp_duty_category",
    }
)

# The running header's name-part boxes on pages 2, 4 and 7. Owner ruling, 2026-11-20: a part
# that doesn't fit its box at 6 pt prints blank there; never refuse the form, never an initial.
_HEADER_TEMPLATE = "form_b101.pdf"
_HEADER_BOXES = {
    "first": ("First Name", "First Name_2", "First Name_3"),
    "middle": ("Middle Name", "Middle Name_2", "Middle Name_3"),
    "last": ("Last Name", "Last Name_2", "Last Name_3"),
}


def _header_part(session: IntakeSession, part: str) -> str:
    """
    The name part when it fits each of its three header boxes at 6 pt or larger, measured as
    check() measures it (composed, the box's own font and inner width); "" when it doesn't, so a
    long name never refuses the form. Line 1 and the whole-name headers print it whole.
    """
    from apps.forms.services.pdf_filler import _as_printed
    from apps.forms.services.text_fit import fit
    from apps.forms.services.widgets import template_widgets

    text = _debtor_text(session, f"{part}_name")
    boxes = [w for w in template_widgets(_HEADER_TEMPLATE) if w.full_name in _HEADER_BOXES[part]]
    missing = set(_HEADER_BOXES[part]) - {w.full_name for w in boxes}
    if missing:
        # No box would read as "fits" and refuse a long name at check(), undoing the ruling.
        raise LookupError(f"{_HEADER_TEMPLATE} has no box {sorted(missing)[0]!r}")
    fits = all(fit(w, _HEADER_TEMPLATE, _as_printed(text)) is not None for w in boxes)
    return text if fits else ""


for _part in _HEADER_BOXES:
    _register(
        f"header_{_part}_name",
        lambda s, part=_part: _header_part(s, part),
        {"step": "debtor_info"},
    )

# Lines 18-20: one box a range, each keyed by the range the existing rule returns.
for _prefix, _range_rule, _ranges, _fix in (
    ("creditor_count_is", _creditor_count_range, _CREDITOR_RANGES, {"step": "debts"}),
    ("total_assets_is", _total_assets_range, _AMOUNT_RANGES, {"step": "assets"}),
    ("total_debts_is", _total_debts_range, _AMOUNT_RANGES, {"step": "debts"}),
):
    for _value in (*(lowest for _, lowest in _ranges), "more"):
        _register(f"{_prefix}_{_value}", _is(_range_rule, _value), _fix)

_PETITION_PREDICATES: dict[str, Callable[..., bool]] = {
    f"petition_{name}": (
        lambda s, answer_cache=None, key=key, value=value: _petition(s, key) == value
    )
    for name, key, value in (
        ("other_names_yes", "other_names_answer", "yes"),
        ("itin_yes", "itin_answer", "yes"),
        ("other_ssn_yes", "other_ssn_answer", "yes"),
        ("mailing_yes", "mailing_answer", "yes"),
        ("venue_other", "venue_choice", "other"),
        ("prior_bankruptcy_yes", "prior_bankruptcy_answer", "yes"),
        ("pending_case_yes", "pending_case_answer", "yes"),
        ("sole_proprietor_yes", "sole_proprietor_answer", "yes"),
        ("hazard_yes", "hazard_answer", "yes"),
        ("rents_yes", "rents_residence", "yes"),
        ("debt_nature_neither", "debt_nature", "neither"),
        ("debt_nature_consumer", "debt_nature", "consumer"),
        ("credit_counseling_exigent", "credit_counseling", "exigent"),
        ("paid_preparer_yes", "paid_preparer", "yes"),
    )
}

# 106Sum line 7's not-consumer box says "You have nothing to report on this part of the form"
# (D7): lines 8-9g print unless the filer's own line 16 answer is business or neither. No
# `key == value` row says "anything but these two", so it has its own row.
_DEBT_NATURE_PREDICATES: dict[str, Callable[..., bool]] = {
    "debt_nature_consumer_or_unanswered": lambda s, answer_cache=None: (
        _petition(s, "debt_nature") not in ("business", "neither")
    ),
}

# Form 122A-1's Parts 1-2 go blank under a Supp outcome (4d-R6). 106Sum line 8 copies 122A-1 line
# 11, so it prints only where line 11 does and D7's line 7 answer allows (D10).
_MEANS_ROUTE_PREDICATES: dict[str, Callable[..., bool]] = {
    "means_parts_1_and_2_print": _means_parts_1_and_2_print,
    "summary_line_8_prints": lambda s, answer_cache=None: (
        _DEBT_NATURE_PREDICATES["debt_nature_consumer_or_unanswered"](s)
        and _means_parts_1_and_2_print(s)
    ),
}


def _petition_answers(session: IntakeSession) -> dict:
    """The session's stored petition answers as stored, {} with no record (Ruling I: no registry
    import, which would be a cycle through fill_resolver)."""
    record = getattr(session, "petition_answers", None)
    return record.get_answers() if record is not None else {}


def _supp_line_3_follow_up(answers) -> bool:
    return supp_line_3_reached(answers) and answers.get("reservist") == "yes"


def _supp_categories(answers) -> bool:
    return _supp_line_3_follow_up(answers) and answers.get("called_to_duty") == "yes"


# Form 122A-1Supp's Part 2 prints each answer only where the form reaches it (4d-R8, R-D2), under
# consumer debts (line 2's gate is `petition_debt_nature_consumer`): line 2's follow-up under its
# Yes, line 3 unless line 2 is Yes to both, line 3's follow-up under the Reservist Yes, the
# categories under "called to duty" Yes and each date under its own category. Complete asks each
# question exactly there (petition._SUPP_SHOWN); test_form_122a1_supp_schema.py pins the two.
_SUPP_PREDICATES: dict[str, Callable[..., bool]] = {
    "supp_line_2_follow_up": lambda s, answer_cache=None: (
        (answers := _petition_answers(s)).get("debt_nature") == "consumer"
        and answers.get("disabled_veteran") == "yes"
    ),
    "supp_line_3": lambda s, answer_cache=None: supp_line_3_reached(_petition_answers(s)),
    "supp_line_3_follow_up": lambda s, answer_cache=None: (
        _supp_line_3_follow_up(_petition_answers(s))
    ),
    "supp_categories": lambda s, answer_cache=None: _supp_categories(_petition_answers(s)),
    "supp_date_1": lambda s, answer_cache=None: (
        _supp_categories(answers := _petition_answers(s)) and answers.get("duty_category") == "2"
    ),
    "supp_date_2": lambda s, answer_cache=None: (
        _supp_categories(answers := _petition_answers(s)) and answers.get("duty_category") == "4"
    ),
}

# Schedule I's and Schedule J line 24's boxes print only what the step shows (4c-R5): your
# occupation once your status is chosen, your employer under Employed, the spouse's column only
# while married with the spouse at home (`married_together`: the spouse isn't filing), and each
# line's text under its own Yes.
_SCHEDULE_I_PREDICATES: dict[str, Callable[..., bool]] = {
    "schedule_i_status_answered": lambda s, answer_cache=None: (
        _schedule_i(s, "employment_status") != ""
    ),
    "schedule_i_employed": lambda s, answer_cache=None: (
        _schedule_i(s, "employment_status") == "employed"
    ),
    "schedule_i_spouse_shown": lambda s, answer_cache=None: (
        married_together(s) and _schedule_i(s, "spouse_employment_status") != ""
    ),
    "schedule_i_spouse_employed": lambda s, answer_cache=None: (
        married_together(s) and _schedule_i(s, "spouse_employment_status") == "employed"
    ),
    "schedule_i_line_11_yes": lambda s, answer_cache=None: (
        _schedule_i(s, "line_11_answer") == "yes"
    ),
    "schedule_i_line_13_yes": lambda s, answer_cache=None: (
        _schedule_i(s, "line_13_answer") == "yes"
    ),
    "schedule_j_line_24_yes": lambda s, answer_cache=None: (
        _schedule_i(s, "schedule_j_line_24_answer") == "yes"
    ),
}


# ---------------------------------------------------------------------------
# DERIVATIONS dict (all referenced functions must be defined above)
# ---------------------------------------------------------------------------

DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
    "full_name": _full_name,
    "family_size": _family_size,
    "first_name": lambda s: _debtor_text(s, "first_name"),
    "middle_name": lambda s: _debtor_text(s, "middle_name"),
    "last_name": lambda s: _debtor_text(s, "last_name"),
    "city": lambda s: _debtor_text(s, "city"),
    "state": lambda s: _debtor_text(s, "state"),
    "zip_code": lambda s: _debtor_text(s, "zip_code"),
    "county": _county,
    "phone": lambda s: _debtor_text(s, "phone"),
    "email": lambda s: _debtor_text(s, "email"),
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
    # Part 2 holds the unsecured debts answered "No", "Not sure" or not yet answered (R2).
    "has_nonpriority_debts": lambda s: "yes" if claim_rows(s).unsecured else "no",
    "total_student_loans": _total_student_loans,
    "total_other_nonpriority": _total_other_nonpriority,
    # Part 1: E/F line 1 and 6a-6e, 106Sum 3a and 9a-9c and 9g (R6)
    "has_priority_debts": _has_priority_debts,
    "total_priority_domestic_support": _total_priority("domestic_support"),
    "total_priority_taxes": _total_priority("taxes"),
    "total_priority_intoxicated": _total_priority("intoxicated"),
    "total_priority_other": _total_priority("other"),
    "total_priority_unsecured": _total_priority(None),
    "total_summary_line_9": _total_summary_line_9,
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
    "means_result_box": _means_result_box,
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
    # 103B lines 4, 5, 7 and 9 (3f spec §8); Form 101 line 8's boxes are the fee_choice_ rules
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
    # Line 8's amount is Schedule I line 11's (4c-R3)
    "fee_waiver_line_8_amount": _fee_waiver_line_8_amount,
    # Schedule I income line item derivations
    **_schedule_i_twins(),
    "schedule_i_income_total": _schedule_i_income_total,
    "schedule_i_line_11_amount": _schedule_i_line_11_amount,
    "schedule_i_line_12": _schedule_i_line_12,
    "schedule_i_payroll_other_specify": _payroll_other_specify,
    "schedule_i_assistance_specify": _assistance_specify,
    "schedule_i_other_income_label": _schedule_i_other_income_label,
    # Schedule J expense line item derivations
    "schedule_j_rent_or_mortgage": _schedule_j_rent_or_mortgage,
    "schedule_j_additional_mortgage": lambda s: _linked_amount(
        linked_payments(s).additional_mortgage
    ),
    "schedule_j_electricity_heat_gas": lambda s: _expense_line(s, "electricity_heat_gas"),
    "schedule_j_water_sewer_garbage": lambda s: _expense_line(s, "water_sewer_garbage"),
    "schedule_j_phone_internet_cable": lambda s: _expense_line(s, "phone_internet_cable"),
    "schedule_j_life_insurance": lambda s: _expense_line(s, "life_insurance"),
    "schedule_j_health_insurance": lambda s: _expense_line(s, "health_insurance"),
    "schedule_j_utilities": lambda s: _expense_line(s, "utilities"),
    "schedule_j_utilities_label": lambda s: _expense_text(s, "utilities", "utilities_specify"),
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
    "schedule_j_insurance_label": lambda s: _expense_text(
        s, "insurance_not_deducted", "insurance_specify"
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
    "schedule_j_total_income": _schedule_i_line_12,
    "schedule_j_monthly_net_income": _schedule_j_monthly_net_income,
    "schedule_j_joint_case": _schedule_j_joint_case,
    "schedule_j_has_dependents": _schedule_j_has_dependents,
    # Schedule H line 2 (3c5): the community property answers, as the claims step asks them
    "schedule_h_community_lived": lambda s: community_answers(s)["lived"],
    "schedule_h_spouse_lived_with": lambda s: community_answers(s)["spouse_lived_with"],
    "schedule_h_community_state": lambda s: community_answers(s)["state"],
    "schedule_h_spouse_name": lambda s: community_answers(s)["spouse_name"],
    "schedule_h_spouse_street": lambda s: _spouse_street(community_answers(s)),
    "schedule_h_spouse_city": lambda s: community_answers(s)["spouse_city"],
    "schedule_h_spouse_state": lambda s: community_answers(s)["spouse_state"],
    "schedule_h_spouse_zip": lambda s: community_answers(s)["spouse_zip"],
    **_PETITION_DERIVATIONS,
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
    "city": {"step": "debtor_info"},
    "state": {"step": "debtor_info"},
    "zip_code": {"step": "debtor_info"},
    "county": {"step": "debtor_info"},
    "phone": {"step": "debtor_info"},
    "email": {"step": "debtor_info"},
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
    "schedule_i_line_11_amount": {"step": "income_info"},
    "schedule_i_line_12": {"step": "income_info"},
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
    # 103B line 8 copies Schedule I line 11, asked on the Income step
    "fee_waiver_line_8_amount": {"step": "income_info"},
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
    "schedule_j_electricity_heat_gas": {"step": "expense_info"},
    "schedule_j_water_sewer_garbage": {"step": "expense_info"},
    "schedule_j_phone_internet_cable": {"step": "expense_info"},
    "schedule_j_life_insurance": {"step": "expense_info"},
    "schedule_j_health_insurance": {"step": "expense_info"},
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
    "total_debts": {"step": "debts"},
    "total_nonpriority_unsecured": {"step": "debts"},
    "total_student_loans": {"step": "debts"},
    "total_other_nonpriority": {"step": "debts"},
    "has_priority_debts": {"step": "debts"},
    "total_priority_domestic_support": {"step": "debts"},
    "total_priority_taxes": {"step": "debts"},
    "total_priority_intoxicated": {"step": "debts"},
    "total_priority_other": {"step": "debts"},
    "total_priority_unsecured": {"step": "debts"},
    "total_summary_line_9": {"step": "debts"},
    # The filing-fee page (3f spec §7)
    "fee_waiver_income_change_explanation": {"page": "/filing-fee"},
    "fee_waiver_installments_explanation": {"page": "/filing-fee"},
    "fee_waiver_others_covered_who": {"page": "/filing-fee"},
    "fee_waiver_expense_change_explanation": {"page": "/filing-fee"},
    # No link. The district and its median income table come from DigniFi's own data.
    "district_name": {},
    "line13a_median_income": {},
    # Form 122A-1's page-1 box: the result Complete works out on Review
    "means_result_box": {"step": "review"},
    # Schedule H line 2: the spouse's name and address are entered on the Codebtors step
    "schedule_h_community_state": {"step": "codebtors"},
    "schedule_h_spouse_name": {"step": "codebtors"},
    "schedule_h_spouse_street": {"step": "codebtors"},
    "schedule_h_spouse_city": {"step": "codebtors"},
    "schedule_h_spouse_state": {"step": "codebtors"},
    "schedule_h_spouse_zip": {"step": "codebtors"},
    **_PETITION_FIXES,
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
    **_PETITION_PREDICATES,
    **_DEBT_NATURE_PREDICATES,
    **_MEANS_ROUTE_PREDICATES,
    **_SUPP_PREDICATES,
    **_SCHEDULE_I_PREDICATES,
}
