"""
Current monthly income (CMI), the one figure the means test, the above-median calculator
and the court forms share (forms step 2 spec §5.5).

CMI counts the filer's monthly income from every source the Income step asks about except
benefits under the Social Security Act, which 11 U.S.C. § 101(10A)(B) leaves out.
"""

from decimal import Decimal


class IncomeNotSplit(ValueError):
    """The filer hasn't entered their income by source, so CMI can't be worked out.

    A total saved before income was stored by source can't be split by anyone but the filer.
    """

    def __init__(self) -> None:
        super().__init__("Enter your income by source on the Income step.")


def current_monthly_income(income_info) -> Decimal:
    """The ten Income step amounts added up, without Social Security.

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
    return sum(
        (amount for field, amount in given.items() if field != "monthly_social_security"),
        Decimal("0"),
    )
