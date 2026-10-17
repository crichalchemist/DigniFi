"""The median income table in force on the day the forms are filled (forms step 3a1 spec §3).

Business intent: the U.S. Trustee applies a new Census median table on a schedule, and the
table decides who is above the median, which forms a filer gets and what 122A-1 prints. So
the means test reads the table in force on the fill date, and when none is in force it
refuses in plain words instead of passing a filer on an out-of-date figure. Lookup tests set
their own date; the rest run on the root conftest's 2026-10-16.
"""

import importlib
import json
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.districts.dated_tables import NoTableInForce, in_force
from apps.districts.models import District, MedianIncome
from apps.eligibility.cmi import is_above_median
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.intake.models import IncomeInfo, IntakeSession
from apps.users.models import User

MEDIAN = "Census median income"
NO_MEDIAN_TABLE = (
    "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your "
    "forms. Please try again later."
)
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "ilnd_2025_data.json"
MIGRATION = "0003_medianincome_dated_table"


@pytest.fixture
def ilnd(db):
    """The real ILND data: the November 2025 and April 2026 median tables."""
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


def _fill_on(monkeypatch, day):
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: day)


def _single_filer(district, monthly_wages):
    user = User.objects.create_user(username="between", password="pw")
    session = IntakeSession.objects.create(user=user, district=district)
    IncomeInfo.objects.create(
        session=session,
        marital_status="single",
        number_of_dependents=0,
        monthly_gross_wages=Decimal(monthly_wages),
    )
    return session


@pytest.mark.parametrize(
    "fill_date,effective",
    [
        (date(2026, 3, 31), date(2025, 11, 1)),
        (date(2026, 4, 1), date(2026, 4, 1)),
        (date(2026, 10, 31), date(2026, 4, 1)),
    ],
    ids=["last_day_of_november_2025_table", "first_day_of_april_2026_table", "its_last_day"],
)
def test_the_newest_table_in_force_on_the_fill_date_is_the_one_used(ilnd, fill_date, effective):
    table = in_force(ilnd.median_incomes.all(), fill_date, MEDIAN, ilnd.code)

    assert table.effective_date == effective


# Tests past the fixture's last day build their own rows, so loading a newer table into the
# fixture changes none of them (docs/REFERENCE_TABLES.md).


@pytest.fixture
def ilcd(db):
    return District.objects.create(
        code="ilcd",
        name="Central District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )


SIZES = {f"family_size_{n}": Decimal(50000 + 10000 * n) for n in range(1, 9)}


def _table(district, effective_date, valid_through=None):
    return MedianIncome.objects.create(
        district=district,
        effective_date=effective_date,
        valid_through=valid_through,
        family_size_additional=Decimal("10000.00"),
        **SIZES,
    )


def test_an_older_open_ended_table_never_stands_in_for_a_newer_one_past_its_valid_through(ilcd):
    _table(ilcd, date(2025, 1, 1))
    _table(ilcd, date(2026, 4, 1), valid_through=date(2026, 10, 31))

    with pytest.raises(NoTableInForce) as refused:
        in_force(ilcd.median_incomes.all(), date(2026, 11, 1), MEDIAN, ilcd.code)

    assert refused.value.table == MEDIAN
    assert refused.value.on == date(2026, 11, 1)


def test_a_newest_table_past_its_valid_through_refuses_and_logs_only_the_table_date_and_district(
    ilcd, caplog
):
    _table(ilcd, date(2026, 4, 1), valid_through=date(2026, 10, 31))

    with pytest.raises(NoTableInForce) as refused:
        in_force(ilcd.median_incomes.all(), date(2026, 11, 1), MEDIAN, ilcd.code)

    assert str(refused.value) == NO_MEDIAN_TABLE
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (logging.ERROR, "No Census median income table in force on 2026-11-01 for district ilcd")
    ]


def test_no_table_started_yet_refuses_in_plain_words_and_logs_only_the_table_date_and_district(
    ilcd, caplog
):
    _table(ilcd, date(2026, 11, 1), valid_through=date(2027, 3, 31))

    with pytest.raises(NoTableInForce) as refused:
        in_force(ilcd.median_incomes.all(), date(2026, 10, 16), MEDIAN, ilcd.code)

    assert str(refused.value) == NO_MEDIAN_TABLE
    assert isinstance(refused.value, ValueError)
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (logging.ERROR, "No Census median income table in force on 2026-10-16 for district ilcd")
    ]


def test_an_open_ended_table_stays_in_force(ilcd):
    open_ended = _table(ilcd, date(2025, 1, 1))

    assert in_force(ilcd.median_incomes.all(), date(2030, 1, 1), MEDIAN) == open_ended


def test_a_filer_between_the_two_tables_is_above_the_median_until_april_1_and_below_from_it(
    ilnd, monkeypatch
):
    # $6,000 a month is $72,000 a year: above the November 2025 single-filer median
    # ($71,304) and below the April 2026 one ($73,180).
    session = _single_filer(ilnd, "6000.00")

    _fill_on(monkeypatch, date(2026, 3, 31))
    before = MeansTestCalculator(session).calculate()
    _fill_on(monkeypatch, date(2026, 4, 1))
    after = MeansTestCalculator(session).calculate()

    assert before["median_income_threshold"] == Decimal("71304.00")
    assert is_above_median(before["cmi"], before["median_income_threshold"])
    assert after["median_income_threshold"] == Decimal("73180.00")
    assert not is_above_median(after["cmi"], after["median_income_threshold"])


def test_the_means_test_records_the_median_table_it_used(ilnd):
    session = _single_filer(ilnd, "3000.00")

    MeansTestCalculator(session).calculate()

    assert session.means_test.get_calculation_details()["median_table"] == {
        "name": MEDIAN,
        "effective_date": "2026-04-01",
        "valid_through": "2026-10-31",
        "source_url": (
            "https://www.justice.gov/ust/eo/bapcpa/20260401/bci_data/median_income_table.htm"
        ),
    }


def test_every_median_row_in_the_fixture_says_when_it_ends_and_where_it_comes_from():
    rows = [
        row["fields"]
        for row in json.loads(FIXTURE.read_text())
        if row["model"] == "districts.medianincome"
    ]

    assert rows
    for row in rows:
        published = row["effective_date"].replace("-", "")
        assert row["valid_through"] > row["effective_date"]
        assert row["source_url"] == (
            f"https://www.justice.gov/ust/eo/bapcpa/{published}/bci_data/median_income_table.htm"
        )


@pytest.mark.parametrize(
    "effective,valid_through",
    [(date(2025, 11, 1), date(2026, 3, 31)), (date(2026, 4, 1), date(2026, 10, 31))],
)
def test_the_migration_ends_a_stored_row_the_day_before_the_next_census_update(
    effective, valid_through
):
    migration = importlib.import_module(f"apps.districts.migrations.{MIGRATION}")

    assert migration.census_valid_through(effective) == valid_through


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


def test_the_migration_dates_each_stored_row_and_names_the_page_it_comes_from(migrate):
    apps = migrate([("districts", "0002_alter_district_state_and_more")])
    district = apps.get_model("districts", "District").objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    for effective in (date(2025, 11, 1), date(2026, 4, 1)):
        apps.get_model("districts", "MedianIncome").objects.create(
            district_id=district.pk, effective_date=effective, **SIZES
        )

    apps = migrate([("districts", MIGRATION)])

    stored = apps.get_model("districts", "MedianIncome").objects.order_by("effective_date")
    assert [(row.valid_through, row.source_url) for row in stored] == [
        (
            date(2026, 3, 31),
            "https://www.justice.gov/ust/eo/bapcpa/20251101/bci_data/median_income_table.htm",
        ),
        (
            date(2026, 10, 31),
            "https://www.justice.gov/ust/eo/bapcpa/20260401/bci_data/median_income_table.htm",
        ),
    ]


# ── The extra-person amount comes from the table (spec §3.2) ──


def _april_2026_table(additional):
    return MedianIncome(family_size_8=Decimal("182302.00"), family_size_additional=additional)


def test_a_household_above_eight_adds_the_tables_own_amount_for_each_extra_person():
    assert _april_2026_table(Decimal("11100.00")).get_median_income(10) == Decimal("204502.00")


def test_a_household_above_eight_is_refused_when_the_table_has_no_extra_person_amount():
    with pytest.raises(ValueError, match="extra person"):
        _april_2026_table(None).get_median_income(9)
