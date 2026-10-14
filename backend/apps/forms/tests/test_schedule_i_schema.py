"""Round-trip tests for Schedule I schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.cmi import IncomeNotSplit
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemasi", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def session_with_income(session):
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
    IncomeInfo.objects.create(
        session=session,
        monthly_gross_wages=Decimal("2000.00"),
        marital_status="single",
        number_of_dependents=0,
    )
    return session


@pytest.mark.django_db
class TestScheduleISchema:
    def test_schema_loads(self):
        schema = load_schema("schedule_i")
        assert schema.form_type == "schedule_i"

    def test_all_fields_have_valid_source(self):
        schema = load_schema("schedule_i")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_resolver_produces_output(self, session_with_income):
        field_map = resolve(load_schema("schedule_i"), session_with_income)
        assert "Bankruptcy District Information" in field_map
        assert "Debtor 1" in field_map
        assert "Jane Doe" in field_map["Debtor 1"]
        assert "Amount 12" in field_map

    def test_cmi_in_field_map(self, session_with_income):
        field_map = resolve(load_schema("schedule_i"), session_with_income)
        # CMI is the wages, the only source given
        assert field_map["Amount 12"] == "2000.00"
        assert field_map["Amount 10 Debtor 1"] == "2000.00"

    def test_empty_session_is_asked_for_income_by_source(self, session):
        # Lines 10 and 12 print CMI until 2b, and a filer who gave no income has none.
        with pytest.raises(IncomeNotSplit):
            resolve(load_schema("schedule_i"), session)
