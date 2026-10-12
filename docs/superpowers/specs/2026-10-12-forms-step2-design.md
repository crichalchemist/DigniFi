# Forms step 2: collected data in the right boxes

**Status:** approved in brainstorming on 2026-10-12, design sections 1–7 one at a time. Revised after an adversarial verification against the code, the field index, the audit, the approved decisions and Plane, which confirmed 59 findings (11 blocking); every one is resolved below. This is step 2 of the forms project. Appendix E lists the few items this document settles that the sections did not show the owner one by one.

**Branch:** `feat/forms-step2`, on `main` at `49f287e` (step 1, PR #18).

**Production:** nothing deploys until all four forms steps are done. After 2a merges, `main` holds a migration that makes every existing filer with income re-enter it by source. That is one more reason the hold matters.

**Vocabulary.** Scope rows use the step 2 scope map's closed set: OK, S2.REBIND, S2.VALUE, S2.WIRE, S2.DROP, S3.ROWS, S3.MODEL, S4.ASK, OUT.JOINT, KEEP.BLANK, OWNER. A binding's **key** is `<source>:<producer>`, where the producer is its `rule`, `binding`, `value` or `ingest_key` (empty for `signature` and `presume`), for example `derived:schedule_j_vehicle_payment`.

## 1. Why

Step 1 gave the packet one fill path and an oracle that checks printed boxes against the verified field index. It also recorded what is still wrong: 142 known defects (4 unmapped checkboxes, 81 bindings on the wrong box, 57 wrong printed values). The scope map of all 17 forms (2,445 rows) shows where they come from:

- **Data the filer gives never reaches a box.** The Income step's ten amounts are dropped, so 122A-1 and Schedule I print 0.00 for every source. The API drops the phone number and the "secured" flag. Choosing "Personal Property" fails the whole Assets save. Contracts and codebtors save only on a separate button.
- **Data that does arrive lands on the wrong line.** Schedule J puts rent on "Personal care", food on "Life insurance" and car payments on Vehicle 2. 122A-1 puts pension income on the business line and household size on line 9. Form 101 prints the filer's own name as "other names you have used".
- **Some boxes print values nobody gave.** An empty sum or a missing attribute becomes 0.00 (`derivations.py` `_fmt`), and `_emit` drops only `None` and `""`. 41 live bindings outside the step 2 rows misprint this way.
- **Forms generate from unfinished sessions.** Nothing on the server checks that the intake is complete, so an empty list never means "the filer said none".

## 2. Where this step fits

| Step                        | What it does                                                                                                                                                           |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Foundation (done, #18)   | One fill path, full-name bindings checked at startup, the packet list, oracle tiers 1–3, the known-defects list                                                        |
| **2. Rebind (this spec)**   | Every figure intake already collects reaches its right box; the API stops dropping fields; forms generate only from a completed intake; the known-defects list empties |
| 3. Schedule rows and models | Item rows on A/B, C, D, E/F, G, H; priority; deductions; spouse income; IRS standards on 122A-2; the DIG-146 and DIG-145 thresholds                                    |
| 4. Form questions           | The asked fields (`ui` blocks), including SOFA and the answers this step only binds                                                                                    |

"Done" for the whole project is a full single-filer packet. Joint filing is out. Production waits for all four steps.

## 3. Owner decisions (2026-10-12)

**Questions answered before the design:**

- **Q1, the tier 3 readings:** all six confirmed. Income is gross. Priya and DeShawn file alone with the spouse counted in household size, so their tier 3 `Debto1.Quest11` rows and 2 known-defect entries are dropped. Sarah's student loan is nonpriority unsecured. Every seeded expense counts in Schedule J 22a. Priya earns $12,000 a month. The sixth, "zero boxes are not asserted", was left for step 2 to revisit; §7.5 (approved in section 7) supersedes it with blank and 0.00 expectations.
- **Q2, the median tie (DIG-136):** "at or below" the median counts as below. 122A-1 is in every packet.
- **Q3, income per source:** store the Income step's ten amounts. CMI leaves out Social Security (DIG-49). This reverses the upload spec's §4.4.
- **Q4, Schedule J (DIG-52):** utilities go on 6d with "Utilities (combined)", insurance not deducted from pay on 15d with "Insurance (combined)"; each label prints only above $0. Vehicle insurance goes on 15c.
- **Q5, the 122A-1 result (DIG-65):** tick line 14 and page-1 box 1 or 2 from line 12b against line 13. Box 3 (military) is never ticked.
- **Q6, signatures (DIG-73):** every signature line and signing date stays blank for wet ink. The dashboard tells the filer which pages to sign and date; that part is step 4 work (Appendix E).
- **Q7, consumer debts (DIG-121):** each filer answers "primarily consumer debts" in step 4. Step 2 binds the answer to 101 `Check Box18`, 106Sum `check7` and 107 `check6`. 101 `Check Box16` (credit counseling) loses its constant.
- **Q8, the section Yes/No boxes (DIG-80, DIG-69):** derived from the lists, Yes with rows and No without: A/B `Check 2`, `Check 3`, `Check 17`, `check 21`, `check 53`; D, G and H `check1`; E/F `check7`.
- **Q9, "Other Asset":** prints on A/B line 53 and in the line 54 and 61 totals. A new `personal_property` asset type feeds line 15 and line 57.
- **Q10, 103B line 2 (DIG-78):** take-home pay, never pre-filled.
- **Q11, 103B line 3:** a Yes/No question in the form's own words, with "What kind?".
- **Q12, paid help (§ 110):** DigniFi is free, so it is not a petition preparer. Each filer answers the forms' own questions in step 4. Step 2 binds two answer sets (§6.3).
- **Q13, the completion check:** forms generate only from a session the server marked complete.
- **Q14, pay stubs:** a stub supplies only the employer's name. Every income box reads the typed amounts.
- **Approach A:** one spec, two PRs, 2a "data and flow" then 2b "bindings". Neither deploys.

**Decisions made while presenting the design:** the commit order and its amendment (§4), the completion check (§5.3), income per source (§5.5), the means test (§5.6), the fee-waiver page (§5.7), the 2b rules (§6.1), the answer placements (§6.3), the five section 6c decisions, the wiring list (§6.4, Appendix A) and testing (§7).

## 4. Layout

- **Worktree:** `.claude/worktrees/forms-step2`. Nothing is committed to `main` directly.
- **Two plans,** each built and dry-run from its own text, as step 1's was. The 2a plan is written when this spec is approved. The 2b plan is written after 2a merges, because its exact counts depend on what 2a leaves.
- **Every commit passes every gate** (§7.1). Each seed, end-to-end or page-object change ships in the commit whose code needs it.
- **Each commit deletes exactly the known-defect entries it clears and never adds one.** A commit that clears something only partly says so in its message.

**2a commit order:**

1. **Oracle re-key** (§7.2).
2. **Completion check** (§5.3).
3. **Save and flow fixes** (§5.4): DIG-147, DIG-26 with its backfill, DIG-47, DIG-120, DIG-149, DIG-148, DIG-55. The three waiver journeys gain the SOFA step here. The API read-back test (§7.6) starts here.
4. **Income per source** (§5.5): the model, the migration, the Income step, the shared CMI that leaves out Social Security, the income rules' new bodies, the "Enter your income by source" refusal, and the seeds' ten amounts. This commit stops writing the old total, so everything that reads income moves with it.
5. **Means test** (§5.6): the median tie, rounding to the cent, recalculating at generate time, the DIG-128 reset and message, keeping and downloading filed forms, and the dashboard showing a whole-call refusal (DIG-156).
6. **Fee-waiver page** (§5.7): the new columns, the page, the seeds' take-home figures and answers, the page object and its end-to-end data.
7. **Docs:** the persona briefs and CLAUDE.md.

**2b** follows the commit rules in Appendix B: a swap chain is one commit, everything else groups by form or by owner question.

## 5. Design: 2a, data and flow

### 5.1 What 2a changes and what it leaves

2a changes data, saves and the generate flow. It moves no binding, with one exception: the re-key changes how tier 2 names its cases, not what any box prints. The pay-stub help text (`DocumentUploadPage.tsx:19`) changes in 2b's Schedule I commit, where stubs stop feeding line 2. It becomes "Your employer's name is used for your income form (Schedule I)."

### 5.2 Ground rules for every 2a change

- An amount the filer never gave is stored as empty (NULL), never as 0, unless an existing column already defaults to 0 (the 13 expense amounts).
- A refusal speaks plain words and names what to do. It is a 422 when the filer can fix it, and a 500 logged by exception type only when operations must. The one exception is the means-test endpoint, which keeps its existing 400 for a refusal the filer can fix (`intake/views.py` `calculate_means_test`).
- Every new or changed write path bounds its amounts: zero or more, finite, within the column.

### 5.3 The completion check (commit 2)

- **Who marks an intake complete.** Only the server's `complete` action (`intake/views.py`). `status` and `current_step` join `IntakeSessionSerializer.Meta.read_only_fields` (`serializers.py:303`), so a PATCH can no longer set them (DIG-151). `update_step` accepts only an integer from 1 to 8. The one rule is `status == "completed"`. `completed_at` stays an audit timestamp, because the seeds never set it.
- **One check in the forms views** refuses an unfinished session with a 422: "Finish your intake before preparing your forms."
  - Generate All runs it first, before it deletes rows of forms that left the packet, and returns one error, not one per form.
  - Generate, regenerate and download of an unfiled form share it through `_fill`.
  - The packet list stays readable. For an unfinished session it returns the packet from stored data and never refuses; it recalculates the means test only for a completed session (§5.6).
  - The check lives in the views, not in `build_field_values`, so value-building and oracle tests are unaffected. The seeds already set `status="completed"` (`seed_demo_data.py:551`). View tests switch their session fixture to a completed session in this commit.
- **Reopening.** Pressing Continue in the wizard after completing calls `update_step`, which sets the session back to in progress, and the filer presses Complete again. Edits saved after only pressing Previous keep the session complete; the means test is recalculated at generate time (§5.6), so the forms still reflect them (Appendix E).
- **A failed Complete or means-test call keeps the filer on Review** with the reason, instead of sending them to `/forms` (`IntakeWizard.tsx` `handleComplete`, DIG-150). When only the means test fails, the session is already complete. The dashboard shows "Finish your intake", with a link back, until the session is complete.
- **The blank-expenses trap (DIG-153).** Saving the Expenses step always creates the expense record, storing blanks as $0, the columns' existing default. Without this, a filer who leaves every expense blank can never complete.

### 5.4 Save and flow fixes (commit 3)

These make an empty list mean "the filer said none", which the Q8 boxes rely on.

- **Contracts and codebtors (DIG-147).** Continue on steps 6 and 7 saves the whole list the way Assets and Debts do: create, update and delete by id, block on failure, show the error. No swallowed errors, no duplicates on a second save, no orphaned rows. Resuming at step 6 or 7 no longer leaves Continue disabled (DIG-165). Review lists contracts and codebtors (DIG-166).
- **The secured flag (DIG-26).** `DebtInfoSerializer` accepts `is_secured` and `collateral_description`, which the Debts step already sends. A one-time data migration marks stored debts secured when their type is a car loan or a mortgage, the rule the Debts step applies when the filer picks the category. This is the intake app's first data migration.
- **Personal property (DIG-47).** `personal_property` becomes a valid asset type, so the Assets save stops failing. Stored "Other" assets stay as they are.
- **The phone number (DIG-120).** The Debtor step reads and sends `phone`, the serializer's name, end to end, so a returning filer sees the saved number. The E2E page object (`wizard.page.ts`) and the vitest session fixture move in the same commit.
- **Waiver filers reach SOFA (DIG-149).** The fee-waiver page continues to `/sofa`, not `/forms`. Maria's, DeShawn's and Sarah's journeys go through the SOFA page in this commit.
- **A half-filled SOFA row (DIG-148).** The SOFA page names the row and the box to finish, instead of failing the whole save with a generic error.
- **A cleared expense (DIG-55).** Clearing an expense box saves $0 instead of leaving the old amount on the server.

**Left alone on purpose:**

- **Priority.** Nothing the filer enters sets `is_priority`, and the Debts step labels every student loan "priority" (DIG-119), against the Q1 reading. Priority is decided in step 3 or 4 (OQ-3). Until then the nonpriority totals count every unsecured debt (§6.1), and E/F's nonpriority question can only err toward "Yes".
- **Scanned debts the filer never confirmed** still count (DIG-163). The completion check makes them rarer, because the filer confirms debts on the Debts step.

### 5.5 Income per source (commit 4)

- **Model.** `IncomeInfo` gains ten amounts named as the Income step names them: `monthly_gross_wages`, `monthly_overtime`, `monthly_tips`, `monthly_rental_income`, `monthly_pension`, `monthly_social_security`, `monthly_unemployment`, `monthly_child_support`, `monthly_alimony`, `monthly_other_income`. Each is `DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)`, the expense columns' width, zero or more and finite. **No default:** a default of 0 would give every existing filer $0 income, CMI 0 and a passed means test.
- **The old total.** `monthly_income` (the six-month array) stops being written and stays for one release after step 2 goes live, as `form_data` did in step 1. It is the only record of what existing filers entered. It is a required JSONField today (`models.py:91`), so commit 4's migration makes it `null=True, blank=True`, and `IncomeInfoSerializer` makes it read-only and stops validating it. Stored values are untouched.
- **Migration.** The per-source amounts were never stored, and the audit log keeps no request bodies, so nothing can be recovered.
  - A saved total above $0 leaves the ten amounts empty. The Income step shows "You entered $X a month in total. Please split it by source," and income forms refuse until the filer does.
  - A saved total of $0 becomes ten $0 amounts, since nothing is lost.
- **The Income step** loads the ten amounts through `hydrateAmounts`. Empty boxes stay empty and are never saved as $0 unless typed. The "We keep only the total" note goes. "Rental Income" becomes "Rental income after the property's costs", because both forms ask for the net figure.
- **One CMI.** CMI = the sum of the ten amounts minus Social Security; commit 5 adds the rounding to the cent (§5.6). One function serves the means test (`eligibility/models.py`), the above-median calculator (`expense_deduction_calculator.py` `_get_cmi`) and the form rule `cmi` (`derivations.py`). The API's read-only `total_monthly_income` becomes the sum of the ten.
- **A separate Schedule I income total** includes Social Security. 2b binds it to Schedule I lines 10 and 12 and 106Sum line 4; Schedule J 23a gets it through `schedule_j_total_income`.
- **The fee-waiver flag** (`qualifies_fee_waiver`, `eligibility/models.py:172`) keeps comparing the shared CMI, now without Social Security, until DIG-145 replaces the whole standard (Appendix E).
- **The income rules read the new columns.** Every derivation that reads a per-source amount switches in this commit to its `monthly_*` column and prints blank when that column is NULL (B2). Today they read attributes `IncomeInfo` never had (`pension_retirement`, `unemployment_compensation`, `social_security`, `child_support_alimony`, `real_property_income`, `other_income`), and `_get_income_field` (`derivations.py:183-193`) turns each missing one into 0. §6.2 lists every rule and its source. Their bindings move in 2b.
- **The refusal.** When the ten amounts are empty, the CMI function raises a precondition error that reads "Enter your income by source on the Income step." Building a form that needs CMI returns it as a 422, and the means-test endpoint returns it as a 400 instead of a 500.
- **Seeds.** Each persona gets the ten amounts, with wages equal to today's figure and the rest $0. The journeys type only wages, so a journey-built session stores the other nine as empty and prints them blank; the seeds' $0 prints 0.00 (Appendix D).

| Income step box        | Schedule I         | 122A-1                    |
| ---------------------- | ------------------ | ------------------------- |
| Wages, tips            | line 2             | line 2                    |
| Overtime               | line 3             | line 2                    |
| Rental (net)           | 8a                 | line 6 (net box)          |
| Child support received | 8c                 | line 4                    |
| Alimony received       | 8c                 | line 3                    |
| Unemployment           | 8d                 | line 8                    |
| Social Security        | 8e                 | nowhere (left out of CMI) |
| Pension                | 8g                 | line 9                    |
| Other                  | 8h, "Other income" | line 10, "Other income"   |

The placements apply in 2b. Deductions are not stored until step 3 (OQ-7), so Schedule I line 7 (take-home) equals gross for now.

### 5.6 The means test (commit 5)

- **Recalculated every time.** The means test is recalculated from the stored intake after the completion check and before the packet is decided: in Generate All, Generate, Regenerate and the download of an unfiled form, and in the packet list for a completed session (an unfinished one gets the stored packet, §5.3). 122A-1 is then always in the packet and always current. A stale row no longer decides the packet (DIG-160).
- **When it can't run.** Income not split by source is the filer's to fix: 422 "Enter your income by source on the Income step." Missing district median data is an operations fault: 500, logged by exception type only. One refusal covers the whole call, the packet list included, and the dashboard shows its message.
- **The median tie (DIG-136).** `eligibility/models.py:139` changes `<` to `<=` and `registry.py:54` changes `>=` to `>`, together. `test_at_median_income_fails` flips. `test_registry.py` gains an exact-median case (CMI × 12 equal to the threshold, so 122A-2 doesn't apply), and its `test_122a2_applies_at_or_above_the_median` becomes `test_122a2_applies_only_above_the_median`. The step 1 spec's §5.6 rule is amended to `>` with a pointer here.
- **One rounding.** CMI is quantized to the cent (half-even) before both comparisons and before printing, so the verdict, the packet and 122A-1 line 12b agree on totals that differ by a fraction of a cent. One comparison function serves the means test, the packet rule and the Q5 ticks. Tests: exactly at the median, one cent over, and a fractional-cent total.
- **Stale above-median results and the message (DIG-128).** Recalculating at or below the median clears the five above-median fields. The result message branches first on annualized CMI against the median (the shared comparison), then on the expense test (`means_test_calculator.py:131-146`), so an above-median filer who passes reads the above-median text, not "your income is below the median".
- **Filed forms are kept and downloadable (DIG-155).** Generate All keeps a form marked filed even when it has left the packet. The dashboard shows it as "Filed, no longer in your current packet", and its stored answers stay. Downloading a filed form fills from its stored `field_values` without the `applies()` check (`forms/views.py:362-364`).
- **The dashboard shows a whole-call failure (DIG-156).** When Generate All or the packet list fails as a whole (422 or 500), the dashboard shows a plain-words message: the 422's own text, or a generic one for a 500. After every Generate All it reloads the packet list. Refusals of a single form's generate or download stay invisible until DIG-138 (§10).
- **Left for step 3:** the $756.25 above-median threshold (DIG-146), because the disposable income it compares comes from 122A-2 deductions that aren't right yet (OQ-9); and the fee-waiver cutoff (DIG-145), which needs the poverty guidelines.

### 5.7 The fee-waiver page and data (commit 6)

- **New columns on `FeeWaiverApplication`, no defaults:**
  - `monthly_take_home_pay`, encrypted like the row's other amounts, zero or more, bounded;
  - `receives_noncash_assistance`, `BooleanField(null=True)`, empty until answered.
- **`benefit_types`** holds the "What kind?" answer. Every stored row has `[]` there today. It is required when the answer is Yes.
- **Old columns.** `monthly_income`, `monthly_expenses` and `receives_public_benefits` stay for one release, become optional and are no longer written. After 2b no form reads them. The dead `qualifies_for_waiver()` still reads the old checkbox; it is left for DIG-145.
- **The page:**
  - It opens with the session's saved answers (a read by session; one user can have several sessions). Saved answers win over pre-fills, so a resubmit no longer resets the "cannot pay" boxes (DIG-157).
  - The income box becomes "Your average monthly take-home pay (after taxes and payroll deductions)", never pre-filled.
  - "Do you receive non-cash help from the government, such as SNAP (food stamps) or a housing subsidy?" gets Yes and No buttons with neither selected. Yes opens "What kind?". An answer is required.
  - The expenses box goes. 103B line 6 copies Schedule J line 22c in 2b.
- **Seeds and journeys.** Maria, DeShawn and Sarah qualify for a waiver; James and Priya don't. Synthetic figures: Maria $2,800 take-home, Yes, "SNAP (food stamps)"; DeShawn $3,050, No; Sarah $1,750, No. The fee-waiver page object types the take-home figure and the answer, and loses its expenses argument. Maria's journey drops its pre-fill assertion and its setup (`maria-happy-path.spec.ts:77-80`).

### 5.8 Docs (commit 7)

- **Persona briefs:** each "take-home" line becomes "before taxes", per Q1, and gains a separate take-home line with the figures above. The married personas' briefs say whose income each figure is (DIG-141).
- **CLAUDE.md gotchas,** rewritten for: income stored per source; the 122A-2 rule (`>`, recalculated at generate); the completion check; Generate All keeping filed forms; the fee-waiver columns (an empty answer prints blank, a stored False prints a sworn "No"); and tier 2 keyed on the binding. The verification-addendum gotcha lands in the 2b commit that creates `step2_verification.json`.

## 6. Design: 2b, bindings

### 6.1 Rules every 2b binding follows

- **Blank or 0.00 (B2).** A box prints 0.00 only when the filer gave that figure, or when it adds up figures they gave. A line resting on something DigniFi never asks (business income, interest, payroll deductions, priority, a partner's money) gets no source and prints blank. No rule turns a missing input into 0.00. This holds even where 122A-1 and Schedule I say "write $0": 0.00 there is a sworn "I have none" the filer never gave. The filer writes $0 by hand, or a later step asks.
- **Totals that count an unasked line as zero.** A total whose form arithmetic includes a line DigniFi never asks counts that line as zero and still prints. This covers: Schedule I line 7 (gross until deductions are stored), line 9 (8b and 8f are never asked), line 10 (its combined column adds a spouse column step 2 never fills) and line 12 (adds line 11); 122A-1 lines 11 and 12b (lines 5 and 7 are never asked) and their copies on 106Sum line 8 and 122A-2 line 1; A/B lines 36, 58, 62 and 63 (Part 4 has sources only for lines 17 and 21; 59 and 60 are never asked), with 106Sum 1b and 1c and Form 101 line 19; and 103B line 2's subtotal and net (§6.3, Q10). 6c approved this for Schedule I lines 7, 10 and 12; the wider list is in Appendix E. 122A-2 line 4 is different: whether line 3 applies depends on marital status, which is never collected (DIG-53), so line 4 stays blank.
- **Expense lines (6c option A).** The 13 expense amounts are stored as $0 when nothing is entered, so "left blank" and "$0" can't be told apart. An expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0. Totals still print: Schedule J 22a and 22c, 106Sum line 5, 103B line 6. The columns stay non-null.
- **The 41 live misprints (B1).** 29 are deleted. Four 122A-1 source rules move to their right lines: three inside chains a–c and `line6a_unemployment` (`Debto1.Quest6A` → `Debto1.Quest8.0`) on its own. Schedule J 12 and 20a move to 6d and 15d (Q4). Five keep their box with a new rule or body: Schedule I lines 4 and 7 take the gross-income rule (6d), Schedule I lines 10 and 12 take the Schedule I income total, and Schedule J 23a gets it through `schedule_j_total_income`; tier 3 keeps checking Schedule I line 12 and 23a. 106Sum line 8 stays (it copies 122A-1 line 11). This clears 25 known defects and adds none; deleting all 41 would break 10 passing persona checks.
- **Two income totals (C1).** CMI, without Social Security, goes on 122A-1 lines 11–12b, 106Sum line 8 and 122A-2 line 1. The Schedule I income total, with all ten sources, goes on Schedule I lines 10 and 12 and 106Sum line 4, and on Schedule J 23a through `schedule_j_total_income`, whose key is unchanged. It lands in the same commit as anything that copies it, or earlier.
- **Totals before item rows (B5).** A total prints once all its inputs follow B2. The rows behind it arrive in step 3. This covers A/B lines 2, 5, 15, 36, 54, 55–58 and 61–63 (59 and 60 stay blank); 106Sum 1b, 1c, 2 and 3b; Schedule D's total; E/F 6f, 6i and 6j; and Form 101's ranges. Until priority is asked (OQ-3), the nonpriority totals count every unsecured debt and the priority totals stay blank.
- **The `derivations.py` header (Rule 9).** It bars any "means-test verdict". The Q5 ticks follow the form's own instruction at line 14 ("Line 12b is less than or equal to line 13. On the top of page 1, check box 1"). The header is reworded: a rule may apply a comparison the form itself spells out, but it may not choose exemptions, decide priority, or answer anything the form leaves to the filer. 122A-2's result boxes stay blank (DIG-146, OQ-9).
- **Rule names.** A rule that moves to its right box keeps its name, so tier 2 keeps checking the move against the audit (§7.2). Several names then describe the old line (for example `line5a_pension_retirement` on 122A-1 line 9, `schedule_i_net_wages_debtor1` on Schedule I line 2). Renaming them is later cleanup, with an addendum row for each.

### 6.2 New and changed rules

Every income rule below reads its `monthly_*` column from commit 4 (§5.5) and prints blank when that column is NULL; a sum prints when at least one of its inputs was given, counting the rest as zero (§6.1).

| Rule                                                                                                                                                                                              | Returns                                                                                    | Notes                                                       |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| `cmi`                                                                                                                                                                                             | CMI (commit 5: to the cent)                                                                | the shared function (§5.5)                                  |
| `schedule_i_income_total`                                                                                                                                                                         | sum of the ten amounts                                                                     | C1                                                          |
| `schedule_i_net_wages_debtor1`                                                                                                                                                                    | `monthly_gross_wages` + `monthly_tips`                                                     | body changes; moves to Schedule I line 2                    |
| `schedule_i_overtime_debtor1`                                                                                                                                                                     | `monthly_overtime`                                                                         | new; line 3                                                 |
| `schedule_i_gross_income_debtor1`                                                                                                                                                                 | line 2 + line 3                                                                            | new; line 4, line 4's copy at the top of page 2, and line 7 |
| `schedule_i_rental_debtor1`                                                                                                                                                                       | `monthly_rental_income`                                                                    | body changes; moves to 8a                                   |
| `schedule_i_child_support_debtor1`                                                                                                                                                                | `monthly_child_support` + `monthly_alimony`                                                | body changes; moves to 8c                                   |
| `schedule_i_unemployment_debtor1`                                                                                                                                                                 | `monthly_unemployment`                                                                     | body changes; moves to 8d                                   |
| `schedule_i_social_security_debtor1`                                                                                                                                                              | `monthly_social_security`                                                                  | body changes; moves to 8e                                   |
| `schedule_i_pension_debtor1`                                                                                                                                                                      | `monthly_pension`                                                                          | body changes; moves to 8g                                   |
| `schedule_i_other_income_debtor1`                                                                                                                                                                 | `monthly_other_income`                                                                     | body changes; moves to 8h                                   |
| `schedule_i_other_income_total_debtor1`                                                                                                                                                           | sum of 8a–8h                                                                               | new; line 9                                                 |
| `other_income_label`                                                                                                                                                                              | "Other income" when `monthly_other_income` > $0                                            | new; 122A-1 line 10 and Schedule I 8h text                  |
| `line1_wages`                                                                                                                                                                                     | wages + tips + overtime                                                                    | body changes; 122A-1 line 2                                 |
| `line3_alimony`                                                                                                                                                                                   | `monthly_alimony`                                                                          | new; 122A-1 line 3                                          |
| `line6b_child_support_alimony`                                                                                                                                                                    | `monthly_child_support`                                                                    | body changes; moves to 122A-1 line 4                        |
| `line3_real_property_income`                                                                                                                                                                      | `monthly_rental_income` (net)                                                              | body changes; moves to 122A-1 line 6 net box                |
| `line6a_unemployment`                                                                                                                                                                             | `monthly_unemployment`                                                                     | body changes; moves to 122A-1 line 8                        |
| `line5a_pension_retirement`                                                                                                                                                                       | `monthly_pension`                                                                          | body changes; moves to 122A-1 line 9                        |
| `line7_other_income`                                                                                                                                                                              | `monthly_other_income`                                                                     | body changes; moves to 122A-1 line 10                       |
| `line13a_median_income`                                                                                                                                                                           | the stored `MeansTest.median_income_threshold`                                             | body changes (DIG-51); moves to 13C                         |
| `median_comparison`                                                                                                                                                                               | `below` / `above`                                                                          | new; 122A-1 14a and page-1 box                              |
| `schedule_j_*` expense rules                                                                                                                                                                      | the amount, blank at $0                                                                    | bodies change (6c option A)                                 |
| `schedule_j_other_expenses`                                                                                                                                                                       | other expenses only                                                                        | body changes                                                |
| `schedule_j_support_paid`                                                                                                                                                                         | child support paid, blank at $0                                                            | new; Schedule J 18 and 122A-2 line 19                       |
| `schedule_j_total_income`                                                                                                                                                                         | Schedule I line 12 (`schedule_i_income_total`)                                             | body changes (C1); key unchanged                            |
| `schedule_j_monthly_net_income`                                                                                                                                                                   | 23a − 23b                                                                                  | new                                                         |
| `schedule_j_joint_case`                                                                                                                                                                           | `no` for an individual filing, blank for Joint                                             | new (DIG-177)                                               |
| `schedule_j_utilities_label`, `schedule_j_insurance_label`                                                                                                                                        | "Utilities (combined)", "Insurance (combined)" above $0                                    | new (Q4)                                                    |
| `total_nonpriority_unsecured`                                                                                                                                                                     | every unsecured debt                                                                       | drops `is_priority=False` (`derivations.py:115`)            |
| `total_student_loans`                                                                                                                                                                             | sum of `student_loan` debts                                                                | new; E/F 6f, 106Sum 9d                                      |
| `total_other_nonpriority`                                                                                                                                                                         | 6j − 6f                                                                                    | new; E/F 6i                                                 |
| `total_vehicles`, `total_household_items`, `total_financial_assets`                                                                                                                               | sums by asset type (`vehicle`; `personal_property`; `bank_account` + `retirement_account`) | new                                                         |
| `other_asset_descriptions`                                                                                                                                                                        | the "Other" assets' descriptions in id order, joined with "; "                             | new; A/B line 53                                            |
| `has_real_property`, `has_vehicles`, `has_bank_accounts`, `has_retirement_accounts`, `has_other_assets`, `has_secured_debts`, `has_nonpriority_debts`, `has_executory_contracts`, `has_codebtors` | `yes` with rows, `no` without                                                              | new (Q8)                                                    |
| `creditor_count_range`, `total_assets_range`, `total_debts_range`                                                                                                                                 | the bucket's lower bound as text (`more` above the top); blank for zero creditors          | new; Form 101 lines 18–20                                   |
| `fee_waiver_monthly_income`                                                                                                                                                                       | `monthly_take_home_pay`                                                                    | body changes (Q10)                                          |
| `fee_waiver_monthly_expenses`                                                                                                                                                                     | Schedule J line 22c                                                                        | body changes (6c)                                           |
| `fee_waiver_noncash_assistance`, `fee_waiver_benefit_types`                                                                                                                                       | `yes`/`no`/blank; the "What kind?" text                                                    | new (Q11)                                                   |

The range rules return a fixed bound, and each box's `choices` maps the bound to that box's own export state, read from the field index. Line 19 and line 20 spell the $100M–$500M state differently (`100000000-500000000` against `100000001-500000000`).

### 6.3 Where the owner's answers print

- **Q7, consumer debts:** `answer:form_101.primarily_consumer_debts` → 101 `Check Box18` (16a), 106Sum `check7`, 107 `check6`, marked for legal review. 101 `Check Box19` (16b) and 107 `check6a` stay blank: only a "No" reaches them, and "No" stops the flow. 107 `check6b` ($600 in 90 days) has no source until step 4 (DIG-167). 101 `Check Box16` loses its binding.
- **Q12, paid help:**
  - `answer:form_101.paid_non_attorney_preparer` → 101 `Check Box26`, 106Dec `check1`, 107 `check30`; `answer:form_101.preparer_name` → the three name boxes.
  - 103B lines 17–19 ask different things: `answer:form_103b.paid_anyone_for_services` (17, attorneys included), `promised_to_pay_for_services` (18), `someone_paid_on_your_behalf` (19).
  - Storage is the existing `FormAnswer` store, lower-case `yes`/`no`. A missing answer prints blank. Before step 4 collects anything, the store needs a read path (DIG-169), write checks (DIG-170) and encryption (DIG-168).
- **Q4:** Schedule J 6d and 15d with their labels; 15c for vehicle insurance. Two swap chains (Appendix B).
- **Q5:** `median_comparison` ticks 122A-1 `14a` and page-1 `CheckBox1`. At or below the median: 14a and box 1 ("No Abuse"). Above: 14b and box 2.
- **Q6:** the signature and date bindings come off 121, 106Dec, 122A-1 and 122A-2, and 101 `Executed on` and `Attorney.Date signed` lose theirs.
- **Q8:** the nine boxes from the `has_*` rules. They rely on 2a's save fixes, so an empty list never comes from a failed save.
- **Q9:** "Other Asset" descriptions on A/B line 53, its value in the line 54 and 61 totals, `check 53` from the list. Personal property feeds line 15 and line 57.
- **Q10:** 103B line 2 prints take-home pay on "You" (`undefined_2`), "Subtotal" (`undefined_4`) and the net income box (`undefined_6`). "Your spouse" (`undefined_3`) and "Subtract any non-cash governmental assistance" (`undefined_5`) stay blank. `4 type` (line 4's "Explain") stops printing income.
- **Q11:** 103B `check 3` and `3 type`.

### 6.4 The wiring list

Appendix A lists every binding change by form, with its box, its line, what it prints today, what it prints after step 2, and how tier 2 checks it. In short:

- **Form 101:** the six line-2 "other names" boxes, the repeated street line, `Check Box5` (the line-6 venue question, not a second chapter box) and `Check Box16` lose their bindings. The header name prints on pages 2–9. `Check Box1` ticks Chapter 7. Line 17 is Yes. "Contact phone" gets the phone; "Cell phone" stays blank, because the wizard never asks whether the number is a cell. The mailing ZIP and city read the mailing-address answers. Lines 18–20 tick their ranges. Nine duplicated or misplaced boxes lose their bindings (Appendix E).
- **103B:** `You` ticked; lines 2, 3 and 17–19 as above; line 5 unbound; line 6 copies Schedule J 22c; the Part 3 line-15 box loses its total-debt binding, and Part 3 stays blank, since the form says to attach Schedule A/B, which is in every packet (OQ-17); the page 2–3 caption prints the name.
- **106Sum:** monthly expenses move from 9a to 5; 3a is blank until priority is asked; 3c is total liabilities; line 4 is the Schedule I income total; `check6` is Yes; 9d copies E/F 6f.
- **122A-1:** the per-source lines (§5.5), four swap chains, CMI on lines 11, line 13's state, household size and median, and the Q5 ticks.
- **122A-2:** line 1 is CMI; lines 19 and 21 print child support paid and childcare above $0; every other amount binding comes off until step 3, while the name and district stay; 41a and 41b stay blank (DIG-72).
- **Schedule I:** per-source lines; line 4 = 2 + 3, and its copy at the top of page 2 repeats it; line 7 = line 4; line 9 = 8a–8h; lines 10 and 12 = the Schedule I income total; the employer's name still comes from the pay stub.
- **Schedule J:** eleven expense moves (Appendix A), support paid on 18, other expenses alone on 21, 22c, 23a–23c, line 1 "No" for an individual filing (blank for Joint, DIG-177). The one Expenses-step car payment prints on 17a, so a filer with two financed cars sees both payments there until step 3 splits them by vehicle (D-2).
- **Schedules A/B, D, E/F, G, H:** the Q8 boxes and the totals in §6.1; D's total moves to its grand-total box; G and H print the header name.
- **Form 107:** the header name on every page; the Q7 and Q12 boxes; `check29` (additional pages attached) stays blank, since it sits in the signing block and the filer may add pages; both repeat groups (prior income, lines 4–5; creditor payments, line 6) come off until steps 3–4 ask the income kind and the 90-day window (DIG-167). The SOFA answers stay stored. Removing the groups ends DIG-77's overflow on a fourth row.
- **Form 121:** the signature, the date and the "no Social Security number" box (Appendix E).

## 7. Testing and the oracle

### 7.1 Gates

Every commit leaves every gate green: backend pytest with coverage at 90% or more, `manage.py check`, ruff 0.8.5, vitest, tsc, eslint and prettier, and the 7 end-to-end journeys. The plan runs the journeys on each commit that changes a page or the flow, and on each PR.

### 7.2 The oracle re-key (2a commit 1)

- **Today tier 2 keys a case on the box only** (`test_oracle_tier2.py:49-71`), with `case=""`. A rule changed in place, or a binding moved onto a listed box, keeps the old verdict as a green stale xfail. A step that later binds a correct producer to a box whose entry step 2 deleted fails on the old verdict (B3).
- **After the re-key:**
  - The tier 2 case slot carries the binding key.
  - Audit rows match on `(box, key)`. Their producer spellings are normalized: strip a leading `rule:`, `rule ` (with a space), `binding:` or `ingest_key:` and a trailing ` (...)`; a producer equal to its source (`signature`, `presume`) becomes empty.
  - **Exact join:** an audit row for `(box, key)` is used as today.
  - **Moved here:** with no exact row, a checked audit row with the same key whose `correct_target` is this box asserts the box and passes. "Checked" means a `verification.json` row or a checked basis on that row's own box. Constants are excluded: a `/Yes` the audit placed for one question proves nothing about another.
  - Anything else is unasserted, as today.
- **No result changes:** 425 cases asserted, 344 pass and 81 xfail before and after. The diff is the `case` value of the 81 tier 2 entries, re-recorded with the recorder's three-file invocation. `oracle.py`'s docstring and the step 1 spec's `case` definition gain "the binding key for tier 2". This closes DIG-173.

### 7.3 Known defects, commit by commit

- **R1–R4** (Appendix B) hold in both PRs.
- **Q1:** Priya's and DeShawn's `Debto1.Quest11` rows leave `EXPECTED` with their 2 entries, in one commit.
- **2a** should clear few or none, because it changes data and flow, and no persona has Social Security.
- **2b's target is an empty `known_defects.json`.** Appendix C maps every entry to the change that clears it. An entry still listed at the end is named in the PR with its reason and ticket.
- **No recorder run after the re-key.** Entries are deleted by hand. A green suite proves the list is exact: a listed case that passes is a strict XPASS, and an entry with no case behind it fails the orphan test. So the recorder's `FORM_TICKET` gap (five forms missing, DIG-143) can't bite, and it stays in that ticket.

### 7.4 Checking step 2's own placements

- **The addendum.** `data/forms/field_index/audit/step2_verification.json` uses `verification.json`'s row shape plus `producer`. Its rows are transcribed from Appendix A's rows marked **ADD**, not from the bindings. Each cites the box's label in the field index and, where one decided it, the owner's answer. Tier 2 reads them as checked exact rows.
- **Rows land with their binding,** in the same commit. A test fails on any addendum row that no binding matches.
- **The coverage count.** Tier 2 pins how many cases it asserts. Most 2b commits change the number, since deleting wrong bindings lowers it. It is a review tripwire that makes each commit's change in coverage visible, not a correctness test.

### 7.5 Tier 3 learns about blanks

Tier 3 skips any box expected to hold zero today ("step 2 decides where blank replaces 0.00"). It gains an expectation that a box shows nothing, and the rows in Appendix D: a line DigniFi never asks prints blank, an expense at $0 prints blank, an income source typed as $0 prints 0.00. Each row lands in the commit that makes it pass, because R3 never adds entries.

### 7.6 The read-back through the API (B15, DIG-140)

- **Why.** Seeds write the database directly (`seed_demo_data.py`), so tier 3 can't see a field the API drops. Phone and "secured" are dropped that way today.
- **What.** One backend test per persona sends the persona's data, including its typed $0 amounts, through the endpoints the wizard and the post-intake pages use: the nested session save, the contracts and codebtors list saves, the SOFA save, the fee-waiver application (Maria, DeShawn and Sarah), `calculate_means_test` until commit 5 makes the means test automatic, then `complete` and Generate All. It requires every form's resolved values to equal those of the seed-built session. Repeat-group rows (Form 107's SOFA rows, until 2b removes them) are compared regardless of order, since stored rows have no fixed order (DIG-164); the one other order-dependent value, A/B line 53's joined descriptions, uses id order. It lands in commit 3 and grows in commits 4 and 6. It also fills 122A-2 with real values for Priya, which no test does today.
- **What it can't catch.** A wizard that sends a field under the wrong name (the DIG-120 kind) still passes, because the test sends what its author wrote. Per-step vitest tests pin the names the server expects. This gap is listed in §10.

### 7.7 Tests named for what they protect

For example: `test_unfinished_intake_cannot_prepare_forms`, `test_browser_cannot_mark_intake_complete`, `test_social_security_never_counts_toward_cmi`, `test_income_exactly_at_median_is_below_median`, `test_one_cent_over_median_is_above_median`, `test_fractional_cent_cmi_rounds_before_the_median_comparison`, `test_above_median_filer_who_passes_is_not_told_below_median`, `test_filed_form_survives_leaving_the_packet` (it also downloads the filed form), `test_expense_line_prints_only_above_zero`, `test_second_save_does_not_duplicate_codebtors`, `test_legacy_income_total_must_be_split_before_forms_print`, `test_new_filer_saves_income_by_source_without_a_total`, and `test_each_income_source_prints_on_its_own_line`, which gives each of the ten sources a distinct non-zero amount and requires each on its 122A-1 and Schedule I box (the seeds can't catch a dead rule body, since their nine non-wage sources are $0). Mocks stand only at boundaries.

### 7.8 Data migrations

Each is tested with Django's own migration executor against prepared rows; no new library. Reversing each is a no-op, since the old columns are kept.

- **Secured backfill (commit 3):** car and mortgage loans become secured; other debts are unchanged.
- **Income (commit 4):** a total above $0 leaves the ten amounts empty; a $0 total becomes ten $0 amounts; the old column is untouched.
- **Fee-waiver columns (commit 6):** existing rows stay empty.

### 7.9 End-to-end changes

- Maria, DeShawn and Sarah continue from the fee-waiver page to SOFA, then the dashboard (commit 3).
- The fee-waiver page object types take-home pay and the non-cash answer, and loses its expenses argument (commit 6).
- Packet sizes don't change.

## 8. Security and UPL

- **No new exposure.** The ten income amounts are plain decimals like the expense amounts; `monthly_take_home_pay` is encrypted like the waiver's other amounts. The API still never returns `field_values`.
- **Answers stay the filer's.** Consumer debts, paid help and non-cash help print only what the filer answers; step 2 writes no answers. `FormAnswer` is plaintext today (DIG-168), so step 4 encrypts it before it collects anything.
- **No legal judgment in rules.** The Q5 ticks apply the comparison 122A-1 spells out. Priority, exemptions and the 122A-2 result stay blank. Help text and refusals are information, not advice (`docs/UPL_COMPLIANCE.md`).
- **The completion check closes a client-writable status** (DIG-151).

## 9. Success criteria

1. **Gates** (§7.1) green on every commit of both PRs.
2. **Known defects:** `known_defects.json` is empty at the end of 2b, or each remaining entry is named in the PR with its reason and ticket.
3. **Placements checked:** every Appendix A row marked ADD has an addendum row, and every MOVED row passes through the moved-here join.
4. **Completion:** Generate All, Generate, Regenerate and the download of an unfiled form refuse an unfinished session with the 422, and a PATCH can't set `status` or `current_step`.
5. **Income:** CMI never includes Social Security; a legacy total above $0 refuses forms until it is split; the median tie counts as below in the means test, the packet and 122A-1.
6. **Read-back:** for each persona, the packet built through the API equals the seed-built packet.
7. **Filed forms** survive leaving the packet and stay downloadable.
8. **Journeys:** all 7 pass; the three waiver journeys go through SOFA.

## 10. Known gaps after step 2

- **Two cars share Schedule J 17a** until step 3 stores a payment per vehicle (D-2).
- **Joint filers get a single-filer packet.** The wizard still offers Joint (DIG-177); Schedule J line 1 stays blank for them.
- **Priority:** priority totals and E/F's priority question stay blank, and the wizard still labels student loans "priority" (DIG-119), until OQ-3.
- **Schedule I deductions** (5a–6) stay blank and line 7 equals gross until step 3 (OQ-7). The spouse column stays blank (OQ-6).
- **122A-2** prints only lines 1, 19 and 21 until step 3 (IRS standards, OQ-9); its result section stays blank (DIG-72, DIG-146).
- **Form 107 lines 4–6** stay blank until steps 3–4.
- **Answers:** every `answer:` box stays blank until step 4 writes answers, after DIG-168/169/170.
- **Wizard key names** are pinned per step by vitest, not by the read-back (§7.6).
- **Rule names** that describe an old line (§6.1).
- **"Other. Specify" text** on Schedule J line 21 and the 122A-1 line 10 / Schedule I 8h source stay generic until step 4 asks.
- **Pay-stub pre-fill** of the Income step is later work (DIG-176); a stub supplies only the employer's name.
- **Recreational vehicles.** An RV entered as a vehicle ticks A/B line 3 instead of line 4 until step 3 splits vehicle kinds.
- **Single-form refusals** from Generate, Regenerate and download stay invisible on the dashboard until DIG-138.
- **Signing guidance.** The dashboard does not yet say which pages to sign and date (Q6, step 4).

## 11. Tickets

**Expected to close with step 2** (each is checked against its ticket text when 2b merges): DIG-47, 49, 51, 52, 55, 56, 59, 61, 120, 128, 136, 140, 141, 147, 148, 149, 150, 151, 153, 154, 155, 156, 157, 160, 165, 166, 173. DIG-49 closes once the fee-waiver income question is recorded on DIG-145 (§5.5).

**Partly addressed:**

| Ticket  | Here                                                                                               | Finished in                                                                                                                                                           |
| ------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DIG-26  | `is_secured` and collateral saved; backfill; Schedule D total and `check1`                         | Schedule D rows with collateral, step 3 (DIG-69)                                                                                                                      |
| DIG-36  | wages and the income lines from typed amounts                                                      | an employer name stored without a pay stub                                                                                                                            |
| DIG-50  | misprinted 122A-2 vehicle lines removed                                                            | IRS standards, step 3 (OQ-9)                                                                                                                                          |
| DIG-53  | 13B and 13C from `household_size`                                                                  | marital status collected (122A-2 line 4, 122A-1 `CheckBox3`/`CheckBox3A`), step 4                                                                                     |
| DIG-60  | 122A-2 line 1; misprints removed                                                                   | deductions, step 3                                                                                                                                                    |
| DIG-65  | 14a and the page-1 result (Q5)                                                                     | `CheckBox3`/`CheckBox3A` once marital status is collected (DIG-53), step 4                                                                                            |
| DIG-66  | misprinted 122A-2 housing lines removed                                                            | IRS standards, step 3 (OQ-9)                                                                                                                                          |
| DIG-68  | the four unmapped boxes                                                                            | asked boxes, step 4                                                                                                                                                   |
| DIG-69  | D, E/F, G, H gates and totals                                                                      | rows, step 3                                                                                                                                                          |
| DIG-73  | signatures and dates blank                                                                         | the dashboard's signing guidance (Q6), step 4                                                                                                                         |
| DIG-74  | `is_secured` saved                                                                                 | `is_priority`, OQ-3                                                                                                                                                   |
| DIG-76  | other names, `Street1`, mailing ZIP and city, phone boxes, duplicates, lines 16a and 17–20, header | line 8 and lines 9–14 asked, and a last-4 rule for `Debtor1 Tax Payer IDNum`, step 4                                                                                  |
| DIG-77  | wrong rows removed; overflow gone                                                                  | lines 4–6, steps 3–4                                                                                                                                                  |
| DIG-78  | lines 1–3, 6, 17–19, caption                                                                       | lines 4, 5, 7–9 and 20 asked, step 4; Part 3 stays blank (OQ-17)                                                                                                      |
| DIG-79  | 3c, 4, 5, 8, `check6`, `check7`, 9d                                                                | 3a and 9a–9c, 9e–9g once priority is asked (OQ-3)                                                                                                                     |
| DIG-80  | gates and totals                                                                                   | rows, step 3                                                                                                                                                          |
| DIG-81  | six misplaced Schedule C answers removed                                                           | Schedule C rows and exemptions, step 3                                                                                                                                |
| DIG-82  | supplement date blank; lines 2–4, 7, 9, 10 and 12 from typed income; Schedule J line 1             | take-home lines 5–7 (OQ-7) and occupation and employer address, step 3; Schedule I lines 1, 11 and 13 and Schedule J `check1a`, `check2`, `check3`, `check24`, step 4 |
| DIG-152 | one CMI                                                                                            | the 122A-2 calculator's missing-data zeros, step 3                                                                                                                    |
| DIG-159 | a missing median row is a logged 500; the ten amounts bounded                                      | a `household_size` cap                                                                                                                                                |
| DIG-161 | stub wages no longer print on line 2                                                               | the employer name across several stubs; pre-fill (DIG-176)                                                                                                            |

**Unchanged and still open:** DIG-72, 119, 121, 138, 143, 145, 146, 163, 164, 167, 168, 169, 170, 176, 177.

## Appendix A. Binding changes, form by form

Boxes are the field index's full names. "Today" is the binding key on `main` at `49f287e`; "unbound" means no binding. Checkbox `choices` are written answer → export state, with the state as `export_state()` spells it (`/` plus the index `on_state` with `#20` decoded). Unlisted bindings don't change.

**How tier 2 checks each row (after the re-key):**

- **KEEP:** the binding key is unchanged, so the audit's verdict still applies.
- **MOVED:** the moved-here join asserts the box from the audit's own `correct_target`.
- **ADD:** an addendum row asserts it (§7.4).
- **DEL:** the binding is removed and the box prints blank.

### A.1 Form 101

| Box                                                                                                                                                                                                                                          | Line                                      | Today                                              | After                                                                                                                                                                                                                                                                                                                                                                                                                                      | Check |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----- |
| `Debtor1.First name_3`, `Debtor1.Middle name_3`, `Debtor1.Last name_3`, `Debtor1.First name_5`, `Debtor1.Middle name_5`, `Debtor1.Last name_5`                                                                                               | 2, other names used                       | `derived:first_name` / `middle_name` / `last_name` | blank until step 4 asks                                                                                                                                                                                                                                                                                                                                                                                                                    | DEL   |
| `Debtor1.Street1`                                                                                                                                                                                                                            | 5, second address line                    | `derived:street_address`                           | blank                                                                                                                                                                                                                                                                                                                                                                                                                                      | DEL   |
| `Debtor1.ZIP Code_2`                                                                                                                                                                                                                         | 5, mailing ZIP                            | `derived:zip_code`                                 | `asked:answer:form_101.mailing_zip`                                                                                                                                                                                                                                                                                                                                                                                                        | ADD   |
| `City_2`                                                                                                                                                                                                                                     | p5, hazard property city                  | `asked:answer:form_101.mailing_city`               | moved to `Debtor1.City_2`; blank                                                                                                                                                                                                                                                                                                                                                                                                           | DEL   |
| `Debtor1.City_2`                                                                                                                                                                                                                             | 5, mailing city                           | unbound                                            | `asked:answer:form_101.mailing_city`                                                                                                                                                                                                                                                                                                                                                                                                       | MOVED |
| `Check Box5`                                                                                                                                                                                                                                 | 6, why this district                      | `constant:/Yes`, `{}`                              | blank (residence time isn't asked)                                                                                                                                                                                                                                                                                                                                                                                                         | DEL   |
| `Check Box1`                                                                                                                                                                                                                                 | p1 and line 7, chapter                    | `constant:/Yes`, `{}`                              | `constant:/Yes`, `{"/yes": "/Chapter 7"}`                                                                                                                                                                                                                                                                                                                                                                                                  | KEEP  |
| `Check Box16`                                                                                                                                                                                                                                | 15, credit counseling                     | `constant:/Yes`, `{}`                              | blank                                                                                                                                                                                                                                                                                                                                                                                                                                      | DEL   |
| `Check Box18`                                                                                                                                                                                                                                | 16a, consumer debts                       | unbound                                            | `asked:answer:form_101.primarily_consumer_debts`, `{"yes": "/Yes", "no": "/No"}`, legal review                                                                                                                                                                                                                                                                                                                                             | ADD   |
| `Check Box20`                                                                                                                                                                                                                                | 17, filing under Chapter 7                | unbound                                            | `constant:yes`, `{"yes": "/Yes"}`                                                                                                                                                                                                                                                                                                                                                                                                          | ADD   |
| `Check Box21`                                                                                                                                                                                                                                | 18, number of creditors                   | unbound                                            | `derived:creditor_count_range`, `{"1": "/1-49", "50": "/50-99", "100": "/100-199", "200": "/200-999", "1000": "/1000-5000", "5001": "/5001-10000", "10001": "/10001-25000", "25001": "/25001-50000", "50001": "/50001-100000", "more": "/More than 100000"}`                                                                                                                                                                               | ADD   |
| `Check Box22`                                                                                                                                                                                                                                | 19, assets                                | unbound                                            | `derived:total_assets_range`, `{"0": "/0-50000", "50001": "/50001-100000", "100001": "/100001-500000", "500001": "/500001-1000000", "1000001": "/1000001-10000000", "10000001": "/10000001-50000000", "50000001": "/50000001-100000000", "100000001": "/100000000-500000000", "500000001": "/500000001-1000000000", "1000000001": "/1000000001-10000000000", "10000000001": "/10000000001-50000000000", "more": "/More than 50000000000"}` | ADD   |
| `Check Box23`                                                                                                                                                                                                                                | 20, liabilities                           | unbound                                            | `derived:total_debts_range`, as `Check Box22` except `"100000001": "/100000001-500000000"`                                                                                                                                                                                                                                                                                                                                                 | ADD   |
| `Debtor1.Name`                                                                                                                                                                                                                               | header, pages 2–9                         | unbound                                            | `derived:full_name`                                                                                                                                                                                                                                                                                                                                                                                                                        | ADD   |
| `Executed on`                                                                                                                                                                                                                                | Part 7, date                              | `asked:answer:form_101.executed_on`                | blank (Q6)                                                                                                                                                                                                                                                                                                                                                                                                                                 | DEL   |
| `Attorney.Date signed`                                                                                                                                                                                                                       | Part 7, attorney date                     | `asked:answer:form_101.attorney_date_signed`       | blank (Q6)                                                                                                                                                                                                                                                                                                                                                                                                                                 | DEL   |
| `Check Box26`                                                                                                                                                                                                                                | Part 7, paid a non-attorney               | unbound                                            | `asked:answer:form_101.paid_non_attorney_preparer`, `{"yes": "/Yes", "no": "/no"}`                                                                                                                                                                                                                                                                                                                                                         | ADD   |
| `Debtor1.Contact phone_2`                                                                                                                                                                                                                    | Part 7, contact phone                     | `asked:answer:form_101.preparer_phone`             | `derived:phone`                                                                                                                                                                                                                                                                                                                                                                                                                            | ADD   |
| `Debtor1.Cell phone`                                                                                                                                                                                                                         | Part 7, cell phone                        | `derived:phone`                                    | blank (not asked whether it's a cell)                                                                                                                                                                                                                                                                                                                                                                                                      | DEL   |
| `Attorney.Street address_3`, `Business Street address2`, `Debtor`, `Debtor_2`, `Debtor1.Business name_3`, `Debtor1.Employer Identification Number2`, `If immediate attention is needed why is it needed2`, `Street_7`, `What is the hazard2` | duplicates and misplacements (Appendix E) | as today                                           | blank                                                                                                                                                                                                                                                                                                                                                                                                                                      | DEL   |

`Name of person payed to help file` already reads `answer:form_101.preparer_name` and doesn't change.

### A.2 Form 103B

| Box              | Line                    | Today                                 | After                                                                             | Check |
| ---------------- | ----------------------- | ------------------------------------- | --------------------------------------------------------------------------------- | ----- |
| `You`            | 1                       | unbound                               | `constant:true`, `{"true": "/On"}`                                                | ADD   |
| `undefined_2`    | 2, You                  | unbound                               | `derived:fee_waiver_monthly_income` (take-home)                                   | ADD   |
| `undefined_4`    | 2, Subtotal             | unbound                               | `derived:fee_waiver_monthly_income`                                               | ADD   |
| `undefined_6`    | 2, family's net income  | unbound                               | `derived:fee_waiver_monthly_income`                                               | MOVED |
| `4 type`         | 4, Explain              | `derived:fee_waiver_monthly_income`   | moved; blank                                                                      | DEL   |
| `check 3`        | 3, non-cash help        | unbound                               | `derived:fee_waiver_noncash_assistance`, `{"yes": "/yes", "no": "/no"}`           | ADD   |
| `3 type`         | 3, type of assistance   | unbound                               | `derived:fee_waiver_benefit_types`                                                | ADD   |
| `5 Type`         | 5, why not installments | `derived:fee_waiver_monthly_expenses` | moved; blank until step 4 asks                                                    | DEL   |
| `undefined_7`    | 6, monthly expenses     | unbound                               | `derived:fee_waiver_monthly_expenses` (Schedule J 22c)                            | MOVED |
| `Amount you owe` | 15, other assets        | `derived:total_debts`                 | blank; Part 3 blank (OQ-17)                                                       | DEL   |
| `Debtor.Name1`   | caption, pages 2–3      | unbound                               | `derived:full_name`                                                               | ADD   |
| `check_17`       | 17                      | unbound                               | `asked:answer:form_103b.paid_anyone_for_services`, `{"yes": "/yes", "no": "/no"}` | ADD   |
| `check_18`       | 18                      | unbound                               | `asked:answer:form_103b.promised_to_pay_for_services`, same choices               | ADD   |
| `check_19`       | 19                      | unbound                               | `asked:answer:form_103b.someone_paid_on_your_behalf`, same choices                | ADD   |

`undefined_3` (spouse) and `undefined_5` (non-cash subtraction) stay unbound. `Debtor.Name1`'s tooltip reads "Judge's Signature", but its position and label make it the page caption.

### A.3 Form 106Dec

| Box                                 | Today               | After                                                                              | Check |
| ----------------------------------- | ------------------- | ---------------------------------------------------------------------------------- | ----- |
| `Debtor1.signature`                 | `derived:full_name` | blank (Q6)                                                                         | DEL   |
| `Executed on`                       | `derived:today_iso` | blank (Q6)                                                                         | DEL   |
| `check1`                            | unbound             | `asked:answer:form_101.paid_non_attorney_preparer`, `{"yes": "/yes", "no": "/no"}` | ADD   |
| `Name of person payed to help file` | `presume:`          | `asked:answer:form_101.preparer_name`                                              | ADD   |

### A.4 Form 106Sum

| Box      | Line                    | Today                                 | After                                                                                                         | Check |
| -------- | ----------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ----- |
| `3a`     | 3a, priority            | `derived:total_priority_unsecured`    | blank until OQ-3 (B1)                                                                                         | DEL   |
| `3b`     | 3b, nonpriority         | `derived:total_nonpriority_unsecured` | same key; counts every unsecured debt                                                                         | KEEP  |
| `3c`     | total liabilities       | `derived:total_unsecured_debts`       | `derived:total_debts`                                                                                         | MOVED |
| `4`      | 4, Schedule I line 12   | `derived:total_debts`                 | `derived:schedule_i_income_total`                                                                             | ADD   |
| `5`      | 5, Schedule J 22c       | unbound                               | `derived:total_monthly_expenses`                                                                              | MOVED |
| `9a`     | 9a, support obligations | `derived:total_monthly_expenses`      | moved; blank until OQ-3                                                                                       | DEL   |
| `9d`     | 9d, student loans       | unbound                               | `derived:total_student_loans`                                                                                 | ADD   |
| `check6` | 6                       | unbound                               | `constant:yes`, `{"yes": "/yes"}`                                                                             | ADD   |
| `check7` | 7                       | unbound                               | `asked:answer:form_101.primarily_consumer_debts`, `{"yes": "/consumer", "no": "/not consumer"}`, legal review | ADD   |

`8` keeps `derived:cmi` (KEEP) and gets the shared CMI.

### A.5 Form 122A-1

| Box                                                                                      | Line                                       | Today                                    | After                                                                                              | Check |
| ---------------------------------------------------------------------------------------- | ------------------------------------------ | ---------------------------------------- | -------------------------------------------------------------------------------------------------- | ----- |
| `Debto1.Quest2.0`                                                                        | 2, wages                                   | `derived:line1_wages`                    | same key; wages + tips + overtime                                                                  | KEEP  |
| `Debto1.Quest3`                                                                          | 3, alimony                                 | `derived:line2_business_income`          | `derived:line3_alimony`                                                                            | ADD   |
| `Debto1.Quest4`                                                                          | 4, household contributions                 | `derived:line3_real_property_income`     | `derived:line6b_child_support_alimony` (child support), chain a                                    | MOVED |
| `Debto1.Quest6C`                                                                         | 6, net rental                              | unbound                                  | `derived:line3_real_property_income`, chain a                                                      | MOVED |
| `Debto1.Quest6B`                                                                         | 6, rental expenses                         | `derived:line6b_child_support_alimony`   | moved; blank                                                                                       | DEL   |
| `Debto1.Quest9`                                                                          | 9, pension                                 | `derived:family_size`                    | `derived:line5a_pension_retirement`, chain b                                                       | MOVED |
| `13B`                                                                                    | 13, household size                         | `derived:line13b_annualized_income`      | `derived:family_size`, chain b                                                                     | MOVED |
| `Debto1.Quest5A`                                                                         | 5, business gross                          | `derived:line5a_pension_retirement`      | moved; blank                                                                                       | DEL   |
| `Debto1.Quest10A`                                                                        | 10, other income amount                    | `derived:line10a_deductions`             | `derived:line7_other_income`, chain c                                                              | MOVED |
| `Debto1.Quest7`                                                                          | 7, interest                                | `derived:line7_other_income`             | moved; blank                                                                                       | DEL   |
| `13C`                                                                                    | 13, median                                 | `derived:line13c_difference`             | `derived:line13a_median_income` (stored threshold), chain d                                        | MOVED |
| `13A`                                                                                    | 13, state                                  | `derived:line13a_median_income`          | `derived:state`, chain d                                                                           | ADD   |
| `Debto1.Quest8.0`                                                                        | 8, unemployment                            | unbound                                  | `derived:line6a_unemployment`                                                                      | MOVED |
| `Debto1.Quest6A`                                                                         | 6, rental gross                            | `derived:line6a_unemployment`            | moved; blank                                                                                       | DEL   |
| `Debto1.Quest5B`                                                                         | 5, business expenses                       | `derived:line5b_social_security`         | blank                                                                                              | DEL   |
| `Debto1.Quest8A`                                                                         | 8, unemployment claimed as Social Security | `derived:line8a_total_gross_income`      | blank                                                                                              | DEL   |
| `Debto1.Quest10B`                                                                        | 10, other income row 2                     | `derived:line10b_total_deductions`       | blank                                                                                              | DEL   |
| `Debto1.Quest10C`                                                                        | 10, separate pages                         | `derived:line10c_net_income`             | blank                                                                                              | DEL   |
| `terrorism If necessary list other sources on a separate page and put the total below 1` | 10, source                                 | unbound                                  | `derived:other_income_label`                                                                       | ADD   |
| `Debto1.Quest11`                                                                         | 11, Column A                               | unbound                                  | `derived:cmi`                                                                                      | ADD   |
| `Quest11`                                                                                | 11, total                                  | `derived:line11_annualized_income`       | `derived:cmi`                                                                                      | ADD   |
| `12B`                                                                                    | 12b                                        | `derived:line12b_annualized_cmi`         | same key; shared CMI × 12                                                                          | KEEP  |
| `14a`                                                                                    | 14a/14b                                    | unbound                                  | `derived:median_comparison`, `{"below": "/12b less or equal to 13", "above": "/12b more than 13"}` | ADD   |
| `CheckBox1`                                                                              | page-1 result                              | unbound                                  | `derived:median_comparison`, `{"below": "/No Abuse", "above": "/Presumption of abuse applies"}`    | ADD   |
| `Debtor1.sig`, `Debtor1.Date signed`                                                     | Part 3                                     | `derived:full_name`, `derived:today_iso` | blank (Q6)                                                                                         | DEL   |

### A.6 Form 122A-2

| Box                                                                                            | Line                             | Today                                    | After                                        | Check |
| ---------------------------------------------------------------------------------------------- | -------------------------------- | ---------------------------------------- | -------------------------------------------- | ----- |
| `Quest1`                                                                                       | 1, CMI                           | `derived:means_test_total_deductions`    | `derived:cmi`                                | ADD   |
| `undefined_51`                                                                                 | 19, court-ordered payments       | unbound                                  | `derived:schedule_j_support_paid` (above $0) | ADD   |
| `undefined_53`                                                                                 | 21, childcare                    | unbound                                  | `derived:schedule_j_childcare` (above $0)    | ADD   |
| `Quest5`, `Quest6`, `Quest8`, `Quest9`, `Quest10`, `Quest12`, `Quest13D`, `Quest14`, `Quest15` | IRS-standard and deduction lines | Schedule J or means-test rules           | blank until step 3 (B1)                      | DEL   |
| `Debtor1.sig`, `Debtor1.Date signed`                                                           | signing                          | `derived:full_name`, `derived:today_iso` | blank (Q6)                                   | DEL   |

`Quest4` (lines 4 and 39a), `undefined_104` (38) and `undefined_110`/`undefined_111` (41a/41b) stay unbound.

### A.7 Schedule I

| Box                                         | Line                             | Today                                                                | After                                                 | Check |
| ------------------------------------------- | -------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------- | ----- |
| `Supplemental income date`                  | header                           | `derived:today_iso`                                                  | blank                                                 | DEL   |
| `Amount 2 Debtor 1`                         | 2, wages                         | `ingested:paystub.gross`                                             | `derived:schedule_i_net_wages_debtor1` (wages + tips) | MOVED |
| `Amount 3 Debtor 1`                         | 3, overtime                      | `derived:schedule_i_net_wages_debtor1`                               | `derived:schedule_i_overtime_debtor1`                 | ADD   |
| `Amount 4 Debtor 1`                         | 4, gross income                  | `derived:schedule_i_self_employment_debtor1`                         | `derived:schedule_i_gross_income_debtor1`             | ADD   |
| `Amount 4 Debtor 1a`                        | 4, its copy at the top of page 2 | unbound                                                              | `derived:schedule_i_gross_income_debtor1`             | ADD   |
| `Amount 5a Debtor 1` → `Amount 8d Debtor 1` | 8d, unemployment                 | `derived:schedule_i_unemployment_debtor1`                            | moved                                                 | MOVED |
| `Amount 5b Debtor 1` → `Amount 8e Debtor 1` | 8e, Social Security              | `derived:schedule_i_social_security_debtor1`                         | moved                                                 | MOVED |
| `Amount 5c Debtor 1` → `Amount 8g Debtor 1` | 8g, pension                      | `derived:schedule_i_pension_debtor1`                                 | moved                                                 | MOVED |
| `Amount 5d Debtor 1` → `Amount 8c Debtor 1` | 8c, family support               | `derived:schedule_i_child_support_debtor1` (child support + alimony) | moved                                                 | MOVED |
| `Amount 5f Debtor 1` → `Amount 8a Debtor 1` | 8a, rental (net)                 | `derived:schedule_i_rental_debtor1`                                  | moved                                                 | MOVED |
| `Amount 5g Debtor 1` → `Amount 8h Debtor 1` | 8h, other                        | `derived:schedule_i_other_income_debtor1`                            | moved                                                 | MOVED |
| `Amount 5e Debtor 1`                        | 5e, insurance                    | `derived:schedule_i_interest_debtor1`                                | blank (interest isn't asked)                          | DEL   |
| `Amount 6 Debtor 1`                         | 6, deductions                    | `derived:schedule_i_total_deductions_debtor1`                        | blank until step 3                                    | DEL   |
| `Amount 7 Debtor 1`                         | 7, take-home                     | `derived:schedule_i_net_income_debtor1`                              | `derived:schedule_i_gross_income_debtor1`             | ADD   |
| `Other income 8h`                           | 8h, specify                      | unbound                                                              | `derived:other_income_label`                          | ADD   |
| `Amount 9 Debtor 1`                         | 9                                | unbound                                                              | `derived:schedule_i_other_income_total_debtor1`       | ADD   |
| `Amount 10 Debtor 1`                        | 10, Debtor 1                     | `derived:cmi`                                                        | `derived:schedule_i_income_total`                     | ADD   |
| `Amount 10`                                 | 10, combined                     | unbound                                                              | `derived:schedule_i_income_total`                     | ADD   |
| `Amount 12`                                 | 12                               | `derived:cmi`                                                        | `derived:schedule_i_income_total`                     | ADD   |

Each of the six 5x → 8x rows names the box the rule leaves, which prints blank after, and the box it moves to. `Employers Name Debtor 1` keeps `ingested:paystub.employer_name` (KEEP). `Amount 8b`, `8f`, `11` and every Debtor 2 box stay blank.

### A.8 Schedule J

| Box                                                 | Line                        | Today                                    | After                                                                                         | Check    |
| --------------------------------------------------- | --------------------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------- | -------- |
| `4`                                                 | 4, rent or mortgage         | unbound                                  | `derived:schedule_j_rent_or_mortgage`, from `10`                                              | MOVED    |
| `4c`                                                | 4c, home upkeep             | unbound                                  | `derived:schedule_j_home_maintenance`, from `14`                                              | MOVED    |
| `6d`, `Other 6d`                                    | 6d, other utilities         | unbound                                  | `derived:schedule_j_utilities`, from `12` (chain a); `derived:schedule_j_utilities_label`     | ADD, ADD |
| `7`                                                 | 7, food                     | unbound                                  | `derived:schedule_j_food_and_groceries`, from `15a`                                           | MOVED    |
| `8`                                                 | 8, childcare                | unbound                                  | `derived:schedule_j_childcare`, from `15b`                                                    | MOVED    |
| `9`                                                 | 9, clothing                 | unbound                                  | `derived:schedule_j_clothing`, from `15c` (chain b)                                           | MOVED    |
| `11`                                                | 11, medical                 | unbound                                  | `derived:schedule_j_medical_expenses`, from `16`                                              | MOVED    |
| `12`                                                | 12, transportation          | `derived:schedule_j_utilities`           | `derived:schedule_j_vehicle_maintenance`, from `17a` (chain a)                                | MOVED    |
| `15c`                                               | 15c, vehicle insurance      | `derived:schedule_j_clothing`            | `derived:schedule_j_vehicle_insurance`, from `17c` (chain b)                                  | MOVED    |
| `15d`, `Other 15d`                                  | 15d, other insurance        | unbound                                  | `derived:schedule_j_insurance_not_deducted`, from `20a`; `derived:schedule_j_insurance_label` | ADD, ADD |
| `17a`                                               | 17a, car payment, vehicle 1 | `derived:schedule_j_vehicle_maintenance` | `derived:schedule_j_vehicle_payment`, from `17b` (chain a)                                    | MOVED    |
| `10`, `14`, `15a`, `15b`, `16`, `17b`, `17c`, `20a` | vacated                     | the moved rules                          | blank                                                                                         | DEL      |
| `18`                                                | 18, support paid            | unbound                                  | `derived:schedule_j_support_paid`                                                             | ADD      |
| `21`                                                | 21, other                   | `derived:schedule_j_other_expenses`      | same key; other expenses only                                                                 | KEEP     |
| `22a`                                               | 22a                         | `derived:schedule_j_total_expenses`      | same                                                                                          | KEEP     |
| `22c`                                               | 22c                         | unbound                                  | `derived:schedule_j_total_expenses`                                                           | ADD      |
| `23a`                                               | 23a                         | `derived:schedule_j_total_income`        | same key; Schedule I line 12                                                                  | KEEP     |
| `23b`                                               | 23b                         | unbound                                  | `derived:schedule_j_total_expenses`                                                           | ADD      |
| `23c`                                               | 23c                         | unbound                                  | `derived:schedule_j_monthly_net_income`                                                       | ADD      |
| `check1`                                            | 1, joint case               | unbound                                  | `derived:schedule_j_joint_case`, `{"no": "/no"}`                                              | ADD      |

The audit names `6a` for utilities and `15b` for insurance; Q4 overrides both, so they carry addendum rows.

### A.9 Schedule A/B

| Box                                                  | Line                | Today                               | After                                                             | Check |
| ---------------------------------------------------- | ------------------- | ----------------------------------- | ----------------------------------------------------------------- | ----- |
| `12`                                                 | 1.2, street address | `derived:total_retirement_accounts` | blank (B1)                                                        | DEL   |
| `16 Cash amount`                                     | 16, cash            | `derived:total_bank_accounts`       | blank (B1)                                                        | DEL   |
| `Check 2`                                            | 1, real estate      | unbound                             | `derived:has_real_property`, `{"yes": "/yes", "no": "/On"}`       | ADD   |
| `Check 3`                                            | 3, vehicles         | unbound                             | `derived:has_vehicles`, `{"yes": "/yes", "no": "/no"}`            | ADD   |
| `Check 17`                                           | 17, deposits        | unbound                             | `derived:has_bank_accounts`, `{"yes": "/yes", "no": "/no"}`       | ADD   |
| `check 21`                                           | 21, retirement      | unbound                             | `derived:has_retirement_accounts`, `{"yes": "/yes", "no": "/no"}` | ADD   |
| `check 53`                                           | 53, other property  | unbound                             | `derived:has_other_assets`, `{"yes": "/On", "no": "/no"}`         | ADD   |
| `53 Examples Season tickets country club membership` | 53, description     | unbound                             | `derived:other_asset_descriptions`                                | ADD   |
| `undefined_13`, `undefined_159`                      | 2, 55               | unbound                             | `derived:total_real_property`                                     | ADD   |
| `undefined_26`, `undefined_160`                      | 5, 56               | unbound                             | `derived:total_vehicles`                                          | ADD   |
| `15 amount`, `undefined_161`                         | 15, 57              | unbound                             | `derived:total_household_items`                                   | ADD   |
| `undefined_124`, `undefined_162`                     | 36, 58              | unbound                             | `derived:total_financial_assets`                                  | ADD   |
| `undefined_158`, `undefined_165`                     | 54, 61              | unbound                             | `derived:total_other_assets`                                      | ADD   |
| `undefined_166`                                      | 62                  | unbound                             | `derived:total_personal_property`                                 | ADD   |
| `undefined_167`                                      | 63                  | unbound                             | `derived:total_assets`                                            | ADD   |

The template's states are irregular: line 1's "No" exports `/On`, and line 53's "Yes" exports `/On`. `undefined_163` and `undefined_164` (lines 59, 60) and the line 53 amounts stay blank.

### A.10 Schedules D, E/F, G and H

| Form | Box                             | Line           | Today                          | After                                                             | Check |
| ---- | ------------------------------- | -------------- | ------------------------------ | ----------------------------------------------------------------- | ----- |
| D    | `undefined_27` → `undefined_24` | 2, total       | `derived:total_secured_claims` | moved to the grand-total box                                      | MOVED |
| D    | `check1`                        | 1              | unbound                        | `derived:has_secured_debts`, `{"yes": "/yes", "no": "/no"}`       | ADD   |
| E/F  | `check7`                        | 3, nonpriority | unbound                        | `derived:has_nonpriority_debts`, `{"yes": "/yes", "no": "/no"}`   | ADD   |
| E/F  | `Total_6f`                      | 6f             | unbound                        | `derived:total_student_loans`                                     | ADD   |
| E/F  | `Total_6i`                      | 6i             | unbound                        | `derived:total_other_nonpriority`                                 | ADD   |
| E/F  | `Total_6j`                      | 6j             | unbound                        | `derived:total_nonpriority_unsecured`                             | ADD   |
| G    | `Debtor 1`                      | header         | unbound                        | `derived:full_name`                                               | ADD   |
| G    | `check1`                        | 1              | unbound                        | `derived:has_executory_contracts`, `{"yes": "/yes", "no": "/no"}` | ADD   |
| H    | `Debtor 1`                      | header         | unbound                        | `derived:full_name`                                               | ADD   |
| H    | `check1`                        | 1              | unbound                        | `derived:has_codebtors`, `{"yes": "/yes", "no": "/no"}`           | ADD   |

E/F `check1` (priority), `Total_6e`, `Total_6g` and `Total_6h` stay blank.

### A.11 Form 107

| Box                                            | Line                         | Today                                                                                                        | After                                                                                          | Check |
| ---------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- | ----- |
| `Debtor 1`                                     | header, pages 1–12           | unbound                                                                                                      | `derived:full_name`                                                                            | ADD   |
| `check6`                                       | 6, consumer debts            | unbound                                                                                                      | `asked:answer:form_101.primarily_consumer_debts`, `{"yes": "/yes", "no": "/no"}`, legal review | ADD   |
| `check30`                                      | Part 12, paid a non-attorney | unbound                                                                                                      | `asked:answer:form_101.paid_non_attorney_preparer`, `{"yes": "/yes", "no": "/no"}`             | ADD   |
| `Name of person agreed to pay`                 | Part 12, name                | `asked:answer:form_107.Name_of_person_agreed_to_pay`                                                         | `asked:answer:form_101.preparer_name`, the shared answer                                       | ADD   |
| repeat group `prior_income` (21 bindings)      | 4, 5                         | `asked:sofa.prior_income[].*`                                                                                | removed until step 4 asks each row's kind                                                      | DEL   |
| repeat group `creditor_payments` (33 bindings) | 6                            | 18 `asked:sofa.creditor_payments[].*` and 15 `asked:answer:form_107.Creditors …` (address, city, state, ZIP) | removed until steps 3–4 ask the 90-day window (DIG-167)                                        | DEL   |

`check6a`, `check6b` and `check29` stay blank.

### A.12 Form 121

| Box                                                       | Today                         | After                                     | Check |
| --------------------------------------------------------- | ----------------------------- | ----------------------------------------- | ----- |
| `Debtor1.signature`                                       | `derived:full_name`           | blank (Q6)                                | DEL   |
| `Executed on`                                             | `derived:today_iso`           | blank (Q6)                                | DEL   |
| `Check Box1` ("You do not have a Social Security number") | `derived:has_ssn_check`, `{}` | `derived:no_ssn_check`, `{"true": "/On"}` | MOVED |

### A.13 Schedule C

| Box                              | Today                                                                                    | After                                            | Check |
| -------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------ | ----- |
| `2.1`, `2.3`, `3`, `4`, `5`, `6` | `asked:answer:schedule_c.desc_2.1`, `amount_2.3`, `desc_3`, `desc_4`, `desc_5`, `desc_6` | blank; Schedule C's rows are step 3 (Appendix E) | DEL   |

`2.2` (`answer:schedule_c.statute_2.2`) is on its right box and stays.

### A.14 Count

Appendix A has 83 ADD boxes, which become 83 addendum rows, and 30 MOVED boxes. Form 121's `Check Box1` is MOVED because the audit's confirmed row for `derived:no_ssn_check` names it as the right box. The 2b plan recounts both against the schemas it writes.

## Appendix B. Commit rules and swap chains

**Rules, proved from the code by the oracle research (scratch experiments E1–E8):**

- **R1. Re-key first,** before any binding change. Before the re-key, a move onto a listed box or an in-place re-rule leaves a green stale xfail.
- **R2. A swap chain is one commit.** A partial chain puts two bindings on one box, which `forms.E006` rejects (`schema.py:191-195`), failing `manage.py check`, `migrate` and the test suite. Where several bindings aim at one box, at most one moves and the rest are deleted or re-ruled: 122A-2 `Quest13D`/`Quest14`/`Quest15` are all deleted, `Quest1` is re-ruled and `Quest10` deleted; Schedule I `Amount 5f` moves to `Amount 8a` and `Amount 4` is re-ruled.
- **R3. Each commit deletes exactly the known-defect entries it orphans or turns into an XPASS,** and never adds one. Deleting early leaves a plain failure; deleting late trips the orphan test or the strict XPASS.
- **R4. Don't delete a binding tier 3 relies on.** Schedule I `Amount 12` and Schedule J `23a` pass tier 3 for all five personas. `Amount 12` is re-ruled to `schedule_i_income_total`; `23a` keeps `schedule_j_total_income`, whose body becomes Schedule I line 12 (C1). Neither loses its binding. The Schedule I income total lands before or with 106Sum `4` and Schedule J `23c`, so those clear against the right rule and not against `cmi`.

**Swap chains (one commit each):**

| Chain        | Moves                                                                                                                                                           |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 122A-1 a     | `Debto1.Quest6B` → `Debto1.Quest4` → `Debto1.Quest6C`                                                                                                           |
| 122A-1 b     | `Debto1.Quest5A` → `Debto1.Quest9` → `13B` (13B's `line13b_annualized_income` is deleted)                                                                       |
| 122A-1 c     | `Debto1.Quest7` → `Debto1.Quest10A` (`line10a_deductions` is deleted)                                                                                           |
| 122A-1 d     | `13A`'s median → `13C` (`line13c_difference` is deleted); `13A` → `derived:state`                                                                               |
| Schedule J a | `17b` → `17a` → `12` → `6d`                                                                                                                                     |
| Schedule J b | `17c` → `15c` → `9`                                                                                                                                             |
| 106Sum       | `4`'s `total_debts` → `3c` (`3c`'s `total_unsecured_debts` is deleted); `4` → `derived:schedule_i_income_total`, with or after the Schedule I income total (R4) |

Schedule J `10`→`4`, `14`→`4c`, `15a`→`7`, `15b`→`8`, `16`→`11` and `20a`→`15d` are independent moves, as are 122A-1 `Debto1.Quest6A`→`Debto1.Quest8.0`, the six Schedule I 5x→8x moves, 103B `4 type`→`undefined_6` and `5 Type`→`undefined_7`, 106Sum `9a`→`5`, D `undefined_27`→`undefined_24`, and 101 `City_2`→`Debtor1.City_2`. Schedule I `Amount 3 Debtor 1`→`Amount 2 Debtor 1` replaces the pay-stub binding in the same commit.

## Appendix C. Clearing map for the 142 known defects

"Orphan" means the orphan test fails until the entry is deleted; "XPASS" means the strict xfail fails once the box prints the right value. Either way CI forces the deletion into the commit that causes it.

### C.1 Tier 1 (4 entries, all `unmapped_choice`, DIG-68)

| Entry                    | Change                                     | Clears by                                             |
| ------------------------ | ------------------------------------------ | ----------------------------------------------------- |
| `form_101` `Check Box1`  | choices mapped to `/Chapter 7`             | orphan; its 5 tier 3 entries XPASS in the same commit |
| `form_101` `Check Box5`  | binding deleted                            | orphan                                                |
| `form_101` `Check Box16` | binding deleted                            | orphan                                                |
| `form_121` `Check Box1`  | re-ruled to `no_ssn_check`, choices mapped | orphan                                                |

### C.2 Tier 2 (81 entries, all `wrong_box`)

After the re-key every change to a listed binding changes its key, so every tier 2 entry clears by orphan.

| Form             | Entries                                                                                                                                                                                                                                                                                                                                                                                                                                      | Change                                                                                   |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| form_101 (19)    | `Attorney.Street address_3`, `Business Street address2`, `Check Box5`, `Check Box16`, `Debtor`, `Debtor_2`, `Debtor1.Business name_3`, `Debtor1.Employer Identification Number2`, `Debtor1.First name_3`, `Debtor1.First name_5`, `Debtor1.Middle name_3`, `Debtor1.Middle name_5`, `Debtor1.Last name_3`, `Debtor1.Last name_5`, `Debtor1.Street1`, `If immediate attention is needed why is it needed2`, `Street_7`, `What is the hazard2` | deleted                                                                                  |
|                  | `City_2`                                                                                                                                                                                                                                                                                                                                                                                                                                     | moved to `Debtor1.City_2`                                                                |
| form_103b (3)    | `4 type`, `5 Type`                                                                                                                                                                                                                                                                                                                                                                                                                           | moved to `undefined_6`, `undefined_7`                                                    |
|                  | `Amount you owe`                                                                                                                                                                                                                                                                                                                                                                                                                             | deleted                                                                                  |
| form_106sum (2)  | `4`                                                                                                                                                                                                                                                                                                                                                                                                                                          | re-ruled to `schedule_i_income_total`; `3c` re-ruled to `total_debts` in the same commit |
|                  | `9a`                                                                                                                                                                                                                                                                                                                                                                                                                                         | moved to `5`                                                                             |
| form_107 (3)     | `Income 5a Debtor 1`, `Income 5b Debtor 1`, `Income 5c Debtor 1`                                                                                                                                                                                                                                                                                                                                                                             | `prior_income` group removed                                                             |
| form_121 (1)     | `Check Box1`                                                                                                                                                                                                                                                                                                                                                                                                                                 | re-ruled to `no_ssn_check`                                                               |
| form_122a1 (15)  | `Debto1.Quest4`, `Debto1.Quest6B`                                                                                                                                                                                                                                                                                                                                                                                                            | chain a                                                                                  |
|                  | `Debto1.Quest5A`, `Debto1.Quest9`, `13B`                                                                                                                                                                                                                                                                                                                                                                                                     | chain b                                                                                  |
|                  | `Debto1.Quest7`, `Debto1.Quest10A`                                                                                                                                                                                                                                                                                                                                                                                                           | chain c                                                                                  |
|                  | `13A`, `13C`                                                                                                                                                                                                                                                                                                                                                                                                                                 | chain d                                                                                  |
|                  | `Debto1.Quest6A`                                                                                                                                                                                                                                                                                                                                                                                                                             | moved to `Debto1.Quest8.0`                                                               |
|                  | `Debto1.Quest3`                                                                                                                                                                                                                                                                                                                                                                                                                              | re-ruled to `line3_alimony`                                                              |
|                  | `Debto1.Quest5B`, `Debto1.Quest8A`, `Debto1.Quest10B`, `Debto1.Quest10C`                                                                                                                                                                                                                                                                                                                                                                     | deleted                                                                                  |
| form_122a2 (8)   | `Quest1`                                                                                                                                                                                                                                                                                                                                                                                                                                     | re-ruled to `cmi`                                                                        |
|                  | `Quest5`, `Quest8`, `Quest9`, `Quest10`, `Quest13D`, `Quest14`, `Quest15`                                                                                                                                                                                                                                                                                                                                                                    | deleted                                                                                  |
| schedule_a_b (2) | `12`, `16 Cash amount`                                                                                                                                                                                                                                                                                                                                                                                                                       | deleted                                                                                  |
| schedule_c (6)   | `2.1`, `2.3`, `3`, `4`, `5`, `6`                                                                                                                                                                                                                                                                                                                                                                                                             | deleted                                                                                  |
| schedule_d (1)   | `undefined_27`                                                                                                                                                                                                                                                                                                                                                                                                                               | moved to `undefined_24`                                                                  |
| schedule_i (10)  | `Amount 3 Debtor 1`                                                                                                                                                                                                                                                                                                                                                                                                                          | moved to `Amount 2 Debtor 1`                                                             |
|                  | `Amount 5a Debtor 1`, `Amount 5b Debtor 1`, `Amount 5c Debtor 1`, `Amount 5d Debtor 1`, `Amount 5f Debtor 1`, `Amount 5g Debtor 1`                                                                                                                                                                                                                                                                                                           | moved to 8d, 8e, 8g, 8c, 8a, 8h                                                          |
|                  | `Amount 4 Debtor 1`                                                                                                                                                                                                                                                                                                                                                                                                                          | re-ruled to `schedule_i_gross_income_debtor1`                                            |
|                  | `Amount 5e Debtor 1`, `Supplemental income date`                                                                                                                                                                                                                                                                                                                                                                                             | deleted                                                                                  |
| schedule_j (11)  | `12`, `17a`, `17b`                                                                                                                                                                                                                                                                                                                                                                                                                           | chain a                                                                                  |
|                  | `15c`, `17c`                                                                                                                                                                                                                                                                                                                                                                                                                                 | chain b                                                                                  |
|                  | `10`, `14`, `15a`, `15b`, `16`, `20a`                                                                                                                                                                                                                                                                                                                                                                                                        | moved                                                                                    |

### C.3 Tier 3 (57 entries, all `wrong_value`)

| Form        | Box                 | Personas            | Ticket | Clears with                                                   |
| ----------- | ------------------- | ------------------- | ------ | ------------------------------------------------------------- |
| form_101    | `Check Box1`        | all 5               | DIG-68 | the tier 1 mapping (XPASS)                                    |
| form_106sum | `3c`                | james, deshawn      | DIG-79 | the `4`/`3c` re-rule (XPASS)                                  |
| form_106sum | `4`                 | all 5               | DIG-79 | the re-rule, after the Schedule I income total exists (XPASS) |
| form_106sum | `5`                 | all 5               | DIG-79 | the `9a` → `5` move (XPASS)                                   |
| form_122a1  | `13B`               | all 5               | DIG-59 | chain b (XPASS)                                               |
| form_122a1  | `13C`               | all 5               | DIG-59 | chain d, with the stored median (XPASS)                       |
| form_122a1  | `14a`               | all 5               | DIG-65 | the Q5 binding (XPASS)                                        |
| form_122a1  | `Debto1.Quest11`    | maria, james, sarah | DIG-59 | its `cmi` binding (XPASS)                                     |
| form_122a1  | `Debto1.Quest11`    | priya, deshawn      | DIG-59 | removed with their `EXPECTED` rows (Q1)                       |
| form_122a1  | `Quest11`           | all 5               | DIG-59 | the `cmi` re-rule (XPASS)                                     |
| schedule_j  | `22c`, `23b`, `23c` | all 5 each          | DIG-61 | the Schedule J totals, `23c` after `23a`'s new body (XPASS)   |

Totals: 85 clear by orphan (4 tier 1, 81 tier 2), 55 by XPASS, 2 are removed with Q1.

## Appendix D. New tier 3 rows

Hand-worked from the seeds after commit 4 (wages equal to the persona's income, the other nine sources $0) and the seeded expenses (every persona's `child_support_paid` is $0). Each row applies to all five personas.

| Form       | Box                  | Expected | Why                           | Passes from                                                     |
| ---------- | -------------------- | -------- | ----------------------------- | --------------------------------------------------------------- |
| schedule_i | `Amount 8b Debtor 1` | blank    | interest is never asked (B2)  | the commit that adds blank expectations (unbound today)         |
| form_122a1 | `Debto1.Quest7`      | blank    | interest is never asked (B2)  | 122A-1 chain c                                                  |
| schedule_j | `18`                 | blank    | support paid is $0 (option A) | the commit that adds blank expectations; stays blank once bound |
| schedule_i | `Amount 8e Debtor 1` | 0.00     | Social Security typed as $0   | the `5b` → `8e` move                                            |
| form_122a1 | `Debto1.Quest9`      | 0.00     | pension typed as $0           | 122A-1 chain b                                                  |

The module docstring's "A box expected to hold zero is not asserted" becomes the rule above.

## Appendix E. Settled here, not shown one by one in sections 1–7

These follow from approved rules or the audit, but the owner should check them in the spec review:

1. **Nine Form 101 boxes lose their bindings:** `Attorney.Street address_3`, `Business Street address2`, `Debtor1.Business name_3`, `Debtor1.Employer Identification Number2`, `If immediate attention is needed why is it needed2`, `Street_7` and `What is the hazard2` repeat a value already bound on the neighbouring box; `Debtor` and `Debtor_2` print the filer's own name where line 10 asks about someone else's pending case. The audit says to leave each blank.
2. **The mailing city moves.** 6d said the mailing ZIP would read the mailing answer "like the street, city and state beside it". The city was in fact bound to the page-5 hazard-property city (`City_2`); it moves to `Debtor1.City_2`.
3. **Form 121's "You do not have a Social Security number" box** is re-ruled to `no_ssn_check`, the box the audit's confirmed row names for it. Today's `has_ssn_check` would tick it for filers who do have one.
4. **Schedule C's six misplaced answer boxes** lose their bindings (Schedule C rows and exemptions are step 3). `2.2` stays.
5. **Boxes behind section 3's table:** 122A-1 line 3 prints alimony, and the 122A-1 line 10 source box and Schedule I's 8h "Specify" print "Other income" when other income is above $0.
6. **103B line 2's spouse box and non-cash subtraction stay blank,** and the subtotal and net income copy the take-home figure.
7. **A/B line 53** prints the "Other" assets' descriptions joined with "; "; its amount boxes wait for step 3.
8. **E/F 6i** is 6j minus 6f; 6e, 6g and 6h stay blank.
9. **DIG-156 joins commit 5.** Without it, the whole-call refusals from section 4 never reach the filer, because the dashboard shows nothing when Generate All fails.
10. **The means-test endpoint** returns a 400 in plain words, not a 500, when income isn't split by source.
11. **Moved rules keep their names** (§6.1).
12. **The packet list's rule.** Section 2 said the packet list stays readable; section 4 said it recalculates and refuses as a whole. Both hold this way: for an unfinished session it returns the stored packet and never refuses; for a completed one it recalculates and can return the 422, which the dashboard shows (§5.3, §5.6).
13. **Edits after Complete.** Section 2 said edits mean pressing Complete again. Only Continue reopens the session; edits saved after pressing Previous keep it complete. Forms still reflect them, because the means test is recalculated at generate time (§5.3).
14. **The totals rule grew.** 6c approved counting unasked lines as zero for Schedule I lines 7, 10 and 12. The same rule covers Schedule I line 9, 122A-1 lines 11 and 12b and their copies, the A/B Part 4 and summary totals with their copies, and 103B line 2 (§6.1).
15. **The fee-waiver flag** keeps comparing the shared CMI, now without Social Security, until DIG-145 replaces the standard. Whether a fee-waiver test should count Social Security is a legal question to record on DIG-145 (§5.5).
16. **Q6's signing guidance** (the dashboard says which pages to sign and date) is step 4 work with DIG-73.
17. **Schedule I's "Copy line 4 here" box** (`Amount 4 Debtor 1a`) is line 4's copy at the top of page 2, not line 5, which 6d called it. Line 5 is the payroll-deduction list and stays blank.
18. **Smaller additions:** `update_step` accepts only 1–8 (DIG-151); the Debtor step reads `phone` as well as sending it (DIG-120); a failed means-test call also keeps the filer on Review (DIG-150); a filed form downloads after leaving the packet (DIG-155); the means-test result message branches on the median first (DIG-128); the married personas' briefs say whose income each figure is (DIG-141); the CLAUDE.md addendum gotcha lands in 2b.
