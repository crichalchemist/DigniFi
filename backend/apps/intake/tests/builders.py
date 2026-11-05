"""Synthetic household answers for intake, eligibility and forms tests.

Every value here is invented. answer_household's defaults make a session that passes 3e1's new
checks: not married, no one else in the home or supported ([]), and Cook County. The 3e2
defaults answer the other four: income not now different, no business or rental ([]), no other
government assistance, and $0 taken out of pay. answer_household also chooses to pay the filing
fee in full (Form 101 line 8), so a forms test meets no refusal for a missing answer;
payment_choice=None leaves the answer as it is.
"""

import json
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal

from apps.intake.asset_lines import shown_lines
from apps.intake.models import AssetLineAnswers, FilingFee, Household, SpouseIncome


def answer_income_detail(
    row,
    *,
    income_now_different: str | None = "no",
    business_and_rental: Sequence[dict] | None = (),
    assistance_answer: str | None = "no",
    payroll_tax: Decimal | None = Decimal("0"),
) -> None:
    """Store the four 3e2 answers on an IncomeInfo or SpouseIncome row and save it.

    The list goes through store_entries as copies, so a caller's rows never gain an id. A test
    that builds a row by hand calls this on it.
    """
    row.income_now_different = income_now_different
    row.store_entries(
        None if business_and_rental is None else [dict(entry) for entry in business_and_rental]
    )
    row.assistance_answer = assistance_answer
    row.payroll_tax = payroll_tax
    row.save()


def answer_asset_lines(session, yes: Iterable[str] = ()) -> None:
    """Store "yes" for the named Schedule A/B lines and "no" for every other line shown.

    A gate named in yes shows its lines (37 and 46), which then store "no". A line whose
    gate isn't answered "yes" is hidden and stores nothing, as the wizard stores it.
    """
    answers = dict.fromkeys(yes, "yes")
    for line in shown_lines(answers):
        answers.setdefault(line.key, "no")
    row = getattr(session, "asset_lines", None) or AssetLineAnswers(session=session)
    row.answers = json.dumps(answers)
    row.save()


def answer_household(
    session,
    *,
    marital_status: str | None = "not_married",
    members: Sequence[dict] | None = (),
    county: str | None = "Cook",
    spouse_income: Mapping[str, Decimal | None] | None = None,
    income_now_different: str | None = "no",
    business_and_rental: Sequence[dict] | None = (),
    assistance_answer: str | None = "no",
    payroll_tax: Decimal | None = Decimal("0"),
    payment_choice: str | None = "pay_in_full",
    asset_lines: Iterable[str] | None = (),
) -> Household:
    """Store the marriage answer, the county and the household list, and the spouse's amounts
    when given, through the session's own relations, so a test holding the session reads them.

    The session needs an income row. A second call replaces the answer, the county and the
    list. spouse_income={} stores all ten amounts empty; None leaves any stored row alone.

    The four 3e2 answers (defaults: "no", [], "no", $0) go to the filer's row, and to the
    spouse's row when spouse_income is given.

    payment_choice goes to the session's FilingFee, created if missing; None leaves any stored
    row alone.

    asset_lines names the Schedule A/B lines answered Yes (default none: every shown line No);
    None leaves the stored answers alone.
    """
    session.income_info.marital_status = marital_status
    session.income_info.save(update_fields=["marital_status"])
    detail = {
        "income_now_different": income_now_different,
        "business_and_rental": business_and_rental,
        "assistance_answer": assistance_answer,
        "payroll_tax": payroll_tax,
    }
    answer_income_detail(session.income_info, **detail)

    household = getattr(session, "household", None) or Household(session=session)
    # Copies, so a caller's module-level rows never gain an id.
    household.store_members(None if members is None else [dict(row) for row in members])
    household.county = county
    household.save()

    if spouse_income is not None:
        row = getattr(session, "spouse_income", None) or SpouseIncome(session=session)
        for field in SpouseIncome.SOURCE_FIELDS:
            setattr(row, field, spouse_income.get(field))
        row.save()
        answer_income_detail(row, **detail)
        row.refresh_from_db()  # the Decimals the encrypted column returns
    if asset_lines is not None:
        answer_asset_lines(session, asset_lines)
    if payment_choice is not None:
        fee = getattr(session, "filing_fee", None) or FilingFee(session=session)
        fee.payment_choice = payment_choice
        fee.save()
    return household
