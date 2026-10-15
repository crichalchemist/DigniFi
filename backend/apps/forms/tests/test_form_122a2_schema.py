"""Form 122A-2: line 1 copies 122A-1's monthly income, and lines 19 and 21 print above $0."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.cmi import IncomeNotSplit
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.tests.test_derivations import TEN_SOURCES
from apps.intake.models import ExpenseInfo, IncomeInfo, IntakeSession

User = get_user_model()

# Every Expenses step amount above $0, so a line still bound to an expense would print.
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
# The IRS and U.S. Trustee standards, the deduction lines and the result: step 3 asks
# for what they need (step 2 spec §6.4, B1), so until then they print nothing.
LEFT_FOR_STEP_3 = {
    "Quest4",  # lines 4 and 39a
    "Quest5",
    "Quest6",
    "Quest8",
    "Quest9",
    "Quest10",
    "Quest12",
    "Quest13D",
    "Quest14",
    "Quest15",
    "undefined_104",  # lines 38 and 39b
    "undefined_110",  # line 41a
    "undefined_111",  # line 41b
}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema122a2", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def test_line_1_copies_the_monthly_income_from_122a1_line_11(session):
    # Line 1 says "Copy line 11 from Official Form 122A-1 here": current monthly income,
    # which leaves Social Security out (C1), never an expense or deduction total.
    IncomeInfo.objects.create(session=session, **TEN_SOURCES)

    printed = resolve(load_schema("form_122a2"), session)

    # Every source but Social Security's 32.00: 1023.00 - 32.00.
    assert printed.get("Quest1") == "991.00"
    assert printed.get("Quest1") == resolve(load_schema("form_122a1"), session)["Debto1.Quest11"]


def test_empty_session_is_asked_for_income_by_source(session):
    # Line 1 is CMI, and a filer who gave no income has none to print (spec §5.5).
    with pytest.raises(IncomeNotSplit):
        resolve(load_schema("form_122a2"), session)


@pytest.mark.parametrize(
    "support_paid,childcare,printed",
    [
        (
            Decimal("450.00"),
            Decimal("1200.00"),
            {"undefined_51": "450.00", "undefined_53": "1200.00"},
        ),
        (Decimal("0.01"), Decimal("0.02"), {"undefined_51": "0.01", "undefined_53": "0.02"}),
        (Decimal("0"), Decimal("0"), {}),
        (None, None, {}),  # the Expenses step was never saved
    ],
)
def test_support_paid_and_childcare_print_on_lines_19_and_21_only_above_zero(
    session, support_paid, childcare, printed
):
    # An expense left empty is stored as $0, so $0 can't be told from "left blank": these
    # lines print only above $0, as Schedule J's do (step 2 spec §6.1, 6c option A).
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("9000.00"))
    if support_paid is not None:
        ExpenseInfo.objects.create(
            session=session, child_support_paid=support_paid, childcare=childcare
        )

    resolved = resolve(load_schema("form_122a2"), session)

    lines = ("undefined_51", "undefined_53")
    assert {box: resolved[box] for box in lines if box in resolved} == printed


def test_lines_left_for_step_3_print_nothing(session):
    # Every expense is above $0, so a line still reading one, or a means-test figure
    # step 2 never works out, would print.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("9000.00"))
    ExpenseInfo.objects.create(session=session, **EXPENSES)

    printed = resolve(load_schema("form_122a2"), session)

    assert sorted(LEFT_FOR_STEP_3 & printed.keys()) == []
