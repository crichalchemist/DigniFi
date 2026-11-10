"""The line 4 question (3c4 R7).

Business intent: a filer who typed rent or lot rent and also linked a first mortgage on the home
they live in is never sent to court with Schedule J line 4 adding both without having said they
pay both. Complete and the forms refuse until the filer confirms the typed figure, and changing
the figure asks again.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.claims import (
    CLAIM_GAP_LEGACY_VEHICLE,
    CLAIM_GAP_LINE_4,
    format_figure,
)
from apps.intake.models import (
    AssetInfo,
    DebtorInfo,
    ExpenseInfo,
    IncomeInfo,
    IntakeSession,
)
from apps.intake.tests.builders import (
    answer_asset_lines,
    answer_claims,
    answer_household,
    linked_lease,
    linked_loan,
)
from apps.users.models import User


@pytest.fixture
def filer(db):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    user = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=user, district=District.objects.get(code="ilnd"))
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
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("3000.00")
    )
    answer_household(session)
    ExpenseInfo.objects.create(
        session=session, expenses_include_others="no", rent_or_mortgage=Decimal("1200.00")
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session


def _property(session, line, **details) -> AssetInfo:
    row = AssetInfo(
        session=session,
        ab_line=line,
        description="",
        current_value=Decimal("100"),
        entire_value=Decimal("100"),
    )
    row.set_details(details)
    row.save()
    return row


def _home(session, line="1") -> AssetInfo:
    if line == "1":
        return _property(
            session,
            "1",
            street="1 Demo Street",
            who="only_you",
            lives_here="yes",
            property_kinds=["single_family"],
        )
    return _property(session, "4", make="Demo", who="only_you", lives_here="yes")


def _deshawn(session, mortgage=1200, line="first"):
    """DeShawn's shape: a lived-in home with a first mortgage, every earlier gap answered."""
    home = _home(session)
    if mortgage is not None:
        linked_loan(session, home, mortgage, home_payment_line=line)
    answer_asset_lines(session, yes=("1",))
    return home


def _stored(session, **figures):
    row = ExpenseInfo.objects.get(session=session)
    for key, value in figures.items():
        setattr(row, key, Decimal(value))
    row.save()


def _complete(client, session):
    return client.post(f"/api/intake/sessions/{session.id}/complete/")


def _errors(client, session) -> list[dict]:
    response = _complete(client, session)
    assert response.status_code == 400, response.data
    return response.data["errors"]


def _sentence(typed="1,200.00", linked="1,200.00"):
    return {
        "step": "expense_info",
        "message": CLAIM_GAP_LINE_4.format(typed=typed, linked=linked),
    }


def _patch(client, session, body):
    return client.patch(f"/api/intake/sessions/{session.id}/", body, format="json")


def _confirm(client, session, value):
    return _patch(client, session, {"claim_answers": {"line_4_both_confirmed": value}})


def _line_4(session):
    return resolve(load_schema("schedule_j"), IntakeSession.objects.get(pk=session.pk)).get("4")


def test_a_typed_line_4_beside_a_first_mortgage_refuses_until_answered(filer):
    client, session = filer
    _deshawn(session)

    assert _errors(client, session)[-1] == _sentence()

    IntakeSession.objects.filter(pk=session.pk).update(status="completed")
    response = client.post(
        "/api/forms/generate/",
        {"session_id": session.id, "form_type": "schedule_j"},
        format="json",
    )
    assert response.status_code == 422
    assert response.data["step"] == "expense_info"
    assert response.data["error"] == _sentence()["message"]


def test_confirming_both_prints_both_and_a_changed_figure_asks_again(filer):
    client, session = filer
    _deshawn(session)

    assert _confirm(client, session, "1200.00").status_code == 200
    assert _complete(client, session).status_code == 200
    assert _line_4(session) == "2400.00"

    response = _patch(client, session, {"expense_info": {"rent_or_mortgage": "1250.00"}})
    assert response.status_code == 200, response.data
    assert _errors(client, session)[-1] == _sentence(typed="1,250.00")


def test_a_confirmed_figure_matches_however_it_was_written(filer):
    client, session = filer
    _deshawn(session)
    answer_claims(session, line_4_both_confirmed="1200")

    assert _complete(client, session).status_code == 200


def test_clearing_the_typed_figure_prints_the_mortgage_alone(filer):
    client, session = filer
    _deshawn(session)

    response = _patch(client, session, {"expense_info": {"rent_or_mortgage": 0}})

    assert response.status_code == 200, response.data
    assert _complete(client, session).status_code == 200
    assert _line_4(session) == "1200.00"


@pytest.mark.parametrize("case", ["no_typed", "no_mortgage", "additional_only", "home_lease_only"])
def test_no_question_without_both_figures(filer, case):
    client, session = filer
    if case == "no_typed":
        _stored(session, rent_or_mortgage="0")
        _deshawn(session)
    elif case == "no_mortgage":
        _deshawn(session, mortgage=None)
    elif case == "additional_only":
        _deshawn(session, line="additional")
    else:
        # R7: a home lease adds to J 4 without asking
        linked_lease(session, _home(session, line="4"), 700)
        answer_asset_lines(session, yes=("4",))

    assert _complete(client, session).status_code == 200


@pytest.mark.parametrize("value", ["abc", "-1", "1.234", "1234567890123", "NaN", "Infinity", 1200])
def test_line_4_confirmed_takes_only_a_figure(filer, value):
    client, session = filer

    assert _confirm(client, session, value).status_code == 400


def test_line_4_confirmed_none_clears_the_stored_value(filer):
    client, session = filer
    _deshawn(session)
    assert _confirm(client, session, "1200.00").status_code == 200

    assert _confirm(client, session, None).status_code == 200

    assert _errors(client, session)[-1] == _sentence()


def test_the_line_4_question_comes_after_the_legacy_gap(filer):
    client, session = filer
    _stored(session, vehicle_payment="350")
    _deshawn(session)

    errors = _errors(client, session)

    assert errors[-2:] == [
        {
            "step": "debts",
            "message": CLAIM_GAP_LEGACY_VEHICLE.format(
                typed="350.00", linked=format_figure(Decimal("0"))
            ),
        },
        _sentence(),
    ]
