# Schema-Driven Form-Fill Engine (SP1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a schema-driven form-fill engine — committed per-form JSON schema, a generic resolver, and a hybrid data model — and prove it end-to-end on Form 107 (Statement of Financial Affairs), raising 107's filled-field count from ~6 to its applicable target.

**Architecture:** A committed, version-pinned JSON schema per form (drafted by ingesting the blank AO PDF) declares every field's `source` (constant/derived/asked/ingested/signature), `binding`, `conditional_on`, and repeat-group membership. `FillResolver.resolve(schema, session)` reads `IntakeSession` + new `SOFAReport`/`FormAnswer` data and returns `{pdf_field: str}` for `PDFFormFiller.fill()`. `form_107_generator.pdf_field_map()` delegates to the resolver; the other 12 generators keep their hand-authored maps as fallback.

**Tech Stack:** Python 3.11, Django 5.0, DRF, pypdf 6.13, PostgreSQL 15, `encrypted-model-fields`; React 19, Vite 7, TypeScript; pytest, vitest, Playwright.

**Design spec:** `docs/superpowers/specs/2026-06-16-form-fill-engine-design.md` (read it first).

## Global Constraints

Every task's requirements implicitly include this section.

- **pypdf 6.13** — pinned; 3.17 raises `KeyError /AP`.
- **Encryption** — financial amounts use `EncryptedDecimalField` (`apps/intake/fields.py`); never store amounts in plaintext.
- **UPL** — legal information, never advice. `legal_review: true` fields fill only from an explicit confirmed answer; no derivation encodes a legal conclusion (exemption choice, debt priority, means-test verdict).
- **Schemas are committed + version-pinned.** A schema whose `template_version` hash no longer matches its template must fail tests, not silently fill.
- **Sworn-document safety** — the resolver never silently truncates a repeat group; overflow raises `RepeatOverflow`.
- **DRF pagination** returns `{count, results}` — frontend guards with `Array.isArray`.
- **household_size** must be set explicitly on any seeded/scripted `DebtorInfo` (default=1 is silently wrong).
- **Lint** — backend `ruff==0.8.5` (CI/container pin); frontend `npm run lint:fix && npm run format`.
- **Accessibility** — WCAG 2.1 AA; trauma-informed, 6th–8th grade reading level for all new copy.
- **Execution discipline (context management)** — chunk by SOFA section (one section = one task = one context); inspect raw `pypdf` AcroForm field dumps with `ctx_execute_file`/`ctx_execute` and emit summaries, never read a raw dump into conversation; the committed schema JSON is the source of truth — each task reads only the field slice it needs. Prefer subagent-per-task execution with review between.

## Commands (run inside the backend container)

```bash
docker compose up -d
docker compose exec backend python -m pytest <path> -v      # backend tests
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
cd frontend && npm test -- <path>                            # frontend tests
cd frontend && npm run e2e                                   # Playwright
```

---

## File Structure

**Create:**

- `backend/apps/forms/schema.py` — `FieldSpec`/`FormSchema` dataclasses, `load_schema()`, `validate_schema()`, `template_field_names()`.
- `backend/apps/forms/services/fill_resolver.py` — `resolve()`, `resolve_binding()`, `RepeatOverflow`.
- `backend/apps/forms/services/derivations.py` — `DERIVATIONS`, `PREDICATES` registries.
- `backend/apps/forms/management/commands/ingest_form_schema.py` — draft-schema generator + drift check.
- `data/forms/schemas/form_107.json` — curated, committed, version-pinned schema.
- `backend/apps/forms/tests/test_schema.py`, `test_fill_resolver.py`, `test_derivations.py`, `test_ingest_command.py`, `test_engine_form_agnostic.py`.
- `backend/apps/intake/tests/test_sofa_models.py`, `test_sofa_api.py`.
- `frontend/src/components/wizard/sofa/SOFAStep.tsx`, `SOFASection.tsx`, `sofaSections.ts`.
- `frontend/src/components/wizard/sofa/__tests__/SOFAStep.test.tsx`.
- `frontend/e2e/specs/sofa-journey.spec.ts`.
- `docs/superpowers/specs/2026-06-16-form-fill-engine-findings.md` — SP1→SP2 carry-forward (final task).

**Modify:**

- `backend/config/settings/base.py` — add `FORM_SCHEMAS_DIRECTORY`.
- `backend/apps/intake/models.py` — `SOFAReport`, `SOFAPriorIncome`, `SOFACreditorPayment`, `FormAnswer` (+ migration `0007`).
- `backend/apps/forms/models.py` — `GeneratedForm.template_version` (+ migration `0003`).
- `backend/apps/forms/services/form_107_generator.py` — `pdf_field_map()` delegates to resolver.
- `backend/apps/forms/views.py:315-337` — `download` catches `(KeyError, FileNotFoundError, RepeatOverflow)`; stamps `template_version`.
- `backend/apps/intake/serializers.py`, `views.py`, `urls.py` — SOFA endpoints.
- `backend/apps/intake/management/commands/seed_demo_data.py` — seed SOFA data for one persona.
- `frontend/src/api/client.ts` — `intakeAPI` SOFA methods.
- `frontend/src/types/api.ts` — SOFA types.
- `frontend/src/pages/IntakeWizard.tsx` — register SOFA step.

---

# Phase A — Engine core (headless; no curated schema required)

### Task 1: Settings + schema dataclasses + loader

**Files:**

- Modify: `backend/config/settings/base.py:235` (after `PDF_FORMS_DIRECTORY`)
- Create: `backend/apps/forms/schema.py`
- Test: `backend/apps/forms/tests/test_schema.py`

**Interfaces:**

- Produces: `FieldSpec` (frozen dataclass), `FormSchema` (frozen dataclass: `form_type`, `template_filename`, `template_version`, `fields: list[FieldSpec]`), `load_schema(form_type: str) -> FormSchema`, `settings.FORM_SCHEMAS_DIRECTORY`.

- [ ] **Step 1: Add the settings constant**

In `backend/config/settings/base.py`, immediately after the existing `PDF_FORMS_DIRECTORY` line:

```python
FORM_SCHEMAS_DIRECTORY = BASE_DIR.parent / "data" / "forms" / "schemas"
```

- [ ] **Step 2: Write the failing test**

Create `backend/apps/forms/tests/test_schema.py`:

```python
"""Tests for the form-schema loader and validator."""
import json
from pathlib import Path

import pytest

from apps.forms.schema import FieldSpec, FormSchema, load_schema

SAMPLE = {
    "form_type": "form_test",
    "template_filename": "b_107_0425-form.pdf",
    "template_version": "abc123",
    "fields": [
        {
            "pdf_field": "Debtor 1", "type": "text", "source": "derived",
            "on_states": [], "page": 1, "label": "Debtor name", "required": True,
            "conditional_on": None, "value": None, "rule": "full_name",
            "ingest_key": None, "binding": None, "repeat": None,
            "repeat_capacity": None, "row": None, "legal_review": False,
        }
    ],
}


def test_load_schema_returns_dataclass(tmp_path, settings):
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    (tmp_path / "form_test.json").write_text(json.dumps(SAMPLE))

    schema = load_schema("form_test")

    assert isinstance(schema, FormSchema)
    assert schema.template_version == "abc123"
    assert len(schema.fields) == 1
    assert isinstance(schema.fields[0], FieldSpec)
    assert schema.fields[0].rule == "full_name"


def test_load_schema_missing_file_raises(tmp_path, settings):
    settings.FORM_SCHEMAS_DIRECTORY = tmp_path
    with pytest.raises(FileNotFoundError):
        load_schema("does_not_exist")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.forms.schema'`.

- [ ] **Step 4: Write minimal implementation**

Create `backend/apps/forms/schema.py`:

```python
"""
Form-schema model + loader.

A schema is a committed JSON file under FORM_SCHEMAS_DIRECTORY describing every
fillable field of an AO template: its source, binding, applicability predicate,
and repeat-group membership. The FillResolver reads it to fill the PDF.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


@dataclass(frozen=True)
class FieldSpec:
    pdf_field: str
    type: str                      # text | checkbox | radio | choice
    source: str                    # constant | derived | asked | ingested | signature | TBD
    on_states: list[str]
    page: int
    label: str
    required: bool
    conditional_on: str | None     # PREDICATES key, or None = always applicable
    value: str | None              # source=constant
    rule: str | None               # source=derived → DERIVATIONS key
    ingest_key: str | None         # source=ingested (inert in SP1)
    binding: str | None            # source=asked
    repeat: str | None             # repeat-group name
    repeat_capacity: int | None    # pre-printed row count for the group
    row: int | None                # 1-based row index within the repeat group
    legal_review: bool


@dataclass(frozen=True)
class FormSchema:
    form_type: str
    template_filename: str
    template_version: str
    fields: list[FieldSpec]


def load_schema(form_type: str) -> FormSchema:
    """Load and parse data/forms/schemas/<form_type>.json. Raises FileNotFoundError."""
    path = Path(settings.FORM_SCHEMAS_DIRECTORY) / f"{form_type}.json"
    raw = json.loads(path.read_text())
    fields = [FieldSpec(**f) for f in raw["fields"]]
    return FormSchema(
        form_type=raw["form_type"],
        template_filename=raw["template_filename"],
        template_version=raw["template_version"],
        fields=fields,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_schema.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/config/settings/base.py backend/apps/forms/schema.py backend/apps/forms/tests/test_schema.py
git commit -m "feat(forms): schema dataclasses + loader for fill engine"
```

---

### Task 2: Schema validator

**Files:**

- Modify: `backend/apps/forms/schema.py`
- Test: `backend/apps/forms/tests/test_schema.py`

**Interfaces:**

- Consumes: `FormSchema`, `settings.PDF_FORMS_DIRECTORY`.
- Produces: `template_field_names(template_path: Path) -> set[str]`, `validate_schema(schema: FormSchema, derivations: set[str], predicates: set[str]) -> list[str]` (returns human-readable error strings; empty = valid).

- [ ] **Step 1: Write the failing test**

Append to `backend/apps/forms/tests/test_schema.py`:

```python
from apps.forms.schema import validate_schema


def _schema(**field_overrides):
    base = dict(SAMPLE["fields"][0])
    base.update(field_overrides)
    return FormSchema("form_test", "b_107_0425-form.pdf", "v1",
                      [FieldSpec(**base)])


def test_validate_flags_unknown_pdf_field():
    schema = _schema(pdf_field="NOT_A_REAL_FIELD_xyz", source="constant",
                     value="x", rule=None)
    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
    assert any("NOT_A_REAL_FIELD_xyz" in e for e in errors)


def test_validate_flags_tbd_source():
    schema = _schema(pdf_field="Debtor 1", source="TBD", rule=None)
    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
    assert any("TBD" in e for e in errors)


def test_validate_flags_unknown_rule():
    schema = _schema(pdf_field="Debtor 1", source="derived", rule="no_such_rule")
    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
    assert any("no_such_rule" in e for e in errors)


def test_validate_clean_schema_returns_empty():
    schema = _schema(pdf_field="Debtor 1", source="derived", rule="full_name")
    errors = validate_schema(schema, derivations={"full_name"}, predicates=set())
    assert errors == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_schema.py -v`
Expected: FAIL — `ImportError: cannot import name 'validate_schema'`.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/apps/forms/schema.py`:

```python
import pypdf


def template_field_names(template_path: Path) -> set[str]:
    """Return the set of AcroForm field names in a PDF template."""
    reader = pypdf.PdfReader(str(template_path))
    return set((reader.get_fields() or {}).keys())


def validate_schema(
    schema: FormSchema, derivations: set[str], predicates: set[str]
) -> list[str]:
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
            errors.append(
                f"unknown predicate {f.conditional_on!r} on {f.pdf_field!r}"
            )
        if f.repeat is not None and not f.repeat_capacity:
            errors.append(f"repeat group {f.repeat!r} missing repeat_capacity")
    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_schema.py -v`
Expected: PASS (6 passed). (Uses the real `b_107_0425-form.pdf` template, which must be present under `data/forms/pdfs/`.)

- [ ] **Step 5: Commit**

```bash
git add backend/apps/forms/schema.py backend/apps/forms/tests/test_schema.py
git commit -m "feat(forms): schema validator (template/TBD/rule/predicate checks)"
```

---

### Task 3: Ingestion command (draft schema + drift detection)

**Files:**

- Create: `backend/apps/forms/management/commands/ingest_form_schema.py`
- Test: `backend/apps/forms/tests/test_ingest_command.py`

**Interfaces:**

- Consumes: `FORM_TEMPLATES` (`apps/forms/services/pdf_filler.py`), `settings.PDF_FORMS_DIRECTORY`, `settings.FORM_SCHEMAS_DIRECTORY`.
- Produces: management command `ingest_form_schema <form_type>`; helper `build_draft_schema(form_type: str) -> dict`; `template_version_hash(template_path: Path) -> str`.

- [ ] **Step 1: Write the failing test**

Create `backend/apps/forms/tests/test_ingest_command.py`:

```python
"""Tests for the ingest_form_schema management command."""
import json

import pytest

from apps.forms.management.commands.ingest_form_schema import (
    build_draft_schema,
    template_version_hash,
)


def test_build_draft_schema_form_107_has_fields_all_tbd():
    draft = build_draft_schema("form_107")

    assert draft["form_type"] == "form_107"
    assert draft["template_filename"] == "b_107_0425-form.pdf"
    assert len(draft["template_version"]) == 64  # sha256 hex
    assert len(draft["fields"]) > 100            # 107 has 537 fillable fields
    assert all(f["source"] == "TBD" for f in draft["fields"])
    assert all("pdf_field" in f and "type" in f for f in draft["fields"])


def test_version_hash_is_stable(settings):
    from pathlib import Path

    p = Path(settings.PDF_FORMS_DIRECTORY) / "b_107_0425-form.pdf"
    assert template_version_hash(p) == template_version_hash(p)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_ingest_command.py -v`
Expected: FAIL — `ModuleNotFoundError` for the command module.

- [ ] **Step 3: Write minimal implementation**

Create `backend/apps/forms/management/commands/ingest_form_schema.py`:

```python
"""
Draft a form schema by introspecting a blank AO PDF template.

Emits a draft JSON under FORM_SCHEMAS_DIRECTORY with field names, type,
checkbox on-states, page, and tooltip label discovered from the AcroForm.
Leaves source/conditional_on/binding as "TBD" for human + UPL curation.
Re-running detects template drift via the version hash.

Usage: python manage.py ingest_form_schema form_107
"""
import hashlib
import json
from pathlib import Path

import pypdf
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.forms.services.pdf_filler import FORM_TEMPLATES


def template_version_hash(template_path: Path) -> str:
    return hashlib.sha256(template_path.read_bytes()).hexdigest()


def _field_type(obj) -> tuple[str, list[str]]:
    """Map a pypdf field object to (type, on_states)."""
    ft = obj.get("/FT")
    if ft == "/Btn":
        states = [s for s in (obj.get("/_States_") or []) if s != "/Off"]
        return ("checkbox", states or ["/Yes"])
    if ft == "/Ch":
        return ("choice", [])
    return ("text", [])


def build_draft_schema(form_type: str) -> dict:
    if form_type not in FORM_TEMPLATES:
        raise CommandError(f"unknown form_type {form_type!r}")
    filename = FORM_TEMPLATES[form_type]
    template_path = Path(settings.PDF_FORMS_DIRECTORY) / filename
    reader = pypdf.PdfReader(str(template_path))
    fields = reader.get_fields() or {}

    # page index per field name
    page_of: dict[str, int] = {}
    for i, page in enumerate(reader.pages, start=1):
        for annot in page.get("/Annots") or []:
            name = annot.get_object().get("/T")
            if name and name not in page_of:
                page_of[name] = i

    records = []
    for name, obj in fields.items():
        ftype, on_states = _field_type(obj)
        records.append({
            "pdf_field": name, "type": ftype, "source": "TBD",
            "on_states": on_states, "page": page_of.get(name, 1),
            "label": str(obj.get("/TU") or ""), "required": False,
            "conditional_on": None, "value": None, "rule": None,
            "ingest_key": None, "binding": None, "repeat": None,
            "repeat_capacity": None, "row": None, "legal_review": False,
        })
    return {
        "form_type": form_type,
        "template_filename": filename,
        "template_version": template_version_hash(template_path),
        "fields": records,
    }


class Command(BaseCommand):
    help = "Draft a form schema from a blank AO PDF template."

    def add_arguments(self, parser):
        parser.add_argument("form_type")

    def handle(self, *args, **opts):
        form_type = opts["form_type"]
        draft = build_draft_schema(form_type)
        out_dir = Path(settings.FORM_SCHEMAS_DIRECTORY)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{form_type}.json"

        if out_path.exists():
            committed = json.loads(out_path.read_text())
            if committed["template_version"] != draft["template_version"]:
                raise CommandError(
                    f"TEMPLATE DRIFT: {form_type} template hash changed. "
                    f"Reconcile {out_path} before overwriting."
                )
            self.stdout.write(f"{form_type}: schema up to date (no drift).")
            return

        out_path.write_text(json.dumps(draft, indent=2))
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote draft {out_path} ({len(draft['fields'])} fields, all source=TBD)."
            )
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_ingest_command.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/forms/management/commands/ingest_form_schema.py backend/apps/forms/tests/test_ingest_command.py
git commit -m "feat(forms): ingest_form_schema draft generator + drift detection"
```

---

### Task 4: Derivations + Predicates registries

**Files:**

- Create: `backend/apps/forms/services/derivations.py`
- Test: `backend/apps/forms/tests/test_derivations.py`

**Interfaces:**

- Consumes: `IntakeSession`, `DebtorInfo` (`first_name`/`middle_name`/`last_name`/`household_size`).
- Produces: `DERIVATIONS: dict[str, Callable[[IntakeSession], str]]`, `PREDICATES: dict[str, Callable[[IntakeSession], bool]]`.

- [ ] **Step 1: Write the failing test**

Create `backend/apps/forms/tests/test_derivations.py`:

```python
"""Tests for factual derivations and section predicates."""
import pytest

from apps.districts.models import District
from apps.forms.services.derivations import DERIVATIONS, PREDICATES
from apps.intake.models import DebtorInfo, IntakeSession


@pytest.fixture
def session(db):
    d = District.objects.create(
        code="ilnd", name="Northern District of Illinois",
        court_name="x", state="IL", filing_fee_chapter_7="338.00",
    )
    s = IntakeSession.objects.create(district=d, status="completed", current_step=6)
    DebtorInfo.objects.create(
        session=s, first_name="Maria", middle_name="", last_name="Torres",
        household_size=3,
    )
    return s


def test_full_name_collapses_blank_middle(session):
    assert DERIVATIONS["full_name"](session) == "Maria Torres"


def test_family_size_reads_household_size(session):
    assert DERIVATIONS["family_size"](session) == "3"


def test_chapter_constant(session):
    assert DERIVATIONS["chapter"](session) == "7"


def test_has_business_predicate_false_without_report(session):
    assert PREDICATES["has_business"](session) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_derivations.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.forms.services.derivations'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/apps/forms/services/derivations.py`:

```python
"""
Factual/clerical derivations (DERIVATIONS) and section-applicability
predicates (PREDICATES) for the fill engine.

UPL boundary: these encode ONLY facts and clerical transforms. No legal
conclusion (exemption-statute choice, debt priority, means-test verdict) may
live here — those are `asked` + `legal_review` in the schema.
"""
from __future__ import annotations

from collections.abc import Callable

from apps.intake.models import IntakeSession


def _full_name(session: IntakeSession) -> str:
    di = session.debtor_info
    return f"{di.first_name} {di.middle_name} {di.last_name}".replace("  ", " ").strip()


def _family_size(session: IntakeSession) -> str:
    return str(session.debtor_info.household_size)


DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
    "full_name": _full_name,
    "family_size": _family_size,
    "chapter": lambda s: "7",
    "debtor_type": lambda s: "Individual",
    "district_name": lambda s: s.district.name,
}


def _has_business(session: IntakeSession) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_business)


def _has_creditor_payments(session: IntakeSession) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_creditor_payments)


def _has_prior_income(session: IntakeSession) -> bool:
    report = getattr(session, "sofa_report", None)
    return bool(report and report.has_prior_income)


PREDICATES: dict[str, Callable[[IntakeSession], bool]] = {
    "has_business": _has_business,
    "has_creditor_payments": _has_creditor_payments,
    "has_prior_income": _has_prior_income,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_derivations.py -v`
Expected: PASS (4 passed). (`has_business` returns False because no `SOFAReport` exists yet — models land in Task 6; the `getattr` guard makes this safe.)

- [ ] **Step 5: Commit**

```bash
git add backend/apps/forms/services/derivations.py backend/apps/forms/tests/test_derivations.py
git commit -m "feat(forms): DERIVATIONS + PREDICATES registries (factual only)"
```

---

### Task 5: `GeneratedForm.template_version` (reproducibility)

**Files:**

- Modify: `backend/apps/forms/models.py` (after `form_data`, ~line 57)
- Create migration: `backend/apps/forms/migrations/0003_generatedform_template_version.py`
- Test: `backend/apps/forms/tests/test_form_views.py` (append one test)

**Interfaces:**

- Produces: `GeneratedForm.template_version` (CharField, blank, default `""`).

- [ ] **Step 1: Write the failing test**

Append to `backend/apps/forms/tests/test_form_views.py`:

```python
def test_generated_form_has_template_version_field(db, generated_form_factory):
    form = generated_form_factory()
    form.template_version = "abc123"
    form.save()
    form.refresh_from_db()
    assert form.template_version == "abc123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_form_views.py::test_generated_form_has_template_version_field -v`
Expected: FAIL — `AttributeError`/`FieldError: template_version`.

- [ ] **Step 3: Add the field**

In `backend/apps/forms/models.py`, after the `form_data` field:

```python
    template_version = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Schema/template version hash this form was filled against (reproducibility)",
    )
```

- [ ] **Step 4: Generate and apply the migration**

Run:

```bash
docker compose exec backend python manage.py makemigrations forms
docker compose exec backend python manage.py migrate
```

Expected: creates `0003_generatedform_template_version.py`.

- [ ] **Step 5: Run test to verify it passes**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_form_views.py::test_generated_form_has_template_version_field -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/forms/models.py backend/apps/forms/migrations/0003_generatedform_template_version.py backend/apps/forms/tests/test_form_views.py
git commit -m "feat(forms): add GeneratedForm.template_version for reproducibility"
```

---

### Task 6: Hybrid data model — SOFA models + FormAnswer

**Files:**

- Modify: `backend/apps/intake/models.py` (append the four models)
- Create migration: `backend/apps/intake/migrations/0007_sofa_models.py`
- Test: `backend/apps/intake/tests/test_sofa_models.py`

**Interfaces:**

- Consumes: `IntakeSession`, `EncryptedDecimalField`.
- Produces: `SOFAReport` (OneToOne `session`, related_name `sofa_report`; booleans `has_prior_income`/`has_creditor_payments`/`has_business`), `SOFAPriorIncome` (FK `report`, related_name `prior_income`; `year`, `source`, `gross_amount`), `SOFACreditorPayment` (FK `report`, related_name `creditor_payments`; `creditor_name`, `total_paid`, `dates_of_payments`), `FormAnswer` (FK `session`, related_name `form_answers`; `form_type`, `field_key`, `value`).

- [ ] **Step 1: Write the failing test**

Create `backend/apps/intake/tests/test_sofa_models.py`:

```python
"""Tests for the SOFA hybrid data model + FormAnswer store."""
from decimal import Decimal

import pytest

from apps.districts.models import District
from apps.intake.models import (
    FormAnswer,
    IntakeSession,
    SOFACreditorPayment,
    SOFAPriorIncome,
    SOFAReport,
)


@pytest.fixture
def session(db):
    d = District.objects.create(
        code="ilnd", name="N.D. Ill.", court_name="x", state="IL",
        filing_fee_chapter_7="338.00",
    )
    return IntakeSession.objects.create(district=d, status="in_progress", current_step=1)


def test_sofa_report_children_and_encrypted_amounts(session):
    report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
    SOFAPriorIncome.objects.create(
        report=report, year=2025, source="Wages", gross_amount=Decimal("42000.00")
    )
    SOFACreditorPayment.objects.create(
        report=report, creditor_name="Acme Card", total_paid=Decimal("1200.50")
    )

    report.refresh_from_db()
    assert session.sofa_report.has_creditor_payments is True
    assert report.prior_income.first().gross_amount == Decimal("42000.00")
    assert report.creditor_payments.first().total_paid == Decimal("1200.50")


def test_form_answer_unique_per_session_form_key(session):
    FormAnswer.objects.create(
        session=session, form_type="form_107", field_key="q9", value="No"
    )
    with pytest.raises(Exception):
        FormAnswer.objects.create(
            session=session, form_type="form_107", field_key="q9", value="Yes"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend python -m pytest apps/intake/tests/test_sofa_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'SOFAReport'`.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/apps/intake/models.py`:

```python
class SOFAReport(models.Model):
    """Statement of Financial Affairs (Form 107) structured data, per session.

    Boolean flags gate conditional sections (drive PREDICATES in the fill engine).
    """

    session = models.OneToOneField(
        IntakeSession, on_delete=models.CASCADE, related_name="sofa_report"
    )
    has_prior_income = models.BooleanField(default=True)
    has_creditor_payments = models.BooleanField(default=False)
    has_business = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sofa_reports"


class SOFAPriorIncome(models.Model):
    """A prior-year income row (Form 107 Q1/Q2)."""

    report = models.ForeignKey(
        SOFAReport, on_delete=models.CASCADE, related_name="prior_income"
    )
    year = models.PositiveIntegerField()
    source = models.CharField(max_length=255, help_text="e.g. Wages, Operating a business")
    gross_amount = EncryptedDecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "sofa_prior_income"
        ordering = ["-year"]


class SOFACreditorPayment(models.Model):
    """A payment-to-creditor row (Form 107 Q6/Q7)."""

    report = models.ForeignKey(
        SOFAReport, on_delete=models.CASCADE, related_name="creditor_payments"
    )
    creditor_name = models.CharField(max_length=255)
    total_paid = EncryptedDecimalField(max_digits=12, decimal_places=2)
    dates_of_payments = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "sofa_creditor_payments"


class FormAnswer(models.Model):
    """Generic key/value answer store for the sparse long tail of form fields."""

    session = models.ForeignKey(
        IntakeSession, on_delete=models.CASCADE, related_name="form_answers"
    )
    form_type = models.CharField(max_length=20)
    field_key = models.CharField(max_length=100)
    value = models.TextField(blank=True)

    class Meta:
        db_table = "form_answers"
        unique_together = [["session", "form_type", "field_key"]]
```

- [ ] **Step 4: Generate and apply the migration**

Run:

```bash
docker compose exec backend python manage.py makemigrations intake
docker compose exec backend python manage.py migrate
```

Expected: creates `0007_*.py` adding the four tables.

- [ ] **Step 5: Run test to verify it passes**

Run: `docker compose exec backend python -m pytest apps/intake/tests/test_sofa_models.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/apps/intake/models.py backend/apps/intake/migrations/0007_*.py backend/apps/intake/tests/test_sofa_models.py
git commit -m "feat(intake): SOFA hybrid data model + FormAnswer store"
```

---

### Task 7: Binding resolver

**Files:**

- Create: `backend/apps/forms/services/fill_resolver.py`
- Test: `backend/apps/forms/tests/test_fill_resolver.py`

**Interfaces:**

- Consumes: `SOFAReport`, `SOFACreditorPayment`, `FormAnswer`.
- Produces: `resolve_binding(binding: str, session: IntakeSession) -> str | list[str]` — `answer:<form_type>.<key>` → scalar str (or `""`); `sofa.<collection>[].<attr>` → `list[str]`; `sofa.<attr>` → scalar str.

- [ ] **Step 1: Write the failing test**

Create `backend/apps/forms/tests/test_fill_resolver.py`:

```python
"""Tests for the fill resolver: binding resolution, dispatch, repeats, UPL guard."""
from decimal import Decimal

import pytest

from apps.districts.models import District
from apps.forms.services.fill_resolver import resolve_binding
from apps.intake.models import (
    FormAnswer,
    IntakeSession,
    SOFACreditorPayment,
    SOFAReport,
)


@pytest.fixture
def session(db):
    d = District.objects.create(
        code="ilnd", name="N.D. Ill.", court_name="x", state="IL",
        filing_fee_chapter_7="338.00",
    )
    return IntakeSession.objects.create(district=d, status="in_progress", current_step=1)


def test_resolve_answer_binding(session):
    FormAnswer.objects.create(
        session=session, form_type="form_107", field_key="q9", value="No"
    )
    assert resolve_binding("answer:form_107.q9", session) == "No"


def test_resolve_answer_binding_missing_returns_empty(session):
    assert resolve_binding("answer:form_107.q9", session) == ""


def test_resolve_collection_binding_returns_list(session):
    report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
    SOFACreditorPayment.objects.create(
        report=report, creditor_name="Acme", total_paid=Decimal("100.00")
    )
    SOFACreditorPayment.objects.create(
        report=report, creditor_name="Beta", total_paid=Decimal("200.00")
    )
    vals = resolve_binding("sofa.creditor_payments[].creditor_name", session)
    assert vals == ["Acme", "Beta"]


def test_resolve_collection_binding_no_report_returns_empty_list(session):
    assert resolve_binding("sofa.creditor_payments[].creditor_name", session) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_fill_resolver.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.forms.services.fill_resolver'`.

- [ ] **Step 3: Write minimal implementation**

Create `backend/apps/forms/services/fill_resolver.py`:

```python
"""
Fill resolver — turns a FormSchema + IntakeSession into {pdf_field: str}.

Source priority is encoded per-field in the schema (constant/derived/asked/
ingested/signature). This module resolves `binding` references; resolve()
(Task 8) orchestrates dispatch, conditional sections, and repeat groups.
"""
from __future__ import annotations

from apps.intake.models import FormAnswer, IntakeSession


def resolve_binding(binding: str, session: IntakeSession) -> str | list[str]:
    """
    Resolve a schema `binding`:
      - "answer:<form_type>.<key>" → the FormAnswer value, or "" if absent
      - "sofa.<collection>[].<attr>" → list of str over the collection
      - "sofa.<attr>" → scalar str on the SOFAReport
    """
    binding = binding.strip()

    if binding.startswith("answer:"):
        form_type, _, key = binding[len("answer:"):].partition(".")
        ans = FormAnswer.objects.filter(
            session=session, form_type=form_type, field_key=key
        ).first()
        return ans.value if ans else ""

    if binding.startswith("sofa."):
        path = binding[len("sofa."):]
        report = getattr(session, "sofa_report", None)
        if "[]." in path:
            coll_name, _, attr = path.partition("[].")
            if report is None:
                return []
            return [str(getattr(row, attr)) for row in getattr(report, coll_name).all()]
        if report is None:
            return ""
        return str(getattr(report, path))

    raise ValueError(f"unrecognized binding: {binding!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_fill_resolver.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/forms/services/fill_resolver.py backend/apps/forms/tests/test_fill_resolver.py
git commit -m "feat(forms): binding resolver (answer + sofa collection/scalar)"
```

---

### Task 8: Fill resolver — dispatch, conditionals, repeats, UPL guard

**Files:**

- Modify: `backend/apps/forms/services/fill_resolver.py`
- Test: `backend/apps/forms/tests/test_fill_resolver.py`

**Interfaces:**

- Consumes: `FormSchema`/`FieldSpec` (Task 1), `DERIVATIONS`/`PREDICATES` (Task 4), `resolve_binding` (Task 7).
- Produces: `resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]`; `RepeatOverflow(Exception)` with attrs `form_type`, `group`, `capacity`, `actual`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/apps/forms/tests/test_fill_resolver.py`:

```python
from apps.forms.schema import FieldSpec, FormSchema
from apps.forms.services.fill_resolver import RepeatOverflow, resolve
from apps.intake.models import DebtorInfo


def _field(**kw):
    base = dict(
        pdf_field="F", type="text", source="constant", on_states=[], page=1,
        label="", required=False, conditional_on=None, value=None, rule=None,
        ingest_key=None, binding=None, repeat=None, repeat_capacity=None,
        row=None, legal_review=False,
    )
    base.update(kw)
    return FieldSpec(**base)


def _schema(fields):
    return FormSchema("form_107", "b_107_0425-form.pdf", "v1", fields)


def test_constant_and_derived_dispatch(session):
    DebtorInfo.objects.create(
        session=session, first_name="Maria", middle_name="", last_name="Torres",
        household_size=2,
    )
    schema = _schema([
        _field(pdf_field="Chapter", source="constant", value="7"),
        _field(pdf_field="Debtor 1", source="derived", rule="full_name"),
    ])
    out = resolve(schema, session)
    assert out["Chapter"] == "7"
    assert out["Debtor 1"] == "Maria Torres"


def test_conditional_section_skipped_when_predicate_false(session):
    schema = _schema([
        _field(pdf_field="BizName", source="constant", value="X",
               conditional_on="has_business"),
    ])
    # no SOFAReport → has_business False → field skipped
    assert "BizName" not in resolve(schema, session)


def test_none_value_dropped(session):
    schema = _schema([_field(pdf_field="Inert", source="ingested", ingest_key="x")])
    assert "Inert" not in resolve(schema, session)


def test_checkbox_emits_on_state(session):
    FormAnswer.objects.create(
        session=session, form_type="form_107", field_key="q1", value="yes"
    )
    schema = _schema([
        _field(pdf_field="Box", type="checkbox", source="asked",
               on_states=["/Yes"], binding="answer:form_107.q1"),
    ])
    assert resolve(schema, session)["Box"] == "/Yes"


def test_repeat_group_expands_rows(session):
    report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
    for name, amt in [("Acme", "100.00"), ("Beta", "200.00")]:
        SOFACreditorPayment.objects.create(
            report=report, creditor_name=name, total_paid=Decimal(amt)
        )
    schema = _schema([
        _field(pdf_field="Cred1", source="asked", repeat="cp", repeat_capacity=3,
               row=1, binding="sofa.creditor_payments[].creditor_name"),
        _field(pdf_field="Cred2", source="asked", repeat="cp", repeat_capacity=3,
               row=2, binding="sofa.creditor_payments[].creditor_name"),
        _field(pdf_field="Cred3", source="asked", repeat="cp", repeat_capacity=3,
               row=3, binding="sofa.creditor_payments[].creditor_name"),
    ])
    out = resolve(schema, session)
    assert out["Cred1"] == "Acme"
    assert out["Cred2"] == "Beta"
    assert "Cred3" not in out  # only two rows of data


def test_repeat_overflow_raises(session):
    report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
    for i in range(4):
        SOFACreditorPayment.objects.create(
            report=report, creditor_name=f"C{i}", total_paid=Decimal("1.00")
        )
    schema = _schema([
        _field(pdf_field="Cred1", source="asked", repeat="cp", repeat_capacity=3,
               row=1, binding="sofa.creditor_payments[].creditor_name"),
    ])
    with pytest.raises(RepeatOverflow):
        resolve(schema, session)


def test_legal_review_field_not_filled_without_answer(session):
    # derived legal_review field must NOT be silently filled
    schema = _schema([
        _field(pdf_field="Exemption", source="derived", rule="chapter",
               legal_review=True),
    ])
    assert "Exemption" not in resolve(schema, session)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_fill_resolver.py -v`
Expected: FAIL — `ImportError: cannot import name 'resolve'`.

- [ ] **Step 3: Write minimal implementation**

Append to `backend/apps/forms/services/fill_resolver.py`:

```python
from apps.forms.schema import FieldSpec, FormSchema
from apps.forms.services.derivations import DERIVATIONS, PREDICATES


class RepeatOverflow(Exception):
    """A bound collection exceeded its template's pre-printed row capacity."""

    def __init__(self, form_type: str, group: str, capacity: int, actual: int):
        self.form_type = form_type
        self.group = group
        self.capacity = capacity
        self.actual = actual
        super().__init__(
            f"{form_type}: repeat group {group!r} has {actual} rows but template "
            f"holds {capacity}. A continuation attachment is required."
        )


def _section_applies(field: FieldSpec, session: IntakeSession) -> bool:
    if field.conditional_on is None:
        return True
    pred = PREDICATES.get(field.conditional_on)
    return bool(pred and pred(session))


def _scalar_value(field: FieldSpec, session: IntakeSession) -> str | None:
    if field.source == "constant":
        return field.value
    if field.source == "derived":
        return DERIVATIONS[field.rule](session)
    if field.source == "asked":
        val = resolve_binding(field.binding, session)
        return val if isinstance(val, str) else None
    # ingested (inert in SP1) / signature → nothing
    return None


def _emit(field: FieldSpec, value: str) -> str | None:
    """Apply checkbox on-state semantics and string coercion. None = skip."""
    if value is None or value == "":
        return None
    if field.type in ("checkbox", "radio"):
        return field.on_states[0] if field.on_states else "/Yes"
    return str(value)


def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
    out: dict[str, str] = {}

    # Non-repeat fields
    for f in schema.fields:
        if f.repeat is not None:
            continue
        if not _section_applies(f, session):
            continue
        # UPL guard: legal_review fields fill only from an explicit asked answer
        if f.legal_review and f.source != "asked":
            continue
        emitted = _emit(f, _scalar_value(f, session))
        if emitted is not None:
            out[f.pdf_field] = emitted

    # Repeat groups
    groups: dict[str, list[FieldSpec]] = {}
    for f in schema.fields:
        if f.repeat is not None and _section_applies(f, session):
            groups.setdefault(f.repeat, []).append(f)

    for group_name, fields in groups.items():
        capacity = fields[0].repeat_capacity or 0
        resolved_cols = {
            f.pdf_field: resolve_binding(f.binding, session)
            for f in fields if f.binding
        }
        actual = max(
            (len(v) for v in resolved_cols.values() if isinstance(v, list)),
            default=0,
        )
        if actual > capacity:
            raise RepeatOverflow(schema.form_type, group_name, capacity, actual)
        for f in fields:
            vals = resolved_cols.get(f.pdf_field)
            if isinstance(vals, list) and f.row and f.row <= len(vals):
                emitted = _emit(f, str(vals[f.row - 1]))
                if emitted is not None:
                    out[f.pdf_field] = emitted

    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_fill_resolver.py -v`
Expected: PASS (all resolver tests green).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/forms/services/fill_resolver.py backend/apps/forms/tests/test_fill_resolver.py
git commit -m "feat(forms): fill resolver (dispatch, conditionals, repeats, UPL guard)"
```

---

# Phase B — Curate the Form 107 schema (SP1's real effort)

### Task 9: Draft, then curate `data/forms/schemas/form_107.json` section by section

> This is the bulk of SP1. The draft is mechanical; assigning `source`/`binding`/
> `conditional_on`/`repeat`/`legal_review` to ~537 fields is hand work. **Chunk by SOFA
> section — one section per work unit per context** (Execution discipline). The committed
> schema passing `validate_schema` with zero `TBD` is the gate.

**Files:**

- Create (via command, then hand-edit): `data/forms/schemas/form_107.json`
- Test: `backend/apps/forms/tests/test_schema.py` (append the live-schema gate)

**Interfaces:**

- Consumes: `ingest_form_schema` (Task 3), `validate_schema` (Task 2), `DERIVATIONS`/`PREDICATES` (Task 4), SOFA bindings (Task 6).

**Curation contract (per field):**
| field shape | `source` | how to fill the rest |
|---|---|---|
| debtor name / district / chapter | `derived` | `rule` = a `DERIVATIONS` key |
| fixed label/checkbox always-on | `constant` | `value` = literal (checkbox: `value` ignored, `on_states[0]` emitted) |
| prior-income & creditor-payment rows | `asked` | `repeat` group name, `row` 1..N, `repeat_capacity` = pre-printed rows, `binding` = `sofa.<collection>[].<attr>` |
| section gating yes/no + long-tail "No" answers | `asked` | `binding` = `answer:form_107.<key>`, `conditional_on` for dependent fields |
| exemption choice / debt priority / any legal conclusion | `asked` + `legal_review: true` | `binding` = `answer:form_107.<key>` — **never** `derived` |
| wet-signature / date-of-signing | `signature` | leave blank |

- [ ] **Step 1: Generate the draft**

Run: `docker compose exec backend python manage.py ingest_form_schema form_107`
Expected: `Wrote draft data/forms/schemas/form_107.json (537 fields, all source=TBD).`

- [ ] **Step 2: Inspect the field inventory in the sandbox (do NOT read the raw draft into context)**

Use `ctx_execute_file` on `data/forms/schemas/form_107.json` to print a per-page, per-type summary (counts, checkbox groups, numeric-suffix repeat candidates) — work from the summary, not the 537-record dump.

- [ ] **Step 3: Curate, one SOFA section at a time**

Worked example — the creditor-payments group (Form 107 Part 2, Q6/Q7). After identifying the three pre-printed creditor rows' AcroForm names from the summary, set each row's records like:

```jsonc
// creditor name, row 1 of 3
{ "pdf_field": "<row1 creditor name field>", "type": "text", "source": "asked",
  "on_states": [], "page": 3, "label": "Creditor name",
  "required": false, "conditional_on": "has_creditor_payments",
  "value": null, "rule": null, "ingest_key": null,
  "binding": "sofa.creditor_payments[].creditor_name",
  "repeat": "creditor_payments", "repeat_capacity": 3, "row": 1,
  "legal_review": false }
// total paid, row 1 of 3
{ "pdf_field": "<row1 total-paid field>", "type": "text", "source": "asked",
  "on_states": [], "page": 3, "label": "Total paid",
  "required": false, "conditional_on": "has_creditor_payments",
  "value": null, "rule": null, "ingest_key": null,
  "binding": "sofa.creditor_payments[].total_paid",
  "repeat": "creditor_payments", "repeat_capacity": 3, "row": 1,
  "legal_review": false }
```

Repeat for rows 2–3 (`"row": 2`/`3`). Apply the same procedure section by section: header constants (`derived`: `full_name`, `district_name`, `chapter`), prior-income rows (`binding: sofa.prior_income[].*`, `conditional_on: has_prior_income`), business section (`conditional_on: has_business`), and the long-tail yes/no questions (`binding: answer:form_107.<qkey>`). Commit after each section so a reviewer can gate one section at a time.

- [ ] **Step 4: Write the live-schema validation gate (the test that fails on any uncurated/typo'd field)**

Append to `backend/apps/forms/tests/test_schema.py`:

```python
from apps.forms.services.derivations import DERIVATIONS, PREDICATES


def test_form_107_schema_is_valid(db):
    schema = load_schema("form_107")
    errors = validate_schema(
        schema, derivations=set(DERIVATIONS), predicates=set(PREDICATES)
    )
    assert errors == [], f"form_107 schema invalid:\n" + "\n".join(errors)


def test_form_107_schema_has_no_tbd():
    schema = load_schema("form_107")
    assert all(f.source != "TBD" for f in schema.fields)
```

- [ ] **Step 5: Run the gate until green (iterate curation)**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_schema.py -v`
Expected: PASS once every field is curated and every `pdf_field`/`rule`/`predicate` resolves. Treat each failure as the to-do list.

- [ ] **Step 6: Commit**

```bash
git add data/forms/schemas/form_107.json backend/apps/forms/tests/test_schema.py
git commit -m "feat(forms): curated, version-pinned Form 107 schema"
```

---

# Phase C — Wire-up + coverage proof

### Task 10: Delegate Form 107 to the resolver; handle download errors; stamp version

**Files:**

- Modify: `backend/apps/forms/services/form_107_generator.py:409` (`pdf_field_map`)
- Modify: `backend/apps/forms/views.py:315-337` (`download`)
- Test: `backend/apps/forms/tests/test_download_action.py`

**Interfaces:**

- Consumes: `load_schema` (Task 1), `resolve`/`RepeatOverflow` (Task 8).

- [ ] **Step 1: Write the failing tests**

Append to `backend/apps/forms/tests/test_download_action.py`:

```python
from unittest.mock import patch

from apps.forms.services.fill_resolver import RepeatOverflow


def test_download_handles_missing_template(api_client_authed, generated_form_factory):
    form = generated_form_factory()
    with patch(
        "apps.forms.views.PDFFormFiller.fill", side_effect=FileNotFoundError("x.pdf")
    ):
        resp = api_client_authed.get(f"/api/forms/{form.id}/download/")
    assert resp.status_code == 500
    assert "detail" in resp.json()


def test_download_handles_repeat_overflow(api_client_authed, generated_form_factory):
    form = generated_form_factory()
    with patch(
        "apps.forms.registry.get_generator"
    ) as gg:
        gg.return_value.pdf_field_map.side_effect = RepeatOverflow(
            "form_121", "cp", 3, 5
        )
        resp = api_client_authed.get(f"/api/forms/{form.id}/download/")
    assert resp.status_code == 422
    assert "continuation" in resp.json()["detail"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_download_action.py -v`
Expected: FAIL — current `download` lets these propagate as unhandled 500s / has no 422 path.

- [ ] **Step 3: Delegate Form 107's map to the resolver**

Replace the body of `pdf_field_map` in `backend/apps/forms/services/form_107_generator.py` with:

```python
    def pdf_field_map(self) -> dict:
        """Map session data to Official Form 107 via the schema-driven resolver."""
        from apps.forms.schema import load_schema
        from apps.forms.services.fill_resolver import resolve

        return resolve(load_schema("form_107"), self.session)
```

- [ ] **Step 4: Handle download errors + stamp template_version**

In `backend/apps/forms/views.py`, update imports and the `download` action:

```python
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import RepeatOverflow
```

```python
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        """Fill the official AO PDF template with session data and stream it."""
        generated_form = self.get_object()
        generator = get_generator(generated_form.form_type, generated_form.session)
        try:
            field_map = generator.pdf_field_map()
        except NotImplementedError:
            return Response(
                {"error": "PDF download is not yet available for this form."},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
        except RepeatOverflow as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        try:
            pdf_bytes = PDFFormFiller().fill(generated_form.form_type, field_map)
        except (KeyError, FileNotFoundError):
            return Response(
                {"detail": "Form template is unavailable. Please contact support."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            generated_form.template_version = load_schema(
                generated_form.form_type
            ).template_version
        except FileNotFoundError:
            pass  # form not yet schema-migrated

        if generated_form.status == "generated":
            generated_form.status = "downloaded"
        generated_form.save()

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{generated_form.form_type}.pdf"'
        )
        return response
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_download_action.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/forms/services/form_107_generator.py backend/apps/forms/views.py backend/apps/forms/tests/test_download_action.py
git commit -m "feat(forms): Form 107 delegates to resolver; download handles errors + stamps version"
```

---

### Task 11: Coverage proof on a seeded persona (the headline numeric test)

**Files:**

- Modify: `backend/apps/intake/management/commands/seed_demo_data.py` (add SOFA data for one persona)
- Test: `backend/apps/forms/tests/test_coverage.py`

**Interfaces:**

- Consumes: `load_schema`, `resolve`, `_section_applies`, SOFA models, `FormAnswer`.

- [ ] **Step 1: Seed SOFA data for the coverage persona**

In `seed_demo_data.py`, for one persona's completed session, create a `SOFAReport(has_prior_income=True, has_creditor_payments=True)`, two `SOFAPriorIncome` rows, two `SOFACreditorPayment` rows, and `FormAnswer` rows for every `asked` long-tail key the curated schema references (the default is `"No"`). Set `household_size` explicitly.

- [ ] **Step 2: Write the failing test**

Create `backend/apps/forms/tests/test_coverage.py`:

```python
"""Headline proof: the resolver fills every applicable Form 107 field."""
import pytest
from django.core.management import call_command

from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.fill_resolver import _section_applies  # noqa: PLC2701
from apps.intake.models import IntakeSession


@pytest.fixture
def seeded(db):
    call_command("seed_demo_data", "--reset")
    # the SOFA-seeded persona's session (adjust the lookup to the seed's marker)
    return IntakeSession.objects.filter(sofa_report__isnull=False).first()


def test_resolver_fills_every_applicable_required_field(seeded):
    schema = load_schema("form_107")
    out = resolve(schema, seeded)

    applicable_required = [
        f for f in schema.fields
        if f.required
        and _section_applies(f, seeded)
        and f.source not in ("signature", "ingested")
        and not f.legal_review
    ]
    unresolved = [f.pdf_field for f in applicable_required if f.pdf_field not in out]
    assert unresolved == [], f"unresolved applicable fields: {unresolved}"


def test_resolved_field_count_jumps(seeded):
    out = resolve(load_schema("form_107"), seeded)
    # Was ~6 with the hand-authored map. Threshold finalized post-curation
    # (spec open question #2 = count of applicable fields for this persona).
    assert len(out) >= 50
```

- [ ] **Step 3: Run tests to verify they fail, then pass**

Run: `docker compose exec backend python -m pytest apps/forms/tests/test_coverage.py -v`
Expected: FAIL first (seed lacks SOFA data / threshold). Iterate the seed + curation until PASS. Set the `>= 50` threshold to the real applicable count once green.

- [ ] **Step 4: Record the coverage metric**

Add a one-off print (or a `--report` flag on the existing coverage diagnostic) that emits `applicable / total_fillable` for 107, and paste the number into the findings doc (Task 17).

- [ ] **Step 5: Commit**

```bash
git add backend/apps/intake/management/commands/seed_demo_data.py backend/apps/forms/tests/test_coverage.py
git commit -m "test(forms): Form 107 coverage proof on seeded SOFA persona"
```

---

# Phase D — SOFA backend endpoints

### Task 12: SOFA serializers, viewset, and route

**Files:**

- Modify: `backend/apps/intake/serializers.py` (append SOFA serializers)
- Modify: `backend/apps/intake/views.py` (append `SOFAReportViewSet`)
- Modify: `backend/apps/intake/urls.py` (register `sofa`)
- Test: `backend/apps/intake/tests/test_sofa_api.py`

**Interfaces:**

- Produces: `GET/POST/PATCH /api/intake/sofa/` upserting a `SOFAReport` by `session`, with nested `prior_income`, `creditor_payments`, and `answers` (replace-on-write, mirroring the existing IntakeSession assets/debts pattern).

- [ ] **Step 1: Write the failing test**

Create `backend/apps/intake/tests/test_sofa_api.py`:

```python
"""Tests for the SOFA upsert endpoint."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import IntakeSession

User = get_user_model()


@pytest.fixture
def client_and_session(db):
    user = User.objects.create_user(username="u", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    d = District.objects.create(
        code="ilnd", name="N.D. Ill.", court_name="x", state="IL",
        filing_fee_chapter_7="338.00",
    )
    session = IntakeSession.objects.create(
        user=user, district=d, status="in_progress", current_step=1
    )
    return client, session


def test_upsert_sofa_round_trips_encrypted_amounts(client_and_session):
    client, session = client_and_session
    payload = {
        "session": session.id,
        "has_creditor_payments": True,
        "prior_income": [{"year": 2025, "source": "Wages", "gross_amount": "42000.00"}],
        "creditor_payments": [
            {"creditor_name": "Acme", "total_paid": "1200.50", "dates_of_payments": "Jan"}
        ],
        "answers": [{"field_key": "q9", "value": "No"}],
    }
    resp = client.post("/api/intake/sofa/", payload, format="json")
    assert resp.status_code in (200, 201)

    get = client.get(f"/api/intake/sofa/?session={session.id}")
    body = get.json()
    row = body["results"][0] if "results" in body else body[0]
    assert row["creditor_payments"][0]["total_paid"] == "1200.50"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec backend python -m pytest apps/intake/tests/test_sofa_api.py -v`
Expected: FAIL — 404 (route not registered).

- [ ] **Step 3: Add serializers**

Append to `backend/apps/intake/serializers.py`:

```python
from .models import (
    FormAnswer,
    SOFACreditorPayment,
    SOFAPriorIncome,
    SOFAReport,
)


class SOFAPriorIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SOFAPriorIncome
        fields = ["id", "year", "source", "gross_amount"]


class SOFACreditorPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SOFACreditorPayment
        fields = ["id", "creditor_name", "total_paid", "dates_of_payments"]


class SOFAAnswerSerializer(serializers.Serializer):
    field_key = serializers.CharField()
    value = serializers.CharField(allow_blank=True)


class SOFAReportSerializer(serializers.ModelSerializer):
    prior_income = SOFAPriorIncomeSerializer(many=True, required=False)
    creditor_payments = SOFACreditorPaymentSerializer(many=True, required=False)
    answers = SOFAAnswerSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = SOFAReport
        fields = [
            "id", "session", "has_prior_income", "has_creditor_payments",
            "has_business", "prior_income", "creditor_payments", "answers",
        ]

    def _write_children(self, report, prior_income, creditor_payments, answers):
        # Replace-on-write (mirrors IntakeSession assets/debts MVP pattern).
        report.prior_income.all().delete()
        for row in prior_income:
            SOFAPriorIncome.objects.create(report=report, **row)
        report.creditor_payments.all().delete()
        for row in creditor_payments:
            SOFACreditorPayment.objects.create(report=report, **row)
        for ans in answers:
            FormAnswer.objects.update_or_create(
                session=report.session, form_type="form_107",
                field_key=ans["field_key"], defaults={"value": ans["value"]},
            )

    def create(self, validated_data):
        prior = validated_data.pop("prior_income", [])
        cred = validated_data.pop("creditor_payments", [])
        answers = validated_data.pop("answers", [])
        report, _ = SOFAReport.objects.update_or_create(
            session=validated_data["session"], defaults=validated_data
        )
        self._write_children(report, prior, cred, answers)
        return report
```

- [ ] **Step 4: Add the viewset and route**

Append to `backend/apps/intake/views.py`:

```python
from .models import SOFAReport
from .serializers import SOFAReportSerializer


class SOFAReportViewSet(viewsets.ModelViewSet):
    serializer_class = SOFAReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = SOFAReport.objects.filter(session__user=self.request.user)
        session_id = self.request.query_params.get("session")
        return qs.filter(session_id=session_id) if session_id else qs
```

In `backend/apps/intake/urls.py`, add the import and registration:

```python
from .views import (
    AssetViewSet, DebtViewSet, FeeWaiverViewSet, IntakeSessionViewSet,
    SOFAReportViewSet,
)
router.register(r"sofa", SOFAReportViewSet, basename="sofa-report")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker compose exec backend python -m pytest apps/intake/tests/test_sofa_api.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/intake/serializers.py backend/apps/intake/views.py backend/apps/intake/urls.py backend/apps/intake/tests/test_sofa_api.py
git commit -m "feat(intake): SOFA upsert endpoint (nested children + answers)"
```

---

# Phase E — Frontend SOFA ask-module

### Task 13: SOFA types + API client methods

**Files:**

- Modify: `frontend/src/types/api.ts` (append SOFA types)
- Modify: `frontend/src/api/client.ts` (append `intakeAPI.getSOFA` / `saveSOFA`)
- Test: `frontend/src/api/__tests__/client.test.ts` (append, or create if absent)

**Interfaces:**

- Produces: `SOFAReport`, `SOFAPriorIncome`, `SOFACreditorPayment` types; `intakeAPI.saveSOFA(data) → Promise<SOFAReport>`, `intakeAPI.getSOFA(sessionId) → Promise<SOFAReport | null>`.

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/api/__tests__/client.test.ts` (mirror existing fetch-mock style):

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { intakeAPI } from '../client';

describe('intakeAPI SOFA', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify({ id: 1, session: 7, creditor_payments: [] }), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
      )
    );
    localStorage.setItem('access_token', 'tok');
  });

  it('saveSOFA POSTs to /intake/sofa/', async () => {
    const r = await intakeAPI.saveSOFA({
      session: 7,
      has_creditor_payments: false,
      prior_income: [],
      creditor_payments: [],
      answers: [],
    });
    expect(r.session).toBe(7);
    const [url, opts] = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(String(url)).toContain('/intake/sofa/');
    expect(opts.method).toBe('POST');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- src/api/__tests__/client.test.ts`
Expected: FAIL — `intakeAPI.saveSOFA is not a function`.

- [ ] **Step 3: Add types and client methods**

Append to `frontend/src/types/api.ts`:

```ts
export interface SOFAPriorIncome {
  id?: number;
  year: number;
  source: string;
  gross_amount: string;
}
export interface SOFACreditorPayment {
  id?: number;
  creditor_name: string;
  total_paid: string;
  dates_of_payments?: string;
}
export interface SOFAAnswer {
  field_key: string;
  value: string;
}
export interface SOFAReport {
  id?: number;
  session: number;
  has_prior_income?: boolean;
  has_creditor_payments?: boolean;
  has_business?: boolean;
  prior_income: SOFAPriorIncome[];
  creditor_payments: SOFACreditorPayment[];
  answers?: SOFAAnswer[];
}
```

Append to `intakeAPI` in `frontend/src/api/client.ts`:

```ts
  /** Upsert the SOFA report. POST /api/intake/sofa/ */
  saveSOFA: async (data: SOFAReport): Promise<SOFAReport> => {
    return apiFetch<SOFAReport>('/intake/sofa/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /** Get the SOFA report for a session. GET /api/intake/sofa/?session={id} */
  getSOFA: async (sessionId: number): Promise<SOFAReport | null> => {
    const res = await apiFetch<{ results?: SOFAReport[] } | SOFAReport[]>(
      `/intake/sofa/?session=${sessionId}`,
    );
    const list = Array.isArray(res) ? res : (res.results ?? []);
    return list[0] ?? null;
  },
```

(Add `SOFAReport` to the existing `types/api` import in `client.ts`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- src/api/__tests__/client.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/api.ts frontend/src/api/client.ts frontend/src/api/__tests__/client.test.ts
git commit -m "feat(frontend): SOFA types + saveSOFA/getSOFA client methods"
```

---

### Task 14: SOFA step — config-driven sections, conditional rows, autosave

**Files:**

- Create: `frontend/src/components/wizard/sofa/sofaSections.ts` (section config — single source of truth)
- Create: `frontend/src/components/wizard/sofa/SOFASection.tsx` (one reusable gated section)
- Create: `frontend/src/components/wizard/sofa/SOFAStep.tsx` (aggregates sections, owns data)
- Modify: `frontend/src/pages/IntakeWizard.tsx` (register the step + autosave wiring)
- Test: `frontend/src/components/wizard/sofa/__tests__/SOFAStep.test.tsx`

**Interfaces:**

- Consumes: `SOFAReport` type, `intakeAPI.saveSOFA`, `useAutoSave`.
- Produces: `SOFAStep` with props `{ initialData?: SOFAReport; onDataChange: (d: SOFAReport) => void; onValidationChange: (v: boolean) => void }`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/wizard/sofa/__tests__/SOFAStep.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SOFAStep } from '../SOFAStep';

describe('SOFAStep', () => {
  it('hides creditor-payment rows until the section is toggled yes', () => {
    render(<SOFAStep onDataChange={vi.fn()} onValidationChange={vi.fn()} />);
    expect(screen.queryByLabelText(/creditor name/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('radio', { name: /yes/i, ...{} }));
    // first "Yes" belongs to the first gating section
    expect(screen.getAllByLabelText(/creditor name|source of income/i).length).toBeGreaterThan(0);
  });

  it('emits aggregated data on change', () => {
    const onDataChange = vi.fn();
    render(<SOFAStep onDataChange={onDataChange} onValidationChange={vi.fn()} />);
    expect(onDataChange).toHaveBeenCalled();
    const arg = onDataChange.mock.calls.at(-1)![0];
    expect(arg).toHaveProperty('creditor_payments');
    expect(arg).toHaveProperty('prior_income');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- src/components/wizard/sofa`
Expected: FAIL — module not found.

- [ ] **Step 3: Write the section config**

Create `frontend/src/components/wizard/sofa/sofaSections.ts`:

```ts
/**
 * SOFA section configuration — the single source of truth for the Form 107
 * ask-module. Each section gates row entry behind a yes/no question, mirroring
 * the resolver's conditional_on predicates. Keep keys in sync with the schema's
 * SOFAReport boolean flags and binding collections.
 */
export type SOFAFieldType = 'text' | 'number' | 'money';

export interface SOFARowField {
  key: string; // maps to a SOFA child-model attr
  label: string; // trauma-informed, 6-8th grade
  type: SOFAFieldType;
}

export interface SOFASectionConfig {
  /** SOFAReport boolean flag this section toggles */
  flag: 'has_prior_income' | 'has_creditor_payments' | 'has_business';
  /** which SOFAReport collection the rows write to */
  collection: 'prior_income' | 'creditor_payments' | null;
  gatingQuestion: string;
  rowNoun: string; // e.g. "income source", "payment"
  fields: SOFARowField[];
}

export const SOFA_SECTIONS: SOFASectionConfig[] = [
  {
    flag: 'has_prior_income',
    collection: 'prior_income',
    gatingQuestion:
      'Did you have income from a job, business, or other source in the last 2 years?',
    rowNoun: 'income source',
    fields: [
      { key: 'year', label: 'Year', type: 'number' },
      { key: 'source', label: 'Where the money came from (for example, wages)', type: 'text' },
      { key: 'gross_amount', label: 'Total amount before taxes', type: 'money' },
    ],
  },
  {
    flag: 'has_creditor_payments',
    collection: 'creditor_payments',
    gatingQuestion: 'In the last 90 days, did you pay any single creditor more than $600 total?',
    rowNoun: 'payment',
    fields: [
      { key: 'creditor_name', label: 'Who you paid', type: 'text' },
      { key: 'total_paid', label: 'Total amount you paid', type: 'money' },
      { key: 'dates_of_payments', label: 'When you paid (dates)', type: 'text' },
    ],
  },
];
```

- [ ] **Step 4: Write the reusable section component**

Create `frontend/src/components/wizard/sofa/SOFASection.tsx`:

```tsx
/**
 * SOFASection — a single gated SOFA section. Renders a yes/no gate; when "yes",
 * reveals add/remove row sub-forms. One component drives every section via config.
 */
import { useState } from 'react';
import { Button, FormField } from '../../common';
import type { SOFASectionConfig } from './sofaSections';

interface SOFASectionProps {
  config: SOFASectionConfig;
  rows: Record<string, string>[];
  enabled: boolean;
  onChange: (enabled: boolean, rows: Record<string, string>[]) => void;
}

export function SOFASection({ config, rows, enabled, onChange }: SOFASectionProps) {
  const [open, setOpen] = useState(enabled);

  const setEnabled = (val: boolean) => {
    setOpen(val);
    onChange(val, val ? rows : []);
  };
  const updateRow = (i: number, key: string, value: string) => {
    const next = rows.map((r, idx) => (idx === i ? { ...r, [key]: value } : r));
    onChange(true, next);
  };
  const addRow = () => onChange(true, [...rows, {}]);
  const removeRow = (i: number) =>
    onChange(
      true,
      rows.filter((_, idx) => idx !== i)
    );

  return (
    <fieldset>
      <legend>{config.gatingQuestion}</legend>
      <label>
        <input type="radio" name={config.flag} checked={open} onChange={() => setEnabled(true)} />{' '}
        Yes
      </label>
      <label>
        <input type="radio" name={config.flag} checked={!open} onChange={() => setEnabled(false)} />{' '}
        No
      </label>

      {open && (
        <div>
          {rows.map((row, i) => (
            <div key={i}>
              {config.fields.map((f) => (
                <FormField
                  key={f.key}
                  label={f.label}
                  value={row[f.key] ?? ''}
                  onChange={(e) => updateRow(i, f.key, e.target.value)}
                />
              ))}
              <Button variant="ghost" onClick={() => removeRow(i)}>
                Remove
              </Button>
            </div>
          ))}
          <Button variant="secondary" onClick={addRow}>
            Add another {config.rowNoun}
          </Button>
        </div>
      )}
    </fieldset>
  );
}
```

(Confirm `FormField`'s exact props against `frontend/src/components/common`; adapt `onChange`/`value` names if the shared component differs.)

- [ ] **Step 5: Write the step container**

Create `frontend/src/components/wizard/sofa/SOFAStep.tsx`:

```tsx
/**
 * SOFAStep — Form 107 (Statement of Financial Affairs) intake. Aggregates the
 * configured sections into a SOFAReport payload for autosave via intakeAPI.saveSOFA.
 */
import { useEffect, useState } from 'react';
import { UPLDisclaimer } from '../../compliance';
import { SOFA_SECTIONS } from './sofaSections';
import { SOFASection } from './SOFASection';
import type { SOFAReport } from '../../../types/api';

interface SOFAStepProps {
  initialData?: SOFAReport;
  onDataChange: (data: SOFAReport) => void;
  onValidationChange: (isValid: boolean) => void;
}

type SectionState = { enabled: boolean; rows: Record<string, string>[] };

export function SOFAStep({ initialData, onDataChange, onValidationChange }: SOFAStepProps) {
  const [sections, setSections] = useState<Record<string, SectionState>>(() =>
    Object.fromEntries(
      SOFA_SECTIONS.map((s) => [
        s.flag,
        {
          enabled: Boolean(initialData?.[s.flag]),
          rows: (initialData?.[s.collection ?? 'prior_income'] as Record<string, string>[]) ?? [],
        },
      ])
    )
  );

  useEffect(() => {
    const payload: SOFAReport = {
      session: initialData?.session ?? 0,
      has_prior_income: sections.has_prior_income?.enabled ?? false,
      has_creditor_payments: sections.has_creditor_payments?.enabled ?? false,
      has_business: sections.has_business?.enabled ?? false,
      prior_income: (sections.has_prior_income?.rows ?? []) as never,
      creditor_payments: (sections.has_creditor_payments?.rows ?? []) as never,
      answers: [],
    };
    onDataChange(payload);
    onValidationChange(true); // every section is optional; "No" is valid
  }, [sections, initialData, onDataChange, onValidationChange]);

  return (
    <div>
      <h2>Your Financial History</h2>
      <p>
        These questions come from the court&apos;s Statement of Financial Affairs. It is okay to
        answer &quot;No&quot; — most people do for many of them.
      </p>
      {SOFA_SECTIONS.map((config) => (
        <SOFASection
          key={config.flag}
          config={config}
          enabled={sections[config.flag].enabled}
          rows={sections[config.flag].rows}
          onChange={(enabled, rows) =>
            setSections((prev) => ({ ...prev, [config.flag]: { enabled, rows } }))
          }
        />
      ))}
      <UPLDisclaimer />
    </div>
  );
}
```

- [ ] **Step 6: Register the step in the wizard**

In `frontend/src/pages/IntakeWizard.tsx`:

- Insert into `WIZARD_STEPS` before `review`: `{ number: 6, label: 'Financial History', key: 'sofa' }` and renumber `review` to 7.
- Add `sofaData` state and include `currentStepKey === 'sofa' ? sofaData : ...` in the `currentStepData` chain.
- In `saveCurrentStepData`, add a `sofa` branch calling `intakeAPI.saveSOFA({ ...sofaData, session: session.id })`.
- Render `<SOFAStep .../>` when `currentStepKey === 'sofa'`, wired like the other steps.

- [ ] **Step 7: Run tests + lint to verify they pass**

Run: `cd frontend && npm test -- src/components/wizard/sofa && npm run lint:fix && npm run format`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/wizard/sofa/ frontend/src/pages/IntakeWizard.tsx
git commit -m "feat(frontend): SOFA ask-module (config-driven gated sections + autosave)"
```

---

### Task 15: E2E — a persona completes SOFA and Form 107 reflects it

**Files:**

- Create: `frontend/e2e/specs/sofa-journey.spec.ts`
- (Optionally) Create: `frontend/e2e/pages/SOFAPage.ts` (page object, following the existing pattern)

**Interfaces:** Consumes the existing API-based auth + page-object helpers in `frontend/e2e/`.

- [ ] **Step 1: Write the E2E spec**

Following the existing persona-journey pattern (API login → set tokens → navigate), drive: open the wizard, reach the Financial History step, answer the creditor-payments gate "Yes", add a payment, advance, generate Form 107, download it, and assert the response is a PDF (200, `application/pdf`).

- [ ] **Step 2: Run it**

Run: `cd frontend && npm run e2e -- sofa-journey`
Expected: PASS (green against `docker compose` services).

- [ ] **Step 3: Commit**

```bash
git add frontend/e2e/specs/sofa-journey.spec.ts frontend/e2e/pages/SOFAPage.ts
git commit -m "test(e2e): SOFA journey — fill, generate, download Form 107"
```

---

# Phase F — SP2 handoff

### Task 16: Form-agnostic acceptance test (the SP2 contract)

**Files:**

- Create: `backend/apps/forms/tests/test_engine_form_agnostic.py`

**Interfaces:** Consumes `build_draft_schema`, `validate_schema`, `resolve`.

- [ ] **Step 1: Write the test**

Create `backend/apps/forms/tests/test_engine_form_agnostic.py`:

```python
"""The engine is not Form-107-special-cased: it operates on a second,
uncurated form's metadata. This is the contract that makes SP2 'curate the
next schema', not 'rebuild the engine'."""
import pytest

from apps.districts.models import District
from apps.forms.management.commands.ingest_form_schema import build_draft_schema
from apps.forms.schema import FormSchema, FieldSpec, validate_schema
from apps.forms.services.derivations import DERIVATIONS, PREDICATES
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import IntakeSession


def test_ingest_runs_on_a_second_form():
    draft = build_draft_schema("schedule_j")          # any other AO template
    assert len(draft["fields"]) > 0
    assert all(f["source"] == "TBD" for f in draft["fields"])


def test_validate_flags_uncurated_draft():
    draft = build_draft_schema("schedule_j")
    schema = FormSchema(**{**draft, "fields": [FieldSpec(**f) for f in draft["fields"]]})
    errors = validate_schema(schema, set(DERIVATIONS), set(PREDICATES))
    assert any("TBD" in e for e in errors)            # uncurated → flagged, not silent


def test_resolver_noops_on_empty_schema(db):
    d = District.objects.create(
        code="ilnd", name="x", court_name="x", state="IL", filing_fee_chapter_7="1.00"
    )
    s = IntakeSession.objects.create(district=d, status="in_progress", current_step=1)
    empty = FormSchema("form_x", "b_107_0425-form.pdf", "v1", [])
    assert resolve(empty, s) == {}
```

- [ ] **Step 2: Run + commit**

```bash
docker compose exec backend python -m pytest apps/forms/tests/test_engine_form_agnostic.py -v
git add backend/apps/forms/tests/test_engine_form_agnostic.py
git commit -m "test(forms): engine is form-agnostic (SP2 contract)"
```

---

### Task 17: Carry-forward findings doc (seeds SP2's brainstorm)

**Files:**

- Create: `docs/superpowers/specs/2026-06-16-form-fill-engine-findings.md`

- [ ] **Step 1: Write the findings doc**

Capture, from the actual SP1 build: per-section curation effort for 107; any `binding`-grammar deltas beyond `answer:` + `sofa.<coll>[].<attr>`; whether the structured-models-vs-`FormAnswer` split held (which sections needed structure); how repeat-overflow resolved in practice; any missing `source`/predicate types discovered; and the **final 107 coverage metric** (`applicable / total_fillable`). End with the explicit next action: _SP2 begins with `brainstorming` seeded by this doc → design spec → `writing-plans`._

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-06-16-form-fill-engine-findings.md
git commit -m "docs(forms): SP1 findings — carry-forward to SP2"
```

---

## Final verification (run after all tasks)

1. `docker compose exec backend python -m pytest apps/forms apps/intake -v` → all green.
2. `cd frontend && npm test && npm run e2e` → green.
3. `docker compose exec backend python manage.py ingest_form_schema form_107` → "schema up to date (no drift)."
4. `GET /api/forms/<107-id>/download/` for the seeded persona → open the PDF: section checkboxes selected, repeating creditor/income rows populated, inapplicable sections blank.
5. Confirm the coverage metric recorded in the findings doc reflects the real jump from ~6.

---

## Self-Review (writing-plans checklist)

**Spec coverage** — every spec component maps to a task: schema artifact → T9; ingestion → T3; loader/validator → T1/T2; resolver → T7/T8; derivations+predicates → T4; hybrid data model → T6; frontend SOFA module → T13/T14/T15; wire-up (delegation, download exceptions, template_version) → T5/T10; curation/section-chunking → T9; SP2 handoff (form-agnostic test + findings) → T16/T17. Test strategy items map to T2, T8, T6/T12, T11, T16, T8/T10.

**Type consistency** — `FieldSpec` field names are identical across T1 (definition), T3 (draft records), T8 (resolver), and T9 (curation): `pdf_field, type, source, on_states, page, label, required, conditional_on, value, rule, ingest_key, binding, repeat, repeat_capacity, row, legal_review`. `resolve_binding`/`resolve`/`RepeatOverflow` names match between T7, T8, T10. `SOFAReport`/`SOFA*`/`FormAnswer` related-names (`sofa_report`, `prior_income`, `creditor_payments`, `form_answers`) are consistent across T6, T7, T11, T12. `intakeAPI.saveSOFA`/`getSOFA` match between T13 and T14.

**Open items the implementer resolves in-task (not placeholders):** the `>= 50` coverage threshold (T11 Step 3 — set to the real applicable count once the schema is curated); exact AO field names for 107 rows (T9 — produced by the ingest command, not guessable in advance); `FormField` prop names (T14 Step 4 — confirm against the shared component). These are flagged with the verification that resolves each.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-16-form-fill-engine.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Fits this plan's per-section chunking and context-management constraints.

**2. Inline Execution** — execute tasks in this session using `executing-plans`, batch execution with checkpoints for review.

**Which approach?**
