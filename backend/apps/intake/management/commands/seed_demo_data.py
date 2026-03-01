"""Seed 5 synthetic personas for partner demos and E2E testing.

Each persona exercises a distinct eligibility path through the ILND
means test calculator and form generation pipeline.  SSNs use the
IRS-reserved 900-xx range so they can never collide with real data.
"""

from decimal import Decimal
from datetime import date
from typing import Callable

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.districts.models import District
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.forms.registry import get_all_form_types, get_generator
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    ExpenseInfo,
    IncomeInfo,
    IntakeSession,
)

User = get_user_model()

DEMO_PASSWORD = "DigniFi-Demo-2026!"


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
            "marital_status": "single",
            "number_of_dependents": 2,
            "monthly_income": [3200, 3200, 3200, 3200, 3200, 3200],
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
                "creditor_name": "Capital One",
                "debt_type": "credit_card",
                "amount_owed": Decimal("4200.00"),
                "monthly_payment": Decimal("85.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Northwestern Memorial Hospital",
                "debt_type": "medical",
                "amount_owed": Decimal("12800.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Discover Financial",
                "debt_type": "personal_loan",
                "amount_owed": Decimal("3500.00"),
                "monthly_payment": Decimal("120.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
        ],
    }


def _james_washington() -> dict:
    """Borderline case — just below single-filer median ($71,304)."""
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
            "marital_status": "single",
            "number_of_dependents": 0,
            "monthly_income": [5833, 5833, 5833, 5833, 5833, 5833],
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
                "creditor_name": "Citibank",
                "debt_type": "credit_card",
                "amount_owed": Decimal("9800.00"),
                "monthly_payment": Decimal("200.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Toyota Financial Services",
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
            "marital_status": "married_joint",
            "number_of_dependents": 2,
            "monthly_income": [10000, 10000, 10000, 10000, 10000, 10000],
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
                "creditor_name": "American Express",
                "debt_type": "credit_card",
                "amount_owed": Decimal("22000.00"),
                "monthly_payment": Decimal("500.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Rush University Medical Center",
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
            "marital_status": "married_joint",
            "number_of_dependents": 0,
            "monthly_income": [3500, 3500, 3500, 3500, 3500, 3500],
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
                "creditor_name": "Wells Fargo Home Mortgage",
                "debt_type": "mortgage",
                "amount_owed": Decimal("160000.00"),
                "monthly_payment": Decimal("1200.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
                "is_secured": True,
                "collateral_description": "Single-family home, 7823 S Sangamon St",
            },
            {
                "creditor_name": "Midland Credit Management",
                "debt_type": "credit_card",
                "amount_owed": Decimal("6700.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "ComEd",
                "debt_type": "utility",
                "amount_owed": Decimal("800.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "Advocate Health",
                "debt_type": "medical",
                "amount_owed": Decimal("4200.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
        ],
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
            "marital_status": "single",
            "number_of_dependents": 0,
            "monthly_income": [2000, 2000, 2000, 2000, 2000, 2000],
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
                "creditor_name": "Navient",
                "debt_type": "student_loan",
                "amount_owed": Decimal("28000.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": False,
                "consumer_business_classification": "consumer",
            },
            {
                "creditor_name": "University of Illinois Hospital",
                "debt_type": "medical",
                "amount_owed": Decimal("3400.00"),
                "monthly_payment": Decimal("0.00"),
                "is_in_collections": True,
                "consumer_business_classification": "consumer",
            },
        ],
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
                    "ILND district not found. "
                    "Run: python manage.py loaddata ilnd_2025_data"
                )
            )
            return

        targets = (
            {options["persona"]: PERSONAS[options["persona"]]}
            if options["persona"]
            else PERSONAS
        )

        if options["reset"]:
            usernames = [fn()["username"] for fn in targets.values()]
            deleted, _ = User.objects.filter(username__in=usernames).delete()
            self.stdout.write(
                self.style.WARNING(f"Deleted {deleted} objects (cascade)")
            )

        for name, persona_fn in targets.items():
            data = persona_fn()
            if User.objects.filter(username=data["username"]).exists():
                self.stdout.write(
                    self.style.NOTICE(
                        f"  {data['username']} already exists "
                        f"(use --reset to recreate)"
                    )
                )
                continue

            self._create_persona(data, district)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Created {data['username']} "
                    f"(password: {DEMO_PASSWORD})"
                )
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

        # Run means test calculation
        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        # Generate forms for eligible personas
        if result["passes_means_test"]:
            for form_type in get_all_form_types():
                try:
                    generator = get_generator(form_type, session)
                    generator.generate()
                except (KeyError, ValueError) as exc:
                    self.stderr.write(
                        self.style.WARNING(
                            f"    Skipped {form_type}: {exc}"
                        )
                    )
