# Forms step 3b: Schedule A/B

- **Status:** drafted 2026-11-05. The owner answered three questions in brainstorming on 2026-11-05 (§2). The spec waits for the owner's review.
- **Drawn from:** the step 3 umbrella spec, `docs/superpowers/specs/2026-10-16-forms-step3-design.md` §5.8 (cited `U:<line>`), its rules U §4.1–§4.7 and Appendix A's 3b rows. Persona targets come from `docs/superpowers/specs/2026-10-16-forms-step3-personas.md` (cited `PS:<line>`). The form's words come from the blank template `data/forms/pdfs/form_b106ab.pdf`, its boxes from `data/forms/field_index/form_b106ab.index.json`.
- **Branch:** `feat/forms-step3b`, from develop `a795a80` (3a1, 3a2, 3e1, 3e2, 3f and DIG-459 merged). The PR targets develop.
- **Tags** such as `[Q24]` trace to the umbrella's Appendix A. `[UPL]` is the rule that DigniFi gives information, never advice.

Inline "**Call:**" marks a choice this spec makes where the umbrella, the code and the owner leave one open. §15 lists them all, so the owner can check them.

## 1. What 3b does, and why

Schedule A/B is the filer's sworn list of everything they own. Today DigniFi asks six loose asset types and prints 20 of the form's bindings: a few Yes/No boxes and some totals. No item prints, and a line never asked prints nothing, though the form says "Answer every question."

After 3b:

1. **Every line is asked in the form's own words** with the form's own examples, Part by Part, and nothing starts answered (§4) `[Q24]`.
2. **Every item prints on its line**, with its own boxes (§5, §8). Rows past a line's slots go on an attached sheet, and the totals include them.
3. **The vehicle lines are split**: line 3 (cars, trucks, motorcycles) from line 4 (boats, RVs, trailers), closing the RV gap.
4. **Both values are stored** for real estate and vehicles: the entire property and the portion the filer owns `[Q14.values]`. Schedule D reads them in 3c. Every total adds the portion.
5. **Ownership** is asked on lines 1, 3 and 4 only, where the form asks it: "only you" or "you and someone else". Debtor 2 boxes stay blank.
6. **Old rows** have no line. DigniFi refuses in plain words until the filer picks one. There is no default placement (§9).
7. **Encryption and order** `[Q7.assets]` `[DIG-164]`: asset descriptions and institutions are encrypted, and rows are ordered in Python.

Nothing in 3b deploys. Production waits for steps 3 to 5 and DIG-146.

**The failure this must not have.** A filer signs a form saying No to something they never saw asked, or a Yes line prints with its item missing. Either is worse than the gap it replaces, because the form is sworn.

## 2. What the owner decided (2026-11-05)

1. **Saying No.** A Yes/No on each line, nothing starts answered. No is stored. Yes opens the line's row. Complete refuses an unanswered line. One Part per screen. A No on the form's own gates (line 37 business, line 46 farm) skips those Parts' lines, as the form says, which leaves 35 answers for most filers.
2. **A leased vehicle** is an ordinary line 3 row. The filer types both values, $0 allowed, and DigniFi never suggests a number. A note says what a lease is worth is the filer's to say and legal aid can help. It goes on the counsel list (C-14), and the wording ships marked draft (U §5.2).
3. **A value the filer doesn't know.** Each value box offers "I don't know the value". The amount prints blank, and totals count it as zero. The row's description still prints. Review lists these back to the filer (§6.5). Whether "unknown" should print goes on the counsel list (C-15).

The form's Part 2 heading supports answer 2: "Do you own, lease, or have legal or equitable interest in any vehicles… If you lease a vehicle, also report it on Schedule G". The form's header supports answer 1 ("Answer every question") and the sheets ("If more space is needed, attach a separate sheet to this form").

## 3. The records

### 3.1 `AssetInfo` changes

| Field                           | Today                         | After 3b                                                                                                                                         |
| ------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ab_line`                       | none                          | New. Encrypted text, one of the catalog's line keys (§5). Null only on an old row.                                                               |
| `details`                       | none                          | New. Encrypted JSON holding what the line's shape asks (§5).                                                                                     |
| `description`                   | plaintext, required           | Encrypted, blank allowed. The line's one text box, whatever the form calls it: "Describe", "Institution name", "Name of entity", "Company name". |
| `current_value`                 | encrypted, required           | Encrypted, **nullable**. The form's "Current value of the portion you own" on every line.                                                        |
| `entire_value`                  | none                          | New. Encrypted decimal, nullable. Lines 1, 3 and 4 only.                                                                                         |
| `financial_institution`         | plaintext                     | Encrypted with its data migration `[Q7.assets]`. Off the API; its column stays.                                                                  |
| `asset_type`                    | required                      | Nullable, read-only, no new writes. Old rows keep it so §9 can show it. Dropped one release after this code is live.                             |
| `amount_owed`, `account_number` | on the step                   | Off the step. Columns stay, nothing reads them. 3c retires `amount_owed` (U Q13).                                                                |
| `equity`                        | property and serializer field | Removed. A/B has no equity figure.                                                                                                               |

`Meta.ordering` on encrypted columns goes. `ordered_assets(session)` (`apps/intake/asset_lines.py`) returns rows in Python, by the catalog's line order, then by id.

**`details` keys, all optional in storage:** `kind`, `street`, `street_2`, `city`, `state`, `zip`, `county`, `property_kinds` (a list), `other_kind`, `nature`, `who`, `community`, `other_info`, `make`, `model`, `year`, `mileage`, `percent`, `beneficiary`, `has_personal_info`, `value_unknown`, `entire_unknown`.

A null value means unanswered unless its flag says the filer chose "I don't know the value". Sending a value clears its flag.

**Call:** one encrypted JSON column, not twenty columns. Only some shapes use each key, and the household list and the business entries already work this way. `description` and the two values stay columns, because 3c and 3g read them.

### 3.2 `AssetLineAnswers`

New, one-to-one with the session (`related_name="asset_lines"`), table `asset_line_answers`. One encrypted JSON column, `answers`: `{"6": "no", "7": "yes"}`, one key per line asked. A missing key is unanswered. Answers never go in `FormAnswer` (U §4.2).

### 3.3 The API

- Session PATCH and PUT gain `asset_lines`, a map of line key to `"yes"`, `"no"` or null (which clears the answer). Only the keys sent change. An unknown line or value is a 400. The session read returns the map. Writes follow the "Saves lock the session" rule, and a save carrying `asset_lines` reopens a completed intake, as `assets` does.
- `assets` rows gain `ab_line`, `details` and `entire_value`. A 400 is only for a value no answer can have: an unknown line, a `kind` not on that line, a negative or over-wide amount, a `percent` outside 0–100. A missing answer saves, and Complete names it (§7). `_save_rows_by_id` keeps its rule: a stored row missing from the payload is deleted.
- **`current_value` keeps `min_value=0`**, so $0 saves. The step's "must be above 0" check goes.
- **`details` is replaced whole on a row save.** `_save_rows_by_id` sets each key sent, and every save sends full rows. The serializer enforces the flag rule: a row sent with a figure and its `value_unknown` or `entire_unknown` flag keeps the figure and clears the flag.
- **`AssetViewSet` stays** (`/assets/`), on the base serializer, which gains the same fields and loses `equity`. It requires `ab_line` on create, a 400 without one, so the per-item path can't make an old row. Its writes keep their lock and reopen.

## 4. The walk

The Assets step stays one wizard step (`assets`, step 5). `WIZARD_STEPS` doesn't change. The Parts are pages inside it: "Part 3 of 7" and the Part's title in the form's words.

**Call:** pages inside the step, not seven wizard steps. New steps would touch `update_step`'s 1–9 bound, the seed's `current_step`, every `?step=` link and every journey.

- **Each line** shows its number, words and examples, and an unselected No and Yes.
- **Yes** opens one row of the line's shape, with "Add another" where the shape takes more.
- **No, on a line with rows,** asks in the page (never a browser dialog) to remove them, naming how many. Canceling keeps the rows and the Yes. Removing the last row leaves the answer at Yes, and the line shows it needs an item or a No.
- **Continue** goes to the next Part. It is disabled until every line shown is answered and every row has what §7 requires. Continue from Part 7 leaves the step. **Back** goes to the previous Part, then the previous step.
- **Gates.** Line 1's No reads "No. Go to Part 2", as the form does. Line 37 No hides lines 38–44, and line 46 No hides lines 47–51. The gate's Yes shows them.
- **Where it opens.** On entry the step opens at the first Part with an unanswered line or an incomplete row, or Part 1 if none. The Part isn't stored.
- **A gate going to No** (line 37 or 46, with rows under it) asks the same way, naming how many items would go. Confirming removes those rows and clears the answers of the lines it hides, so a later Yes on the gate shows them unanswered. Line 1 hides nothing: it is an ordinary line whose No also leaves line 2 blank (§8.1).
- **Saving.** Each Part's Continue saves. **Every save sends every row and every answer of the whole step, unfiltered**, whichever Part is showing: a half-filled row, an old row and a line 16 row with no text included, because a stored row missing from the payload is deleted. Today's body filters on `asset_type` and `description` (`IntakeWizard.tsx:387`), and that filter goes. On this step autosave runs whether or not the Part can continue, unlike the `canProceed` condition other steps keep (`IntakeWizard.tsx:425`), so leaving mid-Part keeps the work. The body is `{assets: rows, asset_lines: map}` and is built the same way from loaded and edited data, so a visit alone saves nothing ("Autosave sends only real edits"). The inputs bound their amounts, so an autosave doesn't draw the server's 400.
- **The buttons.** The wizard's footer stays. The wizard holds the Part, and `handleNext` and `handleBack` move it while on this step: Continue saves and shows the next Part, with no `update_step` until it leaves Part 7. `canProceed` reflects the Part showing.
- **Old rows** appear above Part 1 (§9).

**On a phone.** Andrés fills this in between rides. Each Part scrolls as one column with no side scrolling, No and Yes are full-size tap targets, and amounts open the numeric keypad. Part 4 is the long one, 20 lines.

## 5. The line catalog

`apps/intake/asset_lines.py` is a pure module with no models: each line's key, Part, shape, capacity and kinds, in the form's order. `frontend/src/constants/assetLines.ts` is its copy, pinned by a backend test as `test_household_frontend_copy.py` pins the household words. The form's words and examples live in `formText.ts`, taken from the template's text, not the index's labels (which label lines 12–14 and 26–28 "No").

| Shape                     | Lines                                | Slots per line                                                                                                | The filer gives                                                                                                                                                                                                                          |
| ------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `place`                   | 1                                    | 3                                                                                                             | street (required), second address line, city, state, ZIP, county; "What is the property? Check all that apply" (8 kinds, `Other` with its text); who; community box; nature of interest ("if known"); other information; entire; portion |
| `vehicle`                 | 3                                    | 4                                                                                                             | make, model, year, approximate mileage, other information; who; community box; entire; portion                                                                                                                                           |
| `vehicle` without mileage | 4                                    | 2                                                                                                             | the same, without mileage, as the form has none                                                                                                                                                                                          |
| `item`                    | 6–14, 25–27, 30, 32–35, 38–41, 47–51 | 1                                                                                                             | description, portion                                                                                                                                                                                                                     |
| `item` plus a question    | 43                                   | 1                                                                                                             | "Do your lists include personally identifiable information", with Describe under its Yes; portion                                                                                                                                        |
| `cash`                    | 16                                   | 1                                                                                                             | portion only; the form has no text box                                                                                                                                                                                                   |
| `named`                   | 18, 20, 23, 24                       | 3                                                                                                             | the form's name words, portion                                                                                                                                                                                                           |
| `named`                   | 44                                   | 6                                                                                                             | description, portion                                                                                                                                                                                                                     |
| `named` with share        | 19, 42                               | 3                                                                                                             | name of entity, % of ownership, portion                                                                                                                                                                                                  |
| `insurance`               | 31                                   | 3                                                                                                             | company, beneficiary, surrender or refund value                                                                                                                                                                                          |
| `labelled`                | 17                                   | checking 2, savings 2, CD 1, other 4                                                                          | kind, institution, portion                                                                                                                                                                                                               |
| `labelled`                | 21                                   | 401(k), pension, IRA, retirement, Keogh 1 each; additional 2                                                  | kind, institution, portion                                                                                                                                                                                                               |
| `labelled`                | 22                                   | electric, gas, heating oil, security deposit, prepaid rent, telephone, water, rented furniture, other, 1 each | kind, name, portion                                                                                                                                                                                                                      |
| `shared box`              | 28                                   | one text box; federal, state, local                                                                           | kind, the information the form asks, portion                                                                                                                                                                                             |
| `shared box`              | 29                                   | one text box; alimony, maintenance, support, divorce settlement, property settlement                          | kind, information, portion                                                                                                                                                                                                               |
| `shared box`              | 53                                   | one text box; 3 amounts                                                                                       | information, portion                                                                                                                                                                                                                     |
| gate only                 | 37, 46                               | none                                                                                                          | Yes or No                                                                                                                                                                                                                                |

Lines 2, 5, 15, 36, 45, 52, 54 and 55–63 are arithmetic.

**Answer counts.** Lines 1, 3, 4 (3), 6–14 (9), 16–35 (20), 37, 46, 53 (3): 35. Answering Yes to 37 and 46 adds 7 and 5, for 47.

**Who.** `only_you` ticks "Debtor 1 only"; `with_someone` ticks "At least one of the debtors and another". The screen says "Only you" and "You and someone else" `[Q24]`. The other two boxes are never ticked. The community box stays unticked unless the filer ticks it.

**The shared-box lines.** Each row states its kind (28, 29) or takes the next amount by position (53). The one text box prints the rows' texts in order, joined with "; ". On 28 and 29 two rows of one kind print one amount, their sum. On 53, rows past the third go on a sheet with their own text, and the text box prints only the first three.

**Call:** every line takes rows the same way, so a second row on a one-slot line goes on a sheet rather than being refused or merged. There are two exceptions. Line 16 takes one row. Lines 28 and 29 never need a sheet: the form gives one amount per kind and one text box, so a second row of a kind adds to its amount and its text joins the box (a text too long is `ValueTooLong`). A row's kind can change freely: at print time each kind's group reads the rows of that kind, in `ordered_assets` order. A second 401(k) goes on a sheet too rather than into "Additional account", which the filer picks by choosing that kind: this keeps a row with its stated kind and keeps the code simple.

## 6. Words on the screen

### 6.1 The form's words

Line words and examples are quoted (`formText.ts`). No reading-level test scores them. DigniFi's own sentences go in `copy.ts`.

### 6.2 Notes, all information `[UPL]`

- **Line 3, under the form's sentence:** "If you lease this vehicle, what it is worth is yours to say. Legal aid can help you decide." Draft until C-14.
- **"I don't know the value":** "You can come back and change this. Legal aid can help you find out." Draft until C-15.
- **Portion:** the form's words, with no explanation of how to split a joint account. That stays the filer's answer (PS:639).
- **Secured claims:** the form's "Do not deduct secured claims or exemptions." appears at each value. The old equity figure and "Amount Owed" box go.
- **Nothing to list:** the existing "That's okay… it is not a failure" box stays above Part 1, reworded so it no longer says the section can be left blank.
- The exemption disclaimer stays.

### 6.3 Marked draft

Each draft sentence carries a `DRAFT: counsel C-n` comment in `copy.ts`, as 3e2's do. Filers see no mark. This spec's counsel items are:

| #    | Line | Question for counsel                                                                              |
| ---- | ---- | ------------------------------------------------------------------------------------------------- |
| C-14 | 3    | What value, if any, a lessee reports for a leased vehicle on A/B, and the note's wording          |
| C-15 | all  | Whether a value the filer doesn't know should print blank or as "Unknown", and the note's wording |

### 6.4 Review step

`ReviewStep` lists the rows by Part with each line's number, in `ordered_assets` order.

### 6.5 Values the filer doesn't know

Review adds a list headed in plain words: "You said you don't know the value of these", each row's line, its description and a link to the step. It never says whether that is a problem. The list is absent when there are none.

**Call:** the list lives on Review, the step the filer reads before Complete. The form itself prints only the blank amount.

## 7. What Complete refuses

`asset_step_gaps(session)` (`apps/intake/asset_lines.py`, which reads rows it is handed so the module stays pure, or a thin reader beside it) returns the gaps in the form's order, one sentence each, all with `step: "assets"`. Complete adds them after Schedule J line 3's gap and before the scanned-debt gap, which is wizard order.

1. An old row with no line (§9), naming its description, or its street, its make or "one item" when it has none.
2. An unanswered line that the gates show.
3. A Yes line with no row: "Line 7 says Yes. Add what you have, or change it to No."
4. A No line, or a line hidden by a gate's No, that has rows. The UI prevents it; the API doesn't, so Complete names it.
5. Yes to line 37 or 46 with every line under it No.
6. A row missing what its shape requires:

   - `place`: street, one kind (with its text under Other), who, both values.
   - `vehicle`: make, who, both values. Model, year and mileage aren't required: a trailer may have no model, and the form says "approximate".
   - `item`, `named`, `labelled`, `shared box`: the text and the value. Line 16: the value.
   - `labelled`, and `shared box` on 28 and 29: the kind.
   - `named` with share: the name, the value and `percent`. A blank share would print the template's own "0%" (see CLAUDE.md "Known form defects"), which is a false statement on that row.
   - `insurance`: the company and the value. The beneficiary is optional.
   - line 43: the question, the value, and the description under its Yes.

   A value counts as given when it has a figure or its "I don't know" flag.

**Forms.** Generate, Generate All, Regenerate and an unfiled download first call the same function. A gap raises `AssetStepGap`, a 422 of the whole call carrying `step: "assets"`, as `IncomeStepGap` does, because the A/B totals feed A/B, 106Sum 1a–1c and Form 101's `Check Box22`, not one form. So a session completed before 3b can't print stale totals. The packet list doesn't refuse it: no asset decides the packet. A filed form's download is unchanged. The dashboard already links a `step` refusal.

The session's completion percentage (`apps/intake/views.py:605`) counts the assets section done when `asset_step_gaps` finds nothing, not when a row exists: a filer with no property has finished it.

## 8. The forms

### 8.1 Printing

- The schema binds nearly every A/B widget (Debtor 2's boxes stay out). Bindings read `assets.line_<key>[].<attr>`, a new list namespace in `resolve_binding`, the E007 list pattern and `binding_fix` (step `assets`). The line's slot order is `ordered_assets`'s.
- **Yes/No boxes are derived from rows** `[Q24]`: `yes` with a row, `no` with none and the line shown, blank when a gate's No hid it. Complete guarantees they agree with the stored answers.
- **Under a gate's No,** lines 38–44 and 47–51 stay blank, and so do lines 2, 45 and 52, which the form's "Go to" skips: line 1's No leaves line 2 blank, line 37's line 45, line 46's line 52. Lines 55, 59 and 60 still print 0.00.
- **Unknown values** print blank (§2). A sheet's cell is blank too.
- **A value too long for its box** is the existing `ValueTooLong` 422, with `step: "assets"`. A row's text can be split with "Add another".
- **No account numbers** are asked or printed.

### 8.2 Totals

All add `current_value`, the portion, over rows in the line's Part, sheets included. An unknown value counts as zero.

- 2 = Part 1, 5 = Part 2, 15 = Part 3, 36 = Part 4, 45 = Part 5, 52 = Part 6, 54 = Part 7.
- 55–61 copy them. 62 adds 56–61, 63 adds 55 and 62.
- 5, 15, 36, 54 and 55–63 always print, so a filer with nothing shows 0.00, following U §4.5 and CLAUDE.md's "a total counts an unasked line as zero and still prints". 2, 45 and 52 print except under their gate's No.
- 45, 52, 59, 60 and every line-level amount are new bindings.

The `_total_*` and `has_*` rules keyed on `asset_type` go, replaced by rules keyed on the catalog. `other_asset_descriptions` goes. 106Sum 1a, 1b, 1c and Form 101's `total_assets_range` read the new totals.

### 8.3 Two extensions to the sheets

3a2's sheets can't print A/B as they are. Both limits were checked against the code on 2026-11-05:

1. **The line column.** `LINE_WIDTH` is 36 pt, and E007 measures row 9999. "17.9999" is 36.1 pt, wider than the column's 32 pt inside its padding, so every two-digit line fails `fits_line_column`. A sheet gains an optional `line_width`, default 36, which A/B sets to 48. The sheet part stores it, so a filed sheet redraws as filed, and a part without it draws at 36. Every existing sheet is unchanged.
2. **A column of words for several boxes.** E007 requires a column for every slot binding and refuses a single box's `{"true": …}` as a column. A `place` row has 8 "check all that apply" boxes and a community box, and its 13 values won't fit 504 pt one per column. A column gains an optional `covers`: the slot bindings it prints. Its own `binding` is then a list binding no slot needs to bind, resolved like any other. E007 counts a covered binding as printed. Example columns for line 1: "Where it is" (covers the address), "What it is" (covers the kinds and their text), "Who has an interest" (covers who, nature, community and other information), "Entire", "Portion". Cells wrap, so a long address takes more lines.

**Labelled lines.** Slots are filled by position, and on 17, 21 and 22 the kind decides the slot. So each kind is its own group (`ab_17_checking` capacity 2, `ab_17_savings` capacity 2, and so on), and its sheet's title and `number` name it, such as "17c.3", so a row never collides with the form's own 17.3. A filer with several overflowing kinds gets several sheets.

**Call:** two small, optional schema fields rather than a new sheet kind or a cap on rows. The umbrella promises rows past capacity go on a sheet, and neither change touches a form that doesn't set them.

### 8.4 Oracle

Every new placement gets its row in `step2_verification.json`, citing the box's index label, in the same commit. Tier 1 covers the new boxes, tier 2's `ASSERTED_CASES` rises on purpose, tier 3 gains each persona's A/B values, and `known_defects.json` stays `[]`. An index label that disagrees with the template's printed words is settled against the rendered page.

## 9. Old rows

A row with no `ab_line` is an old row. Above Part 1 the step lists each one: its description, its value and its old type, with a line picker in the form's words and "Remove". Picking a line moves it into that line, answers that line Yes, and asks for what the shape still needs. No line is ever suggested, not even from the old type (U:412).

The old value is shown, and it stays in `current_value` as the portion. On lines 1, 3 and 4 the filer must also give the entire value. It isn't copied, because a co-owned car's old figure may be either one.

The migration encrypts `description` and `financial_institution` and sets no `ab_line`. Undone, it decrypts them; a row added after 3b comes back with its description and value and no type.

## 10. Personas

Each persona's target is in the personas document: Maria PS:147, James PS:388, Priya PS:623, DeShawn PS:844, Sarah PS:1081, Andrés PS:1307 and PS:1392. Seed, E2E fixture and brief change together. `seed_demo_data` writes each persona's rows and answers; personas seeded before 3b are refused until `--reset`.

**Corrections to the targets, which were written before this catalog:**

- Priya's savings and Andrés's share savings are shown at 17.2. A savings kind prints on 17.3, because the form prints 17.1–17.2 as checking. Their totals don't change.
- James's "Wallet" under line 16: line 16 has no text box, so it isn't stored.
- Sarah keeps no assets (PS:1083, README). Her journey answers No to every line, which is now the suite's empty-A/B case.
- PS:1430's open question is closed by §2.
- The asset `amount_owed` values stay in the seed until 3c, off the step.

**Hand-checked totals (tier 3).** Maria 5 = 6,500, 15 = 1,050, 36 = 380, 62 = 63 = 7,930 (PS:250). Priya 62 = 106Sum 1b = 1c = 67,900 (PS:640). Andrés 5 = 4,300, 15 = 1,900, 36 = 557, 45 = 460, 55 = 0, 62 = 63 = 7,217 (PS:1419). James and DeShawn from their tables; DeShawn's 15 is 2,800 and 36 is 12,700.

**Sheets are exercised by synthetic tests.** No persona overflows a line. Andrés is the persona with Part 5, a leased car at $0/$0 and a co-owned car.

**E2E.** `wizard.page.ts` gains `answerLinesNo()` for a Part's unanswered lines, and `addAsset` takes a line. The scanned-bill journey (which spreads `SARAH`) answers the walk too.

## 11. CLAUDE.md gotchas rewritten `[GOTCHAS]`

- **Nested debts and assets save by id:** assets save with `asset_lines`, and every save sends the whole step.
- **Forms need a completed intake:** the new gaps, `AssetStepGap`, and the new refusal order.
- **Autosave sends only real edits:** step 5's body.
- **Seed order:** personas seeded before 3b.
- **Schemas are checked at startup:** `assets.`, `line_width`, `covers`.
- **Blank, not 0.00:** A/B's rules (§8.2).
- A new gotcha for the line catalog and its frontend copy, and the File Map's `asset_lines.py`.

## 12. Testing

- **Backend.** The catalog matches the index: every shape's boxes exist on the page the catalog says, and every line has a shape. Gaps, one test per item of §7. Every encrypted column holds ciphertext. Migration forward and back. The session lock test's `WRITES` gains `asset_lines`. API bounds, $0 saves, and a figure clears "I don't know". `ordered_assets` doesn't depend on ciphertext.
- **Forms.** Each shape prints on its boxes, read off the printed page (`read_drawn`). Overflow on each shape reaches a sheet, and the totals include it. Unknown values print blank and add zero. Gates leave their lines blank. A filed sheet part with no `line_width` draws at 36. E007 refuses a `covers` naming a binding no slot has, and a covered box still needs its column.
- **Frontend (vitest).** Continue stays disabled until the Part is answered. No on a line with rows asks first. Every save carries rows of other Parts. A loaded step sends nothing until edited. Old rows block Continue. Review's list shows and hides. Line words and axe checks on each Part.
- **E2E.** Every journey walks the lines. Andrés's reaches Part 5.
- **Words.** UPL and reading-level checks on `copy.ts`'s new sentences. No sentence predicts an outcome or suggests a value.

## 13. Not in 3b

- Schedule D's Column B and the debt-to-property link (3c).
- Schedule C's choices (3g).
- Debtor 2's boxes, and joint filing.
- Pre-filling assets from uploads, and Plaid.
- Dropping `asset_type` (one release later) and `amount_owed` (3c).

## 14. What changed from the umbrella

- §8.3's two sheet extensions. U:420 assumed 3a2's sheets were enough.
- `current_value` becomes nullable, for §2's unknown values, which the umbrella didn't have.
- U:422's open question on leased vehicles is closed by §2.
- The persona target corrections in §10.
- Two new counsel items, C-14 and C-15.

## 15. Calls this spec makes

1. One encrypted `details` column rather than twenty columns (§3.1).
2. The Parts are pages in one wizard step (§4).
3. A second row on any line goes on a sheet, except line 16 (one row) and lines 28 and 29 (rows add up per kind, texts join) (§5).
4. `amount_owed`, `account_number` and the equity figure leave the step now, and their columns stay (§3.1).
5. Required fields per shape, including a required share on lines 19 and 42, because a blank prints "0%" (§7).
6. The unknown-values list lives on Review (§6.5).
7. An asset gap refuses the whole forms call, as an income gap does (§7).
8. Old values stay as the portion; the entire value is asked, never copied (§9).
9. `line_width` and `covers` on sheets (§8.3).
10. Under a gate's No, lines 2, 45 and 52 stay blank, while the Part 8 totals print 0.00 (§8.2).
11. Each labelled kind is its own group with its own sheet (§8.3).
12. This step sends half-filled rows and autosaves mid-Part, so leaving keeps the work (§4).
13. The wizard holds the Part, and its footer's buttons move it; `update_step` waits for Part 7 (§4).
14. A gate going to No removes the rows under it after asking, and clears those lines' answers (§4).
15. `details` is replaced whole on a save (§3.3).
16. `AssetViewSet` stays and requires `ab_line` on create (§3.3).
