# Forms step 3f: the filing fee

- **Status:** drafted 2026-11-02. The owner chose to skip the brainstorming questions, so this spec is written straight from the umbrella. The owner answered its three questions (§17) on 2026-11-02, each with the recommendation the spec was written for; they are listed at the end, under "Owner answers (2026-11-02)". The spec waits for the owner's review.
- **Drawn from:** the step 3 umbrella spec, `docs/superpowers/specs/2026-10-16-forms-step3-design.md` §5.7 (cited `U:<line>`), its rules U §4.1–§4.7, Appendix A's 3f rows (U:741–742, :766, :773, :780, :787) and Appendix B item 7 (U:801). Persona targets come from `docs/superpowers/specs/2026-10-16-forms-step3-personas.md` (cited `PS:<line>`). The 3e2 spec, `docs/superpowers/specs/2026-11-01-forms-step3e2-design.md`, is cited `E2 §<n>`. The fee-waiver scoping note, `.superpowers/forms-step3/scope/fee-waiver.md` in the `forms-step3` worktree (cited `FW:<line>`), holds the sources: 28 U.S.C. § 1930(f), FRBP 1006, the Guide to Judiciary Policy Vol. 4 Ch. 8 § 820, the AO's instructions, the HHS notice and the courts' 150% table, all fetched 2026-10-15.
- **Branch:** `feat/forms-step3f`, from develop `2fd7e6e` (3a1, 3a2, 3e1 and 3e2 merged). The PR targets develop.
- **Section numbers.** A bare `§4` is this spec's own section; the umbrella's are written `U §4`.
- **Tags** such as `[Q21]` trace each part to the umbrella's Appendix A. `[UPL]` is the umbrella's rule that DigniFi gives information, never advice (U:74–80, `docs/UPL_COMPLIANCE.md`).

Inline "**Call (spec author):**" marks each choice this spec makes where the umbrella and the code leave one open. §16 lists them all, and §15 lists every place this spec departs from or adds to §5.7.

## 1. What 3f does

1. **The filer answers Form 101 line 8** `[Q21]`, "How you will pay the fee", in its three options, on a page every filer passes after Complete (§3, §6). The answer is stored encrypted (§4) and prints on `Check Box7` (§8.1).
2. **103B is in the packet exactly when the answer is the waiver** (§7). Changing the answer withdraws it. The routing on `qualifies_for_fee_waiver` and the fee-waiver page's off-ramp are gone, and so is the flag (§9) `[DIG-145]`.
3. **Beside the question, as information** `[Q22]`: the court's limit, 150% of the HHS poverty guideline for the filer's family size, from a new dated table (§5), and the filer's own § 820.20 figure (§6.2). It never says "you qualify". "The court decides" sits beside it. Counsel confirms the words `[C-7]`.
4. **Installments** shows the "get Form 103A from the court" message (§6.3).
5. **103B reads what the wizard already asked** (§8.2): line 1 from the household list, line 2 from Schedule I line 10, line 3 from the 8f answer. Nothing is typed twice. Line 1 fails loud instead of printing "1" `[DIG-223]`.
6. **103B's own questions for a waiver filer**, lines 4, 5, 7 and 9, are asked on the same page under the waiver choice (§6.4). This is owner question 2.
7. **Encryption** `[DIG-279]`. `FeeWaiverApplication`, whose answers were plaintext, is replaced by one encrypted record of the filing fee (§4).
8. **Personas** (§10). DeShawn leaves 103B, so his packet goes from 15 forms to 14. Maria and Sarah keep 103B through their own answer. James and Priya pay in full. Andrés pays in installments.

Nothing in 3f deploys. Production waits for steps 3 to 5 and DIG-146 (U:9).

## 2. How this spec was made

- The owner skipped brainstorming. Every decision §5.7 leaves open is made here as a call. The exceptions are the three that change what gets built with no rule to settle them; those go to the owner (§17).
- **Settled by the umbrella, so not asked:**
  - The filer chooses. Nothing routes or hides on a computed result (U:375–381, U:391).
  - The threshold and the figure are information, and "the court decides" (U:384–388).
  - The answers are encrypted (U:393), and line 1 fails loud (U:395).
  - 103B line 3 reads 8f (U:399), and line 1 counts the household its own way (U:400, E1's `count_fee_waiver_household`).
- **Settled by the sources** (FW:157–188):
  - § 820.20(a)(2) compares Schedule I's total combined monthly income, less non-cash government assistance.
  - § 820.20(a)(3) counts the debtor, the spouse unless separated, and dependents. DigniFi applies it through 3e1's `count_fee_waiver_household` (`household.py:60-70`), which also leaves out a `married_separately` spouse who lives apart without a legal separation. That reading goes to counsel under C-7 (§17).
  - The test is strictly "less than".
  - The court alone decides "unable to pay in installments" (§ 820.20(a)(4)), and paying a preparer never disqualifies (a)(5).
- **The persona targets** fix every outcome in §10 (PS:128–146, :380–386, :617–621, :830–842, :1067–1079, :1390).

## 3. The flow

**Today.** `handleComplete` (`IntakeWizard.tsx:483-516`) runs the means test and sends a filer whose `qualifies_for_fee_waiver` is true (CMI under 60% of the median, `eligibility/models.py:186-188`) to `/fee-waiver`, and everyone else to `/sofa`. The page tells an eligible filer "you may qualify" and asks household size, take-home pay, non-cash help and two "cannot pay" boxes (`FeeWaiverPage.tsx:139-271`). An ineligible filer who reaches it sees only an off-ramp to `/sofa` (`:70`, `:124-135`).

**After 3f.**

- Complete, then the means test as today, then **always** `/filing-fee` (§6), then `/sofa`. No branch reads a computed result.
- `/fee-waiver` redirects to `/filing-fee` (a `Navigate` with `replace`), so an old link still lands.
- The forms dashboard links a refusal whose `page` is `/filing-fee` there (§7).
- **The way back.** The dashboard always shows the filer's line 8 answer, in the form's words, with a "Change how you will pay the fee" link to `/filing-fee`, or "Choose how you will pay the fee" while it is unanswered (§7). That is how a filer withdraws a waiver, or returns to it. **Call (spec author).**
- **The journeys' wait.** `e2e/pages/wizard.page.ts:44-46` waits for `/(forms|fee-waiver|sofa)/` after Complete; it becomes `/filing-fee/`.

**Call (spec author):** a page after Complete, not a wizard step. The page needs a finished Income step for its figure, and the means test already runs at that point. A wizard step would renumber `current_step` again, as 3e2 did. Form 101 line 8 lives with the other post-intake answers (SOFA, the 103B questions), which never reopen a completed intake.

## 4. The record: `FilingFee`

A new model in `apps/intake/models.py`, one-to-one with the session (`related_name="filing_fee"`). Every answer is encrypted. Null means unanswered.

| Field                        | Type                           | Holds                                                       |
| ---------------------------- | ------------------------------ | ----------------------------------------------------------- |
| `payment_choice`             | `EncryptedCharField(20)`, null | `pay_in_full`, `installments` or `waiver` (Form 101 line 8) |
| `income_change_answer`       | `EncryptedCharField(3)`, null  | `yes` / `no` (103B line 4)                                  |
| `income_change_explanation`  | `EncryptedTextField`, blank    | line 4's "Yes. Explain."                                    |
| `installments_explanation`   | `EncryptedTextField`, blank    | line 5                                                      |
| `others_covered_answer`      | `EncryptedCharField(3)`, null  | `yes` / `no` (line 7)                                       |
| `others_covered_who`         | `EncryptedTextField`, blank    | line 7's "Yes. Identify who"                                |
| `expense_change_answer`      | `EncryptedCharField(3)`, null  | `yes` / `no` (line 9)                                       |
| `expense_change_explanation` | `EncryptedTextField`, blank    | line 9's "Yes. Explain."                                    |
| `created_at`, `updated_at`   | as other models                |                                                             |

- **Why not `DebtorInfo`** (U:381): identity rows stay untouched until step 5 (U:88). **Why not `FeeWaiverApplication`:** a filer who pays in full has no application, and the line 8 answer is every filer's (FW:257–258).
- **Withdrawal** (U:379). Moving off `waiver` takes 103B out of the packet (§7). The waiver answers stay stored and return if the filer picks the waiver again. A filed 103B keeps its stored values (DIG-155).

**`FeeWaiverApplication` is removed.** Every answer it held is now asked once, elsewhere:

- household size by the household list;
- take-home pay by Schedule I;
- non-cash help by 8f.

`cannot_pay_full`, `cannot_pay_installments`, `status`, `filed_at` and `decided_at` print nowhere and are read by nothing (FW:126–131). Line 5 now carries the "cannot pay in installments" facts in the filer's own words.

- **Migration.**
  1. Create `FilingFee`.
  2. A data migration gives every session with a `FeeWaiverApplication` a `FilingFee` with `payment_choice="waiver"`, so its packet keeps 103B.
  3. Delete `FeeWaiverApplication`, so its plaintext columns go with it.
- **Reverse.** Recreate the table, and for each `waiver` choice create a bare application with `household_size=1` and everything else empty. The typed answers don't come back; the reverse says so in its docstring.
- **What existing sessions meet after the migration.** **Call (spec author):** this is intended, and the PR's "Before merging" says so, beside re-seeding the personas with `seed_demo_data --reset`.
  - A session that had an application has `waiver`, but no answers to lines 4, 5, 7 and 9. Its 103B is refused, with a link to `/filing-fee`, until the filer answers them.
  - Every other session has no `FilingFee`. Its Form 101 is refused, with the same link, until the filer chooses.
  - Each refusal names the page, and nothing is guessed for the filer.

**The whole fee-waiver API goes with the model.** **Call (spec author).**

- Backend: `FeeWaiverViewSet` and its route (`intake/urls.py:7`, `:16`); `FeeWaiverApplicationSerializer` (`serializers.py:817`); the ignore entry in `backend/conftest.py:12`.
- Frontend: `api.feeWaiver` (`client.ts:511`), its MSW handlers and fixtures, and `FeeWaiverPage.tsx` with its test.
- Tests: every test of the model, page or API is deleted or rewritten. That covers `test_fee_waiver_views.py`, `test_models.py:132-215`, `test_completion.py:1000-1017`, `config/tests/test_urls.py`, and the files the plan finds by grepping `fee_waiver`, `FeeWaiver` and `/fee-waiver`.
- `RULE_FIXES`' `/fee-waiver` pages (`derivations.py:1081-1083`) become `/filing-fee`, with their tests (`test_rule_fixes.py:175`, `test_check.py:257`, `test_form_views.py:402-406`).
- **CSS.** `global.css`'s `fee-waiver-question` and `fee-waiver-checkbox` classes stay: `IncomeInfoStep`, `ExpenseInfoStep` and `HouseholdList` use them too.

**103B's lines 17–19 stay where they are.** `check_17`–`check_19` are already asked at `/ask/form_103b` and stored as `FormAnswer` rows. They are plaintext until DIG-168 encrypts `FormAnswer`, and they are step 4's to move. Lines 4–9 go on `FilingFee`, not into `FormAnswer`, because U:87 says nothing new goes into `FormAnswer` until DIG-168. So a waiver filer answers on two pages: `/filing-fee`, and `/ask/form_103b` as today. **Call (spec author).**

**Call (spec author):** drop the table in 3f instead of keeping it one release. The usual "one release" keeps a record nothing else holds. Here every value is held elsewhere or printed nowhere, and keeping it would keep the plaintext DIG-279 names. If the owner answers question 1 with a typed take-home figure (§17), `FilingFee` gains an encrypted `monthly_take_home_pay` and the rest stands.

## 5. The poverty table `[Q22]`

**A new dated table.** `PovertyGuideline(DatedTable)` in `apps/districts/models.py`, beside `MedianIncome` (`:60`), for the 48 contiguous states and DC (ILND needs no other; FW:183):

- `first_person` and `each_additional`, whole dollars a year;
- the `DatedTable` fields `effective_date`, `valid_through` and `source_url`.

It holds public data, so it is not encrypted. It is national, so it has no district.

**The 2026 row**, loaded by a data migration, not a fixture, so every database, CI and the Heroku release have it without a new `loaddata` step:

- `first_person` 15,960 and `each_additional` 5,680 (FW:182).
- `effective_date` 2026-01-15, the Federal Register publication date (91 FR 1797, doc. 2026-00755).
- `valid_through` 2027-01-31.
- `source_url` the Federal Register notice.

**Which date counts (FW-5).** The AO's instructions compare against the guideline "last published" (FW:173), so the row takes effect on its publication date.

- HHS's own effective date was 2026-01-13, and ILNB's packet prints "Updated: 1/01/2026" (FW:181, :185).
- **Call (spec author):** the publication date, until the ILNB clerk says otherwise. The umbrella asks for the clerk's answer (U:389). Asking is the owner's action (§17), and a different answer changes only the 2026 row's date and the runbook.

**`valid_through` 2027-01-31.** The guidelines change "each January" (U:102), but the date isn't fixed. January 31 gives HHS the month.

- If the 2027 row isn't loaded by then, the lookup refuses from February 1 (§6.2), as U §4.3 asks.
- **Call (spec author).**

**The court's limit**, for a family of `n`:

```
(first_person + each_additional × (n − 1)) × 1.5 ÷ 12
```

rounded to the cent, half-up. For 2026 this gives the courts' own table exactly (FW:184): 1 = $1,995.00, 2 = $2,705.00, 3 = $3,415.00, 4 = $4,125.00, and $710.00 for each person after.

- The figure meets the limit only when strictly less (§ 1930(f)(1)).
- It lives in a pure function, `poverty_limit_monthly(guideline, family_size) -> Decimal`, in `apps/districts/poverty.py`, and the lookup goes through `in_force(rows, fill_date(), "HHS poverty guidelines")`.

**`docs/REFERENCE_TABLES.md`** gains an "HHS poverty guidelines" section:

- where it is posted (ASPE and the Federal Register);
- when it changes;
- the row DigniFi loads;
- how to add a row, which is a new data migration;
- what a missed change looks like.

**The dead code goes.** `FeeWaiverApplication.qualifies_for_waiver()` and `get_poverty_threshold()` (`models.py:963-987`), with their hard-coded 2024 constants and their tests (`test_models.py:132-215`), go with the model.

## 6. The page: `/filing-fee`

`FilingFeePage.tsx` replaces `FeeWaiverPage.tsx`.

- Its h1 is "How you will pay the filing fee".
- It opens with the saved record, and renders nothing until the read returns, as the fee-waiver page does today (`:36-60`, `:161`).
- It saves on Continue, then goes to `/sofa`.

### 6.1 The question `[Q21]`

Form 101 line 8's words, as a radio group (the words live in `formText.ts`):

- "I will pay the entire fee when I file my petition."
- "I need to pay the fee in installments."
- "I request that my fee be waived."

Nothing is chosen until the filer chooses, and Continue is refused without an answer.

### 6.2 The information beside it `[Q22]` `[C-7]` `[UPL]`

Shown above the choices, for every filer. It uses Form 101's own sentence ("By law, a judge may, but is not required to, waive your fee, and may do so only if your income is less than 150% of the official poverty line that applies to your family size and you are unable to pay the fee in installments") and adds the figures. The plan drafts the final sentences; their content is fixed here:

- **The limit:** "$1,995.00 a month for a family of 1." The family size is `count_fee_waiver_household`, 103B line 1's count. The sentence names the guideline's year and its publication date.
- **The filer's figure:** "Your family's income, as Form 103B counts it from your answers: $1,750.00 a month." This is 103B line 2's total (§8.2): Schedule I line 10 for each person counted, less the non-cash help included in it.
- **"The court decides."** The sentence says the judge also weighs whether the filer can pay in installments.

It never compares the two figures for the filer, never says "qualify" or "eligible", and never suggests a choice. It is marked `DRAFT: counsel C-7` until counsel signs off.

**When a figure can't be shown:**

- **Income step gaps.** If `income_step_gaps` finds a gap (the intake was reopened after Complete), the family size and the figure are unknown. The sentence links to the Income step instead.
- **No table in force.** The lookup logs as `in_force` does. The sentence says DigniFi doesn't have the current poverty figures, and never shows an old one (U:97).
- **It never blocks.** In both cases the question still saves: the information gates nothing (U:391).

**Call (spec author):** the § 820.20 figure is 103B line 2's total, not Schedule I line 12 as U:384 words it.

- Line 12 is line 10 plus line 11, others' contributions, which DigniFi doesn't ask until step 4 (E2 §14). So today the two are equal.
- Once line 11 is asked, 103B separates contributions onto its line 8, and § 820.20(a)(2) reads Schedule I's combined total. Which one the page then shows is for counsel (C-7, §14).

### 6.3 Installments

Under "installments" the page shows, as information:

> To pay in installments, you also file Form 103A, _Application for Individuals to Pay the Filing Fee in Installments_. DigniFi doesn't prepare Form 103A yet. You can get it from the court.

- It links the AO's 103A page; the plan checks the URL.
- The forms dashboard shows the same notice while the answer is `installments` (§7).

### 6.4 103B's own questions, for a waiver filer (owner question 2)

Under "waiver" only, in 103B's words (`formText.ts`):

- **Line 4.** "Do you expect your family's average monthly net income to increase or decrease by more than 10% during the next 6 months?" No / Yes. Under Yes: "Explain."
- **Line 5.** "Tell the court why you are unable to pay the filing fee in installments within 120 days. If you have some additional circumstances that cause you to not be able to pay your filing fee in installments, explain them." A text area.
- **Line 7.** "Do these expenses cover anyone who is not included in your family as reported in line 1?" No / Yes. Under Yes: "Identify who."
- **Line 9.** "Do you expect your average monthly expenses to increase or decrease by more than 10% during the next 6 months?" No / Yes. Under Yes: "Explain."

Beside line 5, as information: the court decides whether the filer can pay in installments, from what they write here and the rest of the form. It is marked `DRAFT: counsel C-7`.

- **Nothing starts answered.** Continue saves whatever is answered. The page doesn't refuse a blank waiver question; 103B's `requires()` does (§7), with a link back here.
- **The other 103B lines.**
  - Line 8 copies Schedule I line 11, unasked until step 4. Part 3 says to attach Schedule A/B. Lines 17–20's details belong to step 4.
  - The page says, as information, that DigniFi leaves those lines blank for now and that 103B asks for copies of Schedule A/B.
- **Length.** Each text's length is bounded by its box. The plan sets the limits from `check()` at the boxes' smallest font, so the page refuses what the form would refuse.

If the owner answers question 2 with "step 4", §6.4 and the six line 4–9 fields go, and 103B prints those lines blank as today.

### 6.5 The API

`GET` and `PUT /api/intake/sessions/{id}/filing-fee/`, an action on `IntakeSessionViewSet`.

- **`GET`** returns the stored answers and `information`, which is null when it can't be computed:
  - `{family_size, limit_monthly, guideline: {year, effective_date, source_url}, family_income_monthly}`;
  - plus `information_gap`: `"income"` or `"no_table"` when one is missing.
- **`PUT`** sets only the keys sent, and validates:
  - `payment_choice` against the three values;
  - the yes/no answers against `yes`, `no` and null;
  - the texts against their limits;
  - anything else is a 400.
- **Locking and reopening.** It locks the session (`lock_session`) like every write to it. It never calls `reopen()`: the filing fee, like SOFA and the 103B answers, never reopens a completed intake.

Another user's session is a 404, as every session action is. Both methods take a session in any status, as SOFA does: the page follows Complete, but the dashboard's link can reach it after a reopen. **Call (spec author).**

## 7. The packet

- **103B** `applies`: the session's `filing_fee.payment_choice == "waiver"`; `_has_fee_waiver` goes.
- **`PreconditionMissing` gains a `page`** beside its `step` (`registry.py:25-33` takes only `step` today), carried into the refusal as `IntakeNotFinished.page` already is. Exactly one of the two is set. **Call (spec author).**
- **103B** `requires`, through `PreconditionMissing` with `page="/filing-fee"`:

  - lines 4, 7 and 9 answered;
  - each "Yes" with its text;
  - line 5 not blank once trimmed.

  Line 1's count needs no new refusal: an Income step gap is already the forms views' 422 before any form resolves.

- **Form 101** `requires` adds: line 8 answered, `PreconditionMissing(page="/filing-fee")`, in the words "Choose how you will pay the filing fee."
- **The dashboard.**
  - `PAGE_LINK_LABELS` swaps `/fee-waiver` for `/filing-fee`, "Go to How you will pay the filing fee".
  - The packet reply gains `payment_choice`. The dashboard shows it with §3's change link, and §6.3's notice for `installments`.
  - Generate All already deletes an unfiled 103B that no longer applies, and keeps a filed one.
- **Packet counts.** A packet is 14 forms, plus 122A-2 above the median, plus 103B for a waiver: 14–16, as today (CLAUDE.md "The packet decides which forms"). Only which filers get 103B changes.

## 8. The forms

### 8.1 Form 101 line 8

`Check Box7` binds a derived rule, `fee_payment_choice`, with choices:

- `pay_in_full` → `/Pay#20entirely`;
- `installments` → `/Pay#20in#20installments`;
- `waiver` → `/Request#20fees#20waived`.

It goes in `form_101.json`, with its addendum row in `step2_verification.json` (U §5.2). It leaves `form_101.unbound.json`.

### 8.2 Form 103B

| Line | Box                                      | Prints                                                                                                                 | Source                                                                                      |
| ---- | ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| 1    | `You`                                    | ticked                                                                                                                 | constant, as today                                                                          |
| 1    | `Your spouse`                            | ticked when the count includes the spouse                                                                              | `married_together`; `married_spouse_filing` is already an Income step gap                   |
| 1    | `Your dependents`, `How many dependents` | ticked, and the number, when `dependents()` less a spouse already counted is above 0                                   | `household.py`                                                                              |
| 1    | `Total number of people`                 | `count_fee_waiver_household`                                                                                           | `_fee_waiver_household_size` reads the list and raises `IncomeStepGap` on a gap `[DIG-223]` |
| 2    | `undefined_2` (You)                      | Schedule I line 10, column 1                                                                                           | `schedule_i_income_total_debtor1`                                                           |
| 2    | `undefined_3` (Your spouse)              | Schedule I line 10, column 2, for `married_together`; blank otherwise                                                  | `schedule_i_income_total_spouse`                                                            |
| 2    | `undefined_4` (Subtotal)                 | the two added                                                                                                          |                                                                                             |
| 2    | `undefined_5` (subtract non-cash)        | the known non-cash 8f values of the people counted, when above $0; blank otherwise                                     | 8f                                                                                          |
| 2    | `undefined_6` (Total)                    | subtotal less `undefined_5`                                                                                            |                                                                                             |
| 3    | `check 3`                                | `yes` when a counted person's 8f is Yes with a non-cash kind; `no` when every counted person answered and none has one | 8f, replacing `receives_noncash_assistance`                                                 |
| 3    | `3 type`                                 | the non-cash kinds, the filer's then "Spouse: " and the spouse's, joined by "; "                                       | 8f                                                                                          |
| 4    | `Check 4`, `4 type`                      | line 4's answer and explanation                                                                                        | `FilingFee`                                                                                 |
| 5    | `5 Type`                                 | line 5                                                                                                                 | `FilingFee`                                                                                 |
| 6    | `undefined_7`                            | Schedule J 22c                                                                                                         | unchanged                                                                                   |
| 7    | `Check 7`, `undefined_8`                 | line 7 and who. The No state is `/On` (FW:36)                                                                          | `FilingFee`                                                                                 |
| 9    | `Check 9`, `undefined_10`                | line 9 and the explanation                                                                                             | `FilingFee`                                                                                 |

- **Line 2 reads Schedule I line 10** (owner question 1). 103B's own line 2 says "If you have already filled out Schedule I: Your Income, see line 10 of that schedule", and DigniFi has filled it out.
  - Line 10 includes 8f, so the non-cash value is added in on the person's line, then taken out on `undefined_5`, as 103B lays out. The persona target does the same (PS:254: Maria 3,150, less 350, makes 2,800).
  - This retires `fee_waiver_monthly_income` and its typed source.
- **Blank, not 0.00** (U §4.5) holds: 103B has no "write $0" instruction.
  - A spouse not counted leaves `undefined_3` blank, and nothing included leaves `undefined_5` blank.
  - The subtotal and total print whenever line 10 prints for the filer.
- **New rules** link their refusals to `income_info`, or to `expense_info` for line 6. The `FilingFee` ones link to the page `/filing-fee` (`RULE_FIXES` and `fix_for` in `fill_resolver.py`).
- **Lines 4–9's boxes** get addendum rows like any new placement. The widgets' states come from the field index.

## 9. The means-test flag `[DIG-145]`

`MeansTest.qualifies_for_fee_waiver` goes: the column (a migration), its computation (`eligibility/models.py:186-188`, `:226`, `:236`) and the calculator's key (`means_test_calculator.py:98`, `:221`). Also:

- the message's sentence "you may qualify for a filing fee waiver" (`:147-150`) `[UPL]`;
- the calculator's other read (`means_test_calculator.py:57`);
- the summary's `qualifies_fee_waiver` and the `calculate_means_test` docstring (`apps/intake/views.py:349`, `:418`);
- `MeansTestPreview`'s "You may qualify for a filing fee waiver" row (`MeansTestPreview.tsx:120-125`);
- the two frontend types (`api.ts:460`, `:721`), the MSW handler (`handlers.ts:75`) and the session fixture (`fixtures/session.ts:135`);
- the tests that pin it: `audit/tests/test_upl_compliance.py:269-315`, `:451`, `test_means_test_calculator.py`, `test_household_means_test.py`, `test_e2e_intake.py:713`, `:768-779`, `MeansTestPreview.test.tsx` and `IntakeWizard.test.tsx:147`, `:174`;
- `sarah-simplest.spec.ts:57-60`, which asserts the preview mentions "fee waiver" or "filing fee". It moves to the filing-fee page and asserts §6.2's limit and figure, and never a verdict;
- the James and SOFA journeys' comments on routing.

Nothing replaces it. The only comparison DigniFi shows is §6.2's, as information.

## 10. Personas

Figures are from the persona targets, rechecked in the plan against the 3e2 seed. "Line 2" is 103B line 2's total, the page's figure.

| Persona | Line 8 (`Check Box7`) | Family | Limit shown | Figure shown                           | 103B                                         | Packet      |
| ------- | --------------------- | ------ | ----------- | -------------------------------------- | -------------------------------------------- | ----------- |
| Maria   | waiver                | 3      | $3,415.00   | $2,800.00 (3,150 − 350)                | yes: line 3 Yes "SNAP (food stamps)" from 8f | 15          |
| Sarah   | waiver                | 1      | $1,995.00   | $1,750.00                              | yes: line 3 No                               | 15          |
| DeShawn | installments          | 2      | $2,705.00   | $3,935.00 (his and his wife's line 10) | **leaves**                                   | 15 → **14** |
| Andrés  | installments          | 2      | $2,705.00   | $3,370.00                              | no (he never applied)                        | 14          |
| James   | pay in full           | 1      | $1,995.00   | $4,500.00                              | no                                           | 14          |
| Priya   | pay in full           | 4      | $4,125.00   | $9,880.00                              | no                                           | 15 (122A-2) |

- **Seed.**
  - `seed_demo_data` writes each persona's `FilingFee`, and the `fee_waiver` dicts and the `qualifies_for_fee_waiver` branch (`:924-936`) go.
  - Maria's and Sarah's line 4–9 answers are drafts for the owner (owner question 3):
    - **Maria:** line 4 No; line 5 "I support two children on what I earn. After rent, food, the car and the children's costs, there is not enough left each month to pay the fee, even in parts."; line 7 No; line 9 No.
    - **Sarah:** line 4 No; line 5 "I have no savings. My pay covers rent, food and my bus pass, and what is left each month goes to bills I already owe."; line 7 No; line 9 No.
- **E2E.**
  - `FeeWaiverPage` (`e2e/pages/fee-waiver.page.ts`) becomes `FilingFeePage` (`filing-fee.page.ts`), whose `answer(choice, waiverAnswers?)` picks the choice, fills the waiver questions under a waiver, clicks Continue and waits for `/sofa`.
  - Every journey passes it: Maria and Sarah choose the waiver; DeShawn and Andrés choose installments and assert the 103A message; James, Priya and the SOFA journey pay in full.
  - The waiver personas' `fee_waiver` fixture becomes `filing_fee`. `expected.fee_waiver_eligible` goes everywhere (`personas.ts`), replaced by the line 8 choice.
  - DeShawn's `generateAllForms(15)` becomes 14.
  - Andrés's journey stops expecting `/fee-waiver` (`andres-gig-driver.spec.ts:75-76`), and its title (`:21`) and header comment (`:6`) lose the waiver page.
  - `wizard.page.ts:44-46`'s wait after Complete becomes `/filing-fee/` (§3).
- **Read-back tests.** `test_api_readback.py` has `QUALIFIES` (`:38`) and `APPLIES` (`:41`); the umbrella's and the targets' `WAIVER_FILERS` (PS:258) is a stale name for them. Both become `WAIVER_CHOICE`, Maria and Sarah, the line 8 waiver filers.
  - The assertion on `qualifies_for_fee_waiver` (`:182-183`) goes.
  - The POSTs to `/api/intake/fee-waiver/` (`:83-93`, `:164-167`) become `PUT`s to the filing-fee action.
  - `_fee_waiver_answers` (`:96-99`, `:258-259`) compares 103B's lines 4–9 to the `FilingFee` answers.
- **Briefs** (`docs/testing/persona-briefs/`):
  - The "(fee waiver page)" rows move to the Income step's answers they now are: 5a–5h and 8f (`maria-torres.md:72-73`, `deshawn-mitchell.md:77-78`, `sarah-chen.md:68-69`).
  - Each brief gains a "How you will pay the fee (Form 101 line 8)" row.
  - Sarah's "You qualify." (`sarah-chen.md:84`) becomes "Is it clear how to ask for a fee waiver and what the court looks at? You plan to ask for one." (PS:1163).
  - Andrés's fee note (`andres-kettleby.md:94`) drops the waiver-page detour.
  - `README.md`'s outcomes read "asks for a fee waiver" and "pays in installments" (PS:1166).

## 11. Words

- **Form words** go in `formText.ts`, which no reading-level test scores: line 8's options and sentence, and 103B lines 4, 5, 7 and 9. **DigniFi's own sentences** go in `copy.ts` and pass its reading-level test: §6.2, §6.3, §6.4's notes, the 101 refusal.
- **Every sentence of §6.2 and §6.4's line 5 note** carries `DRAFT: counsel C-7` beside it in the code, as 3e2's C-12 drafts do.
- **No sentence** says "qualify", "eligible", "you should" or predicts what the court will do `[UPL]`.

## 12. CLAUDE.md gotchas rewritten `[GOTCHAS]`

- **"The fee-waiver application"** becomes "The filing fee":
  - `FilingFee` and its fields;
  - the page and its API;
  - 103B by the line 8 answer;
  - lines 1–3 read from the wizard;
  - the waiver questions;
  - the dropped model.
- **"The packet decides which forms"**: 103B applies on the line 8 answer, not on a row's existence. 101 and 103B gain the `requires()` of §7.
- **"Forms need a completed intake"**: the writes that never reopen gain the filing fee, in place of the fee-waiver application.
- **"Dated tables and the fill date"**: the poverty table, its date rule and its January `valid_through`.
- **"GenerateAll vs single"**: `PAGE_LINK_LABELS` holds `/filing-fee`.
- **File Map**:
  - `handleComplete` goes always to `/filing-fee`;
  - `FilingFeePage.tsx` replaces `FeeWaiverPage.tsx` (`/filing-fee`, with `/fee-waiver` redirecting);
  - `FilingFee` replaces `FeeWaiverApplication` in the models list;
  - `PovertyGuideline` and `poverty.py` join `apps/districts`.

## 13. Testing

**Tests name outcomes:**

- the line 8 answer is the filer's: no answer is preset, and nothing routes on a computed result;
- 103B is in the packet exactly when the answer is the waiver; moving off it removes an unfiled 103B and keeps a filed one; moving back brings the saved answers back;
- 101 `Check Box7` ticks only the filer's choice, and a 101 with no answer is refused with a link to `/filing-fee`;
- 103B with a waiver question unanswered is refused with a link to `/filing-fee`;
- the 2026 table gives $1,995.00 for 1, $710.00 for each person after, and works past 8 people;
- a family whose figure equals the limit is not below it; the page shows both figures and never a verdict;
- the table is chosen by the fill date: before 2026-01-15 none of DigniFi's rows is in force (the page says so, logs, and still saves the answer), and from 2027-02-01 the 2026 row refuses;
- 103B line 1 counts the filer, a spouse at home and the dependents, and never prints a guessed "1";
- 103B line 2 is Schedule I line 10 per person less the counted non-cash value (Maria's 3,150 − 350 = 2,800); a spouse living apart adds nothing;
- 103B line 3 reads 8f: Yes with the kinds, No when no counted person has non-cash help;
- the page's figure equals 103B line 2's total;
- an intake reopened after Complete shows no figure and links to the Income step, and still saves the answer;
- a filing-fee save never reopens a completed intake, and takes the session lock;
- every `FilingFee` column is stored as ciphertext;
- a session with a `FeeWaiverApplication` keeps 103B after the migration;
- the migrations run forward and back on sqlite and Postgres;
- the means test result, the summary and the preview carry no fee-waiver verdict;
- no persona's packet changes except DeShawn's 15 → 14.

**Also:**

- `answer_household` (`apps/intake/tests/builders.py`) gains a `FilingFee` with `pay_in_full` by default, so forms view tests meet no new 101 refusal.
- The session lock test's `WRITES` gains the filing-fee `PUT` (CLAUDE.md "Saves lock the session").
- Tier 3 cases are added for 101 `Check Box7` and 103B lines 1–3 (PS:1190). `ASSERTED_CASES` moves on purpose with the new tier 2 bindings.
- **The gates** are the usual ones:
  - backend pytest with coverage of at least 90%, and ruff 0.8.5;
  - the Postgres tests;
  - vitest, `tsc`, eslint and prettier;
  - the eight E2E journeys.

## 14. Not in 3f

- **Form 103A** `[Q1.103A]` is step 4. Until then, the message (§6.3).
- **103B line 8, Part 3 (10–16), and lines 17–20's details** are step 4. Line 8 waits for Schedule I line 11. Part 3 waits for the dashboard's "attach Schedule A/B" guidance (FW:245). Lines 17–19's payee boxes and line 20 (which Form 101 line 9 also asks) are step 4's too.
- **Which figure the page shows once Schedule I line 11 is asked** (§6.2). It goes to counsel under C-7.
- **Alaska and Hawaii tables.** ILND needs none (FW:183).

## 15. What changed from the umbrella

1. **A page after Complete, not a wizard step,** asks line 8 (§3). U:375 names no place.
2. **The filer's figure is 103B line 2's total,** equal today to U:384's "Schedule I line 12 less the non-cash help", since line 11 is unasked (§6.2).
3. **103B lines 4, 5, 7 and 9 are asked in 3f** for a waiver filer (§6.4, owner question 2). U:399 lists only lines 1–3, and the scope note leaves them to step 4 (FW:22–27).
4. **`FeeWaiverApplication` is dropped,** not encrypted (§4). U:393 asks for its answers encrypted. Every one is now asked elsewhere or printed nowhere, so dropping the table meets DIG-279 for the application. 103B's lines 17–19 stay in plaintext `FormAnswer` rows until DIG-168, as every `FormAnswer` does (§4).
5. **103B line 2 reads Schedule I line 10,** neither pre-filled nor typed (§8.2, owner question 1). U:403 puts a choice between pre-fill and step 2's "never pre-filled" to the owner. A third option, the form's own pointer to line 10, is recommended.
6. **`MeansTest.qualifies_for_fee_waiver` is removed,** not kept as information (§9). U:391 says the 150% test is information. The flag was a 60%-of-median test, never the 150% one, and §6.2 now shows the real one.
7. **The 103A notice also shows on the dashboard** (§6.3). U:378 names only the message.
8. **The poverty table loads by migration,** where the median loads by fixture (§5).

## 16. Calls this spec makes

The owner can overturn any of these.

1. Line 8 on a page after Complete; `/fee-waiver` redirects (§3).
2. One encrypted `FilingFee` record per session, holding line 8 and the waiver answers (§4).
3. `FeeWaiverApplication` dropped in 3f, with a data migration that keeps each applicant's waiver choice (§4).
4. The guideline takes effect on its Federal Register publication date, until the ILNB clerk answers (§5).
5. `valid_through` is January 31 of the next year (§5).
6. The limit is rounded to the cent, half-up, and is met only when the figure is less (§5).
7. The poverty table loads by data migration (§5).
8. The figure shown is 103B line 2's total (§6.2).
9. A missing figure or table never blocks the answer (§6.2).
10. The waiver questions are refused by 103B's `requires()`, not by the page (§6.4, §7).
11. A session action, `filing-fee`, with `GET` and `PUT`; it locks and never reopens (§6.5).
12. The 103A notice on the page and the dashboard (§6.3, §7).
13. 103B line 2's subtract box prints only a non-cash value above $0 (§8.2).
14. Line 3's kinds joined with "; ", the spouse's prefixed "Spouse: " (§8.2).
15. The means-test flag removed outright (§9).
16. The seed's line 5 drafts for Maria and Sarah (§10, owner question 3).
17. `answer_household` defaults to `pay_in_full` (§13).
18. `PreconditionMissing` carries a `page`, so a form's own precondition can link to a page as well as a step (§7). `views._failure` already copies a `page` (`forms/views.py:107-110`).
19. The dashboard always shows the line 8 answer with a link to change it (§3, §7).
20. Existing sessions meet refusals naming `/filing-fee` after the migration, instead of guessed answers (§4).
21. The whole fee-waiver API, page and tests go; the shared CSS classes stay (§4).
22. 103B lines 17–19 stay in `FormAnswer` at `/ask/form_103b`; lines 4–9 go on `FilingFee` (§4).
23. The filing-fee action takes a session in any status (§6.5).

## 17. For the owner

Three questions, most important first. The spec is written for each recommendation.

1. **103B line 2, take-home pay** (U:403, U:801).
   - **Recommended:** print Schedule I line 10, as 103B's own line 2 says to. Nothing is typed twice, and 103B can't disagree with Schedule I.
   - **The alternative:** the page asks for take-home pay again, pre-filled from line 10 or blank, as step 2's rule wanted. That keeps a typed figure the filer swears to twice and can make two sworn forms differ (FW:268).
2. **103B lines 4, 5, 7 and 9.**
   - **Recommended:** ask them in 3f, under the waiver choice. Line 5 is where the filer tells the court why they can't pay in installments, the question § 1930(f) turns on.
   - **The alternative:** leave them to step 4. A flattened packet can't be filled in a viewer (U §4.6), so a waiver filer would write them on the printed form by hand.
3. **The line 5 drafts for Maria and Sarah** (§10), if question 2 is yes. Approve or reword.

**One action, not a question:** the ILNB clerk's answer to "which poverty guideline date do you apply?" (U:389, FW-5). Until then the spec uses the publication date (§5).

**Counsel** `[C-7]` (U:643), unchanged in scope:

- the wording of §6.2 and §6.4's line 5 note;
- the § 820.20 readings DigniFi applies: income as 103B line 2's total, the non-cash deduction, and the family as the filer, a spouse at home and the dependents;
- which figure the page shows once Schedule I line 11 is asked (§6.2).

Like every counsel item, it blocks production, not merges (U:633).

## Owner answers (2026-11-02)

1. **103B line 2:** print Schedule I line 10, as 103B's line 2 says. Nothing is typed again, so `FilingFee` has no take-home field. Implemented in §1 item 5, §4, §8.2, §15 item 5.
2. **103B lines 4, 5, 7 and 9:** asked in 3f, on the filing-fee page under the waiver choice. Implemented in §1 item 6, §4, §6.4, §7, §8.2, §15 item 3.
3. **The line 5 drafts:** approved as written for Maria and Sarah, with lines 4, 7 and 9 No. Stated in §10.
