import json
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.documents.models import DocumentType, OCRResult, OCRStatus, UploadedDocument
from apps.intake.models import IntakeSession
from apps.users.models import User


@pytest.fixture
def district(db):
    return District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=338.00,
    )


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user(username="doctest", password="pass")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def session(db, auth_client, district):
    _, user = auth_client
    return IntakeSession.objects.create(user=user, district=district)


def test_upload_returns_202(db, auth_client, session):
    client, _ = auth_client
    pdf = SimpleUploadedFile("bill.pdf", b"%PDF-1.4 fake", content_type="application/pdf")

    with patch("apps.documents.views.ThreadPoolExecutor") as mock_pool:
        mock_pool.return_value.__enter__.return_value.submit = MagicMock()
        response = client.post(
            "/api/documents/upload/",
            {
                "file": pdf,
                "document_type": DocumentType.CREDITOR_BILL,
                "session_id": session.id,
            },
            format="multipart",
        )

    assert response.status_code == 202
    data = response.json()
    assert "id" in data
    assert data["status"] == "processing"


def test_list_scoped_to_session(db, auth_client, session):
    client, user = auth_client
    UploadedDocument.objects.create(
        session=session,
        uploaded_by=user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename="bill.pdf",
        file_size=100,
        mime_type="application/pdf",
        file="documents/x.pdf",
    )
    response = client.get(f"/api/documents/?session_id={session.id}")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_document_returns_ocr_result(db, auth_client, session):
    client, user = auth_client
    doc = UploadedDocument.objects.create(
        session=session,
        uploaded_by=user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename="bill.pdf",
        file_size=100,
        mime_type="application/pdf",
        file="documents/x.pdf",
    )
    OCRResult.objects.create(
        document=doc,
        status=OCRStatus.COMPLETED,
        extracted_data='{"creditor_name": "Chase"}',
        confidence_scores={"overall": 85},
        overall_confidence=85,
    )
    response = client.get(f"/api/documents/{doc.id}/")
    assert response.status_code == 200
    data = response.json()
    assert data["ocr_result"]["status"] == "completed"


def test_validate_updates_ocr_result(db, auth_client, session):
    client, user = auth_client
    doc = UploadedDocument.objects.create(
        session=session,
        uploaded_by=user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename="bill.pdf",
        file_size=100,
        mime_type="application/pdf",
        file="documents/x.pdf",
    )
    ocr = OCRResult.objects.create(
        document=doc,
        status=OCRStatus.COMPLETED,
        extracted_data='{"creditor_name": "Chase"}',
        confidence_scores={},
        overall_confidence=80,
    )
    response = client.post(
        f"/api/documents/{doc.id}/validate/",
        {"fields": {"creditor_name": "Chase Bank NA"}},
        format="json",
    )
    assert response.status_code == 200
    ocr.refresh_from_db()
    assert ocr.user_validated is True
    assert json.loads(ocr.extracted_data)["creditor_name"] == "Chase Bank NA"
