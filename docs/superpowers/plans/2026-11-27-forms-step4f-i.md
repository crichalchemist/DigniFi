<!-- prettier-ignore-start -->

# Forms step 4f-i: the affairs record, its printing plumbing, and the SOFA cut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land everything Form 107 lines 1–12 need underneath the screen, and take SOFA out of every read and write path. The filer's screens and Form 107's printed output stay as they are at `228371f`, except that `/sofa` is gone and the 122A-2 page continues to `/forms`.

- **The record.** A new encrypted record, `FinancialAffairsAnswers` (intake `0050`), saves Form 107 lines 2 and 4–12 by line through the session PATCH. It locks, reopens a completed intake, prunes picked debt ids, stamps the line 4 year label once and keeps it while any amount it labels is stored (R-4), and keeps line 6's answer and its branch together (R-5).
- **The printing plumbing.** The `affairs.` namespace learns the record's cells as Form 107 prints them: amounts to the cent or blank, dates only as MM/DD/YYYY, last 4 only as four digits, the computed sheet cells, line 12's statement, money cells for totals, a startup key check (E007) and the `affairs_*` section predicates. No live schema binds any of it yet.
- **The fixtures.** The engine tests print `affairs.l6_rows[]` instead of `SOFACreditorPayment` rows.
- **The SOFA cut.** `/sofa`, its links, its E2E pieces, its API, its serializers, its namespace and its seed block go. The three SOFA classes and their tables stay, unread, until 4i (P1). Two SOFA predicates still read `sofa_report` until 4f-ii's tool rewrites the bindings that name them (H6, R-3).

**4f-ii follows.** It builds wizard step 10, "The last few years, part 1": the words (`copy.ts`, `formText.ts`, the two pinned definitions), `build_form_107.py` (the schema, the addendum rows, `form_107.limits.json`, `ASSERTED_CASES` 1935 → 2079, then the two SOFA predicates removed), the image check and `check29`, `affairs_step_gaps` and `affairs_fit`, the step component, and the wiring (the 10 → 11 shift and intake `0051`, `WIZARD_STEPS`, the `completion_gaps` splice, the builders' default, the seed for all six personas, `personas.ts` and `walkLastFewYears1`, Review's date line). 4f-i leaves it:
- a record with no caps file and no reader of caps (R-1);
- `NEW_STEP_KEYS` still holding `last_few_years_1`, and `test_rule_fixes.py` already accepting it (T-i.2);
- `has_prior_income` and `has_creditor_payments` still reading `sofa_report` (H6);
- no `FINANCIAL_AFFAIRS_DEFAULTS`, no seeded affairs record and no gap, so nothing refuses a session for want of step 10.

**Architecture:**

- **The record (§3 of the design).** One encrypted JSON object keyed by line (`KEYS`), plus a server-stamped `answered_on`, one-to-one with the session (`related_name="financial_affairs"`, `db_table="financial_affairs_answers"`).
  - The serializer refuses only an unknown key, a wrong type, a value outside its set, a JSON boolean, an unknown cell, a value over its hard ceiling, and a body carrying only one of `l6_answer` and `l6_branch`. Shapes (dates, amounts, last 4) are stored as typed (B47, R-12).
  - `merge(sent, confirmed_debt_ids, fill_year)` replaces each sent key whole, prunes `debt_id` cells that name no confirmed debt of the session (R-9), and keeps or removes `l4_year` (R-4). It runs last in `create()` and `update()` (R-14).
- **The cells (§5.2).** `answer_records.py` stays a leaf (it imports only `re`, `datetime`, `decimal` and `collections.abc`). It holds a literal table of the record's cells, pinned equal to `FinancialAffairsAnswers.LIST_CELLS` by a test, and the printers. `record_value`'s `affairs.` branch shapes each line 1–12 cell as printed and raises `ValueError` on a list or cell it doesn't know (R-48). Lines 13–28 keep today's plain read until 4g.
- **The check (R-11).** `_affairs_binding_error` refuses an `affairs.` binding that names no key of the record, binds a row list as a scalar or a scalar as a list, or names a cell neither stored nor computed, over every field, sheet column and `covers` entry.
- **The cut (R-3, H5, H9, H10).** The frontend, routes and E2E cut (T-i.4) lands before the backend cut (T-i.5), so no commit opens an E2E red window (CODE-7).

**Tech Stack:** No new dependency.
- Backend: Django 5.0 + DRF, pytest-django (sqlite, plus the throwaway Postgres for `postgres`-marked cases).
- PDFs: pypdf 6.13 and PyMuPDF (only through the existing `split_explain` measure).
- Frontend: React 19 + Vite + TypeScript, vitest + MSW, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-18-forms-step4-design.md` (cited `S:line`): §14.4's SOFA cut (S:662-683), the ordering rules (S:666, S:801), §7.4's record (S:428) and S:187's year label as B44 decides it. The single design source is `.superpowers/plan-4f/plan-design.md` (sections 0–11, cited `D§n`), revision 2, with §11's resolutions. Above it, in order:
- `.superpowers/plan-4f/owner-decisions.md` (`OD`: F1–F8, and P1–P14 adopted as written);
- `.superpowers/plan-4f/owner-copy.md` (`OC`, approved as written by F7, a closed set);
- the spec.

Every `path:line` below was re-read at `feat/forms-step4f` = develop `228371f`. A task that lands earlier moves the lines after it; the symbol named beside each cite is authoritative.

**Owner words.** 4f-i ships no `OC` string. Every `AFFAIRS_*` constant lands in 4f-ii's T-ii.1. The one `OC` row 4f-i acts on is a removal (OC §6): `PAGE_LINK_LABELS['/sofa']`, `'Go to Statement of Financial Affairs'`, goes in T-i.4 with the page and all its words, with nothing carried over and no notice (F6, B24, R-38). The two serializer 400 messages (`"Not a Form 107 line 1-12 answer: {key}."`, `"Check the answer for {key}."`) follow the serializer's existing pattern (`serializers.py:1352`, `:1380`, `:1401`, `:1417`). They are API messages, not `OC` rows, and are carried as D§3 spells them.

**Controller and owner resolutions (D§11, 2026-11-27).** D§8 items 1–4 are acknowledged as written: R-6's tagging (4f-ii), R-1's limits file in 4f-ii, the swap of T-i.4 and T-i.5, and the test-line allowance in T-i.2. D§9's DeShawn question is answered Yes (F8). That decision is 4f-ii's T-ii.6, and nothing in 4f-i depends on it.

## Global Constraints

These are verbatim. Each is expanded in the bullets after it.

- vitest runs with --maxWorkers=2
- never tsc -b
- ruff==0.8.5
- backend tests with --ds=config.settings.test
- each task's commit stages by explicit path, never .serena/, DESIGN.md, assets/, .impeccable, .claude/, .superpowers/
- no model or agent co-author trailer in commits
- 4f-i ships no new sentence; any new sentence would be marked // DRAFT: counsel C-41
- every printed box blank, never 0.00 or a No the filer didn't give
- every new filer column encrypted with a ciphertext test
- known_defects.json stays []
- ASSERTED_CASES stays 1935
- intake migration 0050_financial_affairs_answers, depending on 0049_shift_current_step_for_plans
- DIG-523 (Priya's 42px target, macOS only) is a known local failure

The constraints in full:

- **The PR boundary.** 4f-i changes:
  - one new intake model, `FinancialAffairsAnswers`, and one intake migration, `0050_financial_affairs_answers` (one `CreateModel`, encrypted from creation). There is no forms or districts migration (F4), and no SOFA state change (P1: the classes and tables stay);
  - `answer_records.py`, `explain_split.py`, `fill_resolver.py`, `schema.py` and `derivations.py` for the plumbing, with no schema JSON changed;
  - the SOFA cut, frontend then backend.
  - It changes no Form 107 box: `form_107.json` and `step2_verification.json` are not touched.
- **Commands** (the 4e plan's job scripts, unchanged; `JOB=/Users/controlroom/.claude/jobs/bb720722/tmp/4b-sdd`):
  - Backend tests with `--ds=config.settings.test`: `zsh $JOB/pt.sh <paths relative to backend/> --ds=config.settings.test -q` ("`pt.sh`" below). It passes no `-m`, so `slow` cases run. Name files; never run the whole suite from a task (T-i.6's gate is the one exception). Take counts from pytest's last line through a one-line `printf`.
  - `zsh $JOB/ppt.sh <paths>` for `postgres`-marked cases.
  - `zsh $JOB/py.sh manage.py check --settings=config.settings.test` ("`check`") and `zsh $JOB/py.sh manage.py makemigrations --check --dry-run --settings=config.settings.test` ("`makemigrations --check`"; no CI step runs it).
  - Frontend: `zsh $JOB/fe.sh npx vitest run --maxWorkers=2 <files>` (vitest runs with --maxWorkers=2); `zsh $JOB/fe.sh npx tsc -p tsconfig.app.json --noEmit` (never tsc -b); `zsh $JOB/fe.sh npx eslint <files>`; `zsh $JOB/fe.sh ./node_modules/.bin/prettier --write <files>`, then `--check`; `userEvent` with no fake timers.
  - Lint: ruff==0.8.5. CI runs `ruff check` only. Run `ruff format --check` only on files a task creates (the pre-existing "63 files would be reformatted" stays). Lines are 100 columns at most.
  - E2E: `zsh $JOB/e2e-one.sh <spec|all> <label>`, only in T-i.4 and T-i.6.
- **Git.**
  - `/opt/local/bin/git`: one plain command per call, from the worktree root, on `feat/forms-step4f`. No push, merge or branch change.
  - One commit per task. Each task's commit stages by explicit path, never `.serena/`, `DESIGN.md`, `assets/`, `.impeccable`, `.claude/` or `.superpowers/`. A deletion is staged with `/opt/local/bin/git rm <path>`.
  - No model or agent co-author trailer in commits (Rule 14 overrides the harness's attribution reminder).
  - Never a bare `sed -i`.
  - Pre-commit runs `black`, `ruff`, `prettier`, `eslint --max-warnings=0` and `check-json`. If it reformats a file, re-stage the same paths and commit again.
- **Blank, not 0.00.** No box changes in 4f-i. The printers T-i.2 adds print a malformed amount, date or last 4 as `""`, an absent tick as `""`, and a `"0"` amount as `"0.00"` only because the filer typed it.
- **Encryption.** `FinancialAffairsAnswers.answers` and `answered_on` are encrypted from `0050`, with a ciphertext test that reads the raw row (`gAAAAA…`, no plaintext word or year).
- **Tier 2 and the known defects.** No binding changes, so `ASSERTED_CASES` (`backend/apps/forms/tests/test_oracle_tier2.py:37`) stays **1935** and `known_defects.json` stays `[]`. `check` passes after every task.
- **Known local failure.** DIG-523 is reported, not fixed, in every gate count.
- **Tests encode intent.** Names say the outcome. Synthetic data only, "Demo" names. A guard that passes before its code gets a see-it-fail mutation, named in its task and reverted.

## Review Focus

The five input classes most likely to pass a task review while wrong. Each has its test in the owning task.

1. **The year label never moves under a stored amount** (R-4, B44, D§7 item 1). An unrelated save, a changed figure and the Continue body, each after January 1, keep `l4_year`; clearing every line 4 and line 5 amount removes it; a line 5 amount alone stamps it; an echoed year changes nothing.
   - T-i.1: `test_the_year_label_never_moves_while_an_amount_it_labels_is_stored`, `test_continue_after_new_year_resends_the_whole_body_and_moves_nothing`, `test_line_4_amounts_kept_under_a_no_still_pin_the_year`, `test_deleting_the_six_line_4_amounts_with_no_line_5_amount_removes_the_year`, `test_a_line_5_amount_alone_stamps_the_year`, `test_a_sent_year_or_fill_year_is_ignored`.
2. **The prune drops only `debt_id`, never the row or its typed name, and runs after the same PATCH's debts** (R-9, R-14, D§7 item 8).
   - T-i.1: `test_a_picked_debt_id_is_pruned_when_it_names_no_confirmed_debt_of_the_session`, including the debt deleted in the same PATCH.
3. **No JSON boolean, number or foreign value enters the record** (R-12, R-13, D§7 item 10): `debt_id` sent as `7`, a tick sent as `true`, a status outside its set, half a surrogate pair.
   - T-i.1: `test_an_unknown_key_wrong_type_or_value_over_its_ceiling_is_a_400_naming_the_key_not_the_value` and `test_no_answer_is_stored_as_a_boolean`.
4. **A malformed date or amount is stored, prints blank, and never adds into a total** (B47, R-12, D§7 item 4).
   - T-i.1: `test_a_malformed_date_or_amount_is_stored_as_typed`.
   - T-i.2: `test_an_affairs_amount_prints_to_the_cent_and_a_malformed_one_prints_blank`, `test_an_affairs_date_prints_only_as_mm_dd_yyyy`.
   - T-i.3: `test_a_malformed_paid_amount_prints_blank_and_adds_nothing_to_the_total`.
5. **Old SOFA data changes nothing Form 107 prints, and nothing writes SOFA any more** (D§7 item 14). Tier 3 doesn't cover Form 107, so this needs tests of its own. No binding changes either: `form_107.json` and `step2_verification.json` are untouched in 4f-i, and `ASSERTED_CASES` stays 1935.
   - T-i.5: `test_an_old_sofa_report_changes_nothing_form_107_prints`, `test_saving_form_answers_writes_no_sofa_report`, `test_a_session_with_an_old_sofa_report_still_deletes`.

---

### Task 1: `FinancialAffairsAnswers`, its save, prune, year and branch rules (T-i.1)

Rulings carried: R-4 (B44, P7), R-5 (B51, P2), R-9 (P3), R-12 (B47), R-13 (OPEN-12), R-14 (R-SAVE-ORDER widened), R-47 (CODE-2), P3, P7, F6. No `OC` string ships.

**Files:**
- Create:
  - `backend/apps/intake/migrations/0050_financial_affairs_answers.py` (one `CreateModel`, depending on `0049_shift_current_step_for_plans`);
  - `backend/apps/intake/tests/test_financial_affairs_answers.py`;
  - `backend/apps/intake/tests/test_financial_affairs_encryption.py`.
- Modify:
  - `backend/apps/intake/models.py`: the new class after `IntentionAnswers` (`:1162-1228`, the pattern);
  - `backend/apps/forms/services/answer_records.py`: `branch_of` beside `is_mm_dd_yyyy` (`:150`);
  - `backend/apps/intake/serializers.py`:
    - `_INTAKE_DATA` (`:1027-1040`) gains `"financial_affairs"`;
    - `FinancialAffairsField` after `IntentionAnswersField` (`:1157-1165`);
    - `_save_financial_affairs` after `_save_intention_answers` (`:1176-1186`);
    - the value checks after `_intention_entries_ok` (`:1212-1223`);
    - the field after `intention_answers = IntentionAnswersField(required=False)` (`:1287`) and `"financial_affairs"` after `"intention_answers"` in `fields` (`:1315`);
    - `validate_financial_affairs` after `validate_intention_answers` (`:1407-1419`);
    - the empty-body guard after the `intention_answers` one (`:1523-1525`);
    - the pop beside `intention_answers_data` in `create()` (`:1460`) and `update()` (`:1540`); the save after `_save_intention_answers` in `create()` (`:1501-1502`, before `return session`) and in `update()` (`:1595-1596`, before `return instance`);
    - the import of `FinancialAffairsAnswers` beside `IntentionAnswers` (`:67`). The serializer needs no `branch_of`: the pair rule checks presence only.
  - `backend/apps/intake/views.py:153-165`: `select_related` gains `"financial_affairs"` after `"intention_answers"`;
  - `backend/apps/intake/tests/builders.py`: `answer_financial_affairs` after `answer_intentions` (`:267`);
  - `backend/apps/intake/tests/test_session_lock.py`: `WRITES` (`:560`) gains a `financial_affairs PATCH` row after `intention_answers PATCH` (`:613-618`).

**Interfaces:**
- Consumes `fill_date` (`apps/districts/dated_tables.py:58`), `DebtInfo.objects.confirmed()` / `session.debts.confirmed()` (`models.py:1230-1231`), `answer_petition` (`builders.py:237`).
- Produces, in `apps.forms.services.answer_records`:
  - `branch_of(debt_nature: str | None) -> str | None`: `"consumer"` for `"consumer"`, `"other"` for `"business"` or `"neither"`, `None` otherwise (absent, `""`, any other value). Pure, no import.
- Produces `FinancialAffairsAnswers` (`apps/intake/models.py`), the D§3 model:
  - `session = OneToOneField(IntakeSession, CASCADE, related_name="financial_affairs")`, `answers = EncryptedTextField(default="{}")`, `answered_on = EncryptedCharField(max_length=10, null=True, blank=True)`, `created_at`, `updated_at`; `Meta.db_table = "financial_affairs_answers"`;
  - `KEYS: ClassVar[tuple[str, ...]]`, in this order: `l2_answer`, `l2_rows`, `l4_answer`, `l4_year`, `l4_current_wages`, `l4_current_business`, `l4_last_wages`, `l4_last_business`, `l4_prior_wages`, `l4_prior_business`, `l5_answer`, `l5_current_rows`, `l5_last_rows`, `l5_prior_rows`, `l6_answer`, `l6_branch`, `l6_rows`, `l7_answer`, `l7_rows`, `l8_answer`, `l8_rows`, `l9_answer`, `l9_rows`, `l10_answer`, `l10_rows`, `l11_answer`, `l11_rows`, `l12_answer`, `l12_statement`;
  - `YES_NO_KEYS` (the ten `l<n>_answer`), `BRANCHES = ("consumer", "other")`, `L4_AMOUNT_KEYS` (the six `l4_current_*`/`l4_last_*`/`l4_prior_*`, in `KEYS` order), `L5_LIST_KEYS = ("l5_current_rows", "l5_last_rows", "l5_prior_rows")`, `PICKED_LIST_KEYS = ("l6_rows", "l7_rows", "l8_rows")`;
  - `LIST_CELLS: ClassVar[dict[str, tuple[str, ...]]]`, exactly D§3's table:
    - `l2_rows`: `street`, `street_2`, `city`, `state`, `zip`, `from`, `to`;
    - `l5_current_rows`, `l5_last_rows`, `l5_prior_rows`: `source`, `amount`;
    - `l6_rows`: `debt_id`, `name`, `street`, `street_2`, `city`, `state`, `zip`, `date_1`, `date_2`, `date_3`, `paid`, `owed`, `mortgage`, `car`, `credit_card`, `loan`, `vendors`, `other`, `other_text`;
    - `l7_rows`, `l8_rows`: `debt_id`, `name`, `street`, `street_2`, `city`, `state`, `zip`, `date_1`, `date_2`, `date_3`, `paid`, `owed`, `reason`;
    - `l9_rows`: `case_title`, `case_number`, `nature`, `court_name`, `court_street`, `court_city`, `court_state`, `court_zip`, `status`;
    - `l10_rows`: `name`, `street`, `street_2`, `city`, `state`, `zip`, `property`, `date`, `value`, `repossessed`, `foreclosed`, `garnished`, `attached`;
    - `l11_rows`: `name`, `street`, `street_2`, `city`, `state`, `zip`, `action`, `date`, `amount`, `last_4`;
    - `l12_statement`: `text`;
  - `TICK_CELLS = frozenset({"mortgage", "car", "credit_card", "loan", "vendors", "other", "repossessed", "foreclosed", "garnished", "attached"})` (each `"yes"` or absent);
  - `STATUSES = ("pending", "on_appeal", "concluded")`;
  - `AMOUNT_CELLS = frozenset({"paid", "owed", "amount", "value"})`, `DATE_CELLS = frozenset({"from", "to", "date_1", "date_2", "date_3", "date"})`, `SHAPED_CELLS = frozenset({"state", "zip", "last_4"})`;
  - `TEXT_CEILING = 500`, `STATEMENT_CEILING = 2000`, `SHAPED_CEILING = 32`, `ROW_CEILING = 100`;
  - `get_answers() -> dict` (`json.loads(self.answers)`);
  - `merge(sent: Mapping[str, Any], confirmed_debt_ids: set[int], fill_year: int) -> None` (D§3 "Merge"; it doesn't save):
    1. every key is checked first: one outside `KEYS` raises `KeyError(key)`;
    2. each sent key is replaced whole, and `None` removes it;
    3. R-9: in each row of `PICKED_LIST_KEYS`, a `debt_id` not in `{str(pk) for pk in confirmed_debt_ids}` is removed from that row; the row stays;
    4. R-4: an amount counts when any `L4_AMOUNT_KEYS` value, or any `amount` of a `L5_LIST_KEYS` row, is a string non-blank after `strip()`, whatever `l4_answer` and `l5_answer` say. No amount counted → `l4_year` removed; an amount counted and `l4_year` absent → `l4_year = fill_year` (an int); otherwise left alone;
    5. `answers != stored` → `self.answers = json.dumps(answers)` and `self.answered_on = fill_date().isoformat()`.
- Produces, on `IntakeSessionSerializer`:
  - `financial_affairs = FinancialAffairsField(required=False)`. Read: `{**record.get_answers(), "answered_on": record.answered_on, "fill_year": fill_date().year}`, or `{"answered_on": None, "fill_year": fill_date().year}` with no record. `l4_year` reads as stored (an int) when stored. The PATCH reply carries the same representation, read after the save (R-42 consumes it in 4f-ii).
  - `validate_financial_affairs(sent) -> dict` (D§3 "Validation", all or nothing, before any write):
    - drop the echoes `answered_on`, `l4_year`, `fill_year`;
    - a key outside `KEYS` → `ValidationError("Not a Form 107 line 1-12 answer: {key}.")`;
    - `("l6_answer" in body) != ("l6_branch" in body)` (after dropping echoes) → `ValidationError("Check the answer for l6_answer.")` (R-5);
    - any other refusal → `ValidationError("Check the answer for {key}.")`: a `YES_NO_KEYS` value not `"yes"`/`"no"`; `l6_branch` not in `BRANCHES`; an `L4_AMOUNT_KEYS` value not a string or longer than `SHAPED_CEILING`; a list key whose value isn't a list, holds more than `ROW_CEILING` rows, or holds an element that isn't an object; a row cell (after dropping `_key`) outside `LIST_CELLS[key]`; a non-blank cell value that isn't a string (so no `bool` or number cell enters); a tick not `"yes"`; a status not in `STATUSES`; `debt_id` not matching `^[1-9][0-9]{0,9}$`; an amount, date or shaped cell over `SHAPED_CEILING`; `l12_statement[].text` over `STATEMENT_CEILING`; any other cell over `TEXT_CEILING`; any string `.encode("utf-8")` refuses;
    - `None` is allowed as a key's value (it removes the key);
    - each row's `_key` is dropped before it is checked and stored, and so is a blank cell: a cell whose value is `None`, or `""` on a tick, `status` or `debt_id`, is absent (D§3's "`"yes"` or absent"), never a 400, so no `None` cell is ever stored. A `""` text, amount, date or shaped cell is a string and is stored as typed;
    - no message ever contains the sent value.
  - `_save_financial_affairs(session, data) -> None`: `record, _ = FinancialAffairsAnswers.objects.get_or_create(session=session)`; `record.merge(data, {d.pk for d in session.debts.confirmed()}, fill_date().year)`; `record.save()`; `session.financial_affairs = record`. `confirmed()` is a fresh query, so it sees this PATCH's debts (R-14).
- Produces `builders.answer_financial_affairs(session, **answers) -> FinancialAffairsAnswers`, through the session's own relation as the sibling builders do (`builders.py:237-283`, "never a fresh query", so the session a test holds never reads a stale copy); `None` removes a key (R-47):
  - the record: `record = getattr(session, "financial_affairs", None) or FinancialAffairsAnswers(session=session)`, then `record.merge(answers, {d.pk for d in session.debts.confirmed()}, fill_date().year)`, `record.save()`, `return record`;
  - an `l6_answer` given as a string without `l6_branch` takes `branch_of(<stored debt_nature>)`, read through `getattr(session, "petition_answers", None)` (its `get_answers().get("debt_nature")`; no record counts as none stored); with no stored `debt_nature` it raises `ValueError("answer debt_nature first")`;
  - `l6_answer=None` given without `l6_branch` sends `l6_branch=None` too, so the pair is removed together;
  - an `l6_branch` given without `l6_answer` raises `ValueError("l6_branch travels with l6_answer")`;
  - there is no default (H7: the default lands with the gates in T-ii.6).

- [ ] **Step 0: Check for drift.** Run `makemigrations --check` on the untouched tree. Expected: "No changes detected". Run `ls backend/apps/intake/migrations | tail -2`. Expected: `0049_shift_current_step_for_plans.py` is the newest. Otherwise stop and report.
- [ ] **Step 1: Write the failing tests.** `test_financial_affairs_answers.py` goes through the session PATCH (the `test_intention_answers.py` pattern, with the authenticated `filer` fixture of `apps/intake/tests/conftest.py:23`). The file defines its own helpers, since the siblings' are file-local: `_url` copied from `test_intention_answers.py:19-20`, `_walk` copied from `test_petition_answers.py:38-46`, and
  `_stored(s) = FinancialAffairsAnswers.objects.get(session=s).get_answers()`, `_record(s) = FinancialAffairsAnswers.objects.get(session=s)`, `_status(s) = IntakeSession.objects.get(pk=s.pk).status`. Its `_patch` wraps the body itself, and every call below passes the bare `financial_affairs` body, never a wrapped one:

  ```python
  def _patch(client, session, body):
      return client.patch(_url(session), {"financial_affairs": body}, format="json")
  ```

  The refused-body parametrize alone sends JSON text, as `test_intention_answers.py:225-227` does, since the test renderer can't encode the lone surrogate. Synthetic "Demo" data; `_today` is the root conftest's 2026-10-16 unless a test patches `apps.districts.dated_tables._today`.

  ```python
  def test_line_answers_save_by_line_and_read_back(...):
      body = {"l2_answer": "no", "l9_answer": "yes",
              "l9_rows": [{"_key": "new-1", "case_title": "Demo v. Demo", "status": "pending"}]}
      reply = _patch(client, session, body)
      assert reply.status_code == 200
      read = reply.data["financial_affairs"]
      assert read["l9_rows"] == [{"case_title": "Demo v. Demo", "status": "pending"}]  # _key dropped
      assert (read["l2_answer"], read["answered_on"], read["fill_year"]) == ("no", "2026-10-16", 2026)

  def test_a_session_with_no_record_reads_only_the_date_and_this_year(...):
      assert client.get(url).data["financial_affairs"] == {"answered_on": None, "fill_year": 2026}

  def test_each_key_sent_replaces_its_value_whole_and_null_clears_it(...):
      # two l6 rows, then one row: one stored; then {"l2_answer": None} removes the key
      assert len(_stored(session)["l6_rows"]) == 1
      assert "l2_answer" not in _stored(session)

  @pytest.mark.parametrize("gone", ["scanned_draft", "other_sessions_debt", "deleted_debt",
                                    "deleted_in_the_same_patch"])
  def test_a_picked_debt_id_is_pruned_when_it_names_no_confirmed_debt_of_the_session(gone, ...):
      # A row with debt_id of the `gone` debt and a row with a confirmed debt's id, both named.
      # "deleted_in_the_same_patch": one PATCH carries `debts` without that row and
      # `financial_affairs` naming it (R-14).
      rows = _stored(session)["l6_rows"]
      assert rows[0] == {"name": "Demo Gone Bank", "paid": "100.00"}          # only debt_id went
      assert rows[1]["debt_id"] == str(kept.pk)

  def test_the_year_label_never_moves_while_an_amount_it_labels_is_stored(monkeypatch, ...):
      _patch(..., {"l4_current_wages": "1200"});           assert _stored(s)["l4_year"] == 2026
      monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2027, 1, 5))
      _patch(..., {"l9_answer": "no"});                    assert _stored(s)["l4_year"] == 2026
      _patch(..., {"l4_current_wages": "1300"});           assert _stored(s)["l4_year"] == 2026
      _patch(..., dict.fromkeys(FinancialAffairsAnswers.L4_AMOUNT_KEYS, None))
      assert "l4_year" not in _stored(s)
      _patch(..., {"l4_last_wages": "900"});               assert _stored(s)["l4_year"] == 2027

  def test_continue_after_new_year_resends_the_whole_body_and_moves_nothing(monkeypatch, ...):
      # The body Continue sends (saveNow always saves; update_step never reads the record):
      # every stored KEYS value but l4_year, unchanged, on a completed intake (COV-3, CODE-12a).
      # Stored on 2026-10-16: l4_answer yes, l4_current_wages "1200", l9_answer no.
      monkeypatch.setattr("apps.districts.dated_tables._today", lambda: date(2027, 1, 5))
      body = {k: v for k, v in _stored(s).items() if k != "l4_year"}
      assert _patch(..., body).status_code == 200
      assert _stored(s)["l4_year"] == 2026
      assert _record(s).answered_on == "2026-10-16"
      assert _status(s) == "in_progress"   # any intake-data PATCH reopens (B44)

  def test_line_4_amounts_kept_under_a_no_still_pin_the_year(...):
      # l4_answer "no" with l4_current_wages "1200" still stored keeps l4_year (an amount kept
      # behind Show); then {"l4_current_wages": None} with no other amount removes it.

  def test_deleting_the_six_line_4_amounts_with_no_line_5_amount_removes_the_year(...):
      # the six keys sent as None, as the step's Delete sends them (COV-12, R-43)

  def test_a_line_5_amount_alone_stamps_the_year(...):
      # {"l5_answer": "yes", "l5_last_rows": [{"source": "Demo", "amount": "50"}]} → 2026 (P7)

  def test_a_sent_year_or_fill_year_is_ignored(...):
      # on a completed session with a stored record: {"l4_year": 1999, "fill_year": 1999,
      # "answered_on": "1999-01-01"} → 200, the stored object and answered_on unchanged,
      # status still "completed" (the empty-body guard)

  def test_line_6_answer_and_branch_travel_together(...):
      r = _patch(..., {"l6_answer": "yes"})
      assert r.status_code == 400 and "l6_answer" in str(r.data)
      assert _patch(..., {"l6_answer": "yes", "l6_branch": "consumer"}).status_code == 200
      assert _patch(..., {"l6_answer": None, "l6_branch": None}).status_code == 200
      assert "l6_answer" not in _stored(s) and "l6_branch" not in _stored(s)

  @pytest.mark.parametrize("body,typed", [
      ({"l13_answer": "no"}, None), ({"l2_answer": "maybe"}, "maybe"), ({"l2_answer": True}, None),
      ({"l6_rows": {}}, None), ({"l6_rows": ["x"]}, None), ({"l6_rows": [{"nmae": "Demo"}]}, "nmae"),
      ({"l10_rows": [{"repossessed": "no"}]}, None),
      ({"l10_rows": [{"repossessed": True}]}, None),
      ({"l9_rows": [{"status": "open"}]}, "open"), ({"l6_rows": [{"debt_id": 7}]}, None),
      ({"l6_rows": [{"debt_id": "0"}]}, None),
      ({"l6_rows": [{"name": "D" * 501}]}, "D" * 501),
      ({"l12_statement": [{"text": "D" * 2001}]}, "D" * 2001),
      ({"l6_rows": [{"paid": "1" * 33}]}, "1" * 33), ({"l2_rows": [{"city": "Demo"}] * 101}, "Demo"),
      ({"l2_rows": [{"city": "\ud800"}]}, None),
  ])
  def test_an_unknown_key_wrong_type_or_value_over_its_ceiling_is_a_400_naming_the_key_not_the_value(
      filer, body, typed):
      client, s = filer
      # JSON text, which can carry the lone surrogate the test renderer can't encode.
      text = json.dumps({"financial_affairs": body})
      refused = client.patch(_url(s), data=text, content_type="application/json")
      assert refused.status_code == 400
      assert next(iter(body)) in refused.json()["financial_affairs"][0]    # the key is named
      if typed is not None:
          assert typed not in refused.content.decode()                     # no sent value echoed
      assert not FinancialAffairsAnswers.objects.filter(session=s).exists()
      # No "no digit in the reply" check: the messages carry "107", "1-12" and "l13_answer".

  def test_a_malformed_date_or_amount_is_stored_as_typed(...):
      # {"l6_answer": "yes", "l6_branch": "consumer",
      #  "l6_rows": [{"name": "Demo Bank", "date_1": "13/40/2026", "paid": "12.345"}]}
      assert _stored(s)["l6_rows"][0]["date_1"] == "13/40/2026"
      assert _stored(s)["l6_rows"][0]["paid"] == "12.345"

  def test_no_answer_is_stored_as_a_boolean(...):
      # after a full save of every list, and after each refused boolean body above:
      assert not [v for v in _walk(_stored(s)) if isinstance(v, bool)]   # test_petition_answers.py:92

  def test_saving_line_answers_reopens_a_completed_intake(...)
  def test_an_echoed_answered_on_alone_saves_nothing_and_reopens_nothing(...)
  def test_answered_on_moves_only_when_the_stored_answers_change(...):
      # the same body sent twice on two patched days leaves the first date; then, on a third
      # patched day, one PATCH carries the debts list without the picked row and the unchanged
      # financial_affairs body (the shape Continue sends): the prune is the only change, and
      # answered_on moves to that day

  def test_a_blank_cell_is_stored_as_absent(...):
      # the blank shapes a browser row can carry are absent, never a 400 (D§3 "yes or absent")
      body = {"l6_answer": "yes", "l6_branch": "consumer", "l6_rows": [{"_key": "new-1",
              "name": "Demo Bank", "debt_id": None, "car": "", "mortgage": None, "street": ""}],
              "l9_answer": "yes", "l9_rows": [{"case_title": "Demo v. Demo", "status": ""}]}
      assert _patch(..., body).status_code == 200
      assert _stored(s)["l6_rows"] == [{"name": "Demo Bank", "street": ""}]
      assert _stored(s)["l9_rows"] == [{"case_title": "Demo v. Demo"}]

  def test_branch_of_follows_line_16():
      assert [branch_of(v) for v in ("consumer", "business", "neither", None, "", "x")] == \
             ["consumer", "other", "other", None, None, None]

  def test_the_builder_derives_a_lone_line_6_answers_branch(...):   # R-47
      answer_petition(s, debt_nature="consumer"); answer_financial_affairs(s, l6_answer="no")
      assert _stored(s)["l6_branch"] == "consumer"
      # with "business": "other"; with debt_nature removed (answer_petition(s, debt_nature=None)):
      with pytest.raises(ValueError, match="answer debt_nature first"):
          answer_financial_affairs(s2, l6_answer="no")
      with pytest.raises(ValueError):
          answer_financial_affairs(s, l6_branch="consumer")
  ```

  - `test_financial_affairs_encryption.py`: `test_financial_affairs_are_ciphertext_at_rest`. Save `{"l9_answer": "yes", "l9_rows": [{"case_title": "Demo v. Demo"}]}` and `l4_current_wages: "1200"`; the raw `answers` and `answered_on` columns (a `connection.cursor()` read of `financial_affairs_answers`) start with `gAAAAA` and contain neither `Demo v. Demo` nor `2026`.
  - `test_session_lock.py`: `"financial_affairs PATCH": lambda s, r: ("patch", _session_url(s), {"financial_affairs": {"l2_answer": "no"}}, 200)`.
- [ ] **Step 2: Run them.** `pt.sh apps/intake/tests/test_financial_affairs_answers.py apps/intake/tests/test_financial_affairs_encryption.py --ds=config.settings.test -q`. Expected: FAIL (`ImportError` on `FinancialAffairsAnswers` / `branch_of`).
- [ ] **Step 3: Implement** `branch_of`, the model (the Interfaces above), `0050` (generate with `zsh $JOB/py.sh manage.py makemigrations intake --name financial_affairs_answers --settings=config.settings.test`, then confirm the file is `0050_financial_affairs_answers.py` with one `CreateModel` depending on `("intake", "0049_shift_current_step_for_plans")`), the serializer pieces, `select_related`, the builder and the `WRITES` row.
  - The empty-body guard: `if validated_data.get("financial_affairs") == {}: del validated_data["financial_affairs"]`, beside the three existing guards, so an echo-only body reopens nothing.
  - The save in `update()` sits after `_save_intention_answers` with the comment that it is last so the prune sees this save's debts (R-14).
- [ ] **Step 4: Run** Step 2's command. Expected: PASS. Then the blast radius:
  - `pt.sh apps/intake/tests/test_session_lock.py apps/intake/tests/test_intention_answers.py apps/intake/tests/test_petition_answers.py apps/intake/tests/test_schedule_i_answers.py apps/intake/tests/test_data_migrations.py apps/intake/tests/test_completion.py --ds=config.settings.test -q` (the `migrate` fixture of `test_data_migrations.py` unapplies the newest migration);
  - `ppt.sh apps/intake/tests/test_session_lock.py` (the `financial_affairs PATCH` row on Postgres);
  - `check`; `makemigrations --check` (Expected: "No changes detected");
  - `ruff check` on every touched Python file, `ruff format --check` on the three new files.
  - See-it-fail, each reverted: drop step 3 of `merge` and show `test_a_picked_debt_id_…[scanned_draft]` fail; move the `update()` save above the debts block and show `[deleted_in_the_same_patch]` fail; make step 4 re-stamp on any change and show `test_the_year_label_never_moves…` fail; drop the pair check and show `test_line_6_answer_and_branch_travel_together` fail.
- [ ] **Step 5: Commit** with `/opt/local/bin/git add` of `backend/apps/intake/migrations/0050_financial_affairs_answers.py`, `backend/apps/intake/models.py`, `backend/apps/intake/serializers.py`, `backend/apps/intake/views.py`, `backend/apps/forms/services/answer_records.py`, `backend/apps/intake/tests/builders.py`, `backend/apps/intake/tests/test_session_lock.py`, `backend/apps/intake/tests/test_financial_affairs_answers.py`, `backend/apps/intake/tests/test_financial_affairs_encryption.py`. Message: `intake: FinancialAffairsAnswers, Form 107 lines 1-12's encrypted record, its year label and line 6 branch`.

### Task 2: the `affairs.` engine plumbing (T-i.2)

Rulings carried: R-5, R-8 (formatting, not words), R-11 (OPEN-22), R-12, R-15, R-48 (CODE-10), P5, CONTRA-16, and the CODE-1 allowance. No `OC` string ships; every word a printer emits is the form's own (the index's `option_text`) or the filer's.

**Files:**
- Modify:
  - `backend/apps/forms/services/answer_records.py`;
  - `backend/apps/forms/services/explain_split.py`;
  - `backend/apps/forms/services/fill_resolver.py:453-458` (`is_money_binding`);
  - `backend/apps/forms/schema.py`: `_affairs_binding_error` after `_schedule_i_binding_error` (`:811-820`), called beside the `schedule_i.` loop (`:786-790`); `_STATEMENT_BINDING` (`:832-835`) and the statement-column E007 message (`:676-678`, P5); the sheet-column E007 message's affairs clause (`:925-929`);
  - `backend/apps/forms/services/derivations.py`: `_AFFAIRS_PREDICATES`, spread into `PREDICATES` (`:1876-1921`) beside `**_SCHEDULE_I_PREDICATES`;
  - `backend/apps/forms/tests/test_checks.py`: the new E007 cases; the pinned sheet-column message at `:1278-1282` (affairs clause only); the two pinned statement-column messages at `:1511-1513` (`test_a_statement_column_binding_another_list_is_reported`) and `:1552-1554` (the `_a_means_statement_column` row);
  - `backend/apps/forms/tests/test_answer_records.py:175-194`;
  - `backend/apps/forms/tests/test_rule_fixes.py:124`.
- Create: `backend/apps/forms/tests/test_affairs_cells.py`.

**Interfaces:**
- Consumes T-i.1's `branch_of` and `FinancialAffairsAnswers.LIST_CELLS` (the test only), `option_text` (`apps/forms/field_index.py:86`), `_petition` (`derivations.py:1006`) and `record_value`.
- Produces, in `apps.forms.services.answer_records` (still a leaf: module-level imports are `re`, `datetime`, `decimal.Decimal` and `from collections.abc import Callable` only, all standard library):
  - `is_plain_amount(value) -> bool`: a `str` that fully matches `[0-9]+(\.[0-9]{1,2})?` (ASCII digits only, the Schedule I rule, `serializers.py:1227`) with `Decimal(value) < 10**10`;
  - `is_last_4(value) -> bool`: a `str` fully matching `[0-9]{4}`;
  - `AFFAIRS_LIST_CELLS: dict[str, tuple[str, ...]]`, a literal copy of D§3's `LIST_CELLS` (pinned equal by a test, so no `apps.intake` import);
  - `AFFAIRS_COMPUTED_CELLS: dict[str, tuple[str, ...]]`: `l2_rows`: `address`; `l6_rows`: `name_and_address`, `dates`, `paid_for`; `l7_rows`, `l8_rows`: `name_and_address`, `dates`; `l9_rows`: `court`, `case_title_1`, `case_title_2`; `l10_rows`: `name_and_address`, `what_happened`; `l11_rows`: `name_and_address`;
  - `AFFAIRS_MONEY_CELLS = frozenset({"paid", "owed", "amount", "value"})`;
  - `PAID_FOR_WORDS: dict[str, str]` in the form's order: `mortgage` "Mortgage", `car` "Car", `credit_card` "Credit card", `loan` "Loan repayment", `vendors` "Suppliers or vendors", `other` "Other";
  - `WHAT_HAPPENED_WORDS: dict[str, str]` in the form's order: `repossessed` "Property was repossessed.", `foreclosed` "Property was foreclosed.", `garnished` "Property was garnished.", `attached` "Property was attached, seized, or levied.";
  - `AFFAIRS_CELLS: dict[str, dict[str, Callable[[dict], str]]]`, list → cell → printer of one row, over every stored and computed cell (D§5.2):
    - a tick cell: `"true"` when the stored value is `"yes"`, else `""` (the slot's choices are `{"true": "/<state>"}`). Heads-up for 4f-ii's T-ii.2: the line 6 tick boxes' on-states are mixed (`check mortgage 1`, `check credit card 1` and `check vendors 1` are `no`; `check car 1`, `check loan 1` and `check other 1` are `yes`; `check10a1`–`check10a4` are all `yes`), so each slot's `<state>` is read from that box's own index row, never assumed `/yes`;
    - `status`: as stored when in `("pending", "on_appeal", "concluded")`, else `""`;
    - an amount cell: `str(Decimal(v).quantize(Decimal("0.01")))` when `is_plain_amount(v)`, else `""`;
    - a date cell: as stored when `is_mm_dd_yyyy(v)`, else `""`;
    - `last_4`: as stored when `is_last_4(v)`, else `""`;
    - every other stored cell (`debt_id` included): `_text(v)`, as stored;
    - `address`: street, street 2, then the city line, joined `", "`, blanks skipped; the city line is `", ".join` of the non-blank city and state, then `" "` and the ZIP when given (`fill_resolver._entry_text`'s order, R-8);
    - `name_and_address`: the name, then `address`'s parts, joined `", "`, blanks skipped;
    - `court`: `court_name`, `court_street`, then the city line of `court_city`, `court_state`, `court_zip`, joined `", "`;
    - `dates`: the printed `date_1`, `date_2`, `date_3` (the date printer's output), non-blank ones joined `", "`;
    - `paid_for`: the `PAID_FOR_WORDS` of the ticked boxes in the form's order joined `", "`, with Other as `f"Other: {other_text.strip()}"` when `other_text` is non-blank, else `"Other"` (R-8);
    - `what_happened`: the `WHAT_HAPPENED_WORDS` of the ticked boxes joined `" "` (each word ends in the form's own period, so a `", "` join would print "repossessed., …"; the join is formatting, R-8);
    - `case_title_1`, `case_title_2`: `split_at_box(case_title, "b_107_0425-form.pdf", "Case title1 9a")`, first and second halves (R-15), imported inside the printer's body, never at module level;
  - `affairs_statement(answers: dict) -> list[dict]`: `[]` unless `answers.get("l12_answer") == "yes"`; otherwise `[{"text": row["text"]} for row in l12_statement if isinstance(row, dict) and isinstance(row.get("text"), str) and row["text"].strip()]`;
  - `record_value`'s `affairs.` branch for a list binding on lines 1–12, checked before the record lookup so a bad binding fails with or without a record (R-48): `l12_statement[].text` reads `[r["text"] for r in affairs_statement(answers)]`; another list and cell read `[AFFAIRS_CELLS[key][attr](row) if isinstance(row, dict) else "" for row in rows]`; a list not in `AFFAIRS_CELLS` (or `l12_statement` with a cell other than `text`) or a cell not in its list's printers raises `_unrecognized(binding)`. Scalar bindings and lines 13–28 keep today's read (CODE-10).
- Produces, in `apps.forms.services.explain_split`: `split_at_box(text: str, template: str, box: str) -> tuple[str, str]`, `split_explain`'s algorithm over a new `_fits(text: str, template: str, box: str) -> bool` (`_fits_explain_1`'s body with its template and box as arguments: same function-local imports, same 6 pt test). `_fits_explain_1(text) -> bool` stays, as `return _fits(text, TEMPLATE, EXPLAIN_1)`, because `test_explain_split.py:12` imports it by name and calls it at `:54`, `:58` and `:63` (that file is not touched). `split_explain(text)` becomes `return split_at_box(text, TEMPLATE, EXPLAIN_1)`, unchanged in behavior.
- Produces `is_money_binding(binding)`: also `True` for `affairs.<list>[].<cell>` with `<cell>` in `AFFAIRS_MONEY_CELLS` (regex `affairs\.(\w+)\[\]\.(\w+)`). The `sofa.creditor_payments[].total_paid` fallback stays until T-i.5.
- Produces `_affairs_binding_error(binding: str) -> str | None` (R-11), importing `FinancialAffairsAnswers` inside its body as the two siblings do. It checks every `affairs.` binding, whatever its line, with no line parse first (`key, is_list, attr = binding.removeprefix("affairs.").partition("[].")`):
  - key not in `FinancialAffairsAnswers.KEYS` → `"not a key FinancialAffairsAnswers asks"`. This covers lines 13–28 until 4g's record, and a key with no parsable line (`affairs.pay6[].x`, `affairs.l29_answer`), which would otherwise raise at resolve;
  - a list key bound as a scalar → `f"{key!r} is a row list, so its binding names a cell"`;
  - a scalar bound as a list → `f"{key!r} is not a row list"`;
  - a cell neither in `LIST_CELLS[key]` nor in `AFFAIRS_COMPUTED_CELLS.get(key, ())` → `f"{attr!r} is not a cell of the {key!r} rows"`.
  It is called over every field binding, sheet column binding and `covers` entry that starts `affairs.` (the set the petition loop builds, `:777-781`).
- Produces `_STATEMENT_BINDING` gaining `|affairs\.l12_statement\[\]\.text`, and its statement-column E007 message (`schema.py:676-678`) widened with it, as P5 says: `f"group {name!r}: statement column {column.label!r} binds {column.binding!r}, not an income.statement[].<attr>, means.line_43[].<attr> or affairs.l12_statement[].text list"`.
- Produces the E007 sheet-column message clause `"affairs.<list>[].<cell> list"` in place of `"affairs.<key>[].<attr> list"` (`schema.py:929`, pin `test_checks.py:1282`). The `sofa.` clause stays until T-i.5.
- Produces `_AFFAIRS_PREDICATES: dict[str, Callable[..., bool]]`, each `(session, answer_cache=None) -> bool`, reading through `record_value`:
  - `affairs_l2_rows`, `affairs_l5_rows`, `affairs_l7_rows`, `affairs_l8_rows`, `affairs_l9_rows`, `affairs_l10_rows`, `affairs_l11_rows`: `record_value(session, f"affairs.l{n}_answer") == "yes"`;
  - `affairs_l6_rows`: `l6_answer == "yes"` and `branch_of(_petition(session, "debt_nature")) is not None` and `l6_branch == branch_of(...)` (R-5).

- [ ] **Step 1: Write the failing tests** in `test_affairs_cells.py` (pure where they can be: `_stub(record, answers)` as `test_answer_records.py:59` builds it, and `AFFAIRS_CELLS[...]` called on row dicts). The file defines its own `session` fixture, a copy of `test_answer_records.py:46-57`'s (a user and an `IntakeSession` on an `ilnd` `District`; no forms conftest fixture is named `session`), and `def _reread(s): return IntakeSession.objects.get(pk=s.pk)`:

  ```python
  def test_the_printed_cell_table_is_the_records():
      assert AFFAIRS_LIST_CELLS == FinancialAffairsAnswers.LIST_CELLS

  @pytest.mark.parametrize("typed,printed", [("1250.5", "1250.50"), ("0", "0.00"), ("", ""),
      ("12.345", ""), ("-5", ""), ("1,200", ""), ("10000000000", ""), ("٣", "")])
  def test_an_affairs_amount_prints_to_the_cent_and_a_malformed_one_prints_blank(typed, printed):
      assert AFFAIRS_CELLS["l6_rows"]["paid"]({"paid": typed}) == printed

  @pytest.mark.parametrize("typed,printed", [("09/02/2026", "09/02/2026"), ("9/2/2026", ""),
      ("13/40/2026", ""), ("02/30/2026", ""), ("", "")])
  def test_an_affairs_date_prints_only_as_mm_dd_yyyy(typed, printed):          # R-12
      assert AFFAIRS_CELLS["l2_rows"]["from"]({"from": typed}) == printed

  def test_last_4_prints_only_four_digits():
      assert [AFFAIRS_CELLS["l11_rows"]["last_4"]({"last_4": v}) for v in ("1234", "123", "12345", "12a4")] \
          == ["1234", "", "", ""]

  def test_a_folded_name_and_address_cell_prints_the_parts_given():
      row = {"name": "Demo Bank", "street": "1 Demo St", "street_2": "Suite 2",
             "city": "Chicago", "state": "IL", "zip": "60601"}
      assert AFFAIRS_CELLS["l6_rows"]["name_and_address"](row) == \
          "Demo Bank, 1 Demo St, Suite 2, Chicago, IL 60601"
      assert AFFAIRS_CELLS["l6_rows"]["name_and_address"]({"name": "Demo Bank", "zip": "60601"}) == \
          "Demo Bank, 60601"
      assert AFFAIRS_CELLS["l2_rows"]["address"]({"street": "1 Demo St", "city": "Joliet"}) == \
          "1 Demo St, Joliet"

  def test_the_payment_words_follow_the_ticks_in_the_forms_order():
      row = {"other": "yes", "car": "yes", "other_text": "storage unit"}
      assert AFFAIRS_CELLS["l6_rows"]["paid_for"](row) == "Car, Other: storage unit"
      assert AFFAIRS_CELLS["l10_rows"]["what_happened"]({"garnished": "yes", "repossessed": "yes"}) == \
          "Property was repossessed. Property was garnished."

  @pytest.mark.parametrize("cell,box", [("mortgage", "check mortgage 1"), ("car", "check car 1"),
      ("credit_card", "check credit card 1"), ("loan", "check loan 1"), ("vendors", "check vendors 1"),
      ("other", "check other 1")])
  def test_the_payment_tick_words_are_the_forms_own(cell, box):
      state = next(w for w in load_index("b_107_0425-form.pdf")[box]).on_state
      assert PAID_FOR_WORDS[cell] == option_text("b_107_0425-form.pdf", box, export_state(state))
  # the same for WHAT_HAPPENED_WORDS over check10a1 (repossessed), check10a2 (foreclosed),
  # check10a3 (garnished), check10a4 (attached), each on-state "/yes"

  def test_a_tick_prints_true_only_for_yes():
      assert [AFFAIRS_CELLS["l6_rows"]["car"]({"car": v}) for v in ("yes", "no", "")] == ["true", "", ""]

  def test_line_12s_statement_reads_only_under_its_yes():
      assert affairs_statement({"l12_answer": "no", "l12_statement": [{"text": "Demo"}]}) == []
      assert affairs_statement({"l12_answer": "yes", "l12_statement": [{"text": "  "}]}) == []
      assert record_value(_stub("financial_affairs", {"l12_answer": "yes",
          "l12_statement": [{"text": "Demo note"}, {"text": ""}]}), "affairs.l12_statement[].text") == ["Demo note"]

  @pytest.mark.parametrize("debt_nature", [None, "consumer", "business", "neither"])
  @pytest.mark.parametrize("branch", ["consumer", "other"])
  @pytest.mark.parametrize("answer", ["yes", "no"])
  def test_line_6_rows_print_only_under_the_branch_they_were_given(debt_nature, branch, answer, session):  # R-5
      answer_petition(session, debt_nature=debt_nature)
      answer_financial_affairs(session, l6_answer=answer, l6_branch=branch)
      expected = answer == "yes" and debt_nature is not None and branch_of(debt_nature) == branch
      assert PREDICATES["affairs_l6_rows"](_reread(session)) is expected

  def test_a_case_title_too_long_for_its_first_box_continues_in_the_second():   # R-15
      # Case title1 9a is one line, 111.4 pt wide (index rect [101.5, 193.9, 212.9, 208.5]):
      # about 37 letters at 6 pt, so this 80-letter title overflows it.
      title = "Demo Holdings Limited Partnership v. Demonstration Property Management Company"
      first, second = AFFAIRS_CELLS["l9_rows"]["case_title_1"]({"case_title": title}), \
                      AFFAIRS_CELLS["l9_rows"]["case_title_2"]({"case_title": title})
      assert first and second and f"{first} {second}" == title     # split at a word
      assert AFFAIRS_CELLS["l9_rows"]["case_title_1"]({"case_title": "Demo v. Demo"}) == "Demo v. Demo"

  def test_an_unknown_affairs_list_or_cell_on_lines_1_to_12_raises():          # R-48
      for binding in ("affairs.l1_rows[].street", "affairs.l6_rows[].nmae",
                      "affairs.l12_statement[].words"):
          with pytest.raises(ValueError, match="unrecognized binding"):
              record_value(SimpleNamespace(), binding)          # no record: still refused

  def test_an_affairs_money_cell_can_be_totalled():
      assert is_money_binding("affairs.l6_rows[].paid") and is_money_binding("affairs.l10_rows[].value")
      assert not is_money_binding("affairs.l6_rows[].name")

  def test_split_explain_still_splits_form_108s_words_as_before():
      assert split_explain("My brother Mateo, the co-owner, keeps paying the loan.") == \
             split_at_box("My brother Mateo, the co-owner, keeps paying the loan.", "form_b108.pdf", "Explain1 1a")
  ```

  - `test_answer_records.py:175-194`: `test_a_form_107_line_reads_the_record_that_asks_it` keeps its 12/13 boundary and is re-parametrized as `(line, record, other, rows_key, cell, extra)`: `(2, "financial_affairs", "property_affairs", "l2_rows", "street", {})`, `(12, "financial_affairs", "property_affairs", "l12_statement", "text", {"l12_answer": "yes"})`, `(13, "property_affairs", "financial_affairs", "l13_rows", "street", {})`, `(28, "property_affairs", "financial_affairs", "l28_rows", "street", {})`. The scalar `affairs.l{line}_answer` assertions stay; the row assertion stores `{**extra, rows_key: [{cell: "1 Demo St"}]}` and reads `["1 Demo St"]`.
  - `test_checks.py`, beside `test_a_schedule_i_binding_naming_no_key_is_refused` (`:1060`), on `schedule_d_with_totals` with its name slots rebound through `_edit`. Every rebind in these new tests matches a slot by `f["repeat"] == "d_part_1"` and its `label` (`"Creditor's name"` for a name slot, `"Amount of claim"` for an amount slot, conftest's `_NAME` and `_AMOUNT`), never by its `sofa.` binding string, so T-i.3's re-point of the fixture leaves them binding and no `sofa.` string is added for Task 3's guard to find. Each rebind callback ends with `assert any(f["binding"] == <its target> for f in d["fields"])`:

  ```python
  @pytest.mark.parametrize("binding,error", [
      ("affairs.l6_nmae", "'affairs.l6_nmae': not a key FinancialAffairsAnswers asks"),
      ("affairs.l6_rows", "'affairs.l6_rows': 'l6_rows' is a row list, so its binding names a cell"),
      ("affairs.l2_answer[].street", "'affairs.l2_answer[].street': 'l2_answer' is not a row list"),
      ("affairs.l6_rows[].nmae", "'affairs.l6_rows[].nmae': 'nmae' is not a cell of the 'l6_rows' rows"),
      ("affairs.l13_answer", "'affairs.l13_answer': not a key FinancialAffairsAnswers asks"),
  ])
  def test_an_affairs_binding_naming_no_stored_or_computed_cell_is_a_startup_error(...):
      assert ("forms.E007", f"schedule_d: {error}") in _errors("schedule_d")

  def test_a_misspelt_cell_in_a_covers_list_is_refused_and_a_computed_one_passes(
      schedule_a_b_with_sheet):
      # On schedule_a_b_with_sheet (schedule_d_with_totals has no sheet), through
      # _a_covering_column(covers, binding="affairs.l6_rows[].name_and_address"): with covers
      # ["affairs.l6_rows[].name", "affairs.l6_rows[].stret"] the errors hold
      # ("forms.E007", "schedule_a_b: 'affairs.l6_rows[].stret': 'stret' is not a cell of the "
      #  "'l6_rows' rows"); with covers ["affairs.l6_rows[].name", "affairs.l6_rows[].street"]
      # no error contains "is not a cell of the" or "not a key FinancialAffairsAnswers asks".
      # Filter on _affairs_binding_error's own words only: the slots don't bind affairs. rows
      # here, so the group's "covers ..., which no slot of the group binds" and "isn't the one
      # list its slots bind" errors also quote 'affairs. and are not this test's business.

  def test_an_affairs_amount_column_takes_a_total_and_a_name_column_does_not(
      schedule_d_with_totals):
      # name slots (by label) rebound to affairs.l6_rows[].name, amount slots to
      # affairs.l6_rows[].paid, d["groups"]["d_part_1"]["totals"]["column"] =
      # "affairs.l6_rows[].paid": no error mentions "totals"; with the column
      # "affairs.l6_rows[].name": the existing "'affairs.l6_rows[].name', which holds no
      # amount" error (the :922-928 shape)

  def test_a_statement_column_may_bind_line_12s_statement(schema_copy):     # P5
      # i_line_8a's first column rebound to "affairs.l12_statement[].text" (the :1503 test's
      # edit): no E007 contains "'affairs.l12_statement[].text', not an" (the widened refusal
      # itself; other sheet rules may still speak of the column, and are not this test's)
  ```

  - The two statement-column pins (`:1511-1513`, `:1552-1554`) take the widened message word for word: `"…binds 'household.dependents[].age', not an income.statement[].<attr>, means.line_43[].<attr> or affairs.l12_statement[].text list"` and the same tail after `'means.line_43[].happened'`.

  - `test_rule_fixes.py:124`: `targets = {"step": _wizard_steps() | set(NEW_STEP_KEYS), "page": _pages()}`, importing `NEW_STEP_KEYS` from `apps.forms.services.answer_records` (the 4e Task 4 precedent, `2026-11-24-forms-step4e.md:548`). Nothing in 4f-i yields `last_few_years_1`; from T-ii.2 on every affairs slot does, and 4f-ii's T-ii.6 re-tightens it by changing `NEW_STEP_KEYS` alone (CODE-1).
- [ ] **Step 2: Run them.** `pt.sh apps/forms/tests/test_affairs_cells.py apps/forms/tests/test_answer_records.py apps/forms/tests/test_checks.py apps/forms/tests/test_rule_fixes.py --ds=config.settings.test -q`. Expected: FAIL (`ImportError` on `AFFAIRS_CELLS`; the E007 cases find no error).
- [ ] **Step 3: Implement** the Interfaces above. The bodies follow from the signatures and tests; no body is written out here.
- [ ] **Step 4: Run** Step 2's command. Expected: PASS. Then `pt.sh apps/forms/tests/test_explain_split.py apps/forms/tests/test_form_108_prints.py apps/forms/tests/test_claims_bindings.py apps/forms/tests/test_derivations.py apps/forms/tests/test_fill_resolver.py --ds=config.settings.test -q`, `check`, `ruff check` on the touched files, `ruff format --check` on `test_affairs_cells.py`.
  - See-it-fail, each reverted: drop `affairs.` from `is_money_binding` and show `test_an_affairs_amount_column_takes_a_total…` fail; skip the `_affairs_binding_error` call and show `[affairs.l6_nmae]` pass where it should fail; make the amount printer return the stored text and show `[12.345]` fail.
- [ ] **Step 5: Commit** with `/opt/local/bin/git add` of `backend/apps/forms/services/answer_records.py`, `backend/apps/forms/services/explain_split.py`, `backend/apps/forms/services/fill_resolver.py`, `backend/apps/forms/schema.py`, `backend/apps/forms/services/derivations.py`, `backend/apps/forms/tests/test_affairs_cells.py`, `backend/apps/forms/tests/test_answer_records.py`, `backend/apps/forms/tests/test_checks.py`, `backend/apps/forms/tests/test_rule_fixes.py`. Message: `forms: the affairs. cells, money and dates as printed, the statement reader and the startup key check`.

### Task 3: the engine fixtures re-pointed to `affairs.l6_rows[]` (T-i.3, H3, H4)

Rulings carried: S:666, S:801 rule 3 (fixtures before the SOFA code goes), H3, H4, CODE-6. No `OC` string ships. **Invariant:** no expected printed value changes. `paid` `"100.00"` prints exactly as `total_paid` `Decimal("100.00")` did. Only the fixture calls, the bindings, and the fixes (`(None, "/sofa")` → `("last_few_years_1", None)`) change.

**Files:**
- Modify:
  - `backend/apps/forms/tests/conftest.py`: the imports (`:21-28`, `SOFACreditorPayment` and `SOFAReport` out; `answer_petition`, `answer_financial_affairs` in), `_NAME = ("Creditor's name", "name")` and `_AMOUNT = ("Amount of claim", "paid")` (`:33-35`), `_MAKE = ("Make", "name")` and `_VALUE = ("Current value of the portion you own", "paid")` (`:71-72`, with their comment at `:69-70`), every `sofa.creditor_payments[]` binding the synthetic schemas build (`:69-104`, `:146-180`, `:196`, `:264`, `:279`, `:312`) → `affairs.l6_rows[]`, and the fixture `creditor_payments` (`:463-482`) → `affairs_rows`;
  - the fixture's users. **One rule for every ORM use of a returned row** (the fixture now returns dicts): a mutation (an attribute set then `.save()`, a `.delete()`, `.order_by(…).last().delete()`) becomes an edit of the returned dict list, then `answer_financial_affairs(session, l6_rows=rows)` with the edited list (a deleted row k is `rows[:k] + rows[k + 1:]`); a read of `.creditor_name` becomes `["name"]` and of `.total_paid` becomes `["paid"]`, a string, so a wrapping `str(...)` is dropped and a `Decimal` sum takes `Decimal(r["paid"])`. Examples: `test_continuation_copies.py:214-215`, `test_attached_sheets.py:264-265`, `:405`, `:411`, `:449-450`, `:455`, `:512-513`, `test_group_copies_and_totals.py:295-297` (`first.total_paid = Decimal("0.10")` → `rows[0]["paid"] = "0.10"`), `test_download_action.py:260` (`rows[5].delete()` → `answer_financial_affairs(session, l6_rows=rows[:5] + rows[6:])`), `:520-521`, `:565-566`:
    - `test_group_copies_and_totals.py:17`, `:48-397` (`:232` and `:394-397`: `conditional_on="has_creditor_payments"` → `"affairs_l6_rows"`; `SOFAReport.objects.create(…, has_creditor_payments=False)` → `answer_financial_affairs(session, l6_answer="no")` after `answer_petition(session, debt_nature="consumer")`);
    - `test_continuation_copies.py:66-226` (`:226` → `("last_few_years_1", None)`);
    - `test_download_action.py:236-566`;
    - `test_attached_sheets.py:86-666` (`:246`'s `every_row_total` sums `Decimal(r["paid"])` over `session.financial_affairs.get_answers()["l6_rows"]`; `:277` and `:418` → `("last_few_years_1", None)`; `:455`'s delete becomes `answer_financial_affairs(session, l6_rows=rows[:-1])`);
    - `test_number_boxes.py:125-146`, `:220-240`;
    - `test_checks.py`: `:280`, `:749`, `:780`, `:826`, `:855-859`, `:922-928`, `:1114`, `:1156`, `:1179`, `:1208`, `:1291`, `:1317`, `:1330`, `:1448`, `:1522`; every rebind matcher `if f["binding"] == "sofa.creditor_payments[].creditor_name"` at `:936`, `:946`, `:964`, `:976`, `:996` → `"affairs.l6_rows[].name"`; `dates_of_payments` → `date_1`, `total_paid` → `paid`, `creditor_name` → `name`; `:497`'s `conditional_on: "has_creditor_payments"` → `"affairs_l6_rows"` (CODE-6); `:1655`'s map → `{"name": "make", "paid": "value", "date_1": "community"}`; `:1743` (the parametrize row `("assets.line_3", "sofa.creditor_payments[].creditor_name")` of `test_a_sworn_sheet_cannot_print_another_rows_words_beside_a_row`) → `("assets.line_3", "affairs.l6_rows[].name")`, whose expected error is unchanged in shape (the f-string quotes the row's own binding: `"…covers slots but binds 'affairs.l6_rows[].name', which isn't the one list its slots bind"`; `affairs.l6_rows[].name` is a stored cell, so `_affairs_binding_error` adds nothing, and the row stays a `_LIST_BINDING` match after T-i.5); `:1848` (`test_a_slot_may_bind_an_asset_list`) → the `replace`'s source becomes `"affairs.l6_rows[].name"`. The pinned E007 message at `:1278` keeps its `sofa.` clause until T-i.5;
    - `test_printed_page.py:969` (`SheetColumn("Make", "affairs.l6_rows[].name", 300.0)`);
    - `test_fill_resolver.py:25-26`, `:55-67`, `:69-76`, `:178-182`, `:253-284`, `:309-331`, `:343-362`, `:400`, `:437`, `:522`, `:766-790`, each pinned:
      - `:55-67`: the two list cases store their rows with `answer_financial_affairs(session, l6_answer="yes", l6_branch="consumer", l6_rows=[{"name": "Acme", "paid": "100.00"}, {"name": "Beta", "paid": "200.00"}])` and read `resolve_binding("affairs.l6_rows[].name", session)` (`["Acme", "Beta"]`; with no record, `[]`);
      - `:69-76` (the scalar `sofa.has_business` cases): `test_resolve_scalar_binding_returns_str` reads `resolve_binding("affairs.l6_answer", s) == "yes"` after `answer_financial_affairs(s, l6_answer="yes", l6_branch="consumer")`; `test_resolve_scalar_binding_no_report_returns_empty` reads `resolve_binding("affairs.l6_answer", s) == ""` with no record;
      - `:178-182`: `conditional_on="affairs_l6_rows"` with no record, its comment `# no line 6 answer → affairs_l6_rows False → field skipped` (not `has_business`, which T-i.5 deletes, after which an unknown predicate would make the test pass vacuously);
      - `:522`: the `binding_fix` row → `("affairs.l6_rows[].name", {"step": "last_few_years_1"})` (`binding_fix` gives that today through `record_step`; T-i.4's `sofa.` cut would break the old row);
      - `:766-790`: the two tests' `creditor_payments` fixture argument and calls → `affairs_rows` (`affairs_rows(session, 14)`, `affairs_rows(session, 8)`);
    - `test_claims_bindings.py:284-286` (`is_money_binding("affairs.l6_rows[].paid")` true, `("affairs.l6_rows[].name")` false; the `sofa.` assertion goes with the fallback in T-i.5, so here it is only joined by the affairs pair).
  - `keep! backend/apps/forms/tests/test_rule_fixes.py` in this task: its SOFA lines (`:5`, `:126`, `:140`, `:264`, `:276`) go with the routes in T-i.4 (H9). Re-pointing `:140` here would make the dashboard-links test fail all through 4f-i.

**Interfaces:**
- Consumes T-i.1's record and builder, T-i.2's cells, money cells and predicates.
- Produces the fixture `affairs_rows(session, count, names=None) -> list[dict]`: `answer_petition(session, debt_nature="consumer")`, then `answer_financial_affairs(session, l6_answer="yes", l6_branch="consumer", l6_rows=rows)` with `rows = [{"name": names[n - 1] if n <= len(names) else f"Creditor {n}", "paid": f"{n}00.00"} for n in range(1, count + 1)]` (`names` defaulting to `_CREDITORS`); it returns `rows`. No product code.

- [ ] **Step 1: Write the new failing test** (Review Focus 4) in `test_group_copies_and_totals.py`, beside the totals cases (`:225-236`):

  ```python
  def test_a_malformed_paid_amount_prints_blank_and_adds_nothing_to_the_total(
      schedule_d_with_totals, generated_form_factory, affairs_rows):
      totals = ["undefined_9", "undefined_23", "undefined_24"]
      session = generated_form_factory().session
      rows = affairs_rows(session, 2)
      answer_financial_affairs(session, l6_rows=[rows[0], {**rows[1], "paid": "12.345"}])
      _, _, drawn = _drawn("schedule_d", session)
      assert _printed(drawn, ["undefined_5"]) == {(1, None, "undefined_5"): ""}  # row 2's amount
      one_row = generated_form_factory().session
      affairs_rows(one_row, 1)
      _, _, one_row_drawn = _drawn("schedule_d", one_row)
      # The malformed row adds nothing: every total prints what one valid row's tree prints.
      assert _printed(drawn, totals) == _printed(one_row_drawn, totals)
      assert _printed(drawn, ["undefined_9"]) == {(1, None, "undefined_9"): "100.00"}
  ```

  It carries `@pytest.mark.slow`, as the totals tests beside it do.
- [ ] **Step 2: Run it.** `pt.sh apps/forms/tests/test_group_copies_and_totals.py --ds=config.settings.test -q -k malformed`. Expected: FAIL (`fixture 'affairs_rows' not found`).
- [ ] **Step 3: Re-point** `conftest.py` and every user listed above, file by file, with no expected printed value changed.
- [ ] **Step 4: Run** `pt.sh apps/forms/tests/test_group_copies_and_totals.py apps/forms/tests/test_continuation_copies.py apps/forms/tests/test_download_action.py apps/forms/tests/test_attached_sheets.py apps/forms/tests/test_number_boxes.py apps/forms/tests/test_checks.py apps/forms/tests/test_printed_page.py apps/forms/tests/test_fill_resolver.py apps/forms/tests/test_claims_bindings.py --ds=config.settings.test -q`. Expected: PASS, with the same number of tests as before the change plus one (report both counts through `printf`).
  - The rebinds still bind: in `test_an_answer_record_binding_passes_the_namespace_check` (`:953-968`) and each sibling at `:936`, `:946`, `:976`, `:996`, add `assert any(f["binding"] == binding for f in d["fields"])` (or the rebind's target) inside the rebind callback after the loop, so a matcher that finds nothing fails instead of passing vacuously. See-it-fail: leave one matcher on `sofa.creditor_payments[].creditor_name` and show its test fail; revert.
  - Then `rg -n "sofa|SOFA|creditor_payments|total_paid|dates_of_payments" backend/apps/forms/tests`. Expected hits only: the furniture "sofa" (`test_oracle_tier3.py:282`, `:318`; the capitalized "Sofa" at `test_printed_page.py:1418`, `:1424`, `:1523` doesn't match this case-sensitive pattern), `test_form_107_schema.py` (T-i.5 trims it), `test_rule_fixes.py` (T-i.4 trims it), `test_api_readback.py:291-295` (T-i.5), `test_claims_bindings.py`'s one `sofa.` assertion (T-i.5), `test_checks.py:1278`'s message clause (T-i.5) and `test_derivations.py:106-115` (T-i.5 and T-ii.2). Any other hit stops the task.
  - `ruff check` on every touched file.
- [ ] **Step 5: Commit** with `/opt/local/bin/git add` of each file listed under Files (all under `backend/apps/forms/tests/`). Message: `forms tests: the engine fixtures print affairs.l6_rows, not SOFA rows`.

### Task 4: `/sofa` gone; the routes, the links and the E2E SOFA pieces (T-i.4, H9, H10)

Rulings carried: H9, H10, P12, F6, R-31, R-38, R-40 (OPEN-16), S:662, S:683, CODE-1, CODE-7, CODE-14. The one `OC` row acted on (OC §6, a removal): `PAGE_LINK_LABELS['/sofa']`, `'Go to Statement of Financial Affairs'`, with the old SOFA page and all its words; nothing carried over and no notice. No new string ships.

**Order note.** This task comes before the backend cut because `SOFAStep.tsx:298-307` shows no "Skip for now" once its load fails, so cutting the API first would leave every journey red until this commit (CODE-7). The backend keeps serving the sofa-report API through this commit; nothing calls it any more.

**Files:**
- Delete (`/opt/local/bin/git rm`): `frontend/src/pages/SOFAStep.tsx`, `frontend/src/pages/__tests__/SOFAStep.test.tsx` (R-31: its 18 cases' intent is ported into 4f-ii's T-ii.5), `frontend/e2e/pages/sofa.page.ts`, `frontend/e2e/journeys/sofa-journey.spec.ts`.
- Modify:
  - `frontend/src/App.tsx:24`, `:86` (the import and the route; no redirect, S:683);
  - `frontend/src/api/client.ts:43` (the `SOFAReport` type import, CODE-14), `:792-814` (`sofaReportAPI`, from its `// SOFA Report API` banner) and `:845` (`sofaReport: sofaReportAPI,`);
  - `frontend/src/types/api.ts:1490-1515` (`SOFAPriorIncome`, `SOFACreditorPayment`, `SOFAReport`). `keep!` `:61` `sofa_report?`, which `DynamicFormWizard`'s dead read keeps until 4i (R-3, CR §1.3);
  - `frontend/src/test/mocks/handlers.ts:349-373` (the two sofa-report handlers);
  - `frontend/src/styles/global.css`: lines `:1991-2108`, from the "SOFA Page" header comment (`:1991-1993`) through the closing brace of `.sofa-actions` (which starts at `:2100` and closes at `:2107`) and the blank line after it, so the `/* Site footer` comment (`:2109`) follows `:1990`'s blank line. `.remove-row-button` (`:2087-2097`) goes too: only `SOFAStep.tsx` uses it. No other file uses a `.sofa-` class once `sofa.page.ts` is gone;
  - `frontend/src/utils/parseAmount.ts:57` (the SOFA bullet of the comment);
  - `frontend/src/pages/MeansTestPage.tsx:277` (comment: "the forms dashboard"), `:336`, `:398`, `:454` (`navigate('/forms', …)`, keeping each call's options);
  - `frontend/src/pages/FilingFeePage.tsx:81`, `:155-156` (comments: the exemptions page, then the 122A-2 page or the forms dashboard);
  - `frontend/src/pages/FormDashboard.tsx:96` (the `/sofa` row of `PAGE_LINK_LABELS`);
  - `backend/apps/forms/services/fill_resolver.py:634-635` (the `sofa.` branch of `binding_fix`; a `sofa.` binding now falls through to `{}`);
  - tests:
    - `frontend/src/pages/__tests__/meansTestPageHelpers.tsx:22` (`export const DASHBOARD = 'Forms dashboard';` in place of `SOFA`) and `:101` (`<Route path="/forms" element={<div>{DASHBOARD}</div>} />`);
    - `frontend/src/pages/__tests__/MeansTestPage.test.tsx`: every `SOFA` → `DASHBOARD` (21 uses); the titles at `:196` → `"a filer the form doesn't apply to goes on to the forms dashboard, with no heading first"`, `:292` → `'with no gap and the same result, Continue goes to the forms dashboard'`, `:397` → `'a reply that says the form no longer applies moves to the forms dashboard without showing a heading'`, `:434` → `"a reply that can't say whether the form applies shows why, and Continue goes to the forms dashboard"`;
    - `frontend/src/pages/__tests__/ExemptionsPage.test.tsx:127` and `frontend/src/pages/__tests__/IntakeWizard.test.tsx:132` (the dead `/sofa` route lines). `IntakeWizard.test.tsx:1363` (`?step=sofa`, an unknown step key) stays;
    - `frontend/src/pages/__tests__/FormDashboard.test.tsx:1145-1173`: the comment loses "a SOFA list"; the `schedule_d` entry's `page` becomes `'/exemptions'` and its expected link `['Go to The property you claim as exempt', '/exemptions']`. (D§2 T-i.4 says `/filing-fee`; that page is already the list's first entry, so the case would assert a duplicate link that proves nothing. `/exemptions` is a `PAGE_LINK_LABELS` page the case doesn't yet name. Recorded under Corrections.)
    - `backend/apps/forms/tests/test_rule_fixes.py`: the docstring at `:5` and the comment at `:126` lose SOFA; `:140` (`fix_for(_field("asked", binding="sofa.creditor_payments[].creditor_name"))`) is **deleted**, not re-pointed; the `/sofa` row at `:264` and its id `"sofa"` at `:276` are deleted; a row `(_field("asked", binding="affairs.l6_rows[].name"), {"step": "last_few_years_1"})` is added after the `affairs.l13_answer` row (`:269`) with id `"affairs_lines_1_12"` (D§2 says id `"affairs"`, which `:269`'s row already holds; pytest would rename both).
  - E2E:
    - `frontend/e2e/pages/exemptions.page.ts:3` (comment) and `:20` (`next = '**/forms'`);
    - `frontend/e2e/pages/means-test.page.ts:3` (comment: continues to `/forms`);
    - `frontend/e2e/pages/wizard.page.ts:46-47` (comment: the filing-fee page continues to the exemptions page);
    - the seven journeys `andres-gig-driver.spec.ts`, `deshawn-assets.spec.ts`, `eviction-statement-journey.spec.ts`, `james-borderline.spec.ts`, `maria-happy-path.spec.ts`, `priya-ineligible.spec.ts`, `sarah-simplest.spec.ts`: the `import { SOFAPage } from '../pages/sofa.page';` line, the `const sofa = new SOFAPage(page);` line, and the `await sofa.waitForLoad(); await sofa.skipForNow();` pair become one `await page.waitForURL('**/forms');` (Priya's after `meansTest.continue()`, `priya-ineligible.spec.ts:119`). In Andrés's journey the two calls are not adjacent: `await sofa.waitForLoad();` (`:104`) becomes the `waitForURL`, the `meansTitleSeen` check after it (`:105-106`) stays, and `await sofa.skipForNow();` (`:107`) goes. The comments that cite "skip SOFA" or "covered by sofa-journey.spec.ts" (andres `:84-86`, deshawn `:86-87`, james `:79-80`, maria `:88-89`, sarah `:93-94`) say instead that the forms dashboard follows the 122A-2 page (or that page's replacing itself, below the median);
    - `maria-happy-path.spec.ts` gains, after `generateAllForms(16)` (`:94`), Form 107's download, moved from `sofa-journey.spec.ts:128-148` unchanged: the `.form-card` filtered by `/form 107/i` is visible, its Download button's `download` event gives a `*.pdf` file whose first five bytes are `%PDF-` (P12, R-40). The journeys' `generateAllForms` counts are unchanged (andres 16, deshawn 16, eviction 17, james 16, maria 16, priya 17, sarah 16).

**Interfaces:** consumes nothing new; produces none.

- [ ] **Step 1: Write the failing tests.**
  - `FormDashboard.test.tsx`, a new `it`:

    ```tsx
    import dashboardSource from '../FormDashboard.tsx?raw';
    import appSource from '../../App.tsx?raw';

    it('no refusal links to a page the app no longer serves', () => {
      const block = dashboardSource.slice(dashboardSource.indexOf('const PAGE_LINK_LABELS'));
      const labels = block.slice(0, block.indexOf('};'));
      const pages = [...labels.matchAll(/'(\/[^']*)':/g)].map((m) => m[1]);
      expect(pages.length).toBeGreaterThan(0);
      for (const page of pages) expect(appSource).toContain(`path="${page}"`);
    });
    ```

  - `test_rule_fixes.py`, a new test (S:662, landed early), with `binding_fix` added to the file's `from apps.forms.services.fill_resolver import fix_for` line (`:20`):

    ```python
    def test_no_fix_names_a_route_the_app_no_longer_serves():
        assert binding_fix("sofa.creditor_payments[].creditor_name") == {}
        assert {"page": "/sofa"} not in RULE_FIXES.values()
    ```

  - The renamed `MeansTestPage.test.tsx` cases now find `DASHBOARD` on `/forms`.
- [ ] **Step 2: Run them.** `fe.sh npx vitest run --maxWorkers=2 src/pages/__tests__/FormDashboard.test.tsx src/pages/__tests__/MeansTestPage.test.tsx` and `pt.sh apps/forms/tests/test_rule_fixes.py --ds=config.settings.test -q`. Expected: FAIL. The MeansTestPage cases don't find `DASHBOARD`, and `test_no_fix_names_a_route_the_app_no_longer_serves` gets `{"page": "/sofa"}`. The new dashboard guard passes now, since `/sofa` is still both a label and a route; its see-it-fail is in Step 4.
- [ ] **Step 3: Implement** every edit and deletion in Files, in one tree.
- [ ] **Step 4: Run.**
  - `fe.sh npx vitest run --maxWorkers=2 src/pages/__tests__/FormDashboard.test.tsx src/pages/__tests__/MeansTestPage.test.tsx src/pages/__tests__/ExemptionsPage.test.tsx src/pages/__tests__/IntakeWizard.test.tsx src/pages/__tests__/FilingFeePage.test.tsx`. Expected: PASS.
  - `pt.sh apps/forms/tests/test_rule_fixes.py apps/forms/tests/test_fill_resolver.py --ds=config.settings.test -q`. Expected: PASS.
  - tsc; `fe.sh npx eslint` and prettier `--check` on every touched frontend and E2E file.
  - See-it-fail: put `'/sofa': 'Go to Statement of Financial Affairs'` back in `PAGE_LINK_LABELS` and show `no refusal links to a page the app no longer serves` fail; revert.
  - `zsh $JOB/e2e-one.sh all 4fi-T4`. Expected: all 8 specs green (the seven that lost their SOFA pair, plus `scanned-bill-journey`), Maria's Form 107 download a PDF. DIG-523 is reported, not fixed.
- [ ] **Step 5: Commit** with `/opt/local/bin/git rm` of the four deleted files and `/opt/local/bin/git add` of every modified path above. Message: `frontend, e2e: /sofa removed; the 122A-2 page continues to the dashboard; Maria downloads Form 107`.

### Task 5: the SOFA cut, backend (T-i.5, H5)

Rulings carried: P1, F6, R-3, CONTRA-6, CONTRA-7, CR §1.2, COV-24. No `OC` string ships. The three SOFA classes (`models.py:1662-1705`) and their migrations are `keep!` (P1). `_has_creditor_payments` and `_has_prior_income` are `keep!` until 4f-ii's T-ii.2 (H6): 28 `answer:` bindings on Form 107 name them, and they print blank.

**Files:**
- Delete (`/opt/local/bin/git rm`): `backend/apps/intake/tests/test_sofa_models.py`, `backend/apps/intake/tests/test_sofa_views.py`.
- Modify:
  - `backend/apps/intake/views.py`: `bulk_answers` (`:431-502`) loses the unconditional `SOFAReport.objects.get_or_create` (`:440-441`), `models_to_save` and `cached_collections` (`:443-444`) and the `sofa.` branch with its save loop (`:464-500`), keeping the `answer:` upsert and its reply; `SOFAReportViewSet` (`:950-984`) goes; the imports at `:49` and `:73`;
  - `backend/apps/intake/urls.py:8`, `:15` (the import and the `sofa-report` route);
  - `backend/apps/intake/serializers.py`: the imports `:70-72`; the three SOFA serializers `:2078-2144`; `BulkAnswerItemSerializer.validate`'s `sofa.` half (`:2161-2210`), so `answer:` is the one prefix, refused otherwise with `{"binding": "Invalid binding prefix. Must start with 'answer:'."}`; `_coerce_field_value` (`:2152`) and the `from django.core.exceptions import FieldDoesNotExist` import (`:13`) go, since only the SOFA branch uses them; `import re` (`:9`) stays (`:1190`, `:1227`, `:1253`, `:1789` use it);
  - `backend/apps/forms/services/fill_resolver.py`: the docstring lines `:471-472`, the `sofa.` branch of `resolve_binding` (`:499-510`), the SOFA prefetch (`:1006-1010`), and `is_money_binding`'s fallback (`:458` → `return False`);
  - `backend/apps/forms/schema.py`: `:89` (the `SheetColumn.binding` comment), `:113` (the totals comment), `"sofa.",` in `_BINDING_NAMESPACES` (`:280`), `sofa\.\w+|` in `_LIST_BINDING` (`:837`), and `"not a sofa.<collection>[].<attr>, "` → `"not a "` in the E007 message (`:925`);
  - `backend/apps/forms/services/derivations.py`: `_has_business` (`:1848-1850`) and its `PREDICATES` entry (`:1877`);
  - `backend/apps/intake/models.py:62-66`: `reopen()`'s docstring reads "Form answers and the filing fee, exemptions and means-test pages are not intake data…" (SOFA removed). The SOFA classes are untouched;
  - `backend/apps/intake/management/commands/seed_demo_data.py`: the imports `:44-46`, Maria's `"sofa"` block `:447-475`, and the writer `:1829-1838`;
  - tests:
    - `backend/apps/intake/tests/test_bulk_answers.py`: `:38` (the `sofa.` answer in the mixed payload goes), `:49` (`assert data["updated"] == 1`: the count no longer includes the `sofa.` row; `created` stays 1), `:56-61` (the SOFA assertion), `test_bulk_upsert_handles_sofa_bindings` (`:63-~100`) goes, the invalid-answer parametrize (`:133-139`) becomes `("invalid:q1", "new")` and `("sofa.has_prior_income", "True")`, ids `["invalid_prefix", "sofa_prefix_refused"]`;
    - `backend/apps/intake/tests/test_completion.py:1149-1174`: rewritten as `test_form_answers_leave_a_completed_intake_complete` (the `answer:form_103b.…` POST alone, then status still `completed`);
    - `backend/apps/forms/tests/test_api_readback.py:291-295` (the `if "sofa" in data` PATCH goes; 4f-ii adds the `financial_affairs` PATCH);
    - `backend/apps/forms/tests/test_derivations.py:106-108` (the `has_business` case goes; `:110-115` stay until T-ii.2);
    - `backend/apps/forms/tests/test_claims_bindings.py:284-286` (the `sofa.` `is_money_binding` assertions go; T-i.3's affairs pair stays);
    - `backend/apps/forms/tests/test_checks.py:1278` (the pinned message loses `"not a sofa.<collection>[].<attr>, "`, now `"not a household.dependents[].<attr>, "`);
    - `backend/apps/forms/tests/test_form_107_schema.py`: the header docstring `:8-9`, `_sofa` and the SOFA cases `:60-119` go, replaced by the guard below; the import at `:26` becomes `from apps.intake.models import DebtorInfo, IntakeSession, SOFACreditorPayment, SOFAPriorIncome, SOFAReport` (the guard needs all three); its header-name and `check6` cases stay (T-ii.2 rewrites the file).
  - No change: `backend/apps/intake/tests/test_seed_demo_data.py` (its one "sofa" is the furniture at `:588`); Step 4 still runs it.

**Interfaces:** consumes nothing new; produces none. After this task `answer:` is the only prefix `answers/bulk` takes, and nothing writes or reads `SOFAReport`, `SOFAPriorIncome` or `SOFACreditorPayment` except the two H6 predicates.

- [ ] **Step 1: Write the failing tests.**

  ```python
  # test_bulk_answers.py
  def test_saving_form_answers_writes_no_sofa_report(auth_client_with_session):   # H5, CR §1.2
      client, session = auth_client_with_session
      r = client.post(f"/api/intake/sessions/{session.pk}/answers/bulk/", {"answers": [
          {"form_type": "form_103b", "binding": "answer:form_103b.paid_anyone_for_services",
           "value": "Yes"}]}, format="json")
      assert r.status_code == 200
      assert SOFAReport.objects.count() == 0

  # test_completion.py, after the rewritten :1149 test
  def test_the_sofa_report_route_is_gone(filer, completed):
      client, _ = filer
      assert client.get(f"/api/intake/sofa-report/{completed.pk}/").status_code == 404

  def test_a_session_with_an_old_sofa_report_still_deletes(filer, completed):     # P1
      client, user = filer
      report = SOFAReport.objects.create(session=completed, has_creditor_payments=True)
      SOFACreditorPayment.objects.create(report=report, creditor_name="Demo Bank",
                                         total_paid=Decimal("100.00"))
      user.delete()
      assert not SOFAReport.objects.exists() and not IntakeSession.objects.filter(pk=completed.pk).exists()

  # test_form_107_schema.py (Review Focus 5)
  def test_an_old_sofa_report_changes_nothing_form_107_prints(session):
      before = build_field_values("form_107", session)
      report = SOFAReport.objects.create(session=session, has_prior_income=True,
                                         has_creditor_payments=True, has_business=True)
      SOFAPriorIncome.objects.create(report=report, year=2025, source="Demo wages",
                                     gross_amount=Decimal("1000.00"))
      SOFACreditorPayment.objects.create(report=report, creditor_name="Demo Bank",
                                         total_paid=Decimal("700.00"))
      assert build_field_values("form_107", IntakeSession.objects.get(pk=session.pk)) == before
  ```

  The guard passes before the cut too (the predicates gate only blank `answer:` bindings); its see-it-fail is in Step 4.
- [ ] **Step 2: Run them.** `pt.sh apps/intake/tests/test_bulk_answers.py apps/intake/tests/test_completion.py apps/forms/tests/test_form_107_schema.py --ds=config.settings.test -q`. Expected: FAIL (`test_saving_form_answers_writes_no_sofa_report`: count 1; `test_the_sofa_report_route_is_gone`: 200).
- [ ] **Step 3: Implement** every edit and deletion in Files, in one tree.
- [ ] **Step 4: Run.**
  - Step 2's command, then `pt.sh apps/intake/tests/test_seed_demo_data.py apps/forms/tests/test_api_readback.py apps/forms/tests/test_derivations.py apps/forms/tests/test_claims_bindings.py apps/forms/tests/test_checks.py apps/forms/tests/test_fill_resolver.py apps/forms/tests/test_rule_fixes.py apps/forms/tests/test_oracle_tier3.py --ds=config.settings.test -q`. Expected: PASS, with `test_oracle_tier3.py` and `test_oracle_tier2.py` unedited (`ASSERTED_CASES` 1935).
  - `check`; `makemigrations --check` (Expected: "No changes detected": the classes are kept).
  - See-it-fail, each reverted: delete all three SOFA classes temporarily (`SOFAPriorIncome` and `SOFACreditorPayment` name `SOFAReport` in their ForeignKeys, `models.py:1684`, `:1698`, so deleting `SOFAReport` alone is a `NameError` at import) and show `makemigrations --check` report a change; in a temporary edit of `data/forms/schemas/form_107.json`, reverted (and not staged), make the text field `Other 1` (`type: "text"`, `conditional_on: "has_creditor_payments"`; every field `has_prior_income` gates is a checkbox, where a constant would raise `UnmappedChoice`) `source: "constant"`, `value: "Demo"`, `binding: null`, and show `test_an_old_sofa_report_changes_nothing_form_107_prints` fail (its report has `has_creditor_payments=True`), which proves the guard sees a box the SOFA predicates gate.
  - `ruff check` on every touched file.
  - **Tree-wide SOFA guard** (COV-24), its output pasted in the task report: `rg -n "sofa\.|SOFAReport|SOFAPriorIncome|SOFACreditorPayment|sofa_report|sofaReport|SOFAStep" backend frontend/src frontend/e2e`. The only hits allowed:
    - the three kept classes in `backend/apps/intake/models.py` and their old migrations (`0007_sofareport_…`, `0008_sofa_report_default_fix`), and every migration's dependency line naming `("intake", "0008_sofa_report_default_fix")` (today `backend/apps/documents/migrations/0003_ingestedaggregate.py:11` and `backend/apps/intake/migrations/0009_add_executory_contracts_and_codebtors.py:10`);
    - the two H6 predicates `_has_prior_income` and `_has_creditor_payments` in `derivations.py` and their `test_derivations.py` cases (gone in T-ii.2);
    - the new tests `test_saving_form_answers_writes_no_sofa_report`, `test_the_sofa_report_route_is_gone`, `test_a_session_with_an_old_sofa_report_still_deletes` and `test_an_old_sofa_report_changes_nothing_form_107_prints`, and the `sofa_prefix_refused` parametrize row;
    - the imports those tests need: `test_bulk_answers.py`'s `SOFAReport` import, `test_completion.py`'s `SOFAReport` and `SOFACreditorPayment` import, and `test_form_107_schema.py:26`'s import of `SOFACreditorPayment`, `SOFAPriorIncome` and `SOFAReport`;
    - `backend/apps/forms/tests/test_rule_fixes.py`'s `test_no_fix_names_a_route_the_app_no_longer_serves` (T-i.4), whose `binding_fix("sofa.creditor_payments[].creditor_name") == {}` names a `sofa.` binding on purpose;
    - `frontend/src/types/api.ts:61` `sofa_report?`, `DynamicFormWizard.tsx`'s dead read and its test (CR §1.3);
    - `IntakeWizard.test.tsx:1363` (`?step=sofa`, an unknown step key);
    - the furniture "sofa" hits (SC §1.6).
    Any other hit stops the task.
- [ ] **Step 5: Commit** with `/opt/local/bin/git rm` of the two deleted tests and `/opt/local/bin/git add` of every modified path above. Message: `intake, forms: SOFA is read and written by nothing (its tables stay until 4i)`.

### Task 6: CLAUDE.md, the spec block, Plane, the gate (T-i.6)

Rulings carried: COV-8, COV-9, R-1, R-3, P1, CODE-7. No `OC` string ships.

**Files:**
- Modify:
  - `CLAUDE.md`:
    - `:28` ("Saves lock the session"): the session PATCH's lock covers `financial_affairs`, and the lock test's `WRITES` gains the `financial_affairs` PATCH (COV-8);
    - `:34` (the reopen list): "Form answers (`answers/bulk`), SOFA, the filing fee…" loses SOFA, and `financial_affairs` joins the session PATCH keys that reopen a completed intake (COV-8);
    - `:39` (`PAGE_LINK_LABELS` without `/sofa`);
    - `:40` (the namespace list: `sofa.` out; `is_money_binding` gains the `affairs.` money cells `paid`, `owed`, `amount`, `value` and loses `sofa.creditor_payments[].total_paid`; the E007 column message names `affairs.<list>[].<cell>` and no `sofa.`; a sentence that `_affairs_binding_error` refuses an `affairs.` key, list or cell the record doesn't hold, over fields, sheet columns and `covers`);
    - `:43` ("the SOFA answers stay stored" → "SOFA's tables stay, unread, until 4i");
    - `:83` (`/means-test` continues to `/forms`, not `/sofa`);
    - `:104`, `:172` (8 journey specs: six personas, the scanned bill and the eviction journey; the SOFA journey gone; Maria's journey downloads Form 107);
    - `:164` (the File Map line without `SOFAStep.tsx` and `/sofa`: `handleComplete` → `/filing-fee` → `/exemptions` → `/means-test` → `/forms`);
    - a new gotcha, "Form 107's answers (lines 1–12)": `FinancialAffairsAnswers` (intake `0050`, one encrypted JSON column and `answered_on`), the key list by line, store-then-flag for shaped values with the hard ceilings (500, 2000, 32, 100 rows, `debt_id` as a digit string), the `l6_answer`/`l6_branch` pair, the prune of `debt_id` after the PATCH's debts, `l4_year` (stamped once, kept while any line 4 or line 5 amount is stored, removed when none is), the read's `fill_year`, and `answer_financial_affairs` (R-47);
    - the File Map gains `FinancialAffairsAnswers` in the `apps/intake/models.py` list and a line for `answer_records.py`'s `AFFAIRS_CELLS`.
  - `docs/superpowers/specs/2026-11-18-forms-step4-design.md`: an appended block (D§2 T-i.6's "PR 4f-i (as built)" block), headed `## Spec amendment, 4f-i (2026-11-27, owner decisions)` to match the spec's own amendment headings (`:1099` for 4d, `:1151` for 4e), after the 4e block and before the file's closing `<!-- prettier-ignore-end -->` (only the closing marker moves down; no line above changes). It records:
    - the split (4f-i: record, plumbing, fixtures, cut; 4f-ii: step 10 and Form 107 lines 1–12) and the swapped cut order, frontend before backend (CODE-7);
    - each item of "Corrections to the spec" group A below, with its authority. Group B is not written in this block: 4f-ii's T-ii.7 records it (COV-9).
- [ ] **Step 1: Edit** CLAUDE.md, then `pt.sh apps/intake/tests/test_claude_md_asset_order.py --ds=config.settings.test -q` and prettier `--check` on CLAUDE.md.
- [ ] **Step 2: Append** the spec block, then prettier `--check` on the spec (the file is wrapped in prettier-ignore).
- [ ] **Step 3: The PR gate.** It runs here, and again, unchanged, after the final-review fix wave:
  - `zsh $JOB/gate.sh 4fi`: `ruff check .`, `ruff format --check .` (the pre-existing 63 reported, none new), `check`, `makemigrations --check`, the whole backend run and the whole vitest run;
  - `zsh $JOB/gate_pg.sh 4fi` (the `financial_affairs PATCH` lock row on Postgres);
  - tsc; eslint on the touched frontend files;
  - `zsh $JOB/e2e-one.sh all 4fi-gate` (all 8 specs: the six personas, `scanned-bill-journey` and `eviction-statement-journey`);
  - `known_defects.json` is `[]`; `ASSERTED_CASES` is 1935;
  - `/opt/local/bin/git log develop..HEAD` shows no trailer.
  Report each count through a one-line `printf`. DIG-523 is reported as the known local failure.
- [ ] **Step 4: List the Plane ticket** for the controller (owner-visible): "4i drops the SOFA tables (`SOFAReport`, `SOFAPriorIncome`, `SOFACreditorPayment`) with a migration that logs the row counts (F6); two SOFA predicates, `has_prior_income` and `has_creditor_payments`, read `sofa_report` until 4f-ii's T-ii.2."
- [ ] **Step 5: Commit** with `/opt/local/bin/git add CLAUDE.md docs/superpowers/specs/2026-11-18-forms-step4-design.md`. Message: `docs: 4f-i in CLAUDE.md and the spec`.

## Corrections to the spec (the spec is amended only by Task 6's appended block)

**Group A: recorded in T-i.6's spec block** (D§2 T-i.6's list: P1, the split, R-1, R-3, the swapped cut order, S:233, S:428; COV-9). Owner decisions and adopted rulings (binding):

- **P1 (OD) supersedes S:672's "models removed", and the removal of the SOFA models in 4f that S:666 ("…and the SOFA models go in 4f") and S:801 ("The SOFA models go only after the engine fixtures that use them are re-pointed") order.** The three classes and their tables stay, unread, until 4i's drop migration logs the row counts (F6). The `sofa.` namespace still goes in 4f, as S:666 says (4f-i, T-i.5), and so do the API, the page and every read and write (T-i.4, T-i.5).
- **R-3 (H6) supersedes S:672's "the three `SOFAReport` predicates … are removed in PR 4f".** `has_business` goes in T-i.5; `has_prior_income` and `has_creditor_payments` read `sofa_report` until 4f-ii's T-ii.2 rewrites the 28 bindings that name them. `DynamicFormWizard`'s dead read and the `sofa_report?` type stay until 4i.
- **R-1 (acknowledged in D§11) moves S:428's per-box `TEXT_LIMITS` ("`TEXT_LIMITS` per box from `text_fit` at 6 pt against the narrowest box the value prints in") and `form_107.limits.json` to 4f-ii.** T-ii.2 writes the file and T-ii.4 reads it. 4f-i's record refuses only hard ceilings, and nothing reads caps at model import.
- **B47 and R-12 supersede S:233's "the PUT refuses above the cap with the form's box named", and S:428's "amounts as decimal strings, dates as `MM/DD/YYYY`"**, for Form 107's record: dates, amounts, last 4, state and ZIP are stored as typed up to 32 characters (`"13/40/2026"` and `"12.345"` are stored, T-i.1 `test_a_malformed_date_or_amount_is_stored_as_typed`), print blank when malformed (T-i.2), and are listed by 4f-ii's gaps; a text cap is the browser's `maxLength` and a gap (4f-ii), never a 400. Only hard ceilings refuse.
- **R-13 supersedes S:428's "No row cap".** Each list holds at most 100 rows, a hard ceiling (the 4e-R17 precedent); slot capacity and sheets are unchanged.
- **R-31 supersedes S:679's "rewritten against step 10, not deleted".** `SOFAStep.test.tsx` is deleted with its page in T-i.4, and its 18 cases' intent is ported case for case into 4f-ii's T-ii.5, since the page doesn't exist between the two PRs. (D§2 T-i.6's list omits it; 4f-i is the PR that deletes the file, so its block records it.)

**Group B: recorded by 4f-ii's T-ii.7 block, not by T-i.6's** (COV-9 assigns S:187 and S:683 to T-ii.7). Listed here so the controller sees that 4f-i already acts on them; T-ii.7 records each once:

- **B44 and R-4 supersede S:187's "re-stamps only when the filer saves line 4 again".** `l4_year` is stamped once from `fill_date().year` when the record first holds a line 4 or line 5 amount and is never re-stamped while any such amount is stored; it is removed when none remains (T-i.1). Every step 10 save carries the line 4 keys, so a re-stamp on save would relabel untouched figures.
- **H10 and CODE-7 correct S:683.** There are seven journeys with a `sofa.waitForLoad(); sofa.skipForNow()` pair, not six, and each also loses its `SOFAPage` import and instance. The frontend cut lands before the backend cut (the swapped order itself is recorded by the T-i.6 block's first bullet). S:683's persona-content clause (James's SOFA content becoming step 10 answers) is 4f-ii's (F1, F8). P12 and R-40 move the one Form 107 download into Maria's journey.

**Not a spec amendment** (noted for the controller):

- **S:662's `binding_fix` clause lands partly early.** `binding_fix` loses `/sofa` in T-i.4. Its `answer:` → `/ask/<form>` return stays for Form 107 lines 13–28 because S:650 puts the deletion of `binding_fix`'s `answer:` branch in 4i; `test_rule_fixes.py:263`'s `/ask/form_107` row stays. R-39 covers only the FormCard pending card's `/ask/form_107` fallback, which 4f-i leaves alone.

Plan corrections (not owner decisions; for the controller to see):

- **D§2 T-i.4's FormDashboard sample page** becomes `/exemptions`, not `/filing-fee`, because `/filing-fee` is already the case's first entry.
- **D§2 T-i.4's new `test_rule_fixes.py` id** is `"affairs_lines_1_12"`, not `"affairs"`, which the `affairs.l13_answer` row already holds.
- **`branch_of` lands in T-i.1, not T-i.2**, because T-i.1's builder needs it (R-47). It lives in `answer_records.py`, as D§2 T-i.2 says.
- **A blank cell is absent, never a 400.** D§3 says ticks and the status are `"yes"` (or a status) "or absent", and D§4.4 doesn't fix how 4f-ii's body sends a blank cell. So a `None` cell, and `""` on a tick, `status` or `debt_id`, is dropped from the row before it is stored (T-i.1 `test_a_blank_cell_is_stored_as_absent`). No step 10 body can then be refused for a blank box.
- **`what_happened` joins with `" "`**, since each of the form's words ends in its own period; D§5.2 names no join for it (R-8: joins are formatting).

## Out of scope

- **4f-ii** (`docs/superpowers/plans/2026-11-27-forms-step4f-ii.md`, written separately): every `AFFAIRS_*` word and the two pinned definitions (T-ii.1); `build_form_107.py`, the schema, its addendum rows, `form_107.limits.json`, `ASSERTED_CASES` 1935 → 2079, the line 1, 3, 4 and 6 rules, `RULE_FIXES` for them, and the removal of `has_prior_income` and `has_creditor_payments` (T-ii.2); the image check, `check29` and the README (T-ii.3); `affairs_step_gaps`, `affairs_fit` and the limits reader (T-ii.4); the step 10 component, the year prompt, the pick and the hidden rows (T-ii.5); the 10 → 11 shift with intake `0051`, `WIZARD_STEPS`, `WIZARD_STEP_COUNT`, `NEW_STEP_KEYS = ("last_few_years_2",)`, the `completion_gaps` splice, `FINANCIAL_AFFAIRS_DEFAULTS`, the seed for all six personas (DeShawn's line 6 Yes, F8), `personas.ts`, `walkLastFewYears1`, the reply rule (R-42) and Review's date line (T-ii.6); its CLAUDE.md, spec block and Plane tickets (T-ii.7), including R-4's two residuals and R-5's stale-branch residual.
- **4g:** `PropertyAffairsAnswers` and Form 107 lines 13–28, which keep their `answer:` bindings and today's plain `affairs.` read; `form_107_carried.json`'s deletion.
- **4i:** the SOFA tables' drop migration (with row counts logged), `DynamicFormWizard`'s dead read and `sofa_report?`, the `answer:` namespace, and the `/ask/form_107` fallback.
- **4j:** `has_insider_payments` (P11), which has no reader after T-ii.2.
- Nothing in 4f-i deploys (S:7); H12 (every completed session refused until step 10 is answered) arrives with 4f-ii.

<!-- prettier-ignore-end -->
