"""
Public tables that change on a schedule, and the one way to pick the table in force.

The day the forms are filled stands in for the filing date (forms step 3a1 spec §3.3), so
every lookup of a dated table takes fill_date(), and nothing else reads the clock for this.
"""

import logging
from datetime import date

from django.db import models
from django.db.models import QuerySet
from django.utils import timezone

logger = logging.getLogger(__name__)


class DatedTable(models.Model):
    """A row of a public table that applies from effective_date through valid_through."""

    effective_date = models.DateField(help_text="First day this table applies.")
    valid_through = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Last day before the table's next scheduled change. "
            "Empty means it stays in force until a newer row replaces it."
        ),
    )
    source_url = models.URLField(
        max_length=300, blank=True, default="", help_text="Where the table is published."
    )

    class Meta:
        abstract = True


class NoTableInForce(ValueError):
    """No row of a dated table applies on the fill date, and no older row stands in.

    Either no row has started yet, or the newest one that has is past its valid_through.
    """

    def __init__(self, table: str, on: date) -> None:
        self.table = table
        self.on = on
        super().__init__(
            "DigniFi doesn't have the income figures for today's date yet, so it can't "
            "prepare your forms. Please try again later."
        )


def _today() -> date:
    """Today in the pilot district's zone (TIME_ZONE). The root conftest pins it in tests."""
    return timezone.localdate()


def fill_date() -> date:
    """The day the forms are filled, which stands in for the filing date."""
    return _today()


def in_force(rows: QuerySet, on: date, table: str, district: str = "") -> models.Model:
    """The newest row effective on or before `on`, if its valid_through hasn't passed.

    Rows effective after `on` are ignored. When the newest row that has started ended before
    `on`, no older row is looked at: the table is refused, not replaced by an older one.

    Raises:
        NoTableInForce: no row has started yet, or the newest one that has is past its
            valid_through. Either way it is logged once with the table's name, the date and
            the district code, never the filer's data, since logs reach Sentry (DIG-105).
    """
    row = rows.filter(effective_date__lte=on).order_by("-effective_date").first()
    if row is None or (row.valid_through is not None and row.valid_through < on):
        logger.error(
            "No %s table in force on %s for district %s", table, on.isoformat(), district or "-"
        )
        raise NoTableInForce(table, on)
    return row
