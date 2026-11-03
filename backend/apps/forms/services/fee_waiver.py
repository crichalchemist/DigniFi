"""
Form 103B lines 1-3 from the household list, Schedule I line 10 and 8f (3f spec §8.2).

The form's rules and the filing-fee page both read these, so the two never differ. Line 1
counts the household list as count_fee_waiver_household does; line 2 is the figure Schedule I
line 10 prints for each person counted, less the known non-cash help it includes; line 3 is
the 8f answer about non-cash help.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.eligibility.cmi import counted_spouse_income, household_members, income_step_gaps
from apps.forms.services.derivations import DERIVATIONS
from apps.intake.household import count_fee_waiver_household, fee_waiver_spouse_counted


@dataclass(frozen=True)
class FeeWaiverFamily:
    total: int
    spouse_counted: bool
    dependents: int


@dataclass(frozen=True)
class FeeWaiverIncome:
    you: Decimal
    spouse: Decimal | None
    subtotal: Decimal
    noncash: Decimal | None
    total: Decimal


def _refuse_any_gap(session) -> None:
    gaps = income_step_gaps(session)
    if gaps:
        raise gaps[0]


def _counted_rows(session) -> list:
    """The filer's income row, then the spouse's when the spouse counts; missing rows dropped."""
    rows = [getattr(session, "income_info", None), counted_spouse_income(session)]
    return [row for row in rows if row is not None]


def fee_waiver_family(session) -> FeeWaiverFamily:
    """Line 1: the filer, a spouse at home, and the dependents.

    Raises:
        IncomeStepGap: the first gap on the Income step, rather than a guessed family of 1.
    """
    _refuse_any_gap(session)
    marital_status = session.income_info.marital_status
    total = count_fee_waiver_household(household_members(session), marital_status)
    spouse_counted = fee_waiver_spouse_counted(marital_status)
    dependents = total - (2 if spouse_counted else 1)
    return FeeWaiverFamily(total=total, spouse_counted=spouse_counted, dependents=dependents)


def fee_waiver_income(session) -> FeeWaiverIncome:
    """Line 2: Schedule I line 10 for each person counted, less their known non-cash help.

    Raises:
        IncomeStepGap: the first gap on the Income step.
    """
    _refuse_any_gap(session)
    you = Decimal(DERIVATIONS["schedule_i_income_total_debtor1"](session))
    # Blank unless the filer lives with their spouse.
    spouse_text = DERIVATIONS["schedule_i_income_total_spouse"](session)
    spouse = Decimal(spouse_text) if spouse_text else None
    subtotal = you + (spouse or Decimal("0"))
    known = [
        row.noncash_assistance_value
        for row in _counted_rows(session)
        if row.assistance_answer == "yes" and row.noncash_assistance_value is not None
    ]
    noncash = sum(known, Decimal("0"))
    if noncash <= 0:
        noncash = None
    total = subtotal - (noncash or Decimal("0"))
    return FeeWaiverIncome(you=you, spouse=spouse, subtotal=subtotal, noncash=noncash, total=total)


def fee_waiver_noncash(session) -> tuple[str, str]:
    """Line 3: ("yes", the kinds), ("no", ""), or ("", "") while unanswered. Never raises.

    Cash help is no answer to line 3, which asks only about non-cash help. The kinds are the
    filer's, then the spouse's after "Spouse: ", joined by "; ".
    """
    rows = _counted_rows(session)
    spouse_row = counted_spouse_income(session)
    kinds = []
    for row in rows:
        kind = (row.noncash_assistance_kind or "").strip()
        if row.assistance_answer == "yes" and kind:
            kinds.append(f"Spouse: {kind}" if row is spouse_row else kind)
    if kinds:
        return ("yes", "; ".join(kinds))
    # With no income row there is no answer at all, so no sworn No either.
    if not rows or any(row.assistance_answer is None for row in rows):
        return ("", "")
    return ("no", "")
