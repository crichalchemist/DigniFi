"""Round-trip tests for Form 121 schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.form_121_generator import Form121Generator
from apps.intake.models import DebtorInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema121", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def session_with_ssn(session):
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        middle_name="Marie",
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
    return session


@pytest.mark.django_db
class TestForm121Schema:
    def test_schema_loads(self):
        schema = load_schema("form_121")
        assert schema.form_type == "form_121"
        assert len(schema.fields) == 20

    def test_all_fields_have_valid_source(self):
        schema = load_schema("form_121")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_resolver_produces_output(self, session_with_ssn):
        generator = Form121Generator(session_with_ssn)
        field_map = generator.pdf_field_map()
        assert "Debtor1.First name" in field_map
        assert field_map["Debtor1.First name"] == "Jane"
        assert field_map["Debtor1.Last name"] == "Doe"
        assert "Debtor1a.SSNum" in field_map
        assert field_map["Debtor1a.SSNum"] == "123-45-6789"

    def test_ssn_checkbox(self, session_with_ssn):
        generator = Form121Generator(session_with_ssn)
        field_map = generator.pdf_field_map()
        assert field_map.get("Check Box1") == "/Yes"

    def test_district_name(self, session_with_ssn):
        generator = Form121Generator(session_with_ssn)
        field_map = generator.pdf_field_map()
        assert field_map["Bankruptcy District Information"] == "Northern District of Illinois"

    def test_without_debtor(self, session):
        generator = Form121Generator(session)
        field_map = generator.pdf_field_map()
        assert "Bankruptcy District Information" in field_map
