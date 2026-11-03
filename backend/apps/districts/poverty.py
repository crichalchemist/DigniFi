"""The HHS poverty guideline and the court's filing-fee limit built on it.

A judge may waive the Chapter 7 filing fee only for a family whose income is less than 150% of
the poverty guideline for its size. The court's limit is that 150%, a month. The guideline is
looked up through `in_force` on the fill date, like every dated table.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .dated_tables import fill_date, in_force
from .models import PovertyGuideline

POVERTY_TABLE = "HHS poverty guidelines"


def poverty_limit_monthly(guideline: PovertyGuideline, family_size: int) -> Decimal:
    """The court's limit a month for a family: 150% of its yearly guideline, over 12.

    A family's income meets the limit only when it is strictly less (28 U.S.C. § 1930(f)(1)).
    That comparison is the court's, and DigniFi never makes it for the filer.

    Raises:
        ValueError: If family_size is less than 1.
    """
    if family_size < 1:
        raise ValueError("Family size must be at least 1.")

    yearly = Decimal(guideline.first_person) + Decimal(guideline.each_additional) * (
        family_size - 1
    )
    return (yearly * 3 / 2 / 12).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def poverty_guideline_in_force(on: date | None = None) -> PovertyGuideline:
    """The guideline in force on `on`, or on the fill date when no day is given.

    Raises:
        NoTableInForce: no row has started yet, or the newest one that has is past its
            valid_through. `in_force` logs it once, with the table and the date.
    """
    return in_force(PovertyGuideline.objects.all(), on or fill_date(), POVERTY_TABLE)
