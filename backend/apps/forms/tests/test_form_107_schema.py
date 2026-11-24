"""
What the Statement of Financial Affairs (Form 107) prints from the intake (step 2 spec
§6.4, Appendix A.11).

Business intent: the filer's name heads every page, so a page separated from the filing
still says whose it is. Lines 4-6 stay blank until steps 3-4 ask what each prior-income
row is and whether a payment fell in the 90 days before filing (DIG-167). Until then the
saved SOFA rows printed the income's description in the gross-income boxes and the amount
paid as the amount still owed, and a fourth row refused the whole form (DIG-77). The SOFA
answers stay stored for those steps.
"""

import json
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.field_index import index_path
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import DebtorInfo, IntakeSession, SOFAReport
from apps.intake.tests.builders import answer_petition

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema107", password="pass")
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
        middle_name="Q",
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
    return session


def _sofa(session, prior_income=0, creditor_payments=0):
    """The SOFA page's answers: Yes to both questions, with this many rows of each."""
    report = SOFAReport.objects.create(
        session=session, has_prior_income=True, has_creditor_payments=True
    )
    for i in range(prior_income):
        report.prior_income.create(
            year=2025 - i, source=f"Wages - Employer {i}", gross_amount=Decimal("38400.00")
        )
    for i in range(creditor_payments):
        report.creditor_payments.create(
            creditor_name=f"Creditor {i}",
            total_paid=Decimal("1020.00"),
            dates_of_payments="Monthly Jan-Mar 2026",
        )


def _fill(session):
    return PDFFormFiller().fill("form_107", resolve(load_schema("form_107"), session))


def _boxes_on_lines(*lines):
    """Every box the field index places on these lines of Form 107."""
    rows = json.loads(index_path(load_schema("form_107").template_filename).read_text())
    return {row["full_name"] for row in rows if row["line"] in lines}


@pytest.mark.slow
def test_the_filers_name_heads_every_page(session):
    printed = read_drawn("form_107", _fill(session))

    # Each page's header widget is drawn on its own page.
    pages = [w.page for w in printed if w.full_name == "Debtor 1" and w.value == "Jane Q Doe"]
    assert pages == list(range(1, 13))
    # A single filer's statement: the spouse's line stays blank.
    assert [w.value for w in printed if w.full_name == "Debtor 2"] == [""]


@pytest.mark.slow
def test_saved_sofa_rows_print_nothing_on_lines_4_to_6(session):
    _sofa(session, prior_income=3, creditor_payments=3)

    printed = {
        w.full_name
        for w in read_drawn("form_107", _fill(session))
        if w.full_name in _boxes_on_lines("4", "5", "6")
        and (w.value or w.state not in ("", "/Off"))
    }

    assert printed == set()


@pytest.mark.parametrize("kind", ["prior_income", "creditor_payments"])
def test_a_fourth_sofa_row_no_longer_keeps_form_107_from_printing(session, kind):
    # Lines 4-6 printed three rows of each, so a fourth refused the form (DIG-77).
    _sofa(session, **{kind: 4})

    assert resolve(load_schema("form_107"), session)["Debtor 1"] == "Jane Q Doe"


# Line 6 asks Form 101 line 16a again, one box an answer (4d-R7): the filer's own line 16 answer
# ticks exactly one of its two boxes, and an unanswered line 16 ticks neither.
LINE_6_TICKED = {
    "consumer": {"T6": "/yes"},
    "business": {"T3": "/no"},
    "neither": {"T3": "/no"},
    None: {},
}


@pytest.mark.slow
@pytest.mark.parametrize("answer", LINE_6_TICKED)
def test_each_debt_nature_answer_ticks_exactly_one_line_6_box(session, answer):
    answer_petition(session, debt_nature=answer)
    if answer is None:
        assert "debt_nature" not in session.petition_answers.get_answers()
    line_6 = [w for w in read_drawn("form_107", _fill(session)) if w.full_name == "check6"]
    assert sorted(w.tag for w in line_6) == ["T3", "T6"]
    ticked = {w.tag: w.state for w in line_6 if w.state not in ("", "/Off")}
    assert ticked == LINE_6_TICKED[answer]
