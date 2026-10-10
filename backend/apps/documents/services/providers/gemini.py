"""Google Gemini provider for document OCR via google-genai SDK."""

import os

from google import genai
from google.genai import types

from .base import BaseOCRProvider


class GeminiProvider(BaseOCRProvider):
    """
    Gemini vision/text provider.

    Uses text mode (opendataloader-pdf extracted markdown → prompt) when there are no images.
    Uses vision mode (pymupdf JPEG pages or a direct image upload) otherwise, sending one
    inline image part per page, in page order, before the prompt.
    extract() sets response_mime_type="application/json" for reliable structured output.
    """

    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def classify(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision([image_data], prompt)
        return self._text(prompt)

    def extract(self, images: list[bytes], prompt: str) -> str:
        if images:
            return self._vision(images, prompt, json_mode=True)
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

    def _vision(self, images: list[bytes], prompt: str, *, json_mode: bool = False) -> str:
        config = (
            types.GenerateContentConfig(response_mime_type="application/json")
            if json_mode
            else None
        )
        image_parts = [
            types.Part.from_bytes(data=image, mime_type="image/jpeg") for image in images
        ]
        response = self._client.models.generate_content(
            model=self.model,
            contents=[*image_parts, prompt],
            config=config,
        )
        return response.text or ""
