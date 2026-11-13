# Forms step 3g: Schedule C, the property you claim as exempt

<!-- prettier-ignore-start -->

- **Status:** drafted 2026-11-12. The owner answered four questions on 2026-11-12 and approved the design as played back (§2). Three checks then read the draft: a builder's read, a fact-check against the tree, the template and the statute, and a UPL, reading-level and accuracy review of every drafted sentence. Their findings are folded in. One, where the line 1 notes sit, the copy reviewer called the owner's; the umbrella already approved showing the notes, so this document decides only their position, as Builder's call B14, flagged for the owner in §11. Awaiting the owner's approval of this document.
- **Drawn from:** the step 3 umbrella spec, `docs/superpowers/specs/2026-10-16-forms-step3-design.md` §5.11 (cited `U:<line>`), its rules U §4.1–§4.7, its counsel list (C-8) and Appendix A's Q23 row. Persona targets come from `docs/superpowers/specs/2026-10-16-forms-step3-personas.md` (cited `PS:<line>`), corrected in §3. The October scope report (`.claude/archive/worktrees-2026-11-06/forms-step3/.superpowers/forms-step3/scope/assets-exemptions.md` in the main checkout, cited `SC:<line>`) holds the Q23 options the owner approved. The form's words come from the blank template `data/forms/pdfs/b_106c_0425-form.pdf` (Official Form 106C, rev. 04/25). The law comes from the statutes, read on 2026-11-12 (§5.1).
- **Tree:** develop 80a981d (3d2 merged). Code citations come from a survey of the same tree (worktree `forms-step3d2` at f374bd0, whose tree 80a981d merged unchanged). No test suite ran for this spec; the box measurements in §6.2 were made with `text_fit.fit` on the template.
- **Not read:** the national instructions' Schedule C chunks past the paragraphs §5.1 quotes; the Pension Code articles other than 40 ILCS 5/4-135; the Unemployment Insurance Act's anti-attachment section; 735 ILCS 5/12-1004, 12-1005 and the tenancy-by-the-entirety statutes; 12-1001(j)(1) and (j)'s "account" definition; 11 U.S.C. § 522(n); most federal statutes past 42 U.S.C. § 407 and 38 U.S.C. § 5301 (§5.1 keeps every unread law off the list).
- **Tags** such as `[Q23]` trace to the umbrella's Appendix A. `[UPL]` is the rule that DigniFi gives information, never advice. `[C-8]` is the umbrella's counsel item on Schedule C (written "spec C-8" where it could be confused with controller rulings numbered C-8 in older notes).

Inline "**Builder's call Bn:**" marks a choice this spec makes where the umbrella, the code and the owner leave one open. §11 lists them all, so the owner can check them.

## 1. What 3g does, and why

Schedule C is where a filer lists the property they claim as exempt: for each item, the law that allows the claim and the amount claimed. The form's instructions say it plainly: "Exemptions are not automatic." Today DigniFi asks nothing. Schedule C prints the filer's name and district and nothing else, in every packet, and refuses nothing (`registry.py:183`, `PacketForm(_always, _nothing)`). Its one row binding, `2.2`, reads a plaintext `FormAnswer` that no screen writes (`schedule_c.json:23-39`).

Choosing an exemption is a legal choice. The code DigniFi once had chose for the filer (a deleted generator gave "the homestead statute to any real property, and applied the wildcard exemption to each asset separately"), which is the UPL harm this PR must never bring back. So everything that is the filer's to say is asked in the form's own words, and DigniFi only informs `[Q23]` `[UPL]`.

After 3g:

1. **A page after Complete, "The property you claim as exempt"**, asks line 1 (which set of exemptions), then the claims (an item from the filer's Schedule A/B, a law from one list, an amount), then lines 3 and 3-1 (the homestead questions). Beside the claims it shows a neutral total for each law next to the law's limit.
2. **Schedule C is refused until the page is answered**, with a link to it.
3. **Schedule C prints the claims**: three rows on page 1, twelve on page 2, and copies of page 2 from row 16 on, with lines 1, 3 and 3-1.
4. **The law list carries the Illinois amounts in force since January 1, 2026** (Public Act 104-120), loaded as dated data from the statute's text. The stale, unread figures in the repo go.

Nothing in 3g deploys. Production waits for steps 3 to 5 and DIG-146.

**The failure this must not have.** Schedule C prints a law, an amount, a line 1 tick or a line 3 answer the filer never gave; the page suggests, filters or pre-fills a law or an amount; a limit shown beside a claim is wrong or stale; or a total looks like a verdict. Each of those puts something on a sworn form, or in front of the filer as fact, that is not theirs or not true.

### Goals

- Every Schedule C row, tick and amount comes from the filer's own answer on the page, or is copied from the item's Schedule A/B row (its description, line and value), which is the form's own instruction ("Copy the value from Schedule A/B").
- Every item gets the same law list, in the same order, and nothing on the page is chosen before the filer chooses it.
- Every limit shown is the statute's, read from its text, with the date it took effect and its source.
- A filer with no claims says so on purpose; a skipped page never looks the same as a choice.
- Nothing disappears silently: a claim whose item leaves Schedule A/B stays, and Schedule C is refused until the filer removes or changes it.

### Non-goals

- Debtor 2's boxes, joint filing, the "amended filing" box and the case number. They stay blank, as on every other schedule.
- A list of § 522(d) exemptions or another state's laws. Illinois law bars residents from § 522(d) (735 ILCS 5/12-1201), so the list holds Illinois laws and federal laws outside the Bankruptcy Code's own list, as U:503 says. A filer whose laws are another state's, or who ticks line 1's second box, types each law under "Another law". The list never changes with line 1's answer.
- Any calculation of what an item is worth, what is "covered", or what the trustee may do.
- Form 122A-2's or 122A-1Supp's "exemption" (a different subject, DIG-72) and the means test.

### Anti-goals

- A law suggested, filtered, sorted or pre-selected per item, or a law or amount filled in for the filer.
- Line 1, line 3 or line 3-1 pre-ticked or worked out from the claims.
- An amount pre-filled from a limit, or a "100% of fair market value" claim given a dollar figure.
- A warning, a colour, an alert role or a blocked Continue when a total is over a limit. A total over its limit looks exactly like one under it (C-LIMITS b, SC:211-217).
- Words that judge or predict: "you qualify", "protected", "you keep", "covered", "the best set", or the instructions' "You may lose property if you do not use the best set of exemptions for your situation".

## 2. What the owner decided

Before this spec (umbrella, owner 2026-10-16, Q23 "as recommended"):
- **Line 1** is asked in the form's words, with plain notes on 735 ILCS 5/12-1201 and the 730/180-day rule and a pointer to legal aid (OQ-14 b, SC:194-200; U:502).
- **One law list** in statute order, the same for every item, plus a free-text "another law"; never filtered or suggested (C-CATALOG a, SC:202-209; U:503).
- **Amounts:** a dollar figure or "100% of fair market value, up to any applicable statutory limit"; neutral per-law totals beside each law's limit, no warning and no block (C-LIMITS b; U:504).
- **One row per item and law** (C-STACK a; U:505).
- **Lines 3 and 3-1 asked, never derived** (C-HOMESTEAD a; U:506).
- **Dated data**, the Illinois amounts checked against the statute before loading (U:507); the gate in Schedule C's own `requires()` (U:508, U:121-122).
- **Counsel `[C-8]`** reviews the law summaries, the per-law limit wording, the 12-1201 and domicile notes and ILND's stacking practice (U:511-516). Counsel items never block a merge; the wording ships marked draft (U:9, U:189, U:633).

In this design (owner, 2026-11-12):
- **Where:** a page after Complete, between the filing-fee page and the Statement of Financial Affairs, not a wizard step and not inside the Assets step ("1").
- **No claims:** a filer who adds no claims presses "I'm not claiming any property as exempt", as "I have no amounts owed" works on the Amounts Owed step ("a").
- **The page as played back**, including: the description, line and value copied from Schedule A/B when the form is made; a shorter description asked only when the A/B one won't fit; a claim whose item leaves Schedule A/B staying until the filer removes or changes it; the 2026 figures; "100% of fair market value" rows counted, not valued; a typed law shown with no limit; the personas recalculated by the companion's own rule; a synthetic 16-row case for the copy pages ("nothing, it looks good to me").
- **Two PRs:** 3g1 asks, 3g2 prints ("let's do 2").

## 3. Spec corrections

The survey found these places where the umbrella or the persona companion is wrong today:

1. **Copies start at row 16, not row 4.** U:509 says "Rows past page 1 go on copies of Part 2". The template's page 2 *is* Part 2's first "Additional Page", with 12 rows (3 on page 1, 12 on page 2). The engine requires a group's `extra_page` to be the page of its last slots (`apps/forms/schema.py:574-585`), so the template's own page 2 holds rows 4–15 and copies of page 2 hold rows 16 on, 12 a copy (`_copies`, `fill_resolver.py:698-727`). No persona has more than 9 claims, so no persona prints a copy (§6.5 adds a synthetic case).
2. **The Illinois amounts changed on January 1, 2026.** Public Act 104-120 (SB1738, effective 2026-01-01) set the homestead exemption at $50,000 per person, with co-owners limited to their share of $100,000 (735 ILCS 5/12-901), the vehicle exemption at $3,600 (12-1001(c)) and tools of the trade at $2,250 (12-1001(d)); the "any other property" exemption stays $4,000, of which $1,000 is automatic under the new 12-1001.1 (12-1001(b)). The repo's `ExemptionSchedule` fixture holds $15,000, $2,400, $4,000 and $1,500, undated and read by nothing (`ilnd_2025_data.json:56-103`), with "can double this" sentences that are stale and advice-shaped. The companion used the fixture for Maria and DeShawn and the 2026 figures for James and Andrés (PS:264, PS:320, PS:1438). §6.4 recalculates every persona on the 2026 figures.
3. **The companion's A/B line labels.** PS cites "17.1", "17.2" and "21.1" for checking, savings and the 401(k). Schedule A/B prints a filer's first checking account at 17.1, the first savings account at **17.3** and the first 401(k) at **21**: line 21's "401(k) or similar plan" box is the line's own (the index gives it `line: "21"`; "21.1" is only the widget's name), and rows past A/B's boxes print on its attached sheet as "17c.{n}", "17s.{n}", "21k.{n}" (`schedule_a_b.json` groups `ab_17_checking`, `ab_17_savings`, `ab_21_401k`). Schedule C's "Line from Schedule A/B" prints what A/B prints, without the trailing dot the template draws after its own numbers (§6.2), so Priya's and Andrés's savings rows cite 17.3 and the 401(k) rows cite 21.
4. **DeShawn's watch item** (PS:916: "his equity ($20,000) is more than the homestead amount he typed") rested on the old $15,000 limit. Under $50,000 he claims his equity (§6.4), and the item is rewritten.
5. **"Gate" means more than line 1.** U:508 says Schedule C refuses "until the filer has made the exemption choice". This spec's gate (§5.5) also covers the claims (or the "not claiming" answer) and lines 3 and 3-1, which the form needs answered to print.

## 4. Two PRs

- **3g1 asks and stores.** The law list and its data migration; the records and the endpoint; the item names and A/B labels the page shows; the page and its place in the flow; the "not claiming" answer; the gaps and Schedule C's refusal; the personas' seeded answers; the journeys walking the page; retiring `ExemptionSchedule`. Schedule C refuses until the page is answered, and prints nothing new yet.
- **3g2 prints.** Schedule C's rows (a repeat group of 15 slots continued on copies of page 2), lines 1, 3 and 3-1, page numbers, the oracle tiers, the synthetic 16-row case, and the old `2.2` binding's removal.

Between the two, a filer's claims print nowhere. Nothing deploys, so no filer meets that.

## 5. 3g1: ask and store

### 5.1 The law list

**What is on it.** Illinois laws, then federal laws, each in statute order (Illinois by chapter, act and section; federal by title and section). Only a law whose text was read in the statute itself goes on the list; each entry carries its own source URL. A law that could not be read stays off and is listed for counsel (§7); the filer can still type it under "Another law". On 2026-11-12 these were read:

| Key (Builder's call B1) | Citation printed | What the law covers (from its text) | Limit sentence (draft, B15) |
| --- | --- | --- | --- |
| `il_40_5_4_135` | 40 ILCS 5/4-135 | Firefighters' pension fund benefits | none |
| `il_215_5_238` | 215 ILCS 5/238 | Life insurance and annuity proceeds and cash value payable to a spouse, child, parent or other dependent | none |
| `il_305_5_11_3` | 305 ILCS 5/11-3 | Public aid under Articles III, IV, V and VI, and certain child care payments | none |
| `il_735_5_12_901` | 735 ILCS 5/12-901 | Homestead | "Up to $50,000 for each person. When 2 or more people own the home, each is limited to their share of $100,000, by percentage of ownership." |
| `il_735_5_12_1001_a` | 735 ILCS 5/12-1001(a) | Household goods and personal possessions | "No total limit. A creditor may ask the court to take any one item with a resale value over $5,000, unless another part of this section exempts it. One piece of jewelry is exempt up to $5,000." |
| `il_735_5_12_1001_b` | 735 ILCS 5/12-1001(b) | Equity in any other property | "Up to $4,000." |
| `il_735_5_12_1001_c` | 735 ILCS 5/12-1001(c) | One motor vehicle | "Up to $3,600 in one motor vehicle." |
| `il_735_5_12_1001_d` | 735 ILCS 5/12-1001(d) | Implements, professional books or tools of the trade | "Up to $2,250." |
| `il_735_5_12_1001_e` | 735 ILCS 5/12-1001(e) | Professionally prescribed health aids | none |
| `il_735_5_12_1001_f` | 735 ILCS 5/12-1001(f) | Life insurance proceeds and cash value payable to a spouse, child, parent or other dependent | none |
| `il_735_5_12_1001_g1` … `_g4` | 735 ILCS 5/12-1001(g)(1) … (g)(4) | The right to receive: (1) social security, unemployment or public assistance benefits; (2) a veteran's benefit; (3) a disability, illness or unemployment benefit; (4) alimony, support or separate maintenance | (1)–(3) none; (4) "Only what the person and their dependents reasonably need to live on." |
| `il_735_5_12_1001_h1` … `_h5` | 735 ILCS 5/12-1001(h)(1) … (h)(5) | The right to receive, or property traceable to: (1) a crime victim's reparation award; (2) a wrongful death payment; (3) a life insurance payment; (4) a personal bodily injury payment; (5) Civil Liberties Act restitution | each ends with the time rule T; (2) begins "Only what the person reasonably needs to live on."; (3) begins "Only what the person and their dependents reasonably need to live on."; (4) begins "Up to $22,500." |
| `il_735_5_12_1001_i` | 735 ILCS 5/12-1001(i) | A crime victims' award under Part 20 of Article II | none |
| `il_735_5_12_1001_j` | 735 ILCS 5/12-1001(j) | Illinois College Savings Pool and ABLE accounts, except the contributions the statute lists | drafted once (j) is read in full |
| `il_735_5_12_1006` | 735 ILCS 5/12-1006 | An interest in a retirement plan | none |
| `il_820_305_21` | 820 ILCS 305/21 | Workers' compensation payments, claims and awards | none |
| `us_11_522_b3c` | 11 U.S.C. § 522(b)(3)(C) | Retirement funds in an account exempt from tax under the Internal Revenue Code sections it lists | none |
| `us_38_5301` | 38 U.S.C. § 5301 | Veterans' benefits | none |
| `us_42_407` | 42 U.S.C. § 407 | Social Security benefits | none |

The time rule T, from (h)'s closing words: "The right to a payment is exempt for at most 2 years after the right accrues. Property traced to the payment is exempt for at most 5 years after the payment accrues, and only up to its amount." It keeps the statute's "accrues": a right can accrue long before a payment is due, so a plainer "owed" would move the start date. Each limit sentence was scored with the reading-level formula on 2026-11-12 (the highest, (h)(3) with T, at 7.6).

The builder re-reads every entry's text on the day it loads and records the source URL per entry; 12-1001(j)(1) and the subsection's "account" definition were read only in part on 2026-11-12, so (j) loads only after they are read (or stays off). 40 ILCS 5/8-243, which common lists give for Chicago municipal pensions, is a section on aldermen and is **not** loaded; 820 ILCS 405/900 is "Recoupment and recovery" and is **not** loaded (§7 asks counsel for the right cites).

**Stored as dated data** (U §4.3). **Builder's call B2:** a national dated table in `apps/districts`, as `PovertyGuideline` is:
- `ExemptionCatalog(DatedTable)`: one row per version of the list, with `effective_date` 2026-01-01, `valid_through` empty, and `source_url` the enrolled Public Act (`https://www.ilga.gov/documents/legislation/publicacts/104/PDF/104-0120.pdf`). `in_force(ExemptionCatalog.objects.all(), fill_date(), EXEMPTION_TABLE)` picks the version, so the existing lookup and its logged refusal apply unchanged.
- `ExemptionLaw`: the catalog's rows: `catalog` (FK), `key` (stable across versions), `position` (statute order), `jurisdiction` (`illinois` or `federal`), `citation` (the text Schedule C prints), `limit_text` (the law's limit sentence from the table above, or empty when the law names no limit), `source_url` (the section's page). Unique on (`catalog`, `key`). No separate figure column: nothing compares a total with a limit (C-LIMITS b), so the figure lives only in its sentence.
- The rows come from a data migration (`0006_exemption_catalog_2026` or the next free number), the poverty pattern (`0005_poverty_guideline_2026.py`): a module-level copy of the rows, never imported from app code, a `# DRAFT: counsel C-8` mark on the limit sentences, and a reverse that deletes the version. Every database, CI and the Heroku release then have the rows without `loaddata`.
- `valid_through` stays empty: Illinois exemption amounts change only by Public Act, with no schedule to refuse on, so the runbook is the only guard (U:107). A test pins that the 2026 version's `valid_through` is empty on purpose, beside the twins of `test_poverty.py`'s figure pins.
- A root `backend/conftest.py` fixture, `exemption_catalog_2026`, puts the migrated rows back for a test after a transactional test's teardown, as `poverty_2026` does.

**No catalog in force.** `in_force` raises `NoTableInForce`, whose fixed sentence names income figures (`dated_tables.py:44-50`). **Builder's call B3:** the exemption table gets its own sentence, "DigniFi doesn't have the exemption laws for today's date yet, so it can't prepare Schedule C." (grade 8.6; no "try again later", since with the 2026 version open-ended only a date before 2026-01-01 reaches it), through a message parameter or a subclass, and the page shows its own version of it in place of the law list.

**The words the filer reads.** Each law shows its citation, a one-sentence summary and its limit sentence:
- **Summaries** are DigniFi's sentences, so they live in `copy.ts` as `EXEMPTION_LAW_SUMMARIES` (keyed by `key`), are scored by the reading-level test, carry `// DRAFT: counsel C-8`, and contain no dollar figure and no "you" (**Builder's call B4**). They say what the law covers in the statute's own terms and examples, never apply it to the filer, and never name an account or item kind the statute does not name. Drafts, each scored: 12-1001(a) "Things in a home and things a person owns, such as furniture, clothes, pets, phones and computers." (7.7); (b) "The equity in any other property, up to the limit. Equity is what the property is worth, less what is owed on it." (6.3); (c) "One motor vehicle, up to the limit." (5.7); (d) "Tools, books and equipment for a person's trade or profession." (5.9); 12-1006 "Retirement plans, such as a pension plan or an IRA." (4.8); 12-901 "A home that a person owns or holds by lease and lives in, such as a house, a condo or a co-op, up to the limit." (8.5). The plan drafts the rest under the same rules. A backend test pins that the keys of every catalog version in force have a summary and that every summary has a key, as `test_claims_frontend_copy.py` pins the claims words.
- **Limit sentences** come from the catalog in the endpoint's reply (`limit_text`). **Builder's call B15:** plain sentences per law that state the limit's own unit (per person, in one vehicle, per resale item), not the statute's sentences in quotation marks: the quoted clauses score grade 11 to 25 and say "the debtor" throughout, and a figure shown without its unit invites a comparison with a total that the law does not make. They are dated data, not `copy.ts`, because a new Public Act changes them with the figures; so no frontend test scores them, and a backend test scores every catalog sentence with a port of the reading-level formula (grade 9 or below) and the `ADVICE` patterns except the `$` one, the port pinned to the frontend's by a shared case file both run (the `linkedPaymentCases.json` pattern). A law whose `limit_text` is empty shows "This law names no dollar limit." (`copy.ts`, 4.5), which therefore never shows for 12-1001(a). The (b) sentence leaves out the statute's "of which $1,000 is an automatic exemption pursuant to Section 12-1001.1": 12-1001.1 is a collection-procedure rule, and stated bare it suggests part of a claim needs no claim (counsel decides, §7).

**Retiring the old data (DIG-286).** The `ExemptionSchedule` model and its four fixture rows go (a migration drops the table; `ilnd_2025_data.json` loses lines 56–103), and `backend/apps/forms/fixtures/illinois_exemptions_2024.json`, which nothing loads, is deleted.

### 5.2 Records

Both are encrypted from the start (U §4.2) and are not intake data: like `FilingFee`, saving them never reopens a completed intake (`models.py:1064-1105`).

- **`ExemptionAnswers`**, one-to-one with the session (`related_name="exemption_answers"`):
  - `line_1`: `state_and_federal` (the form's "You are claiming state and federal nonbankruptcy exemptions. 11 U.S.C. § 522(b)(3)") or `federal` ("You are claiming federal exemptions. 11 U.S.C. § 522(b)(2)"); null unanswered.
  - `line_3`, `line_3_1`: `yes`, `no` or null.
  - `no_claims`: true only after the filer presses "I'm not claiming any property as exempt"; false or null otherwise.
- **`ExemptionClaim`**, one row per item and law (C-STACK):
  - `session` (FK, cascade); `asset` (FK to `AssetInfo`, null, `on_delete=SET_NULL`), live only when it names a row of this session (`link_is_live`, `claims.py:188-190`);
  - `law` (an `ExemptionLaw.key`) or `other_law` (the filer's typed law), never both;
  - `amount_kind`: `dollars` or `fair_market_value`, null unanswered; `amount` (`EncryptedDecimalField`, at or above 0, `DecimalField(12, 2)` on the serializer), only under `dollars`;
  - `short_description`: the filer's shorter description, null unless asked for (§5.4).

  Every column but the FKs is encrypted, so the server orders rows in Python (U:86). Ids are server-assigned and never reused.

**Builder's call B5:** a claim row table with an FK, not an encrypted JSON list, because the FK's `SET_NULL` is exactly "the claim stays when its item goes", and the item's description, line and value are read through it when the form is made.

**Builder's call B17:** a claim follows its item. If the filer moves the item to another Schedule A/B line, the claim keeps its law and amount, and its printed line and name follow the item; no gap is raised, because whether a law fits an item is the filer's call (U §4.1), never DigniFi's. A form already marked filed keeps its stored values (the existing rule); nothing new shows on the dashboard.

### 5.3 The endpoint

`GET` and `PUT /api/intake/sessions/{id}/exemptions/`, an `@action` on the session viewset like `filing-fee` (`views.py:568-590`), for a session in any status:

- **GET** returns the answers, the claims in print order (§6.1) with ids, and:
  - `items`: the session's Schedule A/B rows with a line, in `ordered_assets` order (`asset_lines.py:157-174`), each with its id, `name` (B12), `line_label` (B13), `value` (B16, a decimal string, or null when A/B prints none) and `description_fits` (whether `name` fits Schedule C's description box, B6);
  - `catalog`: `{effective_date, source_url, laws: [{key, citation, jurisdiction, limit_text}]}` for the version in force on the fill date, or null with `catalog_gap: "no_table"`.
- **PUT** takes `{line_1, line_3, line_3_1, no_claims, claims}` and sets only the keys sent; `claims`, when sent, is the whole list (a stored claim missing from it is deleted; a claim sent with one of this session's claim ids updates it; any other gets a new id). It calls `get_object()` first (another user's session is a 404), then locks the session inside `transaction.atomic()` before reading anything (`lock_session`), checks every claim before writing any, never calls `reopen()`, and replies with the GET body, claims in the order sent.
- **A 400** for: an unknown key; a `line_1` outside its two answers; a `line_3` or `line_3_1` outside `yes`/`no`; a claim with both `law` and `other_law`; a `law` key that is not in the catalog in force; an `amount_kind` outside its two; a negative amount or one too wide for `DecimalField(12, 2)`; an amount sent under `fair_market_value`; an `other_law` that does not fit Schedule C's law box at 6 pt or a `short_description` that does not fit its description box (B6); `no_claims` true beside any claim; more than 100 claims (Builder's call B7: 15 slots plus 99 pages' worth of copies is far more; 100 bounds the reply).
- **An asset id** that names no row of this session saves as no link (the `secured_by` rule), and the gap in §5.5 names it.
- The lock test's `WRITES` (`test_session_lock.py`, marker `postgres`) gains the PUT.

**Builder's call B6: fit is measured by the server, live.** Text the filer types (`other_law`, `short_description`) is refused on PUT unless it fits its Schedule C box at 6 pt, measured with `text_fit.fit` (DIG-480's lesson: a saved answer must never fail at Generate). An item's `name` can change on the Assets step after a claim is saved, which neither reopens nor re-checks claims, so `description_fits` is worked out again on every GET and in the gate, never stored. One measurement serves every row: the description boxes are 97.3 pt wide on both pages (page 1's 11 pt tall, page 2's 13 pt), and the shorter box is the one measured. Mixed text fits about 19 characters at 10 pt and 31 at 6 pt.

**Builder's call B12: the item's name.** The name the page, the gaps and Schedule C's description box use is the row's description; else, on lines 3 and 4, its make, model and year ("Honda Civic 2015"); else, on line 1, its street; else a short name for the line ("Cash" on line 16, whose rows have no text box). Never "one item": `_row_name` (`asset_lines.py:259-267`) gives "Honda" for a seed car and "one item" for cash, which Schedule C would print. The builder writes a short name for each catalog line whose complete rows can lack a description (`_row_is_complete`, `asset_lines.py:229-256`), in the form's words; the new function lives beside `_row_name`, which Review keeps using.

**Builder's call B13: the line label comes from Schedule A/B's own schema.** A function reads `schedule_a_b.json`'s groups (each group's slots and the line each slot prints, its capacity, and the attached sheet's `number` format) and gives each row the label A/B prints for it: the form's own number for a row in one of A/B's boxes ("3.1", "6", "17.1", "17.3", "21"), else its sheet number ("3.5", "17c.3"), always without the trailing dot. Reading the schema, not a copy of it, keeps the two forms from drifting; a test pins the label of every persona row against what A/B itself prints for that row.

**Builder's call B16: the value is A/B's.** `value` is exactly what Schedule A/B prints in that row's "portion you own" box (`ASSET_CELLS` `value`, `fill_resolver.py`), blank when A/B prints it blank (U §4.5); a co-owned row whose portion is unknown has no value here either.

### 5.4 The page

**Route and flow.** `/exemptions`, `ExemptionsPage.tsx`. The filing-fee page's Continue goes to `/exemptions` instead of `/sofa` (`FilingFeePage.tsx:156`), and the exemptions page's Continue saves and goes to `/sofa`. The forms dashboard links to it from every Schedule C refusal (`PAGE_LINK_LABELS['/exemptions'] = 'Go to The property you claim as exempt'`, `FormDashboard.tsx:67-72`). Like the filing-fee page, it reads first and renders nothing editable until the read returns, offers "Try again" on a failed read, keeps its answers in its own state and saves only on Continue (no autosave).

**Top to bottom** (every DigniFi sentence below is in `copy.ts`, marked `// DRAFT: counsel C-8`, with its grade):

1. **The heading and a short introduction:** "On Schedule C, you list the property you claim as exempt. For each claim, you choose the law and the amount. The limits shown here come from the laws themselves." (3.7) `UPL_EXEMPTION_DISCLAIMER` (`upl.ts:35-37`) shows inline, as on the Assets step.
2. **Line 1**, a fieldset in the form's words (`formText.ts`): the question "Which set of exemptions are you claiming? Check one only, even if your spouse is filing with you." and both choices as radios, neither selected. **Builder's call B14:** the two notes follow both choices, as one block, never before or between them, so neither reads as a comment on one box; and the second note carries both halves of the rule:
   - "The Illinois law 735 ILCS 5/12-1201 says residents of Illinois are prohibited from using the federal exemptions in 11 U.S.C. § 522(d), except as Illinois law otherwise permits." (7.8; the statute's own words, not a paraphrase)
   - "Which state's laws apply depends on where you have lived. The rule, in 11 U.S.C. § 522(b)(3)(A), looks at where your legal home was for the 730 days before you file. If it was not in one state that whole time, the rule looks at where it was for most of the 180 days before that. If that rule leaves a person with no exemptions at all, the person may use the list in 11 U.S.C. § 522(d) instead. Legal aid can help you find out which set is yours." (2.0; "legal home" is the form's own term for domicile; "most of the 180 days" is counsel's to confirm, §7)
3. **The law list**, once, in statute order: each law's citation, summary and limit sentence (§5.1), under the headings "Illinois laws" and "Federal laws". **Builder's call B8:** the list shows once on the page, and each claim's law control is a native `<select>` of the same laws in the same order (citation only), plus "Another law", so every item meets the same list and a phone shows it without a custom widget.
4. **The claims.** "Add a claim" adds a row; each row asks, in order:
   - the property: a native `<select>` of `items`, each shown as its name and its A/B line ("Honda Civic 2015 (line 3.1)"), none selected;
   - the law: the select above, none selected; under "Another law", a text box;
   - the amount: radios "A dollar amount" (with its box) and the form's "100% of fair market value, up to any applicable statutory limit", neither selected;
   - Remove.

   One item may take several rows, one per law (C-STACK). A row whose item's name doesn't fit (`description_fits` false) shows "This description is too long for the box on Schedule C. Type a shorter one for this form." (3.0) and a box for `short_description`. A row whose item has left Schedule A/B (no live link) shows "This claim was for property that is no longer on your property list. Its law and amount are still here. Remove the claim, or choose the property again." (4.1), with its law and amount kept. When `items` is empty (Sarah), the claims part says "No property is listed on the Assets step yet, so there is nothing to claim here." (6.1) and shows no "Add a claim".
5. **The totals**, for each law used, in list order: "Amounts entered under this law: {amount}" (8.4 as a template), then, when any row under it is "100% of fair market value", "{n} more claimed at 100% of fair market value, up to any limit the law sets." (5.0 with a number), then the law's limit sentence, or "This law names no dollar limit." A typed law shows its total and no limit line. Every total uses the same plain text style, inside a region that is no alert; over and under a limit look the same (C-LIMITS b).
6. **"I'm not claiming any property as exempt"**, a toggle button shown while no claim row exists (the `no_debts` pattern). Adding a claim clears it.
7. **Lines 3 and 3-1** in the form's words (`formText.ts`): "Are you claiming a homestead exemption of more than $214,000?" with "(Subject to adjustment on 4/01/28 and every 3 years after that for cases filed on or after the date of adjustment.)", No and Yes; under Yes, "Did you acquire the property covered by the exemption within 1,215 days before you filed this case?", No and Yes. Neither is selected; choosing No on line 3 hides and clears 3-1.
8. **The first gap**, in a `role="status"` region that stays mounted (the Assets step's pattern), once anything on the page is answered; Continue is disabled while a gap stands. `exemptionGaps.ts` copies the server's gap list (§5.5), and a backend test pins its sentences to the server's, as `test_claim_gaps.py` does.

Inputs are named for the journeys: `exemptions_line_1`, `exemptions_line_3`, `exemptions_line_3_1`, and per row `claim_<i>_asset`, `claim_<i>_law`, `claim_<i>_other_law`, `claim_<i>_amount_kind`, `claim_<i>_amount`, `claim_<i>_short_description`. Radio groups are fieldsets with legends carrying the required mark; controls are at least 44 px tall; the page is one column at phone width (`global.css` `@media (max-width: 767px)`), and it joins the vitest-axe test.

### 5.5 Gaps and the gate

`exemption_gaps(session)` in a new pure module `apps/intake/exemptions.py` (no model imported; reads the session's relations by attribute, as `claim_step_gaps` does) returns every gap in page order:

1. `line_1` unanswered: "Choose which set of exemptions you are claiming."
2. No claim and `no_claims` not true: "Add the property you claim as exempt, or press “I'm not claiming any property as exempt.”"; when the session has no item to claim, "Press “I'm not claiming any property as exempt.”"
3. For each claim in print order (§6.1), its first gap:
   - no live item: "One claim is for property that is no longer on your property list. Remove it or choose the property again.";
   - no law and no typed law: "Choose the law for {name}.";
   - a law key not in the catalog in force: "The list of laws has changed since you chose a law for {name}. Choose a law again.";
   - no amount choice: "Choose a dollar amount or 100% of fair market value for {name}.";
   - `dollars` with no amount: "Enter the dollar amount you claim for {name}.";
   - a name that doesn't fit and no short description: "Type a shorter description of {name} for Schedule C."
4. `line_3` unanswered: "Answer line 3, the homestead question."
5. `line_3` Yes and `line_3_1` unanswered: "Answer the second part of line 3."

`{name}` is the item's name (B12). An empty typed law (blank once trimmed) counts as none. Every gap sentence scores grade 8.4 or below.

**The gate.** `FORM_REGISTRY["schedule_c"]` becomes `PacketForm(_always, _needs_exemption_answers)`: it raises `PreconditionMissing(<the first gap's sentence>, page="/exemptions")` (a literal, as `test_rule_fixes.py` reads it), modelled on `_needs_fee_waiver_answers` (`registry.py:119-159`). Generate, Generate All (an `errors` entry), Regenerate and an unfiled download meet it after the completion, Assets, claims and means-test checks; the packet list never runs it. Complete is unchanged: the page's answers are not intake data (U:121-122).

### 5.6 Seed, briefs and journeys

- `seed_demo_data` writes each persona's `ExemptionAnswers` and claims (§6.4), linking items by `asset_at` position. Personas seeded before 3g1 have none, so their Schedule C is refused until the page is answered: re-create them with `seed_demo_data --reset`.
- `answer_household` (`apps/intake/tests/builders.py`) gains an `exemptions` default (line 1 `state_and_federal`, `no_claims` true, line 3 `no`), so tests that generate the whole packet keep passing; `exemptions=None` leaves them unanswered.
- Each persona brief in `docs/testing/persona-briefs/` gains its Schedule C picks (§6.4), so no brief runs ahead of its seed (PS:5); DeShawn's homestead question (`deshawn-mitchell.md:108`) is rewritten for the 2026 figure.
- Every journey that passes the filing-fee page answers the exemptions page through a new page object (`e2e/pages/exemptions.page.ts`) from the personas' fixtures (`e2e/fixtures/personas.ts`).

### 5.7 Testing (3g1)

- **Catalog:** the migration's rows (every key, citation, position, limit sentence and source URL, pinned against the statute as read); `in_force` picks the 2026 version on 2026-10-16 and refuses (with the exemption sentence and a log line) before 2026-01-01; `valid_through` empty on purpose; summaries and keys in step; every limit sentence at grade 9 or below with no `ADVICE` hit but `$`, by the backend port, itself pinned by the shared case file; `ExemptionSchedule` gone and the fixture loads.
- **Names, labels and values:** every persona row's name (B12), label (B13, against A/B's own printed number) and value (B16, against A/B's printed value), including a car ("Honda Civic 2015"), cash ("Cash"), a home (its street), the first savings account (17.3), a 401(k) (21) and a row on A/B's sheet; `description_fits` false for a long name and true for a short one, measured against page 1's box.
- **Records and endpoint:** each column is ciphertext in a raw SQL read; every 400 in §5.3; whole-list semantics and ids; a foreign asset id saves as no link; a claim follows an item moved to another line; the PUT locks (postgres test) and never reopens a completed intake; another user's session is a 404.
- **Gaps and gate:** each gap and its order, both wordings of gap 2; `requires()` refuses with `page="/exemptions"` and passes once answered; a name changed on the Assets step to one that no longer fits raises the description gap; Generate All's `errors` entry carries the page; the dashboard links "Go to The property you claim as exempt".
- **Page (vitest):** nothing selected on load; every row's law select has the same options in the same order whatever its item; the line 1 notes render after both choices; adding a claim clears "not claiming"; the description, removed-item and empty-items notes; totals are neutral (a total over its limit renders the same markup as one under it, and no `role="alert"`); "This law names no dollar limit." shows only for an empty `limit_text`; line 3's No clears 3-1; Continue saves then goes to `/sofa`; the filing-fee page now continues to `/exemptions`.
- **Copy:** a new `upl-exemptions-copy.test.ts` lists every new `copy.ts` sentence by name against the `ADVICE` patterns, adding "protect", "covered", "you keep" and "best set"; the totals are checked as templates with `{amount}` and `{n}` placeholders, and the existing `UPL_EXEMPTION_DISCLAIMER` stays out of it (its "advise" matches `/\badvise/i`; §7); every copy.ts sentence passes the reading-level test (grade 9 or below); the DRAFT C-8 marks are counted.
- **Journeys:** all eight pass, walking the page.

## 6. 3g2: print

### 6.1 The schema

**Builder's call B9:** a tool, `data/forms/field_index/tools/build_schedule_c.py`, writes `schedule_c.json` and its addendum rows in `step2_verification.json` ("change the tool, not the JSON"), as the claims, A/B and List of Creditors tools do; a byte test compares its output with the files.

- **Group `c_part_2`**: 15 slots, rows 1–3 on page 1 and 4–15 on page 2, `extra_page: 2`; no `number`, `number_boxes` or `totals` (the form prints none, as `ef_part_3` and `d_part_2` omit them). Copies of page 2 hold 12 rows each. Every row's text boxes have unique full names, so no row box needs a tag; each row's amount checkbox pair shares a name with distinct on-states (`/On`, `/fair market`), so one untagged binding with a two-key `choices` map ticks one.
- **Page numbers**, declared at the top level, as Schedule G does for the same two-page shape: page 1's total `page@1:T33`, page 2's `this` `page 2` and total `page@2:T88` (the full name `page` sits on both pages, so its keys are tagged). They print only with copies.
- **A binding namespace for the claims:** `exemptions.claims[].<attr>`, resolved through `EXEMPTION_CELLS` in `fill_resolver.py` and read once a call (as `one_read_of_claims`); `exemptions.<answer>` for lines 1, 3 and 3-1. Every binding of a filer's answer is `source: asked`, `legal_review: true`, and the resolver's UPL guard (`fill_resolver.py:904-906`) covers the namespace, with a test that a claim with no law prints no law and an unanswered line prints no tick. A refusal of any cell links to `/exemptions`.
- **Print order:** claims in the A/B order of their items (`ordered_assets` position), an item's claims in the order the filer added them (claim id), and claims with no live item last (they can't print: the gate refuses them first). **Builder's call B10:** A/B order keeps an item's stacked rows together and lets a reader follow Schedule C down Schedule A/B.
- The old `2.2` binding (`answer:schedule_c.statute_2.2`) and `test_schedule_c_schema.py`'s `MISPLACED` pins go; the `schedule_c.audit.json` rows and `test_oracle_tier2.py:222-223` case they feed are replaced by the new bindings' rows.

### 6.2 What each box prints

| Box | Prints |
| --- | --- |
| Line 1 (`check 1`) | `state_and_federal` → `/state and federal`; `federal` → `/federal`; unanswered → nothing (the gate refuses first) |
| Brief description (`description`, `description_2` … `description_15`) | the claim's `short_description` while the item's name doesn't fit (`description_fits` false) and it isn't blank, else the item's name (B12; owner, 2026-11-13: short words left from before a rename to a name that fits never print) |
| Line from Schedule A/B (`Schedule AB`, `Line from`, …) | the item's A/B label (B13), without a trailing dot: "3.1", "6", "17.1", "17.3", "21", or a sheet number such as "3.5" or "17c.3" |
| Current value of the portion you own (`undefined`, `undefined_6`, …) | exactly what A/B prints in the item's "portion you own" box (B16); blank when A/B's is blank (U §4.5) |
| Amount checkbox pair (`check 2.1` … `check 15`) | `dollars` → `/On`; `fair_market_value` → `/fair market` |
| Amount (`undefined_2`, `undefined_7`, …) | the claimed amount as money under `dollars` (a $0 claim prints 0.00); blank under `fair_market_value` |
| Specific laws (`2.1`, `2.2`, `2.3`, `3` … `14`) | the law's `citation` from the catalog in force, or the typed law |
| Line 3 (`check 3`) | `/no` or `/yes` |
| Line 3-1 (`check 3-1`) | `/no` or `/yes` only when line 3 is Yes; blank under No |

Measured with `text_fit.fit` on the template: the description box (97.3 pt wide, 93.3 pt of text width) fits about 19 characters of mixed text at 10 pt and 31 at 6 pt, which is why §5.3 checks every description; the line box (26.6 pt wide, 22.6 pt of text width) fits "17c.12" and "17c.99" at 7.5 pt and "17c.100" at 6 pt, and the first label it refuses is "17c.1000", a `ValueTooLong` linking to `/exemptions`. The law box takes 3 lines at 10 pt and 5 at 6 pt. Page 1's money boxes are left-aligned and page 2's right-aligned, as the template draws them. The page-number boxes have `/MaxLen 2`, so a count past 99 pages refuses, far beyond B7's 100 claims (10 pages: the form's two and 8 copies).

### 6.3 Blank, not 0.00

An unknown item value prints blank; a "100% of fair market value" claim prints no amount; a claim's amount prints only under `dollars`. Schedule C has no totals and is not one of U §4.5's two "$0" forms.

### 6.4 Personas

Each persona's picks follow the companion, recalculated on the 2026 figures by its own rule (PS:265: "row 2 = min(6,500 − vehicle limit, wildcard limit), and any wildcard left goes to checking, then cash, then electronics, then goods"). Line 1 is `state_and_federal` and line 3 is No for all six. Rows are in print order (§6.1); the items are named here by kind, and print by B12's name.

| Persona | Rows: item (A/B line) → law, amount |
| --- | --- |
| Maria (7) | Civic (3.1) → 12-1001(c) $3,600.00; Civic (3.1) → (b) $2,900.00; household goods (6) → (b) $520.00; electronics (7) → (b) $200.00; clothes (11) → (a) 100%; cash (16) → (b) $40.00; checking (17.1) → (b) $340.00 |
| James (7) | Camry (3.1) → (c) $3,600.00; Camry (3.1) → (b) $1,900.00; household goods (6) → (a) 100%; electronics (7) → (a) 100%; clothes (11) → (a) 100%; cash (16) → (b) $40.00; checking (17.1) → (b) $1,200.00 |
| Priya (5) | CR-V (3.1) → (c) 100%; clothes (11) → (a) 100%; checking (17.1) → (b) $1,900.00; savings (17.3) → (b) $2,100.00; 401(k) (21) → 12-1006 100% |
| DeShawn (5) | home (1.1) → 12-901 $20,000.00; F-150 (3.1) → (c) $3,600.00; F-150 (3.1) → (b) $4,000.00; clothes (11) → (a) 100%; 401(k) (21) → 12-1006 100% |
| Sarah (0) | presses "I'm not claiming any property as exempt" (she listed no property) |
| Andrés (9) | Fit (3.2) → (c) 100%; household goods (6) → (a) $1,200.00; electronics (7) → (a) $400.00; clothes (11) → (a) $300.00; cash (16) → (b) $60.00; checking (17.1) → (b) $412.00; savings (17.3) → (b) $85.00; payouts (38) → (b) $310.00; bags (40) → (d) $150.00 |

What changed from the companion: Maria's vehicle rows ($2,400 + $4,000 became $3,600 + $2,900) and the rest of her $4,000 "any other property" amount, spread by the companion's own order; Priya's savings figure ($4,000 − $1,900); DeShawn's homestead row (his $20,000 equity, from his $180,000 home and $160,000 mortgage, in place of the old $15,000 limit) and his vehicle row ((c) $3,600 in place of $2,400); the 401(k) rows' line (21, not 21.1). Every item exists in the seed with the value the companion gives. Every persona but Sarah prints rows on page 2 (page 1 holds 3); nobody prints a copy.

### 6.5 Testing (3g2)

- **Schema:** the tool's byte test; `manage.py check` (forms.E001–E007) passes with the group and page numbers; tier 1 draws and reads every new binding in its own widget; tier 2 gains an addendum row per binding, and `ASSERTED_CASES` (1521 today, `test_oracle_tier2.py:37`) moves to what the run shows, explained in its comment.
- **Rows:** each box in §6.2 by a test with distinct values per row, every one of the 15 slots and both checkbox states per row, so a swapped box fails (3d2's lesson: N parallel boxes need N distinct values); stacked rows keep A/B order; a claim with no live item never prints.
- **Copies:** a synthetic session with 16 or more claims prints rows 16 on on a copy of page 2, with the filer's name repeated and "page N of M" filled on every page; 28 claims print two copies.
- **Blank cases:** unknown value, 100% claims, line 3 No leaves 3-1 blank, no claims prints an empty Part 2 with line 1 and line 3 ticked.
- **UPL:** nothing prints a law or tick without an answer (the guard test above).
- **Tier 3:** each persona's Schedule C as in §6.4 (lines 1 and 3, every row's description, line, value, tick, amount and law).
- **Journeys:** all eight pass.

## 7. Copy and counsel

Every DigniFi sentence about the law (the introduction, the line 1 notes, the summaries, the limit sentences, the totals) carries a `DRAFT: counsel C-8` mark and ships as draft (U:633). The form's own words go in `formText.ts`, unscored and unmarked. Counsel's list for spec C-8:

- the law summaries and the limit sentences, and whether plain sentences (B15) or the statute's own words in quotation marks should show: 12-1001(a)'s resale-value and jewelry words, (g)(4) and (h)(2)–(3)'s "reasonably necessary", (h)'s 2-year and 5-year time rule (which keeps the statute's "accrues"; a plainer word must not move the start date), (j)'s excepted contributions, 12-901's co-owner share (without the word "double"), and whether (b)'s "$1,000 automatic under 12-1001.1" belongs in its sentence;
- whether 12-1006 and § 522(b)(3)(C) name no dollar limit, as "This law names no dollar limit." says, or whether 11 U.S.C. § 522(n)'s cap on IRAs (unread here) needs a sentence;
- the 12-1201 and domicile notes, which are the densest legal text on the page: the grades shown beside them come from the repo's formula, which counts each dot in "U.S.C." as the end of a sentence, so the first note's 7.8 reads nearer grade 12.6 once those dots are discounted; their placement after both choices (B14), the § 522(b) sentence on a person left with no exemptions, "most of the 180 days" for the statute's "a longer portion of such 180-day period than in any other place", and whether to say anything about line 1's second box;
- whether the page should show the form's instruction "Exemptions are not automatic" near "I'm not claiming any property as exempt";
- ILND's practice on stacking: whether one vehicle may be claimed under both 12-1001(b) and (c) (the statutes are silent; the form says only "Check only one box for each exemption");
- the laws left off the list: the Pension Code articles (and the right Article 8 cite), the Unemployment Insurance Act's anti-attachment section, 12-1004, 12-1005 and tenancy by the entirety (§ 522(b)(3)(B)), ERISA, SSI and the other federal statutes;
- whether `UPL_EXEMPTION_DISCLAIMER`'s "general guidance" stays now that the page shows laws and limits, and its "We cannot advise you", which the copy tests' `/\badvise/i` matches.

## 8. CLAUDE.md and docs

- **3g1** adds a gotcha, "Exemptions are the filer's own": the page, its endpoint and records (not intake data, never reopens), the gate (`requires()`, `page="/exemptions"`), the catalog (dated, migrated, `valid_through` empty on purpose, limit sentences scored by the backend port), the item name and A/B label functions, and the rule that no code chooses a law or an amount. It updates "Seed order" (re-create personas seeded before 3g1) and the forms gotchas that list refusals and pages (`PAGE_LINK_LABELS`).
- **3g2** extends it with Schedule C's printing (the group, copies from row 16, page numbers, the namespace) and updates "Blank, not 0.00" and the repeat-group list.
- `docs/REFERENCE_TABLES.md` gains a section for the exemption laws: where they are posted (the ILGA statutes and Public Acts), that they change only by Public Act, how to add a catalog version (a data migration, its limit sentences rewritten and scored), and the owner as named operator (U:108).
- `docs/PLAIN_LANGUAGE_GUIDE.md`'s exemption examples (`:253`, "$15K", now wrong; `:263`, "Most filers keep everything", an outcome claim) are corrected in 3g1 (Builder's call B11).

## 9. Tickets

- **DIG-286** (the unread, unchecked exemption fixture) is done by 3g1.
- **DIG-81** (Schedule C's descriptions bound to statute boxes; the exemption set and homestead question unbound) and **the Schedule C part of DIG-69** (schedules printing no rows) are done by 3g2.
- Ticket states change only on the owner's yes.

## 10. Left to the builder

- Migration numbers and file names; the `ExemptionCatalog` and `ExemptionLaw` field names beyond those named; the exact serializer and view structure.
- The summaries and limit sentences §5.1 doesn't draft, under B4's and B15's rules, each scored.
- The short line names B12 needs, in the form's words.
- The page's component split, its CSS within the existing patterns, and the exact non-legal labels ("Add a claim", "A dollar amount", "Another law").
- How `exemptionGaps.ts` and the server's list are kept in step (a pinned-sentence test, as for claims), and the shared case file that pins the backend reading-level port.
- The journeys' page object shape, given the input names in §5.4.

## 11. Builder's calls

| Call | Section | Choice |
| --- | --- | --- |
| B1 | §5.1 | Stable law keys such as `il_735_5_12_1001_c`, one entry per lettered subsection and per numbered paragraph of (g) and (h) |
| B2 | §5.1 | `ExemptionCatalog(DatedTable)` + `ExemptionLaw` rows in `apps/districts`, loaded by a data migration, `valid_through` empty |
| B3 | §5.1 | The exemption table refuses in its own sentence, not the income one, with no "try again later" |
| B4 | §5.1 | Summaries in `copy.ts` keyed by law, scored and marked draft, in the statute's terms, with no "you", no figure and no account kind the statute doesn't name |
| B5 | §5.2 | A claim table with an FK to the A/B row (`SET_NULL`), not a JSON list |
| B6 | §5.3 | Typed text must fit its box at 6 pt to save; the item name's fit is worked out live on every read and in the gate, against the shorter description box |
| B7 | §5.3 | At most 100 claims |
| B8 | §5.4 | The law list shown once; each claim's law is a native select of the same list |
| B9 | §6.1 | A tool writes Schedule C's schema and addendum rows |
| B10 | §6.1 | Claims print in A/B order, an item's claims in the order added |
| B11 | §8 | Correct the plain-language guide's two exemption examples in 3g1 |
| B12 | §5.3 | The item's name: description, else make, model and year, else street, else a short line name ("Cash"); never "one item" |
| B13 | §5.3 | The A/B line label is read from Schedule A/B's own schema, without a trailing dot, and pinned against A/B's printed numbers |
| B14 | §5.4 | The line 1 notes follow both choices as one block, with both halves of the domicile rule (the copy reviewer called their placement the owner's decision) |
| B15 | §5.1 | Limit sentences are plain, state their unit, live in the catalog as dated data, and are scored by a backend port of the reading-level test |
| B16 | §5.3 | The value is exactly what A/B prints in the row's "portion you own" box |
| B17 | §5.2 | A claim follows its item to another A/B line, with no gap; a filed form keeps its stored values |

<!-- prettier-ignore-end -->
