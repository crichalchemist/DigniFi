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
import unicodedata
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
from apps.eligibility.cmi import HOUSEHOLD_UNANSWERED, NOW_DIFFERENT_UNANSWERED
from apps.eligibility.models import MeansTest
from apps.forms.models import GeneratedForm
from apps.forms.registry import build_parts, packet
from apps.forms.services.fill_resolver import UnmappedChoice
from apps.forms.services.pdf_filler import (
    InvalidFieldValue,
    PDFFormFiller,
    UnknownField,
    UnprintableLetter,
    ValueTooLong,
)
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import (
    AssetInfo,
    DebtorInfo,
    ExpenseInfo,
    FilingFee,
    IncomeInfo,
    IntakeSession,
)
from apps.intake.tests.builders import answer_asset_lines, answer_household, complete_debt

User = get_user_model()

FILED = "This form is marked as filed, so it keeps the answers it was filed with."

WAIVER = {
    "payment_choice": "waiver",
    "income_change_answer": "no",
    "installments_explanation": "I have no savings.",
    "others_covered_answer": "no",
    "expense_change_answer": "no",
}


def _filing_fee(api_client, session, body):
    """Save on the filing-fee page, as the filer does after Complete (it never reopens)."""
    resp = api_client.put(f"/api/intake/sessions/{session.id}/filing-fee/", body, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.data


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
        marital_status="not_married",
        monthly_gross_wages=Decimal("3000.00"),
    )
    answer_household(session)
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

    def test_a_petition_without_the_line_8_answer_links_to_the_filing_fee_page(
        self, api_client, session_with_debtor
    ):
        FilingFee.objects.filter(session=session_with_debtor).delete()
        resp = api_client.post(
            self.URL, {"session_id": session_with_debtor.id, "form_type": "form_101"}, format="json"
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.data == {
            "form_type": "form_101",
            "error": "Choose how you will pay the filing fee.",
            "page": "/filing-fee",
        }

    def test_line_4_moved_back_to_no_keeps_its_explanation_off_103b(
        self, api_client, session_with_debtor
    ):
        session = session_with_debtor
        why = "My hours are being cut in March."
        _filing_fee(
            api_client,
            session,
            {**WAIVER, "income_change_answer": "yes", "income_change_explanation": why},
        )
        _filing_fee(api_client, session, {"income_change_answer": "no"})  # the page sends only No
        resp = api_client.post(
            self.URL, {"session_id": session.id, "form_type": "form_103b"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK, resp.data
        (part,) = json.loads(
            GeneratedForm.objects.get(session=session, form_type="form_103b").field_values
        )["parts"]
        assert (part["values"]["Check 4"], "4 type" in part["values"]) == ("/no", False)
        assert FilingFee.objects.get(session=session).income_change_explanation == why

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

    def test_form_101_without_a_county_names_the_your_information_step(
        self, api_client, session_with_debtor
    ):
        # A session saved before 3e1 has no county (3e1 spec §9.2).
        household = session_with_debtor.household
        household.county = None
        household.save()
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_101"},
            format="json",
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.data == {
            "form_type": "form_101",
            "step": "debtor_info",
            "error": "Choose your county on the Your Information step.",
        }
        assert not GeneratedForm.objects.filter(session=session_with_debtor).exists()

    def test_schedule_j_with_an_unanswered_household_list_names_the_income_step(
        self, api_client, session_with_debtor
    ):
        # A list never answered is refused, not printed as "no dependents" (3e1 spec §9.2).
        answer_household(session_with_debtor, members=None)
        resp = api_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "schedule_j"},
            format="json",
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.data["step"] == "income_info"
        assert resp.data["error"] == HOUSEHOLD_UNANSWERED
        assert not GeneratedForm.objects.filter(session=session_with_debtor).exists()

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

    def test_unauthenticated(self, unauth_client, session_with_debtor):
        resp = unauth_client.post(
            self.URL,
            {"session_id": session_with_debtor.id, "form_type": "form_101"},
            format="json",
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    # The dashboard shows the form's label beside the error, so the sentence
    # names no form, and no internal key or PDF widget the filer can't act on.
    @pytest.mark.parametrize(
        "target,exc,error",
        [
            (
                "apps.forms.views.build_parts",
                UnmappedChoice("Check Box1"),
                "One of your answers doesn't match a choice printed on this form, "
                "so it can't be filled in yet.",
            ),
        ],
        ids=["unmapped_choice"],
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
        with patch.object(PDFFormFiller, "check", side_effect=exc):
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

    # A letter the form can't print, or a value too long for its box, is the filer's to
    # change: a 422 naming the box and where to change it. It is no fault, so nothing is
    # logged, and the filer's letter never reaches the logs (DIG-105).
    @pytest.mark.parametrize(
        "exc,refusal",
        [
            (
                UnprintableLetter("form_101", "ą", "Last name", {"step": "debtor_info"}),
                {
                    "error": "The court form can't print the letter “ą” in “Last name”. "
                    "Change it to a letter without the mark.",
                    "step": "debtor_info",
                },
            ),
            (
                ValueTooLong("form_101", "Type of assistance", {"page": "/filing-fee"}),
                {
                    "error": "“Type of assistance” is too long to fit on the court form, "
                    "even in small print. Shorten it.",
                    "page": "/filing-fee",
                },
            ),
        ],
        ids=["unprintable_letter", "value_too_long"],
    )
    def test_a_refused_letter_or_length_names_where_to_fix_it(
        self, api_client, session_with_debtor, caplog, exc, refusal
    ):
        caplog.set_level(logging.DEBUG)
        with patch.object(PDFFormFiller, "check", side_effect=exc):
            resp = api_client.post(
                self.URL,
                {"session_id": session_with_debtor.id, "form_type": "form_101"},
                format="json",
            )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.data == {"form_type": "form_101", **refusal}
        assert not [r for r in caplog.records if r.name.startswith("apps.")]
        assert exc.label not in caplog.text
        assert "ą" not in caplog.text

    def test_unexpected_failure_points_the_filer_to_no_step_or_page(
        self, api_client, session_with_debtor
    ):
        # Only a refusal names where the filer fixes it; nothing they enter fixes a fault.
        fault = RuntimeError("page 3 could not be written")
        fault.step, fault.page = "debtor_info", 3
        with patch.object(PDFFormFiller, "check", side_effect=fault):
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

    def test_a_petition_without_the_line_8_answer_is_named_with_its_page(
        self, api_client, session_with_debtor
    ):
        FilingFee.objects.filter(session=session_with_debtor).delete()
        resp = api_client.post(self.URL, {"session_id": session_with_debtor.id}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["errors"] == [
            {
                "form_type": "form_101",
                "error": "Choose how you will pay the filing fee.",
                "page": "/filing-fee",
            }
        ]
        assert resp.data["total_generated"] == 13

    def test_moving_off_the_waiver_withdraws_an_unfiled_103b_and_moving_back_brings_its_answers_back(
        self, api_client, session_with_debtor
    ):
        session = session_with_debtor
        _filing_fee(api_client, session, WAIVER)
        first = api_client.post(self.URL, {"session_id": session.id}, format="json")
        assert first.data["errors"] == []
        assert "form_103b" in [f["form_type"] for f in first.data["generated"]]

        _filing_fee(api_client, session, {"payment_choice": "installments"})
        api_client.post(self.URL, {"session_id": session.id}, format="json")
        assert not GeneratedForm.objects.filter(session=session, form_type="form_103b").exists()

        _filing_fee(api_client, session, {"payment_choice": "waiver"})  # only line 8 sent
        again = api_client.post(self.URL, {"session_id": session.id}, format="json")
        assert again.data["errors"] == []
        application = GeneratedForm.objects.get(session=session, form_type="form_103b")
        (part,) = json.loads(application.field_values)["parts"]
        assert (part["values"]["Check 4"], part["values"]["5 Type"]) == (
            "/no",
            "I have no savings.",
        )

    def test_a_filed_103b_stays_when_the_filer_moves_off_the_waiver(
        self, api_client, session_with_debtor, user
    ):
        session = session_with_debtor
        _filing_fee(api_client, session, WAIVER)
        listed = api_client.get("/api/forms/packet/", {"session": session.id})
        assert "form_103b" in listed.data["form_types"]  # the waiver put it in the packet
        filed = _filed_form(session, user, "form_103b", {"5 Type": "I have no savings."})
        _filing_fee(api_client, session, {"payment_choice": "pay_in_full"})
        resp = api_client.post(self.URL, {"session_id": session.id}, format="json")
        returned = [f for f in resp.data["generated"] if f["form_type"] == "form_103b"]
        assert [(f["id"], f["status"]) for f in returned] == [(filed.id, "filed")]

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
        # Line 8 is pay in full: no 103B. Income below the median: no 122A-2. Form 121 needs the SSN,
        # which the filer enters on the step the error names.
        assert resp.data["errors"] == [
            {
                "form_type": "form_121",
                "error": "Enter your 9-digit Social Security number on the Your Information step.",
                "step": "debtor_info",
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
        (part,) = json.loads(petition.field_values)["parts"]
        assert part["values"]["Debtor1.First name"] == "Janet"


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
        (part,) = json.loads(form.field_values)["parts"]
        assert part["values"]["Debtor 1"] == "Jane Doe"

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


# ── Generate, Generate All and Regenerate check; only Download draws (spec §7) ──


@pytest.mark.django_db
def test_generate_all_checks_without_drawing(api_client, session_with_debtor):
    # Drawing takes most of a form's time, so a packet's Generate All only checks what each
    # form prints, and stays inside its budget (DIG-137). Download draws.
    session = session_with_debtor
    with patch.object(PDFFormFiller, "fill") as fill:
        generate = api_client.post(
            "/api/forms/generate/",
            {"session_id": session.id, "form_type": "form_101"},
            format="json",
        )
        generate_all = api_client.post(
            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
        )
        regenerate = api_client.post(f"/api/forms/{generate.data['form']['id']}/regenerate/")

    assert fill.call_count == 0
    assert [r.status_code for r in (generate, generate_all, regenerate)] == [200, 200, 200]
    assert generate_all.data["errors"] == []
    # Each form keeps the parts it was checked with, which its download draws.
    stored = GeneratedForm.objects.filter(session=session)
    assert stored.count() == generate_all.data["total_generated"]
    for form in stored:
        assert json.loads(form.field_values) == build_parts(form.form_type, session)


@pytest.mark.django_db
def test_each_generate_names_the_step_that_fixes_a_letter_the_form_cannot_print(
    api_client, session_with_debtor, user, caplog
):
    # An invented surname: ą is outside the court form's font, which would print "?".
    session = session_with_debtor
    debtor = session.debtor_info
    debtor.last_name = "Wąsowicz"
    debtor.save()
    caplog.set_level(logging.DEBUG)

    generate = api_client.post(
        "/api/forms/generate/", {"session_id": session.id, "form_type": "form_101"}, format="json"
    )
    generate_all = api_client.post(
        "/api/forms/generate_all/", {"session_id": session.id}, format="json"
    )

    refusal = {
        "form_type": "form_101",
        "error": "The court form can't print the letter “ą” in “Last name”. "
        "Change it to a letter without the mark.",
        "step": "debtor_info",
    }
    assert generate.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert generate.data == refusal
    # Every form of the packet prints the surname, so Generate All refuses each the same way.
    errors = generate_all.data["errors"]
    assert refusal in errors
    assert {error["step"] for error in errors} == {"debtor_info"}
    assert all(
        error["error"].startswith("The court form can't print the letter “ą” in “")
        for error in errors
    )
    assert sorted(error["form_type"] for error in errors) == sorted(packet(session))
    assert generate_all.data["generated"] == []
    assert not GeneratedForm.objects.filter(session=session).exists()

    # Regenerate refuses a form generated before the change the same way, and keeps it.
    form = GeneratedForm.objects.create(
        session=session, form_type="form_101", status="generated", generated_by=user
    )
    regenerate = api_client.post(f"/api/forms/{form.id}/regenerate/")

    assert regenerate.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert regenerate.data == refusal
    form.refresh_from_db()
    assert (form.status, form.field_values) == ("generated", "")
    assert "ą" not in caplog.text


@pytest.mark.django_db
def test_a_name_saved_with_its_marks_apart_generates_form_101(api_client, session_with_debtor):
    # The intake keeps a name as typed, so é can arrive as e and U+0301: the form prints é,
    # never a refusal that quotes a lone accent.
    debtor = session_with_debtor.debtor_info
    debtor.first_name = unicodedata.normalize("NFD", "José")
    debtor.save()

    response = api_client.post(
        "/api/forms/generate/",
        {"session_id": session_with_debtor.id, "form_type": "form_101"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK, response.data


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


# The root conftest pins today to 2026-10-16, so the six months in force are April to September
INCOME_NOW = {"start": "2026-04-01", "end": "2026-09-30"}


@pytest.mark.django_db
class TestPacketEndpoint:
    """GET /api/forms/packet/?session=<id>"""

    URL = "/api/forms/packet/"

    def test_lists_the_filers_forms_in_filing_order(self, api_client, session_with_debtor):
        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
        assert resp.status_code == status.HTTP_200_OK
        assert set(resp.data) == {
            "session",
            "form_types",
            "tables",
            "income_period",
            "payment_choice",
        }
        assert resp.data["form_types"][:3] == ["form_101", "form_106dec", "form_106sum"]
        assert "form_103b" not in resp.data["form_types"]
        assert len(resp.data["form_types"]) == 14

    @pytest.mark.parametrize("answer", ["pay_in_full", "installments", "waiver", None])
    def test_the_packet_carries_the_filers_line_8_answer(
        self, api_client, session_with_debtor, answer
    ):
        fee = FilingFee.objects.get(
            session=session_with_debtor
        )  # answer_household's pay-in-full row
        fee.payment_choice = answer
        fee.save()
        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["payment_choice"] == answer
        assert ("form_103b" in resp.data["form_types"]) is (answer == "waiver")

    def test_a_filer_with_no_filing_fee_record_is_shown_no_answer(
        self, api_client, session_with_debtor
    ):
        FilingFee.objects.filter(session=session_with_debtor).delete()
        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
        assert resp.data["payment_choice"] is None

    def test_a_completed_intake_names_the_median_table_its_forms_use(
        self, api_client, session_with_debtor
    ):
        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["tables"] == [
            {
                "name": "Census median income",
                "effective_date": "2026-04-01",
                "valid_through": "2027-03-31",
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

    def test_the_packet_says_which_six_months_the_income_was_answered_for(
        self, api_client, session_with_debtor
    ):
        IncomeInfo.objects.filter(session=session_with_debtor).update(
            income_period_end=date(2026, 8, 31)
        )
        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
        assert resp.data["income_period"] == {
            "answered_for": {"start": "2026-03-01", "end": "2026-08-31"},
            "now": INCOME_NOW,
        }

    def test_a_window_never_confirmed_is_answered_for_nothing(
        self, api_client, session_with_debtor
    ):
        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
        assert resp.data["income_period"] == {"answered_for": None, "now": INCOME_NOW}

    def test_continue_on_the_income_step_brings_the_answer_up_to_date(
        self, api_client, session_with_debtor
    ):
        IncomeInfo.objects.filter(session=session_with_debtor).update(
            income_period_end=date(2026, 8, 31)
        )
        # Continue on the Income step (step 2) sends update_step for the next step, 3
        stepped = api_client.post(
            f"/api/intake/sessions/{session_with_debtor.id}/update_step/",
            {"current_step": 3},
            format="json",
        )
        assert stepped.status_code == status.HTTP_200_OK
        # update_step reopens the intake; an unfinished intake's packet list reads stored data
        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
        assert resp.data["income_period"]["answered_for"] == INCOME_NOW

    def test_a_completed_intake_with_an_open_gap_gets_the_refusal_not_the_notice(
        self, api_client, session_with_debtor
    ):
        IncomeInfo.objects.filter(session=session_with_debtor).update(income_now_different=None)
        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.data == {"error": NOW_DIFFERENT_UNANSWERED, "step": "income_info"}
        assert "income_period" not in resp.data


# ── A session id that is missing, or another user's, is refused everywhere ──

_SESSION_ENDPOINTS = [
    pytest.param(
        "post",
        "/api/forms/generate/",
        "session_id",
        {"form_type": "form_101"},
        lambda data: "session_id" in data["error"],
        id="generate",
    ),
    pytest.param(
        "post", "/api/forms/generate_all/", "session_id", {}, lambda data: True, id="generate_all"
    ),
    pytest.param(
        "get",
        "/api/forms/packet/",
        "session",
        {},
        lambda data: data == {"error": "session is required"},
        id="packet",
    ),
]


def _call(api_client, method, url, payload):
    if method == "post":
        return api_client.post(url, payload, format="json")
    return api_client.get(url, payload)


@pytest.mark.django_db
@pytest.mark.parametrize("method,url,key,extra,says", _SESSION_ENDPOINTS)
def test_missing_session_id_is_a_400(api_client, method, url, key, extra, says):
    resp = _call(api_client, method, url, extra)
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert says(resp.data)


@pytest.mark.django_db
@pytest.mark.parametrize("method,url,key,extra,says", _SESSION_ENDPOINTS)
def test_other_users_session_is_a_404(api_client, other_session, method, url, key, extra, says):
    resp = _call(api_client, method, url, {key: other_session.id, **extra})
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
        # Line 8 is pay in full, so 103B has left the packet; 101 is in it, unfiled.
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

        # One refusal for the whole packet, not one per form, with the page that fixes it.
        assert generate_all.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert generate_all.data == {"error": FINISH, "page": "/intake"}
        for resp, form_type in [
            (generate, "form_106dec"),
            (regenerate, "form_101"),
            (download, "form_101"),
        ]:
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert resp.data == {"form_type": form_type, "error": FINISH, "page": "/intake"}
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
MARRIAGE = "Answer the question about marriage on the Income step."
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
        session.income_info.monthly_income = json.dumps([3000] * 6)
        _set_wages(session, None)
        _stale_means_test(session, "9000.00")

        resp = api_client.get("/api/forms/packet/", {"session": session.id})

        assert resp.status_code == status.HTTP_200_OK
        assert "form_122a2" in resp.data["form_types"]
        assert MeansTest.objects.get(session=session).calculated_cmi == Decimal("9000.00")

    @pytest.mark.parametrize("gap,sentence", [("not_split", SPLIT_BY_SOURCE), ("no_row", MARRIAGE)])
    def test_income_not_split_refuses_every_call_that_prepares_forms(
        self, api_client, session_with_debtor, user, gap, sentence
    ):
        session = session_with_debtor
        if gap == "not_split":
            # A total saved before income was stored by source.
            session.income_info.monthly_income = json.dumps([3000] * 6)
            _set_wages(session, None)
        else:
            # No income row is first a marriage question never answered (3e1 spec §9.1): the
            # filer can fix it, so it is still the plain-words 422, not a 500.
            session.income_info.delete()
        # Line 8 is pay in full, so 103B has left the packet. 106B-Dec reads no income.
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

        # One refusal covers the whole call, the packet list included, with the step that
        # fixes it.
        for resp in (generate_all, listed):
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert resp.data == {"error": sentence, "step": "income_info"}
        for resp in (generate, regenerate, download):
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert resp.data == {
                "form_type": "form_106dec",
                "error": sentence,
                "step": "income_info",
            }
        # Generate All refused before it dropped the form that left the packet.
        assert set(
            GeneratedForm.objects.filter(session=session).values_list("form_type", flat=True)
        ) == {"form_103b", "form_106dec", "form_121"}
        # The filed copy prints what was filed, which needs no means test.
        assert filed_download.status_code == status.HTTP_200_OK

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


@pytest.mark.slow
@pytest.mark.django_db
def test_filed_form_survives_leaving_the_packet(api_client, session_with_debtor):
    session = session_with_debtor
    ExpenseInfo.objects.create(
        session=session, expenses_include_others="no"
    )  # Complete requires it
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
    # It downloads, and prints what was filed, the old name included, in every widget of
    # each name.
    assert download.status_code == status.HTTP_200_OK
    printed = {}
    for w in read_drawn("form_122a2", download.content):
        printed.setdefault(w.full_name, set()).add(w.value)
    (part,) = filed_values["parts"]
    typed = {
        name: value for name, value in part["values"].items() if value and not value.startswith("/")
    }
    assert "Jane Doe" in typed.values()
    assert {name: printed.get(name) for name in typed} == {
        name: {value} for name, value in typed.items()
    }


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


# ── An unfinished Assets step refuses the whole call (3b spec §7) ──

OLD_ROW = 'Pick a line on the Assets step for "Old couch".'


@pytest.mark.django_db
class TestAssetStepCheck:
    """A session completed before 3b can't print A/B totals from rows no line owns."""

    def test_an_old_row_refuses_generate_generate_all_regenerate_and_download(
        self, api_client, session_with_debtor, user
    ):
        session = session_with_debtor
        AssetInfo.objects.create(session=session, description="Old couch")
        GeneratedForm.objects.create(session=session, form_type="form_103b", generated_by=user)
        unfiled = GeneratedForm.objects.create(
            session=session, form_type="form_106dec", status="generated", generated_by=user
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

        assert generate_all.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert generate_all.data == {"error": OLD_ROW, "step": "assets"}
        for resp in (generate, regenerate, download):
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert resp.data == {"form_type": "form_106dec", "error": OLD_ROW, "step": "assets"}
        # Generate All refused before it dropped the form that left the packet.
        assert GeneratedForm.objects.filter(session=session, form_type="form_103b").exists()

    def test_the_assets_sentence_comes_before_an_income_gap(self, api_client, session_with_debtor):
        # Personas seeded before 3b have both gaps, and the Assets step is what they are sent to.
        session = session_with_debtor
        AssetInfo.objects.create(session=session, description="Old couch")
        session.income_info.delete()

        response = api_client.post(
            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.data == {"error": OLD_ROW, "step": "assets"}

    def test_the_packet_list_and_a_filed_download_are_not_refused(
        self, api_client, session_with_debtor, user
    ):
        session = session_with_debtor
        AssetInfo.objects.create(session=session, description="Old couch")
        filed = _filed_form(session, user, "form_121", {"Debtor1.First name": "Jane"})

        listed = api_client.get("/api/forms/packet/", {"session": session.id})
        filed_download = api_client.get(f"/api/forms/{filed.id}/download/")

        assert listed.status_code == status.HTTP_200_OK
        assert filed_download.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize(
        ("rows_before", "box"),
        [
            (0, "Line 18.1: Institution or issuer name"),  # in a box on the form
            (3, "Institution or issuer name"),  # in a column of its attached sheet
        ],
        ids=["on_a_slot", "on_a_sheet"],
    )
    def test_a_letter_the_form_can_t_print_is_a_422_linking_to_assets(
        self, api_client, session_with_debtor, rows_before, box
    ):
        # The Assets step is finished here, so the refusal is the letter's and not a gap's.
        session = session_with_debtor
        answer_asset_lines(session, yes=["18"])
        for n in range(rows_before):
            AssetInfo.objects.create(
                session=session, ab_line="18", description=f"Row {n}", current_value=Decimal(1)
            )
        AssetInfo.objects.create(
            session=session, ab_line="18", description="Bad □ name", current_value=Decimal(1)
        )

        resp = api_client.post(
            "/api/forms/generate/",
            {"session_id": session.id, "form_type": "schedule_a_b"},
            format="json",
        )

        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.data["step"] == "assets"
        assert box in resp.data["error"]
        assert "□" in resp.data["error"]


CLAIM_GAP = "Enter the street, city, two-letter state and ZIP for Demo Card Services."


def _debt_without_an_address(session):
    # complete_debt clears the "no amounts owed" answer answer_household set, so the address
    # gap is the first.
    return complete_debt(session, creditor_name="Demo Card Services", street_address="")


@pytest.mark.django_db
class TestClaimStepCheck:
    """A filer who left a claims answer out can't have forms printed from the gap."""

    def test_a_claim_gap_refuses_generate_generate_all_regenerate_and_download(
        self, api_client, session_with_debtor, user
    ):
        session = session_with_debtor
        _debt_without_an_address(session)
        GeneratedForm.objects.create(session=session, form_type="form_103b", generated_by=user)
        unfiled = GeneratedForm.objects.create(
            session=session, form_type="form_106dec", status="generated", generated_by=user
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

        assert generate_all.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert generate_all.data == {"error": CLAIM_GAP, "step": "debts"}
        for resp in (generate, regenerate, download):
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert resp.data == {
                "form_type": "form_106dec",
                "error": CLAIM_GAP,
                "step": "debts",
            }
        # Generate All refused before it dropped the form that left the packet.
        assert GeneratedForm.objects.filter(session=session, form_type="form_103b").exists()

    def test_the_assets_sentence_comes_before_a_claim_gap(self, api_client, session_with_debtor):
        session = session_with_debtor
        AssetInfo.objects.create(session=session, description="Old couch")
        _debt_without_an_address(session)

        response = api_client.post(
            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.data == {"error": OLD_ROW, "step": "assets"}

    def test_a_claim_gap_is_refused_before_the_means_test_is_worked_out(
        self, api_client, session_with_debtor
    ):
        session = session_with_debtor
        _debt_without_an_address(session)
        session.income_info.delete()

        response = api_client.post(
            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.data == {"error": CLAIM_GAP, "step": "debts"}

    def test_the_packet_list_never_refuses_a_claim_gap(self, api_client, session_with_debtor):
        session = session_with_debtor
        _debt_without_an_address(session)

        listed = api_client.get("/api/forms/packet/", {"session": session.id})

        assert listed.status_code == status.HTTP_200_OK

    def test_a_filed_download_is_not_refused_for_a_claim_gap(
        self, api_client, session_with_debtor, user
    ):
        session = session_with_debtor
        _debt_without_an_address(session)
        filed = _filed_form(session, user, "form_121", {"Debtor1.First name": "Jane"})

        download = api_client.get(f"/api/forms/{filed.id}/download/")

        assert download.status_code == status.HTTP_200_OK

    def test_a_linked_row_with_no_lives_here_answer_names_the_assets_step(
        self, api_client, session_with_debtor
    ):
        # The Assets step is finished (line 1 answered Yes, its row whole), so the gap that
        # speaks is the one about the row a debt links to.
        session = session_with_debtor
        answer_asset_lines(session, ["1"])
        home = AssetInfo(
            session=session,
            ab_line="1",
            current_value=Decimal("100000.00"),
            entire_value=Decimal("100000.00"),
        )
        home.set_details(
            {"street": "7823 S Sangamon St", "property_kinds": ["single_family"], "who": "only_you"}
        )
        home.save()
        complete_debt(
            session,
            creditor_name="Demo Mortgage Services",
            debt_type="mortgage",
            is_secured=True,
            secured_by=home,
        )

        response = api_client.post(
            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.data == {
            "error": (
                "Answer “Do you live here?” for 7823 S Sangamon St on line 1 of the Assets step."
            ),
            "step": "assets",
        }
