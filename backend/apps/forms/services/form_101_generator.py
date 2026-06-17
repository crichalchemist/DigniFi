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

    def generate(self) -> dict[str, Any]:
        """
        Generate Form 101 data structure ready for PDF population.

        Returns pure data dict — DB persistence is handled by the view layer.
        """
        return self.pdf_field_map()

    def pdf_field_map(self) -> dict:
        """Delegate to the schema-driven resolver."""
        from apps.forms.schema import load_schema
        from apps.forms.services.fill_resolver import resolve

        schema = load_schema("form_101")
        return resolve(schema, self.intake_session)

    def preview(self) -> dict[str, Any]:
        """Generate preview data for user review before PDF creation."""
        return self.generate()
