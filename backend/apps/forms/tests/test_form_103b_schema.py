"""Round-trip tests for Form 103B schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.form_103b_generator import Form103BGenerator
from apps.intake.models import (
    DebtorInfo,
    FeeWaiverApplication,
    IntakeSession,
)

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
    FeeWaiverApplication.objects.create(
        session=session,
        household_size=2,
        monthly_income=Decimal("1500.00"),
        monthly_expenses=Decimal("1400.00"),
        receives_public_benefits=True,
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
        assert len(schema.fields) == 42

    def test_all_fields_have_valid_source(self):
        schema = load_schema("form_103b")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_resolver_produces_output(self, session_with_fw):
        generator = Form103BGenerator(session_with_fw)
        field_map = generator.pdf_field_map()
        assert "Bankruptcy District Information" in field_map
        assert "Debtor" in field_map
        assert "Jane Doe" in field_map["Debtor"]

    def test_fee_waiver_fields(self, session_with_fw):
        generator = Form103BGenerator(session_with_fw)
        field_map = generator.pdf_field_map()
        assert field_map["Total number of people"] == "2"
        assert field_map["4 type"] == "1500.00"
        assert field_map["5 Type"] == "1400.00"

    def test_empty_session(self, session):
        generator = Form103BGenerator(session)
        field_map = generator.pdf_field_map()
        assert "Bankruptcy District Information" in field_map
        assert field_map.get("Total number of people", "1") == "1"
