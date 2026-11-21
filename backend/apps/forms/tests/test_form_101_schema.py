"""
What the petition (Form 101) prints from the intake (step 2 spec §6.4, Appendix A.1; rewritten
for the 11/26 revision in forms step 4b, 2026-11-20, step 4 spec §8).

Business intent: the filer signs Form 101 under penalty of perjury, so each box shows
only what its line asks. It ticks Chapter 7 and the ranges on lines 18-20, and prints
the filer's name in the page header and the filer's own phone. A value never spills
into a neighbouring box, and a line the intake doesn't ask stays blank (DIG-76, DIG-68).
On 11/26 every choice is its own box, so a box ticks only for the filer's own answer and
never shows a No the filer didn't give (§5.3).
"""

import hashlib
import importlib.util
import json
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pypdf
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve, resolve_parts
from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    FilingFee,
    Household,
    IntakeSession,
    PetitionAnswers,
)

User = get_user_model()

ROOT = settings.BASE_DIR.parent
TOOL = ROOT / "data/forms/field_index/tools/build_form_101.py"
SCHEMA = ROOT / "data/forms/schemas/form_101.json"
LIMITS = ROOT / "data/forms/schemas/form_101.limits.json"
ADDENDUM = ROOT / "data/forms/field_index/audit/step2_verification.json"
TEMPLATE = Path(settings.PDF_FORMS_DIRECTORY) / "form_b101.pdf"
INDEX = json.loads((settings.FORM_INDEX_DIRECTORY / "form_b101.index.json").read_text())

# The widest amount one row can hold (DecimalField(12, 2)).
WIDEST_ROW = "9999999999.99"

# The 112 names no binding fills (271 names, 159 bound by 160 bindings: District twice; §8, plan
# Task 4): every Debtor 2 box ("9 xx  xx" among them), the 8 case-number boxes, the
# amended-filing box, the other six chapter boxes, Debtor 1's second EIN, four second lines
# (line 12's business address line `1`, which no key asks: step 1's street label says to
# include the unit; and line 14's hazard, reason and address second lines `undefined_20`,
# `undefined_21` and `1_2`, blank by spec §6.5), line 13's other three choices, line 17's No
# and its estimate (4i), the three /Sig fields, the 13 date boxes, the stray "Part 7 Sign
# Below", the attorney block, the notice page's two signature lines, the cell phones and Debtor
# 2's contact boxes. Line 15's exigent explanation has no box of its own on 11/26, so
# `exigent_text` binds nothing.
BLANK_ON_PURPOSE = {
    # Debtor 2, pages 1 and 2
    "First name_2",
    "Middle name_2",
    "Last name_2",
    "Suffix Sr Jr II III_2",
    "First name_4",
    "Middle name_4",
    "Last name_4",
    "First name_6",
    "Middle name_6",
    "Last name_6",
    "Business name if applicable_3",
    "Business name if applicable_4",
    "xx_2",
    "undefined_4",
    "undefined_5",
    "undefined_6",
    "9 xx  xx",
    "undefined_11",
    "undefined_12",
    "undefined_13",
    "EIN_2",
    "undefined_15",
    "EIN_4",
    "undefined_17",
    "Number_3",
    "Street_3",
    "undefined_19",
    "City_3",
    "State_4",
    "ZIP Code_3",
    "County_2",
    "Number_4",
    "Street_4",
    "PO Box_2",
    "City_4",
    "State_5",
    "ZIP Code_4",
    "Over the last 180 days before filing this petition_2",
    "I have another reason Explain_2",
    "See 28 USC  1408 1_2",
    "See 28 USC  1408 2_2",
    "See 28 USC  1408 3_2",
    "See 28 USC  1408 4_2",
    # Debtor 2, line 15
    "I received a briefing from an approved credit_3",
    "I received a briefing from an approved credit_4",
    "I certify that I asked for credit counseling_2",
    "I am not required to receive a briefing about_2",
    "Incapacity_2",
    "Disability_2",
    "Active duty I am currently on active military_2",
    # The case number on every page, and the amended-filing box
    "Case number (if known)",
    "Case number if known",
    "Case number if known_2",
    "Case number if known_5",
    "Case number if known_6",
    "Case number if known_7",
    "Case number if known_8",
    "Case number if known_9",
    "Check if this is an",
    # The other six chapter boxes
    "Chapter 11",
    "Chapter 12",
    "Chapter 13",
    "Chapter 11_2",
    "Chapter 12_2",
    "Chapter 13_2",
    # Debtor 1's second EIN, and the unlabeled second lines
    "EIN_3",
    "undefined_16",
    "undefined_18",
    "1",
    "1_2",
    "undefined_20",
    "undefined_21",
    # Line 13's other choices, line 17's No and its estimate (4i)
    "No_5",
    "Yes I am filing under Chapter 11 I am a small business debtor according to the definition "
    "in the",
    "Yes  I am filing under Chapter 11 I am a debtor according to the definition in  11821 of "
    "the Bankruptcy",
    "No I am not filing under Chapter 7 Go to line 18",
    "administrative expenses are paid that funds will be available to distribute to unsecured "
    "creditors",
    # Part 7: the signatures, the dates, the stray heading box and the attorney block
    "Part 7 Sign Below",
    "Signature of Debtor 1",
    "Signature of Debtor 2",
    "MM",
    "DD",
    " YYYY",
    "MM  DD",
    " YYYY_2",
    "Signature of Attorney for Debtor",
    "MM_2",
    "fill_28",
    "DD_2",
    " YYYY_3",
    "Printed name",
    "Firm name",
    "Number_7",
    "Street_7",
    "1_3",
    "2_3",
    "State_8",
    "ZIP Code_7",
    "Contact phone",
    "Email address",
    "Bar number",
    "State_9",
    # The notice page: the signature lines, the dates, the cell phones and Debtor 2's boxes
    "undefined_23",
    "undefined_24",
    "MM  DD_2",
    " YYYY_4",
    "MM_3",
    "DD  YYYY",
    "Contact phone_3",
    "Cell phone",
    "Cell phone_2",
    "Email address_3",
}

LEGAL_REVIEW = {
    "I received a briefing from an approved credit",
    "I received a briefing from an approved credit_2",
    "I certify that I asked for credit counseling",
    "I am not required to receive a briefing about",
    "Incapacity",
    "Disability",
    "Active duty I am currently on active military",
    "Yes Go to line 17",
}


def _tool():
    spec = importlib.util.spec_from_file_location("build_form_101", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _box(label):
    """The full name of the one widget the index labels so."""
    (row,) = [r for r in INDEX if r["label"] == label]
    return row["full_name"]


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


def _petition_row(session, **answers):
    record = PetitionAnswers(session=session)
    record.merge(answers)
    record.save()
    return record


def _petition(session):
    return resolve(load_schema("form_101"), session)


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
            ab_line="53",
            description=f"Asset {i}",
            current_value=Decimal(amount),
        )
        for i, amount in enumerate(amounts)
    )


def _ticked(values, names):
    return {name for name in names if values.get(name) == "/On"}


def test_the_schema_and_its_rows_and_caps_are_what_the_tool_writes():
    # A hand edit to a binding, a row or a cap would be undone by the next run (4b-R5, 4b-R10).
    tool = _tool()
    index = json.loads((settings.FORM_INDEX_DIRECTORY / "form_b101.index.json").read_text())
    sha256 = hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()
    schema, rows, limits = tool.schema(index, sha256), tool.addendum_rows(index), tool.limits(index)

    assert json.loads(SCHEMA.read_text()) == schema
    assert SCHEMA.read_text() == tool.dumps(schema)
    addendum_text = ADDENDUM.read_text()
    assert [r for r in json.loads(addendum_text) if tool.owned(r)] == rows
    assert addendum_text == tool.merged_text(addendum_text, rows)
    assert LIMITS.read_text() == tool.dumps(limits)
    # The record caps the filer's text by the same file (4b-R10).
    assert PetitionAnswers.TEXT_LIMITS == limits["limits"]
    assert PetitionAnswers.TEXT_LABELS == limits["labels"]


def test_every_widget_is_bound_or_blank_on_purpose():
    bound = {f.pdf_field for f in load_schema("form_101").fields}
    names = {r["full_name"] for r in INDEX}
    assert bound & BLANK_ON_PURPOSE == set()
    assert bound | BLANK_ON_PURPOSE == names
    assert len(BLANK_ON_PURPOSE) == 112


def test_a_session_with_no_record_prints_the_06_24_data_and_nothing_else(session):
    # Until a step asks Form 101's questions (4b-ii), every session prints what 06/24 printed:
    # the intake's own data on the 11/26 boxes, the constants, line 8 and lines 18-20.
    Household.objects.create(session=session, county="Cook")
    FilingFee.objects.create(session=session, payment_choice="pay_in_full")
    _debts(session, ["75000.00"])
    on = "/On"
    expected = {
        "District@1:T1": "Northern",
        "State": "Illinois",
        "Chapter 7": on,
        "Chapter 7_2": on,
        "First name": "Jane",
        "Middle name": "Q",
        "Last name": "Doe",
        "xx": "3",
        "undefined": "4",
        "undefined_2": "5",
        "undefined_3": "6",
        "Number": "123",
        "Street": "Main St",
        "City": "Chicago",
        "State_2": "IL",
        "ZIP Code": "60601",
        "County": "Cook",
        _box("Line 8: pay the entire fee when filing"): on,
        "No_4": on,
        _box("Line 17: Yes, filing under Chapter 7"): on,
        "149": on,
        "050000": on,
        "50001100000_3": on,
        "Contact phone_2": "312-555-0100",
        "Email address_2": "jane@example.com",
    }
    for page in (2, 4, 7):
        suffix = {2: "", 4: "_2", 7: "_3"}[page]
        expected |= {
            f"First Name{suffix}": "Jane",
            f"Middle Name{suffix}": "Q",
            f"Last Name{suffix}": "Doe",
        }
    for name in ("Debtor 1", "Debtor 1_2", "Debtor 1_3", "Debtor 1_4"):
        expected[name] = "Jane Q Doe"
    assert _petition(session) == expected


def test_petition_ticks_chapter_7_on_both_pages(session):
    petition = _petition(session)
    assert petition["Chapter 7"] == "/On"
    assert petition["Chapter 7_2"] == "/On"
    assert {"Chapter 11", "Chapter 12", "Chapter 13", "Chapter 11_2"} & set(petition) == set()


def test_line_13_says_not_filing_under_chapter_11_for_everyone(session):
    petition = _petition(session)
    assert petition["No_4"] == "/On"
    assert "No_5" not in petition


def test_the_court_prints_on_the_cover_and_not_in_line_9(session):
    _petition_row(
        session,
        prior_bankruptcy_answer="no",
        prior_cases=[{"district": "Southern", "filed_on": "01/02/2020", "case_number": "20-1"}],
    )
    petition = _petition(session)
    assert petition["District@1:T1"] == "Northern"
    assert petition["State"] == "Illinois"
    # A bare "District" would fill line 9's box too.
    assert "District" not in petition
    assert [key for key in petition if key.startswith("District@3:")] == []


@pytest.mark.parametrize("count,box", [(1, "149"), (49, "149"), (50, "5099")])
def test_line_18_ticks_the_one_box_the_count_falls_in(session, count, box):
    _debts(session, ["100.00"] * count)
    line_18 = {r["full_name"] for r in INDEX if r["line"] == "18"}
    assert _ticked(_petition(session), line_18) == {box}


def test_a_filer_with_no_creditors_leaves_line_18_blank(session):
    line_18 = {r["full_name"] for r in INDEX if r["line"] == "18"}
    assert _ticked(_petition(session), line_18) == set()


@pytest.mark.parametrize(
    "amounts,line_19,line_20",
    [
        # Nothing owned or owed is the lowest range, not a blank line.
        ([], "050000", "050000_2"),
        (["50000.00"], "050000", "050000_2"),
        # Cents above a range's top belong to the next range up.
        (["50000.01"], "50001100000_2", "50001100000_3"),
        (["100000000.50"], "100000001500 million", "100000001500 million_2"),
        ([WIDEST_ROW] * 6, "More than 50 billion", "More than 50 billion_2"),
    ],
)
def test_lines_19_and_20_tick_their_own_range(session, amounts, line_19, line_20):
    _assets(session, amounts)
    _debts(session, amounts)
    petition = _petition(session)
    assert _ticked(petition, {r["full_name"] for r in INDEX if r["line"] == "19"}) == {line_19}
    assert _ticked(petition, {r["full_name"] for r in INDEX if r["line"] == "20"}) == {line_20}


def test_line_19_reads_what_the_filer_owns_and_line_20_what_they_owe(session):
    # Assets and debts fall in different ranges, so a line that read the other total fails.
    _assets(session, ["10000.00"])
    _debts(session, ["75000.00"])
    petition = _petition(session)
    assert _ticked(petition, {r["full_name"] for r in INDEX if r["line"] == "19"}) == {"050000"}
    assert _ticked(petition, {r["full_name"] for r in INDEX if r["line"] == "20"}) == {
        "50001100000_3"
    }


def test_the_ssn_last_four_print_one_digit_per_box_and_the_whole_number_appears_nowhere(session):
    petition = _petition(session)
    assert [petition[box] for box in ("xx", "undefined", "undefined_2", "undefined_3")] == list(
        "3456"
    )
    assert [v for v in petition.values() if "900" in v or v == "3456"] == []


def test_the_mailing_block_prints_only_under_a_mailing_yes_and_never_in_the_hazard_city(session):
    mailing = {
        "mailing_street": "9 Elm St",
        "mailing_city": "Evanston",
        "mailing_state": "IL",
        "mailing_zip": "60201",
        "mailing_po_box": "1234",
    }
    record = _petition_row(session, mailing_answer="yes", **mailing)
    petition = _petition(session)
    assert petition["Number_2"] == "9"
    assert petition["Street_2"] == "Elm St"
    assert petition["PO Box"] == "1234"
    assert petition["City_2"] == "Evanston"
    assert petition["State_3"] == "IL"
    assert petition["ZIP Code_2"] == "60201"
    # 2_2 is the city of a hazardous property on line 14.
    assert "2_2" not in petition

    record.merge({"mailing_answer": "no"})
    record.save()
    petition = _petition(session)
    mailing_boxes = {"Number_2", "Street_2", "PO Box", "City_2", "State_3", "ZIP Code_2"}
    assert mailing_boxes & set(petition) == set()


def test_line_2_prints_the_other_names_the_filer_gave_and_blank_for_a_no(session):
    # Line 2 was blank by design on 06/24; 11/26 prints what the filer gave, and nothing under No.
    names = [
        {"first": "Janet", "middle": "R", "last": "Roe"},
        {"first": "Jan", "middle": "", "last": "Doe-Roe"},
    ]
    record = _petition_row(
        session,
        other_names_answer="yes",
        other_names=names,
        other_business_names=[{"name": "Demo Cleaning"}],
    )
    petition = _petition(session)
    assert (petition["First name_3"], petition["Middle name_3"], petition["Last name_3"]) == (
        "Janet",
        "R",
        "Roe",
    )
    assert (petition["First name_5"], petition["Last name_5"]) == ("Jan", "Doe-Roe")
    assert "Middle name_5" not in petition
    assert petition["Business name if applicable"] == "Demo Cleaning"
    assert "Business name if applicable_2" not in petition
    # The filer's own name still prints on line 1.
    assert petition["First name"] == "Jane"

    record.merge({"other_names_answer": "no"})
    record.save()
    petition = _petition(session)
    line_2 = {r["full_name"] for r in INDEX if r["line"] == "2"}
    assert line_2 & set(petition) == set()


def test_a_fourth_prior_case_goes_to_the_sheet_and_row_1_fills_one_widget(session):
    cases = [
        {"district": f"District {n}", "filed_on": f"0{n}/01/2020", "case_number": f"20-{n}"}
        for n in range(1, 5)
    ]
    _petition_row(session, prior_bankruptcy_answer="yes", prior_cases=cases)
    parts = resolve_parts(load_schema("form_101"), session)["parts"]
    form = parts[0]["values"]
    assert form["District@3:T11"] == "District 1"
    assert (form["District_2"], form["When_2"], form["Case number_2"]) == (
        "District 2",
        "02/01/2020",
        "20-2",
    )
    assert form["District_3"] == "District 3"
    # Row 1's tagged key fills line 9's widget alone: the cover keeps the court.
    assert form["District@1:T1"] == "Northern"
    assert "District" not in form
    (sheet,) = [p for p in parts if p["kind"] == "sheet"]
    assert sheet["group"] == "prior_cases"
    assert sheet["title"].endswith("line 9")
    assert sheet["rows"] == [{"line": "9.4", "cells": ["District 4", "04/01/2020", "20-4"]}]


LINE_10_CELLS = ("debtor", "relationship to you", "district", "when", "case number")


def _line_10_row(values, n):
    return tuple(values.get(_box(f"Line 10: case {n}, {cell}")) for cell in LINE_10_CELLS)


def test_line_10_prints_two_cases_in_their_boxes_a_third_on_the_sheet_and_none_under_a_no(session):
    # Line 10 names someone else's case: a stored name must never print under the filer's No.
    cases = [
        {
            "debtor": f"Demo Partner Number {n}",
            "relationship": "Business partner",
            "district": "Northern Illinois",
            "filed_on": f"0{n}/15/2025",
            "case_number": f"25-bk-0000{n}",
        }
        for n in (1, 2, 3)
    ]
    record = _petition_row(session, pending_case_answer="yes", pending_cases=cases)
    document = resolve_parts(load_schema("form_101"), session)
    form = document["parts"][0]["values"]
    for n in (1, 2):
        assert _line_10_row(form, n) == (
            f"Demo Partner Number {n}",
            "Business partner",
            "Northern Illinois",
            f"0{n}/15/2025",
            f"25-bk-0000{n}",
        )
    (sheet,) = [p for p in document["parts"] if p["kind"] == "sheet"]
    assert sheet["group"] == "pending_cases"
    assert sheet["title"].endswith("line 10")
    assert sheet["rows"] == [
        {
            "line": "10.3",
            "cells": [
                "Demo Partner Number 3",
                "Business partner",
                "Northern Illinois",
                "03/15/2025",
                "25-bk-00003",
            ],
        }
    ]
    # The boxes and the sheet's columns (When is the narrowest, 62 pt) take these whole.
    PDFFormFiller().check("form_101", document)

    record.merge({"pending_case_answer": "no"})
    record.save()
    parts = resolve_parts(load_schema("form_101"), session)["parts"]
    assert [p for p in parts if p["kind"] == "sheet"] == []
    line_10 = {_box(f"Line 10: case {n}, {cell}") for n in (1, 2) for cell in LINE_10_CELLS}
    assert line_10 & set(parts[0]["values"]) == set()


# Each bound radio: its key, its name, and the states its No and Yes kids carry in the index.
RADIOS = [
    ("prior_bankruptcy_answer", "Line 9: No", "/No", "/Yes"),
    ("pending_case_answer", "Line 10: No", "/No_2", "/Yes_2"),
    ("rents_residence", "Line 11: rent your residence, No", "/No_3", "/Yes_3"),
    ("hazard_answer", "Line 14: No", "/No_6", "/Yes_4"),
    ("aware_consequences", "Notice page: aware of the consequences, No", "/No_8", "/Yes_6"),
    ("aware_fraud", "Notice page: aware that fraud is a crime, No", "/No_9", "/Yes_7"),
]


@pytest.mark.parametrize("key,label,no,yes", RADIOS)
def test_every_radio_prints_neither_state_for_an_absent_key(session, key, label, no, yes):
    name = _box(label)
    assert name not in _petition(session)
    record = _petition_row(session, **{key: "no"})
    assert _petition(session)[name] == no
    record.merge({key: "yes"})
    record.save()
    assert _petition(session)[name] == yes
    # The seventh radio, line 17's estimate, is unbound until 4i.
    assert _box("Line 17: funds will be available, No") not in _petition(session)


def _boxes(*labels):
    return {label: _box(label) for label in labels}


# A single-box group: the answers it needs first, its key, each value → the labels it ticks.
SINGLE_BOX_GROUPS = {
    "line_6": (
        {},
        "venue_choice",
        {
            "lived_here": {"Debtor 1, line 6: lived in this district longer"},
            "other": {"Debtor 1, line 6: another reason"},
        },
    ),
    "line_11_eviction": (
        {"rents_residence": "yes"},
        "eviction_judgment",
        {
            "no": {"Line 11: eviction judgment, No"},
            "yes": {"Line 11: eviction judgment, Yes"},
        },
    ),
    "line_12": (
        {},
        "sole_proprietor_answer",
        {"no": {"Line 12: No"}, "yes": {"Line 12: Yes"}},
    ),
    "line_12_kind": (
        {"sole_proprietor_answer": "yes"},
        "business_kind",
        {
            "health_care": {"Line 12: Health Care Business"},
            "single_asset": {"Line 12: Single Asset Real Estate"},
            "stockbroker": {"Line 12: Stockbroker"},
            "commodity_broker": {"Line 12: Commodity Broker"},
            "none": {"Line 12: None of the above"},
        },
    ),
    "line_15": (
        {},
        "credit_counseling",
        {
            "certificate": {"Debtor 1, line 15: a briefing and a certificate"},
            "no_certificate": {"Debtor 1, line 15: a briefing and no certificate"},
            "exigent": {"Debtor 1, line 15: asked for counseling, a 30-day waiver"},
            "not_required": {"Debtor 1, line 15: not required to receive a briefing"},
            # The app-only state prints nothing (B19).
            "not_yet": set(),
        },
    ),
    "line_15_reason": (
        {"credit_counseling": "not_required"},
        "not_required_reason",
        {
            "incapacity": {
                "Debtor 1, line 15: not required to receive a briefing",
                "Debtor 1, line 15: not required, incapacity",
            },
            "disability": {
                "Debtor 1, line 15: not required to receive a briefing",
                "Debtor 1, line 15: not required, disability",
            },
            "active_duty": {
                "Debtor 1, line 15: not required to receive a briefing",
                "Debtor 1, line 15: not required, active duty",
            },
        },
    ),
    "line_16": (
        {},
        "debt_nature",
        {
            # The form's own routing: "Yes. Go to line 17." leaves 16b blank.
            "consumer": {"Line 16a: consumer debts, Yes"},
            "business": {"Line 16a: consumer debts, No", "Line 16b: business debts, Yes"},
            "neither": {"Line 16a: consumer debts, No", "Line 16b: business debts, No"},
        },
    ),
    "notice_page": (
        {},
        "paid_preparer",
        {
            "no": {"Notice page: paid a non-attorney to help, No"},
            "yes": {"Notice page: paid a non-attorney to help, Yes"},
        },
    ),
}


# The one group whose base answer ticks a box itself: line 15's "not required" is the filer's
# own answer before its reason is given.
BASE_TICKS = {"line_15_reason": {"Debtor 1, line 15: not required to receive a briefing"}}


@pytest.mark.parametrize("group", sorted(SINGLE_BOX_GROUPS))
def test_check_one_holds_for_every_single_box_group(session, group):
    # §18.2: each value ticks its own box (two where the form asks a parent and a reason) and an
    # absent answer ticks none: never a No the filer didn't give (§5.3).
    base, key, ticks = SINGLE_BOX_GROUPS[group]
    labels = set().union(*ticks.values())
    names = {_box(label) for label in labels}
    record = _petition_row(session, **base)
    # Before the key is answered only the base answer's own box ticks (BASE_TICKS).
    parent = {_box(label) for label in BASE_TICKS.get(group, set())}
    assert _ticked(_petition(session), names) == parent
    for value, expected in ticks.items():
        record.merge({key: value})
        record.save()
        assert _ticked(_petition(session), names) == {_box(label) for label in expected}, value


def test_line_15s_reason_prints_only_under_not_required(session):
    _petition_row(session, credit_counseling="certificate", not_required_reason="disability")
    assert "Disability" not in _petition(session)


def test_line_8_ticks_the_fee_choice_the_filer_made(session):
    labels = (
        "Line 8: pay the entire fee when filing",
        "Line 8: pay the fee in installments",
        "Line 8: ask that the fee be waived",
    )
    names = {_box(label) for label in labels}
    assert _ticked(_petition(session), names) == set()
    fee = FilingFee.objects.create(session=session)
    for choice, label in zip(("pay_in_full", "installments", "waiver"), labels, strict=True):
        fee.payment_choice = choice
        fee.save()
        assert _ticked(_petition(session), names) == {_box(label)}


def test_detail_boxes_print_only_under_their_yes(session):
    details = {
        "hazard_what": "Leaking tank",
        "hazard_why": "It may explode",
        "hazard_street": "1 Oak St",
        "hazard_city": "Joliet",
        "hazard_state": "IL",
        "hazard_zip": "60431",
        "business_name": "Demo Cleaning",
        "business_street": "9 Elm St",
        "business_city": "Aurora",
        "business_state": "IL",
        "business_zip": "60505",
        "business_kind": "none",
        "preparer_name": "Demo Preparer",
        "debt_nature_text": "Taxes",
    }
    hazard = ("What is the hazard", "If immediate attention is needed why is it needed")
    hazard_address = ("Number_6", "Street_6", "2_2", "State_7", "ZIP Code_6")
    business = ("Name of business if any", "Number_5", "Street_5", "2", "State_6", "ZIP Code_5")
    detail_boxes = {*hazard, *hazard_address, *business, "undefined_22"}
    record = _petition_row(
        session,
        hazard_answer="yes",
        sole_proprietor_answer="yes",
        paid_preparer="yes",
        debt_nature="neither",
        **details,
    )
    petition = _petition(session)
    assert petition["What is the hazard"] == "Leaking tank"
    assert (petition["Number_6"], petition["Street_6"], petition["2_2"]) == (
        "1",
        "Oak St",
        "Joliet",
    )
    assert (petition["Name of business if any"], petition["2"]) == ("Demo Cleaning", "Aurora")
    assert petition["undefined_22"] == "Demo Preparer"
    assert petition[_box("Line 16c: the type of debts")] == "Taxes"

    record.merge(
        {
            "hazard_answer": "no",
            "sole_proprietor_answer": "no",
            "paid_preparer": "no",
            "debt_nature": "consumer",
        }
    )
    record.save()
    petition = _petition(session)
    assert detail_boxes & set(petition) == set()
    assert _box("Line 16c: the type of debts") not in petition
    assert _box("Line 12: None of the above") not in petition


@pytest.mark.parametrize(
    "gate,no,stored,boxes",
    [
        (
            "itin_answer",
            "no",
            {"itin": "900-70-1234"},
            ("undefined_7", "undefined_8", "undefined_9", "undefined_10"),
        ),
        (
            "venue_choice",
            "lived_here",
            {"venue_reason": "I moved here for work two months ago"},
            ("See 28 USC  1408 1", "See 28 USC  1408 2"),
        ),
    ],
)
def test_a_value_stored_under_a_no_prints_nothing(session, gate, no, stored, boxes):
    # Ruling T4-gates: the digit and venue rules don't read their gate, so the schema does.
    yes = "other" if gate == "venue_choice" else "yes"
    record = _petition_row(session, **{gate: yes}, **stored)
    assert set(boxes[:1]) <= set(_petition(session))
    record.merge({gate: no})
    record.save()
    assert set(boxes) & set(_petition(session)) == set()


@pytest.mark.parametrize(
    "line_12", [{"sole_proprietor_answer": "no"}, {}], ids=["no", "unanswered"]
)
def test_the_ein_prints_whatever_line_12_says(session, line_12):
    # Ruling T4-gates (corrected): spec §6.1 row 1e and §8 line 4 ask the EIN with no gate, so a
    # filer with an EIN who answers line 12 No, or hasn't answered it yet, still sees line 4.
    _petition_row(session, ein="12-3456789", **line_12)
    petition = _petition(session)
    assert (petition.get("EIN"), petition.get("undefined_14")) == ("12", "3456789")


# The running header's name-part boxes on pages 2, 4 and 7, by part (46, 64 and 97 pt wide).
HEADER_PARTS = {
    part: [_box(f"Header, page {page}: Debtor 1 {part} name") for page in (2, 4, 7)]
    for part in ("first", "middle", "last")
}


def _name(session, **parts):
    debtor = session.debtor_info  # the fixture's own row, which the session holds
    for part, text in parts.items():
        setattr(debtor, f"{part}_name", text)
    debtor.save()


def test_a_first_name_too_wide_for_the_header_still_prints_the_form(session):
    # Ruling T4-header (provisional): 06/24 printed this name, so 11/26 must not refuse the
    # form over a 46 pt header box. Line 1 and the whole-name headers print it whole; only the
    # header's first-name box is left blank, never cut or turned into an initial.
    _name(session, first="Maria Guadalupe")
    petition = _petition(session)
    PDFFormFiller().check("form_101", petition)
    assert petition["First name"] == "Maria Guadalupe"
    for name in ("Debtor 1", "Debtor 1_2", "Debtor 1_3", "Debtor 1_4"):
        assert petition[name] == "Maria Guadalupe Q Doe"
    assert set(HEADER_PARTS["first"]) & set(petition) == set()
    assert [petition[box] for box in HEADER_PARTS["middle"]] == ["Q"] * 3
    assert [petition[box] for box in HEADER_PARTS["last"]] == ["Doe"] * 3


def test_a_first_name_that_fits_prints_in_all_three_header_boxes(session):
    _name(session, first="Mary")
    petition = _petition(session)
    assert [petition[box] for box in HEADER_PARTS["first"]] == ["Mary"] * 3


def _fits_every_header_box(part, text):
    """Whether check() takes text in each of the part's three header boxes."""
    try:
        PDFFormFiller().check("form_101", dict.fromkeys(HEADER_PARTS[part], text))
    except ValueTooLong:
        return False
    return True


@pytest.mark.parametrize("part", ["middle", "last"])
def test_a_name_part_at_the_header_boxs_edge_prints_and_one_letter_more_leaves_it_blank(
    session, part
):
    # The edge is check()'s own: the longest run of the letter its three boxes take.
    n = 1
    while _fits_every_header_box(part, "a" * (n + 1)):
        n += 1
    for text, shown in (("a" * n, True), ("a" * (n + 1), False)):
        _name(session, **{part: text})
        petition = _petition(session)
        PDFFormFiller().check("form_101", petition)
        assert petition[f"{part.capitalize()} name"] == text
        printed = [petition.get(box) for box in HEADER_PARTS[part]]
        assert printed == ([text] * 3 if shown else [None] * 3), (len(text), printed)


def _capped_answers(key, text):
    """The answers that show the box `key` prints in, with `text` in it."""
    gate = {
        "mailing": {"mailing_answer": "yes"},
        "business": {"sole_proprietor_answer": "yes"},
        "hazard": {"hazard_answer": "yes"},
        "venue": {"venue_choice": "other"},
        "debt": {"debt_nature": "neither"},
        "preparer": {"paid_preparer": "yes"},
    }.get(key.partition("_")[0], {})
    return {**gate, key: text}


# An answer a filer would type for each capped key: the browser's maxLength is the cap (spec
# §5.7), so a cap below one of these leaves the filer no way to type their own answer.
ORDINARY_ANSWERS = {
    "name_suffix": "Jr.",
    "mailing_street": "1234 N Sheridan Rd Apt 5B",
    "mailing_po_box": "12345",
    "mailing_city": "Arlington Heights",
    "mailing_state": "IL",
    "mailing_zip": "60201",
    "venue_reason": (
        "I moved to Chicago in March for a new job, and my home, my work and my family are all "
        "here now"
    ),
    "business_name": "Demo Cleaning and Restoration Services",
    "business_street": "4500 W Lawrence Ave Suite 200",
    "business_city": "Arlington Heights",
    "business_state": "IL",
    "business_zip": "60630-1234",
    "hazard_what": "The roof is falling in after a storm",
    "hazard_why": "Rain gets into the house and the ceiling may fall",
    "hazard_street": "1234 N Sheridan Rd",
    "hazard_city": "Chicago",
    "hazard_state": "IL",
    "hazard_zip": "60640",
    "debt_nature_text": "Wages I owe a household helper",
    "preparer_name": "Demo Preparer Services of Chicago",
}


def test_every_capped_key_has_an_ordinary_answer():
    assert set(ORDINARY_ANSWERS) == set(PetitionAnswers.TEXT_LIMITS)


@pytest.mark.parametrize("key", sorted(ORDINARY_ANSWERS))
def test_an_ordinary_answer_is_within_its_cap_and_prints(session, key):
    answer = ORDINARY_ANSWERS[key]
    assert len(answer) <= PetitionAnswers.TEXT_LIMITS[key], (answer, len(answer))
    _petition_row(session, **_capped_answers(key, answer))
    PDFFormFiller().check("form_101", _petition(session))


@pytest.mark.parametrize("key", sorted(ORDINARY_ANSWERS))
def test_an_ordinary_answer_typed_in_capitals_prints(session, key):
    # Some filers type every answer in capitals. The caps are measured at ordinary-word width,
    # so only a long answer of wide letters is refused at Generate; an ordinary one in capitals
    # still prints.
    _petition_row(session, **_capped_answers(key, ORDINARY_ANSWERS[key].upper()))
    PDFFormFiller().check("form_101", _petition(session))


def _measuring_letter(key):
    """
    The widest letter a key's cap answers for: a digit for a ZIP code, W for a state's
    capitals, and for ordinary words o, which Helvetica draws as wide as a digit (a street of
    digits alone would go to the Number box).
    """
    if key.endswith("_zip"):
        return "0"
    return "W" if key.endswith("_state") else "o"


@pytest.mark.parametrize("key", sorted(set(PetitionAnswers.TEXT_LIMITS) - {"venue_reason"}))
def test_every_answer_at_its_cap_of_its_measuring_letter_prints_without_refusal(session, key):
    # 4b-R10: a ZIP code or a state the page lets through never fails at Generate, and nor do
    # ordinary words; a text mostly of wider letters may, and check() names the step. The
    # venue reason, which wraps at spaces, is tested at its cap in ordinary words below.
    cap = PetitionAnswers.TEXT_LIMITS[key]
    _petition_row(session, **_capped_answers(key, _measuring_letter(key) * cap))
    PDFFormFiller().check("form_101", _petition(session))


@pytest.mark.parametrize("key", sorted(set(PetitionAnswers.TEXT_LIMITS) - {"venue_reason"}))
def test_no_cap_leaves_room_for_one_more_of_its_measuring_letter(session, key):
    # The cap is the most that fit, not a safe guess below it: one letter more is refused.
    cap = PetitionAnswers.TEXT_LIMITS[key]
    _petition_row(session, **_capped_answers(key, _measuring_letter(key) * (cap + 1)))
    with pytest.raises(ValueTooLong):
        PDFFormFiller().check("form_101", _petition(session))


def _ordinary_venue_reason(length):
    """An ordinary reason in mixed-case words, cut to exactly `length` characters."""
    words = (ORDINARY_ANSWERS["venue_reason"] + " ") * 3
    reason = words[:length]
    return reason if not reason.endswith(" ") else reason[:-1] + "s"


def test_an_ordinary_venue_reason_at_its_cap_prints_whole_on_the_four_lines(session):
    # Ruling T4-caps (method A): the venue reason's cap is two lines' worth of digit-wide
    # letters, so a reason of ordinary words at the cap wraps onto the four lines and prints
    # whole, however its words break.
    from apps.forms.services.derivations import _venue_reason_lines

    reason = _ordinary_venue_reason(PetitionAnswers.TEXT_LIMITS["venue_reason"])
    assert len(reason) == PetitionAnswers.TEXT_LIMITS["venue_reason"]
    _petition_row(session, venue_choice="other", venue_reason=reason)
    lines = _venue_reason_lines(reason)
    assert " ".join(line for line in lines if line) == reason
    petition = _petition(session)
    assert [petition.get(f"See 28 USC  1408 {n}") for n in (1, 2, 3, 4)] == [
        line or None for line in lines
    ]
    PDFFormFiller().check("form_101", petition)


def _fits_a_venue_line(text):
    """Whether text prints whole in the venue reason's first box at 6 pt."""
    from apps.forms.services.text_fit import MIN_SIZE, _width, font_for, reverse_cmap_for
    from apps.forms.services.widgets import template_widgets

    (box,) = [w for w in template_widgets("form_b101.pdf") if w.full_name == "See 28 USC  1408 1"]
    font = font_for("form_b101.pdf", box.font)
    cmap = reverse_cmap_for("form_b101.pdf", box.font)
    return _width(font, cmap, text, MIN_SIZE) <= box.width - 4 * box.margin


def _o_words_at_cap(*word_lengths):
    """A venue reason exactly at its cap: words of o (a digit's width), these lengths by turns."""
    cap = PetitionAnswers.TEXT_LIMITS["venue_reason"]
    words, length = [], 0
    while length < cap:
        room = cap - length - (1 if words else 0)
        words.append("o" * min(word_lengths[len(words) % len(word_lengths)], room))
        length = len(" ".join(words))
    return " ".join(words)


def test_no_venue_reason_of_digit_wide_letters_at_its_cap_needs_a_fifth_line():
    # Ruling T4-caps: the cap is two lines' worth so that the worst word breaks still wrap onto
    # the four lines. Over every break two word lengths can make, taken by turns, a reason at
    # the cap prints whole.
    from apps.forms.services.derivations import _venue_reason_lines

    per_line = 1
    while _fits_a_venue_line("o" * (per_line + 1)):
        per_line += 1
    lengths = range(1, per_line + 1)
    spilled = [
        (first, second)
        for first in lengths
        for second in lengths
        if not all(map(_fits_a_venue_line, _venue_reason_lines(_o_words_at_cap(first, second))))
    ]
    assert spilled == []


def test_a_venue_reason_one_letter_over_its_cap_is_named_too_long(session):
    # The page's maxLength is the cap (spec §5.7); a longer reason saved some other way is a
    # detail gap naming line 6's box, and a reason at the cap is not.
    from apps.intake.petition import DETAIL_TOO_LONG, petition_step_gaps

    too_long = DETAIL_TOO_LONG.format(label="line 6's other reason")
    cap = PetitionAnswers.TEXT_LIMITS["venue_reason"]
    record = _petition_row(session, venue_choice="other", venue_reason=_ordinary_venue_reason(cap))
    assert too_long not in [gap.message for gap in petition_step_gaps(session)]
    record.merge({"venue_reason": _ordinary_venue_reason(cap) + "s"})
    record.save()
    assert too_long in [gap.message for gap in petition_step_gaps(session)]


@pytest.mark.parametrize(
    "key",
    sorted(k for k in PetitionAnswers.TEXT_LIMITS if not k.endswith(("_zip", "_state", "_reason"))),
)
def test_capitals_at_a_cap_are_refused_by_name_with_the_step_that_asks_them(session, key):
    # The caps of ordinary text are measured at ordinary-word width, so the page lets through
    # an answer all in wide capitals that its box can't hold. Generate then refuses it, naming
    # the box and the step that asks it (spec §5.7); it is never printed cut off.
    from apps.forms.services.answer_records import PETITION_STEP_OF_KEY

    _petition_row(session, **_capped_answers(key, "W" * PetitionAnswers.TEXT_LIMITS[key]))
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("form_101", _petition(session))
    assert (refused.value.step, refused.value.page) == (PETITION_STEP_OF_KEY[key], None)


@pytest.mark.slow
def test_the_form_fills_and_bakes_with_its_empty_signature_fields(session):
    pdf = PDFFormFiller().fill("form_101", _petition(session))
    drawn = read_drawn("form_101", pdf)
    assert [w.value for w in drawn if w.full_name == "First name"] == ["Jane"]
    assert {w.page for w in drawn if w.value == "Jane Q Doe"} == {3, 5, 6, 8}
    # A tick is the template's own filled square: Chapter 7 draws on both pages, 11 on neither.
    states = {w.full_name: w.state for w in drawn}
    assert (states["Chapter 7"], states["Chapter 7_2"], states["No_4"]) == ("/On", "/On", "/On")
    assert (states["Chapter 11"], states["Chapter 11_2"], states["No_5"]) == ("/Off",) * 3


@pytest.mark.slow
def test_the_header_name_prints_on_pages_2_to_8(session):
    pdf = PDFFormFiller().fill("form_101", _petition(session))
    header = {r["full_name"] for r in INDEX if r["label"].startswith("Header, page ")}
    header -= {r["full_name"] for r in INDEX if r["label"].endswith("case number")}
    assert len(header) == 13
    pages = {
        w.page
        for w in read_drawn("form_101", pdf)
        if w.full_name in header and w.value in ("Jane Q Doe", "Jane", "Q", "Doe")
    }
    assert pages == set(range(2, 9))


def test_lines_15_and_16a_carry_legal_review():
    # F-5: the boxes whose words make a legal claim, and no other.
    marked = {f.pdf_field for f in load_schema("form_101").fields if f.legal_review}
    assert marked == LEGAL_REVIEW


def test_only_line_15s_and_16as_own_answer_boxes_pass_the_upl_guard():
    # Ruling T4-legalreview: a derived legal_review box prints only when its rule ticks exactly
    # the filer's own stored choice. The guard's list is these eight rules and no other, so a
    # rule joins it only by a change here.
    from apps.forms.services.derivations import ANSWER_BOX_RULES

    reviewed = [f for f in load_schema("form_101").fields if f.legal_review]
    assert {f.source for f in reviewed} == {"derived"}
    assert {f.rule for f in reviewed} == ANSWER_BOX_RULES


def test_the_revision_mark_on_the_template_is_11_26():
    # 4b-R9: formText.ts's FORM_REVISIONS names the edition the PDF prints.
    text = pypdf.PdfReader(BytesIO(TEMPLATE.read_bytes())).pages[0].extract_text()
    assert "11/26" in text
    assert "06/24" not in text


def test_no_binding_reads_the_retired_form_answers():
    # 4b-R2: every asked box reads PetitionAnswers; FormAnswer is written by nothing.
    bindings = [f.binding for f in load_schema("form_101").fields if f.binding]
    assert [b for b in bindings if not b.startswith("petition.")] == []
