"""Credit report extraction schema — one tradeline per account."""

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .base import BaseExtractionSchema


class TradelineItem(BaseModel):
    """A single account line from a credit report."""

    # Models return account numbers as JSON numbers and pad names with spaces.
    model_config = ConfigDict(coerce_numbers_to_str=True, str_strip_whitespace=True)

    creditor_name: str = Field(min_length=1)
    account_number: str | None = None
    # DebtInfo.amount_owed is DecimalField(12, 2) on read; a wider value 500s the session.
    amount_owed: Decimal = Field(ge=0, le=Decimal("9999999999.99"))
    # credit_card | auto_loan | student_loan | mortgage | medical | personal_loan | other
    account_type: str | None = None
    # open | closed | charged_off | in_collections | delinquent
    account_status: str | None = None
    credit_limit: Decimal | None = None

    @field_validator("credit_limit", mode="before")
    @classmethod
    def unreadable_limit_is_none(cls, value):
        """Nothing reads the limit, so a limit that is not a number ("N/A") keeps the account."""
        try:
            limit = Decimal(str(value))
        except InvalidOperation:
            return None
        return limit if limit.is_finite() else None


class CreditReportExtraction(BaseExtractionSchema):
    """Extraction schema for credit reports — a list of tradelines."""

    confidence_score: int = Field(default=0, ge=0, le=100)
    tradelines: list[TradelineItem] = Field(default_factory=list)

    @field_validator("tradelines", mode="before")
    @classmethod
    def keep_readable_tradelines(cls, value):
        """Validate each account on its own, so one unreadable line keeps the rest."""
        if not isinstance(value, list):
            return []
        readable = []
        for line in value:
            try:
                readable.append(TradelineItem.model_validate(line))
            except ValidationError:
                continue
        return readable
