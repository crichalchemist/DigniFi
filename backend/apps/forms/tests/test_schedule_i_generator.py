"""Tests for Schedule I (Current Income of Individual Debtor(s)) generator."""

import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import IncomeInfo, IntakeSession
from apps.forms.services.schedule_i_generator import (
    ScheduleIGenerator,
    _compute_cmi,
    _build_schedule_i_data,
)

User = get_user_model()


def _create_ilnd_district() -> District:
    """Create ILND district fixture for tests."""
    return District.objects.create(
        code='ilnd',
        name='Northern District of Illinois',
        state='IL',
        court_name='U.S. Bankruptcy Court, Northern District of Illinois',
        pro_se_efiling_allowed=False,
        filing_fee_chapter_7=Decimal('338.00'),
    )


def _create_session(user, district: District) -> IntakeSession:
    return IntakeSession.objects.create(user=user, district=district)


def _create_income_info(
    session: IntakeSession,
    monthly_income: list,
    marital_status: str = 'single',
    number_of_dependents: int = 0,
) -> IncomeInfo:
    """Create IncomeInfo with given monthly income array."""
    return IncomeInfo.objects.create(
        session=session,
        marital_status=marital_status,
        number_of_dependents=number_of_dependents,
        monthly_income=monthly_income,
    )


# -- Pure function tests (no database) --

class TestComputeCMI:
    """Unit tests for the pure _compute_cmi helper."""

    def test_all_zeros_returns_zero(self):
        """Six months of $0 income yields CMI of $0."""
        assert _compute_cmi([0, 0, 0, 0, 0, 0]) == Decimal('0.00')

    def test_uniform_income(self):
        """Uniform monthly income yields that same value as CMI."""
        assert _compute_cmi([3000, 3000, 3000, 3000, 3000, 3000]) == Decimal('3000.00')

    def test_varying_income(self):
        """CMI is the average of 6 varying monthly amounts."""
        # (3000 + 3200 + 2800 + 3100 + 3000 + 3050) / 6 = 18150 / 6 = 3025.00
        result = _compute_cmi([3000, 3200, 2800, 3100, 3000, 3050])
        assert result == Decimal('3025.00')

    def test_empty_list_returns_zero(self):
        """Empty income array guards against division by zero."""
        assert _compute_cmi([]) == Decimal('0.00')

    def test_rounding(self):
        """CMI rounds to 2 decimal places (ROUND_HALF_UP)."""
        # (1000 + 1000 + 1000 + 1000 + 1000 + 1001) / 6 = 6001 / 6 = 1000.166...
        result = _compute_cmi([1000, 1000, 1000, 1000, 1000, 1001])
        assert result == Decimal('1000.17')

    def test_single_month(self):
        """Handles non-standard array length gracefully."""
        assert _compute_cmi([5000]) == Decimal('5000.00')


class TestBuildScheduleIData:
    """Unit tests for the pure _build_schedule_i_data helper."""

    def test_zero_income_flags_has_no_income(self):
        """$0 CMI sets has_no_income to True."""
        result = _build_schedule_i_data('single', 0, [0, 0, 0, 0, 0, 0])
        assert result['has_no_income'] is True
        assert result['current_monthly_income'] == Decimal('0.00')
        assert result['total_monthly_income'] == Decimal('0.00')

    def test_positive_income_flags_has_income(self):
        """Positive CMI sets has_no_income to False."""
        result = _build_schedule_i_data('married_joint', 2, [4000, 4000, 4000, 4000, 4000, 4000])
        assert result['has_no_income'] is False
        assert result['current_monthly_income'] == Decimal('4000.00')

    def test_includes_marital_status_and_dependents(self):
        """Output includes marital_status and number_of_dependents."""
        result = _build_schedule_i_data('married_separate', 3, [0, 0, 0, 0, 0, 0])
        assert result['marital_status'] == 'married_separate'
        assert result['number_of_dependents'] == 3

    def test_preserves_raw_income_history(self):
        """monthly_income_history contains the raw 6-month array."""
        history = [1500, 1600, 1400, 1550, 1500, 1450]
        result = _build_schedule_i_data('single', 0, history)
        assert result['monthly_income_history'] == history

    def test_total_equals_cmi(self):
        """total_monthly_income equals current_monthly_income for Schedule I."""
        result = _build_schedule_i_data('single', 1, [2000, 2200, 1800, 2100, 2000, 1900])
        assert result['total_monthly_income'] == result['current_monthly_income']


# -- Integration tests (database) --

@pytest.mark.django_db
class TestScheduleIGenerator:
    """Schedule I income generator integration tests."""

    def test_zero_income_case(self):
        """$0 income across all 6 months flags has_no_income and zeros totals."""
        user = User.objects.create_user(username='test_zero', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_income_info(session, [0, 0, 0, 0, 0, 0])

        result = ScheduleIGenerator(session).generate()

        assert result['has_no_income'] is True
        assert result['current_monthly_income'] == Decimal('0.00')
        assert result['total_monthly_income'] == Decimal('0.00')
        assert result['monthly_income_history'] == [0, 0, 0, 0, 0, 0]

    def test_income_with_values(self):
        """Non-zero income computes correct CMI average."""
        user = User.objects.create_user(username='test_vals', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_income_info(session, [3000, 3200, 2800, 3100, 3000, 3050])

        result = ScheduleIGenerator(session).generate()

        assert result['has_no_income'] is False
        assert result['current_monthly_income'] == Decimal('3025.00')
        assert result['total_monthly_income'] == Decimal('3025.00')

    def test_missing_income_info_defaults_to_zeros(self):
        """Session without IncomeInfo returns graceful defaults (all zeros)."""
        user = User.objects.create_user(username='test_miss', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        # No IncomeInfo created

        result = ScheduleIGenerator(session).generate()

        assert result['has_no_income'] is True
        assert result['current_monthly_income'] == Decimal('0.00')
        assert result['total_monthly_income'] == Decimal('0.00')
        assert result['marital_status'] == 'single'
        assert result['number_of_dependents'] == 0
        assert result['monthly_income_history'] == [0, 0, 0, 0, 0, 0]

    def test_marital_status_and_dependents_included(self):
        """Marital status and dependents flow through to output."""
        user = User.objects.create_user(username='test_mar', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_income_info(
            session,
            [5000, 5000, 5000, 5000, 5000, 5000],
            marital_status='married_joint',
            number_of_dependents=3,
        )

        result = ScheduleIGenerator(session).generate()

        assert result['marital_status'] == 'married_joint'
        assert result['number_of_dependents'] == 3

    def test_preview_returns_same_as_generate(self):
        """Preview method returns identical data to generate."""
        user = User.objects.create_user(username='test_prev', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        _create_income_info(session, [2000, 2000, 2000, 2000, 2000, 2000])

        generator = ScheduleIGenerator(session)
        assert generator.preview() == generator.generate()

    def test_partial_income_months(self):
        """Income that transitions from $0 to positive computes correct average."""
        user = User.objects.create_user(username='test_part', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)
        # Lost job for 3 months, then found new work
        _create_income_info(session, [0, 0, 0, 2400, 2400, 2400])

        result = ScheduleIGenerator(session).generate()

        # (0+0+0+2400+2400+2400) / 6 = 7200 / 6 = 1200.00
        assert result['has_no_income'] is False
        assert result['current_monthly_income'] == Decimal('1200.00')
        assert result['total_monthly_income'] == Decimal('1200.00')
