"""Tests for Pydantic extraction schemas."""

from decimal import Decimal
from datetime import date
import pytest
from pydantic import ValidationError

from apps.documents.schemas import PayStubExtraction


class TestPayStubExtraction:
    """Tests for PayStubExtraction schema."""

    def test_valid_paystub_data(self):
        """Test schema accepts valid pay stub data."""
        data = {
            'employer_name': 'Acme Corp',
            'gross_pay': '3240.00',
            'pay_period_start': '2026-01-01',
            'pay_period_end': '2026-01-15',
            'ytd_gross': '3240.00',
            'net_pay': '2450.00',
            'deductions_total': '790.00',
            'confidence_score': 92
        }

        result = PayStubExtraction(**data)

        assert result.employer_name == 'Acme Corp'
        assert result.gross_pay == Decimal('3240.00')
        assert result.pay_period_start == date(2026, 1, 1)
        assert result.pay_period_end == date(2026, 1, 15)
        assert result.confidence_score == 92

    def test_minimal_paystub_data(self):
        """Test schema works with only required fields."""
        data = {
            'employer_name': 'Test Inc',
            'gross_pay': '1500.00',
            'pay_period_start': '2026-01-01',
            'pay_period_end': '2026-01-15',
            'confidence_score': 85
        }

        result = PayStubExtraction(**data)

        assert result.ytd_gross is None
        assert result.net_pay is None
        assert result.deductions_total is None

    def test_validates_pay_period_order(self):
        """Test end date must be after start date."""
        data = {
            'employer_name': 'Test Inc',
            'gross_pay': '1500.00',
            'pay_period_start': '2026-01-15',
            'pay_period_end': '2026-01-01',  # Before start!
            'confidence_score': 85
        }

        with pytest.raises(ValidationError) as exc_info:
            PayStubExtraction(**data)

        assert 'after start date' in str(exc_info.value)

    def test_validates_gross_pay_positive(self):
        """Test gross pay must be positive."""
        data = {
            'employer_name': 'Test Inc',
            'gross_pay': '-100.00',  # Negative!
            'pay_period_start': '2026-01-01',
            'pay_period_end': '2026-01-15',
            'confidence_score': 85
        }

        with pytest.raises(ValidationError) as exc_info:
            PayStubExtraction(**data)

        assert 'greater than 0' in str(exc_info.value)

    def test_validates_confidence_range(self):
        """Test confidence score must be 0-100."""
        data = {
            'employer_name': 'Test Inc',
            'gross_pay': '1500.00',
            'pay_period_start': '2026-01-01',
            'pay_period_end': '2026-01-15',
            'confidence_score': 150  # Over 100!
        }

        with pytest.raises(ValidationError) as exc_info:
            PayStubExtraction(**data)

        assert 'less than or equal to 100' in str(exc_info.value)
