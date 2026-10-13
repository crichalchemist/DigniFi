# Forms Step 2a (Data and Flow) Implementation Plan, Part 1 of 2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make what the filer gives reach the forms intact, and make the flow honest. Forms are prepared only from a completed intake. Every save keeps every field. Income is stored by source, with Social Security left out of CMI. The means test is right at the median and is worked out again before every packet. The fee-waiver page asks what Form 103B asks.

**Architecture:** 2a changes data, saves and the generate flow, and moves no binding. Its one oracle change re-keys tier 2's cases on the binding, which changes how a case is named, not what any box prints. The 14 tasks follow the spec's seven 2a commits in order. Commits 2, 3 and 5 are split into several tasks, one commit each, and every task boundary passes every gate. The bindings are 2b, which gets its own plan once this one merges.

**This part:** Tasks 1–8, the spec's commits 1–3. Part 2 (`docs/superpowers/plans/2026-10-12-forms-step2a-part2.md`) holds Tasks 9–14 and starts once this part's eight tasks are committed. The plan is split in two only to stay under the repository's 500 KB file limit. Run both parts as one execution: one ledger for Tasks 1–14, and the whole-branch final review only after Task 14, because Part 2's patches expect each file exactly as Part 1's tasks leave it.

**Tech Stack:** Django 5.0 + DRF (Python 3.11), pypdf 6.13.1, encrypted-model-fields, pytest + pytest-django; React 19 + TypeScript, vitest + MSW; Playwright.

**Spec:** `docs/superpowers/specs/2026-10-12-forms-step2-design.md` (approved 2026-10-12; the reopening amendment is commit 3383404). Read §1–§5, §7, §8 and §9 before Task 1. It is the authority this plan argues from. Section 6 and Appendix A's binding changes are 2b, not this plan.

**How this plan was checked:**

- Each task's code was built and committed in order on the local branch `plan/forms-step2a`. Every task ended with every gate green, and an adversarial review approved each commit.
- The plan was then dry-run from its own text in a fresh worktree, and after every task the tree matched the verified commit exactly.
- Final tree: backend `1776 passed, 143 xfailed`, vitest `320 passed`. Journeys: both runs passed at every task that runs them (Tasks 2–7 and 9–14) in the dry-run, and in the build (at Task 5 one build run lost a journey to a slow Generate All under outside load, and a rerun passed both).

## Global Constraints

- **Single filer only.** Joint filing is out, and the wizard still offers it (DIG-177).
- **Empty is not zero** (§5.2): "An amount the filer never gave is stored as empty (NULL), never as 0, unless an existing column already defaults to 0 (the 13 expense amounts)."
- **Refusals** (§5.2): "A refusal speaks plain words and names what to do. It is a 422 when the filer can fix it, and a 500 logged by exception type only when operations must. The one exception is the means-test endpoint, which keeps its existing 400 for a refusal the filer can fix."
- **Bounded amounts** (§5.2): "Every new or changed write path bounds its amounts: zero or more, finite, within the column."
- **No binding moves** (§5.1). No schema in `data/forms/schemas/` changes in 2a.
- **Known defects** (§4): "Each commit deletes exactly the known-defect entries it clears and never adds one." `backend/apps/forms/tests/known_defects.json` changes only where a task says so.
- **Logging:** a 500 logs only the exception's type, with `logger.error`, never its message or a traceback (DIG-105). Logs never carry filer data.
- **Privacy** (§8): the API never returns `field_values`. The ten income amounts are plain decimals like the expense amounts; `monthly_take_home_pay` is encrypted like the fee waiver's other amounts.
- **UPL:** user-facing text is legal information, never advice (`docs/UPL_COMPLIANCE.md`). Use the sentences this plan gives word for word; don't write new filer-facing copy.
- **Test data** is synthetic only, with SSNs from the IRS-reserved 900 range.
- **Gates** (§7.1): every commit leaves backend pytest with coverage at 90% or more, `manage.py check`, ruff 0.8.5, vitest, tsc, eslint and prettier green. The 7 journeys run on every task that changes a page or the flow.
- **Lint:**
  - ruff 0.8.5 (`ruff check backend/`, as CI runs it).
  - Pre-commit runs black 24.10.0 (line length 100) on `backend/`, prettier 3.4.2 on JSON, Markdown and TypeScript outside `backend/`, and eslint on the frontend.
- **Never run `tsc -b`.** It writes build output through the `node_modules` symlink into the main checkout. Use `tsc -p tsconfig.app.json --noEmit` and `tsc -p tsconfig.node.json --noEmit`.
- **Commit messages** end with the last line about the change. **Add no `Co-Authored-By`, `Claude-Session` or other agent trailer, even if your harness asks for one.**
- **Staging:** stage files by explicit path only, never with `git add -A`, `git add .` or `git commit -a`. Commit only the files the task lists.
- **No outward actions:** no push, PR, merge, deploy or production command. Those are the owner's decisions.
- **Databases:** never use the shared development database `dignifi_dev`. This plan makes its own.
- **Keys:** never print, log or commit an API key. This plan does not use the repo-root `.env`; the journeys use a dummy key against a fake OpenAI server.

## Before you start (once per worktree)

- Work in `/Volumes/Containers/DigniFi/.claude/worktrees/forms-step2` (branch `feat/forms-step2`). Every command block runs from that worktree's root.
- Backend tools come from the main checkout's virtualenv, and frontend tools from its `node_modules`. Pre-commit's eslint hook expects that symlink.
- The journeys need Colima running, with the `dignifi-db-1` Postgres container answering on host port 5433, and nothing listening on ports 8000, 5173 or 4010.
- `pytest` uses `config.settings.test` (sqlite in memory). `manage.py` and the journeys use the database below.

```bash
set -eo pipefail
mkdir -p backend/logs .claude   # the audit log handler needs backend/logs; CI creates it too
[ -e frontend/node_modules ] || ln -s /Volumes/Containers/DigniFi/frontend/node_modules frontend/node_modules
# CI's synthetic Fernet key (it encrypts nothing real), read from ci.yml rather than copied here
FERNET=$(sed -n 's/^ *FIELD_ENCRYPTION_KEY: //p' .github/workflows/ci.yml | head -1)
[ -n "$FERNET" ]
# A database of its own keeps the shared dev database on main's migrations.
docker exec dignifi-db-1 dropdb -U dignifi --if-exists dignifi_forms_step2a
docker exec dignifi-db-1 createdb -U dignifi dignifi_forms_step2a
cat > .claude/forms-step2a.env <<ENV
# Settings for forms step 2a (git-ignored). Source from the worktree root.
export PY=/Volumes/Containers/DigniFi/backend/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_forms_step2a
export DJANGO_SECRET_KEY=test-only-not-a-secret
export DEBUG=True
export ALLOWED_HOSTS=localhost,127.0.0.1
export CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
export FIELD_ENCRYPTION_KEY=$FERNET
export OCR_PROVIDER=openai
export OPENAI_API_KEY=e2e-dummy-key
export OPENAI_BASE_URL=http://127.0.0.1:4010/v1
ENV
source .claude/forms-step2a.env && $PY -c "import pypdf; assert pypdf.__version__ == '6.13.1', pypdf.__version__"
git check-ignore -q .claude/forms-step2a.env && git check-ignore -q .claude/e2e.sh && echo "env file is ignored"
```

Expected: `env file is ignored`.

The journeys run through one script, which every task marked for them calls. Write it now:

```bash file=.claude/e2e.sh
#!/bin/zsh
# Run the 7 Playwright journeys on this worktree's own database.
# usage (from the worktree root): zsh .claude/e2e.sh [runs=2]
# Migrates, loads the district data, reseeds the personas, starts runserver (:8000)
# and Vite (:5173), runs the journeys RUNS times, prints one summary line per run,
# and always stops both servers. Logs: .claude/e2e-logs/.
set -u
RUNS=${1:-2}
cd "$(git rev-parse --show-toplevel)" || exit 2
source .claude/forms-step2a.env
export DJANGO_SETTINGS_MODULE=config.settings.development PYTHONUNBUFFERED=1
LOG="$PWD/.claude/e2e-logs"
rm -rf "$LOG"; mkdir -p "$LOG"

for port in 8000 5173 4010; do
  if lsof -nP -iTCP:$port -sTCP:LISTEN >/dev/null 2>&1; then
    echo "PORT $port BUSY: stop whatever holds it first"; exit 3
  fi
done

( cd backend && $PY manage.py migrate -v 0 && $PY manage.py loaddata ilnd_2025_data -v 0 \
  && $PY manage.py seed_demo_data --reset ) > "$LOG/setup.log" 2>&1 || { echo "SETUP FAILED"; tail -20 "$LOG/setup.log"; exit 4; }

( cd backend && exec $PY manage.py runserver 0.0.0.0:8000 --noreload ) > "$LOG/backend.log" 2>&1 &
BPID=$!
( cd frontend && exec ./node_modules/.bin/vite --port 5173 --strictPort ) > "$LOG/vite.log" 2>&1 &
FPID=$!
cleanup() { kill $BPID $FPID 2>/dev/null; wait $BPID $FPID 2>/dev/null; }
trap cleanup EXIT INT TERM

up() { $PY -c "import urllib.request,sys; urllib.request.urlopen(sys.argv[1], timeout=2)" "$1" >/dev/null 2>&1; }
for i in {1..60}; do up http://127.0.0.1:8000/health/ && up http://localhost:5173/ && break; sleep 1; done
up http://127.0.0.1:8000/health/ || { echo "BACKEND NOT UP"; tail -20 "$LOG/backend.log"; exit 5; }
up http://localhost:5173/ || { echo "VITE NOT UP"; tail -20 "$LOG/vite.log"; exit 5; }

overall=0
for r in $(seq 1 $RUNS); do
  ( cd frontend && npx playwright test --config e2e/playwright.config.ts --reporter=line ) > "$LOG/run$r.log" 2>&1
  rc=$?
  perl -pe 's/\e\[[0-9;]*[A-Za-z]//g' "$LOG/run$r.log" > "$LOG/run$r.txt"
  summary=$(grep -E "^\s*[0-9]+ (passed|failed|flaky|skipped|did not run)" "$LOG/run$r.txt" | tr -s ' ' | tr '\n' ' ' | sed 's/^ //')
  echo "RUN $r exit=$rc: $summary"
  if [ $rc -ne 0 ]; then
    overall=1
    grep -E "^\s+[0-9]+\) " "$LOG/run$r.txt" | head -10
  fi
done
exit $overall
```

It migrates the step's database, loads the district data, reseeds the personas, starts the backend on :8000 and Vite on :5173, runs the 7 journeys `RUNS` times, prints one line per run, and always stops both servers. Its logs land in `.claude/e2e-logs/`. A failed run prints the failing journeys; read the trace under `frontend/test-results/` before running again, and don't retry blindly.

Check the baseline before Task 1:

```bash
set -eo pipefail
source .claude/forms-step2a.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -3)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `1609 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  250 passed (250)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

## How to read the code blocks

- **`<language> file=<path>` blocks:** the block is the file's complete content. Create or overwrite the file with exactly that text.
- **`bash` blocks:** run from the worktree root in a fresh shell (bash or zsh). Each block starts with `set -eo pipefail`, so any command that fails, including one inside a pipeline, stops the block and fails it. A block sources `.claude/forms-step2a.env` itself when it needs it.
- **`git apply <<'PATCH'` blocks:** these patch the state the previous task left. If one doesn't apply, stop: the tree has drifted from the plan.
- **"Expected:" lines** say what the command must do. An "Expected: FAIL" step is the red half of test-first. Every other step must succeed.
- **Commit blocks** use each task's verified commit message. A pre-commit hook that rewrites a file means the tree has drifted from the plan: stop and compare.

## Decisions already made

These rulings were settled while the plan was built: by the owner where marked, otherwise by the plan's author against the spec. Every task's code already follows them. Don't reopen them in review. A task that depends on one repeats it in its own text.

- **Seven spec commits, fourteen tasks.** The spec's commits 2, 3 and 5 are split into several tasks, one commit each, in the spec's order, and every task boundary passes every gate. Commit 4 (income per source) and commit 6 (the fee-waiver page) stay one task each, because each stops writing an old column, and everything that reads that column has to move with it.
- **Tier 2's coverage count starts at 425** (§7.4, "the coverage count"). Task 1 pins it.
- **Tier 3's blank expectations and Appendix D's rows (§7.5) are 2b's.** No task here touches them.
- **`update_step` with anything but a whole number from 1 to 8 is a 400.** It is a client fault, not something the filer can fix, so it is not a 422.
- **The step 1 spec's §5.6 amendment** (122A-2 on `>`, pointing at the step 2 spec) lands with the median tie, in Task 10.
- **Known defects** (§7.3): 2a should clear few or none. A task whose change makes a listed case pass (XPASS) or orphans an entry deletes exactly that entry and says so. A new failing oracle case, or an XPASS whose cause you can't name, is a spec problem: stop and report it. Don't patch around it. No task in this plan deletes or adds an entry, apart from Task 1's re-key, which changes only the `case` value of the 81 tier 2 entries.
- **Every intake-data write reopens a completed intake** (owner, 2026-10-12; §5.3 "Reopening"). One server helper, `IntakeSession.reopen()`, sets a completed session back to `in_progress`, so the filer presses Complete again. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it.
- **The Income step's help text** (owner, 2026-10-13). A filer with no income who leaves all ten Income boxes blank is refused by the means test (`IncomeNotSplit`). Only one sentence of the help text changes: "If you don't have income from a source, you can leave it blank or enter $0." becomes exactly "Leave a box blank if you don't get that kind of income. If you have no income at all, enter $0 in any box." The sentence "Enter your average monthly income before taxes." stays, and so does the `IncomeNotSplit` sentence from §5.5. A blank box is still never saved as $0 unless the filer typed it.
- **Review shows the means test's own refusal.** When the means-test call in `handleComplete` fails with a 400, Review shows that response's own `error` sentence (the `IncomeNotSplit` sentence). It is carried on `APIClientError.serverError` and read only by `IntakeContext.calculateMeansTest`. `apiFetch`'s preference for `message` stays unchanged for every other caller.
- **Review's "Total Monthly Income" shows $0.00 when no amount was given.** It is a summary row, not a form box, so the blank-when-empty rule for forms doesn't apply.
- **A district with no median data.** With the ruling above, Review shows the means-test endpoint's raw 400 text for it. That is accepted for 2a: it is an operations fault (the ILND data is loaded), and the endpoint's 400 for it is a separate defect.
- **The fee-waiver IDOR is closed here** (owner, 2026-10-12; DIG-178). A PATCH can't move a fee-waiver application onto another user's session. Task 13 does it the way the asset and debt viewsets do, with `_assert_session_owned` in `perform_update` (a 403).
- **Creating a fee-waiver application requires both new answers** (a JSON create without them is a 400, which is how the page sends it; a form-encoded create that leaves out the yes/no answer still stores No, which 2b closes before it binds 103B line 3). This is stricter than §5.7's page-level "An answer is required". It matches "empty until answered" for older rows, because a PATCH may still send either answer alone, and it stops a misnamed key from being dropped silently (the DIG-120 class).
- **Copy:** use only the sentences this plan gives. Where a task needed words the spec doesn't give, it reuses a sentence the app already shows, and the task says which one.

## Spec coverage

The spec's 2a commits map to tasks as follows: commit 1 is Task 1; commit 2 is Tasks 2–3; commit 3 is Tasks 4–8; commit 4 is Task 9; commit 5 is Tasks 10–12; commit 6 is Task 13; commit 7 is Task 14.

| Spec                                                                                                                                    | Task                                     |
| --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| §7.2 oracle re-key (DIG-173); §7.4 the coverage count                                                                                   | 1                                        |
| §5.3 the completion check: read-only `status` and `current_step` (DIG-151), `update_step` bounds, the 422, reopening a completed intake | 2                                        |
| §5.3 the blank-expenses trap (DIG-153)                                                                                                  | 2                                        |
| §5.3 the client: Review keeps a failed Complete (DIG-150), the dashboard's "Finish your intake", autosave skips unchanged saves         | 3                                        |
| §5.4 contracts and codebtors saved as whole lists (DIG-147, DIG-165, DIG-166)                                                           | 4                                        |
| §5.4 the secured flag and its backfill (DIG-26), personal property (DIG-47); §7.8 secured backfill                                      | 5                                        |
| §5.4 the phone number (DIG-120), a cleared expense saves $0 (DIG-55)                                                                    | 6                                        |
| §5.4 waiver filers reach SOFA (DIG-149), the half-filled SOFA row (DIG-148); §7.9 the waiver journeys go through SOFA                   | 7                                        |
| §7.6 the read-back through the API (DIG-140)                                                                                            | 8; grows in 9 and 13                     |
| §5.5 income per source; §7.8 income migration                                                                                           | 9                                        |
| §5.6 the median tie (DIG-136), one rounding, the DIG-128 reset and message                                                              | 10                                       |
| §5.6 recalculated every time, when it can't run, filed forms (DIG-155, DIG-160)                                                         | 11                                       |
| §5.6 the dashboard shows a whole-call refusal (DIG-156)                                                                                 | 12                                       |
| §5.7 the fee-waiver page and data; §7.8 fee-waiver columns; §7.9 the fee-waiver page object                                             | 13                                       |
| §5.8 docs: persona briefs (DIG-141) and CLAUDE.md                                                                                       | 14                                       |
| §7.3 known defects, commit by commit                                                                                                    | every task                               |
| §7.7 tests named for what they protect                                                                                                  | 2, 3, 4, 9, 10, 11                       |
| §8 security and UPL                                                                                                                     | every task; DIG-151 in 2                 |
| §9 success criteria 1, 4, 5, 6, 7 and 8 (2 and 3 are 2b's)                                                                              | every task; 2; 9 and 10; 8; 11; 7 and 13 |

---

### Task 1: Key tier 2 oracle cases on the box and the binding

_Built and verified as commit `acb96d0` on `plan/forms-step2a`._

**Files:**

- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/oracle.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `docs/superpowers/specs/2026-10-10-forms-foundation-design.md`

**Interfaces:**

- Consumes: step 1's oracle. That is `apps/forms/tests/oracle.py` (`case_param`, `load_known_defects`), `test_oracle_tier2.py`, the audit rows in `data/forms/field_index/audit/` with `verification.json`, and the recorder `data/forms/field_index/tools/record_known_defects.py`.
- Produces:
  - Tier 2's `case` is the binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so a known-defect entry names the binding it convicts.
  - `ASSERTED_CASES = 425` in `test_oracle_tier2.py`, checked by `test_tier2_coverage_changes_only_on_purpose`. A later task that changes how many tier 2 cases are asserted changes this number on purpose.
  - `known_defects.json` with the same 142 entries, of which the 81 tier 2 entries now carry their binding key in `case`.

**Decisions already made in this task:**

- An audit row joins a binding on `(box, key)`, with the producer spellings normalized. With no exact row, a checked row with the same key that names this box as its right one asserts it ("moved here"). Constants are excluded, and anything else stays unasserted.
- When an exact `(box, key)` row exists but nobody checked it, the case is unasserted, and the moved-here join is not tried.
- No result changes: 425 cases are asserted, 344 pass and 81 xfail, before and after.

- [ ] **Step 1: Re-key tier 2 on the binding**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/oracle.py b/backend/apps/forms/tests/oracle.py
index d6ca4f8..55f0315 100644
--- a/backend/apps/forms/tests/oracle.py
+++ b/backend/apps/forms/tests/oracle.py
@@ -1,10 +1,12 @@
 """
 Shared pieces of the court-form oracle (spec §6): case keys and the known-defects list.

-Every oracle case has a key (form_type, pdf_field, tier, case). A key listed in
-known_defects.json runs as a strict expected failure, so a new break fails CI
-and so does a fix until its entry is deleted. test_known_defects.py fails on an
-entry that matches no generated case.
+Every oracle case has a key (form_type, pdf_field, tier, case). `case` is the
+persona for tier 3, the choice key for a tier 1 checkbox case and the binding key
+for tier 2; otherwise it is empty. A key listed in known_defects.json runs as a
+strict expected failure, so a new break fails CI and so does a fix until its
+entry is deleted. test_known_defects.py fails on an entry that matches no
+generated case.
 """

 import json
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index 151ea42..a353b7a 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -1,10 +1,15 @@
 """
 Oracle tier 2: each binding targets the box the verified audit says it should (spec §6).

-Bindings join their audit rows through the conversion report's old→new name
-map. A binding is asserted only where the audit was checked against the page
-image: a verification.json row, or a target widget whose index basis is
-adjudicated or sampled_ok. Everything else is unverified and not asserted.
+A case is keyed on its box and its binding key, `<source>:<producer>` (step 2
+spec §7.2), so a binding re-ruled in place or moved onto a listed box is a new
+case and never keeps an old verdict. Bindings join their audit rows through the
+conversion report's old→new name map, on (box, key). A binding is asserted only
+where the audit was checked against the page image: a verification.json row, or
+an index basis of adjudicated or sampled_ok on the row's own box. With no row
+for its box and key, a binding that a checked row with its key places on this
+box was moved here, and passes; a constant never was. Everything else is
+unverified and not asserted.
 """

 import json
@@ -16,12 +21,13 @@ from django.conf import settings

 from apps.forms.field_index import load_index
 from apps.forms.registry import get_all_form_types
-from apps.forms.schema import load_schema
+from apps.forms.schema import FieldSpec, load_schema
 from apps.forms.tests.oracle import case_param

 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
+ASSERTED_CASES = 425


 def _audit_dir():
@@ -46,29 +52,69 @@ def _renamed(form_type):
     return report["forms"][form_type]["renamed"]


-def _expected_target(form_type, pdf_field):
-    """The full name the audit wants, LEAVE_BLANK, None for "not this box", or "" if unasserted."""
-    old = {new: old for old, new in _renamed(form_type).items()}.get(pdf_field, pdf_field)
+def _binding_key(binding):
+    """`<source>:<producer>`, the producer empty for signature and presume (step 2 spec §7.2)."""
+    if binding.source in ("signature", "presume"):
+        return f"{binding.source}:"
+    producer = binding.rule or binding.binding or binding.value or binding.ingest_key or ""
+    return f"{binding.source}:{producer}"
+
+
+def _audit_key(row):
+    """An audit row's producer spelled as a binding key (step 2 spec §7.2)."""
+    producer = re.sub(r"^(rule:|rule |binding:|ingest_key:)", "", row["producer"])
+    producer = re.sub(r" \(.*\)$", "", producer)
+    return f"{row['source']}:{'' if producer == row['source'] else producer}"
+
+
+def _checked(form_type, old):
+    """(target, verdicts) of the audit row on box `old`, or None if nobody checked it."""
     verified = _verification().get((form_type, old))
-    row = verified or _audit(form_type).get(old)
-    widgets = load_index(load_schema(form_type).template_filename)[pdf_field]
-    if row is None or not (verified or {w.basis for w in widgets} & CHECKED_BASES):
-        return ""
-    target = (verified["correct_target"] if verified else row["correct_target"]) or ""
-    verdicts = verified["final_verdicts"] if verified else row["verdicts"]
-    if not target:
-        # Right box when the audit found no box fault; a wrong box with no recorded target.
-        return None if "wrong_box" in verdicts else pdf_field
+    if verified:
+        target, verdicts = verified["correct_target"], verified["final_verdicts"]
+    else:
+        row = _audit(form_type)[old]
+        box = _renamed(form_type).get(old, old)
+        widgets = load_index(load_schema(form_type).template_filename).get(box, ())
+        if not {w.basis for w in widgets} & CHECKED_BASES:
+            return None
+        target, verdicts = row["correct_target"], row["verdicts"]
     # "Executed on (needs filler change: ...)" → "Executed on"
-    return re.sub(r"\s*\(.*\)$", "", target)
+    return re.sub(r"\s*\(.*\)$", "", target or ""), verdicts
+
+
+def _expected_target(form_type, binding):
+    """The full name the audit wants, LEAVE_BLANK, None for "not this box", or "" if unasserted."""
+    pdf_field, key = binding.pdf_field, _binding_key(binding)
+    old = {new: old for old, new in _renamed(form_type).items()}.get(pdf_field, pdf_field)
+    row = _audit(form_type).get(old)
+    if row is not None and _audit_key(row) == key:
+        checked = _checked(form_type, old)
+        if checked is None:
+            return ""
+        target, verdicts = checked
+        if not target:
+            # Right box when the audit found no box fault; a wrong box with no recorded target.
+            return None if "wrong_box" in verdicts else pdf_field
+        return target
+    # Moved here. A constant is excluded: a /Yes the audit placed for one question
+    # proves nothing about another.
+    if binding.source != "constant":
+        for other, other_row in _audit(form_type).items():
+            if _audit_key(other_row) != key:
+                continue
+            checked = _checked(form_type, other)
+            if checked and checked[0] == pdf_field:
+                return pdf_field
+    return ""


 def _cases():
     for form_type in get_all_form_types():
         for f in load_schema(form_type).fields:
-            target = _expected_target(form_type, f.pdf_field)
+            target = _expected_target(form_type, f)
             if target != "":
-                yield case_param(form_type, f.pdf_field, TIER, "", target)
+                yield case_param(form_type, f.pdf_field, TIER, _binding_key(f), target)


 CASES = list(_cases())
@@ -79,3 +125,70 @@ def test_binding_targets_the_box_the_audit_verified(form_type, pdf_field, case,
     assert target != LEAVE_BLANK, "wrong_box: the audit says this box stays blank"
     assert target is not None, "wrong_box: the audit says this is the wrong box"
     assert pdf_field == target, f"wrong_box: the audit says it belongs in {target!r}"
+
+
+def test_tier2_coverage_changes_only_on_purpose():
+    # A review tripwire, not a correctness test (step 2 spec §7.4): a commit that
+    # changes how many cases tier 2 asserts updates ASSERTED_CASES and says why.
+    assert len(CASES) == ASSERTED_CASES, "tier 2 coverage changed: update ASSERTED_CASES on purpose"
+
+
+def _field(**kw):
+    # Built from literals that match the audit row, not read from the schema, so
+    # these tests outlive 2b moving or deleting the bindings they describe. Every
+    # producer starts empty: _binding_key takes the first one that isn't.
+    base = {
+        "pdf_field": "F",
+        "type": "text",
+        "source": "derived",
+        "page": 1,
+        "label": "",
+        "required": False,
+        "conditional_on": None,
+        "value": None,
+        "rule": None,
+        "ingest_key": None,
+        "binding": None,
+        "repeat": None,
+        "repeat_capacity": None,
+        "row": None,
+        "legal_review": False,
+    }
+    base.update(kw)
+    return FieldSpec(**base)
+
+
+def test_a_binding_re_ruled_in_place_does_not_inherit_the_old_verdict():
+    # The audit judged rent on Schedule J box 10 (Personal care); another rule there is unjudged.
+    re_ruled = _field(pdf_field="10", rule="schedule_j_personal_care")
+    assert _expected_target("schedule_j", re_ruled) == ""
+
+
+def test_a_binding_moved_to_the_box_the_audit_named_is_asserted_and_passes():
+    # The audit's checked row says rent belongs on line 4, which has no audit row of its own.
+    moved = _field(pdf_field="4", rule="schedule_j_rent_or_mortgage")
+    assert _expected_target("schedule_j", moved) == "4"
+
+
+def test_a_binding_moved_to_a_box_the_audit_did_not_name_stays_unasserted():
+    # That checked row names line 4, not line 7, which has no audit row of its own either.
+    moved = _field(pdf_field="7", rule="schedule_j_rent_or_mortgage")
+    assert _expected_target("schedule_j", moved) == ""
+
+
+def test_a_constant_the_audit_placed_elsewhere_proves_nothing_here():
+    # The audit moved Form 101's /Yes from Check Box16 to Check Box18 for one question only.
+    constant = _field(pdf_field="Check Box18", type="checkbox", source="constant", value="/Yes")
+    assert _expected_target("form_101", constant) == ""
+
+
+@pytest.mark.parametrize(
+    "producer,rule",
+    [
+        ("rule district_name", "district_name"),  # Form 107
+        ("rule:full_name (conditional_on has_joint_filer)", "full_name"),  # Schedules G-J
+    ],
+)
+def test_an_audit_row_spelled_loosely_joins_the_binding_it_names(producer, rule):
+    row = {"source": "derived", "producer": producer}
+    assert _audit_key(row) == _binding_key(_field(rule=rule))
PATCH
```

The patch also adds tests for the join itself: a binding re-ruled in place doesn't inherit the old verdict, a binding moved to the box the audit named is asserted, one moved anywhere else stays unasserted, a constant the audit placed elsewhere proves nothing, and an audit row spelled loosely still joins its binding. The `oracle.py` change is its docstring only.

- [ ] **Step 2: Run tier 2 against the old list and watch it fail**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `82 failed`. The 81 wrong-box cases now carry their binding key, but the list still names them with an empty case, so none of them is an expected failure. The 82nd is the orphan check: all 81 tier 2 entries now match no case.

- [ ] **Step 3: Re-record the list**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY ../data/forms/field_index/tools/record_known_defects.py \
  apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py \
  apps/forms/tests/test_oracle_tier3.py | tail -1
cd .. && git diff --stat -- backend/apps/forms/tests/known_defects.json
```

Expected: `142 entries written`, and the diff stat names only the list, which the recorder rewrites. Its diff changes only the case value of the 81 tier 2 entries. Any other change means the tree has drifted from the plan.

- [ ] **Step 4: Run the three tiers and the list check**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `1068 passed, 142 xfailed`: one expected failure for each listed defect, and no failures.

- [ ] **Step 5: Say in step 1's spec what tier 2's case is**

```bash
git apply <<'PATCH'
diff --git a/docs/superpowers/specs/2026-10-10-forms-foundation-design.md b/docs/superpowers/specs/2026-10-10-forms-foundation-design.md
index f8c8a6b..a7bc3c9 100644
--- a/docs/superpowers/specs/2026-10-10-forms-foundation-design.md
+++ b/docs/superpowers/specs/2026-10-10-forms-foundation-design.md
@@ -343,7 +343,7 @@ All three tiers run in the backend test suite. The budget is about 30 seconds:

 **The known-defects list** is `backend/apps/forms/tests/known_defects.json`.

-- **Entries:** each is keyed by `(form_type, pdf_field, tier, case)`, with its defect class and DIG ticket. `case` is the persona for tier 3 and the choice key for a tier 1 checkbox case; otherwise it's empty. A defect that shows for some personas and not others can therefore be listed exactly.
+- **Entries:** each is keyed by `(form_type, pdf_field, tier, case)`, with its defect class and DIG ticket. `case` is the persona for tier 3, the choice key for a tier 1 checkbox case and the binding key for tier 2 (step 2 spec §7.2); otherwise it's empty. A defect that shows for some personas and not others can therefore be listed exactly.
 - **Strict expected failures:** matching cases are marked `xfail(strict=True)`. A new break fails CI, and so does a fix until its entry is deleted.
 - **No orphans:** the test session fails if any entry matches no test that ran. So the list's length is exactly the number of known defects left.
 - **Who maintains it:** step 1 creates it. Step 2 empties it for collected data, and steps 3 and 4 add and remove entries as their bindings land.
PATCH
```

- [ ] **Step 6: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2a.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -3)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `1616 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  250 passed (250)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 7: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/oracle.py \
  backend/apps/forms/tests/test_oracle_tier2.py \
  docs/superpowers/specs/2026-10-10-forms-foundation-design.md
git commit -F - <<'MSG'
test(forms): key tier 2 oracle cases on the box and the binding

Tier 2 keyed each case on the box alone, so a binding re-ruled in place or
moved onto a listed box kept the old verdict as a green stale xfail, and a
later correct binding on that box would fail on it (step 2 spec §7.2, B3).

Each tier 2 case now carries its binding key, <source>:<producer>, in the
case slot. Audit rows join on (box, key), with the producer spellings
normalized; with no exact row, a checked row with the same key that names
this box as its right one asserts it (moved here), constants excluded.
Anything else stays unasserted. A pinned count (425) makes each change in
tier 2 coverage visible in review.

No result changes: 425 cases asserted, 344 pass and 81 xfail before and
after. known_defects.json was re-recorded with the recorder's three-file
invocation; the only change is the case value of the 81 tier 2 entries.
The oracle docstring and the step 1 spec's case definition say tier 2's
case is the binding key.

Closes DIG-173.
MSG
git status --short
```

### Task 2: Prepare forms only from a completed intake

_Built and verified as commit `b4ac8a8` on `plan/forms-step2a`._

**Files:**

- Create: `backend/apps/intake/tests/test_completion.py`
- Modify: `backend/apps/documents/tests/test_processing_outcomes.py`
- Modify: `backend/apps/documents/tests/test_views.py`
- Modify: `backend/apps/documents/views.py`
- Modify: `backend/apps/forms/tests/test_form_views.py`
- Modify: `backend/apps/forms/views.py`
- Modify: `backend/apps/intake/models.py`
- Modify: `backend/apps/intake/serializers.py`
- Modify: `backend/apps/intake/views.py`

**Interfaces:**

- Consumes: the intake's `complete` action, which sets `status = "completed"` and `completed_at`; `update_step`, which already sets `"in_progress"`; the forms views' `_fill`, `_failure`, `_FAILURE_SENTENCES` and `_session_or_error`; `_assert_session_owned` in the debt and asset viewsets; `DraftDebtCreator.create_from_result` and `create_from_credit_report`; `PayStubExtraction`. The seeds already set `status="completed"` (`seed_demo_data.py`), so the journeys' sessions still generate.
- Produces:
  - `IntakeSession.reopen()`: sets a completed intake's `status` back to `"in_progress"` with `save(update_fields=["status"])` and leaves `completed_at` alone. Every intake-data write calls it. A later task that adds an intake-data write path (Task 4's whole-list contracts and codebtors save) calls it too.
  - `_INTAKE_DATA = {"debtor_info", "income_info", "expense_info", "assets", "debts"}` in `apps/intake/serializers.py`. `IntakeSessionSerializer.update` reopens when `validated_data` carries any of them.
  - `status` and `current_step` in `IntakeSessionSerializer.Meta.read_only_fields`. `POST /api/intake/sessions/{id}/update_step/` with anything but an `int` from 1 to 8 (a `bool` included, or a missing key) is a 400 with body `{"current_step": ["Must be a whole number from 1 to 8."]}`.
  - In `apps/forms/views.py`: the exception `IntakeNotFinished`, its sentence "Finish your intake before preparing your forms." in `_FAILURE_SENTENCES`, and `_check_finished(session)`, the one rule (`status != "completed"` raises). `_fill` calls it first. Generate, Regenerate and the download of an unfiled form return a 422 with `{"form_type": ..., "error": ...}`. Generate All returns a 422 with `{"error": ...}` and no `form_type`, before `packet()` and before it deletes any row; Task 12 shows that `error`. `GET /api/forms/packet/` is unchanged and never refuses.
  - The `session` fixture in `apps/forms/tests/test_form_views.py` is a completed session.
  - Tests: `test_unfinished_intake_cannot_prepare_forms`, `test_browser_cannot_mark_intake_complete`, `test_editing_a_completed_intake_asks_for_complete_again`, and `test_saving_an_intake_step_after_complete_reopens_it`, whose `income_info` case sends `monthly_income`. Task 9 changes that case when the months become read-only.

**Decisions already made in this task:**

- `update_step` with anything but a whole number from 1 to 8 is a 400, not a 422: it is a client fault (cross-cutting ruling). The 400 also refuses a missing `current_step`, a numeric string such as `"3"`, a float such as `3.0`, and `True`. The only caller, `IntakeContext.updateCurrentStep`, always sends a JSON number. Its body, "Must be a whole number from 1 to 8.", is a client-fault message that no screen shows, not filer copy.
- Every intake-data write reopens a completed intake through the one helper, `IntakeSession.reopen()` (owner ruling, cross-cutting). Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it.
- A session PATCH reopens when it carries one of the five sections at all, even as `{}` or `null`. The spec's word is "carries", and the unchanged-data check belongs to `useAutoSave` (Task 3). The reopen runs after validation, so a refused save leaves a completed intake complete.
- A per-item PATCH that moves a debt or asset to another of the filer's own sessions reopens both sessions.
- The documents `validate` endpoint also reopens, for a creditor bill or a pay stub, because it writes a bill's draft debt and a pay stub's figures. It reopens even when nothing matched. No screen calls it today. A credit report's `validate` touches no intake row and doesn't reopen.
- An upload reopens only when it adds intake data: a bill that creates its draft debt, a pay stub that passes `PayStubExtraction`, a credit report that creates at least one draft debt. A bill with no creditor, a report of paid-off accounts only and other document types don't.
- Dischargeability doesn't reopen. It writes derived classifications, and the dashboard calls it on every load, so reopening there would stop every completed filer from preparing forms. A `district` PATCH doesn't reopen either: `district` is not in `_INTAKE_DATA`, and §5.3's list doesn't name it.
- `reopen()` leaves `completed_at` unchanged. §5.3 calls it an audit timestamp, and the one rule is `status == "completed"`.
- Generate All's refusal is one 422 for the whole call, `{"error": "Finish your intake before preparing your forms."}` with no `form_type`. The single-form endpoints keep their `{form_type, error}` shape.
- A filed form with a stored snapshot still downloads from an unfinished intake: §5.3 checks only "download of an unfiled form", and the filer still needs the copy they filed. A filed form with no snapshot goes through `_fill`, so it is checked. Regenerate on a filed form from an unfinished intake returns the filed-form 422 first, because `_generate_and_persist` checks filed before it fills.
- DIG-153 is server-only. With every box blank the Expenses step sends `{expense_info: {total_monthly_expenses: 0}}`, DRF drops that read-only key, and the old `if expense_data:` skipped the empty dict. The serializer now tests `is not None`. `debtor_info` and `income_info` keep their truthiness test: an empty `DebtorInfo` would fail its NOT NULL `date_of_birth`.
- `IntakeSessionViewSet.create` no longer copies `data["status"] = "started"` into the request. With `status` read-only the serializer ignores it, and the model default already gives `"started"`.
- `test_editing_a_completed_intake_asks_for_complete_again` edits `debtor_info`, not income, so it stays independent of Task 9's income rework.
- The client is left as it is in this task. A failed Complete still navigates to `/forms`, and the dashboard shows nothing for Generate All's 422. Task 3 keeps the filer on Review, and Task 12 shows the refusal.

- [ ] **Step 1: Write the completion, reopen and refusal tests**

```python file=backend/apps/intake/tests/test_completion.py
"""Only the server marks an intake complete, and an edit after that reopens it (spec §5.3).

Business intent: forms are prepared only from an intake the filer completed, because only
then does an empty list mean "the filer said none". The browser can't claim that state
(DIG-151). Changing intake data after Complete sets the intake back to in progress, so the
filer presses Complete again, which re-runs its checks and the fee-waiver routing. Form
answers, SOFA and the fee-waiver application are not intake data and never reopen it.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    ExpenseInfo,
    IncomeInfo,
    IntakeSession,
)
from apps.users.models import User

FINISH = "Finish your intake before preparing your forms."


@pytest.fixture
def district(db):
    # The name is one of the court forms' district choices, so forms fill.
    return District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court, Northern District of Illinois",
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def filer(district):
    user = User.objects.create_user(username="filer", password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def completed(filer, district):
    """An intake the filer completed, with the three sections Complete requires."""
    _, user = filer
    session = IntakeSession.objects.create(
        user=user, district=district, status="completed", current_step=8
    )
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane.doe@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(
        session=session,
        marital_status="single",
        number_of_dependents=0,
        monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
    )
    ExpenseInfo.objects.create(session=session)
    return session


def _session_url(session, action=""):
    return f"/api/intake/sessions/{session.pk}/{action}"


def _status(session):
    return IntakeSession.objects.get(pk=session.pk).status


def _complete_again(session):
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")


# ── Who marks an intake complete ──────────────────────────────────────


def test_browser_cannot_mark_intake_complete(filer, district):
    client, _ = filer
    claimed = {"status": "completed", "current_step": 8}

    created = client.post(
        "/api/intake/sessions/", {"district": district.id, **claimed}, format="json"
    )
    assert created.status_code == 201
    session = IntakeSession.objects.get(pk=created.data["session"]["id"])
    assert (session.status, session.current_step) == ("started", 1)

    patched = client.patch(_session_url(session), claimed, format="json")
    assert patched.status_code == 200
    session.refresh_from_db()
    assert (session.status, session.current_step) == ("started", 1)

    # update_step's nested data can't carry them either.
    stepped = client.post(
        _session_url(session, "update_step/"),
        {"current_step": 3, "data": claimed},
        format="json",
    )
    assert stepped.status_code == 200
    session.refresh_from_db()
    assert (session.status, session.current_step) == ("in_progress", 3)


_MISSING = object()


@pytest.mark.parametrize(
    "step",
    [0, 9, -1, "3", 3.0, 2.5, True, None, _MISSING],
    ids=["0", "9", "-1", "string", "float", "fraction", "bool", "null", "missing"],
)
def test_wizard_step_must_be_one_of_the_eight_steps(filer, completed, step):
    # A step the wizard doesn't have is a client fault, not something the filer can fix.
    client, _ = filer
    body = {} if step is _MISSING else {"current_step": step}

    response = client.post(_session_url(completed, "update_step/"), body, format="json")

    assert response.status_code == 400
    assert "current_step" in response.data
    completed.refresh_from_db()
    assert (completed.status, completed.current_step) == ("completed", 8)


def test_filer_who_leaves_every_expense_blank_can_complete(filer, district):
    # DIG-153: the Expenses step sends only its computed total when every box is blank.
    client, user = filer
    session = IntakeSession.objects.create(user=user, district=district, current_step=3)
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900-12-3456",
        date_of_birth=date(1990, 1, 15),
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    IncomeInfo.objects.create(session=session, monthly_income=[0, 0, 0, 0, 0, 0])

    saved = client.patch(
        _session_url(session), {"expense_info": {"total_monthly_expenses": 0}}, format="json"
    )

    assert saved.status_code == 200
    expenses = ExpenseInfo.objects.get(session=session)
    assert expenses.calculate_total_monthly_expenses() == 0
    assert client.post(_session_url(session, "complete/")).status_code == 200
    assert _status(session) == "completed"


# ── An edit after Complete reopens the intake ─────────────────────────


def test_editing_a_completed_intake_asks_for_complete_again(filer, completed):
    client, _ = filer
    generate = {"session_id": completed.pk, "form_type": "form_106dec"}

    edited = client.patch(
        _session_url(completed), {"debtor_info": {"first_name": "Janet"}}, format="json"
    )
    assert edited.status_code == 200
    assert edited.data["status"] == "in_progress"
    assert _status(completed) == "in_progress"

    refused = client.post("/api/forms/generate/", generate, format="json")
    assert refused.status_code == 422
    assert refused.data["error"] == FINISH

    assert client.post(_session_url(completed, "complete/")).status_code == 200
    assert client.post("/api/forms/generate/", generate, format="json").status_code == 200


@pytest.mark.parametrize(
    "section,value",
    [
        ("debtor_info", {"first_name": "Janet"}),
        ("income_info", {"monthly_income": [3100, 3100, 3100, 3100, 3100, 3100]}),
        ("expense_info", {"rent_or_mortgage": 900}),
        ("debts", [{"creditor_name": "Chase", "debt_type": "credit_card", "amount_owed": 500}]),
        (
            "assets",
            [{"asset_type": "bank_account", "description": "Checking", "current_value": 800}],
        ),
    ],
)
def test_saving_an_intake_step_after_complete_reopens_it(filer, completed, section, value):
    client, _ = filer

    response = client.patch(_session_url(completed), {section: value}, format="json")

    assert response.status_code == 200
    assert response.data["status"] == "in_progress"
    assert _status(completed) == "in_progress"


def test_a_refused_save_leaves_a_completed_intake_complete(filer, completed):
    client, _ = filer

    response = client.patch(_session_url(completed), {"debtor_info": {"ssn": "123"}}, format="json")

    assert response.status_code == 400
    assert _status(completed) == "completed"


def test_moving_between_wizard_steps_after_complete_reopens_it(filer, completed):
    client, _ = filer

    response = client.post(
        _session_url(completed, "update_step/"), {"current_step": 5}, format="json"
    )

    assert response.status_code == 200
    assert _status(completed) == "in_progress"


@pytest.mark.parametrize(
    "endpoint,row",
    [
        ("contracts", {"counterparty_name": "Oak Street Apartments", "contract_type": "lease"}),
        ("codebtors", {"name": "Sam Doe", "relationship": "relative"}),
    ],
)
def test_adding_or_removing_a_contract_or_codebtor_after_complete_reopens_it(
    filer, completed, endpoint, row
):
    client, _ = filer
    url = _session_url(completed, f"{endpoint}/")

    added = client.post(url, row, format="json")
    assert added.status_code == 201
    assert _status(completed) == "in_progress"

    _complete_again(completed)
    removed = client.delete(f"{url}{added.data['id']}/")
    assert removed.status_code == 204
    assert _status(completed) == "in_progress"


@pytest.mark.parametrize(
    "endpoint,row,change",
    [
        (
            "debts",
            {"creditor_name": "Chase", "debt_type": "credit_card", "amount_owed": "500.00"},
            {"amount_owed": "650.00"},
        ),
        (
            "assets",
            {"asset_type": "bank_account", "description": "Checking", "current_value": "800.00"},
            {"current_value": "950.00"},
        ),
    ],
)
def test_per_item_debt_and_asset_writes_after_complete_reopen_it(
    filer, completed, endpoint, row, change
):
    client, _ = filer
    url = f"/api/intake/{endpoint}/"

    created = client.post(url, {"session": completed.pk, **row}, format="json")
    assert created.status_code == 201
    assert _status(completed) == "in_progress"

    _complete_again(completed)
    updated = client.patch(f"{url}{created.data['id']}/", change, format="json")
    assert updated.status_code == 200
    assert _status(completed) == "in_progress"

    _complete_again(completed)
    deleted = client.delete(f"{url}{created.data['id']}/")
    assert deleted.status_code == 204
    assert _status(completed) == "in_progress"
    assert not AssetInfo.objects.filter(session=completed).exists()
    assert not DebtInfo.objects.filter(session=completed).exists()


def test_moving_a_debt_to_another_intake_reopens_both(filer, completed, district):
    client, user = filer
    other = IntakeSession.objects.create(user=user, district=district, status="completed")
    debt = DebtInfo.objects.create(
        session=completed, creditor_name="Chase", debt_type="credit_card", amount_owed=500
    )

    response = client.patch(f"/api/intake/debts/{debt.pk}/", {"session": other.pk}, format="json")

    assert response.status_code == 200
    assert (_status(completed), _status(other)) == ("in_progress", "in_progress")


# ── What is not intake data ───────────────────────────────────────────


def test_form_answers_sofa_and_fee_waiver_leave_a_completed_intake_complete(filer, completed):
    client, _ = filer

    answers = client.post(
        _session_url(completed, "answers/bulk/"),
        {
            "answers": [
                {"form_type": "form_101", "binding": "answer:form_101.q1", "value": "Yes"},
                {"form_type": "form_107", "binding": "sofa.has_prior_income", "value": "True"},
            ]
        },
        format="json",
    )
    sofa = client.patch(
        f"/api/intake/sofa-report/{completed.pk}/", {"has_business": False}, format="json"
    )
    fee_waiver = client.post(
        "/api/intake/fee-waiver/",
        {
            "session": completed.pk,
            "household_size": 1,
            "monthly_income": "1800.00",
            "monthly_expenses": "1600.00",
            "receives_public_benefits": False,
            "benefit_types": [],
            "cannot_pay_full": True,
            "cannot_pay_installments": True,
        },
        format="json",
    )

    assert (answers.status_code, sofa.status_code, fee_waiver.status_code) == (200, 200, 201)
    assert _status(completed) == "completed"
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/documents/tests/test_processing_outcomes.py b/backend/apps/documents/tests/test_processing_outcomes.py
index 4e16ee2..7c9aece 100644
--- a/backend/apps/documents/tests/test_processing_outcomes.py
+++ b/backend/apps/documents/tests/test_processing_outcomes.py
@@ -474,3 +474,66 @@ def test_scan_records_the_provider_that_read_it(filer, openai_client):
     doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, reply=bill)

     assert OCRResult.objects.get(document_id=doc["id"]).ocr_provider == "openai"
+
+
+# A scan that adds a debt or pay figures changes the intake, so a completed intake goes
+# back to in progress and the filer presses Complete again (spec §5.3).
+
+PAY_STUB = {
+    "employer_name": "Acme Logistics",
+    "gross_pay": "1000.00",
+    "pay_period_start": "2026-01-01",
+    "pay_period_end": "2026-01-14",
+    "confidence_score": 92,
+}
+
+
+@pytest.mark.parametrize(
+    "document_type,reply",
+    [
+        (
+            DocumentType.CREDITOR_BILL,
+            {"creditor_name": "ComEd", "amount_owed": "96.12", "creditor_type": "utility"},
+        ),
+        (DocumentType.PAY_STUB, PAY_STUB),
+        (
+            DocumentType.CREDIT_REPORT,
+            {"tradelines": [{"creditor_name": "Discover", "amount_owed": "310.00"}]},
+        ),
+    ],
+    ids=["bill", "pay-stub", "credit-report"],
+)
+def test_a_scan_that_adds_a_debt_or_pay_figures_reopens_a_completed_intake(
+    filer, openai_client, document_type, reply
+):
+    _, session = filer
+    IntakeSession.objects.filter(pk=session.pk).update(status="completed")
+
+    doc = scan_photo(filer, openai_client, document_type, reply=reply)
+
+    assert doc["ocr_result"]["status"] == "completed"
+    session.refresh_from_db()
+    assert session.status == "in_progress"
+
+
+@pytest.mark.parametrize(
+    "document_type,reply",
+    [
+        (DocumentType.CREDITOR_BILL, {"creditor_name": None, "amount_owed": "125.00"}),
+        (
+            DocumentType.CREDIT_REPORT,
+            {"tradelines": [{"creditor_name": "Discover", "amount_owed": "0"}]},
+        ),
+    ],
+    ids=["nothing-found", "paid-off-accounts-only"],
+)
+def test_a_scan_that_adds_nothing_leaves_a_completed_intake_complete(
+    filer, openai_client, document_type, reply
+):
+    _, session = filer
+    IntakeSession.objects.filter(pk=session.pk).update(status="completed")
+
+    scan_photo(filer, openai_client, document_type, reply=reply)
+
+    session.refresh_from_db()
+    assert session.status == "completed"
diff --git a/backend/apps/documents/tests/test_views.py b/backend/apps/documents/tests/test_views.py
index d206737..426d94e 100644
--- a/backend/apps/documents/tests/test_views.py
+++ b/backend/apps/documents/tests/test_views.py
@@ -197,3 +197,42 @@ def test_a_corrected_amount_reaches_the_draft_debt(db, auth_client, session):
     assert response.status_code == 200
     draft.refresh_from_db()
     assert draft.amount_owed == Decimal("650.00")
+
+
+@pytest.mark.parametrize(
+    "document_type,fields",
+    [
+        (DocumentType.CREDITOR_BILL, {"amount_owed": "650.00"}),
+        (DocumentType.PAY_STUB, {"gross_pay": "1100.00"}),
+    ],
+    ids=["bill", "pay-stub"],
+)
+def test_correcting_a_scanned_bill_or_pay_stub_reopens_a_completed_intake(
+    db, auth_client, session, document_type, fields
+):
+    # A bill's draft debt and a pay stub's figures are intake data (spec §5.3).
+    client, user = auth_client
+    doc = UploadedDocument.objects.create(
+        session=session,
+        uploaded_by=user,
+        document_type=document_type,
+        user_declared_type=document_type,
+        original_filename="scan.pdf",
+        file_size=100,
+        mime_type="application/pdf",
+        file="documents/x.pdf",
+    )
+    OCRResult.objects.create(
+        document=doc,
+        status=OCRStatus.COMPLETED,
+        extracted_data="{}",
+        confidence_scores={},
+        overall_confidence=80,
+    )
+    IntakeSession.objects.filter(pk=session.pk).update(status="completed")
+
+    response = client.post(f"/api/documents/{doc.id}/validate/", {"fields": fields}, format="json")
+
+    assert response.status_code == 200
+    session.refresh_from_db()
+    assert session.status == "in_progress"
diff --git a/backend/apps/forms/tests/test_form_views.py b/backend/apps/forms/tests/test_form_views.py
index b1d87a2..1466444 100644
--- a/backend/apps/forms/tests/test_form_views.py
+++ b/backend/apps/forms/tests/test_form_views.py
@@ -95,7 +95,8 @@ def district(db):

 @pytest.fixture
 def session(user, district):
-    return IntakeSession.objects.create(user=user, district=district)
+    # Forms are prepared only from an intake the filer completed (spec §5.3).
+    return IntakeSession.objects.create(user=user, district=district, status="completed")


 @pytest.fixture
@@ -618,6 +619,76 @@ class TestPacketEndpoint:
         assert resp.status_code == status.HTTP_404_NOT_FOUND


+# ── Only a completed intake prepares forms (spec §5.3) ────────────────
+
+FINISH = "Finish your intake before preparing your forms."
+
+
+@pytest.mark.django_db
+class TestCompletionCheck:
+    """Until the filer presses Complete, an empty list can't mean "none"."""
+
+    def test_unfinished_intake_cannot_prepare_forms(self, api_client, session_with_income, user):
+        session = session_with_income
+        session.status = "in_progress"
+        session.save()
+        # No fee waiver application, so 103B has left the packet; 101 is in it, unfiled.
+        GeneratedForm.objects.create(session=session, form_type="form_103b", generated_by=user)
+        unfiled = GeneratedForm.objects.create(
+            session=session, form_type="form_101", status="generated", generated_by=user
+        )
+
+        generate_all = api_client.post(
+            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
+        )
+        generate = api_client.post(
+            "/api/forms/generate/",
+            {"session_id": session.id, "form_type": "form_106dec"},
+            format="json",
+        )
+        regenerate = api_client.post(f"/api/forms/{unfiled.id}/regenerate/")
+        download = api_client.get(f"/api/forms/{unfiled.id}/download/")
+
+        # One refusal for the whole packet, not one per form.
+        assert generate_all.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
+        assert generate_all.data == {"error": FINISH}
+        for resp, form_type in [
+            (generate, "form_106dec"),
+            (regenerate, "form_101"),
+            (download, "form_101"),
+        ]:
+            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
+            assert resp.data == {"form_type": form_type, "error": FINISH}
+        # Generate All refused before it dropped the form that left the packet.
+        assert set(
+            GeneratedForm.objects.filter(session=session).values_list("form_type", flat=True)
+        ) == {"form_101", "form_103b"}
+        unfiled.refresh_from_db()
+        assert (unfiled.status, unfiled.field_values) == ("generated", "")
+
+    def test_unfinished_intake_can_still_read_its_packet(self, api_client, session_with_debtor):
+        session_with_debtor.status = "in_progress"
+        session_with_debtor.save()
+
+        resp = api_client.get("/api/forms/packet/", {"session": session_with_debtor.id})
+
+        assert resp.status_code == status.HTTP_200_OK
+        assert len(resp.data["form_types"]) == 14
+
+    def test_filed_form_still_downloads_while_the_intake_is_reopened(
+        self, api_client, session_with_debtor, user
+    ):
+        # The filer needs the copy they filed even after an edit sent them back to Review.
+        form = _filed_form(session_with_debtor, user, "form_121", {"Debtor1.First name": "Jane"})
+        session_with_debtor.status = "in_progress"
+        session_with_debtor.save()
+
+        resp = api_client.get(f"/api/forms/{form.id}/download/")
+
+        assert resp.status_code == status.HTTP_200_OK
+        assert resp["Content-Type"] == "application/pdf"
+
+
 # ── The snapshot stays on the server (DIG-124) ────────────────────────


PATCH
```

`test_completion.py` covers who marks an intake complete, the steps `update_step` accepts, the blank-expenses trap (DIG-153), one reopen test per intake-data write, and one test that form answers, SOFA and the fee-waiver application leave a completed intake complete. The `test_form_views.py` patch makes its `session` fixture a completed session and adds `TestCompletionCheck`: an unfinished intake can't prepare forms through any of the four endpoints, can still read its packet, and still downloads a filed form. The two documents patches add the upload and `validate` reopen cases, and the uploads that add nothing.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_completion.py apps/forms/tests/test_form_views.py apps/documents/tests/test_processing_outcomes.py apps/documents/tests/test_views.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `28 failed, 80 passed`. Sixteen reopen cases fail with assert 'completed' == 'in_progress': the edit test, the five sections, contracts and codebtors, the per-item writes, the move (both sessions stay completed), the two corrections and the three scans. The nine bad steps get 200, not 400. Creating a session with current_step 8 stores 8. The all-blank Expenses save creates no ExpenseInfo (DoesNotExist). Generate All prepares forms from an unfinished intake (assert 200 == 422). The 80 passes are the existing tests and the new guards that hold today: a refused save leaves the intake complete, update_step already reopens, the packet list and a filed form's download stay open, uploads that add nothing don't reopen, and form answers, SOFA and the fee-waiver application don't reopen.

- [ ] **Step 3: Let only the server mark an intake complete, and reopen it on every intake-data write**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/models.py b/backend/apps/intake/models.py
index 091ed29..bb5f533 100644
--- a/backend/apps/intake/models.py
+++ b/backend/apps/intake/models.py
@@ -38,6 +38,17 @@ class IntakeSession(models.Model):
     def __str__(self) -> str:
         return f"Intake {self.id} - {self.user} ({self.status})"

+    def reopen(self) -> None:
+        """Set a completed intake back to in progress, because its intake data changed.
+
+        The filer then presses Complete again, which re-runs the completion checks and
+        the fee-waiver routing (spec §5.3). Form answers, SOFA and the fee-waiver
+        application are not intake data and never call this.
+        """
+        if self.status == "completed":
+            self.status = "in_progress"
+            self.save(update_fields=["status"])
+

 class DebtorInfo(models.Model):
     """Personal information for debtor (PII encrypted)."""
diff --git a/backend/apps/intake/serializers.py b/backend/apps/intake/serializers.py
index fe3dc3e..04cd67d 100644
--- a/backend/apps/intake/serializers.py
+++ b/backend/apps/intake/serializers.py
@@ -268,6 +268,10 @@ def _save_rows_by_id(session, model, rows) -> None:
     model.objects.filter(pk__in=existing.keys() - kept).delete()


+# The intake sections a session save can carry (spec §5.3).
+_INTAKE_DATA = {"debtor_info", "income_info", "expense_info", "assets", "debts"}
+
+
 class IntakeSessionSerializer(serializers.ModelSerializer):
     """
     Serializer for intake session with nested related data.
@@ -300,7 +304,16 @@ class IntakeSessionSerializer(serializers.ModelSerializer):
             "created_at",
             "completed_at",
         ]
-        read_only_fields = ["id", "user", "created_at", "completed_at", "district_name"]
+        # Only the complete and update_step actions set status and current_step (DIG-151).
+        read_only_fields = [
+            "id",
+            "user",
+            "status",
+            "current_step",
+            "created_at",
+            "completed_at",
+            "district_name",
+        ]

     def create(self, validated_data):
         """
@@ -344,7 +357,11 @@ class IntakeSessionSerializer(serializers.ModelSerializer):

         Updates or creates debtor_info, income_info, expense_info.
         Saves assets/debts by id (see _save_rows_by_id).
+        Saving any of them reopens a completed intake.
         """
+        if _INTAKE_DATA.intersection(validated_data):
+            instance.reopen()
+
         debtor_data = validated_data.pop("debtor_info", None)
         income_data = validated_data.pop("income_info", None)
         expense_data = validated_data.pop("expense_info", None)
@@ -363,7 +380,9 @@ class IntakeSessionSerializer(serializers.ModelSerializer):
         if income_data:
             IncomeInfo.objects.update_or_create(session=instance, defaults=income_data)

-        if expense_data:
+        # Every box left blank arrives as {}, and still creates the record with its $0
+        # defaults, so the filer can complete (DIG-153).
+        if expense_data is not None:
             ExpenseInfo.objects.update_or_create(session=instance, defaults=expense_data)

         if assets_data is not None:
diff --git a/backend/apps/intake/views.py b/backend/apps/intake/views.py
index c822a9e..8eaf0ce 100644
--- a/backend/apps/intake/views.py
+++ b/backend/apps/intake/views.py
@@ -82,10 +82,7 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
             "current_step": 1
         }
         """
-        data = request.data.copy()
-        data["status"] = "started"
-
-        serializer = self.get_serializer(data=data)
+        serializer = self.get_serializer(data=request.data)
         serializer.is_valid(raise_exception=True)
         self.perform_create(serializer)

@@ -130,11 +127,21 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         """
         session = self.get_object()

+        # Only one of the wizard's 8 steps; anything else is a client fault (DIG-151).
         current_step = request.data.get("current_step")
-        if current_step:
-            session.current_step = current_step
-            session.status = "in_progress"
-            session.save()
+        if (
+            not isinstance(current_step, int)
+            or isinstance(current_step, bool)
+            or not 1 <= current_step <= 8
+        ):
+            return Response(
+                {"current_step": ["Must be a whole number from 1 to 8."]},
+                status=status.HTTP_400_BAD_REQUEST,
+            )
+
+        session.current_step = current_step
+        session.status = "in_progress"
+        session.save()

         # Update with any provided data
         if "data" in request.data:
@@ -359,6 +366,7 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         serializer = ExecutoryContractSerializer(data=request.data)
         serializer.is_valid(raise_exception=True)
         serializer.save(session=session)
+        session.reopen()
         return Response(serializer.data, status=status.HTTP_201_CREATED)

     @action(
@@ -372,6 +380,7 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         try:
             contract = ExecutoryContract.objects.get(pk=contract_id, session=session)
             contract.delete()
+            session.reopen()
             return Response(status=status.HTTP_204_NO_CONTENT)
         except ExecutoryContract.DoesNotExist:
             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
@@ -386,6 +395,7 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         serializer = CodebtorSerializer(data=request.data)
         serializer.is_valid(raise_exception=True)
         serializer.save(session=session)
+        session.reopen()
         return Response(serializer.data, status=status.HTTP_201_CREATED)

     @action(
@@ -399,6 +409,7 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         try:
             codebtor = Codebtor.objects.get(pk=codebtor_id, session=session)
             codebtor.delete()
+            session.reopen()
             return Response(status=status.HTTP_204_NO_CONTENT)
         except Codebtor.DoesNotExist:
             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
@@ -448,12 +459,20 @@ class AssetViewSet(viewsets.ModelViewSet):
     def perform_create(self, serializer):
         _assert_session_owned(serializer.validated_data["session"], self.request.user)
         serializer.save()
+        serializer.instance.session.reopen()

     def perform_update(self, serializer):
         session = serializer.validated_data.get("session")
         if session is not None:
             _assert_session_owned(session, self.request.user)
+        # A row moved to another of the filer's sessions changes both.
+        serializer.instance.session.reopen()
         serializer.save()
+        serializer.instance.session.reopen()
+
+    def perform_destroy(self, instance):
+        instance.delete()
+        instance.session.reopen()


 class DebtViewSet(viewsets.ModelViewSet):
@@ -474,12 +493,20 @@ class DebtViewSet(viewsets.ModelViewSet):
     def perform_create(self, serializer):
         _assert_session_owned(serializer.validated_data["session"], self.request.user)
         serializer.save()
+        serializer.instance.session.reopen()

     def perform_update(self, serializer):
         session = serializer.validated_data.get("session")
         if session is not None:
             _assert_session_owned(session, self.request.user)
+        # A row moved to another of the filer's sessions changes both.
+        serializer.instance.session.reopen()
         serializer.save()
+        serializer.instance.session.reopen()
+
+    def perform_destroy(self, instance):
+        instance.delete()
+        instance.session.reopen()


 class FeeWaiverViewSet(viewsets.ModelViewSet):
PATCH
```

`status` and `current_step` become read-only on the session serializer (DIG-151), and `update_step` accepts only one of the wizard's 8 steps. `IntakeSession.reopen()` is the one helper. The session PATCH, the contracts and codebtors endpoints and the per-item debt and asset writes call it. The serializer's Expenses save tests `is not None`, so an all-blank step creates the record with its $0 defaults (DIG-153).

- [ ] **Step 4: Reopen when a scan adds intake data**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/documents/views.py b/backend/apps/documents/views.py
index e34e3e0..cf79460 100644
--- a/backend/apps/documents/views.py
+++ b/backend/apps/documents/views.py
@@ -59,21 +59,28 @@ def _record_findings(doc: UploadedDocument, result: ExtractionResult) -> bool:
     must pass PayStubExtraction (gross pay and both pay-period dates required), the
     check the income aggregate applies, and a credit report needs one readable
     account. Other types are not judged and count as read.
+
+    A draft debt or pay-stub figures change the intake, so they reopen a completed one.
     """
     if doc.document_type == DocumentType.CREDITOR_BILL:
-        return DraftDebtCreator().create_from_result(result, doc.session, doc) is not None
+        if DraftDebtCreator().create_from_result(result, doc.session, doc) is None:
+            return False
+        doc.session.reopen()
+        return True
     if doc.document_type == DocumentType.PAY_STUB:
         try:
             PayStubExtraction.model_validate(result.fields)
         except ValidationError:
             return False
+        doc.session.reopen()
         return True
     if doc.document_type == DocumentType.CREDIT_REPORT:
         report = CreditReportExtraction.model_validate(result.fields)
         if not report.tradelines:
             return False
         # A report whose accounts are all paid off is read, and adds no debts.
-        DraftDebtCreator().create_from_credit_report(report, doc.session, doc)
+        if DraftDebtCreator().create_from_credit_report(report, doc.session, doc):
+            doc.session.reopen()
         return True
     return True

@@ -228,6 +235,9 @@ class DocumentViewSet(ViewSet):

         if doc.document_type == DocumentType.CREDITOR_BILL:
             doc.draft_debts.filter(is_draft=True).update(**draft_fields)
+        # A bill's draft debt and a pay stub's figures are intake data.
+        if doc.document_type in (DocumentType.CREDITOR_BILL, DocumentType.PAY_STUB):
+            doc.session.reopen()

         try:
             AggregateIngestionService.recalculate(doc.session_id)
PATCH
```

`_record_findings` reopens when a scan adds a draft debt or pay-stub figures, and `validate` reopens for a creditor bill or a pay stub.

- [ ] **Step 5: Refuse an unfinished intake in the forms views**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/views.py b/backend/apps/forms/views.py
index a3397bb..f7dc300 100644
--- a/backend/apps/forms/views.py
+++ b/backend/apps/forms/views.py
@@ -45,11 +45,16 @@ class FormIsFiled(Exception):
     """The form is marked filed, so it keeps the values it was filed with (spec §5.5)."""


+class IntakeNotFinished(Exception):
+    """The filer hasn't completed the intake, so an empty list can't yet mean "none"."""
+
+
 # Failures a filer can act on: 422 in plain words (spec §5.7). Anything else is a 500.
 # PreconditionMissing carries its own plain reason (registry.py). Every other class gets
 # a fixed sentence, because their messages name form keys, repeat groups and PDF
 # widgets. None names the form: the dashboard shows its label beside the error.
 _FAILURE_SENTENCES = {
+    IntakeNotFinished: "Finish your intake before preparing your forms.",
     NotInPacket: "This form isn't part of your packet, based on the answers you've given.",
     FormIsFiled: "This form is marked as filed, so it keeps the answers it was filed with.",
     RepeatOverflow: (
@@ -119,8 +124,19 @@ def _validate_form_type(form_type: str | None) -> Response | None:
     return None


+def _check_finished(session: IntakeSession) -> None:
+    """Refuse an intake the filer hasn't completed (step 2 spec §5.3).
+
+    Only the intake's complete action sets "completed", and an edit to intake data
+    after it sets the intake back to in progress.
+    """
+    if session.status != "completed":
+        raise IntakeNotFinished()
+
+
 def _fill(form_type: str, session: IntakeSession) -> tuple[dict[str, str], bytes]:
     """Resolve a form that applies to this filer and fill its template."""
+    _check_finished(session)
     if not FORM_REGISTRY[form_type].applies(session):
         raise NotInPacket()
     values = build_field_values(form_type, session)
@@ -249,10 +265,19 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
         Each form gets its own savepoint, so one form's failure can't undo the
         others. Rows for forms that no longer apply are deleted. A filed form
         that still applies is returned as it is: not resolved again, not un-filed.
+        An unfinished intake gets one refusal for the whole packet, before anything
+        is deleted.
         """
         session, err = _session_or_error(request, request.data.get("session_id"))
         if err:
             return err
+        try:
+            _check_finished(session)
+        except IntakeNotFinished:
+            return Response(
+                {"error": _FAILURE_SENTENCES[IntakeNotFinished]},
+                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
+            )

         form_types = packet(session)
         GeneratedForm.objects.filter(session=session).exclude(form_type__in=form_types).delete()
PATCH
```

One check in the views, not in `build_field_values`, so value-building and the oracle are unaffected. Generate All runs it first, before it deletes the rows of forms that left the packet, and returns one error. Generate, Regenerate and the download of an unfiled form share it through `_fill`. The packet list stays readable.

- [ ] **Step 6: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_completion.py apps/forms/tests/test_form_views.py apps/documents/tests/test_processing_outcomes.py apps/documents/tests/test_views.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `108 passed`.

- [ ] **Step 7: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2a.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -3)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `1651 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  250 passed (250)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 8: Run the journeys**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 9: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/intake/tests/test_completion.py \
  backend/apps/documents/tests/test_processing_outcomes.py \
  backend/apps/documents/tests/test_views.py \
  backend/apps/documents/views.py \
  backend/apps/forms/tests/test_form_views.py \
  backend/apps/forms/views.py \
  backend/apps/intake/models.py \
  backend/apps/intake/serializers.py \
  backend/apps/intake/views.py
git commit -F - <<'MSG'
feat(intake,forms): prepare forms only from a completed intake

Only the server's complete action marks an intake complete now. status and
current_step are read-only on the session serializer, so a session create or
PATCH can no longer set them (DIG-151), and update_step accepts only a whole
number from 1 to 8; anything else is a 400.

The forms views refuse an unfinished intake with a 422, "Finish your intake
before preparing your forms." Generate All checks first, before it deletes
the rows of forms that left the packet, and returns one error for the whole
call. Generate, Regenerate and the download of an unfiled form share the
check through _fill. The packet list stays readable, and a filed form still
downloads what was filed.

Every intake-data write sets a completed intake back to in progress through
IntakeSession.reopen(), so the filer presses Complete again: a session save
carrying debtor_info, income_info, expense_info, debts or assets; the
contracts and codebtors endpoints; per-item debt and asset writes; an upload
that adds a draft debt or pay-stub figures; and a correction to a scanned
bill or pay stub. Form answers, SOFA and the fee-waiver application never
reopen it.

Saving the Expenses step with every box blank now creates the expense record
with its $0 defaults, so that filer can complete (DIG-153). The serializer
skipped the empty payload; the wizard needs no change.

Forms step 2a, commit 2 (step 2 spec §5.3).
MSG
git status --short
```

### Task 3: Keep the filer on Review when Complete fails, and save only real edits

_Built and verified as commit `7bd0329` on `plan/forms-step2a`._

**Files:**

- Modify: `backend/apps/intake/tests/test_completion.py`
- Modify: `frontend/src/hooks/__tests__/useAutoSave.test.ts`
- Modify: `frontend/src/hooks/useAutoSave.ts`
- Modify: `frontend/src/pages/FormDashboard.tsx`
- Modify: `frontend/src/pages/IntakeWizard.tsx`
- Modify: `frontend/src/pages/__tests__/FormDashboard.test.tsx`
- Modify: `frontend/src/pages/__tests__/IntakeWizard.test.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**

- Consumes: Task 2's server rule (only `complete` sets `"completed"`, and an intake save reopens a completed intake) and its 422, "Finish your intake before preparing your forms."; `IntakeContext`'s `completeSession` and `calculateMeansTest`, which record the server's message as the context `error` and rethrow; `WizardLayout`, which shows the context `error` in a `role="alert"` box; `session.status` from `useIntake()`.
- Produces:
  - `useAutoSave({ data, dataKey, onSave, debounceMs, enabled })` with a new optional `dataKey`. Each name keeps its own copy, as JSON: the first data seen under a name is its loaded copy, and a successful save records the copy it sent, taken before the `await`. A save still on its way is kept in a second map, and the debounced check compares new data with that copy, or with the confirmed copy when no save is out. A failed save leaves the confirmed copy in place. The debounced save is skipped when the data equals that copy. `saveNow` (Continue and Complete) always saves.
  - In `IntakeWizard.tsx`: `currentStepBody`, a `useMemo` of the PATCH body for the step on screen. It is `debtor_info`; `income_info` with `monthly_income` alone; `expense_info` without `total_monthly_expenses`; the filled `assets`; the filled `debts`; and `null` for contracts, codebtors and review. It is the hook's `data`. `saveCurrentStepData(body)` PATCHes the body it is given and only logs for `null`. `dataKey` is `currentStepKey` once `sessionRead === 'done'`, and `undefined` before. Task 4 gives steps 6 and 7 a save branch of their own and never returns a body for them from `currentStepBody`. Tasks 6 and 9 change the Expenses and Income bodies there.
  - `handleComplete`'s catch no longer calls `navigate('/forms')`.
  - `FormDashboard`: while `session.status !== 'completed'`, a `div.form-dashboard-notice` holds the notice sentence and `<Link to="/intake">Finish your intake</Link>`. It has no `role="alert"`.
  - Tests: `useAutoSave` › "sends no save when the filer steps back to a step without changing it"; `IntakeWizard handleComplete routing` › "keeps the filer on Review with the reason when Complete fails" and "keeps the filer on Review with the reason when only the means test fails"; `IntakeWizard stepping back` › "sends no save when the filer steps back through a completed intake without changing it"; `FormDashboard` › "asks the filer to finish their intake, with a link back, until it is complete". `FormDashboard.test.tsx`'s `beforeEach` serves a completed session.

**Decisions already made in this task:**

- The hook's `data` is the PATCH body the save sends, not the step's state. Comparing state would still reopen a completed intake when the filer goes back from Review: Assets with no rows gets a blank placeholder row, and Expenses with cents adds its total in floating point (2560.4500000000003, where the server sends 2560.45). The body already filters out blank rows. The Expenses body leaves out the read-only `total_monthly_expenses`, which the server ignores, so the body is exactly what the server holds.
- Only the debounced autosave skips unchanged data. `saveNow` (Continue and Complete) always saves: a session PATCH carrying `debts` is what clears scanned debts' `is_draft`, `update_step` reopens on Continue anyway, and an existing Income test pins a Continue PATCH with no edit.
- `dataKey` waits for the session read. While it is pending, the steps hold empty placeholders, and seeding Debtor's loaded copy from one would make the real data look like an edit. No test can observe this today, because a loaded Debtor step is never valid (SSN is write-only), so autosave can't run there.
- A loaded step no longer autosaves its unchanged data about 2 s after it appears. A scanned debt stays a draft until the filer edits Amounts Owed or presses Continue, which is the confirmation §5.4 and DIG-163 describe. The two "amounts a returning filer already entered" tests that relied on save-on-load now press Continue; their assertions are unchanged.
- A save on its way has its own map, and the confirmed copy is never rolled back. Restoring the old copy on failure gives the wrong baseline when two overlapping saves both fail, and re-checking after the `await` sends a duplicate save when a second save is already out.
- The dashboard reads `session.status` from the intake context and does not fetch the session again. Known gap: an autosave PATCH doesn't update the context, so a filer who edits after Complete and reaches `/forms` with the browser's Back or Forward sees no notice. Generate All then gets Task 2's 422, which Task 12 shows.
- Generate All stays visible for an unfinished intake. The spec asks only for the notice.
- The reason shown on Review is the server's message as the context records it. The `complete` 400 also lists the missing sections in `errors`, but `handleAPIError` (`client.ts`) keeps only `message` and `error`, and this task doesn't widen the client.
- Pressing Complete again on Review sends no intake save (its body is `null`), so it retries `complete` and the means test without reopening anything.
- The notice's words: the link text "Finish your intake" is §5.3's. The sentence before it is this task's own, accepted by the controller: "Your forms are prepared from your finished intake. To finish it, go back to your intake and press Complete Intake on the last step." "Complete Intake" is the label `WizardLayout` gives the last step's button. The notice is guidance, not an error, so it has no `role="alert"`.
- `FormDashboard.test.tsx`'s `beforeEach` serves a completed session, as Task 2 switched the backend fixture. MSW's default session is `'started'`.
- DIG-153 needs nothing here. With every box blank the Expenses step now sends `{expense_info: {}}`, which Task 2's serializer saves as a $0 record. A comment in `test_completion.py` is reworded to say so; its payload stays.

- [ ] **Step 1: Write the autosave, Review and dashboard tests**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/hooks/__tests__/useAutoSave.test.ts b/frontend/src/hooks/__tests__/useAutoSave.test.ts
index aa0d5de..0d23c46 100644
--- a/frontend/src/hooks/__tests__/useAutoSave.test.ts
+++ b/frontend/src/hooks/__tests__/useAutoSave.test.ts
@@ -37,6 +37,165 @@ describe('useAutoSave', () => {
     expect(onSave).not.toHaveBeenCalled();
   });

+  // A save reopens a completed intake on the server, so showing a step again must not send
+  // one (forms step 2 §5.3). Each step keeps its own last saved or loaded copy.
+  it('sends no save when the filer steps back to a step without changing it', async () => {
+    const onSave = vi.fn().mockResolvedValue(undefined);
+    const { rerender } = renderHook(
+      ({ data, dataKey }) => useAutoSave({ data, dataKey, onSave, debounceMs: 2000 }),
+      { initialProps: { data: { rent: 900 }, dataKey: 'expenses' } }
+    );
+
+    // The filer changes Expenses, and the change is saved.
+    rerender({ data: { rent: 950 }, dataKey: 'expenses' });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(2000);
+    });
+    expect(onSave).toHaveBeenCalledTimes(1);
+
+    // Assets opens as the server holds it, then Go Back shows Expenses again as a new object.
+    rerender({ data: { assets: [] }, dataKey: 'assets' });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(3000);
+    });
+    rerender({ data: { rent: 950 }, dataKey: 'expenses' });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(3000);
+    });
+
+    expect(onSave).toHaveBeenCalledTimes(1);
+  });
+
+  it('does not save the data a step opened with', async () => {
+    const onSave = vi.fn().mockResolvedValue(undefined);
+    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
+      initialProps: { data: { rent: 900 } },
+    });
+
+    // The step hands the same values back as a new object when it mounts.
+    rerender({ data: { rent: 900 } });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(3000);
+    });
+
+    expect(onSave).not.toHaveBeenCalled();
+  });
+
+  it('saves a change back to an earlier value, since the server holds the later one', async () => {
+    const onSave = vi.fn().mockResolvedValue(undefined);
+    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
+      initialProps: { data: { rent: 900 } },
+    });
+
+    rerender({ data: { rent: 950 } });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(2000);
+    });
+    rerender({ data: { rent: 900 } });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(2000);
+    });
+
+    expect(onSave).toHaveBeenCalledTimes(2);
+    expect(onSave).toHaveBeenLastCalledWith({ rent: 900 });
+  });
+
+  // Once the save on its way lands, the server holds 950, so a change back to 900 made
+  // before the reply must still be sent.
+  it('sends an edit made while the previous save was still on its way', async () => {
+    let landSave = () => {};
+    const onSave = vi
+      .fn()
+      .mockImplementationOnce(
+        () =>
+          new Promise<void>((resolve) => {
+            landSave = resolve;
+          })
+      )
+      .mockResolvedValue(undefined);
+    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
+      initialProps: { data: { rent: 900 } },
+    });
+
+    rerender({ data: { rent: 950 } });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(2000);
+    });
+    expect(onSave).toHaveBeenCalledTimes(1);
+
+    // The filer changes the box back, then the 950 save lands.
+    rerender({ data: { rent: 900 } });
+    await act(async () => {
+      landSave();
+      await vi.advanceTimersByTimeAsync(10000);
+    });
+
+    expect(onSave.mock.calls).toEqual([[{ rent: 950 }], [{ rent: 900 }]]);
+  });
+
+  // On a slow connection a second save can go out before the first lands. Until the second
+  // lands too, the server is about to hold its copy, not the first one.
+  it('sends an edit made while a later save was still on its way', async () => {
+    const landSaves: Array<() => void> = [];
+    const onSave = vi.fn().mockImplementation(
+      () =>
+        new Promise<void>((resolve) => {
+          landSaves.push(resolve);
+        })
+    );
+    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
+      initialProps: { data: { rent: 900 } },
+    });
+
+    rerender({ data: { rent: 950 } });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(2000);
+    });
+    rerender({ data: { rent: 1000 } });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(2000);
+    });
+    expect(onSave).toHaveBeenCalledTimes(2);
+
+    // The 950 save lands, the filer changes the box back to 950, then the 1000 save lands.
+    await act(async () => {
+      landSaves[0]();
+      await vi.advanceTimersByTimeAsync(0);
+    });
+    rerender({ data: { rent: 950 } });
+    await act(async () => {
+      landSaves[1]();
+      await vi.advanceTimersByTimeAsync(10000);
+    });
+
+    expect(onSave.mock.calls).toEqual([[{ rent: 950 }], [{ rent: 1000 }], [{ rent: 950 }]]);
+  });
+
+  // A failed save leaves the server holding the earlier copy, so the same change is sent again
+  // when the filer next edits the box, even if the edit ends on the value that failed.
+  it('sends a change again after its save failed', async () => {
+    const onSave = vi.fn().mockRejectedValueOnce(new Error('network')).mockResolvedValue(undefined);
+    const { result, rerender } = renderHook(
+      ({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }),
+      { initialProps: { data: { rent: 900 } } }
+    );
+
+    rerender({ data: { rent: 950 } });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(2000);
+    });
+    expect(result.current.saveStatus).toBe('error');
+
+    // The filer types a digit and deletes it.
+    rerender({ data: { rent: 9500 } });
+    rerender({ data: { rent: 950 } });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(2000);
+    });
+
+    expect(onSave.mock.calls).toEqual([[{ rent: 950 }], [{ rent: 950 }]]);
+  });
+
   it('saveNow returns true on success and false on failure', async () => {
     const onSave = vi
       .fn()
diff --git a/frontend/src/pages/__tests__/FormDashboard.test.tsx b/frontend/src/pages/__tests__/FormDashboard.test.tsx
index 09a76d7..c523e06 100644
--- a/frontend/src/pages/__tests__/FormDashboard.test.tsx
+++ b/frontend/src/pages/__tests__/FormDashboard.test.tsx
@@ -21,7 +21,32 @@ function renderFormDashboard() {
   );
 }

+/** Forms are prepared only from an intake the server marked complete. */
+const completedSession = {
+  id: 1,
+  user: 1,
+  district: 1,
+  current_step: 8,
+  status: 'completed',
+  created_at: '2026-01-20T10:00:00Z',
+  updated_at: '2026-01-20T10:00:00Z',
+  completed_at: '2026-01-20T11:00:00Z',
+  debtor_info: null,
+  income_info: null,
+  expense_info: null,
+  assets: [],
+  debts: [],
+};
+
 describe('FormDashboard', () => {
+  beforeEach(() => {
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+        HttpResponse.json(completedSession)
+      )
+    );
+  });
+
   // ---------------------------------------------------------------------------
   // Loading and display
   // ---------------------------------------------------------------------------
@@ -82,6 +107,33 @@ describe('FormDashboard', () => {
     });
   });

+  // ---------------------------------------------------------------------------
+  // An unfinished intake (forms step 2 §5.3)
+  // ---------------------------------------------------------------------------
+
+  it('asks the filer to finish their intake, with a link back, until it is complete', async () => {
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+        HttpResponse.json({ ...completedSession, status: 'in_progress', completed_at: null })
+      )
+    );
+
+    renderFormDashboard();
+
+    await screen.findByText('Form 101 - Voluntary Petition');
+    expect(screen.getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
+      'href',
+      '/intake'
+    );
+  });
+
+  it('does not ask a filer whose intake is complete to finish it', async () => {
+    renderFormDashboard();
+
+    await screen.findByText('Form 101 - Voluntary Petition');
+    expect(screen.queryByRole('link', { name: 'Finish your intake' })).not.toBeInTheDocument();
+  });
+
   // ---------------------------------------------------------------------------
   // Error handling
   // ---------------------------------------------------------------------------
diff --git a/frontend/src/pages/__tests__/IntakeWizard.test.tsx b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
index f7d6cc1..67a96ac 100644
--- a/frontend/src/pages/__tests__/IntakeWizard.test.tsx
+++ b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
@@ -171,6 +171,189 @@ describe('IntakeWizard handleComplete routing', { timeout: 30_000 }, () => {
       expect(screen.getByText('Statement of Financial Affairs')).toBeInTheDocument();
     });
   });
+
+  // DIG-150: the dashboard can't prepare forms from an unfinished intake, and it never showed
+  // why the filer had landed there. The reason belongs on Review, where they can act on it.
+  it('keeps the filer on Review with the reason when Complete fails', async () => {
+    renderWizard();
+    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
+    server.use(
+      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
+        HttpResponse.json(
+          {
+            errors: ['Expense information is required'],
+            message: 'Please complete all required sections before finalizing',
+          },
+          { status: 400 }
+        )
+      )
+    );
+
+    await userEvent.click(completeBtn);
+
+    expect(await screen.findByRole('alert')).toHaveTextContent(
+      'Please complete all required sections before finalizing'
+    );
+    expect(
+      screen.getByRole('heading', { name: /review & results/i, level: 2 })
+    ).toBeInTheDocument();
+    expect(screen.queryByText('FormDashboard')).not.toBeInTheDocument();
+    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
+  });
+
+  it('keeps the filer on Review with the reason when only the means test fails', async () => {
+    renderWizard();
+    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
+    server.use(
+      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
+        HttpResponse.json(
+          {
+            error: 'No median income data for this district',
+            message:
+              'Unable to calculate means test. Please ensure all income information is provided.',
+          },
+          { status: 400 }
+        )
+      )
+    );
+
+    await userEvent.click(completeBtn);
+
+    expect(await screen.findByRole('alert')).toHaveTextContent(
+      'Unable to calculate means test. Please ensure all income information is provided.'
+    );
+    expect(
+      screen.getByRole('heading', { name: /review & results/i, level: 2 })
+    ).toBeInTheDocument();
+    expect(screen.queryByText('FormDashboard')).not.toBeInTheDocument();
+    expect(screen.queryByText('FeeWaiverPage')).not.toBeInTheDocument();
+    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
+  });
+});
+
+// ===========================================================================
+// Stepping back after Complete (forms step 2 §5.3)
+// ===========================================================================
+
+/**
+ * A completed intake as the API returns it. Any intake save reopens it on the server, so the
+ * filer would have to press Complete again. The expenses have cents, the filer listed no assets,
+ * and the debt amounts arrive as decimal strings.
+ */
+const completedSession = {
+  ...sessionAtStep8,
+  status: 'completed' as const,
+  completed_at: '2026-10-12T10:00:00Z',
+  debtor_info: {
+    first_name: 'Jane',
+    last_name: 'Doe',
+    date_of_birth: '1985-06-15',
+    street_address: '123 Main St',
+    city: 'Chicago',
+    state: 'IL',
+    zip_code: '60601',
+    email: 'jane@example.com',
+    household_size: 2,
+    filing_type: 'individual',
+  },
+  income_info: {
+    marital_status: 'single',
+    number_of_dependents: 1,
+    monthly_income: [3100, 3300, 3200, 3200, 3150, 3250],
+    total_monthly_income: 3200,
+  },
+  expense_info: {
+    data_source: 'manual',
+    rent_or_mortgage: '1100.00',
+    utilities: '180.10',
+    home_maintenance: '0.00',
+    vehicle_payment: '0.00',
+    vehicle_insurance: '85.00',
+    vehicle_maintenance: '40.00',
+    food_and_groceries: '450.20',
+    clothing: '60.00',
+    medical_expenses: '75.00',
+    childcare: '400.00',
+    child_support_paid: '0.00',
+    insurance_not_deducted: '120.00',
+    other_expenses: '50.15',
+    // The server's exact decimal sum; adding the amounts in the browser gives 2560.4500000000003
+    total_monthly_expenses: 2560.45,
+    created_at: '2026-10-01T10:00:00Z',
+    updated_at: '2026-10-01T10:00:00Z',
+  },
+  assets: [],
+  debts: [
+    {
+      id: 7,
+      session: 1,
+      data_source: 'manual',
+      creditor_name: 'Chase',
+      debt_type: 'credit_card',
+      priority_classification: 'unsecured',
+      amount_owed: '2500.00',
+      monthly_payment: '75.00',
+      is_in_collections: false,
+      notes: '',
+      is_draft: false,
+      source_document_name: null,
+    },
+  ],
+};
+
+describe('IntakeWizard stepping back', { timeout: 30_000 }, () => {
+  it('sends no save when the filer steps back through a completed intake without changing it', async () => {
+    let sessionSaves = 0;
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+        HttpResponse.json(completedSession)
+      ),
+      http.patch('http://localhost:8000/api/intake/sessions/:id/', () => {
+        sessionSaves += 1;
+        return HttpResponse.json({ ...completedSession, status: 'in_progress' });
+      }),
+      http.get('http://localhost:8000/api/intake/sessions/:id/contracts/', () =>
+        HttpResponse.json([])
+      ),
+      http.get('http://localhost:8000/api/intake/sessions/:id/codebtors/', () =>
+        HttpResponse.json([])
+      ),
+      http.post(
+        'http://localhost:8000/api/audit/logs/',
+        () => new HttpResponse(null, { status: 201 })
+      )
+    );
+
+    const { container } = renderWizard();
+    await screen.findByRole('heading', { name: /review & results/i, level: 2 });
+
+    // Each step gets longer than the 2 s autosave delay. findBy needs real timers, so the
+    // step title is read directly while the clock is fake.
+    vi.useFakeTimers();
+    try {
+      for (const step of [
+        'Codebtors',
+        'Contracts & Leases',
+        'Amounts Owed',
+        'Assets',
+        'Expenses',
+        'Income',
+        'Your Information',
+      ]) {
+        act(() => {
+          fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
+        });
+        for (let second = 0; second < 3; second += 1) {
+          await act(() => vi.advanceTimersByTimeAsync(1000));
+        }
+        expect(container.querySelector('.step-title')).toHaveTextContent(step);
+      }
+    } finally {
+      vi.useRealTimers();
+    }
+
+    expect(sessionSaves).toBe(0);
+  });
 });

 // ===========================================================================
@@ -528,11 +711,18 @@ describe('IntakeWizard amounts a returning filer already entered', { timeout: 15
       http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
         HttpResponse.json(sessionAtStep5WithDebts)
       ),
-      // Loaded rows are valid, so autosave PATCHes about 2 s after the step appears.
+      // Continue saves the step, even when the filer changed nothing.
       http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
         patchBodies.push(await request.json());
         return HttpResponse.json(sessionAtStep5WithDebts);
-      })
+      }),
+      http.get('http://localhost:8000/api/intake/sessions/:id/contracts/', () =>
+        HttpResponse.json([])
+      ),
+      http.post(
+        'http://localhost:8000/api/audit/logs/',
+        () => new HttpResponse(null, { status: 201 })
+      )
     );
   });

@@ -550,6 +740,7 @@ describe('IntakeWizard amounts a returning filer already entered', { timeout: 15
   it('saves each debt back under its own id, with its amounts as numbers', async () => {
     renderWizard();
     await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
+    await userEvent.click(screen.getByRole('button', { name: /continue/i }));

     await waitFor(() => expect(patchBodies.length).toBeGreaterThan(0));
     const { debts } = patchBodies[0] as { debts: Record<string, unknown>[] };
@@ -566,6 +757,7 @@ describe('IntakeWizard amounts a returning filer already entered', { timeout: 15
     );
     renderWizard();
     await screen.findByRole('heading', { name: /assets/i, level: 2 });
+    await userEvent.click(screen.getByRole('button', { name: /continue/i }));

     await waitFor(() => expect(patchBodies.length).toBeGreaterThan(0));
     const { assets } = patchBodies[0] as { assets: Record<string, unknown>[] };
PATCH
```

The hook tests use the file's fake timers. The wizard's stepping-back test loads a completed session at Review and presses Go Back seven times, holding each step for 3 s, with the CLAUDE.md pattern: `findBy` under real timers, then `vi.useFakeTimers()`, `fireEvent.click` in `act`, and `vi.advanceTimersByTimeAsync(1000)` three times per step. Its fixture's expenses have cents, it has no assets, and its debt amounts arrive as decimal strings.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/hooks/__tests__/useAutoSave.test.ts src/pages/__tests__/IntakeWizard.test.tsx src/pages/__tests__/FormDashboard.test.tsx 2>&1 | tail -5
```

Expected: FAIL — `6 failed` and `30 passed` on the Tests line. The two hook tests save unchanged data: the stepping-back one saves 3 times, not once, and the other saves the data the step opened with. Stepping back through the completed intake sends 4 PATCHes, not 0. Both Review tests find no alert, because a failed Complete lands on the dashboard. The dashboard has no Finish your intake link. The other new tests already pass, because the old hook saves every change: a change back to an earlier value, the two edits made while a save was on its way, a change sent again after its save failed, and a completed intake that shows no notice. They guard the new copy logic and the notice's condition.

- [ ] **Step 3: Skip an autosave whose data equals the step's saved, loaded or sending copy**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/hooks/useAutoSave.ts b/frontend/src/hooks/useAutoSave.ts
index 4013140..acacf5b 100644
--- a/frontend/src/hooks/useAutoSave.ts
+++ b/frontend/src/hooks/useAutoSave.ts
@@ -3,6 +3,10 @@
  *
  * Saves data after 2 seconds of inactivity. Exposes save status
  * so the UI can show "Saving..." / "Saved" indicators.
+ *
+ * A save whose data equals the last saved or loaded copy (or the copy of a save still on its
+ * way) is skipped, so showing a step again sends nothing. Only a real edit is saved, and on
+ * the server it reopens a completed intake (forms step 2 §5.3).
  */

 import { useState, useEffect, useRef, useCallback } from 'react';
@@ -12,6 +16,11 @@ export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';
 interface UseAutoSaveOptions<T> {
   /** The data to auto-save */
   data: T;
+  /**
+   * Names whose data `data` is, for a caller that shows one of several (the wizard's steps).
+   * Each name keeps its own last saved copy; the first data seen under a name is its loaded copy.
+   */
+  dataKey?: string;
   /** Async function that persists the data */
   onSave: (data: T) => Promise<void>;
   /** Debounce delay in milliseconds (default: 2000) */
@@ -30,6 +39,7 @@ interface UseAutoSaveReturn {

 export function useAutoSave<T>({
   data,
+  dataKey,
   onSave,
   debounceMs = 2000,
   enabled = true,
@@ -38,19 +48,29 @@ export function useAutoSave<T>({
   const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
   const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
   const dataRef = useRef(data);
+  const dataKeyRef = useRef(dataKey);
   const onSaveRef = useRef(onSave);
-  const isFirstRender = useRef(true);
+  // The last copy saved or loaded under each name, as JSON
+  const savedCopiesRef = useRef(new Map<string | undefined, string>());
+  // The copy of a save still on its way, by name: once it lands, the server holds it
+  const sendingCopiesRef = useRef(new Map<string | undefined, string>());

   // Keep refs current to avoid stale closures
   useEffect(() => {
     dataRef.current = data;
+    dataKeyRef.current = dataKey;
     onSaveRef.current = onSave;
   });

   const executeSave = useCallback(async (): Promise<boolean> => {
+    // Taken before the save, so a later edit is never recorded as saved
+    const key = dataKeyRef.current;
+    const copy = JSON.stringify(dataRef.current);
+    sendingCopiesRef.current.set(key, copy);
     setSaveStatus('saving');
     try {
       await onSaveRef.current(dataRef.current);
+      savedCopiesRef.current.set(key, copy);
       setSaveStatus('saved');
       setLastSavedAt(new Date());

@@ -60,18 +80,26 @@ export function useAutoSave<T>({
     } catch {
       setSaveStatus('error');
       return false;
+    } finally {
+      // Unless a later save of this name has gone out since
+      if (sendingCopiesRef.current.get(key) === copy) sendingCopiesRef.current.delete(key);
     }
   }, []);

   // Debounced save on data changes
   useEffect(() => {
-    // Skip first render (initial data load)
-    if (isFirstRender.current) {
-      isFirstRender.current = false;
+    const copy = JSON.stringify(data);
+    const savedCopies = savedCopiesRef.current;
+
+    // The first data seen under a name is the loaded copy, not an edit
+    if (!savedCopies.has(dataKey)) {
+      savedCopies.set(dataKey, copy);
       return;
     }

-    if (!enabled) return;
+    // Compared with what the server will hold once a save on its way lands
+    const serverCopy = sendingCopiesRef.current.get(dataKey) ?? savedCopies.get(dataKey);
+    if (!enabled || copy === serverCopy) return;

     if (timerRef.current) clearTimeout(timerRef.current);
     timerRef.current = setTimeout(executeSave, debounceMs);
@@ -79,7 +107,7 @@ export function useAutoSave<T>({
     return () => {
       if (timerRef.current) clearTimeout(timerRef.current);
     };
-  }, [data, debounceMs, enabled, executeSave]);
+  }, [data, dataKey, debounceMs, enabled, executeSave]);

   // Cleanup on unmount
   useEffect(() => {
PATCH
```

Showing a step again sends nothing, so stepping back with Go Back no longer reopens a completed intake. Only a real edit is saved (§5.3).

- [ ] **Step 4: Autosave the PATCH body, and keep the filer on Review when Complete fails**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/tests/test_completion.py b/backend/apps/intake/tests/test_completion.py
index fb95541..42db410 100644
--- a/backend/apps/intake/tests/test_completion.py
+++ b/backend/apps/intake/tests/test_completion.py
@@ -141,7 +141,8 @@ def test_wizard_step_must_be_one_of_the_eight_steps(filer, completed, step):


 def test_filer_who_leaves_every_expense_blank_can_complete(filer, district):
-    # DIG-153: the Expenses step sends only its computed total when every box is blank.
+    # DIG-153: with every box blank, the Expenses step sends no amounts. The server drops the
+    # read-only total sent here, so this body is the same as the step's empty one.
     client, user = filer
     session = IntakeSession.objects.create(user=user, district=district, current_step=3)
     DebtorInfo.objects.create(
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
index 05266d6..a2bb909 100644
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -5,7 +5,7 @@
  * and handles data persistence to backend API.
  */

-import { useState, useEffect, useRef, useLayoutEffect } from 'react';
+import { useState, useEffect, useMemo, useRef, useLayoutEffect } from 'react';
 import { useAutoSave } from '../hooks/useAutoSave';
 import { useNavigate } from 'react-router-dom';
 import { useIntake } from '../context/IntakeContext';
@@ -152,27 +152,56 @@ export function IntakeWizard() {
   // Autosave
   // =========================================================================

-  // The data object for the step currently on screen. useAutoSave watches this;
-  // when it changes (the user typing), it debounces a call to saveCurrentStepData.
+  // What saving the step on screen sends: PATCH /api/intake/sessions/{id}/, whose nested
+  // serializer creates and updates each section. null for the steps the wizard doesn't save.
+  // useAutoSave compares it with the step's last saved or loaded copy, so a step that only
+  // shows what the server holds (a blank row, a recomputed total) sends nothing.
   const currentStepKey = WIZARD_STEPS[currentStepNumber - 1]?.key;
-  const currentStepData =
-    currentStepKey === 'debtor_info'
-      ? debtorData
-      : currentStepKey === 'income_info'
-        ? incomeData
-        : currentStepKey === 'expense_info'
-          ? expenseData
-          : currentStepKey === 'assets'
-            ? assetsData
-            : currentStepKey === 'debts'
-              ? debtsData
-              : null;
+  const currentStepBody = useMemo((): Partial<IntakeSession> | null => {
+    switch (currentStepKey) {
+      case 'debtor_info':
+        return { debtor_info: debtorData } as Partial<IntakeSession>;
+
+      case 'income_info':
+        // Send the months alone: IncomeInfoStep re-emits them as stored unless the filer
+        // entered source amounts. Echoing other fields read from the server (a blank
+        // marital_status) is a 400 that would strand the filer on Income.
+        return {
+          income_info: { monthly_income: incomeData.monthly_income },
+        } as Partial<IntakeSession>;
+
+      case 'expense_info': {
+        // The total is read-only on the server. The step adds it up in floating point, so
+        // it can differ from the server's decimal sum in the last digit.
+        const expenses = { ...expenseData };
+        delete expenses.total_monthly_expenses;
+        return { expense_info: expenses } as Partial<IntakeSession>;
+      }
+
+      case 'assets':
+        // Filter out empty/blank asset forms before sending
+        return {
+          assets: assetsData.filter((a) => a.asset_type && a.description?.trim()),
+        } as Partial<IntakeSession>;
+
+      case 'debts':
+        // Filter empty forms — debt_type, is_secured, and priority_classification
+        // are already set by DebtsStep via DEBT_CATEGORY_META lookup
+        return {
+          debts: debtsData.filter((d) => d.creditor_name?.trim()),
+        } as Partial<IntakeSession>;
+
+      default:
+        return null;
+    }
+  }, [currentStepKey, debtorData, incomeData, expenseData, assetsData, debtsData]);

   const { saveStatus, saveNow, lastSavedAt } = useAutoSave({
-    data: currentStepData,
-    // saveCurrentStepData reads the latest step state from its closure, so the
-    // `data` snapshot useAutoSave passes to onSave is intentionally unused here.
-    onSave: () => saveCurrentStepData(),
+    data: currentStepBody,
+    // Until the read returns, the steps hold empty placeholders, not the session's data, so
+    // they are kept under no step's name.
+    dataKey: sessionRead === 'done' ? currentStepKey : undefined,
+    onSave: (body) => saveCurrentStepData(body),
     // Only autosave a complete, valid step (see architecture rationale). 'review' has nothing
     // to save; disabled until a session exists.
     enabled: !!session && canProceed && currentStepKey !== 'review',
@@ -239,8 +268,10 @@ export function IntakeWizard() {
         navigate('/sofa');
       }
     } catch (error) {
+      // The filer stays on Review, where WizardLayout shows the reason the context recorded
+      // (DIG-150). If only the means test failed, the intake is already complete, and
+      // pressing Complete again retries both calls.
       console.error('Error completing intake:', error);
-      navigate('/forms');
     }
   };

@@ -248,57 +279,15 @@ export function IntakeWizard() {
   // Data Persistence
   // =========================================================================

-  const saveCurrentStepData = async () => {
+  const saveCurrentStepData = async (body: Partial<IntakeSession> | null) => {
     if (!session) return;

-    const currentStep = WIZARD_STEPS[currentStepNumber - 1];
-
-    // All step data is saved via PATCH /api/intake/sessions/{id}/
-    // The backend IntakeSessionSerializer handles nested create/update
-    switch (currentStep.key) {
-      case 'debtor_info':
-        await api.intake.updateSession(session.id, {
-          debtor_info: debtorData,
-        } as Partial<IntakeSession>);
-        break;
-
-      case 'income_info':
-        // Send the months alone: IncomeInfoStep re-emits them as stored unless the filer
-        // entered source amounts. Echoing other fields read from the server (a blank
-        // marital_status) is a 400 that would strand the filer on Income.
-        await api.intake.updateSession(session.id, {
-          income_info: { monthly_income: incomeData.monthly_income },
-        } as Partial<IntakeSession>);
-        break;
-
-      case 'expense_info':
-        await api.intake.updateSession(session.id, {
-          expense_info: expenseData,
-        } as Partial<IntakeSession>);
-        break;
-
-      case 'assets': {
-        // Filter out empty/blank asset forms before sending
-        const filledAssets = assetsData.filter((a) => a.asset_type && a.description?.trim());
-        await api.intake.updateSession(session.id, {
-          assets: filledAssets,
-        } as Partial<IntakeSession>);
-        break;
-      }
-
-      case 'debts': {
-        // Filter empty forms — debt_type, is_secured, and priority_classification
-        // are already set by DebtsStep via DEBT_CATEGORY_META lookup
-        const filledDebts = debtsData.filter((d) => d.creditor_name?.trim());
-        await api.intake.updateSession(session.id, {
-          debts: filledDebts,
-        } as Partial<IntakeSession>);
-        break;
-      }
-
-      default:
-        console.log(`Saving data for ${currentStep.key} not yet implemented`);
+    if (body === null) {
+      console.log(`Saving data for ${currentStepKey} not yet implemented`);
+      return;
     }
+
+    await api.intake.updateSession(session.id, body);
   };

   // =========================================================================
PATCH
```

The per-step `switch` in `saveCurrentStepData` becomes `currentStepBody`, which the hook compares and `saveCurrentStepData(body)` sends. The catch in `handleComplete` no longer navigates, so the filer stays on Review, where `WizardLayout` shows the reason (DIG-150). The backend change is the DIG-153 test's comment only.

- [ ] **Step 5: Ask the filer to finish their intake on the dashboard**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
index c8bc2a5..9986a06 100644
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -132,6 +132,19 @@ export function FormDashboard() {

       <UPLDisclaimer text={UPL_FORM_DISCLAIMER} variant="banner" />

+      {/* Forms are prepared only from an intake the server marked complete (forms step 2 §5.3) */}
+      {session.status !== 'completed' && (
+        <div className="form-dashboard-notice">
+          <p>
+            Your forms are prepared from your finished intake. To finish it, go back to your intake
+            and press Complete Intake on the last step.
+          </p>
+          <Link to="/intake" className="button button--primary">
+            Finish your intake
+          </Link>
+        </div>
+      )}
+
       {error && (
         <div className="form-dashboard-error" role="alert">
           <p>{error}</p>
diff --git a/frontend/src/styles/global.css b/frontend/src/styles/global.css
index 83e65d5..a0cdcb5 100644
--- a/frontend/src/styles/global.css
+++ b/frontend/src/styles/global.css
@@ -1433,7 +1433,8 @@ a {
   color: var(--color-muted);
 }

-.form-dashboard-error {
+.form-dashboard-error,
+.form-dashboard-notice {
   margin-bottom: var(--space-4);
 }

PATCH
```

The dashboard shows the notice with its link back to the wizard until the session is complete. The notice shares `.form-dashboard-error`'s bottom margin.

- [ ] **Step 6: Run the tests again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/hooks/__tests__/useAutoSave.test.ts src/pages/__tests__/IntakeWizard.test.tsx src/pages/__tests__/FormDashboard.test.tsx 2>&1 | tail -5
```

Expected: `36 passed` on the Tests line, and no failures.

- [ ] **Step 7: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2a.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -3)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `1651 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  261 passed (261)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 8: Run the journeys**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 9: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/intake/tests/test_completion.py \
  frontend/src/hooks/__tests__/useAutoSave.test.ts \
  frontend/src/hooks/useAutoSave.ts \
  frontend/src/pages/FormDashboard.tsx \
  frontend/src/pages/IntakeWizard.tsx \
  frontend/src/pages/__tests__/FormDashboard.test.tsx \
  frontend/src/pages/__tests__/IntakeWizard.test.tsx \
  frontend/src/styles/global.css
git commit -F - <<'MSG'
feat(frontend): keep the filer on Review when Complete fails, and save only real edits

A failed Complete or means-test call now leaves the filer on Review, where the
wizard already shows the reason the intake context recorded, instead of sending
them to /forms (DIG-150). When only the means test fails, the intake is already
complete, and pressing Complete again retries both calls.

The forms dashboard says "Finish your intake", with a link back to the wizard,
until the server has marked the intake complete.

Autosave skips a save whose data equals the step's last saved or loaded copy.
Each wizard step keeps its own copy, so stepping back with Go Back sends nothing
and no longer reopens a completed intake. While a save is still on its way, an
edit is compared with that save's copy instead, so changing a box back before
the reply is still sent. The copy is the request body the save sends: a blank
placeholder row is filtered out, and the expense total, which the server
ignores and the browser adds up in floating point, is left out of it. Continue
still saves the step every time. Two tests that relied on the old save-on-load
now save with Continue.
MSG
git status --short
```

### Task 4: Save contracts and codebtors with Continue, as whole lists

_Built and verified as commit `5b43288` on `plan/forms-step2a`._

**Files:**

- Create: `backend/apps/intake/tests/test_list_saves.py`
- Create: `frontend/src/components/wizard/steps/__tests__/CodebtorsStep.test.tsx`
- Create: `frontend/src/components/wizard/steps/__tests__/ContractsStep.test.tsx`
- Modify: `backend/apps/intake/serializers.py`
- Modify: `backend/apps/intake/tests/test_completion.py`
- Modify: `backend/apps/intake/views.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/wizard/steps/CodebtorsStep.tsx`
- Modify: `frontend/src/components/wizard/steps/ContractsStep.tsx`
- Modify: `frontend/src/components/wizard/steps/ReviewStep.tsx`
- Modify: `frontend/src/components/wizard/steps/__tests__/ReviewStep.test.tsx`
- Modify: `frontend/src/pages/IntakeWizard.tsx`
- Modify: `frontend/src/pages/__tests__/IntakeWizard.test.tsx`
- Modify: `frontend/src/test/mocks/handlers.ts`
- Modify: `frontend/src/types/api.ts`

**Interfaces:**

- Consumes:
  - `_save_rows_by_id(session, model, rows)` in `apps/intake/serializers.py`, the by-id save the nested Assets and Amounts Owed save already uses.
  - `IntakeSession.reopen()` and the `filer`/`completed` fixtures of `apps/intake/tests/test_completion.py` (Task 2).
  - The `contracts` and `codebtors` actions on `IntakeSessionViewSet` (`GET` and `POST` on `/api/intake/sessions/{id}/contracts/` and `/codebtors/`).
  - Task 3's `currentStepBody` in `IntakeWizard.tsx`, which returns null for `contracts` and `codebtors`, and `useAutoSave`'s `saveNow`, which Continue calls.
- Produces:
  - `PUT /api/intake/sessions/{id}/contracts/` and `PUT /api/intake/sessions/{id}/codebtors/`. The body is the whole list as a JSON array. The reply is 200 with the saved rows in id order. One bad row is a 400 and nothing is written. Another user's session is a 404. The save reopens a completed intake. Both `GET`s now return rows in id order. The single-row `POST` and `DELETE` are unchanged.
  - `_save_list(session, model, row_serializer, rows)` in `apps/intake/views.py`.
  - `ExecutoryContractRowSerializer` and `CodebtorRowSerializer` in `apps/intake/serializers.py`, whose `id` is writable (`serializers.IntegerField(required=False)`).
  - `ExecutoryContract` (`contract_type: 'lease' | 'contract' | 'other'`) and `Codebtor` (`relationship: 'spouse' | 'former_spouse' | 'relative' | 'friend' | 'business_partner' | 'other'`) in `src/types/api.ts`.
  - `api.intake.saveContracts(sessionId, contracts) -> Promise<ExecutoryContract[]>` and `api.intake.saveCodebtors(sessionId, codebtors) -> Promise<Codebtor[]>`. `api.intake.contracts` and `api.intake.codebtors` are typed. `createContract`, `deleteContract`, `createCodebtor` and `deleteCodebtor` are removed.
  - `ContractsStep` and `CodebtorsStep` take AssetsStep's props: `initialData?`, `onDataChange` and `onValidationChange`.
  - `ReviewStep` takes `contractsData: ExecutoryContract[]` and `codebtorsData: Codebtor[]`.
  - Default MSW handlers in `src/test/mocks/handlers.ts`: `GET` returns `[]` and `PUT` echoes the body, for both lists.
  - Tests: `test_second_save_does_not_duplicate_codebtors` and `test_second_save_does_not_duplicate_contracts` (`test_list_saves.py`), `test_saving_the_contracts_or_codebtors_list_after_complete_reopens_it` (`test_completion.py`), and the vitest block `IntakeWizard contracts and codebtors`.

**Decisions already made in this task:**

- Every intake-data write reopens a completed intake (owner ruling), and the new list save is one of those writes.
- The whole-list save is a `PUT` on the existing `contracts/` and `codebtors/` URLs, not part of the session PATCH. §7.6 names "the contracts and codebtors list saves" apart from "the nested session save", and Task 3's `currentStepBody` stays null for these two steps.
- The lists save only from Continue, through their own branch in `saveCurrentStepData`, and never autosave. A failed save keeps the filer on the step with the footer the other steps show, "We couldn't save just now — we'll try again when you continue." Remove and edits on steps 6 and 7 take effect with that step's Continue.
- The server checks every row (`many=True`) before it writes any. The writes and `session.reopen()` share one `transaction.atomic()`, so a refused save neither writes nor reopens.
- An empty list deletes every stored row, because it means the filer has none (§5.4).
- The writable `id` lives only on the two `*RowSerializer` subclasses, so the single-row `POST` never takes a client id. That `POST` and the `DELETE` stay, because Task 2's reopen tests pin them. The four client functions that called them are removed, because nothing calls them any more.
- `views.py` imports `_save_rows_by_id` under its private name, which root `CLAUDE.md` uses. It is not renamed.
- Both lists are read with the session, before any step shows. A failed list read shows the wizard's existing "Try again" alert. A new session (created, or after a 404) gets empty lists without a read. A list held empty after a failed read would delete every stored row on Continue.
- The wizard keeps the rows the save returns, so the next save updates them by id.
- A row counts as started once a text box holds something; the selects don't count, because they have defaults. A started row with no name holds Continue with "Please enter the name of the other party" (contracts) or "Please enter this person's full name" (codebtors). These two messages are new, worded like the Debts step's "Please enter the creditor name". A blank row is valid and is left out of the save, and so is a row where only a select changed.
- The boxes stop at their columns' lengths: the other party's name and the codebtor's name and street at 255, city at 100, ZIP at 10. The description is a text column with no limit, and State already stopped at 2.
- Review lists each contract's name with its stored type and each codebtor's name with the relationship (`_` shown as a space), as it already does for assets. The headings and empty lines follow Review's "Assets (n)" and "No assets listed.".
- `handleNext` sets `setCanProceed(false)` on every step change. The old pre-approval of steps 6 and 7 is gone, because each step now reports its own validity (DIG-165).
- No journey adds a contract or codebtor. The journeys press Continue on empty lists, and the backend tests cover rows.

- [ ] **Step 1: Write the backend tests for the list save**

```python file=backend/apps/intake/tests/test_list_saves.py
"""Continue on the Contracts and Codebtors steps saves the whole list by id (DIG-147).

Business intent: Schedules G and H, and their yes/no answers, are read from these lists, and
the filer signs them under penalty of perjury. Each Continue sends the list the step shows:
a row carrying one of this session's ids updates in place, any other row is created, and a
stored row the list left out is deleted. So saving twice never lists one contract twice, a
removed row never lingers, one bad row saves nothing, and a row can only ever change the
filer's own session.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import Codebtor, ExecutoryContract, IntakeSession
from apps.users.models import User

# Each list's model, its name field and three rows a filer might enter.
LISTS = {
    "contracts": (
        ExecutoryContract,
        "counterparty_name",
        [
            {
                "counterparty_name": "Oak Street Apartments",
                "contract_type": "lease",
                "description": "Apartment lease",
            },
            {"counterparty_name": "Metro Gym", "contract_type": "contract", "description": ""},
            {"counterparty_name": "Lakeview Storage", "contract_type": "other", "description": ""},
        ],
    ),
    "codebtors": (
        Codebtor,
        "name",
        [
            {"name": "Sam Doe", "relationship": "relative", "city": "Chicago", "state": "IL"},
            {"name": "Ana Ruiz", "relationship": "friend"},
            {"name": "Lee Park", "relationship": "former_spouse", "zip_code": "60601"},
        ],
    ),
}


@pytest.fixture
def district(db):
    return District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )


@pytest.fixture
def filer(district):
    user = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=user, district=district)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session


@pytest.fixture
def other_session(district):
    other = User.objects.create_user(username="other", password="pw")
    return IntakeSession.objects.create(user=other, district=district)


def _list_url(session, endpoint):
    return f"/api/intake/sessions/{session.pk}/{endpoint}/"


def _save_twice_as_the_wizard_does(client, session, endpoint):
    """Continue, then Continue again with the rows the first save returned, one renamed."""
    model, name, rows = LISTS[endpoint]
    url = _list_url(session, endpoint)

    first = client.put(url, rows[:2], format="json")
    assert first.status_code == 200
    first_ids = [row["id"] for row in first.data]

    again = [dict(row) for row in first.data]
    again[0][name] = "Renamed Party"
    second = client.put(url, again, format="json")

    assert second.status_code == 200
    assert [row["id"] for row in second.data] == first_ids
    stored = model.objects.filter(session=session).order_by("id")
    assert list(stored.values_list("pk", flat=True)) == first_ids
    assert [getattr(row, name) for row in stored] == ["Renamed Party", rows[1][name]]


def test_second_save_does_not_duplicate_codebtors(filer):
    client, session = filer
    _save_twice_as_the_wizard_does(client, session, "codebtors")


def test_second_save_does_not_duplicate_contracts(filer):
    client, session = filer
    _save_twice_as_the_wizard_does(client, session, "contracts")


@pytest.mark.parametrize("endpoint", ["contracts", "codebtors"])
def test_saving_a_list_keeps_sent_rows_adds_new_ones_and_drops_removed_ones(filer, endpoint):
    client, session = filer
    model, name, rows = LISTS[endpoint]
    kept = model.objects.create(session=session, **rows[0])
    removed = model.objects.create(session=session, **rows[1])

    response = client.put(
        _list_url(session, endpoint), [{"id": kept.pk, **rows[0]}, rows[2]], format="json"
    )

    assert response.status_code == 200
    stored = {getattr(row, name): row for row in model.objects.filter(session=session)}
    assert set(stored) == {rows[0][name], rows[2][name]}
    assert stored[rows[0][name]].pk == kept.pk
    assert not model.objects.filter(pk=removed.pk).exists()
    assert [row[name] for row in response.data] == [rows[0][name], rows[2][name]]


@pytest.mark.parametrize("endpoint", ["contracts", "codebtors"])
def test_removing_every_row_leaves_none_stored_and_reopens_the_intake(filer, endpoint):
    # An empty list means the filer said none: a removed last lease or codebtor must not
    # stay stored and print on Schedule G or H.
    client, session = filer
    model, _, rows = LISTS[endpoint]
    model.objects.create(session=session, **rows[0])
    model.objects.create(session=session, **rows[1])
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")

    response = client.put(_list_url(session, endpoint), [], format="json")

    assert response.status_code == 200
    assert response.data == []
    assert not model.objects.filter(session=session).exists()
    assert IntakeSession.objects.get(pk=session.pk).status == "in_progress"


@pytest.mark.parametrize(
    "endpoint,bad_row",
    [
        ("contracts", {"counterparty_name": "", "contract_type": "lease"}),
        ("codebtors", {"name": "Lee Park", "zip_code": "60601-1234-99"}),
    ],
)
def test_a_list_with_one_bad_row_saves_nothing(filer, endpoint, bad_row):
    client, session = filer
    model, name, rows = LISTS[endpoint]
    stored = model.objects.create(session=session, **rows[0])
    IntakeSession.objects.filter(pk=session.pk).update(status="completed")

    response = client.put(
        _list_url(session, endpoint),
        [{"id": stored.pk, **rows[0], name: "Renamed Party"}, rows[1], bad_row],
        format="json",
    )

    assert response.status_code == 400
    assert list(model.objects.filter(session=session)) == [stored]
    stored.refresh_from_db()
    assert getattr(stored, name) == rows[0][name]
    assert IntakeSession.objects.get(pk=session.pk).status == "completed"


@pytest.mark.parametrize("endpoint", ["contracts", "codebtors"])
def test_a_list_row_carrying_another_users_row_id_never_changes_that_row(
    filer, other_session, endpoint
):
    client, session = filer
    model, name, rows = LISTS[endpoint]
    theirs = model.objects.create(session=other_session, **rows[0])

    response = client.put(
        _list_url(session, endpoint), [{"id": theirs.pk, **rows[1]}], format="json"
    )

    assert response.status_code == 200
    theirs.refresh_from_db()
    assert theirs.session_id == other_session.pk
    assert getattr(theirs, name) == rows[0][name]
    mine = model.objects.get(session=session)
    assert mine.pk != theirs.pk
    assert getattr(mine, name) == rows[1][name]


@pytest.mark.parametrize("endpoint", ["contracts", "codebtors"])
def test_filer_cannot_save_a_list_onto_another_users_intake(filer, other_session, endpoint):
    client, _ = filer
    _, _, rows = LISTS[endpoint]

    response = client.put(_list_url(other_session, endpoint), rows[:1], format="json")

    assert response.status_code == 404
    assert not LISTS[endpoint][0].objects.filter(session=other_session).exists()
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/tests/test_completion.py b/backend/apps/intake/tests/test_completion.py
index 42db410..8e1cb1b 100644
--- a/backend/apps/intake/tests/test_completion.py
+++ b/backend/apps/intake/tests/test_completion.py
@@ -257,6 +257,25 @@ def test_adding_or_removing_a_contract_or_codebtor_after_complete_reopens_it(
     assert _status(completed) == "in_progress"


+@pytest.mark.parametrize(
+    "endpoint,row",
+    [
+        ("contracts", {"counterparty_name": "Oak Street Apartments", "contract_type": "lease"}),
+        ("codebtors", {"name": "Sam Doe", "relationship": "relative"}),
+    ],
+)
+def test_saving_the_contracts_or_codebtors_list_after_complete_reopens_it(
+    filer, completed, endpoint, row
+):
+    # Continue on steps 6 and 7 saves the whole list (DIG-147).
+    client, _ = filer
+
+    response = client.put(_session_url(completed, f"{endpoint}/"), [row], format="json")
+
+    assert response.status_code == 200
+    assert _status(completed) == "in_progress"
+
+
 @pytest.mark.parametrize(
     "endpoint,row,change",
     [
PATCH
```

`test_list_saves.py` saves each list twice the way Continue does and checks that no row is added again. It also checks that a list keeps the rows it sent, adds new ones and drops the ones it left out, and that an empty list deletes everything and reopens the intake. One bad row must save nothing and leave a completed intake complete. A row carrying another user's row id must never change that row, and another user's intake is a 404. The `test_completion.py` test adds the list save to Task 2's reopen call sites.

- [ ] **Step 2: Run the backend tests and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_list_saves.py apps/intake/tests/test_completion.py -q -p no:cacheprovider 2>&1 | tail -3
```

Expected: FAIL — `14 failed`. The two endpoints don't take a PUT yet, so each new test gets a 405 where it expects a 200, 400 or 404.

- [ ] **Step 3: Save the whole list by id, and read it back in id order**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/serializers.py b/backend/apps/intake/serializers.py
index 04cd67d..ac5284e 100644
--- a/backend/apps/intake/serializers.py
+++ b/backend/apps/intake/serializers.py
@@ -245,7 +245,7 @@ class NestedDebtInfoSerializer(DebtInfoSerializer):


 def _save_rows_by_id(session, model, rows) -> None:
-    """Save a session's nested assets or debts by id.
+    """Save a session's nested assets or debts, or its contracts or codebtors list, by id.

     A row whose id is one of this session's rows updates only the fields it sent, so
     what the browser never received (account numbers, the scanned-bill link, the
@@ -583,3 +583,19 @@ class CodebtorSerializer(serializers.ModelSerializer):
             "zip_code",
             "relationship",
         ]
+
+
+class ExecutoryContractRowSerializer(ExecutoryContractSerializer):
+    """A contract row in the Contracts step's list save.
+
+    The id is writable so a row the wizard loaded updates in place. The single-contract
+    POST keeps the base serializer, so it never accepts a client id.
+    """
+
+    id = serializers.IntegerField(required=False)
+
+
+class CodebtorRowSerializer(CodebtorSerializer):
+    """A codebtor row in the Codebtors step's list save. See ExecutoryContractRowSerializer."""
+
+    id = serializers.IntegerField(required=False)
diff --git a/backend/apps/intake/views.py b/backend/apps/intake/views.py
index 8eaf0ce..0adf432 100644
--- a/backend/apps/intake/views.py
+++ b/backend/apps/intake/views.py
@@ -26,15 +26,35 @@ from .models import (
 from .serializers import (
     AssetInfoSerializer,
     BulkAnswerPayloadSerializer,
+    CodebtorRowSerializer,
     CodebtorSerializer,
     DebtInfoSerializer,
+    ExecutoryContractRowSerializer,
     ExecutoryContractSerializer,
     FeeWaiverApplicationSerializer,
     IntakeSessionSerializer,
     SOFAReportSerializer,
+    _save_rows_by_id,
 )


+def _save_list(session, model, row_serializer, rows):
+    """Save the whole list the Contracts or Codebtors step shows (DIG-147).
+
+    Every row is checked before anything is written, so one bad row saves nothing. Then a
+    row carrying one of this session's ids updates in place, any other row is created, and
+    a stored row the list left out is deleted (see _save_rows_by_id). Returns the saved
+    rows in id order, so the wizard keeps their ids for the next save.
+    """
+    serializer = row_serializer(data=rows, many=True)
+    serializer.is_valid(raise_exception=True)
+    with transaction.atomic():
+        _save_rows_by_id(session, model, serializer.validated_data)
+        session.reopen()
+    saved = model.objects.filter(session=session).order_by("id")
+    return Response(row_serializer(saved, many=True).data)
+
+
 def _assert_session_owned(session, user):
     """Reject writes that attach a row to another user's intake session (IDOR guard).

@@ -356,13 +376,17 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):

         return Response({"status": "success", "created": created_count, "updated": updated_count})

-    @action(detail=True, methods=["get", "post"], url_path="contracts", url_name="contracts")
+    @action(detail=True, methods=["get", "post", "put"], url_path="contracts", url_name="contracts")
     def contracts(self, request, pk=None):
         session = self.get_object()
         if request.method == "GET":
-            contracts = ExecutoryContract.objects.filter(session=session)
+            contracts = ExecutoryContract.objects.filter(session=session).order_by("id")
             serializer = ExecutoryContractSerializer(contracts, many=True)
             return Response(serializer.data)
+        if request.method == "PUT":
+            return _save_list(
+                session, ExecutoryContract, ExecutoryContractRowSerializer, request.data
+            )
         serializer = ExecutoryContractSerializer(data=request.data)
         serializer.is_valid(raise_exception=True)
         serializer.save(session=session)
@@ -385,13 +409,15 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         except ExecutoryContract.DoesNotExist:
             return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

-    @action(detail=True, methods=["get", "post"], url_path="codebtors", url_name="codebtors")
+    @action(detail=True, methods=["get", "post", "put"], url_path="codebtors", url_name="codebtors")
     def codebtors(self, request, pk=None):
         session = self.get_object()
         if request.method == "GET":
-            codebtors = Codebtor.objects.filter(session=session)
+            codebtors = Codebtor.objects.filter(session=session).order_by("id")
             serializer = CodebtorSerializer(codebtors, many=True)
             return Response(serializer.data)
+        if request.method == "PUT":
+            return _save_list(session, Codebtor, CodebtorRowSerializer, request.data)
         serializer = CodebtorSerializer(data=request.data)
         serializer.is_valid(raise_exception=True)
         serializer.save(session=session)
PATCH
```

`_save_list` checks the whole list, then saves it through `_save_rows_by_id` and reopens the intake in one transaction, and returns the saved rows in id order. The `contracts` and `codebtors` actions take `put` and call it, and their `GET`s order by id.

- [ ] **Step 4: Run the backend tests again**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_list_saves.py apps/intake/tests/test_completion.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `39 passed`.

- [ ] **Step 5: Write the frontend tests and the default list handlers**

```tsx file=frontend/src/components/wizard/steps/__tests__/ContractsStep.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ContractsStep } from '../ContractsStep';
import type { ExecutoryContract } from '../../../../types/api';

// The server refuses a contract whose other party's name is longer than its column holds,
// and the wizard can only say it couldn't save, so Continue would never succeed. The box
// stops at that length instead.

const lease: ExecutoryContract = {
  id: 4,
  counterparty_name: 'Oak Street Apartments',
  contract_type: 'lease',
  description: 'Apartment lease',
};

describe('ContractsStep', () => {
  it("keeps the other party's name within the length the server stores, so a long name never blocks Continue", async () => {
    const onDataChange = vi.fn();
    render(
      <ContractsStep
        initialData={[lease]}
        onDataChange={onDataChange}
        onValidationChange={() => {}}
      />
    );

    const user = userEvent.setup();
    await user.clear(screen.getByDisplayValue('Oak Street Apartments'));
    await user.paste('O'.repeat(300));

    expect(onDataChange).toHaveBeenLastCalledWith([
      { ...lease, counterparty_name: 'O'.repeat(255) },
    ]);
  });
});
```

```tsx file=frontend/src/components/wizard/steps/__tests__/CodebtorsStep.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CodebtorsStep } from '../CodebtorsStep';
import type { Codebtor } from '../../../../types/api';

// The server refuses a codebtor whose name, street, city or ZIP is longer than its column
// holds, and the wizard can only say it couldn't save, so Continue would never succeed.
// Each box stops at that length instead.

const codebtor: Codebtor = {
  id: 3,
  name: 'Sam Doe',
  street_address: '1 Main St',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60601',
  relationship: 'relative',
};

describe('CodebtorsStep', () => {
  it('keeps each box within the length the server stores, so a long entry never blocks Continue', async () => {
    const onDataChange = vi.fn();
    render(
      <CodebtorsStep
        initialData={[codebtor]}
        onDataChange={onDataChange}
        onValidationChange={() => {}}
      />
    );

    const user = userEvent.setup();
    const typeOver = async (shown: string, text: string) => {
      await user.clear(screen.getByDisplayValue(shown));
      await user.paste(text);
    };
    await typeOver('Sam Doe', 'N'.repeat(300));
    await typeOver('1 Main St', 'S'.repeat(300));
    await typeOver('Chicago', 'C'.repeat(150));
    await typeOver('60601', '60601-1234-99');

    expect(onDataChange).toHaveBeenLastCalledWith([
      {
        ...codebtor,
        name: 'N'.repeat(255),
        street_address: 'S'.repeat(255),
        city: 'C'.repeat(100),
        zip_code: '60601-1234',
      },
    ]);
  });
});
```

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/wizard/steps/__tests__/ReviewStep.test.tsx b/frontend/src/components/wizard/steps/__tests__/ReviewStep.test.tsx
index 2898ffa..9ffc5cd 100644
--- a/frontend/src/components/wizard/steps/__tests__/ReviewStep.test.tsx
+++ b/frontend/src/components/wizard/steps/__tests__/ReviewStep.test.tsx
@@ -12,6 +12,8 @@ const baseProps = {
   expenseData: {},
   assetsData: [],
   debtsData: [],
+  contractsData: [],
+  codebtorsData: [],
 };

 describe('ReviewStep null-safe rendering', () => {
@@ -44,6 +46,46 @@ describe('ReviewStep null-safe rendering', () => {
     expect(document.body.textContent).not.toMatch(/undefined|NaN/);
   });

+  // DIG-166: the filer's last look before completing includes steps 6 and 7, so a lost or
+  // doubled contract or codebtor shows here instead of only on Schedules G and H.
+  it('lists the contracts and codebtors the filer saved, or says there are none', () => {
+    const { rerender } = render(
+      <ReviewStep
+        {...baseProps}
+        contractsData={[
+          {
+            id: 4,
+            counterparty_name: 'Oak Street Apartments',
+            contract_type: 'lease',
+            description: 'Apartment lease',
+          },
+        ]}
+        codebtorsData={[
+          {
+            id: 3,
+            name: 'Sam Doe',
+            street_address: '',
+            city: 'Chicago',
+            state: 'IL',
+            zip_code: '',
+            relationship: 'former_spouse',
+          },
+        ]}
+        onValidationChange={vi.fn()}
+      />
+    );
+
+    expect(screen.getByText('Contracts & Leases (1)')).toBeInTheDocument();
+    expect(screen.getByText(/Oak Street Apartments/)).toHaveTextContent('(lease)');
+    expect(screen.getByText('Codebtors (1)')).toBeInTheDocument();
+    expect(screen.getByText(/Sam Doe/)).toHaveTextContent('(former spouse)');
+
+    rerender(<ReviewStep {...baseProps} onValidationChange={vi.fn()} />);
+
+    expect(screen.getByText('No contracts or leases listed.')).toBeInTheDocument();
+    expect(screen.getByText('No codebtors listed.')).toBeInTheDocument();
+  });
+
   it('signals the step is always valid to proceed', () => {
     const onValidationChange = vi.fn();
     render(<ReviewStep {...baseProps} onValidationChange={onValidationChange} />);
diff --git a/frontend/src/pages/__tests__/IntakeWizard.test.tsx b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
index 67a96ac..23a6659 100644
--- a/frontend/src/pages/__tests__/IntakeWizard.test.tsx
+++ b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
@@ -318,6 +318,15 @@ describe('IntakeWizard stepping back', { timeout: 30_000 }, () => {
       http.get('http://localhost:8000/api/intake/sessions/:id/codebtors/', () =>
         HttpResponse.json([])
       ),
+      // A list save reopens a completed intake too
+      http.put('http://localhost:8000/api/intake/sessions/:id/contracts/', () => {
+        sessionSaves += 1;
+        return HttpResponse.json([]);
+      }),
+      http.put('http://localhost:8000/api/intake/sessions/:id/codebtors/', () => {
+        sessionSaves += 1;
+        return HttpResponse.json([]);
+      }),
       http.post(
         'http://localhost:8000/api/audit/logs/',
         () => new HttpResponse(null, { status: 201 })
@@ -867,3 +876,290 @@ describe('IntakeWizard expense hydration', { timeout: 15_000 }, () => {
     expect(screen.getByText('$2,560.00')).toBeInTheDocument();
   });
 });
+
+// ===========================================================================
+// Contracts and codebtors (DIG-147, DIG-165, DIG-166)
+// ===========================================================================
+
+const storedLease = {
+  id: 4,
+  counterparty_name: 'Oak Street Apartments',
+  contract_type: 'lease',
+  description: 'Apartment lease',
+};
+const storedGym = {
+  id: 5,
+  counterparty_name: 'Metro Gym',
+  contract_type: 'contract',
+  description: '',
+};
+const storedCodebtor = {
+  id: 3,
+  name: 'Sam Doe',
+  street_address: '',
+  city: 'Chicago',
+  state: 'IL',
+  zip_code: '',
+  relationship: 'relative',
+};
+
+describe('IntakeWizard contracts and codebtors', { timeout: 15_000 }, () => {
+  let contractSaves: unknown[];
+  let codebtorSaves: unknown[];
+  let stepUpdates: unknown[];
+
+  /** A filer who stopped at `step`, with these lists saved earlier. */
+  function serveFiler(
+    step: number,
+    contracts: Record<string, unknown>[] = [],
+    codebtors: Record<string, unknown>[] = []
+  ) {
+    // The server gives each new row the next id, as the list save does
+    let nextId = 10;
+    const saveList =
+      (saves: unknown[]) =>
+      async ({ request }: { request: Request }) => {
+        const rows = (await request.json()) as Record<string, unknown>[];
+        saves.push(rows);
+        return HttpResponse.json(rows.map((row) => ({ ...row, id: row.id ?? nextId++ })));
+      };
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+        HttpResponse.json({
+          ...sessionAtStep1,
+          current_step: step,
+          debtor_info: { first_name: 'Jane', last_name: 'Doe' },
+        })
+      ),
+      http.get('http://localhost:8000/api/intake/sessions/:id/contracts/', () =>
+        HttpResponse.json(contracts)
+      ),
+      http.get('http://localhost:8000/api/intake/sessions/:id/codebtors/', () =>
+        HttpResponse.json(codebtors)
+      ),
+      http.put('http://localhost:8000/api/intake/sessions/:id/contracts/', saveList(contractSaves)),
+      http.put('http://localhost:8000/api/intake/sessions/:id/codebtors/', saveList(codebtorSaves))
+    );
+  }
+
+  /** The wizard's own step title (each list step repeats it in a heading of its own). */
+  async function expectStep(title: string) {
+    await waitFor(() => expect(document.querySelector('.step-title')).toHaveTextContent(title));
+  }
+
+  beforeEach(() => {
+    contractSaves = [];
+    codebtorSaves = [];
+    stepUpdates = [];
+    server.use(
+      http.post(
+        'http://localhost:8000/api/intake/sessions/:id/update_step/',
+        async ({ request }) => {
+          const body = (await request.json()) as { current_step: number };
+          stepUpdates.push(body.current_step);
+          return HttpResponse.json({
+            session: { ...sessionAtStep1, current_step: body.current_step, status: 'in_progress' },
+            message: 'Step updated.',
+          });
+        }
+      ),
+      http.post(
+        'http://localhost:8000/api/audit/logs/',
+        () => new HttpResponse(null, { status: 201 })
+      )
+    );
+  });
+
+  it.each([
+    [6, 'Contracts & Leases'],
+    [7, 'Codebtors'],
+  ])('lets a filer who resumes at step %i (%s) continue', async (step, title) => {
+    serveFiler(step);
+    renderWizard();
+    await expectStep(title);
+
+    // The step reports itself valid just after it shows
+    await waitFor(() => expect(screen.getByRole('button', { name: /continue/i })).toBeEnabled());
+  });
+
+  it('saves the whole contracts list on Continue, and sends the saved ids on the next save instead of adding rows again', async () => {
+    serveFiler(6, [storedLease, storedGym]);
+    renderWizard();
+    await expectStep('Contracts & Leases');
+
+    // Remove the gym, add a storage unit, and add a row the filer leaves blank
+    await userEvent.click(screen.getAllByRole('button', { name: 'Remove' })[1]);
+    await userEvent.click(screen.getByRole('button', { name: /add contract/i }));
+    await userEvent.type(
+      screen.getAllByPlaceholderText('e.g., Landlord Inc.')[1],
+      'Lakeview Storage'
+    );
+    await userEvent.click(screen.getByRole('button', { name: /add contract/i }));
+    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
+    await expectStep('Codebtors');
+
+    const lakeview = {
+      counterparty_name: 'Lakeview Storage',
+      contract_type: 'contract',
+      description: '',
+    };
+    expect(contractSaves).toEqual([[storedLease, lakeview]]);
+
+    // Back to Contracts and on again: the storage unit now carries the id the save returned
+    await userEvent.click(screen.getByRole('button', { name: 'Go Back' }));
+    await expectStep('Contracts & Leases');
+    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
+    await expectStep('Codebtors');
+
+    expect(contractSaves[1]).toEqual([storedLease, { ...lakeview, id: 10 }]);
+  });
+
+  // An empty list means the filer has none: a removed last row must not stay stored and
+  // print on Schedule G or H
+  it.each([
+    [6, 'Contracts & Leases', 'Codebtors', [storedLease], [], () => contractSaves],
+    [7, 'Codebtors', 'Review & Results', [], [storedCodebtor], () => codebtorSaves],
+  ])(
+    'saves an empty list when the filer removes the last row on step %i (%s)',
+    async (step, title, nextTitle, contracts, codebtors, saves) => {
+      serveFiler(step, contracts, codebtors);
+      renderWizard();
+      await expectStep(title);
+
+      await userEvent.click(screen.getByRole('button', { name: 'Remove' }));
+      await userEvent.click(screen.getByRole('button', { name: /continue/i }));
+      await expectStep(nextTitle);
+
+      expect(saves()).toEqual([[]]);
+    }
+  );
+
+  it.each([
+    [6, 'Contracts & Leases', 'contracts', [storedLease], [], 'counterparty_name'],
+    [7, 'Codebtors', 'codebtors', [], [storedCodebtor], 'name'],
+  ])(
+    'keeps the filer on step %i (%s) and says so when the list cannot be saved',
+    async (step, title, list, contracts, codebtors, field) => {
+      serveFiler(step, contracts, codebtors);
+      server.use(
+        http.put(`http://localhost:8000/api/intake/sessions/:id/${list}/`, () =>
+          HttpResponse.json([{ [field]: ['This field may not be blank.'] }], {
+            status: 400,
+          })
+        )
+      );
+      renderWizard();
+      await expectStep(title);
+
+      await userEvent.click(screen.getByRole('button', { name: /continue/i }));
+
+      expect(await screen.findByText(/couldn't save just now/i)).toBeInTheDocument();
+      expect(document.querySelector('.step-title')).toHaveTextContent(title);
+      expect(stepUpdates).toEqual([]);
+    }
+  );
+
+  it("asks for the other party's name before a contract the filer started can be saved", async () => {
+    serveFiler(6);
+    renderWizard();
+    await expectStep('Contracts & Leases');
+
+    await userEvent.click(screen.getByRole('button', { name: /add contract/i }));
+    await userEvent.type(screen.getByPlaceholderText('e.g., Apartment lease, car loan'), 'Lease');
+
+    expect(screen.getByRole('alert')).toHaveTextContent('Please enter the name of the other party');
+    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();
+
+    await userEvent.type(screen.getByPlaceholderText('e.g., Landlord Inc.'), 'Oak Street');
+    expect(screen.getByRole('button', { name: /continue/i })).toBeEnabled();
+  });
+
+  it("asks for the person's name before a codebtor the filer started can be saved", async () => {
+    serveFiler(7);
+    renderWizard();
+    await expectStep('Codebtors');
+
+    await userEvent.click(screen.getByRole('button', { name: /add codebtor/i }));
+    // The City label has no htmlFor yet, so the box is the element after it
+    await userEvent.type(screen.getByText('City').nextElementSibling as HTMLElement, 'Chicago');
+
+    expect(screen.getByRole('alert')).toHaveTextContent("Please enter this person's full name");
+    expect(screen.getByRole('button', { name: /continue/i })).toBeDisabled();
+
+    await userEvent.type(screen.getByPlaceholderText('e.g., Jane Smith'), 'Ana Ruiz');
+    expect(screen.getByRole('button', { name: /continue/i })).toBeEnabled();
+  });
+
+  it('saves the codebtors list on Continue and lists both lists on Review', async () => {
+    serveFiler(7, [storedLease], [storedCodebtor]);
+    renderWizard();
+    await expectStep('Codebtors');
+
+    // Add Ana, and add a row the filer leaves blank
+    await userEvent.click(screen.getByRole('button', { name: /add codebtor/i }));
+    await userEvent.type(screen.getAllByPlaceholderText('e.g., Jane Smith')[1], 'Ana Ruiz');
+    await userEvent.click(screen.getByRole('button', { name: /add codebtor/i }));
+    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
+    await expectStep('Review & Results');
+
+    expect(codebtorSaves).toEqual([
+      [
+        storedCodebtor,
+        {
+          name: 'Ana Ruiz',
+          street_address: '',
+          city: '',
+          state: '',
+          zip_code: '',
+          relationship: 'other',
+        },
+      ],
+    ]);
+    // Review lists the rows the save returned, not the step's copy with the blank row in it
+    expect(screen.getByText('Codebtors (2)')).toBeInTheDocument();
+    expect(screen.getByText(/Oak Street Apartments/)).toBeInTheDocument();
+    expect(screen.getByText(/Sam Doe/)).toBeInTheDocument();
+    expect(screen.getByText(/Ana Ruiz/)).toBeInTheDocument();
+  });
+
+  it('shows the saved contracts and codebtors on Review to a filer who resumes there', async () => {
+    serveFiler(8, [storedLease], [storedCodebtor]);
+    renderWizard();
+    await expectStep('Review & Results');
+
+    expect(screen.getByText(/Oak Street Apartments/)).toBeInTheDocument();
+    expect(screen.getByText(/Sam Doe/)).toBeInTheDocument();
+  });
+
+  it('shows no step when the saved contracts cannot be read, so Continue never saves an empty list over them', async () => {
+    serveFiler(6, [storedLease]);
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/contracts/', () =>
+        HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
+      )
+    );
+    renderWizard();
+
+    expect(await screen.findByRole('alert')).toHaveTextContent(
+      "We couldn't get your latest information just now. Please try again in a moment."
+    );
+    expect(screen.queryByRole('button', { name: /continue/i })).not.toBeInTheDocument();
+    expect(contractSaves).toEqual([]);
+  });
+
+  it('shows no step when the saved codebtors cannot be read, so Continue never saves an empty list over them', async () => {
+    serveFiler(7, [], [storedCodebtor]);
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/codebtors/', () =>
+        HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
+      )
+    );
+    renderWizard();
+
+    expect(await screen.findByRole('alert')).toHaveTextContent(
+      "We couldn't get your latest information just now. Please try again in a moment."
+    );
+    expect(screen.queryByRole('button', { name: /continue/i })).not.toBeInTheDocument();
+    expect(codebtorSaves).toEqual([]);
+  });
+});
diff --git a/frontend/src/test/mocks/handlers.ts b/frontend/src/test/mocks/handlers.ts
index 664bfc1..56a0ba5 100644
--- a/frontend/src/test/mocks/handlers.ts
+++ b/frontend/src/test/mocks/handlers.ts
@@ -171,6 +171,20 @@ export const handlers = [
     HttpResponse.json({ id: 1, session: 1, debt_type: 'credit_card', creditor_name: 'Visa' })
   ),

+  // -- Contracts / Codebtors (the wizard reads both lists with the session) --
+
+  http.get(`${API}/intake/sessions/:id/contracts/`, () => HttpResponse.json([])),
+
+  http.put(`${API}/intake/sessions/:id/contracts/`, async ({ request }) =>
+    HttpResponse.json(await request.json())
+  ),
+
+  http.get(`${API}/intake/sessions/:id/codebtors/`, () => HttpResponse.json([])),
+
+  http.put(`${API}/intake/sessions/:id/codebtors/`, async ({ request }) =>
+    HttpResponse.json(await request.json())
+  ),
+
   // -- Documents -----------------------------------------------------------

   http.post(`${API}/documents/upload/`, () =>
PATCH
```

The `IntakeWizard contracts and codebtors` block serves a filer who stopped at a step with saved lists. Its tests check that:

- a filer who resumes at step 6 or 7 can continue;
- Continue sends the list the step shows without its blank rows, and the next save carries the ids the first one returned;
- removing the last row saves an empty list;
- a refused save keeps the filer on the step with the save error and no step change;
- a started row with no name asks for it;
- Review lists both lists;
- a list that can't be read shows no step, so Continue can't save it as empty.

The two step tests paste past each box's limit and check what the step hands the wizard. Task 3's step-back test now counts list saves too, because a list save reopens a completed intake. Every wizard mount now reads both lists, so the default handlers serve them.

- [ ] **Step 6: Run the frontend tests and watch them fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/IntakeWizard.test.tsx src/components/wizard/steps/__tests__/ReviewStep.test.tsx src/components/wizard/steps/__tests__/ContractsStep.test.tsx src/components/wizard/steps/__tests__/CodebtorsStep.test.tsx 2>&1 | tail -6
```

Expected: FAIL — `16 failed`. The steps fetch and save their own rows and never report to the wizard, Continue never saves the lists, and Review doesn't list them.

- [ ] **Step 7: Type the lists and the client calls**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/api/client.ts b/frontend/src/api/client.ts
index b7f1e83..c24821e 100644
--- a/frontend/src/api/client.ts
+++ b/frontend/src/api/client.ts
@@ -21,6 +21,8 @@ import type {
   SessionSummaryResponse,
   AssetInfo,
   DebtInfo,
+  ExecutoryContract,
+  Codebtor,
   GeneratedForm,
   APIError,
   LoginRequest,
@@ -376,34 +378,36 @@ export const intakeAPI = {
   },

   // Contracts (Schedule G)
-  contracts: async (sessionId: number): Promise<unknown[]> => {
-    return apiFetch<unknown[]>(`/intake/sessions/${sessionId}/contracts/`);
+  contracts: async (sessionId: number): Promise<ExecutoryContract[]> => {
+    return apiFetch<ExecutoryContract[]>(`/intake/sessions/${sessionId}/contracts/`);
   },
-  createContract: async (sessionId: number, data: unknown): Promise<unknown> => {
-    return apiFetch<unknown>(`/intake/sessions/${sessionId}/contracts/`, {
-      method: 'POST',
-      body: JSON.stringify(data),
-    });
-  },
-  deleteContract: async (sessionId: number, contractId: number): Promise<void> => {
-    await apiFetch<void>(`/intake/sessions/${sessionId}/contracts/${contractId}/`, {
-      method: 'DELETE',
+  /**
+   * Save the Contracts step's whole list: a row with an id updates, a row without one is
+   * created, and a saved row the list leaves out is deleted. Resolves with the saved rows.
+   * PUT /api/intake/sessions/{id}/contracts/
+   */
+  saveContracts: async (
+    sessionId: number,
+    contracts: ExecutoryContract[]
+  ): Promise<ExecutoryContract[]> => {
+    return apiFetch<ExecutoryContract[]>(`/intake/sessions/${sessionId}/contracts/`, {
+      method: 'PUT',
+      body: JSON.stringify(contracts),
     });
   },

   // Codebtors (Schedule H)
-  codebtors: async (sessionId: number): Promise<unknown[]> => {
-    return apiFetch<unknown[]>(`/intake/sessions/${sessionId}/codebtors/`);
+  codebtors: async (sessionId: number): Promise<Codebtor[]> => {
+    return apiFetch<Codebtor[]>(`/intake/sessions/${sessionId}/codebtors/`);
   },
-  createCodebtor: async (sessionId: number, data: unknown): Promise<unknown> => {
-    return apiFetch<unknown>(`/intake/sessions/${sessionId}/codebtors/`, {
-      method: 'POST',
-      body: JSON.stringify(data),
-    });
-  },
-  deleteCodebtor: async (sessionId: number, codebtorId: number): Promise<void> => {
-    await apiFetch<void>(`/intake/sessions/${sessionId}/codebtors/${codebtorId}/`, {
-      method: 'DELETE',
+  /**
+   * Save the Codebtors step's whole list, as saveContracts does.
+   * PUT /api/intake/sessions/{id}/codebtors/
+   */
+  saveCodebtors: async (sessionId: number, codebtors: Codebtor[]): Promise<Codebtor[]> => {
+    return apiFetch<Codebtor[]>(`/intake/sessions/${sessionId}/codebtors/`, {
+      method: 'PUT',
+      body: JSON.stringify(codebtors),
     });
   },
   getDischargeability: async (sessionId: number): Promise<unknown[]> => {
diff --git a/frontend/src/types/api.ts b/frontend/src/types/api.ts
index 99cc74a..1de11b3 100644
--- a/frontend/src/types/api.ts
+++ b/frontend/src/types/api.ts
@@ -194,6 +194,25 @@ export interface DebtInfo {
   source_document_name?: string | null;
 }

+/** A contract or lease (Schedule G), as the contracts list endpoint sends and saves it */
+export interface ExecutoryContract {
+  id?: number;
+  counterparty_name: string;
+  contract_type: 'lease' | 'contract' | 'other';
+  description: string;
+}
+
+/** A codebtor (Schedule H), as the codebtors list endpoint sends and saves it */
+export interface Codebtor {
+  id?: number;
+  name: string;
+  street_address: string;
+  city: string;
+  state: string;
+  zip_code: string;
+  relationship: 'spouse' | 'former_spouse' | 'relative' | 'friend' | 'business_partner' | 'other';
+}
+
 // ============================================================================
 // Means Test
 // ============================================================================
PATCH
```

`ExecutoryContract` and `Codebtor` move into `types/api.ts` so the steps, the wizard and Review share them. `saveContracts` and `saveCodebtors` replace the single-row create and delete calls.

- [ ] **Step 8: Make steps 6 and 7 controlled, and list them on Review**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/wizard/steps/CodebtorsStep.tsx b/frontend/src/components/wizard/steps/CodebtorsStep.tsx
index b567958..affc72b 100644
--- a/frontend/src/components/wizard/steps/CodebtorsStep.tsx
+++ b/frontend/src/components/wizard/steps/CodebtorsStep.tsx
@@ -2,22 +2,18 @@
  * CodebtorsStep - Codebtor information (Schedule H)
  *
  * Lists people who are jointly liable on debts with the debtor.
- * Typically a spouse in community property states.
+ * Typically a spouse in community property states. The wizard saves
+ * the whole list when the filer presses Continue (DIG-147).
  */

-import { useState } from 'react';
-import { useIntake } from '../../../context/IntakeContext';
-import { api } from '../../../api/client';
+import { useState, useEffect, useMemo } from 'react';
 import { Button } from '../../common';
+import type { Codebtor } from '../../../types/api';

-interface Codebtor {
-  id?: number;
-  name: string;
-  street_address: string;
-  city: string;
-  state: string;
-  zip_code: string;
-  relationship: string;
+interface CodebtorsStepProps {
+  initialData?: Codebtor[];
+  onDataChange: (data: Codebtor[]) => void;
+  onValidationChange: (isValid: boolean) => void;
 }

 const RELATIONSHIPS = [
@@ -38,26 +34,34 @@ const EMPTY_CODEBTOR: Codebtor = {
   relationship: 'other',
 };

-export function CodebtorsStep() {
-  const { session } = useIntake();
-  const [codebtors, setCodebtors] = useState<Codebtor[]>([]);
-  const [isLoading, setIsLoading] = useState(true);
-
-  const loadCodebtors = async () => {
-    if (!session) return;
-    try {
-      const data = await api.intake.codebtors(session.id);
-      setCodebtors(data as Codebtor[]);
-    } catch {
-      // ignore
-    } finally {
-      setIsLoading(false);
-    }
-  };
+export function CodebtorsStep({
+  initialData,
+  onDataChange,
+  onValidationChange,
+}: CodebtorsStepProps) {
+  const [codebtors, setCodebtors] = useState<Codebtor[]>(initialData ?? []);
+
+  // A row left blank is not saved; a row the filer started needs the person's name
+  const errors = useMemo(
+    () =>
+      codebtors.map((codebtor) =>
+        !codebtor.name.trim() &&
+        [codebtor.street_address, codebtor.city, codebtor.state, codebtor.zip_code].some((value) =>
+          value.trim()
+        )
+          ? "Please enter this person's full name"
+          : undefined
+      ),
+    [codebtors]
+  );
+  const isValid = errors.every((error) => !error);

-  useState(() => {
-    loadCodebtors();
-  });
+  // Update parent when codebtors change
+  useEffect(() => {
+    onDataChange(codebtors);
+    onValidationChange(isValid);
+    // both callbacks are useState setters in IntakeWizard — stable identities
+  }, [codebtors, isValid, onDataChange, onValidationChange]);

   const addCodebtor = () => {
     setCodebtors([...codebtors, { ...EMPTY_CODEBTOR }]);
@@ -69,33 +73,10 @@ export function CodebtorsStep() {
     setCodebtors(updated);
   };

-  const removeCodebtor = async (index: number) => {
-    const codebtor = codebtors[index];
-    if (codebtor.id && session) {
-      try {
-        await api.intake.deleteCodebtor(session.id, codebtor.id);
-      } catch {
-        // ignore
-      }
-    }
+  const removeCodebtor = (index: number) => {
     setCodebtors(codebtors.filter((_, i) => i !== index));
   };

-  const handleSave = async () => {
-    if (!session) return;
-    for (const codebtor of codebtors) {
-      if (!codebtor.name.trim()) continue;
-      if (codebtor.id) continue;
-      try {
-        await api.intake.createCodebtor(session.id, codebtor);
-      } catch {
-        // ignore
-      }
-    }
-  };
-
-  if (isLoading) return <div>Loading codebtors...</div>;
-
   return (
     <div className="codebtors-step">
       <h2 className="text-lg font-semibold mb-4">Codebtors</h2>
@@ -121,7 +102,13 @@ export function CodebtorsStep() {
                 value={codebtor.name}
                 onChange={(e) => updateCodebtor(index, 'name', e.target.value)}
                 placeholder="e.g., Jane Smith"
+                maxLength={255}
               />
+              {errors[index] && (
+                <p className="form-error" role="alert" aria-live="assertive">
+                  {errors[index]}
+                </p>
+              )}
             </div>
             <div>
               <label className="block text-sm font-medium mb-1">Relationship</label>
@@ -146,6 +133,7 @@ export function CodebtorsStep() {
                 className="w-full border rounded px-3 py-2"
                 value={codebtor.street_address}
                 onChange={(e) => updateCodebtor(index, 'street_address', e.target.value)}
+                maxLength={255}
               />
             </div>
             <div>
@@ -155,6 +143,7 @@ export function CodebtorsStep() {
                 className="w-full border rounded px-3 py-2"
                 value={codebtor.city}
                 onChange={(e) => updateCodebtor(index, 'city', e.target.value)}
+                maxLength={100}
               />
             </div>
             <div className="grid grid-cols-2 gap-2">
@@ -175,6 +164,7 @@ export function CodebtorsStep() {
                   className="w-full border rounded px-3 py-2"
                   value={codebtor.zip_code}
                   onChange={(e) => updateCodebtor(index, 'zip_code', e.target.value)}
+                  maxLength={10}
                 />
               </div>
             </div>
@@ -188,14 +178,6 @@ export function CodebtorsStep() {
       <Button variant="outline" onClick={addCodebtor} className="mt-2">
         + Add Codebtor
       </Button>
-
-      {codebtors.length > 0 && (
-        <div className="mt-4">
-          <Button variant="primary" onClick={handleSave}>
-            Save Codebtors
-          </Button>
-        </div>
-      )}
     </div>
   );
 }
diff --git a/frontend/src/components/wizard/steps/ContractsStep.tsx b/frontend/src/components/wizard/steps/ContractsStep.tsx
index 0bcfbb0..d0c0225 100644
--- a/frontend/src/components/wizard/steps/ContractsStep.tsx
+++ b/frontend/src/components/wizard/steps/ContractsStep.tsx
@@ -2,19 +2,18 @@
  * ContractsStep - Executory contracts and unexpired leases (Schedule G)
  *
  * Lists contracts/leases the debtor is party to. Each entry needs
- * counterparty name, type, and description.
+ * counterparty name, type, and description. The wizard saves the whole
+ * list when the filer presses Continue (DIG-147).
  */

-import { useState } from 'react';
-import { useIntake } from '../../../context/IntakeContext';
-import { api } from '../../../api/client';
+import { useState, useEffect, useMemo } from 'react';
 import { Button } from '../../common';
+import type { ExecutoryContract } from '../../../types/api';

-interface Contract {
-  id?: number;
-  counterparty_name: string;
-  contract_type: string;
-  description: string;
+interface ContractsStepProps {
+  initialData?: ExecutoryContract[];
+  onDataChange: (data: ExecutoryContract[]) => void;
+  onValidationChange: (isValid: boolean) => void;
 }

 const CONTRACT_TYPES = [
@@ -23,71 +22,52 @@ const CONTRACT_TYPES = [
   { value: 'other', label: 'Other' },
 ];

-const EMPTY_CONTRACT: Contract = {
+const EMPTY_CONTRACT: ExecutoryContract = {
   counterparty_name: '',
   contract_type: 'contract',
   description: '',
 };

-export function ContractsStep() {
-  const { session } = useIntake();
-  const [contracts, setContracts] = useState<Contract[]>([]);
-  const [isLoading, setIsLoading] = useState(true);
-
-  const loadContracts = async () => {
-    if (!session) return;
-    try {
-      const data = await api.intake.contracts(session.id);
-      setContracts(data as Contract[]);
-    } catch {
-      // ignore
-    } finally {
-      setIsLoading(false);
-    }
-  };
+export function ContractsStep({
+  initialData,
+  onDataChange,
+  onValidationChange,
+}: ContractsStepProps) {
+  const [contracts, setContracts] = useState<ExecutoryContract[]>(initialData ?? []);
+
+  // A row left blank is not saved; a row the filer started needs the other party's name
+  const errors = useMemo(
+    () =>
+      contracts.map((contract) =>
+        !contract.counterparty_name.trim() && contract.description.trim()
+          ? 'Please enter the name of the other party'
+          : undefined
+      ),
+    [contracts]
+  );
+  const isValid = errors.every((error) => !error);

-  // Load on mount
-  useState(() => {
-    loadContracts();
-  });
+  // Update parent when contracts change
+  useEffect(() => {
+    onDataChange(contracts);
+    onValidationChange(isValid);
+    // both callbacks are useState setters in IntakeWizard — stable identities
+  }, [contracts, isValid, onDataChange, onValidationChange]);

   const addContract = () => {
     setContracts([...contracts, { ...EMPTY_CONTRACT }]);
   };

-  const updateContract = (index: number, field: keyof Contract, value: string) => {
+  const updateContract = (index: number, field: keyof ExecutoryContract, value: string) => {
     const updated = [...contracts];
     updated[index] = { ...updated[index], [field]: value };
     setContracts(updated);
   };

-  const removeContract = async (index: number) => {
-    const contract = contracts[index];
-    if (contract.id && session) {
-      try {
-        await api.intake.deleteContract(session.id, contract.id);
-      } catch {
-        // ignore
-      }
-    }
+  const removeContract = (index: number) => {
     setContracts(contracts.filter((_, i) => i !== index));
   };

-  const handleSave = async () => {
-    if (!session) return;
-    for (const contract of contracts) {
-      if (!contract.counterparty_name.trim()) continue;
-      if (contract.id) continue; // already saved
-      try {
-        await api.intake.createContract(session.id, contract);
-      } catch {
-        // ignore
-      }
-    }
-  };
-
-  if (isLoading) return <div>Loading contracts...</div>;
-
   return (
     <div className="contracts-step">
       <h2 className="text-lg font-semibold mb-4">Contracts & Leases</h2>
@@ -113,7 +93,13 @@ export function ContractsStep() {
                 value={contract.counterparty_name}
                 onChange={(e) => updateContract(index, 'counterparty_name', e.target.value)}
                 placeholder="e.g., Landlord Inc."
+                maxLength={255}
               />
+              {errors[index] && (
+                <p className="form-error" role="alert" aria-live="assertive">
+                  {errors[index]}
+                </p>
+              )}
             </div>
             <div>
               <label className="block text-sm font-medium mb-1">Type</label>
@@ -149,14 +135,6 @@ export function ContractsStep() {
       <Button variant="outline" onClick={addContract} className="mt-2">
         + Add Contract
       </Button>
-
-      {contracts.length > 0 && (
-        <div className="mt-4">
-          <Button variant="primary" onClick={handleSave}>
-            Save Contracts
-          </Button>
-        </div>
-      )}
     </div>
   );
 }
PATCH
```

Each step now takes AssetsStep's props and reports its rows and its validity to the wizard. It no longer reads on mount, deletes on Remove, has a Save button, or swallows an error.

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/wizard/steps/ReviewStep.tsx b/frontend/src/components/wizard/steps/ReviewStep.tsx
index c531336..8d4a9fd 100644
--- a/frontend/src/components/wizard/steps/ReviewStep.tsx
+++ b/frontend/src/components/wizard/steps/ReviewStep.tsx
@@ -8,7 +8,15 @@
 import { useEffect } from 'react';
 import { UPLDisclaimer } from '../../compliance';
 import { UPL_REVIEW_DISCLAIMER } from '../../../constants/upl';
-import type { DebtorInfo, IncomeInfo, ExpenseInfo, AssetInfo, DebtInfo } from '../../../types/api';
+import type {
+  DebtorInfo,
+  IncomeInfo,
+  ExpenseInfo,
+  AssetInfo,
+  DebtInfo,
+  ExecutoryContract,
+  Codebtor,
+} from '../../../types/api';

 interface ReviewStepProps {
   debtorData: Partial<DebtorInfo>;
@@ -16,6 +24,8 @@ interface ReviewStepProps {
   expenseData: Partial<ExpenseInfo>;
   assetsData: Partial<AssetInfo>[];
   debtsData: Partial<DebtInfo>[];
+  contractsData: ExecutoryContract[];
+  codebtorsData: Codebtor[];
   onValidationChange: (isValid: boolean) => void;
 }

@@ -25,6 +35,8 @@ export function ReviewStep({
   expenseData,
   assetsData,
   debtsData,
+  contractsData,
+  codebtorsData,
   onValidationChange,
 }: ReviewStepProps) {
   // Always valid to proceed from review (unless we add specific checks)
@@ -141,6 +153,42 @@ export function ReviewStep({
         )}
       </section>

+      {/* Contracts Summary */}
+      <section className="review-section">
+        <h4 className="review-section-title">Contracts & Leases ({contractsData.length})</h4>
+        {contractsData.length === 0 ? (
+          <p className="review-empty">No contracts or leases listed.</p>
+        ) : (
+          <ul className="review-list">
+            {contractsData.map((contract, index) => (
+              <li key={contract.id || index} className="review-list-item">
+                <span>
+                  {contract.counterparty_name} ({contract.contract_type})
+                </span>
+              </li>
+            ))}
+          </ul>
+        )}
+      </section>
+
+      {/* Codebtors Summary */}
+      <section className="review-section">
+        <h4 className="review-section-title">Codebtors ({codebtorsData.length})</h4>
+        {codebtorsData.length === 0 ? (
+          <p className="review-empty">No codebtors listed.</p>
+        ) : (
+          <ul className="review-list">
+            {codebtorsData.map((codebtor, index) => (
+              <li key={codebtor.id || index} className="review-list-item">
+                <span>
+                  {codebtor.name} ({codebtor.relationship.replace('_', ' ')})
+                </span>
+              </li>
+            ))}
+          </ul>
+        )}
+      </section>
+
       <UPLDisclaimer text={UPL_REVIEW_DISCLAIMER} variant="banner" />
     </div>
   );
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
index a2bb909..93f31bf 100644
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -32,6 +32,8 @@ import type {
   ExpenseInfo,
   AssetInfo,
   DebtInfo,
+  ExecutoryContract,
+  Codebtor,
 } from '../types/api';
 import { EXPENSE_FIELDS } from '../types/api';

@@ -80,6 +82,8 @@ export function IntakeWizard() {
   const [expenseData, setExpenseData] = useState<Partial<ExpenseInfo>>({});
   const [assetsData, setAssetsData] = useState<Partial<AssetInfo>[]>([]);
   const [debtsData, setDebtsData] = useState<Partial<DebtInfo>[]>([]);
+  const [contractsData, setContractsData] = useState<ExecutoryContract[]>([]);
+  const [codebtorsData, setCodebtorsData] = useState<Codebtor[]>([]);

   // =========================================================================
   // Read the session on mount
@@ -101,25 +105,38 @@ export function IntakeWizard() {
   useEffect(() => {
     let cancelled = false;

-    const openSession = async (): Promise<IntakeSession> => {
+    // Contracts and codebtors have their own endpoints, and a new session has none yet. Both
+    // lists load before any step shows: Review lists them (DIG-166), and Continue on steps 6
+    // and 7 saves the whole list, so a list that failed to load is never saved as empty.
+    const openSession = async (): Promise<{
+      fresh: IntakeSession;
+      contracts: ExecutoryContract[];
+      codebtors: Codebtor[];
+    }> => {
       if (sessionIdToRead === null) {
         // No session in context AND no saved session — create a new one (District ID 1 = ILND)
-        return createSession(1);
+        return { fresh: await createSession(1), contracts: [], codebtors: [] };
       }
+      let fresh: IntakeSession;
       try {
-        return await loadSession(sessionIdToRead);
+        fresh = await loadSession(sessionIdToRead);
       } catch (error) {
         // A 404 means the saved session is gone or belongs to someone else (a shared
         // computer). Retrying cannot help, so start a new one, as for a new filer.
         if (error instanceof APIClientError && error.statusCode === 404) {
-          return createSession(1);
+          return { fresh: await createSession(1), contracts: [], codebtors: [] };
         }
         throw error;
       }
+      const [contracts, codebtors] = await Promise.all([
+        api.intake.contracts(fresh.id),
+        api.intake.codebtors(fresh.id),
+      ]);
+      return { fresh, contracts, codebtors };
     };

     openSession()
-      .then((fresh) => {
+      .then(({ fresh, contracts, codebtors }) => {
         if (cancelled) return;
         setCurrentStepNumber(fresh.current_step);
         if (fresh.debtor_info) setDebtorData(fresh.debtor_info);
@@ -129,6 +146,8 @@ export function IntakeWizard() {
           setAssetsData(fresh.assets.map((asset) => hydrateAmounts(asset, ASSET_AMOUNT_FIELDS)));
         if (fresh.debts)
           setDebtsData(fresh.debts.map((debt) => hydrateAmounts(debt, DEBT_AMOUNT_FIELDS)));
+        setContractsData(contracts);
+        setCodebtorsData(codebtors);
         setSessionRead('done');
       })
       .catch(() => {
@@ -153,7 +172,8 @@ export function IntakeWizard() {
   // =========================================================================

   // What saving the step on screen sends: PATCH /api/intake/sessions/{id}/, whose nested
-  // serializer creates and updates each section. null for the steps the wizard doesn't save.
+  // serializer creates and updates each section. null for Review, and for Contracts and
+  // Codebtors, whose lists save through their own endpoints (saveCurrentStepData).
   // useAutoSave compares it with the step's last saved or loaded copy, so a step that only
   // shows what the server holds (a blank row, a recomputed total) sends nothing.
   const currentStepKey = WIZARD_STEPS[currentStepNumber - 1]?.key;
@@ -235,8 +255,8 @@ export function IntakeWizard() {
       }

       setCurrentStepNumber(nextStep);
-      // Contracts (6) and Codebtors (7) are optional — pre-approve so Continue stays enabled
-      setCanProceed(nextStep === 6 || nextStep === 7);
+      // Each step reports its own validity once it shows (Contracts and Codebtors too, DIG-165)
+      setCanProceed(false);
     } catch (error) {
       console.error('Error advancing to next step:', error);
     }
@@ -282,6 +302,20 @@ export function IntakeWizard() {
   const saveCurrentStepData = async (body: Partial<IntakeSession> | null) => {
     if (!session) return;

+    // Contracts and codebtors save as whole lists, only from Continue: their step body is null,
+    // so autosave never sends them. Blank rows are left out. The saved rows come back with
+    // their ids, so the next save updates them instead of adding them again (DIG-147).
+    if (currentStepKey === 'contracts') {
+      const named = contractsData.filter((contract) => contract.counterparty_name.trim());
+      setContractsData(await api.intake.saveContracts(session.id, named));
+      return;
+    }
+    if (currentStepKey === 'codebtors') {
+      const named = codebtorsData.filter((codebtor) => codebtor.name.trim());
+      setCodebtorsData(await api.intake.saveCodebtors(session.id, named));
+      return;
+    }
+
     if (body === null) {
       console.log(`Saving data for ${currentStepKey} not yet implemented`);
       return;
@@ -342,10 +376,22 @@ export function IntakeWizard() {
         );

       case 6:
-        return <ContractsStep />;
+        return (
+          <ContractsStep
+            initialData={contractsData}
+            onDataChange={setContractsData}
+            onValidationChange={setCanProceed}
+          />
+        );

       case 7:
-        return <CodebtorsStep />;
+        return (
+          <CodebtorsStep
+            initialData={codebtorsData}
+            onDataChange={setCodebtorsData}
+            onValidationChange={setCanProceed}
+          />
+        );

       case 8:
         return (
@@ -355,6 +401,8 @@ export function IntakeWizard() {
             expenseData={expenseData}
             assetsData={assetsData}
             debtsData={debtsData}
+            contractsData={contractsData}
+            codebtorsData={codebtorsData}
             onValidationChange={setCanProceed}
           />
         );
PATCH
```

The wizard reads both lists with the session and passes them to steps 6 and 7 and to Review. On Continue, `saveCurrentStepData` sends the named rows with a `PUT` and keeps the rows that come back. Review lists "Contracts & Leases (n)" and "Codebtors (n)" (DIG-166).

- [ ] **Step 9: Run the frontend tests again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/IntakeWizard.test.tsx src/components/wizard/steps/__tests__/ReviewStep.test.tsx src/components/wizard/steps/__tests__/ContractsStep.test.tsx src/components/wizard/steps/__tests__/CodebtorsStep.test.tsx 2>&1 | tail -6
```

Expected: `35 passed`.

- [ ] **Step 10: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2a.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -3)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `1665 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  277 passed (277)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 11: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 12: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/intake/tests/test_list_saves.py \
  frontend/src/components/wizard/steps/__tests__/CodebtorsStep.test.tsx \
  frontend/src/components/wizard/steps/__tests__/ContractsStep.test.tsx \
  backend/apps/intake/serializers.py \
  backend/apps/intake/tests/test_completion.py \
  backend/apps/intake/views.py \
  frontend/src/api/client.ts \
  frontend/src/components/wizard/steps/CodebtorsStep.tsx \
  frontend/src/components/wizard/steps/ContractsStep.tsx \
  frontend/src/components/wizard/steps/ReviewStep.tsx \
  frontend/src/components/wizard/steps/__tests__/ReviewStep.test.tsx \
  frontend/src/pages/IntakeWizard.tsx \
  frontend/src/pages/__tests__/IntakeWizard.test.tsx \
  frontend/src/test/mocks/handlers.ts \
  frontend/src/types/api.ts
git commit -F - <<'MSG'
feat(intake,frontend): save contracts and codebtors with Continue, as whole lists

Steps 6 and 7 saved only on their own Save buttons. Edits to saved rows were
never sent, a second Save created every new row again, and every failure was
hidden (DIG-147).

The contracts and codebtors endpoints now take the whole list with a PUT.
Every row is checked before anything is written, so one bad row saves
nothing. Then a row carrying one of the session's ids updates in place, any
other row is created on this session, and a saved row the list left out is
deleted, through the same _save_rows_by_id the Assets and Amounts Owed steps
use. An empty list deletes every stored row, because it means the filer has
none. The save reopens a completed intake and returns the saved rows in id
order; both lists also read back in id order. The single-row POST and DELETE
stay as they were.

Continue on steps 6 and 7 saves the list the step shows, leaving out blank
rows, and keeps the ids the save returns, so the next save updates those
rows. A failed save keeps the filer on the step with the wizard's save error,
as on the other steps. The Save buttons are gone, and Remove takes effect
with that save. A row with typed details but no name asks for the name and
holds Continue. The name, street, city and ZIP boxes stop at the length each
column stores, so a long entry never meets a refusal the filer can't see or
fix. The wizard reads both lists with the session, before any
step shows, so a list that failed to load is never saved as empty.

Steps 6 and 7 report their own validity, so a filer who resumes there can
continue (DIG-165). Review lists the contracts and codebtors (DIG-166).

Forms step 2a, commit 3 (step 2 spec §5.4).
MSG
git status --short
```

### Task 5: Save the secured flag and accept personal property

_Built and verified as commit `f936dea` on `plan/forms-step2a`._

**Files:**

- Create: `backend/apps/intake/migrations/0011_assetinfo_personal_property.py`
- Create: `backend/apps/intake/migrations/0012_backfill_secured_debts.py`
- Create: `backend/apps/intake/tests/test_data_migrations.py`
- Create: `backend/apps/intake/tests/test_secured_debts_and_personal_property.py`
- Modify: `backend/apps/intake/models.py`
- Modify: `backend/apps/intake/serializers.py`
- Modify: `backend/apps/intake/tests/test_session_nested_save.py`
- Modify: `frontend/src/types/api.ts`

**Interfaces:**

- Consumes:
  - `DebtInfoSerializer` in `apps/intake/serializers.py`. `NestedDebtInfoSerializer`, which the session PATCH uses, inherits its fields.
  - `AssetInfo.ASSET_TYPE_CHOICES` in `apps/intake/models.py`, and the intake app's latest migration, `0010_add_adversary_proceedings`.
- Produces:
  - `DebtInfoSerializer.Meta.fields` gains `is_secured` and `collateral_description`, read and write, on the nested session save and on `DebtViewSet`.
  - `AssetInfo.asset_type` accepts `personal_property`, labelled "Personal Property (furniture, jewelry, collectibles)".
  - Migration `0011_assetinfo_personal_property` (an `AlterField` of the choices only) and `0012_backfill_secured_debts` (`RunPython(secure_car_loans_and_mortgages, migrations.RunPython.noop)`), the intake app's first data migration. Later intake migrations depend on `0012`.
  - `apps/intake/tests/test_data_migrations.py`, with the `migrate` fixture (`migrate(targets)` migrates the intake app there and returns the historical apps), the helpers `_session(apps)` and `_debt(apps, session, creditor_name, debt_type, **fields)`, and the targets `BEFORE_STEP_2`, `BEFORE_BACKFILL` and `BACKFILL`. Tasks 9 and 13 add their data-migration tests to this file.
  - The `AssetInfo.asset_type` union in `src/types/api.ts` names `'real_property'`, as the backend does, not `'real_estate'`.

**Decisions already made in this task:**

- `is_secured` and `collateral_description` are read and write, not write-only. The Debts step shows the collateral box, and requires it, only when the flag is set, so a returning filer needs both back. Only the session's owner can read them.
- `is_priority` and `consumer_business_classification` stay out of the serializer. §5.4 leaves priority to step 3 or 4 (OQ-3).
- Migration `0012` sets only `is_secured`, on debts whose type is `auto_loan` or `mortgage`, the two categories the Debts step marks secured. It leaves `priority_classification` (the first key of the debt ordering; no form reads it) and `collateral_description` alone, and undoing it changes nothing. So a stored scanned-bill draft typed as a car loan becomes secured but keeps the classification `unsecured`.
- A migration is not a filer write, so the backfill reopens no completed intake.
- Collateral the old API dropped can't be recovered. A returning filer with a stored car loan or mortgage now sees the collateral box as required and describes it before Continue.
- Two migrations, not one: `0011` is the choices change that `makemigrations` writes for the model, with no SQL and no data change, and `0012` is the backfill. They serve two tickets on two tables.
- The migration tests use `transactional_db`, because SQLite can't change a schema inside the test's transaction. They use the real `User` and `District` models, whose tables are the same at every intake migration, and migrate back to the leaf nodes at teardown. So every later intake migration must stay reversible, which §7.8 already requires.
- The frontend half of DIG-47 is only the type fix. The Assets step already offered and sent `personal_property`; the backend's 400 was the failure. No vitest is added, and tsc checks the type.
- The new choice's label is the Assets step's own label for it.
- The `_save_rows_by_id` docstring and the `test_session_nested_save.py` module docstring stop listing the secured flag as something the browser never receives. Root `CLAUDE.md` still lists `is_secured` there until Task 14 rewrites that gotcha.

- [ ] **Step 1: Write the API tests for the secured flag and personal property**

```python file=backend/apps/intake/tests/test_secured_debts_and_personal_property.py
"""The Debts step's secured flag and the Assets step's personal property save (DIG-26, DIG-47).

Business intent: a car loan or a mortgage is a secured claim (Schedule D) with the property
that secures it, so the flag and the collateral the Debts step sends must be stored, and read
back so a returning filer sees them. Household goods are on nearly every Schedule A/B, so
choosing "Personal Property" on the Assets step must save the step, not refuse it.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import AssetInfo, DebtInfo, IntakeSession
from apps.users.models import User


@pytest.fixture
def filer(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=user, district=district)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session


def _session_url(session):
    return f"/api/intake/sessions/{session.pk}/"


def test_car_loan_from_the_debts_step_saves_as_secured_with_its_collateral(filer):
    client, session = filer

    # The row as the Debts step sends it after the filer picks "Car or vehicle loan".
    response = client.patch(
        _session_url(session),
        {
            "debts": [
                {
                    "creditor_name": "Ally Auto",
                    "debt_type": "auto_loan",
                    "amount_owed": 8500,
                    "monthly_payment": 350,
                    "is_secured": True,
                    "priority_classification": "secured",
                    "collateral_description": "2019 Toyota Camry",
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    saved = DebtInfo.objects.get(session=session)
    assert saved.is_secured is True
    assert saved.collateral_description == "2019 Toyota Camry"
    [row] = client.get(_session_url(session)).data["debts"]
    assert row["is_secured"] is True
    assert row["collateral_description"] == "2019 Toyota Camry"


def test_debt_the_filer_changes_to_unsecured_saves_as_unsecured(filer):
    client, session = filer
    loan = DebtInfo.objects.create(
        session=session,
        creditor_name="Ally Auto",
        debt_type="auto_loan",
        priority_classification="secured",
        amount_owed=Decimal("8500.00"),
        is_secured=True,
        collateral_description="2019 Toyota Camry",
    )

    # The filer meant a credit card: the Debts step sends the new category's flag.
    response = client.patch(
        _session_url(session),
        {
            "debts": [
                {
                    "id": loan.pk,
                    "creditor_name": "Ally Card",
                    "debt_type": "credit_card",
                    "amount_owed": 8500,
                    "is_secured": False,
                    "priority_classification": "unsecured",
                    "collateral_description": "",
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    loan.refresh_from_db()
    assert loan.is_secured is False
    assert loan.collateral_description == ""
    [row] = client.get(_session_url(session)).data["debts"]
    assert row["is_secured"] is False


def test_filer_can_save_personal_property_on_the_assets_step(filer):
    client, session = filer

    response = client.patch(
        _session_url(session),
        {
            "assets": [
                {
                    "asset_type": "personal_property",
                    "description": "Furniture and household goods",
                    "current_value": 1200,
                },
                {"asset_type": "bank_account", "description": "Checking", "current_value": 300},
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    saved = {a.description: a.asset_type for a in AssetInfo.objects.filter(session=session)}
    assert saved == {
        "Furniture and household goods": "personal_property",
        "Checking": "bank_account",
    }
    received = client.get(_session_url(session)).data["assets"]
    assert {a["asset_type"] for a in received} == {"personal_property", "bank_account"}
```

The first test saves a car loan the way the Debts step sends it and expects the flag and the collateral stored and read back. The second checks the other side: a debt the filer changes to unsecured saves as unsecured. The third saves a personal-property asset beside a bank account, so the whole Assets step saves.

- [ ] **Step 2: Run the API tests and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_secured_debts_and_personal_property.py -q -p no:cacheprovider 2>&1 | tail -4
```

Expected: FAIL — `3 failed`. The serializer drops the flag, so the car loan stores False and the debt changed to unsecured keeps its stored True. The Assets save is a 400, because personal_property is not a valid choice.

- [ ] **Step 3: Accept the flag and the new asset type**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/models.py b/backend/apps/intake/models.py
index bb5f533..16d3efd 100644
--- a/backend/apps/intake/models.py
+++ b/backend/apps/intake/models.py
@@ -243,6 +243,7 @@ class AssetInfo(models.Model):
         ("vehicle", "Vehicle"),
         ("bank_account", "Bank Account"),
         ("retirement_account", "Retirement Account (401k, IRA)"),
+        ("personal_property", "Personal Property (furniture, jewelry, collectibles)"),
         ("other", "Other Asset"),
     ]

diff --git a/backend/apps/intake/serializers.py b/backend/apps/intake/serializers.py
index ac5284e..b2c5209 100644
--- a/backend/apps/intake/serializers.py
+++ b/backend/apps/intake/serializers.py
@@ -211,6 +211,8 @@ class DebtInfoSerializer(serializers.ModelSerializer):
             "amount_owed",
             "monthly_payment",
             "is_in_collections",
+            "is_secured",
+            "collateral_description",
             "notes",
             "created_at",
             "updated_at",
@@ -248,8 +250,8 @@ def _save_rows_by_id(session, model, rows) -> None:
     """Save a session's nested assets or debts, or its contracts or codebtors list, by id.

     A row whose id is one of this session's rows updates only the fields it sent, so
-    what the browser never received (account numbers, the scanned-bill link, the
-    secured flag) survives. Any other row is created on this session, so a client-sent
+    what the browser never received (account numbers, the scanned-bill link)
+    survives. Any other row is created on this session, so a client-sent
     ``session`` or another user's id never touches another session. Stored rows the
     payload left out are deleted.
     """
diff --git a/backend/apps/intake/tests/test_session_nested_save.py b/backend/apps/intake/tests/test_session_nested_save.py
index babc69a..a6b0123 100644
--- a/backend/apps/intake/tests/test_session_nested_save.py
+++ b/backend/apps/intake/tests/test_session_nested_save.py
@@ -1,9 +1,9 @@
 """Saving the Assets and Amounts Owed steps updates rows in place (DIG-21, DIG-37).

 Business intent: the wizard sends back the rows it loaded. A row must keep what the
-browser never receives (the encrypted account number, the link to the scanned bill,
-the secured flag), a corrected amount must save instead of crashing, and a nested row
-can only ever change the filer's own session.
+browser never receives (the encrypted account number, the link to the scanned bill),
+a corrected amount must save instead of crashing, and a nested row can only ever
+change the filer's own session.
 """

 from decimal import Decimal
PATCH
```

```python file=backend/apps/intake/migrations/0011_assetinfo_personal_property.py
# Generated by Django 5.0.14 on 2026-10-13 03:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("intake", "0010_add_adversary_proceedings"),
    ]

    operations = [
        migrations.AlterField(
            model_name="assetinfo",
            name="asset_type",
            field=models.CharField(
                choices=[
                    ("real_property", "Real Estate/Home"),
                    ("vehicle", "Vehicle"),
                    ("bank_account", "Bank Account"),
                    ("retirement_account", "Retirement Account (401k, IRA)"),
                    ("personal_property", "Personal Property (furniture, jewelry, collectibles)"),
                    ("other", "Other Asset"),
                ],
                max_length=30,
            ),
        ),
    ]
```

`DebtInfoSerializer` now accepts and returns `is_secured` and `collateral_description` (DIG-26), and `personal_property` joins the asset types before `other`, where the Assets step lists it (DIG-47). `0011` is the migration `makemigrations` writes for the new choice; use this file as given, so its header matches.

- [ ] **Step 4: Run the API tests again**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_secured_debts_and_personal_property.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `3 passed`.

- [ ] **Step 5: Write the data-migration tests**

```python file=backend/apps/intake/tests/test_data_migrations.py
"""The intake app's data migrations, run by Django's migration executor on prepared rows.

Business intent: a data migration rewrites what filers already saved. It must change exactly
the rows it names and nothing else, and undoing it must leave saved data as it is (spec §7.8).
"""

from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.districts.models import District
from apps.users.models import User

BEFORE_STEP_2 = [("intake", "0010_add_adversary_proceedings")]
BEFORE_BACKFILL = [("intake", "0011_assetinfo_personal_property")]
BACKFILL = [("intake", "0012_backfill_secured_debts")]


@pytest.fixture
def migrate(transactional_db):
    """Migrate the intake app to a migration and return the models as they were there.

    SQLite can't change a schema inside the test's transaction, hence transactional_db.
    Afterwards the database returns to the latest migrations for the tests that follow.
    """
    executor = MigrationExecutor(connection)

    def to(targets):
        executor.loader.build_graph()
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    yield to
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())


def _session(apps):
    # The user and district tables are the same at every intake migration.
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    IntakeSession = apps.get_model("intake", "IntakeSession")
    return IntakeSession.objects.create(user_id=user.pk, district_id=district.pk)


def _debt(apps, session, creditor_name, debt_type, **fields):
    DebtInfo = apps.get_model("intake", "DebtInfo")
    return DebtInfo.objects.create(
        session_id=session.pk,
        creditor_name=creditor_name,
        debt_type=debt_type,
        amount_owed=Decimal("1000.00"),
        **fields,
    )


def test_stored_car_loans_and_mortgages_become_secured_and_no_other_debt_changes(migrate):
    apps = migrate(BEFORE_BACKFILL)
    session = _session(apps)
    _debt(apps, session, "Ally Auto", "auto_loan", collateral_description="2019 Toyota Camry")
    _debt(apps, session, "Chase Home Lending", "mortgage")
    _debt(apps, session, "Visa", "credit_card")
    _debt(
        apps,
        session,
        "Couch Store",
        "personal_loan",
        is_secured=True,
        collateral_description="Living room set",
    )

    apps = migrate(BACKFILL)

    DebtInfo = apps.get_model("intake", "DebtInfo")
    stored = {
        d.creditor_name: (d.is_secured, d.collateral_description) for d in DebtInfo.objects.all()
    }
    assert stored == {
        "Ally Auto": (True, "2019 Toyota Camry"),
        "Chase Home Lending": (True, ""),
        "Visa": (False, ""),
        "Couch Store": (True, "Living room set"),
    }


def test_undoing_the_secured_backfill_leaves_debts_as_they_are(migrate):
    apps = migrate(BEFORE_BACKFILL)
    _debt(apps, _session(apps), "Ally Auto", "auto_loan")
    migrate(BACKFILL)

    apps = migrate(BEFORE_BACKFILL)

    DebtInfo = apps.get_model("intake", "DebtInfo")
    assert DebtInfo.objects.get(creditor_name="Ally Auto").is_secured is True


def test_stored_other_assets_stay_other_once_personal_property_exists(migrate):
    apps = migrate(BEFORE_STEP_2)
    AssetInfo = apps.get_model("intake", "AssetInfo")
    AssetInfo.objects.create(
        session_id=_session(apps).pk,
        asset_type="other",
        description="Living room furniture",
        current_value=Decimal("900.00"),
    )

    apps = migrate(BACKFILL)

    AssetInfo = apps.get_model("intake", "AssetInfo")
    assert AssetInfo.objects.get(description="Living room furniture").asset_type == "other"
```

The tests run Django's `MigrationExecutor` on prepared rows (§7.8). Going forward to `0012`, the stored car loan and mortgage become secured, while a credit card stays unsecured and an already secured personal loan keeps its collateral. Going back from `0012` leaves the flag as it is. A stored "Other" asset stays "Other" once `personal_property` exists.

- [ ] **Step 6: Run the data-migration tests and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_data_migrations.py -q -p no:cacheprovider 2>&1 | tail -6
```

Expected: FAIL — `3 failed`, each on `Node ('intake', '0012_backfill_secured_debts') not a valid node` (the output shows the last one): the backfill doesn't exist yet. The third test guards that stored "Other" assets stay "Other", so it fails here only because it migrates through 0012.

- [ ] **Step 7: Mark stored car loans and mortgages secured**

```python file=backend/apps/intake/migrations/0012_backfill_secured_debts.py
"""Stored car loans and mortgages become secured, the rule the Debts step applies (DIG-26).

The API dropped the step's secured flag until now, so every debt the wizard saved is unsecured.
"""

from django.db import migrations


def secure_car_loans_and_mortgages(apps, schema_editor):
    DebtInfo = apps.get_model("intake", "DebtInfo")
    DebtInfo.objects.filter(debt_type__in=["auto_loan", "mortgage"]).update(is_secured=True)


class Migration(migrations.Migration):

    dependencies = [
        ("intake", "0011_assetinfo_personal_property"),
    ]

    operations = [
        migrations.RunPython(secure_car_loans_and_mortgages, migrations.RunPython.noop),
    ]
```

`secure_car_loans_and_mortgages` marks every stored `auto_loan` and `mortgage` debt secured through the historical model, the rule the Debts step applies when the filer picks the category, and going back does nothing (DIG-26, §7.8).

- [ ] **Step 8: Run the data-migration tests again**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_data_migrations.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `3 passed`.

- [ ] **Step 9: Name the real-property asset type as the backend does**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/types/api.ts b/frontend/src/types/api.ts
index 1de11b3..385a973 100644
--- a/frontend/src/types/api.ts
+++ b/frontend/src/types/api.ts
@@ -149,7 +149,7 @@ export interface AssetInfo {
   id: number;
   session: number;
   asset_type:
-    | 'real_estate'
+    | 'real_property'
     | 'vehicle'
     | 'bank_account'
     | 'retirement_account'
PATCH
```

Nothing compares against `'real_estate'`, and the Assets step already sends `'real_property'`, so this changes only what tsc accepts.

- [ ] **Step 10: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2a.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -3)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `1671 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  277 passed (277)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 11: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 12: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/intake/migrations/0011_assetinfo_personal_property.py \
  backend/apps/intake/migrations/0012_backfill_secured_debts.py \
  backend/apps/intake/tests/test_data_migrations.py \
  backend/apps/intake/tests/test_secured_debts_and_personal_property.py \
  backend/apps/intake/models.py \
  backend/apps/intake/serializers.py \
  backend/apps/intake/tests/test_session_nested_save.py \
  frontend/src/types/api.ts
git commit -F - <<'MSG'
fix(intake,frontend): save the secured flag and accept personal property

The Debts step sends is_secured and collateral_description when the filer
picks a car loan or a mortgage, but DebtInfoSerializer left both out, so DRF
dropped them: every debt saved through the wizard was unsecured, Form 106Sum's
secured total missed it, and a returning filer never saw the collateral
(DIG-26). The serializer now accepts and returns both.

Migration 0012, the intake app's first data migration, marks stored car loans
and mortgages secured, the rule the Debts step applies. Other debts are left
as they are, and undoing it changes nothing. Collateral the API dropped can't
be recovered, so a returning filer with such a loan is asked to describe it.

The Assets step offers "Personal Property", but personal_property was not an
asset type, so choosing it refused the whole step's save (DIG-47). It is now
a valid type (0011, choices only); stored "Other" assets stay as they are.
The frontend AssetInfo type names real_property, as the backend does, not
real_estate.

Both migrations are tested with Django's MigrationExecutor on prepared rows.
MSG
git status --short
```

### Task 6: Save the phone number, and save a cleared expense as $0

_Built and verified as commit `151cfd4` on `plan/forms-step2a`._

**Files:**

- Modify: `frontend/e2e/pages/wizard.page.ts`
- Modify: `frontend/src/components/wizard/steps/DebtorInfoStep.tsx`
- Modify: `frontend/src/pages/IntakeWizard.tsx`
- Modify: `frontend/src/pages/__tests__/IntakeWizard.test.tsx`
- Modify: `frontend/src/test/fixtures/session.ts`
- Modify: `frontend/src/types/api.ts`

**Interfaces:**

- Consumes:
  - `DebtorInfoSerializer`'s `phone` field (`backend/apps/intake/serializers.py`, unchanged). DRF drops any other name without an error.
  - Task 3's `currentStepBody` in `IntakeWizard.tsx`, the PATCH body built for each step. `useAutoSave` compares its `JSON.stringify` output with the last saved or loaded copy and skips an unchanged save; Continue always saves through `saveNow`.
  - `EXPENSE_FIELDS` in `frontend/src/types/api.ts`, the 13 `ExpenseInfo` amount names, already imported by `IntakeWizard.tsx`.
  - The helpers in `IntakeWizard.test.tsx`: `sessionAtStep1`, `renderWizard()` and `fillDebtorInfoFields()`, which types the phone `312-555-1234`.
- Produces:
  - `DebtorInfo.phone: string` replaces `phone_number` in `frontend/src/types/api.ts` and in `createMockDebtorInfo` (`frontend/src/test/fixtures/session.ts`). The Debtor step's box is `name="phone"`, so its DOM id becomes `field-phone`, and `WizardPage.fillDebtorInfo` fills `input[name="phone"]`.
  - The Expenses step's save body is `{expense_info: {...}}` holding exactly the 13 `EXPENSE_FIELDS` amounts in that order, each `expenseData[field] ?? 0`. It never carries `total_monthly_expenses`, `data_source`, `created_at` or `updated_at`.
  - Tests in `IntakeWizard.test.tsx`: `IntakeWizard phone number > shows a returning filer the phone number they saved`, `IntakeWizard phone number > saves the phone number under the name the server stores`, and `IntakeWizard cleared expense > saves a cleared expense box as $0, so the old amount does not stay on the server`.

**Decisions already made in this task:**

- DIG-55 is fixed in the wizard's save body (`currentStepBody`), not in `ExpenseInfoStep`. The step keeps a blank box blank and a typed 0 as 0; storing 0 in the step would put "0" in a box the filer just cleared to retype. After a reload a cleared box shows the stored $0 as "0", as a never-touched box already does since DIG-153.
- The body carries the 13 amounts alone, in `EXPENSE_FIELDS` order. `useAutoSave` compares `JSON.stringify` output, so a fixed key order keeps a no-op from reading as an edit, which would reopen a completed intake. The echoed `data_source`, `created_at` and `updated_at` go: the timestamps are read-only, and the server keeps `data_source` as stored.
- A new filer's blank boxes are sent as 0 too. §5.2 names the 13 expense amounts as the one place where blank means $0, and the server already stores $0 for them (DIG-153).
- The tests are wizard-level, because only a test that reads the request body proves the name and the 0 that are sent. No backend test is added: the serializer already says `phone`, and Task 8's read-back compares Form 101's phone through the nested save.
- The cleared-expense test does not assert that `total_monthly_expenses` is absent. Task 3's step-back test already fails if an unchanged step sends a save.
- Two comments now describe a body the wizard no longer sends: "Every box left blank arrives as {}" above the `ExpenseInfo` upsert in `IntakeSessionSerializer.update` (`backend/apps/intake/serializers.py`), and "the Expenses step sends no amounts" in `test_filer_who_leaves_every_expense_blank_can_complete` (`backend/apps/intake/tests/test_completion.py`). Task 14 rewords them; leave them here.
- The joint-filing spouse boxes (`co_debtor_*`) are also dropped by the serializer. Joint filing is out (DIG-177), so they stay as they are.

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/IntakeWizard.test.tsx b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
index 23a6659..8f8c654 100644
--- a/frontend/src/pages/__tests__/IntakeWizard.test.tsx
+++ b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
@@ -877,6 +877,130 @@ describe('IntakeWizard expense hydration', { timeout: 15_000 }, () => {
   });
 });

+// ===========================================================================
+// Phone number (DIG-120)
+// ===========================================================================
+
+// The server stores the phone as `phone`, and DRF drops any other name without an error, so a
+// number sent under another name never reached Form 101 and a returning filer had to retype it.
+describe('IntakeWizard phone number', { timeout: 15_000 }, () => {
+  let patchBodies: Record<string, unknown>[];
+
+  beforeEach(() => {
+    patchBodies = [];
+    server.use(
+      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
+        patchBodies.push((await request.json()) as Record<string, unknown>);
+        return HttpResponse.json(sessionAtStep1);
+      }),
+      http.post(
+        'http://localhost:8000/api/audit/logs/',
+        () => new HttpResponse(null, { status: 201 })
+      )
+    );
+  });
+
+  it('shows a returning filer the phone number they saved', async () => {
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+        HttpResponse.json({
+          ...sessionAtStep1,
+          debtor_info: { first_name: 'Jane', last_name: 'Doe', phone: '312-555-0188' },
+        })
+      )
+    );
+
+    renderWizard();
+    await screen.findByRole('heading', { name: /your information/i, level: 2 });
+
+    expect(screen.getByRole('textbox', { name: /phone number/i })).toHaveValue('312-555-0188');
+  });
+
+  it('saves the phone number under the name the server stores', async () => {
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+        HttpResponse.json(sessionAtStep1)
+      )
+    );
+
+    renderWizard();
+    await screen.findByRole('heading', { name: /your information/i, level: 2 });
+    await fillDebtorInfoFields();
+    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
+    await screen.findByText('DocumentUploadPage');
+
+    const debtorInfo = patchBodies[patchBodies.length - 1].debtor_info as Record<string, unknown>;
+    expect(debtorInfo.phone).toBe('312-555-1234');
+    expect(debtorInfo).not.toHaveProperty('phone_number');
+  });
+});
+
+// ===========================================================================
+// A cleared expense (DIG-55)
+// ===========================================================================
+
+describe('IntakeWizard cleared expense', { timeout: 15_000 }, () => {
+  it('saves a cleared expense box as $0, so the old amount does not stay on the server', async () => {
+    const savedSession = {
+      ...sessionAtStep1,
+      current_step: 3,
+      expense_info: {
+        data_source: 'manual',
+        rent_or_mortgage: '1100.00',
+        utilities: '180.00',
+        home_maintenance: '0.00',
+        vehicle_payment: '0.00',
+        vehicle_insurance: '85.00',
+        vehicle_maintenance: '40.00',
+        food_and_groceries: '450.00',
+        clothing: '60.00',
+        medical_expenses: '75.00',
+        childcare: '400.00',
+        child_support_paid: '0.00',
+        insurance_not_deducted: '120.00',
+        other_expenses: '50.00',
+        total_monthly_expenses: 2560.0,
+        created_at: '2026-10-01T10:00:00Z',
+        updated_at: '2026-10-01T10:00:00Z',
+      },
+    };
+    const patchBodies: Record<string, unknown>[] = [];
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+        HttpResponse.json(savedSession)
+      ),
+      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
+        patchBodies.push((await request.json()) as Record<string, unknown>);
+        return HttpResponse.json(savedSession);
+      }),
+      http.post('http://localhost:8000/api/intake/sessions/:id/update_step/', () =>
+        HttpResponse.json({
+          session: { ...savedSession, current_step: 4 },
+          message: 'Step updated.',
+        })
+      ),
+      http.post(
+        'http://localhost:8000/api/audit/logs/',
+        () => new HttpResponse(null, { status: 201 })
+      )
+    );
+
+    renderWizard();
+    await screen.findByRole('heading', { name: /expenses/i, level: 2 });
+    fireEvent.change(screen.getByRole('spinbutton', { name: /rent or mortgage payment/i }), {
+      target: { value: '' },
+    });
+    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
+    await screen.findByRole('heading', { name: /assets/i, level: 2 });
+
+    const expenseInfo = patchBodies[patchBodies.length - 1].expense_info as Record<string, unknown>;
+    expect(expenseInfo.rent_or_mortgage).toBe(0);
+    // The boxes the filer left alone keep their saved amounts
+    expect(expenseInfo.utilities).toBe(180);
+    expect(expenseInfo.food_and_groceries).toBe(450);
+  });
+});
+
 // ===========================================================================
 // Contracts and codebtors (DIG-147, DIG-165, DIG-166)
 // ===========================================================================
PATCH
```

The two phone tests read a saved `phone` back into the Phone Number box, and require Continue on step 1 to send `debtor_info.phone` with no `phone_number` key. The expense test loads a returning filer at step 3 whose amounts arrive as decimal strings, clears the rent box, presses Continue, and requires `rent_or_mortgage` to be 0 while the untouched `utilities` and `food_and_groceries` keep 180 and 450.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/IntakeWizard.test.tsx -t 'IntakeWizard (phone number|cleared expense)' 2>&1 | tail -64
```

Expected: FAIL — `3 failed`. The read test finds an empty box, the send test reads `expected undefined to be '312-555-1234'`, and the expense test reads `expected undefined to be +0`, because a cleared box is undefined and JSON leaves it out of the request.

- [ ] **Step 3: Read and send the phone number as phone, end to end**

```bash
git apply <<'PATCH'
diff --git a/frontend/e2e/pages/wizard.page.ts b/frontend/e2e/pages/wizard.page.ts
index 8cc633a..a0559f8 100644
--- a/frontend/e2e/pages/wizard.page.ts
+++ b/frontend/e2e/pages/wizard.page.ts
@@ -105,7 +105,7 @@ export class WizardPage {
     // authenticated user. The persona registered with data.email, so the field
     // already holds it — assert instead of fill (fill() times out on readOnly).
     await expect(this.page.locator('input[name="email"]')).toHaveValue(data.email);
-    await fill('phone_number', data.phone);
+    await fill('phone', data.phone);

     // Household & filing info (required since the joint-filing feature)
     await fill('household_size', String(data.household_size));
diff --git a/frontend/src/components/wizard/steps/DebtorInfoStep.tsx b/frontend/src/components/wizard/steps/DebtorInfoStep.tsx
index 751270a..02d845f 100644
--- a/frontend/src/components/wizard/steps/DebtorInfoStep.tsx
+++ b/frontend/src/components/wizard/steps/DebtorInfoStep.tsx
@@ -118,10 +118,10 @@ export function DebtorInfoStep({
       newErrors.email = 'Please enter a valid email address';
     }

-    if (!formData.phone_number?.trim()) {
-      newErrors.phone_number = 'Please enter your phone number';
-    } else if (!/^\d{3}-?\d{3}-?\d{4}$/.test(formData.phone_number)) {
-      newErrors.phone_number = 'Please enter a valid phone number (XXX-XXX-XXXX)';
+    if (!formData.phone?.trim()) {
+      newErrors.phone = 'Please enter your phone number';
+    } else if (!/^\d{3}-?\d{3}-?\d{4}$/.test(formData.phone)) {
+      newErrors.phone = 'Please enter a valid phone number (XXX-XXX-XXXX)';
     }

     if (!formData.household_size || formData.household_size < 1) {
@@ -300,13 +300,13 @@ export function DebtorInfoStep({

           <FormField
             label="Phone Number"
-            name="phone_number"
+            name="phone"
             type="tel"
             inputMode="numeric"
             maxLength={12}
-            value={formData.phone_number || ''}
-            onChange={(e) => handleChange('phone_number', formatPhone(e.target.value))}
-            error={errors.phone_number}
+            value={formData.phone || ''}
+            onChange={(e) => handleChange('phone', formatPhone(e.target.value))}
+            error={errors.phone}
             required
             autoComplete="tel"
             placeholder="XXX-XXX-XXXX"
diff --git a/frontend/src/test/fixtures/session.ts b/frontend/src/test/fixtures/session.ts
index e535975..67e2261 100644
--- a/frontend/src/test/fixtures/session.ts
+++ b/frontend/src/test/fixtures/session.ts
@@ -38,7 +38,7 @@ export const createMockDebtorInfo = (overrides?: Partial<DebtorInfo>): DebtorInf
   city: 'Chicago',
   state: 'IL',
   zip_code: '60601',
-  phone_number: '312-555-0100',
+  phone: '312-555-0100',
   email: 'jane@example.com',
   household_size: 1,
   filing_type: 'individual',
diff --git a/frontend/src/types/api.ts b/frontend/src/types/api.ts
index 385a973..0fbe8e7 100644
--- a/frontend/src/types/api.ts
+++ b/frontend/src/types/api.ts
@@ -58,7 +58,7 @@ export interface DebtorInfo {
   city: string;
   state: string;
   zip_code: string;
-  phone_number: string;
+  phone: string;
   email: string;

   // Household information
PATCH
```

DIG-120: the step's validation key, error key, box name, value and change handler all use `phone`, the serializer's name, so the number a filer types is stored and a returning filer sees it. The type, the vitest fixture and the journeys' page object move with it, as §5.4 requires: the fixture is in `tsconfig.app.json`, so tsc fails without the move, and the page object's `fill` targets `input[name="…"]`, so the old name would time out all 7 journeys.

- [ ] **Step 4: Send every expense amount, a blank box as 0**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
index 93f31bf..27c3904 100644
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -191,10 +191,12 @@ export function IntakeWizard() {
         } as Partial<IntakeSession>;

       case 'expense_info': {
-        // The total is read-only on the server. The step adds it up in floating point, so
-        // it can differ from the server's decimal sum in the last digit.
-        const expenses = { ...expenseData };
-        delete expenses.total_monthly_expenses;
+        // The 13 amounts alone. The total is read-only on the server: the step adds it up in
+        // floating point, so it can differ from the server's decimal sum in the last digit. A
+        // blank box is sent as 0, the column's default; left out, a box the filer cleared would
+        // keep its old amount on the server (DIG-55).
+        const expenses: Partial<ExpenseInfo> = {};
+        for (const field of EXPENSE_FIELDS) expenses[field] = expenseData[field] ?? 0;
         return { expense_info: expenses } as Partial<IntakeSession>;
       }

PATCH
```

DIG-55: the server's `update_or_create(defaults=…)` updates only the amounts it receives, so a cleared box left out of the request kept its old amount, and the means test and the forms kept counting it. The body now names all 13 amounts every time.

- [ ] **Step 5: Run the tests again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/IntakeWizard.test.tsx -t 'IntakeWizard (phone number|cleared expense)' 2>&1 | tail -64
```

Expected: `3 passed`.

- [ ] **Step 6: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2a.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -3)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `1671 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  280 passed (280)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 7: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 8: Commit**

```bash
set -eo pipefail
git add \
  frontend/e2e/pages/wizard.page.ts \
  frontend/src/components/wizard/steps/DebtorInfoStep.tsx \
  frontend/src/pages/IntakeWizard.tsx \
  frontend/src/pages/__tests__/IntakeWizard.test.tsx \
  frontend/src/test/fixtures/session.ts \
  frontend/src/types/api.ts
git commit -F - <<'MSG'
fix(frontend): save the phone number, and save a cleared expense as $0

The Debtor step held the phone number as phone_number, but the server stores
it as phone, and DRF drops a name it doesn't know without an error. So the
number a filer typed was never saved, Form 101 printed no phone, and a
returning filer found the box empty and had to type it again, only for it to
be dropped again (DIG-120). The step now reads and sends phone, the
serializer's name, end to end. The DebtorInfo type, the vitest session
fixture and the E2E page object use the same name.

Clearing an expense box left the field undefined, and JSON leaves an
undefined field out of the request. The server updates only the fields it
receives, so the old amount stayed stored, and the means test and the forms
kept counting it (DIG-55). The Expenses step's save now always sends all 13
amounts, with a blank box as 0, the columns' default. The box itself stays
blank until the filer types. The save sends nothing else: the read-only
total and the echoed data_source and timestamps are left out, and the server
keeps data_source as stored.

Forms step 2a, commit 3 (step 2 spec §5.4).
MSG
git status --short
```

### Task 7: Take waiver filers through SOFA, and name the box a half-filled SOFA row needs

_Built and verified as commit `4c17bbe` on `plan/forms-step2a`._

**Files:**

- Modify: `frontend/e2e/journeys/deshawn-assets.spec.ts`
- Modify: `frontend/e2e/journeys/maria-happy-path.spec.ts`
- Modify: `frontend/e2e/journeys/sarah-simplest.spec.ts`
- Modify: `frontend/e2e/pages/fee-waiver.page.ts`
- Modify: `frontend/src/pages/FeeWaiverPage.tsx`
- Modify: `frontend/src/pages/SOFAStep.tsx`
- Modify: `frontend/src/pages/__tests__/FeeWaiverPage.test.tsx`
- Modify: `frontend/src/pages/__tests__/SOFAStep.test.tsx`

**Interfaces:**

- Consumes:
  - `SOFAPage` (`frontend/e2e/pages/sofa.page.ts`): `waitForLoad()`, and `skipForNow()`, which waits for `/forms`.
  - `sofaReportAPI.patch(sessionId, data: Partial<SOFAReport>)` (`frontend/src/api/client.ts`). `SOFAReportSerializer.update` replaces a section's stored rows when its key (`prior_income`, `creditor_payments`) is in the body, and leaves them alone when it is absent.
  - `FormField`'s `error` prop (`frontend/src/components/common/FormField.tsx`), which shows the message with `role="alert"` and sets `aria-invalid`.
  - The server's row rules, which the page now mirrors: a prior-income row needs `year` (a `PositiveIntegerField`), `source` (`CharField(255)`) and `gross_amount`; a creditor payment needs `creditor_name` (`CharField(255)`) and `total_paid`, and `dates_of_payments` may be blank (up to 255).
  - `IntakeWizard.handleComplete`, unchanged: it sends a waiver filer to `/fee-waiver` and everyone else to `/sofa`.
- Produces:
  - `FeeWaiverPage`: both exits, the submit and the off-ramp button, call `navigate('/sofa')`. The off-ramp button reads "Continue".
  - `FeeWaiverPage.submit(householdSize, monthlyIncome, monthlyExpenses)` in `frontend/e2e/pages/fee-waiver.page.ts` waits for `**/sofa`. Task 13's rewrite of the page object keeps that wait.
  - In `SOFAStep.tsx`, module-private: `incomeRowStarted(row)`, `paymentRowStarted(row)` and `unfinishedBoxes(report)`, which maps each empty required box of a started row in a section switched on (`prior-income-year-<idx>`, `prior-income-source-<idx>`, `prior-income-amount-<idx>`, `creditor-name-<idx>`, `creditor-paid-<idx>`) to its message.
  - The SOFA save body: the report's flags, plus `prior_income` only when `has_prior_income` is true and `creditor_payments` only when `has_creditor_payments` is true, each without its blank rows.
  - Maria's, DeShawn's and Sarah's journeys call `sofa.waitForLoad()` and `sofa.skipForNow()` between the fee-waiver submit and the dashboard.
  - Tests: in `FeeWaiverPage.test.tsx`, `continues to the financial history questions (SOFA), not the forms, once the application is sent` (was `navigates to /forms on successful submission`) and `shows an off-ramp instead of the form when the filer is fee-waiver ineligible, and it leads on to SOFA`. In `SOFAStep.test.tsx`, `describe('SOFAStep unfinished rows (DIG-148)')` with `names the income row and the boxes to finish, and saves nothing until they are filled`, `asks for the Source of an income row that has only an amount, and saves nothing until it is filled`, `names the creditor row and the boxes to finish, counting a row with only its dates as started`, `leaves a blank row out of the save instead of asking the filer to finish it`, `saves without the rows of a section the filer switched off, even a half-filled one`, `saves without the creditor rows the filer switched off, even a half-filled one` and `stops a text box at the 255 characters the server stores`.

**Decisions already made in this task:**

- Both fee-waiver exits go to `/sofa`, because DIG-149 names both. The off-ramp's words change with them, since a button reading "Continue to my forms" that opens SOFA would be false. Its sentence becomes "That's okay — you can continue to your financial history and then your forms." and its button "Continue".
- The three waiver journeys pass through SOFA and skip it with "Skip for now", as James's journey does. §5.4 and §7.9 ask only that they go through the page; the sofa journey covers the save path, and Task 8's read-back sends Maria's SOFA rows through the API.
- Rows are checked on the page before the save, not mapped from the server's 400. That is DIG-148's first fix direction, and the page knows its own row numbers and box labels.
- What starts a row, and what it then needs:
  - An income row starts once it has a source or an amount; the year the page fills in never starts one. A started income row needs a year, a source and a gross amount. The year is required because a cleared year is sent as 0, which the server accepts and Form 107 would print.
  - A creditor row starts once it has a name, an amount or dates. A row with only its dates used to be dropped silently. A started creditor row needs a name and an amount; the dates stay optional.
- A section switched off sends no row key, so the server keeps its stored rows. They don't print: every `sofa.prior_income[]` binding in `form_107.json` (21) carries `conditional_on: has_prior_income`, every `sofa.creditor_payments[]` binding (18) carries `has_creditor_payments`, and `backend/apps/forms/services/fill_resolver.py` adds a repeat-group field only when `_section_applies` holds. Sending `[]` would delete stored rows on an accidental untick.
- The messages appear only after a save attempt, then update live and go as each box is filled, so nothing is flagged while the filer is still typing a row. `showUnfinished` is not reset after that; this is accepted.
- The copy is new; these are the sentences this plan gives. Each box's message is "Please fill in the {box} for {row}.", where {box} is the box's own label (Year, Source, Gross Amount, Creditor Name, Total Amount Paid) and {row} is the row header the page already shows ("Income source N", "Creditor N"). The note at the top reads "Some rows aren't finished, so nothing has been saved yet. Please fill in the boxes marked below, or clear any row you don't need." They follow the fee-waiver page's existing "Please fill in all required fields."
- Source, Creditor Name and Dates of Payments stop at 255 characters (`maxLength={255}`). Amounts are checked only for being present. The serializer's `gross_amount` and `total_paid` have no `min_value`; that is a pre-existing defect, and this frontend task changes no serializer.
- `leaves a blank row out of the save instead of asking the filer to finish it` passes before the change, by design: it guards the existing blank-row rule against the new check.

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/FeeWaiverPage.test.tsx b/frontend/src/pages/__tests__/FeeWaiverPage.test.tsx
index ae1b5b7..6328611 100644
--- a/frontend/src/pages/__tests__/FeeWaiverPage.test.tsx
+++ b/frontend/src/pages/__tests__/FeeWaiverPage.test.tsx
@@ -14,6 +14,7 @@ function renderFeeWaiver() {
       <IntakeProvider>
         <Routes>
           <Route path="/fee-waiver" element={<FeeWaiverPage />} />
+          <Route path="/sofa" element={<div>Statement of Financial Affairs</div>} />
           <Route path="/forms" element={<div>FormDashboard</div>} />
         </Routes>
       </IntakeProvider>
@@ -56,7 +57,7 @@ describe('FeeWaiverPage', () => {
     });
   });

-  it('navigates to /forms on successful submission', async () => {
+  it('continues to the financial history questions (SOFA), not the forms, once the application is sent', async () => {
     renderFeeWaiver();
     await waitFor(() => screen.getByRole('heading', { name: /filing fee waiver/i }));

@@ -66,9 +67,11 @@ describe('FeeWaiverPage', () => {

     await userEvent.click(screen.getByRole('button', { name: /submit/i }));

+    // Form 107 is in every packet, so a waiver filer answers its questions before the forms (DIG-149)
     await waitFor(() => {
-      expect(screen.getByText('FormDashboard')).toBeInTheDocument();
+      expect(screen.getByText('Statement of Financial Affairs')).toBeInTheDocument();
     });
+    expect(screen.queryByText('FormDashboard')).not.toBeInTheDocument();
   });

   it('shows error when submission fails', async () => {
@@ -123,7 +126,7 @@ describe('FeeWaiverPage', () => {
     expect(screen.getByLabelText(/monthly expenses/i)).toHaveValue(1800);
   });

-  it('shows an off-ramp instead of the form when the filer is fee-waiver ineligible', async () => {
+  it('shows an off-ramp instead of the form when the filer is fee-waiver ineligible, and it leads on to SOFA', async () => {
     server.use(
       http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
         HttpResponse.json({ means_test_result: ineligibleResult, session_id: 1 })
@@ -137,6 +140,7 @@ describe('FeeWaiverPage', () => {
           <MeansTestTrigger />
           <Routes>
             <Route path="/fee-waiver" element={<FeeWaiverPage />} />
+            <Route path="/sofa" element={<div>Statement of Financial Affairs</div>} />
             <Route path="/forms" element={<div>FormDashboard</div>} />
           </Routes>
         </IntakeProvider>
@@ -147,10 +151,15 @@ describe('FeeWaiverPage', () => {
     await waitFor(() => {
       expect(screen.getByText(/don't appear to qualify/i)).toBeInTheDocument();
     });
-    expect(screen.getByRole('button', { name: /continue to my forms/i })).toBeInTheDocument();
+    const continueButton = screen.getByRole('button', { name: /^continue$/i });

     // ...and the application form itself is hidden — no fields to fill out.
     expect(screen.queryByLabelText(/household size/i)).not.toBeInTheDocument();
     expect(screen.queryByRole('button', { name: /submit waiver/i })).not.toBeInTheDocument();
+
+    // The off-ramp leads where every filer goes next: the financial history questions
+    await userEvent.click(continueButton);
+    expect(await screen.findByText('Statement of Financial Affairs')).toBeInTheDocument();
+    expect(screen.queryByText('FormDashboard')).not.toBeInTheDocument();
   });
 });
diff --git a/frontend/src/pages/__tests__/SOFAStep.test.tsx b/frontend/src/pages/__tests__/SOFAStep.test.tsx
index eb9bcc1..2976831 100644
--- a/frontend/src/pages/__tests__/SOFAStep.test.tsx
+++ b/frontend/src/pages/__tests__/SOFAStep.test.tsx
@@ -1,7 +1,7 @@
 import { StrictMode } from 'react';
 import { render, screen } from '@testing-library/react';
 import userEvent from '@testing-library/user-event';
-import { MemoryRouter } from 'react-router-dom';
+import { MemoryRouter, Routes, Route } from 'react-router-dom';
 import { http, HttpResponse, delay } from 'msw';
 import { server } from '../../test/mocks/server';
 import { IntakeProvider, useIntake } from '../../context/IntakeContext';
@@ -23,6 +23,31 @@ function SOFAStepWithSession() {
   return session ? <SOFAStep /> : null;
 }

+/** Opens /sofa with the forms dashboard behind it, and records every save the page sends. */
+function renderSOFA() {
+  const saves: Record<string, unknown>[] = [];
+  server.use(
+    http.patch('http://localhost:8000/api/intake/sofa-report/:sessionId/', async ({ request }) => {
+      saves.push((await request.json()) as Record<string, unknown>);
+      return HttpResponse.json(emptyReport);
+    })
+  );
+  localStorage.setItem('current_session_id', '1');
+  render(
+    <MemoryRouter initialEntries={['/sofa']}>
+      <IntakeProvider>
+        <Routes>
+          <Route path="/sofa" element={<SOFAStepWithSession />} />
+          <Route path="/forms" element={<div>FormDashboard</div>} />
+        </Routes>
+      </IntakeProvider>
+    </MemoryRouter>
+  );
+  return { saves, user: userEvent.setup() };
+}
+
+const save = () => screen.getByRole('button', { name: /save & continue/i });
+
 describe('SOFAStep', () => {
   it('keeps a section the filer ticked when an earlier load replies late', async () => {
     // StrictMode mounts the page twice, so the report is read twice; the first read replies last.
@@ -54,3 +79,183 @@ describe('SOFAStep', () => {
     expect(screen.getByRole('checkbox', priorIncome)).toBeChecked();
   });
 });
+
+describe('SOFAStep unfinished rows (DIG-148)', () => {
+  it('names the income row and the boxes to finish, and saves nothing until they are filled', async () => {
+    const { saves, user } = renderSOFA();
+    await user.click(
+      await screen.findByRole('checkbox', { name: /i had income in the past 3 years/i })
+    );
+
+    // Income source 1 is finished; Income source 2 has a source, but no year and no amount
+    await user.type(screen.getByLabelText('Source'), 'Temp Agency');
+    await user.type(screen.getByLabelText('Gross Amount'), '24000');
+    await user.click(screen.getByRole('button', { name: /add another income source/i }));
+    await user.clear(screen.getAllByLabelText('Year')[1]);
+    await user.type(screen.getAllByLabelText('Source')[1], 'Walgreens');
+    // Nothing is asked of a row while the filer is still typing it
+    expect(screen.queryByText(/please fill in/i)).not.toBeInTheDocument();
+    await user.click(save());
+
+    expect(screen.getByText(/nothing has been saved yet/i)).toBeInTheDocument();
+    expect(screen.getByText('Please fill in the Year for Income source 2.')).toBeInTheDocument();
+    expect(
+      screen.getByText('Please fill in the Gross Amount for Income source 2.')
+    ).toBeInTheDocument();
+    expect(screen.queryByText(/for Income source 1\./)).not.toBeInTheDocument();
+    expect(screen.queryByText(/could not save/i)).not.toBeInTheDocument();
+    expect(saves).toHaveLength(0);
+
+    // Once the row is finished, the message goes and the whole page saves
+    await user.type(screen.getAllByLabelText('Year')[1], '2024');
+    await user.type(screen.getAllByLabelText('Gross Amount')[1], '9100.25');
+    expect(screen.queryByText(/please fill in/i)).not.toBeInTheDocument();
+    await user.click(save());
+
+    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
+    expect(saves).toHaveLength(1);
+    expect(saves[0].prior_income).toEqual([
+      expect.objectContaining({ source: 'Temp Agency', gross_amount: '24000' }),
+      expect.objectContaining({ year: 2024, source: 'Walgreens', gross_amount: '9100.25' }),
+    ]);
+  });
+
+  it('asks for the Source of an income row that has only an amount, and saves nothing until it is filled', async () => {
+    const { saves, user } = renderSOFA();
+    await user.click(
+      await screen.findByRole('checkbox', { name: /i had income in the past 3 years/i })
+    );
+
+    // The page fills in the year, so only the Source is missing
+    await user.type(screen.getByLabelText('Gross Amount'), '24000');
+    await user.click(save());
+
+    expect(screen.getByText(/nothing has been saved yet/i)).toBeInTheDocument();
+    expect(screen.getByText('Please fill in the Source for Income source 1.')).toBeInTheDocument();
+    expect(screen.queryByText(/the (Year|Gross Amount) for/)).not.toBeInTheDocument();
+    expect(saves).toHaveLength(0);
+
+    // The one save the page sends is the one after the Source is filled
+    await user.type(screen.getByLabelText('Source'), 'Temp Agency');
+    await user.click(save());
+
+    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
+    expect(saves).toHaveLength(1);
+    expect(saves[0].prior_income).toEqual([
+      expect.objectContaining({ source: 'Temp Agency', gross_amount: '24000' }),
+    ]);
+  });
+
+  it('names the creditor row and the boxes to finish, counting a row with only its dates as started', async () => {
+    const { saves, user } = renderSOFA();
+    await user.click(
+      await screen.findByRole('checkbox', { name: /payments to creditors in the past year/i })
+    );
+
+    await user.type(screen.getByLabelText('Dates of Payments'), 'Monthly Jan-Mar 2026');
+    await user.click(save());
+
+    expect(
+      screen.getByText('Please fill in the Creditor Name for Creditor 1.')
+    ).toBeInTheDocument();
+    expect(
+      screen.getByText('Please fill in the Total Amount Paid for Creditor 1.')
+    ).toBeInTheDocument();
+    expect(saves).toHaveLength(0);
+
+    await user.type(screen.getByLabelText('Creditor Name'), 'Capital One');
+    await user.type(screen.getByLabelText('Total Amount Paid'), '1500');
+    await user.click(save());
+
+    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
+    expect(saves).toHaveLength(1);
+    expect(saves[0].creditor_payments).toEqual([
+      expect.objectContaining({
+        creditor_name: 'Capital One',
+        total_paid: '1500',
+        dates_of_payments: 'Monthly Jan-Mar 2026',
+      }),
+    ]);
+  });
+
+  it('leaves a blank row out of the save instead of asking the filer to finish it', async () => {
+    const { saves, user } = renderSOFA();
+    await user.click(
+      await screen.findByRole('checkbox', { name: /i had income in the past 3 years/i })
+    );
+
+    // Income source 1 keeps only the year the page fills in; Income source 2 is finished
+    await user.click(screen.getByRole('button', { name: /add another income source/i }));
+    await user.type(screen.getAllByLabelText('Source')[1], 'Temp Agency');
+    await user.type(screen.getAllByLabelText('Gross Amount')[1], '24000');
+    await user.click(save());
+
+    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
+    expect(screen.queryByText(/please fill in/i)).not.toBeInTheDocument();
+    expect(saves).toHaveLength(1);
+    expect(saves[0].prior_income).toEqual([
+      expect.objectContaining({ source: 'Temp Agency', gross_amount: '24000' }),
+    ]);
+  });
+
+  it('saves without the rows of a section the filer switched off, even a half-filled one', async () => {
+    const { saves, user } = renderSOFA();
+    const priorIncome = await screen.findByRole('checkbox', {
+      name: /i had income in the past 3 years/i,
+    });
+    await user.click(priorIncome);
+    await user.type(screen.getByLabelText('Source'), 'Walgreens');
+    await user.click(priorIncome);
+    await user.click(save());
+
+    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
+    expect(saves).toHaveLength(1);
+    expect(saves[0].has_prior_income).toBe(false);
+    expect(saves[0]).not.toHaveProperty('prior_income');
+  });
+
+  it('saves without the creditor rows the filer switched off, even a half-filled one', async () => {
+    const { saves, user } = renderSOFA();
+    const creditorPayments = await screen.findByRole('checkbox', {
+      name: /payments to creditors in the past year/i,
+    });
+    await user.click(creditorPayments);
+    await user.type(screen.getByLabelText('Creditor Name'), 'Capital One');
+    await user.click(creditorPayments);
+    await user.click(save());
+
+    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
+    expect(saves).toHaveLength(1);
+    expect(saves[0].has_creditor_payments).toBe(false);
+    expect(saves[0]).not.toHaveProperty('creditor_payments');
+  });
+
+  it('stops a text box at the 255 characters the server stores', async () => {
+    const { saves, user } = renderSOFA();
+    await user.click(
+      await screen.findByRole('checkbox', { name: /i had income in the past 3 years/i })
+    );
+    await user.click(
+      await screen.findByRole('checkbox', { name: /payments to creditors in the past year/i })
+    );
+
+    await user.click(screen.getByLabelText('Source'));
+    await user.paste('S'.repeat(300));
+    await user.type(screen.getByLabelText('Gross Amount'), '24000');
+    await user.click(screen.getByLabelText('Creditor Name'));
+    await user.paste('C'.repeat(300));
+    await user.click(screen.getByLabelText('Dates of Payments'));
+    await user.paste('D'.repeat(300));
+    await user.type(screen.getByLabelText('Total Amount Paid'), '1500');
+    await user.click(save());
+
+    expect(await screen.findByText('FormDashboard', {}, { timeout: 2000 })).toBeInTheDocument();
+    expect(saves[0].prior_income).toEqual([expect.objectContaining({ source: 'S'.repeat(255) })]);
+    expect(saves[0].creditor_payments).toEqual([
+      expect.objectContaining({
+        creditor_name: 'C'.repeat(255),
+        dates_of_payments: 'D'.repeat(255),
+      }),
+    ]);
+  });
+});
PATCH
```

The fee-waiver tests give the page a `/sofa` route beside `/forms`, and require both the submit and the off-ramp's Continue to land on SOFA and not on the dashboard. The SOFA tests open `/sofa` through a `renderSOFA()` helper that records every PATCH body. They require each unfinished box's message and the note, no PATCH until the rows are finished, then exactly one PATCH with the finished rows, no row key for a section switched off, and 255-character text boxes.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FeeWaiverPage.test.tsx src/pages/__tests__/SOFAStep.test.tsx 2>&1 | tail -86
```

Expected: FAIL — `8 failed`: every new and changed test but the blank-row test, which passes as it should before the change. Both fee-waiver exits still go to the dashboard, so the submit's wait for SOFA times out and the off-ramp has no Continue button. The SOFA page shows no message and saves at once, so the row tests find no note. It sends the rows of a section the filer switched off, `to not have property "prior_income"` and `to not have property "creditor_payments"`, and it saves a 300-character Source.

- [ ] **Step 3: Send both fee-waiver exits to SOFA**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/FeeWaiverPage.tsx b/frontend/src/pages/FeeWaiverPage.tsx
index 66aee12..8d936b2 100644
--- a/frontend/src/pages/FeeWaiverPage.tsx
+++ b/frontend/src/pages/FeeWaiverPage.tsx
@@ -56,7 +56,8 @@ export function FeeWaiverPage() {
         cannot_pay_full: cannotPayFull,
         cannot_pay_installments: cannotPayInstallments,
       });
-      navigate('/forms');
+      // Form 107 is in every packet, so its questions come before the forms (DIG-149)
+      navigate('/sofa');
     } catch {
       setError('Unable to submit your fee waiver application. Please try again.');
     } finally {
@@ -72,10 +73,11 @@ export function FeeWaiverPage() {
         <div className="fee-waiver-ineligible info-box" role="status">
           <p>
             Based on the information you entered, you don't appear to qualify for a filing fee
-            waiver. That's okay — you can continue to your forms. A court makes the final decision.
+            waiver. That's okay — you can continue to your financial history and then your forms. A
+            court makes the final decision.
           </p>
-          <Button type="button" onClick={() => navigate('/forms')}>
-            Continue to my forms
+          <Button type="button" onClick={() => navigate('/sofa')}>
+            Continue
           </Button>
         </div>
       )}
PATCH
```

DIG-149: Form 107 is in every packet, so a waiver filer answers its questions before the forms, just as the wizard already sends a filer who doesn't qualify for the waiver to `/sofa`.

- [ ] **Step 4: Check the SOFA rows before saving, and name each box to finish**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/SOFAStep.tsx b/frontend/src/pages/SOFAStep.tsx
index 716ed9f..b937dc5 100644
--- a/frontend/src/pages/SOFAStep.tsx
+++ b/frontend/src/pages/SOFAStep.tsx
@@ -12,7 +12,7 @@
  * - No shame around financial history
  */

-import { useEffect, useState } from 'react';
+import { useEffect, useMemo, useState } from 'react';
 import { useNavigate } from 'react-router-dom';
 import { useIntake } from '../context/IntakeContext';
 import { sofaReportAPI } from '../api/client';
@@ -29,6 +29,45 @@ function emptyCreditorPayment(): SOFACreditorPayment {
   return { id: Math.random(), creditor_name: '', total_paid: '', dates_of_payments: '' };
 }

+// A row counts once the filer types in it; the year the page fills in doesn't count.
+function incomeRowStarted(row: SOFAPriorIncome): boolean {
+  return Boolean(row.source?.trim() || row.gross_amount);
+}
+
+function paymentRowStarted(row: SOFACreditorPayment): boolean {
+  return Boolean(row.creditor_name?.trim() || row.total_paid || row.dates_of_payments?.trim());
+}
+
+/**
+ * The boxes still empty in the started rows of the sections switched on, keyed by the box's
+ * field name. The server refuses a row without them, which used to fail the whole save with a
+ * generic error (DIG-148), so each message names the row and the box to finish.
+ */
+function unfinishedBoxes(report: SOFAReport): Record<string, string> {
+  const missing: Record<string, string> = {};
+  const ask = (name: string, box: string, row: string) => {
+    missing[name] = `Please fill in the ${box} for ${row}.`;
+  };
+  if (report.has_prior_income) {
+    report.prior_income.forEach((row, idx) => {
+      if (!incomeRowStarted(row)) return;
+      const label = `Income source ${idx + 1}`;
+      if (!row.year) ask(`prior-income-year-${idx}`, 'Year', label);
+      if (!row.source?.trim()) ask(`prior-income-source-${idx}`, 'Source', label);
+      if (!row.gross_amount) ask(`prior-income-amount-${idx}`, 'Gross Amount', label);
+    });
+  }
+  if (report.has_creditor_payments) {
+    report.creditor_payments.forEach((row, idx) => {
+      if (!paymentRowStarted(row)) return;
+      const label = `Creditor ${idx + 1}`;
+      if (!row.creditor_name?.trim()) ask(`creditor-name-${idx}`, 'Creditor Name', label);
+      if (!row.total_paid) ask(`creditor-paid-${idx}`, 'Total Amount Paid', label);
+    });
+  }
+  return missing;
+}
+
 export function SOFAStep() {
   const navigate = useNavigate();
   const { session } = useIntake();
@@ -38,6 +77,12 @@ export function SOFAStep() {
   const [saving, setSaving] = useState(false);
   const [error, setError] = useState<string | null>(null);
   const [saved, setSaved] = useState(false);
+  const [showUnfinished, setShowUnfinished] = useState(false);
+
+  // Once a save finds unfinished rows, each empty box says what it needs until it is filled
+  const unfinished = useMemo(() => (report ? unfinishedBoxes(report) : {}), [report]);
+  const hasUnfinished = Object.keys(unfinished).length > 0;
+  const boxError = (name: string) => (showUnfinished ? unfinished[name] : undefined);

   // Load report on mount. A superseded load (StrictMode's second mount, or a new session)
   // is ignored, so its late reply can't undo what the filer has already ticked.
@@ -159,19 +204,23 @@ export function SOFAStep() {

   const handleSave = async () => {
     if (!session || !report) return;
-    setSaving(true);
     setError(null);
+    if (hasUnfinished) {
+      setShowUnfinished(true);
+      return;
+    }
+    setSaving(true);
     setSaved(false);

     try {
-      // Clean empty rows before saving
-      const clean = {
-        ...report,
-        prior_income: report.prior_income.filter((r) => r.source?.trim() || r.gross_amount),
-        creditor_payments: report.creditor_payments.filter(
-          (r) => r.creditor_name?.trim() || r.total_paid
-        ),
-      };
+      // Blank rows are left out. A section switched off sends no rows: its rows don't print, the
+      // server keeps the ones it has, and a half-filled row the filer can't see can't fail the save.
+      const { prior_income, creditor_payments, ...flags } = report;
+      const clean: Partial<SOFAReport> = { ...flags };
+      if (report.has_prior_income) clean.prior_income = prior_income.filter(incomeRowStarted);
+      if (report.has_creditor_payments) {
+        clean.creditor_payments = creditor_payments.filter(paymentRowStarted);
+      }
       await sofaReportAPI.patch(session.id, clean);
       setSaved(true);
       setTimeout(() => navigate('/forms'), 800);
@@ -223,6 +272,13 @@ export function SOFAStep() {
         </div>
       )}

+      {showUnfinished && hasUnfinished && (
+        <div className="info-box info-box--error" role="alert">
+          Some rows aren&apos;t finished, so nothing has been saved yet. Please fill in the boxes
+          marked below, or clear any row you don&apos;t need.
+        </div>
+      )}
+
       {saved && (
         <div className="info-box info-box--success" role="status">
           Saved! Redirecting to your forms...
@@ -278,6 +334,7 @@ export function SOFAStep() {
                       updatePriorIncomeRow(idx, 'year', parseInt(e.target.value, 10) || 0)
                     }
                     placeholder="2025"
+                    error={boxError(`prior-income-year-${idx}`)}
                   />
                   <FormField
                     label="Source"
@@ -287,6 +344,8 @@ export function SOFAStep() {
                     onChange={(e) => updatePriorIncomeRow(idx, 'source', e.target.value)}
                     placeholder="Employer name or income type"
                     helpText="e.g., 'Walmart', 'Self-employment', 'Unemployment benefits'"
+                    maxLength={255}
+                    error={boxError(`prior-income-source-${idx}`)}
                   />
                   <FormField
                     label="Gross Amount"
@@ -297,6 +356,7 @@ export function SOFAStep() {
                     value={row.gross_amount}
                     onChange={(e) => updatePriorIncomeRow(idx, 'gross_amount', e.target.value)}
                     placeholder="0.00"
+                    error={boxError(`prior-income-amount-${idx}`)}
                   />
                 </div>
               </div>
@@ -353,6 +413,8 @@ export function SOFAStep() {
                     value={row.creditor_name}
                     onChange={(e) => updateCreditorPaymentRow(idx, 'creditor_name', e.target.value)}
                     placeholder="Name of the creditor"
+                    maxLength={255}
+                    error={boxError(`creditor-name-${idx}`)}
                   />
                   <FormField
                     label="Total Amount Paid"
@@ -363,6 +425,7 @@ export function SOFAStep() {
                     value={row.total_paid}
                     onChange={(e) => updateCreditorPaymentRow(idx, 'total_paid', e.target.value)}
                     placeholder="0.00"
+                    error={boxError(`creditor-paid-${idx}`)}
                   />
                   <FormField
                     label="Dates of Payments"
@@ -374,6 +437,7 @@ export function SOFAStep() {
                     }
                     placeholder="e.g., Monthly Jan-Mar 2026"
                     helpText="When did you make these payments?"
+                    maxLength={255}
                   />
                 </div>
               </div>
PATCH
```

DIG-148: `handleSave` sends nothing while `unfinishedBoxes` finds an empty box. It shows the note, and each box shows its own message through `FormField`'s `error` prop. A finished page saves as before, without blank rows, and without the rows of a section switched off.

- [ ] **Step 5: Take the waiver journeys through SOFA**

```bash
git apply <<'PATCH'
diff --git a/frontend/e2e/journeys/deshawn-assets.spec.ts b/frontend/e2e/journeys/deshawn-assets.spec.ts
index c918cea..a25b24a 100644
--- a/frontend/e2e/journeys/deshawn-assets.spec.ts
+++ b/frontend/e2e/journeys/deshawn-assets.spec.ts
@@ -13,6 +13,7 @@ import { WizardPage } from '../pages/wizard.page';
 import { DocumentsPage } from '../pages/documents.page';
 import { FeeWaiverPage } from '../pages/fee-waiver.page';
 import { DashboardPage } from '../pages/dashboard.page';
+import { SOFAPage } from '../pages/sofa.page';

 test.describe('DeShawn Mitchell — Assets', () => {
   test('enters 3 assets and 4 debts successfully', async ({ page }) => {
@@ -22,6 +23,7 @@ test.describe('DeShawn Mitchell — Assets', () => {
     const documents = new DocumentsPage(page);
     const feeWaiver = new FeeWaiverPage(page);
     const dashboard = new DashboardPage(page);
+    const sofa = new SOFAPage(page);

     await landing.goto();
     await landing.clickGetStarted();
@@ -82,6 +84,12 @@ test.describe('DeShawn Mitchell — Assets', () => {
       totalExpenses
     );

+    // The waiver application continues to the SOFA step (DIG-149). This journey isn't about
+    // financial history, so skip SOFA to reach the forms dashboard. (The SOFA save path
+    // itself is covered by sofa-journey.spec.ts.)
+    await sofa.waitForLoad();
+    await sofa.skipForNow();
+
     // Generate forms (passes means test)
     await dashboard.generateAllForms(15); // 14 forms + Form 103B (fee waiver)
     const count = await dashboard.getGeneratedCount();
diff --git a/frontend/e2e/journeys/maria-happy-path.spec.ts b/frontend/e2e/journeys/maria-happy-path.spec.ts
index 4c129be..3d0ce24 100644
--- a/frontend/e2e/journeys/maria-happy-path.spec.ts
+++ b/frontend/e2e/journeys/maria-happy-path.spec.ts
@@ -13,6 +13,7 @@ import { WizardPage } from '../pages/wizard.page';
 import { DocumentsPage } from '../pages/documents.page';
 import { FeeWaiverPage } from '../pages/fee-waiver.page';
 import { DashboardPage } from '../pages/dashboard.page';
+import { SOFAPage } from '../pages/sofa.page';

 test.describe('Maria Torres — Happy Path', () => {
   test('completes full intake and generates all forms', async ({ page }) => {
@@ -22,6 +23,7 @@ test.describe('Maria Torres — Happy Path', () => {
     const documents = new DocumentsPage(page);
     const feeWaiver = new FeeWaiverPage(page);
     const dashboard = new DashboardPage(page);
+    const sofa = new SOFAPage(page);

     // Landing → Register
     await landing.goto();
@@ -85,6 +87,12 @@ test.describe('Maria Torres — Happy Path', () => {
       totalExpenses
     );

+    // The waiver application continues to the SOFA step (DIG-149). This journey isn't about
+    // financial history, so skip SOFA to reach the forms dashboard. (The SOFA save path
+    // itself is covered by sofa-journey.spec.ts.)
+    await sofa.waitForLoad();
+    await sofa.skipForNow();
+
     // Dashboard — generate all forms
     await dashboard.generateAllForms(15); // 14 forms + Form 103B (fee waiver)
     const count = await dashboard.getGeneratedCount();
diff --git a/frontend/e2e/journeys/sarah-simplest.spec.ts b/frontend/e2e/journeys/sarah-simplest.spec.ts
index bf83690..6312f5d 100644
--- a/frontend/e2e/journeys/sarah-simplest.spec.ts
+++ b/frontend/e2e/journeys/sarah-simplest.spec.ts
@@ -13,6 +13,7 @@ import { WizardPage } from '../pages/wizard.page';
 import { DocumentsPage } from '../pages/documents.page';
 import { FeeWaiverPage } from '../pages/fee-waiver.page';
 import { DashboardPage } from '../pages/dashboard.page';
+import { SOFAPage } from '../pages/sofa.page';

 test.describe('Sarah Chen — Simplest Case', () => {
   test('completes intake with no assets (fastest path)', async ({ page }) => {
@@ -22,6 +23,7 @@ test.describe('Sarah Chen — Simplest Case', () => {
     const documents = new DocumentsPage(page);
     const feeWaiver = new FeeWaiverPage(page);
     const dashboard = new DashboardPage(page);
+    const sofa = new SOFAPage(page);

     await landing.goto();
     await landing.clickGetStarted();
@@ -81,6 +83,12 @@ test.describe('Sarah Chen — Simplest Case', () => {
       totalExpenses
     );

+    // The waiver application continues to the SOFA step (DIG-149). This journey isn't about
+    // financial history, so skip SOFA to reach the forms dashboard. (The SOFA save path
+    // itself is covered by sofa-journey.spec.ts.)
+    await sofa.waitForLoad();
+    await sofa.skipForNow();
+
     // Generate all forms
     await dashboard.generateAllForms(15); // 14 forms + Form 103B (fee waiver)
     const count = await dashboard.getGeneratedCount();
diff --git a/frontend/e2e/pages/fee-waiver.page.ts b/frontend/e2e/pages/fee-waiver.page.ts
index 3f41fb2..663b5e3 100644
--- a/frontend/e2e/pages/fee-waiver.page.ts
+++ b/frontend/e2e/pages/fee-waiver.page.ts
@@ -1,6 +1,6 @@
 /**
  * Fee Waiver Page Object — the waiver application shown after intake
- * completion for fee-waiver-eligible sessions (routes to /forms on submit).
+ * completion for fee-waiver-eligible sessions (continues to /sofa on submit).
  */

 import type { Page } from '@playwright/test';
@@ -20,6 +20,6 @@ export class FeeWaiverPage {
     await this.page.getByLabel(/cannot pay the full filing fee/i).check();
     await this.page.getByLabel(/cannot pay the filing fee in installments/i).check();
     await this.page.getByRole('button', { name: /submit waiver application/i }).click();
-    await this.page.waitForURL('**/forms');
+    await this.page.waitForURL('**/sofa');
   }
 }
PATCH
```

§7.9: the fee-waiver page now continues to `/sofa`, so the page object's `submit` waits for `**/sofa`; still waiting for `/forms`, all three waiver journeys would time out. Each journey then waits for the SOFA page and skips it to reach the dashboard, and its packet size doesn't change.

- [ ] **Step 6: Run the tests again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FeeWaiverPage.test.tsx src/pages/__tests__/SOFAStep.test.tsx 2>&1 | tail -86
```

Expected: `13 passed`.

- [ ] **Step 7: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2a.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -3)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `1671 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  287 passed (287)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 8: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 9: Commit**

```bash
set -eo pipefail
git add \
  frontend/e2e/journeys/deshawn-assets.spec.ts \
  frontend/e2e/journeys/maria-happy-path.spec.ts \
  frontend/e2e/journeys/sarah-simplest.spec.ts \
  frontend/e2e/pages/fee-waiver.page.ts \
  frontend/src/pages/FeeWaiverPage.tsx \
  frontend/src/pages/SOFAStep.tsx \
  frontend/src/pages/__tests__/FeeWaiverPage.test.tsx \
  frontend/src/pages/__tests__/SOFAStep.test.tsx
git commit -F - <<'MSG'
fix(frontend): take waiver filers through SOFA, and name the box a half-filled SOFA row needs

The fee-waiver page went straight to the forms, so a filer who applied for
the waiver never saw the Statement of Financial Affairs questions, and their
Form 107 printed with no income history and no payments (DIG-149). Both of
the page's exits, the submit and the off-ramp for a filer who doesn't
qualify, now continue to /sofa. The off-ramp's button says "Continue"
instead of "Continue to my forms". Maria's, DeShawn's and Sarah's journeys
pass through the SOFA page and skip it, as James's does.

A SOFA row with a source but no amount, or a creditor but no amount, failed
the whole save with "Could not save your financial history" (DIG-148). The
page now checks the rows before it saves. A row the filer typed in needs its
year, source and gross amount, or its creditor name and amount paid; the
year the page fills in doesn't start a row, and a creditor row with only its
dates does. Each empty box names its row and itself, a note at the top says
nothing has been saved yet, and nothing is sent until the rows are finished.
Blank rows are still left out. A section switched off sends no rows, so the
server keeps the ones it has and a row the filer can't see can't fail the
save. The text boxes stop at the 255 characters their columns store.

Forms step 2a, commit 3 (step 2 spec §5.4, §7.9).
MSG
git status --short
```

### Task 8: Build each persona's forms through the API and compare them with the seeds

_Built and verified as commit `02ff8cc` on `plan/forms-step2a`._

**Files:**

- Create: `backend/apps/forms/tests/test_api_readback.py`

**Interfaces:**

- Consumes:
  - `PERSONAS` in `apps/intake/management/commands/seed_demo_data.py`: persona name → a function returning that persona's data (`debtor`, `income`, `expenses`, `assets`, `debts`, and `sofa` for Maria). `seed_demo_data --persona <name>` seeds the user `demo_<name>`.
  - `packet(session)` and `build_field_values(form_type, session)` from `apps.forms.registry`; `load_schema(form_type).fields`, reading each field's `repeat`, `row`, `pdf_field` and `binding`; `GeneratedForm.field_values` (JSON text).
  - The endpoints the wizard and the pages after it call:
    - `POST /api/intake/sessions/` → 201, with the id at `session.id`
    - `PATCH /api/intake/sessions/{id}/` with one section (`debtor_info`, `income_info`, `expense_info`, `assets` or `debts`)
    - `PUT /api/intake/sessions/{id}/contracts/` and `.../codebtors/` with a list (Task 4)
    - `POST /api/intake/sessions/{id}/complete/`, which Generate All requires since Task 2
    - `POST /api/intake/sessions/{id}/calculate_means_test/` → `means_test_result.qualifies_for_fee_waiver`
    - `POST /api/intake/fee-waiver/` → 201
    - `PATCH /api/intake/sofa-report/{session id}/` → 200
    - `POST /api/forms/generate_all/` with `{session_id}` → `{generated, errors}`
  - Tasks 5 and 6: the API keeps the secured flag and the phone number.
- Produces:
  - `backend/apps/forms/tests/test_api_readback.py` with `test_forms_built_through_the_api_print_what_the_seeded_forms_print`, parametrized over `maria`, `james`, `priya`, `deshawn` and `sarah`.
  - `WAIVER_FILERS = {"maria", "deshawn", "sarah"}`, `WIZARD_STEPS` (the five session sections a step saves), `_sent(data)`, `_fee_waiver_application(data)`, `_send_through_the_api(persona)` → `(session id, form types)`, `_comparable(form_type, values)` and `_amount(text)`.
  - Later tasks grow this test rather than writing another: Task 9 requires every persona to type every Income box and takes the fee waiver's monthly income from `monthly_gross_wages`, Task 11 drops the means-test call and reads `MeansTest.qualifies_for_fee_waiver` after Generate All, and Task 13 builds `_fee_waiver_application` from the seed's `fee_waiver` and compares the stored applications.

**Decisions already made in this task:**

- **No production code changes.** Tasks 5 and 6 already made the API keep the secured flag and the phone number, so the read-back passes for all five personas as written, and `known_defects.json` is untouched.
- **The calls follow `handleComplete`'s order**, not the spec's listing: the five step saves, the two list saves, Complete, the means test, the fee-waiver application, the SOFA save, then Generate All. Because the fee-waiver and SOFA saves land on a completed intake, this order proves that neither reopens it (the reopening ruling: form answers, SOFA and the fee-waiver application never reopen a completed intake). If either did, Generate All would refuse the session.
- **The payloads come from `seed_demo_data.PERSONAS`, sent unfiltered.** One source feeds both sides, so any field the API drops that a form prints shows up as a mismatch. That includes the seed's `marital_status` and `number_of_dependents` in the income save, although the wizard never collects them. Without them, 122A-1 line 13A would print the one-person median for a married filer or one with dependents. That wizard gap is 2b's (DIG-51) and step 4's (DIG-53), not this test's.
- **Only Maria sends a SOFA save,** because she is the only persona with SOFA data. No persona journey saves SOFA either: four press "Skip for now", and Priya's ends after Complete. A report with nothing ticked resolves exactly like no report.
- **The fee waiver goes to the fixed set `WAIVER_FILERS`,** with the figures the seed stores, and the test asserts that the means test agrees. Task 11 removes the means-test call, so the routing must not depend on its response.
- **Values are compared from `GeneratedForm.field_values`,** the snapshot Generate All stores (the API never returns it), against `build_field_values(form_type, seeded)` over `packet(seeded)`.
- **Form 107's repeat-group rows compare in any order** (DIG-164). Each row is the sorted list of its `(binding, value)` cells, and the rows are then sorted, so a row's values stay together and an amount that moves to another row is a difference. No other form has repeat groups.
- **No id-order code for A/B line 53.** Nothing prints line 53 until 2b. Rows are sent in the seed's order, so their ids follow the seeded rows' order.
- **The 122A-2 check names no box,** because 2b moves those boxes. Only Priya's packet holds 122A-2, and it must print at least one amount above zero, so two empty packets can't compare equal.
- **The clock is not frozen.** A run in which Generate All and the seed-side build fall on opposite sides of local midnight fails the `today_iso` boxes; a rerun passes.
- **The JSON is encoded with `DjangoJSONEncoder`** (decimals as strings, dates as ISO), as the browser sends them.
- **The runtime cost is accepted.** Each persona's Generate All fills about 15 templates, so the read-back takes about 25 seconds. Mocking the filler would hide `UnknownField` faults.
- **Two review nits stand as committed:** the status asserts for create, Complete, the means test and Generate All carry no response body, and `WIZARD_STEPS` shares its name with the frontend's 8-step list although it holds the five session sections.

- [ ] **Step 1: Write the read-back**

```python file=backend/apps/forms/tests/test_api_readback.py
"""
The read-back: each persona's forms, built through the API, print what the seeded
persona's forms print (step 2 spec §7.6, DIG-140).

Business intent: the seeds write the database directly, so the oracle never sees a field
the API drops on the way in. The phone number and the "secured" flag were dropped that
way, and the filer signs every page under penalty of perjury. Each test sends one
persona's data, typed $0 amounts included, through the endpoints the wizard and the pages
after it call, then requires every form's stored values to equal the values built from
the seeded session.

It can't catch a page that sends a field under the wrong name, or never sends it: it
sends what this file sends (spec §10). Per-step vitest tests pin the names the server
expects.
"""

import json
from decimal import Decimal, InvalidOperation

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.forms.models import GeneratedForm
from apps.forms.registry import build_field_values, packet
from apps.forms.schema import load_schema
from apps.intake.management.commands.seed_demo_data import PERSONAS
from apps.intake.models import IntakeSession

User = get_user_model()

# The means test qualifies these personas for a fee waiver, so after Complete the wizard
# sends them to the fee-waiver page, and the seed gives them an application.
WAIVER_FILERS = {"maria", "deshawn", "sarah"}

# Each wizard step's session save: (the section it sends, the persona's data for it).
WIZARD_STEPS = [
    ("debtor_info", "debtor"),
    ("income_info", "income"),
    ("expense_info", "expenses"),
    ("assets", "assets"),
    ("debts", "debts"),
]


def _sent(data):
    """Persona data as JSON carries it from the browser: amounts as decimal strings, dates as ISO."""
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def _fee_waiver_application(data):
    """The application the seed stores, as the fee-waiver page sends it."""
    return {
        "household_size": data["debtor"]["household_size"],
        "monthly_income": data["income"]["monthly_income"][0],
        "monthly_expenses": sum(data["expenses"].values()),
        "receives_public_benefits": False,
        "benefit_types": [],
        "cannot_pay_full": True,
        "cannot_pay_installments": True,
    }


def _send_through_the_api(persona):
    """Enter the persona as a filer would, then Generate All. Returns (session id, form types)."""
    data = PERSONAS[persona]()
    client = APIClient()
    client.force_authenticate(User.objects.create_user(username=f"api_{persona}", password="pw"))

    district = District.objects.get(code="ilnd")
    created = client.post(
        "/api/intake/sessions/", {"district": district.pk, "current_step": 1}, format="json"
    )
    assert created.status_code == 201
    session_id = created.data["session"]["id"]
    session_url = f"/api/intake/sessions/{session_id}/"

    # Continue saves each step on its own. Rows go in the seed's order, so they get ids in
    # the same order as the seeded rows.
    for section, key in WIZARD_STEPS:
        response = client.patch(session_url, {section: _sent(data[key])}, format="json")
        assert response.status_code == 200, (section, response.data)
    # No persona has contracts or codebtors: Continue on steps 6 and 7 saves empty lists.
    for endpoint in ("contracts", "codebtors"):
        response = client.put(f"{session_url}{endpoint}/", [], format="json")
        assert response.status_code == 200, (endpoint, response.data)

    # Complete Intake, then the pages that follow it. Their saves keep the intake complete.
    assert client.post(f"{session_url}complete/").status_code == 200
    means_test = client.post(f"{session_url}calculate_means_test/")
    assert means_test.status_code == 200
    qualifies = means_test.data["means_test_result"]["qualifies_for_fee_waiver"]
    assert qualifies == (persona in WAIVER_FILERS)
    if persona in WAIVER_FILERS:
        response = client.post(
            "/api/intake/fee-waiver/",
            {"session": session_id, **_sent(_fee_waiver_application(data))},
            format="json",
        )
        assert response.status_code == 201, response.data
    if "sofa" in data:
        response = client.patch(
            f"/api/intake/sofa-report/{session_id}/", _sent(data["sofa"]), format="json"
        )
        assert response.status_code == 200, response.data

    generated = client.post("/api/forms/generate_all/", {"session_id": session_id}, format="json")
    assert generated.status_code == 200
    assert generated.data["errors"] == []
    return session_id, [form["form_type"] for form in generated.data["generated"]]


def _comparable(form_type, values):
    """
    A form's values, with each repeat group's rows in a fixed order.

    Stored rows have no fixed order (DIG-164), so Form 107's rows compare regardless of it.
    Each row keeps its own values together, so an amount that moves to another row differs.
    """
    fixed = dict(values)
    rows = {}
    for field in load_schema(form_type).fields:
        if field.repeat and field.row and field.pdf_field in fixed:
            cell = (field.binding or "", fixed.pop(field.pdf_field))
            rows.setdefault((field.repeat, field.row), []).append(cell)
    groups = {}
    for (group, _), cells in rows.items():
        groups.setdefault(group, []).append(sorted(cells))
    return fixed, {group: sorted(group_rows) for group, group_rows in groups.items()}


def _amount(text):
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


@pytest.mark.django_db
@pytest.mark.parametrize("persona", list(PERSONAS))
def test_forms_built_through_the_api_print_what_the_seeded_forms_print(persona):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, verbosity=0)
    seeded = IntakeSession.objects.get(user__username=f"demo_{persona}")

    session_id, form_types = _send_through_the_api(persona)

    assert form_types == packet(seeded)
    stored = {
        form.form_type: json.loads(form.field_values)
        for form in GeneratedForm.objects.filter(session_id=session_id)
    }
    assert {form_type: _comparable(form_type, values) for form_type, values in stored.items()} == {
        form_type: _comparable(form_type, build_field_values(form_type, seeded))
        for form_type in packet(seeded)
    }
    # Only Priya's income is above the median, so only her packet holds 122A-2, and it
    # prints figures worked out from her own expenses.
    assert ("form_122a2" in stored) == (persona == "priya")
    if persona == "priya":
        amounts = [_amount(value) for value in stored["form_122a2"].values()]
        assert any(amount is not None and amount > 0 for amount in amounts)
```

For each persona, the test seeds the persona's session, then has a fresh user send the same data through the API, and requires every stored form to hold exactly the values built from the seeded session. The module docstring states its limit (spec §10): it sends what this file sends, so it can't catch a page that sends a field under the wrong name.

- [ ] **Step 2: Run the read-back**

Nothing can be red before the code: this commit adds only the test, and Tasks 5 and 6 already fixed the two fields it was written to catch.

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/forms/tests/test_api_readback.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `5 passed`, one for each persona.

- [ ] **Step 3: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2a.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -3)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `1676 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  287 passed (287)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 4: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_api_readback.py
git commit -F - <<'MSG'
test(forms): build each persona's forms through the API and compare them with the seeds

The seeds write the database directly, so the oracle never sees a field the API drops
on the way in. The phone number and the secured flag were lost that way (DIG-140,
spec section 7.6).

For each of the five personas the new test sends the seed's data, typed $0 amounts
included, through the endpoints the wizard and the pages after it call: one session
save per step, empty contracts and codebtors lists, Complete, the means test, the
fee-waiver application (Maria, DeShawn, Sarah), the SOFA save (Maria), then Generate
All. Every form's stored values must equal the values built from the seeded session.
Form 107's repeat-group rows compare in any order, because stored rows have no fixed
order (DIG-164). Only Priya's packet holds 122A-2, and it prints her own figures.
MSG
git status --short
```
