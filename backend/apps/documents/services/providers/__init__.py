"""OCR provider implementations."""

from .base import BaseOCRProvider
from .clarifai import ClarifaiOCRProvider

__all__ = [
    'BaseOCRProvider',
    'ClarifaiOCRProvider',
]
