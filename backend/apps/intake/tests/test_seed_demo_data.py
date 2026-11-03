"""The demo seed checks for a median table in force before it deletes anything (3a1 spec §3).

Business intent: the demo personas carry the partner demos and the E2E journeys. A reseed
that can't work their means tests out must leave the existing personas as they are and tell
the operator where to find how to load the missing table.

Every seeded persona answers 3e2's questions as the persona targets settle them (3e2 spec
section 11), so the demos and the journeys meet no gap, and no figure the means test reads
moves.
"""

from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from apps.districts.models import MedianIncome
from apps.eligibility.cmi import is_above_median
from apps.eligibility.models import MeansTest
from apps.forms.registry import packet
from apps.intake.management.commands.seed_demo_data import PERSONAS, _andres_kettleby
from apps.intake.models import FeeWaiverApplication, IncomeInfo, IntakeSession, SpouseIncome
from apps.users.models import User


@pytest.mark.django_db
def test_a_reseed_with_no_median_table_in_force_keeps_the_demo_personas_and_points_to_the_runbook():
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona="james", stdout=StringIO())
    james = User.objects.get(username="demo_james").pk
    MedianIncome.objects.all().delete()
    err = StringIO()

    call_command("seed_demo_data", "--reset", stdout=StringIO(), stderr=err)

    assert User.objects.get(username="demo_james").pk == james
    assert "docs/REFERENCE_TABLES.md" in err.getvalue()


def _row(id, relationship, age, lives_with_you, claimed_or_supported, **spouse):
    return {
        "id": id,
        "relationship": relationship,
        "age": age,
        "lives_with_you": lives_with_you,
        "claimed_or_supported": claimed_or_supported,
        **spouse,
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "persona, marital_status, members, spouse_wages, county",
    [
        (
            "maria",
            "not_married",
            [_row(1, "son", 8, True, True), _row(2, "daughter", 5, True, True)],
            None,
            "Cook",
        ),
        ("james", "not_married", [], None, "Cook"),
        (
            "priya",
            "married_together",
            [
                _row(1, "spouse", 45, True, True, spouse_is_dependent=False),
                _row(2, "daughter", 10, True, True),
                _row(3, "son", 7, True, True),
            ],
            "1800.00",
            "Cook",
        ),
        (
            "deshawn",
            "married_together",
            [_row(1, "spouse", 44, True, True, spouse_is_dependent=False)],
            "1000.00",
            "Cook",
        ),
        ("sarah", "not_married", [_row(1, "roommate", 29, True, False)], None, "Cook"),
        ("andres", "not_married", [_row(1, "daughter", 9, True, True)], None, "Kane"),
    ],
)
def test_the_seed_gives_each_persona_their_household_spouse_income_and_county(
    persona, marital_status, members, spouse_wages, county
):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, stdout=StringIO())
    session = IntakeSession.objects.get(user__username=f"demo_{persona}")

    assert session.income_info.marital_status == marital_status
    assert session.household.county == county
    assert session.household.get_members() == members
    if spouse_wages is None:
        assert not SpouseIncome.objects.filter(session=session).exists()
    else:  # the spouse's wages, and $0.00 typed in the other nine boxes (§11)
        assert {f: getattr(session.spouse_income, f) for f in SpouseIncome.SOURCE_FIELDS} == {
            **dict.fromkeys(SpouseIncome.SOURCE_FIELDS, Decimal("0.00")),
            "monthly_gross_wages": Decimal(spouse_wages),
        }


@pytest.mark.django_db
def test_the_seed_gives_the_fee_waiver_application_103b_line_1s_count(monkeypatch):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    for persona in ("maria", "deshawn", "sarah"):
        # Step 1's old Household Size box says 9, so the seed stores these sizes from the
        # household list, not from that box. (test_household_counts.py pins the counting rule.)
        data = PERSONAS[persona]()
        data["debtor"]["household_size"] = 9
        monkeypatch.setitem(PERSONAS, persona, lambda data=data: data)
        call_command("seed_demo_data", persona=persona, stdout=StringIO())

    assert {
        fw.session.user.username: fw.household_size for fw in FeeWaiverApplication.objects.all()
    } == {
        "demo_maria": 3,
        "demo_deshawn": 2,
        "demo_sarah": 1,
    }


DEDUCTION_FIELDS = IncomeInfo.DEDUCTION_FIELDS
DEDUCTIONS = {
    "maria": ({"payroll_tax": "400.00", **dict.fromkeys(DEDUCTION_FIELDS[1:], "0.00")}, None),
    "james": ({"payroll_tax": "1288.00", "payroll_union_dues": "45.00"}, None),
    "priya": (
        {
            "payroll_tax": "2450.00",
            "payroll_voluntary_retirement": "600.00",
            "payroll_insurance": "620.00",
        },
        {"payroll_tax": "250.00"},
    ),
    "deshawn": ({"payroll_tax": "450.00"}, {"payroll_tax": "115.00"}),
    "sarah": ({"payroll_tax": "250.00"}, None),
    "andres": ({}, None),
}
LINE_3 = {
    "maria": "no",
    "james": "no",
    "priya": "yes",
    "deshawn": "yes",
    "sarah": "no",
    "andres": "no",
}
CMI = {
    "maria": "3200.00",
    "james": "5833.00",
    "priya": "13800.00",
    "deshawn": "4500.00",
    "sarah": "2000.00",
    "andres": "3370.00",
}


def _deductions(row):
    return {f: getattr(row, f) for f in DEDUCTION_FIELDS if getattr(row, f) is not None}


@pytest.mark.django_db
@pytest.mark.parametrize("persona", list(DEDUCTIONS))
def test_every_seeded_persona_answers_each_new_income_question(persona):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, stdout=StringIO())
    session = IntakeSession.objects.get(user__username=f"demo_{persona}")
    filer_deductions, spouse_deductions = DEDUCTIONS[persona]
    filer_row = session.income_info
    rows = [(filer_row, filer_deductions)]
    if spouse_deductions is not None:
        rows.append((session.spouse_income, spouse_deductions))
    for row, deductions in rows:
        assert len(row.get_entries()) == (1 if persona == "andres" and row is filer_row else 0)
        assert row.income_now_different == "no"
        assert row.monthly_interest_and_dividends == Decimal("0.00")
        assert row.monthly_rental_income is None
        assert _deductions(row) == {k: Decimal(v) for k, v in deductions.items()}
    filer = session.income_info
    if persona == "maria":
        assert (
            filer.assistance_answer,
            filer.noncash_assistance_kind,
            filer.noncash_assistance_value,
            filer.cash_assistance_kind,
            filer.cash_assistance_amount,
        ) == ("yes", "SNAP (food stamps)", Decimal("350.00"), "", None)
    else:
        assert all(r.assistance_answer == "no" for r, _ in rows)
    assert session.expense_info.expenses_include_others == LINE_3[persona]
    assert filer.income_period_end == date(2026, 9, 30)


@pytest.mark.django_db
@pytest.mark.parametrize("persona", list(CMI))
def test_the_new_answers_move_no_seeded_personas_means_test_fee_flag_or_packet(persona):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, stdout=StringIO())
    session = IntakeSession.objects.get(user__username=f"demo_{persona}")
    means_test = MeansTest.objects.get(session=session)
    assert means_test.calculated_cmi == Decimal(CMI[persona])
    assert is_above_median(means_test.calculated_cmi, means_test.median_income_threshold) is (
        persona == "priya"
    )
    assert means_test.qualifies_for_fee_waiver is (
        persona in {"maria", "deshawn", "sarah", "andres"}
    )
    forms = packet(session)
    assert ("form_122a2" in forms) is (persona == "priya")
    assert ("form_103b" in forms) is (persona in {"maria", "deshawn", "sarah"})


@pytest.mark.django_db
def test_andres_is_seeded_with_his_driving_as_a_business():
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona="andres", stdout=StringIO())
    session = IntakeSession.objects.get(user__username="demo_andres")

    assert session.income_info.get_entries() == [
        {
            "id": 1,
            "kind": "business",
            "description": "Rideshare and delivery driving",
            "gross": "4200.00",
            "expenses": "830.00",
            "current_gross": None,
            "current_expenses": None,
        }
    ]
    assert session.income_info.monthly_other_income == Decimal("0.00")
    assert MeansTest.objects.get(session=session).calculated_cmi == Decimal("3370.00")


@pytest.mark.django_db
def test_a_gig_drivers_business_entry_leaves_his_debts_as_he_classed_them_and_he_reaches_his_forms():
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona="andres", stdout=StringIO())
    session = IntakeSession.objects.get(user__username="demo_andres")

    classed = list(
        session.debts.order_by("id").values_list("consumer_business_classification", flat=True)
    )

    assert classed == [d["consumer_business_classification"] for d in _andres_kettleby()["debts"]]
    assert classed.count("business") == 1
    assert len(packet(session)) == 14


@pytest.mark.django_db
@pytest.mark.parametrize(
    "persona,total",
    [
        ("maria", "2600.00"),
        ("james", "3210.00"),
        ("priya", "7050.00"),
        ("deshawn", "2410.00"),
        ("sarah", "1280.00"),
        ("andres", "3034.00"),
    ],
)
def test_each_personas_expense_total_takes_the_new_schedule_j_lines(persona, total):
    # The Expenses step asks 26 lines now; a persona's sworn monthly expenses are the sum.
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, stdout=StringIO())
    session = IntakeSession.objects.get(user__username=f"demo_{persona}")

    assert Decimal(str(session.expense_info.calculate_total_monthly_expenses())) == Decimal(total)
