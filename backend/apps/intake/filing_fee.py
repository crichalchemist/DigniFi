"""What the filing-fee page shows beside Form 101 line 8, as information only (3f spec §6.2).
Never a verdict: the court decides."""

from apps.districts.dated_tables import NoTableInForce
from apps.districts.poverty import poverty_guideline_in_force, poverty_limit_monthly
from apps.eligibility.cmi import IncomeStepGap
from apps.forms.services.fee_waiver import fee_waiver_family, fee_waiver_income


def filing_fee_information(session) -> tuple[dict | None, str | None]:
    """The court's limit for the filer's family and the filer's own 103B line 2 figure, or
    None and why: "income" while the Income step has a gap, "no_table" while no HHS poverty
    guideline is in force on the fill date (in_force logs which). It never blocks a save."""
    try:
        family = fee_waiver_family(session)
        income = fee_waiver_income(session)
    except IncomeStepGap:
        return None, "income"
    try:
        guideline = poverty_guideline_in_force()
    except NoTableInForce:
        return None, "no_table"
    return {
        "family_size": family.total,
        "limit_monthly": f"{poverty_limit_monthly(guideline, family.total):.2f}",
        "guideline": {
            "year": guideline.effective_date.year,
            "effective_date": guideline.effective_date.isoformat(),
            "source_url": guideline.source_url,
        },
        "family_income_monthly": f"{income.total:.2f}",
    }, None
