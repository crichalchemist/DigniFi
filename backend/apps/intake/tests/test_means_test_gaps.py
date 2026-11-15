"""The page names every answer Form 122A-2 still needs, in the page's order, and the gate refuses with the first."""

from dataclasses import replace
from decimal import Decimal

import pytest

from apps.eligibility.means_lines import SecuredDebt, Vehicle, line_30_cap
from apps.eligibility.tests.test_means_lines import CRV, KESTREL, PRIYA, TABLES
from apps.intake.means_test import means_test_gaps, normalized_answers

PRIYAS_PAGE = {
    "line_3_answer": "yes",
    "line_3_rows": [{"purpose": "His payroll taxes withheld from his pay", "amount": "250.00"}],
    "spouse_vehicles_answer": "no",
    "spouse_vehicles": [],
    "spouse_loans_answer": "no",
    "spouse_loans": [],
    "vehicle_claims": {"asset-1": "yes"},
    "line_15_answer": "no",
    "line_16": "2300.00",
    "line_17": "0.00",
    "line_18": "120.00",
    "line_19": "0.00",
    "line_20": "0.00",
    "line_21": "1200.00",
    "line_22_answer": "no",
    "line_23": "0.00",
    "line_25_answer": "yes",
    "line_25_health": "620.00",
    "line_25_disability": "180.00",
    "line_25_hsa": "0.00",
    "line_25_spends": "yes",
    "line_26_answer": "no",
    "line_27_answer": "no",
    "line_28_answer": "no",
    "line_29_answer": "no",
    "line_30_answer": "no",
    "line_31_answer": "yes",
    "line_31_amount": "50.00",
    "line_34_answer": "no",
    "line_36_answer": "yes",
    "line_36_payment": "1400.00",
    "line_43_answer": "no",
}


def _page(*, vehicles=("asset-1",), **over):
    return normalized_answers({**PRIYAS_PAGE, **over}, set(vehicles), {1})


def _gaps(inputs=PRIYA, **over):
    return means_test_gaps(inputs, TABLES, _page(**over))


def test_priyas_answers_leave_no_gap():
    assert means_test_gaps(PRIYA, TABLES, _page()) == []


@pytest.mark.parametrize(
    ("over", "sentence"),
    [
        ({"line_3_answer": None}, "Answer line 3, about your spouse's income."),
        (
            {"line_3_rows": []},
            "Add each use of your spouse's income on line 3, or change the answer to No.",
        ),
        (
            {"spouse_vehicles_answer": None},
            "Answer whether your spouse has a vehicle that isn't on your property list.",
        ),
        (
            {"spouse_vehicles_answer": "yes", "spouse_vehicles": []},
            "Add each of your spouse's vehicles, or change the answer to No.",
        ),
        (
            {"spouse_loans_answer": None},
            "Answer whether your spouse owes a loan on your home, a vehicle or other property.",
        ),
        (
            {"spouse_loans_answer": "yes", "spouse_loans": []},
            "Add each of your spouse's loans, or change the answer to No.",
        ),
        ({"line_15_answer": None}, "Answer the question on line 15."),
        (
            {"line_15_answer": "yes", "line_15_amount": None},
            "Enter the amount for line 15.",
        ),
        ({"line_16": None}, "Enter the amount for line 16. Enter 0 if you have none."),
        ({"line_17": None}, "Enter the amount for line 17. Enter 0 if you have none."),
        ({"line_18": None}, "Enter the amount for line 18. Enter 0 if you have none."),
        ({"line_19": None}, "Enter the amount for line 19. Enter 0 if you have none."),
        ({"line_20": None}, "Enter the amount for line 20. Enter 0 if you have none."),
        ({"line_21": None}, "Enter the amount for line 21. Enter 0 if you have none."),
        ({"line_23": None}, "Enter the amount for line 23. Enter 0 if you have none."),
        ({"line_22_answer": None}, "Answer line 22."),
        ({"line_22_answer": "yes", "line_22_amount": None}, "Enter the amount for line 22."),
        ({"line_25_answer": None}, "Answer line 25."),
        ({"line_25_hsa": None}, "Enter the three amounts on line 25."),
        ({"line_25_spends": None}, "Answer whether you actually spend the line 25 total."),
        (
            {"line_25_spends": "no", "line_25_actual": None},
            "Enter how much you actually spend, on line 25.",
        ),
        ({"line_26_answer": None}, "Answer line 26."),
        ({"line_31_answer": "yes", "line_31_amount": None}, "Enter the amount for line 31."),
        (
            {"line_34_answer": None},
            "Answer line 34, about debts secured by property you need for support.",
        ),
        ({"line_36_answer": None}, "Answer line 36."),
        (
            {"line_36_payment": None},
            "Enter the projected monthly plan payment on line 36.",
        ),
        ({"line_43_answer": None}, "Answer the question on line 43."),
        (
            {"line_43_answer": "yes", "line_43_circumstances": []},
            "Add each special circumstance on line 43, or change the answer to No.",
        ),
    ],
)
def test_each_missing_answer_is_one_gap_in_the_pages_words(over, sentence):
    assert _gaps(**over) == [sentence]


@pytest.mark.parametrize(
    "rows",
    [
        [{"purpose": "  ", "amount": "5.00"}],
        [{"purpose": "Tax debt", "amount": None}],
        [{"purpose": "", "amount": None}, {"purpose": "x", "amount": None}],
    ],
)
def test_a_line_3_row_with_no_purpose_is_one_gap(rows):
    assert _gaps(line_3_rows=rows) == [
        "Enter what your spouse's income was used for, and the amount, on each row of line 3."
    ]


def test_line_15_above_its_cap_is_a_gap_and_at_it_is_not():
    over = _gaps(line_15_answer="yes", line_15_amount="220.01")
    assert over == ["Line 15 can't be more than $220.00, the IRS amount for public transportation."]
    assert _gaps(line_15_answer="yes", line_15_amount="220.00") == []


def test_line_15_is_asked_only_while_a_vehicle_is_claimed():
    unclaimed = replace(PRIYA, vehicles=(replace(CRV, claimed=False),), secured_debts=())
    assert _gaps(unclaimed, line_15_answer=None) == []


def test_an_unanswered_vehicle_claim_names_the_vehicle():
    unanswered = replace(PRIYA, vehicles=(replace(CRV, claimed=None),))
    assert _gaps(unanswered, line_15_answer=None) == [
        "Answer whether you claim an expense for Honda CR-V EX 2021."
    ]


def test_line_30_above_its_cap_is_a_gap_and_at_it_is_not():
    cap_gap = "Line 30 can't be more than $76.00, which is 5% of the IRS food and clothing amounts for 4 people."
    assert _gaps(line_30_answer="yes", line_30_amount="76.01") == [cap_gap]
    assert _gaps(line_30_answer="yes", line_30_amount="76.00") == []


def test_a_household_of_one_reads_1_person_in_the_line_30_cap_gap():
    alone = replace(PRIYA, ages=(40,))
    one_cent_over = line_30_cap(TABLES, 1) + Decimal("0.01")
    gaps = _gaps(alone, line_30_answer="yes", line_30_amount=str(one_cent_over))
    assert gaps == [
        "Line 30 can't be more than $30.00, which is 5% of the IRS food and clothing amounts for 1 person."
    ]
    assert not any("1 people" in gap for gap in gaps)


def test_line_30_waits_for_the_household_before_it_has_a_cap():
    unknown = replace(PRIYA, ages=None)
    assert _gaps(unknown, line_30_answer="yes", line_30_amount="9999.00") == []


def test_under_line_34s_yes_a_debt_answered_no_asks_no_cure_and_an_unanswered_one_is_a_gap():
    def under_yes(**changes):
        debt = replace(KESTREL, **changes)
        return _gaps(replace(PRIYA, secured_debts=(debt,)), line_34_answer="yes")

    assert under_yes(necessary_for_support="no") == []
    assert under_yes(necessary_for_support=None) == [
        "Say if your debt to Kestrel Auto Finance is secured by property you need for support."
    ]
    assert under_yes(necessary_for_support="yes", cure=None) == [
        "Enter the cure amount for Kestrel Auto Finance. Enter 0 if there is none."
    ]
    assert under_yes(necessary_for_support="yes", cure=Decimal("0.00")) == []


def test_each_debts_own_questions_are_gaps_named_by_creditor():
    def debt_gaps(**changes):
        return _gaps(replace(PRIYA, secured_debts=(replace(KESTREL, **changes),)))

    assert debt_gaps(payments_left=None) == [
        "Enter how many payments you have left to Kestrel Auto Finance."
    ]
    assert debt_gaps(payment_changes=None) == [
        "Answer whether your payment to Kestrel Auto Finance will change."
    ]
    assert debt_gaps(payment_changes="yes", total_60_months=None) == [
        "Enter the total you will owe Kestrel Auto Finance in the 60 months after you file."
    ]


def test_the_taxes_question_is_asked_only_of_a_line_33d_debt():
    unlinked = SecuredDebt(
        ref="debt-2",
        creditor="Demo Furniture Lender",
        secured_by=None,
        on_home=False,
        property="",
        monthly_payment=Decimal("50.00"),
        payments_left=12,
        payment_changes="no",
    )
    assert _gaps(replace(PRIYA, secured_debts=(KESTREL, unlinked))) == [
        "Say if the payment to Demo Furniture Lender pays for taxes or insurance too."
    ]
    # Kestrel is on a vehicle that takes line 13b, so its taxes answer is never asked
    assert _gaps(replace(PRIYA, secured_debts=(replace(KESTREL, taxes_or_insurance=None),))) == []


@pytest.mark.parametrize("text", ["", "   ", " \n  \n"])
def test_an_explanation_of_spaces_and_line_breaks_is_a_gap(text):
    rows = [{"explanation": text, "amount": "10.00"}]
    assert _gaps(line_43_answer="yes", line_43_circumstances=rows) == [
        "Give the explanation for circumstance 1 on line 43."
    ]


def test_a_missing_circumstance_amount_names_its_number():
    rows = [
        {"explanation": "A", "amount": "10.00"},
        {"explanation": "B", "amount": None},
    ]
    assert _gaps(line_43_answer="yes", line_43_circumstances=rows) == [
        "Enter the average monthly amount for circumstance 2 on line 43. Enter 0 if there is none."
    ]


def _loan(number, **over):
    row = {
        "ref": f"spouse-{number}",
        "on_amounts_owed": "no",
        "debt": None,
        "creditor": f"Demo Lender {number}",
        "secured_by": "home",
        "property": "A Demo house",
        "payment": "100.00",
        "payments_left": "10",
        "payment_changes": "no",
    }
    row.update(over)
    return row


def _loan_debt(number, creditor, **over):
    fields = {
        "ref": f"spouse-{number}",
        "creditor": creditor,
        "secured_by": None,
        "on_home": True,
        "property": "A Demo house",
        "monthly_payment": Decimal("100.00"),
        "payments_left": 10,
        "payment_changes": "no",
    }
    fields.update(over)
    return SecuredDebt(**fields)


def test_a_spouse_loan_with_no_creditor_names_no_later_gap():
    row = _loan(1, creditor="", secured_by="home", property="", payment=None)
    inputs = replace(
        PRIYA,
        secured_debts=(KESTREL, _loan_debt(1, "", payments_left=None, payment_changes=None)),
    )
    assert _gaps(inputs, spouse_loans_answer="yes", spouse_loans=[row]) == [
        "Enter who your spouse owes on each of their loans."
    ]


@pytest.mark.parametrize(
    ("loan_over", "vehicles", "stored"),
    [
        # the vehicle it names has gone from the Assets step
        ({"secured_by": "asset-9"}, ("asset-1",), {}),
        # it names a spouse vehicle while the spouse has none
        ({"secured_by": "spouse-1"}, ("asset-1",), {}),
        # an Amounts Owed loan can't name a filer vehicle
        ({"on_amounts_owed": "yes", "debt": 1, "secured_by": "asset-1"}, ("asset-1",), {}),
    ],
)
def test_a_spouse_loan_the_reader_cant_place_is_named_by_a_gap(loan_over, vehicles, stored):
    row = _loan(1, **loan_over)
    debt = _loan_debt(1, "Demo Lender 1", secured_by=None, on_home=False, placed=False)
    inputs = replace(PRIYA, secured_debts=(KESTREL, debt))
    gaps = _gaps(inputs, vehicles=vehicles, spouse_loans_answer="yes", spouse_loans=[row])
    assert gaps == ["Say what secures your spouse's loan from Demo Lender 1."]


@pytest.mark.parametrize("on_list_debt", [None, 2])
def test_a_spouse_loan_naming_a_debt_that_has_gone_or_is_now_secured_asks_which_loan(on_list_debt):
    row = _loan(1, on_amounts_owed="yes", debt=on_list_debt, creditor="")
    inputs = replace(PRIYA, secured_debts=(KESTREL, _loan_debt(1, "", placed=False)))
    # open debts are {1}: debt 2 is not among them, so the named debt reads as gone
    assert _gaps(inputs, spouse_loans_answer="yes", spouse_loans=[row]) == [
        "For each of your spouse's loans that is on your Amounts Owed step, choose which one it is."
    ]


def test_the_vehicle_choice_is_a_gap_for_an_equal_pair_and_for_an_entry_that_is_no_candidate():
    cars = tuple(
        Vehicle(ref=f"asset-{n}", name=f"Demo car {n}", leased=True, claimed=n != 4)
        for n in (1, 2, 3, 4)
    )
    inputs = replace(PRIYA, vehicles=cars, secured_debts=())
    refs = ("asset-1", "asset-2", "asset-3", "asset-4")
    claims = {"asset-1": "yes", "asset-2": "yes", "asset-3": "yes", "asset-4": "no"}
    choose = "Choose your Vehicle 1 and your Vehicle 2."

    def gaps(pair):
        page = _page(vehicles=refs, vehicle_claims=claims, vehicle_choice=pair)
        return means_test_gaps(inputs, TABLES, page)

    assert gaps(["asset-1", "asset-2"]) == []
    assert gaps(["asset-1", "asset-1"]) == [choose]
    assert gaps(["asset-1", None]) == [choose]
    assert gaps([None, None]) == [choose]
    assert gaps(["asset-1", "asset-4"]) == [choose]


def test_the_block_shows_only_for_married_together():
    single = replace(PRIYA, marital_status="not_married")
    rows = [{"ref": "spouse-1", "description": "", "leased": None, "claimed": None}]
    gaps = _gaps(
        single,
        line_3_answer=None,
        spouse_vehicles_answer="yes",
        spouse_vehicles=rows,
        spouse_loans_answer=None,
    )
    assert gaps == []


def test_line_43_is_a_gap_for_every_filer_the_form_applies_to():
    for status in ("not_married", "married_together", "married_separated"):
        inputs = replace(PRIYA, marital_status=status)
        assert _gaps(inputs, line_43_answer=None) == ["Answer the question on line 43."]


# The sentences for an unanswered 122A-2, line 16 to line 31 and line 34 to line 43, written out.
_LINES_16_TO_31 = [
    "Enter the amount for line 16. Enter 0 if you have none.",
    "Enter the amount for line 17. Enter 0 if you have none.",
    "Enter the amount for line 18. Enter 0 if you have none.",
    "Enter the amount for line 19. Enter 0 if you have none.",
    "Enter the amount for line 20. Enter 0 if you have none.",
    "Enter the amount for line 21. Enter 0 if you have none.",
    "Answer line 22.",
    "Enter the amount for line 23. Enter 0 if you have none.",
    "Answer line 25.",
]
_LINES_34_TO_43 = [
    "Answer line 34, about debts secured by property you need for support.",
    "Answer line 36.",
    "Answer the question on line 43.",
]
_KESTREL_UNANSWERED = [
    "Enter how many payments you have left to Kestrel Auto Finance.",
    "Answer whether your payment to Kestrel Auto Finance will change.",
]


def _unanswered_inputs():
    return replace(
        PRIYA,
        vehicles=(replace(CRV, claimed=None),),
        secured_debts=(replace(KESTREL, payments_left=None, payment_changes=None),),
        spouse_vehicles_answer=None,
        spouse_loans_answer=None,
    )


def _unanswered_page(**over):
    return normalized_answers(over, {"asset-1"}, {1})


def test_the_gaps_come_in_the_pages_order():
    inputs = _unanswered_inputs()
    first = means_test_gaps(inputs, TABLES, _unanswered_page())
    assert first == [
        "Answer line 3, about your spouse's income.",
        "Answer whether your spouse has a vehicle that isn't on your property list.",
        "Answer whether your spouse owes a loan on your home, a vehicle or other property.",
        "Answer whether you claim an expense for Honda CR-V EX 2021.",
        "Enter the amount for line 16. Enter 0 if you have none.",
        "Enter the amount for line 17. Enter 0 if you have none.",
        "Enter the amount for line 18. Enter 0 if you have none.",
        "Enter the amount for line 19. Enter 0 if you have none.",
        "Enter the amount for line 20. Enter 0 if you have none.",
        "Enter the amount for line 21. Enter 0 if you have none.",
        "Answer line 22.",
        "Enter the amount for line 23. Enter 0 if you have none.",
        "Answer line 25.",
        "Answer line 26.",
        "Answer line 27.",
        "Answer line 28.",
        "Answer line 29.",
        "Answer line 30.",
        "Answer line 31.",
        "Enter how many payments you have left to Kestrel Auto Finance.",
        "Answer whether your payment to Kestrel Auto Finance will change.",
        "Answer line 34, about debts secured by property you need for support.",
        "Answer line 36.",
        "Answer the question on line 43.",
    ]

    # the spouse's vehicles answered Yes: one describe gap, the described row's lease and claim
    # gaps, and nothing that names the blank row
    rows = [
        {"ref": "spouse-1", "description": "Demo Sedan", "leased": None, "claimed": None},
        {"ref": "spouse-2", "description": "", "leased": None, "claimed": None},
    ]
    with_rows = replace(
        inputs,
        vehicles=(
            replace(CRV, claimed=None),
            Vehicle(ref="spouse-1", name="Demo Sedan", leased=None, claimed=None),
            Vehicle(ref="spouse-2", name="", leased=None, claimed=None),
        ),
        spouse_vehicles_answer="yes",
    )
    page = _unanswered_page(spouse_vehicles_answer="yes", spouse_vehicles=rows)
    assert means_test_gaps(with_rows, TABLES, page) == [
        "Answer line 3, about your spouse's income.",
        "Describe each of your spouse's vehicles.",
        "Answer whether Demo Sedan is leased.",
        "Answer whether your spouse owes a loan on your home, a vehicle or other property.",
        "Answer whether you claim an expense for Honda CR-V EX 2021.",
        "Answer whether you claim an expense for Demo Sedan.",
        *_LINES_16_TO_31,
        "Answer line 26.",
        "Answer line 27.",
        "Answer line 28.",
        "Answer line 29.",
        "Answer line 30.",
        "Answer line 31.",
        *_KESTREL_UNANSWERED,
        *_LINES_34_TO_43,
    ]

    # line 30's cap comes right after line 30, before line 31 (F9)
    third = _unanswered_page(
        line_27_answer="no", line_28_answer="no", line_30_answer="yes", line_30_amount="76.01"
    )
    assert means_test_gaps(inputs, TABLES, third) == [
        "Answer line 3, about your spouse's income.",
        "Answer whether your spouse has a vehicle that isn't on your property list.",
        "Answer whether your spouse owes a loan on your home, a vehicle or other property.",
        "Answer whether you claim an expense for Honda CR-V EX 2021.",
        *_LINES_16_TO_31,
        "Answer line 26.",
        "Answer line 29.",
        "Line 30 can't be more than $76.00, which is 5% of the IRS food and clothing amounts for 4 people.",
        "Answer line 31.",
        *_KESTREL_UNANSWERED,
        *_LINES_34_TO_43,
    ]


def test_the_spouse_loans_identity_sentences_come_once_each_before_the_rows_own_gaps():
    rows = [
        _loan(1, creditor="", on_amounts_owed="no"),
        _loan(2, on_amounts_owed=None),
        _loan(3, on_amounts_owed="yes", debt=None, creditor=""),
        _loan(4, creditor="Demo Lender A", secured_by=None, payment="300.00"),
        _loan(5, creditor="Demo Lender B", property="", payment=None),
        _loan(6, creditor="", on_amounts_owed="no"),
    ]
    debts = tuple(
        _loan_debt(n, creditor, placed=False, secured_by=None, on_home=False)
        for n, creditor in (
            (1, ""),
            (2, ""),
            (3, ""),
            (4, "Demo Lender A"),
            (5, "Demo Lender B"),
            (6, ""),
        )
    )
    inputs = replace(PRIYA, secured_debts=(KESTREL, *debts))
    gaps = _gaps(inputs, spouse_loans_answer="yes", spouse_loans=rows)
    assert gaps == [
        "Answer whether each of your spouse's loans is on your Amounts Owed step.",
        "For each of your spouse's loans that is on your Amounts Owed step, choose which one it is.",
        "Enter who your spouse owes on each of their loans.",
        "Say what secures your spouse's loan from Demo Lender A.",
        "Describe the property that secures your spouse's loan from Demo Lender B.",
        "Enter the monthly payment on your spouse's loan from Demo Lender B.",
    ]
