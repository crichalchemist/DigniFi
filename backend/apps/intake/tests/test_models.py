"""Tests for intake models."""

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import DebtInfo, IntakeSession

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
        return District.objects.create(
            code="ILND",
            name="Illinois Northern",
            state="IL",
            court_name="U.S. Bankruptcy Court ILND",
            filing_fee_chapter_7=338.00,
        )

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

    def test_a_debt_incurred_over_time_keeps_its_range_of_dates(self, session):
        """The national instructions ask for the range of dates (3c2 R4)."""
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Old Creditor",
            amount_owed=3000.00,
            debt_type="credit_card",
            date_incurred="2019–2025",
        )
        debt.refresh_from_db()

        assert debt.date_incurred == "2019–2025"

    def test_a_debt_shows_its_id_type_and_classification_but_never_the_creditor(self, session):
        """Test that __str__ method includes consumer/business classification."""
        debt = DebtInfo.objects.create(
            session=session,
            creditor_name="Business Supplier",
            amount_owed=10000.00,
            debt_type="other",
            consumer_business_classification="business",
        )

        str_repr = str(debt)
        assert "Business Supplier" not in str_repr
        assert str(debt.pk) in str_repr
        assert "Business" in str_repr  # Should show "Business Debt"
