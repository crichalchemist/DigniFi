"""Form 122A-2 reads only what the filer gave DigniFi; whatever the page asks stays
unanswered until the filer answers it."""

import json
from dataclasses import fields, replace
from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.districts.means_standards import NoMeansTestTable
from apps.districts.models import District
from apps.eligibility.means_inputs import page_answers, read_inputs, read_tables
from apps.eligibility.means_lines import (
    PRESUMPTION,
    HealthInsurance,
    MeansTableKeyMissing,
    OptIn,
    debt_lines,
    work_out,
)
from apps.eligibility.tests.test_means_lines import PRIYA
from apps.intake.models import (
    DebtorInfo,
    IncomeInfo,
    IntakeSession,
    MeansTestAnswers,
    SecuredDebtAnswers,
)
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
    if f.name.startswith(("line_", "spouse_"))
    and f.name not in ("line_1", "line_35_past_due", "line_41a")
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


def test_a_session_that_never_saw_the_page_has_every_answer_unanswered(session):
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
        inputs.spouse_vehicles_answer,
        inputs.spouse_loans_answer,
    ) == (None, (), None, None, None, None, None, None, None)
    car = linked_row(session, "3", None, "Demo Car")
    linked_loan(session, car, "300")
    inputs = read_inputs(session)
    (vehicle,) = inputs.vehicles
    (debt,) = inputs.secured_debts
    assert vehicle.claimed is None
    assert (
        debt.payments_left,
        debt.payment_changes,
        debt.total_60_months,
        debt.taxes_or_insurance,
        debt.necessary_for_support,
        debt.cure,
    ) == (None,) * 6


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
    # Created in neither the order they must read in nor its reverse, and named with a lower
    # case and an accented first letter, so only the case- and accent-folded name order passes.
    other = IntakeSession.objects.create(user=session.user, district=session.district)
    foreign = linked_row(other, "3", None, "Foreign Car")
    rental_loan = linked_loan(session, elsewhere, "200", creditor_name="C Rental Bank")
    linked_loan(session, car, "50", creditor_name="E Draft", is_draft=True)
    home_loan = linked_loan(session, home, "800", creditor_name="Á Home Bank")
    stray_loan = linked_loan(session, foreign, "75", creditor_name="F Stray Bank")
    complete_debt(session, creditor_name="D Not Secured", secured_by=car)
    car_loan = linked_loan(session, car, "300", creditor_name="b Car Bank")
    got = {d.ref: d for d in read_inputs(session).secured_debts}
    assert [d.creditor for d in read_inputs(session).secured_debts] == [
        "Á Home Bank",
        "b Car Bank",
        "C Rental Bank",
        "F Stray Bank",
    ]
    home_debt = got[f"debt-{home_loan.pk}"]
    assert (home_debt.secured_by, home_debt.on_home, home_debt.property) == (
        f"asset-{home.pk}",
        True,
        "Demo Home",
    )
    car_debt = got[f"debt-{car_loan.pk}"]
    assert (car_debt.secured_by, car_debt.on_home) == (f"asset-{car.pk}", False)
    assert got[f"debt-{rental_loan.pk}"].on_home is False
    assert car_debt.monthly_payment == Decimal("300.00")
    stray_debt = got[f"debt-{stray_loan.pk}"]
    assert (stray_debt.secured_by, stray_debt.on_home, stray_debt.property) == (None, False, "")


def test_vehicles_are_line_3_rows_and_line_4_rows_not_lived_in_with_their_loans_and_leases(
    session,
):
    # A line 4 row comes first and another last, around the line 3 car, so neither queryset
    # order nor its reverse reads the rows in A/B order.
    trailer = linked_row(session, "4", "no", "Demo Trailer")
    linked_lease(session, trailer, "200")
    car = linked_row(session, "3", None, "")
    car.description = ""
    car.set_details({"make": "Demo", "model": "Hatch", "year": "2019", "lives_here": None})
    car.save()
    linked_loan(session, car, "300")
    # "Do you live here?" unanswered and nothing linked, so no Assets gap: Schedule J's line 17
    # set counts it, and so does line 11 (spec H24)
    camper = linked_row(session, "4", None, "Demo Camper")
    linked_row(session, "4", "yes", "Demo Home On Wheels")
    inputs = read_inputs(session)
    first, second, third = inputs.vehicles
    named = {debt.secured_by for debt in inputs.secured_debts}
    assert (first.ref, first.name, first.ref in named, first.leased) == (
        f"asset-{car.pk}",
        "Demo Hatch 2019",
        True,
        False,
    )
    assert (second.ref, second.name, second.ref in named, second.leased) == (
        f"asset-{trailer.pk}",
        "Demo Trailer",
        False,
        True,
    )
    assert (third.ref, third.name, third.ref in named, third.leased) == (
        f"asset-{camper.pk}",
        "Demo Camper",
        False,
        False,
    )


def test_a_vehicle_is_financed_or_leased_only_by_a_counted_loan_or_a_vehicle_lease(session):
    stale_lease = linked_row(session, "3", None, "Demo Stale Lease Car")
    linked_lease(session, stale_lease, "200", lease_kind="residential")
    other_contract = linked_row(session, "3", None, "Demo Contract Car")
    linked_lease(session, other_contract, "200", contract_type="contract")
    not_counted = linked_row(session, "3", None, "Demo Uncounted Loan Car")
    complete_debt(session, creditor_name="Not Secured", secured_by=not_counted)
    linked_loan(session, not_counted, "50", creditor_name="Draft", is_draft=True)
    inputs = read_inputs(session)
    named = {debt.secured_by for debt in inputs.secured_debts}
    got = {v.ref: (v.ref in named, v.leased) for v in inputs.vehicles}
    assert got == {
        f"asset-{stale_lease.pk}": (False, False),
        f"asset-{other_contract.pk}": (False, False),
        f"asset-{not_counted.pk}": (False, False),
    }


def test_a_loan_on_a_motor_home_the_filer_lives_in_is_on_the_home(session):
    motor_home = linked_row(session, "4", "yes", "Demo Motor Home")
    loan = linked_loan(session, motor_home, "400", creditor_name="G Motor Bank")
    (debt,) = read_inputs(session).secured_debts
    assert (debt.ref, debt.secured_by, debt.on_home, debt.property) == (
        f"debt-{loan.pk}",
        f"asset-{motor_home.pk}",
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
    assert (
        tables.public_transport,
        tables.national_extra,
        tables.health_65_or_older,
        tables.presumption_low,
        tables.presumption_high,
    ) == (
        Decimal("220.00"),
        Decimal("397.00"),
        Decimal("163.00"),
        Decimal("10275.00"),
        Decimal("17150.00"),
    )
    # By value, Decimal("220") equals Decimal("220.00"); the form prints cents
    compared = (
        *tables.housing["Cook"][3],
        *tables.operating["chicago"],
        tables.ownership_one_car,
        tables.public_transport,
        tables.national_extra,
        tables.health_65_or_older,
        tables.presumption_low,
        tables.presumption_high,
    )
    assert all(figure.as_tuple().exponent == -2 for figure in compared)
    assert tables.five_percent == (
        Decimal("30.00"),
        Decimal("53.00"),
        Decimal("64.00"),
        Decimal("76.00"),
    )
    assert (
        tables.five_percent_extra,
        tables.education_per_child,
        tables.chapter_13_unsecured_limit,
        tables.chapter_13_secured_limit,
    ) == (Decimal("14.00"), Decimal("214.58"), Decimal("526700.00"), Decimal("1580125.00"))
    assert used[0] == {
        "name": "IRS expense standards",
        "effective_date": "2026-07-15",
        "valid_through": None,
        "source_url": "https://www.justice.gov/ust/means-testing/20260715",
    }
    assert used[1] == {
        "name": "Bankruptcy Code dollar amounts",
        "effective_date": "2025-04-01",
        "valid_through": "2028-03-31",
        "source_url": (
            "https://www.federalregister.gov/documents/2025/02/04/2025-02207/"
            "adjustment-of-certain-dollar-amounts-applicable-to-bankruptcy-cases"
        ),
    }
    assert len(used) == 2


def test_read_tables_refuses_before_july_15_2026(means_standards_2026, section_104_2025):
    with pytest.raises(NoMeansTestTable):
        read_tables(date(2026, 7, 14))


@pytest.mark.parametrize(
    "lookup, part",
    [
        ({"kind": "national", "size": 4}, "national"),
        ({"kind": "national_extra"}, "national"),
        ({"kind": "health", "key": "under_65"}, "health"),
        ({"kind": "housing_mortgage", "key": "Cook", "size": 5}, "housing"),
        ({"kind": "operating", "key": "chicago", "size": 2}, "transport"),
        ({"kind": "ownership"}, "transport"),
        ({"kind": "public_transport"}, "public_transport"),
    ],
)
def test_a_figure_the_set_lacks_raises_naming_only_its_table_part(
    means_standards_2026, section_104_2025, lookup, part
):
    assert means_standards_2026.figures.filter(**lookup).delete()[0] >= 1
    with pytest.raises(MeansTableKeyMissing) as refused:
        read_tables()
    assert str(refused.value) == f"The means test tables have no {part} figure for this session."


def test_a_set_without_the_five_percent_chart_raises_naming_only_that_part(
    means_standards_2026, section_104_2025
):
    assert means_standards_2026.figures.filter(kind="five_percent").delete()[0] >= 1
    with pytest.raises(MeansTableKeyMissing) as refused:
        read_tables()
    assert (
        str(refused.value) == "The means test tables have no five_percent figure for this session."
    )


def _store(session, answers):
    MeansTestAnswers.objects.create(session=session, answers=json.dumps(answers))
    return IntakeSession.objects.get(pk=session.pk)


def _married(session):
    answer_household(
        session,
        marital_status="married_together",
        members=[ROOMMATE],
        spouse_income={"monthly_gross_wages": Decimal("1000.00")},
    )
    return IntakeSession.objects.get(pk=session.pk)


SPOUSE_CAR = {"ref": "spouse-1", "description": "Demo Spouse Car", "leased": "no", "claimed": "yes"}


def _spouse_loan(**over):
    return {
        "ref": "spouse-1",
        "on_amounts_owed": "no",
        "debt": None,
        "creditor": "Demo Spouse Bank",
        "secured_by": "home",
        "property": "",
        "payment": "250.00",
        "payments_left": "12",
        "payment_changes": "no",
        "total_60_months": None,
        "taxes_or_insurance": "no",
        "necessary_for_support": "no",
        "cure": "0.00",
    } | over


def test_the_stored_answers_reach_the_calculator(session):
    car = linked_row(session, "3", None, "Demo Car")
    loan = linked_loan(session, car, "300")
    SecuredDebtAnswers.objects.create(debt=loan, payments_left="60_or_more", payment_changes="no")
    session = _store(
        session,
        {
            "line_16": "2300.00",
            "line_25_answer": "yes",
            "line_25_health": "10.00",
            "line_25_disability": "20.00",
            "line_25_hsa": "30.00",
            "line_25_spends": "no",
            "line_31_answer": "yes",
            "line_31_amount": "50.00",
            "line_3_rows": [{"amount": "0.00"}],
            "vehicle_claims": {f"asset-{car.pk}": "yes"},
        },
    )
    inputs = read_inputs(session)
    assert inputs.line_16 == Decimal("2300.00")
    assert inputs.line_25 == HealthInsurance(
        "yes",
        health=Decimal("10.00"),
        disability=Decimal("20.00"),
        hsa=Decimal("30.00"),
        actually_spends="no",
        actual=None,
    )
    assert inputs.line_31 == OptIn("yes", Decimal("50.00"))
    assert inputs.line_3_rows == (("", Decimal("0.00")),)
    assert inputs.vehicles[0].claimed is True
    assert inputs.secured_debts[0].payments_left == 60
    assert inputs.secured_debts[0].payment_changes == "no"


def test_the_spouses_rows_join_the_vehicles_and_debts_only_under_married_together(session):
    car = linked_row(session, "3", None, "Demo Car")
    linked_loan(session, car, "300", creditor_name="Demo Car Bank")
    stored = {
        "spouse_vehicles_answer": "yes",
        "spouse_vehicles": [SPOUSE_CAR],
        "spouse_loans_answer": "yes",
        "spouse_loans": [_spouse_loan()],
    }
    session = _store(session, stored)
    alone = read_inputs(session)
    assert (alone.spouse_vehicles_answer, alone.spouse_loans_answer) == (None, None)
    assert len(alone.vehicles) == 1 and len(alone.secured_debts) == 1
    session = _married(session)
    got = read_inputs(session)
    assert (got.spouse_vehicles_answer, got.spouse_loans_answer) == ("yes", "yes")
    assert [v.ref for v in got.vehicles] == [f"asset-{car.pk}", "spouse-1"]
    spouse_vehicle = got.vehicles[1]
    assert (spouse_vehicle.name, spouse_vehicle.leased, spouse_vehicle.claimed) == (
        "Demo Spouse Car",
        False,
        True,
    )
    loan = got.secured_debts[1]
    assert (loan.ref, loan.creditor, loan.secured_by, loan.on_home, loan.placed) == (
        "spouse-1",
        "Demo Spouse Bank",
        None,
        True,
        True,
    )
    assert (loan.monthly_payment, loan.payments_left, loan.cure) == (
        Decimal("250.00"),
        12,
        Decimal("0.00"),
    )
    assert debt_lines(got)[loan.ref] == "9b"


def test_the_spouses_rows_are_read_only_under_their_own_yes(session):
    stored = {
        "spouse_vehicles_answer": "no",
        "spouse_vehicles": [SPOUSE_CAR],
        "spouse_loans_answer": "no",
        "spouse_loans": [_spouse_loan()],
    }
    session = _married(_store(session, stored))
    got = read_inputs(session)
    assert (got.spouse_vehicles_answer, got.spouse_loans_answer) == ("no", "no")
    assert (got.vehicles, got.secured_debts) == ((), ())
    assert page_answers(session)["spouse_loans"][0]["ref"] == "spouse-1"


def test_payments_left_reads_60_or_more_as_60_and_a_count_as_its_number(session):
    home = linked_row(session, "1", "yes", "Demo Home")
    more = linked_loan(session, home, "100", creditor_name="A Bank")
    few = linked_loan(session, home, "100", creditor_name="B Bank")
    none = linked_loan(session, home, "100", creditor_name="C Bank")
    SecuredDebtAnswers.objects.create(debt=more, payments_left="60_or_more")
    SecuredDebtAnswers.objects.create(debt=few, payments_left="0")
    session = IntakeSession.objects.get(pk=session.pk)
    got = {d.ref: d.payments_left for d in read_inputs(session).secured_debts}
    assert got == {f"debt-{more.pk}": 60, f"debt-{few.pk}": 0, f"debt-{none.pk}": None}


def test_a_joint_loan_on_the_spouses_car_counts(session):
    joint = complete_debt(session, creditor_name="Demo Joint Bank", amount_owed=Decimal("5000.00"))
    stored = {
        "spouse_vehicles_answer": "yes",
        "spouse_vehicles": [SPOUSE_CAR],
        "spouse_loans_answer": "yes",
        "spouse_loans": [_spouse_loan(on_amounts_owed="yes", debt=joint.pk, secured_by="spouse-1")],
    }
    session = _married(_store(session, stored))
    got = read_inputs(session)
    (loan,) = got.secured_debts
    assert (loan.creditor, loan.secured_by, loan.property, loan.placed) == (
        "Demo Joint Bank",
        "spouse-1",
        "Demo Spouse Car",
        True,
    )
    assert debt_lines(got)[loan.ref] == "13b"
    assert got.line_41a == Decimal("5000.00")
    joint.is_secured = True
    joint.save()
    again = read_inputs(IntakeSession.objects.get(pk=session.pk))
    assert [d.placed for d in again.secured_debts if d.ref == "spouse-1"] == [False]


def test_every_stored_answer_reaches_its_own_line_so_no_key_is_swapped_or_dropped(session):
    # A line read from another line's key, or left unread, moves line 39d without a gap to clear.
    car = linked_row(session, "3", None, "Demo Car")
    filer_loan = linked_loan(session, car, "300", creditor_name="Demo Car Bank")
    SecuredDebtAnswers.objects.create(
        debt=filer_loan,
        payments_left="7",
        payment_changes="pc-filer",
        total_60_months=Decimal("11.11"),
        taxes_or_insurance="tx-filer",
        necessary_for_support="nf-filer",
        cure=Decimal("12.12"),
    )
    stored = {
        "line_3_answer": "a3",
        "spouse_vehicles_answer": "yes",
        "spouse_vehicles": [SPOUSE_CAR],
        "spouse_loans_answer": "yes",
        "spouse_loans": [
            _spouse_loan(
                payments_left="9",
                payment_changes="pc-spouse",
                total_60_months="21.21",
                taxes_or_insurance="tx-spouse",
                necessary_for_support="nf-spouse",
                cure="22.22",
            )
        ],
        "line_34_answer": "a34",
        "line_36_answer": "a36",
        "line_36_payment": "36.36",
        "line_43_answer": "a43",
        "line_16": "16.16",
        "line_17": "17.17",
        "line_18": "18.18",
        "line_19": "19.19",
        "line_20": "20.20",
        "line_21": "21.21",
        "line_23": "23.23",
        "line_25_answer": "a25",
        "line_25_health": "25.01",
        "line_25_disability": "25.02",
        "line_25_hsa": "25.03",
        "line_25_spends": "s25",
        "line_25_actual": "25.05",
    }
    for n in (15, 22, 26, 27, 28, 29, 30, 31):
        stored[f"line_{n}_answer"] = f"a{n}"
        stored[f"line_{n}_amount"] = f"{n}.{n}"
    got = read_inputs(_married(_store(session, stored)))
    assert got.line_3_answer == "a3"
    assert (got.line_34_answer, got.line_36_answer, got.line_43_answer) == ("a34", "a36", "a43")
    assert got.line_36_payment == Decimal("36.36")
    for n in (16, 17, 18, 19, 20, 21, 23):
        assert getattr(got, f"line_{n}") == Decimal(f"{n}.{n}")
    assert got.line_25 == HealthInsurance(
        "a25",
        health=Decimal("25.01"),
        disability=Decimal("25.02"),
        hsa=Decimal("25.03"),
        actually_spends="s25",
        actual=Decimal("25.05"),
    )
    for n in (15, 22, 26, 27, 28, 29, 30, 31):
        assert getattr(got, f"line_{n}") == OptIn(f"a{n}", Decimal(f"{n}.{n}"))
    filer, spouse = got.secured_debts
    assert (
        filer.payments_left,
        filer.payment_changes,
        filer.total_60_months,
        filer.taxes_or_insurance,
        filer.necessary_for_support,
        filer.cure,
    ) == (7, "pc-filer", Decimal("11.11"), "tx-filer", "nf-filer", Decimal("12.12"))
    assert (
        spouse.payments_left,
        spouse.payment_changes,
        spouse.total_60_months,
        spouse.taxes_or_insurance,
        spouse.necessary_for_support,
        spouse.cure,
    ) == (9, "pc-spouse", Decimal("21.21"), "tx-spouse", "nf-spouse", Decimal("22.22"))


def test_a_reference_to_a_row_that_has_gone_reads_as_unanswered(session):
    car = linked_row(session, "3", None, "Demo Car")
    other = linked_row(session, "3", None, "Demo Other Car")
    joint = complete_debt(session, creditor_name="Demo Joint Bank")
    stored = {
        "spouse_vehicles_answer": "yes",
        "spouse_vehicles": [SPOUSE_CAR],
        "spouse_loans_answer": "yes",
        "spouse_loans": [
            _spouse_loan(on_amounts_owed="yes", debt=joint.pk, secured_by="spouse-1"),
            _spouse_loan(ref="spouse-2", secured_by=f"asset-{car.pk}"),
        ],
        "vehicle_claims": {f"asset-{car.pk}": "yes", f"asset-{other.pk}": "yes"},
        "vehicle_choice": [f"asset-{car.pk}", f"asset-{other.pk}"],
    }
    session = _married(_store(session, stored))
    before = read_inputs(session)
    assert before.vehicle_choice == (f"asset-{car.pk}", f"asset-{other.pk}")
    assert [d.placed for d in before.secured_debts] == [True, True]
    car.delete()
    after = read_inputs(IntakeSession.objects.get(pk=session.pk))
    assert after.vehicle_choice is None
    assert [v.ref for v in after.vehicles] == [f"asset-{other.pk}", "spouse-1"]
    assert [d.placed for d in after.secured_debts] == [True, False]
    joint.is_secured = True
    joint.save()
    last_session = IntakeSession.objects.get(pk=session.pk)
    last = read_inputs(last_session)
    assert [d.placed for d in last.secured_debts if d.ref == "spouse-1"] == [False]
    # what the page is given reads the debt as unanswered too, so a save sends back a null
    assert page_answers(last_session)["spouse_loans"][0]["debt"] is None


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
        car.ref == kestrel.secured_by,
        kestrel.creditor,
        kestrel.secured_by,
        kestrel.monthly_payment,
    ) == (
        "Honda CR-V EX 2021",
        True,
        "Kestrel Auto Finance",
        car.ref,
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
