"""Base schema for all OCR extraction schemas."""

from pydantic import BaseModel, Field


class BaseExtractionSchema(BaseModel):
    """Base class for all document extraction schemas."""

    confidence_score: int = Field(
        ge=0,
        le=100,
        description="Overall extraction confidence (0-100)"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "description": "Base extraction schema with confidence scoring"
        }
