"""One list of what an intake still lacks, and everything that reads it (forms step 4a).

Business intent: Complete, the read-only gaps endpoint and the wizard's step bound all answer
from the same place, so the words a filer sees on Review are the words Complete refuses with,
in the same order, and a check on the list can never move the intake.
"""

import re
from datetime import date
from decimal import Decimal

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.asset_lines import asset_step_gaps
from apps.intake.claims import claim_step_gaps
from apps.intake.completion import WIZARD_STEP_COUNT, Gap, completion_gaps
from apps.intake.models import DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession
from apps.intake.petition import (
    DETAIL_DEBTS_ON_DUTY,
    DETAIL_VENUE,
    GATE_DEBT_NATURE,
    GATE_HAZARD,
    GATE_ITIN,
    GATE_MAILING,
    GATE_OTHER_NAMES,
    GATE_OTHER_SSN,
    GATE_PENDING_CASE,
    GATE_PRIOR_BANKRUPTCY,
    GATE_RENTS,
    GATE_SOLE_PROPRIETOR,
)
from apps.intake.schedule_i import DETAIL_EMPLOYMENT
from apps.intake.tests.builders import (
    answer_asset_lines,
    answer_household,
    answer_petition,
    complete_debt,
)
from apps.users.models import User

# Step 1's seven questions, in the order the step asks them.
STEP_1_GATE_SENTENCES = [
    GATE_OTHER_NAMES,
    GATE_ITIN,
    GATE_OTHER_SSN,
    GATE_MAILING,
    GATE_PRIOR_BANKRUPTCY,
    GATE_PENDING_CASE,
    GATE_SOLE_PROPRIETOR,
]

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"


@pytest.fixture
def district(db):
    # The real ILND data, as test_completion.py loads it: the means test's median table is in
    # force, so a gaps endpoint that wrongly ran the means test would show here.
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
    """An intake the filer completed, with the sections Complete requires."""
    _, user = filer
    session = IntakeSession.objects.create(
        user=user, district=district, status="completed", current_step=9
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
        marital_status="not_married",
        monthly_gross_wages=Decimal("3000.00"),
    )
    answer_household(session)
    ExpenseInfo.objects.create(session=session, expenses_include_others="no")
    answer_petition(session)
    return session


@pytest.fixture
def unfinished(filer, district):
    """The session of test_complete_lists_every_gap_in_wizard_order: nearly everything is open."""
    _, user = filer
    session = IntakeSession.objects.create(user=user, district=district, current_step=9)
    answer_asset_lines(session)
    _scanned_debt(session)
    return session


def _scanned_debt(session):
    # What an upload creates: a draft the filer hasn't checked on the Amounts Owed step yet.
    return complete_debt(
        session,
        is_draft=True,
        creditor_name="Larkfield General Hospital",
        debt_type="medical",
        amount_owed=Decimal("2000.00"),
        data_source="uploaded_document",
    )


def _session_url(session, action=""):
    return f"/api/intake/sessions/{session.pk}/{action}"


def _writes(queries):
    # The audit middleware logs every authenticated request, a GET included, so its own row is
    # not the intake being written.
    return [
        q["sql"]
        for q in queries
        if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        and '"audit_logs"' not in q["sql"]
    ]


def _wizard_steps_source():
    return (FRONTEND / "constants" / "wizardSteps.ts").read_text()


def test_the_gap_list_is_what_complete_refuses_in_the_same_order(filer, unfinished):
    client, _ = filer

    gaps = completion_gaps(unfinished)
    response = client.post(_session_url(unfinished, "complete/"))

    assert response.status_code == 400
    gates = [g for g in gaps if g.kind == Gap.GATE]
    assert gates
    assert [(g.step, str(g)) for g in gates] == [
        (e["step"], e["message"]) for e in response.data["errors"]
    ]
    # The venue choice and the employment status are the details an untouched intake lists (steps
    # 1 and 2 ask them, and Form 101 and Schedule I print the lines blank), and Complete never
    # names them (4b-R4, 4c-R1).
    assert [str(g) for g in gaps if g.kind == Gap.DETAIL] == [DETAIL_VENUE, DETAIL_EMPLOYMENT]


def test_a_finished_intake_has_no_gaps(filer, completed):
    assert completion_gaps(completed) == []


def test_the_seven_step_1_gates_come_after_the_county_and_before_the_income_step(filer, unfinished):
    # Wizard order: Form 101's step 1 questions sit after the county on the same step, so
    # Review lists them before anything the Income step asks (4b-R4).
    gaps = completion_gaps(unfinished)

    assert [g.step for g in gaps[:9]] == ["debtor_info"] * 9
    assert [str(g) for g in gaps[2:9]] == STEP_1_GATE_SENTENCES
    assert all(g.kind == Gap.GATE for g in gaps[:9])
    # Then step 1's one detail (the venue left open), and only then the Income step.
    assert (gaps[9].step, gaps[9].kind, str(gaps[9])) == ("debtor_info", Gap.DETAIL, DETAIL_VENUE)
    assert gaps[10].step == "income_info"
    assert all(g.step != "debtor_info" for g in gaps[10:])


def test_the_hazard_gate_follows_the_assets_gaps_and_the_rent_gate_sits_among_the_contracts_gaps(
    filer, district
):
    # The hazard question ends the Assets step, so it is listed right after the last Schedule A/B
    # gap and before the claims walk; the rent question is on Contracts & Leases, after its gaps
    # and before Codebtors' (4b-R4). No home row is linked, so the claims walk has no Assets gap.
    _, user = filer
    session = IntakeSession.objects.create(user=user, district=district, current_step=9)
    answer_asset_lines(session, yes=("3",))  # Yes on vehicles with no row: an Assets gap
    asset_messages = [str(g) for g in asset_step_gaps(session)]
    claim_messages = [str(g) for g in claim_step_gaps(session)]
    assert asset_messages and claim_messages

    gaps = completion_gaps(session)
    messages = [str(g) for g in gaps]
    hazard = messages.index(GATE_HAZARD)
    rents = messages.index(GATE_RENTS)

    assert messages[hazard - 1] == asset_messages[-1]
    assert messages[hazard + 1] == claim_messages[0]
    assert gaps[hazard].step == "assets"
    assert gaps[rents - 1].step == "contracts"
    assert gaps[rents + 1].step == "codebtors"
    assert gaps[rents].step == "contracts"


def test_the_rent_gate_stays_before_the_claims_tail_when_the_claims_steps_have_no_gap(
    filer, completed
):
    # With Contracts and Codebtors finished there is nothing to sit beside: the rent question
    # still belongs to the wizard-order part of the list, never after the legacy figure's gap,
    # whose step (Amounts Owed) comes before Contracts & Leases in the wizard.
    completed.status = "in_progress"
    completed.save(update_fields=["status"])
    answer_petition(completed, rents_residence=None)
    ExpenseInfo.objects.filter(session=completed).update(vehicle_payment=Decimal("350.00"))
    completed.refresh_from_db()

    gaps = [(g.step, str(g)) for g in completion_gaps(completed)]

    assert [step for step, _ in gaps] == ["contracts", "debts"]
    assert gaps[0][1] == GATE_RENTS


def test_the_debts_petition_gaps_sit_after_the_claims_debts_gaps_and_before_contracts(
    filer, unfinished
):
    # Line 16 and the Supp's questions are asked on Amounts Owed, so they follow that step's own
    # gaps (here the scanned debt) and come before anything Contracts & Leases asks (4d).
    claim_messages = [(g.step, str(g)) for g in claim_step_gaps(unfinished)]
    last_debts = [c for c in claim_messages if c[0] == "debts"][-1]
    first_contracts = next(c for c in claim_messages if c[0] == "contracts")

    gaps = completion_gaps(unfinished)
    at = [str(g) for g in gaps].index(GATE_DEBT_NATURE)

    assert (gaps[at].step, gaps[at].kind) == ("debts", Gap.GATE)
    assert (gaps[at - 1].step, str(gaps[at - 1])) == last_debts
    assert (gaps[at + 1].step, str(gaps[at + 1])) == first_contracts


def test_the_debts_petition_gaps_list_on_a_session_with_no_later_claims_gap(filer, completed):
    # With Contracts and Codebtors finished there is no later claims gap to sit before: line 16's
    # gate still ends the wizard-order part, before the rent question and the claims tail.
    completed.status = "in_progress"
    completed.save(update_fields=["status"])
    answer_petition(completed, debt_nature=None, rents_residence=None)
    ExpenseInfo.objects.filter(session=completed).update(vehicle_payment=Decimal("350.00"))
    completed.refresh_from_db()

    gaps = [(g.step, str(g)) for g in completion_gaps(completed)]

    assert [step for step, _ in gaps] == ["debts", "contracts", "debts"]
    assert gaps[0][1] == GATE_DEBT_NATURE
    assert gaps[1][1] == GATE_RENTS


def test_complete_refuses_an_unanswered_line_16_and_lets_an_open_follow_up_through(
    filer, completed
):
    # Line 16 is a gate; a military follow-up is a detail that prints only on Form 122A-1Supp.
    client, _ = filer
    completed.status = "in_progress"
    completed.save(update_fields=["status"])
    answer_petition(completed, debt_nature=None)

    refused = client.post(_session_url(completed, "complete/"))

    assert refused.status_code == 400
    assert refused.data["errors"] == [{"step": "debts", "message": GATE_DEBT_NATURE}]

    answer_petition(completed, debt_nature="consumer", disabled_veteran="yes")
    listed = client.get(_session_url(completed, "gaps/"))
    finished = client.post(_session_url(completed, "complete/"))

    assert listed.data == {
        "gaps": [
            {
                "kind": "detail",
                "message": DETAIL_DEBTS_ON_DUTY,
                "step": "debts",
                "forms": ["form_122a1_supp"],
            }
        ]
    }
    assert finished.status_code == 200
    assert finished.data["session"]["status"] == "completed"


def test_a_case_on_the_sheet_before_the_name_is_entered_still_lists_every_gap(filer, district):
    # The sheet that measures a fourth earlier case is headed by the filer's name; with step 1's
    # name not saved yet, Review must still list what is missing, never answer with an error.
    client, user = filer
    session = IntakeSession.objects.create(user=user, district=district, current_step=9)
    answer_petition(
        session,
        prior_bankruptcy_answer="yes",
        prior_cases=[{}, {}, {}, {"district": "W" * 40}],
    )

    gaps = completion_gaps(session)
    listed = client.get(_session_url(session, "gaps/"))

    assert str(gaps[0]) == "Enter your name and address on the Your Information step."
    # The sheet was measured, nameless: its case is named too long.
    too_long = "Your answer for line 9's district, in case 4, is too long to fit on Form 101."
    assert too_long in [str(g) for g in gaps]
    assert listed.status_code == 200
    assert listed.data["gaps"][0]["message"] == str(gaps[0])


def test_a_detail_is_listed_and_complete_lets_it_through(filer, completed):
    # Every gate answered and the venue left open: Review names the open line, with the form
    # that prints it blank, and Complete still goes through (spec §5.7).
    client, _ = filer
    completed.status = "in_progress"
    completed.save(update_fields=["status"])
    answer_petition(completed, venue_choice=None)

    listed = client.get(_session_url(completed, "gaps/"))
    finished = client.post(_session_url(completed, "complete/"))

    assert listed.data == {
        "gaps": [
            {
                "kind": "detail",
                "message": DETAIL_VENUE,
                "step": "debtor_info",
                "forms": ["form_101"],
            }
        ]
    }
    assert finished.status_code == 200
    assert finished.data["session"]["status"] == "completed"


def test_a_gate_carries_no_forms(filer, unfinished):
    # A gate refuses every form at once, so no form's card repeats it (4b-R12).
    client, _ = filer

    entries = client.get(_session_url(unfinished, "gaps/")).data["gaps"]

    gates = [e for e in entries if e["kind"] == "gate"]
    assert gates
    assert all(e["forms"] == [] for e in gates)


def test_a_gate_is_what_complete_refuses(filer, completed):
    client, _ = filer
    completed.status = "in_progress"
    completed.save(update_fields=["status"])
    answer_petition(completed, itin_answer=None)

    response = client.post(_session_url(completed, "complete/"))

    assert response.status_code == 400
    assert response.data["errors"] == [{"step": "debtor_info", "message": GATE_ITIN}]


def test_a_detail_gap_never_refuses_complete_but_a_gate_after_it_does(
    filer, completed, monkeypatch
):
    # A detail prints blank, so Complete lets it through (spec §5.7); a gate anywhere in the list
    # refuses, naming the gate's step and never the detail's.
    client, _ = filer
    completed.status = "in_progress"
    completed.save(update_fields=["status"])
    detail = Gap("A detail.", "contracts", Gap.DETAIL)
    gate = Gap("A gate.", "assets", Gap.GATE)

    monkeypatch.setattr("apps.intake.views.completion_gaps", lambda session: [detail, gate])
    refused = client.post(_session_url(completed, "complete/"))
    monkeypatch.setattr("apps.intake.views.completion_gaps", lambda session: [detail])
    passed = client.post(_session_url(completed, "complete/"))

    assert refused.status_code == 400
    assert refused.data["errors"] == [{"step": "assets", "message": "A gate."}]
    assert passed.status_code == 200
    assert passed.data["session"]["status"] == "completed"
    completed.refresh_from_db()
    assert completed.status == "completed"


def test_the_gaps_endpoint_returns_the_list_and_writes_nothing(filer, unfinished, completed):
    client, _ = filer
    before = (unfinished.status, unfinished.current_step, unfinished.completed_at)

    with CaptureQueriesContext(connection) as queries:
        response = client.get(_session_url(unfinished, "gaps/"))

    assert response.status_code == 200
    assert response.data == {
        "gaps": [
            {"message": str(g), "step": g.step, "kind": g.kind, "forms": list(g.forms)}
            for g in completion_gaps(unfinished)
        ]
    }
    assert {e["kind"] for e in response.data["gaps"]} == {"gate", "detail"}
    assert not _writes(queries)
    unfinished.refresh_from_db()
    assert (unfinished.status, unfinished.current_step, unfinished.completed_at) == before

    # A finished intake: an empty list, and it stays completed (a read never reopens it).
    with CaptureQueriesContext(connection) as queries:
        response = client.get(_session_url(completed, "gaps/"))

    assert response.status_code == 200
    assert response.data == {"gaps": []}
    assert not _writes(queries)
    completed.refresh_from_db()
    assert completed.status == "completed"


def test_the_gaps_endpoint_is_the_filers_own(filer, district):
    client, _ = filer
    other = User.objects.create_user(
        username="otherfiler", email="other@example.com", password="testpass123"
    )
    theirs = IntakeSession.objects.create(user=other, district=district)

    assert client.get(_session_url(theirs, "gaps/")).status_code == 404


def test_the_gaps_endpoint_answers_200_where_the_means_test_would_refuse(filer, district):
    # A session with no IncomeInfo row: the means test raises IncomeNotSplit. The endpoint never
    # runs the means test, which the missing income row alone proves.
    client, user = filer
    session = IntakeSession.objects.create(user=user, district=district)

    response = client.get(_session_url(session, "gaps/"))

    assert response.status_code == 200
    assert any(g["step"] == "income_info" for g in response.data["gaps"])


def test_wizard_step_count_is_the_browsers():
    # Read from the frontend itself, so a step added to wizardSteps.ts on one side only fails
    # here: update_step would refuse the new last step.
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")

    assert WIZARD_STEP_COUNT == len(re.findall(r"key: '(\w+)'", _wizard_steps_source()))


def test_update_step_names_the_wizards_last_step_in_its_refusal(filer, completed):
    client, _ = filer

    response = client.post(
        _session_url(completed, "update_step/"),
        {"current_step": WIZARD_STEP_COUNT + 1},
        format="json",
    )

    assert response.data == {
        "current_step": [f"Must be a whole number from 1 to {WIZARD_STEP_COUNT}."]
    }


def test_update_step_bound_follows_the_wizards_step_count(filer, completed, monkeypatch):
    # The refusal above would pass with the constant's value written in as a literal; moving the
    # constant is what proves the view reads it. The patch target is the name views.py imports.
    client, _ = filer
    monkeypatch.setattr("apps.intake.views.WIZARD_STEP_COUNT", 11)

    accepted = client.post(
        _session_url(completed, "update_step/"), {"current_step": 11}, format="json"
    )
    refused = client.post(
        _session_url(completed, "update_step/"), {"current_step": 12}, format="json"
    )

    assert accepted.status_code == 200
    assert refused.status_code == 400
    assert refused.data == {"current_step": ["Must be a whole number from 1 to 11."]}


@pytest.fixture
def bare_session(filer, district):
    """A session with no petition record yet, as a test starts one."""
    _, user = filer
    return IntakeSession.objects.create(user=user, district=district)


def _stored_petition(session) -> dict:
    return IntakeSession.objects.get(pk=session.pk).petition_answers.get_answers()


def test_answer_petition_keeps_what_a_test_stored_and_lets_it_change_or_clear_an_answer(
    bare_session,
):
    # Tasks 8-12 build sessions that answer one question differently and call finish_intake
    # after; a builder that put its default back over that answer would test the wrong filer.
    answer_petition(bare_session, hazard_answer="yes", venue_choice="other")
    answer_petition(bare_session)
    stored = _stored_petition(bare_session)
    assert stored["hazard_answer"] == "yes"
    assert stored["venue_choice"] == "other"
    assert stored["rents_residence"] == "no"

    answer_petition(bare_session, hazard_answer="no", rents_residence=None)
    stored = _stored_petition(bare_session)
    assert stored["hazard_answer"] == "no"
    assert "rents_residence" not in stored


def test_answer_petition_refuses_a_question_form_101_does_not_ask(bare_session):
    with pytest.raises(KeyError):
        answer_petition(bare_session, not_a_question="no")


def test_the_session_a_test_holds_reads_the_second_answer_petition_without_a_reload(
    bare_session,
):
    # A test calls the builder, then reads the gaps or resolves a form on the same session
    # object: a stale cached record there would let a negative test pass on old answers.
    answer_petition(bare_session)
    answer_petition(bare_session, hazard_answer="yes", rents_residence=None)

    held = bare_session.petition_answers.get_answers()
    assert held["hazard_answer"] == "yes"
    assert "rents_residence" not in held
    assert held == _stored_petition(bare_session)
