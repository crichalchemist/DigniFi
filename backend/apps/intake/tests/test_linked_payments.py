"""Which payments on property reach Schedule J, and on which line (3c4 spec §8, rulings R1, R2).

Business intent: each monthly payment on property is counted once, on the line of the property
it pays, so Schedule J's lines and every total agree. A payment the filer's answers no longer
support (a debt that isn't secured, a lease that isn't for a vehicle, a scanned draft, another
filer's row) never prints and never adds to a total.
"""

import json
from decimal import Decimal
from unittest import mock

import pytest
from django.conf import settings

from apps.districts.models import District
from apps.intake.claims import format_figure, linked_payments, total_monthly_expenses
from apps.intake.models import AssetInfo, ExpenseInfo, IntakeSession
from apps.intake.tests.builders import (
    complete_debt,
    linked_lease,
    linked_loan,
    linked_row,
)
from apps.users.models import User

FRONTEND_SRC = settings.BASE_DIR.parent / "frontend" / "src"
CASES = (
    settings.BASE_DIR.parent
    / "frontend"
    / "src"
    / "components"
    / "wizard"
    / "steps"
    / "claims"
    / "linkedPaymentCases.json"
)


@pytest.fixture
def filer(db):
    District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return User.objects.create_user(username="filer", password="pw")


@pytest.fixture
def session(filer):
    return IntakeSession.objects.create(user=filer, district=District.objects.get(code="ILND"))


def _linked(session):
    return linked_payments(IntakeSession.objects.get(pk=session.pk))


def test_a_linked_payment_is_counted_once(session):
    linked_loan(session, linked_row(session, "3"), "350")
    L = _linked(session)
    assert L.j17["17a"] == 350
    assert L.vehicle_total == 350
    assert L.total == 350


def test_unsecured_payments_never_reach_schedule_j(session):
    complete_debt(session, monthly_payment=Decimal("200"))
    L = _linked(session)
    assert L.total == 0
    assert all(value == 0 for value in L.j17.values())


def test_a_co_signed_loan_at_zero_leaves_its_line_blank(session):
    first, second = linked_row(session, "3"), linked_row(session, "3")
    linked_lease(session, first, "389")
    linked_loan(session, second, "0")
    L = _linked(session)
    assert L.j17 == {"17a": 389, "17b": 0, "17c": 0, "17d": 0}
    assert L.total == 389


def test_a_lived_in_motor_home_is_counted_once_and_takes_no_vehicle_line(session):
    other_home = linked_row(session, "4")
    lived_in = linked_row(session, "4", "yes")
    car = linked_row(session, "3")
    linked_loan(session, other_home, "50")
    linked_loan(session, lived_in, "900", home_payment_line="first")
    linked_loan(session, car, "300")
    L = _linked(session)
    assert L.first_mortgage == 900
    assert L.j17["17a"] == 300
    assert L.j17["17b"] == 50
    assert L.vehicle_total == 350
    assert L.total == 1250


def test_a_first_mortgage_goes_to_line_4_and_an_additional_one_to_line_5(session):
    home = linked_row(session, "1", "yes")
    linked_loan(session, home, "1200", home_payment_line="first")
    linked_loan(session, home, "250", home_payment_line="additional")
    L = _linked(session)
    assert L.first_mortgage == 1200
    assert L.additional_mortgage == 250
    assert L.vehicle_total == 0


def test_a_mortgage_on_a_home_the_filer_does_not_live_in_goes_to_line_20a(session):
    linked_loan(session, linked_row(session, "1", "no"), "800")
    linked_loan(session, linked_row(session, "1", None), "100")
    L = _linked(session)
    assert L.other_real_property == 900
    assert L.first_mortgage == 0


def test_home_payment_line_counts_only_on_a_home_row(session):
    linked_loan(session, linked_row(session, "3"), "120", home_payment_line="additional")
    L = _linked(session)
    assert L.j17["17a"] == 120
    assert L.additional_mortgage == 0


def test_a_vehicle_lease_on_a_home_the_filer_lives_in_goes_to_line_4(session):
    linked_lease(session, linked_row(session, "4", "yes"), "700")
    L = _linked(session)
    assert L.home_lease == 700
    assert L.first_mortgage == 0
    assert L.j17["17a"] == 0
    assert L.vehicle_total == 0
    assert L.total == 700


def test_vehicles_three_and_four_take_17c_and_17d_with_their_words(session):
    for payment in ("10", "20", "30", "40"):
        linked_loan(session, linked_row(session, "3"), payment)
    L = _linked(session)
    assert L.j17 == {"17a": 10, "17b": 20, "17c": 30, "17d": 40}
    assert L.j17_words == {"17c": "Vehicle 3", "17d": "Vehicle 4"}


def test_one_other_property_payment_reads_payment_on_other_property(session):
    linked_loan(session, linked_row(session, "3"), "100")
    linked_loan(session, linked_row(session, "6"), "60")
    L = _linked(session)
    assert L.j17["17c"] == 60
    assert L.j17_words["17c"] == "Payment on other property"
    assert L.j17_words["17d"] == ""
    assert L.vehicle_total == 100


def test_payments_past_17d_add_to_17d_and_say_so(session):
    for payment in ("10", "20", "30", "40", "50"):
        linked_loan(session, linked_row(session, "3"), payment)
    linked_loan(session, linked_row(session, "6"), "5")
    L = _linked(session)
    assert L.j17 == {"17a": 10, "17b": 20, "17c": 30, "17d": 95}
    assert L.j17_words["17d"] == "Other secured payments"
    assert L.vehicle_total == 150
    assert L.total == 155


def test_payments_on_one_other_property_share_a_slot(session):
    linked_loan(session, linked_row(session, "3"), "100")
    other = linked_row(session, "6")
    linked_loan(session, other, "60")
    linked_loan(session, other, "15")
    L = _linked(session)
    assert L.j17["17c"] == 75
    assert L.j17_words["17c"] == "Payment on other property"
    assert L.j17["17d"] == 0
    assert L.j17_words["17d"] == ""


def test_other_property_takes_its_slot_in_catalog_order(session):
    linked_loan(session, linked_row(session, "7"), "40")
    linked_loan(session, linked_row(session, "6"), "60")
    L = _linked(session)
    assert L.j17["17c"] == 60
    assert L.j17["17d"] == 40
    assert L.j17_words == {"17c": "Payment on other property", "17d": "Payment on other property"}


def test_a_vehicle_with_no_payment_leaves_its_line_blank(session):
    linked_loan(session, linked_row(session, "3"), "10")
    linked_loan(session, linked_row(session, "3"), "20")
    linked_row(session, "3")
    linked_loan(session, linked_row(session, "6"), "60")
    L = _linked(session)
    assert L.j17["17c"] == 0
    assert L.j17_words["17c"] == ""
    assert L.j17["17d"] == 60
    assert L.j17_words["17d"] == "Payment on other property"


def test_two_loans_on_one_car_add_on_its_line(session):
    car = linked_row(session, "3")
    linked_loan(session, car, "200")
    linked_loan(session, car, "75")
    L = _linked(session)
    assert L.j17["17a"] == 275
    assert L.j17["17b"] == 0


def test_a_debt_no_longer_secured_never_reaches_schedule_j(session):
    car = linked_row(session, "3")
    debt = linked_loan(session, car, "350", is_secured=False)
    stored = type(debt).objects.get(pk=debt.pk)
    assert stored.secured_by_id == car.pk
    assert stored.monthly_payment == Decimal("350")
    assert _linked(session).total == 0


def test_a_lease_changed_away_from_a_vehicle_never_reaches_schedule_j(session):
    car = linked_row(session, "3")
    residential = linked_lease(session, car, "389", lease_kind="residential")
    contract = linked_lease(session, car, "100", contract_type="contract")
    for row in (residential, contract):
        stored = type(row).objects.get(pk=row.pk)
        assert stored.vehicle_asset_id == car.pk
        assert stored.monthly_payment > 0
    assert _linked(session).total == 0


def test_a_draft_never_counts(session):
    linked_loan(session, linked_row(session, "3"), "350", is_draft=True)
    assert _linked(session).total == 0


def test_a_link_to_another_sessions_row_never_counts(session, filer):
    other = IntakeSession.objects.create(user=filer, district=session.district)
    foreign_car = linked_row(other, "3")
    linked_loan(session, foreign_car, "350")
    assert _linked(session).total == 0


def test_a_missing_payment_counts_as_zero(session):
    linked_loan(session, linked_row(session, "3"), "0", monthly_payment=None)
    assert _linked(session).total == 0


def test_the_total_adds_typed_lines_and_linked_payments(session):
    ExpenseInfo.objects.create(
        session=session, rent_or_mortgage=Decimal("1000"), food_and_groceries=Decimal("200")
    )
    linked_loan(session, linked_row(session, "3"), "350")
    assert total_monthly_expenses(IntakeSession.objects.get(pk=session.pk)) == Decimal("1550.00")


def test_the_total_reads_the_typed_sum_through_the_model(session):
    ExpenseInfo.objects.create(session=session)
    with mock.patch.object(
        ExpenseInfo,
        "calculate_total_monthly_expenses",
        side_effect=RuntimeError("decrypt failed"),
    ):
        with pytest.raises(RuntimeError):
            total_monthly_expenses(IntakeSession.objects.get(pk=session.pk))


def test_a_figure_prints_with_cents_and_commas():
    assert format_figure(Decimal("1200")) == "1,200.00"
    assert format_figure(Decimal("0.5")) == "0.50"
    assert format_figure(Decimal("1234567.89")) == "1,234,567.89"


def test_a_missing_shared_cases_file_fails_instead_of_skipping_where_the_frontend_is():
    if not FRONTEND_SRC.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    assert CASES.is_file(), "the one pin between the server's sums and the browser's is gone"


def test_the_shared_cases_match_the_server(filer):
    if not FRONTEND_SRC.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    cases = json.loads(CASES.read_text())
    assert len(cases) >= 16
    district = District.objects.get(code="ILND")
    for case in cases:
        session = IntakeSession.objects.create(user=filer, district=district)
        rows: list[AssetInfo] = [
            linked_row(session, row["line"], row["lives_here"]) for row in case["assets"]
        ]
        for debt in case["debts"]:
            asset = None if debt["asset"] is None else rows[debt["asset"]]
            over = {"is_secured": debt["secured"], "secured_by": asset}
            if debt["home_payment_line"] is not None:
                over["home_payment_line"] = debt["home_payment_line"]
            linked_loan(session, asset, debt["payment"], **over)
        for contract in case["contracts"]:
            linked_lease(
                session,
                rows[contract["asset"]],
                contract["payment"],
                contract_type=contract["contract_type"],
                lease_kind=contract["lease_kind"],
            )
        L = _linked(session)
        got = {
            "allLinked": format_figure(L.total),
            "vehicleTotal": format_figure(L.vehicle_total),
            "otherRealProperty": format_figure(L.other_real_property),
            "firstMortgage": format_figure(L.first_mortgage),
        }
        assert got == case["expect"], case["name"]
