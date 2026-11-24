"""Round-trip tests for Form 106Sum schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.means_lines import OUTCOMES, SUPP_OUTCOMES
from apps.eligibility.models import MeansTest
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
from apps.intake.tests.builders import answer_household, answer_petition

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
        ab_line="1",
        description="Home",
        current_value=Decimal("200000"),
    )
    AssetInfo.objects.create(
        session=session, ab_line="3", description="Car", current_value=Decimal("15000")
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
        priority_answer="taxes",
        past_due_amount=Decimal("5000"),
    )
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))
    answer_household(session)
    ExpenseInfo.objects.create(
        session=session,
        rent_or_mortgage=Decimal("1000"),
        utilities=Decimal("200"),
        food_and_groceries=Decimal("400"),
    )
    return session


@pytest.mark.django_db
class TestForm106SumSchema:
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

    def test_a_value_the_filer_does_not_know_adds_zero_to_the_totals(self, populated_session):
        AssetInfo.objects.create(
            session=populated_session, ab_line="6", description="Dishes", current_value=None
        )
        AssetInfo.objects.create(
            session=populated_session, ab_line="7", description="TV", current_value=Decimal("25")
        )
        field_map = resolve(load_schema("form_106sum"), populated_session)
        assert field_map["1b"] == "15025.00"  # the vehicle and the TV; the dishes add zero
        assert field_map["1c"] == "215025.00"

    def test_debt_totals(self, populated_session):
        field_map = resolve(load_schema("form_106sum"), populated_session)
        assert field_map["2"] == "50000.00"  # secured
        # The IRS debt is in Part 1 (the filer answered taxes), so 3b holds the card alone.
        assert field_map["3b"] == "10000.00"

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

    def test_line_3a_copies_the_part_1_total(self, populated_session):
        # The fixture's IRS debt is the one the filer answered taxes: it is E/F Part 1's
        # whole total (line 6e), and 3b counts the card alone.
        field_map = resolve(load_schema("form_106sum"), populated_session)
        assert field_map["3a"] == "5000.00"

    def test_line_9_copies_6a_to_6c_and_9g_adds_9a_to_9d(self, populated_session):
        field_map = resolve(load_schema("form_106sum"), populated_session)
        assert (field_map["9a"], field_map["9b"], field_map["9c"]) == (
            "0.00",
            "5000.00",
            "0.00",
        )
        printed = [Decimal(field_map[k]) for k in ("9a", "9b", "9c", "9d")]
        assert Decimal(field_map["9g"]) == sum(printed)
        assert field_map["9g"] == "5000.00"

    def test_monthly_expenses_print_on_line_5_not_on_the_support_obligations_line(
        self, populated_session
    ):
        # Line 5 copies Schedule J line 22c. Line 9a prints 6a's total, never the expenses.
        field_map = resolve(load_schema("form_106sum"), populated_session)
        assert field_map.get("5") == "1600.00"  # 1000 + 200 + 400
        assert field_map["9a"] == "0.00"

    def test_line_6_says_the_filer_is_filing_under_chapter_7_11_or_13(self, populated_session):
        # Every DigniFi filing is Chapter 7, so line 6's Yes ticks and its No stays off.
        values = resolve(load_schema("form_106sum"), populated_session)
        widgets = read_drawn("form_106sum", PDFFormFiller().fill("form_106sum", values))
        assert sorted(w.state for w in widgets if w.full_name == "check6") == ["/Off", "/yes"]

    def test_a_filer_with_no_property_who_typed_zero_income_prints_zeros(self, session):
        # Line 1a is not an income box: no real property prints 0.00. Line 8 prints the $0 typed.
        IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("0.00"))
        field_map = resolve(load_schema("form_106sum"), session)
        assert field_map["1a"] == "0.00"
        assert field_map["8"] == "0.00"


# Line 7 asks Form 101 line 16a again, one box an answer (4d-R7): the filer's own line 16 answer
# ticks exactly one of its two boxes, and an unanswered line 16 ticks neither.
LINE_7_TICKED = {
    "consumer": {"T5": "/consumer"},
    "business": {"T6": "/not consumer"},
    "neither": {"T6": "/not consumer"},
    None: {},
}


@pytest.mark.slow
@pytest.mark.parametrize("answer", LINE_7_TICKED)
def test_each_debt_nature_answer_ticks_exactly_one_box_on_the_page(populated_session, answer):
    answer_petition(populated_session, debt_nature=answer)
    if answer is None:
        assert "debt_nature" not in populated_session.petition_answers.get_answers()
    values = resolve(load_schema("form_106sum"), populated_session)
    widgets = read_drawn("form_106sum", PDFFormFiller().fill("form_106sum", values))
    line_7 = [w for w in widgets if w.full_name == "check7"]
    assert sorted(w.tag for w in line_7) == ["T5", "T6"]
    ticked = {w.tag: w.state for w in line_7 if w.state not in ("", "/Off")}
    assert ticked == LINE_7_TICKED[answer]


# Line 7's not-consumer box says "You have nothing to report on this part of the form" (D7): a
# business or neither filer's 106Sum prints no figure on lines 8 to 9g. A consumer filer, or one
# who has not answered line 16, prints them as before.
LINES_8_TO_9G = ("8", "9a", "9b", "9c", "9d", "9g")
REPORTED = {
    "8": "1200.00",
    "9a": "0.00",
    "9b": "5000.00",
    "9c": "0.00",
    "9d": "0.00",
    "9g": "5000.00",
}


@pytest.mark.parametrize(
    "answer,printed",
    [
        ("business", dict.fromkeys(LINES_8_TO_9G)),
        ("neither", dict.fromkeys(LINES_8_TO_9G)),
        ("consumer", REPORTED),
        (None, REPORTED),
    ],
)
def test_a_business_or_neither_filer_reports_nothing_on_lines_8_to_9g(
    populated_session, answer, printed
):
    answer_petition(populated_session, debt_nature=answer)
    if answer is None:
        assert "debt_nature" not in populated_session.petition_answers.get_answers()
    field_map = resolve(load_schema("form_106sum"), populated_session)
    assert {line: field_map.get(line) for line in LINES_8_TO_9G} == printed


@pytest.mark.parametrize("answer", ["consumer", "business", None])
@pytest.mark.parametrize("outcome", [*OUTCOMES, "no means test"])
def test_106sum_line_8_is_blank_whenever_122a1_line_11_is(populated_session, outcome, answer):
    # Line 8 says "Copy your total current monthly income from Official Form 122A-1 Line 11"
    # (D10): where 122A-1 leaves line 11 blank (a Supp outcome, 4d-R6), 106Sum leaves line 8
    # blank too. One-directional on purpose: a stored non-Supp row beside business, which
    # recalculation never leaves, prints line 11 while D7 blanks line 8.
    answer_petition(populated_session, debt_nature=answer)
    if outcome != "no means test":
        MeansTest.objects.create(
            session=populated_session,
            district=populated_session.district,
            calculated_cmi=Decimal("1200.00"),
            median_income_threshold=Decimal("71304.00"),
            outcome=outcome,
        )
    session = IntakeSession.objects.get(pk=populated_session.pk)
    if answer is None:
        assert "debt_nature" not in session.petition_answers.get_answers()

    line_11 = resolve(load_schema("form_122a1"), session).get("Debto1.Quest11")
    line_8 = resolve(load_schema("form_106sum"), session).get("8")

    assert (line_11 is None) is (outcome in SUPP_OUTCOMES)
    if line_11 is None:
        assert line_8 is None
    if answer == "consumer":
        assert (line_8 is None) is (line_11 is None)
