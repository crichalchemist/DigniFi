"""Tests for Schedule J (Expenses) generator."""

import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import ExpenseInfo, IncomeInfo, IntakeSession
from apps.forms.services.schedule_j_generator import (
    ScheduleJGenerator,
    _calculate_cmi,
    _extract_expense_values,
    _build_empty_expenses,
    _sum_fields,
    EXPENSE_FIELDS,
    ZERO,
)

User = get_user_model()


# -- Fixtures --

def _create_district() -> District:
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


def _create_expense_info(session: IntakeSession, **overrides) -> ExpenseInfo:
    """Create ExpenseInfo with sensible defaults, overridable per-test."""
    defaults = {
        'session': session,
        'rent_or_mortgage': Decimal('800.00'),
        'utilities': Decimal('150.00'),
        'home_maintenance': Decimal('50.00'),
        'vehicle_payment': Decimal('250.00'),
        'vehicle_insurance': Decimal('100.00'),
        'vehicle_maintenance': Decimal('40.00'),
        'food_and_groceries': Decimal('400.00'),
        'clothing': Decimal('50.00'),
        'medical_expenses': Decimal('75.00'),
        'childcare': Decimal('0.00'),
        'child_support_paid': Decimal('0.00'),
        'insurance_not_deducted': Decimal('60.00'),
        'other_expenses': Decimal('25.00'),
    }
    defaults.update(overrides)
    return ExpenseInfo.objects.create(**defaults)


def _create_income_info(
    session: IntakeSession,
    monthly_income: list | None = None,
) -> IncomeInfo:
    """Create IncomeInfo with a 6-month income array."""
    return IncomeInfo.objects.create(
        session=session,
        marital_status='single',
        number_of_dependents=0,
        monthly_income=monthly_income or [0, 0, 0, 0, 0, 0],
    )


# -- Pure function tests (no database) --

class TestCalculateCMI:
    """Unit tests for the _calculate_cmi pure function."""

    def test_uniform_income(self):
        assert _calculate_cmi([3000, 3000, 3000, 3000, 3000, 3000]) == Decimal('3000.00')

    def test_varying_income(self):
        # (1000+2000+3000+4000+5000+6000) / 6 = 3500.00
        assert _calculate_cmi([1000, 2000, 3000, 4000, 5000, 6000]) == Decimal('3500.00')

    def test_zero_income(self):
        assert _calculate_cmi([0, 0, 0, 0, 0, 0]) == ZERO

    def test_empty_array_returns_zero(self):
        assert _calculate_cmi([]) == ZERO

    def test_none_returns_zero(self):
        assert _calculate_cmi(None) == ZERO

    def test_rounding(self):
        # (100+100+100+100+100+101) / 6 = 100.166... -> 100.17
        assert _calculate_cmi([100, 100, 100, 100, 100, 101]) == Decimal('100.17')


class TestBuildEmptyExpenses:
    """Verify zeroed-out expense dict covers all fields."""

    def test_all_fields_present(self):
        result = _build_empty_expenses()
        assert set(result.keys()) == set(EXPENSE_FIELDS)

    def test_all_values_zero(self):
        result = _build_empty_expenses()
        assert all(v == ZERO for v in result.values())


# -- Integration tests (database) --

@pytest.mark.django_db
class TestScheduleJGeneratorTotalExpenses:
    """Total expenses calculated correctly from multiple expense fields."""

    def test_total_expenses_summed_correctly(self):
        user = User.objects.create_user(username='test_total', password='test')
        district = _create_district()
        session = _create_session(user, district)
        _create_expense_info(session)

        result = ScheduleJGenerator(session).generate()

        # 800+150+50+250+100+40+400+50+75+0+0+60+25 = 2000.00
        assert result['total_expenses'] == Decimal('2000.00')

    def test_individual_fields_preserved(self):
        user = User.objects.create_user(username='test_fields', password='test')
        district = _create_district()
        session = _create_session(user, district)
        _create_expense_info(session, rent_or_mortgage=Decimal('1200.00'))

        result = ScheduleJGenerator(session).generate()

        assert result['rent_or_mortgage'] == Decimal('1200.00')
        assert result['utilities'] == Decimal('150.00')
        assert result['vehicle_payment'] == Decimal('250.00')


@pytest.mark.django_db
class TestScheduleJGeneratorNetIncome:
    """Net monthly income = CMI - total expenses (can be negative)."""

    def test_zero_income_produces_negative_net(self):
        """$0 income - $2000 expenses = -$2000 deficit."""
        user = User.objects.create_user(username='test_deficit', password='test')
        district = _create_district()
        session = _create_session(user, district)
        _create_expense_info(session)
        _create_income_info(session, monthly_income=[0, 0, 0, 0, 0, 0])

        result = ScheduleJGenerator(session).generate()

        assert result['total_income'] == ZERO
        assert result['total_expenses'] == Decimal('2000.00')
        assert result['net_monthly_income'] == Decimal('-2000.00')

    def test_positive_net_income(self):
        """Income exceeds expenses -> positive net."""
        user = User.objects.create_user(username='test_pos', password='test')
        district = _create_district()
        session = _create_session(user, district)
        _create_expense_info(
            session,
            rent_or_mortgage=Decimal('500.00'),
            utilities=Decimal('100.00'),
            home_maintenance=ZERO,
            vehicle_payment=ZERO,
            vehicle_insurance=ZERO,
            vehicle_maintenance=ZERO,
            food_and_groceries=Decimal('200.00'),
            clothing=ZERO,
            medical_expenses=ZERO,
            childcare=ZERO,
            child_support_paid=ZERO,
            insurance_not_deducted=ZERO,
            other_expenses=ZERO,
        )
        _create_income_info(
            session,
            monthly_income=[2000, 2000, 2000, 2000, 2000, 2000],
        )

        result = ScheduleJGenerator(session).generate()

        assert result['total_income'] == Decimal('2000.00')
        assert result['total_expenses'] == Decimal('800.00')
        assert result['net_monthly_income'] == Decimal('1200.00')


@pytest.mark.django_db
class TestScheduleJGeneratorMissingData:
    """Graceful handling of missing ExpenseInfo and IncomeInfo."""

    def test_missing_expense_info_returns_zeros(self):
        """No ExpenseInfo -> all expense fields zero, total zero."""
        user = User.objects.create_user(username='test_no_exp', password='test')
        district = _create_district()
        session = _create_session(user, district)

        result = ScheduleJGenerator(session).generate()

        assert result['total_expenses'] == ZERO
        assert result['rent_or_mortgage'] == ZERO
        assert result['food_and_groceries'] == ZERO
        assert result['net_monthly_income'] == ZERO

    def test_missing_income_info_returns_zero_income(self):
        """No IncomeInfo -> total_income = 0, net = -total_expenses."""
        user = User.objects.create_user(username='test_no_inc', password='test')
        district = _create_district()
        session = _create_session(user, district)
        _create_expense_info(session)

        result = ScheduleJGenerator(session).generate()

        assert result['total_income'] == ZERO
        assert result['total_expenses'] == Decimal('2000.00')
        assert result['net_monthly_income'] == Decimal('-2000.00')

    def test_missing_both_returns_all_zeros(self):
        """No ExpenseInfo and no IncomeInfo -> everything zero."""
        user = User.objects.create_user(username='test_no_both', password='test')
        district = _create_district()
        session = _create_session(user, district)

        result = ScheduleJGenerator(session).generate()

        assert result['total_expenses'] == ZERO
        assert result['total_income'] == ZERO
        assert result['net_monthly_income'] == ZERO


@pytest.mark.django_db
class TestScheduleJGeneratorPreview:
    """Preview method returns same data as generate."""

    def test_preview_equals_generate(self):
        user = User.objects.create_user(username='test_prev', password='test')
        district = _create_district()
        session = _create_session(user, district)
        _create_expense_info(session)
        _create_income_info(session, monthly_income=[1500, 1500, 1500, 1500, 1500, 1500])

        generator = ScheduleJGenerator(session)
        assert generator.preview() == generator.generate()
