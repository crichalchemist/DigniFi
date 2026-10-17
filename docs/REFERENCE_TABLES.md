# Reference Tables

- **Operator:** the project owner
- **Last updated:** October 16, 2026

DigniFi reads public tables that change on a schedule. Each row of such a table is stored with the first day it applies (`effective_date`), the last day before its next scheduled change (`valid_through`) and the page it comes from (`source_url`). DigniFi uses the newest row that has started by the day the forms are filled, in Chicago time, which stands in for the filing date. If that row's `valid_through` has passed, or no row has started yet, DigniFi refuses to prepare forms. It never falls back to an older row.

The code lives in `backend/apps/districts/dated_tables.py`. Each table below has its own section. A pull request that loads a new kind of table adds its section here.

---

## Census median income

DigniFi compares each filer's income with this table on Form 122A-1 (line 13), and it uses the table to decide whether Form 122A-2 is in the packet and whether the filer is offered the fee-waiver application.

### Where it is posted

- The U.S. Trustee Program's means-testing page lists every period: https://www.justice.gov/ust/means-testing
- Each table has its own page, named by the first day it applies: `https://www.justice.gov/ust/eo/bapcpa/<YYYYMMDD>/bci_data/median_income_table.htm`
- DigniFi reads the Illinois row, for the Northern District of Illinois.

### When it changes

- New Census figures apply to cases filed on or after **April 1** and **November 1** each year.
- The U.S. Trustee usually posts them a few weeks ahead. The November 2025 table was posted on October 16, 2025, and the April 2026 table on March 18, 2026.
- Some periods on that page change only the IRS figures. The July 15, 2026 period is one: its Illinois median row matches the April 2026 table, so it needs no new row.

### The rows DigniFi loads

| Effective  | `valid_through` | Illinois, 1–4 people                    | Each person over 4 |
| ---------- | --------------- | --------------------------------------- | ------------------ |
| 2025-11-01 | 2026-03-31      | $71,304 / $91,526 / $110,712 / $134,366 | $11,100            |
| 2026-04-01 | 2026-10-31      | $73,180 / $93,934 / $113,625 / $137,902 | $11,100            |

### How to add a row

1. Open the new table's page and copy the Illinois figures for 1 to 4 people. For 5 to 8 people, add the posted amount for each person over 4 ("Add $11,100 for each individual in excess of 4") to the 4-person figure, once per person. Store that amount as `family_size_additional` too.
2. Add a `districts.medianincome` row to `backend/apps/districts/fixtures/ilnd_2025_data.json` with the next `pk`, a `created_at`, and:
   - `effective_date`: the first day the table applies;
   - `valid_through`: the day before the next scheduled change, which is March 31 for a November table and October 31 for an April table;
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
