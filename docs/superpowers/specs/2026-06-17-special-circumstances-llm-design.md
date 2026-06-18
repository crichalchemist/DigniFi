# Special Circumstances LLM — Implementation Design Spec

> **Supersedes:** `docs/AI_SPECIAL_CIRCUMSTANCES_DESIGN.md` (Jan 2026, Anthropic-targeted)
> **Status:** Ready for Implementation
> **Priority:** P0 — blocks MVP launch per PRD v0.3

---

## Context

Form 122A-2 Lines 44-47 are the sole mechanism for above-median Chapter 7 filers to rebut the presumption of abuse. Pro se filers succeed 15-25% of the time vs 85-90% for attorney-drafted statements — the gap is articulation, not facts. This feature transforms natural-language user input into legally defensible prose via LLM refinement, with mandatory human-in-the-loop approval.

The existing design doc (`AI_SPECIAL_CIRCUMSTANCES_DESIGN.md`, 1327 lines) covers legal foundation, prompting strategy, and model selection in depth. This spec updates three things:

1. **LLM provider:** Anthropic Claude → local Llama.cpp + Gemma 3 4B (matches `docker-compose.yml` infrastructure)
2. **Scope:** Full production system → MVP that proves the loop end-to-end
3. **Form 122A-2:** No generator exists yet — needs one

---

## Architecture

```
User narrative (text input)
    ↓
SpecialCircumstances model (encrypted storage)
    ↓
SpecialCircumstancesRefiner service
    ↓ POST /api/intake/sessions/{id}/special-circumstances/refine/
    → LlamaCppProvider (Gemma 3 4B, local, zero cost)
    ↓
Refined narrative returned to frontend
    ↓
User reviews, edits, approves
    ↓ POST /api/intake/sessions/{id}/special-circumstances/approve/
    ↓
Refined narrative stored in SpecialCircumstances.refined_narrative
    ↓
Form 122A-2 generator reads from SpecialCircumstances model
    ↓
PDF populated with Lines 44-47
```

---

## Components

### 1. SpecialCircumstances Model

**Location:** `backend/apps/intake/models.py`

```python
class SpecialCircumstances(models.Model):
    session = OneToOneField(IntakeSession, related_name="special_circumstances")
    user_narrative = EncryptedTextField()          # User's raw input
    identified_categories = JSONField(default=list) # ["income_reduction", "medical", ...]
    refined_narrative = EncryptedTextField()        # LLM output (after approval)
    user_approved = BooleanField(default=False)
    refinement_version = IntegerField(default=1)
    refinement_timestamp = DateTimeField(null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

**Why OneToOne:** Each session has at most one special circumstances statement. The 122A-2 is a single narrative, not per-creditor.

**Categories (from intake wizard):**

- `income_reduction` — Involuntary job loss, hours reduction
- `medical` — Chronic illness, disability, ongoing treatment
- `family_support` — Child support, alimony, dependent care
- `debt_service` — Court-ordered restitution, necessary debt payments
- `education` — Vocational training, licensing requirements
- `other` — Anything else

### 2. SpecialCircumstancesRefiner Service

**Location:** `backend/apps/eligibility/services/special_circumstances_refiner.py`

Uses the same `LlamaCppProvider` pattern already established in `backend/apps/documents/services/providers/llama_cpp.py`. No new dependencies — Gemma 3 4B via the existing `llm` Docker service.

**Key design decisions:**

- **Temperature 0.3** — consistent output, not creative writing
- **Max tokens 512** — Lines 44-47 fit ~250 words; Gemma 3 4B handles this well
- **Fallback to template** — if LLM fails, return a fill-in-the-blank template so the user isn't blocked
- **No streaming** — single-shot refinement, not conversational

### 3. API Endpoints

| Endpoint                                                   | Method | Purpose                         |
| ---------------------------------------------------------- | ------ | ------------------------------- |
| `/api/intake/sessions/{id}/special-circumstances/`         | GET    | Retrieve current state          |
| `/api/intake/sessions/{id}/special-circumstances/`         | POST   | Create/update user narrative    |
| `/api/intake/sessions/{id}/special-circumstances/refine/`  | POST   | Trigger LLM refinement          |
| `/api/intake/sessions/{id}/special-circumstances/approve/` | POST   | User approves refined narrative |

### 4. Form 122A-2 Generator + Schema

**Location:** `backend/apps/forms/services/form_122a2_generator.py`

New generator that reads from `SpecialCircumstances` model. Maps:

- Lines 44: checkbox (`/Yes` if `user_approved` is True)
- Lines 45-47: `refined_narrative` text (truncated to PDF field capacity)

Schema file: `data/forms/schemas/form_122a2.json`

### 5. Frontend — SpecialCircumstancesWizard

**Location:** `frontend/src/components/wizard/steps/SpecialCircumstancesStep.tsx`

Integrated into the existing IntakeWizard flow as a new step (after Step 6 Review, before form generation). Renders:

1. Category checkboxes (multi-select from the 6 categories)
2. Text area for natural-language narrative
3. "Refine with AI" button → calls `/refine/` endpoint
4. Side-by-side view: original vs refined (diff highlighted)
5. Edit capability on refined text
6. "Approve" button → calls `/approve/` endpoint
7. "Skip for now" → continues without special circumstances

**UPL compliance:** All text is informational. The refinement is "language enhancement," not "legal advice." The user approves all output.

### 6. Routing Changes

Add `SpecialCircumstancesStep` to the IntakeWizard step array in `frontend/src/pages/IntakeWizard.tsx`. Insert after Review step (step 6) when `means_test_result.passes_means_test === false` (above-median filers only).

---

## Data Flow

```
1. User completes intake → means test runs → above median
2. IntakeWizard shows SpecialCircumstancesStep
3. User selects categories, writes narrative
4. User clicks "Refine" → POST /refine/
5. Backend: SpecialCircumstancesRefiner calls Gemma 3 4B
6. Frontend: shows side-by-side comparison
7. User edits if needed, clicks "Approve" → POST /approve/
8. SpecialCircumstances.user_approved = True
9. User clicks "Complete" → navigates to /forms
10. FormDashboard: "Generate" on Form 122A-2 reads SpecialCircumstances
11. PDF: Lines 44-47 populated with approved narrative
```

---

## Error Handling

| Failure                               | Behavior                                                                                                                  |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| LLM service down                      | Return template-based fallback: "I have special circumstances that may affect my ability to pay. [User fills in details]" |
| LLM returns empty/error               | Show error toast, user can retry or use template                                                                          |
| User narrative too short (<20 chars)  | Block refine button with hint: "Please describe your circumstances in at least one sentence"                              |
| User narrative too long (>2000 chars) | Truncate with warning before sending to LLM                                                                               |
| Approval without refine               | Allow — user can skip AI and write directly                                                                               |

---

## Testing Strategy

- **Unit tests:** `SpecialCircumstancesRefiner` with mocked LLM response
- **Integration test:** Full flow — create narrative → refine → approve → generate 122A-2 → verify PDF field
- **Template fallback test:** Mock LLM failure → verify template fallback renders
- **UPL test:** Verify no advisory language in prompts or outputs
- **E2E test:** Add to `persona-briefs/` — above-median persona completes special circumstances flow

---

## UPL Compliance

- All prompts frame refinement as "language enhancement," not "legal advice"
- No phrases: "you should," "the court will," "you qualify for"
- User explicitly approves all output before it enters the form
- Audit trail: refinement_prompt_hash + llm_response_full stored encrypted
- Disclaimer: "This tool helps articulate your circumstances. It does not determine whether they qualify under § 707(b)(2)(B)."

---

## Deferred (Post-MVP)

- Streaming refinement (show tokens as they generate)
- Multiple refinement passes (user can iterate)
- Category-specific prompts (different prompting for medical vs income reduction)
- Integration with document ingestion (paystub data auto-populates income details)
- Form 122A-2 continuation pages for long narratives
