"""Tests for Schedule E/F (Creditors With Unsecured Claims) generator."""

import pytest
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import IntakeSession, DebtInfo
from apps.forms.services.schedule_ef_generator import ScheduleEFGenerator

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


def _create_debt(session: IntakeSession, **overrides) -> DebtInfo:
    """Create a DebtInfo with sensible defaults, overridable per-test."""
    defaults = {
        'session': session,
        'creditor_name': 'Test Creditor',
        'debt_type': 'credit_card',
        'amount_owed': Decimal('1000.00'),
        'is_secured': False,
        'is_priority': False,
        'consumer_business_classification': 'consumer',
        'is_contingent': False,
        'is_unliquidated': False,
        'is_disputed': False,
        'date_incurred': date(2023, 6, 15),
    }
    defaults.update(overrides)
    return DebtInfo.objects.create(**defaults)


@pytest.mark.django_db
class TestScheduleEFGenerator:
    """Schedule E/F unsecured claims generator tests."""

    def test_separates_priority_from_nonpriority(self):
        """Priority debts land in Part 1, nonpriority in Part 2."""
        user = User.objects.create_user(username='test_sep', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_debt(
            session,
            creditor_name='IRS',
            debt_type='other',
            amount_owed=Decimal('5000.00'),
            is_priority=True,
            consumer_business_classification='consumer',
        )
        _create_debt(
            session,
            creditor_name='Chase Visa',
            debt_type='credit_card',
            amount_owed=Decimal('3000.00'),
            is_priority=False,
            consumer_business_classification='consumer',
        )

        result = ScheduleEFGenerator(session).generate()

        assert len(result['priority_creditors']) == 1
        assert result['priority_creditors'][0]['creditor_name'] == 'IRS'
        assert result['total_priority_claims'] == Decimal('5000.00')

        assert len(result['nonpriority_creditors']) == 1
        assert result['nonpriority_creditors'][0]['creditor_name'] == 'Chase Visa'
        assert result['total_nonpriority_claims'] == Decimal('3000.00')

    def test_consumer_vs_business_percentage_calculation(self):
        """Consumer/business percentages reflect the 70/30 split scenario."""
        user = User.objects.create_user(username='test_pct', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        # 70% consumer: $7,000 across two debts
        _create_debt(
            session,
            creditor_name='Chase Visa',
            amount_owed=Decimal('4000.00'),
            consumer_business_classification='consumer',
        )
        _create_debt(
            session,
            creditor_name='Northwestern Hospital',
            debt_type='medical',
            amount_owed=Decimal('3000.00'),
            consumer_business_classification='consumer',
        )
        # 30% business: $3,000
        _create_debt(
            session,
            creditor_name='Office Depot',
            amount_owed=Decimal('3000.00'),
            consumer_business_classification='business',
        )

        result = ScheduleEFGenerator(session).generate()

        assert result['consumer_debt_total'] == Decimal('7000.00')
        assert result['business_debt_total'] == Decimal('3000.00')
        assert result['consumer_debt_percentage'] == Decimal('70.00')
        assert result['business_debt_percentage'] == Decimal('30.00')

    def test_total_unsecured_claims(self):
        """Total unsecured claims sums priority and nonpriority."""
        user = User.objects.create_user(username='test_total', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_debt(
            session,
            creditor_name='IRS',
            amount_owed=Decimal('2000.00'),
            is_priority=True,
        )
        _create_debt(
            session,
            creditor_name='Amex',
            amount_owed=Decimal('5000.00'),
        )
        _create_debt(
            session,
            creditor_name='Medical Center',
            debt_type='medical',
            amount_owed=Decimal('1500.00'),
        )

        result = ScheduleEFGenerator(session).generate()

        assert result['total_unsecured_claims'] == Decimal('8500.00')
        assert result['number_of_unsecured_claims'] == 3
        assert result['total_priority_claims'] == Decimal('2000.00')
        assert result['total_nonpriority_claims'] == Decimal('6500.00')

    def test_all_consumer_debts_100_percent(self):
        """When all debts are consumer, consumer percentage is 100%."""
        user = User.objects.create_user(username='test_100', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_debt(
            session,
            creditor_name='Discover',
            amount_owed=Decimal('2000.00'),
            consumer_business_classification='consumer',
        )
        _create_debt(
            session,
            creditor_name='Urgent Care',
            debt_type='medical',
            amount_owed=Decimal('800.00'),
            consumer_business_classification='consumer',
        )

        result = ScheduleEFGenerator(session).generate()

        assert result['consumer_debt_percentage'] == Decimal('100.00')
        assert result['business_debt_percentage'] == Decimal('0.00')
        assert result['consumer_debt_total'] == Decimal('2800.00')
        assert result['business_debt_total'] == Decimal('0.00')

    def test_no_unsecured_debts_returns_zeros(self):
        """Session with no unsecured debts returns empty lists and zero totals."""
        user = User.objects.create_user(username='test_none', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        # Only a secured debt -- should NOT appear
        _create_debt(
            session,
            creditor_name='Wells Fargo Mortgage',
            debt_type='mortgage',
            amount_owed=Decimal('150000.00'),
            is_secured=True,
        )

        result = ScheduleEFGenerator(session).generate()

        assert result['priority_creditors'] == []
        assert result['nonpriority_creditors'] == []
        assert result['total_priority_claims'] == Decimal('0.00')
        assert result['total_nonpriority_claims'] == Decimal('0.00')
        assert result['total_unsecured_claims'] == Decimal('0.00')
        assert result['number_of_unsecured_claims'] == 0
        assert result['consumer_debt_percentage'] == Decimal('0.00')
        assert result['business_debt_percentage'] == Decimal('0.00')

    def test_secured_debts_excluded(self):
        """Secured debts are filtered out -- only unsecured appear on E/F."""
        user = User.objects.create_user(username='test_excl', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_debt(
            session,
            creditor_name='Secured Bank',
            amount_owed=Decimal('20000.00'),
            is_secured=True,
        )
        _create_debt(
            session,
            creditor_name='Unsecured Card',
            amount_owed=Decimal('5000.00'),
            is_secured=False,
        )

        result = ScheduleEFGenerator(session).generate()

        assert result['number_of_unsecured_claims'] == 1
        assert result['total_unsecured_claims'] == Decimal('5000.00')

    def test_creditor_format_includes_all_fields(self):
        """Each creditor dict contains the full set of required fields."""
        user = User.objects.create_user(username='test_fmt', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_debt(
            session,
            creditor_name='Collection Agency',
            account_number='XXXX-1234',
            amount_owed=Decimal('2500.00'),
            is_contingent=True,
            is_unliquidated=False,
            is_disputed=True,
            date_incurred=date(2022, 3, 1),
            consumer_business_classification='business',
        )

        result = ScheduleEFGenerator(session).generate()
        creditor = result['nonpriority_creditors'][0]

        assert creditor['creditor_name'] == 'Collection Agency'
        assert creditor['account_number'] == 'XXXX-1234'
        assert creditor['amount_owed'] == Decimal('2500.00')
        assert creditor['date_incurred'] == '2022-03-01'
        assert creditor['debt_type'] == 'business'
        assert creditor['contingent'] is True
        assert creditor['unliquidated'] is False
        assert creditor['disputed'] is True

    def test_preview_returns_same_as_generate(self):
        """Preview method returns identical data to generate."""
        user = User.objects.create_user(username='test_prev', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_debt(session, creditor_name='Test Card', amount_owed=Decimal('1000.00'))

        generator = ScheduleEFGenerator(session)
        assert generator.preview() == generator.generate()

    def test_all_business_debts(self):
        """When all debts are business, means test does not apply."""
        user = User.objects.create_user(username='test_biz', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_debt(
            session,
            creditor_name='Staples',
            amount_owed=Decimal('4000.00'),
            consumer_business_classification='business',
        )
        _create_debt(
            session,
            creditor_name='Dell Financial',
            amount_owed=Decimal('6000.00'),
            consumer_business_classification='business',
        )

        result = ScheduleEFGenerator(session).generate()

        assert result['consumer_debt_percentage'] == Decimal('0.00')
        assert result['business_debt_percentage'] == Decimal('100.00')
        assert result['consumer_debt_total'] == Decimal('0.00')
        assert result['business_debt_total'] == Decimal('10000.00')
