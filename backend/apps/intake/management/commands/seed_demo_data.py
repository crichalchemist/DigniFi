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
from apps.intake.asset_lines import shown_lines
from apps.intake.models import (
    AssetInfo,
    AssetLineAnswers,
    DebtInfo,
    DebtorInfo,
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


def _asset(line: str, value, description: str = "", entire=None, owed="0.00", **details) -> dict:
    """One Schedule A/B row as the Assets step saves it: its line, the filer's text and values."""
    return {
        "ab_line": line,
        "details": details,
        "description": description,
        "current_value": None if value is None else Decimal(str(value)),
        "entire_value": None if entire is None else Decimal(str(entire)),
        "amount_owed": Decimal(owed),
    }


def _car(value, entire, make, model, year, miles, who="only_you", owed="0.00", **more) -> dict:
    """A line 3 row: the two values, the make and model, and who has an interest."""
    return _asset(
        "3",
        value,
        entire=entire,
        owed=owed,
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
            "vehicle_payment": Decimal("0.00"),
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
                "creditor_name": "Brightwater Card Services",
                "debt_type": "credit_card",
                "amount_owed": Decimal("4200.00"),
                "monthly_payment": Decimal("85.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Larkfield General Hospital",
                "debt_type": "medical",
                "amount_owed": Decimal("12800.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Ironbridge Card Company",
                "debt_type": "personal_loan",
                "amount_owed": Decimal("3500.00"),
                "monthly_payment": Decimal("120.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
        ],
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
            "vehicle_payment": Decimal("350.00"),
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
            _car(14000, 14000, "Toyota", "Camry", "2019", "78000", owed="8500.00"),
            _asset("6", 500, "Bed, couch, table, kitchenware (secondhand)"),
            _asset("7", 400, "TV, laptop, cell phone"),
            _asset("11", 300, "Everyday clothes and work clothes"),
            _asset("16", 40),
            _asset("17", 1200, "Bank of America", kind="checking"),
        ],
        "debts": [
            {
                "creditor_name": "Meridale National Bank",
                "debt_type": "credit_card",
                "amount_owed": Decimal("9800.00"),
                "monthly_payment": Decimal("200.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
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
            "vehicle_payment": Decimal("450.00"),
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
                "creditor_name": "Silverpine Card Services",
                "debt_type": "credit_card",
                "amount_owed": Decimal("22000.00"),
                "monthly_payment": Decimal("500.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Westhaven University Medical Center",
                "debt_type": "medical",
                "amount_owed": Decimal("35000.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
        ],
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
            "rent_or_mortgage": Decimal("1200.00"),
            "utilities": Decimal("200.00"),
            "home_maintenance": Decimal("100.00"),
            "vehicle_payment": Decimal("0.00"),
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
                owed="160000.00",
                street="7823 S Sangamon St",
                city="Chicago",
                state="IL",
                zip="60620",
                county="Cook",
                property_kinds=["single_family"],
                who="only_you",
                community=False,
                nature="Fee simple",
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
                "creditor_name": "Harrowgate Home Loans",
                "debt_type": "mortgage",
                "amount_owed": Decimal("160000.00"),
                "monthly_payment": Decimal("1200.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
                "is_secured": True,
                "collateral_description": "Single-family home, 7823 S Sangamon St",
            },
            {
                "creditor_name": "Tallgrass Credit Management",
                "debt_type": "credit_card",
                "amount_owed": Decimal("6700.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Lakeline Electric",
                "debt_type": "utility",
                "amount_owed": Decimal("800.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Southmoor Health",
                "debt_type": "medical",
                "amount_owed": Decimal("4200.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
        ],
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
            "vehicle_payment": Decimal("0.00"),
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
                "creditor_name": "Keelson Loan Servicing",
                "debt_type": "student_loan",
                "amount_owed": Decimal("28000.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Lakemont University Hospital",
                "debt_type": "medical",
                "amount_owed": Decimal("3400.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
        ],
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
            # The Corolla lease, his only car
            "vehicle_payment": Decimal("389.00"),
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
            _car(4300, 8600, "Honda", "Fit", "2017", "96000", who="with_someone", owed="7800.00"),
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
                "creditor_name": "Bright Signal Wireless",
                "debt_type": "utility",
                "amount_owed": Decimal("640.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Calumet Ridge Medical Center",
                "debt_type": "medical",
                "amount_owed": Decimal("3850.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Driveline Tire & Auto",
                "debt_type": "credit_card",
                "amount_owed": Decimal("1180.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "business",
            },
            {
                "creditor_name": "Illinois State Toll Highway Authority",
                "debt_type": "other",
                "amount_owed": Decimal("380.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Tallowfield Lending Co.",
                "debt_type": "personal_loan",
                "amount_owed": Decimal("4100.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Northgate Card Services",
                "debt_type": "credit_card",
                "amount_owed": Decimal("6420.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Prairie Line Credit Union",
                "debt_type": "credit_card",
                "amount_owed": Decimal("1760.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Hollowmere Residential LLC",
                "debt_type": "other",
                "amount_owed": Decimal("1850.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Sablewood Bank",
                "debt_type": "credit_card",
                "amount_owed": Decimal("2980.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
        ],
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
            DebtInfo.objects.create(session=session, **debt)

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
