"""
Tests for IntakeSessionViewSet PATCH behaviour.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import DebtInfo, DebtorInfo, IntakeSession
from apps.users.models import User


@pytest.fixture
def auth_client_with_session(db):
    """Return (authenticated APIClient, IntakeSession) for a fresh test user."""
    user = User.objects.create_user(username="viewtest", password="pass")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session


def test_a_scanned_debt_leaves_draft_state_only_when_the_filer_presses_continue(
    auth_client_with_session,
):
    """Continue on Amounts Owed (update_step 7) confirms scanned debts; an autosave doesn't."""
    client, session = auth_client_with_session
    draft = DebtInfo.objects.create(
        session=session,
        creditor_name="Draft Bank",
        debt_type="credit_card",
        amount_owed="500.00",
        is_draft=True,
    )
    url = f"/api/intake/sessions/{session.id}/"
    saved = client.patch(
        url,
        {
            "debts": [
                {
                    "id": draft.pk,
                    "creditor_name": "Draft Bank",
                    "debt_type": "credit_card",
                    "amount_owed": "500.00",
                }
            ]
        },
        format="json",
    )
    assert saved.status_code in (200, 201)
    assert DebtInfo.objects.filter(session=session, is_draft=True).exists()
    confirmed = client.post(f"{url}update_step/", {"current_step": 7}, format="json")
    assert confirmed.status_code == 200
    assert not DebtInfo.objects.filter(session=session, is_draft=True).exists()


def test_the_session_no_longer_reads_or_takes_household_size_or_filing_type(
    auth_client_with_session,
):
    """Step 1 stopped asking both (3e1 spec §4.3, §7): no step can set a joint filing or a
    household size, so the session takes neither and offers neither back."""
    client, session = auth_client_with_session
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900123456",
        date_of_birth=date(1985, 6, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="1 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    url = f"/api/intake/sessions/{session.id}/"
    sent = {"debtor_info": {"first_name": "Janet", "household_size": 4, "filing_type": "joint"}}
    assert client.patch(url, sent, format="json").status_code == 200
    debtor = DebtorInfo.objects.get(session=session)
    assert (debtor.first_name, debtor.household_size, debtor.filing_type) == (
        "Janet",
        1,
        "individual",
    )
    read = client.get(url).json()["debtor_info"]
    assert "household_size" not in read and "filing_type" not in read
