import json
import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Any

try:
    import opendataloader_pdf
except ImportError:
    opendataloader_pdf = None

from apps.documents.services.providers.base import BaseOCRProvider
from apps.documents.services.providers.prompts.image_extraction import build_image_extraction_prompt
from apps.documents.services.providers.prompts.text_extraction import build_text_extraction_prompt

logger = logging.getLogger(__name__)

_MIN_TEXT_LENGTH = 30
_MAX_SCANNED_PAGES = 3


@dataclass
class ExtractionResult:
    fields: dict[str, Any] = field(default_factory=dict)
    confidence: dict[str, Any] = field(default_factory=dict)
    detected_type: str = ""
    error: str = ""


def _read_odl_output(output_dir: str) -> str:
    for fname in os.listdir(output_dir):
        if fname.endswith(".md") or fname.endswith(".txt"):
            with open(os.path.join(output_dir, fname)) as f:
                return f.read()
    return ""


def _pdf_to_image_bytes(pdf_bytes: bytes, page_index: int = 0) -> bytes:
    import fitz  # pymupdf

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if page_index >= len(doc):
        page_index = 0
    page = doc[page_index]
    pix = page.get_pixmap(dpi=150)
    return pix.tobytes("jpeg")


class DocumentProcessor:
    def __init__(self, provider: BaseOCRProvider):
        self._provider = provider

    def process(self, file_bytes: bytes, mime_type: str, doc_type: str) -> ExtractionResult:
        try:
            if mime_type in ("image/jpeg", "image/png", "image/webp"):
                return self._process_image(file_bytes, doc_type)
            elif mime_type == "application/pdf":
                return self._process_pdf(file_bytes, doc_type)
            else:
                return ExtractionResult(error=f"Unsupported MIME type: {mime_type}")
        except Exception as exc:
            return ExtractionResult(error=str(exc))

    def _process_image(self, image_bytes: bytes, doc_type: str) -> ExtractionResult:
        prompt = build_image_extraction_prompt(doc_type)
        raw = self._provider.extract(image_bytes, prompt)
        return self._parse_result(raw, doc_type)

    def _process_pdf(self, pdf_bytes: bytes, doc_type: str) -> ExtractionResult:
        text = ""
        with tempfile.TemporaryDirectory() as tmp_in, tempfile.TemporaryDirectory() as tmp_out:
            pdf_path = os.path.join(tmp_in, "document.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)

            # opendataloader-pdf shells out to `java`; if the JRE (or the
            # package itself) is missing, degrade to the vision path rather
            # than failing the whole upload.
            if opendataloader_pdf is not None:
                try:
                    opendataloader_pdf.convert(
                        input_path=[pdf_path],
                        output_dir=tmp_out,
                        format="markdown",
                    )
                    text = _read_odl_output(tmp_out)
                except Exception as exc:
                    logger.warning(
                        "opendataloader-pdf text extraction failed (%s); "
                        "falling back to vision OCR",
                        exc,
                    )
            else:
                logger.warning("opendataloader-pdf not installed; using vision OCR for PDF")

        if len(text.strip()) >= _MIN_TEXT_LENGTH:
            prompt = build_text_extraction_prompt(doc_type, text)
            raw = self._provider.extract(b"", prompt)
        else:
            image_bytes = _pdf_to_image_bytes(pdf_bytes, page_index=0)
            prompt = build_image_extraction_prompt(doc_type)
            raw = self._provider.extract(image_bytes, prompt)

        return self._parse_result(raw, doc_type)

    def _parse_result(self, raw: str, doc_type: str) -> ExtractionResult:
        try:
            clean = raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            data = json.loads(clean)
            confidence_score = int(data.pop("confidence_score", 0))
            return ExtractionResult(
                fields=data,
                confidence={"overall": confidence_score},
                detected_type=doc_type,
            )
        except (json.JSONDecodeError, ValueError):
            return ExtractionResult(
                fields={},
                confidence={"overall": 0},
                detected_type=doc_type,
                error=f"Failed to parse LLM response: {raw[:200]}",
            )
