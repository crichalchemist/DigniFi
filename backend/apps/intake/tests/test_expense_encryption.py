"""Expense amounts are stored encrypted and bounded (3e2 spec §3.1, §3.3).

Business intent: expenses are filer financial data, so a stored amount must never be readable
from the database alone, nor wider than the court forms' boxes. An empty body still saves
the row with $0 amounts (DIG-153).
"""

from decimal import Decimal

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import ExpenseInfo, IntakeSession
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


@pytest.mark.parametrize("field", EXPENSE_AMOUNTS)
def test_each_expense_amount_is_stored_as_ciphertext(filer, field):
    client, session = filer
    _save(client, session, {"expense_info": {field: "455.00"}})
    raw = _raw(f"SELECT {field} FROM expense_info WHERE session_id = %s", session)
    assert raw.startswith("gAAAAA") and "455.00" not in raw


def test_an_empty_expenses_body_still_creates_the_row_with_zero_amounts(filer):  # DIG-153
    client, session = filer
    response = _save(client, session, {"expense_info": {}})
    assert response.status_code == 200
    row = ExpenseInfo.objects.get(session=session)
    assert all(Decimal(getattr(row, f)) == 0 for f in EXPENSE_AMOUNTS)
    assert response.data["expense_info"]["rent_or_mortgage"] == "0.00"


@pytest.mark.parametrize("amount", ["-1.00", "100000000.00"], ids=["negative", "too_wide"])
def test_an_expense_amount_outside_the_forms_boxes_is_refused(filer, amount):
    client, session = filer
    assert _save(client, session, {"expense_info": {"utilities": amount}}).status_code == 400


def test_the_data_source_stays_plaintext(filer):  # not filer data (spec §3.1)
    client, session = filer
    _save(client, session, {"expense_info": {}})
    raw = _raw("SELECT data_source FROM expense_info WHERE session_id = %s", session)
    assert raw == "manual"
