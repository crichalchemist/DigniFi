# Forms step 3c: claims

- **Status:** drafted 2026-11-06. The owner answered one question on 2026-11-06 (§2). The spec waits for the owner's review. **The split into six PRs (§4) is proposed, not approved.**
- **Drawn from:** the step 3 umbrella spec, `docs/superpowers/specs/2026-10-16-forms-step3-design.md` §5.9 (cited `U:<line>`), its rules U §4.1–§4.7 and Appendix A's 3c rows. Persona targets come from `docs/superpowers/specs/2026-10-16-forms-step3-personas.md` (cited `PS:<line>`). `3e2:<line>` is `2026-11-01-forms-step3e2-design.md`. The forms' words come from the blank templates `form_b106d.pdf`, `form_b106ef.pdf`, `form_b106g.pdf` and `form_b106h.pdf` in `data/forms/pdfs/`.
- **Tree:** `feat/forms-step3c`, 478868d. Code citations were opened on this tree on 2026-11-06. No test suite ran for this spec. Engine results marked "run" come from direct calls on schema copies in the scope survey, not from `resolve_parts`, so real filers' output is unverified.
- **Not read:** the List of Creditors template (§10), the national instruction booklet's text on dates, LR 1007-1's text, and the owner's production session.
- **Tags** such as `[Q25]` trace to the umbrella's Appendix A. `[UPL]` is the rule that DigniFi gives information, never advice.

Inline "**Builder's call Bn:**" marks a choice this spec makes where the umbrella, the code and the owner leave one open. B1–B27 keep their scope-synthesis numbers. B28 onward are new here. §15 lists them all, so the owner can check them.

## 1. What 3c does, and why

Schedules D, E/F, G and H are the filer's sworn lists of who they owe and who else is on the hook. Today none of their rows print. The four schemas hold 16 bindings out of 858 index rows, and no form reads a contract or a codebtor beyond `.exists()` (`derivations.py:894-895`). A filer with nine creditors swears to a total with no creditor named. ILND also requires the names and addresses of all creditors with the petition, and DigniFi has no address for any of them (`DIG-123`).

After 3c:

1. **Every debt, contract and codebtor prints on its row**, on the official pages and copies of them, with its address `[Q25]`.
2. **The filer answers** status, secured or not, the lien's nature, who else is contacting them and which property secures a debt, with nothing pre-selected except "secured or not", which starts from the debt type and can be changed (U:77).
3. **A secured debt links to its property** `[Q13.link]`, so Schedule D Columns B and C and Schedule J's payment lines come from one source. Three duplicate typed sources retire.
4. **Co-owned collateral** prints Columns B and C blank, with a note, until counsel rules `[Q14]`.
5. **Every packet gains the List of Creditors** `[Q1.list]`.
6. **Debt, contract and codebtor columns are encrypted** `[Q7.claims]`, and debts are ordered in Python `[DIG-164]`.

Nothing in 3c deploys. Production waits for steps 3 to 5 and DIG-146.

**The failure this must not have.** A sworn schedule prints a row with a figure, a line number or an address the filer never gave, or a sworn Schedule J total falls without anyone saying so. Moving the car and mortgage payments is the sharpest case: done wrong, J 22a either double-counts or quietly loses $350 to $1,200 a month (§8).

### Goals

- Every box on D, E/F Parts 2 and 3, G and H that the filer can answer prints their answer, read off the printed page.
- Totals stay equal for every persona across the payment move, except where this spec corrects a target (§3.1).
- A filer can stop on a phone with nine creditors half-typed and lose at most what they typed in the last 2 seconds, the autosave's wait (`useAutoSave.ts:109`, with no save on `pagehide`).

### Non-goals

- E/F Part 1 and the priority split (3d). All unsecured debts print in Part 2 until then.
- 122A-2 lines 9b, 11, 13, 33 and 34 (3h). 3c stores what they read. Payments left is 3h's question (PS:677).
- Form 108 and Form 107 line 6 (step 4). 3c stores their inputs.
- Debtor 2's boxes, and joint filing.
- `AdversaryProceeding`'s plaintext copy of the creditor name (`dischargeability_service.py:54-55`), which U:88 leaves until step 5.
- Pre-filling addresses from a scan (U:444: "can come later").

### Anti-goals

- No "I don't know" on a debt's amount (§2).
- No way round a missing address (§2).
- No suggested answer. The app never proposes which property secures a debt, a lien's nature, a status or a figure (U §4.1).
- No moved figure. Old typed payments are never copied onto a debt (§12).
- No second printing path. Rows go on the official pages and copies of them (U §4.6).

## 2. What the owner decided

**Owner, 2026-11-06, on a filer who doesn't know a debt's amount: "no, they need the amount".** There is no "I don't know" on a debt, and the amount stays required. This is unlike 3b's asset values, and it rejects the survey's recommendation to reuse that answer.

- **A filer who cannot find a debt's amount cannot press Complete.**
- A debt marked contingent or unliquidated still needs a figure.
- A creditor owed nothing can't be a row, and so can't reach the List of Creditors.

**Builder's call B28:** "required" means today's rule stands: above $0. The owner's words don't state the bound; the step's rule does (`DebtsStep.tsx:88`). The rule moves to the server, because today only the browser holds it and the serializer accepts $0 and negatives (`serializers.py:558`):

- `amount_owed` gains `min_value=0` on the serializer and on a scanned bill's correction (`documents/views.py:233-235`), so a negative is a 400 on both.
- Complete refuses any debt, draft or confirmed, whose amount isn't above $0, in the Amounts Owed step's words: "Enter the amount you owe {name}. It must be above $0." A row with no name yet reads: "Enter the amount you owe on the row with no creditor name. It must be above $0."
- **A scanned $0 draft must be corrected before Complete.** A bill with a creditor and no readable balance is stored as a $0 draft (`draft_debt.py:35-36,58`), and this gap catches it, beside the existing draft sentence (`views.py:313-319`).

**Addresses are required with no way round.** U:444 and the owner's Q1 and Q25 settle it. **A filer who can't find an old creditor's address can't press Complete.** 3b gave values an "I don't know", and this gets none. The sentence is stated here so the owner sees it at review. B38's check takes any two letters and there is no country box, so a creditor abroad can be entered only by forcing two letters, which print as a state.

**Standing rules that bind.** The filer decides, and nothing is pre-selected (U §4.1). New filer data is encrypted (U §4.2). Information, never advice. Every refusal names the step or page that fixes it (U:127). Blank versus zero (U §4.5). Counsel items ship as draft comments and never block a merge (U:633). Security, encryption, UPL, IDOR and log-leak tests keep their assertions: a test that must change for a 3c field changes its fixture, never what it asserts.

**Open for the owner:** the split (§4), and O2, a Western Division filer's heading (§10.4).

## 3. Spec corrections

### 3.1 What the code and forms contradict in the umbrella and its companion

| #   | The spec says                                                                                                                                                  | The code or form says                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | Consequence                                                                                                                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S1  | "about 690 row boxes" (U:176, :628), no derivation given                                                                                                       | 749 row widgets, 741 drawn; without E/F Part 1, 616 widgets, 608 drawn (the 8 undrawn are D's stacked seconds)                                                                                                                                                                                                                                                                                                                                                                                                                          | Size only                                                                                                                                                                                                                    |
| S2  | §5.9 names no engine work                                                                                                                                      | D needs 2 continued groups, E/F 2 now and 3 in 3d. E007 refuses a second (`schema.py:532-544`). 3a2's spec hands 3c this limit (`2026-10-17-forms-step3a2-design.md:197`). Past the check, run: the drawing is right and the page numbers are wrong                                                                                                                                                                                                                                                                                     | 3c1                                                                                                                                                                                                                          |
| S3  | U:145: totals include every row, wherever printed                                                                                                              | D has per-page totals and one labelled "If this is the last page of your form". `_copies` writes neither (`fill_resolver.py:414-421`, `_headers` at :362-385), so copies print blank page totals and the last-page total prints before the copies                                                                                                                                                                                                                                                                                       | New mechanism, D only (3c1)                                                                                                                                                                                                  |
| S4  | U:127: every refusal names its step or page                                                                                                                    | A number box's `ValueTooLong` has no step and shows the index's internal label (`pdf_filler.py:154-173`). Run: G's row 10 is refused outright (`/MaxLen` 1), and D's "2.12" too                                                                                                                                                                                                                                                                                                                                                         | A filer with 10 contracts is refused by the blank form's own box (3c1)                                                                                                                                                       |
| S5  | U:457: the List is "an ordinary templated form"                                                                                                                | E001 is unchanged, as stated. But `test_widgets.py:68,74-75` pins widget counts, and `test_printed_page.py:830` and `test_attached_sheets.py:351` pin one `/Helv` encoding across all templates, which a court-made PDF may not share                                                                                                                                                                                                                                                                                                   | "Ordinary" is unproven until the template is read (§10)                                                                                                                                                                      |
| S6  | U:434: "Two duplicate sources retire"                                                                                                                          | A third: `other_property_mortgages`, owner answer 5 (3e2:269, :752, :794)                                                                                                                                                                                                                                                                                                                                                                                                                                                               | Retire it, derive J 20a (3c4)                                                                                                                                                                                                |
| S7  | U:434 states the retirement with no effect on totals                                                                                                           | `calculate_total_monthly_expenses` sums the fields behind J 22a, 22c, 23b, 23c, 106Sum 5 and 103B 6 (`models.py:628-631`, `derivations.py:253-261`). PS:704 and PS:1413 require those totals unchanged                                                                                                                                                                                                                                                                                                                                  | The total must add linked payments. Otherwise James −350, Priya −450, DeShawn −1,200, Andrés −389 (3c4)                                                                                                                      |
| S8  | The retirement doesn't mention the means test                                                                                                                  | The calculator stays live until 3h (U:169, :172). `except Exception` turns a dropped column into five zeros with no log (`expense_deduction_calculator.py:89-99`)                                                                                                                                                                                                                                                                                                                                                                       | Same PR (3c4). By hand, not run, Priya's verdict doesn't flip. A filer near the line could                                                                                                                                   |
| S9  | U:467: `DebtInfo.Meta.ordering` "at `models.py:547`" "moves to Python with them"                                                                               | It is at `models.py:903`. `-amount_owed` is already ciphertext, so the order is arbitrary today. `priority_classification` isn't on the encrypt list and disagrees by source (`DebtsStep.tsx:39`, `draft_debt.py:108`). No spec gives a key                                                                                                                                                                                                                                                                                             | The forms give the key (B5, 3c2)                                                                                                                                                                                             |
| S10 | U:150: "Every row keeps a stable id"                                                                                                                           | Only when the client sends a live id (`serializers.py:619-634`). Contracts and codebtors have no `_key`, no autosave and no pairing, and their reply is in id order (`views.py:67`)                                                                                                                                                                                                                                                                                                                                                     | 3b's list pattern first (3c2)                                                                                                                                                                                                |
| S11 | U:151: links are "codebtor to debt"                                                                                                                            | H's row has a "Schedule G, line" box and tick                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | The link must also reach a contract (B9)                                                                                                                                                                                     |
| S12 | U:446 asks offset of every row                                                                                                                                 | D has no offset box, only the lien tick "Other (including a right to offset)". E/F has "Is the claim subject to offset? No Yes". PS:416 holds an offset answer for a D row, while PS:881 lists none for one                                                                                                                                                                                                                                                                                                                             | Asked on unsecured rows only (B31). PS:416 changes                                                                                                                                                                           |
| S13 | U:432: a lease "gains a monthly payment and a 'vehicle' kind"                                                                                                  | G has no box for either, only the row's `Contact Info 2.n`                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | They feed J and Form 108, and never print as their own box                                                                                                                                                                   |
| S14 | Status list omits it                                                                                                                                           | E/F Part 2 needs a type tick per row (student, divorce, pension, other), and 6g and 6h are unbound. Nothing asks it. PS:424 assumes "Other. Specify: Credit card"                                                                                                                                                                                                                                                                                                                                                                       | B14, C9                                                                                                                                                                                                                      |
| S15 | PS:709: Priya 3a / 3b / 3c 3,000 / 57,000 / 60,000                                                                                                             | 3c is "2a + 3a + 3b", rule `total_debts` (`form_106sum.json:134`). PS:512 and PS:1414 add the secured debt                                                                                                                                                                                                                                                                                                                                                                                                                              | 71,900 from 3c3, 74,900 after 3d. `test_oracle_tier3.py:368` moves, and line 2's row is added                                                                                                                                |
| S16 | PS:422, :649 and others give dates in words                                                                                                                    | Run on D's 50 pt date box: "01/15/2024" fits at 9 pt, "Various 2019-2024" is refused. Run with `PDFFormFiller.check` on E/F's `Date debt was incurred_6` (64.7 pt) and `_7` (67.9 pt): "2019–2025" (PS:182), "2017–2025" (PS:886), "2016–2020" (PS:1089), "2024–2025", "tax year 2025" and "01/15/2024" fit. "11/2025 (son's ER visit)" (PS:183), "opened 06/2015, balance built 2023–2026" (PS:422) and "2024–2025 (most charged during the recovery)" (PS:649) are `ValueTooLong`. Slot boxes differ in width, and only these two ran | Shorten PS:183, :422 and :649 (B11). The plan checks each persona's date by pixels                                                                                                                                           |
| S17 | U:438: Priya's $450 "has no car or loan behind it"                                                                                                             | She has a car since 3b (`seed_demo_data.py:401`). The "no loan" half stands                                                                                                                                                                                                                                                                                                                                                                                                                                                             | Stale. The target (PS:648) still works                                                                                                                                                                                       |
| S18 | U:472 and DIG-281: save "on Go Back"; "Going Back … drops every unsaved edit"                                                                                  | Edits survive Go Back in the wizard's state (`ContractsStep.tsx:36,51-55`, `IntakeWizard.tsx:511-521`, `WizardLayout.tsx:166`; by reading, not run). They die on refresh, tab close or a link away                                                                                                                                                                                                                                                                                                                                      | The spec's fix misses the real loss (B3)                                                                                                                                                                                     |
| S19 | U:471: "three misleading texts"                                                                                                                                | The codebtor sentence went in #29. Two remain (`ContractsStep.tsx:141`, `DebtsStep.tsx:253`), plus the model's help_text (`models.py:798`)                                                                                                                                                                                                                                                                                                                                                                                              | Two texts, one help_text                                                                                                                                                                                                     |
| S20 | PS:1322: "E/F Part 2 is in alphabetical order"; PS:1418: the copy holds "Prairie Line, Ridgeway, Sablewood"                                                    | The creditors were renamed, so PS:1324-1336's order isn't alphabetical (Tallowfield before Northgate; Hollowmere after Prairie Line). Under B5: 4.1 Bright Signal, 4.2 Calumet Ridge, 4.3 Driveline, 4.4 Hollowmere, 4.5 Illinois Toll, 4.6 Northgate, 4.7 Prairie Line, 4.8 Sablewood, 4.9 Tallowfield                                                                                                                                                                                                                                 | The copy holds Prairie Line, Sablewood, Tallowfield. Ashgrove stays on 4.2 and offset on 4.7. PS:1397's "4.8 disputed" becomes 4.4, and PS:1402's "4.4 Not sure" becomes 4.5. Total 23,160 unchanged. Tier 3 uses this order |
| S21 | PS:891's retired list for DeShawn names the asset's `amount_owed` and `vehicle_payment`, not his rent                                                          | U:436 says his typed 1,200 (`seed_demo_data.py:478`) duplicates the mortgage's. Under B22, keeping it prints J 4 at 2,400, raises his J total by 1,200 and fires B23's Review sentence on a seeded persona                                                                                                                                                                                                                                                                                                                              | His `rent_or_mortgage` goes to 0 in 3c4 (§8.4)                                                                                                                                                                               |
| S22 | 3b's spec: "3c retires `amount_owed`", and "Dropping `asset_type` (one release later) and `amount_owed` (3c)" (`2026-11-05-forms-step3b-design.md:49`, `:271`) | 3c4 takes it off every reader. Its column stays one release, as 3b plans for `asset_type`'s, so a rollback finds it                                                                                                                                                                                                                                                                                                                                                                                                                     | The code retires in 3c4 and the column drops a release later (§8.4, §14)                                                                                                                                                     |

Also found, not contradictions: PS:1412's "or 15" hedge is answered by U:474. No persona seeds a contract or codebtor today. Three tests look up by `creditor_name=` and find nothing once it is encrypted (`test_dischargeability_service.py:50,96`, `test_data_migrations.py:126`, the last possibly at a pre-swap schema; not checked). The debts save filter deletes a nameless stored row (`IntakeWizard.tsx:410`), and the contracts and codebtors filters do the same (`:569`, `:574`).

### 3.2 The amount ruling against the targets

The companion and the umbrella were searched for a debt with an unknown, blank or $0 amount. **No target conflicts with §2.** Every persona debt row has a figure above $0. Each candidate, and why it isn't a conflict:

| Candidate                        | Where                                     | Why it stands                                                                                                                                                                                                        |
| -------------------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tollway toll debt, $380          | PS:1331, :1351, :1363, :1402; U:170, :489 | It has an amount. "Not sure" answers E/F Part 1's "Is this one of these?", not the amount. **That answer belongs to 3d**; in 3c it is an ordinary Part 2 row with $380. 3d's target inherits line 4.5, not 4.4 (S20) |
| IRS "split blank"                | PS:660-661, :1327, :1351, :1402           | The priority and nonpriority split, 3d's. The totals are given: Priya's $3,000, Andrés's $2,140. No 3d spec exists yet, so §14 asks it to keep the total required                                                    |
| Copperline $0                    | PS:1322, :1350, :1413, :1429              | A monthly payment, not an amount. B18 allows $0 there. The balance is $7,800                                                                                                                                         |
| Corolla $0/$0                    | PS:1311, :1353                            | An A/B row, ruled in 3b. Its Northlight contract carries no balance, since "owe money on this now?" is No (PS:1340)                                                                                                  |
| Column C = 0                     | PS:417, :511, :973                        | The form's arithmetic                                                                                                                                                                                                |
| Contingent or unliquidated rows  | PS:187, :416, :426, :881, :1091, :1397    | None. Every persona answers none                                                                                                                                                                                     |
| Sarah's possible "Not sure"      | PS:1226                                   | A 3d path on a $3,400 bill                                                                                                                                                                                           |
| Scanned $0 draft                 | `draft_debt.py:35-36`                     | The E2E bill reads $1,247.83 (`e2e/fixtures/fake-openai.ts:23`), so no journey meets one. A backend test covers it (§7.7)                                                                                            |
| Maria's Medicaid "unknown value" | PS:302                                    | Income assistance, not a debt                                                                                                                                                                                        |

The one sentence that reads against the ruling is a model help_text, `is_unliquidated`: "Amount not yet determined" (`models.py:866`). That column goes in 3c3 (B30).

**Survey material removed for §2:** the "I don't know the amount" answer, a Review list of debts with unknown amounts, a typed $0 on a debt, handling of a missing figure in the readers of `amount_owed`. **Unaffected, because neither is a debt's amount:** B18's $0 monthly payment, and B25's blank Columns B and C when an asset's value is unknown.

## 4. Six PRs (proposed)

U:176 allows 3c to split. 3b was one schedule with one model. 3c is four schedules, a new template, three tables' encryption, three reworked wizard steps, an engine change and a retirement that reaches about 27 test or spec files (by grep). The order comes from what must land first:

- Rows can't bind on D or E/F until the engine takes several continued groups.
- Rows that cite each other's line numbers (H, D Part 2, E/F Part 3) need one fixed debt order first.
- Nothing can link to a contract or codebtor row until those rows hold stable ids.
- The retirement must land as one change with its link, its total rule and its seed, or J 22a double-counts or under-reports in between.
- The List reads every other row, and its template isn't on disk.

| PR                              | Delivers on its own                                                                                                                                                                                                                                                                                                                                                                                  | Needs    |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| **3c1 Engine** (§5)             | Several continued groups on one form; pages numbered across them; D's page and last-page totals; number boxes that don't refuse a reachable row and never show an index label. Proven on synthetic schemas. No filer sees a change                                                                                                                                                                   | none     |
| **3c2 Row foundations** (§6)    | Encrypted columns; `ordered_debts`; contracts and codebtors held by the wizard, autosaved and paired; a cleared payment clears; the misleading texts. A real fix with no new question. DIG-164 and DIG-280 close. DIG-281 narrows: a refresh or tab close loses at most the last 2 seconds' typing, and typing while the step can't continue until 3c3 widens autosave, when the ticket closes (B47) | none     |
| **3c3 The questions** (§7)      | Addresses, status, secured, lien, notice parties, links, lease kind and payment, "owe money now", H line 2; Complete's gaps; Review; seeds and journeys. Answers are stored and refused when missing                                                                                                                                                                                                 | 3c2      |
| **3c4 Payments move** (§8)      | J 4, 5, 17a–17d and 20a from links; three columns retired; the total rule; the calculator re-sourced. Totals unchanged. DIG-282 closes                                                                                                                                                                                                                                                               | 3c3      |
| **3c5 Rows print** (§9)         | D Parts 1 and 2 with Columns B and C, E/F Parts 2 and 3, G and H, by a generator; oracle rows                                                                                                                                                                                                                                                                                                        | 3c1, 3c3 |
| **3c6 List of Creditors** (§10) | Template, index, schema, registry entry, heading, fixture text, packet counts. DIG-123 closes                                                                                                                                                                                                                                                                                                        | 3c5      |

**Builder's call B1:** split as above. Each PR gets the owner's yes as any spec call does, targets `develop`, and is squash-merged only with that yes. **No promotion of `develop` to `main` until 3c6 merges**, since 3c3 demands answers that print nowhere yet. Between 3c3 and 3c5, a seeded session's G and H also tick "Yes" with no row beneath it, because `has_executory_contracts` and `has_codebtors` start finding rows.

**Reasonable merges.** 3c1 into 3c5, though 3a2's history argues for its own review. 3c2 into 3c3, if the list pattern proves small. 3c4 and 3c5 can swap. Keep 3c6 apart: it alone carries about 16 count pins and an unread template.

**Gotchas `[GOTCHAS]`.** Each PR rewrites the CLAUDE.md gotchas its change touches, in the same PR. Each section below names them.

## 5. 3c1: the engine

**Delivers:** the four engine changes, proven on synthetic schemas as 3a2 was. **Needs:** nothing.

### 5.1 Several continued groups

`schema.py:532-544`'s limit goes. Its test `test_a_second_group_continued_on_copies_is_reported` (`test_checks.py:741`) becomes a test that a form takes several. Run on real names, tags and states, with the check bypassed, copies already land after their own page (`pdf_filler.py` tracks what it has shown), and the headers repeat. Each group alone validates today, including D's `check 5`, the stacked pairs and tagged names.

### 5.2 Page numbers

`_copies` (`fill_resolver.py:424-432`) numbers from its own group alone, so run on E/F with one copy each of pages 2, 4 and 5, it prints:

| Output page | Is         | Should print | Prints today |
| ----------- | ---------- | ------------ | ------------ |
| 3           | copy of p2 | 3 of 9       | 3 of 7       |
| 4           | p3         | 4 of 9       | 3 of 7       |
| 5           | p4         | 5 of 9       | 4 of 7       |
| 6           | copy of p4 | 6 of 9       | 5 of 7       |
| 7           | p5         | 7 of 9       | 5 of 7       |
| 8           | copy of p5 | 8 of 9       | 6 of 7       |
| 9           | p6         | 9 of 9       | 7 of 7       |

Numbering moves out of the per-group `_copies` to after the loop at `fill_resolver.py:609-621`. The total is the template's pages plus every group's copies. A page's position is its page number plus the copies of every group whose extra page comes before it.

**Builder's call B26 (first part):** page numbers are declared once per form in the schema, not on a group, since two groups can't declare them (`schema.py:333` keys `this` per group, and E006 fires), and one group declaring them numbers nothing when only the other overflows. They print only with copies, keeping today's pin (`test_continuation_copies.py:165`). Filed documents are untouched, because the numbers are stored in the parts.

### 5.3 D's totals

**Builder's call B26 (second part):** a group may declare per-page total boxes and a last-page box, each adding one column:

- Each page and each copy prints the sum of its own rows in its own total box: `undefined_9` on page 1, `undefined_23` on page 2 and on each copy of page 2.
- The last-page box, `undefined_24`, prints the grand total on the last page or copy only, including every row. It is the rule `total_secured_claims`'s figure as today.
- E/F has no page totals (seen on the rendered pages), so only D uses this. No filer sees it until 3c5.

### 5.4 Number boxes

Rows the form can reach are refused by the blank form's own boxes:

| Box                                                        | Holds         | First refused (run) |
| ---------------------------------------------------------- | ------------- | ------------------- |
| G `fill 2.6`–`2.13`                                        | `/MaxLen` 1   | row 10              |
| D, E/F `undefined_12` (15.6 pt)                            | "2.9" at 8 pt | row 12 ("2.12")     |
| D, E/F `undefined_19`, E/F `undefined_4.4`–`4.6` (16.9 pt) |               | row 100             |
| H `fill 3.x`                                               | `/MaxLen` 2   | row 100             |

**Builder's call B26 (third part):** a group's number box skips `/MaxLen` in the baked drawing, since nothing can type in a baked page. If a number still can't fit, the refusal is a plain sentence with its fix, never the index label. `_source` (`pdf_filler.py:154-173`) gains the group's fix and a label in plain words. Measure each box by pixels in 3c1, since `fit` saying it fits doesn't prove a glyph isn't clipped at 6.5 pt (3a2's lesson).

### 5.5 Testing

- E007: several continued groups pass, `page_numbers` at form level, a total box on no page is refused.
- E/F's table above becomes a pin on a synthetic schema with real names, read off the printed page with `read_drawn`. A second pin overflows only the group that doesn't come first.
- D: a copy prints its own page total; the grand total prints on the last copy and on no other page; a form with no copies prints it on page 2.
- G row 10 and D row 12 print, read off the page, with a pixel check for clipping. A forced refusal names its step and quotes no index label.
- A filed document with parts from before 3c1 redraws unchanged.
- **Pins that move:** `test_checks.py:741` (rewritten) and the synthetic fixtures declaring `page_numbers` on a group. **Don't move:** `ASSERTED_CASES`, tier 3, journeys.

**Gotcha:** "Schemas are checked at startup" (the one-group limit, `page_numbers`, totals).

## 6. 3c2: row foundations

**Delivers:** encryption, order, and the list pattern. No new question. **Needs:** nothing.

### 6.1 Encryption `[Q7.claims]`

- `DebtInfo`: `creditor_name`, `monthly_payment`, `notes`, `collateral_description`, `date_incurred`.
- `Codebtor`: `name`, `street_address`, `city`, `state`, `zip_code`, `relationship`. **Builder's call B9 (first part):** "every column" (U:464) excludes `session`.
- `ExecutoryContract`: `counterparty_name`, `description`.

The three-step migration has a precedent, `0032`–`0034`: add, copy in batches by pk with a reverse that refuses an unreadable row naming table and pk only, swap. No production code filters or sorts on these columns. The queryset `update()` at `documents/views.py:251` writes `creditor_name` with the same path `amount_owed` already takes; a test proves it stores ciphertext (not run so far). `monthly_payment` is declared on the serializer as `DecimalField(10, 2, min_value=0)`, as encrypted amounts are. Text fields declare their bounds there too, since the library's `deconstruct` drops `max_length`. A scanned bill's correction takes `creditor_name` with no check (`documents/views.py:228`), so it gains the same 255 limit, or undoing the migration could meet a value wider than the old column.

`DebtInfo.__str__` (`models.py:906`) quotes `creditor_name`, and from now on that is decrypted filer data. It changes to the row's pk and type, so no log line or admin list carries the name. `AdversaryProceeding` keeps its plaintext copy until step 5 (U:88); the spec says so here so it isn't taken for a miss.

**Builder's call B11 (first part):** `date_incurred` becomes encrypted text, because a `DateField` can't hold "2019–2025". It has no production writer or reader today, so the forward copy carries nothing but nulls in practice. Undoing the migration is different once 3c3 writes text: a value that isn't an ISO date returns as null and its text is lost, since saving it to the old `DateField` would stop the rollback with the filer's text in the error. U:446 asks that the type be checked against the national instructions: **not read yet**, and the plan reads them first.

### 6.2 Order `[DIG-164]`

**Builder's call B5:** `ordered_debts(rows)`, in a new pure module `apps/intake/claims.py` beside `asset_lines.py`, sorts the rows it is given: alphabetical by decrypted creditor name, ignoring case, then id. The session serializer passes every row, drafts included, so the wizard can show them. A form passes `.confirmed()`. D page 1 and E/F page 1 say "As much as possible, list the claims in alphabetical order according to the creditor's name", and E/F page 3 says "in the alphabetical order of the creditor who holds each claim". Line numbers are worked out at print from the confirmed list, the same for every form that cites them.

- `DebtInfo.Meta.ordering` (`models.py:903`) goes.
- The session serializer sorts its nested debts with `ordered_debts`, as it does assets. A PATCH reply stays in sent order.
- `DebtViewSet.get_queryset` (`views.py:719`) gains `.order_by("pk")`, as `AssetViewSet` has (`views.py:644`), since it paginates.

**Builder's call B37:** contracts and codebtors keep id order. G and H carry no alphabetical instruction (no such word in their template text), and PS:1340 lists G's rows out of alphabetical order.

### 6.3 The list pattern `[DIG-281]`

**Builder's call B3:** the 3b pattern, not a save on Go Back. It covers the real loss (S18), and stable ids need it anyway (S10).

- `ContractsStep` and `CodebtorsStep` become controlled (`rows`, `onRowsChange`), with `_key` from the step's counter, and `key={row._key}`. Debts' card moves from `key={index}` to `_key` too. Today a mounted step's `useState(initialData)` never receives ids (`ContractsStep.tsx:36`), so its next edit would send id-less rows, and the server would delete and recreate them.
- `currentStepBody` returns a body for steps 7 and 8. `useAutoSave` saves them through the PUT.
- `_save_list` replies in sent order, not id order (`views.py:67`), and `listSavesRef` gains `contracts` and `codebtors` (`IntakeWizard.tsx:155`), so pairing and "only the newest save writes ids" work as they do for assets.
- `_save_list` locks before it validates (`views.py:61-64`), since 3c3's validation reads rows.
- In 3c2, autosave runs on these steps only while the step can continue, as debts do (`IntakeWizard.tsx:443-444`). 3c3 widens it.
- A row with no id and no name stays out of the body (`IntakeWizard.tsx:569,574`). **A stored row never does,** since `_save_rows_by_id` deletes what the list leaves out (`serializers.py:633`). 3c2 changes each step's check so a row with an id and a cleared name is invalid. Today it is invalid only when other text is on the row (`ContractsStep.tsx:42`, `CodebtorsStep.tsx:48-51`). So neither autosave nor Continue sends it until the name is retyped or the row is removed, and its id stands. 3c3 replaces this rule (§7.3).

### 6.4 Fixes

- **A cleared payment clears.** Emptying the box leaves the key out (`DebtsStep.tsx:148-152`, `parseAmount.ts:14-16`, body at `IntakeWizard.tsx:409-411`), and the server keeps the old figure (`serializers.py:628`). The Debts body sends a blank `monthly_payment` as null, as Assets does (`IntakeWizard.tsx:396-400`). It matters once the debt's payment is J's only source.
- **`[DIG-280]` two texts and one help_text.** "car loan" leaves `ContractsStep.tsx:141`, "ABC Collections" leaves `DebtsStep.tsx:253`, and `models.py:798` stops saying "or collection agency". Rewording about collectors is draft under C7.
- Labels on both steps gain `htmlFor` (`ContractsStep.tsx:120,135`, and the same labels in `CodebtorsStep.tsx`).

### 6.5 Testing

- **Encryption:** raw SQL finds ciphertext in every listed column. Forward and reverse migration, and reverse refuses an unreadable row, naming table and pk only. Reverse returns a `date_incurred` of "Various 2019-2024" as null and an ISO date as that date. `update()` at the documents path stores ciphertext, and a `creditor_name` past 255 characters is a 400 there.
- **Order:** `ordered_debts` doesn't depend on ciphertext; a re-save keeps order; ties go by id; case and accents sort as letters.
- **Lists:** an autosave after two seconds on steps 7 and 8; a refresh after that save keeps edits; a second save updates rather than recreating rows (ids stable); clearing a stored row's name sends nothing, and retyping it keeps its id; a reply after a later save changes nothing; a reply of a different length fails the save; Go Back keeps edits.
- **Lock:** `test_session_lock.py` keeps its contracts and codebtors cases, and gains a validate-after-lock case.
- **IDOR:** another filer's id on these lists still creates a new row, as today.
- **Pins that move:** the three plaintext lookups in §3.1 (look up by a decrypted scan, keeping their assertions); `test_claude_md_asset_order.py:18` with the rewritten sentence; `test_session_nested_save.py:344` (`test_a_later_read_keeps_model_order_after_a_save_in_sent_order`); `documents/tests/test_draft_debt.py`'s `debts[0]` indexes (from `:187`); `test_list_saves.py`'s reply order; `IntakeWizard.test.tsx:3274`'s placeholder.
- Tier 2 and tier 3: no change. Journeys pass unchanged.

**Gotchas:** "Nested debts and assets save by id" (contracts and codebtors, debt order), "Autosave sends only real edits" (steps 7 and 8).

## 7. 3c3: the questions

**Delivers:** every answer stored, and refused when missing. Print paths don't change, except `has_*` ticks and totals as rows change. **Needs:** 3c2.

### 7.1 Records

New filer data is encrypted from the start (U:84).

**Builder's call B38:** addresses are columns (`street_address`, `street_2`, `city`, `state`, `zip_code`) on `DebtInfo` and `ExecutoryContract`, and `street_2` joins `Codebtor`, matching `Codebtor`'s and `DebtorInfo`'s names. Every shape holds the same address, unlike 3b's per-shape `details`. `state` is two letters, as `DebtorInfoSerializer`'s check asks (`serializers.py:84-88`), but that check runs at Complete and not on a row's save: a row saves a blank or a single letter, so a half-typed state in one row never refuses the whole list. A creditor abroad has no country box (§2). No persona has one, and it isn't asked here.

**`DebtInfo` gains:**

| Field               | Holds                                                                             | Why                                             |
| ------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------- |
| address columns     | as above                                                                          | D, E/F `[Q25]`                                  |
| `secured_by`        | nullable FK to `AssetInfo`, `SET_NULL`                                            | B7                                              |
| `home_payment_line` | `first`, `additional` or null                                                     | B8                                              |
| `collateral_who`    | `only_you`, `with_someone` or null                                                | B25: only on a shape whose A/B row has no `who` |
| `lien`              | JSON: `{kinds: [...], other: text}`, null unanswered                              | D's "Nature of lien. Check all that apply."     |
| `claim_status`      | JSON list of `contingent`, `unliquidated`, `disputed`; `[]` none; null unanswered | B30                                             |
| `offset_answer`     | `yes`, `no` or null                                                               | B31                                             |
| `community_debt`    | `yes` or blank                                                                    | B33                                             |
| `notice_parties`    | JSON list, `[]` no one, null unanswered                                           | B6                                              |

`is_contingent`, `is_unliquidated` and `is_disputed` go. They are `BooleanField(default=False)` (`models.py:859-872`), can't hold "unanswered", are off the serializer, and have no production writer or reader. `is_priority` stays for 3d.

**`ExecutoryContract` gains:** address columns; `lease_kind` (`residential`, `vehicle`, `other_personal_property`, `other`, or null); `monthly_payment`; `vehicle_asset` (nullable FK to `AssetInfo`, `SET_NULL`); `owes_now` (`yes`, `no` or null); `owed_debt` (nullable FK to `DebtInfo`, `SET_NULL`). The Form 108 flag `[Q1.108data]` is `lease_kind` in (`vehicle`, `other_personal_property`), stored for step 4.

**`Codebtor` gains:** `street_2` and `links`, JSON `[{kind: "debt"|"contract", id}]`.

**Builder's call B34:** nothing ships pre-selected. `contract_type` loses its `contract` default (`models.py:1030`), and old rows keep what they hold. `relationship` loses its `other` default (`models.py:1058`) and may stay blank, since H prints no relationship. The browser's own defaults go with them (`ContractsStep.tsx:27`, `CodebtorsStep.tsx:34`), or every new row still sends the old answer.

**Builder's call B35:** `ClaimAnswers`, one-to-one with the session (`related_name="claim_answers"`, table `claim_answers`), one encrypted JSON column, as `AssetLineAnswers`: `no_debts` (`true` when "I have no amounts owed" is pressed, null otherwise), `contracts_answer`, `codebtors_answer`, `community_lived` (H's `check2`), `community_spouse_lived_with` (H's `check3`), `community_state`, `community_spouse_name` and the spouse's address. A session PATCH or PUT carries `claim_answers`: only the keys sent change, null clears one, an unknown key or value is a 400. It locks and reopens as any intake-data write does.

**Builder's call B6:** notice parties are encrypted JSON on the debt row, with never-reused ids as `Household.members` has (`next_member_id`). Row: `id, name, street_address, street_2, city, state, zip_code, last_4`. No new table or endpoint, and they go with their debt.

**Builder's call B7:** one debt takes one asset, and several debts may share one. The link is scoped to the session in the save. **A foreign or stale id reads as no link, never a 400**, matching the row rule that a foreign id isn't an error, and the reply never echoes a foreign id. `CASCADE` would delete a debt on an Assets save, and `PROTECT` would raise out of a save with no handler, so `SET_NULL`. A secured debt with no link is a Complete gap in the Debts step's words.

**Builder's call B9 (second part):** `links` are ids in encrypted JSON, dropped on read when dead, because a Debts save can delete a row in a request that never touches codebtors. A codebtor left with none is a Complete gap.

**Builder's call B10:** `collateral_description` stays, as the typed D "describe the property" text, since D's middle slot is single-line and A/B rows have no one sentence. It keeps its box under the link and stays required on a secured row, as it is today (`DebtsStep.tsx:93-94`).

**Builder's call B12:** `account_last_4` is a read-only derived field, since `account_number` is write-only and a filer can't otherwise see what they typed. It holds the last four digits only, the same digits the forms print, for a typed or a scanned number. The rule that `account_number` stays write-only stands: `test_readable_amounts.py:83-87` keeps every assertion (no `ssn` or `account_number` key, the full number nowhere in the reply), and a new test proves no other digit of a stored number reaches the reply.

### 7.2 The Amounts Owed step

Each row, in order. The form's words go in `formText.ts`, DigniFi's in `copy.ts`.

- **Type, creditor, address.** The address is required (§2). Help, draft under C2: "The court uses this address to send the creditor notice of your case. A bill, a letter from the creditor or a credit report may show it. Legal aid can help you find it." The gap reads "Enter the street, city, two-letter state and ZIP for {name}.", or "… on the row with no creditor name." The trauma-informed guide lists a required field with no reason as an anti-pattern (`TRAUMA_INFORMED_DESIGN.md:199-200`).
- **Amount,** required and above $0 (§2). No "I don't know". Help, draft under C2: "A recent bill, a letter from the creditor or a credit report may show the amount. Legal aid can help you find it." Nothing tells the filer to estimate `[UPL]`.
- **Monthly payment.** **Builder's call B18:** on a secured debt it must be answered, $0 allowed, since it is now J's only source and Andrés's $0 is a real answer (PS:1350). Unsecured stays optional and never reaches J.
- **"Can the lender take back property…"** `[S3-SECURED]`, Yes or No. It starts from the debt type and can be changed (U:77), the one approved exception. Today there is no control (`DebtsStep.tsx:153-162`). **Builder's call B42:** a type change sets the answer only on a row whose answer the filer hasn't pressed since the row was added, and a loaded row counts as pressed, so the app never overwrites an answer the filer gave. The pressed mark is browser-only, like `_key`, and stays out of the request. **Builder's call B43:** a stored `is_secured` stands as the row's answer, with no nullable state or new gap. Its pre-fill is the approved exception (U:77), and every old row must be reopened for its address and status, where this answer shows beside them. The one change: a scanned draft counts as unpressed until the filer presses, so correcting a draft's type from `other` to `auto_loan` sets it to Yes.
- **Under Yes:** which property (the session's A/B rows that have an id, listed in their own words, none suggested), the lien's nature (the form's four kinds, "check all that apply", nothing ticked), and "describe the property" (B10).
- **Status** `[S3-STATUS]`. **Builder's call B30:** one question per row with the form's three ticks plus an unselected "None of these". null is unanswered, `[]` is "None of these", as the household list has it. D and E/F print "Check all that apply", so a row needs no Yes and No per word, which a filer with nine creditors on a phone would feel. Definitions are draft under C2.
- **Offset.** **Builder's call B31:** on unsecured rows only, in the form's words, No and Yes unselected (S12).
- **Date incurred and last 4.** **Builder's call B32:** optional, printing blank. The owner's rulings name addresses and amounts, not dates, and U §4.4 lets a filer leave blank what they may legitimately not know. **Builder's call B11 (second part):** the date is free text, bounded to what the box prints once measured. A value too long is `ValueTooLong` with `step: "debts"` anyway.
- **"Is anyone else contacting you about this debt?"** `[S3-NOTICE]` No or Yes, nothing selected. Yes opens name, address and last 4, with "Add another". Who counts as the creditor and who as the collector is draft under C7.
- **Community debt.** **Builder's call B33:** one tick in the form's words, unticked unless the filer ticks it, as A/B's community box.

**Builder's call B8:** "my home" is not a second link target. U:426's "or my home" is a line 1 row with a "Do you live here?" answer, `lives_here` (`yes`, `no` or null), asked on the Assets step under each line 1 and line 4 row (a home on wheels) and stored in that row's `details`. It can't be asked at the link, since `details` is replaced whole on an Assets save (`serializers.py:418`) and a Debts save carries no assets. The key joins `AssetDetailsSerializer` (`serializers.py:415-440`, which drops unknown keys) and the frontend's `AssetDetails`. No home concept exists today (a grep finds only form words). That answer separates J 4 and 5 from 20a (§8), so a debt linked to a row with no answer is a gap (§7.5). A debt linked to a row answered Yes asks whether it is a "first mortgage" or "additional, such as home equity", in the form's words: the filer's answer, never derived from order.

**Builder's call B25 (first part):** a debt linked to a row whose shape doesn't ask `who` (such as a line 6 item) asks "Only you" or "You and someone else" at the link.

**Builder's call B17:** "I have no amounts owed", unselected, as household and A/B do, so Remove works on the last row and Continue works with none. Today a filer with no debts can't Continue at all (`DebtsStep.tsx:108`, `:207`), though Complete doesn't require a debt.

**Builder's call B4:** Debts adopt Assets' autosave, so a half-filled row saves and Complete names the gap (`IntakeWizard.tsx:443-444` adds `debts`, and contracts and codebtors). New required fields are server-side gaps, with `assetGaps.ts`'s copy pattern as `debtGaps.ts`, `contractGaps.ts` and `codebtorGaps.ts`, whose sentences a backend test pins to the server's, and a `role="status"` region that stays mounted, since a sentence can quote a name while it is typed. Continue is disabled when a gap exists on the step, except the draft sentence (§7.5): `debtGaps.ts` leaves that one sentence out, and its pin exempts it, since only Continue can clear it.

**Draft confirmation moves off "any PATCH with `debts`"** (`views.py:193-196`), or autosave would confirm scanned rows nobody read. It moves to `update_step` with 7: only Continue sends that, since Go Back and Review's Go to move without `update_step` (`IntakeWizard.tsx:504-509`), and `update_step` already locks. A draft's edits save as drafts until then. The save carrying Continue's rows still comes first.

**Builder's call B29: a row with no amount yet stores 0, not null, and this is not an "I don't know" answer.** `amount_owed` stays non-null (`models.py:814`) and required on the serializer, and the wizard's body always sends it, a blank box as 0. A stored 0 means "not given yet", exactly what a scanned $0 draft already means. The box shows 0 as empty, loaded or typed, so a visit alone sends nothing, and the sentence says what's missing. No reader of `amount_owed` changes. The alternative, holding a row back from the save until it has an amount, would lose the typing and, because a stored row missing from the payload is deleted, can delete a row.

The body stops filtering on `creditor_name` (`IntakeWizard.tsx:410`), since a stored row left out is deleted. Only an all-blank row with no id stays out. The nested serializer allows a blank name and type, and Complete names them. `POST /debts/` (the per-item path) keeps requiring them, as `AssetViewSet` requires `ab_line`.

**Contracts and Codebtors save half-filled rows the same way.** `ExecutoryContractRowSerializer` and `CodebtorRowSerializer` (`serializers.py:1162-1175`) allow a blank `counterparty_name`, `name` and `contract_type`, and every new field is optional on the list save, since `_save_list` saves nothing when one row is bad (`views.py:56`, `:61-62`). The base serializers keep requiring the name and the type on the single POST. The name filters at `IntakeWizard.tsx:569` and `:574` go, and 3c2's invalid-row rule with them: only an all-blank row with no id stays out of the body. Complete names the gaps (§7.5).

### 7.3 The Contracts step

**Builder's call B13:** a Yes and No question first, in G's words, nothing selected, and Complete refuses unanswered. G line 1 is sworn, and an empty list prints a sworn "No" (DIG-281). This is 3b's "saying No" rule.

Each row: name, address, `contract_type` (nothing selected), what it is for (G's `Contact Info`, required), and:

**Builder's call B16:** a lease's kind is asked: residential, vehicle, other personal property, other. A vehicle lease picks its A/B row (Complete gap) and asks a monthly payment. The picker leaves out a row answered "I live here", so §8.1's mapping never meets a lease on a home. Payment is asked on a vehicle lease only. G has no box for either (S13). PS:194's rent stays in the words.

**Builder's call B15:** "Do you owe money on this now?" `[S3-GCLAIM]`, draft under C3. Yes picks an existing debt row from a list, none suggested, so nothing is listed twice. If it isn't there, the question says to add it on Amounts Owed and links there. The filer adds it, gives the amount (§2), presses Continue to return, and picks it. No pre-filled row, no remembered trip and no new save path; a Yes with no pick is §7.5's gap, so an abandoned trip loses nothing. Every persona answers No.

**Builder's call B44:** a vehicle lease whose `owed_debt` is a secured debt linked to the same A/B row is a Contracts gap: "Your lease with {name} and your debt to {debt} are on the same vehicle, and each has a monthly payment above $0. Enter the monthly payment once, on either row, and $0 on the other." Each payment prints from its own row and J adds them, so this keeps the amount counted once without DigniFi choosing which figure is right. No persona has this.

### 7.4 The Codebtors step

**B13 again:** a Yes and No question in H's words, nothing selected. H line 2's community-property answers are asked too (PS:433, :890), `[S3-H]` on the same page, in the form's order: lived in a community state; under Yes, "Did your spouse, former spouse, or legal equivalent live with you at the time?"; under its Yes, the state and that person's name and address.

Each row: name, address, relationship (optional, nothing selected), and which debts and contracts it shares, chosen from a list of the filer's rows by name, none suggested. A linked D or E/F row ticks "At least one of the debtors and another" (§9).

Address: required on every codebtor (U:444). Today's is optional (`CodebtorsStep.tsx:45-56`).

### 7.5 What Complete refuses

`claim_step_gaps(session)` in `apps/intake/claims.py` returns the gaps in order, after `asset_step_gaps` (`views.py:309`), as the wizard's order is. Each row is named by its name, or "one amount owed", "one contract", "one codebtor", and a sentence that reads "you owe {name}" or "for {name}" has its own wording for a row with no name (§2, §7.2). A state counts as missing unless it is two letters.

**Assets,** `step: "assets"`, first: a debt linked to a line 1 or line 4 row whose `lives_here` is null, naming the row (`_row_name`): "Answer 'Do you live here?' for {row} on line {line} of the Assets step." It is on no Debts copy, so it never disables Continue there. Review and the forms calls name it, with their link to the Assets step.

**Debts,** `step: "debts"`, the existing draft sentence (`views.py:313-319`) first:

1. No debt rows and `no_debts` null; `no_debts` true with rows.
2. Per row, drafts included: no creditor name; no type; **an amount not above $0**; a missing street, city, state or ZIP.
3. A secured row: no link, or a dead one; no property description; no lien kind, or Other with no text; payment unanswered; a link to a row answered "I live here" with no `home_payment_line`; a link to a shape with no `who` and no `collateral_who`.
4. Status unanswered. An unsecured row's offset unanswered.
5. "Anyone else contacting you" unanswered; a notice party missing a name or any address part.

**Contracts,** `step: "contracts"`: the question unanswered; Yes with no row; No with rows. Per row: no name, address, type or purpose; a lease with no kind; a vehicle lease with no A/B row or no payment; `owes_now` unanswered; Yes with no live debt; B44's same-vehicle overlap.

**Codebtors,** `step: "codebtors"`: the question unanswered; Yes with no row; No with rows; H line 2 unanswered; `community_lived` Yes with `community_spouse_lived_with` unanswered; that answer Yes with no state, spouse name or address. Per row: no name or address; no live link.

**Forms.** **Builder's call B36:** the same function guards the forms calls, as 3b's does. `_prepare` raises the first `ClaimStepGap` after `AssetStepGap` (`forms/views.py:215-217`) and before the means test, a 422 of the whole call carrying its step, for Generate, Generate All, Regenerate and an unfiled download. The packet list doesn't refuse, and a filed form's stored download is unchanged. A session completed before 3c therefore can't print rows with no address.

**Completion percentage.** Debts count as done when no debt gap remains, not when a row exists (`views.py:622`), since a filer with no debts has finished. Contracts and codebtors aren't sections (`views.py:612`, `:614-623` count five) and 3c adds none, so only that test changes.

### 7.6 Words and Review

- `formText.ts` holds the form's words, and `copy.ts` DigniFi's, with `// DRAFT: counsel C-n` above each draft sentence. Filers see no mark (3b §6.3). **Builder's call B2:** new counsel numbers run from C-16.
- New `upl-*-copy` test lists hold every new sentence. None predicts an outcome or suggests a value.
- Review lists debts, contracts and codebtors in words, not enum values (today `ReviewStep.tsx:411` shows `auto_loan`, and `:430` shows `lease` or `contract`), in `ordered_debts`' order. Go to buttons need no change, since `debts`, `contracts` and `codebtors` are `WIZARD_STEPS` keys.
- **`[UPL]` notes:** at a link to a co-owned row, "Which value applies is something legal aid can help you decide." Draft, C1.
- **On a phone:** Andrés enters ten debts with addresses between rides. One column, full-size targets, numeric keypad for amounts. Autosave lands 2 seconds after typing stops, so leaving keeps the work except what was typed in those last seconds.

**Builder's call B14 (first part):** E/F's type isn't asked as its own question in 3c. See §9.

### 7.7 Testing

- **Backend:** one test per gap in §7.5. **`a_debt_with_no_amount_above_zero_blocks_complete`**, confirmed and draft. **`a_scanned_zero_balance_must_be_corrected_before_complete`**: a $0 draft, then a typed figure, then Continue, and Complete passes. A negative is a 400, on the serializer and on a scanned bill's correction. A half-filled row saves with 0 and prints nowhere. A row whose state holds "I" or nothing, among others, saves the whole list, and Complete names it. A contract or codebtor row with an address and no name saves, and clearing a stored row's name keeps its id; Complete names both. A debt linked to a line 1 or line 4 row with `lives_here` null is refused (`a_home_mortgage_never_reaches_line_20a_unasked`). Every new column holds ciphertext. `update_step` 7 confirms drafts, and an autosaved PATCH with `debts` doesn't.
- **IDOR:** a foreign asset id on `secured_by` or `vehicle_asset`, a foreign debt id on `owed_debt` or a codebtor's `links` links nothing and is never echoed. A stale id reads as no link, and Complete names it.
- **Lock:** `test_session_lock.py`'s `WRITES` gains `claim_answers`, the debts PATCH with links, and the `update_step` confirmation. It runs under `postgres` only.
- **Log leak:** a gap names a creditor in the reply only. No logger call carries a creditor name, address or last 4. `__str__` carries none.
- **Frontend (vitest):** Continue disabled until the step's gaps clear; the amount box shows 0 as empty; a visit alone sends nothing; "None of these" and a tick are exclusive; a pick of a property leaves the others unselected; nothing pre-selected on any radio or select; a type change leaves a pressed secured answer alone and sets an unpressed one (B42); a scanned draft with no other gap can press Continue; axe on each step.
- **`debtGaps.ts`** sentences are pinned to the server's as `test_asset_gaps.py` does, all but the draft sentence.
- **Copies pinned:** `DEBT_TYPE_CHOICES`, `CONTRACT_TYPE_CHOICES` and `RELATIONSHIP_CHOICES` against their frontend copies, which have no pin today. `test_asset_lines_frontend_copy.py` pins `AssetDetails` with `lives_here`.
- **Builders:** `answer_household` (`apps/intake/tests/builders.py`) by default sets `no_debts` true on a session with no debt rows, and answers contracts, codebtors and H line 2 No; `claims=None` leaves them. A new `complete_debt(session, **over)` gives a row every answer.
- **Pins that move:**
  - Every test that presses Complete or a forms call with a debt, contract or codebtor. `DebtInfo.objects.create` is in 23 non-migration files and contract or codebtor creates in 2. How many reach Complete was not counted, and the plan counts them.
  - `test_api_readback.py:121-124` (`backend/apps/forms/tests/`), "No persona has contracts or codebtors", must send rows, with link ids resolved at send time, since persona dicts hold no ids.
  - `test_oracle_tier3.py:368`: Priya's 3c 57,000 → 71,900, and line 2 14,900 is added (S15), when her Kestrel row seeds.
  - Draft confirmation: `intake/tests/test_views.py:33` (`test_debts_patch_clears_is_draft`), `test_session_nested_save.py:303`, and `test_completion.py:787` assert that a PATCH with `debts` confirms drafts. Each moves to `update_step` 7, keeping what it proves: a draft leaves draft state only when the filer confirms. `test_unconfirmed_scanned_debts.py` keeps its assertions.
  - `test_models.py:79-86` (`backend/apps/intake/tests/`) creates a debt with the three dropped status columns and asserts them. The test goes with the columns.
- **Seed:** each persona's target, seed, fixture and brief change together. No persona seeds a contract or codebtor today.

| Persona | 3c3 target                                                                                                                            | List count |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Maria   | PS:182-198: addresses, 2 notice parties, G lease $1,100, no codebtors                                                                 | 6          |
| James   | PS:408-435: Crestway linked to A/B 3.1, G lease, no codebtors. **PS:416's offset answer on a D row drops (S12)**                      | 3          |
| Priya   | PS:646-655: new Kestrel $14,900, $450, linked to A/B 3.1; codebtor Rohan on Westhaven; Lakeshore; G lease $2,800                      | 6          |
| DeShawn | PS:873-892: Harrowgate linked to A/B 1.1, answered "I live here" and first mortgage; 2 notice parties; G and H none, each answered No | 6          |
| Sarah   | PS:1088-1105: addresses, 1 notice party, G lease $850, H No. No link                                                                  | 4          |
| Andrés  | PS:1396-1400: Copperline linked to A/B 3.2, $0 payment; Ashgrove; codebtor Mateo; G 2.1 vehicle, $389, A/B 3.1; G 2.2; lines per S20  | 14         |

Seeded before 3c, personas are refused until `seed_demo_data --reset`. The seed creates assets, then debts, so links resolve in that order, and contracts and codebtors follow.

- **E2E:** `addDebt` (`wizard.page.ts:403-424`) gains address, status, secured, link, first-or-additional, lien and notice inputs. DeShawn's journey answers `line_1_0_lives_here` on the Assets step. `debt_type_<i>`, `creditor_name_<i>`, `amount_owed_<i>`, `monthly_payment_<i>` and `collateral_description_<i>` keep their names. Every journey fills steps 7 and 8 or answers No. Andrés's journey enters ten debts. `sofa-journey` follows James, and `scanned-bill-journey` follows `SARAH`, whose draft needs its address and answers before Continue.

**Gotchas:** "Nested debts and assets save by id", "Forms need a completed intake", "Autosave sends only real edits", "Seed order", "Document upload sits mid-wizard" (a draft confirms on Continue, not on any PATCH), "The Assets step asks Schedule A/B's lines" (`lives_here`), plus a new gotcha for `claims.py`, and the File Map.

## 8. 3c4: payments move

**Delivers:** one source for each payment, with totals unchanged. DIG-282 closes. **Needs:** 3c3. All of this lands as one PR, so no state between PRs exists where J double-counts or under-reports. One double count can remain inside an old session: a typed line 4 beside a linked first mortgage, which only a Review sentence names (§12).

### 8.1 The mapping `[Q13.link]` `[CORR.J45]`

A helper in `claims.py` returns what each line prints, in dollars, from confirmed debts and vehicle leases. The table reads top down, and a payment takes the first row that matches:

| What it is linked to                                                                                       | Prints on                                   |
| ---------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| A row answered "I live here", `first`                                                                      | J 4, added to typed rent or lot rent        |
| A row answered "I live here", `additional`                                                                 | J 5                                         |
| A line 1 row answered No to "Do you live here?"                                                            | J 20a                                       |
| The first A/B vehicle row (lines 3, then 4, in `ordered_assets`, leaving out a row answered "I live here") | J 17a                                       |
| The second                                                                                                 | J 17b                                       |
| A further vehicle, or a secured debt on any other property                                                 | J 17c, then 17d, each with its Specify text |
| Nothing (unsecured)                                                                                        | No J line (PS:649)                          |

- **Builder's call B19:** "Vehicle n" on J 17 is the nth A/B vehicle row. Each debt or lease on it adds up there. So 17a is Andrés's lease, on A/B 3.1, and 17b is blank for his Fit, on 3.2, at $0 (PS:1413). The template's own text puts 17a under "Installment or lease payments:", so a lease on 17a is the form's reading. Past 17d, further payments add to 17d, with words saying so, and totals include them. A line 4 row answered "I live here" goes to J 4 or 5 only and takes no Vehicle n slot: with a car on 3.1, a lived-in motor home on 4.1 and an ATV on 4.2, the car is 17a and the ATV 17b.
- **Builder's call B45:** on 17c and 17d, further vehicles come first, then other property, each in `ordered_assets`' order, and debts on one asset share a slot, added together. The Specify text is fixed words, never the filer's row text, so the filer never meets a too-long refusal for words they didn't type here: "Vehicle 3", "Vehicle 4", or "Payment on other property". Payments past 17d add to 17d, which then reads "Other secured payments". The plan measures these on the box by pixels.
- **Builder's call B22:** line 4 is typed rent or lot rent plus a linked first mortgage, because the form says "Include first mortgage payments and any rent for the ground or lot" (`formText.ts:122-123`). The step's help words change from "Monthly rent or mortgage payment" (`ExpenseInfoStep.tsx:44`).
- A $0 payment prints blank on J, under the existing rule that a Schedule J line prints only above $0.
- **Rule names:** `schedule_j_vehicle_payment` (`derivations.py:980`), `schedule_j_rent_or_mortgage` and `schedule_j_other_property_mortgages` (`derivations.py:1001`, J 20a) keep their names, so tier 2's keys stand. Only what they read changes. New rules cover 5, 17b, 17c, 17d, `Other 17c` and `Other 17d`. Refusals from these rules go to `debts` (today `derivations.py:1129,1138,1153` say `expense_info`).

### 8.2 The total

**Builder's call B20:** a new `total_monthly_expenses(session)` adds typed lines and linked payments, behind the six printed boxes (J 22a, 22c, 23b, 23c, 106Sum 5, 103B 6), through `_total_monthly_expenses` (`derivations.py:253-261`). `ExpenseInfo.calculate_total_monthly_expenses` (`models.py:628-631`) stays the typed sum. No `ExpenseInfo` row stays the one 0.00 exception. `test_seed_demo_data.py:235-236`'s `EXPENSE_TOTAL` moves to the new function.

**Builder's call B24:** the Expenses step's on-screen total stays typed-only (`ExpenseInfoStep.tsx:69`), since step 4 comes before those rows (`wizardSteps.ts:9-12`), with one sentence that car and mortgage payments are added from Amounts Owed and Contracts & Leases.

Review is step 9, after those rows, so it shows the figure the forms print. `ReviewStep.tsx:312`'s "Rent / Mortgage" becomes "Rent or lot rent" and still reads the typed box. `:318`'s total becomes three lines: the typed total, "Payments on property linked on Amounts Owed and Contracts & Leases", and their sum, which J 22a prints. The middle line adds the wizard's own rows, every secured debt with a link and every vehicle lease, since those are the payments §8.1 prints, and the wizard's rows are newer than its last session read. `expense_info.total_monthly_expenses` stays typed, and no step body changes. A scanned draft counts on Review, and Complete refuses while one remains. Tests pin James at 2,860 + 350 = 3,210 and DeShawn at 1,210 + 1,200 = 2,410, with "Rent or lot rent" $0.00.

### 8.3 The calculator

**Builder's call B21:** `ExpenseDeductionCalculator` reads the same helpers for `housing` (J 4 and 5) and `transport` (J 17) and the new total, in the same commit. Its catch-all (`expense_deduction_calculator.py:98-99`) stays until DIG-152, per 3h, so a test proves food and health survive: dropping `vehicle_payment` without this would zero all five figures with no log. Priya's verdict doesn't flip, by hand, not run: about $3,464 allowed against CMI 13,800.

### 8.4 What retires

- `ExpenseInfo.vehicle_payment` (`models.py:509`) and `other_property_mortgages` leave `AMOUNT_FIELDS` (26 → 24), the frontend's interface and `EXPENSE_FIELDS` (`types/api.ts:311`, `:314`, `:356`, `:359`), the step (`ExpenseInfoStep.tsx:47`, `:239`, `:246`) and `formText.ts:159`, `:166`. J 20a's binding reads the helper.
- `AssetInfo.amount_owed` (`models.py:686`) leaves the serializer, the seed's `owed=`, and the wizard's hydration, and `types/api.ts:451`'s comment goes. It is unread (U:434), so no form changes.
- The two expense columns stay, read by the legacy gap only (§12). `AssetInfo.amount_owed`'s column stays, read by nothing (S22). All three drop a release after this code is live.

**Seed, fixture, brief, in this PR:** James's 350 goes, Priya's 450 goes (DIG-282), Andrés's 389 goes (`seed_demo_data.py:702`), DeShawn's typed 1,200 goes to 0 (S21), asset `owed=` goes. `personas.ts` drops `vehicle_payment` from all six, since `fillExpenses` types every key it holds, and DeShawn's `rent_or_mortgage` (`personas.ts:586`) goes to 0, or his journey's packet prints J 4 at 2,400.

### 8.5 Testing

- **Named for the outcome:** `a_linked_payment_is_counted_once`, `moving_a_car_payment_leaves_every_total_unchanged`, `a_co_signed_loan_at_zero_leaves_its_line_blank`, `unsecured_payments_never_reach_schedule_j`, `food_and_health_survive_the_payment_move`, `a_lived_in_motor_home_is_counted_once_and_takes_no_vehicle_line`.
- **Addendum rows** in `audit/step2_verification.json`, in the same commit: J 5, 17b, 17c, 17d, `Other 17c`, `Other 17d`, citing the box's index label and this spec's owner answer. `ASSERTED_CASES` (`test_oracle_tier2.py:37`, 831) rises on purpose.
- **Tier 3 (hand-checked):**

| Persona                            | Row                                                         |
| ---------------------------------- | ----------------------------------------------------------- |
| James                              | 17a 350 (new row)                                           |
| Priya                              | 17a 450 (new row)                                           |
| DeShawn                            | 4 1,200 (new row); 5 blank; 20a blank                       |
| Andrés                             | 17a 389 (unchanged, source moves, `:724`); 17b blank (new)  |
| Maria, James, Priya, Sarah, Andrés | 4 at their typed rent (new rows; no persona pins J 4 today) |

The 24 rows J 22a, 22c, 23b, 23c and 6 rows 106Sum 5 **do not move**. If they do, the total rule is wrong: 16 J rows and 4 106Sum rows fail otherwise.

- **Pins that move:**
  - `test_schedule_j_schema.py:93` `VACATED` drops `17b` and `17c`.
  - `test_schedule_j_schema.py:72` ("the one car payment the Expenses step asks"), `:83` (20a), and the powers-of-two fixture and comment at `:94`.
  - `IntakeWizard.test.tsx:2991-3027` (step 4's whole body), `ExpenseInfoStep.test.tsx`, `test/fixtures/session.ts`.
  - `test_expense_field_names.py`, `test_expense_encryption.py`, `test_expense_lines_storage.py`, `test_form_106sum_schema.py`, `test_form_122a2_schema.py`, `test_means_test_calculator.py`, `test_expense_deduction_calculator.py` (fixture; its `:47-51` food assertion stays), `test_e2e_intake.py`, `test_data_migrations.py` if a column's state moves.
  - `test_readable_amounts.py:82` is deleted. It pins that a field 3c retires can be read, not a security property, so §2's standing rule doesn't cover it. `:83-87` stay.
  - `ReviewStep.tsx:312`, `:318` and their tests (§8.2).
  - About 27 test or spec files by grep, of which 13 backend files name the two fields 36 times. A rent-only mention stays, since renters keep typing.
- **Journeys:** all six fill Expenses without the car box, and Generate All passes. No journey reads a J box (`deshawn-assets.spec.ts` asserts the preview and the packet count), and tier 3 reads the seed, so nothing proves the totals on a journey's own session. That is why `personas.ts:586` is named above.

**Gotchas:** "Expense names are the backend's" (24 amounts), "Debt and asset amounts are readable", "Blank, not 0.00" (the 26 amounts and the one function behind the totals), "Means test units" if its wording touches.

## 9. 3c5: rows print

**Delivers:** D, E/F Parts 2 and 3, G and H print their rows, with Columns B and C. **Needs:** 3c1, 3c3.

### 9.1 Groups

| Group       | Slots        | Extra page | Rows per copy |
| ----------- | ------------ | ---------- | ------------- |
| `d_part_1`  | p1: 2, p2: 3 | 2          | 3             |
| `d_part_2`  | p3: 6        | 3          | 6             |
| `ef_part_2` | p3: 3, p4: 3 | 4          | 3             |
| `ef_part_3` | p5: 7        | 5          | 7             |
| `g`         | p1: 5, p2: 8 | 2          | 8             |
| `h`         | p1: 3, p2: 8 | 2          | 8             |

E/F Part 1 (`ef_part_1`, 133 widgets) goes in 3d, on top of this. Bound: 608 drawn row widgets, plus the unbound page-number boxes these rows need. The filer's own `Case number` stays blank, as on every form today, since nothing supplies it.

Rows read a new namespace, `claims.<list>[].<attr>`, where the list is `secured`, `secured_notices`, `unsecured`, `unsecured_notices`, `contracts` or `codebtors`, through a `CLAIM_CELLS` table in `fill_resolver.py`, as `ASSET_CELLS` does. It goes in `_BINDING_NAMESPACES` (`schema.py:223`), `resolve_binding` (raises on unknown, `fill_resolver.py:233`) and `binding_fix` (`:284-299`), which sends each list to `debts`, `contracts` or `codebtors`. Readers go through `.confirmed()` and one read per form, as `one_read_of_assets` does.

### 9.2 Generator

**Builder's call B26 (fourth part):** a tool, `data/forms/field_index/tools/build_claims_schedules.py`, writes the four schemas' rows and their addendum rows, as `build_schedule_a_b.py` does. Change the tool, not the JSON. Who-owes states are read from the template, because they differ row to row:

- D: `check 2` and `check 4` have named states, `check 3` the same with a lower-case `/debtor 1 and 2`, `check 5` has four `/On` widgets, needing four tagged bindings, and row 3 of page 2 has four separate names.
- E/F: `check 4`, `6`, `7`, `9`, `10` and `11` end in `/On`, and `check 5` and `8` in lower case.
- E/F's `check N` is who-owes and `checkN` is offset, and they aren't the same row.
- `D account number` and `undefined_19` need tags (`tests/conftest.py:177-178`). D's stacked pairs bind the first widget only.

### 9.3 Row contents

- **Numbers.** D's entry box takes the whole "2.n", G's only "n" after a printed "2.", H's only "n" after "3." (seen on a rendered crop). A preprinted row's number needs no box.
- **Addresses.** **Builder's call B26 (fifth part):** where a row has no second line (E/F Part 2, G, H), `street_2` joins the street with a comma. A value too long is `ValueTooLong` with its step.
- **Who owes.** A linked codebtor gives "At least one of the debtors and another" (PS:1398). Otherwise "Debtor 1 only". "Debtor 2 only" and "Debtor 1 and Debtor 2 only" are never ticked.
- **Lien, status, community and offset ticks** print the filer's answers. An answer not given can't reach here past §7.5's gaps.
- **Column A** is the amount, always above $0 on a completed intake (§2).
- **Line citations.** D Part 2's "On which line in Part 1" and E/F Part 3's "Line \_\_\_\_ of", with its Part tick, print the debt's line from `ordered_debts` over the confirmed rows. `check14`–`check20`'s `/yes` state is the Part 2 box, the only one used until 3d. H's "Schedule D, line", "Schedule E/F, line" and "Schedule G, line" print the linked rows' lines, with the tick.
- **H with many links.** **Builder's call B40:** run, "2.1, 2.3" fits at 10 pt and four wrapped lines are refused. A codebtor whose links don't fit one row's box prints further rows with the same name and address. The plan measures how many fit.
- **E/F's type.** **Builder's call B14:** Student loans from the filer's own `debt_type`. The rest tick "Other. Specify" with the type's words, such as "Credit card" (PS:424). Divorce and pension aren't asked until C9 reads, and 6g and 6h stay blank until then.
- **G's row** prints the name, the address and what it's for. The lease's rent stays in the words (PS:194). `fill 2.6`'s template default stays. **Builder's call B41:** a filer with 5 or fewer contracts prints the court's own "2.2" on a blank row, since `read_drawn` reads it as blank and the blank form says it too. D Part 2's unnumbered entry box stays blank, since the form has no instruction for it.
- **G and H lines 1 and 2** print the answers (`check1` from the row list and `claim_answers`, which Complete guarantees agree). H line 2 prints `check2`, `check3` (T10, T11) and, under `check3`'s Yes, the state and the spouse's name and address.

### 9.4 Columns B and C `[Q14]`

**Builder's call B25 (second part):**

| The linked row                                          | Column B                         | Column C      |
| ------------------------------------------------------- | -------------------------------- | ------------- |
| `who` is `only_you`, entire value known                 | entire value                     | max(0, A − B) |
| Item shape, `collateral_who` is `only_you`, value known | `current_value`                  | max(0, A − B) |
| `with_someone` on either                                | blank, with C-1's note on screen | blank         |
| Value unknown (a 3b "I don't know")                     | blank                            | blank         |
| Two or more debts on one asset (C6)                     | blank on each                    | blank on each |

- Column C prints 0.00 when worked out as zero (PS:973, :511 leave it to this spec): both inputs exist, so it isn't an invented zero.
- Column B is a filer-facing figure from a filer-given value and is never derived for co-owned property (U:80, U:440). The rows fill once counsel rules `[C-1]`.
- **C6, draft:** U:428's max(0, A − B) would give a second lien the property's whole value, ignoring the first. Under U:80 that is a legal reading, so both rows print B and C blank with C-1's note. No persona has this.

### 9.5 Totals

D's total boxes as §5.3. E/F's `Total_6f`, `6i` and `6j` keep their rules, over every row, copies included. 106Sum 2, 3b and 3c are unchanged. A total adds confirmed rows only (U:152).

### 9.6 Testing

- **Tier 1 (read off the page):** each box on each block, tagged and stacked ones included. Each who-owes shape. The offset boxes one space from who-owes. Rows on copies. Blank where a value is blank.
- **Tier 2:** every new binding gets its row in `step2_verification.json`, written by the generator and citing the box's index label, in the same commit. Most rows are `pattern`-basis in the index (D 122 of 213, E/F 234 of 388, G 73 of 102, H 106 of 155), so the plan checks each block against the rendered page. `ASSERTED_CASES` rises on purpose. `known_defects.json` stays `[]`.
- **Tier 3 (each VERIFY by hand before pinned; no such rows exist today):**

| Persona | Rows                                                                                                                                                                                                            |
| ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| James   | D 2.1 Crestway A 8,500, B 14,000, C 0.00; E/F 4.1 Meridale; G 2.1                                                                                                                                               |
| Priya   | D 2.1 Kestrel A 14,900, B 20,500, C 0.00; E/F 4.1 Silverpine; 4.2 Westhaven with the codebtor tick; Part 3 Lakeshore on line 4.2; G; H Rohan on E/F 4.2                                                         |
| DeShawn | D 2.1 Harrowgate A 160,000, B 180,000, C 0.00; E/F 4.1 Lakeline, 4.2 Southmoor, 4.3 Tallgrass; Part 3 two parties; G and H "No"                                                                                 |
| Maria   | E/F 4.1 Brightwater, 4.2 Ironbridge, 4.3 Larkfield; Part 3 two parties on 4.1 and 4.3; G                                                                                                                        |
| Sarah   | E/F 4.1 Keelson (Student loans), 4.2 Lakemont; Part 3 Wicker on 4.2; G                                                                                                                                          |
| Andrés  | D 2.1 Copperline A 7,800, B and C blank; E/F 4.1–4.9 per S20, with a copy of page 4 holding 4.7–4.9 and 7 of 7 page numbers; 4.4 disputed, 4.7 offset Yes; Part 3 Ashgrove on 4.2; G 2.1, 2.2; H Mateo on D 2.1 |

- **Synthetic:** overflow on each group, totals including copies, G row 10, D row 12, a codebtor with many links, a shared asset (C6), and a line 6 item as collateral.
- **Journeys:** Generate All passes for all six. A filer past 5 contracts or 2 secured debts is synthetic, since no persona reaches them, except Andrés's E/F copy.
- **Security:** a filed form still prints its stored rows, and a schema change can't alter them.

**Gotchas:** "Schemas are checked at startup" (`claims.`), "Blank, not 0.00" (Columns B and C, row boxes), "`field_values`" (a claims copy), "Known form defects".

## 10. 3c6: the List of Creditors `[Q1.list]` `[DIG-123]`

**Delivers:** the form, in every packet. **Needs:** 3c5, whose row readers it shares.

### 10.1 **The template has not been read**

No copy is on disk, and no tool in this work has opened one. Every statement about its boxes comes from a memory note and U:454-459, both from 2026-10-16: page 1 has 10 creditor boxes (`creditor1.0.0`…), `Debtor1.Name`, `Case number1` and a `chapter` ComboBox; page 2 has 20. **Treat them as unverified.** A web search on 2026-11-06 confirms the bundle at https://www.ilnb.uscourts.gov/sites/ilnb/files/RequiredDocsCh72025January3.pdf is dated January 3, 2025, and its extracted text includes "EASTERN DIVISION". That doesn't settle page text versus widget.

### 10.2 The first step: read it

This belongs before the plan of 3c6, because §10.4 and S5 depend on it. Get the bundle (on 2026-11-06 the court's site answered scripts with "Request Rejected", so the owner downloads it in a browser), re-check its date, extract pages 12–13 into their own file, and read:

1. **Box names** on both pages, and whether page 2 repeats a name or case number. `_headers` repeats a value on a copy only if its box prints on another page too (`fill_resolver.py:362-385`), so otherwise a copy has no filer name.
2. **Multiline flags and sizes**, which decide whether name and address fit one box. A single-line box refuses long entries with `ValueTooLong` (`text_fit.py`).
3. **`/Opt` and the default** of the `chapter` combo. A value outside `/Opt` is refused (`pdf_filler.py:426`). A preset default also touches `read_drawn`'s list of blank-template defaults.
4. **`/Helv` encoding**: each box's `/DA`, and whether `/AcroForm /DR /Font /Helv` exists and matches. `test_printed_page.py:830` and `test_attached_sheets.py:351` pin one encoding across all templates, and `text_fit.font_for` reads that path. A different encoding is a stop, and the owner hears before a pin changes.
5. **Buttons**: `test_widgets.py:74-75` pins every Button as unprinted.
6. **Whether EASTERN DIVISION is page text or a widget** (§10.4).
7. **Whether extracting the pages keeps the AcroForm.**

### 10.3 The form

**Builder's call B27:**

- Commit the two pages as `data/forms/pdfs/ilnb_list_of_creditors.pdf`, matching the three `ilnb_G-*` files. `Dockerfile.heroku` copies the directory, so it needs no change.
- Index: `field_index/ilnb_list_of_creditors.index.json`, with a basis recorded by hand. No tool writes `basis`, and `form_ocr.py`'s model is the one the index README rejected.
- Schema: `template_version` is the hash (E002). Form type `list_of_creditors` (17 characters, `max_length` 20), added to `FORM_TYPE_CHOICES`; the plan checks whether a migration is needed, as earlier additions had one. The frontend `FormType` union and `FORM_TYPE_METADATA` gain it. `order` slot 10 is free.
- **Addendum rows for every binding, the tier 2 way, with no test change.** Checked against the code: `_expected_target` returns on an addendum match (`test_oracle_tier2.py:113-116`) before it reads `_renamed` (`:117`), which raises `KeyError` for a form absent from `conversion_report.json` (`:66-69`), and it does so at collection (`:145`). **So one binding with no row breaks all of tier 2's collection.** Constants need rows too. Audit files stay unedited. No other test under `apps/forms/tests` reads those audit files (grep).
- Registry: after 121 per the court's checklist as the memory note gives it (not re-read), or last if `test_registry.py:87-88`'s pin makes that cleaner. The registry's "filing order" already matches neither court source compared. `applies` is always; `requires` adds nothing beyond Complete and the claim gaps.
- **Rows.** A rule builds the list from D, E/F, G and H rows, notice parties and codebtors: **one entry per name and address, printed once**, comparing them ignoring case and spacing. The filer's own name isn't on it (C5, draft, PS:1400). **A refusal names the step of the row its entry came from,** first in the rule's order (Amounts Owed with its notice parties, then Contracts & Leases, then Codebtors). `RULE_FIXES` gives a rule one fix (`fill_resolver.py:307-308`) and `binding_fix` goes by binding (`:284-299`), so neither does this as it stands. The plan chooses the mechanism once the template is read, and a test refuses one over-long entry from each of the three. Page 2 continues by the copies mechanism: the group's capacity is 30 by the note, unverified, and a copy holds page 2's slots. This would be neither the first nor the only production `extra_page`, since 3c5 lands first.
- **Form 101 line 18** keeps counting debt rows (`derivations.py:412-416`). All personas stay in 1–49, so no pin changes.
- **Fixture.** `LBR-1007-1`'s text (`ilnd_2025_data.json:105-116`) is corrected to the rule's actual words. Per DIG-123's comment, a pro se filer owes the paper list, not the matrix. **The rule itself has not been read:** check it, not only the ticket. Nothing reads `LocalRule` today. It reaches production only by a hand `loaddata`, so the release note says so.

### 10.4 O2: open, for the owner

**A Western Division filer's heading. Asked only if the template prints the words as fixed page text.**

The court's form says "EASTERN DIVISION", and 10 of the 18 counties are Western, Winnebago and McHenry among them (`counties.py:8-27`). If the words sit in a fillable box, the question disappears: DigniFi prints the division from the county. If they're fixed text, the engine can't change them today (`pdf_filler.py` has no overlay or redaction; `insert_text` appears only in `sheets.py`). The options:

- **(a) Cover the words and print "WESTERN DIVISION" over them. Recommended,** after asking the clerk's office whether Rockford has its own version. Every filer gets a true heading. It alters the court's own page, which counsel should see, and it needs a small drawing step in `fill()`.
- **(b) Print the form as published.** Nothing to build, but it states the wrong division on a court paper.
- **(c) Leave Western filers without this page and tell them where to get it.** Honest and cheap, but incomplete for more than half the counties in the pilot district, and the list is required with the petition.

No production code reads a division today (`test_household_storage.py:183-200` pins the values). **No persona is Western** (the seed's counties are Cook and Kane, both Eastern), so any answer is proven with a synthetic Western session only.

### 10.5 Testing

- **Tier 1:** every box read off the page, an entry on page 1, page 2 and a copy.
- **Tier 2:** addendum rows; `ASSERTED_CASES` rises on purpose; the orphan test passes.
- **Tier 3 (entries):** Maria 6, James 3, Priya 6, DeShawn 6, Sarah 4, Andrés 14. 3d takes Priya to 7 and Andrés to 15. Each VERIFY by hand. Their contents follow C4's draft.
- **Same name and address once;** different address twice; a draft's creditor off the list; a Western session's heading per O2.
- **Pins that move** (about 16):

| Pin                                                                                                                    | Now → After                     |
| ---------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `test_registry.py:31` `ALWAYS`                                                                                         | 14 → 15 names                   |
| `test_registry.py:88` exact order                                                                                      | 17 → 18                         |
| `test_registry.py:119` test name, "fourteen"                                                                           | fifteen                         |
| `test_form_views.py:462`, `:520`, `:521`                                                                               | 13 → 14                         |
| `test_form_views.py:838`, `:1043`                                                                                      | 14 → 15                         |
| `test_seed_demo_data.py:116` `PACKET_SIZE`                                                                             | each +1: 16, 16, 15, 15, 15, 16 |
| `test_seed_demo_data.py:288`                                                                                           | 14 → 15                         |
| `andres-gig-driver.spec.ts:79`, `deshawn-assets.spec.ts:88`, `james-borderline.spec.ts:84`, `sofa-journey.spec.ts:119` | 14 → 15                         |
| `maria-happy-path.spec.ts:90`, `sarah-simplest.spec.ts:95` (with comments)                                             | 15 → 16                         |
| `e2e/pages/dashboard.page.ts:11` comment                                                                               | 14 → 15                         |
| `frontend/src/test/mocks/handlers.ts:56-57` `mockPacket`                                                               | 14 → 15                         |
| `test_widgets.py:68`                                                                                                   | 3003 → plus the new widgets     |
| `test_widgets.py:74`                                                                                                   | 67 → plus any buttons           |
| CLAUDE.md "14–16 forms", README                                                                                        | 15–17                           |
| "17" in CLAUDE.md, README, `types/api.ts:564`, `field_index/README.md`; "67" PDFs in CLAUDE.md and README              | 18; 68                          |

Forms parametrized on `get_all_form_types()` (tiers 1 and 2, `test_checks.py`, `test_schema.py`, `test_pdf_filler.py`, `test_printed_page.py`, `test_check.py`, `test_rule_fixes.py`, `test_attached_sheets.py`, `test_widgets.py`) each gain a case and may fail on shape. Their bodies weren't read. `docs/testing/test_maria_quick.py` and `test_persona_full_flow.py` already pin a stale 13 and are left alone, noted for cleanup.

**Gotchas:** "The packet decides which forms a filer gets" (range, the new form), "Schemas are checked at startup" (18 schemas), the Architecture and File Map counts.

## 11. Counsel

Counsel items never block a merge (U:633). "Draft" means a `DRAFT: counsel C-n` source comment; filers see no mark. Item numbers follow the scope synthesis, and the form-wide number is in parentheses.

**From the umbrella `[C-1]` `[C-9]`:**

- **C1 (C-1).** Which value supports a lien on co-owned collateral in Column B, and the legal-aid note's wording.
- **C2 (C-9).** Definitions of contingent, unliquidated, disputed and offset. **The definition of "unliquidated" must not imply the amount can be left blank**, since the owner's ruling makes it required (§2), and no wording may tell the filer to estimate. Counsel sees that ruling with this item. It doesn't wait on counsel. The amount box's and the address's help sentences ship draft here.
- **C3 (C-9).** The "Do you owe money on this now?" wording.
- **C4 (C-9).** Who belongs on the List. The persona counts assume D, E/F, G and H rows and notice parties, one entry per name and address.
- **C5 (C-9).** Whether the filer's own name goes first. Draft: no (PS:1400).

**New, proposed for the list. `C-1[1-5]` are taken in later specs, so these start at C-16 (B2):**

- **C6 (C-16).** Columns B and C when two liens share one property. Draft: both rows blank with C-1's note (§9.4).
- **C7 (C-17).** The word for a debt sold to a collector: who the filer lists as creditor and who as notice party, plus the rewording DIG-280 needs, which the ticket itself reads legally.
- **C8 (C-18).** "Can the lender take back property…" and the plain help beside the lien's four kinds. They are asked in the form's words, but the first sentence is DigniFi's, and it isn't on C-9.
- **C9 (C-19).** E/F Part 2's type ticks, where "divorce" sits beside 3d's domestic support (C-2).

O2's option (a) goes to counsel as well if the owner chooses it.

## 12. Old sessions, the owner's included

U:627 says the owner must plan for this. **The owner's production session has not been read**, so what follows says what refuses, not what the owner's rows hold. Refusals arrive in two PRs: the claim gaps with 3c3 (B36) and the legacy figures with 3c4 (B23). None reaches production before 3c6 is promoted (B1).

**Builder's call B23:**

- `vehicle_payment` and `other_property_mortgages` stay as columns, read only by a legacy gap, the `LEGACY_RENTAL` pattern, and drop a release later, with `AssetInfo.amount_owed`. No figure is copied to a debt, because code can't tell which debt it belongs to, and a sworn J total must not fall silently.
- **A stored figure above $0 that the linked payments don't cover** refuses Complete and every forms call (`step: "debts"`), naming both figures: "You told us you pay $350 a month for a car, and the payments you linked add up to $200. Add the rest to the loan on Amounts Owed or the lease on Contracts & Leases, or remove this figure." `vehicle_payment` compares with the sum of payments linked to vehicle rows (§8.1), debts and leases alike, and `other_property_mortgages` with the sum linked to line 1 rows answered No. A $0 link adds nothing. The gap stays until the sum at least equals the figure or the filer presses Remove (B39). Debt rows hold their own typed figures already (`models.py:821`), so the two can differ. A test holds a stored 350 against linked 0 and linked 200, both refused, and linked 350, which passes.
- **A typed line 4 beside a linked first mortgage** gets one sentence on Review naming both figures, since code can't tell a lot rent from a duplicate. It doesn't refuse. DeShawn's shape, before his seed changes, is this one.

**Builder's call B46:** the legacy gap is the last gap `claim_step_gaps` returns, after Codebtors, so the filer has met both Amounts Owed and Contracts & Leases before it matters. It stays out of `debtGaps.ts` and never disables Continue on Amounts Owed, as the draft sentence doesn't (its pin exempts it too), because the fix may sit on the next step, and Remove would otherwise be the only way forward. The figures reach the browser as a read-only `legacy_payments` on the session read, `{vehicle_payment, other_property_mortgages}`, each null unless it is above $0, since §8.4 takes both off the step's fields. Amounts Owed shows the sentence and Remove while a figure stands, and Review names it with a Go to.

**Builder's call B39:** the "remove this figure" is real, or a figure with nothing behind it (Priya's shape) could never clear. The gap's page offers Remove, which sends that field as 0. The serializer takes only 0 for these two, and anything else is ignored as a read-only field is. The plan checks `_save` accepts a partial `expense_info`.

**What a filer completed before 3c meets, the owner included.** Nothing is lost: the migration encrypts in place, with no default placement. Every completed intake stays `completed`, but the forms calls that run `_prepare` refuse with the first gap, and the dashboard links it. To finish:

1. Each debt: an address; status; on an unsecured row, offset; "anyone else contacting you", and each party's address.
2. Each secured debt: the property link, "I live here" on the home's row and first or additional, the lien, and the monthly payment. A debt typed with no property behind it and marked secured needs the filer's answer to "can the lender take back property".
3. Any debt at $0: an amount above $0. The owner must find every figure and address, with no "I don't know" (§2).
4. Contracts and Codebtors: the Yes or No, and each row's address, kind and links. Old codebtors with no link are a gap.
5. `no_debts`, if none.
6. Any legacy figure above.
7. Complete again. A filed form keeps what was filed.

The stored `collateral_description` stays as typed. Old `contract_type` and `relationship` values stay as stored, though some were the old default, not an answer, and `contract_type` can't tell which. Personas: `seed_demo_data --reset`.

**Undoing a migration** decrypts the listed columns and refuses an unreadable row, naming table and pk only. A `date_incurred` that isn't an ISO date returns as null (§6.1). Rows' new answers don't return to an older schema.

## 13. Left to the plan

- Read the List of Creditors template first (§10.2), and the national instructions on dates (B11).
- Exact helper and field names beyond those named, and how 3c1's total declaration reads in the schema.
- `pdf_filler` pixel measures of number boxes, H's line boxes, each persona's date, and any box this spec reports from `fit` alone.
- How many tests reach Complete with a debt (§7.7), and the order to migrate them.
- New `ASSERTED_CASES` values, on each PR's count.
- Whether `FORM_TYPE_CHOICES` needs a migration.
- Persona date corrections (S16).
- Page 2 of the List printing when blank; a Western heading's drawing, if O2 needs it.
- Persona briefs' wording: each brief changes as its PR lands (U Appendix B item 6). Stale PS line cites (`seed:281`, `personas.ts:257` and others) are re-found, since the companion is a target.

## 14. Not in 3c

- E/F Part 1, the priority split, "Not sure", and `priority_classification` no longer written (3d, DIG-119). 3d's spec, when written, must keep a debt's total required even where the split stays blank (§2).
- 122A-2's lines from the links (3h).
- Form 108, Form 107 line 6, and step 4's questions.
- Encrypting `AdversaryProceeding` (step 5).
- Scan pre-fill of addresses and payments.
- Dropping the retired columns (one release after this code is live).
- E/F 6g and 6h until C9.

## 15. Builder's calls

| #   | Call                                                                                                                       | §                 |
| --- | -------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| B1  | The split; no promotion until 3c6                                                                                          | 4                 |
| B2  | Counsel numbers from C-16; `DRAFT:` in `copy.ts`; form words in `formText.ts`                                              | 7.6, 11           |
| B3  | DIG-281 gets the 3b list pattern, not a save on Go Back                                                                    | 6.3               |
| B4  | Debts autosave half-filled rows; drafts confirm on Continue; gaps server-side with client copies                           | 7.2               |
| B5  | `ordered_debts`: alphabetical by creditor, then id                                                                         | 6.2               |
| B6  | Notice parties as encrypted JSON on the debt                                                                               | 7.1               |
| B7  | Debt-to-property FK, `SET_NULL`, session-scoped; a dead id is no link                                                      | 7.1               |
| B8  | "My home" is a row answered "I live here" (`lives_here`, asked on Assets, a gap once linked); first or additional is asked | 7.2, 7.5          |
| B9  | "Every column" excludes `session`; codebtor links in JSON reach debts and contracts                                        | 6.1, 7.1          |
| B10 | `collateral_description` stays as D's typed text                                                                           | 7.1               |
| B11 | `date_incurred` encrypted text, bounded once measured; undone, a non-date returns as null                                  | 6.1, 7.2          |
| B12 | `account_last_4` read-only derived                                                                                         | 7.1               |
| B13 | Yes/No on Contracts and Codebtors; H line 2 asked                                                                          | 7.3, 7.4          |
| B14 | E/F type from `debt_type`; 6g and 6h blank until C9                                                                        | 7.6, 9.3          |
| B15 | "Owe money now" picks a debt row; if missing, the filer adds it on Amounts Owed, returns and picks it                      | 7.3               |
| B16 | Lease kind asked; vehicle lease picks its row and payment                                                                  | 7.3               |
| B17 | "I have no amounts owed"                                                                                                   | 7.2               |
| B18 | A secured debt's payment must be answered, $0 allowed                                                                      | 7.2               |
| B19 | Vehicle n is the nth A/B vehicle row; 17c, 17d and past them                                                               | 8.1               |
| B20 | `total_monthly_expenses(session)` behind six boxes                                                                         | 8.2               |
| B21 | Calculator re-sourced in the same commit; catch-all stays                                                                  | 8.3               |
| B22 | Line 4 is typed rent or lot rent plus a first mortgage                                                                     | 8.1               |
| B23 | Legacy gap until linked payments cover the old figure; Review sentence on line 4                                           | 12                |
| B24 | Expenses step total stays typed-only; Review shows typed, linked and their sum                                             | 8.2               |
| B25 | Columns B and C table; C prints 0.00; `who` asked at the link where A/B has none                                           | 7.2, 9.4          |
| B26 | Form-level page numbers; D's totals; number boxes; generator; comma-joined second line                                     | 5.2–5.4, 9.2, 9.3 |
| B27 | The List: template, index, addendum, position, one entry per name and address                                              | 10.3              |
| B28 | **Amount: above $0 stands, on the server, with no "I don't know"; a scanned $0 draft is corrected before Complete**        | 2                 |
| B29 | A row with no amount yet stores 0, meaning not given; never null                                                           | 7.2               |
| B30 | Status: one question, null unanswered, `[]` none; three Boolean columns go                                                 | 7.1, 7.2          |
| B31 | Offset on unsecured rows only                                                                                              | 7.2               |
| B32 | Date and last 4 optional, printing blank                                                                                   | 7.2               |
| B33 | Community debt tick, unticked unless ticked                                                                                | 7.2               |
| B34 | `contract_type` and `relationship` lose their defaults                                                                     | 7.1               |
| B35 | `ClaimAnswers`, one-to-one, encrypted JSON                                                                                 | 7.1               |
| B36 | `ClaimStepGap` refuses forms calls after the Assets check                                                                  | 7.5               |
| B37 | Contracts and codebtors stay in id order                                                                                   | 6.2               |
| B38 | Addresses as columns on all three tables; two-letter state checked at Complete                                             | 7.1               |
| B39 | A legacy figure can be removed, to 0 only                                                                                  | 12                |
| B40 | A codebtor's links spill to further H rows                                                                                 | 9.3               |
| B41 | G's template default stays; D Part 2's entry box stays blank                                                               | 9.3               |
| B42 | A type change never overwrites a secured answer the filer pressed                                                          | 7.2               |
| B43 | A stored `is_secured` stands; a scanned draft counts as unpressed                                                          | 7.2               |
| B44 | A lease and a secured debt on one vehicle: a gap until the payment is entered once                                         | 7.3, 7.5          |
| B45 | J 17c and 17d: order, a shared slot, fixed Specify words                                                                   | 8.1               |
| B46 | The legacy gap comes last, never disables Continue, and reads a `legacy_payments` field                                    | 12                |
| B47 | The autosave's 2-second wait is accepted, as on Assets; no save on leaving the page                                        | 1, 4              |

**Tickets closing:** DIG-164 and DIG-280 (3c2), DIG-282 (3c4), DIG-123 (3c6). DIG-281 narrows in 3c2 and closes in 3c3, with the autosave's 2-second wait accepted (B47).
