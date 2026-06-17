"""Round-trip tests for Schedule I schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.schedule_i_generator import ScheduleIGenerator
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
        monthly_income=[2000, 2000, 2000, 2000, 2000, 2000],
        marital_status="single",
        number_of_dependents=0,
    )
    return session


@pytest.mark.django_db
class TestScheduleISchema:
    def test_schema_loads(self):
        schema = load_schema("schedule_i")
        assert schema.form_type == "schedule_i"
        assert len(schema.fields) == 24

    def test_all_fields_have_valid_source(self):
        schema = load_schema("schedule_i")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_resolver_produces_output(self, session_with_income):
        generator = ScheduleIGenerator(session_with_income)
        field_map = generator.pdf_field_map()
        assert "Bankruptcy District Information" in field_map
        assert "Debtor 1" in field_map
        assert "Jane Doe" in field_map["Debtor 1"]
        assert "Amount 12" in field_map

    def test_cmi_in_field_map(self, session_with_income):
        generator = ScheduleIGenerator(session_with_income)
        field_map = generator.pdf_field_map()
        # 2000 * 6 / 6 = 2000
        assert field_map["Amount 12"] == "2000.00"
        assert field_map["Amount 10 Debtor 1"] == "2000.00"

    def test_empty_session(self, session):
        generator = ScheduleIGenerator(session)
        field_map = generator.pdf_field_map()
        assert "Bankruptcy District Information" in field_map
