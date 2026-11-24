# Forms step 4d, consumer debts and the Supp (Form 101 line 16, 106Sum line 7, Form 107 line 6, Form 122A-1Supp and the three new outcomes): Implementation Plan

<!-- prettier-ignore-start -->

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Amounts Owed (step 6) asks Form 101 line 16 as one three-way choice and, under `consumer`, Form 122A-1Supp's two military questions with their follow-ups, in the forms' words, into `PetitionAnswers`.

The one answer prints on four forms: Form 101 16a–c (already bound), 106Sum line 7, Form 107 line 6 and the Supp's line 1.

`MeansTest.calculate()` gains three outcomes, routed in the Supp's order:
- `not_consumer` → Form 122A-1 box 1;
- `veteran_exemption` → box 1 (line 2 Yes/Yes);
- `military_exclusion` → box 3 (a line 3 category, once line 2 is settled).

For all three, Parts 1–2 of 122A-1 (and 106Sum line 8, which copies 122A-1 line 11) print blank, the Supp joins the packet in place of 122A-2, and 122A-1 holds for the Supp and files with it.

Above the median, while line 16 or a military question the form reaches is unanswered, the outcome is `cannot_work_out` and 122A-2 stays in the packet, refused with `step="debts"`; the dashboard and the 122A-2 page then send the filer to Amounts Owed (4d-R27). Line 3's categories carry a fifth answer, "none applies" (D9), which claims no exclusion.

No filer ever gets box 2 without a complete 122A-2, and no screen shows a presumption DigniFi hasn't worked out.

**Architecture:**

- **One routing function.** `route_outcome(answers, above_median) -> str | None` in `backend/apps/eligibility/means_lines.py` (pure, standard library) holds the precedence. Only `MeansTest.calculate()` calls it, after the median lookup and before `read_tables` (4d-R2).
  - Every ROUTING reader reads the stored `MeansTest.outcome`, after `_recalculate_means_test` wherever the view runs it. The routing readers are 122A-2 `applies`, Supp `applies`, 122A-1 `requires`, 122A-1 `CheckBox1`, 122A-1's Parts 1–2 predicate, 106Sum line 8's half of its combined predicate (D10, a routing read on a mirrored box) and `means_page`'s `applies`.
  - Every PRINTING reader reads `PetitionAnswers`: the Supp's boxes, 106Sum `check7`, 107 `check6` and 106Sum 8–9g (D7).
  - `calculate()` records why a `cannot_work_out` waits: `calculation_details["open_on"]` is `"debts"` exactly when `route_outcome` returned `CANNOT_WORK_OUT`, else null. The calculate reply, the packet's `_means_reply` and `means_page` carry it as `open_on` (4d-R27).
  - A null outcome (a row saved before 3h1) is not one of the three, so it routes as today (R-ROUTE).
- **Two shared predicates**, also in `means_lines.py`: `supp_line_3_reached(answers)` (R-D2) and `military_question_open(answers)` (D3, widened by 4d-R3).
  - `route_outcome`, the petition gaps, the Supp's print predicates and 122A-2's D3 refusal all read these two, so "reached" and "open" have one definition.
- **The gaps.** `petition_step_gaps` gains a `debts` block: three gates and six details. `completion_gaps` splices it after the claims Debts gaps and before Contracts' gaps.
- **The prints.**
  - 106Sum `check7`, 107 `check6` and the Supp's `CheckBox2` each become two tagged bindings (R-D6). The consumer widget reads the rule `debt_nature_consumer`, which has `legal_review` and is in `ANSWER_BOX_RULES`. The other widget reads `debt_nature_not_consumer`, with neither.
  - 106Sum 8–9g are blank under `business`/`neither` (D7).
  - The Supp's schema is written by a new tool, `build_form_122a1_supp.py`.
  - 122A-1's `CheckBox1` gets its own rule, `means_result_box`, and a box 3 choice. Its 37 Parts 1–2 bindings take one predicate.
- **The pair.** The views pick 122A-1's partner from the packet: 122A-2, or the Supp, never both. That partner is used in `mark_filed`'s tie and in `mark_pair_filed`.
- **The browser.**
  - A new `petition/DebtNatureQuestion.tsx` is wired into `DebtsStep` with the ContractsStep in-step gate pattern.
  - The step 6 body gains `petition_answers` (`DEBT_NATURE_KEYS`).
  - `meansOutcomeSentences` gains three cases and an `openOn` argument. The dashboard shows them, and the Supp pair's notice, with no 122A-2, and a filed 122A-1 with box 2 gets a notice when its partner is now the Supp (D11).

**Tech Stack:** No new dependency.
- Backend: Django 5.0 + DRF and pytest-django (sqlite, plus the throwaway Postgres for `postgres`-marked cases).
- PDFs: pypdf 6.13 and PyMuPDF. PDF-only scripts run with `/Users/controlroom/.claude/jobs/bb720722/tmp/venv-mac/bin/python -I`, never `backend/.venv`.
- Frontend: React 19 + Vite + TypeScript, vitest + MSW + vitest-axe, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-18-forms-step4-design.md` (cited `S:line`). This plan builds:
- §19 row 4 (S:810);
- §11 whole (S:567-594);
- §6.6 (S:286-305);
- §5.3's 4d bindings (S:176, S:178) and §5.5 (S:194);
- §18's 4d tests (S:766-792);
- B16, B31–B34, B38, B39, B43, B45, B47, B48, B53, B54 and counsel C-39 (S:863), touching C-24.

The surveys are in `.superpowers/plan-4d/`, all read 2026-11-23 at develop `216c3a4`:
- `survey-spec.md` (`SP`), `survey-means.md` (`SM`), `survey-forms.md` (`SF`), `survey-wizard.md` (`SW`);
- `survey-critic.md` (`SC`);
- the owner's decisions and the controller's rulings, `owner-decisions.md` (`OD`: D1, D3, D4, D7, D8, D9, D10, D11, D18, R-D2, R-D5, R-D6, R-ROUTE). These are binding over the spec.
- the two plan reviews, `review-fidelity.md` (`F#`) and `review-exec.md` (`E#`), and their `dispositions.md`, all applied below.

Every new sentence is in `.superpowers/plan-4d/owner-copy.md` (`OC`). The spec's `path:line` cites date from 471f4ec and are stale. Every cite below was re-read at `216c3a4`, and a task that lands earlier moves the lines after it.

**Owner gate.**
- Only Tasks 1 and 3 depend on no word outside `OD`, so only they run before the owner reads `OC`.
- Task 2 waits for `OC` §1 (gap sentences).
- Task 4 follows Task 2, since it consumes `debt_nature_gaps`, `SUPP_DETAILS` and `GATE_*`.
- Task 5 follows Task 4 and waits for `OC` §2's D3 sentence (`FORM_122A2_MILITARY_OPEN`).
- Task 6 waits for `OC` §2 (pair refusal). Task 7 waits for `OC` §§2, 3 and 5 (outcome sentences, the Amounts Owed sentence and its phrase, the pair notice, the filed box 2 notice, card label). Task 8 waits for `OC` §§4 and 6 (step 6 words, the "none applies" label among them).
- An answer the owner changes is a one-place edit: a constant and its mirror. Each mirror is pinned, so a half-edit fails a test.

**The gate reruns after the final-review fix wave.** Task 11 runs it once before the final review, and again, unchanged, after the fix wave lands. The PR opens only on the second green run.

## Owner approvals (2026-11-23)

These are recorded in `.superpowers/plan-4d/owner-decisions.md`:
- D1: follow the form (three outcomes).
- D3: an open military question waits above the median.
- D4: the Supp and Form 122A-1 are tied.
- D7: 106Sum lines 8–9g print blank under not consumer.
- D9: the fifth category answer "none".
- D10: 106Sum line 8 prints blank whenever 122A-1 line 11 is blank.
- D11: the reverse filed-box-2 notice.
- D18: Andrés answers consumer.
- 4d-R20: the card label is the form's own title.

Controller rulings R-D2, R-D5, R-D6, R-ROUTE and 4d-R26 are recorded there too.

**Approved words.** The owner chose "Approve as drafted". Each sentence carries `// DRAFT: counsel C-39` (or `# DRAFT: counsel C-39` on the server), and builders copy them verbatim. The forms' and statutes' own words are in `.superpowers/plan-4d/owner-copy.md` §6, pinned to their sources.

- `GATE_DEBT_NATURE`: Say whether your debts are primarily consumer debts, on the Amounts Owed step.
- `GATE_DISABLED_VETERAN`: Say whether you are a disabled veteran.
- `GATE_RESERVIST`: Say whether you are or have been a Reservist or member of the National Guard.
- `DETAIL_DEBT_NATURE_TEXT`: Say what type of debts you owe.
- `DETAIL_DEBTS_ON_DUTY`: Say whether most of your debts began while you were on active duty. Time doing a homeland defense activity counts too.
- `DETAIL_CALLED_TO_DUTY`: Say whether you were called to active duty. Doing a homeland defense activity counts too.
- `DETAIL_DUTY_CATEGORY`: Choose a category, or say that none applies.
- `DETAIL_DUTY_RELEASED`: A date is written as MM/DD/YYYY. Type the date you were released from active duty.
- `DETAIL_DUTY_ENDED`: A date is written as MM/DD/YYYY. Type the date your homeland defense activity ended.
- `FORM_122A2_MILITARY_OPEN` / `MEANS_MILITARY_OPEN`: Answer each question about military service on the Amounts Owed step. Form 122A-2 waits for those answers.
- `MEANS_SUPP_PAIR_REFUSAL`: File Form 122A-1 and Form 122A-1Supp together.
- `MEANS_SUPP_PAIR_NOTICE`: Form 122A-1Supp says to submit it with the signed Form 122A-1. File them together.
- `MEANS_FILED_BOX_2_NOW_SUPP`: This filed copy has box 2 checked. With your current answers, your packet holds Form 122A-1Supp, and Form 122A-1 checks a different box.
- `MEANS_OUTCOME_NOT_CONSUMER`: You answered that your debts are not primarily consumer debts. Form 122A-1Supp says that a filer who answers this way checks box 1 on Form 122A-1, signs Part 3 and submits this supplement with it. Your packet follows the form.
- `MEANS_OUTCOME_VETERAN`: You answered Yes to both questions on line 2 of Form 122A-1Supp. The form says that a filer who answers this way checks box 1 on Form 122A-1, signs Part 3 and submits this supplement with it. Your packet follows the form.
- `MEANS_OUTCOME_MILITARY`: You chose one of the service categories on line 3 of Form 122A-1Supp. The form says that a filer who answers this way checks box 3 on Form 122A-1 and doesn't fill out the rest of that form during the exclusion period. The form counts back 540 days from the day you file; DigniFi doesn't check that. Your packet follows the form. (Followed by `FORM_122A1SUPP_AMENDED`, the form's own words: "If your exclusion period ends before your case is closed, you may have to file an amended form later.")
- `MEANS_OUTCOME_ANSWER_DEBTS`: Its result can't be worked out until you answer the questions on the Amounts Owed step. Its link text is `MEANS_DEBTS_STEP_PHRASE`, "the Amounts Owed step".
- `DEBT_NATURE_LIST_HEADING`: Your amounts owed, by the kind you chose for each
- `DEBT_NATURE_LIST_NOTE`: The form asks you to say which kind your debts primarily are. It doesn't say how to measure that.
- `DEBT_NATURE_LIST_EMPTY`: You haven't listed any amounts owed on this step.
- `DEBT_NATURE_KIND_NOT_CHOSEN`: Kind not chosen yet
- `MILITARY_FRAMING`: Form 122A-1Supp asks two questions about military service. The form asks these of everyone whose debts are mostly consumer debts.
- `MILITARY_540_DAYS`: The form counts back 540 days from the day you file. DigniFi doesn't know that day and doesn't check it; your tick is your statement.
- `DUTY_CATEGORY_NONE`: None of these categories applies to me
- `WHAT_DOES_DISABLED_VETERAN_MEAN`: What does “disabled veteran” mean?
- `WHAT_DOES_HOMELAND_DEFENSE_MEAN`: What does “homeland defense activity” mean on this form? (owner 2026-11-24, replacing "What’s “homeland defense activity”?", which the reading-level test scores at 12.3)
- `FORM_TYPE_METADATA.form_122a1_supp.label`: Form 122A-1Supp - Statement of Exemption from Presumption of Abuse

## Global Constraints

These ten are verbatim. Each is expanded in the bullets after it.

- vitest runs with --maxWorkers=2
- never tsc -b
- ruff==0.8.5 (CI runs ruff check only; the "63 files would be reformatted" ruff format output is pre-existing)
- backend tests with --ds=config.settings.test
- each task's commit stages by explicit path, never .serena/, DESIGN.md, assets/, .impeccable, .claude/, .superpowers/
- no Co-Authored-By or agent trailer in commits
- copy is grade <= 9 (flesch_kincaid_grade) and information, never advice
- every new sentence marked // DRAFT: counsel C-39 (or C-24 where an existing C-24 sentence is widened)
- every printed box blank, never 0.00 or a No the filer didn't give
- DIG-523 (Priya's 42px target) is a known develop failure.

The constraints in full:

- **The PR boundary.** 4d changes:
  - `PetitionAnswers` readers, plus two class-level edits to `PetitionAnswers` with no intake migration and no new key (all nine exist, `models.py:861-921`): `CHOICE_KEYS["duty_category"]` (`:889`) gains `"none"` (D9, a value in the encrypted JSON column, Task 1), and `RADIO_KEYS` (`:942-949`) gains the four military yes/no keys the Supp's radios print (4d-R26, Task 4);
  - one eligibility migration, `0007`, which edits `help_text` only (4d-R11);
  - the schemas `form_106sum.json`, `form_107.json` (`check6` only, by hand: 4f's tool rewrites the file later), `form_122a1.json` and `form_122a1_supp.json` (through the new tool);
  - `step2_verification.json`;
  - the Amounts Owed step, the dashboard and the sidebar's words.
  It adds no wizard step (`WIZARD_STEP_COUNT` stays 9) and no `FORM_TYPE_CHOICES` value (`form_122a1_supp` exists).
- **The owner's goal.** No filer ever wrongly assumes, or ends up with, a presumption of abuse:
  - never box 2 without a complete 122A-2;
  - never a presumption the app hasn't worked out;
  - an open question that could change the route gives `cannot_work_out`, never a figure.
- **Commands.**
  - **Backend tests with `--ds=config.settings.test`:**
    - `zsh /Users/controlroom/.claude/jobs/bb720722/tmp/4b-sdd/pt.sh <paths relative to backend/> --ds=config.settings.test -q` ("`pt.sh`" below);
    - `ppt.sh` for `postgres`-marked cases;
    - `py.sh manage.py check --settings=config.settings.test`;
    - `py.sh manage.py makemigrations --check --dry-run --settings=config.settings.test`.
    Name files, and never run the whole suite from a task (Task 11's gate is the one exception). Take counts from pytest's last line through a one-line `printf`.
  - **Frontend:**
    - `zsh …/fe.sh npx vitest run --maxWorkers=2 <files>`: vitest runs with --maxWorkers=2;
    - `zsh …/fe.sh npx tsc -p tsconfig.app.json --noEmit`: never tsc -b;
    - `fe.sh npx eslint <files>`;
    - `fe.sh ./node_modules/.bin/prettier --write <files>` then `--check`;
    - `userEvent` with no fake timers.
  - **Lint:** ruff==0.8.5. CI runs `ruff check` only. The "63 files would be reformatted" that `ruff format --check .` prints is pre-existing: run `ruff format --check` only on files a task creates. Lines are 100 columns at most.
  - **E2E:** `zsh /Users/controlroom/.claude/jobs/bb720722/tmp/4b-sdd/e2e-one.sh <spec|all> <label>`.
  - **E2E is expected red from Task 1 (Priya, above median with no `debt_nature`) and from Task 2 (Complete's new gate) until Task 9; run E2E only in Tasks 9 and 11.** The journeys register fresh accounts, so the builders' defaults don't reach them. The `completion_gaps` splice stays in Task 2 with its gap tests; the red window is declared, not narrowed (E6).
- **Git.**
  - Use `/opt/local/bin/git`: one plain command per call, from the worktree root, on `feat/forms-step4d`. No push, merge or branch change.
  - One commit per task. Each task's commit stages by explicit path, never `.serena/`, `DESIGN.md`, `assets/`, `.impeccable`, `.claude/` or `.superpowers/`.
  - No `Co-Authored-By` or agent trailer in commits.
  - Never a bare `sed -i`.
  - Pre-commit runs `black`, `ruff`, `prettier`, `eslint --max-warnings=0` and `check-json`. If it reformats a file, re-stage the same paths and commit again.
- **`step2_verification.json` is byte-compared.** Six tests compare the whole file with what a generator writes (`tool.merged_text`: `json.dumps(indent=2, ensure_ascii=False)`, scalar arrays on one line):
  - `test_claims_generator.py`, `test_form_101_schema.py`, `test_form_101a_schema.py`, `test_form_122a2_generator.py` and `test_schedule_c_generator.py`;
  - after Task 4, the new `test_form_122a1_supp_generator.py`.
  Every hand-edited row takes that format, and every task that touches the file runs all of them.
- **Copy.**
  - Copy is grade <= 9 (`flesch_kincaid_grade`, `reading-level.test.ts`) and information, never advice (`ADVICE`).
  - Every new sentence is marked `// DRAFT: counsel C-39` (or C-24 where an existing C-24 sentence is widened; 4d widens none) in `copy.ts`, and `# DRAFT: counsel C-39` in Python.
  - The forms' and the statutes' words go in `formText.ts`, unscored, each pinned to its source.
  - A word not in `OC` does not ship.
- **Blank, not 0.00.** Every printed box is blank, never 0.00 or a No the filer didn't give:
  - an unanswered `debt_nature` ticks nothing on any form;
  - a military answer prints only where the form reaches it under `consumer`;
  - a date prints only as MM/DD/YYYY;
  - 122A-1 Parts 1–2 go blank under the three outcomes, 106Sum 8–9g under `business`/`neither` (D7), and 106Sum line 8 also wherever 122A-1 line 11 is blank (D10);
  - "none applies" on line 3 ticks no category on the Supp.
- **Tier 2 and the known defects.**
  - Each binding task adds or re-keys its addendum rows in the same commit as the bindings.
  - It re-pins `ASSERTED_CASES` (`backend/apps/forms/tests/test_oracle_tier2.py:37`, 1877 today) from the run, with the arithmetic in the comment.
  - `known_defects.json` stays `[]`.
  - `manage.py check` passes after every task.
- **Known develop failure.** DIG-523 (Priya's 42px target) is a known develop failure. It is reported, not fixed, in every gate count.
- **Tests encode intent.** Names say the outcome. Synthetic data only, "Demo" names. A guard that passes before its code gets a see-it-fail mutation, named in its task.

## Rulings this plan makes (decided here, recorded for the owner)

`OD` settles D1, D3, D4, D7, D8, D9, D10, D11, D18, R-D2, R-D5, R-D6 and R-ROUTE. These are the rest, including the critic's §7 items 9–20 and the controller's rulings on the two plan reviews (F4 → 4d-R27, F11 → 4d-R16). 4d-R26 is new; the controller accepted it and 4d-R3 (Ruling L).

- **4d-R1 Outcome names, `OUTCOMES` and `PASSES`** (`SC` 10).
  - `NOT_CONSUMER = "not_consumer"` (12 characters).
  - `VETERAN_EXEMPTION = "veteran_exemption"` (17). Not `disabled_veteran`, which is a `PetitionAnswers` key, and a shared spelling would defeat every grep.
  - `MILITARY_EXCLUSION = "military_exclusion"` (18). It keeps the spec's name, now for the line 3 path only (D8: "now reservist").
  - All three fit `outcome`'s `max_length=20`. `SUPP_OUTCOMES = (NOT_CONSUMER, VETERAN_EXEMPTION, MILITARY_EXCLUSION)`.
  - `OUTCOMES` grows to seven, the four in today's order then these three.
  - `PASSES`: `NOT_CONSUMER: True` and `VETERAN_EXEMPTION: True`, since both tick box 1, "no presumption". `MILITARY_EXCLUSION: None`: box 3 says the test "does not apply now … but it could apply later", which is neither a pass nor a fail.
  - Nothing reads `passes_means_test` for a decision.
- **4d-R2 Where `calculate()` routes** (`SC` 9). After the median lookup (`models.py:172-179`) and before `read_tables` (`:191`):
  - `routed = route_outcome(answers, is_above_median(cmi, median_income_threshold))`;
  - `outcome = routed` when not `None`, else 122A-2's arithmetic as today.
  - So the non-null `calculated_cmi` and `median_income_threshold` stay filled. 122A-1 holds no figure on these routes (its Parts 1–2 are blank, 4d-R6), and the one form that copies `calculated_cmi` there, 106Sum line 8 ("Copy your total current monthly income from Official Form 122A-1 Line 11"), goes blank with 122A-1 line 11 (D10).
  - `details["open_on"] = "debts"` exactly when `routed == CANNOT_WORK_OUT` (route_outcome returns it only for an absent `debt_nature` or an open military question), and `details.setdefault("open_on", None)` beside `tables_gap`'s (`:200`), so a tables gap and every other outcome carry null (4d-R27).
  - The cost: a not-consumer or excluded filer is still refused by an Income-step gap (a Complete gate anyway) and by `NoTableInForce` from 2027-04-01, as every filer is. Task 11 files that in Plane.
  - `answers` is `self.session.petition_answers.get_answers()` through `getattr` (`{}` with no record). Importing `forms.registry.petition_answers_of` from `eligibility` would be a cycle.
- **4d-R3 What counts as an open military question** (D3, widened; accepted, Ruling L).
  - `military_question_open(answers)` is true under `debt_nature == "consumer"` when any question the Supp reaches is unanswered:
    - `disabled_veteran`;
    - `debts_on_duty` under its Yes;
    - `reservist` where line 3 is reached;
    - `called_to_duty` under its Yes;
    - `duty_category` under that Yes. `"none"` (D9, "None of these categories applies to me") is an answer, so it is not open.
  - D3 named two of these (`debts_on_duty`, `duty_category`). This plan adds the two gates and `called_to_duty`, by D3's own rule, "wait for the answer". `calculate()` runs from step 2 for the sidebar. Without them, an above-median consumer with `disabled_veteran` still unanswered would fall to 122A-2's arithmetic and could see `presumption` mid-wizard.
  - Below the median nothing changes: `at_or_below_median` (D3). A category's missing date is not "open": the claim is made, and the Supp's `requires` refuses the date (4d-R10).
  - A line 3 claim counts only once line 2 is settled (F2, D3 literally): `disabled_veteran` "no", or "yes" with `debts_on_duty` "no". While line 2 is open, a full line 3 claim falls through `route_outcome`'s exclusion branch, so the result is `cannot_work_out` above the median and `at_or_below_median` below it. The open answer could still turn box 3 into box 1, since the form takes line 2 first.
  - `"none"` routes as no exclusion: `route_outcome` falls to the median, `military_question_open` is false, `CheckBox7` prints blank (4d-R26), and the Supp stays out (D9).
- **4d-R4 B32's sentence is the gate's** (`SP` §9.5). `GATE_DEBT_NATURE` (`OC` §1) is the one string.
  - Form 122A-2's `requires` raises it with `step="debts"`.
  - `petition.py` imports `FORM_101A_LANDLORD` from the registry, so the registry imports `GATE_DEBT_NATURE` inside the function, the way `completion.py` imports `petition`, to avoid the cycle.
  - D3's own refusal is a separate constant, `FORM_122A2_MILITARY_OPEN`.
- **4d-R5 122A-1's box rule.** `means_result_box(session) -> str` returns:
  - `""` before the means test;
  - `"box_1"` for `not_consumer` or `veteran_exemption`;
  - `"box_3"` for `military_exclusion`;
  - otherwise `"box_1"`/`"box_2"` by `_median_comparison`'s below/above.
  - `CheckBox1`'s choices become `{"box_1": "/No Abuse", "box_2": "/Presumption of abuse applies", "box_3": "/Does not apply"}`.
  - `14a` stays on `median_comparison` and goes blank under the predicate (4d-R6).
  - `apps/forms/tests/means_pair.py:14` reads `choices["box_1"]`.
- **4d-R6 Parts 1–2 blank.** One predicate, `means_parts_1_and_2_print(session, answer_cache=None)`: true with no means test, or an outcome not in `SUPP_OUTCOMES`.
  - It is the `conditional_on` of every `form_122a1.json` field except `Debtor1.Name` (`:7`), `Bankruptcy District Information` and `CheckBox1` (`:41`): 37 fields, `14a` (`:684`) and `13A` included.
  - `conditional_on` is not in tier 2's key, so this adds no case.
  - D10: 106Sum `8` takes a combined predicate, `summary_line_8_prints(session, answer_cache=None)`, true only when both `debt_nature_consumer_or_unanswered` (D7) and `means_parts_1_and_2_print` hold, so 106Sum line 8 always equals 122A-1 line 11. Task 3 gives `8` the D7 predicate alone; Task 5, which produces `means_parts_1_and_2_print`, re-points `8` to the combined one (an earlier `conditional_on` naming a missing predicate fails `manage.py check`). `9a`–`9d` and `9g` keep D7's predicate: they copy Schedule E/F and still print for consumer filers. Also no tier 2 case.
- **4d-R7 The tagged split reuses the line 16 rules** (R-D6).
  - Two aliases are registered:
    - `debt_nature_consumer`, the `debt_nature_16a_yes` callable (`derivations.py:1193`);
    - `debt_nature_not_consumer`, the `debt_nature_16a_no` callable (`:1194-1198`).
    Both have `_step_of("debt_nature")`. The precedent is `schedule_j_total_income`, an alias of the line 12 rule. The aliases give each box a binding key that names its meaning, never "16a".
  - `debt_nature_consumer` joins `ANSWER_BOX_RULES` (`:1206-1217`): the filer's answer is exactly that box's choice.
  - The pairs:
    - 106Sum: `check7@2:T5` `{"true": "/consumer"}` and `check7@2:T6` `{"true": "/not consumer"}`;
    - 107: `check6@3:T6` `{"true": "/yes"}` and `check6@3:T3` `{"true": "/no"}`;
    - the Supp: `CheckBox2@1:T7` `{"true": "/Yes"}` and `CheckBox2@1:T6` `{"true": "/no"}`.
  - On each pair, the consumer widget is `legal_review: true` and the other is `false` (the `debt_nature_16a_no` precedent).
  - No existing binding covers a tagged pair with two states. `OD` cites Schedule D's `check 4` (untagged, each box its own state) and this plan cited `check 5@2:T51`/`@2:T56` (tagged, but both widgets share `/On`); neither is this shape (F14). So Task 3's Step 0 drawn pre-flight is the only proof and the stop condition: it proves, by drawing, that each answer ticks exactly one widget and that absent ticks none, and tier 1's combined draw (both tagged keys filled at once, two `/V` values on one field) neither spills nor loses a tick. If startup checks refuse, or the shared `/V` makes the blank binding unset the other, the task stops and reports. No untagged fallback is improvised (R-D6 decided).
- **4d-R8 The Supp's Part 2 predicates, one a question** (R-D2, S:177, S:780).

  | Box | Binding | Predicate | Reads |
  |---|---|---|---|
  | `CheckBox3` | `petition.disabled_veteran` | `petition_debt_nature_consumer` (a new row in `_PETITION_PREDICATES`) | `debt_nature` |
  | `CheckBox4` | `petition.debts_on_duty` | `supp_line_2_follow_up` | consumer and `disabled_veteran == "yes"` |
  | `CheckBox5` | `petition.reservist` | `supp_line_3` | `supp_line_3_reached` |
  | `CheckBox6` | `petition.called_to_duty` | `supp_line_3_follow_up` | that and `reservist == "yes"` |
  | `CheckBox7` | `derived:supp_duty_category` (4d-R26) | `supp_categories` | that and `called_to_duty == "yes"` |
  | `Date1` | `petition.duty_released_on` | `supp_date_1` | that and category `"2"` |
  | `Date2` | `petition.duty_ended_on` | `supp_date_2` | that and category `"4"` |

  - `CheckBox3`–`CheckBox6` map `{"yes": "/Yes", "no": "/no"}`, `asked`. `CheckBox7` maps `{"1": "/1", "2": "/2", "3": "/3", "4": "/4"}` through the rule `supp_duty_category`, which returns the stored category for `"1"`–`"4"` and `""` otherwise, so `"none"` prints blank (4d-R26).
  - `CheckBox3`–`CheckBox7` are `legal_review: true`, as `build_form_122a2.py` marks every filer answer. The guard passes `asked`, and `supp_duty_category` joins `ANSWER_BOX_RULES` (it ticks exactly the filer's own stored category). `Date1` and `Date2` are `false`.
  - `CheckBox1` (amended), `Debtor2.Name` and `Case number1` stay unbound.
  - The new predicates live in a `_SUPP_PREDICATES` dict beside `_PETITION_PREDICATES`, merged into `PREDICATES` (`derivations.py:1763`). Each has the signature `(session, answer_cache=None)` and calls the `means_lines` helpers on `petition_answers_of`'s mapping.
- **4d-R9 Dates** (`SC` 15, B47).
  - `record_value` (`answer_records.py:190-215`) blanks a scalar `petition.duty_released_on` or `duty_ended_on` that isn't MM/DD/YYYY, as it does `filed_on` cells (`:212-214`). The stored value stays as typed.
  - No limits file: the browser masks the box to MM/DD/YYYY with `mmDdYyyy` (`masks.ts:33`), the server's 500-character ceiling holds, and a malformed date never prints, so it can't meet `ValueTooLong`.
- **4d-R10 `Gap.forms` and the blank count.**
  - `FORMS_OF_KEY` maps the five military follow-up keys (`debts_on_duty`, `called_to_duty`, `duty_category`, `duty_released_on`, `duty_ended_on`) to `("form_122a1_supp",)`. `debt_nature_text` keeps `("form_101",)`.
  - None of the five military details ever leaves a blank box on a form a filer files:
    - with no exclusion claimed, an open follow-up keeps the Supp out of the packet, and above the median refuses 122A-2 and 122A-1 with D3's sentence;
    - with an exclusion claimed (line 2 settled), the Supp is in the packet, and its `requires` refuses the first open follow-up or bad date, and 122A-1 with it (D4, S:592). Since `military_exclusion` needs line 2 settled, that refusal is always a date (`DETAIL_DUTY_RELEASED`, `DETAIL_DUTY_ENDED`), never `DETAIL_DEBTS_ON_DUTY`.
    - R-D2's boundary (line 2 Yes with `debts_on_duty` open and line 3 fully claimed) is not `military_exclusion` (F2): above the median it is `cannot_work_out`, 122A-2 stays in the packet and refuses with `FORM_122A2_MILITARY_OPEN`, and 122A-1 with it (D3); below the median it is `at_or_below_median` (D3: below unchanged). The Supp stays out either way, so `DETAIL_DEBTS_ON_DUTY` lists with its `GapLink` and leaves no blank box.
    - Under `"none"` (D9) no exclusion is claimed and no follow-up is open.
  - So `GapsNotice` leaves all five out of its blank count by exact match, beside `PETITION_DETAIL_LANDLORD` (`GapsNotice.tsx:68-75`). The sentences still list, with their `GapLink`.
- **4d-R11 `help_text` and `0007`** (`SC` §2.7). `outcome`'s `help_text` (`models.py:79-82`) is rewritten to list the seven. `passes_means_test`'s (`:69-72`) gains "…or while the means test doesn't apply now (a line 3 exclusion)".
  - `backend/apps/eligibility/migrations/0007_meanstest_outcome_help_text.py` holds the two `AlterField`s. It is generated by `makemigrations eligibility --name meanstest_outcome_help_text` and run through `ruff format`.
  - `makemigrations --check` is in the gate, so the edit must carry its migration.
  - Docstrings that list four outcomes are re-worded to seven: `models.py:146-148` and `apps/intake/views.py:338-339`. (`means_test_calculator.py:62` reads `"outcome": str` and lists none; E19.)
- **4d-R12 `/means-test` keeps its redirect** (`SC` 11). For the three outcomes, `applies` is `False` and the page replaces itself with `/sofa` as today. The sentence shows in the sidebar and on the dashboard. Departs from S:579 (Corrections).
- **4d-R13 The dashboard block** (`SC` 12).
  - The outcome block renders when the packet holds 122A-2 or when `outcome` is in the three.
  - Under 122A-2 it carries `MEANS_PAIR_NOTICE`, as today. Under the Supp it carries `MEANS_SUPP_PAIR_NOTICE`.
  - It stays a `role="status"` block that stays mounted.
- **4d-R14 The sidebar names no Amounts Owed dependency (B34)** (S:585, S:912, `SC` 12, narrowed by F4). The sidebar keeps O4's `MEANS_OUTCOME_ANSWER_SIDEBAR` under `cannot_work_out`, whatever `open_on` says. The dashboard and the 122A-2 page do name Amounts Owed (4d-R27). Corrections; nothing is filed in Plane, since B34 rules the sidebar line out.
- **4d-R15 Hidden answers use `HiddenLine`** (`SC` 13, `SW` D3). This is S:177's and 4b-ii's established pattern, not S:298's "disappear".
  - Each block a changed answer hides keeps its stored answers behind one `HIDDEN_ANSWERS` line with Show and Delete:
    - 16c's text under `consumer`/`business`;
    - the military block under a non-consumer answer;
    - line 2's follow-up (`debts_on_duty`) under `disabled_veteran` No (F8);
    - line 3's block under line 2 Yes/Yes;
    - line 3's follow-ups under `reservist` No;
    - the categories and dates under `called_to_duty` No;
    - each date under another category, `"none"` included (D9).
  - A local `GATE_BLOCKS` map re-hides them, as `PetitionQuestions.tsx:122,308` does.
- **4d-R16 The C-39 list** (`SC` 14, `SW` D4, D5, §6).
  - It sits inside the new block, after the legacy sentences and before `UPLDisclaimer` (`DebtsStep.tsx:977-1000`). The step's existing "Total Amounts Owed" (`:1001-1018`) stays where it is, after the disclaimer (F11, controller ruling: keep the order). The list and the sum are one disclaimer apart on the page, so the C-39 packet names that adjacency and quotes S:296's reason: "a total beside the question would adopt the by-amount reading of "primarily", one of several".
  - Rows are `keptRows(rows, isBlankDebt)` (drafts included, as the step shows them), grouped by `debt_type` in `DEBT_TYPE_WORDS` key order, then "Kind not chosen yet".
  - Each row shows `claimRowName` and `formatFigure(amount_owed)`. There is no sum, no count and no comparison.
  - "I have no amounts owed" still asks line 16: Form 101 prints it for every filer. The list then shows `DEBT_NATURE_LIST_EMPTY`.
- **4d-R17 Completion percentage unchanged** (`SC` §2.8). The debts section stays counted from `claim_step_gaps` alone. An unanswered line 16 is already a Complete gate. Recorded, not changed.
- **4d-R18 A filed 122A-1 with box 2 gets a notice once its partner is the Supp** (`SC` 17, D11, F13).
  - The list reply gains nothing: `stored_box_2` exists (`views.py`, H52).
  - The dashboard's `noticeOf` (`FormDashboard.tsx:445-461`) returns `MEANS_FILED_BOX_2_NOW_SUPP` (`OC` §2) for a filed 122A-1 whose `stored_box_2` is true while `meansPartnerOf(packet)` is `'form_122a1_supp'`, after O11's `filed_before_means_test` branch, so O11's notice wins. It is information only, modelled on `MEANS_FILED_MISMATCH` (`copy.ts:172`). Task 7.
- **4d-R19 No 540-day information line** (`SC` 16). S:303 says DigniFi doesn't check the date.
- **4d-R20 The Supp card label** (`SC` 19). This is `OC` §5's proposal, the form's own title, and the owner chooses.
- **4d-R21 Two `WhatDoesThisMean` on one step.** The component (`frontend/src/components/wizard/WhatDoesThisMean.tsx:16`) gains an optional `label?: string`. It goes on `<summary>` as `aria-label`, so each instance has its own accessible name (S:1094's note, needed here before 4f). Without it, nothing changes.
- **4d-R22 `answer_household`'s step 6 default** (`SC` §2.3).
  - New keyword `debt_nature: Mapping[str, str] | None = DEBT_NATURE_DEFAULTS`, where `DEBT_NATURE_DEFAULTS = MappingProxyType({"debt_nature": "consumer", "disabled_veteran": "no", "reservist": "no"})`.
  - It writes only those keys, a stored key beating the default, through the session's own relation (record made if missing). It never goes through `answer_petition`, so step 1's gates stay unanswered for tests that assert them.
  - A mapping passed is merged whole. `None` leaves the record alone.
  - `PETITION_DEFAULTS` (`builders.py:201-208`) gains the same three keys for the `answer_household(debt_nature=None)` + `finish_intake` path.
- **4d-R23 The one-step D18 personas.** All six are `consumer`, line 2 No, line 3 No, written in `_petition` (`seed_demo_data.py:177-191`) and `gates()` (`personas.ts:307-321`). No persona gets the Supp. Tier 3's synthetic sessions cover it (B39).
- **4d-R24 `test_coverage.py`'s dead row** (`SC` §2.4). Its `FormAnswer(form_type="form_101", field_key="primarily_consumer_debts")` (`:24-28`) feeds nothing after Task 3. It is dropped, and the comment says Maria's step 1 answers print.
- **4d-R25 Housekeeping.** DIG-72 (the Supp's unbound Parts 1 and 2) and DIG-121 ("Consumer vs business debts never asked") close with 4d. The PR body says so.
- **4d-R26 `CheckBox7` through a rule, and `RADIO_KEYS` (new, accepted by the controller, Ruling L; found while applying D9).**
  - D9 puts `"none"` in `CHOICE_KEYS["duty_category"]`. A direct `petition.duty_category` binding can't then print it blank: `test_petition_radio_keys.py:37-46` requires a `petition.` radio's `choices` to equal `CHOICE_KEYS[key]`, and a `"none": ""` entry fails E005 (`schema.py:368-370`: no widget has a `""` state). `_emit` does leave a `""` answer blank (`fill_resolver.py:690-703`), so a rule returning `""` works.
  - So `CheckBox7` binds `derived:supp_duty_category` (the category for `"1"`–`"4"`, else `""`; `_step_of("duty_category")`), choices `"1"`–`"4"`, `legal_review: true`, in `ANSWER_BOX_RULES`. It leaves the petition-radio walk.
  - Found outside the dispositions: `test_the_save_guards_exactly_the_keys_a_radio_prints` (`test_petition_radio_keys.py:49-51`) walks every non-single-box `petition.` binding, so `CheckBox3`–`CheckBox6` need `disabled_veteran`, `debts_on_duty`, `reservist` and `called_to_duty` in `RADIO_KEYS` (`models.py:942-949`). All four are `YES_NO_KEYS` (`:861-864`), so the save's guard already holds them. Task 4.
- **4d-R27 `open_on` names Amounts Owed where the result waits on it** (F4/E9, controller ruling).
  - `calculate()` stores `calculation_details["open_on"]` (4d-R2). The calculate reply (`means_test_calculator.py:100-109`), the packet's `_means_reply` (`forms/views.py:214-230`) and `means_page` (`means_page.py:283-286`) carry `open_on`; a row saved before 4d reads null.
  - `means_page`: while `open_on == "debts"`, the reply's `gap` is `GATE_DEBT_NATURE` when `debt_nature` is absent, else `FORM_122A2_MILITARY_OPEN` (existing words), in place of `means_test_gaps`' first (`:252`). So Continue holds with the real reason.
  - The dashboard and the page: under `cannot_work_out` with `open_on` `"debts"` and no table gap, `meansOutcomeSentences` gives `MEANS_OUTCOME_ANSWER_DEBTS` ("…until you answer the questions on the Amounts Owed step.", `OC` §3) in place of `MEANS_OUTCOME_ANSWER_PAGE`. Its phrase `MEANS_DEBTS_STEP_PHRASE` ("the Amounts Owed step") links to `/intake?step=debts` on both, by the split-on-phrase pattern of `FormDashboard.tsx:441`; the `/means-test` link isn't shown on that path.
  - The sidebar keeps `MEANS_OUTCOME_ANSWER_SIDEBAR` (4d-R14, B34).

## Review Focus

Five conditions most likely to pass a task review while wrong:

1. **No box 2 without 122A-2, and no box 2 beside the Supp, including on a stale row.**
   - Task 5 `test_a_supp_outcome_never_ticks_box_2_and_never_holds_for_122a2` and `test_a_stale_presumption_row_routes_by_the_recalculated_outcome`.
2. **An open military question above the median is never worked out to a figure** (4d-R3).
   - Task 1 `test_an_open_military_question_above_the_median_cannot_be_worked_out` (parametrized over the five open questions).
   - Task 5 `test_an_open_military_question_holds_both_forms_in_its_own_sentence`.
   - Task 5 `test_the_page_holds_continue_on_the_amounts_owed_question` and Task 7 `sends a result that waits on Amounts Owed to that step` (4d-R27: the page and the dashboard name the right step).
3. **R-D2's boundary: line 2 Yes/Yes skips line 3, and line 2 Yes with `debts_on_duty` open reaches it but holds its claim (F2).**
   - Task 1 `test_a_line_3_claim_waits_for_line_2_to_settle` (a full line 3 claim with line 2 open gives `cannot_work_out` above the median and `at_or_below_median` below, never `military_exclusion`).
   - Task 2 `test_line_2_yes_yes_asks_no_line_3_gate` and `test_line_2_yes_with_its_follow_up_open_still_asks_line_3`.
   - Task 4 `test_line_2_yes_yes_prints_no_line_3_box`.
   - Task 1 `test_called_to_duty_with_no_category_that_applies_works_out_122a2` (D9).
4. **Each line 16 answer ticks exactly one widget, and absent ticks none, on 106Sum, 107 and the Supp.**
   - Task 3 `test_each_debt_nature_answer_ticks_exactly_one_box_on_the_page` (drawn and read back).
   - Task 4 `test_the_supps_line_1_ticks_exactly_one_box`.
5. **122A-1 and the Supp refuse together and file together, and 122A-1's partner is never both forms.**
   - Task 5 `test_122a1_waits_for_the_supp_in_the_supps_own_words` (F7: its see-it-fail deletes the Supp branch of `_needs_means_test_and_form_122a2`).
   - Task 6 `test_marking_122a1_alone_is_refused_while_the_supp_is_unfiled`, `test_mark_pair_filed_files_122a1_with_the_supp` and `test_a_supp_date_gap_refuses_the_pair_and_writes_nothing`.

---

### Task 1: The outcomes, their precedence and the step 6 defaults

**Files:**
- Create: `backend/apps/eligibility/migrations/0007_meanstest_outcome_help_text.py`.
- Modify:
  - `backend/apps/eligibility/means_lines.py`: constants `:35-39`; the new functions after `OUTCOMES`.
  - `backend/apps/eligibility/models.py`: imports `:29-35`; `PASSES` `:41-46`; `help_text`s `:69-72`, `:79-82`; docstring `:146-148`; routing and `details["open_on"]` beside `:184-200` (4d-R2).
  - `backend/apps/intake/views.py:338-339`: docstring.
  - `backend/apps/intake/models.py:889`: `CHOICE_KEYS["duty_category"]` gains `"none"` (D9).
  - `backend/apps/intake/tests/builders.py`: `answer_household` `:91-180`; `PETITION_DEFAULTS` `:199-208` and its comment.
  - `backend/apps/intake/management/commands/seed_demo_data.py`: `_petition` `:177-191`.
  - `backend/apps/intake/tests/test_seed_demo_data.py:853-881`.
  - `frontend/e2e/fixtures/personas.ts`: `PersonaPetition` `:281-300`; `gates()` `:307-321`.
  - `frontend/src/types/api.ts`: `MeansOutcome` `:820-824`.
  - `backend/apps/eligibility/tests/test_means_lines.py:235-236`, `test_means_outcome.py`, `test_means_test_calculator.py`.
  - Every red test the blast-radius run shows.

**Interfaces:**
- Produces, in `apps.eligibility.means_lines`:
  - the constants `NOT_CONSUMER`, `VETERAN_EXEMPTION`, `MILITARY_EXCLUSION`, `SUPP_OUTCOMES`, and `OUTCOMES` (seven);
  - `supp_line_3_reached(answers: Mapping[str, object]) -> bool`;
  - `military_question_open(answers: Mapping[str, object]) -> bool`;
  - `route_outcome(answers: Mapping[str, object], above_median: bool) -> str | None`.
- Produces `builders.DEBT_NATURE_DEFAULTS`, and `answer_household(…, debt_nature=DEBT_NATURE_DEFAULTS)`.

The precedence, the one body this plan writes, because no test decides its order beyond B53:

```python
def route_outcome(answers, above_median):
    """B53's order. Called only by MeansTest.calculate(); None means work 122A-2 out."""
    nature = answers.get("debt_nature")
    if nature in ("business", "neither"):
        return NOT_CONSUMER
    if nature == "consumer":
        veteran, on_duty = answers.get("disabled_veteran"), answers.get("debts_on_duty")
        if veteran == "yes" and on_duty == "yes":
            return VETERAN_EXEMPTION
        line_2_settled = veteran == "no" or (veteran == "yes" and on_duty == "no")
        if (
            line_2_settled  # D3: an open line 2 could still turn box 3 into box 1 (F2)
            and supp_line_3_reached(answers)
            and answers.get("reservist") == "yes"
            and answers.get("called_to_duty") == "yes"
            and answers.get("duty_category") in ("1", "2", "3", "4")  # "none" claims nothing (D9)
        ):
            return MILITARY_EXCLUSION
    if not above_median:
        return AT_OR_BELOW_MEDIAN
    if nature is None or military_question_open(answers):
        return CANNOT_WORK_OUT
    return None
```

`supp_line_3_reached` is `debt_nature == "consumer" and not (disabled_veteran == "yes" and debts_on_duty == "yes")`. `military_question_open` is 4d-R3's list (an absent `duty_category` is open; `"none"` is not). Whenever an open line 2 holds back a line 3 claim, `military_question_open` is true, so above the median the claim falls to `CANNOT_WORK_OUT` and below it to `AT_OR_BELOW_MEDIAN` (F2, D3).

- [ ] **Step 0: Check for drift.** Run `py.sh manage.py makemigrations --check --dry-run --settings=config.settings.test` on the untouched tree. Expected: "No changes detected". Otherwise stop and report.
- [ ] **Step 1: Write the failing tests.**
  - `test_means_lines.py`:
    - rename `:235` to `test_the_outcomes_are_the_seven_the_app_shows_in_order`, and assert the seven in 4d-R1's order;
    - `test_route_outcome_follows_the_supps_order`, parametrized as below;
    - `test_a_line_3_claim_waits_for_line_2_to_settle`;
    - `test_an_open_military_question_above_the_median_cannot_be_worked_out`, over the five open questions of 4d-R3;
    - `test_a_category_with_no_date_is_still_a_claim` (line 2 No, category `"2"`, no `duty_released_on` → `military_exclusion`);
    - `test_called_to_duty_with_no_category_that_applies_works_out_122a2` (D9): consumer, line 2 No, line 3 Yes/Yes/`"none"` → `None` above the median (122A-2's arithmetic) and `at_or_below_median` below; `military_question_open` is false;
    - `test_only_calculate_routes`: a source scan of `backend/apps/**/*.py`, tests excluded, matches call sites only, `(?<!def )\broute_outcome\(`, and asserts the set of files hit is `{"apps/eligibility/models.py"}` (E11: a plain `route_outcome(` also matches the `def` in `means_lines.py`).

    `test_route_outcome_follows_the_supps_order` cases, each `(answers, above) → expected`:

    | Answers | Above | Expected |
    |---|---|---|
    | `business` | False | `not_consumer` (R-D5) |
    | `business` | True | `not_consumer` |
    | `neither` | True | `not_consumer` |
    | `business` with stale military Yes/Yes answers | True | `not_consumer` (the keys count only under `consumer`) |
    | consumer, line 2 Yes/Yes, line 3 Yes/Yes/"1" | False | `veteran_exemption` (line 2 first) |
    | consumer, line 2 Yes/Yes | True | `veteran_exemption` |
    | consumer, line 2 No, line 3 Yes/Yes/"4" | False | `military_exclusion` (below the median, B53) |
    | unanswered | False | `at_or_below_median` |
    | unanswered | True | `cannot_work_out` (S:575) |
    | consumer, No/No | True | `None` |
    | consumer, No/No | False | `at_or_below_median` |
    | consumer, line 2 Yes/No, line 3 No | True | `None` |
    | consumer, line 2 Yes/No, line 3 Yes/Yes/"3" | True | `military_exclusion` (line 2 settled) |
    | consumer, line 2 Yes/open, line 3 Yes/Yes/"3" | True | `cannot_work_out` (F2, D3) |
    | consumer, line 2 Yes/open, line 3 Yes/Yes/"3" | False | `at_or_below_median` (D3: below unchanged) |
    | consumer, line 2 No, line 3 Yes/Yes/`"none"` | True | `None` (D9) |

    `test_a_line_3_claim_waits_for_line_2_to_settle` (R-D2 boundary, F2): consumer, line 3 Yes/Yes/"3", and line 2 open two ways, `disabled_veteran` absent and `disabled_veteran` "yes" with `debts_on_duty` absent → `cannot_work_out` above the median and `at_or_below_median` below, never `military_exclusion`; `supp_line_3_reached` is true for both. Line 2 Yes/Yes with a stale line 3 claim → `veteran_exemption`.
  - `test_means_outcome.py` (through `MeansTest.calculate()` on built sessions):
    - `test_a_business_filer_above_the_median_is_not_consumer_and_passes`: outcome `not_consumer`, `passes_means_test is True`, `calculated_cmi` and `median_income_threshold` stored;
    - `test_a_veteran_exemption_passes_and_a_military_exclusion_is_neither`: `True` and `None`;
    - `test_an_unanswered_line_16_above_the_median_cannot_be_worked_out`: `answer_household(debt_nature=None)`, so there is no record;
    - `test_an_unanswered_line_16_below_the_median_stays_below`;
    - `test_the_builder_default_keeps_todays_presumption`: the existing presumption fixture, unchanged outcome;
    - `test_a_result_that_waits_on_amounts_owed_says_so` (4d-R27): `calculation_details["open_on"]` is `"debts"` for an unanswered line 16 above the median and for an open military question above it, and `None` for a tables gap (`cannot_work_out` from `NoMeansTestTable`), for `presumption` and for every Supp outcome.
  - `apps/intake/tests/test_petition_answers.py`: `test_none_applies_saves_as_a_category_answer`: a session PATCH with `petition_answers: {duty_category: "none"}` saves (D9's `CHOICE_KEYS` value), and `"5"` is still a 400.
  - `test_seed_demo_data.py`:
    - rename `:853` to `test_no_seed_builder_or_fixture_writes_a_4i_key`;
    - add `"debts"` to the allowed step tuple;
    - drop `"debt_nature"` from the `:863` set, leaving `{"paid_preparer", "credit_counseling"}`;
    - `test_every_persona_answers_line_16_and_both_military_gates`: each of the six has `consumer`, "no", "no";
    - Priya's outcome stays `presumption`.
  - `apps/eligibility/tests/test_means_copy.py`: `test_the_browsers_outcome_type_is_the_servers`. It reads `MeansOutcome`'s string literals from `frontend/src/types/api.ts` and asserts the set equals `OUTCOMES`. It closes the enum-drift gotcha for this field.
- [ ] **Step 2: Run them.** `pt.sh apps/eligibility/tests/test_means_lines.py apps/eligibility/tests/test_means_outcome.py apps/eligibility/tests/test_means_copy.py apps/intake/tests/test_seed_demo_data.py apps/intake/tests/test_petition_answers.py --ds=config.settings.test -q`. Expected: fail (`ImportError` on the new names; the four-tuple; `PASSES` `KeyError`; no `open_on`; `"none"` a 400).
- [ ] **Step 3: Implement**, all in this one commit (`SC` §3.2–3.3: the seed lands no later than `calculate()` reading `debt_nature`, and `PASSES` lands with the first outcome that can reach it):
  - the constants and the three functions;
  - `PASSES` (4d-R1);
  - `calculate()`'s routing and `open_on` (4d-R2, 4d-R27);
  - `CHOICE_KEYS["duty_category"]`'s `"none"` (D9);
  - the `help_text`s and `0007` (4d-R11);
  - the docstrings;
  - `DEBT_NATURE_DEFAULTS` and `answer_household`'s default (4d-R22);
  - `PETITION_DEFAULTS` and its comment ("…the hazard No, the rent No, and line 16 consumer with both military questions No");
  - `_petition`'s three keys and docstring;
  - `PersonaPetition`'s three typed keys (`debt_nature: 'consumer' | 'business' | 'neither'`, `disabled_veteran` and `reservist` `YesNo`) and `gates()`'s three values;
  - the `MeansOutcome` union's three literals.
  `fillPetitionQuestions` names each step 1 radio and never loops `persona.petition` (`wizard.page.ts:141-159`), so the new keys touch no journey until Task 9.
- [ ] **Step 4: Run the blast radius.**
  - The 45 files that call `answer_household`, the `finish_intake`/`answer_petition` callers, `apps/forms/tests/test_oracle_tier3.py`, `test_api_readback.py` and `apps/audit/tests/test_upl_compliance.py`.
  - Expected red, and fixed here:
    - a test that pins Form 101's `Yes Go to line 17` blank on a built session now prints `/On`. Re-pin it, or pass `debt_nature=None` where the test is about absence;
    - a test that asserts no `PetitionAnswers` record on an `answer_household` session passes `debt_nature=None`.
  - An added pin, not a red (E10: tier 3 asserts only listed keys, `test_oracle_tier3.py:1664-1700`): `_petition_boxes` (`test_oracle_tier3.py:190-214`), which the persona Form 101 blocks spread, gains `"Yes Go to line 17": "/On"` and `"No Go to line 16b": ""` once, not in six blocks.
  - Record the count.
- [ ] **Step 5: Run** `check`, `makemigrations --check --dry-run`, `ruff check` on every touched file, `ruff format --check` on `0007`, and `fe.sh npx tsc -p tsconfig.app.json --noEmit`.
  - See-it-fail: swap the not-consumer and veteran branches in `route_outcome`, and show `test_route_outcome_follows_the_supps_order[business-with-stale-military]` fail.
  - Drop `called_to_duty` from `military_question_open`, and show its case of `test_an_open_military_question_…` fail.
  - Drop `line_2_settled` from the exclusion branch, and show `test_a_line_3_claim_waits_for_line_2_to_settle` fail.
- [ ] **Step 6: Commit** `eligibility: three Supp outcomes routed in the form's order, and line 16 answered in the builders, the seed and the personas` with the paths above.

### Task 2: Step 6's gaps, in Complete's list and in the browser's mirror

**Files:**
- Modify:
  - `backend/apps/intake/petition.py`:
    - sentences after `:52` and `:69`;
    - `FORMS_OF_KEY` `:121-126`;
    - `text_shows` `:204-221`;
    - `petition_step_gaps` `:265-304`, its docstring `:266-271` and comment `:274`.
  - `backend/apps/intake/completion.py` `:65-70`, `:122-131`.
  - `frontend/src/constants/copy.ts`: the nine `PETITION_` mirrors beside the existing ones, each `// DRAFT: counsel C-39`.
  - `backend/apps/intake/tests/test_petition_gaps.py`, `test_completion_gaps.py`, `test_completion.py` (`:496-535`, the full pin), `test_petition_frontend_copy.py:102-103`.

The counts don't move with D9 or F10: both only reword (`DETAIL_DUTY_CATEGORY` and `DETAIL_DEBT_NATURE_TEXT`), so `GATE_` stays 10 + 3 = 13 and `DETAIL_` 18 + 6 = 24.

**Interfaces:**
- Consumes: Task 1's `supp_line_3_reached`.
- Produces:
  - `GATE_DEBT_NATURE`, `GATE_DISABLED_VETERAN`, `GATE_RESERVIST`;
  - `DETAIL_DEBT_NATURE_TEXT`, `DETAIL_DEBTS_ON_DUTY`, `DETAIL_CALLED_TO_DUTY`, `DETAIL_DUTY_CATEGORY`, `DETAIL_DUTY_RELEASED`, `DETAIL_DUTY_ENDED` (`OC` §1);
  - `debt_nature_gaps(answers: Mapping) -> list[Gap]`, pure with no measure: the `debts` block's gates, then its details;
  - `SUPP_DETAILS: frozenset[str]`, the five military detail sentences, which Task 4's `requires` and Task 7's `GapsNotice` read.

The block's order is gates first, then details, as step 1's block is:
1. `GATE_DEBT_NATURE` while absent.
2. Under `consumer`: `GATE_DISABLED_VETERAN` while absent.
3. `GATE_RESERVIST` while absent and `supp_line_3_reached`.
4. `DETAIL_DEBT_NATURE_TEXT`: `neither` with a blank text.
5. `DETAIL_DEBTS_ON_DUTY`: consumer, line 2 Yes, follow-up absent.
6. `DETAIL_CALLED_TO_DUTY`: reached, `reservist` Yes, follow-up absent.
7. `DETAIL_DUTY_CATEGORY`: that, `called_to_duty` Yes, no category (`"none"` is an answer, D9).
8. `DETAIL_DUTY_RELEASED`: category `"2"`, the date blank or not MM/DD/YYYY (`is_mm_dd_yyyy`).
9. `DETAIL_DUTY_ENDED`: category `"4"`, the same.

After these comes `debt_nature_text`'s too-long detail: `_too_long(answers, "debts", ["debt_nature_text"], too_wide)`, with `debt_nature_text` added to `measured`.

`text_shows` gains:
- `debt_nature_text` → `neither`;
- the dates → their category under `supp_categories`' condition;
- every military key → its R-D2 reach.

- [ ] **Step 1: Write the failing tests.**
  - `test_petition_gaps.py`:
    - `test_an_unanswered_line_16_is_the_only_debts_gate`;
    - `test_the_military_gates_ask_only_under_consumer`;
    - `test_line_2_yes_yes_asks_no_line_3_gate` (R-D2);
    - `test_line_2_yes_with_its_follow_up_open_still_asks_line_3` (the boundary, `OD`);
    - `test_the_debts_gaps_come_in_one_fixed_order` (every gate and detail at once, the order above);
    - `test_each_military_follow_up_is_a_detail_naming_the_supp`: kind `detail`, `forms == ("form_122a1_supp",)`;
    - `test_a_neither_with_no_words_is_a_form_101_detail`;
    - `test_a_date_that_isnt_mm_dd_yyyy_is_a_detail_under_its_category_only`;
    - `test_military_answers_kept_under_business_raise_no_gap`;
    - `test_none_applies_answers_the_category_question` (D9: no `DETAIL_DUTY_CATEGORY`, no date detail);
    - `test_a_too_long_16c_text_is_a_too_long_detail`: 83 characters, cap 82.
  - `test_completion_gaps.py`:
    - `test_the_debts_petition_gaps_sit_after_the_claims_debts_gaps_and_before_contracts`, on a session with a claims debt gap and a contracts gap;
    - `test_the_debts_petition_gaps_list_on_a_session_with_no_later_claims_gap` (F3/E1): a session whose only gap is the line 16 gate (no Contracts or Codebtors gap) lists `GATE_DEBT_NATURE` at the end of the claims head, before the contracts petition gaps and the tail, with no exception;
    - `test_complete_refuses_an_unanswered_line_16_and_lets_an_open_follow_up_through`.
  - `test_completion.py:496-535`: insert `{"step": "debts", "message": GATE_DEBT_NATURE}` after the `SCANNED_DEBTS` line (`:530`) and before `CONTRACT_GAP_NO_ANSWER` (`:531`), the first `contracts` entry (E7; re-read at the run).
  - `test_petition_frontend_copy.py:102-103`: `GATE_` 10 → **13**, `DETAIL_` 18 → **24**. The `:71-77` set test covers the mirrors once both sides hold them.
- [ ] **Step 2: Run them.** `pt.sh apps/intake/tests/test_petition_gaps.py apps/intake/tests/test_completion_gaps.py apps/intake/tests/test_completion.py apps/intake/tests/test_petition_frontend_copy.py --ds=config.settings.test -q`. Expected: fail (`ImportError`; counts 10/18).
- [ ] **Step 3: Implement** the sentences (each `# DRAFT: counsel C-39`), `FORMS_OF_KEY` (4d-R10), `debt_nature_gaps`, `SUPP_DETAILS`, `text_shows`, the measure and the splice. The splice computes `at_debts = next((i for i, g in enumerate(claims) if g.step in ("contracts", "codebtors")), len(claims))`, with a `len(claims)` default as the existing codebtors splice at `completion.py:128` has (that one matches only `"codebtors"`; with none, at the end), inserts the debts gaps there, then runs the existing contracts splice, whose index is recomputed after the insert. Also update `completion.py`'s docstring and the nine `copy.ts` mirrors. **The mirrors land in this commit**: the `:71-77` test compares both directions.
- [ ] **Step 4: Run the blast radius:** `test_seed_demo_data.py` (no persona has a gate gap), the forms-view callers of `finish_intake`, `test_api_readback.py`, `fe.sh npx vitest run --maxWorkers=2 src/test/reading-level.test.ts src/test/upl-petition-copy.test.ts`, then `check` and `ruff`.
  - See-it-fail: move the splice after Contracts' gaps, and show the ordering test fail. Drop the `len(claims)` default, and show `test_the_debts_petition_gaps_list_on_a_session_with_no_later_claims_gap` fail with `StopIteration`.
- [ ] **Step 5: Commit** `intake: Form 101 line 16 and the Supp's military questions in Complete's list, with the browser's mirror`.

### Task 3: 106Sum line 7, Form 107 line 6 and 106Sum lines 8–9g read line 16

**Files:**
- Modify:
  - `backend/apps/forms/services/derivations.py`: aliases after `:1200`; `ANSWER_BOX_RULES` `:1206-1217`; `_PETITION_PREDICATES` `:1265-1284` (a `key == value` comprehension, which takes `petition_debt_nature_consumer`); a new small dict `_DEBT_NATURE_PREDICATES` for `debt_nature_consumer_or_unanswered`, which no `key == value` row can express, merged into `PREDICATES` (`:1763-1805`) (E12);
  - `data/forms/schemas/form_106sum.json`: `check7` `:214-233` becomes two entries; `conditional_on` on `8` `:235`, `9a` `:252`, `9b` `:269`, `9c` `:286`, `9d` `:303`, `9g` `:320` (all six `debt_nature_consumer_or_unanswered` here; Task 5 re-points `8`, D10);
  - `backend/apps/forms/tests/test_form_101_schema.py:1130-1138` (E3): `test_only_line_15s_and_16as_own_answer_boxes_pass_the_upl_guard` becomes `test_only_the_filers_own_answer_boxes_pass_the_upl_guard_on_any_form`. It collects the derived `legal_review` rules of every registered form (`FORM_REGISTRY`), still `== ANSWER_BOX_RULES`, so adding `debt_nature_consumer` keeps it green, and its comment says the list is nine rules (today only Form 101 has derived `legal_review` boxes: its eight);
  - `data/forms/schemas/form_107.json`: `check6` `:419-438` becomes two entries;
  - `data/forms/field_index/audit/step2_verification.json`: rows 165 (106Sum `check7`) and 166 (107 `check6`), producer `asked:answer:form_101.primarily_consumer_debts`, each replaced by two rows in place;
  - `backend/apps/forms/tests/test_oracle_tier2.py:37`;
  - `backend/apps/forms/tests/test_consumer_debts_and_paid_help.py`: `:12-15`, `:37-41`, `:91-112`, `:152-176`;
  - `backend/apps/forms/tests/test_coverage.py:24-28` (4d-R24);
  - `backend/apps/forms/tests/test_form_106sum_schema.py`, `test_form_107_schema.py`;
  - `backend/apps/forms/tests/test_oracle_tier3.py` (the six `form_106sum` blocks: `:352`, `:542`, `:733`, `:1116`, `:1285`, `:1503`).

**Interfaces:**
- Consumes: Task 1's defaults (personas consumer).
- Produces:
  - the rules `debt_nature_consumer` (in `ANSWER_BOX_RULES`) and `debt_nature_not_consumer`;
  - the predicates `petition_debt_nature_consumer` (Task 4 uses it) and `debt_nature_consumer_or_unanswered`, true unless `debt_nature` is `business` or `neither`.

- [ ] **Step 0: Pre-flight, the tagged split (R-D6).** First register the two aliases (`debt_nature_consumer`, `debt_nature_not_consumer`) and the `ANSWER_BOX_RULES` entry, so the tagged entries name known rules (E4: otherwise `check` fails E007, "unknown derivation rule", for a reason unrelated to R-D6). Then write `test_each_debt_nature_answer_ticks_exactly_one_box_on_the_page` in `test_form_106sum_schema.py`, with 106Sum's and 107's tagged entries in place:
  - for `consumer`, `business`, `neither` and absent: build, `PDFFormFiller().fill()`, then `read_drawn` (`apps/forms/tests/pdf_readback.py`);
  - assert `check7@2:T5` is ticked only for `consumer`, `check7@2:T6` only for `business`/`neither`, and neither for absent.

  Run, in order:
  - `py.sh manage.py check --settings=config.settings.test`. Expected: passes (E003 accepts each tag, E006 counts one widget a binding);
  - `pt.sh apps/forms/tests/test_form_106sum_schema.py::test_each_debt_nature_answer_ticks_exactly_one_box_on_the_page --ds=config.settings.test -q`. Expected: the drawn page ticks exactly one widget;
  - `pt.sh apps/forms/tests/test_oracle_tier1.py -k "form_106sum or form_107" --ds=config.settings.test -q`, which includes the `slow` `test_a_tick_never_spills_into_a_box_the_filer_left_blank` (`test_oracle_tier1.py:327`; `pt.sh` filters no marker). Tier 1's `_box_fill` fills both tagged keys of one name in one draw, two `/V` values on one field, which a one-answer draw can't see (E5). Expected: pass.

  If any fails, stop before Step 1 and report the output to the controller (4d-R7).

  Also confirm from tier 2's run that each tagged binding is its own case, joined on the bare `pdf_field` and its producer, as Schedule I's T28/T29 rows (rows 244, 253) are.
- [ ] **Step 1: Write the failing tests.**
  - `test_consumer_debts_and_paid_help.py`, rewritten against `PetitionAnswers` (S:789), not deleted:
    - the docstring drops "until 4d";
    - `_says` writes `petition.debt_nature` for every form;
    - `test_the_consumer_debts_answer_ticks_the_same_answer_on_every_form`: parametrized `consumer`, `business`, `neither`, absent, across Form 101 16a/16b, 106Sum `check7@2:T5`/`@2:T6` and 107 `check6@3:T6`/`@3:T3`;
    - `test_only_the_filers_own_answer_can_tick_consumer_debts`: asserts each consumer widget is `derived` with `legal_review` true and its rule in `ANSWER_BOX_RULES`, and each not-consumer widget is `derived`, `legal_review` false, rule not in the set.
  - `test_form_107_schema.py`: `test_each_debt_nature_answer_ticks_exactly_one_line_6_box` (drawn, as Step 0).
  - `test_form_106sum_schema.py`: `test_a_business_or_neither_filer_reports_nothing_on_lines_8_to_9g` (D7). For `business` and `neither`, the resolved values hold none of `8`, `9a`–`9d`, `9g`. For `consumer` and absent, they print as today (line 8's Supp-outcome blanking is Task 5's, D10).
  - Tier 3: each persona's `form_106sum` block gains the consumer widget's read (tier 3 keys a tagged widget `<full name>@<page>:<tag>`; its value as tier 3 reads a tick, confirmed from the run).
- [ ] **Step 2: Run them.** `pt.sh apps/forms/tests/test_consumer_debts_and_paid_help.py apps/forms/tests/test_form_106sum_schema.py apps/forms/tests/test_form_107_schema.py --ds=config.settings.test -q`. Expected: fail (`answer:` bindings; 8–9g print).
- [ ] **Step 3: Implement**, in one commit so `forms.E005` never meets a missing name (`SC` §3.5–3.6):
  - the aliases and `ANSWER_BOX_RULES` (already in place from Step 0);
  - the two predicates (`petition_debt_nature_consumer` a `_PETITION_PREDICATES` row, `debt_nature_consumer_or_unanswered` in `_DEBT_NATURE_PREDICATES`);
  - `test_form_101_schema.py`'s widened guard test (E3);
  - the four tagged entries (4d-R7, each with the old entry's `page` and a label naming its box: "Line 7: debts are primarily consumer debts", "Line 7: debts are not primarily consumer debts", and 107's "Line 6: Yes …", "Line 6: No …");
  - the six `conditional_on`s;
  - the addendum rows: each old row is replaced in place by two rows in the tools' format, on the bare `pdf_field`, producers `derived:debt_nature_consumer` and `derived:debt_nature_not_consumer`, `final_verdicts: ["correct"]`, `status: "confirmed"`. Evidence: the field index's T5/T6 (T6/T3) labels, S:176, R-D6, and "the consumer box prints only for the filer's own `consumer`; the other for `business` or `neither`";
  - `test_coverage.py` (4d-R24).
- [ ] **Step 4: Tier 2.** Run `pt.sh apps/forms/tests/test_oracle_tier2.py --ds=config.settings.test -q` and re-pin `ASSERTED_CASES` from its count. Expected **1879**. Comment clause: "+ 2 (4d Task 3): 106Sum check7 and Form 107 check6 each become two tagged bindings (derived:debt_nature_consumer, derived:debt_nature_not_consumer) in place of asked:answer:form_101.primarily_consumer_debts, each pair through two hand addendum rows: (−1 + 2) × 2, 1877 + 2 = 1879."
- [ ] **Step 5: Run** Step 2's command plus:
  - `test_oracle_tier1.py`, `test_oracle_tier2.py`, `test_oracle_tier3.py`, `test_checks.py`, `test_printed_page.py`, `test_coverage.py`, `test_rule_fixes.py`;
  - the six byte-compare tests (Global Constraints);
  - then `check`, `ruff`, and prettier `--check` on the three JSON files.
  - Expected: all pass, `known_defects.json` `[]`.
  - See-it-fail: remove `debt_nature_consumer` from `ANSWER_BOX_RULES`, and show the 106Sum consumer case print blank.
- [ ] **Step 6: Commit** `forms: 106Sum line 7 and Form 107 line 6 print the filer's line 16 answer, and 106Sum lines 8-9g go blank for non-consumer debts`.

### Task 4: Form 122A-1Supp's schema, its tool, `applies` and `requires`

**Files:**
- Create:
  - `data/forms/field_index/tools/build_form_122a1_supp.py`, on `build_form_101a.py`'s shape (`BINDINGS`, `_field()`, `schema()`, `addendum_rows()`, `owned()`, `merged()`, `dumps()`, `main()`), keyed by `full_name` and tag, never by label (`build_form_101a.py:85-89` exits on a label two widgets share);
  - `backend/apps/forms/tests/test_form_122a1_supp_generator.py` (the `test_form_122a2_generator.py:33` pattern) and `backend/apps/forms/tests/test_form_122a1_supp_schema.py`.
- Modify:
  - `data/forms/schemas/form_122a1_supp.json` (written by the tool) and `step2_verification.json` (the tool owns its nine rows only; the header's two bindings, `Debtor1.Name` and `Bankruptcy District Information`, stay asserted by their `verification.json` rows, E13);
  - `derivations.py` (`_SUPP_PREDICATES`; the rule `supp_duty_category` and its `ANSWER_BOX_RULES` entry, 4d-R26; `PREDICATES` `:1763-1805`);
  - `backend/apps/intake/models.py:942-949`: `RADIO_KEYS` gains `disabled_veteran`, `debts_on_duty`, `reservist`, `called_to_duty` (4d-R26);
  - `backend/apps/forms/tests/test_form_101_schema.py`: the widened guard test's comment says ten rules;
  - `backend/apps/forms/services/answer_records.py:190-215` (4d-R9);
  - `backend/apps/forms/registry.py:259`: the row becomes `PacketForm(_never, _needs_supp_answers)`. `applies` stays `_never` in this task (E2): Task 5 flips it to `_supp_applies` beside `_122a2_applies`, and deletes `_never` (`:62-64`);
  - `test_oracle_tier2.py:37`;
  - `backend/apps/forms/tests/test_registry.py` (new direct cases; `:153-156`'s rewrite is Task 5's, E2);
  - `test_printed_page.py:149-152` (`_values`'s docstring, and its Supp values once personas print `CheckBox2`, `CheckBox3`, `CheckBox5`);
  - `test_part_fixes.py:85` (the comment);
  - `data/forms/field_index/audit/form_122a1_supp.unbound.json` (the eight names leave it).

**Interfaces:**
- Consumes: Task 1's helpers and `SUPP_OUTCOMES`; Task 2's `debt_nature_gaps`, `SUPP_DETAILS`, `GATE_*`; Task 3's rules and `petition_debt_nature_consumer`.
- Produces:
  - `_supp_applies(session) -> bool`: stored means test with `outcome in SUPP_OUTCOMES`;
  - `_needs_supp_answers(session) -> None`: `PreconditionMissing(<first>, step="debts")`, where `<first>` is the first of `debt_nature_gaps(petition_answers_of(session))` that is a gate or in `SUPP_DETAILS` (lazy import of `apps.intake.petition`). `step="debts"` is written as a literal, never `step=gap.step`: `test_rule_fixes.py:60-80` reads `step=` only as a literal in the AST, so a computed step passes the tests and drops the fix check (E14);
  - the predicates of 4d-R8 and the rule `supp_duty_category` (4d-R26).

- [ ] **Step 0: Pre-flight, the Supp's tagged pair (R-D6, E5).** With the tool's first draft writing `form_122a1_supp.json` (the `CheckBox2@1:T7`/`@1:T6` pair at least; the Task 3 aliases exist), run `py.sh manage.py check --settings=config.settings.test`, then `pt.sh apps/forms/tests/test_oracle_tier1.py -k form_122a1_supp --ds=config.settings.test -q`, including the `slow` `test_a_tick_never_spills_into_a_box_the_filer_left_blank`. The Supp is registered, so tier 1 covers it whatever `applies` says. If either fails, stop before Step 1 and report (4d-R7).
- [ ] **Step 1: Write the failing tests.**
  - `test_form_122a1_supp_generator.py`:
    - `test_the_supps_schema_is_what_the_tool_writes`;
    - `test_step2_verification_is_what_the_tool_writes`: byte for byte.
  - `test_form_122a1_supp_schema.py`:
    - `test_the_supps_line_1_ticks_exactly_one_box`: drawn, for the four `debt_nature` values;
    - `test_line_2_yes_yes_prints_no_line_3_box`: a stored line 3 claim under line 2 Yes/Yes resolves no `CheckBox5`–`7`, `Date1` or `Date2`;
    - `test_each_follow_up_prints_only_under_its_own_yes`;
    - `test_part_2_prints_nothing_under_business_or_neither`;
    - `test_a_date_prints_only_under_its_category_and_only_as_mm_dd_yyyy` (`"13/45/20"` blank, `"03/14/2026"` prints);
    - `test_none_applies_ticks_no_category` (D9): under `called_to_duty` Yes and `duty_category` `"none"`, `CheckBox7`, `Date1` and `Date2` resolve blank and nothing raises `UnmappedChoice`;
    - `test_the_category_box_ticks_only_the_filers_own_category`: `CheckBox7` is `derived:supp_duty_category`, `legal_review` true, its rule in `ANSWER_BOX_RULES`;
    - `test_the_amended_box_debtor_2_and_case_number_stay_unbound`;
    - `test_every_box_the_tool_binds_is_on_the_index`.
  - `test_registry.py`: `test_supp_applies_reads_the_stored_outcome`, calling `_supp_applies` directly (E2: the registry row stays `_never` here). Each of the three stored outcomes is true; `at_or_below_median`, `presumption`, `None` and no means test are false. (`test_registry.py:153`'s `test_122a1_supplement_follows_the_supp_outcomes` moves to Task 5, where the row flips.)
  - `test_registry.py`: `test_the_supp_refuses_its_first_open_question_on_the_amounts_owed_step`, calling `_needs_supp_answers` directly (line 2 No, a category `"2"` with no date → `DETAIL_DUTY_RELEASED`, `step="debts"`).
  - `test_registry.py`: `test_a_line_3_claim_with_line_2_open_keeps_the_supp_out` (R-D2 boundary, F2: line 2 Yes, `debts_on_duty` absent, line 3 Yes/Yes/"3"). `MeansTest.calculate()` on the session gives `cannot_work_out` above the median and `at_or_below_median` below, and `_supp_applies` is false for both. The 122A-2 refusal on this path is Task 5's (`FORM_122A2_MILITARY_OPEN`).
- [ ] **Step 2: Run them.** `pt.sh apps/forms/tests/test_form_122a1_supp_generator.py apps/forms/tests/test_form_122a1_supp_schema.py apps/forms/tests/test_registry.py --ds=config.settings.test -q`. Expected: fail (no tool; no `_supp_applies` or `_needs_supp_answers`).
- [ ] **Step 3: Implement**, the schema first in the same commit (`SC` §3.4: `applies` never turns on before line 1 and Part 2 are bound):
  - the tool. `template_version` is the PDF's sha256 (`0ef03a89…1cc`, unchanged), `"groups": {}`, the header's two bindings as today, plus 4d-R7's `CheckBox2` pair and 4d-R8's seven (`CheckBox7` through `derived:supp_duty_category`). It owns exactly its nine `form_122a1_supp` rows in `step2_verification.json` (none exist today), and places them in the early block, never after `list_of_creditors`; the header's rows stay in `verification.json` (E13);
  - run it with `venv-mac/bin/python -I`;
  - the predicates; `supp_duty_category` and its `ANSWER_BOX_RULES` entry; `RADIO_KEYS`'s four keys; the date blanking; `_supp_applies`, `_needs_supp_answers` and the row's `requires` (its `applies` stays `_never`, E2).
- [ ] **Step 4: Tier 2.** Re-pin from the run. Expected **1888**. Comment clause: "+ 9 (4d Task 4): Form 122A-1Supp's line 1 pair (CheckBox2@1:T7, @1:T6), CheckBox3-CheckBox6, CheckBox7 (derived:supp_duty_category), Date1 and Date2, each asserted through one of the nine rows build_form_122a1_supp.py writes; its two header bindings stay counted by their verification.json rows, 1879 + 9 = 1888." `CheckBox7` through a rule is still one box with one binding key, so 4d-R26 moves no count.
- [ ] **Step 5: Run** Step 2's command plus tier 1–3, `test_checks.py`, `test_printed_page.py`, `test_part_fixes.py`, `test_box_background.py`, `test_petition_radio_keys.py`, `test_list_of_creditors_template.py` (it reads `step2_verification.json`, `:64-66`, E13), `test_form_101_schema.py` among the five other byte-compare tests, `test_rule_fixes.py`, `check`, `ruff`, `ruff format --check` on the two new Python files, and prettier on the JSON.
  - See-it-fail: give `CheckBox5` the predicate `petition_debt_nature_consumer`, and show `test_line_2_yes_yes_prints_no_line_3_box` fail.
- [ ] **Step 6: Commit** `forms: Form 122A-1Supp prints line 1 and Part 2 as the form routes them, and refuses its open answers on the Amounts Owed step`.

### Task 5: 122A-2 and 122A-1 follow the outcome (the routing readers)

**Files:**
- Modify:
  - `registry.py`: `_above_median` `:97-107` stays; new `_122a2_applies`; `:259` (`_never` → `_supp_applies`, E2) and `_never` `:62-64` deleted; `:260`; `_needs_the_122a2_questions` `:224-238`; `_needs_means_test_and_form_122a2` `:241-245`;
  - `derivations.py`: `means_result_box` beside `_median_comparison` `:598-610`; `DERIVATIONS` `:1408`; `RULE_FIXES`; `means_parts_1_and_2_print` and `summary_line_8_prints` (D10, 4d-R6) in `PREDICATES`;
  - `data/forms/schemas/form_122a1.json`: `CheckBox1` `:41-60`; 37 `conditional_on`s;
  - `data/forms/schemas/form_106sum.json`: `8` (`:235`)'s `conditional_on` → `summary_line_8_prints` (D10);
  - `test_form_106sum_schema.py`; `test_registry.py:153-156` (the moved test);
  - `backend/apps/eligibility/services/means_test_calculator.py`: docstring `:55-64` and reply `:100-109` gain `open_on`; `backend/apps/intake/views.py:330-341` (the calculate docstring); `backend/apps/forms/views.py` `_means_reply` `:214-230` (4d-R27);
  - `step2_verification.json` row 189 (`form_122a1` `CheckBox1`, producer → `derived:means_result_box`);
  - `backend/apps/intake/means_page.py`: `applies` `:242`; `gap` `:252`; the reply's `open_on` beside `:285` (4d-R27);
  - `backend/apps/forms/tests/means_pair.py:11-14`;
  - `test_form_122a1_schema.py` (`:199-205`, `:216-232`);
  - `test_means_hold.py` (the invariant `:242-327`);
  - `test_oracle_tier3.py` (three synthetic sessions after `:1824-1840`);
  - `apps/intake/tests/test_means_test_api.py`.

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces:
  - `_122a2_applies(session) -> bool`: `_above_median(session) and session.means_test.outcome not in SUPP_OUTCOMES`;
  - `FORM_122A2_MILITARY_OPEN` (`OC` §2);
  - the rule `means_result_box`;
  - the predicates `means_parts_1_and_2_print` and `summary_line_8_prints`;
  - `open_on` on the three replies, and `means_page`'s Amounts Owed `gap` (4d-R27).

`_needs_the_122a2_questions` gains, before `read_tables` (`:227`):
1. `GATE_DEBT_NATURE` while `debt_nature` is absent (B32, 4d-R4);
2. then `FORM_122A2_MILITARY_OPEN` while `military_question_open` (D3);
each with `step="debts"` written as a literal (E14).

`_needs_means_test_and_form_122a2` (name kept, since tests monkeypatch and import it; docstring now "waits for its partner, 122A-2 or the Supp") runs 122A-2's `build_parts` + `check()` when `_122a2_applies`, else the Supp's when `_supp_applies` (D4).

- [ ] **Step 1: Write the failing tests.**
  - `test_means_hold.py`:
    - the invariant `test_an_above_median_filers_122a1_and_122a2_never_print_incomplete` gains three cases (S:791):
      - `business` above: 122A-2 `NotInPacket`, 122A-1 prints box 1 with no Part 1–2 key;
      - `military_exclusion` above: 122A-1 box 3;
      - `debt_nature` unanswered on a session completed before 4d: build it with `finish_intake`, then call `answer_petition(session, debt_nature=None, disabled_veteran=None, reservist=None)` to remove the keys `finish_intake`'s `PETITION_DEFAULTS` wrote (E18), and set `status` by hand. `build_parts("form_122a2")` refuses `GATE_DEBT_NATURE` `step="debts"`, and so does 122A-1.
    - `test_a_supp_outcome_never_ticks_box_2_and_never_holds_for_122a2`: each of the three outcomes, above and below the median;
    - `test_an_open_military_question_holds_both_forms_in_its_own_sentence`: through the forms views, on a completed session above the median with `disabled_veteran` "yes" and `debts_on_duty` absent, parametrized with line 3 No and with line 3 Yes/Yes/"3" (F2: the claim waits for line 2); both forms refuse with `FORM_122A2_MILITARY_OPEN`, `step="debts"`, and the packet holds 122A-2 and no Supp;
    - `test_122a1_waits_for_the_supp_in_the_supps_own_words` (F7, D4): a completed session above the median, line 2 No, line 3 Yes/Yes/"2" and no `duty_released_on`. Generate 122A-1 → 422 with `DETAIL_DUTY_RELEASED`, `step="debts"`. Type the date (`answer_petition`, never a PATCH) → 122A-1 prints box 3 (`/Does not apply`). See-it-fail: delete the Supp branch of `_needs_means_test_and_form_122a2`, and show this test fail;
    - `test_a_stale_presumption_row_routes_by_the_recalculated_outcome` (R-ROUTE):
      - Store a `presumption` row on a completed session.
      - Then write `business` with `answer_petition(session, debt_nature="business")`, never a session PATCH: a PATCH reopens the intake, and Generate All would refuse "Finish your intake" before any routing.
      - Assert `session.status == "completed"` before calling Generate All.
      - Expected: Generate All's `generated` holds `form_122a1_supp` and no `form_122a2`, and 122A-1's stored `CheckBox1` is `/No Abuse`;
      - and, on the same stale row before Generate All (F15): the completed intake's packet list (`GET /api/forms/packet/`) holds `form_122a1_supp` and no `form_122a2` (Task 5 writes no Mark as Filed assertion; Task 6 adds the per-row `MEANS_SUPP_PAIR_REFUSAL` assertion to this test, with the tie);
    - `test_an_unfinished_intakes_packet_reads_the_stored_row`: the same, intake in progress, packet list still holds 122A-2 (as today);
    - `test_a_row_saved_before_3h1_routes_as_today`: `outcome` `None` above → 122A-2 applies, box 2.
  - `test_form_122a1_schema.py`:
    - `test_a_supp_outcome_prints_only_the_header_and_its_box`: keys are exactly `Debtor1.Name`, the district and `CheckBox1`;
    - `:216-232`'s parametrization reads the new keys.
  - `test_form_106sum_schema.py`: `test_106sum_line_8_is_blank_whenever_122a1_line_11_is` (D10): over the seven stored outcomes and no means test, crossed with `consumer`, `business` and absent, whenever `Debto1.Quest11` is absent from 122A-1's resolved values, `8` is absent from 106Sum's; on the `consumer` row, `8` is present exactly when `Debto1.Quest11` is. (One-directional on purpose: a stored non-Supp row beside `business`, which recalculation never leaves, prints line 11 while D7 blanks line 8.)
  - `test_registry.py`: `test_122a1_supplement_follows_the_supp_outcomes` (moved from Task 4, E2): each of the three stored outcomes puts it in the packet; `at_or_below_median`, `presumption`, `None` and no means test leave it out.
  - `test_means_test_api.py`:
    - `test_the_page_doesnt_ask_a_non_consumer_or_excluded_filer` (`applies` false for each Supp outcome above the median);
    - `test_the_page_holds_continue_on_the_amounts_owed_question` (4d-R27): above the median with `debt_nature` absent, the GET's `gap` is `GATE_DEBT_NATURE` and `open_on` is `"debts"`; with `debts_on_duty` open, `FORM_122A2_MILITARY_OPEN`; with every answer given, `open_on` is null and `gap` is `means_test_gaps`' as today.
  - `apps/eligibility/tests/test_means_test_calculator.py` (the calculate reply) and `apps/forms/tests/test_form_views.py` (the packet reply): `test_the_replies_say_when_the_result_waits_on_amounts_owed`: the calculate reply and `GET /api/forms/packet/` carry `open_on` `"debts"` on that path, null otherwise, and null for a row saved before 4d.
  - Tier 3, on the 101A synthetic precedent (`:1824-1840`), each asserting the packet length and the boxes:
    - `test_a_non_consumer_filer_gets_the_supp_and_box_1`;
    - `test_a_disabled_veteran_gets_the_supp_and_box_1`;
    - `test_a_reservist_gets_the_supp_and_box_3`.
- [ ] **Step 2: Run them.** `pt.sh apps/forms/tests/test_means_hold.py apps/forms/tests/test_form_122a1_schema.py apps/forms/tests/test_form_106sum_schema.py apps/forms/tests/test_registry.py apps/forms/tests/test_oracle_tier3.py apps/intake/tests/test_means_test_api.py apps/eligibility/tests/test_means_test_calculator.py apps/forms/tests/test_form_views.py --ds=config.settings.test -q`. Expected: fail.
- [ ] **Step 3: Implement**, all together (`SC` §3.1: 122A-2 never leaves a packet before box 1 learns the outcome, and 122A-1 never refuses on a 122A-2 that left):
  - `_122a2_applies` and the registry row; the Supp row's `applies` → `_supp_applies`, and `_never` deleted (E2);
  - the two refusals;
  - `summary_line_8_prints` and 106Sum `8`'s re-pointed `conditional_on` (D10);
  - `open_on` on the calculate reply, `_means_reply` and `means_page`, and `means_page`'s gap override (4d-R27);
  - the 122A-1 `requires`;
  - `means_result_box` (`RULE_FIXES` `{"step": "review"}`, as `median_comparison`'s);
  - `CheckBox1`'s choices (4d-R5);
  - the 37 predicates (4d-R6);
  - the re-keyed row (evidence adds "box 3 for a line 3 exclusion (D1, B33)");
  - `means_page`'s `applies = is_above_median(...) and result["outcome"] not in SUPP_OUTCOMES`;
  - `means_pair.box_1_state`.
  `FORM_122A2_MILITARY_OPEN` and its `copy.ts` mirror `MEANS_MILITARY_OPEN` land together, with a `test_means_copy.py` row and `upl-means-test-copy.test.ts`'s `NAMES`, `EXACT_WORDS` and `counselMark` (a C-39 branch for the 4d names: the regex takes one `C-\d+`, `:786-788`).
- [ ] **Step 4: Tier 2** is unchanged at **1888**: row 189's re-key is −1 + 1 = 0, and D10's `conditional_on` on 106Sum `8` is not in tier 2's (box, binding key), + 0. 1888 + 0 + 0 = 1888. Run it to confirm.
- [ ] **Step 5: Run** Step 2's command plus `test_means_mark_filed.py`, `test_filed_before_means_test_migration.py`, `test_form_122a2_prints.py`, tier 1/2, `test_checks.py`, the six byte-compare tests, `apps/eligibility/tests/test_means_copy.py`, `fe.sh npx vitest run --maxWorkers=2 src/test/upl-means-test-copy.test.ts src/test/reading-level.test.ts`, then `check` and `ruff`.
  - See-it-fail: make `_122a2_applies` return `_above_median(session)` alone, and show the stale-row test fail with both forms in the packet. Delete the `elif _supp_applies` branch, and show `test_122a1_waits_for_the_supp_in_the_supps_own_words` fail (F7). Point 106Sum `8` back at `debt_nature_consumer_or_unanswered`, and show the D10 test fail for `veteran_exemption`.
- [ ] **Step 6: Commit** `forms: 122A-2, the Supp, 122A-1's box, its Parts 1-2 and 106Sum line 8 follow the stored outcome; 122A-1 waits for 122A-2 or the Supp`.

### Task 6: Form 122A-1 and the Supp file together

**Files:**
- Modify:
  - `backend/apps/forms/views.py`: `MEANS_PAIR` `:64`; `MeansPairTie` `:75`; `MEANS_PAIR_REFUSAL` `:86`; `_FAILURE_SENTENCES` `:110-122`; `mark_pair_filed` `:507-580`; `mark_filed` `:630-665`;
  - `frontend/src/constants/copy.ts` (`MEANS_SUPP_PAIR_REFUSAL`);
  - `apps/eligibility/tests/test_means_copy.py`, `frontend/src/test/upl-means-test-copy.test.ts`;
  - `test_means_mark_filed.py`, `test_means_hold.py`.

**Interfaces:**
- Produces:
  - `_means_partner(session) -> str | None`, after `_prepare`: `"form_122a2"` if in `packet()`, else `"form_122a1_supp"` if in it, else `None`;
  - `class SuppPairTie(Exception)`, mapped to `MEANS_SUPP_PAIR_REFUSAL`;
  - `MEANS_FORMS = ("form_122a1", "form_122a2", "form_122a1_supp")`.

The changes:
- `mark_filed` enters the tie for any unfiled `MEANS_FORMS` row. When the row is 122A-1 or the partner and the other is unfiled, it raises `MeansPairTie` (partner 122A-2) or `SuppPairTie` (partner the Supp), after `_prepare`'s refusals and before the form's own.
- `mark_pair_filed` resolves `("form_122a1", partner)`, partner first. With no partner it keeps today's below-median behaviour (122A-2 refused as not in the packet). Its reply's `forms` and `message` name the pair it filed ("Form 122A-1 and Form 122A-1Supp marked as filed with court").
- `stored_box_2` needs no change: box 3 reads `False`, and `MEANS_FILED_MISMATCH` shows only while 122A-2 is in the packet. Its true value feeds D11's notice (Task 7, 4d-R18).

- [ ] **Step 1: Write the failing tests** (`test_means_mark_filed.py` and `test_means_hold.py`):
  - `test_marking_122a1_alone_is_refused_while_the_supp_is_unfiled`;
  - `test_marking_the_supp_alone_is_refused_while_122a1_is_unfiled`;
  - `test_mark_pair_filed_files_122a1_with_the_supp`: both filed, reply names both, 122A-1 `CheckBox1` `/No Abuse`;
  - `test_a_supp_date_gap_refuses_the_pair_and_writes_nothing`, parametrized over two cases (line 2 No in both). In each, the 422 names `form_122a1_supp`, `step="debts"`, and both rows are unchanged:
    - category 4 with no date (`DETAIL_DUTY_ENDED`);
    - category 2 with `"13/45/20"` (`DETAIL_DUTY_RELEASED`);
  - `test_an_open_line_2_answer_refuses_the_122a2_pair_and_writes_nothing` (F2: R-D2's boundary, line 2 Yes, `debts_on_duty` open, line 3 Yes/Yes/"3", above the median): `mark_pair_filed` refuses naming `form_122a2` with `FORM_122A2_MILITARY_OPEN`, `step="debts"`, and both rows are unchanged;
  - Task 5's `test_a_stale_presumption_row_routes_by_the_recalculated_outcome` gains its F15 assertion: per-row Mark as Filed on 122A-1 refuses with `MEANS_SUPP_PAIR_REFUSAL`, not `MEANS_PAIR_REFUSAL`;
  - `test_122a1s_partner_is_never_both_forms` (each stored outcome: the partner is 122A-2, the Supp or none, and never both in `packet()`);
  - `test_a_filed_122a1_with_box_3_shows_no_mismatch` (`stored_box_2` false, no 122A-2).
- [ ] **Step 2: Run them.** `pt.sh apps/forms/tests/test_means_mark_filed.py apps/forms/tests/test_means_hold.py apps/eligibility/tests/test_means_copy.py --ds=config.settings.test -q`. Expected: fail.
- [ ] **Step 3: Implement** the partner, the class, the sentence (`# DRAFT: counsel C-39`), the two actions and the `copy.ts` mirror. The mirror lands in this commit, with its `test_means_copy.py` row and `upl-means-test-copy.test.ts` entries.
- [ ] **Step 4: Run** Step 2's command, `apps/forms/tests/test_views*.py` (whatever the run shows naming `mark_pair_filed`), `fe.sh npx vitest run --maxWorkers=2 src/test/upl-means-test-copy.test.ts src/test/reading-level.test.ts`, `check`, `ruff`.
  - See-it-fail: return `"form_122a2"` from `_means_partner` unconditionally, and show the Supp pair test fail.
- [ ] **Step 5: Commit** `forms: Form 122A-1 and Form 122A-1Supp are marked filed together, as the Supp says`.

### Task 7: The browser's outcome words, the dashboard and the gap count

**Files:**
- Modify:
  - `frontend/src/constants/copy.ts`: `MEANS_OUTCOME_NOT_CONSUMER`, `MEANS_OUTCOME_VETERAN`, `MEANS_OUTCOME_MILITARY`, `MEANS_SUPP_PAIR_NOTICE`;
  - `frontend/src/constants/formText.ts`: `FORM_122A1SUPP_AMENDED`;
  - `frontend/src/constants/copy.ts` also: `MEANS_OUTCOME_ANSWER_DEBTS`, `MEANS_DEBTS_STEP_PHRASE` (4d-R27) and `MEANS_FILED_BOX_2_NOW_SUPP` (D11), beside `MEANS_OUTCOME_ANSWER_PAGE` (`:182`), `MEANS_PAGE_PHRASE` (`:186`) and `MEANS_FILED_MISMATCH` (`:172`);
  - `frontend/src/utils/meansOutcome.ts:11-62` (header comment "one of seven"; the `openOn` argument after `tablesGap`, `:32-37`);
  - its three callers: `FormDashboard.tsx:425`, `pages/meansTest/MeansResult.tsx:24` and `components/wizard/MeansTestPreview.tsx:44-47` (the sidebar passes its reply's `open_on`, and the sidebar branch ignores it);
  - `frontend/src/pages/FormDashboard.tsx` (`:159`, `:355-373`, `:420-439`, `:441`, `:445-461`, `:465-474`, `:640-665`);
  - `frontend/src/pages/meansTest/MeansResult.tsx` (the Amounts Owed link, 4d-R27);
  - `frontend/src/components/forms/GapsNotice.tsx:68-75`;
  - `frontend/src/types/api.ts`: `open_on: 'debts' | null` beside each `tables_gap` (`:835`, `:1004`, `:1369`, `:1382`); `:1204-1208` (label, `OC` §5);
  - `backend/apps/intake/tests/test_petition_frontend_copy.py` (E15: `FORM_122A1SUPP_AMENDED`'s pin lands here, with the Supp's own regex);
  - tests: `src/utils/__tests__/meansOutcome.test.ts`, `src/pages/__tests__/FormDashboard.test.tsx`, `src/pages/__tests__/MeansTestPage.test.tsx`, `src/components/forms/__tests__/GapsNotice.test.tsx`, `src/components/wizard/__tests__/MeansTestPreview.test.tsx`, `src/test/upl-means-test-copy.test.ts`, `src/test/fixtures/session.ts`, `src/test/mocks/handlers.ts`.

**Interfaces:**
- Consumes: Task 1's union; Task 2's `PETITION_DETAIL_*` mirrors; Task 5's `open_on` replies; Task 6's `MEANS_SUPP_PAIR_REFUSAL`.
- Produces:
  - `meansOutcomeSentences(outcome, familySize, tablesGap, openOn: 'debts' | null, place)` cases: `'not_consumer'` → `[MEANS_OUTCOME_NOT_CONSUMER]`, `'veteran_exemption'` → `[MEANS_OUTCOME_VETERAN]`, `'military_exclusion'` → `[MEANS_OUTCOME_MILITARY, FORM_122A1SUPP_AMENDED]`. None needs a family size or place. Under `'cannot_work_out'` with no `tablesGap`, `openOn === 'debts'` gives `MEANS_OUTCOME_ANSWER_DEBTS` at `dashboard` and `page`, and the sidebar keeps `MEANS_OUTCOME_ANSWER_SIDEBAR` (4d-R14, 4d-R27);
  - `meansPartnerOf(packet: FormType[]): 'form_122a2' | 'form_122a1_supp' | null` in `FormDashboard.tsx`.

The dashboard changes:
- `MEANS_PAIR` (`:159`) moves into the component, derived as `partner === null ? [] : ['form_122a1', partner]` from `partner = meansPartnerOf(packet)`, read by `isPair` (`:420`), `pairOf` and `handleMarkPairFiled`'s clears (`:363`, `:367`) (E8).
- `hasMeansPair` (`:426`) splits in two (E8):
  - `has122a2 = packet.includes('form_122a2')` keeps today's meaning for `MEANS_FILED_MISMATCH` (`:456`), `answerPathOf` (`:436`) and the 122A-2 pair notice;
  - `partner !== null` gates `pairOf` (`:466`, which today returns `undefined` unless `hasMeansPair`, so the Supp pair's cards would never offer "mark both") and the outcome block (`:640`).
- The outcome block (4d-R13) shows the right notice. The sentence `MEANS_OUTCOME_ANSWER_DEBTS` renders as the split around `MEANS_DEBTS_STEP_PHRASE`, linked to `/intake?step=debts` (the `:441` pattern); on that path no `/means-test` link shows. `MeansResult.tsx` links the phrase the same way on the page.
- `noticeOf` (`:445-461`) returns `MEANS_FILED_BOX_2_NOW_SUPP` for a filed 122A-1 with `stored_box_2 === true` while `partner === 'form_122a1_supp'`, after O11's branch (D11, 4d-R18).
- `answerPathOf` sends a pending Supp card to `/intake?step=debts`, since the Supp has no `/ask` page.
- `GapsNotice`'s `isRefusedForm` matches `PETITION_DETAIL_LANDLORD` or any of the five `PETITION_DETAIL_` military sentences (4d-R10).

- [ ] **Step 1: Write the failing tests.**
  - `meansOutcome.test.ts`: one case per new outcome, with the exact list, at each place; `cannot_work_out` with `openOn` `'debts'` gives `MEANS_OUTCOME_ANSWER_DEBTS` at `dashboard` and `page` and `MEANS_OUTCOME_ANSWER_SIDEBAR` at `sidebar`; a `tablesGap` still wins.
  - `upl-means-test-copy.test.ts`: the three outcome sentences, `MEANS_OUTCOME_ANSWER_DEBTS`, `MEANS_DEBTS_STEP_PHRASE` and `MEANS_FILED_BOX_2_NOW_SUPP` in `NAMES` and `EXACT_WORDS`, `counselMark` C-39, and not in `SAYS_PRESUMPTION` (none says it).
  - `FormDashboard.test.tsx`:
    - `shows a not-consumer filer's result and the Supp notice with no Form 122A-2`;
    - `marks Form 122A-1 and the Supp together`;
    - `sends a refused Supp card to Amounts Owed`;
    - `keeps the 122A-2 pair's notice unchanged`;
    - `sends a result that waits on Amounts Owed to that step` (4d-R27: the sentence's link goes to `/intake?step=debts`, and no `/means-test` link shows);
    - `tells a filed Form 122A-1 with box 2 that its partner is now the Supp` (D11), and `shows the filed-before notice instead when both apply` (O11 wins).
  - `MeansTestPage.test.tsx`: `sends a result that waits on Amounts Owed to that step` (the page's link, 4d-R27).
  - `GapsNotice.test.tsx`: `doesn't count a military follow-up or a service date as a blank answer`.
  - `MeansTestPreview.test.tsx`: `shows the military exclusion's sentences and the closing sentence`, and `keeps the 122A-2 page sentence in the sidebar while the result waits on Amounts Owed` (4d-R14).
  - `test_petition_frontend_copy.py` (E15): `SUPP_PREFIXES = re.compile(r"^export const (FORM_122A1SUPP_\w*)\b", re.M)`, its own regex beside `OWNED_PREFIXES` (`:216`), with `SUPP_QUOTES` holding `FORM_122A1SUPP_AMENDED` and `test_every_supp_quote_is_pinned` comparing the two, plus `test_the_supp_words_are_the_forms_own` (Task 8's twin, whitespace-squeezed, started here with the one constant). `OWNED_PREFIXES` and `QUOTES` stay as they are (`:264-267`).
- [ ] **Step 2: Run them.** `fe.sh npx vitest run --maxWorkers=2 <the seven test files>` and `pt.sh apps/intake/tests/test_petition_frontend_copy.py --ds=config.settings.test -q`. Expected: fail.
- [ ] **Step 3: Implement**, with the words of `OC` §§2–3 and §5, each sentence `// DRAFT: counsel C-39`, plus the fixtures' outcome cases and `open_on` in the fixtures and MSW handlers.
- [ ] **Step 4: Run** Step 2's commands plus `src/test/reading-level.test.ts`, `src/test/accessibility.test.tsx`, tsc, eslint and prettier on the touched files.
  - See-it-fail: make `pairOf` return `undefined` for the Supp, and show `marks Form 122A-1 and the Supp together` fail (E8: `isPair` only partitions Generate All errors, so mutating it can't).
  - Drop the `openOn` branch, and show both `sends a result that waits on Amounts Owed to that step` cases fail.
- [ ] **Step 5: Commit** `frontend: the three Supp outcomes in the sidebar and on the dashboard, and the Supp filed with Form 122A-1`.

### Task 8: Step 6's words, gate copy and question block

**Files:**
- Create:
  - `frontend/src/components/wizard/steps/petition/DebtNatureQuestion.tsx`;
  - its test `frontend/src/components/wizard/steps/petition/__tests__/DebtNatureQuestion.test.tsx`;
  - `frontend/src/components/wizard/steps/petition/debtNatureList.ts` (`debtsByKind`, so the component file exports only a component: `react-refresh/only-export-components`).
- Modify:
  - `frontend/src/constants/formText.ts`: `FORM_101_LINE_16*`, `FORM_122A1SUPP_*`, `STATUTE_*`; `FORM_REVISIONS` `:828-831`;
  - `frontend/src/constants/copy.ts` (`OC` §4);
  - `frontend/src/components/wizard/steps/petition/petitionGaps.ts` (after `:99`), `petition/index.ts`;
  - `frontend/src/components/wizard/WhatDoesThisMean.tsx` (4d-R21) and `__tests__/frame.test.tsx`;
  - `backend/apps/intake/tests/test_petition_frontend_copy.py`: `OWNED_PREFIXES` `:216`, `QUOTES` `:218-238`, Task 7's `SUPP_QUOTES`, the revision pin `:166-190`, a `DEBT_NATURE_KEYS` pin beside `:256-261`, a choices pin beside `:143-150`;
  - `frontend/src/test/upl-petition-copy.test.ts`.

**Interfaces:**
- Consumes: Task 2's `PETITION_GATE_*` mirrors.
- Produces:
  - `DEBT_NATURE_KEYS`: the nine keys, in `PETITION_STEP_OF_KEY` order (`answer_records.py:77-90`: `debt_nature`, `debt_nature_text`, `disabled_veteran`, …), not `models.py`'s, which lists `debt_nature_text` among the text keys (E16);
  - `debtNatureGap(answers: PetitionAnswers): string | null`: the gates of Task 2's block only, so details never hold Continue;
  - `supplementLineThreeReached(answers): boolean`;
  - `debtsByKind(rows: DebtRow[]): Array<{kind: DebtType | null; rows: DebtRow[]}>`;
  - `DebtNatureQuestion` with props `{answers, onChange, rows, touched, onLeave}`, the `RentQuestion.tsx:62-73` shape plus `rows`.

The block, in order:
1. Line 16's legend and three radios named `debt_nature`, values `consumer`/`business`/`neither`, labelled `FORM_101_LINE_16A`/`B`/`C`.
2. Under `neither`, the 16c box: name `debt_nature_text`, `maxLength={PETITION_TEXT_LIMITS.debt_nature_text}`.
3. The C-39 list (4d-R16).
4. Under `consumer`:
   - `MILITARY_FRAMING`;
   - line 2 (`YesNoThenDetails`, name `disabled_veteran`, a `WhatDoesThisMean` labelled `WHAT_DOES_DISABLED_VETERAN_MEAN` holding `STATUTE_DISABLED_VETERAN`), its follow-up `debts_on_duty` (a `WhatDoesThisMean` for homeland defense);
   - where line 3 is reached: line 3 (`reservist`), `called_to_duty`, the categories (radios named `duty_category`: values `'1'`–`'4'` labelled by `FORM_122A1SUPP_CATEGORIES`, then `'none'` labelled `DUTY_CATEGORY_NONE`, DigniFi's words in `copy.ts`, D9), `duty_released_on` / `duty_ended_on` (masked `mmDdYyyy`) and `MILITARY_540_DAYS`.
5. The `HiddenLine`s of 4d-R15, with a local `GATE_BLOCKS` (line 2's follow-up under `disabled_veteran` No among them, F8).

- [ ] **Step 1: Write the failing tests.**
  - `DebtNatureQuestion.test.tsx`:
    - `asks line 16 with nothing chosen`;
    - `asks the military questions only under consumer`;
    - `hides line 3 under line 2 Yes and Yes and keeps its answers behind one line`;
    - `asks line 3 while line 2's follow-up is unanswered`;
    - `lists the debts by kind with no sum or count` (no `$` total, no digit in any heading);
    - `says no amounts are listed when there are none`;
    - `names each definition by its term` (two distinct accessible names);
    - `Delete clears a hidden block's answers`;
    - `keeps line 2's follow-up behind one line under No` (F8: a stored `debts_on_duty` under `disabled_veteran` No shows `HIDDEN_ANSWERS` with Show and Delete);
    - `offers "none applies" after the four categories and asks no date under it` (D9);
    - vitest-axe clean.
  - `petitionGaps` cases in the same file: `debtNatureGap` returns the three gates in order and ignores details.
  - `test_petition_frontend_copy.py`:
    - `OWNED_PREFIXES` widened to `FORM_101_LINE_1[146]\w*|FORM_101[AB]_\w*` only; the Supp prefix keeps Task 7's own regex, `SUPP_PREFIXES`, and its own `test_every_supp_quote_is_pinned` (E15: widening `OWNED_PREFIXES` to `FORM_122A1SUPP_` would break `test_every_eviction_and_hazard_quote_is_pinned`, `:264-267`, which compares it with `QUOTES` alone);
    - `QUOTES` gains the four line 16 constants (`form_b101.pdf`, line 16's page, read at the run);
    - `SUPP_QUOTES` gains the other Supp constants, and `test_the_supp_words_are_the_forms_own` (Task 7's twin) covers them: it matches on whitespace-squeezed text on both sides, since the Supp's text layer splits words ("A re", "Gu ard", "per forming"), still requires the whole sentence, and iterates `FORM_122A1SUPP_CATEGORIES`' values (a record keyed `'1'`–`'4'`, not a string);
    - `FORM_REVISIONS` gains `form_122a1_supp: '12/15'` against `form_b122a-1supp.pdf`'s title line (B54);
    - `test_the_step_6_body_names_exactly_the_keys_step_6_asks` (`DEBT_NATURE_KEYS` = `PETITION_STEP_OF_KEY`'s `debts` keys, compared as tuples, E16);
    - `test_the_choices_step_6_offers_are_the_servers` (`debt_nature`, and `duty_category` with `"none"`, against `CHOICE_KEYS`).
  - `frame.test.tsx`: `a definition with a label is named by it`.
  - A vitest exact-words case for the two `STATUTE_` constants (`OC` §6, re-checked against uscode.house.gov before commit).
- [ ] **Step 2: Run them.** `fe.sh npx vitest run --maxWorkers=2 <the three test files> src/test/upl-petition-copy.test.ts` and `pt.sh apps/intake/tests/test_petition_frontend_copy.py --ds=config.settings.test -q`. Expected: fail.
- [ ] **Step 3: Implement** the words (`OC` §§4, 6), `petitionGaps.ts`'s additions, `debtNatureList.ts`, `WhatDoesThisMean`'s `label`, and the component.
- [ ] **Step 4: Run** Step 2's commands plus `src/test/reading-level.test.ts` and `src/test/accessibility.test.tsx`, tsc, eslint and prettier.
  - See-it-fail: drop `supplementLineThreeReached` from the reservist branch, and show `hides line 3 under line 2 Yes and Yes…` fail.
- [ ] **Step 5: Commit** `frontend: Form 101 line 16 and Form 122A-1Supp's military questions, in the forms' words`.

### Task 9: Amounts Owed asks it, saves it and holds Continue, and the journeys answer it

**Files:**
- Modify:
  - `frontend/src/components/wizard/steps/DebtsStep.tsx`: props `:117-128`; validity `:383-390`; status `:969-975`; render before `:1000`;
  - `frontend/src/pages/IntakeWizard.tsx`: imports `:86`; comment `:188-190`; `'debts'` body `:728-739`; `<DebtsStep>` `:1242-1259`;
  - `frontend/src/components/wizard/steps/__tests__/DebtsStep.test.tsx`, `frontend/src/pages/__tests__/IntakeWizard.test.tsx`;
  - `frontend/e2e/pages/wizard.page.ts`: `walkDebts` `:635-643`, a new public `answerDebtNature` beside `answerRentQuestion` `:649-672` (which is `private`; the scanned-bill journey calls `answerDebtNature` directly, E17);
  - `frontend/e2e/journeys/scanned-bill-journey.spec.ts:129-133`;
  - `docs/testing/persona-briefs/{andres-kettleby,deshawn-mitchell,james-washington,maria-torres,priya-sharma,sarah-chen}.md` (the step 6 line, B38).

**Interfaces:**
- Consumes: Task 8's component, keys and gate.
- Produces:
  - `DebtsStep` props `petition: PetitionAnswers` and `onPetitionChange: (next: PetitionAnswers) => void`;
  - the step 6 body `{debts, claim_answers: {no_debts}, petition_answers: stepPetitionBody(petitionAnswers, DEBT_NATURE_KEYS)}`;
  - `answerDebtNature(petition: PersonaPetition)`, public (E17).

The wiring follows the ContractsStep pattern (`ContractsStep.tsx:132-141`):
- `natureGate = debtNatureGap(petition)`;
- `isValid = gap === null && partialBoxes === 0 && natureGate === null`;
- `shownGap = gap ?? (natureTouched ? natureGate : null)`, in the one `role="status"` region.

The gate lands with the journeys (`SC` §3.7).

- [ ] **Step 1: Write the failing tests.**
  - `DebtsStep.test.tsx`:
    - `holds Continue until line 16 is answered`;
    - `holds Continue for an unanswered military gate under consumer`;
    - `lets Continue through an open military follow-up`;
    - `shows the line 16 gate only once the block is touched or the claims gaps are done`;
    - `asks line 16 after "I have no amounts owed"`.
  - `IntakeWizard.test.tsx`:
    - `step 6 sends every line 16 and military key, null while unanswered`;
    - `step 6 still sends military answers kept under business`;
    - `autosave on step 6 sends nothing more after a save`.
- [ ] **Step 2: Run them.** `fe.sh npx vitest run --maxWorkers=2 src/components/wizard/steps/__tests__/DebtsStep.test.tsx src/pages/__tests__/IntakeWizard.test.tsx`. Expected: fail.
- [ ] **Step 3: Implement** the props, the gate, the body, the comment, and the E2E changes:
  - `walkDebts(persona: Pick<PersonaData, 'debts' | 'petition'>)` calls `answerDebtNature(persona.petition)` before Continue. It checks `input[name="debt_nature"][value=…]`, then `disabled_veteran` and `reservist` by value;
  - the scanned-bill journey calls `answerDebtNature(FILER.petition)` before its `nextStep()` at `:132` (S:760's "untouched" departs: Corrections);
  - each brief gains "Amounts Owed: debts primarily consumer; not a disabled veteran; not a Reservist or Guard member".
- [ ] **Step 4: Run** Step 2's command plus `src/test/accessibility.test.tsx`, tsc, eslint, prettier, then `e2e-one.sh all 4d-t9`. Expected: all nine journeys green (DIG-523 reported if it shows).
  - See-it-fail: drop `natureGate` from `isValid`, and show `holds Continue until line 16 is answered` fail.
- [ ] **Step 5: Commit** `frontend: Amounts Owed asks line 16 and the military questions, and every journey answers them`.

### Task 10: The persona's packets and the whole-chain check

**Files:**
- Modify: `backend/apps/intake/tests/test_seed_demo_data.py`, `backend/apps/forms/tests/test_registry.py`.

- [ ] **Step 1: Write the tests.**
  - `test_seed_demo_data.py`: `test_no_persona_gets_the_supp_and_every_packet_count_is_unchanged`, pinning `:317,356`'s counts and no `form_122a1_supp`.
  - `test_registry.py`: `test_a_packet_holds_122a2_or_the_supp_never_both`, over the seven outcomes.
- [ ] **Step 2: Run** `pt.sh apps/intake/tests/test_seed_demo_data.py apps/forms/tests/test_registry.py --ds=config.settings.test -q`. Expected: pass at once: they pin Tasks 1–6 end to end. See-it-fail: make `_supp_applies` true for `presumption`, and show both fail.
- [ ] **Step 3: Commit** `tests: no persona's packet changes, and a packet never holds both 122A-2 and the Supp`.

### Task 11: CLAUDE.md, the spec amendment, the follow-ups and the gate

**Files:**
- Modify: `CLAUDE.md`, `docs/superpowers/specs/2026-11-18-forms-step4-design.md` (appended block only).

- [ ] **Step 1: Rewrite the gotchas** (`SC` §6, `SP` §8, `SF` §10):
  - "The packet decides which forms a filer gets":
    - 122A-2's `applies` (above the median and the stored outcome not one of the three);
    - the Supp's `applies`/`requires`;
    - delete "122A-1Supp not until step 4";
    - 122A-1's `requires` runs 122A-2's path "when 122A-2 applies", or the Supp's;
    - the 122A-2 gate sentence ("`_needs_the_122a2_questions`, Form 122A-2's `requires()`, runs …") is rewritten in its new order, the two new refusals first (F12): `GATE_DEBT_NATURE` while line 16 is unanswered, then `FORM_122A2_MILITARY_OPEN` while a military question is open, each `step="debts"`; then the missing table, the Income step's gap, the marriage question, the page gaps and `FORM_122A2_LINE_MISSING`, as today;
    - "15–18 forms" stays;
    - the per-form `errors` list gains the Supp's `requires`.
  - "GenerateAll vs single": the per-form precondition list gains the Supp's.
  - "Means test units": seven outcomes; the precedence in `route_outcome`, called only by `calculate()` after the median lookup, a line 3 claim counting only once line 2 is settled (F2) and `"none"` claiming nothing (D9); `PASSES` for the three; 4d-R3; `calculation_details["open_on"]` and the calculate reply's `open_on` (4d-R27).
  - "The means test is the form's arithmetic": the three `meansOutcomeSentences` cases, the `openOn` argument and `MEANS_OUTCOME_ANSWER_DEBTS` (dashboard and page only; the sidebar names no Amounts Owed dependency, B34), C-39 marks, where they render.
  - "The 122A-2 page": `applies` is the outcome's, and the redirect stays; while `open_on` is `"debts"`, the reply's `gap` is `GATE_DEBT_NATURE` or `FORM_122A2_MILITARY_OPEN`, so Continue holds.
  - "The packet decides…": the packet reply's `_means_reply` carries `open_on`; the dashboard's `MEANS_FILED_BOX_2_NOW_SUPP` beside `MEANS_FILED_MISMATCH` (D11).
  - "Forms need a completed intake": the `debts` petition gaps in Complete's order (after the claims Debts block, before Contracts); `Gap.forms` for the five military details; `GapsNotice`'s exact-match exclusion; the Supp pair in Mark as Filed and `mark_pair_filed`.
  - "Seed order": personas seeded before 4d have no `debt_nature`, so Complete and every `_prepare` caller meet `GATE_DEBT_NATURE`; re-create them with `seed_demo_data --reset`. `_petition` writes line 16 consumer and both military questions No.
  - "Autosave sends only real edits": step 6's body gains `petition_answers` (`DEBT_NATURE_KEYS`).
  - "Form 101's answers": step 6 asks them, and E2E selects by their control names; `duty_category` takes `"none"` (D9); `RADIO_KEYS` holds the four military yes/no keys the Supp prints, and `CheckBox7` prints through `supp_duty_category` (4d-R26).
  - "Document upload sits mid-wizard": `scanned-bill-journey` answers line 16 before Continue on Amounts Owed.
  - "Blank, not 0.00": 122A-1 Parts 1–2 blank under the three outcomes; the Supp's boxes print only what the form reaches, `"none"` ticking no category; 106Sum 8–9g blank for non-consumer debts, and 106Sum line 8 also wherever 122A-1 line 11 is blank (`summary_line_8_prints`, D10); the tagged line 7 / line 6 / line 1 pairs.
  - "`field_values`, not `form_data`": `stored_box_2` reads false under box 3.
  - "A new placement needs its addendum row": `derived:debt_nature_consumer` as an example.
  - File Map: `build_form_122a1_supp.py`; `petition/DebtNatureQuestion.tsx`; `answer_household`'s `debt_nature` default in the builders line; `means_lines.py`'s `route_outcome`.
- [ ] **Step 2: Append the SPEC AMENDMENT block** at the spec's end (3g2 precedent `1b8fd61`: later plans read the spec, B-table included). Heading "## Spec amendment, 4d (2026-11-23, owner decisions)". No spec line above the block changes. It has three parts (F5):
  - **Owner decisions**, one bullet per item of the Corrections' owner part, each naming every spec line and B-row it supersedes:
    - D1: S:575, S:578, S:584, S:591; B31 (S:909, "Two new … outcomes"), B33 (S:911); S:784, S:810 ("the two outcomes"), S:587 and S:863 ("the two outcome sentences");
    - D3 (open follow-up → `cannot_work_out` above the median; a line 3 claim waits for line 2, F2): S:207, S:575;
    - D4 (the tie): S:577, S:592, S:594 ("122A-1 prints at once, with the Supp");
    - D7: S:638;
    - D8 (the military sentence): S:584's words;
    - D9 ("none applies"): S:303's category list and S:305;
    - D10 (106Sum line 8 with 122A-1 line 11): S:638;
    - D11 (the filed box 2 notice): none superseded; it is new;
    - R-D2: S:305, S:593's single `consumer` condition;
    - R-D5: S:790's last clause; B53 (S:931, "then `military_exclusion` whatever the income", now read with F2's line 2 condition);
    - R-D6: S:176, S:593;
    - R-ROUTE: S:575–579's readers.
  - **Plan rulings** under their own heading, "Plan rulings (4d plan, recorded for the owner)", each naming what it supersedes: 4d-R3 (D3 widened to every open question; plan ruling, accepted, Ruling L); 4d-R4 (S:576's sentence); 4d-R12 (S:579); 4d-R14 narrowed (S:585: the sidebar names no Amounts Owed dependency) and 4d-R27 (the dashboard and page name Amounts Owed); 4d-R15 (S:298's "disappear"); 4d-R26 (`CheckBox7` through a rule); S:593 and S:767 (counts: 8 names over 16 widgets; tier 2 +11, 1877 → 1888); S:550 and S:810 (packet range 15–18); S:760 (the scanned-bill journey answers line 16); S:303 (dates checked for shape); S:575's precedence position (after the median lookup, 4d-R2); S:806 and S:810 (Form 101 16a–c already bound in 4b; 4d only asks line 16).
  - **A C-39 line** naming the widened scope for counsel: three outcomes and their sentences (D1, D8), D7's and D10's blanking, the tagged split (R-D6), D3's hold and the Amounts Owed sentence (4d-R27), D9's "none applies" label, D11's notice, and the list's adjacency to "Total Amounts Owed" with S:296's reason quoted (F11, 4d-R16).
- [ ] **Step 3: Check.** `pt.sh apps/intake/tests/test_claude_md_asset_order.py --ds=config.settings.test -q` passes, and prettier `--check` passes on both files.
- [ ] **Step 4: The PR gate.** It runs here, and again after the final-review fix wave:
  - `zsh /Users/controlroom/.claude/jobs/bb720722/tmp/4b-sdd/gate.sh 4d`: `ruff check .`, `ruff format --check .` (the pre-existing 63 reported, none new), `check`, `makemigrations --check --dry-run`, the whole backend run and the whole vitest run;
  - `gate_pg.sh 4d`;
  - tsc;
  - `e2e-one.sh all 4d-gate`;
  - `known_defects.json` is `[]`;
  - `ASSERTED_CASES` is 1888;
  - `/opt/local/bin/git log` shows no trailer.
  Report each count through a one-line `printf`. DIG-523 is reported as the known develop failure.
- [ ] **Step 5: List the Plane tickets** for the controller:
  - `NoTableInForce` refusing filers whose outcome needs no figures (4d-R2);
  - 4f must carry `check6`'s two tagged bindings and rows into `build_form_107.py` (`SC` §2.8);
  - 4e's `DebtsStep.tsx` overlap;
  - Andrés's unread `consumer_business_classification: "business"` rows (dropped in 4j).
  The PR housekeeping line says DIG-72 and DIG-121 close with 4d. Nothing is filed for the sidebar line (4d-R14: B34 rules it out) or the filed box 2 notice (built here, D11).
- [ ] **Step 6: Commit** `docs: CLAUDE.md and the step 4 spec's amendment for consumer debts and the Supp`.

## Corrections to the spec (the spec is amended only by Task 11's appended block)

- **D1 (owner).**
  - S:575, S:578, S:584 and S:591 fold line 2 Yes/Yes and line 3's categories into one `military_exclusion` → box 3. The form sends line 2 Yes/Yes to box 1 ("check box 1, There is no presumption of abuse"). Only line 3's categories send the filer to box 3.
  - So there are three outcomes: `not_consumer` and `veteran_exemption` → box 1, `military_exclusion` → box 3. 122A-1 Parts 1–2 are blank for all three.
  - S:584's sentence covers line 3 only. It gains "during the exclusion period" and the form's amended-form sentence (D8), and the veteran route gets its own sentence (`OC` §3).
- **R-D2.** S:305 "Both gates are required" holds only where the form reaches line 3. Under line 2 Yes/Yes, `reservist` is no gate, the Supp's line 3 boxes print blank, and the step hides line 3. S:593's single `consumer` condition becomes one predicate per question (4d-R8).
- **D3 and B16 against S:207.** The military follow-ups are details, not gates. Above the median, an open question gives `cannot_work_out` with a `step="debts"` refusal. A line 3 claim counts only once line 2 is settled, so line 2 open with line 3 claimed is `cannot_work_out` above the median and `at_or_below_median` below (F2). The plan's own widening of D3's two cases to every open question the Supp reaches (4d-R3) is a plan ruling, listed under its own heading below.
- **D9.** S:303's categories gain a fifth answer, `"none"` ("None of these categories applies to me"): no exclusion, the Supp out, `CheckBox7` blank, the means test worked out as usual. `DETAIL_DUTY_CATEGORY` presumes nothing.
- **D10.** S:638 leaves 106Sum line 8 printing CMI on the veteran and reservist routes. It prints only when 122A-1 line 11 prints (`summary_line_8_prints`).
- **D11.** New: a filed 122A-1 with box 2 shows `MEANS_FILED_BOX_2_NOW_SUPP` once its partner is the Supp. Nothing in the spec is superseded.
- **R-D5.** S:790's last clause ("below the median with `business` → below-median outcome") is replaced by B53: `not_consumer` whatever the income.
- **R-D6.** S:176 and S:593 ask for one derived binding per box. Each of 106Sum `check7`, 107 `check6` and the Supp's `CheckBox2` is two tagged bindings, the consumer widget's rule in `ANSWER_BOX_RULES`.
- **D7.** S:638 binds only `check7`. 106Sum lines 8–9g go blank under `business`/`neither`, as the form's "not consumer" box says ("You have nothing to report on this part").
- **D4.** S:577, S:592 and S:594 ("122A-1 prints at once, with the Supp") leave 122A-1 unpaired with the Supp. 122A-1's `requires` runs the Supp's whole path when the Supp applies, and Mark as Filed ties the two.
- **R-ROUTE.** S:575–579's five readers read one stored outcome, after recalculation, and `route_outcome` is called only by `calculate()`. The spec left the source unsaid.

Plan rulings (not owner decisions; for the owner to see):

- **4d-R3.** D3's two named cases widen to every open question the Supp reaches (accepted, Ruling L).
- **4d-R4.** S:576's B32 sentence becomes the gate's sentence, one string.
- **4d-R12.** S:579's "shows the outcome's sentence and continues" becomes the existing redirect.
- **4d-R14 and 4d-R27.** S:585's sidebar gap line is not built (B34). The dashboard and the 122A-2 page say instead that the result waits on Amounts Owed, and link there.
- **4d-R15.** S:298's "disappear" becomes `HiddenLine` Show/Delete (S:177's pattern).
- **4d-R26.** `CheckBox7` prints through `supp_duty_category`, not `petition.duty_category` (S:177, S:593), and `RADIO_KEYS` gains the four military keys (accepted, Ruling L).
- **S:593 and S:767.** "19 unbound widgets all bind" is 8 names over 16 widgets (`CheckBox1`, `Debtor2.Name` and `Case number1` stay blank). Tier 2's 4d total is +11: the Supp +9 (the line 1 pair counts two), and 106Sum and 107 +1 each. 1877 → **1888**, not S:767's "the Supp 9" alone.
- **S:550 and S:810's packet range.** The Supp and 122A-2 are exclusive, so 4d's range stays 15–18. The spec's 15–19 waits for 4e/4h.
- **S:806 and S:810.** Form 101 16a–c were bound in 4b, so 4d only asks line 16.
- **S:760.** The scanned-bill journey isn't untouched: it answers line 16 (Task 9).
- **S:303.** The dates are checked for shape (a detail) and print blank when malformed (B47). Nothing checks 540 days.
- **S:575.** Precedence sits after the median lookup (4d-R2). A not-consumer filer is still refused by `NoTableInForce` (Plane).
- **Stale cites (S → now):**
  - `models.py:188` → `:142` (def), `:184-200` (branch);
  - `means_lines.py:35-38` → `:35-39`;
  - `registry.py:74,236` → `:97-107`, `:260`;
  - `registry.py:218-222` → `:241-245`;
  - `derivations.py:595-609` → `:598-610`;
  - `means_page.py:240` → `:242`;
  - `types/api.ts:638` → `:820-824`;
  - `meansOutcome.ts:41-58` → `:40-62`;
  - `test_oracle_tier1.py:783` → `:931`;
  - `test_oracle_tier2.py:37` "1740" → 1877.

## Self-review

- **Spec coverage.**
  - §6.6 → T2 (gaps), T8 (words, block), T9 (step, journeys).
  - §11.1–11.2 readers:
    - `calculate()` → T1;
    - 122A-2 `applies` and 122A-1 `requires`/box → T5;
    - `/means-test` → T5 (R12);
    - frontend sentences → T7.
  - §11.3 → T4 (schema, `_supp_applies`, `requires`), T5 (the registry's `applies`, hold), T6 (tie).
  - §5.3 → T3 (106Sum, 107), T4 (Supp `CheckBox2`).
  - §5.5 → T3/T4.
  - §18:
    - S:766 → T4 (tier 1 by registration);
    - S:768 → T5 (tier 3 synthetic);
    - S:773 → T3 (one case per value and absent);
    - S:780 → T4;
    - S:784 and S:790 → T1 (R-D5 corrected);
    - S:789 → T3;
    - S:791 → T5;
    - S:792 → T2, T7, T8.
  - B38/B39 → T1, T9, T10. B43 → T8, `OC` §6. B54 → T8. C-39 → every task with words, and `OC`.
  - D9 → T1 (`CHOICE_KEYS`, route), T2 (gaps), T4 (`CheckBox7`, 4d-R26), T8 (the fifth radio). D10 → T3 (D7 half), T5 (combined). D11 → T7. 4d-R27 → T1 (stored), T5 (replies, page gap), T7 (words, links).
- **Order** (`SC` §3, the advisor's coupling).
  - The defaults, seed and `PASSES` land with `calculate()` reading `debt_nature` (T1), before any gate (T2): defaults before a gate are harmless to the backend builders. The journeys register fresh accounts, so E2E is red from T1 (Priya) and T2 (every journey) until T9, as Global Constraints declare (E6).
  - The Supp's registry row keeps `_never` through T4 and flips in T5 beside `_122a2_applies`, `means_result_box` and 122A-1's `requires`, so no commit puts both 122A-2 and the Supp in one packet (E2).
  - 106Sum `8` takes D7's predicate in T3 and the combined one in T5, once `means_parts_1_and_2_print` exists (D10).
  - Gap sentences and their mirrors land together with the count re-pin (T2).
  - Predicates land with the JSON naming them (T3, T4, T5).
  - The Supp schema lands before its `applies` (T4).
  - The Supp's `requires` (T4) lands before 122A-1 reads it (T5).
  - 122A-2's `applies`, 122A-1's `requires` and `CheckBox1`'s rule land together (T5).
  - Rebind, re-key and test rewrite land together (T3).
  - The step 6 gate lands with the journeys (T9).
- **Type consistency.**
  - Outcome strings come from T1, and T5–T7 use them verbatim.
  - The rule names `debt_nature_consumer`, `debt_nature_not_consumer` and `means_result_box` are T3/T5's.
  - The predicate names are 4d-R6/R8's.
  - `GATE_*`/`DETAIL_*` and `SUPP_DETAILS` are T2's, read by T4 and T7.
  - `DEBT_NATURE_KEYS` and `debtNatureGap` are T8's, read by T9.
- **Arithmetic.** `ASSERTED_CASES`:
  - T3: 1877 + (−1 + 2) × 2 = 1879;
  - T4: 1879 + 9 = 1888 (`CheckBox2` ×2, `CheckBox3`–`CheckBox6`, `CheckBox7` through `derived:supp_duty_category`, `Date1`, `Date2`: 2 + 4 + 1 + 2 = 9; the header 0, its rows staying in `verification.json`). 4d-R26 changes `CheckBox7`'s producer, not its count: still one box, one binding key;
  - T5: 1888 + (−1 + 1) re-key of row 189 + 0 for D10's `conditional_on` (not in the key) = 1888;
  - D11 and 4d-R27 are frontend and reply changes, + 0. Final: 1888.
  - Gate and detail counts: 10 + 3 = 13 and 18 + 6 = 24. D9 and F10 reword `DETAIL_DUTY_CATEGORY` and `DETAIL_DEBT_NATURE_TEXT` and add no sentence, so both stay.
  - `ANSWER_BOX_RULES`: 8 today (Form 101's), 9 after T3 (`debt_nature_consumer`), 10 after T4 (`supp_duty_category`).
  - `RADIO_KEYS`: 6 today, 10 after T4 (+4).
  - Outcome pins: `OUTCOMES` 4 + 3 = 7; `route_outcome`'s table gains four rows (the F2 pair, the settled line 2 case and D9's), 12 + 4 = 16.
- **Proportion.** Eleven tasks against about 60 files. The only body written out is `route_outcome`, whose order the tests don't fully determine.

<!-- prettier-ignore-end -->
