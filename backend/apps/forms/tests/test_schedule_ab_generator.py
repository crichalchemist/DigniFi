import pytest
from decimal import Decimal
from apps.intake.models import IntakeSession, AssetInfo
from apps.forms.services.schedule_ab_generator import ScheduleABGenerator
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestScheduleABGenerator:
    def test_generates_schedule_ab_with_real_property(self):
        """Test generating Schedule A/B with real property."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        # Add real property
        AssetInfo.objects.create(
            session=session,
            asset_type='real_property',
            description='123 Main St, Chicago, IL 60601',
            current_value=Decimal('200000.00'),
            amount_owed=Decimal('150000.00')
        )

        generator = ScheduleABGenerator(session)
        result = generator.generate()

        assert result['total_real_property_value'] == Decimal('200000.00')
        assert result['total_personal_property_value'] == Decimal('0.00')
        assert result['total_value'] == Decimal('200000.00')

    def test_generates_schedule_ab_with_vehicle(self):
        """Test generating Schedule A/B with vehicle."""
        user = User.objects.create_user(username='test', password='test')
        session = IntakeSession.objects.create(user=user)

        # Add vehicle
        AssetInfo.objects.create(
            session=session,
            asset_type='vehicle',
            description='2020 Honda Civic',
            current_value=Decimal('15000.00'),
            amount_owed=Decimal('10000.00')
        )

        generator = ScheduleABGenerator(session)
        result = generator.generate()

        assert result['total_personal_property_value'] == Decimal('15000.00')
        assert len(result['vehicles']) == 1
        assert result['vehicles'][0]['description'] == '2020 Honda Civic'
        assert result['vehicles'][0]['equity'] == Decimal('5000.00')
