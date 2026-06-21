from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.documents.models import DocumentType, OCRResult, OCRStatus, UploadedDocument
from apps.documents.views import _run_processing
from apps.intake.models import IntakeSession


class TestAggregatorHooks(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("testuser", "test@test.com", "pass")
        self.district = District.objects.create(
            name="Test District", state="IL", filing_fee_chapter_7=0.00
        )
        self.session = IntakeSession.objects.create(user=self.user, district=self.district)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        file_content = b"fake pdf content"
        test_file = SimpleUploadedFile("test.pdf", file_content, content_type="application/pdf")

        self.doc = UploadedDocument.objects.create(
            session=self.session,
            uploaded_by=self.user,
            document_type=DocumentType.PAY_STUB,
            file=test_file,
            original_filename="test.pdf",
            file_size=100,
            mime_type="application/pdf",
        )
        self.ocr = OCRResult.objects.create(
            document=self.doc,
            status=OCRStatus.PENDING,
            extracted_data="{}",
            overall_confidence=0,
            confidence_scores={},
        )

    @patch("apps.documents.views._get_processor")
    @patch("apps.documents.views.AggregateIngestionService.recalculate")
    def test_run_processing_hook(self, mock_recalc, mock_get_processor):
        mock_get_processor.return_value.process.return_value.error = None
        mock_get_processor.return_value.process.return_value.fields = {}
        mock_get_processor.return_value.process.return_value.confidence = {}

        _run_processing(self.doc.id)
        mock_recalc.assert_called_once_with(self.session.id)

    @patch("apps.documents.views.AggregateIngestionService.recalculate")
    def test_validate_hook(self, mock_recalc):
        url = reverse("documents:validate", args=[self.doc.id])
        resp = self.client.post(url, {"fields": {"gross_pay": "2000.00"}}, format="json")
        self.assertEqual(resp.status_code, 200)
        mock_recalc.assert_called_once_with(self.session.id)
