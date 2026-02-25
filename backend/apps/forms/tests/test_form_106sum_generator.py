"""Tests for Form 106Sum (Summary of Assets and Liabilities) generator."""

import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import (
    IntakeSession,
    AssetInfo,
    DebtInfo,
    IncomeInfo,
    ExpenseInfo,
)
from apps.forms.services.form_106sum_generator import Form106SumGenerator

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


@pytest.mark.django_db
class TestForm106SumTotalAssets:
    """Schedule A/B summary: total assets from AssetInfo records."""

    def test_sums_multiple_assets(self):
        """Total assets aggregates current_value across all session assets."""
        user = User.objects.create_user(username='test_assets', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='vehicle',
            description='Car',
            current_value=Decimal('10000.00'),
        )
        AssetInfo.objects.create(
            session=session,
            asset_type='bank_account',
            description='Savings',
            current_value=Decimal('500.00'),
        )

        result = Form106SumGenerator(session).generate()

        assert result['total_assets'] == Decimal('10500.00')
        assert result['number_of_assets'] == 2

    def test_no_assets_returns_zero(self):
        """Empty asset set produces zero totals."""
        user = User.objects.create_user(username='test_no_assets', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form106SumGenerator(session).generate()

        assert result['total_assets'] == Decimal('0.00')
        assert result['number_of_assets'] == 0


@pytest.mark.django_db
class TestForm106SumTotalDebts:
    """Schedule D / E/F summary: secured and unsecured debt totals."""

    def test_separates_secured_and_unsecured(self):
        """Debts are classified into secured (Sched D) and unsecured (Sched E/F)."""
        user = User.objects.create_user(username='test_debts', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        DebtInfo.objects.create(
            session=session,
            creditor_name='Auto Lender',
            debt_type='auto_loan',
            amount_owed=Decimal('15000.00'),
            is_secured=True,
        )
        DebtInfo.objects.create(
            session=session,
            creditor_name='Credit Card Co',
            debt_type='credit_card',
            amount_owed=Decimal('5000.00'),
            is_secured=False,
        )

        result = Form106SumGenerator(session).generate()

        assert result['total_secured_debts'] == Decimal('15000.00')
        assert result['total_unsecured_debts'] == Decimal('5000.00')
        assert result['total_debts'] == Decimal('20000.00')
        assert result['number_of_creditors'] == 2

    def test_no_debts_returns_zero(self):
        """Empty debt set produces zero totals."""
        user = User.objects.create_user(username='test_no_debts', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form106SumGenerator(session).generate()

        assert result['total_secured_debts'] == Decimal('0.00')
        assert result['total_unsecured_debts'] == Decimal('0.00')
        assert result['total_debts'] == Decimal('0.00')
        assert result['number_of_creditors'] == 0

    def test_multiple_secured_debts_summed(self):
        """Multiple secured debts are summed correctly."""
        user = User.objects.create_user(username='test_multi_sec', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        DebtInfo.objects.create(
            session=session,
            creditor_name='Mortgage Co',
            debt_type='mortgage',
            amount_owed=Decimal('180000.00'),
            is_secured=True,
        )
        DebtInfo.objects.create(
            session=session,
            creditor_name='Auto Lender',
            debt_type='auto_loan',
            amount_owed=Decimal('12000.00'),
            is_secured=True,
        )

        result = Form106SumGenerator(session).generate()

        assert result['total_secured_debts'] == Decimal('192000.00')
        assert result['total_unsecured_debts'] == Decimal('0.00')
        assert result['number_of_creditors'] == 2


@pytest.mark.django_db
class TestForm106SumIncomeExpenses:
    """Schedule I/J summary: income and expense calculations."""

    def test_income_from_six_month_average(self):
        """Monthly income is CMI (6-month average) from IncomeInfo."""
        user = User.objects.create_user(username='test_income', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        # 6-month income array: average = (3000+3200+3100+3000+3300+3400) / 6 = 3166.67
        IncomeInfo.objects.create(
            session=session,
            marital_status='single',
            number_of_dependents=0,
            monthly_income=[3000, 3200, 3100, 3000, 3300, 3400],
        )

        result = Form106SumGenerator(session).generate()

        expected_cmi = Decimal('3166.67')
        assert result['current_monthly_income'] == expected_cmi

    def test_expenses_from_expense_info(self):
        """Monthly expenses use ExpenseInfo.calculate_total_monthly_expenses()."""
        user = User.objects.create_user(username='test_expense', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        ExpenseInfo.objects.create(
            session=session,
            rent_or_mortgage=Decimal('1200.00'),
            utilities=Decimal('150.00'),
            food_and_groceries=Decimal('400.00'),
            vehicle_payment=Decimal('300.00'),
        )

        result = Form106SumGenerator(session).generate()

        assert result['current_monthly_expenses'] == Decimal('2050.00')

    def test_net_income_calculation(self):
        """Net income is income minus expenses."""
        user = User.objects.create_user(username='test_net', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        IncomeInfo.objects.create(
            session=session,
            marital_status='single',
            number_of_dependents=0,
            monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
        )
        ExpenseInfo.objects.create(
            session=session,
            rent_or_mortgage=Decimal('1200.00'),
            food_and_groceries=Decimal('400.00'),
        )

        result = Form106SumGenerator(session).generate()

        assert result['current_monthly_income'] == Decimal('3000.00')
        assert result['current_monthly_expenses'] == Decimal('1600.00')
        assert result['monthly_net_income'] == Decimal('1400.00')

    def test_missing_income_returns_zero(self):
        """Session without IncomeInfo defaults to zero income."""
        user = User.objects.create_user(username='test_no_inc', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        result = Form106SumGenerator(session).generate()

        assert result['current_monthly_income'] == Decimal('0.00')
        assert result['current_monthly_expenses'] == Decimal('0.00')
        assert result['monthly_net_income'] == Decimal('0.00')

    def test_negative_net_income(self):
        """Expenses exceeding income produce negative net income."""
        user = User.objects.create_user(username='test_neg_net', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        IncomeInfo.objects.create(
            session=session,
            marital_status='single',
            number_of_dependents=0,
            monthly_income=[1500, 1500, 1500, 1500, 1500, 1500],
        )
        ExpenseInfo.objects.create(
            session=session,
            rent_or_mortgage=Decimal('1200.00'),
            utilities=Decimal('200.00'),
            food_and_groceries=Decimal('400.00'),
        )

        result = Form106SumGenerator(session).generate()

        assert result['monthly_net_income'] == Decimal('-300.00')


@pytest.mark.django_db
class TestForm106SumComplete:
    """Integration: full summary with all data sources populated."""

    def test_complete_summary(self):
        """Full session produces accurate summary across all schedules."""
        user = User.objects.create_user(username='test_full', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        # Assets
        AssetInfo.objects.create(
            session=session,
            asset_type='vehicle',
            description='2020 Honda Civic',
            current_value=Decimal('12000.00'),
        )
        AssetInfo.objects.create(
            session=session,
            asset_type='bank_account',
            description='Chase Checking',
            current_value=Decimal('800.00'),
        )

        # Debts
        DebtInfo.objects.create(
            session=session,
            creditor_name='Auto Lender',
            debt_type='auto_loan',
            amount_owed=Decimal('8000.00'),
            is_secured=True,
        )
        DebtInfo.objects.create(
            session=session,
            creditor_name='Visa',
            debt_type='credit_card',
            amount_owed=Decimal('3000.00'),
            is_secured=False,
        )
        DebtInfo.objects.create(
            session=session,
            creditor_name='Medical Center',
            debt_type='medical',
            amount_owed=Decimal('2500.00'),
            is_secured=False,
        )

        # Income (6-month average = $4000)
        IncomeInfo.objects.create(
            session=session,
            marital_status='single',
            number_of_dependents=0,
            monthly_income=[4000, 4000, 4000, 4000, 4000, 4000],
        )

        # Expenses
        ExpenseInfo.objects.create(
            session=session,
            rent_or_mortgage=Decimal('1200.00'),
            utilities=Decimal('150.00'),
            food_and_groceries=Decimal('500.00'),
            vehicle_payment=Decimal('350.00'),
            vehicle_insurance=Decimal('100.00'),
            medical_expenses=Decimal('50.00'),
        )

        result = Form106SumGenerator(session).generate()

        assert result['total_assets'] == Decimal('12800.00')
        assert result['total_secured_debts'] == Decimal('8000.00')
        assert result['total_unsecured_debts'] == Decimal('5500.00')
        assert result['total_debts'] == Decimal('13500.00')
        assert result['current_monthly_income'] == Decimal('4000.00')
        assert result['current_monthly_expenses'] == Decimal('2350.00')
        assert result['monthly_net_income'] == Decimal('1650.00')
        assert result['number_of_creditors'] == 3
        assert result['number_of_assets'] == 2

    def test_preview_returns_same_as_generate(self):
        """Preview method returns identical data to generate."""
        user = User.objects.create_user(username='test_preview', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='bank_account',
            description='Savings',
            current_value=Decimal('1000.00'),
        )

        generator = Form106SumGenerator(session)
        assert generator.preview() == generator.generate()
