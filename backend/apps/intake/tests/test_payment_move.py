"""The car and other-property payments come from their links, and every total adds them once.

3c4 R2, R4, R5: moving a payment from a typed Expenses amount to the debt or lease that pays it
changes no total.
"""

from decimal import Decimal

import pytest

from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import ExpenseInfo, Household, IncomeInfo
from apps.intake.tests.builders import (
    answer_household,
    linked_loan,
    linked_row,
)


def _household(session):
    household = getattr(session, "household", None) or Household(session=session)
    household.store_members([])
    household.save()


def _income(session):
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3000.00"))
    answer_household(session)


@pytest.mark.django_db
def test_moving_a_car_payment_leaves_every_total_unchanged(filer_session):
    _, session = filer_session
    _household(session)
    _income(session)
    ExpenseInfo.objects.create(session=session, rent_or_mortgage=Decimal("1000.00"))
    linked_loan(session, linked_row(session, "3"), 350)

    j = resolve(load_schema("schedule_j"), session)
    summary = resolve(load_schema("form_106sum"), session)
    waiver = resolve(load_schema("form_103b"), session)

    assert j.get("22a") == "1350.00"
    assert j.get("22c") == "1350.00"
    assert j.get("23b") == "1350.00"
    assert summary.get("5") == "1350.00"
    assert waiver.get("undefined_7") == "1350.00"
    assert j.get("17a") == "350.00"
    assert j.get("4") == "1000.00"


@pytest.mark.django_db
def test_stored_retired_figures_no_longer_print_or_count(filer_session):
    _, session = filer_session
    _household(session)
    expense = ExpenseInfo.objects.create(
        session=session,
        rent_or_mortgage=Decimal("1000.00"),
        vehicle_payment=Decimal("350.00"),
        other_property_mortgages=Decimal("600.00"),
    )

    j = resolve(load_schema("schedule_j"), session)

    assert j.get("17a") is None
    assert j.get("20a") is None
    assert j.get("22a") == "1000.00"
    assert expense.calculate_total_monthly_expenses() == 1000.0


@pytest.mark.django_db
def test_the_api_no_longer_reads_an_assets_amount_owed(filer_session):
    client, session = filer_session
    linked_row(session, "3")

    body = client.get(f"/api/intake/sessions/{session.pk}/").json()

    assert body["assets"]
    for asset in body["assets"]:
        assert "amount_owed" not in asset


@pytest.mark.django_db
def test_the_api_no_longer_offers_the_two_retired_amounts(filer_session):
    client, session = filer_session
    ExpenseInfo.objects.create(session=session, rent_or_mortgage=Decimal("100.00"))

    expense_info = client.get(f"/api/intake/sessions/{session.pk}/").json()["expense_info"]

    assert "vehicle_payment" not in expense_info
    assert "other_property_mortgages" not in expense_info
