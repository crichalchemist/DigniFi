# Forms step 4c, income details (Schedule I lines 1, 11, 13 and Schedule J line 24): Implementation Plan

<!-- prettier-ignore-start -->

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The filer answers Schedule I line 1 (employment, occupation, employer, how long; the spouse's too when married filing together), line 11 (regular contributions) and line 13 (an expected change) on the Income step, and Schedule J line 24 on the Expenses step. The answers live in one new encrypted record, `ScheduleIAnswers`. Schedule I, Schedule J and Form 103B line 8 print them. Line 12 becomes line 10 + line 11, and 106Sum line 4 and Schedule J 23a and 23c follow it. The six dead `DebtorInfo` rules and `_safe_debtor_attr` go. The pay stub's employer name stops printing on its own and is shown beside the box as a hint.

**Architecture:**

- **The record.** `ScheduleIAnswers` (`apps/intake/models.py`, migration `intake 0045`, table `schedule_i_answers`, `related_name="schedule_i_answers"`, the name `RECORD_OF_NAMESPACE` already expects) holds one encrypted JSON column and `answered_on`, on the `PetitionAnswers` pattern. A session PATCH key `schedule_i_answers` sets only the keys sent, reopens a completed intake and takes the session lock.
- **The caps.** A new tool, `data/forms/field_index/tools/build_schedule_i_limits.py`, measures each text's narrowest box at 6 pt with `build_form_101a.py`'s formula and writes `data/forms/schemas/schedule_i.limits.json`. The model reads that file at import, with the same guards as Form 101's.
- **The gaps.** A new module, `apps/intake/schedule_i.py`, has `schedule_i_step_gaps(session) -> list[Gap]`, its sentences and one kind table. It reads the session by attribute and imports `ScheduleIAnswers` only for its key list and caps, as `petition.py:31` imports `PetitionAnswers`. Each gap carries its own step (`income_info`, or `expense_info` for line 24). `completion_gaps` splices them by `g.step`, as it splices `petition_step_gaps` (`completion.py:86, :109, :118`): the step 2 gaps right after `income_step_gaps`, and the line 24 gaps right after the Expenses step's. **`income_step_gaps` is untouched**, so the means test, 103B lines 1–3 and the household reads never see a 4c answer.
- **The prints.**
  - Line 1, 11 and 13 boxes and line 24 bind the `schedule_i.` namespace (or a derived rule for each amount), each gated by a `conditional_on` predicate.
  - Line 12 gets its own rule, `schedule_i_line_12`, bound by `Amount 12` and 106Sum `4`. J `23a` keeps its binding to `schedule_j_total_income`, now an alias of the new rule, so its tier 2 key doesn't change. J `23c` is computed from line 12. `Amount 10` keeps `schedule_i_income_total`.
  - 103B `Check 8` and "How much" read line 11.
- **The wizard.**
  - Step 2 gains the line 1 block (and the spouse's under `married_together`) and lines 11 and 13. Step 4 gains line 24.
  - Each step's body carries only its own `schedule_i_answers` keys.
  - Continue waits for the step's gates, computed by the wizard from its own state. Autosave keeps reading the amount checks alone.
- **E2E.** All nine journeys answer the new questions through `fillIncomeInfo` and `fillExpenses`, with each persona's data in `personas.ts`.

**Tech Stack:** No new dependency. Django 5.0 + DRF and pytest-django (sqlite). pypdf 6.13 and PyMuPDF (PDF-only scripts run with `/Users/controlroom/.claude/jobs/bb720722/tmp/venv-mac/bin/python -I`, never `backend/.venv`). React 19 + Vite + TypeScript, vitest + MSW + vitest-axe, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-18-forms-step4-design.md` (cited `S:line`). This plan builds:

- §6.2 (S:263-276), §6.4's line 24 half (S:280), §7.2 (S:418-420);
- §12 (S:596-605), §13.1's line 8 (S:628), row 3 (S:808);
- the §5 rules (S:153-219), §18's tests (S:762-795) and counsel C-42 (S:866).

The surveys, all read on 2026-11-22 at develop `d3a6ffa`, are in `.superpowers/plan-4c/`: `survey-spec.md` (`SS`), `survey-backend.md` (`SB`), `survey-frontend.md` (`SF`), `survey-forms.md` (`SFm`) and `survey-critic.md` (`SC`). The owner's words, defaults D1–D8 and persona drafts are in `.superpowers/plan-4c/owner-copy.md` (`OC`).

The spec's `path:line` cites date from 471f4ec and are stale (`SS` §(c)). Every cite below was re-read at `d3a6ffa`, and a task that lands earlier moves the lines after it. Where the spec is wrong or contradicts itself, "Corrections" at the end lists it, and the spec stays unedited.

**Owner answers, 2026-11-22:** words W1–W18 and §2 "Approve all"; defaults D1–D8 "Accept all eight"; personas "Approve the drafts" (P1–P4 as recommended). The gate below is met.

**Owner gate.**
- Tasks 2–8 write `OC`'s words or persona data. They wait for the owner's approval of `OC` §1, §2 and §4. Tasks 3 and 4 write `OC` §4's values into tier 3, and Task 3 builds on Task 2's seed.
- Only Task 1 can run before the owner answers. It depends only on defaults D1–D8 (`OC` §3), which this plan takes. A default the owner changes is a one-table edit (Rulings 4c-R1 and 4c-R2).

## Global Constraints

- **The PR boundary.** 4c changes:
  - the Schedule I, Schedule J, 106Sum and 103B schemas;
  - one intake migration, and no forms migration (no new form type);
  - steps 2 and 4.
  It adds no step, so `WIZARD_STEP_COUNT` stays 9. It doesn't touch 4c2's split: `ExpenseInfo`'s 24 amounts and the utilities and insurance lines stay as they are, and 4c2 rebases `ExpenseInfoStep.tsx`, `formText.ts` and the step 4 body on whatever lands first.
- **CMI and the means test are untouched** (S:274). No 4c key enters `IncomeInfo`, `income_step_gaps`, `read_inputs` or `apps/eligibility`. Line 11 is not one of the ten sources. 103B lines 1–3 keep reading line 10, which is counsel C-7's default (S:628).
- **Never a No the filer did not give** (§5.3). Every checkbox map is `{answer: state}`. An absent key prints no box. A stored answer the step hides (an employer under Not employed; a text or amount under No; the spouse block outside `married_together`) stays stored and prints nothing, because each binding carries a `conditional_on` predicate (4c-R5).
- **Encryption.** The record's two columns are encrypted from their first migration, and a ciphertext test reads the raw row. No new plaintext column. The pay-stub hint reads the existing `IngestedAggregate` row and adds no column. That row's `value` was already a plaintext `CharField(255)` (`backend/apps/documents/models.py:183`); this is pre-existing, and Plane gets a ticket for it.
- **Reopen and lock** (§5.6).
  - `schedule_i_answers` joins `_INTAKE_DATA` (`backend/apps/intake/serializers.py:1001-1012`), the serializer's `fields`, the viewset's `select_related` (`backend/apps/intake/views.py:153-165`) and the lock test's `WRITES` (`backend/apps/intake/tests/test_session_lock.py:554`, after the `petition_answers PATCH` row at `:595-599`).
  - A body with no answer left saves nothing and reopens nothing, as the `PetitionAnswers` empty-dict guard does (`serializers.py:1323-1327`).
- **Every widget name is the index's `full_name` verbatim** (`SFm` §2), spelling slips included: `Check emploment status Debtor 1`, `Employers Zip debtor 1`.
  - The two shared names are always tagged: `Time employed Debtor 1@1:T28` (yours) and `@1:T29` (the spouse's); `Assistance 8f@2:T49` (line 11). Line 8f's binding stays `@2:T36`.
  - The checkbox pairs carry one untagged binding each, with `choices`:
    - line 1: `{"employed": "/employed", "not_employed": "/unemployed"}`;
    - `Check increase`, `check24` and 103B `Check 8`: `{"no": "/no", "yes": "/yes"}`. Never copy 103B `Check 7`'s `/On`.
- **Money.** An amount stored as a decimal string never binds raw: it prints through a derived rule using `_fmt` (S:1088).
  - The serializer refuses an amount unless it is a plain decimal string ≥ 0 with at most two places that fits `DecimalField(12, 2)` (S:420).
  - The browser holds such an amount back: `IncomeInfoStep`'s `errors` map checks `line_11_amount` with `amountError(value, 12)` while line 11 is Yes, so autosave and Continue both wait and the box says why (Corrections, B47).
- **Copy.**
  - DigniFi's sentences go in `frontend/src/constants/copy.ts` with `// DRAFT: counsel C-42` directly above, scored at grade 9 or below by `src/test/reading-level.test.ts` and checked against `ADVICE` in a new `src/test/upl-schedule-i-copy.test.ts`.
  - The forms' words go in `formText.ts`, unscored, each pinned whole to its template page by a backend test.
  - Every word is in `OC`. A word not in it does not ship. `EmploymentBlock` reuses the existing address labels (`CLAIM_STREET_LABEL`, `AB_ADDRESS_LINE_2_LABEL`, `AB_CITY_LABEL`, `AB_STATE_LABEL`, `AB_ZIP_LABEL`, imported at `frontend/src/components/wizard/steps/claims/AddressFields.tsx:8-16`) and writes its own boxes, because `PartyAddressFields` is typed to `PetitionAnswers` and has no street 2 box.
- **Backend tests** run through the Mac helpers in `/Users/controlroom/.claude/jobs/bb720722/tmp/4b-sdd/`:
  - `GATE_WT=/Volumes/Containers/DigniFi/.claude/worktrees/forms-step4b-ii zsh …/pt.sh <paths relative to backend/> -q` ("`pt.sh`" below);
  - `py.sh manage.py check --settings=config.settings.test`;
  - `py.sh manage.py makemigrations --check --dry-run --settings=config.settings.test`.
  - Never the `handoff/2026-11-18-step4/sdd/*.sh` copies, which point at the Linux boot.
  - Name files and never run the whole suite from a task. Take counts from pytest's last line through a one-line `printf`.
  - `apps/intake/tests/test_session_lock.py` is Postgres-only and skips under `pt.sh`'s sqlite settings. A task that changes it reports the new case as skipped (Rule 13). The controller's gate Postgres run is the case's first real run, and it raises that run's count by one.
  - A tool that imports the backend runs through `py.sh` from `backend/`.
- **Lint.** `ruff==0.8.5`: `ruff check` on every Python file touched, and `ruff format --check` on files a task creates. Lines are 100 columns at most.
- **Frontend tests.**
  - `fe.sh npx vitest run --maxWorkers=2 <files>`;
  - `fe.sh npx tsc -p tsconfig.app.json --noEmit` (never `tsc -b`);
  - `fe.sh npx eslint <files>`;
  - `fe.sh ./node_modules/.bin/prettier --write <files>`, then `--check`.
  - Use `userEvent` with no fake timers (IntakeWizard's autosave tests keep that file's own timer pattern).
- **Git.**
  - Use `/opt/local/bin/git`: one plain command per call, from the worktree root, on `feat/forms-step4c`. Never `git -C`, no chained git, no push, merge or branch change.
  - One commit per task. Stage by explicit path, never `.claude/`, `.superpowers/`, `.serena/`, `DESIGN.md`, `assets/` or `.impeccable`.
  - No `Co-Authored-By`, `Claude-Session` or any agent trailer.
  - Never a bare `sed -i` (BSD leaves `-e` backups): edit with the Edit tool. If the pre-commit hook reformats a hand-written file, re-stage the same paths.
  - The tool-written `schedule_i.limits.json` is checked with `fe.sh ./node_modules/.bin/prettier --check ../<path>` before commit.
- **Tier 2 and the known defects.**
  - Each binding task adds its addendum rows (`data/forms/field_index/audit/step2_verification.json`) in the same commit as the bindings.
  - It deletes the rows its rebinding orphans, and re-pins `ASSERTED_CASES` (`backend/apps/forms/tests/test_oracle_tier2.py:37`, 1852 today) from the run, with the arithmetic in the comment.
  - `known_defects.json` stays `[]`, and `manage.py check` passes after every task.
- **Tests encode intent.**
  - Names say the outcome. Synthetic data only: "Demo" names and IRS-reserved `900-` SSNs.
  - A guard that passes before its code gets a see-it-fail mutation, named in the task.

## Rulings this plan makes (decided here, recorded for the owner)

- **4c-R1 Kinds** (D1, D2).
  - One table in `apps/intake/schedule_i.py`, `KIND_OF: dict[str, str]`, decides each gap's kind.
  - `line_11_answer`, `line_13_answer` and `schedule_j_line_24_answer` unanswered are `gate`s, in that order.
  - Every other gap is a `detail`:
    - `employment_status` unanswered;
    - `spouse_employment_status` unanswered (under `married_together` only);
    - Employed with a blank `employer_name` (and the spouse's twin);
    - line 11 Yes with no amount;
    - line 13 Yes with a blank text;
    - line 24 Yes with a blank text;
    - each text over its cap, only while its 4c-R5 predicate holds (a text kept under a No is never measured, the 4b-ii "only where its box prints" rule).
  - A blank occupation, address, tenure or line 11 text is no gap. The spec names none (S:276).
  - The marriage answer is read in one place, `married_together(session) -> bool` in `apps/intake/schedule_i.py`: `getattr(getattr(session, "income_info", None), "marital_status", None) == "married_together"`. The spouse gaps and the 4c-R5 predicates both import it.
- **4c-R2 Order.**
  - The step 2 gaps, in this order:
    1. your employment detail;
    2. the spouse's (under `married_together`);
    3. your employer detail;
    4. the spouse's employer detail;
    5. line 11's gate, then its amount detail;
    6. line 13's gate, then its text detail;
    7. too-long details in `KEYS` order.
  - Line 24's gate and detail follow the Expenses step's gaps, and the gate is listed even while the Expenses step was never saved, right after `EXPENSES_STEP_NEVER_SAVED`. The record is not the Expenses row, and both gaps link to the same step.
  - Splice points: after `completion.py:90` (the `income_info` gaps) and after the `if/elif` at `:101-104` (the `expense_info` gaps) (`SB` §2). Import lazily, as `petition_step_gaps` is imported at `:70`.
- **4c-R3 Line 11's cells** (D3). The table is the rule:

| line 11 | Schedule I `Amount 11` | `Assistance 8f@2:T49` | 103B `Check 8` | 103B "How much" | Line 12 adds |
|---|---|---|---|---|---|
| unanswered (a gate: no form is prepared) | blank | blank | neither | blank | 0 |
| No | `0.00` | blank | `/no` | blank | 0 |
| Yes, an amount above $0 | the amount | the text | `/yes` | the amount | the amount |
| Yes, `0` typed | `0.00` | the text | `/yes` | `0.00` | 0 |
| Yes, no amount | blank (a detail, S:211) | the text | `/yes` | blank | 0 |

  - Line 12 is blank exactly when line 10's total is blank and line 11 adds nothing. Otherwise it is line 10 (blank counts as 0) plus what line 11 adds, through `_fmt`.
  - 106Sum `4` and J `23a` print line 12, and J `23c` is line 12 less 22c, blank while line 12 is.
  - The `0.00` under No follows `_asked_amounts` (`derivations.py:126-130`) and Schedule I's own "write $0" instruction. S:180's "blank unless typed" governs only lines DigniFi does not ask. Cost if wrong: one box prints 0.00 instead of blank.
  - 103B "How much" copies line 11 as typed, `0.00` included, because 103B line 8 says "copy the total from line 11". Under No it is blank, because 103B ticks its own No box.
- **4c-R4 Continue and autosave** (D4).
  - On steps 2 and 4 the wizard computes `scheduleIGate(answers)` (step 2: lines 11 and 13) or `lineTwentyFourGate(answers)` (step 4) from its own `scheduleIAnswers` state.
  - The Continue button's `canGoNext` (`IntakeWizard.tsx:1321`) reads `canProceed && gate === null`, and `handleNext` (`:766-808`) returns early while the gate is open.
  - This departs from steps 1 and 7, which fold their gates into `onValidationChange` and so also stop autosave. The difference is on purpose: step 2 holds a page of typed income.
  - Autosave's `enabled` keeps reading `canProceed` (the amount checks) alone, so typed income still saves while a gate is open.
  - Steps 2 and 4 do not join `ALWAYS_AUTOSAVE_STEPS`.
  - Plane gets the parity gap: step 2's older Complete gates (marriage, household, assistance) and step 4's line 3 never hold Continue.
- **4c-R5 Predicates.**
  - They go in `_SCHEDULE_I_PREDICATES`, registered as `**_SCHEDULE_I_PREDICATES` in `PREDICATES` beside `**_PETITION_PREDICATES` (`derivations.py:1701-1741`).
  - Each takes the resolver's call shape, `pred(session, answer_cache=None)` (`fill_resolver.py:555-556`). A one-argument lambda raises `TypeError` at resolve.
  - Each reads the record through one helper, `_schedule_i(session, key)`, which uses `getattr(session, "schedule_i_answers", None)`. Example: `"schedule_i_employed": lambda s, answer_cache=None: _schedule_i(s, "employment_status") == "employed"`.
  - The predicates:
  - `schedule_i_status_answered`: `employment_status` answered;
  - `schedule_i_employed`: `employment_status == "employed"`;
  - `schedule_i_spouse_shown`: `married_together` and `spouse_employment_status` answered;
  - `schedule_i_spouse_employed`: `married_together` and `spouse_employment_status == "employed"`;
  - `schedule_i_line_11_yes`;
  - `schedule_i_line_13_yes`;
  - `schedule_j_line_24_yes`.
  - Your status prints whenever answered. Your occupation prints under `schedule_i_status_answered`, the twin of the spouse's rule, so an occupation the step hides behind a hidden line never prints. Your employer name, address and tenure print under `schedule_i_employed`. The spouse's status and occupation print under `schedule_i_spouse_shown`, and the spouse's employer, address and tenure under `schedule_i_spouse_employed`.
  - The line 11 text prints under `schedule_i_line_11_yes`. The line 13 and line 24 texts print under their own Yes.
- **4c-R6 What the step shows.** For each state, the step shows either the block or exactly one `HiddenLine` (`HIDDEN_ANSWERS` with Show and Delete):

| Question | State | Shows |
|---|---|---|
| line 1 (yours) | unanswered, nothing stored below | the two choices only |
| | unanswered, occupation or employer stored | the choices + one hidden line (Delete clears the eight keys below) |
| | Employed | occupation, employer name, address (street, street 2, city, state, ZIP), how long; the hint (W4) beside the name when given |
| | Not employed, no employer key stored | occupation only |
| | Not employed, an employer key stored | occupation + one hidden line (Delete clears `employer_*` and `time_employed`) |
| line 1 (spouse) | not `married_together` | nothing (kept hidden, as `spouse_income`, D5) |
| | `married_together` | the same table with `spouse_` keys; no hint |
| lines 11, 13, 24 | unanswered or Yes | the question; under Yes its boxes |
| | No, nothing stored | the question |
| | No, a text or amount stored | the question + one hidden line (Delete clears that line's boxes) |

  - Show fixes the block's visibility for the visit, so clearing the last box never unmounts it (FR-W4).
  - Under `married_together` the two blocks are named apart. Each block's legend carries the form's column words, "Debtor 1" or "Debtor 2 or non-filing spouse" (`OC` §2).
  - A hidden key the body still sends rides the body. Delete sets it to null in state, and the next save sends the null.
- **4c-R7 Bodies.**
  - Step 2's body adds `schedule_i_answers: pick(answers, STEP_2_SCHEDULE_I_KEYS)`. The nine `spouse_` keys are included only under `married_together`, like `spouse_income` (`IntakeWizard.tsx:617`).
  - Step 4's body adds `schedule_i_answers: pick(answers, STEP_4_SCHEDULE_I_KEYS)`, never inside `expense_info` (Remove's `{expense_info: {field: 0}}` stays the whole body).
  - Every key is `?? null`. The amount is held and sent as the typed string, never hydrated to a number.
  - `paystub_employer_name` and `answered_on` are never sent.
- **4c-R8 Caps.**
  - `build_schedule_i_limits.py` measures each text on its narrowest box (`SFm` §7): single-line boxes with `build_form_101a.py`'s `limits()` formula, the multi-line `Increase/Decrease 13` and `Other 24` with `build_form_101.py`'s venue rule (`floor(lines/2 × room / widest)`, lines from the box height at 6 pt).
  - Line counts use the fitter's own leading, `lines = floor((h - 2 × margin) / (MIN_SIZE × _leading(font)))` (`text_fit.py:70, :174`), so the tool's count matches what `check()` refuses.
  - The serializer refuses an unknown key, a wrong type, a text over 500 characters or a bad amount. An echoed `answered_on` is dropped, as `PETITION_READ_ONLY` drops it (`serializers.py:1226-1233`). A text over its cap is stored and is a too-long detail, by length alone. Its `{label}` is the tool's label for the key (`OC` W18).
  - Generate's `ValueTooLong` stays the backstop for a text within its cap that still doesn't fit its box (wide capitals).
- **4c-R9 Street 2 prints** on `Employers Street2 Debtor 1` and `Debtor 2` (D6). `Street3` stays unbound, and the record has no key for it.
- **4c-R10 The pay-stub hint** (D7).
  - `IntakeSessionSerializer` gains read-only `paystub_employer_name`: the session's `IngestedAggregate` value for `paystub.employer_name`, stripped, or `""`. It comes from a prefetch of `ingested_aggregates`.
  - The step shows W4 beside your own employer name box, under Employed, when the value isn't `""`. It never fills the box.
  - The engine's `ingested` source type, `fix_for`'s `/documents` branch and `PAGE_LINK_LABELS['/documents']` stay, as supported and unused (Rule 5). CLAUDE.md says so.
- **4c-R11 The plain read.**
  - The eleven identity call sites read `_debtor_text(session, attr) -> str`: `"" if value is None else str(value)` from `session.debtor_info`, with no `except`. A session without a `DebtorInfo` raises.
  - `_full_name` and `_has_ssn` keep their own guards. They are out of scope here, and Plane gets a ticket for them under Rule 13.
  - Fixtures that resolve Form 121, 122A-1 or 122A-2 on a bare session change as follows:
    - `test_form_122a2_schema.py:136-145`: `session` gains a `DebtorInfo`.
    - `test_form_122a1_schema.py:93-102`: `session` gains one, and `:176-183` updates that row instead of creating a second (one-to-one).
    - `test_schedule_i_schema.py:69-79`: `session` gains one, and `session_with_income` (`:84-97`) updates it.
    - `test_form_121_schema.py`: `test_without_debtor` (`:69-71`) is deleted, replaced by Task 3's raise test. `session` stays bare, because `session_with_ssn` (`:38`) and `:84` make their own.
- **4c-R12 `Gap.forms`.**
  - Line 1 gaps: `("schedule_i",)`.
  - Line 11's amount detail: `("schedule_i", "form_103b")` while `FilingFee.payment_choice == "waiver"`, else `("schedule_i",)` (the T10-R1 precedent).
  - Line 13: `("schedule_i",)`. Line 24: `("schedule_j",)`. A too-long detail names the form whose box refuses it.
  - A gate's `forms` is `()`.
- **4c-R13 Builder default.**
  - `answer_household(…, schedule_i=SCHEDULE_I_DEFAULTS)` calls `answer_schedule_i(session, **answers)`, with `SCHEDULE_I_DEFAULTS = {"employment_status": "not_employed", "line_11_answer": "no", "line_13_answer": "no", "schedule_j_line_24_answer": "no"}`.
  - It adds `spouse_employment_status: "not_employed"` when the session's marital answer is `married_together`.
  - `schedule_i=None` leaves the record alone. The default leaves zero gaps.
  - `answer_schedule_i` mirrors `answer_petition` (`builders.py:181-194`): it gets or builds the record through the session's relation (`getattr(session, "schedule_i_answers", None) or ScheduleIAnswers(session=session)`), merges, saves and returns it, so the test's session never reads a stale cache.
- **4c-R14 103B.** Line 8 prints from line 11 (4c-R3). 103B's `requires` and `/filing-fee` are unchanged. W16 removes only "line 8 and", and Plane gets the stale "lines 17 to 20" clause.

## Review Focus

Seven conditions the spec doesn't spell out, most likely first. Items 1–3 are where a CLEAN task review is likeliest to be wrong.

1. **Stored answers under a later No.**
   - The cases: an employer under Not employed, a line 11 text or amount under No, a line 13 or 24 text under No, the spouse block after the marital answer changes.
   - Each must print nothing on any form (4c-R5), raise no gap, still ride the body (4c-R7, spouse keys excepted), and sit behind one hidden line on the step (4c-R6).
   - Tests:
     - Task 3 `test_an_employer_kept_under_not_employed_prints_nothing`, `test_the_spouse_column_prints_only_for_married_filing_together`;
     - Task 4 `test_line_11_text_and_amount_kept_under_no_print_nothing_and_add_nothing`;
     - Task 6 `an employer kept under Not employed hides behind one line that offers Show and Delete`;
     - Task 2 `test_answers_kept_under_a_no_raise_no_gap`, `test_a_text_over_its_cap_kept_under_a_no_is_not_measured`.
2. **The means test can't see a 4c answer.**
   - With every 4c question unanswered, the means test outcome, CMI, 103B lines 1–3 and `household.family_size` are what they were.
   - Test: Task 2 `test_an_unanswered_schedule_i_leaves_the_means_test_and_household_reads_alone`.
3. **Line 12 under each line 11 state** (4c-R3), including line 10 blank, and its three copies.
   - Tests: Task 4 `test_line_12_follows_each_line_11_state` (parametrized over the table's five rows × line 10 blank/given), `test_106sum_4_and_schedule_j_23a_23c_copy_line_12`.
4. **A session with no `ScheduleIAnswers` row.**
   - Every session saved before 4c has none. `schedule_i_step_gaps` reads every key as unanswered, so it gives the three gates and the employment detail. Every binding prints blank, and nothing raises `RelatedObjectDoesNotExist`.
   - Tests: Task 2 `test_a_session_with_no_record_lists_every_gate`; Task 4 `test_a_session_with_no_record_prints_every_new_box_blank`.
5. **The plain read on a bare session.**
   - Form 121, 122A-1 (`13A`, rule `state`) and 122A-2 resolve on sessions built without a `DebtorInfo` in their schema tests (`SC` A.1). A `None` column prints `""`, never `"None"`.
   - Tests: Task 3 `test_an_identity_box_with_no_value_prints_blank_not_none`, and the 122A-1 and 122A-2 schema files run whole.
6. **The shared widget names.**
   - Line 11's text must land on T49 and never on 8f's T36. The spouse's tenure must land on T29, never on T28.
   - Tests: Task 3's tier 1 `test_every_tagged_schedule_i_twin_fills_its_one_widget`; Task 4 `test_line_11_text_prints_on_line_11_not_line_8f`.
7. **A stale browser tab.** A step 2 or step 4 PATCH with no `schedule_i_answers` key leaves the record exactly as stored.
   - Test: Task 1 `test_a_patch_without_the_key_leaves_the_record_alone`.

---

### Task 1: The record, its caps, the API and the pay-stub field

**Files:**
- Create: `backend/apps/intake/migrations/0045_schedule_i_answers.py`, `data/forms/field_index/tools/build_schedule_i_limits.py`, `data/forms/schemas/schedule_i.limits.json`, `backend/apps/intake/tests/test_schedule_i_answers.py`, `backend/apps/intake/tests/test_schedule_i_encryption.py`
- Modify: `backend/apps/intake/models.py` (after `PetitionAnswers`, `:829-1004`), `backend/apps/intake/serializers.py` (`_INTAKE_DATA` `:1001`, the `PetitionAnswersField` pattern `:1047-1105`, `fields`, create/update pops `:1273-1375`), `backend/apps/intake/views.py:153-165`, `backend/apps/forms/schema.py:776-806` (E007, beside `_petition_binding_error` `:790-804`), `backend/apps/forms/services/fill_resolver.py:597-603` (the docstring), `backend/apps/intake/tests/builders.py` (`answer_schedule_i` only), `backend/apps/intake/tests/test_session_lock.py:595-599`, `backend/apps/forms/tests/test_checks.py`

**Interfaces:**
- Produces:
  - `ScheduleIAnswers`, with:
    - `CHOICE_KEYS = {"employment_status": ("employed", "not_employed"), "spouse_employment_status": (…)}`;
    - `YES_NO_KEYS = ("line_11_answer", "line_13_answer", "schedule_j_line_24_answer")`;
    - `TEXT_KEYS`: occupation, `employer_name`, `employer_street`, `employer_street_2`, `employer_city`, `employer_state`, `employer_zip`, `time_employed`, their `spouse_` twins, `line_11_text`, `line_13_text`, `schedule_j_line_24_text`;
    - `AMOUNT_KEYS = ("line_11_amount",)`;
    - `KEYS` (the union, in S:420's order), `TEXT_CEILING = 500`;
    - `TEXT_LIMITS` and `TEXT_LABELS` read from `schedule_i.limits.json`;
    - `get_answers() -> dict` and `merge(sent: dict) -> None`, which raises `KeyError` naming an unknown key before any is set, pops on null, and stamps `answered_on` only on a change.
  - The session read's `schedule_i_answers` (the answers, plus `answered_on`, read-only) and `paystub_employer_name: str`.
  - `answer_schedule_i(session, **answers) -> ScheduleIAnswers` in `builders.py`; a `None` value removes a key.

- [ ] **Step 1: Write the failing tests** in `test_schedule_i_answers.py`:
  - `test_a_patch_sets_only_the_keys_sent`
  - `test_a_null_removes_a_key`
  - `test_an_unknown_key_is_refused_by_name_and_nothing_is_saved`
  - `test_a_text_over_500_characters_is_refused`
  - `test_an_amount_that_is_not_a_plain_decimal_at_or_above_zero_is_refused` (parametrized: `"-1"`, `"1e3"`, `"abc"`, `"10000000000.00"`, `12`)
  - `test_a_text_over_its_cap_is_stored` (B47)
  - `test_answered_on_takes_the_fill_date_only_when_an_answer_changes`
  - `test_a_body_with_no_answer_saves_nothing_and_reopens_nothing`
  - `test_a_write_reopens_a_completed_intake`
  - `test_a_patch_without_the_key_leaves_the_record_alone` (Review Focus 7)
  - `test_an_echoed_answered_on_is_ignored`
  - `test_the_session_read_carries_the_pay_stub_employer_name` (`IngestedAggregate.objects.create(session=session, ingest_key="paystub.employer_name", value=" Demo Pharmacy ")` → `"Demo Pharmacy"`)
  - `test_with_no_pay_stub_the_employer_name_reads_empty`
  - `test_the_pay_stub_name_is_read_only` (a PATCH carrying it changes nothing)
  - `test_the_caps_are_measured_on_schedule_i_and_j_boxes`: the file's `limits` equal the tool's output and include `employer_state` and `employer_zip`, with both spouse twins equal to the filer's. The values are the tool's; the `SFm` §7 estimates are 44/22/7/10/20/104 for single-line boxes.
  - The import guards, on a stand-in schemas directory: `test_a_missing_limits_file_fails_at_import`, `test_a_limits_file_with_no_limits_or_no_labels_is_improperly_configured`, `test_a_limits_key_the_record_does_not_ask_is_improperly_configured`.
  - In `test_schedule_i_encryption.py`: `test_the_answers_are_ciphertext_in_the_table` (the raw column holds no `"Demo Pharmacy"`).
  - In `test_session_lock.py`: a `WRITES` row `"schedule_i_answers PATCH": {"schedule_i_answers": {"line_13_answer": "no"}}` → 200.
  - In `test_checks.py`: `test_a_schedule_i_binding_naming_no_key_is_refused` (E007).
- [ ] **Step 2: Run them.** `pt.sh apps/intake/tests/test_schedule_i_answers.py apps/intake/tests/test_schedule_i_encryption.py apps/forms/tests/test_checks.py -q`. Expected: the new cases fail (`ImportError`/`AttributeError`/an ignored key). The `WRITES` row skips under sqlite; say so in the report.
- [ ] **Step 3: Write the tool.** `build_schedule_i_limits.py` copies `build_form_101a.py`'s helpers (4b-R5). It reads `form_b106i.pdf` and `form_b106j.pdf`, measures per 4c-R8, and writes `{"limits": {…}, "labels": {…}}`, where each label is the box's plain words. Run it through `py.sh` and commit its output.
- [ ] **Step 4: Implement.**
  - The model: `db_table = "schedule_i_answers"`, `answers = EncryptedTextField(default="{}")`, `answered_on = EncryptedCharField(max_length=10, null=True, blank=True)`.
  - Its import-time read of `schedule_i.limits.json`, with the three guards.
  - The migration.
  - The serializer field: `ScheduleIAnswersField`, `validate_schedule_i_answers` (drops an echoed `answered_on`), `_save_schedule_i_answers`, and read-only `answered_on` and `paystub_employer_name`.
  - `_INTAKE_DATA`, `select_related("schedule_i_answers")` and `prefetch_related("ingested_aggregates")`.
- [ ] **Step 5: Add the E007 check.** The check (`_schedule_i_binding_error`, beside `_petition_binding_error`) refuses a `schedule_i.` binding whose key is not in `ScheduleIAnswers.KEYS` or that binds a list. Rewrite `binding_fix`'s docstring.
- [ ] **Step 6: Run Step 2's command, `py.sh manage.py check`, `py.sh manage.py makemigrations --check --dry-run`, and `ruff`.** Expected: all pass.
- [ ] **Step 7: Commit** `intake: ScheduleIAnswers, its caps, its API and the pay stub's employer name as a read-only field`.

### Task 2: The gaps, the builder defaults and the personas' answers

**Files:**
- Create: `backend/apps/intake/schedule_i.py`, `backend/apps/intake/tests/test_schedule_i_gaps.py`
- Modify:
  - `backend/apps/intake/completion.py` (after `:90` and after `:101-104`);
  - `backend/apps/intake/tests/builders.py` (`answer_household` `:76-91`, `SCHEDULE_I_DEFAULTS`);
  - `backend/apps/intake/management/commands/seed_demo_data.py` (each persona dict beside `"petition"` at `:367, :534, :755, :981, :1112, :1413`; the create beside the `PetitionAnswers` write at `:1607`, before the means test at `:1666`);
  - `backend/apps/forms/tests/test_api_readback.py` (`:181-189`);
  - `backend/apps/intake/tests/test_completion_gaps.py` (`:158-164`);
  - `backend/apps/intake/tests/test_completion.py` (`:495-530`, the full gate pin);
  - `backend/apps/intake/tests/test_seed_demo_data.py`;
  - and any test the run shows building a "completed" session without `answer_household`.

**Interfaces:**
- Consumes: Task 1's record and `answer_schedule_i`.
- Produces:
  - `schedule_i_step_gaps(session) -> list[Gap]`: every gap of the record, each with its own step (`income_info`, or `expense_info` for line 24);
  - `married_together(session) -> bool`;
  - the module constants `GATE_LINE_11`, `GATE_LINE_13`, `GATE_J24`, `DETAIL_EMPLOYMENT`, `DETAIL_SPOUSE_EMPLOYMENT`, `DETAIL_EMPLOYER`, `DETAIL_SPOUSE_EMPLOYER`, `DETAIL_LINE_11_AMOUNT`, `DETAIL_LINE_13`, `DETAIL_J24`, `DETAIL_TOO_LONG` (template `{label}`, `{form}`), worded as `OC` W5–W15;
  - `KIND_OF`;
  - `SCHEDULE_I_DEFAULTS`.

- [ ] **Step 1: Write the failing tests** in `test_schedule_i_gaps.py`:
  - `test_a_session_with_no_record_lists_every_gate` (the three gates and the employment detail, in 4c-R2's order)
  - `test_the_gaps_come_in_one_fixed_order`
  - `test_each_gap_has_its_kind_from_the_one_table`
  - `test_the_spouse_gaps_show_only_for_married_filing_together`
  - `test_employed_with_no_employer_name_is_a_detail`
  - `test_not_employed_with_no_occupation_is_no_gap`
  - `test_line_11_yes_with_no_amount_names_form_103b_only_under_the_waiver` (4c-R12)
  - `test_a_text_over_its_cap_is_a_too_long_detail_naming_its_form`
  - `test_a_text_over_its_cap_kept_under_a_no_is_not_measured`
  - `test_line_24s_gate_shows_while_the_expenses_step_was_never_saved`
  - `test_answers_kept_under_a_no_raise_no_gap`
  - `test_complete_refuses_an_unanswered_line_11_and_lets_a_missing_employer_through`
  - `test_line_24s_gaps_sit_after_the_expenses_steps`
  - `test_an_unanswered_schedule_i_leaves_the_means_test_and_household_reads_alone` (Review Focus 2: outcome, `cmi`, `household.family_size`, 103B line 1 equal before and after deleting the record)
  - `test_the_builder_default_leaves_no_gap`, under `not_married` and `married_together`.
  - In `test_seed_demo_data.py`: `test_every_persona_has_its_schedule_i_answers` (the values in `OC` §4) and the existing no-gate-gap guard.
- [ ] **Step 2: Run them.** `pt.sh apps/intake/tests/test_schedule_i_gaps.py -q`. Expected: `ImportError`.
- [ ] **Step 3: Implement** the module (it reads the session by attribute and imports `ScheduleIAnswers` only for `KEYS` and the caps), the two splices by `g.step`, the builder default (4c-R13) and the seed (owner-approved `OC` §4 data; Andrés's employer blank per P1).
- [ ] **Step 4: Update `test_api_readback.py`** so each persona's Schedule I answers are PATCHed: the step 2 keys with step 2, the line 24 keys with step 4.
- [ ] **Step 5: Run the blast radius.** Run `pt.sh` over every file `SB` §1 lists (the `finish_intake`, `answer_household`, `answer_petition`, Complete and forms-view callers, `time_packet` included), plus `apps/intake/tests/test_completion_gaps.py`.
  - Any red test that builds a completed session by hand gets `answer_schedule_i(session, **SCHEDULE_I_DEFAULTS)`, or `answer_household`'s default.
  - The pin at `test_completion_gaps.py:158-160` (an untouched intake's details) becomes `[DETAIL_VENUE, DETAIL_EMPLOYMENT]`.
  - `test_completion.py:504-530` gains `{"step": "income_info", "message": GATE_LINE_11}` and `GATE_LINE_13` after `:520` (`ASSISTANCE_UNANSWERED`), and `{"step": "expense_info", "message": GATE_J24}` after `:521` (`EXPENSES_STEP`).
  - Record the count.
- [ ] **Step 6: Run `ruff` and `py.sh manage.py check`.**
- [ ] **Step 7: Commit** `intake: Schedule I's gaps in Complete's list, the builders' default and each persona's answers`.

### Task 3: Line 1 prints from the record, and the dead `DebtorInfo` reads go

**Files:**
- Modify: `data/forms/schemas/schedule_i.json`, `backend/apps/forms/services/derivations.py` (`_safe_debtor_attr` `:60-65`; the dead rules `:690-695`, `:1379-1384`; identity sites `:1058, :1093, :1210, :1265-1273`; `RULE_FIXES` `:1648-1656`; the predicate table), `data/forms/field_index/audit/step2_verification.json`, `backend/apps/forms/tests/test_oracle_tier2.py:37`, `backend/apps/forms/tests/test_oracle_tier1.py` (`:784-813`, generalized), `backend/apps/forms/tests/test_oracle_tier3.py` (each persona's line 1 boxes), `backend/apps/forms/tests/test_schedule_i_schema.py` (`:69-97` fixtures, `:230-243`), `backend/apps/forms/tests/test_derivations.py`, `backend/apps/forms/tests/test_rule_fixes.py:218`, `backend/apps/forms/tests/test_form_122a1_schema.py` (`:93-102`, `:176-183`), `backend/apps/forms/tests/test_form_122a2_schema.py:136-145`, `backend/apps/forms/tests/test_form_121_schema.py:69-71` (the fixture changes are listed in 4c-R11)

**Interfaces:**
- Consumes: Task 1's record, Task 2's seed.
- Produces:
  - the predicates of 4c-R5;
  - `_debtor_text(session, attr) -> str`;
  - bindings:
    - `Check emploment status Debtor 1` / `Debtor 2` ← `schedule_i.employment_status` / `spouse_employment_status` (choices per Global Constraints);
    - `Occupation Debtor 1` / `2`, `Employers Name`, `Street1`, `Street2`, `City`, `State`, `Zip` (D1/D2), `Time employed Debtor 1@1:T28` / `@1:T29` ← the `schedule_i.` keys, with the predicates of 4c-R5.

- [ ] **Step 1: Write the failing tests:**
  - in `test_schedule_i_schema.py`:
    - `test_line_1_prints_your_employment_from_the_record`
    - `test_not_employed_prints_the_unemployed_box_and_the_occupation`
    - `test_an_employer_kept_under_not_employed_prints_nothing`
    - `test_the_spouse_column_prints_only_for_married_filing_together`
    - `test_street_2_prints_and_street_3_stays_blank`
    - `test_an_occupation_with_no_status_prints_nothing` (4c-R5, `schedule_i_status_answered`)
    - `test_the_pay_stub_name_no_longer_prints_on_schedule_i` (an `IngestedAggregate` with a name and no record → `Employers Name Debtor 1` blank)
  - in `test_derivations.py`: `test_an_identity_box_with_no_value_prints_blank_not_none`, `test_an_identity_rule_on_a_session_without_debtor_info_raises`
  - in tier 1:
    - `test_every_schedule_i_binding_names_a_key_the_record_asks`
    - `test_every_tagged_schedule_i_twin_fills_its_one_widget`, over `Time employed Debtor 1` T28/T29 only (Task 4 adds T36/T49)
    - `test_every_schedule_i_choice_map_prints_exactly_the_stored_answer`, parametrized over every `schedule_i.` checkbox binding × {absent → neither state, each answer in its `choices` → that state alone}, so `employed`/`not_employed` here and `no`/`yes` for Task 4's boxes.
- [ ] **Step 2: Run them.** Expected: fail.
- [ ] **Step 3: Implement.**
  - Delete the six dead rules, their `DERIVATIONS` and `RULE_FIXES` entries, their schema bindings and the `ingested` binding.
  - Add the new bindings and the predicates.
  - Replace each `_safe_debtor_attr` call with `_debtor_text`, then delete `_safe_debtor_attr`.
  - Make the fixture changes listed in 4c-R11.
  - Narrow `test_schedule_i_schema.py:242` (`test_a_spouse_at_home_prints_0_00_on_every_asked_line_left_blank`) to the amount boxes (`b.startswith("Amount") and "Debtor 2" in b`), and assert separately that the builder default's spouse status prints `/unemployed`.
- [ ] **Step 4: Update tier 2.**
  - Add addendum rows for each new (box, key): producer `asked:schedule_i.<key>`, the bare `pdf_field`, evidence quoting the index label and citing S:600 and 4c-R5/R9.
  - Delete the rows the deletions orphan. Run `pt.sh apps/forms/tests/test_oracle_tier2.py -q`, re-pin `ASSERTED_CASES` from its count, and write the arithmetic.
- [ ] **Step 5: Update tier 3.** Each persona's Schedule I gains its line 1 values from `OC` §4, and blanks where a box doesn't print.
- [ ] **Step 6: Run** `pt.sh apps/forms/tests/test_schedule_i_schema.py apps/forms/tests/test_derivations.py apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier2.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_rule_fixes.py apps/forms/tests/test_form_101_schema.py apps/forms/tests/test_form_121_schema.py apps/forms/tests/test_form_122a1_schema.py apps/forms/tests/test_form_122a2_schema.py apps/forms/tests/test_printed_page.py apps/forms/tests/test_part_fixes.py apps/forms/tests/test_checks.py -q`, then `py.sh manage.py check` and `ruff`.
  - Expected: all pass, and `known_defects.json` is still `[]`.
  - See-it-fail: drop `conditional_on` from `Employers Name Debtor 1` and show the kept-under-Not-employed test fail.
- [ ] **Step 7: Commit** `forms: Schedule I line 1 prints from the filer's answers; the dead DebtorInfo rules and _safe_debtor_attr go`.

### Task 4: Lines 11, 12 and 13, Schedule J line 24 and Form 103B line 8

**Files:**
- Modify:
  - `derivations.py`:
    - new rules `schedule_i_line_11_amount`, `schedule_i_line_12` and `fee_waiver_line_8_amount`;
    - `_schedule_j_monthly_net_income` (`:866-875`) reads line 12;
    - the alias `schedule_j_total_income` (`:1441`) points at `_schedule_i_line_12`, so `23a`'s binding and tier 2 key don't change;
    - `_schedule_i_income_total`'s docstring loses "Line 11 is never asked";
    - `RULE_FIXES` entries `{"step": "income_info"}`.
  - `schedule_i.json` (`Assistance 8f@2:T49`, `Amount 11`, `Amount 12` → `schedule_i_line_12`, `Check increase`, `Increase/Decrease 13`), `schedule_j.json` (`check24`, `Other 24` only), `form_106sum.json` (`4`), `form_103b.json` (`Check 8`, `Yes How much do you regularly receive as contributions`);
  - `step2_verification.json` (the Amount 12 row `:2225` and the 106Sum `4` row `:2195` re-keyed);
  - `test_oracle_tier1.py` (the twin test gains T36/T49), the tier 2 and tier 3 tests, `test_schedule_i_schema.py`, `test_schedule_j_schema.py`, `test_form_103b_answers.py`, `test_derivations.py:161-164` (`SWITCHED_RULES` still holds with no record, because line 12 then equals line 10), `test_rule_fixes.py`.

**Interfaces:**
- Consumes: Task 3's predicates.
- Produces: `schedule_i_line_12` (4c-R3), bound by `Amount 12` and 106Sum `4`, and reached by J `23a` through its alias; J `23c` is derived from it.

- [ ] **Step 1: Write the failing tests:**
  - `test_line_12_follows_each_line_11_state` (4c-R3's five rows × line 10 blank/given)
  - `test_a_typed_0_under_yes_prints_0_00_on_schedule_i_and_103b`
  - `test_106sum_4_and_schedule_j_23a_23c_copy_line_12`
  - `test_line_10_stays_line_10`
  - `test_line_11_text_prints_on_line_11_not_line_8f`
  - `test_line_11_text_and_amount_kept_under_no_print_nothing_and_add_nothing`
  - `test_line_13_and_line_24_print_their_answer_and_their_text_only_under_yes`
  - `test_form_103b_line_8_reads_schedule_i_line_11` (both forms from one answer, S:789)
  - `test_a_session_with_no_record_prints_every_new_box_blank`
  - `test_a_line_11_amount_too_wide_for_103bs_box_is_refused_naming_the_box` (`ValueTooLong` with step `income_info`; `SFm` trap D)
  - Task 3's choice-map test now covers `Check increase` and `check24` too. 103B `Check 8` gets its own case for absent, `no` and `yes`, because it binds through a rule.
  - In tier 1, extend `test_every_tagged_schedule_i_twin_fills_its_one_widget` with `Assistance 8f` T36/T49.
- [ ] **Step 2: Run them.** Expected: fail.
- [ ] **Step 3: Implement** the rules, bindings and predicates.
- [ ] **Step 4: Update tier 2** as in Task 3 Step 4. **Tier 3:** each persona's new boxes per `OC` §4 (line 11 No → `Amount 11` `0.00`, `Check increase` `/no`, `check24` `/no`; waiver personas' 103B `Check 8` `/no`). Amount 12, 106Sum 4, 23a and 23c are unchanged for every persona (all line 11 No).
- [ ] **Step 5: Run** Task 3's file list plus `test_schedule_j_schema.py`, `test_form_103b_answers.py`, `test_form_103b_schema.py`, `test_form_106sum_schema.py` and `test_filing_fee_forms.py`, then `check` and `ruff`.
  - See-it-fail: bind T49 untagged and show `test_line_11_text_prints_on_line_11_not_line_8f` fail.
- [ ] **Step 6: Commit** `forms: Schedule I lines 11, 12 and 13, Schedule J line 24 and Form 103B line 8 print from the filer's answers`.

### Task 5: The browser's words, gaps, caps and type

**Files:**
- Create: `frontend/src/components/wizard/steps/scheduleI/scheduleIGaps.ts`, `frontend/src/constants/scheduleILimits.ts`, `frontend/src/test/upl-schedule-i-copy.test.ts`, `backend/apps/intake/tests/test_schedule_i_frontend_copy.py`
- Modify: `frontend/src/constants/copy.ts` (`OC` W1–W18, `FEE_OTHER_LINES_NOTE` `:1044-1045`), `frontend/src/constants/formText.ts` (`OC` §2, the column words "Debtor 1" and "Debtor 2 or non-filing spouse" and the line 11 box label "Specify:" included), `frontend/src/types/api.ts` (`ScheduleIAnswers`, `IntakeSession.schedule_i_answers?`, `paystub_employer_name?`), `frontend/src/components/forms/GapsNotice.tsx:49-52` (W15's template joins the too-long patterns), `frontend/src/pages/DocumentUploadPage.tsx:19` (W17), `frontend/src/pages/__tests__/DocumentUploadPage.test.tsx:112-123`, `frontend/src/pages/__tests__/FilingFeePage.test.tsx:231`, `frontend/src/components/forms/__tests__/GapsNotice.test.tsx`

**Interfaces:**
- Produces:
  - In one file, `scheduleIGaps.ts`, two functions, each covering one step (S:210):
    - `scheduleIGate(answers: ScheduleIAnswers): string | null`, the first unanswered of lines 11 and 13, in the server's words;
    - `lineTwentyFourGate(answers): string | null`;
  - `SCHEDULE_I_TEXT_LIMITS: Record<ScheduleITextKey, number>`;
  - `STEP_2_SCHEDULE_I_KEYS`, `STEP_4_SCHEDULE_I_KEYS` (exported from `scheduleIGaps.ts`; `IntakeWizard.tsx` imports them).

- [ ] **Step 1: Write the failing tests** in `test_schedule_i_frontend_copy.py`:
  - `test_the_gate_and_detail_sentences_are_the_servers`
  - `test_the_limits_are_the_servers`
  - `test_the_too_long_labels_are_the_approved_words` (`schedule_i.limits.json`'s `labels` equal `OC` W18)
  - `test_the_step_keys_split_the_record_by_step` (step 2 ∪ step 4 = `KEYS`; `schedule_j_*` only in step 4, matching `record_step`)
  - `test_the_schedule_i_and_j_words_are_the_forms_own` (each `formText.ts` quote found whole on its page)
  - In vitest: `GapsNotice` `a too-long Schedule I answer is not counted as a blank one`; `scheduleIGate` and `lineTwentyFourGate` cases; the UPL list over the `SCHEDULE_I_` and `PAYSTUB_` prefixes.
- [ ] **Step 2: Run them.** Expected: fail.
- [ ] **Step 3: Implement.** Every DigniFi sentence gets `// DRAFT: counsel C-42`.
- [ ] **Step 4: Run** the backend test, `fe.sh npx vitest run --maxWorkers=2` on the touched test files plus `src/test/reading-level.test.ts`, and tsc, eslint, prettier.
- [ ] **Step 5: Commit** `frontend: Schedule I's words, gaps, caps and type`.

### Task 6: Step 2 asks lines 1, 11 and 13

**Files:**
- Create: `frontend/src/components/wizard/steps/scheduleI/EmploymentBlock.tsx`, `frontend/src/components/wizard/steps/scheduleI/LineQuestion.tsx` (one yes/no-then-details line with its hidden line), `frontend/src/components/wizard/steps/scheduleI/__tests__/EmploymentBlock.test.tsx`, `…/__tests__/LineQuestion.test.tsx`
- Modify: `frontend/src/components/wizard/steps/IncomeInfoStep.tsx` (after the ten sources; spouse twin inside `livingTogether` `:756-775`), `frontend/src/pages/IntakeWizard.tsx` (state beside `:353`, hydrate beside `:465`, body `:600-627`, memo deps `:711-733`, props `:1110-1131`, `canGoNext` `:1321` and `handleNext`), `frontend/src/components/wizard/steps/petition/PetitionQuestions.tsx` (export `boxesUnder`'s logic as a helper only if Step 3 reuses it; otherwise leave it), the two test files

**Interfaces:**
- Consumes: Task 5's gates, limits and key lists; `YesNoThenDetails` (`components/wizard/YesNoThenDetails.tsx`); `HiddenLine` (exported from `PetitionQuestions.tsx:211-231`).
- Produces:
  - `EmploymentBlock({answers, onChange, spouse, payStubName?})`. Its control names are the record keys (`employment_status`, `occupation`, `employer_name`, `employer_street`, `employer_street_2`, `employer_city`, `employer_state`, `employer_zip`, `time_employed`, `spouse_…`). The state is a select of `US_STATES_AND_TERRITORIES`; the ZIP has the 5/9 mask.
  - `LineQuestion({question, note?, name, answers, onChange, boxes})`.

- [ ] **Step 1: Write the failing tests** (`userEvent`):
  - `EmploymentBlock`:
    - `Employed shows the occupation, employer, address and how long`
    - `Not employed shows the occupation only`
    - `an employer kept under Not employed hides behind one line that offers Show and Delete`
    - `Delete clears the employer boxes and how long`
  - `the spouse's block is named apart from yours`
  - `a line 11 amount the server would refuse holds autosave and Continue and shows why`
    - `Show keeps the block open while the last box is cleared`
    - `the pay stub hint shows beside your employer box only when a name was read`
    - `the hint never fills the box`
    - `the spouse block has no hint`
    - `each box stops at its cap`
  - `LineQuestion`: `a text kept under No hides behind one line`, `Yes shows the boxes`.
  - `IntakeWizard.test.tsx`:
    - `step 2's body carries only step 2's Schedule I keys`
    - `the spouse keys are sent only for married filing together`
    - `showing step 2 again sends nothing` (extend `:2978`)
    - `Continue waits for lines 11 and 13 while autosave still saves typed income`
    - `a loaded record hydrates the step`
  - The existing step-2 describes (`SF` §6) get lines 11 and 13 answered in their session fixtures.
  - The exact body pin at `IntakeWizard.test.tsx:2684-2692` ("income save") expects `schedule_i_answers` with the step 2 keys (the fixture's answers, the rest `null`).
- [ ] **Step 2: Run them.** Expected: fail.
- [ ] **Step 3: Implement** per 4c-R4, R6 and R7, and the Money constraint (`line_11_amount` in `IncomeInfoStep`'s `errors` via `amountError(value, 12)` while line 11 is Yes). Show `OC` W1, W2, W3 and W4 and the form's words, with the reused address labels. The step's status region (`role="status"`, stays mounted) shows `scheduleIGate`'s sentence once a line 11 or 13 control is touched (the `ContractsStep` pattern).
- [ ] **Step 4: Run** the touched vitest files (`IntakeWizard.test.tsx`, `IncomeInfoStep.test.tsx`, the two new files, `src/test/accessibility.test.tsx`), then tsc, eslint, prettier.
  - See-it-fail: remove the `gate === null` term and show the Continue test fail.
- [ ] **Step 5: Commit** `wizard: the Income step asks Schedule I lines 1, 11 and 13`.

### Task 7: Step 4 asks Schedule J line 24

**Files:**
- Modify: `frontend/src/components/wizard/steps/ExpenseInfoStep.tsx` (after the total block, `:331-340`), `IntakeWizard.tsx` (body `:643-654`, props `:1148-1155`, `canGoNext`, `handleNext`), `frontend/src/components/wizard/steps/__tests__/ExpenseInfoStep.test.tsx`, `IntakeWizard.test.tsx`

- [ ] **Step 1: Write the failing tests:**
  - `line 24 asks in Schedule J's words, with its example`
  - `the step says why Continue waits for line 24` (a `role="status"` region, mounted throughout, shows `lineTwentyFourGate`'s sentence once line 24 is touched)
  - `a text kept under No hides behind one line`
  - `step 4's body carries only the line 24 keys, never inside expense_info`
  - `Remove still sends only the field it clears`
  - `Continue waits for line 24 while autosave still saves typed amounts`
  - `showing step 4 again sends nothing`
  - Existing fixtures: the "cleared expense" (`serveExpensesSession`, `:3711`) and "line 4 question" (`:3865`) fixtures get `schedule_i_answers: {schedule_j_line_24_answer: 'no'}`. `:3748` and `:3981` expect `['expense_info', 'schedule_i_answers']`, and `:3982`'s `expense_info` key-order pin stays as it is.
- [ ] **Step 2: Run them.** Expected: fail.
- [ ] **Step 3: Implement** with `LineQuestion` and the status region (the step 2 pattern).
- [ ] **Step 4: Run** the files, then tsc, eslint, prettier.
- [ ] **Step 5: Commit** `wizard: the Expenses step asks Schedule J line 24`.

### Task 8: The journeys and the personas' briefs

**Files:**
- Modify: `frontend/e2e/fixtures/personas.ts` (`PersonaIncome` `:58-77` gains `schedule_i`; `PersonaData` gains `schedule_j_line_24`; the six persona objects per `OC` §4), `frontend/e2e/pages/wizard.page.ts` (`fillIncomeInfo` `:159-237` calls a new `fillEmployment`, then lines 11 and 13; `fillExpenses` `:304-319` answers line 24, and its `Pick<PersonaData, …>` argument type widens with `'schedule_j_line_24'`; `fillPartyAddress`'s prefix type widens from `'business_'` to `'business_' | 'employer_' | 'spouse_employer_'`), the six `docs/testing/persona-briefs/*.md` (Maria's real company name replaced by the fictional one, per `OC` §4)

- [ ] **Step 1: Make the changes.** No spec file changes, since all nine call `fillIncomeInfo(X.income)` and `fillExpenses(X)`.
- [ ] **Step 2: Run every journey.** `zsh /Users/controlroom/.claude/jobs/bb720722/tmp/4b-sdd/e2e-one.sh all t8`. Expected: 9 pass, or 8 with Priya's DIG-523 42 px check as the only failure, as on develop.
- [ ] **Step 3: Commit** `e2e: every journey answers Schedule I lines 1, 11 and 13 and Schedule J line 24`.

### Task 9: CLAUDE.md and the READMEs

**Files:**
- Modify: `CLAUDE.md`, and the persona-briefs README only if its table names employment.

- [ ] **Step 1: Rewrite the gotchas** `SC` A.6 lists:
  - "Income is stored by source" (line 12, line 11 not a source);
  - "Document upload sits mid-wizard" (the stub's name is a hint; the `ingested` path is supported and unused);
  - "Forms need a completed intake" (the reopen list, Complete's order with the Schedule I gaps, `answer_household`'s `schedule_i` default);
  - "Saves lock the session" (`WRITES`);
  - "Autosave sends only real edits" (the step 2 and step 4 bodies);
  - "Schemas are checked at startup" (the `schedule_i.` namespace and its E007 key check);
  - "Blank, not 0.00" (line 11's cells, line 12, 103B line 8, never a No);
  - "Seed order" (personas seeded before 4c lack `ScheduleIAnswers` and meet line 11's gate: `--reset`);
  - a new gotcha, "Schedule I's answers", on the "Form 101's answers" pattern;
  - the File Map (`apps/intake/schedule_i.py`, `build_schedule_i_limits.py`, `scheduleI/`).
- [ ] **Step 2: Check.** `pt.sh apps/intake/tests/test_claude_md_asset_order.py -q` passes, and prettier `--check` on `CLAUDE.md`.
- [ ] **Step 3: Commit** `docs: CLAUDE.md for Schedule I's answers`.

## Corrections to the spec (the spec stays unedited)

- S:207 and B45 call a choice among states a detail, while S:276 calls 2a a gate. This plan takes detail (D1, 4c-R1).
- S:207 lists Schedule J line 24 as a gate, and §6.4 is silent. This plan takes gate (D1).
- S:274: the identity rules feed Forms 101, 121 and 122A-1 (`13A`), not "106Dec and every schedule header", which read `full_name`. `_needs_ssn` doesn't guard 122A-1.
- S:274 and S:600 count five or six dead rules. Six exist, and five are schema-bound (`schedule_i_employer_debtor1` is unbound).
- S:436: the next intake migration is `0045`.
- S:616: `ASSERTED_CASES` is 1852, not 1740.
- S:269 and S:604 quote the form's sentences short ("…homemaker, if it applies."; "…with information about additional employers."). `formText.ts` takes the page's words.
- S:180 vs `_asked_amounts` on `Amount 11`: 4c-R3.
- S:420 names `employer_street_2` while S:269 binds Street1 only. Street 2 prints (4c-R9).
- S:213 and S:782 (B47) store an over-wide amount and flag it. This plan refuses a bad line 11 amount at the serializer, per S:420's bound, because the browser holds it back first (the Money constraint). A stored amount can therefore never be the wrong shape.
- S:271 asks line 11 as "Does anyone else regularly contribute to the expenses on your Schedule J?". `OC` W1 rewords it to score at grade 9 or below (10.7 as written). The owner's approval of `OC` makes it binding.
- S:760 names Sarah as the one persona with a standing detail. If the owner keeps `OC` P1, Andrés also carries one (employer blank).
- B54 (S:932) pins a revision string for the forms 4b introduced. The Schedule I and J quotes are pinned to their page text instead, and `FORM_REVISIONS` gains no entry.
- S:209 asks for one gap table per record, and this plan has one function. S:210's "each step's mirror covers its own step" is met by two functions in one `scheduleIGaps.ts`.

## Self-review

- **Spec coverage.** Each item maps to a task:
  - §7.2 → T1;
  - §6.2's gaps → T2;
  - S:600's line 1 → T3;
  - S:601–603 and §13.1's line 8 → T4;
  - §6.2's questions → T6;
  - S:280 → T7;
  - §17 → T2/T8;
  - §18's tier 1 namespace, twin and never-a-No tests → T3;
  - store-then-flag → T1;
  - reopen and encryption → T1;
  - one answer on two forms → T4;
  - copy scoring → T5;
  - the gotchas → T9.
- **Type consistency.**
  - `schedule_i_step_gaps`, `married_together` and `SCHEDULE_I_DEFAULTS` are T2's; `answer_schedule_i` is T1's.
  - The predicates and `_debtor_text` are T3's. `schedule_i_line_12` is T4's.
  - `scheduleIGate`, `lineTwentyFourGate`, `STEP_2_SCHEDULE_I_KEYS`, `STEP_4_SCHEDULE_I_KEYS` and `SCHEDULE_I_TEXT_LIMITS` are T5's, consumed by T6 and T7.
- **Ordering.**
  - The record and its migration land before any write (T1).
  - The gates land with every builder, seed and readback change that answers them (T2).
  - No binding is removed before its replacement lands in the same commit (T3).
  - The tier 3 expectations for each box land with its binding (T3, T4).

<!-- prettier-ignore-end -->
