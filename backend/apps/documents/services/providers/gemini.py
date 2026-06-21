"""Google Gemini provider for document OCR via google-genai SDK."""

import os

from google import genai
from google.genai import types

from .base import BaseOCRProvider


class GeminiProvider(BaseOCRProvider):
    """
    Gemini vision/text provider.

    Uses text mode (opendataloader-pdf extracted markdown → prompt) when image_data is empty.
    Uses vision mode (pymupdf JPEG or direct image upload) when image_data is non-empty.
    extract() sets response_mime_type="application/json" for reliable structured output.
    """

    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def classify(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision(image_data, prompt)
        return self._text(prompt)

    def extract(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision(image_data, prompt, json_mode=True)
        return self._text(prompt, json_mode=True)

    def _text(self, prompt: str, *, json_mode: bool = False) -> str:
        config = (
            types.GenerateContentConfig(response_mime_type="application/json")
            if json_mode
            else None
        )
        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response.text or ""

    def _vision(self, image_data: bytes, prompt: str, *, json_mode: bool = False) -> str:
        config = (
            types.GenerateContentConfig(response_mime_type="application/json")
            if json_mode
            else None
        )
        image_part = types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
        response = self._client.models.generate_content(
            model=self.model,
            contents=[image_part, prompt],
            config=config,
        )
        return response.text or ""
