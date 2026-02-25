"""
Tests for the registry-based form generation API endpoints.

Covers:
  - POST /api/forms/generate/       (single form)
  - POST /api/forms/generate_all/   (bulk generation)
  - POST /api/forms/preview/        (preview without DB write)
  - POST /api/forms/{id}/regenerate/
  - POST /api/forms/{id}/mark_downloaded/
  - POST /api/forms/{id}/mark_filed/
  - Permission enforcement (users see only their own sessions)
  - Error handling (missing session, invalid form_type)
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.models import GeneratedForm
from apps.forms.registry import get_all_form_types
from apps.intake.models import (
    DebtorInfo,
    IncomeInfo,
    IntakeSession,
)

User = get_user_model()

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testfiler",
        email="filer@example.com",
        password="testpass123",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="otherfiler",
        email="other@example.com",
        password="testpass456",
    )


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauth_client():
    return APIClient()


@pytest.fixture
def district(db):
    return District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court, Northern District of Illinois",
        pro_se_efiling_allowed=False,
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def session(user, district):
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def session_with_debtor(session):
    """Session with debtor info — minimum data most generators need."""
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        middle_name="",
        ssn="123-45-6789",
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


@pytest.fixture
def session_with_income(session_with_debtor):
    """Session with debtor + income info for means test generators."""
    IncomeInfo.objects.create(
        session=session_with_debtor,
        marital_status="single",
        number_of_dependents=0,
        monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
    )
    return session_with_debtor


@pytest.fixture
def other_session(other_user, district):
    return IntakeSession.objects.create(user=other_user, district=district)


# ── Generate Endpoint ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestGenerateEndpoint:
    """POST /api/forms/generate/"""

    URL = "/api/forms/generate/"

    def test_generate_form_101(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_101"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "form" in resp.data
        assert resp.data["form"]["form_type"] == "form_101"
        assert resp.data["form"]["status"] == "generated"

        # Verify DB record created
        assert GeneratedForm.objects.filter(
            session=session_with_debtor, form_type="form_101"
        ).exists()

    def test_generate_form_106dec(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_106dec"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["form"]["form_type"] == "form_106dec"

    def test_generate_schedule_a_b(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "schedule_a_b"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["form"]["form_type"] == "schedule_a_b"

    def test_generate_schedule_i(self, api_client, session_with_income):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_income.id, "form_type": "schedule_i"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["form"]["form_type"] == "schedule_i"

    def test_idempotent_regeneration(self, api_client, session_with_debtor):
        """Calling generate twice for same form_type updates existing record."""
        for _ in range(2):
            resp = api_client.post(
                self.URL,
                {"session_id": session_with_debtor.id, "form_type": "form_106dec"},
                format="json",
            )
            assert resp.status_code == status.HTTP_200_OK

        assert (
            GeneratedForm.objects.filter(
                session=session_with_debtor, form_type="form_106dec"
            ).count()
            == 1
        )

    def test_missing_session_id(self, api_client):
        resp = api_client.post(
            self.URL, {"form_type": "form_101"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "session_id" in resp.data["error"]

    def test_missing_form_type(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "form_type" in resp.data["error"]

    def test_invalid_form_type(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_999"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "valid_types" in resp.data

    def test_other_users_session_forbidden(self, api_client, other_session):
        resp = api_client.post(
            self.URL,
            {"session_id": other_session.id, "form_type": "form_101"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated(self, unauth_client, session_with_debtor):
        resp = unauth_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_101"},
            format="json",
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ── Generate All Endpoint ─────────────────────────────────────────────


@pytest.mark.django_db
class TestGenerateAllEndpoint:
    """POST /api/forms/generate_all/"""

    URL = "/api/forms/generate_all/"

    def test_generates_multiple_forms(self, api_client, session_with_income):
        """Should attempt all 13 form types; some may error due to missing data."""
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_income.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert "generated" in resp.data
        assert "errors" in resp.data
        total = resp.data["total_generated"] + resp.data["total_errors"]
        assert total == len(get_all_form_types())

    def test_missing_session_id(self, api_client):
        resp = api_client.post(self.URL, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_other_users_session(self, api_client, other_session):
        resp = api_client.post(
            self.URL, {"session_id": other_session.id}, format="json"
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── Preview Endpoint ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestPreviewEndpoint:
    """POST /api/forms/preview/"""

    URL = "/api/forms/preview/"

    def test_preview_returns_data_without_db_write(
        self, api_client, session_with_debtor
    ):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_106dec"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["preview"] is True
        assert "upl_disclaimer" in resp.data
        assert "data" in resp.data

        # No DB record should exist
        assert not GeneratedForm.objects.filter(
            session=session_with_debtor, form_type="form_106dec"
        ).exists()

    def test_preview_invalid_form_type(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "nope"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_preview_missing_session(self, api_client):
        resp = api_client.post(
            self.URL, {"form_type": "form_101"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ── Regenerate Endpoint ───────────────────────────────────────────────


@pytest.mark.django_db
class TestRegenerateEndpoint:
    """POST /api/forms/{id}/regenerate/"""

    def test_regenerate_existing_form(self, api_client, session_with_debtor, user):
        form = GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_106dec",
            form_data={"old": "data"},
            status="generated",
            generated_by=user,
        )

        resp = api_client.post(f"/api/forms/{form.id}/regenerate/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["message"] == "Form regenerated successfully"

        form.refresh_from_db()
        assert form.form_data != {"old": "data"}

    def test_regenerate_other_users_form(
        self, api_client, other_session, other_user
    ):
        form = GeneratedForm.objects.create(
            session=other_session,
            form_type="form_101",
            form_data={},
            status="generated",
            generated_by=other_user,
        )
        resp = api_client.post(f"/api/forms/{form.id}/regenerate/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── Status Transition Endpoints ───────────────────────────────────────


@pytest.mark.django_db
class TestStatusTransitions:

    def test_mark_downloaded(self, api_client, session_with_debtor, user):
        form = GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_101",
            form_data={"test": True},
            status="generated",
            generated_by=user,
        )
        resp = api_client.post(f"/api/forms/{form.id}/mark_downloaded/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "downloaded"

    def test_mark_downloaded_idempotent_on_non_generated(
        self, api_client, session_with_debtor, user
    ):
        """Only transitions from 'generated' — already-downloaded stays put."""
        form = GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_101",
            form_data={},
            status="downloaded",
            generated_by=user,
        )
        resp = api_client.post(f"/api/forms/{form.id}/mark_downloaded/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "downloaded"

    def test_mark_filed(self, api_client, session_with_debtor, user):
        form = GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_101",
            form_data={},
            status="downloaded",
            generated_by=user,
        )
        resp = api_client.post(f"/api/forms/{form.id}/mark_filed/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "filed"


# ── List / Retrieve ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestListRetrieve:

    def test_list_only_own_forms(self, api_client, session_with_debtor, user, other_session, other_user):
        GeneratedForm.objects.create(
            session=session_with_debtor, form_type="form_101",
            form_data={}, generated_by=user,
        )
        GeneratedForm.objects.create(
            session=other_session, form_type="form_101",
            form_data={}, generated_by=other_user,
        )

        resp = api_client.get("/api/forms/")
        assert resp.status_code == status.HTTP_200_OK
        # Response is paginated
        results = resp.data.get("results", resp.data)
        if isinstance(results, list):
            assert len(results) == 1
            assert results[0]["session"] == session_with_debtor.id
        else:
            assert resp.data["count"] == 1

    def test_retrieve_own_form(self, api_client, session_with_debtor, user):
        form = GeneratedForm.objects.create(
            session=session_with_debtor, form_type="form_101",
            form_data={"test": True}, generated_by=user,
        )
        resp = api_client.get(f"/api/forms/{form.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["form_type"] == "form_101"

    def test_retrieve_other_users_form_404(self, api_client, other_session, other_user):
        form = GeneratedForm.objects.create(
            session=other_session, form_type="form_101",
            form_data={}, generated_by=other_user,
        )
        resp = api_client.get(f"/api/forms/{form.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
