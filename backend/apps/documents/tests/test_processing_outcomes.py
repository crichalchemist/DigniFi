"""What a filer's upload turns into, end to end.

Each test posts a file to the real upload endpoint and lets the real view, processor
and OpenAIProvider run. Two boundaries are replaced:

- the OpenAI client (``openai_provider.OpenAI``), and
- the opendataloader JVM, by ``_TextLayerJVM`` below. The real-JVM contract tests in
  test_processor.py check that it behaves like the real CLI.

The upload view runs processing on a worker thread, which cannot see rows inside a
test transaction, so these tests use ``transactional_db``. A test that calls
``views._run_processing(doc.id)`` directly can use plain ``db``.
"""

import base64
import json
import os
import subprocess
from decimal import Decimal
from unittest.mock import patch

import fitz  # pymupdf
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.documents.models import DocumentType, IngestedAggregate, OCRResult, OCRStatus
from apps.documents.tests.builders import (
    chat_completion,
    pdf_with_no_pages,
    scanned_pdf,
    text_pdf,
)
from apps.intake.models import DebtInfo, IntakeSession
from apps.users.models import User

BILL_REPLY = (
    '{"creditor_name": "Lakeshore Medical Billing", "account_number": "4417-2290", '
    '"amount_owed": "1284.50", "minimum_payment": null, "due_date": null, '
    '"creditor_type": "medical", "confidence_score": 88}'
)


class _TextLayerJVM:
    """Stands in for the ``opendataloader_pdf`` module and behaves like the real CLI:

    - It has no hybrid server to reach (none runs on Heroku), so any ``hybrid`` option
      exits 1.
    - It writes each page's text layer as markdown.
    - An image-only page becomes an image placeholder, unless ``image_output="off"``.
    """

    @staticmethod
    def convert(input_path, output_dir, **options):
        if options.get("hybrid"):
            raise subprocess.CalledProcessError(1, "opendataloader-pdf")
        blocks = []
        with fitz.open(input_path[0]) as doc:
            for number, page in enumerate(doc, start=1):
                text = page.get_text().strip()
                if text:
                    blocks.append(text)
                elif options.get("image_output") != "off":
                    blocks.append(f"![image {number}](<document_images/imageFile{number}.png>)")
        with open(os.path.join(output_dir, "document.md"), "w") as f:
            f.write("\n\n".join(blocks))


@pytest.fixture(autouse=True)
def text_layer_jvm():
    with patch("apps.documents.services.processor.opendataloader_pdf", _TextLayerJVM):
        yield


@pytest.fixture
def openai_client(settings, tmp_path):
    """The mocked OpenAI client. Every completion answers BILL_REPLY unless a test
    sets ``chat.completions.create.return_value`` or ``side_effect``."""
    settings.MEDIA_ROOT = tmp_path
    settings.OCR_PROVIDER = "openai"
    settings.OCR_MODEL = ""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        with patch("apps.documents.services.providers.openai_provider.OpenAI") as openai_cls:
            client = openai_cls.return_value
            client.chat.completions.create.return_value = chat_completion(BILL_REPLY)
            yield client


@pytest.fixture
def filer(transactional_db):
    """An authenticated API client and that filer's intake session."""
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=338.00,
    )
    user = User.objects.create_user(username="uploader", password="pass")
    session = IntakeSession.objects.create(user=user, district=district)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session


def upload(filer, data: bytes, filename: str, mime_type: str, document_type: str) -> OCRResult:
    """Post one file the way the upload page does. Processing has finished by the time
    the 202 returns, so the OCRResult is final."""
    client, session = filer
    response = client.post(
        "/api/documents/upload/",
        {
            "file": SimpleUploadedFile(filename, data, content_type=mime_type),
            "document_type": document_type,
            "session_id": session.id,
        },
        format="multipart",
    )
    assert response.status_code == 202
    return OCRResult.objects.get(document_id=response.json()["id"])


def sent_parts(openai_client, call: int = -1) -> list[dict]:
    """The user-message content parts of one completion request (the last by default)."""
    request = openai_client.chat.completions.create.call_args_list[call]
    return request.kwargs["messages"][0]["content"]


def _aspect_ratio(data_url: str) -> float:
    picture = fitz.Pixmap(base64.b64decode(data_url.removeprefix("data:image/jpeg;base64,")))
    return picture.width / picture.height


def test_balance_on_page_two_of_a_text_pdf_reaches_the_model(filer, openai_client):
    pdf = text_pdf(
        [
            "Lakeshore Medical Billing\nPatient statement for services in August.",
            "Account 4417-2290\nBalance due: $1,284.50",
        ]
    )

    ocr = upload(filer, pdf, "bill.pdf", "application/pdf", DocumentType.CREDITOR_BILL)

    parts = sent_parts(openai_client)
    assert [part["type"] for part in parts] == ["text"]
    assert "Balance due: $1,284.50" in parts[0]["text"]
    assert ocr.status == OCRStatus.COMPLETED


def test_a_scanned_pdf_sends_at_most_three_page_images_in_order(filer, openai_client):
    # Four image-only pages, each a different shape, so the images that reach the model
    # show which pages they are.
    pdf = scanned_pdf([(200, 300), (300, 300), (400, 300), (500, 300)])

    upload(filer, pdf, "scan.pdf", "application/pdf", DocumentType.CREDITOR_BILL)

    assert openai_client.chat.completions.create.call_count == 1
    parts = sent_parts(openai_client)
    assert [part["type"] for part in parts] == ["image_url", "image_url", "image_url", "text"]
    shapes = [_aspect_ratio(part["image_url"]["url"]) for part in parts[:3]]
    assert shapes == pytest.approx([200 / 300, 300 / 300, 400 / 300], abs=0.01)


def test_a_pdf_with_no_pages_fails_instead_of_completing_empty(filer, openai_client):
    ocr = upload(
        filer, pdf_with_no_pages(), "empty.pdf", "application/pdf", DocumentType.CREDITOR_BILL
    )

    assert ocr.status == OCRStatus.FAILED
    openai_client.chat.completions.create.assert_not_called()


def test_an_empty_reply_is_retried_once_and_its_cause_is_recorded(filer, openai_client):
    openai_client.chat.completions.create.return_value = chat_completion(
        " \n", finish_reason="length"
    )

    ocr = upload(filer, b"\xff\xd8\xff", "bill.jpg", "image/jpeg", DocumentType.CREDITOR_BILL)

    assert openai_client.chat.completions.create.call_count == 2
    assert ocr.status == OCRStatus.FAILED
    assert "finish_reason=length" in ocr.error_message
    assert "refusal=absent" in ocr.error_message


# What a scan found, as the filer sees it on the upload page (spec 2026-10-09 §4.7).


def scan_photo(filer, openai_client, document_type, reply=None, error=None) -> dict:
    """Upload a photo of a document, let the model answer ``reply`` (or raise ``error``),
    and return the document as the upload page reads it. A photo never starts the JVM."""
    create = openai_client.chat.completions.create
    if error is not None:
        create.side_effect = error
    else:
        create.return_value = chat_completion(json.dumps(reply))
    ocr = upload(filer, b"\xff\xd8\xff", "scan.jpg", "image/jpeg", document_type)
    client, _ = filer
    response = client.get(f"/api/documents/{ocr.document_id}/")
    assert response.status_code == 200
    return response.json()


def test_cover_page_with_no_account_details_is_reported_as_nothing_found(filer, openai_client):
    _, session = filer
    cover_page = {
        "creditor_name": None,
        "account_number": None,
        "amount_owed": None,
        "minimum_payment": None,
        "due_date": None,
        "creditor_type": None,
        "confidence_score": None,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, reply=cover_page)

    assert doc["ocr_result"]["status"] == "failed"
    assert doc["ocr_result"]["failure_reason"] == "nothing_found"
    assert not DebtInfo.objects.filter(session=session).exists()


@pytest.mark.parametrize("creditor_name", [None, "", "   "])
def test_bill_without_a_creditor_creates_no_debt_and_does_not_crash(
    filer, openai_client, creditor_name
):
    _, session = filer
    bill = {
        "creditor_name": creditor_name,
        "amount_owed": "125.00",
        "creditor_type": "medical",
        "confidence_score": 40,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, reply=bill)

    # A crash would surface as processing_error; an unnamed creditor is "nothing found".
    assert doc["ocr_result"]["status"] == "failed"
    assert doc["ocr_result"]["failure_reason"] == "nothing_found"
    assert not DebtInfo.objects.filter(session=session).exists()


def test_bill_with_a_creditor_but_unreadable_balance_becomes_a_draft_to_complete(
    filer, openai_client
):
    _, session = filer
    bill = {
        "creditor_name": "Lakeshore Medical Group",
        "account_number": "88213",
        "amount_owed": None,
        "creditor_type": "medical",
        "confidence_score": 55,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, reply=bill)

    assert doc["ocr_result"]["status"] == "completed"
    assert doc["ocr_result"]["failure_reason"] == ""
    draft = DebtInfo.objects.get(session=session)
    assert draft.is_draft is True
    assert draft.creditor_name == "Lakeshore Medical Group"
    assert draft.amount_owed == Decimal("0")
    assert draft.source_document_id == doc["id"]


def test_pay_stub_upload_produces_monthly_income_for_schedule_i(filer, openai_client):
    _, session = filer
    pay_stub = {
        "employer_name": "Acme Logistics",
        "gross_pay": "1000.00",
        "pay_period_start": "2026-01-01",
        "pay_period_end": "2026-01-14",
        "ytd_gross": None,
        "net_pay": "812.40",
        "deductions_total": "187.60",
        "confidence_score": 92,
    }

    doc = scan_photo(filer, openai_client, DocumentType.PAY_STUB, reply=pay_stub)

    assert doc["ocr_result"]["status"] == "completed"
    # Schedule I reads ingest_key "paystub.gross": 1000 / 14 days * 30.41667 = 2172.62.
    gross = IngestedAggregate.objects.get(session=session, ingest_key="paystub.gross")
    assert gross.value == "2172.62"
    assert not DebtInfo.objects.filter(session=session).exists()


@pytest.mark.parametrize(
    "tradelines",
    [[], None, [{"creditor_name": "", "amount_owed": None}]],
    ids=["empty-list", "null", "only-unreadable-lines"],
)
def test_credit_report_with_no_readable_accounts_is_reported_as_nothing_found(
    filer, openai_client, tradelines
):
    _, session = filer
    doc = scan_photo(
        filer,
        openai_client,
        DocumentType.CREDIT_REPORT,
        reply={"tradelines": tradelines, "confidence_score": 20},
    )

    assert doc["ocr_result"]["status"] == "failed"
    assert doc["ocr_result"]["failure_reason"] == "nothing_found"
    assert not DebtInfo.objects.filter(session=session).exists()


def test_one_bad_account_line_keeps_the_rest_of_the_report(filer, openai_client):
    _, session = filer
    report = {
        "tradelines": [
            {
                "creditor_name": " Chase Card Services ",
                "account_number": 41110000,
                "amount_owed": 2450.75,
                "account_type": "credit_card",
                "account_status": "open",
                "credit_limit": 5000,
            },
            {"creditor_name": "   ", "amount_owed": "300.00"},
            {"creditor_name": "Unreadable Bank", "amount_owed": "illegible"},
            {"creditor_name": "Midwest Auto Finance", "amount_owed": "12000.00"},
        ],
        "confidence_score": 70,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDIT_REPORT, reply=report)

    assert doc["ocr_result"]["status"] == "completed"
    debts = {d.creditor_name: d for d in DebtInfo.objects.filter(session=session)}
    assert set(debts) == {"Chase Card Services", "Midwest Auto Finance"}
    assert debts["Chase Card Services"].amount_owed == Decimal("2450.75")
    assert debts["Chase Card Services"].account_number == "41110000"
    assert debts["Midwest Auto Finance"].amount_owed == Decimal("12000.00")
    assert all(d.is_draft for d in debts.values())


@pytest.mark.parametrize("credit_limit", ["N/A", "$5,000", "", "-", "NaN", True])
def test_loan_whose_credit_limit_is_not_a_number_still_becomes_a_draft_debt(
    filer, openai_client, credit_limit
):
    # A loan has no credit limit, so reports print "N/A" there; nothing reads the limit.
    _, session = filer
    report = {
        "tradelines": [
            {
                "creditor_name": "Midwest Auto Finance",
                "amount_owed": "12000.00",
                "account_type": "auto_loan",
                "account_status": "open",
                "credit_limit": credit_limit,
            }
        ],
        "confidence_score": 75,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDIT_REPORT, reply=report)

    assert doc["ocr_result"]["status"] == "completed"
    assert doc["ocr_result"]["failure_reason"] == ""
    debt = DebtInfo.objects.get(session=session)
    assert debt.creditor_name == "Midwest Auto Finance"
    assert debt.amount_owed == Decimal("12000.00")
    assert debt.is_draft is True
    assert debt.is_secured is True


def test_report_showing_only_paid_off_accounts_is_done_with_no_new_debts(filer, openai_client):
    _, session = filer
    report = {
        "tradelines": [
            {
                "creditor_name": "Discover",
                "amount_owed": "0",
                "account_type": "credit_card",
                "account_status": "closed",
            },
            {
                "creditor_name": "Navient",
                "amount_owed": 0,
                "account_type": "student_loan",
                "account_status": "closed",
            },
        ],
        "confidence_score": 85,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDIT_REPORT, reply=report)

    assert doc["ocr_result"]["status"] == "completed"
    assert doc["ocr_result"]["failure_reason"] == ""
    assert not DebtInfo.objects.filter(session=session).exists()


def test_reading_failure_shows_the_filer_a_reason_code_never_provider_text(filer, openai_client):
    provider_error = RuntimeError(
        "Error code: 403 - {'error': {'message': "
        "'Project proj_8sK2 does not have access to model gpt-4o'}}"
    )

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, error=provider_error)

    assert doc["ocr_result"] == {
        "status": "failed",
        "failure_reason": "processing_error",
        "confidence_scores": {},
        "overall_confidence": 0.0,
        "user_validated": False,
    }
    assert "proj_8sK2" not in json.dumps(doc)
    # error_message is for operations and keeps only the exception's class (spec §4.7).
    assert OCRResult.objects.get(document_id=doc["id"]).error_message == "RuntimeError"


def test_a_crash_while_saving_what_was_read_is_reported_as_a_processing_error(filer, openai_client):
    # Sanctioned internal patch: no OpenAI reply reaches _run_processing's outer handler
    # deterministically (an overflow reply can reach it on Postgres, DIG-106).
    with patch(
        "apps.documents.views._record_findings", side_effect=RuntimeError("synthetic")
    ) as record_findings:
        ocr = upload(filer, b"\xff\xd8\xff", "bill.jpg", "image/jpeg", DocumentType.CREDITOR_BILL)

    # The read itself succeeded (BILL_REPLY); the failure came while recording it.
    record_findings.assert_called_once()
    client, _ = filer
    doc = client.get(f"/api/documents/{ocr.document_id}/").json()
    assert doc["ocr_result"]["status"] == "failed"
    assert doc["ocr_result"]["failure_reason"] == "processing_error"
    assert ocr.error_message == "RuntimeError"


def test_document_api_never_returns_what_was_read_from_the_file(filer, openai_client):
    bill = {
        "creditor_name": "Lakeshore Medical Group",
        "account_number": "5521-0098-7713",
        "amount_owed": "410.00",
        "creditor_type": "medical",
        "confidence_score": 90,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, reply=bill)

    assert doc["ocr_result"]["status"] == "completed"
    assert "extracted_data" not in doc["ocr_result"]
    assert "5521-0098-7713" not in json.dumps(doc)


def test_scan_records_the_provider_that_read_it(filer, openai_client):
    bill = {"creditor_name": "ComEd", "amount_owed": "96.12", "creditor_type": "utility"}

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, reply=bill)

    assert OCRResult.objects.get(document_id=doc["id"]).ocr_provider == "openai"
