# Forms Step 3a1 (Data Foundations) Implementation Plan, Part 1 of 2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lay step 3's foundations. The forms use the U.S. Trustee's median table in force on the day they are filled. Complete and every refusal name the step or page that fixes them. A new asset or debt keeps one id across every save. An unconfirmed scanned debt never prints. Saves on one session take a lock. A sixth persona, Andrés Kettleby, joins the seed and the journeys. The other five personas' private creditors get fictional names, and the site links to its source code.

**Architecture:** One dated-table model (`DatedTable`, `in_force`, `fill_date` in `backend/apps/districts/dated_tables.py`) replaces the median's `latest()` lookup, and the root conftest pins the fill date for every backend test. Refusals carry the wizard step or page that fixes them, from the registry's preconditions through Complete's 400 to the wizard's Review step and the dashboard. The session save returns a sent list in sent order, so the wizard merges new ids by a browser-only row key. `DebtInfo.objects.confirmed()` feeds every form and the means test. `lock_session` (`select_for_update`) guards every intake-data write, and Postgres-only tests prove it in CI. Each of the 12 tasks is one commit, and every task boundary passes every gate.

**This part:** Tasks 1–6. It starts with nothing of 3a1 on this branch. The other parts: Part 2 (`docs/superpowers/plans/2026-10-16-forms-step3a1-part2.md`, Tasks 7–12). The plan is split only to stay under the repository's 500 KB file limit. Run all parts as one execution: one ledger for Tasks 1–12, and the whole-branch final review only after Task 12, because each part's patches expect each file exactly as the earlier tasks leave it.

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

Check the baseline before Task 1:

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

Expected: `2096 passed, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  358 passed (358)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

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

### Task 1: Use the median table in force on the day the forms are filled

_Built and verified as commit `c14a991` on `plan/forms-step3a1`._

**Files:**

- Create: `backend/apps/districts/dated_tables.py`
- Create: `backend/apps/districts/migrations/0003_medianincome_dated_table.py`
- Create: `backend/apps/districts/tests/__init__.py`
- Create: `backend/apps/districts/tests/test_dated_tables.py`
- Create: `backend/apps/intake/tests/test_seed_demo_data.py`
- Create: `docs/REFERENCE_TABLES.md`
- Modify: `CLAUDE.md`
- Modify: `backend/apps/audit/tests/test_upl_compliance.py`
- Modify: `backend/apps/districts/fixtures/ilnd_2025_data.json`
- Modify: `backend/apps/districts/models.py`
- Modify: `backend/apps/eligibility/models.py`
- Modify: `backend/apps/eligibility/services/means_test_calculator.py`
- Modify: `backend/apps/eligibility/tests/test_cmi.py`
- Modify: `backend/apps/eligibility/tests/test_means_test_calculator.py`
- Modify: `backend/apps/forms/tests/test_form_122a1_schema.py`
- Modify: `backend/apps/forms/tests/test_form_views.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier3.py`
- Modify: `backend/apps/forms/views.py`
- Modify: `backend/apps/intake/management/commands/seed_demo_data.py`
- Modify: `backend/apps/intake/tests/test_e2e_intake.py`
- Modify: `backend/apps/intake/tests/test_integration_flow.py`
- Modify: `backend/conftest.py`
- Modify: `frontend/e2e/fixtures/personas.ts`
- Modify: `frontend/e2e/journeys/deshawn-assets.spec.ts`
- Modify: `frontend/e2e/journeys/james-borderline.spec.ts`
- Modify: `frontend/e2e/journeys/priya-ineligible.spec.ts`

**Interfaces:**

- Consumes:
  - `MedianIncome` (`backend/apps/districts/models.py`): `district` (related name `median_incomes`), its own `effective_date`, `family_size_1`…`family_size_8`, `family_size_additional` with `default=9900.00`, and `get_median_income(family_size)`, which uses $9,900 for each person above 8 when the row has no extra-person amount.
  - `MeansTest.calculate` (`backend/apps/eligibility/models.py`), which takes `self.district.median_incomes.latest("effective_date")` and turns any failure into `ValueError("No median income data found for district …")`, and `get_calculation_details()`, which reads the encrypted JSON in `calculation_details`.
  - `MeansTestCalculator` (`backend/apps/eligibility/services/means_test_calculator.py`): `calculate()` passes `IncomeNotSplit` through and prefixes any other `ValueError` with "Means test calculation failed:"; `get_detailed_breakdown()` labels `details["calculated_at"]` as the median's `effective_date`.
  - `_failure(form_type, exc)` in `backend/apps/forms/views.py`: a 422 with the exception's own sentence for `PreconditionMissing | IncomeNotSplit`, a 422 with a fixed sentence for the classes in `_FAILURE_SENTENCES`, and otherwise a 500 logged by exception type only.
  - `seed_demo_data`'s `handle`, which stops with a plain hint when the ILND district is missing, and the fixture `backend/apps/districts/fixtures/ilnd_2025_data.json` with one median row (pk 1, effective 2025-11-01).
  - For the tests: `is_above_median` (`apps.eligibility.cmi`) and the `calculate_means_test` endpoint, which returns a `ValueError` as a 400 whose `error` is `str(e)`.
- Produces:
  - `backend/apps/districts/dated_tables.py`:
    - `class DatedTable(models.Model)`, abstract: `effective_date: DateField`, `valid_through: DateField(null=True, blank=True)`, `source_url: URLField(max_length=300, blank=True, default="")`.
    - `def _today() -> date` (`timezone.localdate()`) and `def fill_date() -> date` (returns `_today()`).
    - `class NoTableInForce(ValueError)` with `.table: str` and `.on: date`; `str(exc)` is the spec §3.4 sentence.
    - `def in_force(rows: QuerySet, on: date, table: str, district: str = "") -> models.Model`: the newest row with `effective_date <= on`, refused when none has started or when that row's `valid_through` is earlier than `on`. A refusal logs `"No %s table in force on %s for district %s"` (table, ISO date, district or `-`) at error level and raises `NoTableInForce`.
  - `MedianIncome(DatedTable)`: `family_size_additional` has no default, and `get_median_income` raises `ValueError` above 8 people when it is `None`.
  - Migration `backend/apps/districts/migrations/0003_medianincome_dated_table.py`, with `census_valid_through(effective_date)` and `date_existing_rows` defined in the file.
  - The fixture's two median rows: pk 1 (2025-11-01 → 2026-03-31) and pk 2 (2026-04-01 → 2026-10-31), each with its `source_url`.
  - `MEDIAN_TABLE = "Census median income"` in `apps/eligibility/models.py`, imported by `seed_demo_data`.
  - `MeansTest.calculation_details["median_table"]`: `{"name": "Census median income", "effective_date": "YYYY-MM-DD", "valid_through": "YYYY-MM-DD" or None, "source_url": str}`. Task 2's packet endpoint reads it.
  - `get_detailed_breakdown()["means_test_threshold"]["effective_date"]` is that table's `effective_date`, or `None` for a row calculated before tables were dated.
  - `_failure`: `NoTableInForce` is a 422 with its own sentence.
  - The root `backend/conftest.py` autouse fixture `_fill_forms_on_a_fixed_day`, which patches `apps.districts.dated_tables._today` to return `date(2026, 10, 16)` for every backend test.
  - `docs/REFERENCE_TABLES.md`, the runbook, with a "Census median income" section.
  - `CLAUDE.md`: the new gotcha "Dated tables and the fill date"; "Seed order", "The packet decides which forms a filer gets", "Forms need a completed intake" and "GenerateAll vs single" reworded.
  - Tests in `backend/apps/districts/tests/test_dated_tables.py`: `test_the_newest_table_in_force_on_the_fill_date_is_the_one_used` (3 cases), `test_an_older_open_ended_table_never_stands_in_for_a_newer_one_past_its_valid_through`, `test_a_newest_table_past_its_valid_through_refuses_and_logs_only_the_table_date_and_district`, `test_no_table_started_yet_refuses_in_plain_words_and_logs_only_the_table_date_and_district`, `test_an_open_ended_table_stays_in_force`, `test_a_filer_between_the_two_tables_is_above_the_median_until_april_1_and_below_from_it`, `test_the_means_test_records_the_median_table_it_used`, `test_every_median_row_in_the_fixture_says_when_it_ends_and_where_it_comes_from`, `test_the_migration_ends_a_stored_row_the_day_before_the_next_census_update` (2 cases), `test_the_migration_dates_each_stored_row_and_names_the_page_it_comes_from`, `test_a_household_above_eight_adds_the_tables_own_amount_for_each_extra_person` and `test_a_household_above_eight_is_refused_when_the_table_has_no_extra_person_amount`.
  - Other tests: `test_cmi.py`'s `test_the_means_test_passes_a_missing_median_table_on_without_its_failure_prefix`, `test_other_means_test_failures_keep_their_prefix` and `test_means_test_endpoint_refuses_without_a_median_table_in_force_as_a_400`; `test_form_views.py`'s `test_no_median_table_in_force_is_refused_in_plain_words_and_logged_without_filer_data`; `backend/apps/intake/tests/test_seed_demo_data.py`'s `test_a_reseed_with_no_median_table_in_force_keeps_the_demo_personas_and_points_to_the_runbook`.

**Decisions already made in this task:**

- **This is 3a1's first commit** (umbrella: "It is 3a1's first commit, built on the dated-data model"). Nothing in 3a1 deploys.
- **The lookup follows Ruling R1-a.** `in_force` takes the newest row whose `effective_date` is on or before the fill date and refuses when that row's `valid_through` has passed. It never looks at an older row, which is spec §3.4's "It never falls back to an older table". Where §3.4's lookup bullet reads as a filter on both dates at once, R1-a wins: under that filter an older open-ended row would stand in after a newer scheduled row expired. The controller rewords that bullet to match when the plan is committed. `test_an_older_open_ended_table_never_stands_in_for_a_newer_one_past_its_valid_through` tells the two apart, and both refusal paths log the same one line.
- **The refusal is the spec's sentence, word for word** (§3.4): "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your forms. Please try again later." The forms views return it as a 422. `calculate_means_test` keeps its 400 and now shows the same sentence, because the calculator passes `NoTableInForce` through unprefixed, as it already did `IncomeNotSplit`.
- **The log names only the table, the date and the district** (logs reach Sentry, DIG-105), for example "No Census median income table in force on 2026-11-01 for district ilnd". The forms views add no "Filling … failed" line for this refusal.
- **No November 2026 table was posted when this commit was built.** On 2026-10-16 the U.S. Trustee's means-testing page still ended at the "7/15/2026 or After" period, and the `20261101` table page returned 404. So the fixture has two rows, not three, and its second row runs to 2026-10-31. From 2026-11-01 the forms, the means test, `seed_demo_data` and CI's E2E job refuse until the November table is loaded as `docs/REFERENCE_TABLES.md` describes. That is the refusal working as designed (spec §3.8). The backend tests are unaffected, because the root conftest pins the fill date to 2026-10-16.
- **The fill date is pinned for every backend test from this commit on.** The conftest patches `apps.districts.dated_tables._today`, and `fill_date()` looks `_today` up at call time, so no module may import `_today` by name. A test of the lookup sets its own day with `monkeypatch`. No date-freezing library is added, and no dependency at all.
- **Tests stay inside the fixture's dates.** The fixture tests use only 2026-03-31, 2026-04-01, 2026-10-31 and the pinned 2026-10-16, and every test of a day past the fixture builds its own rows in a second district, `ilcd`. So loading the November row changes no test, as the runbook says (review I1).
- **`family_size_additional` stays NOT NULL.** It never had `null=True`; only its default goes, so a table row can't load without the amount (spec §3.2). The `ValueError` in `get_median_income` is reachable only on an unsaved row, which is how its test reaches it. Five tests that build their own median row now give it the amount.
- **The migration defines its schedule function in the file,** because a migration must keep running the code it shipped with. `census_valid_through` takes the first of April 1 and November 1 this year and April 1 next year that falls strictly after the effective date, minus a day. The reverse step is a no-op. The two `AlterField`s issue no SQL: `effective_date` takes `DatedTable`'s help text, and `family_size_additional` loses its default.
- **The fixture keeps its name,** `ilnd_2025_data.json`, because CI, the root `CLAUDE.md` and seven test files load it by name. Row 2 sets `created_at` itself, since `loaddata` saves rows raw and skips `auto_now_add`. Its figures match the April 2026 page: $73,180 / $93,934 / $113,625 / $137,902, and $11,100 for each person over 4.
- **`MEDIAN_TABLE` names the table once.** The means test's lookup, the recorded `median_table.name` and the seed's check all use it. The tests keep their own `"Census median income"` literal, so a renamed constant fails them.
- **The calculator's prefix branch keeps a test.** No other `ValueError` from `MeansTest.calculate` is reachable without a mock, so `test_other_means_test_failures_keep_their_prefix` patches `MeansTest.calculate`, the calculator's boundary (review M4).
- **The seed checks first (Ruling R1-c).** `seed_demo_data` runs `in_force` after its district check and before `--reset` deletes anything. With no table in force it writes "No ILND median income table is in force today, so nothing was changed. Add the current table as docs/REFERENCE_TABLES.md describes, then run: python manage.py loaddata ilnd_2025_data" and returns, so a refused reseed leaves the demo personas. `in_force` logs its own line too. The test deletes the median rows instead of moving the date, so a November row never changes it.
- **The runbook names the operator by role,** "the project owner" (Ruling R1-b).
- **Only 122A-1 line 13C moves in tier 3** (spec §3.8): Maria 113625.00, James and Sarah 73180.00, DeShawn 93934.00, Priya 137902.00. No persona's result changes. The comments in the seed, `personas.ts` and three journey specs get the new figures. The frontend unit-test mocks that carry $71,304 stay, since they mock the API.
- **The forms views' refusal test also covers Regenerate** (review M3), so it checks five calls and five log lines. Its old constant `NOT_PREPARED` is used nowhere else and goes.
- **The conftest's other change is black's.** The pre-commit hook turns `'config.settings.test'` into double quotes.
- **Left for later:** the wizard's sidebar preview still maps every 400 from `calculate_means_test` to "We'll estimate your eligibility once you provide income and expense information." Task 4 shows the 400's own sentence there (review M2). `docs/PLAIN_LANGUAGE_GUIDE.md:411` keeps its $91,526 example (review M8).

- [ ] **Step 1: Write the failing tests**

```python file=backend/apps/districts/tests/__init__.py
"""Tests for districts app."""
```

```python file=backend/apps/districts/tests/test_dated_tables.py
"""The median income table in force on the day the forms are filled (forms step 3a1 spec §3).

Business intent: the U.S. Trustee applies a new Census median table on a schedule, and the
table decides who is above the median, which forms a filer gets and what 122A-1 prints. So
the means test reads the table in force on the fill date, and when none is in force it
refuses in plain words instead of passing a filer on an out-of-date figure. Lookup tests set
their own date; the rest run on the root conftest's 2026-10-16.
"""

import importlib
import json
import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.districts.dated_tables import NoTableInForce, in_force
from apps.districts.models import District, MedianIncome
from apps.eligibility.cmi import is_above_median
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.intake.models import IncomeInfo, IntakeSession
from apps.users.models import User

MEDIAN = "Census median income"
NO_MEDIAN_TABLE = (
    "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your "
    "forms. Please try again later."
)
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "ilnd_2025_data.json"
MIGRATION = "0003_medianincome_dated_table"


@pytest.fixture
def ilnd(db):
    """The real ILND data: the November 2025 and April 2026 median tables."""
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    return District.objects.get(code="ilnd")


def _fill_on(monkeypatch, day):
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: day)


def _single_filer(district, monthly_wages):
    user = User.objects.create_user(username="between", password="pw")
    session = IntakeSession.objects.create(user=user, district=district)
    IncomeInfo.objects.create(
        session=session,
        marital_status="single",
        number_of_dependents=0,
        monthly_gross_wages=Decimal(monthly_wages),
    )
    return session


@pytest.mark.parametrize(
    "fill_date,effective",
    [
        (date(2026, 3, 31), date(2025, 11, 1)),
        (date(2026, 4, 1), date(2026, 4, 1)),
        (date(2026, 10, 31), date(2026, 4, 1)),
    ],
    ids=["last_day_of_november_2025_table", "first_day_of_april_2026_table", "its_last_day"],
)
def test_the_newest_table_in_force_on_the_fill_date_is_the_one_used(ilnd, fill_date, effective):
    table = in_force(ilnd.median_incomes.all(), fill_date, MEDIAN, ilnd.code)

    assert table.effective_date == effective


# Tests past the fixture's last day build their own rows, so loading a newer table into the
# fixture changes none of them (docs/REFERENCE_TABLES.md).


@pytest.fixture
def ilcd(db):
    return District.objects.create(
        code="ilcd",
        name="Central District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )


SIZES = {f"family_size_{n}": Decimal(50000 + 10000 * n) for n in range(1, 9)}


def _table(district, effective_date, valid_through=None):
    return MedianIncome.objects.create(
        district=district,
        effective_date=effective_date,
        valid_through=valid_through,
        family_size_additional=Decimal("10000.00"),
        **SIZES,
    )


def test_an_older_open_ended_table_never_stands_in_for_a_newer_one_past_its_valid_through(ilcd):
    _table(ilcd, date(2025, 1, 1))
    _table(ilcd, date(2026, 4, 1), valid_through=date(2026, 10, 31))

    with pytest.raises(NoTableInForce) as refused:
        in_force(ilcd.median_incomes.all(), date(2026, 11, 1), MEDIAN, ilcd.code)

    assert refused.value.table == MEDIAN
    assert refused.value.on == date(2026, 11, 1)


def test_a_newest_table_past_its_valid_through_refuses_and_logs_only_the_table_date_and_district(
    ilcd, caplog
):
    _table(ilcd, date(2026, 4, 1), valid_through=date(2026, 10, 31))

    with pytest.raises(NoTableInForce) as refused:
        in_force(ilcd.median_incomes.all(), date(2026, 11, 1), MEDIAN, ilcd.code)

    assert str(refused.value) == NO_MEDIAN_TABLE
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (logging.ERROR, "No Census median income table in force on 2026-11-01 for district ilcd")
    ]


def test_no_table_started_yet_refuses_in_plain_words_and_logs_only_the_table_date_and_district(
    ilcd, caplog
):
    _table(ilcd, date(2026, 11, 1), valid_through=date(2027, 3, 31))

    with pytest.raises(NoTableInForce) as refused:
        in_force(ilcd.median_incomes.all(), date(2026, 10, 16), MEDIAN, ilcd.code)

    assert str(refused.value) == NO_MEDIAN_TABLE
    assert isinstance(refused.value, ValueError)
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (logging.ERROR, "No Census median income table in force on 2026-10-16 for district ilcd")
    ]


def test_an_open_ended_table_stays_in_force(ilcd):
    open_ended = _table(ilcd, date(2025, 1, 1))

    assert in_force(ilcd.median_incomes.all(), date(2030, 1, 1), MEDIAN) == open_ended


def test_a_filer_between_the_two_tables_is_above_the_median_until_april_1_and_below_from_it(
    ilnd, monkeypatch
):
    # $6,000 a month is $72,000 a year: above the November 2025 single-filer median
    # ($71,304) and below the April 2026 one ($73,180).
    session = _single_filer(ilnd, "6000.00")

    _fill_on(monkeypatch, date(2026, 3, 31))
    before = MeansTestCalculator(session).calculate()
    _fill_on(monkeypatch, date(2026, 4, 1))
    after = MeansTestCalculator(session).calculate()

    assert before["median_income_threshold"] == Decimal("71304.00")
    assert is_above_median(before["cmi"], before["median_income_threshold"])
    assert after["median_income_threshold"] == Decimal("73180.00")
    assert not is_above_median(after["cmi"], after["median_income_threshold"])


def test_the_means_test_records_the_median_table_it_used(ilnd):
    session = _single_filer(ilnd, "3000.00")

    MeansTestCalculator(session).calculate()

    assert session.means_test.get_calculation_details()["median_table"] == {
        "name": MEDIAN,
        "effective_date": "2026-04-01",
        "valid_through": "2026-10-31",
        "source_url": (
            "https://www.justice.gov/ust/eo/bapcpa/20260401/bci_data/median_income_table.htm"
        ),
    }


def test_every_median_row_in_the_fixture_says_when_it_ends_and_where_it_comes_from():
    rows = [
        row["fields"]
        for row in json.loads(FIXTURE.read_text())
        if row["model"] == "districts.medianincome"
    ]

    assert rows
    for row in rows:
        published = row["effective_date"].replace("-", "")
        assert row["valid_through"] > row["effective_date"]
        assert row["source_url"] == (
            f"https://www.justice.gov/ust/eo/bapcpa/{published}/bci_data/median_income_table.htm"
        )


@pytest.mark.parametrize(
    "effective,valid_through",
    [(date(2025, 11, 1), date(2026, 3, 31)), (date(2026, 4, 1), date(2026, 10, 31))],
)
def test_the_migration_ends_a_stored_row_the_day_before_the_next_census_update(
    effective, valid_through
):
    migration = importlib.import_module(f"apps.districts.migrations.{MIGRATION}")

    assert migration.census_valid_through(effective) == valid_through


@pytest.fixture
def migrate(transactional_db):
    """Migrate the districts app to a migration and return the models as they were there.

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


def test_the_migration_dates_each_stored_row_and_names_the_page_it_comes_from(migrate):
    apps = migrate([("districts", "0002_alter_district_state_and_more")])
    district = apps.get_model("districts", "District").objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    for effective in (date(2025, 11, 1), date(2026, 4, 1)):
        apps.get_model("districts", "MedianIncome").objects.create(
            district_id=district.pk, effective_date=effective, **SIZES
        )

    apps = migrate([("districts", MIGRATION)])

    stored = apps.get_model("districts", "MedianIncome").objects.order_by("effective_date")
    assert [(row.valid_through, row.source_url) for row in stored] == [
        (
            date(2026, 3, 31),
            "https://www.justice.gov/ust/eo/bapcpa/20251101/bci_data/median_income_table.htm",
        ),
        (
            date(2026, 10, 31),
            "https://www.justice.gov/ust/eo/bapcpa/20260401/bci_data/median_income_table.htm",
        ),
    ]


# ── The extra-person amount comes from the table (spec §3.2) ──


def _april_2026_table(additional):
    return MedianIncome(family_size_8=Decimal("182302.00"), family_size_additional=additional)


def test_a_household_above_eight_adds_the_tables_own_amount_for_each_extra_person():
    assert _april_2026_table(Decimal("11100.00")).get_median_income(10) == Decimal("204502.00")


def test_a_household_above_eight_is_refused_when_the_table_has_no_extra_person_amount():
    with pytest.raises(ValueError, match="extra person"):
        _april_2026_table(None).get_median_income(9)
```

The districts app gets its first test package. The lookup tests set their own fill date. The fixture tests load `ilnd_2025_data` and use only days inside its rows; the tests of a day past them build their own rows in district `ilcd`. The migration test runs the real migration from `0002` to `0003` with `MigrationExecutor` on `transactional_db`, because SQLite can't change a schema inside a test's transaction, and checks both rows' `valid_through` and `source_url`.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/eligibility/tests/test_cmi.py b/backend/apps/eligibility/tests/test_cmi.py
index ce3870f..a6b4e2d 100644
--- a/backend/apps/eligibility/tests/test_cmi.py
+++ b/backend/apps/eligibility/tests/test_cmi.py
@@ -9,12 +9,15 @@ so CMI refuses it in plain words instead of guessing (forms step 2 spec §5.5).

 from datetime import date
 from decimal import Decimal
+from unittest.mock import patch

 import pytest
 from rest_framework.test import APIClient

+from apps.districts.dated_tables import NoTableInForce
 from apps.districts.models import District, MedianIncome
 from apps.eligibility.cmi import IncomeNotSplit, current_monthly_income
+from apps.eligibility.models import MeansTest
 from apps.eligibility.services.expense_deduction_calculator import ExpenseDeductionCalculator
 from apps.eligibility.services.means_test_calculator import MeansTestCalculator
 from apps.forms.services.derivations import DERIVATIONS
@@ -22,6 +25,10 @@ from apps.intake.models import IncomeInfo, IntakeSession
 from apps.users.models import User

 SPLIT_BY_SOURCE = "Enter your income by source on the Income step."
+NO_MEDIAN_TABLE = (
+    "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your "
+    "forms. Please try again later."
+)


 @pytest.fixture
@@ -116,14 +123,25 @@ def test_the_means_test_passes_the_refusal_on_without_its_failure_prefix(filer):
     assert str(refused.value) == SPLIT_BY_SOURCE


-def test_other_means_test_failures_keep_their_prefix(filer):
+def test_the_means_test_passes_a_missing_median_table_on_without_its_failure_prefix(filer):
     _, session = filer
     IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3000.00"))
     MedianIncome.objects.all().delete()

-    with pytest.raises(ValueError, match="^Means test calculation failed: No median income"):
+    with pytest.raises(NoTableInForce) as refused:
         MeansTestCalculator(session).calculate()

+    assert str(refused.value) == NO_MEDIAN_TABLE
+
+
+def test_other_means_test_failures_keep_their_prefix(filer):
+    _, session = filer
+    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3000.00"))
+
+    with patch.object(MeansTest, "calculate", side_effect=ValueError("x")):
+        with pytest.raises(ValueError, match="^Means test calculation failed: x$"):
+            MeansTestCalculator(session).calculate()
+

 def test_the_above_median_calculator_refuses_income_not_split_instead_of_using_zero(filer):
     _, session = filer
@@ -143,3 +161,16 @@ def test_means_test_endpoint_asks_for_income_by_source_as_a_400(filer):

     assert response.status_code == 400
     assert response.data["error"] == SPLIT_BY_SOURCE
+
+
+def test_means_test_endpoint_refuses_without_a_median_table_in_force_as_a_400(filer):
+    user, session = filer
+    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3000.00"))
+    MedianIncome.objects.all().delete()
+    client = APIClient()
+    client.force_authenticate(user=user)
+
+    response = client.post(f"/api/intake/sessions/{session.pk}/calculate_means_test/")
+
+    assert response.status_code == 400
+    assert response.data["error"] == NO_MEDIAN_TABLE
diff --git a/backend/apps/eligibility/tests/test_means_test_calculator.py b/backend/apps/eligibility/tests/test_means_test_calculator.py
index a0b4d1a..2b5975e 100644
--- a/backend/apps/eligibility/tests/test_means_test_calculator.py
+++ b/backend/apps/eligibility/tests/test_means_test_calculator.py
@@ -826,8 +826,9 @@ class TestDetailedBreakdown:
         assert breakdown["family_composition"]["number_of_dependents"] == 0
         assert breakdown["family_composition"]["total_family_size"] == 1

-        # Verify means test threshold
+        # Verify means test threshold: dated by the median table, not by the calculation
         assert breakdown["means_test_threshold"]["median_income"] == 71304.00
+        assert breakdown["means_test_threshold"]["effective_date"] == "2025-11-01"
         assert breakdown["means_test_threshold"]["district"] == "ILND"

         # Verify results
@@ -1079,6 +1080,7 @@ class TestAboveMedianEndToEnd:
             family_size_6=Decimal("105000"),
             family_size_7=Decimal("115000"),
             family_size_8=Decimal("125000"),
+            family_size_additional=Decimal("11100"),
         )
         session = IntakeSession.objects.create(user=user, district=district)
         DebtorInfo.objects.create(
PATCH
```

`test_cmi.py`'s prefix test, which deleted every median row, becomes the missing-table test and expects the plain sentence. Its name, `test_other_means_test_failures_keep_their_prefix`, goes to a test that patches `MeansTest.calculate` to raise `ValueError("x")` and expects the prefix. The new endpoint test expects the sentence in the 400's `error`. In `test_means_test_calculator.py` the breakdown test now requires the median table's own date, 2025-11-01, the date of the table that test builds. The same patch gives that file's `TestAboveMedianEndToEnd` row its extra-person amount (Step 4 explains why).

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_form_views.py b/backend/apps/forms/tests/test_form_views.py
index 72ba205..d2bd562 100644
--- a/backend/apps/forms/tests/test_form_views.py
+++ b/backend/apps/forms/tests/test_form_views.py
@@ -16,6 +16,7 @@ Covers:
 """

 import json
+import logging
 from datetime import date
 from decimal import Decimal
 from unittest.mock import patch
@@ -695,7 +696,11 @@ class TestCompletionCheck:
 # ── The means test is worked out again before the packet is decided (spec §5.6) ──

 SPLIT_BY_SOURCE = "Enter your income by source on the Income step."
-NOT_PREPARED = "This form couldn't be prepared. Please try again later."
+NO_MEDIAN_TABLE = (
+    "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your "
+    "forms. Please try again later."
+)
+NO_MEDIAN_TABLE_LOGGED = "No Census median income table in force on 2026-10-16 for district ilnd"


 def _set_wages(session, wages):
@@ -838,7 +843,7 @@ class TestMeansTestWorkedOutAgain:
         assert generate.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
         assert generate.data == {"form_type": "form_106dec", "error": SPLIT_BY_SOURCE}

-    def test_missing_median_income_is_a_500_logged_by_type_only(
+    def test_no_median_table_in_force_is_refused_in_plain_words_and_logged_without_filer_data(
         self, api_client, session_with_debtor, user, caplog
     ):
         session = session_with_debtor
@@ -848,29 +853,34 @@ class TestMeansTestWorkedOutAgain:
             session=session, form_type="form_106dec", status="generated", generated_by=user
         )

+        def logged_errors():
+            return [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
+
         generate_all = api_client.post(
             "/api/forms/generate_all/", {"session_id": session.id}, format="json"
         )
+        # Operations fix this, so the refusal is logged once: the table, the date and the
+        # district, and nothing about the filer (logs reach Sentry, DIG-105).
+        assert logged_errors() == [NO_MEDIAN_TABLE_LOGGED]
         listed = api_client.get("/api/forms/packet/", {"session": session.id})
         generate = api_client.post(
             "/api/forms/generate/",
             {"session_id": session.id, "form_type": "form_106dec"},
             format="json",
         )
+        regenerate = api_client.post(f"/api/forms/{unfiled.id}/regenerate/")
         download = api_client.get(f"/api/forms/{unfiled.id}/download/")

         for resp in (generate_all, listed):
-            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
-            assert resp.data == {"error": NOT_PREPARED}
-        for resp in (generate, download):
-            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
-            assert resp.data == {"form_type": "form_106dec", "error": NOT_PREPARED}
+            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
+            assert resp.data == {"error": NO_MEDIAN_TABLE}
+        for resp in (generate, regenerate, download):
+            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
+            assert resp.data == {"form_type": "form_106dec", "error": NO_MEDIAN_TABLE}
         assert set(
             GeneratedForm.objects.filter(session=session).values_list("form_type", flat=True)
         ) == {"form_103b", "form_106dec"}
-        # Operations fix this; the log names the exception's type and nothing it says.
-        assert "ValueError" in caplog.text
-        assert "median income data" not in caplog.text
+        assert logged_errors() == [NO_MEDIAN_TABLE_LOGGED] * 5


 # ── A filed form is kept after it leaves the packet (DIG-155) ─────────
diff --git a/backend/apps/forms/tests/test_oracle_tier3.py b/backend/apps/forms/tests/test_oracle_tier3.py
index 85ab637..badae7f 100644
--- a/backend/apps/forms/tests/test_oracle_tier3.py
+++ b/backend/apps/forms/tests/test_oracle_tier3.py
@@ -59,7 +59,7 @@ EXPECTED = {
             "Quest11": "3200.00",
             "12B": "38400.00",
             "13B": "3",
-            "13C": "110712.00",
+            "13C": "113625.00",
             "14a": BELOW_MEDIAN,
         },
         "schedule_i": {
@@ -94,7 +94,7 @@ EXPECTED = {
             "Quest11": "5833.00",
             "12B": "69996.00",
             "13B": "1",
-            "13C": "71304.00",
+            "13C": "73180.00",
             "14a": BELOW_MEDIAN,
         },
         "schedule_i": {
@@ -127,7 +127,7 @@ EXPECTED = {
             "Quest11": "12000.00",
             "12B": "144000.00",
             "13B": "4",
-            "13C": "134366.00",
+            "13C": "137902.00",
             "14a": ABOVE_MEDIAN,
         },
         "schedule_i": {
@@ -162,7 +162,7 @@ EXPECTED = {
             "Quest11": "3500.00",
             "12B": "42000.00",
             "13B": "2",
-            "13C": "91526.00",
+            "13C": "93934.00",
             "14a": BELOW_MEDIAN,
         },
         "schedule_i": {
@@ -194,7 +194,7 @@ EXPECTED = {
             "Quest11": "2000.00",
             "12B": "24000.00",
             "13B": "1",
-            "13C": "71304.00",
+            "13C": "73180.00",
             "14a": BELOW_MEDIAN,
         },
         "schedule_i": {
PATCH
```

The forms views' missing-median test becomes `test_no_median_table_in_force_is_refused_in_plain_words_and_logged_without_filer_data`. Generate All and the packet list are 422 `{"error"}`, Generate, Regenerate and an unfiled download are 422 `{"form_type", "error"}`, no stored form row is deleted, and the only error-level records are the lookup's one line per refusal. Tier 3 expects each persona's line 13C from the April 2026 table.

```python file=backend/apps/intake/tests/test_seed_demo_data.py
"""The demo seed checks for a median table in force before it deletes anything (3a1 spec §3).

Business intent: the demo personas carry the partner demos and the E2E journeys. A reseed
that can't work their means tests out must leave the existing personas as they are and tell
the operator where to find how to load the missing table.
"""

from io import StringIO

import pytest
from django.core.management import call_command

from apps.districts.models import MedianIncome
from apps.users.models import User


@pytest.mark.django_db
def test_a_reseed_with_no_median_table_in_force_keeps_the_demo_personas_and_points_to_the_runbook():
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona="james", stdout=StringIO())
    james = User.objects.get(username="demo_james").pk
    MedianIncome.objects.all().delete()
    err = StringIO()

    call_command("seed_demo_data", "--reset", stdout=StringIO(), stderr=err)

    assert User.objects.get(username="demo_james").pk == james
    assert "docs/REFERENCE_TABLES.md" in err.getvalue()
```

The seed test seeds James, deletes every median row and reseeds with `--reset`. James must still be there under the same id, and stderr must name `docs/REFERENCE_TABLES.md`.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=line -rN --continue-on-collection-errors apps/districts apps/eligibility/tests/test_cmi.py apps/eligibility/tests/test_means_test_calculator.py apps/forms/tests/test_form_views.py apps/forms/tests/test_oracle_tier3.py apps/intake/tests/test_seed_demo_data.py -q -p no:cacheprovider 2>&1 | tail -40
```

Expected: FAIL — `8 failed, 240 passed` and `2 errors`. Both errors are `ModuleNotFoundError: No module named 'apps.districts.dated_tables'`: test_dated_tables.py and test_cmi.py import the module this task creates, and --continue-on-collection-errors lets the other files run. Tier 3's five 13C cases print the November 2025 medians, for example `wrong_value: prints ['110712.00'], expected 113625.00` for Maria. The seed's --reset deletes James and then stops on `ValueError: Means test calculation failed: No median income data found for district ilnd`. The forms views' refusal test fails on its first assertion, because Generate All is still a 500 logged as "Filling the packet failed" instead of the lookup's one line. The breakdown test finds the calculation's own timestamp where it wants 2025-11-01.

- [ ] **Step 3: Add the dated tables and pin the fill date**

```python file=backend/apps/districts/dated_tables.py
"""
Public tables that change on a schedule, and the one way to pick the table in force.

The day the forms are filled stands in for the filing date (forms step 3a1 spec §3.3), so
every lookup of a dated table takes fill_date(), and nothing else reads the clock for this.
"""

import logging
from datetime import date

from django.db import models
from django.db.models import QuerySet
from django.utils import timezone

logger = logging.getLogger(__name__)


class DatedTable(models.Model):
    """A row of a public table that applies from effective_date through valid_through."""

    effective_date = models.DateField(help_text="First day this table applies.")
    valid_through = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Last day before the table's next scheduled change. "
            "Empty means it stays in force until a newer row replaces it."
        ),
    )
    source_url = models.URLField(
        max_length=300, blank=True, default="", help_text="Where the table is published."
    )

    class Meta:
        abstract = True


class NoTableInForce(ValueError):
    """No row of a dated table applies on the fill date, and no older row stands in.

    Either no row has started yet, or the newest one that has is past its valid_through.
    """

    def __init__(self, table: str, on: date) -> None:
        self.table = table
        self.on = on
        super().__init__(
            "DigniFi doesn't have the income figures for today's date yet, so it can't "
            "prepare your forms. Please try again later."
        )


def _today() -> date:
    """Today in the pilot district's zone (TIME_ZONE). The root conftest pins it in tests."""
    return timezone.localdate()


def fill_date() -> date:
    """The day the forms are filled, which stands in for the filing date."""
    return _today()


def in_force(rows: QuerySet, on: date, table: str, district: str = "") -> models.Model:
    """The newest row effective on or before `on`, if its valid_through hasn't passed.

    Rows effective after `on` are ignored. When the newest row that has started ended before
    `on`, no older row is looked at: the table is refused, not replaced by an older one.

    Raises:
        NoTableInForce: no row has started yet, or the newest one that has is past its
            valid_through. Either way it is logged once with the table's name, the date and
            the district code, never the filer's data, since logs reach Sentry (DIG-105).
    """
    row = rows.filter(effective_date__lte=on).order_by("-effective_date").first()
    if row is None or (row.valid_through is not None and row.valid_through < on):
        logger.error(
            "No %s table in force on %s for district %s", table, on.isoformat(), district or "-"
        )
        raise NoTableInForce(table, on)
    return row
```

```bash
git apply <<'PATCH'
diff --git a/backend/conftest.py b/backend/conftest.py
index 5b0db71..e000e1b 100644
--- a/backend/conftest.py
+++ b/backend/conftest.py
@@ -1,8 +1,11 @@
+from datetime import date
+
 import django
+import pytest
 from django.conf import settings

 # Configure Django settings for pytest
-django_settings_module = 'config.settings.test'
+django_settings_module = "config.settings.test"

 # Standalone manual test scripts — not pytest tests.
 collect_ignore = [
@@ -15,3 +18,12 @@ collect_ignore = [
 def pytest_configure():
     settings.DJANGO_SETTINGS_MODULE = django_settings_module
     django.setup()
+
+
+@pytest.fixture(autouse=True)
+def _fill_forms_on_a_fixed_day(monkeypatch):
+    # Dated tables are looked up by the day the forms are filled (3a1 spec §3.3). Pinning
+    # that day keeps CI the same every month: on the real clock, the fixture's newest
+    # median table would stop being in force on November 1 and every forms test would
+    # refuse. Tests of the lookup itself set their own date.
+    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2026, 10, 16))
PATCH
```

`dated_tables.py` holds the one model shape and the one lookup for every public table step 3 reads (§3.2–3.4). The conftest fixture pins the fill date for every backend test, so CI behaves the same every month (§3.3). It goes in after the module: `monkeypatch` imports `apps.districts.dated_tables` from the dotted path it is given, so before the module exists every test would error.

- [ ] **Step 4: Make the median a dated table**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/districts/models.py b/backend/apps/districts/models.py
index ae0473c..14174a9 100644
--- a/backend/apps/districts/models.py
+++ b/backend/apps/districts/models.py
@@ -8,6 +8,8 @@ from decimal import Decimal
 from django.core.validators import RegexValidator
 from django.db import models

+from .dated_tables import DatedTable
+

 class District(models.Model):
     """
@@ -55,21 +57,20 @@ class District(models.Model):
         return f"{self.name} ({self.code.upper()})"


-class MedianIncome(models.Model):
+class MedianIncome(DatedTable):
     """
     Median income thresholds per district and effective period, for means test qualification.

     Fields:
         district (District): Reference to the relevant district.
         effective_date (date): Date this threshold became effective.
+        valid_through (date): Last day before the next Census update; empty means open-ended.
+        source_url (str): The U.S. Trustee page the figures come from.
         family_size_1..8 (Decimal): Median annual household income by family size.
         created_at (datetime): Timestamp of record creation.
     """

     district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="median_incomes")
-    effective_date = models.DateField(
-        help_text="Date when this median income threshold became effective."
-    )
     family_size_1 = models.DecimalField(
         max_digits=12, decimal_places=2, help_text="1-person household median income."
     )
@@ -98,7 +99,6 @@ class MedianIncome(models.Model):
         max_digits=12,
         decimal_places=2,
         help_text="Amount to add for each additional person above 8.",
-        default=9900.00,
     )
     created_at = models.DateTimeField(auto_now_add=True, help_text="Record creation time.")

@@ -122,7 +122,7 @@ class MedianIncome(models.Model):
             Decimal: The median income for the specified family size.

         Raises:
-            ValueError: If family_size is less than 1.
+            ValueError: If family_size is less than 1, or above 8 with no extra-person amount.
         """
         if family_size < 1:
             raise ValueError("Family size must be at least 1.")
@@ -130,14 +130,11 @@ class MedianIncome(models.Model):
         if family_size <= 8:
             return getattr(self, f"family_size_{family_size}")

-        # For family size > 8, extrapolate
+        # For family size > 8, extrapolate by the table's own extra-person amount
+        if self.family_size_additional is None:
+            raise ValueError("This median income table has no amount for each extra person.")
         additional_people = family_size - 8
-        additional_amount = (
-            self.family_size_additional
-            if self.family_size_additional is not None
-            else Decimal("9900.00")
-        )
-        return self.family_size_8 + (Decimal(additional_people) * additional_amount)
+        return self.family_size_8 + (Decimal(additional_people) * self.family_size_additional)


 class ExemptionSchedule(models.Model):
PATCH
```

```python file=backend/apps/districts/migrations/0003_medianincome_dated_table.py
# Generated by Django 5.0.14 on 2026-10-16 16:38

from datetime import date, timedelta

from django.db import migrations, models


def census_valid_through(effective_date):
    """The day before the next Census update (April 1 or November 1) after effective_date.

    Kept here, not imported, because a migration must keep running the code it shipped with.
    """
    year = effective_date.year
    candidates = [date(year, 4, 1), date(year, 11, 1), date(year + 1, 4, 1)]
    next_update = min(d for d in candidates if d > effective_date)
    return next_update - timedelta(days=1)


def date_existing_rows(apps, schema_editor):
    """Give every stored median row its end date and the U.S. Trustee page it comes from.

    Without an end date, an old row would stay in force forever.
    """
    MedianIncome = apps.get_model("districts", "MedianIncome")
    for row in MedianIncome.objects.all():
        row.valid_through = census_valid_through(row.effective_date)
        row.source_url = (
            "https://www.justice.gov/ust/eo/bapcpa/"
            f"{row.effective_date:%Y%m%d}/bci_data/median_income_table.htm"
        )
        row.save(update_fields=["valid_through", "source_url"])


class Migration(migrations.Migration):

    dependencies = [
        ("districts", "0002_alter_district_state_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="medianincome",
            name="source_url",
            field=models.URLField(
                blank=True, default="", help_text="Where the table is published.", max_length=300
            ),
        ),
        migrations.AddField(
            model_name="medianincome",
            name="valid_through",
            field=models.DateField(
                blank=True,
                help_text=(
                    "Last day before the table's next scheduled change. "
                    "Empty means it stays in force until a newer row replaces it."
                ),
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="medianincome",
            name="effective_date",
            field=models.DateField(help_text="First day this table applies."),
        ),
        migrations.AlterField(
            model_name="medianincome",
            name="family_size_additional",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Amount to add for each additional person above 8.",
                max_digits=12,
            ),
        ),
        migrations.RunPython(date_existing_rows, migrations.RunPython.noop),
    ]
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/districts/fixtures/ilnd_2025_data.json b/backend/apps/districts/fixtures/ilnd_2025_data.json
index f8aea2b..8f5316c 100644
--- a/backend/apps/districts/fixtures/ilnd_2025_data.json
+++ b/backend/apps/districts/fixtures/ilnd_2025_data.json
@@ -19,6 +19,8 @@
     "fields": {
       "district": 1,
       "effective_date": "2025-11-01",
+      "valid_through": "2026-03-31",
+      "source_url": "https://www.justice.gov/ust/eo/bapcpa/20251101/bci_data/median_income_table.htm",
       "family_size_1": "71304.00",
       "family_size_2": "91526.00",
       "family_size_3": "110712.00",
@@ -31,6 +33,26 @@
       "created_at": "2025-01-01T00:00:00Z"
     }
   },
+  {
+    "model": "districts.medianincome",
+    "pk": 2,
+    "fields": {
+      "district": 1,
+      "effective_date": "2026-04-01",
+      "valid_through": "2026-10-31",
+      "source_url": "https://www.justice.gov/ust/eo/bapcpa/20260401/bci_data/median_income_table.htm",
+      "family_size_1": "73180.00",
+      "family_size_2": "93934.00",
+      "family_size_3": "113625.00",
+      "family_size_4": "137902.00",
+      "family_size_5": "149002.00",
+      "family_size_6": "160102.00",
+      "family_size_7": "171202.00",
+      "family_size_8": "182302.00",
+      "family_size_additional": "11100.00",
+      "created_at": "2026-10-16T00:00:00Z"
+    }
+  },
   {
     "model": "districts.exemptionschedule",
     "pk": 1,
PATCH
```

`MedianIncome` inherits `DatedTable`, so it gains `valid_through` and `source_url`, and its extra-person amount always comes from the table. The migration fills both new fields on stored rows from the Census schedule, so production's 2025 row ends on 2026-03-31 instead of staying in force forever (§3.2). The fixture's row 1 gains its end date and page, and row 2 is the April 2026 table (§3.5).

```bash
git apply <<'PATCH'
diff --git a/backend/apps/audit/tests/test_upl_compliance.py b/backend/apps/audit/tests/test_upl_compliance.py
index 1d8a974..123cbb1 100644
--- a/backend/apps/audit/tests/test_upl_compliance.py
+++ b/backend/apps/audit/tests/test_upl_compliance.py
@@ -53,6 +53,7 @@ def _create_median_income(district: District) -> MedianIncome:
         family_size_6=Decimal("143691"),
         family_size_7=Decimal("153691"),
         family_size_8=Decimal("163691"),
+        family_size_additional=Decimal("11100.00"),
     )


diff --git a/backend/apps/forms/tests/test_form_122a1_schema.py b/backend/apps/forms/tests/test_form_122a1_schema.py
index 10f94f6..e64a529 100644
--- a/backend/apps/forms/tests/test_form_122a1_schema.py
+++ b/backend/apps/forms/tests/test_form_122a1_schema.py
@@ -82,6 +82,7 @@ def median_income(session):
         family_size_6=Decimal("156566.00"),
         family_size_7=Decimal("167666.00"),
         family_size_8=Decimal("178766.00"),
+        family_size_additional=Decimal("11100.00"),
     )


diff --git a/backend/apps/intake/tests/test_e2e_intake.py b/backend/apps/intake/tests/test_e2e_intake.py
index 89e65d6..d2ed73f 100644
--- a/backend/apps/intake/tests/test_e2e_intake.py
+++ b/backend/apps/intake/tests/test_e2e_intake.py
@@ -68,6 +68,7 @@ def median_income(district):
         family_size_6=Decimal("143108.00"),
         family_size_7=Decimal("152708.00"),
         family_size_8=Decimal("162308.00"),
+        family_size_additional=Decimal("11100.00"),
     )


diff --git a/backend/apps/intake/tests/test_integration_flow.py b/backend/apps/intake/tests/test_integration_flow.py
index 196729b..5423302 100644
--- a/backend/apps/intake/tests/test_integration_flow.py
+++ b/backend/apps/intake/tests/test_integration_flow.py
@@ -42,6 +42,7 @@ class IntakeFlowIntegrationTest(APITestCase):
             family_size_6=Decimal("125000.00"),
             family_size_7=Decimal("135000.00"),
             family_size_8=Decimal("145000.00"),
+            family_size_additional=Decimal("11100.00"),
         )

     def test_full_intake_flow(self):
PATCH
```

These four tests, and `test_means_test_calculator.py` in Step 1, build their own median row without `family_size_additional`. With the default gone, each `MedianIncome.objects.create` would hit `NOT NULL constraint failed`, so each row now gives the amount. Their own figures are unchanged, and none of them uses a household above 8.

- [ ] **Step 5: Look the table up on the fill date**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/eligibility/models.py b/backend/apps/eligibility/models.py
index d3698e5..ef045cb 100644
--- a/backend/apps/eligibility/models.py
+++ b/backend/apps/eligibility/models.py
@@ -7,8 +7,13 @@ from django.db import models
 from django.utils import timezone
 from encrypted_model_fields.fields import EncryptedTextField

+from apps.districts.dated_tables import fill_date, in_force
+
 from .cmi import current_monthly_income, is_above_median

+# The means test's dated table, by the name its refusals log and calculation_details records.
+MEDIAN_TABLE = "Census median income"
+

 class MeansTest(models.Model):
     """Chapter 7 means test calculation (11 U.S.C. § 707(b))."""
@@ -100,6 +105,7 @@ class MeansTest(models.Model):

         Raises:
             ValueError: If required intake data is missing
+            NoTableInForce: If no median income table is in force on the fill date
         """
         # Get income info from session
         try:
@@ -121,15 +127,16 @@ class MeansTest(models.Model):
             if income_info.marital_status in ["married_joint", "married_separate"]:
                 family_size += 1  # Add spouse

-        # Get median income threshold from district
-        try:
-            median_income_record = self.district.median_incomes.latest("effective_date")
-        except Exception as err:
-            raise ValueError(
-                f"No median income data found for district {self.district.code}"
-            ) from err
+        # The district's median income table in force on the day the forms are filled.
+        # None in force raises NoTableInForce; no older table stands in.
+        median_table = in_force(
+            self.district.median_incomes.all(),
+            fill_date(),
+            MEDIAN_TABLE,
+            self.district.code,
+        )

-        median_income_threshold = median_income_record.get_median_income(family_size)
+        median_income_threshold = median_table.get_median_income(family_size)

         # Determine if passes means test. CMI is monthly; the Census median
         # is annual, so annualize per 11 U.S.C. § 707(b)(7).
@@ -186,6 +193,16 @@ class MeansTest(models.Model):
                 "cmi": float(cmi),
                 "annualized_cmi": float(annualized_cmi),
                 "median_income_threshold": float(median_income_threshold),
+                "median_table": {
+                    "name": MEDIAN_TABLE,
+                    "effective_date": median_table.effective_date.isoformat(),
+                    "valid_through": (
+                        median_table.valid_through.isoformat()
+                        if median_table.valid_through
+                        else None
+                    ),
+                    "source_url": median_table.source_url,
+                },
                 "family_size": family_size,
                 "income_by_source": income_by_source,
                 "marital_status": income_info.marital_status,
diff --git a/backend/apps/eligibility/services/means_test_calculator.py b/backend/apps/eligibility/services/means_test_calculator.py
index b6495d7..cb90144 100644
--- a/backend/apps/eligibility/services/means_test_calculator.py
+++ b/backend/apps/eligibility/services/means_test_calculator.py
@@ -10,6 +10,7 @@ from typing import Any

 from django.db import transaction

+from apps.districts.dated_tables import NoTableInForce
 from apps.eligibility.cmi import IncomeNotSplit, is_above_median
 from apps.eligibility.models import MeansTest
 from apps.intake.models import IntakeSession
@@ -79,10 +80,11 @@ class MeansTestCalculator:
         if not created:
             means_test.district = self.district

-        # Perform calculation. Income not split by source already says what to do.
+        # Perform calculation. Income not split by source and a missing median table already
+        # say what happened in plain words.
         try:
             means_test.calculate()
-        except IncomeNotSplit:
+        except (IncomeNotSplit, NoTableInForce):
             raise
         except ValueError as e:
             raise ValueError(f"Means test calculation failed: {str(e)}") from e
@@ -212,7 +214,8 @@ class MeansTestCalculator:
             "means_test_threshold": {
                 "median_income": float(means_test.median_income_threshold),
                 "district": self.district.code.upper(),
-                "effective_date": details.get("calculated_at"),
+                # The median table's own date; None for a row calculated before tables were dated.
+                "effective_date": details.get("median_table", {}).get("effective_date"),
             },
             "results": {
                 "passes_means_test": means_test.passes_means_test,
PATCH
```

`MeansTest.calculate` replaces `latest()` and its bare `except` with `in_force(..., fill_date(), MEDIAN_TABLE, self.district.code)` and records the table it used in `calculation_details["median_table"]`. The calculator lets `NoTableInForce` through unchanged, and the breakdown dates the median by that table, not by the calculation (§3.4).

- [ ] **Step 6: Refuse in plain words in the forms views and the seed**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/views.py b/backend/apps/forms/views.py
index 391d07f..a3afba6 100644
--- a/backend/apps/forms/views.py
+++ b/backend/apps/forms/views.py
@@ -19,6 +19,7 @@ from rest_framework.permissions import IsAuthenticated
 from rest_framework.response import Response
 from rest_framework.views import APIView

+from apps.districts.dated_tables import NoTableInForce
 from apps.eligibility.cmi import IncomeNotSplit
 from apps.eligibility.services import MeansTestCalculator
 from apps.intake.models import IntakeSession
@@ -52,8 +53,9 @@ class IntakeNotFinished(Exception):


 # Failures a filer can act on: 422 in plain words (spec §5.7). Anything else is a 500.
-# PreconditionMissing and IncomeNotSplit carry their own plain reasons (registry.py,
-# eligibility/cmi.py). Every other class gets a fixed sentence, because their messages
+# PreconditionMissing, IncomeNotSplit and NoTableInForce carry their own plain reasons
+# (registry.py, eligibility/cmi.py, districts/dated_tables.py, which logs its own
+# refusal). Every other class gets a fixed sentence, because their messages
 # name form keys, repeat groups and PDF widgets. None names the form: the dashboard shows
 # its label beside the error.
 _FAILURE_SENTENCES = {
@@ -78,7 +80,7 @@ def _failure(form_type: str | None, exc: Exception) -> tuple[dict, int]:
     form_type is None when the whole call is refused before any form is filled (Generate
     All, the packet list): the body then names no form.
     """
-    if isinstance(exc, PreconditionMissing | IncomeNotSplit):
+    if isinstance(exc, PreconditionMissing | IncomeNotSplit | NoTableInForce):
         error = str(exc)
     else:
         error = _FAILURE_SENTENCES.get(type(exc))
@@ -144,8 +146,8 @@ def _recalculate_means_test(session: IntakeSession) -> None:

     It runs before the packet is decided, so a result worked out from income the filer has
     since changed never decides which forms they get (DIG-160). Raises IncomeNotSplit when
-    the income isn't entered by source, and ValueError when the district's median income
-    data is missing, which operations must fix.
+    the income isn't entered by source, and NoTableInForce when no median income table is in
+    force on the fill date, which operations must fix.
     """
     if getattr(session, "income_info", None) is None:
         # No income at all is income not entered by source, as derivations._cmi rules.
PATCH
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/management/commands/seed_demo_data.py b/backend/apps/intake/management/commands/seed_demo_data.py
index 82dc632..bccb607 100644
--- a/backend/apps/intake/management/commands/seed_demo_data.py
+++ b/backend/apps/intake/management/commands/seed_demo_data.py
@@ -13,7 +13,9 @@ from django.contrib.auth import get_user_model
 from django.core.management.base import BaseCommand
 from django.db import transaction

+from apps.districts.dated_tables import NoTableInForce, fill_date, in_force
 from apps.districts.models import District
+from apps.eligibility.models import MEDIAN_TABLE
 from apps.eligibility.services.means_test_calculator import MeansTestCalculator
 from apps.forms.registry import build_field_values, packet
 from apps.intake.models import (
@@ -166,7 +168,7 @@ def _maria_torres() -> dict:


 def _james_washington() -> dict:
-    """Borderline case — just below single-filer median ($71,304)."""
+    """Borderline case — just below single-filer median ($73,180)."""
     return {
         "username": "demo_james",
         "email": "james.washington@demo.dignifi.org",
@@ -270,7 +272,7 @@ def _priya_sharma() -> dict:
         "income": {
             "marital_status": "married_joint",
             "number_of_dependents": 2,
-            # $12,000/month = $144,000/year — above the $134,366 HH4 median,
+            # $12,000/month = $144,000/year — above the $137,902 HH4 median,
             # so the annualized § 707(b) comparison fails as intended.
             **_wages_only(Decimal("12000.00")),
         },
@@ -535,6 +537,20 @@ class Command(BaseCommand):
             )
             return

+        # Every persona's means test needs a median table in force today; check before
+        # --reset deletes anything, so a refused reseed leaves the existing personas.
+        try:
+            in_force(district.median_incomes.all(), fill_date(), MEDIAN_TABLE, district.code)
+        except NoTableInForce:
+            self.stderr.write(
+                self.style.ERROR(
+                    "No ILND median income table is in force today, so nothing was changed. "
+                    "Add the current table as docs/REFERENCE_TABLES.md describes, then run: "
+                    "python manage.py loaddata ilnd_2025_data"
+                )
+            )
+            return
+
         targets = (
             {options["persona"]: PERSONAS[options["persona"]]} if options["persona"] else PERSONAS
         )
PATCH
```

`_failure` sends `NoTableInForce` through its own sentence as a 422, beside `PreconditionMissing` and `IncomeNotSplit`. The seed checks for a table in force before `--reset` deletes anything (Ruling R1-c), and its two persona comments get the new medians.

- [ ] **Step 7: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=line -rN --continue-on-collection-errors apps/districts apps/eligibility/tests/test_cmi.py apps/eligibility/tests/test_means_test_calculator.py apps/forms/tests/test_form_views.py apps/forms/tests/test_oracle_tier3.py apps/intake/tests/test_seed_demo_data.py -q -p no:cacheprovider 2>&1 | tail -40
```

Expected: `274 passed`, with no failures or errors. The two files that could not be collected add their 26 tests.

- [ ] **Step 8: Write the runbook, the gotchas and the comments**

```markdown file=docs/REFERENCE_TABLES.md
# Reference Tables

- **Operator:** the project owner
- **Last updated:** October 16, 2026

DigniFi reads public tables that change on a schedule. Each row of such a table is stored with the first day it applies (`effective_date`), the last day before its next scheduled change (`valid_through`) and the page it comes from (`source_url`). DigniFi uses the newest row that has started by the day the forms are filled, in Chicago time, which stands in for the filing date. If that row's `valid_through` has passed, or no row has started yet, DigniFi refuses to prepare forms. It never falls back to an older row.

The code lives in `backend/apps/districts/dated_tables.py`. Each table below has its own section. A pull request that loads a new kind of table adds its section here.

---

## Census median income

DigniFi compares each filer's income with this table on Form 122A-1 (line 13), and it uses the table to decide whether Form 122A-2 is in the packet and whether the filer is offered the fee-waiver application.

### Where it is posted

- The U.S. Trustee Program's means-testing page lists every period: https://www.justice.gov/ust/means-testing
- Each table has its own page, named by the first day it applies: `https://www.justice.gov/ust/eo/bapcpa/<YYYYMMDD>/bci_data/median_income_table.htm`
- DigniFi reads the Illinois row, for the Northern District of Illinois.

### When it changes

- New Census figures apply to cases filed on or after **April 1** and **November 1** each year.
- The U.S. Trustee usually posts them a few weeks ahead. The November 2025 table was posted on October 16, 2025, and the April 2026 table on March 18, 2026.
- Some periods on that page change only the IRS figures. The July 15, 2026 period is one: its Illinois median row matches the April 2026 table, so it needs no new row.

### The rows DigniFi loads

| Effective  | `valid_through` | Illinois, 1–4 people                    | Each person over 4 |
| ---------- | --------------- | --------------------------------------- | ------------------ |
| 2025-11-01 | 2026-03-31      | $71,304 / $91,526 / $110,712 / $134,366 | $11,100            |
| 2026-04-01 | 2026-10-31      | $73,180 / $93,934 / $113,625 / $137,902 | $11,100            |

### How to add a row

1. Open the new table's page and copy the Illinois figures for 1 to 4 people. For 5 to 8 people, add the posted amount for each person over 4 ("Add $11,100 for each individual in excess of 4") to the 4-person figure, once per person. Store that amount as `family_size_additional` too.
2. Add a `districts.medianincome` row to `backend/apps/districts/fixtures/ilnd_2025_data.json` with the next `pk`, a `created_at`, and:
   - `effective_date`: the first day the table applies;
   - `valid_through`: the day before the next scheduled change, which is March 31 for a November table and October 31 for an April table;
   - `source_url`: the table's own page.
3. Leave the earlier rows as they are. A test fails if any median row in the fixture has no `valid_through`.
4. Open a pull request to `develop`. Backend tests fill forms on a fixed day, 2026-10-16 (`backend/conftest.py`), so a new row changes no test unless that day moves.
5. After the deploy, load the fixture on production with `python manage.py loaddata ilnd_2025_data` (for example through `heroku run`). Load it on any local database the same way.

### What a missed change looks like

From the day after the last row's `valid_through` until the new row is loaded:

- **Filers** see this sentence: "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your forms. Please try again later." The forms views return it as a 422: Generate All, Generate, Regenerate, the download of an unfiled form, and the packet list of a completed intake. The eligibility check after Complete returns it as a 400, so the filer stays on the Review step.
- **Logs and Sentry** get one error line per refusal, naming only the table, the date and the district: `No Census median income table in force on 2026-11-01 for district ilnd`.
- **`seed_demo_data`** prints a message pointing to this page and changes nothing, even with `--reset`. The E2E journeys fail, in CI too, since they run on the real date.

The fix is to load the new table, as above. If the U.S. Trustee hasn't posted it yet, the refusal is working as designed.
```

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index f3ed4d1..7da3d74 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -25,13 +25,14 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Enum mismatches are silent** — frontend/backend enum drift only surfaces at runtime; check both when adding fields.
 - **Nested debts and assets save by id** — `IntakeSessionSerializer.update` upserts `debts`/`assets` through `_save_rows_by_id`: a row carrying one of this session's ids updates only the keys it sends, a row without one (or with an unknown or foreign id) is created on this session, and a stored row missing from the payload is **deleted**, so send every row you want to keep. A nested `session` is ignored. Fields the browser never receives (`account_number`, `source_document`) survive a re-save. `DebtViewSet`/`AssetViewSet` keep the base serializers, so per-item create never takes a client id. Contracts and codebtors save the same way, as a whole list: `PUT /intake/sessions/{id}/contracts/` (or `codebtors/`) checks every row before writing any, and an empty list deletes every stored row. The wizard sends each list on Continue from steps 6 and 7, and reads both with the session before any step shows, so a list that failed to load is never saved as empty.
 - **Debt and asset amounts are readable, as strings** — the owner gets `DebtInfo.amount_owed` and `AssetInfo.current_value`/`amount_owed` back (SSN and `account_number` stay write-only). DRF sends decimals as strings (`"2500.00"`), so the wizard converts them with `hydrateAmounts` (`utils/parseAmount.ts`) as session data enters step state; a raw string in a step's `reduce` joins as text (`$02500.00100.50`). A stored amount wider than `DecimalField(12, 2)` makes every read of that session 500, so every write path must bound it (`DraftDebtCreator` stores it as 0; documents `validate` returns 400).
-- **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data. Personas seeded before income was stored by source must be re-created with `seed_demo_data --reset` (migration 0014 leaves their totals unsplit, and a plain re-run skips existing users).
+- **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data. It reads the median table in force on today's real date, not the tests' pinned one, and when none is (from November 1, 2026 until the November table is loaded) it prints a message naming `docs/REFERENCE_TABLES.md` and changes nothing, so even `--reset` leaves the existing personas. Personas seeded before income was stored by source must be re-created with `seed_demo_data --reset` (migration 0014 leaves their totals unsplit, and a plain re-run skips existing users).
 - **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
-- **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 > median_income_threshold`, through `is_above_median` (`apps/eligibility/cmi.py`), the means test's own comparison, so income exactly at the median counts as below (DIG-136). Never read `above_median_calculated`: a row calculated before DIG-128 was fixed can still carry a stale True. 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. Generate All, Generate, Regenerate, the download of an unfiled form and the packet list of a completed intake work the means test out again from the stored intake first (`_recalculate_means_test` in `apps/forms/views.py`), so a stale `MeansTest` row never decides the packet (DIG-160); an unfinished intake's packet list reads the stored row. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words, and so is income not entered by source (`IncomeNotSplit`); any other failure, missing district median data included, is a 500 logged by exception type only.
-- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district that has median data, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
+- **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 > median_income_threshold`, through `is_above_median` (`apps/eligibility/cmi.py`), the means test's own comparison, so income exactly at the median counts as below (DIG-136). Never read `above_median_calculated`: a row calculated before DIG-128 was fixed can still carry a stale True. 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. Generate All, Generate, Regenerate, the download of an unfiled form and the packet list of a completed intake work the means test out again from the stored intake first (`_recalculate_means_test` in `apps/forms/views.py`), so a stale `MeansTest` row never decides the packet (DIG-160); an unfinished intake's packet list reads the stored row. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words, and so are income not entered by source (`IncomeNotSplit`) and no median table in force on the fill date (`NoTableInForce`, which logs the table, the date and the district); any other failure is a 500 logged by exception type only.
+- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
-- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type`: Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source (422) or missing median data (500). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types}` in filing order, and the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
+- **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
+- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type`: Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types}` in filing order, and the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
 - **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
 - **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. It has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
PATCH
```

```bash
git apply <<'PATCH'
diff --git a/frontend/e2e/fixtures/personas.ts b/frontend/e2e/fixtures/personas.ts
index bafa84f..d8aa3e5 100644
--- a/frontend/e2e/fixtures/personas.ts
+++ b/frontend/e2e/fixtures/personas.ts
@@ -246,7 +246,7 @@ export const PRIYA: PersonaData = {
   income: {
     marital_status: 'married_joint',
     number_of_dependents: 2,
-    // $12,000/month = $144,000/year — above the $134,366 HH4 median, so the
+    // $12,000/month = $144,000/year — above the $137,902 HH4 median, so the
     // annualized § 707(b) comparison fails as the persona intends.
     total_monthly_income: 12000,
   },
@@ -379,7 +379,7 @@ export const DESHAWN: WaiverPersonaData = {
     },
   ],
   fee_waiver: { take_home_pay: 3050, noncash_assistance: null },
-  // $3,500/month = $42,000/year — below 60% of the HH2 median ($54,915.60),
+  // $3,500/month = $42,000/year — below 60% of the HH2 median ($56,360.40),
   // so DeShawn qualifies for the fee waiver as well as Chapter 7.
   expected: { passes_means_test: true, fee_waiver_eligible: true },
 };
diff --git a/frontend/e2e/journeys/deshawn-assets.spec.ts b/frontend/e2e/journeys/deshawn-assets.spec.ts
index fc164dc..0aec971 100644
--- a/frontend/e2e/journeys/deshawn-assets.spec.ts
+++ b/frontend/e2e/journeys/deshawn-assets.spec.ts
@@ -75,7 +75,7 @@ test.describe('DeShawn Mitchell — Assets', () => {
     await wizard.fillReview();
     await wizard.completeIntake();

-    // $42,000/year is below 60% of the HH2 median ($54,915.60), so DeShawn
+    // $42,000/year is below 60% of the HH2 median ($56,360.40), so DeShawn
     // is fee-waiver eligible and gets routed to the waiver application first.
     await feeWaiver.submit(
       DESHAWN.debtor.household_size,
diff --git a/frontend/e2e/journeys/james-borderline.spec.ts b/frontend/e2e/journeys/james-borderline.spec.ts
index 97b9793..3eb0598 100644
--- a/frontend/e2e/journeys/james-borderline.spec.ts
+++ b/frontend/e2e/journeys/james-borderline.spec.ts
@@ -1,7 +1,7 @@
 /**
  * James Washington — Borderline Case
  *
- * Just below single-filer median ($71,304). Tests near-threshold messaging.
+ * Just below single-filer median ($73,180). Tests near-threshold messaging.
  */

 import { test, expect } from '@playwright/test';
@@ -33,7 +33,7 @@ test.describe('James Washington — Borderline', () => {
     // Uploads come between basic info and Income; this journey types everything in
     await documents.skip();

-    // Step 2: Income (borderline — $5,833/mo × 12 = $69,996 < $71,304 median)
+    // Step 2: Income (borderline — $5,833/mo × 12 = $69,996 < $73,180 median)
     await wizard.fillIncomeInfo(JAMES.income);
     await wizard.nextStep();

diff --git a/frontend/e2e/journeys/priya-ineligible.spec.ts b/frontend/e2e/journeys/priya-ineligible.spec.ts
index 5989596..eccd56c 100644
--- a/frontend/e2e/journeys/priya-ineligible.spec.ts
+++ b/frontend/e2e/journeys/priya-ineligible.spec.ts
@@ -1,7 +1,7 @@
 /**
  * Priya Sharma — Ineligible (Above Median)
  *
- * $144k annual income with 4-person household — above the $134,366
+ * $144k annual income with 4-person household — above the $137,902
  * HH4 median, so the means test fails.
  * Tests the dignity-preserving ineligibility path.
  */
PATCH
```

The runbook says, for the median, where it is posted, when it changes, how to add a row and what a missed change looks like (§3.7). `CLAUDE.md` gains "Dated tables and the fill date". "The packet decides which forms a filer gets" and "GenerateAll vs single" make a missing table a 422 in plain words instead of a 500, "Seed order" says the seed reads the table in force on the real date and changes nothing without one, and "Forms need a completed intake" asks forms view tests for a district with a median table in force on the fill date. The journey comments name the April 2026 figures.

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

Expected: `2114 passed, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  358 passed (358)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 10: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

The journeys run on the real date. Their setup loads `ilnd_2025_data` and runs `seed_demo_data --reset`, which gets past the new table check only while the April 2026 table is in force, through 2026-10-31.

- [ ] **Step 11: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/districts/dated_tables.py \
  backend/apps/districts/migrations/0003_medianincome_dated_table.py \
  backend/apps/districts/tests/__init__.py \
  backend/apps/districts/tests/test_dated_tables.py \
  backend/apps/intake/tests/test_seed_demo_data.py \
  docs/REFERENCE_TABLES.md \
  CLAUDE.md \
  backend/apps/audit/tests/test_upl_compliance.py \
  backend/apps/districts/fixtures/ilnd_2025_data.json \
  backend/apps/districts/models.py \
  backend/apps/eligibility/models.py \
  backend/apps/eligibility/services/means_test_calculator.py \
  backend/apps/eligibility/tests/test_cmi.py \
  backend/apps/eligibility/tests/test_means_test_calculator.py \
  backend/apps/forms/tests/test_form_122a1_schema.py \
  backend/apps/forms/tests/test_form_views.py \
  backend/apps/forms/tests/test_oracle_tier3.py \
  backend/apps/forms/views.py \
  backend/apps/intake/management/commands/seed_demo_data.py \
  backend/apps/intake/tests/test_e2e_intake.py \
  backend/apps/intake/tests/test_integration_flow.py \
  backend/conftest.py \
  frontend/e2e/fixtures/personas.ts \
  frontend/e2e/journeys/deshawn-assets.spec.ts \
  frontend/e2e/journeys/james-borderline.spec.ts \
  frontend/e2e/journeys/priya-ineligible.spec.ts
git commit -F - <<'MSG'
fix(eligibility): use the median table in force on the day the forms are filled

The means test took the newest median row whatever the date, and the
fixture held only the U.S. Trustee table for cases filed from 11/1/2025
to 3/31/2026. Every filer since April 1, 2026 was compared with an
out-of-date median, and a missing table was a 400 from the eligibility
check but a 500 from every forms view (forms step 3a1 spec §3).

- Dated tables: an abstract DatedTable (effective_date, valid_through,
  source_url) in apps/districts/dated_tables.py, with fill_date() (today
  in America/Chicago) and in_force(rows, on, table, district). It takes
  the newest row effective by that day and returns it unless its
  valid_through has passed; when it has, or no row has started yet, it
  logs the table, the date and the district and raises NoTableInForce.
  It never looks at an older row.
- MedianIncome is a DatedTable. Migration 0003 adds valid_through and
  source_url and fills stored rows from the Census schedule (the day
  before the next April 1 or November 1). family_size_additional loses
  its 9,900 default, and get_median_income its fallback: a household
  above 8 uses the table's own amount.
- The fixture gains each row's end date and source, and the April 2026
  table (in force through 2026-10-31). The November 2026 table was not
  posted on 2026-10-16.
- MeansTest.calculate looks the table up on the fill date and records
  it in calculation_details["median_table"]; the breakdown dates the
  median by that table, not by the calculation.
- NoTableInForce reaches the filer in plain words: a 422 from the forms
  views, and the calculator passes it on without its failure prefix, so
  the eligibility check's 400 says the same.
- seed_demo_data checks for a median table in force before --reset
  deletes anything; without one it names docs/REFERENCE_TABLES.md and
  changes nothing.
- The root conftest pins the fill date to 2026-10-16, so CI behaves the
  same every month. Tests of days past the fixture's rows build their
  own rows, so loading a newer table changes no test.
- docs/REFERENCE_TABLES.md is the runbook for adding a table, and the
  CLAUDE.md gotchas say what changed.

Tests the change moved: tier 3's 122A-1 line 13C prints the April 2026
median for all five personas (no other result moved); the forms views'
missing-median test expects the 422 and the logged refusal, not a 500,
and also covers Regenerate; test_cmi's prefix test expects the plain
sentence, and a new one keeps the prefix for any other failure, by
patching MeansTest.calculate. Five tests that build
their own median row now give it the extra-person amount, which no
longer has a default.

Refs DIG-274
MSG
git status --short
```

### Task 2: Name the median table the forms use on the dashboard

_Built and verified as commit `39e4b6f` on `plan/forms-step3a1`._

**Files:**

- Modify: `CLAUDE.md`
- Modify: `backend/apps/forms/tests/test_form_views.py`
- Modify: `backend/apps/forms/views.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/FormDashboard.tsx`
- Modify: `frontend/src/pages/__tests__/FormDashboard.test.tsx`
- Modify: `frontend/src/test/mocks/handlers.ts`
- Modify: `frontend/src/types/api.ts`

**Interfaces:**

- Consumes:
  - Task 1's `MeansTest.calculation_details["median_table"]`: `{"name": "Census median income", "effective_date": "YYYY-MM-DD", "valid_through": "YYYY-MM-DD" or None, "source_url": str}`, read through `MeansTest.get_calculation_details()`, since `calculation_details` is an encrypted JSON string.
  - The `packet` action of `GeneratedFormViewSet` (`backend/apps/forms/views.py`): for a completed intake it runs `_recalculate_means_test` first and sends a refusal through `_failure(None, exc)`; it returns `{session, form_types}`.
  - For the backend tests, in `test_form_views.py`: `TestPacketEndpoint.URL`, the `session_with_debtor` fixture (a completed intake in ILND) and `_stale_means_test(session, cmi)`, which stores a `MeansTest` row with no `calculation_details`.
  - Frontend: `api.forms.packet(sessionId): Promise<FormType[]>` (`frontend/src/api/client.ts`), `FormPacketResponse` (`frontend/src/types/api.ts`), `FormDashboard`'s two calls to it (on load, and again after Generate All), the default MSW packet handler in `frontend/src/test/mocks/handlers.ts`, and the `.form-dashboard-notice` class.
- Produces:
  - `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}`. `tables` is `[median_table]` when the session's `MeansTest` recorded one, and `[]` with no means test or one stored before the record.
  - `_tables_used(session) -> list[dict]` in `backend/apps/forms/views.py`.
  - In `frontend/src/types/api.ts`: `interface DatedTableUsed { name: string; effective_date: string; valid_through: string | null; source_url: string }`, `FormPacketResponse.tables: DatedTableUsed[]` and `interface Packet { form_types: FormType[]; tables: DatedTableUsed[] }`.
  - `api.forms.packet(sessionId): Promise<Packet>`, with `tables` defaulting to `[]`.
  - In `FormDashboard.tsx`: `MONTHS`, `formatIsoDate(iso)`, `tableNotice(table)`, a `tables` state, and one `<p className="form-dashboard-notice">` per table above the form list.
  - Backend tests in `TestPacketEndpoint`: `test_a_completed_intake_names_the_median_table_its_forms_use`, `test_a_filer_with_no_means_test_is_shown_no_table` and `test_a_means_test_stored_before_the_record_names_no_table`.
  - Vitest, in `FormDashboard.test.tsx`'s `describe('the median table notice')`: `tells the filer which figures the forms use and when to download again`, `says only what applies today when no newer figures are expected`, `shows no notice when the forms used no dated table` and `names the day the table starts, not the day before, for a filer west of UTC`.
  - `CLAUDE.md` "GenerateAll vs single": the packet endpoint returns `tables`.

**Decisions already made in this task:**

- **The notice is the spec's text, word for word** (§3.6): "These forms use the median income figures the U.S. Trustee applies to cases filed on or after April 1, 2026. New figures are expected after October 31, 2026. If you file after that date, download your forms again." With no `valid_through`, only the first sentence shows, and with no table there is no notice. It is information, not advice (UPL): an unfiled form fills again on every download, so downloading again picks up a newer table, and a form marked filed keeps its stored answers, as today.
- **"The packet" means the packet endpoint and the dashboard.** A printed notice sheet waits for 3a2's drawing engine (§3.6).
- **`_tables_used` reads the `MeansTest` row again with its own query.** For a completed intake that runs after the recalculation, so it sees the fresh row. For an unfinished intake it reads the stored row, which the packet list never recalculates. It goes through `get_calculation_details()`, because `calculation_details` is an encrypted text field holding a JSON string.
- **Dates are built from the ISO string's parts,** never `new Date(iso)`. That parses as UTC midnight, which is the day before in Chicago. The time-zone test sets `process.env.TZ = 'America/Chicago'` while it runs and restores it after. The reviewer confirmed that the assignment takes effect inside vitest's jsdom worker, so the test fails under `new Date(iso)` whatever the machine's own zone.
- **`api.forms.packet` defaults `tables` to `[]`,** so the per-test MSW handlers that send no `tables` keep working. The default handler sends `tables: []`. The dashboard's two calls are the only callers of `api.forms.packet` in `src` and `e2e`, and both change here.
- **The notice is a plain `<p>` with the existing `.form-dashboard-notice` class:** static information, not an alert or a live region. Its React key is the table's name, which stays unique when a later table shares an effective date.
- **The notice shows whenever `tables` is non-empty,** whatever the loading state. That includes a completed intake whose packet reload failed after Generate All, which the review accepted.
- **This commit includes its review fixes.** The implementer made the packet docstring and the viewset's endpoint list mention `tables`, and keyed the notice on the table's name. The controller then shortened that endpoint-list line in the class docstring to "The packet's form types and its median table".
- **Left as it is:** `get_calculation_details` raises on malformed JSON, which would make the packet list a 500. Nothing writes malformed JSON, so it can't happen today (pre-existing).

- [ ] **Step 1: Write the failing packet tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_form_views.py b/backend/apps/forms/tests/test_form_views.py
index d2bd562..befb81f 100644
--- a/backend/apps/forms/tests/test_form_views.py
+++ b/backend/apps/forms/tests/test_form_views.py
@@ -613,6 +613,43 @@ class TestPacketEndpoint:
         assert "form_103b" not in resp.data["form_types"]
         assert len(resp.data["form_types"]) == 14

+    def test_a_completed_intake_names_the_median_table_its_forms_use(
+        self, api_client, session_with_debtor
+    ):
+        resp = api_client.get(self.URL, {"session": session_with_debtor.id})
+        assert resp.status_code == status.HTTP_200_OK
+        assert resp.data["tables"] == [
+            {
+                "name": "Census median income",
+                "effective_date": "2026-04-01",
+                "valid_through": "2026-10-31",
+                "source_url": (
+                    "https://www.justice.gov/ust/eo/bapcpa/20260401/bci_data/"
+                    "median_income_table.htm"
+                ),
+            }
+        ]
+
+    def test_a_filer_with_no_means_test_is_shown_no_table(self, api_client, session_with_debtor):
+        session = session_with_debtor
+        session.status = "in_progress"
+        session.save()
+        MeansTest.objects.filter(session=session).delete()
+        resp = api_client.get(self.URL, {"session": session.id})
+        assert resp.status_code == status.HTTP_200_OK
+        assert resp.data["tables"] == []
+
+    def test_a_means_test_stored_before_the_record_names_no_table(
+        self, api_client, session_with_debtor
+    ):
+        session = session_with_debtor
+        session.status = "in_progress"
+        session.save()
+        _stale_means_test(session, "3000.00")
+        resp = api_client.get(self.URL, {"session": session.id})
+        assert resp.status_code == status.HTTP_200_OK
+        assert resp.data["tables"] == []
+
     def test_missing_session(self, api_client):
         resp = api_client.get(self.URL)
         assert resp.status_code == status.HTTP_400_BAD_REQUEST
PATCH
```

A completed intake's packet must name the April 2026 table with both dates and its page. An intake with no means test, and one whose stored row predates the record, must get an empty list.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=line apps/forms/tests/test_form_views.py -k TestPacketEndpoint -q -p no:cacheprovider 2>&1 | tail -24
```

Expected: FAIL — `3 failed, 3 passed`, each new test with `KeyError: 'tables'`: the packet body has no tables yet. The three existing packet tests pass.

- [ ] **Step 3: Return the tables the means test used**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/views.py b/backend/apps/forms/views.py
index a3afba6..edb69d8 100644
--- a/backend/apps/forms/views.py
+++ b/backend/apps/forms/views.py
@@ -21,6 +21,7 @@ from rest_framework.views import APIView

 from apps.districts.dated_tables import NoTableInForce
 from apps.eligibility.cmi import IncomeNotSplit
+from apps.eligibility.models import MeansTest
 from apps.eligibility.services import MeansTestCalculator
 from apps.intake.models import IntakeSession

@@ -155,6 +156,16 @@ def _recalculate_means_test(session: IntakeSession) -> None:
     MeansTestCalculator(session).calculate()


+def _tables_used(session: IntakeSession) -> list[dict]:
+    """The dated tables the session's means test used (forms step 3a1 spec §3.6).
+
+    Empty when there is no means test, or a stored one that predates the record.
+    """
+    means_test = MeansTest.objects.filter(session=session).first()
+    table = means_test.get_calculation_details().get("median_table") if means_test else None
+    return [table] if table else []
+
+
 def _prepare(session: IntakeSession) -> None:
     """Refuse an unfinished intake, then work its means test out again. Once per call."""
     _check_finished(session)
@@ -211,7 +222,7 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
     ViewSet for bankruptcy form generation and management.

     Endpoints:
-      GET  /api/forms/packet/?session=<id>  The form types this filer's packet holds
+      GET  /api/forms/packet/?session=<id>  The packet's form types and its median table
       POST /api/forms/generate/              Generate a single form
       POST /api/forms/generate_all/          Generate every form in the packet
       POST /api/forms/{id}/regenerate/       Regenerate an existing form
@@ -243,7 +254,8 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):

         For a completed intake the means test is worked out again first, and a refusal
         covers the whole list. An unfinished intake gets the packet its stored data gives,
-        and is never refused (step 2 spec §5.3, §5.6).
+        and is never refused (step 2 spec §5.3, §5.6). `tables` holds the median table the means
+        test recorded, and is `[]` when there is no means test or it recorded none.
         """
         session, err = _session_or_error(request, request.query_params.get("session"), "session")
         if err:
@@ -254,7 +266,9 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
             except Exception as exc:
                 body, code = _failure(None, exc)
                 return Response(body, status=code)
-        return Response({"session": session.id, "form_types": packet(session)})
+        return Response(
+            {"session": session.id, "form_types": packet(session), "tables": _tables_used(session)}
+        )

     # ------------------------------------------------------------------
     # Generate single form
PATCH
```

`_tables_used` returns the `median_table` the session's means test recorded, as a list, or `[]`. The `packet` action adds it as `tables`, after the recalculation for a completed intake (§3.6). The docstrings name the new key.

- [ ] **Step 4: Run the packet tests again**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=line apps/forms/tests/test_form_views.py -k TestPacketEndpoint -q -p no:cacheprovider 2>&1 | tail -24
```

Expected: `6 passed`.

- [ ] **Step 5: Write the failing dashboard tests**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/FormDashboard.test.tsx b/frontend/src/pages/__tests__/FormDashboard.test.tsx
index ac4fc37..071e6e9 100644
--- a/frontend/src/pages/__tests__/FormDashboard.test.tsx
+++ b/frontend/src/pages/__tests__/FormDashboard.test.tsx
@@ -160,6 +160,71 @@ describe('FormDashboard', () => {
   // Generate All
   // ---------------------------------------------------------------------------

+  describe('the median table notice', () => {
+    const aprilTable = {
+      name: 'Census median income',
+      effective_date: '2026-04-01',
+      valid_through: '2026-10-31',
+      source_url: 'https://www.justice.gov/ust/eo/bapcpa/20260401/bci_data/median_income_table.htm',
+    };
+
+    function packetWith(tables: unknown[]) {
+      server.use(
+        http.get('http://localhost:8000/api/forms/packet/', () =>
+          HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'], tables })
+        )
+      );
+    }
+
+    it('tells the filer which figures the forms use and when to download again', async () => {
+      packetWith([aprilTable]);
+      renderFormDashboard();
+
+      expect(
+        await screen.findByText(
+          'These forms use the median income figures the U.S. Trustee applies to cases filed on or after April 1, 2026. New figures are expected after October 31, 2026. If you file after that date, download your forms again.'
+        )
+      ).toBeInTheDocument();
+    });
+
+    it('says only what applies today when no newer figures are expected', async () => {
+      packetWith([{ ...aprilTable, valid_through: null }]);
+      renderFormDashboard();
+
+      expect(
+        await screen.findByText(
+          'These forms use the median income figures the U.S. Trustee applies to cases filed on or after April 1, 2026.'
+        )
+      ).toBeInTheDocument();
+      expect(screen.queryByText(/New figures are expected/)).not.toBeInTheDocument();
+    });
+
+    it('shows no notice when the forms used no dated table', async () => {
+      packetWith([]);
+      renderFormDashboard();
+
+      await screen.findByText('Form 121 - SSN Statement');
+      expect(screen.queryByText(/median income figures/)).not.toBeInTheDocument();
+    });
+
+    it('names the day the table starts, not the day before, for a filer west of UTC', async () => {
+      // new Date('2026-04-01') is UTC midnight: March 31 in Chicago
+      const savedTz = process.env.TZ;
+      process.env.TZ = 'America/Chicago';
+      try {
+        packetWith([aprilTable]);
+        renderFormDashboard();
+
+        expect(await screen.findByText(/on or after April 1, 2026\./)).toBeInTheDocument();
+        expect(screen.queryByText(/March 31/)).not.toBeInTheDocument();
+        expect(screen.getByText(/after October 31, 2026\./)).toBeInTheDocument();
+      } finally {
+        if (savedTz === undefined) delete process.env.TZ;
+        else process.env.TZ = savedTz;
+      }
+    });
+  });
+
   it('offers only the forms in the filer’s packet', async () => {
     // A stored form that no longer applies (122A-2 after income dropped) is neither shown nor counted
     server.use(
diff --git a/frontend/src/test/mocks/handlers.ts b/frontend/src/test/mocks/handlers.ts
index 9de917a..30279d8 100644
--- a/frontend/src/test/mocks/handlers.ts
+++ b/frontend/src/test/mocks/handlers.ts
@@ -236,7 +236,9 @@ export const handlers = [

   http.get(`${API}/forms/`, () => HttpResponse.json([mockGeneratedForm])),

-  http.get(`${API}/forms/packet/`, () => HttpResponse.json({ session: 1, form_types: mockPacket })),
+  http.get(`${API}/forms/packet/`, () =>
+    HttpResponse.json({ session: 1, form_types: mockPacket, tables: [] })
+  ),

   http.post(`${API}/forms/:id/mark_downloaded/`, () =>
     HttpResponse.json({ message: 'Marked as downloaded.' })
PATCH
```

Each test serves a packet with its own `tables`. The dashboard must show the whole notice for the April 2026 table, only the first sentence when `valid_through` is null, and nothing for an empty list. The last test runs in Chicago time and requires "April 1, 2026", never "March 31". The default MSW packet handler now sends `tables: []`, as the endpoint does.

- [ ] **Step 6: Run them and watch them fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx 2>&1 | tail -25
```

Expected: FAIL — `Tests  3 failed | 22 passed (25)`. The three tests that look for the notice end with `Test timed out in 5000ms`, because the dashboard never renders the text they wait for: the setup's asyncUtilTimeout (5000 ms) equals vitest's test timeout, so the test's own timeout fires first. The test that expects no notice already passes.

- [ ] **Step 7: Show the notice above the form list**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/api/client.ts b/frontend/src/api/client.ts
index 0fbfd2f..fad69de 100644
--- a/frontend/src/api/client.ts
+++ b/frontend/src/api/client.ts
@@ -18,6 +18,7 @@ import type {
   GenerateFormResponse,
   GenerateAllFormsResponse,
   FormPacketResponse,
+  Packet,
   SessionSummaryResponse,
   AssetInfo,
   DebtInfo,
@@ -561,9 +562,9 @@ export const formsAPI = {
    * The form types that apply to this filer, in filing order
    * GET /api/forms/packet/?session={sessionId}
    */
-  packet: async (sessionId: number): Promise<FormType[]> => {
+  packet: async (sessionId: number): Promise<Packet> => {
     const response = await apiFetch<FormPacketResponse>(`/forms/packet/?session=${sessionId}`);
-    return response.form_types;
+    return { form_types: response.form_types, tables: response.tables ?? [] };
   },

   /**
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
index 21bc1bb..a6fe6fd 100644
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -17,7 +17,12 @@ import { UPL_FORM_DISCLAIMER } from '../constants/upl';
 import { DASHBOARD_ERROR, ERROR_GENERIC } from '../constants/copy';
 import { Button } from '../components/common';
 import { PostTaskSurvey } from '../components/survey/PostTaskSurvey';
-import type { GeneratedForm, FormType, GenerateAllFormsResponse } from '../types/api';
+import type {
+  GeneratedForm,
+  FormType,
+  GenerateAllFormsResponse,
+  DatedTableUsed,
+} from '../types/api';
 import { FORM_TYPE_METADATA } from '../types/api';
 import { trackEvent } from '../utils/analytics';

@@ -32,11 +37,43 @@ function wholeCallRefusal(err: unknown, generic: string): string {
   return err instanceof APIClientError && err.statusCode === 422 ? err.message : generic;
 }

+const MONTHS = [
+  'January',
+  'February',
+  'March',
+  'April',
+  'May',
+  'June',
+  'July',
+  'August',
+  'September',
+  'October',
+  'November',
+  'December',
+];
+
+/**
+ * "2026-04-01" as "April 1, 2026", built from the ISO string's parts. Never `new Date(iso)`:
+ * that is UTC midnight, which shows the day before in Chicago.
+ */
+function formatIsoDate(iso: string): string {
+  const [year, month, day] = iso.split('-').map(Number);
+  return `${MONTHS[month - 1]} ${day}, ${year}`;
+}
+
+/** What the forms say about the dated table they were filled from (step 3a1 spec §3.6) */
+function tableNotice(table: DatedTableUsed): string {
+  const first = `These forms use the median income figures the U.S. Trustee applies to cases filed on or after ${formatIsoDate(table.effective_date)}.`;
+  if (!table.valid_through) return first;
+  return `${first} New figures are expected after ${formatIsoDate(table.valid_through)}. If you file after that date, download your forms again.`;
+}
+
 export function FormDashboard() {
   const { session, isLoading: sessionLoading } = useIntake();
   const [forms, setForms] = useState<GeneratedForm[]>([]);
   // The form types that apply to this filer, in filing order
   const [packet, setPacket] = useState<FormType[]>([]);
+  const [tables, setTables] = useState<DatedTableUsed[]>([]);
   const [isLoading, setIsLoading] = useState(true);
   const [error, setError] = useState<string | null>(null);
   const [showSurvey, setShowSurvey] = useState(false);
@@ -50,12 +87,13 @@ export function FormDashboard() {

     setIsLoading(true);
     try {
-      const [loadedForms, packetTypes] = await Promise.all([
+      const [loadedForms, loadedPacket] = await Promise.all([
         api.forms.listBySession(session.id),
         api.forms.packet(session.id),
       ]);
       setForms(loadedForms);
-      setPacket(packetTypes);
+      setPacket(loadedPacket.form_types);
+      setTables(loadedPacket.tables);
       setError(null);
     } catch (err) {
       setError(wholeCallRefusal(err, DASHBOARD_ERROR));
@@ -105,7 +143,9 @@ export function FormDashboard() {
     }
     // Generate All works the means test out again, so the packet may have changed
     try {
-      setPacket(await api.forms.packet(session.id));
+      const reloaded = await api.forms.packet(session.id);
+      setPacket(reloaded.form_types);
+      setTables(reloaded.tables);
       setError(null);
     } catch (err) {
       setError(wholeCallRefusal(err, DASHBOARD_ERROR));
@@ -245,6 +285,12 @@ export function FormDashboard() {
         </>
       )}

+      {tables.map((table) => (
+        <p key={table.name} className="form-dashboard-notice">
+          {tableNotice(table)}
+        </p>
+      ))}
+
       {/* Form cards grid */}
       {isLoading ? (
         <div className="form-dashboard-loading" aria-live="polite">
diff --git a/frontend/src/types/api.ts b/frontend/src/types/api.ts
index 3e1bf7f..d2d0d4d 100644
--- a/frontend/src/types/api.ts
+++ b/frontend/src/types/api.ts
@@ -460,10 +460,27 @@ export interface GenerateAllFormsResponse {
   total_errors: number;
 }

+/** A dated reference table the forms were filled from (forms step 3a1 spec §3.6) */
+export interface DatedTableUsed {
+  name: string;
+  /** ISO date, YYYY-MM-DD */
+  effective_date: string;
+  /** ISO date; null when no newer table is expected */
+  valid_through: string | null;
+  source_url: string;
+}
+
 /** The forms that apply to this filer, in filing order */
 export interface FormPacketResponse {
   session: number;
   form_types: FormType[];
+  tables: DatedTableUsed[];
+}
+
+/** What `api.forms.packet` returns */
+export interface Packet {
+  form_types: FormType[];
+  tables: DatedTableUsed[];
 }

 export interface SessionSummaryResponse {
PATCH
```

`DatedTableUsed` and `Packet` describe the new body, and `api.forms.packet` returns both lists. `FormDashboard` keeps `tables` beside the packet on load and after Generate All, and `tableNotice` writes the spec's sentences with dates that `formatIsoDate` builds from the ISO string's parts.

- [ ] **Step 8: Run the dashboard tests again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx 2>&1 | tail -25
```

Expected: `Tests  25 passed (25)`.

- [ ] **Step 9: Name `tables` in the packet gotcha**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 7da3d74..ad1d717 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -32,7 +32,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
-- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type`: Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types}` in filing order, and the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
+- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type`: Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
 - **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
 - **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. It has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
PATCH
```

- [ ] **Step 10: Run every gate**

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

Expected: `2117 passed, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  362 passed (362)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

The notice is one paragraph on the dashboard and changes no page flow, so the journeys don't run.

- [ ] **Step 11: Commit**

```bash
set -eo pipefail
git add \
  CLAUDE.md \
  backend/apps/forms/tests/test_form_views.py \
  backend/apps/forms/views.py \
  frontend/src/api/client.ts \
  frontend/src/pages/FormDashboard.tsx \
  frontend/src/pages/__tests__/FormDashboard.test.tsx \
  frontend/src/test/mocks/handlers.ts \
  frontend/src/types/api.ts
git commit -F - <<'MSG'
feat(forms): the dashboard names the median table the forms use

The packet endpoint now returns `tables`: the median table the session's
means test recorded in `calculation_details["median_table"]`, or an empty
list when there is no means test or it predates the record. The dashboard
shows, above the form list, which figures the forms use, when new ones are
expected, and that the filer should download again after that date. With no
`valid_through` only the first sentence shows; with no table, no notice.

Dates are built from the ISO string's parts, never `new Date(iso)`, which
shifts a day west of UTC. `api.forms.packet` now returns a `Packet`
(`form_types`, `tables`); its two callers in `FormDashboard` are updated.
The root CLAUDE.md packet gotcha names `tables`.

Spec 3a1 section 3.6.
MSG
git status --short
```

### Task 3: Make Complete name the step that fixes each gap

_Built and verified as commit `a226901` on `plan/forms-step3a1`._

**Files:**

- Modify: `CLAUDE.md`
- Modify: `backend/apps/eligibility/cmi.py`
- Modify: `backend/apps/forms/registry.py`
- Modify: `backend/apps/forms/tests/test_form_views.py`
- Modify: `backend/apps/forms/tests/test_registry.py`
- Modify: `backend/apps/forms/views.py`
- Modify: `backend/apps/intake/tests/test_completion.py`
- Modify: `backend/apps/intake/tests/test_e2e_intake.py`
- Modify: `backend/apps/intake/tests/test_income_resume.py`
- Modify: `backend/apps/intake/views.py`

**Interfaces:**

- Consumes:
  - In `backend/apps/forms/registry.py`: `PreconditionMissing(Exception)`; `_needs_debtor_info` ("Your name and address haven't been entered yet." when the session has no `DebtorInfo`); `_needs_ssn`, which calls `_needs_debtor_info` first and then requires `_SSN` to match the SSN ("Your Social Security number is missing or isn't 9 digits."); `_needs_means_test` ("The eligibility check hasn't been run yet.").
  - `IncomeNotSplit` ("Enter your income by source on the Income step.") and `current_monthly_income(income_info)`, which raises it when all ten income amounts are empty, in `backend/apps/eligibility/cmi.py`.
  - `IntakeNotFinished` and Task 1's `_failure(form_type, exc)` in `backend/apps/forms/views.py`, which builds every forms refusal body: `{"error"}` for a whole-call refusal, `{"form_type", "error"}` otherwise.
  - `IntakeSessionViewSet.complete` (`backend/apps/intake/views.py`), which refuses with a 400 `{"errors": [<string>, ...], "message": "Please complete all required sections before finalizing"}` when the debtor, income or expense row is missing.
  - The wizard's step keys (`WIZARD_STEPS` in `frontend/src/pages/IntakeWizard.tsx`): `debtor_info`, `income_info`, `expense_info`, `review`.
  - For the tests, in `test_completion.py`: the `district`, `filer` (an API client and its user) and `completed` (a completed intake with a 900-range SSN, income by source and an `ExpenseInfo`) fixtures, `_session_url` and `_status`.
- Produces:
  - `PreconditionMissing(message, step=None)`, with `.step`: a `WIZARD_STEPS` key or `None`.
  - The registry's sentences and steps: `_needs_debtor_info` → "Enter your name and address on the Your Information step." (`debtor_info`); `_needs_ssn` → "Enter your 9-digit Social Security number on the Your Information step." (`debtor_info`); `_needs_means_test` → "Press Complete on the Review & Results step to run the eligibility check." (`review`).
  - `IncomeNotSplit.step = "income_info"` and `IntakeNotFinished.page = "/intake"`, both class attributes.
  - `_failure` adds `"step"` and `"page"` to a 422 body when the exception carries a truthy one. A 500 body never has them.
  - Complete's refusal: a 400 `{"errors": [{"step": str, "message": str}, ...], "message": "Please complete all required sections before finalizing"}`, one entry per gap, in this order: identity (`_needs_ssn`, one entry), income by source, the Expenses step. Task 4's wizard reads it, and Task 5 appends its drafts entry after the Expenses entry.
  - Tests: `test_complete_names_the_step_that_fixes_each_gap` (cases `no_name_and_address`, `eight_digit_ssn`, `no_income_by_source`, `no_expenses_step`) and `test_complete_lists_every_gap_in_wizard_order` in `test_completion.py`; `TestGenerateEndpoint::test_unexpected_failure_points_the_filer_to_no_step_or_page` in `test_form_views.py`.
  - `CLAUDE.md`: "Forms need a completed intake" says what Complete refuses, its 400 body, and which forms refusals carry a `step` or `page`; "GenerateAll vs single" notes that a whole-call refusal carries them too.

**Decisions already made in this task:**

- **The sentences are the spec's, word for word** (§4.2): "Enter your name and address on the Your Information step.", "Enter your 9-digit Social Security number on the Your Information step.", "Enter your income by source on the Income step." and "Go through the Expenses step, even if you have no expenses to enter." The means-test precondition reads "Press Complete on the Review & Results step to run the eligibility check." Every sentence a filer reads stays information, never advice.
- **One source of truth (§4.2).** Complete calls the registry's own `_needs_ssn`, which checks the debtor row first, so Complete and Forms 101 and 121 say the same thing. Importing the private `_needs_ssn` from `apps.forms.registry` into `apps.intake.views` is what the spec directs. Forms 101 and 121 keep the same checks in their own `requires()`, which protects sessions completed before 3a1.
- **Identity is one entry,** whichever check fires first. `_needs_debtor_info` checks only that a `DebtorInfo` row exists, not that its name and address fields are filled; the gotcha says so, and the filer-facing sentence is the spec's.
- **No income row counts as income not entered by source,** as `derivations._cmi` already rules, so it gets the same sentence. Complete catches only `IncomeNotSplit` from `current_monthly_income`.
- **The 400 keeps its old key order,** `errors` then `message`. JSON order doesn't matter, and it keeps the diff small.
- **`step` and `page` go on 422 bodies only.** Today no exception in the pipeline, pypdf's included, has such an attribute. But on a 500 one would send the filer to a step that can't fix a fault, and a value that isn't JSON would break the error response itself. `test_unexpected_failure_points_the_filer_to_no_step_or_page` pins the rule. It already passes before this change, since the old `_failure` adds neither key, so it is no red; the implementer proved it by mutation instead.
- **Which refusals carry a key (§4.3).** `IntakeNotFinished` carries `page: "/intake"`, and `IncomeNotSplit` and the registry's checks carry their step. "Already filed", "not in your packet" and `NoTableInForce` carry neither, because no step of the filer's fixes them. A key is absent, never null. The unchanged exact-body tests for `NO_MEDIAN_TABLE`, `NotInPacket` and a filed form prove that.
- **The registry tests now assert each exact sentence and step.** They matched substrings before, which still matched the new sentences and would miss drift. They are the only test of `_needs_means_test`'s sentence, because the forms views recalculate the means test before any of them could reach that check.
- **Three Complete tests in `test_e2e_intake.py` move to the 900 range.** Complete now judges the SSN, and test SSNs must be synthetic, so `test_complete_session_success`, `test_complete_session_missing_income_info` and `test_complete_session_missing_expense_info` store `"900123456"`. The missing-debtor test stores no SSN. The same file's other `"123456789"` SSNs, in tests that never call Complete, are pre-existing and stay.
- **The journeys still pass Complete.** Their personas type a 900-range SSN, enter their wages by source and save the Expenses step, so none of the new checks refuses them.
- **`CLAUDE.md` changes two gotchas.** "Forms need a completed intake" is the task's. "GenerateAll vs single" said a whole-call refusal is `{error}`, which is no longer the whole body, so it gains one parenthesis. The commit was amended after its gates only to make the first gotcha say "the fields themselves aren't checked".
- **Left for later tasks:** Task 4 updates `frontend/src/pages/__tests__/IntakeWizard.test.tsx`'s Complete mock, which still sends `errors` as strings and passes because the wizard reads only `message`. Task 5 adds the unconfirmed-debts entry. `test_form_views.py`'s blank lines after three class lines (not `ruff format`-clean; CI runs `ruff check`) are pre-existing and stay.

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/tests/test_completion.py b/backend/apps/intake/tests/test_completion.py
index b69add4..3f74a68 100644
--- a/backend/apps/intake/tests/test_completion.py
+++ b/backend/apps/intake/tests/test_completion.py
@@ -166,6 +166,75 @@ def test_filer_who_leaves_every_expense_blank_can_complete(filer, district):
     assert _status(session) == "completed"


+# ── Complete names the step that fixes each gap (forms step 3a1 spec §4.2) ──
+
+NOT_FINISHED = "Please complete all required sections before finalizing"
+NAME_AND_ADDRESS = "Enter your name and address on the Your Information step."
+NINE_DIGIT_SSN = "Enter your 9-digit Social Security number on the Your Information step."
+INCOME_BY_SOURCE = "Enter your income by source on the Income step."
+EXPENSES_STEP = "Go through the Expenses step, even if you have no expenses to enter."
+
+
+def _no_debtor(session):
+    session.debtor_info.delete()
+
+
+def _eight_digit_ssn(session):
+    session.debtor_info.ssn = "90012345"
+    session.debtor_info.save()
+
+
+def _income_boxes_all_empty(session):
+    session.income_info.monthly_gross_wages = None
+    session.income_info.save()
+
+
+def _expenses_step_never_saved(session):
+    session.expense_info.delete()
+
+
+@pytest.mark.parametrize(
+    "gap,step,message",
+    [
+        (_no_debtor, "debtor_info", NAME_AND_ADDRESS),
+        (_eight_digit_ssn, "debtor_info", NINE_DIGIT_SSN),
+        (_income_boxes_all_empty, "income_info", INCOME_BY_SOURCE),
+        (_expenses_step_never_saved, "expense_info", EXPENSES_STEP),
+    ],
+    ids=["no_name_and_address", "eight_digit_ssn", "no_income_by_source", "no_expenses_step"],
+)
+def test_complete_names_the_step_that_fixes_each_gap(filer, completed, gap, step, message):
+    # The filer reads why on Review, with a way to the step that fixes it (DIG-181).
+    client, _ = filer
+    completed.status = "in_progress"
+    completed.save()
+    gap(completed)
+
+    response = client.post(_session_url(completed, "complete/"))
+
+    assert response.status_code == 400
+    assert response.data == {
+        "message": NOT_FINISHED,
+        "errors": [{"step": step, "message": message}],
+    }
+    assert _status(completed) == "in_progress"
+
+
+def test_complete_lists_every_gap_in_wizard_order(filer, district):
+    client, user = filer
+    session = IntakeSession.objects.create(user=user, district=district, current_step=8)
+
+    response = client.post(_session_url(session, "complete/"))
+
+    assert response.status_code == 400
+    assert response.data["errors"] == [
+        {"step": "debtor_info", "message": NAME_AND_ADDRESS},
+        {"step": "income_info", "message": INCOME_BY_SOURCE},
+        {"step": "expense_info", "message": EXPENSES_STEP},
+    ]
+    assert _status(session) == "started"
+
+
 # ── An edit after Complete reopens the intake ─────────────────────────


PATCH
```

Each case takes a completed intake back to `in_progress`, opens one gap and presses Complete: it must get exactly one `{step, message}` and stay `in_progress`. An empty intake must get all three entries in wizard order.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_registry.py b/backend/apps/forms/tests/test_registry.py
index 2f26022..1702c26 100644
--- a/backend/apps/forms/tests/test_registry.py
+++ b/backend/apps/forms/tests/test_registry.py
@@ -163,15 +163,24 @@ def test_122a1_supplement_waits_for_its_questions(session):


 def test_petition_needs_the_filers_name_and_address(session):
-    with pytest.raises(PreconditionMissing, match="name and address"):
+    with pytest.raises(PreconditionMissing) as refused:
         build_field_values("form_101", session)
+    # The sentence and the step that fixes it, as Complete shows them (3a1 spec §4.2).
+    assert (str(refused.value), refused.value.step) == (
+        "Enter your name and address on the Your Information step.",
+        "debtor_info",
+    )


 @pytest.mark.parametrize("ssn", ["", "1234", "900-55-000"])
 def test_ssn_statement_needs_a_nine_digit_ssn(session, ssn):
     _debtor(session, ssn=ssn)
-    with pytest.raises(PreconditionMissing, match="Social Security number"):
+    with pytest.raises(PreconditionMissing) as refused:
         build_field_values("form_121", session)
+    assert (str(refused.value), refused.value.step) == (
+        "Enter your 9-digit Social Security number on the Your Information step.",
+        "debtor_info",
+    )


 @pytest.mark.parametrize("ssn", ["900-55-0005", "900550005"])
@@ -188,8 +197,12 @@ def test_ssn_statement_without_a_debtor_fails_instead_of_ticking_no_ssn(session)

 def test_means_test_form_needs_the_eligibility_check(session):
     _debtor(session)
-    with pytest.raises(PreconditionMissing, match="eligibility check"):
+    with pytest.raises(PreconditionMissing) as refused:
         build_field_values("form_122a1", session)
+    assert (str(refused.value), refused.value.step) == (
+        "Press Complete on the Review & Results step to run the eligibility check.",
+        "review",
+    )


 def test_field_values_name_index_widgets(session):
diff --git a/backend/apps/intake/tests/test_e2e_intake.py b/backend/apps/intake/tests/test_e2e_intake.py
index d2ed73f..012abb2 100644
--- a/backend/apps/intake/tests/test_e2e_intake.py
+++ b/backend/apps/intake/tests/test_e2e_intake.py
@@ -384,7 +384,7 @@ class TestIntakeSessionCompletion:
             session=session,
             first_name="John",
             last_name="Doe",
-            ssn="123456789",
+            ssn="900123456",  # IRS-reserved range: synthetic
             date_of_birth="1980-01-01",
             street_address="123 Main St",
             city="Chicago",
@@ -453,8 +453,12 @@ class TestIntakeSessionCompletion:
         response = api_client.post(url)

         assert response.status_code == status.HTTP_400_BAD_REQUEST
-        assert "errors" in response.data
-        assert "Debtor information is required" in response.data["errors"]
+        assert response.data["errors"] == [
+            {
+                "step": "debtor_info",
+                "message": "Enter your name and address on the Your Information step.",
+            }
+        ]

     def test_complete_session_missing_income_info(self, api_client, session):
         """Test completing session without income info returns 400."""
@@ -463,7 +467,7 @@ class TestIntakeSessionCompletion:
             session=session,
             first_name="John",
             last_name="Doe",
-            ssn="123456789",
+            ssn="900123456",  # IRS-reserved range: synthetic
             date_of_birth="1980-01-01",
             street_address="123 Main St",
             city="Chicago",
@@ -490,8 +494,9 @@ class TestIntakeSessionCompletion:
         response = api_client.post(url)

         assert response.status_code == status.HTTP_400_BAD_REQUEST
-        assert "errors" in response.data
-        assert "Income information is required" in response.data["errors"]
+        assert response.data["errors"] == [
+            {"step": "income_info", "message": "Enter your income by source on the Income step."}
+        ]

     def test_complete_session_missing_expense_info(self, api_client, session):
         """Test completing session without expense info returns 400."""
@@ -500,7 +505,7 @@ class TestIntakeSessionCompletion:
             session=session,
             first_name="John",
             last_name="Doe",
-            ssn="123456789",
+            ssn="900123456",  # IRS-reserved range: synthetic
             date_of_birth="1980-01-01",
             street_address="123 Main St",
             city="Chicago",
@@ -519,8 +524,12 @@ class TestIntakeSessionCompletion:
         response = api_client.post(url)

         assert response.status_code == status.HTTP_400_BAD_REQUEST
-        assert "errors" in response.data
-        assert "Expense information is required" in response.data["errors"]
+        assert response.data["errors"] == [
+            {
+                "step": "expense_info",
+                "message": "Go through the Expenses step, even if you have no expenses to enter.",
+            }
+        ]


 @pytest.mark.django_db
PATCH
```

The three missing-row Complete tests assert the exact `errors` list, and the registry tests the exact sentence and `.step` of each precondition.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_form_views.py b/backend/apps/forms/tests/test_form_views.py
index befb81f..bfa22bf 100644
--- a/backend/apps/forms/tests/test_form_views.py
+++ b/backend/apps/forms/tests/test_form_views.py
@@ -351,6 +351,24 @@ class TestGenerateEndpoint:
         assert type(exc).__name__ in caplog.text
         assert "Debtor1.SSNum" not in caplog.text

+    def test_unexpected_failure_points_the_filer_to_no_step_or_page(
+        self, api_client, session_with_debtor
+    ):
+        # Only a refusal names where the filer fixes it; nothing they enter fixes a fault.
+        fault = RuntimeError("page 3 could not be written")
+        fault.step, fault.page = "debtor_info", 3
+        with patch.object(PDFFormFiller, "fill", side_effect=fault):
+            resp = api_client.post(
+                self.URL,
+                {"session_id": session_with_debtor.id, "form_type": "form_101"},
+                format="json",
+            )
+        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
+        assert resp.data == {
+            "form_type": "form_101",
+            "error": "This form couldn't be prepared. Please try again later.",
+        }
+
     def test_filed_form_keeps_what_was_filed(self, api_client, session_with_debtor, user):
         form = _filed_form(session_with_debtor, user, "form_101", {"Debtor1.First name": "Jane"})
         _rename_filer(session_with_debtor, "Janet")
@@ -388,11 +406,13 @@ class TestGenerateAllEndpoint:
             format="json",
         )
         assert resp.status_code == status.HTTP_200_OK
-        # No fee waiver: no 103B. Income below the median: no 122A-2. Form 121 needs the SSN.
+        # No fee waiver: no 103B. Income below the median: no 122A-2. Form 121 needs the SSN,
+        # which the filer enters on the step the error names.
         assert resp.data["errors"] == [
             {
                 "form_type": "form_121",
-                "error": "Your Social Security number is missing or isn't 9 digits.",
+                "error": "Enter your 9-digit Social Security number on the Your Information step.",
+                "step": "debtor_info",
             }
         ]
         assert resp.data["total_generated"] == 13
@@ -690,16 +710,16 @@ class TestCompletionCheck:
         regenerate = api_client.post(f"/api/forms/{unfiled.id}/regenerate/")
         download = api_client.get(f"/api/forms/{unfiled.id}/download/")

-        # One refusal for the whole packet, not one per form.
+        # One refusal for the whole packet, not one per form, with the page that fixes it.
         assert generate_all.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
-        assert generate_all.data == {"error": FINISH}
+        assert generate_all.data == {"error": FINISH, "page": "/intake"}
         for resp, form_type in [
             (generate, "form_106dec"),
             (regenerate, "form_101"),
             (download, "form_101"),
         ]:
             assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
-            assert resp.data == {"form_type": form_type, "error": FINISH}
+            assert resp.data == {"form_type": form_type, "error": FINISH, "page": "/intake"}
         # Generate All refused before it dropped the form that left the packet.
         assert set(
             GeneratedForm.objects.filter(session=session).values_list("form_type", flat=True)
@@ -842,13 +862,18 @@ class TestMeansTestWorkedOutAgain:
         download = api_client.get(f"/api/forms/{unfiled.id}/download/")
         filed_download = api_client.get(f"/api/forms/{filed.id}/download/")

-        # One refusal covers the whole call, the packet list included.
+        # One refusal covers the whole call, the packet list included, with the step that
+        # fixes it.
         for resp in (generate_all, listed):
             assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
-            assert resp.data == {"error": SPLIT_BY_SOURCE}
+            assert resp.data == {"error": SPLIT_BY_SOURCE, "step": "income_info"}
         for resp in (generate, regenerate, download):
             assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
-            assert resp.data == {"form_type": "form_106dec", "error": SPLIT_BY_SOURCE}
+            assert resp.data == {
+                "form_type": "form_106dec",
+                "error": SPLIT_BY_SOURCE,
+                "step": "income_info",
+            }
         # Generate All refused before it dropped the form that left the packet.
         assert set(
             GeneratedForm.objects.filter(session=session).values_list("form_type", flat=True)
@@ -876,9 +901,13 @@ class TestMeansTestWorkedOutAgain:

         for resp in (generate_all, listed):
             assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
-            assert resp.data == {"error": SPLIT_BY_SOURCE}
+            assert resp.data == {"error": SPLIT_BY_SOURCE, "step": "income_info"}
         assert generate.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
-        assert generate.data == {"form_type": "form_106dec", "error": SPLIT_BY_SOURCE}
+        assert generate.data == {
+            "form_type": "form_106dec",
+            "error": SPLIT_BY_SOURCE,
+            "step": "income_info",
+        }

     def test_no_median_table_in_force_is_refused_in_plain_words_and_logged_without_filer_data(
         self, api_client, session_with_debtor, user, caplog
diff --git a/backend/apps/intake/tests/test_income_resume.py b/backend/apps/intake/tests/test_income_resume.py
index b2a2fc9..171147f 100644
--- a/backend/apps/intake/tests/test_income_resume.py
+++ b/backend/apps/intake/tests/test_income_resume.py
@@ -222,11 +222,15 @@ def test_legacy_income_total_must_be_split_before_forms_print(filer_session):

     refused = client.post("/api/forms/generate/", generate, format="json")
     assert refused.status_code == 422
-    assert refused.data == {"form_type": "schedule_i", "error": SPLIT_BY_SOURCE}
+    assert refused.data == {
+        "form_type": "schedule_i",
+        "error": SPLIT_BY_SOURCE,
+        "step": "income_info",
+    }
     # Every form waits for the split, since each call works the means test out first.
     every_form = client.post("/api/forms/generate_all/", {"session_id": session.pk}, format="json")
     assert every_form.status_code == 422
-    assert every_form.data == {"error": SPLIT_BY_SOURCE}
+    assert every_form.data == {"error": SPLIT_BY_SOURCE, "step": "income_info"}

     # The filer splits the total on the Income step and completes the intake again.
     split = client.patch(
PATCH
```

The refusal bodies gain their key: `"step": "debtor_info"` on Form 121's entry in Generate All's `errors`, `"page": "/intake"` on an unfinished intake's four refusals, and `"step": "income_info"` wherever income isn't entered by source. The new 500 test raises a `RuntimeError` carrying `step` and `page` from `PDFFormFiller.fill` and requires a body with neither.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=line -rN apps/intake/tests/test_completion.py apps/intake/tests/test_e2e_intake.py apps/intake/tests/test_income_resume.py apps/forms/tests/test_registry.py apps/forms/tests/test_form_views.py -q -p no:cacheprovider 2>&1 | tail -30
```

Expected: FAIL — `18 failed, 133 passed`. Complete still answers with bare strings, such as "Debtor information is required", where the tests want one step and message per gap, and it completes an intake with an 8-digit SSN or with every income amount empty (`assert 200 == 400`). The registry tests fail on `AttributeError: 'PreconditionMissing' object has no attribute 'step'`, and the forms refusal bodies have no step or page. The new 500 test already passes.

- [ ] **Step 3: Give each refusal the step or page that fixes it**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/eligibility/cmi.py b/backend/apps/eligibility/cmi.py
index e2c2f71..c97844f 100644
--- a/backend/apps/eligibility/cmi.py
+++ b/backend/apps/eligibility/cmi.py
@@ -17,6 +17,8 @@ class IncomeNotSplit(ValueError):
     A total saved before income was stored by source can't be split by anyone but the filer.
     """

+    step = "income_info"  # the wizard step where the filer enters it
+
     def __init__(self) -> None:
         super().__init__("Enter your income by source on the Income step.")

diff --git a/backend/apps/forms/registry.py b/backend/apps/forms/registry.py
index ac6c697..8077e7a 100644
--- a/backend/apps/forms/registry.py
+++ b/backend/apps/forms/registry.py
@@ -21,7 +21,14 @@ _SSN = re.compile(r"\d{3}-\d{2}-\d{4}|\d{9}")


 class PreconditionMissing(Exception):
-    """A form can't be filled yet; the message tells the filer what is missing."""
+    """A form can't be filled yet; the message tells the filer what is missing.
+
+    step is the wizard step (a WIZARD_STEPS key) where the filer fixes it, or None.
+    """
+
+    def __init__(self, message: str, step: str | None = None) -> None:
+        super().__init__(message)
+        self.step = step


 @dataclass(frozen=True)
@@ -62,18 +69,26 @@ def _nothing(session: IntakeSession) -> None:

 def _needs_debtor_info(session: IntakeSession) -> None:
     if not hasattr(session, "debtor_info"):
-        raise PreconditionMissing("Your name and address haven't been entered yet.")
+        raise PreconditionMissing(
+            "Enter your name and address on the Your Information step.", step="debtor_info"
+        )


 def _needs_ssn(session: IntakeSession) -> None:
     _needs_debtor_info(session)
     if not _SSN.fullmatch((session.debtor_info.ssn or "").strip()):
-        raise PreconditionMissing("Your Social Security number is missing or isn't 9 digits.")
+        raise PreconditionMissing(
+            "Enter your 9-digit Social Security number on the Your Information step.",
+            step="debtor_info",
+        )


 def _needs_means_test(session: IntakeSession) -> None:
     if not hasattr(session, "means_test"):
-        raise PreconditionMissing("The eligibility check hasn't been run yet.")
+        raise PreconditionMissing(
+            "Press Complete on the Review & Results step to run the eligibility check.",
+            step="review",
+        )


 # form_type → PacketForm. Every key must match a GeneratedForm.FORM_TYPE_CHOICES value.
PATCH
```

`PreconditionMissing` takes an optional `step`, and the three registry checks raise the spec's sentences with theirs. `IncomeNotSplit` names `income_info` as a class attribute; its message is unchanged.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/views.py b/backend/apps/forms/views.py
index edb69d8..09727ec 100644
--- a/backend/apps/forms/views.py
+++ b/backend/apps/forms/views.py
@@ -52,6 +52,8 @@ class FormIsFiled(Exception):
 class IntakeNotFinished(Exception):
     """The filer hasn't completed the intake, so an empty list can't yet mean "none"."""

+    page = "/intake"  # where the filer finishes it
+

 # Failures a filer can act on: 422 in plain words (spec §5.7). Anything else is a 500.
 # PreconditionMissing, IncomeNotSplit and NoTableInForce carry their own plain reasons
@@ -79,7 +81,8 @@ def _failure(form_type: str | None, exc: Exception) -> tuple[dict, int]:
     """The error body and status for a form that could not be filled.

     form_type is None when the whole call is refused before any form is filled (Generate
-    All, the packet list): the body then names no form.
+    All, the packet list): the body then names no form. A refusal the filer fixes on a
+    wizard step or a page also carries that `step` or `page` (forms step 3a1 spec §4.3).
     """
     if isinstance(exc, PreconditionMissing | IncomeNotSplit | NoTableInForce):
         error = str(exc)
@@ -91,9 +94,13 @@ def _failure(form_type: str | None, exc: Exception) -> tuple[dict, int]:
         logger.error("Filling %s failed: %s", form_type or "the packet", type(exc).__name__)
         error = "This form couldn't be prepared. Please try again later."
         code = status.HTTP_500_INTERNAL_SERVER_ERROR
-    if form_type is None:
-        return {"error": error}, code
-    return {"form_type": form_type, "error": error}, code
+    body = {"error": error} if form_type is None else {"form_type": form_type, "error": error}
+    if code == status.HTTP_422_UNPROCESSABLE_ENTITY:
+        # Only a refusal: an unexpected exception's own step or page attribute means nothing here.
+        for key in ("step", "page"):
+            if getattr(exc, key, None):
+                body[key] = getattr(exc, key)
+    return body, code


 def _session_or_error(
PATCH
```

`IntakeNotFinished` names `/intake`. `_failure` builds the body as before, then copies a truthy `step` or `page` from the exception onto a 422 body (§4.3).

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/views.py b/backend/apps/intake/views.py
index 7214096..0d833e8 100644
--- a/backend/apps/intake/views.py
+++ b/backend/apps/intake/views.py
@@ -11,7 +11,9 @@ from rest_framework.decorators import action
 from rest_framework.permissions import IsAuthenticated
 from rest_framework.response import Response

+from apps.eligibility.cmi import IncomeNotSplit, current_monthly_income
 from apps.eligibility.services import MeansTestCalculator
+from apps.forms.registry import PreconditionMissing, _needs_ssn

 from .models import (
     AssetInfo,
@@ -183,21 +185,35 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):

         POST /api/intake/sessions/{id}/complete/

-        Validates that all required data is present before completion.
+        Refuses with a 400 naming, in wizard order, the step that fixes each gap
+        (forms step 3a1 spec §4.2).
         """
         session = self.get_object()

         # Validate session is complete
         errors = []

-        if not hasattr(session, "debtor_info"):
-            errors.append("Debtor information is required")
+        # The forms' own identity checks, so Complete and the forms say the same thing.
+        try:
+            _needs_ssn(session)  # checks the name and address first
+        except PreconditionMissing as exc:
+            errors.append({"step": exc.step, "message": str(exc)})

-        if not hasattr(session, "income_info"):
-            errors.append("Income information is required")
+        try:
+            income_info = getattr(session, "income_info", None)
+            if income_info is None:
+                raise IncomeNotSplit()  # no income at all is income not entered by source
+            current_monthly_income(income_info)
+        except IncomeNotSplit as exc:
+            errors.append({"step": exc.step, "message": str(exc)})

         if not hasattr(session, "expense_info"):
-            errors.append("Expense information is required")
+            errors.append(
+                {
+                    "step": "expense_info",
+                    "message": "Go through the Expenses step, even if you have no expenses to enter.",
+                }
+            )

         if errors:
             return Response(
PATCH
```

Complete collects one `{step, message}` per gap, in wizard order: identity through `_needs_ssn`, income through `current_monthly_income`, then a missing `ExpenseInfo` row (§4.2).

- [ ] **Step 4: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=line -rN apps/intake/tests/test_completion.py apps/intake/tests/test_e2e_intake.py apps/intake/tests/test_income_resume.py apps/forms/tests/test_registry.py apps/forms/tests/test_form_views.py -q -p no:cacheprovider 2>&1 | tail -30
```

Expected: `151 passed`.

- [ ] **Step 5: Say what Complete refuses in CLAUDE.md**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index ad1d717..13748c1 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -28,11 +28,11 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data. It reads the median table in force on today's real date, not the tests' pinned one, and when none is (from November 1, 2026 until the November table is loaded) it prints a message naming `docs/REFERENCE_TABLES.md` and changes nothing, so even `--reset` leaves the existing personas. Personas seeded before income was stored by source must be re-created with `seed_demo_data --reset` (migration 0014 leaves their totals unsplit, and a plain re-run skips existing users).
 - **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
 - **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 > median_income_threshold`, through `is_above_median` (`apps/eligibility/cmi.py`), the means test's own comparison, so income exactly at the median counts as below (DIG-136). Never read `above_median_calculated`: a row calculated before DIG-128 was fixed can still carry a stale True. 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. Generate All, Generate, Regenerate, the download of an unfiled form and the packet list of a completed intake work the means test out again from the stored intake first (`_recalculate_means_test` in `apps/forms/views.py`), so a stale `MeansTest` row never decides the packet (DIG-160); an unfinished intake's packet list reads the stored row. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words, and so are income not entered by source (`IncomeNotSplit`) and no median table in force on the fill date (`NoTableInForce`, which logs the table, the date and the district); any other failure is a 500 logged by exception type only.
-- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
+- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key: no `DebtorInfo` row (the name-and-address sentence; the fields themselves aren't checked) or an SSN that isn't 9 digits (the registry's own `_needs_ssn`, so Complete and Forms 101 and 121 say the same thing), income not entered by source (`IncomeNotSplit`, no income row included), and an Expenses step never saved (no `ExpenseInfo` row). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. A forms refusal also carries the `step` (a wizard step key) or `page` (a route) that fixes it, when the exception names one: `PreconditionMissing.step`, `IncomeNotSplit.step` (`income_info`) and `IntakeNotFinished.page` (`/intake`); "already filed", "not in your packet" and `NoTableInForce` carry neither, and the key is absent, never null. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
-- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type`: Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
+- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
 - **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
 - **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. It has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
PATCH
```

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

Expected: `2123 passed, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  362 passed (362)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

This task changes only the backend and no page flow, so the journeys don't run.

- [ ] **Step 7: Commit**

```bash
set -eo pipefail
git add \
  CLAUDE.md \
  backend/apps/eligibility/cmi.py \
  backend/apps/forms/registry.py \
  backend/apps/forms/tests/test_form_views.py \
  backend/apps/forms/tests/test_registry.py \
  backend/apps/forms/views.py \
  backend/apps/intake/tests/test_completion.py \
  backend/apps/intake/tests/test_e2e_intake.py \
  backend/apps/intake/tests/test_income_resume.py \
  backend/apps/intake/views.py
git commit -F - <<'MSG'
feat(intake): Complete names the step that fixes each gap

Complete checked only that the debtor, income and expense rows existed and
answered with a list of bare strings the wizard never showed, so a filer read
"Please complete all required sections before finalizing" without learning
which section (forms step 3a1 spec §4.1).

Complete now refuses with a 400 whose errors are {step, message}, one per
gap in wizard order, each step a WIZARD_STEPS key:
- no debtor row (the name-and-address sentence), or an SSN that isn't 9
  digits: the registry's own _needs_ssn, so Complete and Forms 101 and 121
  say the same thing;
- income not entered by source (IncomeNotSplit; no income row counts too);
- the Expenses step never saved (no ExpenseInfo row).

The registry's three preconditions take the spec's sentences, which name
their step, and PreconditionMissing carries the step key. IncomeNotSplit
carries step "income_info" and IntakeNotFinished page "/intake". The forms
views' refusal body adds that step or page when the exception names one,
and only on a 422: "already filed", "not in your packet" and NoTableInForce
carry neither, and a 500 never does.

Tests: Complete names each gap with its exact sentence (no debtor row, an
8-digit SSN, all ten income amounts empty, no expense row) and lists every
gap in wizard order; the registry tests assert each exact sentence and
step; a 500 names no step or page. Changed with the new bodies: the
IncomeNotSplit, IntakeNotFinished and Form 121 refusals in
test_form_views.py and test_income_resume.py, and the three missing-row
Complete tests in test_e2e_intake.py, whose SSNs move to the 900 range.

CLAUDE.md: "Forms need a completed intake" says what Complete refuses, its
400 body and the step or page on forms refusals; "GenerateAll vs single"
notes that a whole-call refusal carries them too.

Refs DIG-181
MSG
git status --short
```

### Task 4: Make the Review step list what Complete is missing, with a way to each step

_Built and verified as commit `cd665a9` on `plan/forms-step3a1`._

**Files:**

- Create: `frontend/src/api/__tests__/client.test.ts`
- Create: `frontend/src/components/wizard/__tests__/MeansTestPreview.test.tsx`
- Modify: `backend/apps/intake/tests/test_e2e_intake.py`
- Modify: `backend/apps/intake/views.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/wizard/steps/ReviewStep.tsx`
- Modify: `frontend/src/hooks/useDebouncedMeansTest.ts`
- Modify: `frontend/src/pages/FormDashboard.tsx`
- Modify: `frontend/src/pages/IntakeWizard.tsx`
- Modify: `frontend/src/pages/__tests__/FormDashboard.test.tsx`
- Modify: `frontend/src/pages/__tests__/IntakeWizard.test.tsx`
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/types/api.ts`

**Interfaces:**

- Consumes:
  - Task 3's Complete refusal: a 400 `{"errors": [{"step": str, "message": str}, ...], "message": "Please complete all required sections before finalizing"}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key.
  - Task 3's forms refusal bodies: a 422 carries `step` (`IncomeNotSplit.step = "income_info"`, the registry's checks) or `page` (`IntakeNotFinished.page = "/intake"`) when one fixes it. `NoTableInForce`, "already filed" and "not in your packet" carry neither.
  - Task 1's `NoTableInForce` (`apps.districts.dated_tables`) and `IncomeNotSplit` (`apps.eligibility.cmi`), whose `str()` is a sentence for the filer.
  - `IntakeSessionViewSet.calculate_means_test` (`backend/apps/intake/views.py`), which answers every `ValueError` with a 400 `{"error": str(e), "message": "Unable to calculate means test. Please ensure all income information is provided."}`.
  - In `frontend/src/api/client.ts`: `APIClientError(message, statusCode, details?, serverError?)`, whose `serverError` keeps the body's `error`, and `handleAPIError(response)`, which builds it from the body's `message || error`. `APIError` in `frontend/src/types/api.ts`.
  - `IntakeContext` (`frontend/src/context/IntakeContext.tsx`): `completeSession` records a refusal's `message` as the context `error` and rethrows the `APIClientError`; `calculateMeansTest` shows a 400's `serverError`, else its `message`. `WizardLayout` shows the context `error` in its `role="alert"` block, whose "Dismiss error message" button calls `clearError`.
  - In `frontend/src/pages/IntakeWizard.tsx`: `WIZARD_STEPS` (`{ number, label, key }`, for example `{ number: 5, label: 'Amounts Owed', key: 'debts' }`), `setCurrentStepNumber`, `handlePrevious` (Go Back), and `handleComplete` with its `pressInFlightRef` guard.
  - `ReviewStep` (`frontend/src/components/wizard/steps/ReviewStep.tsx`) and, in `frontend/src/styles/global.css`, `.review-step` (a flex column with `gap: var(--space-5)`), `.review-section`, `.review-list` and `.review-list-item`. `Button` from `components/common`, with `variant="outline"` and `size="sm"`.
  - `useDebouncedMeansTest` (`frontend/src/hooks/useDebouncedMeansTest.ts`), which shows `INCOMPLETE_DATA_MESSAGE` ("We'll estimate your eligibility once you provide income and expense information.") for every 400, and `MeansTestPreview({ sessionId, currentStep })` with its "Eligibility Estimate" toggle.
  - In `frontend/src/pages/FormDashboard.tsx`: `wholeCallRefusal(err, generic)`, `DASHBOARD_ERROR` and `ERROR_GENERIC` (`constants/copy`), the notice for an unfinished intake (shown while the context's `session.status` is not `completed`) with its "Finish your intake" link, the load-error block (Try Again for `DASHBOARD_ERROR`, a "Finish your intake" link for any other refusal) and the Generate All refusal block.
  - For the tests: `server` (`src/test/mocks/server`); in `IntakeWizard.test.tsx`, `renderWizard()`, `sessionAtStep8`, `completedSession` and "keeps the filer on Review with the reason when Complete fails"; in `FormDashboard.test.tsx`, `renderFormDashboard()`, `completedSession`, and in `describe('when Generate All or the packet list is refused')` `openGenerateAll()`, `FINISH_INTAKE` and `INCOME_NOT_SPLIT`.
- Produces:
  - `calculate_means_test`: a 400 `{"error": str(e), "message": ...}` for `IncomeNotSplit` and `NoTableInForce` only, and a 400 `{"message": "Unable to calculate means test. Please ensure all income information is provided."}` for any other `ValueError`.
  - In `frontend/src/types/api.ts`: `interface CompletionError { step: string; message: string }`; `APIError` gains `errors?: CompletionError[]`, `step?: string` and `page?: string`.
  - `APIClientError` gains `errors?: CompletionError[]`, `step?: string` and `page?: string`, set from an optional fifth constructor argument `pointers: { errors?; step?; page? } = {}`. `handleAPIError` keeps `errors` filtered by the module-private `isCompletionError(entry)` (a string `step` and a string `message`; `undefined` when the body has no array), and `step` and `page` only when they are strings.
  - In `IntakeWizard.tsx`: a `completionErrors` state (`CompletionError[]`) and `moveToStep(stepNumber)`, which Go Back and the "Go to" button share. Review gets `completionReasons` and `onGoToStep={moveToStep}`.
  - `ReviewStep` props `completionReasons?: { message: string; step?: { number: number; label: string } }[]` and `onGoToStep?: (stepNumber: number) => void`. Its first child is `<div className="review-reasons" aria-live="polite">`, holding a `review-section` list of each message with a "Go to {label}" button. Task 5's `debts` entry shows there with "Go to Amounts Owed" and needs no further frontend change.
  - `.review-reasons:empty { margin-bottom: calc(-1 * var(--space-5)); }` in `global.css`.
  - `useDebouncedMeansTest`: a 400 shows `err.serverError || INCOMPLETE_DATA_MESSAGE`.
  - In `FormDashboard.tsx`: `PAGE_LINK_LABELS = { '/intake': 'Finish your intake' }`, `loadFailure(err): { message; namesFix }`, the `error` state as `{ message: string; namesFix: boolean } | null`, `generateAllRefusal` as `{ message: string; page?: string } | null`, and `noticeLinksIntake`, `errorLinksIntake`, `refusalPage` and `refusalLinkLabel`, which decide the one "Finish your intake" link.
  - Vitest in `src/api/__tests__/client.test.ts` (new), `describe('what a refusal says fixes it')`: `keeps each reason Complete gives with its step, and drops an entry that lacks either`, `keeps the step or page a forms refusal names` and `keeps no step or page that is not a string, such as a field error`.
  - Vitest in `src/components/wizard/__tests__/MeansTestPreview.test.tsx` (new), `describe('MeansTestPreview when the means test refuses')`: `says what stands in the way when %s` (cases `no median table is in force` and `income was not entered by source`) and `waits for income and expenses when the refusal carries no sentence for the filer`.
  - Vitest in `IntakeWizard.test.tsx`, `describe("IntakeWizard Complete's reasons")`: `lists each thing Complete found missing under its general message, with a way to each step`, `reads the reasons out to a screen reader, in a polite region that was on Review before them`, `keeps the reasons on Review after the filer dismisses the general message`, `shows none of the old reasons after "Go to" a step and back to Review`, `shows none of the old reasons once the filer leaves Review and comes back` and `drops the reasons once Complete accepts the intake, even if the eligibility check then fails`.
  - Vitest in `FormDashboard.test.tsx`: `offers neither the intake nor a retry when the packet list’s refusal names no fix`, `links a refused Generate All to the page that fixes it`, `adds no second link back to the intake when the dashboard already offers one`, `adds no second link back to the intake when a refused packet list names its fix` and `adds no second link back to the intake when both the packet list and Generate All are refused`; the constants `NOT_SPLIT` (`{ error: INCOME_NOT_SPLIT, step: 'income_info' }`) and `NO_TABLE`.

**Decisions already made in this task:**

- **The only new words are "Go to {label}".** The label is the step's `WIZARD_STEPS` label, so a filer reads "Go to Income" or "Go to Amounts Owed". Each reason is the server's own sentence (spec §4.2), and the general message, "Please complete all required sections before finalizing", stays in WizardLayout's alert above the list. The list has no heading, because the spec gives no words for one. The dashboard's link reads "Finish your intake", words it already used. All of it is navigation, never advice.
- **"Go to" moves the way Go Back does** (spec §4.4). `moveToStep` sets the step and clears the list, and Go Back and the button both call it: no save and no `update_step`, so `current_step` stays where Continue last put it. A reason whose `step` isn't a `WIZARD_STEPS` key shows its sentence with no button.
- **The list clears when the step changes and when Complete is pressed again.** Go Back and "Go to" clear it through `moveToStep`, and `handleComplete` clears it at the press, so a press where Complete passes but the eligibility check fails shows no old reasons. `handleNext` is unchanged: Continue isn't shown on Review, and every way off Review goes through `moveToStep`. It is not an effect keyed on `currentStepNumber`, because the `recommended` preset of `eslint-plugin-react-hooks` 7 reports `react-hooks/set-state-in-effect` as an error, so `npm run lint` would fail.
- **`IntakeContext` is unchanged.** `completeSession` already rethrows the `APIClientError`, which now carries `errors`, and `handleComplete`'s catch reads them from there. That is how the context "passes it to the wizard" (spec §4.4). Context state would need its own clear action for no gain.
- **The reasons sit in a polite live region that is on Review from the start (Ruling R4-d).** `ReviewStep` always renders `<div className="review-reasons" aria-live="polite">` as its first child, and the reasons' `<section>` renders inside it, so a screen reader announces them when they arrive. The `<section>` has no `aria-labelledby`: naming it by the alert's text left a dangling reference once the filer pressed Dismiss, which clears only the context `error`. The reasons stay on Review after Dismiss.
- **`.review-reasons:empty` gives back the gap.** The empty region is a zero-height flex item in `.review-step`, whose `gap: var(--space-5)` would otherwise add space above the info box on every Review. React renders nothing for `false`, so `:empty` matches. The rule is not `display: none`, because a hidden region drops out of the accessibility tree and a live region that appears with its content is not reliably announced. It is not `display: contents` either, which has a history of accessibility-tree bugs. `global.css` already uses the same `calc(-1 * var(--space-N))` idiom.
- **The client keeps only the shapes the server sends.** `errors` keeps entries with a string `step` and a string `message`. `step` and `page` are kept only as strings, so a DRF field error such as `{"step": ["This field is required."]}` is never taken for a pointer. There is no key check: ReviewStep shows no button for an unknown step. The fifth constructor argument defaults to `{}`, so the existing two- and four-argument calls are unchanged.
- **Ruling R4-c: `calculate_means_test` puts `error` only on `IncomeNotSplit` and `NoTableInForce`.** Their text is a sentence for the filer, as in the forms views' `_failure`. Any other `ValueError`'s text is for operations: a new filer with no income saved reads "IntakeSession must have income_info before calculating means test". So that 400 carries only the general `message`, and `test_calculate_means_test_without_income_info` changes with it. `test_cmi.py`'s two endpoint tests already assert each sentence in `error`, so they guard the new `except`. Nothing new is logged: the type alone says only `ValueError`, and the message may not be logged (G6).
- **The preview shows a 400's `error`, else the estimate message** (Task 1 review M2). Under R4-c that `error` is always a sentence for the filer, so the frontend copies no backend sentence. A filer during a gap between median tables, or with income not entered by source, is no longer asked for income they already gave. On Review, `IntakeContext.calculateMeansTest` already shows `serverError`, else `message`, so a 400 without `error` now shows "Unable to calculate means test. Please ensure all income information is provided." instead of operations text. At Complete that can only be an unexpected `ValueError`, such as a household above 8 with no extra-person amount.
- **Ruling R4-b: the packet list's error block links to the intake only when the refusal names a fix.** `loadFailure` sets `namesFix` only for a 422 carrying a `step` or `page`. `NoTableInForce` names neither, since no step of the filer's fixes it (spec §4.3), so its sentence shows alone, with no link and no Try Again. Our own `DASHBOARD_ERROR` keeps Try Again.
- **Ruling R4-a: "Finish your intake" shows at most once, on the first block that offers it.** The order is the notice for an unfinished intake (`noticeLinksIntake`), then a packet-list refusal that names its fix (`errorLinksIntake`), then the page Generate All's refusal names. The page's copy of the intake's status and the server's can disagree when the intake changes in another tab, and the two tests that set that up model the disagreement. A `page` other than `/intake` keeps its own link when `PAGE_LINK_LABELS` has a label for it, and gets none otherwise.
- **Only Generate All's refusal gets a `page` link.** `IntakeNotFinished`, the only refusal with a `page`, reaches the dashboard only through Generate All, because the packet list never refuses an unfinished intake. `FormCard` discards single-form refusals, so their `step` and `page` never show (pre-existing, step 2a).
- **Mocks follow the server's bodies.** `IntakeWizard.test.tsx`'s Complete refusal mock, which Task 3 left as strings, now sends `{step, message}` entries; its assertions are unchanged. The `FormDashboard.test.tsx` packet-list refusals for income not entered by source send `NOT_SPLIT`, which carries `step: 'income_info'` as the server has since Task 3; two of those tests pin the link. The two Generate All `FINISH_INTAKE` mocks without a `page` stay, because they test the sentence and the reload.
- **`CLAUDE.md` is unchanged.** Task 3 already describes the bodies, and no gotcha becomes false.
- **Left as they are, as ticket candidates.** After "Go to", the general alert stays on the new step without its reason until Continue or Dismiss (review M3). "Go to Your Information" then Continue sends `update_step` for step 2, which lowers `current_step`, and detours through `/documents` (review M4). Both follow from the spec's "the way Go Back does".
- **This commit includes three rounds of fixes.** Round 1 applied R4-b and R4-c, and round 2 the review's M1, M2, M5 and M6. Round 3 applied R4-d: it removed the `aria-labelledby` and the alert `id` that round 2 had added, so `WizardLayout.tsx` is unchanged. The controller checked round 3, not a reviewer.

- [ ] **Step 1: Write the failing means-test test**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/tests/test_e2e_intake.py b/backend/apps/intake/tests/test_e2e_intake.py
index 012abb2..4890553 100644
--- a/backend/apps/intake/tests/test_e2e_intake.py
+++ b/backend/apps/intake/tests/test_e2e_intake.py
@@ -706,7 +706,12 @@ class TestMeansTestCalculation:
         assert Decimal(result["cmi"]) == Decimal("80000.00")

     def test_calculate_means_test_without_income_info(self, api_client, district):
-        """Test means test calculation without income info returns 400."""
+        """Without income saved yet, the means test is a 400 with only its general message.
+
+        The wizard's preview asks this at the Income step before anything is saved. The
+        calculator's own words ("IntakeSession must have income_info...") are for operations,
+        so the body carries no `error` for the preview to show.
+        """
         # Create session without income info
         url = reverse("intake-session-list")
         response = api_client.post(url, {"district": district.id, "current_step": 1}, format="json")
@@ -717,7 +722,9 @@ class TestMeansTestCalculation:
         response = api_client.post(calc_url)

         assert response.status_code == status.HTTP_400_BAD_REQUEST
-        assert "error" in response.data
+        assert response.data == {
+            "message": "Unable to calculate means test. Please ensure all income information is provided."
+        }

     def test_fee_waiver_qualification(self, api_client, complete_session, median_income):
         """Test fee waiver qualification for income < 150% poverty line."""
PATCH
```

A session with no income row must get a 400 that is exactly the general message, with no `error`: the wizard's preview asks before the Income step is saved, and the calculator's own words are for operations.

- [ ] **Step 2: Run it and watch it fail**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=short apps/intake/tests/test_e2e_intake.py::TestMeansTestCalculation::test_calculate_means_test_without_income_info apps/eligibility/tests/test_cmi.py::test_means_test_endpoint_asks_for_income_by_source_as_a_400 apps/eligibility/tests/test_cmi.py::test_means_test_endpoint_refuses_without_a_median_table_in_force_as_a_400 -q -p no:cacheprovider 2>&1 | tail -20
```

Expected: FAIL — `1 failed, 2 passed`. The changed test finds the operations text still in the body, `{'error': 'IntakeSession must have income_info before calculating means test'}`. The two endpoint tests in test_cmi.py already pass: they require each plain-words sentence in the body's error, and the new except clause must keep it there.

- [ ] **Step 3: Keep operations text out of the means test's 400**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/views.py b/backend/apps/intake/views.py
index 0d833e8..bf2ca24 100644
--- a/backend/apps/intake/views.py
+++ b/backend/apps/intake/views.py
@@ -11,6 +11,7 @@ from rest_framework.decorators import action
 from rest_framework.permissions import IsAuthenticated
 from rest_framework.response import Response

+from apps.districts.dated_tables import NoTableInForce
 from apps.eligibility.cmi import IncomeNotSplit, current_monthly_income
 from apps.eligibility.services import MeansTestCalculator
 from apps.forms.registry import PreconditionMissing, _needs_ssn
@@ -268,7 +269,10 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
                 }
             )

-        except ValueError as e:
+        # Only these two refusals carry their own plain words for the filer in `error`, as in
+        # the forms views. Any other ValueError's text is for operations (no income row yet
+        # reads "IntakeSession must have income_info..."), so it stays out of the response.
+        except (IncomeNotSplit, NoTableInForce) as e:
             return Response(
                 {
                     "error": str(e),
@@ -276,6 +280,13 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
                 },
                 status=status.HTTP_400_BAD_REQUEST,
             )
+        except ValueError:
+            return Response(
+                {
+                    "message": "Unable to calculate means test. Please ensure all income information is provided.",
+                },
+                status=status.HTTP_400_BAD_REQUEST,
+            )

     @action(detail=True, methods=["get"])
     def summary(self, request, pk=None):
PATCH
```

`calculate_means_test` catches `IncomeNotSplit` and `NoTableInForce` first and keeps their sentence in `error`; any other `ValueError` gets a 400 with only the general `message` (Ruling R4-c).

- [ ] **Step 4: Run the means-test tests again**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=short apps/intake/tests/test_e2e_intake.py::TestMeansTestCalculation::test_calculate_means_test_without_income_info apps/eligibility/tests/test_cmi.py::test_means_test_endpoint_asks_for_income_by_source_as_a_400 apps/eligibility/tests/test_cmi.py::test_means_test_endpoint_refuses_without_a_median_table_in_force_as_a_400 -q -p no:cacheprovider 2>&1 | tail -20
```

Expected: `3 passed`.

- [ ] **Step 5: Write the failing frontend tests**

```ts file=frontend/src/api/__tests__/client.test.ts
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { api, APIClientError } from '../client';

/** The error a call rejects with, so its fields can be read. */
async function refusalOf(call: Promise<unknown>): Promise<APIClientError> {
  try {
    await call;
  } catch (err) {
    if (err instanceof APIClientError) return err;
    throw err;
  }
  throw new Error('the call was not refused');
}

// A refusal says what fixes it (step 3a1 spec §4): the wizard and the dashboard can only point
// the filer there if the client keeps it.
describe('what a refusal says fixes it', () => {
  it('keeps each reason Complete gives with its step, and drops an entry that lacks either', async () => {
    const noExpenses = {
      step: 'expense_info',
      message: 'Go through the Expenses step, even if you have no expenses to enter.',
    };
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
        HttpResponse.json(
          {
            message: 'Please complete all required sections before finalizing',
            errors: [
              noExpenses,
              'Expense information is required',
              { message: 'A sentence with no step' },
              { step: 'income_info' },
            ],
          },
          { status: 400 }
        )
      )
    );

    const err = await refusalOf(api.intake.completeSession(1));

    expect(err.message).toBe('Please complete all required sections before finalizing');
    expect(err.errors).toEqual([noExpenses]);
  });

  it('keeps the step or page a forms refusal names', async () => {
    server.use(
      http.post('http://localhost:8000/api/forms/generate_all/', () =>
        HttpResponse.json(
          { error: 'Finish your intake before preparing your forms.', page: '/intake' },
          { status: 422 }
        )
      ),
      http.post('http://localhost:8000/api/forms/generate/', () =>
        HttpResponse.json(
          {
            form_type: 'form_101',
            error: 'Enter your income by source on the Income step.',
            step: 'income_info',
          },
          { status: 422 }
        )
      )
    );

    const unfinished = await refusalOf(api.forms.generateAll(1));
    const notSplit = await refusalOf(api.forms.generate(1, 'form_101'));

    expect(unfinished.page).toBe('/intake');
    expect(unfinished.step).toBeUndefined();
    expect(notSplit.step).toBe('income_info');
    expect(notSplit.page).toBeUndefined();
  });

  it('keeps no step or page that is not a string, such as a field error', async () => {
    server.use(
      http.post('http://localhost:8000/api/forms/generate_all/', () =>
        HttpResponse.json(
          { step: ['This field is required.'], page: { number: 2 } },
          { status: 400 }
        )
      )
    );

    const err = await refusalOf(api.forms.generateAll(1));

    expect(err.step).toBeUndefined();
    expect(err.page).toBeUndefined();
    expect(err.errors).toBeUndefined();
  });
});
```

The client must keep Complete's entries that name both a step and a sentence, and a forms refusal's `step` or `page`. It must keep no pointer from a DRF field error.

```tsx file=frontend/src/components/wizard/__tests__/MeansTestPreview.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from '../../../test/mocks/server';
import { MeansTestPreview } from '../MeansTestPreview';

const ESTIMATE_LATER =
  "We'll estimate your eligibility once you provide income and expense information.";
const GENERIC = 'Unable to calculate means test. Please ensure all income information is provided.';

/**
 * The means test answers the preview with a 400 carrying this body; resolves once the preview
 * has shown what it makes of it.
 */
async function openPreviewRefusedWith(body: { error?: string; message: string }) {
  let answered = false;
  server.use(
    http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () => {
      answered = true;
      return HttpResponse.json(body, { status: 400 });
    })
  );
  render(<MeansTestPreview sessionId={1} currentStep={3} />);
  await userEvent.click(screen.getByRole('button', { name: /eligibility estimate/i }));
  await waitFor(() => expect(answered).toBe(true));
  await waitFor(() => expect(screen.queryByText('Updating estimate...')).not.toBeInTheDocument());
}

describe('MeansTestPreview when the means test refuses', () => {
  // T1 review M2: during a gap between median tables, asking for income the filer already gave
  // sends them back to a step that can't help
  it.each([
    [
      'no median table is in force',
      "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your forms. Please try again later.",
    ],
    ['income was not entered by source', 'Enter your income by source on the Income step.'],
  ])('says what stands in the way when %s', async (_, sentence) => {
    await openPreviewRefusedWith({ error: sentence, message: GENERIC });

    expect(screen.getByText(sentence)).toBeInTheDocument();
    expect(screen.queryByText(ESTIMATE_LATER)).not.toBeInTheDocument();
  });

  it('waits for income and expenses when the refusal carries no sentence for the filer', async () => {
    // A new filer on the Income step has no income saved yet
    await openPreviewRefusedWith({ message: GENERIC });

    expect(screen.getByText(ESTIMATE_LATER)).toBeInTheDocument();
    expect(screen.queryByText(GENERIC)).not.toBeInTheDocument();
  });
});
```

The preview must show a 400's `error` sentence, and for a 400 with only a `message` it must keep the estimate message, never the general `message`. Each test waits until the means test has answered and "Updating estimate..." is gone, because the preview starts out showing the estimate message: without the wait, the last test would pass without testing anything.

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/IntakeWizard.test.tsx b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
index bc04a81..6b676e2 100644
--- a/frontend/src/pages/__tests__/IntakeWizard.test.tsx
+++ b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
@@ -184,7 +184,12 @@ describe('IntakeWizard handleComplete routing', { timeout: 30_000 }, () => {
       http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
         HttpResponse.json(
           {
-            errors: ['Expense information is required'],
+            errors: [
+              {
+                step: 'expense_info',
+                message: 'Go through the Expenses step, even if you have no expenses to enter.',
+              },
+            ],
             message: 'Please complete all required sections before finalizing',
           },
           { status: 400 }
@@ -242,6 +247,182 @@ describe('IntakeWizard handleComplete routing', { timeout: 30_000 }, () => {
   });
 });

+// ===========================================================================
+// What Complete found missing (step 3a1 spec §4.4, DIG-181)
+// ===========================================================================
+
+describe("IntakeWizard Complete's reasons", { timeout: 30_000 }, () => {
+  const REFUSED = 'Please complete all required sections before finalizing';
+  const NO_INCOME = {
+    step: 'income_info',
+    message: 'Enter your income by source on the Income step.',
+  };
+  const NO_EXPENSES = {
+    step: 'expense_info',
+    message: 'Go through the Expenses step, even if you have no expenses to enter.',
+  };
+
+  /** Complete refuses with these reasons; returns the update_step bodies the wizard sends. */
+  function refuseComplete(errors: Array<{ step: string; message: string }>) {
+    const stepUpdates: unknown[] = [];
+    server.use(
+      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
+        HttpResponse.json({ message: REFUSED, errors }, { status: 400 })
+      ),
+      http.post(
+        'http://localhost:8000/api/intake/sessions/:id/update_step/',
+        async ({ request }) => {
+          stepUpdates.push(await request.json());
+          return HttpResponse.json({ session: sessionAtStep8, message: 'Step updated.' });
+        }
+      )
+    );
+    return stepUpdates;
+  }
+
+  beforeEach(() => {
+    // The wizard logs each refusal; silenced so it doesn't read as a broken test
+    vi.spyOn(console, 'error').mockImplementation(() => {});
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+        HttpResponse.json(sessionAtStep8)
+      )
+    );
+  });
+  afterEach(() => vi.mocked(console.error).mockRestore());
+
+  it('lists each thing Complete found missing under its general message, with a way to each step', async () => {
+    renderWizard();
+    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
+    const stepUpdates = refuseComplete([NO_INCOME, NO_EXPENSES]);
+
+    await userEvent.click(completeBtn);
+
+    const alert = await screen.findByRole('alert');
+    expect(alert).toHaveTextContent(REFUSED);
+    const firstReason = screen.getByText(NO_INCOME.message);
+    // The general message comes first, then the list
+    expect(
+      alert.compareDocumentPosition(firstReason) & Node.DOCUMENT_POSITION_FOLLOWING
+    ).toBeTruthy();
+    expect(screen.getByText(NO_EXPENSES.message)).toBeInTheDocument();
+    expect(screen.getByRole('button', { name: 'Go to Income' })).toBeInTheDocument();
+
+    await userEvent.click(screen.getByRole('button', { name: 'Go to Expenses' }));
+
+    expect(await screen.findByRole('heading', { name: 'Expenses', level: 2 })).toBeInTheDocument();
+    // Like Go Back, it moves without telling the server where the filer is
+    expect(stepUpdates).toEqual([]);
+  });
+
+  // A live region announces only changes to a region already on the page
+  it('reads the reasons out to a screen reader, in a polite region that was on Review before them', async () => {
+    const { container } = renderWizard();
+    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
+    const politeRegionsBefore = Array.from(container.querySelectorAll('[aria-live="polite"]'));
+    refuseComplete([NO_INCOME, NO_EXPENSES]);
+
+    await userEvent.click(completeBtn);
+
+    const reason = await screen.findByText(NO_INCOME.message);
+    const region = reason.closest('[aria-live="polite"]');
+    expect(politeRegionsBefore).toContain(region);
+    expect(region).toHaveTextContent(NO_EXPENSES.message);
+  });
+
+  it('keeps the reasons on Review after the filer dismisses the general message', async () => {
+    renderWizard();
+    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
+    refuseComplete([NO_INCOME, NO_EXPENSES]);
+    await userEvent.click(completeBtn);
+    await screen.findByRole('alert');
+
+    await userEvent.click(screen.getByRole('button', { name: 'Dismiss error message' }));
+
+    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
+    expect(screen.getByText(NO_INCOME.message)).toBeInTheDocument();
+    expect(screen.getByText(NO_EXPENSES.message)).toBeInTheDocument();
+    expect(screen.getByRole('button', { name: 'Go to Income' })).toBeInTheDocument();
+  });
+
+  it('shows none of the old reasons after "Go to" a step and back to Review', async () => {
+    const UNCHECKED_DEBTS = {
+      step: 'debts',
+      message: 'Check the debts read from your documents on the Amounts Owed step.',
+    };
+    // Amounts Owed lets the filer continue once it holds a debt
+    const sessionWithDebt = { ...sessionAtStep8, debts: completedSession.debts };
+    server.use(
+      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+        HttpResponse.json(sessionWithDebt)
+      ),
+      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
+        HttpResponse.json(sessionWithDebt)
+      )
+    );
+    const { container } = renderWizard();
+    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
+    refuseComplete([UNCHECKED_DEBTS]);
+    await userEvent.click(completeBtn);
+
+    await userEvent.click(await screen.findByRole('button', { name: 'Go to Amounts Owed' }));
+    for (const next of ['Contracts & Leases', 'Codebtors', 'Review & Results']) {
+      const continueBtn = screen.getByRole('button', { name: 'Continue' });
+      await waitFor(() => expect(continueBtn).toBeEnabled());
+      await userEvent.click(continueBtn);
+      await waitFor(() => expect(container.querySelector('.step-title')).toHaveTextContent(next));
+    }
+
+    expect(screen.queryByText(UNCHECKED_DEBTS.message)).not.toBeInTheDocument();
+  });
+
+  it('shows none of the old reasons once the filer leaves Review and comes back', async () => {
+    renderWizard();
+    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
+    const stepUpdates = refuseComplete([NO_EXPENSES]);
+    await userEvent.click(completeBtn);
+    await screen.findByText(NO_EXPENSES.message);
+
+    await userEvent.click(screen.getByRole('button', { name: 'Go Back' }));
+    // On Codebtors, the step before Review
+    const continueBtn = await screen.findByRole('button', { name: 'Continue' });
+    await waitFor(() => expect(continueBtn).toBeEnabled());
+    await userEvent.click(continueBtn);
+
+    await screen.findByRole('heading', { name: /review & results/i, level: 2 });
+    expect(stepUpdates).toEqual([{ current_step: 8 }]);
+    expect(screen.queryByText(NO_EXPENSES.message)).not.toBeInTheDocument();
+  });
+
+  it('drops the reasons once Complete accepts the intake, even if the eligibility check then fails', async () => {
+    renderWizard();
+    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
+    refuseComplete([NO_EXPENSES]);
+    await userEvent.click(completeBtn);
+    await screen.findByText(NO_EXPENSES.message);
+    server.use(
+      http.post('http://localhost:8000/api/intake/sessions/:id/complete/', () =>
+        HttpResponse.json({ message: 'Session completed.' })
+      ),
+      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
+        HttpResponse.json(
+          {
+            error: NO_INCOME.message,
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
+    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(NO_INCOME.message));
+    expect(screen.queryByText(NO_EXPENSES.message)).not.toBeInTheDocument();
+  });
+});
+
 // ===========================================================================
 // Stepping back after Complete (forms step 2 §5.3)
 // ===========================================================================
PATCH
```

The old Complete mock sends `{step, message}` entries. The new tests refuse Complete with one or two reasons. Review must list them below the general message, each with a "Go to" button that opens its step without `update_step`. They must sit in a polite live region that was on Review before them, stay after Dismiss, and be gone after "Go to" and back, after Go Back and Continue, and after a second press that Complete accepts. The "Go to Amounts Owed" test uses Task 5's sentence for unconfirmed debts and adds the session PATCH handler that the Amounts Owed save needs.

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/FormDashboard.test.tsx b/frontend/src/pages/__tests__/FormDashboard.test.tsx
index 071e6e9..1c16e80 100644
--- a/frontend/src/pages/__tests__/FormDashboard.test.tsx
+++ b/frontend/src/pages/__tests__/FormDashboard.test.tsx
@@ -322,6 +322,10 @@ describe('FormDashboard', () => {
   describe('when Generate All or the packet list is refused', { timeout: 15_000 }, () => {
     const FINISH_INTAKE = 'Finish your intake before preparing your forms.';
     const INCOME_NOT_SPLIT = 'Enter your income by source on the Income step.';
+    // The refusal as the server sends it, naming the wizard step that fixes it
+    const NOT_SPLIT = { error: INCOME_NOT_SPLIT, step: 'income_info' };
+    const NO_TABLE =
+      "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your forms. Please try again later.";
     // The server's sentence for a 500 speaks of one form, so the dashboard never shows it
     const SERVER_FAILURE = "This form couldn't be prepared. Please try again later.";
     const GENERIC =
@@ -350,7 +354,7 @@ describe('FormDashboard', () => {
     it('shows the packet list’s refusal in its own words', async () => {
       server.use(
         http.get('http://localhost:8000/api/forms/packet/', () =>
-          HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 })
+          HttpResponse.json(NOT_SPLIT, { status: 422 })
         )
       );

@@ -364,7 +368,7 @@ describe('FormDashboard', () => {
       // A completed filer whose income isn't split gets the same refusal on every reload
       server.use(
         http.get('http://localhost:8000/api/forms/packet/', () =>
-          HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 })
+          HttpResponse.json(NOT_SPLIT, { status: 422 })
         )
       );

@@ -378,6 +382,21 @@ describe('FormDashboard', () => {
       expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
     });

+    // Ruling R4-b: no step of the filer's fixes a missing median table (spec §4.3)
+    it('offers neither the intake nor a retry when the packet list’s refusal names no fix', async () => {
+      server.use(
+        http.get('http://localhost:8000/api/forms/packet/', () =>
+          HttpResponse.json({ error: NO_TABLE }, { status: 422 })
+        )
+      );
+
+      renderFormDashboard();
+
+      await screen.findByText(NO_TABLE);
+      expect(screen.queryByRole('link', { name: 'Finish your intake' })).not.toBeInTheDocument();
+      expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
+    });
+
     it('shows generic words, never the server’s, when the packet list fails on the server', async () => {
       server.use(
         http.get('http://localhost:8000/api/forms/packet/', () =>
@@ -435,6 +454,85 @@ describe('FormDashboard', () => {
       expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
     });

+    // The intake was reopened since this page loaded it as complete (step 3a1 spec §4.4)
+    it('links a refused Generate All to the page that fixes it', async () => {
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({ error: FINISH_INTAKE, page: '/intake' }, { status: 422 })
+        )
+      );
+
+      renderFormDashboard();
+      await userEvent.click(await openGenerateAll());
+
+      await screen.findByText(FINISH_INTAKE);
+      const links = screen.getAllByRole('link', { name: 'Finish your intake' });
+      expect(links).toHaveLength(1);
+      expect(links[0]).toHaveAttribute('href', '/intake');
+    });
+
+    // Ruling R4-a: the notice for an unfinished intake already links back to it
+    it('adds no second link back to the intake when the dashboard already offers one', async () => {
+      server.use(
+        http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+          HttpResponse.json({ ...completedSession, status: 'in_progress', completed_at: null })
+        ),
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({ error: FINISH_INTAKE, page: '/intake' }, { status: 422 })
+        )
+      );
+
+      renderFormDashboard();
+      await userEvent.click(await openGenerateAll());
+
+      await screen.findByText(FINISH_INTAKE);
+      expect(screen.getAllByRole('link', { name: 'Finish your intake' })).toHaveLength(1);
+    });
+
+    // This page loaded the intake as unfinished; it was completed since, elsewhere
+    it('adds no second link back to the intake when a refused packet list names its fix', async () => {
+      server.use(
+        http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+          HttpResponse.json({ ...completedSession, status: 'in_progress', completed_at: null })
+        ),
+        http.get('http://localhost:8000/api/forms/packet/', () =>
+          HttpResponse.json(NOT_SPLIT, { status: 422 })
+        )
+      );
+
+      renderFormDashboard();
+
+      await screen.findByText(INCOME_NOT_SPLIT);
+      expect(screen.getAllByRole('link', { name: 'Finish your intake' })).toHaveLength(1);
+    });
+
+    // This page loaded the intake as complete; it was reopened since, elsewhere
+    it('adds no second link back to the intake when both the packet list and Generate All are refused', async () => {
+      let packetCalls = 0;
+      server.use(
+        http.get('http://localhost:8000/api/forms/packet/', () => {
+          packetCalls += 1;
+          return packetCalls === 1
+            ? HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
+            : HttpResponse.json(NOT_SPLIT, { status: 422 });
+        }),
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({ error: FINISH_INTAKE, page: '/intake' }, { status: 422 })
+        )
+      );
+
+      renderFormDashboard();
+      // Marking a form filed reloads the packet list, which is now refused
+      await userEvent.click(await screen.findByRole('button', { name: /mark as filed/i }));
+      await screen.findByText(INCOME_NOT_SPLIT);
+      await userEvent.click(await openGenerateAll());
+
+      await screen.findByText(FINISH_INTAKE);
+      // Generate All reloads the packet list too, and it is refused again
+      await waitFor(() => expect(packetCalls).toBe(3));
+      expect(screen.getAllByRole('link', { name: 'Finish your intake' })).toHaveLength(1);
+    });
+
     it('reloads the packet after Generate All succeeds', async () => {
       server.use(packetThatGains122a2());

@@ -484,7 +582,7 @@ describe('FormDashboard', () => {
           calls += 1;
           return calls === 1
             ? HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
-            : HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 });
+            : HttpResponse.json(NOT_SPLIT, { status: 422 });
         })
       );

@@ -537,7 +635,7 @@ describe('FormDashboard', () => {
         http.get('http://localhost:8000/api/forms/packet/', () => {
           calls += 1;
           return calls === 2
-            ? HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 })
+            ? HttpResponse.json(NOT_SPLIT, { status: 422 })
             : HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] });
         })
       );
PATCH
```

The packet-list refusals for income not entered by source carry `step: 'income_info'` through `NOT_SPLIT`. A `NoTableInForce` refusal must show neither a link nor Try Again, a refused Generate All with `page: '/intake'` must show exactly one link to `/intake`, and the three states where two blocks could offer that link must show it once.

- [ ] **Step 6: Run them and watch them fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/api/__tests__/client.test.ts src/components/wizard/__tests__/MeansTestPreview.test.tsx src/pages/__tests__/IntakeWizard.test.tsx src/pages/__tests__/FormDashboard.test.tsx 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: FAIL — `Test Files  4 failed (4)` and `Tests  13 failed | 64 passed (77)`. Nine fail on an assertion as soon as the page settles. The client keeps no pointer (`AssertionError: expected undefined to be '/intake'`), and the preview shows its estimate message instead of the 400's sentence. The dashboard links every packet-list refusal to the intake, gives a refused Generate All no link, and shows two links where one belongs (`to have a length of 1 but got 2`). Review lists no reason. The other four are wizard tests that wait for a reason with a findBy query. Each ends after testing-library's 5000 ms wait with an element-not-found error, such as `Unable to find role="button" and name "Go to Amounts Owed"`. Their describe allows 30 s, so none of them is a test timeout, but load slows them. Four new tests already pass, and the implementer proved each by mutation: "keeps no step or page that is not a string, such as a field error", "waits for income and expenses when the refusal carries no sentence for the filer", "adds no second link back to the intake when the dashboard already offers one" and "adds no second link back to the intake when both the packet list and Generate All are refused". So does the changed "keeps the filer on Review with the reason when Complete fails", which reads only the general message.

- [ ] **Step 7: Keep what a refusal says fixes it**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/api/client.ts b/frontend/src/api/client.ts
index fad69de..e163c96 100644
--- a/frontend/src/api/client.ts
+++ b/frontend/src/api/client.ts
@@ -26,6 +26,7 @@ import type {
   Codebtor,
   GeneratedForm,
   APIError,
+  CompletionError,
   LoginRequest,
   LoginResponse,
   DemoLoginResponse,
@@ -87,21 +88,41 @@ export class APIClientError extends Error {
   details?: Record<string, unknown>;
   /** The response's own `error` sentence, kept even when its `message` is the one shown. */
   serverError?: string;
+  /** Complete's refusal: each thing missing, with the wizard step that fixes it */
+  errors?: CompletionError[];
+  /** The wizard step key that fixes a refusal, when the server names one */
+  step?: string;
+  /** The page (a route) that fixes a refusal, when the server names one */
+  page?: string;

   constructor(
     message: string,
     statusCode: number,
     details?: Record<string, unknown>,
-    serverError?: string
+    serverError?: string,
+    pointers: { errors?: CompletionError[]; step?: string; page?: string } = {}
   ) {
     super(message);
     this.name = 'APIClientError';
     this.statusCode = statusCode;
     this.details = details;
     this.serverError = serverError;
+    this.errors = pointers.errors;
+    this.step = pointers.step;
+    this.page = pointers.page;
   }
 }

+/** A Complete refusal's entry, as long as it names both its step and its sentence */
+function isCompletionError(entry: unknown): entry is CompletionError {
+  return (
+    typeof entry === 'object' &&
+    entry !== null &&
+    typeof (entry as CompletionError).step === 'string' &&
+    typeof (entry as CompletionError).message === 'string'
+  );
+}
+
 /**
  * Parse API error response and throw typed error
  */
@@ -114,11 +135,18 @@ async function handleAPIError(response: Response): Promise<never> {
     throw new APIClientError('An unexpected error occurred. Please try again.', response.status);
   }

+  // What a refusal says fixes it, kept only in the shapes the server sends (step 3a1 spec §4)
+  const errors: unknown = errorData.errors;
   throw new APIClientError(
     errorData.message || errorData.error || 'Request failed',
     response.status,
     errorData.details,
-    errorData.error
+    errorData.error,
+    {
+      errors: Array.isArray(errors) ? errors.filter(isCompletionError) : undefined,
+      step: typeof errorData.step === 'string' ? errorData.step : undefined,
+      page: typeof errorData.page === 'string' ? errorData.page : undefined,
+    }
   );
 }

diff --git a/frontend/src/types/api.ts b/frontend/src/types/api.ts
index d2d0d4d..2578d4a 100644
--- a/frontend/src/types/api.ts
+++ b/frontend/src/types/api.ts
@@ -573,10 +573,22 @@ export interface SOFAReport {
   creditor_payments: SOFACreditorPayment[];
 }

+/** One thing Complete found missing, with the wizard step (a `WIZARD_STEPS` key) that fixes it */
+export interface CompletionError {
+  step: string;
+  message: string;
+}
+
 export interface APIError {
   error: string;
   message: string;
   details?: Record<string, unknown>;
+  /** Complete's refusal: each thing missing, in wizard order */
+  errors?: CompletionError[];
+  /** The wizard step key that fixes a refusal, when one does */
+  step?: string;
+  /** The page (a route) that fixes a refusal, when one does */
+  page?: string;
 }

 // ============================================================================
PATCH
```

`CompletionError` names Complete's entries, and `APIClientError` keeps `errors`, `step` and `page` from the body in the shapes the server sends (spec §4.4), so the wizard and the dashboard can point the filer at the fix.

- [ ] **Step 8: List the reasons on Review**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/wizard/steps/ReviewStep.tsx b/frontend/src/components/wizard/steps/ReviewStep.tsx
index bb10ef2..1741677 100644
--- a/frontend/src/components/wizard/steps/ReviewStep.tsx
+++ b/frontend/src/components/wizard/steps/ReviewStep.tsx
@@ -6,6 +6,7 @@
  */

 import { useEffect } from 'react';
+import { Button } from '../../common';
 import { UPLDisclaimer } from '../../compliance';
 import { UPL_REVIEW_DISCLAIMER } from '../../../constants/upl';
 import type {
@@ -27,6 +28,10 @@ interface ReviewStepProps {
   contractsData: ExecutoryContract[];
   codebtorsData: Codebtor[];
   onValidationChange: (isValid: boolean) => void;
+  /** Each thing Complete found missing, with the wizard step that fixes it when there is one */
+  completionReasons?: { message: string; step?: { number: number; label: string } }[];
+  /** Moves to a wizard step, the way Go Back does */
+  onGoToStep?: (stepNumber: number) => void;
 }

 export function ReviewStep({
@@ -38,6 +43,8 @@ export function ReviewStep({
   contractsData,
   codebtorsData,
   onValidationChange,
+  completionReasons = [],
+  onGoToStep,
 }: ReviewStepProps) {
   // Always valid to proceed from review (unless we add specific checks)
   useEffect(() => {
@@ -58,6 +65,28 @@ export function ReviewStep({

   return (
     <div className="review-step">
+      {/* Below the wizard's alert, which keeps Complete's general message (step 3a1 spec §4.4).
+          A polite live region from the start, so a screen reader reads out the reasons a
+          refused Complete adds to it. */}
+      <div className="review-reasons" aria-live="polite">
+        {completionReasons.length > 0 && (
+          <section className="review-section">
+            <ul className="review-list">
+              {completionReasons.map(({ message, step }, index) => (
+                <li key={index} className="review-list-item">
+                  <span>{message}</span>
+                  {step && (
+                    <Button variant="outline" size="sm" onClick={() => onGoToStep?.(step.number)}>
+                      Go to {step.label}
+                    </Button>
+                  )}
+                </li>
+              ))}
+            </ul>
+          </section>
+        )}
+      </div>
+
       <div className="info-box">
         <h3 className="info-title">Review Your Information</h3>
         <p className="info-message">
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
index f5e9c14..093d03a 100644
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -34,6 +34,7 @@ import type {
   DebtInfo,
   ExecutoryContract,
   Codebtor,
+  CompletionError,
 } from '../types/api';
 import { EXPENSE_FIELDS, INCOME_FIELDS } from '../types/api';

@@ -87,6 +88,8 @@ export function IntakeWizard() {
   const [debtsData, setDebtsData] = useState<Partial<DebtInfo>[]>([]);
   const [contractsData, setContractsData] = useState<ExecutoryContract[]>([]);
   const [codebtorsData, setCodebtorsData] = useState<Codebtor[]>([]);
+  // What Complete last said is missing, listed on Review until the step changes
+  const [completionErrors, setCompletionErrors] = useState<CompletionError[]>([]);

   // =========================================================================
   // Read the session on mount
@@ -274,10 +277,17 @@ export function IntakeWizard() {
     }
   };

+  // Go Back, and the "Go to" button beside each reason Complete gave, move without update_step:
+  // current_step stays where Continue last put it. Leaving Review drops its reasons.
+  const moveToStep = (stepNumber: number) => {
+    setCurrentStepNumber(stepNumber);
+    setCompletionErrors([]);
+  };
+
   const handlePrevious = () => {
     const prevStep = currentStepNumber - 1;
     if (prevStep >= 1) {
-      setCurrentStepNumber(prevStep);
+      moveToStep(prevStep);
       // Load data for previous step if needed
     }
   };
@@ -285,6 +295,7 @@ export function IntakeWizard() {
   const handleComplete = async () => {
     if (pressInFlightRef.current) return;
     pressInFlightRef.current = true;
+    setCompletionErrors([]);

     try {
       // Save the current step immediately. If it fails, do NOT complete.
@@ -305,8 +316,10 @@ export function IntakeWizard() {
         }
       } catch (error) {
         // The filer stays on Review, where WizardLayout shows the reason the context recorded
-        // (DIG-150). If only the means test failed, the intake is already complete, and
-        // pressing Complete again retries both calls.
+        // (DIG-150), and Review lists each thing Complete found missing. If only the means
+        // test failed, the intake is already complete, and pressing Complete again retries
+        // both calls.
+        if (error instanceof APIClientError && error.errors) setCompletionErrors(error.errors);
         console.error('Error completing intake:', error);
       }
     } finally {
@@ -423,6 +436,11 @@ export function IntakeWizard() {
             contractsData={contractsData}
             codebtorsData={codebtorsData}
             onValidationChange={setCanProceed}
+            completionReasons={completionErrors.map((reason) => ({
+              message: reason.message,
+              step: WIZARD_STEPS.find((step) => step.key === reason.step),
+            }))}
+            onGoToStep={moveToStep}
           />
         );

diff --git a/frontend/src/styles/global.css b/frontend/src/styles/global.css
index ddf04b7..9e7afc7 100644
--- a/frontend/src/styles/global.css
+++ b/frontend/src/styles/global.css
@@ -368,6 +368,12 @@ a {
   gap: var(--space-5);
 }

+/* The live region for Complete's reasons is on the step from the start. Empty, it gives back
+   the gap after it, so the step looks as it did. */
+.review-reasons:empty {
+  margin-bottom: calc(-1 * var(--space-5));
+}
+
 .review-section {
   border: 1px solid var(--color-sand);
   background-color: var(--color-paper);
PATCH
```

The wizard keeps the reasons from Complete's rethrown error and hands Review each sentence with its step's number and label; Review lists them in a live region that is always there, each with a "Go to" button that calls `moveToStep`, and the CSS rule keeps an empty region from adding space (spec §4.4, Ruling R4-d).

- [ ] **Step 9: Show the means test's sentence in the preview**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/hooks/useDebouncedMeansTest.ts b/frontend/src/hooks/useDebouncedMeansTest.ts
index 41031b2..8ffb5ee 100644
--- a/frontend/src/hooks/useDebouncedMeansTest.ts
+++ b/frontend/src/hooks/useDebouncedMeansTest.ts
@@ -64,9 +64,11 @@ export function useDebouncedMeansTest({
     } catch (err) {
       if (abortRef.current?.signal.aborted) return;

-      // Gracefully handle incomplete data errors
+      // Gracefully handle incomplete data errors. A 400's `error` is a sentence for the filer
+      // (no median table in force, income not entered by source), which says what stands in
+      // the way better than asking for income they may already have given.
       if (err instanceof APIClientError && err.statusCode === 400) {
-        setStatusMessage(INCOMPLETE_DATA_MESSAGE);
+        setStatusMessage(err.serverError || INCOMPLETE_DATA_MESSAGE);
       } else {
         setStatusMessage(
           'Unable to estimate eligibility right now. This is not an error with your information.'
PATCH
```

A 400 shows its `error` sentence when it has one and the estimate message otherwise, so the preview says what stands in the way (Task 1 review M2).

- [ ] **Step 10: Link the dashboard's refusals to their fix, once**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
index a6fe6fd..772371b 100644
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -37,6 +37,21 @@ function wholeCallRefusal(err: unknown, generic: string): string {
   return err instanceof APIClientError && err.statusCode === 422 ? err.message : generic;
 }

+/** The words of the link to each page a refusal can name as its fix (step 3a1 spec §4.3) */
+const PAGE_LINK_LABELS: Record<string, string> = { '/intake': 'Finish your intake' };
+
+/**
+ * A failed packet list in the filer's words, and whether its refusal names a fix: a wizard step
+ * or a page (step 3a1 spec §4.3). No step fixes one that names neither, such as no median table
+ * in force on the fill date.
+ */
+function loadFailure(err: unknown): { message: string; namesFix: boolean } {
+  return {
+    message: wholeCallRefusal(err, DASHBOARD_ERROR),
+    namesFix: err instanceof APIClientError && err.statusCode === 422 && !!(err.step || err.page),
+  };
+}
+
 const MONTHS = [
   'January',
   'February',
@@ -75,10 +90,13 @@ export function FormDashboard() {
   const [packet, setPacket] = useState<FormType[]>([]);
   const [tables, setTables] = useState<DatedTableUsed[]>([]);
   const [isLoading, setIsLoading] = useState(true);
-  const [error, setError] = useState<string | null>(null);
+  const [error, setError] = useState<{ message: string; namesFix: boolean } | null>(null);
   const [showSurvey, setShowSurvey] = useState(false);
   const [generationErrors, setGenerationErrors] = useState<GenerateAllError[]>([]);
-  const [generateAllRefusal, setGenerateAllRefusal] = useState<string | null>(null);
+  const [generateAllRefusal, setGenerateAllRefusal] = useState<{
+    message: string;
+    page?: string;
+  } | null>(null);
   const [dischargeData, setDischargeData] = useState<DebtClassification[]>([]);

   // Load existing forms on mount
@@ -96,7 +114,7 @@ export function FormDashboard() {
       setTables(loadedPacket.tables);
       setError(null);
     } catch (err) {
-      setError(wholeCallRefusal(err, DASHBOARD_ERROR));
+      setError(loadFailure(err));
     } finally {
       setIsLoading(false);
     }
@@ -139,7 +157,10 @@ export function FormDashboard() {
       trackEvent('form_generated', { form_type: 'all', session_id: session.id });
       setShowSurvey(true);
     } catch (err) {
-      setGenerateAllRefusal(wholeCallRefusal(err, ERROR_GENERIC));
+      setGenerateAllRefusal({
+        message: wholeCallRefusal(err, ERROR_GENERIC),
+        page: err instanceof APIClientError ? err.page : undefined,
+      });
     }
     // Generate All works the means test out again, so the packet may have changed
     try {
@@ -148,7 +169,7 @@ export function FormDashboard() {
       setTables(reloaded.tables);
       setError(null);
     } catch (err) {
-      setError(wholeCallRefusal(err, DASHBOARD_ERROR));
+      setError(loadFailure(err));
     }
   };

@@ -186,6 +207,16 @@ export function FormDashboard() {
   const filedCount = forms.filter((f) => f.status === 'filed').length;
   const generatedCount = forms.filter((f) => packet.includes(f.form_type)).length;
   const totalCount = packet.length;
+  // "Finish your intake" shows at most once, on the first block that offers it: the notice for
+  // an unfinished intake, then a packet-list refusal that names its fix, then the page Generate
+  // All's refusal names (ruling R4-a). The context's status and the server's can disagree.
+  const noticeLinksIntake = session.status !== 'completed';
+  const errorLinksIntake = !noticeLinksIntake && !!error?.namesFix;
+  const refusalPage = generateAllRefusal?.page;
+  const refusalLinkLabel =
+    refusalPage && !(refusalPage === '/intake' && (noticeLinksIntake || errorLinksIntake))
+      ? PAGE_LINK_LABELS[refusalPage]
+      : undefined;

   return (
     <div className="form-dashboard">
@@ -200,7 +231,7 @@ export function FormDashboard() {
       <UPLDisclaimer text={UPL_FORM_DISCLAIMER} variant="banner" />

       {/* Forms are prepared only from an intake the server marked complete (forms step 2 §5.3) */}
-      {session.status !== 'completed' && (
+      {noticeLinksIntake && (
         <div className="form-dashboard-notice">
           <p>
             Your forms are prepared from your finished intake. To finish it, go back to your intake
@@ -214,24 +245,32 @@ export function FormDashboard() {

       {error && (
         <div className="form-dashboard-error" role="alert">
-          <p>{error}</p>
+          <p>{error.message}</p>
           {/* Our own words mean the load failed and may work again; a 422's words name
-              something to fix at the intake, which a retry can't */}
-          {error === DASHBOARD_ERROR ? (
+              something to fix, which a retry can't. Only a refusal that names a step or page
+              has a fix at the intake (ruling R4-b). */}
+          {error.message === DASHBOARD_ERROR ? (
             <Button variant="outline" size="sm" onClick={loadForms}>
               Try Again
             </Button>
           ) : (
-            <Link to="/intake" className="button button--primary">
-              Finish your intake
-            </Link>
+            errorLinksIntake && (
+              <Link to="/intake" className="button button--primary">
+                Finish your intake
+              </Link>
+            )
           )}
         </div>
       )}

       {generateAllRefusal && (
         <div className="form-dashboard-error" role="alert">
-          <p>{generateAllRefusal}</p>
+          <p>{generateAllRefusal.message}</p>
+          {refusalPage && refusalLinkLabel && (
+            <Link to={refusalPage} className="button button--primary">
+              {refusalLinkLabel}
+            </Link>
+          )}
         </div>
       )}

PATCH
```

Generate All's refusal links to the page its body names, the packet list's links to the intake only when its refusal names a step or page, and the first block that offers "Finish your intake" is the only one that shows it (spec §4.4, Rulings R4-a and R4-b).

- [ ] **Step 11: Run the frontend tests again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/api/__tests__/client.test.ts src/components/wizard/__tests__/MeansTestPreview.test.tsx src/pages/__tests__/IntakeWizard.test.tsx src/pages/__tests__/FormDashboard.test.tsx 2>&1 | grep -E '^ FAIL |^[A-Za-z]*Error: |^ +(Test Files|Tests) '
```

Expected: `Test Files  4 passed (4)` and `Tests  77 passed (77)`.

- [ ] **Step 12: Run every gate**

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

Expected: `2123 passed, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  379 passed (379)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 13: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

The journeys were last run on this commit before its last two rounds of fixes. Those rounds changed only what shows after a refused Complete or a refused dashboard call, and no journey reaches either.

- [ ] **Step 14: Commit**

```bash
set -eo pipefail
git add \
  frontend/src/api/__tests__/client.test.ts \
  frontend/src/components/wizard/__tests__/MeansTestPreview.test.tsx \
  backend/apps/intake/tests/test_e2e_intake.py \
  backend/apps/intake/views.py \
  frontend/src/api/client.ts \
  frontend/src/components/wizard/steps/ReviewStep.tsx \
  frontend/src/hooks/useDebouncedMeansTest.ts \
  frontend/src/pages/FormDashboard.tsx \
  frontend/src/pages/IntakeWizard.tsx \
  frontend/src/pages/__tests__/FormDashboard.test.tsx \
  frontend/src/pages/__tests__/IntakeWizard.test.tsx \
  frontend/src/styles/global.css \
  frontend/src/types/api.ts
git commit -F - <<'MSG'
feat(wizard): the Review step lists what Complete is missing, with a way to each step

Complete's 400 names each gap with the wizard step that fixes it, but the
client kept only the general message, so the filer read "Please complete
all required sections before finalizing" without learning which section.

- The client keeps a refusal's pointers: APIClientError gains errors
  (Complete's entries, only those with a string step and message), step
  and page (only when they are strings).
- The wizard keeps the error IntakeContext.completeSession already
  rethrows. Review lists each reason below the general message, with a
  "Go to {step label}" button that moves to that step the way Go Back
  does (no update_step). The list clears when the step changes and when
  Complete is pressed again. It sits in a polite live region that is on
  Review from the start, so a screen reader reads the reasons out, and
  it stays when the filer dismisses the general message.
- calculate_means_test's 400 carries `error` only for IncomeNotSplit and
  NoTableInForce, whose text is a sentence for the filer, as in the forms
  views. Any other ValueError's text is for operations (a new filer with
  no income saved reads "IntakeSession must have income_info..."), so
  that 400 carries only the general `message`.
- The sidebar preview shows a 400's `error` sentence, so a filer during
  a gap between median tables, or with income not entered by source, is
  no longer asked for income they already gave (T1 review M2). A 400
  without one keeps the estimate message. On Review,
  IntakeContext.calculateMeansTest now shows the general message instead
  of operations text for such a 400.
- The dashboard links a refused Generate All to the page its body names
  ("/intake" reads "Finish your intake"), unless the notice for an
  unfinished intake already links there. A refused packet list offers
  "Finish your intake" only when the refusal names a step or page, so a
  missing median table, which no step of the filer's fixes, shows its
  sentence with no link and no retry. The link shows at most once, on
  the first block that offers it, even when the page's copy of the
  intake's status and the server's disagree.

Tests changed with it: test_calculate_means_test_without_income_info
(test_e2e_intake.py) now expects a 400 with only the general message.
The Complete refusal mock in IntakeWizard.test.tsx moves from a list of
strings to the {step, message} entries the server now sends, and the
FormDashboard packet-list refusal mocks for income not entered by source
carry the step the server sends with them.

Refs DIG-181
MSG
git status --short
```

### Task 5: Leave unconfirmed scanned debts off every form

_Built and verified as commit `83b3b71` on `plan/forms-step3a1`._

**Files:**

- Create: `backend/apps/forms/tests/test_unconfirmed_scanned_debts.py`
- Modify: `CLAUDE.md`
- Modify: `backend/apps/eligibility/services/expense_deduction_calculator.py`
- Modify: `backend/apps/eligibility/tests/test_expense_deduction_calculator.py`
- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/intake/models.py`
- Modify: `backend/apps/intake/tests/test_completion.py`
- Modify: `backend/apps/intake/views.py`

**Interfaces:**

- Consumes:
  - `DebtInfo` (`backend/apps/intake/models.py`): `is_draft = models.BooleanField(default=False)`, which is True for a debt read from a scanned document, and `session`, whose related name is `debts`. Before this task nothing in `apps` or `config` defines a manager or a QuerySet, so `DebtInfo.objects` is Django's plain manager.
  - `DraftDebtCreator` (`backend/apps/documents/services/draft_debt.py`), which creates every debt an upload reads with `is_draft=True`.
  - `IntakeSessionViewSet.partial_update` (`backend/apps/intake/views.py`): when the session PATCH carries `debts`, it runs `DebtInfo.objects.filter(session=instance, is_draft=True).update(is_draft=False)`, which confirms every draft of the session. The wizard's Amounts Owed step saves through it.
  - `_save_rows_by_id` (`backend/apps/intake/serializers.py`), which matches each sent row to a stored row through `model.objects.filter(session=session)`.
  - The debt readers in `backend/apps/forms/services/derivations.py`: `_total_secured_debts`, `_total_nonpriority_unsecured`, `_total_debts`, `_total_student_loans`, `_creditor_count_range`, and the `DERIVATIONS` lambdas `has_secured_debts` and `has_nonpriority_debts`. `_total_other_nonpriority`, `_total_debts_range` and the `total_secured_claims` alias read debts only through them.
  - `ExpenseDeductionCalculator._get_priority_debts_monthly` (`backend/apps/eligibility/services/expense_deduction_calculator.py`), the means test's priority-debt deduction.
  - Task 3's `IntakeSessionViewSet.complete`, which collects one `{"step", "message"}` per gap in wizard order (identity, income by source, the Expenses step) and refuses with a 400 when there is any.
  - The `debts` key in `WIZARD_STEPS` (`frontend/src/pages/IntakeWizard.tsx`), labelled "Amounts Owed", which Task 4's Review list turns into a button to that step.
  - For the tests: `load_schema(form_type)` (`apps.forms.schema`) and `resolve(schema, session)` (`apps.forms.services.fill_resolver`), which return a form's values by full field name; `test_completion.py`'s `filer`, `district` and `completed` fixtures, `_session_url`, `_status` and its four sentence constants; `test_expense_deduction_calculator.py`'s `session_with_expenses` fixture, whose IRS priority debt pays $200 a month.
- Produces:
  - `class DebtInfoQuerySet(models.QuerySet)` in `backend/apps/intake/models.py`, with `confirmed()` → `self.filter(is_draft=False)`, and `DebtInfo.objects = DebtInfoQuerySet.as_manager()`, the default manager. `DebtInfo.objects.confirmed()` and `session.debts.confirmed()` are the one accessor for confirmed debts. Step 3b and 3c's row readers will use it too.
  - These readers read through `confirmed()`: the five derivation functions above, the `has_secured_debts` and `has_nonpriority_debts` lambdas, and `ExpenseDeductionCalculator._get_priority_debts_monthly`. `partial_update`, `_save_rows_by_id` and `complete` don't, since each must see drafts.
  - Complete's fifth entry, after the Expenses entry, while `session.debts.filter(is_draft=True).exists()`: `{"step": "debts", "message": "Check the debts read from your documents on the Amounts Owed step."}`.
  - Tests in `backend/apps/forms/tests/test_unconfirmed_scanned_debts.py`: `test_a_scanned_debt_the_filer_has_not_confirmed_counts_in_no_total`, `test_the_petition_estimates_liabilities_from_confirmed_debts_only` and `test_a_filer_whose_only_debts_are_unconfirmed_lists_no_creditors`.
  - `TestExpenseDeductionCalculator::test_a_scanned_priority_debt_the_filer_has_not_confirmed_is_not_deducted` in `test_expense_deduction_calculator.py`.
  - In `test_completion.py`: the `SCANNED_DEBTS` constant, the `_scanned_debt(session)` helper, the `unconfirmed_scanned_debt` case of `test_complete_names_the_step_that_fixes_each_gap`, and `test_saving_the_amounts_owed_step_confirms_a_scanned_debt_so_complete_passes`. `test_complete_lists_every_gap_in_wizard_order` now expects the debts entry last.
  - `CLAUDE.md`: "Document upload sits mid-wizard" says a scanned debt stays off every form until the Amounts Owed step is saved, and that every form and means-test reader goes through `confirmed()`. "Forms need a completed intake" adds the drafts check to what Complete refuses.

**Decisions already made in this task:**

- **The drafts sentence is the spec's, word for word** (§4.2): "Check the debts read from your documents on the Amounts Owed step." Its step is `debts`, the Amounts Owed step's key in `WIZARD_STEPS`, so Task 4's Review list already offers a button to that step and the frontend doesn't change. The entry comes after the Expenses entry, in wizard order.
- **The filter is the second guard (§6).** Complete refuses while a draft remains, because an upload after Complete reopens the intake (`reopen()`) and the filer could then press Complete on Review without passing step 5. Without the refusal, the scanned debt would silently drop out of the totals.
- **Dischargeability and the completion percentage still read every debt** (spec §6, "Not changed"): they read debts but fill no form. The API's reads see drafts too (the session's `prefetch_related("debts")` and nested `debts` field, `DebtViewSet` and `summary`), because the wizard must receive a draft to show it on Amounts Owed for the filer to check.
- **A session completed before 3a1 with a draft keeps `completed`,** and its forms now leave the draft off without any refusal; before this commit they printed it. The spec accepts this gap. There is no backfill, and a Complete pressed from now on refuses.
- **Only the session PATCH carrying `debts` confirms drafts,** and the wizard saves Amounts Owed only that way. A per-item `PATCH /api/intake/debts/{id}/`, `update_step` with a `data` body carrying `debts`, and a session PUT don't clear `is_draft`. Through them the draft stays, and Complete keeps refusing until Amounts Owed is saved. They stay as they are.
- **The manager is the default `objects`, and it filters nothing.** `confirmed()` is a method a reader calls, so related managers (`session.debts`) and every existing query still see drafts. That matters most to `_save_rows_by_id`: if `model.objects` hid drafts, a draft sent back with its id would be created again as a new row, and the PATCH's draft clear would leave a duplicate debt. The implementer checked that the manager alone changes nothing: `manage.py makemigrations --check --dry-run` reported "No changes detected" (a default manager named `objects` stays out of migration state), and the full suite with only the manager added gave `2123 passed, 1 xfailed`, as before.
- **Each reader keeps its call style.** `.confirmed()` goes in front of the existing filter: `DebtInfo.objects.confirmed().filter(...)` and `s.debts.confirmed().filter(...)`. `_total_student_loans`'s line now wraps at 100 columns. `fill_resolver.py`, `registry.py` and the forms views read no debts, and `MeansTest.calculate` reads them only through the deduction calculator.
- **Complete looks for drafts with a plain `session.debts.filter(is_draft=True).exists()`.** No `drafts()` method is added for one caller. The query bypasses Complete's `prefetch_related("debts")`, which costs one query.
- **Which lines the tests check.** 106Sum's debt lines are 2, 3b, 3c and 9d; line 4 is the Schedule I income total. 103B binds no debt rule, so it has no assertion; the task list asked for one and was corrected after the build. Each debt sits at its own power of two, so a total that counts a draft can't match. The only-drafts test has no confirmed debt, because one confirmed debt plus one draft both tick `/1-49` on Form 101 line 18, and a mixed case couldn't tell them apart.
- **The Complete test saves the way Continue does.** It sends a session PATCH with both rows and their ids, then checks that the draft is the same row, now confirmed, that Complete passes, and that Schedule E/F line 6j prints both debts.
- **Every guard has a test that fails without it.** The implementer removed each `confirmed()` call and Complete's check one at a time, and each removal turned at least one of these tests red.
- **Test data is synthetic (G2).** The creditor names come from the personas doc's fictional rename table, Larkfield General Hospital and Brightwater Card Services. The draft priority debt's creditor is the Illinois Department of Revenue, a government creditor. The new forms test's SSN is in the 900 range.
- **Black re-wrapped one test signature at commit time.** The change is whitespace only. The gate counts were measured just before it, and the three test files gave 43 passed on the committed tree.
- **Left as found:** dischargeability still acts on drafts. It sets `is_dischargeable` and `adversary_proceeding_needed` on them and can create `AdversaryProceeding` rows for them. `backend/apps/forms/tests/test_derivations.py:32` uses the SSN `000-00-0000`, outside the 900 range (pre-existing).

- [ ] **Step 1: Write the failing tests**

```python file=backend/apps/forms/tests/test_unconfirmed_scanned_debts.py
"""
A debt read from a scanned document prints on no form until the filer confirms it
(forms step 3a1 spec §6, DIG-163).

Business intent: an upload creates each debt it reads as a draft, which the filer checks on
the Amounts Owed step. Until the filer saves that step, the figures are only what a model
read from a photo, and the filer signs every form under penalty of perjury. So a draft counts
in no total, answers no schedule's question and is not a creditor on the petition.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import DebtInfo, DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="draftdebts", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    # 106Sum line 8 is CMI, which needs income entered by source.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))
    return session


def _debt(session, debt_type, amount, secured=False, draft=False):
    DebtInfo.objects.create(
        session=session,
        creditor_name=f"{debt_type} creditor",
        debt_type=debt_type,
        amount_owed=Decimal(amount),
        is_secured=secured,
        is_draft=draft,
    )


def _resolved(session, form_type):
    return resolve(load_schema(form_type), session)


def test_a_scanned_debt_the_filer_has_not_confirmed_counts_in_no_total(session):
    # Each debt at its own power of two, so a total that counts a draft can't match.
    _debt(session, "auto_loan", "1000", secured=True)
    _debt(session, "student_loan", "2000")
    _debt(session, "credit_card", "4000")
    _debt(session, "auto_loan", "8000", secured=True, draft=True)
    _debt(session, "student_loan", "16000", draft=True)
    _debt(session, "credit_card", "32000", draft=True)

    d = _resolved(session, "schedule_d")
    ef = _resolved(session, "schedule_e_f")
    summary = _resolved(session, "form_106sum")

    assert d["undefined_24"] == "1000.00"
    assert (ef["Total_6f"], ef["Total_6i"], ef["Total_6j"]) == ("2000.00", "4000.00", "6000.00")
    assert (summary["2"], summary["3b"], summary["3c"], summary["9d"]) == (
        "1000.00",
        "6000.00",
        "7000.00",
        "2000.00",
    )


def test_the_petition_estimates_liabilities_from_confirmed_debts_only(session):
    # The draft's cent would move line 20 into the next range up.
    _debt(session, "credit_card", "50000.00")
    _debt(session, "credit_card", "0.01", draft=True)

    assert _resolved(session, "form_101")["Check Box23"] == "/0-50000"


def test_a_filer_whose_only_debts_are_unconfirmed_lists_no_creditors(session):
    _debt(session, "auto_loan", "1000", secured=True, draft=True)
    _debt(session, "credit_card", "2000", draft=True)

    assert _resolved(session, "schedule_d")["check1"] == "/no"
    assert _resolved(session, "schedule_e_f")["check7"] == "/no"
    # Line 18 asks how many creditors; with none confirmed it stays blank.
    assert "Check Box21" not in _resolved(session, "form_101")
```

Each test puts confirmed debts and drafts on one session and resolves the forms through the fill engine, so it checks the printed values, not the derivations one by one. Schedule D, Schedule E/F and 106Sum must print only the confirmed figures, a draft's cent must not move Form 101's liability range, and a filer whose only debts are drafts answers No on both schedules' questions and leaves line 18 blank.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/eligibility/tests/test_expense_deduction_calculator.py b/backend/apps/eligibility/tests/test_expense_deduction_calculator.py
index f8c4633..ac34f58 100644
--- a/backend/apps/eligibility/tests/test_expense_deduction_calculator.py
+++ b/backend/apps/eligibility/tests/test_expense_deduction_calculator.py
@@ -61,6 +61,25 @@ class TestExpenseDeductionCalculator:
         result = calc.calculate()
         assert result.priority_debts_monthly > Decimal("0")

+    def test_a_scanned_priority_debt_the_filer_has_not_confirmed_is_not_deducted(
+        self, session_with_expenses
+    ):
+        # A draft read from a document is only what a model read until the filer saves the
+        # Amounts Owed step (DIG-163), so it never lowers the means test's disposable income.
+        DebtInfo.objects.create(
+            session=session_with_expenses,
+            creditor_name="Illinois Department of Revenue",
+            amount_owed=Decimal("3000"),
+            is_priority=True,
+            debt_type="other",
+            monthly_payment=Decimal("400"),
+            is_draft=True,
+        )
+
+        result = ExpenseDeductionCalculator(session_with_expenses).calculate()
+
+        assert result.priority_debts_monthly == Decimal("200")
+
     def test_empty_session(self, db):
         user = User.objects.create_user(username="emptycalc", password="pass")
         district = District.objects.create(
PATCH
```

The fixture's IRS debt pays $200 a month. The new test adds a draft priority debt paying $400, and the deduction must stay $200.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/tests/test_completion.py b/backend/apps/intake/tests/test_completion.py
index 3f74a68..681fed0 100644
--- a/backend/apps/intake/tests/test_completion.py
+++ b/backend/apps/intake/tests/test_completion.py
@@ -15,6 +15,8 @@ from django.core.management import call_command
 from rest_framework.test import APIClient

 from apps.districts.models import District
+from apps.forms.schema import load_schema
+from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import (
     AssetInfo,
     DebtInfo,
@@ -173,6 +175,7 @@ NAME_AND_ADDRESS = "Enter your name and address on the Your Information step."
 NINE_DIGIT_SSN = "Enter your 9-digit Social Security number on the Your Information step."
 INCOME_BY_SOURCE = "Enter your income by source on the Income step."
 EXPENSES_STEP = "Go through the Expenses step, even if you have no expenses to enter."
+SCANNED_DEBTS = "Check the debts read from your documents on the Amounts Owed step."


 def _no_debtor(session):
@@ -193,6 +196,18 @@ def _expenses_step_never_saved(session):
     session.expense_info.delete()


+def _scanned_debt(session):
+    # What an upload creates: a draft the filer hasn't checked on the Amounts Owed step yet.
+    return DebtInfo.objects.create(
+        session=session,
+        creditor_name="Larkfield General Hospital",
+        debt_type="medical",
+        amount_owed=Decimal("2000.00"),
+        data_source="uploaded_document",
+        is_draft=True,
+    )
+
+
 @pytest.mark.parametrize(
     "gap,step,message",
     [
@@ -200,8 +215,15 @@ def _expenses_step_never_saved(session):
         (_eight_digit_ssn, "debtor_info", NINE_DIGIT_SSN),
         (_income_boxes_all_empty, "income_info", INCOME_BY_SOURCE),
         (_expenses_step_never_saved, "expense_info", EXPENSES_STEP),
+        (_scanned_debt, "debts", SCANNED_DEBTS),
+    ],
+    ids=[
+        "no_name_and_address",
+        "eight_digit_ssn",
+        "no_income_by_source",
+        "no_expenses_step",
+        "unconfirmed_scanned_debt",
     ],
-    ids=["no_name_and_address", "eight_digit_ssn", "no_income_by_source", "no_expenses_step"],
 )
 def test_complete_names_the_step_that_fixes_each_gap(filer, completed, gap, step, message):
     # The filer reads why on Review, with a way to the step that fixes it (DIG-181).
@@ -223,6 +245,7 @@ def test_complete_names_the_step_that_fixes_each_gap(filer, completed, gap, step
 def test_complete_lists_every_gap_in_wizard_order(filer, district):
     client, user = filer
     session = IntakeSession.objects.create(user=user, district=district, current_step=8)
+    _scanned_debt(session)

     response = client.post(_session_url(session, "complete/"))

@@ -231,10 +254,53 @@ def test_complete_lists_every_gap_in_wizard_order(filer, district):
         {"step": "debtor_info", "message": NAME_AND_ADDRESS},
         {"step": "income_info", "message": INCOME_BY_SOURCE},
         {"step": "expense_info", "message": EXPENSES_STEP},
+        {"step": "debts", "message": SCANNED_DEBTS},
     ]
     assert _status(session) == "started"


+def test_saving_the_amounts_owed_step_confirms_a_scanned_debt_so_complete_passes(filer, completed):
+    # An upload after Complete reopens the intake (DIG-163). Until the filer saves the Amounts
+    # Owed step, the scanned debt is on no form, so Complete sends them there first.
+    client, _ = filer
+    completed.status = "in_progress"
+    completed.save()
+    typed = DebtInfo.objects.create(
+        session=completed,
+        creditor_name="Brightwater Card Services",
+        debt_type="credit_card",
+        amount_owed=Decimal("1000.00"),
+    )
+    scanned = _scanned_debt(completed)
+
+    refused = client.post(_session_url(completed, "complete/"))
+    assert refused.status_code == 400
+    assert refused.data["errors"] == [{"step": "debts", "message": SCANNED_DEBTS}]
+
+    # Continue on Amounts Owed sends every row the step shows, each with its id.
+    saved = client.patch(
+        _session_url(completed),
+        {
+            "debts": [
+                {
+                    "id": row.pk,
+                    "creditor_name": row.creditor_name,
+                    "debt_type": row.debt_type,
+                    "amount_owed": str(row.amount_owed),
+                }
+                for row in (typed, scanned)
+            ]
+        },
+        format="json",
+    )
+    assert saved.status_code == 200
+
+    scanned.refresh_from_db()  # the same row, now confirmed
+    assert scanned.is_draft is False
+    assert client.post(_session_url(completed, "complete/")).status_code == 200
+    assert resolve(load_schema("schedule_e_f"), completed)["Total_6j"] == "3000.00"
+
+
 # ── An edit after Complete reopens the intake ─────────────────────────


PATCH
```

`_scanned_debt` creates what an upload creates. Complete must name the Amounts Owed step for it, alone on a completed intake and last on an empty one. The last test refuses Complete, saves the Amounts Owed step's rows with their ids, and then requires the same row confirmed, Complete to pass and line 6j to print both debts.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=line -rN apps/forms/tests/test_unconfirmed_scanned_debts.py apps/eligibility/tests/test_expense_deduction_calculator.py apps/intake/tests/test_completion.py -q -p no:cacheprovider 2>&1 | tail -20
```

Expected: FAIL — `7 failed, 36 passed`. Every form and the means test still count the drafts. The draft's cent moves Form 101's liability range up (`assert '/50001-100000' == '/0-50000'`), a filer whose only debts are drafts answers Yes on Schedule D's question (`assert '/yes' == '/no'`), and the deduction adds the draft's $400 (`assert Decimal('600.00') == Decimal('200')`). The totals test fails too. Complete still completes an intake that holds a draft (`assert 200 == 400`), and the order test gets a list that ends at the Expenses entry.

- [ ] **Step 3: Add the accessor for confirmed debts**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/models.py b/backend/apps/intake/models.py
index 3213fcf..131f814 100644
--- a/backend/apps/intake/models.py
+++ b/backend/apps/intake/models.py
@@ -405,6 +405,16 @@ class AssetInfo(models.Model):
         return float(self.current_value - self.amount_owed)


+class DebtInfoQuerySet(models.QuerySet):
+    def confirmed(self):
+        """The debts the filer has confirmed, without the drafts read from scanned documents.
+
+        A scanned debt stays a draft until the filer saves the Amounts Owed step (DIG-163).
+        Every reader that feeds a form or the means test reads through this.
+        """
+        return self.filter(is_draft=False)
+
+
 class DebtInfo(models.Model):
     """Creditor and amounts owed information (trauma-informed language)."""

@@ -542,6 +552,8 @@ class DebtInfo(models.Model):
     created_at = models.DateTimeField(auto_now_add=True)
     updated_at = models.DateTimeField(auto_now=True)

+    objects = DebtInfoQuerySet.as_manager()
+
     class Meta:
         db_table = "debt_info"
         ordering: ClassVar[list[str]] = ["priority_classification", "-amount_owed"]
PATCH
```

`DebtInfoQuerySet.confirmed()` leaves out the drafts, and `as_manager()` makes it `DebtInfo`'s default manager, so the method works on `DebtInfo.objects` and on `session.debts` while every existing query keeps seeing drafts (§6, "One accessor").

- [ ] **Step 4: Read every form and means-test reader through it**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/eligibility/services/expense_deduction_calculator.py b/backend/apps/eligibility/services/expense_deduction_calculator.py
index 4629e8b..7d36445 100644
--- a/backend/apps/eligibility/services/expense_deduction_calculator.py
+++ b/backend/apps/eligibility/services/expense_deduction_calculator.py
@@ -106,7 +106,7 @@ class ExpenseDeductionCalculator:
         from apps.intake.models import DebtInfo

         zero = Decimal("0")
-        priority = DebtInfo.objects.filter(session=self.session, is_priority=True)
+        priority = DebtInfo.objects.confirmed().filter(session=self.session, is_priority=True)
         return sum((d.monthly_payment or zero for d in priority), zero)

     def _get_cmi(self) -> Decimal:
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index 9b05984..b253e4f 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -114,7 +114,7 @@ def _total_assets(session: IntakeSession) -> str:
 def _total_secured_debts(session: IntakeSession) -> str:
     from apps.intake.models import DebtInfo

-    qs = DebtInfo.objects.filter(session=session, is_secured=True)
+    qs = DebtInfo.objects.confirmed().filter(session=session, is_secured=True)
     return _fmt(_sum_encrypted(qs, "amount_owed"))


@@ -128,14 +128,14 @@ def _total_nonpriority_unsecured(session: IntakeSession) -> str:
     """
     from apps.intake.models import DebtInfo

-    qs = DebtInfo.objects.filter(session=session, is_secured=False)
+    qs = DebtInfo.objects.confirmed().filter(session=session, is_secured=False)
     return _fmt(_sum_encrypted(qs, "amount_owed"))


 def _total_debts(session: IntakeSession) -> str:
     from apps.intake.models import DebtInfo

-    qs = DebtInfo.objects.filter(session=session)
+    qs = DebtInfo.objects.confirmed().filter(session=session)
     return _fmt(_sum_encrypted(qs, "amount_owed"))


@@ -224,7 +224,9 @@ def _total_student_loans(session: IntakeSession) -> str:
     """
     from apps.intake.models import DebtInfo

-    qs = DebtInfo.objects.filter(session=session, is_secured=False, debt_type="student_loan")
+    qs = DebtInfo.objects.confirmed().filter(
+        session=session, is_secured=False, debt_type="student_loan"
+    )
     return _fmt(_sum_encrypted(qs, "amount_owed"))


@@ -282,7 +284,7 @@ def _range(figure, ranges) -> str:
 def _creditor_count_range(session: IntakeSession) -> str:
     from apps.intake.models import DebtInfo

-    count = DebtInfo.objects.filter(session=session).count()
+    count = DebtInfo.objects.confirmed().filter(session=session).count()
     return _range(count, _CREDITOR_RANGES) if count else ""


@@ -592,9 +594,9 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "has_executory_contracts": lambda s: _yes_if_any(s.executory_contracts.all()),
     "has_codebtors": lambda s: _yes_if_any(s.codebtors.all()),
     # Schedules D and E/F: the section questions and E/F's line 6 totals
-    "has_secured_debts": lambda s: _yes_if_any(s.debts.filter(is_secured=True)),
+    "has_secured_debts": lambda s: _yes_if_any(s.debts.confirmed().filter(is_secured=True)),
     # Every unsecured debt is nonpriority until priority is asked (OQ-3), as on line 6j.
-    "has_nonpriority_debts": lambda s: _yes_if_any(s.debts.filter(is_secured=False)),
+    "has_nonpriority_debts": lambda s: _yes_if_any(s.debts.confirmed().filter(is_secured=False)),
     "total_student_loans": _total_student_loans,
     "total_other_nonpriority": _total_other_nonpriority,
     # Form 101 lines 18-20
PATCH
```

The five derivation functions, the two section-question lambdas and the priority-debt deduction call `confirmed()` before their own filter, so a draft counts in no form and not in the means test.

- [ ] **Step 5: Refuse Complete while a draft remains**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/views.py b/backend/apps/intake/views.py
index bf2ca24..9f1781c 100644
--- a/backend/apps/intake/views.py
+++ b/backend/apps/intake/views.py
@@ -216,6 +216,16 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
                 }
             )

+        # A scanned debt stays off the forms until the filer saves the Amounts Owed step
+        # (DIG-163). An upload after Complete reopens the intake, and Review is one press away.
+        if session.debts.filter(is_draft=True).exists():
+            errors.append(
+                {
+                    "step": "debts",
+                    "message": "Check the debts read from your documents on the Amounts Owed step.",
+                }
+            )
+
         if errors:
             return Response(
                 {
PATCH
```

Complete adds the Amounts Owed entry after the Expenses entry while any debt of the session is a draft (§4.2, §6).

- [ ] **Step 6: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest --tb=line -rN apps/forms/tests/test_unconfirmed_scanned_debts.py apps/eligibility/tests/test_expense_deduction_calculator.py apps/intake/tests/test_completion.py -q -p no:cacheprovider 2>&1 | tail -20
```

Expected: `43 passed`.

- [ ] **Step 7: Say what happens to a scanned debt in CLAUDE.md**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 13748c1..a882ade 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -28,7 +28,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data. It reads the median table in force on today's real date, not the tests' pinned one, and when none is (from November 1, 2026 until the November table is loaded) it prints a message naming `docs/REFERENCE_TABLES.md` and changes nothing, so even `--reset` leaves the existing personas. Personas seeded before income was stored by source must be re-created with `seed_demo_data --reset` (migration 0014 leaves their totals unsplit, and a plain re-run skips existing users).
 - **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
 - **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 > median_income_threshold`, through `is_above_median` (`apps/eligibility/cmi.py`), the means test's own comparison, so income exactly at the median counts as below (DIG-136). Never read `above_median_calculated`: a row calculated before DIG-128 was fixed can still carry a stale True. 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. Generate All, Generate, Regenerate, the download of an unfiled form and the packet list of a completed intake work the means test out again from the stored intake first (`_recalculate_means_test` in `apps/forms/views.py`), so a stale `MeansTest` row never decides the packet (DIG-160); an unfinished intake's packet list reads the stored row. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words, and so are income not entered by source (`IncomeNotSplit`) and no median table in force on the fill date (`NoTableInForce`, which logs the table, the date and the district); any other failure is a 500 logged by exception type only.
-- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key: no `DebtorInfo` row (the name-and-address sentence; the fields themselves aren't checked) or an SSN that isn't 9 digits (the registry's own `_needs_ssn`, so Complete and Forms 101 and 121 say the same thing), income not entered by source (`IncomeNotSplit`, no income row included), and an Expenses step never saved (no `ExpenseInfo` row). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. A forms refusal also carries the `step` (a wizard step key) or `page` (a route) that fixes it, when the exception names one: `PreconditionMissing.step`, `IncomeNotSplit.step` (`income_info`) and `IntakeNotFinished.page` (`/intake`); "already filed", "not in your packet" and `NoTableInForce` carry neither, and the key is absent, never null. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
+- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key: no `DebtorInfo` row (the name-and-address sentence; the fields themselves aren't checked) or an SSN that isn't 9 digits (the registry's own `_needs_ssn`, so Complete and Forms 101 and 121 say the same thing), income not entered by source (`IncomeNotSplit`, no income row included), an Expenses step never saved (no `ExpenseInfo` row), and a scanned debt the filer hasn't confirmed (a `DebtInfo` with `is_draft`, step `debts`; see "Document upload sits mid-wizard"). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. A forms refusal also carries the `step` (a wizard step key) or `page` (a route) that fixes it, when the exception names one: `PreconditionMissing.step`, `IncomeNotSplit.step` (`income_info`) and `IntakeNotFinished.page` (`/intake`); "already filed", "not in your packet" and `NoTableInForce` carry neither, and the key is absent, never null. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
@@ -57,7 +57,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **OCR provider is config-driven** — `_get_processor()` branches on `settings.OCR_PROVIDER` (`openai` | `gemini`) and lazy-imports the provider, so a missing SDK/key surfaces at OCR time, not app boot. `OCR_MODEL` empty ⇒ the provider's own default. Don't hardcode a provider.
 - **`openai_provider.py`, never `openai.py`** — a module named `openai.py` inside `providers/` would shadow the installed `openai` package.
 - **Prod throttling lives in `production.py`, not `base.py`** — base defines only the `auth` scope (`30/minute`); production adds `DEFAULT_THROTTLE_CLASSES` with `anon: 60/minute`, `user: 120/minute`, `auth: 5/minute`. Reading base alone wrongly concludes endpoints are unthrottled — polling ~14 documents exhausts `user` fast.
-- **Document upload sits mid-wizard** — the flow is `login → /intake` step 1 → `/documents` → `/intake` steps 2–8. A scanned bill or credit report pre-fills Amounts Owed; a pay stub supplies only Schedule I's employer name (`IngestedAggregate` `paystub.employer_name`), never an amount and never the Income step: every income box prints what was typed on the Income step. The aggregator still stores `paystub.gross`, which no form reads (pre-fill is DIG-176). `IntakeWizard.handleNext` detours when `nextStep === 2`. Nothing currently links back to `/documents` after a skip. The persona journeys pass the detour with `DocumentsPage.skip()` (`e2e/pages/documents.page.ts`) after step 1; `scanned-bill-journey` uploads with `uploadBill()` and clicks Continue.
+- **Document upload sits mid-wizard** — the flow is `login → /intake` step 1 → `/documents` → `/intake` steps 2–8. A scanned bill or credit report pre-fills Amounts Owed; a pay stub supplies only Schedule I's employer name (`IngestedAggregate` `paystub.employer_name`), never an amount and never the Income step: every income box prints what was typed on the Income step. A scanned debt is a draft (`is_draft`) and stays off every form and out of the means test until the filer saves the Amounts Owed step, whose session PATCH carrying `debts` clears every draft of the session; Complete refuses while one remains (DIG-163). Every reader that feeds a form or the means test reads through `DebtInfo.objects.confirmed()` or `session.debts.confirmed()`, and a new one must too; dischargeability, the completion percentage and the API's reads still see drafts, so the wizard can show them. The aggregator still stores `paystub.gross`, which no form reads (pre-fill is DIG-176). `IntakeWizard.handleNext` detours when `nextStep === 2`. Nothing currently links back to `/documents` after a skip. The persona journeys pass the detour with `DocumentsPage.skip()` (`e2e/pages/documents.page.ts`) after step 1; `scanned-bill-journey` uploads with `uploadBill()` and clicks Continue.
 - **`updateCurrentStep` is POST `/intake/sessions/{id}/update_step/`** — _not_ the PATCH that saves step data. Mocking the PATCH to assert step advancement silently captures the wrong call and passes vacuously.
 - **Upload is synchronous despite the 202** — `views.py` uses `with ThreadPoolExecutor(...)`, whose `__exit__` calls `shutdown(wait=True)`, so `{"status": "processing"}` is returned _after_ OCR completes and holds a gunicorn worker. No `Future` is retained — that's the tell.
 - **PDFs: text layer first, then up to 3 scanned pages** — `processor.py` runs `opendataloader_pdf.convert(..., format="markdown", image_output="off", include_header_footer=True)` with no hybrid arguments. Text of at least `_MIN_TEXT_LENGTH` (30) characters goes to the text prompt; otherwise `_pdf_to_page_images()` sends up to `_MAX_SCANNED_PAGES` (3) JPEG pages to vision, and a PDF with no pages fails. Without `image_output="off"` a scan's image placeholders reach the text prompt; without `include_header_footer=True` the letterhead naming the creditor is dropped.
PATCH
```

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

Expected: `2129 passed, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  379 passed (379)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

This task changes only the backend and no page flow, so the journeys don't run: the seed creates no drafts, every journey but one skips the upload, and `scanned-bill-journey` saves the Amounts Owed step, which confirms its draft, and never reaches Review.

- [ ] **Step 9: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_unconfirmed_scanned_debts.py \
  CLAUDE.md \
  backend/apps/eligibility/services/expense_deduction_calculator.py \
  backend/apps/eligibility/tests/test_expense_deduction_calculator.py \
  backend/apps/forms/services/derivations.py \
  backend/apps/intake/models.py \
  backend/apps/intake/tests/test_completion.py \
  backend/apps/intake/views.py
git commit -F - <<'MSG'
fix(forms): leave unconfirmed scanned debts off every form

An upload creates each debt it reads as a draft (is_draft) for the filer to
check on the Amounts Owed step, but no forms reader filtered drafts, and
neither did the means test's priority-debt deduction. A scanned figure the
filer never confirmed counted in every debt total, the petition's creditor
and liability ranges and the means test (forms step 3a1 spec §6).

- DebtInfo's default manager now comes from a QuerySet with confirmed()
  (filter(is_draft=False)), so DebtInfo.objects.confirmed() and
  session.debts.confirmed() are the one accessor. It is named objects and
  changes no existing query by itself (no migration).
- Every reader that feeds a form or the means test reads through it: the
  Schedule D, E/F and 106Sum totals (106Sum 2, 3b, 3c and 9d), the D and
  E/F section questions, Form 101's creditor count and liability ranges,
  and the priority-debt deduction. Dischargeability, the completion
  percentage and the API's reads still see drafts, so the wizard can show
  them for the filer to check.
- Complete refuses while a draft remains, naming the Amounts Owed step
  after the expenses entry: "Check the debts read from your documents on
  the Amounts Owed step." An upload after Complete reopens the intake, and
  without the refusal the filer could press Complete on Review and the
  scanned debt would silently drop out of the totals. Saving the Amounts
  Owed step, whose session PATCH carries debts, confirms every draft.

Tests: a confirmed debt and a draft in each category, each at its own
power of two, print only the confirmed figures on Schedule D, E/F and
106Sum; the draft's cent never moves Form 101's liability range; a filer
whose only debts are drafts answers No on both schedules' questions and
leaves line 18 blank; a draft priority debt is not deducted; Complete names
the Amounts Owed step for a draft, after the expenses entry; and once the
step is saved, the same row is confirmed, Complete passes and the debt
prints. test_complete_lists_every_gap_in_wizard_order gains a draft so it
checks the new entry's place.

CLAUDE.md: "Document upload sits mid-wizard" says a scanned debt stays off
every form until the Amounts Owed step is saved and that form and means-test
readers go through confirmed(); "Forms need a completed intake" adds the
drafts check to what Complete refuses.

Refs DIG-163
MSG
git status --short
```

### Task 6: Allow one save at a time on a session

_Built and verified as commit `a1b7ee4` on `plan/forms-step3a1`._

**Files:**

- Create: `backend/apps/intake/locking.py`
- Create: `backend/apps/intake/tests/test_session_lock.py`
- Create: `backend/config/settings/test_postgres.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `CLAUDE.md`
- Modify: `backend/apps/documents/views.py`
- Modify: `backend/apps/intake/views.py`
- Modify: `backend/conftest.py`
- Modify: `backend/pyproject.toml`

**Interfaces:**

- Consumes:
  - `IntakeSession` and `IntakeSession.reopen()` (`backend/apps/intake/models.py`), which sets a completed session back to `in_progress`.
  - In `backend/apps/intake/views.py`:
    - `IntakeSessionViewSet`. Its PUT is DRF's own `update`, not overridden. Its `partial_update` is `@transaction.atomic` and runs Task 5's draft clear after the save. `update_step` and `complete` (Task 3's and Task 5's checks, then a full `session.save()`) are not atomic.
    - `_save_list(session, model, row_serializer, rows)`, the contracts and codebtors PUT, which runs `_save_rows_by_id` and `session.reopen()` inside `transaction.atomic()`.
    - The contracts and codebtors POST (inside the `contracts` and `codebtors` actions) and `delete_contract` and `delete_codebtor`.
    - `AssetViewSet` and `DebtViewSet` `perform_create`, `perform_update` and `perform_destroy`, and `_assert_session_owned(session, user)`, which imports `PermissionDenied` inside the function.
  - `IntakeSessionSerializer.update` (`backend/apps/intake/serializers.py`), which calls `instance.save()` on the session before `_save_rows_by_id` reads the stored rows.
  - In `backend/apps/documents/views.py`:
    - `upload`, which waits for `_run_processing(doc_id)` through `with ThreadPoolExecutor(max_workers=1)`.
    - `_run_processing`, which calls `_get_processor()` and `processor.process(...)` (the hosted model), then `_record_findings(doc, result)`, `ocr.save()` and `AggregateIngestionService.recalculate(session_id)`, which logs and swallows its errors.
    - `DocumentViewSet.validate`, the correction of a scanned bill or pay stub.
  - `backend/config/settings/test.py` (sqlite `:memory:`; `env` is `base.py`'s `environ.Env`), the root `backend/conftest.py`'s `collect_ignore`, and `[tool.pytest.ini_options]` in `backend/pyproject.toml`, whose `python_files` includes `test_*.py`.
  - CI's `backend-test` job (`.github/workflows/ci.yml`): its `postgres` service, the job-level `DATABASE_URL`, and the "Run tests with coverage" step.
  - `DATABASE_URL` in `.claude/forms-step3a1.env`, which names the Postgres database the plan's setup created.
- Produces:
  - `lock_session(session_id: int) -> IntakeSession` in `backend/apps/intake/locking.py`: `IntakeSession.objects.select_for_update().get(pk=session_id)`. Call it only inside `transaction.atomic()`, after `get_object()`, and before reading anything the write depends on.
  - These now lock the session first: the session PATCH and PUT, through a new `@transaction.atomic` `IntakeSessionViewSet.update` that `partial_update` goes through; `update_step` and `complete`, both now atomic, with `complete` saving `update_fields=["status", "completed_at"]`; `_save_list`; the contracts and codebtors POST and DELETE; the `AssetViewSet` and `DebtViewSet` writes, whose `perform_update` calls the new `_lock_for_row_update(serializer)`; `validate`; and `_run_processing`'s write of the findings.
  - `config.settings.test_postgres` (`backend/config/settings/test_postgres.py`): `from .test import *`, `DATABASES["default"] = env.db("DATABASE_URL")` and a 10-second `lock_timeout`. The root conftest's `collect_ignore` lists it.
  - The pytest marker `postgres`, registered in `backend/pyproject.toml`.
  - Tests in `backend/apps/intake/tests/test_session_lock.py`, every one marked `postgres`, skipped unless `connection.vendor == "postgresql"`, and run with `django_db(transaction=True)`:
    - `test_two_saves_of_the_same_new_contract_store_it_once`, which patches `apps.intake.views._save_rows_by_id` to pause the first save before it commits;
    - `test_an_uploads_scanned_debt_waits_for_a_save_in_progress_then_is_stored`;
    - `test_an_edit_made_while_complete_runs_reopens_the_intake`;
    - `test_a_pay_stub_read_while_complete_runs_reopens_the_intake`;
    - `test_a_save_keeps_the_step_a_continue_stored_while_it_waited`;
    - `test_a_row_deleted_while_its_update_waited_is_not_found_and_stays_deleted`, one case for assets and one for debts;
    - `test_a_row_moved_to_another_session_while_its_update_waited_is_not_found`;
    - `test_every_intake_write_waits_for_a_save_in_progress`, one case per key of `WRITES` (17).
  - CI's `backend-test` step "Run the Postgres-only tests", after the coverage step: `working-directory: backend`, `DJANGO_SETTINGS_MODULE: config.settings.test_postgres`, `pytest -m postgres --tb=short -q -rs`.
  - `CLAUDE.md`: a new gotcha "Saves lock the session", after "Nested debts and assets save by id". "Forms need a completed intake" says a new intake-data write path locks the session first.

**Decisions already made in this task:**

- **Test 1 is two concurrent contracts PUTs (ruling R6-a).** Two session PATCHes carrying the same new debt already run one after the other without the lock. `IntakeSessionSerializer.update` saves the session row before `_save_rows_by_id` reads the stored rows, and that row lock lasts until `partial_update` commits. So the PATCH version passed with the lock removed and proved nothing. `_save_list`, the contracts and codebtors PUT, writes no session row, so a double Continue on step 6 really stored the new contract twice. Spec §7's "two concurrent saves of the same new rows store each row once" still holds, and the session PATCH is covered by the write-path test and the stale-step test.
- **`config/settings/test_postgres.py` keeps its name (ruling R6-b),** and the root conftest's `collect_ignore` stops pytest from collecting it. The name matches `python_files` (`test_*.py`), so a sqlite run imported it as a test module. Its `DATABASES["default"] = ...` then replaced the running settings' database with a dict that lacks `ATOMIC_REQUESTS`: the first full sqlite run had 285 failures and 20 errors, all `KeyError: 'ATOMIC_REQUESTS'`. The conftest's `pytest_configure`, which sets `settings.DJANGO_SETTINGS_MODULE` to `config.settings.test`, stays: pytest-django reads `--ds` or `DJANGO_SETTINGS_MODULE` before it runs, so either one reaches Postgres (`connection.vendor` is `postgresql`), and with neither the run stays on sqlite.
- **`test_postgres` sets a 10-second `lock_timeout`,** so a deadlock fails its test instead of hanging the run, the teardown flush included. The tests wait `WAIT` (5 seconds) for a request, under it, and a timed-out lock surfaces as `LockNotAvailable`, which fails the test's status or row assertions. `setdefault("OPTIONS", {})` keeps any OPTIONS that `DATABASE_URL` carries, such as `sslmode`.
- **Both `recalculate` calls get their own savepoint.** `AggregateIngestionService.recalculate` swallows its errors. Inside the worker's new atomic block, one failed statement on Postgres would roll the findings back unseen. The implementer's probe ran `_run_processing` with a `recalculate` that hit `SELECT 1/0`: without the savepoint it left no draft, the OCR row stuck at processing and nothing logged; with it, the draft and COMPLETED were stored. The aggregates keep their previous values until the next upload or correction recomputes them.
- **A row deleted or moved while its per-item update waited is a 404.** `_lock_for_row_update` locks the row's session and the session it moves to, in id order, so two moves between the same sessions can't wait on each other, and then reads the row again. A row another save deleted meanwhile raises `NotFound`. Before this task the full save re-created it, and with the re-read alone it raised `DoesNotExist`, a 500. A row moved to a session outside the locked set is also a 404, because locking that session now would break id order. `NotFound` is imported inside the function, as `_assert_session_owned` imports `PermissionDenied`. The wizard never calls these endpoints; it saves rows through the session PATCH.
- **The test module fails loud.** If `config.settings.test_postgres` ever reaches anything but Postgres, the module raises `RuntimeError` at import, so collection errors and CI's step fails instead of passing on 25 skips. Under the default settings the check does nothing and every test skips with its reason. `django.conf.settings` is imported as `django_settings`, as in `apps/forms/tests/test_checks.py`, because two tests take pytest-django's `settings` fixture. The implementer proved the check by pointing `DATABASE_URL` at a sqlite file for one run: collection stopped on `RuntimeError: config.settings.test_postgres reached sqlite, not Postgres`, exit 2.
- **An upload locks only inside its worker's write.** The request thread waits for the worker (`with ThreadPoolExecutor(...)`), so a lock taken in the request deadlocks on its own worker, and a lock held across the hosted-model call makes every save wait out OCR. The worker takes the lock after `processor.process(...)`, around the findings, `ocr.save()` and `recalculate`; the block also covers the `result.error` branch, so a failed read takes the lock briefly. The implementer's mutations: a lock in the request thread failed the scanned-debt test with `LockNotAvailable`, and the run ended in 26 seconds instead of hanging; a lock taken before `process()` let the draft be stored before the save could run.
- **Every path locks after `get_object()`,** so another user's session is still a 404, and before it reads anything its write depends on. `update_step` and `complete` lock on the `get_object()` line itself, so a 400 for a bad step number holds the lock briefly. `validate` locks after its 400 checks and then re-reads the OCR row, so its merge reads the stored findings. A session PATCH now runs `get_object()` three times (`partial_update`, `update` and DRF's `update`).
- **What the tests catch.** After the build, the implementer unlocked every path but kept the tests' real holder. 14 of the 25 tests failed, but only 7 of the 17 write cases: contract and codebtor DELETE, asset and debt PATCH and DELETE, and the scanned bill correction. The other 10 wait on implicit row locks: the session PATCH, PUT, Continue and Complete on their own UPDATE of the session row, and the contracts and codebtors PUT and POST and the asset and debt POST on the foreign-key check of the row they insert. The scanned-debt test passes the same way. Step 3's red, run against the views before this task, fails the same 14 tests. So the write-path test proves that each write waits and runs inside a transaction (Postgres refuses `select_for_update` outside one), not that each calls `lock_session`. Removing only `update()`'s lock fails the stale-step test (`8 == 5`), and removing only the worker's lock fails the pay-stub test. These results are in the commit body.
- **Coverage falls to about 95%** (94.98%, from Task 5's 96.59%). The sqlite run counts the Postgres-only code without running it: it misses 175 statements of `test_session_lock.py`, all 3 of `test_postgres.py`, and the 3 lines of `_lock_for_row_update`'s two 404 branches. The floor stays at 90%.
- **There is no sqlite red.** `select_for_update` does nothing on sqlite, so the sqlite suite can't see a missing lock, and no existing test changes. Under sqlite the new tests skip, with the reason under `-rs`.
- **Test data is synthetic (G2):** the SSN 900-12-3456, the phone 312-555-0100, and fictional creditor, landlord, gym and employer names.
- **Left as found:** the dischargeability action (FormDashboard posts it on every load) updates `DebtInfo` flags and creates `AdversaryProceeding` rows without the lock; session DELETE can deadlock against a locked save, since Django deletes the child rows first; and the upload worker never closes its database connection, so the tests wrap `_run_processing` to close it.

- [ ] **Step 1: Add the session lock and the settings that reach Postgres**

```python file=backend/apps/intake/locking.py
"""One save at a time on an intake session (DIG-188)."""

from .models import IntakeSession


def lock_session(session_id: int) -> IntakeSession:
    """Lock the session's row until the transaction ends, and return the session as stored.

    Every write to a session's intake data calls this first, inside the same
    ``transaction.atomic()`` block as the write, so a second save of the same session waits
    for the first to commit and then reads what it stored. Postgres refuses it outside a
    transaction; sqlite ignores it, so only test_session_lock.py on Postgres proves it.
    """
    return IntakeSession.objects.select_for_update().get(pk=session_id)
```

`lock_session` comes first because the tests call it themselves to stand in for a save in progress. It locks nothing until a write calls it.

```python file=backend/config/settings/test_postgres.py
from .test import *

# The tests marked postgres (apps/intake/tests/test_session_lock.py) need a real row lock,
# and select_for_update does nothing on sqlite. CI runs them against the backend job's
# Postgres service; locally, DATABASE_URL names a Postgres you can create a test database on.
DATABASES["default"] = env.db("DATABASE_URL")
# A save that deadlocks fails its test after 10 seconds instead of hanging the run.
DATABASES["default"].setdefault("OPTIONS", {})["options"] = "-c lock_timeout=10000"
```

```bash
git apply <<'PATCH'
diff --git a/backend/conftest.py b/backend/conftest.py
index e000e1b..daa2154 100644
--- a/backend/conftest.py
+++ b/backend/conftest.py
@@ -12,6 +12,9 @@ collect_ignore = [
     "test_fee_waiver_manual.py",
     "test_debt_classification.py",
     "test_schedule_ab_logic.py",
+    # A settings module, not tests: its name matches python_files, and importing it during
+    # collection would point the running settings' default database at DATABASE_URL.
+    "config/settings/test_postgres.py",
 ]


diff --git a/backend/pyproject.toml b/backend/pyproject.toml
index d2976ca..ea9880c 100644
--- a/backend/pyproject.toml
+++ b/backend/pyproject.toml
@@ -54,3 +54,6 @@ known-first-party = ["config", "apps"]
 DJANGO_SETTINGS_MODULE = "config.settings.test"
 python_files = ["tests.py", "test_*.py", "*_tests.py"]
 addopts = "-v --tb=short"
+markers = [
+    "postgres: needs a real Postgres row lock; run with DJANGO_SETTINGS_MODULE=config.settings.test_postgres pytest -m postgres",
+]
PATCH
```

`config.settings.test_postgres` is `config.settings.test` with the database taken from `DATABASE_URL` and a 10-second `lock_timeout`. The conftest keeps pytest from collecting it as a test module, and the `postgres` marker lets `-m postgres` select the tests that need it.

- [ ] **Step 2: Write the failing tests**

```python file=backend/apps/intake/tests/test_session_lock.py
"""One save at a time on an intake session (DIG-188).

Business intent: a filer can send two saves of one list at once (Continue pressed twice),
an upload can write a scanned debt while the filer saves, and Complete can run while a save
or an upload's findings arrive. Every write to a session's intake data locks the session
first, so they run one after the other: a new row is stored once, a scanned debt waits for
the save in progress instead of slipping into it, and an edit or a pay stub that lands
while Complete runs still sends the filer back to press Complete again.

select_for_update does nothing on sqlite, so these tests run only on Postgres:
    DJANGO_SETTINGS_MODULE=config.settings.test_postgres pytest -m postgres
Each request runs on its own thread and database connection, as two browser requests do.
A request "waits" when Postgres reports its connection waiting on a lock.
"""

import threading
import time
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.conf import settings as django_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, transaction
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.documents import views as document_views
from apps.documents.models import (
    DocumentType,
    IngestedAggregate,
    OCRResult,
    OCRStatus,
    UploadedDocument,
)
from apps.documents.services.processor import ExtractionResult
from apps.intake import views as intake_views
from apps.intake.locking import lock_session
from apps.intake.models import (
    AssetInfo,
    Codebtor,
    DebtInfo,
    DebtorInfo,
    ExecutoryContract,
    ExpenseInfo,
    IncomeInfo,
    IntakeSession,
)
from apps.users.models import User

# CI runs these with config.settings.test_postgres. If those settings ever reach anything
# but Postgres, stop the run here instead of letting every test skip quietly.
if (
    django_settings.SETTINGS_MODULE == "config.settings.test_postgres"
    and connection.vendor != "postgresql"
):
    raise RuntimeError(f"config.settings.test_postgres reached {connection.vendor}, not Postgres")

pytestmark = [
    pytest.mark.postgres,
    pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason=(
            "needs Postgres: select_for_update does nothing on sqlite; "
            "CI runs it with config.settings.test_postgres"
        ),
    ),
    pytest.mark.django_db(transaction=True),
]

# Seconds a test waits for a request. Under test_postgres's lock_timeout (10 s), so a
# deadlock fails the test here instead of hanging the run.
WAIT = 5

NEW_DEBT = {
    "creditor_name": "Prairie Card Services",
    "debt_type": "credit_card",
    "amount_owed": "75.00",
}
NEW_CONTRACT = {
    "counterparty_name": "Oak Street Apartments",
    "contract_type": "lease",
    "description": "",
}


@pytest.fixture
def ready(transactional_db):
    """A filer's intake with everything Complete checks, still in progress."""
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(
        user=user, district=district, status="in_progress", current_step=8
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
        monthly_gross_wages=Decimal("3000.00"),
    )
    ExpenseInfo.objects.create(session=session)
    return user, session


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _session_url(session, action=""):
    return f"/api/intake/sessions/{session.pk}/{action}"


def _on_its_own_thread(request):
    """Start request() on a thread with its own database connection.

    Returns the thread and a dict that gets the response, or the exception it raised.
    """
    outcome = {}

    def run():
        try:
            outcome["response"] = request()
        except BaseException as exc:
            outcome["error"] = exc
        finally:
            connection.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread, outcome


def _waits_on_a_lock(thread):
    """True once a connection to the test database waits on a lock while `thread` runs;
    False when the thread ends first or WAIT runs out."""
    deadline = time.monotonic() + WAIT
    while thread.is_alive() and time.monotonic() < deadline:
        with connection.cursor() as cursor:
            # Postgres reads pg_stat_activity once per transaction; drop that copy.
            cursor.execute("SELECT pg_stat_clear_snapshot()")
            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity"
                " WHERE datname = current_database() AND wait_event_type = 'Lock'"
            )
            if cursor.fetchone()[0]:
                return True
        time.sleep(0.02)
    return False


def _finished(thread, outcome):
    thread.join(WAIT)
    assert not thread.is_alive(), "the request never finished: a save deadlocked"
    if "error" in outcome:
        raise outcome["error"]
    return outcome["response"]


def test_two_saves_of_the_same_new_contract_store_it_once(ready):
    # Continue on the Contracts step sends the whole list. Pressed twice, both saves carry
    # the lease the filer just typed, which has no id yet. Each save reads the stored rows
    # before it writes; this pauses the first save after its writes, before it commits.
    user, session = ready
    first_saved = threading.Event()
    go_on = threading.Event()
    save_rows = intake_views._save_rows_by_id

    def first_save_pauses_before_commit(*args, **kwargs):
        save_rows(*args, **kwargs)
        if not first_saved.is_set():
            first_saved.set()
            go_on.wait(WAIT)

    def save():
        return _client(user).put(_session_url(session, "contracts/"), [NEW_CONTRACT], format="json")

    with patch.object(intake_views, "_save_rows_by_id", first_save_pauses_before_commit):
        first, first_outcome = _on_its_own_thread(save)
        assert first_saved.wait(WAIT)
        second, second_outcome = _on_its_own_thread(save)
        second_waited = _waits_on_a_lock(second)
        go_on.set()
        assert _finished(first, first_outcome).status_code == 200
        assert _finished(second, second_outcome).status_code == 200

    assert ExecutoryContract.objects.filter(session=session).count() == 1
    assert second_waited, "the second save ran while the first was still writing"


@contextmanager
def _the_hosted_model_pauses(reading_of_the_upload):
    """While active, the hosted model's read of an upload sets `reading`, waits for `go_on`
    and returns `reading_of_the_upload`. Yields (reading, go_on)."""
    reading = threading.Event()
    go_on = threading.Event()

    def read(*args):
        reading.set()
        go_on.wait(WAIT)
        return reading_of_the_upload

    run_processing = document_views._run_processing

    def run_processing_then_close(doc_id):
        try:
            run_processing(doc_id)
        finally:
            connection.close()  # the executor's thread opens its own connection

    with (
        patch.object(document_views, "_get_processor") as get_processor,
        patch.object(document_views, "_run_processing", run_processing_then_close),
    ):
        get_processor.return_value.process.side_effect = read
        yield reading, go_on


@contextmanager
def _complete_pauses_in_its_checks():
    """While active, Complete sets `checking` once it holds the lock and is checking the
    intake, then waits for `go_on`. Yields (checking, go_on)."""
    checking = threading.Event()
    go_on = threading.Event()
    income = intake_views.current_monthly_income

    def check_income(income_info):
        checking.set()
        go_on.wait(WAIT)
        return income(income_info)

    with patch.object(intake_views, "current_monthly_income", check_income):
        yield checking, go_on


def _upload(user, session, document_type, filename):
    return _client(user).post(
        "/api/documents/upload/",
        {
            "file": SimpleUploadedFile(filename, b"%PDF-1.4 scan", content_type="application/pdf"),
            "document_type": document_type,
            "session_id": session.pk,
        },
        format="multipart",
    )


def test_an_uploads_scanned_debt_waits_for_a_save_in_progress_then_is_stored(
    ready, settings, tmp_path
):
    # The draft is written by the upload's worker thread while the request thread waits for
    # it, so only the worker may take the lock: a lock held by the request thread, or held
    # across the call to the hosted model, would stop the save below from starting.
    user, session = ready
    settings.MEDIA_ROOT = tmp_path
    bill = ExtractionResult(
        fields={
            "creditor_name": "Lakeshore Medical Billing",
            "amount_owed": "1284.50",
            "creditor_type": "medical",
        },
        confidence={"overall": 88},
        detected_type=DocumentType.CREDITOR_BILL,
    )

    with _the_hosted_model_pauses(bill) as (reading, go_on):
        uploading, outcome = _on_its_own_thread(
            lambda: _upload(user, session, DocumentType.CREDITOR_BILL, "bill.pdf")
        )
        assert reading.wait(WAIT)
        with transaction.atomic():
            lock_session(session.pk)  # the filer's save starts while the bill is being read
            go_on.set()
            findings_waited = _waits_on_a_lock(uploading)
            stored_during_the_save = DebtInfo.objects.filter(session=session).exists()
        response = _finished(uploading, outcome)

    assert not stored_during_the_save
    assert findings_waited, "the scanned debt was written while the save was in progress"

    assert response.status_code == 202
    draft = DebtInfo.objects.get(session=session)
    assert (draft.creditor_name, draft.is_draft) == ("Lakeshore Medical Billing", True)
    assert OCRResult.objects.get(document_id=response.json()["id"]).status == OCRStatus.COMPLETED


def test_an_edit_made_while_complete_runs_reopens_the_intake(ready):
    user, session = ready

    with _complete_pauses_in_its_checks() as (checking, go_on):
        completing, completed = _on_its_own_thread(
            lambda: _client(user).post(_session_url(session, "complete/"))
        )
        assert checking.wait(WAIT)
        editing, edited = _on_its_own_thread(
            lambda: _client(user).patch(_session_url(session), {"debts": [NEW_DEBT]}, format="json")
        )
        edit_waited = _waits_on_a_lock(editing)
        go_on.set()
        assert _finished(completing, completed).status_code == 200
        assert _finished(editing, edited).status_code == 200

    assert IntakeSession.objects.get(pk=session.pk).status == "in_progress"
    assert edit_waited, "the edit saved while Complete was checking"


def test_a_pay_stub_read_while_complete_runs_reopens_the_intake(ready, settings, tmp_path):
    # A pay stub's findings reopen the intake before they write anything that waits on the
    # session row, so only the worker's own lock keeps them from landing inside Complete.
    user, session = ready
    settings.MEDIA_ROOT = tmp_path
    pay_stub = ExtractionResult(
        fields={
            "employer_name": "Lakeview Logistics",
            "gross_pay": "1000.00",
            "pay_period_start": "2026-01-01",
            "pay_period_end": "2026-01-14",
        },
        confidence={"overall": 90},
        detected_type=DocumentType.PAY_STUB,
    )

    with (
        _the_hosted_model_pauses(pay_stub) as (reading, read_on),
        _complete_pauses_in_its_checks() as (checking, complete_on),
    ):
        uploading, uploaded = _on_its_own_thread(
            lambda: _upload(user, session, DocumentType.PAY_STUB, "stub.pdf")
        )
        assert reading.wait(WAIT)
        completing, completed = _on_its_own_thread(
            lambda: _client(user).post(_session_url(session, "complete/"))
        )
        assert checking.wait(WAIT)
        read_on.set()
        findings_waited = _waits_on_a_lock(uploading)
        complete_on.set()
        assert _finished(completing, completed).status_code == 200
        assert _finished(uploading, uploaded).status_code == 202

    assert IntakeSession.objects.get(pk=session.pk).status == "in_progress"
    employer = IngestedAggregate.objects.get(session=session, ingest_key="paystub.employer_name")
    assert employer.value == "Lakeview Logistics"
    assert findings_waited, "the pay stub's findings were written while Complete was checking"


def test_a_save_keeps_the_step_a_continue_stored_while_it_waited(ready):
    # A session save writes the whole session row back. Read before the lock, it would put
    # back the step and status it saw, over a Continue that committed meanwhile.
    user, session = ready

    with transaction.atomic():
        lock_session(session.pk)
        IntakeSession.objects.filter(pk=session.pk).update(current_step=5)  # a Continue
        saving, outcome = _on_its_own_thread(
            lambda: _client(user).patch(_session_url(session), {"debts": [NEW_DEBT]}, format="json")
        )
        save_waited = _waits_on_a_lock(saving)
    response = _finished(saving, outcome)

    assert response.status_code == 200
    assert IntakeSession.objects.get(pk=session.pk).current_step == 5
    assert save_waited, "the save ran while the Continue was in progress"


@pytest.mark.parametrize(
    "endpoint, kind, model", [("assets", "asset", AssetInfo), ("debts", "debt", DebtInfo)]
)
def test_a_row_deleted_while_its_update_waited_is_not_found_and_stays_deleted(
    ready, endpoint, kind, model
):
    # The Assets or Amounts Owed step's save deletes a row the filer removed while a
    # per-item update of that row waits for the lock.
    user, session = ready
    row = _rows(session)[kind]

    with transaction.atomic():
        lock_session(session.pk)
        model.objects.filter(pk=row.pk).delete()  # the step's save drops the row
        updating, outcome = _on_its_own_thread(
            lambda: _client(user).patch(
                f"/api/intake/{endpoint}/{row.pk}/", {"amount_owed": "10.00"}, format="json"
            )
        )
        update_waited = _waits_on_a_lock(updating)
    response = _finished(updating, outcome)

    assert response.status_code == 404
    assert not model.objects.filter(pk=row.pk).exists()
    assert update_waited, "the update ran while the save was in progress"


def test_a_row_moved_to_another_session_while_its_update_waited_is_not_found(ready):
    # The update locked only the session the row was on; writing it now would change the
    # other session without that session's lock.
    user, session = ready
    other = IntakeSession.objects.create(user=user, district=session.district)
    debt = _rows(session)["debt"]

    with transaction.atomic():
        lock_session(session.pk)
        DebtInfo.objects.filter(pk=debt.pk).update(session=other)  # a move by another request
        updating, outcome = _on_its_own_thread(
            lambda: _client(user).patch(
                f"/api/intake/debts/{debt.pk}/", {"amount_owed": "10.00"}, format="json"
            )
        )
        update_waited = _waits_on_a_lock(updating)
    response = _finished(updating, outcome)

    assert response.status_code == 404
    moved = DebtInfo.objects.get(pk=debt.pk)
    assert (moved.session_id, moved.amount_owed) == (other.pk, Decimal("1000.00"))
    assert update_waited, "the update ran while the save was in progress"


def _rows(session):
    """One stored row of each kind a write below changes."""
    bill = UploadedDocument.objects.create(
        session=session,
        uploaded_by=session.user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename="bill.pdf",
        file_size=100,
        mime_type="application/pdf",
        file="documents/bill.pdf",
    )
    OCRResult.objects.create(
        document=bill,
        status=OCRStatus.COMPLETED,
        extracted_data='{"creditor_name": "Lakeshore Medical"}',
        confidence_scores={},
        overall_confidence=80,
    )
    return {
        "contract": ExecutoryContract.objects.create(
            session=session, counterparty_name="Oak Street Apartments", contract_type="lease"
        ),
        "codebtor": Codebtor.objects.create(
            session=session, name="Sam Doe", relationship="relative"
        ),
        "asset": AssetInfo.objects.create(
            session=session,
            asset_type="vehicle",
            description="Car",
            current_value=Decimal("5000.00"),
            amount_owed=Decimal("0.00"),
        ),
        "debt": DebtInfo.objects.create(
            session=session,
            creditor_name="Prairie Card Services",
            debt_type="credit_card",
            amount_owed=Decimal("1000.00"),
        ),
        "bill": bill,
    }


# Every intake-data write: (method, path, body, expected status).
WRITES = {
    "session PATCH": lambda s, r: ("patch", _session_url(s), {"debts": [NEW_DEBT]}, 200),
    "session PUT": lambda s, r: ("put", _session_url(s), {"district": s.district_id}, 200),
    "Continue": lambda s, r: ("post", _session_url(s, "update_step/"), {"current_step": 3}, 200),
    "Complete": lambda s, r: ("post", _session_url(s, "complete/"), {}, 200),
    "contracts PUT": lambda s, r: (
        "put",
        _session_url(s, "contracts/"),
        [{"counterparty_name": "Metro Gym", "contract_type": "contract", "description": ""}],
        200,
    ),
    "contract POST": lambda s, r: (
        "post",
        _session_url(s, "contracts/"),
        {"counterparty_name": "Metro Gym", "contract_type": "contract", "description": ""},
        201,
    ),
    "contract DELETE": lambda s, r: (
        "delete",
        _session_url(s, f"contracts/{r['contract'].pk}/"),
        None,
        204,
    ),
    "codebtors PUT": lambda s, r: (
        "put",
        _session_url(s, "codebtors/"),
        [{"name": "Ana Ruiz", "relationship": "friend"}],
        200,
    ),
    "codebtor POST": lambda s, r: (
        "post",
        _session_url(s, "codebtors/"),
        {"name": "Ana Ruiz", "relationship": "friend"},
        201,
    ),
    "codebtor DELETE": lambda s, r: (
        "delete",
        _session_url(s, f"codebtors/{r['codebtor'].pk}/"),
        None,
        204,
    ),
    "asset POST": lambda s, r: (
        "post",
        "/api/intake/assets/",
        {
            "session": s.pk,
            "asset_type": "vehicle",
            "description": "Second car",
            "current_value": "2000.00",
            "amount_owed": "0",
        },
        201,
    ),
    "asset PATCH": lambda s, r: (
        "patch",
        f"/api/intake/assets/{r['asset'].pk}/",
        {"description": "Paid-off car"},
        200,
    ),
    "asset DELETE": lambda s, r: ("delete", f"/api/intake/assets/{r['asset'].pk}/", None, 204),
    "debt POST": lambda s, r: (
        "post",
        "/api/intake/debts/",
        {
            "session": s.pk,
            "creditor_name": "Lakeshore Medical Billing",
            "debt_type": "medical",
            "priority_classification": "unsecured",
            "amount_owed": "120.00",
            "monthly_payment": "0.00",
        },
        201,
    ),
    "debt PATCH": lambda s, r: (
        "patch",
        f"/api/intake/debts/{r['debt'].pk}/",
        {"amount_owed": "900.00"},
        200,
    ),
    "debt DELETE": lambda s, r: ("delete", f"/api/intake/debts/{r['debt'].pk}/", None, 204),
    "scanned bill correction": lambda s, r: (
        "post",
        f"/api/documents/{r['bill'].pk}/validate/",
        {"fields": {"creditor_name": "Lakeshore Medical Billing"}},
        200,
    ),
}


@pytest.mark.parametrize("write", WRITES)
def test_every_intake_write_waits_for_a_save_in_progress(ready, write):
    # Also proves each write runs inside its own transaction: Postgres refuses a lock
    # taken outside one, which sqlite never does.
    user, session = ready
    method, url, body, expected = WRITES[write](session, _rows(session))

    def send():
        return getattr(_client(user), method)(url, body, format="json")

    with transaction.atomic():
        lock_session(session.pk)  # a save in progress
        sending, outcome = _on_its_own_thread(send)
        waited = _waits_on_a_lock(sending)
    response = _finished(sending, outcome)

    assert waited, f"{write} wrote without waiting for the save in progress"
    assert response.status_code == expected, response.content
```

Each request runs on its own thread with its own database connection, as two browser requests do. A request "waits" when `pg_stat_activity` shows a connection to the test database waiting on a lock; each poll calls `pg_stat_clear_snapshot()` first, because Postgres reads that view once per transaction. The race windows are widened with events, not sleeps: test 1 pauses the first save after `_save_rows_by_id`, before it commits; the upload tests pause the mocked hosted model inside `process()`; the Complete tests pause Complete inside `current_monthly_income`, after it has locked. The other tests hold the lock themselves through `lock_session`, as a save in progress. `_finished` joins each request with a 5-second timeout, as the deadlock detector.

- [ ] **Step 3: Run them on Postgres and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=line -rN --disable-warnings -q -p no:cacheprovider apps/intake/tests/test_session_lock.py 2>&1 | tail -20)
```

Expected: FAIL — `14 failed, 11 passed`. Nothing locks yet. The second contracts save stores the lease again (`assert 2 == 1`), an edit or a pay stub that lands while Complete checks leaves the intake completed (`assert 'completed' == 'in_progress'`), a session save writes back the step it read before a Continue (`assert 8 == 5`), and a per-item update re-creates a deleted row or writes a moved one (`assert 200 == 404`). Seven write cases don't wait (`wrote without waiting for the save in progress`): contract and codebtor DELETE, asset and debt PATCH and DELETE, and the scanned bill correction. The other ten write cases and the scanned-debt test already wait, on implicit row locks.

- [ ] **Step 4: Lock the session in every intake write**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/views.py b/backend/apps/intake/views.py
index 9f1781c..7146744 100644
--- a/backend/apps/intake/views.py
+++ b/backend/apps/intake/views.py
@@ -16,6 +16,7 @@ from apps.eligibility.cmi import IncomeNotSplit, current_monthly_income
 from apps.eligibility.services import MeansTestCalculator
 from apps.forms.registry import PreconditionMissing, _needs_ssn

+from .locking import lock_session
 from .models import (
     AssetInfo,
     Codebtor,
@@ -52,6 +53,7 @@ def _save_list(session, model, row_serializer, rows):
     serializer = row_serializer(data=rows, many=True)
     serializer.is_valid(raise_exception=True)
     with transaction.atomic():
+        lock_session(session.pk)
         _save_rows_by_id(session, model, serializer.validated_data)
         session.reopen()
     saved = model.objects.filter(session=session).order_by("id")
@@ -71,6 +73,29 @@ def _assert_session_owned(session, user):
         raise PermissionDenied("You do not have access to this session.")


+def _lock_for_row_update(serializer):
+    """Lock the sessions a per-item asset or debt update changes, then read the row again.
+
+    A row moved to another of the filer's sessions changes both, so both are locked, in id
+    order, so two moves between the same sessions can't wait on each other (DIG-188). A row
+    that another save deleted or moved while this one waited is a 404, as a missing row is.
+    """
+    from rest_framework.exceptions import NotFound
+
+    row = serializer.instance
+    session = serializer.validated_data.get("session")
+    moved_to = session.pk if session is not None else row.session_id
+    locked = sorted({row.session_id, moved_to})
+    for session_id in locked:
+        lock_session(session_id)
+    try:
+        row.refresh_from_db()  # the row as stored once the lock is held
+    except row.DoesNotExist:
+        raise NotFound() from None
+    if row.session_id not in locked:
+        raise NotFound()  # moved meanwhile: locking its session now would break id order
+
+
 class IntakeSessionViewSet(viewsets.ModelViewSet):
     """
     ViewSet for intake session management.
@@ -117,6 +142,17 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
             status=status.HTTP_201_CREATED,
         )

+    @transaction.atomic
+    def update(self, request, *args, **kwargs):
+        """
+        PUT /api/intake/sessions/{id}/, and every PATCH through partial_update.
+
+        Locks the session before the save reads it and its stored rows, so two saves of one
+        session run one after the other (DIG-188).
+        """
+        lock_session(self.get_object().pk)  # get_object first: another user's session is a 404
+        return super().update(request, *args, **kwargs)
+
     @transaction.atomic
     def partial_update(self, request, *args, **kwargs):
         """
@@ -138,6 +174,7 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         serializer.save(user=self.request.user)

     @action(detail=True, methods=["post"])
+    @transaction.atomic
     def update_step(self, request, pk=None):
         """
         Update current step in intake wizard.
@@ -148,7 +185,7 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
             "data": {...}  // Step-specific data
         }
         """
-        session = self.get_object()
+        session = lock_session(self.get_object().pk)

         # Only one of the wizard's 8 steps; anything else is a client fault (DIG-151).
         current_step = request.data.get("current_step")
@@ -180,6 +217,7 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         )

     @action(detail=True, methods=["post"])
+    @transaction.atomic
     def complete(self, request, pk=None):
         """
         Mark intake session as completed.
@@ -187,9 +225,10 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         POST /api/intake/sessions/{id}/complete/

         Refuses with a 400 naming, in wizard order, the step that fixes each gap
-        (forms step 3a1 spec §4.2).
+        (forms step 3a1 spec §4.2). The session stays locked from the checks to the status
+        write, so a save can't land between them, and a save that waited reopens it.
         """
-        session = self.get_object()
+        session = lock_session(self.get_object().pk)

         # Validate session is complete
         errors = []
@@ -240,7 +279,7 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):

         session.status = "completed"
         session.completed_at = timezone.now()
-        session.save()
+        session.save(update_fields=["status", "completed_at"])

         return Response(
             {
@@ -426,8 +465,10 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
             )
         serializer = ExecutoryContractSerializer(data=request.data)
         serializer.is_valid(raise_exception=True)
-        serializer.save(session=session)
-        session.reopen()
+        with transaction.atomic():
+            lock_session(session.pk)
+            serializer.save(session=session)
+            session.reopen()
         return Response(serializer.data, status=status.HTTP_201_CREATED)

     @action(
@@ -436,8 +477,9 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         url_path="contracts/(?P<contract_id>[0-9]+)",
         url_name="contract-detail",
     )
+    @transaction.atomic
     def delete_contract(self, request, pk=None, contract_id=None):
-        session = self.get_object()
+        session = lock_session(self.get_object().pk)
         try:
             contract = ExecutoryContract.objects.get(pk=contract_id, session=session)
             contract.delete()
@@ -457,8 +499,10 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
             return _save_list(session, Codebtor, CodebtorRowSerializer, request.data)
         serializer = CodebtorSerializer(data=request.data)
         serializer.is_valid(raise_exception=True)
-        serializer.save(session=session)
-        session.reopen()
+        with transaction.atomic():
+            lock_session(session.pk)
+            serializer.save(session=session)
+            session.reopen()
         return Response(serializer.data, status=status.HTTP_201_CREATED)

     @action(
@@ -467,8 +511,9 @@ class IntakeSessionViewSet(viewsets.ModelViewSet):
         url_path="codebtors/(?P<codebtor_id>[0-9]+)",
         url_name="codebtor-detail",
     )
+    @transaction.atomic
     def delete_codebtor(self, request, pk=None, codebtor_id=None):
-        session = self.get_object()
+        session = lock_session(self.get_object().pk)
         try:
             codebtor = Codebtor.objects.get(pk=codebtor_id, session=session)
             codebtor.delete()
@@ -519,21 +564,27 @@ class AssetViewSet(viewsets.ModelViewSet):
         """Return only assets for user's intake sessions."""
         return AssetInfo.objects.filter(session__user=self.request.user).select_related("session")

+    @transaction.atomic
     def perform_create(self, serializer):
         _assert_session_owned(serializer.validated_data["session"], self.request.user)
+        lock_session(serializer.validated_data["session"].pk)
         serializer.save()
         serializer.instance.session.reopen()

+    @transaction.atomic
     def perform_update(self, serializer):
         session = serializer.validated_data.get("session")
         if session is not None:
             _assert_session_owned(session, self.request.user)
+        _lock_for_row_update(serializer)
         # A row moved to another of the filer's sessions changes both.
         serializer.instance.session.reopen()
         serializer.save()
         serializer.instance.session.reopen()

+    @transaction.atomic
     def perform_destroy(self, instance):
+        lock_session(instance.session_id)
         instance.delete()
         instance.session.reopen()

@@ -553,21 +604,27 @@ class DebtViewSet(viewsets.ModelViewSet):
         """Return only debts for user's intake sessions."""
         return DebtInfo.objects.filter(session__user=self.request.user).select_related("session")

+    @transaction.atomic
     def perform_create(self, serializer):
         _assert_session_owned(serializer.validated_data["session"], self.request.user)
+        lock_session(serializer.validated_data["session"].pk)
         serializer.save()
         serializer.instance.session.reopen()

+    @transaction.atomic
     def perform_update(self, serializer):
         session = serializer.validated_data.get("session")
         if session is not None:
             _assert_session_owned(session, self.request.user)
+        _lock_for_row_update(serializer)
         # A row moved to another of the filer's sessions changes both.
         serializer.instance.session.reopen()
         serializer.save()
         serializer.instance.session.reopen()

+    @transaction.atomic
     def perform_destroy(self, instance):
+        lock_session(instance.session_id)
         instance.delete()
         instance.session.reopen()

PATCH
```

Each write locks the session right after `get_object()` and inside the transaction that does its writes, so a second save of the same session waits for the first to commit and then reads what it stored (§7). `complete` holds the lock from its checks to its status write, so an edit that arrives meanwhile waits and then reopens the intake, and it writes only `status` and `completed_at`.

- [ ] **Step 5: Lock the documents' writes**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/documents/views.py b/backend/apps/documents/views.py
index cf79460..035b152 100644
--- a/backend/apps/documents/views.py
+++ b/backend/apps/documents/views.py
@@ -4,6 +4,7 @@ from concurrent.futures import ThreadPoolExecutor

 from django.conf import settings
 from django.core.exceptions import ImproperlyConfigured
+from django.db import transaction
 from pydantic import ValidationError
 from rest_framework import serializers, status
 from rest_framework.decorators import action
@@ -24,6 +25,7 @@ from apps.documents.services.aggregator import AggregateIngestionService
 from apps.documents.services.draft_debt import DraftDebtCreator
 from apps.documents.services.processor import DocumentProcessor, ExtractionResult
 from apps.documents.services.providers.base import BaseOCRProvider
+from apps.intake.locking import lock_session
 from apps.intake.models import IntakeSession

 logger = logging.getLogger(__name__)
@@ -96,29 +98,37 @@ def _run_processing(doc_id: int) -> None:
         processor = _get_processor()
         result = processor.process(file_bytes, doc.mime_type, doc.document_type)

-        if result.error:
-            ocr.status = OCRStatus.FAILED
-            ocr.failure_reason = OCRFailureReason.PROCESSING_ERROR
-            ocr.error_message = result.error
-            ocr.extracted_data = "{}"
-            ocr.overall_confidence = 0
-        else:
-            ocr.extracted_data = json.dumps(result.fields)
-            ocr.confidence_scores = result.confidence
-            ocr.overall_confidence = result.confidence.get("overall", 0)
-            if _record_findings(doc, result):
-                ocr.status = OCRStatus.COMPLETED
-            else:
+        # The findings are intake data, so their writes lock the session (DIG-188): only
+        # here, after the call to the hosted model, and only on this worker thread. The
+        # upload request waits for this thread, so a lock taken there would deadlock.
+        with transaction.atomic():
+            lock_session(doc.session_id)
+            if result.error:
                 ocr.status = OCRStatus.FAILED
-                ocr.failure_reason = OCRFailureReason.NOTHING_FOUND
-
-        ocr.save()
-
-        if ocr.status == OCRStatus.COMPLETED:
-            try:
-                AggregateIngestionService.recalculate(doc.session_id)
-            except Exception as exc:
-                logger.warning("Recalculate failed for doc %s: %s", doc_id, type(exc).__name__)
+                ocr.failure_reason = OCRFailureReason.PROCESSING_ERROR
+                ocr.error_message = result.error
+                ocr.extracted_data = "{}"
+                ocr.overall_confidence = 0
+            else:
+                ocr.extracted_data = json.dumps(result.fields)
+                ocr.confidence_scores = result.confidence
+                ocr.overall_confidence = result.confidence.get("overall", 0)
+                if _record_findings(doc, result):
+                    ocr.status = OCRStatus.COMPLETED
+                else:
+                    ocr.status = OCRStatus.FAILED
+                    ocr.failure_reason = OCRFailureReason.NOTHING_FOUND
+
+            ocr.save()
+
+            if ocr.status == OCRStatus.COMPLETED:
+                try:
+                    # Its own savepoint: recalculate logs and swallows its errors, and on
+                    # Postgres one failed statement would otherwise roll the findings back.
+                    with transaction.atomic():
+                        AggregateIngestionService.recalculate(doc.session_id)
+                except Exception as exc:
+                    logger.warning("Recalculate failed for doc %s: %s", doc_id, type(exc).__name__)

     except Exception as exc:
         # Type only, no traceback: logs reach Sentry, and exception text can quote filer data.
@@ -205,6 +215,7 @@ class DocumentViewSet(ViewSet):
         return Response(_serialize_doc(doc))

     @action(detail=True, methods=["post"], url_path="validate")
+    @transaction.atomic
     def validate(self, request, pk=None):
         try:
             doc = UploadedDocument.objects.select_related("ocr_result", "session").get(
@@ -225,7 +236,10 @@ class DocumentViewSet(ViewSet):
             except serializers.ValidationError as exc:
                 return Response({"amount_owed": exc.detail}, status=status.HTTP_400_BAD_REQUEST)

+        # A correction changes the draft debt and the pay-stub figures (DIG-188).
+        lock_session(doc.session_id)
         ocr = doc.ocr_result
+        ocr.refresh_from_db()  # the findings as stored once the lock is held
         existing = json.loads(ocr.extracted_data or "{}")
         existing.update(fields)
         ocr.extracted_data = json.dumps(existing)
@@ -240,7 +254,8 @@ class DocumentViewSet(ViewSet):
             doc.session.reopen()

         try:
-            AggregateIngestionService.recalculate(doc.session_id)
+            with transaction.atomic():  # its own savepoint, as in _run_processing
+                AggregateIngestionService.recalculate(doc.session_id)
         except Exception as exc:
             logger.warning("Recalculate failed on validate for doc %s: %s", pk, type(exc).__name__)

PATCH
```

The worker locks only after the call to the hosted model, around the write of the findings, and `validate` locks before it reads the findings it merges into. Each `recalculate` runs in its own savepoint, so its swallowed errors can't roll the findings back.

- [ ] **Step 6: Run the tests again, on Postgres and on sqlite**

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=line -rN --disable-warnings -q -p no:cacheprovider apps/intake/tests/test_session_lock.py 2>&1 | tail -20)
```

Expected: `25 passed`.

```bash
set -eo pipefail
source .claude/forms-step3a1.env
cd backend && $PY -m pytest -rs apps/intake/tests/test_session_lock.py -q -p no:cacheprovider 2>&1 | tail -3
```

Expected: `25 skipped`, each with the reason `needs Postgres: select_for_update does nothing on sqlite; CI runs it with config.settings.test_postgres`.

- [ ] **Step 7: Run them in CI**

```bash
git apply <<'PATCH'
diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml
index 3dcbb09..9bf349c 100644
--- a/.github/workflows/ci.yml
+++ b/.github/workflows/ci.yml
@@ -78,6 +78,15 @@ jobs:
         # skips (no `java` on the runner) shows in the log instead of passing quietly.
         run: pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs

+      - name: Run the Postgres-only tests
+        working-directory: backend
+        # select_for_update does nothing on sqlite, so the tests that prove one save at a
+        # time on a session (DIG-188) skip above and run here, against the job's Postgres
+        # service. -rs shows any that skip.
+        env:
+          DJANGO_SETTINGS_MODULE: config.settings.test_postgres
+        run: pytest -m postgres --tb=short -q -rs
+
   security-scan:
     name: Security Scan
     runs-on: ubuntu-latest
PATCH
```

The new step runs after the coverage run, against the job's Postgres service and its `DATABASE_URL`. It has no coverage floor, and `-rs` shows any test that skips.

- [ ] **Step 8: Say in CLAUDE.md that saves lock the session**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index a882ade..f450dcf 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -24,11 +24,12 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Vite HMR in Docker** — type/structure changes don't hot-reload; restart the frontend container.
 - **Enum mismatches are silent** — frontend/backend enum drift only surfaces at runtime; check both when adding fields.
 - **Nested debts and assets save by id** — `IntakeSessionSerializer.update` upserts `debts`/`assets` through `_save_rows_by_id`: a row carrying one of this session's ids updates only the keys it sends, a row without one (or with an unknown or foreign id) is created on this session, and a stored row missing from the payload is **deleted**, so send every row you want to keep. A nested `session` is ignored. Fields the browser never receives (`account_number`, `source_document`) survive a re-save. `DebtViewSet`/`AssetViewSet` keep the base serializers, so per-item create never takes a client id. Contracts and codebtors save the same way, as a whole list: `PUT /intake/sessions/{id}/contracts/` (or `codebtors/`) checks every row before writing any, and an empty list deletes every stored row. The wizard sends each list on Continue from steps 6 and 7, and reads both with the session before any step shows, so a list that failed to load is never saved as empty.
+- **Saves lock the session** — every write to a session's intake data first calls `lock_session` (`apps/intake/locking.py`, `select_for_update` on the session row) inside the same `transaction.atomic()` block as the write, so a second save of the same session waits for the first to commit and then reads what it stored (DIG-188). That covers the session PATCH and PUT, `update_step`, `complete` (which writes only `status` and `completed_at`), the contracts and codebtors PUT, POST and DELETE, the `DebtViewSet`/`AssetViewSet` writes, a scanned bill's correction and an upload's findings. Call `get_object()` before locking (another user's session is a 404), and lock before reading anything the write depends on. An upload locks only in its worker thread, around the write of its findings, after the call to the hosted model: the upload request waits for that thread, so a lock taken in the request deadlocks. `select_for_update` does nothing on sqlite, so the backend suite can't see a missing lock; only `apps/intake/tests/test_session_lock.py` (marker `postgres`) proves it, and it skips under the default settings. Run it locally with `DJANGO_SETTINGS_MODULE=config.settings.test_postgres pytest -m postgres`, with `DATABASE_URL` naming a Postgres whose user can create the test database; CI runs it in the backend job against its Postgres service. `test_postgres` sets a 10-second `lock_timeout`, so a deadlock fails a test instead of hanging the run.
 - **Debt and asset amounts are readable, as strings** — the owner gets `DebtInfo.amount_owed` and `AssetInfo.current_value`/`amount_owed` back (SSN and `account_number` stay write-only). DRF sends decimals as strings (`"2500.00"`), so the wizard converts them with `hydrateAmounts` (`utils/parseAmount.ts`) as session data enters step state; a raw string in a step's `reduce` joins as text (`$02500.00100.50`). A stored amount wider than `DecimalField(12, 2)` makes every read of that session 500, so every write path must bound it (`DraftDebtCreator` stores it as 0; documents `validate` returns 400).
 - **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data. It reads the median table in force on today's real date, not the tests' pinned one, and when none is (from November 1, 2026 until the November table is loaded) it prints a message naming `docs/REFERENCE_TABLES.md` and changes nothing, so even `--reset` leaves the existing personas. Personas seeded before income was stored by source must be re-created with `seed_demo_data --reset` (migration 0014 leaves their totals unsplit, and a plain re-run skips existing users).
 - **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
 - **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 > median_income_threshold`, through `is_above_median` (`apps/eligibility/cmi.py`), the means test's own comparison, so income exactly at the median counts as below (DIG-136). Never read `above_median_calculated`: a row calculated before DIG-128 was fixed can still carry a stale True. 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. Generate All, Generate, Regenerate, the download of an unfiled form and the packet list of a completed intake work the means test out again from the stored intake first (`_recalculate_means_test` in `apps/forms/views.py`), so a stale `MeansTest` row never decides the packet (DIG-160); an unfinished intake's packet list reads the stored row. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words, and so are income not entered by source (`IncomeNotSplit`) and no median table in force on the fill date (`NoTableInForce`, which logs the table, the date and the district); any other failure is a 500 logged by exception type only.
-- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key: no `DebtorInfo` row (the name-and-address sentence; the fields themselves aren't checked) or an SSN that isn't 9 digits (the registry's own `_needs_ssn`, so Complete and Forms 101 and 121 say the same thing), income not entered by source (`IncomeNotSplit`, no income row included), an Expenses step never saved (no `ExpenseInfo` row), and a scanned debt the filer hasn't confirmed (a `DebtInfo` with `is_draft`, step `debts`; see "Document upload sits mid-wizard"). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. A forms refusal also carries the `step` (a wizard step key) or `page` (a route) that fixes it, when the exception names one: `PreconditionMissing.step`, `IncomeNotSplit.step` (`income_info`) and `IntakeNotFinished.page` (`/intake`); "already filed", "not in your packet" and `NoTableInForce` carry neither, and the key is absent, never null. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
+- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key: no `DebtorInfo` row (the name-and-address sentence; the fields themselves aren't checked) or an SSN that isn't 9 digits (the registry's own `_needs_ssn`, so Complete and Forms 101 and 121 say the same thing), income not entered by source (`IncomeNotSplit`, no income row included), an Expenses step never saved (no `ExpenseInfo` row), and a scanned debt the filer hasn't confirmed (a `DebtInfo` with `is_draft`, step `debts`; see "Document upload sits mid-wizard"). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. A forms refusal also carries the `step` (a wizard step key) or `page` (a route) that fixes it, when the exception names one: `PreconditionMissing.step`, `IncomeNotSplit.step` (`income_info`) and `IntakeNotFinished.page` (`/intake`); "already filed", "not in your packet" and `NoTableInForce` carry neither, and the key is absent, never null. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must lock the session first (see "Saves lock the session") and call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
PATCH
```

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

Expected: `2129 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  379 passed (379)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

The 25 skips are the new tests under sqlite. `DATABASE_URL` in `.claude/forms-step3a1.env` names the Postgres database the plan's setup created, and the next command runs the new tests against it, as CI's "Run the Postgres-only tests" step does.

```bash
set -eo pipefail
source .claude/forms-step3a1.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

This task changes no page flow, so the journeys don't run.

- [ ] **Step 10: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/intake/locking.py \
  backend/apps/intake/tests/test_session_lock.py \
  backend/config/settings/test_postgres.py \
  .github/workflows/ci.yml \
  CLAUDE.md \
  backend/apps/documents/views.py \
  backend/apps/intake/views.py \
  backend/conftest.py \
  backend/pyproject.toml
git commit -F - <<'MSG'
fix(intake): one save at a time on a session

Nothing took a row lock. Two saves of the Contracts or Codebtors list
(Continue pressed twice) each read the stored rows before the other
committed and each created the new row; update_step wasn't atomic;
Complete's full session.save() could write "completed" back over a
reopen() that landed during its checks; and an upload's findings could be
written in the middle of a save (forms step 3a1 spec §7).

- apps/intake/locking.py: lock_session(session_id) takes
  select_for_update() on the session row and returns the session as
  stored. Every write to a session's intake data now calls it first,
  inside the same transaction as the write, after get_object() so another
  user's session is still a 404: the session PATCH and PUT (an update()
  override that partial_update goes through, so T5's draft clear runs under
  the lock), update_step (made atomic), complete (made atomic, and saving
  only status and completed_at), the contracts and codebtors PUT, POST and
  DELETE, and the AssetViewSet/DebtViewSet writes. A per-item update locks
  both sessions when it moves a row, in id order, and re-reads the row once
  the lock is held; a row another save deleted, or moved to another
  session, while it waited is a 404, as a missing row is (before, the full
  save re-created a deleted row). reopen() runs inside the lock everywhere.
- Documents: a scanned bill's correction (validate) is atomic and locks
  before it reads the findings it merges into. An upload locks only in its
  worker thread, around the write of its findings, after the call to the
  hosted model: the request thread waits for the worker, so a lock taken
  there would deadlock, and holding it across the model call would make
  every save wait on OCR. Both recalculate calls get their own savepoint,
  because recalculate swallows its errors and on Postgres one failed
  statement would otherwise roll the findings back unseen.
- config/settings/test_postgres.py: the test settings with
  DATABASES["default"] from DATABASE_URL (keeping any OPTIONS it carries)
  and a 10-second lock_timeout, so a deadlock fails a test instead of
  hanging the run. The root conftest
  ignores it at collection: its name matches python_files, and importing it
  mid-run repointed the running settings' database (285 failures).
  --ds or DJANGO_SETTINGS_MODULE already wins over the conftest's own
  assignment (connection.vendor is postgresql under either), so that stays.
- pyproject registers the postgres marker. CI's backend job runs
  pytest -m postgres with config.settings.test_postgres after the coverage
  run, against the job's Postgres service, with -rs and no coverage floor.

Tests (apps/intake/tests/test_session_lock.py, marker postgres; they skip
on sqlite, with the reason shown under -rs, and stop collection if
config.settings.test_postgres ever reaches anything but Postgres, so CI
can't pass on 25 skips): two saves of the same new contract store it once;
an upload's scanned debt waits for a save in progress and then is stored,
with the save starting while the bill is being read; an edit made while
Complete runs reopens the intake; a pay stub read while Complete runs
reopens it too; a session save keeps the step a Continue stored while it
waited; an asset or debt deleted while its per-item update waited is a 404
and stays deleted; a debt moved to another session meanwhile is a 404 and
stays where it was moved; and every intake-data write waits for a save in
progress and then succeeds, which on Postgres also proves each one runs
inside a transaction.

What fails without which lock:
- lock_session as a plain get (the tests' own holder loses its lock too):
  all 25 fail.
- Every path unlocked, but a real holder: 14 of 25 fail. Two contracts are
  stored; the edit and the pay stub leave the intake completed; the save
  writes step 8 back over the Continue's 5; the deleted asset and debt are
  re-created and the moved debt is written back (200). Of the 17 write
  cases, 7 fail: contract and codebtor DELETE, asset and debt PATCH and
  DELETE, and the scanned bill correction.
  The other 10 wait on implicit row locks: the session PATCH, PUT,
  Continue and Complete on their own UPDATE of the session row, and the
  contracts and codebtors PUT and POST and the asset and debt POST on the
  foreign-key check of the row they insert. The scanned-debt test passes
  the same way.
- Only update()'s lock removed: the stale-step test fails (8 == 5).
- The per-item re-read without its 404s: the deleted row raises
  DoesNotExist (a 500); without the moved check, the moved debt is written
  (200).
- Only the worker's lock removed: the pay-stub test fails.
- A lock in the upload's request thread, or one held across the model
  call: the scanned-debt test fails.
No existing test changed.

CLAUDE.md: a new gotcha "Saves lock the session"; "Forms need a completed
intake" says a new intake-data write path locks the session first.

Refs DIG-188
MSG
git status --short
```
