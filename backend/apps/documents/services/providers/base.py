"""Abstract base class for OCR providers."""

from abc import ABC, abstractmethod
from typing import Any


class BaseOCRProvider(ABC):
    """
    Abstract base class for OCR providers.

    Implementations: ClarifaiOCRProvider, VLLMOCRProvider
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
    def extract(self, image_data: bytes, prompt: str) -> str:
        """
        Extract structured data from document.

        Args:
            image_data: Raw image bytes (PDF/JPG/PNG)
            prompt: Extraction prompt with JSON schema

        Returns:
            JSON string with extracted data
        """
        pass
