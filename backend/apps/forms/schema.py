"""
Schema dataclasses and loader for form field specifications.

Provides FieldSpec (individual field definition) and FormSchema (complete form specification),
plus load_schema() function to load form schemas from JSON files.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


@dataclass(frozen=True)
class FieldSpec:
    """Specification for a single form field."""

    pdf_field: str
    type: str  # text | checkbox | radio | choice
    source: str  # constant | derived | asked | ingested | signature | TBD
    on_states: list[str]
    page: int
    label: str
    required: bool
    conditional_on: str | None  # PREDICATES key, or None = always applicable
    value: str | None
    rule: str | None
    ingest_key: str | None
    binding: str | None
    repeat: str | None
    repeat_capacity: int | None
    row: str | None
    legal_review: bool


@dataclass(frozen=True)
class FormSchema:
    """Complete specification for a form, including all fields."""

    form_type: str
    template_filename: str
    template_version: str
    fields: list[FieldSpec]


def load_schema(form_type: str) -> FormSchema:
    """
    Load and parse form schema from JSON.

    Args:
        form_type: The form type identifier (e.g., 'form_101')

    Returns:
        FormSchema dataclass instance

    Raises:
        FileNotFoundError: If schema file does not exist
        json.JSONDecodeError: If schema file is invalid JSON
    """
    schema_path = Path(settings.FORM_SCHEMAS_DIRECTORY) / f"{form_type}.json"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path) as f:
        raw = json.load(f)

    # Convert field dicts to FieldSpec dataclass instances
    fields = [FieldSpec(**field_data) for field_data in raw["fields"]]

    return FormSchema(
        form_type=raw["form_type"],
        template_filename=raw["template_filename"],
        template_version=raw["template_version"],
        fields=fields,
    )
