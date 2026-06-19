"""Tests for dischargeability endpoint."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import DebtInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def auth_client_with_student_loan(db):
    user = User.objects.create_user(username="discview", password="pass")
    district = District.objects.create(
        code="ILND",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtInfo.objects.create(
        session=session,
        creditor_name="Navient",
        amount_owed=Decimal("28000"),
        is_secured=False,
        is_priority=False,
        debt_type="student_loan",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session


@pytest.mark.django_db
class TestDischargeabilityView:
    def test_returns_classification(self, auth_client_with_student_loan):
        client, session = auth_client_with_student_loan
        url = reverse("intake-session-dischargeability", kwargs={"pk": session.pk})
        response = client.post(url)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["debt_type"] == "student_loan"
        assert data[0]["dischargeable"] is False
