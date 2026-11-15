"""The 122A-2 page's answers are stored encrypted, one record a session and one a secured debt, and a debt's answers go with it."""

import json
from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction

from apps.districts.models import District
from apps.intake.means_test import ANSWER_KEYS
from apps.intake.models import IntakeSession, MeansTestAnswers, SecuredDebtAnswers
from apps.intake.tests.builders import complete_debt
from apps.users.models import User


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="meansrecords", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def debt(session):
    return complete_debt(session, is_secured=True)


def _raw(table, column, key_column, key):
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {column} FROM {table} WHERE {key_column} = %s", [key])
        return cursor.fetchone()[0]


def test_every_answer_column_is_ciphertext(session, debt):
    MeansTestAnswers.objects.create(
        session=session,
        debts_answered_on="2026-10-16",
        answers=json.dumps({"line_3_rows": [{"purpose": "Demo purpose", "amount": "250.00"}]}),
    )
    SecuredDebtAnswers.objects.create(
        debt=debt,
        payments_left="37",
        payment_changes="no",
        total_60_months=Decimal("1234.56"),
        taxes_or_insurance="no",
        necessary_for_support="yes",
        cure=Decimal("600.00"),
    )
    checks = [
        ("means_test_answers", "answers", "session_id", session.pk, "Demo purpose"),
        ("means_test_answers", "debts_answered_on", "session_id", session.pk, "2026-10-16"),
    ]
    for column, plain in (
        ("payments_left", "37"),
        ("payment_changes", "no"),
        ("total_60_months", "1234.56"),
        ("taxes_or_insurance", "no"),
        ("necessary_for_support", "yes"),
        ("cure", "600.00"),
    ):
        checks.append(("secured_debt_answers", column, "debt_id", debt.pk, plain))
    for table, column, key_column, key, plain in checks:
        raw = _raw(table, column, key_column, key)
        assert raw.startswith("gAAAAA"), (table, column)
        if len(plain) >= 6:
            assert plain not in raw, (table, column)
        else:
            # a short value can sit inside a random token by chance
            assert raw != plain, (table, column)


def test_a_session_has_one_answers_record(session):
    MeansTestAnswers.objects.create(session=session)
    with pytest.raises(IntegrityError), transaction.atomic():
        MeansTestAnswers.objects.create(session=session)


def test_a_debt_has_one_answers_record(debt):
    SecuredDebtAnswers.objects.create(debt=debt)
    with pytest.raises(IntegrityError), transaction.atomic():
        SecuredDebtAnswers.objects.create(debt=debt)


def test_a_debts_answers_go_with_the_debt(debt):
    SecuredDebtAnswers.objects.create(debt=debt, payments_left="12")
    debt.delete()
    assert SecuredDebtAnswers.objects.count() == 0


def test_merge_sets_only_the_keys_sent_and_replaces_a_list_whole(session):
    record = MeansTestAnswers(session=session)
    record.merge(
        {
            "line_3_answer": "yes",
            "line_3_rows": [{"purpose": "Demo A", "amount": "1.00"}, {"purpose": "Demo B"}],
            "line_15_amount": "40.00",
        }
    )
    record.merge({"line_3_rows": [{"purpose": "Demo C", "amount": "2.00"}], "line_15_amount": None})
    stored = record.get_answers()
    assert stored["line_3_answer"] == "yes"
    assert stored["line_3_rows"] == [{"purpose": "Demo C", "amount": "2.00"}]
    assert stored["line_15_amount"] is None


def test_merge_refuses_a_key_the_page_doesnt_ask(session):
    record = MeansTestAnswers(session=session)
    record.merge({"line_3_answer": "no"})
    with pytest.raises(KeyError) as refused:
        record.merge({"line_3_answer": "yes", "line_99_secret": "x"})
    assert "line_99_secret" not in str(refused.value)
    assert record.get_answers() == {"line_3_answer": "no"}


def test_a_spouse_rows_id_is_never_reused(session):
    record = MeansTestAnswers(session=session)
    assert record.new_spouse_ref("spouse_vehicles") == "spouse-1"
    assert record.new_spouse_ref("spouse_vehicles") == "spouse-2"
    assert record.new_spouse_ref("spouse_loans") == "spouse-1"
    with pytest.raises(KeyError):
        record.new_spouse_ref("line_3_rows")


def test_answered_on_reads_the_stored_day(session):
    record = MeansTestAnswers.objects.create(session=session)
    assert record.answered_on() is None
    record.debts_answered_on = "2026-10-16"
    record.save()
    record = MeansTestAnswers.objects.get(pk=record.pk)
    assert record.answered_on() == date(2026, 10, 16)


def test_the_page_asks_these_answers_in_this_order():
    assert ANSWER_KEYS == (
        "line_3_answer",
        "line_3_rows",
        "spouse_vehicles_answer",
        "spouse_vehicles",
        "spouse_loans_answer",
        "spouse_loans",
        "vehicle_claims",
        "vehicle_choice",
        "line_15_answer",
        "line_15_amount",
        "line_16",
        "line_17",
        "line_18",
        "line_19",
        "line_20",
        "line_21",
        "line_22_answer",
        "line_22_amount",
        "line_23",
        "line_25_answer",
        "line_25_health",
        "line_25_disability",
        "line_25_hsa",
        "line_25_spends",
        "line_25_actual",
        "line_26_answer",
        "line_26_amount",
        "line_27_answer",
        "line_27_amount",
        "line_28_answer",
        "line_28_amount",
        "line_29_answer",
        "line_29_amount",
        "line_30_answer",
        "line_30_amount",
        "line_31_answer",
        "line_31_amount",
        "line_34_answer",
        "line_36_answer",
        "line_36_payment",
        "line_43_answer",
        "line_43_circumstances",
    )


def test_deleting_the_session_deletes_its_answers(session):
    MeansTestAnswers.objects.create(session=session)
    session.delete()
    assert MeansTestAnswers.objects.count() == 0
