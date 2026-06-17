"""
Tests for SOFAReportViewSet.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import IntakeSession, SOFAReport
from apps.users.models import User


@pytest.fixture
def auth_client_session(db):
    """Return (authenticated APIClient, IntakeSession)."""
    user = User.objects.create_user(username="sofatest", password="pass")
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


class TestSOFARetrieve:
    def test_returns_report_with_empty_rows(self, auth_client_session):
        client, session = auth_client_session
        # Create a report with one prior income row
        report = SOFAReport.objects.create(
            session=session, has_prior_income=True, has_creditor_payments=False
        )
        report.prior_income.create(year=2025, source="Wages", gross_amount="50000.00")

        url = f"/api/intake/sofa-report/{session.pk}/"
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["has_prior_income"] is True
        assert len(data["prior_income"]) == 1
        assert data["prior_income"][0]["source"] == "Wages"
        assert data["creditor_payments"] == []

    def test_404_for_wrong_user(self, auth_client_session):
        client, session = auth_client_session
        other = User.objects.create_user(username="other", password="pass")
        other_session = IntakeSession.objects.create(
            user=other,
            district=session.district,
        )

        url = f"/api/intake/sofa-report/{other_session.pk}/"
        response = client.get(url)
        assert response.status_code == 404

        response = client.patch(url, {"has_prior_income": True})
        assert response.status_code == 404

    def test_get_or_creates_report(self, auth_client_session):
        client, session = auth_client_session
        url = f"/api/intake/sofa-report/{session.pk}/"
        response = client.get(url)
        assert response.status_code == 200
        data = response.json()
        assert "has_prior_income" in data  # verify shape, not default value
        assert SOFAReport.objects.filter(session=session).exists()


class TestSOFAUpdate:
    def test_patch_sets_booleans(self, auth_client_session):
        client, session = auth_client_session
        url = f"/api/intake/sofa-report/{session.pk}/"

        response = client.patch(url, {"has_prior_income": True}, format="json")
        assert response.status_code == 200
        assert response.json()["has_prior_income"] is True

    def test_patch_replaces_prior_income_rows(self, auth_client_session):
        client, session = auth_client_session
        report = SOFAReport.objects.create(session=session)
        report.prior_income.create(year=2024, source="Old Job", gross_amount="30000.00")

        url = f"/api/intake/sofa-report/{session.pk}/"
        response = client.patch(
            url,
            {
                "prior_income": [
                    {"year": 2025, "source": "New Job", "gross_amount": "50000.00"},
                ]
            },
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["prior_income"]) == 1
        assert data["prior_income"][0]["source"] == "New Job"

    def test_patch_replaces_creditor_payment_rows(self, auth_client_session):
        client, session = auth_client_session
        report = SOFAReport.objects.create(session=session)
        report.creditor_payments.create(
            creditor_name="OldCred", total_paid="100.00", dates_of_payments="Jan 2025"
        )

        url = f"/api/intake/sofa-report/{session.pk}/"
        response = client.patch(
            url,
            {
                "has_creditor_payments": True,
                "creditor_payments": [
                    {
                        "creditor_name": "NewCred",
                        "total_paid": "500.00",
                        "dates_of_payments": "Monthly Jan-Mar 2026",
                    }
                ],
            },
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_creditor_payments"] is True
        assert len(data["creditor_payments"]) == 1
        assert data["creditor_payments"][0]["creditor_name"] == "NewCred"

    def test_patch_accepts_own_get_body_round_trip(self, auth_client_session):
        """The serializer must accept its own GET output PATCHed back.

        This is exactly what the frontend SOFAStep does: it GETs the report,
        spreads the whole object (`{...report}` — including read-only `id`,
        `session`, timestamps, and each row's own `id`), adds rows, and PATCHes
        the full body. The minimal-payload tests above never exercise this, so a
        serializer that chokes on its own echoed output ships a bug every SOFA
        user hits (Save & Continue silently fails — the catch in SOFAStep
        swallows it and navigation never fires).
        """
        client, session = auth_client_session
        url = f"/api/intake/sofa-report/{session.pk}/"

        # GET (get_or_create) — capture the serializer's own output verbatim.
        body = client.get(url).json()

        # Mutate the way the UI does: toggle gates on and append rows.
        body["has_prior_income"] = True
        body["prior_income"] = [
            {"year": 2025, "source": "Temp Agency", "gross_amount": "24000.00"},
        ]
        body["has_creditor_payments"] = True
        body["creditor_payments"] = [
            {
                "creditor_name": "Capital One",
                "total_paid": "1500.00",
                "dates_of_payments": "Monthly Jan-Mar 2026",
            },
        ]

        # PATCH the whole body back, exactly as the frontend does.
        response = client.patch(url, body, format="json")

        assert response.status_code == 200, response.content
        data = response.json()
        assert data["has_prior_income"] is True
        assert len(data["prior_income"]) == 1
        assert data["prior_income"][0]["source"] == "Temp Agency"
        assert len(data["creditor_payments"]) == 1
        assert data["creditor_payments"][0]["creditor_name"] == "Capital One"
