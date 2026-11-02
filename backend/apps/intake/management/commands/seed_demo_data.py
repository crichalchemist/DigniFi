"""Seed 6 synthetic personas for partner demos and E2E testing.

Each persona exercises a distinct eligibility path through the ILND
means test calculator and form generation pipeline.  SSNs use the
IRS-reserved 900-xx range so they can never collide with real data.
"""

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
from apps.intake.household import count_fee_waiver_household
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    ExpenseInfo,
    FeeWaiverApplication,
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


# ── Persona data functions ──────────────────────────────────────────


def _maria_torres() -> dict:
    """Below-median single parent, fee waiver eligible. PRD primary persona."""
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
        },
        "assets": [
            {
                "asset_type": "vehicle",
                "description": "2015 Honda Civic",
                "current_value": Decimal("6500.00"),
                "amount_owed": Decimal("0.00"),
            },
            {
                "asset_type": "bank_account",
                "description": "Chase checking account",
                "current_value": Decimal("340.00"),
                "amount_owed": Decimal("0.00"),
                "financial_institution": "JPMorgan Chase",
            },
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
        # The fee-waiver page's answers (Form 103B lines 2 and 3)
        "fee_waiver": {
            "monthly_take_home_pay": Decimal("2800.00"),
            "receives_noncash_assistance": True,
            "benefit_types": ["SNAP (food stamps)"],
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
        },
        "assets": [
            {
                "asset_type": "vehicle",
                "description": "2019 Toyota Camry",
                "current_value": Decimal("14000.00"),
                "amount_owed": Decimal("8500.00"),
            },
            {
                "asset_type": "bank_account",
                "description": "Bank of America checking",
                "current_value": Decimal("1200.00"),
                "amount_owed": Decimal("0.00"),
                "financial_institution": "Bank of America",
            },
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
        },
        "assets": [
            {
                "asset_type": "bank_account",
                "description": "Joint savings account",
                "current_value": Decimal("8500.00"),
                "amount_owed": Decimal("0.00"),
                "financial_institution": "Chase",
            },
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
        },
        "assets": [
            {
                "asset_type": "real_property",
                "description": "Single-family home, 7823 S Sangamon",
                "current_value": Decimal("180000.00"),
                "amount_owed": Decimal("160000.00"),
            },
            {
                "asset_type": "vehicle",
                "description": "2012 Ford F-150",
                "current_value": Decimal("8000.00"),
                "amount_owed": Decimal("0.00"),
            },
            {
                "asset_type": "retirement_account",
                "description": "401(k) through employer",
                "current_value": Decimal("12000.00"),
                "amount_owed": Decimal("0.00"),
                "financial_institution": "Fidelity",
            },
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
        # The fee-waiver page's answers (Form 103B lines 2 and 3)
        "fee_waiver": {
            "monthly_take_home_pay": Decimal("3050.00"),
            "receives_noncash_assistance": False,
            "benefit_types": [],
        },
    }


def _sarah_chen() -> dict:
    """Simplest case — single, no assets, fee waiver eligible."""
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
            "other_expenses": Decimal("50.00"),
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
        # The fee-waiver page's answers (Form 103B lines 2 and 3)
        "fee_waiver": {
            "monthly_take_home_pay": Decimal("1750.00"),
            "receives_noncash_assistance": False,
            "benefit_types": [],
        },
    }


def _andres_kettleby() -> dict:
    """Gig driver, below median. Qualifies for a fee waiver but pays in installments."""
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
            # His net driving income ($4,200 from the apps less $830 of driving costs) is
            # other income until the Income step asks for business income (3a1.Q1).
            **dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00")),
            "monthly_other_income": Decimal("3370.00"),
            **_no_business_and_no_assistance(),
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
        },
        "assets": [
            {
                "asset_type": "vehicle",
                "description": "2017 Honda Fit",
                # His half of a car titled to him and his brother
                "current_value": Decimal("4300.00"),
                "amount_owed": Decimal("7800.00"),
            },
            {
                "asset_type": "personal_property",
                "description": "Household goods, electronics and clothing",
                "current_value": Decimal("1900.00"),
                "amount_owed": Decimal("0.00"),
            },
            {
                "asset_type": "bank_account",
                "description": "Harborline Bank checking",
                "current_value": Decimal("412.00"),
                "amount_owed": Decimal("0.00"),
                "financial_institution": "Harborline Bank",
            },
            {
                "asset_type": "bank_account",
                "description": "Prairie Line Credit Union share savings",
                "current_value": Decimal("85.00"),
                "amount_owed": Decimal("0.00"),
                "financial_institution": "Prairie Line Credit Union",
            },
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
        # No "fee_waiver": he means to pay the fee in installments (3a1.Q2).
    }


PERSONAS: dict[str, Callable[[], dict]] = {
    "maria": _maria_torres,
    "james": _james_washington,
    "priya": _priya_sharma,
    "deshawn": _deshawn_mitchell,
    "sarah": _sarah_chen,
    "andres": _andres_kettleby,
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
            AssetInfo.objects.create(session=session, **asset)

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

        # Run means test calculation
        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        # Create FeeWaiverApplication for fee-waiver-eligible personas who apply
        # (required by Form 103B generator); one with no "fee_waiver" answers doesn't
        if result["qualifies_for_fee_waiver"] and "fee_waiver" in data:
            FeeWaiverApplication.objects.create(
                session=session,
                household_size=count_fee_waiver_household(
                    household.get_members(), data["income"]["marital_status"]
                ),
                **data["fee_waiver"],
                cannot_pay_full=True,
                cannot_pay_installments=True,
                status="pending",
            )

        # Check that every form in an eligible persona's packet resolves (none are stored)
        if result["passes_means_test"]:
            for form_type in packet(session):
                try:
                    build_field_values(form_type, session)
                except Exception as exc:
                    self.stderr.write(self.style.WARNING(f"    Skipped {form_type}: {exc}"))
