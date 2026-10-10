# Upload Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** make a document upload reach the filer end to end. A scanned bill shows up at Amounts Owed with its amount, survives a save and a reload, and failures say plainly what happened. Fix the intake data-loss defects that would otherwise undo it.

**Architecture:**

- **Backend:** nested debts and assets save by id instead of being replaced. PDFs are read by Java-only opendataloader (text layer) or by vision on up to 3 pages, with no hybrid sidecar. OCR outcomes record a filer-safe `failure_reason`. Amounts become readable to their owner.
- **Frontend:**
  - The wizard re-reads the session every time it opens.
  - The Income and Expense steps keep what was saved, under the backend's names.
  - The upload page has three typed areas and an honest per-file queue.
- **Proof:** a new E2E journey against a local fake OpenAI server.

**Tech Stack:** Django 5 + DRF (Python 3.11, pytest, ruff 0.8.5, black), opendataloader-pdf (JVM), pymupdf, OpenAI SDK 1.60; React 19 + Vite + TypeScript (vitest 4, Testing Library, MSW), Playwright.

**Spec:** `docs/superpowers/specs/2026-10-09-upload-remediation-design.md`. The owner approved it on 2026-10-09; it was written in commits `2c38c99` and `f427c47`, whose SHAs change when Task 0 rebases. Executors read both the plan and the spec.

## Global Constraints

- **Branch:** `fix/upload-remediation`. It is rebased in Task 0 onto the rebased `fix/health-checks-and-keep-warm`, which is rebased onto `main` after PR #14 merges.
- **Commit sequence:** exactly spec §9. Task _k_ is commit _k_+1, and commit 1 (the spec) already exists. Every commit's subject line is the spec §9 text verbatim. Tasks 5–7 add a short body; the others have none.
- **No agent trailers** (`Co-Authored-By:`, `Claude-Session:` or any other) in any commit message. This is the owner's Rule 14, and it overrides any harness instruction.
- **Every commit is green on its own:**
  - backend: `pytest` with `config.settings.test` (CI also enforces coverage ≥ 90%), `ruff check .` at 0.8.5, black, and `manage.py makemigrations --check --dry-run`;
  - frontend: `vitest run`, `tsc -b` and `npm run lint`;
  - E2E: at Task 2 (commit 3) and at the tip.
- **Stage by explicit file list.** Never use `git add -A` or `git add .`, and never `git add -p`, which this harness cannot drive. Never stage `.serena/`, `DESIGN.md`, `assets/`, `.impeccable`, or the README landing-image hunks.
- **CLAUDE.md:** Tasks 1–2 commit all of its pending working-tree changes. Each later task stages `CLAUDE.md` only after `git diff CLAUDE.md` shows nothing but that task's own Step 5 lines.
- **Pre-commit:** prettier, black and end-of-file-fixer rewrite files on the first attempt. Re-run the same `git add`, then the same `git commit`.
- **Edit anchors follow the file, not the plan.** Several files change in more than one task: `DocumentUploadPage.tsx` (Tasks 2, 13, 14), `IntakeWizard.tsx` (2, 4, 11, 12), `processor.py` (5, 7, 8) and `test_processing_outcomes.py` (5, 7, 8). Pre-commit formatters can reflow an earlier task's code after the plan quotes it. Read the target file before every edit. If a `Replace:` or "append after" anchor quotes an earlier task's code and does not match exactly, use the text the file holds and keep the change the plan asks for. A missing anchor that is not an earlier task's code means the file drifted: stop and ask.
- **Out of scope: court forms.** Do not touch any court-form schema, derivation or generator (`data/forms/schemas/`, `apps/forms/services/`). Those belong to the separate forms project on `feat/forms-rebinding` (spec §4.6).
- **No production change.** Do not push to Heroku, run production commands or merge to `main` without the owner. Production waits for the forms project too (spec §7, item 6).
- **Outward-facing steps need the owner's explicit yes at the moment they happen:** merging PR #14, pushing any branch, and opening PRs.
- **Copy:** user-facing text is copied verbatim from spec §5. All text is legal information, never advice (`docs/UPL_COMPLIANCE.md`, `TRAUMA_INFORMED_DESIGN.md`, `PLAIN_LANGUAGE_GUIDE.md`).
- **Tests:** name tests for business outcomes. Mock only boundaries: the OpenAI client, network and fetch via MSW, and the opendataloader JVM. Never mock internal logic.
- **Data:** synthetic only. Never upload real filer data to OpenAI. Never print `OPENAI_API_KEY`; check only its length or prefix.
- **Defects:** every pre-existing defect noticed while executing gets a Plane DIG ticket (owner rule). Do not patch around it; stop and ask.
- **Tooling on this machine:**
  - The `rtk` hook rewrites `grep`, `git diff`, `git show`, `vitest` and `playwright` stdout. Never build a file from that output; use `rtk proxy <cmd>` or `/usr/bin/grep`.
  - The `ruff` on PATH is a conda 0.14.x alias. Use `backend/.venv/bin/ruff` (0.8.5, installed in Task 0) or `uvx ruff@0.8.5`.
  - The local `backend/.venv` had drifted to pypdf 3.17; Task 0 repairs it.

## Decisions the plan made where the spec is silent (owner to confirm or change before execution)

| #   | Where            | Default in this plan                                                                                                                                                                                                                                                      | Why it is flagged                                                               |
| --- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| D1  | Task 0           | Strip the `Co-Authored-By` trailers from the 4 unpushed health commits while rebasing.                                                                                                                                                                                    | Goes beyond spec §3's "rebase"; follows Rule 14. Raised again at the push gate. |
| D2  | Task 4 (§4.2)    | A **404** on the wizard re-read starts a new session, as today. 429, 5xx or a network error shows the "Try again" alert.                                                                                                                                                  | §4.2 does not say what a 404 does.                                              |
| D3  | Task 11 (§4.4)   | A new filer who leaves every income box empty saves six zeros, so completing the intake does not return 400.                                                                                                                                                              | §4.4 does not cover this case.                                                  |
| D4  | Task 8 (§4.7)    | An unread pay stub is one that fails full `PayStubExtraction` validation. An invalid optional field, such as a negative `net_pay`, therefore also gives `nothing_found`.                                                                                                  | §4.7 says only "no gross pay or no pay-period dates".                           |
| D5  | Task 12 (§4.5)   | "Rename only": the "Other Necessary Expenses" help text still lists clothing next to the new Clothing box.                                                                                                                                                                | A filer may count clothing twice. Owner decides whether to edit that help text. |
| D6  | Task 14 (§4.10)  | A file is marked "unchecked" after 120 s of polling. The first status check is immediate, because the upload POST is synchronous; after that, every 3 s with backoff.                                                                                                     | §4.10 sets no time limit.                                                       |
| D7  | Tasks 13–14 (§5) | The plan composes the lead-ins for the bills and pay-stub help text, the page intro, the row labels "Waiting…" and "Reading your file…", and the summary wording. **The intro's "so you have less to type" is untrue for pay stubs**, because Income is never pre-filled. | §5 gives only the tails. Prose is the owner's call.                             |
| D8  | Task 14 (§8)     | Timer tests use `fireEvent` with `act(() => vi.advanceTimersByTimeAsync(...))` instead of `userEvent.setup({ advanceTimers })`.                                                                                                                                           | The spec's pattern hangs under vitest 4 fake timers (the RTL asyncWrapper).     |

**Not covered by this plan:** the spec §7 deploy gates (DIG-58). Production waits for the forms project, so no task deploys.

**Pre-existing defects found while drafting:** filed as DIG-84 (stale `update_step` response), DIG-85 (`real_estate` vs `real_property`), DIG-86 (inline comments in `.env.example`) and DIG-87 (`/documents` swallows a failed `createSession`). Two were already tracked: DIG-24 (a nested `create` returns 500) and DIG-44 (the E2E timeout docs). Task 12 fixes `test_integration_flow.py`, which was posting the old expense names.

## Task order

| Task | Commit                                                                             | Spec  | Tickets          |
| ---- | ---------------------------------------------------------------------------------- | ----- | ---------------- |
| 0    | — (prerequisites)                                                                  | §3    | —                |
| 1    | 2 feat(documents): read uploads with OpenAI, selected by OCR_PROVIDER              | §9    | —                |
| 2    | 3 feat(intake): ask for documents after the filer's basic information              | §4.12 | DIG-6            |
| 3    | 4 fix(intake): save nested debts and assets by id                                  | §4.1  | DIG-21, 37       |
| 4    | 5 fix(intake): re-read the session whenever the wizard opens                       | §4.2  | DIG-1, 30        |
| 5    | 6 fix(documents): read every page of a PDF without the hybrid sidecar              | §4.8  | DIG-4            |
| 6    | 7 chore(infra): drop the odl-hybrid sidecar and the [hybrid] extra                 | §4.11 | DIG-4, 16 (part) |
| 7    | 8 fix(documents): retry an empty OpenAI reply once and record why                  | §4.9  | DIG-9            |
| 8    | 9 fix(documents): report a scan that found nothing as failed, not done             | §4.7  | DIG-7            |
| 9    | 10 fix(documents): ask the model for each account on a credit report               | §4.7  | DIG-3            |
| 10   | 11 fix(intake): show filers the amounts they already entered                       | §4.3  | DIG-2            |
| 11   | 12 fix(intake): keep saved income when the Income step reopens                     | §4.4  | DIG-41           |
| 12   | 13 fix(intake): save expenses under the names the court forms read                 | §4.5  | DIG-45           |
| 13   | 14 feat(frontend): give bills, pay stubs and credit reports their own upload areas | §4.10 | DIG-3            |
| 14   | 15 fix(frontend): show each file's real outcome and let the filer retry            | §4.10 | DIG-5, 13        |
| 15   | 16 test(e2e): follow a scanned bill from upload to Amounts Owed                    | §4.12 | DIG-1, 6         |

---

<!-- Code blocks below are edit anchors and file contents that must match the source byte for byte. Prettier would re-indent them, so it skips everything from here to the end. -->
<!-- prettier-ignore-start -->

### Task 0: Prerequisites — merge PR #14, rebase both branches, repair the local venv  (no commit; spec §3)

**Files:**
- Create: `/private/tmp/dignifi-upload-plan/requirements-local.txt`, `/private/tmp/dignifi-upload-plan/health-pr-body.md` (scratch, outside the repo, never committed)
- Modify: no tracked file. Branch refs move: `main` (fast-forward to include PR #14), `fix/health-checks-and-keep-warm` (rebased, agent trailers stripped), `fix/upload-remediation` (rebased with `--onto`). Packages in `backend/.venv` change.
- Test: none, because no code changes. Steps 2 and 4 are the gates.

**Interfaces:**
- Consumes:
  - Open PR #14 `fix/ci-e2e-cors-origin`: one commit `4df17c3`; touches only `.github/workflows/ci.yml`.
  - Local `fix/health-checks-and-keep-warm`: 4 commits on `3416f4c` (`4ecad35`, `4a6af28`, `ea99d08`, `02aa5d5`). Never pushed; no upstream.
  - Local `fix/upload-remediation`: `02aa5d5` + `2c38c99` + `f427c47` + the `docs(plan): plan the October upload remediation` commit that adds this file, plus uncommitted provider and reorder work.
- Produces:
  - `main` includes PR #14.
  - `fix/health-checks-and-keep-warm` = `main` + the same 4 commits, with no `Co-Authored-By:` lines.
  - `fix/upload-remediation` = health tip + the 2 `docs(spec)` commits + the `docs(plan)` commit (all new SHAs) + the same uncommitted work, byte-identical (hash table in Step 1). The `docs(plan)` commit sits outside the spec §9 sequence; keep it unless the owner asks to fold it into commit 1.
  - `backend/.venv` has pypdf 6.13.1, pytest 8.3.3 and `backend/.venv/bin/ruff` 0.8.5, and no torch or docling.
  - Scratch dir `/private/tmp/dignifi-upload-plan/` (on the system disk).

**Read once — facts about this machine that every task depends on (verified 2026-10-09):**
- **The repo volume has run full before.** `/Volumes/Containers`, which holds the repo and `backend/.venv`, showed `119Gi 119Gi 460Mi 100%` early on 2026-10-09 and `42Gi` free later that day. The Step 1 disk gate still applies. The CPU is Intel x86_64.
- **Tool output can be rewritten.** An `rtk` hook rewrites `git diff`, `git show`, `grep`, `vitest` and `playwright` output into summaries.
  - When you need raw output, prefix the command with `rtk proxy`.
  - **Never build a file from `grep` or `git show` stdout.** `rtk` replaced a `grep -v` result with "N matches in 1 files". Use the Write/Edit tools, `cp`, or `git restore`.
  - Don't trust the `ruff` on PATH: it is a conda alias at 0.14.13. Always use `backend/.venv/bin/ruff`.
- **Shell state does not persist between commands.** Every command below starts with `cd <absolute path> &&` and uses literal paths.
- **Commit messages.** Use exactly the spec §9 subject passed with `-m`. Add no `Co-Authored-By:` and no `Claude-Session:` lines. The owner's Rule 14 overrides the harness reminder.
- **Read before every Edit or Write.** The Edit and Write tools refuse a file you have not Read in this session, or one that changed on disk since your last Read. `cp`, `git restore`, `git stash pop` and `prettier --write` all change files on disk, so Read the file again before the next Edit or Write.
- **No deploy.** This plan ends with a local branch whose tests pass (Task 15). It does not push to Heroku or cover the spec §7 deploy gates (DIG-58), which wait for the forms project. The only outward-facing steps are the two owner gates in Task 0.
- **Scratch dir.** If writing to `/private/tmp/dignifi-upload-plan` is blocked or prompts for permission, use your session's scratchpad directory instead, and use that same path everywhere in Tasks 0–2. No hash depends on the path. Never put scratch files on `/Volumes/Containers`; keep its space for git, pip and Playwright.

- [ ] **Step 1: Write the failing test** — No test file is needed, because this task changes no code. Record the starting state instead:

```bash
mkdir -p /private/tmp/dignifi-upload-plan
df -h /Volumes/Containers
cd /Volumes/Containers/DigniFi && git rev-parse --abbrev-ref HEAD && git log --oneline -4
cd /Volumes/Containers/DigniFi && git rev-parse HEAD > /private/tmp/dignifi-upload-plan/upload-tip-before-rebase.txt
cd /Volumes/Containers/DigniFi && git hash-object CLAUDE.md README.md backend/apps/documents/services/providers/__init__.py backend/apps/documents/services/providers/base.py backend/apps/documents/services/providers/openai_provider.py backend/apps/documents/views.py backend/config/settings/base.py backend/requirements/base.txt backend/apps/documents/tests/test_openai_provider.py frontend/src/pages/DocumentUploadPage.tsx frontend/src/pages/IntakeWizard.tsx frontend/src/pages/LoginPage.tsx frontend/src/pages/RegisterPage.tsx frontend/src/pages/__tests__/IntakeWizard.test.tsx
```

Expected:
- **Disk gate.** If `Avail` for `/Volumes/Containers` is below `1.0Gi`, **STOP and ask the owner** to free space on that volume. Name the number. Do not delete anything yourself. Near 0 bytes, git, pip and Playwright can fail mid-write. It showed `460Mi` early on 2026-10-09 and `42Gi` later that day.
- The branch is `fix/upload-remediation`.
- `git log --oneline -4` shows `<sha> docs(plan): plan the October upload remediation`, `f427c47 docs(spec): move court-form fixes out of the upload remediation`, `2c38c99 docs(spec): design the October upload remediation` and `02aa5d5 test(urls): ...`.
- The hashes print in the order given and must equal:

| File | blob |
|---|---|
| CLAUDE.md | 7fe942d5a0eb94393c972db77f3800081f0d63e0 |
| README.md | b5fa1bf396cba0721f37601a5ad5c831209e902b |
| backend/apps/documents/services/providers/\_\_init\_\_.py | 36378eed8c55dc306043509d2038513fe53b0e98 |
| backend/apps/documents/services/providers/base.py | e2d701f8c5798a10855b227ec3da3a17a5a27faf |
| backend/apps/documents/services/providers/openai_provider.py | 39e6c312b981548ac3a1ff51baa6ce0ca3213902 |
| backend/apps/documents/views.py | 22829a05dc23436ff644d291fcd6d62ee7d18db9 |
| backend/config/settings/base.py | 671dc0294699111c604450d781034b97510c250c |
| backend/requirements/base.txt | 69cd51929e598fcded0ace9a200377df3d84c6dc |
| backend/apps/documents/tests/test_openai_provider.py | 900aeb6af77b58efcb6191183626297cc1344455 |
| frontend/src/pages/DocumentUploadPage.tsx | 4dab4e8795d5bb194e7338e1b9e00c6436445743 |
| frontend/src/pages/IntakeWizard.tsx | aabfe158e0871a7287840c4f2e3bd0fdfb463f9a |
| frontend/src/pages/LoginPage.tsx | bb735376c6512f2e1329735b0ebaf3c9c78114c8 |
| frontend/src/pages/RegisterPage.tsx | f063b0ca3d81efb5119ac5f530e1646109fe3fdc |
| frontend/src/pages/\_\_tests\_\_/IntakeWizard.test.tsx | f27c3260eea12c41092391f2d7cc47b8aa47243f |

If any hash differs, someone edited the work after this plan was written. Stop and ask the owner which version is canonical.

- [ ] **Step 2: Run it and confirm it fails** — show the venv drift that Step 3 repairs:

```bash
cd /Volumes/Containers/DigniFi/backend && .venv/bin/python -c "import pypdf, pytest; print(pypdf.__version__, pytest.__version__)"
ls /Volumes/Containers/DigniFi/backend/.venv/bin/ruff
```

Expected now: `3.17.0 9.0.2` (CI pins pypdf 6.13.1 and pytest 8.3.3), and `ls: ... No such file or directory`.

- [ ] **Step 3: Implement**

**3a. Stash the tracked work in progress.** Rebasing checks branches out, which a dirty tree blocks. Untracked files stay in place, and no replayed commit touches their paths.

```bash
cd /Volumes/Containers/DigniFi && git stash push -m "upload-remediation WIP: provider + reorder (Task 0)"
cd /Volumes/Containers/DigniFi && git status --short
```

Expected: only `??` lines, for `.impeccable`, `.serena/`, `DESIGN.md`, `assets/`, `backend/apps/documents/services/providers/openai_provider.py` and `backend/apps/documents/tests/test_openai_provider.py`.

**3b. OWNER GATE: merge PR #14. This is outward-facing; ask the owner before merging.**

```bash
cd /Volumes/Containers/DigniFi && gh pr view 14 --json state,mergeable,headRefName && gh pr checks 14
```

Ask the owner, in these words: "PR #14 (`fix/ci-e2e-cors-origin`, BIZ-77) must be in `main` before the upload branch can show green E2E. May I squash-merge it now with `gh pr merge 14 --squash`?"
- Merge only on an explicit yes.
- If the answer is no or not yet, **STOP the whole plan here** and pop the stash (`cd /Volumes/Containers/DigniFi && git stash pop`). Rebasing before #14 lands means rebasing twice.

On yes:

```bash
cd /Volumes/Containers/DigniFi && gh pr merge 14 --squash
cd /Volumes/Containers/DigniFi && git fetch origin main:main
cd /Volumes/Containers/DigniFi && git log --oneline -2 main && git diff --name-only 3416f4c main
```

Expected: the first line is the PR #14 commit and the second is `3416f4c chore: post-review hardening ... (#13)`. The name-only diff prints only `.github/workflows/ci.yml`. `fetch origin main:main` fast-forwards local `main`, which is not checked out.

**3c. Rebase the health branch onto `main` and strip the agent trailers.** The branch has never been pushed, and all 4 commits carry a `Co-Authored-By: Claude ...` line that the owner's Rule 14 forbids. The rebase rewrites them anyway. This exact command was rehearsed in a throwaway clone on 2026-10-09:

```bash
cd /Volumes/Containers/DigniFi && git rebase main fix/health-checks-and-keep-warm --exec 'git log -1 --format=%B | sed "/^Co-Authored-By: /d" | git commit --amend --no-verify -F -'
cd /Volumes/Containers/DigniFi && git log --oneline main..fix/health-checks-and-keep-warm
cd /Volumes/Containers/DigniFi && git diff --name-only 02aa5d5 fix/health-checks-and-keep-warm
cd /Volumes/Containers/DigniFi && git log --format=%B main..fix/health-checks-and-keep-warm | /usr/bin/grep -c "^Co-Authored-By:"
```

Expected:
- 4 commits with new SHAs and these subjects, newest first:
  - `test(urls): cover Django-rendered SPA routing, which E2E never exercises`
  - `fix(urls): stop the SPA catch-all from returning 200 for backend paths`
  - `fix(health): stop reporting status:error for a directory nothing writes to`
  - `fix(ops): track keep-warm workflow so it actually runs`
- The name-only diff prints only `.github/workflows/ci.yml`.
- The trailer count is `0`.

A conflict is impossible: PR #14 touches only `ci.yml`, and the health commits never touch it. If one appears anyway, run `git rebase --abort` and stop.

**3d. OWNER GATE: push the health branch and open its PR. This is outward-facing; ask before pushing.** Ask: "`fix/health-checks-and-keep-warm` is rebased onto `main` (4 commits, agent trailers removed). May I push it and open its PR against `main`?" If the owner says not yet, skip 3d and continue: nothing below pushes, and the upload branch stays local.

On yes, write `/private/tmp/dignifi-upload-plan/health-pr-body.md` with the Write tool, with exactly this content. If your harness asks for PR attribution lines, append them at the end.

```markdown
## Summary

Four fixes split out of the upload work so they can ship on their own:

- **fix(ops): track keep-warm workflow so it actually runs.** The workflow file existed locally but was never committed, so GitHub never scheduled it and the Eco dyno kept idling into H99 cold wakes.
- **fix(health): stop reporting status:error for a directory nothing writes to.** Drops the `disk_generated_forms` check (its directory has no consumer) and creates `MEDIA_ROOT` at image build for `disk_media`.
- **fix(urls): stop the SPA catch-all from returning 200 for backend paths.** `/health` now redirects to `/health/`, and unknown `/api/` paths return 404 instead of the React shell.
- **test(urls): cover Django-rendered SPA routing, which E2E never exercises.**

Rebased onto `main` after PR #14 (E2E CORS origin), so E2E can run green.

## Test plan

- [ ] CI: lint, backend tests (coverage at least 90%), frontend tests, E2E
- [ ] After deploy: `/health/` and `/health/detailed/` return Django JSON, and an unknown `/api/` path returns 404
```

```bash
cd /Volumes/Containers/DigniFi && git push -u origin fix/health-checks-and-keep-warm
cd /Volumes/Containers/DigniFi && gh pr create --base main --head fix/health-checks-and-keep-warm --title "fix(health): honest health checks, 404s for unknown backend paths, and a keep-warm that runs" --body-file /private/tmp/dignifi-upload-plan/health-pr-body.md
```

Report the PR URL to the owner. Do not merge it; merging is the owner's call.

**3e. Move the upload branch onto the new health tip.** This command was rehearsed as well:

```bash
cd /Volumes/Containers/DigniFi && git rebase --onto fix/health-checks-and-keep-warm 02aa5d5 fix/upload-remediation
cd /Volumes/Containers/DigniFi && git rev-parse --abbrev-ref HEAD && git log --oneline -4 && git rev-list --count main..fix/upload-remediation
cd /Volumes/Containers/DigniFi && git diff --name-only "$(cat /private/tmp/dignifi-upload-plan/upload-tip-before-rebase.txt)" fix/upload-remediation
```

Expected:
- The branch is `fix/upload-remediation`.
- The top four commits are `docs(plan): plan the October upload remediation`, `docs(spec): move court-form fixes out of the upload remediation`, `docs(spec): design the October upload remediation` (all three new SHAs) and the health tip `test(urls): ...`.
- The count is `7`.
- The name-only diff prints only `.github/workflows/ci.yml`.

Spec §4.6 still cites `2c38c99`. That SHA now lives only in the reflog, while its content is unchanged under the new SHA. Do not edit the spec.

**3f. Restore the work in progress:**

```bash
cd /Volumes/Containers/DigniFi && git stash pop
cd /Volumes/Containers/DigniFi && git status --short
cd /Volumes/Containers/DigniFi && git hash-object CLAUDE.md README.md backend/apps/documents/services/providers/__init__.py backend/apps/documents/services/providers/base.py backend/apps/documents/services/providers/openai_provider.py backend/apps/documents/views.py backend/config/settings/base.py backend/requirements/base.txt backend/apps/documents/tests/test_openai_provider.py frontend/src/pages/DocumentUploadPage.tsx frontend/src/pages/IntakeWizard.tsx frontend/src/pages/LoginPage.tsx frontend/src/pages/RegisterPage.tsx frontend/src/pages/__tests__/IntakeWizard.test.tsx
```

Expected:
- `git status --short` shows 12 ` M` lines: `CLAUDE.md`, `README.md`, the 6 backend files and the 4 frontend pages plus the test. It also shows the 6 `??` entries from 3a.
- The 14 hashes are identical to the Step 1 table.

A pop conflict can't happen, because none of those paths differ between the pre-rebase tip (recorded in Step 1) and the new tip. If one does, stop: the stash stays in `git stash list`.

**3g. Repair `backend/.venv` without the `[hybrid]` extra.** `pip install -r requirements/base.txt` would resolve `opendataloader-pdf[hybrid]` → `docling[easyocr]` → torch:
- torch has no current wheel for Intel macOS.
- 460 MiB free cannot hold it.
- The venv has never had it (`pip show torch docling` finds nothing).
- Commit 7 removes the extra anyway.

The test and dev pins are inlined rather than pulled in with `-r`, because `-r base.txt` would bring `[hybrid]` back. Write `/private/tmp/dignifi-upload-plan/requirements-local.txt` with the Write tool, with exactly this content:

```text
Django==5.0.14
psycopg2-binary==2.9.11
djangorestframework==3.15.2
djangorestframework-simplejwt==5.3.1
django-cors-headers==4.3.1
django-filter==24.1
django-environ==0.11.2
django-encrypted-model-fields==0.6.5
django-phonenumber-field[phonenumbers]==7.2.0
pypdf==6.13.1
pydantic>=2.9.0,<3.0.0
opendataloader-pdf
google-genai>=0.8
openai>=1.40
pymupdf
cryptography==44.0.1
whitenoise[brotli]~=6.9.0
pytest==8.3.3
pytest-django==4.9.0
pytest-cov==4.1.0
factory-boy==3.3.1
django-extensions==3.2.3
ipython==8.20.0
black==24.10.0
ruff==0.8.5
pre-commit==4.0.1
```

```bash
cd /Volumes/Containers/DigniFi/backend && .venv/bin/pip install --dry-run -r /private/tmp/dignifi-upload-plan/requirements-local.txt
```

Expected:
- Exit 0.
- The `Would install` line had 28 entries when this was written. It includes `pypdf-6.13.1`, `pytest-8.3.3`, `pytest-django-4.9.0`, `ruff-0.8.5`, `black-24.10.0`, `django-extensions-3.2.3`, `factory_boy-3.3.1` and `pre_commit-4.0.1`.
- It contains **no** `torch`, `docling` or `easyocr`. If it does, stop.

```bash
cd /Volumes/Containers/DigniFi/backend && .venv/bin/pip install -r /private/tmp/dignifi-upload-plan/requirements-local.txt
cd /Volumes/Containers/DigniFi/backend && .venv/bin/python -c "import importlib.util as u, pypdf, pytest; print(pypdf.__version__, pytest.__version__, u.find_spec('torch'), u.find_spec('docling'))"
cd /Volumes/Containers/DigniFi/backend && .venv/bin/ruff --version
df -h /Volumes/Containers
```

Expected: `6.13.1 8.3.3 None None`, then `ruff 0.8.5`. Record `Avail`.

The git pre-commit hook runs `backend/.venv/bin/python3.11 -m pre_commit`, so it keeps working, now on pre-commit 4.0.1. Its black, ruff and prettier environments live in `~/.cache/pre-commit`.

- [ ] **Step 4: Run tests and confirm they pass** — these set the baseline every later task compares against:

```bash
cd /Volumes/Containers/DigniFi/backend && .venv/bin/python -m pytest --cov=apps --cov=config --cov-fail-under=90 -q
cd /Volumes/Containers/DigniFi/backend && .venv/bin/ruff check .
cd /Volumes/Containers/DigniFi/backend && DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
cd /Volumes/Containers/DigniFi/frontend && npx vitest run
cd /Volumes/Containers/DigniFi/frontend && npx tsc -b
cd /Volumes/Containers/DigniFi/frontend && npm run lint
```

Expected:
- **pytest:** 0 failed, and `Required test coverage of 90% reached`. Write down the passed and xfailed counts as the baseline. For reference only, not as the expected result: on the old venv (pypdf 3.17, pytest 9.0.2) this exact tree gave `697 passed, 1 xfailed`, total coverage 94.90%.
- **ruff:** `All checks passed!`
- **makemigrations:** `No changes detected`.
- **vitest:** `Test Files 24 passed (24)` and `Tests 209 passed (209)`, measured on this exact tree. The frontend deps did not change.
- **tsc:** exit 0.
- **eslint:** no problems.

No code changed, so any failure here is pre-existing:
- Stop.
- File it in Plane, project DIG. The owner's rule is that every observed pre-existing error gets a ticket.
- Ask the owner whether to proceed.

- [ ] **Step 5: Update CLAUDE.md gotchas** — none. This task changes no tracked file.

- [ ] **Step 6: Commit** — no commit in this task. The only outward-facing actions are the two in 3b and 3d, and each needs the owner's explicit yes.

---

### Task 1: Read uploads with OpenAI, selected by OCR_PROVIDER  (Commit #2 in spec §9)

**Files:**
- Create: `backend/apps/documents/tests/test_provider_selection.py`
- Commit as-is, already untracked in the tree:
  - `backend/apps/documents/services/providers/openai_provider.py` (64 lines)
  - `backend/apps/documents/tests/test_openai_provider.py` (83 lines)
- Commit as-is, already modified in the tree:
  - `backend/apps/documents/services/providers/__init__.py:1-9` (module docstring)
  - `backend/apps/documents/services/providers/base.py:10` (the `Implementations:` line)
  - `backend/apps/documents/views.py:5-6,17,25-43` (imports and `_get_processor`)
  - `backend/config/settings/base.py:244-250` (`OPENAI_API_KEY`, `OCR_PROVIDER`, `OCR_MODEL`)
  - `backend/requirements/base.txt:14` (`openai>=1.40`)
- Modify:
  - `.env.example:24-28`: insert an OCR block between `DOJ_COUNSELING_API_KEY=tbd` (line 25) and `# Frontend` (line 27).
  - `backend/.env.example:26-27`
  - `README.md:159,164` in working-tree numbering, which is HEAD lines 153 and 158.
- Stage part of a file:
  - `CLAUDE.md`: every working-tree change except the four reorder lines, which Task 2 commits.
  - `README.md`: the two provider lines only. The landing-image hunks (working-tree lines 1–24) are never committed.
- Test: `backend/apps/documents/tests/test_provider_selection.py`, `backend/apps/documents/tests/test_openai_provider.py`

**Interfaces:**
- Consumes (all unchanged):
  - `DocumentProcessor(provider: BaseOCRProvider)` and `DocumentProcessor.process(file_bytes: bytes, mime_type: str, doc_type: str) -> ExtractionResult` (`backend/apps/documents/services/processor.py:50-63`)
  - `GeminiProvider(model: str = "gemini-2.0-flash")` (`providers/gemini.py:11-22`)
  - `_run_processing(doc_id: int) -> None` (`views.py:46-99`)
- Produces:
  - **Settings** in `config/settings/base.py`: `OPENAI_API_KEY: str` (default `""`), `OCR_PROVIDER: str` (default `"openai"`), `OCR_MODEL: str` (default `""`).
  - **`apps.documents.views._get_processor() -> DocumentProcessor`:**
    - `openai` gives `OpenAIProvider(model=settings.OCR_MODEL or "gpt-4o")`.
    - `gemini` gives `GeminiProvider(model=settings.OCR_MODEL or "gemini-2.0-flash")`.
    - Any other value raises `ImproperlyConfigured("Unknown OCR_PROVIDER '<value>'; expected 'openai' or 'gemini'.")`. This happens only when a document is read: inside `_run_processing`'s `try`, which marks the `OCRResult` FAILED. It never happens at app boot.
  - **`apps.documents.services.providers.openai_provider.OpenAIProvider(model: str = "gpt-4o")`:**
    - `classify(image_data: bytes, prompt: str) -> str` and `extract(image_data: bytes, prompt: str) -> str`.
    - Private `_complete(content: list[dict[str, Any]], *, json_mode: bool) -> str`, the single `self._client.chat.completions.create(**kwargs)` call. C3's retry lands here in commit 8.
    - The client is `OpenAI(api_key=os.environ["OPENAI_API_KEY"])`. When no `base_url` is passed, the SDK also reads `OPENAI_BASE_URL` from the environment (verified in openai 1.60, `openai/_client.py:126`); C10's fake server relies on this.
    - Commit 6 (C1) changes `extract` to `extract(self, images: list[bytes], prompt: str)`.
  - **Test fixtures later tasks may copy** from `test_provider_selection.py`: `openai_sdk` patches `apps.documents.services.providers.openai_provider.OpenAI`, and `gemini_sdk` patches `apps.documents.services.providers.gemini.genai`.
  - **CLAUDE.md "Gotchas" lines committed here** that later commits must replace or remove, with their exact current text:
    - `` - **`hybrid="docling-fast"` can't work on Heroku** — it needs the `odl-hybrid` sidecar on `localhost:5002` from `docker-compose.yml`; Heroku runs a single container. It's caught and falls back to vision OCR, so the `Hybrid server is not available` log noise is not the failure. `` (commits 6 and 7)
    - `` - **Vision fallback reads page 1 only** — `_pdf_to_image_bytes(pdf_bytes, page_index=0)`; multi-page creditor bills extract partially even on success. `` (commit 6)
    - `` - **Upload is synchronous despite the 202** — ... `` stays true through this PR (DIG-8).
  - The CLAUDE.md "File Map" line `` - `apps/documents/services/` — `processor.py` (DocumentProcessor), `draft_debt.py`, `aggregator.py` (AggregateIngestionService) `` is committed here too.

- [ ] **Step 1: Write the failing test**

Create `backend/apps/documents/tests/test_provider_selection.py`. It is black-clean at line length 100 and ruff-0.8.5-clean, verified.

```python
"""Which hosted model reads a filer's upload is a config var, not a deploy.

These tests drive a real upload through ``_run_processing`` and patch only the SDK client
classes (the network boundary), so they prove which provider and model actually receive
the document.
"""

import importlib
import json
import os
from unittest.mock import MagicMock, patch

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.districts.models import District
from apps.documents.models import DocumentType, OCRResult, OCRStatus, UploadedDocument
from apps.documents.views import _get_processor, _run_processing
from apps.intake.models import IntakeSession
from apps.users.models import User

FAKE_JPEG = b"\xff\xd8\xff\xe0fake-jpeg"
CANNED_BILL = json.dumps(
    {"creditor_name": "Chase Bank", "amount_owed": 1250.0, "confidence_score": 90}
)


@pytest.fixture
def uploaded_bill(db, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    user = User.objects.create_user(username="providerfiler", password="pass")
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=338.00,
    )
    session = IntakeSession.objects.create(user=user, district=district)
    doc = UploadedDocument.objects.create(
        session=session,
        uploaded_by=user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename="bill.jpg",
        file_size=len(FAKE_JPEG),
        mime_type="image/jpeg",
        file=SimpleUploadedFile("bill.jpg", FAKE_JPEG, content_type="image/jpeg"),
    )
    OCRResult.objects.create(
        document=doc,
        status=OCRStatus.PENDING,
        extracted_data="{}",
        confidence_scores={},
        overall_confidence=0,
    )
    return doc


@pytest.fixture
def openai_sdk():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        with patch("apps.documents.services.providers.openai_provider.OpenAI") as client_cls:
            reply = MagicMock()
            reply.choices[0].message.content = CANNED_BILL
            client_cls.return_value.chat.completions.create.return_value = reply
            yield client_cls.return_value


@pytest.fixture
def gemini_sdk():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
        with patch("apps.documents.services.providers.gemini.genai") as genai:
            genai.Client.return_value.models.generate_content.return_value.text = CANNED_BILL
            yield genai.Client.return_value


def test_a_deploy_that_names_no_provider_reads_uploads_with_openai(monkeypatch):
    """Heroku sets OPENAI_API_KEY but not OCR_PROVIDER, so the shipped default decides
    which company receives filers' documents in production."""
    import config.settings.base as base_settings

    monkeypatch.delenv("OCR_PROVIDER", raising=False)
    monkeypatch.delenv("OCR_MODEL", raising=False)
    # A developer's repo-root .env must not stand in for the shipped default.
    monkeypatch.setattr(environ.Env, "read_env", lambda *args, **kwargs: None)
    try:
        reloaded = importlib.reload(base_settings)
        assert reloaded.OCR_PROVIDER == "openai"
        assert reloaded.OCR_MODEL == ""
    finally:
        monkeypatch.undo()
        importlib.reload(base_settings)


def test_openai_reads_the_upload_with_gpt_4o_when_no_model_is_named(
    settings, uploaded_bill, openai_sdk, gemini_sdk
):
    settings.OCR_PROVIDER = "openai"
    settings.OCR_MODEL = ""

    _run_processing(uploaded_bill.id)

    assert openai_sdk.chat.completions.create.call_args.kwargs["model"] == "gpt-4o"
    gemini_sdk.models.generate_content.assert_not_called()
    assert OCRResult.objects.get(document=uploaded_bill).status == OCRStatus.COMPLETED


def test_gemini_reads_the_upload_when_ocr_provider_says_gemini(
    settings, uploaded_bill, openai_sdk, gemini_sdk
):
    settings.OCR_PROVIDER = "gemini"
    settings.OCR_MODEL = ""

    _run_processing(uploaded_bill.id)

    assert gemini_sdk.models.generate_content.call_args.kwargs["model"] == "gemini-2.0-flash"
    openai_sdk.chat.completions.create.assert_not_called()
    assert OCRResult.objects.get(document=uploaded_bill).status == OCRStatus.COMPLETED


def test_ocr_model_switches_the_model_without_a_deploy(settings, uploaded_bill, openai_sdk):
    settings.OCR_PROVIDER = "openai"
    settings.OCR_MODEL = "gpt-4o-mini"

    _run_processing(uploaded_bill.id)

    assert openai_sdk.chat.completions.create.call_args.kwargs["model"] == "gpt-4o-mini"


def test_an_unknown_provider_fails_the_upload_at_read_time_not_at_boot(
    settings, uploaded_bill, openai_sdk, gemini_sdk
):
    # This module imported the documents views without error: a bad value only
    # surfaces when a document is read.
    settings.OCR_PROVIDER = "tesseract"

    with pytest.raises(ImproperlyConfigured, match="tesseract"):
        _get_processor()

    _run_processing(uploaded_bill.id)

    assert OCRResult.objects.get(document=uploaded_bill).status == OCRStatus.FAILED
    openai_sdk.chat.completions.create.assert_not_called()
    gemini_sdk.models.generate_content.assert_not_called()
```

Why these tests are built this way:
- **Only the SDK classes are mocked.** The tests patch `OpenAI` and `genai`, the network boundary. `_get_processor`, `DocumentProcessor`, the prompt builders and `_run_processing` all run for real.
- **The upload is a JPEG on purpose.** It skips the opendataloader JVM, and it still sends exactly one image to the model after commit 6.
- **The default test reloads the settings module.** It stubs `environ.Env.read_env`, because `config/settings/base.py:32` copies the repo-root `.env` into `os.environ`, and the local `.env` sets `OCR_PROVIDER`. It then reloads `base_settings` in `finally`.
- **These assertions survive later commits.** The canned bill has a creditor name, so it stays COMPLETED after commit 9's "nothing found" rule. The unknown-provider test asserts status only, never `error_message`, which commit 9 rewrites to exception class names.
- **Verified to pass alongside the rest of the suite:** run with `apps/documents apps/intake` it gives 147 passed, 1 xfailed; with `apps/documents config` in the other order, 106 passed.

`backend/apps/documents/tests/test_openai_provider.py` already exists, untracked, with blob `900aeb6`. Commit it unchanged. Its full content, so you can recreate it if it is lost:

```python
"""Unit tests for OpenAIProvider."""

import os
from unittest.mock import MagicMock, patch

import pytest

from apps.documents.services.providers.openai_provider import OpenAIProvider


@pytest.fixture
def mock_openai_client():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        with patch("apps.documents.services.providers.openai_provider.OpenAI") as mock_openai:
            mock_response = MagicMock()
            mock_response.choices[0].message.content = '{"document_type": "pay_stub"}'
            mock_openai.return_value.chat.completions.create.return_value = mock_response
            yield mock_openai.return_value


@pytest.fixture
def provider(mock_openai_client):
    return OpenAIProvider()


def _sent_content(client) -> list:
    """The user message content of the single completion call."""
    kwargs = client.chat.completions.create.call_args.kwargs
    return kwargs["messages"][0]["content"]


class TestTextVersusVisionRouting:
    """Text-extracted PDFs must not be re-sent as images, and scanned pages must not
    be silently dropped — either mistake loses the debtor's document contents."""

    def test_markdown_only_document_is_sent_as_text(self, provider, mock_openai_client):
        provider.extract(b"", "Return ONLY a valid JSON object for this pay stub.")
        content = _sent_content(mock_openai_client)
        assert [part["type"] for part in content] == ["text"]

    def test_scanned_page_is_sent_as_an_inline_image(self, provider, mock_openai_client):
        provider.extract(b"\xff\xd8\xff", "Return ONLY a valid JSON object.")
        content = _sent_content(mock_openai_client)
        assert [part["type"] for part in content] == ["image_url", "text"]
        assert content[0]["image_url"]["url"].startswith("data:image/jpeg;base64,")

    def test_image_bytes_survive_the_round_trip_intact(self, provider, mock_openai_client):
        import base64

        provider.extract(b"\xff\xd8\xff\x00binary", "Return ONLY a valid JSON object.")
        url = _sent_content(mock_openai_client)[0]["image_url"]["url"]
        encoded = url.removeprefix("data:image/jpeg;base64,")
        assert base64.b64decode(encoded) == b"\xff\xd8\xff\x00binary"


class TestStructuredOutputGuarantee:
    """DocumentProcessor._parse_result runs json.loads on whatever comes back. Extraction
    must therefore constrain the response to JSON; classification is free-text by design."""

    def test_extraction_constrains_the_response_to_json(self, provider, mock_openai_client):
        provider.extract(b"", "Return ONLY a valid JSON object.")
        kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}

    def test_classification_does_not_constrain_the_response(self, provider, mock_openai_client):
        provider.classify(b"", "Is this a pay stub?")
        kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert "response_format" not in kwargs


class TestProviderContract:
    """BaseOCRProvider promises a str. A None completion must not leak downstream as a
    TypeError inside json.loads."""

    def test_empty_completion_becomes_empty_string(self, provider, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = None
        assert provider.extract(b"", "Return ONLY a valid JSON object.") == ""

    def test_configured_model_is_the_one_requested(self, mock_openai_client):
        OpenAIProvider(model="gpt-4o-mini").extract(b"", "Return ONLY a valid JSON object.")
        kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert kwargs["model"] == "gpt-4o-mini"
```

- [ ] **Step 2: Run it and confirm it fails** — the provider code already sits in the tree, so put `views.py` and `settings/base.py` back to HEAD for the duration of the run:

```bash
cd /Volumes/Containers/DigniFi && git stash push -m "task1-red" -- backend/apps/documents/views.py backend/config/settings/base.py
cd /Volumes/Containers/DigniFi/backend && .venv/bin/python -m pytest apps/documents/tests/test_provider_selection.py -q -rA
cd /Volumes/Containers/DigniFi && git stash pop
cd /Volumes/Containers/DigniFi && git hash-object backend/apps/documents/views.py backend/config/settings/base.py
```

Expected (verified against a HEAD copy): `4 failed, 1 passed`.
- **PASSED** `test_gemini_reads_the_upload_when_ocr_provider_says_gemini`, because HEAD hardcodes `GeminiProvider(model="gemini-2.0-flash")`.
- **FAILED** `test_openai_reads_the_upload_with_gpt_4o_when_no_model_is_named` and `test_ocr_model_switches_the_model_without_a_deploy`, both with `AttributeError: 'NoneType' object has no attribute 'kwargs'`. OpenAI is never called.
- **FAILED** `test_an_unknown_provider_fails_the_upload_at_read_time_not_at_boot` with `Failed: DID NOT RAISE <class 'django.core.exceptions.ImproperlyConfigured'>`.
- **FAILED** `test_a_deploy_that_names_no_provider_reads_uploads_with_openai` with `AttributeError: module 'config.settings.base' has no attribute 'OCR_PROVIDER'`.

After the pop, the hashes must be `22829a05dc23436ff644d291fcd6d62ee7d18db9` and `671dc0294699111c604450d781034b97510c250c`.

- [ ] **Step 3: Implement**

**3a. Code already in the tree.** Check that it matches the content below; the Task 0 hash table already proves the bytes. Create a file only if it is missing.

`backend/apps/documents/services/providers/openai_provider.py` (new, blob `39e6c31`):

```python
"""OpenAI provider for document OCR via the openai SDK."""

import base64
import os
from typing import Any

from openai import OpenAI

from .base import BaseOCRProvider


class OpenAIProvider(BaseOCRProvider):
    """
    OpenAI vision/text provider.

    Uses text mode (opendataloader-pdf extracted markdown → prompt) when image_data is empty.
    Uses vision mode (pymupdf JPEG or direct image upload) when image_data is non-empty.
    extract() sets response_format={"type": "json_object"} for reliable structured output;
    that mode requires the word "json" in the prompt, which the extraction prompts satisfy
    ("Return ONLY a valid JSON object").

    Module is named openai_provider.py rather than openai.py so it cannot shadow the
    installed ``openai`` package for anything importing it by name.
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def classify(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision(image_data, prompt)
        return self._text(prompt)

    def extract(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision(image_data, prompt, json_mode=True)
        return self._text(prompt, json_mode=True)

    def _text(self, prompt: str, *, json_mode: bool = False) -> str:
        return self._complete([{"type": "text", "text": prompt}], json_mode=json_mode)

    def _vision(self, image_data: bytes, prompt: str, *, json_mode: bool = False) -> str:
        # image/jpeg is hardcoded to match GeminiProvider: DocumentProcessor renders
        # PDF pages to JPEG and does not thread the original MIME type through.
        encoded = base64.b64encode(image_data).decode()
        return self._complete(
            [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
                {"type": "text", "text": prompt},
            ],
            json_mode=json_mode,
        )

    def _complete(self, content: list[dict[str, Any]], *, json_mode: bool) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
```

`backend/apps/documents/views.py:1-43`, the final state of that region. Only lines 5-6, 17 and 25-43 differ from HEAD; the rest of the file is unchanged.

```python
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.documents.models import DocumentType, OCRResult, OCRStatus, UploadedDocument
from apps.documents.services.aggregator import AggregateIngestionService
from apps.documents.services.draft_debt import DraftDebtCreator
from apps.documents.services.processor import DocumentProcessor
from apps.documents.services.providers.base import BaseOCRProvider
from apps.intake.models import IntakeSession

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


def _get_processor() -> DocumentProcessor:
    # Providers are imported lazily so the documents URLconf doesn't pull an OCR SDK
    # at module load (and so a missing SDK/key surfaces at OCR time, not app boot).
    provider_name = settings.OCR_PROVIDER.lower()

    if provider_name == "openai":
        from apps.documents.services.providers.openai_provider import OpenAIProvider

        provider: BaseOCRProvider = OpenAIProvider(model=settings.OCR_MODEL or "gpt-4o")
    elif provider_name == "gemini":
        from apps.documents.services.providers.gemini import GeminiProvider

        provider = GeminiProvider(model=settings.OCR_MODEL or "gemini-2.0-flash")
    else:
        raise ImproperlyConfigured(
            f"Unknown OCR_PROVIDER {provider_name!r}; expected 'openai' or 'gemini'."
        )

    return DocumentProcessor(provider=provider)
```

`backend/config/settings/base.py:243-250`:

```python
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")

# Which provider _get_processor() builds: "openai" or "gemini".
# OCR_MODEL overrides the provider's own default model when set, so a model
# change is a config var rather than a deploy.
OCR_PROVIDER = env("OCR_PROVIDER", default="openai")
OCR_MODEL = env("OCR_MODEL", default="")
```

`backend/requirements/base.txt:13-15`. Line 14 is new:

```text
google-genai>=0.8
openai>=1.40
pymupdf
```

`backend/apps/documents/services/providers/__init__.py:1-9`, the module docstring:

```python
"""OCR provider implementations.

``GeminiProvider`` and ``OpenAIProvider`` are intentionally NOT imported here —
importing them pulls the ``google-genai`` / ``openai`` SDK at module load, which
would make the entire documents URLconf (and app boot) hard-depend on an OCR SDK.
Import them lazily where used:
``from apps.documents.services.providers.gemini import GeminiProvider``
``from apps.documents.services.providers.openai_provider import OpenAIProvider``.
"""
```

`backend/apps/documents/services/providers/base.py:10` becomes `    Implementations: GeminiProvider, OpenAIProvider`.

**3b. `.env.example` (repo root).** Use the Edit tool. Comments go on their own lines. django-environ 0.11.2 keeps the spaces before an inline comment, so `OCR_PROVIDER=gemini  # x` would read as `'gemini  '`, an unknown provider. This was verified.

old_string:
```text
# External Services (TBD)
DOJ_COUNSELING_API_KEY=tbd

# Frontend
```
new_string:
```text
# External Services (TBD)
DOJ_COUNSELING_API_KEY=tbd

# OCR: the hosted model that reads uploaded documents.
# OCR_PROVIDER is "openai" (default) or "gemini". Leave OCR_MODEL empty to use the
# provider's default model (gpt-4o / gemini-2.0-flash); set it to switch models
# without a deploy. Keep comments on their own lines: an inline comment becomes part
# of the value.
OCR_PROVIDER=openai
OCR_MODEL=
OPENAI_API_KEY=your-openai-api-key

# Frontend
```

**3c. `backend/.env.example:26-27`.** Use the Edit tool.

old_string:
```text
# OCR Provider (Gemini 2.0 Flash)
GEMINI_API_KEY=your-gemini-api-key
```
new_string:
```text
# OCR_PROVIDER is "openai" (default) or "gemini". Leave OCR_MODEL empty to use the
# provider's default model (gpt-4o / gemini-2.0-flash); set it to switch models
# without a deploy. Keep comments on their own lines: an inline comment becomes part
# of the value.
OCR_PROVIDER=openai
OCR_MODEL=
OPENAI_API_KEY=your-openai-api-key
# Read only when OCR_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key
```

A pre-existing latent issue, not to be fixed here (Rule 5): `backend/.env.example:30,33,34` already carry inline comments (`DOCUMENT_STORAGE_BACKEND=filesystem  # 's3' for production`, `ENABLE_CHAPTER_11=False  # ...`). Nothing compares those values today; `env.bool` still reads False. Mention it in the Task 1 checkpoint and let the owner decide whether to file a low-priority DIG ticket.

**3d. `README.md` provider lines.** These are the working-tree lines 159 and 164. Make two Edit-tool edits.

Edit 1, old_string:
```text
- **Document Scanning**: Gemini 2.0 Flash (Google AI), opendataloader-pdf, pymupdf
```
new_string:
```text
- **Document Scanning**: OpenAI GPT-4o by default, or Gemini 2.0 Flash (chosen by `OCR_PROVIDER`; `OCR_MODEL` overrides the model), opendataloader-pdf, pymupdf
```

Edit 2, old_string:
```text
drag-and-drop upload → Gemini 2.0 Flash OCR → credit reports
```
new_string:
```text
drag-and-drop upload → OCR by the configured provider (OpenAI GPT-4o by default) → credit reports
```

After both edits, `git hash-object README.md` must print `5e3434e7fd206cae130131102d1111a663caa128`. That is the full working copy: landing hunks plus provider lines.

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd /Volumes/Containers/DigniFi/backend && .venv/bin/python -m pytest apps/documents/tests/test_provider_selection.py apps/documents/tests/test_openai_provider.py -q
cd /Volumes/Containers/DigniFi/backend && .venv/bin/python -m pytest --cov=apps --cov=config --cov-fail-under=90 -q
cd /Volumes/Containers/DigniFi/backend && .venv/bin/ruff check .
cd /Volumes/Containers/DigniFi/backend && DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
```

Expected:
- **First pytest run:** `12 passed` (5 new, plus the 7 already in `test_openai_provider.py`).
- **Full pytest run:** 0 failed. The passed count is the Task 0 baseline + 5, and the gate prints `Required test coverage of 90% reached`.
- **ruff:** `All checks passed!`
- **makemigrations:** `No changes detected`.

The frontend is untouched by this commit, so no frontend run is needed.

- [ ] **Step 5: Update CLAUDE.md gotchas** — make no new edits. The working-tree `CLAUDE.md` already holds the lines this commit makes true. Step 6 stages every change in it except the four lines that describe the reorder, which become true only in Task 2. This commit's `CLAUDE.md` therefore carries:
- The provider lines:
  - `` - **OCR provider is config-driven** — ... ``
  - `` - **`openai_provider.py`, never `openai.py`** — ... ``
  - the Architecture `` - **OCR service:** provider-agnostic. ... ``
  - the File Map entries for `apps/documents/services/providers/`, `apps/documents/services/` and `config/settings/base.py` (OCR provider vars)
- The documents-pipeline facts that are true at this commit: `Upload is synchronous despite the 202`, `hybrid="docling-fast"` can't work on Heroku, and `Vision fallback reads page 1 only`.
- The rest of the same working-tree doc refresh:
  - Form 103B 17/18
  - nested `CLAUDE.md` stubs
  - prod throttling in `production.py`
  - 67 PDF templates (counts verified 2026-10-09: 67 PDFs, 18 registry entries, 6 journeys)
  - the `apps/forms/registry.py` and Forms lines
  - the E2E persona line
  - the SOFA/FeeWaiver and AskModule page lines

  These ride along here because the spec has no docs-only commit. If they were left unstaged, the first later task to run `git add CLAUDE.md` would sweep them into an unrelated commit.

- [ ] **Step 6: Commit**

Stage the whole files first:

```bash
cd /Volumes/Containers/DigniFi && git add backend/apps/documents/services/providers/__init__.py backend/apps/documents/services/providers/base.py backend/apps/documents/services/providers/openai_provider.py backend/apps/documents/views.py backend/config/settings/base.py backend/requirements/base.txt backend/apps/documents/tests/test_openai_provider.py backend/apps/documents/tests/test_provider_selection.py .env.example backend/.env.example
```

**README.md: stage only the provider lines.** Don't use `git add -p`, which is interactive and unsupported here. Build the staged version explicitly:

```bash
cd /Volumes/Containers/DigniFi && cp README.md /private/tmp/dignifi-upload-plan/README.final.md
cd /Volumes/Containers/DigniFi && git restore README.md
```

`git restore` resets the working file to HEAD's README, so the landing hunks are gone for the moment. **Read `README.md` again** (it changed on disk), then make the same two Edit-tool edits as in 3d. Then:

```bash
cd /Volumes/Containers/DigniFi && git add README.md && git rev-parse :README.md
cd /Volumes/Containers/DigniFi && cp /private/tmp/dignifi-upload-plan/README.final.md README.md && git hash-object README.md
```

Expected: the staged blob is `1850fed3dcf1ae0efee0266a7b750ebfe61d0103`, and the restored working file is `5e3434e7fd206cae130131102d1111a663caa128`.

**CLAUDE.md: stage everything except the reorder lines.**

```bash
cd /Volumes/Containers/DigniFi && cp CLAUDE.md /private/tmp/dignifi-upload-plan/CLAUDE.full.md && git hash-object CLAUDE.md
```

The hash must be `7fe942d5a0eb94393c972db77f3800081f0d63e0`. Read `CLAUDE.md`, then make three Edit-tool edits on it:

Edit 1. Remove the two reorder gotchas. old_string:
```text
- **Document upload sits mid-wizard** — the flow is `login → /intake` step 1 → `/documents` → `/intake` steps 2–8, so uploads pre-fill the money steps. `IntakeWizard.handleNext` detours when `nextStep === 2`. Nothing currently links back to `/documents` after a skip.
- **`updateCurrentStep` is POST `/intake/sessions/{id}/update_step/`** — _not_ the PATCH that saves step data. Mocking the PATCH to assert step advancement silently captures the wrong call and passes vacuously.
- **Upload is synchronous despite the 202**
```
new_string:
```text
- **Upload is synchronous despite the 202**
```

Edit 2. Drop the detour clause from the IntakeWizard file-map line. old_string:
```text
codebtors, review); detours to `/documents` after step 1
```
new_string:
```text
codebtors, review)
```

Edit 3. Remove the auth-entry-points line; Login and Register still go to `/documents` at this commit. old_string:
```text
- `src/pages/AskModulePage.tsx` — `/ask/:formType`
- `src/pages/LandingPage.tsx`, `LoginPage.tsx`, `RegisterPage.tsx`, `TermsPage.tsx` — public routes; all three auth entry points send authenticated users to `/intake`
```
new_string:
```text
- `src/pages/AskModulePage.tsx` — `/ask/:formType`
```

```bash
cd /Volumes/Containers/DigniFi && git add CLAUDE.md && git rev-parse :CLAUDE.md
cd /Volumes/Containers/DigniFi && cp /private/tmp/dignifi-upload-plan/CLAUDE.full.md CLAUDE.md && git hash-object CLAUDE.md
cd /Volumes/Containers/DigniFi && git diff --cached --name-only && git diff --cached --numstat -- CLAUDE.md README.md
```

Expected:
- The staged `CLAUDE.md` blob is `fb3d04977d971002b68c85299a8aac8e7a9d54c9`, and the restored working file is `7fe942d5a0eb94393c972db77f3800081f0d63e0`.
- The cached name-only list has exactly 12 paths: the 10 above plus `CLAUDE.md` and `README.md`.
- The numstat is `24	10	CLAUDE.md` and `2	2	README.md`.
- Both staged docs are prettier-clean (verified), so the pre-commit prettier hook leaves them alone. That matters: pre-commit stashes the unstaged landing and reorder hunks while hooks run, and a hook rewrite would conflict with them and be rolled back.

Commit:

```bash
cd /Volumes/Containers/DigniFi && git commit -m "feat(documents): read uploads with OpenAI, selected by OCR_PROVIDER"
```

If a pre-commit hook rewrites a file (black, ruff, prettier or end-of-file-fixer), re-run the same `git add` for that file and commit again with the same `-m`. The backend files are verified black- and ruff-clean, so no rewrite is expected. Then:

```bash
cd /Volumes/Containers/DigniFi && git log -1 --format=%B && git show --stat --format=%s HEAD
cd /Volumes/Containers/DigniFi && git status --short
cd /Volumes/Containers/DigniFi && git diff --numstat -- README.md CLAUDE.md
```

Expected:
- The message is exactly `feat(documents): read uploads with OpenAI, selected by OCR_PROVIDER`, with no trailer lines. The commit shows 12 files.
- `git status --short` shows ` M CLAUDE.md`, ` M README.md`, ` M` for the 4 frontend pages and `IntakeWizard.test.tsx`, plus `?? .impeccable`, `?? .serena/`, `?? DESIGN.md` and `?? assets/`.
- The unstaged numstat is `4	1	CLAUDE.md` (Task 2's reorder lines) and `13	7	README.md` (the landing-image hunks only).
- `README.md` no longer contains `Gemini 2.0 Flash (Google AI)`. Check it with the Read tool, not with `grep`.

---

### Task 2: Ask for documents after the filer's basic information  (Commit #3 in spec §9)

**Files:**
- Create: `frontend/e2e/pages/documents.page.ts`
- Modify:
  - Page objects: `frontend/e2e/pages/login.page.ts:15-18`, `frontend/e2e/pages/register.page.ts:23-26`
  - Journey specs, each with an import, a constructor line and a step-1 change:

    | Spec | Import | Constructor | Step 1 |
    |---|---|---|---|
    | `frontend/e2e/journeys/deshawn-assets.spec.ts` | 12 | 20 | 28-30 |
    | `frontend/e2e/journeys/james-borderline.spec.ts` | 11 | 19 | 27-29 |
    | `frontend/e2e/journeys/maria-happy-path.spec.ts` | 12 | 20 | 32-34 |
    | `frontend/e2e/journeys/priya-ineligible.spec.ts` | 13 | 19 | 25-27 |
    | `frontend/e2e/journeys/sarah-simplest.spec.ts` | 12 | 20 | 28-30 |
    | `frontend/e2e/journeys/sofa-journey.spec.ts` | 15 | 28 | 48-50 |
- Commit already-modified files:
  - `frontend/src/pages/IntakeWizard.tsx:140-148`
  - `frontend/src/pages/LoginPage.tsx:24,34`
  - `frontend/src/pages/RegisterPage.tsx:33,55`
  - `frontend/src/pages/DocumentUploadPage.tsx:79-80,110`. Lines 79-80 also get the prettier reflow below.
  - `frontend/src/pages/__tests__/IntakeWizard.test.tsx:63,242-285`
  - `CLAUDE.md`: the 4 lines Task 1 left unstaged, plus one sentence.
- Test: `frontend/src/pages/__tests__/IntakeWizard.test.tsx` (vitest) and all six E2E journeys.

**Interfaces:**
- Consumes:
  - `updateCurrentStep(step: number, data?: Partial<IntakeSession>): Promise<void>` (`frontend/src/context/IntakeContext.tsx:134`). It calls POST `/intake/sessions/{id}/update_step/` and `setSession(response.session)`.
  - `IntakeLayout` shares one `IntakeProvider` across `/intake`, `/documents` and `/forms` (`frontend/src/App.tsx:54-58,76-83`).
  - The session-sync effect in `IntakeWizard.tsx:75-91` sets the step from `session.current_step` on every mount.
- Produces:
  - **Flow:** register or login → `/intake` (step 1) → Continue → `updateCurrentStep(2)` → `/documents` → **Skip for now** or **Continue** → `/intake`, which resumes at step 2 (Income).
  - **Upload-page button labels.** `DocumentUploadPage`'s button reads exactly `Skip for now` (nothing read yet) or `Continue` (`allComplete`). E2E depends on these labels (spec §4.10).
  - **`frontend/e2e/pages/documents.page.ts`:** `export class DocumentsPage { constructor(private page: Page); skip(): Promise<void> }`. This is the C9 subset.
    - `uploadBill(filePath: string): Promise<void>` and `expectDone(): Promise<void>` are **not** added here. They need the drop-zone `aria-label` pattern `${label}: drop files here or click to upload` (commit 14) and the `Upload queue` / done-row locators (commit 15). **The commit-16 task adds them to this class.**
  - **Journeys:** each creates `const documents = new DocumentsPage(page);` and calls `await documents.skip();` right after step 1's `await wizard.nextStep();`.
  - **Page objects:** `RegisterPage.register()` and `LoginPage.login()` end at `waitForURL('**/intake')`.

- [ ] **Step 1: Write the failing test**

The two vitest cases are already in `frontend/src/pages/__tests__/IntakeWizard.test.tsx`, blob `f27c326`. The route line is at line 63 and the cases at lines 242-285. They use the file's existing `renderWizard`, `fillDebtorInfoFields`, `sessionAtStep1`, `server`, `http` and `HttpResponse` (lines 1-8, 37-51, 53-68, 78-...). Their content:

```tsx
          <Route path="/documents" element={<div>DocumentUploadPage</div>} />
```

```tsx
  it('sends the filer to document upload after basic info, so uploads can pre-fill the money steps', async () => {
    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await fillDebtorInfoFields();

    await act(async () => {
      await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    });

    await waitFor(() => {
      expect(screen.getByText('DocumentUploadPage')).toBeInTheDocument();
    });
  });

  it('persists current_step 2 before detouring, so returning from upload resumes at Income rather than bouncing back to upload', async () => {
    // updateCurrentStep is POST /update_step/, not the PATCH that saves step data.
    const persistedSteps: unknown[] = [];
    server.use(
      http.post(
        'http://localhost:8000/api/intake/sessions/:id/update_step/',
        async ({ request }) => {
          const body = (await request.json()) as Record<string, unknown>;
          persistedSteps.push(body.current_step);
          return HttpResponse.json({
            session: { ...sessionAtStep1, current_step: 2 },
            message: 'Step updated.',
          });
        }
      )
    );

    renderWizard();
    await screen.findByRole('heading', { name: /your information/i, level: 2 });
    await fillDebtorInfoFields();

    await act(async () => {
      await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    });

    await waitFor(() => {
      expect(screen.getByText('DocumentUploadPage')).toBeInTheDocument();
    });
    expect(persistedSteps).toContain(2);
  });
```

The E2E test for this commit is the six existing journeys, driven through the new `DocumentsPage.skip()` (Step 3).

- [ ] **Step 2: Run it and confirm it fails**

**2a. vitest.** Put `IntakeWizard.tsx` back to HEAD, which has no detour, for the duration of the run:

```bash
cd /Volumes/Containers/DigniFi && git stash push -m "task2-red" -- frontend/src/pages/IntakeWizard.tsx
cd /Volumes/Containers/DigniFi/frontend && npx vitest run src/pages/__tests__/IntakeWizard.test.tsx
cd /Volumes/Containers/DigniFi && git stash pop && git hash-object frontend/src/pages/IntakeWizard.tsx
```

Expected (verified against a HEAD copy): `Tests 2 failed | 4 passed (6)`. Both `sends the filer to document upload after basic info, ...` and `persists current_step 2 before detouring, ...` fail with `TestingLibraryElementError: Unable to find an element with the text: DocumentUploadPage`. After the pop the hash is `aabfe158e0871a7287840c4f2e3bd0fdfb463f9a`.

**2b. E2E.** Start the local stack; Step 4 reuses it:

1. Write `/private/tmp/dignifi-upload-plan/compose.db-port.yml` with the Write tool:

   ```yaml
   services:
     db:
       ports:
         - "5433:5432"
   ```

   Something other than the compose `db` owns host `localhost:5432` (connections there fail auth), so the backend talks to `localhost:5433`. Compose merges this mapping with the base `5432:5432`. On 2026-10-09, `dignifi-db-1` was already up and healthy with both 5432 and 5433 published.

2. Start the database and prepare it. If `docker compose` cannot reach the daemon, run `colima start` first.

   ```bash
   cd /Volumes/Containers/DigniFi && docker compose -f docker-compose.yml -f /private/tmp/dignifi-upload-plan/compose.db-port.yml up -d db
   cd /Volumes/Containers/DigniFi/backend && DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_dev DJANGO_SETTINGS_MODULE=config.settings.development CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 .venv/bin/python manage.py migrate --noinput
   cd /Volumes/Containers/DigniFi/backend && DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_dev DJANGO_SETTINGS_MODULE=config.settings.development CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 .venv/bin/python manage.py loaddata ilnd_2025_data
   cd /Volumes/Containers/DigniFi/backend && DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_dev DJANGO_SETTINGS_MODULE=config.settings.development CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 .venv/bin/python manage.py seed_demo_data
   ```

   `seed_demo_data` skips personas that already exist (it prints `already exists (use --reset to recreate)`), and the journeys register fresh `e2e_<persona>_<RUN_ID>` users.

3. Start the backend with Bash `run_in_background: true`:

   ```bash
   cd /Volumes/Containers/DigniFi/backend && DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_dev DJANGO_SETTINGS_MODULE=config.settings.development CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 .venv/bin/python manage.py runserver 127.0.0.1:8000
   ```

4. With the old page objects still in place, run one journey. Playwright's `webServer` starts Vite itself (`npm run dev`, `reuseExistingServer: true`).

   ```bash
   cd /Volumes/Containers/DigniFi/frontend && rtk proxy npx playwright test --config e2e/playwright.config.ts sarah-simplest
   ```

Expected: `1 failed`, `Test timeout of 120000ms exceeded`. The error points at `e2e/pages/register.page.ts:24`, `await this.page.waitForURL('**/documents');`: registration now lands on `/intake`.

- [ ] **Step 3: Implement**

**3a. App code already in the tree.** Check it matches the content below; the Task 0 hash table proves it.

`frontend/src/pages/IntakeWizard.tsx:136-156` (`handleNext`). Lines 140-148 are new:

```tsx
    try {
      const nextStep = currentStepNumber + 1;
      await updateCurrentStep(nextStep);

      // Document upload sits between step 1 and step 2. The debtor's own details are
      // typed by hand; uploads then pre-fill the financial steps that follow, so the
      // detour has to happen before Income rather than after Review. current_step is
      // already persisted as 2, so returning to /intake resumes at Income — see the
      // session-sync effect above.
      if (nextStep === 2) {
        navigate('/documents');
        return;
      }

      setCurrentStepNumber(nextStep);
      // Contracts (6) and Codebtors (7) are optional — pre-approve so Continue stays enabled
      setCanProceed(nextStep === 6 || nextStep === 7);
    } catch (error) {
      console.error('Error advancing to next step:', error);
    }
```

`frontend/src/pages/LoginPage.tsx:24` and `:34`, and `frontend/src/pages/RegisterPage.tsx:33` and `:55`. All four lines now read:

```tsx
      navigate('/intake', { replace: true });
```

They were `navigate('/documents', { replace: true });` at HEAD.

`frontend/src/pages/DocumentUploadPage.tsx`:
- Line 110 is `{allComplete ? 'Continue' : 'Skip for now'}`; it was `'Continue to intake'`.
- Lines 78-81 hold the disclosure, which replaces the false "processed locally and never sent to any external service".

The working-tree wrap of that paragraph is **not prettier-clean**. Fix it now, because the pre-commit prettier hook would otherwise rewrite it during the commit:

```bash
cd /Volumes/Containers/DigniFi/frontend && ./node_modules/.bin/prettier --write src/pages/DocumentUploadPage.tsx && git hash-object src/pages/DocumentUploadPage.tsx
```

Expected hash: `47977c3e83411f99d2b9ca152ccecd0af6506e56`. Lines 78-81 now read:

```tsx
      <p className="text-muted">
        To read your documents, we send them to OpenAI, an outside AI service. If you&apos;d rather
        not, you can skip this step and type your information in by hand.
      </p>
```

**3b. New page object `frontend/e2e/pages/documents.page.ts`.** Write it with the Write tool; expected blob `d1119530ac3f6ee9fe63963dfb2d98cc492bda2a`.

```ts
/**
 * Documents Page Object — the upload step. IntakeWizard sends the filer here
 * after step 1 (Your Information) and before step 2 (Income).
 */

import { expect, type Page } from '@playwright/test';

export class DocumentsPage {
  constructor(private page: Page) {}

  /** Leave the upload step without uploading anything; the wizard resumes at Income. */
  async skip() {
    await this.page.waitForURL('**/documents');
    await expect(
      this.page.getByRole('heading', { level: 1, name: 'Upload your documents' })
    ).toBeVisible();
    await this.page.getByRole('button', { name: 'Skip for now', exact: true }).click();
    await this.page.waitForURL('**/intake');
  }
}
```

**3c. `frontend/e2e/pages/login.page.ts`.** Read it, then replace the whole file with the Write tool; expected blob `ac887721c1ebac3959eb9650e4ccaa9135d67690`.

```ts
import type { Page } from '@playwright/test';

export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/login');
  }

  async login(username: string, password: string) {
    await this.page.locator('input[name="username"]').fill(username);
    await this.page.locator('input[name="password"]').fill(password);
    await this.page.getByRole('button', { name: /sign in/i }).click();

    // Sign-in lands on the wizard; the upload step comes after step 1 (DocumentsPage.skip)
    await this.page.waitForURL('**/intake');
  }
}
```

**3d. `frontend/e2e/pages/register.page.ts`.** Read it, then replace the whole file with the Write tool; expected blob `e50e45f380c0970177e71f5dfd2702d1265edfb3`.

```ts
import type { Page } from '@playwright/test';

export class RegisterPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('/register');
  }

  async register(username: string, email: string, password: string) {
    await this.page.locator('input[name="email"]').fill(email);
    await this.page.locator('input[name="username"]').fill(username);
    await this.page.locator('input[name="password"]').fill(password);
    await this.page.locator('input[name="confirmPassword"]').fill(password);

    // Check both required checkboxes (UPL + Terms)
    const checkboxes = this.page.locator('.auth-checkbox');
    await checkboxes.nth(0).check();
    await checkboxes.nth(1).check();

    await this.page.getByRole('button', { name: /create account/i }).click();

    // Registration lands on the wizard; the upload step comes after step 1 (DocumentsPage.skip)
    await this.page.waitForURL('**/intake');
  }
}
```

**3e. The six journeys.** Make three Edit-tool edits per file. Each old_string occurs exactly once in its file; this was verified. The result is prettier-clean, eslint-clean and type-checks under `strict`.

Edits A and B are identical in all six files:
- Edit A. old_string: `import { WizardPage } from '../pages/wizard.page';` → new_string:
  ```ts
  import { WizardPage } from '../pages/wizard.page';
  import { DocumentsPage } from '../pages/documents.page';
  ```
- Edit B. old_string: `    const wizard = new WizardPage(page);` → new_string:
  ```ts
      const wizard = new WizardPage(page);
      const documents = new DocumentsPage(page);
  ```

Edit C differs only in the `fillDebtorInfo` argument: `DESHAWN.debtor` in `deshawn-assets.spec.ts`, `JAMES.debtor` in `james-borderline.spec.ts`, `MARIA.debtor` in `maria-happy-path.spec.ts`, `PRIYA.debtor` in `priya-ineligible.spec.ts`, `SARAH.debtor` in `sarah-simplest.spec.ts`, and `debtorData` in `sofa-journey.spec.ts`. For `deshawn-assets.spec.ts`, old_string:

```ts
    await wizard.fillDebtorInfo(DESHAWN.debtor);
    await wizard.nextStep();
```
new_string:
```ts
    await wizard.fillDebtorInfo(DESHAWN.debtor);
    await wizard.nextStep();

    // Uploads come between basic info and Income; this journey types everything in
    await documents.skip();
```

Make the same Edit C in the other five files, substituting each file's argument in both old_string and new_string. For example, `sofa-journey.spec.ts` uses old_string `    await wizard.fillDebtorInfo(debtorData);\n    await wizard.nextStep();\n` and the same two added lines.

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd /Volumes/Containers/DigniFi/frontend && npx vitest run src/pages/__tests__/IntakeWizard.test.tsx
cd /Volumes/Containers/DigniFi/frontend && npx vitest run
cd /Volumes/Containers/DigniFi/frontend && npx tsc -b
cd /Volumes/Containers/DigniFi/frontend && npm run lint
cd /Volumes/Containers/DigniFi/frontend && ./node_modules/.bin/prettier --check "e2e/**/*.ts" src/pages/DocumentUploadPage.tsx
cd /Volumes/Containers/DigniFi/frontend && rtk proxy npx playwright test --config e2e/playwright.config.ts --list
cd /Volumes/Containers/DigniFi/frontend && rtk proxy npm run e2e
```

Expected:
- **IntakeWizard file:** `6 passed`.
- **Full vitest:** `Test Files 24 passed (24)` and `Tests 209 passed (209)`, the Task 0 baseline. The two cases were already counted there.
- **tsc:** exit 0. It covers `src` only; `tsconfig.app.json` includes `["src"]`.
- **eslint:** clean. `eslint .` lints `e2e/**/*.ts` too.
- **prettier:** all files use Prettier code style.
- **`--list`:** `Total: 6 tests in 6 files`. It compiles every spec without starting servers.
- **E2E:** `6 passed`. The backend from 2b is still running, and Playwright starts Vite.

If a journey fails *after* `documents.skip()` at a step this commit does not touch, it is pre-existing. Do not patch around it:
- Record the failing step and the `test-results/*/error-context.md`.
- File it in Plane (DIG).
- Ask the owner before going on. Spec §9 requires E2E to run at this commit.

Afterwards, stop the background `runserver` task. Leave the `db` container running; it was up before this plan.

- [ ] **Step 5: Update CLAUDE.md gotchas**

The working-tree `CLAUDE.md` still holds the 4 reorder lines that Task 1 left unstaged:
- `Document upload sits mid-wizard`
- ``updateCurrentStep` is POST``
- the IntakeWizard `; detours to /documents after step 1` clause
- the auth-entry-points line

This commit makes them true. Task 1 restored `CLAUDE.md` with `cp`, so **Read it again**, then add one sentence with the Edit tool.

old_string:
```text
Nothing currently links back to `/documents` after a skip.
```
new_string:
```text
Nothing currently links back to `/documents` after a skip. E2E journeys pass the detour with `DocumentsPage.skip()` (`e2e/pages/documents.page.ts`) after step 1.
```

The resulting gotcha line reads in full:

```text
- **Document upload sits mid-wizard** — the flow is `login → /intake` step 1 → `/documents` → `/intake` steps 2–8, so uploads pre-fill the money steps. `IntakeWizard.handleNext` detours when `nextStep === 2`. Nothing currently links back to `/documents` after a skip. E2E journeys pass the detour with `DocumentsPage.skip()` (`e2e/pages/documents.page.ts`) after step 1.
```

- [ ] **Step 6: Commit**

```bash
cd /Volumes/Containers/DigniFi && git add frontend/src/pages/IntakeWizard.tsx frontend/src/pages/LoginPage.tsx frontend/src/pages/RegisterPage.tsx frontend/src/pages/DocumentUploadPage.tsx frontend/src/pages/__tests__/IntakeWizard.test.tsx frontend/e2e/pages/documents.page.ts frontend/e2e/pages/login.page.ts frontend/e2e/pages/register.page.ts frontend/e2e/journeys/deshawn-assets.spec.ts frontend/e2e/journeys/james-borderline.spec.ts frontend/e2e/journeys/maria-happy-path.spec.ts frontend/e2e/journeys/priya-ineligible.spec.ts frontend/e2e/journeys/sarah-simplest.spec.ts frontend/e2e/journeys/sofa-journey.spec.ts CLAUDE.md
cd /Volumes/Containers/DigniFi && git diff --cached --name-only && git rev-parse :CLAUDE.md :frontend/src/pages/DocumentUploadPage.tsx :frontend/e2e/pages/documents.page.ts
cd /Volumes/Containers/DigniFi && git commit -m "feat(intake): ask for documents after the filer's basic information"
```

Expected before the commit:
- 15 cached paths.
- `CLAUDE.md` = `80afa8c17e6e3d615ad1db79d300487b426a269e`, `DocumentUploadPage.tsx` = `47977c3e83411f99d2b9ca152ccecd0af6506e56`, `documents.page.ts` = `d1119530ac3f6ee9fe63963dfb2d98cc492bda2a`.

`CLAUDE.md` and every staged `.ts` and `.tsx` file are prettier-clean (verified), and eslint already passes. If pre-commit's prettier or `eslint --fix` still rewrites a file, `git add` that same file and commit again with the same `-m`.

After the commit:

```bash
cd /Volumes/Containers/DigniFi && git log -1 --format=%B && git show --stat --format=%s HEAD && git status --short
```

Expected:
- The message is exactly `feat(intake): ask for documents after the filer's basic information`, with no trailers. The commit shows 15 files.
- `git status --short` shows only ` M README.md` (the landing-image hunks, which never get committed), `?? .impeccable`, `?? .serena/`, `?? DESIGN.md` and `?? assets/`. Nothing from the provider or reorder work remains unstaged.

---

### Task 3: Save nested debts and assets by id  (Commit #4 in spec §9)

**Files:**
- Modify: `backend/apps/intake/serializers.py:218-224`. Insert `NestedAssetInfoSerializer`, `NestedDebtInfoSerializer` and `_save_rows_by_id` between the end of `DebtInfoSerializer` (line 221) and `class IntakeSessionSerializer` (line 224).
- Modify: `backend/apps/intake/serializers.py:234-235`. The nested `assets` / `debts` fields.
- Modify: `backend/apps/intake/serializers.py:299`. The `update()` docstring line.
- Modify: `backend/apps/intake/serializers.py:322-331`. The replace-all block in `update()`.
- Create: `backend/apps/intake/tests/test_session_nested_save.py`
- Modify: `CLAUDE.md:25`. Add one gotcha directly after the line starting `- **Enum mismatches are silent**`.
- Test: `backend/apps/intake/tests/test_session_nested_save.py`

Line numbers were verified against the working tree on `fix/upload-remediation` before Task 1. Tasks 1–2 do not touch `serializers.py`.

**Interfaces:**
- Consumes:
  - Spec §4.1 (DIG-21, DIG-37). Today `IntakeSessionSerializer.update` deletes and recreates every nested row on each save. That wipes `account_number` (write-only), `source_document` and `is_secured` (neither is in the serializer). Re-sending a loaded row, which carries `session`, also raises `TypeError: create() got multiple values for keyword argument 'session'` (a 500).
  - The existing `AssetInfoSerializer` (`serializers.py:151`) and `DebtInfoSerializer` (`serializers.py:187`).
  - `IntakeSessionViewSet.partial_update` (`backend/apps/intake/views.py:101-113`), unchanged. It still clears `is_draft` on any PATCH that includes `debts`; that is DIG-14 (spec §6).
  - `DebtViewSet` / `AssetViewSet` (`views.py:467-515`), unchanged. They keep the base serializers, so per-item create never accepts a client id.
  - Nothing from Tasks 1–2.
- Produces:
  - Contract C11, `class NestedDebtInfoSerializer(DebtInfoSerializer)` and `class NestedAssetInfoSerializer(AssetInfoSerializer)`, each with `id = serializers.IntegerField(required=False)`. `IntakeSessionSerializer.debts` / `.assets` use them.
  - Module-private `_save_rows_by_id(session, model, rows) -> None`.
  - Behaviour later tasks rely on (Task 4 re-read, Task 10 readable amounts, Task 15 E2E save + reload), for `PATCH /api/intake/sessions/{id}/` (and `update_step` with `data`) carrying `debts` or `assets`:
    - A row whose `id` is one of this session's rows updates only the keys it sent.
    - A row with no id, an unknown id or another user's id is created on this session.
    - A stored row the payload left out is deleted.
    - A nested `session` is ignored.

- [ ] **Step 1: Write the failing test**

Create `backend/apps/intake/tests/test_session_nested_save.py`:

```python
"""Saving the Assets and Amounts Owed steps updates rows in place (DIG-21, DIG-37).

Business intent: the wizard sends back the rows it loaded. A row must keep what the
browser never receives (the encrypted account number, the link to the scanned bill,
the secured flag), a corrected amount must save instead of crashing, and a nested row
can only ever change the filer's own session.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.documents.models import DocumentType, UploadedDocument
from apps.intake.models import AssetInfo, DebtInfo, IntakeSession
from apps.users.models import User


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


def _scanned_car_loan(session):
    bill = UploadedDocument.objects.create(
        session=session,
        uploaded_by=session.user,
        document_type=DocumentType.CREDITOR_BILL,
        file="bill.pdf",
        original_filename="Ally_bill.pdf",
        file_size=100,
        mime_type="application/pdf",
    )
    return DebtInfo.objects.create(
        session=session,
        creditor_name="Ally Auto",
        debt_type="auto_loan",
        priority_classification="secured",
        account_number="4111222233334444",
        amount_owed=Decimal("500.00"),
        is_secured=True,
        source_document=bill,
        is_draft=True,
    )


def _checking_account(session):
    return AssetInfo.objects.create(
        session=session,
        asset_type="bank_account",
        description="Checking",
        current_value=Decimal("800.00"),
        amount_owed=Decimal("0.00"),
        account_number="998877",
        financial_institution="First Bank",
    )


def _session_url(session):
    return f"/api/intake/sessions/{session.pk}/"


def _rows_as_received(client, session, key):
    """The nested rows exactly as the wizard receives them from GET."""
    response = client.get(_session_url(session))
    assert response.status_code == 200
    return [dict(row) for row in response.data[key]]


def test_filer_can_correct_the_amount_on_a_debt_loaded_from_the_server(filer):
    client, session = filer
    debt = _scanned_car_loan(session)
    [row] = _rows_as_received(client, session, "debts")
    row["amount_owed"] = "650.00"

    response = client.patch(_session_url(session), {"debts": [row]}, format="json")

    assert response.status_code == 200
    saved = DebtInfo.objects.get(session=session)
    assert saved.pk == debt.pk
    assert saved.amount_owed == Decimal("650.00")


def test_filer_can_correct_the_value_of_an_asset_loaded_from_the_server(filer):
    client, session = filer
    asset = _checking_account(session)
    [row] = _rows_as_received(client, session, "assets")
    row["current_value"] = "950.00"

    response = client.patch(_session_url(session), {"assets": [row]}, format="json")

    assert response.status_code == 200
    saved = AssetInfo.objects.get(session=session)
    assert saved.pk == asset.pk
    assert saved.current_value == Decimal("950.00")


def test_resaving_a_session_exactly_as_received_keeps_amounts_account_numbers_and_scan_links(
    filer,
):
    client, session = filer
    debt = _scanned_car_loan(session)
    asset = _checking_account(session)
    received = client.get(_session_url(session)).data

    response = client.patch(
        _session_url(session),
        {"debts": received["debts"], "assets": received["assets"]},
        format="json",
    )

    assert response.status_code == 200
    kept_debt = DebtInfo.objects.get(session=session)
    assert kept_debt.pk == debt.pk
    assert kept_debt.amount_owed == Decimal("500.00")
    assert kept_debt.account_number == "4111222233334444"
    assert kept_debt.source_document_id == debt.source_document_id
    assert kept_debt.is_secured is True
    kept_asset = AssetInfo.objects.get(session=session)
    assert kept_asset.pk == asset.pk
    assert kept_asset.current_value == Decimal("800.00")
    assert kept_asset.amount_owed == Decimal("0.00")
    assert kept_asset.account_number == "998877"


def test_saving_amounts_owed_keeps_sent_rows_adds_new_ones_and_drops_removed_ones(filer):
    client, session = filer
    kept = DebtInfo.objects.create(
        session=session,
        creditor_name="Kept Card",
        debt_type="credit_card",
        amount_owed=Decimal("100.00"),
        account_number="1111",
    )
    removed = DebtInfo.objects.create(
        session=session,
        creditor_name="Paid Off Clinic",
        debt_type="medical",
        amount_owed=Decimal("50.00"),
    )

    response = client.patch(
        _session_url(session),
        {
            "debts": [
                {"id": kept.pk, "creditor_name": "Kept Card"},
                {"creditor_name": "New Clinic", "debt_type": "medical", "amount_owed": "75.00"},
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    rows = {d.creditor_name: d for d in DebtInfo.objects.filter(session=session)}
    assert set(rows) == {"Kept Card", "New Clinic"}
    assert rows["Kept Card"].pk == kept.pk
    assert rows["Kept Card"].account_number == "1111"
    assert rows["New Clinic"].amount_owed == Decimal("75.00")
    assert not DebtInfo.objects.filter(pk=removed.pk).exists()


def test_a_nested_row_naming_another_users_session_lands_on_the_owners_session_only(
    filer, other_session
):
    client, session = filer

    response = client.patch(
        _session_url(session),
        {
            "debts": [
                {
                    "session": other_session.pk,
                    "creditor_name": "Owner Clinic",
                    "debt_type": "medical",
                    "amount_owed": "75.00",
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    assert not DebtInfo.objects.filter(session=other_session).exists()
    assert DebtInfo.objects.get(session=session).creditor_name == "Owner Clinic"


def test_a_nested_row_carrying_another_users_row_id_never_changes_that_row(filer, other_session):
    client, session = filer
    their_debt = DebtInfo.objects.create(
        session=other_session,
        creditor_name="Their Bank",
        debt_type="credit_card",
        amount_owed=Decimal("900.00"),
    )

    response = client.patch(
        _session_url(session),
        {
            "debts": [
                {
                    "id": their_debt.pk,
                    "creditor_name": "Owner Clinic",
                    "debt_type": "medical",
                    "amount_owed": "75.00",
                }
            ]
        },
        format="json",
    )

    assert response.status_code == 200
    their_debt.refresh_from_db()
    assert their_debt.session_id == other_session.pk
    assert their_debt.creditor_name == "Their Bank"
    assert their_debt.amount_owed == Decimal("900.00")
    own = DebtInfo.objects.get(session=session)
    assert own.creditor_name == "Owner Clinic"
    assert own.pk != their_debt.pk
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
cd /Volumes/Containers/DigniFi/backend
.venv/bin/python -m pytest apps/intake/tests/test_session_nested_save.py -q --tb=line
```

Expected: `5 failed, 1 passed`. This was verified on a copy of today's tree.

- The DIG-37 crash. These four fail with `TypeError: django.db.models.query.QuerySet.create() got multiple values for keyword argument 'session'`, raised from `serializers.py` `update()`:
  - `test_filer_can_correct_the_amount_on_a_debt_loaded_from_the_server`
  - `test_filer_can_correct_the_value_of_an_asset_loaded_from_the_server`
  - `test_resaving_a_session_exactly_as_received_keeps_amounts_account_numbers_and_scan_links`
  - `test_a_nested_row_naming_another_users_session_lands_on_the_owners_session_only`
- `test_saving_amounts_owed_keeps_sent_rows_adds_new_ones_and_drops_removed_ones` fails with `decimal.InvalidOperation: [<class 'decimal.ConversionSyntax'>]` from `apps/intake/fields.py:63`. Replace-all recreated "Kept Card" with no amount.
- `test_a_nested_row_carrying_another_users_row_id_never_changes_that_row` **passes today**, and that is intended. Today `id` is read-only and dropped. Step 3 makes it writable, and this test pins down that a foreign id still never reaches another user's row.

- [ ] **Step 3: Implement**

All edits are in `backend/apps/intake/serializers.py`.

**3a.** Insert the nested serializers and the helper. Replace lines 218–224:

```python
    def get_source_document_name(self, obj) -> str | None:
        if obj.source_document:
            return obj.source_document.original_filename
        return None


class IntakeSessionSerializer(serializers.ModelSerializer):
```

with:

```python
    def get_source_document_name(self, obj) -> str | None:
        if obj.source_document:
            return obj.source_document.original_filename
        return None


class NestedAssetInfoSerializer(AssetInfoSerializer):
    """An asset row inside a session save.

    The id is writable so a row the wizard loaded updates in place. AssetViewSet keeps
    the base serializer, so per-item create never accepts a client id.
    """

    id = serializers.IntegerField(required=False)


class NestedDebtInfoSerializer(DebtInfoSerializer):
    """A debt row inside a session save. See NestedAssetInfoSerializer."""

    id = serializers.IntegerField(required=False)


def _save_rows_by_id(session, model, rows):
    """Save a session's nested assets or debts by id.

    A row whose id is one of this session's rows updates only the fields it sent, so
    what the browser never received (account numbers, the scanned-bill link, the
    secured flag) survives. Any other row is created on this session, so a client-sent
    ``session`` or another user's id never touches another session. Stored rows the
    payload left out are deleted.
    """
    existing = {row.pk: row for row in model.objects.filter(session=session)}
    kept = set()
    for data in rows:
        data.pop("session", None)
        row = existing.get(data.pop("id", None))
        if row is None:
            model.objects.create(session=session, **data)
            continue
        for attr, value in data.items():
            setattr(row, attr, value)
        row.save()
        kept.add(row.pk)
    model.objects.filter(pk__in=existing.keys() - kept).delete()


class IntakeSessionSerializer(serializers.ModelSerializer):
```

Notes:
- `existing` is a snapshot taken before any create, and only snapshot pks that were not kept are deleted. A fresh `exclude(pk__in=kept)` after the creates would delete the rows just created.
- PATCH is partial, and DRF propagates `partial` to nested fields through `self.root.partial`. A row sent without `amount_owed` or `current_value` therefore leaves the stored value alone.
- The declared `id` overrides the parent `Meta.read_only_fields` entry for `id`. Step 2's same-pk assertions prove that the id reaches `validated_data`.

**3b.** Use the nested serializers. Replace lines 234–235:

```python
    assets = AssetInfoSerializer(many=True, required=False)
    debts = DebtInfoSerializer(many=True, required=False)
```

with:

```python
    assets = NestedAssetInfoSerializer(many=True, required=False)
    debts = NestedDebtInfoSerializer(many=True, required=False)
```

**3c.** Docstring. Replace line 299:

```python
        For assets/debts, replaces entire list (for simplicity in MVP).
```

with:

```python
        Saves assets/debts by id (see _save_rows_by_id).
```

**3d.** Replace the replace-all block at lines 322–331:

```python
        # For MVP: Replace assets/debts entirely (future: partial updates)
        if assets_data is not None:
            instance.assets.all().delete()
            for asset_data in assets_data:
                AssetInfo.objects.create(session=instance, **asset_data)

        if debts_data is not None:
            instance.debts.all().delete()
            for debt_data in debts_data:
                DebtInfo.objects.create(session=instance, **debt_data)
```

with:

```python
        if assets_data is not None:
            _save_rows_by_id(instance, AssetInfo, assets_data)

        if debts_data is not None:
            _save_rows_by_id(instance, DebtInfo, debts_data)
```

Leave everything else alone:
- `create()` (lines 258–292): not part of §4.1.
- Debtor, income and expense `update_or_create`: unchanged per §4.1.
- `views.py`.

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd /Volumes/Containers/DigniFi/backend
.venv/bin/python -m pytest apps/intake/tests/test_session_nested_save.py -q --tb=line
.venv/bin/python -m pytest -q --tb=line
.venv/bin/python -m pytest --cov=apps --cov=config --cov-fail-under=90 -q --tb=line
.venv/bin/ruff check .
.venv/bin/black --line-length 100 --check apps/intake/serializers.py apps/intake/tests/test_session_nested_save.py
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
```

Expected:
- The new test: `6 passed`.
- The full suite: `0 failed`. These existing tests send nested rows and must stay green:
  - `apps/intake/tests/test_views.py::test_debts_patch_clears_is_draft`
  - `apps/intake/tests/test_integration_flow.py`
  - `apps/intake/tests/test_e2e_intake.py`
- Coverage: at least 90%.
- Ruff: `All checks passed!`
- Black: `2 files would be left unchanged.`
- Migrations: `No changes detected`.

Two notes on the tooling:
- Task 0 Step 3g installed ruff 0.8.5 and black 24.10.0 into `backend/.venv`, matching CI (`ci.yml:26`) and `.pre-commit-config.yaml`. Never use the conda `ruff` on PATH (0.14.x).
- Pre-commit also runs black 24.10.0 at line length 100 on `backend/`.

- [ ] **Step 5: Update CLAUDE.md gotchas**

In the root `CLAUDE.md` "Gotchas" list, insert this line directly after the line that starts `- **Enum mismatches are silent**`:

```markdown
- **Nested debts and assets save by id** — `IntakeSessionSerializer.update` upserts `debts`/`assets` through `_save_rows_by_id`: a row carrying one of this session's ids updates only the keys it sends, a row without one (or with an unknown or foreign id) is created on this session, and a stored row missing from the payload is **deleted**, so send every row you want to keep. A nested `session` is ignored. Fields the browser never receives (`account_number`, `source_document`, `is_secured`) survive a re-save. `DebtViewSet`/`AssetViewSet` keep the base serializers, so per-item create never takes a client id.
```

No existing gotcha becomes false.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/Containers/DigniFi
git add backend/apps/intake/serializers.py backend/apps/intake/tests/test_session_nested_save.py
git diff CLAUDE.md
git add CLAUDE.md
git diff --cached --stat
git commit -m "fix(intake): save nested debts and assets by id"
```

Notes on staging:
- **`git diff CLAUDE.md` before `git add CLAUDE.md`:** it must show only this task's Step 5 hunk, the one added line starting `- **Nested debts and assets save by id**`. Tasks 1–2 committed every other `CLAUDE.md` change. If anything else appears, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it.
- **Expected `git diff --cached --stat`:** exactly 3 files, `CLAUDE.md`, `backend/apps/intake/serializers.py` and `backend/apps/intake/tests/test_session_nested_save.py`.
- **Never stage** `.serena/`, `DESIGN.md`, `assets/`, `.impeccable` or README hunks.
- **The commit message** is exactly the line above, with no body and no `Co-Authored-By` or other trailer.
- **If pre-commit rewrites a file** (black, or prettier on `CLAUDE.md`), re-stage the same paths, including `git add CLAUDE.md`. Then rerun the same `git commit` command.

---

### Task 4: Re-read the session whenever the wizard opens  (Commit #5 in spec §9)

Tickets DIG-1, DIG-30. Spec §4.2, contract C7.

Why: the wizard used to fill its steps once per mount from the session held in `IntakeContext`. That copy was set by `update_step` before the filer uploaded anything on `/documents`, so a draft debt from a scanned bill never reached Amounts Owed, and the next autosave of step 5 deleted it. Now every wizard entry re-reads the session from the server and renders no step (so no autosave can fire) until that read returns.

**Files:**
- Modify: `frontend/src/context/IntakeContext.tsx:24-25` (action types), `:83-104` (`createSession`), `:106-129` (`loadSession`)
- Modify: `frontend/src/pages/IntakeWizard.tsx:11-14` (imports), `:51-57` (context destructure and refs), `:71-91` (mount effect), `:333-358` (loading render)
- Modify: `CLAUDE.md` Gotchas list (`:20-53`; one bullet appended after the last bullet, line 53 today)
- Test: `frontend/src/pages/__tests__/IntakeWizard.test.tsx` (imports at lines 4 and 7; new `describe` appended after line 323)
- Test: `frontend/src/context/__tests__/IntakeContext.test.tsx:118-141` (make the 404 test meaningful, add one test after it)
- No change: `frontend/src/pages/DocumentUploadPage.tsx`. Its Continue / Skip button already calls only `navigate('/intake')` (line 106), which is all spec §4.2 asks of it. Do not add a refresh there.

Line numbers are positions on `fix/upload-remediation` once Task 2 (commit 3) has committed the reorder; Task 2 does not move these lines. Apply every hunk by matching its text.

**Interfaces:**
- Consumes: `api.intake.getSession(sessionId: number): Promise<IntakeSession>` and `api.intake.createSession(data)` (`frontend/src/api/client.ts:307-320`); `APIClientError` with `statusCode: number` (`client.ts:82-92`; the field is `statusCode`, there is no `status`); `Button` from `frontend/src/components/common`.
- Produces:
  - C7 `loadSession(sessionId: number): Promise<IntakeSession>`: resolves with the session as the server holds it now; rejects with the `APIClientError`; removes `localStorage.current_session_id` only when `err.statusCode === 404`.
  - `createSession(districtId: number): Promise<IntakeSession>`: now resolves with the created session (was `Promise<void>`; existing callers ignore the value).
  - In `IntakeWizard.tsx`, one mount effect whose `.then((fresh) => { ... })` block fills step state with one line per slice (`if (fresh.debtor_info) setDebtorData(fresh.debtor_info);` through `if (fresh.debts) setDebtsData(fresh.debts);`). Task 10 (commit 11) edits the `assets` / `debts` lines of this block; Task 12 (commit 13) edits the `expense_info` line.
  - Wizard state `sessionRead: 'pending' | 'failed' | 'done'`; steps render only at `'done'`.

Design notes the code depends on:
- The id to read is fixed once, at mount (`useState` initializer): the context session's id, else `current_session_id`, else `null` (a new filer, who gets `createSession(1)` as before). It must not be re-derived on Try again: on a cold load, the provider's own startup effect (`IntakeContext.tsx:56-64`, unchanged per spec, DIG-11) still deletes `current_session_id` on any error, so re-deriving would create a new empty session and lose the filer's place.
- A 404 means the saved session is gone or belongs to another account (a shared computer). Retrying cannot help, so the wizard starts a new session, which is what happens today on that path.
- The effect uses a `cancelled` flag and no "already started" ref. Under `<StrictMode>` (`main.tsx`) React runs the effect, its cleanup and the effect again, keeping refs; a ref guard would block the second run while the cleanup cancelled the first, leaving the wizard on "Loading your information..." forever. Two GETs in dev are fine.
- State is set only inside `.then` / `.catch` and the Try again click handler, never synchronously in the effect body (`react-hooks/set-state-in-effect` is on).
- The effect lists only `readAttempt`: `createSession` and `loadSession` are new closures on every render, so listing them would re-read on every render.

- [ ] **Step 1: Write the failing tests**

In `frontend/src/pages/__tests__/IntakeWizard.test.tsx`, change the two import lines:

Replace:
```tsx
import { MemoryRouter, Routes, Route } from 'react-router-dom';
```
With:
```tsx
import { MemoryRouter, Routes, Route, useNavigate } from 'react-router-dom';
```

Replace:
```tsx
import { IntakeProvider } from '../../context/IntakeContext';
```
With:
```tsx
import { IntakeProvider, useIntake } from '../../context/IntakeContext';
```

Append at the end of the file (after the closing `});` of `describe('IntakeWizard autosave', ...)`):
```tsx

// ===========================================================================
// Re-reading the session on every wizard entry (DIG-1, DIG-30)
// ===========================================================================

/** Session sitting on step 5 (Amounts Owed) with no debts yet. */
const sessionAtStep5 = {
  ...sessionAtStep1,
  current_step: 5,
  debtor_info: { first_name: 'Jane', last_name: 'Doe' },
};

/** A draft debt the document processor created from an uploaded bill. */
const debtFromUploadedBill = {
  id: 7,
  session: 1,
  data_source: 'uploaded_document',
  creditor_name: 'Lakeshore Medical Group',
  debt_type: 'medical',
  priority_classification: 'unsecured',
  monthly_payment: '0.00',
  is_in_collections: false,
  notes: '',
  created_at: '2026-10-09T10:00:00Z',
  updated_at: '2026-10-09T10:00:00Z',
  is_draft: true,
  source_document_name: 'lakeshore-bill.pdf',
};

/** Stands in for DocumentUploadPage, whose Continue button only navigates to /intake. */
function UploadPageStandIn() {
  const navigate = useNavigate();
  const { session } = useIntake();
  if (!session) return <p>Loading uploads</p>;
  return (
    <button type="button" onClick={() => navigate('/intake')}>
      Continue
    </button>
  );
}

describe('IntakeWizard session re-read', { timeout: 15_000 }, () => {
  it('shows a debt read from an uploaded bill at Amounts Owed when the filer continues from uploads, without a reload', async () => {
    // The filer reached Amounts Owed, went back to /documents (header link or browser Back)
    // and uploaded a bill. The provider loaded the session before the upload, so the copy
    // in context has no debts; only the server holds the draft.
    let serverSession: Record<string, unknown> = sessionAtStep5;
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(serverSession)
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(serverSession)
      )
    );
    localStorage.setItem('current_session_id', '1');
    render(
      <MemoryRouter initialEntries={['/documents']}>
        <IntakeProvider>
          <Routes>
            <Route path="/intake" element={<IntakeWizard />} />
            <Route path="/documents" element={<UploadPageStandIn />} />
          </Routes>
        </IntakeProvider>
      </MemoryRouter>
    );
    const continueButton = await screen.findByRole('button', { name: 'Continue' });

    // The bill has been read: the server now holds a draft debt the context never saw.
    serverSession = { ...sessionAtStep5, debts: [debtFromUploadedBill] };
    await userEvent.click(continueButton);

    await screen.findByRole('heading', { name: /amounts owed/i, level: 2 });
    expect(screen.getByDisplayValue('Lakeshore Medical Group')).toBeInTheDocument();
    expect(screen.getByText('From scan')).toBeInTheDocument();
  });

  it("keeps the filer's saved place and lets them try again when the re-read fails", async () => {
    let serverBusy = true;
    let sessionsCreated = 0;
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        serverBusy
          ? HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
          : HttpResponse.json({ ...sessionAtStep1, current_step: 3 })
      ),
      http.post('http://localhost:8000/api/intake/sessions/', () => {
        sessionsCreated += 1;
        return HttpResponse.json(
          { session: sessionAtStep1, message: 'Session created.' },
          { status: 201 }
        );
      }),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({ ...sessionAtStep1, current_step: 3 })
      )
    );

    renderWizard();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "We couldn't get your latest information just now. Please try again in a moment."
    );
    // No step renders after a failed read, so autosave has nothing stale to send.
    expect(screen.queryByRole('heading', { level: 2 })).not.toBeInTheDocument();

    serverBusy = false;
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(
      await screen.findByRole('heading', { name: /expenses/i, level: 2 })
    ).toBeInTheDocument();
    // The filer kept their own session: nothing started a new one behind their back.
    expect(sessionsCreated).toBe(0);
  });

  it('starts one new session when the saved one is gone or belongs to someone else', async () => {
    // A shared computer: the resume pointer names another account's session, so DRF says 404.
    let sessionsCreated = 0;
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({ detail: 'Not found.' }, { status: 404 })
      ),
      http.post('http://localhost:8000/api/intake/sessions/', () => {
        sessionsCreated += 1;
        return HttpResponse.json(
          { session: { ...sessionAtStep1, id: 2 }, message: 'Session created.' },
          { status: 201 }
        );
      })
    );

    renderWizard();

    expect(
      await screen.findByRole('heading', { name: /your information/i, level: 2 })
    ).toBeInTheDocument();
    expect(sessionsCreated).toBe(1);
  });
});
```

The temporary failure uses 429 on purpose: `apiFetch` retries 5xx and network errors three times with backoff (`frontend/src/utils/retry.ts`), about 3.5 s, which collides with the 5 s `asyncUtilTimeout` in `src/test/setup.ts`. A 429 fails at once.

In `frontend/src/context/__tests__/IntakeContext.test.tsx`, the existing 404 test never sets the pointer, so it passes whatever `loadSession` does. Replace the whole test (lines 118-141), from `it('clears localStorage when loading an invalid session', async () => {` through its closing `});`, with:
```tsx
  it('clears localStorage when loading an invalid session', async () => {
    // Instead of relying on the mount effect (which creates an unhandled rejection
    // because loadSession re-throws), we test via the Load Session button which
    // is wrapped in the safe() handler.
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({ error: 'Not found', message: 'Session not found' }, { status: 404 })
      )
    );

    const user = userEvent.setup();
    renderWithIntake();
    // Set the pointer after mount, so the provider's own startup load can't be what clears it.
    localStorage.setItem('current_session_id', '1');

    await act(async () => {
      await user.click(screen.getByText('Load Session'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    expect(localStorage.getItem('current_session_id')).toBeNull();
    expect(screen.getByTestId('error')).not.toHaveTextContent('none');
  });

  it('keeps the resume pointer when a load fails for a reason that can pass, such as a busy server', async () => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
      )
    );

    const user = userEvent.setup();
    renderWithIntake();
    // Set the pointer after mount, so the provider's own startup load can't consume it.
    localStorage.setItem('current_session_id', '1');

    await act(async () => {
      await user.click(screen.getByText('Load Session'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('false');
    });

    expect(localStorage.getItem('current_session_id')).toBe('1');
    expect(screen.getByTestId('error')).not.toHaveTextContent('none');
  });
```

- [ ] **Step 2: Run them and confirm they fail**

```bash
cd /Volumes/Containers/DigniFi/frontend
npx vitest run src/pages/__tests__/IntakeWizard.test.tsx src/context/__tests__/IntakeContext.test.tsx
```

Expected: 3 failures, 20 passes.
- `shows a debt read from an uploaded bill at Amounts Owed ...`: `TestingLibraryElementError: Unable to find an element with the display value: Lakeshore Medical Group.`
- `keeps the filer's saved place and lets them try again ...`: `Found multiple elements with the role "alert"`. The old wizard creates a new session and renders a step instead of the alert.
- `keeps the resume pointer when a load fails ...`: `AssertionError: expected null to be '1'`.

`starts one new session when the saved one is gone ...` passes already; it guards today's shared-computer behaviour against the rewrite. The amended 404 test also passes on both versions; it now actually exercises the removal.

- [ ] **Step 3: Implement**

`frontend/src/context/IntakeContext.tsx`, action types (lines 24-25). Replace:
```tsx
  createSession: (districtId: number) => Promise<void>;
  loadSession: (sessionId: number) => Promise<void>;
```
With:
```tsx
  createSession: (districtId: number) => Promise<IntakeSession>;
  loadSession: (sessionId: number) => Promise<IntakeSession>;
```

`createSession` (lines 83-93). Replace:
```tsx
  const createSession = async (districtId: number): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.intake.createSession({
        district: districtId,
        current_step: 1,
      });

      setSession(response.session);
    } catch (err) {
```
With:
```tsx
  const createSession = async (districtId: number): Promise<IntakeSession> => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.intake.createSession({
        district: districtId,
        current_step: 1,
      });

      setSession(response.session);
      return response.session;
    } catch (err) {
```

`loadSession` (lines 106-125). Replace:
```tsx
  /**
   * Load existing session by ID
   */
  const loadSession = async (sessionId: number): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      const loadedSession = await api.intake.getSession(sessionId);
      setSession(loadedSession);
    } catch (err) {
      const errorMessage =
        err instanceof APIClientError
          ? err.message
          : 'Unable to load your session. Please try again.';
      setError(errorMessage);

      // Clear invalid session from localStorage
      localStorage.removeItem('current_session_id');
      throw err;
```
With:
```tsx
  /**
   * Load existing session by ID. Resolves with the session as the server holds it now.
   */
  const loadSession = async (sessionId: number): Promise<IntakeSession> => {
    setIsLoading(true);
    setError(null);

    try {
      const loadedSession = await api.intake.getSession(sessionId);
      setSession(loadedSession);
      return loadedSession;
    } catch (err) {
      const errorMessage =
        err instanceof APIClientError
          ? err.message
          : 'Unable to load your session. Please try again.';
      setError(errorMessage);

      // Forget the resume pointer only on a 404, DRF's answer for a session that is gone
      // or not this user's. A 429, a 5xx or a network error is temporary: keep the pointer
      // so the filer can pick up where they left off.
      if (err instanceof APIClientError && err.statusCode === 404) {
        localStorage.removeItem('current_session_id');
      }
      throw err;
```
Leave the provider's startup effect (lines 56-64) exactly as it is (spec §4.2; DIG-11 tracks it).

`frontend/src/pages/IntakeWizard.tsx`, imports (lines 11-14). Replace:
```tsx
import { useIntake } from '../context/IntakeContext';
import { api } from '../api/client';
import { trackEvent } from '../utils/analytics';
import { WizardLayout } from '../components/wizard/WizardLayout';
```
With:
```tsx
import { useIntake } from '../context/IntakeContext';
import { api, APIClientError } from '../api/client';
import { trackEvent } from '../utils/analytics';
import { Button } from '../components/common';
import { WizardLayout } from '../components/wizard/WizardLayout';
```

Context destructure and refs (lines 51-57). Replace:
```tsx
  const navigate = useNavigate();
  const { session, createSession, updateCurrentStep, completeSession, calculateMeansTest } =
    useIntake();
  const [currentStepNumber, setCurrentStepNumber] = useState(1);
  const [canProceed, setCanProceed] = useState(false);
  const sessionStartRef = useRef<number>(0);
  const syncedSessionIdRef = useRef<number | null>(null);
```
With:
```tsx
  const navigate = useNavigate();
  const {
    session,
    createSession,
    loadSession,
    updateCurrentStep,
    completeSession,
    calculateMeansTest,
  } = useIntake();
  const [currentStepNumber, setCurrentStepNumber] = useState(1);
  const [canProceed, setCanProceed] = useState(false);
  const sessionStartRef = useRef<number>(0);
```

Mount effect (lines 71-91). Replace the whole block from `  // Initialize session on mount` banner through `  }, [session, createSession]);`:
```tsx
  // =========================================================================
  // Initialize session on mount
  // =========================================================================

  useEffect(() => {
    if (!session && !localStorage.getItem('current_session_id')) {
      // No session in context AND no saved session — create a new one (District ID 1 = ILND)
      createSession(1);
    } else if (session && syncedSessionIdRef.current !== session.id) {
      // Session became available (loaded from localStorage or just created).
      // Sync wizard state once per session id to avoid overwriting in-flight steps.
      syncedSessionIdRef.current = session.id;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- initializer: syncing external session state into local wizard state on session arrival
      setCurrentStepNumber(session.current_step);
      if (session.debtor_info) setDebtorData(session.debtor_info);
      if (session.income_info) setIncomeData(session.income_info);
      if (session.expense_info) setExpenseData(session.expense_info);
      if (session.assets) setAssetsData(session.assets);
      if (session.debts) setDebtsData(session.debts);
    }
  }, [session, createSession]);
```
With:
```tsx
  // =========================================================================
  // Read the session on mount
  // =========================================================================

  // Fixed at mount: the session in context, else the saved resume pointer, else null for a
  // filer with no saved session. A failed read is retried for this same session rather
  // than starting a new one, even if the pointer was cleared in the meantime.
  const [sessionIdToRead] = useState<number | null>(() => {
    const savedSessionId = localStorage.getItem('current_session_id');
    return session?.id ?? (savedSessionId ? parseInt(savedSessionId, 10) : null);
  });
  const [sessionRead, setSessionRead] = useState<'pending' | 'failed' | 'done'>('pending');
  const [readAttempt, setReadAttempt] = useState(0);

  // Every wizard entry re-reads the session, and no step renders until the read returns
  // (DIG-1, DIG-30). The copy in context can predate an upload on /documents; a step that
  // mounted on it would autosave that stale copy over what the server now holds.
  useEffect(() => {
    let cancelled = false;

    const openSession = async (): Promise<IntakeSession> => {
      if (sessionIdToRead === null) {
        // No session in context AND no saved session — create a new one (District ID 1 = ILND)
        return createSession(1);
      }
      try {
        return await loadSession(sessionIdToRead);
      } catch (error) {
        // A 404 means the saved session is gone or belongs to someone else (a shared
        // computer). Retrying cannot help, so start a new one, as for a new filer.
        if (error instanceof APIClientError && error.statusCode === 404) {
          return createSession(1);
        }
        throw error;
      }
    };

    openSession()
      .then((fresh) => {
        if (cancelled) return;
        setCurrentStepNumber(fresh.current_step);
        if (fresh.debtor_info) setDebtorData(fresh.debtor_info);
        if (fresh.income_info) setIncomeData(fresh.income_info);
        if (fresh.expense_info) setExpenseData(fresh.expense_info);
        if (fresh.assets) setAssetsData(fresh.assets);
        if (fresh.debts) setDebtsData(fresh.debts);
        setSessionRead('done');
      })
      .catch(() => {
        if (!cancelled) setSessionRead('failed');
      });

    return () => {
      cancelled = true;
    };
    // Runs once per wizard entry and once per Try again. createSession and loadSession are
    // fresh closures on every render, so listing them would re-read on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readAttempt]);

  const handleRetry = () => {
    setSessionRead('pending');
    setReadAttempt((attempt) => attempt + 1);
  };
```

Loading render (lines 333-335). Replace:
```tsx
  if (!session) {
    return (
      <div className="wizard-loading">
```
With:
```tsx
  if (sessionRead === 'failed') {
    return (
      <div className="wizard-loading">
        <p role="alert">
          We couldn't get your latest information just now. Please try again in a moment.
        </p>
        <Button onClick={handleRetry}>Try again</Button>
      </div>
    );
  }

  // Steps mount only once the read has filled them, so the first autosave sends server data.
  if (!session || sessionRead !== 'done') {
    return (
      <div className="wizard-loading">
```

And the message in that block (line 358). Replace:
```tsx
        <p>Starting your intake session...</p>
```
With:
```tsx
        <p>
          {sessionIdToRead === null
            ? 'Starting your intake session...'
            : 'Loading your information...'}
        </p>
```

The alert copy is spec §5 "wizard refresh failed", verbatim. Do not add an `eslint-disable` for `react-hooks/set-state-in-effect`; none is needed because state is only set after `await`.

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd /Volumes/Containers/DigniFi/frontend
npx vitest run src/pages/__tests__/IntakeWizard.test.tsx src/context/__tests__/IntakeContext.test.tsx
npx vitest run
npx tsc -b
npm run lint
```
Expected: the two files give 23 passed (9 wizard, 14 context). The full suite is green (213 passing on the tree this plan was verified against; your count may differ by tests that earlier tasks added). `tsc -b` and `npm run lint` report nothing. The `The current testing environment is not configured to support act(...)` stderr lines come from the existing autosave tests and predate this change.

If the full stack is up, also run `npm run e2e`: every journey re-enters `/intake` from `/documents` and must still pass (spec §9 requires E2E at commit 3 and at the tip, not here).

- [ ] **Step 5: Update CLAUDE.md gotchas**

Add this bullet at the end of the `## Gotchas (things agents get wrong)` list in `/Volumes/Containers/DigniFi/CLAUDE.md`, right after the list's last bullet and before the blank line above `## Architecture (quick)`:
```markdown
- **The wizard re-reads the session on every mount** — `IntakeWizard` fixes the session id at mount (context session, else `current_session_id`), calls `loadSession(id)`, and renders no step until it returns, so steps and autosave start from server data, not the context copy (which predates any upload on `/documents`). A failed read shows a "Try again" alert for the same id; a 404 starts a new session. `loadSession`/`createSession` resolve with the session, and `loadSession` clears `current_session_id` only on a 404, but the provider's own startup load still clears it on any error (DIG-11).
```
No existing bullet becomes false.

- [ ] **Step 6: Commit**

First check that each file's diff holds only this task's hunks: run `cd /Volumes/Containers/DigniFi && git diff -- CLAUDE.md frontend/src/pages/IntakeWizard.tsx frontend/src/pages/__tests__/IntakeWizard.test.tsx`. `git diff CLAUDE.md` must show only this task's Step 5 hunk, the bullet starting `- **The wizard re-reads the session on every mount**`; Tasks 1–2 committed every other `CLAUDE.md` change, and Task 3 committed its own. If anything else appears in any of these files, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it.
```bash
cd /Volumes/Containers/DigniFi
git add frontend/src/context/IntakeContext.tsx \
  frontend/src/context/__tests__/IntakeContext.test.tsx \
  frontend/src/pages/IntakeWizard.tsx \
  frontend/src/pages/__tests__/IntakeWizard.test.tsx \
  CLAUDE.md
git commit -m "fix(intake): re-read the session whenever the wizard opens"
```
If the pre-commit prettier hook rewrites files, run the same `git add` again (it includes `CLAUDE.md`) and repeat the same `git commit` command. No `Co-Authored-By` or other trailer.

---

### Task 5: Read every page of a PDF without the hybrid sidecar  (Commit #6 in spec §9)

Spec: §4.8, contract C1. Tickets: DIG-4.

**Why.** `processor.py` calls `opendataloader_pdf.convert(..., hybrid="docling-fast")`. That option needs the `odl-hybrid` sidecar. Heroku runs a single container with no sidecar, so the Java CLI exits 1 on every PDF. The processor then falls back to vision on **page 1 only**, so a balance printed on page 2 never reaches the model. The fix: run the Java CLI alone, route text-layer PDFs to the text prompt, and send up to 3 scanned pages to vision, in order.

**Facts verified against the real CLI (opendataloader-pdf 2.4.3, Java 22 locally) while writing this task:**

- `convert(..., hybrid="docling-fast")` with no server raises `subprocess.CalledProcessError` (exit 1).
- With `image_output="off"`, an image-only PDF writes an empty `document.md`.
- Without `image_output="off"`, each page writes `![image N](<document_images/imageFileN.png>)`. That is more than 30 characters, so the scan would wrongly go to the text prompt.
- Without `include_header_footer=True`, a letterhead repeated at the top of every page (the creditor's name) is dropped from the markdown.
- A PDF with an empty page tree makes the CLI exit 1. `fitz.open()` on it gives `len(doc) == 0`.
- The jar's class files are Java 11 (major version 55).
- The first JVM launch on a machine took about 30 s; later launches take about 0.4 s.

**Starting state.** Tasks 1–4 are committed. `openai_provider.py` and `test_openai_provider.py` are committed by Task 1 exactly as they are in today's working tree. All line numbers below were read from today's working tree. If Task 1 changed either file, find each hunk by its quoted text, not by its line number.

**Files:**

- Create: `backend/apps/documents/tests/builders.py`
- Create: `backend/apps/documents/tests/test_processing_outcomes.py`
- Modify: `backend/apps/documents/services/processor.py:39-47` (`_pdf_to_image_bytes`), `:65-68` (`_process_image`), `:82-87` (`convert` call), `:98-104` (routing)
- Modify: `backend/apps/documents/services/providers/base.py:27-39` (abstract `extract`)
- Modify: `backend/apps/documents/services/providers/openai_provider.py:16-17` (docstring), `:30-38` (`classify`/`extract`), `:43-53` (`_vision`)
- Modify: `backend/apps/documents/services/providers/gemini.py:15-16` (docstring), `:24-32` (`classify`/`extract`), `:47-58` (`_vision`)
- Modify: `backend/apps/documents/tests/test_processor.py:1-6, 30, 37, 67, 77-85, 90-99`, and append a class
- Modify: `backend/apps/documents/tests/test_openai_provider.py:37, 42, 50, 53, 61, 77, 80`
- Modify: `backend/apps/documents/tests/test_gemini_provider.py:50, 58, 70, 73-79`
- Modify: `.github/workflows/ci.yml:74-77` (add `-rs`, so skipped tests show in the log)
- Modify: `CLAUDE.md:35, 52, 53`
- Test: `backend/apps/documents/tests/test_processing_outcomes.py`, `backend/apps/documents/tests/test_processor.py`, `backend/apps/documents/tests/test_openai_provider.py`, `backend/apps/documents/tests/test_gemini_provider.py`

**Interfaces:**

- **Consumes:**
  - `OpenAIProvider(model: str = "gpt-4o")` and its `_complete(content, *, json_mode)` (from Task 1).
  - `views._get_processor()`, which builds the provider named by `settings.OCR_PROVIDER` / `settings.OCR_MODEL` (from Task 1).
  - The existing `processor._MIN_TEXT_LENGTH = 30` and `processor._MAX_SCANNED_PAGES = 3` (`processor.py:19-20`).
- **Produces (C1):**
  - `processor._pdf_to_page_images(pdf_bytes: bytes, max_pages: int = _MAX_SCANNED_PAGES) -> list[bytes]`. It returns JPEG bytes per page, in order, and replaces `_pdf_to_image_bytes`.
  - `BaseOCRProvider.extract(self, images: list[bytes], prompt: str) -> str`. An empty list means text mode, and a photo is a one-item list. `classify(self, image_data: bytes, prompt: str) -> str` is unchanged.
  - For a PDF with no pages, `DocumentProcessor` returns `ExtractionResult(error="PDF has no pages")` without calling the provider.
- **Produces (test helpers that later tasks reuse; append to these files, never recreate them):**
  - `apps/documents/tests/builders.py`:
    - `text_pdf(pages: list[str], letterhead: str = "") -> bytes`
    - `scanned_pdf(page_sizes: list[tuple[int, int]]) -> bytes`
    - `pdf_with_no_pages() -> bytes`
    - `chat_completion(content: str | None, *, finish_reason: str = "stop", refusal: str | None = None) -> openai.types.chat.ChatCompletion`
  - `apps/documents/tests/test_processing_outcomes.py`:
    - the autouse fixture `text_layer_jvm`, a stand-in for the JVM;
    - the fixture `openai_client`, the mocked client, whose default reply is `BILL_REPLY`;
    - the fixture `filer`, which returns `(APIClient, IntakeSession)` and uses `transactional_db`;
    - the helper `upload(filer, data, filename, mime_type, document_type) -> OCRResult`;
    - the helper `sent_parts(openai_client, call=-1) -> list[dict]`;
    - the constant `BILL_REPLY`.
  - `test_processor.py::TestRealJvmContract`.

- [ ] **Step 1: Write the failing tests**

1a. Create `backend/apps/documents/tests/builders.py`. It is not collected as a test module, because pytest only collects `test_*.py`, `tests.py` and `*_tests.py`.

```python
"""Synthetic uploads and model replies for document tests.

Every value here is invented. Nothing is a real person, account or creditor.
"""

import fitz  # pymupdf
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice


def text_pdf(pages: list[str], letterhead: str = "") -> bytes:
    """A PDF with a real text layer, one page per string. A letterhead, when given, is
    printed small at the top of every page, where a bill puts the creditor's name."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        if letterhead:
            page.insert_text((72, 30), letterhead, fontsize=9)
        page.insert_text((72, 200), text, fontsize=11)
    return doc.tobytes()


def scanned_pdf(page_sizes: list[tuple[int, int]]) -> bytes:
    """An image-only PDF, like a phone scan: one page per (width, height) in points,
    each covered by a picture and carrying no text layer."""
    doc = fitz.open()
    for shade, (width, height) in enumerate(page_sizes):
        picture = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40), False)
        picture.clear_with(40 + 50 * shade)
        page = doc.new_page(width=width, height=height)
        page.insert_image(page.rect, pixmap=picture)
    return doc.tobytes()


def pdf_with_no_pages() -> bytes:
    """A well-formed PDF whose page tree is empty. Written by hand, because pymupdf
    refuses to save a document with no pages."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
        b"trailer<</Root 1 0 R>>\n"
        b"%%EOF\n"
    )


def chat_completion(
    content: str | None, *, finish_reason: str = "stop", refusal: str | None = None
) -> ChatCompletion:
    """What openai's chat.completions.create returns, built from the SDK's own types so
    a test cannot read an attribute the real reply lacks."""
    return ChatCompletion(
        id="chatcmpl-test",
        object="chat.completion",
        created=0,
        model="gpt-4o",
        choices=[
            Choice(
                index=0,
                finish_reason=finish_reason,
                message=ChatCompletionMessage(role="assistant", content=content, refusal=refusal),
            )
        ],
    )
```

1b. Create `backend/apps/documents/tests/test_processing_outcomes.py`.

- **Why `transactional_db`:** the upload view processes on a `ThreadPoolExecutor` worker. That worker cannot see rows created inside the `db` fixture's transaction; this was verified, and the OCRResult stayed `pending` with zero model calls. With `transactional_db` the full path runs, and the 202 returns after processing finishes.
- **Why replace the JVM:** `_TextLayerJVM` stands in for the JVM so these outcome tests run with or without Java. `TestRealJvmContract` (1c) checks that it behaves like the real CLI.

```python
"""What a filer's upload turns into, end to end.

Each test posts a file to the real upload endpoint and lets the real view, processor
and OpenAIProvider run. Two boundaries are replaced:

- the OpenAI client (``openai_provider.OpenAI``), and
- the opendataloader JVM, by ``_TextLayerJVM`` below. The real-JVM contract tests in
  test_processor.py check that it behaves like the real CLI.

The upload view runs processing on a worker thread, which cannot see rows inside a
test transaction, so these tests use ``transactional_db``. A test that calls
``views._run_processing(doc.id)`` directly can use plain ``db``.
"""

import base64
import os
import subprocess
from unittest.mock import patch

import fitz  # pymupdf
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.documents.models import DocumentType, OCRResult, OCRStatus
from apps.documents.tests.builders import (
    chat_completion,
    pdf_with_no_pages,
    scanned_pdf,
    text_pdf,
)
from apps.intake.models import IntakeSession
from apps.users.models import User

BILL_REPLY = (
    '{"creditor_name": "Lakeshore Medical Billing", "account_number": "4417-2290", '
    '"amount_owed": "1284.50", "minimum_payment": null, "due_date": null, '
    '"creditor_type": "medical", "confidence_score": 88}'
)


class _TextLayerJVM:
    """Stands in for the ``opendataloader_pdf`` module and behaves like the real CLI:

    - It has no hybrid server to reach (none runs on Heroku), so any ``hybrid`` option
      exits 1.
    - It writes each page's text layer as markdown.
    - An image-only page becomes an image placeholder, unless ``image_output="off"``.
    """

    @staticmethod
    def convert(input_path, output_dir, **options):
        if options.get("hybrid"):
            raise subprocess.CalledProcessError(1, "opendataloader-pdf")
        blocks = []
        with fitz.open(input_path[0]) as doc:
            for number, page in enumerate(doc, start=1):
                text = page.get_text().strip()
                if text:
                    blocks.append(text)
                elif options.get("image_output") != "off":
                    blocks.append(f"![image {number}](<document_images/imageFile{number}.png>)")
        with open(os.path.join(output_dir, "document.md"), "w") as f:
            f.write("\n\n".join(blocks))


@pytest.fixture(autouse=True)
def text_layer_jvm():
    with patch("apps.documents.services.processor.opendataloader_pdf", _TextLayerJVM):
        yield


@pytest.fixture
def openai_client(settings, tmp_path):
    """The mocked OpenAI client. Every completion answers BILL_REPLY unless a test
    sets ``chat.completions.create.return_value`` or ``side_effect``."""
    settings.MEDIA_ROOT = tmp_path
    settings.OCR_PROVIDER = "openai"
    settings.OCR_MODEL = ""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
        with patch("apps.documents.services.providers.openai_provider.OpenAI") as openai_cls:
            client = openai_cls.return_value
            client.chat.completions.create.return_value = chat_completion(BILL_REPLY)
            yield client


@pytest.fixture
def filer(transactional_db):
    """An authenticated API client and that filer's intake session."""
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=338.00,
    )
    user = User.objects.create_user(username="uploader", password="pass")
    session = IntakeSession.objects.create(user=user, district=district)
    client = APIClient()
    client.force_authenticate(user=user)
    return client, session


def upload(filer, data: bytes, filename: str, mime_type: str, document_type: str) -> OCRResult:
    """Post one file the way the upload page does. Processing has finished by the time
    the 202 returns, so the OCRResult is final."""
    client, session = filer
    response = client.post(
        "/api/documents/upload/",
        {
            "file": SimpleUploadedFile(filename, data, content_type=mime_type),
            "document_type": document_type,
            "session_id": session.id,
        },
        format="multipart",
    )
    assert response.status_code == 202
    return OCRResult.objects.get(document_id=response.json()["id"])


def sent_parts(openai_client, call: int = -1) -> list[dict]:
    """The user-message content parts of one completion request (the last by default)."""
    request = openai_client.chat.completions.create.call_args_list[call]
    return request.kwargs["messages"][0]["content"]


def _aspect_ratio(data_url: str) -> float:
    picture = fitz.Pixmap(base64.b64decode(data_url.removeprefix("data:image/jpeg;base64,")))
    return picture.width / picture.height


def test_balance_on_page_two_of_a_text_pdf_reaches_the_model(filer, openai_client):
    pdf = text_pdf(
        [
            "Lakeshore Medical Billing\nPatient statement for services in August.",
            "Account 4417-2290\nBalance due: $1,284.50",
        ]
    )

    ocr = upload(filer, pdf, "bill.pdf", "application/pdf", DocumentType.CREDITOR_BILL)

    parts = sent_parts(openai_client)
    assert [part["type"] for part in parts] == ["text"]
    assert "Balance due: $1,284.50" in parts[0]["text"]
    assert ocr.status == OCRStatus.COMPLETED


def test_a_scanned_pdf_sends_at_most_three_page_images_in_order(filer, openai_client):
    # Four image-only pages, each a different shape, so the images that reach the model
    # show which pages they are.
    pdf = scanned_pdf([(200, 300), (300, 300), (400, 300), (500, 300)])

    upload(filer, pdf, "scan.pdf", "application/pdf", DocumentType.CREDITOR_BILL)

    assert openai_client.chat.completions.create.call_count == 1
    parts = sent_parts(openai_client)
    assert [part["type"] for part in parts] == ["image_url", "image_url", "image_url", "text"]
    shapes = [_aspect_ratio(part["image_url"]["url"]) for part in parts[:3]]
    assert shapes == pytest.approx([200 / 300, 300 / 300, 400 / 300], abs=0.01)


def test_a_pdf_with_no_pages_fails_instead_of_completing_empty(filer, openai_client):
    ocr = upload(
        filer, pdf_with_no_pages(), "empty.pdf", "application/pdf", DocumentType.CREDITOR_BILL
    )

    assert ocr.status == OCRStatus.FAILED
    openai_client.chat.completions.create.assert_not_called()
```

1c. `backend/apps/documents/tests/test_processor.py`. The existing tests switch to the list interface, and the real-JVM contract tests are added.

Replace the imports (lines 1-6):

```python
from unittest.mock import MagicMock, patch

import pytest

from apps.documents.models import DocumentType
from apps.documents.services.processor import DocumentProcessor, ExtractionResult
```

with:

```python
import shutil
from unittest.mock import MagicMock, patch

import pytest

from apps.documents.models import DocumentType
from apps.documents.services.processor import (
    DocumentProcessor,
    ExtractionResult,
    opendataloader_pdf,
)
from apps.documents.tests.builders import scanned_pdf, text_pdf
```

In `test_jpeg_routes_to_vision` (line 30), replace `    assert call_args[0][0] == image_bytes` with:

```python
    assert call_args[0][0] == [image_bytes]
```

In `test_png_routes_to_vision` (line 37), replace `    assert call_args[0][0] == png_bytes` with:

```python
    assert call_args[0][0] == [png_bytes]
```

In `test_pdf_with_text_routes_to_text_path` (line 67), replace `    assert call_args[0][0] == b""` with:

```python
    assert call_args[0][0] == []
```

In `test_pdf_falls_back_to_vision_when_java_missing` and `test_pdf_falls_back_to_vision_when_opendataloader_not_installed` (today's lines 75-83 and 88-97), the two blocks below are byte-identical, so one Edit-tool call with this `old_string` is not unique and fails unless you pass **`replace_all: true`**. Make one Edit call with `replace_all: true` that replaces:

```python
        with patch(
            "apps.documents.services.processor._pdf_to_image_bytes",
            return_value=fake_page_image,
        ):
            result = processor.process(b"%PDF-1.4", "application/pdf", DocumentType.CREDITOR_BILL)

    assert result.error == ""
    call_args = mock_provider.extract.call_args
    assert call_args[0][0] == fake_page_image
```

with:

```python
        with patch(
            "apps.documents.services.processor._pdf_to_page_images",
            return_value=[fake_page_image],
        ):
            result = processor.process(b"%PDF-1.4", "application/pdf", DocumentType.CREDITOR_BILL)

    assert result.error == ""
    call_args = mock_provider.extract.call_args
    assert call_args[0][0] == [fake_page_image]
```

After the edit, `git grep -n _pdf_to_image_bytes -- backend/apps/documents/tests/test_processor.py` (run from `/Volumes/Containers/DigniFi`) must print nothing, and `_pdf_to_page_images` must appear in both tests.

Then append this class at the end of the file:

```python


@pytest.mark.skipif(
    shutil.which("java") is None or opendataloader_pdf is None,
    reason="real-JVM contract tests need `java` on PATH and opendataloader-pdf installed",
)
class TestRealJvmContract:
    """Runs the real opendataloader CLI with the options the processor passes, so the
    JVM stand-in in test_processing_outcomes.py stays honest. The first JVM launch on a
    machine can take about 30 s."""

    def test_real_jvm_puts_page_two_of_a_text_pdf_in_the_text_prompt(
        self, processor, mock_provider
    ):
        pdf = text_pdf(
            [
                "Lakeshore Medical Billing\nPatient statement for services in August.",
                "Account 4417-2290\nBalance due: $1,284.50",
            ]
        )

        result = processor.process(pdf, "application/pdf", DocumentType.CREDITOR_BILL)

        images, prompt = mock_provider.extract.call_args[0]
        assert images == []
        assert "Balance due: $1,284.50" in prompt
        assert result.error == ""

    def test_real_jvm_keeps_the_letterhead_that_names_the_creditor(self, processor, mock_provider):
        pdf = text_pdf(
            [
                "Patient statement for services in August.",
                "Account 4417-2290\nBalance due: $1,284.50",
            ],
            letterhead="Lakeshore Medical Billing",
        )

        processor.process(pdf, "application/pdf", DocumentType.CREDITOR_BILL)

        _images, prompt = mock_provider.extract.call_args[0]
        assert "Lakeshore Medical Billing" in prompt

    def test_real_jvm_sends_a_scanned_pdf_to_vision(self, processor, mock_provider):
        pdf = scanned_pdf([(200, 300), (300, 300)])

        processor.process(pdf, "application/pdf", DocumentType.CREDITOR_BILL)

        images, _prompt = mock_provider.extract.call_args[0]
        assert len(images) == 2
```

1d. `backend/apps/documents/tests/test_openai_provider.py`. `extract` now takes a list. `classify` calls stay as bytes.

- line 37: `provider.extract(b"", "Return ONLY a valid JSON object for this pay stub.")` → `provider.extract([], "Return ONLY a valid JSON object for this pay stub.")`
- line 42: `provider.extract(b"\xff\xd8\xff", "Return ONLY a valid JSON object.")` → `provider.extract([b"\xff\xd8\xff"], "Return ONLY a valid JSON object.")`
- line 50: `provider.extract(b"\xff\xd8\xff\x00binary", "Return ONLY a valid JSON object.")` → `provider.extract([b"\xff\xd8\xff\x00binary"], "Return ONLY a valid JSON object.")`
- line 61 (`test_extraction_constrains_the_response_to_json`): `provider.extract(b"", "Return ONLY a valid JSON object.")` → `provider.extract([], "Return ONLY a valid JSON object.")`
- line 77 (`test_empty_completion_becomes_empty_string`): `assert provider.extract(b"", "Return ONLY a valid JSON object.") == ""` → `assert provider.extract([], "Return ONLY a valid JSON object.") == ""`. Task 7 replaces this test.
- line 80: `OpenAIProvider(model="gpt-4o-mini").extract(b"", "Return ONLY a valid JSON object.")` → `OpenAIProvider(model="gpt-4o-mini").extract([], "Return ONLY a valid JSON object.")`

After `test_image_bytes_survive_the_round_trip_intact`, which ends at line 53 with `        assert base64.b64decode(encoded) == b"\xff\xd8\xff\x00binary"`, insert this method inside `TestTextVersusVisionRouting`:

```python

    def test_every_scanned_page_is_sent_in_page_order(self, provider, mock_openai_client):
        import base64

        provider.extract([b"page-1", b"page-2", b"page-3"], "Return ONLY a valid JSON object.")
        content = _sent_content(mock_openai_client)
        assert [part["type"] for part in content] == ["image_url", "image_url", "image_url", "text"]
        sent = [
            base64.b64decode(part["image_url"]["url"].removeprefix("data:image/jpeg;base64,"))
            for part in content[:3]
        ]
        assert sent == [b"page-1", b"page-2", b"page-3"]
```

1e. `backend/apps/documents/tests/test_gemini_provider.py`:

- line 50: `provider.extract(b"", "Extract fields")` → `provider.extract([], "Extract fields")`
- line 58: `provider.extract(b"\xff\xd8\xff", "Extract fields from image")` → `provider.extract([b"\xff\xd8\xff"], "Extract fields from image")`
- line 70: `result = p.extract(b"", "Extract")` → `result = p.extract([], "Extract")`
- line 74: `provider.extract(b"\xff\xd8\xff", "Extract")` → `provider.extract([b"\xff\xd8\xff"], "Extract")`

Append to the end of `TestGeminiProviderExtract`, after line 79 `        assert isinstance(contents[1], str)`. Only `genai` is patched in this file; `types` is real, so each part's `inline_data.data` is the real bytes.

```python

    def test_every_scanned_page_reaches_gemini_in_page_order(self, provider, mock_genai_client):
        provider.extract([b"page-1", b"page-2", b"page-3"], "Extract")
        contents = mock_genai_client.models.generate_content.call_args.kwargs["contents"]
        assert [part.inline_data.data for part in contents[:-1]] == [
            b"page-1",
            b"page-2",
            b"page-3",
        ]
        assert contents[-1] == "Extract"
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
cd /Volumes/Containers/DigniFi/backend && .venv/bin/python -m pytest apps/documents -q
```

Expected: **16 failed** and every other test passes. These are the 16, with the reason for each:

- `test_processing_outcomes.py::test_balance_on_page_two_of_a_text_pdf_reaches_the_model`
  - `assert ['image_url', 'text'] == ['text']`
  - The stand-in exits 1 on today's `hybrid="docling-fast"`, so the processor falls back to vision on page 1. This is the production failure.
- `test_processing_outcomes.py::test_a_scanned_pdf_sends_at_most_three_page_images_in_order`
  - Only one `image_url` part is sent.
- `test_processor.py::test_jpeg_routes_to_vision`, `::test_png_routes_to_vision`, `::test_pdf_with_text_routes_to_text_path`
  - Bytes are compared against a list, e.g. `assert b'' == []`.
- `test_processor.py::test_pdf_falls_back_to_vision_when_java_missing`, `::test_pdf_falls_back_to_vision_when_opendataloader_not_installed`
  - `AttributeError: ... does not have the attribute '_pdf_to_page_images'`.
- `test_processor.py::TestRealJvmContract`, all 3 tests
  - The real CLI exits 1 on `hybrid`, so the provider gets one page-1 JPEG, e.g. `assert 3667 == 2`.
  - Without `java` on PATH these show as 3 skipped instead.
- `test_openai_provider.py::TestTextVersusVisionRouting::test_scanned_page_is_sent_as_an_inline_image`, `::test_image_bytes_survive_the_round_trip_intact`, `::test_every_scanned_page_is_sent_in_page_order`
  - `TypeError: a bytes-like object is required, not 'list'`.
- `test_gemini_provider.py::TestGeminiProviderExtract::test_vision_mode_sets_json_mime`, `::test_vision_mode_passes_image_part_first`, `::test_every_scanned_page_reaches_gemini_in_page_order`
  - `pydantic_core._pydantic_core.ValidationError: 1 validation error for Blob`.

`test_a_pdf_with_no_pages_fails_instead_of_completing_empty` **already passes**: today's page-1 renderer raises `IndexError` on an empty page tree. It is here because of the new contract. An empty list now means text mode, so a processor that passed `[]` for a page-less scan would send the image prompt with no image, and the upload would "complete" empty. The `if not images` guard in Step 3 is what keeps it failing as it should.

- [ ] **Step 3: Implement**

3a. `backend/apps/documents/services/processor.py`. Replace `_pdf_to_image_bytes` (lines 39-47):

```python
def _pdf_to_image_bytes(pdf_bytes: bytes, page_index: int = 0) -> bytes:
    import fitz  # pymupdf

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if page_index >= len(doc):
        page_index = 0
    page = doc[page_index]
    pix = page.get_pixmap(dpi=150)
    return pix.tobytes("jpeg")
```

with:

```python
def _pdf_to_page_images(pdf_bytes: bytes, max_pages: int = _MAX_SCANNED_PAGES) -> list[bytes]:
    """Render the first ``max_pages`` pages as JPEG bytes, in page order. A PDF with
    no pages gives an empty list."""
    import fitz  # pymupdf

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return [doc[i].get_pixmap(dpi=150).tobytes("jpeg") for i in range(min(len(doc), max_pages))]
```

In `_process_image` (lines 65-68), replace:

```python
    def _process_image(self, image_bytes: bytes, doc_type: str) -> ExtractionResult:
        prompt = build_image_extraction_prompt(doc_type)
        raw = self._provider.extract(image_bytes, prompt)
        return self._parse_result(raw, doc_type)
```

with:

```python
    def _process_image(self, image_bytes: bytes, doc_type: str) -> ExtractionResult:
        prompt = build_image_extraction_prompt(doc_type)
        raw = self._provider.extract([image_bytes], prompt)
        return self._parse_result(raw, doc_type)
```

Replace the `convert` call (lines 82-87):

```python
                    opendataloader_pdf.convert(
                        input_path=[pdf_path],
                        output_dir=tmp_out,
                        format="markdown",
                        hybrid="docling-fast",
                    )
```

with:

```python
                    # image_output="off": a scanned page yields no text, so it routes
                    # to vision instead of sending image placeholders to the text
                    # prompt. include_header_footer=True keeps the letterhead, where
                    # creditor names and account numbers usually sit.
                    opendataloader_pdf.convert(
                        input_path=[pdf_path],
                        output_dir=tmp_out,
                        format="markdown",
                        image_output="off",
                        include_header_footer=True,
                    )
```

Replace the routing (lines 98-104):

```python
        if len(text.strip()) >= _MIN_TEXT_LENGTH:
            prompt = build_text_extraction_prompt(doc_type, text)
            raw = self._provider.extract(b"", prompt)
        else:
            image_bytes = _pdf_to_image_bytes(pdf_bytes, page_index=0)
            prompt = build_image_extraction_prompt(doc_type)
            raw = self._provider.extract(image_bytes, prompt)
```

with:

```python
        if len(text.strip()) >= _MIN_TEXT_LENGTH:
            prompt = build_text_extraction_prompt(doc_type, text)
            raw = self._provider.extract([], prompt)
        else:
            images = _pdf_to_page_images(pdf_bytes)
            if not images:
                # An empty list means text mode to a provider, so it must not reach one.
                return ExtractionResult(error="PDF has no pages")
            prompt = build_image_extraction_prompt(doc_type)
            raw = self._provider.extract(images, prompt)
```

3b. `backend/apps/documents/services/providers/base.py`. Replace the abstract `extract` (lines 27-39):

```python
    @abstractmethod
    def extract(self, image_data: bytes, prompt: str) -> str:
        """
        Extract structured data from document.

        Args:
            image_data: Raw image bytes (PDF/JPG/PNG)
            prompt: Extraction prompt with JSON schema

        Returns:
            JSON string with extracted data
        """
        pass
```

with:

```python
    @abstractmethod
    def extract(self, images: list[bytes], prompt: str) -> str:
        """
        Extract structured data from document.

        Args:
            images: JPEG bytes, one per page, in page order (a direct photo upload is a
                one-item list). An empty list means text mode: the document's text is
                already inside the prompt.
            prompt: Extraction prompt with JSON schema

        Returns:
            JSON string with extracted data
        """
        pass
```

Leave `classify` (lines 13-25) unchanged.

3c. `backend/apps/documents/services/providers/openai_provider.py`. In the class docstring, replace lines 16-17:

```
    Uses text mode (opendataloader-pdf extracted markdown → prompt) when image_data is empty.
    Uses vision mode (pymupdf JPEG or direct image upload) when image_data is non-empty.
```

with:

```
    Uses text mode (opendataloader-pdf extracted markdown → prompt) when there are no images.
    Uses vision mode (pymupdf JPEG pages or a direct image upload) otherwise, sending one
    image_url part per page, in page order, before the prompt.
```

Replace `classify` and `extract` (lines 30-38):

```python
    def classify(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision(image_data, prompt)
        return self._text(prompt)

    def extract(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision(image_data, prompt, json_mode=True)
        return self._text(prompt, json_mode=True)
```

with:

```python
    def classify(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision([image_data], prompt)
        return self._text(prompt)

    def extract(self, images: list[bytes], prompt: str) -> str:
        if images:
            return self._vision(images, prompt, json_mode=True)
        return self._text(prompt, json_mode=True)
```

Replace `_vision` (lines 43-53):

```python
    def _vision(self, image_data: bytes, prompt: str, *, json_mode: bool = False) -> str:
        # image/jpeg is hardcoded to match GeminiProvider: DocumentProcessor renders
        # PDF pages to JPEG and does not thread the original MIME type through.
        encoded = base64.b64encode(image_data).decode()
        return self._complete(
            [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}},
                {"type": "text", "text": prompt},
            ],
            json_mode=json_mode,
        )
```

with:

```python
    def _vision(self, images: list[bytes], prompt: str, *, json_mode: bool = False) -> str:
        # image/jpeg is hardcoded to match GeminiProvider: DocumentProcessor renders
        # PDF pages to JPEG and does not thread the original MIME type through.
        content: list[dict[str, Any]] = []
        for image in images:
            encoded = base64.b64encode(image).decode()
            content.append(
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
            )
        content.append({"type": "text", "text": prompt})
        return self._complete(content, json_mode=json_mode)
```

3d. `backend/apps/documents/services/providers/gemini.py`. In the class docstring, replace lines 15-16:

```
    Uses text mode (opendataloader-pdf extracted markdown → prompt) when image_data is empty.
    Uses vision mode (pymupdf JPEG or direct image upload) when image_data is non-empty.
```

with:

```
    Uses text mode (opendataloader-pdf extracted markdown → prompt) when there are no images.
    Uses vision mode (pymupdf JPEG pages or a direct image upload) otherwise, sending one
    inline image part per page, in page order, before the prompt.
```

Replace `classify` and `extract` (lines 24-32) with the same code as in 3c:

```python
    def classify(self, image_data: bytes, prompt: str) -> str:
        if image_data:
            return self._vision([image_data], prompt)
        return self._text(prompt)

    def extract(self, images: list[bytes], prompt: str) -> str:
        if images:
            return self._vision(images, prompt, json_mode=True)
        return self._text(prompt, json_mode=True)
```

In `_vision` (lines 47-58), replace:

```python
    def _vision(self, image_data: bytes, prompt: str, *, json_mode: bool = False) -> str:
        config = (
            types.GenerateContentConfig(response_mime_type="application/json")
            if json_mode
            else None
        )
        image_part = types.Part.from_bytes(data=image_data, mime_type="image/jpeg")
        response = self._client.models.generate_content(
            model=self.model,
            contents=[image_part, prompt],
            config=config,
        )
```

with:

```python
    def _vision(self, images: list[bytes], prompt: str, *, json_mode: bool = False) -> str:
        config = (
            types.GenerateContentConfig(response_mime_type="application/json")
            if json_mode
            else None
        )
        image_parts = [
            types.Part.from_bytes(data=image, mime_type="image/jpeg") for image in images
        ]
        response = self._client.models.generate_content(
            model=self.model,
            contents=[*image_parts, prompt],
            config=config,
        )
```

3e. `.github/workflows/ci.yml` (lines 74-77, job `backend-test`). Replace:

```yaml
      - name: Run tests with coverage
        working-directory: backend
        # --cov-fail-under floors coverage (currently ~95%) so it can't silently regress.
        run: pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q
```

with:

```yaml
      - name: Run tests with coverage
        working-directory: backend
        # --cov-fail-under floors coverage (currently ~95%) so it can't silently regress.
        # -rs lists each skipped test with its reason, so a real-JVM contract test that
        # skips (no `java` on the runner) shows in the log instead of passing quietly.
        run: pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs
```

The GitHub `ubuntu-latest` image is expected to ship a JDK on PATH, so `TestRealJvmContract` should **run** in CI, not skip. The jar needs Java 11 or newer. This is unconfirmed until the first push: check the backend job log's `-rs` summary. If it lists `SKIPPED ... TestRealJvmContract`, the runner has no `java`. Ticket that rather than editing the CLAUDE.md bullet to claim CI coverage.

- [ ] **Step 4: Run tests and confirm they pass**

Task 0 Step 3g installed ruff 0.8.5 and black 24.10.0 into `backend/.venv`, the versions CI and the pre-commit hook pin. Never use the conda `ruff` on PATH (0.14.x).

```bash
cd /Volumes/Containers/DigniFi/backend
.venv/bin/python -m pytest apps/documents -q -rs
.venv/bin/python -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs
PATH=/bin .venv/bin/python -m pytest apps/documents/tests/test_processor.py apps/documents/tests/test_processing_outcomes.py -q -rs
.venv/bin/ruff check .
.venv/bin/black --line-length 100 --check apps/documents/services apps/documents/tests
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
```

Expected:

- `apps/documents`: 0 failed and 0 skipped (Java is installed locally). The 16 tests from Step 2 now pass.
- Full suite: 0 failed, and `Required test coverage of 90% reached`. In verification this reached 95.22%.
- The `PATH=/bin` run hides `java`. It should show exactly 3 `SKIPPED [1] apps/documents/tests/test_processor.py:<line>: real-JVM contract tests need `java` on PATH and opendataloader-pdf installed`, and every test in `test_processing_outcomes.py` still passes.
- `ruff`: `All checks passed!`
- `black`: `would be left unchanged`
- `makemigrations`: `No changes detected`

**Optional: prove each converter option matters.** Edit `processor.py` once per bullet, run `.venv/bin/python -m pytest apps/documents/tests/test_processor.py apps/documents/tests/test_processing_outcomes.py -q`, then undo the edit with `git checkout -p` or by re-editing:

- Set `include_header_footer=False`: only `test_real_jvm_keeps_the_letterhead_that_names_the_creditor` fails.
- Delete `image_output="off",`: `test_a_scanned_pdf_sends_at_most_three_page_images_in_order` and `test_real_jvm_sends_a_scanned_pdf_to_vision` fail.
- Re-add `hybrid="docling-fast",`: the page-two outcome test and the page-two and letterhead contract tests fail.

- [ ] **Step 5: Update CLAUDE.md gotchas**

In the root `CLAUDE.md` "Gotchas" list, make three replacements. Find each bullet by its text, because earlier tasks may have shifted the line numbers.

Replace (line 35):

```
- **opendataloader-pdf needs a JRE** — both Dockerfiles install `default-jre-headless`. Without it, PDF upload errored (tests mock the module so CI can't catch it).
```

with:

```
- **opendataloader-pdf needs a JRE** — both Dockerfiles install `default-jre-headless`. Without one, every PDF falls back to vision. `TestRealJvmContract` (`apps/documents/tests/test_processor.py`) runs the real CLI wherever `java` is on PATH and skips with a visible reason elsewhere (`-rs` in CI); every other test uses a stand-in for the module.
```

Replace (line 52):

```
- **`hybrid="docling-fast"` can't work on Heroku** — it needs the `odl-hybrid` sidecar on `localhost:5002` from `docker-compose.yml`; Heroku runs a single container. It's caught and falls back to vision OCR, so the `Hybrid server is not available` log noise is not the failure.
```

with:

```
- **PDFs: text layer first, then up to 3 scanned pages** — `processor.py` runs `opendataloader_pdf.convert(..., format="markdown", image_output="off", include_header_footer=True)` with no hybrid arguments. Text of at least `_MIN_TEXT_LENGTH` (30) characters goes to the text prompt; otherwise `_pdf_to_page_images()` sends up to `_MAX_SCANNED_PAGES` (3) JPEG pages to vision, and a PDF with no pages fails. Without `image_output="off"` a scan's image placeholders reach the text prompt; without `include_header_footer=True` the letterhead naming the creditor is dropped.
```

Replace (line 53):

```
- **Vision fallback reads page 1 only** — `_pdf_to_image_bytes(pdf_bytes, page_index=0)`; multi-page creditor bills extract partially even on success.
```

with:

```
- **`extract()` takes a list of page images** — `BaseOCRProvider.extract(images: list[bytes], prompt)`: `[]` means text mode, a photo upload is a one-item list, and pages go in page order (one OpenAI `image_url` part or one Gemini inline part each). `classify()` still takes bytes. Never hand a provider `[]` for a scan.
```

- [ ] **Step 6: Commit**

```bash
cd /Volumes/Containers/DigniFi
git add backend/apps/documents/services/processor.py \
        backend/apps/documents/services/providers/base.py \
        backend/apps/documents/services/providers/openai_provider.py \
        backend/apps/documents/services/providers/gemini.py \
        backend/apps/documents/tests/builders.py \
        backend/apps/documents/tests/test_processing_outcomes.py \
        backend/apps/documents/tests/test_processor.py \
        backend/apps/documents/tests/test_openai_provider.py \
        backend/apps/documents/tests/test_gemini_provider.py \
        .github/workflows/ci.yml
git diff CLAUDE.md
```

`git diff CLAUDE.md` must show only this task's Step 5 hunks: the three bullet replacements. Tasks 1–2 committed every other `CLAUDE.md` change (including the triage gotchas and the two hybrid/page-1 bullets this task replaces), and Tasks 3–4 committed their own bullets. If anything else appears, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it. Then:

```bash
cd /Volumes/Containers/DigniFi && git add CLAUDE.md && git diff --cached CLAUDE.md
```

The cached diff shows the three bullet replacements as `-`/`+` pairs, because Task 1 committed the old bullets.

Never stage `.serena/`, `DESIGN.md`, `assets/`, `.impeccable` or the README landing-image hunk.

```bash
git commit -F - <<'EOF'
fix(documents): read every page of a PDF without the hybrid sidecar

The processor asked opendataloader for hybrid="docling-fast", which needs the
odl-hybrid sidecar. Heroku has none, so the Java CLI exited 1 on every PDF and
the processor fell back to vision on page 1 only: a balance printed on page 2
never reached the model (DIG-4).

convert() now runs the Java CLI alone. image_output="off" makes a scan yield no
text, so it routes to vision instead of sending image placeholders to the text
prompt; include_header_footer=True keeps the letterhead that names the
creditor. A scan sends up to three pages to vision, in page order, and a PDF
with no pages fails instead of completing empty. Providers now take a list of
page images: [] is text mode and a photo is a one-item list.

A real-JVM contract test runs wherever java is on PATH and skips visibly
elsewhere; CI's pytest gains -rs so a skip shows in the log.
EOF
```

Pre-commit runs ruff, black and prettier (`CLAUDE.md`). If a hook rewrites a file, `git add` the same files again, including `git add CLAUDE.md`, then rerun the same `git commit` command. Do not add any `Co-Authored-By` or agent trailer.

---

### Task 6: Drop the odl-hybrid sidecar and the [hybrid] extra  (Commit #7 in spec §9)

Spec: §4.11. Tickets: DIG-4, DIG-16 (part).

**Why.** After Task 5 nothing calls the hybrid server. `docker compose up` still builds and waits on an `odl-hybrid` service: the backend `depends_on` it with `condition: service_healthy` and a 60 s `start_period`. The `[hybrid]` extra adds `docling[easyocr]` (which pulls torch and CUDA), `fastapi`, `python-multipart` and `uvicorn` to every backend image, Heroku included. The plain `opendataloader-pdf` 2.4.3 has **no** `Requires-Dist` beyond its extra; this was verified in the package METADATA. Nothing in `backend/` imports fastapi, uvicorn, multipart, docling, easyocr or torch; this was verified with `git grep`.

**Files:**

- Modify: `docker-compose.yml:34-38` (backend `depends_on`) and `:55-69` (the `odl-hybrid` service)
- Modify: `backend/requirements/base.txt:12`
- Modify: `CLAUDE.md:8, 36, 111`
- Test: none. This is a config-only commit. The checks are the commands in Steps 1, 2 and 4, plus the backend suite still passing.

**Interfaces:**

- **Consumes:** Task 5's processor, which passes no `hybrid*` argument to `opendataloader_pdf.convert`. So nothing reaches for a sidecar.
- **Produces:**
  - Compose services: `db`, `backend` and `frontend` only.
  - The requirement line `opendataloader-pdf` with no extras.

- [ ] **Step 1: Write the failing test**

No automated test fits. A unit test that greps requirement files tests text, not behavior. The checks are these commands, run from the repo root (`docker compose config` reads the root `.env`, which exists locally):

```bash
cd /Volumes/Containers/DigniFi
docker compose config --services
git grep -n "opendataloader" -- backend/requirements/base.txt
git grep -n -i "hybrid" -- docker-compose.yml backend/requirements backend/apps/documents/services
```

- [ ] **Step 2: Run it and confirm it fails**

Run the Step 1 commands. Expected today:

- `docker compose config --services` prints `db`, `odl-hybrid`, `backend`, `frontend`.
- The first `git grep` prints `backend/requirements/base.txt:12:opendataloader-pdf[hybrid]`. (Use `git grep`, not `grep`: here `grep` is aliased to `rg`, and `rtk` rewrites its output.)
- The second `git grep` prints the `docker-compose.yml` lines 37, 55 and 61, and `backend/requirements/base.txt:12`. There is no hit in `backend/apps/documents/services`, because Task 5 removed `hybrid="docling-fast"`.

- [ ] **Step 3: Implement**

3a. `docker-compose.yml`. In the `backend` service, replace lines 34-38:

```yaml
    depends_on:
      db:
        condition: service_healthy
      odl-hybrid:
        condition: service_healthy
```

with:

```yaml
    depends_on:
      db:
        condition: service_healthy
```

Then delete the whole `odl-hybrid` service: lines 55-69 plus the blank line after them, so that `frontend`'s `tty: true` is followed by one blank line and then `volumes:`. Remove this block:

```yaml
  odl-hybrid:
    build:
      context: ./backend
      dockerfile: Dockerfile
      args:
        REQUIREMENTS_FILE: requirements/development.txt
    command: opendataloader-pdf-hybrid --port 5002 --force-ocr
    ports:
      - '5002:5002'
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:5002/health']
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

```

The end of the file must then read:

```yaml
    stdin_open: true
    tty: true

volumes:
  postgres_data:
```

Leave `curl` in `backend/Dockerfile` and `Dockerfile.heroku` alone. The backend `HEALTHCHECK` and Heroku's release-phase log streamer use it.

3b. `backend/requirements/base.txt`. Replace line 12:

```
opendataloader-pdf[hybrid]
```

with:

```
opendataloader-pdf
```

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd /Volumes/Containers/DigniFi
docker compose config --services
docker compose config --quiet && echo "compose config valid"
git grep -n "opendataloader" -- backend/requirements/base.txt
git grep -n -i "hybrid" -- docker-compose.yml backend/requirements backend/apps/documents/services
backend/.venv/bin/pip show torch docling 2>&1 | head -1
cd backend && .venv/bin/python -m pytest apps/documents -q -rs
```

Expected:

- `docker compose config --services` prints `db`, `backend`, `frontend`.
- `compose config valid`.
- The first `git grep` prints `backend/requirements/base.txt:12:opendataloader-pdf`.
- The second `git grep` prints nothing and exits 1.
- `pip show` prints `WARNING: Package(s) not found: docling, torch`. That is today's local venv. If either package is installed, recreate the venv with the commands in the commit body before going on.
- The documents tests show 0 failed, and `TestRealJvmContract` runs, because the Java CLI still ships in the plain package.

Optional, only if you use the compose stack: `docker compose up --build --remove-orphans -d && docker compose ps` should list db, backend and frontend, with no `odl-hybrid`. Colima must mount `/Volumes/Containers` (see the CLAUDE.md gotcha).

- [ ] **Step 5: Update CLAUDE.md gotchas**

In the root `CLAUDE.md`, find each line by its text.

Quick Commands, replace (line 8):

```
docker compose up                              # Start all 4 services (db, backend, frontend, odl-hybrid)
```

with:

```
docker compose up                              # Start all 3 services (db, backend, frontend)
```

Gotchas, replace (line 36):

```
- **opendataloader-pdf healthcheck** — 60s start_period; backend `depends_on: odl-hybrid` condition `service_healthy`.
```

with:

```
- **No PDF sidecar** — the `odl-hybrid` service and the `opendataloader-pdf[hybrid]` extra are gone; the backend runs the Java CLI itself. A stack or venv built before the removal still has them: run `docker compose up --build --remove-orphans` and recreate `backend/.venv` (`pip install -r` never uninstalls docling or torch).
```

File Map → Infra, replace (line 111):

```
- `docker-compose.yml` — 4 services: db (postgres:15), backend, frontend, odl-hybrid (opendataloader-pdf)
```

with:

```
- `docker-compose.yml` — 3 services: db (postgres:15), backend, frontend
```

- [ ] **Step 6: Commit**

```bash
cd /Volumes/Containers/DigniFi
git add docker-compose.yml backend/requirements/base.txt
git diff CLAUDE.md
```

`git diff CLAUDE.md` must show only this task's three Step 5 replacements. Tasks 1–2 committed every other `CLAUDE.md` change, and Tasks 3–5 committed their own. If anything else appears, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it. Then run `git add CLAUDE.md`. Check with `git diff --cached --stat`, which should list exactly `CLAUDE.md`, `backend/requirements/base.txt` and `docker-compose.yml`.

```bash
git commit -F - <<'EOF'
chore(infra): drop the odl-hybrid sidecar and the [hybrid] extra

Nothing calls the hybrid server since the processor stopped passing
hybrid="docling-fast". The compose stack still built and health-checked an
odl-hybrid container before the backend could start, and the [hybrid] extra
put docling, easyocr, torch and CUDA wheels, fastapi and uvicorn into every
backend image, Heroku's included (DIG-4, most of DIG-16). The plain
opendataloader-pdf package still ships the Java CLI the processor runs.

After pulling this commit:

  docker compose up --build --remove-orphans

and recreate the backend venv, because pip install -r never uninstalls
packages the old extra pulled in:

  rm -rf backend/.venv
  python3.11 -m venv backend/.venv
  backend/.venv/bin/pip install -r backend/requirements/development.txt
EOF
```

If pre-commit's prettier rewrites `CLAUDE.md`, run `git add CLAUDE.md` again and rerun the same `git commit` command. Do not add any `Co-Authored-By` or agent trailer.

---

### Task 7: Retry an empty OpenAI reply once and record why  (Commit #8 in spec §9)

Spec: §4.9, contract C3. Tickets: DIG-9.

**Why.** `OpenAIProvider._complete` returns `message.content or ""`. An empty reply (content `None`, or only whitespace) therefore reaches `json.loads`. The upload then fails as "Failed to parse LLM response: " with nothing to say why. An empty reply is often a one-off, so it deserves one retry. A refusal or a `content_filter` stop would only repeat. Separately, `_parse_result` copies `raw[:200]` into the error. That error is stored in `OCRResult.error_message`, an operations field, and model output can quote the filer's document.

**Facts verified while writing this task:**

- The installed `openai` is 1.60.0.
- `ChatCompletionMessage` has `content` and `refusal`.
- `Choice.finish_reason` is `Literal['stop', 'length', 'tool_calls', 'content_filter', 'function_call']`.
- In the existing `mock_openai_client` fixture, `message.refusal` is an auto-created `MagicMock`, which is truthy, and `finish_reason` is a `Mock`, not a string. That is why every new test builds real SDK objects with `builders.chat_completion(...)`.

**Files:**

- Modify: `backend/apps/documents/services/providers/base.py:3-6` (add the exception class before `class BaseOCRProvider`)
- Modify: `backend/apps/documents/services/providers/openai_provider.py:9` (import) and `:63-64` (end of `_complete`; line numbers after Task 5)
- Modify: `backend/apps/documents/services/processor.py:133` (`_parse_result` error; line number after Task 5)
- Modify: `backend/apps/documents/tests/test_openai_provider.py:8` (imports) and `:83-89` (`TestProviderContract`; after Task 5), and append a class
- Modify: `backend/apps/documents/tests/test_processor.py`: insert after `test_invalid_json_returns_failed_result` (`:53-57` after Task 5)
- Modify: `backend/apps/documents/tests/test_processing_outcomes.py`: append (created in Task 5)
- Modify: `CLAUDE.md`: add one gotcha
- Test: `backend/apps/documents/tests/test_processing_outcomes.py`, `backend/apps/documents/tests/test_openai_provider.py`, `backend/apps/documents/tests/test_processor.py`

**Interfaces:**

- **Consumes** from Task 5:
  - `builders.chat_completion(content, *, finish_reason="stop", refusal=None)`;
  - the fixtures `filer`, `openai_client` and autouse `text_layer_jvm`;
  - the helper `upload(...)`;
  - `OpenAIProvider.extract(images: list[bytes], prompt)`.
- **Produces (C3):**
  - `apps.documents.services.providers.base.EmptyModelReply(RuntimeError)`. `OpenAIProvider._complete` raises it after the retry, or at once on a refusal or `content_filter`.
  - The message format is exactly `model reply was empty (finish_reason=<finish_reason>, refusal=<present|absent>)`. It never contains refusal text.
  - `DocumentProcessor.process` catches it and stores `str(exc)` in `ExtractionResult.error`, so `OCRResult.error_message` names the cause. Task 8 (commit 9) must keep that text in `error_message` when it adds `failure_reason`.
  - `_parse_result` error: `model reply was not valid JSON (<len(raw)> characters)`.

- [ ] **Step 1: Write the failing tests**

1a. Append to `backend/apps/documents/tests/test_processing_outcomes.py`. Use the module's existing imports; `chat_completion`, `DocumentType` and `OCRStatus` are already imported.

```python


def test_an_empty_reply_is_retried_once_and_its_cause_is_recorded(filer, openai_client):
    openai_client.chat.completions.create.return_value = chat_completion(
        " \n", finish_reason="length"
    )

    ocr = upload(filer, b"\xff\xd8\xff", "bill.jpg", "image/jpeg", DocumentType.CREDITOR_BILL)

    assert openai_client.chat.completions.create.call_count == 2
    assert ocr.status == OCRStatus.FAILED
    assert "finish_reason=length" in ocr.error_message
    assert "refusal=absent" in ocr.error_message
```

1b. `backend/apps/documents/tests/test_openai_provider.py`. Replace the import line 8:

```python
from apps.documents.services.providers.openai_provider import OpenAIProvider
```

with:

```python
from apps.documents.services.providers.base import EmptyModelReply
from apps.documents.services.providers.openai_provider import OpenAIProvider
from apps.documents.tests.builders import chat_completion
```

Replace the start of `TestProviderContract` (after Task 5, lines 83-89):

```python
class TestProviderContract:
    """BaseOCRProvider promises a str. A None completion must not leak downstream as a
    TypeError inside json.loads."""

    def test_empty_completion_becomes_empty_string(self, provider, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value.choices[0].message.content = None
        assert provider.extract([], "Return ONLY a valid JSON object.") == ""
```

with:

```python
class TestProviderContract:
    """BaseOCRProvider promises a str. A None completion must not leak downstream as a
    TypeError inside json.loads; it raises EmptyModelReply instead."""

    def test_empty_completion_raises_instead_of_reaching_the_parser(
        self, provider, mock_openai_client
    ):
        mock_openai_client.chat.completions.create.return_value = chat_completion(None)
        with pytest.raises(EmptyModelReply):
            provider.extract([], "Return ONLY a valid JSON object.")
```

Keep `test_configured_model_is_the_one_requested` as it is. Append at the end of the file:

```python


class TestEmptyReplies:
    """An empty reply used to reach json.loads and fail as unparseable, leaving no trace
    of why. It is now retried once when a retry can help, and the error says why the
    reply was empty without quoting anything the model wrote."""

    def test_a_whitespace_reply_is_retried_once_then_reported(self, provider, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = chat_completion(
            " \n\t", finish_reason="length"
        )
        with pytest.raises(EmptyModelReply, match=r"finish_reason=length, refusal=absent"):
            provider.extract([], "Return ONLY a valid JSON object.")
        assert mock_openai_client.chat.completions.create.call_count == 2

    def test_a_retry_that_answers_is_used(self, provider, mock_openai_client):
        mock_openai_client.chat.completions.create.side_effect = [
            chat_completion(None),
            chat_completion('{"creditor_name": "Lakeshore Medical Billing"}'),
        ]
        reply = provider.extract([], "Return ONLY a valid JSON object.")
        assert reply == '{"creditor_name": "Lakeshore Medical Billing"}'

    def test_a_refusal_is_not_retried_and_its_wording_is_not_kept(
        self, provider, mock_openai_client
    ):
        mock_openai_client.chat.completions.create.return_value = chat_completion(
            None, refusal="I can't read the statement for Jordan Sample, SSN 900-12-3456."
        )
        with pytest.raises(EmptyModelReply) as raised:
            provider.extract([b"\xff\xd8\xff"], "Return ONLY a valid JSON object.")
        assert mock_openai_client.chat.completions.create.call_count == 1
        assert "refusal=present" in str(raised.value)
        assert "Jordan Sample" not in str(raised.value)
        assert "900-12-3456" not in str(raised.value)

    def test_a_filtered_reply_is_not_retried(self, provider, mock_openai_client):
        mock_openai_client.chat.completions.create.return_value = chat_completion(
            None, finish_reason="content_filter"
        )
        with pytest.raises(EmptyModelReply, match="finish_reason=content_filter"):
            provider.extract([b"\xff\xd8\xff"], "Return ONLY a valid JSON object.")
        assert mock_openai_client.chat.completions.create.call_count == 1
```

1c. `backend/apps/documents/tests/test_processor.py`. Keep `test_invalid_json_returns_failed_result`. Directly after it, before `def test_pdf_with_text_routes_to_text_path`, insert the following. The SSN is from the IRS-reserved 900 range used for synthetic data.

```python
def test_an_unparseable_reply_is_recorded_without_its_text(processor, mock_provider):
    # error_message is an operations field, and a reply can quote the filer's document.
    reply = "Jordan Sample, SSN 900-12-3456, owes $1,284.50"
    mock_provider.extract.return_value = reply
    result = processor.process(b"\xff\xd8", "image/jpeg", DocumentType.CREDITOR_BILL)
    assert result.error == f"model reply was not valid JSON ({len(reply)} characters)"
    assert "900-12-3456" not in result.error


```

- [ ] **Step 2: Run it and confirm it fails**

```bash
cd /Volumes/Containers/DigniFi/backend
.venv/bin/python -m pytest apps/documents -q
.venv/bin/python -m pytest apps/documents/tests/test_processing_outcomes.py apps/documents/tests/test_processor.py -q
```

Expected:

- **First command:** collection stops with `ImportError: cannot import name 'EmptyModelReply' from 'apps.documents.services.providers.base'` in `test_openai_provider.py`, followed by `Interrupted: 1 error during collection`.
- **Second command:** 2 failed:
  - `test_an_empty_reply_is_retried_once_and_its_cause_is_recorded`: `assert 1 == 2`. There is no retry today.
  - `test_an_unparseable_reply_is_recorded_without_its_text`: `assert 'Failed to parse LLM response: Jordan Sample, SSN 900-12-3456, owes $1,284.50' == 'model reply was not valid JSON (46 characters)'`. Today the SSN leaks into the error.

- [ ] **Step 3: Implement**

3a. `backend/apps/documents/services/providers/base.py`. Replace:

```python
from abc import ABC, abstractmethod


class BaseOCRProvider(ABC):
```

with:

```python
from abc import ABC, abstractmethod


class EmptyModelReply(RuntimeError):
    """The model sent back no text, after a retry where one could help.

    The message names ``finish_reason`` and whether a refusal was present. It never
    includes the refusal's wording, because it is stored in ``OCRResult.error_message``
    and a refusal can quote the filer's document.
    """


class BaseOCRProvider(ABC):
```

3b. `backend/apps/documents/services/providers/openai_provider.py`. Replace the import on line 9:

```python
from .base import BaseOCRProvider
```

with:

```python
from .base import BaseOCRProvider, EmptyModelReply
```

At the end of `_complete` (after Task 5, lines 61-64), replace:

```python
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""
```

with:

```python
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        choice = self._client.chat.completions.create(**kwargs).choices[0]
        # An empty reply is often a one-off, so it gets one retry. A refusal or a
        # content filter would only repeat, so neither is retried.
        refused = bool(choice.message.refusal) or choice.finish_reason == "content_filter"
        if not (choice.message.content or "").strip() and not refused:
            choice = self._client.chat.completions.create(**kwargs).choices[0]
        reply = choice.message.content or ""
        if not reply.strip():
            raise EmptyModelReply(
                f"model reply was empty (finish_reason={choice.finish_reason}, "
                f"refusal={'present' if choice.message.refusal else 'absent'})"
            )
        return reply
```

`classify()` also goes through `_complete`, so a blank classification raises too. Nothing in production calls `classify()` (verified with grep).

3c. `backend/apps/documents/services/processor.py`. In `_parse_result`'s `except (json.JSONDecodeError, ValueError):` branch (after Task 5, line 133), replace:

```python
                error=f"Failed to parse LLM response: {raw[:200]}",
```

with:

```python
                error=f"model reply was not valid JSON ({len(raw)} characters)",
```

Leave `process()`'s `except Exception as exc: return ExtractionResult(error=str(exc))` unchanged. That is what carries the `EmptyModelReply` message into `OCRResult.error_message` through `views._run_processing`. Gemini's empty-reply parity (DIG-35) and an OpenAI client timeout (DIG-29) stay out of scope.

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd /Volumes/Containers/DigniFi/backend
.venv/bin/python -m pytest apps/documents -q -rs
.venv/bin/python -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs
.venv/bin/ruff check .
.venv/bin/black --line-length 100 --check apps/documents/services apps/documents/tests
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
```

Expected:

- `apps/documents`: 0 failed. These new tests pass:
  - the outcome test;
  - `TestProviderContract::test_empty_completion_raises_instead_of_reaching_the_parser`;
  - the four `TestEmptyReplies` tests;
  - `test_an_unparseable_reply_is_recorded_without_its_text`.
- Full suite: 0 failed, and `Required test coverage of 90% reached`. In verification this reached 95.22%.
- `ruff`: `All checks passed!`
- `black`: unchanged.
- `makemigrations`: `No changes detected`.

- [ ] **Step 5: Update CLAUDE.md gotchas**

In the root `CLAUDE.md` "Gotchas" list, add this bullet directly after the `**`extract()` takes a list of page images**` bullet that Task 5 added:

```
- **An empty OpenAI reply raises `EmptyModelReply`** — `OpenAIProvider._complete` retries a blank or whitespace-only reply once, but never a refusal or `finish_reason == "content_filter"`. The error names `finish_reason` and whether a refusal was present, never its text. `_parse_result` records only the reply's length ("model reply was not valid JSON (N characters)"), so `error_message` never holds model output. Gemini still returns `""` (DIG-35).
```

- [ ] **Step 6: Commit**

```bash
cd /Volumes/Containers/DigniFi
git add backend/apps/documents/services/providers/base.py \
        backend/apps/documents/services/providers/openai_provider.py \
        backend/apps/documents/services/processor.py \
        backend/apps/documents/tests/test_openai_provider.py \
        backend/apps/documents/tests/test_processor.py \
        backend/apps/documents/tests/test_processing_outcomes.py
git diff CLAUDE.md
```

`git diff CLAUDE.md` must show only the new Step 5 bullet. Tasks 1–2 committed every other `CLAUDE.md` change, and Tasks 3–6 committed their own. If anything else appears, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it. Then run `git add CLAUDE.md`, and check that `git diff --cached CLAUDE.md` shows exactly one added line.

```bash
git commit -F - <<'EOF'
fix(documents): retry an empty OpenAI reply once and record why

An empty reply (content None or only whitespace) reached json.loads and failed
as "Failed to parse LLM response: " with no hint of the cause (DIG-9). The
provider now retries it once, but not a refusal or a content_filter stop,
which would only repeat. If the reply is still empty it raises EmptyModelReply
naming finish_reason and whether a refusal was present, never the refusal's
wording, and that message is what lands in OCRResult.error_message.

_parse_result no longer copies the first 200 characters of an unparseable
reply into the error. error_message is an operations field, and a reply can
quote the filer's document, so it now records only the reply's length.
EOF
```

If pre-commit rewrites a file, `git add` the same files again, including `git add CLAUDE.md`, then rerun the same `git commit` command. Do not add any `Co-Authored-By` or agent trailer.

---

### Task 8: Report a scan that found nothing as failed, not done  (Commit #9 in spec §9)

Spec §4.7 (DIG-7). Today every upload that the model answers at all is marked `completed`, even when it found nothing. The upload page then shows "✓ Done" while nothing reaches the wizard. Three more silent losses sit behind that:

- A bill whose `creditor_name` is `null` crashes `DraftDebtCreator` (`None[:255]`), and `views.py:69-72` swallows the crash.
- One malformed account line fails the whole credit report, and `views.py:73-82` swallows that too.
- A real pay stub never reaches Schedule I. `processor._parse_result` pops `confidence_score` before storage, and `PayStubExtraction` requires it, so the aggregator skips every stub.

After this task, a scan is `completed` only when it found something the filer can use. Otherwise it is `failed` with a reason code (`nothing_found` | `processing_error`). The documents API returns that code and stops returning provider text (`error_message`) and decrypted PII (`extracted_data`).

**Files:**
- Modify: `backend/apps/documents/models.py:44-51` (add `OCRFailureReason` after `OCRStatus`), `:129` (add `failure_reason` after `status`), `:150` (comment on `error_message`)
- Create: `backend/apps/documents/migrations/0006_ocrresult_failure_reason.py`
- Modify (whole file): `backend/apps/documents/schemas/credit_report.py:1-27`
- Modify: `backend/apps/documents/schemas/paystub.py:18` (add `confidence_score` default above `employer_name`)
- Modify (whole file): `backend/apps/documents/services/draft_debt.py:1-84`
- Modify: `backend/apps/documents/services/aggregator.py:65-66`
- Modify: `backend/apps/documents/services/processor.py`: the import at :13 (`from apps.documents.services.providers.base import BaseOCRProvider`), `process()`'s `except Exception as exc:` at :62-63, and :116 (`confidence_score = int(data.pop("confidence_score", 0))`), all in today's tree. Tasks 5 and 7 edit this file first, so find each hunk by its text, not its number.
- Modify: `backend/apps/documents/views.py:5-18` (imports), `:46` (new `_record_findings` above `_run_processing`), `:57-84` (outcome branches), `:92-99` (outer except), `:138-144` (`OCRResult.objects.create`), `:215-223` (`_serialize_ocr`)
- Modify: `frontend/src/types/api.ts:333-342` (contract C4)
- Modify: `CLAUDE.md` (Gotchas list)
- Test (modify): `backend/apps/documents/tests/test_processing_outcomes.py` (created in Task 5, appended to in Task 7): the import block at the top, and append after Task 7's `test_an_empty_reply_is_retried_once_and_its_cause_is_recorded`
- Test (modify): `backend/apps/documents/tests/test_draft_debt.py:1-3` (import) and after `:88` (two new tests and a helper)
- Test (modify): `backend/apps/documents/tests/test_aggregator.py` (append after `:99`)
- Test (modify): `backend/apps/documents/tests/test_aggregator_hooks.py:49`

**Interfaces:**
- Consumes:
  - From Task 1 (commit 2): `apps.documents.views._get_processor()`, which builds `OpenAIProvider` when `settings.OCR_PROVIDER == "openai"`, and `settings.OCR_PROVIDER` / `settings.OCR_MODEL`.
  - From Tasks 5 and 7 (commits 6 and 8): `DocumentProcessor.process(file_bytes, mime_type, doc_type) -> ExtractionResult`. The fields `fields`, `confidence`, `detected_type` and `error` are unchanged.
  - Contract C1: `BaseOCRProvider.extract(images: list[bytes], prompt)`.
  - Contract C3: `EmptyModelReply`, whose message reaches `ExtractionResult.error` and therefore `OCRResult.error_message`. `processor.py` now imports it by name: `process()` keeps its message (it names `finish_reason` and whether a refusal was present, never model text) and reduces every other exception to its class name (spec §4.7). Task 7 left `process()`'s `except` unchanged at commit 8; this task is the one that changes it.
  - From Task 5 (commit 6), in `apps/documents/tests/test_processing_outcomes.py`: the fixtures `filer` (`(APIClient, IntakeSession)` on `transactional_db`) and `openai_client` (the mocked client), the autouse `text_layer_jvm`, and the helper `upload(filer, data, filename, mime_type, document_type) -> OCRResult`; from `apps/documents/tests/builders.py`, `chat_completion(content, *, finish_reason="stop", refusal=None)`.
  - The outcome tests assume `OpenAIProvider` reads `response.choices[0].message.content`, `.message.refusal` and `.finish_reason`.
- Produces:
  - **C2:** `apps.documents.models.OCRFailureReason` (`NOTHING_FOUND = "nothing_found"`, `PROCESSING_ERROR = "processing_error"`), `OCRResult.failure_reason` (CharField, max_length 32, blank, default `""`) and migration `documents/0006_ocrresult_failure_reason`.
  - **API shape:** `_serialize_ocr(ocr) -> {"status", "failure_reason", "confidence_scores", "overall_confidence", "user_validated"}`, served by `GET /api/documents/`, `GET /api/documents/{id}/` and `POST /api/documents/{id}/validate/`.
  - **C4:** in `frontend/src/types/api.ts`, `export type OCRFailureReason = 'nothing_found' | 'processing_error'`, and `OCRResult` = `{ status, failure_reason: OCRFailureReason | '', confidence_scores, overall_confidence, user_validated }`. Task 14 (commit 15) consumes it and does not re-add it.
  - `DraftDebtCreator.create_from_result(result, session, source_document) -> DebtInfo | None` returns `None` when the bill names no creditor.
  - `apps.documents.services.draft_debt._bounded_amount(value: object) -> Decimal`.
  - `apps.documents.views._record_findings(doc: UploadedDocument, result: ExtractionResult) -> bool`.
  - `TradelineItem` changes: `account_type` and `account_status` become optional, numbers coerce to `str`, `creditor_name` is stripped with `min_length=1`, and `amount_owed` has `le=9999999999.99`. Task 9 derives its test from `TradelineItem.model_fields`.
  - `CreditReportExtraction.tradelines` defaults to `[]` and keeps only lines that validate.
  - `PayStubExtraction.confidence_score` defaults to 0.

- [ ] **Step 1: Write the failing tests**

Add the spec §8 "processing outcomes" tests for §4.7 to `backend/apps/documents/tests/test_processing_outcomes.py`, the file spec §8 names for them. Task 5 created it and Task 7 appended one test. These tests reuse its fixtures and helpers instead of a second harness:

- `filer` is an `(APIClient, IntakeSession)` pair on `transactional_db`, so the upload view's worker thread sees the rows;
- `openai_client` is the mocked OpenAI client; a test sets `chat.completions.create.return_value` or `side_effect`;
- `upload(...)` posts through the real endpoint and returns the final `OCRResult`;
- `chat_completion(...)` builds a real SDK reply.

Uploads are photos (JPEG), so the autouse JVM stand-in is never called.

Read the file, then edit its import block with the Edit tool. Replace:

```python
import base64
import os
import subprocess
from unittest.mock import patch
```

with:

```python
import base64
import json
import os
import subprocess
from decimal import Decimal
from unittest.mock import patch
```

Replace:

```python
from apps.documents.models import DocumentType, OCRResult, OCRStatus
```

with:

```python
from apps.documents.models import DocumentType, IngestedAggregate, OCRResult, OCRStatus
```

Replace:

```python
from apps.intake.models import IntakeSession
```

with:

```python
from apps.intake.models import DebtInfo, IntakeSession
```

Then append this block at the end of the file, after Task 7's `test_an_empty_reply_is_retried_once_and_its_cause_is_recorded`. Keep two blank lines between top-level definitions:

```python
# What a scan found, as the filer sees it on the upload page (spec 2026-10-09 §4.7).


def scan_photo(filer, openai_client, document_type, reply=None, error=None) -> dict:
    """Upload a photo of a document, let the model answer ``reply`` (or raise ``error``),
    and return the document as the upload page reads it. A photo never starts the JVM."""
    create = openai_client.chat.completions.create
    if error is not None:
        create.side_effect = error
    else:
        create.return_value = chat_completion(json.dumps(reply))
    ocr = upload(filer, b"\xff\xd8\xff", "scan.jpg", "image/jpeg", document_type)
    client, _ = filer
    response = client.get(f"/api/documents/{ocr.document_id}/")
    assert response.status_code == 200
    return response.json()


def test_cover_page_with_no_account_details_is_reported_as_nothing_found(filer, openai_client):
    _, session = filer
    cover_page = {
        "creditor_name": None,
        "account_number": None,
        "amount_owed": None,
        "minimum_payment": None,
        "due_date": None,
        "creditor_type": None,
        "confidence_score": None,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, reply=cover_page)

    assert doc["ocr_result"]["status"] == "failed"
    assert doc["ocr_result"]["failure_reason"] == "nothing_found"
    assert not DebtInfo.objects.filter(session=session).exists()


@pytest.mark.parametrize("creditor_name", [None, "", "   "])
def test_bill_without_a_creditor_creates_no_debt_and_does_not_crash(
    filer, openai_client, creditor_name
):
    _, session = filer
    bill = {
        "creditor_name": creditor_name,
        "amount_owed": "125.00",
        "creditor_type": "medical",
        "confidence_score": 40,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, reply=bill)

    # A crash would surface as processing_error; an unnamed creditor is "nothing found".
    assert doc["ocr_result"]["status"] == "failed"
    assert doc["ocr_result"]["failure_reason"] == "nothing_found"
    assert not DebtInfo.objects.filter(session=session).exists()


def test_bill_with_a_creditor_but_unreadable_balance_becomes_a_draft_to_complete(
    filer, openai_client
):
    _, session = filer
    bill = {
        "creditor_name": "Lakeshore Medical Group",
        "account_number": "88213",
        "amount_owed": None,
        "creditor_type": "medical",
        "confidence_score": 55,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, reply=bill)

    assert doc["ocr_result"]["status"] == "completed"
    assert doc["ocr_result"]["failure_reason"] == ""
    draft = DebtInfo.objects.get(session=session)
    assert draft.is_draft is True
    assert draft.creditor_name == "Lakeshore Medical Group"
    assert draft.amount_owed == Decimal("0")
    assert draft.source_document_id == doc["id"]


def test_pay_stub_upload_produces_monthly_income_for_schedule_i(filer, openai_client):
    _, session = filer
    pay_stub = {
        "employer_name": "Acme Logistics",
        "gross_pay": "1000.00",
        "pay_period_start": "2026-01-01",
        "pay_period_end": "2026-01-14",
        "ytd_gross": None,
        "net_pay": "812.40",
        "deductions_total": "187.60",
        "confidence_score": 92,
    }

    doc = scan_photo(filer, openai_client, DocumentType.PAY_STUB, reply=pay_stub)

    assert doc["ocr_result"]["status"] == "completed"
    # Schedule I reads ingest_key "paystub.gross": 1000 / 14 days * 30.41667 = 2172.62.
    gross = IngestedAggregate.objects.get(session=session, ingest_key="paystub.gross")
    assert gross.value == "2172.62"
    assert not DebtInfo.objects.filter(session=session).exists()


@pytest.mark.parametrize(
    "tradelines",
    [[], None, [{"creditor_name": "", "amount_owed": None}]],
    ids=["empty-list", "null", "only-unreadable-lines"],
)
def test_credit_report_with_no_readable_accounts_is_reported_as_nothing_found(
    filer, openai_client, tradelines
):
    _, session = filer
    doc = scan_photo(
        filer,
        openai_client,
        DocumentType.CREDIT_REPORT,
        reply={"tradelines": tradelines, "confidence_score": 20},
    )

    assert doc["ocr_result"]["status"] == "failed"
    assert doc["ocr_result"]["failure_reason"] == "nothing_found"
    assert not DebtInfo.objects.filter(session=session).exists()


def test_one_bad_account_line_keeps_the_rest_of_the_report(filer, openai_client):
    _, session = filer
    report = {
        "tradelines": [
            {
                "creditor_name": " Chase Card Services ",
                "account_number": 41110000,
                "amount_owed": 2450.75,
                "account_type": "credit_card",
                "account_status": "open",
                "credit_limit": 5000,
            },
            {"creditor_name": "   ", "amount_owed": "300.00"},
            {"creditor_name": "Unreadable Bank", "amount_owed": "illegible"},
            {"creditor_name": "Midwest Auto Finance", "amount_owed": "12000.00"},
        ],
        "confidence_score": 70,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDIT_REPORT, reply=report)

    assert doc["ocr_result"]["status"] == "completed"
    debts = {d.creditor_name: d for d in DebtInfo.objects.filter(session=session)}
    assert set(debts) == {"Chase Card Services", "Midwest Auto Finance"}
    assert debts["Chase Card Services"].amount_owed == Decimal("2450.75")
    assert debts["Chase Card Services"].account_number == "41110000"
    assert debts["Midwest Auto Finance"].amount_owed == Decimal("12000.00")
    assert all(d.is_draft for d in debts.values())


def test_report_showing_only_paid_off_accounts_is_done_with_no_new_debts(filer, openai_client):
    _, session = filer
    report = {
        "tradelines": [
            {
                "creditor_name": "Discover",
                "amount_owed": "0",
                "account_type": "credit_card",
                "account_status": "closed",
            },
            {
                "creditor_name": "Navient",
                "amount_owed": 0,
                "account_type": "student_loan",
                "account_status": "closed",
            },
        ],
        "confidence_score": 85,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDIT_REPORT, reply=report)

    assert doc["ocr_result"]["status"] == "completed"
    assert doc["ocr_result"]["failure_reason"] == ""
    assert not DebtInfo.objects.filter(session=session).exists()


def test_reading_failure_shows_the_filer_a_reason_code_never_provider_text(filer, openai_client):
    provider_error = RuntimeError(
        "Error code: 403 - {'error': {'message': "
        "'Project proj_8sK2 does not have access to model gpt-4o'}}"
    )

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, error=provider_error)

    assert doc["ocr_result"] == {
        "status": "failed",
        "failure_reason": "processing_error",
        "confidence_scores": {},
        "overall_confidence": 0.0,
        "user_validated": False,
    }
    assert "proj_8sK2" not in json.dumps(doc)
    # error_message is for operations and keeps only the exception's class (spec §4.7).
    assert OCRResult.objects.get(document_id=doc["id"]).error_message == "RuntimeError"


def test_document_api_never_returns_what_was_read_from_the_file(filer, openai_client):
    bill = {
        "creditor_name": "Lakeshore Medical Group",
        "account_number": "5521-0098-7713",
        "amount_owed": "410.00",
        "creditor_type": "medical",
        "confidence_score": 90,
    }

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, reply=bill)

    assert doc["ocr_result"]["status"] == "completed"
    assert "extracted_data" not in doc["ocr_result"]
    assert "5521-0098-7713" not in json.dumps(doc)


def test_scan_records_the_provider_that_read_it(filer, openai_client):
    bill = {"creditor_name": "ComEd", "amount_owed": "96.12", "creditor_type": "utility"}

    doc = scan_photo(filer, openai_client, DocumentType.CREDITOR_BILL, reply=bill)

    assert OCRResult.objects.get(document_id=doc["id"]).ocr_provider == "openai"
```

The assembled file (Task 5's module, Task 7's test, these imports and this block) was checked with ruff 0.8.5 (`All checks passed!`) and black 24.10.0 at line length 100 (`1 file would be left unchanged.`).

Edit `backend/apps/documents/tests/test_draft_debt.py` (unit tests from spec §8, "Negative or non-numeric balances are not recorded"). Replace lines 1-3:

```python
import pytest

from apps.districts.models import District
```

with:

```python
from decimal import Decimal

import pytest

from apps.districts.models import District
```

Then insert the block below between `test_non_creditor_bill_raises` (it ends with `creator.create_from_result(result, session, uploaded_doc)`, line 88 before the edit) and `class TestDraftDebtCreatorCreditReport:`. Keep two blank lines on each side.

```python
def _scanned_bill(amount_owed) -> ExtractionResult:
    return ExtractionResult(
        fields={
            "creditor_name": "Lakeshore Medical Group",
            "amount_owed": amount_owed,
            "creditor_type": "medical",
        },
        confidence={"overall": 70},
        detected_type=DocumentType.CREDITOR_BILL,
    )


def test_readable_balance_is_recorded_to_the_cent(db, session, uploaded_doc):
    debt = DraftDebtCreator().create_from_result(_scanned_bill("2450.75"), session, uploaded_doc)

    debt.refresh_from_db()
    assert debt.amount_owed == Decimal("2450.75")


@pytest.mark.parametrize(
    "scanned_balance",
    ["-250.00", "about $1,200", "NaN", "Infinity", "1e12", None],
)
def test_negative_or_non_numeric_balance_is_not_recorded(
    db, session, uploaded_doc, scanned_balance
):
    """A balance the filer never owed must not reach the schedules, and an amount
    DecimalField(12, 2) cannot render would 500 every read of the filer's session."""
    debt = DraftDebtCreator().create_from_result(
        _scanned_bill(scanned_balance), session, uploaded_doc
    )

    debt.refresh_from_db()
    assert debt.amount_owed == Decimal("0")
```

Append this method inside `class TestAggregateIngestionService` in `backend/apps/documents/tests/test_aggregator.py`, after `test_captures_employer_name_from_most_recent_stub` (whose last line, line 99, is `self.assertEqual(agg.value, "New Job")`). Add one blank line before it and indent it four spaces, like its siblings. The file already imports `json`, `Decimal`, `get_user_model`, `District`, `DocumentType`, `OCRResult`, `OCRStatus`, `UploadedDocument`, `AggregateIngestionService` and `IntakeSession`.

```python
    def test_unusable_pay_stub_is_logged_without_its_pay_figures(self):
        """Pay figures are the filer's private data; the log names only what went wrong."""
        user = get_user_model().objects.create_user("logtest", "log@test.com", "pass")
        district = District.objects.create(
            name="ILND3", code="ILND3", state="IL", filing_fee_chapter_7=Decimal("338.00")
        )
        session = IntakeSession.objects.create(user=user, district=district)
        doc = UploadedDocument.objects.create(
            session=session,
            uploaded_by=user,
            document_type=DocumentType.PAY_STUB,
            file="stub.pdf",
            original_filename="stub.pdf",
            file_size=100,
            mime_type="application/pdf",
        )
        OCRResult.objects.create(
            document=doc,
            status=OCRStatus.COMPLETED,
            extracted_data=json.dumps(
                {
                    "employer_name": "Acme",
                    "gross_pay": "-4321.09",
                    "pay_period_start": "2026-01-01",
                    "pay_period_end": "2026-01-14",
                }
            ),
            overall_confidence=Decimal("0"),
        )

        with self.assertLogs("apps.documents.services.aggregator", level="WARNING") as logs:
            AggregateIngestionService.recalculate(session.id)

        output = "\n".join(logs.output)
        self.assertIn("ValidationError", output)
        self.assertNotIn("4321.09", output)
```

Edit `backend/apps/documents/tests/test_aggregator_hooks.py:49`. The hook test feeds `fields = {}` for a pay stub. Under this task's rules that is an unread pay stub (FAILED), so recalculation would rightly not run. Give it a readable stub so it keeps testing the hook. Replace:

```python
        mock_get_processor.return_value.process.return_value.fields = {}
```

with:

```python
        # A pay stub counts as read only with gross pay and both pay-period dates.
        mock_get_processor.return_value.process.return_value.fields = {
            "gross_pay": "1000.00",
            "pay_period_start": "2026-01-01",
            "pay_period_end": "2026-01-14",
        }
```

- [ ] **Step 2: Run them and confirm they fail**

From `/Volumes/Containers/DigniFi/backend`:

```bash
.venv/bin/python -m pytest apps/documents/tests/test_processing_outcomes.py apps/documents/tests/test_draft_debt.py apps/documents/tests/test_aggregator.py apps/documents/tests/test_aggregator_hooks.py -q
```

Expected: **19 failed**, everything else in those files passes. The count and failure messages below were verified against the pre-change code when these 14 tests lived in a separate file with an in-thread executor. After the move onto Task 5's fixtures they were checked only with ruff and black, so confirm the count here; a different count with the same reasons is a harness difference, not a reason to change Task 8's code.

- **The 14 new tests in `test_processing_outcomes.py` fail** (10 functions, 14 cases with the parametrized ones). Task 5's 3 tests and Task 7's 1 test in that file still pass.
  - Most fail with `assert 'completed' == 'failed'`: today's code marks every answered scan `completed`.
  - The rest fail with `KeyError: 'failure_reason'`.
  - The reason-code test fails on dict equality, because `extracted_data` and `error_message` are present and `failure_reason` is absent.
  - `test_scan_records_the_provider_that_read_it` fails on `'gemini' == 'openai'`.
  - The pay-stub test fails with `IngestedAggregate.DoesNotExist`.
- **4 cases of `test_negative_or_non_numeric_balance_is_not_recorded` fail:** `-250.00`, `NaN`, `Infinity` and `1e12`. The `about $1,200` and `None` cases already pass, because today's code maps them to 0.
- **`test_unusable_pay_stub_is_logged_without_its_pay_figures` fails** with `'ValidationError' not found`.
- **`test_aggregator_hooks.py` still passes** with the edited fields.

- [ ] **Step 3: Implement**

**3a. `backend/apps/documents/models.py`** (contract C2).

Insert a new class after `OCRStatus` (lines 44-51), so that the text between `OCRStatus` and `class UploadedDocument` becomes:

```python
    VALIDATED = "validated", "Validated by User"


class OCRFailureReason(models.TextChoices):
    """Why a FAILED scan failed, in terms the upload page can explain to the filer."""

    NOTHING_FOUND = "nothing_found", "Nothing found"
    PROCESSING_ERROR = "processing_error", "Processing error"


class UploadedDocument(models.Model):
```

In `OCRResult`, replace line 129-130:

```python
    status = models.CharField(max_length=20, choices=OCRStatus.choices, default=OCRStatus.PENDING)
    ocr_provider = models.CharField(max_length=50, default="gemini", help_text="OCR provider used")
```

with:

```python
    status = models.CharField(max_length=20, choices=OCRStatus.choices, default=OCRStatus.PENDING)
    failure_reason = models.CharField(
        max_length=32,
        choices=OCRFailureReason.choices,
        blank=True,
        default="",
        help_text="Why a failed scan failed; the only failure detail the API returns",
    )
    ocr_provider = models.CharField(max_length=50, default="gemini", help_text="OCR provider used")
```

Do **not** change the `ocr_provider` default. Doing so would add an `AlterField` to 0006, and the upload view now sets the field explicitly anyway.

Replace line 150:

```python
    error_message = models.TextField(blank=True, null=True)
```

with:

```python
    # Operations only: exception class names and finish_reason, never model output.
    # The documents API does not return it.
    error_message = models.TextField(blank=True, null=True)
```

**3b. Create `backend/apps/documents/migrations/0006_ocrresult_failure_reason.py`.** This content is exactly what `makemigrations documents --name ocrresult_failure_reason` produced for the model above. Only the header timestamp may differ.

```python
# Generated by Django 5.0.14 on 2026-10-10 00:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0005_alter_ocrresult_extracted_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="ocrresult",
            name="failure_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("nothing_found", "Nothing found"),
                    ("processing_error", "Processing error"),
                ],
                default="",
                help_text="Why a failed scan failed; the only failure detail the API returns",
                max_length=32,
            ),
        ),
    ]
```

The `intake` app already has an unrelated `0006`. This migration is `documents.0006`.

**3c. Replace all of `backend/apps/documents/schemas/credit_report.py`.** This makes each account line validate on its own, makes type and status optional, coerces numbers to strings, strips names and bounds the amount.

```python
"""Credit report extraction schema — one tradeline per account."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .base import BaseExtractionSchema


class TradelineItem(BaseModel):
    """A single account line from a credit report."""

    # Models return account numbers as JSON numbers and pad names with spaces.
    model_config = ConfigDict(coerce_numbers_to_str=True, str_strip_whitespace=True)

    creditor_name: str = Field(min_length=1)
    account_number: str | None = None
    # DebtInfo.amount_owed is DecimalField(12, 2) on read; a wider value 500s the session.
    amount_owed: Decimal = Field(ge=0, le=Decimal("9999999999.99"))
    # credit_card | auto_loan | student_loan | mortgage | medical | personal_loan | other
    account_type: str | None = None
    # open | closed | charged_off | in_collections | delinquent
    account_status: str | None = None
    credit_limit: Decimal | None = None


class CreditReportExtraction(BaseExtractionSchema):
    """Extraction schema for credit reports — a list of tradelines."""

    confidence_score: int = Field(default=0, ge=0, le=100)
    tradelines: list[TradelineItem] = Field(default_factory=list)

    @field_validator("tradelines", mode="before")
    @classmethod
    def keep_readable_tradelines(cls, value):
        """Validate each account on its own, so one unreadable line keeps the rest."""
        if not isinstance(value, list):
            return []
        readable = []
        for line in value:
            try:
                readable.append(TradelineItem.model_validate(line))
            except ValidationError:
                continue
        return readable
```

A `null` or missing `tradelines` becomes `[]`, which counts as "no readable accounts" and gives `nothing_found`, not `processing_error`. The existing tests in `test_draft_debt.py` pass `TradelineItem` instances, and `model_validate` returns those unchanged.

**3d. `backend/apps/documents/schemas/paystub.py`.** Replace line 18:

```python
    employer_name: str | None = Field(default=None, description="Employer or company name")
```

with:

```python
    # The processor pops confidence_score before storing extracted_data, so the stored
    # pay stub never carries one; without a default no real pay stub would validate.
    confidence_score: int = Field(default=0, ge=0, le=100)
    employer_name: str | None = Field(default=None, description="Employer or company name")
```

**3e. Replace all of `backend/apps/documents/services/draft_debt.py`.** This makes it None-safe and bounds the amounts.

```python
from decimal import Decimal, InvalidOperation

from apps.documents.models import DocumentType, UploadedDocument
from apps.documents.services.processor import ExtractionResult
from apps.intake.models import DebtInfo, IntakeSession

_VALID_DEBT_TYPES = {c[0] for c in DebtInfo.DEBT_TYPE_CHOICES}

# DebtInfo.amount_owed is read back through DecimalField(max_digits=12, decimal_places=2),
# which raises on NaN, Infinity or a 13th digit and would 500 every read of the session.
_MAX_AMOUNT = Decimal("1e10")
_CENTS = Decimal("0.01")


def _bounded_amount(value: object) -> Decimal:
    """The amount in cents, or 0 when it is not a number, negative, non-finite or >= 1e10."""
    try:
        amount = Decimal(str(value)).quantize(_CENTS)
    except InvalidOperation:  # not a number, infinite, or too many digits to round
        return Decimal("0")
    if amount.is_nan() or amount.is_signed() or amount >= _MAX_AMOUNT:
        return Decimal("0")
    return amount


class DraftDebtCreator:
    def create_from_result(
        self,
        result: ExtractionResult,
        session: IntakeSession,
        source_document: UploadedDocument,
    ) -> DebtInfo | None:
        """Create a draft debt from a scanned bill; None when the bill names no creditor.

        A bill with a creditor but no readable balance still becomes a draft, with
        amount 0, for the filer to complete in the Amounts Owed step.
        """
        if result.detected_type != DocumentType.CREDITOR_BILL:
            raise ValueError(
                f"DraftDebtCreator only handles CREDITOR_BILL, got {result.detected_type}"
            )

        fields = result.fields
        creditor_name = fields.get("creditor_name")
        creditor_name = creditor_name.strip() if isinstance(creditor_name, str) else ""
        if not creditor_name:
            return None

        debt_type = fields.get("creditor_type", "other")
        if debt_type not in _VALID_DEBT_TYPES:
            debt_type = "other"

        return DebtInfo.objects.create(
            session=session,
            creditor_name=creditor_name[:255],
            debt_type=debt_type,
            account_number=str(fields.get("account_number") or ""),
            amount_owed=_bounded_amount(fields.get("amount_owed")),
            data_source="uploaded_document",
            is_draft=True,
            source_document=source_document,
        )

    def create_from_credit_report(
        self,
        result: "CreditReportExtraction",  # noqa: F821
        session: IntakeSession,
        source_document: UploadedDocument,
    ) -> list[DebtInfo]:
        """Create draft DebtInfo records from each non-zero tradeline."""
        created = []
        for tradeline in result.tradelines:
            if tradeline.amount_owed == 0:
                continue
            debt = DebtInfo.objects.create(
                session=session,
                source_document=source_document,
                is_draft=True,
                creditor_name=tradeline.creditor_name[:255],
                account_number=tradeline.account_number or "",
                amount_owed=_bounded_amount(tradeline.amount_owed),
                debt_type=self._map_account_type(tradeline.account_type),
                is_secured=tradeline.account_type in ("auto_loan", "mortgage"),
                is_in_collections=tradeline.account_status in ("in_collections", "charged_off"),
                priority_classification=self._priority_for_type(tradeline.account_type),
                data_source="credit_report",
            )
            created.append(debt)
        return created

    @staticmethod
    def _map_account_type(account_type: str | None) -> str:
        mapping = {
            "credit_card": "credit_card",
            "auto_loan": "auto_loan",
            "student_loan": "student_loan",
            "mortgage": "mortgage",
            "medical": "medical",
            "personal_loan": "personal_loan",
        }
        return mapping.get(account_type, "other")

    @staticmethod
    def _priority_for_type(account_type: str | None) -> str:
        return "secured" if account_type in ("auto_loan", "mortgage") else "unsecured"
```

These edge cases were verified: `None`, `"NaN"`, `"sNaN"`, `"Infinity"`, `float("inf")`, `"-250.00"`, `"-0.001"`, `"1e12"`, `"1e30"`, `"9999999999.995"`, `"$1200"`, `"1,234.56"`, `True` and `[1]` all become 0. `"1200.5"` becomes `1200.50`, and `"9999999999.99"` is kept.

**3f. `backend/apps/documents/services/aggregator.py`.** This logs the exception class, not the pay-stub values. Replace line 66:

```python
                logger.warning("Skipping invalid paystub OCRResult %s: %s", ocr.id, e)
```

with:

```python
                # The exception text quotes the pay-stub values; log only its class.
                logger.warning(
                    "Skipping invalid paystub OCRResult %s (%s)", ocr.id, type(e).__name__
                )
```

**3g. `backend/apps/documents/services/processor.py`, in `DocumentProcessor._parse_result`.** An all-null reply carries `"confidence_score": null`. `int(None)` raises a `TypeError` outside the caught `(json.JSONDecodeError, ValueError)`, so a cover page would wrongly land as `processing_error`. Task 7 rewrites this function's `except` branch and leaves this line. Replace only:

```python
            data = json.loads(clean)
            confidence_score = int(data.pop("confidence_score", 0))
            return ExtractionResult(
```

with:

```python
            data = json.loads(clean)
            # An all-null reply (a cover page) carries "confidence_score": null.
            confidence_score = int(data.pop("confidence_score", None) or 0)
            return ExtractionResult(
```

**3g (continued). `processor.py`: keep provider text out of `error_message`** (spec §4.7: it holds only exception class names and `finish_reason`). Today `process()` stores `str(exc)` for any exception, so an OpenAI 403 body (project id, model-access text) lands in `OCRResult.error_message`. Task 7 left this `except` unchanged at commit 8; this task narrows it.

Replace the import line:

```python
from apps.documents.services.providers.base import BaseOCRProvider
```

with:

```python
from apps.documents.services.providers.base import BaseOCRProvider, EmptyModelReply
```

In `DocumentProcessor.process`, replace (the 8-space-indented `except`; the 16-space one inside `_process_pdf` is a different block):

```python
        except Exception as exc:
            return ExtractionResult(error=str(exc))
```

with:

```python
        except Exception as exc:
            # error_message is operations-only (spec §4.7). EmptyModelReply's own text names
            # finish_reason and never quotes the model; any other exception keeps only its
            # class name, because a provider's error text can carry account or project details.
            return ExtractionResult(
                error=str(exc) if isinstance(exc, EmptyModelReply) else type(exc).__name__
            )
```

Task 7's `test_an_empty_reply_is_retried_once_and_its_cause_is_recorded` (`"finish_reason=length" in ocr.error_message`) and `TestEmptyReplies` still pass, and Step 1's reason-code test now sees `error_message == "RuntimeError"`. This hunk was checked with black 24.10.0 at line length 100.

**3h. `backend/apps/documents/views.py`.**

(1) Imports, lines 5-18. Replace:

```python
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
```

with:

```python
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from pydantic import ValidationError
from rest_framework import status
```

Then replace:

```python
from apps.documents.models import DocumentType, OCRResult, OCRStatus, UploadedDocument
from apps.documents.services.aggregator import AggregateIngestionService
from apps.documents.services.draft_debt import DraftDebtCreator
from apps.documents.services.processor import DocumentProcessor
from apps.documents.services.providers.base import BaseOCRProvider
```

with:

```python
from apps.documents.models import (
    DocumentType,
    OCRFailureReason,
    OCRResult,
    OCRStatus,
    UploadedDocument,
)
from apps.documents.schemas.credit_report import CreditReportExtraction
from apps.documents.schemas.paystub import PayStubExtraction
from apps.documents.services.aggregator import AggregateIngestionService
from apps.documents.services.draft_debt import DraftDebtCreator
from apps.documents.services.processor import DocumentProcessor, ExtractionResult
from apps.documents.services.providers.base import BaseOCRProvider
```

The local `from apps.documents.schemas.credit_report import CreditReportExtraction` inside `_run_processing` goes away with the block replaced in (3) below. `pydantic` is already a dependency (`schemas/` uses it). `views.py` imports no DRF `ValidationError`, so the name does not clash.

(2) Insert this function directly above `def _run_processing(doc_id: int) -> None:` (line 46), followed by two blank lines:

```python
def _record_findings(doc: UploadedDocument, result: ExtractionResult) -> bool:
    """Store what a scan found. False when it found nothing the filer can use.

    Empty means unread, judged per type: a bill needs a creditor name, a pay stub
    must pass PayStubExtraction (gross pay and both pay-period dates required), the
    check the income aggregate applies, and a credit report needs one readable
    account. Other types are not judged and count as read.
    """
    if doc.document_type == DocumentType.CREDITOR_BILL:
        return DraftDebtCreator().create_from_result(result, doc.session, doc) is not None
    if doc.document_type == DocumentType.PAY_STUB:
        try:
            PayStubExtraction.model_validate(result.fields)
        except ValidationError:
            return False
        return True
    if doc.document_type == DocumentType.CREDIT_REPORT:
        report = CreditReportExtraction.model_validate(result.fields)
        if not report.tradelines:
            return False
        # A report whose accounts are all paid off is read, and adds no debts.
        DraftDebtCreator().create_from_credit_report(report, doc.session, doc)
        return True
    return True
```

(3) In `_run_processing`, replace lines 57-84:

```python
        if result.error:
            ocr.status = OCRStatus.FAILED
            ocr.error_message = result.error
            ocr.extracted_data = "{}"
            ocr.overall_confidence = 0
        else:
            ocr.status = OCRStatus.COMPLETED
            ocr.extracted_data = json.dumps(result.fields)
            ocr.confidence_scores = result.confidence
            ocr.overall_confidence = result.confidence.get("overall", 0)

            if doc.document_type == DocumentType.CREDITOR_BILL:
                try:
                    DraftDebtCreator().create_from_result(result, doc.session, doc)
                except Exception as exc:
                    logger.warning("DraftDebtCreator failed for doc %s: %s", doc_id, exc)
            elif doc.document_type == DocumentType.CREDIT_REPORT:
                try:
                    from apps.documents.schemas.credit_report import CreditReportExtraction

                    schema_obj = CreditReportExtraction.model_validate(result.fields)
                    DraftDebtCreator().create_from_credit_report(schema_obj, doc.session, doc)
                except Exception as exc:
                    logger.warning(
                        "DraftDebtCreator (credit report) failed for doc %s: %s", doc_id, exc
                    )

        ocr.save()
```

with:

```python
        if result.error:
            ocr.status = OCRStatus.FAILED
            ocr.failure_reason = OCRFailureReason.PROCESSING_ERROR
            ocr.error_message = result.error
            ocr.extracted_data = "{}"
            ocr.overall_confidence = 0
        else:
            ocr.extracted_data = json.dumps(result.fields)
            ocr.confidence_scores = result.confidence
            ocr.overall_confidence = result.confidence.get("overall", 0)
            if _record_findings(doc, result):
                ocr.status = OCRStatus.COMPLETED
            else:
                ocr.status = OCRStatus.FAILED
                ocr.failure_reason = OCRFailureReason.NOTHING_FOUND

        ocr.save()
```

The two `try/except Exception: logger.warning(...)` wrappers are removed on purpose. They turned a crash in draft creation into a "Done" with nothing created, which is DIG-7 itself. An unexpected error now reaches the outer handler and becomes `failed` / `processing_error`.

(4) In the outer handler, replace lines 95-97:

```python
            OCRResult.objects.filter(document_id=doc_id).update(
                status=OCRStatus.FAILED, error_message=str(exc)
            )
```

with:

```python
            # The class name only: a pydantic error's text quotes the document's values.
            OCRResult.objects.filter(document_id=doc_id).update(
                status=OCRStatus.FAILED,
                failure_reason=OCRFailureReason.PROCESSING_ERROR,
                error_message=type(exc).__name__,
            )
```

(5) In `upload`, the `OCRResult.objects.create(...)` call (lines 138-144) records the provider that reads the file. Replace:

```python
        OCRResult.objects.create(
            document=doc,
            status=OCRStatus.PENDING,
            extracted_data="{}",
```

with:

```python
        OCRResult.objects.create(
            document=doc,
            status=OCRStatus.PENDING,
            ocr_provider=settings.OCR_PROVIDER.lower(),
            extracted_data="{}",
```

`.lower()` matches what `_get_processor()` branches on.

(6) Replace `_serialize_ocr` (lines 215-223):

```python
def _serialize_ocr(ocr: OCRResult) -> dict:
    return {
        "status": ocr.status,
        "extracted_data": json.loads(ocr.extracted_data or "{}"),
        "confidence_scores": ocr.confidence_scores,
        "overall_confidence": float(ocr.overall_confidence),
        "user_validated": ocr.user_validated,
        "error_message": ocr.error_message,
    }
```

with:

```python
def _serialize_ocr(ocr: OCRResult) -> dict:
    # Never error_message (operations text) or extracted_data (decrypted PII): the
    # upload page reads only status and failure_reason.
    return {
        "status": ocr.status,
        "failure_reason": ocr.failure_reason,
        "confidence_scores": ocr.confidence_scores,
        "overall_confidence": float(ocr.overall_confidence),
        "user_validated": ocr.user_validated,
    }
```

`json` is still used by `_run_processing` and `validate`, so keep the import.

**3i. `frontend/src/types/api.ts`** (contract C4). The API shape changes in this commit, so the type changes with it; front-end/back-end enum drift is silent otherwise. Nothing in `src/` or `e2e/` reads `extracted_data` or `error_message`; this was checked by grep. Replace lines 333-342:

```ts
export type OCRStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'validated';

export interface OCRResult {
  status: OCRStatus;
  extracted_data: Record<string, unknown>;
  confidence_scores: Record<string, number>;
  overall_confidence: number;
  user_validated: boolean;
  error_message: string | null;
}
```

with:

```ts
export type OCRStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'validated';

/** Why a failed scan failed. Blank on every other status, and on rows from before 0006. */
export type OCRFailureReason = 'nothing_found' | 'processing_error';

export interface OCRResult {
  status: OCRStatus;
  failure_reason: OCRFailureReason | '';
  confidence_scores: Record<string, number>;
  overall_confidence: number;
  user_validated: boolean;
}
```

- [ ] **Step 4: Run tests and confirm they pass**

From `/Volumes/Containers/DigniFi/backend`:

```bash
.venv/bin/python -m pytest apps/documents/tests/test_processing_outcomes.py apps/documents/tests/test_draft_debt.py apps/documents/tests/test_aggregator.py apps/documents/tests/test_aggregator_hooks.py apps/documents/tests/test_processor.py apps/documents/tests/test_openai_provider.py -q
.venv/bin/python -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q
.venv/bin/ruff check .
.venv/bin/black --line-length 100 --check apps/documents/models.py apps/documents/schemas/credit_report.py apps/documents/schemas/paystub.py apps/documents/services/draft_debt.py apps/documents/services/aggregator.py apps/documents/services/processor.py apps/documents/views.py apps/documents/tests/test_processing_outcomes.py apps/documents/tests/test_draft_debt.py apps/documents/tests/test_aggregator.py apps/documents/tests/test_aggregator_hooks.py
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
```

- **The first command passes in full.** `test_processing_outcomes.py` now holds 18 tests: Task 5's 3, Task 7's 1 and this task's 14 (counting parametrized cases).
- **The full suite passes with coverage ≥ 90.** In a scratch copy with these changes applied on top of a simulated Task 7 provider, the full suite gave 718 passed and 1 xfailed. The only deselected test was the pre-Task-7 `test_empty_completion_becomes_empty_string`, which Task 7 replaces.
- **Ruff prints `All checks passed!`, and black `11 files would be left unchanged.`** (`pyproject.toml` excludes `migrations/` from black.) Task 0 Step 3g installed ruff 0.8.5 and black 24.10.0 into `backend/.venv`, the versions CI and the pre-commit hook pin.
- **`test_processor.py` and `test_openai_provider.py` still pass.** The `process()` change keeps `EmptyModelReply`'s text, so Task 7's `finish_reason=length` assertions hold.
- **makemigrations prints `No changes detected`.**
- **No stray media files.** `ls backend/media/documents` shows nothing new from these tests, because they write to `tmp_path`.

From `/Volumes/Containers/DigniFi/frontend`:

```bash
npx tsc -b
npm run lint
npx vitest run
```

`tsc` and eslint should report no errors, and vitest should pass unchanged, because no component or MSW handler reads the removed fields.

If a test from an earlier task now fails, fix the test's input, not Task 8's code. The likely failures are in Task 5's `test_processing_outcomes.py` or Task 7's empty-reply tests:

- **Bills and pay stubs.** Task 8 changes what an answered scan produces. A canned bill reply with no `creditor_name` is now `failed` / `nothing_found`, and so is a pay stub that does not pass `PayStubExtraction` (it needs `gross_pay` > 0 plus `pay_period_start` and `pay_period_end`). Make the reply name a creditor or carry a valid pay stub.
- **Credit reports.** A report with no readable tradeline is now `failed` / `nothing_found`.
- **Error messages.** A test that read `error_message` from the API must read it from the `OCRResult` row (`OCRResult.objects.get(document_id=...).error_message`). The API no longer returns it.

- [ ] **Step 5: Update CLAUDE.md gotchas**

In the root `CLAUDE.md`, append these three bullets to the end of the `## Gotchas (things agents get wrong)` list, directly above the blank line that precedes `## Architecture (quick)`. They are new facts, and no existing gotcha becomes false.

```markdown
- **An empty scan is FAILED, not done** — `documents/views._record_findings` judges each type: a bill needs a creditor name, a pay stub must pass `PayStubExtraction`, the check the income aggregate applies (gross pay + both pay-period dates required; an invalid optional field such as a negative `net_pay` also fails it), a credit report needs one readable tradeline. Otherwise `OCRResult.status="failed"`, `failure_reason="nothing_found"`; any exception is `processing_error`. A bill with a creditor but no readable balance is `completed` with a $0 draft; a report of only $0 accounts is `completed` with no debts. Other document types are not judged.
- **The documents API never returns `error_message` or `extracted_data`** — `_serialize_ocr` returns `status`, `failure_reason`, `confidence_scores`, `overall_confidence`, `user_validated`. `error_message` is operations-only (exception class, `finish_reason`); read it in a Django shell.
- **Scanned amounts are bounded** — `draft_debt._bounded_amount` stores a non-numeric, negative, non-finite or ≥1e10 balance as 0, and `TradelineItem.amount_owed` has `le=9999999999.99`: a wider value makes `DecimalField(12,2)` raise on every read of the session.
```

- [ ] **Step 6: Commit**

From `/Volumes/Containers/DigniFi`:

```bash
git add backend/apps/documents/models.py \
  backend/apps/documents/migrations/0006_ocrresult_failure_reason.py \
  backend/apps/documents/schemas/credit_report.py \
  backend/apps/documents/schemas/paystub.py \
  backend/apps/documents/services/draft_debt.py \
  backend/apps/documents/services/aggregator.py \
  backend/apps/documents/services/processor.py \
  backend/apps/documents/views.py \
  backend/apps/documents/tests/test_processing_outcomes.py \
  backend/apps/documents/tests/test_draft_debt.py \
  backend/apps/documents/tests/test_aggregator.py \
  backend/apps/documents/tests/test_aggregator_hooks.py \
  frontend/src/types/api.ts
git diff CLAUDE.md
```

`git diff CLAUDE.md` must show only the three bullets added in Step 5. Tasks 1–2 committed every other `CLAUDE.md` change, and Tasks 3–7 committed their own. If it shows any other hunk, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it. Then run `git add CLAUDE.md`.

Then check `git diff --cached --name-only`. It must list exactly the 14 paths above, with no `.serena/`, `DESIGN.md`, `assets/`, `.impeccable` or `README.md`. Then commit:

```bash
git commit -m "fix(documents): report a scan that found nothing as failed, not done"
```

If pre-commit reformats a file (black, ruff or prettier), the commit aborts. Re-run the same `git add` of those files (and `git add CLAUDE.md`) and the same `git commit` command. Do not add any `Co-Authored-By` or other trailer.

---

### Task 9: Ask the model for each account on a credit report  (Commit #10 in spec §9)

Spec §4.7, "Credit-report prompt hint" (DIG-3). `_FIELD_HINTS` in `prompts/image_extraction.py` has entries only for `CREDITOR_BILL` and `PAY_STUB`. A credit report therefore falls back to `_DEFAULT_FIELDS` ("all visible fields as key-value pairs"), so the model is never asked for `tradelines` and no account can reach the Amounts Owed step. This task adds the hint.

**Does the text prompt need the same hint? No separate change is needed.** `prompts/text_extraction.py:1` does `from .image_extraction import _DEFAULT_FIELDS, _FIELD_HINTS`, and `build_text_extraction_prompt` looks the hint up in that same dict. Adding the entry once covers the vision path (scans) and the text path (text-layer PDFs). The test below is parametrized over both builders to prove it.

**Files:**
- Modify: `backend/apps/documents/services/providers/prompts/image_extraction.py:10-16` (add a `CREDIT_REPORT` entry after the `PAY_STUB` entry)
- Modify: `CLAUDE.md` (Gotchas list)
- Test: `backend/apps/documents/tests/test_prompts.py:1-3` (imports) and append after `:27`

**Interfaces:**
- Consumes: from Task 8, `apps.documents.schemas.credit_report.TradelineItem`, whose `model_fields` are `creditor_name`, `account_number`, `amount_owed`, `account_type`, `account_status` and `credit_limit`. Also `DraftDebtCreator.create_from_credit_report`, which reads `account_type in ("auto_loan", "mortgage")` and `account_status in ("in_collections", "charged_off")`. And `CreditReportExtraction`'s per-line validation, which drops any line the model returns with a `null` balance or name.
- Produces: `_FIELD_HINTS[DocumentType.CREDIT_REPORT]`, used by both `build_image_extraction_prompt(DocumentType.CREDIT_REPORT)` and `build_text_extraction_prompt(DocumentType.CREDIT_REPORT, text)`.

- [ ] **Step 1: Write the failing test**

In `backend/apps/documents/tests/test_prompts.py`, replace line 1:

```python
from apps.documents.models import DocumentType
```

with:

```python
import pytest

from apps.documents.models import DocumentType
from apps.documents.schemas.credit_report import TradelineItem
```

Leave the two existing `from apps.documents.services.providers.prompts...` import lines (lines 2-3) where they are, directly below. Then append at the end of the file, after `test_text_prompt_requests_json`, with two blank lines before it:

```python
@pytest.mark.parametrize(
    "build_prompt",
    [
        build_image_extraction_prompt,
        lambda doc_type: build_text_extraction_prompt(doc_type, "EQUIFAX CREDIT FILE ..."),
    ],
    ids=["scanned", "text-layer"],
)
def test_credit_report_prompt_asks_for_every_field_the_importer_needs(build_prompt):
    """Without the hint the model is asked for "all visible fields" and never returns
    tradelines, so no account on a credit report reaches the Amounts Owed step."""
    prompt = build_prompt(DocumentType.CREDIT_REPORT)

    assert "tradelines" in prompt
    for field in TradelineItem.model_fields:
        assert field in prompt
    # DraftDebtCreator marks a debt secured or in collections only on these exact values.
    for value in ("auto_loan", "mortgage", "in_collections", "charged_off"):
        assert value in prompt
```

- [ ] **Step 2: Run it and confirm it fails**

From `/Volumes/Containers/DigniFi/backend`:

```bash
.venv/bin/python -m pytest apps/documents/tests/test_prompts.py -q
```

Expected: `2 failed, 4 passed`. Both `test_credit_report_prompt_asks_for_every_field_the_importer_needs[scanned]` and `[text-layer]` fail with `AssertionError: assert 'tradelines' in 'You are a document data extraction assistant ...'`, because the prompt contains "all visible fields as key-value pairs".

- [ ] **Step 3: Implement**

In `backend/apps/documents/services/providers/prompts/image_extraction.py`, replace the end of `_FIELD_HINTS` (lines 13-16):

```python
        "ytd_gross (decimal string or null), net_pay (decimal string or null), "
        "deductions_total (decimal string or null)"
    ),
}
```

with:

```python
        "ytd_gross (decimal string or null), net_pay (decimal string or null), "
        "deductions_total (decimal string or null)"
    ),
    # Keys match TradelineItem (schemas/credit_report.py), which the importer validates.
    DocumentType.CREDIT_REPORT: (
        "tradelines (a list with one object per account on the report, each with: "
        "creditor_name (string), account_number (string or null), "
        "amount_owed (the current balance as a plain number such as 1234.56, without "
        "a dollar sign or commas; 0 for a credit balance or a paid-off account), "
        "account_type (one of: credit_card, auto_loan, student_loan, mortgage, medical, "
        "personal_loan, other), account_status (one of: open, closed, charged_off, "
        "in_collections, delinquent), credit_limit (plain number or null); "
        "leave out any account whose creditor name or balance you cannot read)"
    ),
}
```

The resulting scanned-report prompt, as verified, is:

> You are a document data extraction assistant for a legal filing platform. Extract the following fields from this credit report image. Return ONLY a valid JSON object with these fields: tradelines (a list with one object per account on the report, each with: creditor_name (string), account_number (string or null), amount_owed (the current balance as a plain number such as 1234.56, without a dollar sign or commas; 0 for a credit balance or a paid-off account), account_type (one of: credit_card, auto_loan, student_loan, mortgage, medical, personal_loan, other), account_status (one of: open, closed, charged_off, in_collections, delinquent), credit_limit (plain number or null); leave out any account whose creditor name or balance you cannot read), confidence_score (integer 0-100 reflecting your extraction confidence). If a field is not visible or not applicable, set it to null. Do not include any text outside the JSON object.

The prompt still contains "JSON", which OpenAI's `response_format={"type": "json_object"}` requires. Do not edit `text_extraction.py`.

- [ ] **Step 4: Run tests and confirm they pass**

From `/Volumes/Containers/DigniFi/backend`:

```bash
.venv/bin/python -m pytest apps/documents/tests/test_prompts.py -q
.venv/bin/python -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q
.venv/bin/ruff check .
.venv/bin/black --line-length 100 --check apps/documents/services/providers/prompts/image_extraction.py apps/documents/tests/test_prompts.py
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
```

- **The prompt tests report `6 passed`.**
- **The full suite passes with coverage ≥ 90.**
- **Ruff prints `All checks passed!`, and black `2 files would be left unchanged.`** Task 0 Step 3g installed ruff 0.8.5 and black 24.10.0 into `backend/.venv`, the versions CI and the pre-commit hook pin.
- **makemigrations prints `No changes detected`.**

- [ ] **Step 5: Update CLAUDE.md gotchas**

In the root `CLAUDE.md`, append this bullet to the end of the `## Gotchas (things agents get wrong)` list, directly above the blank line that precedes `## Architecture (quick)` and after the three bullets from Task 8:

```markdown
- **Prompt hints are per type and shared** — `_FIELD_HINTS` in `documents/services/providers/prompts/image_extraction.py` feeds both the vision and the text prompt (`text_extraction.py` imports it). A type with no hint is asked for "all visible fields as key-value pairs" and never returns the keys its importer reads; the `CREDIT_REPORT` hint's keys must stay in step with `TradelineItem`, and `test_prompts.py` checks that they do.
```

- [ ] **Step 6: Commit**

From `/Volumes/Containers/DigniFi`:

```bash
git add backend/apps/documents/services/providers/prompts/image_extraction.py \
  backend/apps/documents/tests/test_prompts.py
git diff CLAUDE.md
```

`git diff CLAUDE.md` must show only the one bullet added in Step 5. Tasks 1–2 committed every other `CLAUDE.md` change, and Tasks 3–8 committed their own. If it shows any other hunk, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it. Then run `git add CLAUDE.md`.

Then check `git diff --cached --name-only`. It must list exactly those 3 paths. Then commit:

```bash
git commit -m "fix(documents): ask the model for each account on a credit report"
```

If pre-commit reformats a file, the commit aborts. Re-run the same `git add` lines and the same `git commit` command. Do not add any `Co-Authored-By` or other trailer.

---

### Task 10: Show filers the amounts they already entered  (Commit #11 in spec §9)

**Files:**
- Modify: `backend/apps/intake/serializers.py:156-159`. `AssetInfoSerializer.current_value` / `amount_owed`. These lines do not move in Task 3, which only inserts code after line 221.
- Modify: `backend/apps/intake/serializers.py:191`. `DebtInfoSerializer.amount_owed`.
- Modify: `backend/apps/documents/views.py:7` (import).
- Modify: `backend/apps/documents/views.py:180-192`, inside `def validate(self, request, pk=None):` at line 172 of today's working tree. Tasks 1 and 8 edit `_get_processor`/`_run_processing` above it, so locate the hunk by its text, not its line number.
- Modify: `frontend/src/utils/parseAmount.ts:17`. Append after `parseAmount`.
- Modify: `frontend/src/pages/IntakeWizard.tsx:13` (import).
- Modify: `frontend/src/pages/IntakeWizard.tsx:48`. Constants after `WIZARD_STEPS`.
- Modify: `frontend/src/pages/IntakeWizard.tsx`, the assets/debts lines inside Task 4's `.then((fresh) => …)` block (`if (fresh.assets) setAssetsData(fresh.assets);` and `if (fresh.debts) setDebtsData(fresh.debts);`). Task 4 (commit 5) moved them there from today's lines 88–89; see Step 3d.
- Create: `backend/apps/intake/tests/test_readable_amounts.py`
- Modify: `backend/apps/documents/tests/test_views.py:1-2,10` (imports) and append at the end of the file.
- Modify: `frontend/src/utils/__tests__/parseAmount.test.ts:2` (import) and append at the end of the file.
- Modify: `frontend/src/pages/__tests__/IntakeWizard.test.tsx`. Append at the end of the file.
- Modify: `CLAUDE.md`. Add one gotcha after Task 3's `**Nested debts and assets save by id**` line.
- Test: the four test files above.

**Interfaces:**
- Consumes:
  - Spec §4.3 (DIG-2). Debt `amount_owed` and asset `current_value`/`amount_owed` are write-only today, so a returning filer sees empty amount boxes.
  - **Ordering precondition: Task 3 (commit 4) must be in.** This commit uses its upsert by id (contract C11, `_save_rows_by_id`). Readable amounts make hydrated debts valid, so autosave fires on Amounts Owed about 2 s after arrival. Only upsert by id keeps `account_number` and scan links through that save.
  - **Ordering precondition: Task 8 (commit 9) must be in.** Its `DraftDebtCreator` maps non-finite, negative or ≥1e10 amounts to 0, so no upload can write an out-of-range draft. Bounds land before amounts become readable (spec §4.3).
  - **This task closes the last API write path,** `POST /api/documents/{id}/validate/`. Amounts already stored out of range are deploy gate §7.1 (DIG-58), not code. Each one would 500 every read of its session.
  - Task 4's wizard re-read: contract C7, `loadSession(sessionId: number): Promise<IntakeSession>`. Its success branch is where step state is filled.
  - The existing `parseAmount(value: string): number | undefined` (`frontend/src/utils/parseAmount.ts:12`).
- Produces:
  - **Contract C6** in `frontend/src/utils/parseAmount.ts`. Task 12 (commit 13) reuses `hydrateAmounts` for expenses with `EXPENSE_FIELDS`.
    - `export function decimalToNumber(value: unknown): number | undefined`: a finite number passes through; a string goes through `parseAmount` and then a finiteness check; anything else is `undefined`; never `NaN`.
    - `export function hydrateAmounts<T extends object>(row: T, keys: readonly string[]): T`: returns a copy, converts only the listed keys present in the row, never adds keys, and never mutates its input.
  - `ASSET_AMOUNT_FIELDS` / `DEBT_AMOUNT_FIELDS` module constants in `IntakeWizard.tsx`.
  - **API:** `GET /api/intake/sessions/{id}/`, `/api/intake/debts/{id}/` and `/api/intake/assets/{id}/` return the following to the owner as DRF decimal strings (`"1234.56"`): debt `amount_owed`, asset `current_value` and asset `amount_owed`.
  - **API:** `POST /api/documents/{id}/validate/` returns `400 {"amount_owed": [<DRF message>]}` for an `amount_owed` that fails `DecimalField(max_digits=12, decimal_places=2)`. It writes nothing in that case, and the draft debt receives the validated `Decimal`.

- [ ] **Step 1: Write the failing tests**

**1a.** Create `backend/apps/intake/tests/test_readable_amounts.py`:

```python
"""Filers can read back the amounts they entered (DIG-2).

Business intent: the wizard can only show, and safely re-save, an amount the API
returns. The session owner can read debt and asset amounts; the SSN and account
numbers stay write-only, and no one else can read any of it.
"""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import AssetInfo, DebtInfo, DebtorInfo, IntakeSession
from apps.users.models import User

SSN = "900123456"
CARD_NUMBER = "4111222233334444"
LOAN_NUMBER = "998877665544"


@pytest.fixture
def filer_session(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    user = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=user, district=district)
    DebtorInfo.objects.create(
        session=session,
        first_name="Jane",
        last_name="Doe",
        ssn=SSN,
        date_of_birth=date(1985, 6, 15),
        phone="3125551234",
        email="jane@example.com",
        street_address="123 Main St",
        city="Chicago",
        state="IL",
        zip_code="60601",
    )
    debt = DebtInfo.objects.create(
        session=session,
        creditor_name="Chase",
        debt_type="credit_card",
        account_number=CARD_NUMBER,
        amount_owed=Decimal("1234.56"),
    )
    asset = AssetInfo.objects.create(
        session=session,
        asset_type="vehicle",
        description="2015 Honda Civic",
        current_value=Decimal("8000.00"),
        amount_owed=Decimal("3000.00"),
        account_number=LOAN_NUMBER,
    )
    return session, debt, asset


def _client_for(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_amounts_are_readable_while_ssn_and_account_numbers_stay_private(filer_session):
    session, debt, asset = filer_session
    client = _client_for(session.user)

    response = client.get(f"/api/intake/sessions/{session.pk}/")

    assert response.status_code == 200
    [debt_row] = response.data["debts"]
    [asset_row] = response.data["assets"]
    assert debt_row["amount_owed"] == "1234.56"
    assert asset_row["current_value"] == "8000.00"
    assert asset_row["amount_owed"] == "3000.00"
    assert "ssn" not in response.data["debtor_info"]
    assert "account_number" not in debt_row
    assert "account_number" not in asset_row
    for secret in (SSN, CARD_NUMBER, LOAN_NUMBER):
        assert secret.encode() not in response.content

    debt_response = client.get(f"/api/intake/debts/{debt.pk}/")
    asset_response = client.get(f"/api/intake/assets/{asset.pk}/")
    assert debt_response.data["amount_owed"] == "1234.56"
    assert asset_response.data["current_value"] == "8000.00"
    assert CARD_NUMBER.encode() not in debt_response.content
    assert LOAN_NUMBER.encode() not in asset_response.content


def test_only_the_owner_can_read_amounts(filer_session):
    session, debt, asset = filer_session
    stranger = _client_for(User.objects.create_user(username="stranger", password="pw"))

    for url in (
        f"/api/intake/sessions/{session.pk}/",
        f"/api/intake/debts/{debt.pk}/",
        f"/api/intake/assets/{asset.pk}/",
    ):
        assert stranger.get(url).status_code == 404
    for url in ("/api/intake/sessions/", "/api/intake/debts/", "/api/intake/assets/"):
        response = stranger.get(url)
        assert response.status_code == 200
        assert b"1234.56" not in response.content
        assert b"8000.00" not in response.content

    assert APIClient().get(f"/api/intake/sessions/{session.pk}/").status_code == 401
```

**1b.** In `backend/apps/documents/tests/test_views.py`, add `from decimal import Decimal` to the imports. Lines 1–2 are today:

```python
import json
from unittest.mock import MagicMock, patch
```

and become:

```python
import json
from decimal import Decimal
from unittest.mock import MagicMock, patch
```

Then change line 10, `from apps.intake.models import IntakeSession`, to:

```python
from apps.intake.models import DebtInfo, IntakeSession
```

If an earlier task already changed that import line, add `DebtInfo` to whatever it now imports from `apps.intake.models`.

Then append at the end of the file. The tests reuse the file's existing `auth_client` and `session` fixtures:

```python


def _scanned_bill_with_draft(session, user):
    doc = UploadedDocument.objects.create(
        session=session,
        uploaded_by=user,
        document_type=DocumentType.CREDITOR_BILL,
        user_declared_type=DocumentType.CREDITOR_BILL,
        original_filename="bill.pdf",
        file_size=100,
        mime_type="application/pdf",
        file="documents/x.pdf",
    )
    ocr = OCRResult.objects.create(
        document=doc,
        status=OCRStatus.COMPLETED,
        extracted_data='{"creditor_name": "Chase"}',
        confidence_scores={},
        overall_confidence=80,
    )
    draft = DebtInfo.objects.create(
        session=session,
        creditor_name="Chase",
        debt_type="credit_card",
        amount_owed=Decimal("500.00"),
        is_draft=True,
        source_document=doc,
    )
    return doc, ocr, draft


@pytest.mark.parametrize("bad_amount", ["99999999999.99", "not a number"])
def test_a_correction_too_large_or_unreadable_is_refused_and_the_session_still_opens(
    db, auth_client, session, bad_amount
):
    """A stored amount wider than DecimalField(12, 2) would 500 every read of the
    session once amounts are readable (DIG-2), so validate refuses it before writing."""
    client, user = auth_client
    doc, ocr, draft = _scanned_bill_with_draft(session, user)

    response = client.post(
        f"/api/documents/{doc.id}/validate/",
        {"fields": {"amount_owed": bad_amount}},
        format="json",
    )

    assert response.status_code == 400
    assert "amount_owed" in response.json()
    draft.refresh_from_db()
    assert draft.amount_owed == Decimal("500.00")
    ocr.refresh_from_db()
    assert ocr.user_validated is False
    assert client.get(f"/api/intake/sessions/{session.id}/").status_code == 200


def test_a_corrected_amount_reaches_the_draft_debt(db, auth_client, session):
    client, user = auth_client
    doc, _, draft = _scanned_bill_with_draft(session, user)

    response = client.post(
        f"/api/documents/{doc.id}/validate/",
        {"fields": {"amount_owed": "650.00"}},
        format="json",
    )

    assert response.status_code == 200
    draft.refresh_from_db()
    assert draft.amount_owed == Decimal("650.00")
```

These tests assert nothing about the success body of `validate`, because Task 8 reshaped `_serialize_ocr`.

**1c.** In `frontend/src/utils/__tests__/parseAmount.test.ts`, replace line 2:

```ts
import { parseAmount } from '../parseAmount';
```

with:

```ts
import { decimalToNumber, hydrateAmounts, parseAmount } from '../parseAmount';
```

and append at the end of the file:

```ts

describe('decimalToNumber', () => {
  it('turns the decimal strings the API sends into numbers the steps can add', () => {
    expect(decimalToNumber('2500.00')).toBe(2500);
    expect(decimalToNumber('100.50')).toBe(100.5);
  });

  it('keeps a saved 0 as 0, so it does not show as blank', () => {
    expect(decimalToNumber('0.00')).toBe(0);
    expect(decimalToNumber(0)).toBe(0);
  });

  it('passes through a number the filer typed', () => {
    expect(decimalToNumber(12.5)).toBe(12.5);
  });

  it('never yields NaN: a value it cannot read becomes an empty field', () => {
    for (const value of ['abc', '', null, undefined, Number.NaN, Number.POSITIVE_INFINITY, {}]) {
      expect(decimalToNumber(value)).toBeUndefined();
    }
  });
});

describe('hydrateAmounts', () => {
  it('converts only the listed amount fields and leaves the rest of the row alone', () => {
    const row = { id: 7, creditor_name: 'Chase', amount_owed: '2500.00', notes: '42' };
    expect(hydrateAmounts(row, ['amount_owed', 'monthly_payment'])).toEqual({
      id: 7,
      creditor_name: 'Chase',
      amount_owed: 2500,
      notes: '42',
    });
  });

  it('does not add amount fields the server did not send', () => {
    const hydrated = hydrateAmounts({ amount_owed: '1.00' }, ['amount_owed', 'monthly_payment']);
    expect('monthly_payment' in hydrated).toBe(false);
  });

  it('leaves the session data it was given untouched', () => {
    const row = { amount_owed: '2500.00' };
    hydrateAmounts(row, ['amount_owed']);
    expect(row.amount_owed).toBe('2500.00');
  });
});
```

**1d.** Append at the end of `frontend/src/pages/__tests__/IntakeWizard.test.tsx`.

The file already imports `screen`, `http`, `HttpResponse` and `server` (lines 1–6), and defines `sessionAtStep1` (line 37) and `renderWizard()` (line 53). `beforeEach` is a vitest global.

The test serves the same session for every GET, so the provider's startup load and Task 4's wizard re-read both return string amounts. It holds whatever shape Task 4 gave the mount, because it asserts only what the filer sees.

```tsx

// ===========================================================================
// Amounts loaded from the server (DIG-2)
// ===========================================================================

/** A returning filer on Amounts Owed. DRF sends decimal amounts as strings. */
const sessionAtStep5WithDebts = {
  ...sessionAtStep1,
  current_step: 5,
  debts: [
    {
      id: 7,
      session: 1,
      data_source: 'uploaded_document',
      creditor_name: 'Chase',
      debt_type: 'credit_card',
      priority_classification: 'unsecured',
      amount_owed: '2500.00',
      monthly_payment: '75.00',
      is_in_collections: false,
      notes: '',
      is_draft: false,
      source_document_name: null,
    },
    {
      id: 8,
      session: 1,
      data_source: 'manual',
      creditor_name: 'Mercy Hospital',
      debt_type: 'medical',
      priority_classification: 'unsecured',
      amount_owed: '100.50',
      monthly_payment: null,
      is_in_collections: false,
      notes: '',
      is_draft: false,
      source_document_name: null,
    },
  ],
};

describe('IntakeWizard amounts a returning filer already entered', { timeout: 15_000 }, () => {
  beforeEach(() => {
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep5WithDebts)
      ),
      // Loaded debts are valid, so autosave PATCHes about 2 s after the step appears.
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(sessionAtStep5WithDebts)
      )
    );
  });

  it('shows each saved amount and adds them up instead of joining them as text', async () => {
    renderWizard();

    expect(await screen.findByText('$2,600.50')).toBeInTheDocument();
    const amountInputs = screen.getAllByRole('spinbutton', { name: /^amount owed/i });
    expect(amountInputs[0]).toHaveValue(2500);
    expect(amountInputs[1]).toHaveValue(100.5);
  });
});
```

- [ ] **Step 2: Run them and confirm they fail**

```bash
cd /Volumes/Containers/DigniFi/backend
.venv/bin/python -m pytest apps/intake/tests/test_readable_amounts.py apps/documents/tests/test_views.py -q --tb=line
```

Expected: 3 new failures. This was verified on a copy of the tree with Task 3 applied.
- `test_amounts_are_readable_while_ssn_and_account_numbers_stay_private` fails with `KeyError: 'amount_owed'`, because amounts are write-only.
- `test_a_correction_too_large_or_unreadable_is_refused_and_the_session_still_opens[99999999999.99]` fails with `assert 200 == 400`. Today `validate` stores the amount.
- `test_a_correction_too_large_or_unreadable_is_refused_and_the_session_still_opens[not a number]` fails with `decimal.InvalidOperation: [<class 'decimal.ConversionSyntax'>]` from `apps/intake/fields.py:63`. Today this is a 500.

These pass today as guards, and that is intended:
- `test_only_the_owner_can_read_amounts` pins down the access boundary that readable amounts now depend on.
- `test_a_corrected_amount_reaches_the_draft_debt` covers the happy path the new validation must not break.

The file's other existing tests pass.

```bash
cd /Volumes/Containers/DigniFi/frontend
npx vitest run src/utils/__tests__/parseAmount.test.ts src/pages/__tests__/IntakeWizard.test.tsx
```

Expected: 8 failures.
- The 7 new helper tests fail with `TypeError: (0 , __vite_ssr_import_1__.decimalToNumber) is not a function` (or `…hydrateAmounts) is not a function`).
- The wizard test fails with `Unable to find an element with the text: $2,600.50`. The DOM dump shows the total as `$` followed by `02500.00100.50`, which is DebtsStep's `reduce` joining strings.

All pre-existing tests in both files pass.

- [ ] **Step 3: Implement**

**3a.** In `backend/apps/intake/serializers.py`, make the three amounts readable and keep the explicit `DecimalField` declarations. Replace lines 155–159:

```python
    # Explicit field declarations — EncryptedDecimalField confuses DRF's auto-mapper
    current_value = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True)
    amount_owed = serializers.DecimalField(
        max_digits=12, decimal_places=2, write_only=True, required=False, default=0
    )
```

with:

```python
    # Explicit field declarations — EncryptedDecimalField confuses DRF's auto-mapper
    current_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    amount_owed = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=0
    )
```

Keep the `amount_owed` declaration on three lines. Joined it would be 102 characters, and black at line length 100 leaves it split.

Then replace lines 190–191:

```python
    # Explicit field declaration — EncryptedDecimalField confuses DRF's auto-mapper
    amount_owed = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True)
```

with:

```python
    # Explicit field declaration — EncryptedDecimalField confuses DRF's auto-mapper
    amount_owed = serializers.DecimalField(max_digits=12, decimal_places=2)
```

Do not touch these; they stay write-only:
- `"ssn": {"write_only": True}` (line 53)
- both `"account_number": {"write_only": True}` entries (lines 179 and 215)

**3b.** In `backend/apps/documents/views.py`, change the import on line 7 from:

```python
from rest_framework import status
```

to:

```python
from rest_framework import serializers, status
```

Then, inside `def validate(self, request, pk=None):`, replace:

```python
        fields = request.data.get("fields", {})
        ocr = doc.ocr_result
```

with:

```python
        fields = request.data.get("fields", {})
        draft_fields = {k: v for k, v in fields.items() if k in ("creditor_name", "amount_owed")}
        if "amount_owed" in draft_fields:
            # Amounts are readable on every session read, and DecimalField(12, 2) cannot
            # represent a wider value, so refuse it here before anything is written.
            try:
                draft_fields["amount_owed"] = serializers.DecimalField(
                    max_digits=12, decimal_places=2
                ).run_validation(draft_fields["amount_owed"])
            except serializers.ValidationError as exc:
                return Response({"amount_owed": exc.detail}, status=status.HTTP_400_BAD_REQUEST)

        ocr = doc.ocr_result
```

and further down in the same method, replace:

```python
            doc.draft_debts.filter(is_draft=True).update(
                **{k: v for k, v in fields.items() if k in ("creditor_name", "amount_owed")}
            )
```

with:

```python
            doc.draft_debts.filter(is_draft=True).update(**draft_fields)
```

`extracted_data` still records the raw `fields`, because a `Decimal` is not JSON-serializable. The draft debt receives the validated `Decimal`.

**3c.** In `frontend/src/utils/parseAmount.ts`, append after the closing `}` of `parseAmount` (line 17):

```ts

/**
 * Convert a decimal from the API into a number for wizard state.
 *
 * DRF sends decimals as strings ("2500.00"), and the steps add and compare
 * amounts, so a string would join as text instead of adding. Anything that is not
 * a finite number becomes `undefined` (an empty field), never `NaN`.
 */
export function decimalToNumber(value: unknown): number | undefined {
  if (typeof value === 'number') return Number.isFinite(value) ? value : undefined;
  if (typeof value !== 'string') return undefined;
  const parsed = parseAmount(value);
  return parsed !== undefined && Number.isFinite(parsed) ? parsed : undefined;
}

/**
 * Return a copy of `row` with each listed amount converted by `decimalToNumber`.
 * Keys the row does not have stay absent, so a partial save never sends them.
 */
export function hydrateAmounts<T extends object>(row: T, keys: readonly string[]): T {
  const hydrated = { ...row } as Record<string, unknown>;
  for (const key of keys) {
    if (key in hydrated) hydrated[key] = decimalToNumber(hydrated[key]);
  }
  return hydrated as T;
}
```

**3d.** Edit `frontend/src/pages/IntakeWizard.tsx` in three places.

First, add the import directly after `import { trackEvent } from '../utils/analytics';` (line 13):

```tsx
import { hydrateAmounts } from '../utils/parseAmount';
```

Second, add the field lists after the `WIZARD_STEPS` array. Replace:

```tsx
  { number: 8, label: 'Review & Results', key: 'review' },
];
```

with:

```tsx
  { number: 8, label: 'Review & Results', key: 'review' },
];

// DRF sends these decimals as strings ("2500.00"). The steps add and compare them,
// so they become numbers as session data enters wizard state.
const ASSET_AMOUNT_FIELDS = ['current_value', 'amount_owed'] as const;
const DEBT_AMOUNT_FIELDS = ['amount_owed', 'monthly_payment'] as const;
```

Third, hydrate assets and debts where session data enters step state. Task 4 (commit 5) put that in one place: the `.then((fresh) => { ... })` block of the wizard's mount effect, which fills step state from the session `openSession()` resolves with (from `loadSession(id)` or `createSession(1)`). Replace, with the Edit tool (8-space indent, as Task 4 wrote it):

```tsx
        if (fresh.assets) setAssetsData(fresh.assets);
        if (fresh.debts) setDebtsData(fresh.debts);
```

with:

```tsx
        if (fresh.assets)
          setAssetsData(fresh.assets.map((asset) => hydrateAmounts(asset, ASSET_AMOUNT_FIELDS)));
        if (fresh.debts)
          setDebtsData(fresh.debts.map((debt) => hydrateAmounts(debt, DEBT_AMOUNT_FIELDS)));
```

Then run `npx prettier --write src/pages/IntakeWizard.tsx` from `/Volumes/Containers/DigniFi/frontend`, and Read the file again before any later Edit.

Leave the `onDataChange={setAssetsData}` and `onDataChange={setDebtsData}` props alone; steps already hand back numbers. Check that no other call feeds raw session data into these setters (do not use `grep`: it is aliased to `rg` here, and `rtk` rewrites its output):

```bash
cd /Volumes/Containers/DigniFi && git grep -n -e 'setAssetsData(' -e 'setDebtsData(' -- frontend/src/pages/IntakeWizard.tsx
```

Expected: exactly two lines, the hydrated calls above (`setAssetsData(fresh.assets.map((asset) => hydrateAmounts(asset, ASSET_AMOUNT_FIELDS)));` and `setDebtsData(fresh.debts.map((debt) => hydrateAmounts(debt, DEBT_AMOUNT_FIELDS)));`). The `onDataChange={setAssetsData}` props and the `useState` declarations have no `(` after the setter name, so they do not match. Any other line means raw session data still reaches a setter; hydrate it the same way.

Do not hydrate in `IntakeContext`, and do not touch `DebtsStep`/`AssetsStep`. Their own edits already produce numbers through `parseAmount`.

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd /Volumes/Containers/DigniFi/backend
.venv/bin/python -m pytest apps/intake/tests/test_readable_amounts.py apps/documents/tests/test_views.py apps/intake/tests/test_session_nested_save.py -q --tb=line
.venv/bin/python -m pytest -q --tb=line
.venv/bin/python -m pytest --cov=apps --cov=config --cov-fail-under=90 -q --tb=line
.venv/bin/ruff check .
.venv/bin/black --line-length 100 --check apps/intake/serializers.py apps/documents/views.py apps/documents/tests/test_views.py apps/intake/tests/test_readable_amounts.py
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run

cd /Volumes/Containers/DigniFi/frontend
npx vitest run src/utils/__tests__/parseAmount.test.ts src/pages/__tests__/IntakeWizard.test.tsx
npx vitest run
npx tsc -b
npm run lint
npx prettier --check src/utils/parseAmount.ts src/pages/IntakeWizard.tsx src/utils/__tests__/parseAmount.test.ts src/pages/__tests__/IntakeWizard.test.tsx
```

Expected:
- **Backend:**
  - Targeted run: `0 failed`. `test_session_nested_save.py` stays green; its re-save test now round-trips the readable amounts too.
  - Full suite: `0 failed`.
  - Coverage: at least 90%.
  - Ruff: `All checks passed!`
  - Black: `4 files would be left unchanged.`
  - Migrations: `No changes detected`.
- **Frontend:**
  - Both files pass.
  - The full vitest suite: 0 failed.
  - `tsc` and eslint: no errors.
  - Prettier: `All matched files use Prettier code style!`

This was verified on a copy of the tree with Tasks 3 and 10 applied: backend 708 passed and 1 xfailed, frontend 217 passed. The counts will be higher once Tasks 4–9 are in.

- [ ] **Step 5: Update CLAUDE.md gotchas**

In the root `CLAUDE.md` "Gotchas" list, insert this line directly after Task 3's line that starts `- **Nested debts and assets save by id**`:

```markdown
- **Debt and asset amounts are readable, as strings** — the owner gets `DebtInfo.amount_owed` and `AssetInfo.current_value`/`amount_owed` back (SSN and `account_number` stay write-only). DRF sends decimals as strings (`"2500.00"`), so the wizard converts them with `hydrateAmounts` (`utils/parseAmount.ts`) as session data enters step state; a raw string in a step's `reduce` joins as text (`$02500.00100.50`). A stored amount wider than `DecimalField(12, 2)` makes every read of that session 500, so every write path must bound it (`DraftDebtCreator` caps it; documents `validate` returns 400).
```

No existing gotcha becomes false.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/Containers/DigniFi
git diff --stat
git add backend/apps/intake/serializers.py backend/apps/documents/views.py backend/apps/intake/tests/test_readable_amounts.py backend/apps/documents/tests/test_views.py frontend/src/utils/parseAmount.ts frontend/src/utils/__tests__/parseAmount.test.ts frontend/src/pages/IntakeWizard.tsx frontend/src/pages/__tests__/IntakeWizard.test.tsx
git diff CLAUDE.md
git add CLAUDE.md
git diff --cached --stat
git commit -m "fix(intake): show filers the amounts they already entered"
```

Notes on staging:
- **Before staging,** `git diff --stat` must show that the eight code and test files above hold only this task's changes. By commit 11 every earlier task's edits to them are committed. If one still has another task's hunk, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it.
- **`git diff CLAUDE.md` before `git add CLAUDE.md`:** it must show only this task's Step 5 hunk, the one added line starting `- **Debt and asset amounts are readable, as strings**`. Tasks 1–2 committed every other `CLAUDE.md` change, and each later task commits its own. If anything else appears, stop and ask the owner.
- **Expected `git diff --cached --stat`:** exactly 9 files.
- **Never stage** `.serena/`, `DESIGN.md`, `assets/`, `.impeccable` or README hunks.
- **The commit message** is exactly the line above, with no body and no `Co-Authored-By` or other trailer.
- **If pre-commit rewrites a file** (black, prettier or eslint `--fix`), re-stage the same paths, including `git add CLAUDE.md`. Then rerun the same `git commit` command.

---

### Task 11: Keep saved income when the Income step reopens  (Commit #12 in spec §9)

Ticket DIG-41. Spec §4.4.

Why: only `IncomeInfo.monthly_income` (six months) is stored, and it is canonical: means test, Schedule I, 106Sum, 107, 122A-1 and Schedule J all read it. The step's ten per-source boxes are never stored, yet the wizard rebuilt `monthly_income` from them on every save, so reopening Income wrote six zeros. It also echoed every hydrated field back, and a wizard-created row's blank `marital_status` is a 400 that strands the filer on Income.

**Files:**
- Modify: `backend/apps/intake/models.py:97-101` (add a method after `IncomeInfo.__str__`)
- Modify: `backend/apps/intake/serializers.py:73-84` (`IncomeInfoSerializer` head)
- Modify: `frontend/src/components/wizard/steps/IncomeInfoStep.tsx:16` (add `SOURCE_FIELDS` above the props interface), `:31-42` (total), `:63-66` (emitted data), `:99` (saved-total note before `{/* General error */}`)
- Modify: `frontend/src/pages/IntakeWizard.tsx` income branch of `saveCurrentStepData` (lines 207-218 before Task 4; about 256-267 after Task 4; match the text)
- Modify: `CLAUDE.md` Gotchas list (append one bullet)
- Test: `backend/apps/intake/tests/test_income_resume.py` (new)
- Test: `frontend/src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx` (new)
- Test: `frontend/src/pages/__tests__/IntakeWizard.test.tsx` (append one `describe`)

**Interfaces:**
- Consumes: Task 4's wizard (the `saveCurrentStepData` switch is unchanged by Task 4 apart from its position); `parseAmount` (`frontend/src/utils/parseAmount.ts`); the `IncomeInfo` type's existing `monthly_income?: number[]` and `total_monthly_income: number` (`frontend/src/types/api.ts:76-98`).
- Produces:
  - `IncomeInfo.calculate_total_monthly_income(self) -> float`: mean of the stored months, quantized to cents, `0.0` when none (mirrors `ExpenseInfo.calculate_total_monthly_expenses`, which also returns `float`).
  - `IncomeInfoSerializer.total_monthly_income`: read-only `SerializerMethodField`; the API's `income_info` now carries it (the fee-waiver page's income pre-fill, `FeeWaiverPage.tsx:25`, starts working as a side effect).
  - `IncomeInfoStep` always emits `monthly_income` and `total_monthly_income`: the stored months unchanged when no source key is present; six copies of the source sum once any source key is present; six zeros for a new filer who types nothing.
  - The wizard's income save sends exactly `{ income_info: { monthly_income } }`.

- [ ] **Step 1: Write the failing tests**

Create `backend/apps/intake/tests/test_income_resume.py`:
```python
"""A filer who reopens the Income step keeps the income they saved (DIG-41).

Only ``IncomeInfo.monthly_income`` (six months) is stored. The step's per-source boxes
never reach the server, so the step shows the saved total the API reports, and saves send
``monthly_income`` alone.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import IncomeInfo, IntakeSession
from apps.users.models import User


@pytest.fixture
def filer_session(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    filer = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=filer, district=district)
    client = APIClient()
    client.force_authenticate(user=filer)
    return client, session


@pytest.mark.django_db
class TestIncomeStepResume:
    def test_returning_filer_gets_their_saved_monthly_income_total(self, filer_session):
        client, session = filer_session
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            monthly_income=[3100, 3300, 3200, 3200, 3150, 3250],
        )

        resp = client.get(f"/api/intake/sessions/{session.pk}/")

        assert resp.status_code == 200
        assert resp.json()["income_info"]["total_monthly_income"] == 3200.0

    def test_saved_total_is_shown_to_the_cent(self, filer_session):
        client, session = filer_session
        IncomeInfo.objects.create(
            session=session,
            marital_status="single",
            monthly_income=[1000, 1000, 1000, 1000, 1000, 1001],
        )

        resp = client.get(f"/api/intake/sessions/{session.pk}/")

        assert resp.json()["income_info"]["total_monthly_income"] == 1000.17

    def test_row_without_months_reports_zero_instead_of_breaking_the_session_read(
        self, filer_session
    ):
        client, session = filer_session
        IncomeInfo.objects.create(session=session, marital_status="single", monthly_income=[])

        resp = client.get(f"/api/intake/sessions/{session.pk}/")

        assert resp.status_code == 200
        assert resp.json()["income_info"]["total_monthly_income"] == 0.0

    def test_saving_income_amounts_keeps_household_details(self, filer_session):
        client, session = filer_session
        IncomeInfo.objects.create(
            session=session,
            marital_status="married_joint",
            number_of_dependents=2,
            monthly_income=[2500] * 6,
        )

        resp = client.patch(
            f"/api/intake/sessions/{session.pk}/",
            {"income_info": {"monthly_income": [4000] * 6}},
            format="json",
        )

        assert resp.status_code == 200
        income = IncomeInfo.objects.get(session=session)
        assert income.monthly_income == [4000] * 6
        assert income.marital_status == "married_joint"
        assert income.number_of_dependents == 2

    def test_echoing_a_blank_marital_status_back_is_rejected(self, filer_session):
        # Why the wizard sends monthly_income alone: a row the wizard created has a blank
        # marital_status, and sending the row back as read is a 400 that strands the filer.
        client, session = filer_session
        IncomeInfo.objects.create(session=session, monthly_income=[3200] * 6)

        resp = client.patch(
            f"/api/intake/sessions/{session.pk}/",
            {
                "income_info": {
                    "marital_status": "",
                    "number_of_dependents": 0,
                    "monthly_income": [3200] * 6,
                }
            },
            format="json",
        )

        assert resp.status_code == 400
```

Create `frontend/src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx`:
```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { IncomeInfoStep } from '../IncomeInfoStep';
import type { IncomeInfo } from '../../../../types/api';

// The server stores only six months of income and reports their average. It never stores
// the per-source boxes, so a returning filer's data arrives with none of them (DIG-41).
const savedIncome: Partial<IncomeInfo> = {
  monthly_income: [3100, 3300, 3200, 3200, 3150, 3250],
  total_monthly_income: 3200,
};

const SAVED_TOTAL_NOTE =
  'Your saved total is $3,200.00 a month. We keep only the total, not the amount from each source, so the boxes below start empty. If you enter amounts below, they will replace the saved total.';

function renderStep(initialData: Partial<IncomeInfo>) {
  const onDataChange = vi.fn();
  render(
    <IncomeInfoStep
      initialData={initialData}
      onDataChange={onDataChange}
      onValidationChange={vi.fn()}
    />
  );
  const lastEmitted = () =>
    onDataChange.mock.calls[onDataChange.mock.calls.length - 1][0] as Partial<IncomeInfo>;
  return { lastEmitted };
}

describe('IncomeInfoStep', () => {
  it('shows a returning filer their saved income instead of $0', () => {
    renderStep(savedIncome);

    expect(screen.getByText(SAVED_TOTAL_NOTE)).toBeInTheDocument();
    expect(screen.getByText('$3,200.00')).toBeInTheDocument();
  });

  it('keeps each saved month exactly as stored when the filer changes nothing', () => {
    const { lastEmitted } = renderStep(savedIncome);

    expect(lastEmitted().monthly_income).toEqual([3100, 3300, 3200, 3200, 3150, 3250]);
  });

  it('replaces the saved total with the amounts the filer enters', () => {
    const { lastEmitted } = renderStep(savedIncome);

    fireEvent.change(screen.getByLabelText(/monthly wages/i), { target: { value: '2000' } });
    fireEvent.change(screen.getByLabelText(/social security/i), { target: { value: '500' } });

    expect(lastEmitted().monthly_income).toEqual([2500, 2500, 2500, 2500, 2500, 2500]);
    expect(screen.getByText('$2,500.00')).toBeInTheDocument();
    expect(screen.queryByText(SAVED_TOTAL_NOTE)).not.toBeInTheDocument();
  });

  it('lets a filer record $0 income in place of a saved total', () => {
    const { lastEmitted } = renderStep(savedIncome);

    fireEvent.change(screen.getByLabelText(/monthly wages/i), { target: { value: '0' } });

    expect(lastEmitted().monthly_income).toEqual([0, 0, 0, 0, 0, 0]);
    expect(screen.getByText('$0.00')).toBeInTheDocument();
  });

  it('records six months of $0 for a new filer who leaves every box blank', () => {
    const { lastEmitted } = renderStep({});

    expect(lastEmitted().monthly_income).toEqual([0, 0, 0, 0, 0, 0]);
    expect(screen.queryByText(/your saved total is/i)).not.toBeInTheDocument();
  });
});
```
The months are deliberately uneven, so an implementation that sends six copies of the mean fails "keeps each saved month exactly as stored".

Append to the end of `frontend/src/pages/__tests__/IntakeWizard.test.tsx`:
```tsx

// ===========================================================================
// Income save (DIG-41)
// ===========================================================================

describe('IntakeWizard income save', { timeout: 15_000 }, () => {
  it("saves a returning filer's months exactly as stored, and nothing else, when they continue without changes", async () => {
    // What the API returns for a filer who saved income earlier through the wizard: the
    // months, their average, and the blank household fields a wizard-created row holds.
    const savedSession = {
      ...sessionAtStep1,
      current_step: 2,
      income_info: {
        marital_status: '',
        number_of_dependents: 0,
        monthly_income: [3100, 3300, 3200, 3200, 3150, 3250],
        total_monthly_income: 3200,
        created_at: '2026-10-01T10:00:00Z',
      },
    };
    const patchBodies: unknown[] = [];
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(savedSession)
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', async ({ request }) => {
        patchBodies.push(await request.json());
        return HttpResponse.json(savedSession);
      }),
      http.post('http://localhost:8000/api/intake/sessions/:id/update_step/', () =>
        HttpResponse.json({
          session: { ...savedSession, current_step: 3 },
          message: 'Step updated.',
        })
      )
    );

    renderWizard();
    await screen.findByRole('heading', { name: /income/i, level: 2 });
    await userEvent.click(screen.getByRole('button', { name: /continue/i }));
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    expect(patchBodies.length).toBeGreaterThan(0);
    for (const body of patchBodies) {
      expect(body).toEqual({
        income_info: { monthly_income: [3100, 3300, 3200, 3200, 3150, 3250] },
      });
    }
  });
});
```
Every PATCH is checked, not just the last, because autosave can fire before the click on a slow machine.

- [ ] **Step 2: Run them and confirm they fail**

```bash
cd /Volumes/Containers/DigniFi/backend
.venv/bin/python -m pytest apps/intake/tests/test_income_resume.py -q
```
Expected: `3 failed, 2 passed`. `test_returning_filer_gets_their_saved_monthly_income_total`, `test_saved_total_is_shown_to_the_cent` and `test_row_without_months_reports_zero_instead_of_breaking_the_session_read` fail with `KeyError: 'total_monthly_income'`. The empty-months test exists because the serializer method runs on every session read: dividing by zero there would 500 the whole wizard. `test_saving_income_amounts_keeps_household_details` and `test_echoing_a_blank_marital_status_back_is_rejected` already pass: they pin the behaviour the wizard's new payload relies on, and that behaviour is unchanged.

```bash
cd /Volumes/Containers/DigniFi/frontend
npx vitest run src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx src/pages/__tests__/IntakeWizard.test.tsx
```
Expected: 5 failures.
- `shows a returning filer their saved income instead of $0`: `Unable to find an element with the text: Your saved total is $3,200.00 a month. ...`
- `replaces the saved total ...`: `expected [ 3100, 3300, 3200, 3200, 3150, 3250 ] to deeply equal [ 2500, ... ]`
- `lets a filer record $0 ...`: `expected [ 3100, ... ] to deeply equal [ +0, +0, +0, +0, +0, +0 ]`
- `records six months of $0 for a new filer ...`: `expected undefined to deeply equal [ +0, ... ]`
- `saves a returning filer's months exactly as stored ...`: `expected { income_info: { …(5) } } to deeply equal { income_info: { …(1) } }`

`keeps each saved month exactly as stored when the filer changes nothing` already passes. The old step passed the stored array through; the zeros came from the wizard, which the wizard test catches.

- [ ] **Step 3: Implement**

`backend/apps/intake/models.py`: in `class IncomeInfo`, insert a method after `__str__` (lines 97-101). Replace:
```python
    def __str__(self) -> str:
        return (
            f"IncomeInfo: {self.marital_status}, {self.number_of_dependents} dependents "
            f"(Session: {self.session_id})"
        )
```
With:
```python
    def __str__(self) -> str:
        return (
            f"IncomeInfo: {self.marital_status}, {self.number_of_dependents} dependents "
            f"(Session: {self.session_id})"
        )

    def calculate_total_monthly_income(self) -> float:
        """Average monthly income over the stored months, to the cent.

        Only the 6-month array is stored, never the per-source amounts the filer typed,
        so this is the saved total the Income step shows when it reopens.
        """
        months = self.monthly_income or []
        if not months:
            return 0.0
        total = sum(Decimal(str(amount)) for amount in months)
        return float((total / len(months)).quantize(Decimal("0.01")))
```
`Decimal` is already imported at the top of `models.py` (line 3). `Decimal(str(...))` matches how the means test reads the same array (`apps/eligibility/models.py:112`). No migration.

`backend/apps/intake/serializers.py` (lines 73-84). Replace:
```python
class IncomeInfoSerializer(serializers.ModelSerializer):
    """Serializer for income information."""

    class Meta:
        model = IncomeInfo
        fields = [
            "marital_status",
            "number_of_dependents",
            "monthly_income",
            "created_at",
        ]
        read_only_fields = ["created_at"]
```
With:
```python
class IncomeInfoSerializer(serializers.ModelSerializer):
    """Serializer for income information."""

    total_monthly_income = serializers.SerializerMethodField()

    class Meta:
        model = IncomeInfo
        fields = [
            "marital_status",
            "number_of_dependents",
            "monthly_income",
            "total_monthly_income",
            "created_at",
        ]
        read_only_fields = ["created_at", "total_monthly_income"]

    def get_total_monthly_income(self, obj):
        """Return the saved monthly income total (the average of the stored months)."""
        return obj.calculate_total_monthly_income()
```
Leave `validate_monthly_income` and the `update_or_create` in `IntakeSessionSerializer.update` as they are.

`frontend/src/components/wizard/steps/IncomeInfoStep.tsx`, four hunks.

(1) Above the props interface (line 16). Replace:
```tsx
interface IncomeInfoStepProps {
```
With:
```tsx
/**
 * The ten per-source boxes. The server stores only the 6-month `monthly_income` array,
 * never these, so a session read back from the server carries none of them.
 */
const SOURCE_FIELDS = [
  'monthly_gross_wages',
  'monthly_overtime',
  'monthly_tips',
  'monthly_rental_income',
  'monthly_pension',
  'monthly_social_security',
  'monthly_unemployment',
  'monthly_child_support',
  'monthly_alimony',
  'monthly_other_income',
] as const;

interface IncomeInfoStepProps {
```

(2) The total (lines 31-42). Replace:
```tsx
  // Calculate total monthly income
  const totalMonthlyIncome =
    (formData.monthly_gross_wages || 0) +
    (formData.monthly_overtime || 0) +
    (formData.monthly_tips || 0) +
    (formData.monthly_rental_income || 0) +
    (formData.monthly_pension || 0) +
    (formData.monthly_social_security || 0) +
    (formData.monthly_unemployment || 0) +
    (formData.monthly_child_support || 0) +
    (formData.monthly_alimony || 0) +
    (formData.monthly_other_income || 0);
```
With:
```tsx
  // Typing in a box writes its key, so the step switches to source amounts once any key
  // is present, even one cleared back to blank. Until then it keeps the saved months.
  const usesSourceAmounts = SOURCE_FIELDS.some((field) => field in formData);
  const savedMonthlyIncome = usesSourceAmounts ? undefined : formData.monthly_income;

  // Calculate total monthly income: the saved total until the filer enters source amounts
  const totalMonthlyIncome = savedMonthlyIncome
    ? (formData.total_monthly_income ?? 0)
    : SOURCE_FIELDS.reduce((sum, field) => sum + (formData[field] || 0), 0);
```

(3) The emitted data (lines 63-66). Replace:
```tsx
    const dataWithTotal = {
      ...formData,
      total_monthly_income: totalMonthlyIncome,
    };
```
With:
```tsx
    const dataWithTotal = {
      ...formData,
      // Saved months go back exactly as stored. Source amounts replace them with six copies
      // of their sum (MVP: the same income each month), and a new filer who enters nothing
      // records six months of $0.
      monthly_income: savedMonthlyIncome ?? Array(6).fill(totalMonthlyIncome),
      total_monthly_income: totalMonthlyIncome,
    };
```
Keep the effect's dependency list `[formData, totalMonthlyIncome, errors]` and its existing `eslint-disable-next-line react-hooks/exhaustive-deps` comment; `savedMonthlyIncome` derives from `formData`.

(4) The saved-total note, between the explainer `info-box` and the general error (line 99). Replace:
```tsx
      {/* General error */}
```
With:
```tsx
      {/* Saved total: only the total is stored, so the boxes start empty */}
      {savedMonthlyIncome && (
        <div className="info-box">
          <p className="info-message">
            Your saved total is $
            {totalMonthlyIncome.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}{' '}
            a month. We keep only the total, not the amount from each source, so the boxes below
            start empty. If you enter amounts below, they will replace the saved total.
          </p>
        </div>
      )}

      {/* General error */}
```
The note's words are spec §5 "income · saved total note", verbatim, with the amount filled in. The existing "Total Monthly Income" box needs no change: it renders `totalMonthlyIncome`, which now holds the saved total until the filer types.

`frontend/src/pages/IntakeWizard.tsx`, income branch of `saveCurrentStepData`. Replace:
```tsx
      case 'income_info': {
        // Transform detailed income data to backend format (6-month array)
        // MVP Assumption: Current monthly income is consistent for last 6 months
        const incomePayload = {
          ...incomeData,
          monthly_income: Array(6).fill(incomeData.total_monthly_income || 0),
        };
        await api.intake.updateSession(session.id, {
          income_info: incomePayload,
        } as Partial<IntakeSession>);
        break;
      }
```
With:
```tsx
      case 'income_info':
        // Send the months alone: IncomeInfoStep re-emits them as stored unless the filer
        // entered source amounts. Echoing other fields read from the server (a blank
        // marital_status) is a 400 that would strand the filer on Income.
        await api.intake.updateSession(session.id, {
          income_info: { monthly_income: incomeData.monthly_income },
        } as Partial<IntakeSession>);
        break;
```
No backfill of rows already zeroed (spec §4.4, §7 gate 2).

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd /Volumes/Containers/DigniFi/backend
.venv/bin/python -m pytest apps/intake/tests/test_income_resume.py -q
.venv/bin/python -m pytest --cov=apps --cov=config --cov-fail-under=90 -q
.venv/bin/ruff check .
.venv/bin/black --line-length 100 --check apps/intake/models.py apps/intake/serializers.py apps/intake/tests/test_income_resume.py
DJANGO_SETTINGS_MODULE=config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
```
Expected: `5 passed` for the new file; the whole suite green (702 passed, 1 xfailed on the tree this plan was verified against, plus whatever Tasks 3-10 add) with `Required test coverage of 90% reached`; ruff `All checks passed!`; black `3 files would be left unchanged.`; `No changes detected`. Task 0 Step 3g installed ruff 0.8.5 and black 24.10.0 into `backend/.venv`, the versions CI and the pre-commit hook pin. `makemigrations` needs `DJANGO_SETTINGS_MODULE=config.settings.test`: `manage.py` defaults to `config.settings.development`, which points at postgres on `localhost:5432`, a port another process owns on this machine.

```bash
cd /Volumes/Containers/DigniFi/frontend
npx vitest run src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx src/pages/__tests__/IntakeWizard.test.tsx
npx vitest run
npx tsc -b
npm run lint
```
Expected: the two files pass (5 step tests, and the wizard file with its new test); full suite green; `tsc -b` and lint report nothing.

- [ ] **Step 5: Update CLAUDE.md gotchas**

Append at the end of the Gotchas list in `/Volumes/Containers/DigniFi/CLAUDE.md` (after the last bullet, before the blank line above `## Architecture (quick)`):
```markdown
- **Income stores only the 6-month array** — `IncomeInfo.monthly_income` is canonical (means test, Schedule I, 122A-1); the Income step's ten per-source boxes are never stored. The API adds read-only `total_monthly_income` (the mean of the stored months, to the cent). `IncomeInfoStep` switches to per-source amounts only when a source key is _present_ in its data; otherwise it re-emits the stored months unchanged. The wizard saves `{income_info: {monthly_income}}` only, because echoing a wizard-created row's blank `marital_status` back is a 400.
```

- [ ] **Step 6: Commit**

Check `cd /Volumes/Containers/DigniFi && git diff -- backend/apps/intake/serializers.py frontend/src/pages/IntakeWizard.tsx frontend/src/pages/__tests__/IntakeWizard.test.tsx CLAUDE.md` shows only this task's hunks (Tasks 3 and 10 edit `serializers.py` and must already be committed). `git diff CLAUDE.md` must show only the Step 5 bullet starting `- **Income stores only the 6-month array**`; Tasks 1–2 committed every other `CLAUDE.md` change, and each later task commits its own. If anything else appears, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it.
```bash
cd /Volumes/Containers/DigniFi
git add backend/apps/intake/models.py \
  backend/apps/intake/serializers.py \
  backend/apps/intake/tests/test_income_resume.py \
  frontend/src/components/wizard/steps/IncomeInfoStep.tsx \
  frontend/src/components/wizard/steps/__tests__/IncomeInfoStep.test.tsx \
  frontend/src/pages/IntakeWizard.tsx \
  frontend/src/pages/__tests__/IntakeWizard.test.tsx \
  CLAUDE.md
git commit -m "fix(intake): keep saved income when the Income step reopens"
```
If a pre-commit hook (prettier, black, ruff `--fix`) rewrites files, re-run the same `git add` (it includes `CLAUDE.md`) and the same `git commit`. No trailer.

---

### Task 12: Save expenses under the names the court forms read  (Commit #13 in spec §9)

Ticket DIG-45. Spec §4.5, contract C5, uses C6 from Task 10.

Why: the Expenses step sent five names the backend does not know (`car_payment`, `car_insurance`, `gas_transportation`, `food_groceries`, `other_necessary_expenses`) and had no clothing or child-support box. DRF drops unknown names silently, so car, food and other costs saved as $0 and never reached the means test, the fee-waiver total or Schedule J. The backend names are canonical. This task changes only the frontend and E2E; the backend test pins the contract.

Court forms are out of scope (spec §4.6): do not touch any schema, derivation or generator, even though Schedule J's bindings for these fields are wrong until DIG-52 lands in the forms project.

**Files:**
- Modify: `frontend/src/types/api.ts:110-124` (`ExpenseInfo` fields; add `EXPENSE_FIELDS` after the interface)
- Modify: `frontend/src/components/wizard/steps/ExpenseInfoStep.tsx` (whole file; renames at lines 36-43, 155-202, 211-223, 267-278; new row after line 265; import at line 14)
- Modify: `frontend/src/pages/IntakeWizard.tsx` (the `EXPENSE_FIELDS` value import after the `import type { ... } from '../types/api';` block near line 34; the `expense_info` line in Task 4's `.then((fresh) => ...)` block, line 120 after Task 4). The `hydrateAmounts` import is already there from Task 10.
- Modify: `frontend/src/test/fixtures/session.ts:66-77` (`createMockExpenseInfo`; otherwise `tsc -b` fails on the renamed type)
- Modify: `frontend/e2e/pages/wizard.page.ts:115-145` (`fillExpenses`; drop `EXPENSE_FIELD_MAP`)
- Modify: `frontend/e2e/pages/fee-waiver.page.ts:8-9` (add a locator accessor)
- Modify: `frontend/e2e/journeys/maria-happy-path.spec.ts:72-74` (assert the pre-filled expense total)
- Modify: `CLAUDE.md` Gotchas list (append one bullet)
- Test: `frontend/src/components/wizard/steps/__tests__/ExpenseInfoStep.test.tsx` (new)
- Test: `frontend/src/pages/__tests__/IntakeWizard.test.tsx` (append one `describe`)
- Test: `backend/apps/intake/tests/test_expense_field_names.py` (new)
- Modify: `backend/apps/intake/tests/test_integration_flow.py:86-111` (it posts the old names, which DRF drops silently; the same blind spot as DIG-45)

**Interfaces:**
- Consumes:
  - C6 `hydrateAmounts<T extends object>(row: T, keys: readonly string[]): T` from `frontend/src/utils/parseAmount.ts` (Task 10, commit 11).
  - Task 4's line `if (fresh.expense_info) setExpenseData(fresh.expense_info);` inside the wizard's mount effect.
  - Backend `ExpenseInfoSerializer` (`backend/apps/intake/serializers.py:118-148`, unchanged): the 13 canonical decimal fields, returned as strings such as `"1100.00"`, plus `total_monthly_expenses` as a float.
- Produces:
  - C5 `export const EXPENSE_FIELDS = [...] as const` in `frontend/src/types/api.ts`, the 13 keys in model order.
  - `ExpenseInfo` type with `vehicle_payment`, `vehicle_insurance`, `vehicle_maintenance`, `food_and_groceries`, `clothing`, `child_support_paid`, `other_expenses` (old names gone).
  - `ExpenseInfoStep` inputs named exactly by `EXPENSE_FIELDS` (`input[name=<key>]`), including new `clothing` and `child_support_paid`.
  - E2E: `WizardPage.fillExpenses(expenses)` fills `input[name=<key>]` for each persona key; `FeeWaiverPage.monthlyExpenses(): Locator`.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/wizard/steps/__tests__/ExpenseInfoStep.test.tsx`:
```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { ExpenseInfoStep } from '../ExpenseInfoStep';

// The names ExpenseInfo stores and Schedule J, Form 122A-2 and the means test read. DRF
// drops any other name without an error, which is how car, food and other costs once
// saved as $0 (DIG-45).
const COURT_FORM_EXPENSE_NAMES = [
  'rent_or_mortgage',
  'utilities',
  'home_maintenance',
  'vehicle_payment',
  'vehicle_insurance',
  'vehicle_maintenance',
  'food_and_groceries',
  'clothing',
  'medical_expenses',
  'childcare',
  'child_support_paid',
  'insurance_not_deducted',
  'other_expenses',
];

function renderStep() {
  const onDataChange = vi.fn();
  const { container } = render(
    <ExpenseInfoStep initialData={{}} onDataChange={onDataChange} onValidationChange={vi.fn()} />
  );
  const inputNamed = (name: string) =>
    container.querySelector(`input[name="${name}"]`) as HTMLInputElement | null;
  const lastEmitted = () =>
    onDataChange.mock.calls[onDataChange.mock.calls.length - 1][0] as Record<string, unknown>;
  return { inputNamed, lastEmitted };
}

describe('ExpenseInfoStep', () => {
  it('saves every expense under the name the court forms read', () => {
    const { inputNamed, lastEmitted } = renderStep();

    COURT_FORM_EXPENSE_NAMES.forEach((name, index) => {
      const input = inputNamed(name);
      expect(input, `a box named ${name}`).not.toBeNull();
      fireEvent.change(input!, { target: { value: String((index + 1) * 10) } });
    });

    const emitted = lastEmitted();
    COURT_FORM_EXPENSE_NAMES.forEach((name, index) => {
      expect(emitted[name], name).toBe((index + 1) * 10);
    });
    for (const unknownName of [
      'car_payment',
      'car_insurance',
      'gas_transportation',
      'food_groceries',
      'other_necessary_expenses',
    ]) {
      expect(emitted).not.toHaveProperty(unknownName);
    }
  });

  it('counts clothing and child support paid in the monthly total', () => {
    const { inputNamed, lastEmitted } = renderStep();

    fireEvent.change(inputNamed('rent_or_mortgage')!, { target: { value: '1000' } });
    fireEvent.change(screen.getByLabelText('Clothing'), { target: { value: '60' } });
    fireEvent.change(screen.getByLabelText('Child Support Paid'), { target: { value: '200' } });

    expect(screen.getByText('$1,260.00')).toBeInTheDocument();
    expect(lastEmitted().total_monthly_expenses).toBe(1260);
  });
});
```
The names are written out literally rather than imported from `EXPENSE_FIELDS`, so a wrong edit to the constant cannot make the test agree with it.

Append to the end of `frontend/src/pages/__tests__/IntakeWizard.test.tsx`:
```tsx

// ===========================================================================
// Expenses read back from the server (DIG-45)
// ===========================================================================

describe('IntakeWizard expense hydration', { timeout: 15_000 }, () => {
  it("adds up a returning filer's saved expenses, which the API sends as decimal strings", async () => {
    const savedSession = {
      ...sessionAtStep1,
      current_step: 3,
      expense_info: {
        data_source: 'manual',
        rent_or_mortgage: '1100.00',
        utilities: '180.00',
        home_maintenance: '0.00',
        vehicle_payment: '0.00',
        vehicle_insurance: '85.00',
        vehicle_maintenance: '40.00',
        food_and_groceries: '450.00',
        clothing: '60.00',
        medical_expenses: '75.00',
        childcare: '400.00',
        child_support_paid: '0.00',
        insurance_not_deducted: '120.00',
        other_expenses: '50.00',
        total_monthly_expenses: 2560.0,
        created_at: '2026-10-01T10:00:00Z',
        updated_at: '2026-10-01T10:00:00Z',
      },
    };
    server.use(
      http.get('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(savedSession)
      ),
      http.patch('http://localhost:8000/api/intake/sessions/:id/', () =>
        HttpResponse.json(savedSession)
      )
    );

    renderWizard();
    await screen.findByRole('heading', { name: /expenses/i, level: 2 });

    expect(screen.getByText('$2,560.00')).toBeInTheDocument();
  });
});
```

Create `backend/apps/intake/tests/test_expense_field_names.py`:
```python
"""Expenses the wizard saves land in the fields the means test and court forms read (DIG-45).

DRF drops unknown field names without an error. That is how the wizard's old names
(car_payment, food_groceries, other_necessary_expenses, ...) saved car, food and other
costs as $0. These tests pin the canonical names the Expenses step now sends.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.districts.models import District
from apps.intake.models import ExpenseInfo, IntakeSession
from apps.users.models import User

# One distinct amount per canonical ExpenseInfo field, as DRF returns it.
CANONICAL_EXPENSES = {
    "rent_or_mortgage": "1100.00",
    "utilities": "180.00",
    "home_maintenance": "25.00",
    "vehicle_payment": "310.00",
    "vehicle_insurance": "85.00",
    "vehicle_maintenance": "40.00",
    "food_and_groceries": "450.00",
    "clothing": "60.00",
    "medical_expenses": "75.00",
    "childcare": "400.00",
    "child_support_paid": "200.00",
    "insurance_not_deducted": "120.00",
    "other_expenses": "50.00",
}


@pytest.fixture
def filer_session(db):
    district = District.objects.create(
        code="ILND",
        name="Illinois Northern",
        state="IL",
        court_name="U.S. Bankruptcy Court ILND",
        filing_fee_chapter_7=Decimal("338.00"),
    )
    filer = User.objects.create_user(username="filer", password="pw")
    session = IntakeSession.objects.create(user=filer, district=district)
    client = APIClient()
    client.force_authenticate(user=filer)
    return client, session


@pytest.mark.django_db
def test_expense_saved_under_each_canonical_name_is_stored_and_returned(filer_session):
    client, session = filer_session
    # The wizard sends plain numbers.
    payload = {name: float(amount) for name, amount in CANONICAL_EXPENSES.items()}

    resp = client.patch(
        f"/api/intake/sessions/{session.pk}/", {"expense_info": payload}, format="json"
    )

    assert resp.status_code == 200
    stored = ExpenseInfo.objects.get(session=session)
    for name, amount in CANONICAL_EXPENSES.items():
        assert getattr(stored, name) == Decimal(amount), name
    returned = client.get(f"/api/intake/sessions/{session.pk}/").json()["expense_info"]
    for name, amount in CANONICAL_EXPENSES.items():
        assert returned[name] == amount, name
    assert returned["total_monthly_expenses"] == 3095.0
```

- [ ] **Step 2: Run them and confirm they fail**

```bash
cd /Volumes/Containers/DigniFi/frontend
npx vitest run src/components/wizard/steps/__tests__/ExpenseInfoStep.test.tsx src/pages/__tests__/IntakeWizard.test.tsx
```
Expected: 3 failures.
- `saves every expense under the name the court forms read`: `AssertionError: a box named vehicle_payment: expected null not to be null`
- `counts clothing and child support paid ...`: `TestingLibraryElementError: Unable to find a label with the text of: Clothing`
- `adds up a returning filer's saved expenses ...`: `Unable to find an element with the text: $2,560.00`. The decimal strings are concatenated rather than added.

```bash
cd /Volumes/Containers/DigniFi/backend
.venv/bin/python -m pytest apps/intake/tests/test_expense_field_names.py -q
```
Expected: `1 passed`, before and after the change. The backend already stores the canonical names; this test pins the contract the frontend is moving onto, so a backend rename cannot silently reopen DIG-45.

- [ ] **Step 3: Implement**

`frontend/src/types/api.ts` (lines 110-124). Replace:
```ts
  // Transportation
  car_payment: number;
  car_insurance: number;
  gas_transportation: number;

  // Living expenses
  food_groceries: number;
  childcare: number;
  medical_expenses: number;
  insurance_not_deducted: number;
  other_necessary_expenses: number;

  // Calculated field
  total_monthly_expenses: number;
}
```
With:
```ts
  // Transportation
  vehicle_payment: number;
  vehicle_insurance: number;
  vehicle_maintenance: number;

  // Living expenses
  food_and_groceries: number;
  clothing: number;
  childcare: number;
  child_support_paid: number;
  medical_expenses: number;
  insurance_not_deducted: number;
  other_expenses: number;

  // Calculated field
  total_monthly_expenses: number;
}

/**
 * The 13 monthly expense amounts, under the names the backend stores and the court forms
 * read. DRF drops any other name without an error, so the step sums and sends only these.
 */
export const EXPENSE_FIELDS = [
  'rent_or_mortgage',
  'utilities',
  'home_maintenance',
  'vehicle_payment',
  'vehicle_insurance',
  'vehicle_maintenance',
  'food_and_groceries',
  'clothing',
  'medical_expenses',
  'childcare',
  'child_support_paid',
  'insurance_not_deducted',
  'other_expenses',
] as const;
```
(`types/api.ts` already exports runtime values, e.g. `FORM_TYPE_METADATA`.)

`frontend/src/components/wizard/steps/ExpenseInfoStep.tsx`: replace the whole file with:
```tsx
/**
 * Expense Info Step - Monthly expense collection
 *
 * Trauma-informed design:
 * - Non-judgmental language about expenses
 * - Clear explanations of categories
 * - Real-time total calculation
 * - Plain language help text
 */

import { useState, useEffect, useMemo } from 'react';
import { FormField } from '../../common';
import { parseAmount } from '../../../utils/parseAmount';
import type { ExpenseInfo } from '../../../types/api';
import { EXPENSE_FIELDS } from '../../../types/api';

interface ExpenseInfoStepProps {
  initialData?: Partial<ExpenseInfo>;
  onDataChange: (data: Partial<ExpenseInfo>) => void;
  onValidationChange: (isValid: boolean) => void;
}

export function ExpenseInfoStep({
  initialData,
  onDataChange,
  onValidationChange,
}: ExpenseInfoStepProps) {
  // Fields start undefined (empty) rather than 0 so an untouched field reads
  // blank, while a deliberately entered 0 is preserved by parseAmount + `?? ''`.
  const [formData, setFormData] = useState<Partial<ExpenseInfo>>(initialData || {});

  // Calculate total monthly expenses
  const totalMonthlyExpenses = EXPENSE_FIELDS.reduce(
    (sum, field) => sum + (formData[field] || 0),
    0
  );

  const errors = useMemo<Record<string, string>>(() => {
    const newErrors: Record<string, string> = {};

    // No "at least one expense" gate: a blank or $0 expense is a valid answer
    // (the help text invites leaving categories blank or 0).

    // Validate non-negative values
    Object.keys(formData).forEach((key) => {
      const value = formData[key as keyof ExpenseInfo];
      if (typeof value === 'number' && value < 0) {
        newErrors[key] = 'Amount cannot be negative';
      }
    });

    return newErrors;
  }, [formData]);

  // Update parent when form data changes
  useEffect(() => {
    const dataWithTotal = {
      ...formData,
      total_monthly_expenses: totalMonthlyExpenses,
    };
    onDataChange(dataWithTotal);
    onValidationChange(Object.keys(errors).length === 0);
    // onDataChange/onValidationChange are fresh closures each render; including
    // them would loop. Matches the suppression on the sibling step effects.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData, totalMonthlyExpenses, errors]);

  const handleChange = (field: keyof ExpenseInfo, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: parseAmount(value) }));
  };

  return (
    <div className="expense-info-step">
      {/* Explainer */}
      <div className="info-box">
        <svg className="info-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
            clipRule="evenodd"
          />
        </svg>
        <div>
          <h3 className="info-title">Why we ask about expenses</h3>
          <p className="info-message">
            Monthly expenses help determine your financial situation. Enter your average monthly
            costs. If a category doesn't apply to you, you can leave it blank or enter $0.
          </p>
        </div>
      </div>

      {/* General error */}
      {errors.general && (
        <div className="form-error" role="alert">
          {errors.general}
        </div>
      )}

      {/* Housing Expenses */}
      <section className="form-section">
        <h3 className="section-title">Housing Expenses</h3>
        <p className="section-description">
          Include your monthly housing costs (rent or mortgage) and related expenses.
        </p>

        <FormField
          label="Rent or Mortgage Payment"
          name="rent_or_mortgage"
          type="number"
          min="0"
          step="0.01"
          value={formData.rent_or_mortgage ?? ''}
          onChange={(e) => handleChange('rent_or_mortgage', e.target.value)}
          error={errors.rent_or_mortgage}
          helpText="Monthly rent or mortgage payment"
          placeholder="0.00"
        />

        <div className="form-row">
          <FormField
            label="Utilities"
            name="utilities"
            type="number"
            min="0"
            step="0.01"
            value={formData.utilities ?? ''}
            onChange={(e) => handleChange('utilities', e.target.value)}
            error={errors.utilities}
            helpText="Electric, gas, water, trash, internet, phone"
            placeholder="0.00"
          />

          <FormField
            label="Home Maintenance"
            name="home_maintenance"
            type="number"
            min="0"
            step="0.01"
            value={formData.home_maintenance ?? ''}
            onChange={(e) => handleChange('home_maintenance', e.target.value)}
            error={errors.home_maintenance}
            helpText="Repairs, yard work, HOA fees"
            placeholder="0.00"
          />
        </div>
      </section>

      {/* Transportation Expenses */}
      <section className="form-section">
        <h3 className="section-title">Transportation Expenses</h3>
        <p className="section-description">
          Include car payments, insurance, gas, and other transportation costs.
        </p>

        <div className="form-row">
          <FormField
            label="Car Payment"
            name="vehicle_payment"
            type="number"
            min="0"
            step="0.01"
            value={formData.vehicle_payment ?? ''}
            onChange={(e) => handleChange('vehicle_payment', e.target.value)}
            error={errors.vehicle_payment}
            helpText="Monthly auto loan or lease payment"
            placeholder="0.00"
          />

          <FormField
            label="Car Insurance"
            name="vehicle_insurance"
            type="number"
            min="0"
            step="0.01"
            value={formData.vehicle_insurance ?? ''}
            onChange={(e) => handleChange('vehicle_insurance', e.target.value)}
            error={errors.vehicle_insurance}
            helpText="Monthly auto insurance premium"
            placeholder="0.00"
          />
        </div>

        <FormField
          label="Gas & Transportation"
          name="vehicle_maintenance"
          type="number"
          min="0"
          step="0.01"
          value={formData.vehicle_maintenance ?? ''}
          onChange={(e) => handleChange('vehicle_maintenance', e.target.value)}
          error={errors.vehicle_maintenance}
          helpText="Gas, public transit, parking, tolls"
          placeholder="0.00"
        />
      </section>

      {/* Living Expenses */}
      <section className="form-section">
        <h3 className="section-title">Living Expenses</h3>
        <p className="section-description">
          Include food, childcare, medical expenses, and other necessary costs.
        </p>

        <div className="form-row">
          <FormField
            label="Food & Groceries"
            name="food_and_groceries"
            type="number"
            min="0"
            step="0.01"
            value={formData.food_and_groceries ?? ''}
            onChange={(e) => handleChange('food_and_groceries', e.target.value)}
            error={errors.food_and_groceries}
            helpText="Groceries, dining out, household supplies"
            placeholder="0.00"
          />

          <FormField
            label="Childcare"
            name="childcare"
            type="number"
            min="0"
            step="0.01"
            value={formData.childcare ?? ''}
            onChange={(e) => handleChange('childcare', e.target.value)}
            error={errors.childcare}
            helpText="Daycare, after-school care, babysitting"
            placeholder="0.00"
          />
        </div>

        <div className="form-row">
          <FormField
            label="Medical Expenses"
            name="medical_expenses"
            type="number"
            min="0"
            step="0.01"
            value={formData.medical_expenses ?? ''}
            onChange={(e) => handleChange('medical_expenses', e.target.value)}
            error={errors.medical_expenses}
            helpText="Doctor visits, prescriptions, co-pays not covered by insurance"
            placeholder="0.00"
          />

          <FormField
            label="Insurance (Not Deducted from Pay)"
            name="insurance_not_deducted"
            type="number"
            min="0"
            step="0.01"
            value={formData.insurance_not_deducted ?? ''}
            onChange={(e) => handleChange('insurance_not_deducted', e.target.value)}
            error={errors.insurance_not_deducted}
            helpText="Health, life, or disability insurance you pay directly"
            placeholder="0.00"
          />
        </div>

        <div className="form-row">
          <FormField
            label="Clothing"
            name="clothing"
            type="number"
            min="0"
            step="0.01"
            value={formData.clothing ?? ''}
            onChange={(e) => handleChange('clothing', e.target.value)}
            error={errors.clothing}
            helpText="Clothes, shoes, laundry, and dry cleaning"
            placeholder="0.00"
          />

          <FormField
            label="Child Support Paid"
            name="child_support_paid"
            type="number"
            min="0"
            step="0.01"
            value={formData.child_support_paid ?? ''}
            onChange={(e) => handleChange('child_support_paid', e.target.value)}
            error={errors.child_support_paid}
            helpText="Court-ordered support you pay to someone else"
            placeholder="0.00"
          />
        </div>

        <FormField
          label="Other Necessary Expenses"
          name="other_expenses"
          type="number"
          min="0"
          step="0.01"
          value={formData.other_expenses ?? ''}
          onChange={(e) => handleChange('other_expenses', e.target.value)}
          error={errors.other_expenses}
          helpText="Clothing, laundry, personal care, pet care, other essentials"
          placeholder="0.00"
        />
      </section>

      {/* Total Summary */}
      <section className="form-section form-section--summary">
        <div className="expense-total">
          <h3 className="total-label">Total Monthly Expenses</h3>
          <p className="total-amount">
            $
            {totalMonthlyExpenses.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
          <p className="total-help-text">
            This is your total monthly expenses across all categories.
          </p>
        </div>
      </section>
    </div>
  );
}

export default ExpenseInfoStep;
```
Against the current file this does four things and nothing else:
- it renames the five fields (`name`, `value`, `handleChange` key and `errors` key of each);
- it computes the total from `EXPENSE_FIELDS`;
- it adds one `import { EXPENSE_FIELDS }` line;
- it adds one `form-row` holding Clothing and Child Support Paid, between the Medical/Insurance row and Other.

Every existing label and help text stays as it is, including "Gas & Transportation" with its transit help (spec §4.5: Schedule J line 12 groups gas, maintenance and transit fares). The "Other Necessary Expenses" help still lists clothing and laundry; it is left unchanged on purpose because the spec says "rename only". The plan summary raises it as an open item.

`frontend/src/pages/IntakeWizard.tsx`, two edits (item 1 is a no-change check).

(1) `hydrateAmounts` import: Task 10 (commit 11) already imports it, with `import { hydrateAmounts } from '../utils/parseAmount';` on the line after `import { trackEvent } from '../utils/analytics';`. Make no change.

(2) Import `EXPENSE_FIELDS` as a value import directly after the existing `import type { ... } from '../types/api';` block (same two-line pattern as `frontend/src/components/forms/FormCard.tsx:12-13`). Replace:
```tsx
  DebtInfo,
} from '../types/api';
```
With:
```tsx
  DebtInfo,
} from '../types/api';
import { EXPENSE_FIELDS } from '../types/api';
```

(3) In the mount effect's `.then((fresh) => { ... })` block that Task 4 added, replace the expense line:
```tsx
        if (fresh.expense_info) setExpenseData(fresh.expense_info);
```
With:
```tsx
        if (fresh.expense_info) setExpenseData(hydrateAmounts(fresh.expense_info, EXPENSE_FIELDS));
```
Do not touch the `assets` / `debts` lines, which Task 10 already hydrates.

The expense save (`case 'expense_info'` in `saveCurrentStepData`) stays `expense_info: expenseData`. `expenseData` now carries only canonical keys plus read-only fields that DRF ignores.

`frontend/src/test/fixtures/session.ts` (lines 66-77, inside `createMockExpenseInfo`). Replace:
```ts
  rent_or_mortgage: 1200,
  utilities: 150,
  home_maintenance: 50,
  car_payment: 300,
  car_insurance: 100,
  gas_transportation: 80,
  food_groceries: 400,
  childcare: 0,
  medical_expenses: 50,
  insurance_not_deducted: 100,
  other_necessary_expenses: 70,
  total_monthly_expenses: 2500,
```
With:
```ts
  rent_or_mortgage: 1200,
  utilities: 150,
  home_maintenance: 50,
  vehicle_payment: 300,
  vehicle_insurance: 100,
  vehicle_maintenance: 80,
  food_and_groceries: 400,
  clothing: 0,
  childcare: 0,
  child_support_paid: 0,
  medical_expenses: 50,
  insurance_not_deducted: 100,
  other_expenses: 70,
  total_monthly_expenses: 2500,
```

`frontend/e2e/pages/wizard.page.ts` (lines 115-145). Replace:
```ts
  // ── Step 3: Expenses ────────────────────────────────────────────

  /** Persona expense keys → current ExpenseInfoStep field names. */
  private static readonly EXPENSE_FIELD_MAP: Record<string, string> = {
    rent_or_mortgage: 'rent_or_mortgage',
    utilities: 'utilities',
    home_maintenance: 'home_maintenance',
    vehicle_payment: 'car_payment',
    vehicle_insurance: 'car_insurance',
    vehicle_maintenance: 'gas_transportation',
    food_and_groceries: 'food_groceries',
    clothing: 'other_necessary_expenses',
    medical_expenses: 'medical_expenses',
    childcare: 'childcare',
    child_support_paid: 'other_necessary_expenses',
    insurance_not_deducted: 'insurance_not_deducted',
    other_expenses: 'other_necessary_expenses',
  };

  async fillExpenses(expenses: Record<string, number>) {
    // Sum persona values into their mapped fields (several map to "other")
    const totals: Record<string, number> = {};
    for (const [key, value] of Object.entries(expenses)) {
      const field = WizardPage.EXPENSE_FIELD_MAP[key];
      if (!field) continue;
      totals[field] = (totals[field] || 0) + value;
    }
    for (const [field, value] of Object.entries(totals)) {
      await this.page.locator(`input[name="${field}"]`).fill(String(value));
    }
  }
```
With:
```ts
  // ── Step 3: Expenses ────────────────────────────────────────────

  async fillExpenses(expenses: Record<string, number>) {
    // Persona keys are the backend's ExpenseInfo names, and ExpenseInfoStep names each
    // box the same way, so every amount goes straight into its own box.
    for (const [field, value] of Object.entries(expenses)) {
      await this.page.locator(`input[name="${field}"]`).fill(String(value));
    }
  }
```
All five personas in `e2e/fixtures/personas.ts` use exactly the 13 canonical keys, so every key has a box.

`frontend/e2e/pages/fee-waiver.page.ts` (lines 8-9). Replace:
```ts
export class FeeWaiverPage {
  constructor(private page: Page) {}
```
With:
```ts
export class FeeWaiverPage {
  constructor(private page: Page) {}

  /** The expenses box, which the page pre-fills from the total the intake saved. */
  monthlyExpenses() {
    return this.page.getByLabel(/total monthly expenses/i);
  }
```

`frontend/e2e/journeys/maria-happy-path.spec.ts` (lines 72-74; Task 2 adds a `documents.skip()` call earlier in this file and does not touch these lines). The assertion must come before `feeWaiver.submit(...)`, which overwrites the field. Replace:
```ts
    // Maria is fee-waiver eligible → routed to the waiver application first
    const totalExpenses = Object.values(MARIA.expenses).reduce((a, b) => a + b, 0);
    await feeWaiver.submit(
```
With:
```ts
    // Maria is fee-waiver eligible → routed to the waiver application first
    const totalExpenses = Object.values(MARIA.expenses).reduce((a, b) => a + b, 0);
    // Every expense she typed was saved under a name the backend keeps, so the
    // pre-filled total is her full $2,560, not just the fields that kept their names.
    await expect(feeWaiver.monthlyExpenses()).toHaveValue(String(totalExpenses));
    await feeWaiver.submit(
```
`expect` is already imported from `@playwright/test` in this spec. `FeeWaiverPage.tsx:24-29` pre-fills `String(session.expense_info.total_monthly_expenses)`; the server's `2560.0` arrives as the JS number `2560`, so the box holds `"2560"`. Before this change it held `"1875"` (only the six fields whose names matched).

- [ ] **Step 3b: Stop the integration test from posting names the backend drops**

`backend/apps/intake/tests/test_integration_flow.py:86-109` builds `expense_data` twice. Both dicts use names the serializer does not know (`food_groceries`, `transportation`, `other_necessary_expenses`, `car_payment`, `car_insurance`, `gas_transportation`). The test passes only because DRF drops them silently. Replace everything from the `# 4. Add Expense Info` comment through the second dict's closing `}` with the block below. Leave the existing `response = self.client.post(reverse("expense-info-list"), expense_data)` and its 201 assertion in place, and add the vehicle-payment assertion right after them:

```python
        # 4. Add Expense Info, under the canonical ExpenseInfo field names
        expense_data = {
            "session": session_id,
            "rent_or_mortgage": 1500,
            "utilities": 200,
            "home_maintenance": 50,
            "vehicle_payment": 300,
            "vehicle_insurance": 100,
            "vehicle_maintenance": 150,
            "food_and_groceries": 400,
            "childcare": 0,
            "medical_expenses": 50,
            "insurance_not_deducted": 0,
            "other_expenses": 100,
        }
```

```python
        self.assertEqual(response.data["vehicle_payment"], "300.00")
```

Run: `cd /Volumes/Containers/DigniFi/backend && .venv/bin/python -m pytest apps/intake/tests/test_integration_flow.py -q`
Expected: PASS. The new assertion fails if the name is ever dropped again.

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd /Volumes/Containers/DigniFi/frontend
npx vitest run src/components/wizard/steps/__tests__/ExpenseInfoStep.test.tsx src/pages/__tests__/IntakeWizard.test.tsx
npx vitest run
npx tsc -b
npm run lint
git grep -nE "car_payment|car_insurance|gas_transportation|food_groceries|other_necessary_expenses" -- src e2e ':(exclude)src/**/__tests__/**'
```
Expected: the two files pass; the full suite is green (222 on the verified tree: Task 4's 213 plus Task 11's 6 and this task's 3, plus whatever Tasks 5-10 added); `tsc -b` and lint report nothing; the `git grep` prints nothing. Today it lists `e2e/pages/wizard.page.ts`, `ExpenseInfoStep.tsx`, `src/test/fixtures/session.ts` and `src/types/api.ts`. The pathspec excludes `__tests__` because the new step test names the old names on purpose. Use `git grep`, not `grep`: in this environment `grep` may be aliased to `rg`, which reads `-r` as `--replace`. `npm run lint` covers `e2e/`, which `tsc -b` does not type-check. Test files are excluded from `tsc -b` (`tsconfig.app.json`), so lint is what catches an unused import in a test.

```bash
cd /Volumes/Containers/DigniFi/backend
.venv/bin/python -m pytest apps/intake/tests/test_expense_field_names.py -q
.venv/bin/python -m pytest --cov=apps --cov=config --cov-fail-under=90 -q
.venv/bin/ruff check .
.venv/bin/black --line-length 100 --check apps/intake/tests/test_expense_field_names.py
```
Expected: `1 passed`; suite green with `Required test coverage of 90% reached`; `All checks passed!`; black `1 file would be left unchanged.` Task 0 Step 3g installed ruff 0.8.5 and black 24.10.0 into `backend/.venv`.

E2E (spec §9 requires it at the tip; run it here if the stack is up, with the backend migrated and seeded per CLAUDE.md "E2E needs full stack"):
```bash
cd /Volumes/Containers/DigniFi/frontend
npm run e2e -- e2e/journeys/maria-happy-path.spec.ts
npm run e2e
```
Expected: Maria passes with the pre-fill assertion; the other journeys still pass. Persona outcomes do not flip. Fee-waiver eligibility uses income alone (`apps/eligibility/models.py:170-172`). Priya, the one above-median persona, now has food and vehicle payment counted. Her allowable expenses are capped at her actual food, health, housing and vehicle-payment amounts ($4,150), so her disposable income stays at least $7,850 a month against the $756.25 threshold (`apps/eligibility/services/expense_deduction_calculator.py:40-54`).

- [ ] **Step 5: Update CLAUDE.md gotchas**

Append at the end of the Gotchas list in `/Volumes/Containers/DigniFi/CLAUDE.md` (after the last bullet, before the blank line above `## Architecture (quick)`):
```markdown
- **Expense names are the backend's** — the Expenses step, the wizard and the E2E page object use `EXPENSE_FIELDS` (`types/api.ts`), the 13 `ExpenseInfo` names that Schedule J, 122A-2 and the means test read. DRF drops any other name silently: the old frontend names (`car_payment`, `food_groceries`, `other_necessary_expenses`, ...) saved as $0 until DIG-45. The API returns these amounts as decimal strings; the wizard converts them with `hydrateAmounts` when it loads the session.
```

- [ ] **Step 6: Commit**

Check `cd /Volumes/Containers/DigniFi && git diff -- frontend/src/types/api.ts frontend/src/pages/IntakeWizard.tsx frontend/src/pages/__tests__/IntakeWizard.test.tsx CLAUDE.md` shows only this task's hunks. `git diff CLAUDE.md` must show only the Step 5 bullet starting `- **Expense names are the backend's**`; Tasks 1–2 committed every other `CLAUDE.md` change, and each later task commits its own. If anything else appears, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it.
```bash
cd /Volumes/Containers/DigniFi
git add frontend/src/types/api.ts \
  frontend/src/components/wizard/steps/ExpenseInfoStep.tsx \
  frontend/src/components/wizard/steps/__tests__/ExpenseInfoStep.test.tsx \
  frontend/src/pages/IntakeWizard.tsx \
  frontend/src/pages/__tests__/IntakeWizard.test.tsx \
  frontend/src/test/fixtures/session.ts \
  frontend/e2e/pages/wizard.page.ts \
  frontend/e2e/pages/fee-waiver.page.ts \
  frontend/e2e/journeys/maria-happy-path.spec.ts \
  backend/apps/intake/tests/test_expense_field_names.py \
  backend/apps/intake/tests/test_integration_flow.py \
  CLAUDE.md
git commit -m "fix(intake): save expenses under the names the court forms read"
```
If a pre-commit hook rewrites files, re-run the same `git add` (it includes `CLAUDE.md`) and the same `git commit`. No trailer.

---

### Task 13: Give bills, pay stubs and credit reports their own upload areas  (Commit #14 in spec §9)

Every upload is sent as `creditor_bill` today (`DocumentUploadPage.tsx:46`), so a pay stub becomes a fake debt owed to the employer (DIG-3). This task replaces the single drop zone with three labelled areas, each sending its own `document_type`. The queue, polling, summary and button logic stay exactly as they are; Task 14 rewrites them. The two "show/hide" conditions around the zone (`isEmpty` at :89 and `!allComplete` at :94) are kept on purpose, because "areas stay visible after a batch" is Task 14's retry fix.

All code below was run in a scratch copy of `frontend/`: vitest, `tsc` and `eslint --max-warnings=0` all passed, and prettier made no changes.

**Files:**
- Modify: `frontend/src/components/documents/FileDropZone.tsx:1-55` (whole-file replacement). Props are at :3-6. `handleDrop` (:14-18) ignores `disabled`. The fixed `aria-label="Drop files here or click to upload"` is at :29. The hidden `<input>` is at :45-52.
- Modify: `frontend/src/pages/DocumentUploadPage.tsx:1-115` (whole-file replacement). `handleFiles` is at :34-56, with the hard-coded `'creditor_bill'` at :46. The two single zones are at :89 and :94.
- Modify: `frontend/src/test/mocks/handlers.ts:153-155`. The insert goes after the `/intake/debts/` POST handler, the last entry of the `// -- Assets / Debts` block, and before `// -- Forms`. Anchor on that text, because earlier tasks may shift the line numbers.
- Modify: `CLAUDE.md`. Append to the end of the `## Gotchas (things agents get wrong)` list, immediately above `## Architecture (quick)` (currently line 55).
- Test: `frontend/src/pages/__tests__/DocumentUploadPage.test.tsx` (create; no test exists for this page, `UploadQueue` or `FileDropZone` today).

**Interfaces:**
- Consumes:
  - `uploadDocument(sessionId: number, file: File, documentType: string): Promise<DocumentUploadResponse>` (`client.ts:618`, unchanged in this task).
  - `useIntake()` → `{ session, isLoading, createSession }` (`IntakeContext.tsx`).
  - The page exactly as commit 3 leaves it: the OpenAI disclosure paragraph and the `{allComplete ? 'Continue' : 'Skip for now'}` label.
- Produces:
  - **C8:** module-level `const UPLOAD_AREAS = [{ type: 'creditor_bill', label: 'Bills and statements', help }, { type: 'pay_stub', label: 'Pay stubs', help }, { type: 'credit_report', label: 'Credit report', help }] as const` and `type UploadType = (typeof UPLOAD_AREAS)[number]['type']`. Neither is exported, because react-refresh allows only component exports from a page.
  - `FileDropZone` props `{ label: string; onFiles: (files: File[]) => void; disabled?: boolean }`. Its `role="button"` has `aria-label` `${label}: drop files here or click to upload`, and the `<input type="file">` stays nested inside it.
  - A drop or input change is ignored while `disabled`, and the input carries `disabled`.
  - Each area is `<section aria-labelledby="upload-area-<type>">` with `<h2 id="upload-area-<type>">`, so a test can query it as `getByRole('region', { name: 'Pay stubs' })`.
  - MSW default handlers for `POST /documents/upload/` (202 `{ id: 1, status: 'processing' }`) and `GET /documents/:id/` (completed).
  - Test helpers `renderUploadPage`, `dropZone`, `readyZone`, `dropFiles`, `pdf`, `sentDocumentType` (Task 14 keeps them).
  - Locator contract consumed by `e2e/pages/documents.page.ts` (C9): `uploadBill(path)` can `setInputFiles` on `page.getByRole('button', { name: 'Bills and statements: drop files here or click to upload' }).locator('input[type="file"]')`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/pages/__tests__/DocumentUploadPage.test.tsx`:

```tsx
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { DocumentUploadPage } from '../DocumentUploadPage';

const API = 'http://localhost:8000/api';

function renderUploadPage() {
  return render(
    <MemoryRouter initialEntries={['/documents']}>
      <IntakeProvider>
        <Routes>
          <Route path="/documents" element={<DocumentUploadPage />} />
          <Route path="/intake" element={<h1>Intake wizard</h1>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

function dropZone(label: string) {
  return screen.getByRole('button', { name: `${label}: drop files here or click to upload` });
}

/** Under real timers: wait until the session exists and the area's zone takes files. */
async function readyZone(label: string) {
  await waitFor(() => expect(dropZone(label)).toHaveAttribute('aria-disabled', 'false'));
  return dropZone(label);
}

function dropFiles(zone: HTMLElement, ...files: File[]) {
  fireEvent.drop(zone, { dataTransfer: { files } });
}

// undici's request.formData() rejects jsdom's File, so read the field from the multipart text.
async function sentDocumentType(request: Request) {
  const body = await request.text();
  return /name="document_type"\r\n\r\n([^\r\n]*)/.exec(body)?.[1] ?? '';
}

function pdf(name: string) {
  return new File(['%PDF-1.4'], name, { type: 'application/pdf' });
}

describe('DocumentUploadPage', () => {
  it('sends each area its own document type, so a pay stub is never filed as a bill', async () => {
    const sentTypes: string[] = [];
    server.use(
      http.post(`${API}/documents/upload/`, async ({ request }) => {
        sentTypes.push(await sentDocumentType(request));
        return HttpResponse.json({ id: sentTypes.length, status: 'processing' }, { status: 202 });
      }),
      // Every file stays "being read", so this test sees only what each area sent.
      http.get(`${API}/documents/:id/`, ({ params }) =>
        HttpResponse.json({
          id: Number(params.id),
          document_type: 'creditor_bill',
          original_filename: 'file.pdf',
          uploaded_at: '2026-01-20T10:00:00Z',
          ocr_result: {
            status: 'processing',
            failure_reason: '',
            confidence_scores: {},
            overall_confidence: 0,
            user_validated: false,
          },
        })
      )
    );

    renderUploadPage();
    expect(screen.getByRole('heading', { level: 2, name: 'Pay stubs' })).toBeInTheDocument();

    dropFiles(await readyZone('Bills and statements'), pdf('electric-bill.pdf'));
    await waitFor(() => expect(sentTypes).toHaveLength(1));
    dropFiles(await readyZone('Pay stubs'), pdf('pay-stub.pdf'));
    await waitFor(() => expect(sentTypes).toHaveLength(2));
    dropFiles(await readyZone('Credit report'), pdf('credit-report.pdf'));
    await waitFor(() => expect(sentTypes).toHaveLength(3));

    expect(sentTypes).toEqual(['creditor_bill', 'pay_stub', 'credit_report']);
  });
});
```

Notes on the test design, all verified:
- **Session setup.** No `current_session_id` is set, so the page's own auto-create effect makes the session through the default `POST /intake/sessions/` handler. `readyZone` waits for that before dropping.
- **Multipart parsing.** `request.formData()` throws `AssertionError … webidl.is.File(value)` under vitest's jsdom, which is why `sentDocumentType` reads the multipart text. jsdom also loses the file's bytes (the part arrives as `filename="blob"`), and nothing here needs them.
- **Polling override.** The GET override keeps every file "processing". Otherwise the old `UploadQueue` could finish polling after 3 s, set `allComplete`, and hide the areas mid-test.

- [ ] **Step 2: Run it and confirm it fails**

```bash
cd /Volumes/Containers/DigniFi/frontend && npx vitest run src/pages/__tests__/DocumentUploadPage.test.tsx
```

Expected: `Tests 1 failed (1)`, with `TestingLibraryElementError: Unable to find an accessible element with the role "heading" and name "Pay stubs"`. The page has no `<h2>` areas yet, and its single zone is named "Drop files here or click to upload".

- [ ] **Step 3: Implement**

Before replacing anything, confirm the starting state:
- `git log --oneline -- frontend/src/pages/DocumentUploadPage.tsx frontend/src/components/documents/` should show nothing after commit 3.
- `git diff -- frontend/src/pages/DocumentUploadPage.tsx frontend/src/components/documents/` should be empty.

If either shows other work, stop and merge it in rather than overwrite it.

**3a.** Replace the whole of `frontend/src/components/documents/FileDropZone.tsx`:

```tsx
import { useRef } from 'react';

interface FileDropZoneProps {
  label: string;
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}

const ACCEPTED_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
const ACCEPTED_EXTS = '.pdf,.jpg,.jpeg,.png';

export function FileDropZone({ label, onFiles, disabled }: FileDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (disabled) return;
    const files = Array.from(e.dataTransfer.files).filter((f) => ACCEPTED_TYPES.includes(f.type));
    if (files.length) onFiles(files);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) onFiles(files);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`${label}: drop files here or click to upload`}
      aria-disabled={disabled}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={() => !disabled && inputRef.current?.click()}
      onKeyDown={(e) => {
        if (disabled) return;
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
      className="file-drop-zone"
    >
      <p>Drop PDF, JPEG, or PNG files here</p>
      <p className="text-muted">or click to browse</p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTS}
        multiple
        hidden
        disabled={disabled}
        onChange={handleChange}
      />
    </div>
  );
}
```

**3b.** Replace the whole of `frontend/src/pages/DocumentUploadPage.tsx`. Only `UPLOAD_AREAS`, `UploadType`, the `documentType` parameter, the `areas` block and the two `{… && areas}` lines change. Everything else is the commit-3 file verbatim.

Copy notes for the help text:
- The credit-report help is §5 verbatim.
- For bills and pay stubs, §5 gives only the tail of each sentence (the cells start with "…"). The lead-ins, "Bills or statements for money you owe. What we find" and "Recent pay stubs from your job. Your employer's name and your pay before taxes are", come from the upload-page designer's copy in the 2026-10-09 design workflow. The reviewer revised that copy to the tails in §5.
- Measured on the repo's Flesch-Kincaid formula, the three help strings score grade 2.4, 4.8 and 4.0; the limit is 9.

```tsx
import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileDropZone } from '../components/documents/FileDropZone';
import { UploadQueue } from '../components/documents/UploadQueue';
import { uploadDocument } from '../api/client';
import { useIntake } from '../context/IntakeContext';
import type { UploadedDocument } from '../types/api';

const ILND_DISTRICT_ID = 1;

const UPLOAD_AREAS = [
  {
    type: 'creditor_bill',
    label: 'Bills and statements',
    help: 'Bills or statements for money you owe. What we find will show up in the Amounts Owed step, marked "From scan." You can check or change it there.',
  },
  {
    type: 'pay_stub',
    label: 'Pay stubs',
    help: "Recent pay stubs from your job. Your employer's name and your pay before taxes are used for your income form (Schedule I).",
  },
  {
    type: 'credit_report',
    label: 'Credit report',
    help: 'Accounts with a balance will show up in the Amounts Owed step, marked "From scan." If you also uploaded a bill for the same account, it may show up twice. We may miss some, so please check that list.',
  },
] as const;

type UploadType = (typeof UPLOAD_AREAS)[number]['type'];

interface QueuedUpload {
  docId: number;
  filename: string;
  doc: UploadedDocument | null;
}

export function DocumentUploadPage() {
  const navigate = useNavigate();
  const { session, isLoading, createSession } = useIntake();

  // Auto-create a session for new users who arrive here before the intake wizard.
  useEffect(() => {
    if (!isLoading && !session) {
      createSession(ILND_DISTRICT_ID).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading]);
  const [queue, setQueue] = useState<QueuedUpload[]>([]);
  const [uploading, setUploading] = useState(false);
  const [allComplete, setAllComplete] = useState(false);
  const [summary, setSummary] = useState<string>('');
  const [error, setError] = useState<string>('');

  const handleFiles = useCallback(
    async (files: File[], documentType: UploadType) => {
      if (!session?.id) {
        setError('No active session. Please start from the beginning.');
        return;
      }
      setUploading(true);
      setError('');

      const newItems: QueuedUpload[] = [];
      for (const file of files) {
        try {
          const res = await uploadDocument(session.id, file, documentType);
          newItems.push({ docId: res.id, filename: file.name, doc: null });
        } catch {
          setError(`Failed to upload ${file.name}.`);
        }
      }
      setQueue((prev) => [...prev, ...newItems]);
      setUploading(false);
    },
    [session]
  );

  const handleAllComplete = useCallback((docs: UploadedDocument[]) => {
    setAllComplete(true);
    const bills = docs.filter((d) => d.document_type === 'creditor_bill').length;
    const stubs = docs.filter((d) => d.document_type === 'pay_stub').length;
    const parts: string[] = [];
    if (bills) parts.push(`${bills} creditor bill${bills > 1 ? 's' : ''}`);
    if (stubs) parts.push(`${stubs} pay stub${stubs > 1 ? 's' : ''}`);
    setSummary(parts.length ? `Found: ${parts.join(', ')}.` : 'Processing complete.');
  }, []);

  const isEmpty = queue.length === 0 && !uploading;

  const areas = UPLOAD_AREAS.map((area) => (
    <section key={area.type} aria-labelledby={`upload-area-${area.type}`}>
      <h2 id={`upload-area-${area.type}`}>{area.label}</h2>
      <p>{area.help}</p>
      <FileDropZone
        label={area.label}
        onFiles={(files) => handleFiles(files, area.type)}
        disabled={uploading || !session}
      />
    </section>
  ));

  return (
    <main className="document-page">
      <h1>Upload your documents</h1>
      <p>
        Upload paystubs, creditor bills, and other supporting documents. We&apos;ll extract the
        information and pre-fill your intake forms &mdash; you can review and correct anything
        before submitting.
      </p>
      <p className="text-muted">
        To read your documents, we send them to OpenAI, an outside AI service. If you&apos;d
        rather not, you can skip this step and type your information in by hand.
      </p>

      {error && (
        <p role="alert" className="text-error">
          {error}
        </p>
      )}

      {isEmpty && areas}

      {queue.length > 0 && (
        <>
          <UploadQueue items={queue} onAllComplete={handleAllComplete} />
          {!allComplete && areas}
        </>
      )}

      {allComplete && summary && (
        <p role="status" className="text-success">
          {summary}
        </p>
      )}

      <div className="page-actions">
        <button
          onClick={() => navigate('/intake')}
          disabled={uploading}
          className="button button--primary button--md"
        >
          {allComplete ? 'Continue' : 'Skip for now'}
        </button>
      </div>
    </main>
  );
}
```

**3c.** In `frontend/src/test/mocks/handlers.ts`, insert this block between the debts handler and `// -- Forms`. The surrounding lines are shown for placement:

```ts
  http.post(`${API}/intake/debts/`, () =>
    HttpResponse.json({ id: 1, session: 1, debt_type: 'credit_card', creditor_name: 'Visa' })
  ),

  // -- Documents -----------------------------------------------------------

  http.post(`${API}/documents/upload/`, () =>
    HttpResponse.json({ id: 1, status: 'processing' }, { status: 202 })
  ),

  http.get(`${API}/documents/:id/`, ({ params }) =>
    HttpResponse.json({
      id: Number(params.id),
      document_type: 'creditor_bill',
      original_filename: 'bill.pdf',
      uploaded_at: '2026-01-20T10:00:00Z',
      ocr_result: {
        status: 'completed',
        failure_reason: '',
        confidence_scores: {},
        overall_confidence: 0.9,
        user_validated: false,
      },
    })
  ),

  // -- Forms ---------------------------------------------------------------
```

(Without the GET default, a poll from any test goes to the real `localhost:8000`, because `onUnhandledRequest` is only `'warn'`.) Both `ocr_result` bodies, here and in the Step 1 override, use the C4 shape that Task 8 (commit 9) gave the API and `types/api.ts`: `failure_reason`, and no `extracted_data` or `error_message`.

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd /Volumes/Containers/DigniFi/frontend
npx vitest run src/pages/__tests__/DocumentUploadPage.test.tsx   # Tests 1 passed (1)
npx vitest run                                                   # every file passes (25 files / 210 tests when drafted on the pre-Task-1 tree; the count grows with earlier tasks)
npx tsc -b                                                       # exit 0
npm run lint                                                     # eslint . — exit 0, no output
cd /Volumes/Containers/DigniFi && git grep -n "Drop files here or click to upload" -- frontend/e2e frontend/src
```

The last command must print nothing and exit 1. Use `git grep`, not `grep`: here `grep` is aliased to `rg` (which reads `-r` as `--replace`), and `rtk` rewrites `grep` output. Before this task, the old fixed name appeared only at `FileDropZone.tsx:29`. If a page object written in an earlier task (for example `e2e/pages/documents.page.ts`) still locates a zone by that name, change it in this same commit to `` `Bills and statements: drop files here or click to upload` ``, or the area matching the document, and stage it with the files below.

`tsc -b` does not type-check test files: `tsconfig.app.json` excludes `*.test.tsx`. Checking the tests separately turned up 20 type errors that already exist in other test files. None are in the files this task touches, and this task doesn't chase them.

- [ ] **Step 5: Update CLAUDE.md gotchas**

Append these two bullets as the last items of the `## Gotchas (things agents get wrong)` list, directly above `## Architecture (quick)`:

```markdown
- **Upload areas decide the document type** — `DocumentUploadPage`'s `UPLOAD_AREAS` maps "Bills and statements" → `creditor_bill`, "Pay stubs" → `pay_stub`, "Credit report" → `credit_report`. The backend stores whatever type is sent (`user_declared_type`) and never classifies. Each `FileDropZone` is named `${label}: drop files here or click to upload` with its file input inside, and E2E locates zones by that name.
- **MSW can't parse jsdom uploads with `request.formData()`** — undici rejects jsdom's `File` (`AssertionError … webidl.is.File`). Read multipart fields from `await request.text()`, as `sentDocumentType` in `DocumentUploadPage.test.tsx` does.
```

- [ ] **Step 6: Commit**

```bash
cd /Volumes/Containers/DigniFi
git add frontend/src/components/documents/FileDropZone.tsx frontend/src/pages/DocumentUploadPage.tsx frontend/src/test/mocks/handlers.ts frontend/src/pages/__tests__/DocumentUploadPage.test.tsx
git diff CLAUDE.md
git add CLAUDE.md
git diff --cached --stat
git commit -m "feat(frontend): give bills, pay stubs and credit reports their own upload areas"
```

Staging rules:
- **`git diff CLAUDE.md` before `git add CLAUDE.md`:** it must show only this task's Step 5 hunk, the two added bullets. Tasks 1–2 committed every other `CLAUDE.md` change, and Tasks 3–12 committed their own. If anything else appears, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it.
- **`git diff --cached --stat`** must list exactly the four frontend files and `CLAUDE.md`. Never stage `.serena/`, `DESIGN.md`, `assets/`, `.impeccable` or the README landing-image hunk.
- **Pre-commit:**
  - Prettier may reformat on the first attempt. If it does, re-run the same `git add` lines (including `git add CLAUDE.md`) and commit again.
  - ESLint runs with `--max-warnings=0`; these files lint clean.
- **Message:** exactly the line above, with no trailer.

---

### Task 14: Show each file's real outcome and let the filer retry  (Commit #15 in spec §9)

This task fixes DIG-5 and DIG-13. The problems today:
- During an upload the page goes blank.
- A failed check leaves a row on "Processing…" forever, because `UploadQueue.tsx:32-33` clears the interval without setting any state.
- The summary counts failed files ("Found: 5 creditor bills." with 3 failed).
- Once every row is final, the drop zone hides, so a filer can't retry.

What this task does:
- **Rows are owned by the page.** A row appears the moment a file is chosen. Files send one at a time. Each row checks its own status, and failures read from `failure_reason` plus the area's type.
- **Areas always stay visible.** The summary counts only files that were read.
- **The button** reads "Skip for now" until a file is read, then "Continue", and is disabled only while a file is sending.
- **The page copy** drops the review promise and any promise about Income pre-fill. The OpenAI disclosure stays word for word.
- **`uploadDocument`** survives an expired access token.

**Files:**
- Modify: `frontend/src/api/client.ts:618-636`, the `uploadDocument` body. Anchor on `export async function uploadDocument(`. For reference: `attemptTokenRefresh` is at :125-148, `APIClientError` at :82-92, and the 401 pattern copied from `downloadForm` at :587-611. `pollDocument` (:638-640) is not changed.
- Modify: `frontend/src/components/documents/FileDropZone.tsx` `handleChange` (lines 22-25 as Task 13 leaves the file).
- Modify: `frontend/src/components/documents/UploadQueue.tsx:1-69` (whole-file replacement).
- Modify: `frontend/src/pages/DocumentUploadPage.tsx` (whole-file replacement of the Task 13 version).
- Modify: `CLAUDE.md`. Append to the end of the Gotchas list, above `## Architecture (quick)`.
- Test: `frontend/src/pages/__tests__/DocumentUploadPage.test.tsx` (whole-file replacement; Task 13's test is kept inside it).

**Interfaces:**
- Consumes:
  - Task 13: `UPLOAD_AREAS`, `UploadType`, `FileDropZone` `label`/`disabled`, and the MSW document handlers (whose `GET /documents/:id/` default already returns the C4 `ocr_result` shape).
  - Task 8 (commit 9): `_serialize_ocr` returns `status`, `failure_reason`, `confidence_scores`, `overall_confidence` and `user_validated`, and no `error_message` or `extracted_data`. The `failure_reason` values are `'nothing_found' | 'processing_error'` (C2).
  - **C4 from Task 8 (commit 9)** in `frontend/src/types/api.ts`: `export type OCRFailureReason = 'nothing_found' | 'processing_error'`, and `OCRResult` = `{ status: OCRStatus; failure_reason: OCRFailureReason | ''; confidence_scores: Record<string, number>; overall_confidence: number; user_validated: boolean }`. This task does not edit `types/api.ts`.
  - `pollDocument(id: number): Promise<UploadedDocument>` (unchanged; still `apiFetch` → `withRetry`, which retries 5xx and network errors 3× at 500/1000/2000 ms and never 429).
  - `attemptTokenRefresh(): Promise<boolean>`, `getRefreshToken()`, and `APIClientError(message: string, statusCode: number)`.
- Produces:
  - **`uploadDocument`:** on a 401 with a refresh token, it calls `attemptTokenRefresh()` once and retries once. Any non-OK result throws `APIClientError` whose `statusCode` is the HTTP status.
  - **`UploadQueue.tsx` exports:**
    - `type UploadStatus = 'waiting' | 'uploading' | 'checking' | 'done' | 'failed' | 'not_uploaded' | 'unchecked'`
    - `interface QueueItem { key: number; filename: string; documentType: string; docId: number | null; status: UploadStatus; failureReason: OCRFailureReason | ''; wrongFileType: boolean }`
    - `UploadQueue({ items, onSettled })`, where `onSettled: (key: number, patch: Partial<QueueItem>) => void` must be stable (the page passes a `useCallback` with `[]` deps).
  - **Final locator contract** (spec §4.10), for C9 `DocumentsPage`:
    - zones named `${label}: drop files here or click to upload`, each with its file input inside;
    - `<ul aria-label="Upload queue">`;
    - a read row's text "✓ Done";
    - `<h1>Upload your documents</h1>`;
    - the `role="alert"` region;
    - the button "Skip for now" / "Continue".
  - **For `expectDone()`:** use `await expect(page.getByRole('list', { name: 'Upload queue' })).toContainText('Done')`.

- [ ] **Step 1: Write the failing test**

Replace the whole of `frontend/src/pages/__tests__/DocumentUploadPage.test.tsx`:

```tsx
import { render, screen, waitFor, fireEvent, within, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { http, HttpResponse, delay } from 'msw';
import { server } from '../../test/mocks/server';
import { IntakeProvider } from '../../context/IntakeContext';
import { setAccessToken } from '../../api/client';
import { DocumentUploadPage } from '../DocumentUploadPage';

const API = 'http://localhost:8000/api';
const UPLOAD = `${API}/documents/upload/`;
const DOCUMENT = `${API}/documents/:id/`;

const COULD_NOT_READ =
  "We couldn't read this file. You can try again, or type the details in yourself in a later step.";
const UNCHECKED =
  "We couldn't check on this file. If we read it, what we found will still be used.";

function renderUploadPage() {
  return render(
    <MemoryRouter initialEntries={['/documents']}>
      <IntakeProvider>
        <Routes>
          <Route path="/documents" element={<DocumentUploadPage />} />
          <Route path="/intake" element={<h1>Intake wizard</h1>} />
        </Routes>
      </IntakeProvider>
    </MemoryRouter>
  );
}

function dropZone(label: string) {
  return screen.getByRole('button', { name: `${label}: drop files here or click to upload` });
}

/** Under real timers: wait until the session exists and the area's zone takes files. */
async function readyZone(label: string) {
  await waitFor(() => expect(dropZone(label)).toHaveAttribute('aria-disabled', 'false'));
  return dropZone(label);
}

function dropFiles(zone: HTMLElement, ...files: File[]) {
  fireEvent.drop(zone, { dataTransfer: { files } });
}

function pdf(name: string) {
  return new File(['%PDF-1.4'], name, { type: 'application/pdf' });
}

// undici's request.formData() rejects jsdom's File, so read the field from the multipart text.
async function sentDocumentType(request: Request) {
  const body = await request.text();
  return /name="document_type"\r\n\r\n([^\r\n]*)/.exec(body)?.[1] ?? '';
}

type Outcome = { status: 'completed' | 'failed' | 'processing'; failure_reason?: string };

function documentReply(id: number, outcome: Outcome) {
  return HttpResponse.json({
    id,
    document_type: 'creditor_bill',
    original_filename: 'file.pdf',
    uploaded_at: '2026-01-20T10:00:00Z',
    ocr_result: {
      failure_reason: '',
      confidence_scores: {},
      overall_confidence: 0,
      user_validated: false,
      ...outcome,
    },
  });
}

/**
 * Uploads get ids 1, 2, 3, ... in the order they are sent; a document's status
 * answers with outcomes[id], or completed when it is not listed.
 * Returns the document types sent, in order.
 */
function serveDocuments(outcomes: Record<number, Outcome> = {}) {
  const sentTypes: string[] = [];
  server.use(
    http.post(UPLOAD, async ({ request }) => {
      sentTypes.push(await sentDocumentType(request));
      return HttpResponse.json({ id: sentTypes.length, status: 'processing' }, { status: 202 });
    }),
    http.get(DOCUMENT, ({ params }) => {
      const id = Number(params.id);
      return documentReply(id, outcomes[id] ?? { status: 'completed' });
    })
  );
  return sentTypes;
}

afterEach(() => {
  setAccessToken(null);
});

describe('DocumentUploadPage', () => {
  it('sends each area its own document type, so a pay stub is never filed as a bill', async () => {
    const sentTypes = serveDocuments();
    renderUploadPage();
    expect(screen.getByRole('heading', { level: 2, name: 'Pay stubs' })).toBeInTheDocument();

    dropFiles(await readyZone('Bills and statements'), pdf('electric-bill.pdf'));
    await waitFor(() => expect(sentTypes).toHaveLength(1));
    dropFiles(await readyZone('Pay stubs'), pdf('pay-stub.pdf'));
    await waitFor(() => expect(sentTypes).toHaveLength(2));
    dropFiles(await readyZone('Credit report'), pdf('credit-report.pdf'));
    await waitFor(() => expect(sentTypes).toHaveLength(3));

    expect(sentTypes).toEqual(['creditor_bill', 'pay_stub', 'credit_report']);
  });

  it('counts only the files that were read in the summary, in plain words', async () => {
    serveDocuments({ 1: { status: 'failed', failure_reason: 'nothing_found' } });
    renderUploadPage();

    dropFiles(await readyZone('Bills and statements'), pdf('cover-page.pdf'), pdf('statement.pdf'));
    await waitFor(() => expect(screen.getAllByText('✓ Done')).toHaveLength(1));
    dropFiles(await readyZone('Pay stubs'), pdf('june-stub.pdf'), pdf('july-stub.pdf'));

    expect(await screen.findByRole('status')).toHaveTextContent(
      'We read 1 bill or statement and 2 pay stubs.'
    );
  });

  it.each([
    {
      area: 'Bills and statements',
      why: 'nothing was found',
      outcome: { status: 'failed', failure_reason: 'nothing_found' },
      says: "We couldn't find the name of the company you owe in this file. You can upload a different page, or add this bill yourself in a later step.",
    },
    {
      area: 'Pay stubs',
      why: 'nothing was found',
      outcome: { status: 'failed', failure_reason: 'nothing_found' },
      says: "We couldn't find the pay amount and pay dates in this file. You can upload a different page, or type your income in yourself in a later step.",
    },
    {
      area: 'Credit report',
      why: 'nothing was found',
      outcome: { status: 'failed', failure_reason: 'nothing_found' },
      says: "We couldn't find any accounts in this file. You can upload a different file, or add your bills yourself in a later step.",
    },
    {
      area: 'Bills and statements',
      why: 'reading broke',
      outcome: { status: 'failed', failure_reason: 'processing_error' },
      says: COULD_NOT_READ,
    },
    {
      area: 'Pay stubs',
      why: 'an older failure has no reason',
      outcome: { status: 'failed', failure_reason: '' },
      says: COULD_NOT_READ,
    },
  ] as { area: string; why: string; outcome: Outcome; says: string }[])(
    'tells the filer in plain words why a file in $area was not read when $why',
    async ({ area, outcome, says }) => {
      serveDocuments({ 1: outcome });
      renderUploadPage();

      dropFiles(await readyZone(area), pdf('scan.pdf'));

      expect(await screen.findByText(says)).toBeInTheDocument();
    }
  );

  it('says a refused file did not upload, and asks for a PDF, JPEG or PNG only on a 400', async () => {
    let posts = 0;
    server.use(
      http.post(UPLOAD, () => {
        posts += 1;
        return posts === 1
          ? HttpResponse.json({ error: 'Unsupported file type' }, { status: 400 })
          : HttpResponse.json({ error: 'Bad gateway' }, { status: 502 });
      })
    );
    renderUploadPage();

    dropFiles(await readyZone('Bills and statements'), pdf('first.pdf'), pdf('second.pdf'));

    expect(
      await screen.findByText(
        "This file didn't upload. You can try again. Please use a PDF, JPEG, or PNG file."
      )
    ).toBeInTheDocument();
    expect(
      await screen.findByText("This file didn't upload. You can try again.")
    ).toBeInTheDocument();
  });

  it('lists every chosen file at once, before its upload finishes', async () => {
    let release!: () => void;
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    let sent = 0;
    server.use(
      http.post(UPLOAD, async () => {
        await held;
        sent += 1;
        return HttpResponse.json({ id: sent, status: 'processing' }, { status: 202 });
      })
    );
    renderUploadPage();

    dropFiles(await readyZone('Bills and statements'), pdf('january.pdf'), pdf('february.pdf'));

    const queue = screen.getByRole('list', { name: 'Upload queue' });
    expect(within(queue).getByText('january.pdf')).toBeInTheDocument();
    expect(within(queue).getByText('february.pdf')).toBeInTheDocument();
    expect(within(queue).getByText('Reading your file…')).toBeInTheDocument();
    expect(within(queue).getByText('Waiting…')).toBeInTheDocument();
    expect(dropZone('Pay stubs')).toHaveAttribute('aria-disabled', 'true');
    expect(screen.getByRole('button', { name: 'Skip for now' })).toBeDisabled();

    release();

    await waitFor(() => expect(within(queue).getAllByText('✓ Done')).toHaveLength(2));
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled();
  });

  it('sends files one at a time and ignores a drop while a file is sending', async () => {
    let inFlight = 0;
    let maxInFlight = 0;
    let sent = 0;
    server.use(
      http.post(UPLOAD, async () => {
        sent += 1;
        inFlight += 1;
        maxInFlight = Math.max(maxInFlight, inFlight);
        await delay(30);
        inFlight -= 1;
        return HttpResponse.json({ id: sent, status: 'processing' }, { status: 202 });
      })
    );
    renderUploadPage();

    dropFiles(await readyZone('Bills and statements'), pdf('a.pdf'), pdf('b.pdf'), pdf('c.pdf'));
    dropFiles(dropZone('Pay stubs'), pdf('stub.pdf'));

    await waitFor(() => expect(screen.getAllByText('✓ Done')).toHaveLength(3));
    expect(sent).toBe(3);
    expect(maxInFlight).toBe(1);
    expect(screen.queryByText('stub.pdf')).not.toBeInTheDocument();
  });

  it('reads "Skip for now" until a file is read, then "Continue"', async () => {
    serveDocuments({ 1: { status: 'failed', failure_reason: 'nothing_found' } });
    renderUploadPage();
    expect(screen.getByRole('button', { name: 'Skip for now' })).toBeInTheDocument();

    dropFiles(await readyZone('Bills and statements'), pdf('cover-page.pdf'));
    await screen.findByText(/We couldn't find the name of the company you owe/);
    expect(screen.getByRole('button', { name: 'Skip for now' })).toBeEnabled();

    // The areas stay on the page after a batch, so the filer can send another file.
    dropFiles(await readyZone('Bills and statements'), pdf('statement.pdf'));
    await screen.findByText('✓ Done');
    expect(screen.getByRole('button', { name: 'Continue' })).toBeEnabled();
    expect(screen.queryByRole('button', { name: 'Skip for now' })).not.toBeInTheDocument();
  });

  it('lets the filer choose the same file again after it could not be read', async () => {
    serveDocuments({ 1: { status: 'failed', failure_reason: 'processing_error' } });
    const user = userEvent.setup();
    renderUploadPage();
    const file = pdf('bill.pdf');

    const zone = await readyZone('Bills and statements');
    const input = zone.querySelector<HTMLInputElement>('input[type="file"]')!;
    await user.upload(input, file);
    await screen.findByText(COULD_NOT_READ);

    await readyZone('Bills and statements');
    await user.upload(input, file);

    expect(await screen.findByText('✓ Done')).toBeInTheDocument();
    expect(screen.getAllByText('bill.pdf')).toHaveLength(2);
  });

  it('finishes an upload that starts after the login has expired', async () => {
    setAccessToken('expired-access-token');
    localStorage.setItem('refresh_token', 'mock-refresh-token');
    const authHeaders: (string | null)[] = [];
    server.use(
      http.post(UPLOAD, ({ request }) => {
        const auth = request.headers.get('Authorization');
        authHeaders.push(auth);
        return auth === 'Bearer refreshed-access-token'
          ? HttpResponse.json({ id: 1, status: 'processing' }, { status: 202 })
          : HttpResponse.json(
              { detail: 'Given token not valid for any token type' },
              { status: 401 }
            );
      })
    );
    renderUploadPage();

    dropFiles(await readyZone('Bills and statements'), pdf('bill.pdf'));

    expect(await screen.findByText('✓ Done')).toBeInTheDocument();
    expect(authHeaders).toEqual(['Bearer expired-access-token', 'Bearer refreshed-access-token']);
  });

  it('keeps checking on a file through a busy server instead of stranding it', async () => {
    let checks = 0;
    server.use(
      http.post(UPLOAD, () => HttpResponse.json({ id: 1, status: 'processing' }, { status: 202 })),
      http.get(DOCUMENT, ({ params }) => {
        checks += 1;
        return checks <= 2
          ? HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
          : documentReply(Number(params.id), { status: 'completed' });
      })
    );
    renderUploadPage();
    // Real timers until the page and its session are ready; findBy/waitFor hang under fake timers.
    await screen.findByRole('heading', { level: 1, name: 'Upload your documents' });
    const zone = await readyZone('Bills and statements');

    vi.useFakeTimers();
    try {
      dropFiles(zone, pdf('bill.pdf'));
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(checks).toBe(1);
      expect(screen.getByText('Reading your file…')).toBeInTheDocument();

      await act(async () => {
        await vi.advanceTimersByTimeAsync(6000);
      });
      expect(checks).toBe(2);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(12000);
      });
      expect(checks).toBe(3);
      expect(screen.getByText('✓ Done')).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it('lets the filer move on when a file cannot be checked', async () => {
    server.use(
      http.post(UPLOAD, () => HttpResponse.json({ id: 1, status: 'processing' }, { status: 202 })),
      http.get(DOCUMENT, () =>
        HttpResponse.json({ detail: 'Request was throttled.' }, { status: 429 })
      )
    );
    renderUploadPage();
    await screen.findByRole('heading', { level: 1, name: 'Upload your documents' });
    const zone = await readyZone('Bills and statements');

    vi.useFakeTimers();
    try {
      dropFiles(zone, pdf('bill.pdf'));
      // One second at a time, so each check's reply lands before the clock moves on.
      for (let second = 0; second < 119; second += 1) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(1000);
        });
      }
      expect(screen.getByText('Reading your file…')).toBeInTheDocument();

      for (let second = 0; second < 2; second += 1) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(1000);
        });
      }
      expect(screen.getByText(UNCHECKED)).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }

    // Checking has stopped, so click under real timers: a user-event action hangs under
    // vitest fake timers, because RTL drains it with a setTimeout only a `jest` global advances.
    const button = screen.getByRole('button', { name: 'Skip for now' });
    expect(button).toBeEnabled();
    await userEvent.setup().click(button);
    expect(await screen.findByRole('heading', { name: 'Intake wizard' })).toBeInTheDocument();
  });
});
```

How the spec §8 "Upload page" cases map to these tests:

| Spec case | Test |
| --- | --- |
| each area sends its own type | the first test |
| the summary counts only files that were read | "counts only the files…" |
| each failure gets its own plain reason | the `it.each` table and the not-uploaded 400/502 test |
| rows appear at once | "lists every chosen file at once…" |
| a busy server doesn't strand a file | "keeps checking…" |
| an unchecked file still lets the filer move on | "lets the filer move on…" |
| the button reads "Skip for now" until a file is read | "reads 'Skip for now'…" (it also shows the areas staying visible for a retry) |
| files send one at a time | "sends files one at a time…" |
| an upload after an expired login succeeds | "finishes an upload…" |

There is one extra test, "lets the filer choose the same file again…". It covers the input reset that a same-file retry needs. user-event 14.6.1 skips a selection identical to the input's current files, just as browsers do.

Timer-test pattern, as verified:
- **What matches the spec.** Both timer tests wait for the h1 and the session under real timers, then call `vi.useFakeTimers()`, as spec §8 says.
- **What deviates.** Under fake timers they use `fireEvent` with `act(() => vi.advanceTimersByTimeAsync(ms))` instead of `userEvent.setup({ advanceTimers })`. Every user-event action hangs under vitest fake timers, because RTL's `asyncWrapper` (`@testing-library/react/dist/pure.js:83-103`) drains with a `setTimeout(0)` that it advances only when a `jest` global exists. The "move on" test therefore clicks with a real-timer `userEvent` after `vi.useRealTimers()`, once checking has stopped.
- **Why the 120 s test steps one second at a time.** A single `advanceTimersByTimeAsync(120000)` moves the clock before each check's MSW reply resolves, so the next check is scheduled past the window and the test fails.
- **Runtime.** The whole file runs in about 2.4 s and passed five consecutive runs.

- [ ] **Step 2: Run it and confirm it fails**

```bash
cd /Volumes/Containers/DigniFi/frontend && npx vitest run src/pages/__tests__/DocumentUploadPage.test.tsx
```

Expected: `Tests 14 failed | 1 passed (15)`. Only Task 13's "sends each area its own document type…" passes. Representative failures against the Task 13 code:

| Test | Failure |
| --- | --- |
| "lists every chosen file at once…" | `Unable to find an accessible element with the role "list" and name "Upload queue"`: no rows exist until every POST returns. |
| "keeps checking…" | `AssertionError: expected +0 to be 1`: the old queue waits 3 s before its first check. |
| "lets the filer move on…" | `Unable to find an element with the text: Reading your file…` |
| "sends files one at a time…" | `Unable to find an accessible element with the role "button" and name "Pay stubs: drop files here or click to upload"`: the old page hides every area while uploading with an empty queue. |
| the summary, failure-reason, not-uploaded, Skip/Continue, same-file and expired-login tests | `Error: Test timed out in 5000ms.`: the old queue shows only "✗ Failed", the old summary is "Found: …", and the old `uploadDocument` throws a plain `Error` on a 401. |

- [ ] **Step 3: Implement**

**3a.** No change to `frontend/src/types/api.ts`. Task 8 (commit 9, its Step 3i) already exports `OCRFailureReason` and removed `extracted_data` and `error_message` from `OCRResult` (contract C4). Do not add them again: a second `export type OCRFailureReason` breaks `tsc -b`. Confirm the starting state:

```bash
cd /Volumes/Containers/DigniFi && git grep -n -e "export type OCRFailureReason" -e "failure_reason: OCRFailureReason" -e "extracted_data" -e "error_message" -- frontend/src/types/api.ts
```

Expected: exactly two lines, `export type OCRFailureReason = 'nothing_found' | 'processing_error';` and `failure_reason: OCRFailureReason | '';`. `UploadQueue.tsx`'s `import type { OCRFailureReason } from '../../types/api'` (3d) resolves to that export. `validateDocument` (`client.ts:646`) keeps returning `OCRResult` and has no callers.

**3b.** `frontend/src/api/client.ts`. Replace the whole `uploadDocument` function (currently :618-636) with:

```ts
export async function uploadDocument(
  sessionId: number,
  file: File,
  documentType: string
): Promise<DocumentUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', documentType);
  formData.append('session_id', String(sessionId));

  // Raw fetch, not apiFetch: apiFetch forces Content-Type: application/json, which
  // would replace the multipart boundary the browser sets for FormData.
  const doFetch = () => {
    const token = getAccessToken();
    return fetch(`${API_BASE_URL}/documents/upload/`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    });
  };
  let res = await doFetch();
  // Access tokens last 30 minutes; a filer who lingered gets one refresh and one retry.
  if (res.status === 401 && getRefreshToken()) {
    const refreshed = await attemptTokenRefresh();
    if (refreshed) res = await doFetch();
  }
  if (!res.ok) {
    throw new APIClientError(`Upload failed (${res.status})`, res.status);
  }
  return res.json();
}
```

(`FormData` can be sent twice; each `fetch` serializes it again.)

**3c.** `frontend/src/components/documents/FileDropZone.tsx`. Replace `handleChange`:

```tsx
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (files.length) onFiles(files);
  };
```

with:

```tsx
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    // Clear the pick so choosing the same file again (a retry) fires another change.
    e.target.value = '';
    if (files.length) onFiles(files);
  };
```

**3d.** Replace the whole of `frontend/src/components/documents/UploadQueue.tsx`. Each row checks its own file:
- **Cadence:** the first check is immediate, because the POST returns only after OCR (`documents/views.py:146-149`). Later checks run every 3 s.
- **Backoff:** 6 s, 12 s, 24 s… on 429, 5xx or a network error.
- **Time limit:** "unchecked" exactly 2 minutes after the first check.
- **Other errors** (401 after a failed refresh, 403, 404) go straight to "unchecked".

All failure and "unchecked" copy is §5 verbatim. Not in §5: "Waiting…" and "Reading your file…" (the in-progress labels, taken from the design workflow's row text) and the 2-minute limit value.

```tsx
import { useEffect } from 'react';
import { pollDocument, APIClientError } from '../../api/client';
import type { OCRFailureReason } from '../../types/api';

export type UploadStatus =
  | 'waiting'
  | 'uploading'
  | 'checking'
  | 'done'
  | 'failed'
  | 'not_uploaded'
  | 'unchecked';

export interface QueueItem {
  /** Client-side key: a row exists before the server gives the file an id. */
  key: number;
  filename: string;
  documentType: string;
  docId: number | null;
  status: UploadStatus;
  failureReason: OCRFailureReason | '';
  /** The upload was refused with a 400, which is how the server rejects a file type. */
  wrongFileType: boolean;
}

interface UploadQueueProps {
  items: QueueItem[];
  onSettled: (key: number, patch: Partial<QueueItem>) => void;
}

const CHECK_INTERVAL_MS = 3000;
// The upload POST returns only after the file has been read, so the first check
// is normally the final answer. This ceiling only stops a row from waiting forever.
const GIVE_UP_AFTER_MS = 120000;

const NOTHING_FOUND: Record<string, string> = {
  creditor_bill:
    "We couldn't find the name of the company you owe in this file. You can upload a different page, or add this bill yourself in a later step.",
  pay_stub:
    "We couldn't find the pay amount and pay dates in this file. You can upload a different page, or type your income in yourself in a later step.",
  credit_report:
    "We couldn't find any accounts in this file. You can upload a different file, or add your bills yourself in a later step.",
};

const COULD_NOT_READ =
  "We couldn't read this file. You can try again, or type the details in yourself in a later step.";

function statusText(item: QueueItem): string {
  switch (item.status) {
    case 'waiting':
      return 'Waiting…';
    case 'uploading':
    case 'checking':
      return 'Reading your file…';
    case 'done':
      return '✓ Done';
    case 'failed':
      return (
        (item.failureReason === 'nothing_found' && NOTHING_FOUND[item.documentType]) ||
        COULD_NOT_READ
      );
    case 'not_uploaded':
      return item.wrongFileType
        ? "This file didn't upload. You can try again. Please use a PDF, JPEG, or PNG file."
        : "This file didn't upload. You can try again.";
    case 'unchecked':
      return "We couldn't check on this file. If we read it, what we found will still be used.";
  }
}

function QueueRow({
  item,
  onSettled,
}: {
  item: QueueItem;
  onSettled: UploadQueueProps['onSettled'];
}) {
  const { key, docId, status } = item;

  // Each row checks on its own file, so adding files never restarts another row.
  useEffect(() => {
    if (status !== 'checking' || docId === null) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let busyReplies = 0;
    const startedAt = Date.now();

    const check = async () => {
      let wait = CHECK_INTERVAL_MS;
      try {
        const ocr = (await pollDocument(docId)).ocr_result;
        if (cancelled) return;
        if (ocr?.status === 'completed' || ocr?.status === 'validated') {
          onSettled(key, { status: 'done' });
          return;
        }
        if (ocr?.status === 'failed') {
          onSettled(key, { status: 'failed', failureReason: ocr.failure_reason ?? '' });
          return;
        }
        busyReplies = 0;
      } catch (err) {
        if (cancelled) return;
        const busy =
          !(err instanceof APIClientError) || err.statusCode === 429 || err.statusCode >= 500;
        if (!busy) {
          onSettled(key, { status: 'unchecked' });
          return;
        }
        // Back off on 429, 5xx and network errors: 6 s, 12 s, 24 s, ...
        busyReplies += 1;
        wait = CHECK_INTERVAL_MS * 2 ** busyReplies;
      }
      const elapsed = Date.now() - startedAt;
      if (elapsed >= GIVE_UP_AFTER_MS) {
        onSettled(key, { status: 'unchecked' });
        return;
      }
      timer = setTimeout(check, Math.min(wait, GIVE_UP_AFTER_MS - elapsed));
    };

    check();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [key, docId, status, onSettled]);

  return (
    <li className="upload-queue-item">
      <span>{item.filename}</span>
      <span aria-live="polite">{statusText(item)}</span>
    </li>
  );
}

export function UploadQueue({ items, onSettled }: UploadQueueProps) {
  return (
    <ul aria-label="Upload queue" className="upload-queue">
      {items.map((item) => (
        <QueueRow key={item.key} item={item} onSettled={onSettled} />
      ))}
    </ul>
  );
}
```

**3e.** Replace the whole of `frontend/src/pages/DocumentUploadPage.tsx`.

What changes and what stays:
- `UPLOAD_AREAS` and the auto-create effect are unchanged from Task 13.
- The "No active session" guard is kept.
- Gone: `uploading`, `allComplete`, the `summary` state, `handleAllComplete`, the page-level "Failed to upload X." error and the two show/hide conditions.

Copy:
- The OpenAI disclosure paragraph is kept word for word; prettier only re-wraps it.
- The new intro drops "pre-fill your intake forms" and "you can review and correct anything before submitting". It is the upload-page designer's copy from the 2026-10-09 design workflow.
- The summary wording ("bill or statement" / "bills or statements") comes from the same source.
- Grades on the repo's Flesch-Kincaid formula: intro 1.9, summary 2.3.
- **Owner review needed before merge:** "so you have less to type" is a soft promise, and it isn't true for pay stubs, because the Income step is never pre-filled. Keep the line as written unless the owner changes it; prose is their call.

```tsx
import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileDropZone } from '../components/documents/FileDropZone';
import { UploadQueue, type QueueItem } from '../components/documents/UploadQueue';
import { uploadDocument, APIClientError } from '../api/client';
import { useIntake } from '../context/IntakeContext';

const ILND_DISTRICT_ID = 1;

const UPLOAD_AREAS = [
  {
    type: 'creditor_bill',
    label: 'Bills and statements',
    help: 'Bills or statements for money you owe. What we find will show up in the Amounts Owed step, marked "From scan." You can check or change it there.',
  },
  {
    type: 'pay_stub',
    label: 'Pay stubs',
    help: "Recent pay stubs from your job. Your employer's name and your pay before taxes are used for your income form (Schedule I).",
  },
  {
    type: 'credit_report',
    label: 'Credit report',
    help: 'Accounts with a balance will show up in the Amounts Owed step, marked "From scan." If you also uploaded a bill for the same account, it may show up twice. We may miss some, so please check that list.',
  },
] as const;

type UploadType = (typeof UPLOAD_AREAS)[number]['type'];

/** How the summary names what was read, as [one, many]. */
const READ_NAMES: Record<UploadType, [string, string]> = {
  creditor_bill: ['bill or statement', 'bills or statements'],
  pay_stub: ['pay stub', 'pay stubs'],
  credit_report: ['credit report', 'credit reports'],
};

/** "We read 2 bills or statements and 1 pay stub." Only files that were read count. */
function readSummary(queue: QueueItem[]): string {
  const parts = UPLOAD_AREAS.flatMap(({ type }) => {
    const count = queue.filter(
      (item) => item.documentType === type && item.status === 'done'
    ).length;
    if (!count) return [];
    const [one, many] = READ_NAMES[type];
    return [`${count} ${count === 1 ? one : many}`];
  });
  if (!parts.length) return '';
  const last = parts.pop();
  return `We read ${parts.length ? `${parts.join(', ')} and ${last}` : last}.`;
}

export function DocumentUploadPage() {
  const navigate = useNavigate();
  const { session, isLoading, createSession } = useIntake();

  // Auto-create a session for new users who arrive here before the intake wizard.
  useEffect(() => {
    if (!isLoading && !session) {
      createSession(ILND_DISTRICT_ID).catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [error, setError] = useState<string>('');
  const nextKey = useRef(1);

  const updateItem = useCallback((key: number, patch: Partial<QueueItem>) => {
    setQueue((prev) => prev.map((item) => (item.key === key ? { ...item, ...patch } : item)));
  }, []);

  const handleFiles = async (files: File[], documentType: UploadType) => {
    if (!session?.id) {
      setError('No active session. Please start from the beginning.');
      return;
    }
    setError('');

    // Every chosen file gets a row straight away, before anything is sent.
    const added: QueueItem[] = files.map((file) => ({
      key: nextKey.current++,
      filename: file.name,
      documentType,
      docId: null,
      status: 'waiting',
      failureReason: '',
      wrongFileType: false,
    }));
    setQueue((prev) => [...prev, ...added]);

    // One file at a time: each upload holds a server worker until the file is read.
    for (const [index, file] of files.entries()) {
      const { key } = added[index];
      updateItem(key, { status: 'uploading' });
      try {
        const res = await uploadDocument(session.id, file, documentType);
        updateItem(key, { status: 'checking', docId: res.id });
      } catch (err) {
        updateItem(key, {
          status: 'not_uploaded',
          wrongFileType: err instanceof APIClientError && err.statusCode === 400,
        });
      }
    }
  };

  const sending = queue.some((item) => item.status === 'waiting' || item.status === 'uploading');
  const settled = queue.every(
    (item) => item.status !== 'waiting' && item.status !== 'uploading' && item.status !== 'checking'
  );
  const anyRead = queue.some((item) => item.status === 'done');
  const summary = settled ? readSummary(queue) : '';

  return (
    <main className="document-page">
      <h1>Upload your documents</h1>
      <p>
        You can upload bills, pay stubs, and a credit report. We&apos;ll try to read them so you
        have less to type. This step is optional.
      </p>
      <p className="text-muted">
        To read your documents, we send them to OpenAI, an outside AI service. If you&apos;d rather
        not, you can skip this step and type your information in by hand.
      </p>

      {error && (
        <p role="alert" className="text-error">
          {error}
        </p>
      )}

      {UPLOAD_AREAS.map((area) => (
        <section key={area.type} aria-labelledby={`upload-area-${area.type}`}>
          <h2 id={`upload-area-${area.type}`}>{area.label}</h2>
          <p>{area.help}</p>
          <FileDropZone
            label={area.label}
            onFiles={(files) => handleFiles(files, area.type)}
            disabled={sending || !session}
          />
        </section>
      ))}

      {queue.length > 0 && <UploadQueue items={queue} onSettled={updateItem} />}

      {summary && (
        <p role="status" className="text-success">
          {summary}
        </p>
      )}

      <div className="page-actions">
        <button
          onClick={() => navigate('/intake')}
          disabled={sending}
          className="button button--primary button--md"
        >
          {anyRead ? 'Continue' : 'Skip for now'}
        </button>
      </div>
    </main>
  );
}
```

**3f.** No change to `frontend/src/test/mocks/handlers.ts`. Task 13 (commit 14) already wrote its `GET /documents/:id/` default with the C4 `ocr_result` shape (`failure_reason: ''`, no `extracted_data` or `error_message`).

- [ ] **Step 4: Run tests and confirm they pass**

```bash
cd /Volumes/Containers/DigniFi/frontend
npx vitest run src/pages/__tests__/DocumentUploadPage.test.tsx   # Tests 15 passed (15), ~2.5 s
npx vitest run                                                   # every file passes (25 files / 224 tests when drafted on the pre-Task-1 tree; the count grows with earlier tasks)
npx tsc -b                                                       # exit 0
npm run lint                                                     # eslint . — exit 0, no output
```

Run the page test file at least three times. It passed five runs in a row when drafted. A flake here means a timer test has started using `findBy`/`waitFor` or `userEvent` under fake timers.

- [ ] **Step 5: Update CLAUDE.md gotchas**

Append these four bullets as the last items of the `## Gotchas (things agents get wrong)` list, directly above `## Architecture (quick)` and after Task 13's two upload bullets:

```markdown
- **Upload page locator contract** — E2E depends on each zone's name `${label}: drop files here or click to upload` (file input inside), `<ul aria-label="Upload queue">`, a read row's "✓ Done", the h1 "Upload your documents", the `role="alert"` region, and the button reading exactly "Skip for now" until a file is read, then "Continue". Don't reword them.
- **Upload rows check themselves** — each `UploadQueue` row polls its document at once, then every 3 s, waits 6 s, 12 s, 24 s… on 429/5xx/network errors, and shows "unchecked" after 2 minutes. `pollDocument` still goes through `apiFetch`'s `withRetry`, so a 5xx is retried 3× inside each check. The page reads only `status`, `failure_reason` and the area's type, never `error_message`. Files send one at a time; areas and the button are disabled only while a file is sending, not while rows are checking.
- **`uploadDocument` uses raw `fetch`** — `apiFetch` forces `Content-Type: application/json`, which breaks the multipart boundary. It handles its own 401 (one `attemptTokenRefresh()`, one retry) and throws `APIClientError` with the HTTP status; a 400 is how the server refuses a file type.
- **user-event hangs under vitest fake timers** — RTL's `asyncWrapper` drains every user-event action with a `setTimeout(0)` that only a `jest` global advances, so `userEvent.setup({ advanceTimers })` doesn't help. Under `vi.useFakeTimers()` use `fireEvent` + `act(() => vi.advanceTimersByTimeAsync(ms))`, step the clock in ≤1 s increments when each timer's reply schedules the next one, and switch back to real timers before any `userEvent` action, `findBy` or `waitFor`.
```

- [ ] **Step 6: Commit**

```bash
cd /Volumes/Containers/DigniFi
git add frontend/src/api/client.ts frontend/src/components/documents/FileDropZone.tsx frontend/src/components/documents/UploadQueue.tsx frontend/src/pages/DocumentUploadPage.tsx frontend/src/pages/__tests__/DocumentUploadPage.test.tsx
git diff CLAUDE.md
git add CLAUDE.md
git diff --cached --stat
git commit -m "fix(frontend): show each file's real outcome and let the filer retry"
```

Staging rules:
- **Before the first `git add`,** run `git diff -- frontend/src/api/client.ts frontend/src/types/api.ts frontend/src/test/mocks/handlers.ts`. `client.ts` must show only the `uploadDocument` hunk from Step 3b, and `types/api.ts` and `handlers.ts` must show nothing (this task does not edit them). If anything else appears, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it.
- **`git diff CLAUDE.md` before `git add CLAUDE.md`:** it must show only this task's Step 5 hunk, the four added bullets. Tasks 1–2 committed every other `CLAUDE.md` change, and Tasks 3–13 committed their own. If anything else appears, stop and ask the owner.
- **`git diff --cached --stat`** must list exactly the five frontend files and `CLAUDE.md`. Never stage `.serena/`, `DESIGN.md`, `assets/`, `.impeccable` or the README landing-image hunk.
- **Pre-commit:**
  - If prettier reformats on the first attempt, re-run the same `git add` lines (including `git add CLAUDE.md`) and commit again.
  - ESLint runs `--max-warnings=0` on the staged files; they lint clean.
- **Message:** exactly the line above, with no trailer.

---

### Task 15: Follow a scanned bill from upload to Amounts Owed  (Commit #16 in spec §9)

Spec §4.12 (DIG-1, DIG-6). Commits 2–15 repaired each step of the upload path. Until now no test has followed one file through all of them in a real browser against the real backend. This task adds that journey:

1. A filer registers, finishes step 1 and lands on the upload page.
2. They upload a photo of a bill and see "✓ Done".
3. They continue through Income, Expenses and Assets.
4. At Amounts Owed the creditor, debt type and amount are already filled in.
5. They save, reload, and the same values are there.

Only OpenAI is replaced: the spec starts a local fake on `127.0.0.1:4010`, and the backend reaches it through `OPENAI_BASE_URL`.

**Verified before writing this task:**

- **`OpenAIProvider` needs no change.** `backend/apps/documents/services/providers/openai_provider.py:28` builds the client as `OpenAI(api_key=os.environ["OPENAI_API_KEY"])` and passes no `base_url`. When `base_url is None`, the installed SDK (openai 1.60.0, `openai/_client.py:125-128`) falls back to `os.environ.get("OPENAI_BASE_URL")`. With `OPENAI_BASE_URL=http://127.0.0.1:4010/v1` exported, `OpenAI(api_key="x").base_url` printed `http://127.0.0.1:4010/v1/`.
- **An empty `OPENAI_BASE_URL` breaks every call.** With `OPENAI_BASE_URL=` (empty), the SDK uses `''` as the base URL instead of falling back to `api.openai.com`, so every request fails. Step 5 records this as a gotcha.
- **The fake works with the real SDK and processor.** The fake in Step 3b answered today's real `DocumentProcessor` and real `OpenAIProvider`, processing `synthetic-bill.png` as `image/png` with doc type `creditor_bill`. Result: `error == ""`, `fields == {creditor_name: "Lakeside Example Clinic", account_number: "4821", amount_owed: "1247.83", minimum_payment: "65.00", due_date: "2026-10-15", creditor_type: "medical"}`, `confidence == {"overall": 92}`, and the fake counted 1 completion. `close()` returned in about 1 ms, and port 4010 could be bound again right after.
- **Why a PNG and not a PDF:** an image goes straight to vision (`processor.py:56-57` → `_process_image`). The opendataloader JVM never starts, so the E2E job needs no JRE. PDF page handling is covered by the backend's `test_processing_outcomes.py` (Task 5).
- **Resolving the fixture path:** `frontend/package.json` has `"type": "module"`, so the spec resolves the fixture with `fileURLToPath(new URL('../fixtures/synthetic-bill.png', import.meta.url))`. This was verified under Playwright 1.58.2 in a `type: module` package. `__dirname` does not exist there.
- **Skip and fail behaviour:**
  - Run without the wiring, the journey printed `[scanned-bill-journey] skipped. To run it, …` and reported `1 skipped`. The list reporter prints test stdout but not skip annotations, which is why the reason is also written with `console.warn`.
  - With `CI=true` and no wiring it failed: `Error: CI must run this journey: …`.
- **Locators:**
  - `toBeEnabled()` treats `aria-disabled="true"` on a `role="button"` div as disabled.
  - `setInputFiles` on the hidden `<input type="file">` inside that div attaches the file.
- **Lint, format and types:** the three new `.ts` files pass `prettier --check` with the repo's `.prettierrc.json`, `eslint` with `frontend/eslint.config.js`, and a strict `tsc --noEmit`. `e2e/` is not in `tsconfig.app.json`'s `"include": ["src"]`, so `npx tsc -b` never checks it. `npm run lint` (`eslint .`) does.

**Files:**
- Create: `frontend/e2e/fixtures/fake-openai.ts` (contract C10)
- Create: `frontend/e2e/fixtures/synthetic-bill.png` (binary, generated in Step 3a; synthetic data only)
- Create: `frontend/e2e/journeys/scanned-bill-journey.spec.ts`
- Modify (whole file): `frontend/e2e/pages/documents.page.ts`. Task 2 created it with `skip()` only. This task completes contract C9 by adding `uploadBill()` and `expectDone()`.
- Modify: `.github/workflows/ci.yml`, the `e2e-test` job's `env:` block. Insert 7 lines right after the line `      CORS_ALLOWED_ORIGINS: http://localhost:5173,http://127.0.0.1:5173`, which PR #14 added in Task 0. That is `ci.yml:190` once PR #14 is merged; the file in today's working tree is 5 lines shorter there (`:176-185`). Find the anchor by its text, not its number.
- Modify: `CLAUDE.md:41` (Gotchas, "E2E needs full stack"), a new gotcha inserted after it, `:64` (Architecture, E2E) and `:101` (File Map, `e2e/journeys/`), plus one new File Map line after `:101`.
- Test: `frontend/e2e/journeys/scanned-bill-journey.spec.ts`
- Not modified: `backend/apps/documents/services/providers/openai_provider.py`, which already honours `OPENAI_BASE_URL` (see above), and every backend file.

**Interfaces:**
- Consumes:
  - **Task 1 (commit 2):** `apps.documents.views._get_processor()` builds `OpenAIProvider(model=settings.OCR_MODEL or "gpt-4o")` when `settings.OCR_PROVIDER == "openai"`. `OpenAIProvider.__init__` reads `os.environ["OPENAI_API_KEY"]`.
  - **Task 2 (commit 3):**
    - `RegisterPage.goto()`.
    - `RegisterPage.register(username, email, password)`, which resolves once the URL is `/intake`.
    - `frontend/e2e/pages/documents.page.ts` exporting `class DocumentsPage` with `skip()`.
    - `IntakeWizard.handleNext` detours to `/documents` after step 1.
  - **Task 3 (commit 4), contract C11:** `IntakeSessionSerializer` upserts nested debts by `id`, so saving step 5 keeps exactly one row.
  - **Task 4 (commit 5), contract C7:** `IntakeWizard` calls `loadSession(id)` on every mount and renders steps only from the fresh session. A reload therefore resumes at the stored `current_step`, and step 5 hydrates from the server.
  - **Task 8 (commit 9), contract C2:** a creditor bill whose reply names a creditor is `completed`, and `DraftDebtCreator.create_from_result` creates one draft `DebtInfo`. It maps `creditor_type` to `debt_type` and sets `is_draft=True`.
  - **Task 10 (commit 11), contract C6:** debt `amount_owed` is readable, and `hydrateAmounts` turns `"1247.83"` into `1247.83`. The number input's value is then `"1247.83"`.
  - **Task 11 (commit 12):** `WizardPage.fillIncomeInfo(income)` still fills `input[name="monthly_gross_wages"]`.
  - **Task 12 (commit 13):** `WizardPage.fillExpenses(expenses)` fills `input[name=<canonical key>]`.
  - **Tasks 13 and 14 (commits 14–15), contract C8 and the spec §4.10 locator contract:**
    - The drop zone is `role="button"` with `aria-label="Bills and statements: drop files here or click to upload"`. It sets `aria-disabled` while no session exists or a file is sending, and it contains an `<input type="file">`.
    - The queue is `<ul aria-label="Upload queue">`, and a done row contains `✓ Done`.
    - The h1 reads "Upload your documents".
    - The page button reads "Skip for now" until a file is read, then "Continue".
  - **Unchanged UI:**
    - `WizardLayout` renders the step label in `h2.step-title` and a "Go Back" button.
    - `DebtsStep` names its fields `creditor_name_{i}`, `debt_type_{i}` and `amount_owed_{i}`, and renders the badge text `From scan` while `is_draft`.
- Produces:
  - **C9 (complete):** `export class DocumentsPage { constructor(page: Page); skip(): Promise<void>; uploadBill(filePath: string): Promise<void>; expectDone(): Promise<void> }`.
  - **C10:** `export async function startFakeOpenAI(port = 4010): Promise<{ completions(): number; close(): Promise<void> }>`, plus `export const CANNED_BILL`, the canned creditor-bill fields the spec asserts against.
  - **CI wiring:** the `e2e-test` job sets `OCR_PROVIDER=openai`, `OPENAI_API_KEY=e2e-dummy-key-not-a-secret` and `OPENAI_BASE_URL=http://127.0.0.1:4010/v1` at job level, so `runserver` and Playwright both see them. No CI step starts the fake. The spec starts it in its own Playwright worker, because `completions()` is an in-process counter and a second listener on 4010 would fail with `EADDRINUSE`.

- [ ] **Step 1: Write the failing test**

Create `frontend/e2e/journeys/scanned-bill-journey.spec.ts`:

```ts
/**
 * Scanned bill — from upload to Amounts Owed (spec 2026-10-09 §4.12; DIG-1, DIG-6)
 *
 * A filer uploads a photo of a bill after step 1 and sees it read. At Amounts Owed
 * the creditor, the kind of debt and the amount are already filled in, and they are
 * still there after the filer saves and reloads. The real backend reads the upload;
 * only OpenAI is replaced, by the fake server this spec starts (fixtures/fake-openai.ts).
 *
 * Wiring: the backend and this runner both need OPENAI_BASE_URL=http://127.0.0.1:4010/v1,
 * and the backend also needs OCR_PROVIDER=openai and a dummy OPENAI_API_KEY. The CI E2E
 * job sets all three at job level. Without them this journey skips locally (and prints
 * why) and fails in CI.
 *
 * fixtures/synthetic-bill.png is a fictional patient statement drawn with PyMuPDF
 * (Lakeside Example Clinic, account ending 4821, amount due $1,247.83, due 10/15/2026).
 * The fake never looks at it; CANNED_BILL is what a model would read from it.
 *
 * Not asserted:
 * - The "From scan" badge after the reload. Saving debts clears is_draft
 *   (intake/views.py), so the badge is gone once step 5 has saved (DIG-14).
 * - The account number. It is write-only; backend tests prove saving keeps it.
 */

import { fileURLToPath } from 'node:url';
import { test, expect, type Page } from '@playwright/test';
import { SARAH, type PersonaData } from '../fixtures/personas';
import { CANNED_BILL, startFakeOpenAI } from '../fixtures/fake-openai';
import { RegisterPage } from '../pages/register.page';
import { DocumentsPage } from '../pages/documents.page';
import { WizardPage } from '../pages/wizard.page';

// startFakeOpenAI() listens on 4010 by default; .github/workflows/ci.yml uses the same URL.
const FAKE_OPENAI_BASE_URL = 'http://127.0.0.1:4010/v1';
const WIRING =
  `start the backend with OPENAI_BASE_URL=${FAKE_OPENAI_BASE_URL} OCR_PROVIDER=openai ` +
  'OPENAI_API_KEY=e2e-dummy-key, and export the same OPENAI_BASE_URL before npm run e2e';

const BILL = fileURLToPath(new URL('../fixtures/synthetic-bill.png', import.meta.url));

// Sarah's simple finances under a login of its own. personas.ts fixes RUN_ID once per
// module load, so SARAH's username would collide with sarah-simplest in a shared worker.
const RUN_ID = Date.now().toString(36);
const FILER: PersonaData = {
  ...SARAH,
  username: `e2e_scan_${RUN_ID}`,
  debtor: { ...SARAH.debtor, email: `scan.e2e+${RUN_ID}@test.dignifi.org` },
};

/** The scanned bill is the only row at Amounts Owed, with what the model read. */
async function expectScannedBill(page: Page) {
  await expect(page.locator('input[name^="creditor_name_"]')).toHaveCount(1);
  await expect(page.locator('input[name="creditor_name_0"]')).toHaveValue(
    CANNED_BILL.creditor_name
  );
  await expect(page.locator('select[name="debt_type_0"]')).toHaveValue(CANNED_BILL.creditor_type);
  await expect(page.locator('input[name="amount_owed_0"]')).toHaveValue(CANNED_BILL.amount_owed);
}

test.describe('Scanned bill — upload to Amounts Owed', () => {
  test('a bill read at upload is waiting at Amounts Owed and survives save and reload', async ({
    page,
  }) => {
    if (process.env.OPENAI_BASE_URL !== FAKE_OPENAI_BASE_URL) {
      if (process.env.CI) throw new Error(`CI must run this journey: ${WIRING}`);
      console.warn(`[scanned-bill-journey] skipped. To run it, ${WIRING}`);
      test.skip(true, `To run it, ${WIRING}`);
    }

    const fake = await startFakeOpenAI();
    try {
      const register = new RegisterPage(page);
      const documents = new DocumentsPage(page);
      const wizard = new WizardPage(page);
      const stepTitle = page.locator('.step-title');

      await register.goto();
      await register.register(FILER.username, FILER.debtor.email, FILER.password);

      // Step 1, then the upload detour
      await wizard.fillDebtorInfo(FILER.debtor);
      await wizard.nextStep();
      await expect(
        page.getByRole('heading', { level: 1, name: 'Upload your documents' })
      ).toBeVisible();

      await documents.uploadBill(BILL);
      await documents.expectDone();
      expect(
        fake.completions(),
        `the backend never called the fake: ${WIRING}`
      ).toBeGreaterThanOrEqual(1);

      // Back to the wizard, which re-reads the session and resumes at Income
      await page.getByRole('button', { name: 'Continue', exact: true }).click();
      await expect(stepTitle).toHaveText('Income');
      await wizard.fillIncomeInfo(FILER.income);
      await wizard.nextStep();
      await expect(stepTitle).toHaveText('Expenses');
      await wizard.fillExpenses(FILER.expenses);
      await wizard.nextStep();
      await expect(stepTitle).toHaveText('Assets');
      await wizard.nextStep(); // no assets
      await expect(stepTitle).toHaveText('Amounts Owed');

      // First visit: the bill is there, marked as coming from the scan
      await expectScannedBill(page);
      await expect(page.getByText('From scan', { exact: true })).toBeVisible();

      // Continue saves step 5 and stores step 6 as the place to resume
      await wizard.nextStep();
      await expect(stepTitle).toHaveText('Contracts & Leases');

      // A reload re-runs the token refresh and the wizard's session re-read before any step renders
      await page.reload();
      await expect(stepTitle).toHaveText('Contracts & Leases', { timeout: 15_000 });
      await page.getByRole('button', { name: 'Go Back' }).click();
      await expect(stepTitle).toHaveText('Amounts Owed');
      await expectScannedBill(page);
    } finally {
      await fake.close();
    }
  });
});
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
cd /Volumes/Containers/DigniFi/frontend
npm run e2e -- scanned-bill --list
```

Expected: exit code 1, with

```
Error: Cannot find module '/Volumes/Containers/DigniFi/frontend/e2e/fixtures/fake-openai' imported from /Volumes/Containers/DigniFi/frontend/e2e/journeys/scanned-bill-journey.spec.ts
...
Total: 0 tests in 0 files
```

`--list` loads the file without starting the Vite `webServer`, so this needs no running stack. If you skipped ahead and created `fake-openai.ts` first, the load succeeds. In that case a full run without Step 3c fails instead with `TypeError: documents.uploadBill is not a function`.

- [ ] **Step 3: Implement**

**3a. The synthetic bill fixture.** Every name, address and number on it is invented. Write the generator outside the repo and render the PNG with the backend venv's PyMuPDF. PyMuPDF is already in `backend/requirements/base.txt`.

```bash
cat > "$TMPDIR/make_synthetic_bill.py" <<'EOF'
"""Render frontend/e2e/fixtures/synthetic-bill.png, a fictional bill for the E2E journey.

Every name, address and number below is invented. The page is drawn with MuPDF's
built-in Helvetica (no system fonts) and saved as a grayscale PNG with no timestamp,
so the same PyMuPDF version always writes the same bytes.
"""

import sys

import fitz  # PyMuPDF, already in backend/requirements/base.txt

LINES = [
    "LAKESIDE EXAMPLE CLINIC",
    "SYNTHETIC TEST DOCUMENT - NOT A REAL BILL",
    "100 Example Street, Chicago, IL 60601",
    "",
    "PATIENT STATEMENT",
    "Statement date: 09/15/2026",
    "Patient: Test Filer",
    "Account number: XXXX-XXXX-4821",
    "",
    "Previous balance:      $1,312.83",
    "Payments received:       -$65.00",
    "AMOUNT DUE:            $1,247.83",
    "Minimum payment:          $65.00",
    "Payment due by: 10/15/2026",
]

doc = fitz.open()
page = doc.new_page(width=612, height=792)  # US Letter, in points
y = 72
for line in LINES:
    page.insert_text((72, y), line, fontsize=14, fontname="helv")
    y += 21
page.get_pixmap(dpi=100, colorspace=fitz.csGRAY).save(sys.argv[1])
EOF
cd /Volumes/Containers/DigniFi
backend/.venv/bin/python -I "$TMPDIR/make_synthetic_bill.py" frontend/e2e/fixtures/synthetic-bill.png
shasum -a 256 frontend/e2e/fixtures/synthetic-bill.png
file frontend/e2e/fixtures/synthetic-bill.png
```

Expected:

- `file` prints `PNG image data, 850 x 1100, 8-bit grayscale, non-interlaced`.
- With PyMuPDF 1.27.2.3 (`backend/.venv/bin/pip show pymupdf`), the file is 23,986 bytes with sha256 `4b145e9bc4285a5cfd886e3c3ee19c21a6698778f461e7432559f25462328ddb`. Running the generator twice gives identical bytes.

The PNG has no timestamp, and the text uses MuPDF's built-in Helvetica, so no system fonts are involved. Another PyMuPDF version may write different bytes. That is fine: open the image and check that all 14 lines are legible. The fake never reads the image; it is there so the upload is a real file of an accepted type.

**3b.** Create `frontend/e2e/fixtures/fake-openai.ts`:

```ts
/**
 * Fake OpenAI — a stand-in for the Chat Completions API.
 *
 * The scanned-bill journey runs the real upload → OCR → draft-debt path, but no test
 * should need an OpenAI key or the network. The backend reaches this server through
 * OPENAI_BASE_URL=http://127.0.0.1:4010/v1, which the openai SDK reads from the
 * environment on its own (OpenAIProvider passes only the key).
 *
 * Every request to POST /v1/chat/completions gets the same reply: the fields a model
 * would read from fixtures/synthetic-bill.png. Anything else is a 404, so a changed
 * SDK route fails loudly instead of silently returning a bill.
 *
 * The spec that needs it starts it, so completions() counts in that spec's own worker.
 * Nothing else (no CI step, no globalSetup) may listen on the port.
 */

import { createServer } from 'node:http';

/** What the "model" reads from fixtures/synthetic-bill.png. Every value is invented. */
export const CANNED_BILL = {
  creditor_name: 'Lakeside Example Clinic',
  account_number: '4821',
  amount_owed: '1247.83',
  minimum_payment: '65.00',
  due_date: '2026-10-15',
  creditor_type: 'medical',
  confidence_score: 92,
} as const;

export async function startFakeOpenAI(
  port = 4010
): Promise<{ completions(): number; close(): Promise<void> }> {
  let completions = 0;

  const server = createServer((req, res) => {
    // Read the whole request (prompt plus base64 page images) before answering.
    req.resume();
    req.on('end', () => {
      if (req.method !== 'POST' || req.url !== '/v1/chat/completions') {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(
          JSON.stringify({ error: { message: `fake-openai has no ${req.method} ${req.url}` } })
        );
        return;
      }
      completions += 1;
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(
        JSON.stringify({
          id: `chatcmpl-fake-${completions}`,
          object: 'chat.completion',
          created: Math.floor(Date.now() / 1000),
          model: 'gpt-4o',
          choices: [
            {
              index: 0,
              message: { role: 'assistant', content: JSON.stringify(CANNED_BILL), refusal: null },
              finish_reason: 'stop',
              logprobs: null,
            },
          ],
          usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
        })
      );
    });
  });

  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve());
  });

  return {
    completions: () => completions,
    close: () =>
      new Promise<void>((resolve, reject) => {
        // The backend's HTTP client keeps its connection open; drop it so close() returns.
        server.closeAllConnections();
        server.close((err) => (err ? reject(err) : resolve()));
      }),
  };
}
```

**3c.** Replace the whole of `frontend/e2e/pages/documents.page.ts` with the code below. Its `skip()` method, doc comment included, is Task 2's (commit 3) byte for byte, so the diff leaves it untouched; this task changes only the header comment and adds `uploadBill()` and `expectDone()`. Task 2 already imports `expect`.

```ts
/**
 * Documents Page Object — the upload step between wizard step 1 and step 2.
 *
 * Locators follow the upload page's E2E contract (spec 2026-10-09 §4.10): the
 * drop-zone aria-label pattern, the "Upload queue" list, a done row containing
 * "Done", and the "Skip for now" / "Continue" button labels.
 */

import { expect, type Page } from '@playwright/test';

export class DocumentsPage {
  constructor(private page: Page) {}

  /** Leave the upload step without uploading anything; the wizard resumes at Income. */
  async skip() {
    await this.page.waitForURL('**/documents');
    await expect(
      this.page.getByRole('heading', { level: 1, name: 'Upload your documents' })
    ).toBeVisible();
    await this.page.getByRole('button', { name: 'Skip for now', exact: true }).click();
    await this.page.waitForURL('**/intake');
  }

  /** Send one file through the "Bills and statements" area (document type creditor_bill). */
  async uploadBill(filePath: string) {
    const zone = this.page.getByRole('button', {
      name: 'Bills and statements: drop files here or click to upload',
    });
    // The zone is aria-disabled until the session exists and while a file is sending.
    await expect(zone).toBeEnabled();
    await zone.locator('input[type="file"]').setInputFiles(filePath);
  }

  /** Wait until a file in the upload queue has been read ("✓ Done"). */
  async expectDone() {
    const queue = this.page.getByRole('list', { name: 'Upload queue' });
    await expect(queue.getByRole('listitem').filter({ hasText: /\bDone\b/ })).toBeVisible({
      timeout: 30_000,
    });
  }
}
```

**3d.** In `.github/workflows/ci.yml`, inside the `e2e-test` job's `env:` block, find the line

```yaml
      CORS_ALLOWED_ORIGINS: http://localhost:5173,http://127.0.0.1:5173
```

It occurs once in the file. Insert these lines directly after it, at the same indentation:

```yaml
      # The scanned-bill journey starts a fake OpenAI server on 127.0.0.1:4010 inside its
      # Playwright worker (frontend/e2e/fixtures/fake-openai.ts). The backend reaches it
      # because the openai SDK reads OPENAI_BASE_URL itself; the journey reads the same
      # variable to confirm the wiring and fails in CI without it. The key is a dummy.
      OCR_PROVIDER: openai
      OPENAI_API_KEY: e2e-dummy-key-not-a-secret
      OPENAI_BASE_URL: http://127.0.0.1:4010/v1
```

**What stays the same:**

- **The "Start backend server" step** (`run: python manage.py runserver 0.0.0.0:8000 &`) and **the "Start frontend and run E2E tests" step** need no change: job-level `env` already reaches both.
- **Don't add a step that starts the fake.**
- **The insertion was checked** on PR #14's version of the file. `yaml.safe_load` parses it, and `jobs.e2e-test.env` then holds all four of `CORS_ALLOWED_ORIGINS`, `OCR_PROVIDER`, `OPENAI_API_KEY` and `OPENAI_BASE_URL`. `backend-test` gets none of them.

**If the anchor line is missing,** Task 0 did not merge PR #14. Stop and do Task 0 first. Without that line, E2E registration is CORS-blocked anyway.

- [ ] **Step 4: Run tests and confirm they pass**

**4a. Static gates for this commit.** No backend file changes, so the backend gates are unaffected.

```bash
cd /Volumes/Containers/DigniFi/frontend
npm run lint                          # expect: exit 0, no problems (eslint . covers e2e/)
npx tsc -b                            # expect: exit 0 (e2e/ is outside tsconfig.app.json; unchanged)
npx vitest run                        # expect: every test passes; this commit adds no unit code
npm run e2e -- scanned-bill --list    # expect: "Total: 1 test in 1 file"
```

**4b. The guard, without the wiring.** Playwright starts Vite itself through `webServer` (`reuseExistingServer: true`).

```bash
cd /Volumes/Containers/DigniFi/frontend
env -u OPENAI_BASE_URL -u CI npm run e2e -- scanned-bill
```

Expected: the line `[scanned-bill-journey] skipped. To run it, start the backend with OPENAI_BASE_URL=http://127.0.0.1:4010/v1 OCR_PROVIDER=openai OPENAI_API_KEY=e2e-dummy-key, and export the same OPENAI_BASE_URL before npm run e2e`, then `1 skipped`, exit code 0.

Then the CI guard:

```bash
env -u OPENAI_BASE_URL CI=true npm run e2e -- scanned-bill
```

Expected: exit code 1, `Error: CI must run this journey: start the backend with OPENAI_BASE_URL=…` and `1 failed`. This is the intended red: in CI the journey cannot be skipped by accident.

**4c. The journey on the full stack, wired to the fake.**

**Postgres.** On this machine something else owns host port 5432, so publish the compose `db` on 5433:

```bash
cd /Volumes/Containers/DigniFi
printf 'services:\n  db:\n    ports:\n      - "5433:5432"\n' > "$TMPDIR/compose.db-port.yml"
docker compose -f docker-compose.yml -f "$TMPDIR/compose.db-port.yml" up -d db

cd /Volumes/Containers/DigniFi/backend
export DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_dev
.venv/bin/python manage.py migrate --noinput     # must list documents 0006 as applied (Task 8)
.venv/bin/python manage.py loaddata ilnd_2025_data
.venv/bin/python manage.py seed_demo_data         # skips users that already exist
```

**Backend.** Start it with the fake wiring. Run this in the background (Bash `run_in_background`), because it does not exit.

- Export the **dummy** key. The repo-root `.env` may hold a real `OPENAI_API_KEY`, and exported variables win over `.env`, because django-environ only calls `setdefault` and the SDK reads `os.environ`.
- `manage.py` defaults to `config.settings.development`, the same settings the CI E2E job uses.

```bash
cd /Volumes/Containers/DigniFi/backend
DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_dev \
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 \
OCR_PROVIDER=openai OPENAI_API_KEY=e2e-dummy-key OPENAI_BASE_URL=http://127.0.0.1:4010/v1 \
.venv/bin/python manage.py runserver 127.0.0.1:8000 > "$TMPDIR/e2e-backend.log" 2>&1
```

Wait until `$TMPDIR/e2e-backend.log` contains `Quit the server with CONTROL-C.`, then run the journey:

```bash
cd /Volumes/Containers/DigniFi/frontend
OPENAI_BASE_URL=http://127.0.0.1:4010/v1 npm run e2e -- scanned-bill
```

Expected:

- `1 passed`.
- `grep -c 'POST /api/documents/upload/' "$TMPDIR/e2e-backend.log"` prints at least `1`.
- `grep -E '" 500 ' "$TMPDIR/e2e-backend.log"` prints nothing.

If it fails, open the trace (`npx playwright show-trace test-results/<dir>/trace.zip`) and match the failing line:

| Failure | Look at |
| --- | --- |
| Stuck at "Upload your documents" | The drop-zone aria-label (Task 13) |
| No "Done" | The documents GET in the trace and the backend log: was the scan read as `failed`? |
| `completions` is 0 | The backend was started without `OPENAI_BASE_URL` |
| Wrong values at Amounts Owed | Task 4's re-read or Task 10's hydration |
| Two rows after reload | Task 3's upsert |

**4d. The full E2E suite at the tip.** Keep the same backend running.

```bash
cd /Volumes/Containers/DigniFi/frontend
OPENAI_BASE_URL=http://127.0.0.1:4010/v1 npm run e2e
```

Expected: `7 passed`, with `0 skipped` and `0 failed`. The seven are `deshawn-assets`, `james-borderline`, `maria-happy-path`, `priya-ineligible`, `sarah-simplest`, `sofa-journey` and `scanned-bill-journey`.

Then stop the backend task and leave the `db` container running or stop it (`docker compose stop db`). After the push, the PR's "E2E Tests (Playwright)" check must show the same 7 passed. The job runs without `--reporter`, so CI uses the list reporter.

- [ ] **Step 5: Update CLAUDE.md gotchas**

In the root `CLAUDE.md` make four edits.

**(1)** In "Gotchas", replace the whole line

```
- **E2E needs full stack** — Playwright tests (`frontend/e2e/journeys/`) require backend running, migrations applied, and `seed_demo_data` loaded.
```

with

```
- **E2E needs full stack** — Playwright tests (`frontend/e2e/journeys/`) require backend running, migrations applied, and `seed_demo_data` loaded. `scanned-bill-journey` also needs `OPENAI_BASE_URL=http://127.0.0.1:4010/v1` in both the backend's and Playwright's environment, plus `OCR_PROVIDER=openai` and a dummy `OPENAI_API_KEY` for the backend; the spec starts the fake OpenAI server itself (`e2e/fixtures/fake-openai.ts`). Without the wiring it skips locally (printing why) and fails in CI. Export the dummy key: exported variables beat the repo-root `.env`, which may hold a real one.
```

**(2)** Directly below that line, add a new gotcha:

```
- **`OPENAI_BASE_URL` comes from the SDK, not settings** — `OpenAIProvider` passes only the key; the `openai` SDK reads `OPENAI_BASE_URL` from the environment itself. An empty value (`OPENAI_BASE_URL=` in `.env`) is not ignored: the SDK uses `''` as the base URL and every OCR call fails.
```

**(3)** In "Architecture (quick)", replace

```
driving 6 journey specs — one per persona plus `sofa-journey.spec.ts`.
```

with

```
driving 7 journey specs — one per persona plus `sofa-journey.spec.ts` and `scanned-bill-journey.spec.ts` (an upload read through a fake OpenAI server).
```

**(4)** In "File Map", replace the line

```
- `e2e/journeys/` — 6 Playwright journey specs (5 personas + SOFA)
```

with these two lines:

```
- `e2e/journeys/` — 7 Playwright journey specs (5 personas + SOFA + scanned bill)
- `e2e/fixtures/fake-openai.ts` — fake OpenAI Chat Completions server (`startFakeOpenAI`, `CANNED_BILL`) for `scanned-bill-journey`
```

- [ ] **Step 6: Commit**

Check first that the two shared files hold only this task's changes:

```bash
cd /Volumes/Containers/DigniFi
git diff --stat -- CLAUDE.md .github/workflows/ci.yml
git diff -- .github/workflows/ci.yml
```

Expected:

- `ci.yml` shows exactly the 7 added lines from Step 3d.
- `CLAUDE.md` shows exactly the 4 edits from Step 5. Tasks 1–2 committed every other `CLAUDE.md` change, and Tasks 3–14 committed their own. If it also shows hunks from any other change, stop and ask the owner; do not stage it. Never use `git add -p`: it is interactive and this harness cannot drive it.

```bash
cd /Volumes/Containers/DigniFi
git add frontend/e2e/fixtures/fake-openai.ts \
  frontend/e2e/fixtures/synthetic-bill.png \
  frontend/e2e/journeys/scanned-bill-journey.spec.ts \
  frontend/e2e/pages/documents.page.ts \
  .github/workflows/ci.yml \
  CLAUDE.md
git status --short
```

Expected: exactly those 6 paths show as staged (`A ` or `M `). `.serena/`, `DESIGN.md`, `assets/`, `frontend/.impeccable/` and any README landing-image change stay unstaged and untracked.

```bash
git commit -m "test(e2e): follow a scanned bill from upload to Amounts Owed"
```

Pre-commit prettier may reformat `CLAUDE.md` on the first attempt; the `.ts` files are already Prettier-clean. If the hook modified files and the commit aborted, re-run the same `git add` command (it includes `CLAUDE.md`) and the same `git commit` again. `check-added-large-files` passes, because the PNG is about 24 KB against a 500 KB limit. The message is exactly the spec §9 line, with no trailer.

<!-- prettier-ignore-end -->
