"""Management command: ingest_form_schema.

Reads a blank AO court PDF template, discovers all fillable fields,
and writes a draft JSON schema to FORM_SCHEMAS_DIRECTORY.
On subsequent runs detects template drift by comparing SHA-256 hashes.
"""

import hashlib
import json
from pathlib import Path

import pypdf
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.forms.services.pdf_filler import FORM_TEMPLATES


def template_version_hash(template_path: Path) -> str:
    """Return the SHA-256 hex digest of the template PDF file."""
    sha = hashlib.sha256()
    with open(template_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _field_type_and_states(obj: object) -> tuple[str, list[str]]:
    """Classify a PDF annotation object into (type, on_states)."""
    ft = obj.get("/FT")
    if ft == "/Btn":
        states = [s for s in (obj.get("/_States_") or []) if s != "/Off"]
        return ("checkbox", states or ["/Yes"])
    if ft == "/Ch":
        return ("choice", [])
    return ("text", [])


def build_draft_schema(form_type: str) -> dict:
    """
    Build a draft schema dict from a blank AO PDF template.

    Args:
        form_type: A key in FORM_TEMPLATES (e.g. "form_107").

    Returns:
        dict with keys: form_type, template_filename, template_version, fields.

    Raises:
        CommandError: If form_type is not in FORM_TEMPLATES.
    """
    if form_type not in FORM_TEMPLATES:
        raise CommandError(f"unknown form_type {form_type!r}; valid keys: {sorted(FORM_TEMPLATES)}")

    filename = FORM_TEMPLATES[form_type]
    template_path = Path(settings.PDF_FORMS_DIRECTORY) / filename

    reader = pypdf.PdfReader(str(template_path))

    # Build a page-number lookup: field name -> page number (1-based)
    page_of: dict[str, int] = {}
    for page_idx, page in enumerate(reader.pages, start=1):
        annots = page.get("/Annots")
        if not annots:
            continue
        for annot_ref in annots:
            annot = annot_ref.get_object() if hasattr(annot_ref, "get_object") else annot_ref
            name = annot.get("/T")
            if name and name not in page_of:
                page_of[str(name)] = page_idx

    records: list[dict] = []
    seen: set[str] = set()

    for page_idx, page in enumerate(reader.pages, start=1):
        annots = page.get("/Annots")
        if not annots:
            continue
        for annot_ref in annots:
            annot = annot_ref.get_object() if hasattr(annot_ref, "get_object") else annot_ref
            name = annot.get("/T")
            if not name:
                continue
            name = str(name)
            if name in seen:
                continue
            seen.add(name)

            ftype, on_states = _field_type_and_states(annot)
            label_raw = annot.get("/TU")
            label = str(label_raw) if label_raw else ""

            records.append(
                {
                    "pdf_field": name,
                    "type": ftype,
                    "source": "TBD",
                    "on_states": on_states,
                    "page": page_of.get(name, page_idx),
                    "label": label,
                    "required": False,
                    "conditional_on": None,
                    "value": None,
                    "rule": None,
                    "ingest_key": None,
                    "binding": None,
                    "repeat": None,
                    "repeat_capacity": None,
                    "row": None,
                    "legal_review": False,
                }
            )

    return {
        "form_type": form_type,
        "template_filename": filename,
        "template_version": template_version_hash(template_path),
        "fields": records,
    }


class Command(BaseCommand):
    help = "Draft a form schema from a blank AO PDF template."

    def add_arguments(self, parser):
        parser.add_argument(
            "form_type",
            type=str,
            help="Form type key (e.g. form_107). Must be in FORM_TEMPLATES.",
        )

    def handle(self, *args, **options):
        form_type = options["form_type"]
        schemas_dir = Path(settings.FORM_SCHEMAS_DIRECTORY)
        schemas_dir.mkdir(parents=True, exist_ok=True)
        schema_path = schemas_dir / f"{form_type}.json"

        draft = build_draft_schema(form_type)

        if schema_path.exists():
            with open(schema_path) as f:
                existing = json.load(f)
            existing_version = existing.get("template_version", "")
            if existing_version == draft["template_version"]:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{form_type}: no drift — template unchanged (version {draft['template_version'][:8]}…)"
                    )
                )
                return
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"{form_type}: drift detected — template changed "
                        f"({existing_version[:8]}… → {draft['template_version'][:8]}…); updated schema."
                    )
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{form_type}: new schema drafted with {len(draft['fields'])} fields."
                )
            )

        with open(schema_path, "w") as f:
            json.dump(draft, f, indent=2)
            f.write("\n")
