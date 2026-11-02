"""The intake app's data migrations, run by Django's migration executor on prepared rows.

Business intent: a data migration rewrites what filers already saved. It must change exactly
the rows it names and nothing else, and undoing it must leave saved data as it is (spec §7.8).
"""

import json
from decimal import Decimal

import pytest
from cryptography.fernet import Fernet
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.districts.models import District
from apps.users.models import User

BEFORE_STEP_2 = [("intake", "0010_add_adversary_proceedings")]
BEFORE_BACKFILL = [("intake", "0011_assetinfo_personal_property")]
BACKFILL = [("intake", "0012_backfill_secured_debts")]
INCOME_COLUMNS = [("intake", "0013_incomeinfo_income_by_source")]
INCOME_SPLIT = [("intake", "0014_split_income_saved_as_zero")]
FEE_WAIVER_QUESTIONS = [("intake", "0015_feewaiverapplication_take_home_and_noncash")]
HOUSEHOLD = [("intake", "0016_household")]
MARRIAGE_ENCRYPTED = [("intake", "0017_incomeinfo_marital_status_encrypted")]
BEFORE_ENCRYPTION = [("intake", "0019_remove_incomeinfo_number_of_dependents")]
INCOME_ENCRYPTED = [("intake", "0022_incomeinfo_encrypt_swap")]
EXPENSES_ENCRYPTED = [("intake", "0025_expenseinfo_encrypt_swap")]
INCOME_SOURCES = [
    "monthly_gross_wages",
    "monthly_overtime",
    "monthly_tips",
    "monthly_rental_income",
    "monthly_pension",
    "monthly_social_security",
    "monthly_unemployment",
    "monthly_child_support",
    "monthly_alimony",
    "monthly_other_income",
]


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


def _income_rows(apps, saved_totals):
    """One session per saved six-month total, each holding only that total."""
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    IntakeSession = apps.get_model("intake", "IntakeSession")
    IncomeInfo = apps.get_model("intake", "IncomeInfo")
    for name, months in saved_totals.items():
        session = IntakeSession.objects.create(user_id=user.pk, district_id=district.pk)
        IncomeInfo.objects.create(session_id=session.pk, marital_status=name, monthly_income=months)


def _stored_income(apps):
    """Each row's saved total and the set of its ten amounts, keyed by the row's label."""
    IncomeInfo = apps.get_model("intake", "IncomeInfo")
    return {
        row.marital_status: (
            row.monthly_income,
            {getattr(row, field) for field in INCOME_SOURCES},
        )
        for row in IncomeInfo.objects.all()
    }


# Labelled through marital_status, which the migration doesn't read.
SAVED_TOTALS = {
    "above_zero": [3100, 3300, 3200, 3200, 3150, 3250],
    "zero": [0, 0, 0, 0, 0, 0],
    "no_months": [],
}
AFTER_THE_SPLIT = {
    "above_zero": (SAVED_TOTALS["above_zero"], {None}),
    "zero": (SAVED_TOTALS["zero"], {Decimal("0.00")}),
    "no_months": ([], {None}),
}


def test_a_saved_total_above_zero_waits_for_the_filer_and_zero_becomes_ten_zeros(migrate):
    # Nothing recorded the amount from each source, so only a $0 total can be split without
    # the filer: every source was $0. Any other total is kept for the Income step to show.
    apps = migrate(BACKFILL)
    _income_rows(apps, SAVED_TOTALS)

    apps = migrate(INCOME_SPLIT)

    assert _stored_income(apps) == AFTER_THE_SPLIT


def test_undoing_the_income_split_leaves_income_as_it_is(migrate):
    apps = migrate(BACKFILL)
    _income_rows(apps, SAVED_TOTALS)
    migrate(INCOME_SPLIT)

    apps = migrate(INCOME_COLUMNS)

    assert _stored_income(apps) == AFTER_THE_SPLIT


def test_saved_fee_waiver_applications_leave_the_new_questions_unanswered(migrate):
    # A stored False would print a sworn "No" on Form 103B line 3, and a stored amount a
    # take-home figure nobody gave, so rows saved before the questions existed stay empty.
    apps = migrate(INCOME_SPLIT)
    FeeWaiverApplication = apps.get_model("intake", "FeeWaiverApplication")
    FeeWaiverApplication.objects.create(
        session_id=_session(apps).pk,
        household_size=3,
        monthly_income=Decimal("3200.00"),
        monthly_expenses=Decimal("2560.00"),
        receives_public_benefits=True,
    )

    apps = migrate(FEE_WAIVER_QUESTIONS)

    FeeWaiverApplication = apps.get_model("intake", "FeeWaiverApplication")
    fw = FeeWaiverApplication.objects.get()
    assert fw.monthly_take_home_pay is None
    assert fw.receives_noncash_assistance is None
    assert fw.benefit_types == []
    assert (fw.household_size, fw.monthly_income, fw.monthly_expenses) == (
        3,
        Decimal("3200.00"),
        Decimal("2560.00"),
    )
    assert fw.receives_public_benefits is True


def _stored_marriage(apps):
    """The one income row's raw marital_status column, and its wages as the model reads them."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT marital_status FROM income_info")
        [(raw,)] = cursor.fetchall()
    return raw, apps.get_model("intake", "IncomeInfo").objects.get().monthly_gross_wages


def _run_and_undo_the_marriage_migration(migrate):
    """An old tax status saved before 0017: the row after 0017, then after undoing it."""
    apps = migrate(HOUSEHOLD)
    apps.get_model("intake", "IncomeInfo").objects.create(
        session_id=_session(apps).pk,
        marital_status="married_joint",
        monthly_gross_wages=Decimal("3000.00"),
    )
    return _stored_marriage(migrate(MARRIAGE_ENCRYPTED)), _stored_marriage(migrate(HOUSEHOLD))


def test_undoing_the_marriage_migration_restores_an_empty_column(migrate):
    # No tax status is a line 1 answer, so none carries over. Undone, the old column comes
    # back on a table with rows, empty in each, and the amounts are untouched both ways.
    after, undone = _run_and_undo_the_marriage_migration(migrate)
    assert after == (None, Decimal("3000.00"))
    assert undone == ("", Decimal("3000.00"))


@pytest.mark.postgres
@pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="needs Postgres: the undo on a real column type; CI runs it with config.settings.test_postgres",
)
def test_undoing_the_marriage_migration_restores_an_empty_column_on_postgres(migrate):
    after, undone = _run_and_undo_the_marriage_migration(migrate)
    assert (after, undone) == ((None, Decimal("3000.00")), ("", Decimal("3000.00")))
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT data_type, character_maximum_length FROM information_schema.columns"
            " WHERE table_name = 'income_info' AND column_name = 'marital_status'"
        )
        assert cursor.fetchone() == ("character varying", 30)


EXPENSE_AMOUNTS = [
    "rent_or_mortgage",
    "utilities",
    "home_maintenance",
    "vehicle_payment",
    "vehicle_insurance",
    "vehicle_maintenance",
    "food_and_groceries",
    "clothing",
    "medical_expenses",
    "childcare",
    "child_support_paid",
    "insurance_not_deducted",
    "other_expenses",
]


def _plaintext_rows(apps):
    """Four income rows, labelled through marital_status, and one expense row."""
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    IntakeSession = apps.get_model("intake", "IntakeSession")
    IncomeInfo = apps.get_model("intake", "IncomeInfo")
    ExpenseInfo = apps.get_model("intake", "ExpenseInfo")
    rows = {
        "months": {
            "monthly_gross_wages": Decimal("3000.00"),
            "monthly_overtime": None,
            "monthly_income": [3100, 3300, 3200, 3200, 3150, 3250],
        },
        "no_months": {"monthly_income": []},
        "none": {"monthly_income": None},
        "zero": dict.fromkeys(INCOME_SOURCES, Decimal("0.00")),
    }
    sessions = []
    for label, fields in rows.items():
        session = IntakeSession.objects.create(user_id=user.pk, district_id=district.pk)
        sessions.append(session)
        IncomeInfo.objects.create(session_id=session.pk, marital_status=label, **fields)
    ExpenseInfo.objects.create(
        session_id=sessions[0].pk,
        rent_or_mortgage=Decimal("1100.00"),
        utilities=Decimal("180.00"),
    )


def _values(apps):
    """Per label the ten amounts and the old total, plus the expense row's 13 amounts."""
    income = {}
    for row in apps.get_model("intake", "IncomeInfo").objects.all():
        months = row.monthly_income
        if isinstance(months, str):
            months = json.loads(months)
        income[row.marital_status] = (
            {field: getattr(row, field) for field in INCOME_SOURCES},
            months,
        )
    expense = apps.get_model("intake", "ExpenseInfo").objects.get()
    return income, {field: getattr(expense, field) for field in EXPENSE_AMOUNTS}


def _check_round_trip(before, after, undone):
    assert after == before and undone == before
    income, expenses = before
    assert income["months"][0]["monthly_overtime"] is None  # an empty amount stays empty, not 0
    assert income["no_months"][1] == []  # [] stays [], not NULL
    assert expenses["rent_or_mortgage"] == Decimal("1100.00")
    with connection.cursor() as cursor:  # NULL stays NULL, never the text 'null'
        cursor.execute("SELECT COUNT(*) FROM income_info WHERE monthly_income IS NULL")
        assert cursor.fetchone()[0] == 2  # "none" and "zero"


def _round_trip(migrate):
    apps = migrate(BEFORE_ENCRYPTION)
    _plaintext_rows(apps)
    before = _values(apps)
    after = _values(migrate(EXPENSES_ENCRYPTED))
    undone = _values(migrate(BEFORE_ENCRYPTION))
    return before, after, undone


def test_encrypting_income_and_expenses_keeps_every_saved_value_both_ways(migrate):
    _check_round_trip(*_round_trip(migrate))


def _check_ciphertext(migrate):
    apps = migrate(BEFORE_ENCRYPTION)
    _plaintext_rows(apps)
    migrate(EXPENSES_ENCRYPTED)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT monthly_gross_wages, monthly_income FROM income_info"
            " WHERE monthly_gross_wages IS NOT NULL AND monthly_overtime IS NULL"
        )
        wages, months = cursor.fetchone()
        cursor.execute("SELECT rent_or_mortgage FROM expense_info")
        (rent,) = cursor.fetchone()
    assert all(v.startswith("gAAAAA") for v in (wages, months, rent))
    assert "3000.00" not in wages and "[3100, 3300" not in months and "1100.00" not in rent


def test_encrypted_income_and_expenses_are_ciphertext_in_the_table(migrate):
    _check_ciphertext(migrate)


def _undo_refuses_a_foreign_value(migrate, table, column, target):
    apps = migrate(BEFORE_ENCRYPTION)
    _plaintext_rows(apps)
    migrate(EXPENSES_ENCRYPTED)
    foreign = Fernet(Fernet.generate_key()).encrypt(b"3000.00").decode()  # another key
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table} ORDER BY id LIMIT 1")
        (row_id,) = cursor.fetchone()
        cursor.execute(f"UPDATE {table} SET {column} = %s WHERE id = %s", [foreign, row_id])
    with pytest.raises(RuntimeError, match=rf"^{table} row {row_id} can't be read") as refused:
        migrate(target)
    assert "3000" not in str(refused.value) and foreign not in str(refused.value)


@pytest.mark.parametrize(
    "table,column,target",
    [
        ("income_info", "monthly_gross_wages", BEFORE_ENCRYPTION),
        ("income_info", "monthly_income", BEFORE_ENCRYPTION),
        ("expense_info", "rent_or_mortgage", INCOME_ENCRYPTED),
    ],
)
def test_undoing_the_encryption_refuses_a_value_it_cannot_read_rather_than_lose_it(
    migrate, table, column, target
):
    _undo_refuses_a_foreign_value(migrate, table, column, target)


ON_POSTGRES = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="needs Postgres: real column types; CI runs it with config.settings.test_postgres",
)


@pytest.mark.postgres
@ON_POSTGRES
def test_encrypting_income_and_expenses_keeps_every_saved_value_both_ways_on_postgres(migrate):
    def wages_type():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT data_type FROM information_schema.columns"
                " WHERE table_name = 'income_info' AND column_name = 'monthly_gross_wages'"
            )
            return cursor.fetchone()[0]

    apps = migrate(BEFORE_ENCRYPTION)
    _plaintext_rows(apps)
    before = _values(apps)
    after = _values(migrate(EXPENSES_ENCRYPTED))
    assert wages_type() == "text"
    undone = _values(migrate(BEFORE_ENCRYPTION))
    assert wages_type() == "numeric"
    _check_round_trip(before, after, undone)


@pytest.mark.postgres
@ON_POSTGRES
def test_encrypted_income_and_expenses_are_ciphertext_in_the_table_on_postgres(migrate):
    _check_ciphertext(migrate)


@pytest.mark.postgres
@ON_POSTGRES
def test_undoing_the_encryption_refuses_a_value_it_cannot_read_on_postgres(migrate):
    _undo_refuses_a_foreign_value(migrate, "income_info", "monthly_gross_wages", BEFORE_ENCRYPTION)
