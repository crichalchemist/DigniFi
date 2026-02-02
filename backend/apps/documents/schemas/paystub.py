"""Pay stub extraction schema for income verification."""

from decimal import Decimal
from datetime import date
from typing import Optional
from pydantic import Field, field_validator

from .base import BaseExtractionSchema


class PayStubExtraction(BaseExtractionSchema):
    """
    Schema for pay stub OCR extraction.

    Used for Schedule I (Income) and means test calculations.
    """

    employer_name: str = Field(
        min_length=1,
        description="Employer or company name"
    )
    gross_pay: Decimal = Field(
        gt=0,
        description="Gross pay for this period"
    )
    pay_period_start: date = Field(
        description="Pay period start date (YYYY-MM-DD)"
    )
    pay_period_end: date = Field(
        description="Pay period end date (YYYY-MM-DD)"
    )
    ytd_gross: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Year-to-date gross earnings"
    )
    net_pay: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Net pay (take-home)"
    )
    deductions_total: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Total deductions for this period"
    )

    @field_validator('pay_period_end')
    @classmethod
    def end_after_start(cls, v, info):
        """Validate pay period end is after start."""
        if 'pay_period_start' in info.data and v < info.data['pay_period_start']:
            raise ValueError('Pay period end must be after start date')
        return v

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "employer_name": "Acme Corporation",
                "gross_pay": "3240.00",
                "pay_period_start": "2026-01-01",
                "pay_period_end": "2026-01-15",
                "ytd_gross": "3240.00",
                "net_pay": "2450.00",
                "deductions_total": "790.00",
                "confidence_score": 92
            }
        }
