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
  - The means test is worked out again on every call that decides the packet
  - A filed form stays, and downloads, after it leaves the packet
"""

import json
import logging
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from apps.districts.models import District, MedianIncome
from apps.eligibility.models import MeansTest
from apps.forms.models import GeneratedForm
from apps.forms.services.fill_resolver import UnmappedChoice
from apps.forms.services.pdf_filler import (
    InvalidFieldValue,
    PDFFormFiller,
    TemplateHasNoForm,
    UnknownField,
)
from apps.forms.tests.pdf_readback import read_widgets
from apps.intake.models import (
    DebtorInfo,
    ExpenseInfo,
    IncomeInfo,
    IntakeSession,
)

User = get_user_model()

FILED = "This form is marked as filed, so it keeps the answers it was filed with."

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
    # The real ILND data: preparing forms works the means test out against its median income.
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


@pytest.fixture
def session(user, district):
    # Forms are prepared only from an intake the filer completed (spec §5.3), and Complete
    # requires income, which the means test reads on every call (spec §5.6).
    session = IntakeSession.objects.create(user=user, district=district, status="completed")
    IncomeInfo.objects.create(
        session=session,
        marital_status="single",
        number_of_dependents=0,
        monthly_gross_wages=Decimal("3000.00"),
    )
    return session


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
def other_session(other_user, district):
    return IntakeSession.objects.create(user=other_user, district=district)


def _filed_form(session, user, form_type, values):
    return GeneratedForm.objects.create(
        session=session,
        form_type=form_type,
        status="filed",
        generated_by=user,
        field_values=json.dumps(values),
    )


def _rename_filer(session, first_name):
    debtor = session.debtor_info
    debtor.first_name = first_name
    debtor.save()


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

    def test_generate_schedule_i(self, api_client, session_with_debtor):
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "schedule_i"},
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
            "error": "This form isn't part of your packet, based on the answers you've given.",
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

    # The dashboard shows the form's label beside the error, so the sentence
    # names no form, and no internal key or PDF widget the filer can't act on.
    @pytest.mark.parametrize(
        "target,exc,error",
        [
            (
                "apps.forms.views.build_field_values",
                UnmappedChoice("Check Box1"),
                "One of your answers doesn't match a choice printed on this form, "
                "so it can't be filled in yet.",
            ),
            (
                "apps.forms.views.PDFFormFiller.fill",
                TemplateHasNoForm("form_101"),
                "This form's blank court template can't be filled in right now.",
            ),
        ],
        ids=["unmapped_choice", "template_has_no_form"],
    )
    def test_expected_failure_is_explained_in_plain_words(
        self, api_client, session_with_debtor, target, exc, error
    ):
        with patch(target, side_effect=exc):
            resp = api_client.post(
                self.URL,
                {"session_id": session_with_debtor.id, "form_type": "form_101"},
                format="json",
            )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.data == {"form_type": "form_101", "error": error}

    @pytest.mark.parametrize(
        "exc",
        [
            UnknownField("form_101", ["Debtor1.SSNum"]),
            InvalidFieldValue("form_101", "Debtor1.SSNum"),
        ],
        ids=lambda exc: type(exc).__name__,
    )
    def test_filler_fault_is_a_500_logged_by_type_only(
        self, api_client, session_with_debtor, caplog, exc
    ):
        with patch.object(PDFFormFiller, "fill", side_effect=exc):
            resp = api_client.post(
                self.URL,
                {"session_id": session_with_debtor.id, "form_type": "form_101"},
                format="json",
            )
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert resp.data == {
            "form_type": "form_101",
            "error": "This form couldn't be prepared. Please try again later.",
        }
        assert type(exc).__name__ in caplog.text
        assert "Debtor1.SSNum" not in caplog.text

    def test_filed_form_keeps_what_was_filed(self, api_client, session_with_debtor, user):
        form = _filed_form(session_with_debtor, user, "form_101", {"Debtor1.First name": "Jane"})
        _rename_filer(session_with_debtor, "Janet")

        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_101"},
            format="json",
        )

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.data == {"form_type": "form_101", "error": FILED}
        form.refresh_from_db()
        assert form.status == "filed"
        assert json.loads(form.field_values) == {"Debtor1.First name": "Jane"}


# ── Generate All Endpoint ─────────────────────────────────────────────


@pytest.mark.django_db
class TestGenerateAllEndpoint:
    """POST /api/forms/generate_all/"""

    URL = "/api/forms/generate_all/"

    def test_generates_every_form_in_the_packet(self, api_client, session_with_debtor):
        """One form's missing data is reported and doesn't undo the others."""
        debtor = session_with_debtor.debtor_info
        debtor.ssn = ""
        debtor.save()
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        # No fee waiver: no 103B. Income below the median: no 122A-2. Form 121 needs the SSN.
        assert resp.data["errors"] == [
            {
                "form_type": "form_121",
                "error": "Your Social Security number is missing or isn't 9 digits.",
            }
        ]
        assert resp.data["total_generated"] == 13
        assert GeneratedForm.objects.filter(session=session_with_debtor).count() == 13

    def test_drops_forms_that_no_longer_apply(self, api_client, session_with_debtor, user):
        GeneratedForm.objects.create(
            session=session_with_debtor, form_type="form_103b", generated_by=user
        )
        api_client.post(self.URL, {"session_id": session_with_debtor.id}, format="json")
        assert not GeneratedForm.objects.filter(
            session=session_with_debtor, form_type="form_103b"
        ).exists()

    def test_filed_form_is_returned_as_filed(self, api_client, session_with_debtor, user):
        # The dashboard replaces its list with `generated`, so a filed form must be in it.
        form = _filed_form(session_with_debtor, user, "form_106dec", {"Debtor 1": "Jane Doe"})
        _rename_filer(session_with_debtor, "Janet")

        resp = api_client.post(self.URL, {"session_id": session_with_debtor.id}, format="json")

        assert resp.status_code == status.HTTP_200_OK
        returned = [f for f in resp.data["generated"] if f["form_type"] == "form_106dec"]
        assert [(f["id"], f["status"]) for f in returned] == [(form.id, "filed")]
        form.refresh_from_db()
        assert form.status == "filed"
        assert json.loads(form.field_values) == {"Debtor 1": "Jane Doe"}
        # The forms not yet filed are resolved from the current answers.
        petition = GeneratedForm.objects.get(session=session_with_debtor, form_type="form_101")
        assert json.loads(petition.field_values)["Debtor1.First name"] == "Janet"

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

    def test_filed_form_keeps_what_was_filed(self, api_client, session_with_debtor, user):
        form = _filed_form(session_with_debtor, user, "form_106dec", {"Debtor 1": "Jane Doe"})
        _rename_filer(session_with_debtor, "Janet")

        resp = api_client.post(f"/api/forms/{form.id}/regenerate/")

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.data == {"form_type": "form_106dec", "error": FILED}
        form.refresh_from_db()
        assert form.status == "filed"
        assert json.loads(form.field_values) == {"Debtor 1": "Jane Doe"}

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

    def test_list_shows_only_the_asked_sessions_forms(
        self, api_client, session_with_debtor, user, district
    ):
        # The dashboard asks for one session; a filer's other sessions must not mix in.
        second = IntakeSession.objects.create(user=user, district=district)
        for session in [session_with_debtor, second]:
            GeneratedForm.objects.create(session=session, form_type="form_101", generated_by=user)

        resp = api_client.get("/api/forms/", {"session": second.id})
        assert [f["session"] for f in resp.data["results"]] == [second.id]

    def test_list_never_says_whether_another_users_session_exists(
        self, api_client, other_session, other_user
    ):
        GeneratedForm.objects.create(
            session=other_session, form_type="form_101", generated_by=other_user
        )
        foreign = api_client.get("/api/forms/", {"session": other_session.id})
        missing = api_client.get("/api/forms/", {"session": other_session.id + 1000})
        assert foreign.status_code == missing.status_code == status.HTTP_400_BAD_REQUEST
        assert foreign.data == missing.data

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

    def test_a_completed_intake_names_the_median_table_its_forms_use(
        self, api_client, session_with_debtor
    ):
        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["tables"] == [
            {
                "name": "Census median income",
                "effective_date": "2026-04-01",
                "valid_through": "2026-10-31",
                "source_url": (
                    "https://www.justice.gov/ust/eo/bapcpa/20260401/bci_data/"
                    "median_income_table.htm"
                ),
            }
        ]

    def test_a_filer_with_no_means_test_is_shown_no_table(self, api_client, session_with_debtor):
        session = session_with_debtor
        session.status = "in_progress"
        session.save()
        MeansTest.objects.filter(session=session).delete()
        resp = api_client.get(self.URL, {"session": session.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["tables"] == []

    def test_a_means_test_stored_before_the_record_names_no_table(
        self, api_client, session_with_debtor
    ):
        session = session_with_debtor
        session.status = "in_progress"
        session.save()
        _stale_means_test(session, "3000.00")
        resp = api_client.get(self.URL, {"session": session.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["tables"] == []

    def test_missing_session(self, api_client):
        resp = api_client.get(self.URL)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data == {"error": "session is required"}

    def test_other_users_session(self, api_client, other_session):
        resp = api_client.get(self.URL, {"session": other_session.id})
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ── Only a completed intake prepares forms (spec §5.3) ────────────────

FINISH = "Finish your intake before preparing your forms."


@pytest.mark.django_db
class TestCompletionCheck:
    """Until the filer presses Complete, an empty list can't mean "none"."""

    def test_unfinished_intake_cannot_prepare_forms(self, api_client, session_with_debtor, user):
        session = session_with_debtor
        session.status = "in_progress"
        session.save()
        # No fee waiver application, so 103B has left the packet; 101 is in it, unfiled.
        GeneratedForm.objects.create(session=session, form_type="form_103b", generated_by=user)
        unfiled = GeneratedForm.objects.create(
            session=session, form_type="form_101", status="generated", generated_by=user
        )

        generate_all = api_client.post(
            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
        )
        generate = api_client.post(
            "/api/forms/generate/",
            {"session_id": session.id, "form_type": "form_106dec"},
            format="json",
        )
        regenerate = api_client.post(f"/api/forms/{unfiled.id}/regenerate/")
        download = api_client.get(f"/api/forms/{unfiled.id}/download/")

        # One refusal for the whole packet, not one per form.
        assert generate_all.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert generate_all.data == {"error": FINISH}
        for resp, form_type in [
            (generate, "form_106dec"),
            (regenerate, "form_101"),
            (download, "form_101"),
        ]:
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert resp.data == {"form_type": form_type, "error": FINISH}
        # Generate All refused before it dropped the form that left the packet.
        assert set(
            GeneratedForm.objects.filter(session=session).values_list("form_type", flat=True)
        ) == {"form_101", "form_103b"}
        unfiled.refresh_from_db()
        assert (unfiled.status, unfiled.field_values) == ("generated", "")

    def test_unfinished_intake_can_still_read_its_packet(self, api_client, session_with_debtor):
        session_with_debtor.status = "in_progress"
        session_with_debtor.save()

        resp = api_client.get("/api/forms/packet/", {"session": session_with_debtor.id})

        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["form_types"]) == 14

    def test_filed_form_still_downloads_while_the_intake_is_reopened(
        self, api_client, session_with_debtor, user
    ):
        # The filer needs the copy they filed even after an edit sent them back to Review.
        form = _filed_form(session_with_debtor, user, "form_121", {"Debtor1.First name": "Jane"})
        session_with_debtor.status = "in_progress"
        session_with_debtor.save()

        resp = api_client.get(f"/api/forms/{form.id}/download/")

        assert resp.status_code == status.HTTP_200_OK
        assert resp["Content-Type"] == "application/pdf"


# ── The means test is worked out again before the packet is decided (spec §5.6) ──

SPLIT_BY_SOURCE = "Enter your income by source on the Income step."
NO_MEDIAN_TABLE = (
    "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your "
    "forms. Please try again later."
)
NO_MEDIAN_TABLE_LOGGED = "No Census median income table in force on 2026-10-16 for district ilnd"


def _set_wages(session, wages):
    income = session.income_info
    income.monthly_gross_wages = None if wages is None else Decimal(wages)
    income.save()


def _stale_means_test(session, cmi):
    """A stored result, worked out from income the filer has since changed."""
    MeansTest.objects.update_or_create(
        session=session,
        defaults={
            "district": session.district,
            "median_income_threshold": Decimal("71304.00"),
            "calculated_cmi": Decimal(cmi),
            "passes_means_test": Decimal(cmi) * 12 <= Decimal("71304.00"),
        },
    )


@pytest.mark.django_db
class TestMeansTestWorkedOutAgain:
    """122A-2 and 122A-1 follow the filer's current income, never an old result (DIG-160)."""

    @pytest.mark.parametrize(
        "wages,stale_cmi,above_median",
        [("3000.00", "9000.00", False), ("9000.00", "3000.00", True)],
        ids=["income_fell_below_the_median", "income_rose_above_the_median"],
    )
    def test_stale_means_test_no_longer_decides_the_packet(
        self, api_client, session_with_debtor, wages, stale_cmi, above_median
    ):
        session = session_with_debtor
        _set_wages(session, wages)

        _stale_means_test(session, stale_cmi)
        listed = api_client.get("/api/forms/packet/", {"session": session.id})
        _stale_means_test(session, stale_cmi)
        generated = api_client.post(
            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
        )
        _stale_means_test(session, stale_cmi)
        single = api_client.post(
            "/api/forms/generate/",
            {"session_id": session.id, "form_type": "form_122a2"},
            format="json",
        )

        assert ("form_122a2" in listed.data["form_types"]) is above_median
        assert generated.data["errors"] == []
        assert ("form_122a2" in [f["form_type"] for f in generated.data["generated"]]) is (
            above_median
        )
        assert single.status_code == (
            status.HTTP_200_OK if above_median else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        # The stored result is the one worked out from the filer's current income.
        assert MeansTest.objects.get(session=session).calculated_cmi == Decimal(wages)

    def test_unfinished_intake_reads_the_packet_its_stored_data_gives(
        self, api_client, session_with_debtor
    ):
        # Never refused, even with income not yet split by source, and nothing is redone.
        session = session_with_debtor
        session.status = "in_progress"
        session.save()
        session.income_info.monthly_income = [3000] * 6
        _set_wages(session, None)
        _stale_means_test(session, "9000.00")

        resp = api_client.get("/api/forms/packet/", {"session": session.id})

        assert resp.status_code == status.HTTP_200_OK
        assert "form_122a2" in resp.data["form_types"]
        assert MeansTest.objects.get(session=session).calculated_cmi == Decimal("9000.00")

    def test_income_not_split_refuses_every_call_that_prepares_forms(
        self, api_client, session_with_debtor, user
    ):
        session = session_with_debtor
        # A total saved before income was stored by source.
        session.income_info.monthly_income = [3000] * 6
        _set_wages(session, None)
        # No fee waiver application, so 103B has left the packet. 106B-Dec reads no income.
        GeneratedForm.objects.create(session=session, form_type="form_103b", generated_by=user)
        unfiled = GeneratedForm.objects.create(
            session=session, form_type="form_106dec", status="generated", generated_by=user
        )
        filed = _filed_form(session, user, "form_121", {"Debtor1.First name": "Jane"})

        generate_all = api_client.post(
            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
        )
        listed = api_client.get("/api/forms/packet/", {"session": session.id})
        generate = api_client.post(
            "/api/forms/generate/",
            {"session_id": session.id, "form_type": "form_106dec"},
            format="json",
        )
        regenerate = api_client.post(f"/api/forms/{unfiled.id}/regenerate/")
        download = api_client.get(f"/api/forms/{unfiled.id}/download/")
        filed_download = api_client.get(f"/api/forms/{filed.id}/download/")

        # One refusal covers the whole call, the packet list included.
        for resp in (generate_all, listed):
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert resp.data == {"error": SPLIT_BY_SOURCE}
        for resp in (generate, regenerate, download):
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert resp.data == {"form_type": "form_106dec", "error": SPLIT_BY_SOURCE}
        # Generate All refused before it dropped the form that left the packet.
        assert set(
            GeneratedForm.objects.filter(session=session).values_list("form_type", flat=True)
        ) == {"form_103b", "form_106dec", "form_121"}
        # The filed copy prints what was filed, which needs no means test.
        assert filed_download.status_code == status.HTTP_200_OK

    def test_completed_intake_with_no_income_asks_for_income_by_source(
        self, api_client, session_with_debtor
    ):
        # No income at all is income not entered by source: the filer can fix it, so it is
        # the plain-words 422, not a 500.
        session = session_with_debtor
        session.income_info.delete()

        generate_all = api_client.post(
            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
        )
        listed = api_client.get("/api/forms/packet/", {"session": session.id})
        generate = api_client.post(
            "/api/forms/generate/",
            {"session_id": session.id, "form_type": "form_106dec"},
            format="json",
        )

        for resp in (generate_all, listed):
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert resp.data == {"error": SPLIT_BY_SOURCE}
        assert generate.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert generate.data == {"form_type": "form_106dec", "error": SPLIT_BY_SOURCE}

    def test_no_median_table_in_force_is_refused_in_plain_words_and_logged_without_filer_data(
        self, api_client, session_with_debtor, user, caplog
    ):
        session = session_with_debtor
        MedianIncome.objects.filter(district=session.district).delete()
        GeneratedForm.objects.create(session=session, form_type="form_103b", generated_by=user)
        unfiled = GeneratedForm.objects.create(
            session=session, form_type="form_106dec", status="generated", generated_by=user
        )

        def logged_errors():
            return [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]

        generate_all = api_client.post(
            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
        )
        # Operations fix this, so the refusal is logged once: the table, the date and the
        # district, and nothing about the filer (logs reach Sentry, DIG-105).
        assert logged_errors() == [NO_MEDIAN_TABLE_LOGGED]
        listed = api_client.get("/api/forms/packet/", {"session": session.id})
        generate = api_client.post(
            "/api/forms/generate/",
            {"session_id": session.id, "form_type": "form_106dec"},
            format="json",
        )
        regenerate = api_client.post(f"/api/forms/{unfiled.id}/regenerate/")
        download = api_client.get(f"/api/forms/{unfiled.id}/download/")

        for resp in (generate_all, listed):
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert resp.data == {"error": NO_MEDIAN_TABLE}
        for resp in (generate, regenerate, download):
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert resp.data == {"form_type": "form_106dec", "error": NO_MEDIAN_TABLE}
        assert set(
            GeneratedForm.objects.filter(session=session).values_list("form_type", flat=True)
        ) == {"form_103b", "form_106dec"}
        assert logged_errors() == [NO_MEDIAN_TABLE_LOGGED] * 5


# ── A filed form is kept after it leaves the packet (DIG-155) ─────────


@pytest.mark.django_db
def test_filed_form_survives_leaving_the_packet(api_client, session_with_debtor):
    session = session_with_debtor
    ExpenseInfo.objects.create(session=session)  # Complete requires it
    _set_wages(session, "9000.00")  # above the median: 122A-2 is in the packet
    api_client.post("/api/forms/generate_all/", {"session_id": session.id}, format="json")
    form = GeneratedForm.objects.get(session=session, form_type="form_122a2")
    assert api_client.post(f"/api/forms/{form.id}/mark_filed/").status_code == 200
    form.refresh_from_db()
    filed_values = json.loads(form.field_values)

    # The filer's income falls below the median, they correct their first name, and they
    # complete the intake again.
    session_url = f"/api/intake/sessions/{session.id}/"
    lowered = api_client.patch(
        session_url,
        {
            "income_info": {"monthly_gross_wages": "3000.00"},
            "debtor_info": {"first_name": "Janet"},
        },
        format="json",
    )
    assert lowered.status_code == 200
    assert api_client.post(f"{session_url}complete/").status_code == 200
    regenerated = api_client.post(
        "/api/forms/generate_all/", {"session_id": session.id}, format="json"
    )
    listed = api_client.get("/api/forms/packet/", {"session": session.id})
    download = api_client.get(f"/api/forms/{form.id}/download/")

    assert "form_122a2" not in listed.data["form_types"]
    # Generate All keeps it as filed, and returns it, so the dashboard still shows it.
    assert [
        (f["id"], f["status"])
        for f in regenerated.data["generated"]
        if f["form_type"] == "form_122a2"
    ] == [(form.id, "filed")]
    form.refresh_from_db()
    assert json.loads(form.field_values) == filed_values
    # It downloads, and prints what was filed, the old name included.
    assert download.status_code == status.HTTP_200_OK
    printed = {w.full_name: w.value for w in read_widgets(download.content)}
    typed = {
        name: value for name, value in filed_values.items() if value and not value.startswith("/")
    }
    assert "Jane Doe" in typed.values()
    assert {name: printed.get(name) for name in typed} == typed


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
