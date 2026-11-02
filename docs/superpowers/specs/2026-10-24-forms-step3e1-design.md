# Forms step 3e1: household and spouse

- **Status:** draft for the owner's review, 2026-10-24.
- **Drawn from:** the step 3 umbrella spec, `docs/superpowers/specs/2026-10-16-forms-step3-design.md` §5.5 (cited `U:<line>`), and the persona targets, `docs/superpowers/specs/2026-10-16-forms-step3-personas.md` (cited `PS:<line>`).
- **Branch:** `feat/forms-step3e1`, from develop `86bc32a` (3a1 and 3a2 merged). The PR targets develop.
- **Tags** such as `[Q17]` trace each part to the umbrella's map of answers and tickets (its Appendix A); tags such as `[U:80]` and `[PS]` are citations. Four aren't in that map: `[DIG-65]`, which the survey found; `[DIG-71]` and `[DIG-177]`, which joined 3e1 by the owner's answer 3e1.Q2; and `[UPL]`, the umbrella's rule that DigniFi gives information, never advice (U:74-80, `docs/UPL_COMPLIANCE.md`).

The umbrella settles most of 3e1. This spec turns it into a design for the code as it stands after 3a2, and records the owner's three answers (§2). Each call this spec makes on its own is listed in §16 for the owner to check, including the three places it departs from the umbrella (§16 items 2, 16 and 22).

## 1. What 3e1 does

1. **Marital status** `[Q2]` `[Q7.marital]` `[DIG-53]`: the Income step asks Form 122A-1 line 1, in the form's words, and stores the answer encrypted (§3).
2. **The household list** `[Q17]` `[DIG-159]`: one encrypted list of the people in the filer's home and the people they support. Each form counts it by its own definition (§4).
3. **The spouse's income** `[Q2]`: when the filer lives with their spouse, the spouse's income by the same ten sources. Current monthly income becomes the filer's plus the spouse's everywhere (§5).
4. **County** `[OQ9.county]` `[CORR.county]` `[DIG-277]`: every filer picks their county on the Your Information step (§6).
5. **Joint filing comes off step 1** `[DIG-71]` `[DIG-177]`: the Filing Type choice and the spouse identity boxes go (§7).
6. **The forms**: 122A-1's marital boxes, Column B and line 13; Schedule I's spouse column; Schedule J line 2's dependents, with an attached sheet past five; Form 101's County (§10).
7. **Complete and the refusals** name every new gap by its step. Intakes completed before 3e1 refuse to generate until the filer answers (§9).

Nothing in 3e1 deploys: production waits for steps 3 to 5 and DIG-146.

## 2. The owner's calls

The umbrella left one question to this spec: how a spouse appears on the household list (U:310, U:812). The survey found a second it left open: step 1's Joint option and line 1's "filing with you" answer. The Income step's layout was shown as a mockup. The owner answered all three on 2026-10-24.

- **3e1.Q1, how a spouse counts as a dependent: ask the filer.** The household list asks every person "claimed on your tax return, or supported by you?". On a joint tax return a filer may answer Yes for a spouse (Priya and DeShawn do, PS:590, PS:780), and that answer alone must not decide whether the spouse is a Schedule J line 2 dependent. Line 2 says "Do not list Debtor 1 and Debtor 2", and a non-filing spouse is not Debtor 2. The spouse's row therefore asks one more question: "Is your spouse a dependent of yours?". No form asks it in these words (Schedule J line 2 asks "Do you have dependents?"), so it is DigniFi's own sentence, the wording of the option the owner chose. The forms' glossary definition of a dependent is quoted beside it as information (§4.2).
  - The combined "claimed or supported" answer still feeds 122A-2 line 5, whose definition is close to it: "the number of people who could be claimed as exemptions on your federal income tax return, plus the number of any additional dependents whom you support".
  - Form 103B counts the spouse at most once (§4.4).
  - Priya and DeShawn answer No (owner: "No is correct"). Priya's line 2 lists her two children; DeShawn's says No.
- **3e1.Q2, joint filing: one place to say it, on the Income step.** Step 1 loses its Filing Type choice and the spouse's name, birth date and SSN boxes. 122A-1 line 1 is shown with all four answers and the declaration in full, and its answer "Married and your spouse is filing with you" shows information that DigniFi prepares forms for one person filing alone; Complete names it as a gap (§3.2, §7, §9). DIG-71 and DIG-177 join 3e1 (§15).
- **3e1.Q3, the Income step's order: family first.** Marriage, then the household list, then the filer's ten amounts, then the spouse's ten amounts. Marriage comes first, as on 122A-1 line 1, and the marriage answer decides what follows it (§8.2).

**Not asked, because the umbrella settles it:** C-3, which reading of "household" 122A-1 line 13 uses. Line 13 counts the people who live with the filer until counsel rules, and the owner saw Sarah's change on the review sheet (§4.4).

## 3. Marital status `[Q2]` `[Q7.marital]` `[DIG-53]` `[DIG-65]`

### 3.1 The problem

- **The wizard never asks it.** `IncomeInfo.marital_status` exists (`apps/intake/models.py:113-120`), but no step asks it, and today's Income body sends only the ten amounts (`IntakeWizard.tsx:251-259`).
- **Its choices are tax-filing terms:** `single`, `married_joint`, `married_separate`. None can say "married, spouse not filing, living together", which Priya and DeShawn need. The seeds give both `married_joint` though both file alone (DIG-53).
- **It is plaintext**, on a table 3e1 migrates `[Q7.marital]`.

### 3.2 The question

The Income step's first section asks line 1 in the form's own words. The step leaves out each answer's column instruction ("Fill out Column A, lines 2-11." and the like), since the step has no columns; the cuts are marked "…":

> What is your marital and filing status? Check one only.
>
> - Not married. …
> - Married and your spouse is filing with you. …
> - Married and your spouse is NOT filing with you. You and your spouse are:
>   - Living in the same household and are not legally separated. …
>   - Living separately or are legally separated. … By checking this box, you declare under penalty of perjury that you and your spouse are legally separated under nonbankruptcy law that applies or that you and your spouse are living apart for reasons that do not include evading the Means Test requirements. 11 U.S.C. § 707(b)(7)(B).

- **Four stored answers:** `not_married`, `married_spouse_filing`, `married_together`, `married_separately`. Null means unanswered.
- **Nothing is selected** until the filer picks. The two-way sub-question appears under the third answer, and the declaration always shows in full beside "Living separately".
- **"Married and your spouse is filing with you"** shows, as information: "DigniFi prepares forms for one person filing alone. It can't prepare a case your spouse files with you." Complete names it as a gap (§9).
- **No help text characterizes** "legally separated" or "living apart". Those are the filer's sworn answer.

### 3.3 Storage

- **Encrypted** `[Q7.marital]`: an `EncryptedCharField`, nullable, on `IncomeInfo`.
- **No value carries over.** The wizard never asked the field (before #16 it only echoed the stored value back), so no filer gave an answer. A tax status also isn't a line 1 answer: a filer under a final decree of separate maintenance files taxes as unmarried but answers line 1 as married, and "separately" is a sworn declaration that must never be derived `[U:80]`. The seeds set the new answers (§11).
- **This departs from U:299's "with its data migration".** None of the old values is a line 1 answer, so the migration drops them instead of encrypting them (§16).
- **The operations are written by hand**, since `makemigrations` would emit an in-place AlterField that keeps the plaintext and whose reverse casts ciphertext into a 30-character column:

  1. AlterField the old column to `blank=True, default=""`;
  2. RemoveField it;
  3. AddField the nullable `EncryptedCharField`.

  Its reverse must restore the old column filled with `""`, with rows present, and §13's tests prove it on sqlite and on Postgres.

- **The serializer** accepts the four answers or null, and refuses anything else with a 400. CLAUDE.md's "echoing a wizard-created row's blank `marital_status` back is a 400" stops being true and is rewritten (§12).

## 4. The household list `[Q17]` `[DIG-159]` `[C-3]`

### 4.1 The model

A new model, `Household`, one-to-one with the session `[CORR.county]`. It is not on `DebtorInfo`, which step 3 doesn't migrate (U:323), and not in `FormAnswer`, which stays plaintext until DIG-168.

- **`county`**: an `EncryptedCharField`, nullable; null means unanswered (§6).
- **`members`**: an `EncryptedTextField` holding the list as JSON, nullable. Null means unanswered; `[]` means the filer said no one lives with them or depends on them. This is the umbrella's "one encrypted list" (U:301), and the pattern `MeansTest.calculation_details` already uses (`apps/eligibility/models.py:63-67`).
- **`next_member_id`**: a whole number, the next id to give a new row. Ids are never reused.
- **Order** is the filer's, stored in the JSON, so no encrypted column is ever sorted (DIG-164).

### 4.2 Each person

| Key                    | Value                                                                                                                                          | Asked as                                                        |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `id`                   | a whole number, unique in the list, assigned by the server                                                                                     | not asked                                                       |
| `relationship`         | one of `spouse`, `son`, `daughter`, `stepchild`, `grandchild`, `parent`, `sibling`, `other_relative`, `unmarried_partner`, `roommate`, `other` | Relationship, a list (never free text, so no name can be typed) |
| `age`                  | a whole number from 0 to 120                                                                                                                   | Age                                                             |
| `lives_with_you`       | true or false                                                                                                                                  | Lives with you?                                                 |
| `claimed_or_supported` | true or false                                                                                                                                  | Claimed on your tax return, or supported by you?                |
| `spouse_is_dependent`  | true or false, on the spouse's row only                                                                                                        | Is your spouse a dependent of yours?                            |

- **One shape.** Every row the server returns carries every key, with null for an unanswered question; `spouse_is_dependent` appears on the spouse's row only. The wizard builds its body in the same shape, so a loaded list and an unedited one compare equal.
- **No names are stored** (U:308), and the step says not to type any. Schedule J line 2 itself says so: "Do not state the dependents' names."
- **The relationship's words.** One map from each value to its words ("Daughter", "Other relative") serves the step's list and the forms (§10.3). It lives in the backend, and the frontend's copy is pinned to it by a backend test that reads the frontend file, as `test_rule_fixes.py` reads `wizardSteps.ts`.
- **The spouse's extra question** (3e1.Q1) is shown with the glossary sentence of the forms' instructions, quoted as information: "A person who is economically dependent on you regardless of whether the person can be claimed as a dependent on your federal tax return."
- **At most one spouse row**, and at most 20 rows in all `[DIG-159]`. No persona has more than three. DIG-159's floor goes away, since every count includes the filer.
- **A missing answer saves**, and Complete names it (§9). A server 400 is only for a value no answer can have: an unknown relationship, an age outside 0–120 or not whole, a second spouse row, `spouse_is_dependent` on another row (a null there counts as absent), or a 21st row. The step's guards keep it from sending any of these (§8.2).
- **Ids `[U:150]`.** A row sent with one of the list's ids keeps it, and replaces the stored row whole. A row without one, or with an id the list doesn't hold, gets `next_member_id`, which then moves on. The reply returns the list in the order sent, each row with its id, as the asset and debt saves do (CLAUDE.md "Nested debts and assets save by id"). The wizard pairs ids by position with its browser-only `_key`. Nothing links to a member yet; the ids keep the umbrella's rule for every row.

### 4.3 What the list replaces

- **`DebtorInfo.household_size`** stays in its table, unread, because step 3 doesn't migrate `DebtorInfo`; step 5 drops it `[CORR.county]`. It leaves the serializer's fields, and step 1 stops asking it (§8.1).
- **`IncomeInfo.number_of_dependents`** is removed in 3e1's migration of `IncomeInfo`. The wizard never asked it. Its readers change with it:
  - the means test's fallback (`apps/eligibility/models.py:125-128`) and its `calculation_details` (§5.3);
  - the expense calculator (`expense_deduction_calculator.py:71-76`);
  - `MeansTestCalculator.get_detailed_breakdown` (`means_test_calculator.py:209-212`);
  - `IncomeInfo.__str__` (`models.py:207-211`);
  - the serializer's fields (`serializers.py:86-87`);
  - the seed, and every test that builds an `IncomeInfo` with it (§13).
- **The fee-waiver page's pre-fill** comes from the list until 3f (§4.4).

### 4.4 How each form counts the list

| Count                                                  | Who counts                                                                                                                                                                                    | Reads it in 3e1                                                                                                                                                                                                                 | Persona values                                                           |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **122A-1 line 13 and the means test's median** `[C-3]` | the filer, plus every row that lives with them (counsel decides the final reading; the wording ships marked draft, §8.5)                                                                      | the means test's `family_size`, and the `family_size` rule on 122A-1 `13B`                                                                                                                                                      | Maria 3, James 1, Priya 4, DeShawn 2, Sarah 2, Andrés 2                  |
| **Schedule J line 2, dependents**                      | every row other than the spouse's answered Yes to "claimed or supported", and the spouse's row when "Is your spouse a dependent of yours?" is Yes, whatever its "claimed or supported" answer | J `check2` and the rows (§10.3)                                                                                                                                                                                                 | Maria 2 rows, James No, Priya 2 rows, DeShawn No, Sarah No, Andrés 1 row |
| **122A-2 line 5**                                      | the filer, plus every row answered Yes to "claimed or supported"                                                                                                                              | the expense calculator's family size (§5.3); 3h binds the line                                                                                                                                                                  | Priya 4                                                                  |
| **103B line 1**                                        | the filer; the spouse, for any married answer other than "Living separately"; and every J line 2 row, except the spouse's when the spouse already counts as "Your spouse"                     | the fee-waiver page's household-size pre-fill (§8.4), which 103B's `Total number of people` prints through the application's household size; 3f binds `Your spouse` and the dependents boxes and reads the total from the count | Maria 3, DeShawn 2, Sarah 1                                              |

- **The median uses line 13's count.** `MeansTest.calculate` and the `family_size` rule read one function, so `13B` and `13C` can't disagree. Today they read `DebtorInfo.household_size` with different fallbacks (`apps/eligibility/models.py:122-128`, `derivations.py:552`).
- **A spouse on 103B line 1.** 103B counts "you, your spouse, and any dependents listed on Schedule J", and U:315 leaves out a separated spouse. So the marriage answer decides, as the table's row says: under "Living in the same household" the spouse counts once, as "Your spouse", even when line 2 lists them; under "Living separately or are legally separated" they count only as a dependent, and only when line 2 lists them.
- **The counts reach the browser.** The session read and the PATCH reply return `household.family_size` (line 13) and `household.fee_waiver_household_size` (103B line 1), read-only, from the server's functions. Each is named for what it feeds: the means test's `family_size`, and the application's `household_size`. The second only seeds that answer: the filer may change it on the fee-waiver page, and 103B prints the application's stored size through the rule `fee_waiver_household_size` until 3f reads the count itself. Each is null while the income-step check finds a gap (§9.1), since the means test would refuse then. Review and the fee-waiver page show them, so no count is worked out twice. They stay out of the autosave body, as read-only totals do.
- **Sarah** is the one persona whose line 13 changes: her roommate lives with her, so `13B` is 2 and `13C` becomes 93,934.00. She stays below the median either way.

### 4.5 Saving

- **One PATCH per step.** The session PATCH gains a nested `household` key. Step 1 sends `{"county": ...}`, step 2 sends `{"members": [...]}`, and the serializer updates only the keys sent. One PATCH keeps a step's answers in one transaction, so a save never commits half a household.
- **Locked and reopening.** The PATCH already takes the session lock (CLAUDE.md "Saves lock the session"). `household` and `spouse_income` join `_INTAKE_DATA` (`serializers.py:252`), so a write reopens a completed intake.
- **Read on mount.** The session read nests `household` and `spouse_income`, and the wizard hydrates them before any step shows, as it does income.

## 5. The spouse's income `[Q2]`

### 5.1 When it's asked

- Only for "Living in the same household and are not legally separated". 122A-1 says to fill both columns for that answer, and Schedule I's header to include a spouse "living with you".
- If the answer changes away from it, the section hides. The figures stay saved but stop counting everywhere, and come back if the answer does.

### 5.2 The model

- **`SpouseIncome`**, one-to-one with the session, with the ten field names of `IncomeInfo.SOURCE_FIELDS`, each an `EncryptedDecimalField`, nullable, with no default. The spouse's amounts are new data, so they are encrypted from the start (U:299).
- **The serializer** gives each the filer's bounds by declaring it, `DecimalField(max_digits=10, decimal_places=2, min_value=0, allow_null=True)`, as it already declares take-home pay (`serializers.py:394-398`). Left to DRF's auto-mapper, an `EncryptedDecimalField`, a subclass of `EncryptedCharField` (`fields.py:9`), would become an unbounded string field. An empty box is null, never $0 unless typed.
- **One table per person.** `IncomeInfo`'s ten amounts stay plaintext until 3e2 encrypts them (U:299). Putting the spouse's on `IncomeInfo` would mix encrypted and plaintext amounts in one table until then.

### 5.3 Current monthly income is A + B

- **One function.** `current_monthly_income` keeps working on one person's ten amounts. A new function, used by every reader that means the household's CMI, returns the filer's plus the spouse's when the answer is `married_together`, and the filer's alone otherwise. Each column is rounded to the cent as now, so the total is exact.
- **Its readers:**
  - the means test (`apps/eligibility/models.py:117`) and its `calculated_cmi`, and so the packet's above-median check (`registry._above_median`);
  - the expense calculator (`expense_deduction_calculator.py:117`);
  - the `cmi` rule (122A-1 line 11 and 12a, 106Sum line 8, 122A-2 line 1) and `line12b_annualized_cmi`.
- **The refusal is one exception.** `IncomeStepGap`, a subclass of `IncomeNotSplit` with its own sentence and the same `step = "income_info"`, carries every income-step gap of §9.1. Because it is an `IncomeNotSplit`, the three places that let a refusal's sentence through today (`means_test_calculator.py:85-90`, `apps/forms/views.py:91-94`, `apps/intake/views.py:326-333`) pass it unchanged, and `test_rule_fixes.py`'s use of `IncomeNotSplit.step` holds. The household CMI raises it with the spouse's sentence for `married_together` and none of the spouse's ten, rather than calling `current_monthly_income` on the spouse's row, which would raise the filer's.
- **The expense calculator's family size** reads 122A-2 line 5's count (§4.4), since 122A-2 lines 6, 7, 8 and 9a use "the number of people you entered in line 5". Its silent fallback to 1 on an error stays: it is DIG-152's, in 3h.
- **`calculation_details`** stops storing `number_of_dependents`. `marital_status` holds the line 1 answer, `family_size` the line 13 count, and a new `spouse_cmi` holds Column B.
- **Persona figures:** Priya's CMI becomes 13,800.00 a month (165,600.00 a year), and DeShawn's 4,500.00 (54,000.00). Priya stays above the median and DeShawn below. DeShawn's 60%-of-median fee flag still holds, by $196.70 a month.

## 6. County `[OQ9.county]` `[CORR.county]` `[DIG-277]`

- **Asked on step 1** of every filer, after ZIP code, from the Northern District of Illinois's 18 counties (28 U.S.C. § 93(a); the court's own list):
  - Eastern Division: Cook, DuPage, Grundy, Kane, Kendall, Lake, LaSalle, Will;
  - Western Division: Boone, Carroll, DeKalb, Jo Daviess, Lee, McHenry, Ogle, Stephenson, Whiteside, Winnebago.
- **Spelling:** one stored spelling per county, as listed above. That is the court's spelling for DuPage, LaSalle and DeKalb, and the two-word Jo Daviess of the statute and the U.S. Trustee. Form 101 prints it bare, "Cook". The statute's "Du Page", "La Salle" and "De Kalb", the court page's "JoDaviess", and the U.S. Trustee chart's "<name> County" names (LaSalle as "La Salle County") are other spellings of the same counties; 3h maps them when it joins the IRS tables.
- **Where the list lives:** a constant in the districts app, with each county's division. County membership is statutory, not a dated table, and there is no ZIP lookup (U:321). 3c reads the division for the List of Creditors' heading.
- **Required, as step 1's name, birth date, SSN, address and contact answers are** (`DebtorInfoStep.tsx:65-125`). One flag gates both the step's autosave and Continue (`IntakeWizard.tsx:298`, `:605`), so step 1 doesn't save until a county is picked. Complete's gap and Form 101's precondition (§9) cover sessions saved before 3e1, which have no county.
- **A county outside the district.** The step says, as information, that DigniFi prepares forms for the Northern District of Illinois and lists its counties, so a filer who lives elsewhere sees why there is nothing to pick. It doesn't tell the filer where to file `[UPL]`.
- **Stored** on `Household.county`, encrypted (§4.1). The serializer refuses a county outside the list.

## 7. Joint filing comes off step 1 `[DIG-71]` `[DIG-177]`

- **Removed from step 1:** the Filing Type select and its validation, the "Spouse Information" boxes (name, birth date, SSN) and their info box. The browser stops sending a spouse's SSN that the server drops.
- **`DebtorInfo.filing_type`** stays in its table (no migration of `DebtorInfo`), and it leaves the serializer's fields. New sessions keep the model's default, `individual`.
- **Schedule J line 1**'s rule, `schedule_j_joint_case` (`derivations.py:526-535`), is the one reader of `filing_type`. Today it prints "no" for `individual` and blank for `joint`. It now prints "no" for every session: no step can set `joint` any more, and Complete refuses a case the spouse files too (§9.1), so a session saved as `joint` before 3e1 would otherwise keep a blank line 1 that no answer could change. The rule keeps its name, so its tier 2 key stays, and `filing_type` is left with no reader. Its docstring (`derivations.py:528-530`) and the tests that pin a blank line 1 for a joint session and for one with no Your Information step (`test_schedule_j_schema.py:170-200`) change with it.
- **The frontend types** change with the serializers: `DebtorInfo` loses `household_size`, `filing_type` and `co_debtor_*` (`types/api.ts:65-73`); `IncomeInfo` gains `marital_status`; and `IntakeSession` gains `household` and `spouse_income`.
- **The Codebtors step's sentence** "If you filed jointly with your spouse, they will appear automatically" (`CodebtorsStep.tsx:84-85`) is false today and comes out with joint filing.

## 8. The two steps

### 8.1 Step 1, Your Information

- **Adds County** after ZIP code (§6).
- **Removes** the whole "Household & Filing Information" section and its heading (`DebtorInfoStep.tsx:317-407`): Household Size (`:322-332`, and its validation at `:127-129`), Filing Type and the spouse boxes (§7).
- **Its autosave body** gains `household: {county}` beside `debtor_info`.

### 8.2 Step 2, Income, family first (3e1.Q3)

1. **Your marriage:** line 1 (§3.2).
2. **People in your home, and people you support:** the list (§4.2), with "+ Add a person" and a Remove button per row.
3. **Your income:** today's ten boxes, unchanged.
4. **Your spouse's income:** the same ten boxes, for `married_together` only (§5.1), with today's rule: leave a box blank for a source the spouse doesn't have, and enter $0 in one box for no income at all.
5. **The totals line:** "Your income" and "Your spouse's income", a month each.

**The list's behaviour:**

- **A half-answered line 1.** With "Married and your spouse is NOT filing with you" picked and neither answer under it, the step keeps the pick in its own state and sends `marital_status` null; Complete names the unanswered question. There is no fifth stored answer.
- **The spouse row.** When the filer picks "Living in the same household", and the list has no spouse row and fewer than 20 rows, the wizard adds one with relationship spouse and "Lives with you?" Yes, since that is the filer's own answer. It is added only on that pick, never on load or render, so it never undoes a Remove. It counts as touched, so the body sends it. With 20 rows already, it adds none, and Complete names the mismatch. The Yes rests on the filer's marriage answer, so until the filer sets "Lives with you?" on that row themselves, the wizard keeps it matching that answer: Yes for "Living in the same household", and unanswered for any other, which the step marks. This holds only for a row the wizard added during this visit. A loaded row's answer is the filer's saved answer, and the wizard leaves it alone (U:308: never inferred).
- **"No one else lives with me or depends on me."** With no rows, this button records the answer "no one". A list loaded as `[]` shows it pressed. Answering anything on an added row clears it.
- **What the body sends**, in the list's order: every row loaded from the server, the spouse row the wizard added, and every row the filer added and then answered something on. A row added and never touched is left out. With no row to send, the body sends `[]` while the button is pressed and `null` otherwise, so an empty list is only ever the filer's answer, and a save never drops a stored row the filer didn't remove.
- **The wizard never deletes a row on its own.** A row that no longer fits the marriage answer stays, and Complete names it when it is one of §9.1's mismatches.
- **Unfinished rows don't block.** As the Income step already does for blank amounts, a row with an unanswered question never blocks Continue or autosave: the step marks the question, and Complete names the gap (§9). Autosave and Continue share one flag (`IntakeWizard.tsx:298`, `:605`), so blocking Continue would also stop every save on the step.
- **The guards** keep the step from sending a value the server refuses (§4.2), and only these block saving and Continue, as today's invalid amounts do:
  - "Spouse" is offered only when no other row is the spouse;
  - changing a row away from spouse drops its `spouse_is_dependent`;
  - "+ Add a person" is disabled at 20 rows;
  - an age outside 0–120, or not whole, is an error on the step.

**Its autosave body** is `{income_info: {the ten, marital_status}, household: {members}, spouse_income: {the ten}}`, with `spouse_income` only while the answer is `married_together`. A hidden section therefore neither saves nor blocks, an invalid amount left in it included, and the server keeps the spouse's figures it holds (§5.1). The body is built the same way from loaded and edited data, and each row's `_key` stays in the body and out of the request, as the asset and debt rows' do, so showing the step again sends nothing (CLAUDE.md "Autosave sends only real edits").

**The means-test preview** labels its figure "Monthly income for the means test", since it now includes a spouse's (`MeansTestPreview.tsx:110`).

### 8.3 Review

Review shows the marriage answer in the form's words, the line 13 household count (`household.family_size`, §4.4) and the county. It reads the count from the session the context holds, which every Continue replaces (`update_step` returns the session, `apps/intake/views.py:214-219`; `IntakeContext.tsx:155`), since the wizard's own step state never carries it. A null count shows as not answered yet, since Complete will name the gap.

### 8.4 The fee-waiver page, until 3f

- Its household-size pre-fill (`FeeWaiverPage.tsx:25-30`) comes from 103B line 1's count, `household.fee_waiver_household_size` (§4.4). The function behind it is the one 3f binds to 103B line 1.
- A saved application still wins over the pre-fill. `FeeWaiverApplication` isn't migrated in 3e1; its encryption is DIG-279's, in 3f.

### 8.5 Words

- **DigniFi's own sentences on the steps** (help and information) go in `constants/copy.ts`, where `reading-level.test.ts` scores them.
- **Complete's and the forms' refusal sentences** are the server's, and no test scores them today.
- **Text quoted from the forms** (line 1, the declaration, the instructions' glossary sentence) is kept verbatim in a constant outside `copy.ts` and `upl.ts`, so the test doesn't score it. Line 1 and the declaration are asked in the form's own words (U:76), and the glossary sentence is a quotation. The spouse's question, "Is your spouse a dependent of yours?", is DigniFi's own (§2), so it goes in `copy.ts` and is scored.
- **Line 13's reading is draft.** Line 13 counts the people who live with the filer until counsel rules on C-3 (§4.4), and the umbrella ships wording that waits for counsel marked as draft (U:189, U:633). Here that is the "Lives with you?" help, Review's household count sentence and the means-test preview's "Median for Household of" line, which shows the same count (`MeansTestPreview.tsx:114`): their strings carry a `DRAFT: counsel C-3` comment in `copy.ts`, and C-3 stays on the umbrella's counsel list until counsel signs off, before production. Filers see no mark.
- **Sensitive questions.** Asking where a spouse lives follows the trauma-informed guide: validate without requiring disclosure. Nothing asks why a couple lives apart.
- **No household or spouse value** is ever sent to analytics (`trackEvent`), whose `AuditLog.details` is plaintext.

## 9. Complete and the refusals

### 9.1 Complete's new gaps

In wizard order, then step order. New rows are marked.

| Gap                                                                                                                                                | Step key       | Sentence                                                                                                    |
| -------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------- |
| Name and address (3a1)                                                                                                                             | `debtor_info`  | unchanged                                                                                                   |
| A 9-digit SSN (3a1)                                                                                                                                | `debtor_info`  | unchanged                                                                                                   |
| **County not picked**                                                                                                                              | `debtor_info`  | Choose your county on the Your Information step.                                                            |
| **Marriage question unanswered**                                                                                                                   | `income_info`  | Answer the question about marriage on the Income step.                                                      |
| **"Spouse is filing with you"**                                                                                                                    | `income_info`  | DigniFi prepares forms for one person filing alone. Check your answer about marriage on the Income step.    |
| **Household list unanswered** (null, not `[]`)                                                                                                     | `income_info`  | List the people in your home and the people you support on the Income step, or tell us no one does.         |
| **A row with an unanswered question**                                                                                                              | `income_info`  | Answer every question for each person on your household list on the Income step.                            |
| **The list and the marriage answer disagree**: `married_together` with no spouse row that lives with the filer, or a spouse row with `not_married` | `income_info`  | Your household list and your answer about marriage don't match. Check both on the Income step.              |
| Income not entered by source (3a1)                                                                                                                 | `income_info`  | unchanged                                                                                                   |
| **Spouse's income not entered** (`married_together`, none of the ten)                                                                              | `income_info`  | Enter your spouse's income by source on the Income step. If your spouse has no income, enter $0 in one box. |
| The Expenses step saved (3a1)                                                                                                                      | `expense_info` | unchanged                                                                                                   |
| Unconfirmed scanned debts (3a1)                                                                                                                    | `debts`        | unchanged                                                                                                   |

- **A separated spouse at home is no mismatch.** A spouse row that lives with the filer under "Living separately or are legally separated" passes, since a legally separated couple may share a home. Line 13 then counts the spouse, and 103B line 1 doesn't count them as "Your spouse" (§4.4).
- **One source of truth.** The income-step checks are one function that returns every gap in order. Complete lists them all; the means test raises the first as `IncomeStepGap` (§5.3). A refusal then says the same thing wherever it comes from.
- **Not on save.** Autosave sends half-finished states, so these are Complete's checks, not 400s.

### 9.2 Intakes completed before 3e1

- **They refuse, in plain words, with their step.** Generate, Generate All, Regenerate, an unfiled download and a completed intake's packet list work the means test out again first (`_recalculate_means_test`, `apps/forms/views.py:159-170`). It meets the first income-step gap and refuses with a 422 and its `step`, as `IncomeNotSplit` does. `calculate_means_test` returns it as a 400 with the sentence in `error`, as it does for `IncomeNotSplit` (`apps/intake/views.py:326-333`).
- **No intake completed before 3e1 is given a household of one:** the means test refuses before it reads a count `[U:627]`. The expense calculator's fallback to 1 on an error stays until DIG-152 (§5.3).
- **Form 101** also requires a county: a missing one is a `PreconditionMissing` with step `debtor_info`.
- **A filed form** with stored values downloads them, as now. One with none stored is drawn from the current intake as an unfiled form is (CLAUDE.md "`field_values`, not `form_data`"), so it refuses the same way.
- **Who must re-answer:** every filer whose intake was completed before 3e1, wherever the code runs. That means the owner's own session on production after the eventual deploy, the completed intakes on any self-hosted copy that updates from `main`, and the seeded personas until `seed_demo_data --reset` re-creates them (§11).

## 10. The forms

Every new placement gets its row in `step2_verification.json` in the same commit, citing the box's field-index label and, where it decided the placement, the owner's answer (CLAUDE.md "A new placement needs its addendum row"). Each new derived text rule gets its `RULE_FIXES` entry: `income_info` for the money and household rules, `debtor_info` for the county. `known_defects.json` stays `[]`.

### 10.1 Form 122A-1

- **Line 1, two rules.** One `choices` map can't feed both boxes: `CheckBox3A` has only `together` and `separately`, and any other non-blank answer raises `UnmappedChoice` (`fill_resolver.py:146-150`).
  - The rule for `CheckBox3` maps the four answers to the template's own states, including its misspelled `Maried and filing`: `not_married` → Not married; `married_spouse_filing` → Maried and filing (mapped for completeness: Complete refuses it, so no packet reaches it); `married_together` and `married_separately` → Married but not filing.
  - The rule for `CheckBox3A` returns `together` for `married_together`, `separately` for `married_separately`, and blank otherwise.
  - Each rule gets its own step2 row.
- **Column B** fills, for `married_together` only, each line whose Column A box is bound today, from the spouse's same source: lines 2, 3, 4, 6, 8, 9 and 10, and the Column B total on line 11 (`Debto2.Quest11`). Lines 5 and 7 stay unbound in both columns until 3e2. The 3e1 plan lists every box by full name from the index.
- **Line 11's three boxes.** `Debto1.Quest11` gets a new rule, Column A's total. `Debto2.Quest11` gets Column B's. `Quest11` (both widgets, line 11's total and line 12a) keeps the `cmi` rule, now A + B. The step2 rows of the re-ruled boxes are re-keyed in the same commit.
- **Line 10's description box** serves both columns, and prints "Other income" when the filer's other income is above $0 or, for `married_together` only, the spouse's is.
- **Line 13:** `13B` reads line 13's count; `13C` keeps printing the median the means test used, now looked up by the same count.
- **The `family_size` rule** keeps its name, so its tier 2 case survives. Its refusal step in `RULE_FIXES` moves from `debtor_info` to `income_info`, and the pin at `test_rule_fixes.py:164` moves with it.

### 10.2 Schedule I

- **Column 2, "Debtor 2 or non-filing spouse"**, fills for `married_together` only: each income line whose column 1 box is bound today, from the spouse's same source, and line 10's column 2 total.
- **Line 10's combined box** (`Amount 10`) and line 12 keep `schedule_i_income_total`, now both columns. Column 1's line 10 box (`Amount 10 Debtor 1`) gets a new rule, the filer's own total, and its step2 row is re-keyed. 106Sum line 4 and Schedule J 23a, which copy line 12, move with it, and so does 23c.
- **Line 8h's "Specify"** box serves both columns, like 122A-1 line 10's, with the same `married_together` condition for the spouse's.
- **Stays blank:** Debtor 2's name in the header (U:292), and Part 1's column 2, the spouse's employment status, occupation and employer. The umbrella leaves Schedule I line 1, both columns, to step 4, per step 2's DIG-82 row (U:56).
- **Blank, not 0.00:** a filer with no spouse at home gets a blank column 2. A spouse's source typed as $0 prints 0.00, and one left empty prints blank, as for the filer.

### 10.3 Schedule J line 2

- **`check2`**, "Do you have dependents?": Yes when line 2 has any row (§4.4), No otherwise.
- **The rows** `a` to `e`: each row's relationship (`Dependant Relation 2a` … `2e`), age (`Dependant age 2a` … `2e`) and "Does dependent live with you?" (`check2a` … `check2e`).
- **A repeat group** of five rows with an attached sheet, titled for Schedule J line 2, with columns Relationship, Age and Lives with you. The template has no extra page, so rows past five continue on the sheet (U:145). The group's number is `"2.{n}"`, since the engine numbers rows with digits only, so the sixth dependent is "2.6". No persona has more than two rows; tests prove the sheet on a synthetic household.
- **What changes in the engine**, narrowly:

  1. **A list binding for the household**, `household.dependents[].<attr>`, resolving line 2's rows in list order. It is added to the binding namespaces (`_BINDING_NAMESPACES`, `apps/forms/schema.py:199`, which takes `answer:` and `sofa.` today) and to the sheet-column list check (`_LIST_BINDING`, `:580`, which takes only `sofa.`), and `resolve_binding` gains a household branch (`fill_resolver.py:33-60`). The branch returns each relationship's words from the shared map (§4.2), each age as a whole number, and "Lives with you?" as `yes` or `no`, the states of `check2a`–`check2e`. The slots are `asked` bindings, as SOFA's list slots are, and `fix_for` maps `household.` to `{"step": "income_info"}`, so a refusal on line 2 links to the Income step.
     - **One read of the list per form.** `resolve_parts` resolves each slot binding with its own read (`fill_resolver.py:359`), so a row's relationship, age and answer could come from different reads. The 3a2 plan parked that for the first real rows (R71, m7: "resolve each list once, in a stable order, and read every column from those rows"; part 1, line 227). The household branch meets it: it reads the stored list once per form and takes every column from those rows, in their stored order.
  2. **A sheet column may print a box's answer**, as the field index's `option_text` of the widget the answer maps to ("Yes" or "No"). Today startup refuses a sheet column whose binding a box slot binds (`apps/forms/schema.py:421-428`), and a sheet cell prints its slot's text. That refusal and that cell change. The other two box refusals stay: a box slot whose binding no column prints (`:436-444`), and a box slot with no binding (`:453-463`), since the rows past the slots would drop its answer. The first of them takes its text twin's message, "no sheet column prints …" (`:446-451`), since a column now can print it; the second keeps "a sheet can't tick a box".

  Every other forms.E007 check stays.

- **Flagged for the owner's review.** Both changes revise rules made while 3a2 was built, not ones the owner answered. R64 limited a sheet column to a `sofa.<collection>[].<attr>` list that no box slot binds, and R71 (m12) refused any box slot in a sheet group, bound or not (3a2 plan part 1, line 210); startup's messages say "a sheet can't tick a box". Change 1 widens the list rule to the household, and change 2 lets a column print a bound box's answer. It is the narrowest change that keeps, for line 2, the umbrella's rule that extra rows go "on a generated attached sheet when the template has none" (U:145). The other path, refusing a sixth dependent, would break that rule, so it would need the owner's answer.
- **This makes line 2 the first production repeat group,** a departure from the umbrella, which puts the first production rows in 3e2, 3b and 3c (U:268-272, U:795; §16). Line 2's capacity test and a sheet case on a synthetic household arrive in 3e1. Tier 3 is keyed by persona, and no persona has more than two rows.
- **Line 3** stays unbound: 3e2 asks it `[CORR.J3]`.

### 10.4 Form 101

- **`Debtor1.County`** rebinds from `answer:form_101.county`, a FormAnswer nothing writes, to the stored county `[DIG-277]`.
- **Debtor 2's boxes** stay blank (U:292).

### 10.5 Figures that move with CMI

106Sum lines 4 and 8, Schedule I lines 10 and 12, and Schedule J 23a and 23c print the new totals for Priya and DeShawn, and so does 122A-2 line 1 for Priya, the only one of the two who files it. No form joins or leaves any persona's packet.

## 11. The personas, the seed and the journeys

The persona targets set every answer `[PS]`, except "Is your spouse a dependent of yours?", which the owner answered on 2026-10-24 (§2). 3e1 changes no persona's above- or below-median result, fee routing or packet.

| Persona | Marriage answer    | Household list (relationship, age, lives with, claimed or supported)       | Spouse's income                              | County |
| ------- | ------------------ | -------------------------------------------------------------------------- | -------------------------------------------- | ------ |
| Maria   | `not_married`      | son 8, daughter 5 (both Y, Y)                                              | none                                         | Cook   |
| James   | `not_married`      | `[]`, "no one" given                                                       | none                                         | Cook   |
| Priya   | `married_together` | spouse 45 (Y, Y; spouse a dependent: No); daughter 10 (Y, Y); son 7 (Y, Y) | wages $1,800.00; the other nine $0.00, typed | Cook   |
| DeShawn | `married_together` | spouse 44 (Y, Y; spouse a dependent: No)                                   | wages $1,000.00; the other nine $0.00, typed | Cook   |
| Sarah   | `not_married`      | roommate 29 (Y, N)                                                         | none                                         | Cook   |
| Andrés  | `not_married`      | daughter 9 (Y, Y)                                                          | none                                         | Kane   |

- **The seed** writes `Household` and `SpouseIncome` before it runs the means test inside its atomic create (`seed_demo_data.py:783-784`). `household_size` stays on `DebtorInfo`, unread; `number_of_dependents` goes. The fee-waiver application's household size comes from 103B line 1's count, not `data["debtor"]["household_size"]` (`:791`). Personas seeded before 3e1 are re-created with `--reset`, and the "Seed order" gotcha says so.
- **The E2E fixture** (`frontend/e2e/fixtures/personas.ts`) gains each persona's marriage answer, list, spouse's income and county. `fillDebtorInfo` picks the county and stops filling household size and filing type. `fillIncomeInfo` answers line 1, adds the rows, and types the spouse's amounts. Every journey that passes the Income step uses them, `sofa-journey` (James) and `scanned-bill-journey` included.
- **`test_api_readback.py`** sends the same answers before it presses Complete.
- **Tier 3** gains:
  - Column A's line 11 back for Priya and DeShawn, and each spouse's Column B wages and total;
  - Priya's `Quest11` 13,800.00 and `12B` 165,600.00; DeShawn's `Quest11` 4,500.00 and `12B` 54,000.00;
  - Sarah's `13B` 2 and `13C` 93,934.00;
  - every persona's `Debtor1.County`, line 1 boxes and Schedule J line 2;
  - each spouse's Schedule I column 2, and the totals in §10.5;
  - a pin of Priya's 122A-2 line 1, which no tier 3 case checks today.
- **Tier 2** asserts every new and re-ruled placement. `ASSERTED_CASES` moves from 383 to the number the plan counts, on purpose.

## 12. Docs

- **`CLAUDE.md` gotchas** change wherever 3e1 changes behaviour:
  - "`household_size` defaults to 1" is rewritten for the household list and its counts;
  - "Means test units" gains A + B;
  - "Income is stored by source": the household's CMI, the spouse's amounts, and the `marital_status` sentence;
  - "Blank, not 0.00": a spouse's column now prints for a filer living with their spouse, and Schedule J line 2 is the first production repeat group, so its "No production schema has a repeat group" sentence is rewritten;
  - "Schemas are checked at startup": its sheet clauses (a column binds only a `sofa.<collection>[].<attr>` list, and no box slot, bound or not) change with §10.3's two engine changes;
  - "Forms need a completed intake": Complete's new gaps, `IncomeStepGap`, and `household` and `spouse_income` among the writes that reopen;
  - "Saves lock the session" and "Autosave sends only real edits": the new nested keys and step bodies;
  - "The fee-waiver application": the pre-fill's new source;
  - "Seed order": re-create the personas;
  - a new gotcha for the household list: its ids, null versus `[]`, its one row shape, and its read-only counts;
  - the file map: `Household`, `SpouseIncome`, the county constant, and `cmi.py`'s household function and `IncomeStepGap`, with its "(the one CMI)" label rewritten.
- **The persona briefs** change with the steps, applying 3e1's slice of the persona targets (PS:5, PS:747):
  - Priya's, DeShawn's and Andrés's lose the Household Size and Filing Type rows step 1 no longer asks (`priya-sharma.md:48-49`, `deshawn-mitchell.md:50-51`, `andres-kettleby.md:46-47`);
  - every brief gains its persona's line 1 answer, household list, spouse's income and county (§11);
  - Priya's and DeShawn's lose "your husband's income is not part of it" and "your wife's income is not part of it", which Q2 overturned.

## 13. Testing

- **Tests name outcomes:**
  - a filer living with their spouse is compared to the median on both incomes;
  - a spouse's figures stop counting when the answer changes away from living together;
  - a spouse on a joint tax return isn't listed as a dependent unless the filer says so;
  - Sarah's roommate counts in her household, and her median follows;
  - an empty list counts only when the filer said no one;
  - an intake completed before 3e1 refuses to generate, names the Income step, and its dashboard's packet list refuses the same way rather than failing;
  - a sixth dependent continues on the attached sheet;
  - no spouse SSN leaves the browser;
  - a household, county, marital answer or spouse amount is stored as ciphertext;
  - showing the Income step again sends nothing, so a completed intake stays completed;
  - a half-finished household row saves with the rest of the step.
- **One shared test builder** makes "a session that passes 3e1's new checks" (`not_married`, a list of `[]`, a county). Every fixture that runs the means test, Complete or a forms path uses it, `generated_form_factory` (`apps/forms/tests/conftest.py`, whose `IncomeInfo` holds only wages) included. Every test that builds, sends or asserts `number_of_dependents` or an old marital value changes with it: 51 lines pass `number_of_dependents=` and 47 pass `marital_status="single"`, besides the request bodies, a helper, the means test's `married_joint` and `married_separate` cases and the assertions on the old fields.
- **Ciphertext tests** read the raw column. The library passes plaintext through without error, so a test that only reads the model can't tell.
- **The migration** has a test that runs forward and back with an `IncomeInfo` row present and asserts the restored column holds `""`, and one marked `postgres`, so CI's Postgres pass runs it on a real column type.
- **The session lock test** gains a household PATCH.
- **The gates** are the usual ones:
  - backend pytest with coverage of at least 90%, and ruff 0.8.5;
  - the Postgres tests in CI;
  - vitest, `tsc`, eslint and prettier;
  - the eight E2E journeys.
- **November 1.** The E2E journeys, the seed, the means test and the forms calls that work it out refuse from 2026-11-01 until the November median table is loaded (DIG-315). That table is its own PR, and 3e1's journeys need it if they run after that date.

## 14. Not in 3e1

- **Spouse employment** on Schedule I Part 1 (step 4, U:56).
- **Payroll deductions, business income, the six-month framing and the $0.00 exception** for asked-blank lines (3e2: Q16, Q5, Q26, Q27).
- **Schedule J line 3** (3e2).
- **103B's bindings**: 3e1 supplies the data for "Your spouse" and the dependents count, and 3f binds them. `undefined_3`, the spouse's take-home pay on 103B line 2, has no source in 3e1, which collects gross amounts only. 3f places it, as U:297 says, and also settles where its figure comes from, which U:401 expected from 3e1 (§16).
- **122A-2 lines 3, 5, 7b and 7e**: the marital adjustment and the age-65 split (3h). Ages are stored as given.
- **The expense calculator's fallback to 1** (DIG-152, 3h).
- **`IncomeInfo.monthly_income`**, the old six-month total. It stays one release after it goes live, as CLAUDE.md says. 3e2 migrates `IncomeInfo` again.
- **Encrypting `FeeWaiverApplication`** (DIG-279, 3f).
- **A spouse's pay stub.** Uploads still supply only the filer's employer name.
- **Joint filing.** One filer per packet (U:290).

## 15. Defects found while scoping

These are proposed tickets and comments. Plane gets searched for duplicates, and nothing is filed without the owner's yes.

**3e1 closes or advances:**

- **DIG-53**, marital status never collected, and the seeds' marital statuses: closed by §3 and §11.
- **DIG-65**, 122A-1 never marks the filer's marital status: its marital half is closed by §10.1.
- **DIG-177**, joint filing offered while every form is prepared for one filer: closed by §7.
- **DIG-71**, Debtor 2's boxes bound to the filer's own data: its bindings came off in step 1 (no schema binds a Debtor 2 box to the filer's own data), and its comment on the Joint option's spouse details, sent and dropped, is closed by §7. Its other comment, Form 121's `Check Box3` and ITIN boxes left unbound, still holds, so DIG-71 stays open for it.
- **DIG-159**, the household-size cap: closed by §4.2.
- **DIG-216**, persona briefs and demo seeds that ask for fields the wizard doesn't have: advanced by §11 and §12, which give the seeds and the briefs the marriage, household and county answers the wizard now asks, and take out the step 1 fields it no longer asks.
- **DIG-277**, Form 101 County: closed by §10.4.

**New, proposed:**

- **Guidance docs predict outcomes.** `PLAIN_LANGUAGE_GUIDE.md:71` and `TRAUMA_INFORMED_DESIGN.md:293` say "you typically qualify for Chapter 7", which `UPL_COMPLIANCE.md` forbids.
- **List-editor labels.** The Contracts and Codebtors steps' Relationship, address, type and description labels have no `htmlFor`, and their inputs no `id` (`CodebtorsStep.tsx:127-174`, `ContractsStep.tsx:120,135`). 3e1's household list doesn't copy them.
- **Stale notes.** `schedule_i.unbound.json` and `form_101.unbound.json` still list boxes the schemas now bind.
- **The persona spec's flags.** Maria's child ages are marked "OWNER?" (PS:87), though the owner accepted them (PS:18). Andrés is given Form 103B and 15 forms until 3f (PS:1382, :1411), though 3a1.Q2 gives him no application and 14 forms. And the umbrella (U:382) and the persona spec (PS:258 and six other lines) name `WAIVER_FILERS`, which lived only in the backend's `test_api_readback.py`, though U:382 calls it an E2E list; 3a1 split it into `QUALIFIES` and `APPLIES`.

**For counsel, beside C-3:** Schedule I's Part 2 includes a spouse's income "unless you are separated", while 122A-1 Column B takes it only for a spouse living in the same household and not legally separated. 3e1 collects the spouse's income for "living in the same household" only, so a spouse living apart without a legal separation is in neither column.

## 16. Calls this spec makes

The owner can overturn any of these.

1. **Two new models:** `Household` (county, the list as encrypted JSON, and the next row id) and `SpouseIncome` (ten encrypted amounts). Neither goes on `IncomeInfo` or `DebtorInfo` (§4.1, §5.2).
2. **The four stored marriage answers, and no carry-over of the old values** (§3.2, §3.3). This departs from U:299's "with its data migration": none of the old values is a line 1 answer, so the migration drops them instead of encrypting them. A half-answered line 1 stores null, with no fifth answer (§8.2).
3. **`number_of_dependents` is removed** in 3e1, and `household_size` stays on `DebtorInfo` unread. Schedule J line 1 prints "no" for every session, which leaves `filing_type` unread too; both leave the serializer's fields (§4.3, §7).
4. **The relationship list**, ages 0–120, at most one spouse row, and a cap of 20 rows (§4.2).
5. **Server ids inside the JSON**, never reused, with a sent row replacing the stored one whole; the wizard pairs them by position (§4.2).
6. **The spouse row added when the filer picks "Living in the same household"**, with "Lives with you?" Yes, unless the list already has 20 rows; it counts as touched; until the filer sets its "Lives with you?", the wizard keeps that answer matching the marriage answer, on a row added during this visit only; and the wizard never deletes a row on its own (§8.2).
7. **The "No one else lives with me or depends on me"** button, shown pressed for a list loaded as `[]`; every loaded row is sent again, `null` stands for a list the filer never answered, and the spouse's income is sent only while it is asked (§8.2).
8. **Unfinished rows never block Continue or autosave**; Complete names them, and only invalid values block (§8.2).
9. **County is required on step 1**, as its name, address and contact answers are, and Form 101 refuses without one (§6, §9.2).
10. **One PATCH per step** with a nested `household` key, rather than a separate endpoint saved on Continue (§4.5).
11. **The household's CMI** counts the spouse's only for "living together", their figures stay saved but uncounted when the answer moves away (§5.1), and one exception, `IncomeStepGap`, carries every income-step refusal (§5.3).
12. **The expense calculator** takes 122A-2 line 5's count (§5.3).
13. **County** as a constant with the spellings listed in §6, and the divisions.
14. **Complete's new sentences**, the means test refusing with the same check, and a separated spouse at home counting as no mismatch (§9).
15. **Two rules for 122A-1 line 1**, one per box (§10.1).
16. **Schedule J line 2** as a repeat group with an attached sheet, and the narrow engine change it needs, flagged for review (§10.3). This departs from the umbrella, which puts the first production rows in 3e2, 3b and 3c (U:268-272, U:795).
17. **How a spouse counts:** on Schedule J line 2 by "Is your spouse a dependent of yours?" alone, and on 103B line 1 by the marriage answer: once, as "Your spouse", under "Living in the same household", and under "Living separately or are legally separated" only as a dependent, when line 2 lists them (§4.4).
18. **The read-only counts**, `household.family_size` and `household.fee_waiver_household_size`, null while the income step has a gap, shown by Review (from the context's session) and the fee-waiver page (§4.4, §8.3, §8.4).
19. **The spouse's question in DigniFi's own words**, scored by the reading-level test, since no form asks it (§2, §8.5).
20. **Line 13's draft mark** as a code comment on its strings, with no mark the filer sees (§8.5).
21. **The means-test preview's label** (§8.2).
22. **103B's `undefined_3`** left to 3f, as U:297 says. This departs from U:401, which expects its figure from 3e1; 3e1 collects gross amounts only (§14).
