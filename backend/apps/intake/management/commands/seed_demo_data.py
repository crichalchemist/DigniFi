"""Seed 5 synthetic personas for partner demos and E2E testing.

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
from apps.eligibility.models import MEDIAN_TABLE
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.forms.registry import build_field_values, packet
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    ExpenseInfo,
    FeeWaiverApplication,
    IncomeInfo,
    IntakeSession,
    SOFACreditorPayment,
    SOFAPriorIncome,
    SOFAReport,
)

User = get_user_model()

DEMO_PASSWORD = "DigniFi-Demo-2026!"


def _wages_only(wages: Decimal) -> dict:
    """The Income step's ten amounts for a persona whose only income is wages: the rest $0."""
    amounts = dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00"))
    amounts["monthly_gross_wages"] = wages
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
            "household_size": 3,
            "filing_type": "individual",
        },
        "income": {
            "marital_status": "single",
            "number_of_dependents": 2,
            **_wages_only(Decimal("3200.00")),
        },
        "expenses": {
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
            "household_size": 1,
            "filing_type": "individual",
        },
        "income": {
            "marital_status": "single",
            "number_of_dependents": 0,
            **_wages_only(Decimal("5833.00")),
        },
        "expenses": {
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
            "household_size": 4,
            "filing_type": "individual",
        },
        "income": {
            "marital_status": "married_joint",
            "number_of_dependents": 2,
            # $12,000/month = $144,000/year — above the $137,902 HH4 median,
            # so the annualized § 707(b) comparison fails as intended.
            **_wages_only(Decimal("12000.00")),
        },
        "expenses": {
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
            "household_size": 2,
            "filing_type": "individual",
        },
        "income": {
            "marital_status": "married_joint",
            "number_of_dependents": 0,
            **_wages_only(Decimal("3500.00")),
        },
        "expenses": {
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
            "household_size": 1,
            "filing_type": "individual",
        },
        "income": {
            "marital_status": "single",
            "number_of_dependents": 0,
            **_wages_only(Decimal("2000.00")),
        },
        "expenses": {
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


PERSONAS: dict[str, Callable[[], dict]] = {
    "maria": _maria_torres,
    "james": _james_washington,
    "priya": _priya_sharma,
    "deshawn": _deshawn_mitchell,
    "sarah": _sarah_chen,
}


# ── Management command ──────────────────────────────────────────────


class Command(BaseCommand):
    help = "Seed 5 synthetic demo personas for partner demos and E2E testing."

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
            help="Seed a single persona instead of all 5",
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
            current_step=6,
        )

        DebtorInfo.objects.create(session=session, **data["debtor"])
        IncomeInfo.objects.create(session=session, **data["income"])
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

        # Create FeeWaiverApplication for fee-waiver-eligible personas
        # (required by Form 103B generator)
        if result["qualifies_for_fee_waiver"]:
            FeeWaiverApplication.objects.create(
                session=session,
                household_size=data["debtor"]["household_size"],
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
