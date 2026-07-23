"""Regression test for BIZ-58: OCR extracted_data must be encrypted at rest.

Business intent: parsed PII (SSNs, account numbers) extracted from uploaded
documents must not sit in plaintext in the database — matching the field-level
encryption the intake models already enforce.
"""

import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase

from apps.districts.models import District
from apps.documents.models import DocumentType, OCRResult, UploadedDocument
from apps.intake.models import IntakeSession


class TestOCRResultEncryption(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("enctest", "e@t.com", "pw")
        district = District.objects.create(
            code="ILND",
            name="Illinois Northern",
            state="IL",
            court_name="U.S. Bankruptcy Court ILND",
            filing_fee_chapter_7=338.00,
        )
        session = IntakeSession.objects.create(user=user, district=district)
        self.doc = UploadedDocument.objects.create(
            session=session,
            uploaded_by=user,
            document_type=DocumentType.CREDITOR_BILL,
            user_declared_type=DocumentType.CREDITOR_BILL,
            original_filename="bill.pdf",
            file_size=13,
            mime_type="application/pdf",
            file=SimpleUploadedFile("bill.pdf", b"%PDF-1.4 test"),
        )

    def test_extracted_data_is_encrypted_at_rest(self):
        ssn = "123-45-6789"
        ocr = OCRResult.objects.create(
            document=self.doc,
            extracted_data=json.dumps({"ssn": ssn}),
            overall_confidence=0,
        )

        table = OCRResult._meta.db_table
        with connection.cursor() as cur:
            cur.execute(f"SELECT extracted_data FROM {table} WHERE id = %s", [ocr.id])
            raw = cur.fetchone()[0]

        # The raw column must be ciphertext — neither the SSN nor the key appears.
        self.assertNotIn(ssn, raw)
        self.assertNotIn("ssn", raw)

        # And it must round-trip transparently through the ORM.
        ocr.refresh_from_db()
        self.assertEqual(json.loads(ocr.extracted_data)["ssn"], ssn)
