"""The Debts step's secured flag and the Assets step's personal property save (DIG-26, DIG-47).

Business intent: a car loan or a mortgage is a secured claim (Schedule D) with the property
that secures it, so the flag and the collateral the Debts step sends must be stored, and read
back so a returning filer sees them. Household goods are on nearly every Schedule A/B, so
choosing "Personal Property" on the Assets step must save the step, not refuse it.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import AssetInfo, DebtInfo, IntakeSession
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
    session = IntakeSession.objects.create(user=user, district=district)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session


def _session_url(session):
    return f"/api/intake/sessions/{session.pk}/"


def test_car_loan_from_the_debts_step_saves_as_secured_with_its_collateral(filer):
    client, session = filer

    # The row as the Debts step sends it after the filer picks "Car or vehicle loan".
    response = client.patch(
        _session_url(session),
        {
            "debts": [
                {
                    "creditor_name": "Ally Auto",
                    "debt_type": "auto_loan",
                    "amount_owed": 8500,
                    "monthly_payment": 350,
                    "is_secured": True,
                    "priority_classification": "secured",
                    "collateral_description": "2019 Toyota Camry",
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    saved = DebtInfo.objects.get(session=session)
    assert saved.is_secured is True
    assert saved.collateral_description == "2019 Toyota Camry"
    [row] = client.get(_session_url(session)).data["debts"]
    assert row["is_secured"] is True
    assert row["collateral_description"] == "2019 Toyota Camry"


def test_debt_the_filer_changes_to_unsecured_saves_as_unsecured(filer):
    client, session = filer
    loan = DebtInfo.objects.create(
        session=session,
        creditor_name="Ally Auto",
        debt_type="auto_loan",
        priority_classification="secured",
        amount_owed=Decimal("8500.00"),
        is_secured=True,
        collateral_description="2019 Toyota Camry",
    )

    # The filer meant a credit card: the Debts step sends the new category's flag.
    response = client.patch(
        _session_url(session),
        {
            "debts": [
                {
                    "id": loan.pk,
                    "creditor_name": "Ally Card",
                    "debt_type": "credit_card",
                    "amount_owed": 8500,
                    "is_secured": False,
                    "priority_classification": "unsecured",
                    "collateral_description": "",
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    loan.refresh_from_db()
    assert loan.is_secured is False
    assert loan.collateral_description == ""
    [row] = client.get(_session_url(session)).data["debts"]
    assert row["is_secured"] is False


def test_filer_can_save_personal_property_on_the_assets_step(filer):
    client, session = filer

    response = client.patch(
        _session_url(session),
        {
            "assets": [
                {
                    "asset_type": "personal_property",
                    "description": "Furniture and household goods",
                    "current_value": 1200,
                },
                {"asset_type": "bank_account", "description": "Checking", "current_value": 300},
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    saved = {a.description: a.asset_type for a in AssetInfo.objects.filter(session=session)}
    assert saved == {
        "Furniture and household goods": "personal_property",
        "Checking": "bank_account",
    }
    received = client.get(_session_url(session)).data["assets"]
    assert {a["asset_type"] for a in received} == {"personal_property", "bank_account"}
