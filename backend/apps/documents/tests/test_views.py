import json
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.documents.models import DocumentType, OCRResult, OCRStatus, UploadedDocument
from apps.intake.models import DebtInfo, IntakeSession
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


def _scanned_bill_with_draft(session, user):
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
    draft = DebtInfo.objects.create(
        session=session,
        creditor_name="Chase",
        debt_type="credit_card",
        amount_owed=Decimal("500.00"),
        is_draft=True,
        source_document=doc,
    )
    return doc, ocr, draft


@pytest.mark.parametrize("bad_amount", ["99999999999.99", "not a number"])
def test_a_correction_too_large_or_unreadable_is_refused_and_the_session_still_opens(
    db, auth_client, session, bad_amount
):
    """A stored amount wider than DecimalField(12, 2) would 500 every read of the
    session once amounts are readable (DIG-2), so validate refuses it before writing."""
    client, user = auth_client
    doc, ocr, draft = _scanned_bill_with_draft(session, user)

    response = client.post(
        f"/api/documents/{doc.id}/validate/",
        {"fields": {"amount_owed": bad_amount}},
        format="json",
    )

    assert response.status_code == 400
    assert "amount_owed" in response.json()
    draft.refresh_from_db()
    assert draft.amount_owed == Decimal("500.00")
    ocr.refresh_from_db()
    assert ocr.user_validated is False
    assert client.get(f"/api/intake/sessions/{session.id}/").status_code == 200


def test_a_negative_scanned_bill_correction_is_refused(db, auth_client, session):
    client, user = auth_client
    doc, _, draft = _scanned_bill_with_draft(session, user)

    response = client.post(
        f"/api/documents/{doc.id}/validate/",
        {"fields": {"amount_owed": "-5"}},
        format="json",
    )

    assert response.status_code == 400
    draft.refresh_from_db()
    assert draft.amount_owed == Decimal("500.00")


def test_a_corrected_amount_reaches_the_draft_debt(db, auth_client, session):
    client, user = auth_client
    doc, _, draft = _scanned_bill_with_draft(session, user)

    response = client.post(
        f"/api/documents/{doc.id}/validate/",
        {"fields": {"amount_owed": "650.00"}},
        format="json",
    )

    assert response.status_code == 200
    draft.refresh_from_db()
    assert draft.amount_owed == Decimal("650.00")


@pytest.mark.parametrize(
    "document_type,fields",
    [
        (DocumentType.CREDITOR_BILL, {"amount_owed": "650.00"}),
        (DocumentType.PAY_STUB, {"gross_pay": "1100.00"}),
    ],
    ids=["bill", "pay-stub"],
)
def test_correcting_a_scanned_bill_or_pay_stub_reopens_a_completed_intake(
    db, auth_client, session, document_type, fields
):
    # A bill's draft debt and a pay stub's figures are intake data (spec §5.3).
    client, user = auth_client
    doc = UploadedDocument.objects.create(
        session=session,
        uploaded_by=user,
        document_type=document_type,
        user_declared_type=document_type,
        original_filename="scan.pdf",
        file_size=100,
        mime_type="application/pdf",
        file="documents/x.pdf",
    )
    OCRResult.objects.create(
        document=doc,
        status=OCRStatus.COMPLETED,
        extracted_data="{}",
        confidence_scores={},
        overall_confidence=80,
    )
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")

    response = client.post(f"/api/documents/{doc.id}/validate/", {"fields": fields}, format="json")

    assert response.status_code == 200
    session.refresh_from_db()
    assert session.status == "in_progress"


def _raw_creditor_name(debt_id):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT creditor_name FROM debt_info WHERE id = %s", [debt_id])
        return cursor.fetchone()[0]


def test_a_corrected_creditor_name_is_stored_encrypted(db, auth_client, session):
    client, user = auth_client
    doc, _, draft = _scanned_bill_with_draft(session, user)

    response = client.post(
        f"/api/documents/{doc.id}/validate/",
        {"fields": {"creditor_name": "Lakeshore Medical Billing"}},
        format="json",
    )

    assert response.status_code == 200
    raw = _raw_creditor_name(draft.pk)
    assert raw.startswith("gAAAAA")
    assert "Lakeshore" not in raw
    draft.refresh_from_db()
    assert draft.creditor_name == "Lakeshore Medical Billing"


@pytest.mark.parametrize("bad_name", ["N" * 256, "", None])
def test_a_corrected_creditor_name_too_long_blank_or_missing_is_refused(
    db, auth_client, session, bad_name
):
    client, user = auth_client
    doc, ocr, draft = _scanned_bill_with_draft(session, user)

    response = client.post(
        f"/api/documents/{doc.id}/validate/",
        {"fields": {"creditor_name": bad_name}},
        format="json",
    )

    assert response.status_code == 400
    assert "creditor_name" in response.json()
    draft.refresh_from_db()
    assert draft.creditor_name == "Chase"
    ocr.refresh_from_db()
    assert ocr.user_validated is False


def test_a_corrected_creditor_name_of_exactly_255_letters_is_kept(db, auth_client, session):
    client, user = auth_client
    doc, _, draft = _scanned_bill_with_draft(session, user)

    response = client.post(
        f"/api/documents/{doc.id}/validate/",
        {"fields": {"creditor_name": "N" * 255}},
        format="json",
    )

    assert response.status_code == 200
    draft.refresh_from_db()
    assert len(draft.creditor_name) == 255
