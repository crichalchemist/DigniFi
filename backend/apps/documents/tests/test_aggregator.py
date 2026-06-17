import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.districts.models import District
from apps.documents.models import (
    DocumentType,
    IngestedAggregate,
    OCRResult,
    OCRStatus,
    UploadedDocument,
)
from apps.documents.services.aggregator import AggregateIngestionService
from apps.intake.models import IntakeSession


class TestAggregateIngestionService(TestCase):
    def test_recalculate_paystub_gross(self):
        user = get_user_model().objects.create_user("testuser", "test@test.com", "pass")
        district = District.objects.create(
            name="ILND", code="ILND", state="IL", filing_fee_chapter_7=Decimal("338.00")
        )
        session = IntakeSession.objects.create(user=user, district=district)

        doc = UploadedDocument.objects.create(
            session=session,
            uploaded_by=user,
            document_type=DocumentType.PAY_STUB,
            file="test.pdf",
            original_filename="test.pdf",
            file_size=100,
            mime_type="application/pdf",
        )

        OCRResult.objects.create(
            document=doc,
            status=OCRStatus.COMPLETED,
            overall_confidence=Decimal("100"),
            extracted_data=json.dumps(
                {
                    "employer_name": "Acme",
                    "gross_pay": "1000.00",
                    "pay_period_start": "2026-01-01",
                    "pay_period_end": "2026-01-14",  # 14 days
                    "confidence_score": 100,
                }
            ),
        )

        AggregateIngestionService.recalculate(session.id)

        agg = IngestedAggregate.objects.get(session=session, ingest_key="paystub.gross")
        # 1000 / 14 * 30.416666 = 2172.619 -> 2172.62
        self.assertEqual(agg.value, "2172.62")
