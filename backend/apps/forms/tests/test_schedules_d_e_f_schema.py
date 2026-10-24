"""
Schedules D and E/F: each schedule's question answers from the debts the filer listed, and
its totals print on the lines that ask for them, which 106Sum copies.

Business intent: a trustee reads Schedule D's grand total and E/F's line 6 totals against
the summary (106Sum 2, 3b and 9d copy them), and each schedule's question says whether a
list follows. DigniFi doesn't ask which debts have priority (OQ-3), and deciding it is a
legal judgment, so every unsecured debt counts as nonpriority, and E/F's priority question
and priority totals stay blank (step 2 spec §6.1 B5, Appendix A.10). Line 6f counts only
the unsecured student loans: E/F is the unsecured schedule, and 6i (6j - 6f) must never go
below zero (Ruling T16-a).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import DebtInfo, DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemadef", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        middle_name="",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    # 106Sum line 8 is CMI, which needs income entered by source.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))
    return session


def _debt(session, debt_type, amount, secured=False, priority=False):
    DebtInfo.objects.create(
        session=session,
        creditor_name=f"{debt_type} creditor",
        debt_type=debt_type,
        amount_owed=Decimal(amount),
        is_secured=secured,
        is_priority=priority,
    )


@pytest.fixture
def debts(session):
    # Each debt at its own power of two, so a total that counts the wrong debts can't match.
    _debt(session, "auto_loan", "1000", secured=True)
    _debt(session, "student_loan", "2000", secured=True)
    _debt(session, "student_loan", "4000")
    _debt(session, "credit_card", "8000")
    # Marked priority, but nobody asked the filer (OQ-3): it counts as nonpriority.
    _debt(session, "other", "16000", priority=True)
    return session


def _widgets(session, form_type):
    """What the drawn form prints in each widget."""
    values = resolve(load_schema(form_type), session)
    return read_drawn(form_type, PDFFormFiller().fill(form_type, values))


def _printed(session, form_type):
    """Each box as printed: a text box's value, or the states a checkbox ticks."""
    shown = {}
    for w in _widgets(session, form_type):
        if not w.state:
            shown[w.full_name] = w.value
        elif w.state != "/Off":
            shown.setdefault(w.full_name, set()).add(w.state)
    return shown


def test_schedule_d_prints_its_secured_total_in_the_grand_total_box(debts):
    # Line 2's grand total of Column A is on page 2. The page-3 box asks on which line of
    # Part 1 a creditor was entered, and never gets a dollar amount.
    widgets = _widgets(debts, "schedule_d")

    assert [(w.page, w.value) for w in widgets if w.full_name == "undefined_24"] == [(2, "3000.00")]
    assert [w.value for w in widgets if w.full_name == "undefined_27"] == [""]


def test_line_6j_totals_every_unsecured_debt_and_6f_the_unsecured_student_loans(debts):
    shown = _printed(debts, "schedule_e_f")

    assert shown["Total_6f"] == "4000.00"  # the secured student loan is on Schedule D
    assert shown["Total_6i"] == "24000.00"  # the credit card and the debt marked priority
    assert shown["Total_6j"] == "28000.00"


def test_line_6j_adds_lines_6f_through_6i(debts):
    shown = _printed(debts, "schedule_e_f")

    # 6g and 6h are never asked and count as zero (step 2 spec §6.1).
    assert Decimal(shown["Total_6f"]) + Decimal(shown["Total_6i"]) == Decimal(shown["Total_6j"])


def test_a_secured_student_loan_never_turns_line_6i_negative(session):
    # Ruling T16-a: a student loan the filer saved as secured is on Schedule D, not 6f.
    _debt(session, "student_loan", "5000", secured=True)
    _debt(session, "credit_card", "1000")

    shown = _printed(session, "schedule_e_f")

    assert (shown["Total_6f"], shown["Total_6i"], shown["Total_6j"]) == (
        "0.00",
        "1000.00",
        "1000.00",
    )


def test_the_summary_copies_the_totals_schedules_d_and_e_f_print(debts):
    d, ef = _printed(debts, "schedule_d"), _printed(debts, "schedule_e_f")
    summary = resolve(load_schema("form_106sum"), debts)

    assert summary["2"] == d["undefined_24"]
    assert summary["3b"] == ef["Total_6j"]
    assert summary["9d"] == ef["Total_6f"]
    # Total liabilities are 2 + 3a + 3b, and 3a stays blank until priority is asked.
    assert Decimal(summary["3c"]) == Decimal(summary["2"]) + Decimal(summary["3b"])


@pytest.mark.parametrize(
    "secured,d_ticks,ef_ticks",
    [
        pytest.param(True, {"/yes"}, {"/no"}, id="secured_only"),
        pytest.param(False, {"/no"}, {"/yes"}, id="unsecured_only"),
    ],
)
def test_each_debt_question_answers_yes_only_for_the_debts_its_schedule_lists(
    session, secured, d_ticks, ef_ticks
):
    _debt(session, "auto_loan" if secured else "credit_card", "1000", secured=secured)

    assert _printed(session, "schedule_d").get("check1", set()) == d_ticks
    assert _printed(session, "schedule_e_f").get("check7", set()) == ef_ticks


def test_a_filer_with_no_debts_gets_zero_totals_and_no_on_both_questions(session):
    d, ef = _printed(session, "schedule_d"), _printed(session, "schedule_e_f")

    assert d.get("check1", set()) == {"/no"}
    assert ef.get("check7", set()) == {"/no"}
    # Ruling T0-e: the filer finished the intake with no debts listed, so the totals are 0.00.
    assert d["undefined_24"] == "0.00"
    assert (ef["Total_6f"], ef["Total_6i"], ef["Total_6j"]) == ("0.00", "0.00", "0.00")
    assert resolve(load_schema("form_106sum"), session).get("9d") == "0.00"


def test_lines_the_intake_never_asks_print_nothing(debts):
    # A debt marked priority still leaves E/F's priority question (line 1) and its
    # priority totals (6a-6e) blank (OQ-3); 6g and 6h are never asked.
    shown = _printed(debts, "schedule_e_f")

    assert "check1" not in shown
    for box in ("Total_6a", "Total_6b", "Total_6c", "Total_6d", "Total_6e", "Total_6g", "Total_6h"):
        assert shown[box] == "", box
