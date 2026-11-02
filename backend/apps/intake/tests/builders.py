"""Synthetic household answers for intake, eligibility and forms tests.

Every value here is invented. answer_household's defaults make a session that passes 3e1's new
checks: not married, no one else in the home or supported ([]), and Cook County.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal

from apps.intake.models import Household, SpouseIncome


def answer_household(
    session,
    *,
    marital_status: str | None = "not_married",
    members: Sequence[dict] | None = (),
    county: str | None = "Cook",
    spouse_income: Mapping[str, Decimal | None] | None = None,
) -> Household:
    """Store the marriage answer, the county and the household list, and the spouse's amounts
    when given, through the session's own relations, so a test holding the session reads them.

    The session needs an income row. A second call replaces the answer, the county and the
    list. spouse_income={} stores all ten amounts empty; None leaves any stored row alone.
    """
    session.income_info.marital_status = marital_status
    session.income_info.save(update_fields=["marital_status"])

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
        row.refresh_from_db()  # the Decimals the encrypted column returns
    return household
