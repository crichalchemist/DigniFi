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
import os
import subprocess
from unittest.mock import patch

import fitz  # pymupdf
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.documents.models import DocumentType, OCRResult, OCRStatus
from apps.documents.tests.builders import (
    chat_completion,
    pdf_with_no_pages,
    scanned_pdf,
    text_pdf,
)
from apps.intake.models import IntakeSession
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
