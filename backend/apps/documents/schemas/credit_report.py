"""Credit report extraction schema — one tradeline per account."""

from decimal import Decimal

from pydantic import BaseModel, Field

from .base import BaseExtractionSchema


class TradelineItem(BaseModel):
    """A single account line from a credit report."""

    creditor_name: str
    account_number: str | None = None
    amount_owed: Decimal = Field(ge=0)
    account_type: (
        str  # credit_card | auto_loan | student_loan | mortgage | medical | personal_loan | other
    )
    account_status: str  # open | closed | charged_off | in_collections | delinquent
    credit_limit: Decimal | None = None


class CreditReportExtraction(BaseExtractionSchema):
    """Extraction schema for credit reports — a list of tradelines."""

    confidence_score: int = Field(default=0, ge=0, le=100)
    tradelines: list[TradelineItem]
