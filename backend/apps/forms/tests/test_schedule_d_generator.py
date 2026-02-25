"""Tests for Schedule D (Creditors Who Hold Claims Secured by Property) generator."""

import pytest
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import IntakeSession, DebtInfo
from apps.forms.services.schedule_d_generator import ScheduleDGenerator

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


def _create_secured_debt(
    session: IntakeSession,
    *,
    creditor_name: str = 'First National Bank',
    debt_type: str = 'auto_loan',
    amount_owed: Decimal = Decimal('15000.00'),
    collateral_description: str = '2020 Honda Civic VIN: 1HGBH41JXMN109186',
    account_number: str = '****1234',
    is_contingent: bool = False,
    is_unliquidated: bool = False,
    is_disputed: bool = False,
    date_incurred: date | None = None,
) -> DebtInfo:
    """Create a secured debt with sensible defaults."""
    return DebtInfo.objects.create(
        session=session,
        creditor_name=creditor_name,
        debt_type=debt_type,
        priority_classification='secured',
        amount_owed=amount_owed,
        is_secured=True,
        collateral_description=collateral_description,
        account_number=account_number,
        is_contingent=is_contingent,
        is_unliquidated=is_unliquidated,
        is_disputed=is_disputed,
        date_incurred=date_incurred,
    )


def _create_unsecured_debt(
    session: IntakeSession,
    *,
    creditor_name: str = 'Capital One',
    amount_owed: Decimal = Decimal('5000.00'),
) -> DebtInfo:
    """Create an unsecured debt for exclusion tests."""
    return DebtInfo.objects.create(
        session=session,
        creditor_name=creditor_name,
        debt_type='credit_card',
        priority_classification='unsecured',
        amount_owed=amount_owed,
        is_secured=False,
    )


@pytest.mark.django_db
class TestScheduleDGenerator:
    """Schedule D secured creditor listing tests."""

    def test_only_secured_debts_appear(self):
        """Unsecured debts must be excluded from Schedule D."""
        user = User.objects.create_user(username='test_secured_only', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_secured_debt(session, creditor_name='Wells Fargo Home Mortgage')
        _create_unsecured_debt(session, creditor_name='Discover Card')
        _create_unsecured_debt(session, creditor_name='Medical Collections Inc')

        generator = ScheduleDGenerator(session)
        result = generator.generate()

        assert result['number_of_secured_claims'] == 1
        assert len(result['secured_creditors']) == 1
        assert result['secured_creditors'][0]['creditor_name'] == 'Wells Fargo Home Mortgage'

    def test_collateral_description_included(self):
        """Each secured entry must carry its collateral description."""
        user = User.objects.create_user(username='test_collateral', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_secured_debt(
            session,
            creditor_name='Chase Auto Finance',
            collateral_description='2022 Toyota Camry VIN: 4T1BF1FK5CU512345',
        )

        generator = ScheduleDGenerator(session)
        result = generator.generate()

        entry = result['secured_creditors'][0]
        assert entry['collateral_description'] == '2022 Toyota Camry VIN: 4T1BF1FK5CU512345'

    def test_total_secured_claims_calculation(self):
        """Total must equal the sum of all secured creditor amounts."""
        user = User.objects.create_user(username='test_total', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_secured_debt(
            session,
            creditor_name='Bank of America',
            amount_owed=Decimal('180000.00'),
            collateral_description='123 Main St, Chicago, IL 60601',
            debt_type='mortgage',
        )
        _create_secured_debt(
            session,
            creditor_name='Toyota Financial Services',
            amount_owed=Decimal('22000.00'),
            collateral_description='2021 Toyota RAV4',
        )

        generator = ScheduleDGenerator(session)
        result = generator.generate()

        assert result['total_secured_claims'] == Decimal('202000.00')
        assert result['number_of_secured_claims'] == 2

    def test_no_secured_debts_returns_empty(self):
        """Session with no secured debts produces empty results."""
        user = User.objects.create_user(username='test_empty', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_unsecured_debt(session)

        generator = ScheduleDGenerator(session)
        result = generator.generate()

        assert result['secured_creditors'] == []
        assert result['total_secured_claims'] == Decimal('0.00')
        assert result['number_of_secured_claims'] == 0

    def test_no_debts_at_all_returns_empty(self):
        """Session with zero debts produces empty results."""
        user = User.objects.create_user(username='test_no_debts', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        generator = ScheduleDGenerator(session)
        result = generator.generate()

        assert result['secured_creditors'] == []
        assert result['total_secured_claims'] == Decimal('0.00')
        assert result['number_of_secured_claims'] == 0

    def test_claim_status_flags_propagated(self):
        """Contingent, unliquidated, disputed flags must appear in output."""
        user = User.objects.create_user(username='test_flags', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_secured_debt(
            session,
            creditor_name='Judgment Lien Holder LLC',
            is_contingent=True,
            is_unliquidated=True,
            is_disputed=True,
        )

        generator = ScheduleDGenerator(session)
        result = generator.generate()

        entry = result['secured_creditors'][0]
        assert entry['contingent'] is True
        assert entry['unliquidated'] is True
        assert entry['disputed'] is True

    def test_date_incurred_formatted_as_iso(self):
        """date_incurred serializes to ISO format string."""
        user = User.objects.create_user(username='test_date', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_secured_debt(
            session,
            creditor_name='Home Lender Corp',
            date_incurred=date(2019, 6, 15),
        )

        generator = ScheduleDGenerator(session)
        result = generator.generate()

        assert result['secured_creditors'][0]['date_incurred'] == '2019-06-15'

    def test_date_incurred_empty_when_none(self):
        """Missing date_incurred produces empty string."""
        user = User.objects.create_user(username='test_no_date', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_secured_debt(session, date_incurred=None)

        generator = ScheduleDGenerator(session)
        result = generator.generate()

        assert result['secured_creditors'][0]['date_incurred'] == ''

    def test_ordered_alphabetically_by_creditor_name(self):
        """Secured creditors must appear in alphabetical order."""
        user = User.objects.create_user(username='test_order', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_secured_debt(session, creditor_name='Zephyr Bank')
        _create_secured_debt(session, creditor_name='Alpha Credit Union')
        _create_secured_debt(session, creditor_name='Midwest Mortgage Co')

        generator = ScheduleDGenerator(session)
        result = generator.generate()

        names = [c['creditor_name'] for c in result['secured_creditors']]
        assert names == ['Alpha Credit Union', 'Midwest Mortgage Co', 'Zephyr Bank']

    def test_preview_returns_same_as_generate(self):
        """Preview method returns identical data to generate."""
        user = User.objects.create_user(username='test_preview', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        _create_secured_debt(session)

        generator = ScheduleDGenerator(session)
        assert generator.preview() == generator.generate()
