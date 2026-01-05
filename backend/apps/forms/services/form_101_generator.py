"""
Form 101 Generator Service.

Generates Official Bankruptcy Form 101 (Voluntary Petition for Individuals
Filing for Bankruptcy) from intake session data.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.db import transaction

from apps.intake.models import IntakeSession
from apps.forms.models import GeneratedForm


class Form101Generator:
    """
    Service class for generating Form 101 - Voluntary Petition.

    Form 101 is the foundational document for all bankruptcy filings, containing
    debtor information, case type, and basic statistical data.

    Official form reference: https://www.uscourts.gov/forms/bankruptcy-forms
    """

    FORM_TYPE = "form_101"

    def __init__(self, intake_session: IntakeSession):
        """
        Initialize generator with intake session.

        Args:
            intake_session: IntakeSession with complete debtor information

        Raises:
            ValueError: If intake_session is invalid or incomplete
        """
        if not intake_session:
            raise ValueError("IntakeSession is required")

        # Validate required data exists
        if not hasattr(intake_session, "debtor_info"):
            raise ValueError("IntakeSession must have debtor_info")

        self.intake_session = intake_session
        self.debtor_info = intake_session.debtor_info
        self.district = intake_session.district

    @transaction.atomic
    def generate(self, user=None) -> Dict[str, Any]:
        """
        Generate Form 101 data structure ready for PDF population.

        For MVP: Returns structured form data as JSON.
        Future: Will populate actual PDF template and return file path.

        Args:
            user: User generating the form (for audit trail)

        Returns:
            dict: Form data structure with all populated fields
        """
        # Build form data structure matching Official Form 101 fields
        form_data = self._build_form_data()

        # Create or update GeneratedForm record
        generated_form, created = GeneratedForm.objects.update_or_create(
            session=self.intake_session,
            form_type=self.FORM_TYPE,
            defaults={
                "form_data": form_data,
                "status": "generated",
                "generated_by": user,
            },
        )

        return {
            "form_id": generated_form.id,
            "form_type": "form_101",
            "form_name": "Voluntary Petition for Individuals Filing for Bankruptcy",
            "status": generated_form.status,
            "data": form_data,
            "generated_at": generated_form.generated_at.isoformat(),
        }

    def _build_form_data(self) -> Dict[str, Any]:
        """
        Build complete Form 101 data structure.

        Maps intake session data to Official Form 101 fields.

        Returns:
            dict: Complete form data ready for PDF population
        """
        # Part 1: Debtor Information
        debtor_name = {
            "first_name": self.debtor_info.first_name,
            "middle_name": self.debtor_info.middle_name,
            "last_name": self.debtor_info.last_name,
            "full_name": f"{self.debtor_info.first_name} {self.debtor_info.middle_name} {self.debtor_info.last_name}".replace(
                "  ", " "
            ),
        }

        debtor_address = {
            "street": self.debtor_info.street_address,
            "city": self.debtor_info.city,
            "state": self.debtor_info.state,
            "zip": self.debtor_info.zip_code,
        }

        # Part 2: Case Type (Chapter 7 for MVP)
        case_type = {
            "chapter": "7",
            "chapter_name": "Chapter 7 - Liquidation",
        }

        # Part 3: District and Filing Location
        filing_info = {
            "district_code": self.district.code.upper(),
            "district_name": self.district.name,
            "court_name": self.district.court_name,
        }

        # Part 4: Type of Debtor
        debtor_type = {
            "individual": True,
            "business": False,
            "corporation": False,
        }

        # Part 5: Statistical/Administrative Information
        try:
            income_info = self.intake_session.income_info
            family_size = income_info.number_of_dependents + 1
            if income_info.marital_status in ["married_joint", "married_separate"]:
                family_size += 1
        except AttributeError:
            family_size = 1

        statistical_info = {
            "family_size": family_size,
            "estimated_assets_range": self._estimate_asset_range(),
            "estimated_liabilities_range": self._estimate_liability_range(),
        }

        # Part 6: Means Test Declaration
        means_test_info = self._get_means_test_declaration()

        # Assemble complete form
        form_data = {
            "form_101_version": "12/20",  # Current form version
            "debtor_name": debtor_name,
            "debtor_address": debtor_address,
            "case_type": case_type,
            "filing_info": filing_info,
            "debtor_type": debtor_type,
            "statistical_info": statistical_info,
            "means_test": means_test_info,
            "filing_fee_amount": str(self.district.filing_fee_chapter_7),
            "signature_date": None,  # To be signed by user
            "generated_for_preview": True,  # MVP: preview only
        }

        return form_data

    def _estimate_asset_range(self) -> str:
        """
        Estimate total asset range for statistical reporting.

        Returns:
            str: Asset range code (e.g., "$1-$50k", "$50k-$100k")
        """
        # For MVP: Return placeholder
        # Future: Calculate from AssetInfo records
        try:
            assets = self.intake_session.assets.all()
            if not assets.exists():
                return "$0-$50,000"

            # This would decrypt and sum encrypted values
            # For MVP, return placeholder range
            return "$50,000-$100,000"
        except Exception:
            return "$0-$50,000"

    def _estimate_liability_range(self) -> str:
        """
        Estimate total liability range for statistical reporting.

        Returns:
            str: Liability range code
        """
        # For MVP: Return placeholder
        # Future: Calculate from DebtInfo records
        try:
            debts = self.intake_session.debts.all()
            if not debts.exists():
                return "$0-$50,000"

            return "$50,000-$100,000"
        except Exception:
            return "$0-$50,000"

    def _get_means_test_declaration(self) -> Dict[str, Any]:
        """
        Get means test result for Form 101 declaration.

        Returns:
            dict: Means test declaration data
        """
        try:
            means_test = self.intake_session.means_test
            return {
                "calculated": True,
                "passes_test": means_test.passes_means_test,
                "cmi": str(means_test.calculated_cmi),
                "median_threshold": str(means_test.median_income_threshold),
                "declaration": (
                    "Debtor's income is below the median income for applicable family size"
                    if means_test.passes_means_test
                    else "Debtor's income is above the median income (additional means test calculations may be required)"
                ),
            }
        except Exception:
            return {
                "calculated": False,
                "declaration": "Means test calculation pending",
            }

    def preview(self) -> Dict[str, Any]:
        """
        Generate preview of form data without creating GeneratedForm record.

        Useful for showing user what will be filed before final generation.

        Returns:
            dict: Form data preview
        """
        form_data = self._build_form_data()

        return {
            "form_type": "form_101",
            "form_name": "Voluntary Petition for Individuals Filing for Bankruptcy",
            "preview": True,
            "data": form_data,
            "upl_disclaimer": (
                "This is a preview of your petition based on the information provided. "
                "This software provides legal information, not legal advice. "
                "You are responsible for reviewing all information for accuracy before filing."
            ),
        }
