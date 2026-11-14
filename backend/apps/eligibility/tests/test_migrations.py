"""The eligibility app's migrations, run by Django's migration executor on prepared rows.

Business intent: dropping the means test's old fee-waiver flag (3f spec §9) must keep every
stored means test result, since the packet and the dashboard's median notice read them, and
undoing it must give the column back without guessing a verdict. Encrypting the table's
amounts and results (3h1) must keep every stored value and start with no outcome.
"""

from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.districts.models import District
from apps.intake.models import IntakeSession
from apps.users.models import User

WITH_FLAG = [("eligibility", "0002_add_above_median_fields")]
WITHOUT_FLAG = [("eligibility", "0003_remove_meanstest_qualifies_for_fee_waiver")]

ON_POSTGRES = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="needs Postgres: real column types; CI runs it with config.settings.test_postgres",
)


@pytest.fixture
def migrate(transactional_db):
    """Migrate the eligibility app to a migration and return the models as they were there.

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


def _columns():
    with connection.cursor() as cursor:
        table = connection.introspection.get_table_description(cursor, "means_tests")
    return {column.name for column in table}


def _drop_and_undo(migrate):
    # Only the eligibility app moves, so the session and district are today's models.
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user_id=user.pk, district_id=district.pk)
    old = migrate(WITH_FLAG).get_model("eligibility", "MeansTest")
    row = old.objects.create(
        session_id=session.pk,
        district_id=district.pk,
        median_income_threshold=Decimal("110712.00"),
        calculated_cmi=Decimal("2800.00"),
        passes_means_test=True,
        qualifies_for_fee_waiver=True,
    )
    kept = migrate(WITHOUT_FLAG).get_model("eligibility", "MeansTest").objects.get(pk=row.pk)
    after = (kept.calculated_cmi, kept.median_income_threshold, kept.passes_means_test, _columns())
    undone = migrate(WITH_FLAG).get_model("eligibility", "MeansTest").objects.get(pk=row.pk)
    return after, (undone.calculated_cmi, undone.qualifies_for_fee_waiver)


@pytest.mark.slow
def test_dropping_the_fee_flag_keeps_every_means_test_result(migrate):
    (cmi, median, passes, columns), undone = _drop_and_undo(migrate)
    assert (cmi, median, passes) == (Decimal("2800.00"), Decimal("110712.00"), True)
    assert "qualifies_for_fee_waiver" not in columns and "calculated_cmi" in columns
    assert undone == (Decimal("2800.00"), False)  # the column returns empty, never a verdict


@pytest.mark.postgres
@ON_POSTGRES
def test_dropping_the_fee_flag_keeps_every_means_test_result_on_postgres(migrate):
    (cmi, median, passes, columns), undone = _drop_and_undo(migrate)
    assert (cmi, median, passes) == (Decimal("2800.00"), Decimal("110712.00"), True)
    assert "qualifies_for_fee_waiver" not in columns and "calculated_cmi" in columns
    assert undone == (Decimal("2800.00"), False)


BEFORE_ENCRYPTION = [("eligibility", "0003_remove_meanstest_qualifies_for_fee_waiver")]
ENCRYPTED = [("eligibility", "0006_meanstest_encrypt_swap")]
COLUMNS = (
    "calculated_cmi",
    "median_income_threshold",
    "total_allowable_expenses",
    "disposable_income",
    "priority_debts_monthly",
    "passes_above_median",
    "above_median_calculated",
)
VALUES = {
    "calculated_cmi": Decimal("3000.00"),
    "median_income_threshold": Decimal("71304.00"),
    "total_allowable_expenses": Decimal("1.11"),
    "disposable_income": Decimal("2.22"),
    "priority_debts_monthly": Decimal("3.33"),
    "passes_above_median": True,
    "above_median_calculated": False,
}


def _session_and_district():
    # Only the eligibility app moves, so the session and district are today's models.
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user_id=user.pk, district_id=district.pk)
    return session, district


def _raw(pk, column):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {column} FROM means_tests WHERE id = %s", [pk])
        return cursor.fetchone()[0]


def _encrypt_and_read(migrate):
    session, district = _session_and_district()
    old = migrate(BEFORE_ENCRYPTION).get_model("eligibility", "MeansTest")
    row = old.objects.create(
        session_id=session.pk, district_id=district.pk, passes_means_test=True, **VALUES
    )
    new = migrate(ENCRYPTED).get_model("eligibility", "MeansTest")
    raw = {name: _raw(row.pk, name) for name in COLUMNS}
    return raw, new.objects.get(pk=row.pk)


def _assert_kept_and_unreadable_in_the_table(raw, kept):
    for name in COLUMNS:
        assert str(raw[name]).startswith("gAAAAA"), name
        assert str(raw[name]) != str(VALUES[name]), name
        assert getattr(kept, name) == VALUES[name], name
    assert kept.passes_above_median is True and kept.above_median_calculated is False
    assert kept.outcome is None
    assert kept.passes_means_test is True


@pytest.mark.slow
def test_encrypting_the_means_test_keeps_every_value_and_starts_with_no_outcome(migrate):
    raw, kept = _encrypt_and_read(migrate)
    _assert_kept_and_unreadable_in_the_table(raw, kept)


@pytest.mark.slow
def test_undoing_the_encryption_gives_the_plaintext_columns_back(migrate):
    _, kept = _encrypt_and_read(migrate)
    undone = migrate(BEFORE_ENCRYPTION).get_model("eligibility", "MeansTest")
    back = undone.objects.get(pk=kept.pk)
    for name in COLUMNS:
        assert getattr(back, name) == VALUES[name], name
        assert type(getattr(back, name)) is type(VALUES[name]), name
    assert back.passes_means_test is True


@pytest.mark.postgres
@ON_POSTGRES
def test_encrypting_the_means_test_keeps_every_value_on_postgres(migrate):
    # The boolean columns are the reason for add/copy/swap: an in-place cast breaks on Postgres.
    raw, kept = _encrypt_and_read(migrate)
    _assert_kept_and_unreadable_in_the_table(raw, kept)
