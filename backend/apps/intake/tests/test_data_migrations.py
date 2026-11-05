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
from apps.forms.registry import packet
from apps.intake.models import IntakeSession as LiveIntakeSession
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
BEFORE = [("intake", "0027_expenseinfo_schedule_j_lines")]
SHIFT = [("intake", "0028_shift_current_step")]
FILING_FEE = [("intake", "0029_filingfee")]
WAIVER_CARRIED = [("intake", "0030_fee_waiver_applications_to_filing_fee")]
APPLICATION_DROPPED = [("intake", "0031_delete_feewaiverapplication")]
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


@pytest.mark.slow
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

    apps = migrate(BEFORE_BACKFILL)

    DebtInfo = apps.get_model("intake", "DebtInfo")
    assert DebtInfo.objects.get(creditor_name="Ally Auto").is_secured is True


@pytest.mark.slow
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


@pytest.mark.slow
def test_a_saved_total_above_zero_waits_for_the_filer_and_zero_becomes_ten_zeros(migrate):
    # Nothing recorded the amount from each source, so only a $0 total can be split without
    # the filer: every source was $0. Any other total is kept for the Income step to show.
    apps = migrate(BACKFILL)
    _income_rows(apps, SAVED_TOTALS)

    apps = migrate(INCOME_SPLIT)

    assert _stored_income(apps) == AFTER_THE_SPLIT

    apps = migrate(INCOME_COLUMNS)

    assert _stored_income(apps) == AFTER_THE_SPLIT


@pytest.mark.slow
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


@pytest.mark.slow
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


def _assert_ciphertext():
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


def _check_ciphertext(migrate):
    apps = migrate(BEFORE_ENCRYPTION)
    _plaintext_rows(apps)
    migrate(EXPENSES_ENCRYPTED)
    _assert_ciphertext()


@pytest.mark.slow
def test_encrypting_income_and_expenses_keeps_every_saved_value_both_ways(migrate):
    # The stored columns are also Fernet ciphertext once encrypted, never the plaintext.
    apps = migrate(BEFORE_ENCRYPTION)
    _plaintext_rows(apps)
    before = _values(apps)
    after = _values(migrate(EXPENSES_ENCRYPTED))
    _assert_ciphertext()
    undone = _values(migrate(BEFORE_ENCRYPTION))
    _check_round_trip(before, after, undone)


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


@pytest.mark.slow
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


INCOME_DETAIL = [("intake", "0026_income_detail")]


def _income_detail_round_trip(migrate):
    apps = migrate(EXPENSES_ENCRYPTED)
    session = _session(apps)
    apps.get_model("intake", "IncomeInfo").objects.create(
        session_id=session.pk,
        monthly_gross_wages=Decimal("3000.00"),
        monthly_rental_income=Decimal("900.00"),
    )
    apps.get_model("intake", "SpouseIncome").objects.create(
        session_id=session.pk, monthly_gross_wages=Decimal("1800.00")
    )

    def amounts(apps):
        income = apps.get_model("intake", "IncomeInfo").objects.get()
        spouse = apps.get_model("intake", "SpouseIncome").objects.get()
        return income, spouse

    apps = migrate(INCOME_DETAIL)
    income, spouse = amounts(apps)
    kept = (
        (income.monthly_gross_wages, income.monthly_rental_income, spouse.monthly_gross_wages),
        [
            (row.business_and_rental, row.income_now_different, row.next_entry_id)
            for row in (income, spouse)
        ],
        income.income_period_end,
    )
    income, spouse = amounts(migrate(EXPENSES_ENCRYPTED))
    undone = (
        income.monthly_gross_wages,
        income.monthly_rental_income,
        spouse.monthly_gross_wages,
    )
    return kept, undone


@pytest.mark.slow
def test_adding_the_income_detail_columns_keeps_saved_income_and_leaves_them_unanswered(migrate):
    kept, undone = _income_detail_round_trip(migrate)
    amounts = (Decimal("3000.00"), Decimal("900.00"), Decimal("1800.00"))
    assert kept == (amounts, [(None, None, 1), (None, None, 1)], None)
    assert undone == amounts


@pytest.mark.postgres
@ON_POSTGRES
def test_adding_the_income_detail_columns_keeps_saved_income_and_leaves_them_unanswered_on_postgres(
    migrate,
):
    kept, undone = _income_detail_round_trip(migrate)
    amounts = (Decimal("3000.00"), Decimal("900.00"), Decimal("1800.00"))
    assert kept == (amounts, [(None, None, 1), (None, None, 1)], None)
    assert undone == amounts


EXPENSE_LINES = [("intake", "0027_expenseinfo_schedule_j_lines")]
NEW_EXPENSE_AMOUNTS = [
    "real_estate_taxes",
    "home_insurance",
    "hoa_dues",
    "personal_care",
    "entertainment",
    "charitable_contributions",
    "taxes_not_deducted",
    "support_others",
    "other_property_mortgages",
    "other_property_taxes",
    "other_property_insurance",
    "other_property_upkeep",
    "other_property_hoa_dues",
]


def _schedule_j_lines_round_trip(migrate):
    apps = migrate(INCOME_DETAIL)
    session = _session(apps)
    apps.get_model("intake", "ExpenseInfo").objects.create(
        session_id=session.pk, rent_or_mortgage=Decimal("1100.00")
    )
    apps = migrate(EXPENSE_LINES)
    row = apps.get_model("intake", "ExpenseInfo").objects.get()
    kept = (
        row.rent_or_mortgage,
        [getattr(row, name) for name in NEW_EXPENSE_AMOUNTS],
        row.expenses_include_others,
        [row.taxes_specify, row.support_others_specify, row.other_expenses_specify],
    )
    undone = migrate(INCOME_DETAIL).get_model("intake", "ExpenseInfo").objects.get()
    return kept, undone.rent_or_mortgage


@pytest.mark.slow
def test_adding_the_schedule_j_lines_keeps_saved_expenses_and_leaves_line_3_unanswered(migrate):
    kept, undone = _schedule_j_lines_round_trip(migrate)
    assert kept == (Decimal("1100.00"), [0] * 13, None, ["", "", ""])
    assert undone == Decimal("1100.00")


@pytest.mark.postgres
@ON_POSTGRES
def test_adding_the_schedule_j_lines_keeps_saved_expenses_and_leaves_line_3_unanswered_on_postgres(
    migrate,
):
    kept, undone = _schedule_j_lines_round_trip(migrate)
    assert kept == (Decimal("1100.00"), [0] * 13, None, ["", "", ""])
    assert undone == Decimal("1100.00")


def _run_the_shift(migrate):
    apps = migrate(BEFORE)
    IntakeSession = apps.get_model("intake", "IntakeSession")
    first = _session(apps)
    rows = {
        step: IntakeSession.objects.create(
            user_id=first.user_id, district_id=first.district_id, current_step=step
        )
        for step in (1, 2, 3, 8, 0, 12)
    }
    apps = migrate(SHIFT)
    after = {
        step: apps.get_model("intake", "IntakeSession").objects.get(pk=row.pk).current_step
        for step, row in rows.items()
    }
    take_home = apps.get_model("intake", "IntakeSession").objects.create(
        user_id=first.user_id, district_id=first.district_id, current_step=3
    )
    apps = migrate(BEFORE)
    undone = {
        step: apps.get_model("intake", "IntakeSession").objects.get(pk=row.pk).current_step
        for step, row in rows.items()
    }
    return (
        after,
        undone,
        apps.get_model("intake", "IntakeSession").objects.get(pk=take_home.pk).current_step,
    )


def test_a_session_saved_before_take_home_pay_reopens_on_the_same_step(migrate):
    after, undone, take_home = _run_the_shift(migrate)
    assert after == {1: 1, 2: 2, 3: 4, 8: 9, 0: 0, 12: 12}
    assert undone == {1: 1, 2: 2, 3: 3, 8: 8, 0: 0, 12: 12}
    assert take_home == 3  # Take-home pay undone reads as the old Expenses


@pytest.mark.postgres
@ON_POSTGRES
def test_a_session_saved_before_take_home_pay_reopens_on_the_same_step_on_postgres(migrate):
    after, undone, take_home = _run_the_shift(migrate)
    assert after == {1: 1, 2: 2, 3: 4, 8: 9, 0: 0, 12: 12}
    assert undone == {1: 1, 2: 2, 3: 3, 8: 8, 0: 0, 12: 12}
    assert take_home == 3


def _filing_fee_round_trip(migrate):
    apps = migrate(SHIFT)
    session = _session(apps)
    apps = migrate(FILING_FEE)
    FilingFee = apps.get_model("intake", "FilingFee")
    FilingFee.objects.create(session_id=session.pk)
    row = FilingFee.objects.get()
    kept = (row.payment_choice, row.income_change_answer, row.installments_explanation)
    migrate(SHIFT)
    return kept, "filing_fees" in connection.introspection.table_names()


def test_the_filing_fee_record_starts_unanswered_and_undoing_it_drops_its_table(migrate):
    kept, table_left = _filing_fee_round_trip(migrate)
    assert kept == (None, None, "")
    assert table_left is False


@pytest.mark.postgres
@ON_POSTGRES
def test_the_filing_fee_record_starts_unanswered_and_undoing_it_drops_its_table_on_postgres(
    migrate,
):
    kept, table_left = _filing_fee_round_trip(migrate)
    assert kept == (None, None, "")
    assert table_left is False


def _applicants_before_the_drop(migrate):
    """Three sessions at 0029: one applied for the waiver, one applied and then chose
    installments on the filing-fee page, and one never applied."""
    apps = migrate(FILING_FEE)
    IntakeSession = apps.get_model("intake", "IntakeSession")
    applied = _session(apps)
    chose = IntakeSession.objects.create(user_id=applied.user_id, district_id=applied.district_id)
    never = IntakeSession.objects.create(user_id=applied.user_id, district_id=applied.district_id)
    FeeWaiverApplication = apps.get_model("intake", "FeeWaiverApplication")
    for session in (applied, chose):
        FeeWaiverApplication.objects.create(
            session_id=session.pk,
            household_size=3,
            monthly_take_home_pay=Decimal("2800.00"),
            receives_noncash_assistance=True,
            benefit_types=["SNAP (food stamps)"],
        )
    apps.get_model("intake", "FilingFee").objects.create(
        session_id=chose.pk, payment_choice="installments"
    )
    return applied.pk, chose.pk, never.pk


def _choices(apps):
    """Each stored line 8 answer by session, decrypted: payment_choice can't be filtered on."""
    return {
        f.session_id: f.payment_choice for f in apps.get_model("intake", "FilingFee").objects.all()
    }


def test_every_fee_waiver_applicant_keeps_the_waiver_and_103b_when_the_application_table_goes(
    migrate,
):
    # An applicant asked the court to waive the fee. Dropping the plaintext table must not
    # take that request out of the packet, and must not overwrite an answer the filer
    # already gave on the filing-fee page, or invent one for a filer who never applied.
    applied, chose, never = _applicants_before_the_drop(migrate)

    apps = migrate(APPLICATION_DROPPED)

    assert _choices(apps) == {applied: "waiver", chose: "installments"}
    assert "fee_waiver_applications" not in connection.introspection.table_names()
    with pytest.raises(LookupError):
        apps.get_model("intake", "FeeWaiverApplication")
    # APPLICATION_DROPPED is the leaf, so the live models read these rows as they are.
    packets = {pk: packet(LiveIntakeSession.objects.get(pk=pk)) for pk in (applied, chose, never)}
    assert ["form_103b" in packets[pk] for pk in (applied, chose, never)] == [True, False, False]


def test_the_carried_waiver_choice_is_ciphertext_in_the_table(migrate):
    # The migration writes through the encrypted field, so the answer is never plaintext
    # at rest (DIG-279), not even for one release.
    applied, _, _ = _applicants_before_the_drop(migrate)

    migrate(WAIVER_CARRIED)

    with connection.cursor() as cursor:
        cursor.execute("SELECT payment_choice FROM filing_fees WHERE session_id = %s", [applied])
        (raw,) = cursor.fetchone()
    assert raw.startswith("gAAAAA") and "waiver" not in raw


def _undo_the_drop(migrate):
    applied, chose, _ = _applicants_before_the_drop(migrate)
    migrate(APPLICATION_DROPPED)
    apps = migrate(FILING_FEE)
    applications = {
        fw.session_id: (
            fw.household_size,
            fw.monthly_take_home_pay,
            fw.receives_noncash_assistance,
            fw.benefit_types,
        )
        for fw in apps.get_model("intake", "FeeWaiverApplication").objects.all()
    }
    return (applied, chose), applications, _choices(apps)


def test_undoing_the_drop_gives_each_waiver_choice_a_bare_application(migrate):
    # Undone, a waiver filer's packet again holds 103B through an application, but the
    # typed answers are gone with the table: one person and nothing else, never a guess.
    # A filer who chose installments gets none, even though they once applied.
    (applied, chose), applications, choices = _undo_the_drop(migrate)
    assert applications == {applied: (1, None, None, [])}
    assert choices == {applied: "waiver", chose: "installments"}


@pytest.mark.postgres
@ON_POSTGRES
def test_dropping_and_restoring_the_application_table_keeps_each_waiver_choice_on_postgres(
    migrate,
):
    (applied, chose), applications, choices = _undo_the_drop(migrate)
    assert applications == {applied: (1, None, None, [])}
    assert choices == {applied: "waiver", chose: "installments"}
    assert "fee_waiver_applications" in connection.introspection.table_names()


ASSETS_ENCRYPTED = [("intake", "0034_assetinfo_encrypt_swap")]


def _stored_assets(apps):
    """The raw description and institution of the one asset row, and the row as the model reads it."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT description, financial_institution FROM asset_info")
        [raw] = cursor.fetchall()
    row = apps.get_model("intake", "AssetInfo").objects.get()
    return raw, row


def _run_and_undo_the_asset_encryption(migrate):
    apps = migrate(APPLICATION_DROPPED)
    apps.get_model("intake", "AssetInfo").objects.create(
        session_id=_session(apps).pk,
        asset_type="bank_account",
        description="Harborline checking",
        financial_institution="Harborline Bank",
        current_value=Decimal("412.00"),
    )
    return _stored_assets(migrate(ASSETS_ENCRYPTED)), _stored_assets(migrate(APPLICATION_DROPPED))


def _check_asset_round_trip(after, undone):
    raw_after, row = after
    assert row.description == "Harborline checking"
    assert row.financial_institution == "Harborline Bank"
    assert row.ab_line is None  # an old row is on no line, and nothing suggests one
    assert row.asset_type == "bank_account"
    assert row.current_value == Decimal("412.00")
    assert all(value.startswith("gAAAAA") for value in raw_after)
    assert not any("Harborline" in value for value in raw_after)
    raw_undone, old = undone
    assert raw_undone == ("Harborline checking", "Harborline Bank")
    assert (old.description, old.financial_institution) == raw_undone
    assert old.current_value == Decimal("412.00")


@pytest.mark.slow
def test_encrypting_asset_descriptions_keeps_every_saved_asset_both_ways(migrate):
    after, undone = _run_and_undo_the_asset_encryption(migrate)
    _check_asset_round_trip(after, undone)


@pytest.mark.slow
def test_undoing_the_asset_encryption_refuses_a_value_it_cannot_read_rather_than_lose_it(migrate):
    apps = migrate(APPLICATION_DROPPED)
    apps.get_model("intake", "AssetInfo").objects.create(
        session_id=_session(apps).pk,
        asset_type="bank_account",
        description="Harborline checking",
        current_value=Decimal("412.00"),
    )
    migrate(ASSETS_ENCRYPTED)
    foreign = Fernet(Fernet.generate_key()).encrypt(b"Harborline checking").decode()
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM asset_info")
        (row_id,) = cursor.fetchone()
        cursor.execute("UPDATE asset_info SET description = %s WHERE id = %s", [foreign, row_id])
    with pytest.raises(RuntimeError, match=rf"^asset_info row {row_id} can't be read") as refused:
        migrate(APPLICATION_DROPPED)
    assert "Harborline" not in str(refused.value) and foreign not in str(refused.value)


@pytest.mark.postgres
@ON_POSTGRES
def test_encrypting_asset_descriptions_keeps_every_saved_asset_both_ways_on_postgres(migrate):
    def description_type():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT data_type FROM information_schema.columns"
                " WHERE table_name = 'asset_info' AND column_name = 'description'"
            )
            return cursor.fetchone()[0]

    after, undone = _run_and_undo_the_asset_encryption(migrate)
    _check_asset_round_trip(after, undone)
    assert description_type() == "character varying"


def _undo_with_a_row_saved_after_3b(migrate):
    apps = migrate(ASSETS_ENCRYPTED)
    apps.get_model("intake", "AssetInfo").objects.create(
        session_id=_session(apps).pk,
        description="Harborline checking",
        ab_line="17",
        asset_type=None,
        current_value=None,
    )
    old = migrate(APPLICATION_DROPPED)
    return old.get_model("intake", "AssetInfo").objects.get()


@pytest.mark.slow
def test_undoing_the_asset_encryption_keeps_a_row_saved_after_3b_with_no_type_or_value(migrate):
    row = _undo_with_a_row_saved_after_3b(migrate)
    assert row.description == "Harborline checking"
    assert row.asset_type == ""
    assert row.current_value == Decimal("0")


@pytest.mark.postgres
@ON_POSTGRES
def test_undoing_the_asset_encryption_keeps_a_row_saved_after_3b_on_postgres(migrate):
    row = _undo_with_a_row_saved_after_3b(migrate)
    assert (row.asset_type, row.current_value) == ("", Decimal("0"))
