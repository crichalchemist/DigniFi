from decimal import Decimal
from urllib.parse import urlencode

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.registry import packet
from apps.intake.models import FeeWaiverApplication, IntakeSession
from apps.users.models import User


@pytest.fixture
def setup(db):
    user = User.objects.create_user(username="fwtest", password="pass")
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
    return client, session, user


def _application(session, **answers):
    """What the fee-waiver page sends (step 2 spec §5.7)."""
    return {
        "session": session.id,
        "household_size": 1,
        "monthly_take_home_pay": "1750.00",
        "receives_noncash_assistance": False,
        "benefit_types": [],
        "cannot_pay_full": True,
        "cannot_pay_installments": True,
        **answers,
    }


def test_create_fee_waiver(setup):
    """POST /intake/fee-waiver/ creates a FeeWaiverApplication linked to user's session."""
    client, session, _ = setup
    payload = _application(session, household_size=2)
    resp = client.post("/api/intake/fee-waiver/", payload, format="json")
    assert resp.status_code == 201
    data = resp.json()
    assert data["session"] == session.id
    assert data["household_size"] == 2
    assert data["id"] is not None
    fw = FeeWaiverApplication.objects.get(session=session)
    assert data["id"] == fw.id
    assert FeeWaiverApplication.objects.filter(session=session).exists()


def test_create_fee_waiver_unauthenticated(db):
    """POST /intake/fee-waiver/ without auth returns 401."""
    client = APIClient()
    resp = client.post("/api/intake/fee-waiver/", {}, format="json")
    assert resp.status_code == 401


def test_get_fee_waiver(setup):
    """GET /intake/fee-waiver/{id}/ returns record owned by user."""
    client, session, _ = setup
    fw = FeeWaiverApplication.objects.create(
        session=session,
        household_size=1,
        monthly_income=Decimal("1200.00"),
        monthly_expenses=Decimal("1000.00"),
    )
    resp = client.get(f"/api/intake/fee-waiver/{fw.id}/")
    assert resp.status_code == 200
    assert resp.json()["id"] == fw.id


def test_other_user_cannot_access_fee_waiver(db):
    """GET /intake/fee-waiver/{id}/ for another user's record returns 404."""
    owner = User.objects.create_user(username="owner", password="pass")
    other = User.objects.create_user(username="other", password="pass")
    district = District.objects.create(
        code="ILND2",
        name="Illinois Northern 2",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=owner, district=district)
    fw = FeeWaiverApplication.objects.create(
        session=session,
        household_size=1,
        monthly_income=Decimal("1200.00"),
        monthly_expenses=Decimal("1000.00"),
    )
    client = APIClient()
    client.force_authenticate(user=other)
    resp = client.get(f"/api/intake/fee-waiver/{fw.id}/")
    assert resp.status_code == 404


def test_cross_user_post_is_forbidden(db):
    """POST /intake/fee-waiver/ with another user's session returns 403."""
    owner = User.objects.create_user(username="fw_owner2", password="pass")
    attacker = User.objects.create_user(username="fw_attacker", password="pass")
    district = District.objects.create(
        code="ILND3",
        name="Illinois Northern 3",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=owner, district=district)
    client = APIClient()
    client.force_authenticate(user=attacker)
    payload = _application(session, household_size=99, monthly_take_home_pay="100.00")
    resp = client.post("/api/intake/fee-waiver/", payload, format="json")
    assert resp.status_code == 403
    assert not FeeWaiverApplication.objects.filter(session=session).exists()


def test_create_fee_waiver_is_idempotent(setup):
    """Second POST to /intake/fee-waiver/ for same session updates, not duplicates."""
    client, session, _ = setup
    payload = _application(session, monthly_take_home_pay="1000.00")
    client.post("/api/intake/fee-waiver/", payload, format="json")
    updated_payload = {**payload, "household_size": 3}
    resp = client.post("/api/intake/fee-waiver/", updated_payload, format="json")
    assert resp.status_code == 201
    assert FeeWaiverApplication.objects.filter(session=session).count() == 1
    assert FeeWaiverApplication.objects.get(session=session).household_size == 3


# ── The page's questions (step 2 spec §5.7) ───────────────────────────
#
# Form 103B line 2 asks for take-home pay and line 3 asks whether the filer gets non-cash help
# from the government, and if so what kind. The filer signs it under penalty of perjury, so
# the server keeps exactly the answers given: a Yes says what kind, a No says none.


def test_the_page_answers_take_home_pay_and_non_cash_help_and_they_are_kept(setup):
    client, session, _ = setup
    resp = client.post(
        "/api/intake/fee-waiver/",
        _application(
            session,
            monthly_take_home_pay="2800.00",
            receives_noncash_assistance=True,
            benefit_types=["SNAP (food stamps)"],
        ),
        format="json",
    )

    assert resp.status_code == 201
    fw = FeeWaiverApplication.objects.get(session=session)
    assert (fw.monthly_take_home_pay, fw.receives_noncash_assistance, fw.benefit_types) == (
        Decimal("2800.00"),
        True,
        ["SNAP (food stamps)"],
    )
    body = resp.json()
    assert (
        body["monthly_take_home_pay"],
        body["receives_noncash_assistance"],
        body["benefit_types"],
    ) == ("2800.00", True, ["SNAP (food stamps)"])


def test_an_application_needs_take_home_pay_and_an_answer_about_non_cash_help(setup):
    # A page that sent either under another name would otherwise lose it without a word.
    client, session, _ = setup
    payload = _application(session)
    del payload["monthly_take_home_pay"]
    del payload["receives_noncash_assistance"]

    resp = client.post("/api/intake/fee-waiver/", payload, format="json")

    assert resp.status_code == 400
    assert set(resp.json()) == {"monthly_take_home_pay", "receives_noncash_assistance"}
    assert not FeeWaiverApplication.objects.filter(session=session).exists()


@pytest.mark.parametrize("kinds", [None, [], [""], ["   "]])
def test_a_yes_to_non_cash_help_needs_what_kind(setup, kinds):
    client, session, _ = setup
    payload = _application(session, receives_noncash_assistance=True, benefit_types=kinds)
    if kinds is None:
        del payload["benefit_types"]

    resp = client.post("/api/intake/fee-waiver/", payload, format="json")

    assert resp.status_code == 400
    assert "benefit_types" in resp.json()
    assert not FeeWaiverApplication.objects.filter(session=session).exists()


@pytest.mark.parametrize(("length", "status"), [(255, 201), (256, 400)])
def test_what_kind_is_kept_up_to_a_line_of_text(setup, length, status):
    client, session, _ = setup
    payload = _application(session, receives_noncash_assistance=True, benefit_types=["x" * length])

    resp = client.post("/api/intake/fee-waiver/", payload, format="json")

    assert resp.status_code == status
    assert FeeWaiverApplication.objects.filter(session=session).exists() == (status == 201)


def test_a_no_to_non_cash_help_keeps_no_kind(setup):
    # "What kind?" opens only under Yes, so a kind sent with No is not an answer.
    client, session, _ = setup
    resp = client.post(
        "/api/intake/fee-waiver/",
        _application(session, receives_noncash_assistance=False, benefit_types=["SNAP"]),
        format="json",
    )

    assert resp.status_code == 201
    fw = FeeWaiverApplication.objects.get(session=session)
    assert (fw.receives_noncash_assistance, fw.benefit_types) == (False, [])


def test_changing_the_answer_to_yes_later_still_needs_what_kind(setup):
    client, session, _ = setup
    client.post("/api/intake/fee-waiver/", _application(session), format="json")
    fw = FeeWaiverApplication.objects.get(session=session)

    refused = client.patch(
        f"/api/intake/fee-waiver/{fw.id}/", {"receives_noncash_assistance": True}, format="json"
    )
    fw.refresh_from_db()
    assert refused.status_code == 400
    assert fw.receives_noncash_assistance is False

    accepted = client.patch(
        f"/api/intake/fee-waiver/{fw.id}/",
        {"receives_noncash_assistance": True, "benefit_types": ["Housing subsidy"]},
        format="json",
    )
    fw.refresh_from_db()
    assert accepted.status_code == 200
    assert (fw.receives_noncash_assistance, fw.benefit_types) == (True, ["Housing subsidy"])


def test_a_change_that_sends_one_answer_is_checked_against_the_other_one_stored(setup):
    client, session, _ = setup
    client.post(
        "/api/intake/fee-waiver/",
        _application(session, receives_noncash_assistance=True, benefit_types=["SNAP"]),
        format="json",
    )
    fw = FeeWaiverApplication.objects.get(session=session)
    url = f"/api/intake/fee-waiver/{fw.id}/"

    cleared = client.patch(url, {"benefit_types": []}, format="json")
    kept = client.patch(url, {"receives_noncash_assistance": True}, format="json")

    fw.refresh_from_db()
    assert (cleared.status_code, kept.status_code) == (400, 200)
    assert (fw.receives_noncash_assistance, fw.benefit_types) == (True, ["SNAP"])


def test_changing_the_answer_to_no_later_drops_the_kind(setup):
    client, session, _ = setup
    client.post(
        "/api/intake/fee-waiver/",
        _application(session, receives_noncash_assistance=True, benefit_types=["SNAP"]),
        format="json",
    )
    fw = FeeWaiverApplication.objects.get(session=session)

    resp = client.patch(
        f"/api/intake/fee-waiver/{fw.id}/", {"receives_noncash_assistance": False}, format="json"
    )

    fw.refresh_from_db()
    assert resp.status_code == 200
    assert (fw.receives_noncash_assistance, fw.benefit_types) == (False, [])


@pytest.mark.parametrize("amount", ["-0.01", "100000000.00", "12.345", "NaN", "Infinity"])
def test_take_home_pay_must_be_zero_or_more_and_fit_its_column(setup, amount):
    client, session, _ = setup

    resp = client.post(
        "/api/intake/fee-waiver/",
        _application(session, monthly_take_home_pay=amount),
        format="json",
    )

    assert resp.status_code == 400
    assert "monthly_take_home_pay" in resp.json()
    assert not FeeWaiverApplication.objects.filter(session=session).exists()


@pytest.mark.parametrize("amount", ["0.00", "99999999.99"])
def test_take_home_pay_of_zero_or_the_column_maximum_is_kept(setup, amount):
    client, session, _ = setup

    resp = client.post(
        "/api/intake/fee-waiver/",
        _application(session, monthly_take_home_pay=amount),
        format="json",
    )

    assert resp.status_code == 201
    stored = FeeWaiverApplication.objects.get(session=session).monthly_take_home_pay
    assert stored == Decimal(amount)


def test_take_home_pay_is_encrypted_at_rest(setup):
    client, session, _ = setup
    client.post(
        "/api/intake/fee-waiver/",
        _application(session, monthly_take_home_pay="2873.41"),
        format="json",
    )
    fw = FeeWaiverApplication.objects.get(session=session)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT monthly_take_home_pay FROM fee_waiver_applications WHERE id = %s", [fw.id]
        )
        raw = cursor.fetchone()[0]

    assert "2873" not in raw
    assert fw.monthly_take_home_pay == Decimal("2873.41")


def test_the_old_income_expense_and_benefit_answers_are_no_longer_written(setup):
    # The page stopped asking them; the columns stay one release for the rows already saved.
    client, session, _ = setup
    resp = client.post(
        "/api/intake/fee-waiver/",
        _application(
            session,
            monthly_income="3200.00",
            monthly_expenses="2560.00",
            receives_public_benefits=True,
        ),
        format="json",
    )

    assert resp.status_code == 201
    fw = FeeWaiverApplication.objects.get(session=session)
    assert (fw.monthly_income, fw.monthly_expenses, fw.receives_public_benefits) == (
        None,
        None,
        False,
    )
    assert {"monthly_income", "monthly_expenses", "receives_public_benefits"}.isdisjoint(
        resp.json()
    )


# ── An answer the filer never gave (DIG-193) ──────────────────────────
#
# Form 103B line 3 prints the stored answer as a sworn Yes or No, so the server stores one
# only when the filer gave it, whatever the encoding, and keeps no kind of help without a Yes.

ENCODINGS = ["json", "multipart", "urlencoded"]


def _send(client, method, url, payload, encoding):
    if encoding == "json":
        return getattr(client, method)(url, payload, format="json")
    # A form can't carry null: a question left unanswered is missing from the body.
    form = {key: value for key, value in payload.items() if value is not None}
    if encoding == "multipart":
        return getattr(client, method)(url, form, format="multipart")
    return getattr(client, method)(
        url, urlencode(form, doseq=True), content_type="application/x-www-form-urlencoded"
    )


@pytest.mark.parametrize(
    ("encoding", "sent"),
    [
        ("json", "left out"),
        ("json", None),
        ("multipart", "left out"),
        ("multipart", ""),
        ("urlencoded", "left out"),
        ("urlencoded", ""),
    ],
)
def test_an_application_that_does_not_answer_non_cash_help_is_refused(setup, encoding, sent):
    client, session, _ = setup
    payload = _application(session, receives_noncash_assistance=sent)
    if sent == "left out":
        del payload["receives_noncash_assistance"]

    resp = _send(client, "post", "/api/intake/fee-waiver/", payload, encoding)

    assert resp.status_code == 400
    assert "receives_noncash_assistance" in resp.json()
    assert not FeeWaiverApplication.objects.filter(session=session).exists()


@pytest.mark.parametrize("encoding", ["multipart", "urlencoded"])
@pytest.mark.parametrize(("answer", "kinds"), [(False, []), (True, ["SNAP (food stamps)"])])
def test_a_form_encoded_application_keeps_the_answer_it_gives(setup, encoding, answer, kinds):
    client, session, _ = setup
    payload = _application(session, receives_noncash_assistance=answer, benefit_types=kinds)

    resp = _send(client, "post", "/api/intake/fee-waiver/", payload, encoding)

    assert resp.status_code == 201, resp.json()
    fw = FeeWaiverApplication.objects.get(session=session)
    assert (fw.receives_noncash_assistance, fw.benefit_types) == (answer, kinds)


def _saved_before_the_question(session):
    """An application saved before the page asked take-home pay and non-cash help."""
    return FeeWaiverApplication.objects.create(
        session=session, household_size=2, monthly_income=Decimal("1200.00")
    )


@pytest.mark.parametrize("encoding", ENCODINGS)
def test_a_kind_of_help_needs_a_yes_on_an_application_saved_before_the_question(setup, encoding):
    client, session, _ = setup
    fw = _saved_before_the_question(session)

    resp = _send(
        client, "patch", f"/api/intake/fee-waiver/{fw.id}/", {"benefit_types": ["SNAP"]}, encoding
    )

    fw.refresh_from_db()
    assert resp.status_code == 400
    assert (fw.receives_noncash_assistance, fw.benefit_types) == (None, [])


def test_an_application_saved_before_the_question_can_still_be_changed(setup):
    client, session, _ = setup
    fw = _saved_before_the_question(session)

    resp = client.patch(f"/api/intake/fee-waiver/{fw.id}/", {"household_size": 4}, format="json")

    fw.refresh_from_db()
    assert resp.status_code == 200
    assert (fw.household_size, fw.receives_noncash_assistance) == (4, None)


@pytest.mark.parametrize(("encoding", "sent"), [("json", None), ("urlencoded", "")])
def test_an_answer_given_cannot_be_taken_back_to_no_answer(setup, encoding, sent):
    # The filer answered line 3; an empty answer would print it blank and leave the kind stored.
    client, session, _ = setup
    client.post(
        "/api/intake/fee-waiver/",
        _application(session, receives_noncash_assistance=True, benefit_types=["SNAP"]),
        format="json",
    )
    fw = FeeWaiverApplication.objects.get(session=session)

    resp = _send(
        client,
        "patch",
        f"/api/intake/fee-waiver/{fw.id}/",
        {"receives_noncash_assistance": sent},
        encoding,
    )

    fw.refresh_from_db()
    assert resp.status_code == 400
    assert (fw.receives_noncash_assistance, fw.benefit_types) == (True, ["SNAP"])


# ── Reading the application back by session (DIG-157) ─────────────────


def _results(resp):
    assert resp.status_code == 200
    return resp.json()["results"]


def test_the_page_reads_only_the_application_of_the_session_it_shows(setup):
    # One filer can have several sessions, each with its own answers.
    client, session, user = setup
    other_session = IntakeSession.objects.create(user=user, district=session.district)
    client.post("/api/intake/fee-waiver/", _application(session), format="json")
    client.post(
        "/api/intake/fee-waiver/",
        _application(other_session, monthly_take_home_pay="900.00"),
        format="json",
    )

    first = _results(client.get(f"/api/intake/fee-waiver/?session={session.id}"))
    second = _results(client.get(f"/api/intake/fee-waiver/?session={other_session.id}"))

    assert [(row["session"], row["monthly_take_home_pay"]) for row in first] == [
        (session.id, "1750.00")
    ]
    assert [(row["session"], row["monthly_take_home_pay"]) for row in second] == [
        (other_session.id, "900.00")
    ]


def test_reading_another_users_session_returns_nothing(setup):
    client, session, _ = setup
    stranger = User.objects.create_user(username="stranger", password="pass")
    their_session = IntakeSession.objects.create(user=stranger, district=session.district)
    FeeWaiverApplication.objects.create(
        session=their_session,
        monthly_take_home_pay=Decimal("1000.00"),
        receives_noncash_assistance=False,
    )

    assert _results(client.get(f"/api/intake/fee-waiver/?session={their_session.id}")) == []


def test_reading_by_session_never_starts_an_application(setup):
    # An application puts Form 103B in the packet, so opening the page must not create one.
    client, session, _ = setup

    assert _results(client.get(f"/api/intake/fee-waiver/?session={session.id}")) == []
    assert not FeeWaiverApplication.objects.filter(session=session).exists()
    assert "form_103b" not in packet(session)


# ── Moving an application (DIG-178) ───────────────────────────────────


def test_a_filer_cannot_move_their_application_onto_another_users_session(setup):
    client, session, _ = setup
    victim = User.objects.create_user(username="fw_victim", password="pass")
    victim_session = IntakeSession.objects.create(user=victim, district=session.district)
    client.post("/api/intake/fee-waiver/", _application(session), format="json")
    fw = FeeWaiverApplication.objects.get(session=session)

    resp = client.patch(
        f"/api/intake/fee-waiver/{fw.id}/", {"session": victim_session.id}, format="json"
    )

    assert resp.status_code == 403
    fw.refresh_from_db()
    assert fw.session_id == session.id
    assert not FeeWaiverApplication.objects.filter(session=victim_session).exists()


def test_a_filer_can_still_change_their_own_application(setup):
    client, session, _ = setup
    client.post("/api/intake/fee-waiver/", _application(session), format="json")
    fw = FeeWaiverApplication.objects.get(session=session)

    resp = client.patch(
        f"/api/intake/fee-waiver/{fw.id}/",
        {"session": session.id, "household_size": 4},
        format="json",
    )

    assert resp.status_code == 200
    fw.refresh_from_db()
    assert (fw.session_id, fw.household_size) == (session.id, 4)
