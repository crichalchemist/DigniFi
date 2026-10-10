"""OpenAI provider for document OCR via the openai SDK."""

import base64
import os
from typing import Any

from openai import OpenAI

from .base import BaseOCRProvider


class OpenAIProvider(BaseOCRProvider):
    """
    OpenAI vision/text provider.

    Uses text mode (opendataloader-pdf extracted markdown → prompt) when there are no images.
    Uses vision mode (pymupdf JPEG pages or a direct image upload) otherwise, sending one
    image_url part per page, in page order, before the prompt.
    extract() sets response_format={"type": "json_object"} for reliable structured output;
    that mode requires the word "json" in the prompt, which the extraction prompts satisfy
    ("Return ONLY a valid JSON object").

    Module is named openai_provider.py rather than openai.py so it cannot shadow the
    installed ``openai`` package for anything importing it by name.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def classify(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision([image_data], prompt)
        return self._text(prompt)

    def extract(self, images: list[bytes], prompt: str) -> str:
        if images:
            return self._vision(images, prompt, json_mode=True)
        return self._text(prompt, json_mode=True)

    def _text(self, prompt: str, *, json_mode: bool = False) -> str:
        return self._complete([{"type": "text", "text": prompt}], json_mode=json_mode)

    def _vision(self, images: list[bytes], prompt: str, *, json_mode: bool = False) -> str:
        # image/jpeg is hardcoded to match GeminiProvider: DocumentProcessor renders
        # PDF pages to JPEG and does not thread the original MIME type through.
        content: list[dict[str, Any]] = []
        for image in images:
            encoded = base64.b64encode(image).decode()
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
            )
        content.append({"type": "text", "text": prompt})
        return self._complete(content, json_mode=json_mode)

    def _complete(self, content: list[dict[str, Any]], *, json_mode: bool) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
