"""
Form 101 Generator Service.

Generates Official Bankruptcy Form 101 (Voluntary Petition for Individuals
Filing for Bankruptcy) from intake session data.
"""

from typing import Any

from apps.intake.models import IntakeSession


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

    def generate(self) -> dict[str, Any]:
        """
        Generate Form 101 data structure ready for PDF population.

        Returns pure data dict — DB persistence is handled by the view layer.
        """
        return self._build_form_data()

    def pdf_field_map(self) -> dict:
        """Map session data to Official Form 101 (form_b_101_0624_fillable_clean.pdf)."""
        di = self.debtor_info
        full_name = f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()
        return {
            "Debtor1.First name": di.first_name,
            "Debtor1.Middle name": di.middle_name or "",
            "Debtor1.Last name": di.last_name,
            "Debtor1.Name": full_name,
            "Debtor1.First name_3": di.first_name,
            "Debtor1.Middle name_3": di.middle_name or "",
            "Debtor1.Last name_3": di.last_name,
            "Debtor1.First name_5": di.first_name,
            "Debtor1.Middle name_5": di.middle_name or "",
            "Debtor1.Last name_5": di.last_name,
            "Debtor1.SSNum": di.ssn,
            "Debtor1.Street address": di.street_address,
            "Debtor1.City": di.city,
            "Debtor1.State": di.state,
            "Debtor1.Zip": di.zip_code,
            "Debtor1.County": "",
            "Debtor1.Cell phone": di.phone or "",
            "Debtor1.Email address_2": di.email or "",
            "Bankruptcy District Information": self.district.name,
            "Case number": "",
            "Case number1": "",
            "Check Box1": "/Yes",  # Individual debtor
            "Check Box5": "/Yes",  # Chapter 7
            "Check Box16": "/Yes",  # Consumer debts
        }

    def _build_form_data(self) -> dict[str, Any]:
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

    def _get_means_test_declaration(self) -> dict[str, Any]:
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

    def preview(self) -> dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()
