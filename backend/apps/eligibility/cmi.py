"""
Current monthly income (CMI), the one figure the means test, the above-median calculator
and the court forms share (forms step 2 spec §5.5).

CMI counts the filer's monthly income from every source the Income step asks about except
benefits under the Social Security Act, which 11 U.S.C. § 101(10A)(B) leaves out. It is
rounded to the cent once, here, so the means test, the packet and 122A-1 compare and print
the same figure (forms step 2 spec §5.6).
"""

from decimal import ROUND_HALF_EVEN, Decimal


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
    if not given:
        raise IncomeNotSplit()
    total = sum(
        (amount for field, amount in given.items() if field != "monthly_social_security"),
        Decimal("0"),
    )
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def is_above_median(cmi: Decimal, median_income: Decimal) -> bool:
    """Whether monthly CMI times 12 is above the district's annual median income.

    Income exactly at the median counts as below it (DIG-136): 11 U.S.C. § 707(b)(7) reads
    "equal to or less than", and Form 122A-1 line 14a "less than or equal to". The means test
    and the packet both use this one comparison, so they never disagree at the median.
    """
    return cmi * 12 > median_income
