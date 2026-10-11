"""
The packet holds exactly the forms a single Chapter 7 filer needs (spec §5.6, §5.7).

applies() decides which forms are in the packet; requires() stops a form from
filling silently when data it needs is missing.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.models import MeansTest
from apps.forms.field_index import load_index
from apps.forms.models import GeneratedForm
from apps.forms.registry import (
    FORM_REGISTRY,
    PreconditionMissing,
    build_field_values,
    get_all_form_types,
    packet,
)
from apps.forms.schema import load_schema
from apps.intake.models import DebtorInfo, FeeWaiverApplication, IntakeSession

User = get_user_model()

ALWAYS = [
    "form_101",
    "form_106dec",
    "form_106sum",
    "form_107",
    "form_121",
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
        passes_means_test=Decimal(monthly_cmi) * 12 < Decimal(annual_median),
        above_median_calculated=above_median_flag,
    )


def test_registry_is_the_chapter_7_forms_in_filing_order():
    assert get_all_form_types() == [
        "form_101",
        "form_103b",
        "form_106dec",
        "form_106sum",
        "form_107",
        "form_121",
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


def test_below_median_filer_without_fee_waiver_gets_fourteen_forms(session):
    _means_test(session, "2000.00", "71304.00")
    assert packet(session) == ALWAYS


def test_fee_waiver_application_adds_form_103b(session):
    FeeWaiverApplication.objects.create(
        session=session,
        household_size=1,
        monthly_income=Decimal("1500.00"),
        monthly_expenses=Decimal("1400.00"),
        cannot_pay_full=True,
        cannot_pay_installments=True,
    )
    assert "form_103b" in packet(session)


@pytest.mark.parametrize(
    "monthly_cmi,applies",
    [("11197.17", True), ("11197.16", False)],  # 134366.04 and 134365.92 a year
)
def test_122a2_applies_at_or_above_the_median(session, monthly_cmi, applies):
    _means_test(session, monthly_cmi, "134366.00")
    assert ("form_122a2" in packet(session)) is applies


def test_122a2_ignores_the_sticky_above_median_flag(session):
    # calculate() sets above_median_calculated and never clears it (DIG-128).
    _means_test(session, "2000.00", "71304.00", above_median_flag=True)
    assert "form_122a2" not in packet(session)


def test_no_means_test_means_no_122a2(session):
    assert "form_122a2" not in packet(session)


def test_122a1_supplement_waits_for_its_questions(session):
    # Nothing collects a claimed exemption from the presumption until step 4.
    _means_test(session, "12000.00", "134366.00")
    assert "form_122a1_supp" not in packet(session)


def test_petition_needs_the_filers_name_and_address(session):
    with pytest.raises(PreconditionMissing, match="name and address"):
        build_field_values("form_101", session)


@pytest.mark.parametrize("ssn", ["", "1234", "900-55-000"])
def test_ssn_statement_needs_a_nine_digit_ssn(session, ssn):
    _debtor(session, ssn=ssn)
    with pytest.raises(PreconditionMissing, match="Social Security number"):
        build_field_values("form_121", session)


@pytest.mark.parametrize("ssn", ["900-55-0005", "900550005"])
def test_ssn_statement_accepts_either_ssn_format(session, ssn):
    _debtor(session, ssn=ssn)
    assert build_field_values("form_121", session)


def test_ssn_statement_without_a_debtor_fails_instead_of_ticking_no_ssn(session):
    # Before step 1, Form 121's "no SSN" box resolved from missing data.
    with pytest.raises(PreconditionMissing):
        build_field_values("form_121", session)


def test_means_test_form_needs_the_eligibility_check(session):
    _debtor(session)
    with pytest.raises(PreconditionMissing, match="eligibility check"):
        build_field_values("form_122a1", session)


def test_field_values_name_index_widgets(session):
    _debtor(session)
    values = build_field_values("form_101", session)
    widgets = load_index(load_schema("form_101").template_filename)
    assert values["Debtor1.First name"] == "Sarah"
    assert set(values) <= set(widgets)
