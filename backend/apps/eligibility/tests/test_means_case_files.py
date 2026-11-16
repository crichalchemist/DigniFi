"""The browser's copies of the grouping, line 36's product and the rebuttal figure are pinned to
the server by case files both sides run."""

import json
from decimal import Decimal

import pytest
from django.conf import settings

from apps.eligibility.means_lines import (
    MISSING,
    MeansInputs,
    SecuredDebt,
    Vehicle,
    debt_lines,
    plan_product,
    rebuttal_figure,
    slot_candidates,
)

D = Decimal
FRONTEND_SRC = settings.BASE_DIR.parent / "frontend" / "src"
CASE_DIR = FRONTEND_SRC / "pages" / "meansTest"
NAMES = ("meansRowsCases.json", "meansProductCases.json", "meansRebuttalCases.json")
SKIP = "the frontend's source isn't here (compose's backend mounts backend/ only)"


def _cases(name):
    """The file's cases, or [] when it is absent (compose's backend mounts backend/ only)."""
    path = CASE_DIR / name
    return json.loads(path.read_text()) if path.is_file() else []


ROWS, PRODUCTS, REBUTTALS = (_cases(name) for name in NAMES)


def _amount(text):
    return None if text is None else D(text)


def _inputs(case):
    vehicles = tuple(
        Vehicle(ref=v["ref"], name=v["ref"], leased=v["leased"], claimed=v["claimed"])
        for v in case["vehicles"]
    )
    debts = tuple(
        SecuredDebt(
            ref=d["ref"],
            creditor=d["ref"],
            secured_by=d["secured_by"],
            on_home=d["on_home"],
            property="",
            monthly_payment=_amount(d["monthly_payment"]),
            payments_left=d["payments_left"],
            payment_changes=d["payment_changes"],
            total_60_months=_amount(d["total_60_months"]),
            placed=d["placed"],
        )
        for d in case["debts"]
    )
    choice = case["vehicle_choice"]
    return MeansInputs(
        line_1=D("0.00"),
        marital_status=case["marital_status"],
        ages=(40,),
        county=None,
        district="ilnd",
        vehicles=vehicles,
        secured_debts=debts,
        line_35_past_due=None,
        line_41a=D("0.00"),
        vehicle_choice=None if choice is None else tuple(choice),
        spouse_vehicles_answer=case["spouse_vehicles_answer"],
        spouse_loans_answer=case["spouse_loans_answer"],
    )


@pytest.mark.parametrize("name", NAMES)
def test_a_missing_case_file_fails_instead_of_skipping_where_the_frontend_is(name):
    if not FRONTEND_SRC.is_dir():
        pytest.skip(SKIP)
    assert (
        CASE_DIR / name
    ).is_file(), "the pin between the server's rules and the browser's is gone"


def test_the_case_files_hold_the_cases_the_plan_names():
    if not FRONTEND_SRC.is_dir():
        pytest.skip(SKIP)
    assert len(ROWS) >= 17
    assert len(PRODUCTS) >= 5
    assert len(REBUTTALS) >= 5


@pytest.mark.parametrize("case", ROWS, ids=[case["name"] for case in ROWS])
def test_the_grouping_case_file_holds_on_the_server(case):
    inputs = _inputs(case)
    candidates = slot_candidates(inputs)
    expected = case["expect"]
    assert (None if candidates is MISSING else [v.ref for v in candidates]) == expected[
        "candidates"
    ]
    assert debt_lines(inputs) == expected["lines"]


@pytest.mark.parametrize("case", PRODUCTS, ids=[case["name"] for case in PRODUCTS])
def test_the_product_case_file_holds_on_the_server(case):
    assert plan_product(D(case["payment"]), D(case["multiplier"])) == D(case["product"])


@pytest.mark.parametrize("case", REBUTTALS, ids=[case["name"] for case in REBUTTALS])
def test_the_rebuttal_case_file_holds_on_the_server(case):
    amounts = [D(text) for text in case["amounts"]]
    assert rebuttal_figure(D(case["line_39c"]), amounts) == D(case["figure"])
