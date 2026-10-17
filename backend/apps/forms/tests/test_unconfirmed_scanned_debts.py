"""
A debt read from a scanned document prints on no form until the filer confirms it
(forms step 3a1 spec §6, DIG-163).

Business intent: an upload creates each debt it reads as a draft, which the filer checks on
the Amounts Owed step. Until the filer saves that step, the figures are only what a model
read from a photo, and the filer signs every form under penalty of perjury. So a draft counts
in no total, answers no schedule's question and is not a creditor on the petition.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import DebtInfo, DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="draftdebts", password="pass")
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
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    # 106Sum line 8 is CMI, which needs income entered by source.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))
    return session


def _debt(session, debt_type, amount, secured=False, draft=False):
    DebtInfo.objects.create(
        session=session,
        creditor_name=f"{debt_type} creditor",
        debt_type=debt_type,
        amount_owed=Decimal(amount),
        is_secured=secured,
        is_draft=draft,
    )


def _resolved(session, form_type):
    return resolve(load_schema(form_type), session)


def test_a_scanned_debt_the_filer_has_not_confirmed_counts_in_no_total(session):
    # Each debt at its own power of two, so a total that counts a draft can't match.
    _debt(session, "auto_loan", "1000", secured=True)
    _debt(session, "student_loan", "2000")
    _debt(session, "credit_card", "4000")
    _debt(session, "auto_loan", "8000", secured=True, draft=True)
    _debt(session, "student_loan", "16000", draft=True)
    _debt(session, "credit_card", "32000", draft=True)

    d = _resolved(session, "schedule_d")
    ef = _resolved(session, "schedule_e_f")
    summary = _resolved(session, "form_106sum")

    assert d["undefined_24"] == "1000.00"
    assert (ef["Total_6f"], ef["Total_6i"], ef["Total_6j"]) == ("2000.00", "4000.00", "6000.00")
    assert (summary["2"], summary["3b"], summary["3c"], summary["9d"]) == (
        "1000.00",
        "6000.00",
        "7000.00",
        "2000.00",
    )


def test_the_petition_estimates_liabilities_from_confirmed_debts_only(session):
    # The draft's cent would move line 20 into the next range up.
    _debt(session, "credit_card", "50000.00")
    _debt(session, "credit_card", "0.01", draft=True)

    assert _resolved(session, "form_101")["Check Box23"] == "/0-50000"


def test_a_filer_whose_only_debts_are_unconfirmed_lists_no_creditors(session):
    _debt(session, "auto_loan", "1000", secured=True, draft=True)
    _debt(session, "credit_card", "2000", draft=True)

    assert _resolved(session, "schedule_d")["check1"] == "/no"
    assert _resolved(session, "schedule_e_f")["check7"] == "/no"
    # Line 18 asks how many creditors; with none confirmed it stays blank.
    assert "Check Box21" not in _resolved(session, "form_101")
