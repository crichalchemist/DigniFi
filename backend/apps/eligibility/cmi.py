"""
Current monthly income (CMI) (forms step 2 spec §5.5, 3e1 spec §5.3).

The means test, the above-median check, the expense calculator and the forms' `cmi` rule read
the household's CMI, household_cmi: the filer's, plus the spouse's for a filer living with
their spouse (married_together), and the filer's alone otherwise.

current_monthly_income works out one person's: their monthly income from every source the
Income step asks about except benefits under the Social Security Act, which 11 U.S.C.
§ 101(10A)(B) leaves out, rounded to the cent. So each column and their sum print and compare
the same everywhere (forms step 2 spec §5.6).
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal

from apps.intake.household import is_answered
from apps.intake.income import floored_net, has_entry_figures
from apps.intake.models import IncomeInfo, SpouseIncome


def income_window(on: date) -> tuple[date, date]:
    """The six full calendar months before the month of `on` (122A-1's window, 3e2 spec §4.4)."""
    end = on.replace(day=1) - timedelta(days=1)
    months = end.year * 12 + end.month - 1 - 5
    return date(months // 12, months % 12 + 1, 1), end


def answered_window(period_end: date) -> tuple[date, date]:
    """The window whose last day was stamped on the Income step."""
    return income_window(period_end + timedelta(days=1))


class IncomeNotSplit(ValueError):
    """The filer hasn't entered their income by source, so CMI can't be worked out.

    A total saved before income was stored by source can't be split by anyone but the filer.
    """

    step = "income_info"  # the wizard step where the filer enters it

    def __init__(self) -> None:
        super().__init__("Enter your income by source on the Income step.")


def current_monthly_income(income_info) -> Decimal:
    """The ten Income step amounts added up, without Social Security, to the cent (half-even).

    An amount the filer left empty counts as zero once another one was given.

    Raises:
        IncomeNotSplit: the filer gave none of the ten amounts.
    """
    given = {
        field: getattr(income_info, field)
        for field in income_info.SOURCE_FIELDS
        if getattr(income_info, field) is not None
    }
    entries = income_info.get_entries()
    if not given and not has_entry_figures(entries):
        raise IncomeNotSplit()
    total = sum(
        (amount for field, amount in given.items() if field != "monthly_social_security"),
        Decimal("0"),
    )
    total += floored_net(entries, "business") + floored_net(entries, "rental")
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


class IncomeStepGap(IncomeNotSplit):
    """A gap the Income step leaves (3e1 spec §9.1), named in its own sentence.

    A subclass of IncomeNotSplit, so a caller that catches IncomeNotSplit catches it too, with
    the same step.
    """

    def __init__(self, message: str) -> None:
        ValueError.__init__(self, message)


# Each gap's sentence (3e1 spec §9.1).
MARRIAGE_UNANSWERED = "Answer the question about marriage on the Income step."
SPOUSE_FILING = (
    "DigniFi prepares forms for one person filing alone. "
    "Check your answer about marriage on the Income step."
)
HOUSEHOLD_UNANSWERED = (
    "List the people in your home and the people you support on the Income step, "
    "or tell us no one does."
)
MEMBER_UNANSWERED = (
    "Answer every question for each person on your household list on the Income step."
)
HOUSEHOLD_MISMATCH = (
    "Your household list and your answer about marriage don't match. "
    "Check both on the Income step."
)
SPOUSE_INCOME_NOT_SPLIT = (
    "Enter your spouse's income by source on the Income step. "
    "If your spouse has no income, enter $0 in one box."
)
LEGACY_RENTAL = (
    "Rental income was saved as one amount. "
    "Enter each rental property's gross receipts and operating expenses on the Income step."
)
SPOUSE_LEGACY_RENTAL = (
    "Your spouse's rental income was saved as one amount. "
    "Enter each rental property's gross receipts and operating expenses on the Income step."
)


def _legacy_rental_open(row) -> bool:
    """Whether a person's net rental figure is still their only word on rental (3e2 spec §4.7)."""
    return row is not None and (row.monthly_rental_income or 0) > 0 and row.get_entries() is None


def _marriage_answer(session) -> str | None:
    """Form 122A-1 line 1's stored answer, or None with no income row."""
    return getattr(getattr(session, "income_info", None), "marital_status", None)


def counted_spouse_income(session) -> SpouseIncome | None:
    """The spouse's amounts when they count: only for a filer living with their spouse.

    None under any other answer, and under that one with no row stored. Never raises.
    """
    if _marriage_answer(session) != "married_together":
        return None
    return getattr(session, "spouse_income", None)


def spouse_monthly_income(session) -> Decimal | None:
    """The spouse's CMI (122A-1 column B), or None unless the filer lives with their spouse.

    Raises:
        IncomeStepGap: the filer lives with their spouse and gave none of the spouse's amounts.
    """
    if _marriage_answer(session) != "married_together":
        return None
    row = counted_spouse_income(session)
    if (
        row is None
        or all(getattr(row, field) is None for field in row.SOURCE_FIELDS)
        and not has_entry_figures(row.get_entries())
    ):
        raise IncomeStepGap(SPOUSE_INCOME_NOT_SPLIT)
    return current_monthly_income(row)


def household_cmi(session) -> Decimal:
    """The household's CMI: the filer's, plus the spouse's for a filer living with them.

    Raises:
        IncomeNotSplit: the filer's own amounts are missing (checked first), or the spouse's
            are, as an IncomeStepGap.
    """
    income_info = getattr(session, "income_info", None)
    if income_info is None:
        raise IncomeNotSplit()
    filer = current_monthly_income(income_info)
    return filer + (spouse_monthly_income(session) or Decimal("0"))


def household_members(session) -> list[dict]:
    """The stored household list; [] means the filer said no one.

    Raises:
        IncomeStepGap: the filer hasn't answered the list.
    """
    household = getattr(session, "household", None)
    members = household.get_members() if household is not None else None
    if members is None:
        raise IncomeStepGap(HOUSEHOLD_UNANSWERED)
    return members


def _household_mismatch(answer: str, members: list[dict]) -> bool:
    """Whether the list contradicts the marriage answer, judged on answered data only.

    Under married_together, a spouse row whose lives_with_you is unanswered is no mismatch,
    and with no spouse row, neither is a row whose relationship is unanswered and whose
    lives_with_you isn't False, since it may yet be the spouse at home. The row gap names both.
    """
    spouse = next((member for member in members if member.get("relationship") == "spouse"), None)
    if answer == "married_together":
        if spouse is not None:
            return spouse.get("lives_with_you") is False
        return not any(
            member.get("relationship") is None and member.get("lives_with_you") is not False
            for member in members
        )
    if answer == "not_married":
        return spouse is not None
    return False


def income_step_gaps(session) -> list[IncomeStepGap]:
    """Every gap the Income step leaves, at most one of each, in §9.1's order. Never raises."""
    answer = _marriage_answer(session)
    gaps = []
    if answer not in IncomeInfo.MARITAL_ANSWERS:
        gaps.append(IncomeStepGap(MARRIAGE_UNANSWERED))
    if answer == "married_spouse_filing":
        gaps.append(IncomeStepGap(SPOUSE_FILING))
    try:
        members = household_members(session)
    except IncomeStepGap as gap:
        gaps.append(gap)
        members = None
    if members is not None:
        if not all(is_answered(member) for member in members):
            gaps.append(IncomeStepGap(MEMBER_UNANSWERED))
        if answer in IncomeInfo.MARITAL_ANSWERS and _household_mismatch(answer, members):
            gaps.append(IncomeStepGap(HOUSEHOLD_MISMATCH))
    income_info = getattr(session, "income_info", None)
    legacy = _legacy_rental_open(income_info)
    if legacy:
        gaps.append(IncomeStepGap(LEGACY_RENTAL))
    else:
        try:
            if income_info is None:
                raise IncomeNotSplit()
            current_monthly_income(income_info)
        except IncomeNotSplit:
            gaps.append(IncomeStepGap(str(IncomeNotSplit())))
    if _legacy_rental_open(counted_spouse_income(session)):
        gaps.append(IncomeStepGap(SPOUSE_LEGACY_RENTAL))
    else:
        try:
            spouse_monthly_income(session)
        except IncomeStepGap as gap:
            gaps.append(gap)
    return gaps


def is_above_median(cmi: Decimal, median_income: Decimal) -> bool:
    """Whether monthly CMI times 12 is above the district's annual median income.

    Income exactly at the median counts as below it (DIG-136): 11 U.S.C. § 707(b)(7) reads
    "equal to or less than", and Form 122A-1 line 14a "less than or equal to". The means test
    and the packet both use this one comparison, so they never disagree at the median.
    """
    return cmi * 12 > median_income
