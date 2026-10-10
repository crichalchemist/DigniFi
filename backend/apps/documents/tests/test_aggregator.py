import json
from decimal import Decimal
from unittest.mock import patch

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

    def test_captures_employer_name_from_most_recent_stub(self):
        """Employer name comes from the paystub with the latest pay_period_end."""
        user = get_user_model().objects.create_user("emptest", "emp@test.com", "pass")
        district = District.objects.create(
            name="ILND2", code="ILND2", state="IL", filing_fee_chapter_7=Decimal("338.00")
        )
        session = IntakeSession.objects.create(user=user, district=district)

        for i, (employer, start, end) in enumerate(
            [
                ("Old Job", "2026-01-01", "2026-01-15"),
                ("New Job", "2026-02-01", "2026-02-15"),
            ]
        ):
            doc = UploadedDocument.objects.create(
                session=session,
                uploaded_by=user,
                document_type=DocumentType.PAY_STUB,
                file=f"stub{i}.pdf",
                original_filename=f"stub{i}.pdf",
                file_size=100,
                mime_type="application/pdf",
            )
            OCRResult.objects.create(
                document=doc,
                status=OCRStatus.COMPLETED,
                extracted_data=json.dumps(
                    {
                        "employer_name": employer,
                        "gross_pay": "1000.00",
                        "pay_period_start": start,
                        "pay_period_end": end,
                        "confidence_score": 100,
                    }
                ),
                overall_confidence=Decimal("100"),
            )

        AggregateIngestionService.recalculate(session.id)

        agg = IngestedAggregate.objects.get(session=session, ingest_key="paystub.employer_name")
        self.assertEqual(agg.value, "New Job")

    def test_unusable_pay_stub_is_logged_without_its_pay_figures(self):
        """Pay figures are the filer's private data; the log names only what went wrong."""
        user = get_user_model().objects.create_user("logtest", "log@test.com", "pass")
        district = District.objects.create(
            name="ILND3", code="ILND3", state="IL", filing_fee_chapter_7=Decimal("338.00")
        )
        session = IntakeSession.objects.create(user=user, district=district)
        doc = UploadedDocument.objects.create(
            session=session,
            uploaded_by=user,
            document_type=DocumentType.PAY_STUB,
            file="stub.pdf",
            original_filename="stub.pdf",
            file_size=100,
            mime_type="application/pdf",
        )
        OCRResult.objects.create(
            document=doc,
            status=OCRStatus.COMPLETED,
            extracted_data=json.dumps(
                {
                    "employer_name": "Acme",
                    "gross_pay": "-4321.09",
                    "pay_period_start": "2026-01-01",
                    "pay_period_end": "2026-01-14",
                }
            ),
            overall_confidence=Decimal("0"),
        )

        with self.assertLogs("apps.documents.services.aggregator", level="WARNING") as logs:
            AggregateIngestionService.recalculate(session.id)

        output = "\n".join(logs.output)
        self.assertIn("ValidationError", output)
        self.assertNotIn("4321.09", output)

    def test_failed_recalculation_is_logged_by_error_type_never_its_message(self):
        """Logs reach Sentry; a database error's DETAIL can quote pay figures (DIG-105)."""
        user = get_user_model().objects.create_user("failtest", "fail@test.com", "pass")
        district = District.objects.create(
            name="ILND4", code="ILND4", state="IL", filing_fee_chapter_7=Decimal("338.00")
        )
        session = IntakeSession.objects.create(user=user, district=district)
        doc = UploadedDocument.objects.create(
            session=session,
            uploaded_by=user,
            document_type=DocumentType.PAY_STUB,
            file="stub.pdf",
            original_filename="stub.pdf",
            file_size=100,
            mime_type="application/pdf",
        )
        OCRResult.objects.create(
            document=doc,
            status=OCRStatus.COMPLETED,
            extracted_data="{}",
            overall_confidence=Decimal("0"),
        )
        leaked = "DETAIL: Failing row contains (paystub.gross, 4321.09)."

        # Sanctioned internal patch: the outer handler is the unit under test, and no stored
        # row makes the write fail deterministically on SQLite.
        with patch.object(
            AggregateIngestionService, "_calc_paystubs", side_effect=ValueError(leaked)
        ):
            with self.assertLogs("apps.documents.services.aggregator", level="WARNING") as logs:
                AggregateIngestionService.recalculate(session.id)

        output = "\n".join(logs.output)
        self.assertIn("ValueError", output)
        self.assertIn(str(session.id), output)
        self.assertNotIn("4321.09", output)
        self.assertTrue(all(record.exc_info is None for record in logs.records))
