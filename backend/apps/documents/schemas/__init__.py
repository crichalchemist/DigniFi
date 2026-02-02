"""Document extraction schemas."""

from .base import BaseExtractionSchema
from .paystub import PayStubExtraction

__all__ = [
    'BaseExtractionSchema',
    'PayStubExtraction',
]
