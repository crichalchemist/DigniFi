"""Business financial statement extraction schemas for Chapter 11."""

from decimal import Decimal
from datetime import date
from typing import Optional
from pydantic import Field, field_validator

from .base import BaseExtractionSchema


class BalanceSheetExtraction(BaseExtractionSchema):
    """
    Schema for balance sheet OCR extraction.

    Required for Chapter 11 Subchapter V filings.
    Validates accounting equation: Assets = Liabilities + Equity
    """

    as_of_date: date = Field(
        description="Balance sheet date (YYYY-MM-DD)"
    )

    # Assets
    cash: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Cash and cash equivalents"
    )
    accounts_receivable: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Accounts receivable"
    )
    inventory: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Inventory value"
    )
    equipment: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Equipment and fixed assets"
    )
    total_assets: Decimal = Field(
        gt=0,
        decimal_places=2,
        description="Total assets"
    )

    # Liabilities
    accounts_payable: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Accounts payable"
    )
    loans_payable: Optional[Decimal] = Field(
        default=None,
        ge=0,
        decimal_places=2,
        description="Loans and notes payable"
    )
    total_liabilities: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Total liabilities"
    )

    # Equity
    owners_equity: Decimal = Field(
        decimal_places=2,
        description="Owner's equity (can be negative)"
    )

    @field_validator('owners_equity')
    @classmethod
    def validate_accounting_equation(cls, v, info):
        """
        Validate accounting equation: Assets = Liabilities + Equity.

        Allows 1% tolerance for rounding errors.
        """
        if 'total_assets' in info.data and 'total_liabilities' in info.data:
            total_assets = info.data['total_assets']
            total_liabilities = info.data['total_liabilities']

            calculated_equity = total_assets - total_liabilities

            # Allow 1% tolerance
            if abs(calculated_equity - v) / total_assets > Decimal('0.01'):
                raise ValueError(
                    f'Balance sheet equation error: '
                    f'Assets ({total_assets}) ≠ '
                    f'Liabilities ({total_liabilities}) + Equity ({v}). '
                    f'Expected equity: {calculated_equity}'
                )

        return v

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "as_of_date": "2026-01-31",
                "cash": "5000.00",
                "accounts_receivable": "12000.00",
                "inventory": "8000.00",
                "equipment": "25000.00",
                "total_assets": "50000.00",
                "accounts_payable": "8000.00",
                "loans_payable": "30000.00",
                "total_liabilities": "38000.00",
                "owners_equity": "12000.00",
                "confidence_score": 88
            }
        }


class ProfitLossExtraction(BaseExtractionSchema):
    """
    Schema for profit & loss (P&L) statement extraction.

    Required for Chapter 11 Subchapter V filings.
    """

    period_start: date = Field(
        description="P&L period start date"
    )
    period_end: date = Field(
        description="P&L period end date"
    )
    total_revenue: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Total revenue for period"
    )
    total_expenses: Decimal = Field(
        ge=0,
        decimal_places=2,
        description="Total expenses for period"
    )
    net_income: Decimal = Field(
        decimal_places=2,
        description="Net income (can be negative for loss)"
    )

    @field_validator('net_income')
    @classmethod
    def validate_net_income_calculation(cls, v, info):
        """Validate net income = revenue - expenses."""
        if 'total_revenue' in info.data and 'total_expenses' in info.data:
            calculated = info.data['total_revenue'] - info.data['total_expenses']

            # Allow 1% tolerance
            if abs(calculated - v) > abs(v) * Decimal('0.01'):
                raise ValueError(
                    f'Net income calculation error: '
                    f'{v} ≠ {calculated} (revenue - expenses)'
                )

        return v

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
                "total_revenue": "150000.00",
                "total_expenses": "125000.00",
                "net_income": "25000.00",
                "confidence_score": 90
            }
        }
