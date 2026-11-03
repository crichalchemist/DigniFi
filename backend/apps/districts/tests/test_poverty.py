"""The HHS poverty guideline in force on the day the forms are filled (3f spec §5).

Business intent: a judge may waive the Chapter 7 filing fee only for a family whose income is
less than 150% of the poverty guideline for its size (28 U.S.C. § 1930(f)(1)). DigniFi shows
that limit beside Form 101 line 8 as information, so it must be the court's own figure to the
cent, from the guideline last published on the fill date. It never shows last year's figure in
place of a missing one. The 2026 row is loaded by a data migration, so every database has it
without a loaddata step. Lookup tests set their own date; the rest run on the root conftest's
2026-10-16.
"""

import logging
from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from apps.districts.dated_tables import NoTableInForce
from apps.districts.models import PovertyGuideline
from apps.districts.poverty import (
    POVERTY_TABLE,
    poverty_guideline_in_force,
    poverty_limit_monthly,
)

SOURCE_2026 = (
    "https://www.federalregister.gov/documents/2026/01/15/2026-00755/"
    "annual-update-of-the-hhs-poverty-guidelines"
)
BEFORE_2026 = [("districts", "0004_povertyguideline")]
WITH_2026 = [("districts", "0005_poverty_guideline_2026")]

ON_POSTGRES = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="needs Postgres: real column types; CI runs it with config.settings.test_postgres",
)


def _fill_on(monkeypatch, day):
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: day)


def _guideline_2026():
    return PovertyGuideline(first_person=15960, each_additional=5680)


# ── The court's limit (§5) ──


@pytest.mark.parametrize(
    "family_size,limit",
    [
        (1, "1995.00"),
        (2, "2705.00"),
        (3, "3415.00"),
        (4, "4125.00"),
        (5, "4835.00"),
        (6, "5545.00"),
        (7, "6255.00"),
        (8, "6965.00"),
        (9, "7675.00"),
        (10, "8385.00"),
    ],
)
def test_the_2026_limit_is_the_courts_own_monthly_figure_for_every_family_size(family_size, limit):
    # uscourts.gov "150% of the HHS Poverty Guidelines for 2026": $1,995.00 for one person
    # and $710.00 for each person after, with no cap at eight.
    assert poverty_limit_monthly(_guideline_2026(), family_size) == Decimal(limit)


def test_a_limit_that_falls_between_cents_rounds_half_up():
    # $10,001 × 1.5 ÷ 12 = $1,250.125: half-up gives .13, where half-even would give .12.
    guideline = PovertyGuideline(first_person=10001, each_additional=0)

    assert poverty_limit_monthly(guideline, 1) == Decimal("1250.13")


@pytest.mark.parametrize("family_size", [0, -1])
def test_a_family_of_no_one_has_no_limit(family_size):
    with pytest.raises(ValueError, match="at least 1"):
        poverty_limit_monthly(_guideline_2026(), family_size)


# ── The 2026 row the migration loads (§5) ──


def test_every_database_has_the_2026_guideline_as_the_federal_register_published_it(db):
    row = PovertyGuideline.objects.get()

    assert (
        row.first_person,
        row.each_additional,
        row.effective_date,
        row.valid_through,
        row.source_url,
    ) == (15960, 5680, date(2026, 1, 15), date(2027, 1, 31), SOURCE_2026)


def test_every_stored_guideline_says_when_it_ends_and_where_it_comes_from(db):
    rows = list(PovertyGuideline.objects.all())

    assert rows
    for row in rows:
        assert row.valid_through is not None and row.valid_through > row.effective_date
        assert row.source_url.startswith("https://www.federalregister.gov/documents/")


def test_two_guidelines_cannot_start_on_the_same_day(db):
    with pytest.raises(IntegrityError), transaction.atomic():
        PovertyGuideline.objects.create(
            first_person=1, each_additional=1, effective_date=date(2026, 1, 15)
        )


# ── The guideline in force on the fill date (§5, U §4.3) ──


@pytest.mark.parametrize(
    "fill_date",
    [date(2026, 1, 15), date(2026, 10, 16), date(2027, 1, 31)],
    ids=["its_publication_day", "the_pinned_fill_day", "its_last_day"],
)
def test_the_2026_guideline_is_in_force_from_its_publication_through_january_2027(
    db, monkeypatch, fill_date
):
    _fill_on(monkeypatch, fill_date)

    assert poverty_guideline_in_force().effective_date == date(2026, 1, 15)


def test_the_lookup_takes_the_fill_date_unless_given_a_day(db):
    # The root conftest pins the fill date to 2026-10-16.
    assert poverty_guideline_in_force().effective_date == date(2026, 1, 15)
    with pytest.raises(NoTableInForce):
        poverty_guideline_in_force(date(2027, 2, 1))


@pytest.mark.parametrize(
    "fill_date,why",
    [(date(2026, 1, 14), "not_yet_published"), (date(2027, 2, 1), "past_its_valid_through")],
)
def test_no_guideline_in_force_refuses_and_logs_only_the_table_and_the_date(
    db, monkeypatch, caplog, fill_date, why
):
    _fill_on(monkeypatch, fill_date)

    with pytest.raises(NoTableInForce) as refused:
        poverty_guideline_in_force()

    assert refused.value.table == POVERTY_TABLE == "HHS poverty guidelines"
    assert refused.value.on == fill_date
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (
            logging.ERROR,
            f"No HHS poverty guidelines table in force on {fill_date.isoformat()} "
            "for district -",
        )
    ]


def test_a_newer_guideline_takes_over_from_its_own_publication_day(db):
    newer = PovertyGuideline.objects.create(
        first_person=16400,
        each_additional=5800,
        effective_date=date(2027, 1, 14),
        valid_through=date(2028, 1, 31),
        source_url="https://www.federalregister.gov/documents/2027/01/14/synthetic",
    )

    assert poverty_guideline_in_force(date(2027, 1, 13)).effective_date == date(2026, 1, 15)
    assert poverty_guideline_in_force(date(2027, 1, 14)) == newer


def test_a_transactional_test_still_finds_the_2026_guideline_through_the_root_fixture(
    transactional_db, poverty_2026
):
    # A transactional test's teardown empties every table, the migrated row included, and
    # pytest-django runs these tests after the db tests, so in a full run this one follows
    # test_dated_tables.py's flushing migration test. The root fixture puts the row back.
    assert poverty_guideline_in_force() == poverty_2026
    assert (
        poverty_2026.first_person,
        poverty_2026.each_additional,
        poverty_2026.effective_date,
        poverty_2026.valid_through,
        poverty_2026.source_url,
    ) == (15960, 5680, date(2026, 1, 15), date(2027, 1, 31), SOURCE_2026)


# ── The data migration (§5: a migration, not a fixture) ──


@pytest.fixture
def migrate(transactional_db):
    """Migrate the districts app to a migration and return the models as they were there.

    SQLite can't change a schema inside the test's transaction, hence transactional_db.
    Afterwards the database returns to the latest migrations for the tests that follow.
    """
    executor = MigrationExecutor(connection)

    def to(targets):
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    yield to
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


def _round_trip(migrate):
    before = migrate(BEFORE_2026).get_model("districts", "PovertyGuideline")
    assert before.objects.count() == 0

    after = migrate(WITH_2026).get_model("districts", "PovertyGuideline")
    assert list(
        after.objects.values_list(
            "first_person", "each_additional", "effective_date", "valid_through", "source_url"
        )
    ) == [(15960, 5680, date(2026, 1, 15), date(2027, 1, 31), SOURCE_2026)]


@pytest.mark.slow
def test_undoing_the_2026_guideline_removes_its_row_and_redoing_it_loads_it_once(migrate):
    _round_trip(migrate)


@pytest.mark.postgres
@ON_POSTGRES
def test_undoing_the_2026_guideline_removes_its_row_and_redoing_it_loads_it_once_on_postgres(
    migrate,
):
    _round_trip(migrate)
