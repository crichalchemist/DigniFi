"""
Means Test Calculator Service.

Implements Chapter 7 bankruptcy means test calculation (11 U.S.C. § 707(b))
following service layer pattern for separation of business logic.
"""

from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.districts.dated_tables import NoTableInForce
from apps.eligibility.cmi import IncomeNotSplit
from apps.eligibility.models import MeansTest
from apps.intake.models import IntakeSession


class MeansTestCalculator:
    """
    Service class for calculating Chapter 7 bankruptcy means test.

    This service encapsulates the business logic for means test calculations,
    including its seven outcomes.
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

        if not hasattr(intake_session, "income_info"):
            raise ValueError("IntakeSession must have income_info before calculating means test")

        self.intake_session = intake_session
        self.district = intake_session.district

    @transaction.atomic
    def calculate(self) -> dict[str, Any]:
        """
        Calculate or recalculate means test for the intake session.

        Creates or updates MeansTest record and returns its outcome.

        Returns:
            dict: Calculation results with structure:
                {
                    "passes_means_test": bool | None,
                    "cmi": Decimal,
                    "median_income_threshold": Decimal,
                    "family_size": int,
                    "details": dict,
                    "means_test_id": int,
                    "outcome": str,
                    "tables_gap": str | None,
                    "open_on": "debts" | None (the result waits on Amounts Owed, 4d-R27)
                }

        Raises:
            ValueError: If required data is missing or invalid
            MeansTableKeyMissing: If a means-test table lacks a figure the form's lines need
        """
        # Get or create MeansTest record
        means_test, created = MeansTest.objects.get_or_create(
            session=self.intake_session,
            defaults={
                "district": self.district,
                "median_income_threshold": Decimal("0"),
                "calculated_cmi": Decimal("0"),
                "passes_means_test": None,
            },
        )

        # If not newly created, ensure district is current
        if not created:
            means_test.district = self.district

        # Perform calculation. Income not split by source and a missing median table already
        # say what happened in plain words.
        try:
            means_test.calculate()
        except (IncomeNotSplit, NoTableInForce):
            raise
        except ValueError as e:
            raise ValueError(f"Means test calculation failed: {str(e)}") from e

        # Save updated means test
        means_test.save()

        # The result is one of seven outcomes (means_lines.OUTCOMES): the median comparison, Form
        # 122A-2's arithmetic or one of Form 122A-1Supp's three routes. No sentence leaves the
        # server (the browser composes the words).
        details = means_test.get_calculation_details()
        return {
            "passes_means_test": means_test.passes_means_test,
            "cmi": means_test.calculated_cmi,
            "median_income_threshold": means_test.median_income_threshold,
            "family_size": details["family_size"],
            "details": details,
            "means_test_id": means_test.id,
            "outcome": means_test.outcome,
            "tables_gap": details["tables_gap"],
            "open_on": details["open_on"],
        }
