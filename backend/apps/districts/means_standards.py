"""The means test's two dated sets, each in force on the day the forms are filled.

The U.S. Trustee's expense standards and the Bankruptcy Code's dollar amounts are looked up
through `in_force` on the fill date, like every dated table, and refused in one sentence when
none applies.
"""

from datetime import date

from .dated_tables import NoTableInForce, fill_date, in_force
from .models import MeansStandards, Section104Amounts

MEANS_STANDARDS_TABLE = "IRS expense standards"
SECTION_104_TABLE = "Bankruptcy Code dollar amounts"
# DRAFT: counsel C-24
NO_MEANS_TEST_TABLE = (
    "DigniFi doesn't have the means test figures for today's date yet, "
    "so it can't work out Form 122A-2."
)


class NoMeansTestTable(NoTableInForce):
    """No means test set applies on the fill date; the refusal says so in Form 122A-2's words."""

    def __init__(self, table: str, on: date) -> None:
        self.table = table
        self.on = on
        ValueError.__init__(self, NO_MEANS_TEST_TABLE)


def means_standards_in_force(on: date | None = None) -> MeansStandards:
    """The U.S. Trustee's standards in force on `on`, or on the fill date when no day is given.

    Raises:
        NoMeansTestTable: no set has started yet. `in_force` logs it once, with the table and
            the date.
    """
    try:
        return in_force(MeansStandards.objects.all(), on or fill_date(), MEANS_STANDARDS_TABLE)
    except NoTableInForce as exc:
        raise NoMeansTestTable(exc.table, exc.on) from None


def section_104_in_force(on: date | None = None) -> Section104Amounts:
    """The Bankruptcy Code's dollar amounts in force on `on`, or on the fill date.

    Raises:
        NoMeansTestTable: no set has started yet, or the newest one has ended. `in_force` logs
            it once, with the table and the date.
    """
    try:
        return in_force(Section104Amounts.objects.all(), on or fill_date(), SECTION_104_TABLE)
    except NoTableInForce as exc:
        raise NoMeansTestTable(exc.table, exc.on) from None
