"""Tests for intake models."""

import pytest
from django.contrib.auth import get_user_model
from apps.intake.models import DebtInfo, IntakeSession
from apps.districts.models import District

User = get_user_model()


@pytest.mark.django_db
class TestDebtInfoClassification:
    """Tests for Chapter 7 debt classification fields."""

    @pytest.fixture
    def user(self):
        """Create test user."""
        return User.objects.create_user(username="testuser", password="testpass123")

    @pytest.fixture
    def district(self):
        """Create test district."""
        return District.objects.first()  # Use existing ILND fixture

    @pytest.fixture
    def session(self, user, district):
        """Create test intake session."""
        return IntakeSession.objects.create(user=user, district=district)

    def test_consumer_business_classification_defaults_to_consumer(self, session):
        """Test that consumer_business_classification defaults to consumer."""
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Test Creditor",
            amount_owed=1000.00,
            debt_type="credit_card",
        )

        assert debt.consumer_business_classification == "consumer"

    def test_can_mark_debt_as_business(self, session):
        """Test that debt can be marked as business type."""
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Business Vendor",
            amount_owed=5000.00,
            debt_type="other",
            consumer_business_classification="business",
        )

        assert debt.consumer_business_classification == "business"

    def test_can_mark_debt_as_secured(self, session):
        """Test that debt can be marked as secured with collateral."""
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Auto Lender",
            amount_owed=15000.00,
            debt_type="auto_loan",
            is_secured=True,
            collateral_description="2020 Honda Civic VIN: 1HGBH41JXMN109186",
        )

        assert debt.is_secured is True
        assert debt.collateral_description == "2020 Honda Civic VIN: 1HGBH41JXMN109186"

    def test_can_mark_debt_as_priority(self, session):
        """Test that debt can be marked as priority unsecured."""
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="IRS",
            amount_owed=8000.00,
            debt_type="other",
            is_priority=True,
        )

        assert debt.is_priority is True

    def test_debt_status_flags(self, session):
        """Test contingent, unliquidated, and disputed flags."""
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Lawsuit Plaintiff",
            amount_owed=25000.00,
            debt_type="other",
            is_contingent=False,
            is_unliquidated=True,
            is_disputed=True,
        )

        assert debt.is_contingent is False
        assert debt.is_unliquidated is True
        assert debt.is_disputed is True

    def test_date_incurred_tracking(self, session):
        """Test that date_incurred can be set."""
        from datetime import date

        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Old Creditor",
            amount_owed=3000.00,
            debt_type="credit_card",
            date_incurred=date(2023, 6, 15),
        )

        assert debt.date_incurred == date(2023, 6, 15)

    def test_str_method_includes_classification(self, session):
        """Test that __str__ method includes consumer/business classification."""
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Business Supplier",
            amount_owed=10000.00,
            debt_type="other",
            consumer_business_classification="business",
        )

        str_repr = str(debt)
        assert "Business Supplier" in str_repr
        assert "Business" in str_repr  # Should show "Business Debt"


@pytest.mark.django_db
class TestFeeWaiverApplication:
    """Tests for Form 103B fee waiver application."""

    @pytest.fixture
    def user(self):
        """Create test user."""
        return User.objects.create_user(username="testuser", password="testpass123")

    @pytest.fixture
    def district(self):
        """Create test district."""
        return District.objects.first()  # Use existing ILND fixture

    @pytest.fixture
    def session(self, user, district):
        """Create test intake session."""
        return IntakeSession.objects.create(user=user, district=district)

    def test_fee_waiver_defaults_to_pending(self, session):
        """Test that fee waiver status defaults to pending."""
        from apps.intake.models import FeeWaiverApplication

        waiver = FeeWaiverApplication.objects.create(
            session=session,
            monthly_income=0.00,
            monthly_expenses=1200.00
        )

        assert waiver.status == 'pending'

    def test_qualifies_for_waiver_with_zero_income(self, session):
        """Test that $0 income automatically qualifies for fee waiver."""
        from apps.intake.models import FeeWaiverApplication

        waiver = FeeWaiverApplication.objects.create(
            session=session,
            monthly_income=0.00,
            monthly_expenses=1200.00
        )

        # Poverty threshold for 1 person: $1,882.50/month
        assert waiver.qualifies_for_waiver() is True

    def test_qualifies_for_waiver_with_public_benefits(self, session):
        """Test that receiving public benefits qualifies for waiver."""
        from apps.intake.models import FeeWaiverApplication

        waiver = FeeWaiverApplication.objects.create(
            session=session,
            monthly_income=800.00,
            monthly_expenses=1200.00,
            receives_public_benefits=True,
            benefit_types=['SNAP', 'Medicaid']
        )

        assert waiver.qualifies_for_waiver() is True

    def test_household_size_must_be_positive(self, session):
        """Test that household_size must be >= 1."""
        from django.core.exceptions import ValidationError
        from apps.intake.models import FeeWaiverApplication

        waiver = FeeWaiverApplication(
            session=session,
            monthly_income=0.00,
            monthly_expenses=1200.00,
            household_size=0  # Invalid!
        )

        with pytest.raises(ValidationError):
            waiver.full_clean()  # Triggers validators

    def test_public_benefits_qualification_simplified(self, session):
        """Test that receives_public_benefits=True qualifies (no benefit_types required)."""
        from apps.intake.models import FeeWaiverApplication

        # User receives benefits but hasn't listed them yet
        waiver = FeeWaiverApplication.objects.create(
            session=session,
            monthly_income=2500.00,  # Above threshold
            monthly_expenses=1200.00,
            receives_public_benefits=True,
            benefit_types=[]  # Empty list - should still qualify
        )

        assert waiver.qualifies_for_waiver() is True
