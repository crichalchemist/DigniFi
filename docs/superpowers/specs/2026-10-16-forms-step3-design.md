# Forms step 3: schedule rows and models

**Status:** approved in brainstorming on 2026-10-16. The owner answered 31 questions (Q0–Q30), chose approach "a" (ten PRs, income before rows), and approved design sections 1–5 one at a time. Appendix B lists what this document settles that the sections did not show the owner. The owner then approved the written spec and the persona drafts on 2026-10-16, asking for fictional creditor names.

**What this is:** the umbrella spec the owner chose in Q0 `[Q0]`. It fixes step 3's scope, the rules every step 3 PR follows, and the order of the ten PRs. Each PR then gets its own short spec, plan and build. A PR spec asks the owner only the judgment calls this document leaves open, and it never reopens one this document settles.

**Branch:** `feat/forms-step3`, on `develop` at `9bd6665`. The relicence to the AGPL lands in the same PR (#25).

**Production:** nothing deploys until steps 3, 4 and 5 are done and DIG-146 is fixed. Production stays at v31 (`3416f4c`).

**Tags.** A tag in square brackets, such as Q13.link or DIG-274 in brackets, names the owner's answer or the ticket a sentence carries out. Appendix A maps every tag to exactly one PR, and each tag appears in that PR's section below.

## 1. Why

Step 2 put every figure intake already collects into its right box, and it emptied the known-defects list. The packet still falls short of what a filer can sign:

- **The schedules print totals, not rows.** No production schema has a repeat group (checked 2026-10-16), so Schedules A/B, C, D, E/F, G and H list no single asset, exemption, debt, contract or codebtor.
- **The means test passes people it should not.** The in-app verdict and 122A-2 come from different code, and DIG-146 makes the result about 4.4 times too lenient. The Census median is a stale table, read with `latest("effective_date")` (`eligibility/models.py:126`), which ignores the filing date (DIG-274).
- **Whole parts of the forms are never asked:** priority debts, payroll deductions, a non-filing spouse's income, the household, the county, the IRS standards, and a set of Schedule J lines.
- **The fee waiver is decided for the filer.** `handleComplete` routes filers to the waiver on a threshold that is not the court's (DIG-145).
- **Some filer data is still stored in plain text:** income and expense amounts, creditor names, contracts and codebtors.

## 2. Where this step fits

| Step                            | What it does                                                                                                    |
| ------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 1. Foundation (done, #18)       | One fill path, full-name bindings checked at startup, the packet list, oracle tiers 1–3, the known-defects list |
| 2. Rebind (done, #19, #22)      | Every figure intake collects reaches its right box; forms generate only from a completed intake                 |
| **3. Schedule rows and models** | Every row prints; the questions the schedules and means test need; one calculator on dated tables; encryption   |
| 4. Form questions               | The asked fields, SOFA, Forms 108 and 103A, FormAnswer encryption, signing guidance                             |
| 5. Security                     | An adversarial security audit and its remediation                                                               |

"Done" for the project is a full single-filer packet: every form an individual ILND Chapter 7 filer needs. Joint filing is out, and Debtor 2's identity boxes stay blank.

## 3. Scope

### 3.1 What step 3 delivers

When step 3 is done:

- A single ILND Chapter 7 filer, married or not, gets these forms printed from what they told DigniFi, in the boxes the forms ask for:
  - Schedules A/B, C, D, E/F, G, H, I and J;
  - Forms 106Sum, 122A-1 and 122A-2;
  - Form 103B, when the filer asks for a waiver;
  - ILND's List of Creditors.
- Every row a filer lists prints, however many there are. Rows go on copies of the official extra page or on generated attached sheets.
- Every answer that is the filer's to give is asked in the form's own words and never decided for them: exemptions, priority, claimed deductions, Chapter 13 eligibility, the fee-payment choice and debt status.
- The in-app means-test result and the 122A-2 boxes come from one calculation on the official tables in force. That fixes DIG-146.
- Every new piece of filer data is encrypted, and so is every existing plaintext filer column in a table step 3 migrates.

### 3.2 Left to step 4

- Form 108's intention question and the form `[Q1.108form]`. Step 3 stores what it needs: the debt-to-property link and the personal-property-lease flag (§5.9).
- Form 103A `[Q1.103A]`. Until then, a filer who picks installments is told to get Form 103A from the court (§5.7).
- Form 107 lines 4–6, with the rest of the SOFA `[Q3]`: the three-year income questions and line 6's link, purpose and address. Step 3 gives debt rows the address and stable id that line 6 links to (§5.9).
- Schedule I lines 11 and 13 `[Q6.lines11_13]`, and Schedule I line 1 (employment details, both columns), per step 2's DIG-82 row.
- 122A-2 line 43 (special circumstances).
- The consumer-or-business-debt question and the paid-preparer question.
- Form 101 line 12, "Are you a sole proprietor of any full- or part-time business?", with the other asked fields. The gig driver answers Yes.
- FormAnswer encryption (DIG-168). Step 3 writes nothing new into `FormAnswer`.

### 3.3 Left to step 5

- `DebtorInfo` identity encryption, and dropping `DebtorInfo.household_size`.
- The plaintext pay-stub gross figure in `IngestedAggregate` `[DIG-278]`, unless DIG-176 handles it first.
- The adversarial security audit.

### 3.4 Still out

Joint filing. Debtor 2's identity boxes stay blank: names, signatures and Form 101's second column. A non-filing spouse's figures are in scope (§5.5).

## 4. Rules every step 3 PR follows

### 4.1 The filer decides; the app informs

- Anything that is the filer's to say is asked in the form's own words. That covers exemptions, priority, claimed deductions, debt status, Chapter 13 eligibility, the fee-payment choice and "secured or not".
- Nothing is pre-selected, with one approved exception: "secured or not" starts from the debt type, and the filer can change it.
- Arithmetic the form spells out is computed and printed: totals, Schedule D Column C, the 122A-2 result boxes, line 36's product.
- Figures, caps and thresholds the filer might weigh are shown as labelled information, never as a verdict. No text says "you qualify".
- Legal characterizations are asked, or left blank until counsel rules. They are never derived. Two examples are which exemption is a homestead exemption, and the value of co-owned collateral.

### 4.2 Encryption

- New filer data is encrypted from the start.
- Each PR encrypts the plaintext filer columns of the tables it migrates, with the data migration in the same PR. The PR sections below list the columns.
- Sorting, filtering and matching on an encrypted column happen in Python on decrypted values. A `Meta.ordering` or `order_by` on an encrypted column orders rows by ciphertext (DIG-164).
- Nothing new goes into `FormAnswer` until DIG-168 encrypts it.
- Untouched tables keep their plaintext columns until step 5: `DebtorInfo` identity and `AdversaryProceeding`. The SOFA rows and `FormAnswer` belong to step 4.

### 4.3 Dated public data

One policy covers every public table step 3 reads: the Census median, the IRS standards, the HHS poverty guidelines, the Illinois exemption amounts, the § 104 amounts (including the § 109(e) limits and the 122A-2 thresholds), and the USTP district multiplier.

- **Storage.** Each table's rows carry an effective date, a `valid_through` date and a source URL.
- **The date that applies.** The day the forms are filled stands in for the filing date. An unfiled form re-fills on every download, so it always uses the tables in force that day.
- **Lookup.** The newest table whose effective date is on or before the fill date and whose `valid_through` has not passed. This replaces `latest()`.
- **Refusal.** When no table is in force, DigniFi refuses in plain words and logs it. It never falls back to old figures.
- **Notice.** The packet and the dashboard name the periods used, and say to download again if filing after the next change date.
- **Scheduled tables** get a `valid_through` computed from their next scheduled change:

  - the Census median, April 1 and November 1;
  - the HHS guidelines, each January;
  - the § 104 amounts, April 1 every three years.

  If the operator misses a change, the refusal fires.

- **Irregular tables** have no schedule to refuse on. The IRS standards are also posted on May 15 and July 15, and the Illinois exemption amounts change with the statute. For these, the runbook is the only guard.
- **Runbook.** It lists every table's updates and where to find them. The owner is the named operator unless they name someone else.
- **Tests** pin the fill date, so CI behaves the same in every month.

### 4.4 Refusals

Requirements are split by who needs them:

- **Complete** refuses what every packet needs and the intake steps ask:
  - identity;
  - income by source;
  - marital status;
  - the household list;
  - creditor, contract and codebtor addresses.
- **A form's `requires()`** refuses what only that form needs:
  - Schedule C needs the exemption choice;
  - 122A-2 needs its details step;
  - 103B needs the fee-waiver answers;
  - in step 4, Form 108 will need the intentions.
- **Blank.** Anything a filer may legitimately leave unanswered prints blank.
- **Every refusal names the step or page that fixes it.** This closes DIG-181.

3a1 builds the framework. Each later PR adds its own requirements to the right gate.

### 4.5 Blank versus zero

Step 2's rule stands: a derivation never turns a missing input into 0.00.

One exception: Schedule I and 122A-1 both say "If you have nothing to report for any line, write $0 in the space". On those two forms, a line DigniFi asked and the filer left blank prints $0.00. The exception applies only in a column that applies to the filer:

- a spouse column for a filer with no spouse at home stays blank;
- lines DigniFi never asks, such as Schedule I 11 and 13 until step 4, stay blank.

122A-2's own "$0" instructions (line 3, the floors) are arithmetic, which 3h follows.

### 4.6 One way to print

- Every form in the packet is drawn value by value at each widget's own rectangle, then flattened. That gives one printing path and no shared-name errors anywhere.
- Extra rows go on copies of the official extra page, or on a generated attached sheet when the template has none. A form's totals include every row, wherever it printed.
- The packet can no longer be filled in a PDF viewer. A correction goes through DigniFi and a regeneration. Signatures and dates were always handwritten.

### 4.7 Rows and links

- Every row keeps a stable id across saves.
- Links use those ids: debt to property, codebtor to debt, notice party to debt.
- Draft rows from scans never print and never count in a total.
- Saves on one session are serialized.

## 5. The ten PRs

### 5.1 Sequence

Each PR gets its own spec, plan and build. Each targets `develop`, and is squash-merged only with the owner's yes.

| #   | PR                                 | Needs                 | Persona data it adds                                                                                                                                           | CLAUDE.md gotchas it rewrites                                                                                            |
| --- | ---------------------------------- | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 1   | **3a1** data foundations           | none                  | the sixth persona, seeded with the basics; its E2E journey runs from the start                                                                                 | seed order; nested debts and assets save by id; autosave sends only real edits                                           |
| 2   | **3a2** drawing engine             | 3a1                   | none                                                                                                                                                           | `field_values`; schemas checked at startup; known defects; the repeat note in blank-not-zero                             |
| 3   | **3e1** household and spouse       | 3a1                   | spouse figures for Priya and DeShawn; household lists and counties for all six                                                                                 | `household_size` defaults to 1; means-test units                                                                         |
| 4   | **3e2** income detail and expenses | 3a2, 3e1              | deductions matching the briefs' take-home pay; the gig driver's business income; the new Schedule J lines                                                      | income is stored by source; blank, not 0.00; expense names are the backend's                                             |
| 5   | **3f** fee waiver                  | 3e1, 3e2              | each persona's line 8 choice; DeShawn no longer routed to the waiver                                                                                           | the fee-waiver application; the packet decides which forms                                                               |
| 6   | **3b** A/B                         | 3a2                   | asset lines for everyone; the gig driver's co-owned property                                                                                                   | nested debts and assets save by id                                                                                       |
| 7   | **3c** claims                      | 3b                    | addresses, a contract, a codebtor, a notice party; James's and DeShawn's loans linked; Priya's car payment resolved; the gig driver's lease and nine creditors | nested debts and assets save by id (contracts and codebtors); the packet decides which forms; schemas checked at startup |
| 8   | **3d** priority                    | 3c                    | priority tax debts (2025 income tax) for Priya and the gig driver, and the gig driver's "Not sure" toll debt                                                   | none                                                                                                                     |
| 9   | **3g** Schedule C                  | 3b                    | each persona's exemption choices                                                                                                                               | none                                                                                                                     |
| 10  | **3h** 122A-2 and the means test   | 3a1, 3c, 3d, 3e1, 3e2 | Priya's full 122A-2, worked by hand from the official tables                                                                                                   | the packet decides which forms; means-test units                                                                         |

Income comes before rows (approach "a"): the household, spouse and income models land first, so the fee waiver and the means test are fixed early, and the row PRs build on settled income data.

3g can slip to step 4 without blocking 3h. 3c (about 690 row boxes) and 3h may each split in their own specs.

**Gotchas `[GOTCHAS]`.** Each PR rewrites the CLAUDE.md gotchas its change touches, in the same PR. The table's last column lists them. A PR that changes behaviour a gotcha describes and leaves the gotcha stale is not ready.

### 5.2 What every PR shows before it is ready

- Backend tests, vitest and every E2E journey green, the sixth persona's journey included.
- `known_defects.json` still `[]`.
- Every new placement committed with its audit addendum row (`data/forms/field_index/audit/step2_verification.json`, or its step 3 successor).
- Every new or migrated filer column encrypted, with a test that the stored column holds ciphertext.
- No commit trailers.
- `develop`'s CI green after the merge.

Counsel items never block a merge. Wording waiting for counsel ships marked as draft, and counsel signs off before production (§9).

### 5.3 PR 3a1: data foundations

**The median fix comes first `[Q11]` `[DIG-274]`.** It is 3a1's first commit, built on the dated-data model. It loads the Census tables in force when 3a1 lands, and the lookup switches to the newest table in force on the fill date.

The USTP means-testing page, checked 2026-10-16, shows:

- **The Census update** was posted 3/18/2026 "for cases filed on or after April 1, 2026". For Illinois households of 1–4 people it gives $73,180 / $93,934 / $113,625 / $137,902.
- **The fixture** (effective 2025-11-01) holds $71,304 / $91,526 / $110,712 / $134,366.
- **No November 2026 table** was posted yet. Check again when 3a1 builds.

Production v31 ships the same stale fixture.

**The dated-data model `[Q10]` `[CORR.valid_through]`.** It is one model for every table in §4.3:

- the effective date, `valid_through` and source URL per table;
- the lookup and the logged refusal;
- the filer notice;
- the runbook, with the owner as the operator.

3a1 loads only the median. Each later PR loads the tables it reads: HHS in 3f, the Illinois exemptions and law catalog in 3g, the IRS standards, § 104 amounts and district multiplier in 3h.

**The refusal framework `[Q12]`.** Complete and `requires()` split as §4.4 says. Every refusal names the step or page that fixes it, which closes DIG-181.

**Stable row ids `[DIG-273]`.** `IntakeWizard.tsx:343` discards the session PATCH response, so `_save_rows_by_id` re-creates the id-less asset and debt rows on every autosave and deletes the old ones. 3a1 merges the returned ids into step state, and gives `useAutoSave` a baseline that already carries them, so ids survive every save. Links in 3c depend on this.

**Drafts never print `[DIG-163]`.** Scanned draft debts are left out of every row and total until the filer confirms them.

**Serialized saves `[DIG-188]`.** Saves on one session take a lock, so two saves cannot interleave before rows bind.

**The sixth persona `[Q28.data]`.** Its seed and an E2E journey skeleton land here, with only the data the current wizard asks. Each later PR adds the persona data its feature needs (§7).

Two interim choices fall to the 3a1 spec:

- **His business net income.** It has no source until 3e2, so the spec picks where it goes; it must not be typed into the wages box. The seed and the journey must agree.
- **His fee answer.** He chooses installments, but today's seed and fee-waiver page still route on the old flag until 3f.

3a1 also updates every doc and test that counts five personas or seven journeys.

**Fictional creditor names `[Q28.names]`.** 3a1 renames the five personas' private creditors in the seeds, briefs and E2E fixture to the fictional names in the companion document's rename table. No real firm's name ever gets an address on a List of Creditors. Government creditors keep their real names.

**Source code link.** A "Source code" link in the app's footer points to the public repository. The AGPL expects this of a network service (§10).

### 5.4 PR 3a2: drawing engine

**Draw per widget and flatten `[Q8]`.** Every form in the packet is drawn per widget and flattened (§4.6). The method was proven in a spike `[SPIKE]`:

- per widget, PyMuPDF `page.insert_text(Point(rect.x0 + 2, rect.y1 - 0.25 * h), text, fontname="helv")` (`insert_textbox` drew nothing on 14 pt boxes);
- then `delete_widget` on every widget, and `/AcroForm` set to null.

This method was replaced in 3a2: pypdf builds each widget's appearance and PyMuPDF bakes it (`docs/superpowers/specs/2026-10-17-forms-step3a2-design.md` §3).

Writing each value at its own widget's rectangle, not by field name, fixes the shared-name boxes:

- `undefined_19`;
- Schedule D's `account number` and `check 5`;
- Schedule I's `Time employed Debtor 1`;
- Schedule I's `Assistance 8f`, which is both the 8f "Specify" box and line 11's;
- A/B `24.1` and `24.2`.

**Continuation copies `[Q8]`.** For forms whose template has an extra page, DigniFi fills as many copies of the official page as the rows need, numbered as the form says. The forms are:

- D page 2;
- E/F pages 2 and 4;
- G page 2;
- H page 2;
- C Part 2;
- the notice parts D Part 2 and E/F Part 3, by copying their page.

**Attached sheets `[Q9]`.** On forms whose template has no extra page (A/B, Schedule I's employers, 122A-2, 103B), DigniFi generates the attached sheet the form asks for:

- one plain page format, headed with the filer's name, the form's name and a blank "Case number (if known)";
- each row labelled with the line it continues, with the same columns as the form's row;
- the sheet appended after its form;
- the form's totals include the sheet's rows. A/B lines 2, 5, 15 and 52 say so.

The same generator makes the Schedule I 8a business and rental statement (3e2) and the additional-employers page. An attached sheet is part of its form's output, not a separate form, so it needs no registry entry, schema or field index. Startup check forms.E001 is unchanged.

**What 3a2 proves, and on what.** No production schema has a repeat group today. 3a2 therefore proves continuation copies and sheets on synthetic schemas. Its production change is that every existing form prints through the drawing path. The first production rows arrive in:

- 3e2: the 8a statement sheet;
- 3b: A/B rows and sheets;
- 3c: continuation copies of D, E/F, G and H, plus the List of Creditors.

`RepeatOverflow`'s 422 refusal stays only until 3a2's engine replaces it.

**The oracle is rebuilt `[Q8]`.** Flattened pages have no fields left to read (§6.1).

**Filed forms.** `field_values` records each page copy's values (encrypted), so a filed form's download redraws exactly what was filed.

**Pin PyMuPDF.** `pymupdf` is unpinned in `backend/requirements/base.txt` (1.27.2.3 is installed locally). 3a2 pins it.

**Every widget type.** The engine draws every widget type the templates use: text, checkboxes, the 2 radio buttons and the 18 combo boxes. The spikes tested only text and checkboxes. ILND's List of Creditors (3c) adds a `chapter` combo box.

**Fonts.** The built-in Helvetica covers Western European text only. 3a2 either embeds a Unicode font, under an AGPL-compatible licence, or refuses in plain words a value it can't draw. Its spec chooses which.

**Timing.** Before the engine replaces the old filler, 3a2 measures Generate All for a full packet against the Eco dyno's limits (DIG-137).

### 5.5 PR 3e1: household and spouse

**Marital status and the spouse's income `[Q2]`.** The step asks marital status in 122A-1 line 1's terms; joint filing stays out.

When the filer lives with their spouse, the step collects the spouse's income by the same ten sources as the filer's. Those figures fill Schedule I's column 2 and 122A-1's Column B. Current monthly income is A + B everywhere: the median comparison, the means test and the forms. Debtor 2's identity boxes stay blank.

Item 15 of the queue (MERGE-SPOUSE) was settled by Q2. Its details belong to the PRs that print them:

- 122A-2 line 3's marital adjustment is in 3h;
- 103B line 1's "Your spouse" and line 2's `undefined_3` are in 3f.

**Encryption `[Q7.marital]`.** `IncomeInfo.marital_status` is encrypted, with its data migration. `IncomeInfo` is migrated again in 3e2 for the ten amounts. The spouse's amounts are new data, so they are encrypted from the start.

**The household `[Q17]`.** One encrypted list holds the people in the filer's home and the people they support. For each person the filer gives:

- the relationship;
- the age;
- whether the person lives with the filer;
- whether the person is claimed on the filer's tax return or supported by the filer.

These are the filer's answers, never inferred. No names are stored.

"Claimed on your tax return" is ambiguous for a spouse on a joint return, and the answer decides whether a non-filing spouse counts as a Schedule J line 2 dependent. The 3e1 spec settles how a spouse appears on the list, together with C-3.

Each form counts the list by its own definition:

- **Schedule J line 2:** the dependent rows.
- **103B line 1:** the filer, a spouse unless separated, and dependents.
- **122A-2 line 5:** "could be claimed as exemptions … plus any additional dependents whom you support", with the line 7b/7e age-65 split.
- **122A-1 line 13:** the people who live with the filer, until counsel rules `[C-3]`.

**What the list replaces.** It replaces `DebtorInfo.household_size`, the 103B pre-fill from it, and `IncomeInfo.number_of_dependents`. DIG-159's cap becomes a limit on the list's length `[DIG-159]`.

**County `[OQ9.county]`.** The Debtor step asks every filer their county, from ILND's counties. There is no ZIP-to-county lookup; it would be one more dated dataset. Form 101's `Debtor1.County` rebinds from `answer:form_101.county`, a FormAnswer nothing writes, to the stored county `[DIG-277]`. 122A-2 lines 8, 9a and 12 read the same county in 3h.

**Where they live `[CORR.county]`.** County and the household list go in their own new encrypted model, not on `DebtorInfo`, because step 3 does not migrate `DebtorInfo` (§4.2). `DebtorInfo.household_size` stays in place but unread, and step 5 drops it.

**Seeds `[DIG-53]`.** The seeds' marital statuses are corrected. Today they include `married_joint` for filers who file alone.

**Counsel.** C-3 decides which reading of "household" 122A-1 line 13 uses.

### 5.6 PR 3e2: income detail and expenses

**One expense design `[Q4.everyday]`.** The Schedule J lines DigniFi never asks join the Expenses step: 4a, 4b, 4d, 10, 13, 14, 16, 19, 20a–20e and Other 21. One expense model serves Schedule J and 122A-2, so each amount is asked once. The new amounts are encrypted from the start.

**Schedule J line 3 `[CORR.J3]`.** "Do your expenses include expenses of people other than yourself and your dependents?" is asked in the form's words on the Expenses step. No PR placed it until the persona drafts found it; the owner confirmed it at the spec review. A filer whose expenses include a non-filing spouse's would answer Yes.

Four neighbouring groups of lines are placed elsewhere:

- **From 3c's links:** a homeowner's line 4 mortgage payment and line 5 (§5.9). A renter types rent on line 4, as today.

- **Already bound:** J 6d and "Other 6d" (combined utilities, step 2 Q4).
- **Step 4:** 6a–6c, 15a and 15b.
- **From other PRs:** dependents (J line 2) come from 3e1's household list, and 17b–17d from 3c's links.

**Business, rental and interest income `[Q5]`.** The Income step adds three things:

- business or self-employment income, as gross receipts, operating expenses and net. These feed 122A-1 5A–5C and Schedule I 8a.
- rental income, split into gross and costs. These feed 122A-1 6A and 6B; 6C and Schedule I 8a keep the net.
- interest and dividends, for 122A-1 line 7 and Schedule I 8b.

The Schedule I 8a statement prints on 3a2's sheet generator. A gig worker with mostly personal debts stays in the app: the business-debt off-ramp is unchanged. Form 107 line 4's business income is step 4.

A cost used both for the business and at home, such as a car, gas or insurance, could be counted twice: once in operating expenses and again on Schedule J or 122A-2. The filer splits it; the app never does. The 3e2 spec decides whether an information note says so.

**Government assistance, asked once `[Q6]`.** Schedule I 8f is asked once, on the Income step: regular government assistance, with cash or non-cash kinds and the value if known. 103B line 3 reads the same answer in 3f.

**Encryption `[Q7.income]`.** `IncomeInfo`'s ten amounts and `ExpenseInfo`'s 13 amounts are encrypted, with their data migration.

**Payroll deductions `[Q16]`.** Schedule I 5a–5h are asked in the form's own words, typed monthly by the filer, and for a spouse who lives with them.

- **Help text** explains how to turn a per-paycheck amount into a monthly one, and what "mandatory" and "voluntary" mean on 5b and 5c, without choosing for the filer.
- **Arithmetic.** A blank stays blank and counts as zero in line 6. Line 7 is line 4 less line 6, which fixes Schedule I 10 and 12, 106Sum line 4, and Schedule J 23a and 23c.
- **Asked once.** The same amounts feed 122A-2 lines 16–19 in 3h.
- **Pay stubs** keep supplying only the employer's name (step 2 Q14; revisit with DIG-176).

**The six-month window `[Q26]`.** The ten sources, and the spouse's, are asked as the six-month average 122A-1 defines.

- The step names the actual months, computed from the fill date, for example "March 1 through August 31".
- It then asks: "Is your income now different from that average?" On Yes it asks for the current figures, which feed Schedule I. Otherwise Schedule I uses the same figures.
- If the forms are prepared in a later month, the dashboard says the window moved and asks the filer to check.
- Counsel confirms the wording `[C-10]`.

**$0.00 on Schedule I and 122A-1 `[Q27]`.** These two forms carry the exception in §4.5. The CLAUDE.md "Blank, not 0.00" gotcha is rewritten to match.

### 5.7 PR 3f: fee waiver

**The filer picks Form 101 line 8 `[Q21]`.** Every filer answers line 8 (`Check Box7`, stored encrypted) in its three options: pay in full, pay in installments, or ask for a waiver.

- **Beside the question, as information:** "the court may waive the fee only if your family's income is below $X a month for a family of N, and you can't pay in installments". The figure comes from the dated HHS poverty table, which 3f loads.
- **The packet.** 103B is in it exactly when the filer asks for a waiver. Installments shows the "get Form 103A from the court" message until step 4.
- **Withdrawal.** Changing the answer withdraws the application.
- **Removed:** the `qualifies_for_fee_waiver` routing in `handleComplete`, and the `FeeWaiverPage` off-ramp.
- **Where the answer lives:** not on `DebtorInfo` (§5.5). The 3f spec places it.
- **Persona outcomes change.** DeShawn's packet goes from 15 forms to 14, and the E2E `WAIVER_FILERS` list changes.

**The threshold and the filer's figure `[Q22]`.** Beside the threshold, as information, DigniFi shows the filer's own figure as § 820.20(a)(2) defines it: Schedule I line 12 less the non-cash help they entered.

- It never says "you qualify". "The court decides" sits beside it.
- Sarah is the test case.
- Counsel confirms the wording `[C-7]`.
- Which HHS date counts (published, effective, or the court's own table; FW-5) is settled in the 3f spec, after asking the ILNB clerk.

**The 150% test as information `[DIG-145]`.** The poverty test is shown as information. It gates nothing.

**Encryption `[DIG-279]`.** The fee-waiver answers are encrypted: `household_size`, `receives_noncash_assistance`, `benefit_types` and the `cannot_pay_*` answers.

**Fail loud `[DIG-223]`.** `_fee_waiver_household_size` raises on missing data instead of guessing.

**From the earlier PRs.**

- 103B line 3 reads 3e2's Schedule I 8f answer. The fee-waiver page stops asking it again, which fixes Maria's 103B (SNAP) against her blank 8f.
- Line 1 counts the household by its own definition (§5.5).
- Line 1's "Your spouse" and line 2's `undefined_3` come from 3e1.

**A conflict for the 3f spec to put to the owner.** Q16 says 3f _may_ pre-fill 103B's take-home pay from Schedule I line 7. Step 2's rule says take-home pay is never pre-filled. The 3f spec asks the owner which stands. It does not blend the two.

### 5.8 PR 3b: A/B

**The A/B package `[Q24]`.**

- **Every line is walked.** All ~45 A/B lines are shown, grouped by Part with the form's own examples, and every line's Yes/No is derived from its rows. No line can be skipped unseen.
- **Vehicles.** Line 3 (cars, vans, trucks, motorcycles) is split from line 4 (watercraft, aircraft, motor homes, ATVs and other recreational vehicles). That closes the RV gap.
- **Ownership.** The filer picks "only you" or "you and someone else"; the Debtor 2 boxes stay blank. The community-property box stays unticked unless the filer ticks it. The nature of the interest is optional, "if known".
- **Old rows.** An asset saved before 3b has no A/B line. DigniFi refuses in plain words until the filer picks each old row's line. There is no default placement.

**Both values `[Q14.values]`.** The filer types both A/B values: the current value of the entire property, and of the portion they own. Schedule D Column B reads them in 3c.

**Encryption `[Q7.assets]`.** `AssetInfo.description` and `financial_institution` are encrypted, with their data migration.

**Ordering in Python `[DIG-164]`.** `AssetInfo.Meta.ordering` (`["asset_type", "-current_value"]`, `models.py:397`) sorts encrypted columns, so Postgres orders rows by ciphertext. 3b orders assets in Python, with A/B line 53 by id. Debts follow in 3c.

**Rows.** A/B rows past a line's capacity go on 3a2's attached sheet, and the line totals include them.

**A leased vehicle.** A/B Part 2 says "If you lease a vehicle, also report it on Schedule G". Whether a leased vehicle gets an A/B line 3 row, and at what values, is for the 3b spec.

### 5.9 PR 3c: claims

**The debt-to-property link `[Q13.link]`.** Each secured debt links to the property it secures: an asset row, or "my home". The debt's balance and monthly payment become their only sources. The link derives:

- **Schedule D:** Column B, and Column C = max(0, A − B), the form's own arithmetic;
- **Schedule J:** 17a–17d, one payment per car, which closes D-2;
- **Form 108:** its inputs, stored for step 4.

A vehicle lease is a Schedule G contract that gains a monthly payment and a "vehicle" kind. It feeds Schedule J 17 and 122A-2, and it is Form 108's personal-property-lease flag `[Q1.108data]`.

Two duplicate sources retire: `AssetInfo.amount_owed`, which no form reads, and `ExpenseInfo.vehicle_payment`. The seeds are corrected.

**The home's payments `[CORR.J45]`.** For a filer whose home secures debts linked to "my home", Schedule J line 4's first-mortgage payment and line 5 (additional mortgage payments, such as home equity loans) come from those debts' monthly payments. A renter keeps typing rent on line 4. Q4 had placed line 5 on 3e2's Expenses step, but Q13 makes a debt's payment its only source, and the two would ask the same money twice. DeShawn's seeded $1,200 `rent_or_mortgage` duplicates his mortgage's $1,200 payment today. Q13 wins, since it is the specific rule; the owner confirmed it at the spec review.

**Priya's car payment `[DIG-282]`.** Priya's $450 `vehicle_payment` has no car or loan behind it. The link and her persona update resolve it.

**Column B for co-owned collateral `[Q14]`.** For collateral the filer owns alone, Column B prints the one value (entire equals portion), and Column C is the form's arithmetic. For co-owned collateral, Columns B and C stay blank, with an information note that legal aid can help decide which value applies. The rows fill once counsel rules `[C-1]`. Neither the form's text nor the uscourts instruction booklet (December 2015) settles which value applies.

**The claims package `[Q25]`.**

- **Addresses (S3-ADDR).** The filer types creditor, contract and codebtor addresses, and Complete requires them. Scan pre-fill can come later. Debt rows with an address and a stable id are what Form 107 line 6 links to in step 4.
- **Notice parties (S3-NOTICE).** "Is anyone else contacting you about this debt?" asks for a name, an address and the last 4 digits. The answers fill Schedule D Part 2 and E/F Part 3.
- **Status (S3-STATUS).** Date incurred, contingent, unliquidated, disputed and offset are asked plainly, with counsel's definitions, and nothing is pre-ticked. The date's type is checked against the national instructions.
- **Secured (S3-SECURED).** "Can the lender take back property…" starts from the debt type and can be changed. The lien's nature is asked in the form's words, with nothing pre-ticked.
- **Codebtors (S3-H).** Codebtor links give the H rows, and the linked D, E/F rows tick "At least one of the debtors and another".
- **Contracts that are also debts (S3-GCLAIM).** "Do you owe money on this now?" lists a contract on E/F as well.
- **The List of Creditors (S3-LIST)** is described next.

**The List of Creditors `[Q1.list]` `[DIG-123]`.** FRBP 1007(a)(1) requires the names and addresses of all creditors with the petition. ILND's "Requirements for a Bare Bone Petition – Pro Se – Chapter 7" (updated January 3, 2025) includes the court's own fillable List of Creditors on pages 12–13:

- page 1 has the case header and 10 creditor boxes;
- page 2 is a continuation page with 20 boxes.

3c commits those two pages as a template with a field index, a schema and a `FORM_REGISTRY` entry. It is then an ordinary templated form: startup check forms.E001 applies unchanged, and page 2 is copied as rows need. The list is built from the D, E/F, G and H rows, notice parties and codebtors included. The district fixture's LR 1007-1 text is corrected.

The template's header prints "EASTERN DIVISION". The 3c spec decides how a Western Division filer's list is headed; 3e1's county tells which division applies.

**Encryption `[Q7.claims]`.** These columns are encrypted, with their data migration:

- `DebtInfo`: `creditor_name`, `monthly_payment`, `notes`, `collateral_description` and `date_incurred`;
- every column of `Codebtor`;
- `ExecutoryContract`: `counterparty_name` and `description`.

`DebtInfo.Meta.ordering` (`["priority_classification", "-amount_owed"]`, `models.py:547`) moves to Python with them.

**Wizard fixes.**

- `[DIG-280]` fixes three misleading wizard texts.
- `[DIG-281]` saves contract and codebtor edits on Go Back, not only on Continue.

**Packet size.** Every filer's packet gains one form, the List of Creditors. The CLAUDE.md packet range ("14–16 forms") is rewritten here, after its earlier rewrite in 3f.

**Counsel.** C-1 rules on co-owned collateral value. C-9 `[C-9]` covers the status definitions, the "Do you owe money on this now?" wording, who belongs on the List of Creditors, and whether the filer's own name goes first.

### 5.10 PR 3d: priority

**Priority, asked in E/F's words `[Q15]`.** For each unsecured debt the filer answers E/F Part 1's question, "Is this one of these?". The four types are:

- domestic support obligations;
- taxes and certain other debts owed to the government;
- claims for death or personal injury while intoxicated;
- other (specify).

Counsel reviews the plain definitions and the "Not sure" wording `[C-2]`.

- **"Not sure":** the debt stays in Part 2, with a legal-aid note.
- **A priority debt:** the filer types the priority and nonpriority split from the creditor's statement; a blank prints blank. They also give the amount past due on the filing date, for 122A-2 line 35. The form says "Do not include current or ongoing priority claims".
- **Storage.** `is_priority` is encrypted when first written, and it is the only stored answer.
- **Out:** deriving priority from the debt's category. That would be a legal characterization (§4.1).

**Stop writing `priority_classification` `[DIG-119]`.** The category-to-priority mapping and the `priority_classification` writes go. The wizard stops calling student loans "priority".

E/F's priority totals then print. 3d lands before 3h, so 122A-2 lines 41–42 can be computed.

### 5.11 PR 3g: Schedule C

**The Schedule C package `[Q23]`.**

- **Line 1.** The filer picks the set of exemptions in the form's words. Plain notes beside it cover 735 ILCS 5/12-1201 and the 730/180-day domicile rule, and point to legal aid.
- **Laws (C-CATALOG).** One list of Illinois and federal nonbankruptcy exemption laws, in statute order, with plain summaries and printed limits. Every item gets the same list, plus a free-text "another law". DigniFi never filters or suggests laws per item.
- **Amounts (C-LIMITS).** The filer gives an amount, or "100% of fair market value, up to any applicable statutory limit". Neutral per-law totals sit beside each statute's limit, with no warning and no block.
- **Stacking (C-STACK).** One row per item and law.
- **Homestead (C-HOMESTEAD).** Lines 3 and 3-1 are asked, never derived.
- **Data.** The law catalog and its amounts are dated data (§4.3). The Illinois amounts are checked against the statute before loading.
- **Gate.** Schedule C's `requires()` refuses until the filer has made the exemption choice.
- **Rows.** Rows past page 1 go on copies of Part 2 (3a2).

**Counsel `[C-8]`:**

- the law summaries;
- the wording of the per-law limits;
- the 12-1201 and domicile notes;
- ILND's practice on stacking.

### 5.12 PR 3h: 122A-2 and the means test

**One calculator `[DIG-152]` `[DIG-146]`.** One calculator produces both the in-app verdict and every 122A-2 line, from the dated tables in force on the fill date. Missing data never becomes zero: a line with a missing input prints blank, and so does every result that depends on it. The dead `_means_test_disposable_income` goes. DIG-146's verdict bands come from the same calculation.

**The IRS standards `[OQ9.standards]`.** The national and local standards are loaded as dated data. The local ones are read by the county 3e1 stores, for 122A-2 lines 8, 9a and 12.

**From the links `[Q13.122a2]`.** 122A-2 lines 9b, 11, 13, 33 and 34 come from 3c's debt-to-property links and vehicle leases.

**Deductions only above-median filers see `[Q4.122a2only]`.** The deductions that appear only on 122A-2 (lines 25–31 and the opt-ins below) are asked in a details step that only above-median filers see. 122A-2's `requires()` refuses until that step is done.

**Opt-in deductions `[Q18]`.** The filer opts in to each claimable deduction in the form's words: lines 15, 22, 25 and 26–31.

- Computed figures and caps are shown as information, such as line 30's 5% cap and line 22's excess over 7g. Only what the filer claims prints.
- Line 10 stays blank, since it would be a legal argument. Line 43 is step 4.
- Counsel reviews the help text `[C-4]`.

**The result boxes `[Q19]`.** DigniFi ticks `CheckBox14` (line 40), `CheckBox15` (line 42) and page 1's `CheckBox1` from the form's own arithmetic. One comparison function serves the boxes and the in-app verdict, as DIG-136 did for the median.

- At exactly $17,150, DigniFi follows the form's wording. Line 40 says "more than $17,150" for box 2, so $17,150 goes on to line 41. Counsel confirms `[C-5]`, since the statute says "not less than".
- The boxes print only when every input under them was given. Otherwise they stay blank, and the app says the result can't be worked out yet.

**Line 36 `[Q20]`.** The filer answers Yes or No in the form's words.

- Beside it, as information: the Bankruptcy Basics link the form names, the § 109(e) limits (dated) and the filer's own debt totals.
- On Yes, the filer enters a projected monthly plan payment. DigniFi prints the district multiplier from the USTP list (dated) and the product.
- The app never decides Chapter 13 eligibility; regular income is a legal conclusion.
- Counsel reviews the help text, and rules on whether the app may say anything about estimating a plan payment `[C-6]`.

**Tickets.**

- `[DIG-275]`: line 35 divides the past-due priority amount by 60, inside the one calculator.
- `[DIG-276]`: the under-65 split comes from the household's ages.
- 122A-2 line 3's marital adjustment (the part of the spouse's income not used for the household's expenses) is asked in the form's words, and it applies only when 3e1 has spouse figures.

**Rows.** 122A-2 rows past the form's capacity go on 3a2's attached sheet.

## 6. Testing and the oracle

### 6.1 The oracle, rebuilt in 3a2

- **Reading back.** Every check reads the printed page inside each widget's exact rectangle from the field index (PyMuPDF `get_text(clip=rect)`). The spike showed a looser window is unreliable: checkboxes sit 11 pt apart, and a ±4 pt window caught a neighbour's X. Text is read as text. A checkbox counts as ticked when its mark is inside its own box.
- **Tier 1 (sentinels).** A unique value goes into every widget. The read-back proves each value prints in its own box, with nothing spilling over and nothing bleeding between shared names. Tier 1 now covers the shared-name boxes the old filler could not separate.
- **Tier 2 (bindings against the audit).** The idea is unchanged. Every new placement ships with its audit addendum row. Repeated rows are checked one row at a time.
- **Tier 3 (personas' printed values).** It extends to continuation copies and attached sheets.
- **Known defects.** The list moves to the new reading and stays `[]`. Flattening removes the checkbox `/AS` state, so tier 1's checkbox reading and the `pdf_field` keys in `known_defects.json` are rewritten, not adjusted. Step 2's tests that assumed fillable fields are rewritten, not deleted.
- **Filed forms.** A test proves a filed form's download redraws its stored page copies exactly.

### 6.2 New kinds of test

- **Capacity.** For every repeated part, a synthetic case one row past capacity proves three things: the extra page or sheet appears, the numbering continues, and the totals include every row.
- **Dated data.** With the fill date pinned, the right table applies on each side of a change date: March 31 and April 1, October 31 and November 1. A lapsed table refuses, and nothing follows the real calendar.
- **Encryption.** Each migration encrypts existing rows, and the stored column holds ciphertext, not the value.
- **The calculator (3h).** Every 122A-2 line is checked from its inputs. The bands are tested at $10,274.99, $10,275.00, $17,150.00 and $17,150.01, along with the line 42 equality. A missing input leaves its line and the result blank.
- **The filer decides.** No answer is pre-selected except the approved one, and no information text says "you qualify".
- **E2E.** The six persona journeys run, plus the SOFA and scanned-bill journeys. The sixth persona's nine creditors drive the overflow path in a real browser.

Tests are named for what they protect, such as `extra_creditors_print_on_a_second_page`, not for functions.

## 7. Personas

The owner chose (Q28) to have the persona updates drafted for review `[Q28.drafts]`. There are two kinds:

- updates to the five existing briefs;
- a sixth persona, a gig driver.

All figures are synthetic, and SSNs use only the 900 range. The owner approved the drafts with this spec on 2026-10-16 `[Q28.drafts]`. Every private creditor, notice party and lender has a fictional name. Government creditors keep their real names and public addresses: the IRS and the Illinois Tollway.

The approved drafts are committed as one companion document beside this spec: `docs/superpowers/specs/2026-10-16-forms-step3-personas.md`. It is the target. The briefs in `docs/testing/persona-briefs/` change only as each PR lands, and each PR applies only its own slice, together with the seeds and journeys that need it. A brief never runs ahead of its seed again, the mistake behind DIG-129.

**What the five gain:**

- spouse figures for Priya and DeShawn;
- deductions matching each brief's take-home pay;
- James's and DeShawn's secured loans linked to their property;
- Priya's $450 car payment resolved;
- a priority debt, a contract, a codebtor, a notice party, addresses and a county wherever the stories fit.

**The sixth persona** covers the rest end to end:

- a gig driver with a leased car;
- co-owned property securing a debt, so Schedule D Column B is blank with the note;
- more than six nonpriority creditors, so E/F overflows onto a copied page;
- a notice party and a codebtor;
- a new E2E journey.

The persona is below median, so 122A-2 does not apply. Priya remains the only above-median persona.

## 8. Process and risks

### 8.1 Branches and reviews

- This spec, the persona drafts and the relicence go to `develop` as one small PR (#25), so the licence and the plan land first. Each of the ten PRs then branches from `develop`.
- **Each PR's cycle:**
  1. a short spec drawn from this one, asking the owner only the judgment calls it leaves open;
  2. a plan;
  3. a subagent-driven build, with a review after every task and a final review of the whole branch;
  4. the owner's yes to push and to merge.
- Promotions follow the branch model: `develop` to `main` to `prod`, by fast-forward only. Only the owner deploys.

### 8.2 Risks

1. **3a2 changes how every form prints.** It is the riskiest PR. The mitigations:
   - two flattening spikes already pass;
   - the oracle is rebuilt before any form switches over;
   - Generate All is timed against the Eco dyno (DIG-137);
   - filed forms redraw exactly what was filed;
   - the font decision covers names the built-in font can't draw.
2. **Counsel throughput.** There are ten counsel items (§9), plus a review of the licence change. They block production, not merges.
3. **Tables with no fixed change date.** The IRS standards and Illinois exemption law are guarded only by the runbook the owner operates (§4.3).
4. **The owner's own intake on production.** After the eventual deploy, the owner's session will refuse to generate until they answer what step 3 added: marital status, household, county, deductions, the A/B line for each old asset, priority answers and addresses. Then they press Complete again. Nothing is lost, but it is real work, so plan for it before relying on the new packet for their own filing.
5. **Size.** 3c (about 690 row boxes) and 3h may each split in their own specs.
6. **The AGPL.** Every new dependency must be AGPL-compatible, the embedded font included (§10).

## 9. Counsel list

Counsel items never block a merge. Each item's wording ships marked as draft until counsel signs off, before production.

| Item | Asked in | PR  | What counsel decides                                                                                                                                                                         |
| ---- | -------- | --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| C-1  | Q14      | 3c  | Which value supports a lien on co-owned collateral in Schedule D Column B                                                                                                                    |
| C-2  | Q15      | 3d  | Plain definitions of E/F Part 1's four priority types, and the "Not sure" wording                                                                                                            |
| C-3  | Q17      | 3e1 | Which reading of "household" 122A-1 line 13 uses (heads on beds, IRS dependents or economic unit); the default is the people who live with the filer                                         |
| C-4  | Q18      | 3h  | The help text for 122A-2's claimable lines 15, 22, 25 and 26–31                                                                                                                              |
| C-5  | Q19      | 3h  | 122A-2 line 40 at exactly $17,150; the default follows the form ("more than"), while the statute says "not less than"                                                                        |
| C-6  | Q20      | 3h  | Line 36's help text, and whether the app may give any guidance on estimating a Chapter 13 plan payment                                                                                       |
| C-7  | Q21, Q22 | 3f  | The wording of the threshold and the filer's figure, and the § 820.20 readings (income, the non-cash deduction, family)                                                                      |
| C-8  | Q23      | 3g  | The Schedule C law summaries, the per-law limit wording, the 12-1201 and domicile notes, and ILND's stacking practice                                                                        |
| C-9  | Q25      | 3c  | The definitions of contingent, unliquidated, disputed and offset; the "Do you owe money on this now?" wording; who belongs on the List of Creditors; whether the filer's own name goes first |
| C-10 | Q26      | 3e2 | The six-month-average and "income now different" wording                                                                                                                                     |

A review of the AGPL relicence is also recommended before `develop` is promoted to `main`.

## 10. Licence

DigniFi is now licensed under the AGPL-3.0-or-later, from PR #25. The owner chose to relicense rather than drop PyMuPDF `[Q29]`, and chose the "or later" variant `[Q30]`.

- **Why.** PyMuPDF, which the document processor already imports (`documents/services/processor.py:42`) and the drawing engine uses, is licensed under the AGPL-3.0 or Artifex's commercial licence. The Elastic License 2.0 appears incompatible with it.
- **Where the licence is declared:**
  - `LICENSE`, the official text from gnu.org;
  - the README;
  - `frontend/package.json`;
  - the root entry of `frontend/package-lock.json`;
  - `backend/pyproject.toml`.
- **Source link.** A network service under the AGPL should offer its users the source, so 3a1 adds the footer link (§5.3).
- **Dependencies.** Every new dependency must be AGPL-compatible.
- **Copyright.** The owner holds copyright in every commit.

## 11. ILND's own checklist

Q1 asked this spec `[Q1.checklist]` to check the packet against ILND's pro se Chapter 7 requirements. The sources, read 2026-10-16:

- "Requirements for a Bare Bone Petition – Pro Se – Chapter 7" (updated January 3, 2025);
- "Additional Documents – Pro Se – Chapter 7" (updated April 1, 2025);
- the "eSR Chapter 7 Checklist";
- B2000, "Required Lists, Schedules, Statements and Fees", in ILND's Guide for Individuals Filing a Bankruptcy without an Attorney (November 2025).

**Forms DigniFi fills, against the court's lists:**

| Court's item                                                    | DigniFi                                                                                                                                             |
| --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Form 101, with email and phone on page 9                        | In the packet; page 9's email and phone are bound                                                                                                   |
| Form 121                                                        | In the packet                                                                                                                                       |
| Names and addresses of all creditors (ILND's List of Creditors) | 3c                                                                                                                                                  |
| Fee: paid in full, Form 103A or Form 103B                       | 3f (line 8 and 103B); 103A in step 4                                                                                                                |
| Form 122A-1 (and 122A-1Supp, 122A-2 where they apply)           | In the packet; 122A-2 completed in 3h                                                                                                               |
| 106Sum, A/B, C, D, E/F, G, H, I, J, 106Dec                      | In the packet; rows in 3b–3g                                                                                                                        |
| 106J-2 (a separate household of Debtor 2)                       | Out: joint filing only                                                                                                                              |
| Form 107                                                        | In the packet; lines 4–6 in step 4                                                                                                                  |
| Form 108                                                        | Step 4; 3c stores its inputs                                                                                                                        |
| Director's Form 2010, the § 342(b) notice                       | Form 101 carries the certification                                                                                                                  |
| Form 119 and Director's Form 2800, a petition preparer's        | Only when a paid petition preparer is used; step 4's paid-preparer question. Whether DigniFi counts as one under § 110 is for the owner and counsel |
| Director's Form 2030, attorney compensation                     | Does not apply: no attorney                                                                                                                         |
| Form 423, the financial management course                       | Filed after the case opens, outside the packet                                                                                                      |

No form the court requires of a single filer at filing is missing from the plan.

**Documents the filer supplies.** DigniFi does not produce these:

- the certificate of credit counseling, received within 180 days before filing. Tracked as DIG-259.
- a copy of the front and back of a photo ID (LR 5005-1 E);
- payment advices from any employer within 60 days before filing;
- the financial management course certificate, after filing.

The last three are not tracked anywhere. One ticket is proposed, to be filed with the owner's yes: DigniFi's filing instructions should list them.

## Appendix A: every decision, mapped to one PR

Every owner answer, controller ruling, ticket and counsel item maps to exactly one PR, the umbrella (U), step 4 (S4) or step 5 (S5). A script kept with the step 3 working notes (`check_spec_tags.py`) checks two things: each item below is tagged in its PR's section of this spec, and this table matches the working map row for row.

| Item               | PR  | What lands                                                                                                                         |
| ------------------ | --- | ---------------------------------------------------------------------------------------------------------------------------------- |
| Q0                 | U   | This umbrella spec, then a spec, plan and build per PR                                                                             |
| Q1.list            | 3c  | ILND's List of Creditors from the D/E/F/G/H rows                                                                                   |
| Q1.108data         | 3c  | The debt-to-property link and a personal-property-lease flag on contracts                                                          |
| Q1.108form         | S4  | Form 108's intentions and the form                                                                                                 |
| Q1.103A            | S4  | Form 103A; until then a "get it from the court" message (3f)                                                                       |
| Q1.checklist       | U   | The packet checked against ILND's pro se Chapter 7 requirements (§11)                                                              |
| Q2                 | 3e1 | Marital status in 122A-1 line 1 terms; the spouse's income by source; CMI = A+B everywhere                                         |
| Q3                 | S4  | Form 107 lines 4–6 (3c supplies debt addresses and stable ids)                                                                     |
| Q4.everyday        | 3e2 | The never-asked Schedule J lines on the Expenses step; one expense model shared with 122A-2                                        |
| Q4.122a2only       | 3h  | 122A-2-only deductions in the details step                                                                                         |
| Q5                 | 3e2 | Business gross, expenses and net; the rental split; interest; the 8a statement on 3a2's sheet generator                            |
| Q6                 | 3e2 | Schedule I 8f asked once on the Income step (103B line 3 reads it in 3f)                                                           |
| Q6.lines11_13      | S4  | Schedule I lines 11 and 13                                                                                                         |
| Q7.assets          | 3b  | Encrypt `AssetInfo` `description` and `financial_institution`                                                                      |
| Q7.claims          | 3c  | Encrypt `DebtInfo`'s plaintext filer columns, `Codebtor` and `ExecutoryContract`                                                   |
| Q7.income          | 3e2 | Encrypt `IncomeInfo`'s ten amounts and `ExpenseInfo`'s 13                                                                          |
| Q7.marital         | 3e1 | Encrypt `IncomeInfo.marital_status`                                                                                                |
| Q8                 | 3a2 | Per-widget drawing and flattening, official continuation copies, the oracle rebuilt, pymupdf pinned                                |
| Q9                 | 3a2 | The attached-sheet generator for forms with no extra page                                                                          |
| Q10                | 3a1 | The dated reference-data model, the lookup, the refusal, the runbook                                                               |
| Q11                | 3a1 | The median fix as the first commit                                                                                                 |
| Q12                | 3a1 | The refusal framework (Complete vs `requires()`, naming the step that fixes it; DIG-181)                                           |
| Q13.link           | 3c  | The debt-to-asset link, Columns B and C, J 17a–17d, vehicle leases with a payment; two duplicate sources retired                   |
| Q13.122a2          | 3h  | 122A-2 lines 9b, 11, 13, 33 and 34 from the links                                                                                  |
| Q14                | 3c  | Column B only for sole-owned collateral; co-owned rows blank with a note                                                           |
| Q14.values         | 3b  | Both A/B values stored (entire, portion)                                                                                           |
| Q15                | 3d  | Priority asked in E/F Part 1's words; the split and the past-due amount; encrypted `is_priority`                                   |
| Q16                | 3e2 | Payroll deductions 5a–5h, filer and spouse; line 7 = 4 − 6                                                                         |
| Q17                | 3e1 | The household list (encrypted); each form's count by its own definition                                                            |
| Q18                | 3h  | Opt-in claimable deductions 15, 22, 25 and 26–31; line 10 blank                                                                    |
| Q19                | 3h  | 122A-2 result ticks from the shared comparison; the form's wording at $17,150                                                      |
| Q20                | 3h  | Line 36 Yes/No, plan payment and multiplier                                                                                        |
| Q21                | 3f  | Form 101 line 8 chosen by the filer; 103B by that choice; routing and off-ramp removed                                             |
| Q22                | 3f  | The threshold and the filer's § 820.20 figure shown as information                                                                 |
| Q23                | 3g  | The Schedule C package                                                                                                             |
| Q24                | 3b  | The A/B package: every line walked, gates derived, the vehicle split, ownership, old rows                                          |
| Q25                | 3c  | The claims package: addresses, notice parties, status, secured, codebtor links, contracts on E/F                                   |
| Q26                | 3e2 | The six-month average plus "income now different?"                                                                                 |
| Q27                | 3e2 | $0.00 for asked-blank lines on Schedule I and 122A-1; the gotcha rewritten                                                         |
| Q28.drafts         | U   | Drafts of the five brief updates and the sixth persona, reviewed with this spec                                                    |
| Q28.names          | 3a1 | Private creditors renamed to fictional names in seeds, briefs and E2E fixture; government creditors keep real names                |
| Q28.data           | 3a1 | The sixth persona's seed and journey skeleton; each later PR adds what its features need                                           |
| Q29                | U   | The relicence lands with the umbrella PR (#25); 3a2's engine uses PyMuPDF                                                          |
| Q30                | U   | AGPL-3.0-or-later; the footer source link lands in 3a1                                                                             |
| OQ9.county         | 3e1 | County asked on the Debtor step, encrypted with the household record; Form 101 County rebinds                                      |
| OQ9.standards      | 3h  | The IRS standards on the dated data, read by county                                                                                |
| CORR.county        | 3e1 | County and the household list kept off `DebtorInfo`; `household_size` left unread                                                  |
| CORR.valid_through | 3a1 | `valid_through` per table; irregular tables guarded only by the runbook; tests pin the fill date                                   |
| CORR.J3            | 3e2 | Schedule J line 3 asked in the form's words on the Expenses step (owner confirmed)                                                 |
| CORR.J45           | 3c  | A homeowner's J line 4 mortgage payment and J line 5 from the debts linked to "my home"; 3e2 does not ask line 5 (owner confirmed) |
| SPIKE              | 3a2 | The engine method (PyMuPDF `insert_text` plus `delete_widget`; exact-clip oracle), replaced by 3a2's spec §3                       |
| DIG-273            | 3a1 | The id round-trip for assets and debts, and the `useAutoSave` baseline                                                             |
| DIG-274            | 3a1 | The median fix                                                                                                                     |
| DIG-275            | 3h  | Line 35's past-due amount ÷ 60 in the one calculator                                                                               |
| DIG-276            | 3h  | The under-65 split from the household's ages                                                                                       |
| DIG-277            | 3e1 | Form 101 County                                                                                                                    |
| DIG-278            | S5  | `IngestedAggregate`'s plaintext gross (or with DIG-176)                                                                            |
| DIG-279            | 3f  | The fee-waiver answers encrypted                                                                                                   |
| DIG-280            | 3c  | The three misleading wizard texts                                                                                                  |
| DIG-281            | 3c  | Contract and codebtor edits saved on Go Back                                                                                       |
| DIG-282            | 3c  | Priya's $450 resolved by the link and the persona update                                                                           |
| DIG-163            | 3a1 | Drafts left out of rows and totals                                                                                                 |
| DIG-188            | 3a1 | The session lock before rows bind                                                                                                  |
| DIG-146            | 3h  | The verdict bands from the one calculator                                                                                          |
| DIG-145            | 3f  | The 150% poverty test as information, no gate                                                                                      |
| DIG-152            | 3h  | One calculator, no zeros for missing data                                                                                          |
| DIG-159            | 3e1 | The household-size cap becomes a limit on the list's length                                                                        |
| DIG-164            | 3b  | Ordering in Python on decrypted values (assets; debts follow in 3c)                                                                |
| DIG-119            | 3d  | `priority_classification` no longer written                                                                                        |
| DIG-123            | 3c  | The pro se List of Creditors and the fixture's text                                                                                |
| DIG-53             | 3e1 | Marital status and the seeds                                                                                                       |
| DIG-223            | 3f  | `_fee_waiver_household_size` fails loud                                                                                            |
| C-1                | 3c  | Co-owned collateral value                                                                                                          |
| C-2                | 3d  | Priority definitions                                                                                                               |
| C-3                | 3e1 | The 122A-1 line 13 household reading                                                                                               |
| C-4                | 3h  | Claimable-deduction help text                                                                                                      |
| C-5                | 3h  | Line 40 at exactly $17,150                                                                                                         |
| C-6                | 3h  | Line 36 and plan-payment guidance                                                                                                  |
| C-7                | 3f  | Fee-waiver wording and § 820.20 readings                                                                                           |
| C-8                | 3g  | Schedule C summaries, limits, notes and stacking                                                                                   |
| C-9                | 3c  | Claim-status definitions and the List of Creditors                                                                                 |
| C-10               | 3e2 | Six-month-average wording                                                                                                          |
| GOTCHAS            | U   | Each PR rewrites the CLAUDE.md gotchas its change touches (§5.1)                                                                   |

## Appendix B: what this spec settles that the sections did not show

1. **3a2's proof.** Section 3 said 3a2 would be proven on Schedule G's existing rows. No production schema has a repeat group (checked 2026-10-16), so 3a2 proves continuation copies and sheets on synthetic schemas. Its production change is the drawing path for every form. The first production rows bind in 3e2, 3b and 3c (§5.4).
2. **The List of Creditors has a template.** ILND publishes a fillable two-page List of Creditors, so it becomes an ordinary registry form with a field index, a schema and continuation copies. Startup check forms.E001 is unchanged. Attached sheets are part of their form's output and need no registry entry (§5.4, §5.9).
3. **Western Division.** The court's template prints "EASTERN DIVISION". The 3c spec decides how a Western Division filer's list is headed (§5.9).
4. **`IncomeInfo` is migrated twice.** 3e1 encrypts `marital_status`, and 3e2 the ten amounts. The spouse's amounts are new data, encrypted from 3e1 (§5.5, §5.6).
5. **Packet counts move.** Every filer gains the List of Creditors in 3c, and 103B follows the line 8 choice in 3f. CLAUDE.md's "14–16 forms" is rewritten in both PRs (§5.9, §5.7).
6. **Where the persona target lives.** The approved drafts are committed as a companion document beside this spec. The briefs change only as each PR lands (§7).
7. **Take-home pay pre-fill.** Q16 allows 3f to pre-fill 103B's take-home pay, and step 2's rule forbids it. The 3f spec puts the conflict to the owner (§5.7).
8. **The dated tables each PR loads.** 3a1 loads only the median. HHS lands in 3f, the exemption law catalog in 3g, and the IRS standards, § 104 amounts and district multiplier in 3h (§5.3). The USTP district multiplier joins Q10's list of dated tables, since Q20 prints it.
9. **ILND's checklist.** Done in §11. It found no form missing at filing, and three documents the filer supplies are untracked. One ticket is proposed.
10. **The marital adjustment is 122A-2 line 3.** The decision record placed it on line 13. The form's own text puts it on line 3, and line 13 is the vehicle ownership or lease expense that Q13 derives from the links (§5.12). Checked against the template on 2026-10-16.
11. **Schedule J line 3 is asked in 3e2.** No answer placed it; the persona drafts found the gap (§5.6). Confirmed by the owner at the spec review.
12. **A homeowner's J lines 4 and 5 come from the linked debts.** Q4 placed line 5 on the Expenses step, and Q13 makes a debt's payment its only source. The spec follows Q13, so 3e2 does not ask line 5 (§5.6, §5.9). Confirmed by the owner at the spec review.
13. **Points from the gig driver's draft,** each left to the PR spec named:
    - a leased vehicle on A/B line 3 (3b, §5.8);
    - costs used for both business and home (3e2, §5.6);
    - his net income and fee answer before 3e2 and 3f (3a1, §5.3);
    - Form 101 line 12, the sole-proprietor question (step 4, §3.2).
14. **How a spouse appears on the household list** (3e1, §5.5). "Claimed on your tax return" is ambiguous on a joint return.
