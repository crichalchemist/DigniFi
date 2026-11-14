"""Form 122A-2 reads only what the filer gave DigniFi; whatever the page will ask stays
unanswered until the filer answers it."""

from dataclasses import fields, replace
from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.districts.means_standards import NoMeansTestTable
from apps.districts.models import District
from apps.eligibility.means_inputs import read_inputs, read_tables
from apps.eligibility.means_lines import PRESUMPTION, work_out
from apps.eligibility.tests.test_means_lines import PRIYA
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import (
    answer_household,
    complete_debt,
    linked_lease,
    linked_loan,
    linked_row,
)
from apps.users.models import User

PRIYAS_ANSWERS = {
    f.name: getattr(PRIYA, f.name)
    for f in fields(PRIYA)
    if f.name.startswith("line_") and f.name not in ("line_1", "line_35_past_due", "line_41a")
}

ROOMMATE = {
    "relationship": "roommate",
    "age": 30,
    "lives_with_you": True,
    "claimed_or_supported": False,
}
CHILD_ELSEWHERE = {
    "relationship": "child",
    "age": 9,
    "lives_with_you": False,
    "claimed_or_supported": True,
}


@pytest.fixture
def session(db):
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court, Northern District of Illinois",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="means_inputs", password="pw")
    session = IntakeSession.objects.create(user=user, district=district)
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("9000.00")
    )
    answer_household(session, members=[ROOMMATE, CHILD_ELSEWHERE])
    return session


def _debtor(session, born):
    DebtorInfo.objects.create(
        session=session,
        first_name="Demo",
        last_name="Filer",
        ssn="123-45-6789",
        date_of_birth=born,
        phone="3125550100",
        email="demo@example.com",
        street_address="1 Demo St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return IntakeSession.objects.get(pk=session.pk)


def test_line_fives_people_are_the_filer_and_everyone_claimed_or_supported(session):
    session = _debtor(session, date(1990, 1, 15))
    assert read_inputs(session).ages == (36, 9)


@pytest.mark.parametrize("born, age", [(date(1961, 10, 16), 65), (date(1961, 10, 17), 64)])
def test_the_filers_age_is_worked_out_on_the_fill_date_by_calendar(session, born, age):
    assert read_inputs(_debtor(session, born)).ages[0] == age


def test_a_session_with_no_debtor_info_or_county_reads_as_missing_inputs(session):
    session.household.county = None
    session.household.save()
    inputs = read_inputs(IntakeSession.objects.get(pk=session.pk))
    assert (inputs.ages[0], inputs.county) == (None, None)


def test_the_district_code_is_read_in_lower_case(session):
    session.district.code = "ILND"
    session.district.save()
    assert read_inputs(session).district == "ilnd"


def test_every_answer_the_page_will_ask_is_unanswered(session):
    inputs = read_inputs(session)
    asked = (15, 16, 17, 18, 19, 20, 21, 22, 23, 25, 26, 27, 28, 29, 30, 31)
    assert all(getattr(inputs, f"line_{n}") is None for n in asked)
    assert (
        inputs.line_3_answer,
        inputs.line_3_rows,
        inputs.line_34_answer,
        inputs.line_36_answer,
        inputs.line_36_payment,
        inputs.line_43_answer,
        inputs.vehicle_choice,
    ) == (None, (), None, None, None, None, None)


def test_line_35_counts_only_confirmed_unsecured_debts_answered_with_a_priority_kind(session):
    complete_debt(
        session,
        creditor_name="Demo Tax",
        priority_answer="taxes",
        past_due_amount=Decimal("600.00"),
    )
    complete_debt(session, priority_answer="no", past_due_amount=Decimal("100.00"))
    complete_debt(session, priority_answer="not_sure", past_due_amount=Decimal("100.00"))
    complete_debt(
        session, priority_answer="taxes", is_draft=True, past_due_amount=Decimal("500.00")
    )
    home = linked_row(session, "1", "yes", "Demo Home")
    linked_loan(session, home, "100", priority_answer="taxes", past_due_amount=Decimal("900.00"))
    assert read_inputs(session).line_35_past_due == Decimal("600.00")


def test_line_35_is_unknown_while_a_priority_debt_has_no_past_due_figure(session):
    complete_debt(session, priority_answer="taxes", past_due_amount=None)
    assert read_inputs(session).line_35_past_due is None


def test_line_41a_reads_schedule_e_f_part_2_alone(session):
    complete_debt(session, priority_answer="no", amount_owed=Decimal("1000.00"))
    complete_debt(session, priority_answer="not_sure", amount_owed=Decimal("500.00"))
    complete_debt(
        session,
        priority_answer="taxes",
        amount_owed=Decimal("3000.00"),
        nonpriority_amount=Decimal("200.00"),
        past_due_amount=Decimal("3000.00"),
    )
    home = linked_row(session, "1", "yes", "Demo Home")
    linked_loan(session, home, "100", amount_owed=Decimal("9000.00"))
    assert read_inputs(session).line_41a == Decimal("1500.00")


def test_secured_debts_carry_their_property_and_whether_it_is_the_home(session):
    home = linked_row(session, "1", "yes", "Demo Home")
    car = linked_row(session, "3", None, "Demo Car")
    elsewhere = linked_row(session, "1", "no", "Demo Rental")
    home_loan = linked_loan(session, home, "800", creditor_name="A Home Bank")
    car_loan = linked_loan(session, car, "300", creditor_name="B Car Bank")
    rental_loan = linked_loan(session, elsewhere, "200", creditor_name="C Rental Bank")
    complete_debt(session, creditor_name="D Not Secured", secured_by=car)
    linked_loan(session, car, "50", creditor_name="E Draft", is_draft=True)
    other = IntakeSession.objects.create(user=session.user, district=session.district)
    foreign = linked_row(other, "3", None, "Foreign Car")
    stray_loan = linked_loan(session, foreign, "75", creditor_name="F Stray Bank")
    got = {d.debt_id: d for d in read_inputs(session).secured_debts}
    assert [d.creditor for d in read_inputs(session).secured_debts] == [
        "A Home Bank",
        "B Car Bank",
        "C Rental Bank",
        "F Stray Bank",
    ]
    assert (got[home_loan.pk].asset_id, got[home_loan.pk].on_home, got[home_loan.pk].property) == (
        home.pk,
        True,
        "Demo Home",
    )
    assert (got[car_loan.pk].asset_id, got[car_loan.pk].on_home) == (car.pk, False)
    assert got[rental_loan.pk].on_home is False
    assert got[car_loan.pk].monthly_payment == Decimal("300.00")
    assert (
        got[stray_loan.pk].asset_id,
        got[stray_loan.pk].on_home,
        got[stray_loan.pk].property,
    ) == (
        None,
        False,
        "",
    )


def test_vehicles_are_line_3_rows_and_line_4_rows_not_lived_in_with_their_loans_and_leases(
    session,
):
    car = linked_row(session, "3", None, "")
    car.description = ""
    car.set_details({"make": "Demo", "model": "Hatch", "year": "2019", "lives_here": None})
    car.save()
    linked_loan(session, car, "300")
    trailer = linked_row(session, "4", "no", "Demo Trailer")
    linked_lease(session, trailer, "200")
    linked_row(session, "4", "yes", "Demo Home On Wheels")
    first, second = read_inputs(session).vehicles
    assert (first.asset_id, first.name, first.financed, first.leased) == (
        car.pk,
        "Demo Hatch 2019",
        True,
        False,
    )
    assert (second.asset_id, second.name, second.financed, second.leased) == (
        trailer.pk,
        "Demo Trailer",
        False,
        True,
    )


def test_a_vehicle_is_financed_or_leased_only_by_a_counted_loan_or_a_vehicle_lease(session):
    stale_lease = linked_row(session, "3", None, "Demo Stale Lease Car")
    linked_lease(session, stale_lease, "200", lease_kind="residential")
    other_contract = linked_row(session, "3", None, "Demo Contract Car")
    linked_lease(session, other_contract, "200", contract_type="contract")
    not_counted = linked_row(session, "3", None, "Demo Uncounted Loan Car")
    complete_debt(session, creditor_name="Not Secured", secured_by=not_counted)
    linked_loan(session, not_counted, "50", creditor_name="Draft", is_draft=True)
    got = {v.asset_id: (v.financed, v.leased) for v in read_inputs(session).vehicles}
    assert got == {
        stale_lease.pk: (False, False),
        other_contract.pk: (False, False),
        not_counted.pk: (False, False),
    }


def test_a_loan_on_a_motor_home_the_filer_lives_in_is_on_the_home(session):
    motor_home = linked_row(session, "4", "yes", "Demo Motor Home")
    loan = linked_loan(session, motor_home, "400", creditor_name="G Motor Bank")
    (debt,) = read_inputs(session).secured_debts
    assert (debt.debt_id, debt.asset_id, debt.on_home, debt.property) == (
        loan.pk,
        motor_home.pk,
        True,
        "Demo Motor Home",
    )


def test_read_tables_gives_the_calculator_the_figures_in_force(
    means_standards_2026, section_104_2025
):
    tables, used = read_tables()
    assert tables.housing["Cook"][3] == (Decimal("953.00"), Decimal("2219.00"))
    assert (tables.areas["LaSalle"], tables.operating["chicago"], tables.ownership_one_car) == (
        "midwest",
        (Decimal("334.00"), Decimal("668.00")),
        Decimal("703.00"),
    )
    assert [t["name"] for t in used] == ["IRS expense standards", "Bankruptcy Code dollar amounts"]


def test_read_tables_refuses_before_july_15_2026(means_standards_2026, section_104_2025):
    with pytest.raises(NoMeansTestTable):
        read_tables(date(2026, 7, 14))


@pytest.mark.django_db
def test_priyas_122a2_matches_the_hand_worked_figures():
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", "--reset", persona="priya", verbosity=0)
    session = IntakeSession.objects.filter(user__username="demo_priya").latest("id")
    inputs = read_inputs(session)
    assert (
        inputs.line_1,
        inputs.ages,
        inputs.county,
        inputs.line_35_past_due,
        inputs.line_41a,
    ) == (
        Decimal("13800.00"),
        (43, 45, 10, 7),
        "Cook",
        Decimal("3000.00"),
        Decimal("57000.00"),
    )
    (car,) = inputs.vehicles
    (kestrel,) = inputs.secured_debts
    assert (
        car.name,
        car.financed,
        kestrel.creditor,
        kestrel.asset_id,
        kestrel.monthly_payment,
    ) == (
        "Honda CR-V EX 2021",
        True,
        "Kestrel Auto Finance",
        car.asset_id,
        Decimal("450.00"),
    )
    answered = replace(
        inputs,
        vehicles=(replace(car, claimed=True),),
        secured_debts=(replace(kestrel, payments_left=37, payment_changes="no"),),
        **PRIYAS_ANSWERS,
    )
    lines = work_out(answered, read_tables()[0])
    assert {k: lines.lines[k] for k in ("24", "32", "37", "38", "39c", "39d", "40")} == {
        "24": Decimal("10087.50"),
        "32": Decimal("850.00"),
        "37": Decimal("424.10"),
        "38": Decimal("11361.60"),
        "39c": Decimal("2188.40"),
        "39d": Decimal("131304.00"),
        "40": "2",
    }
    assert lines.outcome == PRESUMPTION
