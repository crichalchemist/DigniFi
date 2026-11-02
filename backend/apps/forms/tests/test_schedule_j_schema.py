"""Schedule J: each expense prints on the line that asks for it, and only above $0."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.cmi import HOUSEHOLD_UNANSWERED, IncomeStepGap
from apps.forms.registry import build_parts
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_sheets
from apps.intake.models import DebtorInfo, ExpenseInfo, Household, IncomeInfo, IntakeSession

User = get_user_model()

# Each of the Expenses step's 13 amounts gets a distinct power of two, so a line that reads
# the wrong amount, or adds one too many, prints a different figure.
EXPENSES = {
    "rent_or_mortgage": Decimal("1.00"),
    "utilities": Decimal("2.00"),
    "home_maintenance": Decimal("4.00"),
    "vehicle_payment": Decimal("8.00"),
    "vehicle_insurance": Decimal("16.00"),
    "vehicle_maintenance": Decimal("32.00"),
    "food_and_groceries": Decimal("64.00"),
    "clothing": Decimal("128.00"),
    "medical_expenses": Decimal("256.00"),
    "childcare": Decimal("512.00"),
    "child_support_paid": Decimal("1024.00"),
    "insurance_not_deducted": Decimal("2048.00"),
    "other_expenses": Decimal("4096.00"),
}
# Box → what it prints with EXPENSES (step 2 spec Appendix A.8, owner Q4).
LINE_BY_EXPENSE = {
    "4": "1.00",  # rent or mortgage
    "4c": "4.00",  # home maintenance, repair and upkeep
    "6d": "2.00",  # utilities, combined on "Other"
    "Other 6d": "Utilities (combined)",
    "7": "64.00",  # food and housekeeping supplies
    "8": "512.00",  # childcare
    "9": "128.00",  # clothing
    "11": "256.00",  # medical and dental
    "12": "32.00",  # transportation, never car payments
    "15c": "16.00",  # vehicle insurance
    "15d": "2048.00",  # insurance not deducted from pay, combined on "Other"
    "Other 15d": "Insurance (combined)",
    "17a": "8.00",  # the one car payment the Expenses step asks
    "18": "1024.00",  # support paid
    "21": "4096.00",  # other expenses only
}
# Lines no expense belongs on, which the old bindings filled.
VACATED = {"10", "14", "15a", "15b", "16", "17b", "17c", "20a"}
# The 13 amounts above, added: 1 + 2 + 4 + ... + 4096.
EXPENSE_TOTAL = "8191.00"


def _household(session, members):
    # Change the instance the session holds: the rules read session.household, which a
    # one-to-one keeps cached, so a fresh copy from the database would leave it stale.
    household = getattr(session, "household", None) or Household(session=session)
    household.store_members(members)
    household.save()


def _member(relationship, age, lives_with_you=True, claimed_or_supported=True, **spouse):
    return {
        "relationship": relationship,
        "age": age,
        "lives_with_you": lives_with_you,
        "claimed_or_supported": claimed_or_supported,
        **spouse,
    }


SIX = [
    _member("son", 15),
    _member("daughter", 12),
    _member("stepchild", 10),
    _member("grandchild", 4),
    _member("parent", 70),
    _member("other_relative", 30, lives_with_you=False),
]


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemasj", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    # line 2 refuses a list never answered (3e1 spec §9.2): "no one" here
    _household(session, [])
    return session


def test_each_expense_prints_on_the_line_that_asks_for_it(session):
    ExpenseInfo.objects.create(session=session, **EXPENSES)

    printed = resolve(load_schema("schedule_j"), session)

    assert {box: printed.get(box) for box in LINE_BY_EXPENSE} == LINE_BY_EXPENSE
    assert sorted(VACATED & printed.keys()) == []


@pytest.mark.parametrize(
    "amount,prints",
    [
        (Decimal("0.01"), True),
        (Decimal("0"), False),
        (Decimal("-0.01"), False),
        (None, False),  # the Expenses step was never saved
    ],
)
def test_expense_line_prints_only_above_zero(session, amount, prints):
    # An expense left empty is stored as $0, so $0 can't be told from "left blank": a line
    # prints only above $0, and so do 6d's and 15d's labels (step 2 spec §6.1, Q4).
    if amount is not None:
        ExpenseInfo.objects.create(session=session, **dict.fromkeys(EXPENSES, amount))

    printed = resolve(load_schema("schedule_j"), session)

    labels = {"Other 6d": "Utilities (combined)", "Other 15d": "Insurance (combined)"}
    expected = {box: labels.get(box, "0.01") for box in LINE_BY_EXPENSE} if prints else {}
    assert {box: printed[box] for box in LINE_BY_EXPENSE if box in printed} == expected


def test_support_paid_prints_on_line_18_and_never_on_line_21(session):
    # Line 21 is "Other": court-ordered support has its own line, 18.
    ExpenseInfo.objects.create(session=session, child_support_paid=Decimal("450.00"))

    printed = resolve(load_schema("schedule_j"), session)

    assert (printed.get("18"), printed.get("21")) == ("450.00", None)


def test_monthly_expenses_print_on_22c_and_again_on_23b(session):
    # 22c adds 22a and 22b (Debtor 2's separate household, never asked); 23b copies 22c.
    ExpenseInfo.objects.create(session=session, **EXPENSES)

    printed = resolve(load_schema("schedule_j"), session)

    totals = ("22a", "22c", "23b")
    assert {box: printed.get(box) for box in totals} == dict.fromkeys(totals, EXPENSE_TOTAL)


def test_monthly_net_income_is_income_less_expenses(session):
    # 23a copies Schedule I line 12, Social Security included (C1); 23c is 23a - 23b.
    IncomeInfo.objects.create(
        session=session,
        marital_status="not_married",
        monthly_gross_wages=Decimal("9000.00"),
        monthly_social_security=Decimal("200.00"),
    )
    ExpenseInfo.objects.create(session=session, **EXPENSES)

    printed = resolve(load_schema("schedule_j"), session)

    assert {box: printed.get(box) for box in ("23a", "23b", "23c")} == {
        "23a": "9200.00",
        "23b": EXPENSE_TOTAL,
        "23c": "1009.00",
    }


def test_a_month_that_runs_short_prints_net_income_below_zero(session):
    # The form's own arithmetic: expenses above income leave a negative net income.
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("100.00")
    )
    ExpenseInfo.objects.create(session=session, rent_or_mortgage=Decimal("250.00"))

    printed = resolve(load_schema("schedule_j"), session)

    assert printed.get("23c") == "-150.00"


@pytest.mark.parametrize("income_saved", [True, False])
def test_net_income_stays_blank_until_income_is_given(session, income_saved):
    # With no income row, 23a is blank and 23c has nothing to subtract from, so it is blank
    # too, never the expenses as a loss. The expense total still prints. A row saved with every
    # source empty prints line 12 as 0.00 (§9.6): the Income step's "income not entered" gap
    # refuses every form before this prints (§4.7, §8).
    if income_saved:  # the Income step was saved with every source left empty
        IncomeInfo.objects.create(session=session, marital_status="not_married")
    ExpenseInfo.objects.create(session=session, **EXPENSES)

    printed = resolve(load_schema("schedule_j"), session)

    assert {box: printed.get(box) for box in ("22c", "23a", "23b", "23c")} == {
        "22c": EXPENSE_TOTAL,
        "23a": "0.00" if income_saved else None,
        "23b": EXPENSE_TOTAL,
        "23c": f"-{EXPENSE_TOTAL}" if income_saved else None,
    }


@pytest.mark.parametrize(
    "filing_type", ["individual", "joint", None]
)  # None: Your Information never saved
def test_is_this_a_joint_case_answers_no_for_every_session(session, filing_type):
    # No step offers joint filing since 3e1 and Complete refuses a case the spouse files too
    # (3e1 spec §7), so a session saved as joint before then says No as well.
    if filing_type is not None:
        DebtorInfo.objects.create(
            session=session,
            first_name="Jane",
            middle_name="",
            last_name="Doe",
            ssn="900-13-0001",
            date_of_birth=date(1990, 1, 15),
            phone="312-555-0100",
            email="jane@example.com",
            street_address="123 Main St",
            city="Chicago",
            state="IL",
            zip_code="60601",
            filing_type=filing_type,
        )

    printed = resolve(load_schema("schedule_j"), session)

    assert printed.get("check1") == "/no"


def test_line_2_holds_five_dependents_on_the_form(session):
    _household(session, SIX[:5])
    (form,) = build_parts("schedule_j", session)["parts"]  # no sheet
    rows = [
        tuple(
            form["values"][f"{box}{x}"]
            for box in ("Dependant Relation 2", "Dependant age 2", "check2")
        )
        for x in "abcde"
    ]
    assert rows == [
        ("Son", "15", "/yes"),
        ("Daughter", "12", "/yes"),
        ("Stepchild", "10", "/yes"),
        ("Grandchild", "4", "/yes"),
        ("Parent", "70", "/yes"),
    ]


def test_a_sixth_dependent_continues_on_the_attached_sheet(generated_form_factory):
    # The template has no extra page for line 2, so row 6 goes on a sheet (U:145), "2.6".
    session = generated_form_factory().session
    _household(session, SIX)
    document = build_parts("schedule_j", session)
    assert document["parts"][1:] == [
        {
            "kind": "sheet",
            "group": "j_line_2",
            "title": "Official Form 106J, Schedule J: Your Expenses, line 2",
            "columns": [
                {"label": "Relationship", "width": 220.0},
                {"label": "Age", "width": 80.0},
                {"label": "Lives with you", "width": 168.0},
            ],
            "name": "Maria Torres",
            "rows": [{"line": "2.6", "cells": ["Other relative", "30", "No"]}],
        }
    ]
    PDFFormFiller().check("schedule_j", document)  # every row prints whole
    (sheet,) = read_sheets(
        PDFFormFiller().fill("schedule_j", document),
        load_schema("schedule_j").groups["j_line_2"].sheet,
    )
    assert sheet.rows == (("2.6", "Other relative", "30", "No"),)


@pytest.mark.parametrize(
    "members,ticks,row_a",
    [
        ([], "/no", None),  # "no one", James's answer
        ([_member("roommate", 29, claimed_or_supported=False)], "/no", None),  # Sarah's
        ([_member("spouse", 44, spouse_is_dependent=False)], "/no", None),  # DeShawn's (3e1.Q1)
        ([_member("spouse", 44, spouse_is_dependent=True)], "/yes", "Spouse"),
        ([_member("daughter", 9)], "/yes", "Daughter"),  # Andrés's
    ],
    ids=["no_one", "roommate", "spouse_on_the_tax_return", "spouse_a_dependent", "daughter"],
)
def test_do_you_have_dependents_answers_yes_only_when_line_2_lists_someone(
    session, members, ticks, row_a
):
    _household(session, members)
    printed = resolve(load_schema("schedule_j"), session)
    assert (printed.get("check2"), printed.get("Dependant Relation 2a")) == (ticks, row_a)


def test_an_unanswered_household_list_refuses_line_2_rather_than_answer_no(session):
    _household(session, None)
    with pytest.raises(IncomeStepGap) as refused:
        resolve(load_schema("schedule_j"), session)
    assert (str(refused.value), refused.value.step) == (HOUSEHOLD_UNANSWERED, "income_info")


def test_a_broken_expense_read_fails_the_form_instead_of_printing_0_00(session):
    # A decryption or database error must not become a plausible sworn $0.00 of expenses.
    ExpenseInfo.objects.create(session=session, **EXPENSES)

    with patch.object(
        ExpenseInfo, "calculate_total_monthly_expenses", side_effect=RuntimeError("decrypt failed")
    ):
        with pytest.raises(RuntimeError):
            resolve(load_schema("schedule_j"), session)


def test_every_form_that_copies_the_monthly_expense_total_prints_line_22c(session):
    # Schedule J 22a, 22c and 23b, 106Sum line 5 and 103B line 6 are one figure on four forms,
    # so a filer's sworn expenses can't differ between them.
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("9000.00")
    )
    ExpenseInfo.objects.create(session=session, **EXPENSES)

    schedule_j = resolve(load_schema("schedule_j"), session)
    form_106sum = resolve(load_schema("form_106sum"), session)
    form_103b = resolve(load_schema("form_103b"), session)

    printed = [
        schedule_j.get("22a"),
        schedule_j.get("22c"),
        schedule_j.get("23b"),
        form_106sum.get("5"),
        form_103b.get("undefined_7"),
    ]
    assert printed == ["8191.00"] * 5
