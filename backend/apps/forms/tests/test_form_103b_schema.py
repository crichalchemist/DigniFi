"""Round-trip tests for Form 103B schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.cmi import MARRIAGE_UNANSWERED, IncomeStepGap
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import (
    DebtorInfo,
    FeeWaiverApplication,
    IncomeInfo,
    IntakeSession,
)
from apps.intake.tests.builders import answer_household

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema103b", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def session_with_fw(session):
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        middle_name="",
        last_name="Doe",
        ssn="123-45-6789",
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1500.00"))
    answer_household(session)
    FeeWaiverApplication.objects.create(
        session=session,
        household_size=2,
        monthly_take_home_pay=Decimal("1500.00"),
        receives_noncash_assistance=True,
        benefit_types=["SNAP"],
        cannot_pay_full=True,
        cannot_pay_installments=True,
    )
    return session


@pytest.mark.django_db
class TestForm103BSchema:
    def test_schema_loads(self):
        schema = load_schema("form_103b")
        assert schema.form_type == "form_103b"

    def test_all_fields_have_valid_source(self):
        schema = load_schema("form_103b")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_resolver_produces_output(self, session_with_fw):
        field_map = resolve(load_schema("form_103b"), session_with_fw)
        assert "Bankruptcy District Information" in field_map
        assert "Debtor 1" in field_map
        assert "Jane Doe" in field_map["Debtor 1"]

    def test_line_1_counts_the_household_list_not_the_applications_size(self, session_with_fw):
        # The application says 2; the filer listed no one else, so 103B line 1 is 1.
        field_map = resolve(load_schema("form_103b"), session_with_fw)
        assert field_map["Total number of people"] == "1"

    def test_an_empty_session_is_refused_in_the_income_steps_words(self, session):
        with pytest.raises(IncomeStepGap) as refused:
            resolve(load_schema("form_103b"), session)
        assert str(refused.value) == MARRIAGE_UNANSWERED
