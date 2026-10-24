"""Round-trip tests for Form 106Sum schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.cmi import IncomeNotSplit
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
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
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))
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

    def test_all_fields_have_valid_source(self):
        schema = load_schema("form_106sum")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_resolver_produces_output(self, populated_session):
        field_map = resolve(load_schema("form_106sum"), populated_session)
        assert "Debtor 1" in field_map
        assert "Jane Doe" in field_map["Debtor 1"]
        assert "Bankruptcy District Information" in field_map
        assert "1a" in field_map  # real property
        assert "1b" in field_map  # personal property
        assert "2" in field_map  # secured debts
        assert "8" in field_map  # CMI

    def test_asset_totals(self, populated_session):
        field_map = resolve(load_schema("form_106sum"), populated_session)
        assert field_map["1a"] == "200000.00"  # real property
        assert field_map["1b"] == "15000.00"  # personal property
        assert field_map["1c"] == "215000.00"  # total assets

    def test_debt_totals(self, populated_session):
        field_map = resolve(load_schema("form_106sum"), populated_session)
        assert field_map["2"] == "50000.00"  # secured
        # Every unsecured debt, the IRS debt marked priority too: priority isn't asked (OQ-3).
        assert field_map["3b"] == "15000.00"

    def test_total_liabilities_print_on_3c_and_combined_monthly_income_on_line_4(
        self, populated_session
    ):
        # 3c totals every debt, secured, unsecured and priority alike. Line 4 copies
        # Schedule I line 12, which counts Social Security; line 8, CMI, never does (C1).
        income = populated_session.income_info
        income.monthly_social_security = Decimal("800.00")
        income.save()
        field_map = resolve(load_schema("form_106sum"), populated_session)
        assert field_map["3c"] == "65000.00"  # 50000 + 10000 + 5000
        assert field_map["4"] == "2000.00"  # 1200 wages + 800 Social Security
        assert field_map["8"] == "1200.00"

    def test_line_3a_stays_blank_until_the_filer_is_asked_which_debts_have_priority(
        self, populated_session
    ):
        # The fixture's IRS debt is marked priority, but DigniFi never asks which debts
        # have priority (OQ-3), and deciding it is a legal judgment: line 3a stays blank,
        # and 3b counts the debt with the other unsecured ones (step 2 spec §6.1 B5).
        field_map = resolve(load_schema("form_106sum"), populated_session)
        assert "3a" not in field_map

    def test_monthly_expenses_print_on_line_5_not_on_the_support_obligations_line(
        self, populated_session
    ):
        # Line 5 copies Schedule J line 22c. Line 9a asks for domestic support
        # obligations, which DigniFi never asks (step 2 spec §6.4).
        field_map = resolve(load_schema("form_106sum"), populated_session)
        assert field_map.get("5") == "1900.00"  # 1000 + 200 + 400 + 300
        assert "9a" not in field_map

    def test_line_6_says_the_filer_is_filing_under_chapter_7_11_or_13(self, populated_session):
        # Every DigniFi filing is Chapter 7, so line 6's Yes ticks and its No stays off.
        values = resolve(load_schema("form_106sum"), populated_session)
        widgets = read_drawn("form_106sum", PDFFormFiller().fill("form_106sum", values))
        assert sorted(w.state for w in widgets if w.full_name == "check6") == ["/Off", "/yes"]

    def test_cmi(self, populated_session):
        field_map = resolve(load_schema("form_106sum"), populated_session)
        # 1200 wages = 1200.00 CMI
        assert field_map["8"] == "1200.00"

    def test_empty_session_is_asked_for_income_by_source(self, session):
        # Line 8 is CMI, and a filer who gave no income has none to print (spec §5.5).
        with pytest.raises(IncomeNotSplit):
            resolve(load_schema("form_106sum"), session)

    def test_a_filer_with_no_property_who_typed_zero_income_prints_zeros(self, session):
        # Line 1a is not an income box: no real property prints 0.00. Line 8 prints the $0 typed.
        IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("0.00"))
        field_map = resolve(load_schema("form_106sum"), session)
        assert field_map["1a"] == "0.00"
        assert field_map["8"] == "0.00"
