"""The means test reads only the U.S. Trustee's and the Bankruptcy Code's own figures, each in force on the fill date, and refuses on a day with none."""

import logging
from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from apps.districts.counties import ILND_COUNTIES
from apps.districts.dated_tables import NoTableInForce
from apps.districts.means_standards import (
    MEANS_STANDARDS_TABLE,
    NO_MEANS_TEST_TABLE,
    SECTION_104_TABLE,
    NoMeansTestTable,
    means_standards_in_force,
    section_104_in_force,
)
from apps.districts.models import MeansStandards, Section104Amounts

# The pin: this file's own copy of the figures, read from the U.S. Trustee's July 15, 2026 pages.
# county: ((insurance and operating, mortgage or rent) for 1, 2, 3, 4, 5 or more people)
EXPECTED_HOUSING = {
    "Cook": ((691, 1608), (811, 1889), (855, 1990), (953, 2219), (968, 2255)),
    "DuPage": ((600, 1854), (704, 2178), (742, 2295), (827, 2559), (841, 2600)),
    "Grundy": ((632, 1449), (743, 1701), (783, 1792), (873, 1998), (887, 2030)),
    "Kane": ((615, 1672), (722, 1964), (761, 2069), (848, 2307), (862, 2344)),
    "Kendall": ((632, 1662), (743, 1951), (783, 2056), (872, 2293), (887, 2330)),
    "Lake": ((614, 1886), (721, 2215), (760, 2334), (848, 2602), (861, 2645)),
    "LaSalle": ((622, 990), (730, 1163), (769, 1226), (858, 1366), (871, 1389)),
    "Will": ((631, 1655), (741, 1944), (780, 2049), (870, 2284), (884, 2321)),
    "Boone": ((561, 1188), (658, 1396), (694, 1470), (773, 1640), (786, 1666)),
    "Carroll": ((638, 741), (749, 871), (790, 917), (880, 1023), (895, 1039)),
    "DeKalb": ((600, 1351), (705, 1587), (743, 1672), (829, 1864), (842, 1894)),
    "Jo Daviess": ((604, 990), (709, 1163), (747, 1226), (833, 1367), (846, 1389)),
    "Lee": ((645, 904), (757, 1062), (798, 1119), (889, 1248), (904, 1268)),
    "McHenry": ((604, 1581), (709, 1857), (747, 1957), (833, 2182), (847, 2217)),
    "Ogle": ((603, 1058), (708, 1243), (746, 1310), (832, 1460), (845, 1484)),
    "Stephenson": ((611, 860), (718, 1010), (757, 1064), (844, 1186), (857, 1206)),
    "Whiteside": ((615, 773), (722, 908), (761, 957), (848, 1068), (862, 1084)),
    "Winnebago": ((579, 977), (680, 1148), (716, 1210), (798, 1349), (811, 1371)),
}
EXPECTED_CHICAGO = {
    "Cook",
    "DeKalb",
    "DuPage",
    "Grundy",
    "Kane",
    "Kendall",
    "Lake",
    "McHenry",
    "Will",
}

EXPECTED_FIGURES = (
    [
        ("national", "", size, amount)
        for size, amount in zip((1, 2, 3, 4), (867, 1558, 1857, 2176), strict=False)
    ]
    + [("national_extra", "", 0, 397)]
    + [
        ("five_percent", "", size, amount)
        for size, amount in zip((1, 2, 3, 4), (30, 53, 64, 76), strict=False)
    ]
    + [("five_percent_extra", "", 0, 14)]
    + [("health", "under_65", 0, 90), ("health", "65_or_older", 0, 163)]
    + [
        (kind, county, size, pair[column])
        for county, rows in EXPECTED_HOUSING.items()
        for size, pair in enumerate(rows, start=1)
        for kind, column in (("housing_operating", 0), ("housing_mortgage", 1))
    ]
    + [
        ("operating", "chicago", 1, 334),
        ("operating", "chicago", 2, 668),
        ("operating", "midwest", 1, 263),
        ("operating", "midwest", 2, 526),
    ]
    + [("ownership", "", 1, 703), ("ownership", "", 2, 1406)]
    + [("public_transport", "", 0, 220)]
    + [("multiplier", "ilnd", 0, Decimal("6.9"))]
)
EXPECTED_AREAS = [
    (county, "chicago" if county in EXPECTED_CHICAGO else "midwest") for county in EXPECTED_HOUSING
]

BEFORE_MEANS = [("districts", "0009_means_standards")]
WITH_STANDARDS = [("districts", "0010_means_standards_2026")]
WITH_BOTH = [("districts", "0011_section_104_2025")]
BEFORE_ANY = [("districts", "0008_delete_exemptionschedule")]

ON_POSTGRES = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="needs Postgres: real column types; CI runs it with config.settings.test_postgres",
)


def test_every_database_has_the_2026_us_trustee_figures_as_read_from_its_pages(db):
    standards = MeansStandards.objects.get()
    assert (standards.effective_date, standards.valid_through, standards.source_url) == (
        date(2026, 7, 15),
        None,
        "https://www.justice.gov/ust/means-testing/20260715",
    )
    assert sorted(standards.figures.values_list("kind", "key", "size", "amount")) == sorted(
        EXPECTED_FIGURES
    )
    assert sorted(standards.areas.values_list("county", "area")) == sorted(EXPECTED_AREAS)


def test_every_ilnd_county_has_housing_for_one_to_five_or_more_people_and_one_area(db):
    standards = MeansStandards.objects.get()
    for county in ILND_COUNTIES:
        for kind in ("housing_operating", "housing_mortgage"):
            assert sorted(
                standards.figures.filter(kind=kind, key=county).values_list("size", flat=True)
            ) == [1, 2, 3, 4, 5]
        assert standards.areas.filter(county=county).count() == 1


def test_the_district_multiplier_is_keyed_by_the_lower_case_district_code(db):
    assert MeansStandards.objects.get().figures.get(kind="multiplier").key == "ilnd"


def test_the_us_trustee_set_refuses_on_july_14_2026_and_applies_from_july_15(db, caplog):
    with caplog.at_level(logging.ERROR), pytest.raises(NoMeansTestTable) as refused:
        means_standards_in_force(date(2026, 7, 14))
    assert [r.getMessage() for r in caplog.records] == [
        "No IRS expense standards table in force on 2026-07-14 for district -"
    ]
    assert (refused.value.table, str(refused.value)) == (MEANS_STANDARDS_TABLE, NO_MEANS_TEST_TABLE)
    assert means_standards_in_force(date(2026, 7, 15)).effective_date == date(2026, 7, 15)


def test_a_newer_us_trustee_set_takes_over_on_its_own_effective_date(db):
    newer = MeansStandards.objects.create(
        effective_date=date(2027, 5, 15),
        source_url="https://www.justice.gov/ust/means-testing/synthetic",
    )
    assert means_standards_in_force(date(2027, 5, 14)).effective_date == date(2026, 7, 15)
    assert means_standards_in_force(date(2027, 5, 15)) == newer


def test_the_section_104_amounts_apply_through_march_31_2028_and_refuse_from_april_1(db, caplog):
    amounts = section_104_in_force(date(2028, 3, 31))
    assert (
        amounts.presumption_low,
        amounts.presumption_high,
        amounts.education_per_child_monthly,
        amounts.chapter_13_unsecured_limit,
        amounts.chapter_13_secured_limit,
    ) == (
        Decimal("10275.00"),
        Decimal("17150.00"),
        Decimal("214.58"),
        Decimal("526700.00"),
        Decimal("1580125.00"),
    )
    with caplog.at_level(logging.ERROR), pytest.raises(NoMeansTestTable) as refused:
        section_104_in_force(date(2028, 4, 1))
    assert refused.value.table == SECTION_104_TABLE
    assert [r.getMessage() for r in caplog.records] == [
        "No Bankruptcy Code dollar amounts table in force on 2028-04-01 for district -"
    ]


def test_no_means_test_table_says_its_own_sentence_and_links_nowhere():
    exc = NoMeansTestTable(MEANS_STANDARDS_TABLE, date(2026, 7, 14))
    assert isinstance(exc, NoTableInForce) and str(exc) == NO_MEANS_TEST_TABLE
    assert not hasattr(exc, "step") and not hasattr(exc, "page")


def test_two_us_trustee_sets_cannot_start_on_the_same_day(db):
    with pytest.raises(IntegrityError), transaction.atomic():
        MeansStandards.objects.create(effective_date=date(2026, 7, 15))


def test_the_fixtures_give_back_the_rows_a_transactional_test_needs(
    transactional_db, means_standards_2026, section_104_2025
):
    # A transactional test's teardown empties every table, the migrated rows included, and
    # pytest-django runs these tests after the db tests. The root fixtures put the rows back.
    assert MeansStandards.objects.get() == means_standards_2026
    assert (means_standards_2026.figures.count(), means_standards_2026.areas.count()) == (200, 18)
    assert Section104Amounts.objects.get() == section_104_2025
    assert section_104_2025.effective_date == date(2025, 4, 1)


# ── The data migrations (a migration, not a fixture) ──


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


def _counts(apps):
    return tuple(
        apps.get_model("districts", name).objects.count()
        for name in ("MeansStandards", "MeansFigure", "MeansArea", "Section104Amounts")
    )


def _round_trip(migrate):
    # Each step stops where the tables still exist: dropping 0009 drops them with their rows, so
    # only these stops show that a reverse of 0010 or 0011 removes its own rows.
    assert _counts(migrate(BEFORE_MEANS)) == (0, 0, 0, 0)
    assert _counts(migrate(WITH_STANDARDS)) == (1, 200, 18, 0)
    assert _counts(migrate(WITH_BOTH)) == (1, 200, 18, 1)
    assert _counts(migrate(WITH_STANDARDS)) == (1, 200, 18, 0)
    assert _counts(migrate(BEFORE_MEANS)) == (0, 0, 0, 0)
    assert _counts(migrate(WITH_BOTH)) == (1, 200, 18, 1)
    migrate(BEFORE_ANY)
    tables = connection.introspection.table_names()
    assert "districts_meansstandards" not in tables
    assert "districts_section104amounts" not in tables


@pytest.mark.slow
def test_undoing_the_means_test_tables_removes_their_rows_and_redoing_loads_them_once(migrate):
    _round_trip(migrate)


@pytest.mark.postgres
@ON_POSTGRES
def test_undoing_the_means_test_tables_removes_their_rows_on_postgres(migrate):
    _round_trip(migrate)
