# Forms step 3a1: data foundations

- **Status:** draft for the owner's review, 2026-10-16.
- **Drawn from:** the step 3 umbrella spec, `docs/superpowers/specs/2026-10-16-forms-step3-design.md` §5.3, and the persona targets, `docs/superpowers/specs/2026-10-16-forms-step3-personas.md`.
- **Branch:** `feat/forms-step3a1`, from develop `fae6e6c`. The PR targets develop.
- **Tags** such as `[Q11]` trace each part to the umbrella's map of answers and tickets.

The umbrella settles 3a1's scope and its rules. This spec turns them into a design for the code as it stands, and records the two calls the umbrella left to it.

## 1. What 3a1 does

1. **The median fix comes first** `[Q11]` `[DIG-274]`: the U.S. Trustee's April 2026 table, looked up by the date the forms are filled.
2. **Dated tables** `[Q10]` `[CORR.valid_through]`: one model and one lookup for every public table step 3 reads. 3a1 loads only the median.
3. **Refusals** `[Q12]`: Complete refuses what every packet needs, and every refusal names the step or page that fixes it (DIG-181).
4. **Stable row ids** `[DIG-273]`: a new asset or debt keeps one id across every save.
5. **Unconfirmed scanned debts never print** `[DIG-163]`.
6. **One save at a time** `[DIG-188]`: saves on one session take a lock.
7. **The sixth persona** `[Q28.data]`: Andrés Kettleby's seed, brief and E2E journey, on today's fields.
8. **Fictional creditor names** `[Q28.names]` for the five existing personas.
9. **A "Source code" link** in the site footer `[Q30]`.

The median fix is the first commit. Nothing in 3a1 deploys: production waits for steps 3 to 5 and DIG-146.

## 2. The owner's calls

The umbrella left two interim choices to this spec. The owner answered both on 2026-10-16.

- **3a1.Q1, where Andrés's driving income goes until 3e2: other income.**
  - His net business income, $3,370 a month, is `monthly_other_income` in both the seed and the journey. No income source is business income yet, and the wages box is ruled out.
  - It prints as "Other income" on Schedule I line 8h and 122A-1 line 10. His income figure (CMI), his below-median result and his fee routing are final from 3a1. 3e2 moves the amount to the business lines.
  - The E2E page object types each persona's income into its own box. The other five keep wages.
- **3a1.Q2, his fee answer until 3f: no application.**
  - He means to pay in installments, but today's 60%-of-median flag says he qualifies for a waiver, so Complete sends him to `/fee-waiver`.
  - The seed files no fee-waiver application for a persona without fee-waiver data. This also removes today's `KeyError` (`seed_demo_data.py:611`) for James or Priya, should either ever qualify.
  - His journey checks that he lands on `/fee-waiver`, goes on to `/sofa` and `/forms` by URL, and expects 14 forms, without 103B.
  - Until 3f, `test_api_readback.py` keeps "qualifies under today's flag" apart from "applied".

## 3. Dated tables and the median `[Q11]` `[DIG-274]` `[Q10]` `[CORR.valid_through]`

### 3.1 The problem

- **One stale row.** The fixture holds one median row, effective 2025-11-01 (`ilnd_2025_data.json:21`). It is the U.S. Trustee table for cases filed from 11/1/2025 to 3/31/2026.
- **A lookup that ignores dates.** The lookup is `self.district.median_incomes.latest("effective_date")` (`apps/eligibility/models.py:126`), so it never looks at a date. Its bare `except` turns any failure into "No median income data".
- **Two status codes for the same failure.** Missing median data is a 400 from `calculate_means_test` and a 500 from every forms view.

### 3.2 The model

- **`DatedTable`.** An abstract model in `apps/districts/` holds three fields:
  - `effective_date`;
  - `valid_through`, which is nullable;
  - `source_url`.
- **What `valid_through` means.** A scheduled table carries the last day before its next scheduled change. An empty one means open-ended, and only the irregular tables in later PRs use that.
- **`MedianIncome`** (`apps/districts/models.py:58`) inherits `DatedTable`, so it gains `valid_through` and `source_url`.
- **The migration** fills `valid_through` on existing rows from the Census schedule: the day before the next April 1 or November 1 after the row's effective date.
  - Without this, production's 2025 row would come out open-ended and stay in force forever.
  - With it, that row ends on 2026-03-31, and production refuses until the operator loads the newer table.
- **The extra-person amount.** `family_size_additional` loses its default of $9,900, so the amount always comes from the table. The U.S. Trustee's figure is $11,100.

### 3.3 The fill date

- **What it is.** The day the forms are filled stands in for the filing date (umbrella §4.3).
- **One function.** `fill_date()` returns `timezone.localdate()`. `TIME_ZONE` is America/Chicago (`config/settings/base.py:140`), the pilot district's zone.
- **Every reader.** Every lookup of a dated table takes the fill date, and nothing else reads the clock for this.
- **Pinned in tests.** An autouse fixture in `backend/conftest.py` pins it to 2026-10-16, so CI behaves the same every month. Tests of the lookup itself set their own dates. No date library is added.

### 3.4 The lookup and the refusal

- **The lookup.** `in_force(rows, on)` returns the newest row whose effective date is on or before `on`, and whose `valid_through` is empty or on or after `on`. It replaces `latest()` and the bare `except`.
- **No table in force.** The lookup raises `NoTableInForce`, a `ValueError`. It never falls back to an older table. The refusal reads:

  > DigniFi doesn't have the income figures for today's date yet, so it can't prepare your forms. Please try again later.

- **The calculator.** `MeansTestCalculator` prefixes any other `ValueError` with "Means test calculation failed:". It lets `NoTableInForce` through unchanged, as it already does `IncomeNotSplit`.
- **Status codes.** The forms views return it as a 422, alongside their other plain-words refusals. Today the same failure is a 500, and `test_missing_median_income_is_a_500_logged_by_type_only` changes with it. `calculate_means_test` keeps its 400 and shows the same sentence.
- **The log.** Each refusal is logged at error level with the table's name, the date and the district code, never the filer's data. Logs reach Sentry, so a missed update alerts the operator.
- **What the means test records.** `MeansTest.calculate` stores the table it used (effective date, `valid_through`, source URL) in `calculation_details`. `get_detailed_breakdown` reads that table's effective date. Today it labels the calculation's own timestamp as the median's effective date (`means_test_calculator.py:215`).

### 3.5 The tables 3a1 loads

`ilnd_2025_data.json` keeps its name, since CI, the root `CLAUDE.md` and seven test files load it by name. Each median row lists its own figures and dates.

| Row        | Effective  | `valid_through` | Illinois, 1–4 people                    | 5–8 people                                | Each extra person | Source                                                                            |
| ---------- | ---------- | --------------- | --------------------------------------- | ----------------------------------------- | ----------------- | --------------------------------------------------------------------------------- |
| 1 (exists) | 2025-11-01 | 2026-03-31      | $71,304 / $91,526 / $110,712 / $134,366 | $145,466 / $156,566 / $167,666 / $178,766 | $11,100           | `https://www.justice.gov/ust/eo/bapcpa/20251101/bci_data/median_income_table.htm` |
| 2 (new)    | 2026-04-01 | 2026-10-31      | $73,180 / $93,934 / $113,625 / $137,902 | $149,002 / $160,102 / $171,202 / $182,302 | $11,100           | `https://www.justice.gov/ust/eo/bapcpa/20260401/bci_data/median_income_table.htm` |

- **Checked 2026-10-16.** Both pages show these Illinois figures and "Add $11,100 for each individual in excess of 4". Sizes 5 to 8 follow that rule from the 4-person figure, as the 2025 row already does.
- **The July 2026 period** (`/20260715/`) changed only the IRS data. Its Illinois median row matches the April table.
- **The November 2026 table.** It was not posted on 2026-10-16; last year's appeared on 10/16/2025. The page is checked again before the median commit and before merge. If the table is out, it joins as row 3 with its own `valid_through` of 2027-03-31.
- **A guard test.** It fails if any median row in the fixture has no `valid_through`.

### 3.6 The notice

- **Where it shows.** Here "the packet" means the packet endpoint and the dashboard. A printed notice sheet would need 3a2's drawing engine.
- **The endpoint.** `GET /api/forms/packet/` adds `tables`, the dated tables the means test used. Each has a name, effective date, `valid_through` and source URL.
- **The dashboard** shows it above the form list:

  > These forms use the median income figures the U.S. Trustee applies to cases filed on or after April 1, 2026. New figures are expected after October 31, 2026. If you file after that date, download your forms again.

- **The rules it follows.** This is information, not advice (UPL). An unfiled form re-fills on every download, so downloading again picks up the newer table. A form marked filed keeps its stored answers, as today.

### 3.7 The runbook

`docs/REFERENCE_TABLES.md` is a new document, named in the style of `UPL_COMPLIANCE.md`. For each dated table it says:

- where the table is posted;
- when it changes;
- how to add a row: edit the fixture with its `valid_through` and source URL, open a PR, and run `loaddata ilnd_2025_data` after the deploy;
- what the refusal looks like when a change is missed.

The owner is the named operator. 3a1 writes the median entry, and each later PR adds the tables it loads.

### 3.8 What changes for the personas and the tests

- **The five personas' results don't change** under the new table. Each annual income is the monthly figure × 12, and the waiver line is 60% of the median:

  | Persona | Household | Annual income | Median   | Waiver line | Result                 |
  | ------- | --------- | ------------- | -------- | ----------- | ---------------------- |
  | Maria   | 3         | $38,400       | $113,625 | $68,175.00  | below; qualifies       |
  | James   | 1         | $69,996       | $73,180  | $43,908.00  | below; doesn't qualify |
  | Priya   | 4         | $144,000      | $137,902 | —           | above                  |
  | DeShawn | 2         | $42,000       | $93,934  | $56,360.40  | below; qualifies       |
  | Sarah   | 1         | $24,000       | $73,180  | $43,908.00  | below; qualifies       |
  | Andrés  | 2         | $40,440       | $93,934  | $56,360.40  | below; qualifies       |

- **The printed figures do change.** 122A-1 line 13 prints the new median, so `test_oracle_tier3.py`'s line 13C cases move to the new figures, as does any test that reads the fixture through the lookup.
  - **Tests that keep their figures:**
    - six test files build their own median rows; those rows have no `valid_through`, so they stay in force on the pinned date;
    - `test_registry.py` and `test_form_views.py:713` store a threshold directly.
  - **Two refusal tests change:**
    - `test_form_views.py:841-873`, which expects a 500 logged by type only, now expects the 422 and the logged refusal;
    - `test_cmi.py:118-125`, which expects the calculator's "Means test calculation failed:" prefix, now expects the plain sentence.
- **Stale comments** get the new figures:

  - `seed_demo_data.py:169,273`;
  - `e2e/fixtures/personas.ts:249,382`;
  - `james-borderline.spec.ts:4,36`, `deshawn-assets.spec.ts:78` and `priya-ineligible.spec.ts:4`.

  The frontend unit-test mocks that carry $71,304 are left alone: they mock the API and never read the fixture.

- **Risk: CI goes red on November 1.** E2E and `seed_demo_data` use the real date. From 2026-11-01, unless the November table is loaded, every forms call, the means test and the seed refuse, and the E2E job in CI goes red. That is the refusal working as designed.

## 4. Refusals `[Q12]` `[DIG-181]`

### 4.1 The problem

- **Complete checks too little.** It checks only that three rows exist: debtor, income and expenses (`apps/intake/views.py:193-200`).
- **The reasons are lost.** It returns `{errors, message}` with a 400, but `handleAPIError` keeps only `message` (`frontend/src/api/client.ts:107-121`). The filer reads "Please complete all required sections before finalizing" without learning which section.
- **No refusal names its step** except `IncomeNotSplit`, and only in prose.

### 4.2 What Complete refuses in 3a1

Umbrella §4.4 lists what Complete refuses. 3a1 builds the framework and adds the requirements whose answers today's wizard already asks:

| Requirement                       | Step key       | Sentence                                                                |
| --------------------------------- | -------------- | ----------------------------------------------------------------------- |
| Name and address entered          | `debtor_info`  | Enter your name and address on the Your Information step.               |
| A 9-digit Social Security number  | `debtor_info`  | Enter your 9-digit Social Security number on the Your Information step. |
| Income entered by source          | `income_info`  | Enter your income by source on the Income step.                         |
| The Expenses step saved           | `expense_info` | Go through the Expenses step, even if you have no expenses to enter.    |
| No unconfirmed scanned debts (§6) | `debts`        | Check the debts read from your documents on the Amounts Owed step.      |

- **Not yet.** Marital status and the household list join in 3e1, since the wizard never asks marital status today. Creditor, contract and codebtor addresses join in 3c.
- **One source of truth.** The identity checks are the registry's own, `_needs_debtor_info` and `_needs_ssn` (`apps/forms/registry.py:63-71`). Their sentences change to name the step, and `PreconditionMissing` and `IncomeNotSplit` carry the step key. Complete and the forms views then say the same thing.
- **The registry's checks stay.** Form 101 and Form 121 keep these checks in their own `requires()`, which protects sessions completed before 3a1.
- **The response.** A refusal is a 400:

  ```json
  {
    "message": "Please complete all required sections before finalizing",
    "errors": [{ "step": "income_info", "message": "..." }]
  }
  ```

  Today's `errors` is a list of strings. `test_e2e_intake.py:455-456,492` and the mock at `IntakeWizard.test.tsx:184-190` change with it.

### 4.3 Forms refusals

- **The body.** It keeps its sentence, which names the step or page in words. Where a step or page fixes the refusal, the body also carries `step` (a wizard step key) or `page` (a route).
- **Which refusals carry one:**
  - `IntakeNotFinished` carries `page: "/intake"`.
  - `IncomeNotSplit` and the registry's checks carry their step.
  - "Already filed", "not in your packet" and `NoTableInForce` carry neither, because no step of the filer's fixes them.
- **Later PRs** add their own requirements to the right gate, with their step or page. In 3f, for example, 103B's answers point to `/fee-waiver`.

### 4.4 The wizard

- **The errors list survives.** `APIClientError` keeps it, and `IntakeContext.completeSession` passes it to the wizard.
- **The Review step lists each reason.** Each has a "Go to _step label_" button, which moves to that step the way Go Back does.
- **The dashboard** shows a forms refusal's sentence, as now. When the body carries a `page`, it adds a link.

## 5. Stable row ids `[DIG-273]`

### 5.1 The problem

- **The response is dropped.** `saveCurrentStepData` throws the session PATCH response away (`IntakeWizard.tsx:343`), so a new asset or debt never learns its id.
- **Each save replaces the row.** On every later save, `_save_rows_by_id` creates the row again and deletes the copy it stored last time. Step 3c links debts to assets, codebtors and notice parties by id, so the ids must hold.

Contracts and codebtors fixed this by replacing their state with the PUT response (DIG-147). That pattern can't be copied to assets and debts, for three reasons:

- **Two copies of the rows.** `AssetsStep` and `DebtsStep` copy their rows into local state once, at mount, and push changes up through an effect (`AssetsStep.tsx:34-36,83-87`, `DebtsStep.tsx:55-57,108-111`). Ids written into the wizard's copy would be overwritten by the step's next change. Ids written only into the step's copy are lost when Continue unmounts it.
- **Unreliable order.** The response lists rows in model order, which sorts on encrypted columns, so the order is effectively arbitrary (`models.py:397,547`). The sent list also drops blank rows, so positions don't line up with state.
- **A merge that saves.** The autosave baseline is the body that was sent (`useAutoSave.ts:68,73`). Merging ids into state would change the next body and send one more PATCH, which reopens a completed intake.

### 5.2 The design

- **One copy of the rows.** The Assets and Amounts Owed steps become controlled: the wizard holds their rows and the steps render them.
- **A browser-only key.** Each row in the wizard carries a key that never reaches the server. A loaded row uses its id; a new row gets a random key.
- **The response keeps the sent order.** A session PATCH that carries `assets` or `debts` returns that list in the order it was sent, each row with its id. The order of other reads is unchanged.
- **The merge.** After every save, autosave or Continue, the wizard pairs the row it sent at position _i_ with the returned row at position _i_. It writes the returned id into the wizard row with that key, wherever that row now sits.
  - The pairing covers every sent row, so a row sent with a stale or foreign id takes its new id.
  - A row deleted while the save was in flight is skipped.
  - Amounts are not taken from the response; the wizard keeps what the filer typed.
- **No extra save.** `useAutoSave`'s `onSave` may return the copy the server now holds, and the hook stores it as the baseline. The wizard builds that copy with the same merge function it uses on its rows, so the next body matches it exactly, including key order. A later edit still saves.
- **Unchanged:** contracts and codebtors keep their DIG-147 pattern, since it works on Continue-only saves.

## 6. Unconfirmed scanned debts never print `[DIG-163]`

- **Today.** An upload creates `DebtInfo` rows with `is_draft=True`, and any session PATCH carrying `debts` clears the flag. No forms reader filters drafts (`derivations.py:114-139,218-235,282-295,595,597`), and neither does the means test's priority-debt deduction (`expense_deduction_calculator.py:106-109`).
- **One accessor.** Confirmed debts come from one accessor, a manager or queryset method. Every derivation and the means test read through it, and 3b and 3c's row readers will use it too.
- **Complete refuses while a draft remains** (§4.2), and names the Amounts Owed step.
  - **Why:** an upload after Complete reopens the intake (`reopen()`). The filer can then press Complete on Review without passing step 5, whose Continue confirms drafts. Without the refusal, the scanned debt would silently drop out of the totals.
  - **The filter is the second guard.**
- **Not changed:** the dischargeability service and the completion percentage read debts but fill no form.

## 7. One save at a time `[DIG-188]`

- **Today.** Nothing takes a row lock (`select_for_update` appears nowhere). Two saves of the same new rows can each create them.
  - `update_step` isn't atomic.
  - `complete` does a full `session.save()` that can overwrite a concurrent `reopen()`.
- **The rule.** Every write to a session's intake data first locks the session row with `select_for_update()`, inside the same short transaction as the write. That covers:
  - session PATCH and PUT;
  - `update_step` (made atomic);
  - `complete` (made atomic, and writing only `status` and `completed_at`);
  - the contracts and codebtors PUT, POST and DELETE;
  - the `DebtViewSet` and `AssetViewSet` writes;
  - a scanned bill's correction;
  - the writes of a document's findings.
- **The upload path.** An upload's findings are written by `_run_processing` in an executor thread with its own connection, while the request thread waits on the executor (`documents/views.py:182-183`).
  - The lock is taken only inside the worker's short transaction that writes the draft debts and pay-stub figures. It is never held across the executor or the call to the hosted model.
  - Otherwise the request would deadlock on its own worker, and every autosave would wait out an OCR round-trip.
- **The proof.** `select_for_update` does nothing on sqlite, which the test settings use.
  - **Two Postgres tests:** two concurrent saves of the same new rows store each row once, and an upload's draft write waits for a save's lock and then finishes.
  - **In CI:** they run in the backend job against its existing Postgres service (`ci.yml:35-51`, unused today), through a Postgres test settings module.
  - **Under sqlite** they skip with a visible reason (`-rs`).

## 8. The sixth persona `[Q28.data]`

Andrés Kettleby joins with only the data today's wizard asks. The persona targets doc gives the source, in its "Andrés Kettleby" section: "2. Per PR", item 3a1. Each later PR adds its own slice.

- **The seed.** `_andres_kettleby` (`demo_andres`) is added to `PERSONAS`, with:
  - his identity, `household_size` 2 and `filing_type` individual;
  - every income source at $0 except `monthly_other_income` at $3,370 (3a1.Q1);
  - the 13 expenses, totalling $2,779;
  - four assets;
  - the Honda Fit loan (D 2.1) and nine nonpriority debts (E/F 4.1–4.9);
  - no fee-waiver application (3a1.Q2).
- **The E2E fixture.**
  - `PersonaIncome` replaces `total_monthly_income` with amounts by source.
  - `fillIncomeInfo` types each into its own box (`wizard.page.ts:117-124`), and the five personas carry their wages there.
  - `ANDRES` is `e2e_andres_${RUN_ID}`, SSN 900-66-6006.
- **The journey** `andres-gig-driver.spec.ts`:
  1. register, fill Your Information, skip the documents;
  2. enter income in the other-income box, then expenses, assets and debts;
  3. leave contracts and codebtors empty;
  4. press Complete, and check that the fee-waiver page opens;
  5. go to `/sofa` by URL (the silent refresh on mount restores the login, `AuthContext.tsx:52-63`) and skip it;
  6. Generate All, expecting 14 forms.
- **The readback test.** `WAIVER_FILERS` (`apps/forms/tests/test_api_readback.py:38`) splits into the filers who qualify under today's flag (Maria, DeShawn, Sarah, Andrés) and those who applied (Maria, DeShawn, Sarah). 3f joins them again.
- **Tier 3** gains his hand-worked cases for the boxes 3a1 prints, from the targets doc's outcome list:

  - **122A-1:** lines 10 to 14;
  - **Schedule I:** lines 8h, 10 and 12;
  - **Schedule J:** lines 17a and 22 to 23;
  - **106Sum:** lines 1 to 5.

  Each is worked out by hand before it is committed.

- **The brief** `docs/testing/persona-briefs/andres-kettleby.md` is the target brief cut to the 3a1 slice:
  - **Income:** the other-income box.
  - **Fee step:** he doesn't apply for the waiver and goes on to his forms.
  - **Left out:** anything the wizard doesn't ask yet (addresses, county, household list, business detail, the IRS debt, contracts, the codebtor).
- **The counts** move from five personas to six and from seven journeys to eight:

  - `README.md:27,218`;
  - `CLAUDE.md:12,90,100,129`;
  - `docs/testing/persona-briefs/README.md:5,16-22,46,53,97`;
  - `docs/testing/run-persona-tests.md:22,24,94,177`;
  - `docs/testing/test_persona_full_flow.py:4`;
  - `seed_demo_data.py:1,513,525`.

  Dated specs and plans are records and stay as written.

## 9. Fictional creditor names `[Q28.names]`

The five personas' private creditors take the fictional names in the targets doc's rename table. That covers:

- the seed (`seed_demo_data.py`), including the SOFA creditor-payment rows (`:148,153`) and Maria's employer ("CNA at Northwestern Hospital", `:137,142`, which becomes Larkfield General Hospital);
- the five briefs;
- `e2e/fixtures/personas.ts`;
- `sofa-journey.spec.ts:106`.

Government creditors keep their real names. Banks that hold a persona's own accounts are not creditors and keep theirs.

Not renamed, because none is persona data and none carries an address:

- the scanned-bill schema example (`documents/schemas/creditor_bill.py:65`);
- documents, eligibility and intake unit tests;
- frontend unit tests;
- the Amounts Owed placeholder;
- dated plans.

## 10. The source code link `[Q30]`

- **A site footer.** A footer after `</Routes>` (`App.tsx:85`) shows on every route. It holds a "Source code" link to `https://github.com/crichalchemist/DigniFi`, which is public (checked 2026-10-16). The AGPL expects a network service to offer its source this way (umbrella §10).
- **One footer landmark per page.** The landing page's disclaimer sits in its own `<footer>`, outside `<main>` (`LandingPage.tsx:143-152`). Its element changes so that page keeps one `contentinfo` landmark. The disclaimer's text and look stay as they are.

## 11. Docs

- **`CLAUDE.md` gotchas** change wherever 3a1 changes behaviour:
  - the nested-save gotcha, for the response order and the wizard's merge;
  - "Forms need a completed intake", for what Complete refuses and its new body;
  - "The packet decides" and "GenerateAll vs single", since missing median data is now a 422 refusal, not a 500;
  - "Seed order", for the fill date and November;
  - a new gotcha for the fill-date pin;
  - the upload gotchas, since drafts never print;
  - a new gotcha for the session lock, which is a no-op on sqlite and proved only by the Postgres tests;
  - the counts (§8).
- **`docs/REFERENCE_TABLES.md`** is new (§3.7).
- **The README** gets its counts (§8).

## 12. Testing

- **Tests name outcomes:**
  - a filer whose income falls between the two tables gets the right result on each side of April 1;
  - a fill date past every table's `valid_through` refuses;
  - a new debt keeps one id across autosave, edit and autosave;
  - Continue, Go Back and edit keep one id;
  - an id merge sends no PATCH, so a completed intake stays completed;
  - Complete names each missing step;
  - an unconfirmed scan prints nowhere;
  - two concurrent saves store a new row once.
- **The gates** are the usual ones:
  - backend pytest with coverage of at least 90%, and ruff 0.8.5;
  - vitest, `tsc`, eslint and prettier;
  - the eight E2E journeys;
  - the Postgres lock tests in CI.

## 13. Not in 3a1

- Marital status and the household list (3e1).
- Business income and its lines (3e2).
- The fee answer and the HHS table (3f).
- Addresses (3c).
- The exemption, IRS, § 104 and multiplier tables (3g, 3h).
- **The order of ordinary reads.** Rows still sort on ciphertext there (filed below for 3b).
- **Other `expected` fields in the persona fixture.** Andrés's journey uses only his own, and the five journeys don't read theirs.
- **The thin Priya journey** (filed below).

## 14. Defects found while scoping

Each was checked against the code. Each is to be ticketed in Plane, or added as a comment on its ticket, with the owner's yes.

- **Arbitrary row order.** `AssetInfo` and `DebtInfo` sort on encrypted columns (`apps/intake/models.py:397,547`), so rows read back in arbitrary order within a type. Rows print in that order once 3b and 3c list them. Target: 3b.
- **A wrong comment on the fee-waiver flag.** It says 150% of the poverty line, but the code tests 60% of the median (`apps/eligibility/models.py:175-177`). 3f replaces the rule.
- **The seed's step number.** The seed sets `current_step=6` on an 8-step wizard (`seed_demo_data.py:576-577`).
- **E2E gaps:**
  - nothing reads `expected` in `personas.ts`;
  - the Priya journey never reaches `/sofa` or `/forms`;
  - the page objects never enter `financial_institution` or `is_in_collections`.
- **A comment on DIG-188.** `update_step` isn't atomic, and `complete`'s full save can overwrite a concurrent `reopen()`. 3a1 fixes both (§7).
- **A comment on DIG-274.** Missing median data is a 400 in one view and a 500 in the others, and the breakdown mislabels its date. 3a1 fixes both (§3.4).
