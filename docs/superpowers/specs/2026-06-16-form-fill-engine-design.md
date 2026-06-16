# Schema-Driven Form-Fill Engine — Design Spec (SP1)

**Date:** 2026-06-16
**Status:** Approved (brainstorm with founder) — pending implementation plan via `writing-plans`
**Branch:** `feature/form-fill-engine`
**Scope:** SP1 of a 5-sub-project program. Build the fill-engine infrastructure and prove it end-to-end on **Form 107 (Statement of Financial Affairs)**.

---

## Problem

A field-coverage audit (session 200, all 13 generators) found generated forms are **only ~4% filled**: of **2,161** fillable fields across the AO templates, the hand-authored `pdf_field_map()` methods populate just **102**, and only **7** of 109 mapped keys are even wrong.

So this is **not** a PDF-mapping bug. The root cause — confirmed by the founder — is **intake depth**: ~95% of fields have no data behind them because the wizard never gathers them, and ~489 checkbox/radio fields are never set to their on-state. Another pass of hand-tuning `pdf_field_map()` would optimize the wrong layer.

The forms also carry a latent **reproducibility risk** (CLAUDE.md technical risk #2, "Form Version Drift"): `GeneratedForm` stores only `form_type`, and the template is resolved at download time via `FORM_TEMPLATES[form_type]`. When the AO revises a form, historical downloads silently shift to the new revision — a legal artifact stops being reproducible.

## Goals

1. Replace hand-authored per-generator field maps with a **committed, version-pinned, UPL-reviewed per-form schema** read by a single generic resolver.
2. Gather the **required + applicable** data the forms actually demand — conditionally, never asking for data that does not apply.
3. Establish a **source priority** for every field: **presume/derive → ingest → ask.**
4. Prove the abstraction on the **hardest** form (107: 537 fields, ~70 questions, heavy repeating rows, mostly conditional). If it survives 107, it survives all 13.
5. Subsume three open review-backlog items into the engine (field-map sanitization, download exception handling, form-version pinning).

## Non-Goals (deferred to SP2–SP5)

- The other 12 forms' schemas and wiring (**SP5**: schema curation ×13 + legal/UPL review).
- Document-ingestion extraction — the `ingested` source type and `ingest_key` are **inert** in SP1 (**SP3**).
- Schedule A/B granularity and Schedule C exemption-statute modeling (**SP2**).
- Ask-modules and the conditional engine for forms beyond 107 (**SP4**).

## Decisions (from brainstorming)

| Decision                  | Choice                                                                                                                      |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Field demand scope        | Full Chapter 7 required filing set, **required + applicable only** (conditional/branching)                                  |
| Source priority per field | presume/derive → ingest (forms + documents, layered) → ask                                                                  |
| Backbone                  | Committed, version-pinned, UPL-reviewed per-form **schema**, drafted by ingesting blank AO PDFs, read by a generic resolver |
| Storage                   | **Hybrid** — structured encrypted models for big/sensitive domains, a generic answer store for the sparse long tail         |
| First proof               | Engine built and proven **end-to-end on Form 107 (SOFA)**                                                                   |

---

## Architecture

```
blank AO PDF ──ingest_form_schema──▶ data/forms/schemas/form_107.json   (committed, version-pinned)
                                          │ per field: {pdf_field, type, on_states, page, label,
                                          │   required, conditional_on, source, value|rule|ingest_key|binding,
                                          │   repeat, legal_review}
                                          ▼
 IntakeSession + SOFAReport(+children) + FormAnswer ──▶ FillResolver(schema, session) ──▶ {pdf_field: str}
        ▲ ask layer (SOFA module)   ▲ derivations (factual only)         │ skips inapplicable sections,
                                                                          │ expands repeating rows,
                                                                          ▼ emits correct checkbox on-states
                                                                    PDFFormFiller.fill()
```

The resolver **replaces** the per-generator `pdf_field_map()` body for migrated forms; `form_107_generator.pdf_field_map()` delegates to it. The existing thin hand-authored maps stay as the fallback for the 12 not-yet-migrated forms (they still satisfy the `pdf_field_map() -> dict` interface that `registry.get_generator` and `views.download` already depend on).

### Why a schema, not more Python maps

A JSON schema is **inspectable, diffable, and re-ingestable**. The ingestion command can regenerate a draft from the live template and diff it against the committed schema to detect AO drift; a UPL reviewer can read the schema without reading Python; and the resolver becomes 13× less code to audit because there is exactly one fill path.

---

## Components

All paths relative to repo root `/Volumes/Containers/DigniFi`.

### 1. Schema artifact — `data/forms/schemas/form_107.json`

Committed, version-pinned. Top level pins `template_filename` and a `template_version` hash (sha256 of the template bytes). Per-field record:

```jsonc
{
  "pdf_field": "<exact AcroForm field name>",
  "type": "text|checkbox|radio|choice",
  "on_states": ["/Yes"], // checkbox/radio: the value that means "on"
  "page": 3,
  "label": "<tooltip /TU text>",
  "required": true,
  "conditional_on": "has_business", // predicate key, or null = always applicable
  "source": "constant|derived|ingested|asked|signature",
  "value": "...", // source=constant
  "rule": "full_name", // source=derived → key in derivations.DERIVATIONS
  "ingest_key": "paystub.gross", // source=ingested → inert in SP1
  "binding": "sofa.creditor_payments[].total_paid | answer:107.q9", // source=asked
  "repeat": "sofa.creditor_payments", // rowed group; resolver iterates the bound collection
  "repeat_capacity": 3, // pre-printed rows for this group; overflow fails loud, never truncates
  "legal_review": false, // true → only filled from an explicit confirmed answer
}
```

A new setting locates these:

```python
# config/settings/base.py (sibling of the existing PDF_FORMS_DIRECTORY)
FORM_SCHEMAS_DIRECTORY = BASE_DIR.parent / "data" / "forms" / "schemas"
```

### 2. Ingestion command — `backend/apps/forms/management/commands/ingest_form_schema.py`

`python manage.py ingest_form_schema <form_type>` reads the template via `pypdf` and emits a **draft** schema:

- field names; `/FT` → `type`; checkbox `/_States_` → `on_states`; `/TU` → `label`; page index; repeat-group inference from numeric field-name suffixes.
- Leaves `source`, `conditional_on`, `binding` as `"TBD"` for human + UPL curation.
- Re-runnable: diffs the freshly-ingested draft against the committed schema and **fails loudly** if the `template_version` hash changed (drift detection).

### 3. Schema loader / validator — `backend/apps/forms/schema.py`

```python
@dataclass(frozen=True)
class FieldSpec:
    pdf_field: str
    type: str
    source: str
    on_states: list[str]
    page: int
    label: str
    required: bool
    conditional_on: str | None
    value: str | None
    rule: str | None
    ingest_key: str | None
    binding: str | None
    repeat: str | None
    legal_review: bool

@dataclass(frozen=True)
class FormSchema:
    form_type: str
    template_filename: str
    template_version: str
    fields: list[FieldSpec]

def load_schema(form_type: str) -> FormSchema: ...
def validate_schema(schema: FormSchema, template_path: Path) -> list[str]: ...  # returns error strings
```

`validate_schema` asserts: every `pdf_field` exists in the live template (catches typos/drift at **test time**), no `source: "TBD"` remains, and every `rule`/`binding` target resolves to a real derivation key or model path.

### 4. Fill resolver — `backend/apps/forms/services/fill_resolver.py`

```python
def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]: ...
```

Per field:

1. Evaluate `conditional_on` via the **predicate registry** `PREDICATES` (component 5); if the named predicate returns false, **skip the whole section** (its fields stay blank). `conditional_on: null` = always applicable. A `conditional_on` naming a key absent from `PREDICATES` is a schema-validation error (caught in `validate_schema`), never a silent skip.
2. Dispatch on `source`:
   - `constant` → `value`
   - `derived` → `derivations.DERIVATIONS[rule](session)`
   - `asked` → read `binding` (structured model path **or** `answer:<form>.<key>` in the `FormAnswer` store)
   - `ingested` → **inert in SP1** (returns nothing; reserved for SP3)
   - `signature` → blank (wet/e-signature handled outside the engine)
3. Expand `repeat` groups by iterating the bound collection, filling row _i_'s fields up to the group's `repeat_capacity` (the number of pre-printed rows in the template). **Overflow is not silently truncated** — see "Repeat-row overflow" below.
4. **Coerce every value to `str`; drop `None`.** (subsumes backlog item #1: field-map sanitization — fixes the `None`/`Decimal` → `"None"` leak in `pdf_filler.py`.)
5. Emit checkbox/radio values as the field's `on_states[0]`.
6. **UPL guardrail:** `legal_review: true` fields are filled **only** from an explicit user-confirmed answer, never silently derived.

**Repeat-row overflow (sworn-document safety).** AO templates have a fixed number of pre-printed rows; the _current_ thin map silently does `[:3]`. On a sworn SOFA, a dropped creditor payment is a material omission. For SP1 the resolver **must not truncate silently** when a bound collection exceeds `repeat_capacity`: it raises a typed `RepeatOverflow(form_type, group, capacity, actual)` that the download path surfaces (a handled error telling the user the form needs a continuation attachment). A proper continuation-page generator is deferred to a later sub-project; the SP1 requirement is _fail loud, never silently drop a sworn entry_.

### 5. Derivations & predicates — `backend/apps/forms/services/derivations.py`

```python
DERIVATIONS: dict[str, Callable[[IntakeSession], str]]   # source=derived → a field value
PREDICATES:  dict[str, Callable[[IntakeSession], bool]]  # conditional_on → applies this section?
```

`DERIVATIONS` holds **factual/clerical** value functions only: `full_name`, `county_from_zip`, `family_size`, `prior_two_year_income`, `summary_total`, chapter/debtor-type constants.

`PREDICATES` holds the section-applicability functions the resolver calls for `conditional_on` (e.g. `has_business`, `had_prior_address`, `has_dependents`). Keeping them a named registry — parallel to `DERIVATIONS`, not ad-hoc `getattr(session, ...)` — means `validate_schema` can assert every `conditional_on` key resolves, and a UPL reviewer can read the applicability logic in one file.

**UPL boundary (hard rule):** no legal conclusions. Exemption-statute choice, debt-priority classification, and means-test verdicts are **never** derivations — they are `asked` + `legal_review: true`. This is the information-vs-advice line that the entire product depends on.

### 6. Hybrid data model — `backend/apps/intake/models.py` (+ migration `0007`)

**Structured** (always/often-applicable, PII-bearing — encrypted amounts via the existing `EncryptedDecimalField` from `apps/intake/fields.py`):

- `SOFAReport(session OneToOne)`
- `SOFAPriorIncome` (child rows: year, source, gross amount)
- `SOFACreditorPayment` (child rows: creditor, dates, total paid)

**Generic** (the mostly-"No" long tail — lawsuits, transfers, gifts, losses — until a section proves it needs structure):

- `FormAnswer(session FK, form_type, field_key, value)` — unique on `(session, form_type, field_key)`.

The resolver reads both via `binding`: a dotted path like `sofa.creditor_payments[].total_paid` resolves against the structured models; `answer:107.q9` resolves against `FormAnswer`.

### 7. Form 107 ask-module (frontend) — `frontend/src/components/wizard/sofa/`

Conditional SOFA intake as a new wizard surface (a `WIZARD_STEPS` entry in `frontend/src/pages/IntakeWizard.tsx:37`, or a dedicated `/intake/sofa` route under the shared `IntakeLayout`/`Outlet`). Behavior:

- Gating yes/no per SOFA section; row sub-forms revealed **only** when the section applies (mirrors the resolver's `conditional_on`).
- Reuses the existing autosave/resume hook `useAutoSave<T>({ data, onSave, debounceMs?, enabled? })` (`frontend/src/hooks/useAutoSave.ts`) and trauma-informed copy/components.
- Persists via new SOFA endpoints (extend `api.intake` in `frontend/src/api/client.ts`, following the `updateSession(id, {...})` PATCH pattern).

### 8. Wire-up

- `form_107_generator.pdf_field_map()` delegates to `resolve(load_schema("form_107"), self.session)`.
- `views.py` `download` action adds `except (KeyError, FileNotFoundError, RepeatOverflow)` → handled error with a `detail` body (subsumes backlog item #2: currently only `NotImplementedError` is caught, so unknown `form_type` / missing template propagate as unhandled 500s). `RepeatOverflow` returns a `detail` that names the section needing a continuation attachment.
- `GeneratedForm` gains `template_version` CharField (forms migration `0003`); the resolver/download path stamps it from the schema so a download is reproducible against the exact template revision (subsumes backlog item #3: form-version drift).

---

## Curation & section chunking (SP1's real effort)

Ingestion produces a _draft_; **curating Form 107 is the bulk of SP1**, not a one-line step. ~537 fields / ~70 questions each need `source`, `binding`/`rule`/`value`, `conditional_on`, `repeat`/`repeat_capacity`, and `legal_review` assigned by hand.

- **Unit of work = one SOFA section/question, not the whole form.** Each section is curated, validated, and tested independently. This is both the task boundary for the plan and the context boundary for execution (never hold all 537 records at once).
- **Ownership:** the engineer first-passes every field; the **`legal_review: true` subset and every `conditional_on` predicate** are flagged for founder/UPL review before commit — these are the information-vs-advice fault lines.
- **Drift gate:** the committed schema's `template_version` hash is the contract; re-ingestion that changes it fails CI until the schema is reconciled.

## Handoff to SP2 (how SP1 completion feeds the next sub-project)

The feedback mechanism is **an architectural contract plus a deltas doc**, not automation:

1. **Form-agnostic engine, proven.** The `Form-agnostic acceptance` test (Test Strategy) is the durable contract: `ingest_form_schema`, `schema.py`, and `fill_resolver` are **not** 107-special-cased, so SP2 is "curate the next schema," not "rebuild the engine." The schema JSON format is the stable interface between every sub-project.
2. **Final SP1 task writes a carry-forward note** — `docs/superpowers/specs/2026-06-16-form-fill-engine-findings.md` — capturing what SP2's brainstorm needs: actual per-section curation effort, any `binding`-grammar deltas, whether the structured-models-vs-`FormAnswer` split held (which sections needed structure), how repeat-overflow resolved in practice, any missing `source`/predicate types discovered, and the final 107 coverage metric.
3. **Handoff is the established cycle, made explicit:** SP2 begins with `brainstorming` **seeded by that findings note** → design spec → `writing-plans` → execution. No cron/trigger (over-engineering) — a documented next-action, owned by the carry-forward note.

---

## Global Constraints (carried into the plan header verbatim)

- **Backend:** Python 3.11, Django 5.0, DRF. **pypdf 6.13** (3.17 raises `KeyError /AP`).
- **Frontend:** React 19, Vite 7, TypeScript, Context API (no Redux).
- **Encryption:** financial amounts use `EncryptedDecimalField` (`apps/intake/fields.py`); never store amounts in plaintext.
- **UPL:** legal information, never advice. `legal_review: true` fields are filled only from an explicit confirmed answer; no derivation may encode a legal conclusion. Disclaimers preserved at every decision point.
- **Schemas are committed + version-pinned.** A schema whose `template_version` hash no longer matches its template must fail tests, not silently fill.
- **DRF pagination** returns `{count, results}` — frontend guards with `Array.isArray`.
- **household_size** must be set explicitly on any seeded/scripted `DebtorInfo` (default=1 is silently wrong).
- **Lint:** `ruff==0.8.5` (matches CI/container pin); frontend `npm run lint:fix && npm run format`.
- **Accessibility:** WCAG 2.1 AA; trauma-informed, 6th–8th grade reading level for all new copy.

### Execution discipline — context management (carried into the plan, applies to every task)

The 537-field surface is exactly the kind of data that floods a context window. The plan must enforce:

- **Chunk by section.** One SOFA section = one task. Never load all field records, or the full schema, into a single task's context. (Same boundary as Curation above — they reinforce.)
- **Process PDF AcroForm metadata in the sandbox.** Inspect raw `pypdf` field dumps with `ctx_execute_file` / `ctx_execute` and emit summaries; never read a raw field dump into conversation context.
- **The schema JSON is the source of truth, not the conversation.** Each task reads only the field slice it needs from the committed schema.
- **Subagent-driven execution** (recommended for this plan): one fresh subagent per section/component with review between — the `writing-plans` bite-sized task structure already supports this.

---

## Test Strategy (intent-encoding — CLAUDE.md Rule 9)

- **Schema validation:** every `form_107.json` `pdf_field` exists in the live `b_107_0425-form.pdf`; no `TBD` source remains; every `rule`, `binding`, and `conditional_on` target resolves (to a `DERIVATIONS`/`PREDICATES` key or a real model path); every `repeat` group has a `repeat_capacity`.
- **Resolver units:** one test per `source` type; conditional section skipped when its predicate is false; repeating group expands N rows; checkbox emits its on-state; `None`/non-`str` values coerced to `str`/dropped.
- **Repeat overflow:** a bound collection larger than `repeat_capacity` raises `RepeatOverflow`, never silently truncates.
- **Data model + endpoint:** SOFA models persist; encrypted amounts round-trip through `EncryptedDecimalField`; SOFA PATCH endpoints accept and re-read data.
- **Resolver completeness (the numeric proof — proves the _engine_, not the schema):** for a seeded filer with real SOFA data, **every field the schema declares applicable receives a non-empty value** (0 unresolved applicable fields), and the resolved count rises from **~6 → the applicable-field count**. This catches broken bindings/predicates/resolver bugs. It does **not** by itself prove the schema is correct or that real-world coverage is high — see the next two.
- **Coverage metric (reported, not a pass/fail gate):** `applicable / total-fillable` for 107 is computed and recorded, so SP2 inherits a real number rather than an aspiration.
- **Schema correctness (manual, verification step 4):** a human opens the filled PDF and confirms the _right_ fields carry the _right_ values — the check no automated test can stand in for.
- **Form-agnostic acceptance (the SP2 contract):** the ingester + `validate_schema` + `resolve` run correctly against a **second, uncurated** form's metadata — ingest produces a draft without error, validation flags the `TBD`s, and the resolver no-ops cleanly on an all-`TBD`/empty schema (no `KeyError`, conditional skip holds). This is the test that makes SP2 "curate the next schema," not "rebuild the engine."
- **UPL test:** a `legal_review: true` field is **not** filled absent an explicit confirmed answer.
- **Download exception test:** unknown `form_type`, missing template, and `RepeatOverflow` each return a handled error with `detail`, not an unhandled 500.

## Verification (end-to-end)

1. `docker compose exec backend python manage.py ingest_form_schema form_107` → draft schema written.
2. After curation: `pytest backend/apps/forms` + `pytest backend/apps/intake` green.
3. Re-run the demand-vs-supply coverage diagnostic from the audit → Form 107 filled-field count rises from ~6 to the applicable target for the seeded persona.
4. `GET /api/forms/<107-id>/download/` → open the PDF: section checkboxes **selected**, repeating creditor/income rows **populated**, inapplicable sections **blank**.
5. Frontend: complete the SOFA module for a persona, confirm autosave/resume works, and the regenerated 107 reflects the entries.

## Risks & Mitigations

| Risk                                                      | Mitigation                                                                                               |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Abstraction doesn't generalize past 107                   | 107 is the hardest form by design; if it survives, the others are strictly easier. SP5 curates the rest. |
| Repeating-row inference from field-name suffixes is wrong | Ingestion produces a **draft**; human + UPL curation is a required step before commit.                   |
| A derivation drifts into legal advice                     | Hard UPL rule: legal conclusions are `asked` + `legal_review`, enforced by a dedicated test.             |
| Template revision silently changes output                 | `template_version` hash pinned in schema + stamped on `GeneratedForm`; drift fails tests.                |

## Open Questions (resolve during `writing-plans` or first tasks)

1. **SOFA surface:** a new `WIZARD_STEPS` entry vs. a dedicated `/intake/sofa` route — pick during plan task for component 7.
2. **Applicable-field target number:** the exact numeric threshold for the coverage assertion is set once the curated `form_107.json` exists (it equals the count of `required` + applicable fields for the seeded persona).
3. **`binding` grammar:** confirm the minimal path syntax needed for 107 (`model.collection[].attr` + `answer:<form>.<key>`) — avoid building a general expression language (YAGNI).

## Out of Scope for SP1

Other 12 forms' schemas/wiring; document-ingestion extraction (`ingest_key` inert); Schedule A/B granularity & Schedule C exemptions. These are SP2–SP5, each its own spec→plan cycle.
