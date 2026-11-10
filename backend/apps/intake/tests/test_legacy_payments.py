"""A stored car or other-property payment the links don't cover (3c4 R6, R17).

Business intent: a filer who typed a car or other-property payment before payments moved to the
debts and leases that pay them is never sent to court with a Schedule J that silently drops it.
Complete and the forms refuse until the payments are linked or the figure is removed, and Remove
is a save of 0 that never takes any other figure.
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
    CLAIM_GAP_LEGACY_OTHER,
    CLAIM_GAP_LEGACY_VEHICLE,
    format_figure,
    legacy_payments,
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
    complete_contract,
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
    ExpenseInfo.objects.create(session=session, expenses_include_others="no")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session


def _store(session, **figures):
    row = ExpenseInfo.objects.get(session=session)
    for key, value in figures.items():
        setattr(row, key, Decimal(value))
    row.save()


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


def _car(session) -> AssetInfo:
    return _property(session, "3", make="Demo", who="only_you")


def _other_home(session) -> AssetInfo:
    return _property(
        session,
        "1",
        street="1 Demo Street",
        who="only_you",
        lives_here="no",
        property_kinds=["single_family"],
    )


def _lines(session, *yes):
    answer_asset_lines(session, yes=yes)


def _complete(client, session):
    response = client.post(f"/api/intake/sessions/{session.id}/complete/")
    return response


def _errors(client, session) -> list[dict]:
    response = _complete(client, session)
    assert response.status_code == 400, response.data
    return response.data["errors"]


def _vehicle(typed, linked):
    return {
        "step": "debts",
        "message": CLAIM_GAP_LEGACY_VEHICLE.format(typed=typed, linked=linked),
    }


def _other(typed, linked):
    return {"step": "debts", "message": CLAIM_GAP_LEGACY_OTHER.format(typed=typed, linked=linked)}


def _patch(client, session, expense_info):
    return client.patch(
        f"/api/intake/sessions/{session.id}/", {"expense_info": expense_info}, format="json"
    )


@pytest.mark.parametrize(("linked", "refused"), [(0, True), (200, True), (350, False)])
def test_a_stored_car_payment_the_links_dont_cover_refuses_complete(filer, linked, refused):
    client, session = filer
    _store(session, vehicle_payment="350")
    linked_loan(session, _car(session), linked)
    _lines(session, "3")

    if refused:
        figure = format_figure(Decimal(linked))
        assert _errors(client, session)[-1] == _vehicle("350.00", figure)
    else:
        assert _complete(client, session).status_code == 200


def test_a_lease_covers_a_stored_car_payment(filer):
    client, session = filer
    _store(session, vehicle_payment="389")
    linked_lease(session, _car(session), 389)
    _lines(session, "3")

    assert _complete(client, session).status_code == 200


def test_a_stored_other_property_mortgage_the_links_dont_cover_refuses_complete(filer):
    client, session = filer
    _store(session, other_property_mortgages="600")
    linked_loan(session, _other_home(session), 500)
    linked_loan(session, _car(session), 300)  # a car loan never covers other property
    _lines(session, "1", "3")

    assert _errors(client, session)[-1] == _other("600.00", "500.00")


def test_a_mortgage_on_other_property_never_covers_a_car_figure(filer):
    client, session = filer
    _store(session, vehicle_payment="350")
    linked_loan(session, _other_home(session), 400)
    _lines(session, "1")

    assert _errors(client, session)[-1] == _vehicle("350.00", "0.00")


def test_the_legacy_gap_comes_last(filer):
    client, session = filer
    _store(session, vehicle_payment="350", other_property_mortgages="600")
    complete_contract(session, counterparty_name="Demo Storage Co", description="")

    errors = _errors(client, session)

    assert errors[-2:] == [_vehicle("350.00", "0.00"), _other("600.00", "0.00")]
    assert errors.index(errors[-2]) > 0
    assert any("Demo Storage Co" in error["message"] for error in errors[:-2])


def test_the_forms_refuse_a_legacy_figure_with_the_step_that_fixes_it(filer):
    client, session = filer
    _store(session, vehicle_payment="350")
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")

    response = client.post(
        "/api/forms/generate/",
        {"session_id": session.id, "form_type": "schedule_j"},
        format="json",
    )

    assert response.status_code == 422
    assert response.data["step"] == "debts"
    assert response.data["error"] == _vehicle("350.00", "0.00")["message"]


def test_remove_clears_the_figure_and_the_gap(filer):
    client, session = filer
    _store(session, vehicle_payment="350", rent_or_mortgage="900")

    response = _patch(client, session, {"vehicle_payment": 0})

    assert response.status_code == 200, response.data
    stored = ExpenseInfo.objects.get(session=session)
    assert stored.vehicle_payment == 0
    assert stored.rent_or_mortgage == Decimal("900")
    assert response.data["legacy_payments"]["vehicle_payment"] is None
    assert _complete(client, session).status_code == 200


def test_remove_replies_with_the_figure_cleared(filer):
    # R17: the reply read the Expenses row from before the save, so Remove still showed 350.00.
    client, session = filer
    _store(session, vehicle_payment="350")

    response = _patch(client, session, {"vehicle_payment": 0})

    assert response.data["legacy_payments"] == {
        "vehicle_payment": None,
        "other_property_mortgages": None,
    }


def test_a_legacy_figure_takes_only_zero(filer):
    client, session = filer
    _store(session, vehicle_payment="350")

    response = _patch(client, session, {"vehicle_payment": "200.00"})

    assert response.status_code == 200, response.data
    assert ExpenseInfo.objects.get(session=session).vehicle_payment == Decimal("350")
    assert response.data["legacy_payments"]["vehicle_payment"] == "350.00"

    response = _patch(client, session, {"vehicle_payment": "-1.00"})

    assert response.status_code == 400
    assert ExpenseInfo.objects.get(session=session).vehicle_payment == Decimal("350")


def test_a_save_without_the_retired_figures_leaves_them_alone(filer):
    client, session = filer
    _store(session, vehicle_payment="350")

    response = _patch(client, session, {"rent_or_mortgage": "900.00"})

    assert response.status_code == 200, response.data
    assert ExpenseInfo.objects.get(session=session).vehicle_payment == Decimal("350")


def test_legacy_payments_names_a_figure_only_above_zero(filer):
    _, session = filer
    none = {"vehicle_payment": None, "other_property_mortgages": None}
    assert legacy_payments(IntakeSession.objects.get(pk=session.pk)) == none

    _store(session, vehicle_payment="0")
    assert legacy_payments(IntakeSession.objects.get(pk=session.pk)) == none

    _store(session, vehicle_payment="350")
    assert legacy_payments(IntakeSession.objects.get(pk=session.pk)) == {
        "vehicle_payment": "350.00",
        "other_property_mortgages": None,
    }


def test_legacy_payments_is_null_with_no_expenses_row(db):
    user = User.objects.create_user(username="nobody", password="pw")
    district = District.objects.create(
        code="X", name="X", state="IL", court_name="X", filing_fee_chapter_7=Decimal("338.00")
    )
    session = IntakeSession.objects.create(user=user, district=district)

    assert legacy_payments(session) == {"vehicle_payment": None, "other_property_mortgages": None}


def test_removing_the_car_brings_back_the_legacy_gap(filer):
    client, session = filer
    _store(session, vehicle_payment="350", rent_or_mortgage="1000")
    car = _car(session)
    loan = linked_loan(session, car, 350)
    _lines(session, "3")
    assert _complete(client, session).status_code == 200
    j = resolve(load_schema("schedule_j"), IntakeSession.objects.get(pk=session.pk))
    assert j.get("22a") == "1350.00"

    car.delete()

    loan.refresh_from_db()
    assert loan.secured_by_id is None
    _lines(session)
    j = resolve(load_schema("schedule_j"), IntakeSession.objects.get(pk=session.pk))
    assert j.get("17a") is None
    assert j.get("22a") == "1000.00"
    assert _errors(client, session)[-1] == _vehicle("350.00", "0.00")


def test_remove_reopens_a_completed_intake(filer):
    client, session = filer
    _store(session, vehicle_payment="350")
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")
    answer_claims(session, no_debts=True)

    response = _patch(client, session, {"vehicle_payment": 0})

    assert response.status_code == 200, response.data
    assert IntakeSession.objects.get(pk=session.pk).status == "in_progress"
