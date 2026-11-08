"""Tests for Pydantic extraction schemas."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from apps.documents.models import DocumentType
from apps.documents.schemas import (
    SCHEMA_MAP,
    BalanceSheetExtraction,
    PayStubExtraction,
    ProfitLossExtraction,
    get_schema_for_type,
)


class TestPayStubExtraction:
    """Tests for PayStubExtraction schema."""

    def test_valid_paystub_data(self):
        """Test schema accepts valid pay stub data."""
        data = {
            "employer_name": "Acme Corp",
            "gross_pay": "3240.00",
            "pay_period_start": "2026-01-01",
            "pay_period_end": "2026-01-15",
            "ytd_gross": "3240.00",
            "net_pay": "2450.00",
            "deductions_total": "790.00",
            "confidence_score": 92,
        }

        result = PayStubExtraction(**data)

        assert result.employer_name == "Acme Corp"
        assert result.gross_pay == Decimal("3240.00")
        assert result.pay_period_start == date(2026, 1, 1)
        assert result.pay_period_end == date(2026, 1, 15)
        assert result.confidence_score == 92

    def test_minimal_paystub_data(self):
        """Test schema works with only required fields."""
        data = {
            "employer_name": "Test Inc",
            "gross_pay": "1500.00",
            "pay_period_start": "2026-01-01",
            "pay_period_end": "2026-01-15",
            "confidence_score": 85,
        }

        result = PayStubExtraction(**data)

        assert result.ytd_gross is None
        assert result.net_pay is None
        assert result.deductions_total is None

    def test_validates_pay_period_order(self):
        """Test end date must be after start date."""
        data = {
            "employer_name": "Test Inc",
            "gross_pay": "1500.00",
            "pay_period_start": "2026-01-15",
            "pay_period_end": "2026-01-01",  # Before start!
            "confidence_score": 85,
        }

        with pytest.raises(ValidationError) as exc_info:
            PayStubExtraction(**data)

        assert "after start date" in str(exc_info.value)

    def test_validates_gross_pay_positive(self):
        """Test gross pay must be positive."""
        data = {
            "employer_name": "Test Inc",
            "gross_pay": "-100.00",  # Negative!
            "pay_period_start": "2026-01-01",
            "pay_period_end": "2026-01-15",
            "confidence_score": 85,
        }

        with pytest.raises(ValidationError) as exc_info:
            PayStubExtraction(**data)

        assert "greater than 0" in str(exc_info.value)

    def test_validates_confidence_range(self):
        """Test confidence score must be 0-100."""
        data = {
            "employer_name": "Test Inc",
            "gross_pay": "1500.00",
            "pay_period_start": "2026-01-01",
            "pay_period_end": "2026-01-15",
            "confidence_score": 150,  # Over 100!
        }

        with pytest.raises(ValidationError) as exc_info:
            PayStubExtraction(**data)

        assert "less than or equal to 100" in str(exc_info.value)


class TestBalanceSheetExtraction:
    """Tests for BalanceSheetExtraction schema."""

    def test_valid_balance_sheet(self):
        """Test schema accepts valid balance sheet data."""
        data = {
            "as_of_date": "2026-01-31",
            "cash": "5000.00",
            "total_assets": "50000.00",
            "total_liabilities": "38000.00",
            "owners_equity": "12000.00",
            "confidence_score": 88,
        }

        result = BalanceSheetExtraction(**data)

        assert result.total_assets == Decimal("50000.00")
        assert result.owners_equity == Decimal("12000.00")

    def test_validates_accounting_equation(self):
        """Test balance sheet equation validation."""
        data = {
            "as_of_date": "2026-01-31",
            "total_assets": "50000.00",
            "total_liabilities": "38000.00",
            "owners_equity": "10000.00",  # Wrong! Should be 12000
            "confidence_score": 88,
        }

        with pytest.raises(ValidationError) as exc_info:
            BalanceSheetExtraction(**data)

        assert "equation error" in str(exc_info.value)


class TestProfitLossExtraction:
    """Tests for ProfitLossExtraction schema."""

    def test_valid_profit_loss(self):
        """Test schema accepts valid P&L data."""
        data = {
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "total_revenue": "150000.00",
            "total_expenses": "125000.00",
            "net_income": "25000.00",
            "confidence_score": 90,
        }

        result = ProfitLossExtraction(**data)

        assert result.net_income == Decimal("25000.00")

    def test_validates_net_income_calculation(self):
        """Test net income = revenue - expenses."""
        data = {
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "total_revenue": "150000.00",
            "total_expenses": "125000.00",
            "net_income": "30000.00",  # Wrong! Should be 25000
            "confidence_score": 90,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProfitLossExtraction(**data)

        assert "calculation error" in str(exc_info.value)


class TestCreditorBillExtraction:
    """Tests for CreditorBillExtraction schema."""

    def test_creditor_bill_schema_valid(self):
        """Test schema accepts valid creditor bill data."""
        from apps.documents.schemas.creditor_bill import CreditorBillExtraction

        bill = CreditorBillExtraction(
            creditor_name="Capital One",
            account_number="4111",
            amount_owed="2450.00",
            minimum_payment="35.00",
            creditor_type="credit_card",
            confidence_score=88,
        )
        assert bill.creditor_name == "Capital One"
        assert str(bill.amount_owed) == "2450.00"
        assert bill.minimum_payment == Decimal("35.00")
        assert bill.confidence_score == 88

    def test_creditor_bill_schema_optional_fields(self):
        """Test schema works with optional fields missing."""
        from apps.documents.schemas.creditor_bill import CreditorBillExtraction

        bill = CreditorBillExtraction(
            creditor_name="City Hospital",
            amount_owed="850.00",
            creditor_type="medical",
            confidence_score=72,
        )
        assert bill.account_number is None
        assert bill.minimum_payment is None
        assert bill.due_date is None

    def test_creditor_bill_to_debt_type(self):
        """Test creditor_type mapping to debt type."""
        from apps.documents.schemas.creditor_bill import CreditorBillExtraction

        bill = CreditorBillExtraction(
            creditor_name="Test Creditor",
            amount_owed="1000.00",
            creditor_type="medical",
            confidence_score=80,
        )
        assert bill.to_debt_type() == "medical"

    def test_creditor_bill_validates_amount_positive(self):
        """Test amount_owed must be positive."""
        from apps.documents.schemas.creditor_bill import CreditorBillExtraction

        with pytest.raises(ValidationError) as exc_info:
            CreditorBillExtraction(
                creditor_name="Bad Creditor",
                amount_owed="-100.00",  # Negative!
                creditor_type="credit_card",
                confidence_score=85,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_creditor_bill_validates_minimum_payment_nonnegative(self):
        """Test minimum_payment must be non-negative if present."""
        from apps.documents.schemas.creditor_bill import CreditorBillExtraction

        with pytest.raises(ValidationError) as exc_info:
            CreditorBillExtraction(
                creditor_name="Bad Creditor",
                amount_owed="1000.00",
                minimum_payment="-50.00",  # Negative!
                creditor_type="credit_card",
                confidence_score=85,
            )
        assert "greater than or equal to 0" in str(exc_info.value)


class TestSchemaRegistry:
    """Tests for schema registry."""

    def test_get_schema_for_paystub(self):
        """Test retrieving pay stub schema."""
        schema = get_schema_for_type(DocumentType.PAY_STUB)
        assert schema == PayStubExtraction

    def test_get_schema_for_balance_sheet(self):
        """Test retrieving balance sheet schema."""
        schema = get_schema_for_type(DocumentType.BALANCE_SHEET)
        assert schema == BalanceSheetExtraction

    def test_get_schema_for_creditor_bill(self):
        """Test retrieving creditor bill schema."""
        from apps.documents.schemas.creditor_bill import CreditorBillExtraction

        schema = get_schema_for_type(DocumentType.CREDITOR_BILL)
        assert schema == CreditorBillExtraction

    def test_get_schema_raises_for_unsupported_type(self):
        """Test error for unsupported document type."""
        with pytest.raises(KeyError) as exc_info:
            get_schema_for_type(DocumentType.BANK_STATEMENT)

        assert "No extraction schema defined" in str(exc_info.value)

    def test_schema_map_contains_expected_types(self):
        """Test schema map has expected document types."""
        assert DocumentType.PAY_STUB in SCHEMA_MAP
        assert DocumentType.BALANCE_SHEET in SCHEMA_MAP
        assert DocumentType.PROFIT_LOSS in SCHEMA_MAP
        assert DocumentType.CREDITOR_BILL in SCHEMA_MAP
