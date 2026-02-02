"""Clarifai OCR provider using OpenAI-compatible API."""

import os
import base64
from openai import OpenAI

from .base import BaseOCRProvider


class ClarifaiOCRProvider(BaseOCRProvider):
    """
    Clarifai API provider using OpenAI-compatible endpoint.

    Uses DeepSeek-OCR model hosted on Clarifai.
    Requires CLARIFAI_PAT environment variable.
    """

    def __init__(self):
        """Initialize Clarifai client."""
        api_key = os.environ.get('CLARIFAI_PAT')
        if not api_key:
            raise ValueError(
                'CLARIFAI_PAT environment variable required for Clarifai provider'
            )

        # Clarifai uses OpenAI-compatible API format
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.clarifai.com/v2"
        )

    def classify(self, image_data: bytes, prompt: str) -> str:
        """
        Quick document type classification.

        Args:
            image_data: Raw image bytes
            prompt: Classification prompt

        Returns:
            Document type code as string
        """
        return self._call_api(image_data, prompt)

    def extract(self, image_data: bytes, prompt: str) -> str:
        """
        Extract structured data from document.

        Args:
            image_data: Raw image bytes
            prompt: Extraction prompt with JSON schema

        Returns:
            JSON string with extracted data
        """
        return self._call_api(image_data, prompt)

    def _call_api(self, image_data: bytes, prompt: str) -> str:
        """
        Make API call to Clarifai.

        Args:
            image_data: Raw image bytes
            prompt: Text prompt for OCR

        Returns:
            API response content as string
        """
        # Encode image as base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        # Call Clarifai API (OpenAI-compatible format)
        response = self.client.chat.completions.create(
            model="deepseek-ocr",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            max_tokens=2000,
            temperature=0.0  # Deterministic for data extraction
        )

        return response.choices[0].message.content
