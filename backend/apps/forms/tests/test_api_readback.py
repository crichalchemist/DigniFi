"""
The read-back: each persona's forms, built through the API, print what the seeded
persona's forms print (step 2 spec §7.6, DIG-140).

Business intent: the seeds write the database directly, so the oracle never sees a field
the API drops on the way in. The phone number and the "secured" flag were dropped that
way, and the filer signs every page under penalty of perjury. Each test sends one
persona's data, typed $0 amounts included, through the endpoints the wizard and the pages
after it call, then requires every form's stored values to equal the values built from
the seeded session.

It can't catch a page that sends a field under the wrong name, or never sends it: it
sends what this file sends (spec §10). Per-step vitest tests pin the names the server
expects.
"""

import json
from decimal import Decimal, InvalidOperation

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.models import GeneratedForm
from apps.forms.registry import build_parts, packet
from apps.forms.schema import load_schema
from apps.intake.management.commands.seed_demo_data import PERSONAS
from apps.intake.models import IncomeInfo, IntakeSession, SpouseIncome

User = get_user_model()

# These ask for the fee waiver on Form 101 line 8 (3f spec §10), so 103B is in their packets.
APPLIES = {"maria", "sarah"}


def _step_bodies(data):
    """
    Each wizard step's session save, as the step's autosave body sends it: one PATCH per
    step. The spouse's income goes only while it is asked (spec §8.2), so a persona
    without one sends none. The payroll deductions go on the Take-home pay step, and the
    Income step sends every other key.
    """
    deduction_keys = (*IncomeInfo.DEDUCTION_FIELDS, "payroll_other_specify")

    def split(income):
        kept = {key: value for key, value in income.items() if key not in deduction_keys}
        deductions = {key: income[key] for key in deduction_keys if key in income}
        return kept, deductions

    income, deductions = split(data["income"])
    income_step = {
        "income_info": income,
        "household": {"members": data["household"]["members"]},
    }
    take_home_pay_step = {"income_info": deductions}
    if data["spouse_income"] is not None:
        spouse, spouse_deductions = split(data["spouse_income"])
        income_step["spouse_income"] = spouse
        take_home_pay_step["spouse_income"] = spouse_deductions
    return [
        {"debtor_info": data["debtor"], "household": {"county": data["household"]["county"]}},
        income_step,
        take_home_pay_step,
        {"expense_info": data["expenses"]},
        # Every row, with its line, details and values, and every line answer, as 3b spec §4 saves.
        {"assets": data["assets"], "asset_lines": data["asset_lines"]},
        {"debts": data["debts"]},
    ]


def _sent(data):
    """Persona data as JSON carries it from the browser: amounts as decimal strings, dates as ISO."""
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def _household_answers(session):
    """The marriage answer, county, household list and spouse's income the session holds."""
    spouse = getattr(session, "spouse_income", None)
    return {
        "marital_status": session.income_info.marital_status,
        "county": session.household.county,
        "members": session.household.get_members(),
        "spouse_income": (
            None
            if spouse is None
            else {field: getattr(spouse, field) for field in SpouseIncome.SOURCE_FIELDS}
        ),
    }


def _send_through_the_api(persona):
    """Enter the persona as a filer would, then Generate All. Returns (session id, form types)."""
    data = PERSONAS[persona]()
    # The typed $0 amounts this sends: each persona, and each spouse, typed every Income box,
    # $0 where they get none of that kind, so no box is left blank.
    assert all(data["income"][field] is not None for field in IncomeInfo.SOURCE_FIELDS)
    assert data["spouse_income"] is None or all(
        data["spouse_income"][field] is not None for field in SpouseIncome.SOURCE_FIELDS
    )
    # Line 3 is sent with the Expenses step, so the readback can't pass by leaving it unsent.
    assert data["expenses"]["expenses_include_others"] in ("yes", "no")
    client = APIClient()
    client.force_authenticate(User.objects.create_user(username=f"api_{persona}", password="pw"))

    district = District.objects.get(code="ilnd")
    created = client.post(
        "/api/intake/sessions/", {"district": district.pk, "current_step": 1}, format="json"
    )
    assert created.status_code == 201, created.data
    session_id = created.data["session"]["id"]
    session_url = f"/api/intake/sessions/{session_id}/"

    # Continue saves each step on its own. Rows go in the seed's order, so they get ids in
    # the same order as the seeded rows.
    for body in _step_bodies(data):
        response = client.patch(session_url, _sent(body), format="json")
        assert response.status_code == 200, (list(body), response.data)
    # No persona has contracts or codebtors: Continue on steps 7 and 8 saves empty lists.
    for endpoint in ("contracts", "codebtors"):
        response = client.put(f"{session_url}{endpoint}/", [], format="json")
        assert response.status_code == 200, (endpoint, response.data)

    # Complete Intake, then the pages that follow it. Their saves keep the intake complete.
    # No means-test call: Generate All works it out from the stored intake (spec §5.6).
    response = client.post(f"{session_url}complete/")
    assert response.status_code == 200, response.data
    household_size = response.data["session"]["household"]["fee_waiver_household_size"]
    assert household_size is not None
    # The filing-fee page every filer passes after Complete: Form 101 line 8, and 103B's own
    # questions for a waiver filer. It never reopens the intake.
    response = client.put(f"{session_url}filing-fee/", _sent(data["filing_fee"]), format="json")
    assert response.status_code == 200, response.data
    if "sofa" in data:
        response = client.patch(
            f"/api/intake/sofa-report/{session_id}/", _sent(data["sofa"]), format="json"
        )
        assert response.status_code == 200, response.data

    generated = client.post("/api/forms/generate_all/", {"session_id": session_id}, format="json")
    assert generated.status_code == 200, generated.data
    assert generated.data["errors"] == []
    return session_id, [form["form_type"] for form in generated.data["generated"]]


def _comparable(form_type, values):
    """
    One part's values, with each repeat group's rows in a fixed order.

    Schedule J line 2 is the one production repeat group; its rows come in the household
    list's stored order, the same on both sides. A group a later step binds to stored rows
    has no fixed order (DIG-164), so within one part it compares regardless of it. Across
    parts it doesn't: a group past its last slot puts its rows on the form part and its
    copies by position, so another order moves other rows to a copy. Each row keeps its own
    values together, so an amount that moves to another row differs.
    """
    fixed = dict(values)
    rows = {}
    for field in load_schema(form_type).fields:
        if field.repeat and field.row and field.pdf_field in fixed:
            cell = (field.binding or "", fixed.pop(field.pdf_field))
            rows.setdefault((field.repeat, field.row), []).append(cell)
    groups = {}
    for (group, _), cells in rows.items():
        groups.setdefault(group, []).append(sorted(cells))
    return fixed, {group: sorted(group_rows) for group, group_rows in groups.items()}


def _comparable_document(form_type, document):
    """
    A form's parts document, each part's values made comparable as _comparable does. An
    attached sheet's part has no values: its rows are compared as they are.
    """
    return {
        **document,
        "parts": [
            {**part, "values": _comparable(form_type, part["values"])} if "values" in part else part
            for part in document["parts"]
        ],
    }


def _amount(text):
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


@pytest.mark.slow
@pytest.mark.django_db
@pytest.mark.parametrize("persona", list(PERSONAS))
def test_forms_built_through_the_api_print_what_the_seeded_forms_print(persona):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, verbosity=0)
    seeded = IntakeSession.objects.get(user__username=f"demo_{persona}")

    session_id, form_types = _send_through_the_api(persona)

    assert form_types == packet(seeded)
    assert ("form_103b" in form_types) is (persona in APPLIES)
    stored = {
        form.form_type: json.loads(form.field_values)
        for form in GeneratedForm.objects.filter(session_id=session_id)
    }
    assert {
        form_type: _comparable_document(form_type, document)
        for form_type, document in stored.items()
    } == {
        form_type: _comparable_document(form_type, build_parts(form_type, seeded))
        for form_type in packet(seeded)
    }
    built = IntakeSession.objects.get(pk=session_id)
    # No form reads these yet, so compare the stored answers directly: a member the API
    # dropped would otherwise pass.
    assert _household_answers(built) == _household_answers(seeded)
    # Only Priya's income is above the median, so only her packet holds 122A-2, and it
    # prints her own figures: her household's monthly income, hers and her husband's, on line 1
    # and her childcare on line 21.
    assert ("form_122a2" in stored) == (persona == "priya")
    if persona == "priya":
        (part,) = stored["form_122a2"]["parts"]
        amounts = [_amount(value) for value in part["values"].values()]
        assert any(amount is not None and amount > 0 for amount in amounts)
