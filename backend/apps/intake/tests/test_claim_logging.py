"""A claim gap names a creditor in the reply body and nowhere else (forms 3c3 spec §7.7).

Business intent: a refusal from Complete or the forms calls says which creditor, party or
property needs an answer, because the filer needs to know which row to fix. Logs reach Sentry,
so no log line may carry that name, an address or the last four digits of an account number.
"""

import logging
from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import AssetInfo, DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import (
    answer_asset_lines,
    answer_claims,
    answer_household,
    linked_loan,
)
from apps.users.models import User

CREDITOR = "Zephyrine Credit Union"
CREDITOR_STREET = "9 Demo Quillfeather Lane"
CREDITOR_CITY = "Demo Wrenfield"
CREDITOR_ZIP = "60697"
ACCOUNT_NUMBER = "900123456789"
LAST_4 = "6789"
PARTY = "Hollis Brandt Collections"
PARTY_STREET = "44 Demo Marlowe Court"
PARTY_CITY = "Demo Hollowbrook"
PARTY_ZIP = "60698"
HOME_STREET = "7823 S Sangamon St"


@pytest.fixture
def filer(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    user = User.objects.create_user(username="logfiler", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    district = District.objects.get(code="ilnd")
    session = IntakeSession.objects.create(
        user=user, district=district, status="in_progress", current_step=9
    )
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900-12-3456",
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("3000.00")
    )
    ExpenseInfo.objects.create(session=session, expenses_include_others="no")
    answer_household(session, claims=None)
    return client, session


def _car(session):
    car = AssetInfo(
        session=session,
        ab_line="3",
        description="Demo car",
        current_value=Decimal("5000.00"),
        entire_value=Decimal("5000.00"),
    )
    car.set_details({"who": "only_you", "make": "Demo"})
    car.save()
    answer_asset_lines(session, ["3"])
    return car


def _home(session):
    """A finished line 1 row with no "Do you live here?" answer."""
    home = AssetInfo(
        session=session,
        ab_line="1",
        description="",
        current_value=Decimal("100000.00"),
        entire_value=Decimal("100000.00"),
    )
    home.set_details(
        {"street": HOME_STREET, "property_kinds": ["single_family"], "who": "only_you"}
    )
    home.save()
    answer_asset_lines(session, ["1"])
    return home


def _session_url(session, action=""):
    return f"/api/intake/sessions/{session.pk}/{action}"


def _leaks(caplog, secrets):
    """Every secret that any log record's message or arguments carries."""
    found = set()
    for record in caplog.records:
        text = [record.getMessage(), str(record.args), str(record.exc_text)]
        text.append(str(record.exc_info[1]) if record.exc_info else "")
        for secret in secrets:
            if any(secret in piece for piece in text):
                found.add(secret)
    return found


def _refusals_logged(caplog):
    """The django.request 4xx records: proof the log capture was listening for the refusals."""
    return [
        record
        for record in caplog.records
        if record.name == "django.request" and record.levelno == logging.WARNING
    ]


def _complete_then_generate(client, session):
    """Press Complete with a gap, then ask for a form as a filer who completed earlier."""
    complete = client.post(_session_url(session, "complete/"))
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")
    generate = client.post(
        "/api/forms/generate/",
        {"session_id": session.pk, "form_type": "form_106dec"},
        format="json",
    )
    return complete, generate


def test_no_log_line_carries_a_creditors_name_address_or_last_four(filer, caplog):
    client, session = filer
    car = _car(session)
    caplog.set_level(logging.DEBUG)

    saved = client.patch(
        _session_url(session),
        {
            "debts": [
                {
                    "creditor_name": CREDITOR,
                    "debt_type": "auto_loan",
                    "amount_owed": "500.00",
                    "street_address": CREDITOR_STREET,
                    "city": CREDITOR_CITY,
                    "state": "IL",
                    "zip_code": CREDITOR_ZIP,
                    "account_number": ACCOUNT_NUMBER,
                    "is_secured": True,
                    "secured_by": car.pk,
                    "notice_parties": [
                        {
                            "name": PARTY,
                            "street_address": PARTY_STREET,
                            "city": PARTY_CITY,
                            "state": "IL",
                            "zip_code": PARTY_ZIP,
                        }
                    ],
                }
            ]
        },
        format="json",
    )
    assert saved.status_code == 200, saved.data
    complete, generate = _complete_then_generate(client, session)

    # The filer is told which creditor, in the reply body only.
    assert complete.status_code == 400
    assert any(CREDITOR in error["message"] for error in complete.data["errors"])
    assert generate.status_code == 422
    assert CREDITOR in generate.data["error"]
    assert generate.data["step"] == "debts"
    secrets = [
        CREDITOR,
        CREDITOR_STREET,
        CREDITOR_CITY,
        CREDITOR_ZIP,
        ACCOUNT_NUMBER,
        LAST_4,
        PARTY,
        PARTY_STREET,
        PARTY_CITY,
        PARTY_ZIP,
    ]
    assert len(_refusals_logged(caplog)) == 2
    assert _leaks(caplog, secrets) == set()


def test_no_log_line_carries_the_street_a_do_you_live_here_gap_names(filer, caplog):
    client, session = filer
    home = _home(session)
    caplog.set_level(logging.DEBUG)

    saved = client.patch(
        _session_url(session),
        {
            "debts": [
                {
                    "creditor_name": CREDITOR,
                    "debt_type": "mortgage",
                    "amount_owed": "90000.00",
                    "account_number": ACCOUNT_NUMBER,
                    "is_secured": True,
                    "secured_by": home.pk,
                }
            ]
        },
        format="json",
    )
    assert saved.status_code == 200, saved.data
    complete, generate = _complete_then_generate(client, session)

    assert complete.status_code == 400
    assert complete.data["errors"][0]["step"] == "assets"
    assert HOME_STREET in complete.data["errors"][0]["message"]
    assert generate.status_code == 422
    assert generate.data["step"] == "assets"
    assert HOME_STREET in generate.data["error"]
    assert len(_refusals_logged(caplog)) == 2
    assert _leaks(caplog, [HOME_STREET, CREDITOR, ACCOUNT_NUMBER, LAST_4]) == set()


def test_no_log_line_carries_a_figure_a_payment_gap_quotes(filer, caplog):
    client, session = filer
    home = _home(session)
    home.set_details({**home.get_details(), "lives_here": "yes"})
    home.save()
    linked_loan(session, home, "900", home_payment_line="first")
    answer_asset_lines(session, ["1"])
    answer_claims(session)
    expenses = ExpenseInfo.objects.get(session=session)
    expenses.vehicle_payment = Decimal("4321.09")
    expenses.rent_or_mortgage = Decimal("1234.56")
    expenses.save()
    caplog.set_level(logging.DEBUG)

    complete, generate = _complete_then_generate(client, session)

    # The filer reads each figure in the reply body, as the sentences print it.
    assert complete.status_code == 400
    messages = " ".join(error["message"] for error in complete.data["errors"])
    assert "4,321.09" in messages
    assert "1,234.56" in messages
    assert generate.status_code == 422
    assert "4,321.09" in generate.data["error"]
    assert len(_refusals_logged(caplog)) == 2
    assert _leaks(caplog, ["4,321.09", "4321.09", "1,234.56", "1234.56"]) == set()
