"""Round-trip tests for Form 106Dec schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.form_106dec_generator import Form106DecGenerator
from apps.intake.models import DebtorInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema106dec", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def session_with_debtor(session):
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
class TestForm106DecSchema:
    def test_schema_loads(self):
        schema = load_schema("form_106dec")
        assert schema.form_type == "form_106dec"
        assert len(schema.fields) == 8

    def test_all_fields_have_source(self):
        schema = load_schema("form_106dec")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_required_fields_marked(self):
        schema = load_schema("form_106dec")
        required = [f for f in schema.fields if f.required]
        assert len(required) >= 2  # District and Debtor 1 at minimum

    def test_resolver_produces_output(self, session_with_debtor):
        generator = Form106DecGenerator(session_with_debtor)
        field_map = generator.pdf_field_map()
        assert "Debtor 1" in field_map
        assert "Jane Marie Doe" in field_map["Debtor 1"]
        assert "Bankruptcy District Information" in field_map
        assert "Northern District of Illinois" in field_map["Bankruptcy District Information"]

    def test_resolver_without_debtor(self, session):
        generator = Form106DecGenerator(session)
        field_map = generator.pdf_field_map()
        assert "Bankruptcy District Information" in field_map
        # Debtor 1 should be empty or absent when no debtor_info
        debtor_val = field_map.get("Debtor 1", "")
        assert debtor_val == "" or "Debtor 1" not in field_map
