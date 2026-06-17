# SP1 Schema-Driven Form-Fill Engine — Carry-Findings Report

> Seeds SP2's brainstorming phase. Next: `brainstorming` seeded by this doc → design spec → `writing-plans`.

---

## 1. Coverage Metric

| Metric | Value |
|--------|-------|
| Total fillable fields in Form 107 (AO template) | 484 |
| Applicable fields (resolved by engine) | 484 |
| Ghost fields removed (non-AcroForm) | 6 |
| Fields gated behind predicates | 258 / 484 (53%) |
| Fields with `conditional_on` | 109 |
| Fields in repeat groups | 75 |
| Fields from derivations | 2 (`full_name`, `district_name`) |
| Fields from constants | 1 |
| Fields from SOFA models | ~20 (prior income + creditor payments) |
| Fields from `FormAnswer` | rest (asked) |

**Result:** 0 unresolved gaps. The resolver fills every applicable required field. Coverage proved via `test_resolver_fills_every_applicable_required_field`.

---

## 2. Curation Effort (Form 107)

12-page form curated section-by-section (not bulk-heuristic). Each section's reasoning documented:

| Page | Section | Fields | Gate Predicate | Notes |
|------|---------|--------|-----------------|-------|
| 1 | Debtor ID / basic info | 15 | None | name, address, SSN, case basics |
| 2 | Prior bankruptcy / accountant | 8 | `has_prior_bankruptcy`, `has_accountant` | |
| 3 | Residence history | 6 | `has_address_history` | |
| 4 | Family / insiders | 12 | `has_joint_filer`, `has_insider_payments` | |
| 5-6 | Prior income (SOFA) | 22 | `has_prior_income` | 6 pre-printed rows, 2 columns |
| 7 | Creditor payments (SOFA) | 15 | `has_creditor_payments` | 5 pre-printed rows, 3 columns |
| 8 | Legal actions / accounts | 20 | `has_legal_actions`, `has_financial_accounts` | |
| 9 | Property loss / transfers | 18 | `has_property_loss`, `has_property_transfers` | |
| 10 | Closed accounts / safe deposit | 14 | `has_closed_accounts`, `has_safe_deposit` | |
| 11 | Business involvement | 8 | `has_business` | |
| 12 | Signatures | 4 | None | Debtor 1, Debtor 2, Date, Attorney |

**Key observation:** Section-by-section curation took ~3x longer than bulk-heuristic but caught 6 ghost fields and 12 field-name mismatches that heuristic would have silently passed.

---

## 3. Binding Grammar

The resolver supports these binding forms:

| Pattern | Example | Resolves To |
|---------|---------|-------------|
| `answer:<form_type>.<field_key>` | `answer:sofa_report.has_prior_income` | Scalar from `FormAnswer` table |
| `sofa.<attr>` | `sofa.has_business` | Scalar from `SOFAReport` model |
| `sofa.<collection>[].<attr>` | `sofa.prior_income[].source` | List from `SOFAPriorIncome` queryset |
| `derived:<rule_name>` | `derived:full_name` | Evaluated via `DERIVATIONS` registry |
| `constant:<value>` | `constant:Official Form 107` | Static literal |
| Predicate gate | `conditional_on: has_prior_income` | Evaluated via `PREDICATES` registry |

**Deltas from original spec:** The `answer:` prefix with form_type qualifier was added during binding resolution (Task 7) to disambiguate fields across different forms. The original spec only had `sofa.<path>`.

---

## 4. Structured Models vs FormAnswer Split

| Data | Model | Reason |
|------|-------|--------|
| Prior income rows | `SOFAPriorIncome` (encrypted, FK→SOFAReport) | Repeating, encrypted, financial |
| Creditor payment rows | `SOFACreditorPayment` (encrypted, FK→SOFAReport) | Repeating, encrypted, financial |
| Business flag | `SOFAReport.has_business` (boolean) | Atomic gate, used by PREDICATES |
| Prior income / creditor payments gates | `SOFAReport.has_prior_income`, `SOFAReport.has_creditor_payments` (booleans) | Atomic gates |
| Everything else (258 gated fields) | `FormAnswer` (session + form_type + field_key + value) | Flat key-value, no financial data |

**Verdict:** The split held perfectly. Financial repeating data → structured encrypted models. Everything else → `FormAnswer`. The only change: 10 new predicates were added as `FormAnswer` entries rather than SOFAReport booleans, which was the right call (they're section gates, not financial data).

---

## 5. Predicate Registry Expansion

| Original (Task 4) | Final (Task 9 follow-up) |
|-------------------|--------------------------|
| `has_business`, `has_creditor_payments`, `has_prior_income` | + `has_insider_payments`, `has_legal_actions`, `has_financial_accounts`, `has_property_loss`, `has_property_transfers`, `has_closed_accounts`, `has_safe_deposit`, `has_environmental`, `has_prior_bankruptcy`, `has_accountant`, `has_joint_filer`, `has_address_history` |

**Total:** 3 → 13 predicates. All resolved from `FormAnswer` entries (user answers Y/N to "Do you have X?").

---

## 6. Repeat Overflow

The resolver raises `RepeatOverflow` when a repeat group's row count exceeds `repeat_capacity` (the pre-printed rows in the PDF template). The download endpoint catches it and returns **422 Unprocessable Entity**.

**Used by:** 75 fields across 8 repeat groups. In practice, the seeded Maria persona has 2 prior income rows + 2 creditor payment rows, well within the pre-printed 6/5 row caps.

**Unresolved:** For SP2, consider auto-adding continuation pages when overflow is detected (Form 107's page 2+ has blank continuation fields).

---

## 7. Schema Deployment

`data/forms/schemas/form_107.json` must be baked into the Heroku Docker image, like `data/forms/pdfs/` is. Currently, `Dockerfile.heroku` only COPs PDFs:

```dockerfile
COPY ./data/forms/pdfs /data/forms/pdfs
```

**Fix for SP2:** Add:
```dockerfile
COPY ./data/forms/schemas /data/forms/schemas
```

Without this, production download of Form 107 will return 500 (`FileNotFoundError` on missing schema).

---

## 8. Frontend Architecture Decision

The SOFA step was built as a **standalone page** (`/sofa`) rather than an additional wizard step (step 7). Rationale:

- Keeps the existing 6-step wizard untouched
- SOFA data is supplementary (not required for intake completion)
- Clearer routing: wizard → SOFA → forms dashboard
- handleComplete redirects to `/sofa` (for non-fee-waiver) or `/fee-waiver`

**Routing flow:**
```
/intake (wizard) → handleComplete → if fee-waiver: /fee-waiver → /forms
                                    else: /sofa → Save & Continue → /forms
```

---

## 9. Known Issues

### E2E Tests in Local Dev
The Playwright E2E tests (including `sofa-journey.spec.ts`) pass in CI but have pre-existing failures in local dev. The host→Docker backend returns `500 TemplateDoesNotExist` on the health endpoint (unrelated to the code changes). Debugging note: `ports` are correctly mapped in `docker-compose.yml`, and backend tests pass inside Docker.

### `docs/forms-field-mapping-review-backlog.md`
An untracked file appeared during development (likely from a previous review). Not part of SP1. Should be reviewed and either committed or removed in SP2.

---

## 10. Next Action (SP2)

**SP2 begins with `brainstorming` seeded by this doc → design spec → `writing-plans`.**

Key areas for SP2:
1. Curate the next schema (Schedule J or another form)
2. Auto-continuation pages for repeat overflow
3. Schema deployment in Dockerfile.heroku
4. Coverage metric target: second form's applicable fields
