import shutil
from unittest.mock import MagicMock, patch

import pytest

from apps.documents.models import DocumentType
from apps.documents.services.processor import (
    DocumentProcessor,
    ExtractionResult,
    opendataloader_pdf,
)
from apps.documents.tests.builders import scanned_pdf, text_pdf


@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.extract.return_value = (
        '{"creditor_name": "Chase", "amount_owed": "1200.00", '
        '"creditor_type": "credit_card", "confidence_score": 85}'
    )
    return provider


@pytest.fixture
def processor(mock_provider):
    return DocumentProcessor(provider=mock_provider)


@pytest.mark.parametrize(
    "image_bytes,mime_type",
    [(b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG\r\n", "image/png")],  # magic bytes
    ids=["jpeg", "png"],
)
def test_an_image_routes_to_vision(processor, mock_provider, image_bytes, mime_type):
    result = processor.process(image_bytes, mime_type, DocumentType.CREDITOR_BILL)

    assert isinstance(result, ExtractionResult)
    call_args = mock_provider.extract.call_args
    assert call_args[0][0] == [image_bytes]


def test_extraction_result_parses_fields(processor):
    result = processor.process(b"\xff\xd8", "image/jpeg", DocumentType.CREDITOR_BILL)
    assert result.fields["creditor_name"] == "Chase"
    assert result.confidence["overall"] == 85
    assert result.detected_type == DocumentType.CREDITOR_BILL


def test_an_unparseable_reply_is_recorded_without_its_text(processor, mock_provider):
    # error_message is an operations field, and a reply can quote the filer's document.
    reply = "Jordan Sample, SSN 900-12-3456, owes $1,284.50"
    mock_provider.extract.return_value = reply
    result = processor.process(b"\xff\xd8", "image/jpeg", DocumentType.CREDITOR_BILL)
    assert result.error == f"model reply was not valid JSON ({len(reply)} characters)"
    assert "900-12-3456" not in result.error
    assert result.fields == {}
    assert result.confidence["overall"] == 0


def test_pdf_falls_back_to_vision_when_java_missing(processor, mock_provider):
    """A missing JRE (opendataloader-pdf shells out to `java`) must degrade to
    the vision path, not fail the upload — prod images without Java would
    otherwise reject every PDF."""
    fake_page_image = b"\xff\xd8fake-jpeg"
    with patch("apps.documents.services.processor.opendataloader_pdf") as mock_odl:
        mock_odl.convert.side_effect = FileNotFoundError("java not found")
        with patch(
            "apps.documents.services.processor._pdf_to_page_images",
            return_value=[fake_page_image],
        ):
            result = processor.process(b"%PDF-1.4", "application/pdf", DocumentType.CREDITOR_BILL)

    assert result.error == ""
    call_args = mock_provider.extract.call_args
    assert call_args[0][0] == [fake_page_image]


def test_pdf_falls_back_to_vision_when_opendataloader_not_installed(processor, mock_provider):
    fake_page_image = b"\xff\xd8fake-jpeg"
    with patch("apps.documents.services.processor.opendataloader_pdf", None):
        with patch(
            "apps.documents.services.processor._pdf_to_page_images",
            return_value=[fake_page_image],
        ):
            result = processor.process(b"%PDF-1.4", "application/pdf", DocumentType.CREDITOR_BILL)

    assert result.error == ""
    call_args = mock_provider.extract.call_args
    assert call_args[0][0] == [fake_page_image]


@pytest.mark.skipif(
    shutil.which("java") is None or opendataloader_pdf is None,
    reason="real-JVM contract tests need `java` on PATH and opendataloader-pdf installed",
)
class TestRealJvmContract:
    """Runs the real opendataloader CLI with the options the processor passes, so the
    JVM stand-in in test_processing_outcomes.py stays honest. The first JVM launch on a
    machine can take about 30 s."""

    def test_real_jvm_puts_page_two_of_a_text_pdf_in_the_text_prompt(
        self, processor, mock_provider
    ):
        pdf = text_pdf(
            [
                "Lakeshore Medical Billing\nPatient statement for services in August.",
                "Account 4417-2290\nBalance due: $1,284.50",
            ]
        )

        result = processor.process(pdf, "application/pdf", DocumentType.CREDITOR_BILL)

        images, prompt = mock_provider.extract.call_args[0]
        assert images == []
        assert "Balance due: $1,284.50" in prompt
        assert result.error == ""

    def test_real_jvm_keeps_the_letterhead_that_names_the_creditor(self, processor, mock_provider):
        pdf = text_pdf(
            [
                "Patient statement for services in August.",
                "Account 4417-2290\nBalance due: $1,284.50",
            ],
            letterhead="Lakeshore Medical Billing",
        )

        processor.process(pdf, "application/pdf", DocumentType.CREDITOR_BILL)

        _images, prompt = mock_provider.extract.call_args[0]
        assert "Lakeshore Medical Billing" in prompt

    def test_real_jvm_sends_a_scanned_pdf_to_vision(self, processor, mock_provider):
        pdf = scanned_pdf([(200, 300), (300, 300)])

        processor.process(pdf, "application/pdf", DocumentType.CREDITOR_BILL)

        images, _prompt = mock_provider.extract.call_args[0]
        assert len(images) == 2
