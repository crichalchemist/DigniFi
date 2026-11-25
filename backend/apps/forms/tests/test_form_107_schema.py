"""
What the Statement of Financial Affairs (Form 107) prints from the intake (step 2 spec
§6.4, Appendix A.11).

Business intent: the filer's name heads every page, so a page separated from the filing
still says whose it is. Lines 4-6 stay blank until steps 3-4 ask what each prior-income
row is and whether a payment fell in the 90 days before filing (DIG-167). An old SOFA
report, whose tables stay until 4i, changes nothing the form prints.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.registry import build_field_values
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import (
    DebtorInfo,
    IntakeSession,
    SOFACreditorPayment,
    SOFAPriorIncome,
    SOFAReport,
)
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


def _fill(session):
    return PDFFormFiller().fill("form_107", resolve(load_schema("form_107"), session))


@pytest.mark.slow
def test_the_filers_name_heads_every_page(session):
    printed = read_drawn("form_107", _fill(session))

    # Each page's header widget is drawn on its own page.
    pages = [w.page for w in printed if w.full_name == "Debtor 1" and w.value == "Jane Q Doe"]
    assert pages == list(range(1, 13))
    # A single filer's statement: the spouse's line stays blank.
    assert [w.value for w in printed if w.full_name == "Debtor 2"] == [""]


def test_an_old_sofa_report_alone_changes_nothing_form_107_prints(session):
    # "Alone": this session has no stored answer:form_107 FormAnswer. Under one of the 28 boxes
    # the two kept predicates (has_prior_income, has_creditor_payments) gate, such a FormAnswer
    # still prints while an old report says Yes, as at 228371f, until 4f-ii's T-ii.2 rewrites
    # those bindings (ledger H6, ruling FR-SOFA-TEST).
    before = build_field_values("form_107", session)
    report = SOFAReport.objects.create(
        session=session, has_prior_income=True, has_creditor_payments=True, has_business=True
    )
    SOFAPriorIncome.objects.create(
        report=report, year=2025, source="Demo wages", gross_amount=Decimal("1000.00")
    )
    SOFACreditorPayment.objects.create(
        report=report, creditor_name="Demo Bank", total_paid=Decimal("700.00")
    )
    assert build_field_values("form_107", IntakeSession.objects.get(pk=session.pk)) == before


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
