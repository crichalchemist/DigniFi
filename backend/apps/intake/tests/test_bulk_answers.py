from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import FormAnswer, IntakeSession
from apps.users.models import User


@pytest.fixture
def auth_client_with_session(db):
    user = User.objects.create_user(username="bulktest", password="pass")
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


@pytest.mark.django_db
class TestBulkAnswerView:
    def test_bulk_upsert_handles_sofa_bindings(self, auth_client_with_session):
        client, session = auth_client_with_session
        from apps.intake.models import SOFAReport

        report = SOFAReport.objects.create(session=session)

        payload = {
            "answers": [
                {"form_type": "form_107", "binding": "answer:form_107.street", "value": "123 Main"},
                {
                    "form_type": "form_107",
                    "binding": "sofa.prior_income[0].source",
                    "value": "Acme Corp",
                },
                {
                    "form_type": "form_107",
                    "binding": "sofa.prior_income[0].year",
                    "value": "2023",
                },
                {
                    "form_type": "form_107",
                    "binding": "sofa.prior_income[0].gross_amount",
                    "value": "50000.00",
                },
                {"form_type": "form_107", "binding": "sofa.has_prior_income", "value": "True"},
            ]
        }
        response = client.post(
            f"/api/intake/sessions/{session.pk}/answers/bulk/", payload, format="json"
        )
        assert response.status_code == 200

        # Verify FormAnswer saved
        assert FormAnswer.objects.filter(field_key="street", value="123 Main").exists()

        # Verify SOFA saved
        assert report.prior_income.count() == 1
        assert report.prior_income.first().source == "Acme Corp"
        report.refresh_from_db()
        assert report.has_prior_income is True

    def test_bulk_upsert_empty_list(self, auth_client_with_session):
        client, session = auth_client_with_session
        response = client.post(
            f"/api/intake/sessions/{session.pk}/answers/bulk/",
            {"answers": []},
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 0
        assert data["updated"] == 0

    def test_bulk_upsert_invalid_prefix(self, auth_client_with_session):
        client, session = auth_client_with_session
        payload = {
            "answers": [
                {"form_type": "form_test", "binding": "invalid:q1", "value": "new"},
            ]
        }
        response = client.post(
            f"/api/intake/sessions/{session.pk}/answers/bulk/",
            payload,
            format="json",
        )
        assert response.status_code == 400
        data = response.json()
        assert "answers" in data

    def test_bulk_upsert_unknown_sofa_field(self, auth_client_with_session):
        client, session = auth_client_with_session
        payload = {
            "answers": [
                {"form_type": "form_test", "binding": "sofa.invalid_field", "value": "true"},
            ]
        }
        response = client.post(
            f"/api/intake/sessions/{session.pk}/answers/bulk/",
            payload,
            format="json",
        )
        assert response.status_code == 400
        data = response.json()
        assert "answers" in data

    def test_bulk_upsert_sofa_coercion_invalid(self, auth_client_with_session):
        client, session = auth_client_with_session
        payload = {
            "answers": [
                {
                    "form_type": "form_test",
                    "binding": "sofa.has_prior_income",
                    "value": "not a boolean",
                },
            ]
        }
        response = client.post(
            f"/api/intake/sessions/{session.pk}/answers/bulk/",
            payload,
            format="json",
        )
        assert response.status_code == 400
