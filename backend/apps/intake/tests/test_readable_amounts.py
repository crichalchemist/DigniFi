"""Filers can read back the amounts they entered (DIG-2).

Business intent: the wizard can only show, and safely re-save, an amount the API
returns. The session owner can read debt and asset amounts; the SSN and account
numbers stay write-only, and no one else can read any of it.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import AssetInfo, DebtInfo, DebtorInfo, IntakeSession
from apps.users.models import User

SSN = "900123456"
CARD_NUMBER = "4111222233334444"
LOAN_NUMBER = "998877665544"


@pytest.fixture
def filer_session(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=user, district=district)
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn=SSN,
        date_of_birth=date(1985, 6, 15),
        phone="3125551234",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    debt = DebtInfo.objects.create(
        session=session,
        creditor_name="Chase",
        debt_type="credit_card",
        account_number=CARD_NUMBER,
        amount_owed=Decimal("1234.56"),
    )
    asset = AssetInfo.objects.create(
        session=session,
        asset_type="vehicle",
        description="2015 Honda Civic",
        current_value=Decimal("8000.00"),
        amount_owed=Decimal("3000.00"),
        account_number=LOAN_NUMBER,
    )
    return session, debt, asset


def _client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_amounts_are_readable_while_ssn_and_account_numbers_stay_private(filer_session):
    session, debt, asset = filer_session
    client = _client_for(session.user)

    response = client.get(f"/api/intake/sessions/{session.pk}/")

    assert response.status_code == 200
    [debt_row] = response.data["debts"]
    [asset_row] = response.data["assets"]
    assert debt_row["amount_owed"] == "1234.56"
    assert asset_row["current_value"] == "8000.00"
    assert asset_row["amount_owed"] == "3000.00"
    assert "ssn" not in response.data["debtor_info"]
    assert "account_number" not in debt_row
    assert "account_number" not in asset_row
    for secret in (SSN, CARD_NUMBER, LOAN_NUMBER):
        assert secret.encode() not in response.content

    debt_response = client.get(f"/api/intake/debts/{debt.pk}/")
    asset_response = client.get(f"/api/intake/assets/{asset.pk}/")
    assert debt_response.data["amount_owed"] == "1234.56"
    assert asset_response.data["current_value"] == "8000.00"
    assert CARD_NUMBER.encode() not in debt_response.content
    assert LOAN_NUMBER.encode() not in asset_response.content


def test_only_the_owner_can_read_amounts(filer_session):
    session, debt, asset = filer_session
    stranger = _client_for(User.objects.create_user(username="stranger", password="pw"))

    for url in (
        f"/api/intake/sessions/{session.pk}/",
        f"/api/intake/debts/{debt.pk}/",
        f"/api/intake/assets/{asset.pk}/",
    ):
        assert stranger.get(url).status_code == 404
    for url in ("/api/intake/sessions/", "/api/intake/debts/", "/api/intake/assets/"):
        response = stranger.get(url)
        assert response.status_code == 200
        assert b"1234.56" not in response.content
        assert b"8000.00" not in response.content

    assert APIClient().get(f"/api/intake/sessions/{session.pk}/").status_code == 401
