"""
Verify pdf_field_map() on every generator returns the correct shape and
writes real values into the corresponding AO court PDF template.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.registry import get_generator
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    ExpenseInfo,
    FeeWaiverApplication,
    IncomeInfo,
    IntakeSession,
)

User = get_user_model()


@pytest.fixture
def ilnd(db):
    return District.objects.get_or_create(
        code="ilnd",
        defaults={
            "name": "Northern District of Illinois",
            "court_name": "U.S. Bankruptcy Court, N.D. Ill.",
            "state": "IL",
            "filing_fee_chapter_7": Decimal("338.00"),
        },
    )[0]


@pytest.fixture
def full_session(db, ilnd):
    """IntakeSession with all related models populated (mirrors demo_maria persona)."""
    user = User.objects.create_user(username="maptest", password="x")
    session = IntakeSession.objects.create(
        user=user, district=ilnd, status="completed", current_step=6
    )
    DebtorInfo.objects.create(
        session=session,
        first_name="Maria",
        middle_name="",
        last_name="Torres",
        ssn="900-55-0001",
        date_of_birth=date(1982, 3, 14),
        phone="312-555-0101",
        email="maria.torres@demo.dignifi.org",
        street_address="742 W 18th St Apt 3B",
        city="Chicago",
        state="IL",
        zip_code="60616",
    )
    IncomeInfo.objects.create(
        session=session,
        marital_status="single",
        number_of_dependents=2,
        monthly_income=[2200, 2200, 2200, 2200, 2200, 2200],
    )
    ExpenseInfo.objects.create(
        session=session,
        rent_or_mortgage=Decimal("950.00"),
        utilities=Decimal("120.00"),
        home_maintenance=Decimal("0.00"),
        vehicle_payment=Decimal("0.00"),
        vehicle_insurance=Decimal("80.00"),
        vehicle_maintenance=Decimal("30.00"),
        food_and_groceries=Decimal("400.00"),
        clothing=Decimal("50.00"),
        medical_expenses=Decimal("75.00"),
        childcare=Decimal("200.00"),
        child_support_paid=Decimal("0.00"),
        insurance_not_deducted=Decimal("0.00"),
        other_expenses=Decimal("100.00"),
    )
    AssetInfo.objects.create(
        session=session,
        asset_type="bank_account",
        description="Chase checking",
        current_value=Decimal("320.00"),
        amount_owed=Decimal("0.00"),
    )
    DebtInfo.objects.create(
        session=session,
        creditor_name="Capital One",
        debt_type="credit_card",
        amount_owed=Decimal("4200.00"),
        monthly_payment=Decimal("75.00"),
        is_in_collections=False,
        consumer_business_classification="consumer",
        is_secured=False,
    )
    FeeWaiverApplication.objects.create(
        session=session,
        household_size=3,
        monthly_income=Decimal("2200.00"),
        monthly_expenses=Decimal("2005.00"),
        receives_public_benefits=False,
        cannot_pay_full=True,
        cannot_pay_installments=True,
        status="pending",
    )
    return session


def _assert_map_shape(field_map: dict) -> None:
    """All values must be strings; dict must be non-empty."""
    assert isinstance(field_map, dict), "pdf_field_map() must return a dict"
    assert field_map, "pdf_field_map() must return at least one field"
    for k, v in field_map.items():
        assert isinstance(k, str), f"Key {k!r} is not a string"
        assert isinstance(v, str), f"Value for {k!r} is not a string (got {type(v)})"


# ---------------------------------------------------------------------------
# Form 121
# ---------------------------------------------------------------------------


def test_form_121_pdf_field_map(full_session):
    gen = get_generator("form_121", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert field_map["Debtor1.First name"] == "Maria"
    assert field_map["Debtor1.Last name"] == "Torres"
    assert "900-55-0001" in field_map["Debtor1a.SSNum"]
    assert field_map["Bankruptcy District Information"] == "Northern District of Illinois"


# ---------------------------------------------------------------------------
# Form 106Dec
# ---------------------------------------------------------------------------


def test_form_106dec_pdf_field_map(full_session):
    gen = get_generator("form_106dec", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert "Torres" in field_map["Debtor 1"]
    assert field_map["Bankruptcy District Information"] == "Northern District of Illinois"


# ---------------------------------------------------------------------------
# Form 101
# ---------------------------------------------------------------------------


def test_form_101_pdf_field_map(full_session):
    gen = get_generator("form_101", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert field_map.get("First name") == "Maria"
    assert field_map.get("Last name") == "Torres"
    # SSN last-4
    assert field_map.get("SSNum") == "0001"
    assert field_map.get("City") == "Chicago"
    # Chapter 7 checkbox constant
    assert field_map.get("Check Box2") == "/Yes"
    # Attorney-gated fields are absent (pro se = no attorney)
    assert field_map.get("Firm name") is None  # gated behind has_attorney
    # Business-gated fields absent if no business
    assert field_map.get("Business name") is None


# ---------------------------------------------------------------------------
# Form 106Sum
# ---------------------------------------------------------------------------


def test_form_106sum_pdf_field_map(full_session):
    gen = get_generator("form_106sum", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert "Torres" in field_map.get("Debtor 1", "")
    # full_session has only a bank_account asset — no real property
    assert field_map.get("1a") == "0.00"


# ---------------------------------------------------------------------------
# Schedule I
# ---------------------------------------------------------------------------


def test_schedule_i_pdf_field_map(full_session):
    gen = get_generator("schedule_i", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert "Torres" in field_map.get("Debtor 1", "")
    # CMI for 6x $2200/mo = $2200.00
    assert field_map.get("Amount 10 Debtor 1") == "2200.00"


# ---------------------------------------------------------------------------
# Schedule J
# ---------------------------------------------------------------------------


def test_schedule_j_pdf_field_map(full_session):
    gen = get_generator("schedule_j", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert field_map.get("10") == "950.00"  # rent_or_mortgage
    assert field_map.get("15a") == "400.00"  # food_and_groceries
    assert field_map.get("16") == "75.00"  # medical_expenses


# ---------------------------------------------------------------------------
# Form 122A-1
# ---------------------------------------------------------------------------


def test_form_122a1_pdf_field_map(full_session):
    gen = get_generator("form_122a1", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert field_map["Debtor1.First name"] == "Maria"
    # CMI = $2200/mo, annualized = $26,400
    assert field_map.get("12B") == "26400.00"


# ---------------------------------------------------------------------------
# Form 103B
# ---------------------------------------------------------------------------


def test_form_103b_pdf_field_map(full_session):
    gen = get_generator("form_103b", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert "Torres" in field_map.get("Debtor", "")
    assert field_map.get("Bankruptcy District Information") == "Northern District of Illinois"


# ---------------------------------------------------------------------------
# Schedule A/B
# ---------------------------------------------------------------------------


def test_schedule_ab_pdf_field_map(full_session):
    gen = get_generator("schedule_a_b", full_session)
    field_map = gen.pdf_field_map()
    _assert_map_shape(field_map)
    assert "Torres" in field_map.get("Debtor 1", "")
    # full_session has a bank_account worth $320
    assert field_map.get("16 Cash amount") == "320.00"


# ---------------------------------------------------------------------------
# Schedule C
# ---------------------------------------------------------------------------


def test_schedule_c_pdf_field_map(full_session):
    gen = get_generator("schedule_c", full_session)
    field_map = gen.pdf_field_map()
    assert isinstance(field_map, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in field_map.items())


# ---------------------------------------------------------------------------
# Schedule D
# ---------------------------------------------------------------------------


def test_schedule_d_pdf_field_map(full_session):
    gen = get_generator("schedule_d", full_session)
    field_map = gen.pdf_field_map()
    assert isinstance(field_map, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in field_map.items())
    assert field_map.get("Bankruptcy District Information") == "Northern District of Illinois"


# ---------------------------------------------------------------------------
# Schedule E/F
# ---------------------------------------------------------------------------


def test_schedule_ef_pdf_field_map(full_session):
    gen = get_generator("schedule_e_f", full_session)
    field_map = gen.pdf_field_map()
    assert isinstance(field_map, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in field_map.items())
    # full_session has Capital One credit card ($4200 unsecured)
    assert field_map.get("1") == "Capital One"


# ---------------------------------------------------------------------------
# Form 107
# ---------------------------------------------------------------------------


def test_form_107_pdf_field_map(full_session):
    gen = get_generator("form_107", full_session)
    field_map = gen.pdf_field_map()
    assert isinstance(field_map, dict)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in field_map.items())
    assert field_map.get("Bankruptcy District Information") == "Northern District of Illinois"
    assert "Torres" in field_map.get("Debtor 2", "")
