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
from apps.eligibility.models import MeansTest
from apps.forms.models import GeneratedForm
from apps.forms.registry import build_field_values, packet
from apps.forms.schema import load_schema
from apps.intake.management.commands.seed_demo_data import PERSONAS
from apps.intake.models import IncomeInfo, IntakeSession

User = get_user_model()

# The means test qualifies these personas for a fee waiver, so after Complete the wizard
# sends them to the fee-waiver page, and the seed gives them an application.
WAIVER_FILERS = {"maria", "deshawn", "sarah"}

# Each wizard step's session save: (the section it sends, the persona's data for it).
WIZARD_STEPS = [
    ("debtor_info", "debtor"),
    ("income_info", "income"),
    ("expense_info", "expenses"),
    ("assets", "assets"),
    ("debts", "debts"),
]


def _sent(data):
    """Persona data as JSON carries it from the browser: amounts as decimal strings, dates as ISO."""
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def _fee_waiver_application(data):
    """The application the seed stores, as the fee-waiver page sends it."""
    return {
        "household_size": data["debtor"]["household_size"],
        **data["fee_waiver"],
        "cannot_pay_full": True,
        "cannot_pay_installments": True,
    }


def _fee_waiver_answers(session):
    """What the session's fee-waiver application holds, or None without one."""
    fw = getattr(session, "fee_waiver", None)
    if fw is None:
        return None
    return {
        "household_size": fw.household_size,
        "monthly_take_home_pay": fw.monthly_take_home_pay,
        "receives_noncash_assistance": fw.receives_noncash_assistance,
        "benefit_types": fw.benefit_types,
        "cannot_pay_full": fw.cannot_pay_full,
        "cannot_pay_installments": fw.cannot_pay_installments,
    }


def _send_through_the_api(persona):
    """Enter the persona as a filer would, then Generate All. Returns (session id, form types)."""
    data = PERSONAS[persona]()
    # The typed $0 amounts this sends: each persona typed every Income box, $0 where they
    # get none of that kind, so no box is left blank.
    assert all(data["income"][field] is not None for field in IncomeInfo.SOURCE_FIELDS)
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
    for section, key in WIZARD_STEPS:
        response = client.patch(session_url, {section: _sent(data[key])}, format="json")
        assert response.status_code == 200, (section, response.data)
    # No persona has contracts or codebtors: Continue on steps 6 and 7 saves empty lists.
    for endpoint in ("contracts", "codebtors"):
        response = client.put(f"{session_url}{endpoint}/", [], format="json")
        assert response.status_code == 200, (endpoint, response.data)

    # Complete Intake, then the pages that follow it. Their saves keep the intake complete.
    # No means-test call: Generate All works it out from the stored intake (spec §5.6).
    response = client.post(f"{session_url}complete/")
    assert response.status_code == 200, response.data
    if persona in WAIVER_FILERS:
        response = client.post(
            "/api/intake/fee-waiver/",
            {"session": session_id, **_sent(_fee_waiver_application(data))},
            format="json",
        )
        assert response.status_code == 201, response.data
    if "sofa" in data:
        response = client.patch(
            f"/api/intake/sofa-report/{session_id}/", _sent(data["sofa"]), format="json"
        )
        assert response.status_code == 200, response.data

    generated = client.post("/api/forms/generate_all/", {"session_id": session_id}, format="json")
    assert generated.status_code == 200, generated.data
    assert generated.data["errors"] == []
    # Generate All worked the means test out, and it qualifies exactly the filers the wizard
    # sends to the fee-waiver page.
    qualifies = MeansTest.objects.get(session_id=session_id).qualifies_for_fee_waiver
    assert qualifies == (persona in WAIVER_FILERS)
    return session_id, [form["form_type"] for form in generated.data["generated"]]


def _comparable(form_type, values):
    """
    A form's values, with each repeat group's rows in a fixed order.

    Stored rows have no fixed order (DIG-164), so Form 107's rows compare regardless of it.
    Each row keeps its own values together, so an amount that moves to another row differs.
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


def _amount(text):
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


@pytest.mark.django_db
@pytest.mark.parametrize("persona", list(PERSONAS))
def test_forms_built_through_the_api_print_what_the_seeded_forms_print(persona):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, verbosity=0)
    seeded = IntakeSession.objects.get(user__username=f"demo_{persona}")

    session_id, form_types = _send_through_the_api(persona)

    assert form_types == packet(seeded)
    stored = {
        form.form_type: json.loads(form.field_values)
        for form in GeneratedForm.objects.filter(session_id=session_id)
    }
    assert {form_type: _comparable(form_type, values) for form_type, values in stored.items()} == {
        form_type: _comparable(form_type, build_field_values(form_type, seeded))
        for form_type in packet(seeded)
    }
    # Form 103B prints take-home pay and the non-cash answer, but no form prints the two
    # "cannot pay" answers, so the stored applications are compared directly.
    built = IntakeSession.objects.get(pk=session_id)
    assert _fee_waiver_answers(built) == _fee_waiver_answers(seeded)
    assert (_fee_waiver_answers(built) is None) == (persona not in WAIVER_FILERS)
    # Only Priya's income is above the median, so only her packet holds 122A-2, and it
    # prints figures worked out from her own expenses.
    assert ("form_122a2" in stored) == (persona == "priya")
    if persona == "priya":
        amounts = [_amount(value) for value in stored["form_122a2"].values()]
        assert any(amount is not None and amount > 0 for amount in amounts)
