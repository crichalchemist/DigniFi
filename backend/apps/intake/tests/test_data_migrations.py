"""The intake app's data migrations, run by Django's migration executor on prepared rows.

Business intent: a data migration rewrites what filers already saved. It must change exactly
the rows it names and nothing else, and undoing it must leave saved data as it is (spec §7.8).
"""

from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.districts.models import District
from apps.users.models import User

BEFORE_STEP_2 = [("intake", "0010_add_adversary_proceedings")]
BEFORE_BACKFILL = [("intake", "0011_assetinfo_personal_property")]
BACKFILL = [("intake", "0012_backfill_secured_debts")]


@pytest.fixture
def migrate(transactional_db):
    """Migrate the intake app to a migration and return the models as they were there.

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


def _session(apps):
    # The user and district tables are the same at every intake migration.
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    IntakeSession = apps.get_model("intake", "IntakeSession")
    return IntakeSession.objects.create(user_id=user.pk, district_id=district.pk)


def _debt(apps, session, creditor_name, debt_type, **fields):
    DebtInfo = apps.get_model("intake", "DebtInfo")
    return DebtInfo.objects.create(
        session_id=session.pk,
        creditor_name=creditor_name,
        debt_type=debt_type,
        amount_owed=Decimal("1000.00"),
        **fields,
    )


def test_stored_car_loans_and_mortgages_become_secured_and_no_other_debt_changes(migrate):
    apps = migrate(BEFORE_BACKFILL)
    session = _session(apps)
    _debt(apps, session, "Ally Auto", "auto_loan", collateral_description="2019 Toyota Camry")
    _debt(apps, session, "Chase Home Lending", "mortgage")
    _debt(apps, session, "Visa", "credit_card")
    _debt(
        apps,
        session,
        "Couch Store",
        "personal_loan",
        is_secured=True,
        collateral_description="Living room set",
    )

    apps = migrate(BACKFILL)

    DebtInfo = apps.get_model("intake", "DebtInfo")
    stored = {
        d.creditor_name: (d.is_secured, d.collateral_description) for d in DebtInfo.objects.all()
    }
    assert stored == {
        "Ally Auto": (True, "2019 Toyota Camry"),
        "Chase Home Lending": (True, ""),
        "Visa": (False, ""),
        "Couch Store": (True, "Living room set"),
    }


def test_undoing_the_secured_backfill_leaves_debts_as_they_are(migrate):
    apps = migrate(BEFORE_BACKFILL)
    _debt(apps, _session(apps), "Ally Auto", "auto_loan")
    migrate(BACKFILL)

    apps = migrate(BEFORE_BACKFILL)

    DebtInfo = apps.get_model("intake", "DebtInfo")
    assert DebtInfo.objects.get(creditor_name="Ally Auto").is_secured is True


def test_stored_other_assets_stay_other_once_personal_property_exists(migrate):
    apps = migrate(BEFORE_STEP_2)
    AssetInfo = apps.get_model("intake", "AssetInfo")
    AssetInfo.objects.create(
        session_id=_session(apps).pk,
        asset_type="other",
        description="Living room furniture",
        current_value=Decimal("900.00"),
    )

    apps = migrate(BACKFILL)

    AssetInfo = apps.get_model("intake", "AssetInfo")
    assert AssetInfo.objects.get(description="Living room furniture").asset_type == "other"
