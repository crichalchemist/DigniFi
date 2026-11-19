# Forms step 4a, the frame: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One gap list behind Complete, a read-only endpoint that returns it, Review and the forms dashboard reading that list, the forms views refusing what Complete would, the wizard's step count pinned to the browser's step table, the binding namespaces every later step-4 PR binds through (with nothing bound yet), and the five small components (the yes/no-then-details block, the section intro, the framing line, the public-record notice, the "What does this mean?" expandable) that steps 1–12 are built from. No new record, no new question, no schema change, no migration.

**Architecture:**

- **Backend, one list** (`apps/intake/completion.py`, new): `Gap(Exception)` with `message`, `step`, `kind` (`"gate"` / `"detail"`), `completion_gaps(session) -> list[Gap]` holding exactly what `complete` checks today (`views.py:296-339`) in that order, every entry a `gate`; `WIZARD_STEP_COUNT = 9`. `complete` refuses the gates; a new `GET /api/intake/sessions/{id}/gaps/` returns `{gaps: [{message, step, kind}]}` and writes nothing; `update_step`'s bound reads the constant. The forms' `_prepare` raises the first `gate` (a 422 with its `step`) in place of its separate asset and claims checks, so every caller of `_prepare` (Generate, Generate All, Regenerate, an unfiled download, Mark as Filed on an unfiled means-pair form and `mark_pair_filed`; `forms/views.py:423,458,526,592,645,701`) refuses whatever Complete would (B46); the packet list and a filed download never run it.
- **Backend, the namespaces** (`apps/forms/schema.py`, `apps/forms/services/fill_resolver.py`, `apps/forms/services/answer_records.py`, new): `petition.`, `schedule_i.`, `intentions.`, `affairs.` join `_BINDING_NAMESPACES` and `_LIST_BINDING`; `resolve_binding` reads each through one generic reader over a record's `get_answers()` (blank or `[]` when the session has no such record, which in 4a is always); `binding_fix` maps each to its wizard step by key (B36). `answer:` and `sofa.` stay until 4i and 4f.
- **Frontend, the list** (`api/client.ts`, `types/api.ts`, `pages/IntakeWizard.tsx`, `components/wizard/steps/ReviewStep.tsx`, `pages/FormDashboard.tsx`, `components/forms/GapsNotice.tsx`, new, `components/forms/FormCard.tsx`): the wizard fetches the gaps when Review shows and again after a refused Complete; Review's `review-reasons` region renders that list and nothing else, with "Go to {step}", or "Nothing is missing."; Review is invalid only while a returned list holds a `gate` (while the check is loading or has failed, the server decides). The dashboard fetches once on mount and shows the list above Generate All, a `gate` named as missing and a `detail` as blank; a card's button goes where its refusal points first and takes the refusal's label (B35). The three new step keys and `review` are reserved in the always-autosave list (B3).
- **Frontend, the blocks** (`components/wizard/YesNoThenDetails.tsx`, moved from `pages/meansTest/YesNoQuestion.tsx`; `SectionIntro.tsx`, `FramingLine.tsx`, `PublicRecordNotice.tsx`, `WhatDoesThisMean.tsx`, new): B4, B48, B49, B43; their sentences in `constants/copy.ts`, scored.

**Tech Stack:** Django 5.0 + DRF, pytest-django (sqlite), React 19 + Vite + TypeScript, vitest + MSW + vitest-axe. No new dependency.

**Spec:** `docs/superpowers/specs/2026-11-18-forms-step4-design.md` (cited `§n`; its row 4a is §19 line 805; its builder's calls are `Bn`), read whole on 2026-11-18. The surveys behind it are under `/home/crichalchemist/Desktop/IDEAS/DigniFi/.claude/handoff/2026-11-18-step4/design/` (`survey-wizard.md` is `SWIZ`; `builder-check.md` Q2 and Q3 are the two questions §5.7 answered). Every `path:line` below was read in this worktree at a1a697e on 2026-11-18; a task that lands earlier moves the ones below it, so each is a landmark, not an address. Where this plan reads the spec its own way, the reading is under "Rulings" with its negative cases; nothing else departs. Where a review showed the spec itself wrong against the code (five places: B46's heading, §18.2's `updated_at`, B49's resource, §14.4's `affairs.pay6[]`, §5.7's "wizard order"), the spec is unedited, the correction is recorded in `/home/crichalchemist/Desktop/IDEAS/DigniFi/.claude/handoff/2026-11-18-step4/plan-4a/spec-corrections.md`, and the task that follows the corrected reading says so.

<!-- prettier-ignore-start -->

## Global Constraints

- **The PR boundary.** 4a adds no record, no model, no migration, no schema binding, no new question and no filer-visible copy on any step but Review and the dashboard. No bound box loses its source: `answer:` and `sofa.` stay in `_BINDING_NAMESPACES`, `resolve_binding` and `binding_fix` (§14.4; 4i and 4f delete them). Nothing writes a filer answer anywhere, so nothing unencrypted is written. `makemigrations --check` prints "No changes detected" after every task.
- **One list, and its scope** (B6). `completion_gaps` runs what Complete runs today and nothing more: never `packet()`, never a form's `requires()`, never the means test, never a post-Complete page's gap (the fee choice, the exemptions, line 17). Every existing entry is a `gate`, so Complete's refusals on today's data are byte-for-byte unchanged (`test_complete_lists_every_gap_in_wizard_order`, `test_completion.py:480`, passes untouched). No `detail` exists in 4a; the kind is carried so 4b's first `detail` needs no plumbing.
- **Never a No the filer did not give** (§5.3). Nothing in 4a prints: the only `_emit`-adjacent change is the namespace reader, which returns `""` or `[]` for a missing record and never a default. `YesNoThenDetails` renders nothing checked while `value` is `null`.
- **Copy.** DigniFi's sentences go in `frontend/src/constants/copy.ts`, each a single string literal, scored by `reading-level.test.ts` (grade 9 ceiling, `:54-56`); the ones this plan fixes are under each task. Information, never advice: none says "should", "recommend", "must" or predicts an outcome (the `ADVICE` list of `upl-claims-copy.test.ts:14-33` is copied into Task 6's `upl-frame-copy.test.ts`). `PUBLIC_RECORD_NOTICE` carries `// DRAFT: counsel C-40` on the line above its `export const` (§6.0 B49). Every string export of `copy.ts` is scored, labels included (`reading-level.test.ts:68-70` pushes each `typeof value === 'string'` export); `WHAT_DOES_THIS_MEAN` and the two `SECTION_INTRO_*` lines pass trivially, and `PUBLIC_RECORD_NOTICE` (two sentences, a phone number) is the one to run first. "Go to {step}" is built in the component, not exported, so it is not scored.
- **Reopen and autosave.** The gaps endpoint, the Review fetch and the dashboard fetch write nothing and never `reopen()`; the endpoint takes no `lock_session` (`views.py:215` is the write path's). The autosave `enabled` rule keeps `currentStepKey !== 'review'` (Review has no body until 4i; §6.0); the reservation is the names in `ALWAYS_AUTOSAVE_STEPS`, nothing more. No `currentStepBody` case is added.
- **CLAUDE.md gotchas that bind here:** "Forms need a completed intake" and "GenerateAll vs single" (both rewritten in Task 7; until then they describe `_prepare`'s old order and the old list of whole-call refusals), "Autosave sends only real edits", "DRF pagination", "`updateCurrentStep` is POST `update_step`" (a wizard test that mocks the session PATCH to assert step movement passes vacuously), "user-event hangs under vitest fake timers" (no fake timers are needed in 4a), "Frontend tests use MSW" (every new call has a default handler in `src/test/mocks/handlers.ts`), "known_defects.json stays `[]`" (no oracle case changes; a new namespace with no binding adds no tier-2 row and moves no `ASSERTED_CASES`), "Schemas are checked at startup" (`manage.py check` passes after Task 3).
- **Backend tests.** This worktree has no `backend/.venv`; the interpreter is `$PY` from `/home/crichalchemist/Desktop/IDEAS/DigniFi/.claude/forms-gate.env`: read that one line, never `source` the file (it exports `DEBUG` and the OCR variables too) and never print any value in it. `backend/logs/` is absent here and `config.settings.test` needs it (`base.py:314-318`'s file handler on `LOGS_DIR`, whose `mkdir` is commented out at `:23`): `mkdir -p logs` from `backend/` first; it is gitignored. From `backend/`:
  `PYTHONDONTWRITEBYTECODE=1 DJANGO_SECRET_KEY=synthetic-tests-only FIELD_ENCRYPTION_KEY=U9HKckkKBeT8wag2jMcOx2Cez2M2jtvNG4qxSHuYcAo= DJANGO_SETTINGS_MODULE=config.settings.test "$PY" -m pytest -p no:cacheprovider <paths> -q`
  ("`… python`" below means exactly this). `manage.py check` and `makemigrations --check --dry-run` take the same prefix. Name files; never run the whole suite from a task (the controller runs gates between tasks). Take counts from pytest's last line through a one-line `printf`: tool output here can be compressed.
- **Lint.** `ruff==0.8.5` (CI's pin): `"$PY" -m ruff check <files>` on every Python file touched; `ruff format --check` only on files a task creates or that passed it at a1a697e (61 files on `develop` are already unformatted; never `ruff format` an existing file). Lines to 100 columns.
- **Frontend tests.** `frontend/node_modules/` is absent here: `npm ci` once from `frontend/`. Then `NODE_OPTIONS=--no-experimental-webstorage npx vitest run --maxWorkers=2 <paths>`; `npx tsc -p tsconfig.app.json --noEmit` (never `tsc -b`; `tsc` checks no test file, `tsconfig.app.json:24`); `npx eslint <files>`; `./node_modules/.bin/prettier --write <files>` then `--check`. New API calls get MSW handlers. `userEvent` for clicks, `findBy`/`waitFor` for async; no fake timers.
- **Git.** `/usr/bin/git`, one plain command per call, from inside the worktree, on `feat/forms-step4a`; never `git -C`. One commit a task; stage by explicit path; never `.claude/`, `.superpowers/`, `.serena/`, `DESIGN.md`, `assets/`, `.impeccable`, `node_modules/`, `logs/`, `__pycache__/`. No `Co-Authored-By`, `Claude-Session` or any agent trailer. No push, merge or branch change. The pre-commit hooks reformat on a first commit: re-stage the same paths and commit again.
- **Tests encode intent.** Names say the outcome. Synthetic data only (IRS-reserved SSNs `900-…`, "Demo" names). A test that passes before its code is written gets a "see it fail" step by removing the code's line, as each task says.

## Review Focus

Eight conditions a filer or the suite will meet that §19's row doesn't spell out, most likely first; each has its test in the owning task. Items 2, 3 and 7 are the spec claims most likely to be wrong, and a per-task CLEAN means "matches this plan", so a reviewer reads them against the code, not the plan.

1. **A seeded persona with a `gate` gap.** `seed_demo_data` marks six sessions completed (`seed_demo_data.py:1510` sets `current_step=7` on one); after Task 2 a gate on any of them makes the E2E dashboard's Generate All a 422, and no vitest or pytest today would say so. Test: Task 2, `test_every_seeded_persona_has_no_gate_gap` in `test_seed_demo_data.py`.
2. **A forms view test that completes a session by hand.** Six fixtures build `status="completed"` sessions through `answer_household` with no `ExpenseInfo` row and then call a forms view: `test_form_views.py:129` (`session`), `conftest.py:502` (`generated_form_factory`, which `test_download_action.py` takes), `test_means_hold.py:95`, `test_schedule_c_gate.py:39`, `test_list_of_creditors.py:59`, `test_means_mark_filed.py:54`. Complete refuses each today ("Go through the Expenses step…"), so Task 2's `_prepare` refuses every view call on them. Not in the set, each checked at a1a697e: `test_api_readback.py` finishes its session through the API's own `complete/` (`:183`), so it already carries the row; `test_time_packet.py` and `test_filing_fee_forms.py` call `packet()` directly and never a view (no `/api/forms/` path in either); `test_means_hold.py:1372`'s `theirs` is another filer's session, a 404 before `_prepare`; `means_rows.py:151`, `test_exemption_rows.py:43`, `test_schedule_c_rows.py:64` and `test_derivations.py:41` build completed sessions no view ever sees. One test already creates the row on a fixture that will now carry it (`test_form_views.py:1285`, "Complete requires it"): once `finish_intake` runs in the fixture that `create` is an `IntegrityError` (`ExpenseInfo.session` is a `OneToOneField`, `models.py:539`). Test and fix: Task 2's `finish_intake` (an `update_or_create`) on each of the six, the `:1285` create deleted, and a grep step so the dry run finds any seventh.
3. **Review can't reach the gaps endpoint, or it never answers.** A 500, a network failure or a request that neither resolves nor rejects (`apiFetch` has no timeout: `client.ts:288` is `withRetry` alone, and `:538`'s `signal` is a type) must not lock Complete, since the server still decides; a failure says so in words, and the loading state leaves the button enabled with no words. Tests: Task 4, `an unreachable check leaves Complete enabled and says so` and `a check that has not answered leaves Complete enabled`.
4. **A gap whose step the browser doesn't know** (a server ahead of the browser; a reserved key before its PR). Listed without a button on Review, without a link on the dashboard, never a crash. Tests: Task 4, `a gap on a step the wizard doesn't know shows its words and no button`; Task 5, `a gap on an unknown step shows its words and no link`.
5. **Generate All refused for a gate gap must delete nothing.** Today `generate_all` deletes rows outside the packet right after `_prepare` (`forms/views.py:463-465`); the refusal must come first, and every stored row survive. Test: Task 2, `test_a_refused_generate_all_deletes_no_stored_form` (red before Task 2's Step 3, since `_prepare` lets the missing row through today and the delete runs).
6. **The means-test page after the move.** `YesNoThenDetails` without `unanswered` must render exactly what `YesNoQuestion` rendered (no new line under the radios on `/means-test`). Test: Task 6, `without unanswered nothing is added below the answer`; the four means-test vitest files run unchanged.
7. **The dashboard's heading for a `gate`.** B46's sentence ("N answers are blank on your forms") describes a `detail`, which prints blank (§5.7 line 211); a `gate` prints nothing, because `_prepare` refuses the whole call. 4a has no `detail`, so with B46's words alone every notice 4a can show would tell a filer their forms hold blanks on the page where Generate All is about to refuse. Test: Task 5, `a gate gap is named as missing, not as blank` (4a-R5; spec correction 1).
8. **Mark as Filed after the widening.** `mark_pair_filed` (`forms/views.py:526`) and `mark_filed` on an unfiled means-pair form (`:645`) run `_prepare`, so a filer whose completed session has a gate can't mark the pair filed until it is answered, and neither row may be marked. Test: Task 2, `test_a_gate_gap_refuses_marking_the_pair_filed_and_marks_neither` in `test_means_mark_filed.py` (through `mark_filed`, that file's subject; `mark_pair_filed` reaches the same `_prepare` and its 404-for-another-filer case is already in `test_means_hold.py:1372-1380`).

## Rulings

Where §19's row leaves 4a a choice, this plan's reading, with what must still pass and what must still be refused.

- **4a-R1, `_prepare` reads the whole list** (B46, §5.7). After `_check_finished`, `_prepare` raises the first `gate` of `completion_gaps(session)` and then works the means test out; its asset and claims blocks go, since both are in the list in the same order. This widens every caller of `_prepare` to `_needs_ssn`, `_needs_county`, the income gaps, take-home pay and the Expenses row, which only Complete refused before: Generate (`forms/views.py:423`), Generate All (`:458`), `mark_pair_filed` (`:526`), Regenerate (`:592`), Mark as Filed on an unfiled means-pair form (`:645`) and an unfiled download (`:701`). B46 names only Generate and Generate All; the other four are the same function, and a pair that can't be prepared can't be marked filed. One visible shape change: a completed session with no `DebtorInfo` gets a whole-call 422 `{error, step: "debtor_info"}` from Generate All where today it gets 200 `{generated: [], errors: [...]}` with `_needs_ssn` firing per form inside `build_parts`; no test asserts the old shape (the per-form case at `test_form_views.py:630-668` is an unprintable letter and stays per-form), and Task 7 adds the cause to the "GenerateAll vs single" gotcha. Reason: B6's one list; a session completed before a rule exists is exactly the case B46 names. Negative cases: the packet list (`packet`, `forms/views.py:365`, which calls `_recalculate_means_test` directly) still never refuses an unfinished intake or a gap; a filed form's download still never runs `_prepare`; `IntakeNotFinished` still comes before any gap; a session with no gap sees no change; `mark_pair_filed` on another filer's session is still a 404 before `_prepare` (`test_means_hold.py:1372-1380`).
- **4a-R2, `Gap` is an exception**, like `AssetStepGap` and `ClaimStepGap`, so `_prepare` raises it unchanged and `_failure` reads `str(exc)` and `exc.step`. A `PreconditionMissing(gap.message, step=gap.step)` would fail `test_rule_fixes._precondition_fixes` (`:62-85`), which reads every `PreconditionMissing(...)` call's `step` as a constant. Negative: `_failure` adds `Gap` to its isinstance list and nothing else changes in it.
- **4a-R3, Review's validity** (§5.7 "Continue"; §6.12; §19 "Review is no longer always valid"). Review reports invalid only while a returned list holds a `gate`. While the check is loading, and when it failed, Review is valid: the server refuses a `gate` anyway (§5.7 "Complete refuses a `gate` gap"), so the list is information for the filer, not the lock on the button, and a request that never answers (`apiFetch` has no timeout, `client.ts:288`) can't leave a filer on a page whose one button is disabled with no words. A failed check says `REVIEW_GAPS_UNAVAILABLE`; a loading one shows nothing. Review's own gates arrive in 4i. Negative: a `detail` never disables Complete; once a list with a `gate` arrives Complete is disabled until the next fetch; a refused Complete still re-fetches, so a stale list is corrected by the press; a press during loading reaches the server, whose refusal lists the gaps.
- **4a-R4, the dashboard's per-card line waits.** B46's "each affected form's card repeats the line" is written for a `detail`, which affects the forms that print it. A `gate` refuses every form at once (`_prepare`), so for a gate "each affected card" is every pending card, and the Generate All refusal under the button already says it once; repeating it on fourteen cards adds nothing a filer can act on. The notice above Generate All lands here; the per-card line lands with the first `detail` (4b), whose gap function knows its form. Negative: `FormCard` gains no new prop in 4a.
- **4a-R5, the notice names a `gate` as missing and a `detail` as blank** (spec correction 1). B46's sentence ("N answers are blank on your forms.") is a `detail`'s: a `detail` prints blank (§5.7 line 211). A `gate` prints nothing, because every caller of `_prepare` refuses the whole call, so saying "blank on your forms" for a gate tells a filer something false on the page where they download sworn forms, and contradicts the 422 shown under the button a moment later. The dashboard heading therefore comes in two sentences, each scored: with any `gate`, `DASHBOARD_GATES_ONE` / `DASHBOARD_GATES_MANY` counting the gates ("… still missing. Your forms can't be prepared until …"); with any `detail`, B46's `DASHBOARD_GAPS_ONE` / `DASHBOARD_GAPS_MANY` counting the details; both present → the gate sentence first. 4a has no `detail`, so only the gate sentence can show in 4a; the detail pair is defined and tested with a synthetic `detail` so 4b adds no copy. Negative: an empty list renders nothing (not "Nothing is missing", which is Review's); every gap of either kind still gets its line and its "Go to {step}".
- **4a-R6, the "Not answered yet" line is caller-controlled.** `YesNoThenDetails` shows it only under `unanswered` (the boolean `YesNoQuestion`'s own prop, `steps/YesNoQuestion.tsx:9`, which `HouseholdList.tsx:145` sets as `touched && answer == null`), so the four means-test callers change nothing on their page. Negative: Task 6's test 6 of Review Focus.
- **4a-R7, the namespace reader is generic, not one-read, and prints no structure.** §14.2's "reads its record once per resolve" is the one-read context manager of `means_lines_for`; with no binding using the namespaces, a `getattr(session, "<related>", None)` per call is the whole of 4a's reader, and the PR that binds the first key adds the one-read when it adds the record. A `dict` or `list` stored under a scalar binding (§7.3's `intentions.secured` is "a JSON object keyed by `DebtInfo.id`", not a scalar) reads as `""`, the spec's own rule for a value whose shape is wrong (§5.7 B47 "the derivation prints blank"), never `str(dict)` onto a form. Negative: `resolve_binding("petition.x", session)` on a real session is `""`, never an exception, and never a query the resolver didn't make before for `answer:`; a list binding (`[].`) over a list of objects still returns the list.
- **4a-R8, `binding_fix` by key table.** `petition.` → the step that asks the key (§7.1's brackets, the table in Task 3), `schedule_i.` → `income_info` unless the key starts `schedule_j_` → `expense_info`, `intentions.` → `plans`, `affairs.l<n>_…` → `last_few_years_1` for `n ≤ 12`, `last_few_years_2` above. An unlisted `petition.` key, and an `affairs.` key not matching `^l(\d+)_` (§14.4 spells line 6's rows `affairs.pay6[]` where §7.4 has `l6_rows`; spec correction 4), raise `ValueError`, as `resolve_binding` does for an unrecognized binding, so a misspelt key is found by the tier 1 test the binding PR adds, never linked to a wrong step. Negative: every other namespace's fix is unchanged (`test_rule_fixes.py:252-262` rows pass as they are); every step `record_step` can return is a `WIZARD_STEPS` key or one of `NEW_STEP_KEYS` (§5.7 line 215, tested for all four namespaces).
- **4a-R9, the public-record notice carries the clerk's number only** (spec correction 3). B49 says "with the resource `TRAUMA_INFORMED_DESIGN.md` §IV names"; that section's only resource is the literal placeholder "[Link to DV safety planning]" (`docs/TRAUMA_INFORMED_DESIGN.md:385`), so there is nothing real to print. `PUBLIC_RECORD_NOTICE` is the two sentences the spec quotes, under `// DRAFT: counsel C-40`, and the component takes no `resource` prop: when counsel names one it is a sentence added to the constant under the same mark. Negative: the notice is still information (what exists, not what to do); nothing in 4a renders it on a step.

## Dry run

*(Left empty for the throwaway full build. It records the branch, the per-task counts from pytest's last line and vitest's summary, the defects found and folded, and anything Review Focus item 2 enumerated.)*

---

### Task 1: `apps/intake/completion.py`: `Gap`, `completion_gaps`, `WIZARD_STEP_COUNT`; Complete, `update_step` and the gaps endpoint read them

**Files:**
- Create: `backend/apps/intake/completion.py`
- Modify: `backend/apps/intake/views.py:29,136-150,224-276,278-348`
- Test: `backend/apps/intake/tests/test_completion_gaps.py` (new). `test_completion.py` is not touched: it spells the three take-home and Expenses sentences itself (`:234-242`) rather than importing them, so the words stay pinned there on purpose.

**Interfaces:**
- Produces: `class Gap(Exception)` with `__init__(self, message: str, step: str, kind: str)`, attributes `message`, `step`, `kind`, `str(gap) == message`; `GATE = "gate"`, `DETAIL = "detail"`; `completion_gaps(session) -> list[Gap]`; `WIZARD_STEP_COUNT: int`; `TAKE_HOME_PAY_NOT_ENTERED`, `SPOUSE_TAKE_HOME_PAY_NOT_ENTERED`, `EXPENSES_INCLUDE_OTHERS_UNANSWERED`, `EXPENSES_STEP_NEVER_SAVED` (the inline sentence at `views.py:326`, now a constant) moved here from `views.py:140-150`; `GET /api/intake/sessions/{id}/gaps/` → `200 {"gaps": [{"message", "step", "kind"}]}`.

- [ ] **Step 1: Write the failing tests** in `test_completion_gaps.py`. Build sessions as `test_completion.py` does (its `filer`, `completed`, `_session_url`, `answer_asset_lines`, `_scanned_debt` helpers; its fixtures are `district`, `filer`, `completed` only, `:45-89`; import what it exports, copy what it doesn't). The other filer is built inline, as `test_means_hold.py:1370-1372` does. The "writes nothing" proof is `CaptureQueriesContext` (precedent `apps/intake/tests/test_claim_rows.py:12,348`): `IntakeSession` has no `updated_at` (`models.py:30-48` has `created_at` and `completed_at`; the `updated_at` columns at `:394,485,632` belong to other models), so §18.2's "`updated_at` unchanged" can't be asserted (spec correction 2).

```python
def test_the_gap_list_is_what_complete_refuses_in_the_same_order(filer, district):
    # the session of test_complete_lists_every_gap_in_wizard_order (test_completion.py:480-485)
    gaps = completion_gaps(session)
    response = client.post(_session_url(session, "complete/"))
    assert [(g.step, str(g)) for g in gaps] == [(e["step"], e["message"]) for e in response.data["errors"]]
    assert {g.kind for g in gaps} == {Gap.GATE}

def test_a_finished_intake_has_no_gaps(filer, completed):
    assert completion_gaps(completed) == []

def test_the_gaps_endpoint_returns_the_list_and_writes_nothing(filer, district):
    # the same unfinished session; then the completed fixture
    before = (session.status, session.current_step, session.completed_at)
    with CaptureQueriesContext(connection) as queries:
        response = client.get(_session_url(session, "gaps/"))
    assert response.status_code == 200
    assert response.data == {"gaps": [{"message": str(g), "step": g.step, "kind": "gate"} for g in completion_gaps(session)]}
    assert not [q["sql"] for q in queries if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))]
    session.refresh_from_db(); assert (session.status, session.current_step, session.completed_at) == before
    # completed: {"gaps": []}, the same no-write check, and status still "completed"

def test_the_gaps_endpoint_is_the_filers_own(filer, district):
    other = User.objects.create_user(username="otherfiler", email="other@example.com", password="testpass123")
    theirs = IntakeSession.objects.create(user=other, district=district)
    assert client.get(_session_url(theirs, "gaps/")).status_code == 404

def test_the_gaps_endpoint_answers_200_where_the_means_test_would_refuse(filer, district):
    # a session with no IncomeInfo row: the means test raises IncomeNotSplit (`district` is the real
    # ILND data, test_completion.py:45-50, so its median table is in force; the point is that the
    # endpoint never runs the means test, which the missing income row alone proves)
    assert response.status_code == 200
    assert any(g["step"] == "income_info" for g in response.data["gaps"])

def test_wizard_step_count_is_the_browsers():
    # copy the five-line _wizard_steps() reader and its FRONTEND path of test_rule_fixes.py:23-32
    # into this file (neither tests/ dir has an __init__.py, so importing from another test module
    # loads it twice); skip with that file's sentence (:122-123) when FRONTEND is not a dir
    assert WIZARD_STEP_COUNT == len(re.findall(r"key: '(\w+)'", steps_source))

def test_update_step_names_the_wizards_last_step_in_its_refusal(filer, completed):
    response = client.post(_session_url(completed, "update_step/"), {"current_step": WIZARD_STEP_COUNT + 1}, format="json")
    assert response.data == {"current_step": [f"Must be a whole number from 1 to {WIZARD_STEP_COUNT}."]}
```

- [ ] **Step 2: Run them to see them fail.** Run: `… python -m pytest apps/intake/tests/test_completion_gaps.py -q`. Expected: collection `ImportError` naming `apps.intake.completion`.

- [ ] **Step 3: Write `backend/apps/intake/completion.py`.** `WIZARD_STEP_COUNT = 9` with a comment naming `frontend/src/constants/wizardSteps.ts` and the test that pins it. The four sentence constants (moved verbatim). `class Gap(Exception)` as the Interfaces say, docstring in the `ClaimStepGap` voice (`claims.py:135-141`). `completion_gaps(session) -> list[Gap]`: the body of `complete` at `views.py:296-339` transposed, each `errors.append({...})` becoming `Gap(message, step, Gap.GATE)`, in that order (`_needs_ssn`, `_needs_county` caught as `PreconditionMissing`; `income_step_gaps`; the two take-home rows; the Expenses row and line 3; `asset_step_gaps`; `claim_step_gaps`), with the same imports `views.py:19-33` uses for them (`apps.forms.registry` imports nothing from `apps.intake.views` or this module, so the direction is the one `views.py:29` already takes).

- [ ] **Step 4: Rewrite `complete`** (`views.py:293-339`) as `errors = [{"step": g.step, "message": str(g)} for g in completion_gaps(session) if g.kind == Gap.GATE]`; keep the 400 body, the lock and the status write. Rewrite `update_step`'s bound (`:243`) as `not 1 <= current_step <= WIZARD_STEP_COUNT` and its message (`:246`) as the f-string; the comment at `:238` loses "9". Add, after `complete`:

```python
@action(detail=True, methods=["get"])
def gaps(self, request, pk=None):
    """What Complete would still refuse (kind "gate") and what prints blank (kind "detail"), in
    Complete's order: wizard order, with the claims tail last on purpose (3c4; the comment at
    `complete`, step 4 spec §5.7). Reads only: no lock, no write, never the packet or a form's
    preconditions."""
```
returning `Response({"gaps": [{"message": str(g), "step": g.step, "kind": g.kind} for g in completion_gaps(self.get_object())]})` (`get_queryset` filters by user, `:168-171`, so another filer's session is a 404 with no code). Delete the constants at `views.py:140-150` and the imports ruff now flags (F401) — `_needs_ssn`, `_needs_county`, `PreconditionMissing` if `complete` was their only reader, `income_step_gaps`, `counted_spouse_income`, `deductions_blank`, `schedule_i_line4`; `asset_step_gaps` and `claim_step_gaps` stay (`:855-857`); `IncomeNotSplit` and `income_window` stay used.

- [ ] **Step 5: Run the new file and the completion suite.** Run: `… python -m pytest apps/intake/tests/test_completion_gaps.py apps/intake/tests/test_completion.py apps/intake/tests/test_session_lock.py -q`. Expected: all pass; `test_completion.py`'s count unchanged from a1a697e. Then `… python manage.py check` (no issues) and `… python manage.py makemigrations --check --dry-run` ("No changes detected"). `… python -m ruff check apps/intake/completion.py apps/intake/views.py apps/intake/tests/test_completion_gaps.py` and `ruff format --check` on the two new files.

- [ ] **Step 6: Commit.**

```bash
/usr/bin/git add backend/apps/intake/completion.py backend/apps/intake/views.py backend/apps/intake/tests/test_completion_gaps.py
/usr/bin/git commit -m "intake: one completion gap list, read by Complete and a read-only gaps endpoint (step 4a)"
```

---

### Task 2: The forms views refuse the first gate gap; the view tests' sessions finish their intake

**Files:**
- Modify: `backend/apps/forms/views.py:94-147` (`_failure`), `:259-275` (`_prepare`)
- Modify: `backend/apps/intake/tests/builders.py` (one helper)
- Modify: the six completed-session fixtures Review Focus item 2 names: `backend/apps/forms/tests/test_form_views.py:129-141` (and the `ExpenseInfo.objects.create` at `:1284-1287`, deleted), `conftest.py:502-518`, `test_means_hold.py:94-100`, `test_schedule_c_gate.py:39`, `test_list_of_creditors.py:59`, `test_means_mark_filed.py:54`. Not touched, for the reasons Review Focus 2 gives: `test_api_readback.py`, `test_download_action.py`, `test_time_packet.py`, `test_filing_fee_forms.py`, `means_rows.py`. Step 4's grep is the guard for a seventh.
- Test: `backend/apps/forms/tests/test_form_views.py`, `backend/apps/forms/tests/test_means_mark_filed.py`, `backend/apps/intake/tests/test_seed_demo_data.py`

**Interfaces:**
- Consumes: `Gap`, `completion_gaps` (Task 1).
- Produces: `finish_intake(session, **expense_over) -> None` in `builders.py`, exactly `ExpenseInfo.objects.update_or_create(session=session, defaults={"expenses_include_others": "no", **expense_over})`, so a session that `answer_household` finished passes `completion_gaps` (its `payroll_tax` default of `$0` already covers take-home pay, `builders.py:83`). `update_or_create`, because `ExpenseInfo.session` is a `OneToOneField` (`models.py:539`) and some tests create the row themselves. `"no"`, never `False`: `expenses_include_others` is an `EncryptedCharField(max_length=3)` (`models.py:629`) holding the form's own words through a `ChoiceField` (`serializers.py:406`), and `_schedule_j_expenses_include_others` prints the stored string onto Schedule J (`derivations.py:857-860`), so a boolean would print "False" on every view test's form and be a No the filer did not give (§5.3). The docstring says so.

- [ ] **Step 1: Write the failing tests.** In `test_form_views.py`, beside `test_form_101_without_a_county_names_the_your_information_step` (`:243`); the file has no module-level URL constant (only `URL` inside a class, `:455`), so module-level tests spell the path as `:616-617` does:

```python
def test_generate_all_refuses_a_gate_gap_naming_its_step(api_client, session_with_debtor):
    ExpenseInfo.objects.filter(session=session_with_debtor).delete()
    resp = api_client.post("/api/forms/generate_all/", {"session_id": session_with_debtor.id}, format="json")
    assert resp.status_code == 422
    assert resp.data == {"error": EXPENSES_STEP_NEVER_SAVED, "step": "expense_info"}

def test_generate_refuses_the_same_gate_gap_with_its_form_type(api_client, session_with_debtor):
    assert resp.data == {"form_type": "form_121", "error": EXPENSES_STEP_NEVER_SAVED, "step": "expense_info"}

def test_a_refused_generate_all_deletes_no_stored_form(api_client, session_with_debtor, user):
    # a GeneratedForm of a type outside the packet, then the refusal above: the row survives
    assert GeneratedForm.objects.filter(pk=stale.pk).exists()

def test_the_packet_list_never_refuses_a_gate_gap(api_client, session_with_debtor):
    # the same session: GET /api/forms/packet/?session= is 200 with form_types
```
In `test_means_mark_filed.py`, with its `session_with_debtor` fixture (`:51`) and `_mark_filed(api_client, row)` helper (`:90-91`, `POST /api/forms/{pk}/mark_filed/`), beside `test_a_stale_122a1_row_cant_be_filed_around_the_hold` (`:108`):

```python
def test_a_gate_gap_refuses_marking_the_pair_filed_and_marks_neither(api_client, session_with_debtor):
    # generate the pair, delete the session's ExpenseInfo row, _mark_filed on the 122A-1 row:
    # 422 {"form_type": "form_122a1", "error": EXPENSES_STEP_NEVER_SAVED, "step": "expense_info"}
    # (the shape _failure gives mark_filed today) and both rows still "generated"
```
In `test_seed_demo_data.py`: `test_every_seeded_persona_has_no_gate_gap` — after `loaddata ilnd_2025_data` and `seed_demo_data` (the file's existing setup), `assert [(s.user.username, str(g)) for s in IntakeSession.objects.filter(status="completed") for g in completion_gaps(s) if g.kind == Gap.GATE] == []`.

- [ ] **Step 2: See them fail.** Run: `… python -m pytest apps/forms/tests/test_form_views.py -q -k "gate_gap or deletes_no_stored or never_refuses"`, `… python -m pytest apps/forms/tests/test_means_mark_filed.py -q -k gate_gap` and `… python -m pytest apps/intake/tests/test_seed_demo_data.py -q -k no_gate_gap`. Expected: three `test_form_views.py` tests red — the first two see 200 where 422 is asserted (or the oracle's first-row refusal), the third sees its row deleted (today `_prepare` lets the missing row through and the delete at `forms/views.py:463-465` runs); the packet test is green before and after (a negative case); the `mark_pair_filed` test red (the pair is marked); the persona test red or green (record which; a red one is a seed defect to fix in `seed_demo_data.py` in this task, with the persona named in the commit body).

- [ ] **Step 3: Rewrite `_prepare`** (`forms/views.py:259-275`): `_check_finished(session)`; `gates = [g for g in completion_gaps(session) if g.kind == Gap.GATE]`; `if gates: raise gates[0]`; `_recalculate_means_test(session)`. Docstring: the list is Complete's (4a-R1), first gate first, means test after, and it names its six callers (Generate, Generate All, Regenerate, an unfiled download, Mark as Filed on an unfiled means-pair form, `mark_pair_filed`). Add `Gap` to `_failure`'s isinstance list (`:122-130`) and to the comment above `_FAILURE_SENTENCES` (`:94-96`); import it beside `ClaimStepGap` (`:29`). The import lines `:28-29` become `from apps.intake.asset_lines import AssetStepGap` and `from apps.intake.claims import ClaimStepGap`: `asset_step_gaps` and `claim_step_gaps` were called only inside `_prepare` (`:269,272`), so ruff flags both (F401) once it is rewritten; the two classes stay in `_failure`'s isinstance list, since `completion_gaps` is not the only path that can raise them. `_recalculate_means_test` is left as it is: its own `income_step_gaps` raise (`:203`) is still live for the packet list, which calls it without `completion_gaps`.

- [ ] **Step 4: Add `finish_intake`** to `builders.py` after `answer_household`, and call it in each of the six fixtures, directly after that fixture's `answer_household(session)`. Delete the `ExpenseInfo.objects.create(...)  # Complete requires it` at `test_form_views.py:1284-1287` (the fixture now carries the row; the create would be an `IntegrityError`). Then the guard: `grep -rn 'ExpenseInfo.objects.create\|ExpenseInfo(session' backend/apps/forms/tests/` — any remaining create on a session a `finish_intake` fixture built becomes an `update` or goes (at a1a697e the others are on local `session` fixtures of their own: `test_schedule_j_schema.py`, `test_schedule_j_payments.py`, `test_form_103b_answers.py`, `test_form_106sum_schema.py`, none of which calls a view); and `grep -rln 'status="completed"' backend/apps/forms/tests/` against `grep -rln '"/api/forms/' backend/apps/forms/tests/` — a file in both lists that is not one of the six is the seventh fixture, and gets the call. A fixture the greps missed shows in Step 5 as a 422 "Go through the Expenses step…" or a take-home sentence.

- [ ] **Step 5: Run.** `… python -m pytest apps/forms/tests/test_form_views.py apps/forms/tests/test_download_action.py apps/forms/tests/test_api_readback.py apps/forms/tests/test_means_mark_filed.py apps/forms/tests/test_list_of_creditors.py apps/forms/tests/test_schedule_c_gate.py apps/forms/tests/test_time_packet.py apps/forms/tests/test_filing_fee_forms.py apps/forms/tests/test_schedule_j_schema.py -q` (`test_means_hold.py` in its own call: it runs minutes), then `apps/intake/tests/test_seed_demo_data.py`. Expected: all pass. `ruff check` on every file touched.

- [ ] **Step 6: Commit.**

```bash
/usr/bin/git add backend/apps/forms/views.py backend/apps/intake/tests/builders.py backend/apps/forms/tests/test_form_views.py backend/apps/forms/tests/conftest.py backend/apps/forms/tests/test_means_hold.py backend/apps/forms/tests/test_schedule_c_gate.py backend/apps/forms/tests/test_list_of_creditors.py backend/apps/forms/tests/test_means_mark_filed.py backend/apps/intake/tests/test_seed_demo_data.py
/usr/bin/git commit -m "forms: every caller of _prepare refuses what Complete would, first gate first (step 4a)"
```
The commit body names the six callers, the Generate All shape change for a missing `DebtorInfo` (4a-R1), and any persona the seed had to fix.

---

### Task 3: The four namespaces: `_BINDING_NAMESPACES`, `_LIST_BINDING`, `resolve_binding`, `binding_fix`

**Files:**
- Modify: `backend/apps/forms/schema.py:277-285,787-790`
- Create: `backend/apps/forms/services/answer_records.py`
- Modify: `backend/apps/forms/services/fill_resolver.py:441-536` (`resolve_binding`), `:587-621` (`binding_fix`)
- Test: `backend/apps/forms/tests/test_answer_records.py` (new), `backend/apps/forms/tests/test_rule_fixes.py:250-262`

**Interfaces:**
- Produces, in `answer_records.py`: `ANSWER_NAMESPACES = ("petition.", "schedule_i.", "intentions.", "affairs.")`; `RECORD_OF_NAMESPACE = {"petition.": "petition_answers", "schedule_i.": "schedule_i_answers", "intentions.": "intention_answers"}` (`affairs.` by line: `l1`–`l12` → `financial_affairs`, `l13`–`l28` → `property_affairs`, §7.4); `record_value(session, binding: str) -> str | list[str]`; `record_step(binding: str) -> str`; `PETITION_STEP_OF_KEY: dict[str, str]` holding every §7.1 key with its bracketed step (`name_suffix` … `business_kind`, `other_names`, `other_business_names`, `prior_cases`, `pending_cases` → `debtor_info`; `hazard_*` → `assets`; `debt_nature`, `debt_nature_text`, `disabled_veteran`, `debts_on_duty`, `reservist`, `called_to_duty`, `duty_category`, `duty_released_on`, `duty_ended_on` → `debts`; `rents_residence`, `eviction_judgment`, `landlord_*` → `contracts`; `credit_counseling`, `exigent_text`, `not_required_reason`, `aware_consequences`, `aware_fraud`, `paid_preparer`, `preparer_name` → `review`); `NEW_STEP_KEYS = ("plans", "last_few_years_1", "last_few_years_2")` (B1; each leaves this tuple when its PR adds it to `wizardSteps.ts`).

- [ ] **Step 1: Write the failing tests** in `test_answer_records.py` (DB-free where a stub session serves: `types.SimpleNamespace(petition_answers=SimpleNamespace(get_answers=lambda: {...}))`; one `@pytest.mark.django_db` test on a real `IntakeSession`).

```python
def test_a_session_with_no_record_reads_blank_and_empty(session):
    assert resolve_binding("petition.name_suffix", session) == ""
    assert resolve_binding("petition.prior_cases[].district", session) == []
    assert resolve_binding("affairs.l13_answer", session) == ""

def test_a_record_is_read_through_get_answers():
    stub = SimpleNamespace(petition_answers=SimpleNamespace(get_answers=lambda: {"name_suffix": "Jr.", "itin": None, "prior_cases": [{"district": "Northern", "filed_on": None}]}))
    assert record_value(stub, "petition.name_suffix") == "Jr."
    assert record_value(stub, "petition.itin") == ""          # a null is blank, never "None"
    assert record_value(stub, "petition.prior_cases[].district") == ["Northern"]
    assert record_value(stub, "petition.prior_cases[].filed_on") == [""]

@pytest.mark.parametrize("binding,step", [
    ("petition.name_suffix", "debtor_info"), ("petition.prior_cases[].district", "debtor_info"),
    ("petition.hazard_what", "assets"), ("petition.debt_nature", "debts"),
    ("petition.rents_residence", "contracts"), ("petition.landlord_zip", "contracts"),
    ("petition.paid_preparer", "review"), ("schedule_i.employer_name", "income_info"),
    ("schedule_i.schedule_j_line_24_answer", "expense_info"), ("intentions.secured", "plans"),
    ("affairs.l2_rows[].street", "last_few_years_1"), ("affairs.l12_statement", "last_few_years_1"),
    ("affairs.l13_answer", "last_few_years_2"), ("affairs.l28_rows[].amount", "last_few_years_2"),
])
def test_each_namespace_links_to_the_step_that_asks_it(binding, step):
    assert binding_fix(binding) == {"step": step}

def test_an_unlisted_petition_key_is_a_defect_not_a_wrong_step():
    with pytest.raises(ValueError): binding_fix("petition.not_a_key")

def test_an_affairs_key_without_a_line_is_a_defect_not_a_wrong_step():
    # §14.4 spells line 6's rows `affairs.pay6[]`; §7.4 names them `l6_rows` (4a-R8, spec correction 4)
    with pytest.raises(ValueError): binding_fix("affairs.pay6[].creditor")
    with pytest.raises(ValueError): record_value(SimpleNamespace(), "affairs.pay6[].creditor")

def test_structure_under_a_scalar_binding_reads_blank():
    # §7.3: intentions.secured is a JSON object keyed by DebtInfo.id, not a scalar (4a-R7)
    stub = SimpleNamespace(intention_answers=SimpleNamespace(get_answers=lambda: {"secured": {"7": {"intention": "keep"}}}))
    assert record_value(stub, "intentions.secured") == ""

@pytest.mark.parametrize("binding", [
    "petition.name_suffix", "petition.paid_preparer", "schedule_i.employer_name",
    "schedule_i.schedule_j_line_24_answer", "intentions.secured", "affairs.l2_answer", "affairs.l28_answer",
])
def test_every_step_a_namespace_names_is_a_wizard_step_or_a_reserved_key(binding):
    # wizard_keys from the copied _wizard_steps() reader | NEW_STEP_KEYS; plus every PETITION_STEP_OF_KEY value
    assert record_step(binding) in wizard_keys | set(NEW_STEP_KEYS)
    assert set(PETITION_STEP_OF_KEY.values()) <= wizard_keys | set(NEW_STEP_KEYS)

def test_the_schema_check_accepts_the_new_namespaces():
    # test_schema.py:73's synthetic field with binding "petition.name_suffix": no E007 "unknown binding namespace"
```
`wizard_keys` comes from a copy of the `_wizard_steps()` reader and its `FRONTEND` path (`test_rule_fixes.py:23-32`) in this file, with that file's skip sentence (`:122-123`) when `FRONTEND` is not a dir; the tests directories have no `__init__.py`, so importing one test module from another loads it twice. In `test_rule_fixes.py:252-262` add two rows: `(_field("asked", binding="petition.name_suffix"), {"step": "debtor_info"})`, `(_field("asked", binding="affairs.l13_answer"), {"step": "last_few_years_2"})`, **and** `"petition"`, `"affairs"` to the `ids=[...]` list at `:263-272` in the same edit (eight ids today; pytest refuses a parametrize whose `ids` count differs from its rows, at collection).

- [ ] **Step 2: See them fail.** Run: `… python -m pytest apps/forms/tests/test_answer_records.py apps/forms/tests/test_rule_fixes.py -q`. Expected: `ImportError` naming `answer_records`; the two new rows `ValueError: unrecognized binding` (a collection error instead means the `ids` list was not extended).

- [ ] **Step 3: Write `answer_records.py`.** `record_value`: split the namespace off, then `key, _, attr = rest.partition("[].")`; the record is `getattr(session, related_name, None)` (for `affairs.`, by the key's line number: `re.match(r"l(\d+)_", key)`, and no match raises `ValueError(f"unrecognized binding {binding!r}")`, the same words `resolve_binding`'s final raise uses); `None` → `[]` when `attr` else `""`; otherwise `answers = record.get_answers()`; a list binding → `[str(item.get(attr) or "") for item in answers.get(key) or []]`; a scalar binding → `""` if `answers.get(key) is None` or is a `dict` or `list` (4a-R7), else `str(...)`. `record_step`: 4a-R8, with the same `ValueError` for an unlisted `petition.` key and an `affairs.` key with no line. Then `schema.py:277-285` gains the four prefixes (keep the order: new ones after `means.`; `answer:` and `sofa.` stay); `_LIST_BINDING` (`:787-790`) gains `(?:petition|schedule_i|intentions|affairs)\.\w+` in its alternation, and the E007 message at `:870-878` names the four. In `fill_resolver.py`, before `resolve_binding`'s final `raise` (`:536`): `if binding.startswith(ANSWER_NAMESPACES): return record_value(session, binding)`; in `binding_fix`, before the `means.` branch: `if binding.startswith(ANSWER_NAMESPACES): return {"step": record_step(binding)}`. The docstring at `:441-460` gains one line per namespace.

- [ ] **Step 4: Run.** `… python -m pytest apps/forms/tests/test_answer_records.py apps/forms/tests/test_rule_fixes.py apps/forms/tests/test_schema.py apps/forms/tests/test_checks.py apps/forms/tests/test_fill_resolver.py -q` — all pass; `… python manage.py check` (the startup schema check runs over every schema, none of which binds the new names) prints no issue. `ruff check` on the four files; `ruff format --check` on `answer_records.py` and `test_answer_records.py`.

- [ ] **Step 5: Commit.**

```bash
/usr/bin/git add backend/apps/forms/schema.py backend/apps/forms/services/answer_records.py backend/apps/forms/services/fill_resolver.py backend/apps/forms/tests/test_answer_records.py backend/apps/forms/tests/test_rule_fixes.py
/usr/bin/git commit -m "forms: the petition, schedule_i, intentions and affairs namespaces, with nothing bound yet (step 4a)"
```

---

### Task 4: Review reads the gap list; the wizard fetches it; the autosave reservation

**Files:**
- Modify: `frontend/src/types/api.ts:1289-1292` (beside `CompletionError`), `frontend/src/api/client.ts:393-401`, `frontend/src/test/mocks/handlers.ts:186`
- Modify: `frontend/src/constants/copy.ts`
- Modify: `frontend/src/pages/IntakeWizard.tsx:257-258,548-562,641-672,971-993`
- Modify: `frontend/src/components/wizard/steps/ReviewStep.tsx:81-104,124-127,212-232`
- Test: `frontend/src/components/wizard/steps/__tests__/ReviewStep.test.tsx:216-220`, `frontend/src/pages/__tests__/IntakeWizard.test.tsx:195-345`, `frontend/src/api/__tests__/client.test.ts`

**Interfaces:**
- Consumes: `GET /api/intake/sessions/{id}/gaps/` (Task 1).
- Produces: `export interface CompletionGap { message: string; step: string; kind: 'gate' | 'detail' }`; `export interface GapsResponse { gaps: CompletionGap[] }`; `intakeAPI.gaps(sessionId: number): Promise<GapsResponse>`; `ReviewStep` props `gaps: CompletionGap[] | null` and `gapsStatus: 'loading' | 'done' | 'failed'` replacing `completionReasons`; `ALWAYS_AUTOSAVE_STEPS` in `IntakeWizard.tsx`; copy `REVIEW_NOTHING_MISSING = 'Nothing is missing.'`, `REVIEW_GAPS_UNAVAILABLE = "We couldn't check what is still missing. Press Complete to try again."`.

- [ ] **Step 1: Write the failing tests.** `ReviewStep.test.tsx`: replace `signals the step is always valid to proceed` with

```ts
it('is valid once the server lists no gate gap, and not while one stands', ...)   // gaps [] / done → true; one gate → false
it('a detail gap never blocks Complete', ...)                                       // one detail → true
it('says Nothing is missing with an empty list', ...)                               // REVIEW_NOTHING_MISSING in .review-reasons
it('lists each gap with a way to its step', ...)                                    // message text; button 'Go to Income' calls onGoToStep(2)
it("a gap on a step the wizard doesn't know shows its words and no button", ...)   // step 'plans': text, no button
it('an unreachable check leaves Complete enabled and says so', ...)                 // status 'failed' → true, REVIEW_GAPS_UNAVAILABLE
it('a check that has not answered leaves Complete enabled', ...)                    // status 'loading' → onValidationChange(true), region empty (4a-R3)
```
`IntakeWizard.test.tsx`: `refuseComplete` (`:285-300`) becomes two-phase: it also installs `http.get(…/sessions/:id/gaps/)`, which answers `{ gaps: [] }` until the `complete/` POST handler has refused once (`let refused = false`, flipped inside the POST handler) and `{ gaps: errors.map(e => ({ ...e, kind: 'gate' })) }` after, so Review is valid before the press and lists the refusal after it; a one-phase override would list two gates at mount, Review would report invalid, and `userEvent.click` on the disabled Complete button (`WizardLayout.tsx:208`, `disabled={!canGoNext || isLoading}`) would do nothing. Add a `pressComplete()` helper in that file: `const btn = await screen.findByRole('button', { name: /complete intake/i }); await waitFor(() => expect(btn).toBeEnabled()); await userEvent.click(btn);` and use it in every test that presses Complete (`:173`, `:201`, `:239`, `:313`, `:339`, `:361`, `:374`, `:408`, `:437`, `:455`; none waits for enablement today, `toBeEnabled` appears only for Continue). The "lists each thing Complete found missing" test (`:313`) then passes with its assertions unchanged. Add `Review reads the gap list when it opens, before Complete is pressed` (the gaps handler returns one gate; its words and button show with no click, and Complete is disabled) and `a refused Complete re-reads the list` (the two-phase handler; assert two GETs and the list). `client.test.ts`: `gaps GETs the session's gaps` (URL and method, the file's existing shape).

- [ ] **Step 2: See them fail.** Run: `cd frontend && NODE_OPTIONS=--no-experimental-webstorage npx vitest run --maxWorkers=2 src/components/wizard/steps/__tests__/ReviewStep.test.tsx src/pages/__tests__/IntakeWizard.test.tsx src/api/__tests__/client.test.ts`. Expected: the new tests fail (`api.intake.gaps is not a function`; the always-valid effect).

- [ ] **Step 3: Types, client, handler, copy.** `CompletionGap`, `GapsResponse` in `types/api.ts`; `gaps` in `intakeAPI` after `completeSession` (`client.ts:397`), `apiFetch<GapsResponse>(\`/intake/sessions/${sessionId}/gaps/\`)`; the default handler `http.get(\`${API}/intake/sessions/:id/gaps/\`, () => HttpResponse.json({ gaps: [] }))` beside `complete/` (`handlers.ts:186`); the two copy constants.

- [ ] **Step 4: `IntakeWizard.tsx`.** Replace `completionErrors` (`:258`) with `const [gaps, setGaps] = useState<CompletionGap[] | null>(null)`, `const [gapsStatus, setGapsStatus] = useState<'loading' | 'done' | 'failed'>('loading')`, `const [gapsRead, setGapsRead] = useState(0)`. One effect on `[sessionRead, currentStepKey, session?.id, gapsRead]`: when `sessionRead === 'done' && currentStepKey === 'review' && session`, set `loading`, await `api.intake.gaps(session.id)`, set the list and `done`, or `failed` on a throw (and `console.error` it); a stale reply is ignored with a cancelled flag. `handleComplete`'s catch (`:664-668`): `setGapsRead((n) => n + 1)` in place of `setCompletionErrors`; `moveToStep` stops clearing reasons. `const ALWAYS_AUTOSAVE_STEPS: readonly string[] = ['assets', 'debts', 'contracts', 'codebtors', 'plans', 'last_few_years_1', 'last_few_years_2', 'review']` above `useAutoSave` (typed `readonly string[]`, not `as const`: `currentStepKey` is `string | undefined` because `WIZARD_STEPS` is not `as const`, `wizardSteps.ts:5`, `IntakeWizard.tsx:414`, and a literal tuple's `includes` would be TS2345 under `tsc`) with the comment "the three step-4 steps and Review always autosave (step 4 spec §6.0, B3); Review has no body until 4i, so the exclusion below stands"; `enabled` reads `ALWAYS_AUTOSAVE_STEPS.includes(currentStepKey ?? '')` in place of the inline array (`:559-560`) and keeps `currentStepKey !== 'review'`. The `review` case (`:971-993`) passes `gaps`, `gapsStatus`, `onGoToStep`.

- [ ] **Step 5: `ReviewStep.tsx`.** Props as the Interfaces say. The effect at `:124-127` becomes `onValidationChange(!(gapsStatus === 'done' && (gaps ?? []).some((g) => g.kind === 'gate')))` on `[gaps, gapsStatus, onValidationChange]` (4a-R3: invalid only while a returned list holds a gate; loading and failed leave the server to decide). The `review-reasons` region (`:215-232`): `failed` → `<p>{REVIEW_GAPS_UNAVAILABLE}</p>`; `done` and empty → `<p>{REVIEW_NOTHING_MISSING}</p>`; `done` with gaps → today's list, the step looked up by key in `WIZARD_STEPS` (no match → no button); `loading` → nothing.

- [ ] **Step 6: Run.** The three vitest files pass; `npx tsc -p tsconfig.app.json --noEmit` clean; `npx eslint` and prettier on the files touched. Then the whole `src/pages/__tests__/IntakeWizard.test.tsx` once more (its other Complete tests use `refuseComplete`).

- [ ] **Step 7: Commit.**

```bash
/usr/bin/git add frontend/src/types/api.ts frontend/src/api/client.ts frontend/src/test/mocks/handlers.ts frontend/src/constants/copy.ts frontend/src/pages/IntakeWizard.tsx frontend/src/components/wizard/steps/ReviewStep.tsx frontend/src/components/wizard/steps/__tests__/ReviewStep.test.tsx frontend/src/pages/__tests__/IntakeWizard.test.tsx frontend/src/api/__tests__/client.test.ts
/usr/bin/git commit -m "wizard: Review lists the server's gaps and is valid only with no gate standing (step 4a)"
```

---

### Task 5: The dashboard's gap notice; a card's Answer Questions follows its refusal

**Files:**
- Create: `frontend/src/components/forms/GapsNotice.tsx`
- Modify: `frontend/src/pages/FormDashboard.tsx:185-200,198-230 (the mount load),560-575`, `frontend/src/components/forms/FormCard.tsx:152-158`, `frontend/src/components/forms/index.ts`, `frontend/src/constants/copy.ts`
- Test: `frontend/src/pages/__tests__/FormDashboard.test.tsx`, `frontend/src/components/forms/__tests__/FormCard.test.tsx:115-138`, `frontend/src/components/forms/__tests__/GapsNotice.test.tsx` (new)

**Interfaces:**
- Consumes: `CompletionGap`, `intakeAPI.gaps` (Task 4).
- Produces: `GapsNotice({ gaps }: { gaps: CompletionGap[] })`; copy, each scored: `DASHBOARD_GATES_ONE = "1 answer is still missing. Your forms can't be prepared until it is given."`, `DASHBOARD_GATES_MANY = "{count} answers are still missing. Your forms can't be prepared until each is given."` (the `gate` sentences, 4a-R5, spec correction 1: a gate is what `_prepare` refuses, so nothing prints), and B46's `DASHBOARD_GAPS_ONE = '1 answer is blank on your forms.'`, `DASHBOARD_GAPS_MANY = '{count} answers are blank on your forms.'` (the `detail` sentences; no `detail` exists in 4a, so they are defined and tested here and first shown by 4b); `{count}` filled with `String(n)`.

- [ ] **Step 1: Write the failing tests.** `GapsNotice.test.tsx`: `renders nothing for an empty list`; `a gate gap is named as missing, not as blank` (one gate → `DASHBOARD_GATES_ONE`, and no "blank" in the section's text); `names the count and one way per affected step, in wizard order` (gates on `expense_info`, `income_info`, `income_info` → heading "3 answers are still missing. Your forms can't be prepared until each is given.", links `Go to Income` → `/intake?step=income_info` then `Go to Expenses`, each step's messages under it, one link per step); `a detail gap is named as blank` (one synthetic `detail` → `DASHBOARD_GAPS_ONE`); `with both kinds the missing sentence comes first` (one gate, two details → `DASHBOARD_GATES_ONE` then `DASHBOARD_GAPS_MANY` with "2", in that document order); `a gap on an unknown step shows its words and no link`. `FormDashboard.test.tsx` (its `renderFormDashboard()` and `server.use` shape, `:180-200`): `names each missing answer above Generate All` (the notice precedes the Generate All button in document order: `compareDocumentPosition`); `shows no gap notice when nothing is missing`; `a failed gaps check shows no notice and the forms still load` (handler 500; the packet and cards render; `console.error` called once, spied). `FormCard.test.tsx:115`: add `a pending card's button goes where its refusal points and takes its label, before answerPath` (refusal `{message, link: {to: '/intake?step=debtor_info', label: 'Go to Your Information'}}` and `answerPath="/means-test"` → the button reads "Go to Your Information" and navigates to `/intake?step=debtor_info`); the existing `/ask/` fallback case stays, and still reads "Answer Questions".

- [ ] **Step 2: See them fail.** Run: `NODE_OPTIONS=--no-experimental-webstorage npx vitest run --maxWorkers=2 src/components/forms src/pages/__tests__/FormDashboard.test.tsx`. Expected: `GapsNotice` not found; the FormCard test finds no "Go to Your Information" button and navigates to `/means-test`.

- [ ] **Step 3: `GapsNotice.tsx`.** `<section className="form-dashboard-gaps" role="status">` → one `<p>` per kind present, gates first (`DASHBOARD_GATES_*` with the gate count, then `DASHBOARD_GAPS_*` with the detail count, singular at 1) → `<ul>` with one `<li>` per distinct `step`, ordered by `WIZARD_STEPS` index (unknown keys last, in first-seen order), each holding a `<p>` per message and, when the key is in `WIZARD_STEPS`, `<Link to={\`/intake?step=${key}\`} className="button button--primary">Go to {label}</Link>` (the `fixLink` words, `FormDashboard.tsx:98-101`). Export from `components/forms/index.ts`.

- [ ] **Step 4: `FormDashboard.tsx`.** `const [gaps, setGaps] = useState<CompletionGap[]>([])`; in the mount load beside `loadForms`, `api.intake.gaps(session.id).then((r) => setGaps(r.gaps)).catch((err) => { console.error('Failed to read the gap list', err); setGaps([]); })` (no notice on a failed check, as Task 4's Review does on a throw: the dashboard's own error path is the packet's, and Review already said what was missing; the error is logged, never swallowed); render `<GapsNotice gaps={gaps} />` directly above the `form-dashboard-generate-all` div (`:568`). `FormCard.tsx:155-159`: `onClick={() => navigate(refusal?.link?.to ?? answerPath ?? \`/ask/${formType}\`)}` and the label `{refusal?.link?.label ?? 'Answer Questions'}` (§14.1: the button "becomes 'Go to {step}' from the form's first `PreconditionMissing`"; `FormRefusal.link` already carries `{to, label}`, `:24-27`, with `fixLink`'s "Go to {label}"); the `answerPath` doc comment (`:45`) says a refusal's link, and its label, come first.

- [ ] **Step 5: Run.** The three test files pass; `tsc -p tsconfig.app.json --noEmit`; eslint and prettier on the files touched; `src/test/accessibility.test.tsx` once (the dashboard is in it).

- [ ] **Step 6: Commit.**

```bash
/usr/bin/git add frontend/src/components/forms/GapsNotice.tsx frontend/src/components/forms/index.ts frontend/src/components/forms/FormCard.tsx frontend/src/pages/FormDashboard.tsx frontend/src/constants/copy.ts frontend/src/components/forms/__tests__/GapsNotice.test.tsx frontend/src/components/forms/__tests__/FormCard.test.tsx frontend/src/pages/__tests__/FormDashboard.test.tsx
/usr/bin/git commit -m "dashboard: every missing answer named above Generate All; a card's button follows its refusal (step 4a)"
```

---

### Task 6: `YesNoThenDetails`, `SectionIntro`, `FramingLine`, `PublicRecordNotice`, `WhatDoesThisMean`

**Files:**
- Move: `frontend/src/pages/meansTest/YesNoQuestion.tsx` → `frontend/src/components/wizard/YesNoThenDetails.tsx` (`/usr/bin/git mv`)
- Modify: `frontend/src/pages/MeansTestPage.tsx:94`, `frontend/src/pages/meansTest/Line43.tsx:42`, `DebtQuestions.tsx:16`, `SpouseBlock.tsx:38` (the import and the tag)
- Create: `frontend/src/components/wizard/SectionIntro.tsx`, `FramingLine.tsx`, `PublicRecordNotice.tsx`, `WhatDoesThisMean.tsx`
- Modify: `frontend/src/constants/copy.ts`
- Test: `frontend/src/components/wizard/__tests__/YesNoThenDetails.test.tsx`, `frontend/src/components/wizard/__tests__/frame.test.tsx`, `frontend/src/test/upl-frame-copy.test.ts` (all new)

**Interfaces:**
- Produces: `YesNoThenDetails` with the moved component's props (`question`, `name`, `value: YesNo | null`, `onChange`, `note?`, `id?`, `legendRef?`, `children?`) plus `unanswered?: boolean`; `SectionIntro({ asks, why, minutes }: { asks: string; why: string; minutes: number })`; `FramingLine({ children })` → `<p className="form-help-text framing-line">`; `PublicRecordNotice()` → `<p role="note" className="form-help-text public-record-notice">{PUBLIC_RECORD_NOTICE}</p>`; `WhatDoesThisMean({ citation, children }: { citation: string; children: ReactNode })` → `<details className="what-does-this-mean"><summary>{WHAT_DOES_THIS_MEAN}</summary><blockquote>{children}</blockquote><p className="form-help-text">{citation}</p></details>`.
- Copy, exactly: `SECTION_INTRO_TIME = 'This step takes about {minutes} minutes.'`; `SECTION_INTRO_PAUSE = 'You can stop at any time. What you have typed is saved.'`; `PUBLIC_RECORD_NOTICE = "What you file with the court can be seen by the public. If an address raises a safety concern for you, the court's clerk can tell you what options exist: (312) 408-5000."` under `// DRAFT: counsel C-40` (§6.0 B49's quoted sentences, verbatim; B49's "resource `TRAUMA_INFORMED_DESIGN.md` §IV names" is a placeholder in that document and is left to counsel under C-40, 4a-R9, spec correction 3; the component takes no `resource` prop); `WHAT_DOES_THIS_MEAN = 'What does this mean?'` (B43: the children are the statute's or the court's words verbatim, never a paraphrase; the component's doc comment says so and carries `// DRAFT: counsel`).

- [ ] **Step 1: Write the failing tests.** `YesNoThenDetails.test.tsx`: `offers No before Yes with nothing checked while unanswered`; `the details render inside the fieldset after the answer`; `says Not answered yet only when the caller says so` (with `unanswered` → `NOT_ANSWERED_YET`; without → absent); `without unanswered nothing is added below the answer` (the fieldset's text equals question + required mark + No + Yes + children); `the legend takes focus through its ref`. `frame.test.tsx`: `SectionIntro` prints the three sentences with the minutes filled; `FramingLine` renders its child as help text; `PublicRecordNotice` renders the notice as a note; `WhatDoesThisMean` is collapsed by default, its summary reads "What does this mean?", and opening it shows the quoted text and the citation; one `axe` run over the four together (vitest-axe, as `accessibility.test.tsx` does). `upl-frame-copy.test.ts`: the `ADVICE` array of `upl-claims-copy.test.ts:14-33` copied; `FRAME_NAMES = ['REVIEW_NOTHING_MISSING', 'REVIEW_GAPS_UNAVAILABLE', 'DASHBOARD_GATES_ONE', 'DASHBOARD_GATES_MANY', 'DASHBOARD_GAPS_ONE', 'DASHBOARD_GAPS_MANY', 'SECTION_INTRO_TIME', 'SECTION_INTRO_PAUSE', 'PUBLIC_RECORD_NOTICE', 'WHAT_DOES_THIS_MEAN']`; each exists in `copy` and matches no `ADVICE` pattern; `PUBLIC_RECORD_NOTICE` has `// DRAFT: counsel C-40` on the line above its `export const` (the regex of `upl-means-test-copy.test.ts:787`, reading `copy.ts` as text).

- [ ] **Step 2: See them fail.** Run: `NODE_OPTIONS=--no-experimental-webstorage npx vitest run --maxWorkers=2 src/components/wizard/__tests__ src/test/upl-frame-copy.test.ts`. Expected: module not found for each new file; the copy names missing.

- [ ] **Step 3: Move and rename.** `/usr/bin/git mv frontend/src/pages/meansTest/YesNoQuestion.tsx frontend/src/components/wizard/YesNoThenDetails.tsx`; rename the function and interface; fix the `REQUIRED_MARK` and `YesNo` import paths; add `unanswered` rendering `<p className="form-help-text">{NOT_ANSWERED_YET}</p>` between the radios and `{children}`; the doc comment says No then Yes, the details under the answer (§6.0 B4). Update the four importers' path and tag.

- [ ] **Step 4: The four components and the copy**, as the Interfaces say. `SectionIntro` fills `{minutes}` with `String(minutes)`.

- [ ] **Step 5: Run.** The three new test files, then the means-test files unchanged: `src/pages/__tests__/MeansTestPage.test.tsx src/pages/__tests__/MeansTestPage.debts.test.tsx src/pages/__tests__/MeansTestPage.line43.test.tsx src/pages/__tests__/MeansTestPage.polish.test.tsx src/test/reading-level.test.ts src/test/accessibility.test.tsx`; `tsc -p tsconfig.app.json --noEmit`; eslint and prettier on the files touched; `grep -rn "meansTest/YesNoQuestion" frontend/src` prints nothing.

- [ ] **Step 6: Commit.**

```bash
/usr/bin/git add frontend/src/components/wizard/YesNoThenDetails.tsx frontend/src/pages/meansTest/YesNoQuestion.tsx frontend/src/pages/MeansTestPage.tsx frontend/src/pages/meansTest/Line43.tsx frontend/src/pages/meansTest/DebtQuestions.tsx frontend/src/pages/meansTest/SpouseBlock.tsx frontend/src/components/wizard/SectionIntro.tsx frontend/src/components/wizard/FramingLine.tsx frontend/src/components/wizard/PublicRecordNotice.tsx frontend/src/components/wizard/WhatDoesThisMean.tsx frontend/src/constants/copy.ts frontend/src/components/wizard/__tests__/YesNoThenDetails.test.tsx frontend/src/components/wizard/__tests__/frame.test.tsx frontend/src/test/upl-frame-copy.test.ts
/usr/bin/git commit -m "wizard: the yes/no-then-details block and the intro, framing, public-record and definition components (step 4a)"
```

---

### Task 7: CLAUDE.md's "Forms need a completed intake" and "GenerateAll vs single"

**Files:**
- Modify: `CLAUDE.md:34` and `:39` (re-read as they stand). Only `CLAUDE.md` exists in this worktree: `.agents/AGENTS.md` and `.gemini/GEMINI.md` are untracked regular files in the main checkout (`git ls-files .agents .gemini` prints nothing here), not symlinks and not on this branch, so there is nothing else to edit.

- [ ] **Step 1: Rewrite the sentences the frame changed**, nothing else on either line. Line 34: "`update_step` takes only a whole number from 1 to 9" → "from 1 to `WIZARD_STEP_COUNT` (`apps/intake/completion.py`, 9 today, pinned to `WIZARD_STEPS.length` by `test_wizard_step_count_is_the_browsers`)". After "Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap" add: "— the gaps of `completion_gaps(session)` (`apps/intake/completion.py`), the one list, each a `Gap` with `message`, `step` and `kind` (`gate`, which Complete refuses, or `detail`, which prints blank and Complete lets through; every gap today is a `gate`). `GET /api/intake/sessions/{id}/gaps/` returns `{gaps: [{message, step, kind}]}` and writes nothing, never runs `packet()`, a form's `requires()` or the means test, and never lists a post-Complete page's gap. Review shows that list and nothing else (re-read after a refused Complete), says "Nothing is missing." when empty, and is invalid only while a returned list holds a `gate` (loading or a failed check leaves Complete to the server); the dashboard shows it above Generate All, a `gate` as "still missing" and a `detail` as "blank"." Replace "`_prepare` then raises the first `AssetStepGap` … before it works the means test out, so a session completed before 3b can't print A/B totals from rows no line owns" with "`_prepare` then raises the first `gate` of `completion_gaps` (a 422 `{error, step}` in the gap's own words) before it works the means test out, so every caller of `_prepare` refuses whatever Complete would: Generate, Generate All, Regenerate, an unfiled download, Mark as Filed on an unfiled means-pair form and `mark_pair_filed`". In "forms view tests need a completed session, with income by source and a district with a median table in force" add "and everything else Complete requires (`finish_intake` in `apps/intake/tests/builders.py` after `answer_household`, an `update_or_create` of the `ExpenseInfo` row with `expenses_include_others="no"`)". Keep the rest of the line as it is. Line 39: in "A refusal of the whole call is `{error}` with no `form_type`: Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source (422) or missing median data (500)" add after "an unfinished intake (422)": "or for any `gate` of `completion_gaps` (422 `{error, step}`; a completed session with no `DebtorInfo` is now a whole-call 422 on `debtor_info`, not a 200 with per-form `errors`)". Keep the rest of that line as it is.

- [ ] **Step 2: Check.** `grep -c "from 1 to 9" CLAUDE.md` prints `0`; `grep -c "completion_gaps" CLAUDE.md` prints at least `3`; `grep -c "mark_pair_filed" CLAUDE.md` prints at least `1`; `./node_modules/.bin/prettier --check ../CLAUDE.md` from `frontend/` passes (pre-commit runs prettier on it).

- [ ] **Step 3: Commit.**

```bash
/usr/bin/git add CLAUDE.md
/usr/bin/git commit -m "docs: the completion gap list, its endpoint and every _prepare caller's refusal (step 4a)"
```

---

## After the last task

The controller runs the gates (ruff, `manage.py check`, `makemigrations --check`, the whole backend suite, vitest whole, `tsc -p tsconfig.app.json --noEmit`, eslint, prettier, then the seven E2E journeys with the stack up and seeded) and compares counts with the dry run's. `known_defects.json` is still `[]`; `grep -c "answer:" data/forms/schemas/*.json` is unchanged from a1a697e (nothing bound, nothing unbound). The PR body lists U §5.2's items, Review Focus item 2's fixture set, the six `_prepare` callers and the Generate All shape change (4a-R1), and the five spec corrections in `.claude/handoff/2026-11-18-step4/plan-4a/spec-corrections.md` for the owner to fold into the spec.

## Self-review

- **Spec coverage of row 4a (§19 line 805).** `completion_gaps` extracted, the endpoint, Review's list, the dashboard's line — Tasks 1, 4, 5 (B6, B7, B46, with B46's heading read per 4a-R5); `YesNoThenDetails` — Task 6 (B4); `WIZARD_STEP_COUNT` pinned — Task 1 (B2); the three keys and `review` reserved — Task 4 (B3); the namespaces with nothing bound — Task 3 (B36); `FormCard`'s button reading the refusal's step and label, with the `/ask` fallback kept — Task 5 (B35, §14.1); the intro, framing and public-record components — Task 6 (B48, B49 per 4a-R9); "What does this mean?" — Task 6 (B43); the two gotchas — Task 7. Not 4a's, and not here: the attorney block, line 13, `SIGNING_LINES`, `STILL_PRINTS` (row 4b, §25 A-3); any record, migration or binding; the `reopen()` docstring and completion-test rewrite (4b, §5.6); Review's own save path and gates (4i, §6.0, §6.12). The per-card repeat of B46 is deferred by 4a-R4.
- **Step scan.** Each test step names its tests and assertions; each code step a signature, a file and the spec's values; no "handle edge cases". The one body given (`gaps` action) is a four-line view whose docstring is the decision.
- **Type consistency.** `Gap(message, step, kind)` / `Gap.GATE` in Tasks 1–2 and 7; `CompletionGap {message, step, kind}` and `intakeAPI.gaps` in Tasks 4–5; `ANSWER_NAMESPACES`, `record_value`, `record_step`, `PETITION_STEP_OF_KEY`, `NEW_STEP_KEYS` in Task 3 only; `ALWAYS_AUTOSAVE_STEPS` in Task 4 only; `finish_intake` in Task 2 and the gotcha; the four dashboard sentences in Task 5's copy and Task 6's `FRAME_NAMES`.
- **Review Focus.** Eight items, each pinned to a task's test (1, 2, 5, 8 → Task 2; 3, 4 → Tasks 4 and 5; 6 → Task 6; 7 → Task 5).
- **Reviews folded.** `review-fidelity.md` (14 findings) and `review-exec.md` (18) in `.claude/handoff/2026-11-18-step4/plan-4a/`; every disposition is in `plan-review-log.md` there. Rejected: E-17 only (the `_recalculate_means_test` raise is still live for the packet list).
- **Proportion.** About 430 lines against a 1,063-line spec whose 4a row is one table row; the code 4a writes (two modules, four components, one notice, ~45 tests) is longer than this plan.

<!-- prettier-ignore-end -->
