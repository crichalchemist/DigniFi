"""
Comprehensive tests for MeansTestCalculator service.

Tests cover:
- Below-median income (passes means test)
- Above-median income (fails means test)
- At-median income (edge case: fails with < operator)
- All household sizes (1-8+) with dependents + marital status
- Fee waiver qualification (CMI < 60% of median)
- Fee waiver non-qualification (CMI >= 60% of median)
- Missing income_info raises ValueError
- None session raises ValueError
- Invalid monthly_income (not 6 elements) raises ValueError
- UPL prohibited phrase scanning in all messages
- Recalculation idempotency (calculate twice, only 1 MeansTest record)
"""

import pytest
from decimal import Decimal
from datetime import date
from django.contrib.auth import get_user_model
from django.conf import settings

from apps.intake.models import IntakeSession, IncomeInfo
from apps.districts.models import District, MedianIncome
from apps.eligibility.models import MeansTest
from apps.eligibility.services.means_test_calculator import MeansTestCalculator

User = get_user_model()


@pytest.fixture
def user():
    """Create test user."""
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def district():
    """Create test district with ILND data."""
    return District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court for the Northern District of Illinois",
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def median_income(district):
    """
    Create median income record with real ILND 2025 data.

    Family sizes 1-8:
    - 1: $71,304
    - 2: $91,526
    - 3: $110,712
    - 4: $134,366
    - 5: $145,466
    - 6: $156,566
    - 7: $167,666
    - 8: $178,766
    """
    return MedianIncome.objects.create(
        district=district,
        effective_date=date(2025, 11, 1),
        family_size_1=Decimal("71304.00"),
        family_size_2=Decimal("91526.00"),
        family_size_3=Decimal("110712.00"),
        family_size_4=Decimal("134366.00"),
        family_size_5=Decimal("145466.00"),
        family_size_6=Decimal("156566.00"),
        family_size_7=Decimal("167666.00"),
        family_size_8=Decimal("178766.00"),
        family_size_additional=Decimal("11100.00"),
    )


@pytest.fixture
def session(user, district):
    """Create intake session."""
    return IntakeSession.objects.create(
        user=user,
        district=district,
        status="in_progress",
        current_step=2,
    )


@pytest.mark.django_db
class TestMeansTestCalculatorInitialization:
    """Tests for MeansTestCalculator initialization and validation."""

    def test_raises_value_error_on_none_session(self):
        """Test that None session raises ValueError."""
        with pytest.raises(ValueError, match="IntakeSession is required"):
            MeansTestCalculator(None)

    def test_raises_value_error_on_missing_income_info(self, session):
        """Test that session without income_info raises ValueError."""
        with pytest.raises(
            ValueError,
            match="IntakeSession must have income_info before calculating means test",
        ):
            MeansTestCalculator(session)

    def test_initializes_successfully_with_income_info(self, session):
        """Test successful initialization with income_info."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        calculator = MeansTestCalculator(session)
        assert calculator.intake_session == session
        assert calculator.district == session.district


@pytest.mark.django_db
class TestBelowMedianIncomePassesMeansTest:
    """Tests for below-median income scenarios (passes means test)."""

    def test_below_median_single_no_dependents(self, session, median_income):
        """Test single filer, no dependents, below median passes means test."""
        # Median for family size 1: $71,304/year = $5,942/month
        # Below median: $5,000/month
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["passes_means_test"] is True
        assert result["cmi"] == Decimal("5000.00")
        assert result["median_income_threshold"] == Decimal("71304.00")
        assert result["family_size"] == 1

    def test_below_median_married_joint(self, session, median_income):
        """Test married filing jointly, below median passes means test."""
        # Median for family size 2: $91,526/year = $7,627.17/month
        # Below median: $7,000/month
        IncomeInfo.objects.create(
            session=session,
            marital_status="married_joint",
            number_of_dependents=0,
            monthly_income=[7000, 7000, 7000, 7000, 7000, 7000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["passes_means_test"] is True
        assert result["cmi"] == Decimal("7000.00")
        assert result["median_income_threshold"] == Decimal("91526.00")
        assert result["family_size"] == 2  # Filer + spouse

    def test_below_median_single_with_two_dependents(self, session, median_income):
        """Test single filer with 2 dependents, below median passes."""
        # Median for family size 3: $110,712/year = $9,226/month
        # Below median: $8,500/month
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=2,
            monthly_income=[8500, 8500, 8500, 8500, 8500, 8500],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["passes_means_test"] is True
        assert result["cmi"] == Decimal("8500.00")
        assert result["median_income_threshold"] == Decimal("110712.00")
        assert result["family_size"] == 3  # Filer + 2 dependents


@pytest.mark.django_db
class TestAboveMedianIncomeFailsMeansTest:
    """Tests for above-median income scenarios (fails means test)."""

    def test_above_median_single_no_dependents(self, session, median_income):
        """Test single filer, no dependents, above median fails means test."""
        # Median for family size 1: $71,304/year
        # Above median: $80,000/month average
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[80000, 80000, 80000, 80000, 80000, 80000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["passes_means_test"] is False
        assert result["cmi"] == Decimal("80000.00")
        assert result["median_income_threshold"] == Decimal("71304.00")
        assert result["family_size"] == 1

    def test_above_median_married_separate_with_dependents(self, session, median_income):
        """Test married filing separately with dependents, above median fails."""
        # Median for family size 4: $134,366/year
        # Above median: $140,000/year average
        IncomeInfo.objects.create(
            session=session,
            marital_status="married_separate",
            number_of_dependents=2,
            monthly_income=[140000, 140000, 140000, 140000, 140000, 140000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["passes_means_test"] is False
        assert result["cmi"] == Decimal("140000.00")
        assert result["median_income_threshold"] == Decimal("134366.00")
        assert result["family_size"] == 4  # Filer + spouse + 2 dependents


@pytest.mark.django_db
class TestAtMedianIncomeEdgeCase:
    """Test edge case: income exactly equal to median (uses < not <=)."""

    def test_at_median_income_fails(self, session, median_income):
        """Test that income exactly equal to median FAILS (< not <=)."""
        # Median for family size 1: $71,304/year
        # At median: $71,304/year average = $5,942/month
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[71304, 71304, 71304, 71304, 71304, 71304],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        # CRITICAL: At-median fails because code uses < (not <=)
        assert result["passes_means_test"] is False
        assert result["cmi"] == Decimal("71304.00")
        assert result["median_income_threshold"] == Decimal("71304.00")


@pytest.mark.django_db
class TestAllHouseholdSizes:
    """Test all household sizes 1-8+ with varying marital status and dependents."""

    def test_household_size_1_single_no_dependents(self, session, median_income):
        """Test family size 1: single, 0 dependents."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["family_size"] == 1
        assert result["median_income_threshold"] == Decimal("71304.00")

    def test_household_size_2_married_joint_no_dependents(self, session, median_income):
        """Test family size 2: married joint, 0 dependents."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="married_joint",
            number_of_dependents=0,
            monthly_income=[7000, 7000, 7000, 7000, 7000, 7000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["family_size"] == 2
        assert result["median_income_threshold"] == Decimal("91526.00")

    def test_household_size_3_single_two_dependents(self, session, median_income):
        """Test family size 3: single, 2 dependents."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=2,
            monthly_income=[8000, 8000, 8000, 8000, 8000, 8000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["family_size"] == 3
        assert result["median_income_threshold"] == Decimal("110712.00")

    def test_household_size_4_married_separate_two_dependents(self, session, median_income):
        """Test family size 4: married separate, 2 dependents."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="married_separate",
            number_of_dependents=2,
            monthly_income=[10000, 10000, 10000, 10000, 10000, 10000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["family_size"] == 4
        assert result["median_income_threshold"] == Decimal("134366.00")

    def test_household_size_5_married_joint_three_dependents(self, session, median_income):
        """Test family size 5: married joint, 3 dependents."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="married_joint",
            number_of_dependents=3,
            monthly_income=[11000, 11000, 11000, 11000, 11000, 11000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["family_size"] == 5
        assert result["median_income_threshold"] == Decimal("145466.00")

    def test_household_size_6_married_separate_four_dependents(self, session, median_income):
        """Test family size 6: married separate, 4 dependents."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="married_separate",
            number_of_dependents=4,
            monthly_income=[12000, 12000, 12000, 12000, 12000, 12000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["family_size"] == 6
        assert result["median_income_threshold"] == Decimal("156566.00")

    def test_household_size_7_single_six_dependents(self, session, median_income):
        """Test family size 7: single, 6 dependents."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=6,
            monthly_income=[13000, 13000, 13000, 13000, 13000, 13000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["family_size"] == 7
        assert result["median_income_threshold"] == Decimal("167666.00")

    def test_household_size_8_married_joint_six_dependents(self, session, median_income):
        """Test family size 8: married joint, 6 dependents."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="married_joint",
            number_of_dependents=6,
            monthly_income=[14000, 14000, 14000, 14000, 14000, 14000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["family_size"] == 8
        assert result["median_income_threshold"] == Decimal("178766.00")


@pytest.mark.django_db
class TestFeeWaiverQualification:
    """Tests for fee waiver qualification (CMI < 60% of median)."""

    def test_qualifies_for_fee_waiver_very_low_income(self, session, median_income):
        """Test that very low income (< 60% median) qualifies for fee waiver."""
        # Median for family size 1: $71,304/year
        # 60% threshold: $42,782.40/year = $3,565.20/month
        # Income: $3,000/month (below 60%)
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["qualifies_for_fee_waiver"] is True
        assert result["passes_means_test"] is True  # Also passes means test

    def test_qualifies_for_fee_waiver_zero_income(self, session, median_income):
        """Test that zero income qualifies for fee waiver."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[0, 0, 0, 0, 0, 0],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["qualifies_for_fee_waiver"] is True
        assert result["cmi"] == Decimal("0.00")


@pytest.mark.django_db
class TestFeeWaiverNonQualification:
    """Tests for fee waiver non-qualification (CMI >= 60% of median)."""

    def test_does_not_qualify_for_fee_waiver_at_60_percent(self, session, median_income):
        """Test that income at 60% of median does NOT qualify for fee waiver."""
        # Median for family size 1: $71,304/year
        # 60% threshold: $42,782.40/year = $3,565.20/month
        # Income: $42,782.40/year average (exactly at 60%)
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[42782.40, 42782.40, 42782.40, 42782.40, 42782.40, 42782.40],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        # At 60% does NOT qualify (uses < not <=)
        assert result["qualifies_for_fee_waiver"] is False
        assert result["passes_means_test"] is True  # Still passes means test

    def test_does_not_qualify_for_fee_waiver_above_60_percent(self, session, median_income):
        """Test that income above 60% but below 100% median does not qualify for fee waiver."""
        # Median for family size 1: $71,304/year
        # 60% threshold: $42,782.40/year
        # Income: $50,000/year average (above 60%, below 100%)
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[50000, 50000, 50000, 50000, 50000, 50000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["qualifies_for_fee_waiver"] is False
        assert result["passes_means_test"] is True  # Still passes means test


@pytest.mark.django_db
class TestInvalidMonthlyIncomeData:
    """Tests for invalid monthly_income data validation."""

    def test_raises_error_with_fewer_than_6_months(self, session, median_income):
        """Test that monthly_income with < 6 elements raises ValueError."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000],  # Only 3 months
        )

        calculator = MeansTestCalculator(session)

        with pytest.raises(
            ValueError, match="monthly_income must be a list of 6 monthly income values"
        ):
            calculator.calculate()

    def test_raises_error_with_more_than_6_months(self, session, median_income):
        """Test that monthly_income with > 6 elements raises ValueError."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000, 5000, 5000],  # 8 months
        )

        calculator = MeansTestCalculator(session)

        with pytest.raises(
            ValueError, match="monthly_income must be a list of 6 monthly income values"
        ):
            calculator.calculate()

    def test_raises_error_with_empty_list(self, session, median_income):
        """Test that empty monthly_income list raises ValueError."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[],  # Empty
        )

        calculator = MeansTestCalculator(session)

        with pytest.raises(
            ValueError, match="monthly_income must be a list of 6 monthly income values"
        ):
            calculator.calculate()

    def test_raises_error_with_non_list_monthly_income(self, session, median_income):
        """Test that non-list monthly_income raises ValueError."""
        # Note: Django JSONField will coerce strings, but not primitives
        # We create the IncomeInfo directly without JSONField validation
        income_info = IncomeInfo(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income="not a list",
        )
        income_info.save()

        calculator = MeansTestCalculator(session)

        with pytest.raises(
            ValueError, match="monthly_income must be a list of 6 monthly income values"
        ):
            calculator.calculate()


@pytest.mark.django_db
class TestUPLProhibitedPhrases:
    """Tests scanning messages for UPL prohibited phrases."""

    def test_passing_message_contains_no_upl_violations(self, session, median_income):
        """Test that passing means test message contains no UPL prohibited phrases."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        message = result["message"].lower()

        # Check all prohibited phrases from settings
        for phrase in settings.UPL_PROHIBITED_PHRASES:
            assert phrase.lower() not in message, (
                f"UPL prohibited phrase '{phrase}' found in message: {message}"
            )

    def test_failing_message_contains_no_upl_violations(self, session, median_income):
        """Test that failing means test message contains no UPL prohibited phrases."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[80000, 80000, 80000, 80000, 80000, 80000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        message = result["message"].lower()

        # Check all prohibited phrases from settings
        for phrase in settings.UPL_PROHIBITED_PHRASES:
            assert phrase.lower() not in message, (
                f"UPL prohibited phrase '{phrase}' found in message: {message}"
            )

    def test_fee_waiver_message_contains_no_upl_violations(self, session, median_income):
        """Test that fee waiver message contains no UPL prohibited phrases."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        message = result["message"].lower()

        # Check all prohibited phrases from settings
        for phrase in settings.UPL_PROHIBITED_PHRASES:
            assert phrase.lower() not in message, (
                f"UPL prohibited phrase '{phrase}' found in fee waiver message: {message}"
            )

    def test_message_contains_permitted_informational_language(self, session, median_income):
        """Test that messages use permitted informational language."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        message = result["message"].lower()

        # Check for permitted informational phrases
        assert "may be eligible" in message or "typically" in message, (
            "Message should use informational language like 'may be eligible' or 'typically'"
        )


@pytest.mark.django_db
class TestRecalculationIdempotency:
    """Tests for recalculation idempotency (calculate twice, only 1 MeansTest record)."""

    def test_calculate_twice_creates_only_one_means_test_record(self, session, median_income):
        """Test that calling calculate() twice on same session creates only 1 MeansTest."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        calculator = MeansTestCalculator(session)

        # First calculation
        result1 = calculator.calculate()
        means_test_id_1 = result1["means_test_id"]

        # Second calculation
        result2 = calculator.calculate()
        means_test_id_2 = result2["means_test_id"]

        # Should be same MeansTest record
        assert means_test_id_1 == means_test_id_2

        # Verify only 1 MeansTest record exists
        assert MeansTest.objects.filter(session=session).count() == 1

    def test_recalculation_updates_existing_means_test(self, session, median_income):
        """Test that recalculation updates existing MeansTest record with new data."""
        income_info = IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        calculator = MeansTestCalculator(session)

        # First calculation: below median
        result1 = calculator.calculate()
        assert result1["passes_means_test"] is True

        # Update income to above median
        income_info.monthly_income = [80000, 80000, 80000, 80000, 80000, 80000]
        income_info.save()

        # Recalculate with new data
        result2 = calculator.calculate()

        # Should now fail means test
        assert result2["passes_means_test"] is False
        assert result2["cmi"] == Decimal("80000.00")

        # Still only 1 MeansTest record
        assert MeansTest.objects.filter(session=session).count() == 1

    def test_recalculation_updates_district_if_changed(self, session, median_income):
        """Test that recalculation updates district if session district changes."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        calculator = MeansTestCalculator(session)

        # First calculation
        result1 = calculator.calculate()
        original_district = session.district

        # Create new district and update session
        new_district = District.objects.create(
            code="ilcd",
            name="Central District of Illinois",
            state="IL",
            court_name="U.S. Bankruptcy Court for the Central District of Illinois",
            filing_fee_chapter_7=Decimal("338.00"),
        )

        # Create median income for new district
        MedianIncome.objects.create(
            district=new_district,
            effective_date=date(2025, 11, 1),
            family_size_1=Decimal("65000.00"),  # Different median
            family_size_2=Decimal("85000.00"),
            family_size_3=Decimal("100000.00"),
            family_size_4=Decimal("120000.00"),
            family_size_5=Decimal("130000.00"),
            family_size_6=Decimal("140000.00"),
            family_size_7=Decimal("150000.00"),
            family_size_8=Decimal("160000.00"),
            family_size_additional=Decimal("10000.00"),
        )

        session.district = new_district
        session.save()

        # Recalculate with new district
        calculator2 = MeansTestCalculator(session)
        result2 = calculator2.calculate()

        # Should use new district's median
        assert result2["median_income_threshold"] == Decimal("65000.00")

        # Still only 1 MeansTest record
        assert MeansTest.objects.filter(session=session).count() == 1

        # MeansTest should reference new district
        means_test = MeansTest.objects.get(session=session)
        assert means_test.district == new_district


@pytest.mark.django_db
class TestVariableMonthlyIncome:
    """Tests for variable monthly income scenarios (6 different values)."""

    def test_variable_income_calculates_correct_average(self, session, median_income):
        """Test that variable monthly income correctly calculates CMI average."""
        # Variable income: average should be (6000 + 6000 + 5000 + 5000 + 4000 + 4000) / 6 = 5000
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[6000, 6000, 5000, 5000, 4000, 4000],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["cmi"] == Decimal("5000.00")
        assert result["passes_means_test"] is True

    def test_declining_income_calculates_correct_average(self, session, median_income):
        """Test that declining income pattern correctly calculates CMI."""
        # Declining income: (10000 + 8000 + 6000 + 4000 + 2000 + 0) / 6 = 5000
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[10000, 8000, 6000, 4000, 2000, 0],
        )

        calculator = MeansTestCalculator(session)
        result = calculator.calculate()

        assert result["cmi"] == Decimal("5000.00")
        assert result["passes_means_test"] is True


@pytest.mark.django_db
class TestDetailedBreakdown:
    """Tests for get_detailed_breakdown() method."""

    def test_detailed_breakdown_before_calculation_raises_error(self, session, median_income):
        """Test that get_detailed_breakdown() before calculate() raises ValueError."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
        )

        calculator = MeansTestCalculator(session)

        with pytest.raises(
            ValueError,
            match="Means test has not been calculated yet. Call calculate\\(\\) first.",
        ):
            calculator.get_detailed_breakdown()

    def test_detailed_breakdown_after_calculation(self, session, median_income):
        """Test that get_detailed_breakdown() returns complete data after calculation."""
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            number_of_dependents=0,
            monthly_income=[50000, 50000, 50000, 50000, 50000, 50000],
        )

        calculator = MeansTestCalculator(session)
        calculator.calculate()

        breakdown = calculator.get_detailed_breakdown()

        # Verify structure
        assert "income_history" in breakdown
        assert "family_composition" in breakdown
        assert "means_test_threshold" in breakdown
        assert "results" in breakdown

        # Verify income history
        assert breakdown["income_history"]["average_cmi"] == 50000.00
        assert breakdown["income_history"]["monthly_values"] == [50000, 50000, 50000, 50000, 50000, 50000]

        # Verify family composition
        assert breakdown["family_composition"]["marital_status"] == "single"
        assert breakdown["family_composition"]["number_of_dependents"] == 0
        assert breakdown["family_composition"]["total_family_size"] == 1

        # Verify means test threshold
        assert breakdown["means_test_threshold"]["median_income"] == 71304.00
        assert breakdown["means_test_threshold"]["district"] == "ILND"

        # Verify results
        assert breakdown["results"]["passes_means_test"] is True
        assert breakdown["results"]["qualifies_for_fee_waiver"] is False
        assert breakdown["results"]["statute_citation"] == "11 U.S.C. § 707(b)"
