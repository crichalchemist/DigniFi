# AI Persona Testing Protocol

## Overview

Five AI subagents, each embodying a synthetic persona, navigate the live
DigniFi application through Playwright and report usability findings from
a human perspective. This produces quantitative PRD metrics and qualitative
UX insights before real participant recruitment.

Personas are adapted from the PRD UX research personas
(`Product Docs/UI_UX_RESEARCH.md`) to exercise distinct eligibility paths
through the ILND means test calculator.

## Persona Briefs

| Brief | Archetype | Means Test | Key Test |
|-------|-----------|------------|----------|
| `maria-torres.md` | Below-median single parent | Passes, fee waiver | Full happy path |
| `james-washington.md` | Borderline single filer | Passes (barely) | Near-threshold messaging |
| `priya-sharma.md` | Above-median family | Fails | Dignity-preserving ineligibility |
| `deshawn-mitchell.md` | Asset-heavy homeowner | Passes | Multi-asset entry, exemptions |
| `sarah-chen.md` | Simplest case, no assets | Passes, fee waiver | Fastest path, empty-state handling |

## How to Run

### Prerequisites

```bash
# 1. Start the app
docker compose up

# 2. Seed demo data (for login-based tests)
docker compose exec backend python manage.py seed_demo_data

# 3. Install Playwright browser
cd frontend && npx playwright install chromium
```

### Automated E2E (Playwright — no AI)

```bash
cd frontend && npm run e2e
```

This runs 5 journey specs that exercise each persona's data path
programmatically. No AI involved — pure deterministic E2E testing.

### AI Persona Simulation (subagent-driven)

The orchestrator (main Claude session) launches 5 subagents in parallel
using the Agent tool:

1. Each subagent receives its persona brief
2. Each navigates the app via Playwright (browser only, no source code access)
3. Each returns a structured JSON report
4. Orchestrator aggregates into usability findings

See `docs/testing/run-persona-tests.md` for the full protocol.

## Expected Output Format

Each subagent returns a JSON report:

```json
{
  "persona": "maria_torres",
  "completed": true,
  "completion_time_seconds": 480,
  "friction_points": [
    {
      "step": "debtor_info",
      "description": "SSN field asked too early — felt invasive",
      "severity": "high",
      "screenshot": "maria-step1-ssn.png"
    }
  ],
  "survey_responses": {
    "comprehension": 4,
    "dignity": 5,
    "confidence": 3,
    "confusing": "I didn't understand what 'means test' meant",
    "change": "Explain legal terms when they first appear"
  },
  "trust_score": 4,
  "would_recommend": true,
  "qualitative_notes": "The tone felt respectful throughout..."
}
```

## PRD Metrics Evaluated

| Metric | Target | Measurement |
|--------|--------|-------------|
| Completion rate | 100% (5/5 personas complete) | `completed` field |
| Mean comprehension | >= 3.5 / 5 | `survey_responses.comprehension` |
| Mean dignity | >= 4.0 / 5 | `survey_responses.dignity` |
| Mean confidence | >= 3.5 / 5 | `survey_responses.confidence` |
| Friction points per persona | <= 3 high-severity | `friction_points` count |

## Stop Rules

From the PRD experiment plan:

- **Pause if:** 2+ personas cannot complete the wizard
- **Redesign if:** Mean dignity score < 3.0
- **Celebrate if:** All 5 complete with mean dignity >= 4.0
