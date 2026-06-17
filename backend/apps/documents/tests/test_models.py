from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.districts.models import District
from apps.documents.models import IngestedAggregate
from apps.intake.models import IntakeSession


class TestIngestedAggregate(TestCase):
    def test_unique_constraint(self):
        user = get_user_model().objects.create_user("testuser", "test@test.com", "pass")
        district = District.objects.create(
            code="test",
            name="Test District",
            state="IL",
            court_name="Test Court",
            pro_se_efiling_allowed=True,
            filing_fee_chapter_7=338.00,
        )
        session = IntakeSession.objects.create(user=user, district=district)
        IngestedAggregate.objects.create(session=session, ingest_key="paystub.gross", value="100")
        with self.assertRaises(IntegrityError):
            IngestedAggregate.objects.create(
                session=session, ingest_key="paystub.gross", value="200"
            )
