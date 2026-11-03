"""Income amounts are stored encrypted and bounded (3e2 spec §3.1, §3.3).

Business intent: income is filer financial data, so a stored amount must never be readable
from the database alone, nor wider than the court forms' boxes.
"""

import json
from decimal import Decimal

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import IncomeInfo, IntakeSession
from apps.users.models import User


@pytest.fixture
def filer(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, IntakeSession.objects.create(user=user, district=district)


def _save(client, session, body):
    return client.patch(f"/api/intake/sessions/{session.pk}/", body, format="json")


def _raw(sql, session):
    with connection.cursor() as cursor:
        cursor.execute(sql, [session.pk])
        return cursor.fetchone()[0]


@pytest.mark.parametrize("field", IncomeInfo.SOURCE_FIELDS)
def test_each_income_amount_is_stored_as_ciphertext(filer, field):
    client, session = filer
    assert _save(client, session, {"income_info": {field: "3170.00"}}).status_code == 200
    raw = _raw(f"SELECT {field} FROM income_info WHERE session_id = %s", session)
    assert raw.startswith("gAAAAA") and "3170.00" not in raw  # a Fernet token
    assert getattr(IncomeInfo.objects.get(session=session), field) == Decimal("3170.00")


def test_the_old_six_month_total_is_stored_as_ciphertext_and_read_back_as_the_array(filer):
    client, session = filer
    IncomeInfo.objects.create(session=session, monthly_income=json.dumps([3100, 3300, 3200] * 2))
    raw = _raw("SELECT monthly_income FROM income_info WHERE session_id = %s", session)
    assert raw.startswith("gAAAAA") and "[3100, 3300" not in raw
    income = client.get(f"/api/intake/sessions/{session.pk}/").json()["income_info"]
    assert income["monthly_income"] == [3100, 3300, 3200] * 2


def test_a_blank_old_total_reads_back_as_null_not_the_text_null(filer):
    client, session = filer
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1.00"))
    assert _raw("SELECT monthly_income FROM income_info WHERE session_id = %s", session) is None
    income = client.get(f"/api/intake/sessions/{session.pk}/").json()["income_info"]
    assert income["monthly_income"] is None


@pytest.mark.parametrize("field", IncomeInfo.SOURCE_FIELDS)
@pytest.mark.parametrize(
    "amount",
    ["-1.00", "100000000.00", "NaN", "Infinity", "12.345"],
    ids=["negative", "too_wide", "nan", "infinite", "fraction_of_a_cent"],
)
def test_an_income_amount_outside_the_forms_boxes_is_refused(filer, field, amount):
    client, session = filer
    assert _save(client, session, {"income_info": {field: amount}}).status_code == 400
    assert not IncomeInfo.objects.filter(session=session).exists()


def test_a_blank_income_box_is_stored_empty_not_zero(filer):
    client, session = filer
    _save(
        client,
        session,
        {"income_info": {"monthly_gross_wages": "2000.00", "monthly_tips": None}},
    )
    assert IncomeInfo.objects.get(session=session).monthly_tips is None
