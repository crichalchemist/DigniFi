"""Expenses the wizard saves land in the fields the means test and court forms read (DIG-45).

DRF drops unknown field names without an error. That is how the wizard's old names
(car_payment, food_groceries, other_necessary_expenses, ...) saved car, food and other
costs as $0. These tests pin the canonical names the Expenses step now sends.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import ExpenseInfo, IntakeSession
from apps.users.models import User

# One distinct amount per canonical ExpenseInfo field, as DRF returns it.
CANONICAL_EXPENSES = {
    "rent_or_mortgage": "1100.00",
    "utilities": "180.00",
    "home_maintenance": "25.00",
    "vehicle_payment": "310.00",
    "vehicle_insurance": "85.00",
    "vehicle_maintenance": "40.00",
    "food_and_groceries": "450.00",
    "clothing": "60.00",
    "medical_expenses": "75.00",
    "childcare": "400.00",
    "child_support_paid": "200.00",
    "insurance_not_deducted": "120.00",
    "other_expenses": "50.00",
}


@pytest.fixture
def filer_session(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    filer = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=filer, district=district)
    client = APIClient()
    client.force_authenticate(user=filer)
    return client, session


@pytest.mark.django_db
def test_expense_saved_under_each_canonical_name_is_stored_and_returned(filer_session):
    client, session = filer_session
    # The wizard sends plain numbers.
    payload = {name: float(amount) for name, amount in CANONICAL_EXPENSES.items()}

    resp = client.patch(
        f"/api/intake/sessions/{session.pk}/", {"expense_info": payload}, format="json"
    )

    assert resp.status_code == 200
    stored = ExpenseInfo.objects.get(session=session)
    for name, amount in CANONICAL_EXPENSES.items():
        assert getattr(stored, name) == Decimal(amount), name
    returned = client.get(f"/api/intake/sessions/{session.pk}/").json()["expense_info"]
    for name, amount in CANONICAL_EXPENSES.items():
        assert returned[name] == amount, name
    assert returned["total_monthly_expenses"] == 3095.0
