"""Abstract base class for OCR providers."""

from abc import ABC, abstractmethod


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
