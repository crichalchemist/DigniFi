"""
Tests for IntakeSessionViewSet PATCH behaviour.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import DebtInfo, IntakeSession
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


def test_debts_patch_clears_is_draft(auth_client_with_session):
    """Saving the Debts step sets is_draft=False on all session debts."""
    client, session = auth_client_with_session
    DebtInfo.objects.create(
        session=session,
        creditor_name="Draft Bank",
        debt_type="credit_card",
        amount_owed="500.00",
        is_draft=True,
    )
    response = client.patch(
        f"/api/intake/sessions/{session.id}/",
        {
            "debts": [
                {"creditor_name": "Draft Bank", "debt_type": "credit_card", "amount_owed": "500.00"}
            ]
        },
        format="json",
    )
    assert response.status_code in (200, 201)
    assert not DebtInfo.objects.filter(session=session, is_draft=True).exists()
