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
    def test_bulk_upsert_creates_and_updates(self, auth_client_with_session):
        client, session = auth_client_with_session
        FormAnswer.objects.create(
            session=session, form_type="form_test", field_key="q1", value="old"
        )
        payload = {
            "answers": [
                {"form_type": "form_test", "binding": "answer:q1", "value": "new"},
                {"form_type": "form_test", "binding": "answer:q2", "value": "brand new"},
                {"form_type": "form_test", "binding": "sofa.has_prior_income", "value": "true"},
            ]
        }
        response = client.post(
            f"/api/intake/sessions/{session.pk}/answers/bulk/",
            payload,
            format="json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 2
        assert data["updated"] == 1

        answers = FormAnswer.objects.filter(session=session).order_by("field_key")
        assert answers.count() == 2
        assert answers[0].value == "new"
        assert answers[0].field_key == "q1"
        assert answers[1].value == "brand new"
        assert answers[1].field_key == "q2"

        from apps.intake.models import SOFAReport

        sofa = SOFAReport.objects.get(session=session)
        assert sofa.has_prior_income is True

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
