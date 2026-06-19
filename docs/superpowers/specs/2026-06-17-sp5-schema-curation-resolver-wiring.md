# SP5: Schema Curation ×7 + Resolver Wiring ×11 — Design Spec

> Fifth phase of the schema-driven form-fill engine. Cures the 7 remaining
> forms' schemas and wires all 13 forms through the generic `FillResolver`,
> eliminating hand-authored `pdf_field_map()` code.

**Goal:** Every Chapter 7 form fills via the schema → FillResolver → PDFFormFiller
pipeline. No hand-authored field maps remain.

---

## Context

SP1 proved the engine on Form 107 (484 fields). SP2 proved repetition on
Form 101 (112 fields). SP4 added the Ask-Modules UI for `source: "asked"` fields.
SP3 added `source: "ingested"` resolution.

Six forms already have committed schemas (`form_101`, `form_107`, `schedule_a_b`,
`schedule_c`, `schedule_d`, `schedule_e_f`). Seven forms still lack schemas and
use hand-authored `pdf_field_map()` code.

**Current state:**

| Form         | Fields | Schema | Resolver wired |
| ------------ | ------ | ------ | -------------- |
| form_101     | 112    | yes    | yes            |
| form_103b    | ~142   | no     | no             |
| form_106dec  | ~16    | no     | no             |
| form_106sum  | ~32    | no     | no             |
| form_107     | 484    | yes    | yes            |
| form_121     | ~27    | no     | no             |
| form_122a1   | ~73    | no     | no             |
| schedule_a_b | 379    | yes    | no             |
| schedule_c   | 107    | yes    | no             |
| schedule_d   | 193    | yes    | no             |
| schedule_e_f | 336    | yes    | no             |
| schedule_i   | ~93    | no     | no             |
| schedule_j   | ~94    | yes    | no             |

---

## Architecture

```
                        ┌─────────────────────┐
                        │  ingest_form_schema  │  (one-time per form)
                        │  → draft JSON        │
                        └────────┬────────────┘
                                 │ manual curation
                                 ▼
    data/forms/schemas/{form_type}.json
      committed, version-pinned, UPL-reviewed
                                 │
                                 ▼
    FillResolver(schema, session) → {pdf_field: str}
      source priority: presume → derive → ingest → ask
                                 │
                                 ▼
    PDFFormFiller.fill(form_type, field_map)
```

### Two Parallel Tracks

**Track A — Schema Curation** (7 forms without schemas):

1. Run `ingest_form_schema {form_type}` to generate draft
2. Manually curate: mark `source`, add `binding`/`rule`/`ingest_key`, add `conditional_on`, add `on_states` for checkboxes
3. Legal/UPL review of field labels and prompts
4. Commit JSON + test schema round-trip

**Track B — Resolver Wiring** (11 forms not yet wired):

1. Replace `pdf_field_map()` body with `FillResolver` delegation
2. Remove hand-mapped field code
3. Verify PDF output matches pre-wiring output (byte-level or field-count parity)

### Forms needing both tracks

`form_103b`, `form_106dec`, `form_106sum`, `form_121`, `form_122a1`, `schedule_i`, `schedule_j`

### Forms needing only Track B

`schedule_a_b`, `schedule_c`, `schedule_d`, `schedule_e_f`

---

## Source Priority Rules

Each field's `source` determines how `FillResolver` populates it:

| Source     | Meaning                                  | Example                                |
| ---------- | ---------------------------------------- | -------------------------------------- |
| `presume`  | Derived from session data without asking | Debtor name from DebtorInfo            |
| `derive`   | Calculated from other fields             | Total expenses = sum of expense fields |
| `ingested` | From OCR document extraction             | Paystub gross income                   |
| `asked`    | User must provide via Ask-Modules        | Prior bankruptcy details               |

### Repeat Groups

Forms like Schedule A/B and Schedule D have repeating rows (creditors, assets).
The schema marks these with `repeat: "creditors"` and `repeat_capacity: 20`.
The FillResolver expands the group, emitting `{field}_{N}` suffixed keys.

### Checkbox On-States

PDF checkboxes use `/Yes` for checked. Fields with `on_states` map Python
booleans to the correct PDF string. Example: `"on_states": {"true": "/Yes"}`.

---

## Curation Workflow Per Form

For each form:

1. **Ingest**: `python manage.py ingest_form_schema {form_type}` → `data/forms/schemas/{form_type}.json` (draft)
2. **Audit**: Compare draft fields against existing `pdf_field_map()` to ensure coverage
3. **Classify**: Set `source` for each field (presume/derive/ingested/asked)
4. **Bind**: For `asked` fields, add `binding: "answer:{form_type}.{key}"` and `ui` metadata
5. **Condition**: Add `conditional_on` predicates for fields gated by boolean session data
6. **Review**: UPL check — all labels/prompts must be informational, never advisory
7. **Test**: `pytest` round-trip test loads schema, resolves fields, fills PDF

---

## Wiring Workflow Per Form

For each form with an existing schema:

1. **Read** the current `pdf_field_map()` to understand data dependencies
2. **Replace** body with:
   ```python
   def pdf_field_map(self) -> dict:
       from apps.forms.services.fill_resolver import resolve
       return resolve(self.schema, self.session)
   ```
3. **Remove** dead helper functions no longer called
4. **Test**: `pytest` — verify `generate()` + `pdf_field_map()` still produce valid output

---

## Testing Strategy

- **Schema round-trip test**: Load schema → resolve → verify all required fields present
- **PDF parity test**: For wired forms, compare field count of resolver output vs old hand-map
- **Integration test**: `seed_demo_data` → `generate_all` → verify all 13 forms produce non-empty PDFs

---

## Defer

- Ask-Modules UI wiring for SP5 forms (SP4 infrastructure exists, UI integration is separate)
- Document-ingestion extraction for new forms (SP3 infrastructure, per-form tuning later)
