"""The demo seed checks for a median table in force before it deletes anything (3a1 spec §3).

Business intent: the demo personas carry the partner demos and the E2E journeys. A reseed
that can't work their means tests out must leave the existing personas as they are and tell
the operator where to find how to load the missing table.

Every seeded persona answers 3e2's questions as the persona targets settle them (3e2 spec
section 11), so the demos and the journeys meet no gap, and no figure the means test reads
moves.
"""

import re
from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command

from apps.districts.models import MedianIncome
from apps.eligibility.cmi import is_above_median
from apps.eligibility.models import MeansTest
from apps.forms.registry import packet
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.intake.asset_lines import LINE_BY_KEY, ordered_assets, rows_on, shown_lines
from apps.intake.claims import claim_step_gaps
from apps.intake.management.commands.seed_demo_data import (
    PERSONAS,
    _andres_kettleby,
    asset_at,
    claim_links,
)
from apps.intake.models import (
    AssetInfo,
    FilingFee,
    IncomeInfo,
    IntakeSession,
    SpouseIncome,
)
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


MARIA_LINE_5 = (
    "I support two children on what I earn. After rent, food, the car and the children's "
    "costs, there is not enough left each month to pay the fee, even in parts."
)
SARAH_LINE_5 = (
    "I have no savings. My pay covers rent, food and my bus pass, and what is left each "
    "month goes to bills I already owe."
)
LINE_8 = {
    "maria": "waiver",
    "sarah": "waiver",
    "deshawn": "installments",
    "andres": "installments",
    "james": "pay_in_full",
    "priya": "pay_in_full",
}
PACKET_SIZE = {"maria": 15, "sarah": 15, "deshawn": 14, "andres": 14, "james": 14, "priya": 15}


EXPENSE_TOTAL = {
    "maria": "2600.00",
    "james": "3210.00",
    "priya": "7050.00",
    "deshawn": "2410.00",
    "sarah": "1280.00",
    "andres": "3034.00",
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
def test_the_seed_gives_each_persona_their_stored_answers(
    persona, marital_status, members, spouse_wages, county
):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, stdout=StringIO())
    session = IntakeSession.objects.get(user__username=f"demo_{persona}")

    # household, spouse income and county
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

    # each new income question
    filer_deductions, spouse_deductions = DEDUCTIONS[persona]
    filer = session.income_info
    rows = [(filer, filer_deductions)]
    if spouse_deductions is not None:
        rows.append((session.spouse_income, spouse_deductions))
    for row, deductions in rows:
        assert len(row.get_entries()) == (1 if persona == "andres" and row is filer else 0)
        assert row.income_now_different == "no"
        assert row.monthly_interest_and_dividends == Decimal("0.00")
        assert row.monthly_rental_income is None
        assert _deductions(row) == {k: Decimal(v) for k, v in deductions.items()}
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

    # the new answers move no means test or packet
    means_test = MeansTest.objects.get(session=session)
    assert means_test.calculated_cmi == Decimal(CMI[persona])
    assert is_above_median(means_test.calculated_cmi, means_test.median_income_threshold) is (
        persona == "priya"
    )
    forms = packet(session)
    assert ("form_122a2" in forms) is (persona == "priya")
    assert ("form_103b" in forms) is (persona in {"maria", "sarah"})

    # their own answer to how they will pay the fee
    fee = FilingFee.objects.get(session=session)
    line_5 = {"maria": MARIA_LINE_5, "sarah": SARAH_LINE_5}.get(persona)
    waiver = ("no", line_5, "no", "no") if line_5 else (None, "", None, None)
    assert (
        fee.payment_choice,
        fee.income_change_answer,
        fee.installments_explanation,
        fee.others_covered_answer,
        fee.expense_change_answer,
    ) == (LINE_8[persona], *waiver)
    assert (
        fee.income_change_explanation,
        fee.others_covered_who,
        fee.expense_change_explanation,
    ) == ("", "", "")

    # the sworn monthly total takes the 26 Schedule J lines
    assert Decimal(str(session.expense_info.calculate_total_monthly_expenses())) == Decimal(
        EXPENSE_TOTAL[persona]
    )


@pytest.mark.django_db
def test_103b_follows_each_personas_line_8_answer_so_only_deshawns_packet_shrinks():
    # One test over all six, so it fails first on DeShawn's 15 (a test per persona would
    # pass before the change for the five whose packets don't move).
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    packets = {}
    for persona in PACKET_SIZE:
        call_command("seed_demo_data", persona=persona, stdout=StringIO())
        forms = packet(IntakeSession.objects.get(user__username=f"demo_{persona}"))
        packets[persona] = (len(forms), "form_103b" in forms)
    assert packets == {
        persona: (size, LINE_8[persona] == "waiver") for persona, size in PACKET_SIZE.items()
    }


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
@pytest.mark.parametrize("persona", list(PERSONAS))
def test_every_seeded_persona_has_finished_the_walk(persona):
    # Complete refuses a shown Schedule A/B line with no answer, so a persona must hold one for
    # every line shown, and a Yes on exactly the lines where it holds a row.
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, stdout=StringIO())
    session = IntakeSession.objects.get(user__username=f"demo_{persona}")

    answers = session.asset_lines.get_answers()

    assert {line.key for line in shown_lines(answers)} == set(answers)
    yes = {key for key, value in answers.items() if value == "yes"}
    gates = yes & {"37", "46"}
    assert yes == {row.ab_line for row in session.assets.all()} | gates
    assert all(row.ab_line in LINE_BY_KEY for row in session.assets.all())
    # Andres drives for a living (37 Yes, 46 No); Sarah says no to every line.
    if persona == "andres":
        assert (answers["37"], answers["46"]) == ("yes", "no")
    if persona == "sarah":
        assert yes == set()


@pytest.mark.django_db
def test_a_leased_car_is_seeded_at_zero_not_blank():
    # Andres typed $0 and $0 for the Corolla he leases; blank would read as "unanswered".
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona="andres", stdout=StringIO())
    session = IntakeSession.objects.get(user__username="demo_andres")

    corolla = next(
        a for a in session.assets.all() if a.get_details().get("model") == "Corolla Hybrid"
    )

    assert (corolla.current_value, corolla.entire_value) == (Decimal("0.00"), Decimal("0.00"))


@pytest.mark.django_db
@pytest.mark.parametrize("persona", list(PERSONAS))
def test_a_seeded_row_uses_no_old_asset_type(persona):
    # Old asset_type is read-only and dropped later; a seeded row names its line instead.
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, stdout=StringIO())

    rows = AssetInfo.objects.filter(session__user__username=f"demo_{persona}")

    assert all(row.asset_type is None and row.ab_line for row in rows)


@pytest.mark.parametrize("persona", list(PERSONAS))
def test_a_persona_brief_gives_line_31_the_company_name_the_seed_prints(persona):
    # Line 31's text box is the form's "Company name". A persona working from a brief that names
    # only a type of policy types that into the box, and its form no longer matches the seed's.
    directory = settings.BASE_DIR.parent / "docs" / "testing" / "persona-briefs"
    if not directory.is_dir():
        pytest.skip("the repo's docs aren't here (compose's backend mounts backend/ only)")
    brief = next(directory.glob(f"{persona}-*.md")).read_text()

    seeded = [
        (row["description"], row["details"].get("beneficiary"), row["current_value"])
        for row in PERSONAS[persona]()["assets"]
        if row["ab_line"] == "31"
    ]

    told = [
        (company, beneficiary, Decimal(value))
        for company, beneficiary, value in re.findall(
            r"^- Line 31, company name: (.+?) \(.+?\)(?:, beneficiary: (.+?))? — \$(\d+)$",
            brief,
            flags=re.MULTILINE,
        )
    ]
    assert told == [(company, who or "", value) for company, who, value in seeded]
    assert len(told) == len(re.findall(r"^- Line 31\b", brief, flags=re.MULTILINE))


# ── 3c3: every persona answers the questions Schedules D, E/F, G and H ask ──────────────────


def _seed(persona):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, stdout=StringIO())
    return IntakeSession.objects.get(user__username=f"demo_{persona}")


def _debt(session, name):
    return next(d for d in session.debts.all() if d.creditor_name == name)


@pytest.mark.django_db
@pytest.mark.parametrize("persona", list(PERSONAS))
def test_every_persona_answers_every_claim_question(persona):
    # Seeded before 3c3, a persona is refused until it is re-seeded; seeded now, none is.
    session = _seed(persona)
    assert [str(gap) for gap in claim_step_gaps(session)] == []


@pytest.mark.django_db
def test_priyas_car_loan_links_to_her_car():
    session = _seed("priya")
    kestrel = _debt(session, "Kestrel Auto Finance")
    car = rows_on(ordered_assets(session), "3")[0]
    assert kestrel.secured_by_id == car.pk
    assert (kestrel.amount_owed, kestrel.monthly_payment) == (
        Decimal("14900.00"),
        Decimal("450.00"),
    )
    assert car.get_details()["model"] == "CR-V EX"
    assert session.debts.count() == 3


@pytest.mark.django_db
def test_deshawns_mortgage_links_to_the_home_he_lives_in_as_its_first_mortgage():
    session = _seed("deshawn")
    home = rows_on(ordered_assets(session), "1")[0]
    mortgage = _debt(session, "Harrowgate Home Loans")
    assert mortgage.secured_by_id == home.pk
    assert home.get_details()["lives_here"] == "yes"
    assert mortgage.home_payment_line == "first"


@pytest.mark.django_db
def test_andres_lease_picks_the_corolla_and_copperline_picks_the_fit():
    session = _seed("andres")
    cars = rows_on(ordered_assets(session), "3")
    lease = next(c for c in session.executory_contracts.all() if c.lease_kind == "vehicle")
    copperline = _debt(session, "Copperline Auto Finance")
    assert lease.vehicle_asset_id == cars[0].pk
    assert lease.monthly_payment == Decimal("389.00")
    assert cars[0].get_details()["model"] == "Corolla Hybrid"
    assert copperline.secured_by_id == cars[1].pk
    assert copperline.monthly_payment == Decimal("0.00")
    mateo = next(c for c in session.codebtors.all() if c.name == "Mateo Kettleby")
    assert mateo.get_links() == [{"kind": "debt", "id": copperline.pk}]


@pytest.mark.django_db
@pytest.mark.parametrize("persona", list(PERSONAS))
def test_each_personas_dates_fit_their_boxes(persona):
    # A date too long for its box is ValueTooLong on the form it prints on (S16). D prints only
    # a secured debt's date, in its 50 pt box; E/F prints the rest, in the narrowest of its boxes.
    for debt in PERSONAS[persona]()["debts"]:
        form, key = (
            ("schedule_d", "Date debt was incurred@1:T31")
            if debt.get("is_secured")
            else ("schedule_e_f", "Date debt was incurred@1:T14")
        )
        PDFFormFiller().check(form, {key: debt["date_incurred"]})  # raises ValueTooLong


@pytest.mark.django_db
def test_asset_at_and_claim_links_name_rows_by_position_and_by_name():
    session = _seed("andres")
    assert asset_at(session, "3.2").get_details()["model"] == "Fit"
    with pytest.raises(LookupError):
        asset_at(session, "3.9")
    copperline = _debt(session, "Copperline Auto Finance")
    assert claim_links(session, [("debt", "Copperline Auto Finance")]) == [
        {"kind": "debt", "id": copperline.pk}
    ]
    with pytest.raises(LookupError):
        claim_links(session, [("debt", "No Such Creditor")])
