"""
Schema dataclasses and loader for form field specifications.

Provides FieldSpec (individual field definition) and FormSchema (complete form specification),
plus load_schema() function to load form schemas from JSON files.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import pypdf
from django.conf import settings

from apps.forms.field_index import export_state, load_index


@dataclass(frozen=True)
class UIFieldSpec:
    step: str
    prompt: str
    widget: str
    help_text: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> UIFieldSpec:
        return cls(
            step=data.get("step", "Unknown Step"),
            prompt=data.get("prompt", ""),
            widget=data.get("widget", "text"),
            help_text=data.get("help_text"),
        )


@dataclass(frozen=True)
class FieldSpec:
    """Specification for a single form field."""

    pdf_field: str  # an index full_name (apps.forms.field_index)
    type: str  # text | checkbox | radio | choice
    source: str  # constant | derived | asked | ingested | signature
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
    # checkbox/radio only: normalised answer → export state. {"true": state} is
    # a single box; {} means not mapped yet, and the binding emits nothing.
    choices: dict[str, str] | None = None
    ui: UIFieldSpec | None = None


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
    fields = []
    for field_data in raw["fields"]:
        ui_data = field_data.pop("ui", None)
        ui_spec = UIFieldSpec.from_dict(ui_data) if ui_data else None
        fields.append(FieldSpec(**field_data, ui=ui_spec))

    return FormSchema(
        form_type=raw["form_type"],
        template_filename=raw["template_filename"],
        template_version=raw["template_version"],
        fields=fields,
    )


# Index widget types each binding type may target (spec §5.4 check 4).
_WIDGET_TYPES = {
    "text": {"Text"},
    "choice": {"ComboBox"},
    "checkbox": {"CheckBox", "RadioButton"},
    "radio": {"CheckBox", "RadioButton"},
}
_BINDING_NAMESPACES = ("answer:", "sofa.")


def validate_schema(
    schema: FormSchema, derivations: set[str], predicates: set[str]
) -> list[tuple[str, str]]:
    """
    Check a schema against its template and field index (spec §5.4, checks 2-7).

    Returns (code, message) pairs; an empty list means the schema is valid.
    apps.forms.checks reports each pair as a forms.<code> system-check error.
    """
    errors: list[tuple[str, str]] = []
    template = (Path(settings.PDF_FORMS_DIRECTORY) / schema.template_filename).read_bytes()
    if hashlib.sha256(template).hexdigest() != schema.template_version:
        errors.append(("E002", "template_version is not the template's SHA-256"))

    index = load_index(schema.template_filename)
    template_fields = pypdf.PdfReader(BytesIO(template)).get_fields() or {}
    seen: dict[str, list[FieldSpec]] = {}

    for f in schema.fields:
        widgets = index.get(f.pdf_field)
        if widgets is None:
            errors.append(("E003", f"{f.pdf_field!r} is not a full name in the field index"))
            continue
        seen.setdefault(f.pdf_field, []).append(f)

        types = {w.type for w in widgets}
        if any(w.basis == "form_control" for w in widgets):
            errors.append(("E004", f"{f.pdf_field!r} is a push button"))
        elif not types <= _WIDGET_TYPES.get(f.type, set()):
            errors.append(("E004", f"{f.pdf_field!r} is bound as {f.type} but is {sorted(types)}"))
        is_box = f.type in ("checkbox", "radio")
        if is_box and f.choices is None:
            errors.append(("E004", f"{f.pdf_field!r}: a {f.type} binding needs choices"))
        if not is_box and f.choices is not None:
            errors.append(
                ("E004", f"{f.pdf_field!r}: choices go on checkbox and radio only, not on {f.type}")
            )

        if f.choices:
            # The filler lower-cases the answer before the lookup (spec §5.1).
            for key in sorted(k for k in f.choices if k != k.lower()):
                errors.append(
                    (
                        "E004",
                        f"{f.pdf_field!r}: choices key {key!r} isn't lower-case, "
                        "so no answer can match it",
                    )
                )
            states = {export_state(w.on_state) for w in widgets if w.on_state}
            for state in sorted(set(f.choices.values()) - states):
                errors.append(("E005", f"{f.pdf_field!r} has no state {state!r}"))
        if f.type == "choice" and f.source == "constant":
            # .get: a template that has drifted from its index is an error, not a crash.
            options = [str(o) for o in template_fields.get(f.pdf_field, {}).get("/Opt", [])]
            if f.value not in options:
                errors.append(("E005", f"{f.pdf_field!r} has no option {f.value!r}"))

        if f.source == "TBD":
            errors.append(("E007", f"{f.pdf_field!r}: source is still TBD"))
        if f.source == "derived" and f.rule not in derivations:
            errors.append(("E007", f"{f.pdf_field!r}: unknown derivation rule {f.rule!r}"))
        if f.conditional_on is not None and f.conditional_on not in predicates:
            errors.append(("E007", f"{f.pdf_field!r}: unknown predicate {f.conditional_on!r}"))
        if f.binding is not None and not f.binding.startswith(_BINDING_NAMESPACES):
            errors.append(("E007", f"{f.pdf_field!r}: unknown binding namespace {f.binding!r}"))
        if f.repeat is not None and not f.repeat_capacity:
            errors.append(("E007", f"repeat group {f.repeat!r} has no repeat_capacity"))

    for name, bindings in seen.items():
        rows = {(b.repeat, b.row) for b in bindings}
        same_group = len({b.repeat for b in bindings}) == 1 and bindings[0].repeat is not None
        if len(bindings) > 1 and not (same_group and len(rows) == len(bindings)):
            errors.append(("E006", f"{name!r} is bound {len(bindings)} times"))
    return errors
