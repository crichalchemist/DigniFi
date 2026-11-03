# Forms step 3f, the filing fee: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ask Form 101 line 8 ("How you will pay the fee") of every filer on a page after Complete, with the court's 150% poverty limit and the filer's own 103B line 2 figure shown beside it as information; put 103B in the packet exactly when the answer is the waiver; fill 103B lines 1–3 from the wizard and lines 4, 5, 7 and 9 from the page; and remove `FeeWaiverApplication`, its page and API, and the means test's fee-waiver flag.

**Architecture:** A dated `PovertyGuideline` table in `apps/districts` with a pure limit function; a pure-ish `apps/forms/services/fee_waiver.py` that works out 103B lines 1–3 from the household list and Schedule I, read by both the derivations and the page's API; one encrypted `FilingFee` record per session, saved through a session action `filing-fee` (GET/PUT) that locks and never reopens; the registry keys 103B on `FilingFee.payment_choice`, and `PreconditionMissing` gains a `page` so 101 and 103B refusals link to `/filing-fee`. The frontend replaces `FeeWaiverPage` with `FilingFeePage` at `/filing-fee`, which Complete always reaches.

**Tech Stack:** Django 5.0 + DRF (Python 3.11), `encrypted-model-fields` (Fernet), PostgreSQL 15 / sqlite for tests, pypdf 6.13.1 and PyMuPDF 1.27.2.3; React 19 + Vite 7 + TypeScript, vitest + Testing Library + MSW, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-02-forms-step3f-design.md` (cited `§`), approved by the owner on 2026-11-02 with its three questions answered as recommended. It draws from the umbrella `docs/superpowers/specs/2026-10-16-forms-step3-design.md` (§5.7, cited `U:`), the persona targets `docs/superpowers/specs/2026-10-16-forms-step3-personas.md` (cited `PS:`), and the scoping note `.superpowers/forms-step3/scope/fee-waiver.md` in the `forms-step3` worktree (cited `FW:`). Where this plan and the spec disagree, the spec wins, except at the errata and rulings listed under "For the owner at plan review"; say so in the ledger.

## Global Constraints

- **Encryption.** Every `FilingFee` answer is encrypted from the start: `payment_choice` and the three yes/no answers are `EncryptedCharField` (null = unanswered), the four texts `EncryptedTextField(blank=True, default="")`. `PovertyGuideline` holds public data and stays plaintext. A ciphertext test reads the raw column with SQL.
- **Values.** `payment_choice` ∈ `("pay_in_full", "installments", "waiver")`; null only means never saved, and a PUT of null is a 400. Yes/no answers ∈ `YES_NO` (`("yes", "no")`, `apps/intake/models.py:16`) or null. Anything else, and any key the action doesn't know, is a 400. Nothing starts answered.
- **Migrations.** districts `0004_povertyguideline` and `0005_poverty_guideline_2026` (Task 1, depending on `0003_medianincome_dated_table`); intake `0029_filingfee` (Task 3), `0030_fee_waiver_applications_to_filing_fee` and `0031_delete_feewaiverapplication` (Task 8); eligibility `0003_remove_meanstest_qualifies_for_fee_waiver` (Task 7, after `0002_add_above_median_fields`). No other app gets a migration. `makemigrations --check` passes after every task. Migration tests follow `apps/intake/tests/test_data_migrations.py` (the `migrate` fixture, a Postgres twin under `@pytest.mark.postgres` and `@ON_POSTGRES`).
- **The 2026 guideline** (FW:182, :184): `first_person=15960`, `each_additional=5680`, `effective_date=2026-01-15` (the Federal Register publication date, 91 FR 1797, doc. 2026-00755), `valid_through=2027-01-31`, `source_url="https://www.federalregister.gov/documents/2026/01/15/2026-00755/annual-update-of-the-hhs-poverty-guidelines"` (the plan's Task 1 checks the URL resolves before committing; if it doesn't, use the ASPE page `https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines` and say so in the ledger). The limit is `(first_person + each_additional × (n − 1)) × 3 / 2 / 12`, quantized to the cent `ROUND_HALF_UP`: 1 = 1995.00, 2 = 2705.00, 3 = 3415.00, 4 = 4125.00, 8 = 6965.00, +710.00 each.
- **Persona outcomes (§10):** line 8 Maria `waiver`, Sarah `waiver`, DeShawn `installments`, Andrés `installments`, James `pay_in_full`, Priya `pay_in_full`. Family 3/1/2/2/1/4. Page figure 2800.00 / 1750.00 / 3935.00 / 3370.00 / 4500.00 / 9880.00. Packets after Task 4: Maria 15, Sarah 15, DeShawn **14**, Andrés 14, James 14, Priya 15. Every persona's CMI and median result are unchanged. Maria and Sarah answer line 4 No, line 7 No, line 9 No, and line 5 the owner-approved drafts (§10, verbatim).
- **Blank, not 0.00** (U §4.5): 103B has no "write $0" instruction. `undefined_3` blank unless `married_together`; `undefined_5` prints only a counted non-cash value above $0; `How many dependents` and the `Your dependents` tick only above 0.
- **No verdict.** No sentence, label, test name or log says "qualify", "eligible", "you should", or compares the figure to the limit for the filer `[UPL]`. The page shows the two figures and "The court decides."
- **Words.** Text quoted from Form 101 or 103B goes in `frontend/src/constants/formText.ts` (unscored). DigniFi's own sentences go in `frontend/src/constants/copy.ts` and pass `src/test/reading-level.test.ts`. `// DRAFT: counsel C-7` beside every sentence of §6.2 and §6.4's line 5 note, as a code comment.
- **The forms.** Every new or re-ruled placement gets its row in `data/forms/field_index/audit/step2_verification.json` in the same commit; a renamed rule's row is re-keyed in the same commit (`test_every_step2_placement_matches_a_binding`). Every new rule bound to a text or choice box gets its `RULE_FIXES` entry (checkbox rules get none, as today). A box that gains a binding leaves `form_101.unbound.json` / `form_103b.unbound.json`. `known_defects.json` stays `[]`. Each task changes `ASSERTED_CASES` (`test_oracle_tier2.py:37`, 475 at `dc31b7a`) by the delta it counts and states.
- **Tests** are named after outcomes and use only synthetic data (SSNs 900-xx-xxxx, phones 555-0100 to 555-0199). Never import `_today` by name; a dated test sets its day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`. The backend suite pins `_today` to 2026-10-16.
- **Gates (each task):** `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 -q -p no:cacheprovider`; `/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/` (ruff 0.8.5, the version `ci.yml` pins; never a bare `ruff`); `manage.py check`; `manage.py makemigrations --check --dry-run` when models change; `DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres` when a task adds a migration or a lock entry; when the frontend changes: `npx vitest run --maxWorkers=2`, `npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit`, `npm run lint`, `npm run format:check`. **Never run `tsc -b`.** The journeys (`zsh .claude/e2e.sh 2`) run at the end of Tasks 1, 5, 8 and 9. Task 4 and Task 8 also run the frontend gates. **Between Task 4 and Task 5 the journeys are expected to fail** (fresh journey accounts have no `FilingFee` until the page exists); Task 4 does not run them.
- **The machine is shared with audio work.** Check `uptime` before a full suite or the journeys; run them only with the 1-minute load under 10, and the journeys only with the 5-minute load under 8 as well.
- **Commits.** `PYTHONDONTWRITEBYTECODE=1`. Stage by explicit path only (never `git add -A`, `git add .`, `git commit -a`). `/usr/bin/git`, one plain command per call; every task writes its message to `/tmp/3f-taskN-msg.txt` and commits with `/usr/bin/git commit -F /tmp/3f-taskN-msg.txt`. **No `Co-Authored-By`, `Claude-Session` or other agent trailer**, whatever a harness asks. Never stage `.serena/`, `DESIGN.md`, `assets/`, `.impeccable`, `.claude/` or `.superpowers/`. Pre-commit's prettier may rewrite a staged file on the first commit: re-add it and commit again.
- **Branch and outward actions.** Work on `feat/forms-step3f` (from develop `2fd7e6e`); the PR, when the owner asks for one, targets `develop`. No push, PR, merge, deploy or production command from this plan. Never use the shared `dignifi_dev` database; never print or commit an API key.
- **CLAUDE.md gotchas** change in the task whose code changes the behaviour they describe (each task's Interfaces block names them); a task states each edit as the sentences as they read after it.

## Review Focus

Five inputs the spec implies that no test it names covers, most likely to bite a filer first. Each test lives in the owning task.

1. **A filer who typed waiver answers, then switches to installments**: the page's PUT carries `payment_choice` only, and the stored waiver answers are kept, so they come back if the filer picks the waiver again (Task 5).
2. **Line 5 typed as only spaces**: 103B is refused with the `/filing-fee` link, as if blank (Task 4).
3. **Line 4 answered Yes with an explanation, then No**: the explanation stays stored, and `4 type` prints nothing (Task 4).
4. **A counted spouse with non-cash help but no value**: `check 3` prints Yes, `3 type` carries "Spouse: <kind>", and `undefined_5` stays blank (Task 2).
5. **An old `/fee-waiver` link** lands on `/filing-fee` (Task 5).

## For the owner at plan review

The plan proceeds on its own reading of each item below. The owner's answer goes in the ledger before the task that depends on it starts.

- **Spec errata.**
  - §8.1: `Check Box7`'s states are written decoded in a schema (`/Pay entirely`, `/Pay in installments`, `/Request fees waived`); `field_index.py:23-30` turns the index's `#20` into a space (Task 4).
  - §11: the 101 and 103B refusal sentences are the server's, in `registry.py` with the other precondition sentences, not `copy.ts` (Task 4).
  - §6.5: a PUT of `payment_choice: null` is a 400; the frame's "or null" was wrong (Task 3).
  - §8.2/§16: `3 type` now prints the 8f kinds, so its fix is `income_info`, not `/filing-fee` (Task 2).
  - §4 and §10 cite `test_completion.py:1000-1017` and `test_api_readback.py`'s `WAIVER_FILERS`; the test runs `:1000-1031`, and the names are `QUALIFIES` and `APPLIES` (Tasks 4, 7, 8).
- **Plan decisions the spec leaves open.**
  - The text limits are 520 (lines 4 and 5) and 420 (lines 7 and 9) characters, measured against the boxes; `check()` at Generate stays the last word (Task 3).
  - The 103A link is the AO's current B 103A page (`…-installments-0`); the address without `-0` is the superseded Form 3A (Task 5).
  - Priya's journey ends on `/filing-fee`, checking the limit sentence, without answering (Task 5).
  - The 2026 poverty row expires on 2027-01-31, two months before the median row: from 2027-02-01 the page shows its no-table sentence and the journeys' limit checks fail until the 2027 row is loaded (Task 1).
  - `household.fee_waiver_household_size` loses its last reader with the old page, and stays (Task 5).
- **Logged, not fixed:** `docs/security/data-protection.md:51` (wrong since 3e2 about income encryption), the "you may qualify for a fee waiver" examples in `docs/PLAIN_LANGUAGE_GUIDE.md:254,477,480` and `docs/UPL_COMPLIANCE.md:139,222`, and `form_103b.unbound.json` entries stale since step 2 for boxes 3f doesn't touch. Each is a proposed ticket, filed only with the owner's yes.

## Before you start (once per worktree)

- Work in `/Volumes/Containers/DigniFi/.claude/worktrees/forms-step3f` (branch `feat/forms-step3f`, which holds the spec and this plan). Every command block runs from that worktree's root.
- Backend tools come from the main checkout's virtualenv, and frontend tools from its `node_modules`. Pre-commit's eslint hook expects that symlink.
- The journeys and the Postgres tests need Colima running, with the `dignifi-db-1` Postgres container answering on host port 5433. The journeys also need nothing listening on ports 8000, 5173 or 4010.
- `pytest` uses `config.settings.test` (sqlite in memory). The Postgres tests use `config.settings.test_postgres`, which reads `DATABASE_URL`. `manage.py` and the journeys use the database below.

```bash
set -eo pipefail
mkdir -p backend/logs .claude   # the audit log handler needs backend/logs; CI creates it too
[ -e frontend/node_modules ] || ln -s /Volumes/Containers/DigniFi/frontend/node_modules frontend/node_modules
# CI's synthetic Fernet key (it encrypts nothing real), read from ci.yml rather than copied here
FERNET=$(sed -n 's/^ *FIELD_ENCRYPTION_KEY: //p' .github/workflows/ci.yml | head -1)
[ -n "$FERNET" ]
# A database of its own keeps the shared dev database on develop's migrations. The Postgres
# tests create and drop their own test database beside it.
docker exec dignifi-db-1 dropdb -U dignifi --if-exists dignifi_forms_step3f
docker exec dignifi-db-1 createdb -U dignifi dignifi_forms_step3f
cat > .claude/forms-step3f.env <<ENV
# Settings for forms step 3f (git-ignored). Source from the worktree root.
export PY=/Volumes/Containers/DigniFi/backend/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_forms_step3f
export DJANGO_SECRET_KEY=test-only-not-a-secret
export DEBUG=True
export ALLOWED_HOSTS=localhost,127.0.0.1
export CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
export FIELD_ENCRYPTION_KEY=$FERNET
export OCR_PROVIDER=openai
export OPENAI_API_KEY=e2e-dummy-key
export OPENAI_BASE_URL=http://127.0.0.1:4010/v1
ENV
source .claude/forms-step3f.env && $PY -c "import pypdf, pymupdf; assert pypdf.__version__ == '6.13.1', pypdf.__version__; assert pymupdf.__version__ == '1.27.2.3', pymupdf.__version__"
/usr/bin/git check-ignore -q .claude/forms-step3f.env
/usr/bin/git check-ignore -q .claude/e2e.sh
echo "env file is ignored"
```

Expected: `env file is ignored`. Every later command block assumes `source .claude/forms-step3f.env`, which gives `$PY`.

The journeys run through one script, which Tasks 1, 5, 8 and 9 call. Write it now:

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
source .claude/forms-step3f.env
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

It is 3e1's script (`docs/superpowers/plans/2026-10-24-forms-step3e1.md`, "Before you start") with the env file renamed. A run prints `RUN 1 exit=0: 8 passed`. A failed run prints the failing journeys; read the trace under `frontend/test-results/` before running again, and don't retry blindly. Journeys are sensitive to machine load: check `uptime` before blaming the task.

Check the baseline before Task 1 (with the 1-minute load under 10):

```bash
set -eo pipefail
source .claude/forms-step3f.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run --maxWorkers=2 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
zsh .claude/e2e.sh 2
```

Expected: no failures, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, no output from tsc or eslint, `All matched files use Prettier code style!`, and `8 passed` on both journey runs. Record the counts you get in the ledger; each task's gate compares against them. The only ruff gate is `ruff check`, as in CI (`ci.yml:29`): `ruff format --check` is no gate.

---

## File Structure

Every file a task creates, modifies, deletes or checks, from the tasks' **Files** blocks.

| File                                                                                    | What changes  | Tasks                     |
| --------------------------------------------------------------------------------------- | ------------- | ------------------------- |
| `backend/apps/districts/models.py`                                                      | modify        | 1                         |
| `backend/apps/districts/migrations/0004_povertyguideline.py`                            | create        | 1                         |
| `backend/apps/districts/migrations/0005_poverty_guideline_2026.py`                      | create        | 1                         |
| `backend/apps/districts/poverty.py`                                                     | create        | 1                         |
| `backend/apps/districts/tests/test_poverty.py`                                          | create        | 1                         |
| `backend/conftest.py`                                                                   | modify        | 1, 8                      |
| `docs/REFERENCE_TABLES.md`                                                              | check, modify | 1, 7, 9                   |
| `CLAUDE.md`                                                                             | check, modify | 1, 2, 3, 4, 5, 6, 7, 8, 9 |
| `backend/apps/forms/services/fee_waiver.py`                                             | create        | 2                         |
| `backend/apps/forms/services/derivations.py`                                            | modify        | 2, 4                      |
| `data/forms/schemas/form_103b.json`                                                     | modify        | 2, 4                      |
| `data/forms/field_index/audit/step2_verification.json`                                  | modify        | 2, 4                      |
| `data/forms/field_index/audit/form_103b.unbound.json`                                   | modify        | 2, 4                      |
| `backend/apps/forms/tests/test_form_103b_answers.py`                                    | modify, test  | 2, 8                      |
| `backend/apps/forms/tests/test_form_103b_schema.py`                                     | modify, test  | 2, 8                      |
| `backend/apps/forms/tests/test_schedule_j_schema.py`                                    | test          | 2                         |
| `backend/apps/forms/tests/test_rule_fixes.py`                                           | test          | 2, 4                      |
| `backend/apps/forms/tests/test_check.py`                                                | test          | 2                         |
| `backend/apps/forms/tests/test_download_action.py`                                      | test          | 2, 4                      |
| `backend/apps/forms/tests/test_oracle_tier2.py`                                         | test          | 2, 4                      |
| `backend/apps/forms/tests/test_oracle_tier3.py`                                         | test          | 2, 4                      |
| `backend/apps/intake/models.py`                                                         | modify        | 3, 8                      |
| `backend/apps/intake/migrations/0029_filingfee.py`                                      | create        | 3                         |
| `backend/apps/intake/serializers.py`                                                    | modify        | 3, 8                      |
| `backend/apps/intake/filing_fee.py`                                                     | create        | 3                         |
| `backend/apps/intake/views.py`                                                          | modify        | 3, 7, 8                   |
| `backend/apps/intake/tests/builders.py`                                                 | modify        | 3                         |
| `backend/apps/intake/tests/test_filing_fee.py`                                          | create        | 3                         |
| `backend/apps/intake/tests/test_session_lock.py`                                        | modify        | 3                         |
| `backend/apps/intake/tests/test_data_migrations.py`                                     | modify        | 3, 8                      |
| `backend/apps/forms/registry.py`                                                        | modify        | 4                         |
| `backend/apps/forms/views.py`                                                           | modify        | 4                         |
| `data/forms/schemas/form_101.json`                                                      | modify        | 4                         |
| `data/forms/field_index/audit/form_101.unbound.json`                                    | modify        | 4                         |
| `backend/apps/intake/management/commands/seed_demo_data.py`                             | modify        | 4, 7, 8                   |
| `backend/apps/forms/tests/test_filing_fee_forms.py`                                     | create        | 4                         |
| `backend/apps/forms/tests/test_registry.py`                                             | modify, test  | 4, 8                      |
| `backend/apps/forms/tests/test_form_views.py`                                           | modify, test  | 4, 8                      |
| `backend/apps/forms/tests/test_printed_page.py`                                         | modify, test  | 4, 8                      |
| `backend/apps/forms/tests/test_api_readback.py`                                         | modify, test  | 4, 7, 8                   |
| `backend/apps/intake/tests/test_seed_demo_data.py`                                      | modify, test  | 4, 7, 8                   |
| `frontend/src/pages/FormDashboard.tsx`                                                  | modify        | 4, 6                      |
| `frontend/e2e/journeys/deshawn-assets.spec.ts`                                          | modify        | 4, 5                      |
| `frontend/src/pages/FilingFeePage.tsx`                                                  | create        | 5                         |
| `frontend/src/pages/__tests__/FilingFeePage.test.tsx`                                   | create        | 5                         |
| `frontend/src/constants/filingFee.ts`                                                   | create        | 5                         |
| `backend/apps/intake/tests/test_filing_fee_frontend_copy.py`                            | create        | 5                         |
| `frontend/src/pages/FeeWaiverPage.tsx`                                                  | delete        | 5                         |
| `frontend/src/pages/__tests__/FeeWaiverPage.test.tsx`                                   | delete        | 5                         |
| `frontend/e2e/pages/fee-waiver.page.ts`                                                 | delete        | 5                         |
| `frontend/src/App.tsx`                                                                  | modify        | 5                         |
| `frontend/src/App.test.tsx`                                                             | modify        | 5                         |
| `frontend/src/pages/IntakeWizard.tsx`                                                   | modify        | 5                         |
| `frontend/src/pages/__tests__/IntakeWizard.test.tsx`                                    | modify        | 5                         |
| `frontend/src/api/client.ts`                                                            | modify        | 5, 6, 8                   |
| `frontend/src/types/api.ts`                                                             | modify        | 5, 6, 7                   |
| `frontend/src/test/mocks/handlers.ts`                                                   | modify        | 5, 6, 7, 8                |
| `frontend/src/constants/copy.ts`                                                        | modify        | 5, 6                      |
| `frontend/src/constants/formText.ts`                                                    | modify        | 5                         |
| `frontend/src/styles/global.css`                                                        | modify        | 5, 7                      |
| `frontend/e2e/pages/filing-fee.page.ts`                                                 | create        | 5                         |
| `frontend/e2e/pages/wizard.page.ts`                                                     | modify        | 5                         |
| `frontend/e2e/fixtures/personas.ts`                                                     | modify        | 5                         |
| `frontend/e2e/journeys/maria-happy-path.spec.ts`                                        | modify        | 5                         |
| `frontend/e2e/journeys/sarah-simplest.spec.ts`                                          | modify        | 5                         |
| `frontend/e2e/journeys/andres-gig-driver.spec.ts`                                       | modify        | 5                         |
| `frontend/e2e/journeys/james-borderline.spec.ts`                                        | modify        | 5                         |
| `frontend/e2e/journeys/priya-ineligible.spec.ts`                                        | modify        | 5                         |
| `frontend/e2e/journeys/sofa-journey.spec.ts`                                            | modify        | 5                         |
| `frontend/src/pages/__tests__/FormDashboard.test.tsx`                                   | test          | 6                         |
| `backend/apps/eligibility/models.py`                                                    | modify        | 7                         |
| `backend/apps/eligibility/migrations/0003_remove_meanstest_qualifies_for_fee_waiver.py` | create        | 7                         |
| `backend/apps/eligibility/services/means_test_calculator.py`                            | modify        | 7                         |
| `backend/apps/eligibility/tests/test_migrations.py`                                     | create        | 7                         |
| `backend/apps/eligibility/tests/test_means_test_calculator.py`                          | test          | 7                         |
| `backend/apps/eligibility/tests/test_household_means_test.py`                           | test          | 7                         |
| `backend/apps/intake/tests/test_e2e_intake.py`                                          | test          | 7                         |
| `backend/apps/audit/tests/test_upl_compliance.py`                                       | test          | 7                         |
| `frontend/src/components/wizard/MeansTestPreview.tsx`                                   | modify        | 7                         |
| `frontend/src/test/fixtures/session.ts`                                                 | modify        | 7                         |
| `frontend/src/components/wizard/__tests__/MeansTestPreview.test.tsx`                    | test          | 7                         |
| `backend/apps/intake/migrations/0030_fee_waiver_applications_to_filing_fee.py`          | create        | 8                         |
| `backend/apps/intake/migrations/0031_delete_feewaiverapplication.py`                    | create        | 8                         |
| `backend/apps/intake/urls.py`                                                           | modify        | 8                         |
| `backend/apps/intake/tests/test_fee_waiver_views.py`                                    | delete        | 8                         |
| `backend/apps/intake/tests/test_models.py`                                              | modify        | 8                         |
| `backend/apps/intake/tests/test_completion.py`                                          | modify        | 8                         |
| `backend/config/tests/test_urls.py`                                                     | modify        | 8                         |
| `frontend/src/utils/parseAmount.ts`                                                     | modify        | 8                         |
| `docs/testing/persona-briefs/maria-torres.md`                                           | modify        | 9                         |
| `docs/testing/persona-briefs/sarah-chen.md`                                             | modify        | 9                         |
| `docs/testing/persona-briefs/deshawn-mitchell.md`                                       | modify        | 9                         |
| `docs/testing/persona-briefs/james-washington.md`                                       | modify        | 9                         |
| `docs/testing/persona-briefs/priya-sharma.md`                                           | modify        | 9                         |
| `docs/testing/persona-briefs/andres-kettleby.md`                                        | modify        | 9                         |
| `docs/testing/persona-briefs/README.md`                                                 | modify        | 9                         |
| `README.md`                                                                             | modify        | 9                         |
| `docs/security/compliance.md`                                                           | modify        | 9                         |
| `docs/security/data-protection.md`                                                      | modify        | 9                         |
| `frontend/e2e/pages/dashboard.page.ts`                                                  | modify        | 9                         |

---

## Tasks

### Task 1: The 2026 HHS poverty guideline and the court's limit

**Spec:** §5 (the table, the 2026 row, which date counts, `valid_through`, the court's limit, `REFERENCE_TABLES.md`), §6.2 ("No table in force", for the log line only).

**Files:**

- Modify: `backend/apps/districts/models.py` (new `PovertyGuideline` between `MedianIncome`, which ends at `:137`, and `ExemptionSchedule` at `:140`)
- Create: `backend/apps/districts/migrations/0004_povertyguideline.py` (generated)
- Create: `backend/apps/districts/migrations/0005_poverty_guideline_2026.py` (data migration)
- Create: `backend/apps/districts/poverty.py`
- Create: `backend/apps/districts/tests/test_poverty.py`
- Modify: `backend/conftest.py` (a `poverty_2026` fixture appended after `_fill_forms_on_a_fixed_day`, `:26-32`; Task 8 deletes `:12`, a different line)
- Modify: `docs/REFERENCE_TABLES.md:4` (header date) and a new section appended after `:57`
- Modify: `CLAUDE.md:36` ("Dated tables and the fill date") and the file map after `:108` (`apps/districts/counties.py`)

**Interfaces:**

- Consumes: `DatedTable`, `in_force`, `fill_date`, `NoTableInForce` (`apps/districts/dated_tables.py:18`, `:63`, `:58`, `:38`), unchanged.
- Produces:
  - `apps/districts/models.PovertyGuideline(DatedTable)`:
    - `first_person = models.PositiveIntegerField(help_text="Yearly guideline for one person, in whole dollars.")`
    - `each_additional = models.PositiveIntegerField(help_text="Added for each person after the first, in whole dollars a year.")`
    - `Meta`: `verbose_name = "Poverty Guideline"`, `verbose_name_plural = "Poverty Guidelines"`, `ordering = ["-effective_date"]`, `constraints = [models.UniqueConstraint(fields=["effective_date"], name="poverty_guideline_unique_effective_date")]`. No district, no `created_at`.
    - `__str__` returns `f"HHS Poverty Guidelines ({self.effective_date})"`.
  - `apps/districts/poverty.py`:
    - `POVERTY_TABLE = "HHS poverty guidelines"`;
    - `poverty_limit_monthly(guideline: PovertyGuideline, family_size: int) -> Decimal`, which raises `ValueError("Family size must be at least 1.")` below 1;
    - `poverty_guideline_in_force(on: date | None = None) -> PovertyGuideline`, which returns `in_force(PovertyGuideline.objects.all(), on or fill_date(), POVERTY_TABLE)` and raises `NoTableInForce`.
  - The 2026 row in every migrated database: `first_person=15960`, `each_additional=5680`, `effective_date=2026-01-15`, `valid_through=2027-01-31`, `source_url="https://www.federalregister.gov/documents/2026/01/15/2026-00755/annual-update-of-the-hhs-poverty-guidelines"`.
  - `backend/conftest.py` fixture `poverty_2026(db) -> PovertyGuideline`: `get_or_create`s the 2026 row by `effective_date` with the values above, for any test that needs the row after a transactional test's flush (R4).
- CLAUDE.md: "Dated tables and the fill date" gains the sentences in Step 7. The file map gains one `apps/districts/poverty.py` line.

**Decided here:**

- **Uniqueness.** `effective_date` is made unique with a named `UniqueConstraint`, not by redeclaring the field inherited from the abstract `DatedTable`. `makemigrations` then writes one deterministic `AddConstraint`, and `MedianIncome`'s field stays untouched.
- **The migration's reverse.** `0005` reverses by deleting the row it loaded, matched by its `effective_date`. It is not a `noop`, for two reasons:

  - `test_the_migration_dates_each_stored_row_and_names_the_page_it_comes_from` (`test_dated_tables.py:237`) migrates districts back to `0002`. Without a reverse function, that test hits `IrreversibleError`.
  - A `noop` reverse would leave the row behind, so the next forward run would break the unique date.

  The row's figures are written into the migration itself, under the comment that `0003_medianincome_dated_table.py:11` uses. They are never imported from `poverty.py`.

- **The strict comparison.** "Strictly less" (§5, § 1930(f)(1)) has no caller in code, because no code may compare the figure to the limit (Global Constraints, "No verdict"). It goes in `poverty_limit_monthly`'s docstring as a fact about the court's test. It gets no test and no function.
- **The 2026 figures can't test the rounding.** Every 2026 limit divides exactly: the yearly figure × 3 / 2 / 12 is the yearly figure ÷ 8, and 15,960 and 5,680 are both multiples of 8. So a synthetic unsaved row (`first_person=10001`) pins `ROUND_HALF_UP`: it gives 1250.125, which rounds to 1250.13. `ROUND_HALF_EVEN` would give 1250.12.
- **Migrated rows and transactional tests.**
  - CI runs pytest with migrations (`ci.yml:79`, no `--nomigrations`), so a plain `db` test sees the 2026 row.
  - A test using `transactional_db`, such as the `migrate` fixture, flushes every table at teardown, the migrated row included.
  - pytest-django 4.9.0 runs those tests after every `db` test (`plugin.py:469-476`), so a plain `db` test may rely on the migrated row, and this task's lookup tests do.
  - A transactional test that needs the row asks for the root `backend/conftest.py` fixture `poverty_2026`, which `get_or_create`s the row with the migration's values (R4). It imports the model inside the fixture, since the conftest is imported before `pytest_configure` calls `django.setup()`. `test_poverty.py` proves it with a transactional test that runs after `test_dated_tables.py`'s flushing migration test.
  - The CLAUDE.md sentence in Step 7 states both, since a data-migration row is new precedent here.
- **The row expires before the median table does** (R24). From 2027-02-01 the lookup refuses, two months before the April 1, 2027 median cutoff. The filing-fee page then shows its no-table sentence, and the journeys' limit checks (Task 5) fail until the 2027 row is loaded. The CLAUDE.md sentence and the runbook say so.
- **`REFERENCE_TABLES.md:14` is not edited here.** Today the fee-waiver offer still comes from the median (`eligibility/models.py:186-188`, `IntakeWizard.tsx:500-504`). A doc changes in the task that changes the behaviour (R2), so Task 7 (which removes `qualifies_for_fee_waiver`) owns the edit. This task adds the new section and moves the header date.
- **The new section's "What a missed change looks like"** describes the filing-fee page and its `information_gap`, which Tasks 3 and 5 build. The section is written once, here, for the branch as it merges. Task 3 or Task 5 corrects it only if what they build differs from it.
- **The file map** gains a `poverty.py` line, since the new module would otherwise be missing from it.
- **The source URL** was checked on 2026-11-02. The Federal Register page resolves and shows "Document Citation: 91 FR 1797", "Document Number: 2026-00755", "Publication Date: 01/15/2026" and "Effective Date: January 13, 2026 unless an office administering a program … specifies a different effective date". Step 6 re-checks it before the commit.

- [ ] **Step 1: Write the failing tests**

`backend/apps/districts/tests/test_poverty.py`:

```python
"""The HHS poverty guideline in force on the day the forms are filled (3f spec §5).

Business intent: a judge may waive the Chapter 7 filing fee only for a family whose income is
less than 150% of the poverty guideline for its size (28 U.S.C. § 1930(f)(1)). DigniFi shows
that limit beside Form 101 line 8 as information, so it must be the court's own figure to the
cent, from the guideline last published on the fill date. It never shows last year's figure in
place of a missing one. The 2026 row is loaded by a data migration, so every database has it
without a loaddata step. Lookup tests set their own date; the rest run on the root conftest's
2026-10-16.
"""

import logging
from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from apps.districts.dated_tables import NoTableInForce
from apps.districts.models import PovertyGuideline
from apps.districts.poverty import (
    POVERTY_TABLE,
    poverty_guideline_in_force,
    poverty_limit_monthly,
)

SOURCE_2026 = (
    "https://www.federalregister.gov/documents/2026/01/15/2026-00755/"
    "annual-update-of-the-hhs-poverty-guidelines"
)
BEFORE_2026 = [("districts", "0004_povertyguideline")]
WITH_2026 = [("districts", "0005_poverty_guideline_2026")]

ON_POSTGRES = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="needs Postgres: real column types; CI runs it with config.settings.test_postgres",
)


def _fill_on(monkeypatch, day):
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: day)


def _guideline_2026():
    return PovertyGuideline(first_person=15960, each_additional=5680)


# ── The court's limit (§5) ──


@pytest.mark.parametrize(
    "family_size,limit",
    [
        (1, "1995.00"),
        (2, "2705.00"),
        (3, "3415.00"),
        (4, "4125.00"),
        (5, "4835.00"),
        (6, "5545.00"),
        (7, "6255.00"),
        (8, "6965.00"),
        (9, "7675.00"),
        (10, "8385.00"),
    ],
)
def test_the_2026_limit_is_the_courts_own_monthly_figure_for_every_family_size(
    family_size, limit
):
    # uscourts.gov "150% of the HHS Poverty Guidelines for 2026": $1,995.00 for one person
    # and $710.00 for each person after, with no cap at eight.
    assert poverty_limit_monthly(_guideline_2026(), family_size) == Decimal(limit)


def test_a_limit_that_falls_between_cents_rounds_half_up():
    # $10,001 × 1.5 ÷ 12 = $1,250.125: half-up gives .13, where half-even would give .12.
    guideline = PovertyGuideline(first_person=10001, each_additional=0)

    assert poverty_limit_monthly(guideline, 1) == Decimal("1250.13")


@pytest.mark.parametrize("family_size", [0, -1])
def test_a_family_of_no_one_has_no_limit(family_size):
    with pytest.raises(ValueError, match="at least 1"):
        poverty_limit_monthly(_guideline_2026(), family_size)


# ── The 2026 row the migration loads (§5) ──


def test_every_database_has_the_2026_guideline_as_the_federal_register_published_it(db):
    row = PovertyGuideline.objects.get()

    assert (
        row.first_person,
        row.each_additional,
        row.effective_date,
        row.valid_through,
        row.source_url,
    ) == (15960, 5680, date(2026, 1, 15), date(2027, 1, 31), SOURCE_2026)


def test_every_stored_guideline_says_when_it_ends_and_where_it_comes_from(db):
    rows = list(PovertyGuideline.objects.all())

    assert rows
    for row in rows:
        assert row.valid_through is not None and row.valid_through > row.effective_date
        assert row.source_url.startswith("https://www.federalregister.gov/documents/")


def test_two_guidelines_cannot_start_on_the_same_day(db):
    with pytest.raises(IntegrityError), transaction.atomic():
        PovertyGuideline.objects.create(
            first_person=1, each_additional=1, effective_date=date(2026, 1, 15)
        )


# ── The guideline in force on the fill date (§5, U §4.3) ──


@pytest.mark.parametrize(
    "fill_date",
    [date(2026, 1, 15), date(2026, 10, 16), date(2027, 1, 31)],
    ids=["its_publication_day", "the_pinned_fill_day", "its_last_day"],
)
def test_the_2026_guideline_is_in_force_from_its_publication_through_january_2027(
    db, monkeypatch, fill_date
):
    _fill_on(monkeypatch, fill_date)

    assert poverty_guideline_in_force().effective_date == date(2026, 1, 15)


def test_the_lookup_takes_the_fill_date_unless_given_a_day(db):
    # The root conftest pins the fill date to 2026-10-16.
    assert poverty_guideline_in_force().effective_date == date(2026, 1, 15)
    with pytest.raises(NoTableInForce):
        poverty_guideline_in_force(date(2027, 2, 1))


@pytest.mark.parametrize(
    "fill_date,why",
    [(date(2026, 1, 14), "not_yet_published"), (date(2027, 2, 1), "past_its_valid_through")],
)
def test_no_guideline_in_force_refuses_and_logs_only_the_table_and_the_date(
    db, monkeypatch, caplog, fill_date, why
):
    _fill_on(monkeypatch, fill_date)

    with pytest.raises(NoTableInForce) as refused:
        poverty_guideline_in_force()

    assert refused.value.table == POVERTY_TABLE == "HHS poverty guidelines"
    assert refused.value.on == fill_date
    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (
            logging.ERROR,
            f"No HHS poverty guidelines table in force on {fill_date.isoformat()} "
            "for district -",
        )
    ]


def test_a_newer_guideline_takes_over_from_its_own_publication_day(db):
    newer = PovertyGuideline.objects.create(
        first_person=16400,
        each_additional=5800,
        effective_date=date(2027, 1, 14),
        valid_through=date(2028, 1, 31),
        source_url="https://www.federalregister.gov/documents/2027/01/14/synthetic",
    )

    assert poverty_guideline_in_force(date(2027, 1, 13)).effective_date == date(2026, 1, 15)
    assert poverty_guideline_in_force(date(2027, 1, 14)) == newer


def test_a_transactional_test_still_finds_the_2026_guideline_through_the_root_fixture(
    transactional_db, poverty_2026
):
    # A transactional test's teardown empties every table, the migrated row included, and
    # pytest-django runs these tests after the db tests, so in a full run this one follows
    # test_dated_tables.py's flushing migration test. The root fixture puts the row back.
    assert poverty_guideline_in_force() == poverty_2026
    assert (
        poverty_2026.first_person,
        poverty_2026.each_additional,
        poverty_2026.effective_date,
        poverty_2026.valid_through,
        poverty_2026.source_url,
    ) == (15960, 5680, date(2026, 1, 15), date(2027, 1, 31), SOURCE_2026)


# ── The data migration (§5: a migration, not a fixture) ──


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


def _round_trip(migrate):
    before = migrate(BEFORE_2026).get_model("districts", "PovertyGuideline")
    assert before.objects.count() == 0

    after = migrate(WITH_2026).get_model("districts", "PovertyGuideline")
    assert list(
        after.objects.values_list(
            "first_person", "each_additional", "effective_date", "valid_through", "source_url"
        )
    ) == [(15960, 5680, date(2026, 1, 15), date(2027, 1, 31), SOURCE_2026)]


def test_undoing_the_2026_guideline_removes_its_row_and_redoing_it_loads_it_once(migrate):
    _round_trip(migrate)


@pytest.mark.postgres
@ON_POSTGRES
def test_undoing_the_2026_guideline_removes_its_row_and_redoing_it_loads_it_once_on_postgres(
    migrate,
):
    _round_trip(migrate)
```

No test name or assertion says "qualify" or "eligible" (Global Constraints).

- [ ] **Step 2: Run the tests to verify they fail**

From the worktree root, after `source .claude/forms-step3f.env` ("Before you start"), which gives `$PY`:

Run: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest apps/districts/tests -q -p no:cacheprovider`

Expected: `test_poverty.py` fails to collect with `ImportError: cannot import name 'PovertyGuideline' from 'apps.districts.models'`. `test_dated_tables.py` still passes.

- [ ] **Step 3: The model and its schema migration**

- Add `PovertyGuideline` to `backend/apps/districts/models.py` after `MedianIncome`, as in Interfaces. Its docstring says three things:
  - it holds the HHS poverty guidelines for the 48 contiguous states and DC, the only ones ILND needs;
  - it is national public data, so it has no district and is not encrypted;
  - each row is loaded by a data migration (`docs/REFERENCE_TABLES.md`).
- Update the module docstring's second line (`:3`) to "Defines District, MedianIncome, PovertyGuideline, ExemptionSchedule, and LocalRule."
- Run `cd backend && $PY manage.py makemigrations districts -n povertyguideline`. Expected: `0004_povertyguideline.py`, which depends on `("districts", "0003_medianincome_dated_table")` and holds one `CreateModel` with the constraint in its `options`, or a separate `AddConstraint`.

- [ ] **Step 4: The 2026 row's data migration**

`backend/apps/districts/migrations/0005_poverty_guideline_2026.py`, written by hand (or started with `makemigrations districts --empty -n poverty_guideline_2026`):

```python
"""Load the 2026 HHS poverty guidelines (91 FR 1797, Federal Register doc. 2026-00755)."""

from datetime import date

from django.db import migrations

# Kept here, not imported, because a migration must keep running the code it shipped with.
GUIDELINE_2026 = {
    "first_person": 15960,
    "each_additional": 5680,
    # The publication date: the AO's instructions compare with the guideline "last published"
    # (3f spec §5). HHS's own effective date is 2026-01-13.
    "effective_date": date(2026, 1, 15),
    "valid_through": date(2027, 1, 31),
    "source_url": (
        "https://www.federalregister.gov/documents/2026/01/15/2026-00755/"
        "annual-update-of-the-hhs-poverty-guidelines"
    ),
}


def load_2026(apps, schema_editor):
    apps.get_model("districts", "PovertyGuideline").objects.create(**GUIDELINE_2026)


def unload_2026(apps, schema_editor):
    apps.get_model("districts", "PovertyGuideline").objects.filter(
        effective_date=GUIDELINE_2026["effective_date"]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("districts", "0004_povertyguideline"),
    ]

    operations = [
        migrations.RunPython(load_2026, unload_2026),
    ]
```

- [ ] **Step 5: The limit and the lookup**

`backend/apps/districts/poverty.py`. Its module docstring states:

- the court's limit is 150% of the guideline, a month;
- the lookup goes through `in_force` on the fill date, like every dated table.

```python
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .dated_tables import fill_date, in_force
from .models import PovertyGuideline

POVERTY_TABLE = "HHS poverty guidelines"


def poverty_limit_monthly(guideline: PovertyGuideline, family_size: int) -> Decimal: ...


def poverty_guideline_in_force(on: date | None = None) -> PovertyGuideline: ...
```

- `poverty_limit_monthly`:
  - Below 1, it raises `ValueError("Family size must be at least 1.")`.
  - Otherwise it computes `yearly = Decimal(guideline.first_person) + Decimal(guideline.each_additional) * (family_size - 1)` and returns `(yearly * 3 / 2 / 12).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`.
  - Its docstring adds: "A family's income meets the limit only when it is strictly less (28 U.S.C. § 1930(f)(1)). That comparison is the court's, and DigniFi never makes it for the filer."
- `poverty_guideline_in_force` returns `in_force(PovertyGuideline.objects.all(), on or fill_date(), POVERTY_TABLE)`, with no district, so the log reads `for district -`.
  - It imports `fill_date`, never `_today`.
  - Its docstring names the `NoTableInForce` it raises, and says that `in_force` logs it once.

`backend/conftest.py`, appended after `_fill_forms_on_a_fixed_day` (R4). Nothing else in the file changes:

```python
@pytest.fixture
def poverty_2026(db):
    # The 2026 HHS poverty guideline, which 0005_poverty_guideline_2026 loads. A transactional
    # test's teardown empties every table, the migrated row included, so a test that needs the
    # row after one asks for this fixture. Imported here: this module loads before django.setup().
    from apps.districts.models import PovertyGuideline

    row, _ = PovertyGuideline.objects.get_or_create(
        effective_date=date(2026, 1, 15),
        defaults={
            "first_person": 15960,
            "each_additional": 5680,
            "valid_through": date(2027, 1, 31),
            "source_url": (
                "https://www.federalregister.gov/documents/2026/01/15/2026-00755/"
                "annual-update-of-the-hhs-poverty-guidelines"
            ),
        },
    )
    return row
```

Run: the Step 2 command. Expected: PASS. All of `apps/districts/tests` passes, including `test_dated_tables.py`'s migration test, which now reverses `0005` and `0004` on its way to `0002`.

- [ ] **Step 6: Check the source URL, then write the runbook**

Re-check that `source_url` resolves before committing. `curl` and `WebFetch` are blocked here, so use `ctx_fetch_and_index` or the exa fetch tool. The page must show 91 FR 1797, doc. 2026-00755, published 01/15/2026.

If it doesn't resolve, do all of the following:

- change `source_url` in `0005`, in `SOURCE_2026`, in the `poverty_2026` fixture and in the doc to `https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines`;
- change the `startswith` check in `test_every_stored_guideline_says_when_it_ends_and_where_it_comes_from` to accept that host;
- say so in the ledger.

`docs/REFERENCE_TABLES.md`:

- `:4` becomes `- **Last updated:** <the commit's date, e.g. November 2, 2026>`.
- `:14` is unchanged (see Decided here).
- After `:57`, append `\n---\n` and this section:

```markdown
## HHS poverty guidelines

A judge may waive the Chapter 7 filing fee only for a family whose income is less than 150% of the poverty guideline for its size (28 U.S.C. § 1930(f)(1)). DigniFi shows that limit, a month, on the "How you will pay the filing fee" page, beside Form 101 line 8, as information. It never compares the filer's income with it. The table is national: DigniFi stores the figures for the 48 contiguous states and the District of Columbia, which cover the Northern District of Illinois.

### Where it is posted

- HHS (ASPE) lists every year's guidelines: https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
- Each year's figures are published as a notice in the Federal Register. DigniFi stores that notice's page as the row's `source_url`.
- The courts post the monthly 150% figures as "150% of the HHS Poverty Guidelines" on uscourts.gov. Check DigniFi's limits against that table.

### When it changes

- HHS publishes new guidelines each January. The day isn't fixed: the 2026 notice was published on January 15, 2026, and gave its own effective date as January 13.
- A row takes effect on the day its notice is **published** in the Federal Register. The AO's instructions for Form 103B compare a family's income with the guideline "last published". The ILNB instruction packet prints its table as "Updated: 1/01/2026". The question of which date counts is open with the clerk, and an answer would change only a row's `effective_date` and this page.
- A row's `valid_through` is January 31 of the next year, which gives HHS the month to publish.
- If the next notice is late, extend the current row's `valid_through` with a new data migration, so that its figures stay shown while they are still the last published. Then add the next row as below.

### The rows DigniFi loads

| Effective  | `valid_through` | First person | Each additional person | Court's limit a month, 1–4 people             | Each person after |
| ---------- | --------------- | ------------ | ---------------------- | --------------------------------------------- | ----------------- |
| 2026-01-15 | 2027-01-31      | $15,960      | $5,680                 | $1,995.00 / $2,705.00 / $3,415.00 / $4,125.00 | $710.00           |

### How to add a row

1. Open the new Federal Register notice. Copy the figure for one person and the amount for each additional person from its table for the 48 contiguous states and DC.
2. Run `python manage.py makemigrations districts --empty -n poverty_guideline_<year>`. Write it as `0005_poverty_guideline_2026.py` is written:

   - a `RunPython` that creates one `PovertyGuideline` row, with the figures written into the migration;
   - its reverse, which deletes that row by its `effective_date`.

   The row's fields are:

   - `effective_date`: the notice's publication date;
   - `valid_through`: January 31 of the next year;
   - `source_url`: the notice's page.

3. Leave the earlier rows as they are. A test fails if any stored guideline has no `valid_through`.
4. In `backend/apps/districts/tests/test_poverty.py`, add a test that pins the new row's monthly limits to the courts' 150% table for that year. Then open a pull request to `develop`.
5. Nothing to run after the deploy: the Heroku release runs `migrate`, which loads the row. A local database gets it with `python manage.py migrate`.

### What a missed change looks like

From the day after the last row's `valid_through` until the new row's migration is applied:

- **Filers** see, on the "How you will pay the filing fee" page, a sentence saying DigniFi doesn't have the current poverty figures. They see no limit, never an old one. Their answer still saves, and no form is refused.
- **Logs and Sentry** get one error line per lookup, naming only the table and the date: `No HHS poverty guidelines table in force on 2027-02-01 for district -`.
- **The E2E journeys** fail where they check the limit, in CI too, since they run on the real date. The 2026 row ends on January 31, 2027, two months before the median table's March 31, 2027.

The fix is to add the new row, as above. If HHS hasn't published the new guidelines yet, extend `valid_through` instead.
```

- [ ] **Step 7: Update `CLAUDE.md`**

In "Dated tables and the fill date" (`:36`), insert these sentences after "a test fails on a fixture median row without one." and before "The dev server, the seed and E2E use the real date". Every other sentence of the gotcha is unchanged.

"`PovertyGuideline` (`apps/districts/models.py`) holds the HHS poverty guidelines for the 48 states and DC. It is national, so it has no district, and its rows come from data migrations, not a fixture: `0005_poverty_guideline_2026` loads 2026 ($15,960, and $5,680 for each additional person), effective 2026-01-15, the Federal Register publication date, through 2027-01-31. So every database, CI and the Heroku release have the rows without `loaddata`, and a new year is a new data migration. `poverty_guideline_in_force(on=None)` (`apps/districts/poverty.py`) looks the guideline up through `in_force` on `fill_date()` as `POVERTY_TABLE` ("HHS poverty guidelines"), and logs `for district -`. `poverty_limit_monthly(guideline, family_size)` is the court's 150% limit a month, rounded half-up to the cent ($1,995.00 for one person and $710.00 for each person after, in 2026). It decides nothing: comparing a family's income with it is the court's job. Nothing that prepares a form reads the guideline. A transactional test's teardown empties every table, the migrated rows included, and pytest-django runs those tests after the `db` tests: a plain `db` test may rely on the migrated 2026 row, and any other test that needs it asks for the root `backend/conftest.py` fixture `poverty_2026`, which puts it back. The 2026 row ends two months before the median table does: from 2027-02-01 the filing-fee page shows its no-table sentence and the journeys' limit checks fail until the 2027 row is loaded."

The file map gains, after the `apps/districts/counties.py` entry (`:108`):

"- `apps/districts/poverty.py` — `POVERTY_TABLE`, `poverty_limit_monthly` (the court's 150% limit a month) and `poverty_guideline_in_force`. The table is `PovertyGuideline` in `models.py`, one row per year, each loaded by a data migration."

- [ ] **Step 8: Gates**

Check `uptime` first. Run the full suite only while the 1-minute load is under 10, and the journeys only while the 5-minute load is also under 8. Then run each of these:

- The full backend suite: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 -q -p no:cacheprovider`. Expected: the baseline totals plus 26 tests from `test_poverty.py`, 25 passed and the `postgres` twin skipped; 0 failed; coverage at least 90%.
- `/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/`. Expected: `All checks passed!`.
- `cd backend && $PY manage.py check`. Expected: "System check identified no issues".
- `cd backend && $PY manage.py makemigrations --check --dry-run`. Expected: "No changes detected".
- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres -q -p no:cacheprovider`. Expected: the new twin and the existing `postgres` tests pass.
- `frontend/node_modules/.bin/prettier --check docs/REFERENCE_TABLES.md CLAUDE.md`, run from the worktree root. It reads the root `.prettierrc.json`. Expected: pass. If not, run it with `--write` and check the diff, which should change only the table's padding.
- The journeys, `zsh .claude/e2e.sh 2`. Expected: green both runs. Task 1 changes nothing they touch except one more migration on the dev database.

- [ ] **Step 9: Commit**

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/git add backend/conftest.py backend/apps/districts/models.py backend/apps/districts/migrations/0004_povertyguideline.py backend/apps/districts/migrations/0005_poverty_guideline_2026.py backend/apps/districts/poverty.py backend/apps/districts/tests/test_poverty.py docs/REFERENCE_TABLES.md CLAUDE.md
/usr/bin/git commit -F /tmp/3f-task1-msg.txt
```

Message (`/tmp/3f-task1-msg.txt`), with no trailer:

```
feat(districts): load the 2026 HHS poverty guideline and the court's limit

PovertyGuideline is a dated table, national and plaintext, whose 2026
row ($15,960, $5,680 each additional, published 2026-01-15, through
2027-01-31) a data migration loads. poverty_limit_monthly gives the
court's 150% limit a month, half-up to the cent, and the lookup goes
through in_force on the fill date, refusing rather than showing an old
figure. A root conftest fixture, poverty_2026, puts the row back for
tests that run after a transactional flush. REFERENCE_TABLES.md gains
the table's runbook.
```

---

### Task 2: 103B lines 1–3 read the household list, Schedule I and 8f

**Spec:** §8.2 (lines 1–3, "Line 2 reads Schedule I line 10", "Blank, not 0.00", "New rules"), §1 item 5, §10 (Maria's and Sarah's 103B), §13 (line 1, line 2, line 3 outcomes; tier 3), §16 calls 13 and 14.

Line numbers are as of `dc31b7a`.

**Files:**

- Create: `backend/apps/forms/services/fee_waiver.py`
- Modify: `backend/apps/forms/services/derivations.py`: the "Form 103B fee waiver derivations" section (`:524-564`, the four rules `_fee_waiver_household_size` … `_fee_waiver_benefit_types`), the `DERIVATIONS` entries (`:859-865`) and `RULE_FIXES` "The fee-waiver application" block (`:1080-1083`)
- Modify: `data/forms/schemas/form_103b.json:60-165` (`Total number of people` through `3 type`; four new fields go in between)
- Modify: `data/forms/field_index/audit/step2_verification.json`: delete the four 103B rows after the `You` row (`:202-241`, the old `undefined_2`, `undefined_4`, `check 3`, `3 type` rows) and add eleven rows in their place
- Modify: `data/forms/field_index/audit/form_103b.unbound.json`: delete the entries at `:10-17` (`undefined_6`), `:18-25` (line 2's group), `:34-42` (line 1's group) and `:43-51` (`check 3`)
- Test (rewrite): `backend/apps/forms/tests/test_form_103b_answers.py`
- Test: `backend/apps/forms/tests/test_form_103b_schema.py:34-61` (`session_with_fw`), `:79-81` (`test_fee_waiver_fields`), `:83-85` (`test_empty_session`)
- Test: `backend/apps/forms/tests/test_schedule_j_schema.py:359-378` (`test_every_form_that_copies_the_monthly_expense_total_prints_line_22c`), and its imports (`:11-17`)
- Test: `backend/apps/forms/tests/test_rule_fixes.py:175`
- Test: `backend/apps/forms/tests/test_check.py:42` (the `ASSISTANCE` comment) and `:257` (in `test_a_word_too_wide_for_a_multi_line_box_is_refused`, `:251-257`)
- Test: `backend/apps/forms/tests/test_download_action.py:215` (the comment only)
- Test: `backend/apps/forms/tests/test_oracle_tier2.py:37` (`ASSERTED_CASES` 475 → 480)
- Test: `backend/apps/forms/tests/test_oracle_tier3.py`: `EXPECTED["maria"]` (after `"form_101"`, `:99`) and `EXPECTED["sarah"]` (after `"form_101"`, `:344`)
- Modify: `CLAUDE.md`, the gotchas "The fee-waiver application" and "Blank, not 0.00", and the File Map's `apps/forms/services/` entry

**Interfaces:**

- Consumes: `income_step_gaps`, `household_members`, `counted_spouse_income`, `IncomeStepGap` (`apps/eligibility/cmi.py:306`, `:214`, `:172`, `:79`); `count_fee_waiver_household` (`apps/intake/household.py:60-70`); `DERIVATIONS["schedule_i_income_total_debtor1"]` and `["schedule_i_income_total_spouse"]` (`derivations.py:681-686`, `_schedule_i_twins()` over `SCHEDULE_I_LINES["income_total"]`). Nothing from Task 1.
- Produces (`apps/forms/services/fee_waiver.py`), exactly as the frame names them:
  - `@dataclass(frozen=True) class FeeWaiverFamily: total: int; spouse_counted: bool; dependents: int` and `fee_waiver_family(session) -> FeeWaiverFamily`.
  - `@dataclass(frozen=True) class FeeWaiverIncome: you: Decimal; spouse: Decimal | None; subtotal: Decimal; noncash: Decimal | None; total: Decimal` and `fee_waiver_income(session) -> FeeWaiverIncome`.
  - `fee_waiver_noncash(session) -> tuple[str, str]`.
  - Both `fee_waiver_family` and `fee_waiver_income` begin `gaps = income_step_gaps(session)`; `if gaps: raise gaps[0]`, as `views._recalculate_means_test` does (`forms/views.py:159-170`). `fee_waiver_noncash` never raises.
- Produces (`DERIVATIONS`), each rule's printed value:

  | Rule                          | Box (`form_103b.json`)                                        | Prints                                           |
  | ----------------------------- | ------------------------------------------------------------- | ------------------------------------------------ |
  | `fee_waiver_family_size`      | `Total number of people` (text)                               | `str(family.total)`                              |
  | `fee_waiver_spouse_counted`   | `Your spouse` (checkbox, `{"true": "/On"}`)                   | `"true"` when `family.spouse_counted`, else `""` |
  | `fee_waiver_has_dependents`   | `Your dependents` (checkbox, `{"true": "/On"}`)               | `"true"` when `family.dependents > 0`, else `""` |
  | `fee_waiver_dependents_count` | `How many dependents` (text)                                  | `str(family.dependents)` above 0, else `""`      |
  | `fee_waiver_income_you`       | `undefined_2`                                                 | `_fmt(income.you)`                               |
  | `fee_waiver_income_spouse`    | `undefined_3`                                                 | `_fmt(income.spouse)`, `""` when None            |
  | `fee_waiver_income_subtotal`  | `undefined_4`                                                 | `_fmt(income.subtotal)`                          |
  | `fee_waiver_income_noncash`   | `undefined_5`                                                 | `_fmt(income.noncash)`, `""` when None           |
  | `fee_waiver_income_total`     | `undefined_6`                                                 | `_fmt(income.total)`                             |
  | `fee_waiver_noncash_answer`   | `check 3` (choices `{"yes": "/yes", "no": "/no"}`, unchanged) | `fee_waiver_noncash(session)[0]`                 |
  | `fee_waiver_noncash_kinds`    | `3 type`                                                      | `fee_waiver_noncash(session)[1]`                 |

  Removed: the rules `fee_waiver_household_size`, `fee_waiver_monthly_income`, `fee_waiver_noncash_assistance`, `fee_waiver_benefit_types`, their functions, bindings, `RULE_FIXES` entries and addendum rows. `fee_waiver_monthly_expenses` (line 6) is unchanged. `FeeWaiverApplication` still exists and still decides the packet (`registry.py:113`); no form reads its answers after this task.

- `RULE_FIXES` gains `{"step": "income_info"}` for the eight text-bound rules: `fee_waiver_family_size`, `fee_waiver_dependents_count`, `fee_waiver_income_you`, `fee_waiver_income_spouse`, `fee_waiver_income_subtotal`, `fee_waiver_income_noncash`, `fee_waiver_income_total`, `fee_waiver_noncash_kinds`.
- Tier 2: 103B goes from 14 asserted cases to 19. Six old keyed cases go (`Total number of people`, `undefined_2`, `undefined_4`, `undefined_6`, `check 3`, `3 type`, each under its old rule), and eleven new (box, key) pairs come in, each asserted through its addendum row. 475 − 6 + 11 = **480**. The addendum goes from 178 rows to 178 − 4 + 11 = 185.
- CLAUDE.md:
  - "The fee-waiver application": the sentences "`FeeWaiverApplication.monthly_take_home_pay` (encrypted, zero or more; 103B line 2) and `receives_noncash_assistance` (`BooleanField(null=True)`; 103B line 3) have no defaults and stay empty until the filer answers. Line 3 prints an empty answer blank and a stored False as a sworn "No", so never default it." become "`FeeWaiverApplication.monthly_take_home_pay` (encrypted, zero or more) and `receives_noncash_assistance` (`BooleanField(null=True)`) have no defaults and stay empty until the filer answers. No form prints them: 103B lines 1–3 read the wizard."
  - In the same gotcha, "103B prints take-home pay on line 2 (`undefined_2`, `undefined_4`, `undefined_6`), the answer and its kinds on line 3 (`check 3`, `3 type`, kinds only under a Yes), and Schedule J line 22c on line 6 (`undefined_7`); `4 type` and `5 Type` are unbound." becomes "103B lines 1–3 come from `apps/forms/services/fee_waiver.py`. Line 1 counts the household list (`fee_waiver_family`, through `count_fee_waiver_household`): `You` always, `Your spouse` for a spouse at home, `Your dependents` and `How many dependents` only above 0, and `Total number of people`. Line 2 is Schedule I line 10 for each person counted (`fee_waiver_income`): `undefined_2`, `undefined_3` for `married_together` only, their subtotal, the counted people's known 8f non-cash values on `undefined_5` (only above $0), and the total less them. Line 3 reads 8f (`fee_waiver_noncash`): `check 3` Yes when a counted person answered Yes with a non-cash kind, No when none did, and `3 type` the kinds, the filer's then the spouse's after "Spouse: ", joined by "; ". Lines 1 and 2 raise the first of `income_step_gaps` while any gap is open, and never print a guessed 1 (DIG-223). Line 6 prints Schedule J line 22c (`undefined_7`); `4 type` and `5 Type` are unbound."
  - In the same gotcha, the last sentence, "103B's `Total number of people` still prints the application's own size (rule `fee_waiver_household_size`) until 3f.", is deleted. The rest of the gotcha is Task 8's.
  - "Blank, not 0.00": before "Signature lines and signing dates stay blank for wet ink (`test_signing_lines.py`).", insert "103B has no "write $0" instruction: `undefined_3` is blank unless the answer is `married_together`, `undefined_5` prints only a non-cash value above $0, and `How many dependents` and `Your dependents` only above 0."
  - File Map, `apps/forms/services/`: after "`sheets.py` (attached sheets: `plan_sheet()` checks, `draw_sheet()` draws)," insert "`fee_waiver.py` (103B lines 1–3 from the household list, Schedule I line 10 and 8f),".

**Decided here:**

- **Import direction** (rulings R7). `fee_waiver.py` imports `DERIVATIONS` from `derivations.py` at the top and reads line 10 through `DERIVATIONS["schedule_i_income_total_debtor1"]` and `["schedule_i_income_total_spouse"]`, the strings Schedule I prints. It never imports a private helper. `derivations.py` imports `fee_waiver` inside three shims (`_fee_waiver_family`, `_fee_waiver_income`, `_fee_waiver_noncash`), as its asset and debt rules import models inside their bodies (`:188-237`). A top-level import in both directions would be circular. The frame's "imports models, never views" holds: `fee_waiver.py` imports no view. Task 3's `filing_fee.py` imports `fee_waiver` and gets `derivations` with it.
- **`RULE_FIXES` covers the text-bound rules only** (rulings R8). The frame says "All new rules' `RULE_FIXES`". The comment at `derivations.py:932-936` and `test_every_refusal_names_where_to_fix_it` (`test_rule_fixes.py:104-114`) cover rules bound to a text or choice box. No checkbox rule has an entry today (`fee_waiver_noncash_assistance`, `schedule_j_has_dependents`). So the three checkbox rules get none.
- **`fee_waiver_noncash` returns `""`** only when the session has no income row, or a counted person's `assistance_answer` is None, and no one counted answered Yes with a non-cash kind. Under an intake with no gap this never happens, because line 1 raises first. A Yes with only a cash kind is a No on line 3, because 103B line 3 asks about non-cash help.
- **`noncash`** adds `noncash_assistance_value` for each counted person whose `assistance_answer == "yes"` and whose value is not None. A kind with no known value is named on `3 type` and subtracts nothing.
- **Tier 3 adds 103B cases for Maria and Sarah only.** Task 4 makes `form_103b.requires` refuse a session without the line 4/5/7/9 answers. Only the waiver personas get those answers, and `_printed` (`test_oracle_tier3.py:475-505`) builds every form in a persona's `EXPECTED` entry, so a DeShawn 103B case would break all of DeShawn's tier 3 cases in Task 4. The spouse column is covered by the synthetic `married_together` tests below.
- **`form_103b.unbound.json`**: this task removes only the four entries that name boxes it binds. Other entries were stale before 3f, and they are left alone and noted for later: `Debtor 1` (`:2-9`), `undefined_7` (`:26-33`), `check_17`–`check_19` (`:88-96`) and `Debtor.Name1` in `:124-131`, all bound since step 2. `Check 4`, `Check 7` and `Check 9` are Task 4's. No test reads the file.
- **The `HouseholdSerializer` field `fee_waiver_household_size`** (`apps/intake/serializers.py:562-575`) keeps its name and stays as it is. It is the household API's read-only count, not the removed rule, and `apps/eligibility/tests/test_household_means_test.py:324-380` and `apps/forms/tests/test_api_readback.py:162` read it. Its only frontend reader goes in Task 5; it stays (rulings R26).
- `test_schedule_j_schema.py:359` builds an `IncomeInfo` without the 3e2 answers and resolves 103B. Once line 1 raises on any gap, that test raises too. The frame's Task 2 list doesn't name it. It gains `answer_household(session)`.

- [ ] **Step 1: Write the failing tests**

Rewrite `backend/apps/forms/tests/test_form_103b_answers.py`. Keep `_filled` and `_widgets` (`:93-108`), `test_line_6_is_the_monthly_expense_total_schedule_j_prints`, `test_pages_2_and_3_are_headed_with_the_filers_name` and `test_part_3_stays_blank_because_schedule_a_b_is_attached` (each without its `_apply(session)` line). Delete `TAKE_HOME_BOXES`, `_apply`, the `FeeWaiverApplication` import, the four tests at `:111-157` and `test_line_1_counts_the_filer` (`:170-173`). The new docstring:

```python
"""
Form 103B lines 1-3 print what the wizard already asked (3f spec §8.2), and line 6 the
monthly expense total.

Business intent: the court decides a fee waiver from 103B's family size and income, and the
filer swears to them. Line 1 counts the household list as § 820.20(a)(3) reads it through
count_fee_waiver_household: the filer, a spouse at home, and the dependents. Line 2 is
Schedule I line 10 for each person counted, as 103B's own line 2 says, so the two sworn forms
can't differ; the non-cash help line 10 includes is taken out again on the subtract line.
Line 3 reads the 8f answer. Nothing is typed twice. A gap on the Income step refuses the form
rather than print a guessed family of 1 (DIG-223), and a box with nothing to say prints
blank, never 0.00 (103B has no "write $0" instruction).
"""
```

Imports gain `from apps.eligibility.cmi import HOUSEHOLD_UNANSWERED, NOW_DIFFERENT_UNANSWERED, IncomeStepGap`, `from apps.forms.services.derivations import DERIVATIONS, RULE_FIXES`, `from apps.forms.services.fee_waiver import FeeWaiverFamily, FeeWaiverIncome, fee_waiver_family, fee_waiver_income, fee_waiver_noncash`, `from apps.intake.models import DebtInfo, DebtorInfo, ExpenseInfo, IncomeInfo, IntakeSession` and `from apps.intake.tests.builders import answer_household`. At the end of the `session` fixture (`:39-73`), before `return session`:

```python
    IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("3200.00"))
    answer_household(session)  # not married, no one else, every 3e2 answer No or none
```

New module-level data and helpers:

```python
CHILDREN = [
    {"relationship": "son", "age": 8, "lives_with_you": True, "claimed_or_supported": True},
    {"relationship": "daughter", "age": 5, "lives_with_you": True, "claimed_or_supported": True},
]
SPOUSE_AT_HOME = {
    "relationship": "spouse", "age": 44, "lives_with_you": True,
    "claimed_or_supported": True, "spouse_is_dependent": False,
}
SPOUSE_AWAY = {**SPOUSE_AT_HOME, "lives_with_you": False, "claimed_or_supported": False}
SPOUSE_WAGES = {"monthly_gross_wages": Decimal("885.00")}
LINE_1 = ("You", "Your spouse", "Your dependents", "How many dependents", "Total number of people")
LINE_2 = ("undefined_2", "undefined_3", "undefined_4", "undefined_5", "undefined_6")
LINE_3 = ("check 3", "3 type")


def _non_cash(row, kind="SNAP (food stamps)", value=Decimal("350.00")):
    """The 8f answer Yes with non-cash help, on a filer's or a spouse's income row."""
    row.assistance_answer = "yes"
    row.noncash_assistance_kind = kind
    row.noncash_assistance_value = value
    row.save()


def _lines(session, boxes):
    filled = _filled(session)
    return [filled.get(box) for box in boxes]


@pytest.fixture
def with_children_and_snap(session):
    # $3,200 wages, $400 payroll tax, SNAP worth $350: Schedule I line 10 is 3,150.
    answer_household(session, members=CHILDREN, payroll_tax=Decimal("400.00"))
    _non_cash(session.income_info)
    return session
```

The tests:

```python
def test_line_1_counts_the_filer_and_the_children_they_support(with_children_and_snap):
    assert _lines(with_children_and_snap, LINE_1) == [{"/On"}, set(), {"/On"}, {"2"}, {"3"}]


def test_line_2_is_schedule_i_line_10_less_the_non_cash_help_it_includes(with_children_and_snap):
    # 3,150 less the 350 of SNAP line 10 counts: 2,800 (persona targets V8).
    assert DERIVATIONS["schedule_i_income_total_debtor1"](with_children_and_snap) == "3150.00"
    assert _lines(with_children_and_snap, LINE_2) == [
        {"3150.00"}, set(), {"3150.00"}, {"350.00"}, {"2800.00"}
    ]


def test_line_3_names_the_non_cash_help_from_the_income_step(with_children_and_snap):
    assert _lines(with_children_and_snap, LINE_3) == [{"/yes"}, {"SNAP (food stamps)"}]


def test_the_figures_the_filing_fee_page_reads_are_the_ones_103b_prints(with_children_and_snap):
    assert fee_waiver_family(with_children_and_snap) == FeeWaiverFamily(
        total=3, spouse_counted=False, dependents=2
    )
    assert fee_waiver_income(with_children_and_snap) == FeeWaiverIncome(
        you=Decimal("3150.00"), spouse=None, subtotal=Decimal("3150.00"),
        noncash=Decimal("350.00"), total=Decimal("2800.00"),
    )
    assert fee_waiver_noncash(with_children_and_snap) == ("yes", "SNAP (food stamps)")


def test_a_filer_alone_with_no_help_prints_blank_spouse_dependents_and_subtract_lines(session):
    assert _lines(session, LINE_1) == [{"/On"}, set(), set(), set(), {"1"}]
    assert _lines(session, LINE_2) == [{"3200.00"}, set(), {"3200.00"}, set(), {"3200.00"}]
    assert _lines(session, LINE_3) == [{"/no"}, set()]


def test_a_spouse_at_home_is_counted_once_with_their_own_line_10(session):
    answer_household(
        session, marital_status="married_together", members=[SPOUSE_AT_HOME],
        spouse_income=SPOUSE_WAGES,
    )
    assert _lines(session, LINE_1) == [{"/On"}, {"/On"}, set(), set(), {"2"}]
    assert _lines(session, LINE_2) == [{"3200.00"}, {"885.00"}, {"4085.00"}, set(), {"4085.00"}]
    assert _lines(session, LINE_3) == [{"/no"}, set()]


def test_each_counted_persons_non_cash_help_is_named_and_subtracted(session):
    answer_household(
        session, marital_status="married_together", members=[SPOUSE_AT_HOME],
        spouse_income=SPOUSE_WAGES,
    )
    _non_cash(session.income_info)
    _non_cash(session.spouse_income, kind="LIHEAP energy help", value=Decimal("40.00"))
    assert _lines(session, LINE_2) == [{"3550.00"}, {"925.00"}, {"4475.00"}, {"390.00"}, {"4085.00"}]
    assert _lines(session, LINE_3) == [
        {"/yes"}, {"SNAP (food stamps); Spouse: LIHEAP energy help"}
    ]


def test_only_the_spouses_non_cash_help_is_named_as_the_spouses(session):
    answer_household(
        session, marital_status="married_together", members=[SPOUSE_AT_HOME],
        spouse_income=SPOUSE_WAGES,
    )
    _non_cash(session.spouse_income, kind="LIHEAP energy help", value=Decimal("40.00"))
    assert _lines(session, LINE_3) == [{"/yes"}, {"Spouse: LIHEAP energy help"}]


def test_a_spouses_non_cash_help_with_no_known_value_is_named_but_subtracts_nothing(session):
    answer_household(
        session, marital_status="married_together", members=[SPOUSE_AT_HOME],
        spouse_income=SPOUSE_WAGES,
    )
    _non_cash(session.spouse_income, kind="LIHEAP energy help", value=None)
    assert _lines(session, LINE_2) == [{"3200.00"}, {"885.00"}, {"4085.00"}, set(), {"4085.00"}]
    assert _lines(session, LINE_3) == [{"/yes"}, {"Spouse: LIHEAP energy help"}]


def test_a_spouse_living_apart_adds_nothing_to_line_1_line_2_or_line_3(session):
    answer_household(
        session, marital_status="married_separately", members=[SPOUSE_AWAY],
        spouse_income=SPOUSE_WAGES,
    )
    _non_cash(session.spouse_income)  # stored, but the spouse isn't counted
    assert _lines(session, LINE_1) == [{"/On"}, set(), set(), set(), {"1"}]
    assert _lines(session, LINE_2) == [{"3200.00"}, set(), {"3200.00"}, set(), {"3200.00"}]
    assert _lines(session, LINE_3) == [{"/no"}, set()]


def test_a_spouse_living_apart_the_filer_supports_counts_only_as_a_dependent(session):
    answer_household(
        session, marital_status="married_separately",
        members=[{**SPOUSE_AWAY, "spouse_is_dependent": True}],
    )
    assert _lines(session, LINE_1) == [{"/On"}, set(), {"/On"}, {"1"}, {"2"}]


def test_cash_help_is_not_subtracted_and_is_no_non_cash_help(session):
    row = session.income_info
    row.assistance_answer = "yes"
    row.cash_assistance_kind = "TANF"
    row.cash_assistance_amount = Decimal("200.00")
    row.save()
    assert _lines(session, LINE_2) == [{"3400.00"}, set(), {"3400.00"}, set(), {"3400.00"}]
    assert _lines(session, LINE_3) == [{"/no"}, set()]


def test_non_cash_help_with_no_known_value_is_named_but_subtracts_nothing(session):
    _non_cash(session.income_info, value=None)
    assert _lines(session, LINE_2) == [{"3200.00"}, set(), {"3200.00"}, set(), {"3200.00"}]
    assert _lines(session, LINE_3) == [{"/yes"}, {"SNAP (food stamps)"}]


def test_line_1_is_refused_until_the_household_list_is_answered_never_guessed_as_1(session):
    answer_household(session, members=None)
    with pytest.raises(IncomeStepGap) as refused:
        resolve(load_schema("form_103b"), session)
    assert str(refused.value) == HOUSEHOLD_UNANSWERED


@pytest.mark.parametrize(
    "rule",
    [
        "fee_waiver_family_size", "fee_waiver_spouse_counted", "fee_waiver_has_dependents",
        "fee_waiver_dependents_count", "fee_waiver_income_you", "fee_waiver_income_spouse",
        "fee_waiver_income_subtotal", "fee_waiver_income_noncash", "fee_waiver_income_total",
    ],
)
def test_any_income_step_gap_refuses_lines_1_and_2_in_its_own_words(session, rule):
    answer_household(session, income_now_different=None)
    with pytest.raises(IncomeStepGap) as refused:
        DERIVATIONS[rule](session)
    assert str(refused.value) == NOW_DIFFERENT_UNANSWERED


@pytest.mark.parametrize(
    "rule",
    [
        "fee_waiver_family_size", "fee_waiver_dependents_count", "fee_waiver_income_you",
        "fee_waiver_income_spouse", "fee_waiver_income_subtotal", "fee_waiver_income_noncash",
        "fee_waiver_income_total", "fee_waiver_noncash_kinds",
    ],
)
def test_a_refused_line_1_to_3_value_links_to_the_income_step(rule):
    assert RULE_FIXES[rule] == {"step": "income_info"}


def test_no_rule_reads_the_fee_waiver_pages_typed_answers():
    gone = {
        "fee_waiver_household_size", "fee_waiver_monthly_income",
        "fee_waiver_noncash_assistance", "fee_waiver_benefit_types",
    }
    assert gone & (DERIVATIONS.keys() | RULE_FIXES.keys()) == set()
```

Each of these figures was checked against today's Schedule I rules with these exact rows: line 10 is 3150.00, 3200.00 with the spouse's 885.00, 3550.00 with the spouse's 925.00, 3400.00 with cash, 3200.00 with a non-cash kind and no value, and 885.00 for a spouse with a non-cash kind and no value (8f prints blank, which line 9 counts as zero). `income_step_gaps` finds no gap in any of these sessions except the two refusal tests: a non-cash kind with no value is no gap (`cmi._detail_gaps` asks a kind for a value, not a value for a kind). The whole file, with Steps 3 and 4 applied to a scratch copy of `dc31b7a`, passed.

`test_form_103b_schema.py`:

- Imports gain `from apps.eligibility.cmi import MARRIAGE_UNANSWERED, IncomeStepGap`, `IncomeInfo` and `from apps.intake.tests.builders import answer_household`, each in isort order (ruff I001 refuses `builders` above `models`).
- `session_with_fw` (`:34-61`) adds, before `FeeWaiverApplication.objects.create(...)`, `IncomeInfo.objects.create(session=session, monthly_gross_wages=Decimal("1500.00"))` and `answer_household(session)`. The application keeps `household_size=2`.
- `test_fee_waiver_fields` becomes:

  ```python
  def test_line_1_counts_the_household_list_not_the_applications_size(self, session_with_fw):
      # The application says 2; the filer listed no one else, so 103B line 1 is 1.
      field_map = resolve(load_schema("form_103b"), session_with_fw)
      assert field_map["Total number of people"] == "1"
  ```

- `test_empty_session` becomes:

  ```python
  def test_an_empty_session_is_refused_in_the_income_steps_words(self, session):
      with pytest.raises(IncomeStepGap) as refused:
          resolve(load_schema("form_103b"), session)
      assert str(refused.value) == MARRIAGE_UNANSWERED
  ```

`test_schedule_j_schema.py`: import `answer_household` from `apps.intake.tests.builders`, and in `test_every_form_that_copies_the_monthly_expense_total_prints_line_22c` add `answer_household(session)` right after `IncomeInfo.objects.create(...)` (`:362-364`). The comment above it gains: "103B reads the Income step's answers, so they are all given."

`test_rule_fixes.py:175`: `("fee_waiver_benefit_types", {"page": "/fee-waiver"}),` becomes `("fee_waiver_noncash_kinds", {"step": "income_info"}),  # 103B line 3 reads 8f`.

`test_check.py`:

- `:42` becomes `ASSISTANCE = "3 type"  # Form 103B line 3, multi-line, from the Income step's 8f`.
- `:257` becomes `assert (refused.value.label, refused.value.step, refused.value.page) == ("Type of assistance", "income_info", None)`. It is the plan's ruling on §8.2 vs §4 (frame, "For the owner at plan review").

`test_download_action.py:215`: the comment `# fixed on a page` becomes `# fixed on a step`. The assertion is unchanged: a filed form's refusal names neither.

`test_oracle_tier3.py`, in `EXPECTED["maria"]` after `"form_101"` (persona targets V8; the seed's Maria, checked by seeding at `dc31b7a`):

```python
        "form_103b": {
            "You": "/On",
            "Your spouse": "",
            "Your dependents": "/On",
            "How many dependents": "2",
            "Total number of people": "3",
            "undefined_2": "3150.00",
            "undefined_3": "",
            "undefined_4": "3150.00",
            "undefined_5": "350.00",
            "undefined_6": "2800.00",
            "check 3": "/yes",
            "3 type": "SNAP (food stamps)",
        },
```

and in `EXPECTED["sarah"]` after `"form_101"` (her roommate is not claimed or supported, so her family is 1 although 122A-1 `13B` is 2), labelled as a guard (rulings R29), beside Maria's entry, which fails first:

```python
        # Guard: passes before 3f Task 2 (her typed application equals her Income step
        # figures); Maria's entry fails first.
        "form_103b": {
            "You": "/On",
            "Your spouse": "",
            "Your dependents": "",
            "How many dependents": "",
            "Total number of people": "1",
            "undefined_2": "1750.00",
            "undefined_3": "",
            "undefined_4": "1750.00",
            "undefined_5": "",
            "undefined_6": "1750.00",
            "check 3": "/no",
            "3 type": "",
        },
```

`test_oracle_tier2.py:37`: `ASSERTED_CASES = 480`, with the arithmetic from Interfaces as its comment: `# 475 + 103B lines 1-3 (3f Task 2): six re-keyed, eleven new pairs`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest apps/forms/tests/test_form_103b_answers.py apps/forms/tests/test_form_103b_schema.py apps/forms/tests/test_rule_fixes.py apps/forms/tests/test_check.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py -q -p no:cacheprovider`

Expected: FAIL.

- `test_form_103b_answers.py` fails to import: `ModuleNotFoundError: No module named 'apps.forms.services.fee_waiver'`.
- The module error hides the rest of this file. Once Step 3 exists, these are the reasons the rest of it fails before Step 4:
  - Line 1 prints `"1"` from `_fee_waiver_household_size`'s fallback, and `Your spouse`, `Your dependents` and `How many dependents` are unbound.
  - Line 2 prints nothing, because no application exists.
  - The two refusal tests see no `IncomeStepGap`.
  - `DERIVATIONS["fee_waiver_family_size"]` is a `KeyError`.
  - The "gone" test finds four rules.
  - `test_the_figures_the_filing_fee_page_reads_are_the_ones_103b_prints` passes once Step 3 exists: it pins Step 3, and fails first only through the module error.
- `test_line_1_counts_the_household_list_not_the_applications_size` sees `"2"`, and `test_an_empty_session_is_refused…` sees no exception.
- `test_rule_fixes`: `KeyError: 'fee_waiver_noncash_kinds'`. `test_check`: the page is `/fee-waiver`.
- Tier 2: `tier 2 coverage changed` (475 cases, not 480).
- Tier 3: today 103B prints the seeded applications' typed figures. So Maria's `Your dependents`, `How many dependents`, `undefined_2` and `undefined_4` (both `2800.00` today) and `undefined_5` fail with `wrong_value`. Her other seven cases already pass. All twelve of Sarah's pass before the change, because her typed application happens to equal her Income step figures. They pin that the wizard path prints the same, and are not a failing test.

`test_schedule_j_schema.py` passes before the change, and with Step 3 alone. It is a fixture repair for Step 4: without `answer_household`, its session has no 3e2 answers, so once 103B's rules refuse a gap, resolving 103B raises `IncomeStepGap`.

These reasons were checked at `dc31b7a` with the Step 1 tests in a scratch copy: before the change, exactly the two schema tests, `test_rule_fixes[fee_waiver_noncash_kinds…]`, `test_check`'s multi-line case, tier 2's coverage tripwire and Maria's five tier 3 cases fail.

- [ ] **Step 3: Write `fee_waiver.py`**

`backend/apps/forms/services/fee_waiver.py`. Its docstring says it works out 103B lines 1–3 from the household list, Schedule I line 10 and 8f (3f spec §8.2), for the form's rules and the filing-fee page alike, so the two never differ. Imports: `dataclass`, `Decimal`; `counted_spouse_income`, `household_members`, `income_step_gaps` from `apps.eligibility.cmi`; `count_fee_waiver_household` from `apps.intake.household`; `DERIVATIONS` from `apps.forms.services.derivations`. Don't import `IncomeStepGap`: the gaps it raises come from `income_step_gaps`, and an unused import fails ruff (F401).

- `_refuse_any_gap(session) -> None`: `gaps = income_step_gaps(session)`; `if gaps: raise gaps[0]`.
- `_counted_rows(session) -> list`: `getattr(session, "income_info", None)` and `counted_spouse_income(session)`, with the Nones dropped. A session with no filer row has no row to read, and `fee_waiver_noncash` treats that as unanswered, returning `("", "")` and never raising.
- `fee_waiver_family(session)`:
  - `_refuse_any_gap(session)`.
  - `marital_status = session.income_info.marital_status`.
  - `total = count_fee_waiver_household(household_members(session), marital_status)`.
  - `spouse_counted = marital_status in ("married_spouse_filing", "married_together")`, the same test `count_fee_waiver_household` makes. `married_spouse_filing` is already a gap, so only `married_together` reaches it.
  - `dependents = total - (2 if spouse_counted else 1)`.
- `fee_waiver_income(session)`:
  - `_refuse_any_gap(session)`.
  - `you = Decimal(DERIVATIONS["schedule_i_income_total_debtor1"](session))`.
  - `spouse_text = DERIVATIONS["schedule_i_income_total_spouse"](session)`; `spouse = Decimal(spouse_text) if spouse_text else None`. The text is blank unless `married_together`.
  - `subtotal = you + (spouse or Decimal("0"))`.
  - `known = [row.noncash_assistance_value for row in _counted_rows(session) if row.assistance_answer == "yes" and row.noncash_assistance_value is not None]`.
  - `noncash = sum(known, Decimal("0"))`, or None unless it is above 0.
  - `total = subtotal - (noncash or Decimal("0"))`.
- `fee_waiver_noncash(session) -> tuple[str, str]`:

  - Walk `_counted_rows`, the filer first. For each row with `assistance_answer == "yes"` and a non-blank `noncash_assistance_kind.strip()`, collect the kind, with `"Spouse: "` in front for the spouse's row.
  - Collected kinds → `("yes", "; ".join(kinds))`.
  - Otherwise, no rows at all (no filer row), or any counted row with `assistance_answer is None` → `("", "")`. Write the no-rows case out: `any()` over an empty list is False, so without it a session with no income row would swear a "No".
  - Otherwise → `("no", "")`.

- [ ] **Step 4: Rewire `derivations.py`, the schema and the audit files**

`derivations.py`:

- Replace the four functions at `:530-564`, under the same section header, with three shims. Each imports inside its body and carries the comment "fee_waiver reads Schedule I's rules from this module, so it is imported here, not at the top":
  - `def _fee_waiver_family(session: IntakeSession)` returns `fee_waiver_family(session)`.
  - `def _fee_waiver_income(session: IntakeSession)` returns `fee_waiver_income(session)`.
  - `def _fee_waiver_noncash(session: IntakeSession)` returns `fee_waiver_noncash(session)`.
- In `DERIVATIONS` (`:859-865`), the comment "# Form 103B fee waiver derivations" becomes "# Form 103B lines 1-3: the household list, Schedule I line 10 and 8f (3f spec §8.2)". The four old entries become the eleven of Interfaces' table, written as plain lambdas over the shims and two small helpers placed beside them, `_count_or_blank(n: int) -> str` (`str(n)` above 0, else `""`) and `_money_or_blank(amount: Decimal | None) -> str` (`""` for None, else `_fmt(amount)`). Examples: `"fee_waiver_dependents_count": lambda s: _count_or_blank(_fee_waiver_family(s).dependents),` and `"fee_waiver_income_noncash": lambda s: _money_or_blank(_fee_waiver_income(s).noncash),`. The app code uses no `:=` (only `tests/pdf_readback.py:87` does), so these lambdas don't either. Line 6's comment and `fee_waiver_monthly_expenses` stay where they are.
- In `RULE_FIXES`, the block "# The fee-waiver application" (`:1080-1083`) goes. Under "# Income" (beside `schedule_i_income_total_spouse`, `:1005`) add "# 103B lines 1-3 read the household list, Schedule I line 10 and 8f" and the eight entries of Interfaces.

`form_103b.json`. Each new field copies the key order of its neighbours (`:40-76`): `pdf_field, type, source, [choices,] page, label, required, conditional_on, value, rule, ingest_key, binding, repeat, repeat_capacity, row, legal_review`, with `source` `"derived"`, `page` 1, `required` and `legal_review` false, and `conditional_on`, `value`, `ingest_key`, `binding`, `repeat`, `repeat_capacity` and `row` null. The fields, in this order after `You`:

| `pdf_field`                 | `type`   | `choices`         | `label` (refusals quote it)                                              | `rule`                        |
| --------------------------- | -------- | ----------------- | ------------------------------------------------------------------------ | ----------------------------- |
| `Your spouse` (new)         | checkbox | `{"true": "/On"}` | `Your spouse`                                                            | `fee_waiver_spouse_counted`   |
| `Your dependents` (new)     | checkbox | `{"true": "/On"}` | `Your dependents`                                                        | `fee_waiver_has_dependents`   |
| `How many dependents` (new) | text     | —                 | `How many dependents?`                                                   | `fee_waiver_dependents_count` |
| `Total number of people`    | text     | —                 | unchanged (`Household size`)                                             | `fee_waiver_family_size`      |
| `undefined_2`               | text     | —                 | unchanged (`You: average monthly net income (take-home pay)`)            | `fee_waiver_income_you`       |
| `undefined_3` (new)         | text     | —                 | `Your spouse: average monthly net income (take-home pay)`                | `fee_waiver_income_spouse`    |
| `undefined_4`               | text     | —                 | unchanged (`Subtotal: …`)                                                | `fee_waiver_income_subtotal`  |
| `undefined_5` (new)         | text     | —                 | `Subtract any non-cash governmental assistance that you included above.` | `fee_waiver_income_noncash`   |
| `undefined_6`               | text     | —                 | unchanged                                                                | `fee_waiver_income_total`     |
| `check 3`                   | checkbox | unchanged         | unchanged                                                                | `fee_waiver_noncash_answer`   |
| `3 type`                    | text     | —                 | unchanged (`Type of assistance`)                                         | `fee_waiver_noncash_kinds`    |

`3 type`'s label stays `Type of assistance`, because `test_check.py:257` and `test_download_action.py:215` read it as the refusal's label.

`step2_verification.json`: delete the four 103B rows after the `You` row (`:202-241`) and put eleven rows in their place, after the `You` row (`:193-201`), in the order of the table below. Each has the shape `{"schema": "form_103b", "pdf_field": <box>, "producer": "derived:<rule>", "original_verdicts": [], "final_verdicts": ["correct"], "status": "confirmed", "correct_target": <box>, "evidence": …}`. Each evidence starts with the box's field-index row, as the `You` row and the four rows it replaces do: "Field index: <box> p1 line <n> '<label>'[, column '<column>'][, states …] (sampled_ok)." It continues with the ruling:

| Box                      | Index facts to cite                                                                                      | Ruling to cite                                                                                                                                                        |
| ------------------------ | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Your spouse`            | line 1 'Your spouse', option 'Your spouse', state /On                                                    | 3f spec §8.2: ticked when 103B line 1's count includes the spouse (`married_together`)                                                                                |
| `Your dependents`        | line 1 'Your dependents', option 'Your dependents', state /On                                            | §8.2: ticked when `dependents()` less a spouse already counted is above 0                                                                                             |
| `How many dependents`    | line 1 'How many dependents?' (count)                                                                    | §8.2: that number, printed only above 0                                                                                                                               |
| `Total number of people` | line 1 'Total number of people' (count)                                                                  | §8.2 and DIG-223: `count_fee_waiver_household` over the household list; replaces `derived:fee_waiver_household_size`                                                  |
| `undefined_2`            | line 2 'You', column 'That person’s average monthly net income (take-home pay)'                          | §8.2 and owner answer 1 (2026-11-02): Schedule I line 10 column 1, as 103B line 2 says ("see line 10 of that schedule"); replaces `derived:fee_waiver_monthly_income` |
| `undefined_3`            | line 2 'Your spouse', same column                                                                        | §8.2: Schedule I line 10 column 2 for `married_together`, blank otherwise                                                                                             |
| `undefined_4`            | line 2 'Subtotal', same column                                                                           | §8.2: the two added; replaces `derived:fee_waiver_monthly_income`                                                                                                     |
| `undefined_5`            | line 2 'Subtract any non-cash governmental assistance that you included above.', same column             | §8.2 and §16 call 13: the counted people's known 8f non-cash values, only above $0                                                                                    |
| `undefined_6`            | line 2 'Your family’s average monthly net income', column 'Total'                                        | §8.2: the subtotal less `undefined_5`; replaces `derived:fee_waiver_monthly_income`                                                                                   |
| `check 3`                | line 3 'Do you receive non-cash governmental assistance?', states /no ('No') and /yes ('Yes. Describe.') | §8.2: 8f, Yes when a counted person answered Yes with a non-cash kind, No when none did; replaces `derived:fee_waiver_noncash_assistance`                             |
| `3 type`                 | line 3 'Type of assistance', the box beside 'Yes. Describe.'                                             | §8.2 and §16 call 14: the non-cash kinds, the filer's then "Spouse: " and the spouse's, joined by "; "; replaces `derived:fee_waiver_benefit_types`                   |

`form_103b.unbound.json`: delete the four entries named in Files. Each lists boxes this task binds.

Run: the Step 2 command, plus `apps/forms/tests/test_schedule_j_schema.py`, `apps/forms/tests/test_checks.py` and `apps/forms/tests/test_oracle_tier1.py`.

Expected: PASS. Tier 1 gains the new text and box cases on its own, uncounted. `test_every_step2_placement_matches_a_binding` passes with the eleven rows. Tier 2 is 480.

- [ ] **Step 5: Update `CLAUDE.md`**

The edits in Interfaces' "CLAUDE.md" bullets, each sentence as written there.

- [ ] **Step 6: Gates**

Check `uptime` first, and run the full suite only while the 1-minute load is under 10.

- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 -q -p no:cacheprovider`. Expected: 0 failed, coverage ≥ 90%. `test_printed_page.py`'s `_seeded()` and `test_api_readback.py` still pass: every persona answers every Income step question, and Maria's 103B ticks more boxes, which `test_unticked_boxes_keep_their_squares` allows.
- `/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/` (ruff 0.8.5). Expected: `All checks passed!`.
- `cd backend && $PY manage.py check`. Expected: "System check identified no issues" (forms.E001–E007 accept the four new bindings and the re-ruled seven).

No model changes, so no `makemigrations --check` and no `postgres` run. No frontend change, and no journeys (frame: Tasks 1, 5, 8 and 9).

- [ ] **Step 7: Commit**

```bash
/usr/bin/git add backend/apps/forms/services/fee_waiver.py backend/apps/forms/services/derivations.py data/forms/schemas/form_103b.json data/forms/field_index/audit/step2_verification.json data/forms/field_index/audit/form_103b.unbound.json backend/apps/forms/tests/test_form_103b_answers.py backend/apps/forms/tests/test_form_103b_schema.py backend/apps/forms/tests/test_schedule_j_schema.py backend/apps/forms/tests/test_rule_fixes.py backend/apps/forms/tests/test_check.py backend/apps/forms/tests/test_download_action.py backend/apps/forms/tests/test_oracle_tier2.py backend/apps/forms/tests/test_oracle_tier3.py CLAUDE.md
/usr/bin/git commit -F /tmp/3f-task2-msg.txt
```

The message, in `/tmp/3f-task2-msg.txt`, with no trailer:

```
feat(forms): 103B lines 1-3 read the household list, Schedule I and 8f

Line 1 counts the filer, a spouse at home and the dependents from the
household list, and refuses on an Income step gap instead of printing
a guessed 1. Line 2 is Schedule I line 10 per person counted, less
the non-cash help it includes. Line 3 reads the 8f answer. Nothing on
the fee-waiver page prints any more.
```

### Task 3: One encrypted filing-fee record and its API

**Spec:** §4 (the record), §6.2 (the information and its two gaps), §6.4 ("Length"), §6.5 (the API), §13 ("Also": `answer_household`, the lock test), §16 calls 2, 9, 11, 17, 23.

**Files:**

- Modify: `backend/apps/intake/models.py`. Add `class FilingFee` after `FeeWaiverApplication` (`:863-987`) and before `SOFAReport` (`:990`). `FeeWaiverApplication` stays until Task 8.
- Create: `backend/apps/intake/migrations/0029_filingfee.py`. It depends on `0028_shift_current_step`.
- Modify: `backend/apps/intake/serializers.py`. `FilingFee` joins the models import (`:27-44`), and `FilingFeeSerializer` goes after `FeeWaiverApplicationSerializer` (`:817-887`).
- Create: `backend/apps/intake/filing_fee.py`.
- Modify: `backend/apps/intake/views.py`:
  - `FilingFee` joins the models import (`:26-35`) and `FilingFeeSerializer` the serializers import (`:36-48`);
  - add `from .filing_fee import filing_fee_information`;
  - add the action `filing_fee` after `delete_codebtor` (`:556-571`) and before `dischargeability` (`:573`).
- Modify: `backend/apps/intake/tests/builders.py`: the models import (`:12`), and `answer_household` (`:37-81`) with its docstring.
- Create: `backend/apps/intake/tests/test_filing_fee.py`.
- Modify: `backend/apps/intake/tests/test_session_lock.py`. `WRITES` (`:485-584`) gains `"filing-fee PUT"` after `"codebtor DELETE"` (`:532-537`).
- Modify: `backend/apps/intake/tests/test_data_migrations.py`: a `FILING_FEE` constant after `SHIFT` (`:29`), and the 0029 round trip with its Postgres twin appended after `:609`.
- Modify: `CLAUDE.md:27`, the gotcha "Saves lock the session".

**Interfaces:**

- Consumes:
  - From Task 1: `poverty_guideline_in_force()` and `poverty_limit_monthly(guideline, family_size)` (`apps/districts/poverty.py`), and the 2026 `PovertyGuideline` row from `0005_poverty_guideline_2026`.
  - From Task 2: `fee_waiver_family(session).total` and `fee_waiver_income(session).total` (`apps/forms/services/fee_waiver.py`), and the rules `fee_waiver_family_size` and `fee_waiver_income_total` (`DERIVATIONS`, `apps/forms/services/derivations.py:777`).
  - `NoTableInForce` (`apps/districts/dated_tables.py:38`), `IncomeStepGap` (`apps/eligibility/cmi.py:79`), `lock_session` (`apps/intake/locking.py:6`) and `YES_NO` (`apps/intake/models.py:16`).
- Produces:

  - `FilingFee(models.Model)`, `Meta.db_table = "filing_fees"`, `__str__` → `f"Filing fee (Session: {self.session_id})"`:
    - `session = models.OneToOneField(IntakeSession, on_delete=models.CASCADE, related_name="filing_fee")`;
    - `payment_choice = EncryptedCharField(max_length=20, null=True, blank=True)`;
    - `income_change_answer`, `others_covered_answer` and `expense_change_answer`, each `EncryptedCharField(max_length=3, null=True, blank=True)`;
    - `income_change_explanation`, `installments_explanation`, `others_covered_who` and `expense_change_explanation`, each `EncryptedTextField(blank=True, default="")`;
    - `created_at = models.DateTimeField(auto_now_add=True)` and `updated_at = models.DateTimeField(auto_now=True)`;
    - `PAYMENT_CHOICES: ClassVar[tuple[str, ...]] = ("pay_in_full", "installments", "waiver")`;
    - `YES_NO_FIELDS: ClassVar[tuple[str, ...]] = ("income_change_answer", "others_covered_answer", "expense_change_answer")`;
    - `TEXT_LIMITS: ClassVar[dict[str, int]] = {"income_change_explanation": 520, "installments_explanation": 520, "others_covered_who": 420, "expense_change_explanation": 420}`. These are measured against 103B's `4 type`, `5 Type`, `undefined_8` and `undefined_10`; see "Decided here".
  - `FilingFeeSerializer(serializers.Serializer)`. It is plain, not a `ModelSerializer`, as `IncomeEntrySerializer` (`serializers.py:95`) and `HouseholdMemberSerializer` (`:527`) are: every field is declared, and the view, not `save()`, writes the row under the lock. Its fields:

    - `payment_choice = ChoiceField(choices=FilingFee.PAYMENT_CHOICES, required=False)`, with no `allow_null`;
    - each of `YES_NO_FIELDS` is `ChoiceField(choices=YES_NO, allow_null=True, required=False)`;
    - each text is `CharField(max_length=FilingFee.TEXT_LIMITS[name], allow_blank=True, required=False)`.

    `validate(attrs)` refuses every key of `self.initial_data` that isn't one of these eight. The 400 is `{<key>: ["This is not one of the filing-fee answers."]}`, one entry per unknown key.

  - `filing_fee_information(session) -> tuple[dict | None, str | None]` in `apps/intake/filing_fee.py`. It returns one of:
    - `({"family_size": int, "limit_monthly": "1995.00", "guideline": {"year": int, "effective_date": "YYYY-MM-DD", "source_url": str}, "family_income_monthly": "1750.00"}, None)`;
    - `(None, "income")`;
    - `(None, "no_table")`.
  - `IntakeSessionViewSet.filing_fee`, `@action(detail=True, methods=["get", "put"], url_path="filing-fee", url_name="filing-fee")`. Both methods return `{<the eight answers>, "information", "information_gap"}`.
  - `answer_household(..., payment_choice: str | None = "pay_in_full")`.
  - `ASSERTED_CASES` does not change, since this task binds nothing (delta 0, stays at Task 2's value).

- CLAUDE.md: "Saves lock the session" (Step 7 gives its two sentences as they read after this task).

**Decided here:**

- **`payment_choice: null` on a PUT is a 400** (ruling R9). §6.5 validates `payment_choice` "against the three values" and only the yes/no answers "against `yes`, `no` and null". The frame's "or null" (Global Constraints, "Values") describes what is stored: unanswered, before the first save. The spec wins. A filer changes the answer; nothing takes it back to unanswered.
- **Only the eight answers are known keys.** A PUT that sends `information`, `information_gap`, `session`, an id or any other key is a 400 naming each one. Task 5's page sends only the answer keys, never the GET body sent back.
- **A refused PUT stores nothing.** The serializer validates before the lock, as `_save_list` does (`views.py:59-60`). `FilingFee.objects.get_or_create` then runs inside `transaction.atomic()` after `lock_session`, and the validated keys are set with `setattr` and saved. A GET never creates a row. It serializes an unsaved `FilingFee(session=session)` when none is stored, so every answer reads null or `""`.
- **Texts are strings.** A null text is a 400; blank is `""`. DRF's default `trim_whitespace` applies.
- **The information body:**
  - `information_gap` is null whenever `information` is shown.
  - The income gap is checked first. When both apply, the gap is `"income"` and the table isn't looked up, so it isn't logged.
  - `guideline.year` is `effective_date.year`, because `PovertyGuideline` has no year column.
  - Money is written `f"{value:.2f}"`.
  - `family_size` is `fee_waiver_family(session).total`. `family_income_monthly` is `fee_waiver_income(session).total`, the figure 103B line 2's `undefined_6` prints (§6.2, §8.2).
- **`answer_household(payment_choice=None)` creates no `FilingFee` and leaves any stored one alone,** as `spouse_income=None` already does (`builders.py:53`, `:74`). Any other value is stored on the session's row, which is created if missing. Task 4's `_needs_fee_choice` must refuse both no row and a row with a null answer, because migrated sessions have no row (§4).
- **The text limits** (ruling R10). §6.4 wants the limits from `check()` at the box's smallest font. The method is the frame's owner-review ruling: "the longest repeated sample the box accepts, rounded down to a multiple of 10". The sample is Maria's owner-approved line 5 (§10) plus one space, repeated and cut at the length. `PDFFormFiller().check("form_103b", {box: text})` accepts at most:

  - 527 characters in `4 type` and in `5 Type` (page 1, T20 and T22, multi-line, 280.8 pt wide), so their limit is 520;
  - 427 characters in `undefined_8` and in `undefined_10` (page 2, T5 and T11, multi-line, 281.5 and 281.3 pt wide), so their limit is 420.

  These were measured at `dc31b7a` by binary search, and every shorter length also passed. `check()` takes unbound keys, with the index row's label (`pdf_filler.py:152-171`), so the measurement doesn't need Task 4's bindings.

  A count of characters can't promise a fit:

  - one unbroken word fits only 48 W's or 92 x's;
  - text of eight-letter words of capital W's ("WWWWWWWW WWWWWWWW …") fits 232 and 187 characters;
  - `_as_printed` keeps line breaks (`pdf_filler.py:174-186`), so a text of many short lines fits fewer characters.

  So `check()` at Generate stays the last word: a text under the limit that still doesn't fit is a 422 that links to `/filing-fee`, through Task 4's `RULE_FIXES`. The page reads the same four numbers from `frontend/src/constants/filingFee.ts` (`FILING_FEE_TEXT_LIMITS`), which Task 5 adds and pins to `FilingFee.TEXT_LIMITS` with `test_filing_fee_frontend_copy.py`; this task adds no frontend copy.

- **The information tests are plain `db` tests** (ruling R4). The 2026 row comes from Task 1's data migration. A transactional test's flush deletes it, and pytest-django runs transactional tests after `db` tests (`pytest_django/plugin.py:437-476`), so a plain `db` test may rely on the migrated row. Task 1's root `backend/conftest.py` fixture `poverty_2026` is for a test that needs the row after a flush; no test here does. The lock test is transactional, so its PUT may reply with `information_gap: "no_table"`, still a 200. It asserts only the wait and the status, so the entry holds without `poverty_2026`.
- **`get_queryset`'s `select_related` (`views.py:137-144`) is left as it is.** The action reads the row with its own query.
- **CLAUDE.md "Forms need a completed intake"** lists the writes that never reopen ("Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it"). That is the behaviour this task's PUT adds, but the frame gives that gotcha to Task 4, so it is left for Task 4.

- [ ] **Step 1: Write the failing tests**

`backend/apps/intake/tests/test_filing_fee.py`:

```python
"""Form 101 line 8 and 103B's own answers, kept on one encrypted record (3f spec §4, §6.5).

Business intent: how the filer will pay the filing fee is the filer's own answer. Nothing
starts answered, a save changes only what it sends, and a choice moved off the waiver keeps
the waiver answers for a return. Every answer is filer data, so it is ciphertext in the table.
The court's limit and the filer's own figure are shown beside the question as information
only: when either can't be worked out the page says why, and the answer still saves. Saving
never sends a completed intake back to be completed again, and another filer's session is
never found.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from rest_framework.test import APIClient

from apps.districts.models import District, PovertyGuideline
from apps.forms.services.derivations import DERIVATIONS
from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
from apps.intake.models import FilingFee, IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household
from apps.users.models import User

ANSWER_FIELDS = (
    "payment_choice",
    "income_change_answer",
    "income_change_explanation",
    "installments_explanation",
    "others_covered_answer",
    "others_covered_who",
    "expense_change_answer",
    "expense_change_explanation",
)
# Maria's line 5, approved by the owner (spec §10); the text limits are measured with it.
LINE_5_DRAFT = (
    "I support two children on what I earn. After rent, food, the car and the children's "
    "costs, there is not enough left each month to pay the fee, even in parts."
)
ROOMMATE = {
    "relationship": "roommate",
    "age": 29,
    "lives_with_you": True,
    "claimed_or_supported": False,
}
# Every answer given, for the ciphertext check: (value, a piece that must not show in the table).
ANSWERS = {
    "payment_choice": ("installments", "installments"),
    "income_change_answer": ("yes", None),
    "income_change_explanation": ("My hours at the store drop in December.", "December"),
    "installments_explanation": (LINE_5_DRAFT, "children"),
    "others_covered_answer": ("yes", None),
    "others_covered_who": ("My mother, who stays with us each summer.", "mother"),
    "expense_change_answer": ("yes", None),
    "expense_change_explanation": ("My rent goes up $90 in March.", "March"),
}


def _filer(username):
    user = User.objects.create_user(username=username, password="pw")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def sarah(db):
    """A completed intake shaped like Sarah's (spec §10): not married, a roommate she doesn't
    support, $2,000.00 in wages less $250.00 taken out of pay, and no line 8 answer yet."""
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    client, user = _filer("filer")
    session = IntakeSession.objects.create(
        user=user, district=district, status="completed", current_step=9
    )
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("2000.00")
    )
    answer_household(
        session, members=[ROOMMATE], payroll_tax=Decimal("250.00"), payment_choice=None
    )
    return client, session


def _url(session):
    return f"/api/intake/sessions/{session.pk}/filing-fee/"


def _put(client, session, body):
    return client.put(_url(session), body, format="json")


def _sample(length):
    """Maria's line 5, repeated and cut at length."""
    text = LINE_5_DRAFT + " "
    return (text * (length // len(text) + 1))[:length]


def test_nothing_is_answered_until_the_filer_answers(sarah):
    client, session = sarah
    body = client.get(_url(session)).json()
    assert set(body) == {*ANSWER_FIELDS, "information", "information_gap"}
    assert {name: body[name] for name in ANSWER_FIELDS} == {
        "payment_choice": None,
        "income_change_answer": None,
        "income_change_explanation": "",
        "installments_explanation": "",
        "others_covered_answer": None,
        "others_covered_who": "",
        "expense_change_answer": None,
        "expense_change_explanation": "",
    }
    assert not FilingFee.objects.filter(session=session).exists()  # reading stores nothing


def test_the_court_limit_and_the_filers_own_figure_are_shown_beside_the_question(sarah):
    client, session = sarah
    body = client.get(_url(session)).json()
    guideline = PovertyGuideline.objects.get(effective_date=date(2026, 1, 15))
    # Exactly these four keys: the two figures and where the limit comes from, never a verdict.
    assert body["information"] == {
        "family_size": 1,
        "limit_monthly": "1995.00",
        "guideline": {
            "year": 2026,
            "effective_date": "2026-01-15",
            "source_url": guideline.source_url,
        },
        "family_income_monthly": "1750.00",
    }
    assert body["information_gap"] is None


def test_the_figure_shown_is_the_family_and_total_form_103b_prints(sarah):
    client, session = sarah
    information = client.get(_url(session)).json()["information"]
    assert information["family_size"] == int(DERIVATIONS["fee_waiver_family_size"](session))
    assert Decimal(information["family_income_monthly"]) == Decimal(
        DERIVATIONS["fee_waiver_income_total"](session)
    )


def test_a_save_changes_only_the_answers_it_sends_and_a_withdrawn_waiver_keeps_its_answers(sarah):
    client, session = sarah
    first = _put(
        client,
        session,
        {
            "payment_choice": "waiver",
            "income_change_answer": "no",
            "installments_explanation": LINE_5_DRAFT,
        },
    )
    assert first.status_code == 200
    assert first.json()["payment_choice"] == "waiver"
    assert first.json()["information"]["limit_monthly"] == "1995.00"  # the reply is the GET body

    moved = _put(client, session, {"payment_choice": "pay_in_full"}).json()
    assert (moved["payment_choice"], moved["income_change_answer"]) == ("pay_in_full", "no")
    assert moved["installments_explanation"] == LINE_5_DRAFT

    back = _put(client, session, {"payment_choice": "waiver"}).json()
    assert (back["income_change_answer"], back["installments_explanation"]) == ("no", LINE_5_DRAFT)


def test_a_yes_or_no_answer_can_be_left_unanswered_again(sarah):
    client, session = sarah
    _put(client, session, {"others_covered_answer": "yes"})
    reply = _put(client, session, {"others_covered_answer": None})
    assert reply.status_code == 200
    assert FilingFee.objects.get(session=session).others_covered_answer is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("payment_choice", "monthly"),
        ("payment_choice", None),  # a filer changes the answer; nothing takes it back
        ("payment_choice", ""),
        ("income_change_answer", "maybe"),
        ("others_covered_answer", True),
        ("expense_change_answer", ""),
        ("others_covered_who", None),
    ],
)
def test_an_answer_no_question_on_the_page_can_have_is_refused_and_nothing_is_stored(
    sarah, field, value
):
    client, session = sarah
    reply = _put(client, session, {field: value})
    assert reply.status_code == 400
    assert field in reply.json()
    assert not FilingFee.objects.filter(session=session).exists()


@pytest.mark.parametrize(
    "key,value",
    [("monthly_take_home_pay", "1750.00"), ("information", None), ("session", 1)],
)
def test_a_key_that_is_not_a_filing_fee_answer_is_refused_by_name_and_nothing_is_stored(
    sarah, key, value
):
    client, session = sarah
    reply = _put(client, session, {"payment_choice": "waiver", key: value})
    assert reply.status_code == 400
    assert set(reply.json()) == {key}
    assert not FilingFee.objects.filter(session=session).exists()


@pytest.mark.parametrize("field", sorted(FilingFee.TEXT_LIMITS))
def test_a_text_is_kept_up_to_its_limit_and_refused_past_it(sarah, field):
    client, session = sarah
    limit = FilingFee.TEXT_LIMITS[field]
    assert _put(client, session, {field: _sample(limit)}).status_code == 200
    assert getattr(FilingFee.objects.get(session=session), field) == _sample(limit).strip()
    assert _put(client, session, {field: _sample(limit + 1)}).status_code == 400


@pytest.mark.parametrize(
    "field,box,limit",
    [
        ("income_change_explanation", "4 type", 520),
        ("installments_explanation", "5 Type", 520),
        ("others_covered_who", "undefined_8", 420),
        ("expense_change_explanation", "undefined_10", 420),
    ],
)
def test_the_longest_text_the_page_takes_fits_its_box_on_form_103b(field, box, limit):
    assert FilingFee.TEXT_LIMITS[field] == limit
    PDFFormFiller().check("form_103b", {box: _sample(limit)})  # fits, at some size down to 6 pt
    with pytest.raises(ValueTooLong):
        # The next ten characters don't: the limit is the box's, rounded down to ten.
        PDFFormFiller().check("form_103b", {box: _sample(limit + 10)})


def test_a_filing_fee_save_never_sends_a_completed_intake_back(sarah):
    client, session = sarah
    assert _put(client, session, {"payment_choice": "pay_in_full"}).status_code == 200
    session.refresh_from_db()
    assert session.status == "completed"


def test_an_intake_reopened_with_an_income_gap_shows_no_figures_and_still_saves_the_answer(sarah):
    client, session = sarah
    reopened = client.patch(
        f"/api/intake/sessions/{session.pk}/",
        {"income_info": {"income_now_different": None}},
        format="json",
    )
    assert reopened.status_code == 200
    session.refresh_from_db()
    assert session.status == "in_progress"

    body = client.get(_url(session)).json()
    assert (body["information"], body["information_gap"]) == (None, "income")

    saved = _put(client, session, {"payment_choice": "waiver"})
    assert saved.status_code == 200
    assert (saved.json()["payment_choice"], saved.json()["information_gap"]) == ("waiver", "income")
    assert FilingFee.objects.get(session=session).payment_choice == "waiver"


def test_with_no_poverty_table_in_force_the_page_says_so_logs_and_still_saves_the_answer(
    sarah, monkeypatch, caplog
):
    client, session = sarah
    # The day before the 2026 guideline was published: none of DigniFi's rows is in force.
    monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2026, 1, 14))
    body = client.get(_url(session)).json()
    assert (body["information"], body["information_gap"]) == (None, "no_table")
    assert [
        r.getMessage() for r in caplog.records if r.name == "apps.districts.dated_tables"
    ] == ["No HHS poverty guidelines table in force on 2026-01-14 for district -"]

    assert _put(client, session, {"payment_choice": "installments"}).status_code == 200
    assert FilingFee.objects.get(session=session).payment_choice == "installments"


def test_another_filers_session_is_not_found(sarah):
    _, session = sarah
    stranger, _ = _filer("stranger")
    assert stranger.get(_url(session)).status_code == 404
    assert _put(stranger, session, {"payment_choice": "waiver"}).status_code == 404
    assert not FilingFee.objects.filter(session=session).exists()


@pytest.mark.parametrize("field", ANSWER_FIELDS)
def test_every_filing_fee_answer_is_ciphertext_in_the_table(sarah, field):
    client, session = sarah
    body = {name: value for name, (value, _) in ANSWERS.items()}
    assert _put(client, session, body).status_code == 200
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {field} FROM filing_fees WHERE session_id = %s", [session.pk])
        raw = cursor.fetchone()[0]
    plain = ANSWERS[field][1]
    assert raw.startswith("gAAAAA") and (plain is None or plain not in raw)  # a Fernet token


def test_the_shared_test_household_pays_in_full_so_forms_tests_meet_no_new_refusal(sarah):
    _, session = sarah
    answer_household(session, members=[ROOMMATE], payroll_tax=Decimal("250.00"))
    assert FilingFee.objects.get(session=session).payment_choice == "pay_in_full"
    answer_household(session, payment_choice=None)  # leaves the stored answer alone
    assert FilingFee.objects.get(session=session).payment_choice == "pay_in_full"
```

`test_data_migrations.py`: add `FILING_FEE = [("intake", "0029_filingfee")]` after `SHIFT` (`:29`), then append (Task 8 reuses this constant):

```python
def _filing_fee_round_trip(migrate):
    apps = migrate(SHIFT)
    session = _session(apps)
    apps = migrate(FILING_FEE)
    FilingFee = apps.get_model("intake", "FilingFee")
    FilingFee.objects.create(session_id=session.pk)
    row = FilingFee.objects.get()
    kept = (row.payment_choice, row.income_change_answer, row.installments_explanation)
    migrate(SHIFT)
    return kept, "filing_fees" in connection.introspection.table_names()


def test_the_filing_fee_record_starts_unanswered_and_undoing_it_drops_its_table(migrate):
    kept, table_left = _filing_fee_round_trip(migrate)
    assert kept == (None, None, "")
    assert table_left is False


@pytest.mark.postgres
@ON_POSTGRES
def test_the_filing_fee_record_starts_unanswered_and_undoing_it_drops_its_table_on_postgres(
    migrate,
):
    kept, table_left = _filing_fee_round_trip(migrate)
    assert kept == (None, None, "")
    assert table_left is False
```

`test_session_lock.py`, in `WRITES` after `"codebtor DELETE"`. The `ready` fixture's `answer_household` stores `pay_in_full`, so this PUT changes the stored row:

```python
    "filing-fee PUT": lambda s, r: (
        "put",
        _session_url(s, "filing-fee/"),
        {"payment_choice": "waiver"},
        200,
    ),
```

`test_every_intake_write_waits_for_a_save_in_progress` (`:586-603`) asserts only the wait and the status, never a reopen, so it covers a write that never reopens without any change.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest apps/intake/tests/test_filing_fee.py apps/intake/tests/test_data_migrations.py -q -p no:cacheprovider`

Expected: FAIL.

- `test_filing_fee.py` errors at collection with `ImportError: cannot import name 'FilingFee' from 'apps.intake.models'`.
- The 0029 round trip fails with `NodeNotFoundError` for `('intake', '0029_filingfee')`. Its `_on_postgres` twin is SKIPPED on sqlite.

Then, with `uptime` showing a 1-minute load under 10: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres apps/intake/tests/test_session_lock.py -k "filing-fee" -q -p no:cacheprovider`

Expected: FAIL. The PUT is answered `404` (no `filing-fee` action yet), and the assertion prints `waited` False. Under the default settings the whole file skips with its stated reason.

- [ ] **Step 3: Implement the model and its migration**

- `FilingFee` as in Interfaces, with this docstring: "How the filer will pay the filing fee (Form 101 line 8), and Form 103B's own questions 4, 5, 7 and 9 for a filer who asks for a waiver (3f spec §4). Every answer is encrypted; null means unanswered. It is not intake data: saving it never reopens a completed intake."
- Generate the migration with `cd backend && $PY manage.py makemigrations intake -n filingfee`.

  - Expected: `0029_filingfee.py`, one `CreateModel` with `db_table` `filing_fees`, depending on `("intake", "0028_shift_current_step")`.
  - Read it before staging: it must hold no other operation.

- [ ] **Step 4: Implement the serializer, the information and the action**

- `FilingFeeSerializer` in `serializers.py`, as in Interfaces. Its docstring: "The filing-fee page's answers (3f spec §6.5). A PUT sets only the keys it sends. DRF drops an unknown key silently, so validate() refuses it by name: a page that sent an answer under the wrong name gets a 400 instead of losing it."

  `validate(self, attrs)`:

  ```python
  unknown = sorted(set(self.initial_data) - set(self.fields))
  if unknown:
      raise serializers.ValidationError(
          {name: ["This is not one of the filing-fee answers."] for name in unknown}
      )
  return attrs
  ```

  It runs after the field checks, so a body that isn't a JSON object is refused before `initial_data` is read as one.

- `apps/intake/filing_fee.py`, module docstring: "What the filing-fee page shows beside Form 101 line 8, as information only (3f spec §6.2). Never a verdict: the court decides." The imports are `poverty_guideline_in_force` and `poverty_limit_monthly` (`apps.districts.poverty`), `NoTableInForce` (`apps.districts.dated_tables`), `IncomeStepGap` (`apps.eligibility.cmi`), and `fee_waiver_family` and `fee_waiver_income` (`apps.forms.services.fee_waiver`).

  ```python
  def filing_fee_information(session) -> tuple[dict | None, str | None]:
      """The court's limit for the filer's family and the filer's own 103B line 2 figure, or
      None and why: "income" while the Income step has a gap, "no_table" while no HHS poverty
      guideline is in force on the fill date (in_force logs which). It never blocks a save."""
  ```

  The body:

  - Call `fee_waiver_family(session)` and `fee_waiver_income(session)` in one `try`. On `IncomeStepGap`, return `(None, "income")`.
  - Then call `poverty_guideline_in_force()`. On `NoTableInForce`, return `(None, "no_table")`.
  - Otherwise return the dict of Interfaces:
    - `limit_monthly` is `f"{poverty_limit_monthly(guideline, family.total):.2f}"`;
    - `family_income_monthly` is `f"{income.total:.2f}"`;
    - `guideline` is `{"year": guideline.effective_date.year, "effective_date": guideline.effective_date.isoformat(), "source_url": guideline.source_url}`.

  It logs nothing itself.

- The action in `views.py`:

  ```python
  @action(detail=True, methods=["get", "put"], url_path="filing-fee", url_name="filing-fee")
  def filing_fee(self, request, pk=None):
      """GET or PUT /api/intake/sessions/{id}/filing-fee/ (3f spec §6.5).

      In any status. A PUT sets only the answers it sends, under the session lock, and never
      reopens a completed intake: how the fee is paid is not intake data. Both reply with the
      eight answers, information and information_gap.
      """
  ```

  The body:

  - `session = self.get_object()`, with the comment "another user's session is a 404".
  - On PUT:
    - build `serializer = FilingFeeSerializer(data=request.data, partial=True)` and call `serializer.is_valid(raise_exception=True)`;
    - then, inside `with transaction.atomic():`, call `lock_session(session.pk)` and `row, _ = FilingFee.objects.get_or_create(session=session)`;
    - set each validated key with `setattr` and call `row.save()`.
  - Both methods then reply:
    - `row = FilingFee.objects.filter(session=session).first() or FilingFee(session=session)`;
    - `information, gap = filing_fee_information(session)`;
    - `return Response({**FilingFeeSerializer(row).data, "information": information, "information_gap": gap})`.

  No `session.reopen()`.

- [ ] **Step 5: `answer_household` stores a pay-in-full answer**

- Import `FilingFee` beside `Household, SpouseIncome` (`builders.py:12`).
- Add the keyword `payment_choice: str | None = "pay_in_full"` after `payroll_tax`.
- Before `return household`, add:

  ```python
  if payment_choice is not None:
      fee = getattr(session, "filing_fee", None) or FilingFee(session=session)
      fee.payment_choice = payment_choice
      fee.save()
  ```

- The module docstring gains: "answer_household also chooses to pay the filing fee in full (Form 101 line 8), so a forms test meets no refusal for a missing answer; payment_choice=None leaves the answer as it is."
- The function docstring gains: "payment_choice goes to the session's FilingFee, created if missing; None leaves any stored row alone."

- [ ] **Step 6: Run the tests to verify they pass**

Run: the two Step 2 commands.

Expected: PASS. The `_on_postgres` twin is SKIPPED on sqlite with its reason, and passes under `test_postgres` with the lock test.

- [ ] **Step 7: Update `CLAUDE.md`**

In "Saves lock the session" (`CLAUDE.md:27`), two sentences change. After this task they read:

- "That covers the session PATCH and PUT, `update_step`, `complete` (which writes only `status` and `completed_at`), the contracts and codebtors PUT, POST and DELETE, the filing-fee PUT (`PUT /intake/sessions/{id}/filing-fee/`, which never reopens), the `DebtViewSet`/`AssetViewSet` writes, a scanned bill's correction and an upload's findings."
- "The session PATCH's lock covers its `household`, `spouse_income` and `income_info` keys, and the lock test's `WRITES` holds the household and income PATCHes and the filing-fee PUT."

The rest of the gotcha is unchanged. "Forms need a completed intake" is Task 4's to edit (see "Decided here").

- [ ] **Step 8: Gates**

Check `uptime` first. Run the full suite only while the 1-minute load is under 10.

- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 -q -p no:cacheprovider`. Expected: the baseline totals plus the new tests, 0 failed, coverage ≥ 90%. `filing_fee.py`'s three returns are all reached.
- `/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/` (ruff 0.8.5). Expected: `All checks passed!`.
- `cd backend && $PY manage.py check`. Expected: "System check identified no issues".
- `cd backend && $PY manage.py makemigrations --check --dry-run`. Expected: "No changes detected".
- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres -q -p no:cacheprovider`. Expected: the existing `postgres` tests, the new round-trip twin and `test_every_intake_write_waits_for_a_save_in_progress[filing-fee PUT]` all PASS.
- No frontend gate: the frontend is unchanged. No journeys: the frame runs them at the end of Tasks 1, 5, 8 and 9.

- [ ] **Step 9: Commit**

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/git add backend/apps/intake/models.py backend/apps/intake/migrations/0029_filingfee.py backend/apps/intake/serializers.py backend/apps/intake/filing_fee.py backend/apps/intake/views.py backend/apps/intake/tests/builders.py backend/apps/intake/tests/test_filing_fee.py backend/apps/intake/tests/test_session_lock.py backend/apps/intake/tests/test_data_migrations.py CLAUDE.md
/usr/bin/git commit -F /tmp/3f-task3-msg.txt
```

Message (`/tmp/3f-task3-msg.txt`), with no trailer:

```
feat(intake): keep the filing-fee answers on one encrypted record

FilingFee holds Form 101 line 8 and Form 103B's lines 4, 5, 7 and 9,
each encrypted and unanswered until the filer answers. GET and PUT
/api/intake/sessions/{id}/filing-fee/ read and save it in any status:
a PUT sets only the keys it sends, refuses any other key by name,
takes the session lock and never reopens a completed intake. Both
reply with the court's 150% limit for the filer's family and the
filer's own 103B line 2 figure, as information, or say why either
can't be shown. The texts are bounded by their boxes on Form 103B.
```

---

### Task 4: The packet follows the line 8 answer

**Spec:** §7 (the packet), §8.1 (Form 101 line 8), §8.2 (103B lines 4, 5, 7, 9), §6.4 (the waiver questions), §10 (personas, seed, read-back), §12 (gotchas), §13 (tests), §16 calls 10 and 18, owner answers 2 and 3.

Line numbers are as of `dc31b7a`. Task 2 rewrites the 103B rules, schema, audit rows and unbound file before this task runs, so for those files each `path:lines` also names the block to find.

**Files:**

- Modify: `backend/apps/forms/registry.py`: `PreconditionMissing` (`:25-33`), `_has_fee_waiver` (`:51-52`, removed), `_needs_debtor_info_and_county` (`:97-99`, the new requirement beside it), `FORM_REGISTRY` (`:112-113`), and the module docstring (`:1-11`).
- Modify: `backend/apps/forms/views.py`: the `.registry` import (`:31-37`) and `packet` (`:279-308`), the docstring and the reply.
- Modify: `backend/apps/forms/services/derivations.py`: a new section after Task 2's Form 103B rules (the `# Form 103B fee waiver derivations` block, `:525-565`), its entries in `DERIVATIONS` after Task 2's 103B entries (`:859-865`, under Task 2's comment `# Form 103B lines 1-3: …`), and four `RULE_FIXES` entries under a new comment where Task 2 deleted the block `# The fee-waiver application` (`:1080-1083` at `dc31b7a`, just before `# No link.`).
- Modify: `data/forms/schemas/form_101.json`: a `Check Box7` field between `Check Box1` (`:1128-1147`) and `Check Box18` (`:1148`).
- Modify: `data/forms/schemas/form_103b.json`: `Check 4`, `4 type` and `5 Type` after `3 type` (`:149-165`); `Check 7`, `undefined_8`, `Check 9` and `undefined_10` after `undefined_7` (`:183-199`).
- Modify: `data/forms/field_index/audit/step2_verification.json`: eight rows appended.
- Modify: `data/forms/field_index/audit/form_101.unbound.json`: delete the `Check Box7` entry (`:20-28`).
- Modify: `data/forms/field_index/audit/form_103b.unbound.json`: delete the `Check 4`, `Check 7` and `Check 9` entries (`:52-69`, `:79-87` at `dc31b7a`; find them by `full_name`).
- Modify: `backend/apps/intake/management/commands/seed_demo_data.py`: the models import (`:23-36`), each persona's dict (Maria `:194-200`, James `:286-287`, Priya `:393-394`, DeShawn `:511-517`, Sarah `:594-600`, Andrés `:786-787`), and `_create_persona` after the SOFA block (`:909-918`).
- Create: `backend/apps/forms/tests/test_filing_fee_forms.py`
- Test: `backend/apps/forms/tests/test_registry.py`: the import (`:27`), `test_fee_waiver_application_adds_form_103b` (`:124-133`), `test_field_values_name_index_widgets` (`:208-214`) and `test_petition_prints_only_the_last_four_ssn_digits` (`:217-225`).
- Test: `backend/apps/forms/tests/test_form_views.py`: imports (`:46-52`), `TestGenerateEndpoint` (`:162`), `TestGenerateAllEndpoint` (`:467`), `TestPacketEndpoint` (`:801-812`), and the comments at `:302`, `:918` and `:1068`.
- Test: `backend/apps/forms/tests/test_download_action.py:305` (a comment).
- Test: `backend/apps/forms/tests/test_rule_fixes.py`: `_precondition_steps` (`:60-82`), `test_every_fix_is_a_step_or_page_the_dashboard_links` (`:117-145`), and the parameters of `test_a_rule_links_to_where_its_input_is_entered` (`:160-181`).
- Test: `backend/apps/forms/tests/test_oracle_tier2.py:37` (`ASSERTED_CASES`).
- Test: `backend/apps/forms/tests/test_oracle_tier3.py`: each persona's `form_101` in `EXPECTED` (`:99`, `:162`, `:217`, `:283`, `:344`, `:398`).
- Test: `backend/apps/forms/tests/test_printed_page.py:94-114` (`_seeded`).
- Test: `backend/apps/forms/tests/test_api_readback.py`: `APPLIES` (`:39-41`), `_send_through_the_api` after `complete/` (`:159-170`), and the test body after `assert form_types == packet(seeded)` (`:240`).
- Test: `backend/apps/intake/tests/test_seed_demo_data.py`: the import (`:24`), `test_the_seed_gives_the_fee_waiver_application_103b_line_1s_count` (`:107-124`), `test_the_new_answers_move_no_seeded_personas_means_test_fee_flag_or_packet` (`:197-212`), and two new tests.
- Modify: `frontend/src/pages/FormDashboard.tsx:59` (one `PAGE_LINK_LABELS` entry; see "Decided here").
- Modify: `frontend/e2e/journeys/deshawn-assets.spec.ts:97-99`.
- Modify: `CLAUDE.md`: "Seed order", "The packet decides which forms a filer gets", "Forms need a completed intake", "GenerateAll vs single" (one clause) and "The fee-waiver application" (two clauses).

**Interfaces:**

- Consumes:
  - Task 3: `FilingFee` (`session.filing_fee`, `PAYMENT_CHOICES`, the three yes/no fields and the four texts), the session action `PUT /api/intake/sessions/{id}/filing-fee/` (200, sets only the keys sent, never reopens), and `answer_household(..., payment_choice="pay_in_full")`. `payment_choice=None` creates no row and leaves a stored one alone (Task 3, "Decided here").
  - Task 2: the 103B lines 1–3 rules and bindings, the `form_103b` tier 3 entries, and the `ASSERTED_CASES` value it leaves.
- Produces:

  - `registry.PreconditionMissing(message: str, step: str | None = None, page: str | None = None)`. It sets `self.step` and `self.page`; its docstring says exactly one is set. `views._failure` already copies `page` (`views.py:105-110`).
  - `registry.payment_choice(session: IntakeSession) -> str | None`: the stored line 8 answer, or None with no row. It never raises: `getattr(session, "filing_fee", None)`, as `_above_median` reads `means_test` (`registry.py:61`).
  - `registry._asks_fee_waiver(session) -> bool`: `payment_choice(session) == "waiver"`.
  - `registry._needs_fee_choice(session) -> None`: raises `PreconditionMissing("Choose how you will pay the filing fee.", page="/filing-fee")` while `payment_choice(session)` is None.
  - `registry._needs_debtor_info_county_and_fee_choice(session) -> None`: `_needs_debtor_info`, `_needs_county`, then `_needs_fee_choice`. It is Form 101's `requires`, and replaces `_needs_debtor_info_and_county` (`:97-99`), whose only caller is `FORM_REGISTRY["form_101"]`.
  - `registry._needs_fee_waiver_answers(session) -> None`: Form 103B's `requires`. It checks in the form's order and raises the first gap from the table in "Decided here".
  - `FORM_REGISTRY["form_101"] = PacketForm(_always, _needs_debtor_info_county_and_fee_choice)`, `FORM_REGISTRY["form_103b"] = PacketForm(_asks_fee_waiver, _needs_fee_waiver_answers)`.
  - The rules in `DERIVATIONS`. Each returns `""` with no `FilingFee` row:
    - `fee_payment_choice`: `payment_choice or ""`.
    - `fee_waiver_income_change`, `fee_waiver_others_covered`, `fee_waiver_expense_change`: the stored `yes`/`no`, or `""`.
    - `fee_waiver_income_change_explanation`, `fee_waiver_others_covered_who`, `fee_waiver_expense_change_explanation`: the text `.strip()`ped, only while its answer is `"yes"`, else `""`.
    - `fee_waiver_installments_explanation`: the text `.strip()`ped.
  - `RULE_FIXES` gains `{"page": "/filing-fee"}` for the four text rules.
  - The bindings (all `"source": "derived"`):

    | Schema    | Box                 | Type     | Rule                                    | Choices                                                                                                      |
    | --------- | ------------------- | -------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
    | form_101  | `Check Box7` (p3)   | checkbox | `fee_payment_choice`                    | `{"pay_in_full": "/Pay entirely", "installments": "/Pay in installments", "waiver": "/Request fees waived"}` |
    | form_103b | `Check 4` (p1)      | checkbox | `fee_waiver_income_change`              | `{"no": "/no", "yes": "/yes"}`                                                                               |
    | form_103b | `4 type` (p1)       | text     | `fee_waiver_income_change_explanation`  |                                                                                                              |
    | form_103b | `5 Type` (p1)       | text     | `fee_waiver_installments_explanation`   |                                                                                                              |
    | form_103b | `Check 7` (p2)      | checkbox | `fee_waiver_others_covered`             | `{"no": "/On", "yes": "/yes"}`                                                                               |
    | form_103b | `undefined_8` (p2)  | text     | `fee_waiver_others_covered_who`         |                                                                                                              |
    | form_103b | `Check 9` (p2)      | checkbox | `fee_waiver_expense_change`             | `{"no": "/no", "yes": "/yes"}`                                                                               |
    | form_103b | `undefined_10` (p2) | text     | `fee_waiver_expense_change_explanation` |                                                                                                              |

  - The packet reply is `{"session", "form_types", "tables", "income_period", "payment_choice"}`, with `payment_choice` from `registry.payment_choice(session)`. A refused packet is unchanged and carries no `payment_choice`.
  - The seed: each persona's dict gains `"filing_fee"` (Step 7), and `_create_persona` stores it as `FilingFee.objects.create(session=session, **data["filing_fee"])`.
  - `PAGE_LINK_LABELS['/filing-fee'] = 'Go to How you will pay the filing fee'`, beside the `/fee-waiver` entry, which Task 6 removes.

- CLAUDE.md: Step 10 gives each edited sentence as it reads after this task.

**Decided here:**

- **The choice states are the decoded names.** The frame and §8.1 write `/Pay#20entirely` and the rest, which is the index's raw `on_state` with a slash. Schemas hold the export state `export_state()` makes (`apps/forms/field_index.py:23-30` turns `#20` into a space): `Check Box1` is `"/Chapter 7"` (`form_101.json:1133`) and `Check Box21` is `"/More than 100000"`. So `Check Box7`'s choices are `/Pay entirely`, `/Pay in installments` and `/Request fees waived`, which is what forms.E004 matches and tier 3 reads back. The `#20` spellings would fail `manage.py check`.
- **`PAGE_LINK_LABELS` gains `/filing-fee` here, not in Task 6.** `test_every_fix_is_a_step_or_page_the_dashboard_links` (`test_rule_fixes.py:117-145`) checks every `RULE_FIXES` page against `PAGE_LINK_LABELS`, which it reads from `FormDashboard.tsx:57-62`. Without the entry, this task's four `{"page": "/filing-fee"}` entries go red. Without it the dashboard would also drop the link from every refusal this task adds. This task adds the one line (ruling R12). Task 6 then deletes the `/fee-waiver` line instead of replacing it, and its own failing tests need another reason to fail first. So the frontend gates run in this task.
- **The checkbox rules have no `RULE_FIXES` entry.** The map's comment (`derivations.py:932-936`) and its test (`test_rule_fixes.py:104-114`) cover rules bound to a text or choice box only. `creditor_count_range` and `fee_waiver_noncash_assistance` have none today, since a box's refusal (`UnmappedChoice`) carries no fix. The frame's "Their `RULE_FIXES` are `/filing-fee`" therefore holds for the four text rules.
- **Each `PreconditionMissing` raise names its page as a literal** (`page="/filing-fee"`), never a module constant. `_precondition_steps` (`test_rule_fixes.py:60-82`) reads each call's arguments from the source, and a name it can't read fails its `unread == []`. This task extends it to read `page=` as well, so the dashboard test also checks a precondition's page (Step 1).
- **103B's refusal sentences.** They are checked in the form's order, and only the first gap is raised. A waiver filer with no `FilingFee` row can't reach this (103B wouldn't apply), but if one did, the first row below would be raised.

  | Gap                                        | Sentence                                                                                                 |
  | ------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
  | line 4 unanswered                          | "Answer whether you expect your family's income to go up or down by more than 10% in the next 6 months." |
  | line 4 Yes, explanation blank once trimmed | "Explain how you expect your family's income to change."                                                 |
  | line 5 blank once trimmed                  | "Tell the court why you can't pay the filing fee in installments."                                       |
  | line 7 unanswered                          | "Answer whether your expenses cover anyone not counted in your family."                                  |
  | line 7 Yes, who blank once trimmed         | "Say who else your expenses cover."                                                                      |
  | line 9 unanswered                          | "Answer whether you expect your expenses to go up or down by more than 10% in the next 6 months."        |
  | line 9 Yes, explanation blank once trimmed | "Explain how you expect your expenses to change."                                                        |

- **The refusal sentences live in `registry.py`, not `copy.ts`.** §11 lists "the 101 refusal" with `copy.ts`. But the server raises it, and the dashboard shows the server's `error` text, as it does every `PreconditionMissing` sentence (`registry.py:72-107`). `reading-level.test.ts` scores only `copy.ts` and `upl.ts` (`:9-10`). The sentences use the plain words the existing preconditions use.
- **An explanation prints only under Yes.** The page keeps a typed explanation stored when the filer switches to No (§4: the waiver answers stay stored). A sworn "No" beside an explanation would contradict itself, so the three explanation rules print only while their answer is `yes`, as 3e2's 8f kinds print only under Yes. Line 5 has no Yes/No and prints whenever stored. Every text prints `.strip()`ped.
- **The rules read the stored answers whatever line 8 says.** 103B is in the packet only under `waiver`, and a filed 103B keeps the values it was filed with (DIG-155). A rule that also checked line 8 would add nothing.
- **The seed drops DeShawn's `fee_waiver` dict.** He pays in installments, so, like Andrés (`:786`), he no longer applies. That makes the read-back's `APPLIES`, the line 8 waiver filers, match the seeded applications. The branch that creates applications (`:924-936`) stays, for Task 7 (its `qualifies_for_fee_waiver` read) and Task 8 (the model). The seed test of 103B line 1's count now expects Maria 3 and Sarah 1.
- **The read-back PUTs every persona's `filing_fee` after `complete/`.** The API-built session would otherwise have no line 8 answer. Its Generate All would then carry a Form 101 error, failing `errors == []`, for all six personas. The body is the seed's own dict, so both sides store the same answers.
- **`test_printed_page.py`'s `_seeded` builds a form outside a persona's packet only when its `requires()` lets it.** It builds every form for every persona (`:106-112`), and 103B's `requires()` now refuses the four non-waiver personas. `_values()` still finds 122A-1Supp (in no packet, `requires` `_nothing`) on the first persona.
- **Tier 3:** Task 2 gives only Maria and Sarah a `form_103b` entry in `EXPECTED` (its "Decided here"), because `_printed` (`test_oracle_tier3.py:478`) calls `build_field_values` for every form in `EXPECTED`, and 103B's `requires()` now refuses the other four. This task adds no 103B entry.
- **The read-back keeps the name `APPLIES`.** §10 renames `QUALIFIES` and `APPLIES` to `WAIVER_CHOICE`. Task 7 deletes `QUALIFIES` and Task 8 reads `APPLIES` by name (rulings R15, R20), so this task changes only its value and comment: `{"maria", "sarah"}`, the line 8 waiver filers.
- **CLAUDE.md, beyond the frame's two gotchas.** This task changes the packet reply ("GenerateAll vs single", ruling R13), the seed ("Seed order") and two sentences of "The fee-waiver application" that become false: "an application puts 103B in the packet" and "`4 type` and `5 Type` are unbound". It edits only those clauses; Task 6 adds the dashboard's use of `payment_choice` and Task 8 rewrites the fee-waiver gotcha. "Seed order" gains only the `FilingFee` sentence: its fee-waiver clause and the "Personas seeded before 3f …" sentence are Task 8's (ruling R27).
- **The never-reopen list keeps the fee-waiver application** beside the filing fee until Task 8 removes the model. The frame's "in place of" lands in Task 8.

- [ ] **Step 1: Write the failing tests**

`backend/apps/forms/tests/test_filing_fee_forms.py`. Its docstring gives the intent: Form 101 line 8 is the filer's own answer, so 103B is in the packet exactly when they ask for the waiver, and nothing routes on a computed result (3f spec §7, U:375–381). A petition with no answer, or a waiver application with a question unanswered, is refused with a link to the page that asks it, never filled with a guess (§4, §7).

```python
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.districts.models import District
from apps.eligibility.models import MeansTest
from apps.forms.registry import PreconditionMissing, build_field_values, packet
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import resolve
from apps.forms.services.pdf_filler import PDFFormFiller
from apps.intake.models import DebtorInfo, FilingFee, IncomeInfo, IntakeSession
from apps.intake.tests.builders import answer_household

User = get_user_model()

PAGE = "/filing-fee"
CHOOSE = "Choose how you will pay the filing fee."
MARIA_LINE_5 = (
    "I support two children on what I earn. After rent, food, the car and the children's "
    "costs, there is not enough left each month to pay the fee, even in parts."
)
WAIVER = {
    "income_change_answer": "no",
    "installments_explanation": MARIA_LINE_5,
    "others_covered_answer": "no",
    "expense_change_answer": "no",
}
LINES_4_TO_9 = ("Check 4", "4 type", "5 Type", "Check 7", "undefined_8", "Check 9", "undefined_10")


@pytest.fixture
def session(db):
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ilnd",
        name="Northern District of Illinois",
        court_name="U.S. Bankruptcy Court, N.D. Ill.",
        state="IL",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user=user, district=district)
    DebtorInfo.objects.create(
        session=session, first_name="Sarah", last_name="Chen", ssn="900-55-0005",
        date_of_birth=date(1995, 1, 20), street_address="1520 N Damen Ave Apt 2F",
        city="Chicago", state="IL", zip_code="60622",
    )
    IncomeInfo.objects.create(
        session=session, marital_status="not_married", monthly_gross_wages=Decimal("2000.00")
    )
    answer_household(session, payroll_tax=Decimal("250.00"), payment_choice=None)  # no line 8 yet
    return session


def _line_8(session, payment_choice, **answers):
    """Store the filer's filing-fee answers, and return the session read afresh (no cached row)."""
    FilingFee.objects.update_or_create(
        session=session, defaults={"payment_choice": payment_choice, **answers}
    )
    return IntakeSession.objects.get(pk=session.pk)


# ── The packet ────────────────────────────────────────────────────────


def test_103b_is_in_the_packet_exactly_when_the_filer_asks_for_the_waiver(session):
    # No record yet, then each answer in turn: asking, moving off, and asking again.
    held = ["form_103b" in packet(session)]
    for choice in (None, "installments", "waiver", "pay_in_full", "waiver"):
        held.append("form_103b" in packet(_line_8(session, choice)))
    assert held == [False, False, False, True, False, True]


def test_a_waiver_filer_above_the_median_still_gets_103b(session):
    # The filer chooses; the packet never second-guesses the choice on a computed figure.
    MeansTest.objects.create(
        session=session, district=session.district, calculated_cmi=Decimal("12000.00"),
        median_income_threshold=Decimal("134366.00"), passes_means_test=False,
    )
    forms = packet(_line_8(session, "waiver", **WAIVER))
    assert {"form_103b", "form_122a2"} <= set(forms)


# ── Form 101 line 8 ───────────────────────────────────────────────────


@pytest.mark.parametrize("stored", [False, True], ids=["no_row", "row_with_no_answer"])
def test_the_petition_is_refused_until_the_filer_chooses_how_to_pay_the_fee(session, stored):
    if stored:
        session = _line_8(session, None)
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_101", session)
    assert (str(refused.value), refused.value.step, refused.value.page) == (CHOOSE, None, PAGE)


def test_the_petition_names_a_missing_county_before_the_fee(session):
    # A guard (ruling R29): it passes before Step 3, and fails if the fee check runs first.
    household = session.household
    household.county = None
    household.save()
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_101", session)
    assert (str(refused.value), refused.value.step, refused.value.page) == (
        "Choose your county on the Your Information step.", "debtor_info", None
    )


@pytest.mark.parametrize(
    "choice,state",
    [
        ("pay_in_full", "/Pay entirely"),
        ("installments", "/Pay in installments"),
        ("waiver", "/Request fees waived"),
    ],
)
def test_the_petition_ticks_only_the_filers_own_way_to_pay_the_fee(session, choice, state):
    values = build_field_values("form_101", _line_8(session, choice, **WAIVER))
    assert values["Check Box7"] == state
    PDFFormFiller().check("form_101", values)  # the state is one of the box's own


# ── Form 103B's own questions ─────────────────────────────────────────


@pytest.mark.parametrize(
    "answers,sentence",
    [
        ({"income_change_answer": None},
         "Answer whether you expect your family's income to go up or down by more than 10% in the next 6 months."),
        ({"income_change_answer": "yes", "income_change_explanation": ""},
         "Explain how you expect your family's income to change."),
        ({"income_change_answer": "yes", "income_change_explanation": "  \n "},
         "Explain how you expect your family's income to change."),
        ({"installments_explanation": "   "},  # line 5 typed as only spaces
         "Tell the court why you can't pay the filing fee in installments."),
        ({"installments_explanation": " \t\n"},
         "Tell the court why you can't pay the filing fee in installments."),
        ({"others_covered_answer": None},
         "Answer whether your expenses cover anyone not counted in your family."),
        ({"others_covered_answer": "yes", "others_covered_who": ""},
         "Say who else your expenses cover."),
        ({"expense_change_answer": None},
         "Answer whether you expect your expenses to go up or down by more than 10% in the next 6 months."),
        ({"expense_change_answer": "yes", "expense_change_explanation": " "},
         "Explain how you expect your expenses to change."),
    ],
)
def test_103b_is_refused_with_a_link_to_the_filing_fee_page_until_each_question_is_answered(
    session, answers, sentence
):
    session = _line_8(session, "waiver", **{**WAIVER, **answers})
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_103b", session)
    assert (str(refused.value), refused.value.step, refused.value.page) == (sentence, None, PAGE)


def test_103b_names_the_first_unanswered_line_in_the_forms_order(session):
    with pytest.raises(PreconditionMissing) as refused:
        build_field_values("form_103b", _line_8(session, "waiver"))
    assert str(refused.value).startswith("Answer whether you expect your family's income")


def test_103b_prints_a_waiver_filers_own_answers_to_lines_4_5_7_and_9(session):
    values = build_field_values("form_103b", _line_8(session, "waiver", **WAIVER))
    assert {box: values.get(box) for box in LINES_4_TO_9} == {
        "Check 4": "/no", "4 type": None, "5 Type": MARIA_LINE_5,
        "Check 7": "/On",  # the template's No box exports On (field index, Check 7 T4)
        "undefined_8": None, "Check 9": "/no", "undefined_10": None,
    }
    PDFFormFiller().check("form_103b", values)  # Maria's line 5 fits its box


YESES = {
    "income_change_answer": "yes", "income_change_explanation": "My hours are being cut in March.",
    "others_covered_answer": "yes", "others_covered_who": "My mother, who lives with her sister.",
    "expense_change_answer": "yes", "expense_change_explanation": "My rent goes up $200 in June.",
}
EXPLANATIONS = ("4 type", "undefined_8", "undefined_10")


def test_each_yes_prints_with_what_the_filer_wrote_beside_it(session):
    values = build_field_values("form_103b", _line_8(session, "waiver", **{**WAIVER, **YESES}))
    assert {box: values.get(box) for box in LINES_4_TO_9} == {
        "Check 4": "/yes", "4 type": "My hours are being cut in March.", "5 Type": MARIA_LINE_5,
        "Check 7": "/yes", "undefined_8": "My mother, who lives with her sister.",
        "Check 9": "/yes", "undefined_10": "My rent goes up $200 in June.",
    }


def test_an_explanation_kept_after_the_answer_changes_to_no_does_not_print(session):
    yes = build_field_values("form_103b", _line_8(session, "waiver", **{**WAIVER, **YESES}))
    assert all(yes.get(box) for box in EXPLANATIONS)
    # The page keeps the texts stored when each answer moves to No (spec §4).
    no = {"income_change_answer": "no", "others_covered_answer": "no", "expense_change_answer": "no"}
    values = build_field_values("form_103b", _line_8(session, "waiver", **{**WAIVER, **YESES, **no}))
    assert (values["Check 4"], values["Check 7"], values["Check 9"]) == ("/no", "/On", "/no")
    assert [values.get(box) for box in EXPLANATIONS] == [None] * 3
    stored = FilingFee.objects.get(session=session)
    assert (
        stored.income_change_explanation, stored.others_covered_who,
        stored.expense_change_explanation,
    ) == (YESES["income_change_explanation"], YESES["others_covered_who"],
          YESES["expense_change_explanation"])  # still stored, only not printed


def test_line_5_prints_without_the_spaces_around_it(session):
    session = _line_8(session, "waiver", **{**WAIVER, "installments_explanation": "  I have no savings.\n"})
    assert build_field_values("form_103b", session)["5 Type"] == "I have no savings."


def test_an_unanswered_waiver_question_ticks_no_box(session):
    # resolve() alone, without 103B's requires(): only line 5 is answered, and no other
    # answer is guessed onto the page.
    session = _line_8(session, "waiver", installments_explanation="I have no savings.")
    values = resolve(load_schema("form_103b"), session)
    assert [box for box in LINES_4_TO_9 if box in values] == ["5 Type"]
```

`test_registry.py`:

- The import (`:27`) becomes `from apps.intake.models import DebtorInfo, FeeWaiverApplication, FilingFee, Household, IntakeSession`.
- `test_fee_waiver_application_adds_form_103b` (`:124-133`) becomes `test_a_fee_waiver_application_without_the_line_8_answer_adds_no_103b`. The body creates the same application, then asserts `"form_103b" not in packet(session)`. Task 8 deletes the test with the model.
- `test_field_values_name_index_widgets` and `test_petition_prints_only_the_last_four_ssn_digits` each gain `FilingFee.objects.create(session=session, payment_choice="pay_in_full")` after the `Household` line.

`test_form_views.py`. Add `FilingFee` to the `apps.intake.models` import, and beside `FILED`:

```python
WAIVER = {
    "payment_choice": "waiver",
    "income_change_answer": "no",
    "installments_explanation": "I have no savings.",
    "others_covered_answer": "no",
    "expense_change_answer": "no",
}


def _filing_fee(api_client, session, body):
    """Save on the filing-fee page, as the filer does after Complete (it never reopens)."""
    resp = api_client.put(f"/api/intake/sessions/{session.id}/filing-fee/", body, format="json")
    assert resp.status_code == status.HTTP_200_OK, resp.data
```

In `TestGenerateEndpoint`:

```python
def test_a_petition_without_the_line_8_answer_links_to_the_filing_fee_page(
    self, api_client, session_with_debtor
):
    FilingFee.objects.filter(session=session_with_debtor).delete()
    resp = api_client.post(
        self.URL, {"session_id": session_with_debtor.id, "form_type": "form_101"}, format="json"
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.data == {
        "form_type": "form_101",
        "error": "Choose how you will pay the filing fee.",
        "page": "/filing-fee",
    }

def test_a_waiver_question_left_unanswered_links_103b_to_the_filing_fee_page(
    self, api_client, session_with_debtor
):
    _filing_fee(api_client, session_with_debtor, {**WAIVER, "others_covered_answer": None})
    resp = api_client.post(
        self.URL, {"session_id": session_with_debtor.id, "form_type": "form_103b"}, format="json"
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.data == {
        "form_type": "form_103b",
        "error": "Answer whether your expenses cover anyone not counted in your family.",
        "page": "/filing-fee",
    }

def test_line_5_typed_as_only_spaces_links_103b_to_the_filing_fee_page(
    self, api_client, session_with_debtor
):
    _filing_fee(api_client, session_with_debtor, {**WAIVER, "installments_explanation": "     "})
    resp = api_client.post(
        self.URL, {"session_id": session_with_debtor.id, "form_type": "form_103b"}, format="json"
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert resp.data == {
        "form_type": "form_103b",
        "error": "Tell the court why you can't pay the filing fee in installments.",
        "page": "/filing-fee",
    }

def test_line_4_moved_back_to_no_keeps_its_explanation_off_103b(
    self, api_client, session_with_debtor
):
    session = session_with_debtor
    why = "My hours are being cut in March."
    _filing_fee(api_client, session, {**WAIVER, "income_change_answer": "yes",
                                      "income_change_explanation": why})
    _filing_fee(api_client, session, {"income_change_answer": "no"})  # the page sends only No
    resp = api_client.post(
        self.URL, {"session_id": session.id, "form_type": "form_103b"}, format="json"
    )
    assert resp.status_code == status.HTTP_200_OK, resp.data
    (part,) = json.loads(
        GeneratedForm.objects.get(session=session, form_type="form_103b").field_values
    )["parts"]
    assert (part["values"]["Check 4"], "4 type" in part["values"]) == ("/no", False)
    assert FilingFee.objects.get(session=session).income_change_explanation == why
```

In `TestGenerateAllEndpoint`:

```python
def test_a_petition_without_the_line_8_answer_is_named_with_its_page(
    self, api_client, session_with_debtor
):
    FilingFee.objects.filter(session=session_with_debtor).delete()
    resp = api_client.post(self.URL, {"session_id": session_with_debtor.id}, format="json")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["errors"] == [
        {"form_type": "form_101", "error": "Choose how you will pay the filing fee.", "page": "/filing-fee"}
    ]
    assert resp.data["total_generated"] == 13

def test_moving_off_the_waiver_withdraws_an_unfiled_103b_and_moving_back_brings_its_answers_back(
    self, api_client, session_with_debtor
):
    session = session_with_debtor
    _filing_fee(api_client, session, WAIVER)
    first = api_client.post(self.URL, {"session_id": session.id}, format="json")
    assert first.data["errors"] == []
    assert "form_103b" in [f["form_type"] for f in first.data["generated"]]

    _filing_fee(api_client, session, {"payment_choice": "installments"})
    api_client.post(self.URL, {"session_id": session.id}, format="json")
    assert not GeneratedForm.objects.filter(session=session, form_type="form_103b").exists()

    _filing_fee(api_client, session, {"payment_choice": "waiver"})  # only line 8 sent
    again = api_client.post(self.URL, {"session_id": session.id}, format="json")
    assert again.data["errors"] == []
    application = GeneratedForm.objects.get(session=session, form_type="form_103b")
    (part,) = json.loads(application.field_values)["parts"]
    assert (part["values"]["Check 4"], part["values"]["5 Type"]) == ("/no", "I have no savings.")

def test_a_filed_103b_stays_when_the_filer_moves_off_the_waiver(
    self, api_client, session_with_debtor, user
):
    session = session_with_debtor
    _filing_fee(api_client, session, WAIVER)
    listed = api_client.get("/api/forms/packet/", {"session": session.id})
    assert "form_103b" in listed.data["form_types"]  # the waiver put it in the packet
    filed = _filed_form(session, user, "form_103b", {"5 Type": "I have no savings."})
    _filing_fee(api_client, session, {"payment_choice": "pay_in_full"})
    resp = api_client.post(self.URL, {"session_id": session.id}, format="json")
    returned = [f for f in resp.data["generated"] if f["form_type"] == "form_103b"]
    assert [(f["id"], f["status"]) for f in returned] == [(filed.id, "filed")]
```

In `TestPacketEndpoint`:

- `test_lists_the_filers_forms_in_filing_order` (`:809`) asserts `set(resp.data) == {"session", "form_types", "tables", "income_period", "payment_choice"}`.
- New:

```python
@pytest.mark.parametrize("answer", ["pay_in_full", "installments", "waiver", None])
def test_the_packet_carries_the_filers_line_8_answer(self, api_client, session_with_debtor, answer):
    fee = FilingFee.objects.get(session=session_with_debtor)  # answer_household's pay-in-full row
    fee.payment_choice = answer
    fee.save()
    resp = api_client.get(self.URL, {"session": session_with_debtor.id})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["payment_choice"] == answer
    assert ("form_103b" in resp.data["form_types"]) is (answer == "waiver")

def test_a_filer_with_no_filing_fee_record_is_shown_no_answer(self, api_client, session_with_debtor):
    FilingFee.objects.filter(session=session_with_debtor).delete()
    resp = api_client.get(self.URL, {"session": session_with_debtor.id})
    assert resp.data["payment_choice"] is None
```

The refusal half needs no new test: `test_a_completed_intake_with_an_open_gap_gets_the_refusal_not_the_notice` (`:886-893`) already asserts the whole 422 body, so a `payment_choice` on a refusal fails it.

The comments, which the line 8 answer makes wrong:

- `test_form_views.py:302` becomes `# Line 8 is pay in full, so Form 103B is outside the packet.`
- `:918` becomes `# Line 8 is pay in full, so 103B has left the packet; 101 is in it, unfiled.`
- `:1068` becomes `# Line 8 is pay in full, so 103B has left the packet. 106B-Dec reads no income.`
- `test_download_action.py:305` becomes `# line 8 is pay in full for this session`.

`test_rule_fixes.py`:

- `_precondition_steps` becomes `_precondition_fixes`, and its docstring says "The step or page each call of PreconditionMissing ... names, as a fix". For each call it reads `step` (keyword, or the second positional argument) and `page` (keyword, or the third), appends `{"step": value}` or `{"page": value}` for an `ast.Constant`, and records anything else in `unread`. It returns the list.
- In `test_every_fix_is_a_step_or_page_the_dashboard_links`, `preconditions = _precondition_fixes()`, then `assert {"page": "/filing-fee"} in preconditions  # line 8 and 103B's own questions`. The `fixes` list takes `*preconditions` in place of `*({"step": step} for step in preconditions)`.
- `test_a_rule_links_to_where_its_input_is_entered` gains `("fee_waiver_installments_explanation", {"page": "/filing-fee"})` and `("fee_waiver_others_covered_who", {"page": "/filing-fee"})`.

`test_oracle_tier2.py:37`: `ASSERTED_CASES` goes from Task 2's 480 to **488**. That is one case for each new binding (`_cases()` yields one per schema field whose (box, key) has a checked row), each joined to its own addendum row: `Check Box7`, then `Check 4`, `4 type`, `5 Type`, `Check 7`, `undefined_8`, `Check 9` and `undefined_10`. The comment beside it gains `; + 101 line 8 and 103B lines 4, 5, 7 and 9 (3f Task 4): eight new pairs`.

`test_oracle_tier3.py`, `EXPECTED`. Each persona's `form_101` gains `Check Box7`, the 101 line 8 answer §10 fixes:

- Maria: `{**_common("Maria", ...), "Check Box7": "/Request fees waived"}`, and likewise for Sarah.
- DeShawn: `"/Pay in installments"`.
- Andrés: `{"Debtor1.County": "Kane", "Check Box7": "/Pay in installments"}`.
- James and Priya: `"/Pay entirely"`.

That makes six new tier 3 cases, and the "Decided here" note on Task 2's 103B entries applies.

`test_printed_page.py` `_seeded` (`:106-112`, the `seeded[persona] = (...)` statement):

```python
        forms = packet(session)
        values = {}
        for form_type in get_all_form_types():
            try:
                values[form_type] = build_field_values(form_type, session)
            except PreconditionMissing:
                if form_type in forms:
                    raise
                # 103B outside the packet: its own questions are asked only of a waiver filer
        seeded[persona] = (forms, values)
```

The import gains `PreconditionMissing` from `apps.forms.registry`.

`test_api_readback.py`:

- `:39-41`:

```python
# These ask for the fee waiver on Form 101 line 8 (3f spec §10), so 103B is in their packets,
# and the seed gives them a fee-waiver application, which the page still accepts until it goes.
APPLIES = {"maria", "sarah"}
```

- In `_send_through_the_api`, after the `complete/` assertions (`:160-163`) and before the `APPLIES` POST:

```python
    # The filing-fee page every filer passes after Complete: Form 101 line 8, and 103B's own
    # questions for a waiver filer. It never reopens the intake.
    response = client.put(f"{session_url}filing-fee/", _sent(data["filing_fee"]), format="json")
    assert response.status_code == 200, response.data
```

- In the test, after `assert form_types == packet(seeded)`: `assert ("form_103b" in form_types) is (persona in APPLIES)`.

`test_seed_demo_data.py`:

- The import (`:24`) gains `FilingFee`.
- `test_the_seed_gives_the_fee_waiver_application_103b_line_1s_count`: the expected dict is `{"demo_maria": 3, "demo_sarah": 1}`. A comment above it reads `# DeShawn pays in installments, so he no longer applies (3f spec §10).`
- `test_the_new_answers_move_no_seeded_personas_means_test_fee_flag_or_packet`: its last line becomes `assert ("form_103b" in forms) is (persona in {"maria", "sarah"})`. The `qualifies_for_fee_waiver` assertion stays for Task 7.
- New:

```python
MARIA_LINE_5 = (
    "I support two children on what I earn. After rent, food, the car and the children's "
    "costs, there is not enough left each month to pay the fee, even in parts."
)
SARAH_LINE_5 = (
    "I have no savings. My pay covers rent, food and my bus pass, and what is left each "
    "month goes to bills I already owe."
)
LINE_8 = {"maria": "waiver", "sarah": "waiver", "deshawn": "installments",
          "andres": "installments", "james": "pay_in_full", "priya": "pay_in_full"}
PACKET_SIZE = {"maria": 15, "sarah": 15, "deshawn": 14, "andres": 14, "james": 14, "priya": 15}


@pytest.mark.django_db
@pytest.mark.parametrize("persona", list(LINE_8))
def test_each_persona_is_seeded_with_their_own_answer_to_how_they_will_pay_the_fee(persona):
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    call_command("seed_demo_data", persona=persona, stdout=StringIO())
    fee = FilingFee.objects.get(session__user__username=f"demo_{persona}")
    line_5 = {"maria": MARIA_LINE_5, "sarah": SARAH_LINE_5}.get(persona)
    waiver = ("no", line_5, "no", "no") if line_5 else (None, "", None, None)
    assert (
        fee.payment_choice, fee.income_change_answer, fee.installments_explanation,
        fee.others_covered_answer, fee.expense_change_answer,
    ) == (LINE_8[persona], *waiver)
    assert (fee.income_change_explanation, fee.others_covered_who,
            fee.expense_change_explanation) == ("", "", "")


@pytest.mark.django_db
def test_103b_follows_each_personas_line_8_answer_so_only_deshawns_packet_shrinks():
    # One test over all six, so it fails first on DeShawn's 15 (a test per persona would
    # pass before the change for the five whose packets don't move).
    call_command("loaddata", "ilnd_2025_data", verbosity=0)
    packets = {}
    for persona in PACKET_SIZE:
        call_command("seed_demo_data", persona=persona, stdout=StringIO())
        forms = packet(IntakeSession.objects.get(user__username=f"demo_{persona}"))
        packets[persona] = (len(forms), "form_103b" in forms)
    assert packets == {
        persona: (size, LINE_8[persona] == "waiver") for persona, size in PACKET_SIZE.items()
    }
```

- [ ] **Step 2: Run the tests to verify they fail**

Check `uptime` first (the 1-minute load must be under 10).

Run: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest apps/forms/tests/test_filing_fee_forms.py apps/forms/tests/test_registry.py apps/forms/tests/test_form_views.py apps/forms/tests/test_rule_fixes.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_printed_page.py apps/forms/tests/test_api_readback.py apps/intake/tests/test_seed_demo_data.py -q -p no:cacheprovider`

Expected: FAIL.

- **The packet.** `_has_fee_waiver` reads the application, so `waiver` adds no 103B and the old application still does.
- **The refusals.** `build_field_values("form_101")` raises nothing, so `DID NOT RAISE`. 103B's `requires` is `_nothing`.
- **Line 8 and 103B lines 4–9.** `KeyError: 'Check Box7'`, and lines 4–9 print nothing.
- **The packet reply.** It has no `payment_choice` key, and the set of keys differs.
- **`test_rule_fixes`.** `{"page": "/filing-fee"} in preconditions` is false, and `KeyError: 'fee_waiver_installments_explanation'`.
- **Tier 2.** The coverage count is off by 8.
- **Tier 3.** `Check Box7` ticks `[]`.
- **The read-back.** `KeyError: 'filing_fee'`.
- **The seed.** `FilingFee.DoesNotExist`, and DeShawn's packet is 15.
- **The two view tests of review focus.** Line 5 typed as spaces (the PUT trims it to `""`) and line 4 moved back to No: 103B is outside the packet before Step 3, so each Generate is the "not in your packet" 422, not the body asserted.
- **`test_printed_page`.** It still passes here; it guards Step 3, when 103B's `requires()` starts refusing non-waiver personas.

Every new test fails for a reason above, with two labelled guards that pass before (ruling R29): `test_printed_page`'s `_seeded` and `test_the_petition_names_a_missing_county_before_the_fee`, each beside tests of its own file that fail first.

- [ ] **Step 3: The registry**

- `PreconditionMissing.__init__(self, message: str, step: str | None = None, page: str | None = None)`. The docstring gains: "page is the route (such as /filing-fee) where the filer fixes it, or None. Exactly one of step and page is set."
- Delete `_has_fee_waiver` and `_needs_debtor_info_and_county`. Add `payment_choice`, `_asks_fee_waiver`, `_needs_fee_choice`, `_needs_debtor_info_county_and_fee_choice` and `_needs_fee_waiver_answers`, as in Interfaces.
- `_needs_fee_waiver_answers` reads `fee = getattr(session, "filing_fee", None)` and a local `blank(text)` that is `not (text or "").strip()`. It then raises the first row of the "Decided here" table that holds, in that order, each raise written as `raise PreconditionMissing("<sentence>", page="/filing-fee")`.
- `FORM_REGISTRY` lines `:112-113` as in Interfaces.
- The module docstring's second paragraph gains: "Form 101 and 103B also need the filer's answers on the filing-fee page (forms step 3f spec §7): line 8, and for a waiver 103B lines 4, 5, 7 and 9."

- [ ] **Step 4: The rules, `RULE_FIXES` and the packet reply**

- In `derivations.py`, a section headed `# Form 101 line 8 and Form 103B lines 4–9: the filing-fee page's answers`, with:
  - `_filing_fee(session)` returning `getattr(session, "filing_fee", None)`;
  - `_fee_answer(name: str) -> Callable[[IntakeSession], str]`, which returns the stored value or `""`;
  - `_fee_text(name: str, under: str | None = None) -> Callable[[IntakeSession], str]`, which returns the text stripped, or `""` when `under` names a yes/no field whose value isn't `"yes"`.
  - The nine `DERIVATIONS` entries are built from those helpers: `"fee_payment_choice": _fee_answer("payment_choice")`, `"fee_waiver_income_change_explanation": _fee_text("income_change_explanation", under="income_change_answer")`, `"fee_waiver_installments_explanation": _fee_text("installments_explanation")`, and so on, under the comment `# Form 101 line 8 and 103B lines 4, 5, 7 and 9 (3f spec §8)`.
- `RULE_FIXES` gains a block where Task 2 deleted `# The fee-waiver application` (just before `# No link.`), under `# The filing-fee page (3f spec §7)`: the four text rules, each `{"page": "/filing-fee"}`. The three checkbox rules and `fee_payment_choice` get none (ruling R8).
- `views.py`: import `payment_choice` from `.registry` and add `"payment_choice": payment_choice(session)` to the reply. The docstring gains: "`payment_choice` is the Form 101 line 8 answer, or null before the filer chooses."

- [ ] **Step 5: The bindings**

Each new field copies the key order of its neighbours (`form_103b.json:128-165`):

```json
{
  "pdf_field": "Check 4",
  "type": "checkbox",
  "source": "derived",
  "choices": { "no": "/no", "yes": "/yes" },
  "page": 1,
  "label": "Do you expect your family’s average monthly net income to increase or decrease by more than 10% during the next 6 months?",
  "required": false,
  "conditional_on": null,
  "value": null,
  "rule": "fee_waiver_income_change",
  "ingest_key": null,
  "binding": null,
  "repeat": null,
  "repeat_capacity": null,
  "row": null,
  "legal_review": false
}
```

The schema's `label` is free text, not checked against the index (`3 type` says "Type of assistance"). The checkboxes take the index's `label` word for word; the text boxes take the index's label without its bracketed note. The text boxes have no `choices` key, as `3 type` has none (`:149-165`):

- `Check 7` → "Do these expenses cover anyone who is not included in your family as reported in line 1?" (page 2);
- `Check 9` → "Do you expect your average monthly expenses to increase or decrease by more than 10% during the next 6 months?" (page 2);
- `4 type` → "Line 4 Yes. Explain.";
- `5 Type` → "Line 5: Tell the court why you are unable to pay the filing fee in installments within 120 days";
- `undefined_8` → "Identify who" (page 2);
- `undefined_10` → "Line 9 Yes. Explain" (page 2).

A refusal names the box by these labels. `Check Box7` uses page 3, with label "How you will pay the fee".

- [ ] **Step 6: The audit rows and the unbound files**

Append eight rows to `step2_verification.json`. Each has the shape `{"schema", "pdf_field", "producer": "derived:<rule>", "original_verdicts": [], "final_verdicts": ["correct"], "status": "confirmed", "correct_target": <pdf_field>, "evidence"}`. Each evidence string names the box's index row, as the existing 103B rows do (`check 3`'s, for example):

| Box                   | Producer                                        | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| --------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| form_101 `Check Box7` | `derived:fee_payment_choice`                    | "Field index: Check Box7 p3 line 8 'How you will pay the fee', states /Pay entirely ('I will pay the entire fee when I file my petition.', sampled_ok), /Pay in installments ('I need to pay the fee in installments.', vision_agreed) and /Request fees waived ('I request that my fee be waived', sampled_ok). 3f spec §8.1 and §6.1: line 8 ticks the filer's own answer, FilingFee.payment_choice; blank while unanswered, when Form 101's requires() refuses the form." |
| `Check 4`             | `derived:fee_waiver_income_change`              | "Field index: Check 4 p1 line 4 'Do you expect your family’s average monthly net income to increase or decrease by more than 10% during the next 6 months?', states /no ('No') and /yes ('Yes. Explain.'), sampled_ok. 3f spec §6.4 and §8.2 (owner answer 2): asked on the filing-fee page under the waiver choice, FilingFee.income_change_answer; blank until answered."                                                                                                  |
| `4 type`              | `derived:fee_waiver_income_change_explanation`  | "Field index: 4 type p1 line 4 'Line 4 Yes. Explain. (explanation of expected >10% income change)' (adjudicated; its tooltip 'type of assistance' is a template copy-paste error). 3f spec §6.4 and §8.2: line 4's explanation, printed only beside a Yes."                                                                                                                                                                                                                  |
| `5 Type`              | `derived:fee_waiver_installments_explanation`   | "Field index: 5 Type p1 line 5 'Line 5: Tell the court why you are unable to pay the filing fee in installments within 120 days (explanation)' (adjudicated; its tooltip 'Type of assistance' is a template copy-paste error). 3f spec §6.4 and §8.2: line 5 in the filer's own words, FilingFee.installments_explanation."                                                                                                                                                  |
| `Check 7`             | `derived:fee_waiver_others_covered`             | "Field index: Check 7 p2 line 7 'Do these expenses cover anyone who is not included in your family as reported in line 1?', states /On ('No'; the template's No box exports On, FW:36) and /yes ('Yes. Identify who'), sampled_ok. 3f spec §6.4 and §8.2: FilingFee.others_covered_answer; blank until answered."                                                                                                                                                            |
| `undefined_8`         | `derived:fee_waiver_others_covered_who`         | "Field index: undefined_8 p2 line 7 'Identify who' (sampled_ok). 3f spec §6.4 and §8.2: whom line 7's expenses also cover, printed only beside a Yes."                                                                                                                                                                                                                                                                                                                       |
| `Check 9`             | `derived:fee_waiver_expense_change`             | "Field index: Check 9 p2 line 9 'Do you expect your average monthly expenses to increase or decrease by more than 10% during the next 6 months?', states /no ('No', sampled_ok) and /yes ('Yes. Explain', adjudicated). 3f spec §6.4 and §8.2: FilingFee.expense_change_answer; blank until answered."                                                                                                                                                                       |
| `undefined_10`        | `derived:fee_waiver_expense_change_explanation` | "Field index: undefined_10 p2 line 9 'Line 9 Yes. Explain (expected >10% expense change)' (adjudicated). 3f spec §6.4 and §8.2: line 9's explanation, printed only beside a Yes."                                                                                                                                                                                                                                                                                            |

Then delete `form_101.unbound.json`'s `Check Box7` entry and `form_103b.unbound.json`'s `Check 4`, `Check 7` and `Check 9` entries. `4 type`, `5 Type`, `undefined_8` and `undefined_10` have no entries to delete.

- [ ] **Step 7: The seed**

Each persona's dict gains `"filing_fee"`, after the dict's last key, under the comment `# Form 101 line 8, and for the waiver 103B lines 4, 5, 7 and 9 (3f spec §10)`:

- Maria: `{"payment_choice": "waiver", "income_change_answer": "no", "installments_explanation": "I support two children on what I earn. After rent, food, the car and the children's costs, there is not enough left each month to pay the fee, even in parts.", "others_covered_answer": "no", "expense_change_answer": "no"}`.
- Sarah: the same, with `"installments_explanation": "I have no savings. My pay covers rent, food and my bus pass, and what is left each month goes to bills I already owe."`.
- DeShawn and Andrés: `{"payment_choice": "installments"}`. DeShawn's `fee_waiver` dict and its comment (`:511-517`) give way to `# No "fee_waiver": he pays the fee in installments (3f spec §10).`.
- James and Priya: `{"payment_choice": "pay_in_full"}`.

In `_create_persona`, after the SOFA block and before `# Run means test calculation`, add `FilingFee.objects.create(session=session, **data["filing_fee"])`, with the comment `# The filing-fee page's answers, which every persona gives after Complete`. Add `FilingFee` to the models import.

- [ ] **Step 8: The frontend**

- `FormDashboard.tsx`: after `:59`, add `'/filing-fee': 'Go to How you will pay the filing fee',`.
- `deshawn-assets.spec.ts:97` becomes `await dashboard.generateAllForms(14); // he pays in installments, so no Form 103B`, and `:99` becomes `expect(count).toBe(14);`. The journey still passes the old waiver page until Task 5 replaces it, so it fails between Tasks 4 and 5 (Global Constraints).

- [ ] **Step 9: Run the tests to verify they pass**

Run: the Step 2 command.

Expected: PASS. Then confirm the tier 2 delta: `$PY -m pytest apps/forms/tests/test_oracle_tier2.py -q -p no:cacheprovider` passes with the new `ASSERTED_CASES`, and `known_defects.json` is still `[]`.

- [ ] **Step 10: CLAUDE.md**

After this task the sentences read as follows.

- **"Seed order".** After "...and stamps `income_period_end` with today's window." add: "The seed also writes each persona's `FilingFee`. Maria and Sarah ask for the waiver, with 103B lines 4, 7 and 9 No and their own line 5; DeShawn and Andrés pay in installments; James and Priya pay in full." The "Personas seeded before 3f …" sentence and the fee-waiver clause are Task 8's (ruling R27).
- **"The packet decides which forms a filer gets".**
  - Its second sentence: "103B applies only when the filer's Form 101 line 8 answer, `FilingFee.payment_choice`, is `waiver` (`_asks_fee_waiver`); 122A-2 only when `MeansTest.calculated_cmi × 12 > median_income_threshold`, through `is_above_median` (`apps/eligibility/cmi.py`), the means test's own comparison, so income exactly at the median counts as below (DIG-136)."
  - Its last sentence: "Form 101's `requires` is `_needs_debtor_info_county_and_fee_choice`, so a missing county, and then a missing line 8 answer ("Choose how you will pay the filing fee."), is its `PreconditionMissing`. 103B's is `_needs_fee_waiver_answers`: lines 4, 7 and 9 answered, each Yes with its text, and line 5 not blank once trimmed, the first gap in the form's order refused. Both refuse with `page="/filing-fee"`. A `PreconditionMissing` carries a `step` or a `page`, never both, and a raise names it as a literal, which `test_rule_fixes.py` reads from the source."
- **"Forms need a completed intake".**
  - "`PreconditionMissing.step`," becomes "`PreconditionMissing.step` or `.page` (`/filing-fee` for Form 101's line 8 and 103B's own questions),".
  - "Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it" becomes "Form answers (`answers/bulk`), SOFA, the filing fee (`PUT /api/intake/sessions/{id}/filing-fee/`) and the fee-waiver application never reopen it".
  - "whose defaults are `not_married`, a list of `[]` and county `Cook`." becomes "whose defaults are `not_married`, a list of `[]`, county `Cook` and a `FilingFee` paying in full, so Form 101 has its line 8 answer (`payment_choice=None` leaves the record as it is)."
- **"GenerateAll vs single".** "returns `{session, form_types, tables, income_period}` in filing order" becomes "returns `{session, form_types, tables, income_period, payment_choice}` in filing order". Before "; the dashboard renders from it" add "; `payment_choice` is the Form 101 line 8 answer, or null before the filer chooses". Task 6 rewrites the sentence with the dashboard's use of it.
- **"The fee-waiver application".**

  - ", since an application puts 103B in the packet" is deleted. The clause reads "...reads one session's application and never creates one; the page opens with it...".
  - "`4 type` and `5 Type` are unbound." becomes "Lines 4, 5, 7 and 9 (`Check 4`, `4 type`, `5 Type`, `Check 7`, `undefined_8`, `Check 9`, `undefined_10`) print the filer's `FilingFee` answers, each explanation only beside its Yes, so a text kept after a move to No stays stored and prints nothing (see "The packet decides which forms")."
  - Task 2 may have rewritten the sentences around these clauses; edit each clause where it now stands.

- [ ] **Step 11: Gates**

- Check `uptime` (1-minute load under 10), then the full backend gate from Global Constraints: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 -q -p no:cacheprovider`.
- `/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/` (ruff 0.8.5).
- `cd backend && $PY manage.py check`. It runs forms.E001–E007 on the new bindings and states.
- No model changes, so no `makemigrations --check`. No migration and no lock entry, so no `postgres` run.
- Frontend (this task touches `FormDashboard.tsx` and a journey): `cd frontend && npx vitest run --maxWorkers=2`; `npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit`; `npm run lint`; `npm run format:check`.
- No journeys: they fail until Task 5 (Global Constraints).

Expected: all pass.

- [ ] **Step 12: Commit**

```bash
/usr/bin/git add backend/apps/forms/registry.py backend/apps/forms/views.py backend/apps/forms/services/derivations.py data/forms/schemas/form_101.json data/forms/schemas/form_103b.json data/forms/field_index/audit/step2_verification.json data/forms/field_index/audit/form_101.unbound.json data/forms/field_index/audit/form_103b.unbound.json backend/apps/intake/management/commands/seed_demo_data.py backend/apps/forms/tests/test_filing_fee_forms.py backend/apps/forms/tests/test_registry.py backend/apps/forms/tests/test_form_views.py backend/apps/forms/tests/test_download_action.py backend/apps/forms/tests/test_rule_fixes.py backend/apps/forms/tests/test_oracle_tier2.py backend/apps/forms/tests/test_oracle_tier3.py backend/apps/forms/tests/test_printed_page.py backend/apps/forms/tests/test_api_readback.py backend/apps/intake/tests/test_seed_demo_data.py frontend/src/pages/FormDashboard.tsx frontend/e2e/journeys/deshawn-assets.spec.ts CLAUDE.md
/usr/bin/git commit -F /tmp/3f-task4-msg.txt
```

`/tmp/3f-task4-msg.txt`, with no trailer:

```
feat(forms): the packet follows the filer's line 8 answer

Form 103B is in the packet exactly when the filer asks for the fee waiver
on Form 101 line 8, and Form 101 ticks that answer. A petition with no
answer, or a waiver application with line 4, 5, 7 or 9 unanswered, is
refused with a link to the filing-fee page. 103B prints those lines from
the filing-fee record, the packet reply carries the answer, and the seed
gives each persona theirs: DeShawn pays in installments, so his packet
drops to 14 forms.
```

### Task 5: Every filer chooses how to pay the fee on the filing-fee page

**Spec:** §3 (the flow), §6.1–§6.5 (the page and its API), §10 "E2E", §11 (words), §12 (File Map), §13 (the line 8 answer is the filer's; the page shows both figures and never a verdict; a reopened intake shows no figure and still saves).

Line numbers are as of `dc31b7a`. Before this task, the frontend changes only in two places. Task 4 changes DeShawn's journey count (`deshawn-assets.spec.ts:97`, `:99`) and adds `PAGE_LINK_LABELS['/filing-fee']` to `FormDashboard.tsx` (ruling R12), a file this task doesn't edit. So the numbers below hold. Tasks 2 and 4 will already have edited `CLAUDE.md:75`.

**Files:**

- Create: `frontend/src/pages/FilingFeePage.tsx`
- Create: `frontend/src/pages/__tests__/FilingFeePage.test.tsx`
- Create: `frontend/src/constants/filingFee.ts`
- Create: `backend/apps/intake/tests/test_filing_fee_frontend_copy.py`
- Delete: `frontend/src/pages/FeeWaiverPage.tsx`, `frontend/src/pages/__tests__/FeeWaiverPage.test.tsx`, `frontend/e2e/pages/fee-waiver.page.ts`
- Modify: `frontend/src/App.tsx:9` (import `Navigate`), `:21` (the page import), `:80` (the route)
- Modify: `frontend/src/App.test.tsx:22-27`
- Modify: `frontend/src/pages/IntakeWizard.tsx:483-515` (`handleComplete`, the branch at `:498-504`)
- Modify: `frontend/src/pages/__tests__/IntakeWizard.test.tsx:70` (stub route), `:147-181` (the two routing tests), `:251`
- Modify: `frontend/src/api/client.ts:342-456` (`intakeAPI` gains `filingFee`), `:11-43` (type imports). The Fee Waiver section (`:509-560`) and `:772` (`feeWaiver: feeWaiverAPI,`) stay: Task 8 deletes them with the endpoint (ruling R25). Its line numbers there move down by the lines `filingFee` adds.
- Modify: `frontend/src/types/api.ts`. Add a "Filing fee" section after "Means Test" (`:452-474`).
- Modify: `frontend/src/test/mocks/handlers.ts`. Add a `// -- Filing fee` section with a GET and a PUT after the Fee Waiver handlers (`:146-167`). Those handlers stay for Task 8 (R25), and since nothing is inserted above them, Task 8's line numbers there still hold.
- Modify: `frontend/src/constants/copy.ts` (a new `// Filing fee page` section at the end, after `:335`) and `frontend/src/constants/formText.ts` (appended after `:183`)
- Modify: `frontend/src/styles/global.css:1750-1764`. Rename the banner and the two page-only rules. `.fee-waiver-checkbox` and `.fee-waiver-question` (`:1766-1785`) stay.
- Create: `frontend/e2e/pages/filing-fee.page.ts`
- Modify: `frontend/e2e/pages/wizard.page.ts:41-47` (`completeIntake`)
- Modify: `frontend/e2e/fixtures/personas.ts:125-161` (types), and each persona's tail: `:254-255`, `:338`, `:445`, `:567-571`, `:637-638`, `:819-821`
- Modify: the journeys `frontend/e2e/journeys/maria-happy-path.spec.ts:1-26`, `:83-97`; `sarah-simplest.spec.ts:1-26`, `:39`, `:51-60`, `:82-96`; `deshawn-assets.spec.ts:14`, `:24`, `:81-92`; `andres-gig-driver.spec.ts:1-21`, `:74-86`; `james-borderline.spec.ts:14-24`, `:76-84`; `priya-ineligible.spec.ts:10-22`, `:81-84`; `sofa-journey.spec.ts:1-30`, `:93`, `:120`
- Modify: `CLAUDE.md:130` (File Map) and the gotcha "The fee-waiver application" (`:75`)

**Interfaces:**

- Consumes:
  - Task 3: `GET`/`PUT /api/intake/sessions/{id}/filing-fee/`. The GET body is `{payment_choice, income_change_answer, income_change_explanation, installments_explanation, others_covered_answer, others_covered_who, expense_change_answer, expense_change_explanation, information, information_gap}`. `information` is `{family_size, limit_monthly, guideline: {year, effective_date, source_url}, family_income_monthly}`, with the amounts as decimal strings, or null. `information_gap` is `"income"`, `"no_table"` or null. The PUT sets only the keys sent and returns the GET body.
  - Task 3: `FilingFee.TEXT_LIMITS = {"income_change_explanation": 520, "installments_explanation": 520, "others_covered_who": 420, "expense_change_explanation": 420}` (ruling R10).
  - Task 4: 101's and 103B's `requires()`. The page refuses only a missing choice, in its own `copy.ts` sentence. The 101 refusal's sentence lives in `registry.py` (R14). A blank waiver question is 103B's refusal on the dashboard.
  - Task 4: the seed's and the readback's line 8 answers. The journeys make the same choices.
- Produces (frontend):

  - `types/api.ts`:

    ```ts
    // Form 101 line 8, "How you will pay the fee"
    export type PaymentChoice = 'pay_in_full' | 'installments' | 'waiver';
    // What the page shows beside the question (3f spec §6.2): amounts as decimal strings
    export interface FilingFeeInformation {
      family_size: number;
      limit_monthly: string;
      guideline: { year: number; effective_date: string; source_url: string };
      family_income_monthly: string;
    }
    // The session's filing-fee record, as GET and PUT .../filing-fee/ return it. Null is unanswered.
    export interface FilingFee {
      payment_choice: PaymentChoice | null;
      income_change_answer: YesNo | null;
      income_change_explanation: string;
      installments_explanation: string;
      others_covered_answer: YesNo | null;
      others_covered_who: string;
      expense_change_answer: YesNo | null;
      expense_change_explanation: string;
      information: FilingFeeInformation | null;
      information_gap: 'income' | 'no_table' | null;
    }
    ```

  - `api.intake.filingFee.get(sessionId: number): Promise<FilingFee>` and `api.intake.filingFee.put(sessionId: number, body: Partial<Omit<FilingFee, 'information' | 'information_gap'>>): Promise<FilingFee>`. Both go through `apiFetch`, so a 5xx is retried; a PUT of the same keys is idempotent.
  - `constants/filingFee.ts`:
    - `FILING_FEE_TEXT_LIMITS: Record<'income_change_explanation' | 'installments_explanation' | 'others_covered_who' | 'expense_change_explanation', number>`. Each entry sits on its own line, written `  <key>: <n>,`. Prettier's `trailingComma: "es5"` (root `.prettierrc`) keeps the comma on the last one. The values are `FilingFee.TEXT_LIMITS`'s: 520, 520, 420 and 420. Nothing else goes in the file.
  - `formText.ts` (Form 101 page 3 and `form_b103b.pdf`, read with PyMuPDF for this plan; the line 8 options checked against `form_b_101_0624_fillable_clean.index.json`'s `option_text` for `Check Box7`):
    - `LINE_8_LABEL = 'How you will pay the fee'` (no cut; the field index's `label` for `Check Box7`). Task 6 shows the same label on the dashboard and imports this constant. It does not add its own (see the report on Task 6).
    - `PAYMENT_CHOICE_WORDS: Record<PaymentChoice, string>` (ruling R16, the field index's words):
      - `pay_in_full: 'I will pay the entire fee when I file my petition.'` (cut: "Please check with the clerk's office…" to the end);
      - `installments: 'I need to pay the fee in installments.'` (cut: "If you choose this option, sign and attach…");
      - `waiver: 'I request that my fee be waived'` (cut: the parenthesis and "If you choose this option…"). There is no period, as in the index. Spec §6.1's period is an erratum (R16).
    - `FEE_LAW_SENTENCE = 'By law, a judge may, but is not required to, waive your fee, and may do so only if your income is less than 150% of the official poverty line that applies to your family size and you are unable to pay the fee in installments.'` The cut is the parenthesis's first sentence and its brackets, with a period added. The printed parenthesis closes right after "installments".
    - `WAIVER_LINE_4_QUESTION = "Do you expect your family's average monthly net income to increase or decrease by more than 10% during the next 6 months?"`
    - `WAIVER_LINE_5_QUESTION = 'Tell the court why you are unable to pay the filing fee in installments within 120 days. If you have some additional circumstances that cause you to not be able to pay your filing fee in installments, explain them.'`
    - `WAIVER_LINE_7_QUESTION = 'Do these expenses cover anyone who is not included in your family as reported in line 1?'`
    - `WAIVER_LINE_9_QUESTION = 'Do you expect your average monthly expenses to increase or decrease by more than 10% during the next 6 months?'`
    - `WAIVER_LINE_4_EXPLAIN = 'Explain.'` (cut "Yes.").
    - `WAIVER_LINE_9_EXPLAIN = 'Explain'` (cut "Yes."). Page 2 prints line 9's "Yes. Explain" with no period, unlike line 4.
    - `WAIVER_IDENTIFY_WHO = 'Identify who'` (line 7, cut "Yes.").
    - Each uses the straight apostrophe the file already uses (`formText.ts:125`).
  - `copy.ts`. Each score comes from `reading-level.test.ts`'s formula, computed for this plan against a limit of 9. Each `// DRAFT: counsel C-7` goes on its own line above its constant:
    - `FILING_FEE_TITLE = 'How you will pay the filing fee'` (0.63)
    - `FEE_LIMIT_LEAD = '150% of the official poverty line for a family of'` (7.59), DRAFT C-7
    - `FEE_GUIDELINE_LEAD = 'This comes from the HHS poverty guidelines for'` (8.18), DRAFT C-7
    - `FEE_FIGURE_LEAD = "Your family's income, as Form 103B counts it from your answers:"` (4.82), DRAFT C-7
    - `FEE_COURT_DECIDES = 'The court decides. The judge also looks at whether you can pay the fee in installments.'` (3.76), DRAFT C-7
    - `FEE_INCOME_GAP = "Your family size and income can't be shown until your Income step is finished."` (7.57), DRAFT C-7
    - `FEE_NO_TABLE = "DigniFi doesn't have the current poverty figures, so it can't show the limit right now."` (8.39), DRAFT C-7
    - `FEE_LINE_5_NOTE = 'The court decides whether you can pay in installments, from what you write here and the rest of the form.'` (6.96), DRAFT C-7
    - `FEE_OTHER_LINES_NOTE = 'DigniFi leaves line 8 and Part 3 of Form 103B blank for now, and the details of lines 17 to 20. Form 103B also asks for a copy of your Schedule A/B.'` (5.53)
    - `INSTALLMENTS_NOTICE = "To pay in installments, you also file Form 103A, Application for Individuals to Pay the Filing Fee in Installments. DigniFi doesn't prepare Form 103A yet. You can get it from the court."` (6.22). This is §6.3's three sentences. The title is 103A's own, printed plain because one string can't carry italics.
    - `FORM_103A_LINK = 'Get Form 103A from the U.S. Courts website'` (−1.31)
    - `FORM_103A_URL = 'https://www.uscourts.gov/forms-rules/forms/application-individuals-pay-filing-fee-installments-0'` (R16). The reading-level test scores it too: it splits the URL into 13 words, at 7.88.
    - `FEE_CHOICE_MISSING = 'Choose how you will pay the filing fee.'` (0.80). This is the page's own Continue refusal. Task 4's 101 refusal uses the same words, but that sentence lives in `registry.py` (R14).
    - `FEE_READ_FAILED = "We couldn't get your answers just now. Please try again in a moment."` (1.47)
    - `FEE_SAVE_FAILED = "We couldn't save your answer just now. Please try again."` (0.50)
  - The 103A notice, under installments: `<p className="info-box">{INSTALLMENTS_NOTICE}{' '}<a href={FORM_103A_URL} target="_blank" rel="noopener noreferrer">{FORM_103A_LINK}</a></p>`. Task 6 renders the same three constants on the dashboard in the same shape (§6.3, "the same notice"). Each place writes its own markup, so there is no shared component.
  - `FilingFeePage` (named export) at `/filing-fee`, and `/fee-waiver` → `<Navigate to="/filing-fee" replace />`.
  - `handleComplete` sends every filer to `/filing-fee` after Complete and the means test.
  - The page's form controls are what the e2e page object names: radios `name="payment_choice"`, `name="income_change_answer"`, `name="others_covered_answer"` and `name="expense_change_answer"`, each with `value` set to its stored answer; textareas `name=` each text's key.
  - e2e:
    - `FilingFeePage` (`e2e/pages/filing-fee.page.ts`): `waitForLoad()`, `limitSentence(familySize: number, limit: string)` (a locator), `answer(choice: PaymentChoice, waiver?: PersonaWaiverAnswers)`.
    - `personas.ts`: `PaymentChoice`, `PersonaWaiverAnswers`, `PersonaFilingFee`, and `PersonaData.filing_fee`.

- Produces (backend): `test_filing_fee_frontend_copy.py` pins `FILING_FEE_TEXT_LIMITS` to `FilingFee.TEXT_LIMITS`.
- `ASSERTED_CASES` is unchanged: this task binds nothing.
- CLAUDE.md:
  - File Map, `:130`, reads after this task: "- `src/pages/SOFAStep.tsx` (`/sofa`), `FilingFeePage.tsx` (`/filing-fee`) — post-intake pages; `handleComplete` always goes to `/filing-fee`, which asks Form 101 line 8 (and 103B lines 4, 5, 7 and 9 under the waiver) and continues to `/sofa`; `/fee-waiver` redirects to `/filing-fee`"
  - "The fee-waiver application": the page's sentences go. Delete the clause "; the page opens with it, so saved answers win over pre-fills, and take-home pay is never pre-filled". Delete the two sentences "The page's household-size pre-fill reads `household.fee_waiver_household_size`, 103B line 1's count, which is null while the Income step has a gap. A saved application still wins over it." If Task 2 or Task 4 already reworded or removed either passage, delete whatever text about the page remains. Nothing else changes here: Task 8 rewrites the gotcha whole as "The filing fee".

**Decided here:**

- **What the PUT carries.** §4 says the waiver answers stay stored and come back if the filer picks the waiver again, so the page sends only what the choice shows:
  - Under `pay_in_full` or `installments`, the body is exactly `{payment_choice}`.
  - Under `waiver`, the body carries `payment_choice`, the three yes/no answers (null while unanswered) and `installments_explanation`, plus each Yes text only while its answer is `"yes"`.
  - A text behind No is left out, so the server keeps what an earlier Yes stored and the box still shows it. The same rule covers the current figures in 3e2 (CLAUDE.md "Autosave sends only real edits").
  - Task 4's rules print a text only under its Yes, which keeps a stored text under No off the form.
- **The text limits reach the page as a pinned copy (ruling R10).** Task 3's GET carries no limits. `constants/filingFee.ts` copies `FilingFee.TEXT_LIMITS`, and `test_filing_fee_frontend_copy.py` pins the copy to the model, as `test_household_frontend_copy.py` pins the counties. Each textarea takes its `maxLength` from that copy, so the page can't send what the serializer would refuse. `check()` at Generate still has the last word.
- **The 103A link (R16).** The URL ending `…-installments` (no suffix) is titled "(Superseded)": it is Official Form 3A, replaced December 1, 2015. The current Official Form 103A page ends `-0`. It returned 200 on 2026-11-02 and links `form_b103a.pdf`. The URL lives in `copy.ts` beside the notice and the link words, because Task 6 imports all three from there.
- **The fee-waiver client stays for Task 8 (ruling R25).** This task deletes the page, its test and its page-only CSS. It leaves `feeWaiverAPI` and its two types (`client.ts:509-560`, `:772`) and the MSW handlers (`handlers.ts:146-167`). Task 8 deletes those with the endpoint and runs the frontend gates. After this task, nothing in `src` calls `api.feeWaiver`.
- **`household.fee_waiver_household_size` loses its only reader (ruling R26).** That reader was `FeeWaiverPage.tsx:29`. The field stays: it is 103B line 1's count (`serializers.py:562-573`, `api.ts:270`). It is listed for the owner and not removed.
- **CSS.** `.fee-waiver-page` and `.fee-waiver-error` become `.filing-fee-page` and `.filing-fee-error`, unchanged otherwise. The new page needs the same container. `fee-waiver-ineligible` had no rule. The banner `Fee Waiver` (`:1751`) becomes `Filing fee page (the Yes/No classes below are shared by the wizard's steps)`.
- **Journey comments and personas are this task's (ruling R22).** This task rewrites every routing or "qualifies" comment in the journeys it edits: James `:76-79` and `:83-84`, the SOFA journey `:7-8`, `:93` and `:120`, Andrés `:2-8` and `:21`, and the Maria, Sarah and DeShawn headers and comments. It also removes `personas.ts`'s `fee_waiver_eligible`, the type and every value, renames `fee_waiver` to `filing_fee`, and moves `sarah-simplest.spec.ts:57-60` to the page. Task 7 leaves all of these alone.
- **The wizard's routing test carries no flag.** The new test varies `passes_means_test`, the computed result, and its mock has no `qualifies_for_fee_waiver` key. R22 gives these tests to this task, so Task 7 never touches them. Task 9's final grep would also find any stray key (R21 excludes only the preview test's mock reply). The default means-test handler still sends `qualifies_for_fee_waiver: false` (`handlers.ts:75`) until Task 7.
- **No gate type-checks `frontend/e2e` (ruling R23).** `tsconfig.app.json` includes only `src` and excludes tests. `tsconfig.node.json` includes only `vite.config.ts`. `format:check` globs `src/**`, and Playwright strips types without checking them. `eslint .` does reach `e2e`, and Step 9 adds `npx prettier --check "e2e/**/*.ts"`, which passes at `dc31b7a`. A type error in `personas.ts` or a page object still shows only as a failed journey.

- [ ] **Step 1: Write the failing backend pin test**

`backend/apps/intake/tests/test_filing_fee_frontend_copy.py`:

```python
"""
The filing-fee page stops each text at the length its box on Form 103B can print. The limits
are measured once, on FilingFee (3f spec §6.4), and copied into the page's constants: a copy
that drifted would let the page send a text the server refuses, or cut one the box would print.
"""

import re

import pytest
from django.conf import settings

from apps.intake.models import FilingFee

FRONTEND = settings.BASE_DIR.parent / "frontend" / "src"


def test_the_filing_fee_page_stops_each_text_where_its_box_does():
    if not FRONTEND.is_dir():
        pytest.skip("the frontend's source isn't here (compose's backend mounts backend/ only)")
    text = (FRONTEND / "constants" / "filingFee.ts").read_text()
    copied = {key: int(n) for key, n in re.findall(r"^  (\w+): (\d+),$", text, re.M)}
    assert copied == dict(FilingFee.TEXT_LIMITS)
```

Run: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest apps/intake/tests/test_filing_fee_frontend_copy.py -q -p no:cacheprovider`
Expected: FAIL with `FileNotFoundError` for `constants/filingFee.ts`.

- [ ] **Step 2: Write the failing page tests**

`frontend/src/pages/__tests__/FilingFeePage.test.tsx`:

```tsx
/**
 * The filing-fee page asks every filer Form 101 line 8 after Complete (3f spec §6). It shows the
 * court's limit and the filer's own figure as information, never a verdict, and it never decides
 * for the filer. Under the waiver it asks 103B lines 4, 5, 7 and 9.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { FilingFeePage } from '../FilingFeePage';
import { FILING_FEE_TEXT_LIMITS } from '../../constants/filingFee';
import {
  FEE_LAW_SENTENCE,
  PAYMENT_CHOICE_WORDS,
  WAIVER_LINE_4_QUESTION,
  WAIVER_LINE_5_QUESTION,
  WAIVER_LINE_7_QUESTION,
  WAIVER_LINE_9_QUESTION,
} from '../../constants/formText';
import {
  FEE_CHOICE_MISSING,
  FEE_COURT_DECIDES,
  FEE_INCOME_GAP,
  FEE_LINE_5_NOTE,
  FEE_NO_TABLE,
  FEE_OTHER_LINES_NOTE,
  FEE_READ_FAILED,
  FEE_SAVE_FAILED,
  FORM_103A_LINK,
  FORM_103A_URL,
  INSTALLMENTS_NOTICE,
} from '../../constants/copy';
import type { FilingFee, FilingFeeInformation, PaymentChoice } from '../../types/api';

const URL = 'http://localhost:8000/api/intake/sessions/:id/filing-fee/';

const GUIDELINE = {
  year: 2026,
  effective_date: '2026-01-15',
  source_url:
    'https://www.federalregister.gov/documents/2026/01/15/2026-00755/annual-update-of-the-hhs-poverty-guidelines',
};
// Sarah: a family of 1, below the limit. James: a family of 1, above it.
const SARAH: FilingFeeInformation = {
  family_size: 1,
  limit_monthly: '1995.00',
  guideline: GUIDELINE,
  family_income_monthly: '1750.00',
};
const JAMES: FilingFeeInformation = { ...SARAH, family_income_monthly: '4500.00' };

function record(overrides: Partial<FilingFee> = {}): FilingFee {
  return {
    payment_choice: null,
    income_change_answer: null,
    income_change_explanation: '',
    installments_explanation: '',
    others_covered_answer: null,
    others_covered_who: '',
    expense_change_answer: null,
    expense_change_explanation: '',
    information: SARAH,
    information_gap: null,
    ...overrides,
  };
}

/** Serves `saved` and records each body the page PUTs */
function serve(saved: FilingFee) {
  const sent: Record<string, unknown>[] = [];
  server.use(
    http.get(URL, () => HttpResponse.json(saved)),
    http.put(URL, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      sent.push(body);
      return HttpResponse.json({ ...saved, ...body });
    })
  );
  return sent;
}

function renderPage() {
  localStorage.setItem('current_session_id', '1');
  return render(
    <MemoryRouter initialEntries={['/filing-fee']}>
      <IntakeProvider>
        <Routes>
          <Route path="/filing-fee" element={<FilingFeePage />} />
          <Route path="/sofa" element={<div>Statement of Financial Affairs</div>} />
          <Route path="/intake" element={<div>IntakeWizard</div>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

const choice = (c: PaymentChoice) => screen.findByRole('radio', { name: PAYMENT_CHOICE_WORDS[c] });
const group = (legend: string) => screen.getByRole('group', { name: legend });
const pressContinue = () => userEvent.click(screen.getByRole('button', { name: 'Continue' }));

describe('FilingFeePage', () => {
  it('asks Form 101 line 8 in its own words with nothing chosen', async () => {
    serve(record());
    renderPage();
    expect(
      await screen.findByRole('heading', { level: 1, name: 'How you will pay the filing fee' })
    ).toBeInTheDocument();
    for (const c of ['pay_in_full', 'installments', 'waiver'] as const) {
      expect(await choice(c)).not.toBeChecked();
    }
    expect(screen.getByText(FEE_LAW_SENTENCE)).toBeInTheDocument();
  });

  it("shows the court's limit and the family's own figure, and the court decides", async () => {
    serve(record());
    renderPage();
    expect(
      await screen.findByText(
        '150% of the official poverty line for a family of 1: $1,995.00 a month.'
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'This comes from the HHS poverty guidelines for 2026, published January 15, 2026.'
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Your family's income, as Form 103B counts it from your answers: $1,750.00 a month."
      )
    ).toBeInTheDocument();
    expect(screen.getByText(FEE_COURT_DECIDES)).toBeInTheDocument();
  });

  it('says the same words whether the figure is below the limit or above it', async () => {
    // [UPL] The page compares nothing for the filer: only the two amounts differ
    const words = async (information: FilingFeeInformation) => {
      serve(record({ information }));
      const { unmount } = renderPage();
      await choice('waiver');
      const text = screen.getByRole('main').textContent ?? '';
      unmount();
      return text;
    };
    const below = await words(SARAH);
    const above = await words(JAMES);
    expect(below.replace('$1,750.00', '$X')).toBe(above.replace('$4,500.00', '$X'));
    expect(below).not.toMatch(/qualif|eligib|you should/i);
  });

  it('with an Income step gap shows no figure, links to the Income step, and still saves', async () => {
    const sent = serve(record({ information: null, information_gap: 'income' }));
    renderPage();
    expect(await screen.findByText(FEE_INCOME_GAP)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Go to Income' })).toHaveAttribute(
      'href',
      '/intake?step=income_info'
    );
    expect(screen.getByRole('main').textContent).not.toMatch(/\$/);
    await userEvent.click(await choice('pay_in_full'));
    await pressContinue();
    await screen.findByText('Statement of Financial Affairs');
    expect(sent).toEqual([{ payment_choice: 'pay_in_full' }]);
  });

  it('with no poverty table in force says so, shows no old limit, and still saves', async () => {
    const sent = serve(record({ information: null, information_gap: 'no_table' }));
    renderPage();
    expect(await screen.findByText(FEE_NO_TABLE)).toBeInTheDocument();
    expect(screen.queryByText(/poverty line for a family of/)).not.toBeInTheDocument();
    await userEvent.click(await choice('waiver'));
    await pressContinue();
    await screen.findByText('Statement of Financial Affairs');
    expect(sent).toHaveLength(1);
  });

  it('refuses Continue until the filer chooses, and sends nothing', async () => {
    const sent = serve(record());
    renderPage();
    await choice('pay_in_full');
    await pressContinue();
    expect(await screen.findByRole('alert')).toHaveTextContent(FEE_CHOICE_MISSING);
    expect(sent).toHaveLength(0);
    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
  });

  it('saves the choice and goes on to the financial history questions', async () => {
    const sent = serve(record());
    renderPage();
    await userEvent.click(await choice('installments'));
    await pressContinue();
    await screen.findByText('Statement of Financial Affairs');
    expect(sent).toEqual([{ payment_choice: 'installments' }]);
  });

  it('under installments says where to get Form 103A, and under the other answers it does not', async () => {
    serve(record());
    renderPage();
    await userEvent.click(await choice('pay_in_full'));
    expect(screen.queryByRole('link', { name: FORM_103A_LINK })).not.toBeInTheDocument();
    await userEvent.click(await choice('installments'));
    const link = screen.getByRole('link', { name: FORM_103A_LINK });
    expect(link).toHaveAttribute('href', FORM_103A_URL);
    expect(link.closest('p')).toHaveTextContent(INSTALLMENTS_NOTICE);
    await userEvent.click(await choice('waiver'));
    expect(screen.queryByRole('link', { name: FORM_103A_LINK })).not.toBeInTheDocument();
  });

  it("asks 103B's own questions only under the waiver, with nothing answered", async () => {
    serve(record());
    renderPage();
    await userEvent.click(await choice('pay_in_full'));
    expect(screen.queryByText(WAIVER_LINE_4_QUESTION)).not.toBeInTheDocument();
    await userEvent.click(await choice('waiver'));
    for (const legend of [WAIVER_LINE_4_QUESTION, WAIVER_LINE_7_QUESTION, WAIVER_LINE_9_QUESTION]) {
      for (const radio of within(group(legend)).getAllByRole('radio'))
        expect(radio).not.toBeChecked();
    }
    expect(screen.getByLabelText(WAIVER_LINE_5_QUESTION)).toHaveValue('');
    expect(screen.getByText(FEE_LINE_5_NOTE)).toBeInTheDocument();
    expect(screen.getByText(FEE_OTHER_LINES_NOTE)).toBeInTheDocument();
  });

  it("sends the waiver's answers with the choice, and a Yes's text only under its Yes", async () => {
    const sent = serve(record());
    renderPage();
    await userEvent.click(await choice('waiver'));
    await userEvent.click(
      within(group(WAIVER_LINE_4_QUESTION)).getByRole('radio', { name: 'Yes' })
    );
    await userEvent.type(
      within(group(WAIVER_LINE_4_QUESTION)).getByLabelText('Explain.'),
      'My hours were cut in October.'
    );
    await userEvent.type(screen.getByLabelText(WAIVER_LINE_5_QUESTION), 'I have no savings.');
    await userEvent.click(within(group(WAIVER_LINE_7_QUESTION)).getByRole('radio', { name: 'No' }));
    await userEvent.click(within(group(WAIVER_LINE_9_QUESTION)).getByRole('radio', { name: 'No' }));
    await pressContinue();
    await screen.findByText('Statement of Financial Affairs');
    expect(sent).toEqual([
      {
        payment_choice: 'waiver',
        income_change_answer: 'yes',
        income_change_explanation: 'My hours were cut in October.',
        installments_explanation: 'I have no savings.',
        others_covered_answer: 'no',
        expense_change_answer: 'no',
      },
    ]);
  });

  it('saves a waiver with its questions unanswered, since the forms page names what is missing', async () => {
    const sent = serve(record());
    renderPage();
    await userEvent.click(await choice('waiver'));
    await pressContinue();
    await screen.findByText('Statement of Financial Affairs');
    expect(sent).toEqual([
      {
        payment_choice: 'waiver',
        income_change_answer: null,
        installments_explanation: '',
        others_covered_answer: null,
        expense_change_answer: null,
      },
    ]);
  });

  it('opens with the saved answers, and moving off the waiver leaves them stored', async () => {
    const saved = record({
      payment_choice: 'waiver',
      income_change_answer: 'no',
      installments_explanation: 'I have no savings.',
      others_covered_answer: 'yes',
      others_covered_who: 'My mother',
      expense_change_answer: 'no',
    });
    const sent = serve(saved);
    renderPage();
    expect(await choice('waiver')).toBeChecked();
    expect(screen.getByLabelText(WAIVER_LINE_5_QUESTION)).toHaveValue('I have no savings.');
    expect(within(group(WAIVER_LINE_7_QUESTION)).getByLabelText('Identify who')).toHaveValue(
      'My mother'
    );
    await userEvent.click(await choice('installments'));
    await pressContinue();
    await screen.findByText('Statement of Financial Affairs');
    expect(sent).toEqual([{ payment_choice: 'installments' }]);
  });

  it('a filer who typed waiver answers and then chooses installments sends only the choice', async () => {
    // §4: the waiver answers stay stored and come back if the filer picks the waiver again. The
    // page never clears them, so the PUT leaves out every waiver key and the server keeps them.
    const sent = serve(record());
    renderPage();
    await userEvent.click(await choice('waiver'));
    await userEvent.click(
      within(group(WAIVER_LINE_4_QUESTION)).getByRole('radio', { name: 'Yes' })
    );
    await userEvent.type(
      within(group(WAIVER_LINE_4_QUESTION)).getByLabelText('Explain.'),
      'My hours were cut in October.'
    );
    await userEvent.type(screen.getByLabelText(WAIVER_LINE_5_QUESTION), 'I have no savings.');
    await userEvent.click(await choice('installments'));
    await userEvent.click(await choice('waiver'));
    expect(within(group(WAIVER_LINE_4_QUESTION)).getByRole('radio', { name: 'Yes' })).toBeChecked();
    expect(within(group(WAIVER_LINE_4_QUESTION)).getByLabelText('Explain.')).toHaveValue(
      'My hours were cut in October.'
    );
    expect(screen.getByLabelText(WAIVER_LINE_5_QUESTION)).toHaveValue('I have no savings.');
    await userEvent.click(await choice('installments'));
    await pressContinue();
    await screen.findByText('Statement of Financial Affairs');
    expect(sent).toEqual([{ payment_choice: 'installments' }]);
  });

  it('a waiver picked again shows what was saved under it before', async () => {
    serve(
      record({ payment_choice: 'pay_in_full', installments_explanation: 'I have no savings.' })
    );
    renderPage();
    expect(await choice('pay_in_full')).toBeChecked();
    await userEvent.click(await choice('waiver'));
    expect(screen.getByLabelText(WAIVER_LINE_5_QUESTION)).toHaveValue('I have no savings.');
  });

  it('stops each text at the length its box on the form can print', async () => {
    serve(
      record({
        income_change_answer: 'yes',
        others_covered_answer: 'yes',
        expense_change_answer: 'yes',
      })
    );
    renderPage();
    await userEvent.click(await choice('waiver'));
    const boxes = {
      income_change_explanation: within(group(WAIVER_LINE_4_QUESTION)).getByLabelText('Explain.'),
      installments_explanation: screen.getByLabelText(WAIVER_LINE_5_QUESTION),
      others_covered_who: within(group(WAIVER_LINE_7_QUESTION)).getByLabelText('Identify who'),
      // Line 9 prints "Yes. Explain" with no period
      expense_change_explanation: within(group(WAIVER_LINE_9_QUESTION)).getByLabelText('Explain'),
    };
    for (const [key, box] of Object.entries(boxes)) {
      expect(box).toHaveAttribute(
        'maxLength',
        String(FILING_FEE_TEXT_LIMITS[key as keyof typeof FILING_FEE_TEXT_LIMITS])
      );
    }
  });

  it('shows no question until the saved answers are read, and reads them again on Try again', async () => {
    // A blank page sent over the saved answers would undo them
    let reads = 0;
    server.use(
      http.get(URL, () => {
        reads += 1;
        return reads === 1
          ? HttpResponse.json({ detail: 'Bad request' }, { status: 400 })
          : HttpResponse.json(record({ payment_choice: 'installments' }));
      })
    );
    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent(FEE_READ_FAILED);
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await choice('installments')).toBeChecked();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(reads).toBe(2);
  });

  it('says so when the save fails, and keeps the filer on the page', async () => {
    serve(record());
    server.use(
      http.put(URL, () => HttpResponse.json({ payment_choice: ['bad'] }, { status: 400 }))
    );
    renderPage();
    await userEvent.click(await choice('pay_in_full'));
    await pressContinue();
    expect(await screen.findByRole('alert')).toHaveTextContent(FEE_SAVE_FAILED);
    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
  });
});
```

`App.test.tsx`: the test at `:22-27` renders `/filing-fee` in place of `/fee-waiver`. After the `describe('Source code link')` block (ends `:50`), add a new block:

```tsx
describe('Old links', () => {
  // §3: the fee-waiver page is gone, and a link to it (a bookmark, an old email) still lands
  it('an old link to the fee-waiver page opens the filing-fee page', async () => {
    localStorage.setItem('refresh_token', 'refresh-token');
    renderAt('/fee-waiver');
    expect(
      await screen.findByRole('heading', { level: 1, name: 'How you will pay the filing fee' })
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/filing-fee');
  });
});
```

The page shows its h1 before the read returns, and no session is loaded here. So the heading proves the redirect without an MSW handler for the read.

`IntakeWizard.test.tsx`:

- The stub at `:70` becomes `<Route path="/filing-fee" element={<div>FilingFeePage</div>} />`.
- `:251`'s `queryByText('FeeWaiverPage')` becomes `queryByText('FilingFeePage')`.
- The two tests at `:147-181` become one parametrized test. It varies the computed result and carries no `qualifies_for_fee_waiver` key (see "Decided here"):

```tsx
it.each([true, false])(
  'opens the filing-fee page after Complete whatever the means test returns (passes %s)',
  async (passes) => {
    renderWizard();
    const completeBtn = await screen.findByRole('button', { name: /complete intake/i });
    // Registered after the session GET resolves, as the test it replaces did (load race)
    server.use(
      http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
        HttpResponse.json({
          means_test_result: {
            passes_means_test: passes,
            cmi: passes ? 1000 : 9000,
            median_income_threshold: 5000,
          },
          session_id: 1,
        })
      )
    );
    await userEvent.click(completeBtn);
    expect(await screen.findByText('FilingFeePage')).toBeInTheDocument();
    expect(screen.queryByText('Statement of Financial Affairs')).not.toBeInTheDocument();
  }
);
```

- [ ] **Step 3: Run them and see them fail**

Run: `cd frontend && npx vitest run --maxWorkers=2 src/pages/__tests__/FilingFeePage.test.tsx src/App.test.tsx src/pages/__tests__/IntakeWizard.test.tsx`

Expected: FAIL.

- `FilingFeePage.test.tsx`: `Failed to resolve import "../FilingFeePage"`.
- `App.test.tsx`: the new test finds no heading "How you will pay the filing fee". `/fee-waiver` still renders `FeeWaiverPage`, whose h1 is "Filing Fee Waiver Application".
- `IntakeWizard.test.tsx`: both cases find no "FilingFeePage". The mock's `qualifies_for_fee_waiver` is undefined, so `handleComplete` (`:500-504`) navigates to `/sofa` in both.

- [ ] **Step 4: Implement the types, the client and the handlers**

- `types/api.ts`: add a `// Filing fee` banner section after "Means Test" with the three types from Interfaces. `YesNo` is at `:70`.
- `client.ts`:

  - Import `FilingFee` in the type list (`:11-43`).
  - Add to `intakeAPI`, after `getDischargeability` (`:450-454`), with a JSDoc naming `GET`/`PUT /api/intake/sessions/{id}/filing-fee/`:

    ```ts
    filingFee: {
      get: async (sessionId: number): Promise<FilingFee> =>
        apiFetch<FilingFee>(`/intake/sessions/${sessionId}/filing-fee/`),
      put: async (
        sessionId: number,
        body: Partial<Omit<FilingFee, 'information' | 'information_gap'>>
      ): Promise<FilingFee> =>
        apiFetch<FilingFee>(`/intake/sessions/${sessionId}/filing-fee/`, {
          method: 'PUT',
          body: JSON.stringify(body),
        }),
    },
    ```

  - Leave the Fee Waiver section (`:509-560`) and `feeWaiver: feeWaiverAPI,` (`:772`) as they are. Task 8 deletes them (R25).

- `handlers.ts`: after the Fee Waiver handlers (which end `:167`, and stay for Task 8), add a `// -- Filing fee` section:
  - A `mockFilingFee` fixture: every answer null or `''`; `information` is Sarah's from the test above; `information_gap: null`.
  - `http.get(`${API}/intake/sessions/:id/filing-fee/`)` returns it.
  - `http.put(...)` returns `{ ...mockFilingFee, ...body }`.
- `constants/filingFee.ts`: a header comment says what the file holds and that `test_filing_fee_frontend_copy.py` pins the limits to `FilingFee.TEXT_LIMITS`. Then `FILING_FEE_TEXT_LIMITS` with R10's four values, as in Interfaces. To confirm the model's values, run this from `backend/`:

  ```
  $PY -c "import django,os;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.test');django.setup();from apps.intake.models import FilingFee;print(FilingFee.TEXT_LIMITS)"
  ```

- `formText.ts` and `copy.ts`: add the constants in Interfaces. Give each `formText` entry its cut comment, as the file's existing entries have. `formText.ts` adds `PaymentChoice` to its type import (`:11-17`). `copy.ts` gets a `// Filing fee page` banner section at the end, which holds `INSTALLMENTS_NOTICE`, `FORM_103A_LINK` and `FORM_103A_URL` too.

- [ ] **Step 5: Implement the page, the notice, the route and the wizard**

`FilingFeePage()` (`pages/FilingFeePage.tsx`, named export, like `FeeWaiverPage`):

- **State.**
  - `answers: Omit<FilingFee, 'information' | 'information_gap'> | null`, plus `information` and `informationGap` from the read. A radio or a text sets only its own key in `answers`. Changing the choice never clears a waiver key, so answers typed under the waiver come back when it is picked again (§4).
  - `read: 'pending' | 'done' | 'failed'` and `readAttempt`, loaded on `[sessionId, readAttempt]` with a `cancelled` flag, exactly as `FeeWaiverPage.tsx:36-65`. `sessionId` is `useIntake().session?.id`.
  - `error: string | null` and `isSaving`.
- **Layout.** `<main className="filing-fee-page">`, then:
  1. `<h1>{FILING_FEE_TITLE}</h1>` and `<p>{FEE_LAW_SENTENCE}</p>`, shown before the read returns.
  2. While `read === 'failed'`: `<div className="filing-fee-error"><p role="alert">{FEE_READ_FAILED}</p>` and a `Try again` `Button`.
  3. Everything below only while `read === 'done'`.
  4. The information block:
     - With `information`, three `<p>`s: `${FEE_LIMIT_LEAD} ${family_size}: ${money(limit_monthly)} a month.`, then `${FEE_GUIDELINE_LEAD} ${year}, published ${formatIsoDate(effective_date)}.`, then `${FEE_FIGURE_LEAD} ${money(family_income_monthly)} a month.`. `money(s) = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(s))`, inline as `MeansTestPreview.tsx:32-33` does.
     - Under gap `'income'`: `<p>{FEE_INCOME_GAP}</p>` and a `Link` to `/intake?step=income_info` labelled `` `Go to ${label}` ``, where `label` is the `income_info` entry of `WIZARD_STEPS`. That is `fixLink`'s label in `FormDashboard.tsx:70-74`.
     - Under `'no_table'`: `<p>{FEE_NO_TABLE}</p>`.
     - Then `<p>{FEE_COURT_DECIDES}</p>`, always.
  5. `<fieldset className="form-field fee-waiver-question">` with `<legend className="form-label">{LINE_8_LABEL}</legend>` and three `fee-waiver-checkbox` radios. Each has `name="payment_choice"`, `value={choice}` and its label `PAYMENT_CHOICE_WORDS[choice]`. The radio markup is `ExpenseInfoStep.tsx:182-191`'s.
  6. Under `installments`: the 103A notice from Interfaces.
  7. Under `waiver`:
     - Lines 4, 7 and 9, each a fieldset like step 5's, its legend `WAIVER_LINE_n_QUESTION`, with No/Yes radios (`name` the answer key, `value` `no`/`yes`). Under Yes, inside the fieldset, a `FormTextarea` (`components/common/FormField.tsx:89-139`) with `name` the text key, label `WAIVER_LINE_4_EXPLAIN`, `WAIVER_IDENTIFY_WHO` or `WAIVER_LINE_9_EXPLAIN`, and `maxLength={FILING_FEE_TEXT_LIMITS[key]}`.
     - Line 5, a `FormTextarea` with `name="installments_explanation"`, `label={WAIVER_LINE_5_QUESTION}`, `helpText={FEE_LINE_5_NOTE}` and `maxLength`.
     - `<p className="form-help-text">{FEE_OTHER_LINES_NOTE}</p>`.
  8. The `error` alert (`<div className="filing-fee-error" role="alert">`), then `<Button type="button" onClick={handleContinue} disabled={isSaving}>Continue</Button>`.
- **Continue.**
  - With no choice: `setError(FEE_CHOICE_MISSING)` and send nothing.
  - Otherwise `await api.intake.filingFee.put(sessionId, body)`, with `body` as in "Decided here", then `navigate('/sofa')`.
  - On a throw: `setError(FEE_SAVE_FAILED)`.
  - There is no 800 ms pause as on SOFA: the filer moves on at once, as on the fee-waiver page.

`App.tsx`:

- `:9` imports `Navigate`.
- `:21` imports `FilingFeePage` from `./pages/FilingFeePage`.
- `:80` becomes two routes: `<Route path="/filing-fee" element={<FilingFeePage />} />` and `<Route path="/fee-waiver" element={<Navigate to="/filing-fee" replace />} />`.

`IntakeWizard.tsx`, `handleComplete`: `:498-504` become `await calculateMeansTest();` then `navigate('/filing-fee');`, with the comment "Every filer answers Form 101 line 8 next; nothing routes on the means test's result (3f spec §3)". The catch block is unchanged, so a failed means test still keeps the filer on Review.

Delete `FeeWaiverPage.tsx` and its test. In `global.css`, make the renames and the banner change from "Decided here".

Run `npm run format` from `frontend/`, so the new files take prettier's layout. Then run the Step 3 command, then the Step 1 command. Expected: PASS. The reading-level test scores all 15 new `copy.ts` texts, since each has five or more words.

- [ ] **Step 6: The e2e page objects and personas**

`e2e/pages/filing-fee.page.ts`, after `documents.page.ts`'s shape:

```ts
/**
 * Filing Fee Page Object — Form 101 line 8, "How you will pay the fee", which every filer
 * answers after Complete, with 103B lines 4, 5, 7 and 9 under the waiver. Continues to /sofa.
 */

import { expect, type Page } from '@playwright/test';
import type { PaymentChoice, PersonaWaiverAnswers } from '../fixtures/personas';

export class FilingFeePage {
  constructor(private page: Page) {}

  /** The page shows its choices only once the saved answers are read */
  async waitForLoad() {
    await this.page.waitForURL('**/filing-fee');
    await expect(this.page.locator('h1')).toHaveText('How you will pay the filing fee');
    await expect(this.page.locator('input[name="payment_choice"]').first()).toBeVisible();
  }

  /** The court's limit for the filer's family, as the page words it; limit as "$1,995.00" */
  limitSentence(familySize: number, limit: string) {
    return this.page.getByText(
      `150% of the official poverty line for a family of ${familySize}: ${limit} a month.`
    );
  }

  /** Choose, answer 103B's questions under the waiver, and continue to the SOFA step */
  async answer(choice: PaymentChoice, waiver?: PersonaWaiverAnswers) {
    await this.waitForLoad();
    await this.page.locator(`input[name="payment_choice"][value="${choice}"]`).check();
    if (choice === 'installments') {
      // §6.3: the page says where to get Form 103A, which DigniFi doesn't prepare yet
      await expect(
        this.page.getByRole('link', { name: 'Get Form 103A from the U.S. Courts website' })
      ).toBeVisible();
    }
    if (waiver) {
      const questions = ['income_change_answer', 'others_covered_answer', 'expense_change_answer'];
      for (const name of questions as (keyof PersonaWaiverAnswers)[]) {
        await this.page.locator(`input[name="${name}"][value="${waiver[name]}"]`).check();
      }
      await this.page
        .locator('textarea[name="installments_explanation"]')
        .fill(waiver.installments_explanation);
    }
    await this.page.getByRole('button', { name: 'Continue', exact: true }).click();
    await this.page.waitForURL('**/sofa');
  }
}
```

Delete `e2e/pages/fee-waiver.page.ts`.

`wizard.page.ts:41-47`: the comment becomes "Every filer answers Form 101 line 8 on the filing-fee page next (see IntakeWizard → /filing-fee), which continues to /sofa." The wait becomes `await this.page.waitForURL(/\/filing-fee/);`.

`personas.ts`:

- `PersonaData.expected` becomes `{ passes_means_test: boolean }`. `PersonaData` gains `filing_fee: PersonaFilingFee;` before `expected`.
- `PersonaFeeWaiver` and `WaiverPersonaData` (`:149-161`) are replaced by:

  ```ts
  /** Form 101 line 8, answered on the filing-fee page */
  export type PaymentChoice = 'pay_in_full' | 'installments' | 'waiver';

  /** 103B lines 4, 5, 7 and 9, answered under the waiver. Every persona answers No to 4, 7 and 9. */
  export interface PersonaWaiverAnswers {
    income_change_answer: 'no';
    installments_explanation: string;
    others_covered_answer: 'no';
    expense_change_answer: 'no';
  }

  /** What a persona answers on the filing-fee page (3f spec §10) */
  export interface PersonaFilingFee {
    payment_choice: PaymentChoice;
    waiver?: PersonaWaiverAnswers;
  }
  ```

- MARIA, DESHAWN and SARAH become `PersonaData`. Each `fee_waiver:` line, each `fee_waiver_eligible` and the comments at `:568-570` and `:819-820` go. The `filing_fee` values, with line 5 verbatim from §10:
  - MARIA `{ payment_choice: 'waiver', waiver: { income_change_answer: 'no', installments_explanation: "I support two children on what I earn. After rent, food, the car and the children's costs, there is not enough left each month to pay the fee, even in parts.", others_covered_answer: 'no', expense_change_answer: 'no' } }`
  - SARAH `{ payment_choice: 'waiver', waiver: { income_change_answer: 'no', installments_explanation: 'I have no savings. My pay covers rent, food and my bus pass, and what is left each month goes to bills I already owe.', others_covered_answer: 'no', expense_change_answer: 'no' } }`
  - DESHAWN and ANDRES `{ payment_choice: 'installments' }`.
  - JAMES and PRIYA `{ payment_choice: 'pay_in_full' }`.
  - The two line 5 texts are 157 and 117 characters (recounted for this plan), well under `installments_explanation`'s 520 (R10). Task 4's seed already stores the same texts.
- `PersonaData.expected` keeps only `passes_means_test`, and no `fee_waiver_eligible` is left in the file (R22).

- [ ] **Step 7: The journeys**

Every journey that presses Complete constructs `const filingFee = new FilingFeePage(page);` and imports it from `'../pages/filing-fee.page'`. Maria, Sarah and DeShawn's `FeeWaiverPage` import (`:14`) and constructor (`:24`) become these.

- **Maria.**
  - The header's `:4` becomes "Below-median single parent who asks for a fee waiver."
  - `:83-88` become "// Every filer answers Form 101 line 8 after Complete; Maria asks for the waiver (3f spec §10)" and `await filingFee.answer(MARIA.filing_fee.payment_choice, MARIA.filing_fee.waiver);`.
  - `:90-92`'s first sentence becomes "The filing-fee page continues to the SOFA step (DIG-149)."
  - `:97`'s comment becomes `// 14 forms + Form 103B (she asks for the waiver)`.
- **Sarah.**

  - `:4` becomes "Single, no assets, no dependents, asks for a fee waiver." `:39`'s comment drops ", fee waiver eligible".
  - `:51` becomes "// Means test preview — should indicate eligibility". `:57-60` (the "Fee waiver indication" lines) go.
  - After `completeIntake()`, `:82-87` become:

    ```ts
    // The page shows the court's limit and her own figure as information, never a verdict (§6.2)
    await filingFee.waitForLoad();
    await expect(filingFee.limitSentence(1, '$1,995.00')).toBeVisible();
    await expect(
      page.getByText(
        "Your family's income, as Form 103B counts it from your answers: $1,750.00 a month."
      )
    ).toBeVisible();
    await expect(page.locator('main')).not.toContainText(/qualif|eligib/i);
    await filingFee.answer(SARAH.filing_fee.payment_choice, SARAH.filing_fee.waiver);
    ```

  - `:89`'s first sentence and `:96`'s comment change as Maria's.

- **DeShawn.** `:81-88` become "// DeShawn pays in installments (3f spec §10), so Form 103B leaves his packet" and `await filingFee.answer(DESHAWN.filing_fee.payment_choice);`. `:90`'s first sentence changes as Maria's. The count Task 4 set (`:97-99`) stays.
- **Andrés.**
  - The header `:5-8` ends "…Schedule I line 8a. He pays the fee in installments, so his packet has no Form 103B."
  - The title `:21` becomes `'reaches his forms after choosing to pay in installments'`.
  - `:74-84` become `await filingFee.answer(ANDRES.filing_fee.payment_choice);`, `await sofa.waitForLoad();` and `await sofa.skipForNow();`, with "// He pays in installments; the page says where to get Form 103A, then continues to SOFA". The `page.goto('/sofa')` detour and its 30 s wait go.
  - `:86`'s comment becomes "// He pays in installments, so no Form 103B; below median, so no Form 122A-2".
- **James.** `:76-79` become "// James pays the fee in full, then the page continues to the SOFA step. This journey isn't about financial history, so skip SOFA to reach the forms dashboard. (The SOFA save path itself is covered by sofa-journey.spec.ts.)" and `await filingFee.answer(JAMES.filing_fee.payment_choice);`. `:83-84` become "// Forms generated (passes means test). James pays in full, so Form 103B is not in his packet."
- **Priya.** Import and construct the page object. `:81-84` become:

  ```ts
  // Every filer reaches the filing-fee page; Priya reads the court's limit and stops here
  await filingFee.waitForLoad();
  await expect(filingFee.limitSentence(4, '$4,125.00')).toBeVisible();
  const pageText = await page.textContent('body');
  expect(pageText?.toLowerCase()).not.toContain('error');
  ```

- **SOFA journey.** The header `:7-8` becomes "Uses James Washington, who pays the fee in full, so the filing-fee page continues to /sofa." `:93` becomes `await filingFee.answer(JAMES.filing_fee.payment_choice);` with "// James pays in full; the filing-fee page continues to /sofa". `:120`'s comment becomes `// James pays in full → 14 forms (no 103B)`.

- [ ] **Step 8: CLAUDE.md**

The two edits in Interfaces: the File Map line `:130`, and the page's sentences out of "The fee-waiver application".

- [ ] **Step 9: Gates and the journeys**

Check `uptime` first. Run the full suites and the journeys only while the 1-minute load is under 10, and the journeys only while the 5-minute load is also under 8.

- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 -q -p no:cacheprovider`. Expected: Task 4's totals plus one test, 0 failed, coverage ≥ 90%.
- `/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/` (ruff 0.8.5). Expected: `All checks passed!`.
- `cd backend && $PY manage.py check`. Expected: "System check identified no issues". There are no model changes, so neither `makemigrations --check` nor the `postgres` run applies.
- `cd frontend && NO_COLOR=1 npx vitest run --maxWorkers=2`. Expected: no failures. The count changes by: 17 page tests, one more App test, the wizard's two cases replacing its two tests, and 15 reading-level cases, less `FeeWaiverPage.test.tsx`'s 19.
- `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit`, `npm run lint`, `npm run format:check`. Expected: clean.
- `cd frontend && npx prettier --check "e2e/**/*.ts"` (ruling R23; `format:check` reaches only `src/`). Expected: "All matched files use Prettier code style!". On a failure, run `npx prettier --write "e2e/**/*.ts"` and check again.
- `/usr/bin/grep -rn -e feeWaiver -e FeeWaiver -e /fee-waiver -e fee_waiver_eligible frontend/src frontend/e2e`. Expected survivors, each with the task that removes it:

  - `App.tsx`'s redirect route and `App.test.tsx`'s `'Old links'` test. These stay for good (R21).
  - `client.ts`'s Fee Waiver section (`FeeWaiverPayload`, `FeeWaiverApplication`, `feeWaiverAPI`, `/intake/fee-waiver/`) and `feeWaiver: feeWaiverAPI,`, plus `handlers.ts`'s two `${API}/intake/fee-waiver/` handlers. Task 8 removes these (R25).
  - `FormDashboard.tsx`'s `'/fee-waiver'` `PAGE_LINK_LABELS` entry, and `FormDashboard.test.tsx`'s `/fee-waiver` refusal cases (`:593`, `:612`, `:949`, `:962`). Task 6 removes these (R12, R18).

  Anything else is unfinished work in this task. No pattern matches the shared classes `fee-waiver-question` and `fee-waiver-checkbox`, which have no slash. `qualifies_for_fee_waiver` is left for Task 7, and `fee_waiver_household_size` stays (R26).

- `zsh .claude/e2e.sh 2`. Expected: `RUN 1 exit=0: 8 passed` and `RUN 2 exit=0: 8 passed`. Packets: Maria 15, Sarah 15, DeShawn 14, Andrés 14, James 14, SOFA journey 14. Priya stops on the page. The scanned-bill journey never presses Complete and is unchanged. This is the first green journey run since Task 4. The Sarah and Priya limit checks read the 2026 poverty row. From 2027-02-01 the page shows `FEE_NO_TABLE` instead, and those checks fail until the 2027 row is loaded (R24).

On a failed run, read the trace under `frontend/test-results/` and check `uptime` before running again.

- [ ] **Step 10: Commit**

```bash
/usr/bin/git add frontend/src/pages/FilingFeePage.tsx frontend/src/pages/__tests__/FilingFeePage.test.tsx frontend/src/constants/filingFee.ts frontend/src/constants/copy.ts frontend/src/constants/formText.ts frontend/src/types/api.ts frontend/src/api/client.ts frontend/src/test/mocks/handlers.ts frontend/src/App.tsx frontend/src/App.test.tsx frontend/src/pages/IntakeWizard.tsx frontend/src/pages/__tests__/IntakeWizard.test.tsx frontend/src/styles/global.css frontend/e2e/pages/filing-fee.page.ts frontend/e2e/pages/wizard.page.ts frontend/e2e/fixtures/personas.ts frontend/e2e/journeys/maria-happy-path.spec.ts frontend/e2e/journeys/sarah-simplest.spec.ts frontend/e2e/journeys/deshawn-assets.spec.ts frontend/e2e/journeys/andres-gig-driver.spec.ts frontend/e2e/journeys/james-borderline.spec.ts frontend/e2e/journeys/priya-ineligible.spec.ts frontend/e2e/journeys/sofa-journey.spec.ts backend/apps/intake/tests/test_filing_fee_frontend_copy.py CLAUDE.md
/usr/bin/git rm frontend/src/pages/FeeWaiverPage.tsx frontend/src/pages/__tests__/FeeWaiverPage.test.tsx frontend/e2e/pages/fee-waiver.page.ts
/usr/bin/git commit -F /tmp/3f-task5-msg.txt
```

The message (`/tmp/3f-task5-msg.txt`), with no trailer:

```
feat(intake): ask every filer how they will pay the filing fee

Complete now always opens /filing-fee, which asks Form 101 line 8 in
the form's words. Beside it, as information, the page shows the court's
150% poverty limit for the filer's family and their own 103B line 2
figure, and says the court decides. Under the waiver it asks 103B
lines 4, 5, 7 and 9; under installments it says where to get Form 103A.
The fee-waiver page goes, /fee-waiver redirects, and every journey
answers the page.
```

---

### Task 6: The dashboard shows how the filer will pay the fee

**Spec:** §3 ("The way back"), §6.3 (the 103A notice on the dashboard), §7 ("The dashboard"), §12 ("GenerateAll vs single"), §16 calls 12 and 19.

Line numbers are as of `dc31b7a`. Task 4 adds one `PAGE_LINK_LABELS` line (`FormDashboard.tsx`, after `:59`) and Task 5 adds a "Filing fee" section to `types/api.ts` (after `:452-473`) and `filingFee` to `intakeAPI` in `client.ts` (`:342-456`), so in those files find each block by the name given beside its number.

**Files:**

- Modify: `frontend/src/types/api.ts:697-710` (`FormPacketResponse`, `Packet`)
- Modify: `frontend/src/api/client.ts:595-602` (`formsAPI.packet`, the explicit mapper)
- Modify: `frontend/src/test/mocks/handlers.ts:55` (the `mockPacket` comment) and `:240-242` (the packet handler)
- Modify: `frontend/src/pages/FormDashboard.tsx`: imports `:18`, `:22-28`; `PAGE_LINK_LABELS` `:57-62` (delete the `/fee-waiver` line only); state beside `:119`; the setter sites `:145`, `:148`, `:211`, `:214`; the JSX after the income window notice `:409-416`
- Modify: `frontend/src/constants/copy.ts`, the "Form Dashboard Copy" section (`:69-79`)
- Test: `frontend/src/pages/__tests__/FormDashboard.test.tsx`: the imports (`:1-7`); a new `describe('how the filer will pay the fee')` after `describe('the income window notice')` (`:228-300`); `:584-616` (`'names each page that fixes a form Generate All refused'`); `:939-963` (`'links a form whose Generate was refused to the page that fixes it'`)
- Modify: `CLAUDE.md`, the gotcha "GenerateAll vs single" (`:37` at `dc31b7a`; find it by name)

**Interfaces:**

- Consumes:
  - Task 4: the packet reply's `payment_choice` (`"pay_in_full" | "installments" | "waiver" | null`), present on every successful reply and absent from a refusal (a refusal is `{error, step?, page?}` as today, ruling R17).
  - Task 4: refusals carrying `page: "/filing-fee"` (`PreconditionMissing.page`, the `FilingFee` text rules' `RULE_FIXES`), and `PAGE_LINK_LABELS['/filing-fee'] = 'Go to How you will pay the filing fee'`, which Task 4 adds beside the `/fee-waiver` line (ruling R12).
  - Task 4: "GenerateAll vs single" already reads "returns `{session, form_types, tables, income_period, payment_choice}` in filing order" and "; `payment_choice` is the Form 101 line 8 answer, or null before the filer chooses" (Task 4 Step 10, ruling R13).
  - Task 5 (ruling R16): `PaymentChoice` (`types/api.ts`); the route `/filing-fee`; from `constants/formText.ts`, `LINE_8_LABEL = 'How you will pay the fee'` and `PAYMENT_CHOICE_WORDS: Record<PaymentChoice, string>` (the field index's `option_text` for `Check Box7`: "I will pay the entire fee when I file my petition.", "I need to pay the fee in installments.", "I request that my fee be waived", no period); from `constants/copy.ts`, `INSTALLMENTS_NOTICE` (§6.3's three sentences) and `FORM_103A_LINK` (the link's words); `FORM_103A_URL` (`'https://www.uscourts.gov/forms-rules/forms/application-individuals-pay-filing-fee-installments-0'`), which Task 5 puts in `constants/filingFee.ts`.
- Produces:
  - `FormPacketResponse.payment_choice?: PaymentChoice | null` (optional, as `income_period?` beside it is, since a test's packet reply may leave it out).
  - `Packet.payment_choice: PaymentChoice | null`. The mapper sends `response.payment_choice ?? null`.
  - `PAGE_LINK_LABELS` without its `/fee-waiver` entry. This task adds no `/filing-fee` entry (Task 4's is there).
  - `copy.ts`, in "Form Dashboard Copy": `FILING_FEE_CHANGE_LINK = 'Change how you will pay the fee'` and `FILING_FEE_CHOOSE_LINK = 'Choose how you will pay the fee'`.
  - The dashboard's answer block: `<section className="form-dashboard-notice" aria-label={LINE_8_LABEL}>`, its role `region`, named "How you will pay the fee".
- CLAUDE.md: "GenerateAll vs single", two sentences, as they read after this task (Step 7).

**Decided here:**

- **The names this task imports from Task 5 are ruling R16's**, plus `LINE_8_LABEL`, which Task 5 already puts in `formText.ts` for the page's legend. The dashboard uses that constant for its block's name rather than adding a second constant with the same words. If Task 5 landed any of these under another name or in another file, this task imports Task 5's name from Task 5's file and changes nothing in Task 5's files; the ledger says so. In its current draft, Task 5 has no `INSTALLMENTS_NOTICE` string: it ships `Form103ANotice` (`components/forms/Form103ANotice.tsx`, no props, exported from `components/forms`) built from `FORM_103A_LEAD`, `FORM_103A_TITLE` and `FORM_103A_REST`. If Task 5 lands that way, the dashboard renders `<Form103ANotice />` in place of the notice `<p>` in Step 4 and doesn't import `INSTALLMENTS_NOTICE`, `FORM_103A_LINK` or `FORM_103A_URL`. The tests stand as written: `getByText` with a regex matches the notice's `<p>` across its `<em>`, and the link keeps its name and `href`.
- **`PAGE_LINK_LABELS`: delete, don't add** (ruling R12). Task 4 adds `/filing-fee`, since `test_every_fix_is_a_step_or_page_the_dashboard_links` (`test_rule_fixes.py:117-145`) reads the map. This task deletes `/fee-waiver`, whose last `RULE_FIXES` pages (`derivations.py:1081-1083`) Task 2 removed. The two existing tests that name `/fee-waiver` are rewritten for `/filing-fee`. They pass before and after this task's change, so they are not this task's failing-first tests. The failing-first tests are the answer block's.
- **No answer block without a packet reply.** A refused packet carries no `payment_choice` (ruling R17), so the dashboard can't tell "unanswered" from "unknown". The state is `PaymentChoice | null | undefined`: `undefined` until a reply arrives and after a refusal, and then no block shows. Showing "Choose how you will pay the fee" beside a refusal would tell a filer who has answered to answer again. This follows `incomePeriod` (`:148`, `:214`), which a refusal clears for the same reason.
- **Where it sits.** After the median table notices and the income window notice (`:403-416`), before the cards: it is about the packet, and 103B's card below depends on it.
- **The link isn't deduplicated** through `linksInPageOrder`, like the income window's link (3e2 Task 11): it always shows, and a refusal linking to `/filing-fee` names a different action in different words.
- **The words.** The heading is Form 101 line 8's label (`LINE_8_LABEL`, `formText.ts`, unscored). The two link sentences are DigniFi's and go in `copy.ts`, where `reading-level.test.ts` scores them (7 words each, all short, far under grade 9). They are not §6.2 or §6.4 sentences, so they carry no `DRAFT: counsel C-7`. The notice is Task 5's `INSTALLMENTS_NOTICE` and link, so the page and the dashboard show the same notice (§6.3).
- **The packet sentence in CLAUDE.md** (ruling R13). Task 4 adds the key and "`payment_choice` is the Form 101 line 8 answer, or null before the filer chooses". This task adds the dashboard's use of it to that clause, and names `/filing-fee` in the link sentence's list of pages.
- **The default MSW packet** carries `payment_choice: 'pay_in_full'`, the 14-form packet's answer. Every existing screen-wide link query in `FormDashboard.test.tsx` names its link ("Finish your intake", "Go to Income", "Go to Your Information"), and `getAllByRole('link')` without a name runs only inside `within(alert)`, so the new link changes none of them. `accessibility.test.tsx:224` renders the dashboard with this default and so checks the block with axe.
- **The backend gates run** though no backend file changes: `test_rule_fixes.py` reads `PAGE_LINK_LABELS` from `FormDashboard.tsx` (`:37-42`).

- [ ] **Step 1: Write the failing tests**

In `FormDashboard.test.tsx`, after `describe('the income window notice')` (ends `:300`):

```tsx
describe('how the filer will pay the fee', () => {
  // Form 101 line 8's words, typed out (the field index's option_text for Check Box7)
  const PAY_IN_FULL = 'I will pay the entire fee when I file my petition.';
  const INSTALLMENTS = 'I need to pay the fee in installments.';
  const WAIVER = 'I request that my fee be waived';

  function packetWith(paymentChoice?: unknown) {
    server.use(
      http.get('http://localhost:8000/api/forms/packet/', () =>
        HttpResponse.json({
          session: 1,
          form_types: ['form_101', 'form_121'],
          tables: [],
          ...(paymentChoice === undefined ? {} : { payment_choice: paymentChoice }),
        })
      )
    );
  }

  async function answerBlock() {
    return screen.findByRole('region', { name: 'How you will pay the fee' });
  }

  it('shows the filer’s line 8 answer in the form’s words, with a link to change it', async () => {
    packetWith('pay_in_full');
    renderFormDashboard();

    const block = await answerBlock();
    expect(within(block).getByText(PAY_IN_FULL)).toBeInTheDocument();
    expect(
      within(block).getByRole('link', { name: 'Change how you will pay the fee' })
    ).toHaveAttribute('href', '/filing-fee');
    expect(within(block).queryByRole('link', { name: /^Choose/ })).not.toBeInTheDocument();
  });

  it('asks a filer who has not answered line 8 to choose, and shows no answer', async () => {
    packetWith(null);
    renderFormDashboard();

    const block = await answerBlock();
    expect(
      within(block).getByRole('link', { name: 'Choose how you will pay the fee' })
    ).toHaveAttribute('href', '/filing-fee');
    expect(within(block).queryByRole('link', { name: /^Change/ })).not.toBeInTheDocument();
    for (const words of [PAY_IN_FULL, INSTALLMENTS, WAIVER]) {
      expect(within(block).queryByText(words)).not.toBeInTheDocument();
    }
  });

  it('tells a filer paying in installments to get Form 103A from the court', async () => {
    packetWith('installments');
    renderFormDashboard();

    const block = await answerBlock();
    expect(within(block).getByText(INSTALLMENTS)).toBeInTheDocument();
    expect(within(block).getByText(/DigniFi doesn't prepare Form 103A yet\./)).toBeInTheDocument();
    expect(within(block).getByRole('link', { name: FORM_103A_LINK })).toHaveAttribute(
      'href',
      FORM_103A_URL
    );
  });

  it.each([
    ['waiver', WAIVER],
    ['pay_in_full', PAY_IN_FULL],
  ])('shows no Form 103A notice for the answer %s', async (choice, words) => {
    packetWith(choice);
    renderFormDashboard();

    const block = await answerBlock();
    expect(within(block).getByText(words)).toBeInTheDocument();
    expect(screen.queryByText(/Form 103A/)).not.toBeInTheDocument();
  });

  // Guard (ruling R29): passes before the change; it keeps a block from showing beside a refusal
  it('shows no answer, and no link to choose, when the packet is refused', async () => {
    server.use(
      http.get('http://localhost:8000/api/forms/packet/', () =>
        HttpResponse.json(
          { error: 'Enter your income by source on the Income step.', step: 'income_info' },
          { status: 422 }
        )
      )
    );
    renderFormDashboard();

    await screen.findByText('Enter your income by source on the Income step.');
    expect(
      screen.queryByRole('region', { name: 'How you will pay the fee' })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: /how you will pay the fee/ })
    ).not.toBeInTheDocument();
  });

  it('shows the answer the packet holds after Generate All reloads it', async () => {
    // The filer changed line 8 on /filing-fee in another tab; Generate All reloads the packet
    let calls = 0;
    server.use(
      http.get('http://localhost:8000/api/forms/packet/', () => {
        calls += 1;
        return HttpResponse.json({
          session: 1,
          form_types: calls === 1 ? ['form_101', 'form_103b'] : ['form_101', 'form_121'],
          tables: [],
          payment_choice: calls === 1 ? 'waiver' : 'installments',
        });
      })
    );
    renderFormDashboard();
    expect(within(await answerBlock()).getByText(WAIVER)).toBeInTheDocument();

    await userEvent.click(await screen.findByRole('button', { name: /generate all/i }));
    await userEvent.click(screen.getByRole('checkbox'));
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));

    expect(await within(await answerBlock()).findByText(INSTALLMENTS)).toBeInTheDocument();
    expect(screen.queryByText(WAIVER)).not.toBeInTheDocument();
  });
});
```

The file gains, beside its imports (`:1-7`):

```tsx
import { FORM_103A_LINK } from '../../constants/copy';
import { FORM_103A_URL } from '../../constants/filingFee';
```

The three option words are typed out, not imported, so a test fails if `PAYMENT_CHOICE_WORDS` drifts from Form 101's words (§6.1). The waiver's words have no period, as the form prints them (ruling R16).

Existing tests, rewritten for the page that replaced `/fee-waiver`:

- `:584-586`'s comment: "the fee-waiver rules" becomes "the filing-fee answers".
- `:593`: `{ form_type: 'form_103b', error: TOO_LONG, page: '/filing-fee' },`.
- `:612`: `['Go to How you will pay the filing fee', '/filing-fee'],`.
- `:939-963`, `'links a form whose Generate was refused to the page that fixes it'` (ruling R18):

  - the comment `:940` becomes `// Line 7's "Identify who" is a filing-fee answer, which feeds Form 103B (Task 4)`;
  - `TYPE_TOO_LONG` (`:941-942`) becomes `WHO_TOO_LONG = '“Identify who” is too long to fit on the court form, even in small print. Shorten it.'` (`ValueTooLong`'s sentence, `pdf_filler.py:117-119`, with the field index's label for `undefined_8`). `3 type` now links to `income_info` (Task 2), so "Type of assistance" no longer names this page;
  - `:949` `page: '/filing-fee'`, `:959` `WHO_TOO_LONG`, `:961` `{ name: 'Go to How you will pay the filing fee' }`, `:962` `'/filing-fee'`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run --maxWorkers=2 src/pages/__tests__/FormDashboard.test.tsx`

Expected: FAIL, in the new `describe` only.

- Every case but the refusal guard: `findByRole('region', { name: 'How you will pay the fee' })` times out, since no such block exists.
- The refusal guard passes (it asserts an absence; ruling R29).
- The two rewritten tests pass: Task 4's `/filing-fee` entry already gives their links. They are rewritten now because Step 4 deletes `/fee-waiver`.
- If an import fails to resolve, Task 5 named or placed a constant otherwise: fix the import per "Decided here" and run again.

- [ ] **Step 3: Implement the packet's `payment_choice`**

- `types/api.ts`: `PaymentChoice` is declared in this file by Task 5, so no import. Add `payment_choice?: PaymentChoice | null;` to `FormPacketResponse` with the doc comment `/** Form 101 line 8: the filer's answer, null until they choose (forms step 3f §7) */`, and `payment_choice: PaymentChoice | null;` to `Packet`.
- `client.ts` `packet`: add `payment_choice: response.payment_choice ?? null,` after `income_period`.
- `handlers.ts`:

  - `:55` comment: `/** A below-median filer who pays the fee in full: the 14 forms every packet holds */`;
  - `:241`: `HttpResponse.json({ session: 1, form_types: mockPacket, tables: [], payment_choice: 'pay_in_full' })`.

- [ ] **Step 4: Implement the dashboard**

- `PAGE_LINK_LABELS`: delete `'/fee-waiver': 'Go to Filing Fee Waiver Application',`. Task 4's `'/filing-fee'` line stays as it is.
- `copy.ts`, in "Form Dashboard Copy" after `DASHBOARD_EMPTY`: `FILING_FEE_CHANGE_LINK` and `FILING_FEE_CHOOSE_LINK` (Interfaces), each `export const` with a blank line between, as the section's entries are.
- `FormDashboard.tsx`:

  - Imports: `PaymentChoice` added to the type import from `../types/api` (`:22-28`); `LINE_8_LABEL` and `PAYMENT_CHOICE_WORDS` from `../constants/formText`; `FILING_FEE_CHANGE_LINK`, `FILING_FEE_CHOOSE_LINK`, `INSTALLMENTS_NOTICE` and `FORM_103A_LINK` added to the `../constants/copy` import (`:18`); `FORM_103A_URL` from `../constants/filingFee`.
  - State after `:119`: `// Form 101 line 8, as the packet reply holds it; undefined while no reply has come (a refusal carries none)` then `const [paymentChoice, setPaymentChoice] = useState<PaymentChoice | null | undefined>(undefined);`.
  - `setPaymentChoice(loadedPacket.payment_choice);` after `:145`, `setPaymentChoice(reloaded.payment_choice);` after `:211`, and `setPaymentChoice(undefined);` after each `setIncomePeriod(null);` (`:148`, `:214`).
  - After the income window notice (`:409-416`):
    ```tsx
    {
      paymentChoice !== undefined && (
        <section className="form-dashboard-notice" aria-label={LINE_8_LABEL}>
          {paymentChoice && (
            <p>
              {LINE_8_LABEL}: <span>{PAYMENT_CHOICE_WORDS[paymentChoice]}</span>
            </p>
          )}
          {paymentChoice === 'installments' && (
            <p>
              {INSTALLMENTS_NOTICE}{' '}
              <a href={FORM_103A_URL} target="_blank" rel="noreferrer">
                {FORM_103A_LINK}
              </a>
            </p>
          )}
          <Link to="/filing-fee" className="button button--primary">
            {paymentChoice ? FILING_FEE_CHANGE_LINK : FILING_FEE_CHOOSE_LINK}
          </Link>
        </section>
      );
    }
    ```
    The answer's words sit in their own `<span>` so the tests' exact-string `getByText` finds them apart from the label. `/DigniFi doesn't prepare Form 103A yet\./` matches the notice's `<p>` by part of its text, which a regex allows.
  - No CSS: `.form-dashboard-notice` (`global.css:1448-1450`, a bottom margin) already styles the dashboard's blocks of a paragraph and a button link (`FormDashboard.tsx:296-306`, `:409-416`).

- [ ] **Step 5: Run the tests to verify they pass**

Run: the Step 2 command, then `cd frontend && npx vitest run --maxWorkers=2 src/test/reading-level.test.ts src/test/accessibility.test.tsx`.

Expected: PASS. The reading-level run scores the two new link sentences; the accessibility run checks the dashboard with the block shown.

- [ ] **Step 6: Confirm no old link words remain**

Run: `/usr/bin/grep -rn "Filing Fee Waiver Application'\|'/fee-waiver'" frontend/src/pages/FormDashboard.tsx frontend/src/pages/__tests__/FormDashboard.test.tsx`

Expected: no output. (`FORM_TYPE_METADATA`'s card label "Form 103B - Fee Waiver Application" is the form's name and stays.)

- [ ] **Step 7: Update `CLAUDE.md`**

In "GenerateAll vs single" (find it by name), after this task:

- The link sentence's parenthesis, "(`PAGE_LINK_LABELS` in `FormDashboard.tsx`, or, for `/ask/<form type>`, that form type's label in `FORM_TYPE_METADATA`)", reads "(`PAGE_LINK_LABELS` in `FormDashboard.tsx`: `/intake`, `/filing-fee`, `/sofa` and `/documents`; or, for `/ask/<form type>`, that form type's label in `FORM_TYPE_METADATA`)". The rest of the sentence is unchanged.
- The packet sentence, which Task 4 left with the key and its first clause, reads: "`GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables, income_period, payment_choice}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; `income_period` is `{answered_for, now}`: `answered_for` is the six months the filer last confirmed by Continue on the Income step (null before they have) and `now` is the six months before the fill date's month, and the dashboard shows a notice linking to the Income step while the two differ (none when a refusal replaces the reply); `payment_choice` is the Form 101 line 8 answer, or null before the filer chooses, and the dashboard shows it in the form's words with a link to `/filing-fee`, "Change how you will pay the fee" or, while null, "Choose how you will pay the fee", and, for `installments`, the filing-fee page's Form 103A notice (no block when a refusal replaces the reply); the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet"." If Task 4's wording of its clause differs, keep Task 4's words for the key and its values and add this task's from "and the dashboard shows it".

- [ ] **Step 8: Gates**

`$PY` comes from `.claude/forms-step3f.env` ("Before you start").

- Check `uptime`; run the full suites only with the 1-minute load under 10.
- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 -q -p no:cacheprovider` (`test_rule_fixes.py` reads `PAGE_LINK_LABELS`)
- `/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/` (ruff 0.8.5)
- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY manage.py check`
- `cd frontend && npx vitest run --maxWorkers=2`
- `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit` (never `tsc -b`)
- `cd frontend && npm run lint && npm run format:check`

Expected: all pass. No model, migration or lock entry, so no `makemigrations --check` and no `postgres` run. The journeys don't run in this task (Global Constraints: Tasks 1, 5, 8 and 9).

- [ ] **Step 9: Commit**

```bash
/usr/bin/git add frontend/src/types/api.ts frontend/src/api/client.ts frontend/src/test/mocks/handlers.ts frontend/src/pages/FormDashboard.tsx frontend/src/pages/__tests__/FormDashboard.test.tsx frontend/src/constants/copy.ts CLAUDE.md
/usr/bin/git commit -F /tmp/3f-task6-msg.txt
```

The message, written to `/tmp/3f-task6-msg.txt`, with no trailer:

```
feat(forms): show how the filer will pay the fee on the dashboard

The packet reply's payment_choice reaches the dashboard, which shows
the Form 101 line 8 answer in the form's words with a link to change
it, or to choose while it is unanswered, and the Form 103A notice for
installments. The old fee-waiver page's link words go.
```

---

### Task 7: The means test's fee-waiver flag goes

**Spec:** §9 (the whole section), §13 ("the means test result, the summary and the preview carry no fee-waiver verdict"), §15 item 6, §16 call 15. `[DIG-145]` `[UPL]`

Line numbers are at `dc31b7a`. Other tasks edit some of the same files: `test_seed_demo_data.py` and `seed_demo_data.py` (Tasks 4 and 8), `test_api_readback.py` (Tasks 4 and 8), `handlers.ts` and `types/api.ts` (Tasks 5 and 6), `docs/REFERENCE_TABLES.md` (Task 1) and `CLAUDE.md`. Find each edit by its content and use the line number only as a guide.

**Files:**

- Modify: `backend/apps/eligibility/models.py:96-97` (the field and its comment), `:186-188` (the computation), `:226` (the `calculation_details` key), `:236` (the assignment)
- Create: `backend/apps/eligibility/migrations/0003_remove_meanstest_qualifies_for_fee_waiver.py`
- Modify: `backend/apps/eligibility/services/means_test_calculator.py:57` (docstring), `:98` (result key), `:146-152` (the blank line and the message's sentence), `:192` (docstring), `:221` (breakdown key)
- Modify: `backend/apps/intake/views.py:349` (the `calculate_means_test` docstring), `:416-419` (the summary's `means_test`)
- Modify: `backend/apps/intake/management/commands/seed_demo_data.py:60`, `:521`, `:604` (persona docstrings), `:924-926` (the application branch's comment and condition only)
- Create: `backend/apps/eligibility/tests/test_migrations.py`
- Test: `backend/apps/eligibility/tests/test_means_test_calculator.py:9-10` (module docstring), `:376-449` (`TestFeeWaiverQualification`, `TestFeeWaiverNonQualification`), `:518-535`, `:728-729`, `:774-776`, `:799`
- Test: `backend/apps/eligibility/tests/test_household_means_test.py:167-173`
- Test: `backend/apps/intake/tests/test_e2e_intake.py:713`, `:768-779`
- Test: `backend/apps/audit/tests/test_upl_compliance.py:269-285`, `:315`, `:451`
- Test: `backend/apps/intake/tests/test_seed_demo_data.py:197-209` (the test's name and the flag assertion)
- Test: `backend/apps/forms/tests/test_api_readback.py:27` (the `MeansTest` import), `:36-38` (`QUALIFIES` and its comment), `:180-183` (the flag assertion and its comment)
- Modify: `frontend/src/types/api.ts:460` (`MeansTestResult.qualifies_for_fee_waiver`), `:721` (`SessionSummaryResponse.means_test.qualifies_fee_waiver`)
- Modify: `frontend/src/components/wizard/MeansTestPreview.tsx:120-125` (the "Fee Waiver" row)
- Modify: `frontend/src/styles/global.css:878-882` (`.means-test-preview-detail--highlight`, used only by that row)
- Modify: `frontend/src/test/mocks/handlers.ts:75`, `frontend/src/test/fixtures/session.ts:135`
- Test: `frontend/src/components/wizard/__tests__/MeansTestPreview.test.tsx:62`, plus one new test in `describe('MeansTestPreview with an estimate')`
- Modify: `docs/REFERENCE_TABLES.md:14` (the median no longer decides the fee-waiver offer, R2) and `:4` (the header date)
- Modify: `CLAUDE.md` ("Means test units")
- Not touched (R22, Task 5's): `frontend/e2e/fixtures/personas.ts`, `frontend/e2e/journeys/*.spec.ts`, `frontend/src/pages/__tests__/IntakeWizard.test.tsx`, the File Map line `CLAUDE.md:130`

**Interfaces:**

- Consumes:
  - Task 5:
    - `handleComplete` no longer reads `result.qualifies_for_fee_waiver` (`IntakeWizard.tsx:500-504` at `dc31b7a`), and `FeeWaiverPage.tsx` (`:70`) is deleted. If either still stands, `tsc` fails in Step 9.
    - `FeeWaiverPage.test.tsx` (`:45`) is deleted. Test files are outside `tsconfig.app.json`, so a leftover there shows only in Step 7's grep.
    - The `IntakeWizard.test.tsx` routing tests become Task 5's `it.each([true, false])` test, whose untyped MSW reply sends `qualifies_for_fee_waiver: flag` on purpose. This task leaves it alone (R22).
    - `personas.ts` has no `fee_waiver_eligible`, the James and SOFA journey comments are rewritten, and the File Map line `CLAUDE.md:130` no longer names the flag (R22).
    - Any of these still standing means Task 5 is unfinished. Task 7 records it in the ledger and does not take over the edit.
  - Task 4: the seed writes each persona's `FilingFee` and has dropped DeShawn's `fee_waiver` dict (R15), so only Maria and Sarah keep one. `test_seed_demo_data.py`'s packet assertion says DeShawn has no 103B, and the seed test still asserts `qualifies_for_fee_waiver` for this task to delete. Task 4 also rewrites `test_api_readback.py`'s `APPLIES`.
  - Task 1: `docs/REFERENCE_TABLES.md` has its poverty section and a new header date, and `:14` is unchanged (R2).
  - Task 6: `handlers.ts:55`'s `mockPacket` comment. This task leaves it alone.
- Produces:
  - `MeansTest` has no `qualifies_for_fee_waiver`. It is dropped by `eligibility/0003_remove_meanstest_qualifies_for_fee_waiver`, which depends on `("eligibility", "0002_add_above_median_fields")` and holds one `RemoveField`.
  - `MeansTest.calculate()`'s `calculation_details` has no `qualifies_fee_waiver` key.
  - `MeansTestCalculator.calculate()` returns exactly these keys: `passes_means_test`, `cmi`, `median_income_threshold`, `family_size`, `message`, `details`, `means_test_id`, `above_median_calculated`, `disposable_income`, `total_allowable_expenses`, `priority_debts_monthly`, `passes_above_median`.
  - `get_detailed_breakdown()["results"]` is `{"passes_means_test", "statute_citation"}`.
  - The at-or-below-median message is today's three sentences (`:139-145`), with nothing added to them.
  - `GET /api/intake/sessions/{id}/summary/`: when a means test exists, `means_test` is `{"passes": bool}`.
  - Frontend: `MeansTestResult` has no `qualifies_for_fee_waiver`, and `SessionSummaryResponse.means_test` is `{ passes: boolean }`. The preview shows two rows: the income and the median.
  - `docs/REFERENCE_TABLES.md:14` says the median decides 122A-2 only.
  - `ASSERTED_CASES` is unchanged, a delta of 0: no binding moves.
- CLAUDE.md: "Means test units" changes, in Step 8. That gotcha is the one that lists what `calculation_details` holds. No other gotcha names the flag. The one other mention, the File Map at `CLAUDE.md:130` ("`handleComplete` routes to one or the other on `qualifies_for_fee_waiver`"), is Task 5's (R22).

**Decided here:**

- **The seed's application branch keeps running until Task 8.**
  - `seed_demo_data.py:926` reads `result["qualifies_for_fee_waiver"]`. Once the key goes, that read raises `KeyError` in every seed run and in `test_seed_demo_data.py`. The frame's Task 7 boundary doesn't list it.
  - The condition becomes `if "fee_waiver" in data:` (R19). After Task 4 only Maria and Sarah have that dict (R15), and the flag was True for both (`test_seed_demo_data.py:207-209`), so the seed creates the same two applications as Task 4 left, matching its `{"demo_maria": 3, "demo_sarah": 1}`.
  - Task 8 deletes the branch and the dicts.
  - The three persona docstrings that state the flag's verdict ("fee waiver eligible", "Qualifies for a fee waiver") are rewritten to name the person's Form 101 line 8 answer (§10). They state the removed result, and the seed is already open in this task.
- **`test_api_readback.py`'s `QUALIFIES` goes here (R20).**
  - Its assertion (`:182-183`) reads the dropped column, which is an `AttributeError`.
  - `APPLIES` is Task 4's and the `_fee_waiver_application` helper and POST are Task 8's. This task deletes the constant, its comment, the assertion and its comment.
  - `MeansTest` is imported only for that assertion (`:27`, used once at `:182`), so the import goes too, or ruff F401 fails.
- **The journeys, `personas.ts` and the wizard's routing test are Task 5's (R22).** The frame's task list gives Task 7 "the James and SOFA journey comments", and the spec (§9) lists them and `IntakeWizard.test.tsx:147`, `:174`. R22 moves all of them, with `fee_waiver_eligible` and the File Map line, to Task 5, which edits those lines anyway. This task only checks, in Step 7, that they are gone.
- **`REFERENCE_TABLES.md:14` changes here (R2).** It says the median decides "whether the filer is offered the fee-waiver application". That offer ran on this flag, which this task removes, so the doc changes with it. The sentence keeps its 122A-2 clause. Task 1 has already moved the header date; this task moves it again only if its commit falls on a later day.
- **Old rows keep the key in their stored details. No data migration removes it.**
  - `calculate()` builds `details` from `{}` on every run (`models.py:151`), and every forms call works the means test out again first (`_recalculate_means_test`). So a session's next calculation drops the key.
  - Nothing reads `calculation_details["qualifies_fee_waiver"]`. The only readers of `get_calculation_details()` are the calculator, which returns `details` whole, and the packet's `tables`, which reads `median_table`.
  - A migration that decrypts and rewrites every `MeansTest` row to remove a key nothing reads isn't worth it.
- **Old copy stays readable.** A reply from an old server can still carry the key, and the preview ignores it. The new preview test sends `qualifies_for_fee_waiver: true` on purpose. That is the only way the test fails before the change: the row renders only when the key is true.
- **The migration test lives in a new `apps/eligibility/tests/test_migrations.py`.**
  - It has its own `migrate` fixture and `ON_POSTGRES`, copied from `apps/intake/tests/test_data_migrations.py:45-61`, `:418-421`, as Task 1's `test_poverty.py` does.
  - The intake file is where Tasks 3 and 8 append their tests, and its fixture names intake in its docstring.
  - The session and district are created with the current models, since only the eligibility app moves.
- **Which hits the grep allows.** After this task the identifiers `qualifies_for_fee_waiver` and `qualifies_fee_waiver` may appear only in these places:

  - `eligibility/migrations/0001_initial.py` and `0003_…`;
  - this task's absence assertions and `test_migrations.py`;
  - the preview test's old-server reply;
  - Task 5's `IntakeWizard.test.tsx` routing test, whose untyped reply sends the key to prove nothing routes on it;
  - `docs/internal/DigniFi_PRD_v0_3.md:398`, a June history line this plan doesn't edit;
  - `docs/superpowers/`.

  Task 9's final grep needs the same exclusions (R21 lists all but the wizard test's reply).

- **The CLAUDE.md sentence names no removed identifier.** It says in words that the means test gives no fee-waiver verdict, so Step 7's grep and Task 9's sweep, which read `CLAUDE.md`, find nothing in it.
- **No test name says "qualify" or "eligible"** (Global Constraints, "No verdict"). So `TestFeeWaiverQualification`, `TestFeeWaiverNonQualification` and `test_deshawn_still_qualifies_for_the_fee_flag_on_both_incomes` are renamed or replaced. The DeShawn test keeps its CMI assertion, which pins his household's CMI on both incomes; its comment on the 60% line goes.
- **Every absence assertion here fails first** (R29). Each sits in a test that fails before Step 3 on that assertion or a neighbour (Step 2 lists them), so none needs a guard label.
- **The emptied CSS rule goes.** `.means-test-preview-detail--highlight` (`global.css:878-882`) has no other user (`grep -rn "detail--highlight" frontend/src`), so the row's removal leaves it dead.
- **What the spec overstates.** `MeansTestPreview.test.tsx` never asserted the row: only its `:62` mock carries the key. The new test is the first to pin the row's absence.

- [ ] **Step 1: Write the failing backend tests**

**`backend/apps/eligibility/tests/test_means_test_calculator.py`.**

Make these changes:

- The module docstring's two lines at `:9-10` ("Fee waiver qualification …", "Fee waiver non-qualification …") become one line: `- No fee-waiver verdict at any income: the result, its details, the breakdown and the message carry none (3f spec §9)`.
- Delete both classes at `:376-449`.
- In their place, add:

```python
@pytest.mark.django_db
class TestNoFeeWaiverVerdict:
    """The means test answers § 707(b) only. Whether the fee is waived is the court's, under
    § 1930(f), and the filing-fee page shows its 150% figure as information (3f spec §6.2, §9).
    The old 60%-of-median flag was never that test, so no income gets a fee-waiver verdict."""

    @pytest.mark.parametrize("wages", ["0.00", "1500.00", "3000.00", "3565.20", "4166.67"])
    def test_no_income_gets_a_fee_waiver_verdict_from_the_means_test(
        self, session, median_income, wages
    ):
        _income(
            session=session,
            marital_status="not_married",
            monthly_gross_wages=Decimal(wages),
        )
        calculator = MeansTestCalculator(session)

        result = calculator.calculate()

        assert result["cmi"] == Decimal(wages)
        assert result["passes_means_test"] is True  # every figure is under the $5,942 median
        assert "qualifies_for_fee_waiver" not in result
        assert "qualifies_fee_waiver" not in result["details"]
        assert "qualifies_for_fee_waiver" not in calculator.get_detailed_breakdown()["results"]
        assert "fee waiver" not in result["message"].lower()
        assert "1930" not in result["message"]

    def test_a_means_test_row_stores_no_fee_waiver_verdict(self):
        assert "qualifies_for_fee_waiver" not in {f.name for f in MeansTest._meta.get_fields()}
```

Then change these existing tests:

- `test_fee_waiver_message_contains_no_upl_violations` (`:518-535`) becomes `test_a_very_low_income_message_contains_no_upl_violations`.
  - Its docstring is `"""The message a filer far below the median sees contains no UPL prohibited phrase."""`.
  - Its assertion text is `found in the message: {message}`.
  - Its body is otherwise unchanged.
- `test_detailed_breakdown_after_calculation`:
  - Its comment (`:728-729`, two lines) becomes `# $5,000/month = $60,000/year: below the $71,304 median (passes)`.
  - Its three `results` assertions (`:774-776`) become one: `assert breakdown["results"] == {"passes_means_test": True, "statute_citation": "11 U.S.C. § 707(b)"}`.
- `test_high_monthly_income_fails_after_annualization`: delete `:799` (`assert result["qualifies_for_fee_waiver"] is False`).

**`backend/apps/eligibility/tests/test_household_means_test.py:167-173`** becomes:

```python
def test_deshawns_means_test_counts_his_and_his_wifes_income(filer):
    client, session = filer
    _answer(session, *DESHAWN)
    result = MeansTestCalculator(session).calculate()
    assert (result["cmi"], result["details"]["annualized_cmi"]) == (Decimal("4500.00"), 54000.0)
    assert "qualifies_for_fee_waiver" not in result
```

**`backend/apps/intake/tests/test_e2e_intake.py`.**

- Delete `:713` (`assert "qualifies_for_fee_waiver" in result`).
- Replace `test_fee_waiver_qualification` (`:768-779`) in `TestMeansTestCalculation` with:

```python
    def test_a_very_low_income_hears_no_fee_waiver_verdict_from_the_means_test_or_summary(
        self, api_client, complete_session
    ):
        """The means test answers § 707(b) only; the court decides the fee waiver (3f spec §9)."""
        complete_session.income_info.monthly_gross_wages = Decimal("1500.00")
        complete_session.income_info.save()

        url = reverse("intake-session-calculate-means-test", args=[complete_session.id])
        result = api_client.post(url).data["means_test_result"]
        summary = api_client.get(reverse("intake-session-summary", args=[complete_session.id]))

        assert "qualifies_for_fee_waiver" not in result
        assert "fee waiver" not in result["message"].lower()
        assert summary.status_code == status.HTTP_200_OK
        assert summary.data["means_test"] == {"passes": True}
```

**`backend/apps/audit/tests/test_upl_compliance.py`.**

- `test_fee_waiver_message_no_prohibited_phrases` (`:269-285`) becomes `test_a_very_low_income_message_gives_no_fee_waiver_verdict`.
  - Its docstring is `"""A filer far below the median hears nothing about a fee waiver from the means test: the court decides it (28 U.S.C. § 1930(f)), and the filing-fee page shows its figures as information."""`.
  - The comment at `:275` becomes `# Very low income: under 60% of the median, where the old flag spoke of a fee waiver`.
  - The violation message reads `f"Very low income message contains prohibited phrases: {violations}\n"`.
  - After the `violations == []` assertion, add:

```python
        assert "fee waiver" not in result["message"].lower()
        assert "1930" not in result["message"]
```

- At `:315`, the comment becomes `# Very low`.
- At `:451`, the scenario `("fee_waiver", Decimal("1200.00"))` becomes `("very_low", Decimal("1200.00"))`, so the loop's `f"test_{scenario_name}"` username becomes `test_very_low`.

**`backend/apps/intake/tests/test_seed_demo_data.py`.**

- The test at `:197` is renamed `test_the_new_answers_move_no_seeded_personas_means_test_or_packet`.
- Delete its `assert means_test.qualifies_for_fee_waiver is (…)` (`:207-209`).
- Leave everything else as Task 4 left it, including the 103B assertion.

**`backend/apps/forms/tests/test_api_readback.py`.**

- Delete `from apps.eligibility.models import MeansTest` (`:27`).
- Delete the comment at `:36-37` and `QUALIFIES` at `:38`.
- Delete the two-line comment and the two lines at `:180-183`.
- Leave `APPLIES` (or Task 4's name for it) and everything at `:164` and `:259` alone.

**`backend/apps/eligibility/tests/test_migrations.py`** (new):

```python
"""The eligibility app's migrations, run by Django's migration executor on prepared rows.

Business intent: dropping the means test's old fee-waiver flag (3f spec §9) must keep every
stored means test result, since the packet and the dashboard's median notice read them, and
undoing it must give the column back without guessing a verdict.
"""

from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.districts.models import District
from apps.intake.models import IntakeSession
from apps.users.models import User

WITH_FLAG = [("eligibility", "0002_add_above_median_fields")]
WITHOUT_FLAG = [("eligibility", "0003_remove_meanstest_qualifies_for_fee_waiver")]

ON_POSTGRES = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason="needs Postgres: real column types; CI runs it with config.settings.test_postgres",
)


@pytest.fixture
def migrate(transactional_db):
    """Migrate the eligibility app to a migration and return the models as they were there.

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


def _columns():
    with connection.cursor() as cursor:
        table = connection.introspection.get_table_description(cursor, "means_tests")
    return {column.name for column in table}


def _drop_and_undo(migrate):
    # Only the eligibility app moves, so the session and district are today's models.
    user = User.objects.create_user(username="filer", password="pw")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    session = IntakeSession.objects.create(user_id=user.pk, district_id=district.pk)
    old = migrate(WITH_FLAG).get_model("eligibility", "MeansTest")
    row = old.objects.create(
        session_id=session.pk,
        district_id=district.pk,
        median_income_threshold=Decimal("110712.00"),
        calculated_cmi=Decimal("2800.00"),
        passes_means_test=True,
        qualifies_for_fee_waiver=True,
    )
    kept = migrate(WITHOUT_FLAG).get_model("eligibility", "MeansTest").objects.get(pk=row.pk)
    after = (kept.calculated_cmi, kept.median_income_threshold, kept.passes_means_test, _columns())
    undone = migrate(WITH_FLAG).get_model("eligibility", "MeansTest").objects.get(pk=row.pk)
    return after, (undone.calculated_cmi, undone.qualifies_for_fee_waiver)


def test_dropping_the_fee_flag_keeps_every_means_test_result(migrate):
    (cmi, median, passes, columns), undone = _drop_and_undo(migrate)
    assert (cmi, median, passes) == (Decimal("2800.00"), Decimal("110712.00"), True)
    assert "qualifies_for_fee_waiver" not in columns and "calculated_cmi" in columns
    assert undone == (Decimal("2800.00"), False)  # the column returns empty, never a verdict


@pytest.mark.postgres
@ON_POSTGRES
def test_dropping_the_fee_flag_keeps_every_means_test_result_on_postgres(migrate):
    (cmi, median, passes, columns), undone = _drop_and_undo(migrate)
    assert (cmi, median, passes) == (Decimal("2800.00"), Decimal("110712.00"), True)
    assert "qualifies_for_fee_waiver" not in columns and "calculated_cmi" in columns
    assert undone == (Decimal("2800.00"), False)
```

- [ ] **Step 2: Run the backend tests to verify they fail**

Run: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest apps/eligibility/tests/test_means_test_calculator.py apps/eligibility/tests/test_household_means_test.py apps/eligibility/tests/test_migrations.py apps/intake/tests/test_e2e_intake.py apps/audit/tests/test_upl_compliance.py -q -p no:cacheprovider`

Expected: FAIL, for these reasons:

- `test_no_income_gets_a_fee_waiver_verdict_from_the_means_test`:
  - For `0.00`, `1500.00` and `3000.00`, it fails on `"qualifies_for_fee_waiver" not in result`. The key is in every result.
  - For `3565.20` and `4166.67`, it fails on the same line. Those incomes sit above the old 60% line, so their message is clean but the key is still there.
- `test_a_means_test_row_stores_no_fee_waiver_verdict`: the field exists.
- `test_detailed_breakdown_after_calculation`: `results` has the extra key.
- `test_deshawns_means_test_counts_his_and_his_wifes_income`: the key is in the result.
- `test_a_very_low_income_hears_no_fee_waiver_verdict_from_the_means_test_or_summary`: the key is in the result. With that line commented out, the message contains "fee waiver", and the summary has `qualifies_fee_waiver`.
- `test_a_very_low_income_message_gives_no_fee_waiver_verdict`: the $1,500 message ends "Additionally, you may qualify for a filing fee waiver under 28 U.S.C. § 1930(f) …".
- Both `test_migrations.py` tests: `NodeNotFoundError` for `('eligibility', '0003_remove_meanstest_qualifies_for_fee_waiver')`. The `_on_postgres` twin is skipped on sqlite.

The renamed tests that only lose an assertion (`test_a_very_low_income_message_contains_no_upl_violations`, the seed test, the readback) pass both before and after. They are edits, not new outcomes.

- [ ] **Step 3: Remove the flag from the backend**

- `eligibility/models.py`:
  - Delete the field and its comment (`:96-97`).
  - Delete the three lines of computation (`:186-188`).
  - Delete the `"qualifies_fee_waiver"` entry (`:226`).
  - Delete the assignment (`:236`).
  - `median_income_threshold` is still read by the median comparison above, so no variable becomes unused.
- Generate `0003_remove_meanstest_qualifies_for_fee_waiver.py` with `cd backend && $PY manage.py makemigrations eligibility -n remove_meanstest_qualifies_for_fee_waiver`.
  - Check that it holds exactly `migrations.RemoveField(model_name="meanstest", name="qualifies_for_fee_waiver")` and depends on `("eligibility", "0002_add_above_median_fields")`.
- `means_test_calculator.py`:
  - Delete `:57` from the `calculate` docstring and `- Fee waiver eligibility` (`:192`) from `get_detailed_breakdown`'s.
  - Delete the result key (`:98`) and the breakdown key (`:221`).
  - Delete the blank line and the `if means_test.qualifies_for_fee_waiver:` block (`:146-152`), so `elif` follows the message's closing parenthesis. The below-median message is then its three sentences at `:139-145`, unchanged.
- `intake/views.py`:
  - Delete `:349` from the `calculate_means_test` docstring.
  - The summary's `means_test` (`:416-419`) becomes `{"passes": session.means_test.passes_means_test}`.
- `seed_demo_data.py`:

  - `:924-925`'s comment becomes `# Create FeeWaiverApplication for the personas who apply (required by Form 103B generator); one with no "fee_waiver" answers doesn't`, wrapped at the file's width.
  - `:926` becomes `if "fee_waiver" in data:`.
  - Docstrings:
    - `:60` becomes `"""Below-median single parent who asks for the fee to be waived. PRD primary persona."""`;
    - `:521` becomes `"""Simplest case — single, no assets, asks for the fee to be waived."""`;
    - `:604` becomes `"""Gig driver, below median. Pays the fee in installments."""`.

- [ ] **Step 4: Run the backend tests to verify they pass**

Run: the Step 2 command, plus `apps/intake/tests/test_seed_demo_data.py apps/forms/tests/test_api_readback.py`.

Expected: PASS. The `_on_postgres` twin is skipped on sqlite.

- [ ] **Step 5: Write the failing frontend test**

In `frontend/src/components/wizard/__tests__/MeansTestPreview.test.tsx`:

- Delete `qualifies_for_fee_waiver: false,` (`:62`).
- Inside `describe('MeansTestPreview with an estimate')`, after the existing test, add:

```tsx
// The means test answers § 707(b) only; the court decides a fee waiver, and the filing-fee
// page shows its figures as information (3f spec §9). An old server's key changes nothing.
it('the means-test preview gives no fee-waiver verdict, even for a very low income', async () => {
  server.use(
    http.post('http://localhost:8000/api/intake/sessions/:id/calculate_means_test/', () =>
      HttpResponse.json({
        means_test_result: {
          passes_means_test: true,
          qualifies_for_fee_waiver: true,
          cmi: 1500,
          median_income_threshold: 71304,
          family_size: 1,
        },
        session_id: 1,
      })
    )
  );
  render(<MeansTestPreview sessionId={1} currentStep={3} />);
  await userEvent.click(screen.getByRole('button', { name: /eligibility estimate/i }));
  await screen.findByText('Based on your information, you may be eligible for Chapter 7.');

  expect(screen.getByText('Monthly income for the means test')).toBeInTheDocument();
  expect(screen.queryByText(/fee waiver/i)).not.toBeInTheDocument();
});
```

Run: `cd frontend && npx vitest run src/components/wizard/__tests__/MeansTestPreview.test.tsx --maxWorkers=2`

Expected: FAIL, on the last assertion. The row's `<dt>Fee Waiver</dt>` and "You may qualify for a filing fee waiver" both match `/fee waiver/i`, so `queryByText` throws "Found multiple elements".

- [ ] **Step 6: Remove the flag from the frontend**

- `types/api.ts`:
  - Delete `qualifies_for_fee_waiver: boolean;` (`:460`).
  - Delete `qualifies_fee_waiver: boolean;` (`:721`), leaving `SessionSummaryResponse.means_test` as `{ passes: boolean }` on its own lines.
- `MeansTestPreview.tsx`: delete the `{result.qualifies_for_fee_waiver && (…)}` block (`:120-125`).
- `global.css`: delete the `.means-test-preview-detail--highlight` rule and its blank line (`:878-882`).
- `test/mocks/handlers.ts:75` and `test/fixtures/session.ts:135`: delete `qualifies_for_fee_waiver: false,`.

Run: the Step 5 command. Expected: PASS.

- [ ] **Step 7: Check that no reader of the flag is left**

The journeys, `personas.ts`, the wizard's routing test and the File Map line are Task 5's (R22), so this step only looks. From the worktree root:

`/usr/bin/grep -rIn -e qualifies_for_fee_waiver -e qualifies_fee_waiver -e fee_waiver_eligible -e "fee-waiver eligible" -e "fee waiver eligible" backend frontend/src frontend/e2e CLAUDE.md --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=__pycache__`

Expected: only these lines:

- `backend/apps/eligibility/migrations/0001_initial.py:58` and the `RemoveField` in `0003_…`;
- the absence assertions in `test_means_test_calculator.py`, `test_household_means_test.py` and `test_e2e_intake.py`, and `test_migrations.py` (the field name in `old.objects.create` and the assertions);
- the old-server reply in `MeansTestPreview.test.tsx`;
- Task 5's `qualifies_for_fee_waiver: flag` in the `IntakeWizard.test.tsx` routing test, which stays.

Then:

- Any hit in non-test application code (`backend/apps/**` outside `tests/` and `migrations/`, or `frontend/src` outside `__tests__/`) is a failure of this task.
- A hit in `frontend/e2e`, in `CLAUDE.md:130`, in `FeeWaiverPage.test.tsx` or elsewhere in `IntakeWizard.test.tsx` is Task 5's leftover. Record it in the ledger, for Task 9, and leave it out of this commit.

- [ ] **Step 8: Update `CLAUDE.md` and `docs/REFERENCE_TABLES.md`**

`CLAUDE.md`, "Means test units": the sentence beginning "`calculation_details` holds `marital_status`" (the gotcha's second-to-last) is followed by a new sentence, so the two read, after this task:

"`calculation_details` holds `marital_status` (the line 1 answer), `family_size` (line 13) and `spouse_cmi` (Column B), and no `number_of_dependents`. The means test gives no fee-waiver verdict (3f dropped its flag, eligibility migration 0003): the court decides the waiver, and the filing-fee page shows its figures as information."

The gotcha's other sentences are unchanged.

`docs/REFERENCE_TABLES.md` (R2):

- `:14` reads, after this task: "DigniFi compares each filer's income with this table on Form 122A-1 (line 13), and it uses the table to decide whether Form 122A-2 is in the packet."
- `:4` stays as Task 1 set it, unless this commit falls on a later day; then it becomes `- **Last updated:** <the commit's date>`.

Check: `/usr/bin/grep -n "offered the fee-waiver" docs/REFERENCE_TABLES.md` prints nothing.

- [ ] **Step 9: Gates**

- Check `uptime`. Run the full suites only while the 1-minute load is under 10.
- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 -q -p no:cacheprovider`
  - Expected: 0 failed, coverage at least 90%.
  - The count moves as follows: 4 tests out (the two deleted classes), 6 in (5 parametrized cases and the row test), and 2 in `test_migrations.py`, one passing and its twin skipped. The other changed tests replace or rename one test each.
- `/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/` (ruff 0.8.5). Expected: `All checks passed!`. This catches a leftover `MeansTest` import in `test_api_readback.py`.
- `cd backend && $PY manage.py check`. Expected: "System check identified no issues".
- `cd backend && $PY manage.py makemigrations --check --dry-run`. Expected: "No changes detected".
- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres -q -p no:cacheprovider`
  - Run it with `DATABASE_URL` naming a Postgres whose user can create the test database, never `dignifi_dev`.
  - Expected: the new twin and every existing `postgres` test pass.
- `cd frontend && npx vitest run --maxWorkers=2`
- `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit` (never `tsc -b`)
  - Expected: pass.
  - A failure naming `qualifies_for_fee_waiver` means a reader Task 5 owns is still there. Stop and record it in the ledger.
- `cd frontend && npm run lint && npm run format:check`
- `frontend/node_modules/.bin/prettier --check CLAUDE.md docs/REFERENCE_TABLES.md`, run from the worktree root, since `format:check` covers only `src`.

No journey run in this task (Global Constraints: Tasks 1, 5, 8 and 9). `ASSERTED_CASES` is unchanged.

- [ ] **Step 10: Commit**

With `PYTHONDONTWRITEBYTECODE=1` exported:

```bash
/usr/bin/git add backend/apps/eligibility/models.py backend/apps/eligibility/migrations/0003_remove_meanstest_qualifies_for_fee_waiver.py backend/apps/eligibility/services/means_test_calculator.py backend/apps/intake/views.py backend/apps/intake/management/commands/seed_demo_data.py backend/apps/eligibility/tests/test_migrations.py backend/apps/eligibility/tests/test_means_test_calculator.py backend/apps/eligibility/tests/test_household_means_test.py backend/apps/intake/tests/test_e2e_intake.py backend/apps/audit/tests/test_upl_compliance.py backend/apps/intake/tests/test_seed_demo_data.py backend/apps/forms/tests/test_api_readback.py frontend/src/types/api.ts frontend/src/components/wizard/MeansTestPreview.tsx frontend/src/styles/global.css frontend/src/test/mocks/handlers.ts frontend/src/test/fixtures/session.ts frontend/src/components/wizard/__tests__/MeansTestPreview.test.tsx CLAUDE.md docs/REFERENCE_TABLES.md
/usr/bin/git commit -F /tmp/3f-task7-msg.txt
```

The message, written to `/tmp/3f-task7-msg.txt`, with no trailer:

```
feat(eligibility): drop the means test's fee-waiver flag

MeansTest.qualifies_for_fee_waiver was a 60%-of-median guess, never the
court's 150% poverty test, and it told filers they "may qualify". The
column goes (eligibility 0003), with its computation, the calculator's
keys and sentence, the summary's key and the preview's row, and
REFERENCE_TABLES.md no longer says the median decides the fee-waiver
offer. The means test now answers 11 U.S.C. § 707(b) only; the
filing-fee page shows the court's figures as information (DIG-145).
```

---

### Task 8: `FeeWaiverApplication` is dropped, and every applicant keeps the waiver

**Spec:** §4 ("`FeeWaiverApplication` is removed", "Migration", "Reverse", "What existing sessions meet after the migration", "The whole fee-waiver API goes with the model"), §12 ("The fee-waiver application" becomes "The filing fee", File Map), §13 ("a session with a `FeeWaiverApplication` keeps 103B after the migration", "the migrations run forward and back on sqlite and Postgres"), §15 item 4, §16 calls 3, 20 and 21.

Line numbers are as of `dc31b7a`. Tasks 1–7 shift some of them before this task runs, so each `path:lines` also names the block to find.

**Files:**

- Create: `backend/apps/intake/migrations/0030_fee_waiver_applications_to_filing_fee.py` (hand-written `RunPython`, depends on `0029_filingfee`)
- Create: `backend/apps/intake/migrations/0031_delete_feewaiverapplication.py` (generated)
- Modify: `backend/apps/intake/models.py:8` (the `MinValueValidator` import: only `FeeWaiverApplication.household_size`, `:889`, uses it), `:46-59` (the `IntakeSession.reopen` docstring) and `:863-987` (delete `class FeeWaiverApplication`, with `qualifies_for_waiver` and `get_poverty_threshold`). `ClassVar` and `Decimal` stay imported: other models use them (`Decimal(` at `:242`, `:364`, `:632-633`). Check with ruff.
- Modify: `backend/apps/intake/serializers.py:35` (the import) and `:817-887` (delete `FeeWaiverApplicationSerializer`)
- Modify: `backend/apps/intake/views.py:31` and `:44` (the imports), `:69-79` (the `_assert_session_owned` docstring's last sentence) and `:680-720` (delete `FeeWaiverViewSet`)
- Modify: `backend/apps/intake/urls.py:7`, `:16` (the import and the `fee-waiver` route)
- Modify: `backend/apps/intake/management/commands/seed_demo_data.py`:
  - `:22` (`count_fee_waiver_household` import) and `:28` (`FeeWaiverApplication` import);
  - Maria's and Sarah's `"fee_waiver"` dicts with their comments (`:194-199`, `:594-599`). DeShawn's dict (`:511-516`) is Task 4's (ruling R15), which leaves `# No "fee_waiver": he pays the fee in installments (3f spec §10).` in its place; that comment goes here;
  - Andrés's `:786` comment;
  - the creation branch `:924-936`, with the comment and the `if "fee_waiver" in data:` condition Task 7 gives it (ruling R19).
- Modify: `backend/conftest.py:12` (the `collect_ignore` entry `"test_fee_waiver_manual.py"`; no such file exists in the repo)
- Delete: `backend/apps/intake/tests/test_fee_waiver_views.py` (555 lines, the whole file)
- Modify: `backend/apps/intake/tests/test_models.py:130-215` (delete `class TestFeeWaiverApplication`; the file's imports stay used by `TestDebtInfoClassification`)
- Modify: `backend/apps/intake/tests/test_completion.py:1-8` (module docstring) and `:1000-1031` (`test_form_answers_sofa_and_fee_waiver_leave_a_completed_intake_complete`)
- Modify: `backend/apps/intake/tests/test_seed_demo_data.py:24` (the import) and `:106-123` (delete `test_the_seed_gives_the_fee_waiver_application_103b_line_1s_count`, with the comment Task 4 puts above it)
- Modify: `backend/apps/intake/tests/test_data_migrations.py` (two constants after Task 3's `FILING_FEE`, which follows `SHIFT` at `:29`; three tests and a Postgres twin appended after Task 3's 0029 tests)
- Modify: `backend/apps/forms/tests/test_registry.py:27` (the import) and `:124-133` (delete the test Task 4 renames `test_a_fee_waiver_application_without_the_line_8_answer_adds_no_103b`)
- Modify: `backend/apps/forms/tests/test_api_readback.py`, as Tasks 4 and 7 leave it (ruling R20): `:39-41` (`APPLIES`' comment only), `:83-93` (`_fee_waiver_application`), `:96-108` (`_fee_waiver_answers`), `:164-170` (the POST), `:252-253` (the comparison's comment) and `:258-259` (the two asserts)
- Modify: `backend/apps/forms/tests/test_form_views.py:402-406` (`/fee-waiver` → `/filing-fee`) and the comment at `:483`. The comments at `:302`, `:918` and `:1068` are Task 4's.
- Modify: `backend/apps/forms/tests/test_printed_page.py:219` (comment)
- Modify: `backend/apps/forms/tests/test_form_103b_schema.py` (`:14` import, the `FeeWaiverApplication.objects.create` in `session_with_fw` `:50-58`, and the test Task 2 names `test_line_1_counts_the_household_list_not_the_applications_size`). Task 2 already takes the model out of `test_form_103b_answers.py`.
- Modify: `backend/config/tests/test_urls.py:87` (the SPA route list) and `class TestBackendPathsAreNotSwallowedBySpa` (`:50-80`, one test added)
- Modify: `frontend/src/api/client.ts:509-561` (the "Fee Waiver API" block: its banner, `FeeWaiverPayload`, `FeeWaiverApplication`, `feeWaiverAPI` and the blank line after it) and `:772` (`feeWaiver: feeWaiverAPI,`). Ruling R25: Task 5 leaves these.
- Modify: `frontend/src/test/mocks/handlers.ts:146-168` (the "Fee Waiver" GET and POST handlers and the blank line after them). Ruling R25: Task 5 leaves these.
- Modify: `frontend/src/utils/parseAmount.ts:57-58` (the `amountError` docstring's "Fee waiver take-home pay" bullet, which describes the serializer field this task deletes; no other task names it)
- Modify: `CLAUDE.md:75` ("The fee-waiver application"), `:29` ("Seed order", one clause and Task 4's "Personas seeded before 3f" sentence, ruling R27), `:33` ("Forms need a completed intake", the never-reopen list) and `:99` (File Map, `apps/intake/models.py`)

**Interfaces:**

- Consumes:
  - Task 3: `FilingFee` (`session` one-to-one, `related_name="filing_fee"`, `db_table="filing_fees"`, `payment_choice` encrypted), migration `0029_filingfee`, the session action `PUT /api/intake/sessions/{id}/filing-fee/`, `answer_household`'s default `FilingFee(payment_choice="pay_in_full")`, and `test_data_migrations.py`'s `FILING_FEE = [("intake", "0029_filingfee")]`, which this task reuses and does not redefine.
  - Task 4: `form_103b`'s `applies` (`_asks_fee_waiver`, `payment_choice == "waiver"`), so `packet()` no longer reads `session.fee_waiver`. Also: the seed's `"filing_fee"` dicts and `FilingFee`s, with DeShawn's `"fee_waiver"` dict gone (ruling R15); `test_api_readback.py`'s `APPLIES = {"maria", "sarah"}`, its filing-fee PUT and its `assert ("form_103b" in form_types) is (persona in APPLIES)`; `test_registry.py`'s `test_a_fee_waiver_application_without_the_line_8_answer_adds_no_103b`, left for this task; the comments at `test_form_views.py:302`, `:918`, `:1068` and `test_download_action.py:305`; the CLAUDE.md "Seed order" sentence "Personas seeded before 3f have no `FilingFee`, …" and "Forms need a completed intake"'s "…, the filing fee (`PUT /api/intake/sessions/{id}/filing-fee/`) and the fee-waiver application never reopen it".
  - Task 2: no derivation reads `session.fee_waiver` any more, the `/fee-waiver` `RULE_FIXES` are gone, and `test_form_103b_answers.py` no longer names the model.
  - Task 5: `FeeWaiverPage.tsx` and its test are deleted, so nothing in `frontend/src` calls `api.feeWaiver`; the client and its MSW handlers are left for this task (ruling R25).
  - Task 7: `qualifies_for_fee_waiver` is gone; the seed's branch reads `if "fee_waiver" in data:` (ruling R19); `test_upl_compliance.py:451`'s scenario is `"very_low"`.
- Produces:
  - Migration `0030_fee_waiver_applications_to_filing_fee`. Forward: each session with a `FeeWaiverApplication` and no `FilingFee` gets `FilingFee(payment_choice="waiver")`. Reverse: each `FilingFee` whose `payment_choice` reads `"waiver"`, on a session with no application, gets a bare `FeeWaiverApplication(household_size=1)`.
  - Migration `0031_delete_feewaiverapplication`: `DeleteModel("FeeWaiverApplication")`. Its reverse recreates the table from migration state.
  - No `FeeWaiverApplication`, `FeeWaiverApplicationSerializer`, `FeeWaiverViewSet` or `fee-waiver` route. `GET /api/intake/fee-waiver/` is a 404.
  - No `feeWaiverAPI`, `api.feeWaiver`, `FeeWaiverPayload` or `FeeWaiverApplication` type in the frontend, and no MSW handler for `/intake/fee-waiver/`.
  - `ASSERTED_CASES` is unchanged (delta 0): this task binds nothing.
- CLAUDE.md:
  - "The fee-waiver application" is replaced whole by "The filing fee" (Step 8 gives the text).
  - "Seed order" loses its fee-waiver clause, and its "Personas seeded before 3f" sentence names the migrated waiver (ruling R27; Task 9 no longer edits this gotcha).
  - "Forms need a completed intake": the never-reopen list names the filing fee in place of the fee-waiver application.
  - The File Map's `apps/intake/models.py` entry names `FilingFee` in place of `FeeWaiverApplication`.

**Decided here:**

- **The reverse compares in Python, not in SQL.** `payment_choice` is Fernet ciphertext with a fresh IV on every write, so `FilingFee.objects.filter(payment_choice="waiver")` matches no row, and does so silently. Both directions iterate rows and compare the decrypted value. `test_undoing_the_drop_gives_each_waiver_choice_a_bare_application` fails on a reverse that filters.
- **"Unless one exists" leaves the session's own `FilingFee` as it is**, whatever it holds, null `payment_choice` included. A filer who already answered on `/filing-fee` before this migration ran (a dev database between Tasks 3 and 8) keeps that answer.
- **"Everything else empty" in the reverse** means `monthly_take_home_pay`, `monthly_income`, `monthly_expenses` and `receives_noncash_assistance` are None, and `benefit_types` is `[]`. The non-null columns `receives_public_benefits` (False), `cannot_pay_full` and `cannot_pay_installments` (True) and `status` ("pending") take their model defaults, since they have no empty value.
- **The reverse keeps the `FilingFee` rows the forward created.** It can't tell them from the filer's own. Undoing `0029` drops the table anyway. Going forward again leaves those rows alone, because each has a `FilingFee` already.
- **The frontend fee-waiver client and its MSW handlers go here** (ruling R25). Task 5 deletes the page and its test but leaves `feeWaiverAPI`, its two interfaces (`client.ts:509-561`, `:772`) and the handlers (`handlers.ts:146-168`). The endpoint dies in this task, so its client dies with it (spec §4, "Frontend: `api.feeWaiver` … its MSW handlers and fixtures"). Step 6 first checks that no caller is left, and the frontend gates run in this task (ruling R30).
- **The seed's leftovers are split by ruling.** Task 4 deletes DeShawn's `"fee_waiver"` dict (R15) and Task 7 changes the branch's condition to `"fee_waiver" in data` (R19). This task deletes Maria's and Sarah's dicts, the branch, and the two `# No "fee_waiver": …` comments (DeShawn's from Task 4, Andrés's at `:786`), which describe a key the seed no longer has.
- **`test_api_readback.py` keeps `APPLIES`** (ruling R20). Task 4's packet assertion still reads it. Only its comment changes, because its second line names the application.
- **CLAUDE.md "Seed order" is finished here** (ruling R27). Its fee-waiver clause goes, and Task 4's "Personas seeded before 3f" sentence gains what migration 0030 does to the personas seeded before Task 4 (Maria, DeShawn and Sarah had applications). Task 9 does not edit this gotcha again.
- **`config/tests/test_urls.py:87`'s `/fee-waiver` becomes `/filing-fee`.** The parametrized test pins React deep links that Django must serve. `/filing-fee` is the page now, and `/fee-waiver` is only a client-side redirect. Both resolve through the same catch-all (`BACKEND_ROUTE_PREFIXES` is `admin, api, health, metrics, static, media`, `config/urls.py:28`), so this edit fails nothing before the change. The test that fails first is the new 404 one.
- **`test_the_seed_gives_the_fee_waiver_application_103b_line_1s_count` is deleted, not rewritten.** The seed no longer stores a size. 103B line 1's count from the household list is pinned by Task 2's `fee_waiver_family` tests, and by `test_household_counts.py:79-87` for `count_fee_waiver_household`. Likewise `test_registry.py`'s `test_a_fee_waiver_application_without_the_line_8_answer_adds_no_103b`: with no model there is no application to ignore, and Task 4's `test_filing_fee_forms.py` pins 103B to the line 8 answer.
- **`conftest.py:12` can have no failing test.** `test_fee_waiver_manual.py` exists nowhere in the worktree (`find` returns nothing), so the ignore entry is dead. It goes because spec §4 names it. That is a cleanup with nothing to observe.
- **Spec §4 cites `test_completion.py:1000-1017`;** the test runs `:1000-1031`. This task rewrites all of it.

- [ ] **Step 1: Write the failing tests**

`backend/apps/intake/tests/test_data_migrations.py`. After Task 3's `FILING_FEE = [("intake", "0029_filingfee")]` (just after `SHIFT`, `:29`), add:

```python
WAIVER_CARRIED = [("intake", "0030_fee_waiver_applications_to_filing_fee")]
APPLICATION_DROPPED = [("intake", "0031_delete_feewaiverapplication")]
```

Add `from apps.forms.registry import packet` and `from apps.intake.models import IntakeSession as LiveIntakeSession` to the imports. The module already uses `District` and `User` live, and defines `ON_POSTGRES` (`:418-421`). Append at the end of the file, after Task 3's 0029 tests:

```python
def _applicants_before_the_drop(migrate):
    """Three sessions at 0029: one applied for the waiver, one applied and then chose
    installments on the filing-fee page, and one never applied."""
    apps = migrate(FILING_FEE)
    IntakeSession = apps.get_model("intake", "IntakeSession")
    applied = _session(apps)
    chose = IntakeSession.objects.create(user_id=applied.user_id, district_id=applied.district_id)
    never = IntakeSession.objects.create(user_id=applied.user_id, district_id=applied.district_id)
    FeeWaiverApplication = apps.get_model("intake", "FeeWaiverApplication")
    for session in (applied, chose):
        FeeWaiverApplication.objects.create(
            session_id=session.pk,
            household_size=3,
            monthly_take_home_pay=Decimal("2800.00"),
            receives_noncash_assistance=True,
            benefit_types=["SNAP (food stamps)"],
        )
    apps.get_model("intake", "FilingFee").objects.create(
        session_id=chose.pk, payment_choice="installments"
    )
    return applied.pk, chose.pk, never.pk


def _choices(apps):
    """Each stored line 8 answer by session, decrypted: payment_choice can't be filtered on."""
    return {f.session_id: f.payment_choice for f in apps.get_model("intake", "FilingFee").objects.all()}


def test_every_fee_waiver_applicant_keeps_the_waiver_and_103b_when_the_application_table_goes(
    migrate,
):
    # An applicant asked the court to waive the fee. Dropping the plaintext table must not
    # take that request out of the packet, and must not overwrite an answer the filer
    # already gave on the filing-fee page, or invent one for a filer who never applied.
    applied, chose, never = _applicants_before_the_drop(migrate)

    apps = migrate(APPLICATION_DROPPED)

    assert _choices(apps) == {applied: "waiver", chose: "installments"}
    assert "fee_waiver_applications" not in connection.introspection.table_names()
    with pytest.raises(LookupError):
        apps.get_model("intake", "FeeWaiverApplication")
    # APPLICATION_DROPPED is the leaf, so the live models read these rows as they are.
    packets = {pk: packet(LiveIntakeSession.objects.get(pk=pk)) for pk in (applied, chose, never)}
    assert ["form_103b" in packets[pk] for pk in (applied, chose, never)] == [True, False, False]


def test_the_carried_waiver_choice_is_ciphertext_in_the_table(migrate):
    # The migration writes through the encrypted field, so the answer is never plaintext
    # at rest (DIG-279), not even for one release.
    applied, _, _ = _applicants_before_the_drop(migrate)

    migrate(WAIVER_CARRIED)

    with connection.cursor() as cursor:
        cursor.execute("SELECT payment_choice FROM filing_fees WHERE session_id = %s", [applied])
        (raw,) = cursor.fetchone()
    assert raw.startswith("gAAAAA") and "waiver" not in raw


def _undo_the_drop(migrate):
    applied, chose, _ = _applicants_before_the_drop(migrate)
    migrate(APPLICATION_DROPPED)
    apps = migrate(FILING_FEE)
    applications = {
        fw.session_id: (
            fw.household_size,
            fw.monthly_take_home_pay,
            fw.receives_noncash_assistance,
            fw.benefit_types,
        )
        for fw in apps.get_model("intake", "FeeWaiverApplication").objects.all()
    }
    return (applied, chose), applications, _choices(apps)


def test_undoing_the_drop_gives_each_waiver_choice_a_bare_application(migrate):
    # Undone, a waiver filer's packet again holds 103B through an application, but the
    # typed answers are gone with the table: one person and nothing else, never a guess.
    # A filer who chose installments gets none, even though they once applied.
    (applied, chose), applications, choices = _undo_the_drop(migrate)
    assert applications == {applied: (1, None, None, [])}
    assert choices == {applied: "waiver", chose: "installments"}


@pytest.mark.postgres
@ON_POSTGRES
def test_dropping_and_restoring_the_application_table_keeps_each_waiver_choice_on_postgres(
    migrate,
):
    (applied, chose), applications, choices = _undo_the_drop(migrate)
    assert applications == {applied: (1, None, None, [])}
    assert choices == {applied: "waiver", chose: "installments"}
    assert "fee_waiver_applications" in connection.introspection.table_names()
```

`backend/config/tests/test_urls.py`, in `TestBackendPathsAreNotSwallowedBySpa`, after `test_unknown_api_path_returns_404_not_the_spa_shell` (`:73-75`):

```python
    def test_the_retired_fee_waiver_api_is_gone(self):
        # The application and its plaintext answers were dropped in 3f; the filing-fee
        # action on the session replaced the endpoint, and nothing may still write there.
        assert self.client.get("/api/intake/fee-waiver/").status_code == 404
```

In the same file, `:87`'s list has `"/filing-fee"` in place of `"/fee-waiver"`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest apps/intake/tests/test_data_migrations.py config/tests/test_urls.py -q -p no:cacheprovider`

Expected: FAIL, 4 failed, and the Postgres twin skipped.

- The three migration tests fail with `NodeNotFoundError` naming `0030_fee_waiver_applications_to_filing_fee` or `0031_delete_feewaiverapplication`. Neither migration exists yet.
- `test_the_retired_fee_waiver_api_is_gone`: `assert 401 == 404`. The route exists, and an anonymous request is refused before any lookup.
- Every test that was already there passes, the 0015 test among them.

- [ ] **Step 3: The data migration, then the model's removal**

Order matters: if the model class goes first, `makemigrations` writes the delete as `0030`.

1. `cd backend && $PY manage.py makemigrations intake --empty -n fee_waiver_applications_to_filing_fee`. It writes `0030_…`, depending on `("intake", "0029_filingfee")`. Check the dependency.
2. Fill it in:
   - The module docstring says what it does both ways. It must also say: "The typed answers (household size, take-home pay, non-cash help) don't come back on undo: they now come from the household list, Schedule I and 8f."
   - `def carry_waiver_choice(apps, schema_editor) -> None`:
     - Read `has_fee = set(FilingFee.objects.values_list("session_id", flat=True))`.
     - For each `session_id` in `FeeWaiverApplication.objects.values_list("session_id", flat=True)` that is not in `has_fee`, run `FilingFee.objects.create(session_id=session_id, payment_choice="waiver")`.
   - `def restore_bare_applications(apps, schema_editor) -> None`:
     - Read `has_application` as the set of application `session_id`s.
     - For each `fee in FilingFee.objects.all()`, when `fee.payment_choice == "waiver"` (compared in Python) and `fee.session_id not in has_application`, run `FeeWaiverApplication.objects.create(session_id=fee.session_id, household_size=1)`.
     - Nothing else is passed.
   - `operations = [migrations.RunPython(carry_waiver_choice, restore_bare_applications)]`.
3. Delete `class FeeWaiverApplication` (`models.py:863-987`) and the `from django.core.validators import MinValueValidator` line (`:8`), which nothing else in the file reads (ruff F401 otherwise).
4. `$PY manage.py makemigrations intake -n delete_feewaiverapplication` writes `0031_delete_feewaiverapplication.py`, with one operation, `migrations.DeleteModel(name="FeeWaiverApplication")`, depending on `0030`. Read it, and keep it as generated.
5. The `IntakeSession.reopen` docstring (`models.py:47-51`) reads:

   "Set a completed intake back to in progress, because its intake data changed.

   The filer then presses Complete again, which re-runs the completion checks (spec §5.3). Form answers, SOFA and the filing fee are not intake data and never call this."

   The paragraph after it ("The database decides …") is unchanged.

- [ ] **Step 4: The API and every reader go**

- `serializers.py`: delete `FeeWaiverApplicationSerializer` (`:817-887`) and the `FeeWaiverApplication` import (`:35`).
- `views.py`:
  - Delete `FeeWaiverViewSet` (`:680-720`) and the two imports (`:31`, `:44`).
  - In `_assert_session_owned`'s docstring, delete the sentence "Mirrors the guard in `FeeWaiverViewSet.perform_create`." (`:73-74`). The sentence before it now ends the docstring.
- `urls.py`: drop `FeeWaiverViewSet,` from the import (`:7`) and the `router.register(r"fee-waiver", …)` line (`:16`).
- `conftest.py`: delete the `"test_fee_waiver_manual.py",` line (`:12`). The comment above the list ("Standalone manual test scripts") still describes the two entries after it.
- `seed_demo_data.py`:
  - Delete Maria's and Sarah's `"fee_waiver"` dicts (`:194-199`, `:594-599`), each with its comment line "The fee-waiver page's answers (Form 103B lines 2 and 3)". Their `"filing_fee"` dicts (Task 4) stay.
  - Delete DeShawn's comment `# No "fee_waiver": he pays the fee in installments (3f spec §10).` (Task 4's, where his dict was) and Andrés's `# No "fee_waiver": he means to pay the fee in installments (3a1.Q2).` (`:786`). Their `"filing_fee"` dicts stay.
  - Delete the comment and `if "fee_waiver" in data:` block Task 7 leaves at `:924-936`. `result` is still read by `if result["passes_means_test"]:` (`:939`), and `household` by `store_members` and `save()` (`:893-894`), so both stay.
  - Delete the `FeeWaiverApplication` import (`:28`) and the `from apps.intake.household import count_fee_waiver_household` line (`:22`), which nothing else in the file reads (ruff F401 otherwise).
- [ ] **Step 5: The tests that named the model**

- `git rm` `backend/apps/intake/tests/test_fee_waiver_views.py`. First record its case count: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest --collect-only -q -p no:cacheprovider apps/intake/tests/test_fee_waiver_views.py | tail -1`. Step 9 needs that number.
  - Its ownership guards are still covered for the routes that remain. `_assert_session_owned` serves `AssetViewSet` and `DebtViewSet` (`views.py:617`, `:626`, `:657`, `:666`), and the filing-fee action's 404 for another user's session is Task 3's test.
- `test_models.py`: delete `class TestFeeWaiverApplication` with its decorator and the blank lines before it (`:130-215`, five tests). `User`, `District` and `IntakeSession` stay imported for `TestDebtInfoClassification`.
- `test_seed_demo_data.py`: delete `test_the_seed_gives_the_fee_waiver_application_103b_line_1s_count` (`:106-123`, with its decorator and the comment Task 4 adds above it) and `FeeWaiverApplication` from the `:24` import. Task 4's `FilingFee` stays in it.
- `test_registry.py`: delete `test_a_fee_waiver_application_without_the_line_8_answer_adds_no_103b` (Task 4's name for `:124-133`) and `FeeWaiverApplication` from the `:27` import, which then reads `from apps.intake.models import DebtorInfo, FilingFee, Household, IntakeSession`. `Decimal` stays imported: four other uses remain.
- `test_completion.py`:
  - The module docstring's last two sentences (`:5-7`) read: "Changing intake data after Complete sets the intake back to in progress, so the filer presses Complete again, which re-runs its checks. Form answers, SOFA and the filing fee are not intake data and never reopen it."
  - The test at `:1000` becomes:

```python
def test_form_answers_sofa_and_the_filing_fee_leave_a_completed_intake_complete(filer, completed):
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
    filing_fee = client.put(
        _session_url(completed, "filing-fee/"), {"payment_choice": "waiver"}, format="json"
    )

    assert (answers.status_code, sofa.status_code, filing_fee.status_code) == (200, 200, 200)
    assert _status(completed) == "completed"
```

- `test_api_readback.py`, as Tasks 4 and 7 leave it (ruling R20):
  - Delete `_fee_waiver_application` (`:83-93`), `_fee_waiver_answers` (`:96-108`), the `if persona in APPLIES:` POST to `/api/intake/fee-waiver/` (`:164-170`), and the two `_fee_waiver_answers` asserts (`:258-259`) with their comment ("Form 103B prints take-home pay …", `:252-253`). `built = …` (`:254`) stays: `_household_answers(built)` reads it.
  - `household_size = …["fee_waiver_household_size"]` and its `assert … is not None` (`:162-163`) stay: they check the Complete reply, not the model (ruling R26).
  - Task 4's filing-fee PUT and its `("form_103b" in form_types) is (persona in APPLIES)` assertion stay, so `APPLIES` stays. Its comment (Task 4's) becomes `# These ask for the fee waiver on Form 101 line 8 (3f spec §10), so 103B is in their packets.`
- `test_form_views.py`:
  - `:402` and `:406`: `"/fee-waiver"` becomes `"/filing-fee"`. The case is a synthetic `ValueTooLong` that pins the view copying a `page`.
  - `:483`'s "No fee waiver: no 103B." becomes "Line 8 is pay in full: no 103B.", in Task 4's words for `:302`, with the rest of the comment unchanged. `session_with_debtor` is built on `answer_household`, so its line 8 is `pay_in_full` (Task 3). Leave `:302`, `:918` and `:1068`: Task 4 rewrites them.
- `test_printed_page.py:219`: the comment becomes `# Maria's waiver answer`.
- `test_form_103b_schema.py`, as Task 2 leaves it:
  - Delete the `FeeWaiverApplication.objects.create(...)` from `session_with_fw` (`:50-58`), and `FeeWaiverApplication` from the import (`:14`). The fixture keeps its name, its `DebtorInfo`, and Task 2's `IncomeInfo` and `answer_household(session)`.
  - Task 2's `test_line_1_counts_the_household_list_not_the_applications_size` becomes `test_line_1_counts_the_household_list`, its comment `# The filer listed no one else, so 103B line 1 is 1.`, and its assertion is unchanged.
  - `resolve()` never consults the packet, and after Task 2 every line 1–3 box reads the wizard, so each case's expected values are unchanged.
- `test_form_103b_answers.py` needs nothing: Task 2's rewrite drops `_apply` and the import. Step 7's sweep confirms it.

- [ ] **Step 6: The frontend client goes with the endpoint**

- Check that nothing is left calling it: `/usr/bin/grep -rnE "feeWaiver|FeeWaiverPayload|FeeWaiverApplication|intake/fee-waiver" frontend/src`.
  - Expected hits (at `dc31b7a` numbering; Tasks 5 and 6 shift both files): only `client.ts:514`, `:525`, `:540-542`, `:550-554` and `:772`, and `handlers.ts:148` and `:152`.
  - `App.tsx`'s `/fee-waiver` redirect has no `intake/` prefix, so it doesn't match.
  - Any hit elsewhere (such as `FeeWaiverPage.tsx` or its test) means Task 5 is unfinished. Stop and report it.
- `client.ts`: delete the "Fee Waiver API" block, from its banner comment (`:509-511`) through `feeWaiverAPI`'s closing `};` (`:560`) and the blank line after it (`:561`), and the `feeWaiver: feeWaiverAPI,` line in `api` (`:772`). The "Forms API" banner that follows stays.
- `handlers.ts`: delete the `// -- Fee Waiver --` comment, its sub-comment, both `http.get` / `http.post` handlers for `${API}/intake/fee-waiver/` (`:146-167`) and the blank line after them (`:168`). Task 5's filing-fee handlers stay.
- `parseAmount.ts`: delete the two-line bullet "- Fee waiver take-home pay: the serializer's DecimalField(max_digits=10, decimal_places=2, min_value=0), 99,999,999.99" (`:57-58`) from `amountError`'s docstring. The Income/Expenses and SOFA bullets stay. Then `/usr/bin/grep -rniE "fee.?waiver" frontend/src` may list only: the shared `fee-waiver-question`/`fee-waiver-checkbox` classes and their CSS, `fee_waiver_household_size` (ruling R26), Form 103B's name ("Fee Waiver Application" in `types/api.ts`, `AskModulePage.tsx` and `FormDashboard.test.tsx`), and `handlers.ts`'s `mockPacket` comment (Task 6's). Any other hit is in an earlier task's file: report it in the ledger as that task's miss, and don't fix it here.

- [ ] **Step 7: Run the tests to verify they pass, then sweep**

Run: the Step 2 command, plus `apps/intake/tests/test_completion.py apps/intake/tests/test_models.py apps/intake/tests/test_seed_demo_data.py apps/forms/tests/test_registry.py apps/forms/tests/test_api_readback.py apps/forms/tests/test_form_views.py apps/forms/tests/test_printed_page.py apps/forms/tests/test_form_103b_answers.py apps/forms/tests/test_form_103b_schema.py`.

Expected: PASS, with the Postgres twin skipped.

Sweep. Quote the glob, because zsh expands an unquoted `--include=*.py`:

```bash
/usr/bin/grep -rnE "FeeWaiverApplication|FeeWaiverViewSet|fee-waiver|fee_waiver_applications|\.fee_waiver\b|\"fee_waiver\"|test_fee_waiver_manual" '--include=*.py' backend
```

Expected hits, and no others:

- `backend/apps/intake/migrations/0003_add_fee_waiver.py`: history. It is the only earlier migration this pattern matches; the others name the model in lower case.
- `0030_fee_waiver_applications_to_filing_fee.py` and `0031_delete_feewaiverapplication.py`.
- `test_data_migrations.py`: the 0015 test (`:208-232`) and Step 1's tests.
- `config/tests/test_urls.py`: the new 404 test.

`count_fee_waiver_household`, the new `fee_waiver_*` rule names, `fee_waiver_household_size` on the household serializer and `test_widgets.py:117`'s local `fee_waiver` don't match this pattern.

At `dc31b7a` the pattern also matches the hits below, which earlier tasks own. Each must be gone by now:

- Task 2: `derivations.py:533-560` and `:1080-1083`; `test_check.py:42` and `:257`; `test_rule_fixes.py:175`; the docstring at `test_form_103b_answers.py:2-6`.
- Task 4: `registry.py:52`.
- Task 7: `test_api_readback.py:36-37` and `:181`, the `QUALIFIES` comments; `test_upl_compliance.py:451`'s `("fee_waiver", …)` scenario, renamed `"very_low"`.

This task's own Step 4 and Step 5 edits clear the rest of the `dc31b7a` hits (the seed, models, serializers, views, urls, `conftest.py`, `test_registry.py:27` and `:125`, `test_form_103b_schema.py`, `test_api_readback.py`, `test_completion.py`, `test_models.py`, `test_seed_demo_data.py`, `test_form_views.py:402-406`, `test_printed_page.py:219`).

If one remains:

- A comment or docstring in a file this task already stages: reword it here, in the words of the code as it now stands.
- Any code hit, or a hit in another file: stop and report it as that task's miss rather than fix it here.

- [ ] **Step 8: Update `CLAUDE.md`**

After this task they read as follows.

- "The fee-waiver application" (`:75`) is replaced whole by one bullet, written on one line like every other gotcha. After its bold name, **The filing fee**, it reads: "`FilingFee` (`apps/intake/models.py`, one-to-one with the session, `related_name="filing_fee"`, table `filing_fees`) holds Form 101 line 8 and 103B's own questions, every column encrypted, and nothing starts answered: `payment_choice` (`pay_in_full`, `installments` or `waiver`; null unanswered), 103B lines 4, 7 and 9 as `income_change_answer`, `others_covered_answer` and `expense_change_answer` (`yes`, `no` or null) with their texts `income_change_explanation`, `others_covered_who` and `expense_change_explanation`, and line 5's `installments_explanation`; each text is bounded by `FilingFee.TEXT_LIMITS`, which the serializer and the page enforce. `GET` and `PUT /api/intake/sessions/{id}/filing-fee/` read and save it for a session in any status: the PUT locks the session, sets only the keys sent, refuses an unknown key or value with a 400 (`FilingFeeSerializer`), never reopens a completed intake and returns the GET body, which adds `information` (`{family_size, limit_monthly, guideline: {year, effective_date, source_url}, family_income_monthly}`, decimals as strings, from `filing_fee_information` in `apps/intake/filing_fee.py`), or null with `information_gap` `"income"` or `"no_table"`; a missing figure never blocks the answer. `FilingFeePage` (`/filing-fee`) asks every filer after Complete and shows the court's limit beside the filer's own figure as information, never a verdict ("The court decides."); `/fee-waiver` redirects there. 103B is in the packet exactly when `payment_choice` is `waiver`; its `requires` refuses an unanswered line 4, 7 or 9, a Yes without its text, or a blank line 5, with `page: "/filing-fee"`, and Form 101 refuses an unanswered line 8 the same way ("Choose how you will pay the filing fee.") and prints the answer on `Check Box7`. 103B lines 1–3 read the wizard through `apps/forms/services/fee_waiver.py`, and their refusals link to `income_info`: line 1 is `fee_waiver_family` (the filer, a spouse at home and the dependents, `count_fee_waiver_household`; an Income step gap raises `IncomeStepGap`, never a guessed 1), line 2 is `fee_waiver_income` (Schedule I line 10 per person less the counted non-cash value, the figure the page shows), and line 3 is 8f (`fee_waiver_noncash`). Line 6 prints Schedule J line 22c (`undefined_7`). Lines 17–19 are still asked at `/ask/form_103b` and stored as plaintext `FormAnswer` rows until DIG-168. `FeeWaiverApplication`, its `/api/intake/fee-waiver/` API and its plaintext columns were dropped in 3f: `0030_fee_waiver_applications_to_filing_fee` gave each session that had one a `FilingFee` with `waiver`, leaving an existing `FilingFee` as it was, and `0031_delete_feewaiverapplication` dropped the table; undone, each `waiver` choice gets back a bare one-person application, and the typed answers don't come back. A migrated `waiver` session has no answers to lines 4, 5, 7 and 9, so its 103B is refused until the filer answers them, and a session with no `FilingFee` has its Form 101 refused until the filer chooses; re-create the personas with `seed_demo_data --reset`."
- "Seed order" (`:29`), ruling R27:
  - "The seed writes each persona's `Household` and `SpouseIncome` before it runs the means test, and sizes the fee-waiver application from `count_fee_waiver_household`." becomes "The seed writes each persona's `Household` and `SpouseIncome` before it runs the means test."
  - Task 4's "Personas seeded before 3f have no `FilingFee`, so their Form 101 is refused with a link to `/filing-fee`. Re-create them with `seed_demo_data --reset`." becomes "Personas seeded before 3f have no `FilingFee`, so their Form 101 is refused with a link to `/filing-fee`. Maria, DeShawn and Sarah are the exception: migration 0030 gives each of them `waiver`, with 103B lines 4, 5, 7 and 9 unanswered, so their 103B is refused instead. Re-create them with `seed_demo_data --reset`."
  - Every other sentence of the gotcha, including Task 4's "The seed also writes each persona's `FilingFee`. …", is unchanged.
- "Forms need a completed intake" (`:33`): Task 4's "Form answers (`answers/bulk`), SOFA, the filing fee (`PUT /api/intake/sessions/{id}/filing-fee/`) and the fee-waiver application never reopen it" becomes "Form answers (`answers/bulk`), SOFA and the filing fee (`PUT /api/intake/sessions/{id}/filing-fee/`) never reopen it". The rest of the gotcha is unchanged.
- File Map (`:99`): the `apps/intake/models.py` entry ends "…, AssetInfo, DebtInfo, FilingFee, Household, SpouseIncome". The `src/pages/SOFAStep.tsx` / `FeeWaiverPage.tsx` entry (`:130`) is Task 5's (ruling R22), so this task leaves it alone.

- [ ] **Step 9: Gates**

Check `uptime` first. Run the full suite only while the 1-minute load is under 10, and the journeys only while the 5-minute load is also under 8. Then run each of these:

- The full backend suite: `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 -q -p no:cacheprovider`.
  - Expected: 0 failed, and coverage at least 90%.
  - Fewer tests than before by the cases deleted: Step 5's recorded count for `test_fee_waiver_views.py`, plus 5 in `test_models.py`, 1 in `test_seed_demo_data.py` and 1 in `test_registry.py`.
  - More by 4: three migration tests and the 404 test. The Postgres twin is skipped.
- `/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/` (ruff 0.8.5). Expected: `All checks passed!`. It catches an import left behind in the seed, the views, the serializers or a test.
- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY manage.py check`. Expected: "System check identified no issues".
- `cd backend && $PY manage.py makemigrations --check --dry-run`. Expected: "No changes detected".
- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres -q -p no:cacheprovider`. Expected: the new twin and every existing `postgres` test pass. The twin runs the drop and its reverse on real Postgres column types.
- `cd frontend && npx vitest run --maxWorkers=2`
- `cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit` (never `tsc -b`)
- `cd frontend && npm run lint && npm run format:check`
- `frontend/node_modules/.bin/prettier --check CLAUDE.md`, run from the worktree root.
- The journeys, `zsh .claude/e2e.sh 2`. Expected: green both runs. The dev database first runs `0030` and `0031`. Every journey registers a fresh account, so none meets a migrated session.

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
/usr/bin/git rm backend/apps/intake/tests/test_fee_waiver_views.py
/usr/bin/git add backend/apps/intake/migrations/0030_fee_waiver_applications_to_filing_fee.py backend/apps/intake/migrations/0031_delete_feewaiverapplication.py backend/apps/intake/models.py backend/apps/intake/serializers.py backend/apps/intake/views.py backend/apps/intake/urls.py backend/apps/intake/management/commands/seed_demo_data.py backend/conftest.py backend/apps/intake/tests/test_models.py backend/apps/intake/tests/test_completion.py backend/apps/intake/tests/test_seed_demo_data.py backend/apps/intake/tests/test_data_migrations.py backend/apps/forms/tests/test_registry.py backend/apps/forms/tests/test_api_readback.py backend/apps/forms/tests/test_form_views.py backend/apps/forms/tests/test_printed_page.py backend/apps/forms/tests/test_form_103b_schema.py backend/config/tests/test_urls.py frontend/src/api/client.ts frontend/src/test/mocks/handlers.ts frontend/src/utils/parseAmount.ts CLAUDE.md
/usr/bin/git commit -F /tmp/3f-task8-msg.txt
```

`/usr/bin/git status --short` before committing must list no other path this task touched.

The message, written to `/tmp/3f-task8-msg.txt`, with no trailer:

```
feat(intake): drop the fee-waiver application, keeping each applicant's waiver

Every answer FeeWaiverApplication held is now asked once elsewhere or
printed nowhere, so its plaintext table goes. A data migration first
gives each session that had an application a FilingFee with the
waiver, leaving an answer already given alone; undone, each waiver
choice gets a bare one-person application back. The fee-waiver API,
its serializer, route, client and tests go with it.
```

---

### Task 9: The persona briefs answer line 8, and nothing names the fee-waiver page or its model

**Spec:** §10 ("Briefs"), §12 (the gotchas this task checks), §13 ("The gates").

Line numbers are as of `dc31b7a`. Tasks 1–8 move most of them, so each `path:line` below also names the row, sentence or gotcha to find. This task touches no code. Its fail-then-pass check is the sweep in Steps 1 and 6, not a new test file.

**Files:**

- Modify: `docs/testing/persona-briefs/maria-torres.md:72-73` (the two "(fee waiver page)" rows of "Your Data")
- Modify: `docs/testing/persona-briefs/sarah-chen.md:68-69` (the same two rows) and `:84` ("What to Watch For")
- Modify: `docs/testing/persona-briefs/deshawn-mitchell.md:77-78` (the same two rows)
- Modify: `docs/testing/persona-briefs/james-washington.md`, after `:73` (the last "Your Data" row)
- Modify: `docs/testing/persona-briefs/priya-sharma.md`, after `:79` (the last "Your Data" row)
- Modify: `docs/testing/persona-briefs/andres-kettleby.md`, after `:70` (the last "Your Data" row), plus `:94` ("**The fee:**") and `:108` (the last "What to Watch For" item)
- Modify: `docs/testing/persona-briefs/README.md:18`, `:21`, `:22`, `:23` (the "Means Test" column of the outcomes table)
- Modify: `README.md:168` ("Core Features")
- Modify: `docs/security/compliance.md:198-199` ("DigniFi Implementation" under "Fee Waiver Requirements")
- Modify: `docs/security/data-protection.md:45` ("Encrypted Models")
- Modify: `frontend/e2e/pages/dashboard.page.ts:11-12` (the `generateAllForms` doc comment, which no other task touches)
- Check, edit only for a prose leftover: `CLAUDE.md`, every gotcha §12 names plus "Seed order" (Step 5), and `docs/REFERENCE_TABLES.md:14` (Task 7's, R2)

**Interfaces:**

- Consumes:
  - Task 4's seed: each persona's `FilingFee`, with the §10 answers in Global Constraints ("Persona outcomes").
  - Task 5's page: the option labels in Form 101 line 8's words, `PAYMENT_CHOICE_WORDS` (R16: the field index's words, the waiver option with no final period), and 103B's questions for lines 4, 5, 7 and 9 (§6.4), from `formText.ts`. The page reached after Complete is `/filing-fee`, and its h1 is "How you will pay the filing fee".
  - Task 5's 103A notice under installments (§6.3).
  - The exclusions R21 and Task 7 ("Which hits the grep allows") list for the final grep.
  - Task 8's migrations `0030_fee_waiver_applications_to_filing_fee` and `0031_delete_feewaiverapplication`, its "The filing fee" gotcha, and its "Seed order" sentences (R27).
- Produces: no code, names or `ASSERTED_CASES` change (a delta of 0). After this task the branch holds no mention of the fee-waiver page, its API or its model outside the list in Step 6.
- CLAUDE.md: no sentence is this task's own. "Seed order"'s fee-waiver sentence and its "Personas seeded before 3f …" sentence are Task 8's (R27). Step 5 checks every gotcha §12 names and fixes only a prose leftover.

**Decided here:**

- **The "(fee waiver page)" rows are deleted, not moved** (R28). §10 says they "move to the Income step's answers they now are: 5a–5h and 8f". 3e2's Task 11 already added those rows to each brief:

  - Maria: `maria-torres.md:56` (8f, "SNAP (food stamps)", $350) and `:57` (5a $400);
  - Sarah: `sarah-chen.md:56-57`;
  - DeShawn: `deshawn-mitchell.md:59-60`.

  So the old rows go, and nothing is added in their place except the new rows below. Each take-home figure is the Income step's gross less the deductions row: Maria 3,200 − 400 = 2,800, Sarah 2,000 − 250 = 1,750, DeShawn 3,500 − 450 = 3,050. The deleted rows lose nothing.

- **The line 8 row's label** is "How you will pay the fee (after Complete, Form 101 line 8)", and its value is the option's words as the page shows them. The spec's "How you will pay the fee (Form 101 line 8)" gets "after Complete" added because the briefs label rows by where they are asked, as in "(Income step)". The waiver option is quoted without a final period, as the field index has it (`form_b_101_0624_fillable_clean.index.json:1259`, "I request that my fee be waived") and as R16 has the page print it. §6.1's period is not quoted, so the persona finds on the page exactly the words the brief gives.
- **The waiver rows quote 103B's own questions**, as the briefs already do for Schedule J lines (for example, `priya-sharma.md:78`). The questions are taken from the index labels for `Check 4` (`form_b103b.index.json:281`), `Check 7` (`:389`) and `Check 9` (`:479`), with a straight apostrophe. Line 5 quotes only the first sentence of §6.4's question.
- **Andrés's two lines** are rewritten without the detour (§10), and his new watch item names §6.3's notice. Neither says "qualify" or "eligible" (Global Constraints, "No verdict").
- **Three docs outside the frame's boundary** would make false claims once Task 8 lands, so this task edits only those sentences (R28):
  - root `README.md:168` ("Fee waiver eligibility assessment");
  - `docs/security/compliance.md:198-199` ("Automatic fee waiver calculation", "once the filer submits the fee-waiver application");
  - `docs/security/data-protection.md:45` (`FeeWaiverApplication` listed as encrypted, and `FilingFee` missing).
- **`dashboard.page.ts:11-12`'s comment is edited here.** It reads "plus Form 103B for one with a fee waiver application", and no other task's Files list names the file. It is prose, so it is fixed here rather than sent back.
- **Docs left alone, logged in the ledger (R28):**
  - `data-protection.md:51`, "Not encrypted (among others): `IncomeInfo` and `ExpenseInfo` amounts", has been wrong since 3e2 encrypted them. It is not part of 3f.
  - The "you may qualify for a fee waiver" examples in `docs/PLAIN_LANGUAGE_GUIDE.md:254`, `:477` and `:480` are writing guidance from before step 3, as are `docs/UPL_COMPLIANCE.md:139` and `:222`.
  - `docs/REFERENCE_TABLES.md:14` belongs to Task 7 (R2). Step 5 checks it.
- **The persona-targets doc (`docs/superpowers/specs/2026-10-16-forms-step3-personas.md`) is not edited** (R28). It is an approved target, and its `WAIVER_FILERS` mentions (`:258`, `:945`, `:994`, `:1187-1188`, `:1390`) record what the targets said when they were written. The sweep leaves out `docs/superpowers/` as a whole and `docs/internal/` (the PRD's June history, `DigniFi_PRD_v0_3.md:398`), as R21 says. It also leaves out `docs/reports/`, beyond R21's list: its dated reports (for example `2026-02-28-usability-test.md:24`, `2026-10-13-upsolve-design-extraction.md:193`) record what the app was when they were written.
- **The sweep's patterns are exact names, never bare `fee-waiver` or `fee_waiver`.**
  - Bare `fee-waiver` matches the `fee-waiver-question` and `fee-waiver-checkbox` classes that §4 keeps.
  - Bare `fee_waiver` matches `count_fee_waiver_household`, the serializer's `household.fee_waiver_household_size` (kept, R26) and Task 2's `fee_waiver_*` rules.
  - No `-i`: with it, `feeWaiver` would match Task 2's `FeeWaiverFamily` and `FeeWaiverIncome`.
  - The prose alternative is `[Ff]ee[ -]waiver (page|application|eligib)`, lowercase after the first letter. Form 103B's own name, "Form 103B - Fee Waiver Application", stays in the form-type choices (`apps/forms/models.py:18` and forms migrations `0002`, `0004`, `0005`), `types/api.ts:482`, `:526`, `AskModulePage.tsx:13` and the dashboard tests' card lookups (Task 6, "the form's name and stays"), and must not match. The old page's h1 and link words, "Filing Fee Waiver Application", are their own alternative.
  - The removed rule names `fee_waiver_monthly_income`, `fee_waiver_benefit_types` and `fee_waiver_noncash_assistance` are in the sweep. The removed `fee_waiver_household_size` rule is not, because the serializer field keeps that name.
- **A hit outside Step 6's list is a leftover from an earlier task.** It goes in the ledger with its file, line and owning task.
  - This task fixes it only if it is prose: a comment, a docstring or a doc. The file is then added to this task's commit.
  - A code or data hit (a binding, an audit row, an unbound entry, a test) stops this task, and it goes back to the owning task's fix wave. That change needs its own tests and its `ASSERTED_CASES` arithmetic.
  - "Seed order" is the exception among prose: R27 gives its sentences to Task 8, so a miss there goes back to Task 8's fix wave.
  - The audit evidence `data/forms/field_index/audit/form_103b.audit.json` and `verification.json` is never edited. It records what the original audit saw.
- **The final gate runs every gate**, the Postgres tests and both `tsc` projects included, though this task changes no migration or `src` file. It is the branch's last check before the owner's review.

- [ ] **Step 1: Run the sweep and see it fail**

From the worktree root, with Tasks 1–8 committed:

```bash
grep -rIn -E "qualifies_for_fee_waiver|qualifies_fee_waiver|fee_waiver_eligible|FeeWaiverApplication|FeeWaiverPage|FeeWaiverViewSet|feeWaiver|/fee-waiver|fee-waiver\.page|fee_waiver_(monthly_income|benefit_types|noncash_assistance)\b|[Ff]ee[ -]waiver (page|application|eligib)|Filing Fee Waiver Application" . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.git --exclude-dir=.claude --exclude-dir=superpowers --exclude-dir=internal --exclude-dir=reports
grep -n -i "qualif" docs/testing/persona-briefs/*.md
```

Expected: FAIL. Besides the hits Step 6 allows, the first command prints these lines, which this task removes:

- `docs/testing/persona-briefs/maria-torres.md:72`, `:73`, `sarah-chen.md:68`, `:69`, `deshawn-mitchell.md:77`, `:78` (each "(fee waiver page)");
- `andres-kettleby.md:94` and `:108` ("fee waiver page");
- `README.md:168` ("Fee waiver eligibility");
- `docs/security/compliance.md:199` ("fee-waiver application");
- `docs/security/data-protection.md:45` (`FeeWaiverApplication`);
- `frontend/e2e/pages/dashboard.page.ts:12` ("fee waiver application").

The second command prints `sarah-chen.md:84` ("You qualify."). Record every other hit outside Step 6's list in the ledger, as "Decided here" says.

- [ ] **Step 2: The six briefs**

Each brief's "Your Data" table (`| Field | Value |`) gains the rows below. The old "(fee waiver page)" rows go first: Maria `:72-73`, Sarah `:68-69` and DeShawn `:77-78`. The new rows take their place, or go after the last row for James, Priya and Andrés.

| Brief   | Field                                                                                                                                     | Value                                                                                                                                                                |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Maria   | How you will pay the fee (after Complete, Form 101 line 8)                                                                                | I request that my fee be waived                                                                                                                                      |
| Maria   | 103B line 4 ("Do you expect your family's average monthly net income to increase or decrease by more than 10% during the next 6 months?") | No                                                                                                                                                                   |
| Maria   | 103B line 5 ("Tell the court why you are unable to pay the filing fee in installments within 120 days.")                                  | "I support two children on what I earn. After rent, food, the car and the children's costs, there is not enough left each month to pay the fee, even in parts."      |
| Maria   | 103B line 7 ("Do these expenses cover anyone who is not included in your family as reported in line 1?")                                  | No                                                                                                                                                                   |
| Maria   | 103B line 9 ("Do you expect your average monthly expenses to increase or decrease by more than 10% during the next 6 months?")            | No                                                                                                                                                                   |
| Sarah   | the same five fields                                                                                                                      | I request that my fee be waived; No; "I have no savings. My pay covers rent, food and my bus pass, and what is left each month goes to bills I already owe."; No; No |
| DeShawn | How you will pay the fee (after Complete, Form 101 line 8)                                                                                | I need to pay the fee in installments.                                                                                                                               |
| James   | How you will pay the fee (after Complete, Form 101 line 8)                                                                                | I will pay the entire fee when I file my petition.                                                                                                                   |
| Priya   | How you will pay the fee (after Complete, Form 101 line 8)                                                                                | I will pay the entire fee when I file my petition.                                                                                                                   |
| Andrés  | How you will pay the fee (after Complete, Form 101 line 8)                                                                                | I need to pay the fee in installments.                                                                                                                               |

The two line 5 texts are §10's, as the owner approved them, word for word. They are also the seed's (Task 4).

Then three sentences change:

- `sarah-chen.md:84`, "- Is the fee waiver mentioned clearly? You qualify.", becomes "- Is it clear how to ask for a fee waiver and what the court looks at? You plan to ask for one." (§10, PS:1163).
- `andres-kettleby.md:94` becomes: `**The fee:** you mean to pay the filing fee in installments. After Complete, DigniFi asks how you will pay the fee: choose "I need to pay the fee in installments." and go on.`
- `andres-kettleby.md:108`, "- Does the fee waiver page let you go on without applying?", becomes "- When you choose installments, does the page say what else you file and where to get it?"

`andres-kettleby.md:99` ("**Installments:** $338 at once is more than your best week leaves over …") stays. It is his reason, and it says nothing about the old page.

- [ ] **Step 3: The briefs' README**

In the outcomes table (`docs/testing/persona-briefs/README.md:16-23`), the "Means Test" cells change (§10, PS:1166). James's and Priya's rows stay.

| Row                         | Before                          | After                           |
| --------------------------- | ------------------------------- | ------------------------------- |
| `:18` `maria-torres.md`     | `Passes, fee waiver`            | `Passes, asks for a fee waiver` |
| `:21` `deshawn-mitchell.md` | `Passes, fee waiver`            | `Passes, pays in installments`  |
| `:22` `sarah-chen.md`       | `Passes, fee waiver`            | `Passes, asks for a fee waiver` |
| `:23` `andres-kettleby.md`  | `Passes, no waiver application` | `Passes, pays in installments`  |

- [ ] **Step 4: The docs and the comment that would state a removed behaviour**

- `README.md:168`, "- Fee waiver eligibility assessment (28 U.S.C. § 1930(f))", becomes:

  > - Filing fee (Form 101 line 8): the filer chooses how to pay. A waiver request adds Form 103B, filled from the intake. The court's limit (150% of the HHS poverty guideline) and the filer's own Form 103B figure are shown as information (28 U.S.C. § 1930(f)).

- `docs/security/compliance.md:198-199` ("Automatic fee waiver calculation based on income" and "Form 103B joins the packet once the filer submits the fee-waiver application") become these three bullets. `:200` ("Disclaimers that waiver is not guaranteed") stays.

  > - The filer chooses how to pay the fee (Form 101 line 8). DigniFi never chooses for them.
  > - Form 103B joins the packet when the filer asks for a waiver.
  > - The court's limit (150% of the HHS poverty guideline) and the filer's Form 103B income are shown as information, beside "The court decides."

- `docs/security/data-protection.md:45`, "- `FeeWaiverApplication` `monthly_income`, `monthly_expenses`, `monthly_take_home_pay` - Fee waiver amounts", becomes:

  > - `FilingFee` - every answer: how the filer will pay the fee (Form 101 line 8), and Form 103B lines 4, 5, 7 and 9

  Its `PovertyGuideline` is public data, and the list doesn't name it.

- `frontend/e2e/pages/dashboard.page.ts:11-12`, "@param expectedCount The persona's packet size: 14 forms for a below-median filer, plus Form 103B for one with a fee waiver application.", has its second line read "filer, plus Form 103B for one who asks for the fee waiver (Form 101 line 8)." The code is unchanged.

- [ ] **Step 5: The CLAUDE.md check**

1. Check that each gotcha below reads as its task wrote it. Find each by its name, not its line.

   | Gotcha                                              | Task       | What it must say                                                                                                                                                                                                                                                                                                                        |
   | --------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | "Seed order"                                        | 8 (R27)    | no "sizes the fee-waiver application" clause; each persona's `FilingFee`; a "Personas seeded before 3f …" sentence                                                                                                                                                                                                                      |
   | "Dated tables and the fill date"                    | 1          | the poverty table, that its row takes effect on the publication date, its 2027-01-31 `valid_through` and the refusal from 2027-02-01 (R24), and the `poverty_2026` fixture for transactional tests (R4)                                                                                                                                 |
   | "Saves lock the session"                            | 3          | the filing-fee PUT among the writes that lock                                                                                                                                                                                                                                                                                           |
   | "The packet decides which forms"                    | 4          | 103B applies on `FilingFee.payment_choice == "waiver"`; the `requires()` of 101 and 103B with `page="/filing-fee"`; no `FeeWaiverApplication`                                                                                                                                                                                           |
   | "Forms need a completed intake"                     | 4          | the filing fee among the writes that never reopen, in place of the fee-waiver application; `PreconditionMissing.page`                                                                                                                                                                                                                   |
   | "Means test units"                                  | 7          | `calculation_details` holds no `qualifies_fee_waiver`, and `MeansTest` no `qualifies_for_fee_waiver`                                                                                                                                                                                                                                    |
   | "GenerateAll vs single"                             | 4, 6 (R13) | the packet reply carries `payment_choice` (Task 4); `PAGE_LINK_LABELS` holds `/filing-fee` and the dashboard part is rewritten (Task 6)                                                                                                                                                                                                 |
   | "The filing fee" (was "The fee-waiver application") | 8          | `FilingFee` and its fields, the page and its API, 103B by the line 8 answer, lines 1–3 from the wizard, the waiver questions, the dropped model                                                                                                                                                                                         |
   | File Map                                            | 1, 2, 5, 8 | `poverty.py` (and `PovertyGuideline`) under `apps/districts` (1); `fee_waiver.py` under `apps/forms/services/` (2); `FilingFeePage.tsx` at `/filing-fee`, with `/fee-waiver` redirecting, and `handleComplete` always to `/filing-fee` (5, R22); `FilingFee` in place of `FeeWaiverApplication` in the `apps/intake/models.py` list (8) |

   A row that doesn't hold is the owning task's leftover. Handle it as "Decided here" says: a sentence is prose, so fix it here and log it, except "Seed order", which goes back to Task 8 (R27).

2. `household.fee_waiver_household_size` stays (R26: 103B line 1's count, with no reader after Task 5). "The household list" and "Autosave sends only real edits" keep naming it. It is listed for the owner, not removed.
3. Check `docs/REFERENCE_TABLES.md:14`. After Task 7 (R2) it must not say that the table decides "whether the filer is offered the fee-waiver application". If it still does, that is Task 7's leftover, a doc, and is fixed here.

- [ ] **Step 6: Run the sweep again and see it pass**

Run both Step 1 commands again.

Expected: the second prints nothing. The first prints only these lines (R21):

- intake migrations: `backend/apps/intake/migrations/0003_add_fee_waiver.py:17` (`name="FeeWaiverApplication"`), and Task 8's `0030_fee_waiver_applications_to_filing_fee.py` and `0031_delete_feewaiverapplication.py`;
- eligibility migrations: `backend/apps/eligibility/migrations/0001_initial.py:58` and Task 7's `0003_remove_meanstest_qualifies_for_fee_waiver.py`;
- the migration tests: `backend/apps/intake/tests/test_data_migrations.py` (the historical state at `:207-228` today, and Task 8's tests), and Task 7's `backend/apps/eligibility/tests/test_migrations.py`;
- Task 7's absence assertions in `test_means_test_calculator.py`, `test_household_means_test.py` and `test_e2e_intake.py`, and the old-server reply in `MeansTestPreview.test.tsx`;
- Task 5's routing test in `frontend/src/pages/__tests__/IntakeWizard.test.tsx`, whose mocked means-test reply keeps `qualifies_for_fee_waiver: flag` on purpose, to prove Complete lands on `/filing-fee` whatever the flag says;
- the redirect: `frontend/src/App.tsx` (the `/fee-waiver` route) and the test of it (`App.test.tsx`, and any Task 5 test that asserts Complete never lands on `/fee-waiver`);
- `backend/config/tests/test_urls.py`: Task 8's test that `/api/intake/fee-waiver/` is a 404 (its SPA route list holds `/filing-fee` after Task 8);
- `CLAUDE.md`: the File Map's mention of the `/fee-waiver` redirect (Task 5), "The filing fee"'s sentences on the redirect and the dropped `FeeWaiverApplication` and its `/api/intake/fee-waiver/` API (Task 8), and "Means test units"' `qualifies_fee_waiver` and `qualifies_for_fee_waiver` (Task 7);
- the audit evidence, any line of `data/forms/field_index/audit/form_103b.audit.json` (`:45`, `:59`, `:64`, `:65`, `:85` today) and `verification.json` (`:513`, `:2583` today).

No hit may remain in these:

- `form_101.unbound.json` (Task 4 takes out `Check Box7`, and with it the `:26` mention);
- `form_103b.unbound.json` (Task 2 takes out `check 3`, and with it `:49`);
- `step2_verification.json` (Task 2 re-keys the rows at `:205-240`);
- `data/forms/schemas/`;
- any non-test file under `backend/apps` outside `migrations/`;
- any `frontend/src` file outside `__tests__/` and `App.tsx`;
- `frontend/e2e`;
- `docs/testing` and `docs/security`.

- [ ] **Step 7: Prettier on the docs**

From the worktree root, with the pinned install the setup links (the root has no `package.json`, so `npx` there would fetch an unpinned prettier). The new rows re-pad whole tables, so write first and then check:

```bash
frontend/node_modules/.bin/prettier --write docs/testing/persona-briefs README.md docs/security/compliance.md docs/security/data-protection.md frontend/e2e/pages/dashboard.page.ts
frontend/node_modules/.bin/prettier --check docs/testing/persona-briefs README.md docs/security/compliance.md docs/security/data-protection.md frontend/e2e/pages/dashboard.page.ts CLAUDE.md
```

Add `CLAUDE.md` or `docs/REFERENCE_TABLES.md` to the `--write` line only if Step 5 edited it.

Expected: `All matched files use Prettier code style!`. In `git diff`, the only changes beyond Steps 2–5 are table padding. Any other rewrite is reverted and looked into.

- [ ] **Step 8: The final gates**

Check `uptime` first. Run the suite only with the 1-minute load under 10, and the journeys only with the 5-minute load under 8 as well.

- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 -q -p no:cacheprovider`. Expected: no failures, coverage of at least 90%. The strict xfail outside `known_defects.json` stays the one xfail reported (`apps/intake/tests/test_integration_flow.py`). `known_defects.json` is `[]`. `ASSERTED_CASES` (`test_oracle_tier2.py:37`) is the value the ledger records after Task 8: this task's delta is 0.
- `/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/` (ruff 0.8.5). Expected: `All checks passed!`
- `cd backend && $PY manage.py check`. Expected: `System check identified no issues (0 silenced).`
- `cd backend && $PY manage.py makemigrations --check --dry-run`. Expected: `No changes detected`.
- `cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres -q -rs -p no:cacheprovider`. Expected: no failures. Nothing is skipped for want of a database, and the migration twins of Tasks 1, 3, 7 and 8 run.
- `cd frontend && npx vitest run --maxWorkers=2`, then `npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit`, `npm run lint`, `npm run format:check` and `npx prettier --check "e2e/**/*.ts"` (R23). Expected: all pass, no output from tsc or eslint. Never `tsc -b`.
- The journeys twice: `zsh .claude/e2e.sh 2`. Expected: `8 passed` on both runs.
  - Maria and Sarah answer the waiver on `/filing-fee` and get 15 forms.
  - DeShawn and Andrés answer installments, see the 103A notice and get 14.
  - James and the SOFA journey pay in full and get 14.
  - Priya ends on `/filing-fee`.
  - The scanned-bill journey is unchanged.

Record every count in the ledger beside the baseline's.

- [ ] **Step 9: Commit**

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/git add docs/testing/persona-briefs/README.md docs/testing/persona-briefs/maria-torres.md docs/testing/persona-briefs/sarah-chen.md docs/testing/persona-briefs/deshawn-mitchell.md docs/testing/persona-briefs/james-washington.md docs/testing/persona-briefs/priya-sharma.md docs/testing/persona-briefs/andres-kettleby.md README.md docs/security/compliance.md docs/security/data-protection.md frontend/e2e/pages/dashboard.page.ts
/usr/bin/git commit -F /tmp/3f-task9-msg.txt
```

Add to the `git add` line any prose leftover fixed in Steps 5–6 (`CLAUDE.md`, `docs/REFERENCE_TABLES.md`, a comment), each by its path and each named in the ledger. If pre-commit's prettier rewrites a staged file, re-add it and commit again.

`/tmp/3f-task9-msg.txt`, with no trailer:

```
docs(forms): 3f persona briefs, and the last fee-waiver mentions go

Each persona brief answers Form 101 line 8, and Maria's and Sarah's
also answer 103B lines 4, 5, 7 and 9 in the owner's approved words.
The fee-waiver page rows go, since the Income and Take-home pay
steps already hold those answers. The README, the security docs and
the dashboard page object stop naming the fee-waiver application.
```
