# Phase 7: User Testing Design — AI-Simulated Persona Testing

**Date:** 2026-02-28
**Status:** Approved
**Author:** Brainstorming session (Claude + Courtney)

---

## Overview

Phase 7 prepares DigniFi for paper prototype testing (PRD Experiment 1) using
a novel approach: AI subagents embodying 5 synthetic user personas navigate the
live application through Playwright, report friction points from a human
perspective, and answer post-task surveys in character. This produces
quantitative PRD metrics and qualitative UX insights before real participant
recruitment.

The infrastructure also serves as a polished partner demo (login as any persona
to walk through completed flows) and automated E2E regression coverage.

**Two-stage approach:**
1. **Now:** Build test infrastructure, run AI-simulated testing, fix issues found
2. **Later (post-partnership):** Run real user testing sessions with recruited participants

---

## 1. Synthetic Personas

Five personas exercising distinct eligibility paths through the ILND means test
calculator and form generation pipeline.

| # | Name | Archetype | HH Size | Annual Income | Key Trait |
|---|------|-----------|---------|---------------|-----------|
| 1 | Maria Torres | PRD primary persona | 3 | $38,400 | Below median, fee waiver eligible (<150% poverty). Single parent, 2 kids. Modest assets. |
| 2 | James Washington | Borderline case | 1 | $70,000 | Just below single-filer median ($71,304). No dependents. Vehicle + small savings. |
| 3 | Priya Sharma | Above median | 4 | $120,000 | Fails means test. Demonstrates the "not eligible" path gracefully. |
| 4 | DeShawn Mitchell | Asset-heavy | 2 | $42,000 | Below median but owns home ($180k, $160k mortgage). Tests exemption calculations (IL $15k homestead). |
| 5 | Sarah Chen | Simplest case | 1 | $24,000 | Single, no assets, no dependents, fee waiver eligible. Fastest path through the wizard. |

### Persona Briefs (Subagent Input)

Each subagent receives a ~300-word brief covering:
- **Identity:** Name, age, household, income, occupation
- **Tech literacy:** Device usage patterns, comfort with online forms, trust level
- **Emotional state:** Stress level, shame/anxiety, prior experience with legal system
- **Reading level:** Vocabulary comfort, attention span for text blocks, legal term familiarity
- **Behavioral patterns:** Likely mistakes, hesitation points, skip tendencies
- **Goals:** What they need from bankruptcy, what they're trying to protect

---

## 2. Data Seeding Infrastructure

A Django management command creates all 5 personas atomically for partner demos.

**Command:**
```bash
python manage.py seed_demo_data          # Create all 5 personas
python manage.py seed_demo_data --reset  # Wipe and recreate
python manage.py seed_demo_data --persona maria  # Single persona only
```

**Location:** `backend/apps/intake/management/commands/seed_demo_data.py`

**Per persona, creates:**
1. `User` (username: `demo_maria`, etc.; `is_staff=False`)
2. `IntakeSession` (status: `completed`, all 6 steps)
3. `DebtorInfo` (synthetic SSNs in 900-xx range — IRS-reserved test numbers)
4. `IncomeInfo` (monthly + annual, matching persona profile)
5. `ExpenseInfo` (12 categories, proportional to income)
6. `AssetInfo` (0-3 assets depending on persona)
7. `DebtInfo` (2-5 debts depending on persona)
8. `MeansTest` (pre-calculated via `MeansTestCalculator`)
9. `GeneratedForm` records (all 13 types for eligible personas)

**Design principles:**
- Each persona is a pure function returning model data dicts
- `transaction.atomic()` for all-or-nothing seeding
- Idempotent (skips existing accounts without `--reset`)
- Password printed to stdout on creation: `DigniFi-Demo-2026!`

---

## 3. Playwright E2E Test Journeys

### File Structure

```
frontend/e2e/
├── playwright.config.ts
├── fixtures/
│   └── personas.ts             # Typed persona data
├── pages/                      # Page Object Model
│   ├── landing.page.ts
│   ├── register.page.ts
│   ├── login.page.ts
│   ├── wizard.page.ts          # All 6 steps abstracted
│   └── dashboard.page.ts
└── journeys/
    ├── maria-happy-path.spec.ts
    ├── james-borderline.spec.ts
    ├── priya-ineligible.spec.ts
    ├── deshawn-assets.spec.ts
    └── sarah-simplest.spec.ts
```

### Configuration
- **Browser:** Chromium only (cross-browser deferred to public beta)
- **Base URL:** `http://localhost:5173` (Vite dev server)
- **Timeouts:** 30s navigation, 10s action

### Per-Journey Assertions
1. Registration + login (fresh account each run)
2. Wizard steps 1-6 with persona-specific data entry
3. Real-time means test preview appears at step 2+
4. UPL disclaimers render at every decision point
5. Review step shows correct summary
6. UPL confirmation modal requires acknowledgment
7. Form dashboard shows all 13 form types
8. Generate All produces forms (eligible) or ineligibility message (Priya)
9. Form status badges update correctly
10. Skip navigation works (keyboard Tab + Enter)

### Special Journey Behaviors
- `priya-ineligible.spec.ts`: Verifies rejection uses dignity-preserving language
- `deshawn-assets.spec.ts`: Validates exemption calculations in form previews
- All journeys assert zero console errors and zero uncaught exceptions

### CI Integration
New job in `.github/workflows/ci.yml`: starts Docker dev environment, runs
`npx playwright test`.

---

## 4. Analytics Events

Lightweight event logging using existing `AuditLog` infrastructure. No
third-party analytics — keeps PII in-house for this sensitive population.

### Event Schema

| PRD Metric | Event Name | Payload | Trigger |
|---|---|---|---|
| Task completion | `wizard_step_completed` | `{step, duration_ms, session_id}` | Step "Next" click |
| Abandonment | `wizard_abandoned` | `{last_step, total_time_ms, session_id}` | Inactivity >30 min |
| Error rate | `form_validation_error` | `{step, field, error_type}` | Client validation failure |
| Time to complete | `intake_completed` | `{total_duration_ms, steps_revisited}` | Wizard completion |
| Comprehension | `survey_response` | `{question_id, score, session_id}` | Survey submission |
| Dignity score | `survey_response` | `{question_id, score, session_id}` | Survey submission |
| Means test viewed | `means_test_previewed` | `{step, eligible, session_id}` | Preview renders result |
| Form generated | `form_generated` | `{form_type, session_id}` | Generation triggered |

### Implementation
- `frontend/src/utils/analytics.ts` — thin `trackEvent(name, payload)` function
- `POST /api/audit/events/` — new endpoint using existing `AuditLog` model
- Dev/demo mode: also logs to `console.debug` for Playwright assertion capture

---

## 5. Post-Task Survey

A 5-question modal appearing after intake completion. Not a separate app —
a React component posting to the audit endpoint.

### Questions (from PRD Experiment 1 metrics)

1. "How easy was this to understand?" (1-5 scale)
2. "Did you feel respected while using this?" (1-5, dignity metric)
3. "Would you feel confident filing these forms?" (1-5)
4. "What was confusing?" (open text)
5. "What would you change?" (open text)

---

## 6. AI-Simulated Persona Testing (Novel Pattern)

### Architecture

```
Main agent (orchestrator)
├── Subagent 1: Maria Torres        ─── Playwright session 1
├── Subagent 2: James Washington    ─── Playwright session 2
├── Subagent 3: Priya Sharma        ─── Playwright session 3
├── Subagent 4: DeShawn Mitchell    ─── Playwright session 4
└── Subagent 5: Sarah Chen          ─── Playwright session 5
```

All 5 run in parallel. Each subagent:

1. Receives a persona brief (demographics, tech literacy, emotional state,
   behavioral patterns) — NOT codebase knowledge
2. Opens the app in Playwright (Chromium)
3. Registers a fresh account
4. Navigates the wizard, entering persona-appropriate data
5. Makes persona-realistic mistakes (e.g., Maria enters annual income in
   the monthly field)
6. Notes moments of confusion, hesitation, or friction
7. Completes or abandons the flow (persona-dependent)
8. Answers the 5 survey questions in character
9. Returns a structured report

### Key Constraint
Subagents interact with the app ONLY through the browser. They see what's
rendered, not source code. This prevents "cheating" past UX problems.

### Subagent Output Format

```json
{
  "persona": "Maria Torres",
  "completed": true,
  "estimated_time_minutes": 35,
  "friction_points": [
    {"step": 2, "description": "...", "severity": "high|medium|low"},
  ],
  "mistakes_made": [
    {"step": 3, "description": "Entered annual as monthly income", "recovered": true},
  ],
  "survey": {
    "comprehension": 4,
    "dignity": 5,
    "confidence": 3,
    "confusing": "The exemption part was hard to understand",
    "change": "Explain what happens to my car more clearly"
  },
  "narrative": "First-person 'user voice' summary of the experience..."
}
```

---

## 7. Aggregated Reporting

### Report Location
`docs/reports/YYYY-MM-DD-usability-test.md`

### Report Structure

```markdown
# Usability Test Report — AI-Simulated Personas
Date: YYYY-MM-DD
Method: Subagent-driven Playwright testing (5 personas)

## PRD Stop Rule Check
| Metric              | Threshold | Result | Status |
|---------------------|-----------|--------|--------|
| Completion rate     | >85%      | X/5    | PASS/FAIL |
| Critical error rate | <10%      | X%     | PASS/FAIL |
| Mean comprehension  | >3.5      | X.X    | PASS/FAIL |
| Mean dignity score  | >3.5      | X.X    | PASS/FAIL |

## Per-Persona Results
[Detailed per-persona sections with friction, survey, narrative]

## Aggregated Friction Points (ranked by frequency)
1. [Issue seen by N/5 personas]
2. ...

## Recommendations
- P0 fixes (blocking issues found)
- P1 improvements (before real user testing)
```

---

## Dependency Summary

```
seed_demo_data command ──────────────────────┐
                                             │
analytics.ts + /api/audit/events/ ──────┐    │
                                        │    │
post-task survey component ────────┐    │    │
                                   │    │    │
Playwright Page Objects ──────┐    │    │    │
                              v    v    v    v
                     E2E Journey Specs
                              │
                              v
                 Subagent Persona Testing
                              │
                              v
                   Aggregated Report
```

**Parallelism:** Seed command, analytics, survey component, and Page Objects
can all be built simultaneously. Journey specs depend on Page Objects.
Subagent testing depends on everything above.
