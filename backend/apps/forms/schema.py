"""
Schema dataclasses and loader for form field specifications.

Provides FieldSpec (individual field definition) and FormSchema (complete form specification),
plus load_schema() function to load form schemas from JSON files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pypdf
from django.conf import settings


@dataclass(frozen=True)
class FieldSpec:
    """Specification for a single form field."""

    pdf_field: str
    type: str  # text | checkbox | radio | choice
    source: str  # constant | derived | asked | ingested | signature | TBD
    on_states: tuple[str, ...]
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
    row: int | None
    legal_review: bool


@dataclass(frozen=True)
class FormSchema:
    """Complete specification for a form, including all fields."""

    form_type: str
    template_filename: str
    template_version: str
    fields: list[FieldSpec]


@lru_cache(maxsize=32)
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


def template_field_names(template_path: Path) -> set[str]:
    """Return the set of AcroForm field names in a PDF template."""
    reader = pypdf.PdfReader(str(template_path))
    return set((reader.get_fields() or {}).keys())


def validate_schema(schema: FormSchema, derivations: set[str], predicates: set[str]) -> list[str]:
    """
    Return a list of error strings. Empty list = schema is valid.

    Checks: every pdf_field exists in the live template; no source left "TBD";
    derived rules and conditional_on predicates resolve; repeat groups carry a
    capacity. Run as a test so drift/typos fail CI, not a court filing.
    """
    errors: list[str] = []
    template_path = Path(settings.PDF_FORMS_DIRECTORY) / schema.template_filename
    real_fields = template_field_names(template_path)

    for f in schema.fields:
        if f.pdf_field not in real_fields:
            errors.append(f"pdf_field not in template: {f.pdf_field!r}")
        if f.source == "TBD":
            errors.append(f"source still TBD: {f.pdf_field!r}")
        if f.source == "derived" and f.rule not in derivations:
            errors.append(f"unknown derivation rule {f.rule!r} on {f.pdf_field!r}")
        if f.conditional_on is not None and f.conditional_on not in predicates:
            errors.append(f"unknown predicate {f.conditional_on!r} on {f.pdf_field!r}")
        if f.repeat is not None and not f.repeat_capacity:
            errors.append(f"repeat group {f.repeat!r} missing repeat_capacity")
    return errors
