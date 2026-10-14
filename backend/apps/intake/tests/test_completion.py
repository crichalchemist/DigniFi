"""Only the server marks an intake complete, and an edit after that reopens it (spec §5.3).

Business intent: forms are prepared only from an intake the filer completed, because only
then does an empty list mean "the filer said none". The browser can't claim that state
(DIG-151). Changing intake data after Complete sets the intake back to in progress, so the
filer presses Complete again, which re-runs its checks and the fee-waiver routing. Form
answers, SOFA and the fee-waiver application are not intake data and never reopen it.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    ExpenseInfo,
    IncomeInfo,
    IntakeSession,
)
from apps.users.models import User

FINISH = "Finish your intake before preparing your forms."


@pytest.fixture
def district(db):
    # The real ILND data: its name is one of the court forms' district choices, and preparing
    # forms works the means test out against its median income.
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


@pytest.fixture
def filer(district):
    user = User.objects.create_user(username="filer", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def completed(filer, district):
    """An intake the filer completed, with the three sections Complete requires."""
    _, user = filer
    session = IntakeSession.objects.create(
        user=user, district=district, status="completed", current_step=8
    )
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(
        session=session,
        marital_status="single",
        number_of_dependents=0,
        monthly_gross_wages=Decimal("3000.00"),
    )
    ExpenseInfo.objects.create(session=session)
    return session


def _session_url(session, action=""):
    return f"/api/intake/sessions/{session.pk}/{action}"


def _status(session):
    return IntakeSession.objects.get(pk=session.pk).status


def _complete_again(session):
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")


# ── Who marks an intake complete ──────────────────────────────────────


def test_browser_cannot_mark_intake_complete(filer, district):
    client, _ = filer
    claimed = {"status": "completed", "current_step": 8}

    created = client.post(
        "/api/intake/sessions/", {"district": district.id, **claimed}, format="json"
    )
    assert created.status_code == 201
    session = IntakeSession.objects.get(pk=created.data["session"]["id"])
    assert (session.status, session.current_step) == ("started", 1)

    patched = client.patch(_session_url(session), claimed, format="json")
    assert patched.status_code == 200
    session.refresh_from_db()
    assert (session.status, session.current_step) == ("started", 1)

    # update_step's nested data can't carry them either.
    stepped = client.post(
        _session_url(session, "update_step/"),
        {"current_step": 3, "data": claimed},
        format="json",
    )
    assert stepped.status_code == 200
    session.refresh_from_db()
    assert (session.status, session.current_step) == ("in_progress", 3)


_MISSING = object()


@pytest.mark.parametrize(
    "step",
    [0, 9, -1, "3", 3.0, 2.5, True, None, _MISSING],
    ids=["0", "9", "-1", "string", "float", "fraction", "bool", "null", "missing"],
)
def test_wizard_step_must_be_one_of_the_eight_steps(filer, completed, step):
    # A step the wizard doesn't have is a client fault, not something the filer can fix.
    client, _ = filer
    body = {} if step is _MISSING else {"current_step": step}

    response = client.post(_session_url(completed, "update_step/"), body, format="json")

    assert response.status_code == 400
    assert "current_step" in response.data
    completed.refresh_from_db()
    assert (completed.status, completed.current_step) == ("completed", 8)


def test_filer_who_leaves_every_expense_blank_can_complete(filer, district):
    # DIG-153: with every box blank, the Expenses step sends no amounts. The server drops the
    # read-only total sent here, so this body is the same as the step's empty one.
    client, user = filer
    session = IntakeSession.objects.create(user=user, district=district, current_step=3)
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900-12-3456",
        date_of_birth=date(1990, 1, 15),
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("0.00"))

    saved = client.patch(
        _session_url(session), {"expense_info": {"total_monthly_expenses": 0}}, format="json"
    )

    assert saved.status_code == 200
    expenses = ExpenseInfo.objects.get(session=session)
    assert expenses.calculate_total_monthly_expenses() == 0
    assert client.post(_session_url(session, "complete/")).status_code == 200
    assert _status(session) == "completed"


# ── An edit after Complete reopens the intake ─────────────────────────


def test_editing_a_completed_intake_asks_for_complete_again(filer, completed):
    client, _ = filer
    generate = {"session_id": completed.pk, "form_type": "form_106dec"}

    edited = client.patch(
        _session_url(completed), {"debtor_info": {"first_name": "Janet"}}, format="json"
    )
    assert edited.status_code == 200
    assert edited.data["status"] == "in_progress"
    assert _status(completed) == "in_progress"

    refused = client.post("/api/forms/generate/", generate, format="json")
    assert refused.status_code == 422
    assert refused.data["error"] == FINISH

    assert client.post(_session_url(completed, "complete/")).status_code == 200
    assert client.post("/api/forms/generate/", generate, format="json").status_code == 200


@pytest.mark.parametrize(
    "section,value",
    [
        ("debtor_info", {"first_name": "Janet"}),
        ("income_info", {"monthly_gross_wages": "3100.00", "monthly_tips": None}),
        ("expense_info", {"rent_or_mortgage": 900}),
        ("debts", [{"creditor_name": "Chase", "debt_type": "credit_card", "amount_owed": 500}]),
        (
            "assets",
            [{"asset_type": "bank_account", "description": "Checking", "current_value": 800}],
        ),
    ],
)
def test_saving_an_intake_step_after_complete_reopens_it(filer, completed, section, value):
    client, _ = filer

    response = client.patch(_session_url(completed), {section: value}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == "in_progress"
    assert _status(completed) == "in_progress"


def test_a_refused_save_leaves_a_completed_intake_complete(filer, completed):
    client, _ = filer

    response = client.patch(_session_url(completed), {"debtor_info": {"ssn": "123"}}, format="json")

    assert response.status_code == 400
    assert _status(completed) == "completed"


def test_moving_between_wizard_steps_after_complete_reopens_it(filer, completed):
    client, _ = filer

    response = client.post(
        _session_url(completed, "update_step/"), {"current_step": 5}, format="json"
    )

    assert response.status_code == 200
    assert _status(completed) == "in_progress"


@pytest.mark.parametrize(
    "endpoint,row",
    [
        ("contracts", {"counterparty_name": "Oak Street Apartments", "contract_type": "lease"}),
        ("codebtors", {"name": "Sam Doe", "relationship": "relative"}),
    ],
)
def test_adding_or_removing_a_contract_or_codebtor_after_complete_reopens_it(
    filer, completed, endpoint, row
):
    client, _ = filer
    url = _session_url(completed, f"{endpoint}/")

    added = client.post(url, row, format="json")
    assert added.status_code == 201
    assert _status(completed) == "in_progress"

    _complete_again(completed)
    removed = client.delete(f"{url}{added.data['id']}/")
    assert removed.status_code == 204
    assert _status(completed) == "in_progress"


@pytest.mark.parametrize(
    "endpoint,row",
    [
        ("contracts", {"counterparty_name": "Oak Street Apartments", "contract_type": "lease"}),
        ("codebtors", {"name": "Sam Doe", "relationship": "relative"}),
    ],
)
def test_saving_the_contracts_or_codebtors_list_after_complete_reopens_it(
    filer, completed, endpoint, row
):
    # Continue on steps 6 and 7 saves the whole list (DIG-147).
    client, _ = filer

    response = client.put(_session_url(completed, f"{endpoint}/"), [row], format="json")

    assert response.status_code == 200
    assert _status(completed) == "in_progress"


@pytest.mark.parametrize(
    "endpoint,row,change",
    [
        (
            "debts",
            {"creditor_name": "Chase", "debt_type": "credit_card", "amount_owed": "500.00"},
            {"amount_owed": "650.00"},
        ),
        (
            "assets",
            {"asset_type": "bank_account", "description": "Checking", "current_value": "800.00"},
            {"current_value": "950.00"},
        ),
    ],
)
def test_per_item_debt_and_asset_writes_after_complete_reopen_it(
    filer, completed, endpoint, row, change
):
    client, _ = filer
    url = f"/api/intake/{endpoint}/"

    created = client.post(url, {"session": completed.pk, **row}, format="json")
    assert created.status_code == 201
    assert _status(completed) == "in_progress"

    _complete_again(completed)
    updated = client.patch(f"{url}{created.data['id']}/", change, format="json")
    assert updated.status_code == 200
    assert _status(completed) == "in_progress"

    _complete_again(completed)
    deleted = client.delete(f"{url}{created.data['id']}/")
    assert deleted.status_code == 204
    assert _status(completed) == "in_progress"
    assert not AssetInfo.objects.filter(session=completed).exists()
    assert not DebtInfo.objects.filter(session=completed).exists()


def test_moving_a_debt_to_another_intake_reopens_both(filer, completed, district):
    client, user = filer
    other = IntakeSession.objects.create(user=user, district=district, status="completed")
    debt = DebtInfo.objects.create(
        session=completed, creditor_name="Chase", debt_type="credit_card", amount_owed=500
    )

    response = client.patch(f"/api/intake/debts/{debt.pk}/", {"session": other.pk}, format="json")

    assert response.status_code == 200
    assert (_status(completed), _status(other)) == ("in_progress", "in_progress")


# ── What is not intake data ───────────────────────────────────────────


def test_form_answers_sofa_and_fee_waiver_leave_a_completed_intake_complete(filer, completed):
    client, _ = filer

    answers = client.post(
        _session_url(completed, "answers/bulk/"),
        {
            "answers": [
                {"form_type": "form_101", "binding": "answer:form_101.q1", "value": "Yes"},
                {"form_type": "form_107", "binding": "sofa.has_prior_income", "value": "True"},
            ]
        },
        format="json",
    )
    sofa = client.patch(
        f"/api/intake/sofa-report/{completed.pk}/", {"has_business": False}, format="json"
    )
    fee_waiver = client.post(
        "/api/intake/fee-waiver/",
        {
            "session": completed.pk,
            "household_size": 1,
            "monthly_take_home_pay": "1600.00",
            "receives_noncash_assistance": False,
            "benefit_types": [],
            "cannot_pay_full": True,
            "cannot_pay_installments": True,
        },
        format="json",
    )

    assert (answers.status_code, sofa.status_code, fee_waiver.status_code) == (200, 200, 201)
    assert _status(completed) == "completed"
