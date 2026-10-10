"""Abstract base class for OCR providers."""

from abc import ABC, abstractmethod


class EmptyModelReply(RuntimeError):
    """The model sent back no text, after a retry where one could help.

    The message names ``finish_reason`` and whether a refusal was present. It never
    includes the refusal's wording, because it is stored in ``OCRResult.error_message``
    and a refusal can quote the filer's document.
    """


class BaseOCRProvider(ABC):
    """
    Abstract base class for OCR providers.

    Implementations: GeminiProvider, OpenAIProvider
    """

    @abstractmethod
    def classify(self, image_data: bytes, prompt: str) -> str:
        """
        Classify document type.

        Args:
            image_data: Raw image bytes (PDF/JPG/PNG)
            prompt: Classification prompt

        Returns:
            Document type code (e.g., "pay_stub")
        """
        pass

    @abstractmethod
    def extract(self, images: list[bytes], prompt: str) -> str:
        """
        Extract structured data from document.

        Args:
            images: JPEG bytes, one per page, in page order (a direct photo upload is a
                one-item list). An empty list means text mode: the document's text is
                already inside the prompt.
            prompt: Extraction prompt with JSON schema

        Returns:
            JSON string with extracted data
        """
        pass
