# Forms step 3b, Schedule A/B: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ask every Schedule A/B line in the form's words, one Part per screen, print every item on its own line (rows past a line's slots on an attached sheet), and refuse Complete and the forms until the walk is finished.

**Architecture:** A pure catalog, `apps/intake/asset_lines.py`, says each line's Part, shape, slots and kinds, and holds the gaps and totals. `AssetInfo` gains an encrypted line, encrypted JSON details and an entire value, and a new `AssetLineAnswers` stores each Yes/No. The fill engine gains an `assets.` namespace and two optional sheet settings; `schedule_a_b.json` is generated from the catalog by a committed tool. The wizard keeps one `assets` step whose Parts are pages it holds.

**Tech Stack:** Django 5.0 + DRF (Python 3.11), `encrypted-model-fields`, PostgreSQL 15 / sqlite for tests, pypdf 6.13.1 and PyMuPDF; React 19 + Vite 7 + TypeScript, vitest + Testing Library + MSW, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-05-forms-step3b-design.md` (cited `§`), approved by the owner on 2026-11-05. It draws from the umbrella `docs/superpowers/specs/2026-10-16-forms-step3-design.md` §5.8 and the persona targets `docs/superpowers/specs/2026-10-16-forms-step3-personas.md` (cited `PS:`). Where this plan and the spec disagree, the spec wins, except at the errata under "For the owner at plan review".

## Global Constraints

- **Encryption.** `ab_line`, `details`, `description`, `financial_institution`, `entire_value`, `current_value` and `AssetLineAnswers.answers` are encrypted. Nothing new goes in `FormAnswer`. A ciphertext test reads each raw column with SQL. Sorting and matching happen in Python.
- **Migrations.** Intake `0032_assetinfo_encrypt_add`, `0033_assetinfo_encrypt_copy`, `0034_assetinfo_encrypt_swap`, `0035_assetlineanswers`, following the add/copy/swap shape of `0020`–`0022` and the tests in `apps/intake/tests/test_data_migrations.py` (the `migrate` fixture and a Postgres twin). No other app gets a migration. `makemigrations --check` passes after every task.
- **Values.** Answers are `"yes"`, `"no"` or null. `who` is `only_you` or `with_someone`. Kinds are exactly those in Task 1's catalog. An unknown line, kind or value is a 400. A missing answer saves, and Complete names it.
- **Blank, not 0.00.** An unknown or missing value prints blank and adds zero. Lines 5, 15, 36, 54 and 55–63 always print. Lines 2, 45 and 52 are blank under the No of lines 1, 37 and 46.
- **No verdict.** No sentence suggests a value, predicts an outcome, or explains how to split a joint account `[UPL]`. No line is ever suggested for an old row.
- **Words.** The form's words and examples go in `frontend/src/constants/formText.ts`, copied from the blank template's printed text (never the index's `label`, which reads "No" on lines 12–14 and 26–28). DigniFi's sentences go in `copy.ts` and pass `src/test/reading-level.test.ts`, with `// DRAFT: counsel C-14` or `C-15` beside the two notes of §6.2.
- **Tests that guard filers.** Access-control, encryption, UPL-wording and log-leak tests keep their assertions. A task may change only their setup (for example a payload's `asset_type` becoming `ab_line`), and says so in its report.
- **The forms.** Every new or re-keyed placement has its row in `data/forms/field_index/audit/step2_verification.json` in the same commit. Every new rule bound to a text or choice box has its `RULE_FIXES` entry with `step="assets"`. `known_defects.json` stays `[]`. Each task states its change to `ASSERTED_CASES` (`test_oracle_tier2.py:37`, 488 at `a795a80`).
- **Tests** are named after outcomes and use only synthetic data (SSNs 900-xx-xxxx, phones 555-0100 to 555-0199).
- **Running tests.** An implementer runs only the test files its task names, plus `pytest -m "not slow"` before committing. The controller runs the full gates between tasks: backend with `--cov=apps --cov=config --cov-fail-under=90`, ruff 0.8.5, `manage.py check`, `makemigrations --check --dry-run`, Postgres tests when a task adds a migration or a lock entry; for frontend tasks `npx vitest run --maxWorkers=2`, `npx tsc -p tsconfig.app.json --noEmit`, `npx tsc -p tsconfig.node.json --noEmit`, `npm run lint`, `npm run format:check`. **Never `tsc -b`.** Full suites and journeys run only with the 1-minute load under 10 (journeys: 5-minute load under 8 too); the machine is shared with audio work.
- **Expected red.** From Task 2 until Task 9 the frontend writes no `ab_line`, so the journeys fail, and they aren't run. They run at Task 10.
- **Commits.** `/usr/bin/git`, one plain command per call, stage by explicit path, message via `-F` from a file in the job's tmp directory. **No `Co-Authored-By`, `Claude-Session` or other agent trailer.** Never stage `.serena/`, `DESIGN.md`, `assets/`, `.impeccable`, `.claude/` or `.superpowers/`. Pre-commit's prettier may rewrite a staged file: re-add and commit again.
- **Branch and outward actions.** Work on `feat/forms-step3b` in `.claude/worktrees/forms-step3f`. No push, PR, merge, deploy or production command from this plan. Env values are sourced, never printed.
- **CLAUDE.md gotchas** change in the task whose code changes the behaviour; each task's report lists the edit.

## Review Focus

Five inputs the spec implies and no test it names covers, most likely to bite a filer first. Each test lives in the owning task.

1. **A filer types $0** on a leased car, then reloads: it comes back as 0, counts as answered, and prints 0.00, never blank and never "unanswered" (Tasks 2, 6, 8). JavaScript's `!value` is the trap.
2. **A filer changes one Part after Complete**: a save carrying only `asset_lines` reopens the intake, and an unchanged visit doesn't (Tasks 2, 9).
3. **A filer presses "I don't know", then types a figure, then presses it again**: the figure clears, the flag sets, and the server agrees either way (Tasks 2, 8).
4. **A stored amount too wide**: `entire_value` of 10 billion is a 400 on the session PATCH, because a wider stored value makes every read of the session 500 (Task 2).
5. **A letter the form can't print** in a line's description (such as "□"): the 422 links to `assets`, on a slot and on a sheet (Task 7).

## For the owner at plan review

The plan proceeds on its own reading of each item. The owner's answer goes in the ledger before the task that depends on it.

- **Spec errata.**
  - §3.1 doesn't type `details`' values. `percent` is validated as a decimal and stored as a string, because the column is JSON (Task 2).
  - §5 treats line 24 as an ordinary named line. Its template shares names: row 1 and row 3's text are both `24.1 Interest in an education IRA` (tags `T5`, `T9`), and row 2's text and amount are both `24.2 Interest in an education IRA` (`T7`, `T8`). Those bindings use `tag` (Task 6).
- **Plan decisions the spec leaves open.**
  - The schema is generated by a committed tool rather than hand-edited: about 400 fields, and a reviewer can read the mapping (Task 6).
  - Rule names `total_real_property`, `total_vehicles`, `total_household_items`, `total_financial_assets`, `total_other_assets`, `total_personal_property` and `total_assets` stay, so 106Sum and Form 101 change no binding (Task 3).
  - Text boxes in `details` are bounded at 200 characters, a limit no box comes near; `check()` at Generate stays the last word (Task 2).
- **Proposed ticket, filed only with the owner's yes:** drop `asset_type` one release after this is live. Counsel items C-14 and C-15 are in the spec's §6.3 and need no ticket.

## Before you start

Every command block runs from `/Volumes/Containers/DigniFi/.claude/worktrees/forms-step3f`. `source .claude/forms-step3f.env` sets `$PY` and the test environment (the file also holds secrets; never print it). Backend tests: `cd backend && $PY -m pytest -p no:cacheprovider <args>`. Frontend tools come from the main checkout's `node_modules` through the worktree's symlink. Journeys: `zsh .claude/e2e.sh 2`.

---

### Task 1: The catalog and the records

**Files:**

- Create: `backend/apps/intake/asset_lines.py`, `backend/apps/intake/migrations/0032_assetinfo_encrypt_add.py`, `0033_assetinfo_encrypt_copy.py`, `0034_assetinfo_encrypt_swap.py`, `0035_assetlineanswers.py`, `backend/apps/intake/tests/test_asset_lines.py`
- Modify: `backend/apps/intake/models.py:634-701`, `backend/apps/intake/tests/test_data_migrations.py`

**Interfaces:**

- Produces, in `apps/intake/asset_lines.py` (no model imports):
  - `Line(key: str, part: int, shape: str, capacity: int = 1, kinds: tuple[tuple[str, int], ...] = (), gate: str | None = None)`, frozen.
  - `LINES: tuple[Line, ...]` in form order; `LINE_BY_KEY: dict[str, Line]`; `WHO = ("only_you", "with_someone")`; `PROPERTY_KINDS = ("single_family", "duplex", "condo", "manufactured", "land", "investment", "timeshare", "other")`.
  - `shown_lines(answers: dict[str, str]) -> list[Line]`: every line, less those whose `gate` isn't answered `"yes"`.
  - `ordered_assets(session) -> list`: `session.assets.all()` sorted in Python by catalog position, then id; an old row (no `ab_line`) sorts first.
  - `rows_on(rows: list, key: str, kind: str | None = None) -> list`.
- Produces, in `models.py`: `AssetInfo.ab_line` (`EncryptedCharField(max_length=10, null=True, blank=True)`), `details` (`EncryptedTextField(blank=True, default="{}")` holding JSON, with `get_details() -> dict` and `set_details(value: dict) -> None`), `entire_value` (`EncryptedDecimalField(12, 2, null=True, blank=True)`), `current_value` now `null=True, blank=True`, `description` an `EncryptedCharField(max_length=255, blank=True, default="")`, `financial_institution` an `EncryptedCharField(max_length=100, blank=True, default="")`, `asset_type` `null=True, blank=True`. `Meta.ordering` removed. `equity` stays until Task 2. `AssetLineAnswers(session=OneToOne(related_name="asset_lines"), answers=EncryptedTextField(default="{}"))`, table `asset_line_answers`, with `get_answers() -> dict` and `merge(sent: dict) -> None` (a null value removes the key).

The catalog is exact:

| key                   | part | shape              | capacity / kinds                                                                                              | gate |
| --------------------- | ---- | ------------------ | ------------------------------------------------------------------------------------------------------------- | ---- |
| 1                     | 1    | place              | 3                                                                                                             |      |
| 3                     | 2    | vehicle            | 4                                                                                                             |      |
| 4                     | 2    | vehicle_no_mileage | 2                                                                                                             |      |
| 6–14                  | 3    | item               | 1                                                                                                             |      |
| 16                    | 4    | cash               | 1                                                                                                             |      |
| 17                    | 4    | labelled           | checking 2, savings 2, cd 1, other 4                                                                          |      |
| 18, 20, 23, 24        | 4    | named              | 3                                                                                                             |      |
| 19                    | 4    | named_share        | 3                                                                                                             |      |
| 21                    | 4    | labelled           | 401k, pension, ira, retirement, keogh 1 each; additional 2                                                    |      |
| 22                    | 4    | labelled           | electric, gas, heating_oil, security_deposit, prepaid_rent, telephone, water, rented_furniture, other, 1 each |      |
| 25, 26, 27, 30, 32–35 | 4    | item               | 1                                                                                                             |      |
| 28                    | 4    | shared_box         | federal, state, local, 1 each                                                                                 |      |
| 29                    | 4    | shared_box         | alimony, maintenance, support, divorce_settlement, property_settlement, 1 each                                |      |
| 31                    | 4    | insurance          | 3                                                                                                             |      |
| 37                    | 5    | gate               | none                                                                                                          |      |
| 38–41                 | 5    | item               | 1                                                                                                             | 37   |
| 42                    | 5    | named_share        | 3                                                                                                             | 37   |
| 43                    | 5    | item_question      | 1                                                                                                             | 37   |
| 44                    | 5    | named              | 6                                                                                                             | 37   |
| 46                    | 6    | gate               | none                                                                                                          |      |
| 47–51                 | 6    | item               | 1                                                                                                             | 46   |
| 53                    | 7    | shared_box         | capacity 3, no kinds                                                                                          |      |

- [ ] **Step 1: Write the failing tests** in `test_asset_lines.py`:

```python
def test_a_filer_with_no_business_or_farm_answers_35_lines():
    assert len(shown_lines({})) == 35

def test_yes_to_both_gates_shows_47_lines():
    assert len(shown_lines({"37": "yes", "46": "yes"})) == 47

def test_part_four_has_twenty_lines():
    assert sum(1 for line in LINES if line.part == 4) == 20
```

Also, in the same file: `ordered_assets` returns catalog order for rows created out of order with values whose ciphertext order differs (`test_rows_order_by_line_then_id_not_by_ciphertext`); `merge` with a null removes the key; a raw-SQL ciphertext test for each encrypted column of both models. In `test_data_migrations.py`: a row with plaintext `description` and `financial_institution` reads back decrypted after `0034`, its `ab_line` is null and its `asset_type` kept; migrating back to `0031` restores the plaintext (with the Postgres twin).

- [ ] **Step 2: Run them to verify they fail.** Run: `$PY -m pytest apps/intake/tests/test_asset_lines.py apps/intake/tests/test_data_migrations.py -k "asset" -q`. Expected: import error for `asset_lines`.
- [ ] **Step 3: Implement** the catalog, model fields and the four migrations. `0033` copies with `RunPython`, batched as `0021` does.
- [ ] **Step 4: Run them to verify they pass**, plus `$PY -m pytest -m "not slow" -q`. Expected: all pass (`current_value` nullable and no `Meta.ordering` break no reader).
- [ ] **Step 5: Commit** `feat(intake): add the A/B line catalog and encrypt the asset columns`.

### Task 2: The API

**Files:**

- Modify: `backend/apps/intake/serializers.py:409-442,484-491,665,759-806`, `backend/apps/intake/views.py` (`AssetViewSet`), `backend/apps/intake/models.py` (remove `equity`)
- Test: `backend/apps/intake/tests/test_asset_lines_api.py` (new), `test_session_lock.py`, `test_session_nested_save.py`, `test_readable_amounts.py`, `test_asset_debt_authz.py`, `test_secured_debts_and_personal_property.py`

**Interfaces:**

- Consumes: Task 1's catalog and fields.
- Produces: `AssetDetailsSerializer` (every §3.1 key, optional and nullable; texts `max_length=200`; `who` in `WHO`; `property_kinds` a list of `PROPERTY_KINDS`; `percent` `DecimalField(5, 2, min_value=0, max_value=100)`; `community`, `has_personal_info`, `value_unknown`, `entire_unknown` booleans; `kind` a string). `AssetInfoSerializer` fields: `id, session, ab_line, details, description, current_value, entire_value, asset_type (read-only), data_source, amount_owed, created_at, updated_at`; `current_value` and `entire_value` are `DecimalField(12, 2, min_value=0, required=False, allow_null=True)`; `description` `allow_blank`, `required=False`. `validate()` refuses a `kind` not on `ab_line`'s line, and clears a flag when its figure is present. `equity`, `account_number` and `financial_institution` leave the API. Session serializer gains `asset_lines` read and write: `{line: "yes"|"no"|null}`, sets only the keys sent, and counts as an intake-data write (lock, then `reopen()`).
- CLAUDE.md: rewrite "Nested debts and assets save by id" for `asset_lines` and whole-step saves.

- [ ] **Step 1: Write the failing tests** in `test_asset_lines_api.py`:

```python
def test_zero_is_a_saved_value_and_comes_back_as_zero(filer_session):
    # PATCH assets [{ab_line: "3", current_value: "0.00", entire_value: "0.00"}]
    # GET returns "0.00" for both, not null.

def test_entire_value_wider_than_the_column_is_a_400(filer_session):
    # entire_value "10000000000.00" -> 400, and the session still reads 200.

def test_a_figure_clears_its_unknown_flag(filer_session):
    # PATCH details {value_unknown: true}, current_value "5.00" -> stored flag false, value 5.00.

def test_unknown_with_no_figure_keeps_the_flag_and_a_null_value(filer_session): ...

def test_a_kind_from_another_line_is_a_400(filer_session):
    # ab_line "17", details {kind: "401k"} -> 400.

def test_an_unknown_line_or_answer_is_a_400(filer_session): ...

def test_saving_only_line_answers_reopens_a_completed_intake(completed_session): ...

def test_a_missing_answer_saves(filer_session):
    # ab_line "6" with no description and no value -> 200, one row.

def test_per_item_create_without_a_line_is_a_400(filer_session):
    # POST /assets/ with no ab_line -> 400; no row exists.

def test_old_rows_survive_a_save_that_sends_them_back(filer_session):
    # A row with ab_line null and asset_type "vehicle", sent back with its id -> kept unchanged.
```

Add `asset_lines` to `test_session_lock.py`'s `WRITES`.

- [ ] **Step 2: Run them to verify they fail.** Run: `$PY -m pytest apps/intake/tests/test_asset_lines_api.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** `AssetViewSet` keeps the base serializer; `create` requires `ab_line`. The nested serializer allows a null `ab_line`, so old rows round-trip. `details` is a nested serializer on read and write (the row's `get_details`/`set_details`), replaced whole.
- [ ] **Step 4: Update the listed tests' setup** to the new payload (`ab_line` for `asset_type`), keeping every assertion in `test_asset_debt_authz.py`. Run those files. Expected: pass. Tests that read `equity` assert its absence or are deleted, named in the report.
- [ ] **Step 5: Commit** `feat(intake): save the A/B lines and their answers through the session`.

### Task 3: Totals and the personas

**Files:**

- Modify: `backend/apps/forms/services/derivations.py:189-207,238-242,266-301,842-848`, `backend/apps/intake/asset_lines.py`, `backend/apps/intake/management/commands/seed_demo_data.py`, `docs/testing/persona-briefs/*.md`, `backend/apps/intake/tests/builders.py`
- Test: `test_form_101_schema.py`, `test_form_106sum_schema.py`, `test_schedule_a_b_schema.py`, `test_oracle_tier3.py`, `test_seed_demo_data.py`, `test_e2e_intake.py`, `test_completion.py`

**Interfaces:**

- Consumes: Task 1, Task 2.
- Produces: `part_total(rows: list, part: int) -> Decimal` in `asset_lines.py` (adds `current_value`, a null as zero). Rules, same names as today, keyed on the catalog: `total_real_property` (1), `total_vehicles` (2), `total_household_items` (3), `total_financial_assets` (4), `total_other_assets` (7), `total_personal_property` (2–7), `total_assets` (1–7), and new `total_business_property` (5), `total_farm_property` (6). The `has_*` rules read `ab_line` from this task on, so they stay right until Tasks 6 and 7 replace them. `other_asset_descriptions` reads line 53's rows until Task 7. `answer_asset_lines(session, yes: Iterable[str] = ()) -> None` in `builders.py`: stores `"no"` for every line `shown_lines` shows, `"yes"` for those named (and shows their gates). `answer_household`'s default calls it.
- CLAUDE.md: "Seed order" gains "Personas seeded before 3b have old asset rows and no line answers, so Complete and every forms call refuse them. Re-create them with `seed_demo_data --reset`."

- [ ] **Step 1: Write the failing tests** in `test_oracle_tier3.py` (the printed page, from the seeded persona) and `test_seed_demo_data.py`:

```python
@pytest.mark.parametrize("persona, field, expected", [
    ("maria", "undefined_26", "6,500.00"),      # line 5 (use the file's existing amount format)
    ("maria", "15 amount", "1,050.00"),         # line 15
    ("maria", "undefined_124", "380.00"),       # line 36
    ("maria", "undefined_167", "7,930.00"),     # line 63
    ("priya", "undefined_166", "67,900.00"),    # line 62
    ("deshawn", "15 amount", "2,800.00"),
    ("deshawn", "undefined_124", "12,700.00"),
    ("andres", "undefined_26", "4,300.00"),
    ("andres", "15 amount", "1,900.00"),
    ("andres", "undefined_124", "557.00"),
    ("andres", "undefined_167", "7,217.00"),
    ("sarah", "undefined_167", "0.00"),
])
def test_ab_totals_print_each_persona_s_hand_worked_figure(...): ...

def test_every_seeded_persona_has_finished_the_walk(): ...       # no shown line without an answer
def test_a_leased_car_is_seeded_at_zero_not_blank(): ...         # Andrés's Corolla: 0.00 and 0.00
def test_a_seeded_row_uses_no_old_asset_type(): ...
```

James's and DeShawn's remaining figures come from their PS tables and are worked by hand in the test comment. `test_form_106sum_schema.py`: 1a, 1b, 1c read the new totals; an unknown value adds zero.

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL on the seeded rows.
- [ ] **Step 3: Implement** the rules, then the seed: each persona's rows and answers from PS:147 (Maria), PS:388 (James), PS:623 (Priya), PS:844 (DeShawn), PS:1081 (Sarah, no rows), PS:1307 and PS:1392 (Andrés), with §10's corrections: savings kinds print on 17.3 (the row says `kind: "savings"`), James's line 16 has no text. Answer every other shown line No. Andrés answers 37 Yes and 46 No. Rows hold their `amount_owed` as today, unread. Update the briefs to match, and each persona's README line if it changes.
- [ ] **Step 4: Run** the listed files. Expected: pass. Fix each test the seed moved, and name the change in the report. State the `ASSERTED_CASES` delta (expected 0: no binding changes).
- [ ] **Step 5: Commit** `feat(forms): total A/B by its Parts and seed the personas' lines`.

### Task 4: What Complete and the forms refuse

**Files:**

- Modify: `backend/apps/intake/asset_lines.py`, `backend/apps/intake/views.py:255-314,605-620`, `backend/apps/forms/views.py:201-204` and its refusal handler
- Test: `backend/apps/intake/tests/test_asset_gaps.py` (new), `test_completion.py`, `apps/forms/tests/test_form_views.py`

**Interfaces:**

- Consumes: Task 1, Task 3's `answer_asset_lines`.
- Produces: `class AssetStepGap(Exception)` with `step = "assets"` and `asset_step_gaps(session) -> list[AssetStepGap]` in `asset_lines.py`. `_prepare` raises the first gap after `_check_finished` and before the means test; the views map it to a 422 `{error, step: "assets"}`, as `IncomeStepGap`. The packet list doesn't call it.
- Sentences, exact:
  - Old row: `Pick a line on the Assets step for "{description}".`
  - Unanswered: `Line {key} on the Assets step needs a Yes or No.`
  - Yes, no row: `Line {key} says Yes. Add what you have, or change it to No.`
  - No, or hidden, with rows: `Line {key} says No, but it still lists something. Remove it, or change the answer to Yes.`
  - Gate with nothing under it: `Line {key} says Yes, but every line under it says No. Change one of them.`
  - Row incomplete: `Line {key} needs more about "{name}" on the Assets step.`, where `name` is the row's description or make, or `one item` when it has neither.
- CLAUDE.md: "Forms need a completed intake" gains the assets gaps, `AssetStepGap` and where they fall in the order.

- [ ] **Step 1: Write the failing tests** in `test_asset_gaps.py`, one per §7 item:

```python
def test_an_old_row_is_refused_by_its_description(): ...
def test_an_unanswered_shown_line_is_refused(): ...
def test_a_hidden_line_needs_no_answer(): ...
def test_yes_with_no_row_is_refused(): ...
def test_no_with_a_row_is_refused(): ...
def test_a_row_under_a_gate_answered_no_is_refused(): ...
def test_yes_to_a_gate_with_every_line_under_it_no_is_refused(): ...

@pytest.mark.parametrize("line, details, description, value, entire", [...one failing case per shape in §7...])
def test_a_row_missing_what_its_shape_requires_is_refused(...): ...

def test_an_unknown_value_counts_as_given(): ...
def test_zero_counts_as_given(): ...
def test_cash_needs_no_text(): ...
def test_a_share_is_required_because_a_blank_prints_the_template_s_zero_percent(): ...
def test_a_vehicle_needs_no_model_year_or_mileage(): ...
def test_gaps_come_in_the_form_s_order(): ...
```

In `test_completion.py`: the gaps fall after Schedule J line 3 and before the scanned-debt gap, each with `step: "assets"`; a filer with no property and every line No has 100% for that section. In `test_form_views.py`: Generate, Generate All, Regenerate and an unfiled download are a 422 with `step: "assets"` for a session with an old row; the packet list is a 200; a filed form's download is unchanged.

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL.
- [ ] **Step 3: Implement.** Keep the function free of model imports; it reads `session.assets` and `session.asset_lines`. A session with no `AssetLineAnswers` row has every shown line unanswered.
- [ ] **Step 4: Run** the listed files and `-m "not slow"`. Expected: pass; tests that build a completed session already pass through `answer_household`'s default.
- [ ] **Step 5: Commit** `feat(intake): refuse Complete and the forms until the A/B walk is done`.

### Task 5: Two sheet settings and the `assets.` namespace

**Files:**

- Modify: `backend/apps/forms/schema.py:85-100,192-200,417-481,520-565,607-665`, `backend/apps/forms/services/sheets.py:53,167-235,258-330`, `backend/apps/forms/services/fill_resolver.py:50-96,147-160,300-342`, `backend/apps/intake/asset_lines.py`
- Test: `apps/forms/tests/test_checks.py`, `test_attached_sheets.py`, `test_fill_resolver.py`

**Interfaces:**

- Produces:
  - `SheetColumn.covers: tuple[str, ...] | None = None`; `SheetSpec.line_width: float = 36.0`, from an optional `"line_width"` in the schema's sheet. The sheet part carries `"line_width"` only when it isn't 36, so existing documents stay byte-identical, and `sheet_spec(part)` reads `part.get("line_width", 36.0)`. `fits_line_column(line, template, width=LINE_WIDTH)`.
  - E007: the width total uses `line_width`. A column with `covers` (an empty tuple is allowed) may bind a list no slot binds; each covered binding counts as printed, and a covered binding no slot binds is refused. `_LIST_BINDING` gains `assets\.line_\w+`.
  - `resolve_binding("assets.line_<key>[].<attr>", session)` and `assets.line_<key>_<kind>[].<attr>`: a list over `rows_on(ordered_assets(session), key, kind)`, using `ASSET_CELLS: dict[str, Callable[[AssetInfo], str]]` in `fill_resolver.py`. Cells: `description`, `value` (formatted as the other amounts; blank when null), `entire`, `who`, `nature`, `other_info`, `street`, `street_2`, `city`, `state`, `zip`, `county`, `other_kind`, `make`, `model`, `year`, `mileage`, `percent`, `beneficiary`, `has_personal_info` (`yes`/`no`), `community` (`"true"` or blank), one `kind_<PROPERTY_KIND>` per kind (`"true"` or blank), and the sheet-only `where`, `what`, `interest`, each one joined line of words. Any other attr raises `ValueError`.
  - `_sheet` prints a `covers` column from `resolve_binding(column.binding, session)[position - 1]`. `binding_fix` sends `assets.` to `{"step": "assets"}`.
- CLAUDE.md: "Schemas are checked at startup" gains `assets.`, `line_width` and `covers`.

- [ ] **Step 1: Write the failing tests:**

```python
def test_a_two_digit_line_fits_a_sheet_that_widens_its_line_column(): ...   # "17.{n}", line_width 48 passes E007; default 36 fails
def test_a_sheet_without_a_line_width_stores_none_and_draws_as_before(): ... # part has no key; drawn PDF text positions equal today's
def test_a_filed_sheet_redraws_at_its_stored_line_width(): ...
def test_columns_too_wide_for_the_wider_line_column_are_refused(): ...
def test_a_covering_column_counts_its_boxes_as_printed(): ...              # single-box slots covered: no E007
def test_an_uncovered_single_box_is_still_refused(): ...
def test_a_covering_column_naming_a_binding_no_slot_has_is_refused(): ...
def test_a_covering_column_prints_its_words_on_each_row_past_the_slots(): ...
def test_an_unknown_asset_attr_raises(): ...
def test_a_value_the_filer_does_not_know_is_a_blank_cell_and_a_zero_value_prints(): ...
def test_kinds_read_rows_of_that_kind_in_order(): ...
```

- [ ] **Step 2: Run them to verify they fail.** Run: `$PY -m pytest apps/forms/tests/test_checks.py apps/forms/tests/test_attached_sheets.py apps/forms/tests/test_fill_resolver.py -q`. Expected: the new tests FAIL; all others pass.
- [ ] **Step 3: Implement.** Synthetic schemas only; A/B binds nothing new yet.
- [ ] **Step 4: Run them, and `manage.py check`.** Expected: pass; every existing sheet test unchanged.
- [ ] **Step 5: Commit** `feat(forms): let a sheet widen its line column and print several boxes as words`.

### Task 6: A/B prints places, vehicles, items and cash

**Files:**

- Create: `data/forms/field_index/tools/build_schedule_a_b.py`
- Modify: `data/forms/schemas/schedule_a_b.json`, `data/forms/field_index/audit/step2_verification.json`, `backend/apps/forms/services/derivations.py`, `backend/apps/forms/tests/test_oracle_tier2.py`
- Test: `apps/forms/tests/test_schedule_a_b_schema.py`, `test_oracle_tier1.py`, `test_printed_page.py`

**Interfaces:**

- Consumes: Task 1's `LINES`; Task 3's totals; Task 5's bindings.
- Produces: `build_schedule_a_b.py`, run as `$PY data/forms/field_index/tools/build_schedule_a_b.py`, rewriting the schema and the A/B rows of the addendum. It reads each line's boxes from `form_b106ab.index.json` by `line`, `kind` and rectangle order. A row's boxes that the index's `line` splits (`3.1` and `3.1.`) count as one row. Rules: `ab_has_<key>` for every asked line (`yes` with a row, `no` with none and the line shown, blank when a gate hid it); `ab_line_2`, `ab_line_45`, `ab_line_52` (blank under their gate's No); `total_*` on 5, 15, 36, 54, 55–63, with new bindings for 59 (`undefined_163`) and 60 (`undefined_164`), 45 (`undefined_143`) and 52 (`undefined_154`).
- This task binds shapes `place`, `vehicle`, `vehicle_no_mileage`, `item`, `item_question`, `cash` and gates 37, 46. Groups `ab_<key>`, number `"<key>.{n}"`, `line_width` 48 on every A/B sheet.
- Line 1's sheet columns: Where it is (200, covers street, street_2, city, state, zip, county), What it is (100, covers the 8 kinds and other_kind), Who has an interest (100, covers who, nature, community, other_info), Entire, Portion. The last two widths are the implementer's, so long as the total with `line_width` is at most 504 and E007 passes. A vehicle's: Make, Model, Year, Miles (line 3 only), Who has an interest (covers who, community, other_info), Entire, Portion.
- `who` choices: `only_you` → the row's "Debtor 1 only" state, `with_someone` → its "another" state, taken per row from the index (the state's spelling varies: `One#20of#20debtors…`, `One#20of#20Debtors…`). Each `Check if this is community property…` box and each kind box is `{"true": <state>}`.
- CLAUDE.md: "Blank, not 0.00" gains A/B's rules; the File Map gains `asset_lines.py`.

- [ ] **Step 1: Write the failing tests** in `test_printed_page.py`, reading the baked page with `read_drawn`:

```python
def test_a_home_prints_on_line_1_1_with_both_values_and_its_kinds(): ...
def test_a_third_property_prints_on_page_2_and_a_fourth_on_a_sheet_counted_in_line_2(): ...
def test_a_leased_car_prints_zero_in_both_value_boxes(): ...             # 0.00, 0.00
def test_a_car_of_unknown_value_prints_its_make_and_blank_values(): ...
def test_a_co_owned_car_ticks_the_another_box_and_no_debtor_2_box(): ...
def test_the_community_box_stays_unticked_unless_the_filer_ticks_it(): ...
def test_a_boat_prints_on_line_4_not_line_3(): ...
def test_a_second_item_on_a_one_box_line_goes_on_a_sheet_numbered_6_2(): ...
def test_cash_prints_its_amount(): ...
def test_line_43_s_describe_prints_under_its_yes(): ...
def test_a_no_to_line_37_leaves_38_to_45_blank_and_59_at_zero(): ...
def test_a_no_to_line_1_leaves_line_2_blank_and_55_at_zero(): ...
def test_every_line_says_no_for_a_filer_with_nothing_and_totals_print_zero(): ...
```

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL.
- [ ] **Step 3: Write the tool, run it, and add the rules** with their `RULE_FIXES` entries. Remove `has_real_property`, `has_vehicles`, `has_bank_accounts`, `has_retirement_accounts`, `has_other_assets` for bindings this task re-keys, keeping those Task 7 still needs.
- [ ] **Step 4: Render pages 1–4, 8–10 of a filled test form to PNG and look at them.** Rows land in their boxes; a mismatched `line` in the index is fixed in the tool's mapping, never in the index.
- [ ] **Step 5: Run** the listed files, `manage.py check` and tier 2. Update `ASSERTED_CASES` by the counted delta, stated in the comment.
- [ ] **Step 6: Commit** `feat(forms): print A/B's places, vehicles, items and cash on their lines`.

### Task 7: A/B prints the lists, labelled lines and shared boxes

**Files:**

- Modify: `data/forms/field_index/tools/build_schedule_a_b.py`, `data/forms/schemas/schedule_a_b.json`, `data/forms/field_index/audit/step2_verification.json`, `backend/apps/forms/services/derivations.py`, `backend/apps/forms/tests/test_oracle_tier2.py`
- Test: `apps/forms/tests/test_printed_page.py`, `test_oracle_tier3.py`, `test_schedule_a_b_schema.py`

**Interfaces:**

- Consumes: Task 6's tool.
- Produces: bindings for shapes `named`, `named_share`, `insurance`, `labelled`, `shared_box`. Labelled kinds are groups `ab_<key>_<kind>`, binding `assets.line_<key>_<kind>[]`, with `number` `17c.{n}`, `17s.{n}`, `17d.{n}`, `17o.{n}`; line 21: `21k.{n}`, `21p.{n}`, `21i.{n}`, `21r.{n}`, `21h.{n}`, `21a.{n}`; line 22: `22a.{n}` to `22i.{n}` in form order. Each sheet's title names its kind, for example "Official Form 106A/B, Schedule A/B: Property, line 17, checking accounts". Rules: `ab_line_28_text`, `ab_line_29_text`, `ab_line_53_text` (each row's description in order, joined with `"; "`; line 53 only its first three rows), and `ab_line_28_federal`, `_state`, `_local`, `ab_line_29_alimony`, `_maintenance`, `_support`, `_divorce_settlement`, `_property_settlement` (the kind's known values summed; blank when none is known). Line 53's three amounts are group `ab_53`'s slots; its sheet has a covering column (`covers: []`) binding `assets.line_53[].description` beside the value.
- Line 24's text and amount boxes use tags `T5`/`T6` (row 1), `T7`/`T8` (row 2), `T9`/`T10` (row 3). The form's text column for `percent` prints the number only: the template prints the "%".
- `has_*` and `other_asset_descriptions` are now gone, with their tests.

- [ ] **Step 1: Write the failing tests:**

```python
def test_a_savings_account_prints_on_17_3_not_17_1(): ...
def test_a_third_checking_account_goes_on_a_sheet_numbered_17c_3_and_counts_in_line_36(): ...
def test_a_second_401k_goes_on_a_sheet_and_additional_stays_the_filer_s_choice(): ...
def test_line_19_prints_entity_share_and_value(): ...
def test_each_of_line_24_s_three_rows_prints_in_its_own_box(): ...
def test_line_31_prints_company_beneficiary_and_a_zero_value(): ...
def test_two_federal_refunds_add_up_and_their_texts_join(): ...
def test_line_53_s_fourth_row_goes_on_a_sheet_with_its_text(): ...
def test_a_letter_the_form_can_t_print_is_a_422_linking_to_assets(): ...       # slot
def test_a_letter_the_form_can_t_print_on_a_sheet_links_to_assets(): ...
def test_a_description_too_long_for_its_box_is_a_422_linking_to_assets(): ...
```

Tier 3: each persona's line-level values from the PS tables, including Priya's two line 31 rows at 0.00 and Andrés's lines 38 and 40. `test_schedule_a_b_schema.py`: every catalog line has its boxes; no Debtor 2 box is bound.

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL.
- [ ] **Step 3: Extend the tool, run it, add the rules.**
- [ ] **Step 4: Render pages 5–8 and 10 and look at them,** and one attached sheet per shape.
- [ ] **Step 5: Run** the listed files, tiers 1–3 and `manage.py check`. Update `ASSERTED_CASES`. `known_defects.json` stays `[]`.
- [ ] **Step 6: Commit** `feat(forms): print A/B's lists, labelled lines and shared boxes`.

### Task 8: The walk's screens

**Files:**

- Create: `frontend/src/constants/assetLines.ts`, `frontend/src/components/wizard/steps/assets/AssetLine.tsx`, `frontend/src/components/wizard/steps/assets/AssetRowFields.tsx`, `frontend/src/components/wizard/steps/assets/assetGaps.ts`, `frontend/src/components/wizard/steps/AssetsStep.test.tsx`, `backend/apps/intake/tests/test_asset_lines_frontend_copy.py`
- Modify: `frontend/src/components/wizard/steps/AssetsStep.tsx` (rewritten), `frontend/src/constants/formText.ts`, `frontend/src/constants/copy.ts`, `frontend/src/types/api.ts`, `frontend/src/test/fixtures/session.ts`, `frontend/src/test/mocks/handlers.ts`, the step's CSS

**Interfaces:**

- Consumes: the API of Task 2 and Task 1's catalog.
- Produces:
  - `ASSET_LINES` in `assetLines.ts`, the catalog's copy, plus `AB_PARTS`. `shownLines(answers)`, `partIsComplete(part, rows, answers): boolean`, `firstIncompletePart(rows, answers): number` (1–7; 1 if none) in `assetGaps.ts`, mirroring §7.
  - `AssetsStep` props: `rows: WizardRow<AssetInfo>[]`, `onRowsChange`, `answers: Record<string, 'yes' | 'no'>`, `onAnswersChange`, `part: number` (1–7), `onValidationChange(isValid: boolean)`. `isValid` is `partIsComplete` and no old rows. The step holds no copies.
  - Inputs are named `line_<key>_<rowIndex>_<field>`, the radios `line_<key>_answer` with values `yes` and `no`. E2E depends on them.
- `copy.ts` sentences, exact: §6.2's two notes with their DRAFT comments; "You said you don't know the value of these"; removal: `Remove {n} item(s) you listed on this line?` with `Remove` and `Keep them`; for a gate: `Remove {n} item(s) you listed under this line?`. The box above Part 1 reads: "That's okay. Many Americans filing for bankruptcy don't have significant assets. It is not a failure. Answer No to each line that doesn't apply to you."

- [ ] **Step 1: Write the failing tests:**

```tsx
it('starts with neither No nor Yes selected on any line');
it('shows the form words and examples for each line, including lines 12 to 14 and 26 to 28');
it('keeps Continue invalid until every shown line in the Part is answered');
it('opens one row on Yes, with Add another');
it('treats a typed $0 as an answer and shows it as 0 after a reload');
it('clears the figure when I do not know is pressed, and clears the flag when a figure is typed');
it('asks in the page before No removes rows, and Keep them leaves rows and the Yes');
it('hides lines 38 to 44 until line 37 says Yes');
it('asks before a gate going to No removes rows, and clears the hidden answers');
it('shows Only you and You and someone else only on lines 1, 3 and 4');
it('never pre-selects who, kinds or the community box');
it('shows no amount owed, no account number and no equity');
it('offers the line 3 lease note and marks no value for the filer');
it('has no axe violations on each Part');
```

`test_asset_lines_frontend_copy.py` pins `assetLines.ts` to `LINES` (keys, parts, shapes, capacities, kinds). Reading-level picks up the new `copy.ts` sentences.

- [ ] **Step 2: Run them to verify they fail.** Run: `npx vitest run src/components/wizard/steps/AssetsStep.test.tsx --maxWorkers=2`. Expected: FAIL.
- [ ] **Step 3: Implement.** Amounts use `inputMode="decimal"`. No `||` or `!` on an amount: test against `null`/`undefined`. No browser dialogs. One column at phone width, with tap targets of at least 44 px.
- [ ] **Step 4: Run** the tests, tsc, lint and format. Expected: pass.
- [ ] **Step 5: Commit** `feat(wizard): ask each A/B line in the form's words`.

### Task 9: The wizard holds the Part

**Files:**

- Modify: `frontend/src/pages/IntakeWizard.tsx:152,176,277-285,383-388,417-426,432-481,544-594,709-715`, `frontend/src/components/wizard/steps/AssetsStep.tsx` (old rows), `frontend/src/components/wizard/steps/ReviewStep.tsx`
- Test: `frontend/src/pages/IntakeWizard.test.tsx` (or the wizard's existing test file), `ReviewStep`'s test file

**Interfaces:**

- Consumes: Task 8's props and helpers.
- Produces: wizard state `assetPart: number` and `assetAnswers`. On entering step `assets`, `assetPart = firstIncompletePart(...)`. `handleNext` on this step below Part 7: `saveNow()`, on success `setAssetPart(part + 1)`, no `updateCurrentStep`. `handlePrevious` above Part 1 moves the Part. The body is `{assets: assetsData, asset_lines: assetAnswers}`, unfiltered, each row's `_key` left out as today. `enabled` becomes `!!session && (canProceed || currentStepKey === 'assets') && currentStepKey !== 'review'`. Hydration converts `entire_value` too. Rows pair ids by position as before.
- Old rows: above Part 1, each row's description, value and `asset_type`, a line picker in the form's words with no default, and Remove. Picking sets `ab_line` and answers that line Yes; `current_value` stays; `entire_value` isn't copied.
- Review: rows by Part in catalog order; the unknown-values list with each row's line, its description and a `Go to` link to the step; absent when none.
- CLAUDE.md: "Autosave sends only real edits" gains step 5's body, "The wizard re-reads the session" gains where the step opens.

- [ ] **Step 1: Write the failing tests:**

```tsx
it('sends rows of every Part on each save, a half-filled row and an old row included');
it('sends nothing when a loaded step is only visited');
it('autosaves mid-Part while Continue is disabled');
it('moves Part by Part with no update_step until it leaves Part 7');
it('sends update_step once on leaving Part 7');
it('Back moves to the previous Part, then the previous step');
it('opens at the first Part with an unanswered line or an incomplete row');
it('blocks Continue while an old row has no line, and suggests no line');
it('picking a line keeps the old figure as the portion and asks for the entire value on line 3');
it('keeps ids across saves when a row is added on one Part and another is removed on the next');
it('reads back a completed intake with no save and reopens only on an edit');
it('Review lists values the filer does not know, and omits the list when there are none');
```

- [ ] **Step 2: Run them to verify they fail.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the wizard, Review and useAutoSave tests, then the frontend gates. Expected: pass.
- [ ] **Step 5: Commit** `feat(wizard): walk A/B Part by Part and save the whole step`.

### Task 10: The journeys

**Files:**

- Modify: `frontend/e2e/pages/wizard.page.ts:283-304`, `frontend/e2e/fixtures/personas.ts`, every `frontend/e2e/journeys/*.spec.ts` that passes the Assets step

**Interfaces:**

- Consumes: Task 8's input names.
- Produces: `PersonaAsset` carries `ab_line`, `details`, `current_value`, `entire_value`. `addAsset(asset)`: answers the line Yes, then fills its row by shape. `answerLinesNo()`: answers No on every unanswered radio of the Part showing. `walkAssets(persona)`: for each Part, its rows, then `answerLinesNo()`, then Continue. Fixture rows match the seed's.

- [ ] **Step 1: Update the page object, fixtures and journeys.** Sarah and the scanned-bill journey answer No to every line; Andrés's answers 37 Yes and fills Part 5.
- [ ] **Step 2: The controller runs the journeys** (`zsh .claude/e2e.sh 2`), load permitting. Expected: 8 passed, with no skip other than those CI expects. Packet counts unchanged (Maria 15, Sarah 15, DeShawn 14, Andrés 14, James 14, Priya 15).
- [ ] **Step 3: Check one journey's PDF:** Andrés's A/B prints the Corolla at 0.00/0.00, the Fit at 8,600.00/4,300.00 and lines 38 and 40.
- [ ] **Step 4: Commit** `test(e2e): walk the A/B lines in every journey`.

### Task 11: Sweep

**Files:**

- Modify: `CLAUDE.md`, `docs/superpowers/specs/2026-10-16-forms-step3-personas.md` only if a correction of §10 needs noting at its line

- [ ] **Step 1: Grep for what should be gone.** `grep -rnE "asset_type|equity|has_real_property|has_vehicles|has_bank_accounts|has_retirement_accounts|has_other_assets|other_asset_descriptions" backend/apps frontend/src frontend/e2e --include="*.py" --include="*.ts" --include="*.tsx"`. Expected hits: the model, migrations, the read-only serializer field, the old-row display and their tests. Anything else is fixed or justified in the report.
- [ ] **Step 2: Read each gotcha §11 names against the code,** and add the catalog gotcha: `apps/intake/asset_lines.py` is the catalog, `assetLines.ts` its pinned copy, a new line or kind needs both, the schema is regenerated with the tool, and the form's words come from the template.
- [ ] **Step 3: The controller runs every gate,** journeys included, on the final tree.
- [ ] **Step 4: Commit** `docs: bring CLAUDE.md up to date with Schedule A/B`.
