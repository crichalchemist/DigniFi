"""
Means Test Calculator Service.

Implements Chapter 7 bankruptcy means test calculation (11 U.S.C. § 707(b))
following service layer pattern for separation of business logic.
"""

from decimal import Decimal
from typing import Dict, Any
from django.db import transaction

from apps.intake.models import IntakeSession
from apps.eligibility.models import MeansTest


class MeansTestCalculator:
    """
    Service class for calculating Chapter 7 bankruptcy means test.

    This service encapsulates the business logic for means test calculations,
    including UPL-compliant result messaging and audit logging.
    """

    def __init__(self, intake_session: IntakeSession):
        """
        Initialize calculator with intake session.

        Args:
            intake_session: IntakeSession containing debtor information

        Raises:
            ValueError: If intake_session is invalid or incomplete
        """
        if not intake_session:
            raise ValueError("IntakeSession is required")

        if not hasattr(intake_session, 'income_info'):
            raise ValueError(
                "IntakeSession must have income_info before calculating means test"
            )

        self.intake_session = intake_session
        self.district = intake_session.district

    @transaction.atomic
    def calculate(self) -> Dict[str, Any]:
        """
        Calculate or recalculate means test for the intake session.

        Creates or updates MeansTest record and returns UPL-compliant results.

        Returns:
            dict: Calculation results with structure:
                {
                    "passes_means_test": bool,
                    "qualifies_for_fee_waiver": bool,
                    "cmi": Decimal,
                    "median_income_threshold": Decimal,
                    "family_size": int,
                    "message": str (UPL-compliant),
                    "details": dict
                }

        Raises:
            ValueError: If required data is missing or invalid
        """
        # Get or create MeansTest record
        means_test, created = MeansTest.objects.get_or_create(
            session=self.intake_session,
            defaults={
                "district": self.district,
                "median_income_threshold": Decimal("0"),
                "calculated_cmi": Decimal("0"),
                "passes_means_test": False,
            }
        )

        # If not newly created, ensure district is current
        if not created:
            means_test.district = self.district

        # Perform calculation
        try:
            passes_test = means_test.calculate()
        except ValueError as e:
            raise ValueError(f"Means test calculation failed: {str(e)}")

        # Save updated means test
        means_test.save()

        # Build UPL-compliant response
        result = {
            "passes_means_test": means_test.passes_means_test,
            "qualifies_for_fee_waiver": means_test.qualifies_for_fee_waiver,
            "cmi": means_test.calculated_cmi,
            "median_income_threshold": means_test.median_income_threshold,
            "family_size": means_test.get_calculation_details().get("family_size", 0),
            "message": self._generate_upl_compliant_message(means_test),
            "details": means_test.get_calculation_details(),
            "means_test_id": means_test.id,
        }

        return result

    def _generate_upl_compliant_message(self, means_test: MeansTest) -> str:
        """
        Generate UPL-compliant message about means test results.

        CRITICAL: This must provide legal INFORMATION, never legal ADVICE.

        Prohibited phrases:
        - "you should file"
        - "I recommend"
        - "you should choose"

        Permitted phrases:
        - "you may be eligible"
        - "Chapter 7 typically requires"
        - "many filers in this situation"

        Args:
            means_test: Calculated MeansTest instance

        Returns:
            str: UPL-compliant informational message
        """
        if means_test.passes_means_test:
            message = (
                "Based on the information provided, your income is below the median "
                f"income for a household of this size in {self.district.state}. "
                "This means you may be eligible to file Chapter 7 bankruptcy. "
                "Chapter 7 typically allows debtors with income below the median to "
                "discharge unsecured debts without a repayment plan."
            )

            if means_test.qualifies_for_fee_waiver:
                message += (
                    " Additionally, you may qualify for a filing fee waiver under "
                    "28 U.S.C. § 1930(f), which waives the standard filing fee for "
                    "filers with very low income."
                )
        else:
            message = (
                "Based on the information provided, your income is above the median "
                f"income for a household of this size in {self.district.state}. "
                "This means additional calculations may be needed to determine "
                "Chapter 7 eligibility. Many filers with above-median income still "
                "qualify for Chapter 7 if their allowable expenses are high enough. "
                "You may also be eligible for Chapter 13 bankruptcy, which involves "
                "a repayment plan."
            )

        return message

    def get_detailed_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed calculation breakdown for transparency.

        Returns:
            dict: Detailed breakdown including:
                - Monthly income by source
                - Family size calculation
                - Median income threshold
                - Pass/fail determination
                - Fee waiver eligibility
        """
        try:
            means_test = self.intake_session.means_test
        except MeansTest.DoesNotExist:
            raise ValueError(
                "Means test has not been calculated yet. Call calculate() first."
            )

        income_info = self.intake_session.income_info
        details = means_test.get_calculation_details()

        return {
            "income_history": {
                "monthly_values": details.get("monthly_income_breakdown", []),
                "average_cmi": float(means_test.calculated_cmi),
            },
            "family_composition": {
                "marital_status": income_info.marital_status,
                "number_of_dependents": income_info.number_of_dependents,
                "total_family_size": details.get("family_size", 0),
            },
            "means_test_threshold": {
                "median_income": float(means_test.median_income_threshold),
                "district": self.district.code.upper(),
                "effective_date": details.get("calculated_at"),
            },
            "results": {
                "passes_means_test": means_test.passes_means_test,
                "qualifies_for_fee_waiver": means_test.qualifies_for_fee_waiver,
                "statute_citation": "11 U.S.C. § 707(b)",
            },
        }
