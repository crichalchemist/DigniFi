"""
Tests for the form generation API endpoints.

Covers:
  - GET  /api/forms/packet/?session=<id>
  - POST /api/forms/generate/       (single form)
  - POST /api/forms/generate_all/   (every form in the packet)
  - POST /api/forms/{id}/regenerate/
  - POST /api/forms/{id}/mark_downloaded/
  - POST /api/forms/{id}/mark_filed/
  - Permission enforcement (users see only their own sessions)
  - The error contract: 422 with a reason, 500 logged by type only
  - The encrypted snapshot never leaves the server
"""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.models import GeneratedForm
from apps.intake.models import (
    DebtorInfo,
    IncomeInfo,
    IntakeSession,
)

User = get_user_model()

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def template_version_form(generated_form_factory):
    return generated_form_factory(status="generated")


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
        ssn="900-12-3456",  # IRS-reserved range: synthetic
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
        resp = api_client.post(self.URL, {"form_type": "form_101"}, format="json")
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

    def test_form_outside_the_packet_is_refused(self, api_client, session_with_debtor):
        # Without a fee waiver application, Form 103B would print a $0 application.
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_103b"},
            format="json",
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.data == {
            "form_type": "form_103b",
            "error": "This form isn't part of your packet.",
        }

    def test_missing_data_is_named_instead_of_filled_blank(self, api_client, session):
        resp = api_client.post(
            self.URL,
            {"session_id": session.id, "form_type": "form_121"},
            format="json",
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "name and address" in resp.data["error"]
        assert not GeneratedForm.objects.filter(session=session).exists()

    def test_unexpected_failure_logs_only_its_type(self, api_client, session_with_debtor, caplog):
        with patch(
            "apps.forms.views.build_field_values", side_effect=ValueError("900-12-3456 leaked")
        ):
            resp = api_client.post(
                self.URL,
                {"session_id": session_with_debtor.id, "form_type": "form_101"},
                format="json",
            )
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "900-12-3456" not in json.dumps(resp.data)
        assert "900-12-3456" not in caplog.text
        assert "ValueError" in caplog.text


# ── Generate All Endpoint ─────────────────────────────────────────────


@pytest.mark.django_db
class TestGenerateAllEndpoint:
    """POST /api/forms/generate_all/"""

    URL = "/api/forms/generate_all/"

    def test_generates_every_form_in_the_packet(self, api_client, session_with_income):
        """One form's missing data is reported and doesn't undo the others."""
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_income.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        # No fee waiver: no 103B. No means test yet: 122A-1 can't fill, and no 122A-2.
        assert resp.data["errors"] == [
            {"form_type": "form_122a1", "error": "The eligibility check hasn't been run yet."}
        ]
        assert resp.data["total_generated"] == 13
        assert GeneratedForm.objects.filter(session=session_with_income).count() == 13

    def test_drops_forms_that_no_longer_apply(self, api_client, session_with_income, user):
        GeneratedForm.objects.create(
            session=session_with_income, form_type="form_103b", generated_by=user
        )
        api_client.post(self.URL, {"session_id": session_with_income.id}, format="json")
        assert not GeneratedForm.objects.filter(
            session=session_with_income, form_type="form_103b"
        ).exists()

    def test_missing_session_id(self, api_client):
        resp = api_client.post(self.URL, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_other_users_session(self, api_client, other_session):
        resp = api_client.post(self.URL, {"session_id": other_session.id}, format="json")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestRegenerateEndpoint:
    """POST /api/forms/{id}/regenerate/"""

    def test_regenerate_existing_form(self, api_client, session_with_debtor, user):
        form = GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_106dec",
            status="generated",
            generated_by=user,
        )

        resp = api_client.post(f"/api/forms/{form.id}/regenerate/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["message"] == "Form regenerated successfully"

        form.refresh_from_db()
        assert json.loads(form.field_values)["Debtor 1"] == "Jane Doe"

    def test_regenerate_other_users_form(self, api_client, other_session, other_user):
        form = GeneratedForm.objects.create(
            session=other_session,
            form_type="form_101",
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
            status="downloaded",
            generated_by=user,
        )
        resp = api_client.post(f"/api/forms/{form.id}/mark_filed/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["status"] == "filed"


# ── List / Retrieve ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestListRetrieve:

    def test_list_only_own_forms(
        self, api_client, session_with_debtor, user, other_session, other_user
    ):
        GeneratedForm.objects.create(
            session=session_with_debtor,
            form_type="form_101",
            generated_by=user,
        )
        GeneratedForm.objects.create(
            session=other_session,
            form_type="form_101",
            generated_by=other_user,
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
            session=session_with_debtor,
            form_type="form_101",
            generated_by=user,
        )
        resp = api_client.get(f"/api/forms/{form.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["form_type"] == "form_101"

    def test_retrieve_other_users_form_404(self, api_client, other_session, other_user):
        form = GeneratedForm.objects.create(
            session=other_session,
            form_type="form_101",
            generated_by=other_user,
        )
        resp = api_client.get(f"/api/forms/{form.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_generated_form_template_version_round_trip(db, template_version_form):
    template_version_form.template_version = "abc123"
    template_version_form.save()
    template_version_form.refresh_from_db()
    assert template_version_form.template_version == "abc123"


# ── Packet ────────────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPacketEndpoint:
    """GET /api/forms/packet/?session=<id>"""

    URL = "/api/forms/packet/"

    def test_lists_the_filers_forms_in_filing_order(self, api_client, session_with_debtor):
        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["form_types"][:3] == ["form_101", "form_106dec", "form_106sum"]
        assert "form_103b" not in resp.data["form_types"]
        assert len(resp.data["form_types"]) == 14

    def test_missing_session(self, api_client):
        assert api_client.get(self.URL).status_code == status.HTTP_400_BAD_REQUEST

    def test_other_users_session(self, api_client, other_session):
        resp = api_client.get(self.URL, {"session": other_session.id})
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── The snapshot stays on the server (DIG-124) ────────────────────────


@pytest.mark.django_db
class TestFieldValuesStayPrivate:

    def _generate_121(self, api_client, session):
        return api_client.post(
            "/api/forms/generate/",
            {"session_id": session.id, "form_type": "form_121"},
            format="json",
        )

    def test_api_never_returns_form_values(self, api_client, session_with_debtor):
        resp = self._generate_121(api_client, session_with_debtor)
        assert resp.status_code == status.HTTP_200_OK
        listed = api_client.get("/api/forms/").data["results"][0]
        for body in (resp.data["form"], listed):
            assert "form_data" not in body
            assert "field_values" not in body
            assert "900-12-3456" not in json.dumps(body)

    def test_full_ssn_is_encrypted_at_rest(self, api_client, session_with_debtor):
        self._generate_121(api_client, session_with_debtor)
        form = GeneratedForm.objects.get(session=session_with_debtor, form_type="form_121")
        assert "900-12-3456" in form.field_values  # Form 121 prints the full SSN
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT field_values, form_data FROM generated_forms WHERE id = %s", [form.id]
            )
            raw_values, raw_form_data = cursor.fetchone()
        assert "900-12-3456" not in raw_values
        assert "900123456" not in raw_values
        assert json.loads(raw_form_data) == {}
