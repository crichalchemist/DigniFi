# Forms step 4e, "Your plans" (Form 108, Statement of Intention, and wizard step 9): Implementation Plan

<!-- prettier-ignore-start -->

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new wizard step 9, "Your plans for what you owe on" (`plans`, sidebar "Your Plans"), asks Form 108's questions in the form's words. It saves them to a new encrypted record, `IntentionAnswers`, and Form 108 joins the packet as the 20th form type.

- **Part 1:** for each confirmed secured debt, the form's four choices plus an app-only "I haven't decided yet." Under "Retain the property and [explain]:" the filer types their own words.
- **Part 2:** for each unexpired personal-property lease, "Will the lease be assumed?" with No, Yes and "I haven't decided yet."
- **The exempt box** is never asked. It prints from the exemptions page's own answers (R-EXEMPT).
- **Nothing is pre-selected**, nothing is a gate, and every open choice prints blank and is listed as a `detail`.
- **The definitions.** Each choice has a collapsed panel holding its statute's provision whole (E2), closed by a neutral pointer to an attorney and the court's help desk (E1). No consequence statute is shown (E3), and the form's own deadline sentence is shown as the form's words (E6).
- **Long names are stored and flagged (E4, R-EXPLAIN).** The creditor's name and the collateral on Amounts Owed, the lessor's name and the leased property on Contracts & Leases, and the "[explain]" words are saved as typed. Each box shows a too-long note, Review and the dashboard list a `detail` naming the form, and Generate refuses only while a box truly can't take the text.
- **The step shift.** Review moves from 9 to 10 (the first `current_step` shift of step 4). The four personas with a Form 108 make the choices the owner set (E5), and no persona surrenders.

**Architecture:**

- **The record (R-SHAPE).** `IntentionAnswers` (intake `0048`) is one encrypted JSON object:
  - `{"secured": {"<debt id>": {"intention", "explain"}}, "leases": {"<contract id>": {"assumed"}}}`, plus a server-stamped `answered_on`;
  - a session PATCH's `intention_answers` replaces each top key it sends, then prunes every stored id that isn't a confirmed secured debt or an in-scope lease of the session (R-PRUNE);
  - it is intake data: it locks the session (the PATCH's existing lock) and reopens a completed intake.
- **The reader.** `claim_rows._read` joins the record by id inside the one claims read:
  - each `secured` row gains `intention`, `explain` and `exempt`;
  - a new `leases` list (contracts with `contract_type == "lease"` and `lease_kind` in `vehicle`, `other_personal_property`, `other` or null; R-LEASE-GATE keeps null for API-stored rows) carries `assumed`;
  - so Form 108 prints in Schedule D's and G's order, and a deleted or added debt never moves a choice onto another creditor.
- **The prints.** New `CLAIM_CELLS` entries print the record:
  - `claims.secured[].intention | exempt | explain | explain_1 | explain_2`;
  - `claims.leases[].name | purpose | assumed`;
  - `undecided`, an absent answer, and explain under any other choice all print `""`;
  - the Explain1/Explain2 split lives in one function, `split_explain` (4e-R5);
  - the `intentions.` namespace 4a reserved is removed (4e-R1).
- **The exempt state.** `exempt_states(session)` in `apps/intake/exemptions.py` (pure) is the one rule. It feeds both the cell and a read-only session field, `intention_exempt`, from which the step shows its information line (R-EXEMPT, 4e-R6).
- **Form 108.**
  - `build_form_108_index.py` and `build_form_108.py` write the index, the schema, 47 addendum rows and `form_108.limits.json` (the measured caps);
  - two `sheet` groups take rows past 4 and 7;
  - the registry entry goes after `form_107`, with `applies` reading `claim_rows` and `requires` `_nothing`;
  - the `FORM_TYPE_CHOICES` migration is forms `0012`.
- **The gaps.** `apps/intake/intentions.py` returns two lists of `detail` `Gap`s, never through `claim_step_gaps`, whose gaps are all gates:
  - `intention_step_gaps(session)` (step `plans`): an open choice, `undecided`, `retain_explain` with no words;
  - `claim_text_gaps(session)` (steps `debts`, `contracts` and `plans`): the E4 and R-EXPLAIN too-long details, measured through `check()` by `apps/forms/services/intention_fit.py`, or over a cap from `form_108.limits.json`;
  - `completion_gaps` splices each where its step sits.
- **The step.** `PlansStep.tsx` is a controlled step (`answers`, `onAnswersChange`):
  - the wizard holds `intentionAnswers` and builds the step 9 body from in-scope rows only, keyed by server id, the same way from loaded and edited data;
  - `WIZARD_STEPS`, `WIZARD_STEP_COUNT`, the intake `0049` shift and the journeys' `walkPlans` land in one task;
  - `DebtsStep` and `ContractsStep` gain box notes for the E4 caps, outside their Continue gaps (DIG-542).

**Tech Stack:** No new dependency.
- Backend: Django 5.0 + DRF and pytest-django (sqlite, plus the throwaway Postgres for `postgres`-marked cases).
- PDFs: pypdf 6.13 and PyMuPDF. PDF-only scripts (the index tool) run with `/Users/controlroom/.claude/jobs/bb720722/tmp/venv-mac/bin/python -I`, never `backend/.venv`. Schema tools that measure with `text_fit` run through `py.sh`, as `build_form_101a.py` does.
- Frontend: React 19 + Vite + TypeScript, vitest + MSW + vitest-axe, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-18-forms-step4-design.md` (cited `S:line`). This plan builds:
- §19 row 5 (S:811);
- §6.9 (S:322-334), §7.3 (S:422-424), §10.1 (S:527-534) and §10.3 (S:548-550);
- §6.0's per-step mechanics (S:225-238);
- §18's 4e tests (S:766-793);
- B15, B22, B26, B27, B28, B29, B38, B43, B45, B47, B50 and counsel C-37 (S:861), touching C-21.

Inputs, all read 2026-11-24 at `feat/forms-step4e` = develop `6710e2b` (4a–4d merged; `git diff 7596370 6710e2b -- backend frontend` is empty, so the surveys' cites hold):
- `.superpowers/plan-4e/survey-spec.md` (`SS`), `survey-forms.md` (`SF`), `survey-wizard.md` (`SW`), `survey-law.md` (`SL`), `survey-critic.md` (`SC`);
- `owner-decisions.md` (`OD`: E1–E8, the controller's R-SHAPE, R-LEASE-GATE, R-EXEMPT, R-PRUNE, R-EXPLAIN, and the plan-review rulings R-BLANK-EXPLAIN, R-521-LEAD, R-FORM-WORDS, R-REVIEW-ONCE, R-SAVE-ORDER). These are binding over the spec;
- `owner-copy.md` (`OC`): the approved words (E7, with E8's five strings), and the "Form words (formText.ts)" section, which holds the form's and the statutes' own words (approved in kind by E2 and E6, R-FORM-WORDS), not DigniFi sentences.

The spec's `path:line` cites date from 471f4ec and are stale (`SS` §10). Every cite below was re-read at `6710e2b`, and a task that lands earlier moves the lines after it.

**Owner words.**
- Every DigniFi sentence the tasks ship is in `OC`'s approved table, as E8 updated it. E8 approved the last two open strings, `WHAT_DOES_EXPLAIN_MEAN` and `CLAIM_TEXT_LABELS.explain`, so no task waits on the owner, and the tasks run in order, 1 to 9.
- The explanation's label lands with the other four (Task 4 writes it into `form_108.limits.json`, Task 5's `CLAIM_TEXT_KEYS` holds `explain` from the start), so its too-long detail is built and tested in Task 5 beside the other texts', not split across tasks.
- An answer the owner changes is a one-place edit: a constant and its pinned mirror.

**The gate reruns after the final-review fix wave.** Task 9 runs it once before the final review, and again, unchanged, after the fix wave lands. The PR opens only on the second green run.

## Global Constraints

These are verbatim. Each is expanded in the bullets after it.

- vitest runs with --maxWorkers=2
- never tsc -b
- ruff==0.8.5
- backend tests with --ds=config.settings.test
- each task's commit stages by explicit path, never .serena/, DESIGN.md, assets/, .impeccable, .claude/, .superpowers/
- no Co-Authored-By or agent trailer in commits
- copy is grade <= 9 and information, never advice
- every new sentence marked // DRAFT: counsel C-37
- every printed box blank, never 0.00 or a No the filer didn't give
- every new filer column encrypted with a ciphertext test
- every new placement with its step2_verification.json addendum row
- known_defects.json stays []
- DIG-523 (Priya's 42px target, macOS only) is a known local failure

The constraints in full:

- **The PR boundary.** 4e changes:
  - one new intake model, `IntentionAnswers`, with two intake migrations: `0048_intention_answers` (the model) and `0049_shift_current_step_for_plans` (the step shift);
  - one forms migration, `0012_form_108` (the `FORM_TYPE_CHOICES` `AlterField`);
  - one new schema, `form_108.json`, and its 47 addendum rows; no other schema changes;
  - `claim_rows`, `CLAIM_CELLS`, `binding_fix`, `_LIST_BINDING` and the removal of `intentions.`;
  - the wizard (step 9 new, Review 9 → 10), Amounts Owed's and Contracts & Leases' box notes, Review's test (`ReviewStep.tsx` is not edited, R-REVIEW-ONCE) and the dashboard's pending-card path.
  - It changes nothing in `apps/eligibility`: C-21's default stands (S:856), so a surrender intention moves no 122A-2 line.
- **The owner's goal.** No choice reads as steered:
  - nothing is pre-selected;
  - the choices come in the form's order with "I haven't decided yet." last;
  - every definition panel is one collapsed `WhatDoesThisMean`, with equal prominence;
  - no persona surrenders, and no persona's choice is the product's normal path (E5, B38).
- **Commands.**
  - **Backend tests with `--ds=config.settings.test`:**
    - `zsh /Users/controlroom/.claude/jobs/bb720722/tmp/4b-sdd/pt.sh <paths relative to backend/> --ds=config.settings.test -q` ("`pt.sh`" below). It passes no `-m`, so `slow` cases run;
    - `ppt.sh` for `postgres`-marked cases;
    - `py.sh manage.py check --settings=config.settings.test`;
    - `py.sh manage.py makemigrations --check --dry-run --settings=config.settings.test` (no CI step runs it, `SC` §0.6).
    Name files, and never run the whole suite from a task (Task 9's gate is the one exception). Take counts from pytest's last line through a one-line `printf`.
  - **Frontend:**
    - `zsh …/fe.sh npx vitest run --maxWorkers=2 <files>`: vitest runs with --maxWorkers=2;
    - `zsh …/fe.sh npx tsc -p tsconfig.app.json --noEmit`: never tsc -b;
    - `fe.sh npx eslint <files>`;
    - `fe.sh ./node_modules/.bin/prettier --write <files>`, then `--check`;
    - `userEvent` with no fake timers.
  - **Lint:** ruff==0.8.5. CI runs `ruff check` only. Run `ruff format --check` only on files a task creates (the "63 files would be reformatted" is pre-existing). Lines are 100 columns at most.
  - **E2E:** `zsh /Users/controlroom/.claude/jobs/bb720722/tmp/4b-sdd/e2e-one.sh <spec|all> <label>`. Run E2E only in Tasks 4, 7 and 9. No task adds a gate, so no red window is declared: Task 4 moves the counts with the registry (Form 108's `requires` is `_nothing`), and Task 7 adds the step with every journey's `walkPlans`.
- **Git.**
  - Use `/opt/local/bin/git`: one plain command per call, from the worktree root, on `feat/forms-step4e`. No push, merge or branch change.
  - One commit per task. Each task's commit stages by explicit path, never `.serena/`, `DESIGN.md`, `assets/`, `.impeccable`, `.claude/` or `.superpowers/`.
  - No `Co-Authored-By` or agent trailer in commits.
  - Never a bare `sed -i`.
  - Pre-commit runs `black`, `ruff`, `prettier`, `eslint --max-warnings=0` and `check-json`. If it reformats a file, re-stage the same paths and commit again.
- **`step2_verification.json` is byte-compared.** Six tests compare the whole file with what a generator writes (`tool.merged_text`):
  - `test_claims_generator.py`, `test_form_101_schema.py`, `test_form_101a_schema.py`, `test_form_122a2_generator.py`, `test_schedule_c_generator.py` and `test_form_122a1_supp_generator.py`;
  - after Task 4, the new `test_form_108_generator.py`.
  Every task that touches the file runs all seven.
- **Copy.**
  - Copy is grade <= 9 (`flesch_kincaid_grade`, `reading-level.test.ts`) and information, never advice (`ADVICE`, checked by a new `upl-plans-copy.test.ts`).
  - Every new sentence is marked `// DRAFT: counsel C-37` in `copy.ts`, and `# DRAFT: counsel C-37` in Python.
  - The form's and the statutes' words go in `formText.ts`, unscored, each pinned to its source (the template page, or the uscode.house.gov URL in `OC`'s "Form words" section).
  - A DigniFi sentence not in `OC`'s approved table (E7, as E8 updated it) does not ship. The form's and the statutes' words follow `OC`'s "Form words (formText.ts)" section, which holds the form's and the statutes' own words, approved in kind by E2 and E6 and pinned to their sources, not DigniFi sentences (R-FORM-WORDS).
- **Blank, not 0.00.** Every printed box is blank, never 0.00 or a No the filer didn't give:
  - an absent or `undecided` intention ticks no `check1` box, and an absent or `undecided` `assumed` ticks no `check2x` box;
  - the exempt box ticks No only under `no_claims` (R-EXEMPT), never from absence;
  - Explain1 and Explain2 print only under `retain_explain` with words, and a `retain_explain` row whose words are blank after trimming ticks no `check1` box (R-BLANK-EXPLAIN, S:531);
  - signatures and dates stay blank (wet ink, `test_signing_lines.py`).
- **Encryption.** `IntentionAnswers.answers` and `answered_on` are encrypted from `0048`, with a ciphertext test that reads the raw row (`gAAAAA…`, no plaintext id or word).
- **Tier 2 and the known defects.**
  - Form 108's 47 bindings land with their 47 addendum rows in the same commit (Task 4).
  - `ASSERTED_CASES` (`backend/apps/forms/tests/test_oracle_tier2.py:37`, 1888 today) is re-pinned from the run to **1935**, with the arithmetic in the comment.
  - `known_defects.json` stays `[]`.
  - `manage.py check` passes after every task.
- **The UPL guard.** Every Form 108 `claims.` binding is `source: "asked"` with `legal_review: false` (`SC` §0.5: `fill_resolver.py:681-687` blanks a `legal_review` derived field outside `ANSWER_BOX_RULES`). 4e adds no `answer:` binding (`SC` §2, rule 2; 4i deletes the namespace).
- **Known local failure.** DIG-523 (Priya's 42px target, macOS only) is a known local failure. It is reported, not fixed, in every gate count.
- **Tests encode intent.** Names say the outcome. Synthetic data only, "Demo" names. A guard that passes before its code gets a see-it-fail mutation, named in its task.

## Owner approvals (2026-11-24)

Recorded in `.superpowers/plan-4e/owner-decisions.md`:
- **E1** The closing sentence under each definition is `PLANS_EFFECTS_HELP`, not S:330's guide link (the ILND guide never mentions surrender or retain-and-explain, and it leans toward reaffirmation and redemption, `SL` §0.1).
- **E2** Each choice has one collapsed "What does … mean on this form?" panel holding its provision whole and unedited:
  - surrender and retain-and-explain: 11 U.S.C. § 521(a)(2)(A);
  - redeem: § 722;
  - reaffirm: § 524(c);
  - assumed lease: § 365(p)(2).
  Each panel closes with E1's pointer. The label is the approved question (Ruling M).
- **E3** Step 9 shows neither § 362(h) nor § 521(a)(6). 4i's signing and filing guide quotes both, apart from the choices (a Plane ticket, Task 9).
- **E4** Long names are stored and flagged (B47): `creditor_name` and `collateral_description` on Amounts Owed, and the lessor's name and lease description on Contracts & Leases. The box shows a too-long note, Review and the dashboard list a detail naming the form, and Generate refuses only while the box truly can't take it. The detail lives outside `claim_step_gaps`.
- **E5** Personas:
  - James reaffirms (Crestway, Camry);
  - Priya redeems (Kestrel, CR-V);
  - DeShawn retains and explains (Harrowgate, his home);
  - Andrés retains and explains on Copperline (Honda Fit), with "My brother Mateo, the co-owner, keeps paying the loan.", and assumes his Northlight vehicle lease, Yes.
  No persona surrenders. Surrender is covered by synthetic tier 3 and vitest. Maria and Sarah have no Form 108.
- **E6** Step 9 shows Form 108's own deadline sentence, word for word, labelled as the form's words, from `formText.ts` pinned to the template. The 14-day ILND conflict and the steps after filing stay in 4i.
- **E7** Every sentence in `OC` is approved as drafted (`DRAFT: counsel C-37`), with the reworded `INTENTION_GAP_NONE` and `LEASE_GAP_NONE`.
- **E8** New and corrected words: `WHAT_DOES_EXPLAIN_MEAN` and `CLAIM_TEXT_LABELS.explain` are approved, and `PLANS_UNDECIDED_INFO`, `INTENTION_GAP_UNDECIDED` and `LEASE_GAP_UNDECIDED` replace E7's versions (they no longer say an open row's boxes print blank: its creditor, property and exempt box still print).

The controller's rulings, binding over the spec:
- **R-SHAPE** §7.3's id-keyed object stays. It prints through new `claims.secured[]` cells and a new `claims.leases[]` list joined by id inside the one claims read.
- **R-LEASE-GATE** Today's lease-kind gate stays (`CONTRACT_GAP_LEASE_KIND`, a Complete gate). B15's "detail" is stale. `claims.leases` still includes a null kind, defensively.
- **R-EXEMPT** The exempt box prints:
  - Yes only when a Schedule C claim that prints (`exemption_items`' rows) names the debt's live linked property (`link_is_live`);
  - No whenever `ExemptionAnswers.no_claims` is True;
  - blank otherwise, including a null `secured_by` without `no_claims`.
- **R-PRUNE** The record keeps answers for ids the session no longer has, and readers ignore them. A save of step 9 drops ids not in the current confirmed secured debts and leases. Drafts get no intention until confirmed.
- **R-EXPLAIN** The "[explain]" text has a measured cap across Explain1 + Explain2 (the split rule below, 4e-R5), stored and flagged as E4 does.

The controller's plan-review rulings, binding:
- **R-BLANK-EXPLAIN** A `retain_explain` row whose words are blank after trimming ticks no choice box (S:531) and stays an `INTENTION_GAP_EXPLAIN` detail.
- **R-521-LEAD** The § 521(a)(2)(A) panel quotes what makes (A) a sentence: "(a) The debtor shall—", paragraph (2)'s opening words, then (A) whole, with each omitted paragraph shown as "[…]" (4e-R7). Task 6 Step 0 verifies the fetched text and pins it.
- **R-FORM-WORDS** `OC`'s "Form words (formText.ts)" section holds the form's and the statutes' own words, approved in kind by E2 and E6, not DigniFi sentences. The copy gate treats only the table and E8 as approved DigniFi words.
- **R-REVIEW-ONCE** Review shows step 9's open rows once, through its existing gap list (details included). There is no second section, and the approved heading "Form 108 choices you left open" is not used.
- **R-SAVE-ORDER** `IntentionAnswers` saves and prunes after the same PATCH's debts and contracts are written. Planner's note: `IntakeSessionSerializer` has no contracts field today (contracts save through `PUT …/contracts/`, and `serializers.py` names `executory_contracts` only at `:2263`, outside it), so in 4e only the debts share a PATCH; a later PR that adds contracts to the session PATCH must place the save after that write too.

**Approved words** (E7 and E8; builders copy them verbatim, each with `// DRAFT: counsel C-37` above it in `copy.ts`, or `# DRAFT: counsel C-37` in Python). `OC` names 21 constants (E7's 20 and E8's `WHAT_DOES_EXPLAIN_MEAN`), and every row below ships except `PLANS_REVIEW_HEADING`, approved but not shipped (R-REVIEW-ONCE):

| Constant | Words |
|---|---|
| `PLANS_TITLE` (step heading) | Your plans for what you owe on |
| `WIZARD_STEPS` label | Your Plans |
| `PLANS_INTRO` | These questions are for Form 108. It lists each debt secured by your property and each lease of personal property. For each one, you choose what the form says. DigniFi doesn't choose for you. |
| `PLANS_NOT_APPLICABLE` | DigniFi isn't preparing Form 108. You listed no debt secured by your property and no lease of personal property. If that isn't right, go back to Amounts Owed or Contracts & Leases. |
| `PLANS_UNDECIDED` | I haven't decided yet. |
| `PLANS_UNDECIDED_INFO` (E8) | You can leave a choice open and come back to it. While it is open, no choice is ticked for that row on Form 108. |
| `PLANS_EXPLAIN_LABEL` | Your words for the form |
| `PLANS_EXEMPT_LISTED` | Your Schedule C lists this property. |
| `PLANS_EXEMPT_NOT_CLAIMING` | Your Schedule C doesn't list this property. |
| `PLANS_EXEMPT_LATER` | You answer Schedule C after you finish these steps. This box follows your answers there. |
| `PLANS_EXEMPT_NOT_NAMED` | Your Schedule C answers don't name this property, so this box prints blank. |
| `PLANS_EXEMPT_NO_PROPERTY` | This debt isn't linked to property on your Assets step, so this box prints blank. |
| `WHAT_DOES_SURRENDER_MEAN` | What does “surrender” mean on this form? |
| `WHAT_DOES_REDEEM_MEAN` | What does “redeem” mean on this form? |
| `WHAT_DOES_REAFFIRM_MEAN` | What is a “Reaffirmation Agreement” on this form? |
| `WHAT_DOES_EXPLAIN_MEAN` (E8; the retain-and-explain panel) | What does “retain” mean on this form? |
| `WHAT_DOES_ASSUME_MEAN` | What does it mean for a lease to be “assumed”? |
| `PLANS_EFFECTS_HELP` | A licensed attorney can answer questions about your own case. The court's pro se help desk takes calls at (312) 229-6344. |
| `INTENTION_GAP_NONE` | Choose what you plan to do with the property for {name}, or say you haven't decided. |
| `INTENTION_GAP_UNDECIDED` (E8) | Your choice for {name} is open, so Form 108 shows no choice for it. |
| `INTENTION_GAP_EXPLAIN` | Type your words for {name}, or choose another answer. |
| `LEASE_GAP_NONE` | Say if the lease with {name} will be assumed, or that you haven't decided yet. |
| `LEASE_GAP_UNDECIDED` (E8) | Your answer for the lease with {name} is open, so Form 108 shows no answer for it. |
| too-long detail (the C-42 sentence, reused: `SCHEDULE_I_DETAIL_TOO_LONG` / `schedule_i.DETAIL_TOO_LONG`) | Your answer for {label} is too long for its box on {form}. |
| `CLAIM_TEXT_LABELS` | the creditor's name / the description of the property / the lessor's name / the description of the leased property / the explanation of your plan (`explain`, E8) |
| `PLANS_REVIEW_HEADING` (not shipped, R-REVIEW-ONCE) | Form 108 choices you left open |
| `PLANS_FROM_DEBTS` / `PLANS_FROM_CONTRACTS` | From your Amounts Owed step / From your Contracts & Leases step |
| `PLANS_DEADLINE_LABEL` | Form 108 says: |

## Rulings this plan makes (decided here, recorded for the owner)

`OD` settles E1–E8, the five controller rulings and the five plan-review rulings. These are the rest, including the critic's §§0–4 items that `OD` doesn't answer.

- **4e-R1 The `intentions.` namespace is removed** (R-SHAPE: "removed if 4a's plumbing has no other reader"; `SC` §4).
  - Its only readers are 4a's plumbing and its own placeholder tests: `answer_records.py:4,13,20,235-236`, `schema.py:288,839,929`, `fill_resolver.py:466,604`, `test_answer_records.py:2,113,199-205,215,228` and `test_checks.py:958,1260`.
  - Leaving it would be a silent hole: any key binds and prints blank, with no startup check.
  - `RECORD_OF_NAMESPACE`, `ANSWER_NAMESPACES` and `record_step` lose it. `"plans"` leaves `NEW_STEP_KEYS` in Task 7 (S:238).
- **4e-R2 Which rows step 9 shows** (R-PRUNE, `SW` §6, `SC` §0.8).
  - The browser shows a Part 1 row for each `debtsData` row with an `id`, `is_secured` true and `is_draft` false, and a Part 2 row for each `contractsData` row with an `id`, `contract_type === 'lease'` and `lease_kind !== 'residential'` (null included).
  - The wizard's `debtsData` keeps `is_draft: true` after Continue on Amounts Owed until a reload (`SW` §6), while the server clears it in `update_step` 7 (`views.py:239-240`). So the wizard clears `is_draft` on its own rows once `updateCurrentStep(7)` resolves, mirroring the server. Then the browser's scope and the server's prune scope agree.
  - Step 6's body carries `is_draft` today (`sentDebt` spreads the whole row, `frontend/src/utils/claimRows.ts:123-135`), so the clear would change that body and Go Back to Amounts Owed would autosave and reopen a completed intake. `sentDebt` therefore deletes `is_draft` as it deletes `_securedPressed`. The server loses nothing: `is_draft` is read-only (`serializers.py:794`).
  - A never-confirmed scanned draft reached by `?step=plans` shows no row. Complete refuses while it stands anyway (DIG-163), and Form 108 never prints it (`confirmed()`).
  - Accepted, for the owner to see: if that draft is the session's only secured debt and no lease is in scope, the step shows `PLANS_NOT_APPLICABLE` ("You listed no debt secured by your property…"), which is untrue while the draft stands. No wrong form results, since Complete refuses meanwhile and Review lists the draft gap.
- **4e-R3 The step 9 body.**
  - `{intention_answers: {secured: {...}, leases: {...}}}`, built by one function, `plansBody(answers, securedRows, leaseRows)`, from in-scope rows only, keyed by server id (string).
  - Each entry carries only the keys that hold a value: `intention` and `explain` (a non-blank string, as typed), or `assumed`. An entry with no key is left out. Loaded and edited data pass through the same function, so a visit sends nothing (CLAUDE.md "Autosave sends only real edits").
  - With no in-scope row at all, `plansBody` returns `null` and the step body is `null` too, never `{intention_answers: null}`: `const body = plansBody(…); return body === null ? null : {intention_answers: body};`. Nothing is sent, Continue included (`saveCurrentStepData(null)` sends nothing, as on Review today), so a not-applicable step never reopens a completed intake. Stored stale ids wait for the next save that carries rows (R-PRUNE's stated cost).
  - `intention_exempt` and `answered_on` are never sent.
- **4e-R4 The E4 measure.** Which forms, and how (advisor; `SC` §4 decision 3).
  - Schedule D's name box (148 pt) is narrower than Form 108's (196 pt). Measuring Form 108 alone would leave a name Schedule D refuses unlisted, which breaks the house invariant that Review lists every too-long text Generate refuses.
  - So each text is measured through `PDFFormFiller().check()` in every box that prints it, on the forms its own row prints on, never on a form the row doesn't reach:

    | Text | The row's list | Boxes (form: binding) | Gap step |
    |---|---|---|---|
    | `creditor_name` | `secured` | Form 108 and Schedule D: `claims.secured[].name` | `debts` |
    | `creditor_name` | `priority` | Schedule E/F: `claims.priority[].name` | `debts` |
    | `creditor_name` | `unsecured` | Schedule E/F: `claims.unsecured[].name` | `debts` |
    | `collateral_description` | `secured` | Form 108 and Schedule D: `claims.secured[].property` | `debts` |
    | `counterparty_name` | a lease in `leases` | Schedule G: `claims.contracts[].name`; Form 108: `claims.leases[].name` | `contracts` |
    | `counterparty_name` | a residential lease | Schedule G: `claims.contracts[].name` | `contracts` |
    | `description` | a lease in `leases` | Schedule G: `claims.contracts[].purpose`; Form 108: `claims.leases[].purpose` | `contracts` |
    | `description` | a residential lease | Schedule G: `claims.contracts[].purpose` | `contracts` |
    | `explain` | `secured`, under `retain_explain` | Form 108: `Explain1` + `Explain2` through `split_explain`, and the Part 1 sheet past row 4 | `plans` |

  - **The caps go by box, not by text.** `form_108.limits.json` holds one cap per box, keyed `"<form>:<binding>"` (`"form_108:explain"` for the pair). A row's cap for a text is the smallest cap among the boxes of its own row's list, and the cap's forms are the forms holding that smallest cap. So an unsecured debt's long name is never "too long for its box on Schedule D", and a residential lease's description is never measured against Form 108's two-line box. The browser picks the row's list the same way: `is_secured`; `priority_answer` in the four priority kinds; `contract_type === 'lease'` and `lease_kind`. A shared case file pins the browser's choice to the server's.
  - Each row is measured in its own slot box. A row on a copy of D's, E/F's or G's extra page is measured in each slot box of its column (the copies repeat the same boxes, so the narrowest governs). A Form 108 row past capacity is measured on the sheet, as `petition_fit._sheet_refusals` measures.
  - A detail is listed when the text is over its row's cap (by length, as the browser's note counts) or `check()` refuses it as too long. Only `ValueTooLong` counts: a letter the font can't print (`UnprintableLetter`) is no too-long detail and keeps Generate's own refusal, as `petition_fit.too_long` measures only fit. `{form}` names the refusing forms, plus the cap's form(s), joined with " and " in packet order (`Form 108`, `Schedule D`, `Schedule E/F`, `Schedule G`).
  - Left out, each keeping today's refusal (a Plane ticket, Task 9): the List of Creditors' entry (a name-and-address composite with its own per-row fix), Form 122A-2's creditor and property cells (`means_fit.py` measures them on the 122A-2 page) and a non-lease contract's texts (no approved label fits a non-lease counterparty).
- **4e-R5 The Explain split** (B29, R-EXPLAIN; `SF` §4). This is the one body the plan writes, because no test decides it:

  ```python
  def split_explain(text: str) -> tuple[str, str]:
      """Explain1 takes the longest run of whole leading words that fits its box, letters and
      size alike, down to 6 pt (check()'s own test, text_fit.fit); Explain2 takes the rest.
      A first word that doesn't fit leaves Explain1 blank. Spaces are split on as typed and the
      join drops only the one space at the break, so the non-blank halves joined by one space
      are the text: " ".join(p for p in split_explain(text) if p) == text."""
      words = text.split(" ")
      cut = 0
      for n in range(1, len(words) + 1):
          if _fits_explain_1(" ".join(words[:n])):
              cut = n
          else:
              break
      return " ".join(words[:cut]), " ".join(words[cut:])
  ```

  - `_fits_explain_1(text)` is `exemption_items._fits`'s test on `Explain1 1a` of `form_b108.pdf`: `_refused_letter` is None and `fit(widget, TEMPLATE, _as_printed(text))` is not None. It imports `pdf_filler`, `widgets` and `text_fit` inside its body, never at module level: `pdf_filler.py:57` imports `fill_resolver`, whose `CLAIM_CELLS` imports `split_explain`, so a module-level import is a certain cycle ("partially initialized module"), not a possible one (the `exemption_items` precedent, `fill_resolver.py:529`). The four Explain1 boxes are 50.5 pt wide to 0.1 pt (read 2026-11-24), so row 1a's stands for all four.
  - Each box sizes itself in `check()`, so Explain1 may print at 6 pt beside Explain2 at a larger size. That is accepted and recorded. One shared size would need the engine to size two boxes together, which no form does today.
  - The cap: `form_108.limits.json` `"form_108:explain"` = cap(Explain1) + cap(Explain2), each `floor((width − 4 × margin) / widest digit at 6 pt)`, the 101A formula (about 13 + 49 = 62; the tool's figure is pinned).
  - The too-long detail is listed when `len(explain) > cap` or `check()` refuses the split pair, so the list and Generate agree.
  - Persona fit: Andrés's words (54 characters) and DeShawn's (59, 4e-R18) are both under 62, and Task 8's tier 3 draws them. The margin is thin (the cap is the tool's measure), so Task 8 asserts that no persona's seeded explanation raises a `claim_text_gaps` detail, and a tool cap below 59 fails loudly.
- **4e-R6 The exempt state, one function** (R-EXEMPT; `SC` §0.4, §4).
  - `exempt_states(session) -> dict[int, str]`, in `apps/intake/exemptions.py` (pure, no models), covers every secured debt of the session, drafts included (the step reads drafts' states only after 4e-R2's clear). Precedence:
    1. `getattr(session, "exemption_answers", None)` with `no_claims` True → `"not_claiming"` (box No), even with a null link;
    2. `not link_is_live(debt.secured_by, session)` → `"no_property"` (blank);
    3. `debt.secured_by_id` among the printed claims' asset ids → `"listed"` (box Yes);
    4. no `exemption_answers` record and no `exemption_claims` row → `"later"` (blank);
    5. otherwise → `"not_named"` (blank).
  - "A printed claim" is one whose `asset_id` names a row of `session.assets` whose `ab_line` is in `LINE_BY_KEY`, the filter `exemption_items._read_rows` applies (`exemption_items.py:192-198`). A test pins that the two agree. `exemption_items` is not edited.
  - `claim_rows._read` maps the state to the box (`listed` → `"yes"`, `not_claiming` → `"no"`, else `""`).
  - The session read gains a read-only `intention_exempt`, `{"<debt id>": state}`, from the same function. It stays out of every body.
  - `exemption_items` imports `fill_resolver` (`fill_resolver.py:529`), so nothing on the forms side imports it at module level. `exemptions.py` imports only `asset_lines.LINE_BY_KEY` and `claims.link_is_live`, both pure.
  - `exempt_states` reads the debts through `session.debts.select_related("secured_by")`, a fresh query, never the view's `debts` prefetch, which is stale in a PATCH reply for rows that PATCH added (`serializers.py:1487-1490` writes them after the prefetch). The cost is one debts query on every session read, the list endpoint included; it is accepted and noted.
  - The views' `select_related` (`views.py:152-162`) gains `exemption_answers` and `intention_answers`, and `prefetch_related` (`:163`) gains `exemption_claims` and `executory_contracts`. That widens every action's read, the list endpoint's included; accepted and noted.
  - The step reads `intention_exempt` from the session load only (the wizard takes nothing else from a save's reply). A row whose id has no state (a debt made secured since the read) shows no exempt line.
- **4e-R7 The definitions** (E2, Ruling M; `SL` §3).
  - Part 1 renders four panels once, above its rows, in the form's order: surrender, redeem, reaffirm, explain. Part 2 renders one, above its rows. Rendering them once per Part keeps the accessible names from repeating per row (S:1094).
  - § 521(a)(2)(A) is shown as R-521-LEAD rules: what makes (A) a sentence, with the citation `11 U.S.C. § 521(a)(2)(A)`. Five lines, each quoted segment verbatim from the served page, and "[…]" (U+005B, U+2026, U+005D) at each place text is left out:
    1. `(a) The debtor shall—` (subsection (a)'s opening words);
    2. `[…]` (paragraph (1));
    3. `(2) if an individual debtor’s schedule of assets and liabilities includes debts which are secured by property of the estate—` (paragraph (2)'s opening words);
    4. (A) whole, ending `…or that the debtor intends to reaffirm debts secured by such property; and` (pasted from the served page in Task 6 Step 0, never typed from memory);
    5. `[…]` ((B) and paragraphs (3) onward).
    The owner should see this rendering (counsel may prefer another extent, C-37).
  - The retain-and-explain panel quotes the same § 521(a)(2)(A) text, under its own label, `WHAT_DOES_EXPLAIN_MEAN` (E8).
  - `WhatDoesThisMean` gains an optional `note?: string`, rendered inside `<details>` after the citation, which carries `PLANS_EFFECTS_HELP`. Existing callers pass none, and their output is unchanged.
- **4e-R8 The E2E contract and `walkPlans`** (`SC` §4; S:756, S:760).
  - Each row is a `<fieldset>` whose `<legend>` is the creditor's (lessor's) name, or "one amount owed" ("one contract") when blank, the claims row-name convention (`claimRowName`). Inside it, the name shows again under the form's own label, `FORM_108_CREDITOR_LABEL` ("Creditor’s name:") or `FORM_108_LESSOR_LABEL` ("Lessor’s name:"), as the property shows under its label (S:326, S:332).
  - Names: radios `plans_secured_<i>_intention`, with values `surrender`, `retain_redeem`, `retain_reaffirm`, `retain_explain` and `undecided`; the text box `plans_secured_<i>_explain`; radios `plans_lease_<i>_assumed`, with values `no`, `yes` and `undecided`. `<i>` is the row's position in the step's list.
  - Rows show in the wizard's list order. Form 108's print order is the server's (`ordered_debts`), so E2E finds rows by legend, never by position.
  - `walkPlans(persona: Pick<PersonaData, 'plans'>)`, with `plans: {secured: PersonaIntention[]; leases: PersonaLeasePlan[]}`:
    - with both lists empty (Maria, Sarah) it asserts `PLANS_NOT_APPLICABLE` and presses Continue;
    - otherwise it checks each row's radio inside the fieldset its name labels, types `explain` under `retain_explain`, and presses Continue.
    This replaces S:756's `walkPlans(choice)`, which can't express zero rows or a debt plus a lease.
- **4e-R9 Form 108's sheet groups** (S:532; `SF` §3, `SC` §4).
  - `f108_part_1`: four slots, `number: "1.{n}"`, title "Official Form 108, Statement of Intention for Individuals Filing Under Chapter 7, Part 1". Columns:
    - `claims.secured[].name` "Creditor’s name:";
    - `claims.secured[].property` "Description of property securing debt:";
    - `claims.secured[].intention` "What do you intend to do with the property that secures a debt?";
    - `claims.secured[].explain` "[explain]", with `covers: ["claims.secured[].explain_1", "claims.secured[].explain_2"]`;
    - `claims.secured[].exempt` "Did you claim the property as exempt on Schedule C?".
  - `f108_part_2`: seven slots, `number: "2.{n}"`, title "…, Part 2". Columns: `claims.leases[].name` "Lessor’s name:", `claims.leases[].purpose` "Description of leased property:", `claims.leases[].assumed` "Will the lease be assumed?".
  - The widths are the builder's: at most 504 pt with the 36 pt line column, each label `prints_whole`.
  - Every label is the form's own words. The index's `option_text` for `check1`'s four states is the form's words verbatim, "Retain the property and [explain]:" included (rule: the form's words, never DigniFi's). The explanation prints in its own column beside it.
  - `_LIST_BINDING` gains `claims\.\w+` (`schema.py:837-841`), and its message (`:926-930`, pinned at `test_checks.py:1252-1262`) names `claims.<list>[].<attr>`, dropping `intentions.` (4e-R1).
- **4e-R10 `binding_fix` routes `claims.` by list and attribute** (`SF` §0.5, the `means.` precedent `fill_resolver.py:630-638`):
  - `leases` → `{"step": "contracts"}`, except `assumed` → `{"step": "plans"}`;
  - `secured` `intention`, `explain`, `explain_1`, `explain_2` → `{"step": "plans"}`;
  - `secured` `exempt` → `{"page": "/exemptions"}`;
  - everything else as today.
- **4e-R11 Where the gaps sit in Complete's list** (`SS` §9 "Gaps"; S:209). All are `DETAIL`.
  - `claim_text_gaps`' `debts` details are spliced at the Debts point, after line 16's gaps (`completion.py:130-133`).
  - Its `contracts` details go with the rent gates, before Codebtors (`:135-136`).
  - `intention_step_gaps` and the `plans` too-long detail go after the claims head (`:137`) and before the tail (`:138`), which stays last on purpose (3c4).
  - `Gap.forms`: `("form_108",)` for every `plans` detail, and the refusing or cap forms (4e-R4) for each too-long detail. The step 9 gaps come in Form 108's order (Part 1 in Schedule D order, then Part 2), one gap at most per row.
- **4e-R12 The shift migration.** `0049_shift_current_step_for_plans`:
  - forward: `current_step == 9` → 10;
  - reverse: `== 10` → 9 (a row on Plans reverses to 9 = the old Review; lossy only for rows on the new step, R11 S:836);
  - a value outside 1–9 is left alone (the 0028 pattern).
  - Every server-side step number stays: `== 7` (draft confirm) and `== 3` (income window). The seed's `current_step=7` stays.
- **4e-R13 Review and the dashboard.**
  - Review gains no section (R-REVIEW-ONCE). Its existing gap list (`ReviewStep.tsx:227-246`, every gap the gaps endpoint returns, details included) already shows each open row's `plans` detail once, with "Go to Your Plans" once `plans` is in `WIZARD_STEPS` (Task 7). `ReviewStep.tsx` is not edited, and `PLANS_REVIEW_HEADING` is not shipped.
  - The step itself lists its open rows (S:208): a `role="status"` region after the Parts, mounted whenever a Part shows and never an alert, holding `openPlanRows`' approved gap sentences in the step's order, and empty when every row is chosen.
  - The dashboard's `answerPathOf` maps `form_108` → `/intake?step=plans` (`FormDashboard.tsx:465-471`), so a refused pending card never falls back to `/ask/form_108`.
- **4e-R14 Labels and order of the form type.**
  - `FORM_TYPE_CHOICES` gets `("form_108", "Form 108 - Statement of Intention")`.
  - `FORM_TYPE_METADATA.form_108` gets label `'Form 108 - Statement of Intention'`, the description the form's own title, "Statement of Intention for Individuals Filing Under Chapter 7" (form words, no new sentence), and `order: 7`. Every later `order` moves up one.
  - The `list_of_creditors` order oddity predates 4e and is left (`SF` §8).
- **4e-R15 The completion percentage** counts five sections (`views.py:807-808`), and step 9 is not one. It is left, and noted for Plane (`SC` §4).
- **4e-R16 Explain under another choice** (the 4d-R15 house rule). Stored words under a choice other than `retain_explain` stay behind `HiddenLine`, with Show and Delete (`HIDDEN_ANSWERS`, `copy.ts:1795`). Delete removes `explain` from the entry. The words print nowhere and raise no gap.
- **4e-R17 The record's ceilings** (B47: refuse only an unknown key, a wrong type or a value over a hard ceiling):
  - at most 100 ids per top key (`ROW_CEILING`);
  - `explain` at most 500 characters (`TEXT_CEILING`), and writable in UTF-8;
  - an id key must match `^[1-9][0-9]{0,9}$`.
  - An id not of this session is pruned, not refused.
- **4e-R18 DeShawn's words.** E5 names DeShawn's choice but not his words. The plan uses S:752's draft, "I am current on the mortgage and will keep paying as agreed", and the owner should see it. Each brief gains S:756's sentence, "This is {name}'s own choice for the demo, not a recommended one.", in `docs/testing/persona-briefs/` (never `copy.ts`, where `/recommend/` trips `ADVICE`).
- **4e-R19 Statute source.** uscode.house.gov, in the URL form 4d's comments use (`https://uscode.house.gov/us/usc/t11/s<section>`). It answered 200 on 2026-11-24 for §§ 365, 521, 524 and 722; the `granuleid:` form answered 404. Task 6 re-fetches and pins each provision word for word. No statute text is written from memory.
- **4e-R20 The too-long labels.** The four approved labels are used as written. A detail on Review names the label, not the row: "the description of the property" with two secured debts doesn't say which. The box note sits beside its own row, and the `GapLink` opens the step. This residual ambiguity is recorded for the owner. The explanation's label is E8's, "the explanation of your plan".
- **4e-R21 Gap row names.** `{name}` is the creditor's or lessor's name, stripped, or "one amount owed" / "one contract" (`claims.py`'s row-noun convention).
- **4e-R22 Leases reuse `ContractRow`.** `ContractRow` gains `assumed: str = ""`. `ClaimRows.leases` holds `dataclasses.replace(row, assumed=…)` for each in-scope contract row, so `_address_of`'s `ContractRow` branch (`fill_resolver.py:197-232`) gives the name. `DebtRow` gains `intention: str = ""`, `explain: str = ""` and `exempt: str = ""`. With defaults, no other constructor changes (`SC` §0.3).
  - `DebtRow.intention` is the printed choice, not the stored one (R-BLANK-EXPLAIN): `claim_rows._read` sets it to the stored value when it is in `FORM_INTENTIONS`, except `""` for `retain_explain` whose words are blank after `strip()`, and `""` otherwise. `check1`, the Part 1 sheet's intention column and the `explain` cells all read that one value, so a blank-words row ticks nothing and prints no "[explain]" words.
  - The gaps never read `DebtRow.intention`: `intention_row_gap(name, entry)` reads the stored entry, so a blank-words `retain_explain` is `INTENTION_GAP_EXPLAIN`, never `INTENTION_GAP_NONE`.
- **4e-R23 One lease filter.** `claims.py` gains `FORM_108_LEASE_KINDS = ("vehicle", "other_personal_property", "other", None)` and `is_form_108_lease(contract) -> bool`. The save's prune, `claim_rows`, the browser's `leasePlanRows` (pinned by the lease rows of `claimTextRowCases.json`, which the server reads through `is_form_108_lease`) and Form 108's `applies` read it. `lease_kind` is encrypted, so the filter runs in Python.

## Review Focus

Five conditions most likely to pass a task review while wrong:

1. **Never a box the filer didn't give.** `undecided`, absent and `retain_explain` with blank words tick nothing on `check1` and `check2x`, the exempt box is No only under `no_claims`, and Explain prints only under `retain_explain` with words.
   - Task 4 `test_every_intention_answer_ticks_its_one_box_and_open_ticks_none` (drawn and read back, one case per value plus absent, `undecided` and `retain_explain` with words `"   "`).
   - Task 4 `test_the_exempt_box_follows_schedule_c_and_never_absence` (the five states, a moved or orphaned claim, `no_claims` with a null link).
2. **A deleted or added debt never moves a sworn choice onto another creditor.** Rows print in Schedule D's order, joined by id.
   - Task 4 `test_a_choice_stays_with_its_creditor_when_an_earlier_row_is_added_or_removed`.
3. **The step 9 body is built the same way from loaded and edited data, in the server's scope** (4e-R2, 4e-R3, R-PRUNE).
   - Task 7 `a visit to Your Plans sends nothing`, `a scanned secured debt confirmed on Amounts Owed gets a row on Your Plans`, `Go Back to Amounts Owed after confirming a draft sends nothing`, `a draft never confirmed gets no row` and `with no secured debt or lease, Continue sends nothing`.
   - Task 2 `test_a_save_prunes_ids_that_are_no_longer_in_scope` (drafts, unsecured, residential, another session's id) and `test_one_patch_dropping_a_secured_debt_and_keying_a_choice_to_it_stores_none` (R-SAVE-ORDER).
4. **No detail turns into a gate, and no box note holds Continue** (E4, R-EXPLAIN, DIG-542).
   - Task 5 `test_too_long_and_open_choices_never_hold_complete`.
   - Task 6 `a too-long creditor name shows its note and leaves Continue enabled` (DebtsStep and ContractsStep).
   - Task 5 `GapsNotice leaves the claims too-long details out of the blank count` (passes at once; its see-it-fail is named there).
5. **Review lists every too-long text Generate refuses** (4e-R4, 4e-R5).
   - Task 5 `test_every_text_generate_refuses_as_too_long_is_listed` (a name that fits Form 108 but not Schedule D; a sheet row), `test_an_unsecured_creditors_long_name_never_names_schedule_d_or_form_108` and `test_an_explanation_whose_break_overflows_explain_2_is_listed`.

---

### Task 1: DIG-547's three backend test gaps

**Files:**
- Modify:
  - `backend/apps/forms/tests/test_means_mark_filed.py` (a test after `:255`, using its fixtures `:39-83` and helpers `_generate` `:90`, `_mark_filed` `:98`);
  - `backend/apps/eligibility/tests/test_means_lines.py`: the `test_route_outcome_follows_the_supps_order` parameters (`:283` area, the `neither-above` case), and a test beside `LINE_2_YES_YES` (`:269`).

**Interfaces:** none produced. It consumes `NotInPacket`'s sentence (`backend/apps/forms/views.py:123`), `route_outcome`, `military_question_open` and `LINE_2_YES_YES`.

- [ ] **Step 1: Write the tests.**
  - `test_a_stale_122a2_row_under_a_supp_outcome_is_not_in_the_packet`:
    - generate Form 122A-2 on the file's above-median consumer session;
    - then `answer_petition(session, debt_nature="business")` (a Supp outcome);
    - `POST mark_filed` on the stale 122A-2 row → 422, `error` equals `NotInPacket`'s sentence ("This form isn't part of your packet, based on the answers you've given."), no `step` or `page` key;
    - the row's `status` is still `"generated"`, and its `field_values` equal the copy read before the call.
  - A `route_outcome` case: `pytest.param({"debt_nature": "neither"}, False, NOT_CONSUMER, id="neither-below")`.
  - `test_line_2_yes_yes_leaves_no_line_3_question_open`: `military_question_open({**LINE_2_YES_YES, "reservist": None}) is False`.
- [ ] **Step 2: Run them.** `pt.sh apps/forms/tests/test_means_mark_filed.py apps/eligibility/tests/test_means_lines.py --ds=config.settings.test -q`. Expected: pass at once; they close coverage gaps.
  - See-it-fail, each reverted:
    - make `mark_filed` skip its packet check for a means form, and show the first test fail;
    - return `AT_OR_BELOW_MEDIAN` before the not-consumer branch, and show `neither-below` fail;
    - drop the `supp_line_3_reached` guard on `reservist` in `military_question_open`, and show the third fail.
- [ ] **Step 3: Commit** `tests: DIG-547, a stale 122A-2 under a Supp outcome, a below-median neither and line 2 Yes/Yes` with the two paths.

### Task 2: `IntentionAnswers`, its save, prune and read, and the exempt state

**Files:**
- Create:
  - `backend/apps/intake/migrations/0048_intention_answers.py` (one `CreateModel`, depending on `0047_label_combined_expense_figures`);
  - `backend/apps/intake/tests/test_intention_answers.py`;
  - `backend/apps/intake/tests/test_intention_encryption.py`;
  - `backend/apps/intake/tests/test_exempt_states.py`;
  - `backend/apps/intake/tests/test_claims.py` (the `is_form_108_lease` unit; no such file exists today).
- Modify:
  - `backend/apps/intake/models.py`: the new class after `ScheduleIAnswers` (`:1028-1159`, the pattern);
  - `backend/apps/intake/claims.py`: `FORM_108_LEASE_KINDS` and `is_form_108_lease` (4e-R23), beside `link_is_live` (`:188`);
  - `backend/apps/intake/exemptions.py`: `EXEMPT_*` constants and `exempt_states` (4e-R6);
  - `backend/apps/intake/serializers.py`:
    - `_INTAKE_DATA` `:1019-1031` gains `"intention_answers"`;
    - `IntentionAnswersField` after `ScheduleIAnswersField` `:1137-1145`;
    - `_save_intention_answers` after `:1148-1153`;
    - field and `fields` `:1216`, `:1242`;
    - read-only `intention_exempt` beside `paystub_employer_name` `:1224`, `:1248`, `:1263`;
    - `validate_intention_answers` after `:1318-1330`;
    - the empty-body guard `:1419-1424`;
    - pop in `update()` `:1438` and in `create()` `:1366`; save after the debts are written (R-SAVE-ORDER): in `update()` after the `debts` `_save_rows_by_id` block (`:1487-1490`), just before `return instance` (`:1491`), and in `create()` after `_save_rows_by_id(session, DebtInfo, …)` (`:1404`), just before `return session`. `update()` writes debts last, after every record save, so a save placed after `_save_schedule_i_answers` (`:1478`) would prune before this PATCH's debts exist: a debt made secured in it would lose its choice, and a debt deleted in it would keep one;
  - `backend/apps/intake/views.py:152-163`: `select_related` and `prefetch_related` (4e-R6);
  - `backend/apps/intake/tests/builders.py`: `answer_intentions` after `answer_schedule_i` (`:251-262`);
  - `backend/apps/intake/tests/test_session_lock.py:554`: `WRITES` gains an `intention_answers PATCH` row (the `schedule_i_answers PATCH` pattern, `:601-604`);
  - `frontend/src/types/api.ts:47-49`: `intention_answers?` and `intention_exempt?`, plus the types below.

**Interfaces:**
- Produces `IntentionAnswers` (`related_name="intention_answers"`, `db_table = "intention_answers"`):
  - `KEYS = ("secured", "leases")`;
  - `INTENTIONS = ("surrender", "retain_redeem", "retain_reaffirm", "retain_explain", "undecided")`;
  - `FORM_INTENTIONS = INTENTIONS[:4]`;
  - `ASSUMED = ("yes", "no", "undecided")`;
  - `TEXT_CEILING = 500`, `ROW_CEILING = 100`;
  - `answers = EncryptedTextField(default="{}")`, `answered_on = EncryptedCharField(max_length=10, null=True, blank=True)`, `created_at`, `updated_at`;
  - `get_answers() -> dict`;
  - `merge(sent: Mapping, secured_ids: set[int], lease_ids: set[int]) -> None`: every top key is checked first (an unknown one raises `KeyError`); each sent key is replaced whole (null removes it); then every stored id outside the two sets is dropped; `answered_on = fill_date().isoformat()` only when the stored object changed. It doesn't save.
- Produces, in `apps.intake.claims`, `FORM_108_LEASE_KINDS` and `is_form_108_lease(contract) -> bool`.
- Produces, in `apps.intake.exemptions`:
  - `EXEMPT_LISTED = "listed"`, `EXEMPT_NOT_CLAIMING = "not_claiming"`, `EXEMPT_LATER = "later"`, `EXEMPT_NOT_NAMED = "not_named"`, `EXEMPT_NO_PROPERTY = "no_property"`;
  - `EXEMPT_BOX = {EXEMPT_LISTED: "yes", EXEMPT_NOT_CLAIMING: "no"}`;
  - `exempt_states(session) -> dict[int, str]`.
- Produces, on the serializer:
  - `intention_answers` (read: the answers plus `answered_on`, or `{"answered_on": None}` with no record);
  - `intention_exempt` (read-only, `{str(pk): state}`).
- Produces `builders.answer_intentions(session, secured: dict | None = None, leases: dict | None = None)`. It writes through the session's relation; `None` leaves a key alone, and `{}` clears it.
- Produces the TypeScript types:
  - `Intention = 'surrender' | 'retain_redeem' | 'retain_reaffirm' | 'retain_explain' | 'undecided'`;
  - `Assumed = 'yes' | 'no' | 'undecided'`;
  - `ExemptState = 'listed' | 'not_claiming' | 'later' | 'not_named' | 'no_property'`;
  - `IntentionAnswers = {secured?: Record<string, {intention?: Intention; explain?: string}>; leases?: Record<string, {assumed?: Assumed}>; answered_on?: string | null}`.

- [ ] **Step 0: Check for drift.** Run `py.sh manage.py makemigrations --check --dry-run --settings=config.settings.test` on the untouched tree. Expected: "No changes detected". Otherwise stop and report.
- [ ] **Step 1: Write the failing tests.**
  - `test_intention_answers.py` (through the session PATCH):
    - `test_a_choice_saves_by_debt_id_and_reads_back` (a confirmed secured debt; `{"secured": {"<id>": {"intention": "retain_reaffirm"}}}`);
    - `test_each_top_key_sent_replaces_its_object_and_a_null_clears_it`;
    - `test_a_save_prunes_ids_that_are_no_longer_in_scope`, parametrized over a scanned draft secured debt, an unsecured debt, a residential lease, another session's debt id and a deleted debt id. Each id is gone from the stored object, and a null-kind lease, a `vehicle` lease and an `other` lease stay;
    - `test_one_patch_dropping_a_secured_debt_and_keying_a_choice_to_it_stores_none` (R-SAVE-ORDER): one PATCH carries `debts` without a stored secured row and `intention_answers` keyed to that row's id, and the stored object holds no entry for it; a second case makes an unsecured row secured in the same PATCH that sends its choice, and the choice is kept;
    - `test_an_unknown_key_wrong_type_or_value_over_its_ceiling_is_a_400_naming_the_key_not_the_value`: unknown top key, unknown entry key, intention `"keep"`, assumed `"maybe"`, a 501-character explain, 101 ids, id `"0"`, id `"abc"`, explain `"\ud800"`. The body never contains the sent value, and nothing is saved;
    - `test_an_echoed_answered_on_alone_saves_nothing_and_reopens_nothing`;
    - `test_saving_choices_reopens_a_completed_intake`;
    - `test_answered_on_moves_only_when_an_answer_changes`;
    - `test_the_session_read_carries_each_secured_debts_exempt_state` (`intention_exempt` keyed by id string; drafts included).
  - `test_exempt_states.py`:
    - `test_the_exempt_state_follows_the_precedence`, parametrized over the five rows of 4e-R6, plus `no_claims` with a null link → `not_claiming`, and a claim on an asset with no `ab_line` → `not_named`;
    - `test_a_claim_on_a_row_moved_to_another_session_is_not_listed` (`link_is_live` false → `no_property`);
    - `test_the_exempt_state_and_schedule_c_agree_on_which_claims_print`: for a session with a lined row, an unlined row and an orphaned claim, the asset ids `exempt_states` counts as printed equal the ids of `exemption_rows(session)`'s items.
  - `test_intention_encryption.py`: `test_intention_answers_are_ciphertext_at_rest`. The raw `answers` and `answered_on` columns start `gAAAAA` and contain neither `retain_explain` nor the debt id string.
  - `test_session_lock.py`: the `intention_answers PATCH` row in `WRITES` (the postgres twin runs in Task 9's `gate_pg.sh`).
  - The `claims.py` unit, in the new `test_claims.py`: `test_a_form_108_lease_is_any_lease_but_residential` (`vehicle`, `other_personal_property`, `other` and `None` in; `residential`, a `contract` type and a blank type out).
- [ ] **Step 2: Run them.** `pt.sh apps/intake/tests/test_intention_answers.py apps/intake/tests/test_intention_encryption.py apps/intake/tests/test_exempt_states.py apps/intake/tests/test_claims.py --ds=config.settings.test -q`. Expected: fail (`ImportError`, unknown field).
- [ ] **Step 3: Implement** the model, `0048`, the claims and exemptions helpers, the serializer pieces, the views' prefetches, the builder and the types.
  - `_save_intention_answers` reads `secured_ids = {d.pk for d in session.debts.confirmed() if d.is_secured}` and `lease_ids = {c.pk for c in session.executory_contracts.all() if is_form_108_lease(c)}`, then `get_or_create`, `merge`, `save`, and re-points `session.intention_answers`. `confirmed()` is a `filter` (`models.py:1163-1170`), so it queries afresh and sees the debts this PATCH just wrote, never the view's prefetch; the contracts' prefetch is safe, since a session PATCH never writes contracts.
  - `validate_intention_answers` copies `MeansTestAnswers.merge`'s all-or-nothing key check: it refuses before any write.
- [ ] **Step 4: Run** Step 2's command, then the blast radius: `apps/intake/tests/test_session_lock.py` (sqlite part), the serializer tests, `apps/intake/tests/test_data_migrations.py` (its `migrate` fixture unapplies `0048`, `SC` §0.7), `check`, `makemigrations --check --dry-run`, `ruff check` on every touched file, `ruff format --check` on the new files, and tsc.
  - See-it-fail: drop the prune from `merge`, and show `test_a_save_prunes_…[draft]` fail. Drop step 1 of `exempt_states`, and show the `no_claims`-with-null-link case fail. Move the `update()` save up beside `_save_schedule_i_answers`, and show `test_one_patch_dropping_a_secured_debt_…` fail.
- [ ] **Step 5: Commit** `intake: IntentionAnswers, saved by id and pruned to the session's confirmed secured debts and leases, with the exempt state` with the paths above.

### Task 3: Form 108's index tool and template test

**Files:**
- Create:
  - `data/forms/field_index/tools/build_form_108_index.py` (the `build_form_101a_index.py` pattern: `TYPES` `:46-53`, `ROWS` keyed by `(page, top-left rect rounded to 1 pt)` `:59-92`, per-page tags `:99-101`, the exits `:104-152`, `render` `:155-169`, `dumps()` `:172-186`, `TEMPLATE`/`SOURCE_URL`/`TEMPLATE_SHA256` `:40-42`);
  - `data/forms/field_index/form_b108.index.json` (written by the tool);
  - `backend/apps/forms/tests/test_form_108_template.py` (the `test_form_101a_template.py` pattern, with tags unique per page as `test_list_of_creditors_template.py` does for two pages).
- Modify: `data/forms/field_index/README.md` (`:3` "19 templates" → 20; Form 108's entry: source URL and the 2026-11-24 read, as 4b2 did).

**Interfaces:**
- Produces the index rows, labels unique per row:
  - the two `Debtor 1` kids and the two `Case number` kids each carry their own page label (e.g. "Caption: Debtor 1's name (page 2)");
  - every checkbox kid carries `option_text` in the form's words: `check1 1x` "Surrender the property." / "Retain the property and redeem it." / "Retain the property and enter into a Reaffirmation Agreement." / "Retain the property and [explain]:", and `check2 1x` and `check2x` "No" / "Yes";
  - the four push buttons are `form_control`.

- [ ] **Step 1: Write the failing test** `test_form_108_template.py`:
  - `test_the_committed_index_is_the_tools_output`;
  - `test_the_template_is_the_12_15_revision_we_indexed`: SHA-256 `fe51d222d87f461b8695e3d9b7a061e768b2a75824511d167cfba736ca35e8fe`, 87,667 bytes, 2 pages;
  - `test_the_widget_counts_are_pinned`: 83 rows, `Counter({"Text": 39, "CheckBox": 39, "ComboBox": 1, "Button": 4})` (PyMuPDF's `field_type_string`, read 2026-11-24), 45 on page 1 and 38 on page 2, 58 full names;
  - `test_tags_are_unique_per_page_and_labels_unique_overall`;
  - `test_every_checkbox_kid_carries_the_forms_words` (the eight phrases above);
  - the traps:
    - `test_check2_1a_and_check2a_are_different_fields`;
    - `test_row_2d_is_keyed_by_rectangle_not_widget_order`;
    - `test_explain1_and_explain2_are_the_two_boxes_of_one_line` (`Explain1 1a` 50.5 pt and `Explain2 1a` 169.7 pt wide, to 0.1 pt).
- [ ] **Step 2: Run it.** `pt.sh apps/forms/tests/test_form_108_template.py --ds=config.settings.test -q`. Expected: fail (no index).
- [ ] **Step 3: Implement** the tool (hand table by page and rectangle; no vision run, since every widget has a tooltip, S:523). Write the index with `/Users/controlroom/.claude/jobs/bb720722/tmp/venv-mac/bin/python -I data/forms/field_index/tools/build_form_108_index.py`, render the tagged PNGs to the job tmp, and check them by eye. Each widget's label must match the form's printed row.
- [ ] **Step 4: Run** Step 2's command, `ruff check` and `ruff format --check` on the new files, and prettier `--check` on the JSON.
- [ ] **Step 5: Commit** `forms: Form 108's field index, hand-adjudicated by page and rectangle, and its template test`.

### Task 4: Form 108 end to end: cells, schema, addendum, registry, the tiers and the packet counts

One commit, so the suite is never red between them (`SC` §2 (b), (c)): the cells and their reader, the schema, the 47 addendum rows, `ASSERTED_CASES`, `FORM_TYPE_CHOICES` and `0012`, the registry entry, every packet pin, the frontend form type and the E2E counts.

**Files:**
- Create:
  - `data/forms/field_index/tools/build_form_108.py` (the `build_form_101a.py` pattern: `BINDINGS` `:49-57`, `_by_label` `:85-89`, `schema()` `:114-127`, `addendum_rows()` `:138-166`, `merged()` `:173-184`, `limits()` `:192-214`; groups as `build_claims_schedules.py:131,734-746`);
  - `data/forms/schemas/form_108.json` and `data/forms/schemas/form_108.limits.json` (both written by the tool);
  - `backend/apps/forms/services/explain_split.py`;
  - `backend/apps/forms/migrations/0012_form_108.py` (an `AlterField` of the whole choices list, depending on `0011_form_101a`);
  - `backend/apps/forms/tests/test_form_108_schema.py`, `test_form_108_generator.py`, `test_form_108_prints.py` (synthetic tier 3);
  - `backend/apps/forms/tests/test_explain_split.py`.
- Modify:
  - `backend/apps/intake/claim_rows.py`: `CLAIM_LISTS` `:21-29` (+ `"leases"`), `DebtRow` `:47-53` and `ContractRow` `:63-66` (4e-R22), `ClaimRows` `:77-85` (+ `leases`), `_read` `:165-194` (joins the record and `exempt_states`), the docstring `:198` ("eight lists");
  - `backend/apps/forms/services/fill_resolver.py`: `CLAIM_CELLS` `:353-411` (the new `secured` cells and `leases`), `binding_fix` `:598-640` (4e-R10), and the `intentions.` lines `:466`, `:604`;
  - `backend/apps/forms/services/answer_records.py:4,13,20,235-236` (4e-R1);
  - `backend/apps/forms/schema.py`: `_BINDING_NAMESPACES` `:278-290`, `_LIST_BINDING` `:837-841`, the message `:926-930`;
  - `backend/apps/forms/registry.py`: `_form_108_applies` beside `_supp_applies` (`:277-284`), and the entry between `:305` and `:306`;
  - `backend/apps/forms/models.py:16-36`;
  - `data/forms/field_index/audit/step2_verification.json` (through the tool; 1660 → 1707 rows, Form 108's run placed after `form_101a`'s and before `list_of_creditors`', as 101A's tool places its own);
  - `backend/apps/forms/tests/test_oracle_tier2.py:37` (1888 → 1935);
  - `test_oracle_tier1.py` (`claims_session` `:430-465`: `complete_contract(session, lease_kind="vehicle", description=…)`, so `contracts` and `leases` hold one row each, the List of Creditors stays at 4 entries `:479`, and the unpack `:488` holds; `SC` §1);
  - `test_oracle_tier3.py` (`EXPECTED` gains a `form_108` block for James `:462`, Priya `:650`, DeShawn `:1036` and Andrés `:1391`, with every choice box blank, since no seed intention exists until Task 8, and the exempt box `/yes`; packet sizes `:1849`, `:1911`, `:1927`, `:1944` 16 → 17);
  - `test_claims_bindings.py:108-122` (`expected["leases"] = 0` on its two residential leases; every new `secured` cell returns `""` with no record);
  - `test_registry.py:101-122` (the order list), `test_signing_lines.py:29-50,75`, `test_checks.py:958,1252-1262`, `test_answer_records.py:2,20,113,199-205,215,221-228`;
  - `test_rule_fixes.py:124`: `targets["step"]` becomes `_wizard_steps() | set(NEW_STEP_KEYS)`, the allowance `test_answer_records.py:222` already makes for 4a's reserved keys (S:238: a fix may name a reserved step before its PR adds it). Without it, `Explain1 1x`'s and `Explain2 1x`'s `{"step": "plans"}` fails this test until Task 7 (the test collects `fix_for` of text and choice fields only, `:132-139`, so the checkbox `check1` is not among them). Task 7 takes `"plans"` out of `NEW_STEP_KEYS`, so the pin tightens again by itself;
  - `backend/apps/intake/tests/test_seed_demo_data.py`: `PACKET_SIZE` `:133` (deshawn 16, andres 16, james 16, priya 17, maria 16, sarah 16), `:356` (15 → 16), and `:873` renamed `test_no_persona_gets_the_supp`, with its comment `:874-876` reworded to "Form 108 joins four packets; the Supp joins none";
  - `backend/apps/forms/services/sheets.py:66` and `backend/apps/forms/tests/test_printed_page.py:936` ("19" → "20");
  - `backend/apps/forms/tests/test_box_background.py:23-41`: `FORMS_WITH_WORDS_UNDER_THE_DISTRICT` gains `"form_108"` after `"form_107"`. Form 108's `Bankruptcy District Information` has `/MK /BG [1]` over a printed district line, so it is a 19th district box, and the court-name-prints-clean pixel test must cover it;
  - `frontend/src/types/api.ts:1124-1144` (`FormType` + `'form_108'`, the comment "All 20 form types"), `:1160-1260` (`FORM_TYPE_METADATA`, 4e-R14);
  - `frontend/src/test/mocks/handlers.ts` (`mockPacket`), `frontend/src/pages/__tests__/FormDashboard.test.tsx`;
  - `frontend/src/pages/FormDashboard.tsx:465-471` (4e-R13) and its comment `:463-464`;
  - `frontend/e2e/pages/dashboard.page.ts:10-14` (the comment);
  - the eight journeys' `generateAllForms(n)`: `andres-gig-driver.spec.ts` 15 → 16, `deshawn-assets.spec.ts` 15 → 16, `james-borderline.spec.ts` 15 → 16, `priya-ineligible.spec.ts` 16 → 17, `eviction-statement-journey.spec.ts` 16 → 17 (it spreads `JAMES`), `sofa-journey.spec.ts` 15 → 16, with `maria-happy-path.spec.ts` and `sarah-simplest.spec.ts` staying 16 (their comments unchanged).

**Interfaces:**
- Consumes Task 2's record, `is_form_108_lease`, `exempt_states` and `EXEMPT_BOX`, and Task 3's index.
- Produces:
  - `split_explain(text: str) -> tuple[str, str]` (4e-R5);
  - `ClaimRows.leases: tuple[ContractRow, ...]`, and on the rows `DebtRow.intention`, `.explain`, `.exempt` and `ContractRow.assumed`;
  - the `CLAIM_CELLS` entries:
    - `secured.intention` (`row.intention`, the printed choice of 4e-R22: the stored value when in `FORM_INTENTIONS`, `""` for `retain_explain` with blank words, R-BLANK-EXPLAIN, else `""`);
    - `secured.exempt` (`row.exempt`);
    - `secured.explain` (`row.explain` while `row.intention == "retain_explain"`, else `""`);
    - `secured.explain_1` and `secured.explain_2` (`split_explain` of `explain`);
    - `leases.name` (`_address_cell("name")`), `leases.purpose`, and `leases.assumed` (`yes`/`no`, else `""`);
  - `_form_108_applies(session) -> bool`: `rows = claim_rows(session); return bool(rows.secured or rows.leases)`, never raising;
  - registry `"form_108": PacketForm(_form_108_applies, _nothing)`;
  - `form_108.limits.json`, `{"boxes": {"<form>:<binding>": cap, …, "form_108:explain": cap}, "labels": {creditor_name, collateral_description, counterparty_name, description, explain}}`. The caps are 4e-R4's eleven boxes, measured by the tool on the named boxes at 6 pt: single-line boxes by the 101A formula, and multi-line boxes (the property and lease descriptions) by half the lines' worth, the venue rule. Each slot of a column is measured and the narrowest kept. `labels` holds the five approved labels (E7's four and E8's `explain`, "the explanation of your plan"). JSON holds no comments, so each label's `# DRAFT: counsel C-37` mark sits above it in `build_form_108.py`, which writes the JSON;
  - the schema's 47 bindings:

    | Fields | Binding | Choices |
    |---|---|---|
    | `Debtor 1` (untagged, both pages) | rule `full_name` | — |
    | `Bankruptcy District Information` | rule `district_name` | — |
    | `Creditors Name 1x` (x = a–d) | `claims.secured[].name` | — |
    | `PropertyDescription 1x` | `claims.secured[].property` | — |
    | `check1 1x` | `claims.secured[].intention` | `{surrender: "/surrender", retain_redeem: "/retain and redeem", retain_reaffirm: "/retain and reaffirmation", retain_explain: "/retain and explain"}` |
    | `check2 1x` | `claims.secured[].exempt` | `{no: "/no", yes: "/yes"}` |
    | `Explain1 1x` / `Explain2 1x` | `claims.secured[].explain_1` / `explain_2` | — |
    | `Lessors Name 2x` (x = a–g) | `claims.leases[].name` | — |
    | `PropertyDescription 2x` | `claims.leases[].purpose` | — |
    | `check2x` | `claims.leases[].assumed` | `{no: "/no", yes: "/yes"}` |

    Each `claims.` binding is `source: "asked"`, `legal_review: false`, with `repeat` `f108_part_1` (capacity 4, rows 1–4) or `f108_part_2` (capacity 7, rows 1–7). The groups are 4e-R9's. Unbound: `Debtor 2`, `Case number`, `Check if this is an`, both signatures, both dates. The builder confirms each choice state against the index (PyMuPDF prints `retain#20and#20redeem`, pypdf `/retain and redeem`).

- [ ] **Step 1: Write the failing tests.**
  - `test_explain_split.py`:
    - `test_the_split_keeps_every_word_and_breaks_only_at_a_space`: `" ".join(part for part in split_explain(t) if part) == t` over 20 synthetic texts;
    - `test_explain_1_holds_the_longest_run_of_words_that_fits_at_6_pt`: the next word would not fit (`_fits_explain_1` false on one more word);
    - `test_a_first_word_too_wide_for_explain_1_leaves_it_blank`;
    - `test_an_empty_text_splits_into_two_blanks`.
  - `test_form_108_schema.py`:
    - `test_every_binding_is_asked_and_never_legal_review`;
    - `test_the_header_name_fills_both_pages`;
    - `test_the_seven_signing_and_case_boxes_stay_unbound`;
    - `test_each_choice_maps_to_its_own_box_state`;
    - `test_the_sheet_groups_print_every_slot_column`.
  - `test_form_108_generator.py`: the `test_form_122a1_supp_generator.py` pattern (`:31-60`): the schema's parsed and byte equality with the tool's output, the 47 owned addendum rows equal to the tool's, and their placement; `form_108.limits.json` equals the tool's.
  - `test_form_108_prints.py` (synthetic sessions, drawn with `fill()` and read with `read_drawn`):
    - `test_every_intention_answer_ticks_its_one_box_and_open_ticks_none`: four values tick one widget each (`retain_explain` with words); absent, `undecided` and `retain_explain` with words `"   "` tick none of `check1 1a`'s four, and the blank-words row prints no Explain words and a blank intention cell on the Part 1 sheet (R-BLANK-EXPLAIN);
    - `test_every_assumed_answer_ticks_its_box_and_open_ticks_none`: `yes`, `no`, `undecided`, absent;
    - `test_the_exempt_box_follows_schedule_c_and_never_absence`: `listed` `/yes`, `not_claiming` `/no` (with and without a link), and `later`, `not_named` and `no_property` blank;
    - `test_explain_prints_only_under_retain_explain_and_reads_back_whole`: the readback assigns each letter by its centre (the two boxes overlap by 50.5 × 2.7 pt, `SF` §1). The non-blank halves joined by one space equal the text, and under `retain_reaffirm` with stored words both are blank;
    - `test_a_choice_stays_with_its_creditor_when_an_earlier_row_is_added_or_removed`: three secured debts, the middle one chosen; add a debt sorting first, then delete one; the choice prints beside its own creditor each time;
    - `test_a_fifth_secured_debt_and_an_eighth_lease_print_on_the_sheets`: row "1.5" on Part 1's sheet with the choice in the form's words and the whole explanation, row "2.8" on Part 2's (S:785);
    - `test_a_null_kind_lease_is_in_part_2_and_a_residential_one_is_not` (R-LEASE-GATE: the session is built through the API, which stores a null kind);
    - `test_form_108_applies_to_a_secured_debt_or_an_in_scope_lease_only` (`applies` on: none, a draft only, an unsecured debt only, a residential lease only → False; a confirmed secured debt, a vehicle lease → True).
  - `test_registry.py`: `form_108` between `form_107` and `form_121`.
  - `test_signing_lines.py`:
    - `SIGNING_LINES["form_108"] = ["Signature of Debtor 1", "Signature of Debtor 2", "Date signed Debtor 1", "Date signed Debtor 2"]`;
    - `STILL_PRINTS["form_108"] = {"Debtor 1": "Priya Sharma", "Creditors Name 1a": "Kestrel Auto Finance"}`.
  - `test_checks.py`:
    - `test_an_intentions_binding_is_refused_as_an_unknown_namespace` (replacing `:958`'s placeholder);
    - `test_a_claims_list_may_be_a_sheet_column` (a synthetic schema with a `claims.secured[].name` column passes E007);
    - the message pin at `:1252-1262` reworded.
  - `test_answer_records.py`: the `intentions.` cases are deleted (4e-R1); `:113`'s step table loses its `intentions.secured` row.
  - `test_oracle_tier2.py`: `ASSERTED_CASES = 1935`, with the comment "+47 (4e): Form 108's header 2, Part 1 4 × 6 = 24, Part 2 7 × 3 = 21".
  - The frontend: `FormDashboard.test.tsx` `sends a refused Form 108 card's Answer Questions to Your Plans` (it asserts the href `/intake?step=plans`; the step itself lands in Task 7).
- [ ] **Step 2: Run them.** `pt.sh apps/forms/tests/test_explain_split.py apps/forms/tests/test_form_108_schema.py apps/forms/tests/test_form_108_generator.py apps/forms/tests/test_form_108_prints.py apps/forms/tests/test_registry.py --ds=config.settings.test -q`. Expected: fail (no tool, schema or cells).
- [ ] **Step 3: Implement**, in this order inside the one commit:
  1. `explain_split.py`;
  2. `claim_rows`' fields, list and join;
  3. the cells and `binding_fix`;
  4. `_LIST_BINDING` and the namespace removal;
  5. the tool, then run `py.sh <repo>/data/forms/field_index/tools/build_form_108.py` to write the schema, the limits and the addendum rows;
  6. `FORM_TYPE_CHOICES` and `0012`;
  7. the registry entry, the pins, the frontend type, metadata, `mockPacket` and dashboard path, and the E2E counts.
  `explain_split.py` imports `pdf_filler`, `widgets` and `text_fit` inside `_fits_explain_1` only (4e-R5): `pdf_filler.py:57` imports `fill_resolver`, which imports `split_explain` for `CLAIM_CELLS`, so a module-level import is a certain cycle, not a possible one (the `exemption_items` precedent, `fill_resolver.py:529`).
- [ ] **Step 4: Run the blast radius.**
  - Backend: `apps/forms/tests/` whole (`test_oracle_tier1.py`, `test_oracle_tier2.py`, `test_oracle_tier3.py`, `test_checks.py`, `test_claims_bindings.py`, `test_api_readback.py` (its `form_types == packet(seeded)` holds both sides), `test_signing_lines.py`, the seven byte-compare generator tests), plus `apps/intake/tests/test_seed_demo_data.py`, `check`, `makemigrations --check --dry-run`, `ruff check` on every touched file, and `ruff format --check` on the new files.
  - Frontend: `fe.sh npx vitest run --maxWorkers=2 src/pages/__tests__/FormDashboard.test.tsx src/test/`, tsc, eslint and prettier.
  - Record the counts. Tier 2's run count must equal 1935 (re-pinned from the run, never hand-added).
  - E2E: `e2e-one.sh all 4e-t4`. Expected: nine green (DIG-523 reported if it shows). Every packet with a secured debt or an in-scope lease gains Form 108, and Generate passes with blank choices, since `requires` is `_nothing`.
  - See-it-fail:
    - make `secured.intention` return the stored value unfiltered, and show `test_every_intention_answer_…[undecided]` raise `UnmappedChoice`;
    - drop the blank-words test from `_read`'s printed choice, and show `test_every_intention_answer_…[retain_explain-blank-words]` tick `/retain and explain`;
    - join by position instead of id, and show `test_a_choice_stays_with_its_creditor_…` fail.
- [ ] **Step 5: Commit** `forms: Form 108, its schema and 47 placements, printed from the claims rows joined to IntentionAnswers by id` with the paths above.

### Task 5: The step 9 gaps and the E4 too-long details, in Complete's list

**Files:**
- Create:
  - `backend/apps/intake/intentions.py`;
  - `backend/apps/forms/services/intention_fit.py` (the `petition_fit.py` pattern, `:1-155`);
  - `backend/apps/intake/tests/test_intention_gaps.py`;
  - `backend/apps/intake/tests/test_intention_frontend_copy.py`;
  - `frontend/src/components/wizard/steps/plans/intentionGapCases.json` and `claimTextRowCases.json` (case files run by both sides, as `linkedPaymentCases.json` is). `claimTextRowCases.json` also holds the lease-scope cases (a contract's `lease_kind` → in or out of Form 108's lease list: `vehicle`, `other_personal_property`, `other` and null in; `residential` out), which `planRows.test.ts` and the server both run.
- Modify:
  - `backend/apps/intake/completion.py:123-140` (4e-R11; and its docstring, `:57-60`);
  - `backend/apps/intake/tests/test_completion.py:497` (`test_complete_lists_every_gap_in_wizard_order` gains the `plans` block between Codebtors' gaps and the claims tail, and the `debts` and `contracts` too-long details at their splice points);
  - `frontend/src/constants/copy.ts` (the five gap sentences only; the step's own words are Task 6's), `frontend/src/components/forms/__tests__/GapsNotice.test.tsx`.

**Interfaces:**
- Consumes Task 2's record, Task 4's `claim_rows`, `split_explain` and `form_108.limits.json`, and `schedule_i.DETAIL_TOO_LONG` (`schedule_i.py:35`).
- Produces, in `apps.intake.intentions` (it imports `Gap` inside its functions, as `schedule_i.py` does):
  - the sentences `INTENTION_GAP_NONE`, `INTENTION_GAP_UNDECIDED`, `INTENTION_GAP_EXPLAIN`, `LEASE_GAP_NONE`, `LEASE_GAP_UNDECIDED` (approved words, `# DRAFT: counsel C-37`);
  - `CLAIM_TEXT_KEYS = ("creditor_name", "collateral_description", "counterparty_name", "description", "explain")`;
  - `CLAIM_BOX_CAPS` and `CLAIM_TEXT_LABELS` (the five labels, `explain`'s included), read from `form_108.limits.json` at import. A missing file, a box of 4e-R4's table missing from `boxes`, or a `CLAIM_TEXT_KEYS` key with no label raises `ImproperlyConfigured` (the `_read_schedule_i_limits` precedent, `models.py:1141-1159`);
  - `ROW_BOXES: dict[tuple[str, str], tuple[str, ...]]`, `(text, list)` → the box keys of 4e-R4's table, and `row_cap(text: str, list_name: str) -> tuple[int, tuple[str, ...]]` (the smallest cap and the forms holding it);
  - `FORM_WORDS = {"form_108": "Form 108", "schedule_d": "Schedule D", "schedule_e_f": "Schedule E/F", "schedule_g": "Schedule G"}`;
  - `intention_row_gap(name: str, entry: Mapping) -> str | None` and `lease_row_gap(name: str, entry: Mapping) -> str | None` (pure; the case file pins them). Each reads the stored entry, never `DebtRow.intention`, so `retain_explain` with blank words is `INTENTION_GAP_EXPLAIN` (R-BLANK-EXPLAIN, 4e-R22);
  - `intention_step_gaps(session) -> list[Gap]` (step `plans`, `DETAIL`, `forms=("form_108",)`);
  - `claim_text_gaps(session) -> list[Gap]` (steps `debts`, `contracts` and `plans`; `DETAIL`; `forms` per 4e-R4). The `plans` detail is the explanation's, measured only under a stored `retain_explain` (4e-R16).
- Produces, in `apps.forms.services.intention_fit`, `too_long_texts(session, texts: Collection[str]) -> dict[tuple[str, int, str], frozenset[str]]`, keyed `(kind, pk, text)` with `kind` ∈ `{"debt", "lease"}`, to the refusing form types (4e-R4). It measures only the boxes of each row's own list, and Form 108 only while `_form_108_applies`. It counts only `ValueTooLong`: an `UnprintableLetter` from `check()` is no refusal here (4e-R4). `claim_text_gaps` calls it with all five `CLAIM_TEXT_KEYS`.
- Produces the browser constants in `copy.ts`: the five gap sentences, each under `// DRAFT: counsel C-37` (the step's own status region uses them in Task 6, through `openPlanRows`; Review shows the server's copy, R-REVIEW-ONCE).

- [ ] **Step 1: Write the failing tests.**
  - `test_intention_gaps.py`:
    - `test_each_open_row_is_one_detail_in_form_108s_order`: two secured debts (one absent, one `undecided`) and one lease (absent) → three details, step `plans`, in Schedule D then Part 2 order, `forms == ("form_108",)`;
    - `test_retain_explain_with_blank_words_asks_for_them` (`"   "` counts as blank; the gap is `INTENTION_GAP_EXPLAIN`, never `INTENTION_GAP_NONE`, and `intentionGapCases.json` holds the same case);
    - `test_a_chosen_row_has_no_gap`;
    - `test_a_nameless_row_is_called_one_amount_owed_or_one_contract`;
    - `test_too_long_and_open_choices_never_hold_complete`: a session with every kind of new detail completes (`POST complete/` → 200), and every new gap's `kind` is `"detail"`;
    - `test_every_text_generate_refuses_as_too_long_is_listed`, parametrized:
      - a secured creditor's name that fits Form 108 but not Schedule D → a `debts` detail naming "Schedule D" (the same name, `PDFFormFiller().check("schedule_d", …)`, raises `ValueTooLong`);
      - a fifth secured row's collateral, measured on Form 108's sheet;
      - a lease description too long for Form 108's two-line box → a `contracts` detail naming "Form 108";
    - `test_a_text_over_its_cap_is_listed_with_the_caps_form` (a name of narrow letters over the cap, which `check()` takes);
    - `test_a_text_that_fits_everywhere_is_not_listed`;
    - `test_a_letter_the_form_cant_print_is_not_called_too_long` (a creditor's name within every cap holding a letter the template can't print raises no too-long detail; `check()` raises `UnprintableLetter`, which `too_long_texts` doesn't count);
    - the explanation (R-EXPLAIN), moved here from Task 6 now that E8 approved its label:
      - `test_an_explanation_whose_break_overflows_explain_2_is_listed` (under the cap; a `plans` detail naming "Form 108"; `check("form_108", …)` on the split pair raises `ValueTooLong`);
      - `test_a_fifth_rows_explanation_is_measured_on_the_sheet`;
      - `test_an_explanation_over_its_cap_that_fits_is_listed_by_length`;
      - `test_words_kept_under_another_choice_are_never_measured` (4e-R16);
    - `test_an_unsecured_creditors_long_name_never_names_schedule_d_or_form_108` (it names only "Schedule E/F", by length and by measure);
    - `test_a_residential_lease_description_is_measured_on_schedule_g_only` (one over Form 108's cap but within G's raises no detail);
    - `test_each_rows_cap_is_the_smallest_of_its_own_lists_boxes` (`row_cap` over every `(text, list)` of `ROW_BOXES`, against `form_108.limits.json`), and `test_the_row_list_cases_are_what_the_server_says` (the shared case file `claimTextRowCases.json`: a row's fields → its list, and a contract's `lease_kind` → in or out of the lease list, the latter routed through `is_form_108_lease`, so the server side of 4e-R23's pin is this test);
    - `test_the_gaps_endpoint_lists_them_and_writes_nothing` (the S:786 capture pattern).
  - `test_intention_frontend_copy.py`:
    - `test_the_gap_sentences_are_the_browsers` (`copy.ts`, `_server_sentences` as in `test_schedule_i_frontend_copy.py`);
    - `test_the_choice_words_are_the_browsers` (the `Intention`, `Assumed` and `ExemptState` literals in `types/api.ts` equal `IntentionAnswers.INTENTIONS`, `ASSUMED` and the five `EXEMPT_*`);
    - `test_the_case_file_is_what_the_server_says` (runs `intentionGapCases.json` through the two pure helpers);
    - `test_the_too_long_sentence_is_the_schedule_i_one` (`intentions` reuses `schedule_i.DETAIL_TOO_LONG`, one string).
  - `GapsNotice.test.tsx`: `GapsNotice leaves the claims too-long details out of the blank count`. With one `debts` too-long detail ("Your answer for the creditor's name is too long for its box on Schedule D.") and one open-choice detail, the blank line says one answer, since `patternOf(SCHEDULE_I_DETAIL_TOO_LONG)` (`TOO_LONG_SENTENCES`, `GapsNotice.tsx:55-60`) already matches the reused sentence. It passes at once, so it is a guard with a see-it-fail (Step 4).
  - `test_completion.py:497`: the new blocks in their places (4e-R11).
- [ ] **Step 2: Run them.** `pt.sh apps/intake/tests/test_intention_gaps.py apps/intake/tests/test_intention_frontend_copy.py apps/intake/tests/test_completion.py --ds=config.settings.test -q` and `fe.sh npx vitest run --maxWorkers=2 src/components/forms/__tests__/GapsNotice.test.tsx`. Expected: the backend tests fail (`ImportError`, missing blocks); the GapsNotice test passes at once (a guard).
- [ ] **Step 3: Implement** `intention_fit.py`, `intentions.py`, the two case files, the splice and the `copy.ts` sentences.
- [ ] **Step 4: Run** Step 2's commands, `apps/intake/tests/` whole (the gap pins and the completion tests), `apps/forms/tests/test_rule_fixes.py`, `check`, `ruff check` on every touched file, and `ruff format --check` on the new files.
  - See-it-fail:
    - wrap the new gaps as `GATE` in `completion_gaps`, and show `test_too_long_and_open_choices_never_hold_complete` fail;
    - measure creditor names on Form 108 only, and show `test_every_text_generate_refuses_…[schedule-d-name]` fail;
    - take one cap per text instead of per row's list, and show `test_an_unsecured_creditors_long_name_never_names_…` fail;
    - count every `check()` refusal in `too_long_texts`, and show `test_a_letter_the_form_cant_print_is_not_called_too_long` fail;
    - drop `patternOf(SCHEDULE_I_DETAIL_TOO_LONG)` from `TOO_LONG_SENTENCES`, and show the GapsNotice test count two blank answers.
- [ ] **Step 5: Commit** `intake: Form 108's open choices and the too-long names and explanations as details in Complete's list` with the paths above.

### Task 6: The words, the definition panels, the step 9 component and Amounts Owed's and Contracts' box notes

Every word it needs is approved (E7, E8). The component is built and tested here, before the step exists in `WIZARD_STEPS` (Task 7).

**Files:**
- Create:
  - `frontend/src/components/wizard/steps/PlansStep.tsx`;
  - `frontend/src/components/wizard/steps/plans/planRows.ts`: `securedPlanRows`, `leasePlanRows`, `plansBody`, `openPlanRows`, `intentionRowGap`, `leaseRowGap`;
  - `frontend/src/components/wizard/steps/plans/PlansDefinitions.tsx` (the panels, 4e-R7);
  - `frontend/src/components/wizard/steps/plans/index.ts`;
  - `frontend/src/constants/claimTextLimits.ts` (the browser copy of `form_108.limits.json`'s box caps only, with `rowList(row)` and `rowCap(text, row)`, the browser's copy of `ROW_BOXES` and `row_cap`, run against `claimTextRowCases.json`; the labels live in `copy.ts`'s `CLAIM_TEXT_LABELS` alone, the `SCHEDULE_I_TEXT_LABELS` precedent, `copy.ts:1878`);
  - `frontend/src/components/wizard/steps/__tests__/PlansStep.test.tsx`;
  - `frontend/src/components/wizard/steps/plans/__tests__/planRows.test.ts`;
  - `frontend/src/components/wizard/steps/plans/__tests__/claimTextLimits.test.ts` (beside `planRows.test.ts` and the case file it runs; `src/constants/` holds no tests);
  - `frontend/src/test/upl-plans-copy.test.ts`;
  - `backend/apps/forms/tests/test_form_108_frontend_copy.py`.
- Modify:
  - `frontend/src/constants/copy.ts` (every approved `PLANS_*`, `WHAT_DOES_*` and `CLAIM_TEXT_LABELS` name but `PLANS_REVIEW_HEADING`, which is not shipped (R-REVIEW-ONCE), each under `// DRAFT: counsel C-37`);
  - `frontend/src/constants/formText.ts` (`FORM_108_*`, the four statute pairs, and `FORM_REVISIONS.form_108 = '12/15'` at `:871`);
  - `frontend/src/components/wizard/WhatDoesThisMean.tsx:1-29` (`note?`, 4e-R7);
  - `frontend/src/components/wizard/steps/DebtsStep.tsx`: the creditor field `:612-621` and the collateral textarea `:755-765`;
  - `frontend/src/components/wizard/steps/ContractsStep.tsx`: the counterparty field `:198-210` and the description `:243`;
  - their tests, `DebtsStep.test.tsx` and `ContractsStep.test.tsx`;
  - `backend/apps/intake/tests/test_intention_frontend_copy.py` (it gains `test_the_browsers_caps_and_labels_are_the_tools`, below);
  - `backend/apps/intake/tests/test_petition_frontend_copy.py` (the `FORM_REVISIONS` check reads `form_108`).

**Interfaces:**
- Consumes Task 2's types, Task 5's sentences and `form_108.limits.json`.
- Produces:
  - `PlansStep` props: `debts: DebtRow[]`, `contracts: ContractRow[]`, `answers: IntentionAnswers`, `onAnswersChange: (next: IntentionAnswers) => void`, `exempt: Record<string, ExemptState>`, `onGoToStep: (key: string) => void`, `onValidationChange: (valid: boolean) => void` (always `true`: the step has no gate, S:334);
  - `securedPlanRows(debts) -> DebtRow[]` and `leasePlanRows(contracts) -> ContractRow[]` (4e-R2, 4e-R23);
  - `plansBody(answers, secured, leases) -> {secured: Record<string, …>; leases: Record<string, …>} | null` (4e-R3);
  - `openPlanRows(answers, secured, leases) -> string[]` (the gap sentences, in the step's order, read by the step's own status region, 4e-R13);
  - the form words in `formText.ts`, unscored, each under `// DRAFT: counsel C-37`: `FORM_108_TITLE`, `FORM_108_DEADLINE`, `FORM_108_PART_1_HEADING`, `FORM_108_INTENTION_QUESTION`, `FORM_108_INTENTIONS` (record of the four), `FORM_108_EXEMPT_QUESTION`, `FORM_108_CREDITOR_LABEL`, `FORM_108_PROPERTY_LABEL`, `FORM_108_PART_2_HEADING`, `FORM_108_ASSUME_SENTENCE`, `FORM_108_ASSUMED_QUESTION`, `FORM_108_ASSUMED` (`{no: 'No', yes: 'Yes'}`), `FORM_108_LESSOR_LABEL`, `FORM_108_LEASED_PROPERTY_LABEL`;
  - the statute pairs: `STATUTE_521_A_2_A_CITATION` / `STATUTE_521_A_2_A` ("(a) The debtor shall—", "[…]", paragraph (2)'s opening words, (A) whole, "[…]", R-521-LEAD and 4e-R7), `STATUTE_722_CITATION` / `STATUTE_722`, `STATUTE_524_C_CITATION` / `STATUTE_524_C`, `STATUTE_365_P_2_CITATION` / `STATUTE_365_P_2`. Each comment names its URL (`OC` "Form words") and the re-check date.

The step's layout, top to bottom (Part blocks only while they have rows):
1. `PLANS_TITLE` as the step's own `<h3 className="section-title">` under the layout's `h2.step-title`, which shows the `WIZARD_STEPS` label "Your Plans" (`WizardLayout.tsx:166-167`; the `AssetsStep.tsx:181` pattern), then `PLANS_INTRO`, `PLANS_UNDECIDED_INFO`, then `PLANS_DEADLINE_LABEL` beside `FORM_108_DEADLINE` (E6). The Part headings are `h4`.
2. Part 1:
   - `FORM_108_PART_1_HEADING`, `FORM_108_INTENTION_QUESTION` and the four panels, each a `<details>` rendered closed (no `open`);
   - per row, a fieldset legended by the name, with `PLANS_FROM_DEBTS`, the name under `FORM_108_CREDITOR_LABEL`, the property (`FORM_108_PROPERTY_LABEL` and the filer's words), five radios (the four `FORM_108_INTENTIONS` in the form's order, then `PLANS_UNDECIDED`) and `PLANS_EXPLAIN_LABEL`'s box under `retain_explain` with its too-long note. The box has no `placeholder` and no default value, and no `maxLength` below the record's hard ceiling (`TEXT_CEILING`, 500, 4e-R17): the measured cap is a note, never a limit (R-EXPLAIN);
   - stored words under another choice behind `HiddenLine` (4e-R16);
   - `FORM_108_EXEMPT_QUESTION` with the row's one exempt sentence, by `exempt[id]`: `listed` → `PLANS_EXEMPT_LISTED`, `not_claiming` → `PLANS_EXEMPT_NOT_CLAIMING`, `later` → `PLANS_EXEMPT_LATER`, `not_named` → `PLANS_EXEMPT_NOT_NAMED`, `no_property` → `PLANS_EXEMPT_NO_PROPERTY`, nothing for a missing id.
3. Part 2: `FORM_108_PART_2_HEADING`, `FORM_108_ASSUME_SENTENCE`, `FORM_108_ASSUMED_QUESTION` and the assume panel (closed); per row, a fieldset with `PLANS_FROM_CONTRACTS`, the name under `FORM_108_LESSOR_LABEL`, `FORM_108_LEASED_PROPERTY_LABEL` and the filer's words, and three radios: No, Yes, `PLANS_UNDECIDED`.
4. After the Parts, the step's `role="status"` region (S:208, 4e-R13): mounted whenever a Part shows, never an alert, holding `openPlanRows`' sentences in the step's order, and empty when every row is chosen.
5. With neither Part, `PLANS_NOT_APPLICABLE` alone. Its "Amounts Owed" and "Contracts & Leases" are buttons calling `onGoToStep('debts')` and `onGoToStep('contracts')`, by the split-on-phrase pattern (`FormDashboard.tsx:441`).

- [ ] **Step 0: Fetch and pin the statutes.** `curl -sSL` each `https://uscode.house.gov/us/usc/t11/s<n>` (n = 521, 722, 524, 365) into its own empty directory under the job tmp, and extract with `python3 -I` from outside that directory.
  - The provisions: § 521 as R-521-LEAD rules (4e-R7's five lines: "(a) The debtor shall—", "[…]", paragraph (2)'s opening words, (A) whole, ending "…to reaffirm debts secured by such property; and", "[…]"); § 722 whole; § 524(c) from "(c) An agreement between a holder of a claim…" through (6)(B)'s "…a consumer debt secured by real property."; § 365(p)(2) (A)–(C).
  - Verify § 521's served text first: that subsection (a) opens with exactly "(a) The debtor shall—" and that paragraph (2)'s lead-in governs (A). If either differs, stop and report; don't reshape the quote.
  - Paste each word for word, with curly quotes and dashes checked by code point. Record the date in the comment.
  - The served page puts a U+2060 word joiner between "estate" and the em dash (read 2026-11-24). It is the publisher's typesetting mark, not a word of the statute, so it is stripped. Check for one after "shall" too, and strip it the same way.
  - The check against the served page (this step's `python3 -I` read; the vitest pins then hold the literals): for § 722, § 524(c) and § 365(p)(2), the constant equals the served text after U+2060 is removed and nothing else. § 521's constant is no substring of the page, so its pin splits it on the two "[…]" markers: each of the three quoted segments ("(a) The debtor shall—", paragraph (2)'s opening words, (A) whole) is found in the served text after U+2060 is removed, in that order, and the markers sit as literals at their two places. `PlansStep.test.tsx` asserts no constant holds a U+2060.
- [ ] **Step 1: Write the failing tests.**
  - `PlansStep.test.tsx`:
    - `lists each confirmed secured debt and each lease of personal property`, and `leaves out a residential lease, an unsecured debt and a scanned draft`;
    - `shows the four choices in the form's order and "I haven't decided yet." last, none checked`;
    - `asks for the filer's words only under "Retain the property and [explain]:"`;
    - `keeps words typed under another choice behind Show and Delete`;
    - `a too-long explanation shows its note and leaves Continue enabled`;
    - `shows one exempt sentence per row from Schedule C's answers`, parametrized over the five states;
    - `asks "Will the lease be assumed?" as No, Yes, then "I haven't decided yet."`;
    - `shows the form's deadline sentence as the form's words`;
    - `renders each definition once per Part with its own question as its name` (four in Part 1, one in Part 2; distinct accessible names, the retain-and-explain one `WHAT_DOES_EXPLAIN_MEAN`; each closes with `PLANS_EFFECTS_HELP`);
    - `every definition starts closed` (each `<details>` renders without `open`, E2's "collapsed");
    - `the filer's words box starts empty and suggests nothing` (`plans_secured_<i>_explain` has no `placeholder`, no default value, and no `maxLength` below 500);
    - `shows each row's name under the form's own label` (`FORM_108_CREDITOR_LABEL`, `FORM_108_LESSOR_LABEL`);
    - `lists each open row once in a status region and nothing once every row is chosen` (`role="status"`, not `alert`; each `openPlanRows` sentence exactly once);
    - `puts the step's heading under the wizard's` (`PLANS_TITLE` is an `h3`);
    - `with no secured debt or lease, states the basis and links to both steps`;
    - `reports the step valid with every choice open`;
    - `passes axe`.
  - `planRows.test.ts`:
    - `the body is the same built from loaded answers as from the same answers typed`;
    - `the body leaves out empty entries, blank words and ids out of scope`;
    - `the body is null with no row in scope`;
    - `the browser's gaps are the server's` (runs `intentionGapCases.json`);
    - `a lease of personal property is any lease but residential` (runs the lease-scope cases of `claimTextRowCases.json`, which `test_the_row_list_cases_are_what_the_server_says` also runs through `is_form_108_lease`; Task 2's unit `test_a_form_108_lease_is_any_lease_but_residential` keeps its inline values).
  - `DebtsStep.test.tsx` and `ContractsStep.test.tsx`: `a too-long creditor name shows its note and leaves Continue enabled`, `a too-long collateral description shows its note`, and `a too-long lessor name or lease description shows its note`. Each note is `SCHEDULE_I_DETAIL_TOO_LONG` filled with the approved label and `claimTextLimits`' form words. None enters `debtGaps.ts` or `contractGaps.ts` (DIG-542): the test asserts the step's `role="status"` gap region is unchanged.
  - `upl-plans-copy.test.ts`: every new `copy.ts` name is checked against `ADVICE` and carries its C-37 mark, the `upl-petition-copy.test.ts:16-36` pattern.
  - `test_form_108_frontend_copy.py`: each `FORM_108_*` string appears in `form_b108.pdf`'s page text (pages 1–2; the `_page_words` and `_squeezed` helpers of `test_petition_frontend_copy.py:216-218,350`), and `FORM_REVISIONS.form_108` is the page 1 edition mark `12/15`. The `FORM_108_` prefix is owned by this file: a `FORM_108_` name it doesn't list fails.
  - A vitest pin of each `STATUTE_*` constant, literal `toBe`, in `PlansStep.test.tsx` (the `DebtNatureQuestion.test.tsx:589-602` pattern); `STATUTE_521_A_2_A`'s literal is the five lines of 4e-R7, its two "[…]" included.
  - `test_intention_frontend_copy.py` gains `test_the_browsers_caps_and_labels_are_the_tools`: `claimTextLimits.ts`'s caps equal `form_108.limits.json`'s `boxes`, and `copy.ts`'s `CLAIM_TEXT_LABELS` equal its `labels` (the five). `claimTextLimits.test.ts` runs `claimTextRowCases.json` through `rowList`.
- [ ] **Step 2: Run them.** `fe.sh npx vitest run --maxWorkers=2 src/components/wizard/steps/__tests__/PlansStep.test.tsx src/components/wizard/steps/plans/__tests__/planRows.test.ts src/components/wizard/steps/plans/__tests__/claimTextLimits.test.ts src/components/wizard/steps/__tests__/DebtsStep.test.tsx src/components/wizard/steps/__tests__/ContractsStep.test.tsx src/test/upl-plans-copy.test.ts src/test/reading-level.test.ts`, and `pt.sh apps/forms/tests/test_form_108_frontend_copy.py apps/intake/tests/test_intention_frontend_copy.py apps/intake/tests/test_petition_frontend_copy.py --ds=config.settings.test -q`. Expected: fail.
- [ ] **Step 3: Implement** the words, the panels, the component, `planRows.ts`, the box notes and `claimTextLimits.ts`. No backend source changes here (only the three backend copy tests above): the five labels and the explanation's detail landed in Tasks 4 and 5.
- [ ] **Step 4: Run** Step 2's commands, `src/test/accessibility.test.tsx`, `src/test/reading-level.test.ts`, tsc, eslint and prettier.
  - See-it-fail: check `retain_reaffirm` by default, and show `…none checked` fail. Put the creditor note into `debtGaps.ts`, and show `…leaves Continue enabled` fail. Render one panel with `open`, and show `every definition starts closed` fail.
- [ ] **Step 5: Commit** `frontend: Your Plans' words, the statutes under each choice, the step component and the too-long notes on Amounts Owed and Contracts`.

### Task 7: Step 9 in the wizard, the shift from 9 to 10, Review and the journeys

One commit (`SC` §2 (a)): the step table, the constant and its pins, the shift migration, the wizard wiring, Review's test, and every journey's `walkPlans`.

**Files:**
- Create: `backend/apps/intake/migrations/0049_shift_current_step_for_plans.py` (the `0028_shift_current_step.py` pattern, 4e-R12, depending on `0048_intention_answers`).
- Modify:
  - `frontend/src/constants/wizardSteps.ts:5-15` (`{ number: 9, label: 'Your Plans', key: 'plans' }`, Review `number: 10`);
  - `backend/apps/intake/completion.py:14-16` (`WIZARD_STEP_COUNT = 10`, and its comment "…Review, step 10");
  - `backend/apps/forms/services/answer_records.py:25` (`NEW_STEP_KEYS = ("last_few_years_1", "last_few_years_2")`);
  - `backend/apps/intake/tests/test_completion_gaps.py:440-478` (the patch at `:467` moves to 11: accept 11, refuse 12, "from 1 to 11."; the comment no longer says "passes with a literal 9");
  - `backend/apps/intake/tests/test_completion.py:966-969` (`test_moving_between_wizard_steps_after_complete_reopens_it`: `@pytest.mark.parametrize("step", [5, 9])` → `[5, 10]`, so it still moves to the last step, and its comment "Review, the last, is step 9" → "Review, the last, is step 10");
  - `frontend/src/components/wizard/WizardLayout.tsx:125` ("so nine step names fit …") and `frontend/src/components/common/ProgressIndicator.tsx:71` ("nine labelled steps don't fit a phone …"): both comments say ten, once the layout check (§6.0) confirms ten labels fit at the 16px text floor;
  - `backend/apps/intake/tests/test_completion.py:152-155` (`test_wizard_step_must_be_one_of_the_wizard_steps`' refused value `10` → `11`, its id `"11"`; its fixture's `current_step` 9 stays, a stored value);
  - `backend/apps/forms/tests/test_answer_records.py:221-223`;
  - `backend/apps/intake/tests/test_data_migrations.py:33` (`PLANS_SHIFT = [("intake", "0049_shift_current_step_for_plans")]`), plus a run beside `_run_the_shift` (`:567-621`), with the sqlite and `postgres` twins;
  - `frontend/src/pages/IntakeWizard.tsx`:
    - `useState`s beside `:404`;
    - the hydrate in the session-read effect;
    - `currentStepBody` `case 'plans'` after `case 'codebtors'` (`:765`) and its `useMemo` dependencies;
    - after `await updateCurrentStep(nextStep)` (`:864`), when `nextStep === 7`, clear `is_draft` on `debtsData` (4e-R2);
    - `renderStepContent` `case 'plans'` before `case 'review'` (`:1319`);
  - `frontend/src/utils/claimRows.ts:123-135`: `sentDebt` deletes `is_draft` beside `_securedPressed` (4e-R2), so the clear leaves step 6's body unchanged;
  - `frontend/src/components/wizard/steps/__tests__/ReviewStep.test.tsx`: `:298-302`'s "a step the wizard doesn't know" fixture names `'last_few_years_1'` (still reserved after this task) instead of `'plans'`, which is now a real step. `ReviewStep.tsx` itself is not edited (4e-R13, R-REVIEW-ONCE);
  - `frontend/src/pages/__tests__/IntakeWizard.test.tsx`, every site that reaches or starts on Review:
    - `sessionAtStep9` `:85-89` → `sessionOnReview` at `current_step: 10`, on all 16 lines that name it (the definition and `:267`, `:270`, `:273`, `:426`, `:438`, `:526`, `:565`, `:603`, `:776`, `:1230`, `:1253`, `:1276`, `:1307`, `:1311`, `:6345`), and the `:264` comment "step 9 (Review & Results …)" → step 10;
    - `:587-593` and `:637-641` are Continue-from-Codebtors tests: Continue from Codebtors lands on Your Plans and sends `{current_step: 9}`; one more Continue reaches Review and sends `{current_step: 10}`, where their Review assertions stay (`:593` becomes `[{ current_step: 9 }, { current_step: 10 }]`);
    - the loops at `:550` and `:2615` (`['Contracts & Leases', 'Codebtors', 'Review & Results']`) and at `:5388` gain `'Your Plans'` before `'Review & Results'`;
    - the Go Back walk from Review at `:884-893` starts with `'Your Plans'`, before `'Codebtors'`;
    - the Go Back walk at `:2629-2633` (after the `:2615` loop and Complete, `for (const step of ['Codebtors', 'Contracts & Leases', 'Amounts Owed'])`): its first Go Back from Review now lands on Your Plans, so it starts with `'Your Plans'`, before `'Codebtors'`;
    - the `it.each` row at `:5154-5161` (step 8, Codebtors): its next title `'Review & Results'` → `'Your Plans'`;
    - the codebtors save test that presses Continue on Codebtors (`:5245-5263`): its `expectStep('Review & Results')` at `:5263` → `'Your Plans'`;
    - `serveFiler(9, …)` at `:5289` (a filer who resumes on Review) → `serveFiler(10, …)`;
  - `frontend/src/pages/__tests__/FormDashboard.test.tsx:69` (`current_step: 10`, cosmetic);
  - `frontend/e2e/pages/wizard.page.ts`: `walkPlans` after `walkCodebtors` (`:723-750`); the section header at `:752` "Step 10: Review";
  - `frontend/e2e/fixtures/personas.ts`: `PersonaIntention` and `PersonaLeasePlan` beside `PersonaContract` (`:197`); `plans` on `PersonaData` (`:331`) and on each persona:
    - James `{secured: [{creditor: 'Crestway Auto Credit', intention: 'retain_reaffirm'}], leases: []}`;
    - Priya `[{creditor: 'Kestrel Auto Finance', intention: 'retain_redeem'}]`;
    - DeShawn `[{creditor: 'Harrowgate Home Loans', intention: 'retain_explain', explain: 'I am current on the mortgage and will keep paying as agreed'}]`;
    - Andrés `{secured: [{creditor: 'Copperline Auto Finance', intention: 'retain_explain', explain: 'My brother Mateo, the co-owner, keeps paying the loan.'}], leases: [{lessor: 'Northlight Auto Leasing', assumed: 'yes'}]}`;
    - Maria and Sarah `{secured: [], leases: []}`;
  - the eight journeys (`andres-gig-driver.spec.ts:73-76`, `deshawn-assets.spec.ts:72-75`, `eviction-statement-journey.spec.ts:93-95`, `james-borderline.spec.ts:69-72`, `maria-happy-path.spec.ts:74-77`, `priya-ineligible.spec.ts:82-84`, `sarah-simplest.spec.ts:71-74`, `sofa-journey.spec.ts:86-89`): `await wizard.walkPlans(PERSONA)` between `walkCodebtors` and `fillReview`, and their "Step 9" comments → "Step 10". `scanned-bill-journey` stops at step 7 and is untouched;
  - `docs/testing/persona-briefs/{andres-kettleby,deshawn-mitchell,james-washington,priya-sharma}.md`: the step 9 line (the choice, in the form's words) and 4e-R18's sentence; `maria-torres.md` and `sarah-chen.md`: "Your Plans: Form 108 doesn't apply".

**Interfaces:**
- Consumes Tasks 2, 5 and 6.
- Produces:
  - the step 9 body, exactly (4e-R3): `const body = plansBody(intentionAnswers, securedPlanRows(debtsData), leasePlanRows(contractsData)); return body === null ? null : {intention_answers: body};`, so no `{intention_answers: null}` ever goes out;
  - `walkPlans(persona: Pick<PersonaData, 'plans'>)` (4e-R8).

- [ ] **Step 1: Write the tests.**
  - `test_completion_gaps.py`: `test_wizard_step_count_is_the_browsers` (it counts `key:` entries, so it reads 10 by itself) and the moved patch (`:463-478`: accept 11, refuse 12). S:793's bound for 4e (1 to 10, 11 refused) is covered by this patch and by `test_completion.py:152`'s refused 11, so no new `update_step` test is added (no `test_update_step.py` exists).
  - `test_data_migrations.py`: `test_a_session_on_review_before_4e_opens_on_review_after` (forward: `(1, 7, 8, 9, 0, 12)` → `(1, 7, 8, 10, 0, 12)`; reverse: 10 → 9, 9 stays 9), sqlite and `postgres`.
  - `IntakeWizard.test.tsx`:
    - `a visit to Your Plans sends nothing`;
    - `choosing a plan saves it by the debt's id`;
    - `a scanned secured debt confirmed on Amounts Owed gets a row on Your Plans` (a draft row, Continue on step 6 resolves `update_step` 7, then step 9 shows the row);
    - `Go Back to Amounts Owed after confirming a draft sends nothing` (confirm a draft on step 6, Continue, then Go Back: no PATCH, since `sentDebt` drops `is_draft`);
    - `a draft never confirmed gets no row` (`?step=plans` on a session holding a secured draft);
    - `with no secured debt or lease, Continue sends nothing` (no PATCH at all);
    - `Go Back from Review lands on Your Plans and Continue sends 10`;
    - `a refusal naming plans opens Your Plans`.
  - `ReviewStep.test.tsx`: `shows each open Form 108 choice once, with a link to Your Plans` (gaps holding two `plans` details: each sentence appears exactly once, one "Go to Your Plans" button per gap, as every gap gets today, and no `PLANS_REVIEW_HEADING`).
- [ ] **Step 2: Run them.** `pt.sh apps/intake/tests/test_completion_gaps.py apps/intake/tests/test_completion.py apps/intake/tests/test_data_migrations.py apps/forms/tests/test_answer_records.py --ds=config.settings.test -q`, `ppt.sh apps/intake/tests/test_data_migrations.py -m postgres -q`, and `fe.sh npx vitest run --maxWorkers=2 src/pages/__tests__/IntakeWizard.test.tsx src/components/wizard/steps/__tests__/ReviewStep.test.tsx`.
  - Expected to fail first: `test_a_session_on_review_before_4e_opens_on_review_after` (no `0049`), the new `IntakeWizard.test.tsx` cases and the moved walks (no step 9), and the ReviewStep case (no "Go to Your Plans" while `plans` isn't in `WIZARD_STEPS`).
  - Pass before and after, guarding the pair: `test_wizard_step_count_is_the_browsers` (it compares the constant with the browser's count), the moved monkeypatch (it sets the bound itself) and `test_completion.py:152`'s refused 11.
- [ ] **Step 3: Implement** the step table, the constant, `NEW_STEP_KEYS`, `0049`, the wiring, `sentDebt`, the page object, the personas, the journeys and the briefs.
  - `global.css:173-183`: check the ten labels at 1280 px and at 1024 px. Change the CSS only if a label wraps or overflows (S:237). Record what was seen.
- [ ] **Step 4: Run** Step 2's commands, `src/test/accessibility.test.tsx`, `apps/forms/tests/test_rule_fixes.py` (its `_wizard_steps()` reads the file), `apps/intake/tests/` whole, `check`, `makemigrations --check --dry-run`, tsc, eslint and prettier, then `e2e-one.sh all 4e-t7`. Expected: nine green (DIG-523 reported if it shows).
  - See-it-fail: drop the `is_draft` clear, and show `a scanned secured debt confirmed …` fail. Keep `is_draft` in `sentDebt`, and show `Go Back to Amounts Owed after confirming a draft sends nothing` fail. Build the body from every `debtsData` row, and show `a visit to Your Plans sends nothing` fail. Leave `WIZARD_STEP_COUNT = 9` with the 10-step table, and show `test_wizard_step_count_is_the_browsers` fail.
- [ ] **Step 5: Commit** `wizard: Your Plans is step 9, Review moves to 10, and every journey walks it` with the paths above.

### Task 8: The personas' choices in the seed and the API readback

One commit (`SC` §2 (d)): either half alone turns `test_api_readback` red.

**Files:**
- Modify:
  - `backend/apps/intake/management/commands/seed_demo_data.py`: `_intentions(secured: list[tuple[str, str, str | None]], leases: list[tuple[str, str]]) -> dict` beside `_schedule_i` (`:213`); each persona's data; the write in `_create_persona` (`:1688+`), after the debts and contracts exist, resolving each row by creditor or counterparty name (the `asset_at` precedent, `:156`), never by pk;
  - `backend/apps/forms/tests/test_api_readback.py`: a `PATCH {intention_answers: …}` after the codebtors PUT (`:176-183`) and the `petition_answers` PATCH (`:187`), before `complete/` (`:192`). Ids are resolved from the API session's own rows by name (the `claim_links(session, [("debt", name)])` precedent, `:238`). A PATCH after Complete would reopen the intake;
  - `backend/apps/intake/tests/test_seed_demo_data.py`: `test_each_persona_makes_the_owners_form_108_choice` and `test_no_personas_explanation_is_too_long`;
  - `backend/apps/forms/tests/test_oracle_tier3.py`: the four `form_108` blocks gain their ticks.

**Interfaces:**
- Consumes Task 2's record and Task 4's prints.
- Produces each persona's `IntentionAnswers` (E5):
  - James `{"secured": {<Crestway>: {"intention": "retain_reaffirm"}}}`;
  - Priya `{<Kestrel>: {"intention": "retain_redeem"}}`;
  - DeShawn `{<Harrowgate>: {"intention": "retain_explain", "explain": "I am current on the mortgage and will keep paying as agreed"}}`;
  - Andrés `{"secured": {<Copperline>: {"intention": "retain_explain", "explain": "My brother Mateo, the co-owner, keeps paying the loan."}}, "leases": {<Northlight>: {"assumed": "yes"}}}`;
  - Maria and Sarah: no record.

- [ ] **Step 1: Write the failing tests.**
  - `test_each_persona_makes_the_owners_form_108_choice`: the four records as above, none holding `surrender`, and Maria and Sarah with no record.
  - `test_no_personas_explanation_is_too_long` (in `test_seed_demo_data.py`): no seeded persona's session has a `claim_text_gaps` detail on step `plans` (DeShawn's 59 characters and Andrés's 54 sit under the tool's cap of about 62, 4e-R5, so a cap below 59 fails here loudly).
  - Tier 3, worked by hand and pasted literally:
    - James `check1 1a` `/retain and reaffirmation`, `check2 1a` `/yes`;
    - Priya `/retain and redeem`, `/yes`;
    - DeShawn `/retain and explain`, `/yes`, with `Explain1 1a` and `Explain2 1a`;
    - Andrés `check1 1a` `/retain and explain`, `check2 1a` `/yes`, `Explain1 1a` and `Explain2 1a`, `Lessors Name 2a` "Northlight Auto Leasing", `check2a` `/yes`.
    - The two Explain halves are worked out by hand, never read off `split_explain` (which would pin the function to itself, S:768, Rule 10). The test's comment adds each leading word's Helvetica advance widths at 6 pt, plus the spaces, against `Explain1 1a`'s usable width (50.5 pt less `text_fit`'s margins, as `fit` takes them) and stops at the first word that would overflow; the literals asserted are the halves that sum gives.
  - `test_api_readback.py` runs unchanged in name. It now compares the ticked Form 108 for the four.
- [ ] **Step 2: Run them.** `pt.sh apps/intake/tests/test_seed_demo_data.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_api_readback.py --ds=config.settings.test -q`. Expected: fail before the seed writes the record, except `test_no_personas_explanation_is_too_long`, which passes at once (its see-it-fail is in Step 4).
- [ ] **Step 3: Implement** `_intentions`, the persona data, the write and the readback PATCH.
- [ ] **Step 4: Run** Step 2's command, `apps/intake/tests/test_intention_gaps.py`, and `ruff check`.
  - See-it-fail: give James `surrender` in the seed only, and show `test_api_readback`'s James case fail (the readback still sends `retain_reaffirm`). Lengthen DeShawn's seeded words past the cap, and show `test_no_personas_explanation_is_too_long` fail (it would pass vacuously before the seed writes any record).
- [ ] **Step 5: Commit** `seed: the four personas' Form 108 choices, the same through the API`.

### Task 9: CLAUDE.md, the spec amendment, the follow-ups and the gate

**Files:**
- Modify:
  - `CLAUDE.md`;
  - `docs/superpowers/specs/2026-11-18-forms-step4-design.md` (the appended block only);
  - `README.md:154` ("19 form schemas … 18 official AO forms" → 20 / 19).

- [ ] **Step 1: Rewrite the gotchas** (`SS` §9c, `SC` §1):
  - "The packet decides which forms a filer gets":
    - Form 108 applies to a confirmed secured debt (`claim_rows(session).secured`) or a lease of personal property (`claims.leases`, null kind included, R-LEASE-GATE), and `requires` is `_nothing`;
    - "A packet holds 15–18 forms" → 15–19.
  - "Forms need a completed intake":
    - `update_step` takes 1 to `WIZARD_STEP_COUNT`, "10 today";
    - Complete's order gains the `plans` details after Codebtors' gaps and before the tail, and the too-long details at the Debts and Contracts points (4e-R11);
    - the reopen key list (`:34`) gains `intention_answers`;
    - the lock test's `WRITES` (`:28`) gains the `intention_answers` PATCH.
  - "Nested debts and assets save by id": E4's store-and-flag. Names and collateral save as typed; the box note; the detail through `claim_text_gaps`, measured as in 4e-R4.
  - "Autosave sends only real edits": step 9's body (4e-R3), the `is_draft` clear after `update_step` 7 and `sentDebt` dropping `is_draft` from step 6's body (4e-R2), and `intention_exempt` never sent.
  - "Document upload sits mid-wizard": `/intake` steps 2–9 → 2–10.
  - "Schemas are checked at startup": "all 19 schemas" → 20, and `_LIST_BINDING` takes `claims.<list>[].<attr>` sheet columns; `intentions.` is gone (4e-R1).
  - Architecture, "PDF" (`CLAUDE.md:98`): "the 18 district boxes that sit on the page's printed "District of" (two on 103B, one on each of 16 other forms…" → 19 boxes, one on each of 17 other forms (Form 108's, which `test_box_background.py` now covers).
  - `:40`'s claims namespace sentence: nine lists with `leases` ("one of eight lists" → nine, "the seven `claim_rows` … reads" → eight), and the routing sentence gains `leases` → `contracts` and the attribute routes of 4e-R10. `:45`'s List of Creditors "seven lists" stays seven (`creditor_entries` names its sources).
  - "`field_values`, not `form_data`": no change. "Blank, not 0.00": Form 108's boxes (Global Constraints' list).
  - "Seed order": personas seeded before 4e have no `IntentionAnswers`, so Form 108 prints its choice boxes blank, nothing refuses, and the gap list carries the open choices. Re-create them with `seed_demo_data --reset`. The seed writes James's, Priya's, DeShawn's and Andrés's choices (E5).
  - A new gotcha, "Form 108's choices": the record shape, the prune (R-PRUNE) and its place after the PATCH's debts (R-SAVE-ORDER), the reader joining by id, the printed choice blank for `retain_explain` with blank words (R-BLANK-EXPLAIN), the exempt state (R-EXEMPT, 4e-R6), `split_explain` (4e-R5), the definition panels (E2, E3, R-521-LEAD), Review's one list (R-REVIEW-ONCE), the E2E control names (4e-R8) and `walkPlans`.
  - File Map:
    - `IntakeWizard.tsx`: "10-step wizard orchestrator", with `plans` in the key list;
    - `claim_rows.py`: "the eight lists Schedules D, E/F, G, H and Form 108 print";
    - new lines for `apps/intake/intentions.py`, `apps/forms/services/intention_fit.py`, `explain_split.py`, `build_form_108_index.py`, `build_form_108.py`, `PlansStep.tsx` and `plans/`;
    - "19 form types" → 20; the Data list gains `form_b108.pdf`'s index.
  - Then `pt.sh apps/intake/tests/test_claude_md_asset_order.py --ds=config.settings.test -q`, and prettier `--check` on CLAUDE.md.
- [ ] **Step 2: Append the SPEC AMENDMENT block** after the 4d block, before the file's closing `<!-- prettier-ignore-end -->` (the 4d precedent; no spec line above the block changes, and only the closing marker moves down). Heading "## Spec amendment, 4e (2026-11-24, owner decisions)". Its parts:
  - **Owner decisions**, each naming the spec lines and B-rows it supersedes:
    - E1: S:330's closing sentence;
    - E2: S:330's "verbatim and at equal length" and its three citations, B43 (S:921) and the same three citations in S:161 (§§ 521(a)(2), 722, 524(c)), which widen to the four provisions;
    - E3: none superseded; § 362(h) and § 521(a)(6) go to 4i's guide;
    - E4: S:233's and S:532's "the PUT refuses above the cap" for these four texts, and S:811's (§19 row 5) "measured caps on `creditor_name` and `collateral_description` on the Amounts Owed step" with its gotcha note "(the caps)"; B47 (S:925) applied;
    - E5: S:750-754's Step 9 column, S:756's "spread one per persona", S:811's "persona intentions spread one per choice (B38)", and B38 (S:916)'s "the four Form 108 choices spread one per persona, `walkPlans(choice)` with no default";
    - E6: S:534 (only the form's sentence shows in 4e); the 14-day ILND conflict and the steps after filing stay in 4i (a Plane ticket, Step 4);
    - E7: S:324's and S:328's sentences;
    - E8: E7's `PLANS_UNDECIDED_INFO`, `INTENTION_GAP_UNDECIDED` and `LEASE_GAP_UNDECIDED`, and the two labels the spec left open (the retain-and-explain panel's, the explanation's too-long label).
  - **The controller's rulings**:
    - R-SHAPE: S:424 keeps its shape; S:532's `intentions.` bindings become `claims.` cells; S:1090's note is settled;
    - R-LEASE-GATE: S:332's and S:811's lease-kind "detail" and B15 (S:893)'s last clause;
    - R-EXEMPT: S:328's join and B28 (S:906);
    - R-PRUNE: S:424's "not a confirmed row" prune, with drafts out;
    - R-EXPLAIN: S:532's "about 78 characters" for Explain1, and B29 (S:907);
    - R-BLANK-EXPLAIN: S:531 applied (a `retain_explain` row with no text prints its choice boxes blank);
    - R-521-LEAD: S:330's citation of § 521(a)(2) is shown as "(a) The debtor shall—", "[…]", paragraph (2)'s opening words, (A) whole, "[…]";
    - R-FORM-WORDS: none superseded; the form's and the statutes' words are approved in kind by E2 and E6;
    - R-REVIEW-ONCE: S:334's "Review lists each open row" is met by Review's existing gap list, with no new section;
    - R-SAVE-ORDER: none superseded; the save and prune follow the same PATCH's debts and contracts (in 4e the session PATCH carries no contracts).
  - **Plan rulings (4e plan, recorded for the owner)**: 4e-R1 through 4e-R23, each naming what it supersedes (Corrections below).
  - **A C-37 line**: the scope as built. Every Schedule D Part 1 row (B27); `other` and null leases (B15); the four provisions whole, § 521(a)(2)(A) as R-521-LEAD renders it, "[…]" included (4e-R7); the five exempt sentences and R-EXEMPT's three sources; `undecided`; the deadline sentence (E6); E1's pointer. Plus a C-21 awareness line: a surrender intention leaves 122A-2 lines 9b, 13b, 13e and 33d unchanged (S:856's default stands), beside the owner's presumption-of-abuse goal.
- [ ] **Step 3: The PR gate.** It runs here, and again, unchanged, after the final-review fix wave:
  - `zsh /Users/controlroom/.claude/jobs/bb720722/tmp/4b-sdd/gate.sh 4e`: `ruff check .`, `ruff format --check .` (the pre-existing 63 reported, none new), `check`, `makemigrations --check --dry-run`, the whole backend run and the whole vitest run;
  - `gate_pg.sh 4e`;
  - tsc;
  - `e2e-one.sh all 4e-gate`;
  - `known_defects.json` is `[]`;
  - `ASSERTED_CASES` is 1935;
  - `/opt/local/bin/git log develop..HEAD` shows no trailer.
  Report each count through a one-line `printf`. DIG-523 is reported as the known local failure.
- [ ] **Step 4: List the Plane tickets** for the controller:
  - E3: 4i's signing and filing guide quotes 11 U.S.C. § 362(h) and § 521(a)(6) whole, apart from the choices;
  - the texts 4e-R4 leaves unmeasured (the List of Creditors' entry, 122A-2's cells, a non-lease contract's texts);
  - E6: 4i's guide states the 30-day rule in the form's and § 521(a)(2)(A)'s words, the copies to the trustee and the creditors, and ILND's 14-day conflict (C-36), with the steps after filing;
  - the completion percentage doesn't count step 9 (4e-R15);
  - C-21 and DIG-505 awareness beside the presumption-of-abuse goal (`SC` §3).
  The PR housekeeping line says DIG-542 closes, DIG-547 closes, and DIG-126 closes its Form 108 half only (106J-2 waits for joint filing, DIG-71).
- [ ] **Step 5: Commit** `docs: CLAUDE.md and the step 4 spec's amendment for Form 108 and Your Plans`.

## Corrections to the spec (the spec is amended only by Task 9's appended block)

Owner decisions and controller rulings (binding):

- **E1.** S:330's "The court's guide for filers without an attorney explains the effects: {link}." The guide never mentions surrender or retain-and-explain and leans toward reaffirmation and redemption. Each panel closes with `PLANS_EFFECTS_HELP`.
- **E2.** S:330's "verbatim and at equal length" can't both hold. Each provision is whole and unedited, with equal prominence: one collapsed panel per choice. § 521(a)(2) becomes § 521(a)(2)(A) (shown as R-521-LEAD rules, 4e-R7), and § 365(p)(2) gets a panel for "assumed". B43 (S:921) and S:161's three citations ("11 U.S.C. §§ 521(a)(2), 722, 524(c)") widen to the four provisions.
- **E3.** Step 9 shows no consequence statute. § 362(h) and § 521(a)(6) are 4i's.
- **E4.** S:233 and S:532 ("the PUT refuses above the cap"; "the Amounts Owed step gains a measured cap") become store-and-flag (B47) for `creditor_name`, `collateral_description`, the lessor's name and the lease description, and so do S:811's (§19 row 5) "measured caps on `creditor_name` and `collateral_description` on the Amounts Owed step" and its gotcha note "(the caps)". S:532's reason ("the Form 108 boxes are … narrower than either") holds for the collateral only: Schedule D's name box is narrower than Form 108's, so the measure covers every box that prints the text (4e-R4).
- **E5.** S:754's Andrés surrender becomes retain-and-explain, and no persona surrenders. S:756's "the four Form 108 choices spread one per persona", S:811's "persona intentions spread one per choice (B38)" and B38 (S:916)'s "the four Form 108 choices spread one per persona, `walkPlans(choice)` with no default" no longer hold: surrender is covered by synthetic tier 3 and vitest, and `walkPlans` takes the persona (4e-R8).
- **E6.** S:534's timing information is the form's own sentence on step 9. The statute's wording, the copies and the 14-day conflict stay in 4i (a Plane ticket, Task 9).
- **E7.** S:324's sentence (grade 9.1) and S:328's three information sentences ("Schedule C is answered after Complete.", grade 10.4, and false after a reopen) are replaced by `PLANS_NOT_APPLICABLE` and the five `PLANS_EXEMPT_*` sentences.
- **E8.** E7's `PLANS_UNDECIDED_INFO`, `INTENTION_GAP_UNDECIDED` and `LEASE_GAP_UNDECIDED` said an open row's boxes print blank, but its creditor, property and exempt box still print (S:326, R-EXEMPT). E8's words replace them, and E8 approves `WHAT_DOES_EXPLAIN_MEAN` and `CLAIM_TEXT_LABELS.explain`.
- **R-SHAPE.** S:532's `intentions.secured[].intention` and `intentions.leases[].assumed` can't print in Schedule D's order (`record_value` reads an object as `[]`; S:1090). They become `claims.secured[].intention | exempt | explain_1 | explain_2` and `claims.leases[].assumed`, joined by id in `claim_rows`. S:532's "through a derivation" becomes list cells, which E007 requires in a sheet group (`schema.py:566-584`).
- **R-LEASE-GATE.** S:332, S:811 and B15 (S:893): `claim_step_gaps` already holds the lease-kind gap, as a gate (`claims.py:91`, `:368-369`; `completion.py:127`). Nothing is added. A null kind stays in scope for API-stored rows.
- **R-EXEMPT.** S:328's join (`ExemptionClaim.asset_id == debt.secured_by_id`) gains the live link and a claim Schedule C prints. `no_claims` gives No even with a null link.
- **R-PRUNE.** S:424's prune of "not a confirmed row" keeps drafts out. Drafts get no intention until confirmed (4e-R2's clear makes the browser agree).
- **R-EXPLAIN.** S:532 attaches "about 78 characters" to `Explain1`. That figure is both boxes together (`SF` §1). The cap is measured across both (4e-R5), and the text is stored and flagged.
- **R-BLANK-EXPLAIN.** S:531 holds as written: a `retain_explain` row with blank words prints its creditor and property with the choice boxes blank, and stays an `INTENTION_GAP_EXPLAIN` detail (4e-R22).
- **R-521-LEAD.** S:330's § 521(a)(2) is quoted as "(a) The debtor shall—", "[…]", paragraph (2)'s opening words, (A) whole, "[…]" (4e-R7).
- **R-FORM-WORDS.** `OC`'s Form words section is the form's and the statutes' own words, approved in kind by E2 and E6; the copy gate reads only the approved table and E8 as DigniFi words.
- **R-REVIEW-ONCE.** S:334's "Review lists each open row" is met by Review's existing gap list. No second section, and `PLANS_REVIEW_HEADING` is not shipped.
- **R-SAVE-ORDER.** The record saves and prunes after the same PATCH's debts and contracts are written (in 4e the session PATCH carries no contracts, so only the debts).

Plan rulings (not owner decisions; for the owner to see):

- **4e-R1.** S:766's "a tier 1 test per namespace that every … `intentions.` … binding reads what it names" and S:805's 4a plumbing: the namespace is removed.
- **4e-R3.** S:229's autosave rule applied: with no row in scope the body is null.
- **4e-R4.** The measured forms widen from Form 108 to every box that prints the text.
- **4e-R2.** S:322-334's step shows no row for an unconfirmed draft; while one is the only secured debt, `PLANS_NOT_APPLICABLE` is untrue (accepted; Complete refuses meanwhile).
- **4e-R7.** § 521(a)(2)(A) is shown as R-521-LEAD rules. The retain-and-explain panel's label is E8's `WHAT_DOES_EXPLAIN_MEAN`.
- **4e-R8.** S:756's and S:760's `walkPlans(choice)` becomes `walkPlans(persona)` with a `plans` fixture.
- **4e-R9.** S:532's "two `sheet` groups" need `claims.` in `_LIST_BINDING`, which this plan adds.
- **4e-R11.** S:334's gap list gains the too-long details. Every new gap is a `detail`, spliced by step.
- **4e-R12.** S:226's shift for 4e: 9 → 10 only.
- **4e-R13.** S:208's live region on step 9 (the open rows, `role="status"`), Review's existing list (R-REVIEW-ONCE) and the dashboard's pending-card path.
- **4e-R15.** The completion percentage is unchanged.
- **4e-R18.** DeShawn's words are S:752's draft.
- **4e-R19.** The statute source is uscode.house.gov, not S:731's Cornell [S10].
- **Counts.**
  - S:550 and S:810: 4e alone gives James 15 → 16, Priya 16 → 17, DeShawn 15 → 16 and Andrés 15 → 16 (the spec's 17s include 4h's 103A).
  - There are eight `generateAllForms` calls, not six: the eviction journey 16 → 17 and the SOFA journey 15 → 16.
  - Form types are 19 → 20 (21 after 4h), not "18 → 21".
  - The packet range moves to 15–19 in 4e itself (S:1133's "waits for 4e and 4h" is half right).
  - Tier 2 is +47: 1888 → 1935.
  - S:793's "1..12" reads 1..10 in 4e.
- **Migrations.** S:436's intake "0044" is `0048` (the record) and `0049` (the shift); S:523's forms "0010" is `0012`.
- **Answer order.** S:332's "No / Yes / I haven't decided yet." is kept: it is the form's order (`check2x` kids `/no`, `/yes`), with `undecided` last. Part 1 keeps the form's four in order, with `undecided` last.
- **Stale cites (S → now):**
  - `claim_rows.py:165-190` → `:165-194`;
  - `models.py:964-969` → `:1302-1308`; `:1144` → `:1488-1494`; `:1342-1344` → `:1680-1682`; `:871` → `:1209`; `:921` → `:1259-1262`;
  - `serializers.py:669` / `:674` → `:698`, `:835` / `:703`; `:1928-1930` → `:2152-2154`; `:989-999` → `:1019-1031`;
  - `fill_resolver.py:352-358` → `:353-363`;
  - forms `models.py:16-35` → `:16-36`;
  - `IntakeWizard.tsx:561` → `:251-260`;
  - `views.py:243-246` → `:219-231`; `:172-181` → `:150-164`.

## Self-review

- **Spec coverage.**
  - §6.9 → T6 (words, step), T7 (wiring), T5 (gaps).
  - §7.3 → T2 (record, prune), T4 (reader).
  - §10.1:
    - template → T3;
    - `applies`, `requires`, schema, header and sheets → T4;
    - caps → T4 (limits), T5 (details), T6 (notes);
    - timing → T6 (E6).
  - §10.3 → T4 (counts), T8 (persona ticks).
  - §6.0 → T7 (step table, shift, slot, autosave, layout check, deep link).
  - §18:
    - S:766 → T4 (tier 1 by registration; `claims.` cells read by `test_claims_bindings`);
    - S:767 → T4 (+47);
    - S:768 → T4, T8;
    - S:773 → T4 (`undecided`);
    - S:780 → T2, T4 (exempt);
    - S:782 → T5 (store, then flag);
    - S:785 → T4 (capacity);
    - S:786 → T5;
    - S:787 and S:788 → T2;
    - S:792 → T5, T6;
    - S:793 → T7.
  - B15 → T2, T4. B22 → T2. B26 → T4. B27 → T4. B28 → T2, T4. B29 → T4. B38 → T7, T8. B43 → T6. B45 and B50 → T5. B47 → T2, T5.
  - E1–E8 → T6 (E1, E2, E6, E7, E8's words), T9 (E3 and E6 tickets), T4–T6 (E4), T7–T8 (E5), T4–T5 (E8's `explain` label).
  - R-SHAPE → T4. R-LEASE-GATE → T2, T4. R-EXEMPT → T2. R-PRUNE → T2, T7. R-EXPLAIN → T4 (split, cap, label), T5 (detail), T6 (note).
  - R-BLANK-EXPLAIN → T4 (printed choice), T5 (gap). R-521-LEAD → T6 (Step 0, pin). R-FORM-WORDS → Global Constraints (Copy). R-REVIEW-ONCE → T6 (the step's status region), T7 (Review's test). R-SAVE-ORDER → T2.
  - DIG-547 → T1.
- **Order.**
  - The record's migration (`0048`, T2) lands before anything writes it: the builder (T2), the step (T7), the seed and the readback (T8).
  - The cells, schema, addendum, registry, `0012`, tiers and every packet pin land together (T4), so the suite is green between commits.
  - `form_108.limits.json` (T4, all five labels) exists before `intentions.py` reads it at import (T5). No task waits on the owner (E8), so the tasks run 1 to 9.
  - `test_rule_fixes.py` accepts `NEW_STEP_KEYS` from T4, so `{"step": "plans"}` passes before T7. T7's `NEW_STEP_KEYS` edit re-tightens it.
  - The gap sentences and their mirrors land together (T5).
  - The step shift (`WIZARD_STEPS`, `WIZARD_STEP_COUNT` and its pins, `NEW_STEP_KEYS`, `0049`) lands with every journey's `walkPlans` (T7).
  - The seed and the readback PATCH land together (T8).
  - `plans` gap steps exist from T5. A `GapLink` to `plans` draws only once the key is in `WIZARD_STEPS` (T7), as S:238 allows within one PR.
- **Type consistency.**
  - `Intention`, `Assumed` and `ExemptState` are T2's, pinned by T5.
  - `FORM_108_LEASE_KINDS` and `is_form_108_lease` are T2's, read by T4 and T7 (browser copy pinned by `claimTextRowCases.json`'s lease cases).
  - `split_explain` is T4's, read by T5's measure and T8's tier 3.
  - `plansBody`, `securedPlanRows` and `leasePlanRows` are T6's, read by T7; `openPlanRows` is T6's, read by the step's own status region.
  - The control names are 4e-R8's, used by T6's component and T7's `walkPlans`.
- **Arithmetic.**
  - `ASSERTED_CASES`: 1888 + 47 = 1935. Form 108's header is 2 (`Debtor 1` once, untagged, and `Bankruptcy District Information`), Part 1 is 4 × 6 = 24, and Part 2 is 7 × 3 = 21. No other binding changes (4e-R1 removes no binding; none used `intentions.`).
  - Addendum rows: 1660 + 47 = 1707.
  - Form types: 19 + 1 = 20. Packet range: 15 + 101A + 103B + (122A-2 or the Supp) + 108 = 19, so 15–19.
  - `WIZARD_STEP_COUNT`: 9 + 1 = 10. Migrations: intake 0048, 0049; forms 0012.
  - `generateAllForms`: Andrés 16, DeShawn 16, James 16, Priya 17, Maria 16, Sarah 16, eviction 17, SOFA 16.
  - Seed `PACKET_SIZE`: maria 16, sarah 16, deshawn 16, andres 16, james 16, priya 17. Tier 3's four asserts 16 → 17.
- **Proportion.** Nine tasks against about 73 files (about 70 before the plan review; the review wave adds `test_claims.py`, `claimTextLimits.test.ts`, `claimRows.ts` and `test_box_background.py`, and drops `ReviewStep.tsx`). The one body written out is `split_explain`, whose rule no test decides.

<!-- prettier-ignore-end -->
