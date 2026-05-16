"""Creditor bill extraction schema for debt documentation."""

from datetime import date
from decimal import Decimal

from pydantic import Field

from .base import BaseExtractionSchema

CREDITOR_TYPE_TO_DEBT_TYPE = {
    "credit_card": "credit_card",
    "medical": "medical",
    "personal_loan": "personal_loan",
    "student_loan": "student_loan",
    "auto_loan": "auto_loan",
    "mortgage": "mortgage",
    "utility": "utility",
    "other": "other",
}


class CreditorBillExtraction(BaseExtractionSchema):
    """
    Schema for creditor bill/statement OCR extraction.

    Used for Schedule D (Creditors Holding Unsecured Debts) and
    Schedule E (Creditors Holding Secured Debts) in bankruptcy forms.
    """

    creditor_name: str = Field(
        min_length=1,
        description="Name of the creditor or collection agency",
    )
    account_number: str | None = Field(
        default=None,
        description="Account or reference number (last 4 digits acceptable)",
    )
    amount_owed: Decimal = Field(
        gt=0,
        description="Current balance or total amount owed",
    )
    minimum_payment: Decimal | None = Field(
        default=None,
        ge=0,
        description="Minimum payment due (if shown)",
    )
    due_date: date | None = Field(
        default=None,
        description="Payment due date (YYYY-MM-DD)",
    )
    creditor_type: str = Field(
        description=(
            "Creditor category. One of: credit_card, medical, personal_loan, "
            "student_loan, auto_loan, mortgage, utility, other"
        ),
    )

    def to_debt_type(self) -> str:
        """Map creditor_type to internal debt classification."""
        return CREDITOR_TYPE_TO_DEBT_TYPE.get(self.creditor_type, "other")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "creditor_name": "Capital One",
                "account_number": "4111",
                "amount_owed": "2450.00",
                "minimum_payment": "35.00",
                "due_date": "2026-06-15",
                "creditor_type": "credit_card",
                "confidence_score": 88,
            }
        }
