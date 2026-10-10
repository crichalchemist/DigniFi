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


def test_jpeg_routes_to_vision(processor, mock_provider):
    image_bytes = b"\xff\xd8\xff"  # JPEG magic bytes
    result = processor.process(image_bytes, "image/jpeg", DocumentType.CREDITOR_BILL)

    assert isinstance(result, ExtractionResult)
    call_args = mock_provider.extract.call_args
    assert call_args[0][0] == [image_bytes]


def test_png_routes_to_vision(processor, mock_provider):
    png_bytes = b"\x89PNG\r\n"
    processor.process(png_bytes, "image/png", DocumentType.CREDITOR_BILL)
    call_args = mock_provider.extract.call_args
    assert call_args[0][0] == [png_bytes]


def test_extraction_result_parses_fields(processor):
    result = processor.process(b"\xff\xd8", "image/jpeg", DocumentType.CREDITOR_BILL)
    assert result.fields["creditor_name"] == "Chase"
    assert result.confidence["overall"] == 85
    assert result.detected_type == DocumentType.CREDITOR_BILL


def test_invalid_json_returns_failed_result(processor, mock_provider):
    mock_provider.extract.return_value = "Not JSON at all"
    result = processor.process(b"\xff\xd8", "image/jpeg", DocumentType.CREDITOR_BILL)
    assert result.fields == {}
    assert result.confidence["overall"] == 0


def test_an_unparseable_reply_is_recorded_without_its_text(processor, mock_provider):
    # error_message is an operations field, and a reply can quote the filer's document.
    reply = "Jordan Sample, SSN 900-12-3456, owes $1,284.50"
    mock_provider.extract.return_value = reply
    result = processor.process(b"\xff\xd8", "image/jpeg", DocumentType.CREDITOR_BILL)
    assert result.error == f"model reply was not valid JSON ({len(reply)} characters)"
    assert "900-12-3456" not in result.error


def test_pdf_with_text_routes_to_text_path(processor, mock_provider):
    mock_provider.extract.return_value = (
        '{"employer_name": "Acme", "gross_pay": "3200.00", '
        '"pay_period_start": "2026-01-01", "pay_period_end": "2026-01-15", '
        '"confidence_score": 90}'
    )
    with patch("apps.documents.services.processor.opendataloader_pdf") as mock_odl:
        mock_odl.convert.return_value = None
        with patch("apps.documents.services.processor._read_odl_output") as mock_read:
            mock_read.return_value = "Employer: Acme Corp\nGross Pay: $3,200.00"
            processor.process(b"%PDF-1.4", "application/pdf", DocumentType.PAY_STUB)

    call_args = mock_provider.extract.call_args
    assert call_args[0][0] == []


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
