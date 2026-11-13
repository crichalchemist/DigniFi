"""The list of exemption laws in force on the day the forms are filled.

Schedule C's filer picks a law from one dated list. The list is looked up through `in_force` on
the fill date, like every dated table, and is refused in its own sentence when none applies.
"""

from datetime import date

from .dated_tables import NoTableInForce, fill_date, in_force
from .models import ExemptionCatalog

EXEMPTION_TABLE = "Illinois and federal exemption laws"
NO_EXEMPTION_CATALOG = (
    "DigniFi doesn't have the exemption laws for today's date yet, so it can't prepare Schedule C."
)


class NoExemptionCatalog(NoTableInForce):
    """No exemption list applies on the fill date; the refusal says so in Schedule C's words."""

    def __init__(self, table: str, on: date) -> None:
        self.table = table
        self.on = on
        ValueError.__init__(self, NO_EXEMPTION_CATALOG)


def exemption_catalog_in_force(on: date | None = None) -> ExemptionCatalog:
    """The catalog in force on `on`, or on the fill date when no day is given.

    Raises:
        NoExemptionCatalog: no list has started yet, or the newest one has ended. `in_force`
            logs it once, with the table and the date.
    """
    try:
        return in_force(ExemptionCatalog.objects.all(), on or fill_date(), EXEMPTION_TABLE)
    except NoTableInForce as exc:
        raise NoExemptionCatalog(exc.table, exc.on) from None
