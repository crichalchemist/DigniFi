"""Seed 6 synthetic personas for partner demos and E2E testing.

Each persona exercises a distinct eligibility path through the ILND
means test calculator and form generation pipeline.  SSNs use the
IRS-reserved 900-xx range so they can never collide with real data.
"""

import json
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.districts.dated_tables import NoTableInForce, fill_date, in_force
from apps.districts.models import District
from apps.eligibility.cmi import income_window
from apps.eligibility.models import MEDIAN_TABLE
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.forms.registry import build_field_values, packet
from apps.intake.asset_lines import ordered_assets, rows_on, shown_lines
from apps.intake.models import (
    AssetInfo,
    AssetLineAnswers,
    ClaimAnswers,
    Codebtor,
    DebtInfo,
    DebtorInfo,
    ExecutoryContract,
    ExpenseInfo,
    FilingFee,
    Household,
    IncomeInfo,
    IntakeSession,
    SOFACreditorPayment,
    SOFAPriorIncome,
    SOFAReport,
    SpouseIncome,
)

User = get_user_model()

DEMO_PASSWORD = "DigniFi-Demo-2026!"


def _no_business_and_no_assistance() -> dict:
    """3e2's Income-step answers for a person with no business or rental, no change ahead, no aid."""
    return {"business_and_rental": [], "income_now_different": "no", "assistance_answer": "no"}


def _wages_only(wages: Decimal) -> dict:
    """The Income step's ten amounts for a persona whose only income is wages: the rest $0."""
    amounts = dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00"))
    amounts["monthly_gross_wages"] = wages
    amounts.update(_no_business_and_no_assistance())
    return amounts


def _asset(line: str, value, description: str = "", entire=None, **details) -> dict:
    """One Schedule A/B row as the Assets step saves it: its line, the filer's text and values."""
    return {
        "ab_line": line,
        "details": details,
        "description": description,
        "current_value": None if value is None else Decimal(str(value)),
        "entire_value": None if entire is None else Decimal(str(entire)),
    }


def _car(value, entire, make, model, year, miles, who="only_you", **more) -> dict:
    """A line 3 row: the two values, the make and model, and who has an interest."""
    return _asset(
        "3",
        value,
        entire=entire,
        make=make,
        model=model,
        year=year,
        mileage=miles,
        who=who,
        **more,
    )


def _asset_lines(assets: list[dict], *yes: str) -> dict:
    """The Yes and No on every line shown: Yes where a row sits (and on any gate named), else No."""
    answers = dict.fromkeys({row["ab_line"] for row in assets} | set(yes), "yes")
    for line in shown_lines(answers):
        answers.setdefault(line.key, "no")
    return answers


def _claim(
    street,
    city,
    state,
    zip_code,
    *,
    last_4="",
    date="",
    street_2="",
    status=(),
    offset="no",
    priority="no",
    notice=(),
    link=None,
    lien=None,
    **more,
) -> dict:
    """The keys 3c3 adds to one amount owed: its address, date, answers and notice parties.

    link is an A/B position such as "3.1" (the seed resolves it with asset_at); it is no column.
    """
    row = {
        "street_address": street,
        "street_2": street_2,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "account_number": last_4,
        "date_incurred": date,
        "claim_status": list(status),
        "offset_answer": offset,
        "priority_answer": priority,
        "notice_parties": list(notice),
        **more,
    }
    if link is not None:
        row["link"] = link
    if lien is not None:
        row["lien"] = lien
    return row


def _party(name, street, city, state, zip_code, last_4) -> dict:
    """One notice party (someone else contacting the filer about a debt), with no id."""
    return {
        "name": name,
        "street_address": street,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "last_4": last_4,
    }


def asset_at(session, position: str) -> AssetInfo:
    """The row at an A/B position: "3.2" is the second row on line 3 in ordered_assets order.

    Rows are compared in Python, never filtered: the line is ciphertext in the table.
    """
    line, _, number = position.partition(".")
    rows = rows_on(ordered_assets(session), line)
    if not number.isdigit() or not 1 <= int(number) <= len(rows):
        raise LookupError(f"no row at A/B position {position}")
    return rows[int(number) - 1]


def claim_links(session, pairs) -> list[dict]:
    """Each ("debt", creditor name) or ("contract", counterparty name) as {"kind", "id"}.

    Names are decrypted and compared in Python, never filtered: they are ciphertext in the
    table. An unknown name raises LookupError (without the name, which is the filer's).
    """
    found = []
    for kind, name in pairs:
        rows = session.debts.all() if kind == "debt" else session.executory_contracts.all()
        attr = "creditor_name" if kind == "debt" else "counterparty_name"
        match = next((row for row in rows if getattr(row, attr) == name), None)
        if match is None:
            raise LookupError(f"no {kind} with that name on the session")
        found.append({"kind": kind, "id": match.pk})
    return found


# ── Persona data functions ──────────────────────────────────────────


def _maria_torres() -> dict:
    """Below-median single parent who asks for the fee to be waived. PRD primary persona."""
    return {
        "username": "demo_maria",
        "email": "maria.torres@demo.dignifi.org",
        "first_name": "Maria",
        "last_name": "Torres",
        "debtor": {
            "first_name": "Maria",
            "last_name": "Torres",
            "middle_name": "",
            "ssn": "900-11-0001",
            "date_of_birth": date(1988, 6, 15),
            "phone": "312-555-0101",
            "email": "maria.torres@demo.dignifi.org",
            "street_address": "2145 W Division St Apt 3",
            "city": "Chicago",
            "state": "IL",
            "zip_code": "60622",
        },
        "income": {
            "marital_status": "not_married",
            **_wages_only(Decimal("3200.00")),
            **dict.fromkeys(IncomeInfo.DEDUCTION_FIELDS, Decimal("0.00")),
            "payroll_tax": Decimal("400.00"),
            "assistance_answer": "yes",
            "noncash_assistance_kind": "SNAP (food stamps)",
            "noncash_assistance_value": Decimal("350.00"),
        },
        "household": {
            "county": "Cook",
            "members": [
                {
                    "relationship": "son",
                    "age": 8,
                    "lives_with_you": True,
                    "claimed_or_supported": True,
                },
                {
                    "relationship": "daughter",
                    "age": 5,
                    "lives_with_you": True,
                    "claimed_or_supported": True,
                },
            ],
        },
        "spouse_income": None,
        "expenses": {
            "expenses_include_others": "no",
            "rent_or_mortgage": Decimal("1100.00"),
            "utilities": Decimal("180.00"),
            "home_maintenance": Decimal("0.00"),
            "vehicle_insurance": Decimal("85.00"),
            "vehicle_maintenance": Decimal("40.00"),
            "food_and_groceries": Decimal("450.00"),
            "clothing": Decimal("60.00"),
            "medical_expenses": Decimal("75.00"),
            "childcare": Decimal("400.00"),
            "child_support_paid": Decimal("0.00"),
            "insurance_not_deducted": Decimal("120.00"),
            "other_expenses": Decimal("50.00"),
            "personal_care": Decimal("40.00"),
            "other_expenses_specify": "School supplies and fees",
        },
        "assets": [
            _car(6500, 6500, "Honda", "Civic", "2015", "120000"),
            _asset("6", 600, "Beds, sofa, kitchen table, dishes"),
            _asset("7", 200, "Old laptop, cell phone, 32-inch TV"),
            _asset("11", 250, "Everyday clothes and shoes"),
            _asset("16", 40),
            _asset("17", 340, "JPMorgan Chase", kind="checking"),
            # Her insurance policy has no cash value: typed $0, not left blank.
            _asset("31", 0, "Millbrook Mutual Life"),
        ],
        "debts": [
            {
                **_claim(
                    "1 Demo Way",
                    "Richmond",
                    "VA",
                    "23238",
                    last_4="1001",
                    date="2019–2025",
                    notice=[
                        _party(
                            "Lakefront Demo Recovery LLC",
                            "10 Demo Ct",
                            "Chicago",
                            "IL",
                            "60604",
                            "4004",
                        )
                    ],
                ),
                "creditor_name": "Brightwater Card Services",
                "debt_type": "credit_card",
                "amount_owed": Decimal("4200.00"),
                "monthly_payment": Decimal("85.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim(
                    "2 Demo Plaza",
                    "Chicago",
                    "IL",
                    "60611",
                    last_4="2002",
                    date="11/2025",
                    notice=[
                        _party(
                            "Prairie Demo Collections Inc.",
                            "20 Demo Ave",
                            "Oak Brook",
                            "IL",
                            "60523",
                            "5005",
                        )
                    ],
                ),
                "creditor_name": "Larkfield General Hospital",
                "debt_type": "medical",
                "amount_owed": Decimal("12800.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim("3 Demo Rd", "Riverwoods", "IL", "60015", last_4="3003", date="05/2024"),
                "creditor_name": "Ironbridge Card Company",
                "debt_type": "personal_loan",
                "amount_owed": Decimal("3500.00"),
                "monthly_payment": Decimal("120.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
        ],
        "contracts": [
            {
                "counterparty_name": "Division Demo Properties LLC",
                "street_address": "30 Demo St",
                "street_2": "",
                "city": "Chicago",
                "state": "IL",
                "zip_code": "60622",
                "contract_type": "lease",
                "lease_kind": "residential",
                "description": "Residential lease for 2145 W Division St Apt 3, 07/01/2026–06/30/2027, $1,100 a month",
                "owes_now": "no",
            },
        ],
        "codebtors": [],
        "claims": {"contracts_answer": "yes", "codebtors_answer": "no", "community_lived": "no"},
        "sofa": {
            "has_prior_income": True,
            "has_creditor_payments": True,
            "has_business": False,
            "prior_income": [
                {
                    "year": 2025,
                    "source": "Wages - CNA at Larkfield General Hospital",
                    "gross_amount": Decimal("38400.00"),
                },
                {
                    "year": 2024,
                    "source": "Wages - CNA at Larkfield General Hospital",
                    "gross_amount": Decimal("37000.00"),
                },
            ],
            "creditor_payments": [
                {
                    "creditor_name": "Brightwater Card Services",
                    "total_paid": Decimal("1020.00"),
                    "dates_of_payments": "Monthly Jan-Mar 2026",
                },
                {
                    "creditor_name": "Ironbridge Card Company",
                    "total_paid": Decimal("720.00"),
                    "dates_of_payments": "Monthly Jan-Mar 2026",
                },
            ],
        },
        # Form 101 line 8, and for the waiver 103B lines 4, 5, 7 and 9 (3f spec §10)
        "filing_fee": {
            "payment_choice": "waiver",
            "income_change_answer": "no",
            "installments_explanation": (
                "I support two children on what I earn. After rent, food, the car and the "
                "children's costs, there is not enough left each month to pay the fee, even in "
                "parts."
            ),
            "others_covered_answer": "no",
            "expense_change_answer": "no",
        },
    }


def _james_washington() -> dict:
    """Borderline case — just below single-filer median ($73,180)."""
    return {
        "username": "demo_james",
        "email": "james.washington@demo.dignifi.org",
        "first_name": "James",
        "last_name": "Washington",
        "debtor": {
            "first_name": "James",
            "last_name": "Washington",
            "middle_name": "D",
            "ssn": "900-22-0002",
            "date_of_birth": date(1975, 3, 22),
            "phone": "312-555-0202",
            "email": "james.washington@demo.dignifi.org",
            "street_address": "850 N State St Apt 1204",
            "city": "Chicago",
            "state": "IL",
            "zip_code": "60610",
        },
        "income": {
            "marital_status": "not_married",
            **_wages_only(Decimal("5833.00")),
            "payroll_tax": Decimal("1288.00"),
            "payroll_union_dues": Decimal("45.00"),
        },
        "household": {"county": "Cook", "members": []},
        "spouse_income": None,
        "expenses": {
            "expenses_include_others": "no",
            "rent_or_mortgage": Decimal("1650.00"),
            "utilities": Decimal("120.00"),
            "home_maintenance": Decimal("0.00"),
            "vehicle_insurance": Decimal("110.00"),
            "vehicle_maintenance": Decimal("50.00"),
            "food_and_groceries": Decimal("400.00"),
            "clothing": Decimal("80.00"),
            "medical_expenses": Decimal("50.00"),
            "childcare": Decimal("0.00"),
            "child_support_paid": Decimal("0.00"),
            "insurance_not_deducted": Decimal("200.00"),
            "other_expenses": Decimal("100.00"),
            "home_insurance": Decimal("15.00"),
            "personal_care": Decimal("40.00"),
            "entertainment": Decimal("45.00"),
            "other_expenses_specify": "Work boots and small tools for my job",
        },
        "assets": [
            _car(14000, 14000, "Toyota", "Camry", "2019", "78000"),
            _asset("6", 500, "Bed, couch, table, kitchenware (secondhand)"),
            _asset("7", 400, "TV, laptop, cell phone"),
            _asset("11", 300, "Everyday clothes and work clothes"),
            _asset("16", 40),
            _asset("17", 1200, "Bank of America", kind="checking"),
        ],
        "debts": [
            {
                **_claim(
                    "PO Box 90222", "Sioux Falls", "SD", "57117", last_4="4402", date="06/2015–2026"
                ),
                "creditor_name": "Meridale National Bank",
                "debt_type": "credit_card",
                "amount_owed": Decimal("9800.00"),
                "monthly_payment": Decimal("200.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim(
                    "PO Box 90122",
                    "Plano",
                    "TX",
                    "75025",
                    last_4="7702",
                    date="12/2023",
                    offset=None,
                    priority=None,
                    link="3.1",
                    lien={"kinds": ["agreement"], "other": ""},
                ),
                "creditor_name": "Crestway Auto Credit",
                "debt_type": "auto_loan",
                "amount_owed": Decimal("8500.00"),
                "monthly_payment": Decimal("350.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
                "is_secured": True,
                "collateral_description": "2019 Toyota Camry",
            },
        ],
        "contracts": [
            {
                "counterparty_name": "Gold Coast Example Residential LLC",
                "street_address": "850 N State St",
                "street_2": "c/o Management Office",
                "city": "Chicago",
                "state": "IL",
                "zip_code": "60610",
                "contract_type": "lease",
                "lease_kind": "residential",
                "description": "Residential lease, Apt 1204, 06/01/2026–05/31/2027, $1,650 a month",
                "owes_now": "no",
            },
        ],
        "codebtors": [],
        "claims": {"contracts_answer": "yes", "codebtors_answer": "no", "community_lived": "no"},
        # Form 101 line 8, and for the waiver 103B lines 4, 5, 7 and 9 (3f spec §10)
        "filing_fee": {"payment_choice": "pay_in_full"},
    }


def _priya_sharma() -> dict:
    """Above-median — fails means test. Tests ineligibility path."""
    return {
        "username": "demo_priya",
        "email": "priya.sharma@demo.dignifi.org",
        "first_name": "Priya",
        "last_name": "Sharma",
        "debtor": {
            "first_name": "Priya",
            "last_name": "Sharma",
            "middle_name": "",
            "ssn": "900-33-0003",
            "date_of_birth": date(1982, 11, 8),
            "phone": "312-555-0303",
            "email": "priya.sharma@demo.dignifi.org",
            "street_address": "456 W Fullerton Pkwy",
            "city": "Chicago",
            "state": "IL",
            "zip_code": "60614",
        },
        "income": {
            "marital_status": "married_together",
            # Her own $12,000/month is $144,000/year, above the $137,902 HH4 median by
            # itself; with her husband's $1,800 (122A-1 Column B) it is $165,600/year.
            **_wages_only(Decimal("12000.00")),
            "payroll_tax": Decimal("2450.00"),
            "payroll_voluntary_retirement": Decimal("600.00"),
            "payroll_insurance": Decimal("620.00"),
        },
        "household": {
            "county": "Cook",
            "members": [
                {
                    "relationship": "spouse",
                    "age": 45,
                    "lives_with_you": True,
                    "claimed_or_supported": True,
                    "spouse_is_dependent": False,
                },
                {
                    "relationship": "daughter",
                    "age": 10,
                    "lives_with_you": True,
                    "claimed_or_supported": True,
                },
                {
                    "relationship": "son",
                    "age": 7,
                    "lives_with_you": True,
                    "claimed_or_supported": True,
                },
            ],
        },
        "spouse_income": {**_wages_only(Decimal("1800.00")), "payroll_tax": Decimal("250.00")},
        "expenses": {
            "expenses_include_others": "yes",
            "rent_or_mortgage": Decimal("2800.00"),
            "utilities": Decimal("250.00"),
            "home_maintenance": Decimal("100.00"),
            "vehicle_insurance": Decimal("180.00"),
            "vehicle_maintenance": Decimal("60.00"),
            "food_and_groceries": Decimal("800.00"),
            "clothing": Decimal("150.00"),
            "medical_expenses": Decimal("100.00"),
            "childcare": Decimal("1200.00"),
            "child_support_paid": Decimal("0.00"),
            "insurance_not_deducted": Decimal("350.00"),
            "other_expenses": Decimal("200.00"),
            "home_insurance": Decimal("20.00"),
            "personal_care": Decimal("60.00"),
            "entertainment": Decimal("80.00"),
            "charitable_contributions": Decimal("50.00"),
            "taxes_not_deducted": Decimal("200.00"),
            "taxes_specify": "IRS installment agreement, 2025 tax",
            "other_expenses_specify": "Children's after-school activities",
        },
        "assets": [
            _car(20500, 20500, "Honda", "CR-V EX", "2021", "41000"),
            _asset("6", 2500, "Household goods and furniture"),
            _asset("7", 1500, "Family laptop, two phones, TV"),
            _asset("11", 800, "Clothes"),
            _asset("12", 1200, "Wedding and engagement rings"),
            # Both joint accounts: the whole balance is her portion (her answer).
            _asset("17", 1900, "JPMorgan Chase", kind="checking"),
            _asset("17", 8500, "JPMorgan Chase", kind="savings"),
            _asset("21", 31000, "Vanguard", kind="401k"),
            # Line 31's text box is the form's "Company name". Her term life and her disability
            # policy are with two companies, and the form has no box for the type of policy.
            _asset("31", 0, "Wrenfield Life", beneficiary="Spouse"),
            _asset("31", 0, "Alderbrook Assurance"),
        ],
        "debts": [
            {
                **_claim(
                    "P.O. Box 9313", "El Paso", "TX", "79998", last_4="3313", date="2024–2025"
                ),
                "creditor_name": "Silverpine Card Services",
                "debt_type": "credit_card",
                "amount_owed": Decimal("22000.00"),
                "monthly_payment": Decimal("500.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim(
                    "1653 W Congress Pkwy",
                    "Chicago",
                    "IL",
                    "60612",
                    last_4="3323",
                    date="02/2025",
                    notice=[
                        _party(
                            "Lakeshore Medical Recovery LLC",
                            "P.O. Box 9333",
                            "Chicago",
                            "IL",
                            "60690",
                            "7310",
                        )
                    ],
                ),
                "creditor_name": "Westhaven University Medical Center",
                "debt_type": "medical",
                "amount_owed": Decimal("35000.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Kestrel Auto Finance",
                "debt_type": "auto_loan",
                "amount_owed": Decimal("14900.00"),
                "monthly_payment": Decimal("450.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
                "is_secured": True,
                "collateral_description": "2021 Honda CR-V EX",
                **_claim(
                    "P.O. Box 9303",
                    "Torrance",
                    "CA",
                    "90503",
                    last_4="3303",
                    date="11/2023",
                    offset=None,
                    priority=None,
                    link="3.1",
                    lien={"kinds": ["agreement"], "other": ""},
                ),
            },
        ],
        "contracts": [
            {
                "counterparty_name": "Fullerton Parkway Apartments LLC",
                "street_address": "456 W Fullerton Pkwy",
                "street_2": "Management Office",
                "city": "Chicago",
                "state": "IL",
                "zip_code": "60614",
                "contract_type": "lease",
                "lease_kind": "residential",
                "description": "Residential lease, 456 W Fullerton Pkwy, to 07/31/2027, $2,800 a month",
                "owes_now": "no",
            },
        ],
        "codebtors": [
            {
                "name": "Rohan Sharma",
                "street_address": "456 W Fullerton Pkwy",
                "city": "Chicago",
                "state": "IL",
                "zip_code": "60614",
                "relationship": "spouse",
                "links": [("debt", "Westhaven University Medical Center")],
            },
        ],
        "claims": {"contracts_answer": "yes", "codebtors_answer": "yes", "community_lived": "no"},
        # Form 101 line 8, and for the waiver 103B lines 4, 5, 7 and 9 (3f spec §10)
        "filing_fee": {"payment_choice": "pay_in_full"},
    }


def _deshawn_mitchell() -> dict:
    """Asset-heavy homeowner — tests exemption calculations."""
    return {
        "username": "demo_deshawn",
        "email": "deshawn.mitchell@demo.dignifi.org",
        "first_name": "DeShawn",
        "last_name": "Mitchell",
        "debtor": {
            "first_name": "DeShawn",
            "last_name": "Mitchell",
            "middle_name": "R",
            "ssn": "900-44-0004",
            "date_of_birth": date(1980, 9, 3),
            "phone": "312-555-0404",
            "email": "deshawn.mitchell@demo.dignifi.org",
            "street_address": "7823 S Sangamon St",
            "city": "Chicago",
            "state": "IL",
            "zip_code": "60620",
        },
        "income": {
            "marital_status": "married_together",
            **_wages_only(Decimal("3500.00")),
            "payroll_tax": Decimal("450.00"),
        },
        "household": {
            "county": "Cook",
            "members": [
                {
                    "relationship": "spouse",
                    "age": 44,
                    "lives_with_you": True,
                    "claimed_or_supported": True,
                    "spouse_is_dependent": False,
                },
            ],
        },
        "spouse_income": {**_wages_only(Decimal("1000.00")), "payroll_tax": Decimal("115.00")},
        "expenses": {
            "expenses_include_others": "yes",
            "rent_or_mortgage": Decimal("0.00"),
            "utilities": Decimal("200.00"),
            "home_maintenance": Decimal("100.00"),
            "vehicle_insurance": Decimal("95.00"),
            "vehicle_maintenance": Decimal("50.00"),
            "food_and_groceries": Decimal("350.00"),
            "clothing": Decimal("50.00"),
            "medical_expenses": Decimal("60.00"),
            "childcare": Decimal("0.00"),
            "child_support_paid": Decimal("0.00"),
            "insurance_not_deducted": Decimal("150.00"),
            "other_expenses": Decimal("40.00"),
            "personal_care": Decimal("40.00"),
            "entertainment": Decimal("25.00"),
            "charitable_contributions": Decimal("50.00"),
            "other_expenses_specify": "Printer ink, paper and postage",
        },
        "assets": [
            _asset(
                "1",
                180000,
                entire=180000,
                street="7823 S Sangamon St",
                city="Chicago",
                state="IL",
                zip="60620",
                county="Cook",
                property_kinds=["single_family"],
                who="only_you",
                community=False,
                nature="Fee simple",
                lives_here="yes",
            ),
            _car(8000, 8000, "Ford", "F-150", "2012", "168000"),
            _asset("6", 1500, "Furniture, appliances and beds"),
            _asset("7", 400, "TV, laptop and phone"),
            _asset("11", 300, "Everyday clothes and work boots"),
            _asset("12", 600, "Wedding band and watch"),
            _asset("16", 60),
            _asset("17", 640, "PNC Bank", kind="checking"),
            _asset("21", 12000, "Fidelity", kind="401k"),
        ],
        "debts": [
            {
                **_claim(
                    "PO Box 4401",
                    "Chicago",
                    "IL",
                    "60680",
                    last_4="0441",
                    date="2019",
                    offset=None,
                    priority=None,
                    link="1.1",
                    lien={"kinds": ["agreement"], "other": ""},
                ),
                "creditor_name": "Harrowgate Home Loans",
                "debt_type": "mortgage",
                "amount_owed": Decimal("160000.00"),
                "monthly_payment": Decimal("1200.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
                "is_secured": True,
                "collateral_description": "Single-family home, 7823 S Sangamon St",
                "home_payment_line": "first",
            },
            {
                **_claim("PO Box 4402", "Chicago", "IL", "60680", last_4="0442", date="2017–2025"),
                "creditor_name": "Tallgrass Credit Management",
                "debt_type": "credit_card",
                "amount_owed": Decimal("6700.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim(
                    "PO Box 4403",
                    "Chicago",
                    "IL",
                    "60680",
                    last_4="0443",
                    date="2025",
                    notice=[
                        _party(
                            "Demo Recovery Services",
                            "PO Box 4405",
                            "Chicago",
                            "IL",
                            "60680",
                            "7443",
                        )
                    ],
                ),
                "creditor_name": "Lakeline Electric",
                "debt_type": "utility",
                "amount_owed": Decimal("800.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim(
                    "PO Box 4404",
                    "Chicago",
                    "IL",
                    "60680",
                    last_4="0444",
                    date="2025",
                    notice=[
                        _party(
                            "Demo Medical Collections",
                            "PO Box 4406",
                            "Chicago",
                            "IL",
                            "60680",
                            "7444",
                        )
                    ],
                ),
                "creditor_name": "Southmoor Health",
                "debt_type": "medical",
                "amount_owed": Decimal("4200.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
        ],
        "contracts": [],
        "codebtors": [],
        "claims": {"contracts_answer": "no", "codebtors_answer": "no", "community_lived": "no"},
        # Form 101 line 8, and for the waiver 103B lines 4, 5, 7 and 9 (3f spec §10)
        "filing_fee": {"payment_choice": "installments"},
    }


def _sarah_chen() -> dict:
    """Simplest case — single, no assets, asks for the fee to be waived."""
    return {
        "username": "demo_sarah",
        "email": "sarah.chen@demo.dignifi.org",
        "first_name": "Sarah",
        "last_name": "Chen",
        "debtor": {
            "first_name": "Sarah",
            "last_name": "Chen",
            "middle_name": "",
            "ssn": "900-55-0005",
            "date_of_birth": date(1995, 1, 20),
            "phone": "312-555-0505",
            "email": "sarah.chen@demo.dignifi.org",
            "street_address": "1520 N Damen Ave Apt 2F",
            "city": "Chicago",
            "state": "IL",
            "zip_code": "60622",
        },
        "income": {
            "marital_status": "not_married",
            **_wages_only(Decimal("2000.00")),
            "payroll_tax": Decimal("250.00"),
        },
        "household": {
            "county": "Cook",
            "members": [
                {
                    "relationship": "roommate",
                    "age": 29,
                    "lives_with_you": True,
                    "claimed_or_supported": False,
                },
            ],
        },
        "spouse_income": None,
        "expenses": {
            "expenses_include_others": "no",
            "rent_or_mortgage": Decimal("850.00"),
            "utilities": Decimal("80.00"),
            "home_maintenance": Decimal("0.00"),
            "vehicle_insurance": Decimal("0.00"),
            "vehicle_maintenance": Decimal("0.00"),
            "food_and_groceries": Decimal("250.00"),
            "clothing": Decimal("30.00"),
            "medical_expenses": Decimal("20.00"),
            "childcare": Decimal("0.00"),
            "child_support_paid": Decimal("0.00"),
            "insurance_not_deducted": Decimal("0.00"),
            "other_expenses": Decimal("0.00"),
            "personal_care": Decimal("30.00"),
            "entertainment": Decimal("20.00"),
        },
        "assets": [],
        "debts": [
            {
                **_claim(
                    "60 Demo Way", "Wilkes-Barre", "PA", "18773", last_4="6006", date="2016–2020"
                ),
                "creditor_name": "Keelson Loan Servicing",
                "debt_type": "student_loan",
                "amount_owed": Decimal("28000.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim(
                    "70 Demo Plaza",
                    "Chicago",
                    "IL",
                    "60612",
                    last_4="7007",
                    date="02/2026",
                    street_2="Lakemont Health Patient Accounts",
                    notice=[
                        _party(
                            "Wicker Demo Recovery LLC",
                            "80 Demo Ct",
                            "Oak Brook",
                            "IL",
                            "60523",
                            "8008",
                        )
                    ],
                ),
                "creditor_name": "Lakemont University Hospital",
                "debt_type": "medical",
                "amount_owed": Decimal("3400.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
        ],
        "contracts": [
            {
                "counterparty_name": "Damen Demo Flats LLC",
                "street_address": "90 Demo St",
                "street_2": "",
                "city": "Chicago",
                "state": "IL",
                "zip_code": "60622",
                "contract_type": "lease",
                "lease_kind": "residential",
                "description": "Residential lease, one bedroom at 1520 N Damen Ave Apt 2F, 07/01/2026–06/30/2027, $850 a month",
                "owes_now": "no",
            },
        ],
        "codebtors": [],
        "claims": {"contracts_answer": "yes", "codebtors_answer": "no", "community_lived": "no"},
        # Form 101 line 8, and for the waiver 103B lines 4, 5, 7 and 9 (3f spec §10)
        "filing_fee": {
            "payment_choice": "waiver",
            "income_change_answer": "no",
            "installments_explanation": (
                "I have no savings. My pay covers rent, food and my bus pass, and what is left "
                "each month goes to bills I already owe."
            ),
            "others_covered_answer": "no",
            "expense_change_answer": "no",
        },
    }


def _andres_kettleby() -> dict:
    """Gig driver, below median. Pays the fee in installments."""
    return {
        "username": "demo_andres",
        "email": "andres.kettleby@demo.dignifi.org",
        "first_name": "Andrés",
        "last_name": "Kettleby",
        "debtor": {
            "first_name": "Andrés",
            "last_name": "Kettleby",
            "middle_name": "J",
            "ssn": "900-66-0006",
            "date_of_birth": date(1988, 4, 12),
            "phone": "630-555-0161",
            "email": "andres.kettleby@demo.dignifi.org",
            "street_address": "1418 Marquette Ave Apt 2",
            "city": "Aurora",
            "state": "IL",
            "zip_code": "60505",
        },
        "income": {
            "marital_status": "not_married",
            **dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00")),
            **_no_business_and_no_assistance(),
            # His driving ($4,200 from the apps less $830 of driving costs) is a business.
            "business_and_rental": [
                {
                    "kind": "business",
                    "description": "Rideshare and delivery driving",
                    "gross": Decimal("4200.00"),
                    "expenses": Decimal("830.00"),
                }
            ],
        },
        "household": {
            "county": "Kane",
            "members": [
                {
                    "relationship": "daughter",
                    "age": 9,
                    "lives_with_you": True,
                    "claimed_or_supported": True,
                },
            ],
        },
        "spouse_income": None,
        "expenses": {
            "expenses_include_others": "no",
            "rent_or_mortgage": Decimal("1150.00"),
            "utilities": Decimal("210.00"),
            "home_maintenance": Decimal("0.00"),
            "vehicle_insurance": Decimal("165.00"),
            "vehicle_maintenance": Decimal("60.00"),
            "food_and_groceries": Decimal("520.00"),
            "clothing": Decimal("60.00"),
            "medical_expenses": Decimal("45.00"),
            "childcare": Decimal("180.00"),
            "child_support_paid": Decimal("0.00"),
            "insurance_not_deducted": Decimal("0.00"),
            "other_expenses": Decimal("0.00"),
            "home_insurance": Decimal("15.00"),
            "personal_care": Decimal("40.00"),
            "entertainment": Decimal("30.00"),
            "charitable_contributions": Decimal("20.00"),
            "taxes_not_deducted": Decimal("150.00"),
            "taxes_specify": "2026 estimated income tax",
        },
        "assets": [
            # Leased, so $0 and $0 (his answer); the lease is on Schedule G.
            _car(0, 0, "Toyota", "Corolla Hybrid", "2024", "61000", other_info="Leased"),
            # His half of a car titled to him and his brother.
            _car(4300, 8600, "Honda", "Fit", "2017", "96000", who="with_someone"),
            _asset("6", 1200, "Beds, couch, table, kitchen things"),
            _asset("7", 400, "Phone, TV"),
            _asset("11", 300, "Clothes"),
            _asset("16", 60),
            _asset("17", 412, "Harborline Bank", kind="checking"),
            _asset("17", 85, "Prairie Line Credit Union", kind="savings"),
            _asset("38", 310, "Driving payouts already earned, not yet paid by the apps"),
            _asset("40", 150, "Insulated delivery bags, phone mount, dash camera"),
        ],
        "debts": [
            {
                **_claim(
                    "PO Box 48210",
                    "Schaumburg",
                    "IL",
                    "60168",
                    date="08/15/2022",
                    offset=None,
                    priority=None,
                    link="3.2",
                    lien={"kinds": ["agreement"], "other": ""},
                ),
                "creditor_name": "Copperline Auto Finance",
                "debt_type": "auto_loan",
                "amount_owed": Decimal("7800.00"),
                # His brother drives the car and pays the loan he co-signed
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
                "is_secured": True,
                "collateral_description": "2017 Honda Fit, co-owned with my brother",
            },
            {
                **_claim("PO Box 77031", "Dallas", "TX", "75377", date="07/20/2025"),
                "creditor_name": "Bright Signal Wireless",
                "debt_type": "utility",
                "amount_owed": Decimal("640.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim(
                    "2500 Ridge Crest Pkwy",
                    "Aurora",
                    "IL",
                    "60504",
                    date="02/08/2025",
                    notice=[
                        _party(
                            "Ashgrove Recovery Group",
                            "900 Commerce Dr Ste 210",
                            "Oak Brook",
                            "IL",
                            "60523",
                            "4417",
                        )
                    ],
                ),
                "creditor_name": "Calumet Ridge Medical Center",
                "debt_type": "medical",
                "amount_owed": Decimal("3850.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim("1650 N Farnsworth Ave", "Aurora", "IL", "60505", date="10/03/2025"),
                "creditor_name": "Driveline Tire & Auto",
                "debt_type": "credit_card",
                "amount_owed": Decimal("1180.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "business",
            },
            {
                **_claim(
                    "2700 Ogden Ave",
                    "Downers Grove",
                    "IL",
                    "60515",
                    date="01/14/2026",
                    priority="not_sure",
                ),
                "creditor_name": "Illinois State Toll Highway Authority",
                "debt_type": "other",
                "amount_owed": Decimal("380.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim("PO Box 31544", "Wilmington", "DE", "19850", date="09/05/2025"),
                "creditor_name": "Tallowfield Lending Co.",
                "debt_type": "personal_loan",
                "amount_owed": Decimal("4100.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim("PO Box 60917", "Phoenix", "AZ", "85082", date="05/10/2019"),
                "creditor_name": "Northgate Card Services",
                "debt_type": "credit_card",
                "amount_owed": Decimal("6420.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim(
                    "310 E Galena Blvd", "Aurora", "IL", "60505", date="03/02/2020", offset="yes"
                ),
                "creditor_name": "Prairie Line Credit Union",
                "debt_type": "credit_card",
                "amount_owed": Decimal("1760.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim(
                    "88 Ridgeway Ct",
                    "Naperville",
                    "IL",
                    "60540",
                    date="12/31/2024",
                    status=("disputed",),
                ),
                "creditor_name": "Hollowmere Residential LLC",
                "debt_type": "other",
                "amount_owed": Decimal("1850.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                **_claim("PO Box 15022", "Columbus", "OH", "43218", date="10/18/2021"),
                "creditor_name": "Sablewood Bank",
                "debt_type": "credit_card",
                "amount_owed": Decimal("2980.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
        ],
        "contracts": [
            {
                "counterparty_name": "Northlight Auto Leasing",
                "street_address": "PO Box 92650",
                "street_2": "",
                "city": "Itasca",
                "state": "IL",
                "zip_code": "60143",
                "contract_type": "lease",
                "lease_kind": "vehicle",
                "description": "Lease of a 2024 Toyota Corolla Hybrid, 36 months, 03/01/2025–02/29/2028",
                "monthly_payment": Decimal("389.00"),
                "vehicle_link": "3.1",
                "owes_now": "no",
            },
            {
                "counterparty_name": "Fox Run Property Management",
                "street_address": "2200 W Indian Trail",
                "street_2": "",
                "city": "Aurora",
                "state": "IL",
                "zip_code": "60506",
                "contract_type": "lease",
                "lease_kind": "residential",
                "description": "Apartment lease, 06/01/2026–05/31/2027",
                "owes_now": "no",
            },
        ],
        "codebtors": [
            {
                "name": "Mateo Kettleby",
                "street_address": "377 Douglas Ave",
                "city": "Elgin",
                "state": "IL",
                "zip_code": "60120",
                "relationship": "relative",
                "links": [("debt", "Copperline Auto Finance")],
            },
        ],
        "claims": {"contracts_answer": "yes", "codebtors_answer": "yes", "community_lived": "no"},
        # Form 101 line 8, and for the waiver 103B lines 4, 5, 7 and 9 (3f spec §10)
        "filing_fee": {"payment_choice": "installments"},
    }


def _walked(persona: Callable[[], dict], *yes: str) -> Callable[[], dict]:
    """A persona with its Schedule A/B answers: Yes on each line with a row and on any gate named."""

    def build() -> dict:
        data = persona()
        data["asset_lines"] = _asset_lines(data["assets"], *yes)
        return data

    return build


PERSONAS: dict[str, Callable[[], dict]] = {
    "maria": _walked(_maria_torres),
    "james": _walked(_james_washington),
    "priya": _walked(_priya_sharma),
    "deshawn": _walked(_deshawn_mitchell),
    "sarah": _walked(_sarah_chen),
    # Part 5 is his: line 37 is Yes (driving is his business); line 46 stays No.
    "andres": _walked(_andres_kettleby, "37"),
}


# ── Management command ──────────────────────────────────────────────


class Command(BaseCommand):
    help = "Seed 6 synthetic demo personas for partner demos and E2E testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo accounts before recreating",
        )
        parser.add_argument(
            "--persona",
            type=str,
            choices=list(PERSONAS.keys()),
            help="Seed a single persona instead of all 6",
        )

    def handle(self, *args, **options):
        district = District.objects.filter(code="ilnd").first()
        if not district:
            self.stderr.write(
                self.style.ERROR(
                    "ILND district not found. " "Run: python manage.py loaddata ilnd_2025_data"
                )
            )
            return

        # Every persona's means test needs a median table in force today; check before
        # --reset deletes anything, so a refused reseed leaves the existing personas.
        try:
            in_force(district.median_incomes.all(), fill_date(), MEDIAN_TABLE, district.code)
        except NoTableInForce:
            self.stderr.write(
                self.style.ERROR(
                    "No ILND median income table is in force today, so nothing was changed. "
                    "Add the current table as docs/REFERENCE_TABLES.md describes, then run: "
                    "python manage.py loaddata ilnd_2025_data"
                )
            )
            return

        targets = (
            {options["persona"]: PERSONAS[options["persona"]]} if options["persona"] else PERSONAS
        )

        if options["reset"]:
            usernames = [fn()["username"] for fn in targets.values()]
            deleted, _ = User.objects.filter(username__in=usernames).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} objects (cascade)"))

        for persona_fn in targets.values():
            data = persona_fn()
            if User.objects.filter(username=data["username"]).exists():
                self.stdout.write(
                    self.style.NOTICE(
                        f"  {data['username']} already exists " f"(use --reset to recreate)"
                    )
                )
                continue

            self._create_persona(data, district)
            self.stdout.write(
                self.style.SUCCESS(f"  Created {data['username']} " f"(password: {DEMO_PASSWORD})")
            )

    @transaction.atomic
    def _create_persona(self, data: dict, district: District) -> None:
        """Create user, intake session, and all related records."""
        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=DEMO_PASSWORD,
            first_name=data["first_name"],
            last_name=data["last_name"],
        )

        session = IntakeSession.objects.create(
            user=user,
            district=district,
            status="completed",
            current_step=7,
        )

        DebtorInfo.objects.create(session=session, **data["debtor"])
        income = dict(data["income"])
        entries = income.pop("business_and_rental")
        income_row = IncomeInfo(session=session, **income)
        income_row.store_entries(entries)
        income_row.income_period_end = income_window(fill_date())[1]
        income_row.save()
        household = Household(session=session, county=data["household"]["county"])
        household.store_members(data["household"]["members"])
        household.save()
        if data["spouse_income"] is not None:
            spouse = dict(data["spouse_income"])
            spouse_entries = spouse.pop("business_and_rental")
            spouse_row = SpouseIncome(session=session, **spouse)
            spouse_row.store_entries(spouse_entries)
            spouse_row.save()
        ExpenseInfo.objects.create(session=session, **data["expenses"])

        for asset in data["assets"]:
            row = AssetInfo(session=session, **{k: v for k, v in asset.items() if k != "details"})
            row.set_details(asset["details"])
            row.save()
        AssetLineAnswers.objects.create(session=session, answers=json.dumps(data["asset_lines"]))

        for debt in data["debts"]:
            row = dict(debt)
            link = row.pop("link", None)
            claim_status = row.pop("claim_status")
            lien = row.pop("lien", None)
            parties = row.pop("notice_parties")
            debt_row = DebtInfo(session=session, **row)
            if link is not None:
                debt_row.secured_by = asset_at(session, link)
            debt_row.claim_status = json.dumps(claim_status)
            debt_row.lien = None if lien is None else json.dumps(lien)
            debt_row.store_notice_parties(parties)
            debt_row.save()

        for contract in data["contracts"]:
            row = dict(contract)
            vehicle_link = row.pop("vehicle_link", None)
            if vehicle_link is not None:
                row["vehicle_asset"] = asset_at(session, vehicle_link)
            ExecutoryContract.objects.create(session=session, **row)

        for codebtor in data["codebtors"]:
            row = dict(codebtor)
            pairs = row.pop("links")
            Codebtor.objects.create(
                session=session, links=json.dumps(claim_links(session, pairs)), **row
            )

        ClaimAnswers.objects.create(session=session, answers=json.dumps(data["claims"]))

        # Create SOFA report and related data (Form 107)
        sofa_data = dict(data.get("sofa", {}))
        if sofa_data:
            prior_income_rows = sofa_data.pop("prior_income", [])
            creditor_payment_rows = sofa_data.pop("creditor_payments", [])
            report = SOFAReport.objects.create(session=session, **sofa_data)
            for row in prior_income_rows:
                SOFAPriorIncome.objects.create(report=report, **row)
            for row in creditor_payment_rows:
                SOFACreditorPayment.objects.create(report=report, **row)

        # The filing-fee page's answers, which every persona gives after Complete
        FilingFee.objects.create(session=session, **data["filing_fee"])

        # Run means test calculation
        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        # Check that every form in an eligible persona's packet resolves (none are stored)
        if result["passes_means_test"]:
            for form_type in packet(session):
                try:
                    build_field_values(form_type, session)
                except Exception as exc:
                    self.stderr.write(self.style.WARNING(f"    Skipped {form_type}: {exc}"))
