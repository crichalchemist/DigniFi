"""Tests for Schedule C (Property Claimed as Exempt) generator."""

import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.intake.models import IntakeSession, AssetInfo
from apps.forms.services.schedule_c_generator import ScheduleCGenerator

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


def _create_session(user: User, district: District) -> IntakeSession:
    return IntakeSession.objects.create(user=user, district=district)


@pytest.mark.django_db
class TestScheduleCGenerator:
    """Schedule C exemption application tests."""

    def test_applies_vehicle_exemption_equity_under_limit(self):
        """Vehicle with equity below $2,400 limit is fully exempt."""
        user = User.objects.create_user(username='test_veh', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='vehicle',
            description='2020 Honda Civic',
            current_value=Decimal('10000.00'),
            amount_owed=Decimal('8000.00'),
        )

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        assert len(result['exemptions']) == 1
        exemption = result['exemptions'][0]
        assert exemption['statute'] == '735 ILCS 5/12-1001(c)'
        assert exemption['amount_claimed'] == Decimal('2000.00')
        assert exemption['amount_available'] == Decimal('2400.00')
        assert exemption['equity'] == Decimal('2000.00')

    def test_applies_vehicle_exemption_equity_exceeds_limit(self):
        """Vehicle with equity above $2,400 claims max exemption."""
        user = User.objects.create_user(username='test_veh2', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='vehicle',
            description='2022 Toyota Camry',
            current_value=Decimal('20000.00'),
            amount_owed=Decimal('5000.00'),
        )

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        assert len(result['exemptions']) == 1
        exemption = result['exemptions'][0]
        assert exemption['statute'] == '735 ILCS 5/12-1001(c)'
        # Equity is $15,000, but exemption caps at $2,400
        assert exemption['amount_claimed'] == Decimal('2400.00')
        assert exemption['amount_available'] == Decimal('2400.00')

    def test_applies_wildcard_exemption(self):
        """Household goods use $4,000 wildcard exemption."""
        user = User.objects.create_user(username='test_wild', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='other',
            description='Furniture and appliances',
            current_value=Decimal('3000.00'),
        )

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        assert len(result['exemptions']) == 1
        exemption = result['exemptions'][0]
        assert exemption['statute'] == '735 ILCS 5/12-1001(b)'
        assert exemption['amount_claimed'] == Decimal('3000.00')
        assert exemption['amount_available'] == Decimal('4000.00')

    def test_applies_homestead_exemption(self):
        """Real property applies $15,000 homestead exemption."""
        user = User.objects.create_user(username='test_home', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='real_property',
            description='123 Main St, Chicago, IL 60601',
            current_value=Decimal('200000.00'),
            amount_owed=Decimal('180000.00'),
        )

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        assert len(result['exemptions']) == 1
        exemption = result['exemptions'][0]
        assert exemption['statute'] == '735 ILCS 5/12-901'
        assert exemption['amount_claimed'] == Decimal('15000.00')
        assert exemption['amount_available'] == Decimal('15000.00')

    def test_applies_retirement_exemption_unlimited(self):
        """Retirement accounts are 100% exempt (unlimited)."""
        user = User.objects.create_user(username='test_ret', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='retirement_account',
            description='Fidelity 401k',
            current_value=Decimal('50000.00'),
        )

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        assert len(result['exemptions']) == 1
        exemption = result['exemptions'][0]
        assert exemption['statute'] == '735 ILCS 5/12-1006'
        assert exemption['amount_claimed'] == Decimal('50000.00')
        assert exemption['is_fully_exempt'] is True

    def test_negative_equity_skipped(self):
        """Underwater assets (negative equity) produce no exemption."""
        user = User.objects.create_user(username='test_neg', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='real_property',
            description='456 Elm St, Chicago, IL 60602',
            current_value=Decimal('150000.00'),
            amount_owed=Decimal('175000.00'),
        )

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        assert len(result['exemptions']) == 0
        assert result['total_claimed'] == Decimal('0.00')

    def test_zero_equity_skipped(self):
        """Asset with zero equity produces no exemption."""
        user = User.objects.create_user(username='test_zero', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='vehicle',
            description='2019 Ford Focus',
            current_value=Decimal('8000.00'),
            amount_owed=Decimal('8000.00'),
        )

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        assert len(result['exemptions']) == 0

    def test_no_assets_returns_empty(self):
        """Session with no assets returns empty exemptions list."""
        user = User.objects.create_user(username='test_empty', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        assert result['exemptions'] == []
        assert result['total_claimed'] == Decimal('0.00')

    def test_multiple_assets_each_get_exemptions(self):
        """Multiple assets each receive their own exemption."""
        user = User.objects.create_user(username='test_multi', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='vehicle',
            description='2020 Honda Civic',
            current_value=Decimal('10000.00'),
            amount_owed=Decimal('8000.00'),
        )
        AssetInfo.objects.create(
            session=session,
            asset_type='real_property',
            description='123 Main St',
            current_value=Decimal('200000.00'),
            amount_owed=Decimal('190000.00'),
        )
        AssetInfo.objects.create(
            session=session,
            asset_type='bank_account',
            description='Chase Checking',
            current_value=Decimal('1500.00'),
        )

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        assert len(result['exemptions']) == 3
        statutes = {e['statute'] for e in result['exemptions']}
        assert '735 ILCS 5/12-1001(c)' in statutes  # vehicle
        assert '735 ILCS 5/12-901' in statutes        # homestead
        assert '735 ILCS 5/12-1001(b)' in statutes   # wildcard (bank)

        # Total claimed = $2,000 (vehicle) + $10,000 (home) + $1,500 (bank)
        assert result['total_claimed'] == Decimal('13500.00')

    def test_bank_account_uses_wildcard(self):
        """Bank accounts fall through to wildcard exemption."""
        user = User.objects.create_user(username='test_bank', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='bank_account',
            description='Wells Fargo Savings',
            current_value=Decimal('5000.00'),
        )

        generator = ScheduleCGenerator(session)
        result = generator.generate()

        assert len(result['exemptions']) == 1
        exemption = result['exemptions'][0]
        assert exemption['statute'] == '735 ILCS 5/12-1001(b)'
        # Capped at wildcard limit
        assert exemption['amount_claimed'] == Decimal('4000.00')

    def test_preview_returns_same_as_generate(self):
        """Preview method returns identical data to generate."""
        user = User.objects.create_user(username='test_preview', password='test')
        district = _create_ilnd_district()
        session = _create_session(user, district)

        AssetInfo.objects.create(
            session=session,
            asset_type='vehicle',
            description='2020 Honda Civic',
            current_value=Decimal('10000.00'),
            amount_owed=Decimal('8000.00'),
        )

        generator = ScheduleCGenerator(session)
        assert generator.preview() == generator.generate()
