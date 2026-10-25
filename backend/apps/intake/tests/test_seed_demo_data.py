"""The demo seed checks for a median table in force before it deletes anything (3a1 spec §3).

Business intent: the demo personas carry the partner demos and the E2E journeys. A reseed
that can't work their means tests out must leave the existing personas as they are and tell
the operator where to find how to load the missing table.
"""

from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from apps.districts.models import MedianIncome
from apps.intake.management.commands.seed_demo_data import PERSONAS
from apps.intake.models import FeeWaiverApplication, IntakeSession, SpouseIncome
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
