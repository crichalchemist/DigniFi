"""Round-trip tests for Schedule I schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.tests.test_derivations import TEN_SOURCES
from apps.forms.tests.test_form_122a1_schema import LINE_BY_SOURCE as FORM_122A1_LINE_BY_SOURCE
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()

# Box → what it prints with TEN_SOURCES (wages 1, overtime 2, tips 4, rental 8,
# pension 16, Social Security 32, unemployment 64, child support 128, alimony 256,
# other 512).
LINE_BY_SOURCE = {
    "Amount 2 Debtor 1": "5.00",  # line 2: wages and tips
    "Amount 3 Debtor 1": "2.00",  # line 3: overtime
    "Amount 8a Debtor 1": "8.00",  # 8a: net rental income
    "Amount 8c Debtor 1": "384.00",  # 8c: child support and alimony
    "Amount 8d Debtor 1": "64.00",  # 8d: unemployment
    "Amount 8e Debtor 1": "32.00",  # 8e: Social Security
    "Amount 8g Debtor 1": "16.00",  # 8g: pension
    "Other income 8h": "Other income",  # 8h: what the other income is
    "Amount 8h Debtor 1": "512.00",  # 8h: its amount
}
LINE_TOTALS = {
    "Amount 4 Debtor 1": "7.00",  # line 4: line 2 + line 3
    "Amount 4 Debtor 1a": "7.00",  # line 4's copy at the top of page 2
    "Amount 7 Debtor 1": "7.00",  # line 7: line 4, as no payroll deduction is asked yet
    "Amount 9 Debtor 1": "1016.00",  # line 9: 8a + 8c + 8d + 8e + 8g + 8h
}
NEVER_ASKED = {
    "Supplemental income date",  # a Chapter 13 supplement's date
    "Amount 5a Debtor 1",  # lines 5a-6: payroll deductions
    "Amount 5b Debtor 1",
    "Amount 5c Debtor 1",
    "Amount 5d Debtor 1",
    "Amount 5e Debtor 1",
    "Amount 5f Debtor 1",
    "Amount 5g Debtor 1",
    "Amount 5h Debtor 1",
    "Amount 6 Debtor 1",
    "Amount 8b Debtor 1",  # interest and dividends
    "Amount 8f Debtor 1",  # other government assistance
}
# Schedule I's combined monthly income and every box that copies it: all ten sources,
# Social Security included (step 2 spec §6.1, C1), 1 + 2 + 4 + ... + 512.
COMBINED_INCOME = {
    ("schedule_i", "Amount 10 Debtor 1"): "1023.00",  # line 10: line 7 + line 9
    ("schedule_i", "Amount 10"): "1023.00",  # line 10's total: no spouse column yet
    ("schedule_i", "Amount 12"): "1023.00",  # line 12: line 10 + line 11, never asked
    ("form_106sum", "4"): "1023.00",  # copies Schedule I line 12
    ("schedule_j", "23a"): "1023.00",  # copies Schedule I line 12
    # Current monthly income leaves Social Security (32) out.
    ("form_122a1", "Quest11"): "991.00",  # 122A-1 line 11
    ("form_106sum", "8"): "991.00",  # copies 122A-1 line 11
}
INCOME_LINES = {"Amount 10 Debtor 1", "Amount 10", "Amount 12", *LINE_BY_SOURCE, *LINE_TOTALS}


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

    def test_lines_10_and_12_print_the_income_total(self, session_with_income):
        field_map = resolve(load_schema("schedule_i"), session_with_income)
        # The wages are the only source given, so the Schedule I income total is the wages
        assert field_map["Amount 12"] == "2000.00"
        assert field_map["Amount 10 Debtor 1"] == "2000.00"

    def test_each_income_source_prints_on_its_own_line(self, session):
        # A distinct power of two per source, so a box that reads the wrong source, or
        # adds one too many, prints a different figure (step 2 spec §5.5's table, §7.7).
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)

        schedule_i = resolve(load_schema("schedule_i"), session)
        form_122a1 = resolve(load_schema("form_122a1"), session)

        assert {box: schedule_i.get(box) for box in LINE_BY_SOURCE} == LINE_BY_SOURCE
        assert {
            box: form_122a1.get(box) for box in FORM_122A1_LINE_BY_SOURCE
        } == FORM_122A1_LINE_BY_SOURCE
        # Social Security is Schedule I income (8e), but never current monthly income.
        assert [box for box, value in schedule_i.items() if value == "32.00"] == [
            "Amount 8e Debtor 1"
        ]
        assert "32.00" not in form_122a1.values()

    def test_lines_4_7_and_9_add_the_lines_the_form_names(self, session):
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)

        field_map = resolve(load_schema("schedule_i"), session)

        assert {box: field_map.get(box) for box in LINE_TOTALS} == LINE_TOTALS

    def test_lines_schedule_i_never_asks_about_print_nothing(self, session):
        # Payroll deductions wait for step 3; interest and other government assistance
        # are never asked: blank, never 0.00 (B2).
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)

        field_map = resolve(load_schema("schedule_i"), session)

        assert sorted(NEVER_ASKED & field_map.keys()) == []

    def test_combined_monthly_income_counts_social_security_wherever_it_is_copied(self, session):
        # Schedule I line 12 is all of the filer's income; current monthly income is not
        # (11 U.S.C. § 101(10A)(B)). Each form prints the one its line asks for.
        IncomeInfo.objects.create(session=session, **TEN_SOURCES)

        forms = {form_type for form_type, _ in COMBINED_INCOME}
        printed = {form_type: resolve(load_schema(form_type), session) for form_type in forms}

        assert {
            (form_type, box): printed[form_type].get(box) for form_type, box in COMBINED_INCOME
        } == COMBINED_INCOME

    def test_income_lines_print_blank_until_the_filer_gives_income_by_source(self, session):
        # Forms are refused before they are built (views._prepare, test_income_resume.py);
        # Schedule I and Schedule J line 23a never print an income the filer didn't give.
        def income_printed():
            schedule_i = resolve(load_schema("schedule_i"), session)
            schedule_j = resolve(load_schema("schedule_j"), session)
            return sorted(INCOME_LINES & schedule_i.keys()), schedule_j.get("23a")

        assert income_printed() == ([], None)
        # A total saved before income was stored by source is never split for the filer.
        IncomeInfo.objects.create(session=session, monthly_income=[3000] * 6)
        assert income_printed() == ([], None)
