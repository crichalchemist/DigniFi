# Forms step 3e2: income detail and expenses

- **Status:** revised for the owner's answers, 2026-11-02; drafted 2026-11-01. The owner chose to skip the brainstorming questions, so this spec is written straight from the umbrella. The owner answered its five questions on 2026-11-02, and the spec is now written for those answers throughout. They are listed at the end, under "Owner answers (2026-11-02)". The spec waits for the owner's review of this revision.
- **Drawn from:** the step 3 umbrella spec, `docs/superpowers/specs/2026-10-16-forms-step3-design.md` §5.6 (cited `U:<line>`), its rules U §4.1–§4.7, Appendix A's 3e2 rows (U:717–757 and U:790), counsel item C-10 (U:646) and §8. Persona targets come from `docs/superpowers/specs/2026-10-16-forms-step3-personas.md` (cited `PS:<line>`). The 3e1 spec, `docs/superpowers/specs/2026-10-24-forms-step3e1-design.md`, is cited `E1 §<n>`.
- **Branch:** `feat/forms-step3e2`, from develop `74b2d4b` (3a1, 3a2 and 3e1 merged). The PR targets develop.
- **Section numbers.** A bare `§4.2` is this spec's own section. The umbrella's sections are written `U §4.2`.
- **Tags** such as `[Q16]` trace each part to the umbrella's Appendix A. `[UPL]` is the umbrella's rule that DigniFi gives information, never advice (U:74–80, `docs/UPL_COMPLIANCE.md`).

Inline "**Call (spec author):**" marks each choice this spec makes where the umbrella and the code leave one open. §17 lists them all, and §16 lists every place this spec departs from or adds to §5.6.

## 1. What 3e2 does

1. **Business, rental and interest income** `[Q5]`. The Income step lists each business and rental property with its gross receipts and operating expenses, and asks interest and dividends (§4.2, §4.3).
2. **Government assistance, asked once** `[Q6]`, for Schedule I line 8f (§4.6).
3. **Payroll deductions** `[Q16]`, Schedule I lines 5a–5h, for the filer and a spouse at home, on a new wizard step, "Take-home pay", between Income and Expenses. Schedule I line 7 becomes line 4 less line 6 (§4.5, §7.2).
4. **The six-month window** `[Q26]` `[C-10]`. The step names the actual months and asks "Is your income now different from that average?" (§4.4). The dashboard says when the window has moved (§10).
5. **The Schedule J lines DigniFi never asked** `[Q4.everyday]`, and line 3 in the form's words `[CORR.J3]`, on the Expenses step (§5).
6. **Encryption** `[Q7.income]` of `IncomeInfo`'s amounts and `ExpenseInfo`'s 13 amounts, with their data migrations (§3).
7. **$0.00 for asked-blank lines** on Schedule I and 122A-1 `[Q27]` (§9.6), and the CLAUDE.md gotcha rewritten (§12).
8. **The Schedule I line 8a statement** on an attached sheet. It needs a narrow engine change, flagged for review (§9.2).

No persona's CMI, median result, fee routing or packet changes (§11). Nothing in 3e2 deploys: production waits for steps 3 to 5 and DIG-146 (U:9).

## 2. How this spec was made

- The owner skipped brainstorming. Every decision §5.6 leaves open is made here as a call, unless it changes what gets built and no rule settles it. Those few went to the owner as five questions, answered on 2026-11-02 (end of the spec).
- **Settled by the umbrella, so not asked:**
  - CMI never takes a legal characterization (U:80). So whether government assistance counts in CMI goes to counsel (§4.6, §18).
  - J line 5 is 3c's, from the debts linked to "my home" `[CORR.J45]` (U:436). The persona drafts' line 5 answers are dropped (§16).
  - The filer splits a cost used both for a business and at home; the app never does (U:351). This spec decides only the note (§4.2).
- **The persona targets** fix every figure in §11. The answers they left open were settled by the owner on 2026-11-02 (§11).

## 3. Encryption and the migrations `[Q7.income]`

### 3.1 What is encrypted

| Table                        | Columns                                                                                                                | How                           |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| `IncomeInfo`                 | the ten amounts of today's `SOURCE_FIELDS` (`apps/intake/models.py:98-109`, `:130-202`), and `monthly_income` (`:125`) | migrated with their data      |
| `ExpenseInfo`                | the 13 amounts (`models.py:362-422`)                                                                                   | migrated with their data      |
| `IncomeInfo`, `SpouseIncome` | every new column of §4                                                                                                 | new, encrypted from the start |
| `ExpenseInfo`                | every new column of §5                                                                                                 | new, encrypted from the start |

- **`monthly_income` is included.** It is the old six-month total, read-only and kept one release (`models.py:123-127`). U §4.2 encrypts every plaintext filer column of a table a PR migrates (U:85), and 3e2 migrates `IncomeInfo`.
  - It is a `JSONField(null=True, blank=True)` today (`models.py:125-127`). It becomes an `EncryptedTextField` holding the same JSON array. The migration copies each non-null array in as JSON text (`json.dumps`). A NULL stays NULL, never the text `null`.
  - `IncomeInfoSerializer` still returns it as the array, read-only, by parsing the stored text, as `HouseholdSerializer.to_representation` does for the household list (`serializers.py:372-375`).
  - So its reader sees no change: `IncomeInfoStep.tsx:179` reads it, guarded by `Array.isArray`, and `types/api.ts:74` declares it.
- **`ExpenseInfo.data_source` stays plaintext.** **Call (spec author):** it says how the row was entered (`manual`, `plaid`, `uploaded_document`), not anything about the filer's money, so it is not filer data.
- **`SpouseIncome`** is already encrypted (`models.py:283-334`). It only gains the new columns.

### 3.2 The data migration

No migration in the repo encrypts a column and keeps its data:

- 0017 drops the data (`migrations/0017_incomeinfo_marital_status_encrypted.py:1-44`);
- 0015 alters the columns in place and never re-encrypts the stored rows (`0015_feewaiverapplication_take_home_and_noncash.py:33-54`).

So 3e2 writes its operations by hand. **Call (spec author): each table's re-encryption is three migrations, after 0019.** Then a RunPython never shares a transaction with an ALTER TABLE on PostgreSQL. The repo has mixed them before (`districts/migrations/0003_medianincome_dated_table.py`, `forms/migrations/0005_remove_form_122b.py`, `forms/migrations/0006_field_values.py`), so the split is caution, not precedent. The `postgres` twin of each migration test proves the split runs on real column types. The steps, in order:

1. **AddField** each encrypted column under a temporary name, nullable (the first migration).
2. **RunPython** copies each row's value into it, using the historical model and `save(update_fields=...)`, as 0014 does (`0014_split_income_saved_as_zero.py:37-53`). The save encrypts (the second migration).
3. **RemoveField** each plaintext column, then **RenameField** each encrypted column to the old name. For `ExpenseInfo`, an AlterField then restores `null=False` with its default of 0. An empty body must still create the row with $0 amounts (DIG-153, `serializers.py:533-536`). This is the third migration.

- **The new columns** of §4 and §5 come in a migration of their own after these. `ExpenseInfo`'s new amounts are `null=False` with a default of 0 from the start, like the 13. `calculate_total_monthly_expenses` adds them all (`models.py:434-452`), so none may be NULL.
- **The reverse** runs the same steps backwards. It copies each decrypted amount into a plaintext `DecimalField(max_digits=10, decimal_places=2)` again, and `monthly_income` into a `models.JSONField(null=True, blank=True)` (`models.py:125-127`). An empty `IncomeInfo` amount stays NULL, never 0. A 0 would give an earlier filer $0 income, and so a passed means test (`models.py:128-129`).
- **The reverse refuses rather than loses data.** A value that fails to decrypt reads back as None with no error:

  - the library passes an undecryptable value through (`except cryptography.fernet.InvalidToken: pass`, `encrypted_model_fields/fields.py:74-75`);
  - `EncryptedDecimalField.from_db_value` then turns the failed `Decimal(...)` into None (`apps/intake/fields.py:33-39`).

  So the reverse RunPython raises when a non-NULL raw value decrypts to None, such as one written under another `FIELD_ENCRYPTION_KEY`. Its error names the table and the row id, never the value. `monthly_income` becomes an `EncryptedTextField`, which hands an undecryptable value on as the token itself, not None, so for that column the reverse refuses, with the same error, when the decrypted text doesn't parse as JSON.

- **The key.** RunPython needs a real `FIELD_ENCRYPTION_KEY` (CLAUDE.md). CI has one.
- **Each migration** has a test that runs it forward and back with a row present and checks every value survives: an amount, a NULL amount, a `monthly_income` array and a NULL `monthly_income`. A further test proves the reverse raises on a row whose ciphertext was written under another key. Each has a twin marked `postgres`, which CI's Postgres pass runs on real column types (E1 §13).
- **Ciphertext tests** read the raw column (`test_spouse_and_marriage_storage.py:40-60` is the model). The library passes plaintext through without an error, so a test that only reads the model can't tell (E1 §13).

### 3.3 The serializers

- **Every encrypted amount is declared** as a `DecimalField(max_digits=10, decimal_places=2, min_value=0)`, as `SpouseIncomeSerializer` does (`serializers.py:113-153`). Left to DRF's auto-mapper, an `EncryptedDecimalField`, a subclass of `EncryptedCharField` (`apps/intake/fields.py:9`), becomes a 20-character string field (`max_length = max_digits + 10`, `fields.py:24-25`), with no decimal, range or `min_value` check. A stored amount wider than `DecimalField(12, 2)` would then make every read of the session fail (CLAUDE.md "Debt and asset amounts are readable").
- **`IncomeInfoSerializer`** (`serializers.py:84-110`) and **`ExpenseInfoSerializer`** (`:156-186`) both auto-map today, so both change. Income amounts take `allow_null=True`. Expense amounts take a default of 0.
- **The model's `MinValueValidator`s** on `IncomeInfo` (`models.py:130-202`) go with the plaintext columns. The serializers' `min_value` takes their place.
- No table here has a `Meta.ordering` or an `order_by` on these columns, so nothing sorts ciphertext (DIG-164).

## 4. The Income step's new data

**Call (spec author): one table per person stays.** 3e1 kept the filer's income on `IncomeInfo` and the spouse's on `SpouseIncome` (E1 §16 item 1). Every new income answer goes on both, with the same field names, so a derivation works on either row. A spouse's answers stay saved but stop counting when the marriage answer moves away from living together (E1 §5.1).

### 4.1 The ten sources change by one

- **Rental income leaves the ten.** `monthly_rental_income` is a net figure, and the form wants gross receipts and expenses (§4.2). Its column stays one release, encrypted (§3), unread except by the gap in §8. **Call (spec author):** both serializers return it read-only, as `monthly_income` is, and ignore a write of it. So an old client can't set or clear the legacy gap (`personas.ts:300`, `:385` and `:553` send `monthly_rental_income: 0` today). `SpouseIncomeSerializer` declares it explicitly today (`serializers.py:129-131`) while its `Meta.fields` comes from the tuple (`:153`), so the declaration changes too.
- **Interest and dividends join the ten** as `monthly_interest_and_dividends`, in rental's place in the tuple. It is a CMI source: 122A-1 line 7.
- **So `SOURCE_FIELDS`** stays at ten: wages, overtime, tips, interest and dividends, pension, Social Security, unemployment, child support, alimony, other. `SpouseIncome.SOURCE_FIELDS` is the same tuple (`models.py:290`).
- **Every reader of the tuple or of the rental column changes with it** (from a grep of `SOURCE_FIELDS`, `INCOME_FIELDS` and `monthly_rental_income`):
  - `cmi.py:42` and `:112`;
  - `apps/eligibility/models.py:190`, the means test's `calculation_details`;
  - `models.py:218` (`calculate_total_monthly_income`) and the spouse's column (`:301`);
  - `derivations.py:330`, `:507`, `:518`, `:528-558`, `:708`, `:748` and `:755`: the rental rules, the line 9 sums and Schedule I's line 10 rules;
  - the seed, `seed_demo_data.py:44` and `:584`;
  - `serializers.py:101`, `:129-131` and `:153`;
  - the frontend's `INCOME_FIELDS` (`types/api.ts:100-111`), with its readers: `IncomeInfoStep.tsx:109` (its rental label), `:173-174`, `:184`, `:206` and `:213`; `IntakeWizard.tsx:215-217`, `:275` and `:287`; and the comment at `parseAmount.ts:55`;
  - the E2E fixture's `IncomeSourceKey` and persona values (`frontend/e2e/fixtures/personas.ts:33`, `:300`, `:385`, `:553`), which the page object iterates (`wizard.page.ts:163-166`);
  - `test_api_readback.py`, which needs all ten non-null (PS:1427).

### 4.2 Businesses and rental properties `[Q5]`

**Call (spec author): a list, one entry per business and per property.** Schedule I line 8a says "Attach a statement for each property and business showing gross receipts, ordinary and necessary business expenses, and the total monthly net income." A pair of amounts per person couldn't tell two properties apart.

- **Storage.** `business_and_rental`, an `EncryptedTextField` holding the list as JSON, on `IncomeInfo` and on `SpouseIncome`, with `next_entry_id`. Null means unanswered, and `[]` means the person has none. This is the household list's pattern (`models.py:225-280`, E1 §4.1). **Call (spec author):** `next_entry_id` is a plaintext `models.PositiveIntegerField(default=1)`, as the household's `next_member_id` is (`models.py:238`). It is a counter, not filer data.
- **Each entry:**

  | Key                | Value                                             | Asked as                                                                                                                                                                                                                                                                            |
  | ------------------ | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | `id`               | a whole number from `next_entry_id`, never reused | not asked                                                                                                                                                                                                                                                                           |
  | `kind`             | `business` or `rental`                            | "A business, profession, or farm, or self-employment" / "Rental or other real property"                                                                                                                                                                                             |
  | `description`      | text, up to 200 characters                        | What it is, such as "Rideshare and delivery driving" or the property's address                                                                                                                                                                                                      |
  | `gross`            | an amount, or null                                | Gross receipts (before all deductions), the six-month average. Beside it, 122A-1's own sentence: "If the amount of your monthly income varied during the 6 months, add the income for all 6 months and divide the total by 6." So a business begun inside the window has an average |
  | `expenses`         | an amount, or null                                | Ordinary and necessary operating expenses, the six-month average                                                                                                                                                                                                                    |
  | `current_gross`    | an amount, or null                                | the same, now: asked only when the person's income is now different (§4.4)                                                                                                                                                                                                          |
  | `current_expenses` | an amount, or null                                | the same, now                                                                                                                                                                                                                                                                       |

- **One row shape**, as for the household list: every stored entry carries every key, with null for an unanswered one. Ids, the reply's order and the pairing by position all follow the household list (E1 §4.2, CLAUDE.md "The household list").
- **At most 10 entries per person.** **Call (spec author):** no persona has more than one, and the cap keeps the list and the sheet bounded, as DIG-159's cap of 20 does for the household (`MAX_MEMBERS = 20`, `household.py:18`; E1 §4.2).
- **The net is never typed.** It is gross less expenses, the form's own arithmetic (U:78). The step shows it beside each entry, and the server works it out for the forms.
- **The sums.** 122A-1 has one gross receipts box, one operating expenses box and one net box per person for each kind: line 5 for a business, line 6 for rental property. So each box takes the sum over that person's entries of that kind, and the net is the gross sum less the expenses sum. **Call (spec author):** a loss on one entry nets against a profit on another entry of the same kind.
- **The floor at $0.00** (owner answer 1). A kind's summed net below $0 prints and counts as $0.00. The form itself only says to subtract. The U.S. Trustee Program's means-test guidance says the net "cannot be a negative number". That guidance covers 122A-1 and CMI, and DigniFi applies it there until counsel rules. Schedule I 8a is not a means-test line, and its own words ask only for "the total monthly net income" (§9.2), so flooring 8a and its statement is the owner's extension of that reading (owner answer 1). Both go to counsel, each form apart (counsel item C-12, §18). Precisely:
  - **Per kind, per person, on the summed net.** For each person and each kind, the floored net is the larger of $0.00 and (the gross sum less the expenses sum). The floor never applies to one entry alone, so a loss on one entry still nets against a profit on another of the same kind. A business loss never offsets rental income, or the other way round, and one person's loss never offsets the other's income.
  - **The averages and the current figures alike.** 122A-1 lines 5C and 6C, and CMI, take the floored nets of the averages. Schedule I 8a takes the floored nets of the figures Schedule I uses: the current ones while that person's "now different" answer is Yes, and the averages otherwise (§4.4, §9). Its statement shows each entry's own net and a floor row, so its net column adds to 8a (§9.2).
  - **The gross and expenses boxes are not floored.** 122A-1 5A, 5B, 6A and 6B print the sums as given, so a floored 5C or 6C reads $0.00 beside a larger 5B or 6B.
  - **The statement** shows each entry's own subtraction, which may be below $0, and adds a row for a floored kind that brings the kind up to $0.00 (§9.2).
  - **No gap.** A loss doesn't stop Complete, the means test or any form. No persona has one.
- **The step's information sentences.** **Call (spec author):** each is worked out per person and per kind, on its own set of figures, since the averages and the current figures reach different forms. In DigniFi's words:
  - **On the averages**, below that person's list, while the kind's summed average net is below $0: "For your business income, your operating expenses are more than your gross receipts. DigniFi counts this net as $0.00 on Form 122A-1, and on Schedule I unless your income is now different." (and "For your rental income, …").
  - **On the current figures**, inside "Your income now (a month)", so only under "now different" Yes, while the kind's summed current net is below $0: "For your business income now, your operating expenses are more than your gross receipts. DigniFi counts this net as $0.00 on Schedule I." (and "For your rental income now, …").
  - The plan writes the spouse's twins with the other spouse sentences.
  - **Why:**
    - The step shows each entry's own net, and the totals line would otherwise disagree with the forms without saying why. A silent difference would mislead the filer.
    - Each names only the forms its figures reach: the averages reach 122A-1 always and Schedule I unless "now different" is Yes; the current figures reach Schedule I alone (§4.4).
    - Each names DigniFi, not the form, as the one that counts the net as $0.00, since the form says only to subtract.
    - Each says what the forms do, never what the filer should do `[UPL]`, and carries `DRAFT: counsel` with item C-12 (§7.5, §18).
- **"Do not include any income amount more than once."** 122A-1 says it in its own words: "if both spouses own the same rental property, put the income from that property in one column only." The step quotes that sentence beside the spouse's list. The app can't tell whether two entries are the same property, so the sentence is the only guard.
- **The double-count note.** §5.6 left this to the 3e2 spec (U:351). **Call (spec author): yes, an information note**, beside the operating-expenses box and on the Expenses step. It reads, in DigniFi's words: "If one cost is both for this work and for your home, count each dollar once, in one place only: here or on the Expenses step. How you split it is your choice. Legal aid can help." The Expenses step's copy points the other way: "If one cost is both for your home and for a business or rental property, count each dollar once, in one place only: here or as an operating expense on the Income step. How you split it is your choice. Legal aid can help." Both are marked `DRAFT: counsel` (§7.5). The note gives no example cost, since an example would hint at what counts as an operating expense. Counsel may add examples (§16). Why:
  - Schedule J already warns in its own words against counting a payroll deduction twice (lines 15, 16 and 18), and against counting rental costs twice ("not included in lines 4 or 5 of this form or on Schedule I", line 20).
  - Nothing warns about business costs, and the gig driver's draft found the gap (PS:1428).
  - The note never says what counts as a business cost. Andrés's brief tests exactly that (PS:1357), and "ordinary and necessary" is a legal term `[UPL]`.
  - The note goes to counsel beside C-10, as item C-13 (§18). The umbrella's own examples, "a car, gas or insurance" (U:351), wait for counsel.
- **Form 101 line 12** (sole proprietor) and **Form 107 line 4** (business income) stay in step 4 (U:59, U:349).

### 4.3 Interest and dividends `[Q5]`

- One amount per person, `monthly_interest_and_dividends`, among the ten (§4.1), with an "after" twin for the current figures (§4.4).
- It is asked as "Interest and dividends". 122A-1 line 7 says "Interest, dividends, and royalties", and Schedule I 8b says "Interest and dividends". **Call (spec author):** the box uses 122A-1's words, because the six-month average it asks for is 122A-1's figure.

### 4.4 The six-month window and "now different" `[Q26]` `[C-10]`

**The window.**

- **Worked out on the server** from `fill_date()` (`apps/districts/dated_tables.py:58-60`), never in the browser, by a new function in `apps/eligibility/cmi.py`, `income_window(on: date) -> tuple[date, date]`. It returns the first and last days of the six full calendar months before the fill date's month, as 122A-1 defines them: "For example, if you are filing on September 15, the 6-month period would be March 1 through August 31." A fill date of October 1 and one of October 31 both give April 1 through September 30.
- **The session read** gains a read-only `income_window`, `{"start": "2026-04-01", "end": "2026-09-30"}`. The step names those months: "Your average monthly income for April 1, 2026 through September 30, 2026". **Call (spec author):** each date is written whole, with its year, because the dashboard's `formatIsoDate` always adds the year (`FormDashboard.tsx:121-124`). A window that crosses a year then needs no other wording: a fill date in March 2027 gives "September 1, 2026 through February 28, 2027". `formatIsoDate` builds the words from the ISO parts, never `new Date(iso)` (`FormDashboard.tsx:117-125`). It moves to a shared util, since a second page now uses it.
- **The stamp.** `IncomeInfo.income_period_end`, a `DateField`, nullable. It records the window the filer last confirmed.
  - **Call (spec author): set only by Continue on the Income step**, never by an autosave. The wizard's Continue sends `update_step` with the next step's number, `currentStepNumber + 1` (`IntakeWizard.tsx:360-361`), so Continue on the Income step (step 2) sends 3. Step 3 is now Take-home pay (§7.2), so 3 still means "leaving Income": Continue on Take-home pay sends 4 and stamps nothing. Back and "Go to" move with `moveToStep` and send no `update_step` (`:384-396`). The server sees only the step number (`views.py:197-213`), so it stamps whenever `current_step` is 3, whoever sends it. It sets the stamp to `income_window(fill_date())[1]`. A session with no `IncomeInfo` row has nothing to stamp: the action creates nothing and raises nothing. An autosave of one box changes one figure, and must not clear the dashboard's notice for the other nineteen.
  - **Call (spec author): plaintext.** The stamp records when the filer confirmed the step, as `IntakeSession.completed_at` records when they pressed Complete (`models.py:33`), and nothing about the filer's money.

**The question.** After a person's ten amounts and their list, the step asks in DigniFi's words, which counsel reviews `[C-10]`: "Is your income now different from that average?" For the spouse it asks "Is your spouse's income now different from that average?"

- **Call (spec author): one answer per person.** Schedule I has a column per person, and only one person's income may have changed.
- **Storage.** `income_now_different`, an `EncryptedCharField` holding `yes` or `no`, or null while unanswered, on `IncomeInfo` and `SpouseIncome`.
- **Unanswered blocks.** Schedule I's figures depend on the answer, and treating unanswered as No would answer for the filer (U:77). Complete names it (§8).
- **On Yes**, the step asks the person's current monthly figures. These are the same ten boxes and each entry's `current_gross` and `current_expenses`, under "Your income now (a month)". They feed every Schedule I income line: 2, 3, 8a (the statement too), 8b, 8c, 8d, 8e, 8g and 8h. 8f and 5a–5h are asked only once, as they are now: 8f on the Income step (§4.6), 5a–5h on the Take-home pay step (§4.5). 122A-1 always takes the averages.
- **Storage of the current figures.** **Call (spec author):** `current_` before each of the ten's exact names, such as `current_monthly_gross_wages` and `current_monthly_interest_and_dividends`. Each is an `EncryptedDecimalField`, nullable, on both tables. A tuple, `CURRENT_FIELDS`, names them in `SOURCE_FIELDS`' order. The API, the E2E `input[name=…]` boxes and `test_api_readback.py` use the same names.
- **No pre-fill.** The current boxes start empty, because a pre-filled amount would be an answer the filer never gave (U:77). Under Q27, a current box left blank prints $0.00 (§9.6), so a forgotten box would quietly drop a source from Schedule I. **Call (spec author):** a button, "Start from my average figures", copies the person's averages into the current boxes. The filer presses it, then edits. That is the filer's action, not a pre-selection.
- **On No**, Schedule I uses the averages. Current figures saved under an earlier Yes stay stored and unread, as a spouse's figures do (E1 §5.1).

### 4.5 Payroll deductions `[Q16]`

- **On their own wizard step**, "Take-home pay", after the Income step and before the Expenses step (owner answer 2, §7.2). They are stored with the income, on `IncomeInfo` and `SpouseIncome`, and only the step that asks them moves.
- **Asked in the form's words**, Schedule I lines 5a–5h, for the filer, and for the spouse under "living in the same household" only:
  - 5a. Tax, Medicare, and Social Security deductions
  - 5b. Mandatory contributions for retirement plans
  - 5c. Voluntary contributions for retirement plans
  - 5d. Required repayments of retirement fund loans
  - 5e. Insurance
  - 5f. Domestic support obligations
  - 5g. Union dues
  - 5h. Other deductions. Specify:
- **Typed monthly**, as of now. Schedule I asks for income "as of the date you file this form".
- **Storage.** Eight `EncryptedDecimalField`s, nullable, and the 5h text, an `EncryptedCharField` up to 100 characters, on both tables: `payroll_tax`, `payroll_mandatory_retirement`, `payroll_voluntary_retirement`, `payroll_retirement_loan`, `payroll_insurance`, `payroll_support`, `payroll_union_dues`, `payroll_other` and `payroll_other_specify`. A tuple, `DEDUCTION_FIELDS`, names the eight.
- **Help text**, in DigniFi's words in `copy.ts`, which `reading-level.test.ts` scores:
  - **Per paycheck to monthly:** "Paid every two weeks? Multiply one paycheck's amount by 26, then divide by 12. Paid twice a month? Multiply by 2. Paid every week? Multiply by 52, then divide by 12."
  - **Mandatory and voluntary (5b, 5c):** "Your pay stub or your employer's benefits office can tell you whether your job requires a retirement contribution (mandatory) or you chose it (voluntary)." It doesn't sort any plan for the filer `[UPL]`.
- **A blank** is stored as null, never as $0. It counts as zero in line 6, and prints $0.00 under Q27 (§9.6, §16).
- **All eight blank, with pay.** **Call (spec author):** a person whose Schedule I line 4 is above $0 and who left all eight blank is a Complete gap on the new step (§8). Because the deductions now sit on a step of their own, a filer can reach Review without ever seeing it: a session saved past step 3 before 3e2 (§7.2), or a dashboard link that opens a later step. Printing 0.00 on every line would then answer for them (U:77). A person with no deductions types $0 in one box, as the Income step's rule asks for no income at all (`IncomeInfoStep.tsx:340-341`; the note's first sentence, `:339`, is not a model, §15). A person with no wages, such as Andrés, meets no gap.
- **The arithmetic** (§9.1):

  - line 6 is 5a + … + 5h;
  - line 7 is line 4 less line 6, below $0 if the deductions are larger;
  - line 10 is line 7 + line 9.

  That fixes Schedule I 10 and 12, 106Sum line 4 and Schedule J 23a and 23c.

- **Asked once.** The same amounts feed 122A-2 lines 16–19 in 3h. 3e2 stores them and binds them only on Schedule I (§14).
- **Pay stubs** still supply only the employer's name (CLAUDE.md "Document upload sits mid-wizard"). Pre-filling deductions from a stub waits for DIG-176.

### 4.6 Government assistance, asked once `[Q6]`

The step asks in Schedule I 8f's words: "Other government assistance that you regularly receive. Include cash assistance and the value (if known) of any non-cash assistance that you receive, such as food stamps (benefits under the Supplemental Nutrition Assistance Program) or housing subsidies." Beside it, in DigniFi's words: "Unemployment and Social Security have their own boxes above."

**Call (spec author): flat answers per person, cash and non-cash kept apart.** 3f needs them apart:

- 103B line 3 asks about non-cash help only;
- the § 820.20 figure (U:384) is Schedule I line 12 less the non-cash help.

A list of benefits would need ids and a third list editor for no form's sake.

| Field                      | Value                                                    | Asked as                          |
| -------------------------- | -------------------------------------------------------- | --------------------------------- |
| `assistance_answer`        | `yes`, `no`, or null (unanswered)                        | the question above                |
| `cash_assistance_kind`     | text, up to 100 characters                               | Cash assistance: what kind?       |
| `cash_assistance_amount`   | an amount, or null                                       | How much a month?                 |
| `noncash_assistance_kind`  | text, up to 100 characters, such as "SNAP (food stamps)" | Non-cash assistance: what kind?   |
| `noncash_assistance_value` | an amount, or null for "not known"                       | Its value a month, if you know it |

- **Encrypted from the start**, on both tables. The fee-waiver page's `benefit_types` is a plaintext JSON column (`models.py:744`), so it is not copied. 3f encrypts that page's answers (DIG-279).
- **Not in CMI.** **Call (spec author):** 8f's value stays out of 122A-1 and CMI. Whether a non-cash benefit, or a cash benefit paid under the Social Security Act, is "income" for § 101(10A) is a legal characterization, which is asked or left blank until counsel rules, never derived (U:80). The persona targets left it open (PS:246). It goes to counsel as item C-11 (§16, §18). Maria stays below her median either way: her CMI is $3,200.00 with 8f left out, and $3,550.00 with it counted (PS:247).
- **Until 3f**, the fee-waiver page still asks its own line 3 question, so a waiver filer answers it twice (Maria, PS:140). 3f makes 103B line 3 read this answer and stops the page asking it (U:399, §14).

### 4.7 What counts as income given, and CMI

- **`current_monthly_income(row)`** (`cmi.py:32-51`) adds:

  - the nine sources other than Social Security, interest included;
  - the person's floored business net (122A-1 line 5C);
  - the person's floored rental net (line 6C).

  Each net is that person's gross sum for the kind less its expenses sum, from the averages, and no lower than $0.00 (§4.2). So a loss never lowers CMI. The total is rounded half-even to the cent, as now.

- **"Income not entered by source"** (`IncomeNotSplit`) fires when none of the ten was given and the person lists no entry with a gross or expenses figure. An Andrés with only business income is therefore not refused. The spouse's gap (`cmi.py:112`) changes the same way.
- **A filer whose only income was a legacy rental figure** did enter income, so the legacy gap (§8) names it first, and "income not entered by source" isn't named for that person while it is open.
- **The API's `total_monthly_income`** (`models.py:211-222`) adds the floored business and rental nets of the averages to the ten, Social Security included, so it never shows a loss the means test doesn't count.
- **`calculation_details`** (`apps/eligibility/models.py:188-191`) stores each person's floored business and rental nets beside the ten, the figures CMI added.

## 5. The Expenses step's new data `[Q4.everyday]` `[CORR.J3]`

### 5.1 The new lines

The never-asked lines §5.6 names (U:331), on `ExpenseInfo`, each an `EncryptedDecimalField`, `null=False` with a default of 0, like the 13 (§3.2). A box left empty is stored as $0 and prints blank, as the 13 do (CLAUDE.md "Blank, not 0.00").

| Line | The form's words                                                                          | Field                                                   |
| ---- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| 4a   | Real estate taxes                                                                         | `real_estate_taxes`                                     |
| 4b   | Property, homeowner's, or renter's insurance                                              | `home_insurance`                                        |
| 4d   | Homeowner's association or condominium dues                                               | `hoa_dues`                                              |
| 10   | Personal care products and services                                                       | `personal_care`                                         |
| 13   | Entertainment, clubs, recreation, newspapers, magazines, and books                        | `entertainment`                                         |
| 14   | Charitable contributions and religious donations                                          | `charitable_contributions`                              |
| 16   | Taxes. Do not include taxes deducted from your pay or included in lines 4 or 20. Specify: | `taxes_not_deducted`, and the text `taxes_specify`      |
| 19   | Other payments you make to support others who do not live with you. Specify:              | `support_others`, and the text `support_others_specify` |
| 20a  | Mortgages on other property                                                               | `other_property_mortgages`                              |
| 20b  | Real estate taxes                                                                         | `other_property_taxes`                                  |
| 20c  | Property, homeowner's, or renter's insurance                                              | `other_property_insurance`                              |
| 20d  | Maintenance, repair, and upkeep expenses                                                  | `other_property_upkeep`                                 |
| 20e  | Homeowner's association or condominium dues                                               | `other_property_hoa_dues`                               |
| 21   | Other. Specify: (the text for the existing `other_expenses`)                              | `other_expenses_specify`                                |

- **The three texts** are `EncryptedCharField`s up to 100 characters, blank by default.
- **Group headings, in the form's words:** "If not included in line 4:" over 4a–4d, and line 20's "Other real property expenses not included in lines 4 or 5 of this form or on Schedule I: Your Income." over 20a–20e.
- **The existing 13 are relabelled in Schedule J's words.** **Call (spec author):** two of today's help texts become wrong once the new lines exist: `home_maintenance`'s "Repairs, yard work, HOA fees" (4d is now its own line), and `other_expenses`'s "Clothing, laundry, personal care, pet care, other essentials" (lines 9 and 10) (`ExpenseInfoStep.tsx:141`, `:296`). And three lines now sit beside Schedule I's new deductions, whose own words prevent a double count: 15 ("Do not include insurance deducted from your pay or included in lines 4 or 20"), 16 ("Do not include taxes deducted from your pay or included in lines 4 or 20") and 18 ("that you did not report as deducted from your pay on line 5, Schedule I"). Each line keeps a short help text in DigniFi's words where today's helps.
- **Non-cash help in expenses.** The step quotes Schedule J Part 2's sentence: "Include expenses paid for with non-cash government assistance if you know the value of such assistance and have included it on Schedule I." Maria's SNAP inside J 7's $450 follows it, as the owner accepted (PS:18).
- **Placed elsewhere, unchanged** (U:335-341): J 4's mortgage and line 5 come from 3c's links, and a renter types rent on line 4 as today (U:337); 6d and "Other 6d" stay bound as today (step 2 Q4, U:339); 6a–6c, 15a and 15b are step 4; 17b–17d come from 3c; line 2 came from 3e1.
- **Line 20a and 3c's links.** U:331 puts 20a ("Mortgages on other property") on this step. But Q13 makes a secured debt's monthly payment its only source (U:426), and a mortgage on other property is a debt linked to an asset row. That is the conflict that moved line 5 to 3c (U:436). The owner decided it (owner answer 5): 3e2 asks 20a as a typed amount, the umbrella's explicit list, so a filer with such a mortgage has somewhere to put it. 3c then derives 20a from the debts linked to a property other than the home and retires the typed column (§14). No persona has one.
- **Totals.** `calculate_total_monthly_expenses` (`models.py:434-452`) sums all 26 amounts. It is the one function behind Schedule J 22a, 22c and 23b, 106Sum line 5 and 103B line 6 (`derivations.py:176-184`), so they all move together.

### 5.2 Schedule J line 3 `[CORR.J3]`

- **Asked in the form's words** at the top of the Expenses step: "Do your expenses include expenses of people other than yourself and your dependents?" with No and Yes. Nothing is selected until the filer picks (U:77).
- **Beside it, as information**, the umbrella's example (U:333) in DigniFi's words, with no verdict: "Line 3 asks about the expenses of anyone other than you and your dependents, such as a spouse who isn't your dependent." It quotes no definition of "dependents" beyond the one 3e1 shows, and it carries `DRAFT: counsel` (§7.5).
- **Storage.** `expenses_include_others`, an `EncryptedCharField` holding `yes` or `no`, or null while unanswered, on `ExpenseInfo`.
- **Complete names it** while it's unanswered (§8). Schedule J says "Answer every question."

## 6. Saving and the API

- **One PATCH per step, as now.** `income_info` and `spouse_income` carry the new fields, and `expense_info` carries §5's. The Income step and the Take-home pay step both save into `income_info` and `spouse_income`, each sending only its own keys (§7.4). Today's `update_or_create(..., defaults=income_data)` sets only the keys sent (`serializers.py:529-531`), and `_save_income` keeps that, so one step's save never touches the other's columns. The PATCH already takes the session lock in the viewset (`views.py:152-161`) and reopens a completed intake in the serializer (`serializers.py:508-509`, CLAUDE.md "Saves lock the session"). No new endpoint is added.
- **The serializer's income writes change.** Today `update()` writes the rows with `update_or_create(..., defaults=...)` (`serializers.py:529-531`, `:542-544`), and `create()` writes them with `objects.create(...)` (`:476`, `:485`). That can't mint entry ids, keep `next_entry_id`, store the list as JSON text, clear the legacy rental figure or return the list in the order sent. So, as 3e1 did for the household (`_save_household`, `serializers.py:378-390`; `Household.store_members`, from `models.py:254`):

  - `IncomeInfo` and `SpouseIncome` each gain a `store_entries` method, modelled on `store_members`;
  - new `_save_income` and `_save_spouse_income` helpers write the row, store the entries and clear the legacy figure;
  - both `create()` and `update()` call them.

  The session lock test's `WRITES` gains an "income PATCH" entry whose body carries `income_info.business_and_rental`, as 3e1 added "household PATCH" (§13).

- **The lists.** `business_and_rental` is write-only on the nested serializers. Their representation returns the stored JSON, as `HouseholdSerializer` does (`serializers.py:324-375`). Each entry is checked by an entry serializer modelled on `HouseholdMemberSerializer` (`:307-321`): a `kind` of either value or null, amounts with the filer's bounds or null, and a description of at most 200 characters.
  - A 400 is only for a value no answer can have, or an 11th entry.
  - A missing answer saves, and Complete names it.
  - The reply returns the list in the order sent, each entry with its id.
- **The legacy rental figure clears.** A save that carries a non-null `business_and_rental` sets that row's `monthly_rental_income` to null. The filer has then answered the list that replaces it (§8).
- **`update_step` takes 1 to 9.** The new step makes nine (§7.2). The check and its message, "Must be a whole number from 1 to 8.", and the comment above them change to 9 (`views.py:199-208`).
- **The stamp.** `update_step` with 3, Continue from the Income step, sets `income_period_end` when the session has an `IncomeInfo` row (§4.4). `update_step` already sets a completed intake back to `in_progress` (CLAUDE.md "Forms need a completed intake"), and it takes the session lock before writing (CLAUDE.md "Saves lock the session").
- **The session read** gains `income_window`, read-only (§4.4).
- **`income_now_different` and `assistance_answer`** take `yes`, `no` or null, and anything else is a 400, like `marital_status` (`serializers.py:93-95`). So does `expenses_include_others`.
- **The current figures** are sent only while that person's answer is `yes`. A hidden section then neither saves nor blocks, and the server keeps what it holds (§7.4).
- **Analytics.** No new value is ever sent to `trackEvent`, whose `AuditLog.details` is plaintext (E1 §8.5).

## 7. The wizard

### 7.1 The Income step

**Call (spec author): one step, with sections in this order.** Q5 and Q6 place their questions on the Income step (U:343, U:353). The payroll deductions move to the Take-home pay step (owner answer 2, §7.2), so the step has eight sections, not nine.

1. **Your marriage** (3e1).
2. **People in your home, and people you support** (3e1).
3. **Your income: the six-month average.** The sentence naming the months, then the ten boxes, with interest and dividends after alimony and child support and before unemployment, as on 122A-1 (line 7, then line 8). Today's rule stands: leave a box blank for a source you don't have, and enter $0 in one box for no income at all (`IncomeInfoStep.tsx:340-341`).
4. **Businesses and rental property:** the list (§4.2), with "+ Add a business or property", a Remove button per entry, and a button reading "I have no business or rental income." It works as 3e1's "No one else lives with me" does: `[]` when pressed with no entries, null otherwise. Each entry shows its own net. Below the list, the floor's averages sentence shows while a kind's summed average net is below $0 (§4.2).
5. **Is your income now different from that average?** On Yes, "Your income now (a month)": "Start from my average figures", the ten boxes, each entry's two current amounts, and the floor's current-figures sentence while a kind's summed current net is below $0 (§4.2).
6. **Government assistance** (§4.6).
7. **Your spouse's income**, for `married_together` only: sections 3–6 again for the spouse, with no help text that speaks to the filer, as now (`IncomeInfoStep.tsx:305-307`). The spouse's list carries 122A-1's "one column only" sentence (§4.2).
8. **The totals line:** "Your income" and "Your spouse's income", a month each, now including the entries' floored nets, so the totals match `total_monthly_income` (§4.7).

- **Unfinished answers don't block.** As for 3e1's household rows, an unanswered question never blocks Continue or autosave. Only a value the server would refuse does (E1 §8.2). One flag gates both autosave and Continue (`IntakeWizard.tsx:341`, `:677`), so an invalid amount anywhere on the step stops every save of it. The deductions are no longer on this step, so an invalid deduction no longer blocks saving the income.
- **The means-test preview needs no change.** It shows the server's CMI (`MeansTestPreview.tsx:112`), fetched through `calculateMeansTest` (`useDebouncedMeansTest.ts:58`), and that CMI now includes the floored nets. `MeansTest.calculate()` raises the first Income step gap (`apps/eligibility/models.py:119-121`), and the preview shows a 400's sentence (`useDebouncedMeansTest.ts:70-71`). So it shows the step's refusal until the Income step has no gap left (§8, §16). It shows from step 2 on (`MeansTestPreview.tsx:30`, `useDebouncedMeansTest.ts:46`), and Income stays step 2, so it shows on Take-home pay as on every later step. The take-home pay gap is Complete's alone (§8), so the preview never shows it.
- **Client-side limits.** **Call (spec author):** the new amount boxes use the existing amount validation. The text boxes take the server's limits: a description of 200 characters; 5h, the assistance kinds and the expense texts 100. "+ Add a business or property" is disabled at 10 entries.
- **The Review step** shows the API's `total_monthly_income` (`ReviewStep.tsx:153`), which now includes the floored nets, and the expense total (`:172`), which now covers 26 amounts. **Call (spec author):** it gains one row per new answer: "now different", assistance and the list for each person, and line 3. It also gains a "Take-home pay" section between Income and Monthly Expenses (`ReviewStep.tsx:146-175`), with each counted person's deductions total (line 6), or `NOT_ANSWERED_YET` while all eight are blank and that person's Schedule I line 4 is above $0 (the gap's own test, §8); otherwise line 6 shows as worked out (0.00). Each row shows the answer or `NOT_ANSWERED_YET`, as 3e1's rows do (`ReviewStep.tsx:12`, `:73-77`).
- **When the stamp is older than the window,** the step shows the dashboard's notice at its top (§10). Pressing Continue re-stamps it.

### 7.2 The Take-home pay step

Owner answer 2 puts Schedule I 5a–5h on a wizard step of their own.

- **Its place.** `{ number: 3, label: 'Take-home pay', key: 'take_home_pay' }` in `WIZARD_STEPS`, after `income_info` and before `expense_info` (`frontend/src/constants/wizardSteps.ts:5-14`). Expenses becomes 4, Assets 5, Amounts Owed 6, Contracts & Leases 7, Codebtors 8 and Review & Results 9.
- **What it asks.** §4.5's eight lines and the 5h text, with the help text, for the filer. For `married_together` only, the same again under "Your spouse's deductions", as the Income step shows the spouse's section (`IncomeInfoStep.tsx:170`, `:461`). Beside each person, the step shows Schedule I line 4 (gross pay, from the figures Schedule I uses, §9), line 6 and line 7, worked out from the wizard's step state. Line 4 picks its figures by the same rule as the gaps (§8 "What the gaps test": the current ones under "now different" Yes, the averages otherwise, unanswered included), from the answer and both sets of figures, which the step state holds; each line is then a plain sum or difference, as the Expenses total is. **Call (spec author):** those three figures are shown only, never sent. The forms use the server's arithmetic, as for the Expenses step's running total (`IntakeWizard.tsx:293-296`).
- **What doesn't change with it:**
  - **The documents detour** follows step 1 (`nextStep === 2`, `IntakeWizard.tsx:368`), and Income stays step 2.
  - **The stamp** is still set by `update_step` with 3, which Continue on Income sends (§4.4).
  - **The means-test preview** still shows from step 2 on (§7.1).
  - **The dashboard's fix links** are built from `WIZARD_STEPS` by key (`FormDashboard.tsx:67-70`), so a `take_home_pay` fix reads "Go to Take-home pay" with no new code. Review's "Go to" buttons find the step by key the same way (`IntakeWizard.tsx:602-605`, `ReviewStep.tsx:93-94`).
  - **`test_rule_fixes.py`** reads the step keys from `wizardSteps.ts` (`test_rule_fixes.py:26-32`). So the new key, and every `RULE_FIXES` entry that names it, land in one commit (§9).
- **What changes with it:**
  - **`renderStepContent`** switches on the step's number (`IntakeWizard.tsx:515-612`). **Call (spec author):** it switches on the step's key instead, as `currentStepBody` already does (`:264-266`), and gains a `take_home_pay` case. Its one call, `renderStepContent(step.number)` (`:615-618`), passes `step.key`. A step's number then lives only in `WIZARD_STEPS`.
  - **`currentStepBody`** gains a `take_home_pay` case (§7.4).
  - **The new component**, `TakeHomePayStep.tsx`, takes the same `incomeData` and `spouseIncomeData` state as `IncomeInfoStep` (`IntakeWizard.tsx:119-125`, `:529-542`). So one read of the session hydrates both steps, and each shows what the other last changed.
  - **Unfinished answers don't block**, as on the Income step. Its own validity flag gates its saves, so an invalid deduction blocks only this step.
  - **`update_step`** takes 1 to 9 (§6, `views.py:199-208`). `test_completion.py:125-140` names 9 as a step the wizard doesn't have. It moves to 10, and the test's name drops "eight".
  - **A comment that counts steps:** "Continue on steps 6 and 7" (`IntakeWizard.tsx:161-162`) becomes 7 and 8.
- **Sessions saved before 3e2.** `current_step` is a plain number (`models.py:31`), and the wizard opens the step it names (`IntakeWizard.tsx:193`). Left alone, a session saved at Expenses (3) would open Take-home pay, and one at Review (8) would open Codebtors. **Call (spec author): a data migration** in `apps/intake` adds 1 to every stored `current_step` from 3 to 8, so every session reopens on the step it was on once the new frontend is live. A value outside 1–8, stored before `update_step` checked its range (DIG-151, `views.py:199`), is left as it is. Its reverse subtracts 1 from every value from 4 to 9, and leaves 3 (Take-home pay) as 3, the old Expenses, the step after it, so it loses which of the two a session was on. A test runs it forward, 1, 2, 3 and 8 becoming 1, 2, 4 and 9, and back: 3 stays 3, 4 becomes 3, and 9 becomes 8. During a Heroku deploy the release phase migrates while the old web dynos still serve (`heroku.yml:5-10`, `release` runs `migrate`, beside `run: web:` at `:12-13`), so until each open browser tab reloads, an old bundle reads and writes the old numbers, and a step it stores keeps the new meaning afterwards; this spec accepts it, since nothing in 3e2 deploys (§1). A session saved past step 3 has never seen Take-home pay, so the take-home pay gap (§8) sends a person with pay there before Complete.
- **The seed** writes `current_step=6` (`seed_demo_data.py:825`), which today opens Contracts & Leases. **Call (spec author):** it writes 7, which opens the same step, so a reseeded persona and a migrated one agree. §15 notes the value itself.
- **Frontend tests.** Every fixture or assertion that names a step by its number from 3 up moves by one. A grep of `current_step: <n>` and `updateCurrentStep(<n>)` matches 18 lines in `pages/__tests__/IntakeWizard.test.tsx`, 14 of which name a step from 3 up, and one such line each in `IntakeContext.test.tsx`, `FormDashboard.test.tsx`, `AskModulePage.test.tsx` and `FeeWaiverPage.test.tsx`. `test/fixtures/session.ts` and `test/mocks/handlers.ts` hold only 1 and 2, so they stay. The grep misses number-driven fixtures that move too: the `describe.each` rows `step: 5` and `step: 4` for debts and assets (`IntakeWizard.test.tsx:1237`, `:1267`), the `serveFiler` calls with 6, 7 or 8 (`:2520`, `:2554`, `:2614`, `:2629`, `:2645`, `:2677`, `:2686`, `:2702`), the three `it.each` step tables (`:2507`, `:2570`, `:2588`), and the Go Back walk's title list (`:543-552`), which gains "Take-home pay" between "Expenses" and "Income". It also can't find a test that presses Continue on Income and then expects the Expenses step, so the plan also greps for step titles and step components asserted after a Continue, and for comments that count wizard steps (`steps? [0-9]`), such as `IntakeWizard.test.tsx:124` and `:142` and `ReviewStep.test.tsx:55`. The plan lists each line that moves.
- **Backend tests.** Every fixture or assertion whose `current_step` means Review or a step from Expenses on moves up by one: `test_completion.py:56` and `:381` and `test_session_lock.py:102` (`current_step=8`, Review), and `test_completion.py:128-141` (the refused 9, and the `("completed", 8)` at `:141`). A body sent to prove the field is read-only (`test_completion.py:98`) and a fixture whose number nothing reads (`forms/tests/conftest.py:375`, `test_derivations.py:40`) stay as they are. Thirteen backend test files set `current_step`, and the plan finds the rest by grep, with the step-counting comments (`test_completion.py:541`, `test_api_readback.py:138`). A fixture's 1 or 2 stays.
- **E2E.** Each journey calls `fillIncomeInfo`, then `nextStep`, then `fillExpenses` (for example `maria-happy-path.spec.ts:43-48`, `sofa-journey.spec.ts:57-63`). All eight gain `fillTakeHomePay`, a new page-object method after `fillIncomeInfo` (`e2e/pages/wizard.page.ts:112-171`), and one more `nextStep` between them. The persona fixture's deductions get a field of their own (§11). `scanned-bill-journey.spec.ts:95-98` asserts the step title "Expenses" right after Income, so it gains an assertion of "Take-home pay" between them. Its comment "Continue saves step 5 and stores step 6" (`:109`) becomes 6 and 7. The journeys' and the page object's "Step n" comments are renumbered.

### 7.3 The Expenses step

- Line 3 first (§5.2), then every line in Schedule J's order and words: the existing 13 and the new 13 (§5.1).
- "Other. Specify:" boxes sit beside 16, 19 and 21.
- The running total reads all 26 amounts.

### 7.4 The step bodies and autosave

- **Step 2's body**, Income:

  ```
  {income_info: {the ten, marital_status, business_and_rental, income_now_different,
                 the current ten (only while "yes"), the five assistance fields},
   household: {members},
   spouse_income: {the same, without marital_status}}
  ```

  `spouse_income` is sent only while the answer is `married_together`, as now (CLAUDE.md "Autosave sends only real edits").

- **Step 3's body**, Take-home pay:

  ```
  {income_info: {the eight deductions, payroll_other_specify},
   spouse_income: {the same}}
  ```

  `spouse_income` again only while the answer is `married_together`. A blank deduction is sent as null, never $0 (§4.5). Neither body carries the other's keys, so neither step's saved copy can overwrite what the other saved (§6). Autosave keeps each step's copy under its key (`dataKey`, `IntakeWizard.tsx:337`), so the two copies stay apart.

- **The lists' entries** keep a browser-only `_key`, a loaded entry's id or `new-<n>` from the step's counter. `saveCurrentStepData` leaves it out of the request. The ids pair by position under `listSavesRef`, one key per list (the filer's, the spouse's), and only the newest save of a list writes ids, as for `householdRows` (CLAUDE.md "Nested debts and assets save by id").
- **"Touched" entries**, as for household rows: every loaded entry, and every entry the filer added and answered something on.
- **Step 4's body**, Expenses, is `{expense_info: {the 26 amounts, the three texts, expenses_include_others}}`. A blank amount is sent as 0, the column's default, as now (`IntakeWizard.tsx:293-300`). A blank text is sent as "", and an unanswered line 3 as null.
- **Built the same way from loaded data as from edited data**, so showing a step again sends nothing. `hydrateAmounts` (`utils/parseAmount.ts`) converts every new amount, the entries' and the deductions included, as session data enters step state. `income_window` and `income_period_end` stay out of the body, as read-only fields do.
- **The frontend's types** change with the serializers: `INCOME_FIELDS` (rental out, interest in), new `CURRENT_INCOME_FIELDS` and `DEDUCTION_FIELDS`, `EXPENSE_FIELDS` with 26 names (`types/api.ts:186-206`), and the new keys on `IncomeInfo`, `SpouseIncome`, `ExpenseInfo` and `IntakeSession`.

### 7.5 Words

- **The forms' own words** go in `frontend/src/constants/formText.ts`, which no reading-level test scores:
  - Schedule I's 5a–5h and 8f;
  - 122A-1's "one column only" sentence;
  - Schedule J's line labels, line 3, and the non-cash sentence.
- **The forms' own words** also include 122A-1's averaging sentence beside the six-month boxes (§4.2).
- **DigniFi's own sentences** go in `copy.ts`, where they are scored: the help texts, the double-count note, the window sentence, the "now different" question, the floor's information sentences, line 3's information sentence, the gap sentences and the buttons. The new step's label, "Take-home pay", lives in `WIZARD_STEPS` with the others (`wizardSteps.ts:5-14`). **Call (spec author):** the plan drafts the ones this spec only names, such as the section headings and the button labels. The owner reads the drafts at plan review.
- **Drafts.** The window sentence, the "now different" questions and the dashboard notice carry a `DRAFT: counsel C-10` comment, and C-10 stays on the umbrella's counsel list until counsel signs off (U:189, U:646). The 8f note carries `DRAFT: counsel C-11`, the floor's information sentences `DRAFT: counsel C-12`, and the double-count note and line 3's information sentence `DRAFT: counsel C-13` (§18). Filers see no mark.

## 8. Complete and the refusals

New rows are marked. The table shows every gap in wizard order, then step order.

| Gap                                                                                                                                   | Step key        | Sentence                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 3a1 and 3e1's gaps, up to the household list's                                                                                        | as now          | unchanged                                                                                                                                   |
| **A legacy rental figure:** `monthly_rental_income` above $0 and the list unanswered (null), for the filer                            | `income_info`   | Rental income was saved as one amount. Enter each rental property's gross receipts and operating expenses on the Income step.               |
| Income not entered by source (3a1), now counting entries (§4.7); not named while the legacy gap above is                              | `income_info`   | unchanged                                                                                                                                   |
| **The business and rental list unanswered** (null, not `[]`)                                                                          | `income_info`   | Tell us about any business or rental property on the Income step, or say you have none.                                                     |
| **An entry with an unanswered question** (kind, description, gross, expenses; the two current amounts while "yes")                    | `income_info`   | Answer every question for each business or rental property on the Income step.                                                              |
| **"Now different" unanswered**                                                                                                        | `income_info`   | Answer whether your income is now different from the six-month average, on the Income step.                                                 |
| **"Now different" is Yes, and no current figure given**                                                                               | `income_info`   | Enter your income now on the Income step, or change your answer about whether it is different.                                              |
| **Assistance unanswered**                                                                                                             | `income_info`   | Answer whether you receive other government assistance, on the Income step.                                                                 |
| **Assistance is Yes, and no kind named, or an amount given beside an empty kind**                                                     | `income_info`   | Say what government assistance you receive on the Income step.                                                                              |
| **Assistance is Yes, a cash kind named, and no cash amount**                                                                          | `income_info`   | Enter how much cash assistance you receive a month, on the Income step.                                                                     |
| **The spouse's legacy rental figure**, under `married_together`                                                                       | `income_info`   | Your spouse's rental income was saved as one amount. Enter each rental property's gross receipts and operating expenses on the Income step. |
| Spouse's income not entered (3e1), now counting the spouse's entries; not named while the spouse's legacy gap is                      | `income_info`   | unchanged                                                                                                                                   |
| **The other seven gaps for the spouse** (the list, an entry, "now different" twice, assistance three times), under `married_together` | `income_info`   | the same sentences, for the spouse                                                                                                          |
| **Take-home pay not entered:** the filer's Schedule I line 4 above $0 and all eight deductions blank (§4.5)                           | `take_home_pay` | Enter what is taken out of your pay on the Take-home pay step. If nothing is, enter $0 in one box.                                          |
| **The spouse's take-home pay not entered**, under `married_together`                                                                  | `take_home_pay` | Enter what is taken out of your spouse's pay on the Take-home pay step. If nothing is, enter $0 in one box.                                 |
| The Expenses step saved (3a1)                                                                                                         | `expense_info`  | unchanged                                                                                                                                   |
| **Schedule J line 3 unanswered**                                                                                                      | `expense_info`  | Answer whether your expenses include anyone else's, on the Expenses step.                                                                   |
| Unconfirmed scanned debts (3a1)                                                                                                       | `debts`         | unchanged                                                                                                                                   |

- **What the gaps test.** **Call (spec author):**
  - a current figure is given when at least one of the ten current boxes, or at least one entry's current amount, is not null;
  - a kind is named when its text is not blank;
  - the spouse's sentences swap "your" for "your spouse's" and "you receive" for "your spouse receives", and the plan writes all seven out;
  - a person's Schedule I line 4 is worked from the figures Schedule I uses (§9): the current ones under "now different" Yes, and the averages otherwise, including while that answer is unanswered.
- **Why the list and assistance are gaps.** An unanswered list or assistance question would otherwise print 0.00 under Q27 (§9.6), the same as "none" or No. That would answer for the filer (U:77), as an unanswered "now different" would. The household list's null is a gap for the same reason (`HOUSEHOLD_UNANSWERED`, `cmi.py:71-74`, raised at `:139-140`).
- **The income gaps join `income_step_gaps`** (`cmi.py:164-193`), the one source of truth (E1 §9.1). Complete lists them all, and the means test and every forms call refuse with the first, as `IncomeStepGap` with step `income_info`. The "now different" and assistance gaps don't change CMI. **Call (spec author):** they join anyway. One function keeps every refusal's sentence the same wherever it comes from, as 3e1 did for the household. The household counts on the session read (`household.family_size`) are null while any of them is open (E1 §4.4), and Review shows them as not answered yet.
- **Line 3 is Complete's alone.** It is not income, so it stays out of `income_step_gaps`. An intake completed before 3e2 prints line 3 blank until the filer completes again. The income gaps make every such filer complete again (§8.1).
- **The take-home pay gaps are Complete's alone too.** **Call (spec author):** they stay out of `income_step_gaps`, as line 3 does. Why:

  - Every gap in that list carries the step `income_info`, which `IncomeStepGap` takes from `IncomeNotSplit` as a class attribute (`cmi.py:20-29`, `:54-62`).
  - That list also refuses the means test and its preview, and nulls the household counts on the session read (`serializers.py:349-354`). A gap in it would show on the Income step, before the filer has seen the step that fixes it.
  - Complete protects the forms by itself: every forms call needs a completed intake (CLAUDE.md "Forms need a completed intake"), and every intake completed before 3e2 must complete again (§8.1).

  Complete lists them after every Income step gap and before the Expenses step's, in wizard order (`views.py:256-268`). Deductions never change CMI, so no means test needs them.

- **An unknown non-cash value** is not a gap. The form asks for it only "if known" (§9.1). A cash amount has no "if known", so it is one.
- **Not on save.** As in 3e1, these are Complete's checks, never 400s.

### 8.1 Intakes completed before 3e2

- **They refuse, in plain words, with their step.** None has a "now different" answer, so every forms call refuses with the first Income step gap, a 422 with step `income_info` (`gaps[0]`, `_recalculate_means_test`, `apps/forms/views.py:159-170`). For a filer with a legacy rental figure, that first gap is the legacy one. `calculate_means_test` returns it as a 400, as it does for 3e1's gaps.
- **The dashboard notice (§10) doesn't reach them.** For a completed intake, the packet reply is refused whole while a gap is open (`views.py:276-282`), so the dashboard shows the refusal and its link instead.
- **Who must re-answer:** every filer whose intake was completed before 3e2, wherever the code runs. That includes the owner's own session on production after the eventual deploy (U:627), the completed intakes on any self-hosted copy that updates from `main`, and the seeded personas until `seed_demo_data --reset` (§11).
- **A filed form** keeps its stored values, as now.

## 9. The forms

Every new or re-ruled placement gets its row in `data/forms/field_index/audit/step2_verification.json` in the same commit, citing the box's field-index label (CLAUDE.md "A new placement needs its addendum row"). A re-ruled box's row is re-keyed to its new `derived:<rule>` key. Every new rule gets its `RULE_FIXES` entry (`derivations.py:802`): `take_home_pay` for Schedule I's deduction rules (5a–5h, the 5h text, line 6), `income_info` for every other Schedule I and 122A-1 rule, and `expense_info` for Schedule J's new lines. **Call (spec author):** an entry names one fix only (`test_rule_fixes.py:114`, `len(fix) <= 1`), so a rule that reads both steps needs one. It takes the earlier of its two steps, the file's own rule for Schedule J 23c ("Income less expenses: the earlier of its two steps", `derivations.py:862-863`). So line 7, line 4 less line 6, and lines 10 and 12, and the rules that read them, keep `income_info`. The four removed rules' entries go with them (`derivations.py:823`, `:833`, `:845`, `:853`). `test_rule_fixes.py:113` fails on an entry whose rule is gone. `known_defects.json` stays `[]`.

**Which figures Schedule I uses.** A new helper gives each Schedule I income rule its person's figures: the current ones when that person's `income_now_different` is `yes`, and the averages otherwise. 122A-1's rules always read the averages.

### 9.1 Schedule I

Each line below applies to column 1 (`… Debtor 1`) and, for `married_together` only, column 2 (`… Debtor 2`).

| Line          | Boxes (full names from `form_b106i.index.json`)                                     | Rule and what it prints                                                                                                                                                                                           |
| ------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2, 3, 4       | `Amount 2 Debtor 1`, `Amount 3 Debtor 1`, `Amount 4 Debtor 1`, `Amount 4 Debtor 1a` | today's rules (`derivations.py:477-487`, `:743-750`), from Schedule I's figures                                                                                                                                   |
| 5a–5h         | `Amount 5a Debtor 1` … `Amount 5h Debtor 1`, and `… Debtor 2`                       | new rules, one per line and column: the deduction                                                                                                                                                                 |
| 5h Specify    | `Other deductions 5h` (one box for both columns)                                    | new rule: each counted person's `payroll_other_specify`, joined by "; ", each printed only when that person's 5h is above $0, like 8h's (`derivations.py:349-358`)                                                |
| 6             | `Amount 6 Debtor 1`, `Amount 6 Debtor 2`                                            | new rule: 5a + … + 5h, a blank counting as zero                                                                                                                                                                   |
| 7             | `Amount 7 Debtor 1`, `Amount 7 Debtor 2`                                            | **re-ruled** from the line 4 rule (`schedule_i.json:262`, `:483`) to a new rule: line 4 less line 6                                                                                                               |
| 8a            | `Amount 8a Debtor 1`, `Amount 8a Debtor 2`                                          | **re-ruled** from `schedule_i_rental_*` (`schedule_i.json:279`) to a new rule: the person's floored business net plus floored rental net (§4.2), from Schedule I's figures; never below $0; the statement is §9.2 |
| 8b            | `Amount 8b Debtor 1`, `Amount 8b Debtor 2`                                          | new rule: interest and dividends                                                                                                                                                                                  |
| 8c–8e, 8g, 8h | as bound today                                                                      | today's rules, from Schedule I's figures                                                                                                                                                                          |
| 8f            | `Amount 8f Debtor 1`, `Amount 8f Debtor 2`                                          | new rule: while that person's assistance answer is Yes, the cash amount plus the non-cash value, of those given; under No, 0.00 whatever is stored                                                                |
| 8f Specify    | `Assistance 8f@2:T36`, tagged                                                       | new rule: each counted person's kinds, cash first, joined by "; ", read only while that person's answer is Yes; under No, blank                                                                                   |
| 9             | `Amount 9 Debtor 1`, `Amount 9 Debtor 2`                                            | today's rule names, now 8a + 8b + … + 8h (`derivations.py:514-525` had no 8b or 8f)                                                                                                                               |
| 10            | `Amount 10 Debtor 1`, `Amount 10 Debtor 2`                                          | today's rule names, now line 7 + line 9 as the form says. Today they add the ten sources (`derivations.py:528-539`), which equalled 7 + 9 only while line 7 equalled line 4                                       |
| 10 total, 12  | `Amount 10`, `Amount 12`                                                            | `schedule_i_income_total`: column 1 + column 2 of line 10. Line 11 stays unasked and counts as zero                                                                                                               |

- **`Assistance 8f` is two widgets of one name**: the 8f "Specify" box (T36) and line 11's (T49). The binding carries `tag: "T36"`, so its key is `Assistance 8f@2:T36`, and line 11's box stays blank until step 4 (PS:115, U:247). This is the first production use of the per-widget selector, which 3a2 expected in 3e2, 3b or 3c (`2026-10-17-forms-step3a2-design.md:348`).
- **8f when the value is unknown.** **Call (spec author):** a person who answers Yes, names only non-cash kinds and gives no value gets a blank 8f amount, with the Specify text printed. Under No, 8f prints $0.00 (Q27) and its Specify stays blank, even when kinds or amounts saved under an earlier Yes are still stored; they stay stored and unread, as the current figures do (§4.4). The form asks for a non-cash value only "if known", so a value the filer doesn't know is a legitimate blank (U:126). Printing $0.00 beside a named benefit would state a value nobody gave. This is a narrow exception to Q27 (§16). A cash kind with no amount, and an unanswered question, are gaps (§8), so 8f never meets them at forms time.
- **Stays blank:** line 1's unbound boxes, both columns (step 4, U:56): the employment status, `Time employed Debtor 1` (one name with a widget in each column, T28 and T29, so step 4 must tag it), `Employers Street2`/`Street3` and the Debtor 2 column. The Debtor 1 occupation and employer boxes keep printing as today (`schedule_i.json:41`, `:58-126`). Also the header's `Debtor 2`, `Amount 11`, `Check increase` and `Increase/Decrease 13` (step 4, `[Q6.lines11_13]`).
- **Renamed or removed rules.** `schedule_i_rental_debtor1` and `schedule_i_rental_spouse` go, since rental is no longer a source. Their tier 2 entries and step2 rows are re-keyed to the 8a rule. `schedule_i_gross_income_*` keeps lines 4 and 4a.

### 9.2 The line 8a statement

**What the form asks.** "Attach a statement for each property and business showing gross receipts, ordinary and necessary business expenses, and the total monthly net income." Schedule I has no 8a rows to fill, so every entry goes on the statement.

**The sheet.** One attached sheet (`apps/forms/services/sheets.py`), in the format 3a2 built:

- **Its header:** the filer's name, the title "Official Form 106I, Schedule I: Your Income, line 8a" with " (attached sheet)", and a blank "Case number (if known)" (`sheets.py:6-9`).
- **Its rows:** every counted entry, the filer's in stored order, then the spouse's for `married_together`. A floor row follows a person's entries for each kind floored at $0.00 (below).
- **Its columns**, 468 pt in all beside the 36 pt line column (`sheets.py:46-47`):

  | Label                                    | Width | Cell                                                                                                                         |
  | ---------------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------- |
  | Income of                                | 96    | "Debtor 1", or "Non-filing spouse"                                                                                           |
  | Property or business                     | 132   | "Business: " or "Rental property: ", then the description                                                                    |
  | Gross receipts                           | 80    | the figure Schedule I uses (§9); blank on a floor row                                                                        |
  | Ordinary and necessary business expenses | 80    | the same                                                                                                                     |
  | Total monthly net income                 | 80    | gross less expenses, the entry's own subtraction, even below $0; on a floor row, the amount that brings the kind up to $0.00 |

- **Each row's line.** **Call (spec author): the number `"{n}"`**, so rows read "1", "2" under a title that names line 8a. `"8a.{n}"` was measured with PyMuPDF's Helvetica at 10 pt: row 9999's "8a.9999" is 36.14 pt wide. The line column's text has 32 pt (36 less 2 pt of padding each side, `sheets.py:47-48`), so forms.E007 would refuse it (CLAUDE.md "Schemas are checked at startup"). "8a.1" is 19.46 pt.
- **A row below $0** prints with its minus sign. `_fmt` quantizes and prints the decimal as it is (`derivations.py:75-76`), as Schedule J 23c already prints below zero (`:587-591`).
- **The floor on the statement.** **Call (spec author):** each entry's row shows its own subtraction, and one more row follows a person's entries when that person's summed net for a kind is below $0. Why not floor each row:

  - entries of one kind net against each other (§4.2). A business making $1,000 beside one losing $500 nets $500, but floored rows would add to $1,000;
  - the statement asks for each property's and business's own figures, and an entry's figures are what the filer gave.

  **Call (spec author):** the floor row's cells are the person ("Debtor 1" or "Non-filing spouse"); "Business total below $0, brought up to $0.00" or "Rental property total below $0, brought up to $0.00"; a blank gross receipts cell and a blank expenses cell, so neither column counts the kind twice; and, as its net, the kind's summed net with its sign turned, the amount that brings the kind up to $0.00. A business earning $600 beside one losing $1,100 nets −$500, so its floor row's net is 500.00. It comes after that person's last entry, business before rental, and takes a `"{n}"` number like any other row. So each person's net cells, floor rows included, add to that person's 8a: the sum over kinds of the larger of $0.00 and that kind's rows' nets. The row's words are DigniFi's and carry `DRAFT: counsel C-12` (§18). No persona has one.

- **When it prints.** Whenever any counted entry exists, even at $0. No entry, no sheet.
- **Stored as today's sheet part**, `{"kind": "sheet", "group": "i_line_8a", "title", "columns", "name", "rows"}`. `check()` and `fill()` read the title, columns and rows from the part (`sheets.py:167-176`), so a filed statement redraws exactly as filed, whatever the schema says later.

**What changes in the engine**, narrowly. Today a sheet only takes a repeat group's rows past its last slot:

- `resolve_parts` builds groups from the fields that name a `repeat` (`fill_resolver.py:375-418`);
- `_sheet` takes each cell from the slot that binds the column ("one at least: E007", `:304`);
- E007 refuses a sheet column no slot binds (`schema.py:412-420`).

The 8a statement has no slots. So:

1. **A statement group.** A group declared in the schema's `groups` with a `sheet`, no `extra_page`, and no field naming it as its `repeat`. `resolve_parts` resolves each column's binding once and prints every row on the sheet (capacity 0), when there is at least one row. A cell is the column's text at that row. A statement group has no box columns.
2. **A list binding for the entries**, `income.statement[].<attr>`, with `attr` one of `owner`, `description`, `gross`, `expenses` and `net`. **Call (spec author):** `description` returns the cell's whole text, "Business: " or "Rental property: " then the entry's description, so no `kind` column is needed. The list holds the entries and the floor rows, in the sheet's order. On a floor row, `description` is the floor row's words and `gross` and `expenses` are "".

   - It joins the sheet-column list pattern (`_LIST_BINDING`, `schema.py:577`, checked at `:621`). It stays out of `_BINDING_NAMESPACES` (`:199`), which checks only a field's binding (`:292`), since no field binds `income.`.
   - `resolve_binding` gains an `income.` branch (`fill_resolver.py:71-78` is the household one to copy).

   The branch reads both rows once per form and takes every column from that one read, as the household branch does (E1 §10.3).

3. **A statement column's fix comes from its binding.** Today `sheets._fixes` finds a column's fix through the group's slot that binds the column (`sheets.py:230-245`). A statement group has no slot, so every column would get `{}`. `fix_for` takes a `FieldSpec`, not a binding string (`fill_resolver.py:131-151`). So its `answer:`, `sofa.` and `household.` branches move into a function of a binding string, which `fix_for` calls. It gains `income.` → `{"step": "income_info"}`, and `sheets._fixes` calls it for a statement group's columns. A refused cell (a letter the font can't print, a word wider than its column) then links to the Income step.
4. **E007 for a statement group.** The slot checks sit in a loop over the groups that have slots (`schema.py:340-478`), so a slotless group never meets them. `_sheet_errors` runs for every declared group with a `sheet` (`:496-498`). What changes:
   - `_LIST_BINDING` admits `income.statement[]` (item 2);
   - a new check: every column of a statement group binds the same `income.statement[]` list;
   - the line-column check today measures `capacity + 1` and row 9999 only when the group's slots give a capacity (`schema.py:522-523`), so a slotless group skips it. For a statement group it measures row 1 and row 9999;
   - every other sheet check stays: widths, labels and the title printing whole, `{n}` in the `number`, and no `page_numbers` (`schema.py:496-640`).

**Call (spec author), for review with the spec.** These revise rules made while 3a2 was built, not ones the owner decided, so they stay calls. A sheet so far only continues a group's rows (3a2 spec §5.3, R64, R71). It is the narrowest change that keeps the umbrella's "The Schedule I 8a statement prints on 3a2's sheet generator" (U:349, U:266). The other path, a separate statement form with its own registry entry and template, would break the umbrella's rule that a sheet "needs no registry entry, schema or field index" (U:266).

**Tests.** A capacity-style case with two businesses for the filer and a property for a spouse at home. The rows number 1, 2, 3 across both people, and each column's 8a equals the sum of its person's rows' nets. A second case gives the filer a business losing more than another earns, and a profitable property: the losing row prints below $0, a floor row follows with blank gross and expenses cells, and 8a is the property's net alone, the sum over kinds of the larger of $0.00 and each kind's rows' nets. In both cases each person's net cells add to that person's 8a. A spouse's entry stops printing when the answer moves away from living together. A filed statement redraws exactly. A refused description links to `income_info`.

### 9.3 Form 122A-1

Column A reads the filer's averages, and Column B, for `married_together` only, the spouse's.

| Line   | Boxes (full names from `b_122a-1.index.json`)                                                               | Rule                                                                                                                                                                                                                                                 |
| ------ | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 5A, 5B | `Debto1.Quest5A`, `Debto1.Quest5B`; `Debto2.Quest5A`, `Debto2.Quest5B`                                      | new rules: the sum of the person's business entries' gross, and of their expenses                                                                                                                                                                    |
| 5C     | `Debto1.Quest5C` (two widgets, T24 and T26: the worksheet box and "Copy here"); `Debto2.Quest5C` (T25, T27) | new rule: 5A less 5B, no lower than $0.00 (§4.2). One untagged key fills both widgets, as the form wants                                                                                                                                             |
| 6A, 6B | `Debto1.Quest6A`, `Debto1.Quest6B`; `Debto2.Quest6A`, `Debto2.Quest6B`                                      | new rules: the rental entries' gross, and their expenses                                                                                                                                                                                             |
| 6C     | `Debto1.Quest6C` (T32, T34); `Debto2.Quest6C` (T33, T35)                                                    | **re-ruled** from `line3_real_property_income` and its spouse twin (`derivations.py:329-330`, `:708`) to 6A less 6B, no lower than $0.00, as 5C                                                                                                      |
| 7      | `Debto1.Quest7`, `Debto2.Quest7`                                                                            | new rules: interest and dividends                                                                                                                                                                                                                    |
| 11     | `Debto1.Quest11`, `Debto2.Quest11`, `Quest11`                                                               | unchanged rules, now with lines 5, 6 and 7 inside CMI (§4.7). `Quest11` is one name on two widgets, T19 (line 11's total) and T20 (line 12a, "Copy your total current monthly income from line 11"), so one key fills both, the same value by design |

- **Stays blank:** `Debto1.Quest8A` and `Debto2.Quest8A`, the unemployment the filer "contend[s] … was a benefit under the Social Security Act". DigniFi doesn't ask it, and it is a legal contention `[UPL]`. Also line 10's second row, which nothing asks: its amounts `Debto1.Quest10B` (T13) and `Debto2.Quest10B` (T14), and its source text box, `terrorism If necessary list other sources on a separate page and put the total below 2` (T12). And line 10's totals from separate pages, `Debto1.Quest10C` (T15) and `Debto2.Quest10C` (T16).
- **Removed rules:** `line3_real_property_income` and `line3_real_property_income_spouse`. Their tier 2 entries move to the 6C rule.
- **Line 10** keeps "Other income". For Andrés it now prints 0.00 and no source text, since his driving moved to line 5 (§11).

### 9.4 Schedule J

| Line          | Box (full name from `form_b106j.index.json`)                                               | Rule                                                                                                |
| ------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| 3             | `check3`, choices `{"yes": "/yes", "no": "/no"}` like `check2`'s (`schedule_j.json:86-92`) | new rule: the stored answer; blank while unanswered                                                 |
| 4a, 4b, 4d    | `4a`, `4b`, `4d`                                                                           | new rules, each through `_expense_line` (`derivations.py:572-580`): the amount above $0, else blank |
| 10, 13, 14    | `10`, `13`, `14`                                                                           | the same                                                                                            |
| 16            | `16`, and the text `Other 16`                                                              | the amount; the text printed only when the amount prints, as `_expense_label` does (`:582-584`)     |
| 19            | `19`, and the text `Other 19`                                                              | the same                                                                                            |
| 20a–20e       | `20a` … `20e`                                                                              | the amounts                                                                                         |
| 21            | `Other 21`                                                                                 | new rule: the filer's text, printed only when `21` prints. `21` keeps `schedule_j_other_expenses`   |
| 22a, 22c, 23b | as bound                                                                                   | unchanged rule, now over 26 amounts (§5.1)                                                          |
| 23a, 23c      | as bound                                                                                   | unchanged rules, which now read Schedule I line 12 with deductions (§9.1)                           |

- **Line 22b stays blank.** **Call (spec author):** "Copy line 22 (monthly expenses for Debtor 2), if any, from Official Form 106J-2". Form 106J-2 is only for a joint case whose Debtor 2 lives apart, and joint filing is out (U:70). So 22c = 22a, as today. §5.6 never names 22b.
- **Line 24 stays blank, for step 4.** **Call (spec author):** "Do you expect an increase or decrease in your expenses within the year after you file this form?" is Schedule I line 13's twin, which the owner put in step 4 `[Q6.lines11_13]` (U:56). Both look a year ahead. Asking one in 3e2 and the other in step 4 would ask the filer the same thing in two places at two times. §5.6 never names line 24, so this spec adds it to step 4's list (§16).
- **`check1a`** (line 1's separate-household question) stays blank: it applies only to a joint case.

### 9.5 The other forms

- **106Sum line 4** (Schedule I line 12) and **line 5** (Schedule J 22c) move with their sources. Line 8 (CMI) doesn't move for any persona.
- **103B:** line 6 (J 22c) moves with the new lines. Lines 2 and 3 still print the fee-waiver page's answers until 3f (§14).
- **122A-2:** nothing new is bound (§14). Lines 19 and 21 keep J 18's and J 8's amounts (`form_122a2.json:58-83`).

### 9.6 Blank versus zero on Schedule I and 122A-1 `[Q27]`

- **The rule.** On Schedule I and 122A-1, a line DigniFi asked and the filer left blank prints 0.00, but only in a column that applies to the filer (U:131-140):
  - column 1 and Column A always apply;
  - column 2 and Column B apply only for `married_together`, and stay blank otherwise.
- **The asked lines** are every line in §9.1 and §9.3 that DigniFi computes from a person's answers: Schedule I 2–10 and lines 10 and 12, and 122A-1 lines 2–7, 8, 9, 10's first amount and 11. Column B's line 4 box has an odd name, `Debto2.Quest2.2` (T19), bound to `line6b_child_support_alimony_spouse` (`form_122a1.json:293`); the plan and tier 3 list it under that name.
- **Stays blank, because never asked:** Schedule I line 1's unbound boxes, 11 and 13; 122A-1 `Quest8A`, and line 10's second row (both amounts and its source text) and separate-page totals, both columns (§9.3); and both forms' Debtor 2 header boxes.
- **One helper.** `_given_amounts` (`derivations.py:96-102`) keeps returning "" when nothing was given, for every other form. A new helper for these two forms returns "0.00" instead when its row exists. The rules here call that one. The only exception is 8f with only a non-cash kind named and no value (§9.1).
- **Line 7 and the totals** follow the form's arithmetic over the printed figures, a blank counting as zero.
- **Every other form keeps "blank, not 0.00"**, Schedule J included. Its 26 amounts are stored as $0 when left empty, so a J line prints only above $0 (CLAUDE.md).

**The conflict with today's gotcha, resolved from the umbrella.** CLAUDE.md's "Blank, not 0.00" says "a line DigniFi never asks (interest, payroll deductions, priority) and an income source left empty print blank". U §4.5 and Q27 say an asked line left blank prints $0.00 on these two forms. The umbrella is the binding authority (U:5), so 3e2 follows it and rewrites the gotcha (§12):

- interest and payroll deductions are now asked;
- an income source left empty prints 0.00 on Schedule I and 122A-1 in a column that applies;
- it still prints blank everywhere else.

## 10. The dashboard notice `[Q26]` `[C-10]`

- **The packet reply** (`GET /api/forms/packet/`, `apps/forms/views.py:263-285`) gains `income_period`:

  ```
  {"answered_for": {"start", "end"} or null, "now": {"start", "end"}}
  ```

  `answered_for` comes from `income_period_end`, and `now` from `fill_date()`.

- **When the two differ**, the dashboard shows, beside the median-table notice (`FormDashboard.tsx:128-133`, `:414-416`): "Your income figures are your monthly average for April 1, 2026 through September 30, 2026. If you file now, the six months are May 1, 2026 through October 31, 2026. Check your income on the Income step." It links to `/intake?step=income_info`. The months are words, as `formatIsoDate` builds them. With `answered_for` null, it reads "Check that your income figures are your monthly average for …".
- **Information, not a refusal.** The umbrella asks the filer to check (U:368). Nothing refuses to generate. The notice rides on the packet reply, so it shows only when that reply succeeds: a completed intake with an open gap gets the refusal instead (§8.1).
- **How it clears.** The filer opens the Income step, checks the figures and presses Continue. Continue always saves (CLAUDE.md "Autosave sends only real edits"), and its `update_step` re-stamps the period (§4.4). An autosave never clears the notice. Continue also reopens a completed intake, so the filer presses Complete again.
- **The wording is draft** for counsel `[C-10]` (§7.5).

## 11. The personas, the seed and the journeys

The persona targets set every figure `[PS]`. The owner settled the answers they left open on 2026-11-02 (owner answer 3): J line 3, the spouses' "now different" No, and James's deductions and new J lines, which the targets mark "OWNER TO APPROVE" (PS:354, :370); 3e2 drops the two marks (§12). The spouses' "now different" No is read from the reasons the targets give: "his online tutoring runs year-round" for Priya's husband (PS:600), and "both paychecks have been steady all year" for DeShawn's wife (PS:789). The window in every target is April 1 through September 30, 2026: the root conftest pins the backend's `_today` to 2026-10-16 (CLAUDE.md "Dated tables and the fill date").

| Persona | Deductions (monthly)                                                                     | 8f                                       | Business, rental, interest                                                                                                        | New J lines                                                                                                                           | J line 3                             | Now different |
| ------- | ---------------------------------------------------------------------------------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ | ------------- |
| Maria   | 5a $400; 5b–5h typed $0 (PS:107-110)                                                     | Yes: non-cash "SNAP (food stamps)", $350 | none; interest $0                                                                                                                 | 10 $40; the rest $0; Other 21 "School supplies and fees" (PS:116-122)                                                                 | No (PS:93)                           | No            |
| James   | 5a $1,288, 5g $45, the rest blank (PS:354-366; the $4,500 take-home was accepted, PS:17) | No                                       | none; interest $0                                                                                                                 | 4b $15, 10 $40, 13 $45; Other 21 "Work boots and small tools for my job" (PS:370-376)                                                 | No (PS:343)                          | No            |
| Priya   | hers 5a $2,450, 5c $600, 5e $620; his 5a $250 (PS:602-611)                               | No, both                                 | none; interest $0, both                                                                                                           | 4b $20, 10 $60, 13 $80, 14 $50, 16 $200 "IRS installment agreement, 2025 tax"; Other 21 "Children's after-school activities" (PS:613) | Yes                                  | No, both      |
| DeShawn | his 5a $450; hers 5a $115 (PS:795-814)                                                   | No, both                                 | none; interest $0, both                                                                                                           | 10 $40, 13 $25, 14 $50; Other 21 "Printer ink, paper and postage" (PS:817-829)                                                        | Yes, from a conflicts note (PS:1002) | No, both      |
| Sarah   | 5a $250, the rest blank (PS:1053-1057)                                                   | No                                       | none; interest $0                                                                                                                 | 10 $30, 13 $20; `other_expenses` $50 → $0 (PS:1058-1064)                                                                              | No                                   | No            |
| Andrés  | all blank: no paycheck (PS:1293)                                                         | No                                       | business "Rideshare and delivery driving", gross $4,200, expenses $830; `monthly_other_income` $3,370 → $0; interest $0 (PS:1386) | 4b $15, 10 $40, 13 $30, 14 $20, 16 $150 "2026 estimated income tax" (PS:1388)                                                         | No                                   | No            |

- **J line 3, as the owner approved it:**
  - **Priya, Yes:** her husband is not her dependent, and their expenses include his, which is the umbrella's own example (U:333).
  - **Sarah, No:** her roommate pays the landlord directly, so her expenses are her own (PS:1022).
  - **Andrés, No:** his daughter is his dependent.
  - **DeShawn, Yes:** from the targets' conflicts note (PS:1002).
- **Dropped:** the targets' J line 5 answers, since 3e2 doesn't ask line 5 `[CORR.J45]`.

**The figures each persona's forms move to**, each worked from the targets and checked by hand in the plan:

| Persona | Schedule I line 7 (col 1 / col 2) | Line 12, 106Sum 4, J 23a | J 22a, 22c, 23b, 106Sum 5 | J 23c    | CMI (unchanged) |
| ------- | --------------------------------- | ------------------------ | ------------------------- | -------- | --------------- |
| Maria   | 2,800.00                          | 3,150.00 (8f 350)        | 2,560 → 2,600.00          | 550.00   | 3,200.00        |
| James   | 4,500.00                          | 4,500.00                 | 3,110 → 3,210.00          | 1,290.00 | 5,833.00        |
| Priya   | 8,330.00 / 1,550.00               | 9,880.00                 | 6,640 → 7,050.00          | 2,830.00 | 13,800.00       |
| DeShawn | 3,050.00 / 885.00                 | 3,935.00                 | 2,295 → 2,410.00          | 1,525.00 | 4,500.00        |
| Sarah   | 1,750.00                          | 1,750.00                 | 1,280.00                  | 470.00   | 2,000.00        |
| Andrés  | 0.00                              | 3,370.00 (8a 3,370)      | 2,779 → 3,034.00          | 336.00   | 3,370.00        |

- **Q27 zeros** (PS:238, :495-502, :1136-1140, :1415-1416): every asked-blank line prints 0.00. That includes Schedule I 8b and 122A-1 `Debto1.Quest7`. Five personas' tier 3 rows change from "" to "0.00": Maria (`test_oracle_tier3.py:74`, `:86`), James (`:119`, `:131`), Priya (`:157`, `:172`), DeShawn (`:209`, `:223`) and Sarah (`:249`, `:261`). Andrés's block (from `:276`) has neither key, so it gains both as new entries. It also includes 5A–5C and 6A–6C, and Column B lines 3–10 for Priya and DeShawn, line 4's box being `Debto2.Quest2.2` (§9.6).
- **Andrés:** 122A-1 5A 4,200.00, 5B 830.00, both 5C widgets 3,370.00, line 10 0.00; Schedule I 8a 3,370.00 and 8h 0.00, with one statement row: "Debtor 1", "Business: Rideshare and delivery driving", 4,200.00, 830.00, 3,370.00.
- **Unchanged:** every persona's CMI, above- or below-median result, fee flag (`apps/eligibility/models.py:186`, from CMI) and packet.
- **No persona meets the take-home pay gap** (§8): every persona with wages has at least one deduction typed, and Andrés has no paycheck.
- **No persona has a business or rental loss**, so no floor row prints (§9.2).

**The seed** (`seed_demo_data.py`) writes every answer above, with interest typed $0 for every persona and spouse, and stops writing `monthly_rental_income`. It writes the list as `[]` for each person with no business or rental, and assistance as No where the table says No. **Call (spec author):** it also sets `income_period_end` to `income_window(fill_date())[1]`. The seed never calls `update_step` (it writes `current_step` directly, `seed_demo_data.py:825`, now 7, §7.2), so without the stamp every seeded persona would show the dashboard notice. Personas seeded before 3e2 have no "now different" answer, so the means test and every forms call refuse them. Re-create them with `seed_demo_data --reset`, and the "Seed order" gotcha says so.

**The E2E fixture** (`frontend/e2e/fixtures/personas.ts`):

- `PersonaIncome` gains `interest`, `business`, `assistance` and `now_different`, and the spouse's twins.
- Each persona gains `deductions`, a field of its own beside `income`, with the spouse's twin, since another step asks them.
- `fillIncomeInfo` (`e2e/pages/wizard.page.ts:114`) fills the income by `input[name=…]`. The new `fillTakeHomePay` fills the deductions the same way, after it (§7.2). `fillExpenses` (`:173`) fills the new names and answers line 3.
- **No journey types a month.** The journeys run on the real date (CLAUDE.md "Dated tables and the fill date"). A check of the window sentence reads the session's `income_window`. No journey asserts the dashboard notice: each presses Continue on the Income step, which stamps the window.
- **Call (spec author):** Andrés's journey adds his business through the list's UI. The other journeys press "I have no business or rental income." for each person.
- **Every journey** passes the Take-home pay step between Income and Expenses (§7.2). Andrés's leaves it blank and presses Continue, since he has no paycheck.
- `test_api_readback.py` sends the same answers before it presses Complete. Its `_step_bodies` sends one PATCH per wizard step (`test_api_readback.py:44-62`), so it gains the Take-home pay body as its own PATCH, between the Income and Expenses ones (§7.4).

**Tier 3** gains every changed box above, and Andrés's statement row. **Tier 2** asserts every new and re-ruled placement, and `ASSERTED_CASES` (`test_oracle_tier2.py`) moves on purpose to the number the plan counts.

## 12. Docs

**The `CLAUDE.md` gotchas** change wherever 3e2 changes behaviour (U:166, U:178):

- **"Income is stored by source":**
  - the ten sources (rental out, interest in);
  - the entries list and its floored nets (no lower than $0.00 per kind and person, C-12) in CMI;
  - the current figures and which forms read them;
  - deductions, asked on the Take-home pay step;
  - 8f's fields and that it stays out of CMI;
  - the legacy rental gap;
  - encryption, and the serializers' declared bounds;
  - Schedule I lines 10 and 12 now line 7 + line 9, and 8a re-ruled to the entries' floored nets.
- **"Means test units":** `calculation_details` gains each person's floored business and rental nets, and CMI adds them.
- **"Blank, not 0.00":** rewritten from §9.6. It also drops "(interest, payroll deductions, priority)" as never-asked, since only priority still is. It names the 8f exception, says Column B lines 5 and 7 now print, and says 26 expense amounts, not 13, are stored as $0 when left empty.
- **"Expense names are the backend's":** 26 amounts, three texts and line 3. The amounts are encrypted and come back as strings.
- **"Forms need a completed intake":** Complete's new gaps, and the new `income_step_gaps` entries.
- **"Autosave sends only real edits"** and **"Nested debts and assets save by id":** the new step bodies, the entries' `_key` and id pairing, and the current figures sent only while "yes".
- **"Schemas are checked at startup":** the statement group and the `income.` namespace.
- **"`field_values`, not `form_data`":** the 8a sheet part.
- **"Seed order":** re-create the personas.
- **"GenerateAll vs single":** the packet reply's `income_period`.
- **The file map:** the new fields on `IncomeInfo`, `SpouseIncome` and `ExpenseInfo`, and `cmi.py`'s window function. `IntakeWizard.tsx`'s entry says nine steps, not eight, and its key list gains `take_home_pay` (CLAUDE.md:126).
- **The wizard's step numbers** (§7.2), wherever a gotcha names one:
  - "Nested debts and assets save by id": "Continue from steps 6 and 7" becomes 7 and 8 (CLAUDE.md:26);
  - "Forms need a completed intake": `update_step` takes "a whole number from 1 to 9" (CLAUDE.md:33), and Complete's gaps gain the `take_home_pay` step;
  - "Document upload sits mid-wizard": "`/intake` steps 2–8" becomes 2–9 (CLAUDE.md:62);
  - "Autosave sends only real edits": "Steps 6 and 7 have no body there" becomes 7 and 8, Step 2's body gains §7.4's new keys, and Step 3's body, Take-home pay, follows it (CLAUDE.md:69).
- **Left alone:** "until step 5 drops them" (CLAUDE.md:30) and "step 2's ADD rows" (CLAUDE.md:40) name steps of the forms project, not of the wizard.

**The persona briefs** apply 3e2's slice (PS:5): each brief gains its Income-step rows (8f, business, interest, "now different"), its Take-home pay rows (the deductions) and the new Schedule J lines. The fee-waiver page rows ("Take-home pay", "Non-cash help") stay until 3f, since the page still asks them. Andrés's brief drops "the interim home for his net" (PS:1374).

**The persona targets** (`2026-10-16-forms-step3-personas.md`) drop the two "OWNER TO APPROVE" marks the owner settled (PS:354, :370; owner answer 3).

**`README.md`**, the public file, states the old wizard twice: "Data collection (8-step wizard)" (`README.md:128`) and "8-step intake wizard: Your Information → Income → Expenses → …" (`:166`). Both say nine steps, and the second reads "Income → Take-home pay → Expenses".

## 13. Testing

**Tests name outcomes:**

- a gig driver's receipts and costs reach 122A-1 line 5 and the 8a statement, and his CMI is the net;
- a person whose business or rental net is below $0 is never refused for it: 122A-1 5C or 6C prints 0.00, and the loss never lowers CMI, `total_monthly_income` or `calculation_details`;
- a loss on one entry nets against a profit on another entry of the same kind and person, and the floor applies only to their sum;
- a business loss never lowers rental income, and one person's loss never lowers the other's income;
- a person whose averages show a profit but whose current figures (under "now different" Yes) show a loss gets 0.00 on Schedule I 8a for that kind, while 122A-1 keeps the averages' net;
- on the 8a statement, a losing entry's row prints below $0, a floor row with blank gross and expenses cells follows its kind, each person's 8a is the sum over kinds of the larger of $0.00 and that kind's rows' nets, and each person's net cells, floor rows included, add to that person's 8a (§9.2);
- the step's averages sentence shows only while a kind's summed average net is below $0, and under "now different" Yes the current-figures sentence shows only while that kind's summed current net is below $0, each naming only the forms its figures reach (§4.2);
- a gig driver with a business entry and personal debts stays in the app;
- no new question starts answered: "now different" and assistance for each person, the list (null until the button or an entry), and J line 3;
- take-home pay is gross less the deductions, on Schedule I, 106Sum and Schedule J;
- a blank deduction prints 0.00 on Schedule I and counts as zero;
- a person with pay who left every deduction blank is stopped at Complete with a link to the Take-home pay step, and a person with no pay is not. The test pins the gap's step, `take_home_pay`: Complete's gap keys are literals in `views.py` (`:262-278`), which `test_rule_fixes.py` never reads, and Review shows "Go to" only for a key `WIZARD_STEPS` has (`ReviewStep.tsx:92`); the means test and its preview never refuse for it;
- a session saved at any step before 3e2 reopens on the same step after the migration, and the migration's reverse keeps every step but Take-home pay (§7.2);
- `update_step` takes 9 and refuses 10;
- the Income step's save never changes a deduction, and the Take-home pay step's save never changes an income figure;
- a spouse's column stays blank for a filer living apart from their spouse;
- income that is now different prints on Schedule I, while 122A-1 keeps the average;
- the window names the six full months before the fill date: in October, on the 1st and on the 31st; in January; in March after February; across a year end (a March 2027 fill date gives September 1, 2026 through February 28, 2027); and in a leap year (a March 2028 fill date ends on February 29, 2028);
- the dashboard says when the window has moved, and Continue on the Income step clears it;
- a rental figure saved as one amount refuses until the filer lists the property;
- 8f's value never changes CMI;
- an unknown non-cash 8f value prints blank, with its kind, and a cash kind with no amount is refused;
- a person who typed a kind under assistance Yes and then answered No gets 0.00 on 8f and a blank Specify;
- Schedule J line 3 is never answered for the filer;
- the new Schedule J lines reach 22a and 23c;
- no persona's means-test verdict, fee flag or packet changes. The expense calculator's `disposable_income` reads only the four allowances (`expense_deduction_calculator.py:44-57`), so the new amounts change only `actual_total_expenses`, which no verdict reads;
- every migrated or new column is stored as ciphertext;
- each migration runs forward and back with a row present, keeping every value, on sqlite and on Postgres (§3.2);
- showing any of the three steps again (Income, Take-home pay, Expenses) sends nothing.

**Also:**

- **The shared test builder** `answer_household` (`apps/intake/tests/builders.py`) gains 3e2 defaults: "now different" No, the list `[]`, assistance No, and 5a (`payroll_tax`) typed as $0, so a fixture with wages meets no take-home pay gap. They go on the filer's row, and on the spouse's row the builder writes when `spouse_income` is given (`builders.py:36-41`). With `married_together` and no `spouse_income` there is no spouse row, and the spouse's income gap fires, as today. Every fixture that runs the means test, Complete or a forms path uses it. A fixture that presses Complete also answers J line 3, and the plan finds those fixtures by grep.
- **Every test that builds `IncomeInfo` with `monthly_rental_income`** changes with §4.1: `test_means_test_calculator.py:743`, `test_income_resume.py:28`, `test_derivations.py:138`, `:153`, `:162` and `:172`, `IncomeInfoStep.test.tsx:22`, and `IntakeWizard.test.tsx:454`, `:1575` and `:1591`.
- **The session lock test** (`test_session_lock.py`) needs no new endpoint, since everything saves through the session PATCH. Its `WRITES` gains an "income PATCH" entry whose body carries `income_info.business_and_rental`, which now saves through `_save_income`, as 3e1 added "household PATCH" (§6).
- **The gates** are the usual ones:
  - backend pytest with coverage of at least 90%, and ruff 0.8.5;
  - the Postgres tests in CI;
  - vitest, `tsc`, eslint and prettier;
  - the eight E2E journeys.

## 14. Not in 3e2

**For 3f:**

- 103B line 3 reads 8f's non-cash answer and kind, and the fee-waiver page stops asking it (U:399).
- The § 820.20 figure, Schedule I line 12 less the non-cash value (U:384), which §4.6 keeps apart for it.
- Whether 103B line 2 pre-fills from Schedule I line 7 (U:403), and the spouse's take-home on line 2's `undefined_3`, which Schedule I's column 2 line 7 now holds (E1 §14).
- Two screens named for take-home pay: the wizard's "Take-home pay" step (owner answer 2) asks what comes out of the pay, and shows line 7, while the fee-waiver page asks the filer to type take-home pay itself for 103B line 2 (CLAUDE.md "The fee-waiver application"). 3f revisits both labels with line 2's pre-fill.

**For 3h:**

- 122A-2 lines 16–19 from 5a–5h and the Schedule J amounts (U:361). 3h decides how 5e's one "Insurance" amount serves line 18 (term life only), and whether line 19 adds 5f to J 18.
- The one calculator on dated IRS tables, replacing `irs_standards.py`'s hard-coded 2024 figures and `ExpenseDeductionCalculator` (U:520-522). 3e2 adds amounts to the one expense model, `ExpenseInfo`, and binds nothing on 122A-2, so nothing pre-empts 3h's mapping.

**For step 4:** Schedule I lines 1 (its unbound boxes), 11 and 13; Schedule J 6a–6c, 15a, 15b and line 24 (§9.4); Form 101 line 12; Form 107 line 4.

**For 3c:** J line 4's mortgage, line 5, and 17a–17d with `Other 17c` and `Other 17d`, from the links. As the owner decided (owner answer 5), 3c also derives 20a from the debts linked to a property other than the home and retires 3e2's typed column, with its seed and migration change (§5.1).

**Unchanged:**

- the business-debt off-ramp (U:349). A business entry doesn't touch it: debts keep their own `consumer_business_classification` (`models.py:605-613`), and no income entry writes one;
- the employer name from a pay stub, the only upload figure (DIG-176);
- `IncomeInfo.monthly_income`, kept one release, now encrypted.

## 15. Defects found while scoping

These are proposed tickets. Plane is searched for duplicates first, and nothing is filed without the owner's yes.

- **Misnumbered rule names on 122A-1.** `line5a_pension_retirement` prints line 9, `line6a_unemployment` line 8, `line6b_child_support_alimony` line 4 and `line7_other_income` line 10 (`derivations.py:321-345`). Renaming them would orphan their tier 2 keys, so 3e2 leaves them and names its own rules for the lines they print.
- **`schedule_i_net_wages_debtor1`** prints Schedule I line 2, gross wages (`derivations.py:477-478`). Its name says "net".
- **Schedule J line 24 belongs to step 4** (§9.4), next to `[Q6.lines11_13]`. The umbrella's step 4 list (U:51-60) and Appendix A (U:721) don't record it. A ticket, or an umbrella erratum, records it where step 4 reads its scope.
- **`FeeWaiverApplication.qualifies_for_waiver`** compares `monthly_income`, which nothing writes since step 2, so a new row would raise a `TypeError` (`models.py:780-797`). Only tests call it. For 3f.
- **The seed's `current_step`.** The seed writes 6 for a completed session (`seed_demo_data.py:820-826`), which opens Contracts & Leases, not Review. The page object's own section comment still reads "Step 6: Review" (`e2e/pages/wizard.page.ts:231`), which suggests the value predates the Contracts and Codebtors steps. 3e2 keeps its meaning (7, §7.2) rather than fix it on the way.
- **The Income step's "Why we ask about income" note** opens "Income information helps determine which bankruptcy chapter you may qualify for." (`IncomeInfoStep.tsx:339`), close to the "you qualify" wording U §4.1 forbids (U:79). 3e2 cites only the note's "$0 in any box" rule (`:340-341`) and copies nothing from the sentence. A UPL review takes it.
- **The counsel list gains three items** (§18). The umbrella's counsel list ends at C-10 (U:635-646) and counts "ten counsel items" (U:625). An umbrella erratum adds C-11 to C-13, as for line 24 above.

## 16. What changed from the umbrella

1. **Blank deductions print 0.00.** §5.6 says "A blank stays blank and counts as zero in line 6" (U:360). Q27 says an asked line left blank prints $0.00 on Schedule I (U:371, U:135), and the approved persona targets print 0.00 for blank 5b–5h (PS:238, :497, :1055). So a blank deduction is stored as null, never as $0, counts as zero, and prints 0.00 (§4.5).
2. **8f's unknown non-cash value prints blank,** a narrow exception to Q27. Schedule I asks for the value "if known", which makes it a legitimate blank (U:126). See §9.1.
3. **8f stays out of CMI until counsel rules.** The umbrella is silent, and the targets left it open (PS:246). Counsel item C-11 (§18): whether regular government assistance, cash or non-cash, counts in CMI (122A-1 line 10), and how the step says so (§4.6).
4. **A loss on line 5 or 6 is floored at $0.00.** This departs from U §4.1's default (U:80), which leaves a legal characterization blank until counsel rules. The owner chose the floor (owner answer 1). On 122A-1 and in CMI, DigniFi applies the U.S. Trustee Program's means-test reading, that the net "cannot be a negative number", pending counsel. On Schedule I 8a, which is not a means-test line, the floor is the owner's extension of that reading. It is marked draft for counsel as item C-12, asked for each form apart (§18), and the step's information sentences and the statement's floor row carry `DRAFT: counsel C-12` (§4.2, §9.2). The floor applies per kind and per person to the summed net, on the averages and the current figures alike.
5. **The double-count note** goes to counsel as item C-13, with line 3's information sentence, without the umbrella's examples (U:351) until counsel adds them (§4.2, §18).
6. **Rental income leaves the ten sources and interest joins.** The old net becomes a named gap until the filer lists the property (§4.1, §8). §5.6 says only "split into gross and costs".
7. **Businesses and properties are a list,** one entry each, because 8a asks for a statement "for each property and business" (§4.2).
8. **The 8a statement needs a narrow engine change** (§9.2). The umbrella assumed 3a2's generator could print it as it stands (U:266, U:349), but a sheet today only continues a repeat group's slots.
9. **"Now different" is asked per person, and Yes asks the full set of current figures,** entries and interest included. 8f and the deductions are asked once, as current. §5.6 says only "the current figures, which feed Schedule I" (§4.4).
10. **Encryption reaches `IncomeInfo.monthly_income`**, under U §4.2's rule for the tables a PR migrates (U:85), beyond Appendix A's "the ten amounts" (§3.1).
11. **Schedule J 22b stays blank and line 24 goes to step 4.** §5.6 names neither (§9.4). §15 proposes a ticket or umbrella erratum recording line 24 for step 4.
12. **The persona targets' J line 5 answers are dropped** `[CORR.J45]` (§11).
13. **New Complete gaps** for the questions 3e2 adds (§8), under U §4.4's framework. That includes the take-home pay gap, for a person with pay who left all eight deductions blank, which departs from U:360's "A blank stays blank and counts as zero" and from U §4.5's "a line DigniFi asked and the filer left blank prints $0.00" (U:135) for the all-blank case (§4.5).
14. **The existing 13 expense lines are relabelled** in Schedule J's words (§5.1).
15. **The Income step shows the dashboard's window notice** at its top when the stamp is older than the window (§7.1). U:368 names only the dashboard.
16. **"Start from my average figures"** (§4.4), a button §5.6 doesn't name.
17. **The cap of 10 entries per person** (§4.2).
18. **Three new columns stay plaintext**, readings of U §4.2's "New filer data is encrypted from the start" (U:84): `income_period_end` (§4.4), `ExpenseInfo.data_source` (§3.1) and `next_entry_id` (§4.2). None holds the filer's money or answers.
19. **The new Income step gaps null the household counts** (`household.family_size` and the fee-waiver page's household-size pre-fill) while they are open (§8). That changes 3e1's behaviour for answers no count reads. The take-home pay and line 3 gaps don't, since they stay out of `income_step_gaps`.
20. **The means test refuses on gaps no CMI line reads** ("now different" and assistance), as a 400 from `calculate_means_test` and in the wizard's preview (§7.1, §8). U §4.4 splits refusals between Complete and one form's `requires()` (U:113-125). This spec keeps one list for every refusal instead.
21. **Line 20a is asked as a typed amount in 3e2, though Q13 makes it 3c's** (§5.1, owner answer 5). 3c derives it from the linked debts and retires the typed column (§14).
22. **The payroll deductions get a wizard step of their own,** "Take-home pay", between Income and Expenses (owner answer 2, §7.2). U:357 names no step for them, and the wizard had eight. Every step from Expenses on moves up one, so `update_step` takes 1 to 9 and a data migration moves the stored steps (§6, §7.2).
23. **Three counsel items join C-10** (owner answer 4, §18). They block production, not merges, as U:633 says of every counsel item.
24. **The 8a statement gains a floor row in DigniFi's words** for a kind whose summed net is below $0 (§9.2). Schedule I asks for a statement "for each property and business"; the row is an addition beside them, the one row that is not an entry. It carries `DRAFT: counsel C-12` (§18).

## 17. Calls this spec makes

The owner can overturn any of these.

1. One table per person keeps every new income answer (§4).
2. Rental leaves the ten, interest joins, and the legacy figure becomes a gap that clears when the list is answered (§4.1, §6, §8).
3. Businesses and properties as a list of at most 10 per person, null versus `[]`, with server ids (§4.2).
4. An information note on the double count, worded so it never says what a business cost is (§4.2).
5. Interest asked in 122A-1's words (§4.3).
6. The window is worked out on the server, with a plaintext stamp of the window the filer last confirmed, set only by Continue on the Income step (§4.4).
7. "Now different" per person; Yes asks every Schedule I income line's figures; no pre-fill, but a "Start from my average figures" button (§4.4).
8. 8f as flat fields per person, cash and non-cash apart, encrypted, and kept out of CMI (§4.6).
9. `data_source` stays plaintext (§3.1).
10. The existing 13 expense lines relabelled in Schedule J's words (§5.1).
11. Line 3's information sentence, built from the umbrella's example (§5.2).
12. One Income step with eight sections, the deductions moved to the Take-home pay step (§7.1).
13. "Now different", the list and the assistance gaps join `income_step_gaps`; line 3 and the take-home pay gaps are Complete's alone; what each gap tests (§8).
14. 8f with only a non-cash kind and no value prints blank (§9.1).
15. The statement as a slotless sheet group with the `income.statement[]` binding, numbered `"{n}"`, its `description` cell prefixed with the kind, and its fix from a binding-string function (§9.2).
16. Schedule J 22b stays blank and line 24 goes to step 4 (§9.4).
17. Each table's re-encryption in three migrations, and a reverse that raises on a value it can't decrypt (§3.2).
18. The legacy rental column read-only on both serializers (§4.1).
19. `next_entry_id` plaintext (§4.2).
20. The window's dates written whole, with the year; `income_window`; the stamp set whenever `current_step` is 3, and skipped with no income row (§4.4).
21. The current figures named `current_<source name>` (§4.4).
22. Client limits, and the Review step's new rows and Take-home pay section (§7.1).
23. The plan drafts the sentences this spec only names (§7.5).
24. The seed stamps the window; Andrés's journey adds his entry through the UI (§11).
25. Entries of one kind net against each other, and the floor applies to their sum (§4.2).
26. The floor's information sentences on the Income step, one on the averages and one on the current figures, each naming DigniFi as the one that counts the net as $0.00 and naming only the forms its figures reach (§4.2).
27. The statement's rows show each entry's own subtraction, and a floor row follows a kind whose summed net is below $0, with blank gross and expenses cells and the amount that brings the kind up to $0.00, so the net column adds to 8a (§9.2).
28. The take-home pay gap: a person with Schedule I line 4 above $0 and all eight deductions blank (§4.5, §8).
29. The Take-home pay step shows lines 4, 6 and 7 from step state, never sent (§7.2).
30. `renderStepContent` switches on the step's key (§7.2).
31. A data migration adds 1 to every stored `current_step` from 3 to 8; its reverse subtracts 1 from every value from 4 to 9 and leaves 3 as 3; values outside those ranges stay (§7.2).
32. The seed writes `current_step=7`, the step its 6 opened before (§7.2).
33. A rule that reads both Income and Take-home pay links to the earlier, `income_info`, as Schedule J 23c does: line 7, and lines 10 and 12 (§9).

## 18. For counsel

Owner answer 4 adds three items beside C-10 (U:646). Like every counsel item, they block production, not merges, and their wording ships marked as draft until counsel signs off (U:633). They extend the umbrella's counsel list (U §9), which ends at C-10, so the numbers below are that list's. The step 2b plan's "Ruling C-11" and "Ruling C-12" (`docs/superpowers/plans/2026-10-14-forms-step2b-part2.md:8412-8413`) are rulings made while that plan was built, not counsel items. §15 records the umbrella erratum.

| Item | Asked in           | PR  | What counsel decides                                                                                                                                                                                                                                                                                                                                                                                                               |
| ---- | ------------------ | --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C-11 | `[Q6]`             | 3e2 | Whether regular government assistance, cash or non-cash, counts in CMI (122A-1 line 10), and the 8f note's words (§4.6)                                                                                                                                                                                                                                                                                                            |
| C-12 | `[Q5]`             | 3e2 | How a business or rental loss counts, for each form apart. DigniFi floors each kind's summed net at $0.00 pending counsel (§4.2): on 122A-1 (5C, 6C) and in CMI, following the U.S. Trustee Program's means-test guidance; and on Schedule I 8a and its statement, a sworn schedule of actual income, as the owner's extension of that guidance. Also the floor's information sentences and the statement's floor row (§4.2, §9.2) |
| C-13 | `[Q5]` `[CORR.J3]` | 3e2 | The wording of the double-count note, and whether it may give examples such as the umbrella's "a car, gas or insurance" (U:351); and line 3's information sentence (§4.2, §5.2)                                                                                                                                                                                                                                                    |

C-10 itself, the six-month-average and "income now different" wording, stays as the umbrella lists it (§4.4, §7.5, §10).

## Owner answers (2026-11-02)

1. **A business or rental loss:** floor at $0.00, and it still goes to counsel. Implemented in §4.2, §4.7, §7.1 (the floor's sentences, the totals line, Review), §7.5 (the C-12 draft mark), §9.1 (8a), §9.2 (the statement's floor row), §9.3 (5C, 6C), §11 (no persona has a loss), §13, §12, §16 items 4 and 24, §17 items 25–27 and §18 (C-12).
2. **The payroll deductions:** a new wizard step, "Take-home pay", not a section of the Income step. Implemented in §1 item 3, §4.4 (the stamp), §4.5, §6, §7.1, §7.2, §7.4, §8 (the take-home pay gap), §9 (`RULE_FIXES`), §11, §12, §13, §14 (the label beside 103B's), §15 (the seed's `current_step`), §16 items 13, 19 and 22 and §17 items 28–33.
3. **The persona answers:** approved as written, J line 3 Yes for Priya, No for Sarah, No for Andrés and Yes for DeShawn; the spouses' "now different" No for Priya and DeShawn; James's 5a/5g split and J lines 4b, 10 and 13. Stated as settled in §2 and §11.
4. **The counsel list:** all three items added beside C-10, blocking production, not merges. Listed in §18, and the umbrella erratum in §15. C-11 also covers the 8f note's words, as the question's recommendation proposed (the answer names only whether assistance counts in CMI).
5. **Schedule J line 20a:** asked as a typed amount in 3e2; 3c derives it from the linked debts and retires the typed column. Stated in §5.1, §14 and §16 item 21.
