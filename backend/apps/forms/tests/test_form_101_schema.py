"""
What the petition (Form 101) prints from the intake (step 2 spec §6.4, Appendix A.1).

Business intent: the filer signs Form 101 under penalty of perjury, so each box shows
only what its line asks. It ticks Chapter 7 and the ranges on lines 18-20, and prints
the filer's name in the page header and the filer's own phone. A value never spills
into a neighbouring box, and a line the intake doesn't ask stays blank (DIG-76, DIG-68).
"""

from datetime import date
from decimal import Decimal
from io import BytesIO

import pypdf
import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller, field_of, qualified_name
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    FormAnswer,
    IntakeSession,
    SOFAReport,
)

User = get_user_model()

# The widest amount one row can hold (DecimalField(12, 2)).
WIDEST_ROW = "9999999999.99"


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema101", password="pass")
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


def _petition(session):
    return resolve(load_schema("form_101"), session)


def _answer(session, key, value, form_type="form_101"):
    FormAnswer.objects.create(session=session, form_type=form_type, field_key=key, value=value)


def _debts(session, amounts):
    DebtInfo.objects.bulk_create(
        DebtInfo(
            session=session,
            creditor_name=f"Creditor {i}",
            debt_type="credit_card",
            amount_owed=Decimal(amount),
        )
        for i, amount in enumerate(amounts)
    )


def _assets(session, amounts):
    AssetInfo.objects.bulk_create(
        AssetInfo(
            session=session,
            asset_type="other",
            description=f"Asset {i}",
            current_value=Decimal(amount),
        )
        for i, amount in enumerate(amounts)
    )


def test_petition_ticks_chapter_7(session):
    # One value ticks Chapter 7 in both places the form asks: the page 1 header and line 7.
    assert _petition(session)["Check Box1"] == "/Chapter 7"


def test_petition_answers_yes_to_filing_under_chapter_7(session):
    assert _petition(session)["Check Box20"] == "/Yes"


@pytest.mark.parametrize("count,state", [(1, "/1-49"), (49, "/1-49"), (50, "/50-99")])
def test_line_18_ticks_the_range_the_number_of_creditors_falls_in(session, count, state):
    _debts(session, ["100.00"] * count)
    assert _petition(session)["Check Box21"] == state


def test_a_filer_with_no_creditors_leaves_line_18_blank(session):
    assert "Check Box21" not in _petition(session)


@pytest.mark.parametrize(
    "amounts,line_19,line_20",
    [
        # Nothing owned or owed is the lowest range, not a blank line.
        ([], "/0-50000", "/0-50000"),
        (["50000.00"], "/0-50000", "/0-50000"),
        # Cents above a range's top belong to the next range up.
        (["50000.01"], "/50001-100000", "/50001-100000"),
        # Lines 19 and 20 spell this range differently, and each ticks its own.
        (["100000000.50"], "/100000000-500000000", "/100000001-500000000"),
        ([WIDEST_ROW] * 6, "/More than 50000000000", "/More than 50000000000"),
    ],
)
def test_lines_19_and_20_tick_the_range_the_total_falls_in(session, amounts, line_19, line_20):
    _assets(session, amounts)
    _debts(session, amounts)
    petition = _petition(session)
    assert petition["Check Box22"] == line_19
    assert petition["Check Box23"] == line_20


def test_line_19_reads_what_the_filer_owns_and_line_20_what_they_owe(session):
    # Assets and debts fall in different ranges, so a line that read the other total fails.
    _assets(session, ["10000.00"])
    _debts(session, ["75000.00"])
    petition = _petition(session)
    assert petition["Check Box22"] == "/0-50000"
    assert petition["Check Box23"] == "/50001-100000"


def test_header_name_prints_on_pages_2_to_9(session):
    pdf = PDFFormFiller().fill("form_101", _petition(session))
    # A viewer draws each widget's own appearance stream, so every page must have one.
    pages = []
    for number, page in enumerate(pypdf.PdfReader(BytesIO(pdf)).pages, start=1):
        for annot in page.get("/Annots") or []:
            widget = annot.get_object()
            if qualified_name(field_of(widget)) != "Debtor1.Name":
                continue
            appearance = widget.get("/AP")
            if appearance is not None and b"Jane Q Doe" in appearance["/N"].get_data():
                pages.append(number)
    assert pages == list(range(2, 10))


def test_the_filers_phone_prints_as_their_contact_phone_not_a_cell_phone(session):
    # The intake never asks whether the number is a cell, and a preparer's phone
    # belongs on Form 119, not here.
    _answer(session, "preparer_phone", "773-555-0199")
    petition = _petition(session)
    assert petition["Debtor1.Contact phone_2"] == "312-555-0100"
    assert "Debtor1.Cell phone" not in petition


def test_a_filer_without_a_mailing_address_leaves_the_mailing_block_blank(session):
    petition = _petition(session)
    assert "Debtor1.City_2" not in petition
    assert "Debtor1.ZIP Code_2" not in petition


def test_the_mailing_address_prints_in_the_mailing_block_and_nowhere_else(session):
    _answer(session, "mailing_city", "Evanston")
    _answer(session, "mailing_zip", "60201")
    petition = _petition(session)
    assert petition["Debtor1.City_2"] == "Evanston"
    assert petition["Debtor1.ZIP Code_2"] == "60201"
    # City_2 is the city of a hazardous property on line 14.
    assert "City_2" not in petition


def test_line_2_other_names_and_a_second_street_line_stay_blank(session):
    # The intake asks for no other names and has one street line.
    petition = _petition(session)
    other_names = [
        f"Debtor1.{part} name_{n}" for part in ("First", "Middle", "Last") for n in (3, 5)
    ]
    assert [box for box in [*other_names, "Debtor1.Street1"] if box in petition] == []
    # The filer's name and street still print on the lines that ask for them.
    assert petition["Debtor1.First name"] == "Jane"
    assert petition["Debtor1.Street"] == "123 Main St"


def test_an_answer_prints_once_and_never_in_the_box_beside_it(session):
    SOFAReport.objects.create(session=session, has_business=True)
    _answer(session, "attorney_gate", "yes", form_type="form_107")
    answers = {
        "business_name": "Doe Cleaning",
        "employer_ein": "12-3456789",
        "business_street": "9 Elm St",
        "hazard_description": "Leaking tank",
        "hazard_reason": "It may explode",
        "hazard_street": "1 Oak St",
        "attorney_street": "5 Court St",
    }
    for key, value in answers.items():
        _answer(session, key, value)
    petition = _petition(session)
    # Each answer still prints in its own box.
    assert petition["Debtor1.Business name"] == "Doe Cleaning"
    assert petition["Debtor1.Employer Identification Number1"] == "12-3456789"
    assert petition["Business Street address"] == "9 Elm St"
    assert petition["What is the hazard1"] == "Leaking tank"
    assert petition["If immediate attention is needed why is it needed1"] == "It may explode"
    assert petition["Street_6"] == "1 Oak St"
    assert petition["Attorney.Street address_2"] == "5 Court St"
    repeats = [
        "Debtor1.Business name_3",
        "Debtor1.Employer Identification Number2",
        "Business Street address2",
        "What is the hazard2",
        "If immediate attention is needed why is it needed2",
        "Street_7",
        "Attorney.Street address_3",
    ]
    assert [box for box in repeats if box in petition] == []


def test_line_10_never_names_the_filer_as_the_other_debtor(session):
    # Line 10 asks about a case filed by a spouse, partner or affiliate, not the filer.
    _answer(session, "prior_bankruptcy_gate", "yes")
    petition = _petition(session)
    assert "Debtor" not in petition
    assert "Debtor_2" not in petition
