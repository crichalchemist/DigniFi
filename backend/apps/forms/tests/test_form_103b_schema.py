"""Round-trip tests for Form 103B schema-driven resolution."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.cmi import MARRIAGE_UNANSWERED, IncomeStepGap
from apps.forms.field_index import load_index
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve, resolve_parts
from apps.intake.models import (
    DebtorInfo,
    IncomeInfo,
    IntakeSession,
)
from apps.intake.tests.builders import answer_household, answer_petition

User = get_user_model()

# Line 20's rows as the index draws them (form_b103b.index.json, page 3): district, when and case
# number on one baseline each, y 529.8, 557.1 and 585.2.
LINE_20_ROWS = (
    ("undefined_37", "When", "Case number_2"),
    ("District", "When_2", "Case number_3"),
    ("District_2", "When_3", "Case number_4"),
)
FOUR_CASES = [
    {
        "district": f"Demo District {n}",
        "filed_on": f"0{n}/15/2019",
        "case_number": f"19-bk-0000{n}",
    }
    for n in (1, 2, 3, 4)
]


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema103b", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


@pytest.fixture
def session_with_fw(session):
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
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1500.00"))
    answer_household(session)
    return session


@pytest.mark.django_db
class TestForm103BSchema:
    def test_resolver_produces_output(self, session_with_fw):
        field_map = resolve(load_schema("form_103b"), session_with_fw)
        assert "Bankruptcy District Information" in field_map
        assert "Debtor 1" in field_map
        assert "Jane Doe" in field_map["Debtor 1"]

    def test_line_1_counts_the_household_list(self, session_with_fw):
        # The filer listed no one else, so 103B line 1 is 1.
        field_map = resolve(load_schema("form_103b"), session_with_fw)
        assert field_map["Total number of people"] == "1"

    def test_an_empty_session_is_refused_in_the_income_steps_words(self, session):
        with pytest.raises(IncomeStepGap) as refused:
            resolve(load_schema("form_103b"), session)
        assert str(refused.value) == MARRIAGE_UNANSWERED

    # Line 20 asks Form 101 line 9's question, so it prints the answer and the earlier cases
    # step 1 stored (4b-ii, §13.1). Its rows pair by the index's rectangles, never by a name's
    # suffix: row 1's district box is undefined_37 (spec correction 6).

    def test_line_20_prints_the_prior_cases_step_1_gave_and_a_fourth_on_the_sheet(
        self, session_with_fw
    ):
        answer_petition(session_with_fw, prior_bankruptcy_answer="yes", prior_cases=FOUR_CASES)
        document = resolve_parts(load_schema("form_103b"), session_with_fw)
        form = document["parts"][0]["values"]
        assert form["check_20"] == "/yes"
        for n, boxes in enumerate(LINE_20_ROWS, start=1):
            assert tuple(form.get(box) for box in boxes) == (
                f"Demo District {n}",
                f"0{n}/15/2019",
                f"19-bk-0000{n}",
            ), boxes
        (sheet,) = [p for p in document["parts"] if p["kind"] == "sheet"]
        assert sheet["group"] == "prior_cases_103b"
        assert sheet["title"] == (
            "Official Form 103B, Application to Have the Chapter 7 Filing Fee Waived, line 20"
        )
        assert sheet["rows"] == [
            {"line": "20.4", "cells": ["Demo District 4", "04/15/2019", "19-bk-00004"]}
        ]

    def test_line_20_prints_two_cases_in_rows_1_and_2_and_leaves_row_3_blank(self, session_with_fw):
        answer_petition(session_with_fw, prior_bankruptcy_answer="yes", prior_cases=FOUR_CASES[:2])
        form = resolve(load_schema("form_103b"), session_with_fw)
        assert (form["undefined_37"], form["When"], form["Case number_2"]) == (
            "Demo District 1",
            "01/15/2019",
            "19-bk-00001",
        )
        assert (form["District"], form["When_2"], form["Case number_3"]) == (
            "Demo District 2",
            "02/15/2019",
            "19-bk-00002",
        )
        assert {box: form.get(box) for box in LINE_20_ROWS[2]} == dict.fromkeys(LINE_20_ROWS[2])

    def test_line_20s_three_cells_share_one_baseline_per_row(self):
        # F-1: a suffix pairing (District with When) would print case 1's district a row below
        # its date. Each slot row's three widgets must sit on one line, the rows going down.
        schema = load_schema("form_103b")
        index = load_index("form_b103b.pdf")
        tops = []
        for row in (1, 2, 3):
            boxes = [
                f.pdf_field
                for f in schema.fields
                if f.repeat == "prior_cases_103b" and f.row == row
            ]
            assert len(boxes) == 3, (row, boxes)
            # Each line 20 box is one widget, on page 3.
            assert all([w.page for w in index[box]] == [3] for box in boxes), boxes
            ys = [index[box][0].rect[1] for box in boxes]
            assert max(ys) - min(ys) <= 1, (row, boxes, ys)
            tops.append(min(ys))
        assert tops == sorted(tops) and len(set(tops)) == 3, tops

    def test_line_20_prints_a_no_and_no_row_for_a_no_with_stored_rows(self, session_with_fw):
        # The rows stay stored under a No and print nothing: no box, no sheet.
        answer_petition(session_with_fw, prior_bankruptcy_answer="no", prior_cases=FOUR_CASES)
        document = resolve_parts(load_schema("form_103b"), session_with_fw)
        form = document["parts"][0]["values"]
        assert form["check_20"] == "/no"
        assert [form.get(box) for row in LINE_20_ROWS for box in row] == [None] * 9
        assert [p for p in document["parts"] if p["kind"] == "sheet"] == []

    def test_an_unanswered_line_20_prints_neither_box(self, session_with_fw):
        # Never a No the filer didn't give (§5.3).
        answer_petition(session_with_fw, prior_bankruptcy_answer=None)
        assert "check_20" not in resolve(load_schema("form_103b"), session_with_fw)

    def test_a_date_that_is_not_mm_dd_yyyy_prints_blank_and_the_rest_of_its_row_prints(
        self, session_with_fw
    ):
        # PF2-2: the shared reader blanks a date the form can't read, on 103B as on Form 101.
        case = {"district": "Demo District 1", "filed_on": "2019-01-15", "case_number": "19-1"}
        answer_petition(session_with_fw, prior_bankruptcy_answer="yes", prior_cases=[case])
        form = resolve(load_schema("form_103b"), session_with_fw)
        assert (form.get("undefined_37"), form.get("When"), form.get("Case number_2")) == (
            "Demo District 1",
            None,
            "19-1",
        )


def test_form_103b_line_20s_sheet_keeps_form_101_line_9s_columns():
    # One answer prints on both sheets, and Review names a too-long cell by Form 101's own labels
    # (CELL_LABELS) for either form: a column added, moved, renamed or narrowed on one sheet alone
    # would print the rows differently or name a cell the other form doesn't have.
    def columns(form_type, group):
        sheet = load_schema(form_type).groups[group].sheet
        return sheet.line_width, [(c.label, c.binding, c.width) for c in sheet.columns]

    assert columns("form_103b", "prior_cases_103b") == columns("form_101", "prior_cases")
