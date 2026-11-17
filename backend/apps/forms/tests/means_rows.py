"""A Form 122A-2 session that overflows every row group by one row (3h3 plan R18).

Shared by test_form_122a2_rows.py, test_statement_sheet.py and test_means_rows_builder.py. The
session is above the median, married and living with a spouse whose wages (SPOUSE_WAGES) cover
line 3's total, and keeps a presumption at line 40, so the form reaches line 43. Every row's
figure is distinct, so a box printing another row's figure fails a test by name. ROWS holds what
each row prints, written out here, and total(key) adds a group's printed amounts up.
"""

from datetime import date
from decimal import Decimal

from apps.eligibility.means_inputs import counted_debts, vehicle_rows
from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
from apps.intake.tests.builders import (
    answer_asset_lines,
    answer_household,
    answer_means_test,
    linked_loan,
    linked_row,
)

# The spouse's counted income, Form 122A-1 Column B: at least line 3's total (1,010.00), or
# DIG-514's cap makes line 3 and every later line MISSING (R7).
SPOUSE_WAGES = Decimal("1800.00")
SPOUSE = {
    "relationship": "spouse",
    "age": 40,
    "lives_with_you": True,
    "claimed_or_supported": False,
    "spouse_is_dependent": False,
}

# Line 3: four rows, (purpose, amount); the form has three boxes.
LINE_3 = (
    ("Demo purpose 1", "101.00"),
    ("Demo purpose 2", "202.00"),
    ("Demo purpose 3", "303.00"),
    ("Demo purpose 4", "404.00"),
)
# The secured debts, (creditor, monthly payment): 60 or more payments left and no change, so
# each prints its monthly payment as its 60-month average.
HOME_LOANS = (
    ("Demo Lender 01", "111.00"),
    ("Demo Lender 02", "222.00"),
    ("Demo Lender 03", "333.00"),
    ("Demo Lender 04", "444.00"),
)
VEHICLE_1_LOANS = (
    ("Demo Lender 05", "11.00"),
    ("Demo Lender 06", "22.00"),
    ("Demo Lender 07", "33.00"),
)
VEHICLE_2_LOANS = (
    ("Demo Lender 08", "44.00"),
    ("Demo Lender 09", "55.00"),
    ("Demo Lender 10", "66.00"),
)
# Line 33d's debts, (creditor, the property, monthly payment, taxes-or-insurance answer, cure):
# each secured by a household item, answered Yes on line 34 with a cure, 6000.00 / 60 = 100.00.
OTHER_DEBTS = (
    ("Demo Lender 11", "Demo boat", "71.00", "yes", "6000.00"),
    ("Demo Lender 12", "Demo piano", "82.00", "no", "6060.00"),
    ("Demo Lender 13", "Demo tractor", "93.00", "no", "6120.00"),
    ("Demo Lender 14", "Demo camper", "104.00", "no", "6180.00"),
)
CIRCUMSTANCES = tuple((f"Demo circumstance {n}", f"{n}0.00") for n in range(1, 6))
# The filer's own explanation the polish tests rewrite: six facts as polish_checks reads them
# (figures 1400 and 2025, dated month mar, names demo, clinic and march), no identifier and no
# listed phrase. 3h4's backend tests import it.
POLISH_DEMO_EXPLANATION = (
    "I have been sick since the start of last year, and the illness has changed how I live. "
    "Since March 2025 I pay 1,400 each month to Demo Clinic for my treatment and my medicine. "
    "I used to work full weeks, but now I can only work a few hours at a time, so my pay is "
    "lower than it was. My doctor wants to see me often, and I have to travel a long way to "
    "each visit. I have cut every cost I can. I stopped eating out, I canceled my streaming "
    "services, and I share rides with a neighbor. These payments are the part of my budget "
    "I cannot cut, because without the treatment I could not work at all."
)

# The page's answers, as the builder gives them; vehicle_claims is added from the session's rows.
ANSWERS = {
    "line_3_answer": "yes",
    "line_3_rows": [{"purpose": purpose, "amount": amount} for purpose, amount in LINE_3],
    "line_34_answer": "yes",
    "line_43_answer": "yes",
    "line_43_circumstances": [
        {"explanation": explanation, "amount": amount} for explanation, amount in CIRCUMSTANCES
    ],
}
# Each counted debt's answers by creditor name, over answer_means_test's defaults (60 or more
# payments left, no change, no taxes or insurance): every one answers necessary_for_support,
# since one None makes line 34's total MISSING.
DEBT_ANSWERS = {
    **{
        creditor: {"necessary_for_support": "no"}
        for creditor, _ in (*HOME_LOANS, *VEHICLE_1_LOANS, *VEHICLE_2_LOANS)
    },
    **{
        creditor: {"taxes_or_insurance": flag, "necessary_for_support": "yes", "cure": cure}
        for creditor, _, _, flag, cure in OTHER_DEBTS
    },
}


def _monthly_cure(cure):
    return str((Decimal(cure) / 60).quantize(Decimal("0.01")))


# What each row prints, group by group, in the form's order (R18): the tests read these.
ROWS = {
    "3": LINE_3,
    "9b": HOME_LOANS,
    "13b": VEHICLE_1_LOANS,
    "13e": VEHICLE_2_LOANS,
    "33d": tuple(
        (creditor, item, flag, payment) for creditor, item, payment, flag, _ in OTHER_DEBTS
    ),
    "34": tuple(
        (creditor, item, cure, _monthly_cure(cure)) for creditor, item, _, _, cure in OTHER_DEBTS
    ),
    "43": CIRCUMSTANCES,
}


def total(key):
    """A group's printed amounts, its last cell per row, added up."""
    return sum((Decimal(row[-1]) for row in ROWS[key]), Decimal("0.00"))


def answer_page(session, over=None, debts=None):
    """Re-answer the whole page: `over` merged over the builder's answers, `debts` ({creditor
    name: per-debt answers}) over each debt's. The one way to change one answer, since
    answer_means_test alone resets every default. Returns the session read fresh."""
    fresh = IntakeSession.objects.get(pk=session.pk)
    by_name = {debt.creditor_name: debt.pk for debt in counted_debts(fresh)}
    per_debt = {name: dict(answers) for name, answers in DEBT_ANSWERS.items()}
    for name, answers in (debts or {}).items():
        per_debt[name] = per_debt[name] | answers
    claims = {f"asset-{row.pk}": "yes" for row in vehicle_rows(fresh)}
    answer_means_test(
        fresh,
        debts={by_name[name]: answers for name, answers in per_debt.items()},
        **{**ANSWERS, "vehicle_claims": claims, **(over or {})},
    )
    return IntakeSession.objects.get(pk=session.pk)


def overflowing_session(user, district):
    """A completed, above-median session (wages 9,000.00) with one row past each group's boxes."""
    session = IntakeSession.objects.create(user=user, district=district, status="completed")
    IncomeInfo.objects.create(
        session=session, marital_status="married_together", monthly_gross_wages=Decimal("9000.00")
    )
    DebtorInfo.objects.create(
        session=session,
        first_name="Demo",
        last_name="Filer",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    answer_household(
        session,
        marital_status="married_together",
        members=[SPOUSE],
        spouse_income={"monthly_gross_wages": SPOUSE_WAGES},
    )
    home = linked_row(session, "1", lives_here="yes", description="Demo house")
    for creditor, payment in HOME_LOANS:
        linked_loan(session, home, payment, creditor_name=creditor)
    # both cars claimed, so line 11 is 2 and each takes a slot in Schedule A/B order
    for n, loans in ((1, VEHICLE_1_LOANS), (2, VEHICLE_2_LOANS)):
        car = linked_row(session, "3", description=f"Demo car {n}")
        for creditor, payment in loans:
            linked_loan(session, car, payment, creditor_name=creditor)
    for creditor, item, payment, _, _ in OTHER_DEBTS:
        linked_loan(
            session, linked_row(session, "6", description=item), payment, creditor_name=creditor
        )
    answer_asset_lines(session, ["1", "3", "6"])
    return answer_page(session)
