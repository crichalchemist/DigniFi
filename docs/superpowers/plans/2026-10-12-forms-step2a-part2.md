# Forms Step 2a (Data and Flow) Implementation Plan, Part 2 of 2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make what the filer gives reach the forms intact, and make the flow honest. Forms are prepared only from a completed intake. Every save keeps every field. Income is stored by source, with Social Security left out of CMI. The means test is right at the median and is worked out again before every packet. The fee-waiver page asks what Form 103B asks.

**Architecture:** 2a changes data, saves and the generate flow, and moves no binding. Its one oracle change re-keys tier 2's cases on the binding, which changes how a case is named, not what any box prints. The 14 tasks follow the spec's seven 2a commits in order. Commits 2, 3 and 5 are split into several tasks, one commit each, and every task boundary passes every gate. The bindings are 2b, which gets its own plan once this one merges.

**This part:** Tasks 9–14, the spec's commits 4–7. It starts where Part 1 (`docs/superpowers/plans/2026-10-12-forms-step2a-part1.md`) ends, with Tasks 1–8 committed on this branch. The plan is split in two only to stay under the repository's 500 KB file limit. Run both parts as one execution: one ledger for Tasks 1–14, and the whole-branch final review only after Task 14, because this part's patches expect each file exactly as Part 1's tasks leave it.

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

Check that Part 1 is in place: Task 8's commit is on this branch. Review fixes may have added commits after it.

```bash
set -eo pipefail
git log --format=%s 3383404..HEAD | grep -Fx "test(forms): build each persona's forms through the API and compare them with the seeds" >/dev/null
echo "Part 1 is in place"
```

Expected: `Part 1 is in place`. If the block fails instead, Task 8 isn't committed: finish Part 1 first.

Check the baseline before Task 9:

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

### Task 9: Store income by source, and leave Social Security out of CMI

_Built and verified as commit `cb674d9` on `plan/forms-step2a`._

**Files:**

- Create: `backend/apps/eligibility/cmi.py`
- Create: `backend/apps/eligibility/tests/test_cmi.py`
- Create: `backend/apps/intake/migrations/0013_incomeinfo_income_by_source.py`
- Create: `backend/apps/intake/migrations/0014_split_income_saved_as_zero.py`
- Modify: `backend/apps/audit/tests/test_upl_compliance.py`
- Modify: `backend/apps/eligibility/models.py`
- Modify: `backend/apps/eligibility/services/expense_deduction_calculator.py`
- Modify: `backend/apps/eligibility/services/means_test_calculator.py`
- Modify: `backend/apps/eligibility/tests/test_means_test_calculator.py`
- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/test_api_readback.py`
- Modify: `backend/apps/forms/tests/test_derivations.py`
- Modify: `backend/apps/forms/tests/test_form_106sum_schema.py`
- Modify: `backend/apps/forms/tests/test_form_122a1_schema.py`
- Modify: `backend/apps/forms/tests/test_form_views.py`
- Modify: `backend/apps/forms/tests/test_schedule_i_schema.py`
- Modify: `backend/apps/forms/views.py`
- Modify: `backend/apps/intake/management/commands/seed_demo_data.py`
- Modify: `backend/apps/intake/models.py`
- Modify: `backend/apps/intake/serializers.py`
- Modify: `backend/apps/intake/tests/test_completion.py`
- Modify: `backend/apps/intake/tests/test_data_migrations.py`
- Modify: `backend/apps/intake/tests/test_e2e_intake.py`
- Modify: `backend/apps/intake/tests/test_income_resume.py`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/wizard/steps/IncomeInfoStep.tsx`
- Modify: `frontend/src/components/wizard/steps/ReviewStep.tsx`
- Modify: `frontend/src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx`
- Modify: `frontend/src/context/IntakeContext.tsx`
- Modify: `frontend/src/pages/IntakeWizard.tsx`
- Modify: `frontend/src/pages/__tests__/IntakeWizard.test.tsx`
- Modify: `frontend/src/test/fixtures/session.ts`
- Modify: `frontend/src/types/api.ts`

**Interfaces:**

- Consumes:
  - Task 2's `IntakeSession.reopen()`: a session PATCH carrying `income_info` reopens a completed session. Its parametrized reopen test in `test_completion.py` has an `income_info` case.
  - Task 3's `currentStepBody` in `IntakeWizard.tsx`, which `useAutoSave` compares with the step's last saved or loaded copy, and `WizardLayout`, which shows the intake context's `error` on Review.
  - Task 8's read-back, `_send_through_the_api` in `test_api_readback.py`, which sends each persona's seed data through the API.
  - `hydrateAmounts` and `decimalToNumber` (`frontend/src/utils/parseAmount.ts`), `_failure` in `forms/views.py`, `MeansTestCalculator`, `ExpenseDeductionCalculator._get_cmi`, and the means-test endpoint's existing `except ValueError`, whose 400 body is `{"error": str(e), "message": "Unable to calculate means test. Please ensure all income information is provided."}`.
- Produces:
  - `IncomeInfo.SOURCE_FIELDS`, the ten names in §5.5's order: `monthly_gross_wages`, `monthly_overtime`, `monthly_tips`, `monthly_rental_income`, `monthly_pension`, `monthly_social_security`, `monthly_unemployment`, `monthly_child_support`, `monthly_alimony`, `monthly_other_income`. Each is a column `DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)` with `MinValueValidator(Decimal("0"))` and no default.
  - `IncomeInfo.monthly_income` is `JSONField(null=True, blank=True)`, never written, and read-only in `IncomeInfoSerializer`. `IncomeInfo.calculate_total_monthly_income() -> float | None` is the ten added up, Social Security included, and the API returns it as `total_monthly_income`.
  - Migrations `intake.0013_incomeinfo_income_by_source` (schema) and `intake.0014_split_income_saved_as_zero` (data; the reverse is a no-op).
  - `apps/eligibility/cmi.py`: `IncomeNotSplit(ValueError)`, whose message is "Enter your income by source on the Income step.", and `current_monthly_income(income_info) -> Decimal`, the ten without Social Security. Task 10 adds the rounding to the cent in this function.
  - `MeansTestCalculator.calculate()` re-raises `IncomeNotSplit` without the "Means test calculation failed:" prefix, so the means-test endpoint returns its sentence as `error` in a 400. `_failure` returns it as a 422, `{"form_type": <the form>, "error": "Enter your income by source on the Income step."}`, as it does `PreconditionMissing`; Task 11's whole-call refusal reuses this.
  - `_income_amounts(session, *fields) -> str` in `derivations.py`: the sum of those amounts, or `""` when the filer gave none of them.
  - `_wages_only(wages)` in `seed_demo_data.py`: the ten amounts, wages as given and the other nine `Decimal("0.00")`.
  - `INCOME_FIELDS` in `frontend/src/types/api.ts`, and the Income step's PATCH body `{income_info: {<the ten, each a number or null>}}`.
  - `APIClientError(message, statusCode, details?, serverError?)`, where `serverError` is the response body's own `error`.
  - Tests later tasks and reviewers rely on: `test_social_security_never_counts_toward_cmi`, `test_legacy_income_total_must_be_split_before_forms_print`, `test_new_filer_saves_income_by_source_without_a_total`, `test_each_switched_income_rule_returns_its_own_sources_figure`, `test_a_saved_total_above_zero_waits_for_the_filer_and_zero_becomes_ten_zeros` and `test_undoing_the_income_split_leaves_income_as_it_is`.
  - `known_defects.json` is untouched (kd 0).

**Decisions already made in this task:**

- **Help text** (owner ruling, 2026-10-13): a filer with no income who leaves all ten boxes blank is refused by the means test. Only one sentence changes: "If you don't have income from a source, you can leave it blank or enter $0." becomes exactly "Leave a box blank if you don't get that kind of income. If you have no income at all, enter $0 in any box." The sentence "Enter your average monthly income before taxes." stays.
- **Review shows the means test's own refusal.** The 400's own `error` travels on `APIClientError.serverError`. Only `IntakeContext.calculateMeansTest` reads it, only on a 400, and `handleComplete` is that function's one caller. `handleAPIError`'s `errorData.message || errorData.error || 'Request failed'` is unchanged, so every other caller still shows `message` first.
- **A district with no median data:** the endpoint returns 400 for any `ValueError`, so Review now shows its raw "Means test calculation failed: No median income data found for district …" text too. That is accepted for 2a, as an operations fault.
- **Review's "Total Monthly Income"** shows $0.00 when `total_monthly_income` is null. `ReviewStep.tsx` changes only `formatCurrency`'s parameter type.
- **An empty amount counts as zero once another was given** (§6.2's intro). CMI, `total_monthly_income` and every switched rule refuse, or print blank, only when every amount they read is empty. Social Security counts as given although CMI leaves it out, so a filer living on Social Security alone has a CMI of $0, not a refusal.
- **No income row.** The `cmi` form rule raises `IncomeNotSplit`, because a $0 printed from no income is a sworn figure the filer never gave (B2). `ExpenseDeductionCalculator._get_cmi` still returns 0 for a missing row, which no production path reaches: `MeansTest.calculate` refuses a missing row first. `_get_cmi` no longer catches `Exception`, so `IncomeNotSplit` propagates.
- **`total_monthly_income`** stays a float, as `total_monthly_expenses` is, and is null when none of the ten was given, so the fee-waiver page's pre-fill (`income != null`) skips a legacy filer instead of pre-filling $0.
- **Two migrations**, as Task 5 split 0011 and 0012. 0013 is the schema and 0014 the data. 0014 keeps its own copy of the ten names, because a migration must not import model constants. A "$0 total" is a non-empty month list that sums to 0. `[]`, null, a non-list or months that don't parse count as no total and leave the ten empty, and a parse failure never fails the migration.
- **Bounds.** `MinValueValidator(Decimal("0"))` is how §5.2's "zero or more" reaches DRF as `min_value`. An amount with more than two decimal places is a 400, as on every money column.
- **One list each side.** `IncomeInfo.SOURCE_FIELDS` is the backend's; the serializer, the seeds and `cmi.py` read it, and `cmi.py` reads it from the instance, so it imports no model. `INCOME_FIELDS` in `types/api.ts` is the frontend's and replaces the step's local `SOURCE_FIELDS`.
- **The means test's stored details change shape.** `calculation_details["monthly_income_breakdown"]` (the months) becomes `"income_by_source"` (ten floats or null), and `get_detailed_breakdown()["income_history"]["monthly_values"]` becomes `["by_source"]`. Only tests read either key.
- **The wizard sends a blank box as `null`, not omitted.** An omitted key would keep the old amount on the server, which is DIG-55 for income.
- **The legacy message** ends with a period: "You entered $X a month in total. Please split it by source." The trailing comma in §5.5's quote is the spec's prose. X is the average of the saved months. It shows while every box is empty and X is above 0; a saved $0 total shows nothing, because 0014 gives it ten $0 amounts.
- **Interim boxes until 2b.** Schedule I lines 10 and 12 and Schedule J line 23a print CMI, so they leave out Social Security, which the old total counted, until 2b creates `schedule_i_income_total`. Schedule I 5e (`schedule_i_interest_debtor1`) is not on §5.5's switched list and still prints through `_get_income_field`.
- **Test names.** The §7.7 rule-level test is `test_each_switched_income_rule_returns_its_own_sources_figure`; `test_each_income_source_prints_on_its_own_line` is 2b's. The three schema `test_empty_session` tests become `test_empty_session_is_asked_for_income_by_source`, and 106Sum's old `1a` and `8` zeros move to `test_a_filer_with_no_property_who_typed_zero_income_prints_zeros`, where the filer typed $0.
- **Fixtures.** The UPL test helper keeps its parameter name `monthly_income` (the CMI it wants) and stores it as wages, so its 12 call sites stay as they are. Task 2's reopen case for `income_info` sends `monthly_gross_wages` and `monthly_tips: None`: a writable income field is what drives the reopen.
- **The seeds' nine $0 amounts** are pinned by an assertion on the read-back's input (every one of `IncomeInfo.SOURCE_FIELDS` present and not None), not by a printed box; tier 3's blanks are 2b's.
- **Copy.** The new filer-facing text comes from spec §5.5 (the `IncomeNotSplit` sentence, the legacy message, the rental label "Rental income after the property's costs") and from the owner's ruling (the help text). Nothing else is new.
- **kd 0.** Seed wages equal the old six-month figure, so no box a seed prints changes value.

- [ ] **Step 1: Write the backend tests**

```python file=backend/apps/eligibility/tests/test_cmi.py
"""One current monthly income (CMI) for the means test, the above-median calculator and the forms.

Business intent: CMI decides who passes the means test, which forms a filer gets and what
122A-1 prints, so all three read the same figure. 11 U.S.C. § 101(10A)(B) leaves Social
Security benefits out of CMI; counting them can push a filer over the median (DIG-49).
A total saved before income was stored by source can't be split by anyone but the filer,
so CMI refuses it in plain words instead of guessing (forms step 2 spec §5.5).
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District, MedianIncome
from apps.eligibility.cmi import IncomeNotSplit, current_monthly_income
from apps.eligibility.services.expense_deduction_calculator import ExpenseDeductionCalculator
from apps.eligibility.services.means_test_calculator import MeansTestCalculator
from apps.forms.services.derivations import DERIVATIONS
from apps.intake.models import IncomeInfo, IntakeSession
from apps.users.models import User

SPLIT_BY_SOURCE = "Enter your income by source on the Income step."


@pytest.fixture
def filer(db):
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    MedianIncome.objects.create(
        district=district,
        effective_date=date(2025, 11, 1),
        family_size_1=Decimal("71304.00"),
        family_size_2=Decimal("91526.00"),
        family_size_3=Decimal("110712.00"),
        family_size_4=Decimal("134366.00"),
        family_size_5=Decimal("145466.00"),
        family_size_6=Decimal("156566.00"),
        family_size_7=Decimal("167666.00"),
        family_size_8=Decimal("178766.00"),
        family_size_additional=Decimal("11100.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    return user, session


def test_social_security_never_counts_toward_cmi(filer):
    _, session = filer
    IncomeInfo.objects.create(
        session=session,
        marital_status="single",
        monthly_gross_wages=Decimal("2000.00"),
        monthly_social_security=Decimal("1500.00"),
        monthly_pension=Decimal("500.00"),
    )

    assert current_monthly_income(session.income_info) == Decimal("2500.00")
    assert MeansTestCalculator(session).calculate()["cmi"] == Decimal("2500.00")
    assert DERIVATIONS["cmi"](session) == "2500.00"
    assert ExpenseDeductionCalculator(session)._get_cmi() == Decimal("2500.00")


def test_a_source_left_empty_counts_as_zero_once_another_is_given(filer):
    _, session = filer
    # A journey types only wages, so the other nine are stored empty.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3200.00"))

    assert current_monthly_income(session.income_info) == Decimal("3200.00")


def test_a_filer_who_typed_zero_income_has_a_cmi_of_zero(filer):
    _, session = filer
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("0.00"))

    assert current_monthly_income(session.income_info) == Decimal("0.00")
    assert MeansTestCalculator(session).calculate()["passes_means_test"] is True


def test_a_filer_living_on_social_security_alone_has_a_cmi_of_zero_not_a_refusal(filer):
    _, session = filer
    # Social Security stays out of the sum, but it is still income the filer gave by source:
    # refusing it would stop an SSDI or SSI filer who did exactly what the Income step asks.
    IncomeInfo.objects.create(session=session, monthly_social_security=Decimal("1400.00"))

    assert current_monthly_income(session.income_info) == Decimal("0.00")
    assert MeansTestCalculator(session).calculate()["passes_means_test"] is True
    assert DERIVATIONS["cmi"](session) == "0.00"
    assert ExpenseDeductionCalculator(session)._get_cmi() == Decimal("0.00")


def test_income_saved_only_as_a_total_is_refused_in_plain_words(filer):
    _, session = filer
    IncomeInfo.objects.create(session=session, monthly_income=[3000] * 6)

    with pytest.raises(IncomeNotSplit) as refused:
        current_monthly_income(session.income_info)

    assert str(refused.value) == SPLIT_BY_SOURCE
    assert isinstance(refused.value, ValueError)


def test_the_means_test_passes_the_refusal_on_without_its_failure_prefix(filer):
    _, session = filer
    IncomeInfo.objects.create(session=session, monthly_income=[3000] * 6)

    with pytest.raises(IncomeNotSplit) as refused:
        MeansTestCalculator(session).calculate()

    assert str(refused.value) == SPLIT_BY_SOURCE


def test_other_means_test_failures_keep_their_prefix(filer):
    _, session = filer
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3000.00"))
    MedianIncome.objects.all().delete()

    with pytest.raises(ValueError, match="^Means test calculation failed: No median income"):
        MeansTestCalculator(session).calculate()


def test_the_above_median_calculator_refuses_income_not_split_instead_of_using_zero(filer):
    _, session = filer
    IncomeInfo.objects.create(session=session, monthly_income=[9000] * 6)

    with pytest.raises(IncomeNotSplit):
        ExpenseDeductionCalculator(session).calculate()


def test_means_test_endpoint_asks_for_income_by_source_as_a_400(filer):
    user, session = filer
    IncomeInfo.objects.create(session=session, monthly_income=[3000] * 6)
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(f"/api/intake/sessions/{session.pk}/calculate_means_test/")

    assert response.status_code == 400
    assert response.data["error"] == SPLIT_BY_SOURCE
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/audit/tests/test_upl_compliance.py b/backend/apps/audit/tests/test_upl_compliance.py
index fd4ca55..1d8a974 100644
--- a/backend/apps/audit/tests/test_upl_compliance.py
+++ b/backend/apps/audit/tests/test_upl_compliance.py
@@ -65,9 +65,8 @@ def _create_session_with_income(
 ) -> IntakeSession:
     """Create intake session with income info.

-    monthly_income is the desired CMI (Current Monthly Income).
-    The model stores a 6-month array; we fill all 6 months with the same value
-    so that the average equals the requested CMI.
+    monthly_income is the desired CMI (Current Monthly Income). It is stored as
+    wages, the filer's only income source, so CMI equals it.
     """
     session = IntakeSession.objects.create(user=user, district=district)

@@ -90,7 +89,7 @@ def _create_session_with_income(
         session=session,
         marital_status=marital_status,
         number_of_dependents=number_of_dependents,
-        monthly_income=[float(monthly_income)] * 6,
+        monthly_gross_wages=monthly_income,
     )

     return session
diff --git a/backend/apps/eligibility/tests/test_means_test_calculator.py b/backend/apps/eligibility/tests/test_means_test_calculator.py
index 4706859..bc17d53 100644
--- a/backend/apps/eligibility/tests/test_means_test_calculator.py
+++ b/backend/apps/eligibility/tests/test_means_test_calculator.py
@@ -10,7 +10,7 @@ Tests cover:
 - Fee waiver non-qualification (CMI >= 60% of median)
 - Missing income_info raises ValueError
 - None session raises ValueError
-- Invalid monthly_income (not 6 elements) raises ValueError
+- A total saved before income was stored by source is never read (IncomeNotSplit)
 - UPL prohibited phrase scanning in all messages
 - Recalculation idempotency (calculate twice, only 1 MeansTest record)
 """
@@ -23,6 +23,7 @@ from django.conf import settings
 from django.contrib.auth import get_user_model

 from apps.districts.models import District, MedianIncome
+from apps.eligibility.cmi import IncomeNotSplit
 from apps.eligibility.models import MeansTest
 from apps.eligibility.services.means_test_calculator import MeansTestCalculator
 from apps.forms.registry import build_field_values
@@ -113,7 +114,7 @@ class TestMeansTestCalculatorInitialization:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -133,7 +134,7 @@ class TestBelowMedianIncomePassesMeansTest:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -152,7 +153,7 @@ class TestBelowMedianIncomePassesMeansTest:
             session=session,
             marital_status="married_joint",
             number_of_dependents=0,
-            monthly_income=[7000, 7000, 7000, 7000, 7000, 7000],
+            monthly_gross_wages=Decimal("7000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -171,7 +172,7 @@ class TestBelowMedianIncomePassesMeansTest:
             session=session,
             marital_status="single",
             number_of_dependents=2,
-            monthly_income=[8500, 8500, 8500, 8500, 8500, 8500],
+            monthly_gross_wages=Decimal("8500.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -195,7 +196,7 @@ class TestAboveMedianIncomeFailsMeansTest:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[80000, 80000, 80000, 80000, 80000, 80000],
+            monthly_gross_wages=Decimal("80000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -214,7 +215,7 @@ class TestAboveMedianIncomeFailsMeansTest:
             session=session,
             marital_status="married_separate",
             number_of_dependents=2,
-            monthly_income=[140000, 140000, 140000, 140000, 140000, 140000],
+            monthly_gross_wages=Decimal("140000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -238,7 +239,7 @@ class TestAtMedianIncomeEdgeCase:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5942, 5942, 5942, 5942, 5942, 5942],
+            monthly_gross_wages=Decimal("5942.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -260,7 +261,7 @@ class TestAllHouseholdSizes:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -275,7 +276,7 @@ class TestAllHouseholdSizes:
             session=session,
             marital_status="married_joint",
             number_of_dependents=0,
-            monthly_income=[7000, 7000, 7000, 7000, 7000, 7000],
+            monthly_gross_wages=Decimal("7000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -290,7 +291,7 @@ class TestAllHouseholdSizes:
             session=session,
             marital_status="single",
             number_of_dependents=2,
-            monthly_income=[8000, 8000, 8000, 8000, 8000, 8000],
+            monthly_gross_wages=Decimal("8000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -305,7 +306,7 @@ class TestAllHouseholdSizes:
             session=session,
             marital_status="married_separate",
             number_of_dependents=2,
-            monthly_income=[10000, 10000, 10000, 10000, 10000, 10000],
+            monthly_gross_wages=Decimal("10000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -320,7 +321,7 @@ class TestAllHouseholdSizes:
             session=session,
             marital_status="married_joint",
             number_of_dependents=3,
-            monthly_income=[11000, 11000, 11000, 11000, 11000, 11000],
+            monthly_gross_wages=Decimal("11000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -335,7 +336,7 @@ class TestAllHouseholdSizes:
             session=session,
             marital_status="married_separate",
             number_of_dependents=4,
-            monthly_income=[12000, 12000, 12000, 12000, 12000, 12000],
+            monthly_gross_wages=Decimal("12000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -350,7 +351,7 @@ class TestAllHouseholdSizes:
             session=session,
             marital_status="single",
             number_of_dependents=6,
-            monthly_income=[13000, 13000, 13000, 13000, 13000, 13000],
+            monthly_gross_wages=Decimal("13000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -365,7 +366,7 @@ class TestAllHouseholdSizes:
             session=session,
             marital_status="married_joint",
             number_of_dependents=6,
-            monthly_income=[14000, 14000, 14000, 14000, 14000, 14000],
+            monthly_gross_wages=Decimal("14000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -388,7 +389,7 @@ class TestFeeWaiverQualification:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
+            monthly_gross_wages=Decimal("3000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -403,7 +404,7 @@ class TestFeeWaiverQualification:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[0, 0, 0, 0, 0, 0],
+            monthly_gross_wages=Decimal("0.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -426,7 +427,7 @@ class TestFeeWaiverNonQualification:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[3565.20, 3565.20, 3565.20, 3565.20, 3565.20, 3565.20],
+            monthly_gross_wages=Decimal("3565.20"),
         )

         calculator = MeansTestCalculator(session)
@@ -445,7 +446,7 @@ class TestFeeWaiverNonQualification:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[4166.67, 4166.67, 4166.67, 4166.67, 4166.67, 4166.67],
+            monthly_gross_wages=Decimal("4166.67"),
         )

         calculator = MeansTestCalculator(session)
@@ -456,73 +457,26 @@ class TestFeeWaiverNonQualification:


 @pytest.mark.django_db
-class TestInvalidMonthlyIncomeData:
-    """Tests for invalid monthly_income data validation."""
+class TestTotalSavedBeforeIncomeBySource:
+    """The six-month total saved before step 2 is never read, whatever its shape."""

-    def test_raises_error_with_fewer_than_6_months(self, session, median_income):
-        """Test that monthly_income with < 6 elements raises ValueError."""
+    @pytest.mark.parametrize(
+        "months",
+        [[5000] * 6, [5000] * 3, [5000] * 8, [], "not a list"],
+        ids=["six_months", "three_months", "eight_months", "empty", "not_a_list"],
+    )
+    def test_income_not_split_by_source_is_refused(self, session, median_income, months):
         IncomeInfo.objects.create(
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000],  # Only 3 months
+            monthly_income=months,
         )

         calculator = MeansTestCalculator(session)

         with pytest.raises(
-            ValueError, match="monthly_income must be a list of 6 monthly income values"
-        ):
-            calculator.calculate()
-
-    def test_raises_error_with_more_than_6_months(self, session, median_income):
-        """Test that monthly_income with > 6 elements raises ValueError."""
-        IncomeInfo.objects.create(
-            session=session,
-            marital_status="single",
-            number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000, 5000, 5000],  # 8 months
-        )
-
-        calculator = MeansTestCalculator(session)
-
-        with pytest.raises(
-            ValueError, match="monthly_income must be a list of 6 monthly income values"
-        ):
-            calculator.calculate()
-
-    def test_raises_error_with_empty_list(self, session, median_income):
-        """Test that empty monthly_income list raises ValueError."""
-        IncomeInfo.objects.create(
-            session=session,
-            marital_status="single",
-            number_of_dependents=0,
-            monthly_income=[],  # Empty
-        )
-
-        calculator = MeansTestCalculator(session)
-
-        with pytest.raises(
-            ValueError, match="monthly_income must be a list of 6 monthly income values"
-        ):
-            calculator.calculate()
-
-    def test_raises_error_with_non_list_monthly_income(self, session, median_income):
-        """Test that non-list monthly_income raises ValueError."""
-        # Note: Django JSONField will coerce strings, but not primitives
-        # We create the IncomeInfo directly without JSONField validation
-        income_info = IncomeInfo(
-            session=session,
-            marital_status="single",
-            number_of_dependents=0,
-            monthly_income="not a list",
-        )
-        income_info.save()
-
-        calculator = MeansTestCalculator(session)
-
-        with pytest.raises(
-            ValueError, match="monthly_income must be a list of 6 monthly income values"
+            IncomeNotSplit, match="^Enter your income by source on the Income step.$"
         ):
             calculator.calculate()

@@ -537,7 +491,7 @@ class TestUPLProhibitedPhrases:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -557,7 +511,7 @@ class TestUPLProhibitedPhrases:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[80000, 80000, 80000, 80000, 80000, 80000],
+            monthly_gross_wages=Decimal("80000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -577,7 +531,7 @@ class TestUPLProhibitedPhrases:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
+            monthly_gross_wages=Decimal("3000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -597,7 +551,7 @@ class TestUPLProhibitedPhrases:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -621,7 +575,7 @@ class TestRecalculationIdempotency:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -646,7 +600,7 @@ class TestRecalculationIdempotency:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -656,7 +610,7 @@ class TestRecalculationIdempotency:
         assert result1["passes_means_test"] is True

         # Update income to above median
-        income_info.monthly_income = [80000, 80000, 80000, 80000, 80000, 80000]
+        income_info.monthly_gross_wages = Decimal("80000.00")
         income_info.save()

         # Recalculate with new data
@@ -675,7 +629,7 @@ class TestRecalculationIdempotency:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -726,33 +680,18 @@ class TestRecalculationIdempotency:


 @pytest.mark.django_db
-class TestVariableMonthlyIncome:
-    """Tests for variable monthly income scenarios (6 different values)."""
-
-    def test_variable_income_calculates_correct_average(self, session, median_income):
-        """Test that variable monthly income correctly calculates CMI average."""
-        # Variable income: average should be (6000 + 6000 + 5000 + 5000 + 4000 + 4000) / 6 = 5000
-        IncomeInfo.objects.create(
-            session=session,
-            marital_status="single",
-            number_of_dependents=0,
-            monthly_income=[6000, 6000, 5000, 5000, 4000, 4000],
-        )
-
-        calculator = MeansTestCalculator(session)
-        result = calculator.calculate()
-
-        assert result["cmi"] == Decimal("5000.00")
-        assert result["passes_means_test"] is True
+class TestIncomeFromSeveralSources:
+    """CMI adds up every source the filer gave on the Income step."""

-    def test_declining_income_calculates_correct_average(self, session, median_income):
-        """Test that declining income pattern correctly calculates CMI."""
-        # Declining income: (10000 + 8000 + 6000 + 4000 + 2000 + 0) / 6 = 5000
+    def test_cmi_adds_every_source_the_filer_gave(self, session, median_income):
+        # 3000 + 1000 + 1000 = 5000: below the $5,942/month median for one person
         IncomeInfo.objects.create(
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[10000, 8000, 6000, 4000, 2000, 0],
+            monthly_gross_wages=Decimal("3000.00"),
+            monthly_pension=Decimal("1000.00"),
+            monthly_child_support=Decimal("1000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -772,7 +711,7 @@ class TestDetailedBreakdown:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -791,7 +730,7 @@ class TestDetailedBreakdown:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         calculator = MeansTestCalculator(session)
@@ -807,14 +746,18 @@ class TestDetailedBreakdown:

         # Verify income history
         assert breakdown["income_history"]["average_cmi"] == 5000.00
-        assert breakdown["income_history"]["monthly_values"] == [
-            5000,
-            5000,
-            5000,
-            5000,
-            5000,
-            5000,
-        ]
+        assert breakdown["income_history"]["by_source"] == {
+            "monthly_gross_wages": 5000.0,
+            "monthly_overtime": None,
+            "monthly_tips": None,
+            "monthly_rental_income": None,
+            "monthly_pension": None,
+            "monthly_social_security": None,
+            "monthly_unemployment": None,
+            "monthly_child_support": None,
+            "monthly_alimony": None,
+            "monthly_other_income": None,
+        }

         # Verify family composition
         assert breakdown["family_composition"]["marital_status"] == "single"
@@ -846,7 +789,7 @@ class TestAnnualizedComparison:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[10000, 10000, 10000, 10000, 10000, 10000],
+            monthly_gross_wages=Decimal("10000.00"),
         )

         result = MeansTestCalculator(session).calculate()
@@ -881,7 +824,7 @@ class TestHouseholdSizeFromDebtorInfo:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[9000, 9000, 9000, 9000, 9000, 9000],
+            monthly_gross_wages=Decimal("9000.00"),
         )

         result = MeansTestCalculator(session).calculate()
@@ -920,7 +863,7 @@ def session_with_above_median_income(user, district, median_income):
         session=s,
         marital_status="single",
         number_of_dependents=0,
-        monthly_income=[7000, 7000, 7000, 7000, 7000, 7000],
+        monthly_gross_wages=Decimal("7000.00"),
     )
     return s

@@ -952,7 +895,7 @@ def session_with_below_median_income(user, district, median_income):
         session=s,
         marital_status="single",
         number_of_dependents=0,
-        monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+        monthly_gross_wages=Decimal("5000.00"),
     )
     return s

@@ -1028,7 +971,7 @@ class TestAboveMedianEndToEnd:
         )
         IncomeInfo.objects.create(
             session=session,
-            monthly_income=[6000] * 6,
+            monthly_gross_wages=Decimal("6000.00"),
             marital_status="single",
             number_of_dependents=0,
         )
diff --git a/backend/apps/forms/tests/test_api_readback.py b/backend/apps/forms/tests/test_api_readback.py
index f899d1d..c967b32 100644
--- a/backend/apps/forms/tests/test_api_readback.py
+++ b/backend/apps/forms/tests/test_api_readback.py
@@ -28,7 +28,7 @@ from apps.forms.models import GeneratedForm
 from apps.forms.registry import build_field_values, packet
 from apps.forms.schema import load_schema
 from apps.intake.management.commands.seed_demo_data import PERSONAS
-from apps.intake.models import IntakeSession
+from apps.intake.models import IncomeInfo, IntakeSession

 User = get_user_model()

@@ -55,7 +55,7 @@ def _fee_waiver_application(data):
     """The application the seed stores, as the fee-waiver page sends it."""
     return {
         "household_size": data["debtor"]["household_size"],
-        "monthly_income": data["income"]["monthly_income"][0],
+        "monthly_income": data["income"]["monthly_gross_wages"],
         "monthly_expenses": sum(data["expenses"].values()),
         "receives_public_benefits": False,
         "benefit_types": [],
@@ -67,6 +67,9 @@ def _fee_waiver_application(data):
 def _send_through_the_api(persona):
     """Enter the persona as a filer would, then Generate All. Returns (session id, form types)."""
     data = PERSONAS[persona]()
+    # The typed $0 amounts this sends: each persona typed every Income box, $0 where they
+    # get none of that kind, so no box is left blank.
+    assert all(data["income"][field] is not None for field in IncomeInfo.SOURCE_FIELDS)
     client = APIClient()
     client.force_authenticate(User.objects.create_user(username=f"api_{persona}", password="pw"))

diff --git a/backend/apps/forms/tests/test_derivations.py b/backend/apps/forms/tests/test_derivations.py
index 28344f0..50d0348 100644
--- a/backend/apps/forms/tests/test_derivations.py
+++ b/backend/apps/forms/tests/test_derivations.py
@@ -1,13 +1,14 @@
 """Tests for factual derivations and section predicates."""

 from datetime import date
+from decimal import Decimal

 import pytest
 from django.contrib.auth import get_user_model

 from apps.districts.models import District
 from apps.forms.services.derivations import DERIVATIONS, PREDICATES
-from apps.intake.models import DebtorInfo, IntakeSession
+from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

 User = get_user_model()

@@ -99,3 +100,83 @@ def test_has_attorney_predicate():
         session=session, form_type="form_107", field_key="attorney_gate", value="yes"
     )
     assert PREDICATES["has_attorney"](session) is True
+
+
+# ---------------------------------------------------------------------------
+# Income rules read the Income step's ten amounts (forms step 2 spec §5.5, §7.7)
+# ---------------------------------------------------------------------------
+
+# Each source gets a distinct power of two, so every sum of sources is unique and a rule
+# that reads the wrong source, or adds one too many, returns a different figure.
+TEN_SOURCES = {
+    "monthly_gross_wages": Decimal("1.00"),
+    "monthly_overtime": Decimal("2.00"),
+    "monthly_tips": Decimal("4.00"),
+    "monthly_rental_income": Decimal("8.00"),
+    "monthly_pension": Decimal("16.00"),
+    "monthly_social_security": Decimal("32.00"),
+    "monthly_unemployment": Decimal("64.00"),
+    "monthly_child_support": Decimal("128.00"),
+    "monthly_alimony": Decimal("256.00"),
+    "monthly_other_income": Decimal("512.00"),
+}
+
+# The rules switched in 2a commit 4, with the sources each one adds up (spec §6.2's
+# "Returns"). Their names still describe their old lines until 2b moves the bindings.
+SWITCHED_RULES = {
+    "cmi": [field for field in TEN_SOURCES if field != "monthly_social_security"],
+    "schedule_i_net_wages_debtor1": ["monthly_gross_wages", "monthly_tips"],
+    "schedule_i_rental_debtor1": ["monthly_rental_income"],
+    "schedule_i_child_support_debtor1": ["monthly_child_support", "monthly_alimony"],
+    "schedule_i_unemployment_debtor1": ["monthly_unemployment"],
+    "schedule_i_social_security_debtor1": ["monthly_social_security"],
+    "schedule_i_pension_debtor1": ["monthly_pension"],
+    "schedule_i_other_income_debtor1": ["monthly_other_income"],
+    "line1_wages": ["monthly_gross_wages", "monthly_tips", "monthly_overtime"],
+    "line6b_child_support_alimony": ["monthly_child_support"],
+    "line3_real_property_income": ["monthly_rental_income"],
+    "line6a_unemployment": ["monthly_unemployment"],
+    "line5a_pension_retirement": ["monthly_pension"],
+    "line7_other_income": ["monthly_other_income"],
+}
+
+
+@pytest.mark.parametrize("rule,sources", list(SWITCHED_RULES.items()))
+def test_each_switched_income_rule_returns_its_own_sources_figure(session, rule, sources):
+    IncomeInfo.objects.create(session=session, **TEN_SOURCES)
+
+    expected = sum((TEN_SOURCES[field] for field in sources), Decimal("0"))
+    assert DERIVATIONS[rule](session) == f"{expected:.2f}"
+
+
+@pytest.mark.parametrize("rule", [rule for rule in SWITCHED_RULES if rule != "cmi"])
+def test_an_income_rule_prints_blank_when_the_filer_gave_none_of_its_sources(session, rule):
+    # Every other source was given, so the rule must not borrow one of them.
+    given = {f: a for f, a in TEN_SOURCES.items() if f not in SWITCHED_RULES[rule]}
+    IncomeInfo.objects.create(session=session, **given)
+
+    assert DERIVATIONS[rule](session) == ""
+
+
+@pytest.mark.parametrize("rule", [rule for rule in SWITCHED_RULES if rule != "cmi"])
+def test_an_income_source_typed_as_zero_prints_zero(session, rule):
+    IncomeInfo.objects.create(session=session, **{field: Decimal("0") for field in TEN_SOURCES})
+
+    assert DERIVATIONS[rule](session) == "0.00"
+
+
+def test_an_income_sum_counts_an_empty_source_as_zero(session):
+    # Alimony given, child support left empty: Schedule I's support line still prints.
+    IncomeInfo.objects.create(session=session, monthly_alimony=Decimal("300.00"))
+
+    assert DERIVATIONS["schedule_i_child_support_debtor1"](session) == "300.00"
+
+
+def test_cmi_refuses_a_session_with_no_income_by_source(session):
+    from apps.eligibility.cmi import IncomeNotSplit
+
+    with pytest.raises(IncomeNotSplit):
+        DERIVATIONS["cmi"](session)
+    IncomeInfo.objects.create(session=session, monthly_income=[2500] * 6)
+    with pytest.raises(IncomeNotSplit):
+        DERIVATIONS["cmi"](session)
diff --git a/backend/apps/forms/tests/test_form_106sum_schema.py b/backend/apps/forms/tests/test_form_106sum_schema.py
index ad59ce8..16910a4 100644
--- a/backend/apps/forms/tests/test_form_106sum_schema.py
+++ b/backend/apps/forms/tests/test_form_106sum_schema.py
@@ -7,6 +7,7 @@ import pytest
 from django.contrib.auth import get_user_model

 from apps.districts.models import District
+from apps.eligibility.cmi import IncomeNotSplit
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import (
@@ -80,7 +81,7 @@ def populated_session(session):
         is_secured=False,
         is_priority=True,
     )
-    IncomeInfo.objects.create(session=session, monthly_income=[1200, 1200, 1200, 1200, 1200, 1200])
+    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))
     ExpenseInfo.objects.create(
         session=session,
         rent_or_mortgage=Decimal("1000"),
@@ -126,10 +127,17 @@ class TestForm106SumSchema:

     def test_cmi(self, populated_session):
         field_map = resolve(load_schema("form_106sum"), populated_session)
-        # 1200 * 6 / 6 = 1200.00
+        # 1200 wages = 1200.00 CMI
         assert field_map["8"] == "1200.00"

-    def test_empty_session(self, session):
+    def test_empty_session_is_asked_for_income_by_source(self, session):
+        # Line 8 is CMI, and a filer who gave no income has none to print (spec §5.5).
+        with pytest.raises(IncomeNotSplit):
+            resolve(load_schema("form_106sum"), session)
+
+    def test_a_filer_with_no_property_who_typed_zero_income_prints_zeros(self, session):
+        # Line 1a is not an income box: no real property prints 0.00. Line 8 prints the $0 typed.
+        IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("0.00"))
         field_map = resolve(load_schema("form_106sum"), session)
         assert field_map["1a"] == "0.00"
         assert field_map["8"] == "0.00"
diff --git a/backend/apps/forms/tests/test_form_122a1_schema.py b/backend/apps/forms/tests/test_form_122a1_schema.py
index 5d2f483..0c12daf 100644
--- a/backend/apps/forms/tests/test_form_122a1_schema.py
+++ b/backend/apps/forms/tests/test_form_122a1_schema.py
@@ -6,6 +6,7 @@ import pytest
 from django.contrib.auth import get_user_model

 from apps.districts.models import District
+from apps.eligibility.cmi import IncomeNotSplit
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import IncomeInfo, IntakeSession
@@ -30,7 +31,7 @@ def session(db):
 def session_with_income(session):
     IncomeInfo.objects.create(
         session=session,
-        monthly_income=[2000, 2000, 2000, 2000, 2000, 2000],
+        monthly_gross_wages=Decimal("2000.00"),
         marital_status="single",
         number_of_dependents=0,
     )
@@ -55,9 +56,10 @@ class TestForm122A1Schema:

     def test_cmi_calculation(self, session_with_income):
         field_map = resolve(load_schema("form_122a1"), session_with_income)
-        # 2000 * 6 / 6 = 2000 CMI, annualized = 24000
+        # 2000 wages = 2000 CMI, annualized = 24000
         assert field_map["12B"] == "24000.00"

-    def test_empty_session(self, session):
-        field_map = resolve(load_schema("form_122a1"), session)
-        assert "Bankruptcy District Information" in field_map
+    def test_empty_session_is_asked_for_income_by_source(self, session):
+        # Lines 11 to 13 are CMI, and a filer who gave no income has none (spec §5.5).
+        with pytest.raises(IncomeNotSplit):
+            resolve(load_schema("form_122a1"), session)
diff --git a/backend/apps/forms/tests/test_form_views.py b/backend/apps/forms/tests/test_form_views.py
index 1466444..6c51e64 100644
--- a/backend/apps/forms/tests/test_form_views.py
+++ b/backend/apps/forms/tests/test_form_views.py
@@ -126,7 +126,7 @@ def session_with_income(session_with_debtor):
         session=session_with_debtor,
         marital_status="single",
         number_of_dependents=0,
-        monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
+        monthly_gross_wages=Decimal("3000.00"),
     )
     return session_with_debtor

diff --git a/backend/apps/forms/tests/test_schedule_i_schema.py b/backend/apps/forms/tests/test_schedule_i_schema.py
index db1f0cf..4b8a57b 100644
--- a/backend/apps/forms/tests/test_schedule_i_schema.py
+++ b/backend/apps/forms/tests/test_schedule_i_schema.py
@@ -7,6 +7,7 @@ import pytest
 from django.contrib.auth import get_user_model

 from apps.districts.models import District
+from apps.eligibility.cmi import IncomeNotSplit
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession
@@ -45,7 +46,7 @@ def session_with_income(session):
     )
     IncomeInfo.objects.create(
         session=session,
-        monthly_income=[2000, 2000, 2000, 2000, 2000, 2000],
+        monthly_gross_wages=Decimal("2000.00"),
         marital_status="single",
         number_of_dependents=0,
     )
@@ -72,10 +73,11 @@ class TestScheduleISchema:

     def test_cmi_in_field_map(self, session_with_income):
         field_map = resolve(load_schema("schedule_i"), session_with_income)
-        # 2000 * 6 / 6 = 2000
+        # CMI is the wages, the only source given
         assert field_map["Amount 12"] == "2000.00"
         assert field_map["Amount 10 Debtor 1"] == "2000.00"

-    def test_empty_session(self, session):
-        field_map = resolve(load_schema("schedule_i"), session)
-        assert "Bankruptcy District Information" in field_map
+    def test_empty_session_is_asked_for_income_by_source(self, session):
+        # Lines 10 and 12 print CMI until 2b, and a filer who gave no income has none.
+        with pytest.raises(IncomeNotSplit):
+            resolve(load_schema("schedule_i"), session)
diff --git a/backend/apps/intake/tests/test_completion.py b/backend/apps/intake/tests/test_completion.py
index 8e1cb1b..56bde9a 100644
--- a/backend/apps/intake/tests/test_completion.py
+++ b/backend/apps/intake/tests/test_completion.py
@@ -71,7 +71,7 @@ def completed(filer, district):
         session=session,
         marital_status="single",
         number_of_dependents=0,
-        monthly_income=[3000, 3000, 3000, 3000, 3000, 3000],
+        monthly_gross_wages=Decimal("3000.00"),
     )
     ExpenseInfo.objects.create(session=session)
     return session
@@ -156,7 +156,7 @@ def test_filer_who_leaves_every_expense_blank_can_complete(filer, district):
         state="IL",
         zip_code="60601",
     )
-    IncomeInfo.objects.create(session=session, monthly_income=[0, 0, 0, 0, 0, 0])
+    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("0.00"))

     saved = client.patch(
         _session_url(session), {"expense_info": {"total_monthly_expenses": 0}}, format="json"
@@ -195,7 +195,7 @@ def test_editing_a_completed_intake_asks_for_complete_again(filer, completed):
     "section,value",
     [
         ("debtor_info", {"first_name": "Janet"}),
-        ("income_info", {"monthly_income": [3100, 3100, 3100, 3100, 3100, 3100]}),
+        ("income_info", {"monthly_gross_wages": "3100.00", "monthly_tips": None}),
         ("expense_info", {"rent_or_mortgage": 900}),
         ("debts", [{"creditor_name": "Chase", "debt_type": "credit_card", "amount_owed": 500}]),
         (
diff --git a/backend/apps/intake/tests/test_data_migrations.py b/backend/apps/intake/tests/test_data_migrations.py
index 2ed1692..44ad193 100644
--- a/backend/apps/intake/tests/test_data_migrations.py
+++ b/backend/apps/intake/tests/test_data_migrations.py
@@ -16,6 +16,20 @@ from apps.users.models import User
 BEFORE_STEP_2 = [("intake", "0010_add_adversary_proceedings")]
 BEFORE_BACKFILL = [("intake", "0011_assetinfo_personal_property")]
 BACKFILL = [("intake", "0012_backfill_secured_debts")]
+INCOME_COLUMNS = [("intake", "0013_incomeinfo_income_by_source")]
+INCOME_SPLIT = [("intake", "0014_split_income_saved_as_zero")]
+INCOME_SOURCES = [
+    "monthly_gross_wages",
+    "monthly_overtime",
+    "monthly_tips",
+    "monthly_rental_income",
+    "monthly_pension",
+    "monthly_social_security",
+    "monthly_unemployment",
+    "monthly_child_support",
+    "monthly_alimony",
+    "monthly_other_income",
+]


 @pytest.fixture
@@ -116,3 +130,66 @@ def test_stored_other_assets_stay_other_once_personal_property_exists(migrate):

     AssetInfo = apps.get_model("intake", "AssetInfo")
     assert AssetInfo.objects.get(description="Living room furniture").asset_type == "other"
+
+
+def _income_rows(apps, saved_totals):
+    """One session per saved six-month total, each holding only that total."""
+    user = User.objects.create_user(username="filer", password="pw")
+    district = District.objects.create(
+        code="ILND",
+        name="Illinois Northern",
+        state="IL",
+        court_name="U.S. Bankruptcy Court ILND",
+        filing_fee_chapter_7=Decimal("338.00"),
+    )
+    IntakeSession = apps.get_model("intake", "IntakeSession")
+    IncomeInfo = apps.get_model("intake", "IncomeInfo")
+    for name, months in saved_totals.items():
+        session = IntakeSession.objects.create(user_id=user.pk, district_id=district.pk)
+        IncomeInfo.objects.create(session_id=session.pk, marital_status=name, monthly_income=months)
+
+
+def _stored_income(apps):
+    """Each row's saved total and the set of its ten amounts, keyed by the row's label."""
+    IncomeInfo = apps.get_model("intake", "IncomeInfo")
+    return {
+        row.marital_status: (
+            row.monthly_income,
+            {getattr(row, field) for field in INCOME_SOURCES},
+        )
+        for row in IncomeInfo.objects.all()
+    }
+
+
+# Labelled through marital_status, which the migration doesn't read.
+SAVED_TOTALS = {
+    "above_zero": [3100, 3300, 3200, 3200, 3150, 3250],
+    "zero": [0, 0, 0, 0, 0, 0],
+    "no_months": [],
+}
+AFTER_THE_SPLIT = {
+    "above_zero": (SAVED_TOTALS["above_zero"], {None}),
+    "zero": (SAVED_TOTALS["zero"], {Decimal("0.00")}),
+    "no_months": ([], {None}),
+}
+
+
+def test_a_saved_total_above_zero_waits_for_the_filer_and_zero_becomes_ten_zeros(migrate):
+    # Nothing recorded the amount from each source, so only a $0 total can be split without
+    # the filer: every source was $0. Any other total is kept for the Income step to show.
+    apps = migrate(BACKFILL)
+    _income_rows(apps, SAVED_TOTALS)
+
+    apps = migrate(INCOME_SPLIT)
+
+    assert _stored_income(apps) == AFTER_THE_SPLIT
+
+
+def test_undoing_the_income_split_leaves_income_as_it_is(migrate):
+    apps = migrate(BACKFILL)
+    _income_rows(apps, SAVED_TOTALS)
+    migrate(INCOME_SPLIT)
+
+    apps = migrate(INCOME_COLUMNS)
+
+    assert _stored_income(apps) == AFTER_THE_SPLIT
diff --git a/backend/apps/intake/tests/test_e2e_intake.py b/backend/apps/intake/tests/test_e2e_intake.py
index 6014970..89e65d6 100644
--- a/backend/apps/intake/tests/test_e2e_intake.py
+++ b/backend/apps/intake/tests/test_e2e_intake.py
@@ -396,7 +396,7 @@ class TestIntakeSessionCompletion:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         # Add expense info
@@ -430,7 +430,7 @@ class TestIntakeSessionCompletion:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         ExpenseInfo.objects.create(
@@ -511,7 +511,7 @@ class TestIntakeSessionCompletion:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         url = reverse("intake-session-complete", args=[session.id])
@@ -630,7 +630,7 @@ class TestMeansTestCalculation:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         ExpenseInfo.objects.create(
@@ -669,7 +669,7 @@ class TestMeansTestCalculation:
     def test_calculate_means_test_below_median(self, api_client, complete_session):
         """Test means test with income below median (should pass)."""
         # Update income to be below median ($71,304 annual = $5,942/month)
-        complete_session.income_info.monthly_income = [4000, 4000, 4000, 4000, 4000, 4000]
+        complete_session.income_info.monthly_gross_wages = Decimal("4000.00")
         complete_session.income_info.save()

         url = reverse("intake-session-calculate-means-test", args=[complete_session.id])
@@ -684,7 +684,7 @@ class TestMeansTestCalculation:
         """Test means test with income above median (should fail)."""
         # Note: calculator compares monthly CMI to annual threshold directly.
         # Median is $71,304 annual, so CMI must exceed that to fail.
-        complete_session.income_info.monthly_income = [80000, 80000, 80000, 80000, 80000, 80000]
+        complete_session.income_info.monthly_gross_wages = Decimal("80000.00")
         complete_session.income_info.save()

         url = reverse("intake-session-calculate-means-test", args=[complete_session.id])
@@ -712,7 +712,7 @@ class TestMeansTestCalculation:
     def test_fee_waiver_qualification(self, api_client, complete_session, median_income):
         """Test fee waiver qualification for income < 150% poverty line."""
         # Set income very low for fee waiver (150% of poverty line ~$22k annual = $1,833/month)
-        complete_session.income_info.monthly_income = [1500, 1500, 1500, 1500, 1500, 1500]
+        complete_session.income_info.monthly_gross_wages = Decimal("1500.00")
         complete_session.income_info.save()

         url = reverse("intake-session-calculate-means-test", args=[complete_session.id])
@@ -752,7 +752,7 @@ class TestSessionSummary:
             session=session,
             marital_status="single",
             number_of_dependents=0,
-            monthly_income=[5000, 5000, 5000, 5000, 5000, 5000],
+            monthly_gross_wages=Decimal("5000.00"),
         )

         # Add an asset
diff --git a/backend/apps/intake/tests/test_income_resume.py b/backend/apps/intake/tests/test_income_resume.py
index 7f4660b..0d03b1f 100644
--- a/backend/apps/intake/tests/test_income_resume.py
+++ b/backend/apps/intake/tests/test_income_resume.py
@@ -1,27 +1,46 @@
-"""A filer who reopens the Income step keeps the income they saved (DIG-41).
+"""A filer's income is stored by source, as the Income step's ten boxes name it (spec §5.5).

-Only ``IncomeInfo.monthly_income`` (six months) is stored. The step's per-source boxes
-never reach the server, so the step shows the saved total the API reports, and saves send
-``monthly_income`` alone.
+Business intent: the court forms ask for each kind of income on its own line, and the means
+test leaves Social Security out, so a single total can't fill them. A box the filer left
+empty stays empty, never $0, because a $0 the filer never gave would be sworn on a form.
+The old six-month total is kept, read-only, for one release: it is the only record of what
+an earlier filer entered, and the Income step shows it while asking them to split it.
 """

+from datetime import date
 from decimal import Decimal

 import pytest
 from rest_framework.test import APIClient

 from apps.districts.models import District
-from apps.intake.models import IncomeInfo, IntakeSession
+from apps.intake.models import DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession
 from apps.users.models import User

+SPLIT_BY_SOURCE = "Enter your income by source on the Income step."
+
+TEN_EMPTY = {
+    "monthly_gross_wages": None,
+    "monthly_overtime": None,
+    "monthly_tips": None,
+    "monthly_rental_income": None,
+    "monthly_pension": None,
+    "monthly_social_security": None,
+    "monthly_unemployment": None,
+    "monthly_child_support": None,
+    "monthly_alimony": None,
+    "monthly_other_income": None,
+}
+

 @pytest.fixture
 def filer_session(db):
+    # The name is one of the court forms' district choices, so forms fill.
     district = District.objects.create(
-        code="ILND",
-        name="Illinois Northern",
+        code="ilnd",
+        name="Northern District of Illinois",
         state="IL",
-        court_name="U.S. Bankruptcy Court ILND",
+        court_name="U.S. Bankruptcy Court, Northern District of Illinois",
         filing_fee_chapter_7=Decimal("338.00"),
     )
     filer = User.objects.create_user(username="filer", password="pw")
@@ -31,43 +50,82 @@ def filer_session(db):
     return client, session


+def _session_url(session, action=""):
+    return f"/api/intake/sessions/{session.pk}/{action}"
+
+
 @pytest.mark.django_db
-class TestIncomeStepResume:
-    def test_returning_filer_gets_their_saved_monthly_income_total(self, filer_session):
+class TestIncomeBySource:
+    def test_new_filer_saves_income_by_source_without_a_total(self, filer_session):
         client, session = filer_session
-        IncomeInfo.objects.create(
-            session=session,
-            marital_status="single",
-            monthly_income=[3100, 3300, 3200, 3200, 3150, 3250],
-        )

-        resp = client.get(f"/api/intake/sessions/{session.pk}/")
+        resp = client.patch(
+            _session_url(session),
+            {
+                "income_info": {
+                    **TEN_EMPTY,
+                    "monthly_gross_wages": "3200.00",
+                    "monthly_social_security": "0",
+                }
+            },
+            format="json",
+        )

         assert resp.status_code == 200
-        assert resp.json()["income_info"]["total_monthly_income"] == 3200.0
-
-    def test_saved_total_is_shown_to_the_cent(self, filer_session):
+        income = IncomeInfo.objects.get(session=session)
+        assert income.monthly_gross_wages == Decimal("3200.00")
+        assert income.monthly_social_security == Decimal("0.00")
+        # A box the filer left empty is stored empty, not as $0.
+        assert income.monthly_overtime is None
+        assert income.monthly_other_income is None
+        # The old total is never written again.
+        assert income.monthly_income is None
+        assert resp.data["income_info"]["total_monthly_income"] == 3200.0
+
+    def test_returning_filer_gets_each_saved_amount_back(self, filer_session):
         client, session = filer_session
         IncomeInfo.objects.create(
             session=session,
-            marital_status="single",
-            monthly_income=[1000, 1000, 1000, 1000, 1000, 1001],
+            monthly_gross_wages=Decimal("3100.50"),
+            monthly_tips=Decimal("0.00"),
+            monthly_social_security=Decimal("900.25"),
         )

-        resp = client.get(f"/api/intake/sessions/{session.pk}/")
+        resp = client.get(_session_url(session))

-        assert resp.json()["income_info"]["total_monthly_income"] == 1000.17
+        income = resp.json()["income_info"]
+        assert income["monthly_gross_wages"] == "3100.50"
+        assert income["monthly_tips"] == "0.00"
+        assert income["monthly_overtime"] is None
+        # The total adds every source the filer gave, Social Security included.
+        assert income["total_monthly_income"] == 4000.75

-    def test_row_without_months_reports_zero_instead_of_breaking_the_session_read(
+    def test_a_saved_total_stays_readable_so_the_income_step_can_ask_to_split_it(
         self, filer_session
     ):
         client, session = filer_session
-        IncomeInfo.objects.create(session=session, marital_status="single", monthly_income=[])
+        IncomeInfo.objects.create(session=session, monthly_income=[3100, 3300, 3200] * 2)
+
+        income = client.get(_session_url(session)).json()["income_info"]

-        resp = client.get(f"/api/intake/sessions/{session.pk}/")
+        assert income["monthly_income"] == [3100, 3300, 3200] * 2
+        assert {field: income[field] for field in TEN_EMPTY} == TEN_EMPTY
+        assert income["total_monthly_income"] is None
+
+    def test_a_total_sent_by_an_old_page_is_not_stored(self, filer_session):
+        client, session = filer_session
+        IncomeInfo.objects.create(session=session, monthly_income=[2500] * 6)
+
+        resp = client.patch(
+            _session_url(session),
+            {"income_info": {"monthly_income": [4000] * 6, "monthly_gross_wages": "4000"}},
+            format="json",
+        )

         assert resp.status_code == 200
-        assert resp.json()["income_info"]["total_monthly_income"] == 0.0
+        income = IncomeInfo.objects.get(session=session)
+        assert income.monthly_income == [2500] * 6
+        assert income.monthly_gross_wages == Decimal("4000.00")

     def test_saving_income_amounts_keeps_household_details(self, filer_session):
         client, session = filer_session
@@ -75,37 +133,108 @@ class TestIncomeStepResume:
             session=session,
             marital_status="married_joint",
             number_of_dependents=2,
-            monthly_income=[2500] * 6,
+            monthly_gross_wages=Decimal("2500.00"),
         )

         resp = client.patch(
-            f"/api/intake/sessions/{session.pk}/",
-            {"income_info": {"monthly_income": [4000] * 6}},
+            _session_url(session),
+            {"income_info": {**TEN_EMPTY, "monthly_gross_wages": "4000"}},
             format="json",
         )

         assert resp.status_code == 200
         income = IncomeInfo.objects.get(session=session)
-        assert income.monthly_income == [4000] * 6
+        assert income.monthly_gross_wages == Decimal("4000.00")
         assert income.marital_status == "married_joint"
         assert income.number_of_dependents == 2

     def test_a_wizard_created_row_echoed_back_whole_would_strand_the_filer(self, filer_session):
-        # Why the wizard sends monthly_income alone: a row the wizard created has a blank
+        # Why the wizard sends the ten amounts alone: a row the wizard created has a blank
         # marital_status, and sending the row back as read is a 400 that strands the filer.
         client, session = filer_session
-        IncomeInfo.objects.create(session=session, monthly_income=[3200] * 6)
+        IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3200.00"))

         resp = client.patch(
-            f"/api/intake/sessions/{session.pk}/",
+            _session_url(session),
             {
                 "income_info": {
                     "marital_status": "",
                     "number_of_dependents": 0,
-                    "monthly_income": [3200] * 6,
+                    "monthly_gross_wages": "3200.00",
                 }
             },
             format="json",
         )

         assert resp.status_code == 400
+
+    @pytest.mark.parametrize(
+        "amount",
+        ["-1.00", "100000000.00", "NaN", "Infinity", "12.345"],
+        ids=["negative", "too_wide", "nan", "infinite", "fraction_of_a_cent"],
+    )
+    def test_an_income_amount_outside_the_column_is_refused(self, filer_session, amount):
+        client, session = filer_session
+
+        resp = client.patch(
+            _session_url(session),
+            {"income_info": {"monthly_pension": amount}},
+            format="json",
+        )
+
+        assert resp.status_code == 400
+        assert not IncomeInfo.objects.filter(session=session).exists()
+
+    def test_the_largest_amount_the_column_holds_is_saved(self, filer_session):
+        client, session = filer_session
+
+        resp = client.patch(
+            _session_url(session),
+            {"income_info": {"monthly_pension": "99999999.99"}},
+            format="json",
+        )
+
+        assert resp.status_code == 200
+        assert IncomeInfo.objects.get(session=session).monthly_pension == Decimal("99999999.99")
+
+
+def _complete(session):
+    DebtorInfo.objects.create(
+        session=session,
+        first_name="Jane",
+        last_name="Doe",
+        ssn="900-12-3456",  # IRS-reserved range: synthetic
+        date_of_birth=date(1990, 1, 15),
+        phone="312-555-0100",
+        email="jane.doe@example.com",
+        street_address="123 Main St",
+        city="Chicago",
+        state="IL",
+        zip_code="60601",
+    )
+    ExpenseInfo.objects.create(session=session)
+    session.status = "completed"
+    session.save()
+
+
+def test_legacy_income_total_must_be_split_before_forms_print(filer_session):
+    client, session = filer_session
+    IncomeInfo.objects.create(session=session, monthly_income=[3000] * 6)
+    _complete(session)
+    generate = {"session_id": session.pk, "form_type": "schedule_i"}
+
+    refused = client.post("/api/forms/generate/", generate, format="json")
+    assert refused.status_code == 422
+    assert refused.data == {"form_type": "schedule_i", "error": SPLIT_BY_SOURCE}
+    every_form = client.post("/api/forms/generate_all/", {"session_id": session.pk}, format="json")
+    assert {"form_type": "schedule_i", "error": SPLIT_BY_SOURCE} in every_form.data["errors"]
+
+    # The filer splits the total on the Income step and completes the intake again.
+    split = client.patch(
+        _session_url(session),
+        {"income_info": {**TEN_EMPTY, "monthly_gross_wages": "3000"}},
+        format="json",
+    )
+    assert split.status_code == 200
+    assert client.post(_session_url(session, "complete/")).status_code == 200
+    assert client.post("/api/forms/generate/", generate, format="json").status_code == 200
PATCH
```

`test_cmi.py` checks the one CMI function from all four consumers: the function itself, `MeansTestCalculator`, the `cmi` rule and `_get_cmi`. Social Security never counts, an empty amount counts as zero once another is given, a filer on Social Security alone gets $0, and a filer who gave nothing is refused in plain words: unprefixed by the means test, as a 400 from its endpoint, and never as a CMI of 0 in the above-median calculator.

`test_income_resume.py` is rewritten for income by source: a new filer's empty boxes stay NULL and no total is written, a returning filer gets each amount back, a saved total stays readable but a total sent by an old page is not stored, each out-of-range amount is a 400, and `test_legacy_income_total_must_be_split_before_forms_print` refuses Generate and Generate All until the filer splits the total and presses Complete again. `test_derivations.py` runs each switched rule on a session with ten distinct powers of two, so every sum is unique, and checks that each prints blank when none of its sources was given and 0.00 when the filer typed $0. `test_data_migrations.py` runs 0013 and 0014 forward from 0012 rows and back again.

The other files move their fixtures from `monthly_income=[X] * 6` to `monthly_gross_wages=Decimal("X")` with the same intent. `TestInvalidMonthlyIncomeData` becomes `TestTotalSavedBeforeIncomeBySource`, which expects the unprefixed `IncomeNotSplit` for a session holding only months, and `TestVariableMonthlyIncome` becomes `TestIncomeFromSeveralSources`.

- [ ] **Step 2: Run the CMI tests and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/eligibility/tests/test_cmi.py -q -p no:cacheprovider 2>&1 | tail -5
```

Expected: FAIL — `ModuleNotFoundError: No module named 'apps.eligibility.cmi'`. There is no one CMI function yet.

- [ ] **Step 3: Run the storage and rule tests and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_income_resume.py apps/intake/tests/test_data_migrations.py apps/forms/tests/test_derivations.py -q -p no:cacheprovider 2>&1 | tail -3
```

Expected: FAIL — `57 failed, 13 passed`. IncomeInfo has none of the ten columns yet, so most tests that store income by source fail with a TypeError naming them. The migration tests find no 0014, the cmi rule test finds no apps.eligibility.cmi, each out-of-range amount goes to a key the serializer doesn't know yet and is dropped (a 200 where the test wants a 400), and the legacy filer's Generate gets a 200 where the test wants the 422.

- [ ] **Step 4: Store the ten amounts**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/models.py b/backend/apps/intake/models.py
index 16d3efd..a8b74d3 100644
--- a/backend/apps/intake/models.py
+++ b/backend/apps/intake/models.py
@@ -87,6 +87,20 @@ class DebtorInfo(models.Model):
 class IncomeInfo(models.Model):
     """Income data for means test."""

+    # The Income step's ten monthly amounts, by source (forms step 2 spec §5.5)
+    SOURCE_FIELDS: ClassVar[tuple[str, ...]] = (
+        "monthly_gross_wages",
+        "monthly_overtime",
+        "monthly_tips",
+        "monthly_rental_income",
+        "monthly_pension",
+        "monthly_social_security",
+        "monthly_unemployment",
+        "monthly_child_support",
+        "monthly_alimony",
+        "monthly_other_income",
+    )
+
     session = models.OneToOneField(
         IntakeSession, on_delete=models.CASCADE, related_name="income_info"
     )
@@ -99,7 +113,86 @@ class IncomeInfo(models.Model):
         ],
     )
     number_of_dependents = models.IntegerField(default=0)
-    monthly_income = models.JSONField(help_text="6-month income array")  # [month1, month2, ...]
+    # The total the Income step saved before step 2. It is no longer written, and stays for
+    # one release as the only record of what an earlier filer entered.
+    monthly_income = models.JSONField(
+        null=True, blank=True, help_text="6-month income array"
+    )  # [month1, month2, ...]
+    # No default: an amount the filer never gave stays empty. A default of 0 would give
+    # every earlier filer $0 income, and so a passed means test.
+    monthly_gross_wages = models.DecimalField(
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        validators=[MinValueValidator(Decimal("0"))],
+    )
+    monthly_overtime = models.DecimalField(
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        validators=[MinValueValidator(Decimal("0"))],
+    )
+    monthly_tips = models.DecimalField(
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        validators=[MinValueValidator(Decimal("0"))],
+    )
+    monthly_rental_income = models.DecimalField(
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        validators=[MinValueValidator(Decimal("0"))],
+        help_text="After the property's costs",
+    )
+    monthly_pension = models.DecimalField(
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        validators=[MinValueValidator(Decimal("0"))],
+    )
+    monthly_social_security = models.DecimalField(
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        validators=[MinValueValidator(Decimal("0"))],
+    )
+    monthly_unemployment = models.DecimalField(
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        validators=[MinValueValidator(Decimal("0"))],
+    )
+    monthly_child_support = models.DecimalField(
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        validators=[MinValueValidator(Decimal("0"))],
+        help_text="Child support received",
+    )
+    monthly_alimony = models.DecimalField(
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        validators=[MinValueValidator(Decimal("0"))],
+        help_text="Alimony received",
+    )
+    monthly_other_income = models.DecimalField(
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        validators=[MinValueValidator(Decimal("0"))],
+    )
     created_at = models.DateTimeField(auto_now_add=True)

     class Meta:
@@ -111,17 +204,18 @@ class IncomeInfo(models.Model):
             f"(Session: {self.session_id})"
         )

-    def calculate_total_monthly_income(self) -> float:
-        """Average monthly income over the stored months, to the cent.
+    def calculate_total_monthly_income(self) -> float | None:
+        """The ten monthly amounts added up, Social Security included.

-        Only the 6-month array is stored, never the per-source amounts the filer typed,
-        so this is the saved total the Income step shows when it reopens.
+        An amount left empty counts as zero once another one was given. None when the filer
+        gave none of them, so a total saved before step 2 never reads as $0.
         """
-        months = self.monthly_income or []
-        if not months:
-            return 0.0
-        total = sum(Decimal(str(amount)) for amount in months)
-        return float((total / len(months)).quantize(Decimal("0.01")))
+        given = [
+            getattr(self, field) for field in self.SOURCE_FIELDS if getattr(self, field) is not None
+        ]
+        if not given:
+            return None
+        return float(sum(given, Decimal("0")))


 class ExpenseInfo(models.Model):
PATCH
```

```python file=backend/apps/intake/migrations/0013_incomeinfo_income_by_source.py
# Generated by Django 5.0.14 on 2026-10-13 06:15

from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("intake", "0012_backfill_secured_debts"),
    ]

    operations = [
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_alimony",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Alimony received",
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_child_support",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Child support received",
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_gross_wages",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_other_income",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_overtime",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_pension",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_rental_income",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="After the property's costs",
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_social_security",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_tips",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AddField(
            model_name="incomeinfo",
            name="monthly_unemployment",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("0"))],
            ),
        ),
        migrations.AlterField(
            model_name="incomeinfo",
            name="monthly_income",
            field=models.JSONField(blank=True, help_text="6-month income array", null=True),
        ),
    ]
```

```python file=backend/apps/intake/migrations/0014_split_income_saved_as_zero.py
"""Income saved as a $0 total becomes ten $0 amounts (forms step 2 spec §5.5, §7.8).

Before step 2 only the six-month total was stored, and nothing recorded the amount from each
source. A $0 total loses nothing when split: every source was $0. Any other total leaves
the ten amounts empty, so the Income step asks the filer to split it and income forms
refuse until they do. The old total itself is left as it is.
"""

from decimal import Decimal, InvalidOperation

from django.db import migrations

INCOME_SOURCES = [
    "monthly_gross_wages",
    "monthly_overtime",
    "monthly_tips",
    "monthly_rental_income",
    "monthly_pension",
    "monthly_social_security",
    "monthly_unemployment",
    "monthly_child_support",
    "monthly_alimony",
    "monthly_other_income",
]


def _saved_total_is_zero(months) -> bool:
    # No months saved means no total, not a $0 one.
    if not isinstance(months, list) or not months:
        return False
    try:
        return sum(Decimal(str(month)) for month in months) == 0
    except InvalidOperation:
        return False


def split_income_saved_as_zero(apps, schema_editor):
    IncomeInfo = apps.get_model("intake", "IncomeInfo")
    for income in IncomeInfo.objects.all():
        if _saved_total_is_zero(income.monthly_income):
            for field in INCOME_SOURCES:
                setattr(income, field, Decimal("0.00"))
            income.save(update_fields=INCOME_SOURCES)


class Migration(migrations.Migration):

    dependencies = [
        ("intake", "0013_incomeinfo_income_by_source"),
    ]

    operations = [
        migrations.RunPython(split_income_saved_as_zero, migrations.RunPython.noop),
    ]
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/serializers.py b/backend/apps/intake/serializers.py
index b2c5209..2736e19 100644
--- a/backend/apps/intake/serializers.py
+++ b/backend/apps/intake/serializers.py
@@ -71,7 +71,11 @@ class DebtorInfoSerializer(serializers.ModelSerializer):


 class IncomeInfoSerializer(serializers.ModelSerializer):
-    """Serializer for income information."""
+    """Serializer for income information, stored by source (forms step 2 spec §5.5).
+
+    monthly_income, the total saved before step 2, is read-only: the Income step shows it
+    while asking the filer to split it.
+    """

     total_monthly_income = serializers.SerializerMethodField()

@@ -80,47 +84,17 @@ class IncomeInfoSerializer(serializers.ModelSerializer):
         fields = [
             "marital_status",
             "number_of_dependents",
+            *IncomeInfo.SOURCE_FIELDS,
             "monthly_income",
             "total_monthly_income",
             "created_at",
         ]
-        read_only_fields = ["created_at", "total_monthly_income"]
+        read_only_fields = ["created_at", "monthly_income", "total_monthly_income"]

     def get_total_monthly_income(self, obj):
-        """Return the saved monthly income total (the average of the stored months)."""
+        """Return the ten amounts added up, or None when the filer gave none of them."""
         return obj.calculate_total_monthly_income()

-    def validate_monthly_income(self, value):
-        """
-        Validate monthly_income is a list of 6 positive numbers.
-
-        Args:
-            value: List of monthly income amounts
-
-        Returns:
-            list: Validated monthly income list
-
-        Raises:
-            ValidationError: If format is invalid
-        """
-        if not isinstance(value, list):
-            raise serializers.ValidationError("Please provide income as a list of monthly amounts")
-
-        if len(value) != 6:
-            raise serializers.ValidationError("Please provide income for the last 6 months")
-
-        for i, amount in enumerate(value):
-            try:
-                float_amount = float(amount)
-                if float_amount < 0:
-                    raise serializers.ValidationError(f"Income for month {i+1} cannot be negative")
-            except (TypeError, ValueError) as err:
-                raise serializers.ValidationError(
-                    f"Income for month {i+1} must be a valid number"
-                ) from err
-
-        return value
-

 class ExpenseInfoSerializer(serializers.ModelSerializer):
     """Serializer for monthly expense information."""
PATCH
```

`IncomeInfo` gains the ten amounts under the step's names, empty when the filer gave none, with no default, because $0 would pass every earlier filer's means test. The old six-month total becomes optional and read-only and stays for one release. Write 0013 exactly as given, with its generated header; regenerating it changes the timestamp line. 0014 turns a saved $0 total into ten $0 amounts and leaves any other total for the filer to split, without touching the old column.

- [ ] **Step 5: Work CMI out in one place**

```python file=backend/apps/eligibility/cmi.py
"""
Current monthly income (CMI), the one figure the means test, the above-median calculator
and the court forms share (forms step 2 spec §5.5).

CMI counts the filer's monthly income from every source the Income step asks about except
benefits under the Social Security Act, which 11 U.S.C. § 101(10A)(B) leaves out.
"""

from decimal import Decimal


class IncomeNotSplit(ValueError):
    """The filer hasn't entered their income by source, so CMI can't be worked out.

    A total saved before income was stored by source can't be split by anyone but the filer.
    """

    def __init__(self) -> None:
        super().__init__("Enter your income by source on the Income step.")


def current_monthly_income(income_info) -> Decimal:
    """The ten Income step amounts added up, without Social Security.

    An amount the filer left empty counts as zero once another one was given.

    Raises:
        IncomeNotSplit: the filer gave none of the ten amounts.
    """
    given = {
        field: getattr(income_info, field)
        for field in income_info.SOURCE_FIELDS
        if getattr(income_info, field) is not None
    }
    if not given:
        raise IncomeNotSplit()
    return sum(
        (amount for field, amount in given.items() if field != "monthly_social_security"),
        Decimal("0"),
    )
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/eligibility/models.py b/backend/apps/eligibility/models.py
index 98614b0..601a32c 100644
--- a/backend/apps/eligibility/models.py
+++ b/backend/apps/eligibility/models.py
@@ -7,6 +7,8 @@ from django.db import models
 from django.utils import timezone
 from encrypted_model_fields.fields import EncryptedTextField

+from .cmi import current_monthly_income
+

 class MeansTest(models.Model):
     """Chapter 7 means test calculation (11 U.S.C. § 707(b))."""
@@ -104,13 +106,8 @@ class MeansTest(models.Model):
         except AttributeError as err:
             raise ValueError("IntakeSession must have income_info to calculate means test") from err

-        # Calculate Current Monthly Income (CMI) - average of last 6 months
-        monthly_income_data = income_info.monthly_income
-        if not isinstance(monthly_income_data, list) or len(monthly_income_data) != 6:
-            raise ValueError("monthly_income must be a list of 6 monthly income values")
-
-        total_6_month_income = sum(Decimal(str(amt)) for amt in monthly_income_data)
-        cmi = total_6_month_income / Decimal("6")
+        # Current Monthly Income (CMI): the Income step's amounts, without Social Security
+        cmi = current_monthly_income(income_info)

         # Get family size for median income lookup. The wizard collects
         # household_size on the debtor step; sessions without it fall back
@@ -171,14 +168,18 @@ class MeansTest(models.Model):
         # For MVP, simplified: qualifies if income is very low (< 60% of median)
         qualifies_fee_waiver = annualized_cmi < (median_income_threshold * Decimal("0.60"))

-        # Store calculation details (encrypted)
+        # Store calculation details (encrypted). JSON has no Decimal, and an empty box stays empty.
+        income_by_source = {}
+        for field in income_info.SOURCE_FIELDS:
+            amount = getattr(income_info, field)
+            income_by_source[field] = None if amount is None else float(amount)
         details.update(
             {
                 "cmi": float(cmi),
                 "annualized_cmi": float(annualized_cmi),
                 "median_income_threshold": float(median_income_threshold),
                 "family_size": family_size,
-                "monthly_income_breakdown": monthly_income_data,
+                "income_by_source": income_by_source,
                 "marital_status": income_info.marital_status,
                 "number_of_dependents": income_info.number_of_dependents,
                 "passes_test": passes_test,
diff --git a/backend/apps/eligibility/services/expense_deduction_calculator.py b/backend/apps/eligibility/services/expense_deduction_calculator.py
index a15de45..4629e8b 100644
--- a/backend/apps/eligibility/services/expense_deduction_calculator.py
+++ b/backend/apps/eligibility/services/expense_deduction_calculator.py
@@ -3,6 +3,7 @@
 from dataclasses import dataclass
 from decimal import Decimal

+from apps.eligibility.cmi import current_monthly_income
 from apps.eligibility.services.irs_standards import get_local_standard, get_national_standard
 from apps.intake.models import IntakeSession

@@ -109,9 +110,8 @@ class ExpenseDeductionCalculator:
         return sum((d.monthly_payment or zero for d in priority), zero)

     def _get_cmi(self) -> Decimal:
-        try:
-            ii = self.session.income_info
-            total = sum(Decimal(str(v)) for v in (ii.monthly_income or []))
-            return total / Decimal("6") if total else Decimal("0")
-        except Exception:
+        # The means test's own CMI. Income not split by source raises IncomeNotSplit.
+        ii = getattr(self.session, "income_info", None)
+        if ii is None:
             return Decimal("0")
+        return current_monthly_income(ii)
diff --git a/backend/apps/eligibility/services/means_test_calculator.py b/backend/apps/eligibility/services/means_test_calculator.py
index e4bdb34..4b1f7a1 100644
--- a/backend/apps/eligibility/services/means_test_calculator.py
+++ b/backend/apps/eligibility/services/means_test_calculator.py
@@ -10,6 +10,7 @@ from typing import Any

 from django.db import transaction

+from apps.eligibility.cmi import IncomeNotSplit
 from apps.eligibility.models import MeansTest
 from apps.intake.models import IntakeSession

@@ -78,9 +79,11 @@ class MeansTestCalculator:
         if not created:
             means_test.district = self.district

-        # Perform calculation
+        # Perform calculation. Income not split by source already says what to do.
         try:
             means_test.calculate()
+        except IncomeNotSplit:
+            raise
         except ValueError as e:
             raise ValueError(f"Means test calculation failed: {str(e)}") from e

@@ -196,7 +199,7 @@ class MeansTestCalculator:

         return {
             "income_history": {
-                "monthly_values": details.get("monthly_income_breakdown", []),
+                "by_source": details.get("income_by_source", {}),
                 "average_cmi": float(means_test.calculated_cmi),
             },
             "family_composition": {
PATCH
```

CMI is the ten amounts without Social Security (11 U.S.C. § 101(10A)(B), DIG-49). The means test, and so the fee-waiver flag, the above-median calculator and (in the next step) the forms' `cmi` rule all call `current_monthly_income`. The calculator re-raises `IncomeNotSplit` as it is, so the endpoint's 400 carries the plain sentence.

- [ ] **Step 6: Switch the income rules, and refuse a form in plain words**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index 7380295..b81f6d4 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -14,6 +14,7 @@ from datetime import date
 from decimal import Decimal
 from functools import reduce

+from apps.eligibility.cmi import IncomeNotSplit, current_monthly_income
 from apps.intake.models import IntakeSession

 _ZERO = Decimal("0.00")
@@ -69,6 +70,20 @@ def _sum_encrypted(queryset, field_name: str) -> Decimal:
     return reduce(lambda acc, obj: acc + (getattr(obj, field_name) or _ZERO), queryset, _ZERO)


+def _income_amounts(session: IntakeSession, *fields: str) -> str:
+    """The sum of these Income step amounts, or blank when the filer gave none of them.
+
+    An amount left empty counts as zero once another one was given (step 2 spec §6.1, B2).
+    """
+    income_info = getattr(session, "income_info", None)
+    if income_info is None:
+        return ""
+    given = [getattr(income_info, f) for f in fields if getattr(income_info, f) is not None]
+    if not given:
+        return ""
+    return _fmt(sum(given, _ZERO))
+
+
 # ---------------------------------------------------------------------------
 # Form 106Sum aggregation derivations
 # ---------------------------------------------------------------------------
@@ -157,12 +172,9 @@ def _cmi(session: IntakeSession) -> str:
     try:
         income_info = session.income_info
     except IncomeInfo.DoesNotExist:
-        return "0.00"
-    monthly = getattr(income_info, "monthly_income", None) or []
-    if not monthly:
-        return "0.00"
-    total = reduce(lambda acc, v: acc + Decimal(str(v)), monthly, _ZERO)
-    return _fmt(total / Decimal("6"))
+        # No income at all is income not entered by source.
+        raise IncomeNotSplit() from None
+    return _fmt(current_monthly_income(income_info))


 def _total_monthly_expenses(session: IntakeSession) -> str:
@@ -194,7 +206,7 @@ def _get_income_field(session: IntakeSession, field: str) -> Decimal:


 def _line1_wages(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "wages_salaries_tips"))
+    return _income_amounts(session, "monthly_gross_wages", "monthly_tips", "monthly_overtime")


 def _line2_business_income(session: IntakeSession) -> str:
@@ -202,7 +214,7 @@ def _line2_business_income(session: IntakeSession) -> str:


 def _line3_real_property_income(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "real_property_income"))
+    return _income_amounts(session, "monthly_rental_income")


 def _line4_interest_dividends(session: IntakeSession) -> str:
@@ -210,7 +222,7 @@ def _line4_interest_dividends(session: IntakeSession) -> str:


 def _line5a_pension_retirement(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "pension_retirement"))
+    return _income_amounts(session, "monthly_pension")


 def _line5b_social_security(session: IntakeSession) -> str:
@@ -218,15 +230,15 @@ def _line5b_social_security(session: IntakeSession) -> str:


 def _line6a_unemployment(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "unemployment_compensation"))
+    return _income_amounts(session, "monthly_unemployment")


 def _line6b_child_support_alimony(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "child_support_alimony"))
+    return _income_amounts(session, "monthly_child_support")


 def _line7_other_income(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "other_income"))
+    return _income_amounts(session, "monthly_other_income")


 def _line8a_total_gross_income(session: IntakeSession) -> str:
@@ -348,7 +360,7 @@ def _schedule_i_gross_wages_debtor1(session: IntakeSession) -> str:


 def _schedule_i_net_wages_debtor1(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "wages_salaries_tips"))
+    return _income_amounts(session, "monthly_gross_wages", "monthly_tips")


 def _schedule_i_self_employment_debtor1(session: IntakeSession) -> str:
@@ -356,19 +368,19 @@ def _schedule_i_self_employment_debtor1(session: IntakeSession) -> str:


 def _schedule_i_unemployment_debtor1(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "unemployment_compensation"))
+    return _income_amounts(session, "monthly_unemployment")


 def _schedule_i_social_security_debtor1(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "social_security"))
+    return _income_amounts(session, "monthly_social_security")


 def _schedule_i_pension_debtor1(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "pension_retirement"))
+    return _income_amounts(session, "monthly_pension")


 def _schedule_i_child_support_debtor1(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "child_support_alimony"))
+    return _income_amounts(session, "monthly_child_support", "monthly_alimony")


 def _schedule_i_interest_debtor1(session: IntakeSession) -> str:
@@ -376,11 +388,11 @@ def _schedule_i_interest_debtor1(session: IntakeSession) -> str:


 def _schedule_i_rental_debtor1(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "real_property_income"))
+    return _income_amounts(session, "monthly_rental_income")


 def _schedule_i_other_income_debtor1(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "other_income"))
+    return _income_amounts(session, "monthly_other_income")


 def _schedule_i_total_deductions_debtor1(session: IntakeSession) -> str:
diff --git a/backend/apps/forms/views.py b/backend/apps/forms/views.py
index f7dc300..6dfb31a 100644
--- a/backend/apps/forms/views.py
+++ b/backend/apps/forms/views.py
@@ -19,6 +19,7 @@ from rest_framework.permissions import IsAuthenticated
 from rest_framework.response import Response
 from rest_framework.views import APIView

+from apps.eligibility.cmi import IncomeNotSplit
 from apps.intake.models import IntakeSession

 from .models import GeneratedForm
@@ -50,9 +51,10 @@ class IntakeNotFinished(Exception):


 # Failures a filer can act on: 422 in plain words (spec §5.7). Anything else is a 500.
-# PreconditionMissing carries its own plain reason (registry.py). Every other class gets
-# a fixed sentence, because their messages name form keys, repeat groups and PDF
-# widgets. None names the form: the dashboard shows its label beside the error.
+# PreconditionMissing and IncomeNotSplit carry their own plain reasons (registry.py,
+# eligibility/cmi.py). Every other class gets a fixed sentence, because their messages
+# name form keys, repeat groups and PDF widgets. None names the form: the dashboard shows
+# its label beside the error.
 _FAILURE_SENTENCES = {
     IntakeNotFinished: "Finish your intake before preparing your forms.",
     NotInPacket: "This form isn't part of your packet, based on the answers you've given.",
@@ -71,7 +73,7 @@ _FAILURE_SENTENCES = {

 def _failure(form_type: str, exc: Exception) -> tuple[dict, int]:
     """The error body and status for a form that could not be filled."""
-    if isinstance(exc, PreconditionMissing):
+    if isinstance(exc, PreconditionMissing | IncomeNotSplit):
         error = str(exc)
     else:
         error = _FAILURE_SENTENCES.get(type(exc))
PATCH
```

The 13 rules §5.5 lists read their own columns through `_income_amounts` and print blank when the filer gave none of them; their bindings move in 2b. The five rules §5.5 leaves alone, and `_get_income_field`, are unchanged, and no rule is created. `_failure` returns the `IncomeNotSplit` sentence as a 422, as it does `PreconditionMissing`'s.

- [ ] **Step 7: Give each persona the ten amounts**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/management/commands/seed_demo_data.py b/backend/apps/intake/management/commands/seed_demo_data.py
index d3927a5..e5682bf 100644
--- a/backend/apps/intake/management/commands/seed_demo_data.py
+++ b/backend/apps/intake/management/commands/seed_demo_data.py
@@ -34,6 +34,13 @@ User = get_user_model()
 DEMO_PASSWORD = "DigniFi-Demo-2026!"


+def _wages_only(wages: Decimal) -> dict:
+    """The Income step's ten amounts for a persona whose only income is wages: the rest $0."""
+    amounts = dict.fromkeys(IncomeInfo.SOURCE_FIELDS, Decimal("0.00"))
+    amounts["monthly_gross_wages"] = wages
+    return amounts
+
+
 # ── Persona data functions ──────────────────────────────────────────


@@ -62,7 +69,7 @@ def _maria_torres() -> dict:
         "income": {
             "marital_status": "single",
             "number_of_dependents": 2,
-            "monthly_income": [3200, 3200, 3200, 3200, 3200, 3200],
+            **_wages_only(Decimal("3200.00")),
         },
         "expenses": {
             "rent_or_mortgage": Decimal("1100.00"),
@@ -177,7 +184,7 @@ def _james_washington() -> dict:
         "income": {
             "marital_status": "single",
             "number_of_dependents": 0,
-            "monthly_income": [5833, 5833, 5833, 5833, 5833, 5833],
+            **_wages_only(Decimal("5833.00")),
         },
         "expenses": {
             "rent_or_mortgage": Decimal("1650.00"),
@@ -259,7 +266,7 @@ def _priya_sharma() -> dict:
             "number_of_dependents": 2,
             # $12,000/month = $144,000/year — above the $134,366 HH4 median,
             # so the annualized § 707(b) comparison fails as intended.
-            "monthly_income": [12000, 12000, 12000, 12000, 12000, 12000],
+            **_wages_only(Decimal("12000.00")),
         },
         "expenses": {
             "rent_or_mortgage": Decimal("2800.00"),
@@ -331,7 +338,7 @@ def _deshawn_mitchell() -> dict:
         "income": {
             "marital_status": "married_joint",
             "number_of_dependents": 0,
-            "monthly_income": [3500, 3500, 3500, 3500, 3500, 3500],
+            **_wages_only(Decimal("3500.00")),
         },
         "expenses": {
             "rent_or_mortgage": Decimal("1200.00"),
@@ -433,7 +440,7 @@ def _sarah_chen() -> dict:
         "income": {
             "marital_status": "single",
             "number_of_dependents": 0,
-            "monthly_income": [2000, 2000, 2000, 2000, 2000, 2000],
+            **_wages_only(Decimal("2000.00")),
         },
         "expenses": {
             "rent_or_mortgage": Decimal("850.00"),
@@ -582,7 +589,7 @@ class Command(BaseCommand):
         if result["qualifies_for_fee_waiver"]:
             income_data = data["income"]
             household_size = data["debtor"]["household_size"]
-            monthly_income = Decimal(str(income_data["monthly_income"][0]))
+            monthly_income = income_data["monthly_gross_wages"]
             total_expenses = sum(data["expenses"].values())

             FeeWaiverApplication.objects.create(
PATCH
```

Each persona's wages are today's figure and the other nine amounts are $0, so the read-back sends all ten. The seeded fee-waiver application reads its monthly income from the wages, which is the same value as before.

- [ ] **Step 8: Run the backend tests again**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/eligibility/tests/test_cmi.py apps/intake/tests/test_income_resume.py apps/intake/tests/test_data_migrations.py apps/forms/tests/test_derivations.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `79 passed`.

- [ ] **Step 9: Write the frontend tests**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx b/frontend/src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx
index 8464402..9b1322c 100644
--- a/frontend/src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx
+++ b/frontend/src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx
@@ -1,17 +1,32 @@
 import { render, screen, fireEvent } from '@testing-library/react';
 import { vi } from 'vitest';
 import { IncomeInfoStep } from '../IncomeInfoStep';
+import { INCOME_FIELDS } from '../../../../types/api';
 import type { IncomeInfo } from '../../../../types/api';

-// The server stores only six months of income and reports their average. It never stores
-// the per-source boxes, so a returning filer's data arrives with none of them (DIG-41).
-const savedIncome: Partial<IncomeInfo> = {
+// The server stores the ten amounts by source and drops any other name without an error, so
+// each box must carry the name the court forms read (forms step 2 §5.5).
+const BOXES: [RegExp, (typeof INCOME_FIELDS)[number]][] = [
+  [/monthly wages/i, 'monthly_gross_wages'],
+  [/monthly overtime/i, 'monthly_overtime'],
+  [/monthly tips/i, 'monthly_tips'],
+  [/rental income after the property's costs/i, 'monthly_rental_income'],
+  [/pension/i, 'monthly_pension'],
+  [/social security/i, 'monthly_social_security'],
+  [/unemployment/i, 'monthly_unemployment'],
+  [/child support received/i, 'monthly_child_support'],
+  [/alimony received/i, 'monthly_alimony'],
+  [/other monthly income/i, 'monthly_other_income'],
+];
+
+// A filer who saved income before it was stored by source: the API returns the old six months
+// (read-only) and none of the ten amounts.
+const legacyIncome: Partial<IncomeInfo> = {
   monthly_income: [3100, 3300, 3200, 3200, 3150, 3250],
-  total_monthly_income: 3200,
+  total_monthly_income: null,
 };

-const SAVED_TOTAL_NOTE =
-  'Your saved total is $3,200.00 a month. We keep only the total, not the amount from each source, so the boxes below start empty. If you enter amounts below, they will replace the saved total.';
+const SPLIT_IT = 'You entered $3,200.00 a month in total. Please split it by source.';

 function renderStep(initialData: Partial<IncomeInfo>) {
   const onDataChange = vi.fn();
@@ -28,53 +43,81 @@ function renderStep(initialData: Partial<IncomeInfo>) {
 }

 describe('IncomeInfoStep', () => {
-  it('shows a returning filer their saved income instead of $0', () => {
-    renderStep(savedIncome);
+  it.each(BOXES)('keeps the amount typed in the %s box under %s', (label, name) => {
+    const { lastEmitted } = renderStep({});

-    expect(screen.getByText(SAVED_TOTAL_NOTE)).toBeInTheDocument();
-    expect(screen.getByText('$3,200.00')).toBeInTheDocument();
+    fireEvent.change(screen.getByLabelText(label), { target: { value: '850' } });
+
+    expect(lastEmitted()[name]).toBe(850);
+    for (const other of INCOME_FIELDS) {
+      if (other !== name) expect(lastEmitted()[other]).toBeUndefined();
+    }
   });

-  it('keeps each saved month exactly as stored when the filer changes nothing', () => {
-    const { lastEmitted } = renderStep(savedIncome);
+  it('leaves every box empty for a new filer, so nothing is saved as $0 unless typed', () => {
+    const { lastEmitted } = renderStep({});
+
+    for (const field of INCOME_FIELDS) expect(lastEmitted()[field]).toBeUndefined();
+    for (const [label] of BOXES) expect(screen.getByLabelText(label)).toHaveValue(null);
+  });

-    expect(lastEmitted().monthly_income).toEqual([3100, 3300, 3200, 3200, 3150, 3250]);
+  // Ten blank boxes mean no income was given at all, and the means test refuses that. A filer with
+  // no income needs to know a typed $0 is how to say so (owner ruling O-1).
+  it('tells a filer with no income to enter $0 in a box, since a blank box only means none of that kind', () => {
+    renderStep({});
+
+    const help = screen.getByText(/enter your average monthly income before taxes\./i);
+    expect(help).toHaveTextContent('Enter your average monthly income before taxes.');
+    expect(help).toHaveTextContent(
+      "Leave a box blank if you don't get that kind of income. If you have no income at all, enter $0 in any box."
+    );
+    expect(help).not.toHaveTextContent(/leave it blank or enter \$0/i);
   });

-  it('replaces the saved total with the amounts the filer enters', () => {
-    const { lastEmitted } = renderStep(savedIncome);
+  it('keeps a $0 the filer typed', () => {
+    const { lastEmitted } = renderStep({});

-    fireEvent.change(screen.getByLabelText(/monthly wages/i), { target: { value: '2000' } });
-    fireEvent.change(screen.getByLabelText(/social security/i), { target: { value: '500' } });
+    fireEvent.change(screen.getByLabelText(/social security/i), { target: { value: '0' } });

-    expect(lastEmitted().monthly_income).toEqual([2500, 2500, 2500, 2500, 2500, 2500]);
-    expect(screen.getByText('$2,500.00')).toBeInTheDocument();
-    expect(screen.queryByText(SAVED_TOTAL_NOTE)).not.toBeInTheDocument();
+    expect(lastEmitted().monthly_social_security).toBe(0);
   });

-  it('lets a filer record $0 income in place of a saved total', () => {
-    const { lastEmitted } = renderStep(savedIncome);
+  it("shows a returning filer's saved amounts, and empty boxes stay empty", () => {
+    renderStep({ monthly_gross_wages: 3200, monthly_tips: 0, total_monthly_income: 3200 });

-    fireEvent.change(screen.getByLabelText(/monthly wages/i), { target: { value: '0' } });
+    expect(screen.getByLabelText(/monthly wages/i)).toHaveValue(3200);
+    expect(screen.getByLabelText(/monthly tips/i)).toHaveValue(0);
+    expect(screen.getByLabelText(/monthly overtime/i)).toHaveValue(null);
+    expect(screen.getByText('$3,200.00')).toBeInTheDocument();
+  });
+
+  it('asks a filer who saved only a total to split it by source', () => {
+    renderStep(legacyIncome);

-    expect(lastEmitted().monthly_income).toEqual([0, 0, 0, 0, 0, 0]);
-    expect(screen.getByText('$0.00')).toBeInTheDocument();
+    expect(screen.getByText(SPLIT_IT)).toBeInTheDocument();
+    expect(screen.queryByText(/we keep only the total/i)).not.toBeInTheDocument();
+    // The old total isn't an amount from any source, so no box starts with it.
+    for (const [label] of BOXES) expect(screen.getByLabelText(label)).toHaveValue(null);
   });

-  it('records six months of $0 for a new filer who leaves every box blank', () => {
-    const { lastEmitted } = renderStep({});
+  it('stops asking once the filer enters an amount by source', () => {
+    const { lastEmitted } = renderStep(legacyIncome);
+
+    fireEvent.change(screen.getByLabelText(/monthly wages/i), { target: { value: '3200' } });
+
+    expect(screen.queryByText(SPLIT_IT)).not.toBeInTheDocument();
+    expect(lastEmitted().monthly_gross_wages).toBe(3200);
+  });
+
+  it('never asks a filer whose income is already stored by source', () => {
+    renderStep({ ...legacyIncome, monthly_gross_wages: 3200 });

-    expect(lastEmitted().monthly_income).toEqual([0, 0, 0, 0, 0, 0]);
-    expect(screen.queryByText(/your saved total is/i)).not.toBeInTheDocument();
+    expect(screen.queryByText(/please split it by source/i)).not.toBeInTheDocument();
   });

-  it('never sends back a stored income shorter than six months, which the server would reject', () => {
-    const { lastEmitted } = renderStep({
-      monthly_income: [3100, 3300],
-      total_monthly_income: 3200,
-    });
+  it('never asks a filer whose saved total was $0, which nothing needs to split', () => {
+    renderStep({ monthly_income: [0, 0, 0, 0, 0, 0], total_monthly_income: null });

-    expect(lastEmitted().monthly_income).toEqual([0, 0, 0, 0, 0, 0]);
-    expect(screen.queryByText(/your saved total is/i)).not.toBeInTheDocument();
+    expect(screen.queryByText(/please split it by source/i)).not.toBeInTheDocument();
   });
 });
diff --git a/frontend/src/pages/__tests__/IntakeWizard.test.tsx b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
index 8f8c654..cfa8968 100644
--- a/frontend/src/pages/__tests__/IntakeWizard.test.tsx
+++ b/frontend/src/pages/__tests__/IntakeWizard.test.tsx
@@ -27,7 +27,7 @@ const sessionAtStep8 = {
   updated_at: '2026-01-20T10:00:00Z',
   completed_at: null,
   debtor_info: { first_name: 'Jane', last_name: 'Doe' },
-  income_info: { monthly_income: [1200, 1200, 1200, 1200, 1200, 1200] },
+  income_info: { monthly_gross_wages: '1200.00', total_monthly_income: 1200 },
   expense_info: { rent_or_mortgage: 1000 },
   assets: [],
   debts: [],
@@ -201,6 +201,8 @@ describe('IntakeWizard handleComplete routing', { timeout: 30_000 }, () => {
     expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
   });

+  // A filer who left every Income box blank is refused by the means test. Its 400 carries its own
+  // sentence, which says what to do, beside a generic message, which doesn't (ruling C-5).
   it('keeps the filer on Review with the reason when only the means test fails', async () => {
     renderWizard();
     const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
@@ -208,7 +210,7 @@ describe('IntakeWizard handleComplete routing', { timeout: 30_000 }, () => {
       http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
         HttpResponse.json(
           {
-            error: 'No median income data for this district',
+            error: 'Enter your income by source on the Income step.',
             message:
               'Unable to calculate means test. Please ensure all income information is provided.',
           },
@@ -219,9 +221,9 @@ describe('IntakeWizard handleComplete routing', { timeout: 30_000 }, () => {

     await userEvent.click(completeBtn);

-    expect(await screen.findByRole('alert')).toHaveTextContent(
-      'Unable to calculate means test. Please ensure all income information is provided.'
-    );
+    const alert = await screen.findByRole('alert');
+    expect(alert).toHaveTextContent('Enter your income by source on the Income step.');
+    expect(alert).not.toHaveTextContent(/unable to calculate means test/i);
     expect(
       screen.getByRole('heading', { name: /review & results/i, level: 2 })
     ).toBeInTheDocument();
@@ -259,7 +261,18 @@ const completedSession = {
   income_info: {
     marital_status: 'single',
     number_of_dependents: 1,
-    monthly_income: [3100, 3300, 3200, 3200, 3150, 3250],
+    // The API sends each amount as a decimal string, and an amount never given as null
+    monthly_gross_wages: '3100.50',
+    monthly_overtime: null,
+    monthly_tips: '0.00',
+    monthly_rental_income: null,
+    monthly_pension: null,
+    monthly_social_security: '99.50',
+    monthly_unemployment: null,
+    monthly_child_support: null,
+    monthly_alimony: null,
+    monthly_other_income: null,
+    monthly_income: null,
     total_monthly_income: 3200,
   },
   expense_info: {
@@ -781,21 +794,46 @@ describe('IntakeWizard amounts a returning filer already entered', { timeout: 15
 // ===========================================================================

 describe('IntakeWizard income save', { timeout: 15_000 }, () => {
-  it("saves a returning filer's months exactly as stored, and nothing else, when they continue without changes", async () => {
-    // What the API returns for a filer who saved income earlier through the wizard: the
-    // months, their average, and the blank household fields a wizard-created row holds.
-    const savedSession = {
-      ...sessionAtStep1,
-      current_step: 2,
-      income_info: {
-        marital_status: '',
-        number_of_dependents: 0,
-        monthly_income: [3100, 3300, 3200, 3200, 3150, 3250],
-        total_monthly_income: 3200,
-        created_at: '2026-10-01T10:00:00Z',
-      },
-    };
-    const patchBodies: unknown[] = [];
+  // What the API returns for a filer who saved income by source through the wizard: decimal
+  // strings, null for a box left empty, and the blank household fields a wizard-created row
+  // holds. Echoing those back is a 400, and the old total is read-only.
+  const savedSession = {
+    ...sessionAtStep1,
+    current_step: 2,
+    income_info: {
+      marital_status: '',
+      number_of_dependents: 0,
+      monthly_gross_wages: '3100.50',
+      monthly_overtime: null,
+      monthly_tips: '0.00',
+      monthly_rental_income: null,
+      monthly_pension: null,
+      monthly_social_security: '99.50',
+      monthly_unemployment: null,
+      monthly_child_support: null,
+      monthly_alimony: null,
+      monthly_other_income: null,
+      monthly_income: null,
+      total_monthly_income: 3200,
+      created_at: '2026-10-01T10:00:00Z',
+    },
+  };
+  const savedAmounts = {
+    monthly_gross_wages: 3100.5,
+    monthly_overtime: null,
+    monthly_tips: 0,
+    monthly_rental_income: null,
+    monthly_pension: null,
+    monthly_social_security: 99.5,
+    monthly_unemployment: null,
+    monthly_child_support: null,
+    monthly_alimony: null,
+    monthly_other_income: null,
+  };
+  let patchBodies: unknown[];
+
+  beforeEach(() => {
+    patchBodies = [];
     server.use(
       http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
         HttpResponse.json(savedSession)
@@ -817,19 +855,32 @@ describe('IntakeWizard income save', { timeout: 15_000 }, () => {
         () => new HttpResponse(null, { status: 201 })
       )
     );
+  });

+  it("sends a returning filer's ten amounts as numbers, a box left empty as empty, and nothing else", async () => {
     renderWizard();
     await screen.findByRole('heading', { name: /income/i, level: 2 });
+    expect(screen.getByLabelText(/monthly wages/i)).toHaveValue(3100.5);
     await userEvent.click(screen.getByRole('button', { name: /continue/i }));
     await screen.findByRole('heading', { name: /expenses/i, level: 2 });

     expect(patchBodies.length).toBeGreaterThan(0);
     for (const body of patchBodies) {
-      expect(body).toEqual({
-        income_info: { monthly_income: [3100, 3300, 3200, 3200, 3150, 3250] },
-      });
+      expect(body).toEqual({ income_info: savedAmounts });
     }
   });
+
+  it('empties a box on the server too when the filer clears it', async () => {
+    renderWizard();
+    await screen.findByRole('heading', { name: /income/i, level: 2 });
+    await userEvent.clear(screen.getByLabelText(/social security/i));
+    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
+    await screen.findByRole('heading', { name: /expenses/i, level: 2 });
+
+    expect(patchBodies.at(-1)).toEqual({
+      income_info: { ...savedAmounts, monthly_social_security: null },
+    });
+  });
 });

 // ===========================================================================
diff --git a/frontend/src/test/fixtures/session.ts b/frontend/src/test/fixtures/session.ts
index 67e2261..444c4fb 100644
--- a/frontend/src/test/fixtures/session.ts
+++ b/frontend/src/test/fixtures/session.ts
@@ -54,7 +54,7 @@ export const createMockIncomeInfo = (overrides?: Partial<IncomeInfo>): IncomeInf
   id: 1,
   session: 1,
   data_source: 'manual',
-  monthly_income: [3500, 3500, 3500, 3500, 3500, 3500],
+  monthly_gross_wages: 3500,
   total_monthly_income: 3500,
   ...overrides,
 });
PATCH
```

`IncomeInfoStep.test.tsx` pins each box's label with its name, leaves every box empty for a new filer, keeps a typed $0, shows a returning filer's amounts, and asks a filer with only a saved total to split it, but never one whose income is stored by source or whose saved total was $0. It also pins the owner's help text. `IntakeWizard.test.tsx` checks that the Income step sends the ten amounts as numbers, a box left empty as null, and nothing else, and that clearing a box empties it on the server. It also rewrites the DIG-150 test "keeps the filer on Review with the reason when only the means test fails" in place: the mocked 400 is now the real two-key body, `error` "Enter your income by source on the Income step." beside the generic `message`, and Review must show the `error` sentence. That test is what drives the `client.ts` and `IntakeContext.tsx` changes in Step 12. The session fixture moves to the by-source shape.

- [ ] **Step 10: Run them and watch them fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx src/pages/__tests__/IntakeWizard.test.tsx 2>&1 | tail -5
```

Expected: FAIL — `17 failed` and `35 passed`. The step has no INCOME_FIELDS to import, no new help text, no legacy message and the old rental label. The wizard still sends the months alone, so the two income-save tests get one key where they want ten, and the stepping-back test sees a save, because the old step re-emits months for a session stored by source. Review still shows the generic means-test message.

- [ ] **Step 11: Load and save the ten amounts on the Income step**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/wizard/steps/IncomeInfoStep.tsx b/frontend/src/components/wizard/steps/IncomeInfoStep.tsx
index d110aaf..41f0c81 100644
--- a/frontend/src/components/wizard/steps/IncomeInfoStep.tsx
+++ b/frontend/src/components/wizard/steps/IncomeInfoStep.tsx
@@ -10,26 +10,10 @@

 import { useState, useEffect, useMemo } from 'react';
 import { FormField } from '../../common';
-import { parseAmount } from '../../../utils/parseAmount';
+import { decimalToNumber, parseAmount } from '../../../utils/parseAmount';
+import { INCOME_FIELDS } from '../../../types/api';
 import type { IncomeInfo } from '../../../types/api';

-/**
- * The ten per-source boxes. The server stores only the 6-month `monthly_income` array,
- * never these, so a session read back from the server carries none of them.
- */
-const SOURCE_FIELDS = [
-  'monthly_gross_wages',
-  'monthly_overtime',
-  'monthly_tips',
-  'monthly_rental_income',
-  'monthly_pension',
-  'monthly_social_security',
-  'monthly_unemployment',
-  'monthly_child_support',
-  'monthly_alimony',
-  'monthly_other_income',
-] as const;
-
 interface IncomeInfoStepProps {
   initialData?: Partial<IncomeInfo>;
   onDataChange: (data: Partial<IncomeInfo>) => void;
@@ -45,24 +29,24 @@ export function IncomeInfoStep({
   // blank, while a deliberately entered 0 is preserved by parseAmount + `?? ''`.
   const [formData, setFormData] = useState<Partial<IncomeInfo>>(initialData || {});

-  // Typing in a box writes its key, so the step switches to source amounts once any key
-  // is present, even one cleared back to blank. Until then it keeps the saved months.
-  const usesSourceAmounts = SOURCE_FIELDS.some((field) => field in formData);
-  const savedMonthlyIncome =
-    !usesSourceAmounts && formData.monthly_income?.length === 6
-      ? formData.monthly_income
-      : undefined;
+  // Calculate total monthly income
+  const totalMonthlyIncome = INCOME_FIELDS.reduce((sum, field) => sum + (formData[field] || 0), 0);

-  // Calculate total monthly income: the saved total until the filer enters source amounts
-  const totalMonthlyIncome = savedMonthlyIncome
-    ? (formData.total_monthly_income ?? 0)
-    : SOURCE_FIELDS.reduce((sum, field) => sum + (formData[field] || 0), 0);
+  // A filer who saved income before it was stored by source has only the old six-month total,
+  // read-only. It counts toward nothing, so the step asks them to split it until they enter an
+  // amount in any box (forms step 2 §5.5).
+  const savedMonths = Array.isArray(formData.monthly_income) ? formData.monthly_income : [];
+  const savedTotal = savedMonths.length
+    ? savedMonths.reduce((sum, month) => sum + (decimalToNumber(month) ?? 0), 0) /
+      savedMonths.length
+    : 0;
+  const asksToSplit = savedTotal > 0 && INCOME_FIELDS.every((field) => formData[field] == null);

   const errors = useMemo<Record<string, string>>(() => {
     const newErrors: Record<string, string> = {};

-    // No "at least one source" gate: $0 total income is a valid answer for a
-    // bankruptcy filer (and the help text invites leaving fields blank or 0).
+    // No "at least one source" gate: a blank box means none of that kind, and a filer
+    // with no income types $0 in a box (O-1). The means test refuses all ten blank.

     // Validate non-negative values
     Object.keys(formData).forEach((key) => {
@@ -79,10 +63,6 @@ export function IncomeInfoStep({
   useEffect(() => {
     const dataWithTotal = {
       ...formData,
-      // Saved months go back exactly as stored. Source amounts replace them with six copies
-      // of their sum (MVP: the same income each month), and a new filer who enters nothing
-      // records six months of $0.
-      monthly_income: savedMonthlyIncome ?? Array(6).fill(totalMonthlyIncome),
       total_monthly_income: totalMonthlyIncome,
     };
     onDataChange(dataWithTotal);
@@ -111,23 +91,22 @@ export function IncomeInfoStep({
           <h3 className="info-title">Why we ask about income</h3>
           <p className="info-message">
             Income information helps determine which bankruptcy chapter you may qualify for. Enter
-            your average monthly income before taxes. If you don't have income from a source, you
-            can leave it blank or enter $0.
+            your average monthly income before taxes. Leave a box blank if you don't get that kind
+            of income. If you have no income at all, enter $0 in any box.
           </p>
         </div>
       </div>

-      {/* Saved total: only the total is stored, so the boxes start empty */}
-      {savedMonthlyIncome && (
+      {/* A total saved before income was stored by source */}
+      {asksToSplit && (
         <div className="info-box">
           <p className="info-message">
-            Your saved total is $
-            {totalMonthlyIncome.toLocaleString('en-US', {
+            You entered $
+            {savedTotal.toLocaleString('en-US', {
               minimumFractionDigits: 2,
               maximumFractionDigits: 2,
             })}{' '}
-            a month. We keep only the total, not the amount from each source, so the boxes below
-            start empty. If you enter amounts below, they will replace the saved total.
+            a month in total. Please split it by source.
           </p>
         </div>
       )}
@@ -244,7 +223,7 @@ export function IncomeInfoStep({
           />

           <FormField
-            label="Rental Income"
+            label="Rental income after the property's costs"
             name="monthly_rental_income"
             type="number"
             min="0"
diff --git a/frontend/src/components/wizard/steps/ReviewStep.tsx b/frontend/src/components/wizard/steps/ReviewStep.tsx
index 8d4a9fd..bb10ef2 100644
--- a/frontend/src/components/wizard/steps/ReviewStep.tsx
+++ b/frontend/src/components/wizard/steps/ReviewStep.tsx
@@ -44,7 +44,7 @@ export function ReviewStep({
     onValidationChange(true);
   }, [onValidationChange]);

-  const formatCurrency = (amount?: number) => {
+  const formatCurrency = (amount?: number | null) => {
     return new Intl.NumberFormat('en-US', {
       style: 'currency',
       currency: 'USD',
diff --git a/frontend/src/pages/IntakeWizard.tsx b/frontend/src/pages/IntakeWizard.tsx
index 27c3904..1015700 100644
--- a/frontend/src/pages/IntakeWizard.tsx
+++ b/frontend/src/pages/IntakeWizard.tsx
@@ -35,7 +35,7 @@ import type {
   ExecutoryContract,
   Codebtor,
 } from '../types/api';
-import { EXPENSE_FIELDS } from '../types/api';
+import { EXPENSE_FIELDS, INCOME_FIELDS } from '../types/api';

 // ============================================================================
 // Wizard Configuration
@@ -140,7 +140,7 @@ export function IntakeWizard() {
         if (cancelled) return;
         setCurrentStepNumber(fresh.current_step);
         if (fresh.debtor_info) setDebtorData(fresh.debtor_info);
-        if (fresh.income_info) setIncomeData(fresh.income_info);
+        if (fresh.income_info) setIncomeData(hydrateAmounts(fresh.income_info, INCOME_FIELDS));
         if (fresh.expense_info) setExpenseData(hydrateAmounts(fresh.expense_info, EXPENSE_FIELDS));
         if (fresh.assets)
           setAssetsData(fresh.assets.map((asset) => hydrateAmounts(asset, ASSET_AMOUNT_FIELDS)));
@@ -182,13 +182,15 @@ export function IntakeWizard() {
       case 'debtor_info':
         return { debtor_info: debtorData } as Partial<IntakeSession>;

-      case 'income_info':
-        // Send the months alone: IncomeInfoStep re-emits them as stored unless the filer
-        // entered source amounts. Echoing other fields read from the server (a blank
-        // marital_status) is a 400 that would strand the filer on Income.
-        return {
-          income_info: { monthly_income: incomeData.monthly_income },
-        } as Partial<IntakeSession>;
+      case 'income_info': {
+        // The ten amounts alone. A blank box is sent as null, so it stays empty on the server
+        // and a box the filer cleared is emptied there too, never saved as $0. Echoing other
+        // fields read from the server (a blank marital_status) is a 400 that would strand the
+        // filer on Income, and the old six-month total is read-only.
+        const income: Partial<IncomeInfo> = {};
+        for (const field of INCOME_FIELDS) income[field] = incomeData[field] ?? null;
+        return { income_info: income } as Partial<IntakeSession>;
+      }

       case 'expense_info': {
         // The 13 amounts alone. The total is read-only on the server: the step adds it up in
diff --git a/frontend/src/types/api.ts b/frontend/src/types/api.ts
index 0fbe8e7..3e1bf7f 100644
--- a/frontend/src/types/api.ts
+++ b/frontend/src/types/api.ts
@@ -78,25 +78,44 @@ export interface IncomeInfo {
   session: number;
   data_source: 'manual' | 'bank_import' | 'tax_return';

-  // Backend expects this
-  monthly_income?: number[];
-
-  // Frontend form fields (not in backend model, but useful for state)
-  monthly_gross_wages?: number;
-  monthly_overtime?: number;
-  monthly_tips?: number;
-  monthly_rental_income?: number;
-  monthly_pension?: number;
-  monthly_social_security?: number;
-  monthly_unemployment?: number;
-  monthly_child_support?: number;
-  monthly_alimony?: number;
-  monthly_other_income?: number;
-
-  // Calculated field
-  total_monthly_income: number;
+  // The six-month total saved before income was stored by source. Read-only: the Income step
+  // shows it while asking the filer to split it.
+  monthly_income?: number[] | null;
+
+  // The ten monthly amounts by source (INCOME_FIELDS). Empty (null) when the filer gave none.
+  monthly_gross_wages?: number | null;
+  monthly_overtime?: number | null;
+  monthly_tips?: number | null;
+  monthly_rental_income?: number | null;
+  monthly_pension?: number | null;
+  monthly_social_security?: number | null;
+  monthly_unemployment?: number | null;
+  monthly_child_support?: number | null;
+  monthly_alimony?: number | null;
+  monthly_other_income?: number | null;
+
+  // Calculated field: the ten added up, null when the filer gave none of them
+  total_monthly_income: number | null;
 }

+/**
+ * The ten monthly income amounts, under the names the backend stores and the court forms read.
+ * DRF drops any other name without an error, so the step saves only these. The API sends each
+ * as a decimal string or null.
+ */
+export const INCOME_FIELDS = [
+  'monthly_gross_wages',
+  'monthly_overtime',
+  'monthly_tips',
+  'monthly_rental_income',
+  'monthly_pension',
+  'monthly_social_security',
+  'monthly_unemployment',
+  'monthly_child_support',
+  'monthly_alimony',
+  'monthly_other_income',
+] as const;
+
 export interface ExpenseInfo {
   id: number;
   session: number;
PATCH
```

The wizard loads the ten amounts through `hydrateAmounts(…, INCOME_FIELDS)` and saves them alone, a blank box as null so it stays empty. The step drops its saved-months logic and the "We keep only the total" note, asks a filer with only a saved total to split it, renames the rental box, and carries the owner's help text. `ReviewStep.tsx`'s `formatCurrency` accepts null, a type change only.

- [ ] **Step 12: Show the means test's own refusal on Review**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/api/client.ts b/frontend/src/api/client.ts
index c24821e..ac20aa6 100644
--- a/frontend/src/api/client.ts
+++ b/frontend/src/api/client.ts
@@ -84,12 +84,20 @@ export function clearTokens(): void {
 export class APIClientError extends Error {
   statusCode: number;
   details?: Record<string, unknown>;
-
-  constructor(message: string, statusCode: number, details?: Record<string, unknown>) {
+  /** The response's own `error` sentence, kept even when its `message` is the one shown. */
+  serverError?: string;
+
+  constructor(
+    message: string,
+    statusCode: number,
+    details?: Record<string, unknown>,
+    serverError?: string
+  ) {
     super(message);
     this.name = 'APIClientError';
     this.statusCode = statusCode;
     this.details = details;
+    this.serverError = serverError;
   }
 }

@@ -108,7 +116,8 @@ async function handleAPIError(response: Response): Promise<never> {
   throw new APIClientError(
     errorData.message || errorData.error || 'Request failed',
     response.status,
-    errorData.details
+    errorData.details,
+    errorData.error
   );
 }

diff --git a/frontend/src/context/IntakeContext.tsx b/frontend/src/context/IntakeContext.tsx
index 7e8833b..601dc95 100644
--- a/frontend/src/context/IntakeContext.tsx
+++ b/frontend/src/context/IntakeContext.tsx
@@ -209,9 +209,11 @@ export function IntakeProvider({ children }: IntakeProviderProps) {
       setMeansTestResult(response.means_test_result);
       return response.means_test_result;
     } catch (err) {
+      // A 400 refusal's own sentence says what to fix (income not split by source); its
+      // `message` is generic.
       const errorMessage =
         err instanceof APIClientError
-          ? err.message
+          ? (err.statusCode === 400 && err.serverError) || err.message
           : 'Unable to calculate means test. Please ensure all income information is provided.';
       setError(errorMessage);
       throw err;
PATCH
```

`APIClientError` keeps the body's `error` as `serverError`, and `IntakeContext.calculateMeansTest` shows it on a 400. `apiFetch`'s message is unchanged for every other caller.

- [ ] **Step 13: Run the frontend tests again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx src/pages/__tests__/IntakeWizard.test.tsx 2>&1 | tail -5
```

Expected: `52 passed`.

- [ ] **Step 14: Run every gate**

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

Expected: `1738 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  300 passed (300)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 15: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`. The journeys type only wages, so a journey-built session stores the other nine amounts empty, and 0014 runs on the step's database before the backend starts.

- [ ] **Step 16: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/eligibility/cmi.py \
  backend/apps/eligibility/tests/test_cmi.py \
  backend/apps/intake/migrations/0013_incomeinfo_income_by_source.py \
  backend/apps/intake/migrations/0014_split_income_saved_as_zero.py \
  backend/apps/audit/tests/test_upl_compliance.py \
  backend/apps/eligibility/models.py \
  backend/apps/eligibility/services/expense_deduction_calculator.py \
  backend/apps/eligibility/services/means_test_calculator.py \
  backend/apps/eligibility/tests/test_means_test_calculator.py \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/test_api_readback.py \
  backend/apps/forms/tests/test_derivations.py \
  backend/apps/forms/tests/test_form_106sum_schema.py \
  backend/apps/forms/tests/test_form_122a1_schema.py \
  backend/apps/forms/tests/test_form_views.py \
  backend/apps/forms/tests/test_schedule_i_schema.py \
  backend/apps/forms/views.py \
  backend/apps/intake/management/commands/seed_demo_data.py \
  backend/apps/intake/models.py \
  backend/apps/intake/serializers.py \
  backend/apps/intake/tests/test_completion.py \
  backend/apps/intake/tests/test_data_migrations.py \
  backend/apps/intake/tests/test_e2e_intake.py \
  backend/apps/intake/tests/test_income_resume.py \
  frontend/src/api/client.ts \
  frontend/src/components/wizard/steps/IncomeInfoStep.tsx \
  frontend/src/components/wizard/steps/ReviewStep.tsx \
  frontend/src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx \
  frontend/src/context/IntakeContext.tsx \
  frontend/src/pages/IntakeWizard.tsx \
  frontend/src/pages/__tests__/IntakeWizard.test.tsx \
  frontend/src/test/fixtures/session.ts \
  frontend/src/types/api.ts
git commit -F - <<'MSG'
feat(intake,forms,frontend): store income by source, and leave Social Security out of CMI

The Income step added its ten boxes into one six-month total, and only the
total was stored. The court forms ask for each kind of income on its own
line, and the means test must leave Social Security out (11 U.S.C.
§ 101(10A)(B), DIG-49), so neither could be right: every income box printed
0.00, and CMI counted Social Security.

IncomeInfo now stores the ten amounts under the step's names, empty when the
filer gave none. They have no default, because $0 would pass every earlier
filer's means test. The old six-month total is no longer written: it becomes
optional and read-only, and stays for one release. A data migration turns a
saved $0 total into ten $0 amounts and leaves any other total for the filer
to split. The old column is untouched, and undoing the migration changes
nothing.

One function in apps/eligibility works out CMI: the ten amounts without
Social Security, an empty one counting as zero once another was given. The
means test (and so the fee-waiver flag), the above-median calculator and the
forms' cmi rule all use it. When none of the ten was given it refuses with
"Enter your income by source on the Income step.": a 422 for a form, and a
400 from the means-test endpoint without the "Means test calculation failed:"
prefix. The API's total_monthly_income is the ten added up, or null.

The 13 income rules that spec section 5.5 switches read their own columns and
print blank when the filer gave none of them. Their bindings move in 2b, so
until then Schedule I line 3 prints wages and tips. Schedule I lines 10 and
12 and Schedule J line 23a print CMI until 2b creates schedule_i_income_total,
so for now they leave out Social Security, which the old total counted. The
five rules the spec leaves alone, and _get_income_field, are unchanged.

The Income step loads the ten amounts as numbers and saves them alone, a
blank box as null so it stays empty. A filer with only a saved total is asked
to split it, the "We keep only the total" note is gone, and the rental box
reads "Rental income after the property's costs". The seeds give each persona
the ten amounts, wages as before and the rest $0, so the read-back sends them.

The means test refuses ten blank boxes, so the Income step's help text now
tells a filer to leave a box blank for a kind of income they don't get, and
to enter $0 in any box when they have no income at all. When the means test
refuses on Review, Review shows the refusal's own sentence. The endpoint's
400 also carries a generic message ("Unable to calculate means test. Please
ensure all income information is provided."), and apiFetch shows message
before error, so that sentence never reached the filer. APIClientError now
also keeps the body's error as serverError, and only the means-test call
that Complete makes reads it, on a 400; apiFetch still prefers message for
every other caller. The endpoint returns 400 for any ValueError, so in a
district with no median income data Review now shows that raw text too,
"Means test calculation failed: No median income data found for district"
and the district's code.

Forms step 2a, commit 4 (step 2 spec §5.2, §5.5, §7.7, §7.8).
MSG
git status --short
```

### Task 10: Count income at the median as below it, and round CMI once

_Built and verified as commit `3566dcf` on `plan/forms-step2a`._

**Files:**

- Modify: `backend/apps/eligibility/cmi.py`
- Modify: `backend/apps/eligibility/models.py`
- Modify: `backend/apps/eligibility/services/means_test_calculator.py`
- Modify: `backend/apps/eligibility/tests/test_means_test_calculator.py`
- Modify: `backend/apps/forms/registry.py`
- Modify: `backend/apps/forms/tests/test_registry.py`
- Modify: `docs/superpowers/specs/2026-10-10-forms-foundation-design.md`

**Interfaces:**

- Consumes: `current_monthly_income(income_info)` and `IncomeNotSplit` in `apps/eligibility/cmi.py` (Task 9); `MeansTest.calculate()`; `MeansTestCalculator.calculate()` and its `_generate_upl_compliant_message`; `_above_median` and `packet(session)` in `apps/forms/registry.py`; `DERIVATIONS["cmi"]` and `DERIVATIONS["line12b_annualized_cmi"]`.
- Produces:
  - `is_above_median(cmi: Decimal, median_income: Decimal) -> bool` in `apps/eligibility/cmi.py`, which returns `cmi * 12 > median_income`. It takes monthly CMI and the annual median and does the ×12 itself. The module has no Django imports, so `forms/registry.py` and 2b's Q5 rule import it without a cycle.
  - `current_monthly_income` returns its sum quantized to the cent with `ROUND_HALF_EVEN`. The means test, `ExpenseDeductionCalculator._get_cmi`, the stored `MeansTest.calculated_cmi` and the `cmi` rule all get that figure.
  - `MeansTest.calculate()` sets `passes_means_test = not is_above_median(cmi, median_income_threshold)`. At or below the median it resets `total_allowable_expenses`, `disposable_income` and `priority_debts_monthly` to `Decimal("0")`, and `passes_above_median` and `above_median_calculated` to `False` (DIG-128).
  - `packet(session)` includes `form_122a2` only when `is_above_median(calculated_cmi, median_income_threshold)` holds for the stored `MeansTest`.
  - The result message branches first on `is_above_median`, then on the expense test. No sentence changes.
  - Tests: `test_income_exactly_at_median_is_below_median` (it replaces `test_at_median_income_fails`), `test_one_cent_over_median_is_above_median`, `test_fractional_cent_cmi_rounds_before_the_median_comparison`, `test_above_median_filer_who_passes_is_not_told_below_median`, `test_recalculating_below_the_median_clears_the_above_median_results`, and `test_122a2_applies_only_above_the_median` (it replaces `test_122a2_applies_at_or_above_the_median` and gains the exact-median case).

**Decisions already made in this task:**

- The step 1 spec's §5.6 amendment (122A-2 on `>`, pointing at the step 2 spec) lands here. Only the 122A-2 row of its table changes. The "Why not `above_median_calculated`" bullet below the table is left for Task 14, which marks it fixed.
- CMI is rounded once, inside `current_monthly_income`, and `is_above_median` doesn't round again. §5.6 asks for "one rounding", and the stored `calculated_cmi` that the packet compares must be the rounded figure: Postgres's `numeric(12,2)` rounds half away from zero, so the rounding has to happen before the save.
- `test_at_median_income_fails` is flipped and renamed to `test_income_exactly_at_median_is_below_median`, not kept under its old name. A test named "fails" that asserts a pass misleads, and the two would assert the same thing.
- A filer exactly at the median reads the existing below-median message ("your income is below the median …"). No "at or below" wording is written. Whether the sentence should say "at or below" is an open question for the owner.
- An above-median filer who passes the expense test now reads the existing above-median text ("may still be eligible"), which no filer could reach before. Its wording is unchanged, and it has no hits against the six `UPL_PROHIBITED_PHRASES`.
- The message's last branch ("additional calculations may be needed") stays, although `calculate()` always runs the above-median pathway above the median, so nothing reaches it. Only the first branch's condition had to change.
- The DIG-128 reset writes the five fields' model defaults (0, 0, 0, False, False), not NULL, because the columns are non-null. Below the median nothing a filer sees reads them: only `form_122a2.json` does, and that form applies only above the median.
- The reset test's name, `test_recalculating_below_the_median_clears_the_above_median_results`, is the implementer's; the task named none. It recalculates at $5,000, clearly below the median, so it tests the reset apart from the tie.
- `test_registry.py`'s `_means_test` helper sets `passes_means_test` with `<=`. It is fixture data that states the new rule, and `packet()` never reads that field.
- Root `CLAUDE.md` still states the 122A-2 rule as `≥` and calls `above_median_calculated` sticky after this task. Task 14 rewrites it.
- No migration, and `known_defects.json` doesn't change. Every stored amount is whole cents and no persona sits exactly at its median, so no oracle value moves.

- [ ] **Step 1: Write the median-tie, rounding and DIG-128 tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/eligibility/tests/test_means_test_calculator.py b/backend/apps/eligibility/tests/test_means_test_calculator.py
index bc17d53..671aab5 100644
--- a/backend/apps/eligibility/tests/test_means_test_calculator.py
+++ b/backend/apps/eligibility/tests/test_means_test_calculator.py
@@ -4,7 +4,7 @@ Comprehensive tests for MeansTestCalculator service.
 Tests cover:
 - Below-median income (passes means test)
 - Above-median income (fails means test)
-- At-median income (edge case: fails with < operator)
+- At-median income (edge case: counts as below the median, DIG-136), and CMI rounded to the cent
 - All household sizes (1-8+) with dependents + marital status
 - Fee waiver qualification (CMI < 60% of median)
 - Fee waiver non-qualification (CMI >= 60% of median)
@@ -26,8 +26,9 @@ from apps.districts.models import District, MedianIncome
 from apps.eligibility.cmi import IncomeNotSplit
 from apps.eligibility.models import MeansTest
 from apps.eligibility.services.means_test_calculator import MeansTestCalculator
-from apps.forms.registry import build_field_values
-from apps.intake.models import DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession
+from apps.forms.registry import build_field_values, packet
+from apps.forms.services.derivations import DERIVATIONS
+from apps.intake.models import DebtInfo, DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession

 User = get_user_model()

@@ -229,10 +230,10 @@ class TestAboveMedianIncomeFailsMeansTest:

 @pytest.mark.django_db
 class TestAtMedianIncomeEdgeCase:
-    """Test edge case: income exactly equal to median (uses < not <=)."""
+    """Income exactly at the median counts as below it (DIG-136), in the means test and the
+    packet alike: Form 122A-1 line 14a reads "less than or equal to"."""

-    def test_at_median_income_fails(self, session, median_income):
-        """Test that income exactly equal to median FAILS (< not <=)."""
+    def test_income_exactly_at_median_is_below_median(self, session, median_income):
         # Median for family size 1: $71,304/year
         # At median: $5,942/month annualizes to exactly $71,304/year
         IncomeInfo.objects.create(
@@ -245,10 +246,49 @@ class TestAtMedianIncomeEdgeCase:
         calculator = MeansTestCalculator(session)
         result = calculator.calculate()

-        # CRITICAL: At-median fails because code uses < (not <=)
-        assert result["passes_means_test"] is False
+        assert result["passes_means_test"] is True
+        assert result["above_median_calculated"] is False
+        assert "your income is below the median" in result["message"]
         assert result["cmi"] == Decimal("5942.00")
         assert result["median_income_threshold"] == Decimal("71304.00")
+        assert "form_122a2" not in packet(session)
+
+    def test_one_cent_over_median_is_above_median(self, session, median_income):
+        # $5,942.01/month annualizes to $71,304.12/year, over the $71,304 median
+        IncomeInfo.objects.create(
+            session=session,
+            marital_status="single",
+            number_of_dependents=0,
+            monthly_gross_wages=Decimal("5942.01"),
+        )
+
+        result = MeansTestCalculator(session).calculate()
+
+        assert result["passes_means_test"] is False
+        assert result["above_median_calculated"] is True
+        assert "your income is above the median" in result["message"]
+        assert "form_122a2" in packet(session)
+
+    def test_fractional_cent_cmi_rounds_before_the_median_comparison(self, session, median_income):
+        # Stored amounts are whole cents, so a fraction of a cent can only come from arithmetic
+        # on unsaved amounts, as here. Rounded half-even, $5,942.005 is $5,942.00, exactly the
+        # median a month. Unrounded it is $71,304.06 a year, and rounded half up $5,942.01:
+        # both above the median, while 122A-1 would print $5,942.00. The verdict, the packet
+        # and the printed CMI must agree on one figure.
+        IncomeInfo.objects.create(
+            session=session,
+            marital_status="single",
+            number_of_dependents=0,
+            monthly_gross_wages=Decimal("5942.005"),
+        )
+
+        result = MeansTestCalculator(session).calculate()
+
+        assert result["cmi"] == Decimal("5942.00")
+        assert result["passes_means_test"] is True
+        assert "form_122a2" not in packet(session)
+        assert DERIVATIONS["cmi"](session) == "5942.00"
+        assert DERIVATIONS["line12b_annualized_cmi"](session) == "71304.00"


 @pytest.mark.django_db
@@ -929,6 +969,71 @@ class TestAboveMedianCalculation:
         assert result["above_median_calculated"] is False


+def _expenses_and_priority_debt(session):
+    """Expenses at the IRS caps ($2,799 allowed for one person) and $3,500 a month of priority
+    debt: $7,000 of CMI leaves $701 of disposable income, under the $756.25 threshold."""
+    ExpenseInfo.objects.create(
+        session=session,
+        rent_or_mortgage=Decimal("1730.00"),
+        food_and_groceries=Decimal("713.00"),
+        medical_expenses=Decimal("73.00"),
+        vehicle_payment=Decimal("283.00"),
+    )
+    DebtInfo.objects.create(
+        session=session,
+        creditor_name="Illinois Department of Revenue",
+        debt_type="other",
+        amount_owed=Decimal("42000.00"),
+        monthly_payment=Decimal("3500.00"),
+        is_priority=True,
+    )
+
+
+@pytest.mark.django_db
+class TestAboveMedianResultAndMessage:
+    """DIG-128: the message says which side of the median the filer is on before it says
+    anything about the expense test, and a recalculation at or below the median leaves no
+    above-median result behind."""
+
+    def test_above_median_filer_who_passes_is_not_told_below_median(
+        self, session_with_above_median_income
+    ):
+        session = session_with_above_median_income
+        _expenses_and_priority_debt(session)
+
+        result = MeansTestCalculator(session).calculate()
+
+        assert result["passes_means_test"] is True
+        assert result["passes_above_median"] is True
+        assert "below the median" not in result["message"]
+        assert "your income is above the median" in result["message"]
+        assert "may still be eligible" in result["message"]
+
+    def test_recalculating_below_the_median_clears_the_above_median_results(
+        self, session_with_above_median_income
+    ):
+        session = session_with_above_median_income
+        _expenses_and_priority_debt(session)
+        first = MeansTestCalculator(session).calculate()
+        assert first["above_median_calculated"] is True
+        assert first["passes_above_median"] is True
+        assert first["total_allowable_expenses"] == Decimal("2799.00")
+        assert first["priority_debts_monthly"] == Decimal("3500.00")
+        assert first["disposable_income"] == Decimal("701.00")
+
+        session.income_info.monthly_gross_wages = Decimal("5000.00")
+        session.income_info.save()
+        MeansTestCalculator(session).calculate()
+
+        stored = MeansTest.objects.get(session=session)
+        assert stored.passes_means_test is True
+        assert stored.above_median_calculated is False
+        assert stored.passes_above_median is False
+        assert stored.total_allowable_expenses == Decimal("0")
+        assert stored.disposable_income == Decimal("0")
+        assert stored.priority_debts_monthly == Decimal("0")
+
+
 @pytest.mark.django_db
 class TestAboveMedianEndToEnd:
     def test_above_median_full_flow(self):
diff --git a/backend/apps/forms/tests/test_registry.py b/backend/apps/forms/tests/test_registry.py
index 600f604..2f26022 100644
--- a/backend/apps/forms/tests/test_registry.py
+++ b/backend/apps/forms/tests/test_registry.py
@@ -79,7 +79,7 @@ def _means_test(session, monthly_cmi, annual_median, above_median_flag=False):
         district=session.district,
         calculated_cmi=Decimal(monthly_cmi),
         median_income_threshold=Decimal(annual_median),
-        passes_means_test=Decimal(monthly_cmi) * 12 < Decimal(annual_median),
+        passes_means_test=Decimal(monthly_cmi) * 12 <= Decimal(annual_median),
         above_median_calculated=above_median_flag,
     )

@@ -134,16 +134,20 @@ def test_fee_waiver_application_adds_form_103b(session):


 @pytest.mark.parametrize(
-    "monthly_cmi,applies",
-    [("11197.17", True), ("11197.16", False)],  # 134366.04 and 134365.92 a year
+    "monthly_cmi,annual_median,applies",
+    [
+        ("11197.17", "134366.00", True),  # 134366.04 a year
+        ("11197.16", "134366.00", False),  # 134365.92 a year
+        ("5942.00", "71304.00", False),  # exactly the median, which counts as below (DIG-136)
+    ],
 )
-def test_122a2_applies_at_or_above_the_median(session, monthly_cmi, applies):
-    _means_test(session, monthly_cmi, "134366.00")
+def test_122a2_applies_only_above_the_median(session, monthly_cmi, annual_median, applies):
+    _means_test(session, monthly_cmi, annual_median)
     assert ("form_122a2" in packet(session)) is applies


 def test_122a2_ignores_the_sticky_above_median_flag(session):
-    # calculate() sets above_median_calculated and never clears it (DIG-128).
+    # A row calculated before DIG-128 was fixed can still carry above_median_calculated.
     _means_test(session, "2000.00", "71304.00", above_median_flag=True)
     assert "form_122a2" not in packet(session)

PATCH
```

The fractional-cent test is the only way to test the rounding. The ten income columns hold whole cents, so the test puts $5,942.005 on the unsaved instance the session caches, which the means test, `packet()` and `DERIVATIONS` all read. Rounded half-even, that is $5,942.00, exactly the $71,304 median a month. Unrounded, or rounded half up, it is above the median. The test requires the verdict, the packet, `DERIVATIONS["cmi"]` and line 12b to agree. `_expenses_and_priority_debt` builds an above-median filer who passes: expenses at the caps for one person ($2,799 allowed) and $3,500 a month of priority debt leave $701 of disposable income on $7,000 of CMI, under the $756.25 threshold.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/eligibility/tests/test_means_test_calculator.py apps/forms/tests/test_registry.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `5 failed, 64 passed`. The tie counts as above the median in the means test and in the packet (the at-median test and the registry's exact-median case), CMI isn't rounded (the fractional-cent test), an above-median filer who passes reads the below-median text, and a recalculation below the median leaves above_median_calculated set. The one-cent-over test passes already: it guards the other side of the boundary.

- [ ] **Step 3: Round CMI once, and add the one comparison beside it**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/eligibility/cmi.py b/backend/apps/eligibility/cmi.py
index b80ffe4..e2c2f71 100644
--- a/backend/apps/eligibility/cmi.py
+++ b/backend/apps/eligibility/cmi.py
@@ -3,10 +3,12 @@ Current monthly income (CMI), the one figure the means test, the above-median ca
 and the court forms share (forms step 2 spec §5.5).

 CMI counts the filer's monthly income from every source the Income step asks about except
-benefits under the Social Security Act, which 11 U.S.C. § 101(10A)(B) leaves out.
+benefits under the Social Security Act, which 11 U.S.C. § 101(10A)(B) leaves out. It is
+rounded to the cent once, here, so the means test, the packet and 122A-1 compare and print
+the same figure (forms step 2 spec §5.6).
 """

-from decimal import Decimal
+from decimal import ROUND_HALF_EVEN, Decimal


 class IncomeNotSplit(ValueError):
@@ -20,7 +22,7 @@ class IncomeNotSplit(ValueError):


 def current_monthly_income(income_info) -> Decimal:
-    """The ten Income step amounts added up, without Social Security.
+    """The ten Income step amounts added up, without Social Security, to the cent (half-even).

     An amount the filer left empty counts as zero once another one was given.

@@ -34,7 +36,18 @@ def current_monthly_income(income_info) -> Decimal:
     }
     if not given:
         raise IncomeNotSplit()
-    return sum(
+    total = sum(
         (amount for field, amount in given.items() if field != "monthly_social_security"),
         Decimal("0"),
     )
+    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
+
+
+def is_above_median(cmi: Decimal, median_income: Decimal) -> bool:
+    """Whether monthly CMI times 12 is above the district's annual median income.
+
+    Income exactly at the median counts as below it (DIG-136): 11 U.S.C. § 707(b)(7) reads
+    "equal to or less than", and Form 122A-1 line 14a "less than or equal to". The means test
+    and the packet both use this one comparison, so they never disagree at the median.
+    """
+    return cmi * 12 > median_income
PATCH
```

- [ ] **Step 4: Make the means test, its message and the packet use that comparison**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/eligibility/models.py b/backend/apps/eligibility/models.py
index 601a32c..d3698e5 100644
--- a/backend/apps/eligibility/models.py
+++ b/backend/apps/eligibility/models.py
@@ -7,7 +7,7 @@ from django.db import models
 from django.utils import timezone
 from encrypted_model_fields.fields import EncryptedTextField

-from .cmi import current_monthly_income
+from .cmi import current_monthly_income, is_above_median


 class MeansTest(models.Model):
@@ -95,7 +95,8 @@ class MeansTest(models.Model):
         Calculate means test using 11 U.S.C. § 707(b) methodology.

         Returns:
-            bool: True if debtor passes means test (CMI < median income)
+            bool: True if debtor passes means test (CMI × 12 at or below the median income, or
+            above it with disposable income under the threshold)

         Raises:
             ValueError: If required intake data is missing
@@ -133,7 +134,7 @@ class MeansTest(models.Model):
         # Determine if passes means test. CMI is monthly; the Census median
         # is annual, so annualize per 11 U.S.C. § 707(b)(7).
         annualized_cmi = cmi * Decimal("12")
-        passes_test = annualized_cmi < median_income_threshold
+        passes_test = not is_above_median(cmi, median_income_threshold)

         # Initialize calculation details (used by above-median pathway below)
         details: dict = {}
@@ -163,6 +164,13 @@ class MeansTest(models.Model):
                 "priority_debts": float(ded_result.priority_debts_monthly),
                 "passes_above_median": self.passes_above_median,
             }
+        else:
+            # At or below the median: an earlier above-median result no longer holds (DIG-128).
+            self.total_allowable_expenses = Decimal("0")
+            self.disposable_income = Decimal("0")
+            self.priority_debts_monthly = Decimal("0")
+            self.passes_above_median = False
+            self.above_median_calculated = False

         # Calculate fee waiver eligibility (CMI < 150% of poverty line)
         # For MVP, simplified: qualifies if income is very low (< 60% of median)
diff --git a/backend/apps/eligibility/services/means_test_calculator.py b/backend/apps/eligibility/services/means_test_calculator.py
index 4b1f7a1..47b92a3 100644
--- a/backend/apps/eligibility/services/means_test_calculator.py
+++ b/backend/apps/eligibility/services/means_test_calculator.py
@@ -10,7 +10,7 @@ from typing import Any

 from django.db import transaction

-from apps.eligibility.cmi import IncomeNotSplit
+from apps.eligibility.cmi import IncomeNotSplit, is_above_median
 from apps.eligibility.models import MeansTest
 from apps.intake.models import IntakeSession

@@ -131,7 +131,9 @@ class MeansTestCalculator:
         Returns:
             str: UPL-compliant informational message
         """
-        if means_test.passes_means_test:
+        # Which side of the median first, then the expense test: an above-median filer who
+        # passes it must not be told their income is below the median (DIG-128).
+        if not is_above_median(means_test.calculated_cmi, means_test.median_income_threshold):
             message = (
                 "Based on the information provided, your income is below the median "
                 f"income for a household of this size in {self.district.state}. "
diff --git a/backend/apps/forms/registry.py b/backend/apps/forms/registry.py
index 7f03548..ac6c697 100644
--- a/backend/apps/forms/registry.py
+++ b/backend/apps/forms/registry.py
@@ -12,6 +12,7 @@ import re
 from collections.abc import Callable
 from dataclasses import dataclass

+from apps.eligibility.cmi import is_above_median
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.intake.models import IntakeSession
@@ -44,14 +45,15 @@ def _has_fee_waiver(session: IntakeSession) -> bool:

 def _above_median(session: IntakeSession) -> bool:
     """
-    Annualized income at or above the median, from the stored MeansTest.
+    Annualized income above the median, from the stored MeansTest, by the means test's own
+    comparison: income exactly at the median counts as below it (DIG-136).

-    Not above_median_calculated: calculate() sets it and never clears it (DIG-128).
+    Not above_median_calculated: a row calculated before DIG-128 was fixed can still carry it.
     """
     means_test = getattr(session, "means_test", None)
     if means_test is None:
         return False
-    return means_test.calculated_cmi * 12 >= means_test.median_income_threshold
+    return is_above_median(means_test.calculated_cmi, means_test.median_income_threshold)


 def _nothing(session: IntakeSession) -> None:
PATCH
```

`MeansTest.calculate()` passes a filer at or below the median, and below it clears the five above-median fields an earlier run left (DIG-128). The message asks which side of the median the filer is on before it looks at the expense test. `_above_median` makes the packet's 122A-2 rule the means test's own comparison, so the two can't disagree at the median.

- [ ] **Step 5: Amend the step 1 spec's 122A-2 rule**

```bash
git apply <<'PATCH'
diff --git a/docs/superpowers/specs/2026-10-10-forms-foundation-design.md b/docs/superpowers/specs/2026-10-10-forms-foundation-design.md
index a7bc3c9..00250e7 100644
--- a/docs/superpowers/specs/2026-10-10-forms-foundation-design.md
+++ b/docs/superpowers/specs/2026-10-10-forms-foundation-design.md
@@ -252,12 +252,12 @@ A plan step is complete only when a search for `Generator\b`, `get_generator`, `

 ### 5.6 The packet list

-| Form                                                                                      | Applies when                                                                                                                                                                                                                                                                                 |
-| ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
-| 101, 106A/B, 106C, 106D, 106E/F, 106G, 106H, 106I, 106J, 106Sum, 106Dec, 107, 121, 122A-1 | Always                                                                                                                                                                                                                                                                                       |
-| 122A-2                                                                                    | The session's stored `MeansTest` shows annualized income at or above the median: `calculated_cmi × 12 ≥ median_income_threshold`. Both fields are rewritten on every calculation. With no `MeansTest` row, it doesn't apply, and 122A-1's `requires` reports the missing calculation (§5.7). |
-| 103B                                                                                      | A `FeeWaiverApplication` exists for the session                                                                                                                                                                                                                                              |
-| 122A-1Supp                                                                                | The filer claims an exemption from the presumption of abuse. Nothing collects that yet, so it never applies until step 4.                                                                                                                                                                    |
+| Form                                                                                      | Applies when                                                                                                                                                                                                                                                                                                                                                                                                           |
+| ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
+| 101, 106A/B, 106C, 106D, 106E/F, 106G, 106H, 106I, 106J, 106Sum, 106Dec, 107, 121, 122A-1 | Always                                                                                                                                                                                                                                                                                                                                                                                                                 |
+| 122A-2                                                                                    | The session's stored `MeansTest` shows annualized income above the median: `calculated_cmi × 12 > median_income_threshold`. Income exactly at the median counts as below it (amended by the step 2 spec, `2026-10-12-forms-step2-design.md` §5.6, DIG-136). Both fields are rewritten on every calculation. With no `MeansTest` row, it doesn't apply, and 122A-1's `requires` reports the missing calculation (§5.7). |
+| 103B                                                                                      | A `FeeWaiverApplication` exists for the session                                                                                                                                                                                                                                                                                                                                                                        |
+| 122A-1Supp                                                                                | The filer claims an exemption from the presumption of abuse. Nothing collects that yet, so it never applies until step 4.                                                                                                                                                                                                                                                                                              |

 - **Removed: 122B.** It goes from the registry, the model choices, its schema and the frontend. It is the Chapter 11 statement, and its download raised a 500 (DIG-125).
 - **Not added: 106J-2.** It covers a spouse's separate household.
PATCH
```

- [ ] **Step 6: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/eligibility/tests/test_means_test_calculator.py apps/forms/tests/test_registry.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `69 passed`.

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

Expected: `1743 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  300 passed (300)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

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
  backend/apps/eligibility/cmi.py \
  backend/apps/eligibility/models.py \
  backend/apps/eligibility/services/means_test_calculator.py \
  backend/apps/eligibility/tests/test_means_test_calculator.py \
  backend/apps/forms/registry.py \
  backend/apps/forms/tests/test_registry.py \
  docs/superpowers/specs/2026-10-10-forms-foundation-design.md
git commit -F - <<'MSG'
fix(eligibility,forms): count income at the median as below it, and round CMI once

The means test passed a filer only below the median (`<`), and the packet
gave 122A-2 to a filer at or above it (`>=`), so both treated income exactly
at the median as above it. 11 U.S.C. § 707(b)(7) and Form 122A-1 line 14a
both count it as below, and so does the owner's ruling (DIG-136). One
function beside CMI in apps/eligibility/cmi.py, is_above_median, now makes
that comparison (CMI × 12 > median) for the means test and the packet, so
the two can't disagree.

CMI is now rounded to the cent, half-even, inside current_monthly_income, so
the verdict, the packet and the printed 122A-1 figures use one number. Every
stored amount is whole cents, so saved data gets the same CMI as before. The
rounding matters when a fraction of a cent would otherwise decide the verdict
while 122A-1 prints the rounded figure.

DIG-128: a recalculation at or below the median now clears the five
above-median fields (allowable expenses, disposable income, priority debts,
passes_above_median, above_median_calculated). Before, they kept the values
of an earlier above-median run. The result message now asks which side of
the median the filer is on before it looks at the expense test. So an
above-median filer who passes that test reads the above-median text, not
"your income is below the median". No message wording changed; a filer
exactly at the median reads the below-median text.

The step 1 spec's 122A-2 rule is amended to `>`, with a pointer to the
step 2 spec.

test_at_median_income_fails becomes
test_income_exactly_at_median_is_below_median and now expects a pass and no
122A-2. test_122a2_applies_at_or_above_the_median becomes
test_122a2_applies_only_above_the_median, with an exact-median case. New
tests cover one cent over the median, a fractional-cent CMI, the
above-median filer who passes, and the reset after recalculating below the
median.

Forms step 2a, commit 5 (step 2 spec §5.6).
MSG
git status --short
```

### Task 11: Work the means test out before every packet, and keep filed forms

_Built and verified as commit `a0f47cd` on `plan/forms-step2a`._

**Files:**

- Modify: `backend/apps/forms/tests/conftest.py`
- Modify: `backend/apps/forms/tests/test_api_readback.py`
- Modify: `backend/apps/forms/tests/test_form_views.py`
- Modify: `backend/apps/forms/views.py`
- Modify: `backend/apps/intake/tests/test_completion.py`
- Modify: `backend/apps/intake/tests/test_income_resume.py`
- Modify: `frontend/src/components/forms/FormCard.tsx`
- Modify: `frontend/src/pages/FormDashboard.tsx`
- Modify: `frontend/src/pages/__tests__/FormDashboard.test.tsx`

**Interfaces:**

- Consumes:
  - `MeansTestCalculator(session).calculate()` from `apps.eligibility.services`, the service the means-test endpoint uses. It raises `IncomeNotSplit` (Task 9, sentence "Enter your income by source on the Income step.") and a `ValueError` when the district has no median income data.
  - `is_above_median` through `packet(session)` (Task 10).
  - `_check_finished`, `IntakeNotFinished`, `_FAILURE_SENTENCES` and Generate All's whole-call 422 `{"error": "Finish your intake before preparing your forms."}` in `apps/forms/views.py` (Task 2).
  - `FormCard` and `FormDashboard`'s `packet` and `forms` state (step 1).
- Produces:
  - In `apps/forms/views.py`:
    - `_recalculate_means_test(session)`, which calls `MeansTestCalculator(session).calculate()`;
    - `_prepare(session)`, which runs `_check_finished` and then `_recalculate_means_test`, once per call. `_fill` no longer runs `_check_finished`; every caller runs `_prepare` first;
    - `_failure(form_type: str | None, exc)`. With `form_type=None` the body is `{"error": ...}` with no form named, and a 500 logs `Filling the packet failed: <ExceptionType>`.
  - `GET /api/forms/packet/?session=<id>`: for a completed intake it works the means test out first. A refusal covers the whole list: 422 `{"error": "Enter your income by source on the Income step."}`, or 500 `{"error": "This form couldn't be prepared. Please try again later."}`. An unfinished intake gets the packet its stored data gives, with no write and no refusal.
  - `POST /api/forms/generate_all/`: completion check, recalculation, `packet()`, then the delete. It refuses with the same whole-call bodies before it deletes anything. It never deletes a filed form, and it appends each filed form that left the packet to `generated`, after the packet's forms; `total_generated` counts them.
  - `generate`, `regenerate` and the download of an unfiled form run `_prepare` and refuse with the per-form body `{"form_type": ..., "error": ...}` (the same 422 and 500).
  - The download of a filed form with stored `field_values` fills from them without the `applies()` check.
  - `FormCard` gains the optional prop `leftPacket?: boolean`, which adds the caption line "Filed, no longer in your current packet". `FormDashboard` renders each filed form whose type is not in the packet after the packet's cards, with `leftPacket`.
  - Tests: `TestMeansTestWorkedOutAgain` (`test_stale_means_test_no_longer_decides_the_packet[income_fell_below_the_median]` and `[income_rose_above_the_median]`, `test_unfinished_intake_reads_the_packet_its_stored_data_gives`, `test_income_not_split_refuses_every_call_that_prepares_forms`, `test_missing_median_income_is_a_500_logged_by_type_only`), `test_filed_form_survives_leaving_the_packet`, and the vitest "keeps showing a filed form after it leaves the packet, and says so".
  - For Task 12: Generate All and the packet list both refuse a whole call with an `{"error": ...}` body, 422 or 500.

**Decisions already made in this task:**

- The means test runs once per call, through `_prepare(session)` at each entry point (Generate, Generate All, Regenerate, the unfiled download), and `_check_finished` moves from `_fill` into `_prepare`. Generate All calls `_fill` once per form, so recalculating there would run the means test about 14 times and turn a missing median into 14 per-form 500s, not one refusal. §5.3's "share it through `_fill`" now holds through `_prepare`, with the same behavior.
- Generate and Regenerate run `_prepare` before the "marked as filed" check. A filed form on a reopened intake therefore gets "Finish your intake before preparing your forms." (still a 422) instead of the filed sentence. No screen reaches this: `FormCard` offers Generate only for a pending form, and the frontend never calls regenerate.
- The packet view tests `session.status == "completed"` itself, the same rule as `_check_finished`, rather than catching `IntakeNotFinished` for control flow.
- A whole-call 500 (Generate All, the packet list) reuses the existing sentence "This form couldn't be prepared. Please try again later." The spec gives no whole-call 500 sentence, and Task 12 shows its own generic text for a 500. The log line is `Filling the packet failed: <ExceptionType>`, type only (DIG-105).
- A completed intake with no `IncomeInfo` gets a 500 (the calculator's `ValueError`), not a skipped recalculation. Complete refuses an intake without income, so the API can't reach that state, and skipping would let a stale row decide the packet.
- `_recalculate_means_test` uses `MeansTestCalculator(session).calculate()` as it is, including the message the views discard, so the means test keeps one code path.
- Filed forms that left the packet come last in Generate All's `generated`, and `total_generated` counts them, because the dashboard replaces its list with `generated`. Without them the card would vanish after Generate All.
- On the dashboard such a form is a normal `FormCard` after the packet's cards, with the spec's sentence word for word as a second caption line: "Filed, no longer in your current packet". It keeps its "Filed" badge and Download button. "X of N generated" still counts only packet forms (the test pins it); "| K filed" still counts every filed form, as before.
- Four fixtures load the real ILND data (`loaddata ilnd_2025_data`) for its median row: the `district` fixtures in `test_form_views.py` and `test_completion.py`, `filer_session` in `test_income_resume.py`, and `generated_form_factory` in the forms `conftest.py`. The read-back, tier 3 and coverage tests already load it.
- `test_form_views.py`'s base `session` fixture carries the income Complete requires (wages $3,000), so `session_with_income` is deleted and its 8 uses move to `session_with_debtor`.
- `test_generates_every_form_in_the_packet` keeps its intent: one form's missing data is reported and doesn't undo the others. 122A-1 now fills, because Generate All works the means test out, so the failing form is Form 121, through an empty SSN.
- `test_legacy_income_total_must_be_split_before_forms_print` now expects Generate All's whole-call 422, not a per-form entry in `errors`: one refusal covers the whole call.
- The read-back keeps its fee-waiver guard as an assertion on the `MeansTest` row Generate All stores, instead of dropping it with the `calculate_means_test` call.
- Until Task 12, a completed intake whose packet list is refused sees no cards and "Unable to load your forms. Please try refreshing the page." Only a legacy income total or a district with no median row gets there, and no persona does. Task 12 shows the refusal (DIG-156); nothing ships in between.
- The packet list for a completed intake now writes the `MeansTest` row. Measured for Priya (median of 3), it went from 7 ms to 24 ms; Generate All and a download moved within noise.
- `known_defects.json` doesn't change: tier 3 resolves seeded sessions directly, never through the views.

- [ ] **Step 1: Write the backend tests, and give the view tests a median and income**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/conftest.py b/backend/apps/forms/tests/conftest.py
index 9f166ef..824d0e1 100644
--- a/backend/apps/forms/tests/conftest.py
+++ b/backend/apps/forms/tests/conftest.py
@@ -1,14 +1,16 @@
 """Shared test fixtures for the forms app."""

 from datetime import date
+from decimal import Decimal

 import pytest
 from django.contrib.auth import get_user_model
+from django.core.management import call_command
 from rest_framework.test import APIClient

 from apps.districts.models import District
 from apps.forms.models import GeneratedForm
-from apps.intake.models import DebtorInfo, IntakeSession
+from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

 User = get_user_model()

@@ -27,13 +29,9 @@ def generated_form_factory(db, api_client_authed):
         user = User.objects.filter(username="testuser").first()
         district = District.objects.filter(code="ilnd").first()
         if not district:
-            district = District.objects.create(
-                code="ilnd",
-                name="Northern District of Illinois",
-                court_name="U.S. Bankruptcy Court, N.D. Ill.",
-                state="IL",
-                filing_fee_chapter_7="338.00",
-            )
+            # The real ILND data: preparing a form works the means test out against its median.
+            call_command("loaddata", "ilnd_2025_data", verbosity=0)
+            district = District.objects.get(code="ilnd")
         session = IntakeSession.objects.create(
             user=user, district=district, status="completed", current_step=6
         )
@@ -48,6 +46,7 @@ def generated_form_factory(db, api_client_authed):
             state="IL",
             zip_code="60622",
         )
+        IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("2800.00"))
         return GeneratedForm.objects.create(
             session=session,
             form_type="form_121",
diff --git a/backend/apps/forms/tests/test_api_readback.py b/backend/apps/forms/tests/test_api_readback.py
index c967b32..07c2142 100644
--- a/backend/apps/forms/tests/test_api_readback.py
+++ b/backend/apps/forms/tests/test_api_readback.py
@@ -24,6 +24,7 @@ from django.core.serializers.json import DjangoJSONEncoder
 from rest_framework.test import APIClient

 from apps.districts.models import District
+from apps.eligibility.models import MeansTest
 from apps.forms.models import GeneratedForm
 from apps.forms.registry import build_field_values, packet
 from apps.forms.schema import load_schema
@@ -92,11 +93,8 @@ def _send_through_the_api(persona):
         assert response.status_code == 200, (endpoint, response.data)

     # Complete Intake, then the pages that follow it. Their saves keep the intake complete.
+    # No means-test call: Generate All works it out from the stored intake (spec §5.6).
     assert client.post(f"{session_url}complete/").status_code == 200
-    means_test = client.post(f"{session_url}calculate_means_test/")
-    assert means_test.status_code == 200
-    qualifies = means_test.data["means_test_result"]["qualifies_for_fee_waiver"]
-    assert qualifies == (persona in WAIVER_FILERS)
     if persona in WAIVER_FILERS:
         response = client.post(
             "/api/intake/fee-waiver/",
@@ -113,6 +111,10 @@ def _send_through_the_api(persona):
     generated = client.post("/api/forms/generate_all/", {"session_id": session_id}, format="json")
     assert generated.status_code == 200
     assert generated.data["errors"] == []
+    # Generate All worked the means test out, and it qualifies exactly the filers the wizard
+    # sends to the fee-waiver page.
+    qualifies = MeansTest.objects.get(session_id=session_id).qualifies_for_fee_waiver
+    assert qualifies == (persona in WAIVER_FILERS)
     return session_id, [form["form_type"] for form in generated.data["generated"]]


diff --git a/backend/apps/forms/tests/test_form_views.py b/backend/apps/forms/tests/test_form_views.py
index 6c51e64..b9ee1dc 100644
--- a/backend/apps/forms/tests/test_form_views.py
+++ b/backend/apps/forms/tests/test_form_views.py
@@ -11,6 +11,8 @@ Covers:
   - Permission enforcement (users see only their own sessions)
   - The error contract: 422 with a reason, 500 logged by type only
   - The encrypted snapshot never leaves the server
+  - The means test is worked out again on every call that decides the packet
+  - A filed form stays, and downloads, after it leaves the packet
 """

 import json
@@ -20,11 +22,13 @@ from unittest.mock import patch

 import pytest
 from django.contrib.auth import get_user_model
+from django.core.management import call_command
 from django.db import connection
 from rest_framework import status
 from rest_framework.test import APIClient

-from apps.districts.models import District
+from apps.districts.models import District, MedianIncome
+from apps.eligibility.models import MeansTest
 from apps.forms.models import GeneratedForm
 from apps.forms.services.fill_resolver import UnmappedChoice
 from apps.forms.services.pdf_filler import (
@@ -33,8 +37,10 @@ from apps.forms.services.pdf_filler import (
     TemplateHasNoForm,
     UnknownField,
 )
+from apps.forms.tests.pdf_readback import read_widgets
 from apps.intake.models import (
     DebtorInfo,
+    ExpenseInfo,
     IncomeInfo,
     IntakeSession,
 )
@@ -83,20 +89,23 @@ def unauth_client():

 @pytest.fixture
 def district(db):
-    return District.objects.create(
-        code="ilnd",
-        name="Northern District of Illinois",
-        state="IL",
-        court_name="U.S. Bankruptcy Court, Northern District of Illinois",
-        pro_se_efiling_allowed=False,
-        filing_fee_chapter_7=Decimal("338.00"),
-    )
+    # The real ILND data: preparing forms works the means test out against its median income.
+    call_command("loaddata", "ilnd_2025_data", verbosity=0)
+    return District.objects.get(code="ilnd")


 @pytest.fixture
 def session(user, district):
-    # Forms are prepared only from an intake the filer completed (spec §5.3).
-    return IntakeSession.objects.create(user=user, district=district, status="completed")
+    # Forms are prepared only from an intake the filer completed (spec §5.3), and Complete
+    # requires income, which the means test reads on every call (spec §5.6).
+    session = IntakeSession.objects.create(user=user, district=district, status="completed")
+    IncomeInfo.objects.create(
+        session=session,
+        marital_status="single",
+        number_of_dependents=0,
+        monthly_gross_wages=Decimal("3000.00"),
+    )
+    return session


 @pytest.fixture
@@ -119,18 +128,6 @@ def session_with_debtor(session):
     return session


-@pytest.fixture
-def session_with_income(session_with_debtor):
-    """Session with debtor + income info for means test generators."""
-    IncomeInfo.objects.create(
-        session=session_with_debtor,
-        marital_status="single",
-        number_of_dependents=0,
-        monthly_gross_wages=Decimal("3000.00"),
-    )
-    return session_with_debtor
-
-
 @pytest.fixture
 def other_session(other_user, district):
     return IntakeSession.objects.create(user=other_user, district=district)
@@ -195,10 +192,10 @@ class TestGenerateEndpoint:
         assert resp.status_code == status.HTTP_200_OK
         assert resp.data["form"]["form_type"] == "schedule_a_b"

-    def test_generate_schedule_i(self, api_client, session_with_income):
+    def test_generate_schedule_i(self, api_client, session_with_debtor):
         resp = api_client.post(
             self.URL,
-            {"session_id": session_with_income.id, "form_type": "schedule_i"},
+            {"session_id": session_with_debtor.id, "form_type": "schedule_i"},
             format="json",
         )
         assert resp.status_code == status.HTTP_200_OK
@@ -379,36 +376,42 @@ class TestGenerateAllEndpoint:

     URL = "/api/forms/generate_all/"

-    def test_generates_every_form_in_the_packet(self, api_client, session_with_income):
+    def test_generates_every_form_in_the_packet(self, api_client, session_with_debtor):
         """One form's missing data is reported and doesn't undo the others."""
+        debtor = session_with_debtor.debtor_info
+        debtor.ssn = ""
+        debtor.save()
         resp = api_client.post(
             self.URL,
-            {"session_id": session_with_income.id},
+            {"session_id": session_with_debtor.id},
             format="json",
         )
         assert resp.status_code == status.HTTP_200_OK
-        # No fee waiver: no 103B. No means test yet: 122A-1 can't fill, and no 122A-2.
+        # No fee waiver: no 103B. Income below the median: no 122A-2. Form 121 needs the SSN.
         assert resp.data["errors"] == [
-            {"form_type": "form_122a1", "error": "The eligibility check hasn't been run yet."}
+            {
+                "form_type": "form_121",
+                "error": "Your Social Security number is missing or isn't 9 digits.",
+            }
         ]
         assert resp.data["total_generated"] == 13
-        assert GeneratedForm.objects.filter(session=session_with_income).count() == 13
+        assert GeneratedForm.objects.filter(session=session_with_debtor).count() == 13

-    def test_drops_forms_that_no_longer_apply(self, api_client, session_with_income, user):
+    def test_drops_forms_that_no_longer_apply(self, api_client, session_with_debtor, user):
         GeneratedForm.objects.create(
-            session=session_with_income, form_type="form_103b", generated_by=user
+            session=session_with_debtor, form_type="form_103b", generated_by=user
         )
-        api_client.post(self.URL, {"session_id": session_with_income.id}, format="json")
+        api_client.post(self.URL, {"session_id": session_with_debtor.id}, format="json")
         assert not GeneratedForm.objects.filter(
-            session=session_with_income, form_type="form_103b"
+            session=session_with_debtor, form_type="form_103b"
         ).exists()

-    def test_filed_form_is_returned_as_filed(self, api_client, session_with_income, user):
+    def test_filed_form_is_returned_as_filed(self, api_client, session_with_debtor, user):
         # The dashboard replaces its list with `generated`, so a filed form must be in it.
-        form = _filed_form(session_with_income, user, "form_106dec", {"Debtor 1": "Jane Doe"})
-        _rename_filer(session_with_income, "Janet")
+        form = _filed_form(session_with_debtor, user, "form_106dec", {"Debtor 1": "Jane Doe"})
+        _rename_filer(session_with_debtor, "Janet")

-        resp = api_client.post(self.URL, {"session_id": session_with_income.id}, format="json")
+        resp = api_client.post(self.URL, {"session_id": session_with_debtor.id}, format="json")

         assert resp.status_code == status.HTTP_200_OK
         returned = [f for f in resp.data["generated"] if f["form_type"] == "form_106dec"]
@@ -417,7 +420,7 @@ class TestGenerateAllEndpoint:
         assert form.status == "filed"
         assert json.loads(form.field_values) == {"Debtor 1": "Jane Doe"}
         # The forms not yet filed are resolved from the current answers.
-        petition = GeneratedForm.objects.get(session=session_with_income, form_type="form_101")
+        petition = GeneratedForm.objects.get(session=session_with_debtor, form_type="form_101")
         assert json.loads(petition.field_values)["Debtor1.First name"] == "Janet"

     def test_missing_session_id(self, api_client):
@@ -628,8 +631,8 @@ FINISH = "Finish your intake before preparing your forms."
 class TestCompletionCheck:
     """Until the filer presses Complete, an empty list can't mean "none"."""

-    def test_unfinished_intake_cannot_prepare_forms(self, api_client, session_with_income, user):
-        session = session_with_income
+    def test_unfinished_intake_cannot_prepare_forms(self, api_client, session_with_debtor, user):
+        session = session_with_debtor
         session.status = "in_progress"
         session.save()
         # No fee waiver application, so 103B has left the packet; 101 is in it, unfiled.
@@ -689,6 +692,215 @@ class TestCompletionCheck:
         assert resp["Content-Type"] == "application/pdf"


+# ── The means test is worked out again before the packet is decided (spec §5.6) ──
+
+SPLIT_BY_SOURCE = "Enter your income by source on the Income step."
+NOT_PREPARED = "This form couldn't be prepared. Please try again later."
+
+
+def _set_wages(session, wages):
+    income = session.income_info
+    income.monthly_gross_wages = None if wages is None else Decimal(wages)
+    income.save()
+
+
+def _stale_means_test(session, cmi):
+    """A stored result, worked out from income the filer has since changed."""
+    MeansTest.objects.update_or_create(
+        session=session,
+        defaults={
+            "district": session.district,
+            "median_income_threshold": Decimal("71304.00"),
+            "calculated_cmi": Decimal(cmi),
+            "passes_means_test": Decimal(cmi) * 12 <= Decimal("71304.00"),
+        },
+    )
+
+
+@pytest.mark.django_db
+class TestMeansTestWorkedOutAgain:
+    """122A-2 and 122A-1 follow the filer's current income, never an old result (DIG-160)."""
+
+    @pytest.mark.parametrize(
+        "wages,stale_cmi,above_median",
+        [("3000.00", "9000.00", False), ("9000.00", "3000.00", True)],
+        ids=["income_fell_below_the_median", "income_rose_above_the_median"],
+    )
+    def test_stale_means_test_no_longer_decides_the_packet(
+        self, api_client, session_with_debtor, wages, stale_cmi, above_median
+    ):
+        session = session_with_debtor
+        _set_wages(session, wages)
+
+        _stale_means_test(session, stale_cmi)
+        listed = api_client.get("/api/forms/packet/", {"session": session.id})
+        _stale_means_test(session, stale_cmi)
+        generated = api_client.post(
+            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
+        )
+        _stale_means_test(session, stale_cmi)
+        single = api_client.post(
+            "/api/forms/generate/",
+            {"session_id": session.id, "form_type": "form_122a2"},
+            format="json",
+        )
+
+        assert ("form_122a2" in listed.data["form_types"]) is above_median
+        assert generated.data["errors"] == []
+        assert ("form_122a2" in [f["form_type"] for f in generated.data["generated"]]) is (
+            above_median
+        )
+        assert single.status_code == (
+            status.HTTP_200_OK if above_median else status.HTTP_422_UNPROCESSABLE_ENTITY
+        )
+        # The stored result is the one worked out from the filer's current income.
+        assert MeansTest.objects.get(session=session).calculated_cmi == Decimal(wages)
+
+    def test_unfinished_intake_reads_the_packet_its_stored_data_gives(
+        self, api_client, session_with_debtor
+    ):
+        # Never refused, even with income not yet split by source, and nothing is redone.
+        session = session_with_debtor
+        session.status = "in_progress"
+        session.save()
+        session.income_info.monthly_income = [3000] * 6
+        _set_wages(session, None)
+        _stale_means_test(session, "9000.00")
+
+        resp = api_client.get("/api/forms/packet/", {"session": session.id})
+
+        assert resp.status_code == status.HTTP_200_OK
+        assert "form_122a2" in resp.data["form_types"]
+        assert MeansTest.objects.get(session=session).calculated_cmi == Decimal("9000.00")
+
+    def test_income_not_split_refuses_every_call_that_prepares_forms(
+        self, api_client, session_with_debtor, user
+    ):
+        session = session_with_debtor
+        # A total saved before income was stored by source.
+        session.income_info.monthly_income = [3000] * 6
+        _set_wages(session, None)
+        # No fee waiver application, so 103B has left the packet. 106B-Dec reads no income.
+        GeneratedForm.objects.create(session=session, form_type="form_103b", generated_by=user)
+        unfiled = GeneratedForm.objects.create(
+            session=session, form_type="form_106dec", status="generated", generated_by=user
+        )
+        filed = _filed_form(session, user, "form_121", {"Debtor1.First name": "Jane"})
+
+        generate_all = api_client.post(
+            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
+        )
+        listed = api_client.get("/api/forms/packet/", {"session": session.id})
+        generate = api_client.post(
+            "/api/forms/generate/",
+            {"session_id": session.id, "form_type": "form_106dec"},
+            format="json",
+        )
+        regenerate = api_client.post(f"/api/forms/{unfiled.id}/regenerate/")
+        download = api_client.get(f"/api/forms/{unfiled.id}/download/")
+        filed_download = api_client.get(f"/api/forms/{filed.id}/download/")
+
+        # One refusal covers the whole call, the packet list included.
+        for resp in (generate_all, listed):
+            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
+            assert resp.data == {"error": SPLIT_BY_SOURCE}
+        for resp in (generate, regenerate, download):
+            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
+            assert resp.data == {"form_type": "form_106dec", "error": SPLIT_BY_SOURCE}
+        # Generate All refused before it dropped the form that left the packet.
+        assert set(
+            GeneratedForm.objects.filter(session=session).values_list("form_type", flat=True)
+        ) == {"form_103b", "form_106dec", "form_121"}
+        # The filed copy prints what was filed, which needs no means test.
+        assert filed_download.status_code == status.HTTP_200_OK
+
+    def test_missing_median_income_is_a_500_logged_by_type_only(
+        self, api_client, session_with_debtor, user, caplog
+    ):
+        session = session_with_debtor
+        MedianIncome.objects.filter(district=session.district).delete()
+        GeneratedForm.objects.create(session=session, form_type="form_103b", generated_by=user)
+        unfiled = GeneratedForm.objects.create(
+            session=session, form_type="form_106dec", status="generated", generated_by=user
+        )
+
+        generate_all = api_client.post(
+            "/api/forms/generate_all/", {"session_id": session.id}, format="json"
+        )
+        listed = api_client.get("/api/forms/packet/", {"session": session.id})
+        generate = api_client.post(
+            "/api/forms/generate/",
+            {"session_id": session.id, "form_type": "form_106dec"},
+            format="json",
+        )
+        download = api_client.get(f"/api/forms/{unfiled.id}/download/")
+
+        for resp in (generate_all, listed):
+            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
+            assert resp.data == {"error": NOT_PREPARED}
+        for resp in (generate, download):
+            assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
+            assert resp.data == {"form_type": "form_106dec", "error": NOT_PREPARED}
+        assert set(
+            GeneratedForm.objects.filter(session=session).values_list("form_type", flat=True)
+        ) == {"form_103b", "form_106dec"}
+        # Operations fix this; the log names the exception's type and nothing it says.
+        assert "ValueError" in caplog.text
+        assert "median income data" not in caplog.text
+
+
+# ── A filed form is kept after it leaves the packet (DIG-155) ─────────
+
+
+@pytest.mark.django_db
+def test_filed_form_survives_leaving_the_packet(api_client, session_with_debtor):
+    session = session_with_debtor
+    ExpenseInfo.objects.create(session=session)  # Complete requires it
+    _set_wages(session, "9000.00")  # above the median: 122A-2 is in the packet
+    api_client.post("/api/forms/generate_all/", {"session_id": session.id}, format="json")
+    form = GeneratedForm.objects.get(session=session, form_type="form_122a2")
+    assert api_client.post(f"/api/forms/{form.id}/mark_filed/").status_code == 200
+    form.refresh_from_db()
+    filed_values = json.loads(form.field_values)
+
+    # The filer's income falls below the median, they correct their first name, and they
+    # complete the intake again.
+    session_url = f"/api/intake/sessions/{session.id}/"
+    lowered = api_client.patch(
+        session_url,
+        {
+            "income_info": {"monthly_gross_wages": "3000.00"},
+            "debtor_info": {"first_name": "Janet"},
+        },
+        format="json",
+    )
+    assert lowered.status_code == 200
+    assert api_client.post(f"{session_url}complete/").status_code == 200
+    regenerated = api_client.post(
+        "/api/forms/generate_all/", {"session_id": session.id}, format="json"
+    )
+    listed = api_client.get("/api/forms/packet/", {"session": session.id})
+    download = api_client.get(f"/api/forms/{form.id}/download/")
+
+    assert "form_122a2" not in listed.data["form_types"]
+    # Generate All keeps it as filed, and returns it, so the dashboard still shows it.
+    assert [
+        (f["id"], f["status"])
+        for f in regenerated.data["generated"]
+        if f["form_type"] == "form_122a2"
+    ] == [(form.id, "filed")]
+    form.refresh_from_db()
+    assert json.loads(form.field_values) == filed_values
+    # It downloads, and prints what was filed, the old name included.
+    assert download.status_code == status.HTTP_200_OK
+    printed = {w.full_name: w.value for w in read_widgets(download.content)}
+    typed = {
+        name: value for name, value in filed_values.items() if value and not value.startswith("/")
+    }
+    assert "Jane Doe" in typed.values()
+    assert {name: printed.get(name) for name in typed} == typed
+
+
 # ── The snapshot stays on the server (DIG-124) ────────────────────────


diff --git a/backend/apps/intake/tests/test_completion.py b/backend/apps/intake/tests/test_completion.py
index 56bde9a..1ee344f 100644
--- a/backend/apps/intake/tests/test_completion.py
+++ b/backend/apps/intake/tests/test_completion.py
@@ -11,6 +11,7 @@ from datetime import date
 from decimal import Decimal

 import pytest
+from django.core.management import call_command
 from rest_framework.test import APIClient

 from apps.districts.models import District
@@ -29,14 +30,10 @@ FINISH = "Finish your intake before preparing your forms."

 @pytest.fixture
 def district(db):
-    # The name is one of the court forms' district choices, so forms fill.
-    return District.objects.create(
-        code="ilnd",
-        name="Northern District of Illinois",
-        state="IL",
-        court_name="U.S. Bankruptcy Court, Northern District of Illinois",
-        filing_fee_chapter_7=Decimal("338.00"),
-    )
+    # The real ILND data: its name is one of the court forms' district choices, and preparing
+    # forms works the means test out against its median income.
+    call_command("loaddata", "ilnd_2025_data", verbosity=0)
+    return District.objects.get(code="ilnd")


 @pytest.fixture
diff --git a/backend/apps/intake/tests/test_income_resume.py b/backend/apps/intake/tests/test_income_resume.py
index 0d03b1f..b2a2fc9 100644
--- a/backend/apps/intake/tests/test_income_resume.py
+++ b/backend/apps/intake/tests/test_income_resume.py
@@ -11,6 +11,7 @@ from datetime import date
 from decimal import Decimal

 import pytest
+from django.core.management import call_command
 from rest_framework.test import APIClient

 from apps.districts.models import District
@@ -35,14 +36,10 @@ TEN_EMPTY = {

 @pytest.fixture
 def filer_session(db):
-    # The name is one of the court forms' district choices, so forms fill.
-    district = District.objects.create(
-        code="ilnd",
-        name="Northern District of Illinois",
-        state="IL",
-        court_name="U.S. Bankruptcy Court, Northern District of Illinois",
-        filing_fee_chapter_7=Decimal("338.00"),
-    )
+    # The real ILND data: its name is one of the court forms' district choices, and preparing
+    # forms works the means test out against its median income.
+    call_command("loaddata", "ilnd_2025_data", verbosity=0)
+    district = District.objects.get(code="ilnd")
     filer = User.objects.create_user(username="filer", password="pw")
     session = IntakeSession.objects.create(user=filer, district=district)
     client = APIClient()
@@ -226,8 +223,10 @@ def test_legacy_income_total_must_be_split_before_forms_print(filer_session):
     refused = client.post("/api/forms/generate/", generate, format="json")
     assert refused.status_code == 422
     assert refused.data == {"form_type": "schedule_i", "error": SPLIT_BY_SOURCE}
+    # Every form waits for the split, since each call works the means test out first.
     every_form = client.post("/api/forms/generate_all/", {"session_id": session.pk}, format="json")
-    assert {"form_type": "schedule_i", "error": SPLIT_BY_SOURCE} in every_form.data["errors"]
+    assert every_form.status_code == 422
+    assert every_form.data == {"error": SPLIT_BY_SOURCE}

     # The filer splits the total on the Income step and completes the intake again.
     split = client.patch(
PATCH
```

`test_stale_means_test_no_longer_decides_the_packet` plants a stale `MeansTest` row before each of three calls (the packet list, Generate All, Generate of 122A-2), in both directions, and checks the stored CMI afterwards. `test_income_not_split_refuses_every_call_that_prepares_forms` uses Form 106Dec, which reads no income, so only the up-front recalculation can refuse it. `test_filed_form_survives_leaving_the_packet` builds its state through the API: Generate All above the median, `mark_filed` on 122A-2, then a PATCH that lowers the income and renames the filer (which reopens the intake), and Complete. Its download must print the filed "Jane Doe", so a fresh resolve, which would print "Janet Doe", fails it.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/forms/tests/test_form_views.py apps/forms/tests/test_api_readback.py apps/intake/tests/test_completion.py apps/intake/tests/test_income_resume.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `12 failed, 82 passed`. Nothing works the means test out yet. A stale row decides the packet (both stale cases). Unsplit income and a missing median refuse nothing. Generate All can't fill 122A-1, because no means test has run ("The eligibility check hasn't been run yet."), which fails the five read-backs and test_generates_every_form_in_the_packet. Above the median 122A-2 never enters the packet, so the filed-form test finds no 122A-2 to file. The unfinished-intake test passes already: it guards the side that must not change.

- [ ] **Step 3: Write the dashboard test**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/FormDashboard.test.tsx b/frontend/src/pages/__tests__/FormDashboard.test.tsx
index c523e06..0e86d6c 100644
--- a/frontend/src/pages/__tests__/FormDashboard.test.tsx
+++ b/frontend/src/pages/__tests__/FormDashboard.test.tsx
@@ -184,6 +184,36 @@ describe('FormDashboard', () => {
     expect(screen.queryByText('Form 122A-2 - Means Test Expenses')).not.toBeInTheDocument();
   });

+  it('keeps showing a filed form after it leaves the packet, and says so', async () => {
+    // 122A-2 was filed, then income dropped below the median (forms step 2 §5.6, DIG-155)
+    server.use(
+      http.get('http://localhost:8000/api/forms/packet/', () =>
+        HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
+      ),
+      http.get('http://localhost:8000/api/forms/', () =>
+        HttpResponse.json([
+          { id: 1, session: 1, form_type: 'form_101', status: 'generated' },
+          { id: 2, session: 1, form_type: 'form_121', status: 'filed' },
+          { id: 3, session: 1, form_type: 'form_122a2', status: 'filed' },
+          { id: 4, session: 1, form_type: 'form_103b', status: 'generated' },
+        ])
+      )
+    );
+
+    renderFormDashboard();
+    await screen.findByText('Form 101 - Voluntary Petition');
+
+    // Only the filed form outside the packet carries the note; filed 121 is in the packet
+    const notes = screen.queryAllByText('Filed, no longer in your current packet');
+    expect(notes).toHaveLength(1);
+    const leftPacket = notes[0].closest('article') as HTMLElement;
+    expect(leftPacket).toHaveAttribute('aria-label', 'Form 122A-2 - Means Test Expenses');
+    expect(within(leftPacket).getByRole('button', { name: /download/i })).toBeInTheDocument();
+    // A form that left the packet without being filed is neither shown nor counted
+    expect(screen.queryByText('Form 103B - Fee Waiver Application')).not.toBeInTheDocument();
+    expect(screen.getByText(/^2 of 2 generated/)).toBeInTheDocument();
+  });
+
   it('shows error banner when generate_all returns partial failures', async () => {
     server.use(
       http.post('http://localhost:8000/api/forms/generate_all/', () =>
PATCH
```

- [ ] **Step 4: Run it and watch it fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx 2>&1 | tail -40
```

Expected: FAIL — `expected [] to have a length of 1`: no card says the filed 122A-2 has left the packet.

- [ ] **Step 5: Work the means test out once per call, refuse the whole call when it can't run, and keep filed forms**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/views.py b/backend/apps/forms/views.py
index 6dfb31a..f60526e 100644
--- a/backend/apps/forms/views.py
+++ b/backend/apps/forms/views.py
@@ -20,6 +20,7 @@ from rest_framework.response import Response
 from rest_framework.views import APIView

 from apps.eligibility.cmi import IncomeNotSplit
+from apps.eligibility.services import MeansTestCalculator
 from apps.intake.models import IntakeSession

 from .models import GeneratedForm
@@ -71,23 +72,25 @@ _FAILURE_SENTENCES = {
 }


-def _failure(form_type: str, exc: Exception) -> tuple[dict, int]:
-    """The error body and status for a form that could not be filled."""
+def _failure(form_type: str | None, exc: Exception) -> tuple[dict, int]:
+    """The error body and status for a form that could not be filled.
+
+    form_type is None when the whole call is refused before any form is filled (Generate
+    All, the packet list): the body then names no form.
+    """
     if isinstance(exc, PreconditionMissing | IncomeNotSplit):
         error = str(exc)
     else:
         error = _FAILURE_SENTENCES.get(type(exc))
-    if error is not None:
-        return {"form_type": form_type, "error": error}, status.HTTP_422_UNPROCESSABLE_ENTITY
-    # Type only: a message or traceback can quote filer data, and logs reach Sentry (DIG-105).
-    logger.error("Filling %s failed: %s", form_type, type(exc).__name__)
-    return (
-        {
-            "form_type": form_type,
-            "error": "This form couldn't be prepared. Please try again later.",
-        },
-        status.HTTP_500_INTERNAL_SERVER_ERROR,
-    )
+    code = status.HTTP_422_UNPROCESSABLE_ENTITY
+    if error is None:
+        # Type only: a message or traceback can quote filer data, and logs reach Sentry (DIG-105).
+        logger.error("Filling %s failed: %s", form_type or "the packet", type(exc).__name__)
+        error = "This form couldn't be prepared. Please try again later."
+        code = status.HTTP_500_INTERNAL_SERVER_ERROR
+    if form_type is None:
+        return {"error": error}, code
+    return {"form_type": form_type, "error": error}, code


 def _session_or_error(
@@ -136,9 +139,25 @@ def _check_finished(session: IntakeSession) -> None:
         raise IntakeNotFinished()


-def _fill(form_type: str, session: IntakeSession) -> tuple[dict[str, str], bytes]:
-    """Resolve a form that applies to this filer and fill its template."""
+def _recalculate_means_test(session: IntakeSession) -> None:
+    """Work the means test out again from the stored intake (step 2 spec §5.6).
+
+    It runs before the packet is decided, so a result worked out from income the filer has
+    since changed never decides which forms they get (DIG-160). Raises IncomeNotSplit when
+    the income isn't entered by source, and ValueError when the district's median income
+    data is missing, which operations must fix.
+    """
+    MeansTestCalculator(session).calculate()
+
+
+def _prepare(session: IntakeSession) -> None:
+    """Refuse an unfinished intake, then work its means test out again. Once per call."""
     _check_finished(session)
+    _recalculate_means_test(session)
+
+
+def _fill(form_type: str, session: IntakeSession) -> tuple[dict[str, str], bytes]:
+    """Resolve a form that applies to this filer and fill its template. _prepare() runs first."""
     if not FORM_REGISTRY[form_type].applies(session):
         raise NotInPacket()
     values = build_field_values(form_type, session)
@@ -151,7 +170,10 @@ def _store(generated_form: GeneratedForm, values: dict[str, str]) -> None:


 def _generate_and_persist(session: IntakeSession, form_type: str, user) -> GeneratedForm:
-    """Fill the form (which proves it fills) and keep its values as the snapshot."""
+    """Fill the form (which proves it fills) and keep its values as the snapshot.
+
+    _prepare() runs first.
+    """
     if GeneratedForm.objects.filter(session=session, form_type=form_type, status="filed").exists():
         raise FormIsFiled()
     values, _ = _fill(form_type, session)
@@ -213,10 +235,20 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
         The ordered form types that apply to this filer.

         GET /api/forms/packet/?session=1
+
+        For a completed intake the means test is worked out again first, and a refusal
+        covers the whole list. An unfinished intake gets the packet its stored data gives,
+        and is never refused (step 2 spec §5.3, §5.6).
         """
         session, err = _session_or_error(request, request.query_params.get("session"), "session")
         if err:
             return err
+        if session.status == "completed":
+            try:
+                _recalculate_means_test(session)
+            except Exception as exc:
+                body, code = _failure(None, exc)
+                return Response(body, status=code)
         return Response({"session": session.id, "form_types": packet(session)})

     # ------------------------------------------------------------------
@@ -241,6 +273,7 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
             return err

         try:
+            _prepare(session)
             generated_form = _generate_and_persist(session, form_type, request.user)
         except Exception as exc:
             body, code = _failure(form_type, exc)
@@ -265,24 +298,25 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
         { "session_id": 1 }

         Each form gets its own savepoint, so one form's failure can't undo the
-        others. Rows for forms that no longer apply are deleted. A filed form
-        that still applies is returned as it is: not resolved again, not un-filed.
-        An unfinished intake gets one refusal for the whole packet, before anything
+        others. Rows for forms that no longer apply are deleted. A filed form is
+        returned as it is, in the packet or out of it: not resolved again, not
+        un-filed, not deleted (DIG-155). An unfinished intake, or a means test that
+        can't be worked out, gets one refusal for the whole packet, before anything
         is deleted.
         """
         session, err = _session_or_error(request, request.data.get("session_id"))
         if err:
             return err
         try:
-            _check_finished(session)
-        except IntakeNotFinished:
-            return Response(
-                {"error": _FAILURE_SENTENCES[IntakeNotFinished]},
-                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
-            )
+            _prepare(session)
+        except Exception as exc:
+            body, code = _failure(None, exc)
+            return Response(body, status=code)

         form_types = packet(session)
-        GeneratedForm.objects.filter(session=session).exclude(form_type__in=form_types).delete()
+        GeneratedForm.objects.filter(session=session).exclude(form_type__in=form_types).exclude(
+            status="filed"
+        ).delete()
         filed = {
             f.form_type: f for f in GeneratedForm.objects.filter(session=session, status="filed")
         }
@@ -299,6 +333,13 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
                 results.append(self.get_serializer(generated_form).data)
             except Exception as exc:
                 errors.append(_failure(form_type, exc)[0])
+        # Filed forms that left the packet go last: the dashboard replaces its list with
+        # `generated`, so a form missing from it would vanish from the dashboard.
+        results += [
+            self.get_serializer(form).data
+            for form_type, form in filed.items()
+            if form_type not in form_types
+        ]

         return Response(
             {
@@ -322,6 +363,7 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):
         """
         generated_form = self.get_object()
         try:
+            _prepare(generated_form.session)
             generated_form = _generate_and_persist(
                 generated_form.session, generated_form.form_type, request.user
             )
@@ -379,7 +421,8 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):

         A form not yet filed is resolved fresh, so the filer always downloads
         their current answers, and its snapshot is refreshed. A filed form
-        fills from its snapshot, so it matches what was filed.
+        fills from its snapshot, so it matches what was filed, even after it
+        has left the packet (DIG-155).
         """
         generated_form = self.get_object()
         form_type = generated_form.form_type
@@ -387,10 +430,9 @@ class GeneratedFormViewSet(viewsets.ReadOnlyModelViewSet):

         try:
             if generated_form.status == "filed" and generated_form.field_values:
-                if not FORM_REGISTRY[form_type].applies(session):
-                    raise NotInPacket()
                 pdf_bytes = PDFFormFiller().fill(form_type, json.loads(generated_form.field_values))
             else:
+                _prepare(session)
                 values, pdf_bytes = _fill(form_type, session)
                 _store(generated_form, values)
         except Exception as exc:
PATCH
```

Every call that decides the packet now recalculates the means test from the stored intake after the completion check (§5.6, "Recalculated every time"), so a stale row no longer decides it (DIG-160). Generate All refuses before its delete, keeps filed forms, and returns the ones that left the packet. A filed form's download prints its snapshot without asking whether the form still applies (DIG-155).

- [ ] **Step 6: Show a filed form that left the packet on the dashboard**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/components/forms/FormCard.tsx b/frontend/src/components/forms/FormCard.tsx
index e6c27bb..0a46029 100644
--- a/frontend/src/components/forms/FormCard.tsx
+++ b/frontend/src/components/forms/FormCard.tsx
@@ -15,6 +15,8 @@ import { FORM_TYPE_METADATA } from '../../types/api';
 interface FormCardProps {
   formType: FormType;
   generatedForm?: GeneratedForm;
+  /** A filed form whose type is no longer in the filer's packet */
+  leftPacket?: boolean;
   onGenerate: (formType: FormType) => Promise<void>;
   onDownload: (formId: number) => Promise<void>;
   onMarkFiled: (formId: number) => Promise<void>;
@@ -23,6 +25,7 @@ interface FormCardProps {
 export function FormCard({
   formType,
   generatedForm,
+  leftPacket = false,
   onGenerate,
   onDownload,
   onMarkFiled,
@@ -49,6 +52,9 @@ export function FormCard({
         <div className="form-card-info">
           <h3 className="form-card-title">{metadata.label}</h3>
           <p className="form-card-description">{metadata.description}</p>
+          {leftPacket && (
+            <p className="form-card-description">Filed, no longer in your current packet</p>
+          )}
         </div>
         <FormStatusBadge status={status} />
       </div>
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
index 9986a06..733c758 100644
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -67,6 +67,10 @@ export function FormDashboard() {

   // Map form_type → GeneratedForm for quick lookup
   const formsByType = new Map(forms.map((f) => [f.form_type, f]));
+  // A filed form stays after it leaves the packet, with what was filed (forms step 2 §5.6)
+  const filedOutsidePacket = forms.filter(
+    (f) => f.status === 'filed' && !packet.includes(f.form_type)
+  );

   const handleGenerate = async (formType: FormType) => {
     if (!session) return;
@@ -221,6 +225,17 @@ export function FormDashboard() {
               onMarkFiled={handleMarkFiled}
             />
           ))}
+          {filedOutsidePacket.map((form) => (
+            <FormCard
+              key={form.form_type}
+              formType={form.form_type}
+              generatedForm={form}
+              leftPacket
+              onGenerate={handleGenerate}
+              onDownload={handleDownload}
+              onMarkFiled={handleMarkFiled}
+            />
+          ))}
         </div>
       )}

PATCH
```

- [ ] **Step 7: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/forms/tests/test_form_views.py apps/forms/tests/test_api_readback.py apps/intake/tests/test_completion.py apps/intake/tests/test_income_resume.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `94 passed`.

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx 2>&1 | tail -6
```

Expected: `11 passed`, with no test failed.

- [ ] **Step 8: Run every gate**

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

Expected: `1749 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  301 passed (301)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 9: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 10: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/conftest.py \
  backend/apps/forms/tests/test_api_readback.py \
  backend/apps/forms/tests/test_form_views.py \
  backend/apps/forms/views.py \
  backend/apps/intake/tests/test_completion.py \
  backend/apps/intake/tests/test_income_resume.py \
  frontend/src/components/forms/FormCard.tsx \
  frontend/src/pages/FormDashboard.tsx \
  frontend/src/pages/__tests__/FormDashboard.test.tsx
git commit -F - <<'MSG'
feat(forms,frontend): work the means test out before every packet, and keep filed forms

A MeansTest row was written only when the wizard called calculate_means_test, so a
filer who changed their income after that still got the packet the old result decided
(DIG-160). Every call that decides the packet now works the means test out again from
the stored intake, after the completion check (step 2 spec §5.6): Generate All,
Generate, Regenerate, the download of an unfiled form, and the packet list for a
completed intake. An unfinished intake still reads the packet its stored data gives
and is never refused.

When the means test can't be worked out, one refusal covers the whole call: income not
entered by source is a 422 with "Enter your income by source on the Income step.", and
missing district median data is a 500 logged by exception type only. Generate All and
the packet list answer {"error": ...} with no form named, as for an unfinished intake,
and Generate All refuses before it deletes anything.

A form marked filed is no longer deleted when it leaves the packet (DIG-155). Generate
All keeps it and returns it in `generated`, after the packet's forms, because the
dashboard replaces its list with that array. Its download fills from the stored
snapshot without the packet check. The dashboard shows it after the packet's cards as
"Filed, no longer in your current packet".

The read-back test no longer calls calculate_means_test: Generate All works the means
test out itself. The view tests' district is the real ILND fixture, and their completed
intakes carry income, since Complete requires it and every call now reads it.
MSG
git status --short
```

### Task 12: Show a refused Generate All or packet list, and reload the packet after Generate All

_Built and verified as commit `cfa7b8d` on `plan/forms-step2a`._

**Files:**

- Modify: `frontend/src/pages/FormDashboard.tsx`
- Modify: `frontend/src/pages/__tests__/FormDashboard.test.tsx`

**Interfaces:**

- Consumes:
  - Task 11's whole-call refusals. `POST /api/forms/generate_all/` and `GET /api/forms/packet/?session=<id>` refuse the whole call with an `{"error": ...}` body that names no form: a 422 with "Finish your intake before preparing your forms." (Generate All for an unfinished intake) or "Enter your income by source on the Income step." (income not entered by source), or a 500 with "This form couldn't be prepared. Please try again later.".
  - `APIClientError` from `frontend/src/api/client.ts`, with `statusCode` and `message`. `handleAPIError` fills `message` from `errorData.message || errorData.error`, so a whole-call body's `error` becomes the message. `apiFetch` sends a 5xx through `withRetry` (`frontend/src/utils/retry.ts`), which tries it three more times, 0.5 s, 1 s and 2 s apart.
  - `ERROR_GENERIC` from `frontend/src/constants/copy.ts`: "Something went wrong. Your information is safe — please try again in a moment."
  - `api.forms.generateAll(sessionId)`, `api.forms.packet(sessionId)` and `api.forms.listBySession(sessionId)`.
  - Task 3's unfinished-intake notice in `FormDashboard.tsx`, whose link is `<Link to="/intake" className="button button--primary">Finish your intake</Link>`.
- Produces:
  - In `frontend/src/pages/FormDashboard.tsx`, module-private:
    - `LOAD_ERROR = 'Unable to load your forms. Please try refreshing the page.'`, the sentence the load banner already showed;
    - `wholeCallRefusal(err: unknown, generic: string): string`, which returns `err.message` for an `APIClientError` whose `statusCode` is 422, and `generic` for anything else.
  - `loadForms` sets `error` to `wholeCallRefusal(err, LOAD_ERROR)`.
  - New state `generateAllRefusal: string | null`, shown in its own `<div className="form-dashboard-error" role="alert">` with no button, between the load banner and the per-form errors.
  - `handleGenerateAll` never throws. It clears `generateAllRefusal`, and on a failure sets it to `wholeCallRefusal(err, ERROR_GENERIC)`. Then, refused or not, it reloads `GET /forms/packet/` (`setPacket`, then `setError(null)`), and a failed reload sets `error` to `wholeCallRefusal(err, LOAD_ERROR)`.
  - The load banner shows Try Again only while its text is `LOAD_ERROR`. Any other text is a 422's sentence, and the banner shows the "Finish your intake" link to `/intake` instead.
  - Tests in `FormDashboard.test.tsx`, under `describe('when Generate All or the packet list is refused', { timeout: 15_000 })`: `shows the packet list’s refusal in its own words`, `offers the way back to the intake, not a retry, when the packet list is refused`, `shows generic words, never the server’s, when the packet list fails on the server`, `shows Generate All’s refusal in its own words`, `shows generic words, never the server’s, when Generate All fails on the server`, `reloads the packet after Generate All succeeds`, `reloads the packet after Generate All is refused`, `shows the packet list’s refusal when it reloads after Generate All`, `still offers a retry when the reload after Generate All fails on the server` and `clears a failed reload once a later reload after Generate All succeeds`. The apostrophes in the names are curly (’).

**Decisions already made in this task:**

- A 422 shows its own sentence, read from `err.message`. That works because `apiFetch` still prefers a body's `message` and falls back to `error` (the decision that Review shows the means test's own refusal leaves that preference alone), and a whole-call body carries only `error`. Anything else, a 500 included, shows generic words, never the 500's text, which speaks of one form.
- The generic words reuse sentences the app already has; this task writes no new copy.
  - Generate All's is `ERROR_GENERIC` from `frontend/src/constants/copy.ts`, "Something went wrong. Your information is safe — please try again in a moment." It is in the copy deck and its reading-level test, though no screen showed it before this task.
  - The packet list keeps the dashboard's own "Unable to load your forms. Please try refreshing the page.", moved into the constant `LOAD_ERROR` because it is now used in several places.
  - The two differ because "Unable to load your forms" is untrue for a generate, and keeping the packet list's sentence changes nothing a filer sees for its 500. Other words for either are the owner's call, not this task's.
- A load banner that shows a 422's sentence offers Task 3's "Finish your intake" link to `/intake` instead of Try Again: the same element, label and class as the unfinished-intake notice in the same file. The same 422 comes back on every reload, so Try Again would loop. Every intake-data write reopens a completed intake, so a filer who fixes their income must press Complete again, which is finishing the intake. `LOAD_ERROR` (a 500, a 400 or a network failure) keeps Try Again, because a retry can work.
- The banner tells the two apart with `error === LOAD_ERROR`, with no second state flag. That holds because `error` is set only through `wholeCallRefusal(err, LOAD_ERROR)`.
- Any 422 that reaches `loadForms` shows its own text, not only the packet list's. The forms list never answers 422: it filters `session` through a ModelChoiceFilter over the user's own sessions, which answers 400 for any other id. So the existing test `shows error message when form loading fails` now mocks a 400 where it mocked a 422; its body and assertions are unchanged.
- Generate All's refusal gets its own alert with no Try Again. The Generate All button is the retry, and `loadForms` clears `error` when it succeeds, which would wipe a refusal kept there.
- "Reloads the packet list" means `GET /forms/packet/` only (`setPacket`), never `loadForms`. `response.generated` already replaces the forms list after a success, a whole-call refusal comes before anything is deleted, and `loadForms` would flash "Loading your forms..." and clear the refusal. The reload runs after every Generate All, refused or not, and is awaited inside the handler, so the Generate All button stays in its loading state until the reload ends. A failed reload leaves the cards as they were; a successful one clears an earlier load failure.
- Single-form generate, download and mark-filed are unchanged (DIG-138).
- Accepted and left as they are:
  - when Generate All and its reload are refused with the same 422, the sentence shows in both alerts, since dropping the load banner would drop its link;
  - the Generate All alert has no link; the only path with no link anywhere needs a context that still says `completed` after an autosave reopened the session;
  - no test pins that a new Generate All clears an earlier refusal, or that a refused Generate All keeps the survey closed (the code does both);
  - a 500 that persists waits through the existing `withRetry` for both calls, about 7 s, with the Generate All button still loading.
- The 500 tests for Generate All and for the reload use the CLAUDE.md fake-timer pattern. The packet list's 500 at mount uses real timers, an 8 s `findByText` and the describe's 15 s timeout, because the mount's fetch schedules its backoff before a switch to fake timers could apply. The test that a later reload clears a failed one fails its first reload with a 422, which reaches the same line without the backoff.

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/FormDashboard.test.tsx b/frontend/src/pages/__tests__/FormDashboard.test.tsx
index 0e86d6c..d0a81d9 100644
--- a/frontend/src/pages/__tests__/FormDashboard.test.tsx
+++ b/frontend/src/pages/__tests__/FormDashboard.test.tsx
@@ -1,4 +1,4 @@
-import { render, screen, waitFor, within } from '@testing-library/react';
+import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
 import userEvent from '@testing-library/user-event';
 import { MemoryRouter } from 'react-router-dom';
 import { http, HttpResponse } from 'msw';
@@ -141,7 +141,7 @@ describe('FormDashboard', () => {
   it('shows error message when form loading fails', async () => {
     server.use(
       http.get('http://localhost:8000/api/forms/', () =>
-        HttpResponse.json({ message: 'Server error' }, { status: 422 })
+        HttpResponse.json({ message: 'Server error' }, { status: 400 })
       )
     );

@@ -248,4 +248,229 @@ describe('FormDashboard', () => {
     expect(failure).toHaveTextContent('Form 101 - Voluntary Petition: Missing debtor name');
     expect(failure).not.toHaveTextContent('form_101');
   });
+
+  // ---------------------------------------------------------------------------
+  // A refusal of the whole call (forms step 2 §5.6, DIG-156)
+  // ---------------------------------------------------------------------------
+
+  describe('when Generate All or the packet list is refused', { timeout: 15_000 }, () => {
+    const FINISH_INTAKE = 'Finish your intake before preparing your forms.';
+    const INCOME_NOT_SPLIT = 'Enter your income by source on the Income step.';
+    // The server's sentence for a 500 speaks of one form, so the dashboard never shows it
+    const SERVER_FAILURE = "This form couldn't be prepared. Please try again later.";
+    const GENERIC =
+      'Something went wrong. Your information is safe — please try again in a moment.';
+
+    /** Open Generate All and tick the UPL notice; returns the notice's Continue button. */
+    async function openGenerateAll() {
+      await userEvent.click(await screen.findByRole('button', { name: /generate all/i }));
+      await userEvent.click(screen.getByRole('checkbox'));
+      return screen.getByRole('button', { name: /continue/i });
+    }
+
+    /** A packet that gains Form 122A-2 once the means test is worked out again. */
+    function packetThatGains122a2() {
+      let calls = 0;
+      return http.get('http://localhost:8000/api/forms/packet/', () => {
+        calls += 1;
+        return HttpResponse.json({
+          session: 1,
+          form_types:
+            calls === 1 ? ['form_101', 'form_121'] : ['form_101', 'form_121', 'form_122a2'],
+        });
+      });
+    }
+
+    it('shows the packet list’s refusal in its own words', async () => {
+      server.use(
+        http.get('http://localhost:8000/api/forms/packet/', () =>
+          HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 })
+        )
+      );
+
+      renderFormDashboard();
+
+      expect(await screen.findByText(INCOME_NOT_SPLIT)).toBeInTheDocument();
+      expect(screen.queryByText(/unable to load your forms/i)).not.toBeInTheDocument();
+    });
+
+    it('offers the way back to the intake, not a retry, when the packet list is refused', async () => {
+      // A completed filer whose income isn't split gets the same refusal on every reload
+      server.use(
+        http.get('http://localhost:8000/api/forms/packet/', () =>
+          HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 })
+        )
+      );
+
+      renderFormDashboard();
+
+      await screen.findByText(INCOME_NOT_SPLIT);
+      expect(screen.getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
+        'href',
+        '/intake'
+      );
+      expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
+    });
+
+    it('shows generic words, never the server’s, when the packet list fails on the server', async () => {
+      server.use(
+        http.get('http://localhost:8000/api/forms/packet/', () =>
+          HttpResponse.json({ error: SERVER_FAILURE }, { status: 500 })
+        )
+      );
+
+      renderFormDashboard();
+
+      // A 500 is tried three more times, 3.5 s of backoff, before the dashboard gives up
+      expect(
+        await screen.findByText(/unable to load your forms/i, {}, { timeout: 8000 })
+      ).toBeInTheDocument();
+      expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
+    });
+
+    it('shows Generate All’s refusal in its own words', async () => {
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({ error: FINISH_INTAKE }, { status: 422 })
+        )
+      );
+
+      renderFormDashboard();
+      await userEvent.click(await openGenerateAll());
+
+      expect(await screen.findByText(FINISH_INTAKE)).toBeInTheDocument();
+      expect(screen.queryByText(GENERIC)).not.toBeInTheDocument();
+    });
+
+    it('shows generic words, never the server’s, when Generate All fails on the server', async () => {
+      server.use(
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({ error: SERVER_FAILURE }, { status: 500 })
+        )
+      );
+
+      renderFormDashboard();
+      const continueBtn = await openGenerateAll();
+
+      // A 500 is tried three more times (0.5 s, 1 s, 2 s apart) before the dashboard gives up
+      vi.useFakeTimers();
+      try {
+        fireEvent.click(continueBtn);
+        for (let second = 0; second < 5; second += 1) {
+          await act(async () => {
+            await vi.advanceTimersByTimeAsync(1000);
+          });
+        }
+      } finally {
+        vi.useRealTimers();
+      }
+
+      expect(await screen.findByText(GENERIC)).toBeInTheDocument();
+      expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
+    });
+
+    it('reloads the packet after Generate All succeeds', async () => {
+      server.use(packetThatGains122a2());
+
+      renderFormDashboard();
+      const continueBtn = await openGenerateAll();
+      expect(screen.queryByText('Form 122A-2 - Means Test Expenses')).not.toBeInTheDocument();
+      await userEvent.click(continueBtn);
+
+      expect(await screen.findByText('Form 122A-2 - Means Test Expenses')).toBeInTheDocument();
+    });
+
+    it('reloads the packet after Generate All is refused', async () => {
+      server.use(
+        packetThatGains122a2(),
+        http.post('http://localhost:8000/api/forms/generate_all/', () =>
+          HttpResponse.json({ error: FINISH_INTAKE }, { status: 422 })
+        )
+      );
+
+      renderFormDashboard();
+      const continueBtn = await openGenerateAll();
+      expect(screen.queryByText('Form 122A-2 - Means Test Expenses')).not.toBeInTheDocument();
+      await userEvent.click(continueBtn);
+
+      expect(await screen.findByText('Form 122A-2 - Means Test Expenses')).toBeInTheDocument();
+      expect(screen.getByText(FINISH_INTAKE)).toBeInTheDocument();
+    });
+
+    it('shows the packet list’s refusal when it reloads after Generate All', async () => {
+      let calls = 0;
+      server.use(
+        http.get('http://localhost:8000/api/forms/packet/', () => {
+          calls += 1;
+          return calls === 1
+            ? HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
+            : HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 });
+        })
+      );
+
+      renderFormDashboard();
+      await userEvent.click(await openGenerateAll());
+
+      expect(await screen.findByText(INCOME_NOT_SPLIT)).toBeInTheDocument();
+      expect(screen.getByRole('link', { name: 'Finish your intake' })).toHaveAttribute(
+        'href',
+        '/intake'
+      );
+      expect(screen.queryByRole('button', { name: /try again/i })).not.toBeInTheDocument();
+    });
+
+    it('still offers a retry when the reload after Generate All fails on the server', async () => {
+      let calls = 0;
+      server.use(
+        http.get('http://localhost:8000/api/forms/packet/', () => {
+          calls += 1;
+          return calls === 1
+            ? HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] })
+            : HttpResponse.json({ error: SERVER_FAILURE }, { status: 500 });
+        })
+      );
+
+      renderFormDashboard();
+      const continueBtn = await openGenerateAll();
+
+      // The reload's 500 is tried three more times (0.5 s, 1 s, 2 s apart) before it gives up
+      vi.useFakeTimers();
+      try {
+        fireEvent.click(continueBtn);
+        for (let second = 0; second < 5; second += 1) {
+          await act(async () => {
+            await vi.advanceTimersByTimeAsync(1000);
+          });
+        }
+      } finally {
+        vi.useRealTimers();
+      }
+
+      expect(await screen.findByText(/unable to load your forms/i)).toBeInTheDocument();
+      expect(screen.queryByText(SERVER_FAILURE)).not.toBeInTheDocument();
+      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
+    });
+
+    it('clears a failed reload once a later reload after Generate All succeeds', async () => {
+      let calls = 0;
+      server.use(
+        http.get('http://localhost:8000/api/forms/packet/', () => {
+          calls += 1;
+          return calls === 2
+            ? HttpResponse.json({ error: INCOME_NOT_SPLIT }, { status: 422 })
+            : HttpResponse.json({ session: 1, form_types: ['form_101', 'form_121'] });
+        })
+      );
+
+      renderFormDashboard();
+      await userEvent.click(await openGenerateAll());
+      await screen.findByText(INCOME_NOT_SPLIT);
+
+      await userEvent.click(await openGenerateAll());
+
+      await waitFor(() => expect(calls).toBe(3));
+      await waitFor(() => expect(screen.queryByText(INCOME_NOT_SPLIT)).not.toBeInTheDocument());
+      expect(screen.getByText('Form 121 - SSN Statement')).toBeInTheDocument();
+    });
+  });
 });
PATCH
```

The new tests answer the packet list and Generate All through MSW with Task 11's bodies: a 422 with each sentence, and a 500 with the server's per-form sentence, which must never show. `packetThatGains122a2()` answers the first packet call with Forms 101 and 121 and every later call with 122A-2 added, so a card for 122A-2 appears only if the dashboard reloads the packet. `openGenerateAll()` opens Generate All's UPL notice, ticks its checkbox and returns its Continue button. The patch also moves the existing test `shows error message when form loading fails` from a 422 to a 400, as the decisions above explain.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx 2>&1 | grep -E '×|Unable to find|Tests '
```

Expected: FAIL — `9 failed` and `12 passed`. Each failing test times out waiting for text the old dashboard never shows, such as `Unable to find an element with the text: Form 122A-2 - Means Test Expenses` and `Unable to find an element with the text: Enter your income by source on the Income step.`: the old dashboard shows nothing when Generate All is refused, shows its own fixed sentence for every load failure, a 422 included, and never reloads the packet. The one new test that passes is the packet list's 500 test, which guards the sentence the dashboard already shows for a 500; the existing load-failure test passes on its 400 as well.

- [ ] **Step 3: Show a whole-call refusal in its own words, and reload the packet after Generate All**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/FormDashboard.tsx b/frontend/src/pages/FormDashboard.tsx
index 733c758..0b59baf 100644
--- a/frontend/src/pages/FormDashboard.tsx
+++ b/frontend/src/pages/FormDashboard.tsx
@@ -9,11 +9,12 @@
 import { useState, useEffect, useCallback } from 'react';
 import { Link } from 'react-router-dom';
 import { useIntake } from '../context/IntakeContext';
-import { api } from '../api/client';
+import { api, APIClientError } from '../api/client';
 import { FormCard, GenerateAllButton, DebtExplanationsPanel } from '../components/forms';
 import type { DebtClassification } from '../components/forms/DebtExplanationsPanel';
 import { UPLDisclaimer } from '../components/compliance';
 import { UPL_FORM_DISCLAIMER } from '../constants/upl';
+import { ERROR_GENERIC } from '../constants/copy';
 import { Button } from '../components/common';
 import { PostTaskSurvey } from '../components/survey/PostTaskSurvey';
 import type { GeneratedForm, FormType, GenerateAllFormsResponse } from '../types/api';
@@ -22,6 +23,17 @@ import { trackEvent } from '../utils/analytics';

 type GenerateAllError = GenerateAllFormsResponse['errors'][number];

+const LOAD_ERROR = 'Unable to load your forms. Please try refreshing the page.';
+
+/**
+ * What the filer reads when Generate All or the packet list is refused as a whole
+ * (forms step 2 §5.6): a 422 says in plain words what to fix; anything else gets the
+ * generic words, since a 500's text is for operations.
+ */
+function wholeCallRefusal(err: unknown, generic: string): string {
+  return err instanceof APIClientError && err.statusCode === 422 ? err.message : generic;
+}
+
 export function FormDashboard() {
   const { session, isLoading: sessionLoading } = useIntake();
   const [forms, setForms] = useState<GeneratedForm[]>([]);
@@ -31,6 +43,7 @@ export function FormDashboard() {
   const [error, setError] = useState<string | null>(null);
   const [showSurvey, setShowSurvey] = useState(false);
   const [generationErrors, setGenerationErrors] = useState<GenerateAllError[]>([]);
+  const [generateAllRefusal, setGenerateAllRefusal] = useState<string | null>(null);
   const [dischargeData, setDischargeData] = useState<DebtClassification[]>([]);

   // Load existing forms on mount
@@ -46,8 +59,8 @@ export function FormDashboard() {
       setForms(loadedForms);
       setPacket(packetTypes);
       setError(null);
-    } catch {
-      setError('Unable to load your forms. Please try refreshing the page.');
+    } catch (err) {
+      setError(wholeCallRefusal(err, LOAD_ERROR));
     } finally {
       setIsLoading(false);
     }
@@ -82,11 +95,23 @@ export function FormDashboard() {
   const handleGenerateAll = async () => {
     if (!session) return;
     setGenerationErrors([]);
-    const response = await api.forms.generateAll(session.id);
-    setForms(response.generated);
-    setGenerationErrors(response.errors);
-    trackEvent('form_generated', { form_type: 'all', session_id: session.id });
-    setShowSurvey(true);
+    setGenerateAllRefusal(null);
+    try {
+      const response = await api.forms.generateAll(session.id);
+      setForms(response.generated);
+      setGenerationErrors(response.errors);
+      trackEvent('form_generated', { form_type: 'all', session_id: session.id });
+      setShowSurvey(true);
+    } catch (err) {
+      setGenerateAllRefusal(wholeCallRefusal(err, ERROR_GENERIC));
+    }
+    // Generate All works the means test out again, so the packet may have changed
+    try {
+      setPacket(await api.forms.packet(session.id));
+      setError(null);
+    } catch (err) {
+      setError(wholeCallRefusal(err, LOAD_ERROR));
+    }
   };

   const handleDownload = async (formId: number) => {
@@ -152,9 +177,23 @@ export function FormDashboard() {
       {error && (
         <div className="form-dashboard-error" role="alert">
           <p>{error}</p>
-          <Button variant="outline" size="sm" onClick={loadForms}>
-            Try Again
-          </Button>
+          {/* Our own words mean the load failed and may work again; a 422's words name
+              something to fix at the intake, which a retry can't */}
+          {error === LOAD_ERROR ? (
+            <Button variant="outline" size="sm" onClick={loadForms}>
+              Try Again
+            </Button>
+          ) : (
+            <Link to="/intake" className="button button--primary">
+              Finish your intake
+            </Link>
+          )}
+        </div>
+      )}
+
+      {generateAllRefusal && (
+        <div className="form-dashboard-error" role="alert">
+          <p>{generateAllRefusal}</p>
         </div>
       )}

PATCH
```

DIG-156 (§5.6): when Generate All or the packet list is refused as a whole, the filer now reads the 422's plain words, or generic words for a 500, and a refused packet list points back to the intake. Generate All works the means test out again, so the packet it decides can differ from the one on screen; the dashboard reloads it after every Generate All.

- [ ] **Step 4: Run the tests again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FormDashboard.test.tsx 2>&1 | grep -E '×|Unable to find|Tests '
```

Expected: `21 passed`.

- [ ] **Step 5: Run every gate**

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

Expected: `1749 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  311 passed (311)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 6: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 7: Commit**

```bash
set -eo pipefail
git add \
  frontend/src/pages/FormDashboard.tsx \
  frontend/src/pages/__tests__/FormDashboard.test.tsx
git commit -F - <<'MSG'
fix(frontend): show a refused Generate All or packet list, and reload the packet after Generate All

When Generate All or the packet list was refused as a whole, the dashboard showed
nothing for Generate All and a fixed "Unable to load your forms" for the packet list,
so a filer never learned that their intake was unfinished or their income wasn't
entered by source (DIG-156). The dashboard now shows a 422's own sentence. A 500 gets
generic words instead of the server's text, which speaks of one form: Generate All
uses the copy deck's ERROR_GENERIC, and the packet list keeps "Unable to load your
forms. Please try refreshing the page." (step 2 spec §5.6).

A refused packet list returns the same 422 on every reload, so its banner offers the
"Finish your intake" link back to the intake instead of Try Again; a load that failed
on the server keeps Try Again.

Generate All works the means test out again, so the packet it decides can differ from
the one on screen. After every Generate All, refused or not, the dashboard reloads the
packet list, and a reload that succeeds clears an earlier load failure. Refusals of a
single form's generate or download stay as they are until DIG-138.

The existing load-failure test sent a 422 from the forms list, which never answers
422; it now sends a 400, DRF's answer for an unknown session filter.
MSG
git status --short
```

### Task 13: Ask the fee waiver's take-home pay and non-cash help, and keep its answers

_Built and verified as commit `d35a61f` on `plan/forms-step2a`._

**Files:**

- Create: `backend/apps/intake/migrations/0015_feewaiverapplication_take_home_and_noncash.py`
- Modify: `backend/apps/forms/tests/test_api_readback.py`
- Modify: `backend/apps/intake/management/commands/seed_demo_data.py`
- Modify: `backend/apps/intake/models.py`
- Modify: `backend/apps/intake/serializers.py`
- Modify: `backend/apps/intake/tests/test_completion.py`
- Modify: `backend/apps/intake/tests/test_data_migrations.py`
- Modify: `backend/apps/intake/tests/test_fee_waiver_views.py`
- Modify: `backend/apps/intake/views.py`
- Modify: `frontend/e2e/fixtures/personas.ts`
- Modify: `frontend/e2e/journeys/deshawn-assets.spec.ts`
- Modify: `frontend/e2e/journeys/maria-happy-path.spec.ts`
- Modify: `frontend/e2e/journeys/sarah-simplest.spec.ts`
- Modify: `frontend/e2e/pages/fee-waiver.page.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/FeeWaiverPage.tsx`
- Modify: `frontend/src/pages/__tests__/FeeWaiverPage.test.tsx`
- Modify: `frontend/src/styles/global.css`
- Modify: `frontend/src/test/mocks/handlers.ts`

**Interfaces:**

- Consumes:
  - `_assert_session_owned(session, user)` in `apps/intake/views.py`, which `AssetViewSet` and `DebtViewSet` call from `perform_update`. It raises `PermissionDenied("You do not have access to this session.")`, a 403.
  - DRF's global `DjangoFilterBackend` and `PageNumberPagination` (`PAGE_SIZE` 25) from `config/settings/base.py`, so a list endpoint answers `{count, next, previous, results}`.
  - The intake app's latest migration, Task 9's `0014_split_income_saved_as_zero`, and Task 5's helpers in `apps/intake/tests/test_data_migrations.py`: the `migrate` fixture, `_session(apps)` and the `INCOME_SPLIT` target.
  - Task 8's read-back in `apps/forms/tests/test_api_readback.py`: `_fee_waiver_application(data)`, `WAIVER_FILERS` and `test_forms_built_through_the_api_print_what_the_seeded_forms_print`.
  - Task 2's rule that a fee-waiver write never reopens a completed intake, pinned by `test_form_answers_sofa_and_fee_waiver_leave_a_completed_intake_complete` in `apps/intake/tests/test_completion.py`.
  - Task 7's fee-waiver page, whose submit and off-ramp both go to `/sofa`, and its page object's `submit`, which waits for `**/sofa`.
  - `packet(session)` in `apps/forms/registry.py`: Form 103B is in the packet only when the session has a `FeeWaiverApplication`.
  - `api.feeWaiver.create(data: FeeWaiverPayload)` in `frontend/src/api/client.ts` (`feeWaiverAPI`).
- Produces:
  - `FeeWaiverApplication.monthly_take_home_pay`, an `EncryptedDecimalField(max_digits=10, decimal_places=2, null=True, blank=True)`, and `FeeWaiverApplication.receives_noncash_assistance`, a `BooleanField(null=True)`. Neither has a default. `monthly_income` and `monthly_expenses` become `null=True, blank=True`, and `receives_public_benefits` keeps `default=False`. `benefit_types` (a JSON list) holds the "What kind?" answer.
  - Migration `intake.0015_feewaiverapplication_take_home_and_noncash`: two `AddField` and two `AlterField`, with no data step. The target `FEE_WAIVER_QUESTIONS` in `test_data_migrations.py` names it.
  - `FeeWaiverApplicationSerializer.Meta.fields`: `id`, `session`, `household_size`, `monthly_take_home_pay`, `receives_noncash_assistance`, `benefit_types`, `cannot_pay_full`, `cannot_pay_installments`, `status`, `created_at`, `updated_at`.
    - `monthly_take_home_pay` is a required `DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"))`.
    - `receives_noncash_assistance` is a required `BooleanField()`.
    - `benefit_types` is a `ListField(child=CharField(max_length=255), required=False)`.
    - `validate(attrs)` stores `[]` for a No and refuses a Yes with no kind: a 400 keyed on `benefit_types` with "This field is required.". On a PATCH, the answer or the kinds left out of the body come from the stored row.
  - `GET /api/intake/fee-waiver/?session=<id>` (`filterset_fields = ["session"]`, ordered by `id`) returns the user's application for that session as `{count, next, previous, results}` and never creates one. Another user's session reads as an empty list, and a session id that doesn't exist is a 400.
  - `FeeWaiverViewSet.perform_update` refuses a PATCH whose `session` belongs to another user with a 403 (DIG-178).
  - `seed_demo_data`: the persona dicts of Maria, DeShawn and Sarah gain a `fee_waiver` key (`monthly_take_home_pay`, `receives_noncash_assistance`, `benefit_types`), which `_create_persona` passes to `FeeWaiverApplication.objects.create`. Task 14's persona briefs quote these figures.
  - `frontend/src/api/client.ts`:
    - `FeeWaiverPayload` sends `monthly_take_home_pay: string`, `receives_noncash_assistance: boolean` and `benefit_types: string[]`.
    - `FeeWaiverApplication` reads `monthly_take_home_pay: string | null` and `receives_noncash_assistance: boolean | null`.
    - `feeWaiverAPI.getBySession(sessionId: number): Promise<FeeWaiverApplication | null>`, called as `api.feeWaiver.getBySession`.
  - `FeeWaiverPage` labels: "Household Size", "Your average monthly take-home pay (after taxes and payroll deductions)", a `<fieldset>` whose `<legend>` is "Do you receive non-cash help from the government, such as SNAP (food stamps) or a housing subsidy?" with the radios "Yes" and "No", and "What kind?" under Yes. The form renders only once the read has settled. A failed read shows a "Try again" button.
  - The CSS class `.fee-waiver-question` in `frontend/src/styles/global.css`.
  - MSW's default `GET /intake/fee-waiver/` handler in `frontend/src/test/mocks/handlers.ts`, which answers `{count: 0, next: null, previous: null, results: []}`.
  - E2E: `PersonaFeeWaiver` (`take_home_pay: number`, `noncash_assistance: string | null`) and `WaiverPersonaData extends PersonaData` in `frontend/e2e/fixtures/personas.ts`, the type of MARIA, DESHAWN and SARAH. `FeeWaiverPage.submit(householdSize: number, takeHomePay: number, noncashAssistance: string | null)` in `frontend/e2e/pages/fee-waiver.page.ts`, where null answers No.
  - Backend tests in `test_fee_waiver_views.py`: `test_the_page_answers_take_home_pay_and_non_cash_help_and_they_are_kept`, `test_an_application_needs_take_home_pay_and_an_answer_about_non_cash_help`, `test_a_yes_to_non_cash_help_needs_what_kind`, `test_what_kind_is_kept_up_to_a_line_of_text`, `test_a_no_to_non_cash_help_keeps_no_kind`, `test_changing_the_answer_to_yes_later_still_needs_what_kind`, `test_a_change_that_sends_one_answer_is_checked_against_the_other_one_stored`, `test_changing_the_answer_to_no_later_drops_the_kind`, `test_take_home_pay_must_be_zero_or_more_and_fit_its_column`, `test_take_home_pay_of_zero_or_the_column_maximum_is_kept`, `test_take_home_pay_is_encrypted_at_rest`, `test_the_old_income_expense_and_benefit_answers_are_no_longer_written`, `test_the_page_reads_only_the_application_of_the_session_it_shows`, `test_reading_another_users_session_returns_nothing`, `test_reading_by_session_never_starts_an_application`, `test_a_filer_cannot_move_their_application_onto_another_users_session` and `test_a_filer_can_still_change_their_own_application`. In `test_data_migrations.py`: `test_saved_fee_waiver_applications_leave_the_new_questions_unanswered`.
  - Vitest tests in `FeeWaiverPage.test.tsx`: `fills in the household size from the intake, but never take-home pay, and no longer asks for expenses`, `opens with the answers this session already sent, which win over the intake figures`, `shows a saved No as No`, `shows neither answer for an application saved before the question was asked`, `holds the form until the saved answers are read, so nothing typed is overwritten`, `asks about non-cash help with neither answer picked, and only Yes asks what kind`, `sends take-home pay and the non-cash answer under the names the server keeps`, `sends a Yes with what kind`, `will not send the application until every question is answered` and `shows no form when the saved answers cannot be read, and reads them again on Try again`.

**Decisions already made in this task:**

- Restated from the plan's cross-cutting decisions:
  - A fee-waiver write never reopens a completed intake.
  - A PATCH can't move an application onto another user's session (owner, DIG-178).
  - Creating an application through the JSON API requires both new answers.
- The new filer-facing words are §5.7's, word for word: the take-home label "Your average monthly take-home pay (after taxes and payroll deductions)", the question "Do you receive non-cash help from the government, such as SNAP (food stamps) or a housing subsidy?" with its Yes and No, and "What kind?". Don't reword them.
- The DIG-178 refusal is `_assert_session_owned` in `perform_update`, a 403, as in `AssetViewSet` and `DebtViewSet`. The serializer's `session` field keeps `IntakeSession.objects.all()`. Narrowing that queryset would turn the existing `test_cross_user_post_is_forbidden` (a 403) into a 400. `perform_create` keeps its own ownership check, unchanged.
- The create-time requirement is stricter than §5.7's page-level "An answer is required". It keeps a misnamed key from being dropped silently (the DIG-120 class), and a PATCH may still send either answer alone. A form-encoded create that leaves out the answer still stores No, because DRF reads an absent HTML checkbox as False. No client sends form data, and 2b closes it before it binds 103B line 3.
- A No stores `benefit_types = []`, even when kinds are sent, and so does a PATCH that switches to No. A Yes with no kind, or only blank kinds, is a 400 with DRF's own "This field is required.". The page never shows that text, so no new sentence is written.
- "What kind?" is one text box. The page sends `[text.trim()]` and shows a saved list joined with ", ". Each kind is capped at 255 characters by the server and by `maxLength` on the page, as Task 7 ruled for the SOFA text boxes.
- The read is `filterset_fields = ["session"]` on the existing paginated list, not a new action or a nested field on the session. `.order_by("id")` comes with it, because the list now has a reader. An unknown session id answers 400, which the page treats as a failed read that Try again can't mend; only a session deleted on the server leads there. Another user's existing id answers 200 with an empty list, so a filer can tell whether an id exists. Ids hold no filer data, so this is accepted.
- A failed read hides the form, because an empty form sent over the saved answers would reset the "cannot pay" boxes, which is DIG-157 itself. The page shows IntakeWizard's existing sentence word for word, "We couldn't get your latest information just now. Please try again in a moment.", with IntakeWizard's "Try again" button, which reads again. This is existing copy in a new place, and its wording is left to the owner.
- While the read is pending, the page shows only its heading and intro, with no loading text, so no new sentence is written. With no session in context, the form never shows; before this task it showed a form whose submit did nothing.
- The "I receive SSI, SNAP, TANF, or other means-tested public benefits" checkbox is removed. It wrote only `receives_public_benefits`, which is no longer written, and the non-cash question asks 103B line 3 in its place. That column keeps `default=False`, so it is already optional, and only the dead `qualifies_for_waiver()` reads it (DIG-145).
- Missing household size, take-home pay or answer, and a Yes with a blank kind, all show the page's existing "Please fill in all required fields.". The page checks only that take-home pay is present. A negative figure gets the server's 400 and the page's existing "Unable to submit your fee waiver application. Please try again." That is accepted here; the class is codebase-wide.
- A PATCH that sends only `benefit_types` to a legacy row with no answer stores a kind with no answer. No screen PATCHes, so it is accepted.
- The seeds stop writing the old columns, because the API can't write them any more and the read-back compares the two. Until 2b, every 103B prints 0.00 in its "4 type" and "5 Type" boxes, whose rules read the now-empty old columns; before, they printed the wrong-box income and expense figures. Both are listed tier 2 wrong-box defects (DIG-78), so their xfails stay, and no known-defect entry changes.
- No 2a form prints the new answers, so the read-back compares the API-built and seed-built applications field by field, beside `field_values`.
- Migration 0015 has no undo test. It is a schema migration, and §7.8's "reversing is a no-op" covers data migrations. Reversing it to NOT NULL would fail on any row saved after this task.
- The E2E figures live on a new `WaiverPersonaData` type, so the journeys read `MARIA.fee_waiver.*` without non-null assertions. James and Priya stay `PersonaData`.
- The spec numbers Maria's removed pre-fill check as `maria-happy-path.spec.ts:78-81` and the `totalExpenses` argument as line 85, counted at 49f287e. In the tree Task 12 leaves, they are lines 80-83 and line 87.

- [ ] **Step 1: Write the backend tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_api_readback.py b/backend/apps/forms/tests/test_api_readback.py
index 07c2142..3591931 100644
--- a/backend/apps/forms/tests/test_api_readback.py
+++ b/backend/apps/forms/tests/test_api_readback.py
@@ -56,15 +56,27 @@ def _fee_waiver_application(data):
     """The application the seed stores, as the fee-waiver page sends it."""
     return {
         "household_size": data["debtor"]["household_size"],
-        "monthly_income": data["income"]["monthly_gross_wages"],
-        "monthly_expenses": sum(data["expenses"].values()),
-        "receives_public_benefits": False,
-        "benefit_types": [],
+        **data["fee_waiver"],
         "cannot_pay_full": True,
         "cannot_pay_installments": True,
     }


+def _fee_waiver_answers(session):
+    """What the session's fee-waiver application holds, or None without one."""
+    fw = getattr(session, "fee_waiver", None)
+    if fw is None:
+        return None
+    return {
+        "household_size": fw.household_size,
+        "monthly_take_home_pay": fw.monthly_take_home_pay,
+        "receives_noncash_assistance": fw.receives_noncash_assistance,
+        "benefit_types": fw.benefit_types,
+        "cannot_pay_full": fw.cannot_pay_full,
+        "cannot_pay_installments": fw.cannot_pay_installments,
+    }
+
+
 def _send_through_the_api(persona):
     """Enter the persona as a filer would, then Generate All. Returns (session id, form types)."""
     data = PERSONAS[persona]()
@@ -162,6 +174,11 @@ def test_forms_built_through_the_api_print_what_the_seeded_forms_print(persona):
         form_type: _comparable(form_type, build_field_values(form_type, seeded))
         for form_type in packet(seeded)
     }
+    # No form prints take-home pay or the non-cash answer until 2b binds them on Form 103B,
+    # so the stored applications are compared directly.
+    built = IntakeSession.objects.get(pk=session_id)
+    assert _fee_waiver_answers(built) == _fee_waiver_answers(seeded)
+    assert (_fee_waiver_answers(built) is None) == (persona not in WAIVER_FILERS)
     # Only Priya's income is above the median, so only her packet holds 122A-2, and it
     # prints figures worked out from her own expenses.
     assert ("form_122a2" in stored) == (persona == "priya")
diff --git a/backend/apps/intake/tests/test_completion.py b/backend/apps/intake/tests/test_completion.py
index 1ee344f..0e20e2b 100644
--- a/backend/apps/intake/tests/test_completion.py
+++ b/backend/apps/intake/tests/test_completion.py
@@ -348,9 +348,8 @@ def test_form_answers_sofa_and_fee_waiver_leave_a_completed_intake_complete(file
         {
             "session": completed.pk,
             "household_size": 1,
-            "monthly_income": "1800.00",
-            "monthly_expenses": "1600.00",
-            "receives_public_benefits": False,
+            "monthly_take_home_pay": "1600.00",
+            "receives_noncash_assistance": False,
             "benefit_types": [],
             "cannot_pay_full": True,
             "cannot_pay_installments": True,
diff --git a/backend/apps/intake/tests/test_data_migrations.py b/backend/apps/intake/tests/test_data_migrations.py
index 44ad193..2c194e5 100644
--- a/backend/apps/intake/tests/test_data_migrations.py
+++ b/backend/apps/intake/tests/test_data_migrations.py
@@ -18,6 +18,7 @@ BEFORE_BACKFILL = [("intake", "0011_assetinfo_personal_property")]
 BACKFILL = [("intake", "0012_backfill_secured_debts")]
 INCOME_COLUMNS = [("intake", "0013_incomeinfo_income_by_source")]
 INCOME_SPLIT = [("intake", "0014_split_income_saved_as_zero")]
+FEE_WAIVER_QUESTIONS = [("intake", "0015_feewaiverapplication_take_home_and_noncash")]
 INCOME_SOURCES = [
     "monthly_gross_wages",
     "monthly_overtime",
@@ -193,3 +194,31 @@ def test_undoing_the_income_split_leaves_income_as_it_is(migrate):
     apps = migrate(INCOME_COLUMNS)

     assert _stored_income(apps) == AFTER_THE_SPLIT
+
+
+def test_saved_fee_waiver_applications_leave_the_new_questions_unanswered(migrate):
+    # A stored False would print a sworn "No" on Form 103B line 3, and a stored amount a
+    # take-home figure nobody gave, so rows saved before the questions existed stay empty.
+    apps = migrate(INCOME_SPLIT)
+    FeeWaiverApplication = apps.get_model("intake", "FeeWaiverApplication")
+    FeeWaiverApplication.objects.create(
+        session_id=_session(apps).pk,
+        household_size=3,
+        monthly_income=Decimal("3200.00"),
+        monthly_expenses=Decimal("2560.00"),
+        receives_public_benefits=True,
+    )
+
+    apps = migrate(FEE_WAIVER_QUESTIONS)
+
+    FeeWaiverApplication = apps.get_model("intake", "FeeWaiverApplication")
+    fw = FeeWaiverApplication.objects.get()
+    assert fw.monthly_take_home_pay is None
+    assert fw.receives_noncash_assistance is None
+    assert fw.benefit_types == []
+    assert (fw.household_size, fw.monthly_income, fw.monthly_expenses) == (
+        3,
+        Decimal("3200.00"),
+        Decimal("2560.00"),
+    )
+    assert fw.receives_public_benefits is True
diff --git a/backend/apps/intake/tests/test_fee_waiver_views.py b/backend/apps/intake/tests/test_fee_waiver_views.py
index 70eb366..1d38002 100644
--- a/backend/apps/intake/tests/test_fee_waiver_views.py
+++ b/backend/apps/intake/tests/test_fee_waiver_views.py
@@ -1,9 +1,11 @@
 from decimal import Decimal

 import pytest
+from django.db import connection
 from rest_framework.test import APIClient

 from apps.districts.models import District
+from apps.forms.registry import packet
 from apps.intake.models import FeeWaiverApplication, IntakeSession
 from apps.users.models import User

@@ -24,19 +26,24 @@ def setup(db):
     return client, session, user


-def test_create_fee_waiver(setup):
-    """POST /intake/fee-waiver/ creates a FeeWaiverApplication linked to user's session."""
-    client, session, _ = setup
-    payload = {
+def _application(session, **answers):
+    """What the fee-waiver page sends (step 2 spec §5.7)."""
+    return {
         "session": session.id,
-        "household_size": 2,
-        "monthly_income": "1800.00",
-        "monthly_expenses": "1600.00",
-        "receives_public_benefits": False,
+        "household_size": 1,
+        "monthly_take_home_pay": "1750.00",
+        "receives_noncash_assistance": False,
         "benefit_types": [],
         "cannot_pay_full": True,
         "cannot_pay_installments": True,
+        **answers,
     }
+
+
+def test_create_fee_waiver(setup):
+    """POST /intake/fee-waiver/ creates a FeeWaiverApplication linked to user's session."""
+    client, session, _ = setup
+    payload = _application(session, household_size=2)
     resp = client.post("/api/intake/fee-waiver/", payload, format="json")
     assert resp.status_code == 201
     data = resp.json()
@@ -107,16 +114,7 @@ def test_cross_user_post_is_forbidden(db):
     session = IntakeSession.objects.create(user=owner, district=district)
     client = APIClient()
     client.force_authenticate(user=attacker)
-    payload = {
-        "session": session.id,
-        "household_size": 99,
-        "monthly_income": "100.00",
-        "monthly_expenses": "100.00",
-        "receives_public_benefits": False,
-        "benefit_types": [],
-        "cannot_pay_full": True,
-        "cannot_pay_installments": True,
-    }
+    payload = _application(session, household_size=99, monthly_take_home_pay="100.00")
     resp = client.post("/api/intake/fee-waiver/", payload, format="json")
     assert resp.status_code == 403
     assert not FeeWaiverApplication.objects.filter(session=session).exists()
@@ -125,19 +123,319 @@ def test_cross_user_post_is_forbidden(db):
 def test_create_fee_waiver_is_idempotent(setup):
     """Second POST to /intake/fee-waiver/ for same session updates, not duplicates."""
     client, session, _ = setup
-    payload = {
-        "session": session.id,
-        "household_size": 1,
-        "monthly_income": "1000.00",
-        "monthly_expenses": "800.00",
-        "receives_public_benefits": False,
-        "benefit_types": [],
-        "cannot_pay_full": True,
-        "cannot_pay_installments": True,
-    }
+    payload = _application(session, monthly_take_home_pay="1000.00")
     client.post("/api/intake/fee-waiver/", payload, format="json")
     updated_payload = {**payload, "household_size": 3}
     resp = client.post("/api/intake/fee-waiver/", updated_payload, format="json")
     assert resp.status_code == 201
     assert FeeWaiverApplication.objects.filter(session=session).count() == 1
     assert FeeWaiverApplication.objects.get(session=session).household_size == 3
+
+
+# ── The page's questions (step 2 spec §5.7) ───────────────────────────
+#
+# Form 103B line 2 asks for take-home pay and line 3 asks whether the filer gets non-cash help
+# from the government, and if so what kind. The filer signs it under penalty of perjury, so
+# the server keeps exactly the answers given: a Yes says what kind, a No says none.
+
+
+def test_the_page_answers_take_home_pay_and_non_cash_help_and_they_are_kept(setup):
+    client, session, _ = setup
+    resp = client.post(
+        "/api/intake/fee-waiver/",
+        _application(
+            session,
+            monthly_take_home_pay="2800.00",
+            receives_noncash_assistance=True,
+            benefit_types=["SNAP (food stamps)"],
+        ),
+        format="json",
+    )
+
+    assert resp.status_code == 201
+    fw = FeeWaiverApplication.objects.get(session=session)
+    assert (fw.monthly_take_home_pay, fw.receives_noncash_assistance, fw.benefit_types) == (
+        Decimal("2800.00"),
+        True,
+        ["SNAP (food stamps)"],
+    )
+    body = resp.json()
+    assert (
+        body["monthly_take_home_pay"],
+        body["receives_noncash_assistance"],
+        body["benefit_types"],
+    ) == ("2800.00", True, ["SNAP (food stamps)"])
+
+
+def test_an_application_needs_take_home_pay_and_an_answer_about_non_cash_help(setup):
+    # A page that sent either under another name would otherwise lose it without a word.
+    client, session, _ = setup
+    payload = _application(session)
+    del payload["monthly_take_home_pay"]
+    del payload["receives_noncash_assistance"]
+
+    resp = client.post("/api/intake/fee-waiver/", payload, format="json")
+
+    assert resp.status_code == 400
+    assert set(resp.json()) == {"monthly_take_home_pay", "receives_noncash_assistance"}
+    assert not FeeWaiverApplication.objects.filter(session=session).exists()
+
+
+@pytest.mark.parametrize("kinds", [None, [], [""], ["   "]])
+def test_a_yes_to_non_cash_help_needs_what_kind(setup, kinds):
+    client, session, _ = setup
+    payload = _application(session, receives_noncash_assistance=True, benefit_types=kinds)
+    if kinds is None:
+        del payload["benefit_types"]
+
+    resp = client.post("/api/intake/fee-waiver/", payload, format="json")
+
+    assert resp.status_code == 400
+    assert "benefit_types" in resp.json()
+    assert not FeeWaiverApplication.objects.filter(session=session).exists()
+
+
+@pytest.mark.parametrize(("length", "status"), [(255, 201), (256, 400)])
+def test_what_kind_is_kept_up_to_a_line_of_text(setup, length, status):
+    client, session, _ = setup
+    payload = _application(session, receives_noncash_assistance=True, benefit_types=["x" * length])
+
+    resp = client.post("/api/intake/fee-waiver/", payload, format="json")
+
+    assert resp.status_code == status
+    assert FeeWaiverApplication.objects.filter(session=session).exists() == (status == 201)
+
+
+def test_a_no_to_non_cash_help_keeps_no_kind(setup):
+    # "What kind?" opens only under Yes, so a kind sent with No is not an answer.
+    client, session, _ = setup
+    resp = client.post(
+        "/api/intake/fee-waiver/",
+        _application(session, receives_noncash_assistance=False, benefit_types=["SNAP"]),
+        format="json",
+    )
+
+    assert resp.status_code == 201
+    fw = FeeWaiverApplication.objects.get(session=session)
+    assert (fw.receives_noncash_assistance, fw.benefit_types) == (False, [])
+
+
+def test_changing_the_answer_to_yes_later_still_needs_what_kind(setup):
+    client, session, _ = setup
+    client.post("/api/intake/fee-waiver/", _application(session), format="json")
+    fw = FeeWaiverApplication.objects.get(session=session)
+
+    refused = client.patch(
+        f"/api/intake/fee-waiver/{fw.id}/", {"receives_noncash_assistance": True}, format="json"
+    )
+    fw.refresh_from_db()
+    assert refused.status_code == 400
+    assert fw.receives_noncash_assistance is False
+
+    accepted = client.patch(
+        f"/api/intake/fee-waiver/{fw.id}/",
+        {"receives_noncash_assistance": True, "benefit_types": ["Housing subsidy"]},
+        format="json",
+    )
+    fw.refresh_from_db()
+    assert accepted.status_code == 200
+    assert (fw.receives_noncash_assistance, fw.benefit_types) == (True, ["Housing subsidy"])
+
+
+def test_a_change_that_sends_one_answer_is_checked_against_the_other_one_stored(setup):
+    client, session, _ = setup
+    client.post(
+        "/api/intake/fee-waiver/",
+        _application(session, receives_noncash_assistance=True, benefit_types=["SNAP"]),
+        format="json",
+    )
+    fw = FeeWaiverApplication.objects.get(session=session)
+    url = f"/api/intake/fee-waiver/{fw.id}/"
+
+    cleared = client.patch(url, {"benefit_types": []}, format="json")
+    kept = client.patch(url, {"receives_noncash_assistance": True}, format="json")
+
+    fw.refresh_from_db()
+    assert (cleared.status_code, kept.status_code) == (400, 200)
+    assert (fw.receives_noncash_assistance, fw.benefit_types) == (True, ["SNAP"])
+
+
+def test_changing_the_answer_to_no_later_drops_the_kind(setup):
+    client, session, _ = setup
+    client.post(
+        "/api/intake/fee-waiver/",
+        _application(session, receives_noncash_assistance=True, benefit_types=["SNAP"]),
+        format="json",
+    )
+    fw = FeeWaiverApplication.objects.get(session=session)
+
+    resp = client.patch(
+        f"/api/intake/fee-waiver/{fw.id}/", {"receives_noncash_assistance": False}, format="json"
+    )
+
+    fw.refresh_from_db()
+    assert resp.status_code == 200
+    assert (fw.receives_noncash_assistance, fw.benefit_types) == (False, [])
+
+
+@pytest.mark.parametrize("amount", ["-0.01", "100000000.00", "12.345", "NaN", "Infinity"])
+def test_take_home_pay_must_be_zero_or_more_and_fit_its_column(setup, amount):
+    client, session, _ = setup
+
+    resp = client.post(
+        "/api/intake/fee-waiver/",
+        _application(session, monthly_take_home_pay=amount),
+        format="json",
+    )
+
+    assert resp.status_code == 400
+    assert "monthly_take_home_pay" in resp.json()
+    assert not FeeWaiverApplication.objects.filter(session=session).exists()
+
+
+@pytest.mark.parametrize("amount", ["0.00", "99999999.99"])
+def test_take_home_pay_of_zero_or_the_column_maximum_is_kept(setup, amount):
+    client, session, _ = setup
+
+    resp = client.post(
+        "/api/intake/fee-waiver/",
+        _application(session, monthly_take_home_pay=amount),
+        format="json",
+    )
+
+    assert resp.status_code == 201
+    stored = FeeWaiverApplication.objects.get(session=session).monthly_take_home_pay
+    assert stored == Decimal(amount)
+
+
+def test_take_home_pay_is_encrypted_at_rest(setup):
+    client, session, _ = setup
+    client.post(
+        "/api/intake/fee-waiver/",
+        _application(session, monthly_take_home_pay="2873.41"),
+        format="json",
+    )
+    fw = FeeWaiverApplication.objects.get(session=session)
+
+    with connection.cursor() as cursor:
+        cursor.execute(
+            "SELECT monthly_take_home_pay FROM fee_waiver_applications WHERE id = %s", [fw.id]
+        )
+        raw = cursor.fetchone()[0]
+
+    assert "2873" not in raw
+    assert fw.monthly_take_home_pay == Decimal("2873.41")
+
+
+def test_the_old_income_expense_and_benefit_answers_are_no_longer_written(setup):
+    # The page stopped asking them; the columns stay one release for the rows already saved.
+    client, session, _ = setup
+    resp = client.post(
+        "/api/intake/fee-waiver/",
+        _application(
+            session,
+            monthly_income="3200.00",
+            monthly_expenses="2560.00",
+            receives_public_benefits=True,
+        ),
+        format="json",
+    )
+
+    assert resp.status_code == 201
+    fw = FeeWaiverApplication.objects.get(session=session)
+    assert (fw.monthly_income, fw.monthly_expenses, fw.receives_public_benefits) == (
+        None,
+        None,
+        False,
+    )
+    assert {"monthly_income", "monthly_expenses", "receives_public_benefits"}.isdisjoint(
+        resp.json()
+    )
+
+
+# ── Reading the application back by session (DIG-157) ─────────────────
+
+
+def _results(resp):
+    assert resp.status_code == 200
+    return resp.json()["results"]
+
+
+def test_the_page_reads_only_the_application_of_the_session_it_shows(setup):
+    # One filer can have several sessions, each with its own answers.
+    client, session, user = setup
+    other_session = IntakeSession.objects.create(user=user, district=session.district)
+    client.post("/api/intake/fee-waiver/", _application(session), format="json")
+    client.post(
+        "/api/intake/fee-waiver/",
+        _application(other_session, monthly_take_home_pay="900.00"),
+        format="json",
+    )
+
+    first = _results(client.get(f"/api/intake/fee-waiver/?session={session.id}"))
+    second = _results(client.get(f"/api/intake/fee-waiver/?session={other_session.id}"))
+
+    assert [(row["session"], row["monthly_take_home_pay"]) for row in first] == [
+        (session.id, "1750.00")
+    ]
+    assert [(row["session"], row["monthly_take_home_pay"]) for row in second] == [
+        (other_session.id, "900.00")
+    ]
+
+
+def test_reading_another_users_session_returns_nothing(setup):
+    client, session, _ = setup
+    stranger = User.objects.create_user(username="stranger", password="pass")
+    their_session = IntakeSession.objects.create(user=stranger, district=session.district)
+    FeeWaiverApplication.objects.create(
+        session=their_session,
+        monthly_take_home_pay=Decimal("1000.00"),
+        receives_noncash_assistance=False,
+    )
+
+    assert _results(client.get(f"/api/intake/fee-waiver/?session={their_session.id}")) == []
+
+
+def test_reading_by_session_never_starts_an_application(setup):
+    # An application puts Form 103B in the packet, so opening the page must not create one.
+    client, session, _ = setup
+
+    assert _results(client.get(f"/api/intake/fee-waiver/?session={session.id}")) == []
+    assert not FeeWaiverApplication.objects.filter(session=session).exists()
+    assert "form_103b" not in packet(session)
+
+
+# ── Moving an application (DIG-178) ───────────────────────────────────
+
+
+def test_a_filer_cannot_move_their_application_onto_another_users_session(setup):
+    client, session, _ = setup
+    victim = User.objects.create_user(username="fw_victim", password="pass")
+    victim_session = IntakeSession.objects.create(user=victim, district=session.district)
+    client.post("/api/intake/fee-waiver/", _application(session), format="json")
+    fw = FeeWaiverApplication.objects.get(session=session)
+
+    resp = client.patch(
+        f"/api/intake/fee-waiver/{fw.id}/", {"session": victim_session.id}, format="json"
+    )
+
+    assert resp.status_code == 403
+    fw.refresh_from_db()
+    assert fw.session_id == session.id
+    assert not FeeWaiverApplication.objects.filter(session=victim_session).exists()
+
+
+def test_a_filer_can_still_change_their_own_application(setup):
+    client, session, _ = setup
+    client.post("/api/intake/fee-waiver/", _application(session), format="json")
+    fw = FeeWaiverApplication.objects.get(session=session)
+
+    resp = client.patch(
+        f"/api/intake/fee-waiver/{fw.id}/",
+        {"session": session.id, "household_size": 4},
+        format="json",
+    )
+
+    assert resp.status_code == 200
+    fw.refresh_from_db()
+    assert (fw.session_id, fw.household_size) == (session.id, 4)
PATCH
```

`test_fee_waiver_views.py` gains `_application(session, **answers)`, the body the page sends, and moves the existing tests onto it. The new tests check that the page's answers are kept and both are required; that a Yes needs a kind of at most 255 characters and a No keeps none, on a create and on a PATCH; and that take-home pay is zero or more, fits its column and is encrypted at rest. They also check that the old answers are no longer written, that the read by session returns only that session's application and never starts one, and that a PATCH can't move an application onto another user's session but can still change the filer's own. The migration test runs 0015 forward over a row saved before it and requires both new answers to stay empty. `test_completion.py` sends the new answers, and the read-back sends each waiver persona's `fee_waiver` answers and compares the stored applications.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_fee_waiver_views.py apps/intake/tests/test_data_migrations.py apps/intake/tests/test_completion.py::test_form_answers_sofa_and_fee_waiver_leave_a_completed_intake_complete -q -p no:cacheprovider 2>&1 | tail -31
```

Expected: FAIL — `29 failed, 10 passed`. The serializer still requires monthly_income and monthly_expenses and knows neither new field, so every request that sends the page's new body is a 400 naming the two old fields, and each test that saves an application first then finds none. test_cross_user_post_is_forbidden gets that 400 before its 403, and test_a_filer_cannot_move_their_application_onto_another_users_session fails at its setup, not on the missing guard; Step 4 shows its own red. Creating a row with the new fields through the ORM is a TypeError, and the migration test finds no node for 0015. The 10 that pass are the five older migration tests; three older fee-waiver tests that send no answers (the unauthenticated POST, and the two reads by id, whose rows the ORM creates with the old columns); and two that hold either way: the 256-character kind is still refused, by the 400 for the old fields, and a read with nothing saved returns nothing and starts no application. The read-back is left out here: until Step 6 it fails only on the seeds' missing fee_waiver key, and it runs in Step 7.

- [ ] **Step 3: Store the two answers, and stop writing the old ones**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/models.py b/backend/apps/intake/models.py
index a8b74d3..dccab2f 100644
--- a/backend/apps/intake/models.py
+++ b/backend/apps/intake/models.py
@@ -574,13 +574,27 @@ class FeeWaiverApplication(models.Model):
         help_text="Number of people in household (must be at least 1)",
     )

-    # Financial information (encrypted)
+    # Financial information (encrypted). monthly_income, monthly_expenses and
+    # receives_public_benefits are no longer written: the page stopped asking them, and they
+    # stay one release for the rows saved before (forms step 2 spec §5.7).
     monthly_income = EncryptedDecimalField(
-        max_digits=10, decimal_places=2, help_text="Total monthly income from all sources"
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        help_text="Total monthly income from all sources",
     )

     monthly_expenses = EncryptedDecimalField(
-        max_digits=10, decimal_places=2, help_text="Total monthly expenses"
+        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Total monthly expenses"
+    )
+
+    monthly_take_home_pay = EncryptedDecimalField(
+        max_digits=10,
+        decimal_places=2,
+        null=True,
+        blank=True,
+        help_text="Average monthly take-home pay, after taxes and payroll deductions (103B line 2)",
     )

     # Public benefits
@@ -588,6 +602,12 @@ class FeeWaiverApplication(models.Model):
         default=False, help_text="Receives SSI, SNAP, TANF, or other means-tested benefits"
     )

+    # Empty until the filer answers: a stored False prints a sworn "No" on 103B line 3.
+    receives_noncash_assistance = models.BooleanField(
+        null=True, help_text="Receives non-cash help from the government (103B line 3)"
+    )
+
+    # The "What kind?" answer when receives_noncash_assistance is True
     benefit_types = models.JSONField(
         default=list, blank=True, help_text="List of benefit programs (e.g., ['SNAP', 'Medicaid'])"
     )
diff --git a/backend/apps/intake/serializers.py b/backend/apps/intake/serializers.py
index 2736e19..0a06e9f 100644
--- a/backend/apps/intake/serializers.py
+++ b/backend/apps/intake/serializers.py
@@ -6,6 +6,7 @@ validation, nested relationships, and trauma-informed error messages.
 """

 import re
+from decimal import Decimal

 from django.contrib.auth import get_user_model
 from django.core.exceptions import FieldDoesNotExist
@@ -371,9 +372,24 @@ class IntakeSessionSerializer(serializers.ModelSerializer):


 class FeeWaiverApplicationSerializer(serializers.ModelSerializer):
-    # Explicit field declarations — EncryptedDecimalField confuses DRF's auto-mapper
-    monthly_income = serializers.DecimalField(max_digits=10, decimal_places=2)
-    monthly_expenses = serializers.DecimalField(max_digits=10, decimal_places=2)
+    """The fee-waiver page's answers (forms step 2 spec §5.7).
+
+    The old income, expenses and benefits answers are no longer written, so they are not
+    fields here. Take-home pay and the non-cash answer are required, so a page that sent
+    either under another name gets a 400 instead of losing it.
+    """
+
+    # Explicit field declaration — EncryptedDecimalField confuses DRF's auto-mapper.
+    # Zero or more and within the column, like every amount the filer types.
+    monthly_take_home_pay = serializers.DecimalField(
+        max_digits=10, decimal_places=2, min_value=Decimal("0")
+    )
+    # The model allows empty, for rows saved before the question existed.
+    receives_noncash_assistance = serializers.BooleanField()
+    # The "What kind?" answer: each kind is a non-blank line of text.
+    benefit_types = serializers.ListField(
+        child=serializers.CharField(max_length=255), required=False
+    )
     # Remove the auto-generated UniqueValidator on session so that a second POST
     # from the same session passes validation — perform_create uses update_or_create
     # to handle the upsert safely.
@@ -387,9 +403,8 @@ class FeeWaiverApplicationSerializer(serializers.ModelSerializer):
             "id",
             "session",
             "household_size",
-            "monthly_income",
-            "monthly_expenses",
-            "receives_public_benefits",
+            "monthly_take_home_pay",
+            "receives_noncash_assistance",
             "benefit_types",
             "cannot_pay_full",
             "cannot_pay_installments",
@@ -399,6 +414,23 @@ class FeeWaiverApplicationSerializer(serializers.ModelSerializer):
         ]
         read_only_fields = ["id", "status", "created_at", "updated_at"]

+    def validate(self, attrs):
+        """A Yes to non-cash help needs "What kind?" answered, and a No keeps no kind.
+
+        A PATCH may send only one of the two, so the other is the stored one.
+        """
+        answer = attrs.get(
+            "receives_noncash_assistance",
+            getattr(self.instance, "receives_noncash_assistance", None),
+        )
+        if answer is False:
+            attrs["benefit_types"] = []
+        elif answer and not attrs.get("benefit_types", getattr(self.instance, "benefit_types", [])):
+            raise serializers.ValidationError(
+                {"benefit_types": [self.fields["benefit_types"].error_messages["required"]]}
+            )
+        return attrs
+

 class SOFAPriorIncomeSerializer(serializers.ModelSerializer):
     """Prior income row for SOFA Form 107 Part 1."""
PATCH
```

```python file=backend/apps/intake/migrations/0015_feewaiverapplication_take_home_and_noncash.py
# Generated by Django 5.0.14 on 2026-10-13 13:07

from django.db import migrations, models

import apps.intake.fields


class Migration(migrations.Migration):

    dependencies = [
        ("intake", "0014_split_income_saved_as_zero"),
    ]

    operations = [
        migrations.AddField(
            model_name="feewaiverapplication",
            name="monthly_take_home_pay",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Average monthly take-home pay, after taxes and payroll deductions (103B line 2)",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="feewaiverapplication",
            name="receives_noncash_assistance",
            field=models.BooleanField(
                help_text="Receives non-cash help from the government (103B line 3)", null=True
            ),
        ),
        migrations.AlterField(
            model_name="feewaiverapplication",
            name="monthly_expenses",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Total monthly expenses",
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="feewaiverapplication",
            name="monthly_income",
            field=apps.intake.fields.EncryptedDecimalField(
                blank=True,
                decimal_places=2,
                help_text="Total monthly income from all sources",
                max_digits=10,
                null=True,
            ),
        ),
    ]
```

§5.7: `FeeWaiverApplication` gains take-home pay, encrypted like the row's other amounts, and the non-cash answer, empty until answered, because a stored False would print a sworn "No" on 103B line 3. Neither has a default, so rows saved before stay empty. The old income, expenses and benefits answers leave the serializer, so nothing writes them, and the two old amounts become optional. The serializer requires both new answers, keeps take-home pay at zero or more within its column, and checks "What kind?" against the answer, taking the half a PATCH leaves out from the stored row. Write 0015 exactly as given; regenerating it changes its header's timestamp.

- [ ] **Step 4: Run the fee-waiver API tests and watch the read and the move fail**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_fee_waiver_views.py -q -p no:cacheprovider 2>&1 | tail -4
```

Expected: FAIL — `2 failed, 30 passed`. The answers are now kept and checked, so only the view's two changes are missing. The read by session returns both of the filer's applications, because the list has no session filter, and the PATCH that moves the application onto another user's session answers 200 where the test wants the 403.

- [ ] **Step 5: Read the application by session, and refuse a move to another user's session**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/views.py b/backend/apps/intake/views.py
index 0adf432..7214096 100644
--- a/backend/apps/intake/views.py
+++ b/backend/apps/intake/views.py
@@ -536,17 +536,32 @@ class DebtViewSet(viewsets.ModelViewSet):


 class FeeWaiverViewSet(viewsets.ModelViewSet):
-    """CRUD for fee waiver applications, scoped to authenticated user's sessions."""
+    """CRUD for fee waiver applications, scoped to authenticated user's sessions.
+
+    GET /api/intake/fee-waiver/?session={id} reads one session's application, so the page
+    opens with the answers already sent (DIG-157). The read never creates one: an
+    application puts Form 103B in the packet.
+    """

     serializer_class = FeeWaiverApplicationSerializer
     permission_classes = [IsAuthenticated]
     http_method_names = ["get", "post", "patch", "head", "options"]
+    filterset_fields = ["session"]

     def get_queryset(self):
-        return FeeWaiverApplication.objects.filter(session__user=self.request.user).select_related(
-            "session"
+        return (
+            FeeWaiverApplication.objects.filter(session__user=self.request.user)
+            .select_related("session")
+            .order_by("id")
         )

+    def perform_update(self, serializer):
+        # A PATCH can't move the application onto another user's session (DIG-178).
+        session = serializer.validated_data.get("session")
+        if session is not None:
+            _assert_session_owned(session, self.request.user)
+        serializer.save()
+
     def perform_create(self, serializer):
         # FeeWaiverApplication is OneToOne with IntakeSession — second POST from
         # the same session would raise IntegrityError. Use update_or_create so
PATCH
```

The page reads one session's application without creating one, because an application puts 103B in the packet (DIG-157). `perform_update` closes DIG-178.

- [ ] **Step 6: Give the waiver personas their answers**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/management/commands/seed_demo_data.py b/backend/apps/intake/management/commands/seed_demo_data.py
index e5682bf..82dc632 100644
--- a/backend/apps/intake/management/commands/seed_demo_data.py
+++ b/backend/apps/intake/management/commands/seed_demo_data.py
@@ -156,6 +156,12 @@ def _maria_torres() -> dict:
                 },
             ],
         },
+        # The fee-waiver page's answers (Form 103B lines 2 and 3)
+        "fee_waiver": {
+            "monthly_take_home_pay": Decimal("2800.00"),
+            "receives_noncash_assistance": True,
+            "benefit_types": ["SNAP (food stamps)"],
+        },
     }


@@ -412,6 +418,12 @@ def _deshawn_mitchell() -> dict:
                 "consumer_business_classification": "consumer",
             },
         ],
+        # The fee-waiver page's answers (Form 103B lines 2 and 3)
+        "fee_waiver": {
+            "monthly_take_home_pay": Decimal("3050.00"),
+            "receives_noncash_assistance": False,
+            "benefit_types": [],
+        },
     }


@@ -476,6 +488,12 @@ def _sarah_chen() -> dict:
                 "consumer_business_classification": "consumer",
             },
         ],
+        # The fee-waiver page's answers (Form 103B lines 2 and 3)
+        "fee_waiver": {
+            "monthly_take_home_pay": Decimal("1750.00"),
+            "receives_noncash_assistance": False,
+            "benefit_types": [],
+        },
     }


@@ -587,17 +605,10 @@ class Command(BaseCommand):
         # Create FeeWaiverApplication for fee-waiver-eligible personas
         # (required by Form 103B generator)
         if result["qualifies_for_fee_waiver"]:
-            income_data = data["income"]
-            household_size = data["debtor"]["household_size"]
-            monthly_income = income_data["monthly_gross_wages"]
-            total_expenses = sum(data["expenses"].values())
-
             FeeWaiverApplication.objects.create(
                 session=session,
-                household_size=household_size,
-                monthly_income=monthly_income,
-                monthly_expenses=total_expenses,
-                receives_public_benefits=False,
+                household_size=data["debtor"]["household_size"],
+                **data["fee_waiver"],
                 cannot_pay_full=True,
                 cannot_pay_installments=True,
                 status="pending",
PATCH
```

§5.7's synthetic figures: Maria $2,800 take-home, Yes, "SNAP (food stamps)"; DeShawn $3,050, No; Sarah $1,750, No. `_create_persona` stops writing the old income, expenses and benefits columns.

- [ ] **Step 7: Run the backend tests again**

```bash
set -eo pipefail
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_fee_waiver_views.py apps/intake/tests/test_data_migrations.py apps/intake/tests/test_completion.py::test_form_answers_sofa_and_fee_waiver_leave_a_completed_intake_complete apps/forms/tests/test_api_readback.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `44 passed`: the 32 fee-waiver API tests, the six migration tests, the completion test and the five personas' read-backs.

- [ ] **Step 8: Write the page tests**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/FeeWaiverPage.test.tsx b/frontend/src/pages/__tests__/FeeWaiverPage.test.tsx
index 6328611..83683a9 100644
--- a/frontend/src/pages/__tests__/FeeWaiverPage.test.tsx
+++ b/frontend/src/pages/__tests__/FeeWaiverPage.test.tsx
@@ -7,6 +7,8 @@ import { server } from '../../test/mocks/server';
 import { IntakeProvider, useIntake } from '../../context/IntakeContext';
 import { FeeWaiverPage } from '../FeeWaiverPage';

+const API = 'http://localhost:8000/api';
+
 function renderFeeWaiver() {
   localStorage.setItem('current_session_id', '1');
   return render(
@@ -49,6 +51,60 @@ const ineligibleResult = {
   means_test_id: 1,
 };

+/** A session whose intake gave a household of 4 and income and expense totals */
+function sessionWithIntakeFigures() {
+  return http.get(`${API}/intake/sessions/:id/`, () =>
+    HttpResponse.json({
+      id: 1,
+      user: 1,
+      district: 1,
+      current_step: 8,
+      status: 'completed',
+      created_at: '2026-01-20T10:00:00Z',
+      updated_at: '2026-01-20T10:00:00Z',
+      completed_at: null,
+      debtor_info: { household_size: 4 },
+      income_info: { total_monthly_income: '2500.00' },
+      expense_info: { total_monthly_expenses: 1800 },
+      assets: [],
+      debts: [],
+    })
+  );
+}
+
+/** The application this session already sent, as the server returns it */
+function savedApplication(answers: Record<string, unknown>) {
+  return {
+    id: 7,
+    session: 1,
+    household_size: 2,
+    monthly_take_home_pay: '1750.00',
+    receives_noncash_assistance: true,
+    benefit_types: ['SNAP (food stamps)'],
+    cannot_pay_full: true,
+    cannot_pay_installments: true,
+    status: 'pending',
+    created_at: '2026-01-20T10:00:00Z',
+    updated_at: '2026-01-20T10:00:00Z',
+    ...answers,
+  };
+}
+
+/** Records each application the page sends */
+function captureSent() {
+  const sent: Record<string, unknown>[] = [];
+  server.use(
+    http.post(`${API}/intake/fee-waiver/`, async ({ request }) => {
+      const body = (await request.json()) as Record<string, unknown>;
+      sent.push(body);
+      return HttpResponse.json({ id: 1, ...body, status: 'pending' }, { status: 201 });
+    })
+  );
+  return sent;
+}
+
+const nonCashQuestion = () => screen.findByRole('group', { name: /non-cash help/i });
+
 describe('FeeWaiverPage', () => {
   it('renders the fee waiver heading', async () => {
     renderFeeWaiver();
@@ -59,11 +115,10 @@ describe('FeeWaiverPage', () => {

   it('continues to the financial history questions (SOFA), not the forms, once the application is sent', async () => {
     renderFeeWaiver();
-    await waitFor(() => screen.getByRole('heading', { name: /filing fee waiver/i }));

-    await userEvent.type(screen.getByLabelText(/household size/i), '1');
-    await userEvent.type(screen.getByLabelText(/monthly income/i), '1200');
-    await userEvent.type(screen.getByLabelText(/monthly expenses/i), '1000');
+    await userEvent.type(await screen.findByLabelText(/household size/i), '1');
+    await userEvent.type(screen.getByLabelText(/take-home pay/i), '1200');
+    await userEvent.click(screen.getByRole('radio', { name: 'No' }));

     await userEvent.click(screen.getByRole('button', { name: /submit/i }));

@@ -76,17 +131,16 @@ describe('FeeWaiverPage', () => {

   it('shows error when submission fails', async () => {
     server.use(
-      http.post('http://localhost:8000/api/intake/fee-waiver/', () =>
+      http.post(`${API}/intake/fee-waiver/`, () =>
         HttpResponse.json({ detail: 'Server error' }, { status: 400 })
       )
     );

     renderFeeWaiver();
-    await waitFor(() => screen.getByRole('heading', { name: /filing fee waiver/i }));

-    await userEvent.type(screen.getByLabelText(/household size/i), '1');
-    await userEvent.type(screen.getByLabelText(/monthly income/i), '1200');
-    await userEvent.type(screen.getByLabelText(/monthly expenses/i), '1000');
+    await userEvent.type(await screen.findByLabelText(/household size/i), '1');
+    await userEvent.type(screen.getByLabelText(/take-home pay/i), '1200');
+    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
     await userEvent.click(screen.getByRole('button', { name: /submit/i }));

     await waitFor(() => {
@@ -94,41 +148,244 @@ describe('FeeWaiverPage', () => {
     });
   });

-  it('pre-fills the form with the figures saved during intake', async () => {
+  it('fills in the household size from the intake, but never take-home pay, and no longer asks for expenses', async () => {
+    server.use(sessionWithIntakeFigures());
+
+    renderFeeWaiver();
+
+    // The filer only confirms the household they already gave
+    await waitFor(() => {
+      expect(screen.getByLabelText(/household size/i)).toHaveValue(4);
+    });
+    // Form 103B line 2 asks for take-home pay, which the intake never asked: the box starts empty
+    expect(
+      screen.getByLabelText(
+        'Your average monthly take-home pay (after taxes and payroll deductions)'
+      )
+    ).toHaveValue(null);
+    expect(screen.queryByLabelText(/monthly expenses/i)).not.toBeInTheDocument();
+    expect(screen.queryByLabelText(/means-tested public benefits/i)).not.toBeInTheDocument();
+  });
+
+  it('opens with the answers this session already sent, which win over the intake figures', async () => {
+    const reads: string[] = [];
     server.use(
-      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
+      sessionWithIntakeFigures(),
+      http.get(`${API}/intake/fee-waiver/`, ({ request }) => {
+        reads.push(new URL(request.url).searchParams.get('session') ?? '');
+        return HttpResponse.json({ count: 1, results: [savedApplication({})] });
+      })
+    );
+
+    renderFeeWaiver();
+
+    // A resubmit keeps every answer, the "cannot pay" boxes included (DIG-157)
+    await waitFor(() => {
+      expect(screen.getByLabelText(/household size/i)).toHaveValue(2);
+    });
+    expect(screen.getByLabelText(/take-home pay/i)).toHaveValue(1750);
+    expect(screen.getByRole('radio', { name: 'Yes' })).toBeChecked();
+    expect(screen.getByLabelText('What kind?')).toHaveValue('SNAP (food stamps)');
+    expect(screen.getByLabelText(/cannot pay the full filing fee/i)).toBeChecked();
+    expect(screen.getByLabelText(/cannot pay the filing fee in installments/i)).toBeChecked();
+    // One filer can have several sessions: the page reads this one's application
+    expect(reads).toEqual(['1']);
+  });
+
+  it('shows a saved No as No', async () => {
+    server.use(
+      http.get(`${API}/intake/fee-waiver/`, () =>
         HttpResponse.json({
-          id: 1,
-          user: 1,
-          district: 1,
-          current_step: 6,
-          status: 'in_progress',
-          created_at: '2026-01-20T10:00:00Z',
-          updated_at: '2026-01-20T10:00:00Z',
-          completed_at: null,
-          debtor_info: { household_size: 4 },
-          income_info: { total_monthly_income: 2500 },
-          expense_info: { total_monthly_expenses: 1800 },
-          assets: [],
-          debts: [],
+          count: 1,
+          results: [savedApplication({ receives_noncash_assistance: false, benefit_types: [] })],
         })
       )
     );

     renderFeeWaiver();
-    await waitFor(() => screen.getByRole('heading', { name: /filing fee waiver/i }));

-    // The filer only confirms numbers they already gave — they shouldn't retype.
+    await nonCashQuestion();
     await waitFor(() => {
-      expect(screen.getByLabelText(/household size/i)).toHaveValue(4);
+      expect(screen.getByRole('radio', { name: 'No' })).toBeChecked();
+    });
+    expect(screen.getByRole('radio', { name: 'Yes' })).not.toBeChecked();
+    expect(screen.queryByLabelText('What kind?')).not.toBeInTheDocument();
+  });
+
+  it('shows neither answer for an application saved before the question was asked', async () => {
+    // A stored answer is sworn on Form 103B, so an empty one stays empty until the filer picks
+    server.use(
+      http.get(`${API}/intake/fee-waiver/`, () =>
+        HttpResponse.json({
+          count: 1,
+          results: [
+            savedApplication({
+              monthly_take_home_pay: null,
+              receives_noncash_assistance: null,
+              benefit_types: [],
+            }),
+          ],
+        })
+      )
+    );
+
+    renderFeeWaiver();
+
+    await waitFor(() => {
+      expect(screen.getByLabelText(/household size/i)).toHaveValue(2);
+    });
+    expect(screen.getByLabelText(/take-home pay/i)).toHaveValue(null);
+    expect(screen.getByRole('radio', { name: 'Yes' })).not.toBeChecked();
+    expect(screen.getByRole('radio', { name: 'No' })).not.toBeChecked();
+  });
+
+  it('holds the form until the saved answers are read, so nothing typed is overwritten', async () => {
+    let answer: () => void = () => {};
+    const read = new Promise<void>((resolve) => {
+      answer = resolve;
+    });
+    server.use(
+      http.get(`${API}/intake/fee-waiver/`, async () => {
+        await read;
+        return HttpResponse.json({ count: 1, results: [savedApplication({})] });
+      })
+    );
+
+    renderFeeWaiver();
+
+    await screen.findByRole('heading', { name: /filing fee waiver/i });
+    // Let the session load and the read start, then check the form is still held back
+    await new Promise((resolve) => setTimeout(resolve, 100));
+    expect(screen.queryByLabelText(/household size/i)).not.toBeInTheDocument();
+    expect(screen.queryByRole('button', { name: /submit/i })).not.toBeInTheDocument();
+
+    answer();
+    await waitFor(() => {
+      expect(screen.getByLabelText(/household size/i)).toHaveValue(2);
+    });
+  });
+
+  it('asks about non-cash help with neither answer picked, and only Yes asks what kind', async () => {
+    renderFeeWaiver();
+
+    const question = await nonCashQuestion();
+    expect(question).toHaveAccessibleName(
+      'Do you receive non-cash help from the government, such as SNAP (food stamps) or a housing subsidy?'
+    );
+    expect(screen.getByRole('radio', { name: 'Yes' })).not.toBeChecked();
+    expect(screen.getByRole('radio', { name: 'No' })).not.toBeChecked();
+    expect(screen.queryByLabelText('What kind?')).not.toBeInTheDocument();
+
+    await userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
+    expect(screen.getByLabelText('What kind?')).toBeInTheDocument();
+
+    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
+    expect(screen.queryByLabelText('What kind?')).not.toBeInTheDocument();
+  });
+
+  it('sends take-home pay and the non-cash answer under the names the server keeps', async () => {
+    const sent = captureSent();
+    renderFeeWaiver();
+
+    await userEvent.type(await screen.findByLabelText(/household size/i), '3');
+    await userEvent.type(screen.getByLabelText(/take-home pay/i), '2800');
+    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
+    await userEvent.click(screen.getByLabelText(/cannot pay the full filing fee/i));
+    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
+
+    await screen.findByText('Statement of Financial Affairs');
+    // The old income, expenses and benefits answers are no longer sent
+    expect(sent).toEqual([
+      {
+        session: 1,
+        household_size: 3,
+        monthly_take_home_pay: '2800',
+        receives_noncash_assistance: false,
+        benefit_types: [],
+        cannot_pay_full: true,
+        cannot_pay_installments: false,
+      },
+    ]);
+  });
+
+  it('sends a Yes with what kind', async () => {
+    const sent = captureSent();
+    renderFeeWaiver();
+
+    await userEvent.type(await screen.findByLabelText(/household size/i), '3');
+    await userEvent.type(screen.getByLabelText(/take-home pay/i), '2800');
+    await userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
+    await userEvent.type(screen.getByLabelText('What kind?'), '  SNAP (food stamps) ');
+    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
+
+    await screen.findByText('Statement of Financial Affairs');
+    expect(sent).toHaveLength(1);
+    expect(sent[0]).toMatchObject({
+      receives_noncash_assistance: true,
+      benefit_types: ['SNAP (food stamps)'],
+    });
+  });
+
+  it('will not send the application until every question is answered', async () => {
+    const sent = captureSent();
+    renderFeeWaiver();
+
+    // Household size and take-home pay given, the non-cash question left unanswered
+    await userEvent.type(await screen.findByLabelText(/household size/i), '1');
+    await userEvent.type(screen.getByLabelText(/take-home pay/i), '1200');
+    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
+    expect(await screen.findByRole('alert')).toHaveTextContent(
+      'Please fill in all required fields.'
+    );
+
+    // A Yes without saying what kind
+    await userEvent.click(screen.getByRole('radio', { name: 'Yes' }));
+    await userEvent.type(screen.getByLabelText('What kind?'), '   ');
+    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
+    expect(screen.getByRole('alert')).toHaveTextContent('Please fill in all required fields.');
+
+    // Take-home pay cleared, the rest answered
+    await userEvent.click(screen.getByRole('radio', { name: 'No' }));
+    await userEvent.clear(screen.getByLabelText(/take-home pay/i));
+    await userEvent.click(screen.getByRole('button', { name: /submit/i }));
+    expect(screen.getByRole('alert')).toHaveTextContent('Please fill in all required fields.');
+
+    expect(sent).toEqual([]);
+    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
+  });
+
+  it('shows no form when the saved answers cannot be read, and reads them again on Try again', async () => {
+    // An empty form would send unticked "cannot pay" boxes over the saved ones (DIG-157)
+    let reads = 0;
+    server.use(
+      http.get(`${API}/intake/fee-waiver/`, () => {
+        reads += 1;
+        if (reads === 1) return HttpResponse.json({ detail: 'Bad request' }, { status: 400 });
+        return HttpResponse.json({ count: 1, results: [savedApplication({})] });
+      })
+    );
+
+    renderFeeWaiver();
+
+    expect(await screen.findByRole('alert')).toHaveTextContent(
+      "We couldn't get your latest information just now. Please try again in a moment."
+    );
+    expect(screen.queryByLabelText(/household size/i)).not.toBeInTheDocument();
+    expect(screen.queryByRole('button', { name: /submit/i })).not.toBeInTheDocument();
+
+    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
+
+    await waitFor(() => {
+      expect(screen.getByLabelText(/household size/i)).toHaveValue(2);
     });
-    expect(screen.getByLabelText(/monthly income/i)).toHaveValue(2500);
-    expect(screen.getByLabelText(/monthly expenses/i)).toHaveValue(1800);
+    expect(screen.getByLabelText(/take-home pay/i)).toHaveValue(1750);
+    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
+    expect(reads).toBe(2);
   });

   it('shows an off-ramp instead of the form when the filer is fee-waiver ineligible, and it leads on to SOFA', async () => {
     server.use(
-      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
+      http.post(`${API}/intake/sessions/:id/calculate_means_test/`, () =>
         HttpResponse.json({ means_test_result: ineligibleResult, session_id: 1 })
       )
     );
diff --git a/frontend/src/test/mocks/handlers.ts b/frontend/src/test/mocks/handlers.ts
index 56a0ba5..e4188d2 100644
--- a/frontend/src/test/mocks/handlers.ts
+++ b/frontend/src/test/mocks/handlers.ts
@@ -143,15 +143,19 @@ export const handlers = [
   ),

   // -- Fee Waiver -----------------------------------------------------------
+  // No application saved yet for the session the page reads (paginated, like every DRF list)
+  http.get(`${API}/intake/fee-waiver/`, () =>
+    HttpResponse.json({ count: 0, next: null, previous: null, results: [] })
+  ),
+
   http.post(`${API}/intake/fee-waiver/`, async ({ request }) => {
     const body = (await request.json()) as { session: number };
     return HttpResponse.json({
       id: 1,
       session: body.session,
       household_size: 1,
-      monthly_income: '1200.00',
-      monthly_expenses: '1000.00',
-      receives_public_benefits: false,
+      monthly_take_home_pay: '1200.00',
+      receives_noncash_assistance: false,
       benefit_types: [],
       cannot_pay_full: true,
       cannot_pay_installments: true,
PATCH
```

MSW gains a default read that finds no saved application, and its POST reply moves to the new fields. The page tests require the household pre-fill but never a take-home one; the saved answers to win over the pre-fill, read for this session; a saved No and an old row with neither answer shown as they are; the form held back until the read settles; the question's exact words with neither radio picked; the new names in the body sent; no send while a question is unanswered; and no form after a failed read, until Try again reads it.

- [ ] **Step 9: Run them and watch them fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FeeWaiverPage.test.tsx 2>&1 | tail -8
```

Expected: FAIL — `12 failed` and `2 passed`. The page has no take-home box, no non-cash question and no "What kind?", and it never reads the saved application, so it shows its form at once and opens empty. Only the heading test and the off-ramp test pass.

- [ ] **Step 10: Ask take-home pay and non-cash help, and open with the saved answers**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/api/client.ts b/frontend/src/api/client.ts
index ac20aa6..0fbfd2f 100644
--- a/frontend/src/api/client.ts
+++ b/frontend/src/api/client.ts
@@ -485,9 +485,9 @@ export const debtsAPI = {
 export interface FeeWaiverPayload {
   session: number;
   household_size: number;
-  monthly_income: string;
-  monthly_expenses: string;
-  receives_public_benefits: boolean;
+  monthly_take_home_pay: string;
+  receives_noncash_assistance: boolean;
+  // The "What kind?" answer; empty when the filer gets no non-cash help
   benefit_types: string[];
   cannot_pay_full: boolean;
   cannot_pay_installments: boolean;
@@ -497,9 +497,9 @@ export interface FeeWaiverApplication {
   id: number;
   session: number;
   household_size: number;
-  monthly_income: string;
-  monthly_expenses: string;
-  receives_public_benefits: boolean;
+  // Both null on an application saved before the page asked them
+  monthly_take_home_pay: string | null;
+  receives_noncash_assistance: boolean | null;
   benefit_types: string[];
   cannot_pay_full: boolean;
   cannot_pay_installments: boolean;
@@ -515,6 +515,19 @@ export const feeWaiverAPI = {
       body: JSON.stringify(data),
     });
   },
+
+  /**
+   * The application this session already sent, or null
+   * GET /api/intake/fee-waiver/?session={sessionId}
+   */
+  getBySession: async (sessionId: number): Promise<FeeWaiverApplication | null> => {
+    const response = await apiFetch<FeeWaiverApplication[] | { results: FeeWaiverApplication[] }>(
+      `/intake/fee-waiver/?session=${sessionId}`
+    );
+    // Handle both paginated ({results: [...]}) and unpaginated ([...]) responses
+    const applications = Array.isArray(response) ? response : (response.results ?? []);
+    return applications[0] ?? null;
+  },
 };

 // ============================================================================
diff --git a/frontend/src/pages/FeeWaiverPage.tsx b/frontend/src/pages/FeeWaiverPage.tsx
index 8d936b2..eb14fd8 100644
--- a/frontend/src/pages/FeeWaiverPage.tsx
+++ b/frontend/src/pages/FeeWaiverPage.tsx
@@ -7,28 +7,61 @@ import { Button } from '../components/common';
 export function FeeWaiverPage() {
   const navigate = useNavigate();
   const { session, meansTestResult } = useIntake();
+  const sessionId = session?.id;

   const [householdSize, setHouseholdSize] = useState('');
-  const [monthlyIncome, setMonthlyIncome] = useState('');
-  const [monthlyExpenses, setMonthlyExpenses] = useState('');
-  const [receivesPublicBenefits, setReceivesPublicBenefits] = useState(false);
+  const [takeHomePay, setTakeHomePay] = useState('');
+  // null until the filer picks Yes or No: neither is selected to start with
+  const [receivesNoncash, setReceivesNoncash] = useState<boolean | null>(null);
+  const [noncashKind, setNoncashKind] = useState('');
   const [cannotPayFull, setCannotPayFull] = useState(false);
   const [cannotPayInstallments, setCannotPayInstallments] = useState(false);
   const [error, setError] = useState<string | null>(null);
   const [isSubmitting, setIsSubmitting] = useState(false);
+  const [savedRead, setSavedRead] = useState<'pending' | 'done' | 'failed'>('pending');
+  const [readAttempt, setReadAttempt] = useState(0);

-  // Pre-fill the figures the filer already gave during intake — they only need
-  // to confirm them. Functional updates avoid clobbering any edits they make.
+  // Pre-fill the household size the filer already gave during intake — they only need
+  // to confirm it. Take-home pay is never pre-filled: the intake asks income before taxes.
   useEffect(() => {
-    if (!session) return;
-    const hh = session.debtor_info?.household_size;
-    const income = session.income_info?.total_monthly_income;
-    const expenses = session.expense_info?.total_monthly_expenses;
+    const hh = session?.debtor_info?.household_size;
     if (hh != null) setHouseholdSize((cur) => cur || String(hh));
-    if (income != null) setMonthlyIncome((cur) => cur || String(income));
-    if (expenses != null) setMonthlyExpenses((cur) => cur || String(expenses));
   }, [session]);

+  // Open with the answers this session already sent. They win over the pre-fill, so sending
+  // the application again keeps every box the filer ticked (DIG-157). The form waits for the
+  // read: an empty form sent over the saved answers would undo them.
+  useEffect(() => {
+    if (sessionId == null) return;
+    let cancelled = false;
+    api.feeWaiver
+      .getBySession(sessionId)
+      .then((saved) => {
+        if (cancelled) return;
+        if (saved) {
+          setHouseholdSize(String(saved.household_size));
+          setTakeHomePay(saved.monthly_take_home_pay ?? '');
+          setReceivesNoncash(saved.receives_noncash_assistance);
+          setNoncashKind(saved.benefit_types.join(', '));
+          setCannotPayFull(saved.cannot_pay_full);
+          setCannotPayInstallments(saved.cannot_pay_installments);
+        }
+        setSavedRead('done');
+      })
+      .catch(() => {
+        if (!cancelled) setSavedRead('failed');
+      });
+
+    return () => {
+      cancelled = true;
+    };
+  }, [sessionId, readAttempt]);
+
+  const handleRetry = () => {
+    setSavedRead('pending');
+    setReadAttempt((attempt) => attempt + 1);
+  };
+
   // Only show the application to filers the means test flags as fee-waiver
   // eligible. If we have a result and it says no, offer a gentle off-ramp
   // rather than a form they can't benefit from (note 21).
@@ -37,7 +70,12 @@ export function FeeWaiverPage() {
   const handleSubmit = async (e: React.FormEvent) => {
     e.preventDefault();
     if (!session) return;
-    if (!householdSize || !monthlyIncome || !monthlyExpenses) {
+    if (
+      !householdSize ||
+      !takeHomePay ||
+      receivesNoncash === null ||
+      (receivesNoncash && !noncashKind.trim())
+    ) {
       setError('Please fill in all required fields.');
       return;
     }
@@ -49,10 +87,9 @@ export function FeeWaiverPage() {
       await api.feeWaiver.create({
         session: session.id,
         household_size: parseInt(householdSize, 10),
-        monthly_income: monthlyIncome,
-        monthly_expenses: monthlyExpenses,
-        receives_public_benefits: receivesPublicBenefits,
-        benefit_types: [],
+        monthly_take_home_pay: takeHomePay,
+        receives_noncash_assistance: receivesNoncash,
+        benefit_types: receivesNoncash ? [noncashKind.trim()] : [],
         cannot_pay_full: cannotPayFull,
         cannot_pay_installments: cannotPayInstallments,
       });
@@ -89,97 +126,125 @@ export function FeeWaiverPage() {
             Please confirm the details below.
           </p>

+          {savedRead === 'failed' && (
+            <div className="fee-waiver-error">
+              <p role="alert">
+                We couldn't get your latest information just now. Please try again in a moment.
+              </p>
+              <Button type="button" onClick={handleRetry}>
+                Try again
+              </Button>
+            </div>
+          )}
+
           {error && (
             <div className="fee-waiver-error" role="alert">
               <p>{error}</p>
             </div>
           )}

-          <form onSubmit={handleSubmit} noValidate>
-            <div className="form-field">
-              <label className="form-label" htmlFor="household-size">
-                Household Size
-              </label>
-              <input
-                className="form-input"
-                id="household-size"
-                type="number"
-                min={1}
-                value={householdSize}
-                onChange={(e) => setHouseholdSize(e.target.value)}
-                required
-              />
-            </div>
-
-            <div className="form-field">
-              <label className="form-label" htmlFor="monthly-income">
-                Total Monthly Income
-              </label>
-              <input
-                className="form-input"
-                id="monthly-income"
-                type="number"
-                min={0}
-                step="0.01"
-                value={monthlyIncome}
-                onChange={(e) => setMonthlyIncome(e.target.value)}
-                required
-              />
-            </div>
-
-            <div className="form-field">
-              <label className="form-label" htmlFor="monthly-expenses">
-                Total Monthly Expenses
-              </label>
-              <input
-                className="form-input"
-                id="monthly-expenses"
-                type="number"
-                min={0}
-                step="0.01"
-                value={monthlyExpenses}
-                onChange={(e) => setMonthlyExpenses(e.target.value)}
-                required
-              />
-            </div>
-
-            <div className="form-field">
-              <label className="fee-waiver-checkbox">
-                <input
-                  type="checkbox"
-                  checked={receivesPublicBenefits}
-                  onChange={(e) => setReceivesPublicBenefits(e.target.checked)}
-                />{' '}
-                I receive SSI, SNAP, TANF, or other means-tested public benefits
-              </label>
-            </div>
-
-            <div className="form-field">
-              <label className="fee-waiver-checkbox">
+          {savedRead === 'done' && (
+            <form onSubmit={handleSubmit} noValidate>
+              <div className="form-field">
+                <label className="form-label" htmlFor="household-size">
+                  Household Size
+                </label>
                 <input
-                  type="checkbox"
-                  checked={cannotPayFull}
-                  onChange={(e) => setCannotPayFull(e.target.checked)}
-                />{' '}
-                I cannot pay the full filing fee ($338) today
-              </label>
-            </div>
-
-            <div className="form-field">
-              <label className="fee-waiver-checkbox">
+                  className="form-input"
+                  id="household-size"
+                  type="number"
+                  min={1}
+                  value={householdSize}
+                  onChange={(e) => setHouseholdSize(e.target.value)}
+                  required
+                />
+              </div>
+
+              <div className="form-field">
+                <label className="form-label" htmlFor="take-home-pay">
+                  Your average monthly take-home pay (after taxes and payroll deductions)
+                </label>
                 <input
-                  type="checkbox"
-                  checked={cannotPayInstallments}
-                  onChange={(e) => setCannotPayInstallments(e.target.checked)}
-                />{' '}
-                I cannot pay the filing fee in installments
-              </label>
-            </div>
-
-            <Button type="submit" disabled={isSubmitting}>
-              {isSubmitting ? 'Submitting...' : 'Submit Waiver Application'}
-            </Button>
-          </form>
+                  className="form-input"
+                  id="take-home-pay"
+                  type="number"
+                  min={0}
+                  step="0.01"
+                  value={takeHomePay}
+                  onChange={(e) => setTakeHomePay(e.target.value)}
+                  required
+                />
+              </div>
+
+              <fieldset className="form-field fee-waiver-question">
+                <legend className="form-label">
+                  Do you receive non-cash help from the government, such as SNAP (food stamps) or a
+                  housing subsidy?
+                </legend>
+                <label className="fee-waiver-checkbox">
+                  <input
+                    type="radio"
+                    name="receives-noncash-assistance"
+                    checked={receivesNoncash === true}
+                    onChange={() => setReceivesNoncash(true)}
+                  />{' '}
+                  Yes
+                </label>
+                <label className="fee-waiver-checkbox">
+                  <input
+                    type="radio"
+                    name="receives-noncash-assistance"
+                    checked={receivesNoncash === false}
+                    onChange={() => setReceivesNoncash(false)}
+                  />{' '}
+                  No
+                </label>
+              </fieldset>
+
+              {receivesNoncash && (
+                <div className="form-field">
+                  <label className="form-label" htmlFor="noncash-kind">
+                    What kind?
+                  </label>
+                  <input
+                    className="form-input"
+                    id="noncash-kind"
+                    type="text"
+                    maxLength={255}
+                    value={noncashKind}
+                    onChange={(e) => setNoncashKind(e.target.value)}
+                    required
+                  />
+                </div>
+              )}
+
+              <div className="form-field">
+                <label className="fee-waiver-checkbox">
+                  <input
+                    type="checkbox"
+                    checked={cannotPayFull}
+                    onChange={(e) => setCannotPayFull(e.target.checked)}
+                  />{' '}
+                  I cannot pay the full filing fee ($338) today
+                </label>
+              </div>
+
+              <div className="form-field">
+                <label className="fee-waiver-checkbox">
+                  <input
+                    type="checkbox"
+                    checked={cannotPayInstallments}
+                    onChange={(e) => setCannotPayInstallments(e.target.checked)}
+                  />{' '}
+                  I cannot pay the filing fee in installments
+                </label>
+              </div>
+
+              <Button type="submit" disabled={isSubmitting}>
+                {isSubmitting ? 'Submitting...' : 'Submit Waiver Application'}
+              </Button>
+            </form>
+          )}
         </>
       )}
     </main>
diff --git a/frontend/src/styles/global.css b/frontend/src/styles/global.css
index a0cdcb5..ddf04b7 100644
--- a/frontend/src/styles/global.css
+++ b/frontend/src/styles/global.css
@@ -1759,6 +1759,13 @@ a {
   margin-top: 0.2em;
 }

+/* The Yes/No question: a fieldset for its legend, without the browser's frame */
+.fee-waiver-question {
+  border: none;
+  padding: 0;
+  min-width: 0;
+}
+
 /* =========================================================================
    SOFA Page (Form 107 - Statement of Financial Affairs)
    ========================================================================= */
PATCH
```

§5.7 and DIG-157: the page reads the session's saved application through `getBySession` and opens with it, so a resubmit keeps every box. The read runs once per session id and once per Try again, and it uses SOFAStep's `cancelled` flag, so the reply to an effect already cleaned up, such as StrictMode's first run, is ignored. Household size is still pre-filled from the intake until the saved answers replace it. The take-home box carries the spec's label and is never pre-filled, the non-cash question starts with neither answer picked, and Yes opens "What kind?". The expenses box and the public-benefits checkbox are gone. `.fee-waiver-question` removes the fieldset's frame.

- [ ] **Step 11: Run the page tests again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/FeeWaiverPage.test.tsx 2>&1 | tail -8
```

Expected: `14 passed`.

- [ ] **Step 12: Answer the new questions in the journeys**

```bash
git apply <<'PATCH'
diff --git a/frontend/e2e/fixtures/personas.ts b/frontend/e2e/fixtures/personas.ts
index 5b97d07..bafa84f 100644
--- a/frontend/e2e/fixtures/personas.ts
+++ b/frontend/e2e/fixtures/personas.ts
@@ -65,7 +65,19 @@ export interface PersonaData {
   };
 }

-export const MARIA: PersonaData = {
+/** What a persona answers on the fee-waiver page (Form 103B lines 2 and 3) */
+export interface PersonaFeeWaiver {
+  take_home_pay: number;
+  // The "What kind?" answer, or null for a persona who gets no non-cash help
+  noncash_assistance: string | null;
+}
+
+/** A persona the means test sends to the fee-waiver page */
+export interface WaiverPersonaData extends PersonaData {
+  fee_waiver: PersonaFeeWaiver;
+}
+
+export const MARIA: WaiverPersonaData = {
   username: `e2e_maria_${RUN_ID}`,
   password: 'TestPass-2026!',
   debtor: {
@@ -136,6 +148,7 @@ export const MARIA: PersonaData = {
       is_in_collections: false,
     },
   ],
+  fee_waiver: { take_home_pay: 2800, noncash_assistance: 'SNAP (food stamps)' },
   expected: { passes_means_test: true, fee_waiver_eligible: true },
 };

@@ -280,7 +293,7 @@ export const PRIYA: PersonaData = {
   expected: { passes_means_test: false, fee_waiver_eligible: false },
 };

-export const DESHAWN: PersonaData = {
+export const DESHAWN: WaiverPersonaData = {
   username: `e2e_deshawn_${RUN_ID}`,
   password: 'TestPass-2026!',
   debtor: {
@@ -365,12 +378,13 @@ export const DESHAWN: PersonaData = {
       is_in_collections: true,
     },
   ],
+  fee_waiver: { take_home_pay: 3050, noncash_assistance: null },
   // $3,500/month = $42,000/year — below 60% of the HH2 median ($54,915.60),
   // so DeShawn qualifies for the fee waiver as well as Chapter 7.
   expected: { passes_means_test: true, fee_waiver_eligible: true },
 };

-export const SARAH: PersonaData = {
+export const SARAH: WaiverPersonaData = {
   username: `e2e_sarah_${RUN_ID}`,
   password: 'TestPass-2026!',
   debtor: {
@@ -425,5 +439,6 @@ export const SARAH: PersonaData = {
       is_in_collections: true,
     },
   ],
+  fee_waiver: { take_home_pay: 1750, noncash_assistance: null },
   expected: { passes_means_test: true, fee_waiver_eligible: true },
 };
diff --git a/frontend/e2e/journeys/deshawn-assets.spec.ts b/frontend/e2e/journeys/deshawn-assets.spec.ts
index a25b24a..fc164dc 100644
--- a/frontend/e2e/journeys/deshawn-assets.spec.ts
+++ b/frontend/e2e/journeys/deshawn-assets.spec.ts
@@ -77,11 +77,10 @@ test.describe('DeShawn Mitchell — Assets', () => {

     // $42,000/year is below 60% of the HH2 median ($54,915.60), so DeShawn
     // is fee-waiver eligible and gets routed to the waiver application first.
-    const totalExpenses = Object.values(DESHAWN.expenses).reduce((a, b) => a + b, 0);
     await feeWaiver.submit(
       DESHAWN.debtor.household_size,
-      DESHAWN.income.total_monthly_income,
-      totalExpenses
+      DESHAWN.fee_waiver.take_home_pay,
+      DESHAWN.fee_waiver.noncash_assistance
     );

     // The waiver application continues to the SOFA step (DIG-149). This journey isn't about
diff --git a/frontend/e2e/journeys/maria-happy-path.spec.ts b/frontend/e2e/journeys/maria-happy-path.spec.ts
index 3d0ce24..d921c7f 100644
--- a/frontend/e2e/journeys/maria-happy-path.spec.ts
+++ b/frontend/e2e/journeys/maria-happy-path.spec.ts
@@ -77,14 +77,10 @@ test.describe('Maria Torres — Happy Path', () => {
     await wizard.completeIntake();

     // Maria is fee-waiver eligible → routed to the waiver application first
-    const totalExpenses = Object.values(MARIA.expenses).reduce((a, b) => a + b, 0);
-    // Every expense she typed was saved under a name the backend keeps, so the
-    // pre-filled total is her full $2,560, not just the fields that kept their names.
-    await expect(feeWaiver.monthlyExpenses()).toHaveValue(String(totalExpenses));
     await feeWaiver.submit(
       MARIA.debtor.household_size,
-      MARIA.income.total_monthly_income,
-      totalExpenses
+      MARIA.fee_waiver.take_home_pay,
+      MARIA.fee_waiver.noncash_assistance
     );

     // The waiver application continues to the SOFA step (DIG-149). This journey isn't about
diff --git a/frontend/e2e/journeys/sarah-simplest.spec.ts b/frontend/e2e/journeys/sarah-simplest.spec.ts
index 6312f5d..27cec81 100644
--- a/frontend/e2e/journeys/sarah-simplest.spec.ts
+++ b/frontend/e2e/journeys/sarah-simplest.spec.ts
@@ -76,11 +76,10 @@ test.describe('Sarah Chen — Simplest Case', () => {
     await wizard.completeIntake();

     // Sarah is fee-waiver eligible → routed to the waiver application first
-    const totalExpenses = Object.values(SARAH.expenses).reduce((a, b) => a + b, 0);
     await feeWaiver.submit(
       SARAH.debtor.household_size,
-      SARAH.income.total_monthly_income,
-      totalExpenses
+      SARAH.fee_waiver.take_home_pay,
+      SARAH.fee_waiver.noncash_assistance
     );

     // The waiver application continues to the SOFA step (DIG-149). This journey isn't about
diff --git a/frontend/e2e/pages/fee-waiver.page.ts b/frontend/e2e/pages/fee-waiver.page.ts
index 663b5e3..a1f4f7f 100644
--- a/frontend/e2e/pages/fee-waiver.page.ts
+++ b/frontend/e2e/pages/fee-waiver.page.ts
@@ -8,15 +8,17 @@ import type { Page } from '@playwright/test';
 export class FeeWaiverPage {
   constructor(private page: Page) {}

-  /** The expenses box, which the page pre-fills from the total the intake saved. */
-  monthlyExpenses() {
-    return this.page.getByLabel(/total monthly expenses/i);
-  }
-
-  async submit(householdSize: number, monthlyIncome: number, monthlyExpenses: number) {
+  /** noncashAssistance is the "What kind?" answer, or null to answer No */
+  async submit(householdSize: number, takeHomePay: number, noncashAssistance: string | null) {
     await this.page.getByLabel(/household size/i).fill(String(householdSize));
-    await this.page.getByLabel(/total monthly income/i).fill(String(monthlyIncome));
-    await this.page.getByLabel(/total monthly expenses/i).fill(String(monthlyExpenses));
+    await this.page.getByLabel(/take-home pay/i).fill(String(takeHomePay));
+    const question = this.page.getByRole('group', { name: /non-cash help/i });
+    if (noncashAssistance === null) {
+      await question.getByRole('radio', { name: 'No' }).check();
+    } else {
+      await question.getByRole('radio', { name: 'Yes' }).check();
+      await this.page.getByLabel('What kind?').fill(noncashAssistance);
+    }
     await this.page.getByLabel(/cannot pay the full filing fee/i).check();
     await this.page.getByLabel(/cannot pay the filing fee in installments/i).check();
     await this.page.getByRole('button', { name: /submit waiver application/i }).click();
PATCH
```

§7.9: the page object types the take-home figure and answers the question, and loses its expenses argument and `monthlyExpenses()`. The waiver personas carry the seeds' figures. Each waiver journey passes its persona's take-home figure and answer in place of the income and expense totals, and Maria's journey drops its expenses pre-fill check.

- [ ] **Step 13: Run every gate**

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

Expected: `1776 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  320 passed (320)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 14: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 15: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/intake/migrations/0015_feewaiverapplication_take_home_and_noncash.py \
  backend/apps/forms/tests/test_api_readback.py \
  backend/apps/intake/management/commands/seed_demo_data.py \
  backend/apps/intake/models.py \
  backend/apps/intake/serializers.py \
  backend/apps/intake/tests/test_completion.py \
  backend/apps/intake/tests/test_data_migrations.py \
  backend/apps/intake/tests/test_fee_waiver_views.py \
  backend/apps/intake/views.py \
  frontend/e2e/fixtures/personas.ts \
  frontend/e2e/journeys/deshawn-assets.spec.ts \
  frontend/e2e/journeys/maria-happy-path.spec.ts \
  frontend/e2e/journeys/sarah-simplest.spec.ts \
  frontend/e2e/pages/fee-waiver.page.ts \
  frontend/src/api/client.ts \
  frontend/src/pages/FeeWaiverPage.tsx \
  frontend/src/pages/__tests__/FeeWaiverPage.test.tsx \
  frontend/src/styles/global.css \
  frontend/src/test/mocks/handlers.ts
git commit -F - <<'MSG'
feat(intake,frontend): ask the fee waiver's take-home pay and non-cash help, and keep its answers

Form 103B line 2 asks for take-home pay, and line 3 asks whether the filer
gets non-cash help from the government, and what kind. The page asked for
total income and expenses instead, pre-filled them from the intake, and
reset every answer when the filer came back to it (DIG-157).

FeeWaiverApplication gains monthly_take_home_pay, encrypted like the row's
other amounts, and receives_noncash_assistance, empty until answered: a
stored False would print a sworn "No". Neither has a default, so rows saved
before stay empty. benefit_types holds the "What kind?" answer: a Yes needs
one, and a No keeps none. Take-home pay is zero or more and fits its column.
The API requires both new answers, so a page that sent one under another
name gets a 400 instead of losing it. The old income, expenses and benefits
columns become optional and are no longer written; they stay one release.

The page reads the session's saved application (GET
/api/intake/fee-waiver/?session=<id>, which never creates one) and opens
with it, so sending it again keeps the "cannot pay" boxes. The form waits
for that read, and a failed read offers Try again instead of an empty form.
The take-home box is never pre-filled, the non-cash question starts with
neither answer picked and Yes opens "What kind?", and the expenses box and
the public-benefits checkbox are gone.

A PATCH can no longer move an application onto another user's session
(DIG-178).

The seeds give Maria $2,800 take-home and SNAP, DeShawn $3,050 and Sarah
$1,750 with no non-cash help, and stop writing the old columns. The
fee-waiver page object types the take-home figure and the answer and loses
its expenses argument, and Maria's journey drops its expenses pre-fill
check. The read-back sends the new answers and compares the stored
applications, since no form prints them until 2b. Until 2b moves them,
103B's "4 type" and "5 Type" boxes, which read the old columns, print 0.00;
both are known wrong-box defects (DIG-78).
MSG
git status --short
```

### Task 14: Describe what forms step 2a changed, and say whose income each persona figure is

_Built and verified as commit `902cafa` on `plan/forms-step2a`._

**Files:**

- Modify: `CLAUDE.md`
- Modify: `backend/apps/intake/serializers.py`
- Modify: `backend/apps/intake/tests/test_completion.py`
- Modify: `docs/superpowers/specs/2026-10-10-forms-foundation-design.md`
- Modify: `docs/testing/persona-briefs/deshawn-mitchell.md`
- Modify: `docs/testing/persona-briefs/james-washington.md`
- Modify: `docs/testing/persona-briefs/maria-torres.md`
- Modify: `docs/testing/persona-briefs/priya-sharma.md`
- Modify: `docs/testing/persona-briefs/sarah-chen.md`

**Interfaces:**

- Consumes:
  - The code Tasks 1 to 13 built, which the new gotchas name: `ASSERTED_CASES` and the binding key `<source>:<producer>` (Task 1); `IntakeSession.reopen()` and the 422 "Finish your intake before preparing your forms." (Task 2); `useAutoSave`, `currentStepBody` and `saveNow` (Task 3); `PUT /intake/sessions/{id}/contracts/` and `codebtors/` (Task 4); `is_secured` read and written (Task 5); the wizard sending all 13 expense amounts, a blank box as 0 (Task 6); the fee-waiver page continuing to `/sofa` (Task 7); `IncomeInfo.SOURCE_FIELDS`, `current_monthly_income`, `IncomeNotSplit` and `total_monthly_income` (Task 9); `is_above_median` (Task 10); `_prepare` and `_recalculate_means_test` in `apps/forms/views.py`, filed forms kept outside the packet and "Filed, no longer in your current packet" (Task 11); the packet reload after every Generate All (Task 12); `FeeWaiverApplication.monthly_take_home_pay`, `receives_noncash_assistance`, `benefit_types` and `GET /api/intake/fee-waiver/?session=<id>` (Task 13).
  - The seeds' figures in `seed_demo_data.py`: Maria $2,800 take-home, Yes, "SNAP (food stamps)"; DeShawn $3,050, No; Sarah $1,750, No; DeShawn household size 2 and Priya 4, both `filing_type` `individual`; every persona's income in `monthly_gross_wages`.
  - The wizard's labels: the Income step's "Monthly Wages/Salary" box, and the Debtor step's "Household Size", "Filing Type" and "Individual (filing alone)".
- Produces:
  - Root `CLAUDE.md` (`AGENTS.md` and `GEMINI.md` are symlinks to it):
    - rewritten gotchas: "Nested debts and assets save by id" (drops `is_secured` from the fields the browser never receives, and adds the contracts and codebtors whole-list save), "The packet decides which forms a filer gets", "GenerateAll vs single" and "Known form defects are strict xfails";
    - "Income is stored by source", which replaces "Income stores only the 6-month array";
    - new gotchas: "Forms need a completed intake", "Autosave sends only real edits" and "The fee-waiver application";
    - the file map gains a line for `apps/eligibility/cmi.py` (`current_monthly_income`, `IncomeNotSplit`, `is_above_median`), and its `SOFAStep.tsx` / `FeeWaiverPage.tsx` line says the fee-waiver page continues to `/sofa`.
  - The five persona briefs (DIG-141): each monthly income figure says "before taxes", and its table row names the Income step box it goes in; the three fee-waiver personas gain a take-home line and the fee-waiver page's two answers; DeShawn's and Priya's figures are their own income.
  - Comment-only changes in `backend/apps/intake/serializers.py` and `backend/apps/intake/tests/test_completion.py`, and a pointer at the end of the step 1 spec's "Why not `above_median_calculated`" bullet.
  - No code, test or behaviour changes. `known_defects.json` is untouched.

**Decisions already made in this task:**

- **The reopening ruling, which `CLAUDE.md` now states:** every intake-data write sets a completed intake back to `in_progress` through `IntakeSession.reopen()`; form answers, SOFA and the fee-waiver application never reopen it.
- **The Income step's help text ruling, which `CLAUDE.md` now states:** a filer with no income at all enters $0 in one box, because the means test refuses an intake with all ten boxes blank (`IncomeNotSplit`).
- **Take-home lines go to Maria, DeShawn and Sarah only.** §5.7 gives take-home figures only for the three fee-waiver personas, and James and Priya never reach the fee-waiver page. Don't invent figures for them.
- **The three fee-waiver briefs' tables also carry the fee-waiver page's two answers,** with the seeds' values: Maria $2,800 and "Yes. What kind? SNAP (food stamps)"; DeShawn $3,050 and No; Sarah $1,750 and No. The page refuses to submit without the non-cash answer, and the table is what a persona agent types.
- **Every brief's income row says "before taxes" and names its box by the on-screen label,** "(Monthly Wages/Salary box)". The seeds (`_wages_only`) and the journeys put each persona's whole figure there. An unlabelled income row beside a take-home row is the ambiguity DIG-141 describes.
- **DeShawn's and Priya's figures are their own income,** not combined with their spouse's: they file alone, with the spouse counted in household size (spec §3, Q1). Their old row "Marital status | Married Filing Jointly" becomes three rows: "Marital status | Married", "Household Size | 2" (DeShawn) or "4" (Priya), and "Filing Type | Individual (filing alone)", in the Debtor step's own labels and with the seeds' values. Spec §3 settles this, so it is not an owner question.
- **Priya's backstory ("you work part-time as a tutor") is left as it is,** although it now sits beside "Your own monthly income before taxes: about $12,000". Rewriting her job is a persona decision for the owner.
- **Prettier realigns the tables of four briefs** (DeShawn, James, Maria and Sarah) that were never formatted before, and adds a blank line after **Assets:** and **Amounts Owed:**. No value changes. The pre-commit prettier hook would make the same change.
- **The step 1 spec gets a pointer only,** in the exact words the task note gave: the bullet now ends "Both are DIG-128 (fixed by the step 2 spec §5.6, DIG-128)." The doubled DIG-128 is those words; leave it. Nothing else in the step 1 spec changes.
- **The two Expenses comments are reworded only.** The server contract they guard is unchanged: an empty body still creates the record with its $0 defaults (DIG-153).
- **`CLAUDE.md` says more than §5.8's minimum list.** Each addition is a statement 2a made false or incomplete in a way an agent would act on: the contracts and codebtors whole-list save (Task 4), the fee-waiver page continuing to `/sofa` (Task 7), the recorder sentence, Generate and Regenerate refusing on the completion check and the means test before `FormIsFiled` (asked for by Task 11's review), and the interim prints until 2b (Schedule I lines 3, 10 and 12, Schedule J 23a, and 103B's `4 type` and `5 Type` at 0.00).
- **The interim 103B 0.00 note goes in `CLAUDE.md`, not in the step 2 spec's §5.1,** which this task doesn't touch.
- **The sworn "No" is stated as taking effect once 2b binds 103B line 3.** In 2a no binding reads the new fee-waiver columns.
- **Three `CLAUDE.md` sentences are exact on purpose; don't loosen them:**
  - a filed form keeps its place in Generate All's `generated` while it is in the packet, and comes after the packet's forms only once it has left it;
  - cleared known defects are deleted by hand because a green suite proves the list exact (a strict XPASS, and the orphan test), and deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list;
  - a zero-income fixture sets one income amount to 0, not all ten to null.
- **Not in this task:** the verification-addendum gotcha, which is 2b's. `README.md`, `docs/testing/persona-briefs/README.md`, the docstring of `test_oracle_tier3.py`, `test_registry.py`'s `test_122a2_ignores_the_sticky_above_median_flag`, `docs/UPL_COMPLIANCE.md` and `docs/PLAIN_LANGUAGE_GUIDE.md` keep stale lines outside §5.8; they are listed for the owner. The task note's "`CLAUDE.md` :94" meant line 94 of the historical step 1 plan, which stays as written; `CLAUDE.md`'s own line 94 is still true.
- **The journeys run on this task although only documentation changes,** because this task leaves the branch's final tree.

- [ ] **Step 1: Say in each persona brief which figure is before taxes, which is take-home, and whose it is**

```bash
git apply <<'PATCH'
diff --git a/docs/testing/persona-briefs/deshawn-mitchell.md b/docs/testing/persona-briefs/deshawn-mitchell.md
index c05b052..2e7a333 100644
--- a/docs/testing/persona-briefs/deshawn-mitchell.md
+++ b/docs/testing/persona-briefs/deshawn-mitchell.md
@@ -6,7 +6,8 @@ You ARE DeShawn Mitchell. Navigate DigniFi as he would.

 - 45 years old, married, no children
 - Work as a warehouse supervisor on the South Side
-- Combined monthly take-home with spouse: about $3,500
+- Your own monthly income before taxes: about $3,500 (your wife's income is not part of it)
+- Your own monthly take-home pay (after taxes and payroll deductions): about $3,050
 - Own a single-family home on S Sangamon St ($180k value, $160k mortgage)
 - Drive a 2012 Ford F-150 (paid off) and have a small 401(k) ($12,000)

@@ -36,36 +37,42 @@ You ARE DeShawn Mitchell. Navigate DigniFi as he would.

 ## Your Data (enter this exactly)

-| Field | Value |
-|-------|-------|
-| First name | DeShawn |
-| Middle name | R |
-| Last name | Mitchell |
-| SSN | 900-44-0004 |
-| Date of birth | 09/03/1980 |
-| Phone | 312-555-0404 |
-| Email | deshawn.mitchell@demo.dignifi.org |
-| Address | 7823 S Sangamon St, Chicago, IL 60620 |
-| Marital status | Married Filing Jointly |
-| Dependents | 0 |
-| Monthly income | $3,500 |
-| Mortgage | $1,200 |
-| Utilities | $200 |
-| Home maintenance | $100 |
-| Vehicle insurance | $95 |
-| Vehicle maintenance | $50 |
-| Food | $350 |
-| Clothing | $50 |
-| Medical | $60 |
-| Insurance (not deducted) | $150 |
-| Other expenses | $40 |
+| Field                                                           | Value                                 |
+| --------------------------------------------------------------- | ------------------------------------- |
+| First name                                                      | DeShawn                               |
+| Middle name                                                     | R                                     |
+| Last name                                                       | Mitchell                              |
+| SSN                                                             | 900-44-0004                           |
+| Date of birth                                                   | 09/03/1980                            |
+| Phone                                                           | 312-555-0404                          |
+| Email                                                           | deshawn.mitchell@demo.dignifi.org     |
+| Address                                                         | 7823 S Sangamon St, Chicago, IL 60620 |
+| Marital status                                                  | Married                               |
+| Household Size                                                  | 2                                     |
+| Filing Type                                                     | Individual (filing alone)             |
+| Dependents                                                      | 0                                     |
+| Your own monthly income before taxes (Monthly Wages/Salary box) | $3,500                                |
+| Mortgage                                                        | $1,200                                |
+| Utilities                                                       | $200                                  |
+| Home maintenance                                                | $100                                  |
+| Vehicle insurance                                               | $95                                   |
+| Vehicle maintenance                                             | $50                                   |
+| Food                                                            | $350                                  |
+| Clothing                                                        | $50                                   |
+| Medical                                                         | $60                                   |
+| Insurance (not deducted)                                        | $150                                  |
+| Other expenses                                                  | $40                                   |
+| Your own take-home pay (fee waiver page)                        | $3,050                                |
+| Non-cash help from the government (fee waiver page)             | No                                    |

 **Assets:**
+
 - Single-family home, 7823 S Sangamon — value $180,000, owed $160,000
 - 2012 Ford F-150 — value $8,000, owed $0
 - 401(k) at Fidelity — $12,000

 **Amounts Owed:**
+
 - Wells Fargo Home Mortgage — $160,000, paying $1,200/mo (secured by home)
 - Midland Credit Management credit card — $6,700, paying $0 (in collections)
 - ComEd utility — $800, paying $0 (in collections)
diff --git a/docs/testing/persona-briefs/james-washington.md b/docs/testing/persona-briefs/james-washington.md
index 13fae84..4243eef 100644
--- a/docs/testing/persona-briefs/james-washington.md
+++ b/docs/testing/persona-briefs/james-washington.md
@@ -6,7 +6,7 @@ You ARE James Washington. Navigate DigniFi as he would.

 - 50 years old, single, no children
 - Work as a maintenance technician at a downtown hotel
-- Monthly take-home: about $5,833 (annual ~$70,000)
+- Monthly income before taxes: about $5,833 (annual ~$70,000)
 - Live alone in a studio apartment on the Near North Side
 - Drive a 2019 Toyota Camry with $8,500 still owed

@@ -36,35 +36,37 @@ You ARE James Washington. Navigate DigniFi as he would.

 ## Your Data (enter this exactly)

-| Field | Value |
-|-------|-------|
-| First name | James |
-| Middle name | D |
-| Last name | Washington |
-| SSN | 900-22-0002 |
-| Date of birth | 03/22/1975 |
-| Phone | 312-555-0202 |
-| Email | james.washington@demo.dignifi.org |
-| Address | 850 N State St Apt 1204, Chicago, IL 60610 |
-| Marital status | Single |
-| Dependents | 0 |
-| Monthly income | $5,833 |
-| Rent | $1,650 |
-| Utilities | $120 |
-| Vehicle payment | $350 |
-| Vehicle insurance | $110 |
-| Vehicle maintenance | $50 |
-| Food | $400 |
-| Clothing | $80 |
-| Medical | $50 |
-| Insurance (not deducted) | $200 |
-| Other expenses | $100 |
+| Field                                                  | Value                                      |
+| ------------------------------------------------------ | ------------------------------------------ |
+| First name                                             | James                                      |
+| Middle name                                            | D                                          |
+| Last name                                              | Washington                                 |
+| SSN                                                    | 900-22-0002                                |
+| Date of birth                                          | 03/22/1975                                 |
+| Phone                                                  | 312-555-0202                               |
+| Email                                                  | james.washington@demo.dignifi.org          |
+| Address                                                | 850 N State St Apt 1204, Chicago, IL 60610 |
+| Marital status                                         | Single                                     |
+| Dependents                                             | 0                                          |
+| Monthly income before taxes (Monthly Wages/Salary box) | $5,833                                     |
+| Rent                                                   | $1,650                                     |
+| Utilities                                              | $120                                       |
+| Vehicle payment                                        | $350                                       |
+| Vehicle insurance                                      | $110                                       |
+| Vehicle maintenance                                    | $50                                        |
+| Food                                                   | $400                                       |
+| Clothing                                               | $80                                        |
+| Medical                                                | $50                                        |
+| Insurance (not deducted)                               | $200                                       |
+| Other expenses                                         | $100                                       |

 **Assets:**
+
 - 2019 Toyota Camry — value $14,000, owed $8,500
 - Bank of America checking — $1,200

 **Amounts Owed:**
+
 - Citibank credit card — $9,800, paying $200/mo
 - Toyota Financial Services auto loan — $8,500, paying $350/mo (secured by vehicle)

diff --git a/docs/testing/persona-briefs/maria-torres.md b/docs/testing/persona-briefs/maria-torres.md
index deb36f6..06a3e62 100644
--- a/docs/testing/persona-briefs/maria-torres.md
+++ b/docs/testing/persona-briefs/maria-torres.md
@@ -6,7 +6,8 @@ You ARE Maria Torres. Navigate DigniFi as she would.

 - 36 years old, single mother of two (ages 8 and 5)
 - Work two jobs: daytime cashier at Walgreens, evening shift at a restaurant
-- Monthly take-home: about $3,200
+- Monthly income before taxes: about $3,200
+- Monthly take-home pay (after taxes and payroll deductions): about $2,800
 - Live in a 2-bedroom apartment in Wicker Park, Chicago
 - Have a 2015 Honda Civic (paid off) that you need for getting kids to school

@@ -35,34 +36,38 @@ You ARE Maria Torres. Navigate DigniFi as she would.

 ## Your Data (enter this exactly)

-| Field | Value |
-|-------|-------|
-| First name | Maria |
-| Last name | Torres |
-| SSN | 900-11-0001 |
-| Date of birth | 06/15/1988 |
-| Phone | 312-555-0101 |
-| Email | maria.torres@demo.dignifi.org |
-| Address | 2145 W Division St Apt 3, Chicago, IL 60622 |
-| Marital status | Single |
-| Dependents | 2 |
-| Monthly income | $3,200 |
-| Rent | $1,100 |
-| Utilities | $180 |
-| Vehicle insurance | $85 |
-| Vehicle maintenance | $40 |
-| Food | $450 |
-| Clothing | $60 |
-| Medical | $75 |
-| Childcare | $400 |
-| Insurance (not deducted) | $120 |
-| Other expenses | $50 |
+| Field                                                  | Value                                       |
+| ------------------------------------------------------ | ------------------------------------------- |
+| First name                                             | Maria                                       |
+| Last name                                              | Torres                                      |
+| SSN                                                    | 900-11-0001                                 |
+| Date of birth                                          | 06/15/1988                                  |
+| Phone                                                  | 312-555-0101                                |
+| Email                                                  | maria.torres@demo.dignifi.org               |
+| Address                                                | 2145 W Division St Apt 3, Chicago, IL 60622 |
+| Marital status                                         | Single                                      |
+| Dependents                                             | 2                                           |
+| Monthly income before taxes (Monthly Wages/Salary box) | $3,200                                      |
+| Rent                                                   | $1,100                                      |
+| Utilities                                              | $180                                        |
+| Vehicle insurance                                      | $85                                         |
+| Vehicle maintenance                                    | $40                                         |
+| Food                                                   | $450                                        |
+| Clothing                                               | $60                                         |
+| Medical                                                | $75                                         |
+| Childcare                                              | $400                                        |
+| Insurance (not deducted)                               | $120                                        |
+| Other expenses                                         | $50                                         |
+| Take-home pay (fee waiver page)                        | $2,800                                      |
+| Non-cash help from the government (fee waiver page)    | Yes. What kind? SNAP (food stamps)          |

 **Assets:**
+
 - 2015 Honda Civic — value $6,500, owed $0
 - Chase checking account — $340

 **Amounts Owed:**
+
 - Capital One credit card — $4,200, paying $85/mo (in collections)
 - Northwestern Memorial Hospital — $12,800, paying $0 (in collections)
 - Discover Financial personal loan — $3,500, paying $120/mo
diff --git a/docs/testing/persona-briefs/priya-sharma.md b/docs/testing/persona-briefs/priya-sharma.md
index 85e6b6b..7459876 100644
--- a/docs/testing/persona-briefs/priya-sharma.md
+++ b/docs/testing/persona-briefs/priya-sharma.md
@@ -6,7 +6,7 @@ You ARE Priya Sharma. Navigate DigniFi as she would.

 - 43 years old, married with two children (ages 10 and 7)
 - Husband works as a software engineer; you work part-time as a tutor
-- Combined monthly take-home: about $12,000 (annual ~$144,000)
+- Your own monthly income before taxes: about $12,000 (annual ~$144,000; your husband's income is not part of it)
 - Live in Lincoln Park — a nice neighborhood, but the medical bills are crushing
 - Your daughter had a complicated surgery and recovery ($35,000 in medical debt)

@@ -36,30 +36,32 @@ You ARE Priya Sharma. Navigate DigniFi as she would.

 ## Your Data (enter this exactly)

-| Field                    | Value                                   |
-| ------------------------ | --------------------------------------- |
-| First name               | Priya                                   |
-| Last name                | Sharma                                  |
-| SSN                      | 900-33-0003                             |
-| Date of birth            | 11/08/1982                              |
-| Phone                    | 312-555-0303                            |
-| Email                    | priya.sharma@demo.dignifi.org           |
-| Address                  | 456 W Fullerton Pkwy, Chicago, IL 60614 |
-| Marital status           | Married Filing Jointly                  |
-| Dependents               | 2                                       |
-| Monthly income           | $12,000                                 |
-| Rent/mortgage            | $2,800                                  |
-| Utilities                | $250                                    |
-| Home maintenance         | $100                                    |
-| Vehicle payment          | $450                                    |
-| Vehicle insurance        | $180                                    |
-| Vehicle maintenance      | $60                                     |
-| Food                     | $800                                    |
-| Clothing                 | $150                                    |
-| Medical                  | $100                                    |
-| Childcare                | $1,200                                  |
-| Insurance (not deducted) | $350                                    |
-| Other expenses           | $200                                    |
+| Field                                                           | Value                                   |
+| --------------------------------------------------------------- | --------------------------------------- |
+| First name                                                      | Priya                                   |
+| Last name                                                       | Sharma                                  |
+| SSN                                                             | 900-33-0003                             |
+| Date of birth                                                   | 11/08/1982                              |
+| Phone                                                           | 312-555-0303                            |
+| Email                                                           | priya.sharma@demo.dignifi.org           |
+| Address                                                         | 456 W Fullerton Pkwy, Chicago, IL 60614 |
+| Marital status                                                  | Married                                 |
+| Household Size                                                  | 4                                       |
+| Filing Type                                                     | Individual (filing alone)               |
+| Dependents                                                      | 2                                       |
+| Your own monthly income before taxes (Monthly Wages/Salary box) | $12,000                                 |
+| Rent/mortgage                                                   | $2,800                                  |
+| Utilities                                                       | $250                                    |
+| Home maintenance                                                | $100                                    |
+| Vehicle payment                                                 | $450                                    |
+| Vehicle insurance                                               | $180                                    |
+| Vehicle maintenance                                             | $60                                     |
+| Food                                                            | $800                                    |
+| Clothing                                                        | $150                                    |
+| Medical                                                         | $100                                    |
+| Childcare                                                       | $1,200                                  |
+| Insurance (not deducted)                                        | $350                                    |
+| Other expenses                                                  | $200                                    |

 **Assets:**

diff --git a/docs/testing/persona-briefs/sarah-chen.md b/docs/testing/persona-briefs/sarah-chen.md
index 732d75f..9272eee 100644
--- a/docs/testing/persona-briefs/sarah-chen.md
+++ b/docs/testing/persona-briefs/sarah-chen.md
@@ -6,7 +6,8 @@ You ARE Sarah Chen. Navigate DigniFi as she would.

 - 31 years old, single, no children
 - Work part-time at a bookstore while looking for full-time work
-- Monthly take-home: about $2,000
+- Monthly income before taxes: about $2,000
+- Monthly take-home pay (after taxes and payroll deductions): about $1,750
 - Live in a shared apartment in Wicker Park (your name is on the lease)
 - No car, no savings, no property — just student loans and a medical bill

@@ -36,29 +37,33 @@ You ARE Sarah Chen. Navigate DigniFi as she would.

 ## Your Data (enter this exactly)

-| Field | Value |
-|-------|-------|
-| First name | Sarah |
-| Last name | Chen |
-| SSN | 900-55-0005 |
-| Date of birth | 01/20/1995 |
-| Phone | 312-555-0505 |
-| Email | sarah.chen@demo.dignifi.org |
-| Address | 1520 N Damen Ave Apt 2F, Chicago, IL 60622 |
-| Marital status | Single |
-| Dependents | 0 |
-| Monthly income | $2,000 |
-| Rent | $850 |
-| Utilities | $80 |
-| Food | $250 |
-| Clothing | $30 |
-| Medical | $20 |
-| Other expenses | $50 |
+| Field                                                  | Value                                      |
+| ------------------------------------------------------ | ------------------------------------------ |
+| First name                                             | Sarah                                      |
+| Last name                                              | Chen                                       |
+| SSN                                                    | 900-55-0005                                |
+| Date of birth                                          | 01/20/1995                                 |
+| Phone                                                  | 312-555-0505                               |
+| Email                                                  | sarah.chen@demo.dignifi.org                |
+| Address                                                | 1520 N Damen Ave Apt 2F, Chicago, IL 60622 |
+| Marital status                                         | Single                                     |
+| Dependents                                             | 0                                          |
+| Monthly income before taxes (Monthly Wages/Salary box) | $2,000                                     |
+| Rent                                                   | $850                                       |
+| Utilities                                              | $80                                        |
+| Food                                                   | $250                                       |
+| Clothing                                               | $30                                        |
+| Medical                                                | $20                                        |
+| Other expenses                                         | $50                                        |
+| Take-home pay (fee waiver page)                        | $1,750                                     |
+| Non-cash help from the government (fee waiver page)    | No                                         |

 **Assets:**
+
 - None

 **Amounts Owed:**
+
 - Navient student loan — $28,000, paying $0
 - University of Illinois Hospital medical — $3,400, paying $0 (in collections)

PATCH
```

DIG-141 (§5.8): each "take-home" line becomes "before taxes", per Q1, and the three fee-waiver personas gain a separate take-home line with the figures the fee-waiver page now asks for; the married personas' briefs say the figure is their own income.

- [ ] **Step 2: Rewrite the CLAUDE.md gotchas 2a made false**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 315ea55..0f35b9e 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -23,16 +23,17 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **React 19 + navigate()** — calling `navigate()` in render body crashes the reconciler. Use `useEffect`.
 - **Vite HMR in Docker** — type/structure changes don't hot-reload; restart the frontend container.
 - **Enum mismatches are silent** — frontend/backend enum drift only surfaces at runtime; check both when adding fields.
-- **Nested debts and assets save by id** — `IntakeSessionSerializer.update` upserts `debts`/`assets` through `_save_rows_by_id`: a row carrying one of this session's ids updates only the keys it sends, a row without one (or with an unknown or foreign id) is created on this session, and a stored row missing from the payload is **deleted**, so send every row you want to keep. A nested `session` is ignored. Fields the browser never receives (`account_number`, `source_document`, `is_secured`) survive a re-save. `DebtViewSet`/`AssetViewSet` keep the base serializers, so per-item create never takes a client id.
+- **Nested debts and assets save by id** — `IntakeSessionSerializer.update` upserts `debts`/`assets` through `_save_rows_by_id`: a row carrying one of this session's ids updates only the keys it sends, a row without one (or with an unknown or foreign id) is created on this session, and a stored row missing from the payload is **deleted**, so send every row you want to keep. A nested `session` is ignored. Fields the browser never receives (`account_number`, `source_document`) survive a re-save. `DebtViewSet`/`AssetViewSet` keep the base serializers, so per-item create never takes a client id. Contracts and codebtors save the same way, as a whole list: `PUT /intake/sessions/{id}/contracts/` (or `codebtors/`) checks every row before writing any, and an empty list deletes every stored row. The wizard sends each list on Continue from steps 6 and 7, and reads both with the session before any step shows, so a list that failed to load is never saved as empty.
 - **Debt and asset amounts are readable, as strings** — the owner gets `DebtInfo.amount_owed` and `AssetInfo.current_value`/`amount_owed` back (SSN and `account_number` stay write-only). DRF sends decimals as strings (`"2500.00"`), so the wizard converts them with `hydrateAmounts` (`utils/parseAmount.ts`) as session data enters step state; a raw string in a step's `reduce` joins as text (`$02500.00100.50`). A stored amount wider than `DecimalField(12, 2)` makes every read of that session 500, so every write path must bound it (`DraftDebtCreator` stores it as 0; documents `validate` returns 400).
 - **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data.
 - **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
-- **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 ≥ median_income_threshold` (never `above_median_calculated`, which is sticky, DIG-128); 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words; any other failure is a 500 logged by exception type only.
+- **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 > median_income_threshold`, through `is_above_median` (`apps/eligibility/cmi.py`), the means test's own comparison, so income exactly at the median counts as below (DIG-136). Never read `above_median_calculated`: a row calculated before DIG-128 was fixed can still carry a stale True. 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. Generate All, Generate, Regenerate, the download of an unfiled form and the packet list of a completed intake work the means test out again from the stored intake first (`_recalculate_means_test` in `apps/forms/views.py`), so a stale `MeansTest` row never decides the packet (DIG-160); an unfinished intake's packet list reads the stored row. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words, and so is income not entered by source (`IncomeNotSplit`); any other failure, missing district median data included, is a 500 logged by exception type only.
+- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district that has median data, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
-- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. `generate_all` covers only the packet and deletes the rows of forms that no longer apply. A form marked filed keeps its stored answers: `generate` and `regenerate` return 422 for it, and `generate_all` leaves it untouched and returns it in `generated`. `GET /api/forms/packet/?session=<id>` returns `{session, form_types}` in filing order, and the dashboard renders from it.
+- **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type`: Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source (422) or missing median data (500). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types}` in filing order, and the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
 - **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: template hash, full names, widget types, export states, `/Opt` values, duplicate bindings, TBD). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box, `{}` is unmapped and prints nothing.
-- **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails today, each with its DIG ticket. Fixing a defect turns its xfail into a failure until you delete the entry. Regenerate it with `data/forms/field_index/tools/record_known_defects.py` (usage in its docstring) and review the diff by hand.
+- **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails today, each with its DIG ticket. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, and the API never returns it. `form_data` is blank; its column is dropped one release after this code is live. A filed form downloads its stored `field_values`; an unfiled one is resolved fresh on every download.
 - **Analytics auth** — `trackEvent()` must use `getAccessToken()` for Bearer header, not raw fetch.
 - **heroku.yml release** — must be one command string (not argv list). `heroku releases:output` is empty; use `heroku logs --dyno release`.
@@ -59,11 +60,13 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **`extract()` takes a list of page images** — `BaseOCRProvider.extract(images: list[bytes], prompt)`: `[]` means text mode, a photo upload is a one-item list, and pages go in page order (one OpenAI `image_url` part or one Gemini inline part each). `classify()` still takes bytes. Never hand a provider `[]` for a scan.
 - **An empty OpenAI reply raises `EmptyModelReply`** — `OpenAIProvider._complete` retries a blank or whitespace-only reply once, but never a refusal or `finish_reason == "content_filter"`. The error names `finish_reason` and whether a refusal was present, never its text. `_parse_result` records only the reply's length ("model reply was not valid JSON (N characters)"), so `error_message` never holds model output. Gemini still returns `""` (DIG-35).
 - **The wizard re-reads the session on every mount** — `IntakeWizard` fixes the session id at mount (context session, else `current_session_id`), calls `loadSession(id)`, and renders no step until it returns, so steps and autosave start from server data, not the context copy (which predates any upload on `/documents`). A failed read shows a "Try again" alert for the same id; a 404 starts a new session. `loadSession`/`createSession` resolve with the session, and `loadSession` clears `current_session_id` only on a 404, but the provider's own startup load still clears it on any error (DIG-11).
+- **Autosave sends only real edits** — `useAutoSave` compares the step's PATCH body (`currentStepBody` in `IntakeWizard`) as JSON with that step's last saved or loaded copy (the first body seen under a step's name) and skips an equal one, so showing a step again (Go Back) sends nothing and doesn't reopen a completed intake. A body must therefore be built the same way from loaded data as from edited data: leave out read-only totals and echoed fields, or every visit saves. Continue (`saveNow`) always saves. Steps 6 and 7 have no body there; their lists save only on Continue.
 - **An empty scan is FAILED, not done** — `documents/views._record_findings` judges each type: a bill needs a creditor name, a pay stub must pass `PayStubExtraction`, the check the income aggregate applies (gross pay + both pay-period dates required; an invalid optional field such as a negative `net_pay` also fails it), a credit report needs one readable tradeline. Otherwise `OCRResult.status="failed"`, `failure_reason="nothing_found"`; any exception is `processing_error`. A bill with a creditor but no readable balance is `completed` with a $0 draft; a report of only $0 accounts is `completed` with no debts. Other document types are not judged.
 - **The documents API never returns `error_message` or `extracted_data`** — `_serialize_ocr` returns `status`, `failure_reason`, `confidence_scores`, `overall_confidence`, `user_validated`. `error_message` is operations-only (exception class, `finish_reason`); read it in a Django shell. The pipeline's catch-all handlers (`_run_processing`, `AggregateIngestionService.recalculate`) log only the exception's type with `logger.error`, never `logger.exception`: logs reach Sentry, and a DB error's DETAIL quotes row values (DIG-105).
 - **Scanned amounts are bounded** — `draft_debt._bounded_amount` stores a non-numeric, negative, non-finite or ≥1e10 balance as 0, and `TradelineItem.amount_owed` has `le=9999999999.99`: a wider value makes `DecimalField(12,2)` raise on every read of the session.
 - **Prompt hints are per type and shared** — `_FIELD_HINTS` in `documents/services/providers/prompts/image_extraction.py` feeds both the vision and the text prompt (`text_extraction.py` imports it). A type with no hint is asked for "all visible fields as key-value pairs" and never returns the keys its importer reads; the `CREDIT_REPORT` hint's keys must stay in step with `TradelineItem`, and `test_prompts.py` checks that they do.
-- **Income stores only the 6-month array** — `IncomeInfo.monthly_income` is canonical (means test, Schedule I, 122A-1); the Income step's ten per-source boxes are never stored. The API adds read-only `total_monthly_income` (the mean of the stored months, to the cent). `IncomeInfoStep` switches to per-source amounts only when a source key is _present_ in its data; otherwise it re-emits the stored months unchanged. The wizard saves `{income_info: {monthly_income}}` only, because echoing a wizard-created row's blank `marital_status` back is a 400.
+- **Income is stored by source** — `IncomeInfo` holds the Income step's ten amounts (`IncomeInfo.SOURCE_FIELDS`, `monthly_gross_wages` … `monthly_other_income`), each nullable with no default: an amount the filer never gave stays NULL, because a $0 default would pass every earlier filer's means test. The old six-month `monthly_income` is read-only and no longer written; it stays one release, and a filer who has only that total is asked on the Income step to split it. CMI is one function, `current_monthly_income` in `apps/eligibility/cmi.py`, used by the means test, the above-median calculator and the forms' `cmi` rule: the ten without Social Security (DIG-49), an empty one counting as zero once another was given, rounded to the cent half-even. With all ten empty it raises `IncomeNotSplit` ("Enter your income by source on the Income step."): a 422 from the forms views, a 400 from `calculate_means_test`. So a filer with no income at all enters $0 in one box, as the Income step's help text says, and a zero-income fixture sets one amount to 0, not all ten to null. The API's read-only `total_monthly_income` is the ten added up, Social Security included, or null. The wizard loads the ten through `hydrateAmounts` and saves `{income_info: {<the ten>}}` alone, a blank box as null, never $0 unless typed: echoing a wizard-created row's blank `marital_status` back is a 400. Until 2b moves the bindings, Schedule I line 3 prints wages and tips, and Schedule I lines 10 and 12 and Schedule J 23a print CMI, so they leave out Social Security.
+- **The fee-waiver application** — `FeeWaiverApplication.monthly_take_home_pay` (encrypted, zero or more; 103B line 2) and `receives_noncash_assistance` (`BooleanField(null=True)`; 103B line 3) have no defaults and stay empty until the filer answers. Once 2b binds line 3, an empty answer prints blank and a stored False prints a sworn "No", so never default it. `benefit_types` holds the "What kind?" answer: required with Yes, `[]` with No. Creating one requires both answers (400 otherwise). `monthly_income`, `monthly_expenses` and `receives_public_benefits` are no longer written and stay one release. `GET /api/intake/fee-waiver/?session=<id>` reads one session's application and never creates one, since an application puts 103B in the packet; the page opens with it, so saved answers win over pre-fills, and take-home pay is never pre-filled. A PATCH can't move an application to another user's session (DIG-178). Until 2b, nothing prints the new columns, and 103B's `4 type` and `5 Type` print 0.00 from the empty old columns (DIG-78).
 - **Expense names are the backend's** — the Expenses step and the wizard's hydration use `EXPENSE_FIELDS` (`types/api.ts`), the 13 `ExpenseInfo` names that Schedule J, 122A-2 and the means test read; the E2E page object fills `input[name=<key>]` from the personas' canonical keys. DRF drops any other name silently: the old frontend names (`car_payment`, `food_groceries`, `other_necessary_expenses`, ...) saved as $0 until DIG-45. The API returns these amounts as decimal strings; the wizard converts them with `hydrateAmounts` when it loads the session.
 - **Upload areas decide the document type** — `DocumentUploadPage`'s `UPLOAD_AREAS` maps "Bills and statements" → `creditor_bill`, "Pay stubs" → `pay_stub`, "Credit report" → `credit_report`. The backend stores whatever type is sent (`user_declared_type`) and never classifies. Each `FileDropZone` is named `${label}: drop files here or click to upload` with its file input inside.
 - **MSW can't parse jsdom uploads with `request.formData()`** — undici rejects jsdom's `File`, so the read fails. Read multipart fields from `await request.text()`, as `sentDocumentType` in `DocumentUploadPage.test.tsx` does.
@@ -93,6 +96,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - `apps/intake/serializers.py` — nested serializers; DRF silently drops unknown fields (mismatch with frontend)
 - `apps/intake/management/commands/seed_demo_data.py` — 5 AI personas
 - `apps/eligibility/services/means_test_calculator.py` — § 707(b) logic, annualizes CMI
+- `apps/eligibility/cmi.py` — `current_monthly_income` (the one CMI), `IncomeNotSplit`, `is_above_median`
 - `apps/forms/registry.py` — `FORM_REGISTRY` (17 form_type → `PacketForm(applies, requires)`) in filing order, `packet()`, `build_field_values()`
 - `apps/forms/services/` — `pdf_filler.py` (`PDFFormFiller`, exact full names), `fill_resolver.py` + `derivations.py` (schema-driven fill engine)
 - `apps/forms/field_index.py` + `apps/forms/checks.py` — the field index loader and the schema system check
@@ -113,7 +117,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - `src/pages/IntakeWizard.tsx` — 8-step wizard orchestrator (`WIZARD_STEPS`: debtor_info, income_info, expense_info, assets, debts, contracts, codebtors, review); detours to `/documents` after step 1
 - `src/pages/DocumentUploadPage.tsx` — upload + OCR queue; auto-creates a session if none exists
 - `src/pages/FormDashboard.tsx` — Generate All, download, mark filed
-- `src/pages/SOFAStep.tsx` (`/sofa`), `FeeWaiverPage.tsx` (`/fee-waiver`) — post-intake branches; `handleComplete` routes to one or the other on `qualifies_for_fee_waiver`
+- `src/pages/SOFAStep.tsx` (`/sofa`), `FeeWaiverPage.tsx` (`/fee-waiver`) — post-intake pages; `handleComplete` routes to one or the other on `qualifies_for_fee_waiver`, and the fee-waiver page continues to `/sofa`
 - `src/pages/AskModulePage.tsx` — `/ask/:formType`
 - `src/pages/LandingPage.tsx`, `LoginPage.tsx`, `RegisterPage.tsx`, `TermsPage.tsx` — public routes; all three auth entry points send authenticated users to `/intake`
 - `src/components/compliance/UPLConfirmationModal.tsx` — gates form generation
PATCH
```

The gotchas now describe 2a (§5.8): income stored per source with one CMI that leaves out Social Security; the 122A-2 rule (`>`, recalculated at generate); the completion check and the writes that reopen a completed intake; Generate All keeping filed forms, and their downloads; the fee-waiver columns; tier 2 keyed on the binding; autosave skipping unchanged saves; and contracts and codebtors saved as whole lists.

- [ ] **Step 3: Reword the two Expenses comments, and point the step 1 spec at the fix**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/serializers.py b/backend/apps/intake/serializers.py
index 0a06e9f..12fec49 100644
--- a/backend/apps/intake/serializers.py
+++ b/backend/apps/intake/serializers.py
@@ -357,8 +357,8 @@ class IntakeSessionSerializer(serializers.ModelSerializer):
         if income_data:
             IncomeInfo.objects.update_or_create(session=instance, defaults=income_data)

-        # Every box left blank arrives as {}, and still creates the record with its $0
-        # defaults, so the filer can complete (DIG-153).
+        # An empty body still creates the record with its $0 defaults, so the filer can
+        # complete (DIG-153). The wizard sends all 13 amounts, a blank box as 0.
         if expense_data is not None:
             ExpenseInfo.objects.update_or_create(session=instance, defaults=expense_data)

diff --git a/backend/apps/intake/tests/test_completion.py b/backend/apps/intake/tests/test_completion.py
index 0e20e2b..bdb54dc 100644
--- a/backend/apps/intake/tests/test_completion.py
+++ b/backend/apps/intake/tests/test_completion.py
@@ -138,8 +138,8 @@ def test_wizard_step_must_be_one_of_the_eight_steps(filer, completed, step):


 def test_filer_who_leaves_every_expense_blank_can_complete(filer, district):
-    # DIG-153: with every box blank, the Expenses step sends no amounts. The server drops the
-    # read-only total sent here, so this body is the same as the step's empty one.
+    # DIG-153: a body with no amounts still creates the record with its $0 defaults. The server
+    # drops the read-only total sent here. The wizard sends all 13 amounts, a blank box as 0.
     client, user = filer
     session = IntakeSession.objects.create(user=user, district=district, current_step=3)
     DebtorInfo.objects.create(
diff --git a/docs/superpowers/specs/2026-10-10-forms-foundation-design.md b/docs/superpowers/specs/2026-10-10-forms-foundation-design.md
index 00250e7..bdfa91e 100644
--- a/docs/superpowers/specs/2026-10-10-forms-foundation-design.md
+++ b/docs/superpowers/specs/2026-10-10-forms-foundation-design.md
@@ -264,7 +264,7 @@ A plan step is complete only when a search for `Generator\b`, `get_generator`, `
 - **Later: 108.** It is added in step 3.
 - **Packet size.** A packet therefore holds 14 to 16 forms.
 - **Always a yes or no.** `applies` never raises. `packet` therefore always returns a list, and generate-all deletes a stored 122A-2 row whenever `applies` is false.
-- **Why not `above_median_calculated`.** That flag is sticky: `calculate()` sets it true and never resets it, and the wizard's live preview saves calculations during intake. A filer who briefly entered above-median income would keep 122A-2 for good. The same code also gives above-median filers who pass the expense test the below-median message. Both are DIG-128.
+- **Why not `above_median_calculated`.** That flag is sticky: `calculate()` sets it true and never resets it, and the wizard's live preview saves calculations during intake. A filer who briefly entered above-median income would keep 122A-2 for good. The same code also gives above-median filers who pass the expense test the below-median message. Both are DIG-128 (fixed by the step 2 spec §5.6, DIG-128).
 - **Known inconsistency.** Line 13 of 122A-1 and `MeansTest` use different household sizes (DIG-51). Step 2 fixes that; until then, `applies` follows `MeansTest`, the figure the app already shows the filer.

 ### 5.7 Preconditions and the error contract
PATCH
```

Both comments said a blank Expenses save arrives as `{}`; since Task 6 the wizard sends all 13 amounts, a blank box as 0, and the comments now say so. Task 10 fixed both problems the step 1 spec's bullet describes, so the bullet now points to the step 2 spec.

- [ ] **Step 4: Check the edits**

Nothing can be red: this task changes only documentation and two comments, and no test reads either. This step checks that the pre-commit prettier hook won't rewrite the seven Markdown files, which the gates' `format:check` (`frontend/src` only) doesn't cover, and that the test whose comment changed still passes.

```bash
set -eo pipefail
frontend/node_modules/.bin/prettier --check \
  CLAUDE.md docs/superpowers/specs/2026-10-10-forms-foundation-design.md \
  docs/testing/persona-briefs/deshawn-mitchell.md docs/testing/persona-briefs/james-washington.md docs/testing/persona-briefs/maria-torres.md docs/testing/persona-briefs/priya-sharma.md docs/testing/persona-briefs/sarah-chen.md
source .claude/forms-step2a.env
cd backend && $PY -m pytest apps/intake/tests/test_completion.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `All matched files use Prettier code style!`, then `27 passed`.

- [ ] **Step 5: Run every gate**

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

Expected: `1776 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  320 passed (320)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 6: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 7: Commit**

```bash
set -eo pipefail
git add \
  CLAUDE.md \
  backend/apps/intake/serializers.py \
  backend/apps/intake/tests/test_completion.py \
  docs/superpowers/specs/2026-10-10-forms-foundation-design.md \
  docs/testing/persona-briefs/deshawn-mitchell.md \
  docs/testing/persona-briefs/james-washington.md \
  docs/testing/persona-briefs/maria-torres.md \
  docs/testing/persona-briefs/priya-sharma.md \
  docs/testing/persona-briefs/sarah-chen.md
git commit -F - <<'MSG'
docs: describe what forms step 2a changed, and say whose income each persona figure is

The persona briefs called each persona's monthly income "take-home", but
the Income step asks for income before taxes, and the means test and
Schedule I are worked out from it (DIG-141). Each brief now gives that
figure as income before taxes. Maria, DeShawn and Sarah, who apply for the
fee waiver, also get a separate take-home figure and their answer to the
non-cash help question, the two things the fee-waiver page now asks, as the
seeds hold them: $2,800 and SNAP, $3,050 and No, $1,750 and No. James and
Priya never reach that page and get no take-home figure. DeShawn's and
Priya's briefs say the figure is their own income, not their spouse's:
each files alone, with the spouse counted in household size (step 2 spec
§3, Q1). Their tables, which had said "Married Filing Jointly", now say
so in the Debtor step's own words, as the seeds hold them: Household
Size 2 for DeShawn and 4 for Priya, Filing Type "Individual (filing
alone)". Each brief's income row names the Income step box it goes in,
Monthly Wages/Salary, where the seeds and the journeys put it. Prettier
aligns the tables of the four briefs it had not formatted before.

CLAUDE.md's gotchas now describe 2a: income stored by source and the one
CMI without Social Security; the 122A-2 rule (`>`, through
is_above_median) and the means test worked out again before every packet;
forms only from a completed intake, and the writes that reopen one;
Generate All keeping filed forms, and their downloads; the fee-waiver
columns; tier 2 keyed on the binding; autosave skipping unchanged saves;
contracts and codebtors saved as whole lists. is_secured leaves the list
of fields the browser never receives. The file map gains
apps/eligibility/cmi.py and says the fee-waiver page continues to /sofa.

Two comments said a blank Expenses save arrives as {}; they now say the
wizard sends all 13 amounts, a blank box as 0. The server contract they
guard is unchanged. The step 1 spec's "Why not above_median_calculated"
bullet points to the step 2 spec, which fixed both of its DIG-128
problems.

Forms step 2a, commit 7 (step 2 spec §5.8).
MSG
git status --short
```
