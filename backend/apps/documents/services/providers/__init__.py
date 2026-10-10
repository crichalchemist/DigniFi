"""OCR provider implementations.

``GeminiProvider`` and ``OpenAIProvider`` are intentionally NOT imported here —
importing them pulls the ``google-genai`` / ``openai`` SDK at module load, which
would make the entire documents URLconf (and app boot) hard-depend on an OCR SDK.
Import them lazily where used:
``from apps.documents.services.providers.gemini import GeminiProvider``
``from apps.documents.services.providers.openai_provider import OpenAIProvider``.
"""

from .base import BaseOCRProvider

__all__ = [
    "BaseOCRProvider",
]
