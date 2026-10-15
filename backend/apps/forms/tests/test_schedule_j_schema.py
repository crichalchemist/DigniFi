"""Schedule J: each expense prints on the line that asks for it, and only above $0."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import ExpenseInfo, IntakeSession

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
    return IntakeSession.objects.create(user=user, district=district)


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
