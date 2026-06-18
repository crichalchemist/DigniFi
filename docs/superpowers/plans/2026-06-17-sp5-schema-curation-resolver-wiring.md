# SP5: Schema Curation ×7 + Resolver Wiring ×11 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every Chapter 7 form fills via schema → FillResolver → PDFFormFiller. No hand-authored field maps remain.

**Depends on:** SP1 (FillResolver), SP2 (Form 101 schema), SP3 (IngestedAggregate), SP4 (Ask-Modules infrastructure).

---

## Task 1: Curate Form 106Dec Schema (simplest — 16 fields) ✅

**Why first:** Smallest form, proves the curation workflow on a trivial case.

**Files:**

- Create: `data/forms/schemas/form_106dec.json`
- Modify: `backend/apps/forms/services/form_106dec_generator.py`
- Create: `backend/apps/forms/tests/test_form_106dec_schema.py`

- [x] **Step 1: Ingest draft** — 12 fields ingested, 4 UI buttons removed, 8 real fields curated
- [x] **Step 2: Audit** — verified coverage against old pdf_field_map()
- [x] **Step 3: Curate** — 8 fields: 4 derived, 1 constant, 1 presume, 2 conditional
- [x] **Step 4: Wire resolver** — pdf_field_map() delegates to FillResolver
- [x] **Step 5: Round-trip test** — 5 new tests in test_form_106dec_schema.py
- [x] **Step 6: Tests** — 579 passed (3 new)
- [x] **Step 7: Commit** — `ed2dce2`

---

## Task 2: Curate Form 106Sum Schema (32 fields)

**Files:**

- Create: `data/forms/schemas/form_106sum.json`
- Modify: `backend/apps/forms/services/form_106sum_generator.py`
- Create: `backend/apps/forms/tests/test_form_106sum_schema.py`

- [ ] **Step 1: Ingest draft**

  ```bash
  cd backend && python manage.py ingest_form_schema form_106sum
  ```

- [ ] **Step 2: Audit against pdf_field_map()** — compare ingested fields with the 14 mapped fields in the existing generator.

- [ ] **Step 3: Curate schema** — `source: "derive"` for CMI calculation fields, `source: "presume"` for debtor info.

- [ ] **Step 4: Wire resolver** — replace `pdf_field_map()`, remove dead code.

- [ ] **Step 5: Write round-trip test** (same pattern as Task 1).

- [ ] **Step 6: Run tests.**

- [ ] **Step 7: Commit**
  ```bash
  git commit -m "feat(sp5): curate form_106sum schema and wire resolver"
  ```

---

## Task 3: Curate Form 121 Schema (27 fields)

**Files:**

- Create: `data/forms/schemas/form_121.json`
- Modify: `backend/apps/forms/services/form_121_generator.py`
- Create: `backend/apps/forms/tests/test_form_121_schema.py`

- [ ] **Step 1–7:** Same workflow. Form 121 is the SSN statement — most fields are debtor name/SSN (`source: "presume"`), with a checkbox for SSN vs ITIN (`on_states`).

---

## Task 4: Curate Form 122A1 Schema (73 fields)

**Files:**

- Create: `data/forms/schemas/form_122a1.json`
- Modify: `backend/apps/forms/services/form_122a1_generator.py`
- Create: `backend/apps/forms/tests/test_form_122a1_schema.py`

- [ ] **Step 1–7:** Means test calculation form. Heavy `source: "derive"` for income/expense aggregation. Conditional sections for household size, special circumstances.

---

## Task 5: Curate Form 103B Schema (142 fields)

**Files:**

- Create: `data/forms/schemas/form_103b.json`
- Modify: `backend/apps/forms/services/form_103b_generator.py`
- Create: `backend/apps/forms/tests/test_form_103b_schema.py`

- [ ] **Step 1–7:** Fee waiver application. Most fields are `source: "presume"` from session data, with conditional sections for income sources and expenses. Requires `FeeWaiverApplication` model integration.

---

## Task 6: Curate Schedule I Schema (93 fields)

**Files:**

- Create: `data/forms/schemas/schedule_i.json`
- Modify: `backend/apps/forms/services/schedule_i_generator.py`
- Create: `backend/apps/forms/tests/test_schedule_i_schema.py`

- [ ] **Step 1–7:** Other household members' income. Repeating group for additional members. `source: "asked"` for member details, `source: "derive"` for totals.

---

## Task 7: Wire Schedule A/B Resolver

**Files:**

- Modify: `backend/apps/forms/services/schedule_ab_generator.py`

Schema already exists (379 fields, 2 asked). Only wiring needed.

- [ ] **Step 1: Read existing pdf_field_map()** — understand data dependencies (assets list from session).
- [ ] **Step 2: Wire resolver** — replace `pdf_field_map()` with FillResolver delegation.
- [ ] **Step 3: Verify** — asset repeat groups resolve correctly with `_N` suffixes.
- [ ] **Step 4: Run tests.**
- [ ] **Step 5: Commit**
  ```bash
  git commit -m "feat(sp5): wire schedule_a_b through FillResolver"
  ```

---

## Task 8: Wire Schedule C Resolver

**Files:**

- Modify: `backend/apps/forms/services/schedule_c_generator.py`

Schema exists (107 fields, 7 asked). Wiring only.

- [ ] **Step 1–5:** Same workflow. Exempt property categories with conditional `on_states`.

---

## Task 9: Wire Schedule D Resolver

**Files:**

- Modify: `backend/apps/forms/services/schedule_d_generator.py`

Schema exists (193 fields, 27 asked). Wiring only.

- [ ] **Step 1–5:** Same workflow. Secured debt priority classification with repeat groups.

---

## Task 10: Wire Schedule E/F Resolver

**Files:**

- Modify: `backend/apps/forms/services/schedule_ef_generator.py`

Schema exists (336 fields, 38 asked). Wiring only.

- [ ] **Step 1–5:** Same workflow. Unsecured debt priority with repeat groups.

---

## Task 11: Wire Schedule J Resolver

**Files:**

- Modify: `backend/apps/forms/services/schedule_j_generator.py`

Schema exists (94 fields). Wiring only.

- [ ] **Step 1–5:** Same workflow. Expense fields from `ExpenseInfo` model.

---

## Task 12: Integration Test — Generate All 13 Forms

**Files:**

- Create/Modify: `backend/apps/forms/tests/test_generate_all_schema_driven.py`

- [ ] **Step 1: Write integration test**

  ```python
  @pytest.mark.django_db
  def test_generate_all_13_forms():
      """Every form type generates without error via schema → resolver pipeline."""
      # Create session with minimal required data
      # Call generate_all
      # Assert 13 forms generated, 0 errors
      # Assert each form has non-empty form_data
  ```

- [ ] **Step 2: Run full test suite**

  ```bash
  python -m pytest backend/ --tb=short -q
  ```

- [ ] **Step 3: Commit**
  ```bash
  git commit -m "test(sp5): integration test for all 13 forms via schema pipeline"
  ```

---

## Task 13: Remove Dead Generator Code

After all forms are wired, remove unused helper functions from generators.

- [ ] **Step 1: Audit** each generator for dead code (private helpers only called by old `pdf_field_map()`).
- [ ] **Step 2: Remove** dead code.
- [ ] **Step 3: Run** `ruff check backend/` + full test suite.
- [ ] **Step 4: Commit**
  ```bash
  git commit -m "refactor(sp5): remove dead generator helper code after resolver wiring"
  ```

---

## Task Ordering

Tasks 1–6 (schema curation) are independent and can be done in any order.
Tasks 7–11 (resolver wiring) depend on their schema existing.
Task 12 (integration test) depends on all wiring being complete.
Task 13 (cleanup) is last.

Recommended sequence:

1. Tasks 1–3 (simple forms: 106dec, 106sum, 121) — prove curation workflow
2. Tasks 4–5 (medium forms: 122a1, 103b) — heavier curation
3. Task 6 (Schedule I) — repeat group pattern
4. Tasks 7–11 (wire existing schemas) — mechanical, batch-friendly
5. Task 12 (integration test) — verify everything
6. Task 13 (cleanup) — remove dead code
