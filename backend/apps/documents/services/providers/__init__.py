"""OCR provider implementations.

``GeminiProvider`` is intentionally NOT imported here — importing it pulls the
``google-genai`` SDK at module load, which would make the entire documents
URLconf (and app boot) hard-depend on the OCR SDK. Import it lazily where used:
``from apps.documents.services.providers.gemini import GeminiProvider``.
"""

from .base import BaseOCRProvider

__all__ = [
    "BaseOCRProvider",
]
