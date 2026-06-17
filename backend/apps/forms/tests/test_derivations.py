"""Tests for factual derivations and section predicates."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.services.derivations import DERIVATIONS, PREDICATES
from apps.intake.models import DebtorInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="testuser", password="pw")
    d = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        court_name="x",
        state="IL",
        filing_fee_chapter_7="338.00",
    )
    s = IntakeSession.objects.create(user=user, district=d, status="completed", current_step=6)
    DebtorInfo.objects.create(
        session=s,
        first_name="Maria",
        middle_name="",
        last_name="Torres",
        ssn="000-00-0000",
        date_of_birth=date(1985, 6, 1),
        phone="555-0100",
        email="maria@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
        household_size=3,
    )
    return s


def test_full_name_collapses_blank_middle(session):
    assert DERIVATIONS["full_name"](session) == "Maria Torres"


def test_full_name_includes_middle(session):
    session.debtor_info.middle_name = "A."
    session.debtor_info.save()
    assert DERIVATIONS["full_name"](session) == "Maria A. Torres"


def test_family_size_reads_household_size(session):
    assert DERIVATIONS["family_size"](session) == "3"


def test_chapter_constant(session):
    assert DERIVATIONS["chapter"](session) == "7"


def test_debtor_type_individual(session):
    assert DERIVATIONS["debtor_type"](session) == "Individual"


def test_district_name(session):
    assert DERIVATIONS["district_name"](session) == "Northern District of Illinois"


def test_has_business_predicate_false_without_report(session):
    assert PREDICATES["has_business"](session) is False


def test_has_creditor_payments_predicate_false_without_report(session):
    assert PREDICATES["has_creditor_payments"](session) is False


def test_has_prior_income_predicate_false_without_report(session):
    assert PREDICATES["has_prior_income"](session) is False
