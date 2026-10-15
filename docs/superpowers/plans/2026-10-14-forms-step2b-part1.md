# Forms Step 2b (Bindings) Implementation Plan, Part 1 of 2

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put what the filer gave in the box that asks for it, leave a box blank where the filer gave nothing, and clear all 142 known defects. Step 1 checked every binding against the field index, and 2a made the data arrive intact. 2b moves the bindings.

**Architecture:** 2b changes the form schemas in `data/forms/schemas/`, the rules in `backend/apps/forms/services/derivations.py`, and the oracle's records: the tier 2 addendum `data/forms/field_index/audit/step2_verification.json`, tier 3's expectations and `backend/apps/forms/tests/known_defects.json`. Two other changes ride along. Task 6 makes the fee-waiver serializer keep only a non-cash answer the filer gave, before 103B prints it (DIG-193). Task 2 makes the Claude review check fail when the review posts nothing (DIG-144). Each of the 18 tasks is one commit, and every task boundary passes every gate.

**This part:** Tasks 1–9. It starts with nothing of 2b on this branch. The other parts: Part 2 (`docs/superpowers/plans/2026-10-14-forms-step2b-part2.md`, Tasks 10–18). The plan is split only to stay under the repository's 500 KB file limit. Run all parts as one execution: one ledger for Tasks 1–18, and the whole-branch final review only after Task 18, because each part's patches expect each file exactly as the earlier tasks leave it.

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

Check the baseline before Task 1:

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

Expected: `1785 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  357 passed (357)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

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

### Task 1: Read step 2's own placements in tier 2, and let tier 3 expect a blank box

_Built and verified as commit `f620a49` on `plan/forms-step2b`._

**Files:**

- Create: `data/forms/field_index/audit/step2_verification.json`
- Modify: `CLAUDE.md`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier3.py`
- Modify: `data/forms/field_index/tools/record_known_defects.py`

**Interfaces:**

- Consumes:
  - 2a's tier 2 in `backend/apps/forms/tests/test_oracle_tier2.py`: `_audit`, `_verification`, `_renamed`, `_audit_key`, `_binding_key`, `_checked`, `_expected_target`, the test helper `_field`, and `ASSERTED_CASES = 425`, with the audit rows and `verification.json` in `data/forms/field_index/audit/`.
  - Tier 3 in `backend/apps/forms/tests/test_oracle_tier3.py`: `EXPECTED`, `_printed` and `read_widgets`.
  - The recorder's `ticket_for` in `data/forms/field_index/tools/record_known_defects.py`, which imports tier 2's `_audit`.
- Produces:
  - `data/forms/field_index/audit/step2_verification.json`, the addendum, as `[]`. Every later row has `verification.json`'s shape (`schema`, `pdf_field`, `original_verdicts`, `final_verdicts`, `status`, `correct_target`, `evidence`) plus `producer`, the whole binding key exactly as `_binding_key` builds it (`derived:phone`, `constant:yes`, `asked:answer:form_101.mailing_zip`).
  - In tier 2:
    - `_audit(form_type)` returns box → list of every audit row on it.
    - `_addendum()` returns (schema, box, producer) → addendum row.
    - `_checked(form_type, old, row)` takes the row it judges.
    - `_wanted(pdf_field, target, verdicts)` turns a checked row into the box it wants.
    - `_expected_target` reads the addendum first, then the exact (box, key) audit row, then moved-here.
  - Tier 2 tests: `test_every_step2_placement_matches_a_binding`, the orphan check every later addendum row must pass; `test_an_unchecked_audit_row_on_the_box_is_never_overruled_by_a_moved_here_row`; `test_a_step2_placement_is_asserted_beside_the_audit_row_under_the_old_key`; and `test_an_audit_row_spelled_loosely_joins_the_binding_it_names`, parametrized as `source,producer,producer_field` with six cases.
  - Tier 3: an expected `""` means the box shows nothing, and `EXPECTED` gains Schedule I `Amount 8b Debtor 1` and Schedule J `18` as `""` for all five personas.
  - `ASSERTED_CASES` stays 425. `known_defects.json` is unchanged, with 142 entries.
  - `ticket_for` reads the tickets from every audit row on the box.
  - A `CLAUDE.md` gotcha, "A new placement needs its addendum row in the same commit".

**Decisions already made in this task:**

- **The addendum's `producer` is the whole binding key** (Ruling C-1), spelled as `_binding_key` builds it and compared as written, with no `_audit_key` normalization. The spec's row shape has no `source` column, so (schema, box, whole key) is the only join.
- **Tier 2 reads the addendum first,** on the schema's own box name and before the constant exclusion, so a constant that step 2 places (Task 3's `constant:yes` on Form 101 `Check Box20`) can be asserted. Next comes the exact (box, key) audit join, and then moved-here.
- **An exact (box, key) audit row that nobody checked leaves the box unasserted** (`""`) and never falls through to moved-here (DIG-217, M1-1). No real audit row is in that state today, so the test uses synthetic boxes X and Y, which have no widgets in the index.
- **`_audit` keeps every row on a box,** so a box can carry its audit row under the old key next to an addendum row under the new one. No audit file has two rows on one box today.
- **No result changes:** tier 2 asserts 425 cases, 344 pass and 81 xfail, before and after. Task 1 owns no Appendix A row, so it deletes 0 known-defect entries.
- **Tier 3's `_printed` gives every box in the filled forms an entry,** so a blank expectation on a name that is no box fails with "no box named …", and an empty `/V` counts as showing nothing. The implementer proved the blank branch by mutation: Maria's Schedule I `Amount 5a Debtor 1` expected as `""` failed with "wrong_value: prints ['0.00'], expected blank".
- **The two Appendix D rows that pass at the start land here,** for all five personas. Both boxes are unbound today. No existing `EXPECTED` row holds 0.00 (rows with a zero were left out), so the new rule asserts nothing else.
- **The recorder edit is Ruling C-10.** `ticket_for` is `_audit`'s only other reader. Without the edit, recording any tier 2 failure crashes with an `AttributeError` on the list (a pytest INTERNALERROR). The recorder's other crash, `item.callspec` on a failing test that isn't parametrized, predates 2b; leave it.
- **The `CLAUDE.md` gotcha states the general rule:** a binding moved onto the box an audit row names needs no row. Ruling T0-b still gives Form 101 `Debtor1.ZIP Code_2` (Task 3) and Form 107 `Debtor 1` (Task 17) addendum rows.
- **Left as they are:**

  - `_addendum()` has no guard against two rows with the same (schema, box, producer).
  - No test pins that the addendum wins over an audit row with the same (box, key), or that `_audit` keeps two rows on one box. No planned row reaches either path.
  - `_verification()` stays keyed on (schema, box).
  - `data/forms/field_index/README.md` gains its addendum line in Task 18.

- [ ] **Step 1: Pin tier 2's result before the change**

Nothing can be red here. The tests and the code they test are the oracle's own harness, so they share two files, and this task's acceptance is that no result changes. This step records tier 2's result before the change, and Step 6 checks it is the same after.

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier2.py -k test_binding_targets_the_box_the_audit_verified -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `344 passed`, and `81 xfailed`.

- [ ] **Step 2: Read the addendum in tier 2**

```json file=data/forms/field_index/audit/step2_verification.json
[]
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index a353b7a..54221b5 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -10,10 +10,17 @@ an index basis of adjudicated or sampled_ok on the row's own box. With no row
 for its box and key, a binding that a checked row with its key places on this
 box was moved here, and passes; a constant never was. Everything else is
 unverified and not asserted.
+
+Step 2's own placements, which the audit never judged, are rows in
+step2_verification.json (step 2 spec §7.4): verification.json's row shape plus
+`producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`).
+Each counts as checked, joins on (box, key) before the audit does, and must
+match a binding.
 """

 import json
 import re
+import sys
 from functools import cache

 import pytest
@@ -42,8 +49,18 @@ def _verification():

 @cache
 def _audit(form_type):
-    rows = json.loads((_audit_dir() / f"{form_type}.audit.json").read_text())
-    return {r["pdf_field"]: r for r in rows}
+    """Box → every audit row on it, so a box keeps a row under each key it was judged with."""
+    rows = {}
+    for r in json.loads((_audit_dir() / f"{form_type}.audit.json").read_text()):
+        rows.setdefault(r["pdf_field"], []).append(r)
+    return rows
+
+
+@cache
+def _addendum():
+    """(schema, box, binding key) → step 2's own placement of that binding (step 2 spec §7.4)."""
+    rows = json.loads((_audit_dir() / "step2_verification.json").read_text())
+    return {(r["schema"], r["pdf_field"], r["producer"]): r for r in rows}


 @cache
@@ -67,13 +84,12 @@ def _audit_key(row):
     return f"{row['source']}:{'' if producer == row['source'] else producer}"


-def _checked(form_type, old):
-    """(target, verdicts) of the audit row on box `old`, or None if nobody checked it."""
+def _checked(form_type, old, row):
+    """(target, verdicts) of audit row `row` on box `old`, or None if nobody checked it."""
     verified = _verification().get((form_type, old))
     if verified:
         target, verdicts = verified["correct_target"], verified["final_verdicts"]
     else:
-        row = _audit(form_type)[old]
         box = _renamed(form_type).get(old, old)
         widgets = load_index(load_schema(form_type).template_filename).get(box, ())
         if not {w.basis for w in widgets} & CHECKED_BASES:
@@ -83,29 +99,38 @@ def _checked(form_type, old):
     return re.sub(r"\s*\(.*\)$", "", target or ""), verdicts


+def _wanted(pdf_field, target, verdicts):
+    """The box a checked row wants the binding on pdf_field in, or None for "not this box"."""
+    if not target:
+        # Right box when the row found no box fault; a wrong box with no recorded target.
+        return None if "wrong_box" in verdicts else pdf_field
+    return target
+
+
 def _expected_target(form_type, binding):
     """The full name the audit wants, LEAVE_BLANK, None for "not this box", or "" if unasserted."""
     pdf_field, key = binding.pdf_field, _binding_key(binding)
+    added = _addendum().get((form_type, pdf_field, key))
+    if added is not None:
+        # Step 2's own placement, checked against the box's index label.
+        return _wanted(pdf_field, added["correct_target"], added["final_verdicts"])
     old = {new: old for old, new in _renamed(form_type).items()}.get(pdf_field, pdf_field)
-    row = _audit(form_type).get(old)
-    if row is not None and _audit_key(row) == key:
-        checked = _checked(form_type, old)
+    row = next((r for r in _audit(form_type).get(old, []) if _audit_key(r) == key), None)
+    if row is not None:
+        checked = _checked(form_type, old, row)
         if checked is None:
             return ""
-        target, verdicts = checked
-        if not target:
-            # Right box when the audit found no box fault; a wrong box with no recorded target.
-            return None if "wrong_box" in verdicts else pdf_field
-        return target
+        return _wanted(pdf_field, *checked)
     # Moved here. A constant is excluded: a /Yes the audit placed for one question
     # proves nothing about another.
     if binding.source != "constant":
-        for other, other_row in _audit(form_type).items():
-            if _audit_key(other_row) != key:
-                continue
-            checked = _checked(form_type, other)
-            if checked and checked[0] == pdf_field:
-                return pdf_field
+        for other, other_rows in _audit(form_type).items():
+            for other_row in other_rows:
+                if _audit_key(other_row) != key:
+                    continue
+                checked = _checked(form_type, other, other_row)
+                if checked and checked[0] == pdf_field:
+                    return pdf_field
     return ""


@@ -183,12 +208,84 @@ def test_a_constant_the_audit_placed_elsewhere_proves_nothing_here():


 @pytest.mark.parametrize(
-    "producer,rule",
+    "source,producer,producer_field",
     [
-        ("rule district_name", "district_name"),  # Form 107
-        ("rule:full_name (conditional_on has_joint_filer)", "full_name"),  # Schedules G-J
+        ("derived", "rule district_name", {"rule": "district_name"}),  # Form 107
+        (
+            "derived",
+            "rule:full_name (conditional_on has_joint_filer)",
+            {"rule": "full_name"},
+        ),  # Schedules G-J
+        (
+            "asked",
+            "binding:answer:schedule_c.statute_2.2",
+            {"binding": "answer:schedule_c.statute_2.2"},
+        ),  # Schedule C
+        (
+            "ingested",
+            "ingest_key:paystub.employer_name",
+            {"ingest_key": "paystub.employer_name"},
+        ),  # Schedule I
+        ("signature", "signature", {}),  # Form 101: a signature line has no producer
+        ("presume", "presume", {}),  # Form 106Dec
     ],
 )
-def test_an_audit_row_spelled_loosely_joins_the_binding_it_names(producer, rule):
-    row = {"source": "derived", "producer": producer}
-    assert _audit_key(row) == _binding_key(_field(rule=rule))
+def test_an_audit_row_spelled_loosely_joins_the_binding_it_names(source, producer, producer_field):
+    row = {"source": source, "producer": producer}
+    assert _audit_key(row) == _binding_key(_field(source=source, **producer_field))
+
+
+def test_an_unchecked_audit_row_on_the_box_is_never_overruled_by_a_moved_here_row(monkeypatch):
+    # Nobody checked box X's own row against the page image, so X stays unasserted,
+    # although a checked row on Y names X as the right box for the same producer.
+    # X and Y have no widgets in the index, so only verification.json can check them.
+    def row(box, verdicts, target):
+        return {
+            "pdf_field": box,
+            "source": "derived",
+            "producer": "rule:r",
+            "verdicts": verdicts,
+            "correct_target": target,
+        }
+
+    audit = {"X": [row("X", ["correct"], "X")], "Y": [row("Y", ["wrong_box"], "X")]}
+    verified = {("schedule_j", "Y"): {"correct_target": "X", "final_verdicts": ["wrong_box"]}}
+    monkeypatch.setattr(sys.modules[__name__], "_audit", lambda form_type: audit)
+    monkeypatch.setattr(sys.modules[__name__], "_verification", lambda: verified)
+    assert _expected_target("schedule_j", _field(pdf_field="X", rule="r")) == ""
+
+
+def test_a_step2_placement_is_asserted_beside_the_audit_row_under_the_old_key(monkeypatch):
+    # 2b puts the Schedule I income total on 106Sum line 4. The audit's checked row
+    # there judged the old total_debts binding, which belongs on 3c.
+    added = {
+        "schema": "form_106sum",
+        "pdf_field": "4",
+        "producer": "derived:schedule_i_income_total",
+        "original_verdicts": [],
+        "final_verdicts": ["correct"],
+        "status": "confirmed",
+        "correct_target": "4",
+        "evidence": "",
+    }
+    monkeypatch.setattr(
+        sys.modules[__name__],
+        "_addendum",
+        lambda: {(added["schema"], added["pdf_field"], added["producer"]): added},
+    )
+    new = _field(pdf_field="4", rule="schedule_i_income_total")
+    old = _field(pdf_field="4", rule="total_debts")
+    assert _expected_target("form_106sum", new) == "4"
+    assert _expected_target("form_106sum", old) == "3c"
+
+
+def test_every_step2_placement_matches_a_binding():
+    # A row lands with its binding (step 2 spec §7.4). A row no binding matches asserts
+    # nothing: its binding was moved, re-ruled or never written.
+    bound = {
+        (form_type, f.pdf_field, _binding_key(f))
+        for form_type in get_all_form_types()
+        for f in load_schema(form_type).fields
+    }
+    orphans = sorted(set(_addendum()) - bound)
+    assert orphans == [], f"step2_verification.json rows no binding matches: {orphans}"
PATCH
```

Tier 2 reads `step2_verification.json` as checked exact rows (§7.4), keeps every audit row on a box, and asserts an addendum row before the audit join. The patch adds the orphan test that fails on an addendum row no binding matches, the unchecked-row test for DIG-217, a test that a box keeps its old audit verdict next to a new addendum row (106Sum `4`, which Task 11 re-rules), and four loose-spelling cases (M1-2) for the §7.2 normalizations `binding:`, `ingest_key:` and a producer equal to its source (`signature`, `presume`).

- [ ] **Step 3: Let tier 3 expect a blank box**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_oracle_tier3.py b/backend/apps/forms/tests/test_oracle_tier3.py
index bffed1b..8dfcecf 100644
--- a/backend/apps/forms/tests/test_oracle_tier3.py
+++ b/backend/apps/forms/tests/test_oracle_tier3.py
@@ -5,8 +5,9 @@ Expected values are worked out by hand from each persona's data (the seed, which
 matches docs/testing/persona-briefs/ except Priya's stale income line), never
 from the app's derivations. Boxes are named from the verified field index, not
 from the schema, so a value bound to the wrong line fails here. Money compares
-as a number, so "3,200.00" equals "3200.00". A box expected to hold zero is not
-asserted: step 2 decides where blank replaces 0.00.
+as a number, so "3,200.00" equals "3200.00". An expected "" means the box shows
+nothing (step 2 spec §7.5): a line DigniFi never asks prints blank, and so does
+an expense at $0, but an income source typed as $0 prints 0.00.
 """

 from decimal import Decimal, InvalidOperation
@@ -59,8 +60,9 @@ EXPECTED = {
             "13C": "110712.00",
             "14a": BELOW_MEDIAN,
         },
-        "schedule_i": {"Amount 12": "3200.00"},
+        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "3200.00"},
         "schedule_j": {
+            "18": "",
             "22a": "2560.00",
             "22c": "2560.00",
             "23a": "3200.00",
@@ -87,8 +89,9 @@ EXPECTED = {
             "13C": "71304.00",
             "14a": BELOW_MEDIAN,
         },
-        "schedule_i": {"Amount 12": "5833.00"},
+        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "5833.00"},
         "schedule_j": {
+            "18": "",
             "22a": "3110.00",
             "22c": "3110.00",
             "23a": "5833.00",
@@ -114,8 +117,9 @@ EXPECTED = {
             "13C": "134366.00",
             "14a": ABOVE_MEDIAN,
         },
-        "schedule_i": {"Amount 12": "12000.00"},
+        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "12000.00"},
         "schedule_j": {
+            "18": "",
             "22a": "6640.00",
             "22c": "6640.00",
             "23a": "12000.00",
@@ -143,8 +147,9 @@ EXPECTED = {
             "13C": "91526.00",
             "14a": BELOW_MEDIAN,
         },
-        "schedule_i": {"Amount 12": "3500.00"},
+        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "3500.00"},
         "schedule_j": {
+            "18": "",
             "22a": "2295.00",
             "22c": "2295.00",
             "23a": "3500.00",
@@ -168,8 +173,9 @@ EXPECTED = {
             "13C": "71304.00",
             "14a": BELOW_MEDIAN,
         },
-        "schedule_i": {"Amount 12": "2000.00"},
+        "schedule_i": {"Amount 8b Debtor 1": "", "Amount 12": "2000.00"},
         "schedule_j": {
+            "18": "",
             "22a": "1280.00",
             "22c": "1280.00",
             "23a": "2000.00",
@@ -196,7 +202,9 @@ def _printed(persona):
     (form_type, full name) → what the persona's filled forms show there.

     A box shows its tick, the /AS of each widget that isn't /Off, and never its /V
-    (spec §6). A text box has no /AS, and shows its /V.
+    (spec §6). A text box has no /AS, and shows its /V unless that is empty. Every
+    box in the filled forms has an entry, so an expected blank can't pass on a
+    name that is no box.
     """
     if not District.objects.filter(code="ilnd").exists():
         call_command("loaddata", "ilnd_2025_data", verbosity=0)
@@ -206,14 +214,15 @@ def _printed(persona):
     for form_type in EXPECTED[persona]:
         values = build_field_values(form_type, session)
         for w in read_widgets(PDFFormFiller().fill(form_type, values)):
+            shows = printed.setdefault((form_type, w.full_name), set())
             if w.state is None:
                 shown = w.value
             elif w.state != "/Off":
                 shown = w.state
             else:
                 continue
-            if shown is not None:
-                printed.setdefault((form_type, w.full_name), set()).add(shown)
+            if shown:
+                shows.add(shown)
     return printed


@@ -227,8 +236,12 @@ def _amount(text):
 @pytest.mark.django_db
 @pytest.mark.parametrize("form_type,pdf_field,case,expected", CASES)
 def test_persona_packet_prints_the_right_figure(form_type, pdf_field, case, expected):
-    shown = _printed(case).get((form_type, pdf_field), set())
-    if expected.startswith("/"):  # a box: this tick and no other
+    printed = _printed(case)
+    shown = printed.get((form_type, pdf_field), set())
+    if expected == "":  # the box shows nothing
+        assert (form_type, pdf_field) in printed, f"no box named {pdf_field!r} on {form_type}"
+        assert shown == set(), f"wrong_value: prints {sorted(shown)}, expected blank"
+    elif expected.startswith("/"):  # a box: this tick and no other
         assert shown == {expected}, f"wrong_value: ticks {sorted(shown)}, expected {expected}"
     elif _amount(expected) is not None:
         assert {_amount(s) for s in shown} == {
PATCH
```

An expected `""` now means the box shows nothing (§7.5): a line DigniFi never asks prints blank, an expense at $0 prints blank, and an income source typed as $0 prints 0.00. The docstring states that rule in place of "a box expected to hold zero is not asserted", and `EXPECTED` gains Appendix D's blank Schedule I `Amount 8b Debtor 1` and Schedule J `18` for every persona.

- [ ] **Step 4: Make the recorder read every audit row on a box**

```bash
git apply <<'PATCH'
diff --git a/data/forms/field_index/tools/record_known_defects.py b/data/forms/field_index/tools/record_known_defects.py
index 5b8e49d..154474e 100644
--- a/data/forms/field_index/tools/record_known_defects.py
+++ b/data/forms/field_index/tools/record_known_defects.py
@@ -53,7 +53,8 @@ def ticket_for(tier, defect_class, form_type, pdf_field):
         from apps.forms.tests.test_oracle_tier2 import _audit, _renamed

         old = {new: old for old, new in _renamed(form_type).items()}.get(pdf_field, pdf_field)
-        cited = re.findall(r"DIG-\d+", _audit(form_type).get(old, {}).get("known") or "")
+        rows = _audit(form_type).get(old, [])
+        cited = re.findall(r"DIG-\d+", " ".join(r.get("known") or "" for r in rows))
         open_tickets = [t for t in cited if t not in CLOSED]
         if open_tickets:
             return open_tickets[0]
PATCH
```

`_audit` now returns a list per box, so `ticket_for` joins the `known` text of every row on the box before it looks for a DIG ticket.

- [ ] **Step 5: Add the addendum gotcha to CLAUDE.md**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 9213a81..562b1d1 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -34,6 +34,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type`: Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source (422) or missing median data (500). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types}` in filing order, and the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
 - **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: template hash, full names, widget types, export states, `/Opt` values, duplicate bindings, TBD). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box, `{}` is unmapped and prints nothing.
 - **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails today, each with its DIG ticket. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
+- **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
 - **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, and the API never returns it. `form_data` is blank; its column is dropped one release after this code is live. A filed form downloads its stored `field_values`; an unfiled one is resolved fresh on every download.
 - **Analytics auth** — `trackEvent()` must use `getAccessToken()` for Bearer header, not raw fetch.
 - **heroku.yml release** — must be one command string (not argv list). `heroku releases:output` is empty; use `heroku logs --dyno release`.
PATCH
```

- [ ] **Step 6: Check that tier 2's result didn't change**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier2.py -k test_binding_targets_the_box_the_audit_verified -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `344 passed`, and `81 xfailed`, the same as Step 1.

- [ ] **Step 7: Run tier 2, tier 3 and the list check**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `440 passed, 138 xfailed`. The 10 new tier 3 blank cases, the 4 new loose-spelling cases and the 3 new tier 2 tests pass, and every listed defect in these tiers still fails as expected.

- [ ] **Step 8: Check that the recorder still names a tier 2 box's own ticket**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -c '
import sys
import django

django.setup()
sys.path.insert(0, "../data/forms/field_index/tools")
from record_known_defects import ticket_for

print("ticket:", ticket_for("2", "wrong_box", "schedule_i", "Amount 3 Debtor 1"))'
```

Expected: `ticket: DIG-56`. The audit row on that box cites DIG-56, where Schedule I's fallback ticket would be DIG-82, so the recorder read the box's rows from the list.

- [ ] **Step 9: Run every gate**

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

Expected: `1802 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  357 passed (357)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

This task changes no page and no flow, so the journeys don't run here.

- [ ] **Step 10: Commit**

```bash
set -eo pipefail
git add \
  data/forms/field_index/audit/step2_verification.json \
  CLAUDE.md \
  backend/apps/forms/tests/test_oracle_tier2.py \
  backend/apps/forms/tests/test_oracle_tier3.py \
  data/forms/field_index/tools/record_known_defects.py
git commit -F - <<'MSG'
test(forms): read step 2's own placements in tier 2, and let tier 3 expect a blank box

Tier 2 now reads data/forms/field_index/audit/step2_verification.json (new,
empty). Its rows have verification.json's shape plus `producer`, spelled as
the whole binding key (`derived:phone`, `constant:yes`). They count as checked
rows, join on (box, binding key) before the audit does, and
test_every_step2_placement_matches_a_binding fails on a row that no binding
matches (step 2 spec §7.4). `_audit` keeps every row on a box, so a box keeps
its audit row under the old key next to a step 2 row under the new one.
record_known_defects.py, the other reader of `_audit`, now reads the
tickets from every row on the box.

New tier 2 tests pin two things. An unchecked audit row on a box leaves the
box unasserted and never falls through to moved-here (DIG-217). Audit rows
spelled `binding:` or `ingest_key:`, or with their source as their producer
(signature, presume), join the binding they name.

In tier 3, an expected "" now means the box shows nothing (§7.5): an empty /V
counts as showing nothing, and a blank expectation on a name that is no box
fails. The docstring states §7.5's rule in place of "a box expected to hold
zero is not asserted". This adds Appendix D's blank rows on Schedule I
`Amount 8b Debtor 1` and Schedule J `18` for all five personas. Both boxes
are unbound today. No existing EXPECTED row held 0.00.

CLAUDE.md gains the addendum gotcha.

Clears 0 known-defect entries; known_defects.json is unchanged.
ASSERTED_CASES stays at 425 (344 pass, 81 xfail). The addendum is empty, and
no audit file has two rows on one box, so no tier 2 case changes.

Refs DIG-217
MSG
git status --short
```

### Task 2: Fail the review check when no summary was posted, and show the refused calls

_Built and verified as commit `a2f7bfb` on `plan/forms-step2b`._

**Files:**

- Modify: `.github/workflows/claude-code-review.yml`

**Interfaces:**

- Consumes:
  - The review job in `.github/workflows/claude-code-review.yml`: its triggers, its `concurrency` group with `cancel-in-progress: true`, its permissions (`issues: read` among them), the checkout step, and the step `claude-review`, which runs `anthropics/claude-code-action@756cc22e19660d20e8cc9496b4f242475a7f7790` (v1.0.235).
  - That action's `execution_file` output: the path of a JSON array of the run's SDK messages. Its last `type == "result"` message carries `num_turns`, `total_cost_usd` and `permission_denials`, each denial `{tool_name, tool_use_id, tool_input}`. The output can be empty when the run fails.
  - `github.token`, `gh` and `jq` on the runner.
- Produces:
  - A step "Record when the review started", which writes `REVIEW_STARTED_AT` (UTC, `%Y-%m-%dT%H:%M:%SZ`) to `$GITHUB_ENV`.
  - A step "Show the review's turns, cost and refused calls", which prints `Turns: …`, `Cost (USD): …`, `Refused calls: N` and one `- <tool_name>: <input, at most 200 characters>` line per refused call.
  - A step "Check the review posted its summary", which fails with `::error::The review posted no "## Claude review" summary on this PR.` unless a PR comment starting with `## Claude review` has an `updated_at` at or after `REVIEW_STARTED_AT`.
  - The prompt's summary contract: the first line is exactly `## Claude review`, the summary ends with "Reviewed N of M changed files", and it is written to `review-summary.md` with the Write tool and posted with `gh pr comment <number> --body-file review-summary.md` (or `--edit-last --body-file review-summary.md`), even when the review can't finish.
  - `Write` added to `--allowed-tools`. No form, rule or test changes: `ASSERTED_CASES` stays 425, and `known_defects.json` keeps 142 entries.

**Decisions already made in this task:**

- **No red test step, and the 2b pull request can't prove the fix** (Ruling T2-a). The task changes YAML only, and no workflow linter is installed here. On a pull request that changes this workflow, the action refuses to run and reports success. #17's run logged "Workflow validation failed. The workflow file must exist and have identical content to the version on the repository's default branch." On the 2b pull request, the new check therefore turns `claude-review` red with the error "The review posted no `## Claude review` summary on this PR." That is true, since no review ran, but it isn't DIG-144: say so in the pull request's description. The first pull request after 2b merges is the proof.
- **Both new steps run under `if: ${{ !cancelled() }}`, not `always()`** (Ruling C-2). A run that a newer push cancels would otherwise log a false "no summary" error.
- **jq reads a missing `permission_denials` as `[]`** (C-2). The action's own sanitizer treats the field as optional. Without `// []`, jq exits 5 on "Cannot iterate over null" and turns the job red even when the summary was posted.
- **The summary's first line must be exactly `## Claude review`** (C-2), because the check matches `startswith("## Claude review")`.
- **The reviewer writes the summary with the Write tool and posts it with `--body-file`** (C-2). The allowed tools refuse `$(...)`, heredocs, pipes and `&&`, so a comment built with any of them is refused and never posted, which is the likely cause of the silent runs on PR #18 and PR #19. `Write` is the one tool added. Triggers, concurrency, permissions, the checkout and the action pin are unchanged.
- **The check reads `updated_at` alone.** It equals `created_at` on a new comment and moves on `--edit-last`, so it covers both. It counts any comment that starts with the heading, whoever wrote it.
- **`: "${REVIEW_STARTED_AT:?...}"` fails loudly when the start time was never recorded,** because gojq treats a null start as earlier than every string and the check would pass falsely. Its message has no apostrophe: one broke bash parsing.
- **`gh api` writes into a variable, with no pipeline,** so a `gh` failure fails the step with `gh`'s own error and not the misleading `::error::` line.
- **The report step takes the path through `env:`** and never interpolates it into `run:`. It prints nothing from the execution file except the turn count, the cost and each refused call, because the file holds every model message. Each refused call's line starts with `- `, so no input can pass as a workflow command.
- Clears 0 known-defect entries; `ASSERTED_CASES` stays at 425.

- [ ] **Step 1: Change the review workflow**

```bash
git apply <<'PATCH'
diff --git a/.github/workflows/claude-code-review.yml b/.github/workflows/claude-code-review.yml
index b5f307f..d91a63b 100644
--- a/.github/workflows/claude-code-review.yml
+++ b/.github/workflows/claude-code-review.yml
@@ -27,6 +27,11 @@ jobs:
           # so `git diff HEAD^1 HEAD` is exactly what the PR changes.
           fetch-depth: 2

+      - name: Record when the review started
+        # The last step looks for a summary posted or edited after this time. Same format as
+        # the API's created_at and updated_at, so the two compare as strings.
+        run: echo "REVIEW_STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$GITHUB_ENV"
+
       - name: Run Claude Code Review
         id: claude-review
         # Pinned by commit: @v1 moves with every release.
@@ -66,12 +71,60 @@ jobs:
             (confirmed: true). Start it with **Blocking**, **Should fix** or **Nit**, say what goes
             wrong and when, and suggest a fix.

-            Then post one summary with `gh pr comment`, under the heading "## Claude review".
-            List blocking findings first, end with "Reviewed N of N changed files", and name any
-            file you skipped. Leave out praise and anything that is fine. If your most recent
-            comment on this PR is an earlier summary under that heading, replace it with
-            `gh pr comment <number> --edit-last` instead of adding another.
+            Then post one summary. Its first line must be exactly `## Claude review`. List
+            blocking findings first, end with "Reviewed N of M changed files", and name any file
+            you skipped. Leave out praise and anything that is fine. Write the summary to
+            review-summary.md with the Write tool, then post it with
+            `gh pr comment <number> --body-file review-summary.md`. If your most recent comment on
+            this PR is an earlier summary, replace it with
+            `gh pr comment <number> --edit-last --body-file review-summary.md` instead.
+            Run each command on its own: the allowed tools refuse `$(...)`, heredocs, pipes and
+            `&&`, so a comment built with any of them is never posted.
+
+            Post the summary even when you can't finish the review: list what you found so far
+            and name every file you didn't reach. Never end without posting it.

           # See https://github.com/anthropics/claude-code-action/blob/main/docs/usage.md
           # or https://code.claude.com/docs/en/cli-reference for available options
-          claude_args: '--allowed-tools "Read,Grep,Glob,Bash(git diff:*),Bash(git log:*),Bash(gh issue view:*),Bash(gh search:*),Bash(gh issue list:*),Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*),Bash(gh pr list:*),mcp__github_inline_comment__create_inline_comment"'
+          claude_args: '--allowed-tools "Read,Grep,Glob,Write,Bash(git diff:*),Bash(git log:*),Bash(gh issue view:*),Bash(gh search:*),Bash(gh issue list:*),Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*),Bash(gh pr list:*),mcp__github_inline_comment__create_inline_comment"'
+
+      - name: Show the review's turns, cost and refused calls
+        # The execution file holds every message the model wrote, so print only the turn count,
+        # the cost and each call the allowed tools refused, its input cut to 200 characters.
+        # Each refused call's line starts with "- ", so no input can pass as a workflow command.
+        if: ${{ !cancelled() }}
+        env:
+          EXECUTION_FILE: ${{ steps.claude-review.outputs.execution_file }}
+        run: |
+          if [ ! -f "$EXECUTION_FILE" ]; then
+            echo "The review left no execution file."
+            exit 0
+          fi
+          jq -r '
+            [.[] | select(.type == "result")] | last
+            | if . == null then "The review ended without a result."
+              else
+                "Turns: \(.num_turns)",
+                "Cost (USD): \(.total_cost_usd)",
+                "Refused calls: \((.permission_denials // []) | length)",
+                ((.permission_denials // [])[] | "- \(.tool_name): \(.tool_input | tostring | .[0:200])")
+              end
+          ' "$EXECUTION_FILE"
+
+      - name: Check the review posted its summary
+        # A green run once posted nothing at all (DIG-144). Fail unless a comment under
+        # "## Claude review" was posted, or an earlier one edited, since the review started.
+        # updated_at equals created_at on a new comment and moves on an edit, so it covers both.
+        if: ${{ !cancelled() }}
+        env:
+          GH_TOKEN: ${{ github.token }}
+          PR_NUMBER: ${{ github.event.pull_request.number }}
+        run: |
+          : "${REVIEW_STARTED_AT:?the start time was never recorded}"
+          posted=$(gh api --paginate "repos/$GITHUB_REPOSITORY/issues/$PR_NUMBER/comments" \
+            --jq '.[] | select((.body | startswith("## Claude review")) and .updated_at >= env.REVIEW_STARTED_AT) | .id')
+          if [ -z "$posted" ]; then
+            echo "::error::The review posted no \"## Claude review\" summary on this PR."
+            exit 1
+          fi
+          echo "Summary posted or updated since $REVIEW_STARTED_AT."
PATCH
```

DIG-144: a review run could finish green and post nothing. The job now records when it started, shows what the allowed tools refused, and fails unless a summary was posted or edited since the start. The prompt asks for the summary even when the review can't finish, naming the files it didn't reach.

- [ ] **Step 2: Check that the workflow parses and changes only what it should**

Nothing can be red: this task changes one workflow file, which no test reads (Ruling T2-a). This step parses the new file and the one at `HEAD`, and checks that the triggers, concurrency, permissions, checkout and action pin are unchanged, that the allowed tools gain only `Write`, and that the new steps sit where they should.

```bash
set -eo pipefail
source .claude/forms-step2b.env
$PY - <<'PY'
import subprocess

import yaml

PATH = ".github/workflows/claude-code-review.yml"
new = yaml.safe_load(open(PATH))
old = yaml.safe_load(
    subprocess.run(["git", "show", f"HEAD:{PATH}"], capture_output=True, text=True, check=True).stdout
)
# PyYAML reads the `on:` key as True.
assert new[True] == old[True], "triggers changed"
assert new["concurrency"] == old["concurrency"], "concurrency changed"
job, old_job = new["jobs"]["claude-review"], old["jobs"]["claude-review"]
for key in ("if", "runs-on", "permissions"):
    assert job[key] == old_job[key], key
names = [step["name"] for step in job["steps"]]
assert names == [
    "Checkout repository",
    "Record when the review started",
    "Run Claude Code Review",
    "Show the review's turns, cost and refused calls",
    "Check the review posted its summary",
], names
assert job["steps"][0] == old_job["steps"][0], "checkout changed"
review, old_review = job["steps"][2], old_job["steps"][1]
assert review["uses"] == old_review["uses"], "action pin changed"


def tools(step):
    return set(step["with"]["claude_args"].split('"')[1].split(","))


assert tools(review) - tools(old_review) == {"Write"}, tools(review) - tools(old_review)
assert tools(old_review) <= tools(review), tools(old_review) - tools(review)
assert [step["if"] for step in job["steps"][3:]] == ["${{ !cancelled() }}"] * 2
print("workflow parses; triggers, concurrency, permissions, checkout and pin unchanged; tools gain Write")
PY
```

Expected: `workflow parses; triggers, concurrency, permissions, checkout and pin unchanged; tools gain Write`.

- [ ] **Step 3: Run the report step on two made-up execution files**

This runs the report step's own script, read from the workflow, the way Actions runs it (`bash -e`). One file has a result message without `permission_denials`; the other has a model message and one refused call.

```bash
set -eo pipefail
source .claude/forms-step2b.env
tmp=$(mktemp -d)
$PY - "$tmp" <<'PY'
import json
import sys
from pathlib import Path

import yaml

tmp = Path(sys.argv[1])
steps = yaml.safe_load(open(".github/workflows/claude-code-review.yml"))["jobs"]["claude-review"]["steps"]
report = next(s for s in steps if s["name"] == "Show the review's turns, cost and refused calls")
(tmp / "report.sh").write_text(report["run"])
(tmp / "no-denials.json").write_text(
    json.dumps([{"type": "result", "num_turns": 3, "total_cost_usd": 0.2}])
)
(tmp / "one-denial.json").write_text(
    json.dumps(
        [
            {"type": "assistant", "message": "MODEL TEXT"},
            {
                "type": "result",
                "num_turns": 21,
                "total_cost_usd": 2.45,
                "permission_denials": [
                    {
                        "tool_name": "Bash",
                        "tool_use_id": "t1",
                        "tool_input": {"command": "gh pr comment 20 --body-file x"},
                    }
                ],
            },
        ]
    )
)
PY
EXECUTION_FILE="$tmp/no-denials.json" bash -e "$tmp/report.sh"
EXECUTION_FILE="$tmp/one-denial.json" bash -e "$tmp/report.sh" > "$tmp/out.txt"
cat "$tmp/out.txt"
if grep -q "MODEL TEXT" "$tmp/out.txt"; then echo "a model message was printed"; exit 1; fi
rm -rf "$tmp"
```

Expected: `Refused calls: 0` for the first file, then `Turns: 21`, `Refused calls: 1` and `- Bash: {"command":"gh pr comment 20 --body-file x"}` for the second, and nothing from its model message.

- [ ] **Step 4: Run every gate**

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

Expected: `1802 passed, 143 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  357 passed (357)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

This task changes no page and no flow, so the journeys don't run here.

- [ ] **Step 5: Commit**

```bash
set -eo pipefail
git add \
  .github/workflows/claude-code-review.yml
git commit -F - <<'MSG'
ci(claude): fail the review check when no summary was posted, and show the refused calls

A review run could finish green and post nothing (PR #18, PR #19). The job
now records when it started and, after the review, fails with ::error:: when
no comment starting with "## Claude review" was posted or edited since then.
It reads the PR's issue comments with the job's own token (issues: read).

A step before that check prints the run's turn count, its cost, and each call
the allowed tools refused, with the tool's name and at most 200 characters of
its input. It reads these from the action's execution_file output and prints
nothing else from that file, which holds every model message. Today the log
shows only a count of refused calls.

The prompt tells the reviewer to post the summary even when it can't finish,
ending with "Reviewed N of M changed files" and naming the files it didn't
reach. The summary's first line must be exactly "## Claude review", which is
what the check looks for. The reviewer writes it to a file with the Write tool
and posts it with `gh pr comment --body-file`: the allowed tools refuse
compound commands, so a comment built with $(cat <<EOF) or a pipe is refused
and never posted, which is the likely cause of the silent runs. Write is the
one tool added.

The report step reads a result with no permission_denials key as zero refused
calls instead of failing, and both new steps skip a run that a newer push
cancelled.

Triggers and permissions are unchanged. The file parses. Each
new step's script was run as written against synthetic execution files and
against the real comments on PR #20, which passes, and on PR #19, which fails.

Clears 0 known-defect entries; known_defects.json is unchanged.
ASSERTED_CASES stays at 425: no form or test changes.

Refs DIG-144
MSG
git status --short
```

### Task 3: Tick Chapter 7 and lines 17-20 on Form 101, and print each value only where its line asks

_Built and verified as commit `72e8591` on `plan/forms-step2b`._

**Files:**

- Create: `backend/apps/forms/tests/test_form_101_schema.py`
- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/form_101.json`

**Interfaces:**

- Consumes:
  - Task 1's addendum reader in tier 2 and its orphan check, `test_every_step2_placement_matches_a_binding`.
  - Existing rules in `backend/apps/forms/services/derivations.py`: `_total_assets` and `_total_debts` (the totals 106Sum prints), `full_name` and `phone`.
  - The `FormAnswer` answers `form_101.mailing_city` and `form_101.mailing_zip`, read through `asked` bindings.
  - The field index's export states for Form 101 `Check Box1`, `Check Box20`, `Check Box21`, `Check Box22` and `Check Box23`.
- Produces:
  - Rules in `derivations.py`, under a new section "Form 101 lines 18-20": `creditor_count_range` (`_creditor_count_range`), `total_assets_range` (`_total_assets_range`) and `total_debts_range` (`_total_debts_range`), built on `_CREDITOR_RANGES`, `_AMOUNT_RANGES` and `_range(figure, ranges)`. Each returns a range's lowest figure as text, or `"more"` above the last range; `creditor_count_range` returns `""` with no debts.
  - In `data/forms/schemas/form_101.json` (87 fields to 73):
    - `Check Box1` keeps its constant `/Yes` and gains `choices` `{"/yes": "/Chapter 7"}`.
    - `Check Box20`: constant `yes`, `{"yes": "/Yes"}`.
    - `Check Box21`: `derived:creditor_count_range`, keys `1`, `50`, `100`, `200`, `1000`, `5001`, `10001`, `25001`, `50001` and `more`.
    - `Check Box22` and `Check Box23`: `derived:total_assets_range` and `derived:total_debts_range`, keys `0`, `50001`, `100001`, `500001`, `1000001`, `10000001`, `50000001`, `100000001`, `500000001`, `1000000001`, `10000000001` and `more`. Key `100000001` maps to `/100000000-500000000` on `Check Box22` and to `/100000001-500000000` on `Check Box23`.
    - `Debtor1.Name`: `derived:full_name` (the page 2-9 header).
    - `Debtor1.Contact phone_2`: `derived:phone`. `Debtor1.ZIP Code_2`: `asked:answer:form_101.mailing_zip`. `Debtor1.City_2`: `asked:answer:form_101.mailing_city`.
    - 20 boxes lose their binding: `Debtor1.First name_3`, `Debtor1.Middle name_3`, `Debtor1.Last name_3`, `Debtor1.First name_5`, `Debtor1.Middle name_5`, `Debtor1.Last name_5`, `Debtor1.Street1`, `City_2` (its binding moves to `Debtor1.City_2`), `Check Box5`, `Check Box16`, `Debtor1.Cell phone`, and the nine Appendix E 1 boxes `Attorney.Street address_3`, `Business Street address2`, `Debtor`, `Debtor_2`, `Debtor1.Business name_3`, `Debtor1.Employer Identification Number2`, `If immediate attention is needed why is it needed2`, `Street_7` and `What is the hazard2`.
  - Seven addendum rows in `step2_verification.json` (producer in brackets): `Debtor1.ZIP Code_2` (`asked:answer:form_101.mailing_zip`), `Check Box20` (`constant:yes`), `Check Box21` (`derived:creditor_count_range`), `Check Box22` (`derived:total_assets_range`), `Check Box23` (`derived:total_debts_range`), `Debtor1.Name` (`derived:full_name`) and `Debtor1.Contact phone_2` (`derived:phone`).
  - `ASSERTED_CASES = 411`. `known_defects.json` has 115 entries.
  - `backend/apps/forms/tests/test_form_101_schema.py`, 19 cases: `test_petition_ticks_chapter_7`, `test_petition_answers_yes_to_filing_under_chapter_7`, `test_line_18_ticks_the_range_the_number_of_creditors_falls_in` (3 cases), `test_a_filer_with_no_creditors_leaves_line_18_blank`, `test_lines_19_and_20_tick_the_range_the_total_falls_in` (5 cases), `test_line_19_reads_what_the_filer_owns_and_line_20_what_they_owe`, `test_header_name_prints_on_pages_2_to_9`, `test_the_filers_phone_prints_as_their_contact_phone_not_a_cell_phone`, `test_a_filer_without_a_mailing_address_leaves_the_mailing_block_blank`, `test_the_mailing_address_prints_in_the_mailing_block_and_nowhere_else`, `test_line_2_other_names_and_a_second_street_line_stay_blank`, `test_an_answer_prints_once_and_never_in_the_box_beside_it` and `test_line_10_never_names_the_filer_as_the_other_debtor`.

**Decisions already made in this task:**

- **One binding per box (E006).** `Debtor1.ZIP Code_2` and `Debtor1.Contact phone_2` are re-ruled in place. `City_2`'s object now carries `pdf_field` `Debtor1.City_2`, so the move and the delete are one edit. No box gets a second object.
- **Line 18 counts the session's `DebtInfo` rows,** not distinct creditor names, as `data/forms/field_index/audit/form_101.unbound.json` puts it ("derivable from count of DebtInfo rows"). With no debts, line 18 is blank.
- **Lines 19 and 20 read the figures `total_assets` and `total_debts` print,** so the petition never disagrees with 106Sum. With nothing owned or owed, the line ticks $0-$50,000 (key `0`), not blank: a total prints once all its inputs follow B2 (§6.1 B5).
- **Each range rule returns the range's lowest figure,** and each box's `choices` maps it to that box's own export state from the index (§6.2). A total is compared with each range's top, so cents between two ranges go up. Line 19 spells the $100M range `/100000000-500000000` and line 20 `/100000001-500000000`.
- **`Check Box1` keeps its constant `/Yes`,** which the resolver lower-cases to `/yes`. `{"/yes": "/Chapter 7"}` ticks both of its widgets, on page 1 and at line 7. Its schema label still reads "Individual", though the index calls it "Chapter you are filing under". That label never prints and predates 2b; leave it.
- **`Check Box16` loses its binding on the owner's answer to Q7** (§3): "101 `Check Box16` (credit counseling) loses its constant." The rest of Q7, the consumer-debts answer on `Check Box18`, is Task 5's. `Check Box5` loses its binding because it is "the line-6 venue question, not a second chapter box" (§6.4).
- **"Contact phone" gets the filer's phone, and `Debtor1.Cell phone` loses its binding,** because the wizard never asks whether the number is a cell (§6.4). The answer key `form_101.preparer_phone` is now bound nowhere: a preparer's phone belongs on Form 119.
- **`Debtor1.ZIP Code_2` stays ADD, with an addendum row,** although the moved-here join would also assert it (Ruling T0-b). Its evidence cites the owner's decision 6d, which Appendix E 2 quotes: the mailing ZIP would read the mailing answer "like the street, city and state beside it". `Debtor1.City_2` is MOVED and needs no row: `verification.json`'s confirmed `City_2` row names it. The addendum's `producer` is the whole binding key (Ruling C-1).
- **No rule loses its last binding.** `first_name`, `middle_name`, `last_name`, `street_address`, `zip_code`, `full_name` and `phone` stay bound.
- **`test_line_19_reads_what_the_filer_owns_and_line_20_what_they_owe` stays.** Every other range case gives assets and debts the same amounts, so a schema that crossed lines 19 and 20 passed the whole suite until this test was added in review.
- **No tier 3 rows for Form 101's new boxes.** Appendix D has none.
- **`ASSERTED_CASES` goes from 425 to 411 (−14):** −19 for the deleted or moved wrong-box bindings, −1 for `Debtor1.Cell phone`'s passing case, +1 for `Debtor1.City_2` through moved-here, and +5 for `Check Box20`–`23` and `Debtor1.Name` through the addendum. `Debtor1.ZIP Code_2` and `Debtor1.Contact phone_2` stay asserted, under their new keys.
- **27 known-defect entries are deleted by hand (142 → 115):**

  - 3 tier 1 orphans, `unmapped_choice` (DIG-68): `Check Box1`, `Check Box5` and `Check Box16`.
  - 19 tier 2 orphans, `wrong_box` (DIG-76): the six line-2 other-name boxes, `Debtor1.Street1`, `City_2`, `Check Box5`, `Check Box16`, and the nine Appendix E 1 boxes.
  - 5 tier 3 strict XPASS, `wrong_value` (DIG-68): `Check Box1` for maria, james, priya, deshawn and sarah.

- [ ] **Step 1: Write the failing tests**

```python file=backend/apps/forms/tests/test_form_101_schema.py
"""
What the petition (Form 101) prints from the intake (step 2 spec §6.4, Appendix A.1).

Business intent: the filer signs Form 101 under penalty of perjury, so each box shows
only what its line asks. It ticks Chapter 7 and the ranges on lines 18-20, and prints
the filer's name in the page header and the filer's own phone. A value never spills
into a neighbouring box, and a line the intake doesn't ask stays blank (DIG-76, DIG-68).
"""

from datetime import date
from decimal import Decimal
from io import BytesIO

import pypdf
import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller, field_of, qualified_name
from apps.intake.models import (
    AssetInfo,
    DebtInfo,
    DebtorInfo,
    FormAnswer,
    IntakeSession,
    SOFAReport,
)

User = get_user_model()

# The widest amount one row can hold (DecimalField(12, 2)).
WIDEST_ROW = "9999999999.99"


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="schema101", password="pass")
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


def _petition(session):
    return resolve(load_schema("form_101"), session)


def _answer(session, key, value, form_type="form_101"):
    FormAnswer.objects.create(session=session, form_type=form_type, field_key=key, value=value)


def _debts(session, amounts):
    DebtInfo.objects.bulk_create(
        DebtInfo(
            session=session,
            creditor_name=f"Creditor {i}",
            debt_type="credit_card",
            amount_owed=Decimal(amount),
        )
        for i, amount in enumerate(amounts)
    )


def _assets(session, amounts):
    AssetInfo.objects.bulk_create(
        AssetInfo(
            session=session,
            asset_type="other",
            description=f"Asset {i}",
            current_value=Decimal(amount),
        )
        for i, amount in enumerate(amounts)
    )


def test_petition_ticks_chapter_7(session):
    # One value ticks Chapter 7 in both places the form asks: the page 1 header and line 7.
    assert _petition(session)["Check Box1"] == "/Chapter 7"


def test_petition_answers_yes_to_filing_under_chapter_7(session):
    assert _petition(session)["Check Box20"] == "/Yes"


@pytest.mark.parametrize("count,state", [(1, "/1-49"), (49, "/1-49"), (50, "/50-99")])
def test_line_18_ticks_the_range_the_number_of_creditors_falls_in(session, count, state):
    _debts(session, ["100.00"] * count)
    assert _petition(session)["Check Box21"] == state


def test_a_filer_with_no_creditors_leaves_line_18_blank(session):
    assert "Check Box21" not in _petition(session)


@pytest.mark.parametrize(
    "amounts,line_19,line_20",
    [
        # Nothing owned or owed is the lowest range, not a blank line.
        ([], "/0-50000", "/0-50000"),
        (["50000.00"], "/0-50000", "/0-50000"),
        # Cents above a range's top belong to the next range up.
        (["50000.01"], "/50001-100000", "/50001-100000"),
        # Lines 19 and 20 spell this range differently, and each ticks its own.
        (["100000000.50"], "/100000000-500000000", "/100000001-500000000"),
        ([WIDEST_ROW] * 6, "/More than 50000000000", "/More than 50000000000"),
    ],
)
def test_lines_19_and_20_tick_the_range_the_total_falls_in(session, amounts, line_19, line_20):
    _assets(session, amounts)
    _debts(session, amounts)
    petition = _petition(session)
    assert petition["Check Box22"] == line_19
    assert petition["Check Box23"] == line_20


def test_line_19_reads_what_the_filer_owns_and_line_20_what_they_owe(session):
    # Assets and debts fall in different ranges, so a line that read the other total fails.
    _assets(session, ["10000.00"])
    _debts(session, ["75000.00"])
    petition = _petition(session)
    assert petition["Check Box22"] == "/0-50000"
    assert petition["Check Box23"] == "/50001-100000"


def test_header_name_prints_on_pages_2_to_9(session):
    pdf = PDFFormFiller().fill("form_101", _petition(session))
    # A viewer draws each widget's own appearance stream, so every page must have one.
    pages = []
    for number, page in enumerate(pypdf.PdfReader(BytesIO(pdf)).pages, start=1):
        for annot in page.get("/Annots") or []:
            widget = annot.get_object()
            if qualified_name(field_of(widget)) != "Debtor1.Name":
                continue
            appearance = widget.get("/AP")
            if appearance is not None and b"Jane Q Doe" in appearance["/N"].get_data():
                pages.append(number)
    assert pages == list(range(2, 10))


def test_the_filers_phone_prints_as_their_contact_phone_not_a_cell_phone(session):
    # The intake never asks whether the number is a cell, and a preparer's phone
    # belongs on Form 119, not here.
    _answer(session, "preparer_phone", "773-555-0199")
    petition = _petition(session)
    assert petition["Debtor1.Contact phone_2"] == "312-555-0100"
    assert "Debtor1.Cell phone" not in petition


def test_a_filer_without_a_mailing_address_leaves_the_mailing_block_blank(session):
    petition = _petition(session)
    assert "Debtor1.City_2" not in petition
    assert "Debtor1.ZIP Code_2" not in petition


def test_the_mailing_address_prints_in_the_mailing_block_and_nowhere_else(session):
    _answer(session, "mailing_city", "Evanston")
    _answer(session, "mailing_zip", "60201")
    petition = _petition(session)
    assert petition["Debtor1.City_2"] == "Evanston"
    assert petition["Debtor1.ZIP Code_2"] == "60201"
    # City_2 is the city of a hazardous property on line 14.
    assert "City_2" not in petition


def test_line_2_other_names_and_a_second_street_line_stay_blank(session):
    # The intake asks for no other names and has one street line.
    petition = _petition(session)
    other_names = [
        f"Debtor1.{part} name_{n}" for part in ("First", "Middle", "Last") for n in (3, 5)
    ]
    assert [box for box in [*other_names, "Debtor1.Street1"] if box in petition] == []
    # The filer's name and street still print on the lines that ask for them.
    assert petition["Debtor1.First name"] == "Jane"
    assert petition["Debtor1.Street"] == "123 Main St"


def test_an_answer_prints_once_and_never_in_the_box_beside_it(session):
    SOFAReport.objects.create(session=session, has_business=True)
    _answer(session, "attorney_gate", "yes", form_type="form_107")
    answers = {
        "business_name": "Doe Cleaning",
        "employer_ein": "12-3456789",
        "business_street": "9 Elm St",
        "hazard_description": "Leaking tank",
        "hazard_reason": "It may explode",
        "hazard_street": "1 Oak St",
        "attorney_street": "5 Court St",
    }
    for key, value in answers.items():
        _answer(session, key, value)
    petition = _petition(session)
    # Each answer still prints in its own box.
    assert petition["Debtor1.Business name"] == "Doe Cleaning"
    assert petition["Debtor1.Employer Identification Number1"] == "12-3456789"
    assert petition["Business Street address"] == "9 Elm St"
    assert petition["What is the hazard1"] == "Leaking tank"
    assert petition["If immediate attention is needed why is it needed1"] == "It may explode"
    assert petition["Street_6"] == "1 Oak St"
    assert petition["Attorney.Street address_2"] == "5 Court St"
    repeats = [
        "Debtor1.Business name_3",
        "Debtor1.Employer Identification Number2",
        "Business Street address2",
        "What is the hazard2",
        "If immediate attention is needed why is it needed2",
        "Street_7",
        "Attorney.Street address_3",
    ]
    assert [box for box in repeats if box in petition] == []


def test_line_10_never_names_the_filer_as_the_other_debtor(session):
    # Line 10 asks about a case filed by a spouse, partner or affiliate, not the filer.
    _answer(session, "prior_bankruptcy_gate", "yes")
    petition = _petition(session)
    assert "Debtor" not in petition
    assert "Debtor_2" not in petition
```

Every test resolves the real schema with `resolve(load_schema("form_101"), session)`. The header test fills the PDF and reads each `Debtor1.Name` widget's own appearance stream, because a viewer draws that and tier 1 reads only `/V`. The duplicate test sets the seven answers behind seven of the Appendix E 1 boxes and requires each one to print in its own box, so it can't pass on an empty petition; the line 10 test covers the other two, `Debtor` and `Debtor_2`.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_101_schema.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: FAIL — `18 failed, 1 passed`. The tick tests stop on a KeyError for Check Box1, Check Box20, Check Box21 and Check Box22, because nothing ticks them. No page draws the header name, the preparer's phone prints as the contact phone, the residence ZIP fills the mailing block while the mailing city is missing from it, the six other-name boxes and the second street line print, the seven duplicate boxes print, and line 10 names the filer. The one pass is the no-creditor test, which passes only because Check Box21 is unbound until Step 4.

- [ ] **Step 3: Add the range rules for lines 18-20**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index b81f6d4..17051c8 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -187,6 +187,66 @@ def _total_monthly_expenses(session: IntakeSession) -> str:
     return _fmt(Decimal(str(expense_info.calculate_total_monthly_expenses())))


+# ---------------------------------------------------------------------------
+# Form 101 lines 18-20: estimated creditors, assets and liabilities
+# ---------------------------------------------------------------------------
+
+# (a range's top, its lowest figure). Each box's choices map the lowest figure to that
+# box's own spelling of the range, which differs between lines 19 and 20.
+_CREDITOR_RANGES = (
+    (49, "1"),
+    (99, "50"),
+    (199, "100"),
+    (999, "200"),
+    (5000, "1000"),
+    (10000, "5001"),
+    (25000, "10001"),
+    (50000, "25001"),
+    (100000, "50001"),
+)
+_AMOUNT_RANGES = (
+    (50000, "0"),
+    (100000, "50001"),
+    (500000, "100001"),
+    (1000000, "500001"),
+    (10000000, "1000001"),
+    (50000000, "10000001"),
+    (100000000, "50000001"),
+    (500000000, "100000001"),
+    (1000000000, "500000001"),
+    (10000000000, "1000000001"),
+    (50000000000, "10000000001"),
+)
+
+
+def _range(figure, ranges) -> str:
+    """
+    The lowest figure of the first range whose top `figure` doesn't pass, or "more".
+
+    Comparing with each range's top puts cents between two ranges in the higher one.
+    """
+    for top, lowest in ranges:
+        if figure <= top:
+            return lowest
+    return "more"
+
+
+def _creditor_count_range(session: IntakeSession) -> str:
+    from apps.intake.models import DebtInfo
+
+    count = DebtInfo.objects.filter(session=session).count()
+    return _range(count, _CREDITOR_RANGES) if count else ""
+
+
+def _total_assets_range(session: IntakeSession) -> str:
+    # No assets is the $0-$50,000 range, not a blank line.
+    return _range(Decimal(_total_assets(session)), _AMOUNT_RANGES)
+
+
+def _total_debts_range(session: IntakeSession) -> str:
+    return _range(Decimal(_total_debts(session)), _AMOUNT_RANGES)
+
+
 # ---------------------------------------------------------------------------
 # Form 122A-1 means test derivations
 # ---------------------------------------------------------------------------
@@ -497,6 +557,10 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "joint_filer_name": _full_name,
     "cmi": _cmi,
     "total_monthly_expenses": _total_monthly_expenses,
+    # Form 101 lines 18-20
+    "creditor_count_range": _creditor_count_range,
+    "total_assets_range": _total_assets_range,
+    "total_debts_range": _total_debts_range,
     # Form 122A-1 means test derivations
     "line1_wages": _line1_wages,
     "line2_business_income": _line2_business_income,
PATCH
```

`_range` walks a table of (top, lowest figure) pairs and returns the first range whose top the figure doesn't pass. Lines 19 and 20 bucket `Decimal(_total_assets(session))` and `Decimal(_total_debts(session))`, and line 18 counts debts with `DebtInfo.objects.filter(session=session).count()`, which reads no encrypted field.

- [ ] **Step 4: Rebind Form 101, with an addendum row for each ADD box**

```bash
git apply <<'PATCH'
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index fe51488..f258e63 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -1 +1,72 @@
-[]
+[
+  {
+    "schema": "form_101",
+    "pdf_field": "Debtor1.ZIP Code_2",
+    "producer": "asked:answer:form_101.mailing_zip",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Debtor1.ZIP Code_2",
+    "evidence": "Field index: Debtor1.ZIP Code_2 p2 line 5 'If your mailing address is different from the one above (mailing address): ZIP Code' (adjudicated). The audit's own row on this box says the residence ZIP doesn't belong here, and its confirmed rows on Debtor2.ZIP and ZIP Code_4 name this box for the mailing_zip answer. Owner's decision 6d (step 2 spec Appendix E 2, §6.4): the mailing ZIP reads the mailing answer, like the street, city and state beside it."
+  },
+  {
+    "schema": "form_101",
+    "pdf_field": "Check Box20",
+    "producer": "constant:yes",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Check Box20",
+    "evidence": "Field index: Check Box20 p7 line 17 'Are you filing under Chapter 7?', states /No and /Yes. Step 2 spec §6.4: line 17 is Yes; every DigniFi filing is Chapter 7."
+  },
+  {
+    "schema": "form_101",
+    "pdf_field": "Check Box21",
+    "producer": "derived:creditor_count_range",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Check Box21",
+    "evidence": "Field index: Check Box21 p7 line 18 'How many creditors do you estimate that you owe?', ten states from /1-49 to /More than 100000. Step 2 spec §6.2 and §6.4: lines 18-20 tick their ranges; creditor_count_range buckets the number of debts in the intake and is blank with none."
+  },
+  {
+    "schema": "form_101",
+    "pdf_field": "Check Box22",
+    "producer": "derived:total_assets_range",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Check Box22",
+    "evidence": "Field index: Check Box22 p7 line 19 'How much do you estimate your assets to be worth?', twelve states from /0-50000 to /More than 50000000000; this line spells the $100M range /100000000-500000000. Step 2 spec §6.1 (B5) and §6.2: total_assets_range buckets the total of every asset, the figure 106Sum line 1c prints."
+  },
+  {
+    "schema": "form_101",
+    "pdf_field": "Check Box23",
+    "producer": "derived:total_debts_range",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Check Box23",
+    "evidence": "Field index: Check Box23 p7 line 20 'How much do you estimate your liabilities to be?', twelve states from /0-50000 to /More than 50000000000; this line spells the $100M range /100000001-500000000. Step 2 spec §6.1 (B5) and §6.2: total_debts_range buckets the total of every debt (total_debts)."
+  },
+  {
+    "schema": "form_101",
+    "pdf_field": "Debtor1.Name",
+    "producer": "derived:full_name",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Debtor1.Name",
+    "evidence": "Field index: Debtor1.Name 'Running header: Debtor 1 (First Name Middle Name Last Name)', one field with a widget on each of pages 2-9 (header). Step 2 spec §6.4: the header name prints on pages 2-9."
+  },
+  {
+    "schema": "form_101",
+    "pdf_field": "Debtor1.Contact phone_2",
+    "producer": "derived:phone",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Debtor1.Contact phone_2",
+    "evidence": "Field index: Debtor1.Contact phone_2 p9 Part 7 'For you if you are filing this bankruptcy without an attorney: Contact phone' (adjudicated). The audit's confirmed note on this box: the debtor's own phone, which the phone rule gives; the preparer's phone belongs on Form 119. Step 2 spec §6.4: Contact phone gets the phone, and Cell phone stays blank because the wizard never asks whether the number is a cell."
+  }
+]
diff --git a/data/forms/schemas/form_101.json b/data/forms/schemas/form_101.json
index f75e63e..ec0bebe 100644
--- a/data/forms/schemas/form_101.json
+++ b/data/forms/schemas/form_101.json
@@ -122,108 +122,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Debtor1.First name_3",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "First name",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "first_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.Middle name_3",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Middle name",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "middle_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.Last name_3",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Last name",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "last_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.First name_5",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "First name",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "first_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.Middle name_5",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Middle name",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "middle_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.Last name_5",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Last name",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "last_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "Debtor1.Business name",
       "type": "text",
@@ -242,41 +140,24 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Debtor1.Business name_3",
+      "pdf_field": "Debtor1.Name",
       "type": "text",
-      "source": "asked",
-      "page": 1,
-      "label": "Business name",
-      "required": false,
-      "conditional_on": "has_business",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_101.business_name",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.Employer Identification Number1",
-      "type": "text",
-      "source": "asked",
+      "source": "derived",
       "page": 2,
-      "label": "Employer Identification Number",
+      "label": "Debtor name",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": null,
+      "rule": "full_name",
       "ingest_key": null,
-      "binding": "answer:form_101.employer_ein",
+      "binding": null,
       "repeat": null,
       "repeat_capacity": null,
       "row": null,
       "legal_review": false
     },
     {
-      "pdf_field": "Debtor1.Employer Identification Number2",
+      "pdf_field": "Debtor1.Employer Identification Number1",
       "type": "text",
       "source": "asked",
       "page": 2,
@@ -309,23 +190,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Debtor1.Street1",
-      "type": "text",
-      "source": "derived",
-      "page": 2,
-      "label": "Street address",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "street_address",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "Debtor1.City",
       "type": "text",
@@ -429,7 +293,7 @@
       "legal_review": false
     },
     {
-      "pdf_field": "City_2",
+      "pdf_field": "Debtor1.City_2",
       "type": "text",
       "source": "asked",
       "page": 2,
@@ -533,15 +397,15 @@
     {
       "pdf_field": "Debtor1.ZIP Code_2",
       "type": "text",
-      "source": "derived",
+      "source": "asked",
       "page": 2,
       "label": "ZIP Code",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "zip_code",
+      "rule": null,
       "ingest_key": null,
-      "binding": null,
+      "binding": "answer:form_101.mailing_zip",
       "repeat": null,
       "repeat_capacity": null,
       "row": null,
@@ -700,23 +564,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Debtor",
-      "type": "text",
-      "source": "derived",
-      "page": 3,
-      "label": "Debtor",
-      "required": false,
-      "conditional_on": "has_prior_bankruptcy",
-      "value": null,
-      "rule": "full_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "Relationship to you",
       "type": "text",
@@ -785,23 +632,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Debtor_2",
-      "type": "text",
-      "source": "derived",
-      "page": 3,
-      "label": "Debtor",
-      "required": false,
-      "conditional_on": "has_prior_bankruptcy",
-      "value": null,
-      "rule": "full_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "Relationship to you_2",
       "type": "text",
@@ -904,23 +734,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Business Street address2",
-      "type": "text",
-      "source": "asked",
-      "page": 4,
-      "label": "Street address",
-      "required": false,
-      "conditional_on": "has_business",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_101.business_street",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "Business City",
       "type": "text",
@@ -989,23 +802,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "What is the hazard2",
-      "type": "text",
-      "source": "asked",
-      "page": 5,
-      "label": "What is the hazard",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_101.hazard_description",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "If immediate attention is needed why is it needed1",
       "type": "text",
@@ -1023,23 +819,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "If immediate attention is needed why is it needed2",
-      "type": "text",
-      "source": "asked",
-      "page": 5,
-      "label": "If immediate attention is needed, why is it needed",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_101.hazard_reason",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "Street_6",
       "type": "text",
@@ -1057,23 +836,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Street_7",
-      "type": "text",
-      "source": "asked",
-      "page": 5,
-      "label": "Street address",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_101.hazard_street",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "State_6",
       "type": "text",
@@ -1244,23 +1006,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Attorney.Street address_3",
-      "type": "text",
-      "source": "asked",
-      "page": 8,
-      "label": "Street address",
-      "required": false,
-      "conditional_on": "has_attorney",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_101.attorney_street",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "Attorney.Zip",
       "type": "text",
@@ -1383,26 +1128,9 @@
     {
       "pdf_field": "Debtor1.Contact phone_2",
       "type": "text",
-      "source": "asked",
-      "page": 9,
-      "label": "Contact phone",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_101.preparer_phone",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.Cell phone",
-      "type": "text",
       "source": "derived",
       "page": 9,
-      "label": "Cell phone",
+      "label": "Contact phone",
       "required": false,
       "conditional_on": null,
       "value": null,
@@ -1435,7 +1163,9 @@
       "pdf_field": "Check Box1",
       "type": "checkbox",
       "source": "constant",
-      "choices": {},
+      "choices": {
+        "/yes": "/Chapter 7"
+      },
       "page": 1,
       "label": "Individual",
       "required": false,
@@ -1450,15 +1180,17 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Check Box5",
+      "pdf_field": "Check Box20",
       "type": "checkbox",
       "source": "constant",
-      "choices": {},
-      "page": 1,
-      "label": "Chapter 7",
+      "choices": {
+        "yes": "/Yes"
+      },
+      "page": 7,
+      "label": "Are you filing under Chapter 7?",
       "required": false,
       "conditional_on": null,
-      "value": "/Yes",
+      "value": "yes",
       "rule": null,
       "ingest_key": null,
       "binding": null,
@@ -1468,16 +1200,89 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Check Box16",
+      "pdf_field": "Check Box21",
       "type": "checkbox",
-      "source": "constant",
-      "choices": {},
-      "page": 1,
-      "label": "Consumer debts",
+      "source": "derived",
+      "choices": {
+        "1": "/1-49",
+        "50": "/50-99",
+        "100": "/100-199",
+        "200": "/200-999",
+        "1000": "/1000-5000",
+        "5001": "/5001-10000",
+        "10001": "/10001-25000",
+        "25001": "/25001-50000",
+        "50001": "/50001-100000",
+        "more": "/More than 100000"
+      },
+      "page": 7,
+      "label": "How many creditors do you estimate that you owe?",
       "required": false,
       "conditional_on": null,
-      "value": "/Yes",
-      "rule": null,
+      "value": null,
+      "rule": "creditor_count_range",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "Check Box22",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "0": "/0-50000",
+        "50001": "/50001-100000",
+        "100001": "/100001-500000",
+        "500001": "/500001-1000000",
+        "1000001": "/1000001-10000000",
+        "10000001": "/10000001-50000000",
+        "50000001": "/50000001-100000000",
+        "100000001": "/100000000-500000000",
+        "500000001": "/500000001-1000000000",
+        "1000000001": "/1000000001-10000000000",
+        "10000000001": "/10000000001-50000000000",
+        "more": "/More than 50000000000"
+      },
+      "page": 7,
+      "label": "How much do you estimate your assets to be worth?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_assets_range",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "Check Box23",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "0": "/0-50000",
+        "50001": "/50001-100000",
+        "100001": "/100001-500000",
+        "500001": "/500001-1000000",
+        "1000001": "/1000001-10000000",
+        "10000001": "/10000001-50000000",
+        "50000001": "/50000001-100000000",
+        "100000001": "/100000001-500000000",
+        "500000001": "/500000001-1000000000",
+        "1000000001": "/1000000001-10000000000",
+        "10000000001": "/10000000001-50000000000",
+        "more": "/More than 50000000000"
+      },
+      "page": 7,
+      "label": "How much do you estimate your liabilities to be?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "total_debts_range",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
PATCH
```

The schema follows §6.4 and Appendix A.1: Chapter 7 ticks, line 17 is Yes, lines 18-20 tick their ranges, the header name prints on pages 2-9, Contact phone gets the phone, and the mailing ZIP and city read the mailing-address answers. Twenty boxes lose their bindings: the 19 that tier 2 convicts of the wrong box (`City_2`'s moves to `Debtor1.City_2`) and `Debtor1.Cell phone`. Each of the seven ADD boxes gets its addendum row in this commit (§7.4), citing the box's field-index label and the spec section that decided it.

- [ ] **Step 5: Update tier 2's count and delete the 27 cleared entries**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index 83b4569..351ac53 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -1,28 +1,4 @@
 [
-  {
-    "form_type": "form_101",
-    "pdf_field": "Check Box1",
-    "tier": "1",
-    "case": "",
-    "class": "unmapped_choice",
-    "ticket": "DIG-68"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Check Box16",
-    "tier": "1",
-    "case": "",
-    "class": "unmapped_choice",
-    "ticket": "DIG-68"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Check Box5",
-    "tier": "1",
-    "case": "",
-    "class": "unmapped_choice",
-    "ticket": "DIG-68"
-  },
   {
     "form_type": "form_121",
     "pdf_field": "Check Box1",
@@ -31,158 +7,6 @@
     "class": "unmapped_choice",
     "ticket": "DIG-68"
   },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Attorney.Street address_3",
-    "tier": "2",
-    "case": "asked:answer:form_101.attorney_street",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Business Street address2",
-    "tier": "2",
-    "case": "asked:answer:form_101.business_street",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Check Box16",
-    "tier": "2",
-    "case": "constant:/Yes",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Check Box5",
-    "tier": "2",
-    "case": "constant:/Yes",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "City_2",
-    "tier": "2",
-    "case": "asked:answer:form_101.mailing_city",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Debtor",
-    "tier": "2",
-    "case": "derived:full_name",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Debtor1.Business name_3",
-    "tier": "2",
-    "case": "asked:answer:form_101.business_name",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Debtor1.Employer Identification Number2",
-    "tier": "2",
-    "case": "asked:answer:form_101.employer_ein",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Debtor1.First name_3",
-    "tier": "2",
-    "case": "derived:first_name",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Debtor1.First name_5",
-    "tier": "2",
-    "case": "derived:first_name",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Debtor1.Last name_3",
-    "tier": "2",
-    "case": "derived:last_name",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Debtor1.Last name_5",
-    "tier": "2",
-    "case": "derived:last_name",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Debtor1.Middle name_3",
-    "tier": "2",
-    "case": "derived:middle_name",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Debtor1.Middle name_5",
-    "tier": "2",
-    "case": "derived:middle_name",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Debtor1.Street1",
-    "tier": "2",
-    "case": "derived:street_address",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Debtor_2",
-    "tier": "2",
-    "case": "derived:full_name",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "If immediate attention is needed why is it needed2",
-    "tier": "2",
-    "case": "asked:answer:form_101.hazard_reason",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Street_7",
-    "tier": "2",
-    "case": "asked:answer:form_101.hazard_street",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "What is the hazard2",
-    "tier": "2",
-    "case": "asked:answer:form_101.hazard_description",
-    "class": "wrong_box",
-    "ticket": "DIG-76"
-  },
   {
     "form_type": "form_103b",
     "pdf_field": "4 type",
@@ -679,46 +503,6 @@
     "class": "wrong_box",
     "ticket": "DIG-52"
   },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Check Box1",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-68"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Check Box1",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-68"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Check Box1",
-    "tier": "3",
-    "case": "maria",
-    "class": "wrong_value",
-    "ticket": "DIG-68"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Check Box1",
-    "tier": "3",
-    "case": "priya",
-    "class": "wrong_value",
-    "ticket": "DIG-68"
-  },
-  {
-    "form_type": "form_101",
-    "pdf_field": "Check Box1",
-    "tier": "3",
-    "case": "sarah",
-    "class": "wrong_value",
-    "ticket": "DIG-68"
-  },
   {
     "form_type": "form_106sum",
     "pdf_field": "3c",
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index 54221b5..f41af3a 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 425
+ASSERTED_CASES = 411


 def _audit_dir():
PATCH
```

R3: the commit deletes exactly the entries it orphans or turns into a strict XPASS, by hand, and adds none.

- [ ] **Step 6: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_101_schema.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `19 passed`.

- [ ] **Step 7: Run the oracle and the list check**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `1115 passed, 115 xfailed`, with no failures: one expected failure for each listed defect. A listed case that now passes would be a strict XPASS, and an entry with no case behind it would fail the orphan test, so a green run proves the list holds exactly the right entries.

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

Expected: `1851 passed, 116 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  357 passed (357)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

This task changes no page and no flow, so the journeys don't run here.

- [ ] **Step 9: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_form_101_schema.py \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_oracle_tier2.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/form_101.json
git commit -F - <<'MSG'
fix(forms): Form 101 ticks Chapter 7 and lines 17-20, and prints each value only where its line asks

Form 101 now prints these from the intake (step 2 spec §6.4, Appendix A.1):
- Chapter 7 ticks on page 1 and line 7. Check Box1 maps its constant to
  /Chapter 7; until now it ticked nothing.
- Line 17 is Yes (Check Box20, constant).
- Lines 18-20 tick their ranges through three new rules:
  - `creditor_count_range` counts the session's debts. With none, line 18
    is blank.
  - `total_assets_range` and `total_debts_range` use the totals that
    `total_assets` and `total_debts` print. With nothing owned or owed,
    the line ticks $0-$50,000.
  - Each rule returns a range's lowest figure, which the box's choices map
    to that box's own state from the index. A total is compared with each
    range's top, so cents between two ranges go up. Lines 19 and 20 spell
    the $100M range differently, and each ticks its own spelling.
- The header name prints on pages 2-9 (Debtor1.Name, full_name).
- Contact phone gets the filer's phone, re-ruled in place from the
  preparer's phone. Cell phone loses its binding, because the wizard never
  asks whether the number is a cell.
- The mailing ZIP reads the mailing_zip answer, re-ruled in place; it
  printed the residence ZIP. The mailing city moves from City_2, which is
  line 14's hazardous-property city, to Debtor1.City_2.
- These lose their bindings: the six line-2 other-name boxes, the second
  street line, Check Box5 (line 6, why this district), Check Box16 (line
  15, credit counseling), and the nine boxes that repeat a neighbour's
  value or put the filer's own name on line 10 (Appendix E 1).

step2_verification.json gains the 7 rows for the ADD boxes. Debtor1.City_2
is MOVED: the audit's confirmed City_2 row names it.

New test file: test_form_101_schema.py. No rule loses its last binding. The
answer key form_101.preparer_phone is no longer bound anywhere.

Clears 27 known-defect entries (142 -> 115):
- 3 tier 1, by orphan: Check Box1, Check Box5 and Check Box16.
- 19 tier 2, by orphan.
- 5 tier 3, by strict XPASS: Check Box1 for all five personas.

ASSERTED_CASES 425 -> 411 (-14):
- -19 for the deleted or moved wrong-box bindings.
- -1 for Debtor1.Cell phone's passing case.
- +1 for Debtor1.City_2, through moved-here.
- +5 for Check Box20-23 and Debtor1.Name, through the addendum.
Debtor1.ZIP Code_2 and Debtor1.Contact phone_2 stay asserted, now under
their new keys.

Refs DIG-76, DIG-68
MSG
git status --short
```

### Task 4: Leave signature lines and signing dates blank for wet ink

_Built and verified as commit `eba92f6` on `plan/forms-step2b`._

**Files:**

- Create: `backend/apps/forms/tests/test_signing_lines.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `data/forms/schemas/form_101.json`
- Modify: `data/forms/schemas/form_106dec.json`
- Modify: `data/forms/schemas/form_121.json`
- Modify: `data/forms/schemas/form_122a1.json`
- Modify: `data/forms/schemas/form_122a2.json`

**Interfaces:**

- Consumes:
  - Task 3's schemas `form_101.json`, `form_106dec.json`, `form_121.json`, `form_122a1.json` and `form_122a2.json`, each with exactly one field object per box.
  - `ASSERTED_CASES = 411` in `test_oracle_tier2.py` (Task 3), and the 115 entries in `known_defects.json`.
  - The rules `full_name` and `today_iso` in `DERIVATIONS` (`backend/apps/forms/services/derivations.py`, unchanged).
  - For the test: `build_field_values` (`apps.forms.registry`), `PDFFormFiller` (`apps.forms.services.pdf_filler`), `read_widgets` (`apps.forms.tests.pdf_readback`), the `ilnd_2025_data` fixture and `seed_demo_data` with `persona="priya"`, whose session belongs to `demo_priya`.
- Produces:
  - Ten boxes with no field object: Form 101 `Executed on` and `Attorney.Date signed`; 106Dec and 121 `Debtor1.signature` and `Executed on`; 122A-1 and 122A-2 `Debtor1.sig` and `Debtor1.Date signed`.
  - `today_iso` keeps one binding, Schedule I `Supplemental income date`. Task 10 removes it and deletes the rule. `full_name` stays bound on every caption.
  - The answer keys `answer:form_101.executed_on` and `answer:form_101.attorney_date_signed` are bound nowhere.
  - `ASSERTED_CASES = 401`.
  - `known_defects.json` is unchanged, with 115 entries.
  - `backend/apps/forms/tests/test_signing_lines.py`: `test_signature_lines_and_signing_dates_stay_blank_for_wet_ink`, parametrized over `SIGNING_LINES` (10 cases), with each form's `STILL_PRINTS` neighbours.

**Decisions already made in this task:**

- The owner's Q6 (§3) decides all ten boxes: "every signature line and signing date stays blank for wet ink. The dashboard tells the filer which pages to sign and date; that part is step 4 work (Appendix E)."
- Each box is an Appendix A DEL row: its field object is deleted, not re-ruled to print blank. A DEL row needs no addendum row, so `step2_verification.json` is unchanged.
- No rule is deleted. `full_name` still prints every caption. `today_iso` keeps its last binding, Schedule I `Supplemental income date`, until Task 10 deletes the box and the rule together (a rule goes only with its last binding).
- `ASSERTED_CASES` goes from 411 to 401 (−10), measured from tier 2's collected cases. Tier 2 asserted all ten bindings, Form 101's two asked-answer boxes included, and all ten passed. Tier 1 loses the same ten text cases; its count is not pinned.
- No known-defect entry is deleted: none is listed on these ten boxes.
- The test seeds Priya, whose packet holds all five forms, 122A-2 included. It also stores a signing date, an attorney's printed name and the attorney gate, so a blank box comes from the removed binding and not from missing input. `STILL_PRINTS` requires each form's name box, and Form 101's `Attorney.Printed name`, to keep printing, so a form that printed nothing can't pass.
- The test guards only the ten boxes that held a binding. The other signing widgets (Form 101 `Debtor1.signature`, `Debtor1.Date signed` and `Attorney.Sig`, Form 107's signing block, 103B `undefined_38` and `Date`, and the Debtor 2 lines) are unbound or `source: "signature"` placeholders today. Guarding them is step 4's, with DIG-73.
- `test_api_readback.py`'s TODAY comment and `_comparable`'s docstring ("signing date") now describe only Schedule I's box. Task 10 rewords them when `today_iso` goes; leave them here.

- [ ] **Step 1: Write the failing test**

```python file=backend/apps/forms/tests/test_signing_lines.py
"""
Signature lines and signing dates print blank (step 2 spec §3 Q6, §6.3; DIG-73).

Business intent: the filer signs each form in ink and dates it on the day they sign.
A typed name on a signature line is not their signature, and a date printed when the
packet was built is not the day they swore to it under penalty of perjury. So both stay
blank, even for a filer who gave a signing date or named an attorney.
"""

from functools import cache

import pytest
from django.core.management import call_command

from apps.forms.registry import build_field_values
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_widgets
from apps.intake.models import FormAnswer, IntakeSession

# Each form's Debtor 1 signature line and signing date that held a binding before Q6.
# Priya's packet holds all five forms, 122A-2 included.
SIGNING_LINES = {
    "form_101": ["Executed on", "Attorney.Date signed"],
    "form_106dec": ["Debtor1.signature", "Executed on"],
    "form_121": ["Debtor1.signature", "Executed on"],
    "form_122a1": ["Debtor1.sig", "Debtor1.Date signed"],
    "form_122a2": ["Debtor1.sig", "Debtor1.Date signed"],
}

# Boxes on the same form that must still print, so a blank signing line can't come from
# a form that printed nothing, or from an attorney block that was never switched on.
STILL_PRINTS = {
    "form_101": {"Debtor1.First name": "Priya", "Attorney.Printed name": "Ann Lee"},
    "form_106dec": {"Debtor 1": "Priya Sharma"},
    "form_121": {"Debtor1.First name": "Priya"},
    "form_122a1": {"Debtor1.Name": "Priya Sharma"},
    "form_122a2": {"Debtor1.Name": "Priya Sharma"},
}


@cache
def _printed():
    """
    (form_type, full name) → the text Priya's filled forms show there, once she has given
    a signing date and named an attorney. Every box in the filled forms has an entry, so a
    box name that is no box can't pass as blank.
    """
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona="priya", verbosity=0)
    session = IntakeSession.objects.get(user__username="demo_priya")
    for form_type, key, value in [
        ("form_107", "attorney_gate", "yes"),
        ("form_101", "attorney_printed_name", "Ann Lee"),
        ("form_101", "executed_on", "10/14/2026"),
        ("form_101", "attorney_date_signed", "10/14/2026"),
    ]:
        FormAnswer.objects.create(session=session, form_type=form_type, field_key=key, value=value)
    printed = {}
    for form_type in SIGNING_LINES:
        values = build_field_values(form_type, session)
        for widget in read_widgets(PDFFormFiller().fill(form_type, values)):
            shows = printed.setdefault((form_type, widget.full_name), set())
            if widget.value:
                shows.add(widget.value)
    return printed


@pytest.mark.django_db
@pytest.mark.parametrize(
    "form_type,box",
    [(form_type, box) for form_type, boxes in SIGNING_LINES.items() for box in boxes],
)
def test_signature_lines_and_signing_dates_stay_blank_for_wet_ink(form_type, box):
    printed = _printed()
    assert (form_type, box) in printed, f"no box named {box!r} on {form_type}"
    assert printed[(form_type, box)] == set()
    for neighbour, value in STILL_PRINTS[form_type].items():
        assert printed[(form_type, neighbour)] == {value}
```

The test fills Priya's five forms once per process, as tier 3 does, and reads every widget back. Each case requires its box to exist on the filled form, so a misspelt name can't pass as blank, and to show nothing.

- [ ] **Step 2: Run it with tier 2 and watch it fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line -rN apps/forms/tests/test_signing_lines.py apps/forms/tests/test_oracle_tier2.py -q -p no:cacheprovider 2>&1 | tail -12
```

Expected: FAIL — `10 failed, 363 passed, 62 xfailed`. Every one of the ten boxes still prints something. Form 101's two dates print the date the test stored as the filer's answer (`assert {'10/14/2026'} == set()`). The four signature lines print the typed name (`assert {'Priya Sharma'} == set()`). The four other dates print the day the packet was built. Tier 2 still passes, with its 62 listed defects as expected failures.

- [ ] **Step 3: Take the ten signing bindings off**

```bash
git apply <<'PATCH'
diff --git a/data/forms/schemas/form_101.json b/data/forms/schemas/form_101.json
index ec0bebe..f4c3129 100644
--- a/data/forms/schemas/form_101.json
+++ b/data/forms/schemas/form_101.json
@@ -904,23 +904,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Executed on",
-      "type": "text",
-      "source": "asked",
-      "page": 7,
-      "label": "Executed on (Date mm/dd/yyyy)",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_101.executed_on",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "Attorney.Sig",
       "type": "text",
@@ -938,23 +921,6 @@
       "row": null,
       "legal_review": false
     },
-    {
-      "pdf_field": "Attorney.Date signed",
-      "type": "text",
-      "source": "asked",
-      "page": 8,
-      "label": "Date signed (Format mm/dd/yyyy)",
-      "required": false,
-      "conditional_on": "has_attorney",
-      "value": null,
-      "rule": null,
-      "ingest_key": null,
-      "binding": "answer:form_101.attorney_date_signed",
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
     {
       "pdf_field": "Attorney.Printed name",
       "type": "text",
diff --git a/data/forms/schemas/form_106dec.json b/data/forms/schemas/form_106dec.json
index e928721..f4d20c4 100644
--- a/data/forms/schemas/form_106dec.json
+++ b/data/forms/schemas/form_106dec.json
@@ -53,40 +53,6 @@
       "repeat_capacity": null,
       "row": null,
       "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.signature",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Signature of debtor",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "full_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Executed on",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Date signed",
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
     }
   ]
 }
diff --git a/data/forms/schemas/form_121.json b/data/forms/schemas/form_121.json
index a3908c4..44a4cb1 100644
--- a/data/forms/schemas/form_121.json
+++ b/data/forms/schemas/form_121.json
@@ -105,40 +105,6 @@
       "repeat_capacity": null,
       "row": null,
       "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.signature",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Signature of debtor",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "full_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Executed on",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Date signed",
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
     }
   ]
 }
diff --git a/data/forms/schemas/form_122a1.json b/data/forms/schemas/form_122a1.json
index 0a30dcb..568fe98 100644
--- a/data/forms/schemas/form_122a1.json
+++ b/data/forms/schemas/form_122a1.json
@@ -342,40 +342,6 @@
       "repeat_capacity": null,
       "row": null,
       "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.sig",
-      "type": "text",
-      "source": "derived",
-      "page": 3,
-      "label": "Signature of debtor",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "full_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.Date signed",
-      "type": "text",
-      "source": "derived",
-      "page": 3,
-      "label": "Date signed",
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
     }
   ]
 }
diff --git a/data/forms/schemas/form_122a2.json b/data/forms/schemas/form_122a2.json
index be24af2..18124f4 100644
--- a/data/forms/schemas/form_122a2.json
+++ b/data/forms/schemas/form_122a2.json
@@ -206,40 +206,6 @@
       "repeat_capacity": null,
       "row": null,
       "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.sig",
-      "type": "text",
-      "source": "derived",
-      "page": 9,
-      "label": "Signature of Debtor",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "full_name",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debtor1.Date signed",
-      "type": "text",
-      "source": "derived",
-      "page": 9,
-      "label": "Date signed (format mm/dd/yyyy)",
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
     }
   ]
 }
PATCH
```

Each schema loses two field objects and nothing else. A typed name on a signature line is not the filer's signature, and a date printed when the packet was built is not the day they sign it under penalty of perjury (Q6).

- [ ] **Step 4: Pin tier 2's new coverage**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index f41af3a..d5dfb9d 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 411
+ASSERTED_CASES = 401


 def _audit_dir():
PATCH
```

Tier 2's `test_tier2_coverage_changes_only_on_purpose` fails until `ASSERTED_CASES` is 401, ten fewer than before.

- [ ] **Step 5: Run the test and tier 2 again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line -rN apps/forms/tests/test_signing_lines.py apps/forms/tests/test_oracle_tier2.py -q -p no:cacheprovider 2>&1 | tail -12
```

Expected: `363 passed, 62 xfailed`, and no failures. The ten new cases pass, and tier 2 has ten fewer cases, so the passed count is the same as before.

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

Expected: `1841 passed, 116 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  357 passed (357)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

This task changes no page or flow, so the journeys don't run.

- [ ] **Step 7: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_signing_lines.py \
  backend/apps/forms/tests/test_oracle_tier2.py \
  data/forms/schemas/form_101.json \
  data/forms/schemas/form_106dec.json \
  data/forms/schemas/form_121.json \
  data/forms/schemas/form_122a1.json \
  data/forms/schemas/form_122a2.json
git commit -F - <<'MSG'
fix(forms): leave signature lines and signing dates blank for wet ink

The filer signs each form in ink and dates it on the day they sign (Q6).
Ten boxes printed a typed name or a date for them: Form 101 "Executed on"
and "Attorney.Date signed" (the filer's own answers), and the Debtor 1
signature line and signing date on 106Dec, 121, 122A-1 and 122A-2
(full_name, and today_iso's build date). Their field objects are deleted
(Appendix A DEL rows), so each box prints blank.

full_name stays bound on every caption. today_iso keeps one binding,
Schedule I "Supplemental income date", until that box comes off too.

test_signing_lines.py fills Priya's five forms after she gives a signing
date and names an attorney, and requires each of the ten boxes to show
nothing while her name and the attorney's printed name still print.

Clears 0 known-defect entries (none was listed on these boxes).
ASSERTED_CASES 411 -> 401 (-10): tier 2 asserted all ten bindings, and
all ten passed; with no binding left there is no case. Tier 1 loses the
same ten box cases (not pinned).

Refs DIG-73
MSG
git status --short
```

### Task 5: Print the filer's consumer-debts and paid-help answers on every form that asks

_Built and verified as commit `0e70ffe` on `plan/forms-step2b`._

**Files:**

- Create: `backend/apps/forms/tests/test_consumer_debts_and_paid_help.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/form_101.json`
- Modify: `data/forms/schemas/form_103b.json`
- Modify: `data/forms/schemas/form_106dec.json`
- Modify: `data/forms/schemas/form_106sum.json`
- Modify: `data/forms/schemas/form_107.json`

**Interfaces:**

- Consumes:
  - Task 4's schemas. Form 101's `Name of person payed to help file` already reads `answer:form_101.preparer_name` (Appendix A.1) and doesn't change.
  - The `FormAnswer` store (`session`, `form_type`, `field_key`, `value`). An `asked` binding `answer:<form_type>.<field_key>` prints the stored value through the box's `choices`, and the step 2 spec stores lower-case `yes` and `no`. A missing answer prints blank.
  - The UPL guard in `fill_resolver.resolve`: a `legal_review` field fills only from source `asked`.
  - Tier 2's addendum reader (Task 1), which joins a `step2_verification.json` row on (schema, box, whole binding key). The addendum holds Task 3's 7 rows. `ASSERTED_CASES = 401` (Task 4).
  - For the tests: `load_schema` (`apps.forms.schema`), `resolve`, `PDFFormFiller` and `read_widgets`.
- Produces:
  - Nine new checkbox bindings, each `"type": "checkbox"` with source `asked`:
    - `answer:form_101.primarily_consumer_debts`, each with `legal_review: true`: Form 101 `Check Box18` `{"yes": "/Yes", "no": "/No"}`, 106Sum `check7` `{"yes": "/consumer", "no": "/not consumer"}` and 107 `check6` `{"yes": "/yes", "no": "/no"}`.
    - `answer:form_101.paid_non_attorney_preparer`: Form 101 `Check Box26` `{"yes": "/Yes", "no": "/no"}`, 106Dec `check1` and 107 `check30`, both `{"yes": "/yes", "no": "/no"}`.
    - 103B `check_17` from `answer:form_103b.paid_anyone_for_services`, `check_18` from `answer:form_103b.promised_to_pay_for_services` and `check_19` from `answer:form_103b.someone_paid_on_your_behalf`, each `{"yes": "/yes", "no": "/no"}`.
  - Two name boxes re-ruled in place to `answer:form_101.preparer_name`: 106Dec `Name of person payed to help file` (was `presume` with value `""`) and 107 `Name of person agreed to pay` (was `answer:form_107.Name_of_person_agreed_to_pay`, now bound nowhere).
  - `step2_verification.json` with 18 rows (11 new).
  - `ASSERTED_CASES = 410`.
  - `known_defects.json` is unchanged, with 115 entries.
  - Tests in `backend/apps/forms/tests/test_consumer_debts_and_paid_help.py`: `test_the_consumer_debts_answer_ticks_the_same_answer_on_every_form_that_asks` (6 cases), `test_only_the_filers_own_answer_can_tick_consumer_debts` (3), `test_a_filer_who_paid_a_non_lawyer_says_so_and_names_them_on_every_form_that_asks` (3), `test_a_filer_who_paid_no_one_says_no_and_names_no_one` (3), `test_form_107_names_the_helper_the_filer_named_once_for_every_form`, `test_each_form_103b_payment_question_prints_its_own_answer` (3) and `test_a_question_the_filer_has_not_answered_prints_nothing`.

**Decisions already made in this task:**

- The owner's Q7 (§3) decides the consumer-debts boxes: "each filer answers "primarily consumer debts" in step 4. Step 2 binds the answer to 101 `Check Box18`, 106Sum `check7` and 107 `check6`."
- The owner's Q12 (§3) decides the paid-help boxes: "DigniFi is free, so it is not a petition preparer. Each filer answers the forms' own questions in step 4. Step 2 binds two answer sets (§6.3)." The first set is the paid-help answer and the helper's name on 101, 106Dec and 107. The second is 103B lines 17–19, which ask three different things (line 17 counts attorneys too), so each line reads its own key.
- Every `choices` state is the box's own index state, spelled as `export_state()` gives it. Form 101 `Check Box26` really is `/Yes` with a lower-case `/no`. 106Sum's `/not consumer` (index `not#20consumer`) is the first export state with a space in any schema. Tier 1 gains 18 box cases (9 boxes, yes and no), the filler-level proof that each state ticks.
- The three Q7 boxes carry `legal_review: true`, so only the filer's own answer can fill them. `test_only_the_filers_own_answer_can_tick_consumer_debts` pins the flags, not a printed result; the guard itself is tested in `test_fill_resolver.py`. It stays as it is.
- The preparer-name boxes print a stored name whatever the paid-help answer is. The spec binds them without a condition (Q12), and nothing collects the answer yet. Step 4 clears the name on a No when it asks the question.
- 106Dec's name box keeps its label "Petition preparer name". The re-rule changes only its source, value and binding, and nothing prints the label.
- 101 `Check Box19` (16b) and 107 `check6a` and `check6b` stay unbound (§6.3).
- The addendum gains 11 rows, one per Appendix A ADD row. `producer` is the whole binding key, spelled as tier 2's `_binding_key` builds it and compared as written. Each row cites the box's field-index label and Q7 (DIG-121) or Q12. 106Dec `check1` cites the label, not the index tooltip "Any creditors clims secured by property", a template copy error. The two re-ruled name boxes need their rows although each keeps an audit row under its old key: tier 2 joins on (box, key), so without the addendum they would go unasserted.
- `ASSERTED_CASES` goes from 401 to 410 (+9), measured from tier 2's collected cases. The nine new boxes are asserted through the addendum (+9). The two re-ruled name boxes trade their old-key cases, both passing, for addendum cases under the new key (−2, +2).
- No known-defect entry is deleted: none is listed on these boxes.
- The answer key `form_107.Name_of_person_agreed_to_pay` is now bound nowhere, and nothing in the app writes it. Step 4 asks the helper's name once, as `form_101.preparer_name`.
- Answer values are not checked on write yet (DIG-170). A stored `y`, `true` or `1` on one of these boxes raises `UnmappedChoice`. Nothing in the app writes these five keys today.

- [ ] **Step 1: Write the failing tests**

```python file=backend/apps/forms/tests/test_consumer_debts_and_paid_help.py
"""
The filer's answers about consumer debts and paid help print on every form that asks
(step 2 spec §3 Q7 and Q12, §6.3).

Business intent: whether the debts are primarily consumer debts (Form 101 line 16a,
106Sum line 7, 107 line 6) and whether the filer paid someone who is not a lawyer to
help with the forms (101 Part 7, 106Dec, 107 Part 12, with that person's name) are the
filer's own sworn answers. DigniFi never answers them. Each form prints exactly what
the filer said, all of them say the same, and a question the filer hasn't answered
stays blank. Form 103B lines 17-19 ask three different payment questions, and each
prints its own answer.
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
from apps.intake.models import DebtorInfo, FormAnswer, IncomeInfo, IntakeSession

User = get_user_model()

# Form → (box, state its "yes" ticks, state its "no" ticks), each state from the index.
CONSUMER_DEBTS = {
    "form_101": ("Check Box18", "/Yes", "/No"),
    "form_106sum": ("check7", "/consumer", "/not consumer"),
    "form_107": ("check6", "/yes", "/no"),
}
PAID_HELP = {
    "form_101": ("Check Box26", "/Yes", "/no"),
    "form_106dec": ("check1", "/yes", "/no"),
    "form_107": ("check30", "/yes", "/no"),
}
HELPER_NAME = {
    "form_101": "Name of person payed to help file",
    "form_106dec": "Name of person payed to help file",
    "form_107": "Name of person agreed to pay",
}
# Form 103B line → (its answer key, its box).
PAYMENT_LINES = {
    "17": ("paid_anyone_for_services", "check_17"),
    "18": ("promised_to_pay_for_services", "check_18"),
    "19": ("someone_paid_on_your_behalf", "check_19"),
}


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="filer_answers", password="pass")
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
    # 106Sum line 8 prints CMI, which needs income entered by source.
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1200.00"))
    return session


def _answer(session, key, value, form_type="form_101"):
    FormAnswer.objects.create(session=session, form_type=form_type, field_key=key, value=value)


def _filled(session, form_type):
    """Box → what a viewer sees in it once the form is filled: the ticked states, or the text."""
    values = resolve(load_schema(form_type), session)
    shows = {}
    for widget in read_widgets(PDFFormFiller().fill(form_type, values)):
        seen = shows.setdefault(widget.full_name, set())
        if widget.state is not None:
            if widget.state != "/Off":
                seen.add(widget.state)
        elif widget.value:
            seen.add(widget.value)
    return shows


@pytest.mark.parametrize("answer", ["yes", "no"])
@pytest.mark.parametrize("form_type", CONSUMER_DEBTS)
def test_the_consumer_debts_answer_ticks_the_same_answer_on_every_form_that_asks(
    session, form_type, answer
):
    _answer(session, "primarily_consumer_debts", answer)
    box, yes, no = CONSUMER_DEBTS[form_type]
    assert _filled(session, form_type).get(box) == {yes if answer == "yes" else no}


@pytest.mark.parametrize("form_type", CONSUMER_DEBTS)
def test_only_the_filers_own_answer_can_tick_consumer_debts(form_type):
    # The answer decides whether the means test applies, and DigniFi never gives it for
    # the filer: the box is held for legal review, which fills it only from an answer.
    box = CONSUMER_DEBTS[form_type][0]
    field = next((f for f in load_schema(form_type).fields if f.pdf_field == box), None)
    assert field is not None, f"{box!r} is not bound on {form_type}"
    assert (field.source, field.legal_review) == ("asked", True)


@pytest.mark.parametrize("form_type", PAID_HELP)
def test_a_filer_who_paid_a_non_lawyer_says_so_and_names_them_on_every_form_that_asks(
    session, form_type
):
    _answer(session, "paid_non_attorney_preparer", "yes")
    _answer(session, "preparer_name", "Pat Helper")
    box, yes, _ = PAID_HELP[form_type]
    filled = _filled(session, form_type)
    assert filled.get(box) == {yes}
    assert filled.get(HELPER_NAME[form_type]) == {"Pat Helper"}


@pytest.mark.parametrize("form_type", PAID_HELP)
def test_a_filer_who_paid_no_one_says_no_and_names_no_one(session, form_type):
    _answer(session, "paid_non_attorney_preparer", "no")
    box, _, no = PAID_HELP[form_type]
    filled = _filled(session, form_type)
    assert filled.get(box) == {no}
    assert filled.get(HELPER_NAME[form_type]) == set()


def test_form_107_names_the_helper_the_filer_named_once_for_every_form(session):
    # A separate Form 107 answer could name someone the petition doesn't.
    _answer(session, "Name_of_person_agreed_to_pay", "Someone Else", form_type="form_107")
    _answer(session, "preparer_name", "Pat Helper")
    assert _filled(session, "form_107").get("Name of person agreed to pay") == {"Pat Helper"}


@pytest.mark.parametrize("yes_line", PAYMENT_LINES)
def test_each_form_103b_payment_question_prints_its_own_answer(session, yes_line):
    # Lines 17-19 ask three different things, so a "yes" to one ticks Yes on that line only.
    for line, (key, _) in PAYMENT_LINES.items():
        _answer(session, key, "yes" if line == yes_line else "no", form_type="form_103b")
    filled = _filled(session, "form_103b")
    assert {line: filled.get(box) for line, (_, box) in PAYMENT_LINES.items()} == {
        line: {"/yes" if line == yes_line else "/no"} for line in PAYMENT_LINES
    }


def test_a_question_the_filer_has_not_answered_prints_nothing(session):
    boxes = {
        "form_101": ["Check Box18", "Check Box26", HELPER_NAME["form_101"]],
        "form_103b": [box for _, box in PAYMENT_LINES.values()],
        "form_106dec": ["check1", HELPER_NAME["form_106dec"]],
        "form_106sum": ["check7"],
        "form_107": ["check6", "check30", HELPER_NAME["form_107"]],
    }
    for form_type, names in boxes.items():
        filled = _filled(session, form_type)
        # A box name that is no box on the form reads None here, not blank.
        assert {box: filled.get(box) for box in names} == {box: set() for box in names}
```

Each test stores the filer's answers as `FormAnswer` rows, resolves the form, fills the real template and reads every widget back. A box shows its ticked state, or its text. A box name that is no box on the form reads `None`, never blank. The fixture adds an `IncomeInfo` because 106Sum line 8 (`cmi`) needs income entered by source.

- [ ] **Step 2: Run them with tier 2 and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line -rN apps/forms/tests/test_consumer_debts_and_paid_help.py apps/forms/tests/test_oracle_tier2.py -q -p no:cacheprovider 2>&1 | tail -21
```

Expected: FAIL — `19 failed, 354 passed, 62 xfailed`. No box ticks for any answer (`assert set() == {'/not consumer'}`), and Form 107 prints the old Form 107-only answer instead of the shared name (`assert {'Someone Else'} == {'Pat Helper'}`). The three legal-review cases find no field: `'Check Box18' is not bound on form_101`. The one test that passes, the unanswered-question test, passes because the boxes are still unbound.

- [ ] **Step 3: Bind the answers on the five schemas**

```bash
git apply <<'PATCH'
diff --git a/data/forms/schemas/form_101.json b/data/forms/schemas/form_101.json
index f4c3129..7f63a27 100644
--- a/data/forms/schemas/form_101.json
+++ b/data/forms/schemas/form_101.json
@@ -1145,6 +1145,27 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "Check Box18",
+      "type": "checkbox",
+      "source": "asked",
+      "choices": {
+        "yes": "/Yes",
+        "no": "/No"
+      },
+      "page": 7,
+      "label": "Are your debts primarily consumer debts?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": null,
+      "ingest_key": null,
+      "binding": "answer:form_101.primarily_consumer_debts",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": true
+    },
     {
       "pdf_field": "Check Box20",
       "type": "checkbox",
@@ -1255,6 +1276,27 @@
       "repeat_capacity": null,
       "row": null,
       "legal_review": false
+    },
+    {
+      "pdf_field": "Check Box26",
+      "type": "checkbox",
+      "source": "asked",
+      "choices": {
+        "yes": "/Yes",
+        "no": "/no"
+      },
+      "page": 9,
+      "label": "Did you pay or agree to pay someone who is not an attorney to help you fill out your bankruptcy forms?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": null,
+      "ingest_key": null,
+      "binding": "answer:form_101.paid_non_attorney_preparer",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
     }
   ]
 }
diff --git a/data/forms/schemas/form_103b.json b/data/forms/schemas/form_103b.json
index 7fc7c1b..3f833b8 100644
--- a/data/forms/schemas/form_103b.json
+++ b/data/forms/schemas/form_103b.json
@@ -104,6 +104,69 @@
       "repeat_capacity": null,
       "row": null,
       "legal_review": false
+    },
+    {
+      "pdf_field": "check_17",
+      "type": "checkbox",
+      "source": "asked",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 3,
+      "label": "Have you paid anyone for services for this case, including filling out this application, the bankruptcy filing package, or the schedules?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": null,
+      "ingest_key": null,
+      "binding": "answer:form_103b.paid_anyone_for_services",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "check_18",
+      "type": "checkbox",
+      "source": "asked",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 3,
+      "label": "Have you promised to pay or do you expect to pay someone for services for your bankruptcy case?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": null,
+      "ingest_key": null,
+      "binding": "answer:form_103b.promised_to_pay_for_services",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "check_19",
+      "type": "checkbox",
+      "source": "asked",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 3,
+      "label": "Has anyone paid someone on your behalf for services for this case?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": null,
+      "ingest_key": null,
+      "binding": "answer:form_103b.someone_paid_on_your_behalf",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
     }
   ]
 }
diff --git a/data/forms/schemas/form_106dec.json b/data/forms/schemas/form_106dec.json
index f4d20c4..9f8b19f 100644
--- a/data/forms/schemas/form_106dec.json
+++ b/data/forms/schemas/form_106dec.json
@@ -37,18 +37,39 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "check1",
+      "type": "checkbox",
+      "source": "asked",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 1,
+      "label": "Did you pay or agree to pay someone who is NOT an attorney to help you fill out bankruptcy forms?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": null,
+      "ingest_key": null,
+      "binding": "answer:form_101.paid_non_attorney_preparer",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "Name of person payed to help file",
       "type": "text",
-      "source": "presume",
+      "source": "asked",
       "page": 1,
       "label": "Petition preparer name",
       "required": false,
       "conditional_on": null,
-      "value": "",
+      "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": null,
+      "binding": "answer:form_101.preparer_name",
       "repeat": null,
       "repeat_capacity": null,
       "row": null,
diff --git a/data/forms/schemas/form_106sum.json b/data/forms/schemas/form_106sum.json
index 9202dc4..85f58f7 100644
--- a/data/forms/schemas/form_106sum.json
+++ b/data/forms/schemas/form_106sum.json
@@ -173,6 +173,27 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "check7",
+      "type": "checkbox",
+      "source": "asked",
+      "choices": {
+        "yes": "/consumer",
+        "no": "/not consumer"
+      },
+      "page": 2,
+      "label": "What kind of debt do you have?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": null,
+      "ingest_key": null,
+      "binding": "answer:form_101.primarily_consumer_debts",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": true
+    },
     {
       "pdf_field": "8",
       "type": "text",
diff --git a/data/forms/schemas/form_107.json b/data/forms/schemas/form_107.json
index 343e048..1d05d6d 100644
--- a/data/forms/schemas/form_107.json
+++ b/data/forms/schemas/form_107.json
@@ -755,6 +755,27 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "check6",
+      "type": "checkbox",
+      "source": "asked",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 3,
+      "label": "Are either Debtor 1’s or Debtor 2’s debts primarily consumer debts?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": null,
+      "ingest_key": null,
+      "binding": "answer:form_101.primarily_consumer_debts",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": true
+    },
     {
       "pdf_field": "Creditors Name 1",
       "type": "text",
@@ -7508,6 +7529,27 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "check30",
+      "type": "checkbox",
+      "source": "asked",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 12,
+      "label": "Did you pay or agree to pay someone who is not an attorney to help you fill out bankruptcy forms?",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": null,
+      "ingest_key": null,
+      "binding": "answer:form_101.paid_non_attorney_preparer",
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "Name of person agreed to pay",
       "type": "text",
@@ -7519,7 +7561,7 @@
       "value": null,
       "rule": null,
       "ingest_key": null,
-      "binding": "answer:form_107.Name_of_person_agreed_to_pay",
+      "binding": "answer:form_101.preparer_name",
       "repeat": null,
       "repeat_capacity": null,
       "row": null,
PATCH
```

Whether the debts are primarily consumer debts and whether the filer paid someone who is not a lawyer are the filer's own sworn answers, so each box prints exactly what the filer said, and every form says the same. The nine new objects sit beside their neighbours on the same page, and the two name boxes are edited in place (E006).

- [ ] **Step 4: Record the eleven placements, and pin tier 2's new coverage**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index d5dfb9d..2268628 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 401
+ASSERTED_CASES = 410


 def _audit_dir():
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index f258e63..59383bb 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -68,5 +68,115 @@
     "status": "confirmed",
     "correct_target": "Debtor1.Contact phone_2",
     "evidence": "Field index: Debtor1.Contact phone_2 p9 Part 7 'For you if you are filing this bankruptcy without an attorney: Contact phone' (adjudicated). The audit's confirmed note on this box: the debtor's own phone, which the phone rule gives; the preparer's phone belongs on Form 119. Step 2 spec §6.4: Contact phone gets the phone, and Cell phone stays blank because the wizard never asks whether the number is a cell."
+  },
+  {
+    "schema": "form_101",
+    "pdf_field": "Check Box18",
+    "producer": "asked:answer:form_101.primarily_consumer_debts",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Check Box18",
+    "evidence": "Field index: Check Box18 p7 line 16a 'Are your debts primarily consumer debts?', states /No (sampled_ok) and /Yes (vision_agreed). form_101.unbound.json names this box for the answer: 'the Check Box16 constant was evidently meant for it'. Owner's answer Q7 (DIG-121; step 2 spec §3, §6.3): each filer answers 'primarily consumer debts', and the answer prints on 101 Check Box18, 106Sum check7 and 107 check6, marked for legal review."
+  },
+  {
+    "schema": "form_101",
+    "pdf_field": "Check Box26",
+    "producer": "asked:answer:form_101.paid_non_attorney_preparer",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Check Box26",
+    "evidence": "Field index: Check Box26 p9 Part 7 'For you if you are filing this bankruptcy without an attorney: Did you pay or agree to pay someone who is not an attorney to help you fill out your bankruptcy forms?', states /no ('No') and /Yes ('Yes. Name of Person'), adjudicated. Owner's answer Q12 (step 2 spec §3, §6.3): DigniFi is free, so it is not a petition preparer; each filer answers the form's own question, and the paid-help answer prints on 101 Check Box26, 106Dec check1 and 107 check30."
+  },
+  {
+    "schema": "form_103b",
+    "pdf_field": "check_17",
+    "producer": "asked:answer:form_103b.paid_anyone_for_services",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check_17",
+    "evidence": "Field index: check_17 p3 line 17 'Have you paid anyone for services for this case, including filling out this application, the bankruptcy filing package, or the schedules?', states /no ('No', sampled_ok) and /yes ('Yes. Whom did you pay?', adjudicated). Owner's answer Q12 (step 2 spec §3, §6.3): 103B lines 17-19 ask different things from the paid-help question (line 17 counts attorneys too), so each line has its own answer."
+  },
+  {
+    "schema": "form_103b",
+    "pdf_field": "check_18",
+    "producer": "asked:answer:form_103b.promised_to_pay_for_services",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check_18",
+    "evidence": "Field index: check_18 p3 line 18 'Have you promised to pay or do you expect to pay someone for services for your bankruptcy case?', states /no ('No') and /yes ('Yes. Whom do you expect to pay?'), adjudicated. Owner's answer Q12 (step 2 spec §3, §6.3): 103B lines 17-19 ask different things from the paid-help question (line 17 counts attorneys too), so each line has its own answer."
+  },
+  {
+    "schema": "form_103b",
+    "pdf_field": "check_19",
+    "producer": "asked:answer:form_103b.someone_paid_on_your_behalf",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check_19",
+    "evidence": "Field index: check_19 p3 line 19 'Has anyone paid someone on your behalf for services for this case?', states /no ('No') and /yes ('Yes. Who was paid on your behalf?'), adjudicated. Owner's answer Q12 (step 2 spec §3, §6.3): 103B lines 17-19 ask different things from the paid-help question (line 17 counts attorneys too), so each line has its own answer."
+  },
+  {
+    "schema": "form_106dec",
+    "pdf_field": "check1",
+    "producer": "asked:answer:form_101.paid_non_attorney_preparer",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check1",
+    "evidence": "Field index: check1 p1 'Did you pay or agree to pay someone who is NOT an attorney to help you fill out bankruptcy forms?', states /no ('No') and /yes ('Yes.'), adjudicated. The index tooltip 'Any creditors clims secured by property' is a template copy error; the label and option text decide the box. Owner's answer Q12 (step 2 spec §3, §6.3): DigniFi is free, so it is not a petition preparer; each filer answers the form's own question, and the paid-help answer prints on 101 Check Box26, 106Dec check1 and 107 check30."
+  },
+  {
+    "schema": "form_106dec",
+    "pdf_field": "Name of person payed to help file",
+    "producer": "asked:answer:form_101.preparer_name",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Name of person payed to help file",
+    "evidence": "Field index: Name of person payed to help file p1 'Yes. Name of person (non-attorney preparer)', adjudicated. The audit judged this box under presume: (needs_legal_review: whether DigniFi is a § 110 preparer). Owner's answer Q12 (step 2 spec §3, §6.3): the filer names their paid helper once, in answer:form_101.preparer_name, which prints on the three name boxes (101, 106Dec, 107)."
+  },
+  {
+    "schema": "form_106sum",
+    "pdf_field": "check7",
+    "producer": "asked:answer:form_101.primarily_consumer_debts",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check7",
+    "evidence": "Field index: check7 p2 line 7 'What kind of debt do you have?', states /consumer ('Your debts are primarily consumer debts') and /not consumer (on_state not#20consumer), both sampled_ok. Yes ticks /consumer and No ticks /not consumer. Owner's answer Q7 (DIG-121; step 2 spec §3, §6.3): each filer answers 'primarily consumer debts', and the answer prints on 101 Check Box18, 106Sum check7 and 107 check6, marked for legal review."
+  },
+  {
+    "schema": "form_107",
+    "pdf_field": "check6",
+    "producer": "asked:answer:form_101.primarily_consumer_debts",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check6",
+    "evidence": "Field index: check6 p3 line 6 'Are either Debtor 1’s or Debtor 2’s debts primarily consumer debts?', states /no ('No. Neither Debtor 1 nor Debtor 2 has primarily consumer debts.') and /yes ('Yes. Debtor 1 or Debtor 2 or both have primarily consumer debts.'), sampled_ok. check6a and check6b stay blank. Owner's answer Q7 (DIG-121; step 2 spec §3, §6.3): each filer answers 'primarily consumer debts', and the answer prints on 101 Check Box18, 106Sum check7 and 107 check6, marked for legal review."
+  },
+  {
+    "schema": "form_107",
+    "pdf_field": "check30",
+    "producer": "asked:answer:form_101.paid_non_attorney_preparer",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check30",
+    "evidence": "Field index: check30 p12 'Did you pay or agree to pay someone who is not an attorney to help you fill out bankruptcy forms?', states /no ('No') and /yes ('Yes.'), adjudicated. Owner's answer Q12 (step 2 spec §3, §6.3): DigniFi is free, so it is not a petition preparer; each filer answers the form's own question, and the paid-help answer prints on 101 Check Box26, 106Dec check1 and 107 check30."
+  },
+  {
+    "schema": "form_107",
+    "pdf_field": "Name of person agreed to pay",
+    "producer": "asked:answer:form_101.preparer_name",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Name of person agreed to pay",
+    "evidence": "Field index: Name of person agreed to pay p12 'Yes. Name of person (attach Official Form 119)' (tooltip 'Name of person to help fill out forms (not an attorney)'), adjudicated. The audit's row judged a separate answer, form_107.Name_of_person_agreed_to_pay. Owner's answer Q12 (step 2 spec §3, §6.3): the filer names their paid helper once, in answer:form_101.preparer_name, which prints on the three name boxes (101, 106Dec, 107)."
   }
 ]
PATCH
```

Every ADD row gets its addendum row in the commit that binds it (§7.4), and `ASSERTED_CASES` names the new count.

- [ ] **Step 5: Run the tests and tier 2 again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line -rN apps/forms/tests/test_consumer_debts_and_paid_help.py apps/forms/tests/test_oracle_tier2.py -q -p no:cacheprovider 2>&1 | tail -21
```

Expected: `382 passed, 62 xfailed`, and no failures.

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

Expected: `1888 passed, 116 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  357 passed (357)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

This task changes no page or flow, and no seed writes these answers, so the journeys don't run.

- [ ] **Step 7: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_consumer_debts_and_paid_help.py \
  backend/apps/forms/tests/test_oracle_tier2.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/form_101.json \
  data/forms/schemas/form_103b.json \
  data/forms/schemas/form_106dec.json \
  data/forms/schemas/form_106sum.json \
  data/forms/schemas/form_107.json
git commit -F - <<'MSG'
fix(forms): print the filer's consumer-debts and paid-help answers on every form that asks

Whether the debts are primarily consumer debts (Q7) and whether the filer
paid someone who is not a lawyer to help with the forms (Q12) are the
filer's own answers. Step 2 binds them; step 4 asks them (step 2 spec §6.3,
Appendix A). Each prints only what the filer said, and a question not yet
answered stays blank.

- answer:form_101.primarily_consumer_debts ticks 101 Check Box18 (line
  16a, /Yes or /No), 106Sum check7 (line 7, /consumer or /not consumer)
  and 107 check6 (line 6, /yes or /no). All three are marked
  legal_review, so only an asked answer can fill them.
- answer:form_101.paid_non_attorney_preparer ticks 101 Check Box26 (/Yes
  or lower-case /no, as the index spells them), 106Dec check1 and 107
  check30.
- answer:form_101.preparer_name, already on 101's name box, now also
  prints on 106Dec "Name of person payed to help file" (re-ruled in place
  from presume:) and 107 "Name of person agreed to pay" (re-ruled in place
  from its own answer:form_107.Name_of_person_agreed_to_pay). The filer
  names the helper once, and the three forms agree.
- 103B lines 17-19 ask three different payment questions, so each box
  reads its own answer: check_17 paid_anyone_for_services, check_18
  promised_to_pay_for_services, check_19 someone_paid_on_your_behalf.

Every choices state is read from the box's own index states. Tier 1 adds
18 box cases (9 boxes, yes and no). They are the proof that the filler
ticks each state, /not consumer included.

step2_verification.json gains 11 rows, one per ADD box. Each cites the
box's field-index label and Q7 (DIG-121) or Q12.

New test file: test_consumer_debts_and_paid_help.py. One FormAnswer row
per answer must reach every box that reads it, so a misspelt key prints
blank and fails the test. Each of 103B's lines answers "yes" in turn while
the others answer "no", which catches a swapped key. No existing test
needed changing.

Clears 0 known-defect entries (none was listed on these boxes; 115
remain).

ASSERTED_CASES 401 -> 410 (+9):
- +9 for the nine new boxes, asserted through the addendum.
- The two re-ruled name boxes trade their old-key cases for addendum
  cases under the new key (-2 +2). Both old cases were passing.

Refs DIG-121, DIG-76, DIG-78, DIG-79
MSG
git status --short
```

### Task 6: Print the fee-waiver answers where Form 103B's lines ask, never an unanswered No

_Built and verified as commit `d116c9e` on `plan/forms-step2b`._

**Files:**

- Create: `backend/apps/forms/tests/test_form_103b_answers.py`
- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_api_readback.py`
- Modify: `backend/apps/forms/tests/test_form_103b_schema.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `backend/apps/intake/serializers.py`
- Modify: `backend/apps/intake/tests/test_fee_waiver_views.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/form_103b.json`

**Interfaces:**

- Consumes:
  - 2a's `FeeWaiverApplication` columns: `monthly_take_home_pay` (encrypted decimal, `null=True`), `receives_noncash_assistance` (`BooleanField(null=True)`, empty until answered) and `benefit_types` (a JSON list, the "What kind?" answer). The old `monthly_income`, `monthly_expenses` and `receives_public_benefits` columns stay but are no longer written.
  - `FeeWaiverApplicationSerializer` (`backend/apps/intake/serializers.py`), whose `validate()` already drops any kind sent with a No and requires a kind under a Yes, behind `POST /api/intake/fee-waiver/` and `PATCH /api/intake/fee-waiver/<id>/`. In `test_fee_waiver_views.py`, the `setup` fixture (client, session, user) and `_application(session, **answers)`, a complete application as the page sends it.
  - In `derivations.py`: `_schedule_j_total_expenses` (Schedule J line 22c, `ExpenseInfo.calculate_total_monthly_expenses()`), `full_name`, `total_debts` and `_fmt`.
  - Task 5's `form_103b.json` (`check_17`–`check_19`), the addendum's 18 rows, `ASSERTED_CASES = 410`, and `known_defects.json` with 115 entries.
- Produces:
  - `FeeWaiverApplicationSerializer.receives_noncash_assistance = serializers.BooleanField(allow_null=True)`. `validate()` raises `{"receives_noncash_assistance": [<the field's required message>]}` when the answer is empty on create, when a request sends it empty, and when kinds are sent while the answer stays empty.
  - Rules in `DERIVATIONS`:
    - `fee_waiver_monthly_income`: `monthly_take_home_pay` as 0.00-format text, `""` when it is NULL or there is no application.
    - `fee_waiver_monthly_expenses`: now `_schedule_j_total_expenses`. The function `_fee_waiver_monthly_expenses` is deleted.
    - `fee_waiver_noncash_assistance` (new): `"yes"`, `"no"` or `""`.
    - `fee_waiver_benefit_types` (new): `", ".join(benefit_types)` under a Yes, else `""`.
  - `form_103b.json` (9 → 14 fields):
    - `You`: constant `"true"`, `{"true": "/On"}`.
    - `undefined_2`, `undefined_4` and `undefined_6`: `derived:fee_waiver_monthly_income`.
    - `check 3`: `derived:fee_waiver_noncash_assistance`, `{"yes": "/yes", "no": "/no"}`.
    - `3 type`: `derived:fee_waiver_benefit_types`.
    - `undefined_7`: `derived:fee_waiver_monthly_expenses`.
    - `Debtor.Name1`: `derived:full_name`.
    - `4 type`, `5 Type` and `Amount you owe` are unbound.
  - `step2_verification.json` with 24 rows (6 new), `ASSERTED_CASES = 415`, and `known_defects.json` with 112 entries.
  - Tests:
    - In `test_fee_waiver_views.py`: `ENCODINGS`, `_send(client, method, url, payload, encoding)`, `test_an_application_that_does_not_answer_non_cash_help_is_refused` (6 cases), `test_a_form_encoded_application_keeps_the_answer_it_gives` (4), `test_a_kind_of_help_needs_a_yes_on_an_application_saved_before_the_question` (3), `test_an_application_saved_before_the_question_can_still_be_changed` and `test_an_answer_given_cannot_be_taken_back_to_no_answer` (2).
    - In `backend/apps/forms/tests/test_form_103b_answers.py`: `test_line_2_prints_take_home_pay_for_you_the_subtotal_and_the_family_total`, `test_take_home_pay_never_given_prints_blank_not_zero`, `test_take_home_pay_typed_as_zero_prints_zero`, `test_line_3_prints_the_filers_own_answer_about_non_cash_help` (3 cases), `test_line_6_is_the_monthly_expense_total_schedule_j_prints`, `test_line_1_counts_the_filer`, `test_pages_2_and_3_are_headed_with_the_filers_name` and `test_part_3_stays_blank_because_schedule_a_b_is_attached`.

**Decisions already made in this task:**

- The owner's answers decide line 2 and line 3. Q10: "take-home pay, never pre-filled." Q11: "a Yes/No question in the form's own words, with "What kind?"." The rest of the form follows §6.4's wiring list.
- K-1 (DIG-193) lands in this commit, before line 3 prints anything. Line 3 prints the stored answer as a sworn Yes or No, so the server keeps an answer only when the filer gave it:
  - `allow_null=True` switches DRF's `default_empty_html` from `False` to `None`. A form-encoded or multipart create that leaves the answer out reaches `validate()` as empty instead of being stored as No.
  - `validate()` refuses an empty answer on create in every encoding: JSON null, a missing form field or a blank one. The refusal reuses the field's own DRF `required` message, keyed on `receives_noncash_assistance`, the same shape as a JSON omission.
  - An answer sent empty on a PATCH is refused too. Without that check, `allow_null` would let a PATCH erase a sworn answer and leave its kinds behind.
  - "Kinds of help need a Yes" is read narrowly. A No still drops any kind sent with it and returns 201, as 2a's `test_a_no_to_non_cash_help_keeps_no_kind` and `test_changing_the_answer_to_no_later_drops_the_kind` require. The 400 is for kinds sent while the answer stays empty, which only a PATCH of a row saved before the question can reach. Any other change to such a row still saves.
- `fee_waiver_monthly_income` reads take-home pay and prints blank when it was never given, and 0.00 when the filer typed 0 (B2). The old body read `monthly_income`, which 2a stopped writing, through a bare `except`, so `4 type` printed 0.00 for every waiver filer.
- `fee_waiver_monthly_expenses` keeps its key, so the moved-here join asserts `undefined_7`. The key now points at `_schedule_j_total_expenses`, so 103B line 6 and Schedule J line 22c are one figure by construction. Line 6 is a total, so it prints even at $0 (§6.1).
- `fee_waiver_noncash_assistance` returns exactly `yes`, `no` or `""`. `check 3`'s `choices` has two keys, so any other value would raise `UnmappedChoice`.
- `fee_waiver_benefit_types` joins the kinds with ", ", as the fee-waiver page shows them; the spec names no joiner. It prints only under a Yes. The test's No and empty-answer rows store a kind directly through the ORM, past the serializer, so they fail if the guard goes.
- `You` is the constant string `"true"` with `{"true": "/On"}`. `undefined_3` ("Your spouse") and `undefined_5` (the non-cash subtraction) stay unbound (§6.3, Q10).
- `Debtor.Name1` is one field with two widgets, the captions of pages 2 and 3, so it gets one binding. Its tooltip, "Judge's Signature", is a template copy error; its position and label make it the caption.
- `Amount you owe` (line 15) loses `total_debts`, and Part 3 stays blank: the form says to attach Schedule A/B instead, and every packet has it (OQ-17). `total_debts` stays bound on 106Sum `4`, so no rule loses its last binding.
- The addendum gains 6 rows, one per ADD box (`You`, `undefined_2`, `undefined_4`, `check 3`, `3 type`, `Debtor.Name1`). Each cites the box's index label and Q10, Q11 or §6.4. The MOVED boxes `undefined_6` and `undefined_7` need none: the moved-here join asserts them from `verification.json`'s confirmed rows on `4 type` and `5 Type`.
- `ASSERTED_CASES` goes from 410 to 415 (+5), measured from tier 2's collected cases: −3 for the deleted bindings on `4 type`, `5 Type` and `Amount you owe` (all xfails), +6 for the addendum rows and +2 for `undefined_6` and `undefined_7` through moved-here.
- Exactly 3 known-defect entries are deleted, all tier 2 `wrong_box` under DIG-78, orphaned by the deleted bindings: `form_103b` `4 type` (`derived:fee_waiver_monthly_income`), `5 Type` (`derived:fee_waiver_monthly_expenses`) and `Amount you owe` (`derived:total_debts`). 112 entries remain.
- CLAUDE.md's fee-waiver gotcha has two sentences that are false from this commit on. Task 18 rewrites them; leave CLAUDE.md here.
- Two older defects are left as they are. `cannot_pay_full` and `cannot_pay_installments` still store False when a form-encoded create leaves them out, but neither prints on any form. `_schedule_j_total_expenses` returns 0.00 without an `ExpenseInfo`, which a completed intake always has.

- [ ] **Step 1: Write the failing tests for an answer the filer never gave**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/tests/test_fee_waiver_views.py b/backend/apps/intake/tests/test_fee_waiver_views.py
index 1d38002..7d80d68 100644
--- a/backend/apps/intake/tests/test_fee_waiver_views.py
+++ b/backend/apps/intake/tests/test_fee_waiver_views.py
@@ -1,4 +1,5 @@
 from decimal import Decimal
+from urllib.parse import urlencode

 import pytest
 from django.db import connection
@@ -353,6 +354,119 @@ def test_the_old_income_expense_and_benefit_answers_are_no_longer_written(setup)
     )


+# ── An answer the filer never gave (DIG-193) ──────────────────────────
+#
+# Form 103B line 3 prints the stored answer as a sworn Yes or No, so the server stores one
+# only when the filer gave it, whatever the encoding, and keeps no kind of help without a Yes.
+
+ENCODINGS = ["json", "multipart", "urlencoded"]
+
+
+def _send(client, method, url, payload, encoding):
+    if encoding == "json":
+        return getattr(client, method)(url, payload, format="json")
+    # A form can't carry null: a question left unanswered is missing from the body.
+    form = {key: value for key, value in payload.items() if value is not None}
+    if encoding == "multipart":
+        return getattr(client, method)(url, form, format="multipart")
+    return getattr(client, method)(
+        url, urlencode(form, doseq=True), content_type="application/x-www-form-urlencoded"
+    )
+
+
+@pytest.mark.parametrize(
+    ("encoding", "sent"),
+    [
+        ("json", "left out"),
+        ("json", None),
+        ("multipart", "left out"),
+        ("multipart", ""),
+        ("urlencoded", "left out"),
+        ("urlencoded", ""),
+    ],
+)
+def test_an_application_that_does_not_answer_non_cash_help_is_refused(setup, encoding, sent):
+    client, session, _ = setup
+    payload = _application(session, receives_noncash_assistance=sent)
+    if sent == "left out":
+        del payload["receives_noncash_assistance"]
+
+    resp = _send(client, "post", "/api/intake/fee-waiver/", payload, encoding)
+
+    assert resp.status_code == 400
+    assert "receives_noncash_assistance" in resp.json()
+    assert not FeeWaiverApplication.objects.filter(session=session).exists()
+
+
+@pytest.mark.parametrize("encoding", ["multipart", "urlencoded"])
+@pytest.mark.parametrize(("answer", "kinds"), [(False, []), (True, ["SNAP (food stamps)"])])
+def test_a_form_encoded_application_keeps_the_answer_it_gives(setup, encoding, answer, kinds):
+    client, session, _ = setup
+    payload = _application(session, receives_noncash_assistance=answer, benefit_types=kinds)
+
+    resp = _send(client, "post", "/api/intake/fee-waiver/", payload, encoding)
+
+    assert resp.status_code == 201, resp.json()
+    fw = FeeWaiverApplication.objects.get(session=session)
+    assert (fw.receives_noncash_assistance, fw.benefit_types) == (answer, kinds)
+
+
+def _saved_before_the_question(session):
+    """An application saved before the page asked take-home pay and non-cash help."""
+    return FeeWaiverApplication.objects.create(
+        session=session, household_size=2, monthly_income=Decimal("1200.00")
+    )
+
+
+@pytest.mark.parametrize("encoding", ENCODINGS)
+def test_a_kind_of_help_needs_a_yes_on_an_application_saved_before_the_question(setup, encoding):
+    client, session, _ = setup
+    fw = _saved_before_the_question(session)
+
+    resp = _send(
+        client, "patch", f"/api/intake/fee-waiver/{fw.id}/", {"benefit_types": ["SNAP"]}, encoding
+    )
+
+    fw.refresh_from_db()
+    assert resp.status_code == 400
+    assert (fw.receives_noncash_assistance, fw.benefit_types) == (None, [])
+
+
+def test_an_application_saved_before_the_question_can_still_be_changed(setup):
+    client, session, _ = setup
+    fw = _saved_before_the_question(session)
+
+    resp = client.patch(f"/api/intake/fee-waiver/{fw.id}/", {"household_size": 4}, format="json")
+
+    fw.refresh_from_db()
+    assert resp.status_code == 200
+    assert (fw.household_size, fw.receives_noncash_assistance) == (4, None)
+
+
+@pytest.mark.parametrize(("encoding", "sent"), [("json", None), ("urlencoded", "")])
+def test_an_answer_given_cannot_be_taken_back_to_no_answer(setup, encoding, sent):
+    # The filer answered line 3; an empty answer would print it blank and leave the kind stored.
+    client, session, _ = setup
+    client.post(
+        "/api/intake/fee-waiver/",
+        _application(session, receives_noncash_assistance=True, benefit_types=["SNAP"]),
+        format="json",
+    )
+    fw = FeeWaiverApplication.objects.get(session=session)
+
+    resp = _send(
+        client,
+        "patch",
+        f"/api/intake/fee-waiver/{fw.id}/",
+        {"receives_noncash_assistance": sent},
+        encoding,
+    )
+
+    fw.refresh_from_db()
+    assert resp.status_code == 400
+    assert (fw.receives_noncash_assistance, fw.benefit_types) == (True, ["SNAP"])
+
+
 # ── Reading the application back by session (DIG-157) ─────────────────


PATCH
```

`_send` posts JSON, multipart or urlencoded, and never puts `None` into a form body: a question left unanswered is missing from it. A row saved before the question is made through the ORM with only the old columns.

- [ ] **Step 2: Write the failing tests for what Form 103B prints**

```python file=backend/apps/forms/tests/test_form_103b_answers.py
"""
Form 103B prints the fee-waiver page's answers on the lines that ask them (step 2 spec §3
Q10 and Q11, §6.4, Appendix A.2).

Business intent: the fee-waiver application is sworn, and the court decides the waiver from
it. Line 2 is the filer's take-home pay, which they typed on the fee-waiver page; line 3 is
their own Yes or No about non-cash help, with what kind; line 6 is the same monthly expense
total as Schedule J line 22c. A figure or answer the filer never gave prints blank, never
0.00 or a No, and the boxes the old bindings misused (line 4's and line 5's explanations,
Part 3's other assets) stay blank.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.forms.schema import load_schema
from apps.forms.services.derivations import DERIVATIONS
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.forms.tests.pdf_readback import read_widgets
from apps.intake.models import (
    DebtInfo,
    DebtorInfo,
    ExpenseInfo,
    FeeWaiverApplication,
    IntakeSession,
)

User = get_user_model()

# Line 2's boxes the take-home figure prints in: You, Subtotal and the family's net income.
TAKE_HOME_BOXES = ("undefined_2", "undefined_4", "undefined_6")


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="filer_103b", password="pass")
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
    ExpenseInfo.objects.create(
        session=session, rent_or_mortgage=Decimal("1200.00"), food_and_groceries=Decimal("400.50")
    )
    DebtInfo.objects.create(
        session=session,
        creditor_name="First Bank",
        debt_type="credit_card",
        amount_owed=Decimal("5000.00"),
    )
    return session


def _apply(session, **answers):
    """The filer's application. The old columns hold figures no box may print any more."""
    page_answers = {
        "monthly_take_home_pay": Decimal("2800.00"),
        "receives_noncash_assistance": False,
        "benefit_types": [],
        **answers,
    }
    return FeeWaiverApplication.objects.create(
        session=session,
        household_size=2,
        monthly_income=Decimal("3200.00"),
        monthly_expenses=Decimal("2560.00"),
        **page_answers,
    )


def _filled(session):
    """Box → what a viewer sees in it once the form is filled: the ticked states, or the text."""
    shows = {}
    for widget in _widgets(session):
        seen = shows.setdefault(widget.full_name, set())
        if widget.state is not None:
            if widget.state != "/Off":
                seen.add(widget.state)
        elif widget.value:
            seen.add(widget.value)
    return shows


def _widgets(session):
    values = resolve(load_schema("form_103b"), session)
    return read_widgets(PDFFormFiller().fill("form_103b", values))


def test_line_2_prints_take_home_pay_for_you_the_subtotal_and_the_family_total(session):
    _apply(session)
    filled = _filled(session)

    assert [filled.get(box) for box in TAKE_HOME_BOXES] == [{"2800.00"}] * 3
    # Nobody else's income and no non-cash subtraction is asked, and line 4 is an explanation.
    assert [filled.get(box) for box in ("undefined_3", "undefined_5", "4 type")] == [set()] * 3


def test_take_home_pay_never_given_prints_blank_not_zero(session):
    # An application saved before the page asked take-home pay.
    _apply(session, monthly_take_home_pay=None)
    filled = _filled(session)

    assert [filled.get(box) for box in TAKE_HOME_BOXES] == [set()] * 3


def test_take_home_pay_typed_as_zero_prints_zero(session):
    _apply(session, monthly_take_home_pay=Decimal("0.00"))
    filled = _filled(session)

    assert [filled.get(box) for box in TAKE_HOME_BOXES] == [{"0.00"}] * 3


@pytest.mark.parametrize(
    ("answer", "kinds", "ticked", "what_kind"),
    [
        (
            True,
            ["SNAP (food stamps)", "Housing subsidy"],
            {"/yes"},
            {"SNAP (food stamps), Housing subsidy"},
        ),
        # A kind stored beside a sworn No never prints under it.
        (False, ["SNAP (food stamps)"], {"/no"}, set()),
        # Saved before the page asked: no sworn answer either way, so no kind prints either.
        (None, ["SNAP (food stamps)"], set(), set()),
    ],
)
def test_line_3_prints_the_filers_own_answer_about_non_cash_help(
    session, answer, kinds, ticked, what_kind
):
    _apply(session, receives_noncash_assistance=answer, benefit_types=kinds)
    filled = _filled(session)

    assert (filled.get("check 3"), filled.get("3 type")) == (ticked, what_kind)


def test_line_6_is_the_monthly_expense_total_schedule_j_prints(session):
    _apply(session)
    filled = _filled(session)

    # $1,200.00 rent and $400.50 food, the only expenses entered.
    assert filled.get("undefined_7") == {"1600.50"}
    assert DERIVATIONS["schedule_j_total_expenses"](session) == "1600.50"
    # Line 5 explains why installments won't work, which no page asks yet.
    assert filled.get("5 Type") == set()


def test_line_1_counts_the_filer(session):
    _apply(session)

    assert _filled(session).get("You") == {"/On"}


def test_pages_2_and_3_are_headed_with_the_filers_name(session):
    _apply(session)

    assert {
        widget.page: widget.value
        for widget in _widgets(session)
        if widget.full_name == "Debtor.Name1"
    } == {2: "Jane Doe", 3: "Jane Doe"}


def test_part_3_stays_blank_because_schedule_a_b_is_attached(session):
    # The form says to attach Schedule A/B instead, and every packet has it (OQ-17).
    _apply(session)

    assert _filled(session).get("Amount you owe") == set()
```

The tests fill the real template and read it back. Every application also holds the old `monthly_income` (3200.00) and `monthly_expenses` (2560.00) columns, so a box that still read them would show it.

- [ ] **Step 3: Run them with tier 2 and the list check, and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line -rN apps/intake/tests/test_fee_waiver_views.py apps/forms/tests/test_form_103b_answers.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -21
```

Expected: FAIL — `13 failed, 410 passed, 62 xfailed`. Two form-encoded creates that leave the answer out are stored instead of refused (`assert 201 == 400`), and the three PATCHes that send a kind to a row with no answer are saved (`assert 200 == 400`). Form 103B prints nothing on line 2, line 3, line 6 (`assert set() == {'1600.50'}`), line 1's You box or the page captions (`assert {2: None, 3: None} == {2: 'Jane Doe', 3: 'Jane Doe'}`), and Part 3 prints the total debt (`assert {'5000.00'} == set()`). The other 13 new tests already pass, and they guard the change against a later regression. The JSON creates that leave the answer out or send null, and the form creates that send it blank, are already refused. The four form-encoded creates that give an answer keep it. A row saved before the question can still be changed, and both attempts to take an answer back are refused. On Form 103B, take-home pay never given and an empty line 3 answer print nothing while their boxes are unbound. The warnings summary is known suite noise (DIG-211): Django reports the missing backend/staticfiles directory.

- [ ] **Step 4: Keep only a non-cash answer the filer gave**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/intake/serializers.py b/backend/apps/intake/serializers.py
index 61e92d0..684a42f 100644
--- a/backend/apps/intake/serializers.py
+++ b/backend/apps/intake/serializers.py
@@ -384,8 +384,10 @@ class FeeWaiverApplicationSerializer(serializers.ModelSerializer):
     monthly_take_home_pay = serializers.DecimalField(
         max_digits=10, decimal_places=2, min_value=Decimal("0")
     )
-    # The model allows empty, for rows saved before the question existed.
-    receives_noncash_assistance = serializers.BooleanField()
+    # The model allows empty, for rows saved before the question existed. allow_null makes a
+    # form-encoded request that leaves the answer out read as empty, not as No (DIG-193), and
+    # validate() refuses the empty answer.
+    receives_noncash_assistance = serializers.BooleanField(allow_null=True)
     # The "What kind?" answer: each kind is a non-blank line of text.
     benefit_types = serializers.ListField(
         child=serializers.CharField(max_length=255), required=False
@@ -417,12 +419,22 @@ class FeeWaiverApplicationSerializer(serializers.ModelSerializer):
     def validate(self, attrs):
         """A Yes to non-cash help needs "What kind?" answered, and a No keeps no kind.

-        A PATCH may send only one of the two, so the other is the stored one.
+        The answer is required on create and can't be sent empty: Form 103B line 3 prints a
+        stored answer as a sworn Yes or No (DIG-193). A PATCH may send only one of the two, so
+        the other is the stored one, which is empty on a row saved before the question; a kind
+        sent there needs a Yes first.
         """
+        required = self.fields["receives_noncash_assistance"].error_messages["required"]
+        if attrs.get("receives_noncash_assistance") is None and (
+            self.instance is None or "receives_noncash_assistance" in attrs
+        ):
+            raise serializers.ValidationError({"receives_noncash_assistance": [required]})
         answer = attrs.get(
             "receives_noncash_assistance",
             getattr(self.instance, "receives_noncash_assistance", None),
         )
+        if answer is None and attrs.get("benefit_types"):
+            raise serializers.ValidationError({"receives_noncash_assistance": [required]})
         if answer is False:
             attrs["benefit_types"] = []
         elif answer and not attrs.get("benefit_types", getattr(self.instance, "benefit_types", [])):
PATCH
```

DIG-193: an empty answer is refused in every encoding, and a kind of help is refused while the answer is empty, so line 3 never prints a No the filer didn't give.

- [ ] **Step 5: Read the fee-waiver page's answers in the 103B rules**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index 17051c8..6234425 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -385,21 +385,30 @@ def _fee_waiver_household_size(session: IntakeSession) -> str:


 def _fee_waiver_monthly_income(session: IntakeSession) -> str:
+    """Line 2: the take-home pay the filer typed, blank if they never gave it (B2)."""
+    fw = getattr(session, "fee_waiver", None)
+    if fw is None or fw.monthly_take_home_pay is None:
+        return ""
+    return _fmt(Decimal(str(fw.monthly_take_home_pay)))

-    try:
-        fw = session.fee_waiver
-        return _fmt(Decimal(str(fw.monthly_income)))
-    except Exception:
-        return "0.00"

+def _fee_waiver_noncash_assistance(session: IntakeSession) -> str:
+    """Line 3: the filer's own yes or no, blank until they answer (DIG-193)."""
+    fw = getattr(session, "fee_waiver", None)
+    answer = None if fw is None else fw.receives_noncash_assistance
+    if answer is True:
+        return "yes"
+    if answer is False:
+        return "no"
+    return ""

-def _fee_waiver_monthly_expenses(session: IntakeSession) -> str:

-    try:
-        fw = session.fee_waiver
-        return _fmt(Decimal(str(fw.monthly_expenses)))
-    except Exception:
-        return "0.00"
+def _fee_waiver_benefit_types(session: IntakeSession) -> str:
+    """Line 3's "Describe": the kinds of help, joined as the fee-waiver page shows them."""
+    fw = getattr(session, "fee_waiver", None)
+    if fw is None or fw.receives_noncash_assistance is not True:
+        return ""
+    return ", ".join(fw.benefit_types)


 # ---------------------------------------------------------------------------
@@ -583,7 +592,10 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     # Form 103B fee waiver derivations
     "fee_waiver_household_size": _fee_waiver_household_size,
     "fee_waiver_monthly_income": _fee_waiver_monthly_income,
-    "fee_waiver_monthly_expenses": _fee_waiver_monthly_expenses,
+    # Line 6 is Schedule J line 22c: one figure on both forms
+    "fee_waiver_monthly_expenses": _schedule_j_total_expenses,
+    "fee_waiver_noncash_assistance": _fee_waiver_noncash_assistance,
+    "fee_waiver_benefit_types": _fee_waiver_benefit_types,
     # Schedule I income line item derivations
     "schedule_i_occupation_debtor1": _schedule_i_occupation_debtor1,
     "schedule_i_employer_debtor1": _schedule_i_employer_debtor1,
PATCH
```

Line 2 reads take-home pay (Q10), line 3 reads the filer's own answer and its kinds (Q11), and line 6 is Schedule J line 22c. A figure or answer the filer never gave prints blank, never 0.00 or a No.

- [ ] **Step 6: Bind Form 103B's lines, and record the six placements**

```bash
git apply <<'PATCH'
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index 59383bb..a3e5f90 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -178,5 +178,65 @@
     "status": "confirmed",
     "correct_target": "Name of person agreed to pay",
     "evidence": "Field index: Name of person agreed to pay p12 'Yes. Name of person (attach Official Form 119)' (tooltip 'Name of person to help fill out forms (not an attorney)'), adjudicated. The audit's row judged a separate answer, form_107.Name_of_person_agreed_to_pay. Owner's answer Q12 (step 2 spec §3, §6.3): the filer names their paid helper once, in answer:form_101.preparer_name, which prints on the three name boxes (101, 106Dec, 107)."
+  },
+  {
+    "schema": "form_103b",
+    "pdf_field": "You",
+    "producer": "constant:true",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "You",
+    "evidence": "Field index: You p1 line 1 'You' (option 'You', state /On, sampled_ok), the first 'check all that apply' box of the family-size question. Step 2 spec §6.4 and Appendix A.2: You is ticked; the filer is always one of the people counted."
+  },
+  {
+    "schema": "form_103b",
+    "pdf_field": "undefined_2",
+    "producer": "derived:fee_waiver_monthly_income",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_2",
+    "evidence": "Field index: undefined_2 p1 line 2 'You', column 'That person’s average monthly net income (take-home pay)' (sampled_ok). Owner's answer Q10 (step 2 spec §3, §6.3, DIG-78): 103B line 2 prints the take-home pay the filer typed on the fee-waiver page, on You, Subtotal and the family's net income; Your spouse and the non-cash subtraction stay blank (Appendix E 6)."
+  },
+  {
+    "schema": "form_103b",
+    "pdf_field": "undefined_4",
+    "producer": "derived:fee_waiver_monthly_income",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "undefined_4",
+    "evidence": "Field index: undefined_4 p1 line 2 'Subtotal', column 'That person’s average monthly net income (take-home pay)' (sampled_ok). Owner's answer Q10 (step 2 spec §3, §6.3, DIG-78): 103B line 2 prints the take-home pay the filer typed on the fee-waiver page, on You, Subtotal and the family's net income; Your spouse and the non-cash subtraction stay blank (Appendix E 6)."
+  },
+  {
+    "schema": "form_103b",
+    "pdf_field": "check 3",
+    "producer": "derived:fee_waiver_noncash_assistance",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check 3",
+    "evidence": "Field index: check 3 p1 line 3 'Do you receive non-cash governmental assistance?', states /no ('No') and /yes ('Yes. Describe.'), sampled_ok. Owner's answer Q11 (step 2 spec §3, §6.3): line 3 is a Yes/No question in the form's own words with \"What kind?\", answered on the fee-waiver page; blank until answered (DIG-193)."
+  },
+  {
+    "schema": "form_103b",
+    "pdf_field": "3 type",
+    "producer": "derived:fee_waiver_benefit_types",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "3 type",
+    "evidence": "Field index: 3 type p1 line 3 'Type of assistance' (sampled_ok), the box beside 'Yes. Describe.'. Owner's answer Q11 (step 2 spec §3, §6.3): line 3 is a Yes/No question in the form's own words with \"What kind?\", answered on the fee-waiver page; blank until answered (DIG-193). The kinds print only with a Yes."
+  },
+  {
+    "schema": "form_103b",
+    "pdf_field": "Debtor.Name1",
+    "producer": "derived:full_name",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Debtor.Name1",
+    "evidence": "Field index: Debtor.Name1 'Debtor 1 (continuation-page caption)', one field with a widget on pages 2 and 3 (adjudicated; its tooltip \"Judge's Signature\" is a template error). Step 2 spec §6.4 and Appendix A.2: the page 2-3 caption prints the name. The audit's derived:full_name row on 'Debtor' names 'Debtor 1', so it doesn't place this box."
   }
 ]
diff --git a/data/forms/schemas/form_103b.json b/data/forms/schemas/form_103b.json
index 3f833b8..7035150 100644
--- a/data/forms/schemas/form_103b.json
+++ b/data/forms/schemas/form_103b.json
@@ -37,6 +37,26 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "You",
+      "type": "checkbox",
+      "source": "constant",
+      "choices": {
+        "true": "/On"
+      },
+      "page": 1,
+      "label": "You",
+      "required": false,
+      "conditional_on": null,
+      "value": "true",
+      "rule": null,
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "Total number of people",
       "type": "text",
@@ -55,11 +75,11 @@
       "legal_review": false
     },
     {
-      "pdf_field": "4 type",
+      "pdf_field": "undefined_2",
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Monthly income",
+      "label": "You: average monthly net income (take-home pay)",
       "required": false,
       "conditional_on": null,
       "value": null,
@@ -72,15 +92,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "5 Type",
+      "pdf_field": "undefined_4",
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Monthly expenses",
+      "label": "Subtotal: average monthly net income (take-home pay)",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "fee_waiver_monthly_expenses",
+      "rule": "fee_waiver_monthly_income",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -89,15 +109,87 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Amount you owe",
+      "pdf_field": "undefined_6",
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Total debt",
+      "label": "Your family’s average monthly net income",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "fee_waiver_monthly_income",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "check 3",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "yes": "/yes",
+        "no": "/no"
+      },
+      "page": 1,
+      "label": "Do you receive non-cash governmental assistance?",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "total_debts",
+      "rule": "fee_waiver_noncash_assistance",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "3 type",
+      "type": "text",
+      "source": "derived",
+      "page": 1,
+      "label": "Type of assistance",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "fee_waiver_benefit_types",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "Debtor.Name1",
+      "type": "text",
+      "source": "derived",
+      "page": 2,
+      "label": "Debtor name",
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
+      "pdf_field": "undefined_7",
+      "type": "text",
+      "source": "derived",
+      "page": 2,
+      "label": "Estimate your average monthly expenses.",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "fee_waiver_monthly_expenses",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
PATCH
```

`You` is ticked; line 2's three boxes, line 3's two, line 6 and the caption are bound; `4 type`, `5 Type` and `Amount you owe` lose their bindings. Each ADD box's addendum row lands with its binding (§7.4).

- [ ] **Step 7: Delete the three orphaned entries, and pin tier 2's new coverage**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index 351ac53..d1be215 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -7,30 +7,6 @@
     "class": "unmapped_choice",
     "ticket": "DIG-68"
   },
-  {
-    "form_type": "form_103b",
-    "pdf_field": "4 type",
-    "tier": "2",
-    "case": "derived:fee_waiver_monthly_income",
-    "class": "wrong_box",
-    "ticket": "DIG-78"
-  },
-  {
-    "form_type": "form_103b",
-    "pdf_field": "5 Type",
-    "tier": "2",
-    "case": "derived:fee_waiver_monthly_expenses",
-    "class": "wrong_box",
-    "ticket": "DIG-78"
-  },
-  {
-    "form_type": "form_103b",
-    "pdf_field": "Amount you owe",
-    "tier": "2",
-    "case": "derived:total_debts",
-    "class": "wrong_box",
-    "ticket": "DIG-78"
-  },
   {
     "form_type": "form_106sum",
     "pdf_field": "4",
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index 2268628..3da6926 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 410
+ASSERTED_CASES = 415


 def _audit_dir():
PATCH
```

Delete the three entries by hand, as the patch does; never re-run the recorder (§7.3).

- [ ] **Step 8: Fix the tests that describe the old columns**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_api_readback.py b/backend/apps/forms/tests/test_api_readback.py
index a5eb353..db85357 100644
--- a/backend/apps/forms/tests/test_api_readback.py
+++ b/backend/apps/forms/tests/test_api_readback.py
@@ -186,8 +186,8 @@ def test_forms_built_through_the_api_print_what_the_seeded_forms_print(persona):
         form_type: _comparable(form_type, build_field_values(form_type, seeded))
         for form_type in packet(seeded)
     }
-    # No form prints take-home pay or the non-cash answer until 2b binds them on Form 103B,
-    # so the stored applications are compared directly.
+    # Form 103B prints take-home pay and the non-cash answer, but no form prints the two
+    # "cannot pay" answers, so the stored applications are compared directly.
     built = IntakeSession.objects.get(pk=session_id)
     assert _fee_waiver_answers(built) == _fee_waiver_answers(seeded)
     assert (_fee_waiver_answers(built) is None) == (persona not in WAIVER_FILERS)
diff --git a/backend/apps/forms/tests/test_form_103b_schema.py b/backend/apps/forms/tests/test_form_103b_schema.py
index bbceebd..db4231b 100644
--- a/backend/apps/forms/tests/test_form_103b_schema.py
+++ b/backend/apps/forms/tests/test_form_103b_schema.py
@@ -50,9 +50,8 @@ def session_with_fw(session):
     FeeWaiverApplication.objects.create(
         session=session,
         household_size=2,
-        monthly_income=Decimal("1500.00"),
-        monthly_expenses=Decimal("1400.00"),
-        receives_public_benefits=True,
+        monthly_take_home_pay=Decimal("1500.00"),
+        receives_noncash_assistance=True,
         benefit_types=["SNAP"],
         cannot_pay_full=True,
         cannot_pay_installments=True,
PATCH
```

`test_form_103b_schema.py`'s fixture wrote the dead `monthly_income`, `monthly_expenses` and `receives_public_benefits`; it now writes the page's columns. `test_api_readback.py`'s comment said no form prints take-home pay or the non-cash answer until 2b.

- [ ] **Step 9: Run the tests, tier 2 and the list check again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest --tb=line -rN apps/intake/tests/test_fee_waiver_views.py apps/forms/tests/test_form_103b_answers.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider 2>&1 | tail -21
```

Expected: `431 passed, 59 xfailed`, and no failures. Tier 2 asserts five more cases, and the three deleted bindings take their expected failures with them.

- [ ] **Step 10: Run every gate**

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

Expected: `1928 passed, 113 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  357 passed (357)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

- [ ] **Step 11: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 7 passed` and `RUN 2 exit=0: 7 passed`. The fee-waiver page calls the serializer this task changes, and Maria's Yes and DeShawn's and Sarah's No reach Form 103B through Generate All, where a value outside check 3's choices would fail the form.

- [ ] **Step 12: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/tests/test_form_103b_answers.py \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_api_readback.py \
  backend/apps/forms/tests/test_form_103b_schema.py \
  backend/apps/forms/tests/test_oracle_tier2.py \
  backend/apps/intake/serializers.py \
  backend/apps/intake/tests/test_fee_waiver_views.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/form_103b.json
git commit -F - <<'MSG'
fix(forms): Form 103B prints the fee-waiver answers where its lines ask, never an unanswered No

The fee-waiver application is sworn, and the court decides the waiver
from it. Step 2 binds 103B to the fee-waiver page's answers (step 2 spec
§3 Q10 and Q11, §6.4, Appendix A.2). A figure or answer the filer never
gave prints blank, never 0.00 or a No.

The non-cash answer first (DIG-193). Line 3 now prints the stored
answer, so the server keeps one only when the filer gave it:
- receives_noncash_assistance allows null, so a form-encoded or
  multipart create that leaves the answer out reads as empty instead of
  DRF's default False, and validate() refuses an empty answer on create
  in every encoding (JSON null, a missing form field, a blank one).
- An answer, once given, can't be sent back as empty.
- On a row saved before the question (answer empty), a PATCH that sends
  kinds of help is refused until the filer says Yes. Other changes to
  such a row still save.
- A No still drops any kind sent with it, as before.

The bindings:
- You (line 1) is ticked: constant "true", {"true": "/On"}.
- Line 2: take-home pay prints on You (undefined_2), Subtotal
  (undefined_4) and the family's net income (undefined_6, moved from line
  4's "Explain" box, 4 type). fee_waiver_monthly_income now reads
  monthly_take_home_pay and is blank when it is empty. It read the old
  monthly_income, which 2a stopped writing, through a bare except, so 4
  type printed 0.00 for every waiver filer. Your spouse and the non-cash
  subtraction stay blank.
- Line 3: check 3 ticks /yes or /no from the new rule
  fee_waiver_noncash_assistance (blank when empty); 3 type prints the
  kinds of help, joined with ", " as the page shows them, only under a
  Yes (fee_waiver_benefit_types, new).
- Line 6 (undefined_7, moved from line 5's explanation box, 5 Type) is
  Schedule J line 22c: fee_waiver_monthly_expenses now points at
  _schedule_j_total_expenses, so both forms print one figure. The old
  body read the unwritten monthly_expenses column.
- The page 2-3 caption (Debtor.Name1, one field, two widgets) prints the
  filer's name.
- Part 3's "Amount you owe" box (line 15's description) loses its
  total-debt binding; Part 3 stays blank because Schedule A/B is attached
  (OQ-17). total_debts stays bound on 106Sum.

step2_verification.json gains 6 rows, one per ADD box (You, undefined_2,
undefined_4, check 3, 3 type, Debtor.Name1), each citing the box's index
label and Q10, Q11 or §6.4. The two MOVED boxes are asserted by the
moved-here join from verification.json's confirmed rows on 4 type and 5
Type.

Tests:
- test_fee_waiver_views.py: an application that doesn't answer non-cash
  help is refused in JSON, multipart and urlencoded; a form-encoded
  application keeps the Yes or No it gives; kinds of help need a Yes on
  a row saved before the question, which can still be changed; an answer
  given can't be taken back to none.
- New test_form_103b_answers.py fills the real template and reads it
  back: take-home pay on line 2's three boxes, blank when never given,
  0.00 when typed as 0; line 3's own answer (Yes with its kinds, No, or
  nothing), with a kind stored beside a No or no answer left unprinted;
  line 6 equals Schedule J's total, not the old column; You
  ticked; the name on pages 2 and 3; line 4's and 5's explanations and
  Part 3 blank.
- Fixed: test_form_103b_schema.py's fixture wrote the dead
  monthly_income, monthly_expenses and receives_public_benefits; it now
  writes the page's columns. test_api_readback.py's comment said no form
  prints take-home pay or the non-cash answer until 2b.

Clears 3 known-defect entries, all tier 2 wrong_box (DIG-78): 103B "4
type", "5 Type" and "Amount you owe" (orphaned); 112 remain.

ASSERTED_CASES 410 -> 415 (+5):
- -3 for the deleted bindings on 4 type, 5 Type and Amount you owe (all
  xfails).
- +6 for the ADD boxes, asserted through the addendum.
- +2 for undefined_6 and undefined_7, asserted by the moved-here join.

Refs DIG-193, DIG-78
MSG
git status --short
```

### Task 7: Print monthly expenses on 106Sum line 5, and never mark a Form 121 filer with an SSN as having none

_Built and verified as commit `ccebdbf` on `plan/forms-step2b`._

**Files:**

- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_form_106sum_schema.py`
- Modify: `backend/apps/forms/tests/test_form_121_schema.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/form_106sum.json`
- Modify: `data/forms/schemas/form_121.json`

**Interfaces:**

- Consumes:
  - `total_monthly_expenses` (`ExpenseInfo.calculate_total_monthly_expenses()`, the figure Schedule J 22c prints) and `no_ssn_check` (`""` when `DebtorInfo.ssn` is set, otherwise `"true"`), both already in `DERIVATIONS` and unchanged.
  - `verification.json`'s confirmed rows (form_106sum, `9a`) with `correct_target` `5`, and (form_121, `Check Box2`) with `correct_target` `Check Box1`. Tier 2's moved-here join asserts the two moved bindings through them.
  - Task 1's addendum reader in `test_oracle_tier2.py`, and `step2_verification.json` as Task 6 leaves it (24 rows).
  - `PDFFormFiller` and `read_widgets` (`apps/forms/tests/pdf_readback.py`), to read line 6's ticks back from the filled template.
- Produces:
  - 106Sum: `5` ← `derived:total_monthly_expenses` on page 1; `check6` ← `constant` `"yes"` with `choices` `{"yes": "/yes"}` on page 2; `3a` and `9a` unbound.
  - Form 121: `Check Box1` ← `derived:no_ssn_check` with `choices` `{"true": "/On"}`, labelled "Debtor 1 does not have a Social Security number".
  - `total_priority_unsecured` and `has_ssn_check` are gone from `DERIVATIONS`, with `_total_priority_unsecured`.
  - `step2_verification.json` has 25 rows; the new one is (form_106sum, `check6`, `constant:yes`).
  - `ASSERTED_CASES` stays 415 in `test_oracle_tier2.py`, which this task doesn't touch.
  - `known_defects.json` has 104 entries.
  - Tests in `test_form_106sum_schema.py`: `test_priority_debts_print_nowhere_until_the_filer_is_asked_which_have_priority`, `test_monthly_expenses_print_on_line_5_not_on_the_support_obligations_line`, `test_line_6_says_the_filer_is_filing_under_chapter_7_11_or_13`. In `test_form_121_schema.py`: `test_a_filer_with_a_social_security_number_is_never_marked_as_having_none` and `test_a_filer_without_a_social_security_number_is_marked_as_having_none`.
  - Tier 1's `test_checkbox_answer_is_mapped_to_a_box` has no case left, so pytest reports `1 skipped` from here until Task 18.

**Decisions already made in this task:**

- 106Sum `3a` (priority unsecured claims) goes blank. Which debts have priority is never asked (OQ-3), and deciding it is a legal judgment; §6.1 B5: "Until priority is asked (OQ-3), the nonpriority totals count every unsecured debt and the priority totals stay blank." `total_priority_unsecured` loses its only binding, so `_total_priority_unsecured` and its `DERIVATIONS` entry go (Ruling T0-d). A grep finds no other caller and no test of it.
- 106Sum line 5 ("Copy your monthly expenses from line 22c of Schedule J") takes `total_monthly_expenses` from `9a`, which asks for domestic support obligations that DigniFi never asks. Line 5 is a total, and §6.1 option A names it among the totals that still print. It goes on page 1, the field index's page; the old `9a` object said page 2.
- `5` and Form 121 `Check Box1` are MOVED, so they get no addendum row: the moved-here join asserts them. `check6` is an ADD, and moved-here excludes constants, so it gets the addendum row, with `producer` `constant:yes` (the whole binding key, as tier 2's `_binding_key` builds it).
- `check6` is a constant Yes: every DigniFi filing is Chapter 7. Its `choices` key isn't `"true"`, so the filler looks up `"yes"` and writes `/yes`, the index's on state.
- Form 121 `Check Box1` is Debtor 1's "You do not have a Social Security number". It was bound to `has_ssn_check`, which is true for a filer who has one, and held with empty `choices`, so it ticked nothing (DIG-68). It is re-ruled in place (E006) to `no_ssn_check`, and `has_ssn_check` goes. `_has_ssn` stays, because `no_ssn_check` calls it.
- The packet refuses Form 121 without a 9-digit SSN (`registry._needs_ssn`), so the box never ticks in a generated packet. The no-SSN test reaches it through `resolve()` only, and says so.
- `test_debt_totals` loses its `3a` line. Its `3b` line stays as it is until Task 16.
- Form 121's box was the last checkbox held unmapped, so tier 1's `test_checkbox_answer_is_mapped_to_a_box` has an empty parameter set, and pytest reports it as 1 skipped until Task 18 replaces it (Ruling C-6). A checkbox bound with `{}` would still become a case and fail.
- `ASSERTED_CASES` stays 415 (delta 0), measured by diffing the collected IDs: −1 for `3a` (it passed), −2 for `9a` and `Check Box1` under `has_ssn_check` (both xfails), +2 for `5` and `Check Box1` under `no_ssn_check` through moved-here, and +1 for `check6` through the addendum.
- Known defects: delete exactly these 8 entries (112 → 104). The tier 2 entry for 106Sum `9a` under `derived:total_monthly_expenses` (DIG-79) is orphaned. The five tier 3 entries for 106Sum `5` (deshawn, james, maria, priya, sarah; DIG-79) now pass, a strict XPASS. Form 121 `Check Box1`'s tier 1 `unmapped_choice` entry and its tier 2 entry under `derived:has_ssn_check` (both DIG-68) are orphaned.
- Leave three things as they are: `Total_6e`'s note in `data/forms/field_index/audit/schedule_e_f.unbound.json` still names `total_priority_unsecured`, the `HELD_UNMAPPED` comment in `data/forms/field_index/tools/convert_schemas.py` still describes `has_ssn_check`, and `_total_monthly_expenses` still returns `"0.00"` without an `ExpenseInfo`. No code reads the first two, and the intake's `complete` refuses a session without expenses.

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_form_106sum_schema.py b/backend/apps/forms/tests/test_form_106sum_schema.py
index 16910a4..363b8e0 100644
--- a/backend/apps/forms/tests/test_form_106sum_schema.py
+++ b/backend/apps/forms/tests/test_form_106sum_schema.py
@@ -10,6 +10,8 @@ from apps.districts.models import District
 from apps.eligibility.cmi import IncomeNotSplit
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
+from apps.forms.services.pdf_filler import PDFFormFiller
+from apps.forms.tests.pdf_readback import read_widgets
 from apps.intake.models import (
     AssetInfo,
     DebtInfo,
@@ -122,9 +124,31 @@ class TestForm106SumSchema:
     def test_debt_totals(self, populated_session):
         field_map = resolve(load_schema("form_106sum"), populated_session)
         assert field_map["2"] == "50000.00"  # secured
-        assert field_map["3a"] == "5000.00"  # priority unsecured
         assert field_map["3b"] == "10000.00"  # nonpriority unsecured

+    def test_priority_debts_print_nowhere_until_the_filer_is_asked_which_have_priority(
+        self, populated_session
+    ):
+        # The fixture's IRS debt is marked priority, but DigniFi never asks which debts
+        # have priority (OQ-3), and deciding it is a legal judgment: line 3a stays blank.
+        field_map = resolve(load_schema("form_106sum"), populated_session)
+        assert "3a" not in field_map
+
+    def test_monthly_expenses_print_on_line_5_not_on_the_support_obligations_line(
+        self, populated_session
+    ):
+        # Line 5 copies Schedule J line 22c. Line 9a asks for domestic support
+        # obligations, which DigniFi never asks (step 2 spec §6.4).
+        field_map = resolve(load_schema("form_106sum"), populated_session)
+        assert field_map.get("5") == "1900.00"  # 1000 + 200 + 400 + 300
+        assert "9a" not in field_map
+
+    def test_line_6_says_the_filer_is_filing_under_chapter_7_11_or_13(self, populated_session):
+        # Every DigniFi filing is Chapter 7, so line 6's Yes ticks and its No stays off.
+        values = resolve(load_schema("form_106sum"), populated_session)
+        widgets = read_widgets(PDFFormFiller().fill("form_106sum", values))
+        assert sorted(w.state for w in widgets if w.full_name == "check6") == ["/Off", "/yes"]
+
     def test_cmi(self, populated_session):
         field_map = resolve(load_schema("form_106sum"), populated_session)
         # 1200 wages = 1200.00 CMI
diff --git a/backend/apps/forms/tests/test_form_121_schema.py b/backend/apps/forms/tests/test_form_121_schema.py
index 1938535..9f6ba85 100644
--- a/backend/apps/forms/tests/test_form_121_schema.py
+++ b/backend/apps/forms/tests/test_form_121_schema.py
@@ -72,3 +72,31 @@ class TestForm121Schema:
     def test_without_debtor(self, session):
         field_map = resolve(load_schema("form_121"), session)
         assert "Bankruptcy District Information" in field_map
+
+    def test_a_filer_with_a_social_security_number_is_never_marked_as_having_none(
+        self, session_with_ssn
+    ):
+        # Line 2's Debtor 1 box says "You do not have a Social Security number". The old
+        # rule would have ticked it for exactly the filers who have one (DIG-68).
+        field_map = resolve(load_schema("form_121"), session_with_ssn)
+        assert "Check Box1" not in field_map
+
+    def test_a_filer_without_a_social_security_number_is_marked_as_having_none(self, session):
+        # Only resolve() reaches this: the packet refuses Form 121 without a 9-digit
+        # number (registry._needs_ssn), so a generated packet never ticks the box.
+        DebtorInfo.objects.create(
+            session=session,
+            first_name="Jane",
+            middle_name="Marie",
+            last_name="Doe",
+            ssn="",
+            date_of_birth=date(1990, 1, 15),
+            phone="312-555-0100",
+            email="jane@example.com",
+            street_address="123 Main St",
+            city="Chicago",
+            state="IL",
+            zip_code="60601",
+        )
+        field_map = resolve(load_schema("form_121"), session)
+        assert field_map.get("Check Box1") == "/On"
PATCH
```

The 106Sum tests require line 5 to print the fixture's hand-summed expenses (1000 + 200 + 400 + 300 = 1900.00) with `9a` absent, `3a` absent although the fixture's IRS debt is marked priority, and line 6's two widgets to read `/Off` and `/yes` back from the filled template. The Form 121 tests require `Check Box1` absent for a filer with an SSN and `/On` for one stored with `ssn=""`.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_106sum_schema.py apps/forms/tests/test_form_121_schema.py -q -p no:cacheprovider 2>&1 | tail -30
```

Expected: FAIL — `4 failed, 14 passed`. Line 3a still prints `5000.00`, line 5 is unbound (`assert None == '1900.00'`), line 6 reads `['/Off', '/Off']`, and Form 121's box is unmapped, so the no-SSN test reads `assert None == '/On'`. The test for a filer with an SSN passes today only because the box maps nothing. After Task 7 it passes because the rule is right: binding has_ssn_check with the new choices turns it red.

- [ ] **Step 3: Bind 106Sum line 5 and line 6, and re-rule Form 121's no-SSN box**

```bash
git apply <<'PATCH'
diff --git a/data/forms/schemas/form_106sum.json b/data/forms/schemas/form_106sum.json
index 85f58f7..ce22d6c 100644
--- a/data/forms/schemas/form_106sum.json
+++ b/data/forms/schemas/form_106sum.json
@@ -106,15 +106,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "3a",
+      "pdf_field": "3b",
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Priority unsecured debts",
+      "label": "Nonpriority unsecured debts",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "total_priority_unsecured",
+      "rule": "total_nonpriority_unsecured",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -123,15 +123,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "3b",
+      "pdf_field": "3c",
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Nonpriority unsecured debts",
+      "label": "Total unsecured debts",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "total_nonpriority_unsecured",
+      "rule": "total_unsecured_debts",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -140,15 +140,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "3c",
+      "pdf_field": "4",
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Total unsecured debts",
+      "label": "Total debts",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "total_unsecured_debts",
+      "rule": "total_debts",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -157,15 +157,35 @@
       "legal_review": false
     },
     {
-      "pdf_field": "4",
+      "pdf_field": "5",
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Total debts",
+      "label": "Monthly expenses (Schedule J line 22c)",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "total_debts",
+      "rule": "total_monthly_expenses",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "check6",
+      "type": "checkbox",
+      "source": "constant",
+      "choices": {
+        "yes": "/yes"
+      },
+      "page": 2,
+      "label": "Are you filing for bankruptcy under Chapters 7, 11, or 13?",
+      "required": false,
+      "conditional_on": null,
+      "value": "yes",
+      "rule": null,
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -210,23 +230,6 @@
       "repeat_capacity": null,
       "row": null,
       "legal_review": false
-    },
-    {
-      "pdf_field": "9a",
-      "type": "text",
-      "source": "derived",
-      "page": 2,
-      "label": "Total monthly expenses",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "total_monthly_expenses",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
     }
   ]
 }
diff --git a/data/forms/schemas/form_121.json b/data/forms/schemas/form_121.json
index 44a4cb1..3a34151 100644
--- a/data/forms/schemas/form_121.json
+++ b/data/forms/schemas/form_121.json
@@ -92,13 +92,15 @@
       "pdf_field": "Check Box1",
       "type": "checkbox",
       "source": "derived",
-      "choices": {},
+      "choices": {
+        "true": "/On"
+      },
       "page": 1,
-      "label": "Debtor 1 has SSN",
+      "label": "Debtor 1 does not have a Social Security number",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "has_ssn_check",
+      "rule": "no_ssn_check",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
PATCH
```

In 106Sum, `5` follows `4` as the last page 1 object, `check6` comes before `check7`, and the `3a` and `9a` objects are gone. Form 121's `Check Box1` keeps its object and changes its rule, its `choices` and its label (E006: one binding per box).

- [ ] **Step 4: Delete the two rules that lost their last binding**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index 6234425..62dab15 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -117,13 +117,6 @@ def _total_secured_debts(session: IntakeSession) -> str:
     return _fmt(_sum_encrypted(qs, "amount_owed"))


-def _total_priority_unsecured(session: IntakeSession) -> str:
-    from apps.intake.models import DebtInfo
-
-    qs = DebtInfo.objects.filter(session=session, is_secured=False, is_priority=True)
-    return _fmt(_sum_encrypted(qs, "amount_owed"))
-
-
 def _total_nonpriority_unsecured(session: IntakeSession) -> str:
     from apps.intake.models import DebtInfo

@@ -546,7 +539,6 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "district_name": lambda s: s.district.name,
     "today_iso": lambda s: date.today().isoformat(),
     "ssn_formatted": _ssn_formatted,
-    "has_ssn_check": lambda s: "true" if _has_ssn(s) else "",
     "no_ssn_check": lambda s: "" if _has_ssn(s) else "true",
     "joint_filer_check": lambda s: (
         "true" if _form_answer_predicate(s, "joint_filer_gate") else ""
@@ -555,7 +547,6 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "total_personal_property": _total_personal_property,
     "total_assets": _total_assets,
     "total_secured_debts": _total_secured_debts,
-    "total_priority_unsecured": _total_priority_unsecured,
     "total_nonpriority_unsecured": _total_nonpriority_unsecured,
     "total_unsecured_debts": _total_unsecured_debts,
     "total_debts": _total_debts,
PATCH
```

E007 allows this only now: no schema binds `total_priority_unsecured` or `has_ssn_check` after Step 3.

- [ ] **Step 5: Add check6's addendum row and delete the 8 known-defect entries**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index d1be215..2f87c54 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -1,12 +1,4 @@
 [
-  {
-    "form_type": "form_121",
-    "pdf_field": "Check Box1",
-    "tier": "1",
-    "case": "",
-    "class": "unmapped_choice",
-    "ticket": "DIG-68"
-  },
   {
     "form_type": "form_106sum",
     "pdf_field": "4",
@@ -15,14 +7,6 @@
     "class": "wrong_box",
     "ticket": "DIG-79"
   },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "9a",
-    "tier": "2",
-    "case": "derived:total_monthly_expenses",
-    "class": "wrong_box",
-    "ticket": "DIG-79"
-  },
   {
     "form_type": "form_107",
     "pdf_field": "Income 5a Debtor 1",
@@ -47,14 +31,6 @@
     "class": "wrong_box",
     "ticket": "DIG-77"
   },
-  {
-    "form_type": "form_121",
-    "pdf_field": "Check Box1",
-    "tier": "2",
-    "case": "derived:has_ssn_check",
-    "class": "wrong_box",
-    "ticket": "DIG-68"
-  },
   {
     "form_type": "form_122a1",
     "pdf_field": "13A",
@@ -535,46 +511,6 @@
     "class": "wrong_value",
     "ticket": "DIG-79"
   },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "5",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "5",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "5",
-    "tier": "3",
-    "case": "maria",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "5",
-    "tier": "3",
-    "case": "priya",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
-  {
-    "form_type": "form_106sum",
-    "pdf_field": "5",
-    "tier": "3",
-    "case": "sarah",
-    "class": "wrong_value",
-    "ticket": "DIG-79"
-  },
   {
     "form_type": "form_122a1",
     "pdf_field": "13B",
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index a3e5f90..ab760d3 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -238,5 +238,15 @@
     "status": "confirmed",
     "correct_target": "Debtor.Name1",
     "evidence": "Field index: Debtor.Name1 'Debtor 1 (continuation-page caption)', one field with a widget on pages 2 and 3 (adjudicated; its tooltip \"Judge's Signature\" is a template error). Step 2 spec §6.4 and Appendix A.2: the page 2-3 caption prints the name. The audit's derived:full_name row on 'Debtor' names 'Debtor 1', so it doesn't place this box."
+  },
+  {
+    "schema": "form_106sum",
+    "pdf_field": "check6",
+    "producer": "constant:yes",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "check6",
+    "evidence": "Field index: check6 p2 line 6 'Are you filing for bankruptcy under Chapters 7, 11, or 13?', states /no ('No. You have nothing to report on this part of the form...') and /yes ('Yes'), both sampled_ok. Step 2 spec §6.4 and Appendix A.4: check6 is Yes; every DigniFi filing is Chapter 7."
   }
 ]
PATCH
```

The addendum row cites `check6`'s field-index label, "Are you filing for bankruptcy under Chapters 7, 11, or 13?", its two states and §6.4 (§7.4: rows land with their binding). The known-defects patch only deletes the 8 entries named above; it changes nothing else in the list.

- [ ] **Step 6: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_106sum_schema.py apps/forms/tests/test_form_121_schema.py -q -p no:cacheprovider 2>&1 | tail -30
```

Expected: `18 passed`.

- [ ] **Step 7: Run the oracle, the list check and the schema check**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py apps/forms/tests/test_checks.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `1178 passed, 1 skipped, 104 xfailed`: one expected failure per remaining entry, no XPASS, no orphan, and every schema passes the system check. The skip is tier 1's empty unmapped-checkbox test.

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

Expected: `1941 passed, 1 skipped, 105 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  357 passed (357)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

Task 7 changes no page or flow, so the journeys don't run for it.

- [ ] **Step 9: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_form_106sum_schema.py \
  backend/apps/forms/tests/test_form_121_schema.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/form_106sum.json \
  data/forms/schemas/form_121.json
git commit -F - <<'MSG'
fix(forms): 106Sum prints monthly expenses on line 5, and Form 121 never says a filer with an SSN has none

Form 106Sum and Form 121 now print these (step 2 spec §6.4, Appendix
A.4 and A.12, Appendix E 3):
- 106Sum line 5 ("Copy your monthly expenses from line 22c of Schedule
  J") prints total_monthly_expenses, moved from 9a. 9a asks for
  domestic support obligations, which DigniFi never asks, so it is now
  blank.
- 106Sum 3a (priority unsecured claims) loses its binding. Which debts
  have priority is never asked (OQ-3), so 3a stays blank until it is.
  total_priority_unsecured had no other binding and is deleted.
- 106Sum line 6 ticks Yes (check6, constant "yes", {"yes": "/yes"}):
  every DigniFi filing is Chapter 7.
- Form 121's Check Box1 is Debtor 1's "You do not have a Social
  Security number". It was bound to has_ssn_check, which is true for a
  filer who has one, and held unmapped so it ticked nothing (DIG-68).
  It is re-ruled in place to no_ssn_check with {"true": "/On"}, and its
  label now says what the box asks. has_ssn_check had no other binding
  and is deleted. The packet still refuses Form 121 without a 9-digit
  SSN, so the box never ticks in a generated packet.

step2_verification.json gains 1 row, for the ADD box check6, citing
its index label and §6.4. 106Sum 5 and 121 Check Box1 are MOVED: the
moved-here join asserts them from verification.json's confirmed rows
on 9a and Check Box2.

Tests:
- test_form_106sum_schema.py: priority debts print nowhere until the
  filer is asked which have priority; monthly expenses print on line 5
  and not on 9a; line 6 ticks Yes and leaves No off (read back from the
  filled template).
- test_form_121_schema.py: a filer with an SSN is never marked as
  having none (proved by mutation: has_ssn_check with the new choices
  fails it); a filer without one is (resolve() only).
- Fixed: test_debt_totals asserted 3a's 5000.00; that line is gone (3b
  changes in a later commit).

Tier 1's unmapped-checkbox test has no case left, because Form 121's
box was the last one held unmapped. Pytest reports it as 1 skipped
("got empty parameter set"). A checkbox bound without choices would
still become a case and fail.

Clears 8 known-defect entries (112 -> 104):
- 106Sum 9a, tier 2 wrong_box (DIG-79), by orphan.
- 106Sum 5, tier 3 wrong_value for all five personas (DIG-79), by
  strict XPASS.
- 121 Check Box1, tier 1 unmapped_choice and tier 2 wrong_box under
  has_ssn_check (DIG-68), by orphan.

ASSERTED_CASES 415 -> 415 (0):
- -1 for 3a's deleted binding (passing).
- -2 for 9a and Check Box1 under has_ssn_check (both xfails).
- +2 for 5 and Check Box1 under no_ssn_check, through moved-here (both
  pass).
- +1 for check6, through the addendum.

Refs DIG-79, DIG-68
MSG
git status --short
```

### Task 8: Print each income source on the Form 122A-1 line that asks for it, and the household size on line 13

_Built and verified as commit `e1e5672` on `plan/forms-step2b`._

**Files:**

- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_derivations.py`
- Modify: `backend/apps/forms/tests/test_form_122a1_schema.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier3.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/form_122a1.json`

**Interfaces:**

- Consumes:
  - The 122A-1 income rules 2a already switched to the Income step's amounts (Ruling T0-c): `line1_wages`, `line6b_child_support_alimony` (`monthly_child_support`), `line3_real_property_income` (`monthly_rental_income`), `line6a_unemployment` (`monthly_unemployment`), `line5a_pension_retirement` (`monthly_pension`) and `line7_other_income` (`monthly_other_income`). Each goes through `_income_amounts(session, *fields)`, which is blank when the filer gave none of its amounts. `family_size` reads `DebtorInfo.household_size`.
  - `verification.json`'s confirmed form_122a1 rows whose `correct_target` names the new box: `Quest6B` → `Debto1.Quest4`, `Quest4` → `Debto1.Quest6C`, `Quest5A` → `Debto1.Quest9`, `Quest9` → `13B`, `Quest7` → `Debto1.Quest10A` and `Quest6A` → `Debto1.Quest8.0`. Tier 2's moved-here join asserts the six moves through them.
  - `TEN_SOURCES` (a distinct power of two per income source) and `SWITCHED_RULES` in `test_derivations.py`.
  - Task 1's tier 3 expectation `""` (the box shows nothing), and `step2_verification.json` as Task 7 leaves it (25 rows).
- Produces:
  - Form 122A-1 bindings, in line order: `Debto1.Quest3` ← `derived:line3_alimony`; `Debto1.Quest4` ← `derived:line6b_child_support_alimony`; `Debto1.Quest6C` ← `derived:line3_real_property_income` (one full name, two widgets on page 1); `Debto1.Quest8.0` ← `derived:line6a_unemployment`; `Debto1.Quest9` ← `derived:line5a_pension_retirement`; `terrorism If necessary list other sources on a separate page and put the total below 1` (line 10's source box) ← `derived:other_income_label`; `Debto1.Quest10A` ← `derived:line7_other_income`; `13B` ← `derived:family_size`. `Debto1.Quest5A`, `Debto1.Quest5B`, `Debto1.Quest6A`, `Debto1.Quest6B`, `Debto1.Quest7`, `Debto1.Quest8A`, `Debto1.Quest10B` and `Debto1.Quest10C` are unbound.
  - New rules `line3_alimony` (`_income_amounts(session, "monthly_alimony")`) and `other_income_label` ("Other income" when `IncomeInfo.monthly_other_income` is not NULL and above $0, otherwise `""`, also with no `IncomeInfo`). Task 10 binds `other_income_label` to Schedule I `Other income 8h`; it must not create it again.
  - Gone from `DERIVATIONS`: `line2_business_income`, `line5b_social_security`, `line8a_total_gross_income`, `line10a_deductions`, `line10b_total_deductions`, `line10c_net_income` and `line13b_annualized_income`, with the functions `_line2_business_income`, `_line5b_social_security`, `_line10a_deductions`, `_line10b_total_deductions`, `_line10c_net_income` and `_line13b_annualized_income`. `_line8a_total_gross_income` and `_get_income_field` stay for Schedule I until Task 10, and `_line11_annualized_income` stays.
  - `step2_verification.json` has 27 rows; the new ones are (form_122a1, `Debto1.Quest3`, `derived:line3_alimony`) and (form_122a1, line 10's source box, `derived:other_income_label`).
  - `ASSERTED_CASES = 410` in `test_oracle_tier2.py`.
  - Tier 3 `EXPECTED` gains, for all five personas, form_122a1 `Debto1.Quest7` `""` and `Debto1.Quest9` `"0.00"`.
  - `known_defects.json` has 86 entries.
  - Tests in `test_form_122a1_schema.py`: `test_each_income_source_prints_on_the_122a1_line_that_asks_for_it`, `test_lines_the_filer_is_never_asked_about_print_nothing` and `test_line_13_prints_the_household_size`, with the module constants `LINE_BY_SOURCE` and `NEVER_ASKED`. The module imports `TEN_SOURCES` from `apps.forms.tests.test_derivations`, so Task 10 keeps it importable there. In `test_derivations.py`: `line3_alimony` joins `SWITCHED_RULES`, plus `test_other_income_is_named_only_when_the_filer_has_some` and `test_other_income_is_not_named_before_the_filer_gives_any_income`.

**Decisions already made in this task:**

- Swap chains 122A-1 a (`Debto1.Quest6B` → `Debto1.Quest4` → `Debto1.Quest6C`), b (`Debto1.Quest5A` → `Debto1.Quest9` → `13B`) and c (`Debto1.Quest7` → `Debto1.Quest10A`) land in this one commit (R2): a partial chain puts two bindings on one box, which E006 rejects. `Debto1.Quest6A` → `Debto1.Quest8.0` is an independent move that rides along.
- Boxes that already have an object are re-ruled in place (`Debto1.Quest3`, `Debto1.Quest4`, `Debto1.Quest9`, `13B`, `Debto1.Quest10A`); `Debto1.Quest6C`, `Debto1.Quest8.0` and line 10's source box get new objects. Their labels are retitled from the field index. Labels on boxes this task doesn't touch stay as they are, even where they are wrong (`Debto1.Quest2.0` still says "Line 1").
- Only bindings move. The six income rules already read the `monthly_*` columns since 2a (Ruling T0-c), and a moved rule keeps its name although it describes the old line (§6.1 Rule names), so tier 2 keeps checking the move against the audit.
- The boxes for lines DigniFi never asks (5 business, 6 rental gross and costs, 7 interest, 8 unemployment claimed as Social Security, 10's second row and its separate-pages total) lose their bindings and print blank, never 0.00 (§6.1 B2). Social Security prints on no 122A-1 line.
- `Debto1.Quest3` and line 10's source box are ADD, so each gets an addendum row with its whole binding key as `producer` (Ruling C-1). verification.json already holds a (form_122a1, `Quest3`) row under the old key `derived:line2_business_income`; tier 2 joins on (box, key), so both rows stay. The six MOVED boxes need no row.
- Seven rules lose their last binding and go (Ruling T0-d). `_line8a_total_gross_income` loses only its `DERIVATIONS` key: Schedule I's `_schedule_i_net_income_debtor1` still calls the function until Task 10. `_get_income_field` stays for the same reason. `_line11_annualized_income` stays: the `line11_annualized_income` and `line12b_annualized_cmi` rules call it, and `eligibility/tests/test_means_test_calculator.py` checks `line12b_annualized_cmi`. A grep finds no other caller of the deleted rules outside the audit's historical JSON.
- `test_each_income_source_prints_on_the_122a1_line_that_asks_for_it` is the 122A-1 half of §7.7's `test_each_income_source_prints_on_its_own_line`, which lands in Task 10 with Schedule I's boxes. It imports `TEN_SOURCES` from `test_derivations.py`, as `test_known_defects.py` imports the tier modules.
- Appendix D's rows land here, in the commit that makes them pass: `Debto1.Quest9` prints `0.00` for every persona (the seeds store pension as $0, and an income source typed as $0 prints 0.00), and `Debto1.Quest7` prints nothing (interest is never asked).
- `ASSERTED_CASES` goes from 415 to 410 (−5), measured by diffing the collected IDs: 13 tier 2 cases leave with their bindings (all were xfails), and 8 arrive, all passing: 6 moved-here joins (`Debto1.Quest4`, `Debto1.Quest6C`, `Debto1.Quest8.0`, `Debto1.Quest9`, `Debto1.Quest10A`, `13B`) and the 2 addendum rows.
- Known defects: delete exactly these 18 entries (104 → 86). Thirteen tier 2 `wrong_box` entries are orphaned, one per old binding: `Debto1.Quest3` `derived:line2_business_income`, `Debto1.Quest4` `derived:line3_real_property_income`, `Debto1.Quest5A` `derived:line5a_pension_retirement`, `Debto1.Quest5B` `derived:line5b_social_security`, `Debto1.Quest6A` `derived:line6a_unemployment`, `Debto1.Quest6B` `derived:line6b_child_support_alimony`, `Debto1.Quest7` `derived:line7_other_income`, `Debto1.Quest8A` `derived:line8a_total_gross_income`, `Debto1.Quest10A` `derived:line10a_deductions`, `Debto1.Quest10B` `derived:line10b_total_deductions`, `Debto1.Quest10C` `derived:line10c_net_income` (all DIG-56), and `Debto1.Quest9` `derived:family_size` and `13B` `derived:line13b_annualized_income` (DIG-59). The five tier 3 `13B` entries (deshawn, james, maria, priya, sarah; DIG-59) now pass, a strict XPASS: the seeds' household sizes are 2, 1, 3, 4 and 1.
- `family_size` prints a stored `household_size` of 0 as "0", and the median beside it still sizes the household its own way until Task 9 reads the stored means test. The rule is unchanged here.

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_derivations.py b/backend/apps/forms/tests/test_derivations.py
index 50d0348..46de40d 100644
--- a/backend/apps/forms/tests/test_derivations.py
+++ b/backend/apps/forms/tests/test_derivations.py
@@ -121,8 +121,8 @@ TEN_SOURCES = {
     "monthly_other_income": Decimal("512.00"),
 }

-# The rules switched in 2a commit 4, with the sources each one adds up (spec §6.2's
-# "Returns"). Their names still describe their old lines until 2b moves the bindings.
+# The rules switched in 2a commit 4 or created in 2b, with the sources each one adds up
+# (spec §6.2's "Returns"). Moved rules keep names that describe their old lines (§6.1).
 SWITCHED_RULES = {
     "cmi": [field for field in TEN_SOURCES if field != "monthly_social_security"],
     "schedule_i_net_wages_debtor1": ["monthly_gross_wages", "monthly_tips"],
@@ -138,6 +138,7 @@ SWITCHED_RULES = {
     "line6a_unemployment": ["monthly_unemployment"],
     "line5a_pension_retirement": ["monthly_pension"],
     "line7_other_income": ["monthly_other_income"],
+    "line3_alimony": ["monthly_alimony"],
 }


@@ -172,6 +173,23 @@ def test_an_income_sum_counts_an_empty_source_as_zero(session):
     assert DERIVATIONS["schedule_i_child_support_debtor1"](session) == "300.00"


+@pytest.mark.parametrize(
+    "other_income,named",
+    [(Decimal("0.01"), "Other income"), (Decimal("0"), ""), (None, "")],
+)
+def test_other_income_is_named_only_when_the_filer_has_some(session, other_income, named):
+    # 122A-1 line 10 and Schedule I 8h ask what the other income is (Appendix E 5).
+    IncomeInfo.objects.create(
+        session=session, monthly_gross_wages=Decimal("100.00"), monthly_other_income=other_income
+    )
+
+    assert DERIVATIONS["other_income_label"](session) == named
+
+
+def test_other_income_is_not_named_before_the_filer_gives_any_income(session):
+    assert DERIVATIONS["other_income_label"](session) == ""
+
+
 def test_cmi_refuses_a_session_with_no_income_by_source(session):
     from apps.eligibility.cmi import IncomeNotSplit

diff --git a/backend/apps/forms/tests/test_form_122a1_schema.py b/backend/apps/forms/tests/test_form_122a1_schema.py
index 0c12daf..26cf852 100644
--- a/backend/apps/forms/tests/test_form_122a1_schema.py
+++ b/backend/apps/forms/tests/test_form_122a1_schema.py
@@ -1,5 +1,6 @@
 """Round-trip tests for Form 122A-1 schema-driven resolution."""

+from datetime import date
 from decimal import Decimal

 import pytest
@@ -9,10 +10,37 @@ from apps.districts.models import District
 from apps.eligibility.cmi import IncomeNotSplit
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
-from apps.intake.models import IncomeInfo, IntakeSession
+from apps.forms.tests.test_derivations import TEN_SOURCES
+from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

 User = get_user_model()

+# Box → what it prints with TEN_SOURCES (wages 1, overtime 2, tips 4, rental 8,
+# pension 16, Social Security 32, unemployment 64, child support 128, alimony 256,
+# other 512).
+LINE_BY_SOURCE = {
+    "Debto1.Quest2.0": "7.00",  # line 2: wages, overtime and tips
+    "Debto1.Quest3": "256.00",  # line 3: alimony
+    "Debto1.Quest4": "128.00",  # line 4: child support
+    "Debto1.Quest6C": "8.00",  # line 6: net rental income
+    "Debto1.Quest8.0": "64.00",  # line 8: unemployment
+    "Debto1.Quest9": "16.00",  # line 9: pension
+    "terrorism If necessary list other sources on a separate page and put the total below 1": (
+        "Other income"
+    ),  # line 10: the source
+    "Debto1.Quest10A": "512.00",  # line 10: its amount
+}
+NEVER_ASKED = {
+    "Debto1.Quest5A",
+    "Debto1.Quest5B",
+    "Debto1.Quest6A",
+    "Debto1.Quest6B",
+    "Debto1.Quest7",
+    "Debto1.Quest8A",
+    "Debto1.Quest10B",
+    "Debto1.Quest10C",
+}
+

 @pytest.fixture
 def session(db):
@@ -63,3 +91,37 @@ class TestForm122A1Schema:
         # Lines 11 to 13 are CMI, and a filer who gave no income has none (spec §5.5).
         with pytest.raises(IncomeNotSplit):
             resolve(load_schema("form_122a1"), session)
+
+    def test_each_income_source_prints_on_the_122a1_line_that_asks_for_it(self, session):
+        # A distinct power of two per source, so a box that reads the wrong source, or
+        # adds one too many, prints a different figure (step 2 spec §5.5's table).
+        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
+
+        field_map = resolve(load_schema("form_122a1"), session)
+
+        assert {box: field_map.get(box) for box in LINE_BY_SOURCE} == LINE_BY_SOURCE
+        # Social Security is left out of current monthly income, so no line shows it.
+        assert "32.00" not in field_map.values()
+
+    def test_lines_the_filer_is_never_asked_about_print_nothing(self, session):
+        # Business income, interest, rental gross and costs, unemployment claimed as
+        # Social Security, a second other-income row: blank, never 0.00 (B2).
+        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
+
+        field_map = resolve(load_schema("form_122a1"), session)
+
+        assert sorted(NEVER_ASKED & field_map.keys()) == []
+
+    def test_line_13_prints_the_household_size(self, session_with_income):
+        DebtorInfo.objects.create(
+            session=session_with_income,
+            first_name="Maria",
+            last_name="Torres",
+            ssn="900-11-0001",  # IRS-reserved range: synthetic
+            date_of_birth=date(1988, 6, 15),
+            household_size=3,
+        )
+
+        field_map = resolve(load_schema("form_122a1"), session_with_income)
+
+        assert field_map["13B"] == "3"
PATCH
```

The per-source test gives each of the ten sources its own power of two, so a box that reads the wrong source, or one source too many, prints a different figure. It requires every 122A-1 box in `LINE_BY_SOURCE` to print its own figure and no box to print Social Security's 32.00. The never-asked test requires the eight `NEVER_ASKED` boxes to be absent, and the household test requires `13B` to print the stored household size 3. In `test_derivations.py`, `line3_alimony` joins the per-source rule cases (its own figure, blank when only other sources are given, 0.00 when typed as $0), and `other_income_label` names other income only above $0.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_122a1_schema.py apps/forms/tests/test_derivations.py -q -p no:cacheprovider 2>&1 | tail -90
```

Expected: FAIL — `10 failed, 57 passed`. The per-source test finds the boxes holding other lines' figures, for example line 9 printing the household size instead of the pension (its dict diff starts `Omitting 1 identical items`; which differing boxes it lists depends on Python's hash seed), the never-asked test finds the eight boxes still bound (`first extra item: 'Debto1.Quest10B'`), and the household test reads `assert '24000.00' == '3'`, because 13B prints the annualized income. The seven rule cases raise `KeyError: 'line3_alimony'` and `KeyError: 'other_income_label'`: neither rule exists yet.

- [ ] **Step 3: Move the 122A-1 income bindings, chains a, b and c in one change**

```bash
git apply <<'PATCH'
diff --git a/data/forms/schemas/form_122a1.json b/data/forms/schemas/form_122a1.json
index 568fe98..d5a30e3 100644
--- a/data/forms/schemas/form_122a1.json
+++ b/data/forms/schemas/form_122a1.json
@@ -59,11 +59,11 @@
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Line 2: Business income",
+      "label": "Line 3: Alimony and maintenance payments",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "line2_business_income",
+      "rule": "line3_alimony",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -76,75 +76,7 @@
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Line 3: Real property income",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "line3_real_property_income",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debto1.Quest5A",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Line 5a: Pension, retirement",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "line5a_pension_retirement",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debto1.Quest5B",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Line 5b: Social Security",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "line5b_social_security",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debto1.Quest6A",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Line 6a: Unemployment compensation",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "line6a_unemployment",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debto1.Quest6B",
-      "type": "text",
-      "source": "derived",
-      "page": 1,
-      "label": "Line 6b: Child support, alimony",
+      "label": "Line 4: Amounts regularly paid for household expenses, including child support",
       "required": false,
       "conditional_on": null,
       "value": null,
@@ -157,15 +89,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Debto1.Quest7",
+      "pdf_field": "Debto1.Quest6C",
       "type": "text",
       "source": "derived",
       "page": 1,
-      "label": "Line 7: Other income",
+      "label": "Line 6: Net monthly income from rental or other real property",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "line7_other_income",
+      "rule": "line3_real_property_income",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -174,15 +106,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Debto1.Quest8A",
+      "pdf_field": "Debto1.Quest8.0",
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Line 8a: Total gross income",
+      "label": "Line 8: Unemployment compensation",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "line8a_total_gross_income",
+      "rule": "line6a_unemployment",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -195,28 +127,11 @@
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Line 9: Household size",
+      "label": "Line 9: Pension or retirement income",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "family_size",
-      "ingest_key": null,
-      "binding": null,
-      "repeat": null,
-      "repeat_capacity": null,
-      "row": null,
-      "legal_review": false
-    },
-    {
-      "pdf_field": "Debto1.Quest10A",
-      "type": "text",
-      "source": "derived",
-      "page": 2,
-      "label": "Line 10a: Deductions",
-      "required": false,
-      "conditional_on": null,
-      "value": null,
-      "rule": "line10a_deductions",
+      "rule": "line5a_pension_retirement",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -225,15 +140,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Debto1.Quest10B",
+      "pdf_field": "terrorism If necessary list other sources on a separate page and put the total below 1",
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Line 10b: Total deductions",
+      "label": "Line 10: Other income, source",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "line10b_total_deductions",
+      "rule": "other_income_label",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -242,15 +157,15 @@
       "legal_review": false
     },
     {
-      "pdf_field": "Debto1.Quest10C",
+      "pdf_field": "Debto1.Quest10A",
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Line 10c: Net income",
+      "label": "Line 10: Other income, amount",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "line10c_net_income",
+      "rule": "line7_other_income",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -314,11 +229,11 @@
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Line 13B: Annualized income",
+      "label": "Line 13: Number of people in your household",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "line13b_annualized_income",
+      "rule": "family_size",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
PATCH
```

The schema goes from 20 objects to 15. Every box stays in line order, and no `pdf_field` appears twice (E006).

- [ ] **Step 4: Add line3_alimony and other_income_label, and delete the rules with no binding left**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index 62dab15..c196ca7 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -262,8 +262,8 @@ def _line1_wages(session: IntakeSession) -> str:
     return _income_amounts(session, "monthly_gross_wages", "monthly_tips", "monthly_overtime")


-def _line2_business_income(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "business_income"))
+def _line3_alimony(session: IntakeSession) -> str:
+    return _income_amounts(session, "monthly_alimony")


 def _line3_real_property_income(session: IntakeSession) -> str:
@@ -278,10 +278,6 @@ def _line5a_pension_retirement(session: IntakeSession) -> str:
     return _income_amounts(session, "monthly_pension")


-def _line5b_social_security(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "social_security"))
-
-
 def _line6a_unemployment(session: IntakeSession) -> str:
     return _income_amounts(session, "monthly_unemployment")

@@ -294,6 +290,13 @@ def _line7_other_income(session: IntakeSession) -> str:
     return _income_amounts(session, "monthly_other_income")


+def _other_income_label(session: IntakeSession) -> str:
+    """What the other income is, on 122A-1 line 10 and Schedule I 8h: named only above $0."""
+    income_info = getattr(session, "income_info", None)
+    other = None if income_info is None else income_info.monthly_other_income
+    return "Other income" if other is not None and other > 0 else ""
+
+
 def _line8a_total_gross_income(session: IntakeSession) -> str:
     total = sum(
         (
@@ -312,20 +315,6 @@ def _line8a_total_gross_income(session: IntakeSession) -> str:
     return _fmt(total)


-def _line10a_deductions(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "deductions"))
-
-
-def _line10b_total_deductions(session: IntakeSession) -> str:
-    return _fmt(_get_income_field(session, "total_deductions"))
-
-
-def _line10c_net_income(session: IntakeSession) -> str:
-    gross = Decimal(_line8a_total_gross_income(session))
-    deductions = Decimal(_line10b_total_deductions(session))
-    return _fmt(gross - deductions)
-
-
 def _line11_annualized_income(session: IntakeSession) -> str:
     cmi = Decimal(_cmi(session))
     return _fmt(cmi * Decimal("12"))
@@ -353,10 +342,6 @@ def _line13a_median_income(session: IntakeSession) -> str:
     return _fmt(median.get_median_income(size))


-def _line13b_annualized_income(session: IntakeSession) -> str:
-    return _line11_annualized_income(session)
-
-
 def _line13c_difference(session: IntakeSession) -> str:
     annualized = Decimal(_line11_annualized_income(session))
     median = Decimal(_line13a_median_income(session))
@@ -563,22 +548,17 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "total_debts_range": _total_debts_range,
     # Form 122A-1 means test derivations
     "line1_wages": _line1_wages,
-    "line2_business_income": _line2_business_income,
+    "line3_alimony": _line3_alimony,
     "line3_real_property_income": _line3_real_property_income,
     "line4_interest_dividends": _line4_interest_dividends,
     "line5a_pension_retirement": _line5a_pension_retirement,
-    "line5b_social_security": _line5b_social_security,
     "line6a_unemployment": _line6a_unemployment,
     "line6b_child_support_alimony": _line6b_child_support_alimony,
     "line7_other_income": _line7_other_income,
-    "line8a_total_gross_income": _line8a_total_gross_income,
-    "line10a_deductions": _line10a_deductions,
-    "line10b_total_deductions": _line10b_total_deductions,
-    "line10c_net_income": _line10c_net_income,
+    "other_income_label": _other_income_label,
     "line11_annualized_income": _line11_annualized_income,
     "line12b_annualized_cmi": _line12b_annualized_cmi,
     "line13a_median_income": _line13a_median_income,
-    "line13b_annualized_income": _line13b_annualized_income,
     "line13c_difference": _line13c_difference,
     # Form 103B fee waiver derivations
     "fee_waiver_household_size": _fee_waiver_household_size,
PATCH
```

The two new rules sit beside the 122A-1 income rules. `other_income_label` reads `monthly_other_income` itself, because it prints a word, not an amount.

- [ ] **Step 5: Give tier 2 the two ADD rows and its new count**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index 3da6926..2268628 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 415
+ASSERTED_CASES = 410


 def _audit_dir():
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index ab760d3..56f5005 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -248,5 +248,25 @@
     "status": "confirmed",
     "correct_target": "check6",
     "evidence": "Field index: check6 p2 line 6 'Are you filing for bankruptcy under Chapters 7, 11, or 13?', states /no ('No. You have nothing to report on this part of the form...') and /yes ('Yes'), both sampled_ok. Step 2 spec §6.4 and Appendix A.4: check6 is Yes; every DigniFi filing is Chapter 7."
+  },
+  {
+    "schema": "form_122a1",
+    "pdf_field": "Debto1.Quest3",
+    "producer": "derived:line3_alimony",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Debto1.Quest3",
+    "evidence": "Field index: Debto1.Quest3 p1 line 3, Column A (Debtor 1), 'Alimony and maintenance payments (not from a spouse if Column B is filled in)' (adjudicated). Step 2 spec §5.5 table (alimony received: 122A-1 line 3), §6.2 and Appendix E 5: 122A-1 line 3 prints alimony. The audit's row on this box judged the old line2_business_income binding."
+  },
+  {
+    "schema": "form_122a1",
+    "pdf_field": "terrorism If necessary list other sources on a separate page and put the total below 1",
+    "producer": "derived:other_income_label",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "terrorism If necessary list other sources on a separate page and put the total below 1",
+    "evidence": "Field index: this box p2 line 10 'Income from all other sources not listed above - source description, row 1' (adjudicated), beside its amount Debto1.Quest10A. Step 2 spec §5.5 table (other: 122A-1 line 10, \"Other income\"), §6.2 and Appendix E 5: the line 10 source box prints \"Other income\" when other income is above $0."
   }
 ]
PATCH
```

Each addendum row cites the box's field-index label and line, §5.5's table and Appendix E 5 (§7.4: rows land with their binding). `ASSERTED_CASES` changes from 415 to 410 for the reasons above.

- [ ] **Step 6: Add Appendix D's tier 3 rows and delete the 18 known-defect entries**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index 2f87c54..b4d5fdd 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -39,14 +39,6 @@
     "class": "wrong_box",
     "ticket": "DIG-59"
   },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13B",
-    "tier": "2",
-    "case": "derived:line13b_annualized_income",
-    "class": "wrong_box",
-    "ticket": "DIG-59"
-  },
   {
     "form_type": "form_122a1",
     "pdf_field": "13C",
@@ -55,102 +47,6 @@
     "class": "wrong_box",
     "ticket": "DIG-59"
   },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest10A",
-    "tier": "2",
-    "case": "derived:line10a_deductions",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest10B",
-    "tier": "2",
-    "case": "derived:line10b_total_deductions",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest10C",
-    "tier": "2",
-    "case": "derived:line10c_net_income",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest3",
-    "tier": "2",
-    "case": "derived:line2_business_income",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest4",
-    "tier": "2",
-    "case": "derived:line3_real_property_income",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest5A",
-    "tier": "2",
-    "case": "derived:line5a_pension_retirement",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest5B",
-    "tier": "2",
-    "case": "derived:line5b_social_security",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest6A",
-    "tier": "2",
-    "case": "derived:line6a_unemployment",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest6B",
-    "tier": "2",
-    "case": "derived:line6b_child_support_alimony",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest7",
-    "tier": "2",
-    "case": "derived:line7_other_income",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest8A",
-    "tier": "2",
-    "case": "derived:line8a_total_gross_income",
-    "class": "wrong_box",
-    "ticket": "DIG-56"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest9",
-    "tier": "2",
-    "case": "derived:family_size",
-    "class": "wrong_box",
-    "ticket": "DIG-59"
-  },
   {
     "form_type": "form_122a2",
     "pdf_field": "Quest1",
@@ -511,46 +407,6 @@
     "class": "wrong_value",
     "ticket": "DIG-79"
   },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13B",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13B",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13B",
-    "tier": "3",
-    "case": "maria",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13B",
-    "tier": "3",
-    "case": "priya",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13B",
-    "tier": "3",
-    "case": "sarah",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
   {
     "form_type": "form_122a1",
     "pdf_field": "13C",
diff --git a/backend/apps/forms/tests/test_oracle_tier3.py b/backend/apps/forms/tests/test_oracle_tier3.py
index 8dfcecf..2721322 100644
--- a/backend/apps/forms/tests/test_oracle_tier3.py
+++ b/backend/apps/forms/tests/test_oracle_tier3.py
@@ -53,6 +53,8 @@ EXPECTED = {
             "5": "2560.00",
         },
         "form_122a1": {
+            "Debto1.Quest7": "",
+            "Debto1.Quest9": "0.00",
             "Debto1.Quest11": "3200.00",
             "Quest11": "3200.00",
             "12B": "38400.00",
@@ -82,6 +84,8 @@ EXPECTED = {
             "5": "3110.00",
         },
         "form_122a1": {
+            "Debto1.Quest7": "",
+            "Debto1.Quest9": "0.00",
             "Debto1.Quest11": "5833.00",
             "Quest11": "5833.00",
             "12B": "69996.00",
@@ -110,6 +114,8 @@ EXPECTED = {
             "5": "6640.00",
         },
         "form_122a1": {
+            "Debto1.Quest7": "",
+            "Debto1.Quest9": "0.00",
             "Debto1.Quest11": "12000.00",
             "Quest11": "12000.00",
             "12B": "144000.00",
@@ -140,6 +146,8 @@ EXPECTED = {
             "5": "2295.00",
         },
         "form_122a1": {
+            "Debto1.Quest7": "",
+            "Debto1.Quest9": "0.00",
             "Debto1.Quest11": "3500.00",
             "Quest11": "3500.00",
             "12B": "42000.00",
@@ -166,6 +174,8 @@ EXPECTED = {
             "5": "1280.00",
         },
         "form_122a1": {
+            "Debto1.Quest7": "",
+            "Debto1.Quest9": "0.00",
             "Debto1.Quest11": "2000.00",
             "Quest11": "2000.00",
             "12B": "24000.00",
PATCH
```

The tier 3 patch adds two rows to each persona's form_122a1 block. The known-defects patch only deletes the 18 entries named above.

- [ ] **Step 7: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_122a1_schema.py apps/forms/tests/test_derivations.py -q -p no:cacheprovider 2>&1 | tail -90
```

Expected: `67 passed`.

- [ ] **Step 8: Run the oracle, the list check and the schema check**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py apps/forms/tests/test_checks.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `1196 passed, 1 skipped, 86 xfailed`: one expected failure per remaining entry, no XPASS, no orphan, and every schema passes the system check.

- [ ] **Step 9: Run every gate**

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

Expected: `1969 passed, 1 skipped, 87 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  357 passed (357)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

Task 8 changes no page or flow, so the journeys don't run for it.

- [ ] **Step 10: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_derivations.py \
  backend/apps/forms/tests/test_form_122a1_schema.py \
  backend/apps/forms/tests/test_oracle_tier2.py \
  backend/apps/forms/tests/test_oracle_tier3.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/form_122a1.json
git commit -F - <<'MSG'
fix(forms): Form 122A-1 prints each income source on the line that asks for it, and the household size on line 13

Form 122A-1's income lines now follow the step 2 spec's per-source table
(§5.5; Appendix A.5; chains a, b and c of Appendix B, in one commit):
- line 3 prints alimony (new rule line3_alimony);
- line 4 prints child support (line6b_child_support_alimony, moved from 6B);
- line 6's net rental box, both widgets, prints net rental income
  (line3_real_property_income, moved from line 4);
- line 8 prints unemployment (line6a_unemployment, moved from 6A);
- line 9 prints the pension (line5a_pension_retirement, moved from 5A);
- line 10 prints other income (line7_other_income, moved from line 7), with
  "Other income" in its source box when it is above $0 (new rule
  other_income_label, which Schedule I 8h will share);
- line 13 prints the household size (family_size, moved from line 9).

The boxes for lines DigniFi never asks (5 business, 6 rental gross and
costs, 7 interest, 8 unemployment claimed as Social Security, 10 row 2 and
10 separate pages) lose their bindings and print blank, never 0.00 (B2).
Social Security prints on no 122A-1 line.

Rules that lost their last binding are deleted: line2_business_income,
line5b_social_security, line8a_total_gross_income (the key only; Schedule I
still calls the function until its own move), line10a_deductions,
line10b_total_deductions, line10c_net_income and line13b_annualized_income.

Oracle:
- step2_verification.json gains the two ADD rows, line 3 and line 10's
  source box (25 -> 27).
- Tier 3 gains Appendix D's rows for all five personas: line 9 prints 0.00
  (pension typed as $0) and line 7 prints nothing (interest is never asked).

Clears 18 known-defect entries (104 -> 86): 13 tier 2 orphans (122A-1
lines 3, 4, 5A, 5B, 6A, 6B, 7, 8A, 9, 10A, 10B, 10C and 13B) and the 5
tier 3 13B entries, which now pass (strict XPASS).

ASSERTED_CASES 415 -> 410 (-5), measured by diffing the collected IDs:
- 13 tier 2 cases left with their bindings;
- 8 new cases: 6 moved-here joins (lines 4, 6C, 8, 9, 10A and 13B) and
  2 addendum rows (line 3 and line 10's source box). All pass.

New tests:
- test_each_income_source_prints_on_the_122a1_line_that_asks_for_it
- test_lines_the_filer_is_never_asked_about_print_nothing
- test_line_13_prints_the_household_size
- test_other_income_is_named_only_when_the_filer_has_some
- test_other_income_is_not_named_before_the_filer_gives_any_income
- line3_alimony joins the per-source rule tests in test_derivations.py

Refs DIG-56, DIG-59
MSG
git status --short
```

### Task 9: Print monthly income on Form 122A-1 line 11 and the means test's median on line 13, and tick the result

_Built and verified as commit `d1cc0f8` on `plan/forms-step2b`._

**Files:**

- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/tests/known_defects.json`
- Modify: `backend/apps/forms/tests/test_form_122a1_schema.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier2.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier3.py`
- Modify: `data/forms/field_index/audit/step2_verification.json`
- Modify: `data/forms/schemas/form_122a1.json`

**Interfaces:**

- Consumes:
  - `cmi`: `_fmt(current_monthly_income(income_info))` from `apps/eligibility/cmi.py`, the ten Income step amounts without Social Security, to the cent. It raises `IncomeNotSplit` when the filer gave none of them. `state` reads `DebtorInfo.state`. Both are unchanged.
  - Task 8's 122A-1 bindings, with `13B` ← `derived:family_size`, and `line12b_annualized_cmi`, which calls `_line11_annualized_income` (CMI × 12).
  - `is_above_median(cmi, median_income)` in `apps/eligibility/cmi.py` (`cmi * 12 > median_income`, so exactly the median is below it, DIG-136). `registry._above_median` decides whether Form 122A-2 is in the packet with the same call on the stored means test.
  - `MeansTest` (`session.means_test`: `calculated_cmi`, `median_income_threshold`), written by `MeansTestCalculator(session).calculate()`. Generate, Generate All, Regenerate and an unfiled download recalculate it before they resolve a form (§5.6).
  - `verification.json`'s confirmed (form_122a1, `13A`) row with `correct_target` `13C`, for the moved-here join, and `step2_verification.json` as Task 8 leaves it (27 rows).
  - The field index's on states for `14a` (`12b#20less#20or#20equal#20to#2013`, `12b#20more#20than#2013`) and `CheckBox1` (`No#20Abuse`, `Presumption#20of#20abuse#20applies`, `Does#20not#20apply`), spelled through `export_state()`.
- Produces:
  - Form 122A-1 bindings: `CheckBox1` (page 1, checkbox) ← `derived:median_comparison` with `choices` `{"below": "/No Abuse", "above": "/Presumption of abuse applies"}`; `Debto1.Quest11` (page 2) ← `derived:cmi`; `Quest11` ← `derived:cmi` (its two widgets are line 11's total and line 12a's copy); `13A` ← `derived:state`; `13C` ← `derived:line13a_median_income`; `14a` (page 2, checkbox) ← `derived:median_comparison` with `choices` `{"below": "/12b less or equal to 13", "above": "/12b more than 13"}`. `12B` keeps `derived:line12b_annualized_cmi`.
  - `line13a_median_income` returns `_fmt(session.means_test.median_income_threshold)`, and `""` when the session has no `MeansTest`.
  - New rule `median_comparison`: `""` without a `MeansTest`, otherwise `"above"` when `is_above_median(calculated_cmi, median_income_threshold)` and `"below"` when not.
  - Gone from `DERIVATIONS`: `line13c_difference` (with `_line13c_difference`) and the `line11_annualized_income` key. `_line11_annualized_income` stays as `_line12b_annualized_cmi`'s helper.
  - The `derivations.py` module docstring states §6.1 Rule 9.
  - `step2_verification.json` has 32 rows; the new ones are form_122a1 `Debto1.Quest11` and `Quest11` (`derived:cmi`), `13A` (`derived:state`), and `14a` and `CheckBox1` (`derived:median_comparison`).
  - `ASSERTED_CASES = 413` in `test_oracle_tier2.py`.
  - Tier 3 `EXPECTED` no longer holds Priya's or DeShawn's form_122a1 `Debto1.Quest11` row (Q1).
  - `known_defects.json` has 64 entries, none of them for form_122a1.
  - In `test_form_122a1_schema.py`: the fixture `median_income` (ILND's 2025 medians on the session's district) and the tests `test_line_11_prints_monthly_income_and_only_line_12b_multiplies_it_by_12`, `test_line_13_prints_the_state_and_the_median_the_means_test_compared_against`, `test_line_13_median_and_the_result_wait_for_the_eligibility_check` and `test_the_result_ticks_agree_with_whether_form_122a2_is_in_the_packet[at_the_median|one_cent_over]`.

**Decisions already made in this task:**

- Swap chain 122A-1 d is this commit (R2): `13A`'s median moves to `13C`, `line13c_difference` goes, and `13A` takes `derived:state`. `13A`, `13C` and `Quest11` are re-ruled in place (E006); `Debto1.Quest11`, `14a` and `CheckBox1` get new objects. The re-ruled boxes are retitled from the field index; `12B`'s label stays as it is.
- Line 11 prints CMI, a month, in Column A and in the total box, whose second widget is line 12a's copy. Only line 12b multiplies it by 12 (§6.1 C1: "CMI, without Social Security, goes on 122A-1 lines 11–12b"). `Quest11` used to print CMI × 12.
- `line13a_median_income` reads the stored `MeansTest.median_income_threshold` instead of re-sizing the household from dependents and marital status (DIG-51), so line 13 prints the median the means test compared against. It and `median_comparison` print blank before the means test runs: `resolve()` doesn't catch a rule's exception, and the 122A-1 schema tests' fixtures have no `MeansTest`, so both rules use `getattr(session, "means_test", None)`.
- The owner's answer Q5 decides `14a` and `CheckBox1`: "tick line 14 and page-1 box 1 or 2 from line 12b against line 13. Box 3 (military) is never ticked." Q2 decides the tie: "at or below" the median counts as below. `median_comparison` calls `is_above_median` on the stored means test, the call that puts Form 122A-2 in the packet, so the ticks never disagree with the packet. Every `choices` state is read from the index through `export_state()`, never typed, and the military box 3 (`/Does not apply`) is never mapped. Both bindings are `legal_review: false`.
- The `derivations.py` header said no rule may hold a "means-test verdict". It is reworded in this commit, the one that adds `median_comparison` (§6.1 Rule 9): "a rule may apply a comparison the form itself spells out, but it may not choose exemptions, decide priority, or answer anything the form leaves to the filer."
- Q1, the owner's answer: "Priya and DeShawn file alone with the spouse counted in household size, so their tier 3 `Debto1.Quest11` rows and 2 known-defect entries are dropped." They leave in this commit, the one that first binds `Debto1.Quest11`, and their 2 entries go with them (§7.3: "in one commit").
- `13C` is MOVED, so moved-here asserts it through verification.json's (form_122a1, `13A`) row. The other five boxes are ADD and get addendum rows. Each cites the box's field-index label, and `14a` and `CheckBox1` also cite Q5 (DIG-65) and Q2 (DIG-136).
- `line11_annualized_income` loses its last binding, so its key goes. Its function stays, because `_line12b_annualized_cmi` calls it and `eligibility/tests/test_means_test_calculator.py` reaches it through `line12b_annualized_cmi`. Its name now describes the wrong line; §6.1 leaves renames for later.
- No tier 3 row checks `13A` or `CheckBox1`: Appendix D adds none. The new schema tests pin both, and tier 1's box cases prove `CheckBox1` ticks only box 1 or box 2.
- `ASSERTED_CASES` goes from 410 to 413 (+3), measured by diffing the collected IDs. Three tier 2 cases leave with their bindings: `13A` under `derived:line13a_median_income` and `13C` under `derived:line13c_difference` (both xfails), and `Quest11` under `derived:line11_annualized_income` (it passed). Six arrive, all passing: the five addendum rows and `13C`'s moved-here join.
- Known defects: delete exactly these 22 entries (86 → 64). Two tier 2 `wrong_box` entries are orphaned: `13A` `derived:line13a_median_income` and `13C` `derived:line13c_difference` (DIG-59). Two tier 3 entries leave with their Q1 rows: `Debto1.Quest11` priya and deshawn (DIG-59). Eighteen tier 3 entries now pass, a strict XPASS: `13C` and `Quest11` for all five personas (DIG-59), `14a` for all five (DIG-65), and `Debto1.Quest11` for maria, james and sarah (DIG-59).

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_form_122a1_schema.py b/backend/apps/forms/tests/test_form_122a1_schema.py
index 26cf852..10f94f6 100644
--- a/backend/apps/forms/tests/test_form_122a1_schema.py
+++ b/backend/apps/forms/tests/test_form_122a1_schema.py
@@ -6,8 +6,10 @@ from decimal import Decimal
 import pytest
 from django.contrib.auth import get_user_model

-from apps.districts.models import District
+from apps.districts.models import District, MedianIncome
 from apps.eligibility.cmi import IncomeNotSplit
+from apps.eligibility.services.means_test_calculator import MeansTestCalculator
+from apps.forms.registry import packet
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.forms.tests.test_derivations import TEN_SOURCES
@@ -66,6 +68,23 @@ def session_with_income(session):
     return session


+@pytest.fixture
+def median_income(session):
+    # ILND's 2025 medians, one per household size.
+    return MedianIncome.objects.create(
+        district=session.district,
+        effective_date=date(2025, 11, 1),
+        family_size_1=Decimal("71304.00"),
+        family_size_2=Decimal("91526.00"),
+        family_size_3=Decimal("110712.00"),
+        family_size_4=Decimal("134366.00"),
+        family_size_5=Decimal("145466.00"),
+        family_size_6=Decimal("156566.00"),
+        family_size_7=Decimal("167666.00"),
+        family_size_8=Decimal("178766.00"),
+    )
+
+
 @pytest.mark.django_db
 class TestForm122A1Schema:
     def test_schema_loads(self):
@@ -125,3 +144,70 @@ class TestForm122A1Schema:
         field_map = resolve(load_schema("form_122a1"), session_with_income)

         assert field_map["13B"] == "3"
+
+    def test_line_11_prints_monthly_income_and_only_line_12b_multiplies_it_by_12(self, session):
+        # Line 11 adds lines 2-10 for the month in Column A and in the total box, whose
+        # second widget is line 12a's copy; line 12b is the year (step 2 spec §6.1, C1).
+        IncomeInfo.objects.create(session=session, **TEN_SOURCES)
+
+        field_map = resolve(load_schema("form_122a1"), session)
+
+        # Every source but Social Security's 32.00: 1023.00 - 32.00.
+        printed = (field_map.get("Debto1.Quest11"), field_map.get("Quest11"), field_map.get("12B"))
+        assert printed == ("991.00", "991.00", "11892.00")
+
+    def test_line_13_prints_the_state_and_the_median_the_means_test_compared_against(
+        self, session_with_income, median_income
+    ):
+        # DIG-51: the filer counts 3 people in the household, while single with no dependents
+        # would size it at 1. Line 13 must print the median the means test used.
+        DebtorInfo.objects.create(
+            session=session_with_income,
+            first_name="Maria",
+            last_name="Torres",
+            ssn="900-11-0001",  # IRS-reserved range: synthetic
+            date_of_birth=date(1988, 6, 15),
+            state="IL",
+            household_size=3,
+        )
+        MeansTestCalculator(session_with_income).calculate()
+
+        field_map = resolve(load_schema("form_122a1"), session_with_income)
+
+        printed = (field_map.get("13A"), field_map.get("13B"), field_map.get("13C"))
+        assert printed == ("IL", "3", "110712.00")
+
+    def test_line_13_median_and_the_result_wait_for_the_eligibility_check(
+        self, session_with_income
+    ):
+        # Before the means test runs there is no median to print and nothing to compare.
+        field_map = resolve(load_schema("form_122a1"), session_with_income)
+
+        assert sorted({"13C", "14a", "CheckBox1"} & field_map.keys()) == []
+
+    @pytest.mark.parametrize(
+        "monthly_wages,line_14,page_1,form_122a2_applies",
+        [
+            # Exactly the median ($71,304 a year) is below it (DIG-136).
+            ("5942.00", "/12b less or equal to 13", "/No Abuse", False),
+            ("5942.01", "/12b more than 13", "/Presumption of abuse applies", True),
+        ],
+        ids=["at_the_median", "one_cent_over"],
+    )
+    def test_the_result_ticks_agree_with_whether_form_122a2_is_in_the_packet(
+        self, session, median_income, monthly_wages, line_14, page_1, form_122a2_applies
+    ):
+        # Line 14 and the page-1 result follow the form's own instruction (Q5, DIG-65), by
+        # the one comparison that decides the packet, so they never disagree at the median.
+        IncomeInfo.objects.create(
+            session=session,
+            monthly_gross_wages=Decimal(monthly_wages),
+            marital_status="single",
+            number_of_dependents=0,
+        )
+        MeansTestCalculator(session).calculate()
+
+        field_map = resolve(load_schema("form_122a1"), session)
+
+        assert (field_map.get("14a"), field_map.get("CheckBox1")) == (line_14, page_1)
+        assert ("form_122a2" in packet(session)) is form_122a2_applies
PATCH
```

The line 11 test gives the ten sources their powers of two and requires `Debto1.Quest11`, `Quest11` and `12B` to print 991.00, 991.00 and 11892.00 (every source but Social Security's 32.00, then × 12). The line 13 test stores a household of 3 for a filer who is single with no dependents, runs the means test, and requires `13A`, `13B` and `13C` to print IL, 3 and 110712.00. The wait test requires `13C`, `14a` and `CheckBox1` to be absent before the means test runs. The ticks test runs the means test on $5,942.00 a month (exactly the $71,304 median for one) and on one cent more, and requires the ticks to agree with whether Form 122A-2 is in the packet.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_122a1_schema.py -q -p no:cacheprovider 2>&1 | tail -60
```

Expected: FAIL — `5 failed, 8 passed`. Line 11 reads `assert (None, '11892.00', '11892.00') == ('991.00'`: Column A is unbound and the total prints CMI × 12. Line 13 reads `assert ('71304.00', '3', '-47304.00') == ('IL', '3', '110712.00')`: the state box prints a median sized for one person, and 13C a difference. The wait test finds 13C printed without a means test (`Left contains one more item: '13C'`), and both tick cases read `assert (None, None) ==`, because 14a and CheckBox1 are unbound. The ticks test's packet line can't be red on its own; it guards that the ticks and the packet keep one comparison.

- [ ] **Step 3: Bind line 11, chain d and the result boxes**

```bash
git apply <<'PATCH'
diff --git a/data/forms/schemas/form_122a1.json b/data/forms/schemas/form_122a1.json
index d5a30e3..1065c0e 100644
--- a/data/forms/schemas/form_122a1.json
+++ b/data/forms/schemas/form_122a1.json
@@ -37,6 +37,27 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "CheckBox1",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "below": "/No Abuse",
+        "above": "/Presumption of abuse applies"
+      },
+      "page": 1,
+      "label": "Page 1: There is no presumption of abuse, or Form 122A-2 decides",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "median_comparison",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "Debto1.Quest2.0",
       "type": "text",
@@ -173,16 +194,33 @@
       "row": null,
       "legal_review": false
     },
+    {
+      "pdf_field": "Debto1.Quest11",
+      "type": "text",
+      "source": "derived",
+      "page": 2,
+      "label": "Line 11: Total current monthly income, Column A",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "cmi",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
     {
       "pdf_field": "Quest11",
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Line 11: Annualized income",
+      "label": "Line 11: Total current monthly income, copied to line 12a",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "line11_annualized_income",
+      "rule": "cmi",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -212,11 +250,11 @@
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Line 13A: State median income",
+      "label": "Line 13: State in which you live",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "line13a_median_income",
+      "rule": "state",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
@@ -246,11 +284,32 @@
       "type": "text",
       "source": "derived",
       "page": 2,
-      "label": "Line 13C: Difference",
+      "label": "Line 13: Median family income for your state and size of household",
+      "required": false,
+      "conditional_on": null,
+      "value": null,
+      "rule": "line13a_median_income",
+      "ingest_key": null,
+      "binding": null,
+      "repeat": null,
+      "repeat_capacity": null,
+      "row": null,
+      "legal_review": false
+    },
+    {
+      "pdf_field": "14a",
+      "type": "checkbox",
+      "source": "derived",
+      "choices": {
+        "below": "/12b less or equal to 13",
+        "above": "/12b more than 13"
+      },
+      "page": 2,
+      "label": "Line 14: How do the lines compare?",
       "required": false,
       "conditional_on": null,
       "value": null,
-      "rule": "line13c_difference",
+      "rule": "median_comparison",
       "ingest_key": null,
       "binding": null,
       "repeat": null,
PATCH
```

The schema goes from 15 objects to 18: `CheckBox1` goes before the line 2 box, `Debto1.Quest11` before `Quest11`, and `14a` after `13C`.

- [ ] **Step 4: Read the stored median, add median_comparison and reword the header**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index c196ca7..bfeffed 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -2,9 +2,11 @@
 Factual/clerical derivations (DERIVATIONS) and section-applicability
 predicates (PREDICATES) for the fill engine.

-UPL boundary: these encode ONLY facts and clerical transforms. No legal
-conclusion (exemption-statute choice, debt priority, means-test verdict) may
-live here — those are ``asked`` + ``legal_review`` in the schema.
+UPL boundary: these encode ONLY facts and clerical transforms. A rule may
+apply a comparison the form itself spells out (122A-1 line 14: line 12b
+against line 13), but no rule may choose exemptions, decide priority, or
+answer anything the form leaves to the filer — those are ``asked`` +
+``legal_review`` in the schema.
 """

 from __future__ import annotations
@@ -14,7 +16,7 @@ from datetime import date
 from decimal import Decimal
 from functools import reduce

-from apps.eligibility.cmi import IncomeNotSplit, current_monthly_income
+from apps.eligibility.cmi import IncomeNotSplit, current_monthly_income, is_above_median
 from apps.intake.models import IntakeSession

 _ZERO = Decimal("0.00")
@@ -325,27 +327,26 @@ def _line12b_annualized_cmi(session: IntakeSession) -> str:


 def _line13a_median_income(session: IntakeSession) -> str:
-    from apps.districts.models import MedianIncome
+    """Line 13: the median the means test compared against (DIG-51), blank before it runs."""
+    means_test = getattr(session, "means_test", None)
+    if means_test is None:
+        return ""
+    return _fmt(means_test.median_income_threshold)

-    try:
-        income_info = session.income_info
-        size = 1 + income_info.number_of_dependents
-        if income_info.marital_status in ("married_joint", "married_separate"):
-            size += 1
-    except Exception:
-        size = 1
-    median = (
-        MedianIncome.objects.filter(district=session.district).order_by("-effective_date").first()
-    )
-    if median is None:
-        return "0.00"
-    return _fmt(median.get_median_income(size))

+def _median_comparison(session: IntakeSession) -> str:
+    """
+    Line 14 and the page-1 result: line 12b against line 13, as the form says to compare.

-def _line13c_difference(session: IntakeSession) -> str:
-    annualized = Decimal(_line11_annualized_income(session))
-    median = Decimal(_line13a_median_income(session))
-    return _fmt(annualized - median)
+    The packet's comparison (exactly the median is below it, DIG-136), so the ticks always
+    agree with whether Form 122A-2 is filed. Blank before the means test runs.
+    """
+    means_test = getattr(session, "means_test", None)
+    if means_test is None:
+        return ""
+    if is_above_median(means_test.calculated_cmi, means_test.median_income_threshold):
+        return "above"
+    return "below"


 # ---------------------------------------------------------------------------
@@ -556,10 +557,9 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
     "line6b_child_support_alimony": _line6b_child_support_alimony,
     "line7_other_income": _line7_other_income,
     "other_income_label": _other_income_label,
-    "line11_annualized_income": _line11_annualized_income,
     "line12b_annualized_cmi": _line12b_annualized_cmi,
     "line13a_median_income": _line13a_median_income,
-    "line13c_difference": _line13c_difference,
+    "median_comparison": _median_comparison,
     # Form 103B fee waiver derivations
     "fee_waiver_household_size": _fee_waiver_household_size,
     "fee_waiver_monthly_income": _fee_waiver_monthly_income,
PATCH
```

`median_comparison` imports `is_above_median` beside `current_monthly_income`. `_line13c_difference` and the `line11_annualized_income` key go, since no schema binds them after Step 3 (E007).

- [ ] **Step 5: Give tier 2 the five ADD rows and its new count**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_oracle_tier2.py b/backend/apps/forms/tests/test_oracle_tier2.py
index 2268628..531cf62 100644
--- a/backend/apps/forms/tests/test_oracle_tier2.py
+++ b/backend/apps/forms/tests/test_oracle_tier2.py
@@ -34,7 +34,7 @@ from apps.forms.tests.oracle import case_param
 TIER = "2"
 CHECKED_BASES = {"adjudicated", "sampled_ok"}
 LEAVE_BLANK = "leave blank"
-ASSERTED_CASES = 410
+ASSERTED_CASES = 413


 def _audit_dir():
diff --git a/data/forms/field_index/audit/step2_verification.json b/data/forms/field_index/audit/step2_verification.json
index 56f5005..5477246 100644
--- a/data/forms/field_index/audit/step2_verification.json
+++ b/data/forms/field_index/audit/step2_verification.json
@@ -268,5 +268,55 @@
     "status": "confirmed",
     "correct_target": "terrorism If necessary list other sources on a separate page and put the total below 1",
     "evidence": "Field index: this box p2 line 10 'Income from all other sources not listed above - source description, row 1' (adjudicated), beside its amount Debto1.Quest10A. Step 2 spec §5.5 table (other: 122A-1 line 10, \"Other income\"), §6.2 and Appendix E 5: the line 10 source box prints \"Other income\" when other income is above $0."
+  },
+  {
+    "schema": "form_122a1",
+    "pdf_field": "Debto1.Quest11",
+    "producer": "derived:cmi",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Debto1.Quest11",
+    "evidence": "Field index: Debto1.Quest11 p2 line 11, Column A (Debtor 1), 'Calculate your total current monthly income - add lines 2 through 10 for the column (monthly)' (adjudicated). Step 2 spec §6.1 (C1, two income totals): CMI, without Social Security, goes on 122A-1 lines 11-12b; lines 5 and 7 are never asked and count as zero. The audit's row on Quest8A names this box for the income total, under the old line8a_total_gross_income key, not cmi."
+  },
+  {
+    "schema": "form_122a1",
+    "pdf_field": "Quest11",
+    "producer": "derived:cmi",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "Quest11",
+    "evidence": "Field index: Quest11 p2, one full name with two widgets: line 11, column Total, 'Total current monthly income (Column A + Column B) (monthly)', and line 12a, 'Copy your total current monthly income from line 11 (monthly; then multiply by 12)', both adjudicated. Both are monthly; only 12B is the year. Step 2 spec §6.1 (C1): CMI goes on 122A-1 lines 11-12b. The audit's row on this box judged the old line11_annualized_income binding, which printed CMI x 12."
+  },
+  {
+    "schema": "form_122a1",
+    "pdf_field": "13A",
+    "producer": "derived:state",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "13A",
+    "evidence": "Field index: 13A p2 line 13 'Fill in the state in which you live.' (adjudicated). Step 2 spec §6.4 (122A-1: line 13's state) and Appendix B chain d: 13A takes derived:state; its old median binding moves to 13C, where the audit's verified row for 13A places it."
+  },
+  {
+    "schema": "form_122a1",
+    "pdf_field": "14a",
+    "producer": "derived:median_comparison",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "14a",
+    "evidence": "Field index: 14a p2, one full name with two widgets, 'How do the lines compare?' (adjudicated): line 14a, state /12b less or equal to 13, 'Line 12b is less than or equal to line 13. On the top of page 1, check box 1'; line 14b, state /12b more than 13, 'Line 12b is more than line 13. On the top of page 1, check box 2'. Owner's answer Q5 (DIG-65; step 2 spec §3, §6.3): tick line 14 and the page-1 box from line 12b against line 13; at or below the median is below (Q2, DIG-136)."
+  },
+  {
+    "schema": "form_122a1",
+    "pdf_field": "CheckBox1",
+    "producer": "derived:median_comparison",
+    "original_verdicts": [],
+    "final_verdicts": ["correct"],
+    "status": "confirmed",
+    "correct_target": "CheckBox1",
+    "evidence": "Field index: CheckBox1 p1, three widgets (adjudicated): top box 1, state /No Abuse, 'There is no presumption of abuse.'; top box 2, state /Presumption of abuse applies, 'The calculation to determine if a presumption of abuse applies will be made under Chapter 7 Means Test Calculation (Official Form 122A-2).'; top box 3, state /Does not apply (qualified military service). Owner's answer Q5 (DIG-65; step 2 spec §3, §6.3): at or below the median, box 1; above, box 2; box 3 is never ticked."
   }
 ]
PATCH
```

`ASSERTED_CASES` changes from 410 to 413 for the reasons above.

- [ ] **Step 6: Drop the Q1 rows from tier 3 and delete the 22 known-defect entries**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/known_defects.json b/backend/apps/forms/tests/known_defects.json
index b4d5fdd..666b199 100644
--- a/backend/apps/forms/tests/known_defects.json
+++ b/backend/apps/forms/tests/known_defects.json
@@ -31,22 +31,6 @@
     "class": "wrong_box",
     "ticket": "DIG-77"
   },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13A",
-    "tier": "2",
-    "case": "derived:line13a_median_income",
-    "class": "wrong_box",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13C",
-    "tier": "2",
-    "case": "derived:line13c_difference",
-    "class": "wrong_box",
-    "ticket": "DIG-59"
-  },
   {
     "form_type": "form_122a2",
     "pdf_field": "Quest1",
@@ -407,166 +391,6 @@
     "class": "wrong_value",
     "ticket": "DIG-79"
   },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13C",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13C",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13C",
-    "tier": "3",
-    "case": "maria",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13C",
-    "tier": "3",
-    "case": "priya",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "13C",
-    "tier": "3",
-    "case": "sarah",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "14a",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-65"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "14a",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-65"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "14a",
-    "tier": "3",
-    "case": "maria",
-    "class": "wrong_value",
-    "ticket": "DIG-65"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "14a",
-    "tier": "3",
-    "case": "priya",
-    "class": "wrong_value",
-    "ticket": "DIG-65"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "14a",
-    "tier": "3",
-    "case": "sarah",
-    "class": "wrong_value",
-    "ticket": "DIG-65"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest11",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest11",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest11",
-    "tier": "3",
-    "case": "maria",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest11",
-    "tier": "3",
-    "case": "priya",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Debto1.Quest11",
-    "tier": "3",
-    "case": "sarah",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Quest11",
-    "tier": "3",
-    "case": "deshawn",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Quest11",
-    "tier": "3",
-    "case": "james",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Quest11",
-    "tier": "3",
-    "case": "maria",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Quest11",
-    "tier": "3",
-    "case": "priya",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
-  {
-    "form_type": "form_122a1",
-    "pdf_field": "Quest11",
-    "tier": "3",
-    "case": "sarah",
-    "class": "wrong_value",
-    "ticket": "DIG-59"
-  },
   {
     "form_type": "schedule_j",
     "pdf_field": "22c",
diff --git a/backend/apps/forms/tests/test_oracle_tier3.py b/backend/apps/forms/tests/test_oracle_tier3.py
index 2721322..96f3988 100644
--- a/backend/apps/forms/tests/test_oracle_tier3.py
+++ b/backend/apps/forms/tests/test_oracle_tier3.py
@@ -116,7 +116,6 @@ EXPECTED = {
         "form_122a1": {
             "Debto1.Quest7": "",
             "Debto1.Quest9": "0.00",
-            "Debto1.Quest11": "12000.00",
             "Quest11": "12000.00",
             "12B": "144000.00",
             "13B": "4",
@@ -148,7 +147,6 @@ EXPECTED = {
         "form_122a1": {
             "Debto1.Quest7": "",
             "Debto1.Quest9": "0.00",
-            "Debto1.Quest11": "3500.00",
             "Quest11": "3500.00",
             "12B": "42000.00",
             "13B": "2",
PATCH
```

The tier 3 patch removes only Priya's and DeShawn's `Debto1.Quest11` rows. The known-defects patch only deletes the 22 entries named above.

- [ ] **Step 7: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_form_122a1_schema.py -q -p no:cacheprovider 2>&1 | tail -60
```

Expected: `13 passed`.

- [ ] **Step 8: Run the oracle, the list check and the schema check**

```bash
set -eo pipefail
source .claude/forms-step2b.env
cd backend && $PY -m pytest apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_known_defects.py apps/forms/tests/test_checks.py -q -p no:cacheprovider 2>&1 | tail -1
```

Expected: `1224 passed, 1 skipped, 64 xfailed`: one expected failure per remaining entry, no XPASS, no orphan, and every schema passes the system check.

- [ ] **Step 9: Run every gate**

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

Task 9 changes no page or flow, so the journeys don't run for it.

- [ ] **Step 10: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/tests/known_defects.json \
  backend/apps/forms/tests/test_form_122a1_schema.py \
  backend/apps/forms/tests/test_oracle_tier2.py \
  backend/apps/forms/tests/test_oracle_tier3.py \
  data/forms/field_index/audit/step2_verification.json \
  data/forms/schemas/form_122a1.json
git commit -F - <<'MSG'
fix(forms): Form 122A-1 prints monthly income on line 11, the means test's median on line 13, and ticks the result

Form 122A-1's result follows the step 2 spec (Appendix A.5; chain d of
Appendix B; §6.1 C1 and Rule 9; Q5):
- Line 11 prints current monthly income (cmi) in Column A
  (Debto1.Quest11, new) and in the total box, whose second widget is
  line 12a's copy (Quest11, re-ruled from line11_annualized_income,
  which printed CMI x 12). Line 12b alone multiplies by 12.
- Line 13 prints the filer's state on 13A (state) and, on 13C, the
  median the means test compared against (line13a_median_income, moved
  from 13A). Its body now reads the stored
  MeansTest.median_income_threshold instead of re-sizing the household
  from dependents and marital status (DIG-51); it prints blank before
  the means test runs.
- Line 14 (14a) and the page-1 result (CheckBox1) tick from the new rule
  median_comparison: below at or under the median (box 1, "No Abuse"),
  above over it (box 2). It uses eligibility.cmi.is_above_median on the
  stored means test, the comparison that decides whether 122A-2 is in
  the packet, so the ticks never disagree with it. Box 3 (military) is
  never mapped. The states come from the field index.
- The derivations.py header is reworded (Rule 9): a rule may apply a
  comparison the form itself spells out, but never choose exemptions,
  decide priority, or answer what the form leaves to the filer.

Rules that lost their last binding are deleted: line13c_difference and
the line11_annualized_income key (its function stays as 12b's helper).

Oracle:
- step2_verification.json gains the five ADD rows: 13A, Debto1.Quest11,
  Quest11, 14a and CheckBox1 (27 -> 32). 13C is MOVED and asserted by
  the moved-here join through the audit's verified 13A row.
- Q1: Priya's and DeShawn's Debto1.Quest11 tier 3 rows leave EXPECTED.

Clears 22 known-defect entries (86 -> 64): 2 tier 2 orphans (13A, 13C),
2 tier 3 orphans removed with their Q1 rows, and 18 tier 3 entries that
now pass (strict XPASS): 13C x5, Quest11 x5, 14a x5 and Debto1.Quest11
for Maria, James and Sarah.

ASSERTED_CASES 410 -> 413 (+3), measured by diffing the collected IDs:
- 3 tier 2 cases left with their bindings (13A line13a_median_income,
  13C line13c_difference, Quest11 line11_annualized_income);
- 6 new cases: 5 addendum rows and the 13C moved-here join. All pass.

New tests:
- test_line_11_prints_monthly_income_and_only_line_12b_multiplies_it_by_12
- test_line_13_prints_the_state_and_the_median_the_means_test_compared_against
- test_line_13_median_and_the_result_wait_for_the_eligibility_check
- test_the_result_ticks_agree_with_whether_form_122a2_is_in_the_packet
  (exactly at the median, and one cent over)

Refs DIG-51, DIG-59, DIG-65
MSG
git status --short
```
