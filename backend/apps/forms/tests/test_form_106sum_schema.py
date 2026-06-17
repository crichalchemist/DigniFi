"""Round-trip tests for Form 106Sum schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.form_106sum_generator import Form106SumGenerator
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    ExpenseInfo,
    IncomeInfo,
    IntakeSession,
)

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema106sum", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def populated_session(session):
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
    AssetInfo.objects.create(
        session=session,
        asset_type="real_property",
        description="Home",
        current_value=Decimal("200000"),
    )
    AssetInfo.objects.create(
        session=session, asset_type="vehicle", description="Car", current_value=Decimal("15000")
    )
    DebtInfo.objects.create(
        session=session,
        creditor_name="Bank A",
        amount_owed=Decimal("50000"),
        is_secured=True,
        is_priority=False,
    )
    DebtInfo.objects.create(
        session=session,
        creditor_name="Credit Card B",
        amount_owed=Decimal("10000"),
        is_secured=False,
        is_priority=False,
    )
    DebtInfo.objects.create(
        session=session,
        creditor_name="IRS",
        amount_owed=Decimal("5000"),
        is_secured=False,
        is_priority=True,
    )
    IncomeInfo.objects.create(session=session, monthly_income=[1200, 1200, 1200, 1200, 1200, 1200])
    ExpenseInfo.objects.create(
        session=session,
        rent_or_mortgage=Decimal("1000"),
        utilities=Decimal("200"),
        food_and_groceries=Decimal("400"),
        vehicle_payment=Decimal("300"),
    )
    return session


@pytest.mark.django_db
class TestForm106SumSchema:
    def test_schema_loads(self):
        schema = load_schema("form_106sum")
        assert schema.form_type == "form_106sum"
        assert len(schema.fields) == 21

    def test_all_fields_have_valid_source(self):
        schema = load_schema("form_106sum")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_resolver_produces_output(self, populated_session):
        generator = Form106SumGenerator(populated_session)
        field_map = generator.pdf_field_map()
        assert "Debtor 1" in field_map
        assert "Jane Doe" in field_map["Debtor 1"]
        assert "Bankruptcy District Information" in field_map
        assert "1a" in field_map  # real property
        assert "1b" in field_map  # personal property
        assert "2" in field_map  # secured debts
        assert "8" in field_map  # CMI

    def test_asset_totals(self, populated_session):
        generator = Form106SumGenerator(populated_session)
        field_map = generator.pdf_field_map()
        assert field_map["1a"] == "200000.00"  # real property
        assert field_map["1b"] == "15000.00"  # personal property
        assert field_map["1c"] == "215000.00"  # total assets

    def test_debt_totals(self, populated_session):
        generator = Form106SumGenerator(populated_session)
        field_map = generator.pdf_field_map()
        assert field_map["2"] == "50000.00"  # secured
        assert field_map["3a"] == "5000.00"  # priority unsecured
        assert field_map["3b"] == "10000.00"  # nonpriority unsecured
        assert field_map["3c"] == "15000.00"  # total unsecured
        assert field_map["4"] == "65000.00"  # total debts

    def test_cmi(self, populated_session):
        generator = Form106SumGenerator(populated_session)
        field_map = generator.pdf_field_map()
        # 1200 * 6 / 6 = 1200.00
        assert field_map["8"] == "1200.00"

    def test_empty_session(self, session):
        generator = Form106SumGenerator(session)
        field_map = generator.pdf_field_map()
        assert field_map["1a"] == "0.00"
        assert field_map["8"] == "0.00"
