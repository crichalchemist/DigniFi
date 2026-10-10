"""Which hosted model reads a filer's upload is a config var, not a deploy.

These tests drive a real upload through ``_run_processing`` and patch only the SDK client
classes (the network boundary), so they prove which provider and model actually receive
the document.
"""

import importlib
import json
import os
from unittest.mock import MagicMock, patch

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.districts.models import District
from apps.documents.models import DocumentType, OCRResult, OCRStatus, UploadedDocument
from apps.documents.views import _get_processor, _run_processing
from apps.intake.models import IntakeSession
from apps.users.models import User

FAKE_JPEG = b"\xff\xd8\xff\xe0fake-jpeg"
CANNED_BILL = json.dumps(
    {"creditor_name": "Chase Bank", "amount_owed": 1250.0, "confidence_score": 90}
)


@pytest.fixture
def uploaded_bill(db, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user = User.objects.create_user(username="providerfiler", password="pass")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=338.00,
    )
    session = IntakeSession.objects.create(user=user, district=district)
    doc = UploadedDocument.objects.create(
        session=session,
        uploaded_by=user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename="bill.jpg",
        file_size=len(FAKE_JPEG),
        mime_type="image/jpeg",
        file=SimpleUploadedFile("bill.jpg", FAKE_JPEG, content_type="image/jpeg"),
    )
    OCRResult.objects.create(
        document=doc,
        status=OCRStatus.PENDING,
        extracted_data="{}",
        confidence_scores={},
        overall_confidence=0,
    )
    return doc


@pytest.fixture
def openai_sdk():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        with patch("apps.documents.services.providers.openai_provider.OpenAI") as client_cls:
            reply = MagicMock()
            reply.choices[0].message.content = CANNED_BILL
            client_cls.return_value.chat.completions.create.return_value = reply
            yield client_cls.return_value


@pytest.fixture
def gemini_sdk():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        with patch("apps.documents.services.providers.gemini.genai") as genai:
            genai.Client.return_value.models.generate_content.return_value.text = CANNED_BILL
            yield genai.Client.return_value


def test_a_deploy_that_names_no_provider_reads_uploads_with_openai(monkeypatch):
    """Heroku sets OPENAI_API_KEY but not OCR_PROVIDER, so the shipped default decides
    which company receives filers' documents in production."""
    import config.settings.base as base_settings

    monkeypatch.delenv("OCR_PROVIDER", raising=False)
    monkeypatch.delenv("OCR_MODEL", raising=False)
    # A developer's repo-root .env must not stand in for the shipped default.
    monkeypatch.setattr(environ.Env, "read_env", lambda *args, **kwargs: None)
    try:
        reloaded = importlib.reload(base_settings)
        assert reloaded.OCR_PROVIDER == "openai"
        assert reloaded.OCR_MODEL == ""
    finally:
        monkeypatch.undo()
        importlib.reload(base_settings)


def test_openai_reads_the_upload_with_gpt_4o_when_no_model_is_named(
    settings, uploaded_bill, openai_sdk, gemini_sdk
):
    settings.OCR_PROVIDER = "openai"
    settings.OCR_MODEL = ""

    _run_processing(uploaded_bill.id)

    assert openai_sdk.chat.completions.create.call_args.kwargs["model"] == "gpt-4o"
    gemini_sdk.models.generate_content.assert_not_called()
    assert OCRResult.objects.get(document=uploaded_bill).status == OCRStatus.COMPLETED


def test_gemini_reads_the_upload_when_ocr_provider_says_gemini(
    settings, uploaded_bill, openai_sdk, gemini_sdk
):
    settings.OCR_PROVIDER = "gemini"
    settings.OCR_MODEL = ""

    _run_processing(uploaded_bill.id)

    assert gemini_sdk.models.generate_content.call_args.kwargs["model"] == "gemini-2.0-flash"
    openai_sdk.chat.completions.create.assert_not_called()
    assert OCRResult.objects.get(document=uploaded_bill).status == OCRStatus.COMPLETED


def test_ocr_model_switches_the_model_without_a_deploy(settings, uploaded_bill, openai_sdk):
    settings.OCR_PROVIDER = "openai"
    settings.OCR_MODEL = "gpt-4o-mini"

    _run_processing(uploaded_bill.id)

    assert openai_sdk.chat.completions.create.call_args.kwargs["model"] == "gpt-4o-mini"


def test_an_unknown_provider_fails_the_upload_at_read_time_not_at_boot(
    settings, uploaded_bill, openai_sdk, gemini_sdk
):
    # This module imported the documents views without error: a bad value only
    # surfaces when a document is read.
    settings.OCR_PROVIDER = "tesseract"

    with pytest.raises(ImproperlyConfigured, match="tesseract"):
        _get_processor()

    _run_processing(uploaded_bill.id)

    assert OCRResult.objects.get(document=uploaded_bill).status == OCRStatus.FAILED
    openai_sdk.chat.completions.create.assert_not_called()
    gemini_sdk.models.generate_content.assert_not_called()
