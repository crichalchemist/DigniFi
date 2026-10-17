# Forms Step 3a1 (Data Foundations) Implementation Plan, Part 2 of 2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay step 3's foundations. The forms use the U.S. Trustee's median table in force on the day they are filled. Complete and every refusal name the step or page that fixes them. A new asset or debt keeps one id across every save. An unconfirmed scanned debt never prints. Saves on one session take a lock. A sixth persona, Andrés Kettleby, joins the seed and the journeys. The other five personas' private creditors get fictional names, and the site links to its source code.

**Architecture:** One dated-table model (`DatedTable`, `in_force`, `fill_date` in `backend/apps/districts/dated_tables.py`) replaces the median's `latest()` lookup, and the root conftest pins the fill date for every backend test. Refusals carry the wizard step or page that fixes them, from the registry's preconditions through Complete's 400 to the wizard's Review step and the dashboard. The session save returns a sent list in sent order, so the wizard merges new ids by a browser-only row key. `DebtInfo.objects.confirmed()` feeds every form and the means test. `lock_session` (`select_for_update`) guards every intake-data write, and Postgres-only tests prove it in CI. Each of the 12 tasks is one commit, and every task boundary passes every gate.

**This part:** Tasks 7–12. It starts where Part 1 ends, with Tasks 1–6 committed on this branch. The other parts: Part 1 (`docs/superpowers/plans/2026-10-16-forms-step3a1-part1.md`, Tasks 1–6). The plan is split only to stay under the repository's 500 KB file limit. Run all parts as one execution: one ledger for Tasks 1–12, and the whole-branch final review only after Task 12, because each part's patches expect each file exactly as the earlier tasks leave it.

**Tech Stack:** Django 5.0 + DRF (Python 3.11), PostgreSQL 15, pytest + pytest-django; React 19 + TypeScript, vitest + MSW; Playwright; GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-16-forms-step3a1-design.md` (approved by the owner 2026-10-16), drawn from the step 3 umbrella spec `docs/superpowers/specs/2026-10-16-forms-step3-design.md` §5.3 and the persona targets `docs/superpowers/specs/2026-10-16-forms-step3-personas.md`. Read the 3a1 spec in full before Task 1. It is the authority this plan argues from.

**How this plan was checked:**

- Each task's code was built and committed in order on the local branch `plan/forms-step3a1`. Each task's gates passed, and an adversarial review approved each commit.
- Some commits changed after their gates or their review, or ran their gates on an earlier tree: Task 2's backend count comes from the tree before its review fixes and a one-line docstring change. Task 3 ran its gates before a prose-only `CLAUDE.md` change. Task 4's journeys ran before its last two fix rounds, which changed only a refused Complete and the dashboard's refusals, paths the journeys never reach. The plan's author, not a reviewer, checked Task 4's last fix (the reasons lose their `aria-labelledby`). Task 5's gates ran before black re-wrapped one test signature. The author, not a reviewer, checked Task 7's three added tests, Task 8's added `CLAUDE.md` sentence on a reply of a different length, and Task 10's three wording changes to Andrés's brief. After their reviews, the author gave Task 11's journey a 30-second SOFA wait and removed an undefined CSS token from Task 12, then reran the gates and the journeys on both. A reviewer should read these changes in the whole-branch final review.
- The plan was then dry-run from its own text in a fresh worktree, and after every task the tree matched the verified commit exactly.
- Final tree: backend `2166 passed, 25 skipped, 1 xfailed`, the Postgres lock tests `25 passed`, vitest `392 passed`. Journeys: in the dry-run, both runs passed every journey at every task that runs them: 7 of 7 at Tasks 1, 4 and 8, and 8 of 8 at Tasks 11 and 12. In the build, two of Task 1's runs failed while outside work held the load average at 172–325, and passed once it dropped; twice, with the load above 20, Andrés's second run missed the SOFA heading within 5 seconds, which Task 11's 30-second wait (R11-a) now covers.

## Global Constraints

- **The fill date.** Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago. The root `backend/conftest.py` pins it to 2026-10-16 for every backend test (spec §3.3). The dev server, the seed and the journeys use the real date.
- **November 1, 2026.** The fixture's newest median row runs to 2026-10-31. From 2026-11-01 the forms, the means test, `seed_demo_data` and the journeys refuse until the November table is loaded (`docs/REFERENCE_TABLES.md`). Run the journeys before then, or load the November table first.
- **Filer-facing words** are information, never advice (`docs/UPL_COMPLIANCE.md`), in plain language (`docs/PLAIN_LANGUAGE_GUIDE.md`). Where the spec gives a sentence, the code uses it word for word.
- **Never log filer data.** Logs reach Sentry (DIG-105). Log types, table names, dates and district codes only.
- **Shape changes:** before changing a function's signature, return shape, exception or response body, grep every caller and update them in the same commit.
- **Tests are named for the outcome they protect**, mock boundaries and never logic, and a test the change breaks is fixed in the same commit.
- **No new dependencies** (Python or npm), and no date-freezing library.
- **Test data** is synthetic only: SSNs from the IRS-reserved 900 range, new phone numbers from 555-0100–0199, and no real person's or private firm's name in persona data (government creditors keep their real names).
- **Encryption:** any new field holding a filer's personal data is encrypted from the start.
- **CLAUDE.md gotchas** that a task makes false are updated in that task's commit.
- **Gates:** every commit leaves backend pytest with coverage at 90% or more, `manage.py check`, ruff 0.8.5, vitest, tsc, eslint and prettier green. From Task 6, the Postgres lock tests pass too. The journeys run on Tasks 1, 4, 8, 11 and 12.
- **Lint:**
  - ruff 0.8.5 (`ruff check backend/`, as CI runs it).
  - Pre-commit runs black 24.10.0 (line length 100) on `backend/`, prettier 3.4.2 on JSON, Markdown, CSS and TypeScript outside `backend/` (not YAML; `check-yaml` parses it), and eslint on the frontend.
- **Never run `tsc -b`.** It writes build output through the `node_modules` symlink into the main checkout. Use `tsc -p tsconfig.app.json --noEmit` and `tsc -p tsconfig.node.json --noEmit`.
- **Commit messages** end with the last line about the change. **Add no `Co-Authored-By`, `Claude-Session` or other agent trailer, even if your harness asks for one.**
- **Staging:** stage files by explicit path only, never with `git add -A`, `git add .` or `git commit -a`. Commit only the files the task lists.
- **No outward actions:** no push, PR, merge, deploy or production command. Those are the owner's decisions. Nothing in 3a1 deploys: production waits for steps 3–5 and DIG-146.
- **Databases:** never use the shared development database `dignifi_dev`. This plan makes its own.
- **Keys:** never print, log or commit an API key. This plan does not use the repo-root `.env`; the journeys use a dummy key against a fake OpenAI server.

## Before you start (once per worktree)

- Work in `/Volumes/Containers/DigniFi/.claude/worktrees/forms-step3` (branch `feat/forms-step3a1`, which holds the 3a1 spec). Every command block runs from that worktree's root.
- Backend tools come from the main checkout's virtualenv, and frontend tools from its `node_modules`. Pre-commit's eslint hook expects that symlink.
- The journeys and the Postgres lock tests need Colima running, with the `dignifi-db-1` Postgres container answering on host port 5433. The journeys also need nothing listening on ports 8000, 5173 or 4010.
- `pytest` uses `config.settings.test` (sqlite in memory). From Task 6, the Postgres lock tests use `config.settings.test_postgres`, which reads `DATABASE_URL`. `manage.py` and the journeys use the database below.

```bash
set -eo pipefail
mkdir -p backend/logs .claude   # the audit log handler needs backend/logs; CI creates it too
[ -e frontend/node_modules ] || ln -s /Volumes/Containers/DigniFi/frontend/node_modules frontend/node_modules
# CI's synthetic Fernet key (it encrypts nothing real), read from ci.yml rather than copied here
FERNET=$(sed -n 's/^ *FIELD_ENCRYPTION_KEY: //p' .github/workflows/ci.yml | head -1)
[ -n "$FERNET" ]
# A database of its own keeps the shared dev database on develop's migrations. The Postgres
# lock tests (Task 6 on) create and drop their own test database beside it.
docker exec dignifi-db-1 dropdb -U dignifi --if-exists dignifi_forms_step3a1
docker exec dignifi-db-1 createdb -U dignifi dignifi_forms_step3a1
cat > .claude/forms-step3a1.env <<ENV
# Settings for forms step 3a1 (git-ignored). Source from the worktree root.
export PY=/Volumes/Containers/DigniFi/backend/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_forms_step3a1
export DJANGO_SECRET_KEY=test-only-not-a-secret
export DEBUG=True
export ALLOWED_HOSTS=localhost,127.0.0.1
export CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
export FIELD_ENCRYPTION_KEY=$FERNET
export OCR_PROVIDER=openai
export OPENAI_API_KEY=e2e-dummy-key
export OPENAI_BASE_URL=http://127.0.0.1:4010/v1
ENV
source .claude/forms-step3a1.env && $PY -c "import pypdf; assert pypdf.__version__ == '6.13.1', pypdf.__version__"
git check-ignore -q .claude/forms-step3a1.env && git check-ignore -q .claude/e2e.sh && echo "env file is ignored"
```

Expected: `env file is ignored`.

The journeys run through one script, which every task marked for them calls. Write it now:

```bash file=.claude/e2e.sh
#!/bin/zsh
# Run the Playwright journeys on this worktree's own database.
# usage (from the worktree root): zsh .claude/e2e.sh [runs=2]
# Migrates, loads the district data, reseeds the personas, starts runserver (:8000)
# and Vite (:5173), runs the journeys RUNS times, prints one summary line per run,
# and always stops both servers. Logs: .claude/e2e-logs/.
set -u
RUNS=${1:-2}
cd "$(git rev-parse --show-toplevel)" || exit 2
source .claude/forms-step3a1.env
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

It migrates the step's database, loads the district data, reseeds the personas, starts the backend on :8000 and Vite on :5173, runs every journey in `frontend/e2e/journeys/` `RUNS` times, prints one line per run, and always stops both servers. Its logs land in `.claude/e2e-logs/`. A failed run prints the failing journeys; read the trace under `frontend/test-results/` before running again, and don't retry blindly. Journeys are sensitive to machine load: under a load average far above the core count, Generate All can outrun the dashboard's 60-second wait. Check `uptime` before blaming the task.

Check that Part 1 is in place: Task 6's commit is on this branch. Review fixes may have added commits after it.

```bash
set -eo pipefail
git log --format=%s fae6e6c..HEAD | grep -Fx "fix(intake): one save at a time on a session" >/dev/null
echo "Part 1 is in place"
```

Expected: `Part 1 is in place`. If the block fails instead, Task 6 isn't committed: finish Part 1 first.

Check the baseline before Task 7:

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2129 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  379 passed (379)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

## How to read the code blocks

- **`<language> file=<path>` blocks:** the block is the file's complete content. Create or overwrite the file with exactly that text.
- **`bash` blocks:** run from the worktree root in a fresh shell (bash or zsh). Each block starts with `set -eo pipefail`, so any command that fails, including one inside a pipeline, stops the block and fails it. A block sources `.claude/forms-step3a1.env` itself when it needs it.
- **`git apply <<'PATCH'` blocks:** these patch the state the previous task left. If one doesn't apply, stop: the tree has drifted from the plan.
- **"Expected:" lines** say what the command must do. An "Expected: FAIL" step is the red half of test-first. Every other step must succeed.
- **Commit blocks** use each task's verified commit message. A pre-commit hook that rewrites a file means the tree has drifted from the plan: stop and compare.

## Decisions already made

These rulings were settled while the plan was built: by the owner where marked, otherwise by the plan's author against the spec. Every task's code already follows them. Don't reopen them in review. A task that depends on one repeats it in its own text.

- **Twelve tasks, one commit each, in this order.** The median fix is the first commit (spec §1). Every task boundary passes every gate.
- **The owner's calls (spec §2).** 3a1.Q1: Andrés's net driving income, $3,370 a month, is `monthly_other_income` until 3e2. 3a1.Q2: he files no fee-waiver application until 3f, and his journey goes from `/fee-waiver` to `/sofa` and `/forms` by URL, expecting 14 forms.
- **R1-a, the lookup never falls back.** `in_force` takes the newest row whose `effective_date` is on or before the fill date, and refuses when that row's `valid_through` has passed or no row has started. It never looks at an older row. The spec says "It never falls back to an older table"; a filter on both dates alone would let an older open-ended row stand in.
- **R1-b.** `docs/REFERENCE_TABLES.md` names the operator by role, "the project owner".
- **R1-c.** `seed_demo_data` checks that a median table is in force before `--reset` deletes anything, so a refused reseed never wipes the demo personas.
- **R4-a.** The dashboard never shows a second "Finish your intake" link: at most one shows in every state.
- **R4-b.** The dashboard's load-error block offers "Finish your intake" only for a refusal that carries a `step` or `page`. `NoTableInForce` carries neither (spec §4.3), so it shows its sentence alone.
- **R4-c.** `calculate_means_test` puts `error` on its 400 only for the two plain-words refusals, `IncomeNotSplit` and `NoTableInForce`. Any other `ValueError` gets `message` only. The wizard's preview shows `error` when there is one, and otherwise the estimate message. This is the forms views' `_failure` pattern.
- **R4-d.** The Review step's reasons have no accessible name of their own. A polite live region, present before the reasons arrive, announces them.
- **R6-a.** The first lock test is two concurrent contracts PUTs, a double Continue on step 6. Two session PATCHes already serialize on the session row each one writes first, so a test built on them passes without the lock.
- **R6-b.** `config/settings/test_postgres.py` keeps its name. The root conftest's `collect_ignore` stops pytest from collecting it, since the name matches `test_*.py`.
- **R7-a.** Ordinary reads still sort rows on ciphertext (DIG-164, for 3b). So some of Task 7's tests can pass at red by chance; the red step's Expected names only the test that always fails. Their green is exact.
- **R8-a.** A new wizard row's key comes from a counter (`new-<n>`), not `crypto.randomUUID()`, which exists only in secure contexts. A self-hoster who opens DigniFi from another device over plain HTTP would otherwise hit an error on the Assets and Amounts Owed steps.
- **R11-a.** Andrés reaches the SOFA page by a full reload, so its heading waits on the token refresh, the session read and the SOFA read. His journey gives that one wait 30 seconds instead of the default 5; every other journey keeps the default.

## Spec coverage

The 3a1 spec's sections map to tasks as follows.

| Spec                                                                                                                                                | Task                                                                      |
| --------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| §3.1–§3.5, §3.7, §3.8: dated tables, the fill date, the April 2026 median, the refusal, `docs/REFERENCE_TABLES.md`, the figures that move (DIG-274) | 1                                                                         |
| §3.6: the dashboard's notice naming the median table                                                                                                | 2                                                                         |
| §4.1–§4.3: Complete names each gap's step, and forms refusals carry `step` or `page` (DIG-181)                                                      | 3                                                                         |
| §4.4: the Review step lists each reason with a way to its step, and the dashboard links a refusal's page                                            | 4                                                                         |
| §6: unconfirmed scanned debts never print, and Complete refuses while one remains (DIG-163)                                                         | 5                                                                         |
| §7: one save at a time on a session, and the Postgres lock tests in CI (DIG-188)                                                                    | 6                                                                         |
| §5.2, server side: a session save returns a sent list in sent order (DIG-273)                                                                       | 7                                                                         |
| §5, wizard side: new assets and debts keep one id across every save (DIG-273)                                                                       | 8                                                                         |
| §9: fictional names for the five personas' private creditors                                                                                        | 9                                                                         |
| §2 and §8: Andrés Kettleby's seed, readback and tier 3 cases                                                                                        | 10                                                                        |
| §8: Andrés's journey, income typed by source, and the persona and journey counts                                                                    | 11                                                                        |
| §10: the source code link in the footer                                                                                                             | 12                                                                        |
| §11: `CLAUDE.md` gotchas and the README counts                                                                                                      | each task that changes the behaviour a gotcha describes; the counts in 11 |
| §12: tests named for outcomes; the gates                                                                                                            | every task                                                                |
| §13: not in 3a1                                                                                                                                     | none (the plan adds nothing it lists)                                     |
| §14: defects found while scoping                                                                                                                    | filed in Plane before the plan; none is fixed here unless a task names it |

---

### Task 7: Return the rows a session save was sent in the order they were sent

_Built and verified as commit `07673dc` on `plan/forms-step3a1`._

**Files:**

- Modify: `CLAUDE.md`
- Modify: `backend/apps/intake/serializers.py`
- Modify: `backend/apps/intake/tests/test_session_lock.py`
- Modify: `backend/apps/intake/tests/test_session_nested_save.py`
- Modify: `backend/apps/intake/views.py`

**Interfaces:**

- Consumes:
  - `_save_rows_by_id(session, model, rows)` in `backend/apps/intake/serializers.py`, which upserts a session's nested assets or debts, or its contracts or codebtors, by id, and deletes the stored rows the list left out. Its callers are `IntakeSessionSerializer.update` and, in `backend/apps/intake/views.py`, `_save_list` (the contracts and codebtors PUT), which ignores its return.
  - `IntakeSessionSerializer.update`, which Task 6's `IntakeSessionViewSet.update` reaches through `serializer.save()`, and the serializer's `assets` and `debts` fields, which a read builds in model order.
  - `IntakeSessionViewSet.partial_update` (`backend/apps/intake/views.py`), which saves through `update` and then clears `is_draft` on the session's debts when the request carried `debts`.
  - Task 6's wrapper `first_save_pauses_before_commit` in `backend/apps/intake/tests/test_session_lock.py`, which replaces `apps.intake.views._save_rows_by_id`.
  - The `filer` and `other_session` fixtures, `_session_url`, and the imports `Decimal`, `AssetInfo` and `DebtInfo` already in `backend/apps/intake/tests/test_session_nested_save.py`.
- Produces:
  - `_save_rows_by_id(session, model, rows) -> list`: the saved rows in payload order, each with its `pk`. A row sent with another session's id or an unknown one is created, so it appears at its own position with a new id. A stored row the list left out is deleted and is not in the list.
  - `instance.sent_rows: dict`, set by `IntakeSessionSerializer.update` on the session it saves: `"assets"` or `"debts"` maps to that list's saved rows, and only for a list the request carried. A read that did no save has no `sent_rows`.
  - `IntakeSessionSerializer.to_representation`: for each key of `sent_rows`, the field is rendered from the saved rows, so a session PATCH or PUT that carried `assets` or `debts` answers with that list in sent order, each row with its `id`. Every other read, and a list the save did not carry, stays in model order (DIG-164 stays for step 3b).
  - `partial_update` sets `is_draft` to `False` on each debt it returns, so the PATCH response matches the stored rows.
  - Task 8's wizard relies on this: it pairs each row it sent with the response row at the same index and writes the response's `id` into the row it sent, so a new row keeps one id across every later save.
  - Tests in `backend/apps/intake/tests/test_session_nested_save.py`: `test_a_save_hands_back_new_debts_in_the_order_they_were_sent_with_their_ids`, `test_a_save_hands_back_assets_in_the_order_they_were_sent`, `test_a_row_sent_with_another_filers_id_comes_back_at_its_place_with_a_new_id`, `test_a_later_read_keeps_model_order_after_a_save_in_sent_order`, `test_a_save_carrying_only_assets_leaves_the_debts_in_model_order` and `test_a_stored_debt_left_out_of_the_sent_list_is_deleted_and_not_returned`.
  - `CLAUDE.md`: the gotcha "Nested debts and assets save by id" says a session PATCH or PUT returns a sent list in sent order, each row with its id.

**Decisions already made in this task:**

- Only the save that carried the list gets it back in sent order. Every other read keeps model order, because DIG-164 (the lists have no defined order) stays for step 3b. `sent_rows` is an attribute on the instance, not a model field, so it never outlives the request.
- `partial_update` sets `is_draft` to `False` on the debts it returns. Before this commit the PATCH response showed scanned debts as drafts, because the response was built before the clear. It patches `response.data` rather than refreshing the rows, which would cost a query for the same answer. A PUT does not clear `is_draft`, and this task leaves that as it is.
- Task 6's lock-test wrapper now returns the wrapped value, so a wrapped save still returns its rows. The contracts save ignores the return, so the lock tests pass either way.
- The test of a stored debt left out of the sent list can't go red without breaking the delete itself: the response is built from the sent rows, so a surviving row would show only in the `exists()` assertion. It guards the delete and the response together.

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/tests/test_session_lock.py b/backend/apps/intake/tests/test_session_lock.py
index 0d9c127..0e565e6 100644
--- a/backend/apps/intake/tests/test_session_lock.py
+++ b/backend/apps/intake/tests/test_session_lock.py
@@ -189,10 +189,11 @@ def test_two_saves_of_the_same_new_contract_store_it_once(ready):
     save_rows = intake_views._save_rows_by_id

     def first_save_pauses_before_commit(*args, **kwargs):
-        save_rows(*args, **kwargs)
+        saved = save_rows(*args, **kwargs)
         if not first_saved.is_set():
             first_saved.set()
             go_on.wait(WAIT)
+        return saved

     def save():
         return _client(user).put(_session_url(session, "contracts/"), [NEW_CONTRACT], format="json")
diff --git a/backend/apps/intake/tests/test_session_nested_save.py b/backend/apps/intake/tests/test_session_nested_save.py
index a6b0123..9aa99a6 100644
--- a/backend/apps/intake/tests/test_session_nested_save.py
+++ b/backend/apps/intake/tests/test_session_nested_save.py
@@ -268,3 +268,121 @@ def test_a_nested_row_carrying_another_users_row_id_never_changes_that_row(filer
     own = DebtInfo.objects.get(session=session)
     assert own.creditor_name == "Owner Clinic"
     assert own.pk != their_debt.pk
+
+
+def _new_debt(name, amount):
+    return {"creditor_name": name, "debt_type": "credit_card", "amount_owed": amount}
+
+
+def test_a_save_hands_back_new_debts_in_the_order_they_were_sent_with_their_ids(filer):
+    # The wizard pairs each row it sent with the response row at the same index, so a
+    # new row learns its id and keeps it on every later save (DIG-273).
+    client, session = filer
+    kept = DebtInfo.objects.create(
+        session=session, creditor_name="Kept", debt_type="medical", amount_owed=Decimal("40.00")
+    )
+    sent = [
+        _new_debt("First new", "10.00"),
+        {"id": kept.pk, **_new_debt("Kept", "40.00")},
+        _new_debt("Second new", "900.00"),
+        _new_debt("Third new", "5.00"),
+        _new_debt("Fourth new", "300.00"),
+    ]
+
+    response = client.patch(_session_url(session), {"debts": sent}, format="json")
+
+    assert response.status_code == 200
+    assert [row["creditor_name"] for row in response.data["debts"]] == [
+        row["creditor_name"] for row in sent
+    ]
+    assert response.data["debts"][1]["id"] == kept.pk
+    stored = {debt.creditor_name: debt.pk for debt in DebtInfo.objects.filter(session=session)}
+    assert [row["id"] for row in response.data["debts"]] == [
+        stored[row["creditor_name"]] for row in sent
+    ]
+    assert all(row["is_draft"] is False for row in response.data["debts"])
+
+
+def test_a_save_hands_back_assets_in_the_order_they_were_sent(filer):
+    client, session = filer
+    sent = [
+        {"asset_type": "vehicle", "description": name, "current_value": value}
+        for name, value in [("A", "10.00"), ("B", "7000.00"), ("C", "300.00"), ("D", "55.00")]
+    ]
+
+    response = client.patch(_session_url(session), {"assets": sent}, format="json")
+
+    assert [row["description"] for row in response.data["assets"]] == ["A", "B", "C", "D"]
+    stored = {a.description: a.pk for a in AssetInfo.objects.filter(session=session)}
+    assert [row["id"] for row in response.data["assets"]] == [stored[n] for n in "ABCD"]
+
+
+def test_a_row_sent_with_another_filers_id_comes_back_at_its_place_with_a_new_id(
+    filer, other_session
+):
+    client, session = filer
+    theirs = DebtInfo.objects.create(
+        session=other_session,
+        creditor_name="Their Bank",
+        debt_type="credit_card",
+        amount_owed=Decimal("900.00"),
+    )
+    sent = [
+        _new_debt("Mine first", "1.00"),
+        {"id": theirs.pk, **_new_debt("Mine second", "75.00")},
+        _new_debt("Mine third", "2.00"),
+    ]
+
+    response = client.patch(_session_url(session), {"debts": sent}, format="json")
+
+    names = [row["creditor_name"] for row in response.data["debts"]]
+    assert names == ["Mine first", "Mine second", "Mine third"]
+    assert theirs.pk not in [row["id"] for row in response.data["debts"]]
+    assert len({row["id"] for row in response.data["debts"]}) == 3
+
+
+def test_a_later_read_keeps_model_order_after_a_save_in_sent_order(filer):
+    client, session = filer
+    sent = [_new_debt(f"Debt {i}", f"{i * 37}.00") for i in range(1, 6)]
+    client.patch(_session_url(session), {"debts": sent}, format="json")
+
+    read = client.get(_session_url(session))
+
+    assert [row["id"] for row in read.data["debts"]] == [
+        debt.pk for debt in DebtInfo.objects.filter(session=session)
+    ]
+
+
+def test_a_save_carrying_only_assets_leaves_the_debts_in_model_order(filer):
+    client, session = filer
+    for i in range(1, 6):
+        DebtInfo.objects.create(
+            session=session,
+            creditor_name=f"Debt {i}",
+            debt_type="credit_card",
+            amount_owed=Decimal(f"{i * 37}.00"),
+        )
+    sent = [
+        {"asset_type": "vehicle", "description": name, "current_value": value}
+        for name, value in [("A", "10.00"), ("B", "7000.00"), ("C", "300.00")]
+    ]
+
+    response = client.patch(_session_url(session), {"assets": sent}, format="json")
+
+    assert [row["description"] for row in response.data["assets"]] == ["A", "B", "C"]
+    assert [row["id"] for row in response.data["debts"]] == [
+        debt.pk for debt in DebtInfo.objects.filter(session=session)
+    ]
+
+
+def test_a_stored_debt_left_out_of_the_sent_list_is_deleted_and_not_returned(filer):
+    client, session = filer
+    left_out = DebtInfo.objects.create(
+        session=session, creditor_name="Left out", debt_type="medical", amount_owed=Decimal("40.00")
+    )
+    sent = [_new_debt("Only new", "10.00")]
+
+    response = client.patch(_session_url(session), {"debts": sent}, format="json")
+
+    assert [row["creditor_name"] for row in response.data["debts"]] == ["Only new"]
+    assert not DebtInfo.objects.filter(pk=left_out.pk).exists()
PATCH
```

The tests send lists of new rows with a stored row or another filer's row among them, and compare the response's names and ids with the order sent and with the ids the database assigned. The one-line change to `test_session_lock.py` is Task 6's wrapper: it now returns the rows the wrapped `_save_rows_by_id` returns. That file runs only on Postgres, so the Postgres run in step 7 checks it.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest apps/intake/tests/test_session_nested_save.py -q -p no:cacheprovider 2>&1 | tail -15
```

Expected: FAIL — `test_a_save_hands_back_new_debts_in_the_order_they_were_sent_with_their_ids` fails. A save answers with its rows in model order, so a list comes back out of the order it was sent. The later-read guard and the left-out-row test pass, because they hold behavior the change must keep. Model order puts the rows by an encrypted amount, which differs on every run, so the assets test, the assets-only test and the foreign-id test each fail on some runs and pass on others: two to four tests fail in all.

- [ ] **Step 3: Return the saved rows in the order they were sent**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/serializers.py b/backend/apps/intake/serializers.py
index 684a42f..1424802 100644
--- a/backend/apps/intake/serializers.py
+++ b/backend/apps/intake/serializers.py
@@ -221,28 +221,31 @@ class NestedDebtInfoSerializer(DebtInfoSerializer):
     id = serializers.IntegerField(required=False)


-def _save_rows_by_id(session, model, rows) -> None:
+def _save_rows_by_id(session, model, rows) -> list:
     """Save a session's nested assets or debts, or its contracts or codebtors list, by id.

     A row whose id is one of this session's rows updates only the fields it sent, so
     what the browser never received (account numbers, the scanned-bill link)
     survives. Any other row is created on this session, so a client-sent
     ``session`` or another user's id never touches another session. Stored rows the
-    payload left out are deleted.
+    payload left out are deleted. Returns the saved rows in payload order, each with its id.
     """
     existing = {row.pk: row for row in model.objects.filter(session=session)}
     kept = set()
+    saved = []
     for data in rows:
         data.pop("session", None)
         row = existing.get(data.pop("id", None))
         if row is None:
-            model.objects.create(session=session, **data)
+            saved.append(model.objects.create(session=session, **data))
             continue
         for attr, value in data.items():
             setattr(row, attr, value)
         row.save()
         kept.add(row.pk)
+        saved.append(row)
     model.objects.filter(pk__in=existing.keys() - kept).delete()
+    return saved


 # The intake sections a session save can carry (spec §5.3).
@@ -362,14 +365,23 @@ class IntakeSessionSerializer(serializers.ModelSerializer):
         if expense_data is not None:
             ExpenseInfo.objects.update_or_create(session=instance, defaults=expense_data)

+        # The response lists a sent list in sent order, so the wizard can pair each row it
+        # sent with its id (DIG-273). Every other read keeps model order.
+        instance.sent_rows = {}
         if assets_data is not None:
-            _save_rows_by_id(instance, AssetInfo, assets_data)
+            instance.sent_rows["assets"] = _save_rows_by_id(instance, AssetInfo, assets_data)

         if debts_data is not None:
-            _save_rows_by_id(instance, DebtInfo, debts_data)
+            instance.sent_rows["debts"] = _save_rows_by_id(instance, DebtInfo, debts_data)

         return instance

+    def to_representation(self, instance):
+        data = super().to_representation(instance)
+        for name, rows in getattr(instance, "sent_rows", {}).items():
+            data[name] = self.fields[name].to_representation(rows)
+        return data
+

 class FeeWaiverApplicationSerializer(serializers.ModelSerializer):
     """The fee-waiver page's answers (forms step 2 spec §5.7).
PATCH
```

`_save_rows_by_id` returns the rows it created or updated in payload order, and `update` keeps the assets' and debts' rows on `instance.sent_rows`. `to_representation` renders those two fields from them, so only the save that carried a list gets it back in sent order. Rows a list left out are deleted before the return, so they never appear.

- [ ] **Step 4: Show the returned debts as confirmed**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/views.py b/backend/apps/intake/views.py
index 7146744..270fbed 100644
--- a/backend/apps/intake/views.py
+++ b/backend/apps/intake/views.py
@@ -165,6 +165,8 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         response = super().partial_update(request, *args, **kwargs)
         if "debts" in request.data:
             DebtInfo.objects.filter(session=instance, is_draft=True).update(is_draft=False)
+            for debt in response.data["debts"]:
+                debt["is_draft"] = False
         return response

     def perform_create(self, serializer):
PATCH
```

`partial_update` builds its response before it clears `is_draft`, so a scanned debt came back as a draft while the database already held it as confirmed. The loop sets the flag on every returned debt, which is every debt of the session, the same rows the clear updated.

- [ ] **Step 5: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest apps/intake/tests/test_session_nested_save.py -q -p no:cacheprovider 2>&1 | tail -15
```

Expected: `13 passed`.

- [ ] **Step 6: Say in CLAUDE.md that a save returns its lists in sent order**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index f450dcf..89d2978 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -23,7 +23,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **React 19 + navigate()** — calling `navigate()` in render body crashes the reconciler. Use `useEffect`.
 - **Vite HMR in Docker** — type/structure changes don't hot-reload; restart the frontend container.
 - **Enum mismatches are silent** — frontend/backend enum drift only surfaces at runtime; check both when adding fields.
-- **Nested debts and assets save by id** — `IntakeSessionSerializer.update` upserts `debts`/`assets` through `_save_rows_by_id`: a row carrying one of this session's ids updates only the keys it sends, a row without one (or with an unknown or foreign id) is created on this session, and a stored row missing from the payload is **deleted**, so send every row you want to keep. A nested `session` is ignored. Fields the browser never receives (`account_number`, `source_document`) survive a re-save. `DebtViewSet`/`AssetViewSet` keep the base serializers, so per-item create never takes a client id. Contracts and codebtors save the same way, as a whole list: `PUT /intake/sessions/{id}/contracts/` (or `codebtors/`) checks every row before writing any, and an empty list deletes every stored row. The wizard sends each list on Continue from steps 6 and 7, and reads both with the session before any step shows, so a list that failed to load is never saved as empty.
+- **Nested debts and assets save by id** — `IntakeSessionSerializer.update` upserts `debts`/`assets` through `_save_rows_by_id`: a row carrying one of this session's ids updates only the keys it sends, a row without one (or with an unknown or foreign id) is created on this session, and a stored row missing from the payload is **deleted**, so send every row you want to keep. A nested `session` is ignored. A session PATCH or PUT that carries `assets` or `debts` returns that list in the order it was sent, each row with its id (a new row, or one sent with a foreign or unknown id, shows its new id), so the wizard can pair rows by position and keep a new row's id; every other read keeps model order (DIG-164). Fields the browser never receives (`account_number`, `source_document`) survive a re-save. `DebtViewSet`/`AssetViewSet` keep the base serializers, so per-item create never takes a client id. Contracts and codebtors save the same way, as a whole list: `PUT /intake/sessions/{id}/contracts/` (or `codebtors/`) checks every row before writing any, and an empty list deletes every stored row. The wizard sends each list on Continue from steps 6 and 7, and reads both with the session before any step shows, so a list that failed to load is never saved as empty.
 - **Saves lock the session** — every write to a session's intake data first calls `lock_session` (`apps/intake/locking.py`, `select_for_update` on the session row) inside the same `transaction.atomic()` block as the write, so a second save of the same session waits for the first to commit and then reads what it stored (DIG-188). That covers the session PATCH and PUT, `update_step`, `complete` (which writes only `status` and `completed_at`), the contracts and codebtors PUT, POST and DELETE, the `DebtViewSet`/`AssetViewSet` writes, a scanned bill's correction and an upload's findings. Call `get_object()` before locking (another user's session is a 404), and lock before reading anything the write depends on. An upload locks only in its worker thread, around the write of its findings, after the call to the hosted model: the upload request waits for that thread, so a lock taken in the request deadlocks. `select_for_update` does nothing on sqlite, so the backend suite can't see a missing lock; only `apps/intake/tests/test_session_lock.py` (marker `postgres`) proves it, and it skips under the default settings. Run it locally with `DJANGO_SETTINGS_MODULE=config.settings.test_postgres pytest -m postgres`, with `DATABASE_URL` naming a Postgres whose user can create the test database; CI runs it in the backend job against its Postgres service. `test_postgres` sets a 10-second `lock_timeout`, so a deadlock fails a test instead of hanging the run.
 - **Debt and asset amounts are readable, as strings** — the owner gets `DebtInfo.amount_owed` and `AssetInfo.current_value`/`amount_owed` back (SSN and `account_number` stay write-only). DRF sends decimals as strings (`"2500.00"`), so the wizard converts them with `hydrateAmounts` (`utils/parseAmount.ts`) as session data enters step state; a raw string in a step's `reduce` joins as text (`$02500.00100.50`). A stored amount wider than `DecimalField(12, 2)` makes every read of that session 500, so every write path must bound it (`DraftDebtCreator` stores it as 0; documents `validate` returns 400).
 - **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data. It reads the median table in force on today's real date, not the tests' pinned one, and when none is (from November 1, 2026 until the November table is loaded) it prints a message naming `docs/REFERENCE_TABLES.md` and changes nothing, so even `--reset` leaves the existing personas. Personas seeded before income was stored by source must be re-created with `seed_demo_data --reset` (migration 0014 leaves their totals unsplit, and a plain re-run skips existing users).
PATCH
```

- [ ] **Step 7: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2135 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  379 passed (379)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

The 25 skips are Task 6's Postgres-only tests under sqlite. The next command runs them against the Postgres database named in `.claude/forms-step3a1.env`, which checks the lock-test wrapper change.

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

This task changes no page flow, so the journeys don't run. Task 8's wizard change, which uses the response order, runs them.

- [ ] **Step 8: Commit**

```bash
set -eo pipefail
git add \
  CLAUDE.md \
  backend/apps/intake/serializers.py \
  backend/apps/intake/tests/test_session_lock.py \
  backend/apps/intake/tests/test_session_nested_save.py \
  backend/apps/intake/views.py
git commit -F - <<'MSG'
feat(intake): a session save returns the rows it was sent in the same order

A session PATCH or PUT that carries assets or debts now answers with that list
in the order it was sent, each row with its id. The wizard (next commit) pairs
each row it sent with the response row at the same index, so a new row learns
its id and keeps it on every later save. Every other read keeps model order.

_save_rows_by_id returns the saved rows in payload order (the contracts and
codebtors saves ignore it). The serializer keeps them for the response.
partial_update shows the returned debts as confirmed, as the stored rows are
once it has cleared is_draft (views.py): the response was built before the
clear and showed scanned debts as drafts.

The wrapper in test_session_lock.py that widens the race window now returns
the wrapped function's rows, so a wrapped save still returns them.

Refs DIG-273
MSG
git status --short
```

### Task 8: Keep one id for each new asset and debt across every save

_Built and verified as commit `d10c4b2` on `plan/forms-step3a1`._

**Files:**

- Modify: `CLAUDE.md`
- Modify: `frontend/src/components/wizard/steps/AssetsStep.tsx`
- Modify: `frontend/src/components/wizard/steps/DebtsStep.tsx`
- Modify: `frontend/src/components/wizard/steps/__tests__/DebtsStep.test.tsx`
- Modify: `frontend/src/hooks/__tests__/useAutoSave.test.ts`
- Modify: `frontend/src/hooks/useAutoSave.ts`
- Modify: `frontend/src/pages/IntakeWizard.tsx`
- Modify: `frontend/src/pages/__tests__/IntakeWizard.test.tsx`
- Modify: `frontend/src/types/api.ts`

**Interfaces:**

- Consumes:
  - Task 7's session save: a PATCH that carries `assets` or `debts` answers with that list in the order it was sent, each row with its `id`. A row sent without an id, or with an id the session doesn't hold, comes back at its own position with a new id. `api.intake.updateSession(id, body)` (`frontend/src/api/client.ts`) resolves with that session.
  - `useAutoSave({ data, dataKey, onSave, debounceMs, enabled })` (`frontend/src/hooks/useAutoSave.ts`). It compares the JSON of `data` with the copy of a save still on its way under `dataKey` (`sendingCopiesRef`), else with the last saved or loaded copy (`savedCopiesRef`), and saves 2 s after the last change. `saveNow()`, which Continue calls, always saves. Before this task `onSave` was `(data: T) => Promise<void>`, and the copy sent always became the saved copy.
  - In `frontend/src/pages/IntakeWizard.tsx`: the `assetsData` and `debtsData` state; `currentStepBody`, whose Assets body keeps the rows with an `asset_type` and a `description` and whose Amounts Owed body keeps the rows with a `creditor_name`; `saveCurrentStepData(body)`, which PATCHed the body and dropped the reply; the session load, which runs each row through `hydrateAmounts` with `ASSET_AMOUNT_FIELDS` or `DEBT_AMOUNT_FIELDS`; and `useAutoSave({ ..., onSave: (body) => saveCurrentStepData(body) })`.
  - `AssetsStep` and `DebtsStep` (`frontend/src/components/wizard/steps/`), which took `initialData`, `onDataChange` and `onValidationChange`. Each copied `initialData` into local state at mount, or one blank row from `createEmptyAsset` or `createEmptyDebt`, and pushed every change up through an effect.
  - `ReviewStep`, which lists the wizard's rows and shows "No assets listed." or "No amounts owed listed." for an empty list.
  - For the tests: `server` (`src/test/mocks/server`); in `IntakeWizard.test.tsx`, `renderWizard()`, `sessionAtStep1`, `sessionAtStep5WithDebts` and the describe "IntakeWizard amounts a returning filer already entered"; in `DebtsStep.test.tsx`, `baseDebt` and `noop`.
- Produces:
  - `export type WizardRow<T> = Partial<T> & { _key: string }` in `frontend/src/types/api.ts`. `_key` is the browser's own name for a row and never reaches the server: a loaded row's `String(id)`, or `new-<n>` for a new row.
  - `AssetsStep({ rows, onRowsChange, onValidationChange })` and `DebtsStep({ rows, onRowsChange, onValidationChange })`, with `rows: WizardRow<AssetInfo>[]` (or `WizardRow<DebtInfo>[]`) and `onRowsChange: (rows) => void` in place of `initialData` and `onDataChange`. The steps keep no copy of the rows. With `rows` empty, a step shows one blank row, made once per mount by `useState(createEmptyAsset)` (or `createEmptyDebt`), which joins the wizard's rows at the filer's first edit. Each step module has its own `let nextKey = 0`, and `createEmptyAsset` and `createEmptyDebt` set `_key` to the template string `new-${++nextKey}`. The steps' effect reports only validity.
  - `useAutoSave`'s `onSave: (data: T) => Promise<T | void>`. The JSON of a returned copy becomes the saved copy; `undefined` keeps the copy sent, as before.
  - Module-level helpers in `IntakeWizard.tsx`: `withoutKey(row)`, a copy of the row without `_key`; `savedIds(sent, saved)`, a `Map` from each sent row's `_key` to the `id` at the same position in the reply, which throws `Error('The session save did not return each row it was sent')` when the reply's list is missing or a different length; and `withSavedIds(rows, ids)`, which sets `id` on each row whose `_key` is in the map and leaves every other row as it is.
  - `assetsData: WizardRow<AssetInfo>[]` and `debtsData: WizardRow<DebtInfo>[]`. A loaded row gets `_key: String(id)` after its hydrated fields, and `currentStepBody` keeps `_key`.
  - `saveCurrentStepData(body): Promise<Partial<IntakeSession> | void>`. For assets or debts it sends the rows without `_key`, writes the reply's ids into the wizard's rows with a functional updater, and returns `{ ...body, assets: withSavedIds(assets, ids) }` (or `debts`), the copy the server now holds. It returns `undefined` for every other step.
  - Vitest in `src/hooks/__tests__/useAutoSave.test.ts`: `keeps the copy a save returns as the saved copy, so the new ids reaching the data send nothing`.
  - Vitest in `src/pages/__tests__/IntakeWizard.test.tsx`: the helpers `serveSessionSaves(loaded, held = loaded)`, which returns `{ bodies, stored, holdNextReply }`, `field(name)` and `waitSeconds(seconds)`; `describe.each` over debts (step 5) and assets (step 4), titled `IntakeWizard new $list keep one id`, with `saves a new row under one id across autosave, an edit and autosave, once per edit`, `saves a new row under one id across Continue, Go Back, an edit and Continue`, `saves a row sent with an id the server no longer holds under the new id it got` and `drops a row the filer removed while its save was on its way, and keeps the other new row`; and `describe('IntakeWizard a new debt after Complete')` with `keeps a completed intake completed when the filer steps back to the debt they added`.
  - In `src/components/wizard/steps/__tests__/DebtsStep.test.tsx`: fixtures typed `WizardRow<DebtInfo>` with a `_key`, the props `rows` and `onRowsChange`, and `StepWithRows({ onRowsChange })`, which holds the rows for the secured-debt test.
  - `CLAUDE.md`: "Nested debts and assets save by id" describes the controlled steps, the `_key`, the merge and the failed save on a reply of a different length; "Autosave sends only real edits" describes the returned saved copy.

**Decisions already made in this task:**

- **Ruling R8-a: a new row's key comes from a counter, not `crypto.randomUUID()`.** Spec §5.2 says a new row gets a random key. Browsers offer `crypto.randomUUID` only in a secure context (HTTPS, `localhost` or `127.0.0.1`), so someone who runs DigniFi on their own machine and opens it from a phone over plain HTTP would get a TypeError as soon as Assets or Amounts Owed showed a blank row, or at Add. A module-level `let nextKey = 0` in each step gives `new-1`, `new-2` and so on. The counter outlives a remount of the step, so keys stay unique while the page is open, and the `new-` prefix keeps a new row's key apart from a loaded row's, which is its id. The two lists have separate counters, which is safe because ids merge within one list.
- **The steps are controlled and keep no copy of the rows** (spec §5.1–5.2). With a copy in the step, an id written into the wizard's rows would be overwritten by the step's next change, and an id written into the step's copy would be lost when Continue unmounts it. Add, change and remove index into the list on screen (the rows, or the blank row), so Add on an untouched step still gives two rows, as the journeys' page object expects. An untouched Assets step is still valid and an untouched Amounts Owed step still is not.
- **The merge takes only ids from the reply.** `withSavedIds` writes `id` and nothing else, so amounts stay as the filer typed them, as numbers rather than the reply's decimal strings. A row removed while its save was on its way is skipped, and a row sent with a stale or foreign id takes its new id. The state update is a functional updater, so an edit made while the save was in flight is kept.
- **A reply whose list is a different length fails the save.** Pairing by position means nothing then, and a silent fallback would hide the fault. Task 7's server always returns one row per sent row, so only a broken server or mock can trigger it; `useAutoSave` then sets its status to `'error'`. The returning-filer PATCH mock was such a mock: it answered every save with a fixed session whose `assets` list is empty, so under this change the assets test's save failed while the test, which reads only the first PATCH body, still passed. It now answers with the lists it was sent.
- **The merge sends no PATCH.** `saveCurrentStepData` builds the copy it returns from the body with the same `withSavedIds` that updates the rows, so the copy's JSON matches the next body exactly, key order included, and `useAutoSave` keeps it as the saved copy. Showing the step again sends nothing, so a completed intake stays completed. Every other step returns `undefined` and keeps the copy sent.
- **One self-correcting extra PATCH can still go out when two saves overlap by more than 2 s.** `useAutoSave` compares the data with the copy of a save still on its way. Once the first reply's ids reach the rows, the data differs from the second save's copy, which has no ids. If the second reply lands more than 2 s after the first, one more PATCH goes out carrying an id the second save has already replaced, so the server creates the row again and the wizard takes the new id. It costs a round trip and an id, never data. Changing the hook's in-flight comparison is outside this task.
- **Review shows "No assets listed." for an untouched step.** The old steps pushed their blank row into the wizard's state on mount, so a filer who passed Assets without typing saw "Unnamed Asset $0.00" on Review. The blank row now stays in the step until the filer edits it, so Review shows "No assets listed." or "No amounts owed listed.". No test or journey pinned the old text. A blank row added with Add still shows on Review, as before.
- **Cards stay keyed by index** (`key={index}`), to keep the change to the steps' data flow. Every input is controlled from `rows`, the form fields hold no state, and the blank row keeps one `_key` through its first edit, so values and focus behave as before. The only effect is on which card element React reuses when a card other than the last is removed, which was already so.
- **The completed-intake test covers debts only.** Continue from Assets needs a valid Amounts Owed step after it, which means saving a debt too. The first two tests of each list prove that the merge sends no PATCH for both lists.
- **This commit includes one round of fixes and one amend.** The first build keyed new rows with `crypto.randomUUID()`; fix round 1 applied R8-a. After the review, the controller added one sentence to the "Nested debts and assets save by id" gotcha: a reply whose list is a different length from the one sent fails the save (review Minor 4).

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/hooks/__tests__/useAutoSave.test.ts b/frontend/src/hooks/__tests__/useAutoSave.test.ts
index 0d23c46..3d7ea2b 100644
--- a/frontend/src/hooks/__tests__/useAutoSave.test.ts
+++ b/frontend/src/hooks/__tests__/useAutoSave.test.ts
@@ -81,6 +81,35 @@ describe('useAutoSave', () => {
     expect(onSave).not.toHaveBeenCalled();
   });

+  // The wizard returns its rows with the ids the save gave them (DIG-273). Once the ids reach its
+  // data, they must not count as an edit, or each save of a new row would send one more.
+  it('keeps the copy a save returns as the saved copy, so the new ids reaching the data send nothing', async () => {
+    const onSave = vi
+      .fn()
+      .mockResolvedValueOnce({ debts: [{ creditor: 'Elm Street Clinic', id: 101 }] })
+      .mockResolvedValue(undefined);
+    const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
+      initialProps: { data: { debts: [] as Array<{ creditor: string; id?: number }> } },
+    });
+
+    rerender({ data: { debts: [{ creditor: 'Elm Street Clinic' }] } });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(2000);
+    });
+    rerender({ data: { debts: [{ creditor: 'Elm Street Clinic', id: 101 }] } });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(3000);
+    });
+    expect(onSave).toHaveBeenCalledTimes(1);
+
+    // The copy that was sent is no longer what the server holds
+    rerender({ data: { debts: [{ creditor: 'Elm Street Clinic' }] } });
+    await act(async () => {
+      await vi.advanceTimersByTimeAsync(2000);
+    });
+    expect(onSave).toHaveBeenCalledTimes(2);
+  });
+
   it('saves a change back to an earlier value, since the server holds the later one', async () => {
     const onSave = vi.fn().mockResolvedValue(undefined);
     const { rerender } = renderHook(({ data }) => useAutoSave({ data, onSave, debounceMs: 2000 }), {
PATCH
```

A save that returns a copy with an id must make that copy the saved copy: the id reaching the data sends nothing, and going back to the copy that was sent saves again, since the server no longer holds it.

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/IntakeWizard.test.tsx b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
index 6b676e2..51fcf79 100644
--- a/frontend/src/pages/__tests__/IntakeWizard.test.tsx
+++ b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
@@ -925,10 +925,12 @@ describe('IntakeWizard amounts a returning filer already entered', { timeout: 15
       http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
         HttpResponse.json(sessionAtStep5WithDebts)
       ),
-      // Continue saves the step, even when the filer changed nothing.
+      // Continue saves the step, even when the filer changed nothing. A saved list comes back
+      // in the order sent, each row with its id (DIG-273).
       http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
-        patchBodies.push(await request.json());
-        return HttpResponse.json(sessionAtStep5WithDebts);
+        const body = (await request.json()) as Record<string, unknown>;
+        patchBodies.push(body);
+        return HttpResponse.json({ ...sessionAtStep5WithDebts, ...body });
       }),
       http.get('http://localhost:8000/api/intake/sessions/:id/contracts/', () =>
         HttpResponse.json([])
@@ -981,6 +983,336 @@ describe('IntakeWizard amounts a returning filer already entered', { timeout: 15
   });
 });

+// ===========================================================================
+// New assets and debts keep one id (step 3a1 spec §5, DIG-273)
+// ===========================================================================
+
+/**
+ * The session server for one filer. GET sends `loaded`. A PATCH that carries assets or debts
+ * stores that list as sent and returns it in the order sent, each row with its id: a row sent
+ * without an id, or with one the server doesn't hold, gets the next new id, and a stored row left
+ * out is gone. Amounts come back as decimal strings, and any save reopens a completed intake.
+ */
+function serveSessionSaves(
+  loaded: Record<string, unknown>,
+  held: Record<string, unknown> = loaded
+) {
+  let stored = held;
+  let nextId = 101;
+  let heldReply: Promise<void> | null = null;
+  const bodies: Record<string, unknown>[] = [];
+  server.use(
+    http.get('http://localhost:8000/api/intake/sessions/:id/', () => HttpResponse.json(loaded)),
+    http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
+      const body = (await request.json()) as Record<string, unknown>;
+      bodies.push(body);
+      stored = { ...stored, status: 'in_progress' };
+      for (const list of ['assets', 'debts']) {
+        const sent = body[list] as Record<string, unknown>[] | undefined;
+        if (!sent) continue;
+        const heldIds = (stored[list] as Record<string, unknown>[]).map((row) => row.id);
+        stored[list] = sent.map((row) => {
+          const saved: Record<string, unknown> = {
+            ...row,
+            id: heldIds.includes(row.id) ? row.id : nextId++,
+          };
+          for (const amount of ['current_value', 'amount_owed', 'monthly_payment']) {
+            if (typeof saved[amount] === 'number') saved[amount] = saved[amount].toFixed(2);
+          }
+          return saved;
+        });
+      }
+      const reply = HttpResponse.json(stored);
+      if (heldReply) {
+        const wait = heldReply;
+        heldReply = null;
+        await wait;
+      }
+      return reply;
+    }),
+    http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () => {
+      stored = { ...stored, status: 'completed' };
+      return HttpResponse.json({ message: 'Session completed.' });
+    })
+  );
+  return {
+    bodies,
+    stored: () => stored,
+    /** Keeps the next save's reply on its way until the returned function is called */
+    holdNextReply: () => {
+      let release = () => {};
+      heldReply = new Promise<void>((resolve) => {
+        release = resolve;
+      });
+      return release;
+    },
+  };
+}
+
+/** A form control by its name, as the journeys find them */
+function field(name: string) {
+  const control = document.querySelector(`[name="${name}"]`);
+  if (!control) throw new Error(`No control named ${name}`);
+  return control;
+}
+
+/** Moves the fake clock on in 1 s steps, so each save's reply lands before the next timer */
+async function waitSeconds(seconds: number) {
+  for (let second = 0; second < seconds; second += 1) {
+    await act(() => vi.advanceTimersByTimeAsync(1000));
+  }
+}
+
+describe.each([
+  {
+    list: 'debts',
+    step: 5,
+    title: /amounts owed/i,
+    nameKey: 'creditor_name',
+    amountKey: 'amount_owed',
+    removeLabel: 'Remove amount owed 1',
+    addLabel: /add another amount owed/i,
+    fill: (index: number, name: string, amount: string) => {
+      fireEvent.change(field(`debt_type_${index}`), { target: { value: 'credit_card' } });
+      fireEvent.change(field(`creditor_name_${index}`), { target: { value: name } });
+      fireEvent.change(field(`amount_owed_${index}`), { target: { value: amount } });
+    },
+    stored: {
+      id: 7,
+      session: 1,
+      data_source: 'manual',
+      creditor_name: 'Northwind Card Services',
+      debt_type: 'credit_card',
+      priority_classification: 'unsecured',
+      amount_owed: '2500.00',
+      monthly_payment: '75.00',
+      is_in_collections: false,
+      is_secured: false,
+      collateral_description: '',
+      notes: '',
+      is_draft: false,
+      source_document_name: null,
+    },
+  },
+  {
+    list: 'assets',
+    step: 4,
+    title: /assets/i,
+    nameKey: 'description',
+    amountKey: 'current_value',
+    removeLabel: 'Remove asset 1',
+    addLabel: /add another asset/i,
+    fill: (index: number, name: string, amount: string) => {
+      fireEvent.change(field(`asset_type_${index}`), { target: { value: 'vehicle' } });
+      fireEvent.change(field(`description_${index}`), { target: { value: name } });
+      fireEvent.change(field(`current_value_${index}`), { target: { value: amount } });
+    },
+    stored: {
+      id: 3,
+      session: 1,
+      asset_type: 'vehicle',
+      data_source: 'manual',
+      description: 'Family car',
+      current_value: '8000.00',
+      amount_owed: '3000.00',
+      equity: 5000,
+      financial_institution: '',
+    },
+  },
+])(
+  'IntakeWizard new $list keep one id',
+  { timeout: 30_000 },
+  ({ list, step, title, nameKey, amountKey, removeLabel, addLabel, fill, stored }) => {
+    const onStep = { ...sessionAtStep1, current_step: step };
+    const rowsSent = (body: Record<string, unknown>) => body[list] as Record<string, unknown>[];
+    const idsSent = (bodies: Record<string, unknown>[]) =>
+      bodies.map((body) => rowsSent(body).map((row) => row.id));
+
+    beforeEach(() => {
+      server.use(
+        http.post(
+          'http://localhost:8000/api/intake/sessions/:id/update_step/',
+          async ({ request }) => {
+            const { current_step } = (await request.json()) as { current_step: number };
+            return HttpResponse.json({
+              session: { ...onStep, current_step },
+              message: 'Step updated.',
+            });
+          }
+        ),
+        http.post(
+          'http://localhost:8000/api/audit/logs/',
+          () => new HttpResponse(null, { status: 201 })
+        )
+      );
+    });
+
+    // A save of a row without its id replaces the row, and step 3c links rows by id
+    it('saves a new row under one id across autosave, an edit and autosave, once per edit', async () => {
+      const { bodies } = serveSessionSaves(onStep);
+      renderWizard();
+      await screen.findByRole('heading', { name: title, level: 2 });
+
+      vi.useFakeTimers();
+      try {
+        // Each wait outlasts the 2 s autosave delay after the save lands
+        fill(0, 'Elm Street Clinic', '1200');
+        await waitSeconds(5);
+        fireEvent.change(field(`${nameKey}_0`), { target: { value: 'Elm Street Health' } });
+        await waitSeconds(5);
+      } finally {
+        vi.useRealTimers();
+      }
+
+      expect(idsSent(bodies)).toEqual([[undefined], [101]]);
+      const [, second] = bodies.map(rowsSent);
+      expect(second[0][nameKey]).toBe('Elm Street Health');
+      // The amount the filer typed, never the reply's decimal string
+      expect(second[0][amountKey]).toBe(1200);
+      // The browser's own key stays in the browser
+      expect(second[0]).not.toHaveProperty('_key');
+    });
+
+    it('saves a new row under one id across Continue, Go Back, an edit and Continue', async () => {
+      const { bodies } = serveSessionSaves(onStep);
+      const { container } = renderWizard();
+      await screen.findByRole('heading', { name: title, level: 2 });
+
+      vi.useFakeTimers();
+      try {
+        fill(0, 'Elm Street Clinic', '1200');
+        fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
+        await waitSeconds(1);
+        expect(container.querySelector('.step-title')).not.toHaveTextContent(title);
+
+        // Going back sends nothing: the new row's id is already in the saved copy
+        fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
+        await waitSeconds(3);
+        expect(bodies).toHaveLength(1);
+
+        fireEvent.change(field(`${nameKey}_0`), { target: { value: 'Elm Street Health' } });
+        fireEvent.click(screen.getByRole('button', { name: 'Continue' }));
+        await waitSeconds(3);
+      } finally {
+        vi.useRealTimers();
+      }
+
+      expect(idsSent(bodies)).toEqual([[undefined], [101]]);
+    });
+
+    // Another tab, or a save the filer never saw land, can leave the browser with an id the server
+    // no longer holds: the server stores that row under a new id, and the browser must use it
+    it('saves a row sent with an id the server no longer holds under the new id it got', async () => {
+      const { bodies } = serveSessionSaves(
+        { ...onStep, [list]: [stored] },
+        { ...onStep, [list]: [] }
+      );
+      renderWizard();
+      await screen.findByRole('heading', { name: title, level: 2 });
+
+      vi.useFakeTimers();
+      try {
+        fireEvent.change(field(`${nameKey}_0`), { target: { value: 'Edited once' } });
+        await waitSeconds(3);
+        fireEvent.change(field(`${nameKey}_0`), { target: { value: 'Edited twice' } });
+        await waitSeconds(3);
+      } finally {
+        vi.useRealTimers();
+      }
+
+      expect(idsSent(bodies)).toEqual([[stored.id], [101]]);
+    });
+
+    it('drops a row the filer removed while its save was on its way, and keeps the other new row', async () => {
+      const saves = serveSessionSaves(onStep);
+      renderWizard();
+      await screen.findByRole('heading', { name: title, level: 2 });
+      const landSave = saves.holdNextReply();
+
+      vi.useFakeTimers();
+      try {
+        fill(0, 'Elm Street Clinic', '1200');
+        fireEvent.click(screen.getByRole('button', { name: addLabel }));
+        fill(1, 'Harbor Light Dental', '300');
+        await waitSeconds(3);
+        expect(saves.bodies).toHaveLength(1);
+
+        fireEvent.click(screen.getByRole('button', { name: removeLabel }));
+        await act(async () => landSave());
+        await waitSeconds(4);
+      } finally {
+        vi.useRealTimers();
+      }
+
+      expect(idsSent(saves.bodies)).toEqual([[undefined, undefined], [102]]);
+      expect(rowsSent(saves.bodies[1])[0][nameKey]).toBe('Harbor Light Dental');
+      expect(rowsSent(saves.stored())).toEqual([
+        expect.objectContaining({ id: 102, [nameKey]: 'Harbor Light Dental' }),
+      ]);
+    });
+  }
+);
+
+describe('IntakeWizard a new debt after Complete', { timeout: 30_000 }, () => {
+  // Any save reopens a completed intake, and the filer would have to press Complete again. Once a
+  // new debt has its id, stepping back over Amounts Owed must not save it again.
+  it('keeps a completed intake completed when the filer steps back to the debt they added', async () => {
+    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
+    const saves = serveSessionSaves({ ...sessionAtStep1, current_step: 5 });
+    server.use(
+      http.post(
+        'http://localhost:8000/api/intake/sessions/:id/update_step/',
+        async ({ request }) => {
+          const { current_step } = (await request.json()) as { current_step: number };
+          return HttpResponse.json({
+            session: { ...sessionAtStep1, current_step },
+            message: 'Step updated.',
+          });
+        }
+      ),
+      // The means test fails after Complete accepts the intake, so the filer stays on Review
+      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
+        HttpResponse.json({ message: 'Unable to calculate means test.' }, { status: 400 })
+      ),
+      http.post(
+        'http://localhost:8000/api/audit/logs/',
+        () => new HttpResponse(null, { status: 201 })
+      )
+    );
+    const { container } = renderWizard();
+    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
+    const stepTitle = () => container.querySelector('.step-title');
+
+    fireEvent.change(field('debt_type_0'), { target: { value: 'credit_card' } });
+    fireEvent.change(field('creditor_name_0'), { target: { value: 'Elm Street Clinic' } });
+    fireEvent.change(field('amount_owed_0'), { target: { value: '1200' } });
+    for (const next of ['Contracts & Leases', 'Codebtors', 'Review & Results']) {
+      const continueBtn = screen.getByRole('button', { name: 'Continue' });
+      await waitFor(() => expect(continueBtn).toBeEnabled());
+      await userEvent.click(continueBtn);
+      await waitFor(() => expect(stepTitle()).toHaveTextContent(next));
+    }
+    await userEvent.click(screen.getByRole('button', { name: /complete intake/i }));
+    await screen.findByRole('alert');
+    expect(saves.stored().status).toBe('completed');
+
+    vi.useFakeTimers();
+    try {
+      for (const step of ['Codebtors', 'Contracts & Leases', 'Amounts Owed']) {
+        fireEvent.click(screen.getByRole('button', { name: 'Go Back' }));
+        await waitSeconds(3);
+        expect(stepTitle()).toHaveTextContent(step);
+      }
+    } finally {
+      vi.useRealTimers();
+    }
+
+    expect(saves.bodies).toHaveLength(1);
+    expect(saves.stored().status).toBe('completed');
+    consoleError.mockRestore();
+  });
+});
+
 // ===========================================================================
 // Income save (DIG-41)
 // ===========================================================================
PATCH
```

`serveSessionSaves` is a fake of Task 7's server. It stores a sent list as sent and returns it in sent order, gives the next new id (101, 102 and so on) to a row sent without an id or with one it doesn't hold, returns amounts as decimal strings, reopens a completed intake on any PATCH, and can hold one reply until the test releases it. The `describe.each` runs four tests for Amounts Owed and four for Assets on fake timers, which `waitSeconds` moves on one second at a time; each wait outlasts the 2 s autosave delay after a save lands. A new row must keep the id its first save gave it across autosave, an edit and autosave, and across Continue, Go Back, an edit and Continue, with one PATCH per real edit, the typed amount as a number and no `_key` in the request. A row loaded with an id the server no longer holds must take its new id, and a row removed while its save was on its way must not take one. The completed-intake test adds a debt, walks to Review, completes, steps back to Amounts Owed, and expects one PATCH in all and a completed intake. The returning-filer PATCH mock now answers with the lists it was sent, as Task 7's server does.

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/wizard/steps/__tests__/DebtsStep.test.tsx b/frontend/src/components/wizard/steps/__tests__/DebtsStep.test.tsx
index b21e068..53d047e 100644
--- a/frontend/src/components/wizard/steps/__tests__/DebtsStep.test.tsx
+++ b/frontend/src/components/wizard/steps/__tests__/DebtsStep.test.tsx
@@ -1,14 +1,16 @@
+import { useState } from 'react';
 import { render, screen } from '@testing-library/react';
 import userEvent from '@testing-library/user-event';
 import { DebtsStep } from '../DebtsStep';
-import type { DebtInfo } from '../../../../types/api';
+import type { DebtInfo, WizardRow } from '../../../../types/api';

-// DebtsStep validates and renders debts passed via initialData.
+// DebtsStep validates and renders the wizard's debt rows.
 // These tests focus on the draft-badge feature: when is_draft is true on a
 // debt, the component must render a visible "From scan" badge so users know
 // the entry was pre-filled by document scanning rather than entered manually.

-const baseDebt: Partial<DebtInfo> = {
+const baseDebt: WizardRow<DebtInfo> = {
+  _key: '1',
   id: 1,
   session: 42,
   debt_type: 'credit_card',
@@ -26,24 +28,25 @@ const noop = () => {};

 describe('DebtsStep draft badge', () => {
   it('renders "From scan" badge when is_draft is true', () => {
-    const draftDebt: Partial<DebtInfo> = { ...baseDebt, is_draft: true };
+    const draftDebt: WizardRow<DebtInfo> = { ...baseDebt, is_draft: true };

-    render(<DebtsStep initialData={[draftDebt]} onDataChange={noop} onValidationChange={noop} />);
+    render(<DebtsStep rows={[draftDebt]} onRowsChange={noop} onValidationChange={noop} />);

     expect(screen.getByText('From scan')).toBeInTheDocument();
   });

   it('does not render a badge when is_draft is false', () => {
-    const manualDebt: Partial<DebtInfo> = { ...baseDebt, is_draft: false };
+    const manualDebt: WizardRow<DebtInfo> = { ...baseDebt, is_draft: false };

-    render(<DebtsStep initialData={[manualDebt]} onDataChange={noop} onValidationChange={noop} />);
+    render(<DebtsStep rows={[manualDebt]} onRowsChange={noop} onValidationChange={noop} />);

     expect(screen.queryByText('From scan')).not.toBeInTheDocument();
   });

   it('does not render a badge when is_draft is absent', () => {
     // Omit is_draft entirely to verify the badge is absent when the field is missing
-    const debtWithoutDraft: Partial<DebtInfo> = {
+    const debtWithoutDraft: WizardRow<DebtInfo> = {
+      _key: baseDebt._key,
       id: baseDebt.id,
       session: baseDebt.session,
       debt_type: baseDebt.debt_type,
@@ -53,33 +56,29 @@ describe('DebtsStep draft badge', () => {
       is_secured: baseDebt.is_secured,
     };

-    render(
-      <DebtsStep initialData={[debtWithoutDraft]} onDataChange={noop} onValidationChange={noop} />
-    );
+    render(<DebtsStep rows={[debtWithoutDraft]} onRowsChange={noop} onValidationChange={noop} />);

     expect(screen.queryByText('From scan')).not.toBeInTheDocument();
   });

   it('renders badge on each draft debt in a mixed list', () => {
-    const manualDebt: Partial<DebtInfo> = {
+    const manualDebt: WizardRow<DebtInfo> = {
       ...baseDebt,
+      _key: '2',
       id: 2,
       creditor_name: 'Manual Citi',
       is_draft: false,
     };
-    const draftDebt: Partial<DebtInfo> = {
+    const draftDebt: WizardRow<DebtInfo> = {
       ...baseDebt,
+      _key: '3',
       id: 3,
       creditor_name: 'Scanned Wells Fargo',
       is_draft: true,
     };

     render(
-      <DebtsStep
-        initialData={[manualDebt, draftDebt]}
-        onDataChange={noop}
-        onValidationChange={noop}
-      />
+      <DebtsStep rows={[manualDebt, draftDebt]} onRowsChange={noop} onValidationChange={noop} />
     );

     // Only the draft entry gets a badge — the manual entry must not.
@@ -87,31 +86,31 @@ describe('DebtsStep draft badge', () => {
   });

   it('renders badges on all draft debts when multiple are present', () => {
-    const draftA: Partial<DebtInfo> = {
+    const draftA: WizardRow<DebtInfo> = {
       ...baseDebt,
+      _key: '10',
       id: 10,
       creditor_name: 'Scanned Amex',
       is_draft: true,
     };
-    const draftB: Partial<DebtInfo> = {
+    const draftB: WizardRow<DebtInfo> = {
       ...baseDebt,
+      _key: '11',
       id: 11,
       creditor_name: 'Scanned Discover',
       is_draft: true,
       source_document_name: 'credit_report.pdf',
     };

-    render(
-      <DebtsStep initialData={[draftA, draftB]} onDataChange={noop} onValidationChange={noop} />
-    );
+    render(<DebtsStep rows={[draftA, draftB]} onRowsChange={noop} onValidationChange={noop} />);

     expect(screen.getAllByText('From scan')).toHaveLength(2);
   });

   it('badge has the correct aria-label for screen reader users', () => {
-    const draftDebt: Partial<DebtInfo> = { ...baseDebt, is_draft: true };
+    const draftDebt: WizardRow<DebtInfo> = { ...baseDebt, is_draft: true };

-    render(<DebtsStep initialData={[draftDebt]} onDataChange={noop} onValidationChange={noop} />);
+    render(<DebtsStep rows={[draftDebt]} onRowsChange={noop} onValidationChange={noop} />);

     expect(
       screen.getByRole('generic', { name: /pre-filled from document scan/i })
@@ -122,9 +121,24 @@ describe('DebtsStep draft badge', () => {
 // Schedule D lists a secured amount owed with what secures it, and the server reads both
 // under these names: a renamed key is dropped without an error (DIG-26)
 describe('DebtsStep secured amounts owed', () => {
+  /** The wizard's part: it holds the rows the step shows */
+  function StepWithRows({ onRowsChange }: { onRowsChange: (rows: WizardRow<DebtInfo>[]) => void }) {
+    const [rows, setRows] = useState<WizardRow<DebtInfo>[]>([]);
+    return (
+      <DebtsStep
+        rows={rows}
+        onRowsChange={(next) => {
+          setRows(next);
+          onRowsChange(next);
+        }}
+        onValidationChange={noop}
+      />
+    );
+  }
+
   it('marks a car loan secured and keeps what secures it, under the names the server stores', async () => {
-    const onDataChange = vi.fn();
-    render(<DebtsStep onDataChange={onDataChange} onValidationChange={noop} />);
+    const onRowsChange = vi.fn();
+    render(<StepWithRows onRowsChange={onRowsChange} />);
     const user = userEvent.setup();

     await user.selectOptions(
@@ -133,7 +147,7 @@ describe('DebtsStep secured amounts owed', () => {
     );
     await user.type(screen.getByLabelText(/what secures this amount owed/i), '2015 Honda Civic');

-    expect(onDataChange).toHaveBeenLastCalledWith([
+    expect(onRowsChange).toHaveBeenLastCalledWith([
       expect.objectContaining({
         debt_type: 'auto_loan',
         is_secured: true,
PATCH
```

The draft-badge tests pass `rows` and `onRowsChange`, with a `_key` in each fixture. The secured-debt test renders the step inside `StepWithRows`, which holds the rows the way the wizard does: a controlled step given a bare `vi.fn()` never shows what the filer chose, so the box for what secures the debt would never appear.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/hooks/__tests__/useAutoSave.test.ts src/components/wizard/steps/__tests__/DebtsStep.test.tsx src/pages/__tests__/IntakeWizard.test.tsx 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Test Files  3 failed (3)` and `Tests  16 failed | 51 passed (67)`. Every failure is an assertion or an error on the first render; none waits for an element and runs out of time. The new hook test fails with `AssertionError: expected "vi.fn()" to be called 1 times, but got 2 times`: the hook ignores the copy the save returns, so the id reaching the data is saved again. The eight tests of new rows fail on the ids sent, because the wizard drops the reply and the second save sends the row without its id, or with the id it was loaded with: `AssertionError: expected [ [ undefined ], [ undefined ] ] to deeply equal [ [ undefined ], [ 101 ] ]` for the first two tests of each list, `AssertionError: expected [ [ 7 ], [ 7 ] ] to deeply equal [ [ 7 ], [ 101 ] ]` and `AssertionError: expected [ [ 3 ], [ 3 ] ] to deeply equal [ [ 3 ], [ 101 ] ]` for a stale id, and an undefined id where 102 belongs for the row kept after the other was removed. The seven DebtsStep tests fail on the prop rename, not on what they assert: the old step ignores the rows it is given and calls a prop the tests no longer pass, `TypeError: onDataChange is not a function`.

The completed-intake test passes before the change: with no ids written into the rows, the body on stepping back equals the copy Continue sent. It guards the change instead. The implementer's mutations failed it when `useAutoSave` ignored the returned copy and when the merge took whole rows from the reply, amounts included. The returning-filer tests, whose PATCH mock changed, pass too, since each reads only the first PATCH body.

- [ ] **Step 3: Make the Assets and Amounts Owed steps controlled**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/wizard/steps/AssetsStep.tsx b/frontend/src/components/wizard/steps/AssetsStep.tsx
index 1975a8b..3b6731e 100644
--- a/frontend/src/components/wizard/steps/AssetsStep.tsx
+++ b/frontend/src/components/wizard/steps/AssetsStep.tsx
@@ -13,11 +13,12 @@ import { FormField, FormSelect, Button } from '../../common';
 import { UPLDisclaimer } from '../../compliance';
 import { UPL_EXEMPTION_DISCLAIMER } from '../../../constants/upl';
 import { parseAmount } from '../../../utils/parseAmount';
-import type { AssetInfo } from '../../../types/api';
+import type { AssetInfo, WizardRow } from '../../../types/api';

 interface AssetsStepProps {
-  initialData?: Partial<AssetInfo>[];
-  onDataChange: (data: Partial<AssetInfo>[]) => void;
+  /** The wizard's rows. The step keeps no copy, so an id a save writes into a row stays there. */
+  rows: WizardRow<AssetInfo>[];
+  onRowsChange: (rows: WizardRow<AssetInfo>[]) => void;
   onValidationChange: (isValid: boolean) => void;
 }

@@ -30,10 +31,15 @@ const ASSET_TYPES = [
   { value: 'other', label: 'Other Asset' },
 ];

-export function AssetsStep({ initialData, onDataChange, onValidationChange }: AssetsStepProps) {
-  const [assets, setAssets] = useState<Partial<AssetInfo>[]>(
-    initialData && initialData.length > 0 ? initialData : [createEmptyAsset()]
-  );
+// The last new row's key: unique while the page is open, and the prefix keeps it apart from a
+// loaded row's key, which is its id
+let nextKey = 0;
+
+export function AssetsStep({ rows, onRowsChange, onValidationChange }: AssetsStepProps) {
+  // With no rows, the step shows one blank row. It joins the wizard's rows at the filer's first
+  // edit, and a blank row is never saved.
+  const [blankRow] = useState(createEmptyAsset);
+  const assets = useMemo(() => (rows.length > 0 ? rows : [blankRow]), [rows, blankRow]);

   const { errors, isValid } = useMemo(() => {
     const newErrors: Record<number, Record<string, string>> = {};
@@ -79,15 +85,15 @@ export function AssetsStep({ initialData, onDataChange, onValidationChange }: As
     return { errors: newErrors, isValid: valid };
   }, [assets]);

-  // Update parent when assets change
+  // Tell the parent whether the step can be saved
   useEffect(() => {
-    onDataChange(assets);
     onValidationChange(isValid);
-    // both callbacks are useState setters in IntakeWizard — stable identities
-  }, [assets, isValid, onDataChange, onValidationChange]);
+    // a useState setter in IntakeWizard — a stable identity
+  }, [isValid, onValidationChange]);

-  function createEmptyAsset(): Partial<AssetInfo> {
+  function createEmptyAsset(): WizardRow<AssetInfo> {
     return {
+      _key: `new-${++nextKey}`,
       asset_type: undefined,
       description: '',
       current_value: undefined,
@@ -97,15 +103,15 @@ export function AssetsStep({ initialData, onDataChange, onValidationChange }: As
   }

   const handleAddAsset = () => {
-    setAssets([...assets, createEmptyAsset()]);
+    onRowsChange([...assets, createEmptyAsset()]);
   };

   const handleRemoveAsset = (index: number) => {
     if (assets.length === 1) {
       // Keep at least one asset form
-      setAssets([createEmptyAsset()]);
+      onRowsChange([createEmptyAsset()]);
     } else {
-      setAssets(assets.filter((_, i) => i !== index));
+      onRowsChange(assets.filter((_, i) => i !== index));
     }
   };

@@ -124,7 +130,7 @@ export function AssetsStep({ initialData, onDataChange, onValidationChange }: As
       };
     }

-    setAssets(updatedAssets);
+    onRowsChange(updatedAssets);
   };

   const calculateEquity = (asset: Partial<AssetInfo>): number => {
diff --git a/frontend/src/components/wizard/steps/DebtsStep.tsx b/frontend/src/components/wizard/steps/DebtsStep.tsx
index 161b493..4bee93f 100644
--- a/frontend/src/components/wizard/steps/DebtsStep.tsx
+++ b/frontend/src/components/wizard/steps/DebtsStep.tsx
@@ -14,11 +14,12 @@ import { FormField, FormSelect, FormTextarea, Button } from '../../common';
 import { UPLDisclaimer } from '../../compliance';
 import { UPL_EXEMPTION_DISCLAIMER } from '../../../constants/upl';
 import { parseAmount } from '../../../utils/parseAmount';
-import type { DebtInfo } from '../../../types/api';
+import type { DebtInfo, WizardRow } from '../../../types/api';

 interface DebtsStepProps {
-  initialData?: Partial<DebtInfo>[];
-  onDataChange: (data: Partial<DebtInfo>[]) => void;
+  /** The wizard's rows. The step keeps no copy, so an id a save writes into a row stays there. */
+  rows: WizardRow<DebtInfo>[];
+  onRowsChange: (rows: WizardRow<DebtInfo>[]) => void;
   onValidationChange: (isValid: boolean) => void;
 }

@@ -51,10 +52,15 @@ const DEBT_CATEGORY_OPTIONS = Object.entries(DEBT_CATEGORY_META).map(([value, {
   label,
 }));

-export function DebtsStep({ initialData, onDataChange, onValidationChange }: DebtsStepProps) {
-  const [debts, setDebts] = useState<Partial<DebtInfo>[]>(
-    initialData && initialData.length > 0 ? initialData : [createEmptyDebt()]
-  );
+// The last new row's key: unique while the page is open, and the prefix keeps it apart from a
+// loaded row's key, which is its id
+let nextKey = 0;
+
+export function DebtsStep({ rows, onRowsChange, onValidationChange }: DebtsStepProps) {
+  // With no rows, the step shows one blank row. It joins the wizard's rows at the filer's first
+  // edit, and a blank row is never saved.
+  const [blankRow] = useState(createEmptyDebt);
+  const debts = useMemo(() => (rows.length > 0 ? rows : [blankRow]), [rows, blankRow]);

   const { errors, isValid } = useMemo(() => {
     const newErrors: Record<number, Record<string, string>> = {};
@@ -103,16 +109,16 @@ export function DebtsStep({ initialData, onDataChange, onValidationChange }: Deb
     return { errors: newErrors, isValid: valid };
   }, [debts]);

-  // Update parent when debts change
+  // Tell the parent whether the step can be saved
   /* eslint-disable react-hooks/exhaustive-deps */
   useEffect(() => {
-    onDataChange(debts);
     onValidationChange(isValid);
-  }, [debts, isValid]);
+  }, [isValid]);
   /* eslint-enable react-hooks/exhaustive-deps */

-  function createEmptyDebt(): Partial<DebtInfo> {
+  function createEmptyDebt(): WizardRow<DebtInfo> {
     return {
+      _key: `new-${++nextKey}`,
       debt_type: undefined,
       creditor_name: '',
       account_number: '',
@@ -124,15 +130,15 @@ export function DebtsStep({ initialData, onDataChange, onValidationChange }: Deb
   }

   const handleAddDebt = () => {
-    setDebts([...debts, createEmptyDebt()]);
+    onRowsChange([...debts, createEmptyDebt()]);
   };

   const handleRemoveDebt = (index: number) => {
     if (debts.length === 1) {
       // Keep at least one debt form
-      setDebts([createEmptyDebt()]);
+      onRowsChange([createEmptyDebt()]);
     } else {
-      setDebts(debts.filter((_, i) => i !== index));
+      onRowsChange(debts.filter((_, i) => i !== index));
     }
   };

@@ -161,7 +167,7 @@ export function DebtsStep({ initialData, onDataChange, onValidationChange }: Deb
       };
     }

-    setDebts(updatedDebts);
+    onRowsChange(updatedDebts);
   };

   return (
diff --git a/frontend/src/types/api.ts b/frontend/src/types/api.ts
index 2578d4a..42c2921 100644
--- a/frontend/src/types/api.ts
+++ b/frontend/src/types/api.ts
@@ -213,6 +213,13 @@ export interface DebtInfo {
   source_document_name?: string | null;
 }

+/**
+ * An asset or debt row as the wizard holds it. `_key` is the browser's own name for the row and
+ * never reaches the server: a loaded row's id, or `new-<n>` from a counter for a new row. A save
+ * writes the id the server gave each row into the row with that key (DIG-273).
+ */
+export type WizardRow<T> = Partial<T> & { _key: string };
+
 /** A contract or lease (Schedule G), as the contracts list endpoint sends and saves it */
 export interface ExecutoryContract {
   id?: number;
PATCH
```

`WizardRow` names a row with its browser-only `_key`. Each step renders the wizard's rows, or one blank row while there are none, and hands every change back through `onRowsChange`, so the wizard holds the only copy and an id written into a row stays there (spec §5.2). A new row's key comes from the step's counter (Ruling R8-a).

- [ ] **Step 4: Let a save hand back the copy the server holds**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/hooks/useAutoSave.ts b/frontend/src/hooks/useAutoSave.ts
index 1dd650f..0b0b030 100644
--- a/frontend/src/hooks/useAutoSave.ts
+++ b/frontend/src/hooks/useAutoSave.ts
@@ -21,8 +21,12 @@ interface UseAutoSaveOptions<T> {
    * Each name keeps its own last saved copy; the first data seen under a name is its loaded copy.
    */
   dataKey?: string;
-  /** Async function that persists the data */
-  onSave: (data: T) => Promise<void>;
+  /**
+   * Async function that persists the data. It may return the copy the server now holds (the
+   * wizard's rows with the ids the save gave them), which becomes the last saved copy in place
+   * of the data sent.
+   */
+  onSave: (data: T) => Promise<T | void>;
   /** Debounce delay in milliseconds (default: 2000) */
   debounceMs?: number;
   /** Whether auto-save is enabled (default: true) */
@@ -69,8 +73,8 @@ export function useAutoSave<T>({
     sendingCopiesRef.current.set(key, copy);
     setSaveStatus('saving');
     try {
-      await onSaveRef.current(dataRef.current);
-      savedCopiesRef.current.set(key, copy);
+      const savedCopy = await onSaveRef.current(dataRef.current);
+      savedCopiesRef.current.set(key, savedCopy === undefined ? copy : JSON.stringify(savedCopy));
       setSaveStatus('saved');
       setLastSavedAt(new Date());

PATCH
```

When `onSave` returns a copy, the hook keeps that copy's JSON as the saved copy in place of the data sent, so ids that reach the data after a save don't count as an edit (spec §5.2, "No extra save").

- [ ] **Step 5: Write each saved row's id into the wizard's rows**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
index 093d03a..2194d5a 100644
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -35,6 +35,7 @@ import type {
   ExecutoryContract,
   Codebtor,
   CompletionError,
+  WizardRow,
 } from '../types/api';
 import { EXPENSE_FIELDS, INCOME_FIELDS } from '../types/api';

@@ -58,6 +59,40 @@ const WIZARD_STEPS = [
 const ASSET_AMOUNT_FIELDS = ['current_value', 'amount_owed'] as const;
 const DEBT_AMOUNT_FIELDS = ['amount_owed', 'monthly_payment'] as const;

+/** A row as the server takes it, without the browser's own key */
+function withoutKey<Row extends { _key: string }>(row: Row): Partial<Row> {
+  const sent: Partial<Row> = { ...row };
+  delete sent._key;
+  return sent;
+}
+
+/**
+ * The id each sent row came back with, by the row's key. A session save returns a list it was
+ * sent in the order sent (DIG-273), so the row sent at each position takes the id at that
+ * position, a row sent with a stale or foreign id included.
+ */
+function savedIds(sent: { _key: string }[], saved: { id: number }[] | undefined) {
+  if (saved?.length !== sent.length) {
+    throw new Error('The session save did not return each row it was sent');
+  }
+  return new Map(sent.map((row, index) => [row._key, saved[index].id]));
+}
+
+/**
+ * Writes each saved row's id into the row with the same key, wherever that row now sits. A key no
+ * longer present (a row removed while its save was on its way) is skipped. Nothing else comes from
+ * the reply, so the amounts stay as the filer typed them.
+ */
+function withSavedIds<Row extends { _key: string; id?: number }>(
+  rows: Row[],
+  ids: Map<string, number>
+): Row[] {
+  return rows.map((row) => {
+    const id = ids.get(row._key);
+    return id === undefined ? row : { ...row, id };
+  });
+}
+
 export function IntakeWizard() {
   const navigate = useNavigate();
   const {
@@ -84,8 +119,8 @@ export function IntakeWizard() {
   const [debtorData, setDebtorData] = useState<Partial<DebtorInfo>>({});
   const [incomeData, setIncomeData] = useState<Partial<IncomeInfo>>({});
   const [expenseData, setExpenseData] = useState<Partial<ExpenseInfo>>({});
-  const [assetsData, setAssetsData] = useState<Partial<AssetInfo>[]>([]);
-  const [debtsData, setDebtsData] = useState<Partial<DebtInfo>[]>([]);
+  const [assetsData, setAssetsData] = useState<WizardRow<AssetInfo>[]>([]);
+  const [debtsData, setDebtsData] = useState<WizardRow<DebtInfo>[]>([]);
   const [contractsData, setContractsData] = useState<ExecutoryContract[]>([]);
   const [codebtorsData, setCodebtorsData] = useState<Codebtor[]>([]);
   // What Complete last said is missing, listed on Review until the step changes
@@ -148,10 +183,21 @@ export function IntakeWizard() {
         if (fresh.debtor_info) setDebtorData(fresh.debtor_info);
         if (fresh.income_info) setIncomeData(hydrateAmounts(fresh.income_info, INCOME_FIELDS));
         if (fresh.expense_info) setExpenseData(hydrateAmounts(fresh.expense_info, EXPENSE_FIELDS));
+        // A loaded row's key is its id
         if (fresh.assets)
-          setAssetsData(fresh.assets.map((asset) => hydrateAmounts(asset, ASSET_AMOUNT_FIELDS)));
+          setAssetsData(
+            fresh.assets.map((asset) => ({
+              ...hydrateAmounts(asset, ASSET_AMOUNT_FIELDS),
+              _key: String(asset.id),
+            }))
+          );
         if (fresh.debts)
-          setDebtsData(fresh.debts.map((debt) => hydrateAmounts(debt, DEBT_AMOUNT_FIELDS)));
+          setDebtsData(
+            fresh.debts.map((debt) => ({
+              ...hydrateAmounts(debt, DEBT_AMOUNT_FIELDS),
+              _key: String(debt.id),
+            }))
+          );
         setContractsData(contracts);
         setCodebtorsData(codebtors);
         setSessionRead('done');
@@ -209,7 +255,8 @@ export function IntakeWizard() {
       }

       case 'assets':
-        // Filter out empty/blank asset forms before sending
+        // Filter out empty/blank asset forms before sending. Each row keeps its `_key` here;
+        // saveCurrentStepData leaves it out of the request.
         return {
           assets: assetsData.filter((a) => a.asset_type && a.description?.trim()),
         } as Partial<IntakeSession>;
@@ -331,7 +378,9 @@ export function IntakeWizard() {
   // Data Persistence
   // =========================================================================

-  const saveCurrentStepData = async (body: Partial<IntakeSession> | null) => {
+  const saveCurrentStepData = async (
+    body: Partial<IntakeSession> | null
+  ): Promise<Partial<IntakeSession> | void> => {
     if (!session) return;

     // Contracts and codebtors save as whole lists, only from Continue: their step body is null,
@@ -353,7 +402,29 @@ export function IntakeWizard() {
       return;
     }

-    await api.intake.updateSession(session.id, body);
+    // Assets and debts carry the browser's own key, which never reaches the server
+    const { assets, debts } = body as {
+      assets?: WizardRow<AssetInfo>[];
+      debts?: WizardRow<DebtInfo>[];
+    };
+    const request: Partial<Record<keyof IntakeSession, unknown>> = { ...body };
+    if (assets) request.assets = assets.map(withoutKey);
+    if (debts) request.debts = debts.map(withoutKey);
+    const saved = await api.intake.updateSession(session.id, request as Partial<IntakeSession>);
+
+    // A new row keeps the id its first save gave it, so the next save updates that row instead of
+    // replacing it. The copy returned is what the server now holds, built by the same merge as
+    // the rows, so autosave sends nothing more until the filer changes something (DIG-273).
+    if (assets) {
+      const ids = savedIds(assets, saved.assets);
+      setAssetsData((rows) => withSavedIds(rows, ids));
+      return { ...body, assets: withSavedIds(assets, ids) } as Partial<IntakeSession>;
+    }
+    if (debts) {
+      const ids = savedIds(debts, saved.debts);
+      setDebtsData((rows) => withSavedIds(rows, ids));
+      return { ...body, debts: withSavedIds(debts, ids) } as Partial<IntakeSession>;
+    }
   };

   // =========================================================================
@@ -392,8 +463,8 @@ export function IntakeWizard() {
       case 4:
         return (
           <AssetsStep
-            initialData={assetsData}
-            onDataChange={setAssetsData}
+            rows={assetsData}
+            onRowsChange={setAssetsData}
             onValidationChange={setCanProceed}
           />
         );
@@ -401,8 +472,8 @@ export function IntakeWizard() {
       case 5:
         return (
           <DebtsStep
-            initialData={debtsData}
-            onDataChange={setDebtsData}
+            rows={debtsData}
+            onRowsChange={setDebtsData}
             onValidationChange={setCanProceed}
           />
         );
PATCH
```

A loaded row's key is its id. `saveCurrentStepData` sends the rows without `_key`, pairs each sent row with the reply's row at the same position, writes that id into the wizard row with the same key wherever it now sits, and returns the copy the server holds, built by the same merge from the body (spec §5.2, "The merge").

- [ ] **Step 6: Run the tests again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/hooks/__tests__/useAutoSave.test.ts src/components/wizard/steps/__tests__/DebtsStep.test.tsx src/pages/__tests__/IntakeWizard.test.tsx 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: `Test Files  3 passed (3)` and `Tests  67 passed (67)`.

- [ ] **Step 7: Describe the merge and the saved copy in CLAUDE.md**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 89d2978..ec68ddf 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -23,7 +23,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **React 19 + navigate()** — calling `navigate()` in render body crashes the reconciler. Use `useEffect`.
 - **Vite HMR in Docker** — type/structure changes don't hot-reload; restart the frontend container.
 - **Enum mismatches are silent** — frontend/backend enum drift only surfaces at runtime; check both when adding fields.
-- **Nested debts and assets save by id** — `IntakeSessionSerializer.update` upserts `debts`/`assets` through `_save_rows_by_id`: a row carrying one of this session's ids updates only the keys it sends, a row without one (or with an unknown or foreign id) is created on this session, and a stored row missing from the payload is **deleted**, so send every row you want to keep. A nested `session` is ignored. A session PATCH or PUT that carries `assets` or `debts` returns that list in the order it was sent, each row with its id (a new row, or one sent with a foreign or unknown id, shows its new id), so the wizard can pair rows by position and keep a new row's id; every other read keeps model order (DIG-164). Fields the browser never receives (`account_number`, `source_document`) survive a re-save. `DebtViewSet`/`AssetViewSet` keep the base serializers, so per-item create never takes a client id. Contracts and codebtors save the same way, as a whole list: `PUT /intake/sessions/{id}/contracts/` (or `codebtors/`) checks every row before writing any, and an empty list deletes every stored row. The wizard sends each list on Continue from steps 6 and 7, and reads both with the session before any step shows, so a list that failed to load is never saved as empty.
+- **Nested debts and assets save by id** — `IntakeSessionSerializer.update` upserts `debts`/`assets` through `_save_rows_by_id`: a row carrying one of this session's ids updates only the keys it sends, a row without one (or with an unknown or foreign id) is created on this session, and a stored row missing from the payload is **deleted**, so send every row you want to keep. A nested `session` is ignored. A session PATCH or PUT that carries `assets` or `debts` returns that list in the order it was sent, each row with its id (a new row, or one sent with a foreign or unknown id, shows its new id), so the wizard can pair rows by position and keep a new row's id; every other read keeps model order (DIG-164). The wizard holds the Assets and Amounts Owed rows itself (`AssetsStep`/`DebtsStep` are controlled: `rows`, `onRowsChange`) and gives each row a browser-only `_key`, a loaded row's id or `new-<n>` from a counter in the step for a new row (not `crypto.randomUUID()`, which plain HTTP from another device lacks), which `saveCurrentStepData` leaves out of the request. After each save it writes the id at each position into the row with that `_key`, wherever it now sits, skips a row removed while the save was on its way, and takes nothing else from the reply, so amounts stay as typed. A reply whose list is a different length from the one sent fails the save rather than pairing ids by guesswork. Fields the browser never receives (`account_number`, `source_document`) survive a re-save. `DebtViewSet`/`AssetViewSet` keep the base serializers, so per-item create never takes a client id. Contracts and codebtors save the same way, as a whole list: `PUT /intake/sessions/{id}/contracts/` (or `codebtors/`) checks every row before writing any, and an empty list deletes every stored row. The wizard sends each list on Continue from steps 6 and 7, and reads both with the session before any step shows, so a list that failed to load is never saved as empty.
 - **Saves lock the session** — every write to a session's intake data first calls `lock_session` (`apps/intake/locking.py`, `select_for_update` on the session row) inside the same `transaction.atomic()` block as the write, so a second save of the same session waits for the first to commit and then reads what it stored (DIG-188). That covers the session PATCH and PUT, `update_step`, `complete` (which writes only `status` and `completed_at`), the contracts and codebtors PUT, POST and DELETE, the `DebtViewSet`/`AssetViewSet` writes, a scanned bill's correction and an upload's findings. Call `get_object()` before locking (another user's session is a 404), and lock before reading anything the write depends on. An upload locks only in its worker thread, around the write of its findings, after the call to the hosted model: the upload request waits for that thread, so a lock taken in the request deadlocks. `select_for_update` does nothing on sqlite, so the backend suite can't see a missing lock; only `apps/intake/tests/test_session_lock.py` (marker `postgres`) proves it, and it skips under the default settings. Run it locally with `DJANGO_SETTINGS_MODULE=config.settings.test_postgres pytest -m postgres`, with `DATABASE_URL` naming a Postgres whose user can create the test database; CI runs it in the backend job against its Postgres service. `test_postgres` sets a 10-second `lock_timeout`, so a deadlock fails a test instead of hanging the run.
 - **Debt and asset amounts are readable, as strings** — the owner gets `DebtInfo.amount_owed` and `AssetInfo.current_value`/`amount_owed` back (SSN and `account_number` stay write-only). DRF sends decimals as strings (`"2500.00"`), so the wizard converts them with `hydrateAmounts` (`utils/parseAmount.ts`) as session data enters step state; a raw string in a step's `reduce` joins as text (`$02500.00100.50`). A stored amount wider than `DecimalField(12, 2)` makes every read of that session 500, so every write path must bound it (`DraftDebtCreator` stores it as 0; documents `validate` returns 400).
 - **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data. It reads the median table in force on today's real date, not the tests' pinned one, and when none is (from November 1, 2026 until the November table is loaded) it prints a message naming `docs/REFERENCE_TABLES.md` and changes nothing, so even `--reset` leaves the existing personas. Personas seeded before income was stored by source must be re-created with `seed_demo_data --reset` (migration 0014 leaves their totals unsplit, and a plain re-run skips existing users).
@@ -65,7 +65,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **`extract()` takes a list of page images** — `BaseOCRProvider.extract(images: list[bytes], prompt)`: `[]` means text mode, a photo upload is a one-item list, and pages go in page order (one OpenAI `image_url` part or one Gemini inline part each). `classify()` still takes bytes. Never hand a provider `[]` for a scan.
 - **An empty OpenAI reply raises `EmptyModelReply`** — `OpenAIProvider._complete` retries a blank or whitespace-only reply once, but never a refusal or `finish_reason == "content_filter"`. The error names `finish_reason` and whether a refusal was present, never its text. `_parse_result` records only the reply's length ("model reply was not valid JSON (N characters)"), so `error_message` never holds model output. Gemini still returns `""` (DIG-35).
 - **The wizard re-reads the session on every mount** — `IntakeWizard` fixes the session id at mount (context session, else `current_session_id`), calls `loadSession(id)`, and renders no step until it returns, so steps and autosave start from server data, not the context copy (which predates any upload on `/documents`). A failed read shows a "Try again" alert for the same id; a 404 starts a new session. `loadSession`/`createSession` resolve with the session, and `loadSession` clears `current_session_id` only on a 404, but the provider's own startup load still clears it on any error (DIG-11).
-- **Autosave sends only real edits** — `useAutoSave` compares the step's PATCH body (`currentStepBody` in `IntakeWizard`) as JSON with that step's last saved or loaded copy (the first body seen under a step's name) and skips an equal one, so showing a step again (Go Back) sends nothing and doesn't reopen a completed intake. A body must therefore be built the same way from loaded data as from edited data: leave out read-only totals and echoed fields, or every visit saves. Continue (`saveNow`) always saves. Steps 6 and 7 have no body there; their lists save only on Continue.
+- **Autosave sends only real edits** — `useAutoSave` compares the step's PATCH body (`currentStepBody` in `IntakeWizard`) as JSON with that step's last saved or loaded copy (the first body seen under a step's name) and skips an equal one, so showing a step again (Go Back) sends nothing and doesn't reopen a completed intake. A body must therefore be built the same way from loaded data as from edited data: leave out read-only totals and echoed fields, or every visit saves. A save of assets or debts returns the copy the server now holds, the sent rows with the ids the reply gave them, built by the same merge as the wizard's rows; `onSave` may return such a copy, and the hook keeps it as the saved copy, so the ids reaching the rows send nothing more. Continue (`saveNow`) always saves. Steps 6 and 7 have no body there; their lists save only on Continue.
 - **An empty scan is FAILED, not done** — `documents/views._record_findings` judges each type: a bill needs a creditor name, a pay stub must pass `PayStubExtraction`, the check the income aggregate applies (gross pay + both pay-period dates required; an invalid optional field such as a negative `net_pay` also fails it), a credit report needs one readable tradeline. Otherwise `OCRResult.status="failed"`, `failure_reason="nothing_found"`; any exception is `processing_error`. A bill with a creditor but no readable balance is `completed` with a $0 draft; a report of only $0 accounts is `completed` with no debts. Other document types are not judged.
 - **The documents API never returns `error_message` or `extracted_data`** — `_serialize_ocr` returns `status`, `failure_reason`, `confidence_scores`, `overall_confidence`, `user_validated`. `error_message` is operations-only (exception class, `finish_reason`); read it in a Django shell. The pipeline's catch-all handlers (`_run_processing`, `AggregateIngestionService.recalculate`) log only the exception's type with `logger.error`, never `logger.exception`: logs reach Sentry, and a DB error's DETAIL quotes row values (DIG-105).
 - **Scanned amounts are bounded** — `draft_debt._bounded_amount` stores a non-numeric, negative, non-finite or ≥1e10 balance as 0, and `TradelineItem.amount_owed` has `le=9999999999.99`: a wider value makes `DecimalField(12,2)` raise on every read of the session.
PATCH
```

"Nested debts and assets save by id" now says how the wizard holds the rows, keys them and merges the reply's ids, and that a reply of a different length fails the save. "Autosave sends only real edits" says that a save of assets or debts returns the saved copy the hook keeps.

- [ ] **Step 8: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2135 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  389 passed (389)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

The 25 skips are Task 6's Postgres-only tests under sqlite. The next command runs them against the Postgres database named in `.claude/forms-step3a1.env`: this task changes no backend code, but every task from Task 6 on keeps them green.

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

The gates were run on this commit before the controller added the CLAUDE.md sentence on a reply of a different length; prettier ran on the amend.

- [ ] **Step 9: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

DeShawn's journey enters three assets and four debts through the wizard, James's a vehicle and a bank account, and the scanned bill's debt must survive a save and a reload. The journeys were run on this commit before a re-wrap of its message and the CLAUDE.md sentence above, neither of which changes code.

- [ ] **Step 10: Commit**

```bash
set -eo pipefail
git add \
  CLAUDE.md \
  frontend/src/components/wizard/steps/AssetsStep.tsx \
  frontend/src/components/wizard/steps/DebtsStep.tsx \
  frontend/src/components/wizard/steps/__tests__/DebtsStep.test.tsx \
  frontend/src/hooks/__tests__/useAutoSave.test.ts \
  frontend/src/hooks/useAutoSave.ts \
  frontend/src/pages/IntakeWizard.tsx \
  frontend/src/pages/__tests__/IntakeWizard.test.tsx \
  frontend/src/types/api.ts
git commit -F - <<'MSG'
fix(wizard): new assets and debts keep one id across every save

A new asset or debt never learned the id its first save gave it, so every
later save created the row again and deleted the copy stored the time
before. Step 3c links debts to assets, codebtors and notice parties by id,
so the ids must hold.

The Assets and Amounts Owed steps are now controlled: the wizard holds
their rows (`rows`, `onRowsChange`) and the steps keep no copy, so an id
written into a row is neither overwritten by the step's next change nor
lost when Continue unmounts the step. With no rows a step still shows one
blank row, which joins the wizard's rows at the filer's first edit. Since
the steps no longer push that blank row up on mount, Review shows "No
assets listed." instead of an unnamed asset for a filer who listed none.

Each wizard row carries a browser-only `_key`: a loaded row's id, or
`new-<n>` from a module counter in the step for a new row, unique while the
page is open. Not `crypto.randomUUID()`: browsers offer it only on HTTPS or
localhost, so someone opening a self-hosted copy from a phone over plain
HTTP would get a TypeError as soon as Assets or Amounts Owed mounts.

`saveCurrentStepData` leaves `_key` out of the request, pairs each sent row
with the reply's row at the same position (the server returns a sent list
in the order sent), and writes that id into the wizard row with the same
key, wherever it now sits. A row
removed while its save was on its way is skipped, a row sent with a stale
id takes its new id, and nothing else comes from the reply, so amounts
stay as typed. A reply that lists a different number of rows fails the
save rather than pairing ids at random.

`useAutoSave`'s `onSave` may now return the copy the server holds, and the
hook keeps it as the saved copy in place of the body sent. The wizard
builds that copy with the same merge as its rows, so the ids reaching the
rows send no extra PATCH, and stepping back over the step does not reopen
a completed intake.

Tests: a new debt or asset keeps one id across autosave, an edit and
autosave (one PATCH per edit), and across Continue, Go Back, an edit and
Continue; a row sent with an id the server no longer holds takes its new
id; a row removed during its save is skipped; a completed intake stays
completed when the filer steps back to a debt they added; `useAutoSave`
keeps a returned copy as its baseline. The DebtsStep tests, which the new
props broke, now pass `rows` and `onRowsChange`, and the secured-debt test
holds the rows in a small stateful wrapper. The returning-filer PATCH mock
now returns the sent lists with their ids, as the server does.

CLAUDE.md: "Autosave sends only real edits" and "Nested debts and assets
save by id" describe the returned copy and the browser-only key.

Refs DIG-273
MSG
git status --short
```

### Task 9: Give the personas' private creditors fictional names

_Built and verified as commit `f40f647` on `plan/forms-step3a1`._

**Files:**

- Modify: `backend/apps/intake/management/commands/seed_demo_data.py`
- Modify: `docs/testing/persona-briefs/deshawn-mitchell.md`
- Modify: `docs/testing/persona-briefs/james-washington.md`
- Modify: `docs/testing/persona-briefs/maria-torres.md`
- Modify: `docs/testing/persona-briefs/priya-sharma.md`
- Modify: `docs/testing/persona-briefs/sarah-chen.md`
- Modify: `frontend/e2e/fixtures/personas.ts`
- Modify: `frontend/e2e/journeys/sofa-journey.spec.ts`

**Interfaces:**

- Consumes:
  - `PERSONAS` in `backend/apps/intake/management/commands/seed_demo_data.py`: each persona's debt rows carry a `creditor_name`, and Maria's wage lines and the SOFA creditor-payment rows carry names too.
  - The persona fixtures in `frontend/e2e/fixtures/personas.ts`, which the journeys type into the Debts step.
  - The five persona briefs in `docs/testing/persona-briefs/`, which tell the persona agents which creditors to enter.
  - The rename table in `docs/superpowers/specs/2026-10-16-forms-step3-personas.md`, which fixes the 13 fictional names, and spec section 9.
- Produces: each persona's creditors under their fictional names, the same in the seed, the brief and the E2E fixture. Task 10 and Task 11 rely on these names and write no real one:

  | Persona | Fictional creditors                                                                                                                                   |
  | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
  | Maria   | Brightwater Card Services; Larkfield General Hospital; Ironbridge Card Company. Her wages line now reads "Wages - CNA at Larkfield General Hospital". |
  | James   | Meridale National Bank; Crestway Auto Credit                                                                                                          |
  | Priya   | Silverpine Card Services; Westhaven University Medical Center                                                                                         |
  | DeShawn | Harrowgate Home Loans; Tallgrass Credit Management; Lakeline Electric; Southmoor Health                                                               |
  | Sarah   | Keelson Loan Servicing; Lakemont University Hospital                                                                                                  |

  - The seed's SOFA creditor-payment rows and the creditor-payment row that `sofa-journey.spec.ts` fills carry the new names (Brightwater Card Services, Ironbridge Card Company).
  - No test changes. The oracle tier 3 cases and `test_api_readback.py` print no creditor name, so no expected value moves.

**Decisions already made in this task:**

- Spec section 9 renames the five personas' private creditors, and Maria's employer, which carried the name of a real hospital. The seed, the five briefs, `personas.ts` and `sofa-journey.spec.ts` must agree, because the persona agents read the briefs and the journeys type the fixture. A mismatch would make a journey look for a creditor it never entered.
- Government creditors keep their real names, and so do the banks that hold a persona's own accounts. A government creditor is a public body with a public address, and a bank holding a persona's account is not a creditor of that persona.
- Unit tests, the scanned-bill schema example, the Amounts Owed placeholder, and the dated plans, specs and reports keep the real names. None is persona data and none carries an address, and a dated plan records what was true when it was written.
- Priya's "American Honda Finance (new)", which the rename table pairs with Kestrel Auto Finance, is not added. She has no such debt yet, and a rename adds no rows.
- No test expectation changes, because tier 3 and the API readback print no creditor name.

- [ ] **Step 1: Check that the real names are there**

A rename has no failing test before it, so this task has no red step. In its place, search the eight files for the real names.

```bash
set -eo pipefail
grep -n -i -E 'capital one|northwestern|discover|citibank|toyota fin|american express|rush univ|wells fargo|midland|comed|advocate|navient|university of illinois' backend/apps/intake/management/commands/seed_demo_data.py docs/testing/persona-briefs/deshawn-mitchell.md docs/testing/persona-briefs/james-washington.md docs/testing/persona-briefs/maria-torres.md docs/testing/persona-briefs/priya-sharma.md docs/testing/persona-briefs/sarah-chen.md frontend/e2e/fixtures/personas.ts frontend/e2e/journeys/sofa-journey.spec.ts | head -1
```

Expected: `"creditor_name": "Capital One",`, the first hit, in `seed_demo_data.py`. The search finds the real names in all eight files.

- [ ] **Step 2: Rename the creditors in the seed**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/management/commands/seed_demo_data.py b/backend/apps/intake/management/commands/seed_demo_data.py
index bccb607..52555c8 100644
--- a/backend/apps/intake/management/commands/seed_demo_data.py
+++ b/backend/apps/intake/management/commands/seed_demo_data.py
@@ -105,7 +105,7 @@ def _maria_torres() -> dict:
         ],
         "debts": [
             {
-                "creditor_name": "Capital One",
+                "creditor_name": "Brightwater Card Services",
                 "debt_type": "credit_card",
                 "amount_owed": Decimal("4200.00"),
                 "monthly_payment": Decimal("85.00"),
@@ -113,7 +113,7 @@ def _maria_torres() -> dict:
                 "consumer_business_classification": "consumer",
             },
             {
-                "creditor_name": "Northwestern Memorial Hospital",
+                "creditor_name": "Larkfield General Hospital",
                 "debt_type": "medical",
                 "amount_owed": Decimal("12800.00"),
                 "monthly_payment": Decimal("0.00"),
@@ -121,7 +121,7 @@ def _maria_torres() -> dict:
                 "consumer_business_classification": "consumer",
             },
             {
-                "creditor_name": "Discover Financial",
+                "creditor_name": "Ironbridge Card Company",
                 "debt_type": "personal_loan",
                 "amount_owed": Decimal("3500.00"),
                 "monthly_payment": Decimal("120.00"),
@@ -136,23 +136,23 @@ def _maria_torres() -> dict:
             "prior_income": [
                 {
                     "year": 2025,
-                    "source": "Wages - CNA at Northwestern Hospital",
+                    "source": "Wages - CNA at Larkfield General Hospital",
                     "gross_amount": Decimal("38400.00"),
                 },
                 {
                     "year": 2024,
-                    "source": "Wages - CNA at Northwestern Hospital",
+                    "source": "Wages - CNA at Larkfield General Hospital",
                     "gross_amount": Decimal("37000.00"),
                 },
             ],
             "creditor_payments": [
                 {
-                    "creditor_name": "Capital One",
+                    "creditor_name": "Brightwater Card Services",
                     "total_paid": Decimal("1020.00"),
                     "dates_of_payments": "Monthly Jan-Mar 2026",
                 },
                 {
-                    "creditor_name": "Discover Financial",
+                    "creditor_name": "Ironbridge Card Company",
                     "total_paid": Decimal("720.00"),
                     "dates_of_payments": "Monthly Jan-Mar 2026",
                 },
@@ -226,7 +226,7 @@ def _james_washington() -> dict:
         ],
         "debts": [
             {
-                "creditor_name": "Citibank",
+                "creditor_name": "Meridale National Bank",
                 "debt_type": "credit_card",
                 "amount_owed": Decimal("9800.00"),
                 "monthly_payment": Decimal("200.00"),
@@ -234,7 +234,7 @@ def _james_washington() -> dict:
                 "consumer_business_classification": "consumer",
             },
             {
-                "creditor_name": "Toyota Financial Services",
+                "creditor_name": "Crestway Auto Credit",
                 "debt_type": "auto_loan",
                 "amount_owed": Decimal("8500.00"),
                 "monthly_payment": Decimal("350.00"),
@@ -302,7 +302,7 @@ def _priya_sharma() -> dict:
         ],
         "debts": [
             {
-                "creditor_name": "American Express",
+                "creditor_name": "Silverpine Card Services",
                 "debt_type": "credit_card",
                 "amount_owed": Decimal("22000.00"),
                 "monthly_payment": Decimal("500.00"),
@@ -310,7 +310,7 @@ def _priya_sharma() -> dict:
                 "consumer_business_classification": "consumer",
             },
             {
-                "creditor_name": "Rush University Medical Center",
+                "creditor_name": "Westhaven University Medical Center",
                 "debt_type": "medical",
                 "amount_owed": Decimal("35000.00"),
                 "monthly_payment": Decimal("0.00"),
@@ -386,7 +386,7 @@ def _deshawn_mitchell() -> dict:
         ],
         "debts": [
             {
-                "creditor_name": "Wells Fargo Home Mortgage",
+                "creditor_name": "Harrowgate Home Loans",
                 "debt_type": "mortgage",
                 "amount_owed": Decimal("160000.00"),
                 "monthly_payment": Decimal("1200.00"),
@@ -396,7 +396,7 @@ def _deshawn_mitchell() -> dict:
                 "collateral_description": "Single-family home, 7823 S Sangamon St",
             },
             {
-                "creditor_name": "Midland Credit Management",
+                "creditor_name": "Tallgrass Credit Management",
                 "debt_type": "credit_card",
                 "amount_owed": Decimal("6700.00"),
                 "monthly_payment": Decimal("0.00"),
@@ -404,7 +404,7 @@ def _deshawn_mitchell() -> dict:
                 "consumer_business_classification": "consumer",
             },
             {
-                "creditor_name": "ComEd",
+                "creditor_name": "Lakeline Electric",
                 "debt_type": "utility",
                 "amount_owed": Decimal("800.00"),
                 "monthly_payment": Decimal("0.00"),
@@ -412,7 +412,7 @@ def _deshawn_mitchell() -> dict:
                 "consumer_business_classification": "consumer",
             },
             {
-                "creditor_name": "Advocate Health",
+                "creditor_name": "Southmoor Health",
                 "debt_type": "medical",
                 "amount_owed": Decimal("4200.00"),
                 "monthly_payment": Decimal("0.00"),
@@ -474,7 +474,7 @@ def _sarah_chen() -> dict:
         "assets": [],
         "debts": [
             {
-                "creditor_name": "Navient",
+                "creditor_name": "Keelson Loan Servicing",
                 "debt_type": "student_loan",
                 "amount_owed": Decimal("28000.00"),
                 "monthly_payment": Decimal("0.00"),
@@ -482,7 +482,7 @@ def _sarah_chen() -> dict:
                 "consumer_business_classification": "consumer",
             },
             {
-                "creditor_name": "University of Illinois Hospital",
+                "creditor_name": "Lakemont University Hospital",
                 "debt_type": "medical",
                 "amount_owed": Decimal("3400.00"),
                 "monthly_payment": Decimal("0.00"),
PATCH
```

The patch renames the 13 creditors, Maria's employer on her two wage lines, and the creditors on her SOFA payment rows. It changes strings only.

- [ ] **Step 3: Rename the creditors in the five briefs**

```bash
git apply <<'PATCH'
diff --git a/docs/testing/persona-briefs/deshawn-mitchell.md b/docs/testing/persona-briefs/deshawn-mitchell.md
index a5cc8e8..7e9a0c3 100644
--- a/docs/testing/persona-briefs/deshawn-mitchell.md
+++ b/docs/testing/persona-briefs/deshawn-mitchell.md
@@ -71,10 +71,10 @@ You ARE DeShawn Mitchell. Navigate DigniFi as he would.

 **Amounts Owed:**

-- Wells Fargo Home Mortgage — $160,000, paying $1,200/mo (secured by home)
-- Midland Credit Management credit card — $6,700, paying $0 (in collections)
-- ComEd utility — $800, paying $0 (in collections)
-- Advocate Health medical — $4,200, paying $0 (in collections)
+- Harrowgate Home Loans — $160,000, paying $1,200/mo (secured by home)
+- Tallgrass Credit Management credit card — $6,700, paying $0 (in collections)
+- Lakeline Electric utility — $800, paying $0 (in collections)
+- Southmoor Health medical — $4,200, paying $0 (in collections)

 ## What to Watch For

diff --git a/docs/testing/persona-briefs/james-washington.md b/docs/testing/persona-briefs/james-washington.md
index 01167d1..fbae27b 100644
--- a/docs/testing/persona-briefs/james-washington.md
+++ b/docs/testing/persona-briefs/james-washington.md
@@ -65,8 +65,8 @@ You ARE James Washington. Navigate DigniFi as he would.

 **Amounts Owed:**

-- Citibank credit card — $9,800, paying $200/mo
-- Toyota Financial Services auto loan — $8,500, paying $350/mo (secured by vehicle)
+- Meridale National Bank credit card — $9,800, paying $200/mo
+- Crestway Auto Credit auto loan — $8,500, paying $350/mo (secured by vehicle)

 ## What to Watch For

diff --git a/docs/testing/persona-briefs/maria-torres.md b/docs/testing/persona-briefs/maria-torres.md
index 213e0f5..c590e88 100644
--- a/docs/testing/persona-briefs/maria-torres.md
+++ b/docs/testing/persona-briefs/maria-torres.md
@@ -66,9 +66,9 @@ You ARE Maria Torres. Navigate DigniFi as she would.

 **Amounts Owed:**

-- Capital One credit card — $4,200, paying $85/mo (in collections)
-- Northwestern Memorial Hospital — $12,800, paying $0 (in collections)
-- Discover Financial personal loan — $3,500, paying $120/mo
+- Brightwater Card Services credit card — $4,200, paying $85/mo (in collections)
+- Larkfield General Hospital — $12,800, paying $0 (in collections)
+- Ironbridge Card Company personal loan — $3,500, paying $120/mo

 ## What to Watch For

diff --git a/docs/testing/persona-briefs/priya-sharma.md b/docs/testing/persona-briefs/priya-sharma.md
index 5175363..40828dd 100644
--- a/docs/testing/persona-briefs/priya-sharma.md
+++ b/docs/testing/persona-briefs/priya-sharma.md
@@ -67,8 +67,8 @@ You ARE Priya Sharma. Navigate DigniFi as she would.

 **Amounts Owed:**

-- American Express credit card — $22,000, paying $500/mo
-- Rush University Medical Center — $35,000, paying $0 (in collections)
+- Silverpine Card Services credit card — $22,000, paying $500/mo
+- Westhaven University Medical Center — $35,000, paying $0 (in collections)

 ## What to Watch For

diff --git a/docs/testing/persona-briefs/sarah-chen.md b/docs/testing/persona-briefs/sarah-chen.md
index 618153f..ea02597 100644
--- a/docs/testing/persona-briefs/sarah-chen.md
+++ b/docs/testing/persona-briefs/sarah-chen.md
@@ -62,8 +62,8 @@ You ARE Sarah Chen. Navigate DigniFi as she would.

 **Amounts Owed:**

-- Navient student loan — $28,000, paying $0
-- University of Illinois Hospital medical — $3,400, paying $0 (in collections)
+- Keelson Loan Servicing student loan — $28,000, paying $0
+- Lakemont University Hospital medical — $3,400, paying $0 (in collections)

 ## What to Watch For

PATCH
```

Each brief now names the creditors its persona's seed and fixture carry, so a persona agent enters what the journey enters.

- [ ] **Step 4: Rename the creditors in the E2E fixture and the SOFA journey**

```bash
git apply <<'PATCH'
diff --git a/frontend/e2e/fixtures/personas.ts b/frontend/e2e/fixtures/personas.ts
index d8aa3e5..05530c9 100644
--- a/frontend/e2e/fixtures/personas.ts
+++ b/frontend/e2e/fixtures/personas.ts
@@ -127,21 +127,21 @@ export const MARIA: WaiverPersonaData = {
   ],
   debts: [
     {
-      creditor_name: 'Capital One',
+      creditor_name: 'Brightwater Card Services',
       debt_type: 'credit_card',
       amount_owed: 4200,
       monthly_payment: 85,
       is_in_collections: true,
     },
     {
-      creditor_name: 'Northwestern Memorial Hospital',
+      creditor_name: 'Larkfield General Hospital',
       debt_type: 'medical',
       amount_owed: 12800,
       monthly_payment: 0,
       is_in_collections: true,
     },
     {
-      creditor_name: 'Discover Financial',
+      creditor_name: 'Ironbridge Card Company',
       debt_type: 'personal_loan',
       amount_owed: 3500,
       monthly_payment: 120,
@@ -207,14 +207,14 @@ export const JAMES: PersonaData = {
   ],
   debts: [
     {
-      creditor_name: 'Citibank',
+      creditor_name: 'Meridale National Bank',
       debt_type: 'credit_card',
       amount_owed: 9800,
       monthly_payment: 200,
       is_in_collections: false,
     },
     {
-      creditor_name: 'Toyota Financial Services',
+      creditor_name: 'Crestway Auto Credit',
       debt_type: 'auto_loan',
       amount_owed: 8500,
       monthly_payment: 350,
@@ -276,14 +276,14 @@ export const PRIYA: PersonaData = {
   ],
   debts: [
     {
-      creditor_name: 'American Express',
+      creditor_name: 'Silverpine Card Services',
       debt_type: 'credit_card',
       amount_owed: 22000,
       monthly_payment: 500,
       is_in_collections: false,
     },
     {
-      creditor_name: 'Rush University Medical Center',
+      creditor_name: 'Westhaven University Medical Center',
       debt_type: 'medical',
       amount_owed: 35000,
       monthly_payment: 0,
@@ -349,7 +349,7 @@ export const DESHAWN: WaiverPersonaData = {
   ],
   debts: [
     {
-      creditor_name: 'Wells Fargo Home Mortgage',
+      creditor_name: 'Harrowgate Home Loans',
       debt_type: 'mortgage',
       amount_owed: 160000,
       monthly_payment: 1200,
@@ -357,21 +357,21 @@ export const DESHAWN: WaiverPersonaData = {
       collateral_description: 'Single-family home, 7823 S Sangamon St',
     },
     {
-      creditor_name: 'Midland Credit Management',
+      creditor_name: 'Tallgrass Credit Management',
       debt_type: 'credit_card',
       amount_owed: 6700,
       monthly_payment: 0,
       is_in_collections: true,
     },
     {
-      creditor_name: 'ComEd',
+      creditor_name: 'Lakeline Electric',
       debt_type: 'utility',
       amount_owed: 800,
       monthly_payment: 0,
       is_in_collections: true,
     },
     {
-      creditor_name: 'Advocate Health',
+      creditor_name: 'Southmoor Health',
       debt_type: 'medical',
       amount_owed: 4200,
       monthly_payment: 0,
@@ -425,14 +425,14 @@ export const SARAH: WaiverPersonaData = {
   assets: [],
   debts: [
     {
-      creditor_name: 'Navient',
+      creditor_name: 'Keelson Loan Servicing',
       debt_type: 'student_loan',
       amount_owed: 28000,
       monthly_payment: 0,
       is_in_collections: false,
     },
     {
-      creditor_name: 'University of Illinois Hospital',
+      creditor_name: 'Lakemont University Hospital',
       debt_type: 'medical',
       amount_owed: 3400,
       monthly_payment: 0,
diff --git a/frontend/e2e/journeys/sofa-journey.spec.ts b/frontend/e2e/journeys/sofa-journey.spec.ts
index addf3e9..54f48af 100644
--- a/frontend/e2e/journeys/sofa-journey.spec.ts
+++ b/frontend/e2e/journeys/sofa-journey.spec.ts
@@ -103,7 +103,7 @@ test.describe('SOFA — Form 107 Financial History', () => {
     // Toggle Creditor Payments on and fill a row
     await sofa.toggleCreditorPayments(true);
     await sofa.addCreditorPaymentRow({
-      creditorName: 'Capital One',
+      creditorName: 'Brightwater Card Services',
       totalPaid: '1500',
       datesOfPayments: 'Monthly Jan-Mar 2026',
     });
PATCH
```

`personas.ts` carries the same names as the seed. `sofa-journey.spec.ts` fills its creditor-payment row with the new name for the card issuer.

- [ ] **Step 5: Check that no real name is left**

```bash
set -eo pipefail
! grep -n -i -E 'capital one|northwestern|discover|citibank|toyota fin|american express|rush univ|wells fargo|midland|comed|advocate|navient|university of illinois' backend/apps/intake/management/commands/seed_demo_data.py docs/testing/persona-briefs/deshawn-mitchell.md docs/testing/persona-briefs/james-washington.md docs/testing/persona-briefs/maria-torres.md docs/testing/persona-briefs/priya-sharma.md docs/testing/persona-briefs/sarah-chen.md frontend/e2e/fixtures/personas.ts frontend/e2e/journeys/sofa-journey.spec.ts
echo "no real creditor names left"
```

Expected: `no real creditor names left`.

- [ ] **Step 6: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2135 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  389 passed (389)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

The 25 skips are the Postgres-only tests under sqlite. The next command runs them against the Postgres database named in `.claude/forms-step3a1.env`.

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

This task changes only persona data and no page flow, so the journeys don't run here. Task 11 runs them with these names.

- [ ] **Step 7: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/intake/management/commands/seed_demo_data.py \
  docs/testing/persona-briefs/deshawn-mitchell.md \
  docs/testing/persona-briefs/james-washington.md \
  docs/testing/persona-briefs/maria-torres.md \
  docs/testing/persona-briefs/priya-sharma.md \
  docs/testing/persona-briefs/sarah-chen.md \
  frontend/e2e/fixtures/personas.ts \
  frontend/e2e/journeys/sofa-journey.spec.ts
git commit -F - <<'MSG'
chore(personas): fictional names for the personas' private creditors

The seed, the five persona briefs, the E2E persona fixture and the SOFA
journey now use the fictional creditor names from the personas doc's
rename table (13 creditors, plus Maria's employer, now Larkfield General
Hospital). Government creditors and the personas' own banks are not
renamed. Frontend, documents, eligibility and intake unit tests, the
scanned-bill schema example and the Amounts Owed placeholder are left
as they are. No test changed: tier 3 and the API readback never print a
creditor name.
MSG
git status --short
```

### Task 10: Add Andrés Kettleby, a gig driver, to the demo seed

_Built and verified as commit `eb3918e` on `plan/forms-step3a1`._

**Files:**

- Create: `docs/testing/persona-briefs/andres-kettleby.md`
- Modify: `backend/apps/forms/tests/test_api_readback.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier3.py`
- Modify: `backend/apps/intake/management/commands/seed_demo_data.py`

**Interfaces:**

- Consumes:
  - `PERSONAS` in `backend/apps/intake/management/commands/seed_demo_data.py`: each key maps to a function that returns one persona's dict, with `username`, `email`, `first_name`, `last_name`, `debtor`, `income`, `expenses`, `assets`, `debts`, and optional `sofa` and `fee_waiver`. `--persona` takes its choices from the keys. `_create_persona` creates the rows, runs `MeansTestCalculator`, and before this task creates a `FeeWaiverApplication` from `data["fee_waiver"]` for every persona the means test qualifies.
  - `IncomeInfo.SOURCE_FIELDS` (`backend/apps/intake/models.py`), the Income step's ten amounts.
  - Task 1's median table: the `ilnd_2025_data` row in force on the tests' pinned fill date, 2026-10-16, runs from 2026-04-01 through 2026-10-31, and its `family_size_2` is 93934.00.
  - Task 9's rule: a persona's private creditors carry fictional names. His come from the personas doc.
  - `backend/apps/forms/tests/test_api_readback.py`: `WAIVER_FILERS = {"maria", "deshawn", "sarah"}` drives both the fee-waiver POST and the qualifies assert, and `test_forms_built_through_the_api_print_what_the_seeded_forms_print` is parametrized over `list(PERSONAS)`.
  - `backend/apps/forms/tests/test_oracle_tier3.py`: `EXPECTED` (persona → form type → full name → printed value), `BELOW_MEDIAN`, and `_printed(persona)`, which runs `call_command("seed_demo_data", "--reset", persona=persona)` and fills the persona's forms. Each case's id is `<form type>:<full name>:<persona>`.
  - The personas doc (`docs/superpowers/specs/2026-10-16-forms-step3-personas.md`), section "Andrés Kettleby": "2. Per PR", item 3a1, the brief's table "Your Data (enter this exactly)", and "3. Outcome changes".
- Produces:
  - `_andres_kettleby()` and `PERSONAS["andres"]`: username `demo_andres`, SSN 900-66-0006, phone 630-555-0161, `household_size` 2, `filing_type` individual, every income source 0.00 except `monthly_other_income` 3370.00, the 13 expenses (2,779), four assets, the Copperline Auto Finance loan (D 2.1) and nine nonpriority debts (E/F 4.1–4.9). No `fee_waiver` or `sofa` key.
  - In `_create_persona`: a `FeeWaiverApplication` only when `result["qualifies_for_fee_waiver"] and "fee_waiver" in data`.
  - In `test_api_readback.py`: `QUALIFIES = {"maria", "deshawn", "sarah", "andres"}` and `APPLIES = {"maria", "deshawn", "sarah"}` replace `WAIVER_FILERS`, and the readback gains the case `test_forms_built_through_the_api_print_what_the_seeded_forms_print[andres]`.
  - In `test_oracle_tier3.py`: an `"andres"` block in `EXPECTED`, which makes 30 cases of `test_persona_packet_prints_the_right_figure`, each id ending `:andres`:
    - `form_106sum`: `1a`, `1b`, `1c`, `2`, `3a`, `3b`, `3c`, `4`, `5`;
    - `form_122a1`: `CheckBox1`, `terrorism If necessary list other sources on a separate page and put the total below 1`, `Debto1.Quest10A`, `Debto1.Quest11`, `Quest11`, `12B`, `13A`, `13B`, `13C`, `14a`;
    - `schedule_i`: `Other income 8h`, `Amount 8h Debtor 1`, `Amount 10 Debtor 1`, `Amount 10`, `Amount 12`;
    - `schedule_j`: `17a`, `22a`, `22c`, `23a`, `23b`, `23c`.
  - `docs/testing/persona-briefs/andres-kettleby.md`. Task 11 builds its `ANDRES` fixture from this brief's table "Your Data (enter this exactly)", its **Assets** list and its **Amounts Owed** list, with the fixture's own SSN, 900-66-6006, in place of the seed's. The vehicle's description is "2017 Honda Fit", the text before the dash.

**Decisions already made in this task:**

- **The owner's calls, word for word from spec §2:**
  - **3a1.Q1, where Andrés's driving income goes until 3e2: other income.**
    - His net business income, $3,370 a month, is `monthly_other_income` in both the seed and the journey. No income source is business income yet, and the wages box is ruled out.
    - It prints as "Other income" on Schedule I line 8h and 122A-1 line 10. His income figure (CMI), his below-median result and his fee routing are final from 3a1. 3e2 moves the amount to the business lines.
    - The E2E page object types each persona's income into its own box. The other five keep wages.
  - **3a1.Q2, his fee answer until 3f: no application.**
    - He means to pay in installments, but today's 60%-of-median flag says he qualifies for a waiver, so Complete sends him to `/fee-waiver`.
    - The seed files no fee-waiver application for a persona without fee-waiver data. This also removes today's `KeyError` (`seed_demo_data.py:611`) for James or Priya, should either ever qualify.
    - His journey checks that he lands on `/fee-waiver`, goes on to `/sofa` and `/forms` by URL, and expects 14 forms, without 103B.
    - Until 3f, `test_api_readback.py` keeps "qualifies under today's flag" apart from "applied".
- **The seed files a fee-waiver application only for a persona with `fee_waiver` data.** The guard is `result["qualifies_for_fee_waiver"] and "fee_waiver" in data`. Andrés qualifies under today's flag (0.6 × $93,934 = $56,360.40, above his $40,440) but has no `fee_waiver` key, so he gets no application, and `**data["fee_waiver"]` can no longer raise a `KeyError` for a qualifying persona without answers. The qualifies test stays, so the change is the smallest one that does this. The implementer proved the guard: with his persona and the tests in place but no guard, `-k andres` over tier 3 and the readback gave 31 failures, each a `KeyError: 'fee_waiver'`.
- **The readback keeps "qualifies" apart from "applied".** `QUALIFIES` drives the qualifies assert, and `APPLIES` drives the fee-waiver POST and the `is None` assert. Together with `_fee_waiver_answers(built) == _fee_waiver_answers(seeded)`, they prove that the seed stores no application for him. Step 3f joins the two sets again.
- **106Sum line 1a prints 0.00, because it is a total.** 1a copies Schedule A/B line 55 (rule `total_real_property`). The Assets step asks about real estate, and he has none, so line 55 totals an answered question at $0. CLAUDE.md's "Blank, not 0.00" says "A total counts an unasked line as zero and still prints". `test_schedule_a_b_schema.py` already requires 1a to equal A/B line 55, and `test_form_106sum_schema.py` already expects `"0.00"` for a filer with no real estate. The other personas without real estate leave 1a out of tier 3; that is an omission, not a different ruling.
- **His packet is 14 forms:** 101, 106Dec, 106Sum, 107, 121, 122A-1, A/B, C, D, E/F, G, H, I and J. It has no 103B, because he files no application, and no 122A-2, because he is below the median. The readback asserts that the packet built through the API equals the seeded one, not its size. The implementer checked the 14 with a scratch test that was never staged, and Task 11's journey asserts it.
- **His SSN and phone are synthetic** (G2): 900-66-0006 is in the IRS-reserved 900 range, and 630-555-0161 is in the 555-0100–0199 fiction block. His email is on demo.dignifi.org. His private creditors carry the personas doc's fictional names, and the Illinois State Toll Highway Authority, a government creditor, keeps its real name (spec §9).
- **The brief is cut to 3a1.** It keeps his story and asks only what today's wizard asks: his identity, the Other Monthly Income box with every other income box at $0, the nine expenses above $0, the four assets and the ten amounts owed, each as the seed has it. His story still gives his driving receipts and costs, but as entries it leaves out the county, creditor addresses, the household list, the business figures, the IRS row, Ashgrove (the party to notify about the medical bill), Schedules G and H, the 3e2 expense lines and the 3b assets, and it tells him to leave Contracts and Codebtors empty. An eligible filer's fee-waiver page offers no way on without applying until 3f (`FeeWaiverPage.tsx` shows its go-on button only to a filer who doesn't qualify), so the brief tells him to note it and open his forms page, `/forms`, directly. Its watch item "Does the fee waiver page let you go on without applying?" stays.
- **`priority_classification` on his secured loan keeps the model default, "unsecured", as James's does.** The wizard sends "secured" for an `auto_loan`, but no form or derivation reads the field, and the readback sends the seed's value, so the seeded and the API-built sessions agree.
- **The seed also carries what no form reads yet:** the Fit's `amount_owed` of 7,800 (every `amount_owed` total reads `DebtInfo`), `marital_status` and `number_of_dependents`, `is_in_collections` on Calumet Ridge Medical Center, and "business" on Driveline Tire & Auto (step 4 asks it). The income is written as `**dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00"))` followed by the other income, so every source is a typed $0.
- **Tier 3 covers the boxes 3a1 prints** (spec §8): 122A-1 lines 10 to 14 and the page-1 result, Schedule I lines 8h, 10 and 12, Schedule J lines 17a and 22 to 23, and 106Sum lines 1 to 5. It has no Form 101 cases, which the task doesn't list and whose `_common()` address is Chicago's. Blank columns are left out, except 106Sum 3a, which the personas doc names. Every figure was worked out by hand before its case was written, and agrees with the personas doc's "3. Outcome changes" and the spec §3.8 row (household 2, $40,440 a year, median $93,934, below the median, qualifies). All 30 passed on their first run, so no figure was fitted to the code. The implementer's mutations each turned cases red: his 3,370 typed as wages (4 cases), `vehicle_payment` at 0 (6), Driveline's 1,180 as 1,181 (2), and `QUALIFIES` without him (the readback).
- **The review's fix round changed only the brief:** the fee step's way on to `/forms`, the vehicle line, whose text before the dash now matches the seed's description, and the Contracts and Codebtors line.

**The working for the tier 3 figures.** From the seed: income 3,370 (other income; every other source 0); expenses 1150 + 210 + 0 + 389 + 165 + 60 + 520 + 60 + 45 + 180 + 0 + 0 + 0 = 2,779; personal property 4300 + 1900 + 412 + 85 = 6,697, and no real estate; secured debt 7,800; unsecured debt 640 + 3850 + 1180 + 380 + 4100 + 6420 + 1760 + 1850 + 2980 = 23,160. Money compares as a number, and a blank figure means the box shows nothing.

| Line                              | Box                                                                                      | Figure                   | How it is reached                                                    |
| --------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------ | -------------------------------------------------------------------- |
| 122A-1 line 10, source            | `terrorism If necessary list other sources on a separate page and put the total below 1` | Other income             | his only source above $0 is other income (rule `other_income_label`) |
| 122A-1 line 10, Column A          | `Debto1.Quest10A`                                                                        | 3370.00                  | `monthly_other_income`                                               |
| 122A-1 line 11, Column A          | `Debto1.Quest11`                                                                         | 3370.00                  | CMI: the ten sources less Social Security, all $0 but 3,370          |
| 122A-1 lines 11 and 12a (one box) | `Quest11`                                                                                | 3370.00                  | Column A plus no Column B                                            |
| 122A-1 line 12b                   | `12B`                                                                                    | 40440.00                 | 3,370 × 12                                                           |
| 122A-1 line 13, state             | `13A`                                                                                    | IL                       | his address                                                          |
| 122A-1 line 13, household         | `13B`                                                                                    | 2                        | `household_size`: him and his daughter                               |
| 122A-1 line 13, median            | `13C`                                                                                    | 93934.00                 | Illinois, household of 2, the table in force on 2026-10-16           |
| 122A-1 line 14                    | `14a`                                                                                    | /12b less or equal to 13 | 40,440 ≤ 93,934                                                      |
| 122A-1 page 1                     | `CheckBox1`                                                                              | /No Abuse                | below the median: box 1, no presumption of abuse                     |
| Schedule I line 8h, specify       | `Other income 8h`                                                                        | Other income             | the other-income label                                               |
| Schedule I line 8h                | `Amount 8h Debtor 1`                                                                     | 3370.00                  | `monthly_other_income`                                               |
| Schedule I line 10, Debtor 1      | `Amount 10 Debtor 1`                                                                     | 3370.00                  | line 7 plus line 9: the ten sources, Social Security included        |
| Schedule I line 10, both columns  | `Amount 10`                                                                              | 3370.00                  | Debtor 1 plus no Debtor 2                                            |
| Schedule I line 12                | `Amount 12`                                                                              | 3370.00                  | line 10 plus line 11, which is never asked                           |
| Schedule J line 17a               | `17a`                                                                                    | 389.00                   | `vehicle_payment`, the Corolla lease                                 |
| Schedule J lines 22a, 22c and 23b | `22a`, `22c`, `23b`                                                                      | 2779.00                  | the 13 expenses; 22b is never asked                                  |
| Schedule J line 23a               | `23a`                                                                                    | 3370.00                  | Schedule I line 12                                                   |
| Schedule J line 23c               | `23c`                                                                                    | 591.00                   | 3,370 − 2,779                                                        |
| 106Sum line 1a                    | `1a`                                                                                     | 0.00                     | A/B line 55: no real estate, a total                                 |
| 106Sum line 1b                    | `1b`                                                                                     | 6697.00                  | A/B line 62: 4,300 + 1,900 + 412 + 85                                |
| 106Sum line 1c                    | `1c`                                                                                     | 6697.00                  | 1a + 1b                                                              |
| 106Sum line 2                     | `2`                                                                                      | 7800.00                  | Schedule D Column A: the Copperline loan                             |
| 106Sum line 3a                    | `3a`                                                                                     | blank                    | E/F 6e, priority claims, never asked until 3d                        |
| 106Sum line 3b                    | `3b`                                                                                     | 23160.00                 | E/F 6j: the nine unsecured debts                                     |
| 106Sum line 3c                    | `3c`                                                                                     | 30960.00                 | 7,800 + 0 + 23,160                                                   |
| 106Sum line 4                     | `4`                                                                                      | 3370.00                  | Schedule I line 12                                                   |
| 106Sum line 5                     | `5`                                                                                      | 2779.00                  | Schedule J line 22c                                                  |

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_oracle_tier3.py b/backend/apps/forms/tests/test_oracle_tier3.py
index badae7f..fb9b9bf 100644
--- a/backend/apps/forms/tests/test_oracle_tier3.py
+++ b/backend/apps/forms/tests/test_oracle_tier3.py
@@ -211,6 +211,47 @@ EXPECTED = {
             "23c": "720.00",
         },
     },
+    # His net driving income is other income until step 3e2 (3a1 spec §2, 3a1.Q1).
+    "andres": {
+        "form_106sum": {
+            "1a": "0.00",
+            "1b": "6697.00",
+            "1c": "6697.00",
+            "2": "7800.00",
+            "3a": "",
+            "3b": "23160.00",
+            "3c": "30960.00",
+            "4": "3370.00",
+            "5": "2779.00",
+        },
+        "form_122a1": {
+            "CheckBox1": "/No Abuse",
+            "terrorism If necessary list other sources on a separate page and put the total below 1": "Other income",
+            "Debto1.Quest10A": "3370.00",
+            "Debto1.Quest11": "3370.00",
+            "Quest11": "3370.00",
+            "12B": "40440.00",
+            "13A": "IL",
+            "13B": "2",
+            "13C": "93934.00",
+            "14a": BELOW_MEDIAN,
+        },
+        "schedule_i": {
+            "Other income 8h": "Other income",
+            "Amount 8h Debtor 1": "3370.00",
+            "Amount 10 Debtor 1": "3370.00",
+            "Amount 10": "3370.00",
+            "Amount 12": "3370.00",
+        },
+        "schedule_j": {
+            "17a": "389.00",
+            "22a": "2779.00",
+            "22c": "2779.00",
+            "23a": "3370.00",
+            "23b": "2779.00",
+            "23c": "591.00",
+        },
+    },
 }


PATCH
```

His block holds the 30 figures in the table above, each read back from the filled PDF.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_api_readback.py b/backend/apps/forms/tests/test_api_readback.py
index e9788cd..6a59505 100644
--- a/backend/apps/forms/tests/test_api_readback.py
+++ b/backend/apps/forms/tests/test_api_readback.py
@@ -34,8 +34,11 @@ from apps.intake.models import IncomeInfo, IntakeSession
 User = get_user_model()

 # The means test qualifies these personas for a fee waiver, so after Complete the wizard
-# sends them to the fee-waiver page, and the seed gives them an application.
-WAIVER_FILERS = {"maria", "deshawn", "sarah"}
+# sends them to the fee-waiver page.
+QUALIFIES = {"maria", "deshawn", "sarah", "andres"}
+# These apply for the waiver there, and the seed gives them an application. Andrés means to
+# pay in installments (3a1 spec §2, 3a1.Q2), so the two sets differ until step 3f.
+APPLIES = {"maria", "deshawn", "sarah"}

 # Each wizard step's session save: (the section it sends, the persona's data for it).
 WIZARD_STEPS = [
@@ -108,7 +111,7 @@ def _send_through_the_api(persona):
     # No means-test call: Generate All works it out from the stored intake (spec §5.6).
     response = client.post(f"{session_url}complete/")
     assert response.status_code == 200, response.data
-    if persona in WAIVER_FILERS:
+    if persona in APPLIES:
         response = client.post(
             "/api/intake/fee-waiver/",
             {"session": session_id, **_sent(_fee_waiver_application(data))},
@@ -127,7 +130,7 @@ def _send_through_the_api(persona):
     # Generate All worked the means test out, and it qualifies exactly the filers the wizard
     # sends to the fee-waiver page.
     qualifies = MeansTest.objects.get(session_id=session_id).qualifies_for_fee_waiver
-    assert qualifies == (persona in WAIVER_FILERS)
+    assert qualifies == (persona in QUALIFIES)
     return session_id, [form["form_type"] for form in generated.data["generated"]]


@@ -180,7 +183,7 @@ def test_forms_built_through_the_api_print_what_the_seeded_forms_print(persona):
     # "cannot pay" answers, so the stored applications are compared directly.
     built = IntakeSession.objects.get(pk=session_id)
     assert _fee_waiver_answers(built) == _fee_waiver_answers(seeded)
-    assert (_fee_waiver_answers(built) is None) == (persona not in WAIVER_FILERS)
+    assert (_fee_waiver_answers(built) is None) == (persona not in APPLIES)
     # Only Priya's income is above the median, so only her packet holds 122A-2, and it
     # prints her own figures: her monthly income on line 1 and her childcare on line 21.
     assert ("form_122a2" in stored) == (persona == "priya")
PATCH
```

`QUALIFIES` names the filers today's flag sends to the fee-waiver page, and `APPLIES` the ones who apply there and get an application in the seed.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=line -rN --disable-warnings apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_api_readback.py -k andres -q -p no:cacheprovider 2>&1 | tail -5
```

Expected: FAIL — `30 failed, 154 deselected`. Each tier 3 case fails on `KeyError: 'andres'`, because the seed has no persona by that name.

`_printed` seeds him through `call_command`, which passes `persona=` straight to `handle` without checking it against `--persona`'s choices, so the lookup in `PERSONAS` raises. The readback is parametrized over `list(PERSONAS)`, so it has no case for him until the seed does.

- [ ] **Step 3: Add Andrés to the seed**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/management/commands/seed_demo_data.py b/backend/apps/intake/management/commands/seed_demo_data.py
index 52555c8..89d8017 100644
--- a/backend/apps/intake/management/commands/seed_demo_data.py
+++ b/backend/apps/intake/management/commands/seed_demo_data.py
@@ -1,4 +1,4 @@
-"""Seed 5 synthetic personas for partner demos and E2E testing.
+"""Seed 6 synthetic personas for partner demos and E2E testing.

 Each persona exercises a distinct eligibility path through the ILND
 means test calculator and form generation pipeline.  SSNs use the
@@ -499,12 +499,177 @@ def _sarah_chen() -> dict:
     }


+def _andres_kettleby() -> dict:
+    """Gig driver, below median. Qualifies for a fee waiver but pays in installments."""
+    return {
+        "username": "demo_andres",
+        "email": "andres.kettleby@demo.dignifi.org",
+        "first_name": "Andrés",
+        "last_name": "Kettleby",
+        "debtor": {
+            "first_name": "Andrés",
+            "last_name": "Kettleby",
+            "middle_name": "J",
+            "ssn": "900-66-0006",
+            "date_of_birth": date(1988, 4, 12),
+            "phone": "630-555-0161",
+            "email": "andres.kettleby@demo.dignifi.org",
+            "street_address": "1418 Marquette Ave Apt 2",
+            "city": "Aurora",
+            "state": "IL",
+            "zip_code": "60505",
+            "household_size": 2,
+            "filing_type": "individual",
+        },
+        "income": {
+            "marital_status": "single",
+            "number_of_dependents": 1,
+            # His net driving income ($4,200 from the apps less $830 of driving costs) is
+            # other income until the Income step asks for business income (3a1.Q1).
+            **dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00")),
+            "monthly_other_income": Decimal("3370.00"),
+        },
+        "expenses": {
+            "rent_or_mortgage": Decimal("1150.00"),
+            "utilities": Decimal("210.00"),
+            "home_maintenance": Decimal("0.00"),
+            # The Corolla lease, his only car
+            "vehicle_payment": Decimal("389.00"),
+            "vehicle_insurance": Decimal("165.00"),
+            "vehicle_maintenance": Decimal("60.00"),
+            "food_and_groceries": Decimal("520.00"),
+            "clothing": Decimal("60.00"),
+            "medical_expenses": Decimal("45.00"),
+            "childcare": Decimal("180.00"),
+            "child_support_paid": Decimal("0.00"),
+            "insurance_not_deducted": Decimal("0.00"),
+            "other_expenses": Decimal("0.00"),
+        },
+        "assets": [
+            {
+                "asset_type": "vehicle",
+                "description": "2017 Honda Fit",
+                # His half of a car titled to him and his brother
+                "current_value": Decimal("4300.00"),
+                "amount_owed": Decimal("7800.00"),
+            },
+            {
+                "asset_type": "personal_property",
+                "description": "Household goods, electronics and clothing",
+                "current_value": Decimal("1900.00"),
+                "amount_owed": Decimal("0.00"),
+            },
+            {
+                "asset_type": "bank_account",
+                "description": "Harborline Bank checking",
+                "current_value": Decimal("412.00"),
+                "amount_owed": Decimal("0.00"),
+                "financial_institution": "Harborline Bank",
+            },
+            {
+                "asset_type": "bank_account",
+                "description": "Prairie Line Credit Union share savings",
+                "current_value": Decimal("85.00"),
+                "amount_owed": Decimal("0.00"),
+                "financial_institution": "Prairie Line Credit Union",
+            },
+        ],
+        "debts": [
+            {
+                "creditor_name": "Copperline Auto Finance",
+                "debt_type": "auto_loan",
+                "amount_owed": Decimal("7800.00"),
+                # His brother drives the car and pays the loan he co-signed
+                "monthly_payment": Decimal("0.00"),
+                "is_in_collections": False,
+                "consumer_business_classification": "consumer",
+                "is_secured": True,
+                "collateral_description": "2017 Honda Fit, co-owned with my brother",
+            },
+            {
+                "creditor_name": "Bright Signal Wireless",
+                "debt_type": "utility",
+                "amount_owed": Decimal("640.00"),
+                "monthly_payment": Decimal("0.00"),
+                "is_in_collections": False,
+                "consumer_business_classification": "consumer",
+            },
+            {
+                "creditor_name": "Calumet Ridge Medical Center",
+                "debt_type": "medical",
+                "amount_owed": Decimal("3850.00"),
+                "monthly_payment": Decimal("0.00"),
+                "is_in_collections": True,
+                "consumer_business_classification": "consumer",
+            },
+            {
+                "creditor_name": "Driveline Tire & Auto",
+                "debt_type": "credit_card",
+                "amount_owed": Decimal("1180.00"),
+                "monthly_payment": Decimal("0.00"),
+                "is_in_collections": False,
+                "consumer_business_classification": "business",
+            },
+            {
+                "creditor_name": "Illinois State Toll Highway Authority",
+                "debt_type": "other",
+                "amount_owed": Decimal("380.00"),
+                "monthly_payment": Decimal("0.00"),
+                "is_in_collections": False,
+                "consumer_business_classification": "consumer",
+            },
+            {
+                "creditor_name": "Meridian Lending Co.",
+                "debt_type": "personal_loan",
+                "amount_owed": Decimal("4100.00"),
+                "monthly_payment": Decimal("0.00"),
+                "is_in_collections": False,
+                "consumer_business_classification": "consumer",
+            },
+            {
+                "creditor_name": "Northgate Card Services",
+                "debt_type": "credit_card",
+                "amount_owed": Decimal("6420.00"),
+                "monthly_payment": Decimal("0.00"),
+                "is_in_collections": False,
+                "consumer_business_classification": "consumer",
+            },
+            {
+                "creditor_name": "Prairie Line Credit Union",
+                "debt_type": "credit_card",
+                "amount_owed": Decimal("1760.00"),
+                "monthly_payment": Decimal("0.00"),
+                "is_in_collections": False,
+                "consumer_business_classification": "consumer",
+            },
+            {
+                "creditor_name": "Ridgeway Apartments LLC",
+                "debt_type": "other",
+                "amount_owed": Decimal("1850.00"),
+                "monthly_payment": Decimal("0.00"),
+                "is_in_collections": False,
+                "consumer_business_classification": "consumer",
+            },
+            {
+                "creditor_name": "Sablewood Bank",
+                "debt_type": "credit_card",
+                "amount_owed": Decimal("2980.00"),
+                "monthly_payment": Decimal("0.00"),
+                "is_in_collections": False,
+                "consumer_business_classification": "consumer",
+            },
+        ],
+        # No "fee_waiver": he means to pay the fee in installments (3a1.Q2).
+    }
+
+
 PERSONAS: dict[str, Callable[[], dict]] = {
     "maria": _maria_torres,
     "james": _james_washington,
     "priya": _priya_sharma,
     "deshawn": _deshawn_mitchell,
     "sarah": _sarah_chen,
+    "andres": _andres_kettleby,
 }


@@ -512,7 +677,7 @@ PERSONAS: dict[str, Callable[[], dict]] = {


 class Command(BaseCommand):
-    help = "Seed 5 synthetic demo personas for partner demos and E2E testing."
+    help = "Seed 6 synthetic demo personas for partner demos and E2E testing."

     def add_arguments(self, parser):
         parser.add_argument(
@@ -524,7 +689,7 @@ class Command(BaseCommand):
             "--persona",
             type=str,
             choices=list(PERSONAS.keys()),
-            help="Seed a single persona instead of all 5",
+            help="Seed a single persona instead of all 6",
         )

     def handle(self, *args, **options):
@@ -618,9 +783,9 @@ class Command(BaseCommand):
         calculator = MeansTestCalculator(session)
         result = calculator.calculate()

-        # Create FeeWaiverApplication for fee-waiver-eligible personas
-        # (required by Form 103B generator)
-        if result["qualifies_for_fee_waiver"]:
+        # Create FeeWaiverApplication for fee-waiver-eligible personas who apply
+        # (required by Form 103B generator); one with no "fee_waiver" answers doesn't
+        if result["qualifies_for_fee_waiver"] and "fee_waiver" in data:
             FeeWaiverApplication.objects.create(
                 session=session,
                 household_size=data["debtor"]["household_size"],
PATCH
```

The patch adds `_andres_kettleby()` and `PERSONAS["andres"]`, files a fee-waiver application only for a persona with `fee_waiver` data, and makes the docstring and help say 6 personas.

- [ ] **Step 4: Write his brief**

```markdown file=docs/testing/persona-briefs/andres-kettleby.md
# Andrés Kettleby — Persona Brief for AI Testing Agent

You ARE Andrés Kettleby. Navigate DigniFi as he would.

## Who You Are

- 38 years old, never married, single father of a daughter, age 9, who lives with you full time.
- Her mother lives in Indiana. She pays no support, and keeps your daughter on her employer's health plan.
- You drive for rideshare and delivery apps about 50 hours a week. You are self-employed, with no boss and no paycheck.
- Over the last six months the apps paid you about $4,200 a month. Driving costs you about $830 a month, so you keep about $3,370.
- You rent a 2-bedroom apartment in Aurora for $1,150 a month.
- You lease a 2024 Toyota Corolla Hybrid ($389 a month), the car you drive for work.
- Your name is on your brother Mateo's 2017 Honda Fit and its loan. He drives it and pays it.

## Your Emotional State

- Scared about the Corolla. With no car you have no income.
- Guilty about Mateo. You co-signed so he could get to his job, and you don't want this to land on him.
- Angry about your old landlord's $1,850 damage bill. You left the place clean and you have the photos.
- You work hard. Being called "unemployed", or "a business", stings.

## Your Tech Comfort

- You live on your phone (the driver apps, your banking app) and fill DigniFi in on it in short bursts between rides.
- You expect your work to save if a ride request interrupts you.
- You copy creditor names and amounts from photos of your mail, and typing ten of them tests your patience.

## How You Read

- You finished high school and read English well. You speak Spanish with your mother.
- You know "earnings", "tips" and "payout". "Gross receipts", "ordinary and necessary", "executory contract" and "unliquidated" are new to you.
- You read anything about the Corolla or Mateo twice, and you skim the rest.

## Your Data (enter this exactly)

| Field                                                                   | Value                                      |
| ----------------------------------------------------------------------- | ------------------------------------------ |
| First name                                                              | Andrés                                     |
| Middle name                                                             | J                                          |
| Last name                                                               | Kettleby                                   |
| SSN                                                                     | 900-66-0006                                |
| Date of birth                                                           | 04/12/1988                                 |
| Phone                                                                   | 630-555-0161                               |
| Email                                                                   | andres.kettleby@demo.dignifi.org           |
| Address                                                                 | 1418 Marquette Ave Apt 2, Aurora, IL 60505 |
| Household Size                                                          | 2                                          |
| Filing Type                                                             | Individual (filing alone)                  |
| What you keep from driving each month (Other Monthly Income box)        | $3,370                                     |
| Every other income box                                                  | $0                                         |
| Rent                                                                    | $1,150                                     |
| Utilities: electric, gas, internet, your share of the phone             | $210                                       |
| Vehicle payment (Car Payment box): the Corolla lease                    | $389                                       |
| Vehicle insurance: your personal policy                                 | $165                                       |
| Vehicle maintenance (Gas & Transportation box): school runs and errands | $60                                        |
| Food                                                                    | $520                                       |
| Clothing                                                                | $60                                        |
| Medical                                                                 | $45                                        |
| Childcare: after-school program                                         | $180                                       |
| Every other expense box                                                 | $0                                         |

**Assets:**

- 2017 Honda Fit — titled to you and Mateo, value $4,300 (your half of $8,600), owed $7,800
- Household goods, electronics and clothing — $1,900
- Harborline Bank checking — $412
- Prairie Line Credit Union share savings — $85

**Amounts Owed.** You pay $0 a month on every one of these.

- Copperline Auto Finance car loan — $7,800, paying $0 (Mateo's Fit loan you co-signed; what secures it: "2017 Honda Fit, co-owned with my brother")
- Bright Signal Wireless utility bill — $640, paying $0 (final phone bill and early termination)
- Calumet Ridge Medical Center medical bill — $3,850, paying $0 (your daughter's ER visit, in collections)
- Driveline Tire & Auto credit card — $1,180, paying $0 (store card: tires and brakes)
- Illinois State Toll Highway Authority other amount owed — $380, paying $0 (unpaid tolls and violation fines)
- Meridian Lending Co. personal loan — $4,100, paying $0 (online loan for rent)
- Northgate Card Services credit card — $6,420, paying $0
- Prairie Line Credit Union credit card — $1,760, paying $0
- Ridgeway Apartments LLC other amount owed — $1,850, paying $0 (old landlord's move-out damage claim)
- Sablewood Bank credit card — $2,980, paying $0

**Contracts and codebtors:** leave both steps empty, and go on.

**The fee:** you mean to pay the filing fee in installments. If DigniFi sends you to the fee waiver page, you don't apply for the waiver, and you go on to your forms. If the page gives you no way on without applying, note it, then open your forms page (`/forms`) directly.

**Why these are your answers:**

- **Other Monthly Income, not wages:** you have no boss and no paycheck. What you keep after driving costs, $3,370, is your income.
- **Installments:** $338 at once is more than your best week leaves over; weekly payouts fit four payments.
- **The lease is your car payment:** "It's my only car; I'd have it even if I didn't drive for the apps."
- **Copperline $0 a month:** the box asks for your monthly payment, and Mateo pays it, not you.

## What to Watch For

- Can you report what you keep from driving without the app calling it wages?
- Does anything say what will happen to your lease, or push you on it?
- Can you enter ten amounts owed on your phone without losing work?
- Does the fee waiver page let you go on without applying?
```

The brief is the personas doc's target brief cut to what today's wizard asks, with the same data as the seed.

- [ ] **Step 5: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=line -rN --disable-warnings apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_api_readback.py -k andres -q -p no:cacheprovider 2>&1 | tail -5
```

Expected: `31 passed, 154 deselected`.

The 31 are his 30 tier 3 cases and his readback case.

- [ ] **Step 6: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2166 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  389 passed (389)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

The 25 skips are the Postgres-only tests under sqlite. The gates ran on the commit before the review's fix round, which changed three lines of the brief, and prettier passed on the amended commit. The next command runs the Postgres-only tests against the Postgres database named in `.claude/forms-step3a1.env`.

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

The journeys don't run here, because Task 11 adds his journey and runs them all.

- [ ] **Step 7: Commit**

```bash
set -eo pipefail
git add \
  docs/testing/persona-briefs/andres-kettleby.md \
  backend/apps/forms/tests/test_api_readback.py \
  backend/apps/forms/tests/test_oracle_tier3.py \
  backend/apps/intake/management/commands/seed_demo_data.py
git commit -F - <<'MSG'
feat(personas): Andrés Kettleby, a gig driver, joins the demo seed

The seed gains a sixth persona, demo_andres, with only the data
today's wizard asks (3a1 spec §8): his identity, a household of 2, his
net driving income of $3,370 a month as other income with every other
source at $0 (3a1.Q1), the 13 expenses ($2,779), four assets, the
co-signed Honda Fit loan and nine unsecured debts. He qualifies under
today's fee-waiver flag but means to pay in installments, so the seed
creates a fee-waiver application only for a persona with fee-waiver
answers (3a1.Q2). That also ends the KeyError the seed raised for a
qualifying persona without them.

The API readback splits WAIVER_FILERS into QUALIFIES (Maria, DeShawn,
Sarah, Andrés) and APPLIES (Maria, DeShawn, Sarah) until step 3f.
Tier 3 gains his hand-worked figures for 122A-1 lines 10 to 14 and the
page-1 result, Schedule I lines 8h, 10 and 12, Schedule J lines 17a and
22 to 23, and 106Sum lines 1 to 5. His brief is the target brief cut to
what the wizard asks today. The seed's docstring and help say 6
personas.
MSG
git status --short
```

### Task 11: Add Andrés's journey, and type each persona's income into its own box

_Built and verified as commit `6f5f71d` on `plan/forms-step3a1`._

**Files:**

- Create: `frontend/e2e/journeys/andres-gig-driver.spec.ts`
- Modify: `CLAUDE.md`
- Modify: `CONTRIBUTING.md`
- Modify: `README.md`
- Modify: `docs/testing/persona-briefs/README.md`
- Modify: `docs/testing/run-persona-tests.md`
- Modify: `docs/testing/test_persona_full_flow.py`
- Modify: `frontend/e2e/fixtures/personas.ts`
- Modify: `frontend/e2e/pages/sofa.page.ts`
- Modify: `frontend/e2e/pages/wizard.page.ts`

**Interfaces:**

- Consumes:
  - `PersonaIncome` in `frontend/e2e/fixtures/personas.ts`, which before this task is `{ marital_status, number_of_dependents, total_monthly_income }`, and `WizardPage.fillIncomeInfo(income)` in `frontend/e2e/pages/wizard.page.ts`, which typed `total_monthly_income` into `input[name="monthly_gross_wages"]`. The page object reads neither `marital_status` nor `number_of_dependents`.
  - The Income step's ten boxes, each an input named as the backend stores the amount: `INCOME_FIELDS` in `frontend/src/types/api.ts`, `monthly_gross_wages` through `monthly_other_income`. No box is required: the step checks each amount on its own.
  - In `personas.ts`: `RUN_ID`, `PersonaData`, and the fixtures `MARIA`, `JAMES`, `PRIYA`, `DESHAWN` and `SARAH`, whose incomes are 3200, 5833, 12000, 3500 and 2000.
  - Task 10's brief, `docs/testing/persona-briefs/andres-kettleby.md` (its table "Your Data (enter this exactly)", its **Assets** list and its **Amounts Owed** list), and the seed's `_andres_kettleby()`, which the fixture matches field for field except the SSN. Task 9's fictional creditor names.
  - The page objects the journey drives: `LandingPage.goto()` and `clickGetStarted()`; `RegisterPage.register(username, email, password)`; `WizardPage.fillDebtorInfo`, `nextStep`, `fillIncomeInfo`, `fillExpenses`, `addAsset`, `addDebt`, `fillReview` and `completeIntake`, which waits for any of `/forms`, `/fee-waiver` or `/sofa`; `DocumentsPage.skip()`; `SOFAPage.waitForLoad()` and `skipForNow()`, which waits for `/forms`; `DashboardPage.generateAllForms(expectedCount)`, which waits for "N of N", and `getGeneratedCount()`.
  - Complete's routing in `frontend/src/pages/IntakeWizard.tsx`: `navigate('/fee-waiver')` when `calculateMeansTest()` returns `qualifies_for_fee_waiver`, else `navigate('/sofa')`. `FeeWaiverPage`'s `<h1>` reads "Filing Fee Waiver Application", and the page shows its go-on button only to a filer who doesn't qualify.
  - `.claude/e2e.sh`, which reseeds this worktree's database, starts both servers and runs every spec in `frontend/e2e/journeys/`, printing one `RUN <n> exit=<code>: <summary>` line per run.
- Produces:
  - `export type IncomeSourceKey` in `personas.ts`: the union of the ten box names.
  - `PersonaIncome.sources: Partial<Record<IncomeSourceKey, number>>` in place of `total_monthly_income`. `marital_status` and `number_of_dependents` stay.
  - `fillIncomeInfo` types each `sources` entry into `input[name="<source>"]`. A source left out stays blank.
  - The five personas' `sources: { monthly_gross_wages: N }`, N being their old totals.
  - `export const ANDRES: PersonaData`: username `e2e_andres_${RUN_ID}`, SSN 900-66-6006, email `andres.e2e+${RUN_ID}@test.dignifi.org`, all ten sources (`monthly_other_income` 3370, the other nine 0), the 13 expenses (2,779), four assets, ten debts, `expected: { passes_means_test: true, fee_waiver_eligible: true }` and no `fee_waiver` answers.
  - `frontend/e2e/journeys/andres-gig-driver.spec.ts`: describe "Andrés Kettleby — Gig Driver", test "reaches his forms from the fee waiver page without applying".
  - `SOFAPage.waitForLoad(timeout?: number)` in `frontend/e2e/pages/sofa.page.ts`; called with no argument it waits as before.
  - The counts, from five personas to six and from seven journeys to eight, in `README.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `docs/testing/persona-briefs/README.md` (with his row), `docs/testing/run-persona-tests.md` (with his name in the quick-start list) and `docs/testing/test_persona_full_flow.py` (which lists `demo_andres`).

**Decisions already made in this task:**

- **3a1.Q1 (spec §2):** until 3e2, the $3,370 a month he keeps from driving goes in the other-income box, in the seed and in this journey, and the other five personas keep wages.
- **3a1.Q2 (spec §2):** until 3f he files no fee-waiver application, so today's 60%-of-median flag sends him to `/fee-waiver` and his journey goes on to his forms without applying.
- **His journey goes `/fee-waiver` → `page.goto('/sofa')` → skip → `/forms`, and expects 14 forms** (spec §8, steps 4 to 6).
  - The fee-waiver page offers no way on without applying, since it shows its go-on button only to a filer who doesn't qualify. So he opens `/sofa` by URL.
  - `/sofa` sits under `ProtectedRoute`, which shows only its loading state until the silent refresh on mount (`AuthContext.tsx`) restores his login. The `IntakeProvider` below it therefore reads `current_session_id` only once he is logged in again.
  - The check that the fee-waiver page opened is its URL and its `<h1>`. `completeIntake()` already waits for `/forms`, `/fee-waiver` or `/sofa`, so it proves nothing about which one opened.
  - The 14 forms are 101, 106Dec, 106Sum, 107, 121, 122A-1, A/B, C, D, E/F, G, H, I and J: no 103B, because he files no application, and no 122A-2, because he is below the median.
  - His brief tells a human tester to open `/forms` directly; the journey goes through `/sofa`, as spec §8 says. Both reach the same forms.
- **His journey SSN, 900-66-6006, differs from the seed's 900-66-0006.** Every fixture's SSN repeats one digit (900-11-1001 … 900-55-5005) and every seed's ends in 000N (900-11-0001 … 900-55-0005), so his follows the other five. Both are in the IRS-reserved 900 range, and his phone, 630-555-0161, is in the 555-0100–0199 fiction block (G2).
- **The five personas carry their old totals as `monthly_gross_wages`:** Maria 3200, James 5833, Priya 12000, DeShawn 3500 and Sarah 2000. `fillIncomeInfo` typed that total into the wages box before, so each journey types exactly what it typed before and no outcome changes.
- **`IncomeSourceKey` is a local union in `personas.ts`, not an import from `src/types/api.ts`.** No e2e file imports from `src` today, so the fixture doesn't start that pattern; its doc comment names `INCOME_FIELDS` as its source. `PersonaIncome` keeps `marital_status` and `number_of_dependents`, because the Interfaces table replaces only `total_monthly_income`.
- **He types all ten sources:** nine 0s and 3370 in `monthly_other_income`. His brief says every other income box is $0, and the seed stores a typed $0 for each. A typed $0 prints 0.00 and a blank box prints blank, so typing only the one amount would leave his journey's session different from the seed's.
- **The journey has no means-test preview check,** because spec §8's six steps list none. Every other persona journey checks the preview, so his differs from them there.
- **No journey asserts which box his income lands in.** If `fillIncomeInfo` typed every amount into the wages box, his last amount, 3370, would win there and the other-income box would stay blank. His CMI, his fee routing and his 14 forms would not change, so the journeys would stay green. Task 10's tier 3 proves the seed side, where 3370 typed as wages failed 4 cases. Spec §8 asks for no such assertion, and one would cost another journey run.
- **The counts were fixed beyond tasks.md's list,** each found by grep in a current doc:
  - tasks.md's `CLAUDE.md:12,90,100,129` are lines 12, 92, 102 and 131 today, and line 92's list of brief names now includes andres;
  - `CONTRIBUTING.md:179`;
  - `docs/testing/persona-briefs/README.md:109`, "Celebrate if";
  - `docs/testing/run-persona-tests.md` lines 25, 111, 115, 118, 169 and 186, and his name in the quick-start list at line 179;
  - `{"username": "demo_andres", "name": "Andrés Kettleby"}` in `test_persona_full_flow.py`'s `PERSONAS`, because a docstring that says 6 over a list of 5 would be false.
  - The dated `docs/reports/2026-02-28-usability-test.md` stays as written: it is a record, as spec §8 says of dated specs and plans. `seed_demo_data.py` already says 6, from Task 10.
- **The red proof is a mutation:** with qualifying filers routed to `/sofa`, his journey fails at the `/fee-waiver` check. Step 2 quotes the run.
- **His SOFA wait is 30 s, not the default 5 s.** He is the only persona who reaches `/sofa` by a full reload, so the heading shows only after the token refresh, the session read and the SOFA read. Twice, with the machine's load average above 20, his second run missed the heading within 5 s. `SOFAPage.waitForLoad` takes an optional timeout, and only his journey passes one; every other caller keeps the default.

- [ ] **Step 1: Write the journey**

```ts file=frontend/e2e/journeys/andres-gig-driver.spec.ts
/**
 * Andrés Kettleby — Gig Driver
 *
 * Self-employed rideshare and delivery driver, below median, ten amounts owed.
 * What he keeps from driving goes in the other-income box until the Income step
 * asks for business income (3a1.Q1). Today's flag qualifies him for a fee waiver,
 * so Complete opens the waiver page, but he pays in installments and files no
 * application (3a1.Q2): his packet has no Form 103B.
 */

import { test, expect } from '@playwright/test';
import { ANDRES } from '../fixtures/personas';
import { LandingPage } from '../pages/landing.page';
import { RegisterPage } from '../pages/register.page';
import { WizardPage } from '../pages/wizard.page';
import { DocumentsPage } from '../pages/documents.page';
import { DashboardPage } from '../pages/dashboard.page';
import { SOFAPage } from '../pages/sofa.page';

test.describe('Andrés Kettleby — Gig Driver', () => {
  test('reaches his forms from the fee waiver page without applying', async ({ page }) => {
    const landing = new LandingPage(page);
    const register = new RegisterPage(page);
    const wizard = new WizardPage(page);
    const documents = new DocumentsPage(page);
    const sofa = new SOFAPage(page);
    const dashboard = new DashboardPage(page);

    await landing.goto();
    await landing.clickGetStarted();
    await register.register(ANDRES.username, ANDRES.debtor.email, ANDRES.password);

    // Step 1: Debtor Info
    await wizard.fillDebtorInfo(ANDRES.debtor);
    await wizard.nextStep();

    // Uploads come between basic info and Income; this journey types everything in
    await documents.skip();

    // Step 2: Income ($3,370/mo in Other Monthly Income, $0 in every other box)
    await wizard.fillIncomeInfo(ANDRES.income);
    await wizard.nextStep();

    // Step 3: Expenses
    await wizard.fillExpenses(ANDRES.expenses);
    await wizard.nextStep();

    // Step 4: Assets (his half of the Honda Fit, household goods, two accounts)
    for (const asset of ANDRES.assets) {
      await wizard.addAsset(asset);
    }
    await wizard.nextStep();

    // Step 5: Debts (the co-signed Honda Fit loan and nine unsecured debts)
    for (const debt of ANDRES.debts) {
      await wizard.addDebt(debt);
    }
    await wizard.nextStep();

    // Step 6: Contracts & Leases (left empty)
    await wizard.nextStep();

    // Step 7: Codebtors (left empty)
    await wizard.nextStep();

    // Step 8: Review & Complete
    await wizard.fillReview();
    await wizard.completeIntake();

    // He qualifies under today's flag, so Complete opens the waiver application
    await expect(page).toHaveURL(/\/fee-waiver$/);
    await expect(page.locator('h1')).toHaveText('Filing Fee Waiver Application');

    // He doesn't apply. The page has no way on without applying, so he opens the SOFA
    // step by URL (the silent refresh on load restores his login) and skips it.
    await page.goto('/sofa');
    // A full reload shows the heading only after the token refresh, the session read and the
    // SOFA read, so it gets longer than the default 5 s (two loaded runs missed it)
    await sofa.waitForLoad(30_000);
    await sofa.skipForNow();

    // No waiver application, so no Form 103B; below median, so no Form 122A-2
    await dashboard.generateAllForms(14);
    const count = await dashboard.getGeneratedCount();
    expect(count).toBe(14);
  });
});
```

```bash
git apply <<'PATCH'
diff --git a/frontend/e2e/pages/sofa.page.ts b/frontend/e2e/pages/sofa.page.ts
index 71d62bd..a0db426 100644
--- a/frontend/e2e/pages/sofa.page.ts
+++ b/frontend/e2e/pages/sofa.page.ts
@@ -23,9 +23,12 @@ export class SOFAPage {

   /**
    * Wait for the SOFA page to be fully loaded.
+   * @param timeout ms to wait for the heading, when the page loads from a full reload
    */
-  async waitForLoad() {
-    await expect(this.page.locator('h1')).toContainText('Statement of Financial Affairs');
+  async waitForLoad(timeout?: number) {
+    await expect(this.page.locator('h1')).toContainText('Statement of Financial Affairs', {
+      timeout,
+    });
   }

   /**
PATCH
```

The journey follows spec §8's six steps with his fixture, `ANDRES`, which the next steps add. It leaves Contracts and Codebtors empty, checks that Complete opens the fee-waiver page, opens `/sofa` by URL, skips it, and generates his 14 forms. `SOFAPage.waitForLoad` gains an optional timeout, which his journey sets to 30 s after the full reload.

- [ ] **Step 2: Type-check the e2e code and watch it fail**

```bash
set -eo pipefail
cd frontend && npx tsc --noEmit --strict --target es2022 --module esnext --moduleResolution bundler \
  --types node --skipLibCheck --noUnusedLocals --noUnusedParameters --allowImportingTsExtensions \
  e2e/*.ts e2e/*/*.ts
```

Expected: FAIL — `error TS2305` on the journey's import: `has no exported member 'ANDRES'`.

That import is the only error: the fixture has no `ANDRES` yet. No gate type-checks `frontend/e2e/`, since `tsconfig.app.json` covers only `src` and `tsconfig.node.json` only `vite.config.ts`, so this strict check stands in for one. It covers the new journey and the 18 e2e files the parent commit holds, which are clean on their own. `--noEmit` leaves no build output. The check also catches the old field: the implementer's probe outside the repo gave TS2339 for `ANDRES.income.total_monthly_income` and TS2353 for an unknown source key, `monthly_wages`.

The journey's own red needs the full stack, so it is stated here and not run. To prove that its fee-waiver check can fail, the implementer changed `navigate('/fee-waiver')` at `frontend/src/pages/IntakeWizard.tsx:360` to `navigate('/sofa')`, so that Complete sent every qualifying filer to `/sofa`, and ran the journeys once with this task's change in place. `e2e.sh` printed:

```text
RUN 1 exit=1: 4 failed  4 passed (2.9m)
  1) [chromium] › e2e/journeys/andres-gig-driver.spec.ts:21:3 › Andrés Kettleby — Gig Driver › reaches his forms from the fee waiver page without applying
  2) [chromium] › e2e/journeys/maria-happy-path.spec.ts:19:3 › Maria Torres — Happy Path › completes full intake and generates all forms
  3) [chromium] › e2e/journeys/deshawn-assets.spec.ts:19:3 › DeShawn Mitchell — Assets › enters 3 assets and 4 debts successfully
  4) [chromium] › e2e/journeys/sarah-simplest.spec.ts:19:3 › Sarah Chen — Simplest Case › completes intake with no assets (fastest path)
```

The run's log, `.claude/e2e-logs/run1.txt`, gives his failure:

```text
    Error: expect(page).toHaveURL(expected) failed

    Expected pattern: /\/fee-waiver$/
    Received string:  "http://localhost:5173/sofa"
    Timeout: 5000ms

    Call log:
      - Expect "toHaveURL" with timeout 5000ms
        9 × unexpected value "http://localhost:5173/sofa"


      69 |
      70 |     // He qualifies under today's flag, so Complete opens the waiver application
    > 71 |     await expect(page).toHaveURL(/\/fee-waiver$/);
```

His journey failed at its fee-waiver check. Maria's, DeShawn's and Sarah's failed too, because each also qualifies under today's flag and expects the fee-waiver page. The implementer then restored the line. This red run came before the 30 s SOFA wait was added, which doesn't touch the fee-waiver check.

- [ ] **Step 3: Give each persona's income by source, and add Andrés's data**

```bash
git apply <<'PATCH'
diff --git a/frontend/e2e/fixtures/personas.ts b/frontend/e2e/fixtures/personas.ts
index 05530c9..6a4cafd 100644
--- a/frontend/e2e/fixtures/personas.ts
+++ b/frontend/e2e/fixtures/personas.ts
@@ -27,10 +27,24 @@ export interface PersonaDebtor {
   filing_type: 'individual' | 'joint';
 }

+/** The Income step's ten boxes, named as the backend stores them (INCOME_FIELDS in types/api.ts) */
+export type IncomeSourceKey =
+  | 'monthly_gross_wages'
+  | 'monthly_overtime'
+  | 'monthly_tips'
+  | 'monthly_rental_income'
+  | 'monthly_pension'
+  | 'monthly_social_security'
+  | 'monthly_unemployment'
+  | 'monthly_child_support'
+  | 'monthly_alimony'
+  | 'monthly_other_income';
+
 export interface PersonaIncome {
   marital_status: string;
   number_of_dependents: number;
-  total_monthly_income: number;
+  // Each amount the persona types, in its own box. A source left out stays blank.
+  sources: Partial<Record<IncomeSourceKey, number>>;
 }

 export interface PersonaAsset {
@@ -98,7 +112,7 @@ export const MARIA: WaiverPersonaData = {
   income: {
     marital_status: 'single',
     number_of_dependents: 2,
-    total_monthly_income: 3200,
+    sources: { monthly_gross_wages: 3200 },
   },
   expenses: {
     rent_or_mortgage: 1100,
@@ -173,7 +187,7 @@ export const JAMES: PersonaData = {
   income: {
     marital_status: 'single',
     number_of_dependents: 0,
-    total_monthly_income: 5833,
+    sources: { monthly_gross_wages: 5833 },
   },
   expenses: {
     rent_or_mortgage: 1650,
@@ -248,7 +262,7 @@ export const PRIYA: PersonaData = {
     number_of_dependents: 2,
     // $12,000/month = $144,000/year — above the $137,902 HH4 median, so the
     // annualized § 707(b) comparison fails as the persona intends.
-    total_monthly_income: 12000,
+    sources: { monthly_gross_wages: 12000 },
   },
   expenses: {
     rent_or_mortgage: 2800,
@@ -314,7 +328,7 @@ export const DESHAWN: WaiverPersonaData = {
   income: {
     marital_status: 'married_joint',
     number_of_dependents: 0,
-    total_monthly_income: 3500,
+    sources: { monthly_gross_wages: 3500 },
   },
   expenses: {
     rent_or_mortgage: 1200,
@@ -405,7 +419,7 @@ export const SARAH: WaiverPersonaData = {
   income: {
     marital_status: 'single',
     number_of_dependents: 0,
-    total_monthly_income: 2000,
+    sources: { monthly_gross_wages: 2000 },
   },
   expenses: {
     rent_or_mortgage: 850,
@@ -442,3 +456,165 @@ export const SARAH: WaiverPersonaData = {
   fee_waiver: { take_home_pay: 1750, noncash_assistance: null },
   expected: { passes_means_test: true, fee_waiver_eligible: true },
 };
+
+// Data from docs/testing/persona-briefs/andres-kettleby.md, with an SSN of the journey's own:
+// the seed's demo_andres has 900-66-0006.
+export const ANDRES: PersonaData = {
+  username: `e2e_andres_${RUN_ID}`,
+  password: 'TestPass-2026!',
+  debtor: {
+    first_name: 'Andrés',
+    last_name: 'Kettleby',
+    middle_name: 'J',
+    ssn: '900-66-6006',
+    date_of_birth: '1988-04-12',
+    phone: '630-555-0161',
+    email: `andres.e2e+${RUN_ID}@test.dignifi.org`,
+    household_size: 2,
+    filing_type: 'individual',
+    street_address: '1418 Marquette Ave Apt 2',
+    city: 'Aurora',
+    state: 'IL',
+    zip_code: '60505',
+  },
+  income: {
+    marital_status: 'single',
+    number_of_dependents: 1,
+    // What he keeps from driving ($4,200 from the apps less $830 of driving costs) is other
+    // income until the Income step asks for business income (3a1.Q1). Every other box is $0.
+    sources: {
+      monthly_gross_wages: 0,
+      monthly_overtime: 0,
+      monthly_tips: 0,
+      monthly_rental_income: 0,
+      monthly_pension: 0,
+      monthly_social_security: 0,
+      monthly_unemployment: 0,
+      monthly_child_support: 0,
+      monthly_alimony: 0,
+      monthly_other_income: 3370,
+    },
+  },
+  expenses: {
+    rent_or_mortgage: 1150,
+    utilities: 210,
+    home_maintenance: 0,
+    // The Corolla lease, his only car
+    vehicle_payment: 389,
+    vehicle_insurance: 165,
+    vehicle_maintenance: 60,
+    food_and_groceries: 520,
+    clothing: 60,
+    medical_expenses: 45,
+    childcare: 180,
+    child_support_paid: 0,
+    insurance_not_deducted: 0,
+    other_expenses: 0,
+  },
+  assets: [
+    // His half of a car titled to him and his brother
+    {
+      asset_type: 'vehicle',
+      description: '2017 Honda Fit',
+      current_value: 4300,
+      amount_owed: 7800,
+    },
+    {
+      asset_type: 'personal_property',
+      description: 'Household goods, electronics and clothing',
+      current_value: 1900,
+      amount_owed: 0,
+    },
+    {
+      asset_type: 'bank_account',
+      description: 'Harborline Bank checking',
+      current_value: 412,
+      amount_owed: 0,
+      financial_institution: 'Harborline Bank',
+    },
+    {
+      asset_type: 'bank_account',
+      description: 'Prairie Line Credit Union share savings',
+      current_value: 85,
+      amount_owed: 0,
+      financial_institution: 'Prairie Line Credit Union',
+    },
+  ],
+  debts: [
+    {
+      creditor_name: 'Copperline Auto Finance',
+      debt_type: 'auto_loan',
+      amount_owed: 7800,
+      // His brother drives the car and pays the loan he co-signed
+      monthly_payment: 0,
+      is_in_collections: false,
+      collateral_description: '2017 Honda Fit, co-owned with my brother',
+    },
+    {
+      creditor_name: 'Bright Signal Wireless',
+      debt_type: 'utility',
+      amount_owed: 640,
+      monthly_payment: 0,
+      is_in_collections: false,
+    },
+    {
+      creditor_name: 'Calumet Ridge Medical Center',
+      debt_type: 'medical',
+      amount_owed: 3850,
+      monthly_payment: 0,
+      is_in_collections: true,
+    },
+    {
+      creditor_name: 'Driveline Tire & Auto',
+      debt_type: 'credit_card',
+      amount_owed: 1180,
+      monthly_payment: 0,
+      is_in_collections: false,
+    },
+    {
+      creditor_name: 'Illinois State Toll Highway Authority',
+      debt_type: 'other',
+      amount_owed: 380,
+      monthly_payment: 0,
+      is_in_collections: false,
+    },
+    {
+      creditor_name: 'Meridian Lending Co.',
+      debt_type: 'personal_loan',
+      amount_owed: 4100,
+      monthly_payment: 0,
+      is_in_collections: false,
+    },
+    {
+      creditor_name: 'Northgate Card Services',
+      debt_type: 'credit_card',
+      amount_owed: 6420,
+      monthly_payment: 0,
+      is_in_collections: false,
+    },
+    {
+      creditor_name: 'Prairie Line Credit Union',
+      debt_type: 'credit_card',
+      amount_owed: 1760,
+      monthly_payment: 0,
+      is_in_collections: false,
+    },
+    {
+      creditor_name: 'Ridgeway Apartments LLC',
+      debt_type: 'other',
+      amount_owed: 1850,
+      monthly_payment: 0,
+      is_in_collections: false,
+    },
+    {
+      creditor_name: 'Sablewood Bank',
+      debt_type: 'credit_card',
+      amount_owed: 2980,
+      monthly_payment: 0,
+      is_in_collections: false,
+    },
+  ],
+  // Today's flag (income under 60% of the median) qualifies him for a fee waiver, but he pays
+  // in installments and files no application (3a1.Q2), so he has no fee_waiver answers.
+  expected: { passes_means_test: true, fee_waiver_eligible: true },
+};
diff --git a/frontend/e2e/pages/wizard.page.ts b/frontend/e2e/pages/wizard.page.ts
index a0559f8..e492329 100644
--- a/frontend/e2e/pages/wizard.page.ts
+++ b/frontend/e2e/pages/wizard.page.ts
@@ -115,12 +115,12 @@ export class WizardPage {
   // ── Step 2: Income Info ─────────────────────────────────────────

   async fillIncomeInfo(income: PersonaIncome) {
-    // The income step itemizes sources and requires a total > 0; enter the
-    // persona's total as gross wages. Marital status / dependents are no
-    // longer collected on this step.
-    await this.page
-      .locator('input[name="monthly_gross_wages"]')
-      .fill(String(income.total_monthly_income));
+    // The income step has a box for each source, named as the backend stores it, so each
+    // amount goes into its own box and a source the persona leaves out stays blank.
+    // Marital status / dependents are no longer collected on this step.
+    for (const [source, amount] of Object.entries(income.sources)) {
+      await this.page.locator(`input[name="${source}"]`).fill(String(amount));
+    }
   }

   // ── Step 3: Expenses ────────────────────────────────────────────
PATCH
```

`PersonaIncome` carries a partial map of the ten boxes in place of one total, and `fillIncomeInfo` types each amount into the input of the same name, so a source a persona leaves out stays blank (spec §8, 3a1.Q1). The five personas keep their wages, and `ANDRES` holds his brief's data under the journey's own login and SSN.

- [ ] **Step 4: Type-check the e2e code again**

```bash
set -eo pipefail
cd frontend && npx tsc --noEmit --strict --target es2022 --module esnext --moduleResolution bundler \
  --types node --skipLibCheck --noUnusedLocals --noUnusedParameters --allowImportingTsExtensions \
  e2e/*.ts e2e/*/*.ts
echo "no type errors in the e2e code"
```

Expected: `no type errors in the e2e code`.

- [ ] **Step 5: Move the counts to six personas and eight journeys**

````bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index ec68ddf..c4a9af1 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -9,7 +9,7 @@ docker compose up                              # Start all 3 services (db, backe
 docker compose exec backend python -m pytest --ds=config.settings.test    # Backend tests (sqlite :memory:, no postgres needed)
 docker compose exec backend python manage.py migrate
 docker compose exec backend python manage.py loaddata ilnd_2025_data   # Required before seed
-docker compose exec backend python manage.py seed_demo_data            # Loads 5 AI personas
+docker compose exec backend python manage.py seed_demo_data            # Loads 6 AI personas

 cd frontend && npm test                        # Frontend tests (vitest)
 cd frontend && npm run e2e                     # E2E (requires backend running + seeded)
@@ -89,7 +89,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Forms:** 17 form types in `apps/forms/registry.py` (`FORM_REGISTRY` / `get_all_form_types()` / `packet(session)`). `generate_all` gives each form its own savepoint.
 - **OCR service:** provider-agnostic. `OCR_PROVIDER` selects `openai` (default, `gpt-4o`, `OPENAI_API_KEY`) or `gemini` (`gemini-2.0-flash`, `GEMINI_API_KEY`); `OCR_MODEL` overrides the model so a model change is a config var, not a deploy. No local model — both call a hosted API directly.
 - **Auth:** JWT (simplejwt). Access in memory, refresh in localStorage. `POST /api/token/obtain/` + `/api/token/refresh/`.
-- **E2E:** 5 AI persona briefs in `docs/testing/persona-briefs/` (deshawn, james, maria, priya, sarah) driving 7 journey specs — one per persona plus `sofa-journey.spec.ts` and `scanned-bill-journey.spec.ts` (an upload read through a fake OpenAI server). `seed_demo_data` creates synthetic sessions with all intake data.
+- **E2E:** 6 AI persona briefs in `docs/testing/persona-briefs/` (andres, deshawn, james, maria, priya, sarah) driving 8 journey specs — one per persona plus `sofa-journey.spec.ts` and `scanned-bill-journey.spec.ts` (an upload read through a fake OpenAI server). `seed_demo_data` creates synthetic sessions with all intake data.

 ## File Map (what lives where)

@@ -99,7 +99,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - `apps/intake/fields.py` — Custom `EncryptedDecimalField`
 - `apps/intake/views.py` — IntakeSessionViewSet, AssetViewSet, DebtViewSet
 - `apps/intake/serializers.py` — nested serializers; DRF silently drops unknown fields (mismatch with frontend)
-- `apps/intake/management/commands/seed_demo_data.py` — 5 AI personas
+- `apps/intake/management/commands/seed_demo_data.py` — 6 AI personas
 - `apps/eligibility/services/means_test_calculator.py` — `MeansTestCalculator`, which runs and saves `MeansTest.calculate()` (`apps/eligibility/models.py`, where CMI is annualized)
 - `apps/eligibility/cmi.py` — `current_monthly_income` (the one CMI), `IncomeNotSplit`, `is_above_median`
 - `apps/forms/registry.py` — `FORM_REGISTRY` (17 form_type → `PacketForm(applies, requires)`) in filing order, `packet()`, `build_field_values()`
@@ -128,7 +128,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - `src/components/compliance/UPLConfirmationModal.tsx` — gates form generation
 - `src/types/api.ts` — TypeScript interfaces matching DRF serializers
 - `src/test/setup.ts` — vitest globals, MSW, vitest-axe matchers
-- `e2e/journeys/` — 7 Playwright journey specs (5 personas + SOFA + scanned bill)
+- `e2e/journeys/` — 8 Playwright journey specs (6 personas + SOFA + scanned bill)
 - `e2e/fixtures/fake-openai.ts` — fake OpenAI Chat Completions server (`startFakeOpenAI`, `CANNED_BILL`) for `scanned-bill-journey`
 - `e2e/playwright.config.ts` — Chromium only, 120s timeout, `reuseExistingServer`

diff --git a/CONTRIBUTING.md b/CONTRIBUTING.md
index 208dad6..cc70802 100644
--- a/CONTRIBUTING.md
+++ b/CONTRIBUTING.md
@@ -176,7 +176,7 @@ Co-Authored-By: Jane Doe <jane@example.com>
 4. **E2E Tests** (Playwright)
    - Full user journeys, persona-based scenarios
    - `python3 docs/testing/test_maria_quick.py` (quick smoke test)
-   - `cd frontend && npm run e2e` (7 journey specs; needs the backend running and seeded)
+   - `cd frontend && npm run e2e` (8 journey specs; needs the backend running and seeded)

 ### Running Tests Locally

diff --git a/README.md b/README.md
index 08d0578..89538c0 100644
--- a/README.md
+++ b/README.md
@@ -24,7 +24,7 @@
 | ------------------------- | ---------------- | --------------- |
 | Backend (pytest)          | 2,096 (+1 xfail) | Passing         |
 | Frontend (vitest)         | 358              | Passing         |
-| E2E journeys (Playwright) | 7/7 journeys     | All steps green |
+| E2E journeys (Playwright) | 8/8 journeys     | All steps green |

 ## Quick Start

@@ -215,7 +215,7 @@ docker compose exec backend pytest -q
 # Frontend (358 tests)
 cd frontend && npx vitest run

-# Full E2E (7 Playwright journeys; backend running and seeded)
+# Full E2E (8 Playwright journeys; backend running and seeded)
 cd frontend && npm run e2e

 # Quick smoke test (Maria only)
diff --git a/docs/testing/persona-briefs/README.md b/docs/testing/persona-briefs/README.md
index 12afb5d..299507b 100644
--- a/docs/testing/persona-briefs/README.md
+++ b/docs/testing/persona-briefs/README.md
@@ -2,7 +2,7 @@

 ## Overview

-Five AI subagents, each embodying a synthetic persona, navigate the live
+Six AI subagents, each embodying a synthetic persona, navigate the live
 DigniFi application through Playwright and report usability findings from
 a human perspective. This produces quantitative PRD metrics and qualitative
 UX insights before real participant recruitment.
@@ -13,13 +13,14 @@ through the ILND means test calculator.

 ## Persona Briefs

-| Brief                 | Archetype                  | Means Test         | Key Test                           |
-| --------------------- | -------------------------- | ------------------ | ---------------------------------- |
-| `maria-torres.md`     | Below-median single parent | Passes, fee waiver | Full happy path                    |
-| `james-washington.md` | Borderline single filer    | Passes (barely)    | Near-threshold messaging           |
-| `priya-sharma.md`     | Above-median family        | Fails              | Dignity-preserving ineligibility   |
-| `deshawn-mitchell.md` | Asset-heavy homeowner      | Passes, fee waiver | Multi-asset entry, exemptions      |
-| `sarah-chen.md`       | Simplest case, no assets   | Passes, fee waiver | Fastest path, empty-state handling |
+| Brief                 | Archetype                  | Means Test                    | Key Test                                  |
+| --------------------- | -------------------------- | ----------------------------- | ----------------------------------------- |
+| `maria-torres.md`     | Below-median single parent | Passes, fee waiver            | Full happy path                           |
+| `james-washington.md` | Borderline single filer    | Passes (barely)               | Near-threshold messaging                  |
+| `priya-sharma.md`     | Above-median family        | Fails                         | Dignity-preserving ineligibility          |
+| `deshawn-mitchell.md` | Asset-heavy homeowner      | Passes, fee waiver            | Multi-asset entry, exemptions             |
+| `sarah-chen.md`       | Simplest case, no assets   | Passes, fee waiver            | Fastest path, empty-state handling        |
+| `andres-kettleby.md`  | Self-employed gig driver   | Passes, no waiver application | Income that isn't wages, ten amounts owed |

 ## How to Run

@@ -43,14 +44,14 @@ cd frontend && npx playwright install chromium
 cd frontend && npm run e2e
 ```

-This runs 7 journey specs programmatically: one for each persona's data path,
+This runs 8 journey specs programmatically: one for each persona's data path,
 plus the SOFA and scanned-bill journeys (the scanned-bill journey skips locally
 unless OPENAI_BASE_URL points at its fake OpenAI server; see the spec's header).
 No AI involved — pure deterministic E2E testing.

 ### AI Persona Simulation (subagent-driven)

-The orchestrator (main Claude session) launches 5 subagents in parallel
+The orchestrator (main Claude session) launches 6 subagents in parallel
 using the Agent tool:

 1. Each subagent receives its persona brief
@@ -94,7 +95,7 @@ Each subagent returns a JSON report:

 | Metric                      | Target                       | Measurement                      |
 | --------------------------- | ---------------------------- | -------------------------------- |
-| Completion rate             | 100% (5/5 personas complete) | `completed` field                |
+| Completion rate             | 100% (6/6 personas complete) | `completed` field                |
 | Mean comprehension          | >= 3.5 / 5                   | `survey_responses.comprehension` |
 | Mean dignity                | >= 4.0 / 5                   | `survey_responses.dignity`       |
 | Mean confidence             | >= 3.5 / 5                   | `survey_responses.confidence`    |
@@ -106,4 +107,4 @@ From the PRD experiment plan:

 - **Pause if:** 2+ personas cannot complete the wizard
 - **Redesign if:** Mean dignity score < 3.0
-- **Celebrate if:** All 5 complete with mean dignity >= 4.0
+- **Celebrate if:** All 6 complete with mean dignity >= 4.0
diff --git a/docs/testing/run-persona-tests.md b/docs/testing/run-persona-tests.md
index 83b0c5d..319d872 100644
--- a/docs/testing/run-persona-tests.md
+++ b/docs/testing/run-persona-tests.md
@@ -19,10 +19,10 @@ cd frontend && npm run e2e

 ## Execution Protocol

-### Step 1: Launch 5 Subagents in Parallel
+### Step 1: Launch 6 Subagents in Parallel

-The orchestrator (main Claude session) launches 5 subagents using the
-Agent tool with `subagent_type: "general-purpose"`. All 5 launch in a
+The orchestrator (main Claude session) launches 6 subagents using the
+Agent tool with `subagent_type: "general-purpose"`. All 6 launch in a
 single message for maximum parallelism.

 Each subagent receives:
@@ -91,7 +91,7 @@ OUTPUT FORMAT:

 ### Step 3: Collect Reports

-After all 5 subagents complete, the orchestrator collects the 5 JSON
+After all 6 subagents complete, the orchestrator collects the 6 JSON
 reports. If a subagent fails or times out, record it as:

 ```json
@@ -108,14 +108,14 @@ The orchestrator computes:

 | Metric                  | Calculation                         |
 | ----------------------- | ----------------------------------- |
-| **Completion rate**     | count(completed=true) / 5           |
+| **Completion rate**     | count(completed=true) / 6           |
 | **Mean comprehension**  | avg(survey_responses.comprehension) |
 | **Mean dignity**        | avg(survey_responses.dignity)       |
 | **Mean confidence**     | avg(survey_responses.confidence)    |
-| **Friction density**    | total friction_points / 5           |
+| **Friction density**    | total friction_points / 6           |
 | **High-severity count** | count(severity="high")              |
 | **Trust score**         | avg(trust_score)                    |
-| **NPS proxy**           | count(would_recommend=true) / 5     |
+| **NPS proxy**           | count(would_recommend=true) / 6     |

 ### Step 5: Rank Friction Points

@@ -166,7 +166,7 @@ From the PRD experiment plan:
 | ----------------------------------- | ----------------------------------------------- |
 | 2+ personas cannot complete         | **PAUSE** — fix blockers before continuing      |
 | Mean dignity < 3.0                  | **REDESIGN** — fundamental tone/language issues |
-| All 5 complete, mean dignity >= 4.0 | **CELEBRATE** — ready for real user testing     |
+| All 6 complete, mean dignity >= 4.0 | **CELEBRATE** — ready for real user testing     |
 | 1 persona fails, dignity >= 3.5     | **ITERATE** — fix specific issue, rerun         |

 ## Quick-Start Command
@@ -174,15 +174,15 @@ From the PRD experiment plan:
 For the orchestrator to copy-paste:

 ```
-Launch 5 subagents in parallel using Agent tool (subagent_type:
+Launch 6 subagents in parallel using Agent tool (subagent_type:
 "general-purpose"). For each persona (maria-torres, james-washington,
-priya-sharma, deshawn-mitchell, sarah-chen):
+priya-sharma, deshawn-mitchell, sarah-chen, andres-kettleby):

 1. Read docs/testing/persona-briefs/<name>.md
 2. Invoke /webapp-testing skill
 3. Navigate http://localhost:5173 as the persona
 4. Return JSON report per the schema above

-After all 5 complete, aggregate results into
+After all 6 complete, aggregate results into
 docs/reports/YYYY-MM-DD-usability-test.md
 ```
diff --git a/docs/testing/test_persona_full_flow.py b/docs/testing/test_persona_full_flow.py
index 0c7394c..0e9a06f 100644
--- a/docs/testing/test_persona_full_flow.py
+++ b/docs/testing/test_persona_full_flow.py
@@ -1,7 +1,7 @@
 """
 Full persona test: login → forms dashboard → generate all → verify → survey.

-Tests all 5 seeded personas through form generation and survey collection.
+Tests all 6 seeded personas through form generation and survey collection.
 Uses pre-seeded accounts (seed_demo_data) which already have completed sessions.

 Strategy: Login via API, set tokens + session ID in localStorage,
@@ -23,6 +23,7 @@ PERSONAS = [
     {"username": "demo_priya", "name": "Priya Sharma"},
     {"username": "demo_deshawn", "name": "DeShawn Mitchell"},
     {"username": "demo_sarah", "name": "Sarah Chen"},
+    {"username": "demo_andres", "name": "Andrés Kettleby"},
 ]
 PASSWORD = "DigniFi-Demo-2026!"

PATCH
````

Each line that counted five personas or seven journeys now counts six or eight. The persona briefs' README gains his row, "Self-employed gig driver | Passes, no waiver application | Income that isn't wages, ten amounts owed", for which prettier re-pads the whole table. `run-persona-tests.md` names him in the quick-start list, and `test_persona_full_flow.py` lists `demo_andres` under its docstring's 6.

- [ ] **Step 6: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2166 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  389 passed (389)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

The counts are Task 10's, since this task changes no backend code and no vitest test. The 25 skips are the Postgres-only tests under sqlite. The next command runs them against the Postgres database named in `.claude/forms-step3a1.env`.

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

- [ ] **Step 7: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 8 passed` and `RUN 2 exit=0: 8 passed`.

The eight are the five persona journeys, the SOFA and scanned-bill journeys, and his. The implementer's runs took 2.0m and 1.8m, and none was skipped, so the scanned-bill journey had its wiring. The five persona journeys type the same amounts into the same box as before, so their outcomes don't change.

- [ ] **Step 8: Commit**

```bash
set -eo pipefail
git add \
  frontend/e2e/journeys/andres-gig-driver.spec.ts \
  CLAUDE.md \
  CONTRIBUTING.md \
  README.md \
  docs/testing/persona-briefs/README.md \
  docs/testing/run-persona-tests.md \
  docs/testing/test_persona_full_flow.py \
  frontend/e2e/fixtures/personas.ts \
  frontend/e2e/pages/sofa.page.ts \
  frontend/e2e/pages/wizard.page.ts
git commit -F - <<'MSG'
test(e2e): Andrés's journey, and income typed by source

The E2E fixture's PersonaIncome carries its amounts by source
(sources: a partial map of the Income step's ten boxes) in place of a
single total, and fillIncomeInfo types each into its own box, leaving
the rest blank. The five existing personas keep their wages, each as
{ monthly_gross_wages: N } with the total they had before, so no
journey's outcome changes (3a1 spec §8, 3a1.Q1).

ANDRES is the sixth persona's data from his brief, under his own login
and SSN 900-66-6006 (the seed's demo_andres has 900-66-0006):
$3,370 a month in the other-income box and $0 in the other nine, the
13 expenses, four assets and ten amounts owed. His journey,
andres-gig-driver.spec.ts, fills the wizard, leaves contracts and
codebtors empty and presses Complete. Today's fee-waiver flag qualifies
him, so it checks that the waiver application opens. He files none
(3a1.Q2): he goes to /sofa by URL, skips it, and Generate All makes 14
forms, with no 103B and, below the median, no 122A-2. After that full
reload the SOFA heading waits on the token refresh, the session read and
the SOFA read, so SOFAPage.waitForLoad takes an optional timeout and his
journey gives it 30 s, not the default 5 s.

The counts move from five personas to six and from seven journeys to
eight in README.md, CLAUDE.md, CONTRIBUTING.md, the persona briefs'
README (with his row) and run-persona-tests.md (with his name in the
quick-start list). test_persona_full_flow.py says 6 and lists
demo_andres.
MSG
git status --short
```

### Task 12: Add a source code link to the footer, as the AGPL expects

_Built and verified as commit `b24f7c4` on `plan/forms-step3a1`._

**Files:**

- Create: `frontend/src/App.test.tsx`
- Create: `frontend/src/components/common/SiteFooter.tsx`
- Modify: `CLAUDE.md`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/common/index.ts`
- Modify: `frontend/src/pages/LandingPage.tsx`
- Modify: `frontend/src/styles/global.css`

**Interfaces:**

- Consumes:
  - `App` in `frontend/src/App.tsx`: the `<Routes>` block inside the `.app` div, after `AppHeader` and the routes, in `AuthProvider` and `ErrorBoundary`.
  - `frontend/src/components/common/index.ts`, which re-exports `SkipNavigation` and `AppHeader` among others, and the barrel import in `App.tsx`: `import { SkipNavigation, AppHeader } from './components/common';`.
  - `LandingPage` in `frontend/src/pages/LandingPage.tsx`, whose UPL disclaimer is a `<footer className="landing-footer">`. Every selector for it in `global.css` names the class (`.landing-footer`, `.landing-footer :focus-visible`, `.landing-disclaimer`), none the tag.
  - The tokens `--space-4`, `--space-5` and `--text-caption` in `frontend/src/styles/global.css`.
  - `vitest-axe`'s `axe` and the `toHaveNoViolations` matcher, registered in `src/test/setup.ts`, and the MSW server there.
  - The project licence, AGPL-3.0-or-later since `d29109c`, and spec section 10.
- Produces:
  - `SiteFooter` in `frontend/src/components/common/SiteFooter.tsx`, a named export and a default export: `<footer className="site-footer">` holding one link, `<a href="https://github.com/crichalchemist/DigniFi">Source code</a>`.
  - `export { SiteFooter } from './SiteFooter';` in `components/common/index.ts`.
  - `<SiteFooter />` in `App.tsx`, directly after `</Routes>`, so it renders on every route, public and signed in.
  - The landing page's disclaimer as `<div className="landing-footer">`: same class, text and children.
  - The `.site-footer` rule in `global.css`.
  - `frontend/src/App.test.tsx`, `describe('Source code link')`: `a visitor on a public page can reach the source`, `a signed-in filer can reach the source` and `the landing page has exactly one contentinfo landmark`.
  - A line in the `CLAUDE.md` frontend file map that names `SiteFooter` and tells a later author to keep the landing disclaimer a `div`.

**Decisions already made in this task:**

- DigniFi is AGPL-3.0-or-later (spec section 10), and a user of the deployed service must be able to reach its source. The footer sits in `App`, after the routes, so no page can leave it out.
- **The link reads exactly "Source code" and opens in the same tab.** The codebase has no external-link convention beyond the register form's `/terms` link, so the link has no `target` or `rel`.
- **The landing page's disclaimer becomes a non-landmark element, so the page has one `contentinfo`.** A `<footer>` that is not inside `article`, `aside`, `main`, `nav` or `section` is a `contentinfo` landmark. The landing page's disclaimer is one, and so is `SiteFooter`. The disclaimer becomes a `div` with the same class, text and children. It looks the same, because the CSS names the class and no selector names the tag. The `WizardLayout` footer sits inside the wizard's layout, not at the top level, and the wizard shows no landing page.
- **The a11y test runs only the contentinfo rules,** `landmark-no-duplicate-contentinfo` and `landmark-contentinfo-is-top-level`. The landing page already has two banner landmarks, `AppHeader.tsx` (`<header role="banner">`) and `LandingPage.tsx` (its top-level hero `<header>`), so a full axe run fails on `landmark-no-duplicate-banner`. That defect is pre-existing and ticketed, and this task leaves it alone. The test says so in a comment.
- **The plan's author dropped `max-width: var(--max-width)` from `.site-footer` after the review.** The review found that no stylesheet defines `--max-width`, so the declaration never applied and the footer was a full-width block anyway. `.app-header-inner` has the same dead declaration. That is pre-existing, and this task leaves it alone. The rule here uses only tokens that exist.
- The footer is not fixed or sticky. It flows after the content, so it covers nothing in the wizard.
- No E2E page object has a `footer` locator: `landing.page.ts` uses `.landing-disclaimer`, and `dashboard.page.ts` uses `.upl-modal-footer`. No journey changes.
- This commit includes the `CLAUDE.md` file-map line, because the rule "keep the landing disclaimer a `div`" is a gotcha for the next author.
- The final gates and journeys ran on this commit.

- [ ] **Step 1: Write the failing test**

```tsx file=frontend/src/App.test.tsx
/**
 * The site footer links to the source on every route (DigniFi is AGPL-3.0-or-later).
 */

import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import App from './App';

const SOURCE_URL = 'https://github.com/crichalchemist/DigniFi';

function renderAt(path: string) {
  window.history.pushState({}, '', path);
  return render(<App />);
}

describe('Source code link', () => {
  it('a visitor on a public page can reach the source', () => {
    renderAt('/terms');
    expect(screen.getByRole('link', { name: 'Source code' })).toHaveAttribute('href', SOURCE_URL);
  });

  it('a signed-in filer can reach the source', async () => {
    localStorage.setItem('refresh_token', 'refresh-token');
    renderAt('/fee-waiver');
    await screen.findByRole('button', { name: 'Sign out' });
    expect(screen.getByRole('link', { name: 'Source code' })).toHaveAttribute('href', SOURCE_URL);
  });

  it('the landing page has exactly one contentinfo landmark', async () => {
    const { container } = renderAt('/');
    expect(screen.getAllByRole('contentinfo')).toHaveLength(1);
    expect(screen.getByRole('link', { name: 'Source code' })).toBeInTheDocument();
    // Only the contentinfo rules: the landing page already has two banners (pre-existing).
    const results = await axe(container, {
      runOnly: ['landmark-no-duplicate-contentinfo', 'landmark-contentinfo-is-top-level'],
    });
    expect(results).toHaveNoViolations();
  });
});
```

The first two tests need the link on a public route (`/terms`) and on a signed-in one (`/fee-waiver`, behind `ProtectedRoute`, with a refresh token in storage). The third needs the landing page to have exactly one `contentinfo` landmark, and the link there too, and no violation of the two contentinfo rules.

- [ ] **Step 2: Run it and watch it fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/App.test.tsx 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Test Files  1 failed (1)` and `Tests  3 failed (3)`. Each test fails on an assertion, because the page has no such link: `Unable to find an accessible element with the role "link" and name "Source code"`.

- [ ] **Step 3: Write the footer and export it**

```tsx file=frontend/src/components/common/SiteFooter.tsx
const SOURCE_URL = 'https://github.com/crichalchemist/DigniFi';

/** The page footer on every route: DigniFi is AGPL-3.0-or-later, so it links to its source. */
export function SiteFooter() {
  return (
    <footer className="site-footer">
      <a href={SOURCE_URL}>Source code</a>
    </footer>
  );
}

export default SiteFooter;
```

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/common/index.ts b/frontend/src/components/common/index.ts
index 1145580..dd6c1fa 100644
--- a/frontend/src/components/common/index.ts
+++ b/frontend/src/components/common/index.ts
@@ -7,3 +7,4 @@ export { FormField, FormTextarea, FormSelect } from './FormField';
 export { Button } from './Button';
 export { SkipNavigation } from './SkipNavigation';
 export { AppHeader } from './AppHeader';
+export { SiteFooter } from './SiteFooter';
PATCH
```

`SiteFooter` is one `<footer>` with one link to the repository. The barrel exports it beside `AppHeader`.

- [ ] **Step 4: Render it on every route**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/App.tsx b/frontend/src/App.tsx
index e821634..faee569 100644
--- a/frontend/src/App.tsx
+++ b/frontend/src/App.tsx
@@ -10,7 +10,7 @@ import { BrowserRouter, Routes, Route, Outlet } from 'react-router-dom';
 import { AuthProvider } from './context/AuthContext';
 import { IntakeProvider } from './context/IntakeContext';
 import { ProtectedRoute } from './components/auth/ProtectedRoute';
-import { SkipNavigation, AppHeader } from './components/common';
+import { SkipNavigation, AppHeader, SiteFooter } from './components/common';
 import { LandingPage } from './pages/LandingPage';
 import { LoginPage } from './pages/LoginPage';
 import { RegisterPage } from './pages/RegisterPage';
@@ -83,6 +83,7 @@ function App() {
                 </Route>
               </Route>
             </Routes>
+            <SiteFooter />
           </div>
         </ErrorBoundary>
       </AuthProvider>
PATCH
```

`<SiteFooter />` follows `</Routes>` inside the `.app` div, so every route shows it.

- [ ] **Step 5: Make the landing disclaimer a div**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/LandingPage.tsx b/frontend/src/pages/LandingPage.tsx
index 5a4daf6..d1ab6b9 100644
--- a/frontend/src/pages/LandingPage.tsx
+++ b/frontend/src/pages/LandingPage.tsx
@@ -140,8 +140,8 @@ export function LandingPage() {
         </div>
       </main>

-      {/* UPL Disclaimer Footer */}
-      <footer className="landing-footer">
+      {/* UPL disclaimer: a div, since SiteFooter is the page's one contentinfo landmark */}
+      <div className="landing-footer">
         <div className="landing-container">
           <p className="landing-disclaimer">
             DigniFi provides legal <strong>information</strong>, not legal advice. This platform
@@ -149,7 +149,7 @@ export function LandingPage() {
             consult a licensed attorney in your jurisdiction.
           </p>
         </div>
-      </footer>
+      </div>
     </div>
   );
 }
PATCH
```

The disclaimer keeps its class and its text and stops being a `contentinfo` landmark, so the landing page has only `SiteFooter`'s.

- [ ] **Step 6: Style the footer**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/styles/global.css b/frontend/src/styles/global.css
index 9e7afc7..38a2ed4 100644
--- a/frontend/src/styles/global.css
+++ b/frontend/src/styles/global.css
@@ -1889,3 +1889,10 @@ a {
   padding-top: var(--space-4);
   border-top: 1px solid var(--color-border);
 }
+
+/* Site footer: the source code link the AGPL expects */
+.site-footer {
+  margin: 0 auto;
+  padding: var(--space-4) var(--space-5);
+  font-size: var(--text-caption);
+}
PATCH
```

`.site-footer` centers its block and pads it with existing space tokens, and sets the caption size.

- [ ] **Step 7: Run the test again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/App.test.tsx 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: `Test Files  1 passed (1)` and `Tests  3 passed (3)`.

- [ ] **Step 8: Name the footer in CLAUDE.md**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index c4a9af1..73f9b73 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -116,6 +116,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 **Frontend:**

 - `src/App.tsx` — Routes, ErrorBoundary, IntakeLayout (shared provider via Outlet)
+- `src/components/common/SiteFooter.tsx` — the one `<footer>` (the page's `contentinfo`), rendered after `</Routes>` on every route: a "Source code" link to the GitHub repo, as the AGPL expects. The landing page's disclaimer is a `div.landing-footer`, not a second footer; keep it so, since the landing page must have one `contentinfo`
 - `src/context/AuthContext.tsx` — JWT auth, silent refresh
 - `src/context/IntakeContext.tsx` — Session state
 - `src/api/client.ts` — typed API client, `getAccessToken()`, `downloadForm()`
PATCH
```

The file map names `SiteFooter` and says to keep the landing disclaimer a `div`.

- [ ] **Step 9: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2166 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  392 passed (392)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

The 25 skips are the Postgres-only tests under sqlite. The next command runs them against the Postgres database named in `.claude/forms-step3a1.env`.

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

- [ ] **Step 10: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 8 passed` and `RUN 2 exit=0: 8 passed`.

The journeys ran on this commit, with the footer on every page they visit.

- [ ] **Step 11: Commit**

```bash
set -eo pipefail
git add \
  frontend/src/App.test.tsx \
  frontend/src/components/common/SiteFooter.tsx \
  CLAUDE.md \
  frontend/src/App.tsx \
  frontend/src/components/common/index.ts \
  frontend/src/pages/LandingPage.tsx \
  frontend/src/styles/global.css
git commit -F - <<'MSG'
feat(app): a source code link in the footer, as the AGPL expects

DigniFi is AGPL-3.0-or-later, so every page now carries a footer with a
"Source code" link to the GitHub repository. SiteFooter renders after the
routes in App, public and signed-in alike.

The landing page's disclaimer was a <footer>, which would have made two
contentinfo landmarks there. It is now a div with the same class, text and
look (the global.css selectors name the class, not the tag).

Tests: the link shows on a public route and a signed-in one, and the landing
page has exactly one contentinfo landmark (checked with vitest-axe's
contentinfo rules). CLAUDE.md's file map names the footer.
MSG
git status --short
```
