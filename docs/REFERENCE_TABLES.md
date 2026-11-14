# Reference Tables

- **Operator:** the project owner
- **Last updated:** November 14, 2026

DigniFi reads public tables that change on a schedule. Each row of such a table is stored with the first day it applies (`effective_date`), the last day before its next scheduled change (`valid_through`) and the page it comes from (`source_url`). DigniFi uses the newest row that has started by the day the forms are filled, in Chicago time, which stands in for the filing date. If that row's `valid_through` has passed, or no row has started yet, DigniFi refuses to prepare forms. It never falls back to an older row.

The code lives in `backend/apps/districts/dated_tables.py`. Each table below has its own section. A pull request that loads a new kind of table adds its section here.

---

## Census median income

DigniFi compares each filer's income with this table on Form 122A-1 (line 13), and it uses the table to decide whether Form 122A-2 is in the packet.

### Where it is posted

- The U.S. Trustee Program's means-testing page lists every period: https://www.justice.gov/ust/means-testing
- Each table has its own page, named by the first day it applies: `https://www.justice.gov/ust/eo/bapcpa/<YYYYMMDD>/bci_data/median_income_table.htm`
- DigniFi reads the Illinois row, for the Northern District of Illinois.

### When it changes

- New Census figures apply to cases filed on or after **April 1** and **November 1** each year.
- The U.S. Trustee usually posts them a few weeks ahead. The November 2025 table was posted on October 16, 2025, and the April 2026 table on March 18, 2026.
- Some periods on that page change only the IRS figures. The July 15, 2026 period is one: its Illinois median row matches the April 2026 table, so it needs no new row.
- The November 2026 update had not been posted on November 1, 2026: the period list still began with "7/15/2026 or After". As with the skipped November 2021 update, the April 2026 row is taken to run to March 31, 2027 (the period is open-ended; move it when the next table is posted). An existing database keeps the old date until you run `python manage.py loaddata ilnd_2025_data` again. If a table effective before then is posted, add its row; DigniFi uses the newest row that has started, so the new row takes over from its `effective_date`.
- The U.S. Trustee's period list, not the calendar, sets a row's dates (`effective_date` and `valid_through`). Updates sometimes slip: the list has a period of 5/15/2021 to 3/31/2022, so one November update was skipped, and a period that starts on 11/15/2013.
- When a scheduled update is skipped or late, extend the current row's `valid_through` to the real end of its period, so filers aren't refused while the old figures still apply. Then add the next row with its own `effective_date`, as below.

### The rows DigniFi loads

| Effective  | `valid_through` | Illinois, 1–4 people                    | Each person over 4 |
| ---------- | --------------- | --------------------------------------- | ------------------ |
| 2025-11-01 | 2026-03-31      | $71,304 / $91,526 / $110,712 / $134,366 | $11,100            |
| 2026-04-01 | 2027-03-31      | $73,180 / $93,934 / $113,625 / $137,902 | $11,100            |

### How to add a row

1. Open the new table's page and copy the Illinois figures for 1 to 4 people. For 5 to 8 people, add the posted amount for each person over 4 ("Add $11,100 for each individual in excess of 4") to the 4-person figure, once per person. Store that amount as `family_size_additional` too.
2. Add a `districts.medianincome` row to `backend/apps/districts/fixtures/ilnd_2025_data.json` with the next `pk`, a `created_at`, and:
   - `effective_date`: the first day the table applies;
   - `valid_through`: the day before the next scheduled change, which is March 31 for a November table and October 31 for an April table (unless an update was skipped; see above);
   - `source_url`: the table's own page.
3. Leave the earlier rows as they are. A test fails if any median row in the fixture has no `valid_through`.
4. Open a pull request to `develop`. Backend tests fill forms on a fixed day, 2026-10-16 (`backend/conftest.py`), so a new row changes no test unless that day moves.
5. After the deploy, load the fixture on production with `python manage.py loaddata ilnd_2025_data` (for example through `heroku run`). Load it on any local database the same way.

### What a missed change looks like

From the day after the last row's `valid_through` until the new row is loaded:

- **Filers** see this sentence: "DigniFi doesn't have the income figures for today's date yet, so it can't prepare your forms. Please try again later." The forms views return it as a 422: Generate All, Generate, Regenerate, the download of an unfiled form, and the packet list of a completed intake. The eligibility check after Complete returns it as a 400, so the filer stays on the Review step.
- **Logs and Sentry** get one error line per refusal, naming only the table, the date and the district: `No Census median income table in force on 2026-11-01 for district ilnd`.
- **`seed_demo_data`** prints a message pointing to this page and changes nothing, even with `--reset`. The E2E journeys fail, in CI too, since they run on the real date.

The fix is to load the new table, as above. If the U.S. Trustee hasn't posted it yet, the refusal is working as designed.

---

## HHS poverty guidelines

A judge may waive the Chapter 7 filing fee only for a family whose income is less than 150% of the poverty guideline for its size (28 U.S.C. § 1930(f)(1)). DigniFi shows that limit, a month, on the "How you will pay the filing fee" page, beside Form 101 line 8, as information. It never compares the filer's income with it. The table is national: DigniFi stores the figures for the 48 contiguous states and the District of Columbia, which cover the Northern District of Illinois.

### Where it is posted

- HHS (ASPE) lists every year's guidelines: https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
- Each year's figures are published as a notice in the Federal Register. DigniFi stores that notice's page as the row's `source_url`.
- The courts post the monthly 150% figures as "150% of the HHS Poverty Guidelines" on uscourts.gov. Check DigniFi's limits against that table.

### When it changes

- HHS publishes new guidelines each January. The day isn't fixed: the 2026 notice was published on January 15, 2026, and gave its own effective date as January 13.
- A row takes effect on the day its notice is **published** in the Federal Register. The AO's instructions for Form 103B compare a family's income with the guideline "last published". The ILNB instruction packet prints its table as "Updated: 1/01/2026". The question of which date counts is open with the clerk, and an answer would change only a row's `effective_date` and this page.
- A row's `valid_through` is January 31 of the next year, which gives HHS the month to publish.
- If the next notice is late, extend the current row's `valid_through` with a new data migration, so that its figures stay shown while they are still the last published. Then add the next row as below.

### The rows DigniFi loads

| Effective  | `valid_through` | First person | Each additional person | Court's limit a month, 1–4 people             | Each person after |
| ---------- | --------------- | ------------ | ---------------------- | --------------------------------------------- | ----------------- |
| 2026-01-15 | 2027-01-31      | $15,960      | $5,680                 | $1,995.00 / $2,705.00 / $3,415.00 / $4,125.00 | $710.00           |

### How to add a row

1. Open the new Federal Register notice. Copy the figure for one person and the amount for each additional person from its table for the 48 contiguous states and DC.
2. Run `python manage.py makemigrations districts --empty -n poverty_guideline_<year>`. Write it as `0005_poverty_guideline_2026.py` is written:

   - a `RunPython` that creates one `PovertyGuideline` row, with the figures written into the migration;
   - its reverse, which deletes that row by its `effective_date`.

   The row's fields are:

   - `effective_date`: the notice's publication date;
   - `valid_through`: January 31 of the next year;
   - `source_url`: the notice's page.

3. Leave the earlier rows as they are. A test fails if any stored guideline has no `valid_through`.
4. In `backend/apps/districts/tests/test_poverty.py`, add a test that pins the new row's monthly limits to the courts' 150% table for that year. Then open a pull request to `develop`.
5. Nothing to run after the deploy: the Heroku release runs `migrate`, which loads the row. A local database gets it with `python manage.py migrate`.

### What a missed change looks like

From the day after the last row's `valid_through` until the new row's migration is applied:

- **Filers** see, on the "How you will pay the filing fee" page, a sentence saying DigniFi doesn't have the current poverty figures. They see no limit, never an old one. Their answer still saves, and no form is refused.
- **Logs and Sentry** get one error line per lookup, naming only the table and the date: `No HHS poverty guidelines table in force on 2027-02-01 for district -`.
- **The E2E journeys** fail where they check the limit, in CI too, since they run on the real date. The 2026 row ends on January 31, 2027, two months before the median table's March 31, 2027.

The fix is to add the new row, as above. If HHS hasn't published the new guidelines yet, extend `valid_through` instead.

---

## Illinois and federal exemption laws

The exemptions page (`/exemptions`, after the filing-fee page) lists the Illinois and federal laws a filer may cite for the property they claim as exempt on Schedule C, each with its citation and the law's own limit sentence. DigniFi never chooses a law or an amount for the filer. The list is Illinois and federal law that applies across the whole state, so it has no district. It holds 25 laws.

### Where it is posted

- The Illinois statutes and Public Acts: https://www.ilga.gov/ (735 ILCS 5/12-901 and 5/12-1001 are the main ones). DigniFi stores the Public Act that last changed the list as the row's `source_url`.
- The U.S. Code, as Cornell's Legal Information Institute posts it: https://www.law.cornell.edu/uscode/text/

### When it changes

- Only by a Public Act of Illinois or an Act of Congress. There is no schedule, so the row's `valid_through` stays empty: DigniFi never stops showing the list on a date.
- The owner, the named operator, watches for such Acts. Nothing in DigniFi watches for them.

### The rows DigniFi loads

| Effective  | `valid_through` | Laws | Source       |
| ---------- | --------------- | ---- | ------------ |
| 2026-01-01 | empty           | 25   | P.A. 104-120 |

### How to add a version

1. Run `python manage.py makemigrations districts --empty -n exemption_catalog_<year>`. Write it as `0007_exemption_catalog_2026.py` is written: a `RunPython` that creates one `ExemptionCatalog` row and its `ExemptionLaw` rows, with the values written into the migration, and a reverse that deletes that row by its `effective_date`.
2. Rewrite each law's limit sentence in plain words, with its units. Mark the sentences `# DRAFT: counsel C-8`. `backend/apps/districts/tests/test_exemption_catalog.py` scores each one of five words or more with `flesch_kincaid_grade` (grade 9 or below) and checks every one for advice words and for "you". The cases in `frontend/src/test/readingLevelCases.json` only keep that formula the same as the frontend's.
3. Leave the earlier versions as they are.
4. Update `EXPECTED` in `backend/apps/districts/tests/test_exemption_catalog.py`, and keep the law summaries in `frontend/src/constants/copy.ts` in step with the list.
5. Open a pull request to `develop`. Nothing to run after the deploy: the Heroku release runs `migrate`.

### What a missed change looks like

- The old figures stay shown. Nothing refuses, which is why the owner watches for Acts.
- Before the first version is loaded, the exemptions page shows `EXEMPTIONS_NO_TABLE`: "DigniFi doesn't have the exemption laws for today's date yet, so it can't prepare Schedule C." Schedule C is refused in the same words (`NO_EXEMPTION_CATALOG`), but only for a filer whose claims name a law from the list: a filer who claims nothing, or only types their own law, is not refused.

---

## U.S. Trustee means test standards

Form 122A-2 uses the IRS national and local expense standards, the out-of-pocket health care amounts, the transportation figures and the district's multiplier that the U.S. Trustee Program posts. DigniFi stores one set for the Northern District of Illinois: the national standards for 1 to 4 people and the extra for each person after 4, the five percent figures for line 30, health care per person under 65 and 65 or older, housing and utilities for each of the 18 ILND counties for 1 to 5 or more people (insurance and operating, and mortgage or rent), the Chicago and Midwest Region transportation figures, and which of the two each county uses, and the multiplier (6.9 percent). Each set is a `MeansStandards` row with its `MeansFigure` and `MeansArea` rows.

### Where it is posted

- The U.S. Trustee Program's means-testing page: https://www.justice.gov/ust/means-testing
- Each period has one page, `https://www.justice.gov/ust/means-testing/<YYYYMMDD>`, named by the first day it applies. It bundles every IRS table and the multipliers. DigniFi stores that page as the row's `source_url`.
- The Trustee spells LaSalle "La Salle" and this district "ILN". DigniFi's rows use "LaSalle" and the code "ilnd".

### When it changes

- There is no fixed change date. The Trustee posts a new period when the IRS changes its standards, and some periods change only these figures. This page is the only guard: the owner, the named operator, watches the means-testing page. Nothing in DigniFi watches it.
- The row's `valid_through` stays empty, so DigniFi never stops using a set on a date.

### The rows DigniFi loads

| Effective  | `valid_through` | Figures | Areas | Source                                             |
| ---------- | --------------- | ------- | ----- | -------------------------------------------------- |
| 2026-07-15 | empty           | 200     | 18    | https://www.justice.gov/ust/means-testing/20260715 |

### How to add a version

1. Run `python manage.py makemigrations districts --empty -n means_standards_<yyyymmdd>`. Write it as `0010_means_standards_2026.py` is written: a `RunPython` that creates one `MeansStandards` row and its `MeansFigure` and `MeansArea` rows, with the values written into the migration, and a reverse that deletes that row by its `effective_date`.
2. Copy every figure from the new period's page. Check the Chicago county list against the IRS conversion chart.
3. Leave the earlier rows as they are.
4. Update `EXPECTED_FIGURES` and `EXPECTED_AREAS` in `backend/apps/districts/tests/test_means_standards.py`, and the `means_standards_2026` fixture in `backend/conftest.py` if the new set should be the one tests load.
5. Open a pull request to `develop`. Nothing to run after the deploy: the Heroku release runs `migrate`.

### What a missed change looks like

- Nothing shows. The old figures stay in use, since the row never lapses, which is why the owner watches the page.
- Before the first row's date, the refusal line is `No IRS expense standards table in force on 2026-07-14 for district -`, and above-median filers see the missing-table sentence in place of Form 122A-2.

---

## Bankruptcy Code dollar amounts

Form 122A-2 and the means test use three amounts that 11 U.S.C. § 104 adjusts every three years: the two presumption thresholds ($10,275 and $17,150 over five years), the Chapter 13 debt limits and the education amount per child. DigniFi stores them as one `Section104Amounts` row.

### Where it is posted

- The Judicial Conference's notice in the Federal Register: 90 FR 8941, https://www.federalregister.gov/documents/2025/02/04/2025-02207/adjustment-of-certain-dollar-amounts-applicable-to-bankruptcy-cases. DigniFi stores that page as the row's `source_url`.

### When it changes

- On **April 1, 2028**, and every three years after. The 122A-2 template prints the old figures itself, so the form and the row change together.
- The row's `valid_through` is the day before: 2028-03-31.

### The rows DigniFi loads

| Effective  | `valid_through` | Presumption thresholds | Chapter 13 limits (unsecured / secured) | Education per child a month |
| ---------- | --------------- | ---------------------- | --------------------------------------- | --------------------------- |
| 2025-04-01 | 2028-03-31      | $10,275 / $17,150      | $526,700 / $1,580,125                   | $214.58                     |

### How to add a version

1. Run `python manage.py makemigrations districts --empty -n section_104_<year>`. Write it as `0011_section_104_2025.py` is written: a `RunPython` that creates one `Section104Amounts` row, and a reverse that deletes it by its `effective_date`.
2. Copy the figures from the new Federal Register notice, and the education amount from the new Form 122A-2.
3. Leave the earlier rows as they are.
4. Update the figures pinned in `backend/apps/districts/tests/test_means_standards.py`, then open a pull request to `develop`.

### What a missed change looks like

- From April 1, 2028 until the new row is loaded, the refusal line is `No Bankruptcy Code dollar amounts table in force on 2028-04-01 for district -`.
- Every above-median filer sees the missing-table sentence in place of Form 122A-2: "DigniFi doesn't have the means test figures for today's date yet, so it can't work out Form 122A-2."
