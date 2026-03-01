# Running AI Persona Tests

## Prerequisites

```bash
# 1. App running
docker compose up

# 2. Demo data seeded
docker compose exec backend python manage.py seed_demo_data

# 3. Playwright browser installed
cd frontend && npx playwright install chromium

# 4. Verify E2E specs pass first (deterministic baseline)
cd frontend && npm run e2e
```

## Execution Protocol

### Step 1: Launch 5 Subagents in Parallel

The orchestrator (main Claude session) launches 5 subagents using the
Agent tool with `subagent_type: "general-purpose"`. All 5 launch in a
single message for maximum parallelism.

Each subagent receives:

1. **The persona brief** — read from `docs/testing/persona-briefs/<name>.md`
2. **The webapp-testing skill** — invoked via `/webapp-testing`
3. **The output format** — JSON schema from the README
4. **The constraint** — "You have NO access to source code. Interact ONLY
   through the browser. You ARE this person."

### Step 2: Subagent Prompt Template

```
You are about to test a web application called DigniFi as a specific
person. Read the persona brief below carefully — you ARE this person.

PERSONA BRIEF:
[contents of docs/testing/persona-briefs/<name>.md]

INSTRUCTIONS:
1. Use the webapp-testing skill to interact with the app at
   http://localhost:5173
2. Navigate as your persona would — at their pace, with their
   hesitations, making their likely mistakes
3. Enter ALL the data from "Your Data" section exactly as listed
4. Note every moment of confusion, friction, or emotional reaction
5. Complete the post-task survey IN CHARACTER
6. Return a JSON report (schema below)

CONSTRAINTS:
- You have NO access to source code — browser only
- Do NOT skip steps or rush — your persona's pace matters
- Note timestamps for each major action
- Take screenshots at friction points

OUTPUT FORMAT:
{
  "persona": "<name>",
  "completed": boolean,
  "completion_time_seconds": number,
  "steps_completed": number,
  "friction_points": [
    {
      "step": "step_name",
      "timestamp": "ISO-8601",
      "description": "what happened",
      "severity": "low|medium|high",
      "emotional_reaction": "how the persona felt",
      "suggestion": "what would help"
    }
  ],
  "survey_responses": {
    "comprehension": 1-5,
    "dignity": 1-5,
    "confidence": 1-5,
    "confusing": "free text",
    "change": "free text"
  },
  "trust_score": 1-5,
  "would_recommend": boolean,
  "qualitative_notes": "paragraph from persona's perspective",
  "accessibility_issues": ["list of any a11y problems noticed"],
  "language_issues": ["jargon or confusing terms encountered"]
}
```

### Step 3: Collect Reports

After all 5 subagents complete, the orchestrator collects the 5 JSON
reports. If a subagent fails or times out, record it as:

```json
{
  "persona": "<name>",
  "completed": false,
  "failure_reason": "description of what went wrong"
}
```

### Step 4: Aggregate Results

The orchestrator computes:

| Metric | Calculation |
|--------|-------------|
| **Completion rate** | count(completed=true) / 5 |
| **Mean comprehension** | avg(survey_responses.comprehension) |
| **Mean dignity** | avg(survey_responses.dignity) |
| **Mean confidence** | avg(survey_responses.confidence) |
| **Friction density** | total friction_points / 5 |
| **High-severity count** | count(severity="high") |
| **Trust score** | avg(trust_score) |
| **NPS proxy** | count(would_recommend=true) / 5 |

### Step 5: Rank Friction Points

1. Group friction_points by `step`
2. Sort by frequency (most common first)
3. Within each step, sort by severity (high > medium > low)
4. Top 5 become the actionable findings

### Step 6: Write Report

Save to `docs/reports/YYYY-MM-DD-usability-test.md` with:

```markdown
# Usability Test Report — YYYY-MM-DD

## Summary Metrics
[table of metrics vs targets]

## Stop Rule Evaluation
- Completion: [pass/fail]
- Dignity: [pass/fail]
- Action: [continue / pause / redesign / celebrate]

## Top Friction Points
[ranked list with persona context]

## Per-Persona Summaries
[brief narrative for each]

## Recommendations
[prioritized list of changes]

## Raw Data
[link to individual JSON reports]
```

### Step 7: Evaluate Stop Rules

From the PRD experiment plan:

| Condition | Action |
|-----------|--------|
| 2+ personas cannot complete | **PAUSE** — fix blockers before continuing |
| Mean dignity < 3.0 | **REDESIGN** — fundamental tone/language issues |
| All 5 complete, mean dignity >= 4.0 | **CELEBRATE** — ready for real user testing |
| 1 persona fails, dignity >= 3.5 | **ITERATE** — fix specific issue, rerun |

## Quick-Start Command

For the orchestrator to copy-paste:

```
Launch 5 subagents in parallel using Agent tool (subagent_type:
"general-purpose"). For each persona (maria-torres, james-washington,
priya-sharma, deshawn-mitchell, sarah-chen):

1. Read docs/testing/persona-briefs/<name>.md
2. Invoke /webapp-testing skill
3. Navigate http://localhost:5173 as the persona
4. Return JSON report per the schema above

After all 5 complete, aggregate results into
docs/reports/YYYY-MM-DD-usability-test.md
```
