"""Round-trip tests for Form 122A-1 schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.cmi import IncomeNotSplit
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.tests.test_derivations import TEN_SOURCES
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()

# Box → what it prints with TEN_SOURCES (wages 1, overtime 2, tips 4, rental 8,
# pension 16, Social Security 32, unemployment 64, child support 128, alimony 256,
# other 512).
LINE_BY_SOURCE = {
    "Debto1.Quest2.0": "7.00",  # line 2: wages, overtime and tips
    "Debto1.Quest3": "256.00",  # line 3: alimony
    "Debto1.Quest4": "128.00",  # line 4: child support
    "Debto1.Quest6C": "8.00",  # line 6: net rental income
    "Debto1.Quest8.0": "64.00",  # line 8: unemployment
    "Debto1.Quest9": "16.00",  # line 9: pension
    "terrorism If necessary list other sources on a separate page and put the total below 1": (
        "Other income"
    ),  # line 10: the source
    "Debto1.Quest10A": "512.00",  # line 10: its amount
}
NEVER_ASKED = {
    "Debto1.Quest5A",
    "Debto1.Quest5B",
    "Debto1.Quest6A",
    "Debto1.Quest6B",
    "Debto1.Quest7",
    "Debto1.Quest8A",
    "Debto1.Quest10B",
    "Debto1.Quest10C",
}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema122a1", password="pass")
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
    IncomeInfo.objects.create(
        session=session,
        monthly_gross_wages=Decimal("2000.00"),
        marital_status="single",
        number_of_dependents=0,
    )
    return session


@pytest.mark.django_db
class TestForm122A1Schema:
    def test_schema_loads(self):
        schema = load_schema("form_122a1")
        assert schema.form_type == "form_122a1"

    def test_all_fields_have_valid_source(self):
        schema = load_schema("form_122a1")
        for f in schema.fields:
            assert f.source in ("presume", "derived", "constant", "asked", "ingested")

    def test_resolver_produces_output(self, session_with_income):
        field_map = resolve(load_schema("form_122a1"), session_with_income)
        assert "Bankruptcy District Information" in field_map
        assert "12B" in field_map  # annualized CMI

    def test_cmi_calculation(self, session_with_income):
        field_map = resolve(load_schema("form_122a1"), session_with_income)
        # 2000 wages = 2000 CMI, annualized = 24000
        assert field_map["12B"] == "24000.00"

    def test_empty_session_is_asked_for_income_by_source(self, session):
        # Lines 11 to 13 are CMI, and a filer who gave no income has none (spec §5.5).
        with pytest.raises(IncomeNotSplit):
            resolve(load_schema("form_122a1"), session)

    def test_each_income_source_prints_on_the_122a1_line_that_asks_for_it(self, session):
        # A distinct power of two per source, so a box that reads the wrong source, or
        # adds one too many, prints a different figure (step 2 spec §5.5's table).
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)

        field_map = resolve(load_schema("form_122a1"), session)

        assert {box: field_map.get(box) for box in LINE_BY_SOURCE} == LINE_BY_SOURCE
        # Social Security is left out of current monthly income, so no line shows it.
        assert "32.00" not in field_map.values()

    def test_lines_the_filer_is_never_asked_about_print_nothing(self, session):
        # Business income, interest, rental gross and costs, unemployment claimed as
        # Social Security, a second other-income row: blank, never 0.00 (B2).
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)

        field_map = resolve(load_schema("form_122a1"), session)

        assert sorted(NEVER_ASKED & field_map.keys()) == []

    def test_line_13_prints_the_household_size(self, session_with_income):
        DebtorInfo.objects.create(
            session=session_with_income,
            first_name="Maria",
            last_name="Torres",
            ssn="900-11-0001",  # IRS-reserved range: synthetic
            date_of_birth=date(1988, 6, 15),
            household_size=3,
        )

        field_map = resolve(load_schema("form_122a1"), session_with_income)

        assert field_map["13B"] == "3"
