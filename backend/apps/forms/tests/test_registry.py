"""
The packet holds exactly the forms a single Chapter 7 filer needs (spec §5.6, §5.7).

applies() decides which forms are in the packet; requires() stops a form from
filling silently when data it needs is missing.
"""

import re
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.districts.models import District
from apps.eligibility.models import MeansTest
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.forms.field_index import load_index
from apps.forms.models import GeneratedForm
from apps.forms.registry import (
    FORM_101A_LANDLORD,
    FORM_REGISTRY,
    PreconditionMissing,
    _needs_supp_answers,
    _supp_applies,
    build_field_values,
    build_parts,
    get_all_form_types,
    packet,
)
from apps.forms.schema import load_schema
from apps.intake.models import DebtorInfo, FilingFee, Household, IncomeInfo, IntakeSession
from apps.intake.petition import DETAIL_DUTY_RELEASED
from apps.intake.tests.builders import answer_household, answer_petition

User = get_user_model()

ALWAYS = [
    "form_101",
    "form_106dec",
    "form_106sum",
    "form_107",
    "form_121",
    "list_of_creditors",
    "form_122a1",
    "schedule_a_b",
    "schedule_c",
    "schedule_d",
    "schedule_e_f",
    "schedule_g",
    "schedule_h",
    "schedule_i",
    "schedule_j",
]


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        court_name="U.S. Bankruptcy Court, N.D. Ill.",
        state="IL",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def _debtor(session, ssn="900-55-0005"):
    return DebtorInfo.objects.create(
        session=session,
        first_name="Sarah",
        last_name="Chen",
        ssn=ssn,
        date_of_birth=date(1995, 1, 20),
        street_address="1520 N Damen Ave Apt 2F",
        city="Chicago",
        state="IL",
        zip_code="60622",
    )


def _means_test(session, monthly_cmi, annual_median, above_median_flag=False):
    return MeansTest.objects.create(
        session=session,
        district=session.district,
        calculated_cmi=Decimal(monthly_cmi),
        median_income_threshold=Decimal(annual_median),
        passes_means_test=Decimal(monthly_cmi) * 12 <= Decimal(annual_median),
        above_median_calculated=above_median_flag,
    )


def test_registry_is_the_chapter_7_forms_in_filing_order():
    assert get_all_form_types() == [
        "form_101",
        "form_101a",
        "form_103b",
        "form_106dec",
        "form_106sum",
        "form_107",
        "form_121",
        "list_of_creditors",
        "form_122a1",
        "form_122a1_supp",
        "form_122a2",
        "schedule_a_b",
        "schedule_c",
        "schedule_d",
        "schedule_e_f",
        "schedule_g",
        "schedule_h",
        "schedule_i",
        "schedule_j",
    ]


def test_chapter_11_means_test_is_not_offered():
    # Form 122B is the Chapter 11 statement, and its download raised a 500 (DIG-125).
    assert "form_122b" not in FORM_REGISTRY
    assert "form_122b" not in dict(GeneratedForm.FORM_TYPE_CHOICES)


def test_every_registered_form_can_be_stored():
    assert set(get_all_form_types()) <= set(dict(GeneratedForm.FORM_TYPE_CHOICES))


def test_below_median_filer_without_fee_waiver_gets_fifteen_forms(session):
    _means_test(session, "2000.00", "71304.00")
    assert packet(session) == ALWAYS


@pytest.mark.parametrize(
    "monthly_cmi,annual_median,applies",
    [
        ("11197.17", "134366.00", True),  # 134366.04 a year
        ("11197.16", "134366.00", False),  # 134365.92 a year
        ("5942.00", "71304.00", False),  # exactly the median, which counts as below (DIG-136)
    ],
)
def test_122a2_applies_only_above_the_median(session, monthly_cmi, annual_median, applies):
    _means_test(session, monthly_cmi, annual_median)
    assert ("form_122a2" in packet(session)) is applies


def test_122a2_ignores_the_sticky_above_median_flag(session):
    # A row calculated before DIG-128 was fixed can still carry above_median_calculated.
    _means_test(session, "2000.00", "71304.00", above_median_flag=True)
    assert "form_122a2" not in packet(session)


def test_no_means_test_means_no_122a2(session):
    assert "form_122a2" not in packet(session)


def test_122a1_supplement_waits_for_its_questions(session):
    # Nothing collects a claimed exemption from the presumption until step 4.
    _means_test(session, "12000.00", "134366.00")
    assert "form_122a1_supp" not in packet(session)


@pytest.mark.parametrize(
    "outcome,applies",
    [
        ("not_consumer", True),
        ("veteran_exemption", True),
        ("military_exclusion", True),
        ("at_or_below_median", False),
        ("presumption", False),
        (None, False),
    ],
)
def test_supp_applies_reads_the_stored_outcome(session, outcome, applies):
    # The Supp takes 122A-2's place exactly when the stored means test routed the filer to one
    # of its three outcomes (R-ROUTE); a row saved before 3h1 (no outcome) routes as before.
    means_test = _means_test(session, "12000.00", "134366.00")
    means_test.outcome = outcome
    means_test.save()

    assert _supp_applies(IntakeSession.objects.get(pk=session.pk)) is applies


def test_supp_applies_needs_a_means_test(session):
    assert _supp_applies(session) is False


def test_the_supp_refuses_its_first_open_question_on_the_amounts_owed_step(session):
    # A category-2 claim with no release date: the Supp would print a claim the filer can't date,
    # so it refuses in the gap's own words and links to Amounts Owed.
    answer_petition(
        session,
        debt_nature="consumer",
        disabled_veteran="no",
        reservist="yes",
        called_to_duty="yes",
        duty_category="2",
    )

    with pytest.raises(PreconditionMissing) as refused:
        _needs_supp_answers(session)

    assert (str(refused.value), refused.value.step, refused.value.page) == (
        DETAIL_DUTY_RELEASED,
        "debts",
        None,
    )

    answer_petition(session, duty_released_on="03/14/2026")
    assert _needs_supp_answers(session) is None


def _supp_session(wages, debt_nature):
    """A session the means test can work out, with income of `wages` a month (test_means_outcome's
    shape) and the given Amounts Owed answers."""
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    user = User.objects.create_user(username=f"supp{wages}", password="pw")
    session = IntakeSession.objects.create(user=user, district=District.objects.get(code="ilnd"))
    IncomeInfo.objects.create(
        session=session,
        **{
            **dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00")),
            "monthly_gross_wages": Decimal(wages),
        },
    )
    answer_household(session, debt_nature=debt_nature)
    _debtor(session)
    return IntakeSession.objects.get(pk=session.pk)


@pytest.mark.parametrize(
    "wages,outcome",
    [("9000.00", "cannot_work_out"), ("3000.00", "at_or_below_median")],
)
def test_a_line_3_claim_with_line_2_open_keeps_the_supp_out(db, wages, outcome):
    # R-D2's boundary (F2): line 2 Yes with its follow-up open still reaches line 3, but the form
    # takes line 2 first, so a whole line 3 claim can't route to box 3 while line 2 is open.
    answers = {
        "debt_nature": "consumer",
        "disabled_veteran": "yes",
        "reservist": "yes",
        "called_to_duty": "yes",
        "duty_category": "3",
    }
    session = _supp_session(wages, answers)
    assert "debts_on_duty" not in session.petition_answers.get_answers()

    MeansTestCalculator(session).calculate()

    session = IntakeSession.objects.get(pk=session.pk)
    assert session.means_test.outcome == outcome
    assert _supp_applies(session) is False


def test_petition_needs_the_filers_name_and_address(session):
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_101", session)
    # The sentence and the step that fixes it, as Complete shows them (3a1 spec §4.2).
    assert (str(refused.value), refused.value.step) == (
        "Enter your name and address on the Your Information step.",
        "debtor_info",
    )


@pytest.mark.parametrize("ssn", ["", "1234", "900-55-000"])
def test_ssn_statement_needs_a_nine_digit_ssn(session, ssn):
    _debtor(session, ssn=ssn)
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_121", session)
    assert (str(refused.value), refused.value.step) == (
        "Enter your 9-digit Social Security number on the Your Information step.",
        "debtor_info",
    )


@pytest.mark.parametrize("ssn", ["900-55-0005", "900550005"])
def test_ssn_statement_accepts_either_ssn_format(session, ssn):
    _debtor(session, ssn=ssn)
    assert build_field_values("form_121", session)


def test_means_test_form_needs_the_income_test_worked_out(session):
    _debtor(session)
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_122a1", session)
    assert (str(refused.value), refused.value.step) == (
        "Press Complete on the Review & Results step to work out your income test.",
        "review",
    )


def test_field_values_name_index_widgets(session):
    _debtor(session)
    Household.objects.create(session=session, county="Cook")
    FilingFee.objects.create(session=session, payment_choice="pay_in_full")
    values = build_field_values("form_101", session)
    widgets = load_index(load_schema("form_101").template_filename)
    assert values["First name"] == "Sarah"
    # A tagged key reads `<full name>@<page>:<tag>`; its name is the index's.
    assert {key.split("@")[0] for key in values} <= set(widgets)


@pytest.mark.parametrize("ssn", ["900-55-0005", "900550005"])
def test_petition_prints_only_the_last_four_ssn_digits(session, ssn):
    # The petition is public; only Form 121, which is not, carries the full number.
    _debtor(session, ssn=ssn)
    Household.objects.create(session=session, county="Cook")
    FilingFee.objects.create(session=session, payment_choice="pay_in_full")
    values = build_field_values("form_101", session)
    digits = [values["xx"], values["undefined"], values["undefined_2"], values["undefined_3"]]
    assert digits == ["0", "0", "0", "5"]
    leaks = [name for name, value in values.items() if "900550005" in re.sub(r"\D", "", value)]
    assert leaks == []


LANDLORD = {
    "landlord_name": "Demo Property Holdings LLC",
    "landlord_street": "100 Demo St",
    "landlord_city": "Chicago",
    "landlord_state": "IL",
    "landlord_zip": "60601",
}


def _evicted(session, **over):
    answer_petition(session, rents_residence="yes", eviction_judgment="yes", **over)


def test_a_renter_with_an_eviction_judgment_gets_form_101a_after_form_101(session):
    _evicted(session)
    forms = packet(session)
    assert forms[:2] == ["form_101", "form_101a"]
    assert len(forms) == 16


def test_a_stale_eviction_yes_under_a_rent_no_gets_no_form_101a(session):
    # Moving the rent answer to No keeps the eviction Yes stored (S:316).
    answer_petition(session, rents_residence="no", eviction_judgment="yes")
    assert "form_101a" not in packet(session)


def test_eviction_yes_with_rent_unanswered_gets_no_form_101a(session):
    answer_petition(session, rents_residence=None, eviction_judgment="yes")
    assert "form_101a" not in packet(session)


def test_a_session_with_no_petition_record_gets_no_form_101a_and_no_error(session):
    assert not hasattr(session, "petition_answers")
    assert FORM_REGISTRY["form_101a"].applies(session) is False


@pytest.mark.parametrize("key", list(LANDLORD))
def test_form_101a_refuses_until_the_landlord_block_is_whole(session, key):
    _debtor(session)
    _evicted(session, **{**LANDLORD, key: "  "})
    with pytest.raises(PreconditionMissing) as refused:
        build_parts("form_101a", session)
    assert refused.value.step == "contracts"
    assert str(refused.value) == (
        "Form 101A asks for your landlord's name and address, on Contracts & Leases."
    )
    assert str(refused.value) == FORM_101A_LANDLORD


def test_form_101a_builds_once_the_landlord_block_is_whole(session):
    _debtor(session)
    _evicted(session, **LANDLORD)
    (form_part,) = [p for p in build_parts("form_101a", session)["parts"] if p["kind"] == "form"]
    values = form_part["values"]
    assert values["Name of landlord"] == LANDLORD["landlord_name"]
    assert values["Landlord Street address"] == LANDLORD["landlord_street"]
    assert values["Landlord City"] == LANDLORD["landlord_city"]
    assert values["Landlord State"] == LANDLORD["landlord_state"]
    assert values["Landlord ZIP Code_5"] == LANDLORD["landlord_zip"]


def test_form_101a_never_refuses_off_the_pair(session):
    _debtor(session)
    answer_petition(session, rents_residence="no", eviction_judgment="yes")
    assert build_parts("form_101a", session)
