# Forms step 3d: priority claims

- **Status:** drafted 2026-11-11. The owner answered two questions on 2026-11-11 (§2). A builder check, a fact-check of 118 claims against the tree, and a UPL and reading-level review of the draft copy ran on 2026-11-11; their findings are folded in, and none needed the owner. Not yet approved.
- **Drawn from:** the step 3 umbrella spec, `docs/superpowers/specs/2026-10-16-forms-step3-design.md` §5.10 (cited `U:<line>`), its rules U §4.1–§4.7 and Appendix A's 3d rows. Persona targets come from `docs/superpowers/specs/2026-10-16-forms-step3-personas.md` (cited `PS:<line>`). `C:<line>` is the 3c spec, `2026-11-06-forms-step3c-design.md`. The forms' words come from the blank templates `form_b106ef.pdf`, `form_b106sum.pdf` and `b_122a-2_0425-form.pdf` in `data/forms/pdfs/`, read as printed text with PyMuPDF on 2026-11-11.
- **Tree:** `feat/forms-step3d`, 7de0b96 (develop after 3c6). Code citations come from a survey of the same tree (40924c7, whose tree 7de0b96 merged unchanged). No test suite ran for this spec.
- **Not read:** the national instruction booklet's explanation of each priority type, the DIG-119 ticket text, and `docs/testing/persona-briefs/` beyond the lines the personas spec quotes.
- **Tags** such as `[Q15]` trace to the umbrella's Appendix A. `[UPL]` is the rule that DigniFi gives information, never advice. `[C-2]` is the counsel item on the priority definitions.

Inline "**Builder's call Bn:**" marks a choice this spec makes where the umbrella, the code and the owner leave one open. §11 lists them all, so the owner can check them.

## 1. What 3d does, and why

Schedule E/F has two lists of unsecured debts. Part 1 holds **priority** claims, the kinds the law pays first: support owed to a child or a former spouse, certain taxes, debts for a death or injury caused while intoxicated, and a few others. Part 2 holds everything else. Today DigniFi never asks which list a debt belongs on. Every unsecured debt prints in Part 2, Part 1 stays blank, and its line 1 ("Do any creditors have priority unsecured claims against you?") is left unanswered on a sworn form.

Two filers in the persona set owe the IRS for 2025 income tax (PS:659-663, PS:1328). Their tax debt belongs in Part 1, and the totals that follow from it (E/F 6b and 6e, Form 106Sum 3a) are blank. Separately, the wizard labels every student loan "priority" behind the filer's back (`DebtsStep.tsx:133-137`, DIG-119). No form reads that label, but it is a legal characterization DigniFi has no business making (U §4.1).

After 3d:

1. **The filer answers, for each unsecured debt, whether it is one of E/F Part 1's four types, "No", or "Not sure"** `[Q15]`. Nothing is pre-selected. Under a type they type the priority and nonpriority amounts from the creditor's notice and the amount past due on the date they file.
2. **E/F Part 1 prints the debts the filer put there**, on page 1 and copies of page 2, with line 1, the type totals 6a–6e and Form 106Sum's priority lines. Part 2 then holds only the rest.
3. **The wizard stops calling student loans "priority"** `[DIG-119]`, and the scan pipeline stops writing the label.

Nothing in 3d deploys. Production waits for steps 3 to 5 and DIG-146.

**The failure this must not have.** A debt prints in Part 1 that the filer never put there, a debt prints in both Parts or in neither, or a line number shifts so that Part 3 or Schedule H cites the wrong row. The sharpest case is the stored default: every debt today carries `is_priority = False` and a `priority_classification` of `"unsecured"`, `"secured"` or `"priority"` (`models.py:844-848,868-873`; the wizard writes it from the debt's kind), none of which the filer ever said. Reading either as an answer would move debts silently. Second sharpest: the means test changing because a priority answer now exists (§2).

### Goals

- Every confirmed unsecured debt prints in exactly one of E/F Part 1 or Part 2, by the filer's answer alone.
- E/F 6e + 6j equals the sum of the confirmed unsecured debts' totals, and 106Sum 3c still equals 2 + 3a + 3b, for every persona and every test session.
- Each Part numbers its own rows: Part 1 "2.1", "2.2", … over Part 1's debts and Part 2 "4.1", "4.2", … over Part 2's, so Part 1's count never offsets a Part 2 number. (A debt that leaves Part 2 does renumber the Part 2 rows after it, as removing any row does today; Part 3 and Schedule H cite the new numbers, since they read the same rows.)
- A claim with both a priority and a nonpriority amount prints once, in Part 1, with both amounts: the form's own page 1 instruction ("If a claim has both priority and nonpriority amounts, list that claim here and show both priority and nonpriority amounts"). It never prints again in Part 2.
- The means test gives the same result before and after 3d for every persona.

### Non-goals

- 122A-2 lines 35, 41 and 42 (3h, DIG-275). 3d stores the past-due figure line 35 reads and makes 6j and 3b nonpriority-only, which line 41a reads.
- Schedule E/F Part 2's type ticks for divorce obligations and pension debts (6g, 6h, C:672's C-19). They stay unasked and blank.
- Debtor 2's boxes, and joint filing.
- A classifier. Nothing suggests a type from the creditor's name, the debt's kind or a scan.

### Anti-goals

- **No suggested answer.** The question starts unanswered for every debt, including an IRS bill read from a scan and a student loan (U §4.1, U:492).
- **No stored default read as an answer.** `is_priority` and `priority_classification` never become a priority answer, in a migration or anywhere else (§5.1).
- **No change to the means test in 3d** (§2).
- **No verdict.** DigniFi never tells a filer that a debt "is priority" or "will be paid first". The definitions describe the form's categories; the filer picks.

## 2. What the owner decided

**Owner, 2026-11-11, on the means test: "Off until 3h".** Today `ExpenseDeductionCalculator._get_priority_debts_monthly` subtracts the monthly payments of debts with `is_priority=True` from disposable income (`expense_deduction_calculator.py:54-57,109-114`). Nothing in production writes `is_priority`, so the deduction is $0 for every filer. Once 3d records priority answers, wiring the deduction to them would change above-median filers' results, and it would subtract the wrong figure anyway: 122A-2 line 35 takes the amount **past due** divided by 60, not the monthly payment (DIG-275). So in 3d:

- the deduction reads nothing and is $0 until 3h replaces it with line 35's figure inside the one calculator (U:548);
- a test pins that a confirmed debt answered with a priority type, carrying a monthly payment and a past-due amount, leaves `priority_debts_monthly` at 0 and disposable income unchanged.

**Owner, 2026-11-11, on the build: two PRs, "lets go 2"** (§4). 3d1 asks and stores; 3d2 prints.

**Two calls stated to the owner on 2026-11-11 with the approaches, and not objected to:**

- **Storage** (B1). The umbrella says "`is_priority` is encrypted when first written, and it is the only stored answer" (U:491). A yes/no cannot hold the type, "Not sure" or "not answered yet", and the form also needs the split and the past-due amount (U:490; PS:661, PS:1328 store them). 3d stores exactly what the filer typed, all encrypted (§5.1). The old flag is no longer read or written, and its column drops a release later.
- **Debts saved before 3d** (B2). Their stored `False` was a default, not something the filer said, so they start unanswered and Complete asks.

**Standing rules that bind.** The filer decides, and nothing is pre-selected (U §4.1). New filer data is encrypted (U §4.2). Information, never advice. Every refusal names the step or page that fixes it (U:127). Blank versus zero (U §4.5). Counsel items ship as draft comments and never block a merge (U:633). Security, encryption, UPL, IDOR and log-leak tests keep their assertions: a test that must change for a 3d field changes its fixture, never what it asserts.

## 3. Spec corrections

| #   | The source says                                                                                  | The code or form says                                                                                                                                                                               | 3d does                                                                                                                                                   |
| --- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1  | U:491: `is_priority` "is the only stored answer"                                                 | U:490 itself asks for the type, the split and the past-due amount; `is_priority` is a plain `BooleanField(default=False)` (`models.py:921-924`) that cannot hold unanswered or "Not sure"           | Five encrypted columns (§5.1, B1)                                                                                                                         |
| S2  | U:480: E/F Part 1's question "Is this one of these?"                                             | The template prints no per-debt question. Each Part 1 row prints "Type of PRIORITY unsecured claim:" and the four ticks; line 1 asks "Do any creditors have priority unsecured claims against you?" | DigniFi asks in its own words, "Is this amount owed one of these kinds?" (copy.ts), a plainer form of U:480's; the four options are the form's words (B3) |
| S3  | U:482-485: the four types in lower case, "claims for death or personal injury while intoxicated" | The template prints "Domestic support obligations", "Taxes and certain other debts you owe the government", "Claims for death or personal injury while you were intoxicated" and "Other. Specify"   | The template's words, in formText.ts                                                                                                                      |
| S4  | C:290: "`is_priority` stays for 3d"                                                              | Its one reader is the deduction the owner switched off (§2)                                                                                                                                         | Retired in 3d1, column kept a release (§5.1)                                                                                                              |
| S5  | U:467: `DebtInfo.Meta.ordering` on `priority_classification` (`models.py:547`)                   | Gone since 3c2 (migration 0039; `models.py:1007-1008` is `db_table` only)                                                                                                                           | Nothing to move                                                                                                                                           |
| S6  | PS:710: Priya's 106Sum 3a / 3b / 3c "3,000 / 57,000 / 60,000"                                    | 3c is 2 + 3a + 3b (rule `total_debts`, every confirmed debt); C:95 S15 already corrected it                                                                                                         | 3,000 / 57,000 / 74,900                                                                                                                                   |
| S7  | PS:1403: Andrés's "4.5 Not sure"; PS:1332 names the toll debt 4.4                                | C:100 S20 fixed Part 2's order: 4.5 is Illinois State Toll Highway Authority (`seed_demo_data.py:1116`)                                                                                             | The toll debt answers "Not sure" and stays 4.5                                                                                                            |
| S8  | PS:730 (Priya: "lines 41-42 not reached") against PS:1114 and U:496                              | Lines 41-42 are reached only when line 40 is not above the limit; both are 3h's                                                                                                                     | No 3d effect; 3h settles it                                                                                                                               |
| S9  | My approaches message (2026-11-11): "Part 3, D Part 2 and H cite Part 1 lines"                   | D Part 2 cites Schedule D's own lines only                                                                                                                                                          | E/F Part 3 and H gain Part 1 citations (§6.1)                                                                                                             |

## 4. Two PRs

| PR      | What it does                                                                                                                                                                                                   | What it leaves                                                                   |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **3d1** | The five columns, the question on the Amounts Owed step, its gaps, Review, the API, the means-test cut, DIG-119, drafts left unanswered, the seed's and journeys' answers ("No", and Andrés's toll "Not sure") | Every printed form. A debt answered with a type still prints in Part 2 until 3d2 |
| **3d2** | `claim_rows`' Part 1 list, E/F Part 1 and line 1, 6a–6j, Part 3's and H's citations, 106Sum 3a, 3b, 9a–9c and 9g, the List of Creditors' order, the IRS rows for Priya and Andrés, tier 3                      | 122A-2 (3h)                                                                      |

The in-between state (answers stored, Part 1 not printed) never reaches a filer, since nothing deploys before step 5. **Builder's call B9:** the persona IRS rows land in 3d2, not 3d1, so that 3d1 changes no printed form and tier 3 moves once. 3d1's seed and journeys answer "No" on every unsecured debt and "Not sure" on Andrés's toll debt, which print exactly as today.

Each PR gets its own plan, 3d1 first. 3d2 branches from develop after 3d1 merges.

## 5. 3d1: ask and store

### 5.1 Records

**Builder's call B1, the columns.** On `DebtInfo`, all nullable, all encrypted (U §4.2), null meaning unanswered or blank:

| Column               | Type                                            | Holds                                                                       |
| -------------------- | ----------------------------------------------- | --------------------------------------------------------------------------- |
| `priority_answer`    | `EncryptedCharField`, one of `PRIORITY_ANSWERS` | `domestic_support`, `taxes`, `intoxicated`, `other`, `no`, `not_sure` (B17) |
| `priority_other`     | `EncryptedCharField`, at most 100 characters    | The words after "Other. Specify" (B6)                                       |
| `priority_amount`    | `EncryptedDecimalField`                         | The "Priority amount" the filer copies from the notice                      |
| `nonpriority_amount` | `EncryptedDecimalField`                         | The "Nonpriority amount"                                                    |
| `past_due_amount`    | `EncryptedDecimalField`                         | The amount past due on the date they file, for 122A-2 line 35 (3h)          |

`PRIORITY_TYPES` is the first four keys, the ones that put a debt in Part 1. The serializer declares the three amounts as `DecimalField(12, 2, min_value=0, allow_null=True, required=False)`, as it does `amount_owed` (DRF would map an encrypted decimal to a string), so a negative or a value wider than `DecimalField(12, 2)` is a 400 and never reaches storage, where it would make every read of the session 500. `priority_answer` is a `ChoiceField` with `allow_null`, like `offset_answer` (`serializers.py:670`): any other value is a 400. A `priority_other` longer than 100 characters is a 400.

The five fields save on both paths, like `offset_answer`: the nested session save (`NestedDebtInfoSerializer`, `serializers.py:752-767`, through `_save_rows_by_id`) and the per-item `DebtViewSet` (B18). The server stores what is sent and judges nothing between them. Readers apply the conditions: a figure or the "Other" text counts only while the answer is one of `PRIORITY_TYPES`, and no priority field counts on a secured debt (§5.3, §6.1).

**Migration** `0041` adds the five columns. No data step: every existing row starts with all five null (B2). A test pins that a row stored with `is_priority=True`, and one with `priority_classification="priority"`, both come out of the migration unanswered.

**Retired fields.**

- `priority_classification` leaves `DebtInfoSerializer.Meta.fields` (`serializers.py:690`) and `types/api.ts:477`. An older wizard bundle that still sends it is ignored, since DRF drops an unknown key. The column keeps its default, nothing sets or reads it, and it drops a release after 3d is live (B8).
- `is_priority` loses its one reader (§5.4). It was never on the API. Its column drops a release after 3d is live (B8).

Tests that construct a `DebtInfo` with either keyword keep working while the columns exist. A test that uses `is_priority=True` to mean "priority on the forms" moves to `priority_answer` in 3d2, where the forms first read it.

### 5.2 The question on the Amounts Owed step

**Builder's call B4, placement.** For each debt with "Can the lender take back property…" answered No, the question sits right after the offset question (`DebtsStep.tsx:722-733`), as a fieldset of six radios named `priority_answer_<i>`, values the `PRIORITY_ANSWERS` keys. It reuses the step's `ChoiceGroup` (`DebtsStep.tsx:219-265`) or its pattern: the legend carries the required mark, the radios carry `aria-required`, and nothing is checked until the filer presses one. A secured debt doesn't show it (the form keeps secured debts off E/F, page 1's instructions).

What the filer sees (words are drafts; §7):

```
Is this amount owed one of these kinds? *
  ( ) Domestic support obligations
      Child support, or support for a spouse or former spouse. A court
      order, a divorce or separation agreement, or a government agency
      sets it.
  ( ) Taxes and certain other debts you owe the government
      Certain taxes, such as some income taxes, and certain other debts
      owed to the government. Not every debt owed to the government is
      one.
  ( ) Claims for death or personal injury while you were intoxicated
      Money owed for a death or injury caused by a car, boat or plane.
      It applies only if the person at the controls was intoxicated.
  ( ) Other. Specify
      A few other kinds the law lists, such as wages owed to a worker.
      Legal aid can tell you whether yours is one.
  ( ) No, none of these
  ( ) Not sure

-- under one of the four types --
  Priority amount      [$          ]
  Nonpriority amount   [$          ]
    If the bill or notice shows a priority amount and a nonpriority
    amount, copy them here. Leave a box blank if it doesn't show them.
  How much of this is past due as of the day you file? *   [$          ]
    Do not include current or ongoing priority claims.
    Leave out amounts that are not due yet. Enter 0 if none of it is
    past due.

-- under Other, also --
  Other. Specify *   [                              ]

-- under Not sure --
  If you are not sure, this amount goes in Part 2 of Schedule E/F, with
  your other amounts owed. You can change your answer later. Legal aid
  can help you find out which part fits.
```

The definitions are second drafts. A copy review on 2026-11-11 scored each with the reading-level test's method (each at grade 8 or below) and replaced three first drafts: one that read as "any debt owed to a government", one that read as an accusation in the second person, and a "Not sure" note that read as a decision made for the filer. All stay drafts for counsel (§7). Points for counsel `[C-2]` from that review: whether the intoxication definition should name the filer's own operation and its unlawfulness (§ 507(a)(10)), whether the support definition should name a government agency owed the support (§ 101(14A)), which examples "Other" should name, and whether a "Not sure" debt in Part 2 of a sworn form needs more than the legal-aid note.

- Each definition is the description of its radio (for example `aria-describedby`), so a screen reader hears it with the option.
- The amount boxes are the step's own amount boxes: a box holding part of a number holds Continue, as the step's other boxes do (`countPartialBox`).
- **Clearing.** Answering the secured question Yes clears all five fields, as `securedChanges(true)` already clears `offset_answer` (`DebtsStep.tsx:212-217`). Moving the answer from one of the four types to No or Not sure clears the two split amounts, the past-due amount and the "Other" text. Moving between two of the four types clears the "Other" text only when the new type isn't Other. **Builder's call B4 (cont.):** 3h will add up past-due amounts, so a hidden figure must not stay in the row the wizard sends. The readers' conditions (§5.1) back this up on the server.
- **Saving.** `sentDebt` spreads the row (`utils/claimRows.ts:113-122`), so the five keys go with every debts save. `isBlankDebt` (`claimRows.ts:28-57`) counts a row with any of the five as touched. The three amounts join `DEBT_AMOUNT_FIELDS` so `hydrateAmounts` converts them as session data enters step state, and the answer and text hydrate as stored, so loading a step and saving it unchanged builds the same body and autosave sends nothing.
- **Review** lists each unsecured debt's answer in the option's words and, under a type, the three figures as typed, blank where blank.

### 5.3 Gaps

**Builder's call B7.** `_debt_answer_gaps` (`claims.py:289-300`) gains three gaps, after the offset gap, for a debt that is not secured, draft or confirmed (step `debts`):

| Gap                       | When                                                                | Sentence (draft, one literal each)                                             |
| ------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `DEBT_GAP_PRIORITY`       | `priority_answer` is null                                           | "Answer “Is this amount owed one of these kinds?” for {name}."                 |
| `DEBT_GAP_PRIORITY_OTHER` | the answer is `other` and `priority_other` is blank once trimmed    | "Fill in “Other. Specify” for {name}."                                         |
| `DEBT_GAP_PAST_DUE`       | the answer is one of `PRIORITY_TYPES` and `past_due_amount` is null | "Enter how much of what you owe {name} is past due. Enter 0 if none of it is." |

No sentence calls the debt a "priority claim": the filer has picked a box on the form, and DigniFi doesn't characterize the debt (the copy review struck a first draft that did). The curly quotes must be the same characters in `claims.py` and `copy.ts`, since `test_claim_gaps.py` compares the literals.

**Builder's call B5.** The past-due amount is required under a type, and $0 is an answer: 3h's line 35 must tell "nothing past due" from "not answered". The split may stay blank (U:490: "a blank prints blank"), so a blank split is no gap. No check compares the split or the past-due amount with the total: the figures are the creditor's, and the form prints them as the filer copied them.

"No" and "Not sure" are answers, so neither is a gap. A scanned draft starts unanswered, so a draft unsecured debt shows the priority gap beside the draft sentence, as it shows its other gaps today.

The sentences live in `claims.py` and, as one literal each, in `frontend/src/constants/copy.ts`; `test_claim_gaps.py` pins them (`_copy_sentence`, `STATES`, `test_every_gap_sentence_in_copy_is_pinned`), and `upl-claims-copy.test.ts`'s `CLAIM_NAMES` lists them. `debtGaps.ts` copies the three gaps in the same place, after the offset gap, so Continue and Complete give the same sentence.

`complete_debt` (`apps/intake/tests/builders.py:186-215`) gains `priority_answer="no"` on an unsecured debt, so "a complete debt has no gap" keeps holding everywhere it is used.

### 5.4 The means test

`_get_priority_debts_monthly` returns `Decimal("0")` without reading any debt, with a comment naming DIG-275 and 3h (§2). The new pin: a confirmed debt answered `taxes` with a $200 monthly payment and a $3,000 past-due amount leaves `priority_debts_monthly` at 0 and disposable income unchanged. The tests that set `is_priority=True` today change as follows:

- `test_expense_deduction_calculator.py` (fixture at `:37`, assertion of 200 at `:69`): the 200 becomes the pin's 0.
- `test_means_test_calculator.py:886-960` reach their verdicts through the deduction. Their fixture's $3,500 of priority debt takes $7,000 of CMI less $2,799 of allowed expenses down to $701, under the $756.25 line, so one test asserts `passes_above_median` and "may still be eligible" (`:925-930`) and the other asserts 3,500.00 and 701.00 (`:945-948`). With the deduction at 0 that filer's disposable income is $4,201 and the verdict flips. These tests keep what they guard (the above-median path that passes, and its message) with a fixture that gets under $756.25 without the deduction (a lower CMI or higher allowed expenses), and their 3,500.00 assertion becomes the pin's 0. A test whose subject was the deduction itself is replaced by the pin, not kept with a new figure. `MeansTest.priority_debts_monthly` stays, stored as 0. The result messages' words "after accounting for allowable expenses and priority debts" (`means_test_calculator.py:148,156`) stay as they are; 3h owns them with the calculator.

### 5.5 DIG-119

- `DEBT_CATEGORY_META` (`DebtsStep.tsx:114-154`) loses `priority_classification`, and `changeType` (`:356-366`) stops writing it. A student loan is asked the question like any other unsecured debt, with nothing pre-selected.
- `draft_debt.py` stops writing it (`:61`, `:88`) and `_priority_for_type` (`:106-108`) goes, with its assertion in `test_draft_debt.py:154`. A scanned draft leaves all five priority fields null.
- The test fixtures that send the field (`IntakeWizard.test.tsx` at the lines the survey lists; `test_session_lock.py:629`; `test_session_nested_save.py:61`) drop it.

### 5.6 Seed and journeys

- **Seed.** Every persona's unsecured debts get `priority_answer="no"`, except Andrés's Illinois State Toll Highway Authority debt (`seed_demo_data.py:1116`), which gets `"not_sure"` (PS:1352, S7). Sarah answers No throughout (PS:1108-1114). A persona seeded before 3d has no answer, so Complete and every forms call past the Assets step's check meet the priority gap first among its debt answers: re-create with `seed_demo_data --reset`, the existing pattern.
- **Journeys.** `fillDebtAnswers` (`e2e/pages/wizard.page.ts:447-515`) answers `priority_answer_<i>` for an unsecured row, default `"no"`, as it answers `offset_answer_<i>`. `PersonaDebt` gains an optional `priority_answer`, and Andrés's toll row sets `"not_sure"`. `scanned-bill-journey` answers its draft "no" through `SCANNED_BILL_ANSWERS`.

### 5.7 Testing (3d1)

- **Records:** the five columns are ciphertext in the database (the claims encryption test's pattern); the 400s (unknown answer, negative, too wide, "Other" text past 100) on the nested and per-item paths; null round-trips; the migration pin (§5.1).
- **Gaps:** each gap and its sentence; their place after offset; a secured debt has none of them; "No" and "Not sure" have none; a blank split has none; $0 past due has none; a draft shows the priority gap.
- **Means test:** the §5.4 pin; Priya's seeded disposable income stays 10,336.00 (`test_seed_demo_data.py:221-225`).
- **Wizard:** the question shows only on an unsecured debt; nothing is checked on a new, a loaded or a scanned debt, a student loan included; each clearing rule; the "Not sure" note; Continue held by each gap and by a partial box; the save body carries the five keys and leaves `priority_classification` out; a visit to the step sends nothing; Review's words.
- **Copy:** the gap pins, `CLAIM_NAMES`, every other new sentence in `OTHER_CLAIM_SENTENCES`, the reading-level test (automatic for copy.ts), and a pin of the frontend's answer keys to `PRIORITY_ANSWERS` in `test_claims_frontend_copy.py`.
- **Journeys:** all eight pass with the default "no" and Andrés's "Not sure".
- **Unchanged on purpose:** every tier 1–3 oracle case and every printed form (3d1 prints nothing new).

## 6. 3d2: print

### 6.1 Rows

`claim_rows._read` (`claim_rows.py:161-185`) splits the confirmed unsecured debts, in `ordered_debts` order, into:

- **`priority`**, E/F Part 1: answer one of `PRIORITY_TYPES`, numbered "2.1", "2.2", …;
- **`unsecured`**, E/F Part 2: every other unsecured debt, numbered "4.1", "4.2", … over this list alone.

**Builder's call B15:** "No", "Not sure" and an unanswered debt all go to Part 2. An unanswered debt can't reach a form, since `_prepare` refuses its gap first; Part 2 is where it printed before 3d, and no answer of the filer's is asserted by leaving it there.

**Builder's call B11:** `ClaimRows` gains `priority` as a seventh list. The touch points are the `ClaimRows` dataclass (`claim_rows.py:76-82`), `_read`, `CLAIM_LISTS` (`claim_rows.py:21`, read only by `test_claims_bindings.py`), `CLAIM_CELLS` (`fill_resolver.py:340`), `creditor_entries` and `test_claims_bindings.py`. `one_read_of_claims` and the `claims.` namespace in `checks.py` name no list and need no change.

**Builder's call B10, Part 3.** E/F Part 3 stays one list, `unsecured_notices`, because a repeat group binds one list (forms.E007). It holds the notice parties of Part 1's debts first, in Part 1's line order, then Part 2's. Each row carries its parent's `part` ("1" or "2") and `line` ("2.n" or "4.n"). The `part` cell, a constant "2" today (`fill_resolver.py:370`), becomes the row's own, and the binding's choices become `{"1": "/Part 1", "2": "/yes"}` (the Part 1 tick's on-state is `Part#201`, `form_b106ef.index.json`; `build_claims_schedules.py:168-172` maps only Part 2 today).

**Builder's call B12, Schedule H.** A codebtor's E/F citations (`_codebtor_rows`, `claim_rows.py:144-158`) cite Part 1 lines before Part 2 lines, two to a box as 3c5 ruled (R6), each in the line's own words ("2.1", "4.3").

### 6.2 Schedule E/F

All of it is written by `data/forms/field_index/tools/build_claims_schedules.py`; change the tool, not the JSON (`test_the_claims_schedules_are_what_the_generator_writes`).

- **Line 1, `check1`** (Builder's call B13). A derived rule, `has_priority_debts`: Yes with any Part 1 row, No otherwise, as `check7` follows Part 2 (`derivations.py:921-924`). Today it is blank for every filer; after 3d2 a filer with no Part 1 row prints No.
- **Group `ef_part_1`.** `repeat` over `claims.priority[]`, capacity 5 (rows 2.1 and 2.2 on page 1, three rows on page 2), `extra_page` 2, `number` "2.{n}", `number_boxes` `{"3": "undefined_12", "4": "undefined_19@2:T30", "5": "undefined_19@2:T57"}` (rows 2 and 3 of page 2 share the name `undefined_19`, so they are tagged, as Schedule D's are, tool line 394). Rows 2.1 and 2.2 print their numbers already. Rows past 5 print on copies of page 2, three a copy, with the form's existing `page_numbers`. Its fix is `debts`, the fix E/F's other groups share (`test_group_fixes.py:34`). `backend/apps/forms/tests/conftest.py:64` already names the group's page-2 columns.
- **Part 1 columns.** Each row prints, by the same cells Part 2 uses: the creditor's name, last 4, address (with `outside_us`), date, contingent, unliquidated and disputed, who incurred it, community, and offset. New:

  - **Total claim** prints `amount_owed`;
  - **Priority amount** and **Nonpriority amount** print the filer's figures, blank where blank;
  - **the type tick** for the row's answer, one of the four boxes (`Domestic support obligations`, `Taxes and ceratin other debts you owe the government` (the template's spelling), `Claims for death or personal injury while intoxicated`, `Other`, with their `_2`…`_5` names);
  - **"Other. Specify"** prints `priority_other` beside the Other tick only.

  The "who incurred" boxes take each widget's own on-state, since page 2's rows spell "At least one of the debtors and another" three ways (`On`, `One#20of…`, lowercase); the tool's `choices_for` by option text already handles this. The three amounts join `CLAIM_MONEY_CELLS` so they print as money.

- **Part 2** lists `unsecured` only. `check7` and its rows are otherwise unchanged.
- **Part 4.** **Builder's call B13:** 6a–6d print the sum of the Total claim column over Part 1 rows of each type (6d for `other`), 6e their sum: page 6 heads the block "Total claims from Part 1" over a "Total claim" column, the name of Part 1's first amount column. So a claim with both amounts counts whole in 6a–6e and 106Sum 3a, and nowhere in 6j or 3b; that is the form's own arithmetic, and 122A-2 line 41a, which reads 3b, inherits it. Like 6f–6j today, each prints its sum, "0.00" with none. 6j becomes the Part 2 rows' total; **Builder's call B16:** 6f counts Part 2's student loans only, so a student loan the filer put in Part 1 leaves 6f; 6i stays 6j − 6f. 6g and 6h stay blank.

The rules behind 6f, 6i and 6j (`derivations.py:225-236,348-366`) read Part 2 through `claim_rows` (or the same split) instead of every unsecured debt, and their docstrings lose "priority is never asked". The new priority rules live beside them and link to `debts` (`derivations.py:1238-1240`).

### 6.3 Form 106Sum

- **3a** prints 6e; **3b** stays 6j (now Part 2 only); **3c** stays `total_debts`, every confirmed debt, so 3c = 2 + 3a + 3b keeps holding.
- **9a**, **9b** and **9c** print 6a, 6b and 6c; **9d** stays 6f.
- **Builder's call B14:** **9g** ("Total. Add lines 9a through 9f.") prints 9a + 9b + 9c + 9d, with 9e and 9f unasked, blank and counting as zero. It is blank today beside a printed 9d; once 9a–9c print, leaving it blank would leave the block's own total off.

### 6.4 The List of Creditors

`creditor_entries` (`fill_resolver.py:262-291`) reads the lists in the schedules' printed order: `secured`, `secured_notices`, `priority`, `unsecured`, `unsecured_notices`, `contracts`, `codebtors` (D Part 1, D Part 2, E/F Part 1, E/F Part 2, E/F Part 3, G, H). One entry per name and address stays the rule, so a creditor in both Parts prints once, at its Part 1 row.

### 6.5 Personas

The IRS rows join the seed and the journeys in 3d2 (B9):

- **Priya** (PS:659-663): Internal Revenue Service, Centralized Insolvency Operation, P.O. Box 7346, Philadelphia, PA 19101-7346 (PS marks the address VERIFY; the plan confirms it against the IRS's published bankruptcy address); $3,000; last 4 0003; incurred "tax year 2025"; no status flags; payment $200; answer `taxes`; priority $3,000, nonpriority blank; past due $3,000. Silverpine and Westhaven No; Kestrel is secured and not asked.
- **Andrés** (PS:1328, PS:1403): the IRS at the same address; $2,140; "tax year 2025"; `debt_type` other; `consumer_business_classification` "business"; answer `taxes`; split blank; past due $2,140. His toll debt stays "Not sure" (3d1).

Targets after 3d2:

| Persona | E/F Part 1                                  | 6b / 6e  | 6j                    | 106Sum 3a / 3b / 3c          | List of Creditors                      |
| ------- | ------------------------------------------- | -------- | --------------------- | ---------------------------- | -------------------------------------- |
| Priya   | 2.1 IRS: 3,000.00 / 3,000.00 / blank, Taxes | 3,000.00 | 57,000.00 (unchanged) | 3,000 / 57,000 / 74,900      | 6 → 7 (IRS second, after Kestrel)      |
| Andrés  | 2.1 IRS: 2,140.00 / blank / blank, Taxes    | 2,140.00 | 23,160.00 (unchanged) | 2,140 / 23,160 / 33,100      | 14 → 15 (IRS second, after Copperline) |
| Others  | none; line 1 No                             | 0.00     | unchanged             | 0.00 / unchanged / unchanged | unchanged                              |

Part 2's lines don't move for anyone (Andrés's toll debt stays 4.5, Ashgrove's Part 3 row still cites 4.2). Andrés's List of Creditors boxes all shift one place after Copperline, so his tier 3 rows for both pages change. The means test is unchanged for both (§2). The journeys add the IRS row through `addDebt` with its answers, and the packet count is unchanged.

### 6.6 Testing (3d2)

- **The invariant:** for every persona and a set of built sessions (a mix of types, No, Not sure, secured, drafts), each confirmed unsecured debt is in exactly one of `priority` and `unsecured`; 6e + 6j equals their totals; 3c = 2 + 3a + 3b.
- **Rows:** each Part numbered over its own rows alone (adding Part 1 rows leaves Part 2's numbers as they were; a debt moving from Part 2 to Part 1 renumbers only the Part 2 rows after it, and Part 3 and H cite the new numbers); a claim with both amounts prints once, in Part 1; Part 3's parts and lines; H's citation order; a draft never prints.
- **E/F:** the generator's byte test; tier 1's column map for `ef_part_1` and `_ROWS_BEFORE_THE_ADDITIONAL_PAGE` gaining `"ef_part_1": 2` (`test_oracle_tier1.py:595`); the page-2 number boxes (`test_number_boxes.py:84-85` already hand-pin "2.17" in `undefined_12` and both tagged `undefined_19` boxes); copies of page 2; the Part 3 Part 1 tick printing `/Part 1`; each type tick; "Other. Specify" only under Other; a split blank prints blank.
- **Tier 2:** the tool's own addendum rows in `step2_verification.json` for every new binding, and `ASSERTED_CASES` (1400, `test_oracle_tier2.py:37`) moved on purpose.
- **Tier 3:** Priya's and Andrés's E/F, 106Sum and List of Creditors rows (§6.5); every other persona's line 1 No and 6a–6e 0.00.
- **Tests that flip,** because they pinned "priority is never asked": `test_schedules_d_e_f_schema.py:7-10,72-91,122-127,147-153,515-520`, `test_form_106sum_schema.py:129-152`, `test_unconfirmed_scanned_debts.py:79-83,105`. Each keeps what it guards and moves its fixture to `priority_answer`.
- **Journeys:** all eight, with Priya's and Andrés's IRS rows.

## 7. Copy and counsel

- **Where words live.** The four type names, "Priority amount", "Nonpriority amount", "Other. Specify" and "Do not include current or ongoing priority claims" (122A-2 line 35) are the forms' printed words and go in `formText.ts`, which no reading-level test scores. Everything else is DigniFi's and goes in `copy.ts`: the legend "Is this amount owed one of these kinds?", the four definitions, "No, none of these", "Not sure", the "Not sure" note, the split help, the past-due label and help, and the gap sentences. Each must pass the reading-level test (grade 9 at most for five words or more) and the UPL tests.
- **Counsel `[C-2]`.** The definitions, the "Not sure" wording and its note ship marked `// DRAFT: counsel C-2`, as U:487 asks, and never block a merge. §5.2's sketch holds the drafts; the plan fixes their final wording against the tests. The rule that "Not sure" keeps a debt in Part 2 is the umbrella's (U:489), and counsel's review covers it too.
- **No advice.** No sentence tells the filer which type a debt is, that a type is better or worse, or what happens to a priority debt in the case. "Legal aid can help…" closes the sentences that point onward, the pattern `AMOUNT_HELP` and `CO_OWNED_NOTE` use.

## 8. Hand-offs to 3h

- **Line 35** (DIG-275): the sum of `past_due_amount` over confirmed, unsecured debts answered with one of `PRIORITY_TYPES`, divided by 60, inside the one calculator. Not "No", not "Not sure", not secured, not draft.
- **Line 41a** reads 106Sum 3b, which is Part 2 only after 3d2.
- **The deduction** `_get_priority_debts_monthly` (0 since 3d1) is replaced, and the result messages' "priority debts" words with it.
- **Columns** `is_priority` and `priority_classification` drop a release after 3d is live (B8), whichever PR comes then.

## 9. CLAUDE.md and docs

- **3d1:** the nested debts gotcha (the five fields save with the row; their 400s), the claims steps gotcha (the question, its three gaps, nothing pre-selected), the means test units gotcha (priority deduction is 0 until 3h), the seed order gotcha (pre-3d personas meet the priority gap; `--reset`), the document upload gotcha (a draft starts unanswered), and the autosave gotcha's step 6 body.
- **3d2:** "six lists" becomes seven wherever it is said (`claim_rows`, the List of Creditors, the claims gotcha), the List of Creditors' order, the blank-versus-zero gotcha (6a–6e, a blank split), and the forms notes that say Part 1 stays blank.

## 10. Left to the builder

- Exact names of the new rules, cells and test files, and whether `ChoiceGroup` is reused or extended for the definitions.
- How 6f–6j's rules read the Part 2 split (through `claim_rows` or the same filter), as long as one split decides both the rows and the totals.
- The final wording of every draft sentence, within §7.
- The task order inside each plan.

## 11. Builder's calls

| Call | Where | What                                                                                                                                                                                                                            |
| ---- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B1   | §5.1  | Five encrypted nullable columns on `DebtInfo`; the server stores what is sent, readers apply the conditions (stated to the owner 2026-11-11)                                                                                    |
| B2   | §5.1  | No data migration; every existing debt starts unanswered (stated to the owner 2026-11-11)                                                                                                                                       |
| B3   | §3 S2 | "Is this amount owed one of these kinds?" is DigniFi's legend (U:480's "Is this one of these?" made plain, after the copy review); the four options are the template's words; "No, none of these" and "Not sure" close the list |
| B4   | §5.2  | The question follows offset, unsecured only, nothing pre-selected; a secured Yes clears all five; leaving a type clears the figures and the "Other" text                                                                        |
| B5   | §5.3  | Past due required under a type, $0 allowed; split blanks allowed; no check against the total                                                                                                                                    |
| B6   | §5.1  | "Other" text required under Other, at most 100 characters                                                                                                                                                                       |
| B7   | §5.3  | Three gaps after offset, and their draft sentences                                                                                                                                                                              |
| B8   | §5.1  | `is_priority` and `priority_classification` retired in 3d1; columns drop a release after 3d is live                                                                                                                             |
| B9   | §4    | Persona IRS rows land in 3d2; 3d1's seed answers No and Andrés's toll Not sure                                                                                                                                                  |
| B10  | §6.1  | Part 3 keeps one list, Part 1's parties first; the `part` cell follows the parent                                                                                                                                               |
| B11  | §6.1  | `priority` is a seventh claims list                                                                                                                                                                                             |
| B12  | §6.1  | H cites Part 1 lines before Part 2's                                                                                                                                                                                            |
| B13  | §6.2  | 6a–6e sum the Total claim column, "0.00" with none; line 1 prints No with no Part 1 row                                                                                                                                         |
| B14  | §6.3  | 106Sum 9g prints 9a + 9b + 9c + 9d                                                                                                                                                                                              |
| B15  | §6.1  | No, Not sure and unanswered print in Part 2                                                                                                                                                                                     |
| B16  | §6.2  | 6f counts Part 2's student loans only                                                                                                                                                                                           |
| B17  | §5.1  | The answer keys `domestic_support`, `taxes`, `intoxicated`, `other`, `no`, `not_sure`                                                                                                                                           |
| B18  | §5.1  | The per-item `DebtViewSet` takes the five fields, as it takes `offset_answer`                                                                                                                                                   |
