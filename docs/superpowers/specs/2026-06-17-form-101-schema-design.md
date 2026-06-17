# SP2: Form 101 Schema Curation — Design Spec

> Second schema curation for the form-fill engine. Proves the engine workflow
> repeats on a different form. SP1's `form_107.json` → **SP2's `form_101.json`**.

---

## Goal

Replace Form 101 (Voluntary Petition) hand-authored `pdf_field_map()` with a
schema-driven resolver delegate, using a committed `form_101.json` schema.
The old map is removed — the resolver is the only path.

---

## Scope

**110 fields** across **8 pages** (template pages 1–5, 7–9; page 6 has no
fillable fields). About ¼ the curation effort of Form 107 (484 fields).

Draft schema generated via `ingest_form_schema form_101`. Field names in the
template use bare names (`First name`, `Last name`, `SSNum`) with `_N`
suffixes for repeats — the old hand-authored map used dotted notation
(`Debtor1.First name`) which doesn't match the template and will be removed.

---

## Schema Curation

### Sections by page

| Page | Field count | Content | Gate predicate |
|------|------------|---------|----------------|
| 1 | 27 | Debtor 1 name (first, middle, last, suffix), SSN/Tax ID, Debtor 2 name, Business name | `has_joint_filer` gates Debtor 2 fields (3×3 name sets = 9 fields) |
| 2 | 26 | Address, mailing address, venue district info, Employer IDs | None |
| 3 | 19 | Prior bankruptcy history × 4 prior cases | `has_prior_bankruptcy` |
| 4 | 6 | Business name + address | `has_business` |
| 5 | 8 | Emergency/hazard information | None |
| 7 | 3 | Non-consumer debt type, signature, executory date | None |
| 8 | 11 | Attorney name, firm, address, bar info | **`has_attorney`** (new predicate, default false) |
| 9 | 10 | Petition preparer name, signature, contact | None |

### New predicate

- **`has_attorney`** — resolves from `FormAnswer` entry. Defaults `false` for
  pro se filers (no answer = no attorney). All 11 page-8 fields gated behind it.

### Existing predicates reused (from SP1's 13)

- `has_joint_filer` — used on page 1 to show Debtor 2 name fields
- `has_prior_bankruptcy` — shows page 3 prior-bankruptcy section
- `has_business` — shows page 4 business address

No other predicates needed — the remaining pages are always applicable.

---

## Derivation Coverage

| Rule | Applied to |
|------|-----------|
| `full_name` | Debtor 1 full name (concatenates first + middle + last), appears on pages 1 and 3 |
| `chapter` | Chapter 7 checkbox (fixed for MVP) |
| `district_name` | Bankruptcy District Information field (page 1) |

---

## Wire-up

`Form101Generator.pdf_field_map()` delegates to:

```python
def pdf_field_map(self) -> dict:
    schema = load_schema("form_101")
    return resolve(schema, self.intake_session)
```

The old hand-authored field dict is removed entirely. The `download` endpoint
(already catching `NotImplementedError` → 501, `RepeatOverflow` → 422,
`FileNotFoundError`/`KeyError` → 500) works unchanged — the generator already
implements `pdf_field_map()`.

---

## Testing

### Coverage proof

Adapt the existing coverage test from SP1 (Task 11) to also run on Form 101.
The test `test_resolver_fills_every_applicable_required_field` proves 0
unresolved gaps for a seeded persona.

### Updated field-map test

`test_form_101_field_map` in `test_pdf_field_maps.py` currently checks the
hand-authored map. Update it to assert the resolver-based map returns the
expected fields for a known session.

### Form-agnostic test

The existing `test_engine_form_agnostic.py` already proves the engine works
on a second form's metadata. No changes needed.

---

## Files changed

| File | Action |
|------|--------|
| `data/forms/schemas/form_101.json` | **Create** — curated schema (110 fields) |
| `backend/apps/forms/services/form_101_generator.py` | **Modify** — `pdf_field_map()` delegates to resolver; remove hand-authored dict |
| `backend/apps/forms/services/derivations.py` | **Modify** — add `has_attorney` to PREDICATES |
| `backend/apps/forms/tests/test_pdf_field_maps.py` | **Modify** — update Form 101 field-map test |
| `backend/apps/forms/tests/test_coverage.py` | **Modify** — add Form 101 coverage to existing proof |
| `Dockerfile.heroku` | **Modify** — add `COPY ./data/forms/schemas /data/forms/schemas` |

---

## Non-goals

- **No new models** — Attorney info is gated, not stored. All page-8 data
  comes from `FormAnswer` entries.
- **No frontend changes** — Form 101 is filled server-side the same way all
  forms are. The wizard collects the necessary data in existing steps.
- **No continuation pages** — SP1's `RepeatOverflow` cap (6/5 rows) is fine;
  Form 101 has no repeating groups that exceed pre-printed capacity.
