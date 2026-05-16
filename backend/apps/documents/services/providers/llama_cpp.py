"""llama.cpp server provider using OpenAI-compatible API."""

import base64

from openai import OpenAI

from .base import BaseOCRProvider


class LlamaCppProvider(BaseOCRProvider):
    """
    llama.cpp server provider (Gemma 3 4B multimodal).

    Uses the OpenAI-compatible API exposed by the llama.cpp server.
    No API key required for local deployment.

    Args:
        base_url: Base URL of the llama.cpp server (default: http://llm:8080/v1)
    """

    def __init__(self, base_url: str = "http://llm:8080/v1"):
        """
        Initialize llama.cpp provider.

        Args:
            base_url: llama.cpp server base URL
        """
        self.client = OpenAI(api_key="not-required", base_url=base_url)

    def classify(self, image_data: bytes, prompt: str) -> str:
        """
        Classify document type.

        Args:
            image_data: Raw image bytes (PDF/JPG/PNG)
            prompt: Classification prompt

        Returns:
            Document type code (e.g., "pay_stub")
        """
        return self._call_vision(image_data, prompt)

    def extract(self, image_data: bytes, prompt: str) -> str:
        """
        Extract structured data from document.

        Args:
            image_data: Raw image bytes (PDF/JPG/PNG). If empty, uses text-only mode.
            prompt: Extraction prompt with JSON schema

        Returns:
            JSON string with extracted data
        """
        if image_data:
            return self._call_vision(image_data, prompt)
        return self._call_text(prompt)

    def _call_vision(self, image_data: bytes, prompt: str) -> str:
        """
        Make vision API call with image data.

        Args:
            image_data: Raw image bytes
            prompt: Text prompt for vision model

        Returns:
            API response content as string
        """
        b64 = base64.b64encode(image_data).decode("utf-8")
        response = self.client.chat.completions.create(
            model="gemma-3-4b-it",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        return response.choices[0].message.content

    def _call_text(self, prompt: str) -> str:
        """
        Make text-only API call.

        Args:
            prompt: Text prompt for model

        Returns:
            API response content as string
        """
        response = self.client.chat.completions.create(
            model="gemma-3-4b-it",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1024,
        )
        return response.choices[0].message.content
