# Forms Step 2b (Bindings) Implementation Plan, Part 2 of 2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put what the filer gave in the box that asks for it, leave a box blank where the filer gave nothing, and clear all 142 known defects. Step 1 checked every binding against the field index, and 2a made the data arrive intact. 2b moves the bindings.

**Architecture:** 2b changes the form schemas in `data/forms/schemas/`, the rules in `backend/apps/forms/services/derivations.py`, and the oracle's records: the tier 2 addendum `data/forms/field_index/audit/step2_verification.json`, tier 3's expectations and `backend/apps/forms/tests/known_defects.json`. Two other changes ride along. Task 6 makes the fee-waiver serializer keep only a non-cash answer the filer gave, before 103B prints it (DIG-193). Task 2 makes the Claude review check fail when the review posts nothing (DIG-144). Each of the 18 tasks is one commit, and every task boundary passes every gate.

**This part:** Tasks 10–18. It starts where Part 1 ends, with Tasks 1–9 committed on this branch. The other parts: Part 1 (`docs/superpowers/plans/2026-10-14-forms-step2b-part1.md`, Tasks 1–9). The plan is split only to stay under the repository's 500 KB file limit. Run all parts as one execution: one ledger for Tasks 1–18, and the whole-branch final review only after Task 18, because each part's patches expect each file exactly as the earlier tasks leave it.

**Tech Stack:** Django 5.0 + DRF (Python 3.11), pypdf 6.13.1, pytest + pytest-django; React 19 + TypeScript, vitest; Playwright; GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-12-forms-step2-design.md` (approved 2026-10-12). Read §6, §7.1–§7.5, §7.7, Appendix A (the forms your task changes), Appendix B, Appendix C and Appendix D before Task 1. It is the authority this plan argues from. 2a (§5) is merged as #19 (main `a8c266e`).

**How this plan was checked:**

- Each task's code was built and committed in order on the local branch `plan/forms-step2b`. Every task ended with every gate green, and an adversarial review approved each commit.
- The plan's author then amended four commits after their review and replayed the later commits on top. Task 1's recorder now reads every audit row on a box. Task 2's review workflow gained the jq default for refused calls, the exact summary heading, `--body-file` and `!cancelled()`. Task 10 deletes the three dead income rules and carries the pay-stub help text, moved in from Task 18. Task 18 corrects one CLAUDE.md sentence. The gates, the journeys and the dry-run checked these amendments, but no reviewer did. The whole-branch final review should read them.
- The plan was then dry-run from its own text in a fresh worktree, and after every task the tree matched the verified commit exactly.
- Final tree: backend `2094 passed, 1 xfailed`, vitest `358 passed`. Journeys: both runs passed 7 of 7 at every task that runs them (Tasks 6, 10, 17 and 18), in the build and in the dry-run. Once in the dry-run, Task 16's gate lost 3 vitest tests while outside work held the machine's load average at 144; vitest alone then passed 358 of 358 on the same tree, and Tasks 16–18 reran clean.

## Global Constraints

- **Single filer only.** Joint filing is out, and the wizard still offers it (DIG-177).
- **Blank or 0.00** (§6.1 B2): "A box prints 0.00 only when the filer gave that figure, or when it adds up figures they gave." "No rule turns a missing input into 0.00."
- **Expense lines** (§6.1, option A): "An expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0." Compare with `> 0`, never `!= 0`.
- **One binding per box** (E006). Re-rule a box in place by editing its field object; never add a second object for the same `pdf_field`. A partial swap chain fails `manage.py check`, so a chain is one commit (R2).
- **Rules exist** (E007). A bound rule must exist in `DERIVATIONS`. A rule is deleted only in the commit that removes its last binding, after a grep for other callers.
- **Checkbox bindings** carry `"type": "checkbox"` and `choices` (answer → export state, spelled as `export_state()` gives it from the field index). A rule or answer feeding a multi-key `choices` map returns exactly one of its keys or `""`. Anything else raises `UnmappedChoice`.
- **R4:** Schedule I `Amount 12` and Schedule J `23a` never lose their binding.
- **Known defects** (§7.3, R3): "Each commit deletes exactly the known-defect entries it orphans or turns into an XPASS, and never adds one." Delete entries by hand, never by re-running the recorder.
- **The addendum** (§7.4): every Appendix A row marked ADD gets its `step2_verification.json` row in the same commit as its binding. MOVED rows need none: the moved-here join asserts them.
- **Tier 2's coverage count** (`ASSERTED_CASES`, 425 at `a8c266e`) is pinned. Each task that changes it says the new number and why.
- **Tier 3:** Appendix D's rows land in the commit that makes them pass.
- **Tests are named for the outcome they protect** (§7.7).
- **UPL:** user-facing text is legal information, never advice (`docs/UPL_COMPLIANCE.md`). 2b's one filer-facing change is Task 10's pay-stub help text, which uses §5.1's words exactly.
- **Test data** is synthetic only, with SSNs from the IRS-reserved 900 range.
- **Gates** (§7.1): every commit leaves backend pytest with coverage at 90% or more, `manage.py check`, ruff 0.8.5, vitest, tsc, eslint and prettier green. The 7 journeys run on Tasks 6, 10, 17 and 18.
- **Lint:**
  - ruff 0.8.5 (`ruff check backend/`, as CI runs it).
  - Pre-commit runs black 24.10.0 (line length 100) on `backend/`, prettier 3.4.2 on JSON, Markdown, CSS and TypeScript outside `backend/` (not YAML; `check-yaml` parses it), and eslint on the frontend.
- **Never run `tsc -b`.** It writes build output through the `node_modules` symlink into the main checkout. Use `tsc -p tsconfig.app.json --noEmit` and `tsc -p tsconfig.node.json --noEmit`.
- **Commit messages** end with the last line about the change. **Add no `Co-Authored-By`, `Claude-Session` or other agent trailer, even if your harness asks for one.**
- **Staging:** stage files by explicit path only, never with `git add -A`, `git add .` or `git commit -a`. Commit only the files the task lists.
- **No outward actions:** no push, PR, merge, deploy or production command. Those are the owner's decisions.
- **Databases:** never use the shared development database `dignifi_dev`. This plan makes its own.
- **Keys:** never print, log or commit an API key. This plan does not use the repo-root `.env`; the journeys use a dummy key against a fake OpenAI server.

## Before you start (once per worktree)

- Work in `/Volumes/Containers/DigniFi/.claude/worktrees/forms-step2b` (branch `feat/forms-step2b`). Every command block runs from that worktree's root.
- Backend tools come from the main checkout's virtualenv, and frontend tools from its `node_modules`. Pre-commit's eslint hook expects that symlink.
- Task 2's check runs `jq` (MacPorts installs it as `/opt/local/bin/jq`); the setup block below stops if it isn't on `PATH`.
- The journeys need Colima running, with the `dignifi-db-1` Postgres container answering on host port 5433, and nothing listening on ports 8000, 5173 or 4010.
- `pytest` uses `config.settings.test` (sqlite in memory). `manage.py` and the journeys use the database below.

```bash
set -eo pipefail
mkdir -p backend/logs .claude   # the audit log handler needs backend/logs; CI creates it too
[ -e frontend/node_modules ] || ln -s /Volumes/Containers/DigniFi/frontend/node_modules frontend/node_modules
command -v jq >/dev/null   # Task 2 runs the review workflow's jq filter
# CI's synthetic Fernet key (it encrypts nothing real), read from ci.yml rather than copied here
FERNET=$(sed -n 's/^ *FIELD_ENCRYPTION_KEY: //p' .github/workflows/ci.yml | head -1)
[ -n "$FERNET" ]
# A database of its own keeps the shared dev database on main's migrations.
docker exec dignifi-db-1 dropdb -U dignifi --if-exists dignifi_forms_step2b
docker exec dignifi-db-1 createdb -U dignifi dignifi_forms_step2b
cat > .claude/forms-step2b.env <<ENV
# Settings for forms step 2b (git-ignored). Source from the worktree root.
export PY=/Volumes/Containers/DigniFi/backend/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_forms_step2b
export DJANGO_SECRET_KEY=test-only-not-a-secret
export DEBUG=True
export ALLOWED_HOSTS=localhost,127.0.0.1
export CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
export FIELD_ENCRYPTION_KEY=$FERNET
export OCR_PROVIDER=openai
export OPENAI_API_KEY=e2e-dummy-key
export OPENAI_BASE_URL=http://127.0.0.1:4010/v1
ENV
source .claude/forms-step2b.env && $PY -c "import pypdf; assert pypdf.__version__ == '6.13.1', pypdf.__version__"
git check-ignore -q .claude/forms-step2b.env && git check-ignore -q .claude/e2e.sh && echo "env file is ignored"
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
source .claude/forms-step2b.env
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

Check that Part 1 is in place: Task 9's commit is on this branch. Review fixes may have added commits after it.

```bash
set -eo pipefail
git log --format=%s a8c266e..HEAD | grep -Fx "fix(forms): Form 122A-1 prints monthly income on line 11, the means test's median on line 13, and ticks the result" >/dev/null
echo "Part 1 is in place"
```

Expected: `Part 1 is in place`. If the block fails instead, Task 9 isn't committed: finish Part 1 first.

Check the baseline before Task 10:

```bash
set -eo pipefail
source .claude/forms-step2b.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2002 passed, 1 skipped, 65 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  357 passed (357)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

## How to read the code blocks

- **`<language> file=<path>` blocks:** the block is the file's complete content. Create or overwrite the file with exactly that text.
- **`bash` blocks:** run from the worktree root in a fresh shell (bash or zsh). Each block starts with `set -eo pipefail`, so any command that fails, including one inside a pipeline, stops the block and fails it. A block sources `.claude/forms-step2b.env` itself when it needs it.
- **`git apply <<'PATCH'` blocks:** these patch the state the previous task left. If one doesn't apply, stop: the tree has drifted from the plan.
- **"Expected:" lines** say what the command must do. An "Expected: FAIL" step is the red half of test-first. Every other step must succeed.
- **Commit blocks** use each task's verified commit message. A pre-commit hook that rewrites a file means the tree has drifted from the plan: stop and compare.

## Decisions already made

These rulings were settled while the plan was built: by the owner where marked, otherwise by the plan's author against the spec. Every task's code already follows them. Don't reopen them in review. A task that depends on one repeats it in its own text.

- **Eighteen tasks, one commit each, in this order.** The spec's commit rules fix the order: R1–R4, E006, E007 and §7.4's "rows land with their binding". Grouping by form or by owner question follows Appendix B. Every task boundary passes every gate.
- **The owner's answers Q4–Q12 (§6.3) are settled.** Tasks quote them where they decide a box. Q6: signature lines and signing dates stay blank for wet ink. Q7 and Q12: the consumer-debts and paid-help answers print on every form that asks.
- **The addendum's `producer` is the whole binding key** (§7.4). In `data/forms/field_index/audit/step2_verification.json` it is spelled exactly as tier 2's `_binding_key` builds it, for example `derived:phone`, `asked:answer:form_101.mailing_zip` or `constant:yes`, and compared as written. The spec's row shape has no separate source column, so (schema, box, whole key) is the only join.
- **Appendix A.14's classes stand: 83 ADD and 30 MOVED.** Form 107 `Debtor 1` and Form 101 `Debtor1.ZIP Code_2` stay ADD, with addendum rows, even though the moved-here join would also assert them.
- **The income rules 2a already switched are done.** Of §6.2's "body changes", six 122A-1 rules and seven Schedule I rules were switched in 2a. 2b moves only their bindings.
- **A rule that loses its last binding is deleted in that task**, with its tests, after a grep for other callers. A helper that a still-bound rule calls stays. `has_prior_income` and `has_creditor_payments` are still bound, so they stay.
- **Task 10 deletes `_get_income_field`**, because §5.5 deletes it "with the last of" the per-source rules, and Task 10 removes the last one bound. Two unbound rules go with it: `schedule_i_gross_wages_debtor1`, which §5.5 names, and `line4_interest_dividends`, which was its last other caller. Both read `IncomeInfo` attributes that never existed.
- **Some rules stay unbound, as they were before 2b:** `chapter`, `debtor_type`, `joint_filer_check`, `joint_filer_name`, `means_test_disposable_income` and `schedule_i_employer_debtor1`. 2b didn't unbind them, so 2b doesn't delete them.
- **Empty lists keep printing 0.00 on totals.** The filer finished the intake, and Q8 already reads an empty list as "No".
- **Schedule J 23c prints a negative result with a minus sign.** It is blank when 23a is blank, which is the form's own arithmetic.
- **106Sum 3c and 4 move in one commit with the Schedule I income total** (Appendix B, C.2), in Task 11.
- **`total_student_loans` counts only unsecured student loans.** E/F is the unsecured schedule, and otherwise 6i (6j − 6f) can go negative.
- **The fee-waiver noncash answer is required before 103B binds line 3** (K-1, DIG-193). Task 6 makes the serializer refuse a create that omits it, in every encoding. Kinds of help are kept only under a Yes.
- **The preparer-name boxes print a stored name whatever the paid-help answer is.** This covers Forms 101, 106Dec and 107. The spec binds them without a condition (Q12), and nothing collects the answer yet. Step 4 clears the name on a No when it asks the question.
- **The DIG-144 task has no red test step, and the 2b pull request can't prove it.** It changes YAML only. On a pull request that changes this workflow, the action refuses to run (#17 logged "Workflow validation failed. The workflow file must exist and have identical content to the version on the repository's default branch.") and reports success. So on the 2b pull request, Task 2's new check turns `claude-review` red: no summary was posted, but because no review ran, not because of DIG-144. The pull request's description must say so. The first pull request after 2b merges is the proof.
- **Every `ASSERTED_CASES` change is measured.** Each commit's delta comes from diffing the collected test IDs before and after, not from adding up the map's notes.
- **Known defects** (§7.3): each task deletes exactly the entries its slice names, by hand. A new failing oracle case, or an XPASS whose cause you can't name, is a spec problem: stop and report it. Don't patch around it. The list goes from 142 entries to none.
- **Copy:** 2b changes one filer-facing sentence. Task 10 sets the upload page's Pay stubs help text to §5.1's words, exactly: "Recent pay stubs from your job. Your employer's name is used for your income form (Schedule I)." Task 6's refusal reuses the field's own DRF `required` message.
- **Task 1 also edits `data/forms/field_index/tools/record_known_defects.py`.** Task 1 makes tier 2's `_audit` return every row on a box as a list, and the recorder is its only other reader. Without the edit, recording any tier 2 failure crashes.
- **Task 10 also edits the upload page** (`frontend/src/pages/DocumentUploadPage.tsx` and its test). §5.1 puts the pay-stub help text in "2b's Schedule I commit, where stubs stop feeding line 2". So Task 10 runs the journeys too.
- **From Task 7 to Task 17, pytest reports `1 skipped`.** Task 7 maps the last unmapped checkbox, so tier 1's `test_checkbox_answer_is_mapped_to_a_box` has an empty parameter set. The guard still fails on a checkbox bound with `{}`. Task 18 replaces it with one plain test, and the suite reports 0 skipped.
- **Between Task 12 and Task 14, some 122A-2 boxes print blank at $0.** `Quest6`, `Quest8`, `Quest9`, `Quest12`, `Quest13D`, `Quest14` and `Quest15` share the Schedule J expense rules that Task 12 makes blank at $0. Task 14 deletes those bindings.

## Spec coverage

Section 6 and Appendices A–D of the spec map to tasks as follows. Task 2 is DIG-144, which the owner added to 2b. It is outside the spec.

| Spec                                                                                                                                                | Task                            |
| --------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| §7.4 the addendum and how tier 2 reads it; §7.5 tier 3's "shows nothing" expectation and the Appendix D rows that pass at the start; DIG-217 (M1-1) | 1                               |
| DIG-144: the review check says when the review posted no summary                                                                                    | 2                               |
| A.1 Form 101 (except Q6, Q7 and Q12); §6.1 B5 for Form 101's ranges                                                                                 | 3                               |
| §6.3 Q6: signature lines and dates (A.1, A.3, A.5, A.6, A.12)                                                                                       | 4                               |
| §6.3 Q7 and Q12: the owner's answer boxes on 101, 103B, 106Sum, 106Dec and 107                                                                      | 5                               |
| A.2 Form 103B; §6.3 Q10 and Q11; K-1 (DIG-193)                                                                                                      | 6                               |
| A.4 106Sum lines 5, 3a, `check6`; A.12 Form 121's no-SSN box                                                                                        | 7                               |
| A.5 122A-1 income lines; swap chains 122A-1 a, b and c                                                                                              | 8                               |
| A.5 122A-1 result: swap chain d, lines 11 and 13, §6.3 Q5; §6.1 Rule 9                                                                              | 9                               |
| A.7 Schedule I per source; the six 5x→8x moves; §5.1 the pay-stub help text                                                                         | 10                              |
| §6.1 C1: the Schedule I income total; the 106Sum swap chain; R4                                                                                     | 11                              |
| A.8 Schedule J expense lines; §6.1 option A; §6.3 Q4; swap chains Schedule J a and b                                                                | 12                              |
| A.8 Schedule J 22c, 23b, 23c and line 1                                                                                                             | 13                              |
| A.6 Form 122A-2                                                                                                                                     | 14                              |
| A.9 Schedule A/B (§6.3 Q8 and Q9; DIG-164); A.13 Schedule C; A.10 Schedules G and H                                                                 | 15                              |
| A.10 Schedules D and E/F; 106Sum 3b and 9d                                                                                                          | 16                              |
| A.11 Form 107                                                                                                                                       | 17                              |
| Docs: CLAUDE.md and the stale test names and comments; tier 1's checkbox test without a skip; `known_defects.json` is empty                         | 18                              |
| §6.1 B2: blank instead of 0.00                                                                                                                      | every binding task              |
| §7.3 and Appendix C: known defects, commit by commit (142 → 0)                                                                                      | 3, 6–17                         |
| Appendix B: R2, R3 and R4; E006 and E007                                                                                                            | every binding task              |
| §7.7 tests named for what they protect                                                                                                              | every task                      |
| §9 success criteria 1, 2 and 3 (4–8 are 2a's and stay green)                                                                                        | every task; 18; 1 and every ADD |

---

### Task 10: Print each Schedule I income source on the line that asks for it, and add lines 4, 7 and 9

_Built and verified as commit `c64195f` on `plan/forms-step2b`._

**Files:**

- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_api_readback.py`
- Modify: `backend/apps/forms/tests/test_derivations.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier3.py`
- Modify: `backend/apps/forms/tests/test_schedule_i_schema.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/schedule_i.json`
- Modify: `frontend/src/pages/DocumentUploadPage.tsx`
- Modify: `frontend/src/pages/__tests__/DocumentUploadPage.test.tsx`

**Interfaces:**

- Consumes:
  - 2a's `_income_amounts(session, *fields)` in `derivations.py`: the sum of those `IncomeInfo` amounts, or `""` when the filer gave none of them. 2a already switched to it the seven per-source rules whose bindings this task moves: `schedule_i_net_wages_debtor1` (wages + tips), `schedule_i_rental_debtor1`, `schedule_i_child_support_debtor1` (child support + alimony), `schedule_i_unemployment_debtor1`, `schedule_i_social_security_debtor1`, `schedule_i_pension_debtor1` and `schedule_i_other_income_debtor1`.
  - Task 8's `other_income_label` ("Other income" when `monthly_other_income` is above $0, else `""`), already bound on 122A-1 line 10's source box, and `LINE_BY_SOURCE` in `test_form_122a1_schema.py` (122A-1 box → figure with `TEN_SOURCES`).
  - `TEN_SOURCES` (a distinct power of two per source) and `SWITCHED_RULES` (rule → the sources it adds) in `test_derivations.py`, whose parametrized tests check each rule's own figure, a blank when none of its sources was given, and 0.00 when all were typed as $0.
  - Task 1's addendum reader in tier 2 and tier 3's blank expectation; Task 4 left `today_iso` bound only on Schedule I `Supplemental income date`.
- Produces:
  - `data/forms/schemas/schedule_i.json` (23 objects): `Amount 2 Debtor 1` ← `derived:schedule_i_net_wages_debtor1` (re-ruled in place from `ingested:paystub.gross`; `ingest_key` is null); `Amount 3 Debtor 1` ← `schedule_i_overtime_debtor1`; `Amount 4 Debtor 1`, `Amount 4 Debtor 1a` and `Amount 7 Debtor 1` ← `schedule_i_gross_income_debtor1`; `Amount 8a`, `8c`, `8d`, `8e`, `8g` and `8h Debtor 1` ← the rental, child support, unemployment, Social Security, pension and other income rules; `Other income 8h` ← `other_income_label`; `Amount 9 Debtor 1` ← `schedule_i_other_income_total_debtor1`. `Supplemental income date`, `Amount 5a`–`5h Debtor 1` and `Amount 6 Debtor 1` are unbound. `Amount 10 Debtor 1` and `Amount 12` still print `cmi` (Task 11 re-rules them).
  - New rules, each `_income_amounts` over its sources, `str`, blank when none was given: `schedule_i_overtime_debtor1` (`monthly_overtime`), `schedule_i_gross_income_debtor1` (`monthly_gross_wages`, `monthly_tips`, `monthly_overtime`) and `schedule_i_other_income_total_debtor1` (rental, child support, alimony, unemployment, Social Security, pension, other).
  - Deleted from `DERIVATIONS`: `today_iso`, `schedule_i_self_employment_debtor1`, `schedule_i_interest_debtor1`, `schedule_i_total_deductions_debtor1`, `schedule_i_net_income_debtor1`, `schedule_i_gross_wages_debtor1` and `line4_interest_dividends`; deleted helpers `_line8a_total_gross_income` and `_get_income_field`, and the `from datetime import date` import.
  - In `test_schedule_i_schema.py`: the module tables `LINE_BY_SOURCE`, `LINE_TOTALS` and `NEVER_ASKED` (Task 11's `INCOME_LINES` reads the first two), and the tests `test_each_income_source_prints_on_its_own_line` (§7.7), `test_lines_4_7_and_9_add_the_lines_the_form_names` and `test_lines_schedule_i_never_asks_about_print_nothing`.
  - Tier 3's `EXPECTED`: `Amount 8e Debtor 1` is "0.00" for all five personas.
  - `step2_verification.json` 32 → 38 rows; `ASSERTED_CASES` stays 413; `known_defects.json` 64 → 54 entries.
  - The upload page's Pay stubs help text is §5.1's sentence, and the vitest test `DocumentUploadPage > never tells the filer a pay stub fills in their pay` pins it.

**Decisions already made in this task:**

- Only bindings move. 2a switched the seven per-source rule bodies (§5.5), and each moved rule keeps its name so tier 2's moved-here join checks the move against the audit (§6.1 "Rule names"). `schedule_i_net_wages_debtor1` keeps its name on line 2.
- `Amount 2 Debtor 1` is re-ruled in place, from the pay stub's gross pay to wages + tips, in the commit that takes the rule off `Amount 3 Debtor 1`: a box takes one binding (E006, Appendix B). Owner Q14: "a stub supplies only the employer's name. Every income box reads the typed amounts." `Employers Name Debtor 1` keeps `ingested:paystub.employer_name`. `apps/documents/services/aggregator.py` still writes `paystub.gross`, which no schema reads now; Task 18 records that, so leave it.
- Only rental moves to 8a (old 5f). `Amount 4 Debtor 1` loses `schedule_i_self_employment_debtor1` by a re-rule in place, never a move (R2): business income is never asked.
- Lines 4, 4's copy at the top of page 2 and 7 print line 2 + line 3. "Deductions are not stored until step 3 (OQ-7), so Schedule I line 7 (take-home) equals gross for now" (§5.5); the 6c decision approved counting the unasked line as zero for line 7 (§6.1).
- Line 9 adds 8a–8h. 8b (interest) and 8f (other government assistance) are never asked and count as zero; `Assistance 8f` is never bound.
- `Other income 8h` binds Task 8's `other_income_label`; the rule is not created again.
- B2: `Supplemental income date`, `Amount 5e Debtor 1` (line 5e asks for insurance; it carried the interest rule) and `Amount 6 Debtor 1` (payroll deductions, step 3) lose their bindings and print blank.
- A rule that loses its last binding is deleted here, after a grep for other callers: `today_iso`, `schedule_i_self_employment_debtor1`, `schedule_i_interest_debtor1`, `schedule_i_total_deductions_debtor1`, `schedule_i_net_income_debtor1`, and `_line8a_total_gross_income`, whose only caller was the last.
- `_get_income_field` goes too, because §5.5 deletes it "with the last of" the per-source rules. The two unbound rules that still called it go with it: `schedule_i_gross_wages_debtor1` (named in §5.5) and `line4_interest_dividends`. Both read `IncomeInfo` attributes that never existed, and nothing else calls or binds them.
- With `today_iso` gone, `test_api_readback.py` loses its `today_iso` branch, the `TODAY` constant, the signing-date sentences in `_comparable`'s docstring, and `import re`, which only the branch used. No form prints today's date any more.
- `Amount 10 Debtor 1` and `Amount 12` still print `cmi`, so with Social Security given line 10 is not line 7 + line 9 until Task 11. No persona shows it: every seed's Social Security is $0. Leave them.
- `TEN_SOURCES` stays in `test_derivations.py`, where Task 8's `test_form_122a1_schema.py` imports it. The §7.7 test lands here, the commit that binds the last income box it checks; it reads 122A-1's figures from Task 8's `LINE_BY_SOURCE`, so the two tables can't drift. Task 8's 122A-1-only test stays.
- Moved objects keep their labels, so `Amount 8a Debtor 1` keeps 5f's "Debtor 1 rental/royalty income" (labels are never printed; an accepted nit). Re-ruled objects are retitled.
- `ASSERTED_CASES` stays 413, measured by diffing the collected IDs: 13 tier 2 cases leave with their bindings (10 xfails, and 3 passes: line 2's pay-stub key, line 6 and line 7's old rule), and 13 arrive, all passing: 7 moved-here joins (2, 8a, 8c, 8d, 8e, 8g, 8h) and the 6 addendum rows. `test_oracle_tier2.py` is unchanged.
- Known defects (R3): delete exactly 10 tier 2 entries, all orphans: `Supplemental income date` under `derived:today_iso` (DIG-82), and DIG-56's `Amount 3 Debtor 1`, `Amount 4 Debtor 1`, `Amount 5a`, `5b`, `5c`, `5d`, `5e`, `5f` and `5g Debtor 1`, each under its old binding key. 64 → 54.
- Copy: §5.1 puts the pay-stub help text "in 2b's Schedule I commit, where stubs stop feeding line 2". It becomes exactly "Recent pay stubs from your job. Your employer's name is used for your income form (Schedule I)." This task changes a page, so it runs the journeys.

- [ ] **Step 1: Write the failing Schedule I tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_derivations.py b/backend/apps/forms/tests/test_derivations.py
index 46de40d..9eb30cb 100644
--- a/backend/apps/forms/tests/test_derivations.py
+++ b/backend/apps/forms/tests/test_derivations.py
@@ -132,6 +132,17 @@ SWITCHED_RULES = {
     "schedule_i_social_security_debtor1": ["monthly_social_security"],
     "schedule_i_pension_debtor1": ["monthly_pension"],
     "schedule_i_other_income_debtor1": ["monthly_other_income"],
+    "schedule_i_overtime_debtor1": ["monthly_overtime"],
+    "schedule_i_gross_income_debtor1": ["monthly_gross_wages", "monthly_tips", "monthly_overtime"],
+    "schedule_i_other_income_total_debtor1": [
+        "monthly_rental_income",
+        "monthly_child_support",
+        "monthly_alimony",
+        "monthly_unemployment",
+        "monthly_social_security",
+        "monthly_pension",
+        "monthly_other_income",
+    ],
     "line1_wages": ["monthly_gross_wages", "monthly_tips", "monthly_overtime"],
     "line6b_child_support_alimony": ["monthly_child_support"],
     "line3_real_property_income": ["monthly_rental_income"],
diff --git a/backend/apps/forms/tests/test_oracle_tier3.py b/backend/apps/forms/tests/test_oracle_tier3.py
index 96f3988..85ab637 100644
--- a/backend/apps/forms/tests/test_oracle_tier3.py
+++ b/backend/apps/forms/tests/test_oracle_tier3.py
@@ -62,7 +62,11 @@ EXPECTED = {
             "13C": "110712.00",
             "14a": BELOW_MEDIAN,
         },
-        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "3200.00"},
+        "schedule_i": {
+            "Amount 8b Debtor 1": "",
+            "Amount 8e Debtor 1": "0.00",
+            "Amount 12": "3200.00",
+        },
         "schedule_j": {
             "18": "",
             "22a": "2560.00",
@@ -93,7 +97,11 @@ EXPECTED = {
             "13C": "71304.00",
             "14a": BELOW_MEDIAN,
         },
-        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "5833.00"},
+        "schedule_i": {
+            "Amount 8b Debtor 1": "",
+            "Amount 8e Debtor 1": "0.00",
+            "Amount 12": "5833.00",
+        },
         "schedule_j": {
             "18": "",
             "22a": "3110.00",
@@ -122,7 +130,11 @@ EXPECTED = {
             "13C": "134366.00",
             "14a": ABOVE_MEDIAN,
         },
-        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "12000.00"},
+        "schedule_i": {
+            "Amount 8b Debtor 1": "",
+            "Amount 8e Debtor 1": "0.00",
+            "Amount 12": "12000.00",
+        },
         "schedule_j": {
             "18": "",
             "22a": "6640.00",
@@ -153,7 +165,11 @@ EXPECTED = {
             "13C": "91526.00",
             "14a": BELOW_MEDIAN,
         },
-        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "3500.00"},
+        "schedule_i": {
+            "Amount 8b Debtor 1": "",
+            "Amount 8e Debtor 1": "0.00",
+            "Amount 12": "3500.00",
+        },
         "schedule_j": {
             "18": "",
             "22a": "2295.00",
@@ -181,7 +197,11 @@ EXPECTED = {
             "13C": "71304.00",
             "14a": BELOW_MEDIAN,
         },
-        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "2000.00"},
+        "schedule_i": {
+            "Amount 8b Debtor 1": "",
+            "Amount 8e Debtor 1": "0.00",
+            "Amount 12": "2000.00",
+        },
         "schedule_j": {
             "18": "",
             "22a": "1280.00",
diff --git a/backend/apps/forms/tests/test_schedule_i_schema.py b/backend/apps/forms/tests/test_schedule_i_schema.py
index 4b8a57b..11c5652 100644
--- a/backend/apps/forms/tests/test_schedule_i_schema.py
+++ b/backend/apps/forms/tests/test_schedule_i_schema.py
@@ -10,10 +10,47 @@ from apps.districts.models import District
 from apps.eligibility.cmi import IncomeNotSplit
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
+from apps.forms.tests.test_derivations import TEN_SOURCES
+from apps.forms.tests.test_form_122a1_schema import LINE_BY_SOURCE as FORM_122A1_LINE_BY_SOURCE
 from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

 User = get_user_model()

+# Box → what it prints with TEN_SOURCES (wages 1, overtime 2, tips 4, rental 8,
+# pension 16, Social Security 32, unemployment 64, child support 128, alimony 256,
+# other 512).
+LINE_BY_SOURCE = {
+    "Amount 2 Debtor 1": "5.00",  # line 2: wages and tips
+    "Amount 3 Debtor 1": "2.00",  # line 3: overtime
+    "Amount 8a Debtor 1": "8.00",  # 8a: net rental income
+    "Amount 8c Debtor 1": "384.00",  # 8c: child support and alimony
+    "Amount 8d Debtor 1": "64.00",  # 8d: unemployment
+    "Amount 8e Debtor 1": "32.00",  # 8e: Social Security
+    "Amount 8g Debtor 1": "16.00",  # 8g: pension
+    "Other income 8h": "Other income",  # 8h: what the other income is
+    "Amount 8h Debtor 1": "512.00",  # 8h: its amount
+}
+LINE_TOTALS = {
+    "Amount 4 Debtor 1": "7.00",  # line 4: line 2 + line 3
+    "Amount 4 Debtor 1a": "7.00",  # line 4's copy at the top of page 2
+    "Amount 7 Debtor 1": "7.00",  # line 7: line 4, as no payroll deduction is asked yet
+    "Amount 9 Debtor 1": "1016.00",  # line 9: 8a + 8c + 8d + 8e + 8g + 8h
+}
+NEVER_ASKED = {
+    "Supplemental income date",  # a Chapter 13 supplement's date
+    "Amount 5a Debtor 1",  # lines 5a-6: payroll deductions
+    "Amount 5b Debtor 1",
+    "Amount 5c Debtor 1",
+    "Amount 5d Debtor 1",
+    "Amount 5e Debtor 1",
+    "Amount 5f Debtor 1",
+    "Amount 5g Debtor 1",
+    "Amount 5h Debtor 1",
+    "Amount 6 Debtor 1",
+    "Amount 8b Debtor 1",  # interest and dividends
+    "Amount 8f Debtor 1",  # other government assistance
+}
+

 @pytest.fixture
 def session(db):
@@ -77,6 +114,40 @@ class TestScheduleISchema:
         assert field_map["Amount 12"] == "2000.00"
         assert field_map["Amount 10 Debtor 1"] == "2000.00"

+    def test_each_income_source_prints_on_its_own_line(self, session):
+        # A distinct power of two per source, so a box that reads the wrong source, or
+        # adds one too many, prints a different figure (step 2 spec §5.5's table, §7.7).
+        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
+
+        schedule_i = resolve(load_schema("schedule_i"), session)
+        form_122a1 = resolve(load_schema("form_122a1"), session)
+
+        assert {box: schedule_i.get(box) for box in LINE_BY_SOURCE} == LINE_BY_SOURCE
+        assert {
+            box: form_122a1.get(box) for box in FORM_122A1_LINE_BY_SOURCE
+        } == FORM_122A1_LINE_BY_SOURCE
+        # Social Security is Schedule I income (8e), but never current monthly income.
+        assert [box for box, value in schedule_i.items() if value == "32.00"] == [
+            "Amount 8e Debtor 1"
+        ]
+        assert "32.00" not in form_122a1.values()
+
+    def test_lines_4_7_and_9_add_the_lines_the_form_names(self, session):
+        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
+
+        field_map = resolve(load_schema("schedule_i"), session)
+
+        assert {box: field_map.get(box) for box in LINE_TOTALS} == LINE_TOTALS
+
+    def test_lines_schedule_i_never_asks_about_print_nothing(self, session):
+        # Payroll deductions wait for step 3; interest and other government assistance
+        # are never asked: blank, never 0.00 (B2).
+        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
+
+        field_map = resolve(load_schema("schedule_i"), session)
+
+        assert sorted(NEVER_ASKED & field_map.keys()) == []
+
     def test_empty_session_is_asked_for_income_by_source(self, session):
         # Lines 10 and 12 print CMI until 2b, and a filer who gave no income has none.
         with pytest.raises(IncomeNotSplit):
PATCH
```

`test_each_income_source_prints_on_its_own_line` stores `TEN_SOURCES` and requires each Schedule I box in `LINE_BY_SOURCE` to print its own figure, 122A-1 to print Task 8's figures, and 32.00 (Social Security) to print only on `Amount 8e Debtor 1` and on no 122A-1 box. `test_lines_4_7_and_9_add_the_lines_the_form_names` requires 7.00 on lines 4, 4's copy and 7, and 1016.00 on line 9. `test_lines_schedule_i_never_asks_about_print_nothing` requires the boxes in `NEVER_ASKED` to be absent from the resolved values. The three new rules join `SWITCHED_RULES`, and tier 3 expects 0.00 on 8e for every persona.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line apps/forms/tests/test_schedule_i_schema.py apps/forms/tests/test_derivations.py apps/forms/tests/test_oracle_tier3.py -q -p no:cacheprovider 2>&1 | tail -40
```

Expected: FAIL — `17 failed, 186 passed, 22 xfailed`. The three new rules are missing from DERIVATIONS, so each of their 9 cases raises a KeyError such as `KeyError: 'schedule_i_overtime_debtor1'`. Tier 3 reads `wrong_value: prints [], expected 0.00` for each persona, because 8e is unbound.

The three schema tests fail too: lines 8a–8h, 4's copy and 9 are unbound, lines 4 and 7 print 0.00 from the dead per-source bodies, and the payroll-deduction boxes 5a–6 are still bound.

- [ ] **Step 3: Move the income bindings and add the three rules**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index bfeffed..57b8a47 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -12,7 +12,6 @@ answer anything the form leaves to the filer — those are ``asked`` +
 from __future__ import annotations

 from collections.abc import Callable
-from datetime import date
 from decimal import Decimal
 from functools import reduce

@@ -247,19 +246,6 @@ def _total_debts_range(session: IntakeSession) -> str:
 # ---------------------------------------------------------------------------


-def _get_income_field(session: IntakeSession, field: str) -> Decimal:
-    try:
-        income_info = session.income_info
-        val = getattr(income_info, field, None)
-        if val is None:
-            return _ZERO
-        if isinstance(val, list):
-            return sum((Decimal(str(v)) for v in val), _ZERO) / Decimal(str(len(val)))
-        return Decimal(str(val))
-    except Exception:
-        return _ZERO
-
-
 def _line1_wages(session: IntakeSession) -> str:
     return _income_amounts(session, "monthly_gross_wages", "monthly_tips", "monthly_overtime")

@@ -272,10 +258,6 @@ def _line3_real_property_income(session: IntakeSession) -> str:
     return _income_amounts(session, "monthly_rental_income")


-def _line4_interest_dividends(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "interest_dividends"))
-
-
 def _line5a_pension_retirement(session: IntakeSession) -> str:
     return _income_amounts(session, "monthly_pension")

@@ -299,24 +281,6 @@ def _other_income_label(session: IntakeSession) -> str:
     return "Other income" if other is not None and other > 0 else ""


-def _line8a_total_gross_income(session: IntakeSession) -> str:
-    total = sum(
-        (
-            _get_income_field(session, "wages_salaries_tips"),
-            _get_income_field(session, "business_income"),
-            _get_income_field(session, "real_property_income"),
-            _get_income_field(session, "interest_dividends"),
-            _get_income_field(session, "pension_retirement"),
-            _get_income_field(session, "social_security"),
-            _get_income_field(session, "unemployment_compensation"),
-            _get_income_field(session, "child_support_alimony"),
-            _get_income_field(session, "other_income"),
-        ),
-        _ZERO,
-    )
-    return _fmt(total)
-
-
 def _line11_annualized_income(session: IntakeSession) -> str:
     cmi = Decimal(_cmi(session))
     return _fmt(cmi * Decimal("12"))
@@ -403,16 +367,17 @@ def _schedule_i_employer_debtor1(session: IntakeSession) -> str:
     return _safe_debtor_attr(session, "employer_name", "")


-def _schedule_i_gross_wages_debtor1(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "wages_salaries_tips"))
-
-
 def _schedule_i_net_wages_debtor1(session: IntakeSession) -> str:
     return _income_amounts(session, "monthly_gross_wages", "monthly_tips")


-def _schedule_i_self_employment_debtor1(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "business_income"))
+def _schedule_i_overtime_debtor1(session: IntakeSession) -> str:
+    return _income_amounts(session, "monthly_overtime")
+
+
+def _schedule_i_gross_income_debtor1(session: IntakeSession) -> str:
+    """Line 4, line 2 + line 3, and line 7 until payroll deductions are asked (step 3)."""
+    return _income_amounts(session, "monthly_gross_wages", "monthly_tips", "monthly_overtime")


 def _schedule_i_unemployment_debtor1(session: IntakeSession) -> str:
@@ -431,10 +396,6 @@ def _schedule_i_child_support_debtor1(session: IntakeSession) -> str:
     return _income_amounts(session, "monthly_child_support", "monthly_alimony")


-def _schedule_i_interest_debtor1(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "interest_dividends"))
-
-
 def _schedule_i_rental_debtor1(session: IntakeSession) -> str:
     return _income_amounts(session, "monthly_rental_income")

@@ -443,14 +404,18 @@ def _schedule_i_other_income_debtor1(session: IntakeSession) -> str:
     return _income_amounts(session, "monthly_other_income")


-def _schedule_i_total_deductions_debtor1(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "deductions"))
-
-
-def _schedule_i_net_income_debtor1(session: IntakeSession) -> str:
-    gross = Decimal(_line8a_total_gross_income(session))
-    deductions = Decimal(_schedule_i_total_deductions_debtor1(session))
-    return _fmt(gross - deductions)
+def _schedule_i_other_income_total_debtor1(session: IntakeSession) -> str:
+    """Line 9, 8a through 8h: interest (8b) and other assistance (8f) are never asked."""
+    return _income_amounts(
+        session,
+        "monthly_rental_income",
+        "monthly_child_support",
+        "monthly_alimony",
+        "monthly_unemployment",
+        "monthly_social_security",
+        "monthly_pension",
+        "monthly_other_income",
+    )


 # ---------------------------------------------------------------------------
@@ -523,7 +488,6 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "chapter": lambda s: "7",
     "debtor_type": lambda s: "Individual",
     "district_name": lambda s: s.district.name,
-    "today_iso": lambda s: date.today().isoformat(),
     "ssn_formatted": _ssn_formatted,
     "no_ssn_check": lambda s: "" if _has_ssn(s) else "true",
     "joint_filer_check": lambda s: (
@@ -551,7 +515,6 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "line1_wages": _line1_wages,
     "line3_alimony": _line3_alimony,
     "line3_real_property_income": _line3_real_property_income,
-    "line4_interest_dividends": _line4_interest_dividends,
     "line5a_pension_retirement": _line5a_pension_retirement,
     "line6a_unemployment": _line6a_unemployment,
     "line6b_child_support_alimony": _line6b_child_support_alimony,
@@ -574,18 +537,16 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "schedule_i_employer_city_debtor1": lambda s: _safe_debtor_attr(s, "employer_city", ""),
     "schedule_i_employer_state_debtor1": lambda s: _safe_debtor_attr(s, "employer_state", ""),
     "schedule_i_employer_zip_debtor1": lambda s: _safe_debtor_attr(s, "employer_zip", ""),
-    "schedule_i_gross_wages_debtor1": _schedule_i_gross_wages_debtor1,
     "schedule_i_net_wages_debtor1": _schedule_i_net_wages_debtor1,
-    "schedule_i_self_employment_debtor1": _schedule_i_self_employment_debtor1,
+    "schedule_i_overtime_debtor1": _schedule_i_overtime_debtor1,
+    "schedule_i_gross_income_debtor1": _schedule_i_gross_income_debtor1,
     "schedule_i_unemployment_debtor1": _schedule_i_unemployment_debtor1,
     "schedule_i_social_security_debtor1": _schedule_i_social_security_debtor1,
     "schedule_i_pension_debtor1": _schedule_i_pension_debtor1,
     "schedule_i_child_support_debtor1": _schedule_i_child_support_debtor1,
-    "schedule_i_interest_debtor1": _schedule_i_interest_debtor1,
     "schedule_i_rental_debtor1": _schedule_i_rental_debtor1,
     "schedule_i_other_income_debtor1": _schedule_i_other_income_debtor1,
-    "schedule_i_total_deductions_debtor1": _schedule_i_total_deductions_debtor1,
-    "schedule_i_net_income_debtor1": _schedule_i_net_income_debtor1,
+    "schedule_i_other_income_total_debtor1": _schedule_i_other_income_total_debtor1,
     # Schedule J expense line item derivations
     "schedule_j_rent_or_mortgage": lambda s: _fmt(_get_expense_field(s, "rent_or_mortgage")),
     "schedule_j_utilities": lambda s: _fmt(_get_expense_field(s, "utilities")),
diff --git a/data/forms/schemas/schedule_i.json b/data/forms/schemas/schedule_i.json
index 088c057..966d1d7 100644
--- a/data/forms/schemas/schedule_i.json
+++ b/data/forms/schemas/schedule_i.json
@@ -37,23 +37,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Supplemental income date",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Date",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "today_iso",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "Occupation Debtor 1",
       "type": "text",
@@ -159,14 +142,14 @@
     {
       "pdf_field": "Amount 2 Debtor 1",
       "type": "text",
-      "source": "ingested",
+      "source": "derived",
       "page": 1,
       "label": "Debtor 1 gross wages",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": null,
-      "ingest_key": "paystub.gross",
+      "rule": "schedule_i_net_wages_debtor1",
+      "ingest_key": null,
       "binding": null,
       "repeat": null,
       "repeat_capacity": null,
@@ -212,11 +195,11 @@
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Debtor 1 net wages",
+      "label": "Debtor 1 overtime pay",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_i_net_wages_debtor1",
+      "rule": "schedule_i_overtime_debtor1",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -229,11 +212,11 @@
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Debtor 1 self-employment income",
+      "label": "Debtor 1 gross income",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_i_self_employment_debtor1",
+      "rule": "schedule_i_gross_income_debtor1",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -242,15 +225,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Amount 5a Debtor 1",
+      "pdf_field": "Amount 4 Debtor 1a",
       "type": "text",
       "source": "derived",
-      "page": 1,
-      "label": "Debtor 1 unemployment compensation",
+      "page": 2,
+      "label": "Debtor 1 gross income (line 4 copied)",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_i_unemployment_debtor1",
+      "rule": "schedule_i_gross_income_debtor1",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -259,15 +242,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Amount 5b Debtor 1",
+      "pdf_field": "Amount 7 Debtor 1",
       "type": "text",
       "source": "derived",
-      "page": 1,
-      "label": "Debtor 1 social security",
+      "page": 2,
+      "label": "Debtor 1 take-home pay",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_i_social_security_debtor1",
+      "rule": "schedule_i_gross_income_debtor1",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -276,15 +259,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Amount 5c Debtor 1",
+      "pdf_field": "Amount 8a Debtor 1",
       "type": "text",
       "source": "derived",
-      "page": 1,
-      "label": "Debtor 1 pension/retirement",
+      "page": 2,
+      "label": "Debtor 1 rental/royalty income",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_i_pension_debtor1",
+      "rule": "schedule_i_rental_debtor1",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -293,10 +276,10 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Amount 5d Debtor 1",
+      "pdf_field": "Amount 8c Debtor 1",
       "type": "text",
       "source": "derived",
-      "page": 1,
+      "page": 2,
       "label": "Debtor 1 child support/alimony",
       "required": false,
       "conditional_on": null,
@@ -310,15 +293,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Amount 5e Debtor 1",
+      "pdf_field": "Amount 8d Debtor 1",
       "type": "text",
       "source": "derived",
-      "page": 1,
-      "label": "Debtor 1 interest/dividends",
+      "page": 2,
+      "label": "Debtor 1 unemployment compensation",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_i_interest_debtor1",
+      "rule": "schedule_i_unemployment_debtor1",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -327,15 +310,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Amount 5f Debtor 1",
+      "pdf_field": "Amount 8e Debtor 1",
       "type": "text",
       "source": "derived",
-      "page": 1,
-      "label": "Debtor 1 rental/royalty income",
+      "page": 2,
+      "label": "Debtor 1 social security",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_i_rental_debtor1",
+      "rule": "schedule_i_social_security_debtor1",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -344,15 +327,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Amount 5g Debtor 1",
+      "pdf_field": "Amount 8g Debtor 1",
       "type": "text",
       "source": "derived",
-      "page": 1,
-      "label": "Debtor 1 other income",
+      "page": 2,
+      "label": "Debtor 1 pension/retirement",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_i_other_income_debtor1",
+      "rule": "schedule_i_pension_debtor1",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -361,15 +344,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Amount 6 Debtor 1",
+      "pdf_field": "Other income 8h",
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Debtor 1 total deductions",
+      "label": "Debtor 1 other income, specify",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_i_total_deductions_debtor1",
+      "rule": "other_income_label",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -378,15 +361,32 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Amount 7 Debtor 1",
+      "pdf_field": "Amount 8h Debtor 1",
+      "type": "text",
+      "source": "derived",
+      "page": 2,
+      "label": "Debtor 1 other income",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "schedule_i_other_income_debtor1",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "Amount 9 Debtor 1",
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Debtor 1 net monthly income",
+      "label": "Debtor 1 total other income",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_i_net_income_debtor1",
+      "rule": "schedule_i_other_income_total_debtor1",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
PATCH
```

The schema follows §5.5's table: line 2 is wages and tips, line 3 overtime, and the six other sources move from the payroll-deduction lines 5a–5g to 8a, 8c, 8d, 8e, 8g and 8h on page 2, the index's page. Lines 4, 4's copy and 7 take `schedule_i_gross_income_debtor1`, line 9 takes `schedule_i_other_income_total_debtor1`, and 8h's Specify box takes `other_income_label`. The rules that lost their last binding are deleted, with `_get_income_field` and the two unbound rules that still called it (§5.5).

- [ ] **Step 4: Drop the read-back's signing-date branch**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_api_readback.py b/backend/apps/forms/tests/test_api_readback.py
index db85357..a3b3791 100644
--- a/backend/apps/forms/tests/test_api_readback.py
+++ b/backend/apps/forms/tests/test_api_readback.py
@@ -15,7 +15,6 @@ expects.
 """

 import json
-import re
 from decimal import Decimal, InvalidOperation

 import pytest
@@ -47,10 +46,6 @@ WIZARD_STEPS = [
     ("debts", "debts"),
 ]

-# What a signing-date box compares as: the date is today's when it is built, and a run that
-# straddles midnight stores one day and rebuilds the next.
-TODAY = "<today>"
-

 def _sent(data):
     """Persona data as JSON carries it from the browser: amounts as decimal strings, dates as ISO."""
@@ -138,20 +133,14 @@ def _send_through_the_api(persona):

 def _comparable(form_type, values):
     """
-    A form's values, with each repeat group's rows in a fixed order and each date it was
-    built on as TODAY.
+    A form's values, with each repeat group's rows in a fixed order.

     Stored rows have no fixed order (DIG-164), so Form 107's rows compare regardless of it.
     Each row keeps its own values together, so an amount that moves to another row differs.
-    A signing date must still print as a date, but need not be the same day on both sides.
     """
     fixed = dict(values)
     rows = {}
     for field in load_schema(form_type).fields:
-        if field.rule == "today_iso":
-            date_printed = fixed.get(field.pdf_field, "")
-            assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_printed), (form_type, field.pdf_field)
-            fixed[field.pdf_field] = TODAY
         if field.repeat and field.row and field.pdf_field in fixed:
             cell = (field.binding or "", fixed.pop(field.pdf_field))
             rows.setdefault((field.repeat, field.row), []).append(cell)
PATCH
```

`_comparable` rewrote each `today_iso` box as `TODAY` so a run straddling midnight still compared. No schema binds `today_iso` now, so the branch, its constant and its comments go.

- [ ] **Step 5: Record the addendum rows and delete the 10 cleared entries**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index 666b199..7c0ac20 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -167,86 +167,6 @@
     "class": "wrong_box",
     "ticket": "DIG-69"
   },
-  {
-    "form_type": "schedule_i",
-    "pdf_field": "Amount 3 Debtor 1",
-    "tier": "2",
-    "case": "derived:schedule_i_net_wages_debtor1",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "schedule_i",
-    "pdf_field": "Amount 4 Debtor 1",
-    "tier": "2",
-    "case": "derived:schedule_i_self_employment_debtor1",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "schedule_i",
-    "pdf_field": "Amount 5a Debtor 1",
-    "tier": "2",
-    "case": "derived:schedule_i_unemployment_debtor1",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "schedule_i",
-    "pdf_field": "Amount 5b Debtor 1",
-    "tier": "2",
-    "case": "derived:schedule_i_social_security_debtor1",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "schedule_i",
-    "pdf_field": "Amount 5c Debtor 1",
-    "tier": "2",
-    "case": "derived:schedule_i_pension_debtor1",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "schedule_i",
-    "pdf_field": "Amount 5d Debtor 1",
-    "tier": "2",
-    "case": "derived:schedule_i_child_support_debtor1",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "schedule_i",
-    "pdf_field": "Amount 5e Debtor 1",
-    "tier": "2",
-    "case": "derived:schedule_i_interest_debtor1",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "schedule_i",
-    "pdf_field": "Amount 5f Debtor 1",
-    "tier": "2",
-    "case": "derived:schedule_i_rental_debtor1",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "schedule_i",
-    "pdf_field": "Amount 5g Debtor 1",
-    "tier": "2",
-    "case": "derived:schedule_i_other_income_debtor1",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "schedule_i",
-    "pdf_field": "Supplemental income date",
-    "tier": "2",
-    "case": "derived:today_iso",
-    "class": "wrong_box",
-    "ticket": "DIG-82"
-  },
   {
     "form_type": "schedule_j",
     "pdf_field": "10",
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index 5477246..069c012 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -318,5 +318,65 @@
     "status": "confirmed",
     "correct_target": "CheckBox1",
     "evidence": "Field index: CheckBox1 p1, three widgets (adjudicated): top box 1, state /No Abuse, 'There is no presumption of abuse.'; top box 2, state /Presumption of abuse applies, 'The calculation to determine if a presumption of abuse applies will be made under Chapter 7 Means Test Calculation (Official Form 122A-2).'; top box 3, state /Does not apply (qualified military service). Owner's answer Q5 (DIG-65; step 2 spec §3, §6.3): at or below the median, box 1; above, box 2; box 3 is never ticked."
+  },
+  {
+    "schema": "schedule_i",
+    "pdf_field": "Amount 3 Debtor 1",
+    "producer": "derived:schedule_i_overtime_debtor1",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Amount 3 Debtor 1",
+    "evidence": "Field index: Amount 3 Debtor 1 p1 line 3, column 'For Debtor 1', 'Estimate and list monthly overtime pay.' (adjudicated). Owner's answer Q3 (income per source) and step 2 spec §5.5's table (Overtime -> Schedule I line 3); §6.2 (schedule_i_overtime_debtor1, new; line 3). The audit's verified row on this box judged the old schedule_i_net_wages_debtor1 binding, which belongs on line 2."
+  },
+  {
+    "schema": "schedule_i",
+    "pdf_field": "Amount 4 Debtor 1",
+    "producer": "derived:schedule_i_gross_income_debtor1",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Amount 4 Debtor 1",
+    "evidence": "Field index: Amount 4 Debtor 1 p1 line 4, column 'For Debtor 1', 'Calculate gross income.' (adjudicated). Step 2 spec §6.2 (schedule_i_gross_income_debtor1: line 2 + line 3; line 4) and §6.1 B1 (line 4 keeps its box with the gross-income rule). The audit's verified row on this box judged the old schedule_i_self_employment_debtor1 binding, which it placed on 8a."
+  },
+  {
+    "schema": "schedule_i",
+    "pdf_field": "Amount 4 Debtor 1a",
+    "producer": "derived:schedule_i_gross_income_debtor1",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Amount 4 Debtor 1a",
+    "evidence": "Field index: Amount 4 Debtor 1a p2 line 4, column 'For Debtor 1', 'Copy line 4 here' (adjudicated). Step 2 spec §6.2 (schedule_i_gross_income_debtor1: line 4's copy at the top of page 2) and Appendix E 16 (line 4's copy, not line 5). The audit has no row for this box."
+  },
+  {
+    "schema": "schedule_i",
+    "pdf_field": "Amount 7 Debtor 1",
+    "producer": "derived:schedule_i_gross_income_debtor1",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Amount 7 Debtor 1",
+    "evidence": "Field index: Amount 7 Debtor 1 p2 line 7, column 'For Debtor 1', 'Calculate total monthly take-home pay. Subtract line 6 from line 4.' (adjudicated). Payroll deductions (lines 5a-6) are not asked until step 3 (OQ-7), so line 6 counts as zero and line 7 equals line 4: step 2 spec §5.5 ('Schedule I line 7 (take-home) equals gross for now'), §6.1 (totals that count an unasked line as zero; the section 6c decision covers Schedule I line 7) and §6.2."
+  },
+  {
+    "schema": "schedule_i",
+    "pdf_field": "Other income 8h",
+    "producer": "derived:other_income_label",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Other income 8h",
+    "evidence": "Field index: Other income 8h p2 line 8h, 'Other monthly income. Specify:' (adjudicated; tooltip 'Specify'), the text box beside Amount 8h Debtor 1. Step 2 spec §5.5's table (Other -> 8h, 'Other income'), §6.2 (other_income_label, shared with 122A-1 line 10) and Appendix E 5: 'Other income' when other income is above $0. The audit has no row for this box."
+  },
+  {
+    "schema": "schedule_i",
+    "pdf_field": "Amount 9 Debtor 1",
+    "producer": "derived:schedule_i_other_income_total_debtor1",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Amount 9 Debtor 1",
+    "evidence": "Field index: Amount 9 Debtor 1 p2 line 9, column 'For Debtor 1', 'Add all other income.' (adjudicated). Step 2 spec §6.2 (schedule_i_other_income_total_debtor1: the sum of 8a-8h; line 9) and §6.1 (8b and 8f are never asked and count as zero). The audit has no row for this box."
   }
 ]
PATCH
```

The addendum gains a row for each ADD box (§7.4): `Amount 3 Debtor 1`, `Amount 4 Debtor 1`, `Amount 4 Debtor 1a`, `Amount 7 Debtor 1`, `Other income 8h` and `Amount 9 Debtor 1`. Each cites the box's field-index label and the spec section or owner answer that decided it. The seven MOVED boxes need no row: the moved-here join asserts them through their verified audit rows. The list loses exactly the 10 entries the moves orphan, deleted by hand (R3).

- [ ] **Step 6: Run the Schedule I tests again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line apps/forms/tests/test_schedule_i_schema.py apps/forms/tests/test_derivations.py apps/forms/tests/test_oracle_tier3.py -q -p no:cacheprovider 2>&1 | tail -40
```

Expected: `203 passed, 22 xfailed`.

- [ ] **Step 7: Write the failing upload-page test**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/__tests__/DocumentUploadPage.test.tsx b/frontend/src/pages/__tests__/DocumentUploadPage.test.tsx
index 49f557c..4ca92dc 100644
--- a/frontend/src/pages/__tests__/DocumentUploadPage.test.tsx
+++ b/frontend/src/pages/__tests__/DocumentUploadPage.test.tsx
@@ -112,6 +112,18 @@ describe('DocumentUploadPage', () => {
     expect(sentTypes).toEqual(['creditor_bill', 'pay_stub', 'credit_report']);
   });

+  it('never tells the filer a pay stub fills in their pay', async () => {
+    renderUploadPage();
+    const payStubs = screen.getByRole('region', { name: 'Pay stubs' });
+
+    // Schedule I prints the pay typed on the Income step; a stub supplies only the employer's name.
+    expect(payStubs).toHaveTextContent(
+      "Your employer's name is used for your income form (Schedule I)."
+    );
+    expect(payStubs).not.toHaveTextContent(/pay before taxes/i);
+    await readyZone('Pay stubs');
+  });
+
   it('counts only the files that were read in the summary, in plain words', async () => {
     serveDocuments({ 1: { status: 'failed', failure_reason: 'nothing_found' } });
     renderUploadPage();
PATCH
```

The test requires the Pay stubs area to say only that the employer's name is used, and never "pay before taxes".

- [ ] **Step 8: Run it and watch it fail**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/DocumentUploadPage.test.tsx 2>&1 | tail -25
```

Expected: FAIL — `Tests  1 failed | 15 passed (16)`, with `Expected element to have text content`. The area still says the stub's pay before taxes is used for Schedule I.

- [ ] **Step 9: Say what a pay stub is used for**

```bash
git apply <<'PATCH'
diff --git a/frontend/src/pages/DocumentUploadPage.tsx b/frontend/src/pages/DocumentUploadPage.tsx
index 66877c9..f535cdb 100644
--- a/frontend/src/pages/DocumentUploadPage.tsx
+++ b/frontend/src/pages/DocumentUploadPage.tsx
@@ -16,7 +16,7 @@ const UPLOAD_AREAS = [
   {
     type: 'pay_stub',
     label: 'Pay stubs',
-    help: "Recent pay stubs from your job. Your employer's name and your pay before taxes are used for your income form (Schedule I).",
+    help: "Recent pay stubs from your job. Your employer's name is used for your income form (Schedule I).",
   },
   {
     type: 'credit_report',
PATCH
```

Schedule I prints the pay typed on the Income step; a stub supplies only the employer's name (Q14). The help text is §5.1's sentence, word for word.

- [ ] **Step 10: Run the upload-page tests again**

```bash
set -eo pipefail
cd frontend && NO_COLOR=1 npx vitest run src/pages/__tests__/DocumentUploadPage.test.tsx 2>&1 | tail -25
```

Expected: `Tests  16 passed (16)`.

- [ ] **Step 11: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2b.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2029 passed, 1 skipped, 55 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  358 passed (358)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 12: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 13: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_api_readback.py \
  backend/apps/forms/tests/test_derivations.py \
  backend/apps/forms/tests/test_oracle_tier3.py \
  backend/apps/forms/tests/test_schedule_i_schema.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/schedule_i.json \
  frontend/src/pages/DocumentUploadPage.tsx \
  frontend/src/pages/__tests__/DocumentUploadPage.test.tsx
git commit -F - <<'MSG'
fix(forms): Schedule I prints each income source on the line that asks for it, and lines 4, 7 and 9 add them

Schedule I's income lines follow the step 2 spec's per-source table
(§5.5; Appendix A.7; Appendix B):
- line 2 prints wages and tips (schedule_i_net_wages_debtor1, moved from
  line 3). It replaces the pay stub's gross pay (ingested paystub.gross)
  in the same commit, because a box takes one binding (E006). No form
  reads a stub's gross pay any more; a stub supplies only the employer's
  name (Q14);
- line 3 prints overtime (new rule schedule_i_overtime_debtor1);
- line 4, its copy at the top of page 2 (Amount 4 Debtor 1a) and line 7
  print line 2 + line 3 (new rule schedule_i_gross_income_debtor1). Line 7
  equals gross until payroll deductions are asked in step 3 (§5.5, §6.1);
- the six other sources leave payroll-deduction lines 5a-5g for the lines
  that ask for them: rental 8a, child support and alimony 8c, unemployment
  8d, Social Security 8e, pension 8g and other income 8h, with "Other
  income" in 8h's Specify box above $0 (other_income_label, shared with
  122A-1 line 10);
- line 9 adds 8a-8h (new rule schedule_i_other_income_total_debtor1); 8b
  and 8f are never asked and count as zero.

The boxes DigniFi never fills print blank, never 0.00 (B2): the Chapter 13
supplement date, interest on 5e and payroll deductions on line 6.

Rules that lost their last binding are deleted: today_iso,
schedule_i_self_employment_debtor1, schedule_i_interest_debtor1,
schedule_i_total_deductions_debtor1 and schedule_i_net_income_debtor1,
with _line8a_total_gross_income, whose only caller was the last.
With the last of them goes _get_income_field (§5.5), and with it the
two unbound rules that still called it and read attributes IncomeInfo
never had: schedule_i_gross_wages_debtor1 (named in §5.5) and
line4_interest_dividends.
test_api_readback.py loses its today_iso branch and its signing-date
comments, since no form prints today's date any more.

The upload page's Pay stubs area stops saying the stub's pay before
taxes is used: its help text is now the spec's wording (§5.1), "Recent
pay stubs from your job. Your employer's name is used for your income
form (Schedule I)."

Oracle:
- step2_verification.json gains the six ADD rows: lines 3, 4, 4's copy,
  7, 8h's Specify box and 9 (32 -> 38). The seven moved boxes (2, 8a, 8c,
  8d, 8e, 8g, 8h) are asserted by the moved-here join.
- Tier 3 gains Appendix D's row for all five personas: 8e prints 0.00
  (Social Security typed as $0).

Clears 10 known-defect entries (64 -> 54), all tier 2 orphans: the
supplement date, lines 3 and 4, and 5a-5g.

ASSERTED_CASES 413 -> 413 (0), measured by diffing the collected IDs:
- 13 tier 2 cases left with their bindings (the supplement date, line 2's
  pay-stub key, 3, 4, 5a-5g, 6 and line 7's old rule): 10 xfails, 3 passes;
- 13 new cases: 7 moved-here joins (2, 8a, 8c, 8d, 8e, 8g, 8h) and the 6
  addendum rows. All pass.

New tests:
- test_each_income_source_prints_on_its_own_line (§7.7): each of the ten
  sources on its Schedule I and 122A-1 boxes, Social Security only on
  Schedule I 8e
- test_lines_4_7_and_9_add_the_lines_the_form_names
- test_lines_schedule_i_never_asks_about_print_nothing
- schedule_i_overtime_debtor1, schedule_i_gross_income_debtor1 and
  schedule_i_other_income_total_debtor1 join the per-source rule tests in
  test_derivations.py
- DocumentUploadPage: never tells the filer a pay stub fills in their
  pay

Refs DIG-36, DIG-56, DIG-82, DIG-161
MSG
git status --short
```

### Task 11: Count Social Security in Schedule I lines 10 and 12, and in 106Sum line 4 and Schedule J 23a, which copy them

_Built and verified as commit `533f78e` on `plan/forms-step2b`._

**Files:**

- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_derivations.py`
- Modify: `backend/apps/forms/tests/test_form_106sum_schema.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `backend/apps/forms/tests/test_schedule_i_schema.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/form_106sum.json`
- Modify: `data/forms/schemas/schedule_i.json`

**Interfaces:**

- Consumes:
  - `IncomeInfo.SOURCE_FIELDS` (2a), the ten Income step amounts, and 2a's `_income_amounts(session, *fields)`, which returns their sum or `""` when the filer gave none of them.
  - The `cmi` rule (2a): current monthly income, without Social Security. It stays bound on 122A-1 `Quest11` and `Debto1.Quest11` (Task 9) and 106Sum `8`. `views._prepare` refuses `IncomeNotSplit` before any form is built (2a).
  - `total_debts` (every `DebtInfo.amount_owed`), bound on 106Sum `4` until now and called by Task 3's `_total_debts_range`.
  - Task 10's Schedule I bindings and its tables in `test_schedule_i_schema.py`: `LINE_BY_SOURCE`, `LINE_TOTALS` and the imported `TEN_SOURCES`. `SWITCHED_RULES` in `test_derivations.py`.
  - The `populated_session` fixture of `test_form_106sum_schema.py`: $1,200 wages, a $50,000 secured debt, a $10,000 unsecured debt and a $5,000 priority debt.
- Produces:
  - Rule `schedule_i_income_total` → `str`: `_income_amounts(session, *IncomeInfo.SOURCE_FIELDS)`, all ten sources with Social Security, blank with no `IncomeInfo` or when all ten are empty. Task 13's `schedule_j_monthly_net_income` (23c) subtracts from it.
  - `schedule_j_total_income` keeps its key and now maps to `_schedule_i_income_total`. `_schedule_j_total_income` (CMI) and the `total_unsecured_debts` rule are deleted.
  - `schedule_i.json` (24 objects): `Amount 10 Debtor 1` and `Amount 12` re-ruled in place to `schedule_i_income_total`; a new object `Amount 10` (page 2) ← `schedule_i_income_total`.
  - `form_106sum.json`: `3c` ← `total_debts` and `4` ← `schedule_i_income_total`, both re-ruled in place.
  - In `test_schedule_i_schema.py`: the tables `COMBINED_INCOME` and `INCOME_LINES`, and the tests `test_combined_monthly_income_counts_social_security_wherever_it_is_copied` and `test_income_lines_print_blank_until_the_filer_gives_income_by_source`, which replaces `test_empty_session_is_asked_for_income_by_source`. In `test_form_106sum_schema.py`: `test_total_liabilities_print_on_3c_and_combined_monthly_income_on_line_4`. `SWITCHED_RULES` gains `schedule_i_income_total` and `schedule_j_total_income`, each over all ten sources.
  - `step2_verification.json` 38 → 42 rows; `ASSERTED_CASES = 414`; `known_defects.json` 54 → 46 entries.

**Decisions already made in this task:**

- C1 (§6.1), two income totals: CMI, without Social Security, stays on 122A-1 line 11 and 106Sum line 8 (`cmi`). Schedule I's own total, all ten sources with Social Security, is the new `schedule_i_income_total` on Schedule I line 10 (both columns) and line 12, 106Sum line 4, and Schedule J 23a.
- The new rule adds the ten in Decimal through `_income_amounts`, never through the float `IncomeInfo.calculate_total_monthly_income()`. An empty source counts as zero once another was given, and the total is blank when none was (B2).
- R4: `Amount 12` is re-ruled in place and never loses its binding. Schedule J `23a` keeps its binding and its key: `schedule_j_total_income` now points at the same function, one figure on both forms, as `fee_waiver_monthly_expenses` points at `_schedule_j_total_expenses`. Tier 3's `Amount 12` and `23a` rows keep passing for all five personas, because every seed's Social Security is $0.
- `Amount 10`, line 10's total column, was unbound, so it gets one new object; the re-rule in place applies to the two bound boxes. Line 10's spouse column and line 11 are never asked and count as zero (§6.1; the 6c decision covers lines 10 and 12).
- The 106Sum chain moves in this commit with the income total (Appendix B): `3c` is re-ruled in place to `total_debts` (total liabilities, every debt), not given a second object (E006), and `4` is re-ruled in place to the Schedule I total. `total_unsecured_debts` lost its last binding (3c) and is deleted; nothing else calls it. The re-ruled objects are retitled from their index lines.
- Schedule I and Schedule J no longer raise `IncomeNotSplit` when income isn't stored by source; their income lines print blank. The filer still meets the refusal first: `views._prepare` works the means test out before any form is built, and `test_income_resume.py` passes unchanged. So `test_empty_session_is_asked_for_income_by_source` in `test_schedule_i_schema.py` is replaced on purpose; 106Sum's test of the same name stays, because line 8 is still `cmi`.
- With the 106Sum fixture's priority debt, `3c` (65000.00) is not `2` + `3b` (60000.00): `3a` stays blank until priority is asked, and `3b` still leaves priority out until Task 16. No persona has a priority debt.
- `3c` is MOVED: the moved-here join asserts it through the verified audit row on box `4` (`correct_target` 3c), so it has no addendum row. The four ADD boxes get one each, producer `derived:schedule_i_income_total`: 106Sum `4` and Schedule I `Amount 10 Debtor 1`, `Amount 10` and `Amount 12`.
- `ASSERTED_CASES` 413 → 414 (+1), measured by diffing the collected IDs: 4 tier 2 cases leave with their keys (106Sum `3c` under `total_unsecured_debts`, `4` under `total_debts` (the xfail), and `Amount 10 Debtor 1` and `Amount 12` under `cmi`), and 5 arrive, all passing: `3c` under `total_debts` through moved-here, and the 4 addendum rows.
- Known defects (R3): delete exactly 8 DIG-79 entries: 1 tier 2 orphan, 106Sum `4` under `derived:total_debts`; and 7 tier 3 strict XPASS, 106Sum `3c` for james and deshawn and 106Sum `4` for all five personas. 54 → 46. Appendix D adds no tier 3 row here.
- `CLAUDE.md`'s sentence "Until 2b moves the bindings, Schedule I line 3 prints wages and tips, and Schedule I lines 10 and 12 and Schedule J 23a print CMI …" is false from this commit, and `test_cmi_in_field_map`'s name goes stale. Task 18 rewrites both; leave them.

- [ ] **Step 1: Write the failing income-total tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_derivations.py b/backend/apps/forms/tests/test_derivations.py
index 9eb30cb..b4ac498 100644
--- a/backend/apps/forms/tests/test_derivations.py
+++ b/backend/apps/forms/tests/test_derivations.py
@@ -150,6 +150,9 @@ SWITCHED_RULES = {
     "line5a_pension_retirement": ["monthly_pension"],
     "line7_other_income": ["monthly_other_income"],
     "line3_alimony": ["monthly_alimony"],
+    # Schedule I line 12 and Schedule J 23a, which copies it: Social Security included (C1)
+    "schedule_i_income_total": list(TEN_SOURCES),
+    "schedule_j_total_income": list(TEN_SOURCES),
 }


diff --git a/backend/apps/forms/tests/test_form_106sum_schema.py b/backend/apps/forms/tests/test_form_106sum_schema.py
index 363b8e0..5642cfd 100644
--- a/backend/apps/forms/tests/test_form_106sum_schema.py
+++ b/backend/apps/forms/tests/test_form_106sum_schema.py
@@ -126,6 +126,19 @@ class TestForm106SumSchema:
         assert field_map["2"] == "50000.00"  # secured
         assert field_map["3b"] == "10000.00"  # nonpriority unsecured

+    def test_total_liabilities_print_on_3c_and_combined_monthly_income_on_line_4(
+        self, populated_session
+    ):
+        # 3c totals every debt, secured, unsecured and priority alike. Line 4 copies
+        # Schedule I line 12, which counts Social Security; line 8, CMI, never does (C1).
+        income = populated_session.income_info
+        income.monthly_social_security = Decimal("800.00")
+        income.save()
+        field_map = resolve(load_schema("form_106sum"), populated_session)
+        assert field_map["3c"] == "65000.00"  # 50000 + 10000 + 5000
+        assert field_map["4"] == "2000.00"  # 1200 wages + 800 Social Security
+        assert field_map["8"] == "1200.00"
+
     def test_priority_debts_print_nowhere_until_the_filer_is_asked_which_have_priority(
         self, populated_session
     ):
diff --git a/backend/apps/forms/tests/test_schedule_i_schema.py b/backend/apps/forms/tests/test_schedule_i_schema.py
index 11c5652..cc1653e 100644
--- a/backend/apps/forms/tests/test_schedule_i_schema.py
+++ b/backend/apps/forms/tests/test_schedule_i_schema.py
@@ -7,7 +7,6 @@ import pytest
 from django.contrib.auth import get_user_model

 from apps.districts.models import District
-from apps.eligibility.cmi import IncomeNotSplit
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.forms.tests.test_derivations import TEN_SOURCES
@@ -50,6 +49,19 @@ NEVER_ASKED = {
     "Amount 8b Debtor 1",  # interest and dividends
     "Amount 8f Debtor 1",  # other government assistance
 }
+# Schedule I's combined monthly income and every box that copies it: all ten sources,
+# Social Security included (step 2 spec §6.1, C1), 1 + 2 + 4 + ... + 512.
+COMBINED_INCOME = {
+    ("schedule_i", "Amount 10 Debtor 1"): "1023.00",  # line 10: line 7 + line 9
+    ("schedule_i", "Amount 10"): "1023.00",  # line 10's total: no spouse column yet
+    ("schedule_i", "Amount 12"): "1023.00",  # line 12: line 10 + line 11, never asked
+    ("form_106sum", "4"): "1023.00",  # copies Schedule I line 12
+    ("schedule_j", "23a"): "1023.00",  # copies Schedule I line 12
+    # Current monthly income leaves Social Security (32) out.
+    ("form_122a1", "Quest11"): "991.00",  # 122A-1 line 11
+    ("form_106sum", "8"): "991.00",  # copies 122A-1 line 11
+}
+INCOME_LINES = {"Amount 10 Debtor 1", "Amount 10", "Amount 12", *LINE_BY_SOURCE, *LINE_TOTALS}


 @pytest.fixture
@@ -148,7 +160,27 @@ class TestScheduleISchema:

         assert sorted(NEVER_ASKED & field_map.keys()) == []

-    def test_empty_session_is_asked_for_income_by_source(self, session):
-        # Lines 10 and 12 print CMI until 2b, and a filer who gave no income has none.
-        with pytest.raises(IncomeNotSplit):
-            resolve(load_schema("schedule_i"), session)
+    def test_combined_monthly_income_counts_social_security_wherever_it_is_copied(self, session):
+        # Schedule I line 12 is all of the filer's income; current monthly income is not
+        # (11 U.S.C. § 101(10A)(B)). Each form prints the one its line asks for.
+        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
+
+        forms = {form_type for form_type, _ in COMBINED_INCOME}
+        printed = {form_type: resolve(load_schema(form_type), session) for form_type in forms}
+
+        assert {
+            (form_type, box): printed[form_type].get(box) for form_type, box in COMBINED_INCOME
+        } == COMBINED_INCOME
+
+    def test_income_lines_print_blank_until_the_filer_gives_income_by_source(self, session):
+        # Forms are refused before they are built (views._prepare, test_income_resume.py);
+        # Schedule I and Schedule J line 23a never print an income the filer didn't give.
+        def income_printed():
+            schedule_i = resolve(load_schema("schedule_i"), session)
+            schedule_j = resolve(load_schema("schedule_j"), session)
+            return sorted(INCOME_LINES & schedule_i.keys()), schedule_j.get("23a")
+
+        assert income_printed() == ([], None)
+        # A total saved before income was stored by source is never split for the filer.
+        IncomeInfo.objects.create(session=session, monthly_income=[3000] * 6)
+        assert income_printed() == ([], None)
PATCH
```

With `TEN_SOURCES`, `test_combined_monthly_income_counts_social_security_wherever_it_is_copied` requires 1023.00 (all ten) on Schedule I `Amount 10 Debtor 1`, `Amount 10` and `Amount 12`, 106Sum `4` and Schedule J `23a`, and 991.00 (CMI, without Social Security's 32) on 122A-1 `Quest11` and 106Sum `8`. It is the only test that tells the two totals apart, since every seed's Social Security is $0. `test_income_lines_print_blank_until_the_filer_gives_income_by_source` requires Schedule I's income lines and Schedule J `23a` to print nothing, both with no `IncomeInfo` and with a total saved before income was stored by source. The 106Sum test adds $800 of Social Security to the fixture's wages and requires 65000.00 on `3c`, 2000.00 on `4` and 1200.00 on `8`. Both totals join `SWITCHED_RULES`.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line apps/forms/tests/test_schedule_i_schema.py apps/forms/tests/test_form_106sum_schema.py apps/forms/tests/test_derivations.py -q -p no:cacheprovider 2>&1 | tail -20
```

Expected: FAIL — `8 failed, 87 passed`. The new rule is missing, so its cases raise `KeyError: 'schedule_i_income_total'`. The rule schedule_j_total_income still returns CMI, `assert '991.00' == '1023.00'`, and raises `IncomeNotSplit` when no source was given, as the blank-lines test does through the cmi rule on lines 10 and 12. The 106Sum test reads `assert '15000.00' == '65000.00'`, because 3c prints unsecured debts only.

The C1 test finds CMI's 991.00 where the Schedule I total belongs, total debts on 106Sum line 4, and nothing on line 10's total column.

- [ ] **Step 3: Add the Schedule I income total and bind it where the forms copy it**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index 57b8a47..143ec3b 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -125,13 +125,6 @@ def _total_nonpriority_unsecured(session: IntakeSession) -> str:
     return _fmt(_sum_encrypted(qs, "amount_owed"))


-def _total_unsecured_debts(session: IntakeSession) -> str:
-    from apps.intake.models import DebtInfo
-
-    qs = DebtInfo.objects.filter(session=session, is_secured=False)
-    return _fmt(_sum_encrypted(qs, "amount_owed"))
-
-
 def _total_debts(session: IntakeSession) -> str:
     from apps.intake.models import DebtInfo

@@ -418,6 +411,17 @@ def _schedule_i_other_income_total_debtor1(session: IntakeSession) -> str:
     )


+def _schedule_i_income_total(session: IntakeSession) -> str:
+    """
+    Schedule I lines 10 and 12: all ten sources, Social Security included (C1), unlike CMI.
+
+    Line 10's spouse column and line 11 are never asked and count as zero (step 2 spec §6.1).
+    """
+    from apps.intake.models import IncomeInfo
+
+    return _income_amounts(session, *IncomeInfo.SOURCE_FIELDS)
+
+
 # ---------------------------------------------------------------------------
 # Schedule J expense line item derivations
 # ---------------------------------------------------------------------------
@@ -440,10 +444,6 @@ def _schedule_j_total_expenses(session: IntakeSession) -> str:
         return "0.00"


-def _schedule_j_total_income(session: IntakeSession) -> str:
-    return _fmt(Decimal(_cmi(session)))
-
-
 def _means_test_disposable_income(session: IntakeSession) -> str:
     try:
         mt = session.means_test
@@ -498,7 +498,6 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "total_assets": _total_assets,
     "total_secured_debts": _total_secured_debts,
     "total_nonpriority_unsecured": _total_nonpriority_unsecured,
-    "total_unsecured_debts": _total_unsecured_debts,
     "total_debts": _total_debts,
     "total_bank_accounts": _total_bank_accounts,
     "total_retirement_accounts": _total_retirement_accounts,
@@ -547,6 +546,7 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "schedule_i_rental_debtor1": _schedule_i_rental_debtor1,
     "schedule_i_other_income_debtor1": _schedule_i_other_income_debtor1,
     "schedule_i_other_income_total_debtor1": _schedule_i_other_income_total_debtor1,
+    "schedule_i_income_total": _schedule_i_income_total,
     # Schedule J expense line item derivations
     "schedule_j_rent_or_mortgage": lambda s: _fmt(_get_expense_field(s, "rent_or_mortgage")),
     "schedule_j_utilities": lambda s: _fmt(_get_expense_field(s, "utilities")),
@@ -565,7 +565,8 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
         _get_expense_field(s, "other_expenses") + _get_expense_field(s, "child_support_paid")
     ),
     "schedule_j_total_expenses": _schedule_j_total_expenses,
-    "schedule_j_total_income": _schedule_j_total_income,
+    # Line 23a is Schedule I line 12: one figure on both forms
+    "schedule_j_total_income": _schedule_i_income_total,
     # Form 122A-2 means test expense deduction derivations
     "means_test_disposable_income": _means_test_disposable_income,
     "means_test_total_deductions": _means_test_total_deductions,
diff --git a/data/forms/schemas/form_106sum.json b/data/forms/schemas/form_106sum.json
index ce22d6c..a91bd4a 100644
--- a/data/forms/schemas/form_106sum.json
+++ b/data/forms/schemas/form_106sum.json
@@ -127,11 +127,11 @@
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Total unsecured debts",
+      "label": "Total liabilities",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "total_unsecured_debts",
+      "rule": "total_debts",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -144,11 +144,11 @@
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Total debts",
+      "label": "Combined monthly income (Schedule I line 12)",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "total_debts",
+      "rule": "schedule_i_income_total",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
diff --git a/data/forms/schemas/schedule_i.json b/data/forms/schemas/schedule_i.json
index 966d1d7..b1a2d51 100644
--- a/data/forms/schemas/schedule_i.json
+++ b/data/forms/schemas/schedule_i.json
@@ -161,11 +161,28 @@
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Debtor 1 total income",
+      "label": "Debtor 1 monthly income (line 7 + line 9)",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "cmi",
+      "rule": "schedule_i_income_total",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "Amount 10",
+      "type": "text",
+      "source": "derived",
+      "page": 2,
+      "label": "Monthly income, Debtor 1 + Debtor 2",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "schedule_i_income_total",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -178,11 +195,11 @@
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Total current monthly income",
+      "label": "Combined monthly income",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "cmi",
+      "rule": "schedule_i_income_total",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
PATCH
```

`schedule_i_income_total` adds the ten sources, and `schedule_j_total_income` points at it, so Schedule J 23a prints Schedule I line 12 (§5.5). Schedule I lines 10 and 12 are re-ruled in place, line 10's total column gets its object, and the 106Sum chain moves total debts to `3c` and the income total to `4`. `_schedule_j_total_income` and `total_unsecured_debts` lost their last use and are deleted.

- [ ] **Step 4: Record the addendum rows, the new count and the cleared entries**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index 7c0ac20..2711666 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -1,12 +1,4 @@
 [
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "4",
-    "tier": "2",
-    "case": "derived:total_debts",
-    "class": "wrong_box",
-    "ticket": "DIG-79"
-  },
   {
     "form_type": "form_107",
     "pdf_field": "Income 5a Debtor 1",
@@ -255,62 +247,6 @@
     "class": "wrong_box",
     "ticket": "DIG-52"
   },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "3c",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "3c",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "4",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "4",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "4",
-    "tier": "3",
-    "case": "maria",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "4",
-    "tier": "3",
-    "case": "priya",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "4",
-    "tier": "3",
-    "case": "sarah",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
   {
     "form_type": "schedule_j",
     "pdf_field": "22c",
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index 531cf62..52bffc2 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 413
+ASSERTED_CASES = 414


 def _audit_dir():
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index 069c012..ac7280c 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -378,5 +378,45 @@
     "status": "confirmed",
     "correct_target": "Amount 9 Debtor 1",
     "evidence": "Field index: Amount 9 Debtor 1 p2 line 9, column 'For Debtor 1', 'Add all other income.' (adjudicated). Step 2 spec §6.2 (schedule_i_other_income_total_debtor1: the sum of 8a-8h; line 9) and §6.1 (8b and 8f are never asked and count as zero). The audit has no row for this box."
+  },
+  {
+    "schema": "form_106sum",
+    "pdf_field": "4",
+    "producer": "derived:schedule_i_income_total",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "4",
+    "evidence": "Field index: 4 p1 line 4, 'Line 4: Copy your combined monthly income from line 12 of Schedule I' (adjudicated). Step 2 spec §5.5 (a separate Schedule I income total, bound to Schedule I lines 10 and 12 and 106Sum line 4), §6.1 C1 (two income totals: CMI without Social Security on 106Sum line 8, the Schedule I income total on line 4) and §6.2 (schedule_i_income_total); Appendix B's 106Sum chain. The audit's verified row on this box judged the old total_debts binding, which belongs on 3c."
+  },
+  {
+    "schema": "schedule_i",
+    "pdf_field": "Amount 10 Debtor 1",
+    "producer": "derived:schedule_i_income_total",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Amount 10 Debtor 1",
+    "evidence": "Field index: Amount 10 Debtor 1 p2 line 10, column 'For Debtor 1', 'Calculate monthly income. Add line 7 + line 9.' (adjudicated). Line 7 (lines 2 + 3, Schedule I's gross income, until payroll deductions are asked) plus line 9 (8a-8h) is all ten Income step sources. Step 2 spec §5.5, §6.1 B1 and C1 (lines 10 and 12 take the Schedule I income total, Social Security included) and §6.2 (schedule_i_income_total). The audit's verified row on this box judged the old cmi binding, which leaves Social Security out."
+  },
+  {
+    "schema": "schedule_i",
+    "pdf_field": "Amount 10",
+    "producer": "derived:schedule_i_income_total",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Amount 10",
+    "evidence": "Field index: Amount 10 p2 line 10, column 'Total (Debtor 1 + Debtor 2)', 'Add the entries in line 10 for Debtor 1 and Debtor 2 or non-filing spouse' (adjudicated). Step 2 never fills the spouse column, so the total equals Debtor 1's line 10: step 2 spec §6.1 (totals that count an unasked line as zero; line 10's combined column adds a spouse column step 2 never fills; the section 6c decision covers Schedule I line 10), §5.5 and §6.2 (schedule_i_income_total). The audit has no row for this box."
+  },
+  {
+    "schema": "schedule_i",
+    "pdf_field": "Amount 12",
+    "producer": "derived:schedule_i_income_total",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Amount 12",
+    "evidence": "Field index: Amount 12 p2 line 12, column 'Combined monthly income', 'Add the amount in the last column of line 10 to the amount in line 11 (Combined monthly income)' (adjudicated). Line 11 (others' regular contributions) is never asked and counts as zero: step 2 spec §6.1 (totals that count an unasked line as zero; the section 6c decision covers Schedule I line 12) and C1 (the Schedule I income total, Social Security included), §5.5 and §6.2 (schedule_i_income_total). Appendix B R4: the box keeps a binding. The audit's verified row on this box judged the old cmi binding, which leaves Social Security out."
   }
 ]
PATCH
```

The addendum gains the four ADD rows, each citing the box's field-index label and the spec sections that decided it (§5.5, §6.1 C1, the 6c totals decision, Appendix B R4 and the 106Sum chain). `ASSERTED_CASES` becomes 414. The list loses exactly the 8 entries this commit orphans or turns into a strict XPASS, deleted by hand (R3).

- [ ] **Step 5: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line apps/forms/tests/test_schedule_i_schema.py apps/forms/tests/test_form_106sum_schema.py apps/forms/tests/test_derivations.py -q -p no:cacheprovider 2>&1 | tail -20
```

Expected: `95 passed`.

- [ ] **Step 6: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2b.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2047 passed, 1 skipped, 47 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  358 passed (358)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

This task changes no page or flow, so the journeys don't run here.

- [ ] **Step 7: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_derivations.py \
  backend/apps/forms/tests/test_form_106sum_schema.py \
  backend/apps/forms/tests/test_oracle_tier2.py \
  backend/apps/forms/tests/test_schedule_i_schema.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/form_106sum.json \
  data/forms/schemas/schedule_i.json
git commit -F - <<'MSG'
fix(forms): Schedule I lines 10 and 12 count Social Security, and so do 106Sum line 4 and Schedule J 23a, which copy them

The step 2 spec keeps two income totals (§6.1 C1; §5.5; Appendix A.4,
A.7; Appendix B R4 and the 106Sum chain):
- Current monthly income, without Social Security, stays on 122A-1
  line 11 and 106Sum line 8 (cmi).
- Schedule I's own total, all ten Income step sources with Social
  Security, is the new rule schedule_i_income_total. It prints blank
  when the filer gave none of them, counting an empty one as zero once
  another was given (B2).

Where the Schedule I total prints:
- Schedule I line 10 for Debtor 1 (Amount 10 Debtor 1) and line 12
  (Amount 12) are re-ruled in place from cmi. Amount 12 never loses its
  binding (R4). Line 10 now equals line 7 + line 9.
- Line 10's total column (Amount 10), unbound until now, gets a new
  object. Line 10's spouse column and line 11 are never asked and count
  as zero (§6.1).
- Schedule J 23a keeps its binding and its key, schedule_j_total_income,
  which now points at the same function: one figure on both forms. The
  old body (_schedule_j_total_income, CMI) is deleted.
- 106Sum chain: 4's total_debts moves to 3c, total liabilities (every
  debt), re-ruled in place. Line 4 is re-ruled in place to the Schedule I
  total. total_unsecured_debts lost its last binding (3c) and is deleted;
  nothing else called it.
- The re-ruled objects are retitled from their index lines.

Schedule I and Schedule J no longer raise IncomeNotSplit when income
isn't entered by source; their income lines print blank. The filer
still meets the refusal first: views._prepare works the means test out
before any form is built, and test_income_resume.py passes unchanged.
test_schedule_i_schema.py's test_empty_session_is_asked_for_income_by_source
is replaced on purpose by
test_income_lines_print_blank_until_the_filer_gives_income_by_source.
106Sum's own empty-session test is unchanged, because line 8 is still
CMI.

Oracle:
- step2_verification.json gains 4 ADD rows (38 -> 42): 106Sum 4 and
  Schedule I Amount 10 Debtor 1, Amount 10 and Amount 12. 106Sum 3c is
  MOVED, and the moved-here join asserts it through the verified row on
  box 4.
- No tier 3 rows are added. Schedule I Amount 12 and Schedule J 23a keep
  passing for all five personas, because the seeds' Social Security is
  $0.

Clears 8 known-defect entries (54 -> 46):
- 1 tier 2 orphan: 106Sum 4 under derived:total_debts.
- 7 tier 3 strict XPASS: 106Sum 3c for james and deshawn, and 106Sum 4
  for all five personas.

ASSERTED_CASES 413 -> 414 (+1), measured by diffing the collected IDs:
- 4 tier 2 cases left with their keys: 3c total_unsecured_debts,
  4 total_debts (the xfail), and Amount 10 Debtor 1 and Amount 12 on
  cmi.
- 5 arrived: 3c total_debts through moved-here, and the 4 addendum rows.
  All pass.

New tests:
- test_combined_monthly_income_counts_social_security_wherever_it_is_copied:
  with ten distinct sources, Schedule I 10, 10's total and 12, 106Sum 4
  and Schedule J 23a print 1023.00, while 122A-1 line 11 and 106Sum 8
  print CMI, 991.00.
- test_total_liabilities_print_on_3c_and_combined_monthly_income_on_line_4
- test_income_lines_print_blank_until_the_filer_gives_income_by_source
- schedule_i_income_total and schedule_j_total_income join the
  per-source rule tests in test_derivations.py.

Refs DIG-79, DIG-82, DIG-36
MSG
git status --short
```

### Task 12: Print each Schedule J expense on the line that asks for it, and only above $0

_Built and verified as commit `fc7741b` on `plan/forms-step2b`._

**Files:**

- Create: `backend/apps/forms/tests/test_schedule_j_schema.py`
- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/schedule_j.json`

**Interfaces:**

- Consumes:
  - `ExpenseInfo`'s 13 amounts (non-null decimals, default $0): `rent_or_mortgage`, `utilities`, `home_maintenance`, `vehicle_payment`, `vehicle_insurance`, `vehicle_maintenance`, `food_and_groceries`, `clothing`, `medical_expenses`, `childcare`, `child_support_paid`, `insurance_not_deducted` and `other_expenses`.
  - The `schedule_j_*` expense rules already bound in `schedule_j.json`, five of which 122A-2 also binds: food on `Quest6`, rent on `Quest8`, utilities on `Quest9`, vehicle maintenance on `Quest12`, and the car payment on `Quest13D`, `Quest14` and `Quest15`.
  - `schedule_j_total_expenses` (22a, and 103B line 6 through `fee_waiver_monthly_expenses`) and Task 11's `schedule_j_total_income` (23a), both unchanged.
  - Tier 3's Schedule J `18` blank row (Task 1).
- Produces:
  - Helpers in `derivations.py`: `_expense_amount(session, field) -> Decimal` ($0 when the Expenses step was never saved), `_expense_line(session, field) -> str` (the amount when it is above $0, else `""`) and `_expense_label(session, field, label) -> str` (the label when its amount is above $0).
  - The 11 moved expense rules print through `_expense_line`. `schedule_j_other_expenses` prints `other_expenses` only, above $0.
  - New rules: `schedule_j_support_paid` (`child_support_paid` above $0; Task 14 binds it to 122A-2 line 19), `schedule_j_utilities_label` ("Utilities (combined)") and `schedule_j_insurance_label` ("Insurance (combined)"). `schedule_j_childcare` keeps its key for Task 14's 122A-2 line 21. `_get_expense_field` is deleted.
  - `schedule_j.json` (19 objects): `4` rent, `4c` home maintenance, `6d` utilities with `Other 6d` its label, `7` food, `8` childcare, `9` clothing, `11` medical, `12` vehicle maintenance, `15c` vehicle insurance, `15d` insurance not deducted with `Other 15d` its label, `17a` the car payment, `18` support paid, `21` other expenses. `10`, `14`, `15a`, `15b`, `16`, `17b`, `17c` and `20a` are unbound.
  - The new test file `test_schedule_j_schema.py` with the tables `EXPENSES`, `LINE_BY_EXPENSE` and `VACATED`, and the tests `test_each_expense_prints_on_the_line_that_asks_for_it`, `test_expense_line_prints_only_above_zero` (§7.7) and `test_support_paid_prints_on_line_18_and_never_on_line_21`.
  - `step2_verification.json` 42 → 47 rows; `ASSERTED_CASES = 417`; `known_defects.json` 46 → 35 entries.

**Decisions already made in this task:**

- Option A (§6.1, the 6c decision): "An expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0." The 13 amounts are stored as $0 when nothing is entered, so $0 can't be told from "left blank". Compare with `> 0`, never `!= 0`: the −$0.01 case pins it. A session that never saved the Expenses step now prints nothing on any line (B2), where it printed 0.00.
- Owner Q4: "utilities go on 6d with "Utilities (combined)", insurance not deducted from pay on 15d with "Insurance (combined)"; each label prints only above $0. Vehicle insurance goes on 15c." The audit put utilities on 6a and this insurance on 15b; Q4 overrides both, so 6d and 15d carry addendum rows.
- Chain a (`17b` → `17a` → `12` → `6d`) and chain b (`17c` → `15c` → `9`) move in this one commit (R2), with the independent moves `10` → `4`, `14` → `4c`, `15a` → `7`, `15b` → `8`, `16` → `11` and `20a` → `15d`. `4` and `4c` are on page 1, as the field index says; the old bindings said page 2.
- `18` ← `schedule_j_support_paid` and `21` ← `schedule_j_other_expenses` (other expenses only) land together, so support paid is printed once, on its own line. Until now line 21 added support paid to other expenses.
- The Expenses step asks one car payment, so it prints on `17a`; a filer with two financed cars sees both there until step 3 splits them (§6.4, D-2).
- Totals are unchanged: 22a still adds all 13 amounts. Its bare except still prints 0.00 with no `ExpenseInfo` (pre-existing), so 22a can show 0.00 under blank lines. The API also accepts a negative expense (no lower bound, pre-existing): its line prints blank and 22a still subtracts it.
- The 12 expense rule bodies call `_expense_line`. `_get_expense_field`, whose bare except read any error as $0, lost its last caller and is deleted. `_expense_amount` keeps `Decimal(str(value))`, because a freshly created `ExpenseInfo` holds whatever Python value it was given, and an int has no `quantize`. No rule lost its last binding.
- The new and moved objects keep `"label": ""`, as every object in `schedule_j.json` already has (labels are never printed; an accepted nit).
- Between this task and Task 14, 122A-2's `Quest6`, `Quest8`, `Quest9`, `Quest12`, `Quest13D`, `Quest14` and `Quest15` share these rules and print blank at $0 instead of 0.00. Task 14 deletes those bindings. No tier 3 row covers 122A-2, and `test_api_readback.py` still finds an amount above $0 on Priya's 122A-2, from her rent.
- Tier 3 is unchanged. Appendix D's row "18 is blank" has run for all five personas since Task 1, and still passes now that 18 is bound, because every seed's support paid is $0.
- The addendum gains the five ADD rows: `6d`, `Other 6d`, `15d`, `Other 15d` and `18`; row 18 cites the audit's verified row on 21, which says support paid belongs on 18. The nine MOVED boxes (`4`, `4c`, `7`, `8`, `9`, `11`, `12`, `15c`, `17a`) are asserted by the moved-here join.
- `ASSERTED_CASES` 414 → 417 (+3), measured by diffing the collected IDs: 11 tier 2 cases leave with their bindings (the 11 xfails below), and 14 arrive, all passing: 9 moved-here joins and 5 addendum rows.
- Known defects (R3): delete exactly 11 DIG-52 tier 2 orphans, Schedule J `10`, `12`, `14`, `15a`, `15b`, `15c`, `16`, `17a`, `17b`, `17c` and `20a`, each under its old binding key. 46 → 35.

- [ ] **Step 1: Write the failing Schedule J tests**

```python file=backend/apps/forms/tests/test_schedule_j_schema.py
"""Schedule J: each expense prints on the line that asks for it, and only above $0."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import ExpenseInfo, IntakeSession

User = get_user_model()

# Each of the Expenses step's 13 amounts gets a distinct power of two, so a line that reads
# the wrong amount, or adds one too many, prints a different figure.
EXPENSES = {
    "rent_or_mortgage": Decimal("1.00"),
    "utilities": Decimal("2.00"),
    "home_maintenance": Decimal("4.00"),
    "vehicle_payment": Decimal("8.00"),
    "vehicle_insurance": Decimal("16.00"),
    "vehicle_maintenance": Decimal("32.00"),
    "food_and_groceries": Decimal("64.00"),
    "clothing": Decimal("128.00"),
    "medical_expenses": Decimal("256.00"),
    "childcare": Decimal("512.00"),
    "child_support_paid": Decimal("1024.00"),
    "insurance_not_deducted": Decimal("2048.00"),
    "other_expenses": Decimal("4096.00"),
}
# Box → what it prints with EXPENSES (step 2 spec Appendix A.8, owner Q4).
LINE_BY_EXPENSE = {
    "4": "1.00",  # rent or mortgage
    "4c": "4.00",  # home maintenance, repair and upkeep
    "6d": "2.00",  # utilities, combined on "Other"
    "Other 6d": "Utilities (combined)",
    "7": "64.00",  # food and housekeeping supplies
    "8": "512.00",  # childcare
    "9": "128.00",  # clothing
    "11": "256.00",  # medical and dental
    "12": "32.00",  # transportation, never car payments
    "15c": "16.00",  # vehicle insurance
    "15d": "2048.00",  # insurance not deducted from pay, combined on "Other"
    "Other 15d": "Insurance (combined)",
    "17a": "8.00",  # the one car payment the Expenses step asks
    "18": "1024.00",  # support paid
    "21": "4096.00",  # other expenses only
}
# Lines no expense belongs on, which the old bindings filled.
VACATED = {"10", "14", "15a", "15b", "16", "17b", "17c", "20a"}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemasj", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def test_each_expense_prints_on_the_line_that_asks_for_it(session):
    ExpenseInfo.objects.create(session=session, **EXPENSES)

    printed = resolve(load_schema("schedule_j"), session)

    assert {box: printed.get(box) for box in LINE_BY_EXPENSE} == LINE_BY_EXPENSE
    assert sorted(VACATED & printed.keys()) == []


@pytest.mark.parametrize(
    "amount,prints",
    [
        (Decimal("0.01"), True),
        (Decimal("0"), False),
        (Decimal("-0.01"), False),
        (None, False),  # the Expenses step was never saved
    ],
)
def test_expense_line_prints_only_above_zero(session, amount, prints):
    # An expense left empty is stored as $0, so $0 can't be told from "left blank": a line
    # prints only above $0, and so do 6d's and 15d's labels (step 2 spec §6.1, Q4).
    if amount is not None:
        ExpenseInfo.objects.create(session=session, **dict.fromkeys(EXPENSES, amount))

    printed = resolve(load_schema("schedule_j"), session)

    labels = {"Other 6d": "Utilities (combined)", "Other 15d": "Insurance (combined)"}
    expected = {box: labels.get(box, "0.01") for box in LINE_BY_EXPENSE} if prints else {}
    assert {box: printed[box] for box in LINE_BY_EXPENSE if box in printed} == expected


def test_support_paid_prints_on_line_18_and_never_on_line_21(session):
    # Line 21 is "Other": court-ordered support has its own line, 18.
    ExpenseInfo.objects.create(session=session, child_support_paid=Decimal("450.00"))

    printed = resolve(load_schema("schedule_j"), session)

    assert (printed.get("18"), printed.get("21")) == ("450.00", None)
```

Each of the 13 amounts is a distinct power of two, so a line that reads the wrong amount, or adds one too many, prints a different figure. `test_each_expense_prints_on_the_line_that_asks_for_it` requires each figure and both labels on their boxes and nothing on the vacated lines. `test_expense_line_prints_only_above_zero` sets all 13 amounts alike: $0.01 prints on every line with both labels, while $0, −$0.01 and an unsaved Expenses step print nothing, labels included. `test_support_paid_prints_on_line_18_and_never_on_line_21` stores $450 of support paid and requires it on 18 alone.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line apps/forms/tests/test_schedule_j_schema.py -q -p no:cacheprovider 2>&1 | tail -15
```

Expected: FAIL — `6 failed`, the last reading `assert (None, '450.00') == ('450.00', None)`: 18 is unbound and line 21 prints the support paid. The moved boxes are unbound, and every bound line prints 0.00 at $0, −0.01 below it and 0.00 with no Expenses step.

- [ ] **Step 3: Move the expense lines and print each only above $0**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index 143ec3b..34832bb 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -427,13 +427,25 @@ def _schedule_i_income_total(session: IntakeSession) -> str:
 # ---------------------------------------------------------------------------


-def _get_expense_field(session: IntakeSession, field: str) -> Decimal:
-    try:
-        expense_info = session.expense_info
-        val = getattr(expense_info, field, None)
-        return Decimal(str(val)) if val is not None else _ZERO
-    except Exception:
-        return _ZERO
+def _expense_amount(session: IntakeSession, field: str) -> Decimal:
+    """An Expenses step amount, or $0 when the step was never saved."""
+    expense_info = getattr(session, "expense_info", None)
+    return _ZERO if expense_info is None else Decimal(str(getattr(expense_info, field)))
+
+
+def _expense_line(session: IntakeSession, field: str) -> str:
+    """
+    An expense line prints only above $0 (step 2 spec §6.1, 6c option A).
+
+    An expense left empty is stored as $0, so $0 can't be told from "left blank".
+    """
+    amount = _expense_amount(session, field)
+    return _fmt(amount) if amount > 0 else ""
+
+
+def _expense_label(session: IntakeSession, field: str, label: str) -> str:
+    """An "Other. Specify:" line's text, printed only when its amount prints (Q4)."""
+    return label if _expense_amount(session, field) > 0 else ""


 def _schedule_j_total_expenses(session: IntakeSession) -> str:
@@ -548,22 +560,23 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "schedule_i_other_income_total_debtor1": _schedule_i_other_income_total_debtor1,
     "schedule_i_income_total": _schedule_i_income_total,
     # Schedule J expense line item derivations
-    "schedule_j_rent_or_mortgage": lambda s: _fmt(_get_expense_field(s, "rent_or_mortgage")),
-    "schedule_j_utilities": lambda s: _fmt(_get_expense_field(s, "utilities")),
-    "schedule_j_home_maintenance": lambda s: _fmt(_get_expense_field(s, "home_maintenance")),
-    "schedule_j_food_and_groceries": lambda s: _fmt(_get_expense_field(s, "food_and_groceries")),
-    "schedule_j_childcare": lambda s: _fmt(_get_expense_field(s, "childcare")),
-    "schedule_j_clothing": lambda s: _fmt(_get_expense_field(s, "clothing")),
-    "schedule_j_medical_expenses": lambda s: _fmt(_get_expense_field(s, "medical_expenses")),
-    "schedule_j_vehicle_maintenance": lambda s: _fmt(_get_expense_field(s, "vehicle_maintenance")),
-    "schedule_j_vehicle_payment": lambda s: _fmt(_get_expense_field(s, "vehicle_payment")),
-    "schedule_j_vehicle_insurance": lambda s: _fmt(_get_expense_field(s, "vehicle_insurance")),
-    "schedule_j_insurance_not_deducted": lambda s: _fmt(
-        _get_expense_field(s, "insurance_not_deducted")
-    ),
-    "schedule_j_other_expenses": lambda s: _fmt(
-        _get_expense_field(s, "other_expenses") + _get_expense_field(s, "child_support_paid")
+    "schedule_j_rent_or_mortgage": lambda s: _expense_line(s, "rent_or_mortgage"),
+    "schedule_j_utilities": lambda s: _expense_line(s, "utilities"),
+    "schedule_j_utilities_label": lambda s: _expense_label(s, "utilities", "Utilities (combined)"),
+    "schedule_j_home_maintenance": lambda s: _expense_line(s, "home_maintenance"),
+    "schedule_j_food_and_groceries": lambda s: _expense_line(s, "food_and_groceries"),
+    "schedule_j_childcare": lambda s: _expense_line(s, "childcare"),
+    "schedule_j_clothing": lambda s: _expense_line(s, "clothing"),
+    "schedule_j_medical_expenses": lambda s: _expense_line(s, "medical_expenses"),
+    "schedule_j_vehicle_maintenance": lambda s: _expense_line(s, "vehicle_maintenance"),
+    "schedule_j_vehicle_payment": lambda s: _expense_line(s, "vehicle_payment"),
+    "schedule_j_vehicle_insurance": lambda s: _expense_line(s, "vehicle_insurance"),
+    "schedule_j_insurance_not_deducted": lambda s: _expense_line(s, "insurance_not_deducted"),
+    "schedule_j_insurance_label": lambda s: _expense_label(
+        s, "insurance_not_deducted", "Insurance (combined)"
     ),
+    "schedule_j_support_paid": lambda s: _expense_line(s, "child_support_paid"),
+    "schedule_j_other_expenses": lambda s: _expense_line(s, "other_expenses"),
     "schedule_j_total_expenses": _schedule_j_total_expenses,
     # Line 23a is Schedule I line 12: one figure on both forms
     "schedule_j_total_income": _schedule_i_income_total,
diff --git a/data/forms/schemas/schedule_j.json b/data/forms/schemas/schedule_j.json
index c4e074a..7b68044 100644
--- a/data/forms/schemas/schedule_j.json
+++ b/data/forms/schemas/schedule_j.json
@@ -38,10 +38,10 @@
       "legal_review": false
     },
     {
-      "pdf_field": "10",
+      "pdf_field": "4",
       "type": "text",
       "source": "derived",
-      "page": 2,
+      "page": 1,
       "label": "",
       "required": false,
       "conditional_on": null,
@@ -55,7 +55,24 @@
       "legal_review": false
     },
     {
-      "pdf_field": "12",
+      "pdf_field": "4c",
+      "type": "text",
+      "source": "derived",
+      "page": 1,
+      "label": "",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "schedule_j_home_maintenance",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "6d",
       "type": "text",
       "source": "derived",
       "page": 2,
@@ -72,7 +89,7 @@
       "legal_review": false
     },
     {
-      "pdf_field": "14",
+      "pdf_field": "Other 6d",
       "type": "text",
       "source": "derived",
       "page": 2,
@@ -80,7 +97,7 @@
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_j_home_maintenance",
+      "rule": "schedule_j_utilities_label",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -89,7 +106,7 @@
       "legal_review": false
     },
     {
-      "pdf_field": "15a",
+      "pdf_field": "7",
       "type": "text",
       "source": "derived",
       "page": 2,
@@ -106,7 +123,7 @@
       "legal_review": false
     },
     {
-      "pdf_field": "15b",
+      "pdf_field": "8",
       "type": "text",
       "source": "derived",
       "page": 2,
@@ -123,7 +140,7 @@
       "legal_review": false
     },
     {
-      "pdf_field": "15c",
+      "pdf_field": "9",
       "type": "text",
       "source": "derived",
       "page": 2,
@@ -140,7 +157,7 @@
       "legal_review": false
     },
     {
-      "pdf_field": "16",
+      "pdf_field": "11",
       "type": "text",
       "source": "derived",
       "page": 2,
@@ -157,7 +174,7 @@
       "legal_review": false
     },
     {
-      "pdf_field": "17a",
+      "pdf_field": "12",
       "type": "text",
       "source": "derived",
       "page": 2,
@@ -174,7 +191,7 @@
       "legal_review": false
     },
     {
-      "pdf_field": "17b",
+      "pdf_field": "15c",
       "type": "text",
       "source": "derived",
       "page": 2,
@@ -182,7 +199,7 @@
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_j_vehicle_payment",
+      "rule": "schedule_j_vehicle_insurance",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -191,7 +208,7 @@
       "legal_review": false
     },
     {
-      "pdf_field": "17c",
+      "pdf_field": "15d",
       "type": "text",
       "source": "derived",
       "page": 2,
@@ -199,7 +216,7 @@
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_j_vehicle_insurance",
+      "rule": "schedule_j_insurance_not_deducted",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -208,7 +225,7 @@
       "legal_review": false
     },
     {
-      "pdf_field": "20a",
+      "pdf_field": "Other 15d",
       "type": "text",
       "source": "derived",
       "page": 2,
@@ -216,7 +233,41 @@
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_j_insurance_not_deducted",
+      "rule": "schedule_j_insurance_label",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "17a",
+      "type": "text",
+      "source": "derived",
+      "page": 2,
+      "label": "",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "schedule_j_vehicle_payment",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "18",
+      "type": "text",
+      "source": "derived",
+      "page": 2,
+      "label": "",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "schedule_j_support_paid",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
PATCH
```

The rules read each amount through `_expense_line`, and the three new rules give line 18 and the two Specify boxes their text. The schema moves the 11 bound expense objects to the boxes Appendix A.8 names, adds `Other 6d`, `Other 15d` and `18`, and leaves the vacated lines unbound.

- [ ] **Step 4: Record the addendum rows, the new count and the cleared entries**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index 2711666..1574939 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -159,94 +159,6 @@
     "class": "wrong_box",
     "ticket": "DIG-69"
   },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "10",
-    "tier": "2",
-    "case": "derived:schedule_j_rent_or_mortgage",
-    "class": "wrong_box",
-    "ticket": "DIG-52"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "12",
-    "tier": "2",
-    "case": "derived:schedule_j_utilities",
-    "class": "wrong_box",
-    "ticket": "DIG-52"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "14",
-    "tier": "2",
-    "case": "derived:schedule_j_home_maintenance",
-    "class": "wrong_box",
-    "ticket": "DIG-52"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "15a",
-    "tier": "2",
-    "case": "derived:schedule_j_food_and_groceries",
-    "class": "wrong_box",
-    "ticket": "DIG-52"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "15b",
-    "tier": "2",
-    "case": "derived:schedule_j_childcare",
-    "class": "wrong_box",
-    "ticket": "DIG-52"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "15c",
-    "tier": "2",
-    "case": "derived:schedule_j_clothing",
-    "class": "wrong_box",
-    "ticket": "DIG-52"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "16",
-    "tier": "2",
-    "case": "derived:schedule_j_medical_expenses",
-    "class": "wrong_box",
-    "ticket": "DIG-52"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "17a",
-    "tier": "2",
-    "case": "derived:schedule_j_vehicle_maintenance",
-    "class": "wrong_box",
-    "ticket": "DIG-52"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "17b",
-    "tier": "2",
-    "case": "derived:schedule_j_vehicle_payment",
-    "class": "wrong_box",
-    "ticket": "DIG-52"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "17c",
-    "tier": "2",
-    "case": "derived:schedule_j_vehicle_insurance",
-    "class": "wrong_box",
-    "ticket": "DIG-52"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "20a",
-    "tier": "2",
-    "case": "derived:schedule_j_insurance_not_deducted",
-    "class": "wrong_box",
-    "ticket": "DIG-52"
-  },
   {
     "form_type": "schedule_j",
     "pdf_field": "22c",
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index 52bffc2..e167bbe 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 414
+ASSERTED_CASES = 417


 def _audit_dir():
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index ac7280c..681dfdf 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -418,5 +418,55 @@
     "status": "confirmed",
     "correct_target": "Amount 12",
     "evidence": "Field index: Amount 12 p2 line 12, column 'Combined monthly income', 'Add the amount in the last column of line 10 to the amount in line 11 (Combined monthly income)' (adjudicated). Line 11 (others' regular contributions) is never asked and counts as zero: step 2 spec §6.1 (totals that count an unasked line as zero; the section 6c decision covers Schedule I line 12) and C1 (the Schedule I income total, Social Security included), §5.5 and §6.2 (schedule_i_income_total). Appendix B R4: the box keeps a binding. The audit's verified row on this box judged the old cmi binding, which leaves Social Security out."
+  },
+  {
+    "schema": "schedule_j",
+    "pdf_field": "6d",
+    "producer": "derived:schedule_j_utilities",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "6d",
+    "evidence": "Field index: 6d p2 line 6d, column 'Your expenses', 'Utilities: Other. Specify: (amount)' (adjudicated). Owner Q4 (step 2 spec §3, DIG-52): utilities go on 6d with 'Utilities (combined)', insurance not deducted from pay on 15d with 'Insurance (combined)'; each label prints only above $0. The Expenses step stores one utilities figure, which 6a-6c can't take without a split. Step 2 spec Appendix A.8 and Appendix B chain a (12 -> 6d); §6.1 and §6.2 (blank at $0, 6c option A). The audit's verified row on 12 names 6a for this rule; Q4 overrides it."
+  },
+  {
+    "schema": "schedule_j",
+    "pdf_field": "Other 6d",
+    "producer": "derived:schedule_j_utilities_label",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Other 6d",
+    "evidence": "Field index: Other 6d p2 line 6d, tooltip 'Specify', 'Utilities: Other. Specify:' (adjudicated): the text naming 6d's amount. Owner Q4 (step 2 spec §3, DIG-52): utilities go on 6d with 'Utilities (combined)', insurance not deducted from pay on 15d with 'Insurance (combined)'; each label prints only above $0. Step 2 spec Appendix A.8, §6.2 (schedule_j_utilities_label). The audit has no row for this box."
+  },
+  {
+    "schema": "schedule_j",
+    "pdf_field": "15d",
+    "producer": "derived:schedule_j_insurance_not_deducted",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "15d",
+    "evidence": "Field index: 15d p2 line 15d, column 'Your expenses', 'Other insurance. Specify: (amount)' (adjudicated). Owner Q4 (step 2 spec §3, DIG-52): utilities go on 6d with 'Utilities (combined)', insurance not deducted from pay on 15d with 'Insurance (combined)'; each label prints only above $0. The Expenses step stores one figure for health, life or disability insurance not deducted from pay, which 15a and 15b can't take without a split. Step 2 spec Appendix A.8 (20a -> 15d); §6.1 and §6.2 (blank at $0, 6c option A). The audit's verified row on 20a names 15b for this rule; Q4 overrides it."
+  },
+  {
+    "schema": "schedule_j",
+    "pdf_field": "Other 15d",
+    "producer": "derived:schedule_j_insurance_label",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Other 15d",
+    "evidence": "Field index: Other 15d p2 line 15d, tooltip 'Specify', 'Other insurance. Specify:' (adjudicated): the text naming 15d's amount. Owner Q4 (step 2 spec §3, DIG-52): utilities go on 6d with 'Utilities (combined)', insurance not deducted from pay on 15d with 'Insurance (combined)'; each label prints only above $0. Step 2 spec Appendix A.8, §6.2 (schedule_j_insurance_label). The audit has no row for this box."
+  },
+  {
+    "schema": "schedule_j",
+    "pdf_field": "18",
+    "producer": "derived:schedule_j_support_paid",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "18",
+    "evidence": "Field index: 18 p2 line 18, column 'Your expenses', 'Your payments of alimony, maintenance, and support that you did not report as deducted from your pay on line 5, Schedule I' (adjudicated). ExpenseInfo.child_support_paid is court-ordered support paid. The audit's verified row on 21 (wrong_value) says court-ordered support paid belongs on line 18, not in line 21's other expenses. Step 2 spec Appendix A.8, §6.1 and §6.2 (schedule_j_support_paid, blank at $0, 6c option A)."
   }
 ]
PATCH
```

Each addendum row cites the box's field-index label and owner Q4 where Q4 decided it. `ASSERTED_CASES` becomes 417. The list loses exactly the 11 entries the moves orphan, deleted by hand (R3).

- [ ] **Step 5: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line apps/forms/tests/test_schedule_j_schema.py -q -p no:cacheprovider 2>&1 | tail -15
```

Expected: `6 passed`.

- [ ] **Step 6: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2b.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2070 passed, 1 skipped, 36 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  358 passed (358)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

This task changes no page or flow, so the journeys don't run here.

- [ ] **Step 7: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_schedule_j_schema.py \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_oracle_tier2.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/schedule_j.json
git commit -F - <<'MSG'
fix(forms): Schedule J prints each expense on the line that asks for it, and only above $0

Schedule J's expense lines follow the step 2 spec (Appendix A.8,
Appendix B, owner Q4):
- chain a: the car payment moves 17b -> 17a, transportation (vehicle
  maintenance) 17a -> 12, and utilities 12 -> 6d with "Utilities
  (combined)" in 6d's Specify box (new rule schedule_j_utilities_label);
- chain b: vehicle insurance moves 17c -> 15c, and clothing 15c -> 9;
- independent moves: rent 10 -> 4 and home upkeep 14 -> 4c (both on page
  1, not page 2 as the old bindings said), food 15a -> 7, childcare
  15b -> 8, medical 16 -> 11, and insurance not deducted from pay
  20a -> 15d with "Insurance (combined)" in 15d's Specify box (new rule
  schedule_j_insurance_label);
- line 18 prints support paid (new rule schedule_j_support_paid), and
  line 21 prints other expenses only. Until now line 21 added support
  paid to other expenses.

Line 10 (personal care), 14 (charity), 15a (life insurance), 15b (health
insurance), 16 (taxes), 17b (a second car), 17c (other installments) and
20a (other property's mortgage) now print nothing.

Every expense line prints only above $0 (spec §6.1, 6c option A): an
expense left empty is stored as $0, so $0 can't be told from "left
blank". The same holds for a negative amount, and for a session that
never saved the Expenses step, which printed 0.00 on every line before
(B2). The two labels print only when their amount does. Totals are
unchanged: 22a still adds all 13 amounts.

The 12 expense rule bodies call a new _expense_line helper.
_get_expense_field, whose bare except read any error as $0, lost its
last caller and is deleted. No rule lost its last binding.

Form 122A-2 binds five of these rules to seven boxes: Quest6, 8, 9, 12,
13D, 14 and 15. At $0 those boxes now print blank instead of 0.00, until
T14 removes them. No tier 3 row covers 122A-2. test_api_readback still finds an
amount above 0 on Priya's 122A-2, from her rent.

Oracle:
- step2_verification.json gains the five ADD rows: 6d, its Specify box,
  15d, its Specify box, and 18 (42 -> 47). The nine moved boxes (4, 4c,
  7, 8, 9, 11, 12, 15c, 17a) are asserted by the moved-here join.
- Tier 3 is unchanged. Appendix D's row "18 is blank" already ran for all
  five personas, and it still passes now that 18 is bound, because every
  seed's support paid is $0.

Clears 11 known-defect entries (46 -> 35), all tier 2 orphans: 10, 12,
14, 15a, 15b, 15c, 16, 17a, 17b, 17c and 20a. Before the deletion,
exactly those 11 entries and the coverage tripwire failed.

ASSERTED_CASES 414 -> 417 (+3), measured by diffing the collected IDs:
- 11 tier 2 cases left with their bindings (the 11 xfails above);
- 14 new tier 2 cases, all passing: 9 moved-here joins and the 5
  addendum rows.

New tests (test_schedule_j_schema.py):
- test_each_expense_prints_on_the_line_that_asks_for_it: each of the 13
  amounts is a distinct power of two, printed on its own line, with
  nothing on the vacated lines
- test_expense_line_prints_only_above_zero: $0.01 prints; $0, -$0.01 and
  an unsaved Expenses step print nothing, labels included
- test_support_paid_prints_on_line_18_and_never_on_line_21

Refs DIG-52
MSG
git status --short
```

### Task 13: Print Schedule J's totals on 22c, 23b and 23c, and tick "No" on line 1 for an individual filing

_Built and verified as commit `5a30a53` on `plan/forms-step2b`._

**Files:**

- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `backend/apps/forms/tests/test_schedule_j_schema.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/schedule_j.json`

**Interfaces:**

- Consumes:
  - Task 11's `_schedule_i_income_total`, which `DERIVATIONS` binds as both `schedule_i_income_total` (Schedule I line 12) and `schedule_j_total_income` (Schedule J 23a). It returns all ten income sources summed, or `""` when no source was given.
  - `_schedule_j_total_expenses` (rule `schedule_j_total_expenses`, already on 22a). It returns `_fmt` of `ExpenseInfo.calculate_total_monthly_expenses()`, and `"0.00"` through a bare except when there is no `ExpenseInfo`.
  - `_fmt` in `derivations.py`, and `DebtorInfo.filing_type` (`"individual"` by default, or `"joint"`).
  - Task 12's `test_schedule_j_schema.py`: the `session` fixture, and `EXPENSES` (the 13 Expenses amounts as the powers of two from 1.00 to 4096.00).
  - Tier 3's existing Schedule J rows for 22c, 23b and 23c, all five personas, listed in `known_defects.json` as strict xfails (DIG-61).
- Produces:
  - Rules in `DERIVATIONS`, after `schedule_j_total_income`:
    - `schedule_j_monthly_net_income` (`_schedule_j_monthly_net_income`) returns 23a − 23b, `_fmt(Decimal(_schedule_i_income_total(s)) - Decimal(_schedule_j_total_expenses(s)))`. It is `""` while `_schedule_i_income_total` is `""`, and a negative result keeps its minus sign.
    - `schedule_j_joint_case` (`_schedule_j_joint_case`) returns `"no"` when the session has a `DebtorInfo` with `filing_type == "individual"`, and `""` otherwise.
  - `data/forms/schemas/schedule_j.json` goes from 19 objects to 23. All four new objects are `derived` with label `""`:
    - `check1` (page 1, after `Debtor 1`): `"type": "checkbox"`, `"choices": {"no": "/no"}`, rule `schedule_j_joint_case`;
    - `22c` (page 3, after `22a`) and `23b` (page 3, after `23a`): rule `schedule_j_total_expenses`;
    - `23c` (page 3, after `23b`): rule `schedule_j_monthly_net_income`.
  - `step2_verification.json` goes from 47 rows to 51. The new rows are `schedule_j` `check1` `derived:schedule_j_joint_case`, `22c` and `23b` `derived:schedule_j_total_expenses`, and `23c` `derived:schedule_j_monthly_net_income`.
  - `ASSERTED_CASES = 421`. `known_defects.json` drops from 35 entries to 20.
  - In `test_schedule_j_schema.py`:
    - the constant `EXPENSE_TOTAL = "8191.00"`;
    - `test_monthly_expenses_print_on_22c_and_again_on_23b`;
    - `test_monthly_net_income_is_income_less_expenses`;
    - `test_a_month_that_runs_short_prints_net_income_below_zero`;
    - `test_net_income_stays_blank_until_income_is_given[True|False]`;
    - `test_only_an_individual_filing_answers_no_to_is_this_a_joint_case[individual-/no|joint-None|None-None]`.

**Decisions already made in this task:**

- 23c is 23a − 23b, computed by calling 23a's rule (`_schedule_i_income_total`) and 23b's rule (`_schedule_j_total_expenses`), so 23c can't drift from the two boxes it subtracts. It never calls `cmi`. 23a has counted all ten sources, Social Security included, since Task 11 (C1, R4), so a CMI figure would be wrong here.
- Ruling T0-f: 23c is blank while 23a is blank. A month whose expenses pass its income prints with a minus sign (`-150.00`), as the form's own arithmetic does. A blank 23a is never read as 0. A filer who gave no income can't reach a packet anyway, because `views._prepare` refuses `IncomeNotSplit` first.
- 22b holds Debtor 2's expenses from Official Form 106J-2, which DigniFi never asks. So 22c equals 22a, and 23b copies 22c. Both bind `schedule_j_total_expenses`, the rule 22a already uses (§6.1: "Totals still print: Schedule J 22a and 22c").
- 22c and 23b inherit `_schedule_j_total_expenses`'s bare except. With no Expenses row it prints 0.00, and 23c then prints the income less 0.00. This is pre-existing (B9), as on 22a and 103B line 6, and no packet reaches it: `complete` refuses a session with no Expenses row, and every generate and download path runs `_check_finished`. Leave it.
- Line 1 binds `check1`, not `Check 1`, which is the amended/supplemental box. Its choices are `{"no": "/no"}`: the index's "No. Go to line 2." widget has on_state `no`. `_schedule_j_joint_case` returns only `"no"` or `""`, so it can't raise `UnmappedChoice`.
- A joint filing leaves line 1 blank rather than ticking "No": a joint filer still gets a single filer's packet (DIG-177). Nothing ever ticks "Yes". A session whose Debtor step was never saved is blank too.
- The four new objects carry label `""`, like every line object already in `schedule_j.json`.
- No owner answer (Q4–Q12) decides these four boxes, so no addendum row cites one.
- No existing rule body changes, and no rule loses its last binding, so nothing is deleted.
- `ASSERTED_CASES` goes from 417 to 421 (+4), measured by diffing the collected IDs: the four addendum rows, all passing. No tier 2 case is lost. Tier 1 gains four passing cases (22c, 23b, 23c, and `check1`'s `no`), which are not pinned.
- The 15 entries deleted are all tier 3 strict XPASSes (`wrong_value`, DIG-61): 22c, 23b and 23c for maria, james, priya, deshawn and sarah. Tier 3's rows already existed, so tier 3 gains no case.

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_schedule_j_schema.py b/backend/apps/forms/tests/test_schedule_j_schema.py
index b2a6bf2..ef0f318 100644
--- a/backend/apps/forms/tests/test_schedule_j_schema.py
+++ b/backend/apps/forms/tests/test_schedule_j_schema.py
@@ -1,5 +1,6 @@
 """Schedule J: each expense prints on the line that asks for it, and only above $0."""

+from datetime import date
 from decimal import Decimal

 import pytest
@@ -8,7 +9,7 @@ from django.contrib.auth import get_user_model
 from apps.districts.models import District
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
-from apps.intake.models import ExpenseInfo, IntakeSession
+from apps.intake.models import DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession

 User = get_user_model()

@@ -49,6 +50,8 @@ LINE_BY_EXPENSE = {
 }
 # Lines no expense belongs on, which the old bindings filled.
 VACATED = {"10", "14", "15a", "15b", "16", "17b", "17c", "20a"}
+# The 13 amounts above, added: 1 + 2 + 4 + ... + 4096.
+EXPENSE_TOTAL = "8191.00"


 @pytest.fixture
@@ -102,3 +105,95 @@ def test_support_paid_prints_on_line_18_and_never_on_line_21(session):
     printed = resolve(load_schema("schedule_j"), session)

     assert (printed.get("18"), printed.get("21")) == ("450.00", None)
+
+
+def test_monthly_expenses_print_on_22c_and_again_on_23b(session):
+    # 22c adds 22a and 22b (Debtor 2's separate household, never asked); 23b copies 22c.
+    ExpenseInfo.objects.create(session=session, **EXPENSES)
+
+    printed = resolve(load_schema("schedule_j"), session)
+
+    totals = ("22a", "22c", "23b")
+    assert {box: printed.get(box) for box in totals} == dict.fromkeys(totals, EXPENSE_TOTAL)
+
+
+def test_monthly_net_income_is_income_less_expenses(session):
+    # 23a copies Schedule I line 12, Social Security included (C1); 23c is 23a - 23b.
+    IncomeInfo.objects.create(
+        session=session,
+        marital_status="single",
+        monthly_gross_wages=Decimal("9000.00"),
+        monthly_social_security=Decimal("200.00"),
+    )
+    ExpenseInfo.objects.create(session=session, **EXPENSES)
+
+    printed = resolve(load_schema("schedule_j"), session)
+
+    assert {box: printed.get(box) for box in ("23a", "23b", "23c")} == {
+        "23a": "9200.00",
+        "23b": EXPENSE_TOTAL,
+        "23c": "1009.00",
+    }
+
+
+def test_a_month_that_runs_short_prints_net_income_below_zero(session):
+    # The form's own arithmetic: expenses above income leave a negative net income.
+    IncomeInfo.objects.create(
+        session=session, marital_status="single", monthly_gross_wages=Decimal("100.00")
+    )
+    ExpenseInfo.objects.create(session=session, rent_or_mortgage=Decimal("250.00"))
+
+    printed = resolve(load_schema("schedule_j"), session)
+
+    assert printed.get("23c") == "-150.00"
+
+
+@pytest.mark.parametrize("income_saved", [True, False])
+def test_net_income_stays_blank_until_income_is_given(session, income_saved):
+    # With no income given, 23a is blank and 23c has nothing to subtract from, so it is
+    # blank too, never the expenses as a loss. The expense total still prints.
+    if income_saved:  # the Income step was saved with every source left empty
+        IncomeInfo.objects.create(session=session, marital_status="single")
+    ExpenseInfo.objects.create(session=session, **EXPENSES)
+
+    printed = resolve(load_schema("schedule_j"), session)
+
+    assert {box: printed.get(box) for box in ("22c", "23a", "23b", "23c")} == {
+        "22c": EXPENSE_TOTAL,
+        "23a": None,
+        "23b": EXPENSE_TOTAL,
+        "23c": None,
+    }
+
+
+@pytest.mark.parametrize(
+    "filing_type,ticks",
+    [
+        ("individual", "/no"),
+        ("joint", None),
+        (None, None),  # the Debtor step was never saved
+    ],
+)
+def test_only_an_individual_filing_answers_no_to_is_this_a_joint_case(session, filing_type, ticks):
+    # A joint filer still gets a single filer's packet (DIG-177), so line 1 stays blank for
+    # them rather than say "No", and nothing ever ticks "Yes".
+    if filing_type is not None:
+        DebtorInfo.objects.create(
+            session=session,
+            first_name="Jane",
+            middle_name="",
+            last_name="Doe",
+            ssn="123-45-6789",
+            date_of_birth=date(1990, 1, 15),
+            phone="312-555-0100",
+            email="jane@example.com",
+            street_address="123 Main St",
+            city="Chicago",
+            state="IL",
+            zip_code="60601",
+            filing_type=filing_type,
+        )
+
+    printed = resolve(load_schema("schedule_j"), session)
+
+    assert printed.get("check1") == ticks
PATCH
```

The tests add up the 13 power-of-two amounts to `EXPENSE_TOTAL`, 8191.00, so a total that misses or doubles an amount prints a different figure. The net-income test gives wages of 9000 and Social Security of 200: 23a is 9200.00, and 23c is 1009.00, where a CMI-based 23c would print 809.00. The joint-case test saves a Debtor step for an individual filing, for a joint one, and not at all.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_schedule_j_schema.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `6 failed, 8 passed`. 22c, 23b, 23c and check1 are unbound, so each test that expects them to print finds nothing: the 22c and 23b total, the net income, the short month, both blank-until-income cases (their 22c and 23b anchors are missing) and the individual filing's /no. The 8 passes are Task 12's six tests, plus the joint and no-Debtor cases of the joint-case test, which pass vacuously because an unbound box also prints nothing. Once check1 is bound they guard the rule.

- [ ] **Step 3: Add the net income and joint-case rules**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index 34832bb..f1ace2e 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -456,6 +456,30 @@ def _schedule_j_total_expenses(session: IntakeSession) -> str:
         return "0.00"


+def _schedule_j_monthly_net_income(session: IntakeSession) -> str:
+    """
+    Line 23c, 23a - 23b: blank while 23a is, and below zero when expenses pass income.
+
+    23a is Schedule I line 12 and 23b is line 22c, so 23c is computed from those rules.
+    """
+    income = _schedule_i_income_total(session)
+    if income == "":
+        return ""
+    return _fmt(Decimal(income) - Decimal(_schedule_j_total_expenses(session)))
+
+
+def _schedule_j_joint_case(session: IntakeSession) -> str:
+    """
+    Line 1: "no" for an individual filing, blank for a joint one (DIG-177).
+
+    A joint filer still gets a single filer's packet, so line 1 says nothing for them.
+    """
+    debtor_info = getattr(session, "debtor_info", None)
+    if debtor_info is not None and debtor_info.filing_type == "individual":
+        return "no"
+    return ""
+
+
 def _means_test_disposable_income(session: IntakeSession) -> str:
     try:
         mt = session.means_test
@@ -580,6 +604,8 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "schedule_j_total_expenses": _schedule_j_total_expenses,
     # Line 23a is Schedule I line 12: one figure on both forms
     "schedule_j_total_income": _schedule_i_income_total,
+    "schedule_j_monthly_net_income": _schedule_j_monthly_net_income,
+    "schedule_j_joint_case": _schedule_j_joint_case,
     # Form 122A-2 means test expense deduction derivations
     "means_test_disposable_income": _means_test_disposable_income,
     "means_test_total_deductions": _means_test_total_deductions,
PATCH
```

`_schedule_j_monthly_net_income` is §6.2's "23a − 23b", and `_schedule_j_joint_case` is its "`no` for an individual filing, blank for Joint" (DIG-177). Both go in `DERIVATIONS` beside `schedule_j_total_income`.

- [ ] **Step 4: Bind 22c, 23b, 23c and line 1, with their addendum rows**

```bash
git apply <<'PATCH'
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index 681dfdf..c2eb9e9 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -468,5 +468,45 @@
     "status": "confirmed",
     "correct_target": "18",
     "evidence": "Field index: 18 p2 line 18, column 'Your expenses', 'Your payments of alimony, maintenance, and support that you did not report as deducted from your pay on line 5, Schedule I' (adjudicated). ExpenseInfo.child_support_paid is court-ordered support paid. The audit's verified row on 21 (wrong_value) says court-ordered support paid belongs on line 18, not in line 21's other expenses. Step 2 spec Appendix A.8, §6.1 and §6.2 (schedule_j_support_paid, blank at $0, 6c option A)."
+  },
+  {
+    "schema": "schedule_j",
+    "pdf_field": "check1",
+    "producer": "derived:schedule_j_joint_case",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check1",
+    "evidence": "Field index: check1 p1 line 1, 'Is this a joint case?', option 'No. Go to line 2.' (on_state 'no', export state /no; adjudicated); its other widget is 'Yes. Does Debtor 2 live in a separate household?' (on_state 'yes'). Not 'Check 1', the amended/supplemental box. DebtorInfo.filing_type 'individual' is a single filer's case. Step 2 spec Appendix A.8, §6.2 (schedule_j_joint_case: 'no' for an individual filing, blank for Joint) and §10: a joint filer still gets a single filer's packet, so line 1 stays blank for them (DIG-177). The audit lists check1 as unbound (schedule_j.unbound.json)."
+  },
+  {
+    "schema": "schedule_j",
+    "pdf_field": "22c",
+    "producer": "derived:schedule_j_total_expenses",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "22c",
+    "evidence": "Field index: 22c p3 line 22c, column 'Your expenses', 'Add line 22a and 22b. The result is your monthly expenses.' (adjudicated). 22b copies Debtor 2's expenses from Official Form 106J-2, which is never asked, so 22c is 22a: all 13 Expenses step amounts. Step 2 spec Appendix A.8, §6.1 (totals still print: Schedule J 22a and 22c) and Appendix C.3 (DIG-61). The audit's one row with this key is on 22a and targets 22a, so the moved-here join can't assert 22c; the audit lists 22c as unbound (schedule_j.unbound.json, DIG-61)."
+  },
+  {
+    "schema": "schedule_j",
+    "pdf_field": "23b",
+    "producer": "derived:schedule_j_total_expenses",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "23b",
+    "evidence": "Field index: 23b p3 line 23b, column 'Your expenses', 'Copy your monthly expenses from line 22c above.' (adjudicated): the same figure as 22c. Step 2 spec Appendix A.8 and Appendix C.3 (DIG-61). The audit's one row with this key is on 22a and targets 22a; the audit lists 23b as unbound (schedule_j.unbound.json, DIG-61)."
+  },
+  {
+    "schema": "schedule_j",
+    "pdf_field": "23c",
+    "producer": "derived:schedule_j_monthly_net_income",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "23c",
+    "evidence": "Field index: 23c p3 line 23c, column 'Your expenses', 'Subtract your monthly expenses from your monthly income. The result is your monthly net income.' (adjudicated): 23a (Schedule I line 12, schedule_i_income_total) minus 23b (line 22c). Step 2 spec Appendix A.8, §6.2 (schedule_j_monthly_net_income, 23a - 23b), Appendix B R4 (after 23a's new body) and Appendix C.3 (DIG-61); ruling T0-f: blank while 23a is blank, a negative result prints with a minus sign. The audit lists 23c as unbound (schedule_j.unbound.json, DIG-61)."
   }
 ]
diff --git a/data/forms/schemas/schedule_j.json b/data/forms/schemas/schedule_j.json
index 7b68044..543ebb4 100644
--- a/data/forms/schemas/schedule_j.json
+++ b/data/forms/schemas/schedule_j.json
@@ -37,6 +37,26 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "check1",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "no": "/no"
+      },
+      "page": 1,
+      "label": "",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "schedule_j_joint_case",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "4",
       "type": "text",
@@ -309,6 +329,23 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "22c",
+      "type": "text",
+      "source": "derived",
+      "page": 3,
+      "label": "",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "schedule_j_total_expenses",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "23a",
       "type": "text",
@@ -325,6 +362,40 @@
       "repeat_capacity": null,
       "row": null,
       "legal_review": false
+    },
+    {
+      "pdf_field": "23b",
+      "type": "text",
+      "source": "derived",
+      "page": 3,
+      "label": "",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "schedule_j_total_expenses",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "23c",
+      "type": "text",
+      "source": "derived",
+      "page": 3,
+      "label": "",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "schedule_j_monthly_net_income",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
     }
   ]
 }
PATCH
```

All four boxes are ADD rows in Appendix A.8, so each gets its `step2_verification.json` row in this commit (§7.4). Each row cites the box's field-index label. The audit's one row with 22c's and 23b's key sits on 22a and targets 22a, so the moved-here join can't assert them.

- [ ] **Step 5: Run the oracle against the old list and watch it fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `16 failed, 1239 passed`. The bound boxes now print what tier 3 expects, so the 15 Schedule J cases the list still marks as strict xfails (22c, 23b and 23c for maria, james, priya, deshawn and sarah) fail as XPASS(strict). The 16th is the tier 2 coverage tripwire, test_tier2_coverage_changes_only_on_purpose, which collects 421 asserted cases against the pinned 417. Nothing else may fail. Any other failure, or an XPASS you can't name, means the tree has drifted from the plan.

- [ ] **Step 6: Delete the 15 entries and pin the new count**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index 1574939..6ef005e 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -158,125 +158,5 @@
     "case": "derived:total_secured_claims",
     "class": "wrong_box",
     "ticket": "DIG-69"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "22c",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "22c",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "22c",
-    "tier": "3",
-    "case": "maria",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "22c",
-    "tier": "3",
-    "case": "priya",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "22c",
-    "tier": "3",
-    "case": "sarah",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "23b",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "23b",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "23b",
-    "tier": "3",
-    "case": "maria",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "23b",
-    "tier": "3",
-    "case": "priya",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "23b",
-    "tier": "3",
-    "case": "sarah",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "23c",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "23c",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "23c",
-    "tier": "3",
-    "case": "maria",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "23c",
-    "tier": "3",
-    "case": "priya",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
-  },
-  {
-    "form_type": "schedule_j",
-    "pdf_field": "23c",
-    "tier": "3",
-    "case": "sarah",
-    "class": "wrong_value",
-    "ticket": "DIG-61"
   }
 ]
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index e167bbe..aa2d684 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 417
+ASSERTED_CASES = 421


 def _audit_dir():
PATCH
```

The patch deletes exactly the 15 entries (120 lines) and keeps the order of the 20 that remain. Never produce this change by re-running the recorder (R3).

- [ ] **Step 7: Run the tests and the oracle again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_schedule_j_schema.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `14 passed`.

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `1255 passed, 1 skipped, 20 xfailed`. That is one xfail for each of the 20 entries left, and the skip is tier 1's empty checkbox parameter set (Ruling C-6).

- [ ] **Step 8: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2b.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2101 passed, 1 skipped, 21 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  358 passed (358)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

No journeys this task: it changes no page or flow, only what Schedule J prints.

- [ ] **Step 9: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_oracle_tier2.py \
  backend/apps/forms/tests/test_schedule_j_schema.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/schedule_j.json
git commit -F - <<'MSG'
fix(forms): Schedule J prints its totals on 22c, 23b and 23c, and ticks "No" on line 1 for an individual filing

Schedule J's totals and line 1 follow the step 2 spec (Appendix A.8,
§6.2):
- 22c and 23b print the monthly expense total (schedule_j_total_expenses,
  as 22a already does). 22b, Debtor 2's separate household, is never
  asked, so 22c is 22a, and 23b copies 22c.
- 23c prints the monthly net income, 23a - 23b (new rule
  schedule_j_monthly_net_income). 23a is Schedule I line 12, all ten
  sources (C1, since T11), so 23c clears against the right income and
  not against CMI (R4). 23c is blank while 23a is blank, and a month
  whose expenses pass its income prints with a minus sign (ruling T0-f).
- Line 1, "Is this a joint case?", ticks "No. Go to line 2." for an
  individual filing (new rule schedule_j_joint_case, choices
  {"no": "/no"}). It stays blank for a joint filing, which still gets a
  single filer's packet (DIG-177), and when the Debtor step was never
  saved. The rule returns only "no" or "", so it can't raise
  UnmappedChoice.

No body of an existing rule changes. 22c and 23b inherit
_schedule_j_total_expenses's bare except, which prints 0.00 for a
session that never saved the Expenses step (pre-existing, as on 22a
and 103B line 6).

Oracle:
- step2_verification.json gains the four ADD rows: check1, 22c, 23b and
  23c (47 -> 51). The audit's one row with 22c's and 23b's key is on 22a
  and targets 22a, so the moved-here join can't assert them.
- Tier 3 is unchanged: its 22c, 23b and 23c rows were already there for
  all five personas, as strict xfails.

Clears 15 known-defect entries (35 -> 20), all tier 3 strict XPASS
(DIG-61): 22c, 23b and 23c for maria, james, priya, deshawn and sarah.
Before the deletion, exactly those 15 and the coverage tripwire failed.

ASSERTED_CASES 417 -> 421 (+4), measured by diffing the collected IDs:
the four addendum rows, all passing. No tier 2 case left. Tier 1 gains
four passing cases (22c, 23b, 23c, and check1's "no").

New tests (test_schedule_j_schema.py):
- test_monthly_expenses_print_on_22c_and_again_on_23b
- test_monthly_net_income_is_income_less_expenses: Social Security
  counts, as Schedule I line 12 does
- test_a_month_that_runs_short_prints_net_income_below_zero
- test_net_income_stays_blank_until_income_is_given: with no income row,
  and with every source left empty
- test_only_an_individual_filing_answers_no_to_is_this_a_joint_case:
  individual ticks /no; joint and no Debtor step print nothing

Refs DIG-61, DIG-177
MSG
git status --short
```

### Task 14: Print monthly income on Form 122A-2 line 1, and support paid and childcare on lines 19 and 21

_Built and verified as commit `526ed27` on `plan/forms-step2b`._

**Files:**

- Create: `backend/apps/forms/tests/test_form_122a2_schema.py`
- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_api_readback.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/form_122a2.json`

**Interfaces:**

- Consumes:
  - The rule `cmi` (`_cmi`, through `current_monthly_income` in `apps/eligibility/cmi.py`). It returns current monthly income: the ten sources without Social Security, quantized half-even to the cent. It raises `IncomeNotSplit` when no source was given or there is no `IncomeInfo`. 122A-1 line 11 (`Debto1.Quest11`) prints it since Task 9.
  - Task 12's rules `schedule_j_support_paid` (`ExpenseInfo.child_support_paid`) and `schedule_j_childcare` (`ExpenseInfo.childcare`). Each returns the amount above $0, and `""` at $0 or with no `ExpenseInfo`.
  - `TEN_SOURCES` in `apps/forms/tests/test_derivations.py`: the ten income amounts, 1023.00 in all, of which Social Security is 32.00.
  - `test_api_readback.py`'s check that Priya's stored 122A-2 holds an amount above 0.
- Produces:
  - `data/forms/schemas/form_122a2.json` goes from 12 objects to 5:
    - `Debtor1.Name` and `Bankruptcy District Information`, unchanged;
    - `Quest1` re-ruled in place to `cmi` (page 1, label "Total monthly income");
    - `undefined_51` (page 5, label "Court-ordered payments", rule `schedule_j_support_paid`);
    - `undefined_53` (page 5, label "Childcare", rule `schedule_j_childcare`).
  - The objects for `Quest5`, `Quest6`, `Quest8`, `Quest9`, `Quest10`, `Quest12`, `Quest13D`, `Quest14` and `Quest15` are gone.
  - The rules `means_test_total_deductions` and `means_test_priority_debts` are deleted, with their functions.
  - `step2_verification.json` goes from 51 rows to 54. The new rows are `form_122a2` `Quest1` `derived:cmi`, `undefined_51` `derived:schedule_j_support_paid` and `undefined_53` `derived:schedule_j_childcare`.
  - `ASSERTED_CASES = 414`. `known_defects.json` drops from 20 entries to 12, and no `form_122a2` entry is left.
  - `backend/apps/forms/tests/test_form_122a2_schema.py`, with:
    - `LEFT_FOR_STEP_3` (13 boxes);
    - `test_line_1_copies_the_monthly_income_from_122a1_line_11`;
    - `test_empty_session_is_asked_for_income_by_source`;
    - `test_support_paid_and_childcare_print_on_lines_19_and_21_only_above_zero` (4 cases);
    - `test_lines_left_for_step_3_print_nothing`.

**Decisions already made in this task:**

- `Quest1` is re-ruled in place: only its `rule` changes, so the box keeps one binding (E006). Line 1 says "Copy line 11 from Official Form 122A-1", so it prints `cmi`, the figure 122A-1 line 11 prints, which leaves Social Security out (C1). It never prints the Schedule I income total.
- `Quest1` lands in the same commit as the nine deletions. `test_api_readback.py` requires Priya's 122A-2, the only one any persona gets, to print an amount above 0. Without `Quest1` she would have only childcare. Her 122A-2 now prints `Quest1` 12000.00 and `undefined_53` 1200.00. Only the comment above that check changes; its assertion stays.
- Lines 19 and 21 share Schedule J's rules for lines 18 and 8, so they print only above $0 (§6.1, 6c option A). An expense left empty is stored as $0, so $0 can't be told from "left blank".
- The nine IRS-standard and deduction boxes lose their bindings until step 3 asks for what they need (B1). They were printing a priority-debt total as a head count on line 5, Schedule J expenses as IRS and U.S. Trustee standards, and the deduction total on line 10. `Quest4` (lines 4 and 39a), `undefined_104` (lines 38 and 39b), `undefined_110` (41a) and `undefined_111` (41b) stay unbound. The 122A-2 result boxes stay blank (DIG-146, OQ-9).
- This ends the transient that started in Task 12. `Quest6`, `Quest8`, `Quest9`, `Quest12`, `Quest13D`, `Quest14` and `Quest15` printed blank at $0 since then, because they shared Schedule J's expense rules. Those bindings are gone now.
- `means_test_total_deductions` and `means_test_priority_debts` lose their last bindings here, so they are deleted (Ruling T0-d). `git grep` finds them only in audit JSON and `known_defects.json`: no code calls them and no test names them. `means_test_disposable_income` stays. It was unbound before 2b (Ruling C-9).
- 122A-2 now raises `IncomeNotSplit` through `cmi` for a session with no income by source, as 122A-1 and 106Sum already do, and a test pins it. Only an above-median session gets 122A-2, and `views._prepare` refuses unsplit income before any form resolves.
- The comment "# Form 122A-2 means test expense deduction derivations" in `DERIVATIONS` now heads only the unbound `means_test_disposable_income`. That is pre-existing (B12). Leave it.
- No owner answer (Q4–Q12) decides these three boxes, so no addendum row cites one. There are no MOVED rows: `form_122a2.audit.json` has no row with these keys. The verified audit row on `Quest1` judged the old binding (target `undefined_104`). The addendum joins on (box, key), so that target never applies to `cmi`.
- The four cases of the lines-19-and-21 test keep pytest's automatic IDs. A reviewer's nit asked for named IDs, and it was accepted as committed.
- `ASSERTED_CASES` goes from 421 to 414 (−7), measured by diffing the collected IDs:
  - −10: the 8 cleared xfails, plus `Quest6` (`schedule_j_food_and_groceries`) and `Quest12` (`schedule_j_vehicle_maintenance`). Those two passed against the audit, and they go with their bindings, clearing nothing.
  - +3: the three addendum rows, all passing.
  - Tier 1, which is not pinned, loses the nine deleted boxes' cases and gains `undefined_51` and `undefined_53`.
- The 8 entries deleted are all tier 2 `wrong_box` orphans:

  - `Quest1` and `Quest10` (`derived:means_test_total_deductions`) and `Quest5` (`derived:means_test_priority_debts`), DIG-60;
  - `Quest8` (`derived:schedule_j_rent_or_mortgage`) and `Quest9` (`derived:schedule_j_utilities`), DIG-66;
  - `Quest13D`, `Quest14` and `Quest15` (`derived:schedule_j_vehicle_payment`), DIG-50.

- [ ] **Step 1: Write the failing tests**

```python file=backend/apps/forms/tests/test_form_122a2_schema.py
"""Form 122A-2: line 1 copies 122A-1's monthly income, and lines 19 and 21 print above $0."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.cmi import IncomeNotSplit
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.tests.test_derivations import TEN_SOURCES
from apps.intake.models import ExpenseInfo, IncomeInfo, IntakeSession

User = get_user_model()

# Every Expenses step amount above $0, so a line still bound to an expense would print.
EXPENSES = {
    "rent_or_mortgage": Decimal("1.00"),
    "utilities": Decimal("2.00"),
    "home_maintenance": Decimal("4.00"),
    "vehicle_payment": Decimal("8.00"),
    "vehicle_insurance": Decimal("16.00"),
    "vehicle_maintenance": Decimal("32.00"),
    "food_and_groceries": Decimal("64.00"),
    "clothing": Decimal("128.00"),
    "medical_expenses": Decimal("256.00"),
    "childcare": Decimal("512.00"),
    "child_support_paid": Decimal("1024.00"),
    "insurance_not_deducted": Decimal("2048.00"),
    "other_expenses": Decimal("4096.00"),
}
# The IRS and U.S. Trustee standards, the deduction lines and the result: step 3 asks
# for what they need (step 2 spec §6.4, B1), so until then they print nothing.
LEFT_FOR_STEP_3 = {
    "Quest4",  # lines 4 and 39a
    "Quest5",
    "Quest6",
    "Quest8",
    "Quest9",
    "Quest10",
    "Quest12",
    "Quest13D",
    "Quest14",
    "Quest15",
    "undefined_104",  # lines 38 and 39b
    "undefined_110",  # line 41a
    "undefined_111",  # line 41b
}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema122a2", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def test_line_1_copies_the_monthly_income_from_122a1_line_11(session):
    # Line 1 says "Copy line 11 from Official Form 122A-1 here": current monthly income,
    # which leaves Social Security out (C1), never an expense or deduction total.
    IncomeInfo.objects.create(session=session, **TEN_SOURCES)

    printed = resolve(load_schema("form_122a2"), session)

    # Every source but Social Security's 32.00: 1023.00 - 32.00.
    assert printed.get("Quest1") == "991.00"
    assert printed.get("Quest1") == resolve(load_schema("form_122a1"), session)["Debto1.Quest11"]


def test_empty_session_is_asked_for_income_by_source(session):
    # Line 1 is CMI, and a filer who gave no income has none to print (spec §5.5).
    with pytest.raises(IncomeNotSplit):
        resolve(load_schema("form_122a2"), session)


@pytest.mark.parametrize(
    "support_paid,childcare,printed",
    [
        (
            Decimal("450.00"),
            Decimal("1200.00"),
            {"undefined_51": "450.00", "undefined_53": "1200.00"},
        ),
        (Decimal("0.01"), Decimal("0.02"), {"undefined_51": "0.01", "undefined_53": "0.02"}),
        (Decimal("0"), Decimal("0"), {}),
        (None, None, {}),  # the Expenses step was never saved
    ],
)
def test_support_paid_and_childcare_print_on_lines_19_and_21_only_above_zero(
    session, support_paid, childcare, printed
):
    # An expense left empty is stored as $0, so $0 can't be told from "left blank": these
    # lines print only above $0, as Schedule J's do (step 2 spec §6.1, 6c option A).
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("9000.00"))
    if support_paid is not None:
        ExpenseInfo.objects.create(
            session=session, child_support_paid=support_paid, childcare=childcare
        )

    resolved = resolve(load_schema("form_122a2"), session)

    lines = ("undefined_51", "undefined_53")
    assert {box: resolved[box] for box in lines if box in resolved} == printed


def test_lines_left_for_step_3_print_nothing(session):
    # Every expense is above $0, so a line still reading one, or a means-test figure
    # step 2 never works out, would print.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("9000.00"))
    ExpenseInfo.objects.create(session=session, **EXPENSES)

    printed = resolve(load_schema("form_122a2"), session)

    assert sorted(LEFT_FOR_STEP_3 & printed.keys()) == []
```

Line 1 must print 991.00 for `TEN_SOURCES` (1023.00 less Social Security's 32.00) and equal 122A-1's resolved `Debto1.Quest11`. Lines 19 and 21 get two different amounts, so a line reading the wrong source fails. `test_lines_left_for_step_3_print_nothing` sets every Expenses amount above $0, so a box still bound to an expense or a means-test figure would print.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_122a2_schema.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `5 failed, 2 passed`. Each failure has the cause this task removes:

- Line 1 prints 0.00, because means_test_total_deductions's bare except finds no means test.
- The empty session raises nothing, because no binding reads income.
- Lines 19 and 21 are unbound, so both non-zero cases print nothing.
- The nine deleted boxes still print.

The 2 passes are the $0 and no-Expenses cases. They pass vacuously, because an unbound box also prints nothing. Once lines 19 and 21 are bound they guard the above-$0 rule.

- [ ] **Step 3: Re-rule line 1, bind lines 19 and 21, and drop the lines step 3 owns**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index f1ace2e..16d17ae 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -488,22 +488,6 @@ def _means_test_disposable_income(session: IntakeSession) -> str:
         return "0.00"


-def _means_test_total_deductions(session: IntakeSession) -> str:
-    try:
-        mt = session.means_test
-        return _fmt(mt.total_allowable_expenses)
-    except Exception:
-        return "0.00"
-
-
-def _means_test_priority_debts(session: IntakeSession) -> str:
-    try:
-        mt = session.means_test
-        return _fmt(mt.priority_debts_monthly)
-    except Exception:
-        return "0.00"
-
-
 # ---------------------------------------------------------------------------
 # DERIVATIONS dict (all referenced functions must be defined above)
 # ---------------------------------------------------------------------------
@@ -608,8 +592,6 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "schedule_j_joint_case": _schedule_j_joint_case,
     # Form 122A-2 means test expense deduction derivations
     "means_test_disposable_income": _means_test_disposable_income,
-    "means_test_total_deductions": _means_test_total_deductions,
-    "means_test_priority_debts": _means_test_priority_debts,
 }


diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index c2eb9e9..d8a50c6 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -508,5 +508,35 @@
     "status": "confirmed",
     "correct_target": "23c",
     "evidence": "Field index: 23c p3 line 23c, column 'Your expenses', 'Subtract your monthly expenses from your monthly income. The result is your monthly net income.' (adjudicated): 23a (Schedule I line 12, schedule_i_income_total) minus 23b (line 22c). Step 2 spec Appendix A.8, §6.2 (schedule_j_monthly_net_income, 23a - 23b), Appendix B R4 (after 23a's new body) and Appendix C.3 (DIG-61); ruling T0-f: blank while 23a is blank, a negative result prints with a minus sign. The audit lists 23c as unbound (schedule_j.unbound.json, DIG-61)."
+  },
+  {
+    "schema": "form_122a2",
+    "pdf_field": "Quest1",
+    "producer": "derived:cmi",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Quest1",
+    "evidence": "Field index: Quest1 p1 line 1, 'Copy your total current monthly income (copy line 11 from Official Form 122A-1)' (adjudicated). 122A-1 line 11 prints cmi (Debto1.Quest11, Quest11). Step 2 spec Appendix A.6, §6.1 (C1, two income totals: CMI, without Social Security, goes on 122A-2 line 1) and §6.4. The audit's verified row on this box judged the old means_test_total_deductions binding, whose total belongs on line 38 (undefined_104), and its auditor note names cmi for line 1; this row joins on (box, key), so that row's target never applies to cmi."
+  },
+  {
+    "schema": "form_122a2",
+    "pdf_field": "undefined_51",
+    "producer": "derived:schedule_j_support_paid",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_51",
+    "evidence": "Field index: undefined_51 p5 line 19, 'Court-ordered payments: total monthly amount paid under court/agency order (e.g., spousal or child support), excluding past-due amounts' (adjudicated). ExpenseInfo.child_support_paid is court-ordered support paid, the figure Schedule J line 18 prints. Step 2 spec Appendix A.6, §6.1 (expense lines, 6c option A: 122A-2 lines 19 and 21 print only above $0), §6.2 (schedule_j_support_paid, Schedule J 18 and 122A-2 line 19) and §6.4. The audit has no row on this box."
+  },
+  {
+    "schema": "form_122a2",
+    "pdf_field": "undefined_53",
+    "producer": "derived:schedule_j_childcare",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_53",
+    "evidence": "Field index: undefined_53 p5 line 21, 'Childcare (babysitting, daycare, nursery, preschool)' (adjudicated). ExpenseInfo.childcare is the filer's childcare, the figure Schedule J line 8 prints. Step 2 spec Appendix A.6, §6.1 (expense lines, 6c option A: 122A-2 lines 19 and 21 print only above $0) and §6.4. The audit has no row on this box."
   }
 ]
diff --git a/data/forms/schemas/form_122a2.json b/data/forms/schemas/form_122a2.json
index 18124f4..0500e08 100644
--- a/data/forms/schemas/form_122a2.json
+++ b/data/forms/schemas/form_122a2.json
@@ -46,7 +46,7 @@
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "means_test_total_deductions",
+      "rule": "cmi",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -55,15 +55,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Quest5",
+      "pdf_field": "undefined_51",
       "type": "text",
       "source": "derived",
-      "page": 2,
-      "label": "Number used for deductions",
+      "page": 5,
+      "label": "Court-ordered payments",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "means_test_priority_debts",
+      "rule": "schedule_j_support_paid",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -72,134 +72,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Quest6",
+      "pdf_field": "undefined_53",
       "type": "text",
       "source": "derived",
-      "page": 2,
-      "label": "Amount for food, clothing, and other items",
+      "page": 5,
+      "label": "Childcare",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "schedule_j_food_and_groceries",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Quest8",
-      "type": "text",
-      "source": "derived",
-      "page": 3,
-      "label": "Net mortgage/rent expenses",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "schedule_j_rent_or_mortgage",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Quest9",
-      "type": "text",
-      "source": "derived",
-      "page": 3,
-      "label": "Housing/utilities - Morgage and rent expenses",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "schedule_j_utilities",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Quest10",
-      "type": "text",
-      "source": "derived",
-      "page": 3,
-      "label": "Corrected housing calculation of monthly expenses",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "means_test_total_deductions",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Quest12",
-      "type": "text",
-      "source": "derived",
-      "page": 3,
-      "label": "Vehicle operating expenses",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "schedule_j_vehicle_maintenance",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Quest13D",
-      "type": "text",
-      "source": "derived",
-      "page": 4,
-      "label": "Ownership or leasing costs",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "schedule_j_vehicle_payment",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Quest14",
-      "type": "text",
-      "source": "derived",
-      "page": 4,
-      "label": "Public transportation expense",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "schedule_j_vehicle_payment",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Quest15",
-      "type": "text",
-      "source": "derived",
-      "page": 4,
-      "label": "Additional public transportation expense",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "schedule_j_vehicle_payment",
+      "rule": "schedule_j_childcare",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
PATCH
```

The schema follows Appendix A.6 row by row. The three ADD rows get their addendum rows in this commit (§7.4), each citing the box's field-index label. The two means-test rules lose their last bindings with the nine deleted boxes, so they go in the same commit (E007 only forbids deleting a rule that is still bound).

- [ ] **Step 4: Run the oracle against the old list and watch it fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `2 failed, 1247 passed`. test_every_listed_defect_is_a_case_the_oracle_runs names the 8 form_122a2 entries whose cases are gone: Quest1, Quest5, Quest8, Quest9, Quest10, Quest13D, Quest14 and Quest15. Quest1's old case went with its re-rule. The coverage tripwire, test_tier2_coverage_changes_only_on_purpose, collects 414 asserted cases against the pinned 421. There is no XPASS, and nothing else may fail.

- [ ] **Step 5: Delete the 8 entries, pin the new count, and say what Priya's 122A-2 prints**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index 6ef005e..bda001d 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -23,70 +23,6 @@
     "class": "wrong_box",
     "ticket": "DIG-77"
   },
-  {
-    "form_type": "form_122a2",
-    "pdf_field": "Quest1",
-    "tier": "2",
-    "case": "derived:means_test_total_deductions",
-    "class": "wrong_box",
-    "ticket": "DIG-60"
-  },
-  {
-    "form_type": "form_122a2",
-    "pdf_field": "Quest10",
-    "tier": "2",
-    "case": "derived:means_test_total_deductions",
-    "class": "wrong_box",
-    "ticket": "DIG-60"
-  },
-  {
-    "form_type": "form_122a2",
-    "pdf_field": "Quest13D",
-    "tier": "2",
-    "case": "derived:schedule_j_vehicle_payment",
-    "class": "wrong_box",
-    "ticket": "DIG-50"
-  },
-  {
-    "form_type": "form_122a2",
-    "pdf_field": "Quest14",
-    "tier": "2",
-    "case": "derived:schedule_j_vehicle_payment",
-    "class": "wrong_box",
-    "ticket": "DIG-50"
-  },
-  {
-    "form_type": "form_122a2",
-    "pdf_field": "Quest15",
-    "tier": "2",
-    "case": "derived:schedule_j_vehicle_payment",
-    "class": "wrong_box",
-    "ticket": "DIG-50"
-  },
-  {
-    "form_type": "form_122a2",
-    "pdf_field": "Quest5",
-    "tier": "2",
-    "case": "derived:means_test_priority_debts",
-    "class": "wrong_box",
-    "ticket": "DIG-60"
-  },
-  {
-    "form_type": "form_122a2",
-    "pdf_field": "Quest8",
-    "tier": "2",
-    "case": "derived:schedule_j_rent_or_mortgage",
-    "class": "wrong_box",
-    "ticket": "DIG-66"
-  },
-  {
-    "form_type": "form_122a2",
-    "pdf_field": "Quest9",
-    "tier": "2",
-    "case": "derived:schedule_j_utilities",
-    "class": "wrong_box",
-    "ticket": "DIG-66"
-  },
   {
     "form_type": "schedule_a_b",
     "pdf_field": "12",
diff --git a/backend/apps/forms/tests/test_api_readback.py b/backend/apps/forms/tests/test_api_readback.py
index a3b3791..0608f22 100644
--- a/backend/apps/forms/tests/test_api_readback.py
+++ b/backend/apps/forms/tests/test_api_readback.py
@@ -181,7 +181,7 @@ def test_forms_built_through_the_api_print_what_the_seeded_forms_print(persona):
     assert _fee_waiver_answers(built) == _fee_waiver_answers(seeded)
     assert (_fee_waiver_answers(built) is None) == (persona not in WAIVER_FILERS)
     # Only Priya's income is above the median, so only her packet holds 122A-2, and it
-    # prints figures worked out from her own expenses.
+    # prints her own figures: her monthly income on line 1 and her childcare on line 21.
     assert ("form_122a2" in stored) == (persona == "priya")
     if persona == "priya":
         amounts = [_amount(value) for value in stored["form_122a2"].values()]
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index aa2d684..52bffc2 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 421
+ASSERTED_CASES = 414


 def _audit_dir():
PATCH
```

The patch deletes exactly the 8 entries (64 lines) and keeps the order of the 12 that remain. Never produce this change by re-running the recorder (R3). The read-back's comment on Priya's 122A-2 said it "prints figures worked out from her own expenses". It now says what she gets: her monthly income on line 1 and her childcare on line 21.

- [ ] **Step 6: Run the tests and the oracle again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_122a2_schema.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `7 passed`.

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `1249 passed, 1 skipped, 12 xfailed`. That is one xfail for each of the 12 entries left, and the skip is tier 1's empty checkbox parameter set (Ruling C-6).

- [ ] **Step 7: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2b.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2102 passed, 1 skipped, 13 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  358 passed (358)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

No journeys this task: it changes no page or flow, only what Form 122A-2 prints.

- [ ] **Step 8: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_form_122a2_schema.py \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_api_readback.py \
  backend/apps/forms/tests/test_oracle_tier2.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/form_122a2.json
git commit -F - <<'MSG'
fix(forms): Form 122A-2 prints monthly income on line 1, and support paid and childcare on lines 19 and 21

Form 122A-2 follows the step 2 spec (Appendix A.6, §6.1, §6.4):
- Line 1, "Copy line 11 from Official Form 122A-1", prints current
  monthly income: Quest1 is re-ruled in place from
  means_test_total_deductions to cmi, the rule 122A-1 line 11 prints
  (C1: Social Security left out).
- Line 19 (undefined_51) prints court-ordered support paid
  (schedule_j_support_paid) and line 21 (undefined_53) childcare
  (schedule_j_childcare), each only above $0 (6c option A), as on
  Schedule J 18 and 8.
- The IRS and U.S. Trustee standard lines and the deduction lines lose
  their bindings until step 3 asks what they need (B1): Quest5, Quest6,
  Quest8, Quest9, Quest10, Quest12, Quest13D, Quest14 and Quest15. They
  printed a priority-debt total as a head count, Schedule J expenses as
  IRS standards, and the deduction total on line 10. The name and the
  district stay; Quest4 (lines 4 and 39a), undefined_104 (38) and
  41a/41b stay unbound.

means_test_total_deductions and means_test_priority_debts lose their
last bindings and are deleted (no caller outside DERIVATIONS, no test
names them). means_test_disposable_income stays: it was unbound before
step 2 (Ruling C-9).

122A-2 now raises IncomeNotSplit through cmi for a session with no
income by source, as 122A-1 and 106Sum already do. Only an
above-median session gets 122A-2, and the forms views refuse unsplit
income before any form is built.

Oracle:
- step2_verification.json gains the three ADD rows: Quest1 (cmi),
  undefined_51 and undefined_53 (51 -> 54). The audit's verified row on
  Quest1 judged the old binding (target undefined_104); the addendum
  joins on (box, key), so that target never applies to cmi.
- Tier 3 is unchanged: 122A-2 has no rows.

Clears 8 known-defect entries (20 -> 12), all tier 2 wrong_box by
orphan: Quest1, Quest5 and Quest10 (DIG-60), Quest8 and Quest9
(DIG-66), Quest13D, Quest14 and Quest15 (DIG-50). Before the deletion,
exactly those 8 orphans and the coverage tripwire failed.

ASSERTED_CASES 421 -> 414 (-7), measured by diffing the collected IDs:
-10 (the 10 deleted or re-keyed cases: the 8 cleared xfails, and
Quest6 and Quest12, which passed against the audit and go with their
bindings), +3 (the three addendum rows, all passing). Tier 1 loses the
nine deleted boxes' cases and gains undefined_51 and undefined_53.

New tests (test_form_122a2_schema.py):
- test_line_1_copies_the_monthly_income_from_122a1_line_11
- test_empty_session_is_asked_for_income_by_source
- test_support_paid_and_childcare_print_on_lines_19_and_21_only_above_zero:
  distinct amounts, one cent, $0 and no Expenses step
- test_lines_left_for_step_3_print_nothing: every expense above $0

test_api_readback.py: the comment on Priya's 122A-2 now says what it
prints (line 1 income, line 21 childcare); the assertion is unchanged.

Refs DIG-50, DIG-60, DIG-66
MSG
git status --short
```

### Task 15: Print Schedule A/B's totals and section answers, G's and H's name and line 1, and only Schedule C's law

_Built and verified as commit `4ed54e3` on `plan/forms-step2b`._

**Files:**

- Create: `backend/apps/forms/tests/test_schedule_a_b_schema.py`
- Create: `backend/apps/forms/tests/test_schedule_c_schema.py`
- Create: `backend/apps/forms/tests/test_schedules_g_h_schema.py`
- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/schedule_a_b.json`
- Modify: `data/forms/schemas/schedule_c.json`
- Modify: `data/forms/schemas/schedule_g.json`
- Modify: `data/forms/schemas/schedule_h.json`

**Interfaces:**

- Consumes:
  - `_sum_encrypted` and `_fmt` in `derivations.py`.
  - `AssetInfo`, through `session.assets`:
    - its six `asset_type` values: `real_property`, `vehicle`, `bank_account`, `retirement_account`, `personal_property` and `other`;
    - `current_value`, an `EncryptedDecimalField`, so SQL `Sum()` can't add it;
    - `description`, a `CharField(255)`;
    - `Meta.ordering = ["asset_type", "-current_value"]`.
  - `ExecutoryContract` through `session.executory_contracts`, and `Codebtor` through `session.codebtors`.
  - Existing rules, whose bodies stay unchanged:
    - `full_name`;
    - `total_real_property`, shared with 106Sum 1a;
    - `total_personal_property` (every asset but real property), shared with 106Sum 1b;
    - `total_assets`, shared with 106Sum 1c and Form 101's `total_assets_range`;
    - `total_other_assets`, which no schema has bound since before 2b.
  - `PDFFormFiller().fill` and `read_widgets` (`apps/forms/tests/pdf_readback.py`). The new tests read what a filled box shows through them.
- Produces:
  - Rules in `DERIVATIONS`, under the new heading "Schedule A/B part totals, line 53, and the section questions of A/B, G and H":
    - `total_vehicles` (`_total_vehicles`, `vehicle`), `total_household_items` (`_total_household_items`, `personal_property`) and `total_financial_assets` (`_total_financial_assets`, `bank_account` and `retirement_account`). Each sums `current_value` with `_sum_encrypted` and prints 0.00 for an empty list.
    - `other_asset_descriptions` (`_other_asset_descriptions`): the `other` assets' descriptions, `.order_by("id")`, joined with `"; "`. It returns `""` when there are none.
    - `has_real_property`, `has_vehicles`, `has_bank_accounts`, `has_retirement_accounts`, `has_other_assets`, `has_executory_contracts` and `has_codebtors`. Each is a lambda over `_yes_if_any(rows)`, which returns `"yes"` if `rows.exists()` and `"no"` otherwise. Task 16 reuses `_yes_if_any`.
  - The rules `total_bank_accounts` and `total_retirement_accounts` are deleted, with their functions.
  - `schedule_a_b.json` goes from 4 objects to 20. `12` and `16 Cash amount` are gone. These derived objects are added:
    - Checkboxes `Check 2` (`has_real_property`, `{"yes": "/yes", "no": "/On"}`), `Check 3` (`has_vehicles`), `Check 17` (`has_bank_accounts`) and `check 21` (`has_retirement_accounts`), the last three `{"yes": "/yes", "no": "/no"}`, and `check 53` (`has_other_assets`, `{"yes": "/On", "no": "/no"}`).
    - Text box `53 Examples Season tickets country club membership` (`other_asset_descriptions`).
    - Totals: `undefined_13` and `undefined_159` (`total_real_property`); `undefined_26` and `undefined_160` (`total_vehicles`); `15 amount` and `undefined_161` (`total_household_items`); `undefined_124` and `undefined_162` (`total_financial_assets`); `undefined_158` and `undefined_165` (`total_other_assets`); `undefined_166` (`total_personal_property`); `undefined_167` (`total_assets`).
  - `schedule_c.json` goes from 9 objects to 3: `Debtor 1`, `2.2` (`answer:schedule_c.statute_2.2`) and the district. `2.1`, `2.3`, `3`, `4`, `5` and `6` are gone.
  - `schedule_g.json` and `schedule_h.json` go from 1 object to 3 each. They gain `Debtor 1` (`full_name`, page 1) and `check1`, a checkbox with `{"yes": "/yes", "no": "/no"}` (`has_executory_contracts` on G, `has_codebtors` on H).
  - `step2_verification.json` goes from 54 rows to 76: 18 on A/B, 2 on G and 2 on H, one for each new binding, each under its own binding key (for example `derived:has_real_property`, `derived:total_vehicles`, `derived:full_name`).
  - `ASSERTED_CASES = 428`. `known_defects.json` drops from 12 entries to 4: Form 107 `Income 5a Debtor 1`, `Income 5b Debtor 1` and `Income 5c Debtor 1`, and Schedule D `undefined_27`.
  - New test modules:
    - `test_schedule_a_b_schema.py`: `test_each_part_total_prints_on_its_own_line_and_again_on_the_summary`, `test_the_summary_adds_up_the_way_the_form_says`, `test_the_summary_form_copies_the_property_totals_schedule_a_b_prints`, `test_a_filer_with_no_property_gets_zero_totals_and_no_on_every_question`, `test_each_property_question_answers_yes_only_for_the_kind_listed` (one case per `ASSET_TYPE_CHOICES` kind), `test_other_property_is_described_in_the_order_the_filer_listed_it` and `test_lines_the_intake_never_asks_print_nothing`.
    - `test_schedule_c_schema.py`: `test_no_description_or_amount_prints_where_the_form_asks_for_a_law`.
    - `test_schedules_g_h_schema.py`: `test_the_filers_name_heads_every_page`, `test_line_1_answers_yes_only_when_the_filer_listed_one` and `test_each_schedule_answers_from_its_own_list_only`, each run for G and H.

**Decisions already made in this task:**

- The owner's Q8 decides the section questions, word for word: "derived from the lists, Yes with rows and No without: A/B `Check 2`, `Check 3`, `Check 17`, `check 21`, `check 53`; D, G and H `check1`; E/F `check7`." This task binds the A/B, G and H boxes. D and E/F are Task 16's. Each `has_*` rule returns exactly `yes` or `no`, never `""`, so an empty list answers No and can't raise `UnmappedChoice`. 2a's save fixes are why an empty list means the filer listed none, not a failed save.
- The owner's Q9 decides line 53 and Part 3, word for word: "prints on A/B line 53 and in the line 54 and 61 totals. A new `personal_property` asset type feeds line 15 and line 57."
- The template's states are irregular, and every state comes from the field index. Line 1's "No. Go to Part 2." exports `/On`, and so does line 53's "Yes. Give specific information." So `Check 2` is `{"yes": "/yes", "no": "/On"}` and `check 53` is `{"yes": "/On", "no": "/no"}`. Tier 1's box cases prove the filler ticks them.
- The totals print before their item rows (§6.1 B5):
  - Part 4 (lines 36 and 58) adds deposits and retirement accounts, the only Part 4 lines DigniFi asks; the other lines count as zero (§6.1).
  - Lines 59 and 60 stay blank.
  - Line 62 adds 56 through 61 only because `asset_type` has exactly six kinds. Its rule, `total_personal_property`, keeps its body, as do `total_real_property` and `total_assets`: 106Sum 1a–1c share them, and tier 3 checks those three boxes.
- Ruling T0-e: an empty list prints 0.00 on every total. The filer finished the intake, and Q8 already reads an empty list as "No".
- Every total sums in Python with `_sum_encrypted`, as the existing totals do, never with SQL `Sum()`: `current_value` is encrypted.
- `undefined_166` is one full name with two widgets, line 62 and its "Copy personal property total" box. One binding fills both (E006).
- `other_asset_descriptions` must call `.order_by("id")`. The model's own order sorts on the encrypted `current_value`, so it follows ciphertext, and the filer's order is the id's (DIG-164). Line 53's text has no length limit: a long list overflows the box on the page, and nothing errors. The spec asks for the join as it is, and step 3's rows replace it.
- `total_other_assets` is bound again, on lines 54 and 61, with its body unchanged, so it leaves the list of rules unbound since before 2b (Ruling C-9). The A/B audit row with its key names no box (`correct_target` `""`), so only the addendum rows assert lines 54 and 61.
- Only G and H gain `Debtor 1`. A/B, C, D and E/F already bind it, so a second object there is an E006 error. The G and H audits' `Debtor 2` rows carry the key `derived:full_name` but target "leave blank", so moved-here can't assert the new headers. Each has its addendum row.
- The `has_*` lambdas read the session's related managers (`s.assets`, `s.executory_contracts`, `s.codebtors`), where the totals filter `AssetInfo.objects` with a local import. Both forms are scoped to the session and give the same rows.
- `total_bank_accounts` and `total_retirement_accounts` lose their only bindings, A/B `12` and `16 Cash amount`, so they are deleted (Ruling T0-d). A whole-tree `git grep` finds no caller and no test that names them.
- Schedule C keeps only `2.2` (`answer:schedule_c.statute_2.2`), the law. The six boxes put descriptions and an amount in the "Specific laws that allow exemption" column, and they wait for step 3's rows (Appendix E).
- These A/B boxes stay unbound, as Appendix A.9 says: line 4's question, `Check 16` (cash), `6 check`, line 53's amounts (`undefined_155` to `undefined_157`), and lines 59 and 60. An RV entered as a vehicle ticks line 3, not line 4 (spec §10).
- The new objects' labels come from the index wording, or a short "Part N total: …" where the index says only "Write that number here". A reviewer's nit about the paraphrase was accepted as committed: no check reads labels.
- After this task, `test_oracle_tier1.py`'s comment "Another key's value can hide a marker in a batch (Schedule C 2.3); re-check alone" names a box that is no longer bound. Its re-check branch no longer runs. Task 18 rewrites that test. Leave it here.
- `ASSERTED_CASES` goes from 414 to 428 (+14), measured by diffing the collected IDs:
  - −8: the 8 cleared xfails.
  - +22: the addendum rows, all passing.
  - Tier 1, which is not pinned, loses the deleted boxes' 8 text cases and gains 15 text cases and 14 checkbox cases.
- The 8 entries deleted are all tier 2 `wrong_box` orphans:
  - A/B `12` (`derived:total_retirement_accounts`) and `16 Cash amount` (`derived:total_bank_accounts`), DIG-80;
  - Schedule C `2.1` (`asked:answer:schedule_c.desc_2.1`), `2.3` (`asked:answer:schedule_c.amount_2.3`), and `3`, `4`, `5` and `6` (`asked:answer:schedule_c.desc_3` to `desc_6`), DIG-81.
- Tier 3 doesn't change: A/B, C, G and H have no rows, and 106Sum's 1a–1c rows read the unchanged rules.

- [ ] **Step 1: Write the failing tests**

```python file=backend/apps/forms/tests/test_schedule_a_b_schema.py
"""
Schedule A/B: each part's total prints on its own line and again on the summary, and each
property question answers Yes only for the kind of property the filer listed.

Business intent: the totals are what the trustee reads first, and 106Sum copies lines 55,
62 and 63. Until step 3 asks for each item's row, the boxes that need a row stay blank
(step 2 spec §6.1 B5, Appendix A.9, owner Q8 and Q9).
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_widgets
from apps.intake.models import AssetInfo, IncomeInfo, IntakeSession

User = get_user_model()

# One or two rows of each kind, each a distinct power of two, so a total that reads the
# wrong kind, or misses a row, prints a different figure.
ASSETS = [
    ("real_property", "1.00"),
    ("vehicle", "2.00"),
    ("vehicle", "4.00"),
    ("bank_account", "8.00"),
    ("retirement_account", "16.00"),
    ("personal_property", "32.00"),
    ("personal_property", "64.00"),
    ("other", "128.00"),
]
# Box → what it prints with ASSETS.
TOTALS = {
    "undefined_13": "1.00",  # line 2, Part 1: real estate
    "undefined_159": "1.00",  # line 55, copies line 2
    "undefined_26": "6.00",  # line 5, Part 2: vehicles
    "undefined_160": "6.00",  # line 56, copies line 5
    "15 amount": "96.00",  # line 15, Part 3: personal and household items
    "undefined_161": "96.00",  # line 57, copies line 15
    "undefined_124": "24.00",  # line 36, Part 4: deposits (17) and retirement accounts (21)
    "undefined_162": "24.00",  # line 58, copies line 36
    "undefined_158": "128.00",  # line 54, Part 7: other property
    "undefined_165": "128.00",  # line 61, copies line 54
    "undefined_166": "254.00",  # line 62, lines 56 through 61
    "undefined_167": "255.00",  # line 63, line 55 + line 62
}
# Kind of property → (its question's box, the state its "Yes" exports, its "No"), each
# state from the field index. The template is irregular: line 1's "No. Go to Part 2."
# exports On, and so does line 53's "Yes. Give specific information."
QUESTIONS = {
    "real_property": ("Check 2", "/yes", "/On"),  # line 1
    "vehicle": ("Check 3", "/yes", "/no"),  # line 3
    "bank_account": ("Check 17", "/yes", "/no"),  # line 17
    "retirement_account": ("check 21", "/yes", "/no"),  # line 21
    "other": ("check 53", "/On", "/no"),  # line 53
}
OTHER_PROPERTY = "53 Examples Season tickets country club membership"
LINE_4_QUESTION = (
    "Examples Boats trailers motors personal watercraft fishing vessels snowmobiles "
    "motorcycle accessories"
)
# Boxes that need a row, or a figure, the intake never asks for (step 3).
LEFT_BLANK = {
    "12",  # line 1.2, a second property's street address
    "16 Cash amount",  # line 16, cash
    "Check 16",  # line 16's question
    LINE_4_QUESTION,  # boats and other recreational vehicles (spec §10)
    "6 check",  # line 6's question, household goods
    "undefined_155",  # line 53's amounts
    "undefined_156",
    "undefined_157",
    "undefined_163",  # line 59, Part 5: business property
    "undefined_164",  # line 60, Part 6: farm and fishing property
}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemaab", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def _asset(session, asset_type, value, description="Item"):
    AssetInfo.objects.create(
        session=session,
        asset_type=asset_type,
        description=description,
        current_value=Decimal(value),
    )


def _filled(session):
    """Box → what a viewer sees in it once the form is filled: the ticked states, or the text."""
    values = resolve(load_schema("schedule_a_b"), session)
    shows = {}
    for widget in read_widgets(PDFFormFiller().fill("schedule_a_b", values)):
        seen = shows.setdefault(widget.full_name, set())
        if widget.state is not None:
            if widget.state != "/Off":
                seen.add(widget.state)
        elif widget.value:
            seen.add(widget.value)
    return shows


def test_each_part_total_prints_on_its_own_line_and_again_on_the_summary(session):
    for asset_type, value in ASSETS:
        _asset(session, asset_type, value)

    printed = resolve(load_schema("schedule_a_b"), session)

    assert {box: printed.get(box) for box in TOTALS} == TOTALS


def test_the_summary_adds_up_the_way_the_form_says(session):
    # Line 62 adds lines 56 through 61, and line 63 adds line 55 and line 62. Lines 59
    # and 60 (business and farm property) are never asked, so they count as zero.
    for asset_type, value in ASSETS:
        _asset(session, asset_type, value)

    printed = resolve(load_schema("schedule_a_b"), session)

    def line(box):
        return Decimal(printed[box])

    assert "undefined_163" not in printed and "undefined_164" not in printed
    lines_56_to_61 = ("undefined_160", "undefined_161", "undefined_162", "undefined_165")
    assert line("undefined_166") == sum(line(box) for box in lines_56_to_61)
    assert line("undefined_167") == line("undefined_159") + line("undefined_166")


def test_the_summary_form_copies_the_property_totals_schedule_a_b_prints(session):
    # 106Sum lines 1a, 1b and 1c say "Copy line 55", "Copy line 62" and "Copy line 63
    # from Schedule A/B": the two forms must never disagree.
    for asset_type, value in ASSETS:
        _asset(session, asset_type, value)
    # 106Sum line 8 prints current monthly income, which needs income by source.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))

    schedule = resolve(load_schema("schedule_a_b"), session)
    summary = resolve(load_schema("form_106sum"), session)

    assert {line: summary[line] for line in ("1a", "1b", "1c")} == {
        "1a": schedule["undefined_159"],
        "1b": schedule["undefined_166"],
        "1c": schedule["undefined_167"],
    }


def test_a_filer_with_no_property_gets_zero_totals_and_no_on_every_question(session):
    # The filer finished the intake with an empty list, which is "none" (Ruling T0-e,
    # owner Q8), so the totals print 0.00 and every question says No.
    filled = _filled(session)

    assert {box: filled.get(box) for box in TOTALS} == {box: {"0.00"} for box in TOTALS}
    assert {box: filled.get(box) for box, _, _ in QUESTIONS.values()} == {
        box: {no} for box, _, no in QUESTIONS.values()
    }
    assert filled.get(OTHER_PROPERTY) == set()


@pytest.mark.parametrize("asset_type", [kind for kind, _ in AssetInfo.ASSET_TYPE_CHOICES])
def test_each_property_question_answers_yes_only_for_the_kind_listed(session, asset_type):
    # Household goods have no question bound yet (lines 6-14 need rows, step 3), so a
    # filer who lists only those answers No to all five.
    _asset(session, asset_type, "1.00")

    filled = _filled(session)

    assert {kind: filled.get(box) for kind, (box, _, _) in QUESTIONS.items()} == {
        kind: {yes if kind == asset_type else no} for kind, (_, yes, no) in QUESTIONS.items()
    }


def test_other_property_is_described_in_the_order_the_filer_listed_it(session):
    # The values run against the order listed, so an order by value can't pass, and the
    # stored order follows the encrypted value (DIG-164): only the id is the filer's order.
    _asset(session, "other", "50.00", "Season tickets")
    _asset(session, "vehicle", "4000.00", "2015 Honda Civic")
    _asset(session, "other", "900.00", "Club membership")
    _asset(session, "other", "10.00", "Coin collection")
    _asset(session, "other", "300.00", "Timeshare points")

    printed = resolve(load_schema("schedule_a_b"), session)

    assert printed.get(OTHER_PROPERTY) == (
        "Season tickets; Club membership; Coin collection; Timeshare points"
    )


def test_lines_the_intake_never_asks_print_nothing(session):
    # Every kind of property is listed, so a box still bound to a total, or to an
    # answer about one, would print. The account totals once filled the second
    # property's street address (line 1.2) and the cash line (16).
    for asset_type, value in ASSETS:
        _asset(session, asset_type, value)

    filled = _filled(session)

    assert {box: filled.get(box) for box in LEFT_BLANK} == {box: set() for box in LEFT_BLANK}
```

```python file=backend/apps/forms/tests/test_schedule_c_schema.py
"""
Schedule C: an answer prints only on the box that asks for it.

Business intent: Schedule C claims exemptions, a legal choice the filer makes. Six answer
boxes printed descriptions and amounts in the "Specific laws that allow exemption" column,
which would claim an exemption under a law nobody chose. They stay blank until step 3
asks for each row; the law the filer gave for row 2.2 stays on its own line (step 2 spec
Appendix A.13, Appendix E 4).
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.intake.models import FormAnswer, IntakeSession

User = get_user_model()

# Answer key → the box that printed it, though that box asks for a law.
MISPLACED = {
    "desc_2.1": "2.1",
    "amount_2.3": "2.3",
    "desc_3": "3",
    "desc_4": "4",
    "desc_5": "5",
    "desc_6": "6",
}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemac", password="pass")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        state="IL",
        court_name="U.S. Bankruptcy Court",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    return IntakeSession.objects.create(user=user, district=district)


def test_no_description_or_amount_prints_where_the_form_asks_for_a_law(session):
    for key in [*MISPLACED, "statute_2.2"]:
        FormAnswer.objects.create(
            session=session, form_type="schedule_c", field_key=key, value=f"answer {key}"
        )

    printed = resolve(load_schema("schedule_c"), session)

    assert sorted(set(MISPLACED.values()) & printed.keys()) == []
    assert printed.get("2.2") == "answer statute_2.2"
```

```python file=backend/apps/forms/tests/test_schedules_g_h_schema.py
"""
Schedules G and H: the filer's name heads every page, and line 1 answers Yes only when the
filer listed a contract or lease (G) or a codebtor (H).

Business intent: a page without the filer's name can be separated from the filing, and
line 1's answer tells the trustee whether to read on. DigniFi derives it from the lists
the filer saved, Yes with rows and No without (step 2 spec Appendix A.10, owner Q8).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_widgets
from apps.intake.models import Codebtor, DebtorInfo, ExecutoryContract, IntakeSession

User = get_user_model()


def _contract(session):
    ExecutoryContract.objects.create(
        session=session, counterparty_name="Lakeview Apartments", contract_type="lease"
    )


def _codebtor(session):
    Codebtor.objects.create(session=session, name="Pat Doe", relationship="relative")


# Form → how the filer lists one of what its line 1 asks about.
LISTS = {"schedule_g": _contract, "schedule_h": _codebtor}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemagh", password="pass")
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
        middle_name="",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


def _printed(session, form_type):
    """The filled form's widgets, as a viewer sees them."""
    values = resolve(load_schema(form_type), session)
    return read_widgets(PDFFormFiller().fill(form_type, values))


@pytest.mark.parametrize("form_type", LISTS)
def test_the_filers_name_heads_every_page(session, form_type):
    widgets = _printed(session, form_type)

    # One field with a widget on each page: both pages show the name.
    named = {w.page for w in widgets if w.full_name == "Debtor 1" and w.value == "Jane Doe"}
    assert named == {1, 2}
    # A single filer's packet: the spouse's line stays blank.
    assert [w.value for w in widgets if w.full_name == "Debtor 2"] == [None]


@pytest.mark.parametrize("listed,ticks", [(True, {"/yes"}), (False, {"/no"})])
@pytest.mark.parametrize("form_type", LISTS)
def test_line_1_answers_yes_only_when_the_filer_listed_one(session, form_type, listed, ticks):
    if listed:
        LISTS[form_type](session)

    widgets = _printed(session, form_type)

    assert {w.state for w in widgets if w.full_name == "check1" and w.state != "/Off"} == ticks


@pytest.mark.parametrize("form_type", LISTS)
def test_each_schedule_answers_from_its_own_list_only(session, form_type):
    # A lease is no codebtor, and a codebtor no lease.
    for other, list_one in LISTS.items():
        if other != form_type:
            list_one(session)

    assert resolve(load_schema(form_type), session).get("check1") == "/no"
```

- **Schedule A/B:** the tests list assets at distinct powers of two, with two rows each for vehicles and household goods, so a total that reads the wrong kind or misses a row prints a different figure. The question tests and the empty-list test fill the PDF and read back what each box shows, so they catch a wrong export state, not just a wrong answer. The line-53 test lists four "Other" rows whose values run against the order they were listed, plus a vehicle whose description must not appear.
- **Schedule C:** the test stores all seven answer keys and requires that only `2.2` prints.
- **Schedules G and H:** the tests read the filled PDF for the name on both pages and for line 1's tick. They also check that a lease never answers H's question and a codebtor never answers G's.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_schedule_a_b_schema.py apps/forms/tests/test_schedule_c_schema.py apps/forms/tests/test_schedules_g_h_schema.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `21 failed`. Every case fails for the reason this task removes:

- A/B's totals and line 53 are unbound and print nothing.
- The summary and 106Sum tests find no line 55 or 62.
- No A/B question ticks.
- Lines 12 and 16 Cash amount still print the retirement and bank totals.
- G and H print no name and tick nothing.
- Schedule C prints 2.1, 2.3, 3, 4, 5 and 6.

- [ ] **Step 3: Add the part totals, line 53's descriptions and the section-question rules, and drop the two account totals**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index 16d17ae..7d7f1a4 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -132,20 +132,6 @@ def _total_debts(session: IntakeSession) -> str:
     return _fmt(_sum_encrypted(qs, "amount_owed"))


-def _total_bank_accounts(session: IntakeSession) -> str:
-    from apps.intake.models import AssetInfo
-
-    qs = AssetInfo.objects.filter(session=session, asset_type="bank_account")
-    return _fmt(_sum_encrypted(qs, "current_value"))
-
-
-def _total_retirement_accounts(session: IntakeSession) -> str:
-    from apps.intake.models import AssetInfo
-
-    qs = AssetInfo.objects.filter(session=session, asset_type="retirement_account")
-    return _fmt(_sum_encrypted(qs, "current_value"))
-
-
 def _total_other_assets(session: IntakeSession) -> str:
     from apps.intake.models import AssetInfo

@@ -174,6 +160,49 @@ def _total_monthly_expenses(session: IntakeSession) -> str:
     return _fmt(Decimal(str(expense_info.calculate_total_monthly_expenses())))


+# ---------------------------------------------------------------------------
+# Schedule A/B part totals, line 53, and the section questions of A/B, G and H
+# ---------------------------------------------------------------------------
+
+
+def _total_vehicles(session: IntakeSession) -> str:
+    from apps.intake.models import AssetInfo
+
+    qs = AssetInfo.objects.filter(session=session, asset_type="vehicle")
+    return _fmt(_sum_encrypted(qs, "current_value"))
+
+
+def _total_household_items(session: IntakeSession) -> str:
+    from apps.intake.models import AssetInfo
+
+    qs = AssetInfo.objects.filter(session=session, asset_type="personal_property")
+    return _fmt(_sum_encrypted(qs, "current_value"))
+
+
+def _total_financial_assets(session: IntakeSession) -> str:
+    """Part 4, line 36: deposits (17) and retirement accounts (21), the only lines asked."""
+    from apps.intake.models import AssetInfo
+
+    qs = AssetInfo.objects.filter(
+        session=session, asset_type__in=("bank_account", "retirement_account")
+    )
+    return _fmt(_sum_encrypted(qs, "current_value"))
+
+
+def _other_asset_descriptions(session: IntakeSession) -> str:
+    """Line 53: the "Other" assets in the order the filer listed them (DIG-164)."""
+    from apps.intake.models import AssetInfo
+
+    # The model orders by encrypted value, so the filer's order is the id's.
+    qs = AssetInfo.objects.filter(session=session, asset_type="other").order_by("id")
+    return "; ".join(qs.values_list("description", flat=True))
+
+
+def _yes_if_any(rows) -> str:
+    """A section's Yes/No question (owner Q8): "yes" when the filer listed one, else "no"."""
+    return "yes" if rows.exists() else "no"
+
+
 # ---------------------------------------------------------------------------
 # Form 101 lines 18-20: estimated creditors, assets and liabilities
 # ---------------------------------------------------------------------------
@@ -519,13 +548,25 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "total_secured_debts": _total_secured_debts,
     "total_nonpriority_unsecured": _total_nonpriority_unsecured,
     "total_debts": _total_debts,
-    "total_bank_accounts": _total_bank_accounts,
-    "total_retirement_accounts": _total_retirement_accounts,
     "total_other_assets": _total_other_assets,
     "total_secured_claims": _total_secured_debts,
     "joint_filer_name": _full_name,
     "cmi": _cmi,
     "total_monthly_expenses": _total_monthly_expenses,
+    # Schedule A/B part totals, line 53, and the section questions of A/B, G and H
+    "total_vehicles": _total_vehicles,
+    "total_household_items": _total_household_items,
+    "total_financial_assets": _total_financial_assets,
+    "other_asset_descriptions": _other_asset_descriptions,
+    "has_real_property": lambda s: _yes_if_any(s.assets.filter(asset_type="real_property")),
+    "has_vehicles": lambda s: _yes_if_any(s.assets.filter(asset_type="vehicle")),
+    "has_bank_accounts": lambda s: _yes_if_any(s.assets.filter(asset_type="bank_account")),
+    "has_retirement_accounts": lambda s: _yes_if_any(
+        s.assets.filter(asset_type="retirement_account")
+    ),
+    "has_other_assets": lambda s: _yes_if_any(s.assets.filter(asset_type="other")),
+    "has_executory_contracts": lambda s: _yes_if_any(s.executory_contracts.all()),
+    "has_codebtors": lambda s: _yes_if_any(s.codebtors.all()),
     # Form 101 lines 18-20
     "creditor_count_range": _creditor_count_range,
     "total_assets_range": _total_assets_range,
PATCH
```

These are §6.2's new rules: the sums by asset type, `other_asset_descriptions` in id order, and the `has_*` rules (Q8). `total_bank_accounts` and `total_retirement_accounts` are deleted here: the schema patch below removes their only bindings, so neither has a binding after this commit.

- [ ] **Step 4: Bind Schedule A/B's questions, line 53 and totals, and unbind lines 1.2 and 16**

```bash
git apply <<'PATCH'
diff --git a/data/forms/schemas/schedule_a_b.json b/data/forms/schemas/schedule_a_b.json
index ba574fb..1b1d32d 100644
--- a/data/forms/schemas/schedule_a_b.json
+++ b/data/forms/schemas/schedule_a_b.json
@@ -4,15 +4,15 @@
   "template_version": "be67241975ab52fe8c46495a11e0ad3d565554ad8cc6879283ac17ee38cbe210",
   "fields": [
     {
-      "pdf_field": "12",
+      "pdf_field": "Debtor 1",
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "1.2",
+      "label": "Debtor 1",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "total_retirement_accounts",
+      "rule": "full_name",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -21,15 +21,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Debtor 1",
-      "type": "text",
+      "pdf_field": "Bankruptcy District Information",
+      "type": "choice",
       "source": "derived",
       "page": 1,
-      "label": "Debtor 1",
+      "label": "District Information",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "full_name",
+      "rule": "district_name",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -38,15 +38,19 @@
       "legal_review": false
     },
     {
-      "pdf_field": "16 Cash amount",
-      "type": "text",
+      "pdf_field": "Check 2",
+      "type": "checkbox",
       "source": "derived",
+      "choices": {
+        "yes": "/yes",
+        "no": "/On"
+      },
       "page": 1,
-      "label": "amount",
+      "label": "Do you own or have any legal or equitable interest in any residence, building, land, or similar property?",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "total_bank_accounts",
+      "rule": "has_real_property",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -55,15 +59,303 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Bankruptcy District Information",
-      "type": "choice",
+      "pdf_field": "undefined_13",
+      "type": "text",
       "source": "derived",
-      "page": 1,
-      "label": "District Information",
+      "page": 2,
+      "label": "Part 1 total: real estate",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "district_name",
+      "rule": "total_real_property",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "Check 3",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 2,
+      "label": "Cars, vans, trucks, tractors, sport utility vehicles, motorcycles",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "has_vehicles",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "undefined_26",
+      "type": "text",
+      "source": "derived",
+      "page": 3,
+      "label": "Part 2 total: vehicles",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_vehicles",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "15 amount",
+      "type": "text",
+      "source": "derived",
+      "page": 4,
+      "label": "Part 3 total: personal and household items",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_household_items",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "Check 17",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 5,
+      "label": "Deposits of money",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "has_bank_accounts",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "check 21",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 6,
+      "label": "Retirement or pension accounts",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "has_retirement_accounts",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "undefined_124",
+      "type": "text",
+      "source": "derived",
+      "page": 8,
+      "label": "Part 4 total: financial assets",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_financial_assets",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "check 53",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "yes": "/On",
+        "no": "/no"
+      },
+      "page": 10,
+      "label": "Do you have other property of any kind you did not already list?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "has_other_assets",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "53 Examples Season tickets country club membership",
+      "type": "text",
+      "source": "derived",
+      "page": 10,
+      "label": "Line 53 Other property: Give specific information.",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "other_asset_descriptions",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "undefined_158",
+      "type": "text",
+      "source": "derived",
+      "page": 10,
+      "label": "Part 7 total: other property",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_other_assets",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "undefined_159",
+      "type": "text",
+      "source": "derived",
+      "page": 10,
+      "label": "Part 1: Total real estate, line 2",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_real_property",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "undefined_160",
+      "type": "text",
+      "source": "derived",
+      "page": 10,
+      "label": "Part 2: Total vehicles, line 5",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_vehicles",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "undefined_161",
+      "type": "text",
+      "source": "derived",
+      "page": 10,
+      "label": "Part 3: Total personal and household items, line 15",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_household_items",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "undefined_162",
+      "type": "text",
+      "source": "derived",
+      "page": 10,
+      "label": "Part 4: Total financial assets, line 36",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_financial_assets",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "undefined_165",
+      "type": "text",
+      "source": "derived",
+      "page": 10,
+      "label": "Part 7: Total other property not listed, line 54",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_other_assets",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "undefined_166",
+      "type": "text",
+      "source": "derived",
+      "page": 10,
+      "label": "Total personal property. Add lines 56 through 61.",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_personal_property",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "undefined_167",
+      "type": "text",
+      "source": "derived",
+      "page": 10,
+      "label": "Total of all property on Schedule A/B. Add line 55 + line 62.",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_assets",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
PATCH
```

This follows Appendix A.9 row by row. Each checkbox's states are exactly the box's own export states in the field index. Line 1.2's street address and line 16's cash amount lose the retirement and bank totals they printed (B1).

- [ ] **Step 5: Leave Schedule C's description and amount boxes blank**

```bash
git apply <<'PATCH'
diff --git a/data/forms/schemas/schedule_c.json b/data/forms/schemas/schedule_c.json
index 6a693fb..dca4aae 100644
--- a/data/forms/schemas/schedule_c.json
+++ b/data/forms/schemas/schedule_c.json
@@ -37,108 +37,6 @@
       "row": null,
       "legal_review": true
     },
-    {
-      "pdf_field": "2.1",
-      "type": "text",
-      "source": "asked",
-      "page": 1,
-      "label": "Specify laws that allow exemption",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:schedule_c.desc_2.1",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": true
-    },
-    {
-      "pdf_field": "2.3",
-      "type": "text",
-      "source": "asked",
-      "page": 1,
-      "label": "Specify laws that allow exemption",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:schedule_c.amount_2.3",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": true
-    },
-    {
-      "pdf_field": "3",
-      "type": "text",
-      "source": "asked",
-      "page": 1,
-      "label": "Specify laws that allow exemption",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:schedule_c.desc_3",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": true
-    },
-    {
-      "pdf_field": "4",
-      "type": "text",
-      "source": "asked",
-      "page": 1,
-      "label": "Specify laws that allow exemption",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:schedule_c.desc_4",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": true
-    },
-    {
-      "pdf_field": "5",
-      "type": "text",
-      "source": "asked",
-      "page": 1,
-      "label": "Specify laws that allow exemption",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:schedule_c.desc_5",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": true
-    },
-    {
-      "pdf_field": "6",
-      "type": "text",
-      "source": "asked",
-      "page": 1,
-      "label": "Specify laws that allow exemption",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:schedule_c.desc_6",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": true
-    },
     {
       "pdf_field": "Bankruptcy District Information",
       "type": "choice",
PATCH
```

- [ ] **Step 6: Print the filer's name and answer line 1 on Schedules G and H**

```bash
git apply <<'PATCH'
diff --git a/data/forms/schemas/schedule_g.json b/data/forms/schemas/schedule_g.json
index feb60d0..9275e4f 100644
--- a/data/forms/schemas/schedule_g.json
+++ b/data/forms/schemas/schedule_g.json
@@ -3,6 +3,44 @@
   "template_filename": "form_b106g.pdf",
   "template_version": "61ece0c241f110549349889be12a2ff140a15a8a8b5ba825bac2a5f284849880",
   "fields": [
+    {
+      "pdf_field": "Debtor 1",
+      "type": "text",
+      "source": "derived",
+      "page": 1,
+      "label": "Debtor 1",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "full_name",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "check1",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 1,
+      "label": "Do you have any executory contracts or unexpired leases?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "has_executory_contracts",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "Bankruptcy District Information",
       "type": "choice",
diff --git a/data/forms/schemas/schedule_h.json b/data/forms/schemas/schedule_h.json
index 54f07bc..49ef334 100644
--- a/data/forms/schemas/schedule_h.json
+++ b/data/forms/schemas/schedule_h.json
@@ -3,6 +3,44 @@
   "template_filename": "form_b106h.pdf",
   "template_version": "e20d32f18c2d3f80c75079dc821372ddc1ecfc8be228ad93a636b67a0778bdb8",
   "fields": [
+    {
+      "pdf_field": "Debtor 1",
+      "type": "text",
+      "source": "derived",
+      "page": 1,
+      "label": "Debtor 1",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "full_name",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "check1",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 1,
+      "label": "Do you have any codebtors?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "has_codebtors",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "Bankruptcy District Information",
       "type": "choice",
PATCH
```

- [ ] **Step 7: Record the 22 addendum rows**

```bash
git apply <<'PATCH'
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index d8a50c6..f06b631 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -538,5 +538,225 @@
     "status": "confirmed",
     "correct_target": "undefined_53",
     "evidence": "Field index: undefined_53 p5 line 21, 'Childcare (babysitting, daycare, nursery, preschool)' (adjudicated). ExpenseInfo.childcare is the filer's childcare, the figure Schedule J line 8 prints. Step 2 spec Appendix A.6, §6.1 (expense lines, 6c option A: 122A-2 lines 19 and 21 print only above $0) and §6.4. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "Check 2",
+    "producer": "derived:has_real_property",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Check 2",
+    "evidence": "Field index: Check 2 p1 line 1, 'Do you own or have any legal or equitable interest in any residence, building, land, or similar property?'. Its 'No. Go to Part 2.' widget exports On and its 'Yes. Where is the property?' widget exports yes (both sampled_ok), so the choices are {yes: /yes, no: /On}. has_real_property is 'yes' when the filer listed a real_property asset. Owner's answer Q8 (DIG-80, DIG-69; step 2 spec §3, §6.3): the section Yes/No boxes are derived from the lists, Yes with rows and No without. Spec Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "Check 3",
+    "producer": "derived:has_vehicles",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Check 3",
+    "evidence": "Field index: Check 3 p2 line 3, 'Cars, vans, trucks, tractors, sport utility vehicles, motorcycles', options No (no) and Yes (yes), vision_agreed. has_vehicles is 'yes' when the filer listed a vehicle asset; line 4 (boats and other vehicles) stays blank, so an RV entered as a vehicle ticks line 3 (spec §10). Owner's answer Q8 (DIG-80, DIG-69; step 2 spec §3, §6.3): the section Yes/No boxes are derived from the lists, Yes with rows and No without. Spec Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "Check 17",
+    "producer": "derived:has_bank_accounts",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Check 17",
+    "evidence": "Field index: Check 17 p5 line 17, 'Deposits of money', options No (no) and Yes (yes), sampled_ok. has_bank_accounts is 'yes' when the filer listed a bank_account asset. Owner's answer Q8 (DIG-80, DIG-69; step 2 spec §3, §6.3): the section Yes/No boxes are derived from the lists, Yes with rows and No without. Spec Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "check 21",
+    "producer": "derived:has_retirement_accounts",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check 21",
+    "evidence": "Field index: check 21 p6 line 21, 'Retirement or pension accounts', options No (no) and 'Yes. List each account separately.' (yes), sampled_ok. has_retirement_accounts is 'yes' when the filer listed a retirement_account asset. Owner's answer Q8 (DIG-80, DIG-69; step 2 spec §3, §6.3): the section Yes/No boxes are derived from the lists, Yes with rows and No without. Spec Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "check 53",
+    "producer": "derived:has_other_assets",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check 53",
+    "evidence": "Field index: check 53 p10 line 53, 'Do you have other property of any kind you did not already list?'. Its No widget exports no and its 'Yes. Give specific information.' widget exports On (both sampled_ok), so the choices are {yes: /On, no: /no}. has_other_assets is 'yes' when the filer listed an 'Other Asset'. Owner's answer Q8 (DIG-80, DIG-69; step 2 spec §3, §6.3): the section Yes/No boxes are derived from the lists, Yes with rows and No without. Owner's answer Q9: 'Other Asset' prints on line 53. Spec Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "53 Examples Season tickets country club membership",
+    "producer": "derived:other_asset_descriptions",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "53 Examples Season tickets country club membership",
+    "evidence": "Field index: p10 line 53, 'Line 53 Other property: Give specific information.', tooltip 'Examples: Season tickets, country club membership' (adjudicated). other_asset_descriptions joins the 'Other' assets' descriptions with '; ' in id order, the order the filer listed them (DIG-164). Owner's answer Q9 (step 2 spec §3, §6.3, Appendix E 7); spec §6.2 and Appendix A.9. Line 53's amount boxes (undefined_155-157) stay blank until step 3. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "undefined_13",
+    "producer": "derived:total_real_property",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_13",
+    "evidence": "Field index: undefined_13 p2 line 2, 'Add the dollar value of the portion you own for all of your entries from Part 1, including any entries for pages you have attached for Part 1. Write that number here.' (vision_agreed). total_real_property sums the real_property assets' current values, the figure 106Sum line 1a copies from line 55. Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "undefined_159",
+    "producer": "derived:total_real_property",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_159",
+    "evidence": "Field index: undefined_159 p10 line 55, 'Part 1: Total real estate, line 2' (sampled_ok). Line 55 copies line 2 (undefined_13), and 106Sum line 1a copies line 55. Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "undefined_26",
+    "producer": "derived:total_vehicles",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_26",
+    "evidence": "Field index: undefined_26 p3 line 5, 'Add the dollar value of the portion you own for all of your entries from Part 2, including any entries for pages you have attached for Part 2. Write that number here' (sampled_ok). total_vehicles sums the vehicle assets' current values. Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec §6.2 and Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "undefined_160",
+    "producer": "derived:total_vehicles",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_160",
+    "evidence": "Field index: undefined_160 p10 line 56, 'Part 2: Total vehicles, line 5' (sampled_ok). Line 56 copies line 5 (undefined_26). Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "15 amount",
+    "producer": "derived:total_household_items",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "15 amount",
+    "evidence": "Field index: 15 amount p4 line 15, 'Write that number here' (sampled_ok), the Part 3 total ('Add the dollar value of all of your entries from Part 3'). total_household_items sums the personal_property assets' current values. Owner's answer Q9: personal property feeds line 15 and line 57. Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec §6.2 and Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "undefined_161",
+    "producer": "derived:total_household_items",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_161",
+    "evidence": "Field index: undefined_161 p10 line 57, 'Part 3: Total personal and household items, line 15' (sampled_ok). Line 57 copies line 15. Owner's answer Q9: personal property feeds line 15 and line 57. Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "undefined_124",
+    "producer": "derived:total_financial_assets",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_124",
+    "evidence": "Field index: undefined_124 p8 line 36, 'Write that number here', column 'Current value of the portion you own' (vision_agreed), the Part 4 total. total_financial_assets sums the bank_account (line 17) and retirement_account (line 21) assets' current values; Part 4 has sources only for lines 17 and 21, so its other lines count as zero (step 2 spec §6.1). Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec §6.2 and Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "undefined_162",
+    "producer": "derived:total_financial_assets",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_162",
+    "evidence": "Field index: undefined_162 p10 line 58, 'Part 4: Total financial assets, line 36' (sampled_ok). Line 58 copies line 36 (undefined_124). Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec §6.1 and Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "undefined_158",
+    "producer": "derived:total_other_assets",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_158",
+    "evidence": "Field index: undefined_158 p10 line 54, 'Write that number here' (sampled_ok), the Part 7 total. total_other_assets sums the 'Other' assets' current values. Owner's answer Q9: 'Other Asset' counts in the line 54 and 61 totals. Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec Appendix A.9. The audit's A/B row '17' has this key, but its verification.json correct_target is '' (missing_field), so the moved-here join can't assert this box; this row does."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "undefined_165",
+    "producer": "derived:total_other_assets",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_165",
+    "evidence": "Field index: undefined_165 p10 line 61, 'Part 7: Total other property not listed, line 54' (sampled_ok). Line 61 copies line 54 (undefined_158). Owner's answer Q9: 'Other Asset' counts in the line 54 and 61 totals. Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec Appendix A.9. The audit's A/B row '17' has this key, but its correct_target is '', so the moved-here join can't assert this box; this row does."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "undefined_166",
+    "producer": "derived:total_personal_property",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_166",
+    "evidence": "Field index: undefined_166 p10 line 62, one full name with two widgets: 'Total personal property. Add lines 56 through 61.' (sampled_ok) and 'Copy personal property total' (adjudicated); one binding fills both. total_personal_property sums every asset but real_property, which equals lines 56 + 57 + 58 + 61 because asset_type has exactly six kinds; lines 59 and 60 (business, farm) are never asked and count as zero (step 2 spec §6.1). 106Sum line 1b copies line 62. Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_a_b",
+    "pdf_field": "undefined_167",
+    "producer": "derived:total_assets",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_167",
+    "evidence": "Field index: undefined_167 p10 line 63, 'Total of all property on Schedule A/B. Add line 55 + line 62.' (sampled_ok). total_assets sums every asset, which is line 55 + line 62. 106Sum line 1c copies line 63, and Form 101 line 19 buckets it. Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec §6.1 and Appendix A.9. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_g",
+    "pdf_field": "Debtor 1",
+    "producer": "derived:full_name",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Debtor 1",
+    "evidence": "Field index: Debtor 1, 'Debtor 1 (First Name, Middle Name, Last Name)', one field with a widget on pages 1 and 2 (basis header, so not a checked basis). Step 2 spec §6.4 and Appendix A.10: G and H print the header name. The G audit's checked 'Debtor 2' row has this key, but its correct_target is 'leave blank', so the moved-here join can't assert this box; this row does."
+  },
+  {
+    "schema": "schedule_g",
+    "pdf_field": "check1",
+    "producer": "derived:has_executory_contracts",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check1",
+    "evidence": "Field index: check1 p1 line 1, 'Do you have any executory contracts or unexpired leases?' (its tooltip was copied from Schedule D). Options 'No. Check this box and file this form with the court...' (no) and 'Yes. Fill in all of the information below even if the contracts or leases are listed on Schedule A/B' (yes), sampled_ok. has_executory_contracts is 'yes' when the filer saved a contract or lease. Owner's answer Q8 (DIG-80, DIG-69; step 2 spec §3, §6.3): the section Yes/No boxes are derived from the lists, Yes with rows and No without. Spec Appendix A.10. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_h",
+    "pdf_field": "Debtor 1",
+    "producer": "derived:full_name",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Debtor 1",
+    "evidence": "Field index: Debtor 1, 'Debtor 1 (First Name, Middle Name, Last Name)', one field with a widget on pages 1 and 2 (basis header, so not a checked basis). Step 2 spec §6.4 and Appendix A.10: G and H print the header name. The H audit's 'Debtor 2' row has this key, but its correct_target is 'leave blank', so the moved-here join can't assert this box; this row does."
+  },
+  {
+    "schema": "schedule_h",
+    "pdf_field": "check1",
+    "producer": "derived:has_codebtors",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check1",
+    "evidence": "Field index: check1 p1 line 1, 'Do you have any codebtors? (If you are filing a joint case, do not list either spouse as a codebtor.)', options No (no) and Yes (yes), adjudicated. has_codebtors is 'yes' when the filer saved a codebtor. Owner's answer Q8 (DIG-80, DIG-69; step 2 spec §3, §6.3): the section Yes/No boxes are derived from the lists, Yes with rows and No without. Spec Appendix A.10. The audit has no row on this box."
   }
 ]
PATCH
```

Every box this task binds is an ADD row in Appendix A, so each gets its `step2_verification.json` row in this commit (§7.4). Each row cites the box's field-index label and basis, and the option text for a checkbox. Rows cite Q8 for the questions, Q9 for line 53 and lines 15, 57, 54 and 61, and §6.1 B5 and Ruling T0-e for the totals. There are no MOVED rows.

- [ ] **Step 8: Run the oracle against the old list and watch it fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `2 failed, 1290 passed`. test_every_listed_defect_is_a_case_the_oracle_runs names the 8 entries whose cases are gone: schedule_a_b 12 and 16 Cash amount, and schedule_c 2.1, 2.3, 3, 4, 5 and 6. The coverage tripwire, test_tier2_coverage_changes_only_on_purpose, collects 428 asserted cases against the pinned 414. There is no XPASS, and nothing else may fail.

- [ ] **Step 9: Delete the 8 entries and pin the new count**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index bda001d..2984d17 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -23,70 +23,6 @@
     "class": "wrong_box",
     "ticket": "DIG-77"
   },
-  {
-    "form_type": "schedule_a_b",
-    "pdf_field": "12",
-    "tier": "2",
-    "case": "derived:total_retirement_accounts",
-    "class": "wrong_box",
-    "ticket": "DIG-80"
-  },
-  {
-    "form_type": "schedule_a_b",
-    "pdf_field": "16 Cash amount",
-    "tier": "2",
-    "case": "derived:total_bank_accounts",
-    "class": "wrong_box",
-    "ticket": "DIG-80"
-  },
-  {
-    "form_type": "schedule_c",
-    "pdf_field": "2.1",
-    "tier": "2",
-    "case": "asked:answer:schedule_c.desc_2.1",
-    "class": "wrong_box",
-    "ticket": "DIG-81"
-  },
-  {
-    "form_type": "schedule_c",
-    "pdf_field": "2.3",
-    "tier": "2",
-    "case": "asked:answer:schedule_c.amount_2.3",
-    "class": "wrong_box",
-    "ticket": "DIG-81"
-  },
-  {
-    "form_type": "schedule_c",
-    "pdf_field": "3",
-    "tier": "2",
-    "case": "asked:answer:schedule_c.desc_3",
-    "class": "wrong_box",
-    "ticket": "DIG-81"
-  },
-  {
-    "form_type": "schedule_c",
-    "pdf_field": "4",
-    "tier": "2",
-    "case": "asked:answer:schedule_c.desc_4",
-    "class": "wrong_box",
-    "ticket": "DIG-81"
-  },
-  {
-    "form_type": "schedule_c",
-    "pdf_field": "5",
-    "tier": "2",
-    "case": "asked:answer:schedule_c.desc_5",
-    "class": "wrong_box",
-    "ticket": "DIG-81"
-  },
-  {
-    "form_type": "schedule_c",
-    "pdf_field": "6",
-    "tier": "2",
-    "case": "asked:answer:schedule_c.desc_6",
-    "class": "wrong_box",
-    "ticket": "DIG-81"
-  },
   {
     "form_type": "schedule_d",
     "pdf_field": "undefined_27",
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index 52bffc2..73ca409 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 414
+ASSERTED_CASES = 428


 def _audit_dir():
PATCH
```

The patch deletes exactly the 8 entries (64 lines) and keeps the order of the 4 that remain. Never produce this change by re-running the recorder (R3).

- [ ] **Step 10: Run the tests and the oracle again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_schedule_a_b_schema.py apps/forms/tests/test_schedule_c_schema.py apps/forms/tests/test_schedules_g_h_schema.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `21 passed`.

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `1292 passed, 1 skipped, 4 xfailed`. That is one xfail for each of the 4 entries left, and the skip is tier 1's empty checkbox parameter set (Ruling C-6).

- [ ] **Step 11: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2b.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2166 passed, 1 skipped, 5 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  358 passed (358)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

No journeys this task: it changes no page or flow, only what Schedules A/B, C, G and H print.

- [ ] **Step 12: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_schedule_a_b_schema.py \
  backend/apps/forms/tests/test_schedule_c_schema.py \
  backend/apps/forms/tests/test_schedules_g_h_schema.py \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_oracle_tier2.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/schedule_a_b.json \
  data/forms/schemas/schedule_c.json \
  data/forms/schemas/schedule_g.json \
  data/forms/schemas/schedule_h.json
git commit -F - <<'MSG'
fix(forms): Schedule A/B prints its totals and section answers, G and H the name and line 1, and Schedule C only its law

Schedules A/B, C, G and H follow the step 2 spec (Appendix A.9, A.10,
A.13; §6.1, §6.3 Q8 and Q9):

Schedule A/B:
- Lines 1, 3, 17, 21 and 53 answer Yes when the filer listed that kind
  of property and No when the list is empty (Q8), from new rules
  has_real_property, has_vehicles, has_bank_accounts,
  has_retirement_accounts and has_other_assets. Each box's states come
  from the field index; the template is irregular, so line 1's "No"
  and line 53's "Yes" export /On.
- Line 53 describes the "Other" assets, joined with "; " in the order
  the filer listed them (other_asset_descriptions orders by id: the
  model's own order follows the encrypted value, DIG-164).
- The part totals and the summary print (B5): lines 2 and 55 real
  estate, 5 and 56 vehicles (total_vehicles), 15 and 57 personal and
  household items (total_household_items), 36 and 58 deposits plus
  retirement accounts (total_financial_assets), 54 and 61 other
  property (total_other_assets, bound again), 62 total personal
  property (one binding fills both of undefined_166's widgets) and 63
  total property. Lines 59 and 60 and line 53's amounts stay blank. An
  empty list prints 0.00 (Ruling T0-e). Every total sums in Python with
  _sum_encrypted, since current_value is encrypted.
- Line 1.2's street address (12) and line 16's cash amount lose the
  retirement and bank totals they printed (B1). total_bank_accounts and
  total_retirement_accounts lose their last bindings and are deleted
  (no other caller; no test names them).

Schedule C: the six answer boxes that put descriptions and an amount in
the "Specific laws that allow exemption" column (2.1, 2.3, 3, 4, 5, 6)
lose their bindings until step 3 asks for the rows. 2.2 keeps the law.

Schedules G and H: Debtor 1 prints the filer's name on both pages, and
line 1 answers from the filer's contracts and leases
(has_executory_contracts) or codebtors (has_codebtors).

Oracle:
- step2_verification.json gains the 22 ADD rows (54 -> 76): 18 on A/B,
  2 on G, 2 on H. For A/B 54 and 61 and the G and H headers, the audit's
  rows with the same key name no box ('' or "leave blank"), so only
  these rows assert them.
- Tier 3 is unchanged: A/B, C, G and H have no rows; 106Sum 1a-1c share
  their rules with lines 55, 62 and 63, which are unchanged.

Clears 8 known-defect entries (12 -> 4), all tier 2 wrong_box by
orphan: A/B 12 and 16 Cash amount (DIG-80), Schedule C 2.1, 2.3, 3, 4, 5
and 6 (DIG-81). Before the deletion, exactly those 8 orphans and the
coverage tripwire failed.

ASSERTED_CASES 414 -> 428 (+14), measured by diffing the collected IDs:
-8 (the 8 cleared xfails), +22 (the addendum rows, all passing). Tier 1
loses the 8 deleted boxes' text cases and gains 15 text cases and 14
checkbox cases.

New tests:
- test_schedule_a_b_schema.py: each part total on its line and the
  summary; the summary adds up as the form says; 106Sum 1a-1c copy
  lines 55, 62 and 63; no property gives 0.00 totals and No on every
  question; each question answers Yes only for its own kind (household
  goods answer none); line 53 in the order listed; lines the intake
  never asks print nothing.
- test_schedule_c_schema.py: no description or amount prints where the
  form asks for a law.
- test_schedules_g_h_schema.py: the name heads both pages; line 1 says
  Yes only with a row; each schedule answers from its own list.

Refs DIG-69, DIG-80, DIG-81, DIG-164
MSG
git status --short
```

### Task 16: Print the totals and debt questions on Schedules D and E/F, and copy the totals on 106Sum 3b and 9d

_Built and verified as commit `b1f8f31` on `plan/forms-step2b`._

**Files:**

- Create: `backend/apps/forms/tests/test_schedules_d_e_f_schema.py`
- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_form_106sum_schema.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/form_106sum.json`
- Modify: `data/forms/schemas/schedule_d.json`
- Modify: `data/forms/schemas/schedule_e_f.json`

**Interfaces:**

- Consumes:
  - `_sum_encrypted(queryset, field_name)`, `_fmt(Decimal)` and `_yes_if_any(rows)` (Task 15) in `backend/apps/forms/services/derivations.py`, and the existing rule `total_secured_claims`, an alias of `_total_secured_debts` (the same function as 106Sum 2's `total_secured_debts`).
  - `DebtInfo.is_secured` (saved since 2a), `DebtInfo.debt_type` (`"student_loan"`) and `DebtInfo.is_priority`, which no production code writes.
  - Tier 2's moved-here join (Task 1): `verification.json`'s confirmed `(schedule_d, undefined_27)` row names `undefined_24` as its correct target.
  - `read_widgets` (`apps/forms/tests/pdf_readback.py`), `PDFFormFiller().fill`, `resolve` and `load_schema`.
- Produces:
  - `_total_nonpriority_unsecured` (rule `total_nonpriority_unsecured`) counts every unsecured debt: the `is_priority=False` filter is gone.
  - New rules in `DERIVATIONS`:
    - `has_secured_debts`: `"yes"` when a debt has `is_secured=True`, else `"no"`.
    - `has_nonpriority_debts`: `"yes"` when a debt has `is_secured=False`, else `"no"`.
    - `total_student_loans` (`_total_student_loans`): the sum of the unsecured debts with `debt_type="student_loan"`, formatted by `_fmt`.
    - `total_other_nonpriority` (`_total_other_nonpriority`): `total_nonpriority_unsecured` minus `total_student_loans`.
  - Schedule D (`schedule_d.json`, 3 → 4 objects): the `total_secured_claims` object moves in place from `undefined_27` to `undefined_24`, page 2, label "Line 2: grand total of Column A, Amount of claim"; `check1` ← `derived:has_secured_debts`, choices `{"yes": "/yes", "no": "/no"}`, page 1.
  - Schedule E/F (`schedule_e_f.json`, 2 → 6 objects): `check7` ← `derived:has_nonpriority_debts`, choices `{"yes": "/yes", "no": "/no"}`, page 3; `Total_6f` ← `derived:total_student_loans`, `Total_6i` ← `derived:total_other_nonpriority` and `Total_6j` ← `derived:total_nonpriority_unsecured`, all page 6.
  - 106Sum (`form_106sum.json`, 13 → 14 objects): `9d` ← `derived:total_student_loans`, page 2. `3b` keeps `derived:total_nonpriority_unsecured` and gets its new body.
  - Six addendum rows in `step2_verification.json` (76 → 82): `schedule_d` `check1` `derived:has_secured_debts`; `schedule_e_f` `check7` `derived:has_nonpriority_debts`, `Total_6f` `derived:total_student_loans`, `Total_6i` `derived:total_other_nonpriority` and `Total_6j` `derived:total_nonpriority_unsecured`; `form_106sum` `9d` `derived:total_student_loans`.
  - `ASSERTED_CASES = 434`. `known_defects.json` holds 3 entries.
  - New `backend/apps/forms/tests/test_schedules_d_e_f_schema.py` with `test_schedule_d_prints_its_secured_total_in_the_grand_total_box`, `test_line_6j_totals_every_unsecured_debt_and_6f_the_unsecured_student_loans`, `test_line_6j_adds_lines_6f_through_6i`, `test_a_secured_student_loan_never_turns_line_6i_negative`, `test_the_summary_copies_the_totals_schedules_d_and_e_f_print`, `test_each_debt_question_answers_yes_only_for_the_debts_its_schedule_lists[secured_only]` and `[unsecured_only]`, `test_a_filer_with_no_debts_gets_zero_totals_and_no_on_both_questions` and `test_lines_the_intake_never_asks_print_nothing`.
  - In `test_form_106sum_schema.py`, `test_priority_debts_print_nowhere_until_the_filer_is_asked_which_have_priority` is renamed `test_line_3a_stays_blank_until_the_filer_is_asked_which_debts_have_priority`.

**Decisions already made in this task:**

- **Q8, the owner's answer:** "the section Yes/No boxes (DIG-80, DIG-69): derived from the lists, Yes with rows and No without: A/B `Check 2`, `Check 3`, `Check 17`, `check 21`, `check 53`; D, G and H `check1`; E/F `check7`." Schedule D's `check1` answers from the secured debts and E/F's `check7` from the unsecured ones.
- **Priority is never asked (OQ-3), so every unsecured debt counts as nonpriority** (§6.1 B5): "Until priority is asked (OQ-3), the nonpriority totals count every unsecured debt and the priority totals stay blank." `total_nonpriority_unsecured` drops `is_priority=False` (§6.2), `has_nonpriority_debts` matches it, and E/F `check1` (the priority question), `Total_6a`–`Total_6e`, `Total_6g` and `Total_6h` stay unbound.
- **Ruling T16-a:** `total_student_loans` counts only unsecured student loans. E/F is the unsecured schedule, and otherwise 6i (6j − 6f) could go negative. A student loan saved as secured is on Schedule D.
- **Ruling T0-e:** a filer with no debts gets 0.00 on Schedule D's total, on 6f, 6i and 6j, and on 106Sum 9d. The filer finished the intake, and Q8 already reads an empty list as "No".
- **6i is computed as 6j − 6f** (`_total_other_nonpriority` reads the debts twice), so 6f + 6i always equals 6j, the form's own arithmetic. Lines 6g and 6h are never asked and count as zero.
- **Schedule D's total moves in place.** The existing `undefined_27` object becomes `undefined_24`, so the box keeps one binding (E006) and `total_secured_claims` never loses its last binding. Its page is 2, from the field index (the old object said 1, though `undefined_27` is on page 3). The label "Line 2: grand total of Column A, Amount of claim" is the implementer's wording; the old one was the tooltip "undefined". D's page subtotals (`undefined_9`, `undefined_23`) stay blank beside the grand total until step 3 lists the rows.
- **106Sum 3b keeps its key and gets the new body.** `test_form_106sum_schema.py`'s `test_debt_totals` now expects 3b to be 15000.00, because its fixture's IRS debt is marked `is_priority` and now counts. `test_priority_debts_print_nowhere_until_the_filer_is_asked_which_have_priority` still passed, but its name became false, so it is renamed `test_line_3a_stays_blank_until_the_filer_is_asked_which_debts_have_priority`. The five personas' tier 3 rows on 3b don't move: no seed sets `is_priority`.
- **106Sum `9d` carries `"required": true`,** unlike its sibling totals. Only `test_form_106dec_schema.py` reads `required`, so nothing prints differently. Leave it.
- **No test covers E/F `check7` for a debt that is only marked priority.** Nothing in production writes `is_priority`. This is an accepted review nit.
- **The addendum:** six ADD rows land with their bindings. Schedule D `undefined_24` is MOVED and needs no row: the moved-here join asserts it from `verification.json`'s `undefined_27` row. 106Sum 3b is KEEP.
- **Known defects:** 1 entry deleted (4 → 3), schedule_d `undefined_27`, tier 2, `derived:total_secured_claims`, `wrong_box` (DIG-69), orphaned by the move.
- **`ASSERTED_CASES` 428 → 434 (+6):** −1 for the cleared `undefined_27` xfail, +1 for `undefined_24` through the moved-here join, and +6 for the addendum rows, all passing.
- **No rule loses its last binding,** so nothing is deleted.

- [ ] **Step 1: Write the failing tests**

```python file=backend/apps/forms/tests/test_schedules_d_e_f_schema.py
"""
Schedules D and E/F: each schedule's question answers from the debts the filer listed, and
its totals print on the lines that ask for them, which 106Sum copies.

Business intent: a trustee reads Schedule D's grand total and E/F's line 6 totals against
the summary (106Sum 2, 3b and 9d copy them), and each schedule's question says whether a
list follows. DigniFi doesn't ask which debts have priority (OQ-3), and deciding it is a
legal judgment, so every unsecured debt counts as nonpriority, and E/F's priority question
and priority totals stay blank (step 2 spec §6.1 B5, Appendix A.10). Line 6f counts only
the unsecured student loans: E/F is the unsecured schedule, and 6i (6j - 6f) must never go
below zero (Ruling T16-a).
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_widgets
from apps.intake.models import DebtInfo, DebtorInfo, IncomeInfo, IntakeSession

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schemadef", password="pass")
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
        middle_name="",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    # 106Sum line 8 is CMI, which needs income entered by source.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))
    return session


def _debt(session, debt_type, amount, secured=False, priority=False):
    DebtInfo.objects.create(
        session=session,
        creditor_name=f"{debt_type} creditor",
        debt_type=debt_type,
        amount_owed=Decimal(amount),
        is_secured=secured,
        is_priority=priority,
    )


@pytest.fixture
def debts(session):
    # Each debt at its own power of two, so a total that counts the wrong debts can't match.
    _debt(session, "auto_loan", "1000", secured=True)
    _debt(session, "student_loan", "2000", secured=True)
    _debt(session, "student_loan", "4000")
    _debt(session, "credit_card", "8000")
    # Marked priority, but nobody asked the filer (OQ-3): it counts as nonpriority.
    _debt(session, "other", "16000", priority=True)
    return session


def _widgets(session, form_type):
    """The filled form's widgets, as a viewer sees them."""
    values = resolve(load_schema(form_type), session)
    return read_widgets(PDFFormFiller().fill(form_type, values))


def _printed(session, form_type):
    """Each box as a viewer sees it: a text box's value, or the states a checkbox ticks."""
    shown = {}
    for w in _widgets(session, form_type):
        if w.state is None:
            shown[w.full_name] = w.value
        elif w.state != "/Off":
            shown.setdefault(w.full_name, set()).add(w.state)
    return shown


def test_schedule_d_prints_its_secured_total_in_the_grand_total_box(debts):
    # Line 2's grand total of Column A is on page 2. The page-3 box asks on which line of
    # Part 1 a creditor was entered, and never gets a dollar amount.
    widgets = _widgets(debts, "schedule_d")

    assert [(w.page, w.value) for w in widgets if w.full_name == "undefined_24"] == [(2, "3000.00")]
    assert [w.value for w in widgets if w.full_name == "undefined_27"] == [None]


def test_line_6j_totals_every_unsecured_debt_and_6f_the_unsecured_student_loans(debts):
    shown = _printed(debts, "schedule_e_f")

    assert shown["Total_6f"] == "4000.00"  # the secured student loan is on Schedule D
    assert shown["Total_6i"] == "24000.00"  # the credit card and the debt marked priority
    assert shown["Total_6j"] == "28000.00"


def test_line_6j_adds_lines_6f_through_6i(debts):
    shown = _printed(debts, "schedule_e_f")

    # 6g and 6h are never asked and count as zero (step 2 spec §6.1).
    assert Decimal(shown["Total_6f"]) + Decimal(shown["Total_6i"]) == Decimal(shown["Total_6j"])


def test_a_secured_student_loan_never_turns_line_6i_negative(session):
    # Ruling T16-a: a student loan the filer saved as secured is on Schedule D, not 6f.
    _debt(session, "student_loan", "5000", secured=True)
    _debt(session, "credit_card", "1000")

    shown = _printed(session, "schedule_e_f")

    assert (shown["Total_6f"], shown["Total_6i"], shown["Total_6j"]) == (
        "0.00",
        "1000.00",
        "1000.00",
    )


def test_the_summary_copies_the_totals_schedules_d_and_e_f_print(debts):
    d, ef = _printed(debts, "schedule_d"), _printed(debts, "schedule_e_f")
    summary = resolve(load_schema("form_106sum"), debts)

    assert summary["2"] == d["undefined_24"]
    assert summary["3b"] == ef["Total_6j"]
    assert summary["9d"] == ef["Total_6f"]
    # Total liabilities are 2 + 3a + 3b, and 3a stays blank until priority is asked.
    assert Decimal(summary["3c"]) == Decimal(summary["2"]) + Decimal(summary["3b"])


@pytest.mark.parametrize(
    "secured,d_ticks,ef_ticks",
    [
        pytest.param(True, {"/yes"}, {"/no"}, id="secured_only"),
        pytest.param(False, {"/no"}, {"/yes"}, id="unsecured_only"),
    ],
)
def test_each_debt_question_answers_yes_only_for_the_debts_its_schedule_lists(
    session, secured, d_ticks, ef_ticks
):
    _debt(session, "auto_loan" if secured else "credit_card", "1000", secured=secured)

    assert _printed(session, "schedule_d").get("check1", set()) == d_ticks
    assert _printed(session, "schedule_e_f").get("check7", set()) == ef_ticks


def test_a_filer_with_no_debts_gets_zero_totals_and_no_on_both_questions(session):
    d, ef = _printed(session, "schedule_d"), _printed(session, "schedule_e_f")

    assert d.get("check1", set()) == {"/no"}
    assert ef.get("check7", set()) == {"/no"}
    # Ruling T0-e: the filer finished the intake with no debts listed, so the totals are 0.00.
    assert d["undefined_24"] == "0.00"
    assert (ef["Total_6f"], ef["Total_6i"], ef["Total_6j"]) == ("0.00", "0.00", "0.00")
    assert resolve(load_schema("form_106sum"), session).get("9d") == "0.00"


def test_lines_the_intake_never_asks_print_nothing(debts):
    # A debt marked priority still leaves E/F's priority question (line 1) and its
    # priority totals (6a-6e) blank (OQ-3); 6g and 6h are never asked.
    shown = _printed(debts, "schedule_e_f")

    assert "check1" not in shown
    for box in ("Total_6a", "Total_6b", "Total_6c", "Total_6d", "Total_6e", "Total_6g", "Total_6h"):
        assert shown[box] is None, box
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_form_106sum_schema.py b/backend/apps/forms/tests/test_form_106sum_schema.py
index 5642cfd..390042c 100644
--- a/backend/apps/forms/tests/test_form_106sum_schema.py
+++ b/backend/apps/forms/tests/test_form_106sum_schema.py
@@ -124,7 +124,8 @@ class TestForm106SumSchema:
     def test_debt_totals(self, populated_session):
         field_map = resolve(load_schema("form_106sum"), populated_session)
         assert field_map["2"] == "50000.00"  # secured
-        assert field_map["3b"] == "10000.00"  # nonpriority unsecured
+        # Every unsecured debt, the IRS debt marked priority too: priority isn't asked (OQ-3).
+        assert field_map["3b"] == "15000.00"

     def test_total_liabilities_print_on_3c_and_combined_monthly_income_on_line_4(
         self, populated_session
@@ -139,11 +140,12 @@ class TestForm106SumSchema:
         assert field_map["4"] == "2000.00"  # 1200 wages + 800 Social Security
         assert field_map["8"] == "1200.00"

-    def test_priority_debts_print_nowhere_until_the_filer_is_asked_which_have_priority(
+    def test_line_3a_stays_blank_until_the_filer_is_asked_which_debts_have_priority(
         self, populated_session
     ):
         # The fixture's IRS debt is marked priority, but DigniFi never asks which debts
-        # have priority (OQ-3), and deciding it is a legal judgment: line 3a stays blank.
+        # have priority (OQ-3), and deciding it is a legal judgment: line 3a stays blank,
+        # and 3b counts the debt with the other unsecured ones (step 2 spec §6.1 B5).
         field_map = resolve(load_schema("form_106sum"), populated_session)
         assert "3a" not in field_map

PATCH
```

The new file's `debts` fixture holds one debt at each power of two: a secured auto loan of 1000, a secured student loan of 2000, an unsecured student loan of 4000, a credit card of 8000, and an unsecured `other` debt of 16000 marked `is_priority`. A total that counts the wrong debts can't match: Schedule D is 3000, 6f is 4000, 6i is 24000 and 6j is 28000. The tests read the filled PDF, as a viewer sees it. `test_lines_the_intake_never_asks_print_nothing` is a guard: those boxes are unbound today and must stay unbound.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_schedules_d_e_f_schema.py apps/forms/tests/test_form_106sum_schema.py --tb=line -q -p no:cacheprovider 2>&1 | tail -24
```

Expected: FAIL — `9 failed, 12 passed`. Schedule D's grand-total box is empty (`assert [(2, None)] == [(2, '3000.00')]`), E/F's line 6 boxes are blank (`assert None == '4000.00'`), no debt question ticks a box (`assert set() == {'/no'}`), and 106Sum 3b leaves out the debt marked priority (`assert '10000.00' == '15000.00'`). The never-asked guard and the other 106Sum tests pass.

- [ ] **Step 3: Count every unsecured debt as nonpriority, and add E/F's line 6 rules and the two debt questions**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index 7d7f1a4..2ea3d9f 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -119,9 +119,16 @@ def _total_secured_debts(session: IntakeSession) -> str:


 def _total_nonpriority_unsecured(session: IntakeSession) -> str:
+    """
+    E/F line 6j and 106Sum 3b: every unsecured debt.
+
+    Which debts have priority is never asked (OQ-3), and a rule may not decide it, so
+    every unsecured debt counts as nonpriority and the priority lines stay blank
+    (step 2 spec §6.1 B5).
+    """
     from apps.intake.models import DebtInfo

-    qs = DebtInfo.objects.filter(session=session, is_secured=False, is_priority=False)
+    qs = DebtInfo.objects.filter(session=session, is_secured=False)
     return _fmt(_sum_encrypted(qs, "amount_owed"))


@@ -203,6 +210,30 @@ def _yes_if_any(rows) -> str:
     return "yes" if rows.exists() else "no"


+# ---------------------------------------------------------------------------
+# Schedule E/F line 6 totals
+# ---------------------------------------------------------------------------
+
+
+def _total_student_loans(session: IntakeSession) -> str:
+    """
+    E/F line 6f and 106Sum 9d: the unsecured student loans.
+
+    A student loan saved as secured is on Schedule D, not E/F (Ruling T16-a).
+    """
+    from apps.intake.models import DebtInfo
+
+    qs = DebtInfo.objects.filter(session=session, is_secured=False, debt_type="student_loan")
+    return _fmt(_sum_encrypted(qs, "amount_owed"))
+
+
+def _total_other_nonpriority(session: IntakeSession) -> str:
+    """E/F line 6i, 6j - 6f: lines 6g and 6h are never asked, so 6i holds the rest."""
+    return _fmt(
+        Decimal(_total_nonpriority_unsecured(session)) - Decimal(_total_student_loans(session))
+    )
+
+
 # ---------------------------------------------------------------------------
 # Form 101 lines 18-20: estimated creditors, assets and liabilities
 # ---------------------------------------------------------------------------
@@ -567,6 +598,12 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "has_other_assets": lambda s: _yes_if_any(s.assets.filter(asset_type="other")),
     "has_executory_contracts": lambda s: _yes_if_any(s.executory_contracts.all()),
     "has_codebtors": lambda s: _yes_if_any(s.codebtors.all()),
+    # Schedules D and E/F: the section questions and E/F's line 6 totals
+    "has_secured_debts": lambda s: _yes_if_any(s.debts.filter(is_secured=True)),
+    # Every unsecured debt is nonpriority until priority is asked (OQ-3), as on line 6j.
+    "has_nonpriority_debts": lambda s: _yes_if_any(s.debts.filter(is_secured=False)),
+    "total_student_loans": _total_student_loans,
+    "total_other_nonpriority": _total_other_nonpriority,
     # Form 101 lines 18-20
     "creditor_count_range": _creditor_count_range,
     "total_assets_range": _total_assets_range,
PATCH
```

§6.2: "`total_nonpriority_unsecured` drops its `is_priority=False` filter". The two `has_*` rules follow Q8, and the two new totals give 6f and 6i (6j − 6f). Each binding in the next step names a rule that exists (E007).

- [ ] **Step 4: Bind Schedules D and E/F, and 106Sum 9d**

```bash
git apply <<'PATCH'
diff --git a/data/forms/schemas/form_106sum.json b/data/forms/schemas/form_106sum.json
index a91bd4a..a67c5ae 100644
--- a/data/forms/schemas/form_106sum.json
+++ b/data/forms/schemas/form_106sum.json
@@ -230,6 +230,23 @@
       "repeat_capacity": null,
       "row": null,
       "legal_review": false
+    },
+    {
+      "pdf_field": "9d",
+      "type": "text",
+      "source": "derived",
+      "page": 2,
+      "label": "Student loans (Schedule E/F line 6f)",
+      "required": true,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_student_loans",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
     }
   ]
 }
diff --git a/data/forms/schemas/schedule_d.json b/data/forms/schemas/schedule_d.json
index 72b895b..90c03e8 100644
--- a/data/forms/schemas/schedule_d.json
+++ b/data/forms/schemas/schedule_d.json
@@ -4,11 +4,11 @@
   "template_version": "0d0a009235bf4c70d5dd89c80616712c8c681537e49f17d7473e7367d608428b",
   "fields": [
     {
-      "pdf_field": "undefined_27",
+      "pdf_field": "undefined_24",
       "type": "text",
       "source": "derived",
-      "page": 1,
-      "label": "undefined",
+      "page": 2,
+      "label": "Line 2: grand total of Column A, Amount of claim",
       "required": false,
       "conditional_on": null,
       "value": null,
@@ -37,6 +37,27 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "check1",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 1,
+      "label": "Do any creditors have claims secured by your property?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "has_secured_debts",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "Bankruptcy District Information",
       "type": "choice",
diff --git a/data/forms/schemas/schedule_e_f.json b/data/forms/schemas/schedule_e_f.json
index aed9382..07fa6fa 100644
--- a/data/forms/schemas/schedule_e_f.json
+++ b/data/forms/schemas/schedule_e_f.json
@@ -20,6 +20,78 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "check7",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 3,
+      "label": "Do any creditors have nonpriority unsecured claims against you?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "has_nonpriority_debts",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "Total_6f",
+      "type": "text",
+      "source": "derived",
+      "page": 6,
+      "label": "Line 6f: Student loans",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_student_loans",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "Total_6i",
+      "type": "text",
+      "source": "derived",
+      "page": 6,
+      "label": "Line 6i: Other nonpriority unsecured claims",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_other_nonpriority",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "Total_6j",
+      "type": "text",
+      "source": "derived",
+      "page": 6,
+      "label": "Line 6j: Total nonpriority unsecured claims (6f through 6i)",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_nonpriority_unsecured",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "Bankruptcy District Information",
       "type": "choice",
PATCH
```

Appendix A.10: Schedule D's total moves to line 2's grand total of Column A, `check1` and `check7` answer from the lists (Q8), and E/F prints 6f, 6i and 6j. Appendix A.4: 106Sum 9d copies 6f. Each checkbox's states are the box's own export states in the field index.

- [ ] **Step 5: Record the new placements, the cleared entry and the new coverage count**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index 2984d17..d39fefa 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -22,13 +22,5 @@
     "case": "asked:sofa.prior_income[].source",
     "class": "wrong_box",
     "ticket": "DIG-77"
-  },
-  {
-    "form_type": "schedule_d",
-    "pdf_field": "undefined_27",
-    "tier": "2",
-    "case": "derived:total_secured_claims",
-    "class": "wrong_box",
-    "ticket": "DIG-69"
   }
 ]
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index 73ca409..c852dd5 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 428
+ASSERTED_CASES = 434


 def _audit_dir():
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index f06b631..4e2c9b2 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -758,5 +758,65 @@
     "status": "confirmed",
     "correct_target": "check1",
     "evidence": "Field index: check1 p1 line 1, 'Do you have any codebtors? (If you are filing a joint case, do not list either spouse as a codebtor.)', options No (no) and Yes (yes), adjudicated. has_codebtors is 'yes' when the filer saved a codebtor. Owner's answer Q8 (DIG-80, DIG-69; step 2 spec §3, §6.3): the section Yes/No boxes are derived from the lists, Yes with rows and No without. Spec Appendix A.10. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_d",
+    "pdf_field": "check1",
+    "producer": "derived:has_secured_debts",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check1",
+    "evidence": "Field index: check1 p1 line 1, 'Do any creditors have claims secured by your property?', options 'No. Check this box and submit this form to the court with your other schedules. You have nothing else to report on this form.' (no) and 'Yes. Fill in all of the information below.' (yes), sampled_ok. has_secured_debts is 'yes' when the filer saved a debt marked secured (is_secured, saved since step 2a). Owner's answer Q8 (DIG-80, DIG-69; step 2 spec §3, §6.3): the section Yes/No boxes are derived from the lists, Yes with rows and No without. Spec Appendix A.10. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_e_f",
+    "pdf_field": "check7",
+    "producer": "derived:has_nonpriority_debts",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check7",
+    "evidence": "Field index: check7 p3 line 3, 'Do any creditors have nonpriority unsecured claims against you?', options 'No. You have nothing to report in this part. Submit this form to the court with your other schedules.' (no) and 'Yes' (yes), sampled_ok. has_nonpriority_debts is 'yes' when the filer saved a debt not marked secured. Until priority is asked (OQ-3), every unsecured debt counts as nonpriority and the priority lines stay blank (step 2 spec §6.1 B5). E/F check1, line 1's priority question, stays blank. Owner's answer Q8 (DIG-80, DIG-69; step 2 spec §3, §6.3): the section Yes/No boxes are derived from the lists, Yes with rows and No without. Spec Appendix A.10. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_e_f",
+    "pdf_field": "Total_6f",
+    "producer": "derived:total_student_loans",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Total_6f",
+    "evidence": "Field index: Total_6f p6 line 6f, 'Student loans', column 'Total claims from Part 2 (Total claim)', sampled_ok. total_student_loans sums the unsecured debts of type student_loan; a student loan saved as secured is on Schedule D (Ruling T16-a: E/F is the unsecured schedule, and 6i, 6j - 6f, never goes below zero). 106Sum line 9d copies it. Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec §6.2 and Appendix A.10. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_e_f",
+    "pdf_field": "Total_6i",
+    "producer": "derived:total_other_nonpriority",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Total_6i",
+    "evidence": "Field index: Total_6i p6 line 6i, 'Other. Add all other nonpriority unsecured claims. Write that amount here.', column 'Total claims from Part 2 (Total claim)', adjudicated. total_other_nonpriority is 6j - 6f: lines 6g and 6h are never asked, so every other unsecured debt is on 6i (spec Appendix E 8). Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec §6.2 and Appendix A.10. The audit has no row on this box."
+  },
+  {
+    "schema": "schedule_e_f",
+    "pdf_field": "Total_6j",
+    "producer": "derived:total_nonpriority_unsecured",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Total_6j",
+    "evidence": "Field index: Total_6j p6 line 6j, 'Total. Add lines 6f through 6i.', column 'Total claims from Part 2 (Total claim)', adjudicated. total_nonpriority_unsecured sums every unsecured debt (spec §6.2: its is_priority filter is dropped). Until priority is asked (OQ-3), every unsecured debt counts as nonpriority and the priority lines stay blank (step 2 spec §6.1 B5). 106Sum line 3b copies it. Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec Appendix A.10. The audit has no row on this box."
+  },
+  {
+    "schema": "form_106sum",
+    "pdf_field": "9d",
+    "producer": "derived:total_student_loans",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "9d",
+    "evidence": "Field index: 9d p2 line 9d, 'Student loans. (Copy line 6f.)', column 'Total claim', sampled_ok. The rule is Schedule E/F line 6f's, so both forms print one figure. total_student_loans sums the unsecured debts of type student_loan; a student loan saved as secured is on Schedule D (Ruling T16-a: E/F is the unsecured schedule, and 6i, 6j - 6f, never goes below zero). Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec §6.4 and Appendix A.4. The audit has no row on this box."
   }
 ]
PATCH
```

§7.4: each ADD row gets its addendum row in the same commit, citing the box's field-index label and, for the two questions, Q8. R3: the one entry the move orphans is deleted by hand. `ASSERTED_CASES` becomes 434.

- [ ] **Step 6: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_schedules_d_e_f_schema.py apps/forms/tests/test_form_106sum_schema.py --tb=line -q -p no:cacheprovider 2>&1 | tail -24
```

Expected: `21 passed`.

- [ ] **Step 7: Run tier 2 and the list check**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `448 passed, 3 xfailed`. The three expected failures are Form 107's Income 5a, 5b and 5c entries, which Task 17 clears. A leftover undefined_27 entry would fail the orphan test, and a wrong count would fail test_tier2_coverage_changes_only_on_purpose.

- [ ] **Step 8: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2b.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2190 passed, 1 skipped, 4 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  358 passed (358)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

This task changes no page or flow, so the journeys don't run here.

- [ ] **Step 9: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_schedules_d_e_f_schema.py \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_form_106sum_schema.py \
  backend/apps/forms/tests/test_oracle_tier2.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/form_106sum.json \
  data/forms/schemas/schedule_d.json \
  data/forms/schemas/schedule_e_f.json
git commit -F - <<'MSG'
fix(forms): Schedules D and E/F print their totals and answer their debt questions, and 106Sum copies them on 3b and 9d

Schedules D and E/F and 106Sum lines 3b and 9d follow the step 2 spec
(Appendix A.4, A.10; §6.1 B5, §6.2, §6.3 Q8):

Schedule D:
- The secured total (total_secured_claims) moves from undefined_27, the
  page-3 box that asks on which line of Part 1 a creditor was entered,
  to undefined_24, line 2's grand total of Column A on page 2. The
  object moves in place, so the box keeps one binding (E006), and its
  page is now 2.
- Line 1 answers from the filer's debts (new has_secured_debts): Yes
  when one is marked secured, No otherwise (Q8).

Schedule E/F:
- Part 2's question (check7) answers Yes when the filer listed a debt
  not marked secured (new has_nonpriority_debts). Line 1's priority
  question (check1) and lines 6a-6e stay blank.
- Line 6j prints every unsecured debt (total_nonpriority_unsecured),
  6f the unsecured student loans (new total_student_loans), and 6i the
  rest, 6j - 6f (new total_other_nonpriority); 6g and 6h are never
  asked. A student loan saved as secured is on Schedule D and never on
  6f, so 6i can't go below zero (Ruling T16-a). No debts prints 0.00
  (Ruling T0-e).
- total_nonpriority_unsecured drops its is_priority=False filter (spec
  §6.2): priority is never asked (OQ-3) and no rule may decide it, so
  every unsecured debt counts as nonpriority until it is (B5).

106Sum:
- 9d copies E/F 6f (total_student_loans).
- 3b keeps its key and gets the new body, so it copies 6j. Seeds never
  set is_priority and no production code writes it, so the five
  personas' tier 3 rows on 3b are unchanged. 3c now equals 2 + 3b, as
  the form adds them while 3a is blank.

Oracle:
- step2_verification.json gains the 6 ADD rows (76 -> 82): D check1,
  E/F check7, Total_6f, Total_6i and Total_6j, and 106Sum 9d. D's
  undefined_24 needs none: the moved-here join asserts it from
  verification.json's undefined_27 row, which names it.
- Tier 3 is unchanged: D, E/F and 106Sum 9d have no rows.

Clears 1 known-defect entry (4 -> 3): schedule_d undefined_27, tier 2
wrong_box (DIG-69), by orphan. Before the deletion, exactly that orphan
and the coverage tripwire failed.

ASSERTED_CASES 428 -> 434 (+6), measured by diffing the collected IDs:
-1 (the cleared undefined_27 xfail), +1 (undefined_24, moved here) and
+6 (the addendum rows), all passing. Tier 1 loses undefined_27's text
case and gains 5 text cases and 4 checkbox cases.

Tests:
- New test_schedules_d_e_f_schema.py: D's total prints in the grand
  total box and not in Part 2; 6j counts every unsecured debt and 6f
  the unsecured student loans; 6j = 6f + 6i; a secured student loan
  never turns 6i negative; 106Sum 2, 3b and 9d copy D and E/F, and
  3c = 2 + 3b; each question answers Yes only for its own schedule's
  debts; no debts gives 0.00 totals and No on both questions; the
  priority question and lines 6a-6e, 6g and 6h print nothing.
- test_form_106sum_schema.py, changed by this commit's rule body:
  test_debt_totals expects 3b 15000.00 (its fixture's IRS debt is
  marked priority and now counts), and
  test_priority_debts_print_nowhere_until_the_filer_is_asked_which_have_priority
  is renamed test_line_3a_stays_blank_until_the_filer_is_asked_which_debts_have_priority,
  since that debt now prints on 3b.

Refs DIG-26, DIG-69, DIG-79
MSG
git status --short
```

### Task 17: Print the filer's name on every page of Form 107, and leave lines 4-6 blank until the intake asks them

_Built and verified as commit `9e37548` on `plan/forms-step2b`._

**Files:**

- Create: `backend/apps/forms/tests/test_form_107_schema.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_coverage.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/form_107.json`

**Interfaces:**

- Consumes:
  - The rule `full_name` (`_full_name` in `derivations.py`), unchanged and shared with the header binding of the other forms.
  - The predicates `has_prior_income` and `has_creditor_payments`, which still gate 28 non-repeat boxes on Form 107 lines 4-6.
  - `SOFAReport` with its `prior_income` and `creditor_payments` rows, `FormAnswer(session, form_type, field_key, value)`, `packet(session)` from `apps.forms.registry`, and `seed_demo_data --reset --persona maria`.
  - `index_path` (`apps/forms/field_index.py`), whose rows carry each box's `line`; `field_of` and `qualified_name` from `apps/forms/services/pdf_filler.py`; `read_widgets`.
  - `verification.json`'s confirmed `(form_107, Debtor 2)` row, whose correct target is `Debtor 1`.
- Produces:
  - `form_107.json` (436 → 383 objects) has no repeat group: the 21 `prior_income` bindings (all `asked:sofa.prior_income[].source`) and the 33 `creditor_payments` bindings (18 `asked:sofa.creditor_payments[].*` and 15 `asked:answer:form_107.Creditors …`) are gone. No production schema has a repeat group from here on.
  - `Debtor 1` ← `derived:full_name`, the first object in `form_107.json`: text, page 1, label "Debtor 1". One binding fills its 12 widgets, one in the header of each page.
  - One addendum row in `step2_verification.json` (82 → 83, Appendix A.14's ADD count): `form_107` `Debtor 1` `derived:full_name`.
  - `ASSERTED_CASES = 383`. `known_defects.json` is `[]`.
  - New `backend/apps/forms/tests/test_form_107_schema.py` with `test_the_filers_name_heads_every_page`, `test_saved_sofa_rows_print_nothing_on_lines_4_to_6`, and `test_a_fourth_sofa_row_no_longer_keeps_form_107_from_printing[prior_income]` and `[creditor_payments]`.
  - `test_coverage.py::test_resolved_fields_come_from_multiple_sources`, rewritten: the boxes Maria's packet prints come from the sources `constant`, `derived` and `asked`.

**Decisions already made in this task:**

- **Both repeat groups come off** (§6.4): "both repeat groups (prior income, lines 4–5; creditor payments, line 6) come off until steps 3–4 ask the income kind and the 90-day window (DIG-167). The SOFA answers stay stored. Removing the groups ends DIG-77's overflow on a fourth row." They printed each income's description in the gross-income boxes (5a-5c) and the amount paid as the amount still owed. The SOFA models, serializer, page and journey stay as they are.
- **`has_prior_income` and `has_creditor_payments` stay.** 28 boxes on lines 4-6 still use them. Every removed binding was `asked:`, so no rule loses its last binding and nothing is deleted.
- **`Debtor 1` stays ADD, with its addendum row** (Ruling T0-b). The audit's confirmed `Debtor 2` row names `Debtor 1` as its correct target, so the moved-here join would assert it too; the addendum row is read first. One tier 2 case either way.
- **`Debtor 2` (the spouse's line), `check6a`, `check6b` and `check29` stay unbound** (Appendix A.11), and the signing block is unchanged.
- **The coverage test is rewritten because this commit breaks it.** It asked for 10 or more values on Maria's Form 107, which now resolves 2 (the district and `Debtor 1`), so it fails with "only 2 fields resolved". The SOFA was its third source, and no schema reads `sofa.` any more. The new test resolves Maria's whole packet after one test-made answer (`form_101.primarily_consumer_debts` = `yes`, which step 4 will ask) and requires `{"constant", "derived", "asked"}` among the sources of the boxes it prints. The seeds store no answer, so without it the test would prove only two kinds. Its docstring says "every kind of source" though `ingested` isn't checked; that review nit is accepted. The "4 placeholder fields" comment goes with the old body.
- **The lines 4-6 test reads the field index's `line` column directly** (through `index_path`), not the schema, so a box bound again on those lines fails it whatever the binding.
- **Left in place for later steps:** `resolve()`'s prefetch of `report.prior_income` and `report.creditor_payments` in `fill_resolver.py`, `_comparable`'s repeat-group branch in `test_api_readback.py` (Task 18 rewords its docstring), and `RepeatOverflow` with its 422. Only synthetic tests reach them now.
- **Known defects:** 3 entries deleted (3 → 0), form_107 `Income 5a Debtor 1`, `Income 5b Debtor 1` and `Income 5c Debtor 1`, tier 2, `asked:sofa.prior_income[].source`, `wrong_box` (DIG-77), orphaned when their bindings go. `known_defects.json` is now `[]`.
- **`ASSERTED_CASES` 434 → 383 (−51):** −21 `prior_income` cases (18 passing and the 3 cleared xfails), −31 `creditor_payments` cases (all passing; `Creditors Name 2` and `Creditors amount paid 2` were never asserted) and +1 for the `Debtor 1` addendum row. Tier 1 loses the 54 text cases of the removed boxes and gains `Debtor 1`'s.

- [ ] **Step 1: Write the failing tests**

```python file=backend/apps/forms/tests/test_form_107_schema.py
"""
What the Statement of Financial Affairs (Form 107) prints from the intake (step 2 spec
§6.4, Appendix A.11).

Business intent: the filer's name heads every page, so a page separated from the filing
still says whose it is. Lines 4-6 stay blank until steps 3-4 ask what each prior-income
row is and whether a payment fell in the 90 days before filing (DIG-167). Until then the
saved SOFA rows printed the income's description in the gross-income boxes and the amount
paid as the amount still owed, and a fourth row refused the whole form (DIG-77). The SOFA
answers stay stored for those steps.
"""

import json
from datetime import date
from decimal import Decimal
from io import BytesIO

import pypdf
import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.field_index import index_path
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller, field_of, qualified_name
from apps.forms.tests.pdf_readback import read_widgets
from apps.intake.models import DebtorInfo, IntakeSession, SOFAReport

User = get_user_model()


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema107", password="pass")
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
        middle_name="Q",
        last_name="Doe",
        ssn="900-12-3456",  # IRS-reserved range: synthetic
        date_of_birth=date(1990, 1, 15),
        phone="312-555-0100",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    return session


def _sofa(session, prior_income=0, creditor_payments=0):
    """The SOFA page's answers: Yes to both questions, with this many rows of each."""
    report = SOFAReport.objects.create(
        session=session, has_prior_income=True, has_creditor_payments=True
    )
    for i in range(prior_income):
        report.prior_income.create(
            year=2025 - i, source=f"Wages - Employer {i}", gross_amount=Decimal("38400.00")
        )
    for i in range(creditor_payments):
        report.creditor_payments.create(
            creditor_name=f"Creditor {i}",
            total_paid=Decimal("1020.00"),
            dates_of_payments="Monthly Jan-Mar 2026",
        )


def _fill(session):
    return PDFFormFiller().fill("form_107", resolve(load_schema("form_107"), session))


def _boxes_on_lines(*lines):
    """Every box the field index places on these lines of Form 107."""
    rows = json.loads(index_path(load_schema("form_107").template_filename).read_text())
    return {row["full_name"] for row in rows if row["line"] in lines}


def test_the_filers_name_heads_every_page(session):
    pdf = _fill(session)

    # A viewer draws each widget's own appearance stream, so every page must have one.
    pages = []
    for number, page in enumerate(pypdf.PdfReader(BytesIO(pdf)).pages, start=1):
        for annot in page.get("/Annots") or []:
            widget = annot.get_object()
            if qualified_name(field_of(widget)) != "Debtor 1":
                continue
            appearance = widget.get("/AP")
            if appearance is not None and b"Jane Q Doe" in appearance["/N"].get_data():
                pages.append(number)
    assert pages == list(range(1, 13))
    # A single filer's statement: the spouse's line stays blank.
    assert [w.value for w in read_widgets(pdf) if w.full_name == "Debtor 2"] == [None]


def test_saved_sofa_rows_print_nothing_on_lines_4_to_6(session):
    _sofa(session, prior_income=3, creditor_payments=3)

    printed = {
        w.full_name
        for w in read_widgets(_fill(session))
        if w.full_name in _boxes_on_lines("4", "5", "6")
        and (w.value not in (None, "") or w.state not in (None, "/Off"))
    }

    assert printed == set()


@pytest.mark.parametrize("kind", ["prior_income", "creditor_payments"])
def test_a_fourth_sofa_row_no_longer_keeps_form_107_from_printing(session, kind):
    # Lines 4-6 printed three rows of each, so a fourth refused the form (DIG-77).
    _sofa(session, **{kind: 4})

    assert resolve(load_schema("form_107"), session)["Debtor 1"] == "Jane Q Doe"
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_coverage.py b/backend/apps/forms/tests/test_coverage.py
index 46f4cec..575d16e 100644
--- a/backend/apps/forms/tests/test_coverage.py
+++ b/backend/apps/forms/tests/test_coverage.py
@@ -1,12 +1,13 @@
-"""Headline proof: the resolver fills every applicable form field."""
+"""Headline proof: the resolver fills a filer's forms from every kind of source they bind."""

 import pytest
 from django.core.management import call_command

 from apps.districts.models import District
+from apps.forms.registry import packet
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
-from apps.intake.models import IntakeSession
+from apps.intake.models import FormAnswer, IntakeSession


 @pytest.fixture
@@ -18,19 +19,21 @@ def ilnd_fixture(db):

 @pytest.mark.django_db
 def test_resolved_fields_come_from_multiple_sources(ilnd_fixture):
-    """Resolver pulls from derivations, SOFA, constants — not just one source."""
+    """Resolver pulls from derivations, constants and the filer's answers — not just one source."""
     call_command("seed_demo_data", "--reset", persona="maria")
     session = IntakeSession.objects.filter(user__username="demo_maria").first()
+    # The seeds store no answers, so Maria gives one, as step 4 will ask her to.
+    FormAnswer.objects.create(
+        session=session, form_type="form_101", field_key="primarily_consumer_debts", value="yes"
+    )

-    out = resolve(load_schema("form_107"), session)
-    # Hand-authored map filled ~6 fields. Schema-driven resolver
-    # fills every applicable field with available data:
-    #   - constants: chapter, debtor_type
-    #   - derivations: full_name, family_size, district_name
-    #   - SOFA: prior income rows x N, creditor payment rows x M
-    #   - signature: 4 placeholder fields
-    assert len(out) >= 10, f"only {len(out)} fields resolved"
-    # Verify we have data from multiple resolvers
-    assert any(
-        v for v in out.values() if v
-    ), "all fields are empty — resolver may not be pulling source data"
+    # The kind of source behind every box Maria's packet prints.
+    sources = set()
+    for form_type in packet(session):
+        schema = load_schema(form_type)
+        out = resolve(schema, session)
+        sources |= {f.source for f in schema.fields if out.get(f.pdf_field)}
+    #   - constants: Chapter 7, the 106Sum and 103B ticks
+    #   - derivations: name, address, district, totals, income
+    #   - answers: whether her debts are primarily consumer debts
+    assert {"constant", "derived", "asked"} <= sources
PATCH
```

The header test reads each `Debtor 1` widget's own appearance stream, because a viewer draws that, and requires "Jane Q Doe" on pages 1-12. The lines 4-6 test saves three prior-income rows and three creditor payments with Yes on both questions, and requires every box the field index places on lines 4, 5 or 6 to show no value and no tick. The fourth-row test is DIG-77's overflow. The rewritten coverage test passes before and after this commit.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_107_schema.py apps/forms/tests/test_coverage.py --tb=line -q -p no:cacheprovider 2>&1 | tail -12
```

Expected: FAIL — `4 failed, 1 passed`. Debtor 1 is unbound, so no page draws the name (`assert [] == [1, 2, 3, 4, 5, 6, ...]`); the saved rows print on lines 4-6 (`assert {'Creditors N...t owe 3', ...} == set()`); and a fourth row of either kind refuses the form (`RepeatOverflow: form_107: repeat group 'prior_income' has 4 rows but template holds 3`).

- [ ] **Step 3: Take both repeat groups off Form 107, and print the name in its header**

```bash
git apply <<'PATCH'
diff --git a/data/forms/schemas/form_107.json b/data/forms/schemas/form_107.json
index 1d05d6d..64c38eb 100644
--- a/data/forms/schemas/form_107.json
+++ b/data/forms/schemas/form_107.json
@@ -3,6 +3,23 @@
   "template_filename": "b_107_0425-form.pdf",
   "template_version": "efdcb1446328c3cca29b3c2e424c1984a4ca185f79f0f20f43e1271cbdd9ed52",
   "fields": [
+    {
+      "pdf_field": "Debtor 1",
+      "type": "text",
+      "source": "derived",
+      "page": 1,
+      "label": "Debtor 1",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "full_name",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "Bankruptcy District Information",
       "type": "choice",
@@ -278,23 +295,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Income 4a Debtor 1",
-      "type": "text",
-      "source": "asked",
-      "page": 2,
-      "label": "Gross income",
-      "required": false,
-      "conditional_on": "has_prior_income",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
-      "row": 1,
-      "legal_review": false
-    },
     {
       "pdf_field": "check4b Debtor 1",
       "type": "checkbox",
@@ -335,23 +335,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Income 4b Debtor 1",
-      "type": "text",
-      "source": "asked",
-      "page": 2,
-      "label": "Gross income",
-      "required": false,
-      "conditional_on": "has_prior_income",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
-      "row": 2,
-      "legal_review": false
-    },
     {
       "pdf_field": "check4d Debtor 1",
       "type": "checkbox",
@@ -412,23 +395,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Income 4c Debtor 1",
-      "type": "text",
-      "source": "asked",
-      "page": 2,
-      "label": "Gross income",
-      "required": false,
-      "conditional_on": "has_prior_income",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
-      "row": 3,
-      "legal_review": false
-    },
     {
       "pdf_field": "check5",
       "type": "checkbox",
@@ -450,1048 +416,300 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Income source 5a Debtor 1",
-      "type": "text",
+      "pdf_field": "check6",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Source of income",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 3,
+      "label": "Are either Debtor 1’s or Debtor 2’s debts primarily consumer debts?",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": null,
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
+      "binding": "answer:form_101.primarily_consumer_debts",
+      "repeat": null,
+      "repeat_capacity": null,
       "row": null,
-      "legal_review": false
+      "legal_review": true
     },
     {
-      "pdf_field": "Income 5a Debtor 1",
-      "type": "text",
+      "pdf_field": "check mortgage 1",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Gross income",
+      "choices": {
+        "true": "/no"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
-      "row": 1,
+      "binding": "answer:form_107.check mortgage 1",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income source 5b Debtor 1",
-      "type": "text",
+      "pdf_field": "check car 1",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Source of income",
+      "choices": {
+        "true": "/yes"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
+      "binding": "answer:form_107.check car 1",
+      "repeat": null,
+      "repeat_capacity": null,
       "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income 5b Debtor 1",
-      "type": "text",
+      "pdf_field": "check credit card 1",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Gross income",
+      "choices": {
+        "true": "/no"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
-      "row": 2,
+      "binding": "answer:form_107.check credit card 1",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income source 5c Debtor 1",
-      "type": "text",
+      "pdf_field": "check loan 1",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Source of income",
+      "choices": {
+        "true": "/yes"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
+      "binding": "answer:form_107.check loan 1",
+      "repeat": null,
+      "repeat_capacity": null,
       "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income 5c Debtor 1",
-      "type": "text",
+      "pdf_field": "check vendors 1",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Gross income",
+      "choices": {
+        "true": "/no"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
-      "row": 3,
+      "binding": "answer:form_107.check vendors 1",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income source 5d Debtor 1",
-      "type": "text",
+      "pdf_field": "check other 1",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Source of income",
+      "choices": {
+        "true": "/yes"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
+      "binding": "answer:form_107.check other 1",
+      "repeat": null,
+      "repeat_capacity": null,
       "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income 5d Debtor 1",
+      "pdf_field": "Other 1",
       "type": "text",
       "source": "asked",
-      "page": 2,
-      "label": "Gross income",
+      "page": 3,
+      "label": "Other",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
-      "row": 4,
+      "binding": "answer:form_107.Other 1",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income source 5e Debtor 1",
-      "type": "text",
+      "pdf_field": "check mortgage 2",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Source of income",
+      "choices": {
+        "true": "/no"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
+      "binding": "answer:form_107.check mortgage 2",
+      "repeat": null,
+      "repeat_capacity": null,
       "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income 5e Debtor 1",
-      "type": "text",
+      "pdf_field": "check car 2",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Gross income",
+      "choices": {
+        "true": "/yes"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
-      "row": 5,
+      "binding": "answer:form_107.check car 2",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income source 5f Debtor 1",
-      "type": "text",
+      "pdf_field": "check credit card 2",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Source of income",
+      "choices": {
+        "true": "/no"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
+      "binding": "answer:form_107.check credit card 2",
+      "repeat": null,
+      "repeat_capacity": null,
       "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income 5f Debtor 1",
-      "type": "text",
+      "pdf_field": "check loan 2",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Gross income",
+      "choices": {
+        "true": "/yes"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
+      "binding": "answer:form_107.check loan 2",
+      "repeat": null,
+      "repeat_capacity": null,
       "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income source 5g Debtor 1",
-      "type": "text",
+      "pdf_field": "check vendors 2",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Source of income",
+      "choices": {
+        "true": "/no"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
+      "binding": "answer:form_107.check vendors 2",
+      "repeat": null,
+      "repeat_capacity": null,
       "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income 5g Debtor 1",
-      "type": "text",
+      "pdf_field": "check other 2",
+      "type": "checkbox",
       "source": "asked",
-      "page": 2,
-      "label": "Gross income",
+      "choices": {
+        "true": "/yes"
+      },
+      "page": 3,
+      "label": "",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
+      "binding": "answer:form_107.check other 2",
+      "repeat": null,
+      "repeat_capacity": null,
       "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Income source 5h Debtor 1",
+      "pdf_field": "Other 2",
       "type": "text",
       "source": "asked",
-      "page": 2,
-      "label": "Source of income",
+      "page": 3,
+      "label": "Other",
       "required": false,
-      "conditional_on": "has_prior_income",
+      "conditional_on": "has_creditor_payments",
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
+      "binding": "answer:form_107.Other 2",
+      "repeat": null,
+      "repeat_capacity": null,
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Income 5h Debtor 1",
-      "type": "text",
-      "source": "asked",
-      "page": 2,
-      "label": "Gross income",
-      "required": false,
-      "conditional_on": "has_prior_income",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Income source 5i Debtor 1",
-      "type": "text",
-      "source": "asked",
-      "page": 2,
-      "label": "Source of income",
-      "required": false,
-      "conditional_on": "has_prior_income",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Income 5i Debtor 1",
-      "type": "text",
-      "source": "asked",
-      "page": 2,
-      "label": "Gross income",
-      "required": false,
-      "conditional_on": "has_prior_income",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.prior_income[].source",
-      "repeat": "prior_income",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check6",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "yes": "/yes",
-        "no": "/no"
-      },
-      "page": 3,
-      "label": "Are either Debtor 1’s or Debtor 2’s debts primarily consumer debts?",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_101.primarily_consumer_debts",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": true
-    },
-    {
-      "pdf_field": "Creditors Name 1",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Creditors Name",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].creditor_name",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 1,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors payment Date 1a",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Date",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].dates_of_payments",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors amount paid 1",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Total amount paid",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].total_paid",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 1,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors amount owe 1",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Total amount you still owe",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].total_paid",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 1,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check mortgage 1",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/no"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check mortgage 1",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors address a 1",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Street address",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors address a 1",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 1,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors payment Date 1b",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Date",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].dates_of_payments",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check car 1",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/yes"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check car 1",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check credit card 1",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/no"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check credit card 1",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors address b 1",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Street address",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors address b 1",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 1,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors payment Date 1c",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Date",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].dates_of_payments",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check loan 1",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/yes"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check loan 1",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check vendors 1",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/no"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check vendors 1",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors City 1",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "City",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors City 1",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 1,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors State 1",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "State",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors State 1",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 1,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors ZIP Code 1",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "ZIP Code",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors ZIP Code 1",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 1,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check other 1",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/yes"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check other 1",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Other 1",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Other",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Other 1",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors Name 2",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Creditors Name",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].creditor_name",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 2,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors payment Date 2a",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Date",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].dates_of_payments",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors amount paid 2",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Total amount paid",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].total_paid",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 2,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors amount owe 2",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Total amount you still owe",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].total_paid",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 2,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check mortgage 2",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/no"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check mortgage 2",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors address a 2",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Street address",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors address a 2",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 2,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors payment Date 2b",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Date",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].dates_of_payments",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check car 2",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/yes"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check car 2",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check credit card 2",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/no"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check credit card 2",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors address b 2",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Street address",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors address b 2",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 2,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors payment Date 2c",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Date",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].dates_of_payments",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check loan 2",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/yes"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check loan 2",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check vendors 2",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/no"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check vendors 2",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors City 2",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "City",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors City 2",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 2,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors State 2",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "State",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors State 2",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 2,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors ZIP Code 2",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "ZIP Code",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors ZIP Code 2",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 2,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "check other 2",
-      "type": "checkbox",
-      "source": "asked",
-      "choices": {
-        "true": "/yes"
-      },
-      "page": 3,
-      "label": "",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.check other 2",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Other 2",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Other",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Other 2",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors Name 3",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Creditors Name",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].creditor_name",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 3,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors payment Date 3a",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Date",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].dates_of_payments",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors amount paid 3",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Total amount paid",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].total_paid",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 3,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors amount owe 3",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Total amount you still owe",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].total_paid",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 3,
-      "legal_review": false
-    },
     {
       "pdf_field": "check mortgage 3",
       "type": "checkbox",
@@ -1512,23 +730,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Creditors address a 3",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Street address",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors address a 3",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 3,
-      "legal_review": false
-    },
     {
       "pdf_field": "check car 3",
       "type": "checkbox",
@@ -1549,23 +750,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Creditors payment Date 3b",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Date",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].dates_of_payments",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "check credit card 3",
       "type": "checkbox",
@@ -1586,40 +770,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Creditors address b 3",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Street address",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors address b 3",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 3,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors payment Date 3c",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "Date",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "sofa.creditor_payments[].dates_of_payments",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "check loan 3",
       "type": "checkbox",
@@ -1660,57 +810,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Creditors City 3",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "City",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors City 3",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 3,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors State 3",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "State",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors State 3",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 3,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Creditors ZIP Code 3",
-      "type": "text",
-      "source": "asked",
-      "page": 3,
-      "label": "ZIP Code",
-      "required": false,
-      "conditional_on": "has_creditor_payments",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_107.Creditors ZIP Code 3",
-      "repeat": "creditor_payments",
-      "repeat_capacity": 3,
-      "row": 3,
-      "legal_review": false
-    },
     {
       "pdf_field": "check other 3",
       "type": "checkbox",
PATCH
```

Appendix A.11: the 21 `prior_income` and 33 `creditor_payments` bindings are removed, and `Debtor 1` ← `derived:full_name` is added as the first object. The diff is long because the 54 removed objects sit between the boxes that stay.

- [ ] **Step 4: Record the header placement, the cleared entries and the new coverage count**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index d39fefa..fe51488 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -1,26 +1 @@
-[
-  {
-    "form_type": "form_107",
-    "pdf_field": "Income 5a Debtor 1",
-    "tier": "2",
-    "case": "asked:sofa.prior_income[].source",
-    "class": "wrong_box",
-    "ticket": "DIG-77"
-  },
-  {
-    "form_type": "form_107",
-    "pdf_field": "Income 5b Debtor 1",
-    "tier": "2",
-    "case": "asked:sofa.prior_income[].source",
-    "class": "wrong_box",
-    "ticket": "DIG-77"
-  },
-  {
-    "form_type": "form_107",
-    "pdf_field": "Income 5c Debtor 1",
-    "tier": "2",
-    "case": "asked:sofa.prior_income[].source",
-    "class": "wrong_box",
-    "ticket": "DIG-77"
-  }
-]
+[]
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index c852dd5..c77dbbf 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 434
+ASSERTED_CASES = 383


 def _audit_dir():
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index 4e2c9b2..25dac9f 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -818,5 +818,15 @@
     "status": "confirmed",
     "correct_target": "9d",
     "evidence": "Field index: 9d p2 line 9d, 'Student loans. (Copy line 6f.)', column 'Total claim', sampled_ok. The rule is Schedule E/F line 6f's, so both forms print one figure. total_student_loans sums the unsecured debts of type student_loan; a student loan saved as secured is on Schedule D (Ruling T16-a: E/F is the unsecured schedule, and 6i, 6j - 6f, never goes below zero). Step 2 spec §6.1 (totals before item rows, B5): the total prints once its inputs follow B2; the rows behind it arrive in step 3. An empty list prints 0.00 (Ruling T0-e). Spec §6.4 and Appendix A.4. The audit has no row on this box."
+  },
+  {
+    "schema": "form_107",
+    "pdf_field": "Debtor 1",
+    "producer": "derived:full_name",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Debtor 1",
+    "evidence": "Field index: Debtor 1, 'Debtor 1', one field with a text widget in the header of each of pages 1-12 (basis header, so not a checked basis). Step 2 spec §6.4 and Appendix A.11: the header name prints on every page. The audit's 'Debtor 2' row, confirmed in verification.json, found this key on the spouse's box and names 'Debtor 1' as its correct target, so the moved-here join would assert this box too; the row is kept per Ruling T0-b (A.14 counts it ADD). The audit has no row on this box."
   }
 ]
PATCH
```

§7.4: the `Debtor 1` ADD row lands with its binding and cites the index's header label. R3: the three entries the removal orphans are deleted by hand, which empties the list. `ASSERTED_CASES` becomes 383.

- [ ] **Step 5: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_107_schema.py apps/forms/tests/test_coverage.py --tb=line -q -p no:cacheprovider 2>&1 | tail -12
```

Expected: `5 passed`.

- [ ] **Step 6: Run tier 2 and the list check**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `400 passed`, with no expected failures left. A leftover Income 5a-5c entry would fail the orphan test, and a wrong count would fail test_tier2_coverage_changes_only_on_purpose.

- [ ] **Step 7: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2b.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2093 passed, 1 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  358 passed (358)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 8: Run the journeys twice**

The SOFA journey fills the SOFA page, then generates and downloads Form 107, so it runs the changed form end to end.

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 9: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_form_107_schema.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_coverage.py \
  backend/apps/forms/tests/test_oracle_tier2.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/form_107.json
git commit -F - <<'MSG'
fix(forms): Form 107 prints the filer's name on every page, and leaves lines 4-6 blank until the intake asks them

Form 107 follows the step 2 spec (Appendix A.11, §6.4):

- The page header Debtor 1 prints the filer's name (derived:full_name):
  one binding fills its 12 widgets, one on each page. The spouse's
  line, Debtor 2, stays blank.
- Both repeat groups come off until steps 3-4 ask what each row is and
  whether a payment fell in the 90 days before filing (DIG-167):
  prior_income (lines 4 and 5, 21 bindings) and creditor_payments
  (line 6, 33 bindings: 18 SOFA rows and 15 answers). They printed each
  income's description in the gross-income boxes (5a-5c) and the amount
  paid as the amount still owed, and a fourth row of either kind
  refused the whole form with RepeatOverflow (DIG-77). The SOFA answers
  stay stored; the SOFA models, page and journey are unchanged.
- has_prior_income and has_creditor_payments keep gating the 28 other
  boxes on lines 4-6. Every removed binding was asked:, so no rule
  loses its last binding.

Oracle:
- step2_verification.json gains the Debtor 1 ADD row (82 -> 83, A.14's
  ADD count). The audit's confirmed Debtor 2 row names Debtor 1 for
  this key, so the moved-here join would assert it too; it stays ADD
  (Ruling T0-b).
- Tier 3 has no Form 107 rows.

Clears 3 known-defect entries (3 -> 0): form_107 Income 5a, 5b and 5c
Debtor 1, tier 2 wrong_box (DIG-77), by orphan. Before the deletion,
exactly those three orphans and the coverage tripwire failed.
known_defects.json is now empty.

ASSERTED_CASES 434 -> 383 (-51), measured by diffing the collected IDs:
-21 prior_income cases (18 passing and the 3 cleared xfails), -31
creditor_payments cases (all passing; Creditors Name 2 and Creditors
amount paid 2 were never asserted) and +1 for the Debtor 1 addendum
row. Tier 1 loses the 54 text cases of the removed boxes and gains
Debtor 1's.

Tests:
- New test_form_107_schema.py: the name is drawn in the header of pages
  1-12 and Debtor 2 stays blank; saved SOFA rows print nothing on lines
  4-6; a fourth prior-income row or creditor payment no longer keeps
  the form from printing.
- test_coverage.py::test_resolved_fields_come_from_multiple_sources,
  broken by this commit: it asked for 10 or more values on Maria's
  Form 107, which now resolves 2. It now checks that the boxes Maria's
  packet prints come from constants, derivations and an answer she
  gives, not from one source. The SOFA was its third source, and no
  schema reads it now. Its count and its "4 placeholder fields" comment
  go.

Refs DIG-77, DIG-167
MSG
git status --short
```

### Task 18: Record what step 2b prints on the forms

_Built and verified as commit `048c4f9` on `plan/forms-step2b`._

**Files:**

- Modify: `CLAUDE.md`
- Modify: `backend/apps/documents/tests/test_processing_outcomes.py`
- Modify: `backend/apps/forms/tests/test_api_readback.py`
- Modify: `backend/apps/forms/tests/test_known_defects.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier1.py`
- Modify: `backend/apps/forms/tests/test_schedule_i_schema.py`
- Modify: `data/forms/field_index/README.md`

**Interfaces:**

- Consumes:
  - Tier 1's helpers in `test_oracle_tier1.py`: `_fields(form_type, kinds)`, `_text_landing(form_type)`, `get_all_form_types()`, `case_param`, `TEXT_CASES` and `BOX_CASES`; and `ORACLE_CASES` in `test_known_defects.py`.
  - The end state Tasks 1-17 leave, which the docs now describe: `known_defects.json` is `[]` (Task 17), no production schema has a repeat group (Task 17), a pay stub feeds only `paystub.employer_name` (Task 10), the Schedule I income total `schedule_i_income_total` (Task 11), the fee-waiver serializer and 103B's bindings (Task 6), `UnmappedChoice` refused as a 422 by `views._FAILURE_SENTENCES`, and the addendum `step2_verification.json` (Task 1).
- Produces:
  - `test_every_checkbox_binding_maps_its_answers_to_a_box` in `test_oracle_tier1.py`, one plain test that fails on any checkbox or radio binding with empty `choices` and names each one. It replaces the parametrized `test_checkbox_answer_is_mapped_to_a_box`, whose parameter set has been empty since Task 7. `_box_cases()` takes no parameter and `UNMAPPED_CASES` is gone; `ORACLE_CASES["1"]` is `TEXT_CASES + BOX_CASES`. pytest reports 0 skipped.
  - `_text_landing` fills each form's markers once and no longer re-checks a hidden marker alone.
  - Renamed tests: `test_schedule_i_schema.py::TestScheduleISchema::test_lines_10_and_12_print_the_income_total` (was `test_cmi_in_field_map`) and `test_processing_outcomes.py::test_pay_stub_upload_stores_its_monthly_gross_pay_and_no_debt` (was `test_pay_stub_upload_produces_monthly_income_for_schedule_i`).
  - `CLAUDE.md`: rewritten gotchas "Schemas are checked at startup", "Known form defects are strict xfails", "Document upload sits mid-wizard", "Income is stored by source" and "The fee-waiver application", and a new gotcha "Blank, not 0.00, on the forms".
  - `data/forms/field_index/README.md` lists `audit/step2_verification.json`.
  - `known_defects.json` stays `[]` and `ASSERTED_CASES` stays 383.

**Decisions already made in this task:**

- **Ruling C-6:** tier 1's `test_checkbox_answer_is_mapped_to_a_box` has had an empty parameter set since Task 7, so pytest reported it as `1 skipped`. It becomes one plain test. Emptying form_121 `Check Box1`'s choices (`{"true": "/On"}` → `{}`) makes the new test fail with `unmapped_choice: no answer value maps to a box yet: [('form_121', 'Check Box1')]`.
- **Tier 1's alone re-check is removed.** `_text_landing` re-filled a marker alone when another key's value hid it in the batch fill. Its only case, Schedule C 2.3, lost its binding in Task 15, no test exercises the branch, and 0 of the 527 text and choice markers are hidden today.
- **The `unmapped_choice` class stays.** It stays in `DEFECT_CLASSES["1"]` (`oracle.py`), and `record_known_defects.py` keeps its DIG-68 branch. Neither can match a case now that `UNMAPPED_CASES` is gone. The class name survives as the new assertion's message prefix.
- **Ruling C-11:** the upload page's pay-stub help text moved to Task 10 (spec §5.1), so this task changes no page.
- **Ruling C-12:** the new "Blank, not 0.00" gotcha names the one exception left. With no `ExpenseInfo` row, `_total_monthly_expenses` and `_schedule_j_total_expenses` give 0.00 to Schedule J 22a, 22c and 23b, 106Sum 5 and 103B line 6, and 23c prints the income less 0.00. The code is unchanged.
- **The `CLAUDE.md` statements that 2b made false are replaced:**
  - Task 6's fee-waiver gotcha: a create now requires both answers in every encoding, and 103B prints lines 2, 3 and 6.
  - The "Until 2b moves the bindings…" income sentence becomes what prints the Schedule I income total and CMI.
  - The pay-stub gotcha: a stub supplies only Schedule I's employer name. The aggregator still stores `paystub.gross`, which no form reads (DIG-176).
- **`CLAUDE.md` also gains three statements:**
  - The schemas gotcha says a map with several keys takes one of them or blank, and any other value raises `UnmappedChoice`, a 422 in plain words (`views._FAILURE_SENTENCES`).
  - The known-defects gotcha says the list has been empty since 2b, and that the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list.
  - The new "Blank, not 0.00, on the forms" gotcha covers B2, totals that count an unasked line as zero, expense lines above $0, signing lines left blank for wet ink, and the fact that no production schema has a repeat group while the engine and its 422 stay.
- **`data/forms/field_index/README.md` lists the addendum** (carried from Task 1's review). It also says the 2026-10-09 audit files aren't edited as bindings land, so some boxes they list as unbound are bound now.
- **Two tests are renamed to what they prove now; their assertions don't change.**
  - `test_lines_10_and_12_print_the_income_total` uses a wages-only fixture, so it can't tell the income total from CMI. Social Security is proven by `test_combined_monthly_income_counts_social_security_wherever_it_is_copied`. This is an accepted review nit.
  - `test_pay_stub_upload_stores_its_monthly_gross_pay_and_no_debt` keeps checking the stored `paystub.gross` and that no debt is made.
- **`_comparable`'s docstring** (`test_api_readback.py`) now says no production schema has a repeat group. Its branch stays for a group a later step binds.
- **`resolve()`'s SOFA prefetch** (`fill_resolver.py`) stays: it is engine code, and this task changes docs and tests only.
- **Root `README.md` is not touched.** It still says pay stubs aggregate income into Schedule I prefill, and this task's files don't include it.
- **Six `DERIVATIONS` keys stay unbound**, as they were before 2b: `chapter`, `debtor_type`, `joint_filer_check`, `joint_filer_name`, `means_test_disposable_income` and `schedule_i_employer_debtor1`. No rule that 2b unbound is left behind.
- **Known defects:** 0 entries deleted. The list has been `[]` since Task 17. `ASSERTED_CASES` stays 383: no binding or addendum row changes.

- [ ] **Step 1: Replace tier 1's empty parametrized check with one plain test**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_known_defects.py b/backend/apps/forms/tests/test_known_defects.py
index ded56e1..9dbae71 100644
--- a/backend/apps/forms/tests/test_known_defects.py
+++ b/backend/apps/forms/tests/test_known_defects.py
@@ -18,7 +18,7 @@ from apps.forms.tests import test_oracle_tier3 as tier3
 from apps.forms.tests.oracle import DEFECT_CLASSES, KNOWN_DEFECTS

 ORACLE_CASES = {
-    "1": tier1.TEXT_CASES + tier1.BOX_CASES + tier1.UNMAPPED_CASES,
+    "1": tier1.TEXT_CASES + tier1.BOX_CASES,
     "2": tier2.CASES,
     "3": tier3.CASES,
 }
diff --git a/backend/apps/forms/tests/test_oracle_tier1.py b/backend/apps/forms/tests/test_oracle_tier1.py
index 580047c..5f067ab 100644
--- a/backend/apps/forms/tests/test_oracle_tier1.py
+++ b/backend/apps/forms/tests/test_oracle_tier1.py
@@ -40,18 +40,11 @@ def _text_landing(form_type):
         f.pdf_field: (_first_option(form_type, f.pdf_field) if f.type == "choice" else f"Q{i:03d}")
         for i, f in enumerate(_fields(form_type, ("text", "choice")))
     }
-    filler = PDFFormFiller()
-    widgets = read_widgets(filler.fill(form_type, markers))
-    landing = {
+    widgets = read_widgets(PDFFormFiller().fill(form_type, markers))
+    return {
         name: {w.full_name for w in widgets if w.value == marker}
         for name, marker in markers.items()
     }
-    # Another key's value can hide a marker in a batch (Schedule C 2.3); re-check alone.
-    for name, found in landing.items():
-        if not found:
-            alone = read_widgets(filler.fill(form_type, {name: markers[name]}))
-            landing[name] = {w.full_name for w in alone if w.value == markers[name]}
-    return landing


 @cache
@@ -71,19 +64,15 @@ def _text_cases():
             yield case_param(form_type, f.pdf_field, TIER, "")


-def _box_cases(mapped):
+def _box_cases():
     for form_type in get_all_form_types():
         for f in _fields(form_type, ("checkbox", "radio")):
-            if mapped:
-                for key in sorted(f.choices or {}):
-                    yield case_param(form_type, f.pdf_field, TIER, key)
-            elif not f.choices:
-                yield case_param(form_type, f.pdf_field, TIER, "")
+            for key in sorted(f.choices or {}):
+                yield case_param(form_type, f.pdf_field, TIER, key)


 TEXT_CASES = list(_text_cases())
-BOX_CASES = list(_box_cases(mapped=True))
-UNMAPPED_CASES = list(_box_cases(mapped=False))
+BOX_CASES = list(_box_cases())


 @pytest.mark.parametrize("form_type,pdf_field,case", TEXT_CASES)
@@ -113,7 +102,12 @@ def test_checkbox_ticks_only_the_widgets_for_its_answer(form_type, pdf_field, ca
     assert all(w.state == "/Off" for w in own if w.state != state), "spill: another option is on"


-@pytest.mark.parametrize("form_type,pdf_field,case", UNMAPPED_CASES)
-def test_checkbox_answer_is_mapped_to_a_box(form_type, pdf_field, case):
-    field = next(f for f in load_schema(form_type).fields if f.pdf_field == pdf_field)
-    assert field.choices, "unmapped_choice: no answer value maps to a box yet"
+def test_every_checkbox_binding_maps_its_answers_to_a_box():
+    # A box bound with empty choices prints nothing, whatever the filer answers.
+    unmapped = [
+        (form_type, f.pdf_field)
+        for form_type in get_all_form_types()
+        for f in _fields(form_type, ("checkbox", "radio"))
+        if not f.choices
+    ]
+    assert unmapped == [], f"unmapped_choice: no answer value maps to a box yet: {unmapped}"
PATCH
```

Both files change in one step: `test_known_defects.py` imports `UNMAPPED_CASES`, which the first file deletes. The same patch drops `_text_landing`'s alone re-check.

- [ ] **Step 2: Run tier 1 and the list check**

Nothing can be red before the code: the guard holds on today's tree, because Task 7 mapped the last unmapped checkbox. Before Step 1's patch the same run reports one skipped test; after it, none.

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `661 passed in`, with no skipped test.

- [ ] **Step 3: Rename the two tests to what they prove now, and reword the read-back's docstring**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/documents/tests/test_processing_outcomes.py b/backend/apps/documents/tests/test_processing_outcomes.py
index f3e2ada..f9005e5 100644
--- a/backend/apps/documents/tests/test_processing_outcomes.py
+++ b/backend/apps/documents/tests/test_processing_outcomes.py
@@ -283,7 +283,7 @@ def test_a_scanned_car_loan_bill_reads_back_as_secured(filer, openai_client):
     ]


-def test_pay_stub_upload_produces_monthly_income_for_schedule_i(filer, openai_client):
+def test_pay_stub_upload_stores_its_monthly_gross_pay_and_no_debt(filer, openai_client):
     _, session = filer
     pay_stub = {
         "employer_name": "Acme Logistics",
@@ -299,7 +299,8 @@ def test_pay_stub_upload_produces_monthly_income_for_schedule_i(filer, openai_cl
     doc = scan_photo(filer, openai_client, DocumentType.PAY_STUB, reply=pay_stub)

     assert doc["ocr_result"]["status"] == "completed"
-    # Schedule I reads ingest_key "paystub.gross": 1000 / 14 days * 30.41667 = 2172.62.
+    # No form reads "paystub.gross" since step 2: Schedule I line 2 prints the wages typed on
+    # the Income step. The stub's monthly figure is still stored: 1000 / 14 days * 30.41667.
     gross = IngestedAggregate.objects.get(session=session, ingest_key="paystub.gross")
     assert gross.value == "2172.62"
     assert not DebtInfo.objects.filter(session=session).exists()
diff --git a/backend/apps/forms/tests/test_api_readback.py b/backend/apps/forms/tests/test_api_readback.py
index 0608f22..e9788cd 100644
--- a/backend/apps/forms/tests/test_api_readback.py
+++ b/backend/apps/forms/tests/test_api_readback.py
@@ -135,7 +135,8 @@ def _comparable(form_type, values):
     """
     A form's values, with each repeat group's rows in a fixed order.

-    Stored rows have no fixed order (DIG-164), so Form 107's rows compare regardless of it.
+    No production schema has a repeat group since step 2 took Form 107's off. Stored rows
+    have no fixed order (DIG-164), so a group a later step binds compares regardless of it.
     Each row keeps its own values together, so an amount that moves to another row differs.
     """
     fixed = dict(values)
diff --git a/backend/apps/forms/tests/test_schedule_i_schema.py b/backend/apps/forms/tests/test_schedule_i_schema.py
index cc1653e..e9c8344 100644
--- a/backend/apps/forms/tests/test_schedule_i_schema.py
+++ b/backend/apps/forms/tests/test_schedule_i_schema.py
@@ -120,9 +120,9 @@ class TestScheduleISchema:
         assert "Jane Doe" in field_map["Debtor 1"]
         assert "Amount 12" in field_map

-    def test_cmi_in_field_map(self, session_with_income):
+    def test_lines_10_and_12_print_the_income_total(self, session_with_income):
         field_map = resolve(load_schema("schedule_i"), session_with_income)
-        # CMI is the wages, the only source given
+        # The wages are the only source given, so the Schedule I income total is the wages
         assert field_map["Amount 12"] == "2000.00"
         assert field_map["Amount 10 Debtor 1"] == "2000.00"

PATCH
```

Since Task 11, Schedule I lines 10 and 12 print the Schedule I income total, not CMI. Since Task 10, no form reads a pay stub's `paystub.gross`. Since Task 17, Form 107 has no rows for `_comparable` to sort.

- [ ] **Step 4: Describe 2b's end state in CLAUDE.md and the field index README**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 562b1d1..04ddb3e 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -32,9 +32,10 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type`: Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source (422) or missing median data (500). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types}` in filing order, and the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
-- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: template hash, full names, widget types, export states, `/Opt` values, duplicate bindings, TBD). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box, `{}` is unmapped and prints nothing.
-- **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails today, each with its DIG ticket. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
+- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: template hash, full names, widget types, export states, `/Opt` values, duplicate bindings, TBD). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. A rule or answer feeding a map with several keys must return one of them or `""` (blank); any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
+- **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. It has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
+- **Blank, not 0.00, on the forms** — a derivation must not turn a missing input into 0.00: a line DigniFi never asks (interest, payroll deductions, priority, a spouse's column) and an income source left empty print blank, and a source typed as $0 prints 0.00. A total counts an unasked line as zero and still prints. The 13 expense amounts are stored as $0 when left empty, so an expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0, while the totals (Schedule J 22a and 22c, 106Sum line 5, 103B line 6) still print. One exception remains: with no `ExpenseInfo` row at all, those totals and Schedule J 23b print 0.00, and 23c prints the income less 0.00 (`_total_monthly_expenses`, `_schedule_j_total_expenses`). Signature lines and signing dates stay blank for wet ink (`test_signing_lines.py`). No production schema has a repeat group: Form 107's prior-income and creditor-payment rows came off until steps 3–4 ask what they need, and the SOFA answers stay stored. The engine (`repeat`, `RepeatOverflow` and its 422) stays for later steps; only synthetic tests reach it.
 - **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, and the API never returns it. `form_data` is blank; its column is dropped one release after this code is live. A filed form downloads its stored `field_values`; an unfiled one is resolved fresh on every download.
 - **Analytics auth** — `trackEvent()` must use `getAccessToken()` for Bearer header, not raw fetch.
 - **heroku.yml release** — must be one command string (not argv list). `heroku releases:output` is empty; use `heroku logs --dyno release`.
@@ -54,7 +55,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **OCR provider is config-driven** — `_get_processor()` branches on `settings.OCR_PROVIDER` (`openai` | `gemini`) and lazy-imports the provider, so a missing SDK/key surfaces at OCR time, not app boot. `OCR_MODEL` empty ⇒ the provider's own default. Don't hardcode a provider.
 - **`openai_provider.py`, never `openai.py`** — a module named `openai.py` inside `providers/` would shadow the installed `openai` package.
 - **Prod throttling lives in `production.py`, not `base.py`** — base defines only the `auth` scope (`30/minute`); production adds `DEFAULT_THROTTLE_CLASSES` with `anon: 60/minute`, `user: 120/minute`, `auth: 5/minute`. Reading base alone wrongly concludes endpoints are unthrottled — polling ~14 documents exhausts `user` fast.
-- **Document upload sits mid-wizard** — the flow is `login → /intake` step 1 → `/documents` → `/intake` steps 2–8. A scanned bill or credit report pre-fills Amounts Owed; pay stubs feed Schedule I through `IngestedAggregate`, never the Income step. `IntakeWizard.handleNext` detours when `nextStep === 2`. Nothing currently links back to `/documents` after a skip. The persona journeys pass the detour with `DocumentsPage.skip()` (`e2e/pages/documents.page.ts`) after step 1; `scanned-bill-journey` uploads with `uploadBill()` and clicks Continue.
+- **Document upload sits mid-wizard** — the flow is `login → /intake` step 1 → `/documents` → `/intake` steps 2–8. A scanned bill or credit report pre-fills Amounts Owed; a pay stub supplies only Schedule I's employer name (`IngestedAggregate` `paystub.employer_name`), never an amount and never the Income step: every income box prints what was typed on the Income step. The aggregator still stores `paystub.gross`, which no form reads (pre-fill is DIG-176). `IntakeWizard.handleNext` detours when `nextStep === 2`. Nothing currently links back to `/documents` after a skip. The persona journeys pass the detour with `DocumentsPage.skip()` (`e2e/pages/documents.page.ts`) after step 1; `scanned-bill-journey` uploads with `uploadBill()` and clicks Continue.
 - **`updateCurrentStep` is POST `/intake/sessions/{id}/update_step/`** — _not_ the PATCH that saves step data. Mocking the PATCH to assert step advancement silently captures the wrong call and passes vacuously.
 - **Upload is synchronous despite the 202** — `views.py` uses `with ThreadPoolExecutor(...)`, whose `__exit__` calls `shutdown(wait=True)`, so `{"status": "processing"}` is returned _after_ OCR completes and holds a gunicorn worker. No `Future` is retained — that's the tell.
 - **PDFs: text layer first, then up to 3 scanned pages** — `processor.py` runs `opendataloader_pdf.convert(..., format="markdown", image_output="off", include_header_footer=True)` with no hybrid arguments. Text of at least `_MIN_TEXT_LENGTH` (30) characters goes to the text prompt; otherwise `_pdf_to_page_images()` sends up to `_MAX_SCANNED_PAGES` (3) JPEG pages to vision, and a PDF with no pages fails. Without `image_output="off"` a scan's image placeholders reach the text prompt; without `include_header_footer=True` the letterhead naming the creditor is dropped.
@@ -66,8 +67,8 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **The documents API never returns `error_message` or `extracted_data`** — `_serialize_ocr` returns `status`, `failure_reason`, `confidence_scores`, `overall_confidence`, `user_validated`. `error_message` is operations-only (exception class, `finish_reason`); read it in a Django shell. The pipeline's catch-all handlers (`_run_processing`, `AggregateIngestionService.recalculate`) log only the exception's type with `logger.error`, never `logger.exception`: logs reach Sentry, and a DB error's DETAIL quotes row values (DIG-105).
 - **Scanned amounts are bounded** — `draft_debt._bounded_amount` stores a non-numeric, negative, non-finite or ≥1e10 balance as 0, and `TradelineItem.amount_owed` has `le=9999999999.99`: a wider value makes `DecimalField(12,2)` raise on every read of the session.
 - **Prompt hints are per type and shared** — `_FIELD_HINTS` in `documents/services/providers/prompts/image_extraction.py` feeds both the vision and the text prompt (`text_extraction.py` imports it). A type with no hint is asked for "all visible fields as key-value pairs" and never returns the keys its importer reads; the `CREDIT_REPORT` hint's keys must stay in step with `TradelineItem`, and `test_prompts.py` checks that they do.
-- **Income is stored by source** — `IncomeInfo` holds the Income step's ten amounts (`IncomeInfo.SOURCE_FIELDS`, `monthly_gross_wages` … `monthly_other_income`), each nullable with no default: an amount the filer never gave stays NULL, because a $0 default would pass every earlier filer's means test. The old six-month `monthly_income` is read-only and no longer written; it stays one release, and a filer who has only that total is asked on the Income step to split it. CMI is one function, `current_monthly_income` in `apps/eligibility/cmi.py`, used by the means test, the above-median calculator and the forms' `cmi` rule: the ten without Social Security (DIG-49), an empty one counting as zero once another was given, rounded to the cent half-even. With all ten empty it raises `IncomeNotSplit` ("Enter your income by source on the Income step."): a 422 from the forms views, a 400 from `calculate_means_test`. So a filer with no income at all enters $0 in one box, as the Income step's help text says, and a zero-income fixture sets one amount to 0, not all ten to null. The API's read-only `total_monthly_income` is the ten added up, Social Security included, or null. The wizard loads the ten through `hydrateAmounts` and saves `{income_info: {<the ten>}}` alone, a blank box as null, never $0 unless typed: echoing a wizard-created row's blank `marital_status` back is a 400. Until 2b moves the bindings, Schedule I line 3 prints wages and tips, and Schedule I lines 10 and 12 and Schedule J 23a print CMI, so they leave out Social Security.
-- **The fee-waiver application** — `FeeWaiverApplication.monthly_take_home_pay` (encrypted, zero or more; 103B line 2) and `receives_noncash_assistance` (`BooleanField(null=True)`; 103B line 3) have no defaults and stay empty until the filer answers. Once 2b binds line 3, an empty answer prints blank and a stored False prints a sworn "No", so never default it. `benefit_types` holds the "What kind?" answer: required with Yes, `[]` with No. A JSON create requires both answers (400 otherwise); a form-encoded create that leaves out the yes/no stores No until 2b closes it. `monthly_income`, `monthly_expenses` and `receives_public_benefits` are no longer written and stay one release. `GET /api/intake/fee-waiver/?session=<id>` reads one session's application and never creates one, since an application puts 103B in the packet; the page opens with it, so saved answers win over pre-fills, and take-home pay is never pre-filled. A PATCH can't move an application to another user's session (DIG-178). Until 2b, nothing prints the new columns, and 103B's `4 type` and `5 Type` print 0.00 from the empty old columns (DIG-78).
+- **Income is stored by source** — `IncomeInfo` holds the Income step's ten amounts (`IncomeInfo.SOURCE_FIELDS`, `monthly_gross_wages` … `monthly_other_income`), each nullable with no default: an amount the filer never gave stays NULL, because a $0 default would pass every earlier filer's means test. The old six-month `monthly_income` is read-only and no longer written; it stays one release, and a filer who has only that total is asked on the Income step to split it. CMI is one function, `current_monthly_income` in `apps/eligibility/cmi.py`, used by the means test, the above-median calculator and the forms' `cmi` rule: the ten without Social Security (DIG-49), an empty one counting as zero once another was given, rounded to the cent half-even. With all ten empty it raises `IncomeNotSplit` ("Enter your income by source on the Income step."): a 422 from the forms views, a 400 from `calculate_means_test`. So a filer with no income at all enters $0 in one box, as the Income step's help text says, and a zero-income fixture sets one amount to 0, not all ten to null. The API's read-only `total_monthly_income` is the ten added up, Social Security included, or null. The wizard loads the ten through `hydrateAmounts` and saves `{income_info: {<the ten>}}` alone, a blank box as null, never $0 unless typed: echoing a wizard-created row's blank `marital_status` back is a 400. Schedule I lines 10 and 12, 106Sum line 4 and Schedule J 23a print the Schedule I income total (`schedule_i_income_total`, all ten sources, Social Security included); CMI, without it, prints on 122A-1 lines 11 and 12b (annualized), 106Sum line 8 and 122A-2 line 1.
+- **The fee-waiver application** — `FeeWaiverApplication.monthly_take_home_pay` (encrypted, zero or more; 103B line 2) and `receives_noncash_assistance` (`BooleanField(null=True)`; 103B line 3) have no defaults and stay empty until the filer answers. Line 3 prints an empty answer blank and a stored False as a sworn "No", so never default it. `benefit_types` holds the "What kind?" answer: required with Yes, `[]` with No. A create requires both answers in every encoding, JSON or form-encoded (400 otherwise); the yes/no can't be sent empty, even in a PATCH, and kinds sent to a row with no answer are refused. `monthly_income`, `monthly_expenses` and `receives_public_benefits` are no longer written and stay one release. `GET /api/intake/fee-waiver/?session=<id>` reads one session's application and never creates one, since an application puts 103B in the packet; the page opens with it, so saved answers win over pre-fills, and take-home pay is never pre-filled. A PATCH can't move an application to another user's session (DIG-178). 103B prints take-home pay on line 2 (`undefined_2`, `undefined_4`, `undefined_6`), the answer and its kinds on line 3 (`check 3`, `3 type`, kinds only under a Yes), and Schedule J line 22c on line 6 (`undefined_7`); `4 type` and `5 Type` are unbound.
 - **Expense names are the backend's** — the Expenses step and the wizard's hydration use `EXPENSE_FIELDS` (`types/api.ts`), the 13 `ExpenseInfo` names that Schedule J, 122A-2 and the means test read; the E2E page object fills `input[name=<key>]` from the personas' canonical keys. DRF drops any other name silently: the old frontend names (`car_payment`, `food_groceries`, `other_necessary_expenses`, ...) saved as $0 until DIG-45. The API returns these amounts as decimal strings; the wizard converts them with `hydrateAmounts` when it loads the session.
 - **Upload areas decide the document type** — `DocumentUploadPage`'s `UPLOAD_AREAS` maps "Bills and statements" → `creditor_bill`, "Pay stubs" → `pay_stub`, "Credit report" → `credit_report`. The backend stores whatever type is sent (`user_declared_type`) and never classifies. Each `FileDropZone` is named `${label}: drop files here or click to upload` with its file input inside.
 - **MSW can't parse jsdom uploads with `request.formData()`** — undici rejects jsdom's `File`, so the read fails. Read multipart fields from `await request.text()`, as `sentDocumentType` in `DocumentUploadPage.test.tsx` does.
diff --git a/data/forms/field_index/README.md b/data/forms/field_index/README.md
index 8e3a01a..964661c 100644
--- a/data/forms/field_index/README.md
+++ b/data/forms/field_index/README.md
@@ -8,6 +8,8 @@ Ground truth for every fillable box on the 17 AO templates in `../pdfs/` that th
 - `audit/<schema>.audit.json`: every schema binding checked against the index. For each binding it records the field it targets, what it writes, its verdicts and the correct target.
 - `audit/<schema>.unbound.json`: boxes a complete filing needs that no binding fills.
 - `audit/verification.json`: an independent re-check of every non-correct verdict, plus a sample of correct ones. **Where it disagrees with a per-schema audit file, `verification.json` wins.** It modifies 13 verdicts and adds 18 the audit files mark correct.
+- `audit/step2_verification.json`: forms step 2's own placements, the bindings the audit never judged. Each row has `verification.json`'s shape plus `producer`, the whole binding key (`derived:phone`), and cites the box's label in the index. Tier 2 (`backend/apps/forms/tests/test_oracle_tier2.py`) reads these rows before the audit's, matching on box and binding key, and fails on a row that no binding matches.
+- The audit, unbound and verification files are the 2026-10-09 audit's record. Later steps don't edit them, so some boxes listed as unbound are bound now.
 - `audit/ocr_cross.json`: where the vision reading and the text-layer reading disagreed.
 - `tools/`: the scripts that built the index (`form_ocr.py`, `ocr_crosscheck.py`, `field_index.py`).

PATCH
```

`CLAUDE.md` now says what step 2b prints and what it leaves blank. The README names the addendum that tier 2 reads first.

- [ ] **Step 5: Check the edits**

This step checks two things. The pre-commit prettier hook must not rewrite the two Markdown files, which the gates' `format:check` (`frontend/src` only) doesn't cover. And the renamed tests must still pass.

```bash
set -eo pipefail
frontend/node_modules/.bin/prettier --check CLAUDE.md data/forms/field_index/README.md
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_schedule_i_schema.py::TestScheduleISchema::test_lines_10_and_12_print_the_income_total apps/documents/tests/test_processing_outcomes.py::test_pay_stub_upload_stores_its_monthly_gross_pay_and_no_debt -q -p no:cacheprovider 2>&1 | tail -3
```

Expected: `All matched files use Prettier code style!`, then `2 passed`.

- [ ] **Step 6: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step2b.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2094 passed, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  358 passed (358)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

The one expected failure is the marker in `apps/intake/tests/test_integration_flow.py`, outside the list, and no test is skipped.

- [ ] **Step 7: Run the journeys twice**

This task changes no page, but it leaves 2b's final tree, so the journeys run on it.

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`.

- [ ] **Step 8: Commit**

```bash
set -eo pipefail
git add \
  CLAUDE.md \
  backend/apps/documents/tests/test_processing_outcomes.py \
  backend/apps/forms/tests/test_api_readback.py \
  backend/apps/forms/tests/test_known_defects.py \
  backend/apps/forms/tests/test_oracle_tier1.py \
  backend/apps/forms/tests/test_schedule_i_schema.py \
  data/forms/field_index/README.md
git commit -F - <<'MSG'
docs(forms): record what step 2b prints on the forms

Step 2b's end state, written down where agents and contributors read it:

- CLAUDE.md:
  - A pay stub supplies only Schedule I's employer name.
  - Schedule I 10 and 12, 106Sum 4 and Schedule J 23a print the Schedule
    I income total, and CMI prints on 122A-1 11 and 12b, 106Sum 8 and
    122A-2 1. This replaces the "until 2b" sentence.
  - The fee-waiver gotcha now says what 103B prints and that the
    yes/no is required in every encoding. This replaces the two "until
    2b" sentences.
  - known_defects.json is empty.
  - A multi-key choices map takes one of its keys or blank, and tier 1
    fails on {}.
  - A new gotcha covers blank versus 0.00, signing lines, and the fact
    that no production schema has a repeat group (the engine and its
    422 stay). It names the one exception left: with no ExpenseInfo
    row, the expense totals and Schedule J 23b print 0.00.
- data/forms/field_index/README.md lists audit/step2_verification.json.
  It also says the 2026-10-09 audit files aren't updated as bindings
  land.

Oracle:
- Tier 1's unmapped-choice check had an empty parameter set since
  1ade6b3, so pytest reported it as 1 skipped. It is now one plain
  test, test_every_checkbox_binding_maps_its_answers_to_a_box: no
  checkbox or radio binding in any schema has empty choices. With
  form_121 Check Box1 emptied, it fails and names the box.
  test_known_defects.py's tier 1 cases drop the empty list. The suite
  now reports 0 skipped.
- Tier 1's re-check of a marker hidden in a batch fill is gone. Its
  only case, Schedule C 2.3, lost its binding in 857c181, and 0 of the
  527 text and choice markers are hidden today.
- No DERIVATIONS rule that 2b unbound is left. The 6 keys no schema
  binds (chapter, debtor_type, joint_filer_check, joint_filer_name,
  means_test_disposable_income, schedule_i_employer_debtor1) were
  unbound before 2b.

Clears 0 known-defect entries: known_defects.json has been [] since
6544c6a, and this commit lists none. ASSERTED_CASES 383 -> 383: no
tier 2 case changes.

Tests:
- Renamed to what they prove now:
  - test_schedule_i_schema.py test_cmi_in_field_map ->
    test_lines_10_and_12_print_the_income_total.
  - test_processing_outcomes.py
    test_pay_stub_upload_produces_monthly_income_for_schedule_i ->
    test_pay_stub_upload_stores_its_monthly_gross_pay_and_no_debt.
    Its comment no longer says Schedule I reads paystub.gross.
- test_api_readback.py: _comparable's docstring no longer says Form 107
  has rows.

Refs DIG-161, DIG-176, DIG-68
MSG
git status --short
```
