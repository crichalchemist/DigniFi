# Forms step 3: persona targets

**Status:** approved by the owner on 2026-10-16, with the umbrella spec `docs/superpowers/specs/2026-10-16-forms-step3-design.md` (§7). The owner asked for fictional creditor names. Each section below began as one persona's draft, written against the tree at `9bd6665`.

**What this is:** the target for the six personas once step 3 is done. The briefs in `docs/testing/persona-briefs/`, the seeds and the E2E fixture change only as each PR lands, and each PR applies only its own slice ("Per PR" in each section). A brief never runs ahead of its seed.

**How to read a section:**

- **Story delta, Per PR and Outcome changes** are the target.
  - Every "his answer" or "her answer" is the persona's own answer, never the app deciding.
  - "VERIFY" marks an expected figure to work out by hand in the PR that changes it.
  - Each draft pins the fill date at 2026-10-15, so the six-month window is April 1 through September 30, 2026.
- **Conflicts** quote the files as they stood at `9bd6665`, real names included. Each PR's spec resolves the conflicts in its slice.

**The owner's calls, 2026-10-16.** Accepted as drafted:

- James's take-home pay ($4,500) and Priya's ($8,330, with $1,550 for her spouse);
- Maria's SNAP counted inside J 7's $450; her son is 8, her daughter 5, and Medicaid stays out;
- Sarah with no assets;
- Priya's $3,000 IRS priority debt;
- Andrés Kettleby as drafted;
- the story tensions left as they are.

**Fictional creditor names (Q28.names, 3a1).** Every private creditor, notice party and lender is fictional. The target sections below already use these names, and 3a1 renames the seeds, briefs and E2E fixture to match. A file reference beside a renamed creditor points at the row 3a1 renames.

| Today (seed, brief, fixture)    | Target                              | Persona |
| ------------------------------- | ----------------------------------- | ------- |
| Capital One                     | Brightwater Card Services           | Maria   |
| Northwestern Memorial Hospital  | Larkfield General Hospital          | Maria   |
| Discover Financial              | Ironbridge Card Company             | Maria   |
| Citibank                        | Meridale National Bank              | James   |
| Toyota Financial Services       | Crestway Auto Credit                | James   |
| American Express                | Silverpine Card Services            | Priya   |
| Rush University Medical Center  | Westhaven University Medical Center | Priya   |
| American Honda Finance (new)    | Kestrel Auto Finance                | Priya   |
| Wells Fargo Home Mortgage       | Harrowgate Home Loans               | DeShawn |
| Midland Credit Management       | Tallgrass Credit Management         | DeShawn |
| ComEd                           | Lakeline Electric                   | DeShawn |
| Advocate Health                 | Southmoor Health                    | DeShawn |
| Navient                         | Keelson Loan Servicing              | Sarah   |
| University of Illinois Hospital | Lakemont University Hospital        | Sarah   |

- **Names that stay:**
  - Government creditors keep their real names and public addresses, both verified 2026-10-16: the IRS (Centralized Insolvency Operation, P.O. Box 7346, Philadelphia, PA 19101-7346) and the Illinois Tollway (2700 Ogden Ave, Downers Grove, IL 60515).
  - Banks that hold a persona's own accounts are not creditors, so they keep their names: Chase, PNC and Bank of America.
  - The drafters' own invented names stay as written, "Demo" names included.
- **Any resemblance** of a fictional name to a real firm is unintended.

**Persona order:** Maria, James, Priya, DeShawn, Sarah, then the new sixth persona, Andrés Kettleby.

## Maria Torres: step 3 persona update (approved 2026-10-16)

The figures are synthetic, and so are all new names, addresses and last-4 digits. The SSN stays at 900-11-0001 (the E2E fixture uses 900-11-1001). Every answer below is **Maria's own answer**, with the reason it fits her story. None of them is the app deciding for her.

The draft pins a **fill date of 2026-10-15**, and everything dated is derived from it:

- the six-month window is April 1 through September 30, 2026;
- the children are 8 and 5;
- the median table in force is the one for cases filed on or after 2026-04-01;
- the HHS table in force is the 2026 guidelines.

### 1. Story delta

Maria makes her $3,200 a month in two jobs. She is a cashier at Walgreens (about $2,150) and works hourly evenings at a restaurant (about $1,050), with no tips. Across both jobs her paychecks lose $400 a month to Social Security, Medicare and withholding, which leaves the $2,800 take-home the brief fixed. SNAP adds $350 a month on her Link card; she knows the figure from her approval notice and reads money carefully. The children's father pays nothing and there is no support order, so Schedule I 8c and A/B line 29 are both nothing. She has lived in Illinois all her life and at 2145 W Division St since July 2021, on a lease she renews every year; she paid a move-in fee and no security deposit, which is common in Chicago. Her 2025 tax refund came in March 2026 and is spent.

### 2. Per PR

#### 3a1 (data foundations)

- No new persona data.
- The median lookup now reads the table in force on the fill date (see V1). The tests pin the fill date.
- DIG-273: her two asset rows and three debt rows keep their ids across autosaves, with no data change.

#### 3e1 (household and spouse)

- **Marital status, in 122A-1 line 1's three answers:** "Not married". This is the seed's `single` (`seed_demo_data.py:70`), now encrypted. There is no spouse, so no Column B and no Schedule I column 2.
- **County:** Cook. Wicker Park (60622) is in Chicago.
  - It is stored encrypted in the new household/county model.
  - 101 `Debtor1.County` prints "Cook" (DIG-277).
- **Household list:** these are her answers, and no names are stored.

| #   | Relationship | Age | Lives with her? | Claimed on her return / supported by her? |
| --- | ------------ | --- | --------------- | ----------------------------------------- |
| 1   | Son          | 8   | Yes             | Yes                                       |
| 2   | Daughter     | 5   | Yes             | Yes                                       |

- The brief says only "your son's ER visit" (`maria-torres.md:17`) and "two (ages 8 and 5)" (`:7`). "Daughter" and putting the son at 8 are the drafter's picks. **OWNER?**
- **The counts the list gives, one per form:**
  - Schedule J line 2: 2 rows.
  - 103B line 1: you 1 + spouse 0 + dependents 2 = 3.
  - 122A-1 line 13: 3 people live with her.
  - 122A-2 line 5: not used, because 122A-2 is not in her packet.
- **Schedule J line 3** ("expenses of people other than yourself and your dependents"): No, if 3e1 asks it.
- **Removed:**
  - `DebtorInfo.household_size: 3` (`seed:66`) stays in place but is no longer read.
  - `number_of_dependents: 2` (`seed:71`) is gone.

#### 3e2 (income detail and expenses)

- **Income step (Q26):** "Your average monthly income for April 1 through September 30, 2026".
  - The ten sources stay as seeded: wages $3,200 and every other source typed $0 (tips, rental, pension, Social Security, unemployment, child support, alimony, other).
  - "Is your income now different from that average?" No. Schedule I uses the same set.
- **Q5:**
  - Business: none (gross $0, expenses $0, net $0).
  - Rental gross and costs: $0 / $0.
  - Interest and dividends: $0. Her Chase checking account pays nothing.
- **Q16, payroll deductions (Schedule I 5a–5h, monthly, both jobs combined):**
  - 5a tax, Medicare and Social Security: **$400**. That is about $245 of FICA (7.65% × 3,200) plus about $155 of Illinois and federal withholding.
  - 5b–5h: typed $0. She has no retirement plan or loan deductions, and her insurance is not deducted from pay (J 15d).
  - Line 6 = $400. Line 7 = $2,800.
- **Q6, 8f government assistance, asked once:**
  - Regular assistance: Yes.
  - Cash: none.
  - Non-cash kind: "SNAP (food stamps)", value if known **$350/month**.
  - Prints on 8f with Specify "SNAP (food stamps)". The shared `Assistance 8f` widget prints only at 8f, and line 11 stays blank until step 4.
- **Q4, the newly asked everyday Schedule J lines (her answers):**
  - 4a, 4b, 4d, 5 and 20a–20e: $0. She rents and has no renter's insurance.
  - 10, personal care products and services: **$40** (toiletries and haircuts for three).
  - 13 and 14: $0 (no room in the budget).
  - 16: $0 (her taxes are withheld through 5a).
  - 19: $0 (she supports no one outside the home).
  - "Other 21" Specify, for her existing $50: "School supplies and fees".
  - The 13 seeded amounts are unchanged (`seed:74-88`). Food stays $450 (see OWNER? in section 4).
- **E2E fixture:**
  - `MARIA.income` gains the deduction lines, 8f and the "now different?" answer.
  - `total_monthly_income` (`personas.ts:101`) becomes the wages box.

#### 3f (fee waiver)

- **Form 101 line 8 (`Check Box7`), her answer: "I request that my fee be waived."**
  - Her reason: with two kids and $550 a month left on Schedule J (23c, see V4), she doesn't think she can spare $338, so she asks. The court weighs that, not the app.
  - The information beside the question shows she is below the line for a family of 3.
  - The court decides, and the app says so.
- **The information shown (Q21/Q22, dated per Q10):**
  - threshold: 150% of the 2026 HHS guideline for 3, $3,415/month (`scope/fee-waiver.md`, persona table);
  - her § 820.20 figure: Schedule I line 12 less the non-cash help, 3,150 − 350 = $2,800.
- **103B:**
  - line 1 reads the household list;
  - line 2 reads Schedule I;
  - line 3 reads 8f (Yes, "SNAP (food stamps)") and is no longer asked on the page.
- **The take-home answer** on the fee-waiver page is replaced by Schedule I data (Q16 pre-fill, or nothing to ask).
- **Seed:**
  - Maria's line 8 choice is stored, and her `FeeWaiverApplication` exists because of it (not `qualifies_for_fee_waiver`).
  - `cannot_pay_full`/`cannot_pay_installments` and `household_size` (`seed:610-613`) follow the 3f model.
- **E2E:** the journey picks "waiver" on line 8, and `MARIA.fee_waiver` shrinks to what the page still asks.

#### 3b (A/B): every line walked, her answers

Ownership is "Debtor 1 only" on every item, so entire value = portion. Nature of interest is left blank.

| Line                                  | Answer                                                                                 | Value         |
| ------------------------------------- | -------------------------------------------------------------------------------------- | ------------- |
| 1–2 real estate                       | No (renter)                                                                            | 0             |
| 3.1                                   | 2015 Honda Civic, about 120,000 miles, no liens                                        | 6,500         |
| 4 (boats, trailers, RVs…)             | No                                                                                     | —             |
| 5 total                               |                                                                                        | 6,500         |
| 6 household goods                     | Beds, sofa, kitchen table, dishes                                                      | 600           |
| 7 electronics                         | Old laptop, cell phone, 32-inch TV (the brief's phone and laptop)                      | 200           |
| 8, 9, 10, 12, 13, 14                  | No                                                                                     | —             |
| 11 clothes                            | Everyday clothes and shoes                                                             | 250           |
| 15 total                              |                                                                                        | 1,050         |
| 16 cash                               | Cash on hand                                                                           | 40            |
| 17.1 checking                         | JPMorgan Chase                                                                         | 340           |
| 18–20, 23–27, 30, 32–35               | No                                                                                     | —             |
| 21 retirement                         | No (no plan at either job)                                                             | —             |
| 22 security deposits                  | No (move-in fee, no deposit)                                                           | —             |
| 28 tax refunds                        | No (2025 refund received and spent in spring 2026)                                     | —             |
| 29 family support                     | No (no order; the father pays nothing)                                                 | —             |
| 31 insurance                          | Yes: her insurance policy (the $120/mo on J 15d; J 15a/15b stay step 4), no cash value | 0             |
| 36 total                              |                                                                                        | 380           |
| 37 (Part 5), 46 (Part 6), 53 (Part 7) | No                                                                                     | —             |
| 62 / 63                               |                                                                                        | 7,930 / 7,930 |

- **OWNER?** A $1,100 deposit on line 22 is the alternative to the move-in fee. It would add $1,100 to line 36 and to her wildcard demand.

#### 3c (claims, collateral link, creditor list)

The names are fictional for every new party; see section 4 for the three existing creditors. The last-4 digits are synthetic.

| Debt                                   | Address (synthetic)             | Last 4 | Incurred                 | "Can the lender take back property?" | Status flags |
| -------------------------------------- | ------------------------------- | ------ | ------------------------ | ------------------------------------ | ------------ |
| Brightwater Card Services card, $4,200 | 1 Demo Way, Richmond, VA 23238  | 1001   | 2019–2025                | No                                   | none         |
| Larkfield General Hospital, $12,800    | 2 Demo Plaza, Chicago, IL 60611 | 2002   | 11/2025 (son's ER visit) | No                                   | none         |
| Ironbridge personal loan, $3,500       | 3 Demo Rd, Riverwoods, IL 60015 | 3003   | 05/2024                  | No                                   | none         |

- **Secured:** her answer is No for all three, because she pledged nothing. The Civic's title is clear (paid off). There is no collateral link, and Schedule D stays empty.
- **Status flags:** contingent, unliquidated, disputed and offset are all No, by her answers. Nothing is pre-ticked.
- **Timeline:** the hospital bill and the card went to collections about February 2026, matching the brief's "8 months" of dodging calls at the fill date.
- **"Is anyone else contacting you about this debt?" (S3-NOTICE):**
  - Brightwater Card Services: Yes, "Lakefront Demo Recovery LLC, 10 Demo Ct, Chicago, IL 60604", last 4 "4004".
  - Hospital: Yes, "Prairie Demo Collections Inc., 20 Demo Ave, Oak Brook, IL 60523", last 4 "5005".
  - Ironbridge: No. It isn't in collections (`seed:126`).
- **Schedule G:**
  - "Division Demo Properties LLC, 30 Demo St, Chicago, IL 60622". Residential lease for 2145 W Division St Apt 3, $1,100/month, current term 07/01/2026–06/30/2027.
  - Kind: residential, not a vehicle and not a personal-property lease (Form 108 flag false).
  - "Do you owe money on this now?" No; her rent is current.
- **Codebtors:** none. No one co-signed, and Illinois is not a community-property state.
- **Creditor list (S3-LIST):** the 3 creditors, 2 notice parties and the landlord, so 6 entries.
- The E2E fixture gains the addresses, notice parties and lease. The journey fills step 6 instead of skipping it (`maria-happy-path.spec.ts:69-70`).

#### 3d (priority)

- **E/F Part 1 "Is this one of these?":** her answer is "No" for each of the three debts.
- **Why it fits:** she owes no taxes (withheld, refund received), no support (she is the custodial parent), and there is no injury claim.
- She has no priority debt and no line 35 past-due amount. Another persona carries the priority debt.

#### 3g (Schedule C): her picks from the one catalog

- **Line 1:** "state and federal nonbankruptcy exemptions" (§ 522(b)(3)).
  - This is her own pick, after the plain notes on 12-1201 and the 730-day rule.
  - It fits because she has lived only in Illinois.
- **Line 2:** one row per (item, law). She protects the car first ("it's how you get to work"), and she keeps every law within its printed limit because she reads money carefully. At the fixture amounts ($2,400 / $4,000):

| Row | Item (A/B line)     | Law                   | Amount                                                          |
| --- | ------------------- | --------------------- | --------------------------------------------------------------- |
| 1   | Civic (3.1), $6,500 | 735 ILCS 5/12-1001(c) | $2,400 (the vehicle limit)                                      |
| 2   | Civic (3.1)         | 735 ILCS 5/12-1001(b) | $4,000 (all of the wildcard)                                    |
| 3   | Clothes (11), $250  | 735 ILCS 5/12-1001(a) | 100% of fair market value, up to any applicable statutory limit |

- Checking, cash, household goods and electronics are left unclaimed, because no wildcard is left. $100 of the Civic is not covered. Both are her choice.
- The rows are 3, so they fit page 1. Variant B below has 7 rows and exercises the Part 2 additional page (Q8).
- **Line 3** (homestead over $214,000): No. She is a renter.
- **OWNER?** Variant B: she also claims checking $340, cash $40, goods $600 and electronics $200 under (b). That brings the (b) total to $5,180 against $4,000 and tests that the neutral totals warn about nothing (C-LIMITS b). The draft prefers the within-limit default for her character.

#### 3h (122A-2)

- None. She is below the median, so 122A-2 and line 36 are not in her packet.
- DIG-276 and the opt-ins don't apply.

### 3. Outcome changes (each VERIFY: worked out by hand later)

**The SNAP chain (V2), to which V3, V4 and V8 point back:** Schedule I line 4 = 3,200; 6 = 400, so 7 = 2,800; 8f = 350, so 9 = 350; 10 = 2,800 + 350 = 3,150, and 12 = 3,150. Check: 12 − 8f = 3,150 − 350 = 2,800, the owner's fixed take-home.

- **V1 (3a1), VERIFY:** 122A-1 13C goes from 110,712 to 113,625. That is Illinois for 3 people, the table in force for cases filed on or after 2026-04-01 (Q11). It holds only while the fill date is before any November 2026 Census table. 14a stays below: 38,400 ≤ 113,625.
- **V2 (3e2), VERIFY:**
  - Schedule I `Amount 12`: 3,200 → 3,150 (the chain above).
  - Also 5a 400, 6 400, 7 2,800, 8f 350, 9 350, 10 3,150.
  - 5b–5h, 8a–8e, 8g and 8h print 0.00.
  - 11 and 13 stay blank (step 4).
- **V3 (3e2), VERIFY:** 106Sum 4 goes 3,200 → 3,150, and J 23a goes 3,200 → 3,150 (from V2).
- **V4 (3e2), VERIFY:**
  - J 22a, 22c and 23b: 2,560 → 2,600 (+ J 10 $40). 106Sum 5 → 2,600.
  - J 23c: 640 → 550 (3,150 − 2,600).
  - Expenses: 1,100 + 180 + 85 + 40 + 450 + 60 + 75 + 400 + 120 + 50 + 40 = 2,600.
- **V5 (3e2, Q27), VERIFY:** Schedule I `Amount 8b Debtor 1` and 122A-1 `Debto1.Quest7` go from "" to "0.00", because interest is asked and typed $0. Tier 3 currently expects "" (`test_oracle_tier3.py:56`, `:66`).
- **V6 (3e2), VERIFY; open question for the 3e2 spec and counsel:** does 8f's value feed 122A-1 line 10 / CMI? Not decided here.
  - If not: CMI = 3,200 and 12B = 38,400, unchanged. If yes: CMI = 3,550 and 12B = 42,600. Either way it is below 113,625; 106Sum 8 follows CMI.
- **V7 (3b), VERIFY:**
  - 106Sum 1b and 1c: 6,840 → 7,930 (6,500 + 1,050 + 380).
  - A/B lines 5 = 6,500, 15 = 1,050, 36 = 380, 62 = 63 = 7,930.
  - 106Sum 3b/3c stay at 20,500 (4,200 + 12,800 + 3,500).
- **V8 (3f), VERIFY:**
  - 103B line 1: total 3, dependents 2.
  - Line 2: `undefined_2` 2,800 → 3,150 (Schedule I line 10, as 103B says); `undefined_4` 3,150; `undefined_5` 350 (non-cash subtracted); `undefined_6` 2,800.
  - Line 3: Yes, "SNAP (food stamps)".
  - Line 6 (`undefined_7`) = J 22c, 2,560 → 2,600.
- **V9 (3f), VERIFY:**
  - Fee choice: still a waiver filer, now by her line 8 answer. 103B stays in her packet, and `WAIVER_FILERS` keeps "maria" (`test_api_readback.py:38`).
  - Shown threshold $3,415 against her figure $2,800, below. Gross 3,200 and line 12 3,150 are also below 3,415.
- **V10 (3c), VERIFY, packet count:** 15 (14 + 103B, `maria-happy-path.spec.ts:93`). It becomes 16 if the 3c creditor list counts as a Generate All packet entry; otherwise it stays 15. 108 doesn't apply (no secured debts or personal-property lease), and 103A doesn't apply (she chose the waiver).
- **V11 (3e1), VERIFY:** 101 `Debtor1.County`: blank → "Cook". 122A-1 13B stays 3.
- **V12 (3g), VERIFY:**
  - Schedule C rows 2,400 / 4,000 / 100%, against the catalog that Q23 verifies against the statute, not the fixture (`ilnd_2025_data.json`, vehicle 2,400, wildcard 4,000).
  - If the verified limits are higher, row 2 = min(6,500 − vehicle limit, wildcard limit), and any wildcard left goes to checking, then cash, then electronics, then goods.
- **V13 (3a2), VERIFY:** tier 3 ticks (14a) are read from the drawn text, not `/AS`. No value changes.
- **In-app verdict:** "may be eligible" (`maria-happy-path.spec.ts:55`), unchanged.

### 4. Conflicts and owner questions

**Brief, seed, E2E and tier 3 against each other:**

1. **Her job.**
   - The seed's SOFA source is "Wages - CNA at Northwestern Hospital" (`seed_demo_data.py:137`, `:142`). The brief has a Walgreens cashier job plus a restaurant job (`maria-torres.md:8`).
   - It also makes her an employee of her own $12,800 creditor.
   - Form 107 is step 4 (Q3), so this draft doesn't change it. The owner picks.
2. **SOFA creditor payments.**
   - Capital One shows $1,020 and Discover $720, "Monthly Jan-Mar 2026" (`seed:146-156`). Three months at $85 and $120 would be $255 and $360.
   - Jan–Mar 2026 also falls outside 107's 90-day window at a 2026-10-15 fill date.
   - Step 4; flagged only.
3. **Tier 3's claim.** Its docstring says the seed "matches docs/testing/persona-briefs/ except Priya's stale income line" (`test_oracle_tier3.py:5`). Item 1 is another mismatch, though it lies outside tier 3's boxes.
4. **SSNs.** The E2E SSN is 900-11-1001 (`personas.ts:87`); the seed and brief have 900-11-0001 (`seed:58`, `maria-torres.md:43`). Every E2E persona follows the 900-NN-NNNN pattern, so this looks deliberate. Both are in the 900 range.
5. **The checking account's description.** The E2E fixture has "Chase checking" (`personas.ts:122`); the seed has "Chase checking account" (`seed:98`). This is harmless today. 3b's line 17.1 has its own institution field.

**Against decisions.md:**

6. `seed:607-615` creates the 103B application from the means-test flag, `qualifies_for_fee_waiver`. That contradicts Q21, where 103B follows the filer's line 8 choice.
   - The journey's routing comment says the same (`maria-happy-path.spec.ts:79`).
   - So does `test_api_readback.py:36-38` ("The means test qualifies these personas").
7. **Brief rows that move.**
   - "Take-home pay (fee waiver page) $2,800" and "Non-cash help … (fee waiver page)" (`maria-torres.md:59-60`) move to the Income step: 5a–5h under Q16, and 8f under Q6.
   - `household_size` and `number_of_dependents` (`personas.ts:91`, `:100`; `seed:66`, `:71`) become the household list (Q17).

**OWNER? (judgment calls in this draft):**

8. **Food and SNAP.** J 7 "Food and housekeeping supplies" stays $450, so the $350 of SNAP is inside it, with $100 in cash.
   - Option B is to raise J 7 to $800 (SNAP on top of $450 cash). Then 22c = 2,950, 23c = 200, and 103B line 6 = 2,950.
   - Option A leaves 23c at $550, which may read as room for installments. The court weighs that, not the app.
9. **Real company names.**
   - The creditor names are real companies (Capital One, Northwestern Memorial Hospital, Discover; `seed:106`, `:114`, `:122`). S3-ADDR, S3-NOTICE and S3-LIST attach synthetic addresses and last-4 digits to them on a mailable list.
   - The choice: fictionalize the three names, or use their real public addresses. The drafter did not pick.
   - **Resolved 2026-10-16:** the owner chose fictional names. See the rename table at the top; 3a1 renames.
10. **Medicaid.** The brief says she has filled out Medicaid forms (`maria-torres.md:26`). If the children are on All Kids, 8f and 103B line 3 would list it with an unknown value. It is left out because the owner fixed "with SNAP".
11. **Household list.** The second child's relationship (Daughter), and which child is 8 (see 3e1).
12. **Line 22.** The move-in fee instead of a deposit (see 3b).
13. **Schedule C.** The within-limit default, or variant B (see 3g).

## James Washington: step 3 persona update (approved 2026-10-16)

All figures are synthetic, and so are all new names, addresses, last-4 digits and mileage. The SSN stays at 900-22-0002 (the E2E fixture uses 900-22-2002; see C1). Every answer marked **his answer** is James's own choice, with the reason it fits his story. None of them is the app deciding for him.

**Assumed fill date: 2026-10-15**, the same as the Maria and Priya drafts. Everything dated follows from it:

- the six-month window is April 1 through September 30, 2026;
- the Illinois median for one person is $73,180, from the table for cases filed on or after 2026-04-01 (Q11);
- the HHS table is the 2026 guidelines.

If the tests pin a date on or after 2026-11-01 and a November Census table has been loaded, the median moves again (V1).

The Illinois exemption limits come from P.A. 104-120, effective 2026-01-01, as quoted in `scope/assets-exemptions.md:182`. I have not verified them against ilga.gov (V9).

### 1. Story delta

The family car stayed with James's ex-wife in the fall 2023 divorce, so in December 2023 he bought the 2019 Camry used, on a 60-month Crestway Auto Credit contract at $350 a month (about 5.5% APR); 26 payments are left, worth about $8,561, which fits the $8,500 owed. He is paid every two weeks at the hotel, and withholding plus union dues bring his $5,833 gross to a $4,500 take-home; his checking earns nothing to speak of. He rents his Cook County studio on a 12-month lease from a fictional management company, is current on rent, and owns secondhand furnishings, a TV, a laptop, a phone, his clothes and about $40 cash. Nobody lives with him or depends on him, he pays his ex-wife nothing, and both debts are in his name alone. Each new fact answers a line that the A/B walk (Q24), Schedule I 5a–5h (Q16) or Schedule G now asks, and none contradicts the brief.

### 2. Per PR

#### 3a1 (data foundations)

- No new persona data.
- The median lookup reads the table in force on the fill date, so 122A-1 13C becomes $73,180 (V1).
- DIG-273: his two asset rows and two debt rows keep their ids across autosaves. 3c's link needs that.

#### 3a2 (drawing engine)

- No new data. His packet has no row overflow.
- The tier 3 read-back changes mechanism (flattened pages, exact-clip read), but not the values.

#### 3e1 (household and spouse)

- **122A-1 line 1 (`CheckBox3`): "Not married. Fill out Column A, lines 2-11."** This is his answer: the divorce was final three years ago. No spouse column, and no Column B or Schedule I column 2.
- **Household list: no entries.** His answer to "who lives with you or depends on you" is "no one", given explicitly, because Complete refuses an unanswered list (Q12).
  - Schedule J line 2, "Do you have dependents?": No.
  - Schedule J line 3 (`check3`), expenses of others: No, if 3e1 asks it.
  - 122A-1 line 13: 1 person, so 13B stays "1".
- **County: Cook.** Form 101 `Debtor1.County` prints "Cook" (DIG-277). The county is stored on the new encrypted household/county record, not on `DebtorInfo` (CORR.county).
- **Retired from his data:** `marital_status: "single"` becomes the 122A-1 "Not married" value; `number_of_dependents: 0` is replaced by the empty list; `household_size: 1` stays in the seed but is no longer read.

#### 3e2 (income detail and expenses)

- **Six-month average (Q26).** For April 1 through September 30, 2026, his gross wages averaged $5,833.00, and the other nine sources are $0.
  - "Is your income now different from that average?" No (his answer: steady salary, no overtime that month). Schedule I uses the same set.
- **Business, rental, interest (Q5):** business or self-employment: No; rental: No; interest and dividends: $0.00. His answer: the checking pays a few cents a year.
- **Schedule I 8f (Q6):** "Other government assistance that you regularly receive": No, so $0.
- **Schedule I 5a–5h (Q16): OWNER TO APPROVE.** Q28 fixes take-home pay only for Maria, DeShawn and Sarah, so these figures are my proposal. He types monthly figures, converted from his biweekly stub (×26÷12).

  | Line                                  | Amount    | Basis (synthetic)                                                                |
  | ------------------------------------- | --------- | -------------------------------------------------------------------------------- |
  | 5a Tax, Medicare, and Social Security | $1,288.00 | SS 6.2% $361.65 + Medicare 1.45% $84.58 + federal ≈ $560 + Illinois 4.95% ≈ $282 |
  | 5b, 5c, 5d                            | blank     | no retirement plan contribution or loan                                          |
  | 5e Insurance                          | blank     | his $200 insurance is paid outside payroll and stays on J 15d (no double count)  |
  | 5f Domestic support obligations       | blank     | he pays no support                                                               |
  | 5g Union dues                         | $45.00    | hotel engineers' union, about $20.77 per paycheck                                |
  | 5h Other                              | blank     |                                                                                  |
  | 6 (sum)                               | $1,333.00 |                                                                                  |
  | 7 = 4 − 6                             | $4,500.00 | 5,833.00 − 1,333.00                                                              |

  - Line 8a–8h: $0 each. Line 9: $0.00. Line 10: $4,500.00.
  - Lines 11 and 13 are not asked (step 4). Line 12: $4,500.00.

- **Expenses (Q4).** The brief's 13 amounts are unchanged. New lines, each **his answer, OWNER TO APPROVE**:
  - **Entered:**
    - J 4b renter's insurance: $15;
    - J 10 personal care: $40 (haircuts, toiletries);
    - J 13 entertainment, clubs, recreation: $45 (streaming and a Bears game a season).
  - **$0 / blank:** J 4a, 4d, 5, 14, 16, 19 and 20a–20e.
  - **J 21 "Other. Specify":** "Work boots and small tools for my job" on the existing $100. Today that $100 has no specify text.
  - **Total:** J 22a goes from $3,110 to $3,210 (V5). The Meridale National Bank $200 a month is not a Schedule J expense and is not entered.
- **No new data from:** the CMI (still $5,833: gross wages, no spouse), and encryption (Q7.income).

#### 3f (fee waiver)

- **Form 101 line 8 (`Check Box7`): "I will pay the entire fee when I file my petition."**
  - His answer. He is practical and has a steady paycheck. $338 is about two days' take-home, and he doesn't want installments "hanging over" him.
  - **Information beside it (Q22):** his figure is Schedule I line 12 less his non-cash help, $4,500 − $0 = $4,500. The 150% threshold for a family of 1 is shown beside it ($1,995 a month; V4), with "the court decides". He reads it and doesn't ask for a waiver.
- **Result:** no FeeWaiverApplication and no 103B. He doesn't choose installments, so no 103A message appears.
- **Seed:** stores his line 8 choice. James has had no fee-waiver row before (seed `:607`).

#### 3b (A/B)

Every one of the ~45 lines is walked (AB-GATES). His answer is **No to every line not listed here**, including line 4, line 21 (no retirement account) and line 28 (no refund owed).

| A/B line                          | Row                                                            | Ownership     | Entire value | Portion owned |
| --------------------------------- | -------------------------------------------------------------- | ------------- | ------------ | ------------- |
| 3.1 Cars…                         | Toyota / Camry / 2019 / approx. 78,000 miles; other info blank | Debtor 1 only | $14,000.00   | $14,000.00    |
| 6 Household goods and furnishings | Bed, couch, table, kitchenware (secondhand)                    | —             | —            | $500.00       |
| 7 Electronics                     | TV, laptop, cell phone                                         | —             | —            | $400.00       |
| 11 Clothes                        | Everyday clothes and work clothes                              | —             | —            | $300.00       |
| 16 Cash                           | Wallet                                                         | —             | —            | $40.00        |
| 17.1 Checking account             | Bank of America                                                | —             | —            | $1,200.00     |

- Community-property box: unticked. Nature of interest: blank ("if known").
- Totals: line 5 $14,000; line 15 $1,200; line 36 $1,240; lines 62 and 63 **$16,440** (V7).
- **LEGACY-ROWS.** The seed's two existing rows name their lines: Camry → line 3, checking → line 17.1. Lines 6, 7, 11 and 16 are new rows (PROPOSED; the owner may drop them, see C9).
- **Retired:** the Camry's `amount_owed` (8,500), per Q13. The owed amount lives only on the debt.

#### 3c (claims, collateral link, creditor list)

- **Crestway Auto Credit (Schedule D):**
  - linked to the A/B 3.1 Camry row (Q13);
  - address: PO Box 90122, Plano, TX 75025 (synthetic, not the creditor's real address);
  - last 4: 7702;
  - date incurred: 12/2023;
  - Debtor 1 only.
  - **Nature of lien: "An agreement you made (such as mortgage or secured car loan)".** His answer: he signed the dealer's finance contract.
  - **"Can the lender take back property…": Yes,** pre-selected from auto_loan and kept by him.
  - Contingent, unliquidated, disputed, offset: none (his answers). Notice party: No.
  - **Columns:** A $8,500.00. B $14,000.00 (sole owner, so entire equals portion; Q14). C = max(0, 8,500 − 14,000) = 0 (V8).
  - **Schedule J 17a:** "Car payments for Vehicle 1" is $350.00, from the debt's `monthly_payment`. `ExpenseInfo.vehicle_payment` is retired: the seed drops the 350 in the same commit that adds the link, so 22a neither double-counts nor loses it.
- **Meridale National Bank (E/F Part 2):**
  - address: PO Box 90222, Sioux Falls, SD 57117 (synthetic);
  - last 4: 4402;
  - date incurred: opened 06/2015, balance built 2023–2026;
  - Debtor 1 only;
  - type: "Other. Specify: Credit card";
  - $9,800.00;
  - contingent, unliquidated, disputed, offset: none;
  - notice party: No. His answer: the account isn't in collections, and only Meridale contacts him.
- **Schedule G (new, PROPOSED):**
  - "Gold Coast Example Residential LLC" (fictional), c/o Management Office, 850 N State St, Chicago, IL 60610;
  - "Residential lease, Apt 1204, 06/01/2026–05/31/2027, $1,650/month";
  - kind: not a vehicle, and not a personal-property lease (Form 108 flag No);
  - S3-GCLAIM "Do you owe money on this now?": No (rent is paid through October).
- **Codebtors (Schedule H):** none, his answer: the card and the loan are in his name alone. If H line 2 (community-property state) is asked: No.
- **Creditor list (S3-LIST):** three entries, Meridale National Bank, Crestway Auto Credit and the landlord, if G counterparties belong on it (C-9).
- **E2E step 6** gains the lease row; step 7 stays empty.

#### 3d (priority)

- **Meridale National Bank, "Is this one of these?": No, none of the four.** His answer: it's a credit card he used for everyday bills after the divorce. It stays in Part 2.
- `is_priority` is false. No split and no line 35 past-due amount.
- Toyota is secured and is not asked.

#### 3g (Schedule C)

- **Line 1 (`check 1`): "You are claiming state and federal nonbankruptcy exemptions. 11 U.S.C. § 522(b)(3)".** His answer: he read the 12-1201 note and has lived in Illinois far longer than 730 days.
- **Rows, one per (item, law) (C-STACK).** These are his amounts. He worked out his car equity himself: $14,000 − $8,500 = $5,500. The car is what he's worried about, so he covers it first.

  | Item (A/B line, value)                  | Law                   | Amount claimed                                                  |
  | --------------------------------------- | --------------------- | --------------------------------------------------------------- |
  | 2019 Toyota Camry (3.1, $14,000)        | 735 ILCS 5/12-1001(c) | $3,600.00                                                       |
  | 2019 Toyota Camry (3.1, $14,000)        | 735 ILCS 5/12-1001(b) | $1,900.00                                                       |
  | Bank of America checking (17.1, $1,200) | 735 ILCS 5/12-1001(b) | $1,200.00                                                       |
  | Cash (16, $40)                          | 735 ILCS 5/12-1001(b) | $40.00                                                          |
  | Household goods (6, $500)               | 735 ILCS 5/12-1001(a) | 100% of fair market value, up to any applicable statutory limit |
  | Electronics (7, $400)                   | 735 ILCS 5/12-1001(a) | 100% of FMV, up to any applicable statutory limit               |
  | Clothes (11, $300)                      | 735 ILCS 5/12-1001(a) | 100% of FMV, up to any applicable statutory limit               |

- **Neutral per-law totals shown:** (c) $3,600 of $3,600, and (b) $3,140 of $4,000. No warning either way (V9).
- **Line 3, homestead over $214,000: No.** His answer: he rents. Line 3-1 is not reached.

#### 3h (122A-2 and the means test)

- None. He is below median, so 122A-2 is not in his packet, and Q18, Q19 and Q20 (line 36) don't reach him.
- The in-app verdict comes from the one calculator (DIG-146). See C6 for the E2E string.

### 3. Outcome changes (each VERIFY: worked out by hand later)

- **V1. Median (3a1).**
  - **Change:** 122A-1 13C goes from 71,304.00 to 73,180.00.
  - **Arithmetic:** 12b = 5,833 × 12 = 69,996.00, still below, so 14a stays BELOW_MEDIAN.
  - **Margin:** it widens from $1,308 a year ($109 a month) to $3,184 a year ($265.33 a month), so "borderline / passes (barely)" (README) is weaker.
  - **Owner choice:** keep $5,833 (this draft), or raise his gross to restore a ~$100-a-month margin. Raising it changes a brief fact.
  - **VERIFY:** the pinned fill date, and whether a 2026-11-01 table is loaded.
- **V2. CMI unchanged (3e1/3e2).**
  - 122A-1 Quest11 = 5,833.00, 12B = 69,996.00, and 106Sum line 8 = 5,833.00.
  - Deductions, interest $0 and 8f $0 do not enter CMI. No Column B.
  - VERIFY.
- **V3. Packet count.**
  - **Today:** 14 (101, 106Dec, 106Sum, 107, 121, 122A-1, A/B, C, D, E/F, G, H, I, J).
  - **Step 3:** 103B stays out (pay in full), 122A-2 stays out (below median), and 108 is step 4.
  - **The creditor list (3c):** if it is a registry form, the count is 15. Otherwise it stays 14.
  - **Affected:** `james-borderline.spec.ts:81-83` `generateAllForms(14)`.
  - VERIFY.
- **V4. Fee waiver (3f).**
  - Not requested.
  - **Information only:** 150% of the 2026 HHS guideline for 1 = $15,960 × 1.5 ÷ 12 = $1,995.00 a month, against his $4,500.00.
  - VERIFY the HHS figure and which date counts (FW-5).
- **V5. Schedule J (3e2).**
  - 22a, 22c and 23b: 3,110 + 15 + 40 + 45 = 3,210.00.
  - 23a: 4,500.00. 23c: 4,500 − 3,210 = 1,290.00.
  - 106Sum line 5 = 3,210.00 and line 4 = 4,500.00.
  - **Before Q4's lines:** 22a stays 3,110 and 23c = 1,390.
  - **3c:** moves 17a's source and keeps 22a.
  - VERIFY.
- **V6. Schedule I and 122A-1 zeros (3e2, Q27).**
  - **Schedule I:**
    - 5a 1,288.00; 5b–5f and 5h 0.00; 5g 45.00;
    - 6 1,333.00; 7 4,500.00;
    - 8a–8h 0.00 (8b and 8f are new);
    - 10 and 12 4,500.00 (12 was 5,833.00).
  - **122A-1:** `Debto1.Quest7` goes from "" to 0.00.
  - **Tier 3 rows:** `Amount 8b Debtor 1` and `Debto1.Quest7` change from "" to "0.00" (`test_oracle_tier3.py:91,101`). `Amount 12` changes from 5833.00 to 4500.00 (`:103`).
  - **106Sum line 4:** 4,500.00 (`:87`). J 23a, 23c and 22a/22c/23b: `:107-111`.
  - VERIFY.
- **V7. 106Sum 1b/1c (3b).**
  - 14,000 + 500 + 400 + 300 + 40 + 1,200 = 16,440.00, against 15,200.00 at `:82-83`.
  - If the owner drops the proposed lines 6, 7, 11 and 16, both stay 15,200.
  - VERIFY.
- **V8. Schedule D (3c).**
  - Column B 14,000.00; Column C = max(0, −5,500) = 0.
  - **Unsettled:** whether C prints 0.00 or blank. Q27 narrows only Schedule I and 122A-1, and B2 forbids only an invented zero. Here both inputs exist.
  - 106Sum 2 = 8,500.00, 3b = 9,800.00 and 3c = 18,300.00 are unchanged.
  - VERIFY.
- **V9. Schedule C (3g).**
  - **Under the scope report's 2026 limits:**
    - (c) $3,600 ≤ $3,600;
    - (b) 1,900 + 1,200 + 40 = 3,140 ≤ 4,000;
    - (a) covers household goods and personal possessions.
  - **Under the fixture's limits** ((c) $2,400 and the old (a) text, `ilnd_2025_data.json:40-77`):
    - (c) is $1,200 over;
    - goods and electronics fall to (b), so (b) = 4,040, $40 over.
  - **If the catalog differs,** James re-splits his own amounts; the app never does.
  - VERIFY against ilga.gov (Q23 data) and C-8.
- **V10. 122A-2 result:** not in the packet, so none. VERIFY that the packet rule still reads `is_above_median` after Q2's A+B change.

### 4. Conflicts and gaps (file:line)

- **C1. SSN.**
  - **The values:** `docs/testing/persona-briefs/james-washington.md:44` and `seed_demo_data.py:179` say 900-22-0002; `frontend/e2e/fixtures/personas.ts:162` says 900-22-2002.
  - **Pattern:** all five personas differ the same way (Maria 0001/1001), so the difference looks deliberate. But the brief says "enter this exactly".
- **C2. Age.**
  - **The values:** `james-washington.md:7` says "50 years old", but DOB 1975-03-22 (`:45`, seed `:180`) makes him 51 on the fill date.
- **C3. Stale median ($71,304).**
  - `seed_demo_data.py:169` (docstring);
  - `james-borderline.spec.ts:4,36`;
  - `test_oracle_tier3.py:97` (13C);
  - `persona-briefs/README.md` ("Passes (barely)").
  - All change with 3a1 (V1).
- **C4. `vehicle_payment` 350.**
  - **Where:** `james-washington.md:52`, `seed_demo_data.py:199`, `personas.ts:182`.
  - **Asset `amount_owed` 8,500:** `james-washington.md:63`, `seed_demo_data.py:215`, `personas.ts:198`, and the `PersonaAsset.amount_owed` type at `:40`.
  - Both are retired by Q13 in 3c.
- **C5. Household and marital fields.**
  - **Where:** `marital_status: 'single'` (`personas.ts:174`, seed `:191`), `number_of_dependents: 0` (`personas.ts:175`, seed `:192`) and `household_size: 1` (`personas.ts:166`, seed `:187`).
  - **Replaced by:** 122A-1 line 1 terms and the household list (Q2, Q17, CORR.county).
- **C6. Fee-waiver routing and verdict copy.**
  - **Routing:** `james-borderline.spec.ts:72-77` says handleComplete routes non-waiver filers to SOFA. Q21 removes `qualifies_for_fee_waiver` routing.
  - **Fixture flag:** `personas.ts:225` `fee_waiver_eligible: false` no longer describes an app decision. The fixture needs his line 8 choice instead.
  - **Verdict copy:** `:48` `toContain('eligible')` may break with DIG-146's verdict bands (3h).
- **C7. Secured flag.** The seed sets `is_secured: True` on Toyota (`:241`). `personas.ts:216-223` has no `is_secured`; it relies on the wizard's debt-type pre-selection (S3-SECURED).
- **C8. Real creditor names.**
  - **The problem:** Citibank and Toyota Financial Services are real institutions (pre-existing, `seed :229,236`). Step 3 adds addresses and last-4 digits, which this draft makes synthetic.
  - **Owner choice:** keep the real names with synthetic addresses, or rename to fictional creditors.
  - **Resolved 2026-10-16:** the owner chose fictional names. See the rename table at the top; 3a1 renames.
- **C9. Proposed new facts (owner decides).**
  - **Not covered by any ruling:** Q16 says "the owner supplies synthetic deductions", but Q28 names amounts only for Maria, DeShawn and Sarah, and the brief has no take-home figure (`scope/fee-waiver.md:147` "n/a").
  - **So these are mine:** 5a $1,288 and 5g $45 (take-home $4,500). So are A/B lines 6, 7, 11 and 16, J 4b, 10 and 13, the J 21 specify text, and the Schedule G lease.
- **C10. Story tension (no file conflict).**
  - **The numbers:** with take-home $4,500 and expenses $3,210, J 23c leaves $1,290 a month. Yet the brief has him "treading water" on a $9,800 card at $200 a month (`james-washington.md:16,68`). Today's gross-based 23c ($2,723) hides it.
  - **Owner choice:** (a) leave it, since the app shows 23c and judges nothing; or (b) add a fact that explains it. One example is court-ordered maintenance withheld on 5f, but that brings in DSO questions and a J line 19/5f choice, so this draft does not add it.
- **C11. Exemption amounts.** The fixture (`ilnd_2025_data.json:40-77`) says vehicle $2,400. The scope report quotes P.A. 104-120's $3,600 (`assets-exemptions.md:182,188`). Q23 requires statute verification before loading; this draft assumes the 2026 figures (V9).
- **No contradiction with decisions.md found.** Q13, Q14, Q21, Q23, Q24 and Q28 are applied as written. CORR.county keeps county and household off `DebtorInfo`, and this draft does too.

## Priya Sharma: step 3 persona update (approved 2026-10-16)

Target data; each step 3 PR applies its slice. Monthly figures unless marked; all synthetic. No new SSNs: Debtor 2's identity stays blank and 103B is not in her packet. "Her answer" marks a question the filer answers herself; DigniFi never answers it for her. **VERIFY** = to be worked out by hand later.

### 1. Story delta

Her husband (45) lives with her and tutors high-school students online for a tutoring company, a part-time W-2 job at $1,800 a month gross, all of it spent on the household except his own payroll taxes; this gives Q2's Column B and explains the brief's "you teach online" (:23). She drives a 2021 Honda CR-V titled in her name alone, bought used in November 2023 on a 72-month Kestrel Auto Finance loan at $450 a month; the brief already pays insurance ($180) and gas and upkeep ($60) on a car, so **DIG-282 keeps the payment and adds the car and the loan** (dropping it would leave car insurance on a car she doesn't own). In March 2025 she took a $25,000 hardship withdrawal from her 401(k) toward Westhaven's up-front deposit for her daughter's surgery; withholding didn't cover the tax and the 10% additional tax, and she now owes the IRS $3,000 on a $200-a-month installment agreement (the one addition the owner may strike: Priya is the only persona who reaches 122A-2, so it is the only persona test of line 35, DIG-275, and E/F Part 1). Both parents signed Westhaven's financial-responsibility form at admission, so her husband is a codebtor on that bill, and a collection agency now writes to her about it. They rent in Lincoln Park (Cook County) on a lease to July 2027, and her payroll and insurance details fill the everyday Schedule I and J lines a $144,000 salaried earner has.

### 2. Per PR

#### 3a1 data foundations

- Data: none. The comments citing the stale $134,366 HH4 median (`seed_demo_data.py:273-274`, `personas.ts:249-250`, `priya-ineligible.spec.ts:4-5`) move to the table in force, $137,902 (Q11).

#### 3a2 drawing engine

- None. Her lists fit their rows: D 1, E/F 2+1, G 1, H 1, one employer per column, 122A-2 13b one row.

#### 3e1 household and spouse

- **County** (Debtor step): Cook.
- **122A-1 line 1:** "Married and your spouse is NOT filing with you" → "Living in the same household and are not legally separated". Replaces `married_joint`.
- **Household list** (no names stored; everyone under 65; Priya born 1982-11-08):

| relationship | age | lives with her | claimed on her return or supported |
| ------------ | --- | -------------- | ---------------------------------- |
| spouse       | 45  | yes            | yes (joint federal return)         |
| daughter     | 10  | yes            | yes                                |
| son          | 7   | yes            | yes                                |

- **Spouse income by source** (six-month average; 122A-1 Column B, Schedule I column 2): `monthly_gross_wages` $1,800; the other nine $0, as `_wages_only` does.
- The seed keeps `household_size` 4 and `number_of_dependents` 2 unread (CORR).
- E2E: `fillDebtorInfo` adds county; `fillIncomeInfo` adds the marital answer, three household rows and the spouse's wages.

#### 3e2 income detail and expenses

- **Her answers:** Q26 "Is your income now different from that average?" No (salary unchanged; his online tutoring runs year-round). Q5: no business, no rental; interest and dividends $0 (the Chase savings pays pennies). Q6 Schedule I 8f: no government assistance.
- **Schedule I 5–10** (blank prints $0.00 in both columns under Q27, since the spouse column applies):

| Line          | Priya (col 1)                                                                 | Spouse (col 2)                                              |
| ------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------- |
| 5a            | 2,450.00 (federal 1,010, SS 706, Medicare 165, IL 569; set high, so a refund) | 250.00 (federal 35.00, SS 111.60, Medicare 26.10, IL 77.30) |
| 5b, 5d, 5f–5h | blank (5d: her 2025 draw was a withdrawal, not a loan)                        | blank                                                       |
| 5c            | 600.00 (5% voluntary to her 401(k))                                           | blank                                                       |
| 5e            | 620.00 (family health, dental, vision through work)                           | blank                                                       |
| 6 / 7         | 3,670.00 / 8,330.00                                                           | 250.00 / 1,550.00                                           |
| 8a–8h, 9      | 0.00                                                                          | 0.00                                                        |
| 10            | 8,330.00                                                                      | 1,550.00 (combined 9,880.00)                                |

- **New J lines (her answers):** 4a 0 (renter); 4b 20 (renter's insurance); 4d 0; 5 0; 10 60; 13 80; 14 50 (a standing gift she has made for years to a neighbourhood food pantry); 16 200, "Specify: IRS installment agreement, 2025 tax"; 19 0; 20a–20e 0; Other 21 specify "Children's after-school activities" for the existing $200.
- Unchanged: the brief's other figures. `insurance_not_deducted` stays one $350 on J 15 (15a/15b are step 4); its parts are in 3h.
- E2E: `fillIncomeInfo` adds 5a–5h for both columns and the "income now different" answer; `fillExpenses` adds the new lines.

#### 3f fee waiver

- **101 line 8 (`Check Box7`), her answer:** pay the entire fee when she files. The $338 fits her pay, and she would rather not ask the court for installments.
- Information shown: the family-of-4 threshold from the dated poverty table, beside her § 820.20 figure: Schedule I 12 ($9,880) less non-cash help ($0) = $9,880.
- No 103B, no `FeeWaiverApplication` (unchanged). E2E: she answers "pay in full".

#### 3b A/B

Every line walked; "No" on every line not listed.

| A/B  | Item                                                  | Who           | Entire | Portion she owns       |
| ---- | ----------------------------------------------------- | ------------- | ------ | ---------------------- |
| 3.1  | 2021 Honda CR-V EX, 41,000 miles                      | Debtor 1 only | 20,500 | 20,500                 |
| 6    | Household goods and furniture                         |               |        | 2,500                  |
| 7    | Family laptop, two phones, TV                         |               |        | 1,500                  |
| 11   | Clothes                                               |               |        | 800                    |
| 12   | Wedding and engagement rings                          |               |        | 1,200                  |
| 17.1 | Checking, JPMorgan Chase (joint with spouse)          |               |        | 1,900                  |
| 17.2 | Savings, JPMorgan Chase (joint), today's row          |               |        | 8,500                  |
| 21.1 | 401(k), her employer's plan at Vanguard               |               |        | 31,000                 |
| 31   | Term life (beneficiary: spouse); long-term disability |               |        | 0 each (no cash value) |

- **Her answer on the joint accounts:** the whole balance is her portion, because nearly all deposits come from her paychecks. That keeps today's $8,500.
- Totals: A/B 62 = 106Sum 1b = 1c = 67,900. E2E: `addAsset` per row with its A/B line.

#### 3c claims, collateral link, creditor list

Addresses marked (synthetic) are placeholders the owner confirms or replaces; every last 4 is synthetic.

| Row                                     | Address                                                                              | Last 4 | Incurred                                     | Her answers and links                                                                                                                                                                                                       |
| --------------------------------------- | ------------------------------------------------------------------------------------ | ------ | -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Kestrel Auto Finance (new, `auto_loan`) | P.O. Box 9303, Torrance, CA 90503 (synthetic)                                        | 3303   | 11/2023                                      | "Can the lender take back property?" Yes (pre-selected; she keeps it). Linked to A/B 3.1. Balance $14,900, payment $450. Lien: "An agreement you made (such as mortgage or secured car loan)". No status flags; not behind. |
| Silverpine Card Services                | P.O. Box 9313, El Paso, TX 79998 (synthetic)                                         | 3313   | 2024–2025 (most charged during the recovery) | No status flags. Payment $500 unchanged (not a J line).                                                                                                                                                                     |
| Westhaven University Medical Center     | 1653 W Congress Pkwy, Chicago, IL 60612 (public hospital address; VERIFY or replace) | 3323   | 02/2025                                      | No status flags. Codebtor: spouse, so E/F ticks "At least one of the debtors and another". Notice party: Lakeshore Medical Recovery LLC (fictional), P.O. Box 9333, Chicago, IL 60690 (synthetic), last 4 7310.             |

- **Schedule D:** A 14,900, B 20,500, C 0 (sole-owned, Q14). **J 17a** = 450 from the link; `ExpenseInfo.vehicle_payment` retired, and the seed and fixture drop the 450 (DIG-282).
- **Codebtor (H):** spouse "Rohan Sharma" (fictional; H line 3 needs a name, and Q17's "no names" covers only the household list), 456 W Fullerton Pkwy, Chicago, IL 60614, on the Westhaven row. H line 2, community property state in the last 8 years: No.
- **Contract (G):** residential lease, Fullerton Parkway Apartments LLC (fictional), Management Office, 456 W Fullerton Pkwy, Chicago, IL 60614; $2,800 a month to 07/31/2027. Personal-property lease: No. "Do you owe money on this now?" No (rent current).
- **Creditor list:** Kestrel, Silverpine, Westhaven, Lakeshore, the landlord and the spouse as codebtor; the IRS joins in 3d. Who belongs on it is C-9.
- E2E: `addDebt` adds address, link and status; the journey stops skipping steps 6 and 7 (`priya-ineligible.spec.ts:67-71`).

#### 3d priority

- **New row:** Internal Revenue Service, Centralized Insolvency Operation, P.O. Box 7346, Philadelphia, PA 19101-7346 (the IRS's published bankruptcy-notice address; VERIFY). 2025 federal income tax including the 10% additional tax on the withdrawal; total $3,000; last 4 0003 (her synthetic SSN); incurred tax year 2025; no status flags; payment $200.
- **Her answers:** "Is this one of these?" → "Taxes and certain other debts you owe the government" (the notice is a tax bill). Priority $3,000; nonpriority blank (the notice gives one balance). Past due on the filing date: $3,000 (due 04/15/2026). Silverpine and Westhaven → "No"; Kestrel is secured, so it isn't asked.
- Why here and not 3c: 106Sum 3b stays 57,000 throughout; the row carries its 3c fields with it. E2E: `addDebt` for the IRS row with the priority answers.

#### 3g Schedule C (her picks from the one catalog)

- **Line 1:** state and federal nonbankruptcy exemptions, 11 U.S.C. § 522(b)(3); 12 years in Illinois, and she read the 12-1201 note.
- **Claims:** CR-V (3.1) 735 ILCS 5/12-1001(c), "100% of fair market value, up to any applicable statutory limit"; 401(k) (21.1) 12-1006, the same wording; clothes (11) 12-1001(a), the same; checking (17.1) 12-1001(b) $1,900; savings (17.2) 12-1001(b), the rest of that subsection's limit as a dollar figure (**VERIFY** the loaded amount). No claim on goods, electronics or rings: she keeps 12-1001(b) for cash, for rent.
- **Lines 3 and 3-1:** No (no homestead).

#### 3h 122A-2 details step (her answers)

| Line       | Answer                                                                      | Why it fits her story                                                                                                                                     |
| ---------- | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2          | Column B filled; spouse filing with her: No                                 | married, filing alone                                                                                                                                     |
| 3          | Yes, $250, "his payroll taxes withheld from his pay"                        | the form's own example: "payment of the spouse's tax liability"                                                                                           |
| 5, 7b, 7e  | 4; 4 under 65; 0                                                            | all four on the joint return                                                                                                                              |
| 11, 13b    | 1 vehicle; 37 payments left × $450 = $16,650 due in 60 months               | the CR-V loan                                                                                                                                             |
| 15         | No                                                                          | he tutors from home; no transit claimed                                                                                                                   |
| 16         | expected 2026 joint refund $1,800 → 2,450 − 150 = 2,300                     | her 5a only; his taxes went on line 3                                                                                                                     |
| 17         | $0                                                                          | her 401(k) is voluntary; her job requires nothing                                                                                                         |
| 18         | $120, her own term life                                                     | of the $350 on J 15: her term life 120 + spouse's term life 50 (excluded by the line's text) + her disability 180                                         |
| 19, 20, 23 | $0                                                                          | none                                                                                                                                                      |
| 22         | No                                                                          | medical $100 is under 7g ($360)                                                                                                                           |
| 25         | health $620 (5e) + disability $180 + HSA $0 = $800; actually spends it: Yes |                                                                                                                                                           |
| 26–30      | No                                                                          | line 30: food + clothing $950 is under the $1,527 standard                                                                                                |
| 31         | Yes, $50                                                                    | the continuing gift on J 14                                                                                                                               |
| 34         | No                                                                          | not behind on the CR-V                                                                                                                                    |
| 35         | $3,000 (from 3d)                                                            |                                                                                                                                                           |
| 36         | Yes; projected plan payment $1,400                                          | salaried; debts ($60,000 unsecured, $14,900 secured) far under § 109(e) ($526,700 / $1,580,125); $1,400 is her own estimate, about half her J 23c surplus |

Line 10 stays blank (Q18); line 43 is step 4.

### 3. Outcome changes (all VERIFY: worked out by hand later)

**1. Above median, unchanged in direction.** 122A-1 (3e1): Quest11 12,000 → 13,800 (A 12,000 + B 1,800); 12B 144,000 → 165,600; 13B 4. 13C (3a1) 134,366 → 137,902, if the fill date is pinned in the 2026-04-01 period (a November 2026 table changes it). 14a stays ABOVE, by $27,698 a year. Column B prints 1,800 on line 2 and 0.00 on lines 3–10 (Q27, 3e2).

**2. Packet count.** 15 today (14 always-forms + 122A-2). 16 after 3c if the creditor list is a registry entry. 103B never applies; 108 is step 4 (17 then).

**3. Schedule I, J and 106Sum.**

| Box                            | Today               | After 3e1                            | After 3e2                    | Later                                    |
| ------------------------------ | ------------------- | ------------------------------------ | ---------------------------- | ---------------------------------------- |
| Schedule I 12, 106Sum 4, J 23a | 12,000              | 13,800 (line 7 = line 4 until 5a–5h) | 9,880                        |                                          |
| J 22a/22c, 106Sum 5            | 6,640               | 6,640                                | 7,050 (+20 +60 +80 +50 +200) | 3c moves the 450 to 17a; no total change |
| J 23c                          | 5,360               | 7,160                                | 2,830                        |                                          |
| 106Sum 8 (CMI)                 | 12,000              | 13,800                               |                              |                                          |
| 106Sum 1b/1c                   | 8,500               |                                      |                              | 67,900 (3b)                              |
| 106Sum 2                       | –                   |                                      |                              | 14,900 (3c)                              |
| 106Sum 3a / 3b / 3c            | – / 57,000 / 57,000 |                                      |                              | 3,000 / 57,000 / 60,000 (3d)             |

**4. 122A-2 estimated outline.** USTP tables for cases filed on or after 2026-07-15. Lines 6, 7a and 7d, 12, 13a and the ILN multiplier (6.9%) are from `scope/means-test-122a2.md` §4.2. Cook's 4-person figures ($953 non-mortgage, $2,219 rent) were read from justice.gov `.../20260715/bci_data/housing_charts/irs_housing_charts_IL.htm` on 2026-10-16.

| Lines             | Values                                    |
| ----------------- | ----------------------------------------- |
| 1 / 3 / 4         | 13,800.00 / 250.00 / 13,550.00            |
| 5 / 6             | 4 / 2,176.00                              |
| 7a–7g             | 90 × 4 = 360.00; 163 × 0 = 0; 7g 360.00   |
| 8 / 9a / 9b / 9c  | 953.00 / 2,219.00 / 0 / 2,219.00          |
| 11 / 12           | 1 / 334.00                                |
| 13a / 13b / 13c   | 703.00 / 277.50 / 425.50                  |
| 16 / 17 / 18 / 21 | 2,300.00 / 0 / 120.00 / 1,200.00          |
| 24                | 10,087.50                                 |
| 25 / 31 / 32      | 800.00 / 50.00 / 850.00                   |
| 33b = 33e / 34    | 277.50 / 0                                |
| 35 / 36           | 3,000 ÷ 60 = 50.00 / 1,400 × 6.9% = 96.60 |
| 37 / 38           | 424.10 / 11,361.60                        |
| 39a / 39c / 39d   | 13,550.00 / 2,188.40 / 131,304.00         |

- **Line 40:** more than $17,150 → box 2; page-1 `CheckBox1` "Presumption of abuse applies"; lines 41–42 not reached.
- **Robust:** 39c is about $1,900 a month above the $285.83 edge ($17,150 ÷ 60). Moving the spouse's $250 from line 3 to line 16 leaves 39c at 2,188.40; striking the IRS debt raises it by $50.
- The in-app verdict fails today too (`< 756.25`), so the E2E "further review" assertion (`priya-ineligible.spec.ts:55`) holds in direction; its wording and position may move with DIG-146's bands and the 3h details step.

**5. Fee waiver and 101 line 8.** No change: not in the packet; she pays in full.

**6. `test_api_readback.py:186-189`** still holds (122A-2 in her packet, figures above zero).

### 4. Conflicts found

1. **Marital status.** `seed_demo_data.py:271` and `personas.ts:247` say `married_joint`; `priya-sharma.md:49` says "Individual (filing alone)" and `seed_demo_data.py:268` `filing_type: "individual"`. Q2/3e1 resolves it (DIG-53 comment; `critic.md:225`).
2. **DIG-282.** The $450 with no car or loan is at `priya-sharma.md:54`, `seed_demo_data.py:281` and `personas.ts:257`. The brief's insurance (:55) and maintenance (:56) support keeping a car.
3. **Stale median.** $134,366 against $137,902 in force (Q11) at `seed_demo_data.py:273-274`, `personas.ts:249-250`, `priya-ineligible.spec.ts:4-5` and `test_oracle_tier3.py:130` (`13C`).
4. **Tier 3's docstring** (`test_oracle_tier3.py:5`) says the seed matches the briefs "except Priya's stale income line". It dates from 49f287e (step 1); the brief's income lines (:9, :50) were changed in a8c266e and match the seed's $12,000, so the exception reads stale.
5. **"You teach online"** (`priya-sharma.md:23`) clashes with "software engineer; your husband works part-time as a tutor" (:8). This draft makes the husband the online tutor; the owner may reword :23.
6. **Savings wording** differs (cosmetic): brief :66 "Joint savings account at Chase"; seed :295/:298 "Joint savings account" / "Chase"; `personas.ts:270` "Joint savings".
7. **Not a conflict:** the SSN differs on purpose (seed and brief 900-33-0003, `personas.ts:235` 900-33-3003); every E2E persona uses its own 900-range pattern.
8. **Probable typo, `decisions.md:294`:** "the 122A-2 line 13 marital adjustment". The marital adjustment is 122A-2 **line 3**; line 13 is vehicle ownership.
9. **Brief "Household Size 4" (:48)** and the seed's `household_size`/`number_of_dependents` (:267, :272) are superseded by the Q17 list; the brief row becomes the list.
10. **Brief "Insurance (not deducted) $350" (:61)** is one figure, but 122A-2 lines 18 and 25 need its parts; this draft adds the split (120/50/180). Not a contradiction.
11. **Q28 pins take-home** only for Maria, DeShawn and Sarah. Priya's $8,330 own / $1,550 spouse are new and unanchored; the owner should check them.
12. **Step 4, noted only:** her 90-day payments (AmEx $500 × 3, IRS $200 × 3, AHF $450 × 3) are Form 107 line 6 data, and the 2025 withdrawal and her husband's income are Form 107 lines 4–5.

## DeShawn Mitchell: step 3 persona update (approved 2026-10-16)

All figures are synthetic. The SSN stays 900-44-0004 (brief and seed). His wife gets no name, SSN or birth date in any data field: Debtor 2 identity boxes stay blank (Q2), and the household list stores no names (Q17). Creditor names are the existing seed's. Every new address, notice-party name and account last-4 below is synthetic and marked so. Answers to questions the form leaves to the filer are given as **his answer**, with the reason it fits his story. The app never makes those choices for him.

Fixed facts kept: $3,500 gross, $3,050 take-home ($450 of deductions, Q28), home $180,000 with $160,000 mortgage at $1,200/month, F-150 $8,000 paid off, 401(k) $12,000, the four debts, and the brief's 10 expense amounts ($2,295).

### 1. Story delta

DeShawn bought the Sangamon house in 2019, two years before he married, so the title and the Harrowgate mortgage are in his name alone, and his $1,200 payment includes escrow for property tax and homeowner's insurance. His wife, 44, lives with him and works weekend shifts at a neighborhood grocery store for about $1,000 a month before taxes; they file a joint federal tax return. In 2025 he was hospitalized and missed about two months of unpaid work, and that hospital bill plus the lost pay pushed the credit card, Lakeline Electric and hospital accounts into collections and made him stop his 401(k) contributions. Collection agencies now call about the Lakeline Electric and hospital bills, while Tallgrass calls about the card itself. This is an ordinary two-earner South Side household: it explains a past deficit beside a positive budget today, and it keeps him the below-median homeowner (A+B = $4,500 a month).

### 2. Per PR

#### 3a1 (data foundations)

- None. His data doesn't change. The median fix changes one printed figure (§3).

#### 3e1 (household and spouse)

- **County (OQ9.county), encrypted on the new household record:** Cook. 7823 S Sangamon St, 60620, is in Chicago.
- **122A-1 line 1, his answer:**
  - `CheckBox3` = `Married but not filing` ("Married and your spouse is NOT filing with you").
  - `CheckBox3A` = `together` ("Living in the same household and are not legally separated").
  - Why it fits: they live together and aren't separated, so the form says to fill both Columns A and B.
  - This replaces the seed's `married_joint` (DIG-53). It is stored encrypted on `IncomeInfo` (Q7.marital).
- **Household list (Q17), one person:**
  - relationship: spouse;
  - age: 44;
  - lives with him: Yes;
  - claimed on his tax return or supported by him: Yes, his answer, because they file a joint return.
  - There are no children (brief :7).
- **Spouse income by source (Q2):** the ten sources mirror his. `monthly_gross_wages` is $1,000.00; the other nine are $0.00, typed, the same way `_wages_only` types them for him.
- **Removed from use:** `household_size` 2 stays stored but unread (CORR.county).

#### 3e2 (income detail and expenses)

- **Income period (Q26):** the step names the six full months before the fill date (April 1 to September 30, 2026, for a mid-October fill).
  - His answer to "Is your income now different from that average?" is No.
  - Why: both paychecks have been steady all year, and the 2025 lost work is outside the window.
- **New sources (Q5, Q6), his answers, both columns:**
  - business income: none;
  - rental: none;
  - interest and dividends: $0. The checking account pays nothing.
  - regular government assistance (Schedule I 8f): No. The brief's "non-cash help: No" moves here from the fee-waiver page.
- **Payroll deductions (Q16), typed monthly. His column (Debtor 1):**

  | Line                                             | His answer | Why it fits                                                                                                            |
  | ------------------------------------------------ | ---------- | ---------------------------------------------------------------------------------------------------------------------- |
  | 5a Tax, Medicare, and Social Security deductions | $450.00    |                                                                                                                        |
  | 5b                                               | blank      | no mandatory plan contribution                                                                                         |
  | 5c                                               | blank      | he stopped 401(k) contributions in 2025                                                                                |
  | 5d, 5e, 5f, 5g                                   | blank      | no plan loan; no premium is deducted, since the household's insurance is the $150 on J 15d; no support order; no union |
  | 5h                                               | blank      |                                                                                                                        |
  | 6                                                | $450.00    |                                                                                                                        |
  | 7                                                | $3,050.00  |                                                                                                                        |

  - 5a must be at least FICA (7.65% × 3,500 = $267.75), and Illinois withholding (4.95%) also belongs in 5a. That puts nearly all of the $450 there.
  - $450 of tax on $3,500 is low for a married filer with a joint return. It is the owner's fixed figure, so it is kept.

- **Spouse column:**
  - 5a: $115.00 (FICA $76.50 plus about $38.50 Illinois withholding);
  - 5b to 5h: blank;
  - 6: $115.00;
  - 7: $885.00.
- **Schedule I lines 8a to 8h:** $0 in both columns. Line 9 is $0.00 in both.
- **Line 10:** $3,050 + $885 = $3,935.00. Line 11 is step 4 (blank). Line 12 is $3,935.00.
- **Schedule J new lines (Q4), his answers:**
  - **4a and 4b:** blank. His answer is that they're in his escrow, which the form excludes ("If not included in line 4").
  - **4d (HOA):** blank.
  - **5 (additional mortgage payments):** blank. He has no home-equity loan.
  - **10 (personal care):** $40.
  - **13 (entertainment):** $25.
  - **14 (charitable and religious donations):** $50, his church offering.
  - **16 (taxes not deducted):** blank.
  - **19 (support of others):** blank.
  - **20a to 20e:** blank. He has no other real property.
  - **21 Other, Specify:** "Printer ink, paper and postage" for the existing $40. He prints everything (brief :28).
- **Schedule J totals:** 22a = 22c = 23b = $2,410.00 (2,295 + 40 + 25 + 50). 23a = $3,935.00. 23c = $1,525.00.

#### 3f (fee waiver)

- **Form 101 line 8 (Q21), his answer:** `Check Box7` = `Pay in installments` ("I need to pay the fee in installments.").
  - Why: he is proud and won't ask for a waiver.
  - His checking account holds about $640 on filing day, with the mortgage due on the 1st, so he would rather pay the $338 in parts than empty it at once.
  - The alternative for the owner is "pay the entire fee" (James and Priya already take that path). DeShawn is the only persona on installments, so he alone exercises 3f's "get Form 103A from the court" message. 103A itself is step 4 (Q1).
- **Information he sees (Q22), not a verdict:**
  - "$2,705 a month for a family of 2". This is the 2026 150% table (scope/fee-waiver.md:140,184); its date is FW-5.
  - His figure: Schedule I line 12 $3,935 less non-cash help $0 = $3,935.
  - "The court decides."
- **Seed and E2E changes:**
  - No `FeeWaiverApplication` and no 103B. The seed's `fee_waiver` dict and the waiver page's answers go.
  - The journey answers line 8 instead of `feeWaiver.submit`.

#### 3b (A/B)

- **Line 1.1 (Q24):**
  - address: 7823 S Sangamon St, Chicago, IL 60620, Cook;
  - "Single-family home";
  - Who has an interest: Debtor 1 only;
  - value of the entire property $180,000, value of the portion you own $180,000 (Q14.values);
  - nature of ownership interest: "Fee simple", his answer, copied from his deed;
  - community-property box unticked.
- **Line 3.1:** Ford F-150, 2012, about 168,000 miles (synthetic). Debtor 1 only, entire $8,000, portion $8,000. **Line 4:** No.
- **Part 3, his answers:**
  - **6:** $1,500, furniture, appliances and beds. This is his share of what he and his wife own together, since the form asks for the portion he owns.
  - **7:** $400, TV, laptop and phone.
  - **11:** $300, everyday clothes and work boots.
  - **12:** $600, wedding band and watch.
  - **8 to 10, 13 and 14:** No.
  - **Line 15:** $2,800.
- **Part 4:**
  - **16 (cash):** $60.
  - **17.1:** checking account, "PNC Bank" (a real bank name, as Maria's Chase and James's BofA are; no account number), $640.
  - **21.1:** 401(k), Fidelity, $12,000.
  - **18 to 20 and 22 to 35:** No.
  - **Line 36:** $12,700.
- **Parts 5 to 7:** No.
- **Totals:** 55 $180,000; 56 $8,000; 57 $2,800; 58 $12,700; 62 $23,500; 63 $203,500.
- **Legacy rows (LEGACY-ROWS):** the seed sets each old row's line (1.1, 3.1, 21.1) explicitly, or Complete refuses.

#### 3c (claims, collateral link, creditor list)

- **Harrowgate Home Loans (Schedule D 2.1):**
  - linked to "my home" (A/B 1.1, Q13);
  - address: PO Box 4401, Chicago, IL 60680 (synthetic);
  - last 4: 0441 (synthetic);
  - date incurred: 2019.
  - **His answers:**
    - "Can the lender take back property…": Yes, pre-selected from the mortgage type, and he keeps it.
    - Nature of lien: "An agreement you made (such as mortgage or secured car loan)".
    - Contingent, unliquidated and disputed: none ticked.
    - Who owes: Debtor 1 only.
    - Notice party: No.
  - **Columns:** A $160,000; B $180,000 (he owns it alone, Q14); C = max(0, 160,000 − 180,000) = 0.
- **E/F Part 2, nonpriority, each "Debtor 1 only" with no status flags and no offset (his answers):**
  - **Tallgrass Credit Management:** PO Box 4402 (synthetic), last 4 0442, incurred 2017–2025. Notice party: No (Tallgrass calls him itself).
  - **Lakeline Electric:** PO Box 4403 (synthetic), last 4 0443, incurred 2025. Notice party: "Demo Recovery Services", PO Box 4405, Chicago, IL 60680, last 4 7443 (all synthetic).
  - **Southmoor Health:** PO Box 4404 (synthetic), last 4 0444, incurred 2025. Notice party: "Demo Medical Collections", PO Box 4406, Chicago, IL 60680, last 4 7444 (all synthetic).
- **Schedule G:** none.
- **Schedule H, his answers:** no codebtors (the accounts are in his name alone; Priya covers a spouse codebtor). Community-property state in the last 8 years: No.
- **Retired (Q13):** the home asset's `amount_owed` 160,000 and `vehicle_payment` 0.
- **Creditor list (S3-LIST):** 4 creditors plus 2 notice parties = 6 entries (who belongs is C-9).

#### 3d (priority)

- Asked "Is this one of these?" (E/F Part 1's four types), his answer is **No** for each:
  - Tallgrass: a credit card;
  - Lakeline Electric: an electric bill;
  - Advocate: a hospital bill.
- Why it fits: none is support, a tax or government debt, or an intoxication injury claim, as he reads the plain definitions (C-2).
- E/F Part 1 stays empty. He has no line 35 past-due amount.

#### 3g (Schedule C; may slip to step 4)

- **Line 1, his answer:** "state and federal nonbankruptcy exemptions, 11 U.S.C. § 522(b)(3)". He has lived in Illinois all his life (well past 730 days) and reads the 12-1201 note.
- **Line 2 rows, his picks from the one list (C-STACK one row per item and law):**
  - home, A/B 1.1 → 735 ILCS 5/12-901, $15,000;
  - F-150, A/B 3.1 → 12-1001(c), $2,400;
  - F-150, A/B 3.1 → 12-1001(b), $4,000. His reason: he needs the truck to get to the warehouse.
  - 401(k), A/B 21.1 → 735 ILCS 5/12-1006, "100% of fair market value, up to any applicable statutory limit";
  - clothes, A/B 11 → 12-1001(a), 100%.
- **Left unclaimed:** furniture, electronics, jewelry, cash and checking. That is his choice, and the app's neutral per-law totals show 12-1001(b) at $4,000 against its $4,000 limit.
- **Limits:** taken from `ilnd_2025_data.json:39-41,51-53,63-65`, to be verified against the statute per Q23.
- **Line 3** (homestead over the form's threshold), his answer: No.
- **Brief "What to watch for", new:** his equity ($20,000) is more than the homestead amount he typed. Does the app say what the form shows, without predicting what the trustee will do?

#### 3h (122A-2)

- None. He is below the median, so 122A-2 is not in his packet and line 36 is never asked.

### 3. Outcome changes (each VERIFY: worked out by hand later)

**After 3a1**

- 122A-1 `13C`: 91,526 → **93,934**. This is the in-force Illinois 2-person median for a fill date from 2026-04-01 (decisions.md:138), and it follows the pinned fill date. VERIFY: worked out by hand later.
- The legacy 60% flag threshold becomes 0.6 × 93,934 = $56,360.40 a year. VERIFY: worked out by hand later.

**After 3e1**

| Box                             | Before         | After                      |
| ------------------------------- | -------------- | -------------------------- |
| `Debto1.Quest11` (row restored) | (not asserted) | 3,500.00                   |
| `Debto2.Quest2.0`               | (none)         | 1,000.00                   |
| `Debto2.Quest11`                | (none)         | 1,000.00                   |
| `Quest11` (both widgets)        | 3,500          | **4,500.00**               |
| `12B`                           | 42,000         | **54,000.00** (4,500 × 12) |
| `13B`                           | 2              | 2 (unchanged)              |
| `14a`                           | below          | below (54,000 < 93,934)    |
| 106Sum `8` (cmi)                | 3,500          | 4,500                      |
| 101 `Debtor1.County`            | blank          | Cook                       |

- Column B lines 3–10 print 0.00 from 3e1 on: the spouse's other nine sources are typed $0 (the existing typed-$0 rule, not Q27).

- Interim gross on both columns, until 3e2: Schedule I `Amount 12`, 106Sum `4` and J `23a` = 4,500; J `23c` = 4,500 − 2,295 = 2,205. VERIFY: worked out by hand later.
- **Fee-waiver flag stays True until 3f:** 54,000 < 56,360.40 (and < 54,915.60 on the old fixture), so the packet stays at 15 and `WAIVER_FILERS` holds. The spouse figure was kept modest partly so that DeShawn's 15→14 lands in 3f, where Q21 puts it. A spouse gross above $1,196.70 would move the flip into 3e1. VERIFY: worked out by hand later.
- Schedule J line 2: whether his wife appears as a dependent row depends on the 3e1 rule (see §4). VERIFY: worked out by hand later.

**After 3e2**

- Schedule I:
  - `Amount 7`: Debtor 1 3,050, spouse 885;
  - line 10: 3,935;
  - `Amount 12`: **3,935.00**.
- 106Sum `4`: 3,935. 106Sum `5`: 2,295 → **2,410**.
- J `22a`/`22c`/`23b`: 2,410; `23a`: 3,935; `23c`: 1,205 → **1,525**.
- Q27 ($0.00 for lines that were asked and left blank, both columns, since both apply):
  - `Debto1.Quest7` "" → 0.00;
  - Schedule I `Amount 8b Debtor 1` "" → 0.00;
  - Schedule I 5b to 5h → 0.00 in both columns.
- 122A-1 is unchanged from 3e1, because deductions don't touch CMI. VERIFY: worked out by hand later.

**After 3f**

- Packet 15 → **14**: no 103B, and 101 `Check Box7` = installments.
- His § 820.20 figure is $3,935 against $2,705. VERIFY: worked out by hand later.

**After 3b**

- 106Sum `1a` 180,000 (unchanged); `1b` 20,000 → **23,500**; `1c` 200,000 → **203,500**. VERIFY: worked out by hand later.

**After 3c**

- Schedule D: Column B 180,000. Column C = 0, and whether it prints "0.00" or blank is the 3c spec's call.
- 106Sum `2`, `3b` and `3c` unchanged (160,000; 11,700; 171,700).
- If the creditor list is a `packet()` entry, the count goes 14 → 15. VERIFY: worked out by hand later.

**3d, 3g, 3h:** no count change. 122A-2 stays out (54,000 < 93,934). VERIFY: worked out by hand later.

**Step 4 (not counted):** Form 108 joins his packet (secured mortgage), and 103A follows his installments choice.

### 4. Conflicts and gaps (file:line)

1. **Marital status:**
   - `marital_status: "married_joint"` at `seed_demo_data.py:345` and `personas.ts:315`
   - contradicts "Individual (filing alone)" at `deshawn-mitchell.md:51` and `filing_type: individual` at seed `:342` and `personas.ts:308`.
   - Q2 and DIG-53 settle it in 3e1.
2. **Wife's income:** `deshawn-mitchell.md:9` says "your wife's income is not part of it". Q2 requires it in Column B and Schedule I column 2, so the line must be rewritten.
3. **Age:** the brief says "45 years old" (`:7`), but the DOB 09/03/1980 (`:46`, seed `:334`) makes him 46 on 2026-10-16. I'm reporting it, not picking.
4. **Fee waiver:** these all assume eligibility that Q21, Q22 and DIG-145 remove:
   - brief `:63-64`;
   - seed `:421-426` and `:605-615` (the application keyed on the 60% flag);
   - `personas.ts:381-384` ("$54,915.60" is 60% of the stale fixture median);
   - `deshawn-assets.spec.ts:78-84` and `:93` (`generateAllForms(15)`);
   - `test_api_readback.py:38` (`WAIVER_FILERS`).
5. **Retired by Q13:**
   - the home asset's `amount_owed: 160000` (seed `:369`, `personas.ts:339`);
   - `vehicle_payment` (seed `:353`, `personas.ts:323`).
6. **Household size:** brief `:50`, seed `:341` and `personas.ts:307` are replaced by the household list (Q17). `PersonaIncome` (`personas.ts:30-34`) has no spouse or deductions shape yet.
7. **Tier 3:** DeShawn's `Debto1.Quest11` was removed on purpose in 07ad5a6 (step 2b Q1, pending spouse data). It is absent at `test_oracle_tier3.py:159-167`, while Maria (`:58`), James (`:93`) and Sarah (`:193`) keep theirs. 3e1 restores it with `Debto2.Quest11`. 106Sum `8` is asserted for no persona.
8. **SSN:** the E2E SSN is 900-44-4004 (`personas.ts:303`) against 900-44-0004 (brief `:45`, seed `:333`). All five personas carry the same systematic offset, so it looks deliberate. Both are in the 900 range, and I changed nothing.
9. **Source for J line 4:** `rent_or_mortgage` $1,200 (seed `:350`) duplicates the mortgage's `monthly_payment` (seed `:390`). Q13 makes the debt the only source but names only J 17, not J 4, and DeShawn is the only mortgage persona. That's for the 3c/3e2 specs.
10. **Schedule J line 3 is unplaced:** no PR in `pr-map.md` places it ("expenses of people other than yourself and your dependents"). His expenses include his wife's, so his answer would be Yes. It is unbound today.
11. **Household-list wording:** "claimed on your tax return" is ambiguous for a spouse on a joint return. That decides whether she becomes a J line 2 row and how 103B line 1 counts her (the 3e1 spec; C-3).
12. **Exemption catalog:** the fixture carries only four laws (`ilnd_2025_data.json:39-77`). 12-1006 and 12-1001(a), which he picks, must come from 3g's catalog. The fixture's "Married couples filing jointly can double" text (`:42`) is irrelevant to him but is advice-shaped. Brief `:82` "$15,000" should cite the dated catalog (Q10, Q23).
13. **Realism, for the owner's judgment:**
    - J 23c is $1,525/month of surplus against $11,700 of unsecured debt in collections. The 2025 story explains the past deficit, but the fixed budget looks thin for two adults: $350 food, and $50 transportation that has to cover gas for a pickup.
    - The owner may raise expenses or lower the spouse figure. Nothing here changed the fixed amounts. A $640 checking balance also sits oddly beside the surplus, and it is the stated reason for installments, so that reason moves with any budget change.
14. **Option not taken:** ComEd in both names would make his wife a Schedule H codebtor, but it needs her name on H, so I left it out.

## Sarah Chen: step 3 persona update (approved 2026-10-16)

The figures are synthetic, and so are all new names, addresses and last-4 digits. The SSN stays at 900-55-0005 (the E2E fixture uses 900-55-5005, the same per-persona pattern as the others). Every answer below is **Sarah's own answer**, with the reason it fits her story. None of them is the app deciding for her.

The draft pins a **fill date of 2026-10-15** (the same date as the other drafts), and everything dated is derived from it:

- the six-month window is April 1 through September 30, 2026;
- the median table in force is the one for cases filed on or after 2026-04-01 (Q11);
- the HHS table in force is the 2026 guidelines; 150% for a family of 1 is $1,995.00 a month (`scope/fee-waiver.md:184`).

### 1. Story delta

Sarah rents one bedroom of a shared two-bedroom at 1520 N Damen Ave, in Cook County, on an individual lease in her own name ($850 a month, renewed each July). Her roommate has a separate lease with the same landlord and pays the landlord directly, so no roommate money passes through Sarah: Schedule I line 11 stays empty and J line 4 stays $850. The bookstore pays her twice a month, $1,000 gross per check with $125 withheld for taxes, Social Security and Medicare, which gives the brief's $2,000 gross and $1,750 take-home; the part-time job offers no retirement plan and no health insurance, which is why the February 2026 ER visit was uninsured. That Lakemont Health bill has since gone to a collection agency that writes to her. She took out the Keelson Loan Servicing loan across 2016–2020 and finished her degree in spring 2020, during the COVID recession, which squares the brief's "graduated during a recession" with her 1995 birth date. Everything else is unchanged: no spouse, no dependents, no car, no assets and no priority debt.

### 2. Per PR

#### 3a1 (data foundations)

- **Data:** none.
- The median now comes from the dated table in force on the fill date (Q10, Q11); see §3.2.
- **3a2 (drawing engine):** none either. Two creditors, one notice party and one lease fit the official pages, so she gets no continuation copy and no attached sheet.

#### 3e1 (household and spouse)

- **Marital status (122A-1 line 1):** her answer is "Not married" (`CheckBox3` = `Not married`). Column B and Schedule I column 2 stay blank, and no spouse income is asked.
- **County (Debtor step):** Cook. Form 101 `Debtor1.County` prints "Cook" (DIG-277).
- **Household list (Q17):** one row, all her answers.
  - The row: relationship "roommate"; age 29; lives with Sarah: yes; claimed on her tax return or supported by her: no.
  - Why: the list asks for the people in her home, and her roommate lives there. She supports no one. No name is stored.
- **What each form derives from the list:**
  - Schedule J line 2, "Do you have dependents?": No.
  - 103B line 1: 1 (you; no spouse; no dependents).
  - 122A-1 line 13: 2 under C-3's default (the people who live with the filer), or 1 under the IRS-dependents or economic-unit readings. VERIFY, §3.3.
  - Among the drafts so far (Maria, James, Priya), Sarah is the only persona whose household and family counts differ, so she tests that each form uses its own definition.
- **Replaced:** `DebtorInfo.household_size` 1 (left unread) and `IncomeInfo.number_of_dependents` 0.

#### 3e2 (income detail and expenses)

- **Six-month average (Q26):** wages $2,000.00 for April 1 – September 30, 2026; the other nine sources $0.00, as `_wages_only` stores them today.
- **"Is your income now different from that average?":** her answer is No. Her hours have been the same all year, so Schedule I uses the same set.
- **Business or self-employment (122A-1 5A–5C, Schedule I 8a):** none. **Rental split (6A/6B):** none.
- **Interest and dividends (122A-1 line 7, Schedule I 8b):** none.
- **Schedule I 8f (Q6):** her answer to regular government assistance is No. It is asked here now, not on the fee-waiver page.
- **Payroll deductions (Q16),** monthly, from her pay stub ($125 per check × 2 checks a month):
  - 5a Tax, Medicare, and Social Security deductions: **$250.00**.
  - 5b–5h: she leaves them blank. She has no retirement plan, no insurance through work, no retirement loan, no support order, no union and no other deductions. They print $0.00 (Q27).
  - Line 6 = $250.00; line 7 = $2,000.00 − $250.00 = $1,750.00.
  - Twice-monthly pay exercises the help text's per-paycheck conversion with exact cents.
- **Expenses (Q4): her answers on the never-asked Schedule J lines.**
  - 4a, 4b (she has no renter's insurance), 4d and 5: $0. She rents and owns no home.
  - 10 Personal care products and services: **$30**.
  - 13 Entertainment, clubs, recreation, newspapers, magazines, and books: **$20** (books at her staff discount, one streaming plan).
  - 14, 16, 19 and 20a–20e: $0.
  - 21 Other: **$0**, down from $50. Her $50 "Other Necessary Expenses" was personal care and books, and those now have their own lines, so the total is unchanged.
  - **Unchanged:** J 4 $850, 6d $80, 7 $250, 9 $30, 11 $20; 12 Transportation $0 (but see the transit gap in §4).
- **122A-2-only deductions:** not asked. She is below the median.

#### 3f (fee waiver)

- **Form 101 line 8 (Q21):** her answer is "I request that my fee be waived" (`Check Box7` = `Request fees waived`).
  - Beside the question she sees the court's figure for a family of 1 ($1,995.00 a month), her own § 820.20 figure ($1,750.00, which is Schedule I line 12 less $0 non-cash help), and "the court decides" (Q22).
  - Why: she has no savings and can't pay $338 at filing. She has read that the judge also weighs whether she could pay in installments, and she knows her Schedule J shows $470 left each month. She asks anyway, because that weighing is the court's call, not hers or the app's.
  - The app never tells her she qualifies, and nothing routes her anywhere.
- **103B:**
  - Line 1: "You" ticked, total 1, derived from her list.
  - Line 2: take-home pre-filled from Schedule I, $1,750.00, which she confirms (`undefined_2`, `undefined_4`, `undefined_6`).
  - Line 3: No, read from her 8f answer.
  - Line 6: `undefined_7` = J 22c = $1,280.00.
- **Seed:** her application exists because her line 8 answer is the waiver, not because of `qualifies_for_fee_waiver`.
- **Brief:** the two "(fee waiver page)" rows move to the Income step (5a, 8f). Add a row for line 8.

#### 3b (A/B)

- **None** in the target. She walks every A/B line (Q24) and answers No to each. She has no legacy rows.
- The owner call on this (her phone, laptop and the account her pay goes into) is in §4.

#### 3c (claims, collateral link, creditor list)

- **Keelson Loan Servicing student loan, $28,000 (E/F Part 2, "Student loans"):**
  - Address: Keelson Loan Servicing, 60 Demo Way, Wilkes-Barre, PA 18773. Last 4: 6006. Incurred: 2016–2020.
  - "Can the lender take back property?": No (pre-selected from the debt type; she keeps it).
  - Contingent, unliquidated, disputed and offset: all No, by her answers.
  - Codebtor: none (she signed alone). Notice party: none (Keelson Loan Servicing writes to her itself).
- **Lakemont University Hospital, $3,400 (E/F Part 2, other: medical):**
  - Address: Lakemont Health Patient Accounts, 70 Demo Plaza, Chicago, IL 60612. Last 4: 7007. Incurred: 02/2026 (the ER visit).
  - "Can the lender take back property?": No.
  - Status flags: all No. She agrees she owes it, and the bill fixes the amount.
  - **"Is anyone else contacting you about this debt?" (S3-NOTICE):** Yes, "Wicker Demo Recovery LLC, 80 Demo Ct, Oak Brook, IL 60523", last 4 "8008". This matches `is_in_collections: True`.
- **Schedule G:**
  - "Damen Demo Flats LLC, 90 Demo St, Chicago, IL 60622". Residential lease for one bedroom at 1520 N Damen Ave Apt 2F, $850/month, current term 07/01/2026–06/30/2027.
  - Kind: residential, not a vehicle and not a personal-property lease (the Form 108 flag is false).
  - "Do you owe money on this now?" (S3-GCLAIM): No; her rent is current.
- **Schedule H:** none. The lease is hers alone, and nobody co-signed anything.
- **Debt-to-asset link:** none. Both debts are unsecured, so Schedule D stays empty.
- **Creditor list (S3-LIST):** 2 creditors, 1 notice party and the landlord, so 4 entries (who belongs is C-9).
- **E2E:** the fixture gains the addresses, the notice party and the lease, and step 6 is filled instead of skipped.

#### 3d (priority)

- **E/F Part 1 "Is this one of these?":** her answer is "No" for both debts. `is_priority` is false on each, stored as an answer rather than "Not sure". There is no split and no past-due amount.
- **Why it fits:** she owes no support (no children, never married), no taxes (W-2 wages with withholding) and no injury claim.
- **The hospital is a state hospital.** Her "No" to "taxes and certain other debts you owe the government" is a live test of C-2's plain wording; see §4.
- **Priority debt: none.** Brief:12 says "just student loans and a medical bill", and adding one would end her simplest-case role.
  - Priya's draft already carries Q15's priority debt (`personas/priya.md:88-91`, a 2025 IRS balance). That is the better fit: she is above the median, so the debt also exercises 122A-2 line 35 ÷ 60 (DIG-275) and lines 41–42.
  - If a second is wanted, the sixth persona (gig driver) fits: unpaid self-employment tax on 1099 income.

#### 3g (Schedule C)

- **Line 1:** her answer is "You are claiming state and federal nonbankruptcy exemptions. 11 U.S.C. § 522(b)(3)." She has lived in Illinois her whole adult life, well past 730 days, and she reads the 12-1201 note beside the question.
- **Line 2 rows:** none; she has no property.
- **Line 3** (homestead over the § 522(p) amount): No.
- VERIFY: does 3g ask line 1, and does C's `requires()` refuse without it (Q12), for a filer whose A/B is empty?

#### 3h (122A-2)

- **None.** She is below the median, so 122A-2 is not in her packet. Line 36, the claimable deductions and the result ticks are never asked.

### 3. Outcome changes (each VERIFY: worked out by hand later)

1. **Packet count stays 15:** the 14 forms every filer gets, plus 103B. 103B is now there because she asked for the waiver on line 8, not because of the computed flag. **VERIFY:** it becomes 16 if 3c's creditor list is a registry entry that Generate All counts (`sarah-simplest.spec.ts:92`).
2. **Median (3a1):** 122A-1 13C goes from 71,304.00 to **73,180.00** (Illinois, 1 person, Q11). 12B stays 24,000.00 (2,000 × 12). Below the median: 24,000 ≤ 73,180; 14a is unchanged. **VERIFY**
3. **Household (3e1):**
   - Under C-3's default, 13B goes from 1 to **2** and 13C to **93,934.00**.
   - Under the IRS-dependents or economic-unit readings, it stays 1 and 73,180.00.
   - She is below the median either way: 24,000 < 73,180 < 93,934.
   - **VERIFY** after C-3.
4. **122A-1 (3e2):** Quest7 goes from "" to **0.00** (asked, $0, Q27), and the new 5A–5C and 6A/6B boxes print 0.00. Quest11 and its copy stay 2,000.00: CMI is gross, so deductions don't touch it. **VERIFY**
5. **Schedule I (3e2):**
   - 5a 250.00; 5b–5h 0.00; 6 250.00.
   - 7 goes from 2,000.00 to **1,750.00**.
   - 8a 0.00; 8b goes from "" to **0.00**; 8f 0.00; 9 0.00.
   - 10 and 12 go from 2,000.00 to **1,750.00** (1,750 + 0; line 11 stays blank until step 4).
   - Column 2 stays blank. **VERIFY**
6. **Schedule J (3e2):**
   - 10 prints 30.00 and 13 prints 20.00. 21 goes from 50.00 to blank, since a $0 expense prints blank on J.
   - 22a, 22c and 23b stay 1,280.00 (850 + 80 + 250 + 30 + 20 + 30 + 20).
   - 23a goes from 2,000.00 to **1,750.00**, and 23c from 720.00 to **470.00** (1,750 − 1,280). **VERIFY**
7. **106Sum (3e2):** line 4 goes from 2,000.00 to **1,750.00**. Line 5 stays 1,280.00, and 3b/3c stay 31,400.00 (28,000 + 3,400). The CMI line stays 2,000.00. **VERIFY**
8. **Fee waiver (3f):**
   - 101 `Check Box7` goes from blank to `Request fees waived`.
   - 103B: line 1 total 1; line 2's three boxes 1,750.00; line 6 1,280.00.
   - **The Q22 test case holds.** Her § 820.20 figure is $1,750 < $1,995.00, with $245 to spare. On CMI she would be at $2,000 ≥ $1,995. **VERIFY**
   - Today's flag (`eligibility/models.py:177`) gives 24,000 < 0.6 × 71,304 = 42,782.40, so True. After 3f it decides nothing.
   - **Fragile:**
     - The 2027 HHS table (January 2027, about +2%, like 2025→2026's 15,650→15,960) puts 150% for one person near 16,279 × 1.5 ÷ 12 ≈ $2,035. Her $2,000 CMI would then also be under it, and she would stop separating the two measures. Tests pin the fill date (CORR.valid_through), so CI is safe; the persona isn't, after January.
     - Any roommate money to Sarah lands on Schedule I line 11 (step 4) and adds to line 12. More than $245 a month crosses $1,995. Her own-name, per-room lease is what keeps it at $0.
9. **101 County (3e1):** goes from blank to **Cook**. `CheckBox3` = `Not married`. **VERIFY**
10. **122A-2:** not in her packet; nothing changes.

### 4. Conflicts and owner questions

**Brief against decisions.md:**

- `sarah-chen.md:72`: "Is the fee waiver mentioned clearly? You qualify." This contradicts Q22 (the app never says "you qualify"; the court decides) and Q21 (no computed routing). Proposed: "Is it clear how to ask for a fee waiver and what the court looks at? You plan to ask for one."
- `sarah-chen.md:56-57`: take-home and non-cash help are listed as fee-waiver-page answers. After 3e2/3f they are Income-step answers (5a $250, 8f No), and the page pre-fills or reads them (Q6, Q16).
- `sarah-chen.md:7`, "single": the step asks 122A-1 line 1's words, so her answer is "Not married".
- `README.md:20`, "Passes, fee waiver": suggest "Passes, asks for a fee waiver" (Q21).

**Seed (`seed_demo_data.py`):**

- `:431` says "fee waiver eligible", and `:605-615` creates the application only when `qualifies_for_fee_waiver` (the 60%-of-median flag) is true. Under Q21 her line 8 answer creates it.
- `:610` sets household size from `DebtorInfo`; it should come from her list (DIG-223).
- `:449` `household_size` 1 and `:454` `number_of_dependents` 0 stay but go unread (CORR.county).

**E2E:**

- `sarah-simplest.spec.ts:4`, `:39` and `:78` ("fee-waiver eligible → routed"): the routing is gone (Q21), and the journey answers line 8 itself.
- `:47-56`: the preview test expects "fee waiver" or "filing fee" text. Under Q22 that text is information (the threshold and her figure); re-pin it to that wording.
- `:68`: "Contracts & Leases (optional — no entries needed)". She now enters her lease. `:71` (codebtors) stays empty.
- `:79-83`: `feeWaiver.submit(household_size, take_home, noncash)`. Line 1 now comes from the list and line 3 from 8f, so the call changes.
- `:92`, `generateAllForms(15)`: see §3.1.
- `personas.ts:443`: `expected.fee_waiver_eligible: true` is a computed verdict that Q21/Q22 retire. Replace it with her line 8 choice (`waiver`).
- `personas.ts:25`: the comment "household_size mirrors seed_demo_data: dependents + 1 (+1 if married)". Her list (herself plus a roommate) breaks that formula.
- `scanned-bill-journey.spec.ts:44` spreads `SARAH`, and `:102` relies on "no assets" at Assets. Every `SARAH` change (county, deductions, the A/B walk, the lease at step 6) reaches that journey too.

**Backend tests:**

- `test_api_readback.py:36-38`: the comment on `WAIVER_FILERS` says "the means test qualifies these personas".
- `test_api_readback.py:129-130`: asserts `qualifies_for_fee_waiver == (persona in WAIVER_FILERS)`. Under Q21 membership is her line 8 choice. Any 150%-of-poverty test run on her CMI gives False (2,000 ≥ 1,995).
- `test_oracle_tier3.py`, lines that change per §3: `:187`, `:191`, `:196-197`, `:201`, `:203`, `:209`, `:211`.
- Tier 3 cases to add: 101 County and `Check Box7`; 122A-1 `CheckBox3`; Schedule I 5a, 6 and 7; J 10, 13 and 23c; 103B line 2.

**Owner calls (story gaps; the draft keeps the owner's facts):**

- **Assets.** Brief:61 says none, and `README.md:20` makes her the empty-state case.
  - **The tension:** brief:24-25 has her typing on a phone and a laptop, her pay lands in some account, and Q24's walk prints each line's examples.
  - **What a careful filer would answer Yes to:**
    - line 7, electronics (phone and laptop, $350);
    - line 11, clothes ($200);
    - line 17.1, checking ($120).
  - **What that alternative does:**
    - 106Sum 1b/1c become 670.00;
    - 3g gains rows: her picks of law and amount, from the one catalog;
    - the walk lengthens against her 15-minute target;
    - the scanned-bill journey loses "no assets";
    - no persona is left testing an empty A/B.
- **Transit.** J 12 is $0 in the brief and seed, but she has no car in Chicago, and the step's help text names public transit (`ExpenseInfoStep.tsx:191`). A CTA 30-day pass, about $75 (VERIFY the fare), changes:

  - 22a/22c/23b and 106Sum line 5 to 1,355.00;
  - 23c to 395.00;
  - 103B line 6 to 1,355.00.

  Nothing else moves.

- **Withholding realism.** $250 on $2,000 is light:

  - Social Security plus Medicare alone is $153.00 (7.65%);
  - Illinois is about $87 (4.95% after the exemption);
  - federal is roughly $50–75;
  - so roughly $290–315 in all.

  Q28 fixed $250, and the draft keeps it. If the owner wants realism, about $1,700 take-home still sits under $1,995.

- **Installments against the waiver.** Her sworn J 23c shows $470 a month left ($395 with transit), and four installments of $338 come to about $85 each. A judge reading 103B line 6 against her income could order installments. This changes no app outcome, but the persona's reviewers should expect it; the brief should not imply the waiver is certain.
- **Her $50 "Other" moved.** This is a change to an owner-fixed brief row: the draft moves her $50 onto J 10 ($30) and J 13 ($20), with the same total. To approve, or keep $50 on line 21.
- **Graduation year.** With a 1995 birth date, the usual 2017 graduation was not in a recession. The draft uses spring 2020, which gives a loan incurred 2016–2020.
- **C-2 path.** If counsel wants "Not sure" exercised, Sarah's state-hospital bill is the natural place: Q15 keeps a "Not sure" debt in Part 2 with a legal-aid note, so no total moves.

**Against decisions.md:** no other conflict found. Q28's "Sarah $250", the $1,750 take-home, the nonpriority student loan and the seed's figures all agree.

## Andrés Kettleby: sixth persona, gig driver (approved 2026-10-16)

Everything here is synthetic: the name, addresses, private creditor names, figures and last-4 digits. SSNs: 900-66-0006 in the brief and seed, and 900-66-6006 in the E2E fixture, following the split the other five use (§4.9). Phone numbers are in 555-0100–0199, the block reserved for fiction. Every answer marked "his answer" belongs to Andrés, with the reason it fits his story. None of them is the app deciding for him.

Like the other drafts, this one pins the **fill date at 2026-10-15**:

- the six-month window is April 1 through September 30, 2026;
- the median table is the one in force on or after 2026-04-01; for a household of 2 it is $93,934 (Q11);
- the 150% HHS figure for a family of 2 is $2,705.00 a month (`scope/fee-waiver.md:184`).

### 1. Story delta

Andrés, 38, a never-married father of a 9-year-old, drives rideshare and food delivery around Aurora, which spans four counties; his lease and license say Kane. He is self-employed with no withholding, which is how he came to owe the IRS for 2025. In 2025 he leased a 2024 Corolla Hybrid because his old car was too old for the rideshare app, and in 2022 he co-signed his brother Mateo's car loan, so the 2017 Honda Fit is titled to both of them while Mateo drives it and pays. Nine unsecured creditors came from about eight lean months: his daughter's ER visit, a forced move, a payday-style loan for rent, and tolls that piled up while his transponder was broken. All of this is ordinary for an ILND gig driver, and together it exercises every step 3 feature the other five don't: Q5's business split, a vehicle lease on G, co-owned collateral on D, the E/F overflow, a notice party and a codebtor. He is below the median, so 122A-2 never applies.

---

## Andrés Kettleby — Persona Brief for AI Testing Agent

You ARE Andrés Kettleby. Navigate DigniFi as he would.

### Who You Are

- 38 years old, never married, single father of a daughter, age 9, who lives with you full time.
- Her mother lives in Indiana. She pays no support, and keeps your daughter on her employer's health plan.
- You drive for rideshare and delivery apps about 50 hours a week. You are self-employed, with no boss and no paycheck.
- Over the last six months the apps paid you about $4,200 a month. Driving costs you about $830 a month, so you keep about $3,370.
- You rent a 2-bedroom apartment in Aurora (Kane County) for $1,150 a month.
- You lease a 2024 Toyota Corolla Hybrid ($389 a month), the car you drive for work.
- Your name is on your brother Mateo's 2017 Honda Fit and its loan. He drives it and pays it.

### Your Emotional State

- Scared about the Corolla. With no car you have no income.
- Guilty about Mateo. You co-signed so he could get to his job, and you don't want this to land on him.
- The IRS letter frightened you most. You never knew the apps don't take out taxes.
- Angry about your old landlord's $1,850 damage bill. You left the place clean and you have the photos.
- You work hard. Being called "unemployed", or "a business", stings.

### Your Tech Comfort

- You live on your phone (the driver apps, your banking app) and fill DigniFi in on it in short bursts between rides.
- You expect your work to save if a ride request interrupts you.
- You copy creditor addresses from photos of your mail, and typing nine of them tests your patience.

### How You Read

- You finished high school and read English well. You speak Spanish with your mother.
- You know "earnings", "tips" and "payout". "Gross receipts", "ordinary and necessary", "executory contract" and "unliquidated" are new to you.
- You read anything about the Corolla or Mateo twice, and you skim the rest.

### Your Data (enter this exactly)

| Field                                                              | Value                                                                                                                                           |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| First / middle / last name                                         | Andrés / J / Kettleby                                                                                                                           |
| SSN · Date of birth                                                | 900-66-0006 · 04/12/1988                                                                                                                        |
| Phone · Email                                                      | 630-555-0161 · andres.kettleby@demo.dignifi.org                                                                                                 |
| Address · County                                                   | 1418 Marquette Ave Apt 2, Aurora, IL 60505 · Kane                                                                                               |
| Marital status (122A-1 line 1)                                     | Not married                                                                                                                                     |
| People in your home                                                | Daughter, age 9, lives with you: Yes, claimed on your tax return: Yes                                                                           |
| Business gross receipts, 6-month average (122A-1 5a)               | $4,200 (Apr 3,950 · May 4,300 · Jun 4,450 · Jul 4,050 · Aug 4,280 · Sep 4,170)                                                                  |
| Ordinary and necessary operating expenses (122A-1 5b)              | $830: gas 560, rideshare insurance add-on 35, phone/data share 45, washes 40, tolls/parking 50, oil and tires 60, supplies 15, cash-out fees 25 |
| Every other income box, interest included                          | $0                                                                                                                                              |
| Payroll deductions (Schedule I 5a–5h)                              | leave blank (no paycheck)                                                                                                                       |
| Government help (Schedule I 8f)                                    | No                                                                                                                                              |
| Is your income now different from that average?                    | No                                                                                                                                              |
| Rent (J 4) · Renter's insurance (J 4b)                             | $1,150 · $15                                                                                                                                    |
| Utilities: electric, gas, internet, your share of the phone (J 6d) | $210                                                                                                                                            |
| Food (J 7) · After-school program (J 8) · Clothing (J 9)           | $520 · $180 · $60                                                                                                                               |
| Personal care (J 10) · Medical (J 11)                              | $40 · $45                                                                                                                                       |
| Transportation: gas for school runs and errands (J 12)             | $60                                                                                                                                             |
| Entertainment (J 13) · Donations (J 14)                            | $30 · $20                                                                                                                                       |
| Vehicle insurance, your personal policy (J 15c)                    | $165                                                                                                                                            |
| Taxes (J 16), specify "2026 estimated income tax"                  | $150                                                                                                                                            |
| Every other Schedule J line                                        | $0                                                                                                                                              |
| How you will pay the fee (Form 101 line 8)                         | I need to pay the fee in installments                                                                                                           |

**Assets (Schedule A/B):**

| Line | Item                                                               | Who has an interest  | Entire | Portion |
| ---- | ------------------------------------------------------------------ | -------------------- | ------ | ------- |
| 3.1  | 2024 Toyota Corolla Hybrid, about 61,000 miles, leased (see G 2.1) | Debtor 1 only        | $0     | $0      |
| 3.2  | 2017 Honda Fit, about 96,000 miles, titled to you and Mateo        | You and someone else | $8,600 | $4,300  |
| 6    | Beds, couch, table, kitchen things                                 |                      |        | $1,200  |
| 7    | Phone, TV                                                          |                      |        | $400    |
| 11   | Clothes                                                            |                      |        | $300    |
| 16   | Cash                                                               |                      |        | $60     |
| 17.1 | Checking, Harborline Bank                                          |                      |        | $412    |
| 17.2 | Share savings, Prairie Line Credit Union                           |                      |        | $85     |
| 38   | Driving payouts already earned, not yet paid by the apps           |                      |        | $310    |
| 40   | Insulated delivery bags, phone mount, dash camera                  |                      |        | $150    |

**Amounts Owed.** You pay $0 a month on every one of these. E/F Part 2 is in alphabetical order.

| Row     | Creditor and address                                                                                 | What                                 | Amount | Since         | Your answers                                                                              |
| ------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------ | ------ | ------------- | ----------------------------------------------------------------------------------------- |
| D 2.1   | Copperline Auto Finance, PO Box 48210, Schaumburg, IL 60168                                          | Mateo's Fit loan you co-signed       | $7,800 | 08/15/2022    | secured by A/B 3.2; lender can take it back: Yes; "An agreement you made"; codebtor Mateo |
| E/F 2.1 | Internal Revenue Service, Centralized Insolvency Operation, PO Box 7346, Philadelphia, PA 19101-7346 | 2025 income and self-employment tax  | $2,140 | tax year 2025 | "Taxes and certain other debts you owe the government"; split blank; past due $2,140      |
| E/F 4.1 | Bright Signal Wireless, PO Box 77031, Dallas, TX 75377                                               | final phone bill + early termination | $640   | 07/20/2025    |                                                                                           |
| E/F 4.2 | Calumet Ridge Medical Center, 2500 Ridge Crest Pkwy, Aurora, IL 60504                                | daughter's ER visit (in collections) | $3,850 | 02/08/2025    | someone else contacts you: Ashgrove (below)                                               |
| E/F 4.3 | Driveline Tire & Auto, 1650 N Farnsworth Ave, Aurora, IL 60505                                       | store card: tires and brakes         | $1,180 | 10/03/2025    |                                                                                           |
| E/F 4.4 | Illinois State Toll Highway Authority, 2700 Ogden Ave, Downers Grove, IL 60515                       | unpaid tolls and violation fines     | $380   | 01/14/2026    | "Is this one of these?": Not sure                                                         |
| E/F 4.5 | Meridian Lending Co., PO Box 31544, Wilmington, DE 19850                                             | online installment loan (rent)       | $4,100 | 09/05/2025    |                                                                                           |
| E/F 4.6 | Northgate Card Services, PO Box 60917, Phoenix, AZ 85082                                             | credit card                          | $6,420 | 05/10/2019    |                                                                                           |
| E/F 4.7 | Prairie Line Credit Union, 310 E Galena Blvd, Aurora, IL 60505                                       | credit card                          | $1,760 | 03/02/2020    | offset: Yes                                                                               |
| E/F 4.8 | Ridgeway Apartments LLC, 88 Ridgeway Ct, Naperville, IL 60540                                        | old landlord's move-out damage claim | $1,850 | 12/31/2024    | disputed: Yes                                                                             |
| E/F 4.9 | Sablewood Bank, PO Box 15022, Columbus, OH 43218                                                     | credit card                          | $2,980 | 10/18/2021    |                                                                                           |

**Someone else contacting you (E/F Part 3, 5.1):** Ashgrove Recovery Group, 900 Commerce Dr Ste 210, Oak Brook, IL 60523, on line 4.2, last 4 digits 4417.

**Contracts and leases (Schedule G):** 2.1 Northlight Auto Leasing, PO Box 92650, Itasca, IL 60143: lease of the 2024 Toyota Corolla Hybrid, 36 months, 03/01/2025 to 02/29/2028, $389 a month, kind "vehicle"; owe money on it now? No. 2.2 Fox Run Property Management, 2200 W Indian Trail, Aurora, IL 60506: apartment lease, 06/01/2026 to 05/31/2027, not a vehicle; owe money on it now? No.

**Codebtor (Schedule H 3.1):** Mateo Kettleby, 377 Douglas Ave, Elgin, IL 60120, your brother, on Schedule D line 2.1. Lived in a community property state in the last 8 years? No.

**Exemptions (Schedule C), your own picks:** line 1 § 522(b)(3) (state and federal nonbankruptcy); the Fit under 735 ILCS 5/12-1001(c), "100% of fair market value, up to any applicable statutory limit"; lines 6, 7, 11 under 12-1001(a); lines 16, 17.1, 17.2, 38 under 12-1001(b); line 40 under 12-1001(d); nothing on the Corolla. Line 3 (homestead over $214,000): No.

**Why these are your answers:**

- **Installments:** $338 at once is more than your best week leaves over; weekly payouts fit four payments. **§ 522(b)(3):** you have lived in Illinois all your life, so the 730-day note points to Illinois law.
- **The lease stays on J 17a, not in your $830:** "It's my only car; I'd have it even if I didn't drive for the apps. What driving costs me is gas, the insurance add-on, tolls, washes and the phone." Your app mileage log shows about 90% app miles, so gas is $560 business and $60 school runs; the $35 add-on is business and the $165 policy is J 15c.
- **Copperline $0 a month:** the box asks "your regular monthly payment", and Mateo pays it, not you.
- **IRS split blank:** the notice lists tax, penalty and interest, never "priority". **Tollway Not sure:** "It's the state and the notices say 'fine'; I don't know if that's 'debts you owe the government'."
- **Ridgeway disputed:** you have the move-out photos. **Prairie Line offset:** your card agreement lets the credit union take your savings.
- **A/B 3.1 at $0/$0:** the form asks about vehicles you "own, lease, or have legal or equitable interest in"; you lease it and Northlight owns all of it. **Line 38:** "commissions you already earned": you earned the payouts driving.

### What to Watch For

- Can you report your driving as earnings and costs, without the app calling it wages or telling you what counts as a cost?
- Is your co-signed loan explained, including that Mateo stays responsible for it, without the app telling you what to do?
- Does anything say what will happen to your lease, or push you on it?
- Can you enter nine creditors and their addresses on your phone without losing work?
- Is the difference between the hospital and the collection agency clear?
- Does the fee question show installments plainly, and say where to get Form 103A?
- Does "Not sure" on the toll debt feel safe to pick?

---

### 2. Per PR

Each PR adds only what its feature asks for; row names point to the brief above.

**3a1 (data foundations).** Seed `_andres_kettleby` (`demo_andres`), fixture `ANDRES` (`e2e_andres_${RUN_ID}`, SSN 900-66-6006) and journey `andres-gig-driver.spec.ts`, on existing fields only:

- `DebtorInfo`: the identity rows, `household_size` 2, `filing_type` individual.
- `IncomeInfo`: `marital_status` "single", `number_of_dependents` 1; all ten sources $0 except `monthly_other_income` $3,370, the interim home for his **net**, so CMI, line 11 and the median result are final from day one.
- `ExpenseInfo`: rent 1,150, utilities 210, home_maintenance 0, **vehicle_payment 389** (the lease, until 3c), vehicle_insurance 165, vehicle_maintenance 60, food 520, clothing 60, medical 45, childcare 180, child_support_paid 0, insurance_not_deducted 0, other 0 (total $2,779).
- `AssetInfo`: vehicle "2017 Honda Fit" 4,300 (the portion; `amount_owed` 7,800, read by no form); personal_property "Household goods, electronics and clothing" 1,900; bank_account Harborline checking 412; bank_account Prairie Line share savings 85.
- `DebtInfo`: D 2.1 `auto_loan`, `is_secured`, `collateral_description` "2017 Honda Fit, co-owned with my brother"; E/F 4.1–4.9 as utility, medical (`is_in_collections`), credit_card, other, personal_loan, credit_card ×2, other, credit_card; every payment 0; `consumer_business_classification` "consumer" except 4.3 "business" (his answer; nothing reads it, step 4 asks Q7).
- Not yet: the IRS row (3d), contracts and the codebtor (3c, §4.3), Schedule C. Fee waiver in the interim: §4.1.

**3a2 (drawing engine).** None. The é in "Andrés" checks SPIKE 2's WinAnsi/Latin-1 path on every header.

**3e1 (household and spouse).** County Kane, so 101 `Debtor1.County` prints "Kane" (DIG-277). Household list: one person, daughter, age 9, lives with him, claimed on his return (J line 2 one row; 122A-1 line 13 = 2; 103B line 1 = 2 while 103B is still in his packet). Marital status "Not married"; no spouse figures. `number_of_dependents` retired; `household_size` 2 left unread.

**3e2 (income detail and expenses).**

- Business gross receipts $4,200 and operating expenses $830, so net $3,370 (5c = 5a − 5b); `monthly_other_income` $3,370 → $0. Interest $0; rental gross $0 and costs $0; 5a–5h blank; 8f No; "income now different?" No.
- Schedule I 8a statement (sheet generator): "Rideshare and delivery driving", gross receipts $4,200, ordinary and necessary business expenses $830, net $3,370.
- Schedule J new lines: 4b $15, 10 $40, 13 $30, 14 $20, 16 $150 (specify "2026 estimated income tax"); 4a, 4d, 5, 19, 20a–20e and Other 21 $0. Total $2,779 → $3,034.

**3f (fee waiver).** Form 101 line 8: installments (`Check Box7`, encrypted). The seed's interim application goes (§4.1) and `andres` leaves `WAIVER_FILERS`. The journey skips `/fee-waiver` and asserts the "get Form 103A from the court" message. Information shown: $2,705 for a family of 2, beside his figure, $3,370 − $0 = $3,370.

**3b (A/B).** The brief's ten A/B rows: the Fit gains both values (8,600 entire, 4,300 portion) and "you and someone else"; new rows 3.1 Corolla $0/$0 (§4.6), line 16 $60, line 38 $310, line 40 $150; the personal_property row splits into lines 6, 7 and 11.

**3c (claims, link, creditor list).**

- Addresses on every D, E/F, G and H row. D 2.1 linked to A/B 3.2; lien "An agreement you made (such as mortgage or secured car loan)"; "take back" Yes; Columns B and C blank with the legal-aid note (Q14).
- Notice 5.1 Ashgrove → line 4.2, last 4 digits 4417. Status: dates as in the brief; 4.8 disputed; 4.7 offset; nothing contingent or unliquidated.
- Codebtor Mateo linked to D 2.1, which ticks "At least one of the debtors and another".
- G 2.1 kind "vehicle", $389 a month, personal-property-lease flag Yes, "owe now?" No, so `vehicle_payment` 389 → 0. G 2.2 not a vehicle, "owe now?" No. `AssetInfo.amount_owed` on the Fit retired.
- List of Creditors: 14 entities (D 2.1, E/F 4.1–4.9, Ashgrove, Northlight, Fox Run, Mateo).

**3d (priority).** "Is this one of these?": No for 4.1–4.9, except 4.4 **Not sure**, which stays in Part 2 with the legal-aid note. New row E/F 2.1, the IRS: `debt_type` other, $2,140, address as in the brief, `consumer_business_classification` "business" (his answer), type "Taxes…", split blank, past due $2,140 (stored; he has no 122A-2). List of Creditors: 15 entities.

**3g (Schedule C).** The brief's exemption picks, one row for each item and law.

**3h (122A-2).** None. He is below the median; the journey asserts no details step and no 122A-2.

### 3. Outcome changes (each VERIFY: worked out by hand later)

1. **Median (3a1).** 122A-1 13C: $91,526 (fixture) → $93,934. 12b = $3,370 × 12 = $40,440, below both, so he is below median in every PR and 122A-2 never applies. 14a `/12b less or equal to 13`; page-1 `CheckBox1` no presumption. VERIFY: worked out by hand later.
2. **Fee routing, 3a1–3e2.** Today's flag: 0.6 × $93,934 = $56,360.40 > $40,440, so he "qualifies" and is sent to `/fee-waiver`; 103B makes **15** forms. From 3f, installments takes 103B out: **14**. VERIFY: worked out by hand later.
3. **Packet at the end of step 3.** 14 forms (101, 106Dec, 106Sum, 107, 121, 122A-1, A/B, C, D, E/F, G, H, I, J), or 15 if Generate All counts the List of Creditors. Step 4 adds 108 (D 2.1 plus the G 2.1 personal-property lease) and 103A: 16 or 17. VERIFY: worked out by hand later.
4. **Schedule J.** 22a/22c/23b $2,779 → $3,034 in 3e2 (+15 +40 +30 +20 +150); 23a $3,370; 23c $591 → $336; 17a $389 throughout (its source moves in 3c); 17b blank (D 2.1 payment $0). VERIFY: worked out by hand later.
5. **106Sum.** 1b/1c $6,697 (4,300 + 1,900 + 412 + 85) → $7,217 in 3b (+60 +310 +150 +0); 2 $7,800; 3a blank → $2,140 in 3d; 3b $23,160; 3c $30,960 → $33,100 in 3d; 4 $3,370; 5 $2,779 → $3,034. VERIFY: worked out by hand later.
6. **122A-1.** 3a1–3e1: line 10 $3,370 as other income. From 3e2: 5a $4,200, 5b $830, 5c and line 5 $3,370; line 10 and lines 2–4, 6–9 $0.00 (Q27); 11 $3,370; 13B 2. VERIFY: worked out by hand later.
7. **Schedule I.** 3a1–3e1: 8h $3,370. From 3e2: 8a $3,370 with the statement appended; lines 2–7 and 8b–8h $0.00 (Q27); 10 and 12 $3,370. VERIFY: worked out by hand later.
8. **Schedule D (3c).** Column A $7,800; B and C blank. If C-1 rules "portion": B $4,300, C $3,500; if "entire": B $8,600, C $0. VERIFY: worked out by hand later.
9. **E/F.** Part 2 fills p3 (4.1–4.3), p4 (4.4–4.6) and one copy of p4 (4.7–4.9: Prairie Line, Ridgeway, Sablewood). 6i and 6j $23,160 (640 + 3,850 + 1,180 + 380 + 4,100 + 6,420 + 1,760 + 1,850 + 2,980). From 3d: 6b and 6e $2,140. VERIFY: worked out by hand later.
10. **A/B (3b).** Line 5 $4,300; 15 $1,900; 36 $557; 45 $460; 55 $0; 62 and 63 $7,217. VERIFY: worked out by hand later.
11. **Schedule C (3g) per-law totals.** (a) $1,900; (b) $867; (c) the Fit's $4,300 portion; (d) $150, beside the scope's 2026 limits ((b) $4,000, (c) $3,600, (d) $2,250; `scope/assets-exemptions.md:182`, unverified). VERIFY: worked out by hand later.
12. **Form 101 ranges.** Creditors 1–49 (11 debts plus 4 other entities); assets and liabilities both $0–$50,000. VERIFY: worked out by hand later.

### 4. Conflicts and owner questions

1. **The interim fee routing contradicts his line 8 answer (3a1–3e2).** `seed_demo_data.py:605-615` creates an application for any filer who qualifies, reads `data["fee_waiver"]` (KeyError without it) and hard-codes `cannot_pay_installments=True`. `FeeWaiverPage.tsx` gives an eligible filer only "Submit waiver application"; `e2e/pages/fee-waiver.page.ts:22-23` ticks both "cannot pay" boxes; `test_api_readback.py:38,130` needs him in `WAIVER_FILERS`. Options for the 3a1 spec: **(a)** an interim application (take-home $3,370, non-cash No), deleted in 3f, though until then the fixture swears he can't pay in installments; **(b)** the seed skips the application for a persona with no `fee_waiver` data and the journey stops at Complete until 3f (he still needs `WAIVER_FILERS` for the qualifies assert).
2. **The E2E income fill uses the wages line.** `wizard.page.ts:117-124` types the total into `monthly_gross_wages`, but the seed's interim net is in `monthly_other_income`. Until 3e2 the journey prints on Schedule I line 2 and 122A-1 line 2, the seed on 8h and line 10; CMI is the same. Either the page object fills by source in 3a1, or the mismatch is accepted until 3e2. Driving income should not be typed as wages.
3. **`test_api_readback.py` takes him in automatically** (`:162` parametrizes over `PERSONAS`). `:85` needs all ten sources non-None, so the seed types $0. `:102-106` sends empty contracts and codebtors, so 3c must send his G and H rows; that is why 3a1 seeds neither.
4. **Gap: one cost counted twice (Q5 × Q13).** No ruling stops a filer putting the lease on 5b/8a and on J 17a (or 122A-2 line 13), gas on 5b and J 12, or insurance on 5b and J 15c. The brief splits them as his answer; the 3e2 and 3c specs may want an information note.
5. **The co-signed payment (Q13).** He types $0 at "Your regular monthly payment (if any)" (`DebtsStep.tsx:285`), since Mateo pays. Q13 makes the debt's payment the only source, so J 17b is blank, which is right for his budget. Step 4's Form 108, and 122A-2 lines 13 and 33 had he been above median, would also read $0, not the contract's $245.
6. **The leased car on A/B line 3.** The template says "If you lease a vehicle, also report it on Schedule G" (A/B Part 2 header), and G says to list leases "even if … listed on Schedule A/B". Q24 and Q13 don't say whether 3b keeps a lease row on line 3, or at what values. The brief lists it at $0/$0 as his answer; the 3b spec decides. VERIFY.
7. **Form 101 lines 12 and 16 have no step 3 home.** Line 12 ("Are you a sole proprietor…?") is placed in no PR and no step; spec §3.2 lists only Q7 and the paid preparer. It reads `answer:form_101.business_name`, which nothing writes. His answer, for whichever step takes it: Yes, no business name, at his home address. Line 16a (Q7) is step 4 (step 2 spec Q7). His answer: Yes, primarily consumer debts, with $3,320 of $33,100 business by his own count (4.3 and the IRS), so the off-ramp, which only a "No" triggers, keeps him in.
8. **Form 107 (step 4).** Line 4 (business income) and line 27 (business) will need his driving. Out of step 3, but worth knowing now.
9. **SSN split.** The briefs say "enter this exactly" with the seed's SSN (`maria-torres.md:43` = `seed_demo_data.py:58`, 900-11-0001), while E2E types another (`personas.ts:87`, 900-11-1001). He follows both conventions.
10. **Phone numbers outside the fiction block.** 312-555-0202/0303/0404/0505 (briefs; `seed_demo_data.py:181,262,336,444`; `personas.ts`) fall outside 555-0100–0199. Only Maria's 0101 is inside. His is 630-555-0161.
11. **Real or fictional creditor names.** The five use real firms and no addresses. He needs addresses (S3-ADDR), so his private creditors are fictional. The IRS and Tollway addresses are their public ones, given from memory: VERIFY against irs.gov and illinoistollway.com before committing. **Resolved 2026-10-16:** both were verified on the official sites, and the owner chose fictional names for the five personas' private creditors as well.
12. **Docs that still say five.** `docs/testing/persona-briefs/README.md:5,16-22,46,97` (five personas, 7 journeys, the 5/5 target) and `seed_demo_data.py:1,513,525` ("5 personas").
13. **Exemption amounts.** The fixture has vehicle $2,400 and tools $1,500 (`ilnd_2025_data.json:52-76`); the scope's 2026 figures are $3,600 and $2,250. Q23 verifies them before loading. His C totals sit beside whichever loads.
14. **No conflict with existing data.** Nothing exists for him yet in the brief, seed, fixture or tier 3. Tier 3's docstring excuses only Priya (`test_oracle_tier3.py:4-5`), so his rows must match this brief exactly from 3a1.
15. **No contradiction with `decisions.md`.** Q5's gig worker stays in, and Q14's blank Column B and Q21's installments path are exercised as ruled.
