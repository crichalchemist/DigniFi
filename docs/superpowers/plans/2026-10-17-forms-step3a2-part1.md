# Forms Step 3a2 (Drawing Engine) Implementation Plan, Part 1 of 4

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Print every court form through one engine. Each widget gets its own value, drawn with the template's own layout, and the page is flattened, so the packet has no fillable fields left. A letter the form's font can't print, or a value too long for its box even at 6 pt, is refused in plain words, and the dashboard links the refusal to the step or page that fixes it. Extra rows continue on copies of a form's extra page or on an attached sheet (proven on synthetic schemas). Generate All checks without drawing; Download draws.

**Architecture:** `apps/forms/services/widgets.py` addresses every template widget by page and index tag, so a binding can name one widget of a shared name (`<full name>@<page>:<tag>`). `PDFFormFiller.check()` plans each widget from cached widget maps and fonts without opening a PDF: the letters its font prints, the size its value fits at (mirroring pypdf 6.13.1's layout, `text_fit.py`), and where to fix a refusal (`RULE_FIXES`, `fix_for`). `fill()` runs `check()`, builds each planned widget's appearance with pypdf, removes the widgets that never print, bakes with PyMuPDF and nulls `/AcroForm`. `field_values` stores parts (`{"version": 2, "parts": [...]}`): the form, its continuation copies and its attached sheet. The tests read what is printed on the page (`read_drawn`). Each of the 9 tasks is one commit, and every task boundary passes every gate.

**This part:** Tasks 1–4. It starts with nothing of 3a2's code on this branch. The other parts: Part 2 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part2.md`, Tasks 5–6), Part 3 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part3.md`, Tasks 7–8), Part 4 (`docs/superpowers/plans/2026-10-17-forms-step3a2-part4.md`, Task 9). The plan is split only to stay under the repository's 500 KB file limit. Run all parts as one execution: one ledger for Tasks 1–9, and the whole-branch final review only after Task 9, because each part's patches expect each file exactly as the earlier tasks leave it.

**Tech Stack:** Django 5.0 + DRF (Python 3.11), PostgreSQL 15, pypdf 6.13.1, PyMuPDF 1.27.2.3, pytest + pytest-django; React 19 + TypeScript, vitest + MSW; Playwright.

**Spec:** `docs/superpowers/specs/2026-10-17-forms-step3a2-design.md` (approved by the owner 2026-10-17, with factual corrections the same day and from the build on 2026-10-19, which mark four build rulings for the owner's review and record three open questions), drawn from the step 3 umbrella spec `docs/superpowers/specs/2026-10-16-forms-step3-design.md` §4.6, §5.4, §6.1 and §8.2. Read the 3a2 spec in full before Task 1. It is the authority this plan argues from; where a task departs from it, the task's "Decisions already made" and the rulings below say why.

**How this plan was checked:**

- Each task's code was built and committed in order on the local branch `plan/forms-step3a2`. Each task's gates passed, and an adversarial review approved each commit.
- Some commits changed after their gates or their review, or ran their gates on an earlier tree: Task 5 (`467e49b`) ran its journeys before its review's fix round, and after its re-review the plan's author amended one test comment and renamed one test; Task 8 (`71c173f`) ran its journeys before its second fix round (comments, two test titles and one test), which the plan's author checked rather than a further review; Task 9 (`54410ef`) ran its journeys before its fix round (one startup rule for repeat groups, tests and wording), which the plan's author checked the same way. A reviewer should read these changes in the whole-branch final review.
- The plan was then dry-run from its own text in a fresh worktree, and after every task the tree matched the verified commit exactly.
- Final tree: backend `2814 passed, 25 skipped, 1 xfailed`, the Postgres lock tests `25 passed`, vitest `Tests  423 passed (423)`. Journeys: in the dry-run, all 8 passed on both runs after each of Tasks 3, 5, 8 and 9. Timing: on the dry-run's final tree, `time_packet` held every budget for all six personas, each in a fresh process at a 1-minute load of 3.9 to 4.9: Generate All 2.24 to 2.56 s (budget 5 s), and the slowest download, Form 107 in every packet, 1.42 to 1.54 s (budget 3 s each).

## Global Constraints

- **pypdf internals** are used only through `pypdf.generic._appearance_stream.TextStreamAppearance` (`from_text_annotation`), `pypdf.PdfWriter._add_object`, `pypdf._font.Font` (`from_font_resource`, `can_encode`, `get_text_width`, `_get_typographic_maps`, `font_descriptor`) and `pypdf._codecs.adobe_glyphs` (`"/.notdef"`), each pinned by a test with `pypdf.__version__ == "6.13.1"`. New code imports PyMuPDF as `import pymupdf`; the documents app's `import fitz` stays.
- **PyMuPDF** is already installed (1.27.2.3); Task 3 pins it in `backend/requirements/base.txt`. It is AGPL-licensed, as DigniFi is.
- **Speed:** `check()` opens no PDF. It works from the cached widget map and cached fonts. Drawing clones each template once per form and writes once. Caches are keyed by template filename, never by form type.
- **Line breaks** are what pypdf splits on: `str.splitlines()`. Never split or join on `"\n"` alone.
- **The fill date.** The root `backend/conftest.py` pins it to 2026-10-16 for every backend test. The dev server, the seed and the journeys use the real date: from 2026-11-01 the forms, the means test, `seed_demo_data` and the journeys refuse until the November median table is loaded (`docs/REFERENCE_TABLES.md`). Run the journeys before then, or load the November table first.
- **Filer-facing words** are information, never advice (`docs/UPL_COMPLIANCE.md`), in plain language (`docs/PLAIN_LANGUAGE_GUIDE.md`). Where the spec gives a sentence, the code uses it word for word, curly quotes included.
- **Never log filer data.** Logs reach Sentry (DIG-105). A refusal carries the filer's letter only in its 422 body, never in a log line.
- **Shape changes:** before changing a function's signature, return shape, exception or response body, grep every caller (tests, `data/forms/field_index/tools/`, frontend) and update them in the same commit.
- **Tests are named for the outcome they protect**, mock boundaries and never logic, and a test the change breaks is fixed in the same commit.
- **No new dependencies** (Python or npm).
- **Test data** is synthetic only: SSNs from the IRS-reserved 900 range, phone numbers from 555-0100–0199, invented names of people and firms.
- **Known form defects:** `backend/apps/forms/tests/known_defects.json` stays `[]`.
- **CLAUDE.md gotchas** that a task makes false are updated in that task's commit.
- **Gates:** every commit leaves backend pytest with coverage at 90% or more, `manage.py check`, ruff 0.8.5, the Postgres lock tests, vitest, tsc, eslint and prettier green. The journeys run on Tasks 3, 5, 8 and 9.
- **Lint:**
  - ruff 0.8.5 (`ruff check backend/`, as CI runs it).
  - Pre-commit runs black 24.10.0 (line length 100) on `backend/`, prettier 3.4.2 on JSON, Markdown, CSS and TypeScript outside `backend/` (not YAML; `check-yaml` parses it), and eslint on the frontend.
- **Never run `tsc -b`.** It writes build output through the `node_modules` symlink into the main checkout. Use `tsc -p tsconfig.app.json --noEmit` and `tsc -p tsconfig.node.json --noEmit`.
- **Commit messages** end with the last line about the change. **Add no `Co-Authored-By`, `Claude-Session` or other agent trailer, even if your harness asks for one.**
- **Staging:** stage files by explicit path only, never with `git add -A`, `git add .` or `git commit -a`. Commit only the files the task lists.
- **No outward actions:** no push, PR, merge, deploy or production command. Those are the owner's decisions. Nothing in 3a2 deploys: production waits for steps 3–5 and DIG-146.
- **Databases:** never use the shared development database `dignifi_dev`. This plan makes its own.
- **Keys:** never print, log or commit an API key. This plan does not use the repo-root `.env`; the journeys use a dummy key against a fake OpenAI server.

## Before you start (once per worktree)

- Work in `/Volumes/Containers/DigniFi/.claude/worktrees/forms-step3` (branch `feat/forms-step3a2`, which holds the 3a2 spec). Every command block runs from that worktree's root.
- Backend tools come from the main checkout's virtualenv, and frontend tools from its `node_modules`. Pre-commit's eslint hook expects that symlink.
- The journeys and the Postgres lock tests need Colima running, with the `dignifi-db-1` Postgres container answering on host port 5433. The journeys also need nothing listening on ports 8000, 5173 or 4010.
- `pytest` uses `config.settings.test` (sqlite in memory). The Postgres lock tests use `config.settings.test_postgres`, which reads `DATABASE_URL`. `manage.py` and the journeys use the database below.

```bash
set -eo pipefail
mkdir -p backend/logs .claude   # the audit log handler needs backend/logs; CI creates it too
[ -e frontend/node_modules ] || ln -s /Volumes/Containers/DigniFi/frontend/node_modules frontend/node_modules
# CI's synthetic Fernet key (it encrypts nothing real), read from ci.yml rather than copied here
FERNET=$(sed -n 's/^ *FIELD_ENCRYPTION_KEY: //p' .github/workflows/ci.yml | head -1)
[ -n "$FERNET" ]
# A database of its own keeps the shared dev database on develop's migrations. The Postgres
# lock tests create and drop their own test database beside it.
docker exec dignifi-db-1 dropdb -U dignifi --if-exists dignifi_forms_step3a2
docker exec dignifi-db-1 createdb -U dignifi dignifi_forms_step3a2
cat > .claude/forms-step3a2.env <<ENV
# Settings for forms step 3a2 (git-ignored). Source from the worktree root.
export PY=/Volumes/Containers/DigniFi/backend/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export DATABASE_URL=postgres://dignifi:dignifi_dev_password@localhost:5433/dignifi_forms_step3a2
export DJANGO_SECRET_KEY=test-only-not-a-secret
export DEBUG=True
export ALLOWED_HOSTS=localhost,127.0.0.1
export CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
export FIELD_ENCRYPTION_KEY=$FERNET
export OCR_PROVIDER=openai
export OPENAI_API_KEY=e2e-dummy-key
export OPENAI_BASE_URL=http://127.0.0.1:4010/v1
ENV
source .claude/forms-step3a2.env && $PY -c "import pypdf, pymupdf; assert pypdf.__version__ == '6.13.1', pypdf.__version__; assert pymupdf.__version__ == '1.27.2.3', pymupdf.__version__"
git check-ignore -q .claude/forms-step3a2.env && git check-ignore -q .claude/e2e.sh && echo "env file is ignored"
```

Expected: `env file is ignored`.

The journeys run through one script, which every task marked for them calls. Write it now:

```bash file=.claude/e2e.sh
#!/bin/zsh
# Run the Playwright journeys on this worktree's own database.
# usage (from the worktree root): zsh .claude/e2e.sh [runs=2]
# Migrates, loads the district data, reseeds the personas, starts runserver (:8000)
# and Vite (:5173), runs the journeys RUNS times, prints one summary line per run,
# and always stops both servers. Logs: .claude/e2e-logs/.
set -u
RUNS=${1:-2}
cd "$(git rev-parse --show-toplevel)" || exit 2
source .claude/forms-step3a2.env
export DJANGO_SETTINGS_MODULE=config.settings.development PYTHONUNBUFFERED=1
LOG="$PWD/.claude/e2e-logs"
rm -rf "$LOG"; mkdir -p "$LOG"

for port in 8000 5173 4010; do
  if lsof -nP -iTCP:$port -sTCP:LISTEN >/dev/null 2>&1; then
    echo "PORT $port BUSY: stop whatever holds it first"; exit 3
  fi
done

( cd backend && $PY manage.py migrate -v 0 && $PY manage.py loaddata ilnd_2025_data -v 0 \
  && $PY manage.py seed_demo_data --reset ) > "$LOG/setup.log" 2>&1 || { echo "SETUP FAILED"; tail -20 "$LOG/setup.log"; exit 4; }

( cd backend && exec $PY manage.py runserver 0.0.0.0:8000 --noreload ) > "$LOG/backend.log" 2>&1 &
BPID=$!
( cd frontend && exec ./node_modules/.bin/vite --port 5173 --strictPort ) > "$LOG/vite.log" 2>&1 &
FPID=$!
cleanup() { kill $BPID $FPID 2>/dev/null; wait $BPID $FPID 2>/dev/null; }
trap cleanup EXIT INT TERM

up() { $PY -c "import urllib.request,sys; urllib.request.urlopen(sys.argv[1], timeout=2)" "$1" >/dev/null 2>&1; }
for i in {1..60}; do up http://127.0.0.1:8000/health/ && up http://localhost:5173/ && break; sleep 1; done
up http://127.0.0.1:8000/health/ || { echo "BACKEND NOT UP"; tail -20 "$LOG/backend.log"; exit 5; }
up http://localhost:5173/ || { echo "VITE NOT UP"; tail -20 "$LOG/vite.log"; exit 5; }

overall=0
for r in $(seq 1 $RUNS); do
  ( cd frontend && npx playwright test --config e2e/playwright.config.ts --reporter=line ) > "$LOG/run$r.log" 2>&1
  rc=$?
  perl -pe 's/\e\[[0-9;]*[A-Za-z]//g' "$LOG/run$r.log" > "$LOG/run$r.txt"
  summary=$(grep -E "^\s*[0-9]+ (passed|failed|flaky|skipped|did not run)" "$LOG/run$r.txt" | tr -s ' ' | tr '\n' ' ' | sed 's/^ //')
  echo "RUN $r exit=$rc: $summary"
  if [ $rc -ne 0 ]; then
    overall=1
    grep -E "^\s+[0-9]+\) " "$LOG/run$r.txt" | head -10
  fi
done
exit $overall
```

It migrates the step's database, loads the district data, reseeds the personas, starts the backend on :8000 and Vite on :5173, runs every journey in `frontend/e2e/journeys/` `RUNS` times, prints one line per run, and always stops both servers. Its logs land in `.claude/e2e-logs/`. A failed run prints the failing journeys; read the trace under `frontend/test-results/` before running again, and don't retry blindly. Journeys are sensitive to machine load: under a load average far above the core count, Generate All can outrun the dashboard's wait. Check `uptime` before blaming the task.

Check the baseline before Task 1:

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2166 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  397 passed (397)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

## How to read the code blocks

- **`<language> file=<path>` blocks:** the block is the file's complete content. Create or overwrite the file with exactly that text.
- **`bash` blocks:** run from the worktree root in a fresh shell (bash or zsh). Each block starts with `set -eo pipefail`, so any command that fails, including one inside a pipeline, stops the block and fails it. A block sources `.claude/forms-step3a2.env` itself when it needs it.
- **`git apply <<'PATCH'` blocks:** these patch the state the previous task left. If one doesn't apply, stop: the tree has drifted from the plan.
- **"Expected:" lines** say what the command must do. An "Expected: FAIL" step is the red half of test-first. Every other step must succeed.
- **Commit blocks** use each task's verified commit message; Task 5's leaves out one sentence that proved false, as its commit step says. A pre-commit hook that rewrites a file means the tree has drifted from the plan: stop and compare.

## Decisions already made

These rulings were settled while the plan was built: by the owner where marked, otherwise by the plan's author against the spec. Every task's code already follows them. Don't reopen them in review; the owner may still overturn the build rulings listed under "Open for the owner or parked". A task that depends on one repeats it in its own text.

- **Nine tasks, one commit each, in this order.** Each task builds on earlier ones: widget addresses (1), `check()` (2), the drawing (3), the page tests (4), Generate without drawing and the stored parts (5), copies (6), sheets (7), the dashboard's links to the `step` or `page` each refusal carries (8), and what the whole-branch review found once Tasks 1–8 were each approved (9). The read-back was proven on the real templates before any test was ported (Task 3's decisions). R25 split Task 4 from Task 3; Task 4 changes no production code. R71 put the whole-branch review's fixes in a task of their own rather than back into Tasks 2–8, so each earlier task stays exactly as it was reviewed.
- **The owner's calls (spec §2, answered 2026-10-17), in the spec's words.**
  - 3a2.Q1, letters the form can't print: refuse in plain words. The forms keep the template's own font. A value with a letter that font can't draw is refused. The refusal names the letter and the box, and sends the filer to the step or page that holds the value. Nothing ever prints as "?". A Unicode font can follow in a later PR if real filers need it.
  - 3a2.Q2, a value too long for its box: shrink, then refuse. The value shrinks down to 6 pt and wraps in multi-line boxes. If it still doesn't fit, it is refused in plain words, naming the box and the step or page that fixes it. Nothing is ever cut off.
  - 3a2.Q3, timing: check without drawing. Generate All, Generate and Regenerate run every check drawing runs, then store the result without drawing. Download draws. A command times a full persona packet locally against a budget, and the deploy steps time it on the Eco dyno. The browser stops retrying Generate All.
  - The budgets (spec §7): for every persona, Generate All at 5 s or less and each download at 3 s or less. A miss stops the build and comes back to the owner. The budget is not moved to fit. On the Eco dyno the ceiling is 15 s each, half of Heroku's 30 s router timeout.
- **R1.** Frontend tests take prose `it('…')` names that carry the meaning of spec §9's snake_case names, as the existing frontend tests are named: none of them is snake_case. Backend tests keep the spec's snake_case names, pytest's convention. Spec §9 says so since its second errata.
- **R2.** The dashboard links refusals from Generate All, Generate and Download. Spec §4.5 also listed Regenerate until its second errata, but the frontend has no Regenerate: no client call, handler or button.
- **R15, R27, R30.** A binding may name one widget with `tag` (`FieldSpec.tag`, after `choices`), and it resolves under the key `<full name>@<page>:<tag>`. E003 refuses a tag that isn't a drawn widget of that name on that page, and an index full name containing `@`; a template that no longer matches its index is reported as E003, not raised. E006 counts the drawn widgets each writer would fill, and two writers of one widget conflict, rows of one repeat group included: the old "same group, different rows" exemption never worked, since `resolve()` wrote one key per name.
- **R17, R31.** A template widget is matched to its index row by page and rectangle within 0.6 pt, one-to-one, or `TemplateMismatch`. The flip to the index's top-left coordinates uses the page's mediabox top, so it is exact for any mediabox origin. `parse_key` raises `ValueError` on a malformed key, and `check()` reports it as `UnknownField`.
- **R4, R28.** A widget's `MaxLen` is its own, else inherited from its parents, and it limits every box, comb or not. pypdf reads a comb box's cell count from the widget alone, so the drawing copies the inherited value onto a comb widget that lacks one; otherwise Schedule D's two `account number` boxes print every digit in the first cell.
- **R5, R38 (as corrected).** A single-line box fits on width alone: the text, measured as pypdf measures it, must fit the box's width less 4 × margin, pypdf's own padding. The margin is the field's `/BS` width (1 if unset), doubled for a `/B` or `/I` style, and at least 1 pt. There is no height rule: at their own size, 37 single-line boxes let only Ç's cedilla dip below the rect, by at most 0.108 pt, which is the template's own size and invisible. Task 4's cut-off test allows 0.11 pt at the bottom for exactly those boxes and pins their count at 37. Spec §4.3 says so since its second errata, which marks it as a build ruling for the owner to review.
- **R7, R64.** A letter is printable when the box's font can encode it (`Font.can_encode`, the test pypdf makes before it warns), except □: pypdf reads the font's `/.notdef` glyph as □, which the templates' `/Helv` puts at code 173. `text_fit.printable` refuses it, for the forms and the sheets alike.
- **R6, R33, R36.** In every box and in a sheet's cells, a tab and every Unicode space separator (Zs) print as a plain space, a format character (Cf, such as a soft hyphen) is dropped, and any other control character (Cc) except a line break is refused as `UnprintableLetter`. A line break, anything `str.splitlines()` splits on, is a space in a single-line box and a new line in a multi-line box. A comb box also refuses `(`, `)` and `\`, whose escapes break a cell. Widths are measured on the escaped text, as pypdf measures them. R36 replaced R34, which covered only a tab and U+00A0. Spec §4.3 says so since its second errata, which marks R33's and R36's rules as build rulings for the owner to review.
- **R71 (F1).** The letter rules start by composing the text (Unicode NFC), so a letter typed as a base letter plus a combining mark (e + U+0301, as text pasted from some systems arrives) is checked, measured and drawn as the one letter the form prints (é). Without it the check refused the combining mark and quoted it alone. `_as_printed` is the one entry for `check()`, the drawing and the sheets, so all three agree. Composing also prints six characters Unicode treats as the same as a letter the form prints (the Ångström sign as Å, the Kelvin sign as K, the Greek question mark as ";" and three more) as that letter.
- **R29, R32.** Every text box's `/DA` names `/Helv`, which each template's `/AcroForm /DR` resolves to Helvetica, and `check()` measures and encodes with that font. 567 text and combo widget annotations on five templates carry their own `/DR /Helv` without the template's encoding, so pypdf printed "?" for Ł, ’ or – there. The drawing deletes a widget's own `/DR` before building its appearance, so spec §4.3's "same encoder" holds. Spec §4.3 says so since its second errata.
- **R8, R26, R42.** pypdf reads a widget's value and alignment from its field, which siblings share. So just before building each text or combo widget, the drawing sets the field's `/V` to that widget's planned text and its `/Q` to the widget's own alignment, and builds at the planned size (`user_font_size`), so pypdf's own auto size never runs. Right after, it puts the field's original `/V` back, or deletes it: MuPDF's bake builds an appearance from `/V` for a sibling with no `/AP`, which printed one widget's value in every sibling.
- **R35.** pypdf hangs a multi-line box's first line from the font's top at the box's height plus its margin, which cuts off a capital's mark. The drawing lowers the first line by 2 × margin, and `check()`'s height rule is `lines × size × leading ≤ height − 2 × margin`. Spec §4.3 says so since its second errata. Accepting the cut would break 3a2.Q2, and refusing a capital with a mark on line 1 would refuse common names.
- **R39.** No code sets `/NeedAppearances`, and no template does. Setting it doesn't change MuPDF 1.27.2.3's bake either (Task 3), so no test guards the rule; `test_a_shrunk_value_prints_at_its_planned_size` proves the bake keeps pypdf's appearance. MuPDF extracts a partly hidden glyph whole, so the tests judge a cut by where each glyph sits, or by its pixels, never by its text.
- **R40, R43, R49.** `read_drawn` gives a character to a widget when the character's centre lies inside the widget's rect, since a plain clip read a neighbour's tick where two rects overlap (a test pins those pairs by page and tag). A box that prints exactly what the blank template prints there (a district placeholder, A/B's 19.x "0%", C's `page 2`, G's `fill 2.6`) reads as blank. `read_drawn` raises `ValueError` when any page still has a widget, since MuPDF reads an unbaked widget as text; a `ValueError`, not an assertion, so a known defect's xfail can't swallow a missing bake. Spec §8 says so since its second errata.
- **R44, R50.** Tiers 1 and 3 assert every drawn widget of a binding's full name, so a widget that prints blank fails. Tier 1's engine check covers every full name with more than one drawn widget, text, combo and box alike (spec §8: "every widget of every shared full name"): each text or combo widget gets its own sentinel through its widget key, and each box widget is ticked alone, in rounds. Spec §8 says so since its second errata.
- **R48.** Caches of template data are keyed by template filename. Tier 1's cached draws (`_text_fill`, `_box_fill`, `_widget_fill`, `_widget_box_fill`) stay keyed by form type, as that file's caches were before 3a2: each holds one form's drawn output, the 17 form types use 17 distinct templates, and no tier 1 draw runs under a synthetic schema.
- **R20.** `registry.build_parts` returns the `{"version": 2, "parts": [...]}` document the views store. `build_field_values` keeps returning the form's `{key: value}` for its other callers, `seed_demo_data` and the tests. `check()` and `fill()` take either shape through `parts_of`: a dict without `"version": 2`, such as a form filed before 3a2, is one form part.
- **R14, R53.** Task 5 stops Generate from drawing. Four Generate tests patched `fill()`, six cases in all. Three of them (five cases) patch `check()` instead, each keeping what it proved. The fourth, `test_expected_failure_is_explained_in_plain_words`, loses its `TemplateHasNoForm` case: only drawing raises it, so its plain-words sentence is proven through Download alone. Each download that `time_packet` times includes `_prepare`, as a real Download request does.
- **R13.** `time_packet` runs the views' own helpers inside one `transaction.atomic()` that ends with `transaction.set_rollback(True)`, so it times the request's code and writes nothing. It skips the system checks, which would build every template's widget map, so it judges the first run of a fresh process with every cache cold, as on an Eco dyno that has just woken.
- **R41 (amended), R51, R52.** `fill()` returns `tobytes()` without `garbage` or `deflate`: the spec sets no size limit, and `time_packet` prints each PDF's size beside its template's. `text_fit` builds pypdf's typographic maps once per template filename and font name (`reverse_cmap_for`), since pypdf rebuilds them on every call, so `fit(widget, template_filename, text)` takes the template and finds the box's font itself. Cloning from a template parsed once was not taken: every `time_packet` budget held without it.
- **R46, R71 (m6).** A filed form whose stored values `check()` now refuses for a letter or a length downloads as a 422 with the refusal's sentence and no `step` or `page`, because no step changes what was filed. Any other refusal of a filed form (a key or box state the template no longer has) stays a 500: it means the template changed under a filed form, which is an operations problem, not the filer's. Production v31 stores no values, so it holds no such row. `main`, the copy self-hosters run, has stored each form's values unchecked since forms step 1, so a self-hoster's filed form can hold one; whether it should then download as this 422 is open for the owner (R73).
- **R47 (amended).** PyMuPDF isn't thread-safe, and nothing takes a lock around it. Download bakes with it. Since Task 7, every `check()` imports `sheets`, which builds PyMuPDF's `Font` when first imported, and Generate (through `check()`) and the startup check measure an attached sheet's text with it. Production runs gunicorn with 2 sync workers, one request per process, and `CLAUDE.md` says the server stays on sync workers, with no `--threads`, unless the bake gets a lock. The threaded dev server could crash, rarely, on two such calls at once.
- **R18, R19.** Copies and sheets are proven on synthetic schemas over the real templates: a test copies the real schemas into `tmp_path`, adds a group to Schedule D or A/B, and points `FORM_SCHEMAS_DIRECTORY` there. The groups bind `sofa.creditor_payments[].creditor_name` and `sofa.creditor_payments[].total_paid`, an existing list; 3a2 adds no list source. No production schema has a group or a tag.
- **R12.** No production schema has a `sofa.` binding or a text constant (its four constants are checkboxes), so the `/sofa` fix and the constant rule are proven on synthetic bindings.
- **R9, R10, R11, R37.** `fix_for(field)` follows spec §4.5's table. A derived rule's fix is a copy of its entry in `RULE_FIXES`, the map beside `DERIVATIONS` that covers every derived rule bound to a text or choice box; a test fails on a missing rule or a step that isn't a `WIZARD_STEPS` key. `fee_waiver_monthly_expenses` goes to `expense_info`, since 103B line 6 is Schedule J line 22c; `schedule_j_monthly_net_income` goes to the earlier of its two steps, `income_info`; and a rule no filer edits gets no fix. An asked answer links to `/ask/` with the form type its binding names, not the form being drawn. `ingested` and `db_aggregate` go to `/documents`. Since its second errata, spec §4.5's table has the `db_aggregate` row, and the paragraph under it counts the district name (`district_name`, in the forms' district boxes) among the rules with no link.
- **R21 (as amended), R56.** One group with an `extra_page` per form is 3a2's own limit, not the spec's; spec §5.2 records it since its second errata, which marks it as a build ruling for the owner to review. Startup (E007) refuses a second one, because 3a2 numbers a form's pages counting one group's copies; a sheet group doesn't count. Before 3c binds a second group with an extra page on any form (spec §5.1: D's page 2 and its Part 2; E/F's pages 2 and 4 and its Part 3), it must lift the refusal and count every group's copies. Page-number boxes are a group declaration, filled only when the group has copies. A group's slot rows must be exactly 1 to its `repeat_capacity`, with one capacity and one `conditional_on` across its fields, so no row prints twice or nowhere.
- **R24, R55 (2, 4, 5).** A copy repeats only the form's page headers: a value whose full name is drawn on the extra page and on another page, never a page total, and never a group's own slot, number or page-number box. Spec §5.2 says so since its second errata. `fill()` draws each copy alone on its own clone, keeps that page, bakes it, and inserts it after its extra page or the copy before; a copy's widgets are never merged into the form's. An overflowing group that isn't declared in `groups` or names neither an extra page nor a sheet, and a part of a kind `check()` doesn't know, each raise `ValueError`, a 500 logged by type, which no schema startup accepts and no part DigniFi stores can reach.
- **R55 (3), R58, R59, R60.** Startup refuses a group declaration that would print a row wrong, rather than printing it wrong. E003 refuses an untagged binding whose `page` holds no drawn widget of its name, since a copy picks a row's boxes by `page`; a number box for a row that isn't a slot row; a number or page-number box that is no drawn widget on its row's or page's page; and an untagged number or page-number `this` box whose name has more than one drawn widget. E007 refuses a slot row on two pages, rows that go back a page, a `number` whose `format(n=1)` fails or prints the same as `format(n=2)`, and an untagged slot that would print twice: a text or combo slot whose name has more than one drawn widget, or a box slot whose drawn widgets share an on-state. E006 counts every number and page-number box a group writes as a writer beside the bindings. A copy takes its slots from the group's mapped fields on the extra page; `legal_review` decides only which cells print.
- **R64 (Importants 2 and 7), Task 7's sheet rules.** E007 refuses a group that names both an `extra_page` and a `sheet`, or neither; a sheet group with `page_numbers`; a sheet with no columns, or whose columns and 36 pt line column are wider than 504 pt; a column whose binding isn't a `sofa.<collection>[].<attr>` list or isn't one of the group's slot bindings, or is a box slot's; a slot binding no column prints, since the rows past the slots would drop it, and, since Task 9 (R71, m12), any slot with no binding and any box slot, bound or not; a title or label the sheet can't print whole; and a first sheet line (`number` for the row past the slots) that doesn't print whole on one line of the line column.
- **R23, R63.** A sheet part stores the filer's name, the sheet's title and its columns' labels and widths beside its rows. `check()` and `fill()` take a sheet's title, columns and rows from its part, never from the live schema, so a filed sheet prints exactly what was filed (spec §6, DIG-155). Only a refusal looks there: for a refused cell's link to its fix (R65 (1)), and for the label of the form's name box when the filer's name is refused. Spec §6 says so, and its example has those keys, since its second errata.
- **R62.** A sheet prints in the forms' own text font: base-14 Helvetica with the `/Encoding` every template's `/Helv` shares, so it prints exactly the letters the forms print, Ł, ł and ı included, and its letter check is the forms' own `printable`. Spec §5.3 says so since its second errata. Spec §5.3 asks for "The same rules as the form", and Task 7's first build, in PyMuPDF's WinAnsi Helvetica, refused 13 letters the forms print.
- **R65 (1), R66.** A sheet refusal names a column by its label and takes its fix from the slot, in the live schema, whose binding the column of that label prints. E007 refuses two columns with one label, so a label can't point a refusal at the wrong slot. A filed sheet's refusal carries no fix anyway (R46).
- **R67, Task 7's sheet layout.** Spec §5.3 leaves a sheet's layout open. A sheet has a 36 pt line column, 2 pt cell padding, a 180 pt blank after "Case number (if known)" and no "Debtor 1" label. Its pages aren't counted in the form's page numbers: §5.2 counts the copies. Task 7's review accepted these; 3c revisits the page count when it binds sheets.
- **Spec errata, done.** The spec's second errata is committed before this plan. It corrects §4.3 (the same encoder, R32; a multi-line box's height and first line, R35; the rules for spaces, format and control characters and a comb box's `(`, `)` and `\`, R33 and R36, whose refusals take the letter sentence for now, W-1; a single-line box's height, R38), §4.5 (the `db_aggregate` row; `district_name`'s place in the fix map, R11; no Regenerate, R2; a link only for a refusal whose fix the dashboard can link to; the retry advice, which shows only when a form in Generate All's list names no such fix), §5.2 (copies repeat the page headers, R24 and R55 (2); one extra-page group per form, R21 and R56), §5.3 (the sheet's encoding, R62), §6 (the sheet part's title, columns and name, R23 and R63; the copy example's key), §8 (the read-back, R40 and R49; a box's blank text; boxes in the engine check, R50), §9 (the cut-off test's method; prose frontend test names, R1), §10 (tiers 1 and 3 read drawn text, R3) and §11 (one extra-page group per form, R21 and R56; two-digit entry numbers on D, R57, and correcting a scanned value the form can't print, R69, both open questions). It marks R33, R36, R38 and R21/R56 as build rulings for the owner to review.

**Open for the owner or parked:**

- **R22 (amended), for the owner.** These fix-link words are the plan author's, not the spec's: `/fee-waiver` reads "Go to Filing Fee Waiver Application"; `/sofa` reads "Go to Statement of Financial Affairs"; `/documents` reads "Go to Upload your documents"; and `/ask/<form type>` reads `Answer the questions for <form label>`. A step reads `Go to <step label>`, the Review step's own words, and `/intake` keeps "Finish your intake", step 2 spec §5.3's. They go to the owner with the plan (ledger R22, amended; Task 8).
- **R33, R36, R38, R21 and R56, for the owner.** The spec's second errata marks these build rulings for the owner's review: a tab and every space separator print as a space, format characters are dropped and other control characters, except line breaks, are refused (R36); a comb box refuses `(`, `)` and `\` (R33); a single-line box fits on width alone, so Ç's cedilla may dip up to 0.108 pt below 37 boxes (R38); and only one group per form continues on copies (R21, R56). The code follows each until the owner rules.
- **W-1, under R36 and R71, for the owner.** The letter sentence, "Change it to a letter without the mark.", fits only a letter with a mark. It is also what a comb box's `(`, `)` and `\` get, a control character, a letter with no mark at all (Cyrillic, Greek, CJK, ə), and a mark with no composed letter (n̈, refused at its mark). The owner words the sentence or sentences for those cases at handover (ledger R36, R71; Task 2's decisions).
- **R71 (m16), for the owner: the README.** The public README still says pypdf alone makes the PDFs. Since Task 3, PyMuPDF bakes every download and measures a sheet's text, and it is the AGPL dependency behind the licence. README hunks need the owner's yes, so the plan leaves it.
- **R57, for the owner, and a 3c prerequisite.** An entry number with two digits after the point, such as 2.10 or 2.12, doesn't fit Schedule D's `undefined_12@2:T3` even at 6 pt (on the synthetic D, row 12 is the first to reach it), so real Schedule D must not be bound until the owner decides. Spec §11 records it as an open question since its second errata (ledger R57; Task 6's decisions).
- **R69, for the owner: a scanned value the form can't print.** Schedule I's employer name comes only from a pay stub. A letter its box can't print, or a name too long for it even at 6 pt (about 41 capitals), is refused with a link to `/documents`, as spec §4.5's table says, but nothing there can change the name, so Schedule I can't be prepared. The owner chooses the fix: a correction field on the upload page (the documents API's `validate` already re-reads the pay stub), no link and a sentence of its own, or a bound when the pay stub is read. Spec §11 records it as an open question since its second errata (ledger R69; Task 8's review).
- **R73, for the owner: a self-hoster's filed form.** `main` draws a filed form's stored values as they are, so a letter the form's font can't print came out as "?" and a long value was cut off at the box's edge. Once 3a2 reaches `main`, a filed form holding such a letter, or a value too long for its box even at 6 pt, downloads as R46's 422, which names the letter or the box, instead of that misprinted PDF. Production v31 stores no values and isn't affected. The owner chooses: keep the 422; draw a form filed before 3a2 without the letter and length refusal, misprints included; or check self-hosters' filed rows before `main` is promoted. The code keeps the 422 until the owner rules. Spec §11 records it as an open question since its second errata (ledger R73; the final ticket sweep).
- **R61, parked for 3c.** (1) An untagged column of own-state boxes spread over several pages passes startup, though no template has one; (3) startup checks that a number box is a drawn widget on its row's page, not that it sits beside its own row: two rows that swap number boxes pass and print 2.5, 2.4, 2.3, so before 3c binds real groups, group boxes need an audit or tier 2 placement check, as bindings have (ledger R61; Task 6's decisions).
- **R71 (m7), parked for 3b and 3c.** `resolve_parts` resolves each slot binding with its own query, with no order, and pairs a row's cells by position, so which row lands on which slot, copy or sheet line isn't stable, and a SOFA row changed between those queries could pair one creditor's name with another's amount. It predates 3a2, and no production schema has a group. Before 3b or 3c binds real rows: resolve each list once, in a stable order, and read every column from those rows (ledger R71; final review).
- **R56, parked: Task 6's review Minor 17.** Two parts of `_headers`, its tag condition and its exclusion of group boxes, have no test (Task 6's decisions).
- **R64, parked: Task 7's review finding 20.** `test_totals_count_rows_printed_on_copies_and_sheets` sums the rows in a test-only rule, so it can't catch a defect in a real total (ledger R64; Task 7's commit body).
- **R65 (2), parked.** Startup checks only a sheet's first line against the 36 pt line column; a later line too wide is a `ValueError`, a 500 at Generate, first at row 10,000 for `"3.{n}"` (ledger R65).
- **R54, parked: Task 5's review findings 9, 10 and 12.** Download timing leaves out the store and `save()`; Download's full `save()` can undo a concurrent `mark_filed` (pre-existing, a ticket candidate); the R51 cache has no test (Task 5's decisions).

## Spec coverage

The 3a2 spec's sections map to tasks as follows.

| Spec                                                                                                                           | Task                                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| §1 and §2: what 3a2 does, and the owner's three calls (3a2.Q1 refuse letters, Q2 shrink then refuse, Q3 check without drawing) | 2 (Q1, Q2), 5 (Q3), 8 (the browser stops retrying), 9 (composed letters)                                                       |
| §3: why the drawing method changes                                                                                             | 3 (the drawing), with the umbrella spec's pointers in its docs; 9 (the pointer to §8 for the oracle)                           |
| §4.1–§4.2: today's filler, and each widget's address by page and tag                                                           | 1                                                                                                                              |
| §4.3: `check()`, the letters each box prints and the size each value fits at                                                   | 2; 9 (composed letters, an empty label)                                                                                        |
| §4.4: `fill()` draws, removes what never prints, bakes and nulls `/AcroForm`                                                   | 3                                                                                                                              |
| §4.5: refusals and where they send the filer, server side                                                                      | 2                                                                                                                              |
| §4.5: the dashboard's link to each refusal's fix                                                                               | 8; 9 (Generate All's answer replaces the cards' refusals)                                                                      |
| §4.6: PyMuPDF pinned                                                                                                           | 3                                                                                                                              |
| §5.1, §5.2: slots and continuation copies, and §5.4 for Schedule D                                                             | 6                                                                                                                              |
| §5.3: attached sheets, and §5.4 for Schedules A/B                                                                              | 7; 9 (every slot a sheet group can't print is refused)                                                                         |
| §6: stored values in parts, and filed forms redrawn as filed                                                                   | 5                                                                                                                              |
| §7: Generate All, Generate and Regenerate check; Download draws; `time_packet`                                                 | 5 (server), 8 (no retry), 9 (`time_packet` skips filed forms)                                                                  |
| §8: the oracle reads the printed page                                                                                          | 3 (`read_drawn`, tiers 1 and 3 ported), 4 (tier 1's every-widget check), 9 (no tick spills into another name's widget)         |
| §9: tests                                                                                                                      | the task that builds each behaviour; the page tests in 4; the frontend tests in 8; the gaps the whole-branch review found in 9 |
| §10: docs and `CLAUDE.md` gotchas                                                                                              | each task that changes the behaviour a gotcha describes                                                                        |
| §11: not in 3a2                                                                                                                | none (the plan adds nothing it lists)                                                                                          |
| §12: defects found while scoping                                                                                               | filed in Plane after the plan; none is fixed here unless a task names it                                                       |

---

### Task 1: Address every template widget by page and tag

_Built and verified as commit `156dd84` on `plan/forms-step3a2`._

**Files:**

- Create: `backend/apps/forms/services/widgets.py`
- Create: `backend/apps/forms/tests/test_widgets.py`
- Modify: `CLAUDE.md`
- Modify: `backend/apps/forms/field_index.py`
- Modify: `backend/apps/forms/schema.py`
- Modify: `backend/apps/forms/services/fill_resolver.py`
- Modify: `backend/apps/forms/services/pdf_filler.py`
- Modify: `backend/apps/forms/tests/conftest.py`
- Modify: `backend/apps/forms/tests/pdf_readback.py`
- Modify: `backend/apps/forms/tests/test_checks.py`
- Modify: `backend/apps/forms/tests/test_fill_resolver.py`
- Modify: `backend/apps/forms/tests/test_form_101_schema.py`
- Modify: `backend/apps/forms/tests/test_form_107_schema.py`
- Modify: `data/forms/field_index/README.md`

**Interfaces:**

- Consumes:
  - `IndexWidget` and `load_index(template_filename: str) -> dict[str, tuple[IndexWidget, ...]]` (`backend/apps/forms/field_index.py`, `@lru_cache(maxsize=32)`), which reads `<FORM_INDEX_DIRECTORY>/<template stem>.index.json`. Every index row already carries `tag` (`"T1"`, `"T2"`, …, unique on its page) and `rect` (`[x0, y0, x1, y1]` measured from the page's top left, rounded to 0.1 pt), but `load_index` reads neither before this task.
  - The 17 AO templates in `settings.PDF_FORMS_DIRECTORY`, one per form type in `get_all_form_types()` (`apps.forms.registry`), each named by its schema's `template_filename`.
  - pypdf 6.13.1: `PdfReader`, `DictionaryObject.get_inherited`, and, in one test, `PdfWriter(clone_from=...)` and `TextStreamAppearance.from_text_annotation(writer, page, False, acro_form, field, annotation)` (`pypdf.generic._appearance_stream`, already pinned by `test_pdf_filler.py`, G12).
  - `qualified_name(field: DictionaryObject) -> str` and `field_of(widget: DictionaryObject) -> DictionaryObject`, defined before this task in `backend/apps/forms/services/pdf_filler.py`. `fill()` uses both, and `tests/pdf_readback.py`, `test_form_101_schema.py` and `test_form_107_schema.py` import them from `pdf_filler`.
  - `backend/apps/forms/schema.py`: `FieldSpec`, `FormSchema`, `load_schema(form_type)` (`@lru_cache`; it builds each binding with `FieldSpec(**field_data, ui=...)`, so a JSON key the dataclass lacks is a `TypeError`) and `validate_schema(schema, derivations, predicates) -> list[tuple[str, str]]`. `validate_form(form_type)` (`backend/apps/forms/checks.py`) prefixes each message with the form type and reports it as `forms.<code>`.
  - `resolve(schema, session) -> dict[str, str]` (`backend/apps/forms/services/fill_resolver.py`): its plain branch and its repeat-group branch, which resolves each column's list into `resolved_cols` before emitting rows.
  - For the tests: `test_checks.py`'s `schema_copy` fixture and its `_edit`, `_field`, `_ids` and `_errors` helpers; `test_fill_resolver.py`'s `session` fixture and its `_field(**kw)` and `_schema(fields)` helpers; `SOFAReport` and `SOFACreditorPayment` (`apps.intake.models`), which a `sofa.creditor_payments[].<attr>` binding reads.
- Produces:
  - `backend/apps/forms/services/widgets.py`:
    - `class TemplateMismatch(Exception)`: `__init__(self, template_filename: str, page: int)`, attributes `template_filename` and `page`, message `"<template filename> page <n>: the widgets don't match the field index one-to-one"`. It carries no filer data.
    - `@dataclass(frozen=True) class TemplateWidget`, fields in this order: `full_name: str`, `page: int` (1-based), `tag: str`, `rect: tuple[float, float, float, float]` (the index rect), `width: float` and `height: float` (of the PDF `/Rect`, unrounded), `kind: str` (`Text`, `CheckBox`, `RadioButton`, `ComboBox` or `Button`), `printed: bool`, `stacked: bool`, `states: tuple[str, ...]`, `options: tuple[str, ...]`, `font: str` (`""` for a box), `size: float` (0 = auto), `align: int` (the widget's own `/Q`, else its field's), `comb: bool`, `multiline: bool`, `max_len: int | None` (inherited), `margin: float`. Property `drawn` = `printed and not stacked`; property `key` = `f"{full_name}@{page}:{tag}"`.
    - `qualified_name` and `field_of`, moved here unchanged. Later tasks import them from `widgets`; `pdf_filler` imports them for `fill()`.
    - `def parse_key(key: str) -> tuple[str, int | None, str | None]`: `"name"` → `("name", None, None)`, `"name@2:T37"` → `("name", 2, "T37")`. A key with an empty name, or whose part after `@` isn't `<digits>:T<digits>`, raises `ValueError`.
    - `@lru_cache(maxsize=32) def template_widgets(template_filename: str) -> tuple[TemplateWidget, ...]`, ordered by page then tag number. Raises `TemplateMismatch`.
    - `def widget_for(template_filename: str, page: int, annotation: DictionaryObject, page_top: float) -> TemplateWidget`: the widget on `page` whose rect matches the annotation's `/Rect` within 0.6 pt. Pass `float(page.mediabox.top)`. Raises `TemplateMismatch` when no widget or more than one matches.
  - `IndexWidget` gains `tag: str` and `rect: tuple[float, float, float, float]`, right after `page`; `load_index` fills both.
  - `FieldSpec.tag: str | None = None`, after `choices` and before `ui`. A tagged binding fills only the widget with its `page` and `tag`.
  - `validate_schema` reports, as `(code, message)`:
    - `("E003", "'<name>': a full name in the field index contains '@'")` for each such index name, sorted;
    - `("E003", str(mismatch))` for a `TemplateMismatch`, after which that form's tag and E006 checks are skipped;
    - `("E003", "'<name>' has no drawn widget 'T<n>' on page <p>")` for a tag that isn't a drawn widget of that name on that page;
    - `("E006", "'<name>' is bound <k> times on page <p>")`, once per name, at the first drawn widget that two or more bindings would fill. This replaces `"'<name>' is bound <k> times"`.
  - `resolve()` emits a tagged binding under `f"{pdf_field}@{page}:{tag}"` in both branches, and keys `resolved_cols` the same way. An untagged binding keeps its full name as its key.
  - The `index_copy` fixture in `backend/apps/forms/tests/conftest.py`: it copies every `*.index.json` into `tmp_path`, points `FORM_INDEX_DIRECTORY` at the copy, clears the `load_index` and `template_widgets` caches before and after, and yields `edit(template_filename, change)`, where `change` mutates the list of row dicts.
  - Tests: `test_widgets.py` (new): `test_every_template_widget_matches_one_index_row`, `test_only_the_print_buttons_are_left_unprinted`, `test_schedule_d_page_2_has_eight_stacked_pairs`, `test_box_layout_is_read_as_the_template_sets_it`, `test_every_box_is_measured_the_way_pypdf_draws_it`, `test_text_boxes_start_at_the_templates_font_and_size`, `test_a_box_lists_its_on_states_and_a_combo_its_options`, `test_a_values_key_names_a_full_name_or_one_widget`, `test_a_malformed_values_key_is_refused` (7 cases), `test_an_annotation_the_template_lacks_is_a_mismatch` and `test_an_index_that_doesnt_match_its_template_one_to_one_is_refused` (3 cases). In `test_checks.py`: the `_text(pdf_field, page, tag)` and `_row(tag, row)` binding helpers, `test_a_tag_that_isnt_one_of_the_names_widgets_on_its_page_is_reported` (2 cases), `test_a_tag_on_the_second_of_a_stacked_pair_is_reported`, `test_a_tag_on_a_print_button_is_reported`, `test_two_tagged_bindings_on_different_widgets_of_one_name_pass`, `test_a_tagged_and_an_untagged_binding_of_one_name_are_reported`, `test_two_rows_of_a_group_that_would_fill_one_widget_are_reported` (2 cases), `test_rows_of_a_group_on_different_widgets_of_one_name_pass`, `test_a_template_that_doesnt_match_its_index_is_reported_not_raised` and `test_a_full_name_with_an_at_sign_in_the_index_is_reported`. In `test_fill_resolver.py`: `test_a_tagged_binding_resolves_under_its_widget_address` and `test_repeat_rows_of_a_shared_name_land_on_their_own_widgets`.
  - `CLAUDE.md`: "Schemas are checked at startup" gains the `tag` selector and the `@` check. `data/forms/field_index/README.md` lists `tag` among the row keys.

**Decisions already made in this task:**

- **No drawing changes here.** `fill()` still takes only full names and raises `UnknownField` on a `name@page:tag` key. No production schema uses a tag, so that can't happen yet. The `CLAUDE.md` sentence says so ("which `fill()` doesn't take yet"), and Task 3, which teaches `fill()` the key, drops that clause. `known_defects.json` stays `[]`.
- **A widget is matched to its index row by page and rectangle, within 0.6 pt** (spec §4.2, R17). The index is not in the PDF's widget order (14 of the 17 templates differ), so position is the only link. The annotation's `/Rect` is turned into the index's top-left coordinates as `page_top - y`, with `page_top = float(page.mediabox.top)`, so the flip is exact for any mediabox origin (R31). All 72 template pages are `[0 0 612 792]`, with no `/Rotate` and the cropbox equal to the mediabox, so no test can tell the top from the height, and only y is adjusted. The nearest index row that isn't a widget's own sits 0.62 pt away (Schedule D's stacked pairs), against the 0.6 pt tolerance; `test_every_template_widget_matches_one_index_row` fails if a regenerated index narrows that. A mutation to 0.7 pt made Schedule D's pairs collide and turned the test red.
- **The match is one-to-one in both directions, or `TemplateMismatch`.** Each annotation must hit exactly one row on its page, every row of the page must be hit, and no row may name a page past the template's last. The message names the template and page only, never filer data. A probe matched all 3,003 widgets of the 17 templates, and every matched row's `full_name` equals pypdf's qualified name of the widget's field.
- **`rect` is the index's rect; `width` and `height` come from the PDF `/Rect`, unrounded** (`abs(x1 - x0)`, `abs(y1 - y0)`), because that is what `from_text_annotation` measures and Task 2's fit check needs pypdf's exact width.
- **The layout is read where pypdf's `from_text_annotation` reads it**, so Task 2's size check and Task 3's drawing see the same numbers. `/DA` comes from `annotation.get_inherited("/DA", acro_form.get("/DA"))`, defaulting to `"/Helv 0 Tf 0 g"`, and the font and size are the two tokens before `Tf`. The comb bit (25) and multi-line bit (13) of `/Ff` and the border come from `field_of(annotation)`, never inherited, and `margin = max(/BS /W × (2 if /S is /B or /I else 1), 1)` (R5).
- **Two facts come from where the template puts them, which pypdf doesn't read.** Task 3 hands both over before drawing.
  - `max_len` is `annotation.get_inherited("/MaxLen")` (R4): Schedule D's two `account number` comb boxes (pages 1 and 3) keep `/MaxLen 4` on the parent field, and pypdf would otherwise print every digit in the first cell. Inherited `max_len` applies to every box, comb or not (R28). The 10 non-comb boxes that get a MaxLen only from a parent (Form 106C's two `page` boxes, MaxLen 2, and eight Form 107 date boxes, MaxLen 10) are unbound.
  - `align` is the widget's own `/Q`, else its field's (R26). Three A/B widgets set `/Q 2` on the kid widget alone: `24.2 Interest in an education IRA` T8 on page 7 (its sibling T7 has none) and both `undefined_166` widgets on page 10. No ancestor or AcroForm `/Q` exists, so this covers every case, and spec §3's 547 right-aligned boxes then hold.
- **One test compares every text and combo box with pypdf** (`test_every_box_is_measured_the_way_pypdf_draws_it`, review finding 4). It patches `TextStreamAppearance.__init__` with a stand-in that raises what `from_text_annotation` hands it, which observes pypdf without replacing our logic, and runs it on all 2,053 Text and 18 ComboBox widgets. The difference set must be exactly the R4 pair (`account number@1:T32`, `account number@3:T33`, `max_len`) and the R26 three (`24.2 Interest in an education IRA@7:T8`, `undefined_166@10:T34`, `undefined_166@10:T35`, `align`). It compares `max_len` only on comb boxes, since pypdf uses MaxLen only there. The test adds about 6 s to the suite.
- **What the census found.** Text sizes are 1,959 at 10 pt, 65 at 9, 19 at 12 and 10 auto; 51 boxes are comb and 94 multi-line. Every one of the 2,053 Text and 18 ComboBox widgets resolves `/Helv`, Form 107's two boxes that take `/DA` from the AcroForm included (R29; `facts-pypdf.md`'s "2,051" was wrong). Form 103B has 14 Text widgets with `/BS /W 3 /S /S` on the field, so their margin is 3; its two `Debtor.Name1` widgets carry `/BS /W 3` on the kid only, which pypdf ignores, so their margin is 1. Form 121's `Debtor1a.SSNum` is comb with MaxLen 11, and Schedule I's `Amount 2 Debtor 1` has `/Q 2`.
- **A box gets `font = ""` and `size = 0.0`.** `states` are read only for `CheckBox` and `RadioButton`: the keys of `/AP /N` other than `/Off` (for a Text or Button widget `/N` is a stream). `options` are the inherited `/Opt`, read only for `ComboBox`. `align`, `comb`, `multiline`, `max_len` and `margin` are read the same way for every kind; no `/Btn` field has the comb or multi-line bit. The states test uses Form 103B's `check 3`, whose `/N` has an `/Off` entry; Form 101's chapter boxes have none, so a test on them couldn't fail when `/Off` was kept.
- **`printed` is the annotation's Print flag, `/F` bit 3 (value 4).** Exactly the 67 `Button` widgets lack it. Schedule D's page 3 box `be notified for any debts in Part 1 do not fill out or submit this page.1` (T12) has `/F 36` (Print + NoView), so it prints, as it would from the fillable form. A mutation to `/F == 4` turned the test red on that box.
- **`stacked`: two widgets of one full name on one page whose overlap is more than half the smaller one's area; the higher tag number is stacked.** That gives exactly 8 pairs, all on Schedule D page 2 (`4_3` and the seven `_3` checkboxes of spec §4.2). They overlap 0.95; the next-highest same-name overlap on any template is 0.215. In a triple every widget but the lowest tag would be stacked; none exists.
- **`template_widgets` is the one cache, keyed by template filename** (G11), `@lru_cache(maxsize=32)`. `widget_for` scans it filtered by page instead of keeping a second cache: the reviewer timed 142 ms for every annotation of the 17 templates, 31 ms at worst (Form 107, 606 widgets). Building the map for all 17 templates costs about 1.4 s cold, once per process (`manage.py check`, `runserver`, `migrate` and a worker's first Generate). The ledger accepts it; Task 5's cold timing measures it.
- **`field_of` and `qualified_name` move into `widgets.py`.** `schema.py` now imports `widgets`, so if `widgets` imported them from `pdf_filler`, `schema → widgets → pdf_filler → schema` would be an import cycle. Their three test importers now import them from `widgets` (G5, review finding 3), so a later rewrite of `fill()` that stops using them can't strand them behind a re-export. `pdf_filler` imports both because `fill()` uses them.
- **`parse_key` refuses any malformed key with `ValueError`** (R31, review finding 5): after `@` the address must fully match `([0-9]+):(T[0-9]+)`, and the name must not be empty. It also refuses a tag that isn't `T<number>` (`"x@2:7"`) and `""`, since every index tag is `T<n>` and no full name is empty. Task 2's `check()` turns the `ValueError` into `UnknownField`; this task only raises it.
- **`FieldSpec.tag` goes after `choices` and before `ui`** (R15), defaulting to `None`, so every existing schema and every test that builds a `FieldSpec` keeps working unchanged.
- **The `@` check runs once per template, from the index**, before the bindings: `@` marks a widget's own key. No full name in the 17 indexes contains one.
- **A `TemplateMismatch` is reported as E003, not raised** (R27), as `validate_schema`'s own "an error, not a crash" convention does, and that form's tag and E006 checks are skipped. Skipping is required: with an empty widget map every tagged binding would also report E003, and E006 would go silent. The test adds a valid tagged binding (`4_3` T13) and expects exactly the one mismatch E003, so it fails if the skip breaks.
- **The tag check runs right after the name lookup**, against drawn widgets only, so a tag naming a print button or the second of a stacked pair is refused, and a tagged print button reports `[E003, E004]`. The E003 message says "no drawn widget"; it is a developer message, not one a filer reads.
- **E006 counts the drawn widgets each binding would fill** (R15, R30): an untagged binding fills every drawn widget of its name, a tagged one fills one, and any two bindings that would fill one drawn widget conflict, rows of one repeat group included. The old exemption for "the same repeat group, different rows" (the foundation spec's check 6) is dropped. It could never work, since `resolve()` wrote one key per name and rows overwrote each other, and with per-widget counting it was reached only by real collisions (review finding 1). No production schema has a repeat group. E006 is reported once per name, at the first widget filled twice, and its message now names the page; the existing `test_box_bound_twice_is_reported` checks only the id. One edge changes: a name with no drawn widget (only print buttons today) bound twice no longer gets E006, though E004 still fires for each binding.
- **`resolve()` keys `resolved_cols` by the output key too**, so two tagged cells of one name in a repeat group can bind different columns, which later Schedule D and A/B slots need.
- **`index_copy` lives in `apps/forms/tests/conftest.py`** because `test_widgets.py` and `test_checks.py` both use it, and it clears both caches before and after (G11). In this plan the fixture's two `template_widgets` lines go in with `widgets.py` (Step 4): until the module exists, importing it from `conftest.py` would stop every forms test from loading.
- **Every new test was shown red** (G4). The implementer ran each before the change, then mutated the production code one change at a time and restored it (`.claude/plan3a2-work/t01/mutate.py`), and every mutation turned its tests red but one. A margin factor of always 1 stays green, because no Text or ComboBox field has border style `/B` or `/I` (the only margin-2 widgets are 18 CheckBoxes and the 67 Buttons); the population test still pins every text box's margin, 103B's margin-3 boxes included. The mediabox-top flip can't be shown red either (see above). Two `parse_key` cases, `"x@a:T1"` and `"x@:T1"`, already raised through `int()` before the fix round.
- **Tests beyond tasks.md's list** each cover T1 behaviour that would otherwise have no test that fails (G4): the font and size census, states and options, `parse_key`, the `widget_for` mismatch, the three index-mismatch cases, the `@` test, the repeat shared-name test and the population test. The layout test was renamed in the fix round from `test_box_layout_is_read_where_pypdf_reads_it` to `test_box_layout_is_read_as_the_template_sets_it`, because alignment now departs from pypdf on purpose. None of spec §9's names is a T1 test: its widget tests read the drawn page, and they belong to Task 4.
- **Test data is synthetic (G2):** "SNAP", "WIC", "Acme" and "Beta". No SSN, phone number or person's name is added.
- **Left as found:** `_safe_debtor_attr` and the five dead Schedule I rules (backend survey §0.9) are pre-existing. `CLAUDE.md` doesn't say that a template/index mismatch is reported as E003 (the re-review's optional note).

- [ ] **Step 1: Write the failing tests**

```python file=backend/apps/forms/tests/test_widgets.py
"""
Every widget of each AO template has one address, its page and tag (spec §4.2).

The engine finds a template widget's index row by page and rectangle, so a value
meant for one of two same-name boxes lands on that box. The template's print
buttons never print, a stacked duplicate prints its value once, and each box is
laid out the way pypdf will draw it.
"""

from collections import Counter
from pathlib import Path

import pypdf
import pytest
from django.conf import settings
from pypdf.generic import ArrayObject, DictionaryObject, FloatObject, NameObject
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.forms.field_index import load_index
from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services.widgets import (
    TemplateMismatch,
    field_of,
    parse_key,
    qualified_name,
    template_widgets,
    widget_for,
)

SCHEDULE_D = "form_b106d.pdf"


def _templates():
    return sorted({load_schema(form_type).template_filename for form_type in get_all_form_types()})


def _all_widgets():
    return [widget for template in _templates() for widget in template_widgets(template)]


def _named(template, full_name):
    return [w for w in template_widgets(template) if w.full_name == full_name]


def test_every_template_widget_matches_one_index_row():
    total = 0
    for template in _templates():
        widgets = template_widgets(template)
        rows = [row for rows in load_index(template).values() for row in rows]
        assert sorted(w.key for w in widgets) == sorted(
            f"{row.full_name}@{row.page}:{row.tag}" for row in rows
        )
        reader = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template)
        found = []
        for number, page in enumerate(reader.pages, start=1):
            for annot in page.get("/Annots") or []:
                annotation = annot.get_object()
                if annotation.get("/Subtype") != "/Widget":
                    continue
                widget = widget_for(template, number, annotation, float(page.mediabox.top))
                # The rect is the only thing matched: the name proves it found the right row.
                assert widget.full_name == qualified_name(field_of(annotation))
                found.append(widget.key)
        assert sorted(found) == sorted(w.key for w in widgets)
        total += len(widgets)
    assert total == 3003


def test_only_the_print_buttons_are_left_unprinted():
    widgets = _all_widgets()
    unprinted = [w for w in widgets if not w.printed]
    assert len(unprinted) == 67
    assert unprinted == [w for w in widgets if w.kind == "Button"]
    # Flagged not to show on screen but to print: it prints, as from the fillable form.
    (hidden,) = _named(
        SCHEDULE_D, "be notified for any debts in Part 1 do not fill out or submit this page.1"
    )
    assert (hidden.page, hidden.printed, hidden.drawn) == (3, True, True)


SCHEDULE_D_STACKED = {
    "4_3",
    "Contingent_3",
    "Unliquidated_3",
    "Disputed_3",
    "An agreement you made such as mortgage or secured_3",
    "Statutory lien such as tax lien mechanics lien_3",
    "Judgment lien from a lawsuit_3",
    "Other including a right to offset_3",
}


def test_schedule_d_page_2_has_eight_stacked_pairs():
    # One widget of each pair, all of them Schedule D's, and none on any other template.
    stacked = [w for w in _all_widgets() if w.stacked]
    assert sorted(w.full_name for w in stacked) == sorted(SCHEDULE_D_STACKED)
    assert set(stacked) <= set(template_widgets(SCHEDULE_D))
    for name in SCHEDULE_D_STACKED:
        first, second = _named(SCHEDULE_D, name)
        # The pair's second widget by tag number is left out; the first one prints the value.
        assert (first.page, second.page) == (2, 2)
        assert int(first.tag[1:]) < int(second.tag[1:])
        assert (first.drawn, second.drawn) == (True, False)


def test_box_layout_is_read_as_the_template_sets_it():
    # Schedule D's account boxes keep their cell count (MaxLen) on the parent field.
    assert [(w.page, w.comb, w.max_len) for w in _named(SCHEDULE_D, "account number")] == [
        (1, True, 4),
        (3, True, 4),
    ]
    # Form 121 prints the SSN one digit to a cell.
    (ssn,) = _named("form_b121.pdf", "Debtor1a.SSNum")
    assert (ssn.comb, ssn.max_len) == (True, 11)
    # pypdf pads text by the field's border: 103B's 3 pt borders give a margin of 3.
    fee_waiver = template_widgets("form_b103b.pdf")
    assert len([w for w in fee_waiver if w.kind == "Text" and w.margin == 3]) == 14
    # A border on a kid widget alone is one pypdf never reads.
    assert [w.margin for w in _named("form_b103b.pdf", "Debtor.Name1")] == [1, 1]
    # Amounts are right-aligned ...
    (wages,) = _named("form_b106i.pdf", "Amount 2 Debtor 1")
    assert wages.align == 2
    # ... including where /Q 2 sits on the kid widget alone, which pypdf reads only from
    # the field: undefined_166's two widgets, and T8 but not T7 of 24.2's pair.
    assert [w.align for w in _named("form_b106ab.pdf", "undefined_166")] == [2, 2]
    ira = _named("form_b106ab.pdf", "24.2 Interest in an education IRA")
    assert [(w.tag, w.align) for w in ira] == [("T7", 0), ("T8", 2)]


class _Built(Exception):
    """What from_text_annotation handed TextStreamAppearance, raised by the stand-in below."""

    def __init__(self, layout, kwargs):
        self.layout = layout
        self.kwargs = kwargs


def test_every_box_is_measured_the_way_pypdf_draws_it(monkeypatch):
    # The stand-in records what pypdf would build each text and combo box from, then stops.
    def built(self, layout=None, *args, **kwargs):
        raise _Built(layout, kwargs)

    monkeypatch.setattr(TextStreamAppearance, "__init__", built)
    differences = set()
    compared = 0
    for template in _templates():
        writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
        acro_form = writer.root_object["/AcroForm"]
        for number, page in enumerate(writer.pages, start=1):
            for annot in page.get("/Annots") or []:
                annotation = annot.get_object()
                if annotation.get("/Subtype") != "/Widget":
                    continue
                widget = widget_for(template, number, annotation, float(page.mediabox.top))
                if widget.kind not in ("Text", "ComboBox"):
                    continue
                with pytest.raises(_Built) as seen:
                    TextStreamAppearance.from_text_annotation(
                        writer, page, False, acro_form, field_of(annotation), annotation
                    )
                layout, kwargs = seen.value.layout, seen.value.kwargs
                factor = 2 if layout.border_style in ("/B", "/I") else 1
                pypdf_reads = {
                    "font": kwargs["font_name"],
                    "size": float(kwargs["font_size"]),
                    "align": int(kwargs["alignment"]),
                    "comb": kwargs["is_comb"],
                    "multiline": kwargs["is_multiline"],
                    "max_len": kwargs["max_length"],
                    "margin": max(float(layout.border_width) * factor, 1),
                    "width": float(layout.rectangle.width),
                    "height": float(layout.rectangle.height),
                }
                ours = {
                    "font": widget.font,
                    "size": widget.size,
                    "align": widget.align,
                    "comb": widget.comb,
                    "multiline": widget.multiline,
                    "max_len": widget.max_len if widget.comb else None,  # pypdf's use of MaxLen
                    "margin": widget.margin,
                    "width": widget.width,
                    "height": widget.height,
                }
                differences |= {(widget.key, k) for k in ours if ours[k] != pypdf_reads[k]}
                compared += 1
    assert compared == 2053 + 18
    # Only what pypdf doesn't read from where the template puts it, and the drawing hands
    # over: MaxLen on the parent field (R4), /Q on the kid widget alone (R26).
    assert differences == {
        ("account number@1:T32", "max_len"),
        ("account number@3:T33", "max_len"),
        ("24.2 Interest in an education IRA@7:T8", "align"),
        ("undefined_166@10:T34", "align"),
        ("undefined_166@10:T35", "align"),
    }


def test_text_boxes_start_at_the_templates_font_and_size():
    text = [w for w in _all_widgets() if w.kind == "Text"]
    assert Counter((w.font, w.size) for w in text) == {
        ("/Helv", 10.0): 1959,
        ("/Helv", 9.0): 65,
        ("/Helv", 12.0): 19,
        ("/Helv", 0.0): 10,  # auto size
    }
    assert (sum(w.comb for w in text), sum(w.multiline for w in text)) == (51, 94)


def test_a_box_lists_its_on_states_and_a_combo_its_options():
    # 103B line 3's Yes and No boxes also draw an /Off appearance; it isn't a state to tick.
    line_3 = _named("form_b103b.pdf", "check 3")
    assert sorted(w.states for w in line_3) == [("/no",), ("/yes",)]
    assert {w.font for w in line_3} == {""}
    (district,) = _named("form_b121.pdf", "Bankruptcy District Information")
    assert "Northern District of Illinois" in district.options
    assert (district.font, district.states) == ("/Helv", ())


def test_a_values_key_names_a_full_name_or_one_widget():
    assert parse_key("Debtor 1") == ("Debtor 1", None, None)
    assert parse_key("Assistance 8f@2:T49") == ("Assistance 8f", 2, "T49")
    (_, second) = _named("form_b106i.pdf", "Assistance 8f")
    assert second.key == "Assistance 8f@2:T49"
    assert parse_key(second.key) == (second.full_name, second.page, second.tag)


@pytest.mark.parametrize("key", ["x@2", "x@a:T1", "x@2:", "x@:T1", "x@2:7", "@2:T1", ""])
def test_a_malformed_values_key_is_refused(key):
    with pytest.raises(ValueError):
        parse_key(key)


def test_an_annotation_the_template_lacks_is_a_mismatch():
    stray = DictionaryObject(
        {NameObject("/Rect"): ArrayObject([FloatObject(v) for v in (1, 1, 2, 2)])}
    )
    with pytest.raises(TemplateMismatch, match=r"form_b106d\.pdf page 2"):
        widget_for(SCHEDULE_D, 2, stray, 792.0)


def _drop_a_row(rows):
    rows.remove(next(row for row in rows if row["page"] == 2))


def _add_a_row_with_no_widget(rows):
    rows.append(
        {**next(row for row in rows if row["page"] == 2), "tag": "T999", "rect": [1, 1, 2, 2]}
    )


def _add_a_row_past_the_last_page(rows):
    rows.append({**next(row for row in rows if row["page"] == 2), "page": 9, "tag": "T1"})


@pytest.mark.parametrize(
    "change, page",
    [(_drop_a_row, 2), (_add_a_row_with_no_widget, 2), (_add_a_row_past_the_last_page, 9)],
)
def test_an_index_that_doesnt_match_its_template_one_to_one_is_refused(index_copy, change, page):
    index_copy(SCHEDULE_D, change)
    with pytest.raises(TemplateMismatch, match=rf"form_b106d\.pdf page {page}:"):
        template_widgets(SCHEDULE_D)
```

The widget tests read all 17 templates through the new map: 3,003 widgets matched one-to-one, the 67 print buttons the only unprinted widgets, the eight stacked pairs on Schedule D page 2, and each box's layout as the template sets it, compared box by box with what pypdf's `from_text_annotation` would build from. They also pin `parse_key`, `widget_for` on a stray annotation, and three ways an index can stop matching its template.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_checks.py b/backend/apps/forms/tests/test_checks.py
index 95ebf98..cb4aaea 100644
--- a/backend/apps/forms/tests/test_checks.py
+++ b/backend/apps/forms/tests/test_checks.py
@@ -168,6 +168,138 @@ def test_box_bound_twice_is_reported(schema_copy):
     assert _ids("form_121") == ["forms.E006"]


+def _text(pdf_field, page, tag):
+    """A constant text binding of one widget: the name's widget `tag` on `page`."""
+    return {
+        "pdf_field": pdf_field,
+        "type": "text",
+        "source": "constant",
+        "page": page,
+        "label": "",
+        "required": False,
+        "conditional_on": None,
+        "value": "x",
+        "rule": None,
+        "ingest_key": None,
+        "binding": None,
+        "repeat": None,
+        "repeat_capacity": None,
+        "row": None,
+        "legal_review": False,
+        "tag": tag,
+    }
+
+
+@pytest.mark.parametrize(
+    "page, tag",
+    [(1, "T7"), (2, "T3")],  # T7 is Debtor1.Last name; T3 is this name's widget, but on page 1
+)
+def test_a_tag_that_isnt_one_of_the_names_widgets_on_its_page_is_reported(schema_copy, page, tag):
+    _edit(
+        schema_copy,
+        "form_121",
+        lambda d: _field(d, "Debtor1.First name").update(page=page, tag=tag),
+    )
+    assert _errors("form_121") == [
+        (
+            "forms.E003",
+            f"form_121: 'Debtor1.First name' has no drawn widget {tag!r} on page {page}",
+        )
+    ]
+
+
+def test_a_tag_on_the_second_of_a_stacked_pair_is_reported(schema_copy):
+    # Schedule D page 2 lays 4_3's T14 over T13; only T13 prints a value.
+    _edit(schema_copy, "schedule_d", lambda d: d["fields"].append(_text("4_3", 2, "T14")))
+    assert _ids("schedule_d") == ["forms.E003"]
+    _edit(schema_copy, "schedule_d", lambda d: _field(d, "4_3").update(tag="T13"))
+    load_schema.cache_clear()
+    assert _ids("schedule_d") == []
+
+
+def test_a_tag_on_a_print_button_is_reported(schema_copy):
+    _edit(schema_copy, "form_101", lambda d: d["fields"].append(_text("Button.Print1", 9, "T20")))
+    assert _ids("form_101") == ["forms.E003", "forms.E004"]
+
+
+def test_two_tagged_bindings_on_different_widgets_of_one_name_pass(schema_copy):
+    # Schedule I prints "Assistance 8f" twice on page 2; each can take its own value.
+    def change(d):
+        d["fields"] += [_text("Assistance 8f", 2, "T36"), _text("Assistance 8f", 2, "T49")]
+
+    _edit(schema_copy, "schedule_i", change)
+    assert _ids("schedule_i") == []
+
+
+def test_a_tagged_and_an_untagged_binding_of_one_name_are_reported(schema_copy):
+    # The untagged binding fills both widgets, so T49 would get two values.
+    def change(d):
+        d["fields"] += [_text("Assistance 8f", 2, None), _text("Assistance 8f", 2, "T49")]
+
+    _edit(schema_copy, "schedule_i", change)
+    assert _errors("schedule_i") == [
+        ("forms.E006", "schedule_i: 'Assistance 8f' is bound 2 times on page 2")
+    ]
+
+
+def _row(tag, row):
+    """Row `row` of a repeat group of creditor payments, bound to Assistance 8f's widget `tag`."""
+    return {
+        **_text("Assistance 8f", 2, tag),
+        "source": "asked",
+        "value": None,
+        "binding": "sofa.creditor_payments[].creditor_name",
+        "repeat": "cp",
+        "repeat_capacity": 2,
+        "row": row,
+    }
+
+
+@pytest.mark.parametrize(
+    "first, second",
+    [(("T49", 1), ("T49", 2)), ((None, 1), ("T49", 2))],
+    ids=["two rows tagged to one widget", "an untagged and a tagged row"],
+)
+def test_two_rows_of_a_group_that_would_fill_one_widget_are_reported(schema_copy, first, second):
+    # A box shows one value: the later row would overwrite the earlier one.
+    _edit(schema_copy, "schedule_i", lambda d: d["fields"].extend([_row(*first), _row(*second)]))
+    assert _errors("schedule_i") == [
+        ("forms.E006", "schedule_i: 'Assistance 8f' is bound 2 times on page 2")
+    ]
+
+
+def test_rows_of_a_group_on_different_widgets_of_one_name_pass(schema_copy):
+    _edit(schema_copy, "schedule_i", lambda d: d["fields"].extend([_row("T36", 1), _row("T49", 2)]))
+    assert _ids("schedule_i") == []
+
+
+def test_a_template_that_doesnt_match_its_index_is_reported_not_raised(schema_copy, index_copy):
+    def move_a_row_off_its_widget(rows):
+        next(row for row in rows if row["page"] == 2)["rect"] = [1, 1, 2, 2]
+
+    index_copy("form_b106d.pdf", move_a_row_off_its_widget)
+    # The tag check needs the widget map, so it is skipped: this good tag adds no error.
+    _edit(schema_copy, "schedule_d", lambda d: d["fields"].append(_text("4_3", 2, "T13")))
+    assert _errors("schedule_d") == [
+        (
+            "forms.E003",
+            "schedule_d: form_b106d.pdf page 2: "
+            "the widgets don't match the field index one-to-one",
+        )
+    ]
+
+
+def test_a_full_name_with_an_at_sign_in_the_index_is_reported(index_copy):
+    # "@" separates a full name from a widget's page and tag in the resolved values.
+    def rename(rows):
+        next(row for row in rows if row["full_name"] == "Case number1")["full_name"] = "Case@1"
+
+    index_copy("form_b121.pdf", rename)
+    assert _errors("form_121") == [
+        ("forms.E003", "form_121: 'Case@1': a full name in the field index contains '@'")
+    ]
+
+
 @pytest.mark.parametrize(
     "change",
     [
PATCH
```

The startup-check tests add tagged bindings to copies of the real schemas: a tag on another name's widget or on the wrong page, on the second of a stacked pair, on a print button, two tags on different widgets of one name (passes), a tagged and an untagged binding of one name, rows of a repeat group that would fill one widget, rows on different widgets (passes), a template whose index no longer matches, and an index full name containing `@`.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_fill_resolver.py b/backend/apps/forms/tests/test_fill_resolver.py
index 1c09615..3bcaa49 100644
--- a/backend/apps/forms/tests/test_fill_resolver.py
+++ b/backend/apps/forms/tests/test_fill_resolver.py
@@ -259,6 +259,54 @@ def test_repeat_group_expands_rows(session):
     assert "Cred3" not in out  # only two rows of data


+def test_a_tagged_binding_resolves_under_its_widget_address(session):
+    # Schedule I prints "Assistance 8f" twice; a tag gives each widget a value of its own.
+    schema = _schema(
+        [
+            _field(pdf_field="Assistance 8f", page=2, tag="T36", value="SNAP"),
+            _field(pdf_field="Assistance 8f", page=2, tag="T49", value="WIC"),
+        ]
+    )
+    assert resolve(schema, session) == {
+        "Assistance 8f@2:T36": "SNAP",
+        "Assistance 8f@2:T49": "WIC",
+    }
+
+
+def test_repeat_rows_of_a_shared_name_land_on_their_own_widgets(session):
+    report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
+    for name, amt in [("Acme", "100.00"), ("Beta", "200.00")]:
+        SOFACreditorPayment.objects.create(
+            report=report, creditor_name=name, total_paid=Decimal(amt)
+        )
+
+    def cell(tag, row, attr):
+        return _field(
+            pdf_field="Line",
+            tag=tag,
+            source="asked",
+            repeat="cp",
+            repeat_capacity=2,
+            row=row,
+            binding=f"sofa.creditor_payments[].{attr}",
+        )
+
+    schema = _schema(
+        [
+            cell("T5", 1, "creditor_name"),
+            cell("T6", 1, "total_paid"),
+            cell("T9", 2, "creditor_name"),
+            cell("T10", 2, "total_paid"),
+        ]
+    )
+    assert resolve(schema, session) == {
+        "Line@1:T5": "Acme",
+        "Line@1:T6": "100.00",
+        "Line@1:T9": "Beta",
+        "Line@1:T10": "200.00",
+    }
+
+
 def test_repeat_overflow_raises(session):
     report = SOFAReport.objects.create(session=session, has_creditor_payments=True)
     for i in range(4):
PATCH
```

A tagged binding must resolve under its widget's key, and four tagged cells of one name in a repeat group must land on their own widgets with their own columns.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/conftest.py b/backend/apps/forms/tests/conftest.py
--- a/backend/apps/forms/tests/conftest.py
+++ b/backend/apps/forms/tests/conftest.py
@@ -1,18 +1,45 @@
 """Shared test fixtures for the forms app."""

+import json
+import shutil
 from datetime import date
 from decimal import Decimal
+from pathlib import Path

 import pytest
+from django.conf import settings as django_settings
 from django.contrib.auth import get_user_model
 from django.core.management import call_command
 from rest_framework.test import APIClient

 from apps.districts.models import District
+from apps.forms.field_index import load_index
 from apps.forms.models import GeneratedForm
 from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

 User = get_user_model()
+
+
+@pytest.fixture
+def index_copy(tmp_path, settings):
+    """
+    A writable copy of the field index. edit(template, change) rewrites one
+    template's rows. The caches built from an index are cleared before and after,
+    so the copy never poisons, or is poisoned by, the real index.
+    """
+    for path in Path(django_settings.FORM_INDEX_DIRECTORY).glob("*.index.json"):
+        shutil.copy(path, tmp_path)
+    settings.FORM_INDEX_DIRECTORY = tmp_path
+    load_index.cache_clear()
+
+    def edit(template_filename, change):
+        path = tmp_path / f"{Path(template_filename).stem}.index.json"
+        rows = json.loads(path.read_text())
+        change(rows)
+        path.write_text(json.dumps(rows))
+
+    yield edit
+    load_index.cache_clear()


 @pytest.fixture
PATCH
```

`index_copy` gives a test a writable copy of the field index. Step 4 adds the two lines that also clear the widget map's cache, once the module that holds it exists.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
cd backend && $PY -m pytest --tb=line -rN --continue-on-collection-errors apps/forms/tests/test_widgets.py apps/forms/tests/test_checks.py apps/forms/tests/test_fill_resolver.py -q -p no:cacheprovider 2>&1 | tail -40
```

Expected: FAIL — `13 failed, 53 passed, 1 error`. The widget tests can't be collected (`ModuleNotFoundError: No module named 'apps.forms.services.widgets'`). Twelve of the new tests stop on `TypeError: FieldSpec.__init__() got an unexpected keyword argument 'tag'`, and the `@` test gets no error where it wants one (`assert [] == [('forms.E003...ontains '@'")]`).

The twelve are the two resolver tests and every new startup-check test but the `@` one: each builds a tagged binding, directly or through `load_schema`, which passes every JSON key of a binding to `FieldSpec`. The existing tests in both files still pass.

- [ ] **Step 3: Give each index row its tag and rectangle**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/field_index.py b/backend/apps/forms/field_index.py
index 68f419e..74aaa63 100644
--- a/backend/apps/forms/field_index.py
+++ b/backend/apps/forms/field_index.py
@@ -36,6 +36,8 @@ class IndexWidget:

     full_name: str
     page: int
+    tag: str  # T1, T2, …: unique on its page
+    rect: tuple[float, float, float, float]  # x0, y0, x1, y1 from the page's top left
     type: str  # Text | CheckBox | RadioButton | ComboBox | Button
     on_state: str | None
     basis: str
@@ -67,6 +69,8 @@ def load_index(template_filename: str) -> dict[str, tuple[IndexWidget, ...]]:
             IndexWidget(
                 full_name=row["full_name"],
                 page=row["page"],
+                tag=row["tag"],
+                rect=tuple(float(v) for v in row["rect"]),
                 type=row["type"],
                 on_state=row["on_state"],
                 basis=row["basis"],
diff --git a/data/forms/field_index/README.md b/data/forms/field_index/README.md
index eebab63..c2ef100 100644
--- a/data/forms/field_index/README.md
+++ b/data/forms/field_index/README.md
@@ -4,7 +4,7 @@ Ground truth for every fillable box on the 17 AO templates in `../pdfs/` that th

 ## Files

-- `<template-stem>.index.json`: one row per widget. Each row has `full_name`, `page`, `rect`, `type`, `on_state`, `tooltip`, `line`, `label`, `column`, `kind`, `option_text` and `basis`.
+- `<template-stem>.index.json`: one row per widget. Each row has `full_name`, `page`, `tag`, `rect`, `type`, `on_state`, `tooltip`, `line`, `label`, `column`, `kind`, `option_text` and `basis`.
 - `audit/<schema>.audit.json`: every schema binding checked against the index. For each binding it records the field it targets, what it writes, its verdicts and the correct target.
 - `audit/<schema>.unbound.json`: boxes a complete filing needs that no binding fills.
 - `audit/verification.json`: an independent re-check of every non-correct verdict, plus a sample of correct ones. **Where it disagrees with a per-schema audit file, `verification.json` wins.** It modifies 13 verdicts and adds 18 the audit files mark correct.
PATCH
```

`IndexWidget` gains the row's `tag` and `rect`, which every index file already holds (R16; only `load_index` constructs it). The README lists `tag` among the row keys.

- [ ] **Step 4: Map every template widget**

```python file=backend/apps/forms/services/widgets.py
"""
Template widgets: every widget of an AO template, addressed by page and tag.

The field index (apps.forms.field_index) gives each widget a tag that is unique
on its page and its rectangle, but its rows are not in the PDF's widget order.
template_widgets() therefore matches each /Widget annotation to its index row
by page and rectangle, and records what drawing the widget needs: whether it
prints, whether it is the second of a stacked pair, and its text layout as
pypdf's TextStreamAppearance.from_text_annotation reads it.

A key in the resolved values is a full name, which fills every drawn widget of
that name, or "<full name>@<page>:<tag>", which fills that one widget.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import pypdf
from django.conf import settings
from pypdf.generic import DictionaryObject

from apps.forms.field_index import IndexWidget, load_index

# The index rounds rects to 0.1 pt; Schedule D's stacked pairs sit 0.62 pt apart.
_TOLERANCE = 0.6
_PRINT = 1 << 2  # annotation flag bit 3
_MULTILINE = 1 << 12  # field flag bit 13
_COMB = 1 << 24  # field flag bit 25
_ADDRESS = re.compile(r"([0-9]+):(T[0-9]+)")  # "<page>:<tag>" after a key's "@"


class TemplateMismatch(Exception):
    """A template's widgets and its index rows don't match one-to-one."""

    def __init__(self, template_filename: str, page: int):
        self.template_filename = template_filename
        self.page = page
        super().__init__(
            f"{template_filename} page {page}: the widgets don't match the field index one-to-one"
        )


@dataclass(frozen=True)
class TemplateWidget:
    """One widget of a template: its index address, and what pypdf reads to draw it."""

    full_name: str
    page: int  # 1-based
    tag: str  # the index tag, unique on its page
    rect: tuple[float, float, float, float]  # the index rect, from the page's top left
    width: float  # of the PDF /Rect, as pypdf measures it
    height: float
    kind: str  # the index type: Text | CheckBox | RadioButton | ComboBox | Button
    printed: bool  # the annotation's Print flag
    stacked: bool  # the second widget of a stacked same-name pair
    states: tuple[str, ...]  # a box's on-states, as pypdf names them ("/Chapter 7")
    options: tuple[str, ...]  # a combo's /Opt
    font: str  # the /DA font name ("/Helv"); "" for a box
    size: float  # the /DA font size; 0 = auto
    # The template's alignment (0 left, 1 centre, 2 right): the widget's own /Q, else its
    # field's. pypdf reads only the field's, so the drawing hands this one over.
    align: int
    comb: bool
    multiline: bool
    max_len: int | None  # /MaxLen, on the widget or inherited from its parents
    margin: float  # pypdf's border margin

    @property
    def drawn(self) -> bool:
        """A value bound to this widget's name prints here."""
        return self.printed and not self.stacked

    @property
    def key(self) -> str:
        """This widget's own key in the resolved values."""
        return f"{self.full_name}@{self.page}:{self.tag}"


def qualified_name(field: DictionaryObject) -> str:
    """The field's full name: every /T up the /Parent chain, joined with dots."""
    parts = []
    node = field
    while node is not None:
        if "/T" in node:
            parts.append(str(node["/T"]))
        parent = node.get("/Parent")
        node = parent.get_object() if parent is not None else None
    return ".".join(reversed(parts))


def field_of(widget: DictionaryObject) -> DictionaryObject:
    """The field a widget belongs to: the widget itself when it carries /T, else its parent."""
    return widget if "/T" in widget else widget["/Parent"].get_object()


def parse_key(key: str) -> tuple[str, int | None, str | None]:
    """
    Split a values key: "name" → ("name", None, None); "name@2:T37" → ("name", 2, "T37").

    Raises:
        ValueError: the key has no name, or its address isn't "<page>:T<number>".
    """
    name, at, address = key.partition("@")
    match = _ADDRESS.fullmatch(address)
    if not name or (at and match is None):
        raise ValueError(f"{key!r} is neither a full name nor <full name>@<page>:<tag>")
    if not at:
        return key, None, None
    return name, int(match[1]), match[2]


def _top_left(annotation: DictionaryObject, page_top: float) -> tuple[float, ...]:
    """An annotation's /Rect in the index's coordinates: y measured down from the page's top."""
    x0, y0, x1, y1 = (float(v) for v in annotation["/Rect"])
    return (min(x0, x1), page_top - max(y0, y1), max(x0, x1), page_top - min(y0, y1))


def _same_rect(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return all(abs(p - q) <= _TOLERANCE for p, q in zip(a, b, strict=True))


def _area(rect: tuple[float, ...]) -> float:
    return max(rect[2] - rect[0], 0) * max(rect[3] - rect[1], 0)


def _stacked(rows: list[IndexWidget]) -> set[tuple[int, str]]:
    """
    (page, tag) of the second widget of each stacked pair: two widgets with one full
    name on one page whose overlap is more than half the smaller one's area.
    """
    by_name: dict[tuple[int, str], list[IndexWidget]] = {}
    for row in rows:
        by_name.setdefault((row.page, row.full_name), []).append(row)
    stacked = set()
    for group in by_name.values():
        for a, b in combinations(group, 2):
            overlap = (
                max(a.rect[0], b.rect[0]),
                max(a.rect[1], b.rect[1]),
                min(a.rect[2], b.rect[2]),
                min(a.rect[3], b.rect[3]),
            )
            if _area(overlap) > min(_area(a.rect), _area(b.rect)) / 2:
                second = max(a, b, key=lambda row: int(row.tag[1:]))
                stacked.add((second.page, second.tag))
    return stacked


def _template_widget(
    row: IndexWidget, annotation: DictionaryObject, acro_form: DictionaryObject, stacked: bool
) -> TemplateWidget:
    """A widget from its index row and its annotation, read where pypdf reads it but /Q."""
    field = field_of(annotation)
    font, size = "", 0.0
    if row.type in ("Text", "ComboBox"):
        appearance = annotation.get_inherited("/DA", acro_form.get("/DA"))
        da = str(appearance.get_object()) if appearance else "/Helv 0 Tf 0 g"
        parts = da.split()
        tf = parts.index("Tf")
        font, size = parts[tf - 2], float(parts[tf - 1])
    states: tuple[str, ...] = ()
    if row.type in ("CheckBox", "RadioButton"):
        states = tuple(str(state) for state in annotation["/AP"]["/N"] if state != "/Off")
    options: tuple[str, ...] = ()
    if row.type == "ComboBox":
        options = tuple(str(option) for option in field.get_inherited("/Opt", []))
    # pypdf reads /Ff, /Q and /BS from the field, never inherited or from a kid widget.
    # Three A/B widgets set /Q on the kid alone, so align takes the widget's own first.
    flags = int(field.get("/Ff", 0))
    border = field["/BS"] if "/BS" in field else DictionaryObject()
    factor = 2 if border.get("/S", "/S") in ("/B", "/I") else 1
    max_len = annotation.get_inherited("/MaxLen")
    x0, y0, x1, y1 = (float(v) for v in annotation["/Rect"])
    return TemplateWidget(
        full_name=row.full_name,
        page=row.page,
        tag=row.tag,
        rect=row.rect,
        width=abs(x1 - x0),
        height=abs(y1 - y0),
        kind=row.type,
        printed=bool(int(annotation.get("/F", 0)) & _PRINT),
        stacked=stacked,
        states=states,
        options=options,
        font=font,
        size=size,
        align=int(annotation.get("/Q", field.get("/Q", 0))),
        comb=bool(flags & _COMB),
        multiline=bool(flags & _MULTILINE),
        max_len=None if max_len is None else int(max_len),
        margin=max(float(border.get("/W", 1)) * factor, 1.0),
    )


@lru_cache(maxsize=32)
def template_widgets(template_filename: str) -> tuple[TemplateWidget, ...]:
    """
    Every widget of a template, ordered by page then tag number.

    Each /Widget annotation is matched to the index row on its page whose rect
    agrees with its /Rect within 0.6 pt, y measured down from the page's mediabox top.

    Raises:
        TemplateMismatch: on some page the widgets and the index rows don't
            match one-to-one.
    """
    rows_by_page: dict[int, list[IndexWidget]] = {}
    for rows in load_index(template_filename).values():
        for row in rows:
            rows_by_page.setdefault(row.page, []).append(row)
    stacked = _stacked([row for rows in rows_by_page.values() for row in rows])

    reader = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template_filename)
    root = reader.root_object
    acro_form = root["/AcroForm"] if "/AcroForm" in root else DictionaryObject()
    for number in rows_by_page:
        if number > len(reader.pages):
            raise TemplateMismatch(template_filename, number)

    widgets = []
    for number, page in enumerate(reader.pages, start=1):
        rows = rows_by_page.get(number, [])
        top = float(page.mediabox.top)
        matched = []
        for annot in page.get("/Annots") or []:
            annotation = annot.get_object()
            if annotation.get("/Subtype") != "/Widget":
                continue
            rect = _top_left(annotation, top)
            hits = [row for row in rows if _same_rect(rect, row.rect)]
            if len(hits) != 1:
                raise TemplateMismatch(template_filename, number)
            matched.append((hits[0], annotation))
        if len(matched) != len(rows) or {r.tag for r, _ in matched} != {r.tag for r in rows}:
            raise TemplateMismatch(template_filename, number)
        widgets += [
            _template_widget(row, annotation, acro_form, (row.page, row.tag) in stacked)
            for row, annotation in matched
        ]
    return tuple(sorted(widgets, key=lambda w: (w.page, int(w.tag[1:]))))


def widget_for(
    template_filename: str, page: int, annotation: DictionaryObject, page_top: float
) -> TemplateWidget:
    """
    The template widget an annotation on `page` of a copy of the template is: the
    one whose rect matches the annotation's /Rect within 0.6 pt. `page_top` is the
    page's mediabox top (`float(page.mediabox.top)`).

    Raises:
        TemplateMismatch: no widget on that page matches, or more than one does.
    """
    rect = _top_left(annotation, page_top)
    hits = [
        w
        for w in template_widgets(template_filename)
        if w.page == page and _same_rect(rect, w.rect)
    ]
    if len(hits) != 1:
        raise TemplateMismatch(template_filename, page)
    return hits[0]
```

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/conftest.py b/backend/apps/forms/tests/conftest.py
--- a/backend/apps/forms/tests/conftest.py
+++ b/backend/apps/forms/tests/conftest.py
@@ -15,6 +15,7 @@
 from apps.districts.models import District
 from apps.forms.field_index import load_index
 from apps.forms.models import GeneratedForm
+from apps.forms.services.widgets import template_widgets
 from apps.intake.models import DebtorInfo, IncomeInfo, IntakeSession

 User = get_user_model()
@@ -31,6 +32,7 @@
         shutil.copy(path, tmp_path)
     settings.FORM_INDEX_DIRECTORY = tmp_path
     load_index.cache_clear()
+    template_widgets.cache_clear()

     def edit(template_filename, change):
         path = tmp_path / f"{Path(template_filename).stem}.index.json"
@@ -40,6 +42,7 @@

     yield edit
     load_index.cache_clear()
+    template_widgets.cache_clear()


 @pytest.fixture
PATCH
```

`template_widgets()` opens a template once, matches each `/Widget` annotation to its index row by page and rectangle, and records what drawing will need: whether the widget prints, whether it is the second of a stacked pair, and its layout as pypdf reads it, with MaxLen inherited and the widget's own `/Q` first (§4.2, R4, R17, R26). `widget_for()` finds the widget for an annotation of a copy of the template, and `parse_key()` splits a values key. `qualified_name` and `field_of` now live here. `index_copy` now also clears the map's cache.

- [ ] **Step 5: Import the moved helpers from their new home**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
index 6c4ee3c..da43d88 100644
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -22,6 +22,7 @@ from pypdf.generic import DictionaryObject, NameObject, TextStringObject
 from pypdf.generic._appearance_stream import TextStreamAppearance

 from apps.forms.schema import load_schema
+from apps.forms.services.widgets import field_of, qualified_name


 class UnknownField(Exception):
@@ -50,23 +51,6 @@ class InvalidFieldValue(Exception):
         super().__init__(f"{form_type}: {name!r} can't take this value")


-def qualified_name(field: DictionaryObject) -> str:
-    """The field's full name: every /T up the /Parent chain, joined with dots."""
-    parts = []
-    node = field
-    while node is not None:
-        if "/T" in node:
-            parts.append(str(node["/T"]))
-        parent = node.get("/Parent")
-        node = parent.get_object() if parent is not None else None
-    return ".".join(reversed(parts))
-
-
-def field_of(widget: DictionaryObject) -> DictionaryObject:
-    """The field a widget belongs to: the widget itself when it carries /T, else its parent."""
-    return widget if "/T" in widget else widget["/Parent"].get_object()
-
-
 class PDFFormFiller:
     """Fill AO court PDF templates with field values and return bytes."""

diff --git a/backend/apps/forms/tests/pdf_readback.py b/backend/apps/forms/tests/pdf_readback.py
index 2ecbbe5..c6976c5 100644
--- a/backend/apps/forms/tests/pdf_readback.py
+++ b/backend/apps/forms/tests/pdf_readback.py
@@ -5,7 +5,7 @@ from io import BytesIO

 import pypdf

-from apps.forms.services.pdf_filler import field_of, qualified_name
+from apps.forms.services.widgets import field_of, qualified_name


 @dataclass(frozen=True)
diff --git a/backend/apps/forms/tests/test_form_101_schema.py b/backend/apps/forms/tests/test_form_101_schema.py
index e2c12cf..0bac23c 100644
--- a/backend/apps/forms/tests/test_form_101_schema.py
+++ b/backend/apps/forms/tests/test_form_101_schema.py
@@ -18,7 +18,8 @@ from django.contrib.auth import get_user_model
 from apps.districts.models import District
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
-from apps.forms.services.pdf_filler import PDFFormFiller, field_of, qualified_name
+from apps.forms.services.pdf_filler import PDFFormFiller
+from apps.forms.services.widgets import field_of, qualified_name
 from apps.intake.models import (
     AssetInfo,
     DebtInfo,
diff --git a/backend/apps/forms/tests/test_form_107_schema.py b/backend/apps/forms/tests/test_form_107_schema.py
index ff006f1..8e1bb55 100644
--- a/backend/apps/forms/tests/test_form_107_schema.py
+++ b/backend/apps/forms/tests/test_form_107_schema.py
@@ -23,7 +23,8 @@ from apps.districts.models import District
 from apps.forms.field_index import index_path
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
-from apps.forms.services.pdf_filler import PDFFormFiller, field_of, qualified_name
+from apps.forms.services.pdf_filler import PDFFormFiller
+from apps.forms.services.widgets import field_of, qualified_name
 from apps.forms.tests.pdf_readback import read_widgets
 from apps.intake.models import DebtorInfo, IntakeSession, SOFAReport

PATCH
```

`pdf_filler.py` drops its own copies of the two helpers and imports them from `widgets`, since `fill()` uses both; the three test modules import them from `widgets` directly (G5).

- [ ] **Step 6: Let a binding name one widget, and check it at startup**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/schema.py b/backend/apps/forms/schema.py
index 5ab8641..7c86e1d 100644
--- a/backend/apps/forms/schema.py
+++ b/backend/apps/forms/schema.py
@@ -18,6 +18,7 @@ import pypdf
 from django.conf import settings

 from apps.forms.field_index import export_state, load_index
+from apps.forms.services.widgets import TemplateMismatch, TemplateWidget, template_widgets


 @dataclass(frozen=True)
@@ -59,6 +60,8 @@ class FieldSpec:
     # checkbox/radio only: normalised answer → export state. {"true": state} is
     # a single box; {} means not mapped yet, and the binding emits nothing.
     choices: dict[str, str] | None = None
+    # One widget of pdf_field: its index tag on `page`. None fills every widget of the name.
+    tag: str | None = None
     ui: UIFieldSpec | None = None


@@ -136,6 +139,20 @@ def validate_schema(

     index = load_index(schema.template_filename)
     template_fields = pypdf.PdfReader(BytesIO(template)).get_fields() or {}
+    # "@" marks a widget's own key in the resolved values: "<full name>@<page>:<tag>".
+    for name in sorted(name for name in index if "@" in name):
+        errors.append(("E003", f"{name!r}: a full name in the field index contains '@'"))
+    # A template that has drifted from its index is an error, not a crash. The tag and
+    # E006 checks need the widget map, so they are skipped for this form.
+    try:
+        widget_map: tuple[TemplateWidget, ...] | None = template_widgets(schema.template_filename)
+    except TemplateMismatch as mismatch:
+        errors.append(("E003", str(mismatch)))
+        widget_map = None
+    drawn: dict[str, list[TemplateWidget]] = {}
+    for widget in widget_map or ():
+        if widget.drawn:
+            drawn.setdefault(widget.full_name, []).append(widget)
     seen: dict[str, list[FieldSpec]] = {}

     for f in schema.fields:
@@ -143,6 +160,14 @@ def validate_schema(
         if widgets is None:
             errors.append(("E003", f"{f.pdf_field!r} is not a full name in the field index"))
             continue
+        if (
+            f.tag is not None
+            and widget_map is not None
+            and not any((w.page, w.tag) == (f.page, f.tag) for w in drawn.get(f.pdf_field, ()))
+        ):
+            errors.append(
+                ("E003", f"{f.pdf_field!r} has no drawn widget {f.tag!r} on page {f.page}")
+            )
         seen.setdefault(f.pdf_field, []).append(f)

         types = {w.type for w in widgets}
@@ -189,8 +214,16 @@ def validate_schema(
             errors.append(("E007", f"repeat group {f.repeat!r} has no repeat_capacity"))

     for name, bindings in seen.items():
-        rows = {(b.repeat, b.row) for b in bindings}
-        same_group = len({b.repeat for b in bindings}) == 1 and bindings[0].repeat is not None
-        if len(bindings) > 1 and not (same_group and len(rows) == len(bindings)):
-            errors.append(("E006", f"{name!r} is bound {len(bindings)} times"))
+        # A binding fills every drawn widget of its name, or with a tag only that one. A
+        # widget shows one value, so two bindings that would fill it conflict, rows of
+        # one repeat group included.
+        for widget in drawn.get(name, ()):
+            fills = [
+                b for b in bindings if b.tag is None or (b.page, b.tag) == (widget.page, widget.tag)
+            ]
+            if len(fills) > 1:
+                errors.append(
+                    ("E006", f"{name!r} is bound {len(fills)} times on page {widget.page}")
+                )
+                break
     return errors
PATCH
```

`FieldSpec` gains `tag` (R15). `validate_schema` refuses an index full name containing `@`, reports a template that no longer matches its index as E003 and skips that form's widget-level checks (R27), refuses a tag that isn't a drawn widget of its name on its page, and counts E006 per drawn widget with no repeat-group exemption (R30).

- [ ] **Step 7: Resolve a tagged binding under its widget's key**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/fill_resolver.py b/backend/apps/forms/services/fill_resolver.py
index 3dad0a5..452a718 100644
--- a/backend/apps/forms/services/fill_resolver.py
+++ b/backend/apps/forms/services/fill_resolver.py
@@ -1,5 +1,6 @@
 """
-Fill resolver — turns a FormSchema + IntakeSession into {pdf_field: str}.
+Fill resolver — turns a FormSchema + IntakeSession into {pdf_field: str}, or, for a
+binding with a tag, {"<pdf_field>@<page>:<tag>": str}.

 Source priority is encoded per-field in the schema (constant/derived/asked/
 ingested/signature). This module resolves ``binding`` references; resolve()
@@ -111,6 +112,13 @@ def _scalar_value(
     return None


+def _key(field: FieldSpec) -> str:
+    """The values key a binding fills: its full name, or "<name>@<page>:<tag>" for one widget."""
+    if field.tag is None:
+        return field.pdf_field
+    return f"{field.pdf_field}@{field.page}:{field.tag}"
+
+
 def _unmapped(field: FieldSpec) -> bool:
     """A checkbox or radio binding whose choices are not mapped yet emits nothing."""
     return field.type in ("checkbox", "radio") and not field.choices
@@ -165,7 +173,7 @@ def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
             continue
         emitted = _emit(f, _scalar_value(f, session, ingested_cache=_ingested_cache))
         if emitted is not None:
-            out[f.pdf_field] = emitted
+            out[_key(f)] = emitted

     # Repeat groups. An unmapped box is dropped before any lookup, so its binding
     # is never resolved and never counts toward RepeatOverflow (spec §5.1).
@@ -178,9 +186,7 @@ def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:

     for group_name, fields in groups.items():
         capacity = fields[0].repeat_capacity or 0
-        resolved_cols = {
-            f.pdf_field: resolve_binding(f.binding, session) for f in fields if f.binding
-        }
+        resolved_cols = {_key(f): resolve_binding(f.binding, session) for f in fields if f.binding}
         actual = max(
             (len(v) for v in resolved_cols.values() if isinstance(v, list)),
             default=0,
@@ -191,14 +197,14 @@ def resolve(schema: FormSchema, session: IntakeSession) -> dict[str, str]:
             if f.legal_review and f.source != "asked":
                 continue
             if f.binding:
-                vals = resolved_cols.get(f.pdf_field)
+                vals = resolved_cols.get(_key(f))
                 if isinstance(vals, list) and f.row and f.row <= len(vals):
                     emitted = _emit(f, str(vals[f.row - 1]))
                     if emitted is not None:
-                        out[f.pdf_field] = emitted
+                        out[_key(f)] = emitted
             else:
                 emitted = _emit(f, _scalar_value(f, session, ingested_cache=_ingested_cache))
                 if emitted is not None:
-                    out[f.pdf_field] = emitted
+                    out[_key(f)] = emitted

     return out
PATCH
```

`_key()` gives a tagged binding the key `<full name>@<page>:<tag>`, in the plain branch and the repeat branch, where `resolved_cols` uses it too, so cells of one name can bind different columns.

- [ ] **Step 8: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
cd backend && $PY -m pytest --tb=line -rN --continue-on-collection-errors apps/forms/tests/test_widgets.py apps/forms/tests/test_checks.py apps/forms/tests/test_fill_resolver.py -q -p no:cacheprovider 2>&1 | tail -40
```

Expected: `85 passed`. The widget file adds its 19 cases to the 66 that ran in Step 2.

- [ ] **Step 9: Say in CLAUDE.md what a tag does**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 411b80c..60c06d5 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -34,7 +34,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
 - **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
-- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
+- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`, which `fill()` doesn't take yet: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
 - **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. It has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
 - **Blank, not 0.00, on the forms** — a derivation must not turn a missing input into 0.00: a line DigniFi never asks (interest, payroll deductions, priority, a spouse's column) and an income source left empty print blank, and a source typed as $0 prints 0.00. A total counts an unasked line as zero and still prints. The 13 expense amounts are stored as $0 when left empty, so an expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0, while the totals (Schedule J 22a and 22c, 106Sum line 5, 103B line 6) still print. One exception remains: with no `ExpenseInfo` row at all, those totals and Schedule J 23b print 0.00, and 23c prints the income less 0.00 (`_total_monthly_expenses`, the one function behind all of them; any other error fails the form). Signature lines and signing dates stay blank for wet ink (`test_signing_lines.py`). No production schema has a repeat group: Form 107's prior-income and creditor-payment rows came off until steps 3–4 ask what they need, and the SOFA answers stay stored. The engine (`repeat`, `RepeatOverflow` and its 422) stays for later steps; only synthetic tests reach it.
PATCH
```

- [ ] **Step 10: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2198 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  397 passed (397)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

That is 32 more backend cases than before this task: 19 in `test_widgets.py`, 11 in `test_checks.py` and 2 in `test_fill_resolver.py`. The 25 skips are the Postgres-only tests under sqlite; the next command runs them against the Postgres database named by `DATABASE_URL` in `.claude/forms-step3a2.env`, as CI's "Run the Postgres-only tests" step does. This task touches no locking, so they pass unchanged.

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

This task changes no page flow and no drawing, so the journeys don't run.

- [ ] **Step 11: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/services/widgets.py \
  backend/apps/forms/tests/test_widgets.py \
  CLAUDE.md \
  backend/apps/forms/field_index.py \
  backend/apps/forms/schema.py \
  backend/apps/forms/services/fill_resolver.py \
  backend/apps/forms/services/pdf_filler.py \
  backend/apps/forms/tests/conftest.py \
  backend/apps/forms/tests/pdf_readback.py \
  backend/apps/forms/tests/test_checks.py \
  backend/apps/forms/tests/test_fill_resolver.py \
  backend/apps/forms/tests/test_form_101_schema.py \
  backend/apps/forms/tests/test_form_107_schema.py \
  data/forms/field_index/README.md
git commit -F - <<'MSG'
feat(forms): address each template widget by page and tag

Every later part of the drawing engine finds a template's widgets
through one map, built by apps/forms/services/widgets.py.
template_widgets() matches each /Widget annotation to its field-index
row by page and rect: the /Rect is turned into top-left coordinates,
y measured down from the page's mediabox top, and must agree within
0.6 pt. Anything but a one-to-one match raises TemplateMismatch,
naming the template and page. All 17 templates match on all 3,003
widgets.

Each TemplateWidget records what drawing it will need. Most of it is
read where pypdf's TextStreamAppearance reads it: the /DA font and
size (inherited), and comb, multi-line and the border margin from the
field. A test compares every text and combo box with what
from_text_annotation hands TextStreamAppearance. Two facts are taken
from where the template puts them, which pypdf doesn't read, and the
drawing will hand them over:
- MaxLen comes from the widget or its parents, since Schedule D's
  account boxes keep it on the parent;
- the alignment is the widget's own /Q, else its field's, since three
  A/B widgets set it on the kid alone.
A box lists its on-states and a combo its options. The map also says
whether a widget prints (all but the 67 print, save, reset and attach
buttons do) and whether it is the second of one of the eight stacked
same-name pairs on Schedule D page 2, which the drawing will leave
out. widget_for() finds the widget for an annotation of a copy of the
template. parse_key() splits a values key and raises ValueError on a
malformed one.

A schema binding may now give a tag. It fills only that widget, and
resolve() emits it under "<full name>@<page>:<tag>". The startup check
refuses (E003) a tag that isn't a drawn widget of that name on that
page, and an index full name containing "@". A template whose widgets
don't match its index is reported as E003 instead of stopping the
check, and that form's tag and E006 checks are skipped. E006 now
counts the widgets each binding would fill: any two bindings that
would fill one drawn widget conflict, rows of one repeat group
included, so a tagged and an untagged binding of one name conflict
while tagged bindings on different widgets pass. The old exemption
for rows of one group could never work, since resolve() wrote one key
per name. No production schema uses a tag or a repeat group, and the
filler draws as before.

IndexWidget gains tag and rect. field_of() and qualified_name() move
from pdf_filler to widgets, because the schema check now imports
widgets; their importers now import them from widgets.
MSG
git status --short
```

### Task 2: Check what each box prints, and refuse what it can't

_Built and verified as commit `647e21b` on `plan/forms-step3a2`._

**Files:**

- Create: `backend/apps/forms/services/text_fit.py`
- Create: `backend/apps/forms/tests/test_check.py`
- Create: `backend/apps/forms/tests/test_rule_fixes.py`
- Modify: `backend/apps/forms/services/derivations.py`
- Modify: `backend/apps/forms/services/fill_resolver.py`
- Modify: `backend/apps/forms/services/pdf_filler.py`
- Modify: `backend/apps/forms/tests/test_form_views.py`
- Modify: `backend/apps/forms/tests/test_pdf_filler.py`
- Modify: `backend/apps/forms/views.py`

**Interfaces:**

- Consumes:
  - From Task 1, `backend/apps/forms/services/widgets.py`:
    - `TemplateWidget` (frozen, so hashable). `check()` reads its `full_name`, `page`, `tag`, `kind`, `drawn`, `states`, `options`, `font`, `size`, `width`, `height`, `margin`, `comb`, `multiline`, `max_len` and `key`.
    - `template_widgets(template_filename: str) -> tuple[TemplateWidget, ...]` (`@lru_cache(maxsize=32)`, ordered by page then tag number).
    - `parse_key(key: str) -> tuple[str, int | None, str | None]`, which raises `ValueError` on a malformed key (R31).
    - In tests: `field_of(widget)` and `widget_for(template_filename, page, annotation, page_top)`.
  - `backend/apps/forms/schema.py`: `load_schema(form_type) -> FormSchema` (`@lru_cache`), `FormSchema.template_filename` and `.fields`, and `FieldSpec`'s `pdf_field`, `page`, `tag` (Task 1), `label`, `type`, `source`, `rule`, `binding` and `value`. The 17 schemas use the sources `derived`, `asked`, `ingested`, `constant` and `signature`; every asked binding is `answer:<form_type>.<key>`.
  - `load_index(template_filename) -> dict[str, tuple[IndexWidget, ...]]` (`backend/apps/forms/field_index.py`), whose rows carry `label`, `page` and `tag`.
  - `DERIVATIONS: dict[str, Callable[[IntakeSession], str]]` in `backend/apps/forms/services/derivations.py`.
  - In `backend/apps/forms/services/pdf_filler.py`: `UnknownField(form_type: str, names: list[str])` (attribute `names`) and `InvalidFieldValue(form_type: str, name: str)`. `fill()` is not changed.
  - `_failure(form_type: str | None, exc: Exception) -> tuple[dict, int]` in `backend/apps/forms/views.py`. Its plain-reason tuple is `PreconditionMissing | IncomeNotSplit | NoTableInForce` (message `str(exc)`, 422). It copies an exception's `step` or `page` onto a 422 body, and it logs the type of anything it turns into a 500.
  - pypdf 6.13.1's `pypdf._font.Font`: `from_font_resource`, `can_encode`, `get_text_width`, `_get_typographic_maps()` (whose first item is the reverse map, character to glyph) and `font_descriptor.bbox`. In tests, also `TextStreamAppearance.from_text_annotation(writer, page, False, acro_form, field, annotation, user_font_size=size)` (G12).
  - For the tests:
    - PyMuPDF 1.27.2.3's `pymupdf.get_text_length(text, fontname="helv", fontsize=size)`, already installed (G7).
    - `fill_resolver._emit(field, value)` and `_key(field)`, the path `resolve()` emits through.
    - `test_form_views.py`'s `TestGenerateEndpoint` (its `URL`) with the `api_client` and `session_with_debtor` fixtures.
- Produces:
  - `backend/apps/forms/services/text_fit.py` (new):
    - `MIN_SIZE = 6.0` and `STEP = 0.5`.
    - `@lru_cache(maxsize=64) def font_for(template_filename: str, font_name: str) -> Font`: the template's `/AcroForm /DR /Font` entry, built with `Font.from_font_resource`.
    - `def printable(font: Font, letter: str) -> bool`, which is `font.can_encode(letter)`.
    - `def wrap(font: Font, text: str, size: float, width: float) -> list[str] | None`: one paragraph broken at spaces into lines no wider than `width`. Returns `None` when a word is wider than `width`.
    - `def fit(widget: TemplateWidget, font: Font, text: str) -> tuple[str, float] | None`: the text as drawn and its size. Returns `None` when no size from the start down to 6 pt fits.
  - In `backend/apps/forms/services/pdf_filler.py`:
    - `class UnprintableLetter(Exception)`: `__init__(self, form_type: str, letter: str, label: str, fix: dict[str, str])`. Attributes `form_type`, `letter`, `label`, `step` (`fix.get("step")`) and `page` (`fix.get("page")`). `str(exc)` is the spec §4.5 sentence.
    - `class ValueTooLong(Exception)`: `__init__(self, form_type: str, label: str, fix: dict[str, str])`, with the same attributes less `letter`.
    - `@dataclass(frozen=True) class Planned`: `widget: TemplateWidget`, `value: str` (the text as drawn, with a multi-line box's lines joined by `"\n"`; a box's state or `"/Off"`; a combo's option) and `size: float | None` (`None` for a box).
    - `@dataclass(frozen=True) class PlannedPart`: `part: dict` and `widgets: tuple[Planned, ...]`.
    - `PDFFormFiller.check(self, form_type: str, values: dict) -> tuple[PlannedPart, ...]`. In this task it returns one part, `{"kind": "form", "values": values}`, with its widgets in page and tag order.
    - The private helpers `_as_printed(text) -> str` and `_refused_letter(widget, font, text) -> str | None`, which Task 7's `plan_sheet` reuses.
  - `RULE_FIXES: dict[str, dict[str, str]]` in `backend/apps/forms/services/derivations.py`, right after `DERIVATIONS`. It maps each rule to `{"step": <WIZARD_STEPS key>}`, `{"page": <path>}` or `{}`.
  - `def fix_for(field: FieldSpec) -> dict[str, str]` in `backend/apps/forms/services/fill_resolver.py`. It returns a new dict on every call.
  - `_failure` treats `UnprintableLetter` and `ValueTooLong` as 422 refusals with their own sentence and their `step` or `page`.
  - Tests:
    - `test_check.py` (new): `test_a_letter_the_form_cannot_print_is_refused` (7 cases), `test_a_tab_or_any_other_space_prints_as_a_space` (4), `test_a_character_that_prints_nothing_is_left_out` (2), `test_a_control_character_is_refused`, `test_a_comb_box_refuses_a_character_that_breaks_its_cells` (3), `test_a_refusal_names_the_box_as_its_binding_does`, `test_a_long_value_shrinks_before_it_is_refused`, `test_a_word_too_wide_for_a_multi_line_box_is_refused`, `test_a_comb_value_longer_than_its_cells_is_refused_not_shrunk`, `test_a_box_with_a_maximum_length_refuses_a_longer_value`, `test_parentheses_take_the_room_pypdf_gives_them`, `test_a_multi_line_value_wraps_at_spaces_into_lines_that_fit`, `test_a_multi_line_value_shrinks_to_the_largest_size_its_lines_fit`, `test_a_line_break_starts_a_new_line_only_in_a_multi_line_box` (3), `test_an_auto_size_box_starts_where_pypdf_would_size_it` (2), `test_a_value_pypdf_would_print_below_6_pt_is_refused`, `test_branches_no_template_has`, `test_a_widgets_own_key_fills_only_that_widget`, `test_a_full_name_fills_every_drawn_widget_but_never_a_stacked_one`, `test_a_key_that_names_no_drawn_widget_is_refused`, `test_a_box_prints_its_state_on_the_widgets_that_have_it`, `test_a_combo_prints_one_of_its_options` and `test_every_constant_prints`. That is 38 cases.
    - `test_rule_fixes.py` (new): `test_every_refusal_names_where_to_fix_it`, `test_a_rule_links_to_where_its_input_is_entered` (12 cases), `test_a_refusal_sends_the_filer_to_where_the_value_came_from` (7), `test_changing_a_refusals_fix_leaves_the_map_alone` and `test_an_answer_is_fixed_on_the_form_that_asks_it`. That is 22 cases.
    - In `test_form_views.py`: `TestGenerateEndpoint.test_a_refused_letter_or_length_names_where_to_fix_it` (2 cases).
    - In `test_pdf_filler.py`: `test_text_is_measured_with_pinned_pypdf_font_internals`.

**Decisions already made in this task:**

_Scope:_

- **Nothing calls `check()` yet.** `fill()` is unchanged, and Generate and Download still call `fill()` alone, so no `CLAUDE.md` sentence becomes false and `CLAUDE.md` doesn't change. Task 3 makes `fill()` run `check()` first and draw its plan. Task 5 makes Generate call `check()`.
  - `check()` takes a flat `{key: value}` dict.
  - It returns one `PlannedPart`, whose `part` is `{"kind": "form", "values": values}`.
  - Task 5 adds the `{"version": 2, "parts": [...]}` document.
- **`check()` opens no PDF of its own** (G14). It reads only `template_widgets`, `font_for`, `load_index` and `load_schema`, all `lru_cache`d.
- **It never raises `TemplateHasNoForm`.** `font_for` would raise `KeyError` on a template with no `/AcroForm`, but only for a text value, and no registered template lacks one. `fill()` keeps its own check.

_Which widgets a key fills:_

- **A key reaches drawn widgets only.**
  - A full name reaches every drawn widget of that name.
  - `<full name>@<page>:<tag>` reaches that one widget and wins over the full name there: full-name keys are applied first, then widget keys overwrite them.
  - A key that reaches no drawn widget is refused: a stacked widget's key, a print button's, or an unknown name. So is a key `parse_key` refuses with `ValueError` (R31).
  - All such keys raise one `UnknownField`, sorted, as `fill()` reports them today.
- **Refusals come in a fixed order.** The first refused widget in page order is the one a refusal names.
  1. `UnknownField`, for every bad key at once.
  2. Box values, key by key. They are checked against every widget a key reaches, before a widget's own key overrides any of them (the controller accepted this).
  3. Widget by widget, in page and tag-number order: a combo's option, then the letters, then the fit.
- **Boxes are planned as `fill()` ticks them today.**
  - A `CheckBox` or `RadioButton` widget whose `states` hold the value is planned with it. Every other widget the key reaches is planned with `"/Off"`, and `size` is `None`.
  - A value that no reached widget has is `InvalidFieldValue`.
  - `states` leaves out `/Off`, so `check()` refuses `"/Off"` as a value. Today's `fill()` accepts it as a key of `/AP /N`. No schema emits it (the reviewer's grep), and R37 notes it for Task 3's port of the box tests.
- **A combo's value must be one of its options.** The raw value is compared, before any letter handling; anything else is `InvalidFieldValue`. The value is then checked for letters and fitted as a single-line box.
  - All 18 `ComboBox` widgets are 8 pt, and none is comb or multi-line.
  - The implementer's probe (`t02/probe10.py`) planned "Northern District of Illinois" on every `district_name` binding, and all 18 fit at 8 pt.

_Letters:_

- **A letter is printable when the AcroForm's font can encode it** (R7). `printable(font, letter)` is `font.can_encode(letter)`, the test pypdf itself makes before it warns.
  - `font_for(template, font_name)` builds `Font.from_font_resource(acro_form["/DR"]["/Font"][font_name])`.
  - It is cached by template filename and font name, never by form type (G11), with `maxsize=64`.
  - Every text box's `/DA` names `/Helv` (R29), so each template has one font in practice.
- **`check()` reads the AcroForm's font, not a widget's own (R32).**
  - 567 `Text` and `ComboBox` widget annotations carry their own `/DR /Helv` without the template's `/Differences` encoding: Form 101 has 1, 122A-2 116, A/B 266, C 75 and D 109.
  - pypdf encodes with that font but renders with the AcroForm's. So Ł, ’, “, ”, –, € and • print "?" on 18 bound boxes today (the implementer's first-round probes, `t02/probe5.py` to `probe9.py`).
  - Ruling (a): Task 3 deletes each drawn widget's own `/DR` on the clone before building its appearance, so the drawing encodes with the font `check()` reads. Probe 9 proved this on every bound box of the five templates.
  - Until Task 3, `check()` passes letters that `fill()` still prints as "?". Nothing calls `check()` yet. Ticket candidate (6) records today's defect.
- **Spaces, invisible characters and control characters follow R36,** which replaced R34's rule for a tab and U+00A0 alone.
  - `_as_printed()` runs first, so `Planned.value` holds the result.
    - A tab or any Unicode space separator (category Zs: U+00A0, U+2000–U+200A, U+202F, U+205F, U+3000) becomes a plain space. The template's font draws U+00A0 as "€" and has no glyph for the others.
    - A format character (category Cf: U+00AD, U+200B–U+200F, U+2060, U+FEFF and the rest) is dropped, since it prints nothing.
  - `_refused_letter()` then returns the first character the font can't encode, or a control character (category Cc).
  - A value made only of Cf characters becomes `""` and plans as a blank box. That is the same as typing nothing visible (re-review note).
  - Cf includes the joiners and direction marks some scripts need, but those scripts are refused anyway, as letters the font can't encode.
- **A line break is whatever `str.splitlines()` splits on** (G15, R6).
  - A single-line box, comb boxes and combos included, joins the lines with single spaces.
  - A multi-line box joins its paragraphs with `"\n"`.
  - The letter check runs on `"".join(text.splitlines())`, so a line-break character is never refused as a letter.
- **A comb box refuses `(`, `)` and `\`** as `UnprintableLetter` (R33). pypdf draws each cell's character as its own escaped string, and these break that even within MaxLen.
- **The refusal sentences are spec §4.5's, verbatim.** They use U+201C and U+201D quotes and a straight apostrophe in "can't". The implementer's `t02/sentences.py` compared them with tasks.md and with the spec's filled-in examples.
  - The two sentences are "The court form can't print the letter “{letter}” in “{label}”. Change it to a letter without the mark." and "“{label}” is too long to fit on the court form, even in small print. Shorten it."
  - `step` and `page` are `fix.get("step")` and `fix.get("page")`. Each exception also keeps `form_type`, as `UnknownField` does.
  - The letter sentence is also used for `(`, `)` and `\` in a comb box and for control characters, which aren't letters. That wording question (W-1) goes to the owner at handover; the spec calls its wording a draft.
- **A refusal names the box by the label of the binding that produced its key.** The binding must have the same `pdf_field` and `tag`, and for a tagged key the same `page`, so a tagged key never matches an untagged binding. A key no binding produced (a test's, the oracle's, or one widget of a name bound as a whole) takes the index row's label and links nowhere (`{}`).

_Fit:_

- **Widths are measured on the escaped text (R33).** `_width()` escapes `\` → `\\`, `(` → `\(` and `)` → `\)`, as `from_text_annotation` does before it measures and places right- or centre-aligned text. It maps each character through the reverse map of `_get_typographic_maps()` and takes `get_text_width × size / 1000`.
  - `Planned.value` stays unescaped, since pypdf escapes `/V` itself.
  - A comb box counts the escaped length against MaxLen, as pypdf does. Since `(`, `)` and `\` are refused there, that equals the plain length.
- **A single-line box fits on width alone:** width ≤ `widget.width − 4 × margin` (R5), since pypdf's padding is 2 × margin on each side. There is no height rule (R38).
  - R38 was ruled after this commit, when Task 3 was dispatched. The controller's probe (`t03/probe_height.py`) placed all 1,966 fixed-size single-line text and combo widgets at their own size, centred as pypdf centres them, and found no mark cut off at the top.
  - On 37 widgets, only Ç's cedilla dips below the rectangle, by up to 0.108 pt; Task 3's real draw measured it. Twenty-six are 11.52–11.64 pt high at 10 pt, on Forms C, 103B, A/B and D, and none of them is bound. Eleven are 13.8 pt high at 12 pt: ten on Form 101, nine of them bound (the `Debtor1.Name` header on pages 2–9 and `Attorney.Sig` on page 8), and one on Form 121. That is the template's own size, invisible, and it prints the same today. Task 4's geometric test allows 0.11 pt for it.
  - Auto sizes are bounded by (h − 2m) / leading, so they stay inside.
- **Sizes start at the box's own and shrink to 6 pt.**
  - A box starts at its own `/DA` size: 1,959 boxes at 10 pt, 65 at 9 and 19 at 12.
  - An auto-size box (`size == 0`, 10 boxes, all single-line) starts where pypdf's auto path would: `round(min((h − 2m) / leading, (w − 4m) / width_at_1pt), 1)`. `leading = (bbox[3] − bbox[1]) / 1000` comes from `font.font_descriptor`, and is 1.156 for Helvetica.
  - pypdf's `max(…, 4.0)` floor is left out, since 6 pt is the floor here. A start below 6 tries no size and is refused.
  - A multi-line auto-size box starts at 12, as pypdf's does. No template has one, so a test reaches it through `dataclasses.replace`.
  - Sizes then go down in 0.5 pt steps to 6 (`STEP`, `MIN_SIZE`). An off-grid start, such as an auto size of 7.6, is tried first, then the grid below it. The first size that fits is planned.
- **An auto-size box can plan below pypdf's own choice, by design** (fix report).
  - When pypdf's `round(…, 1)` rounds up past the fit, `check()` falls to the grid below. In Form 107's `Email 16a`, "rosalind.quintanilla-oyelaran@example.org" gets 7.4 pt from pypdf and 7.0 from `check()`.
  - The reviewer compared all 10 auto-size widgets with 3 values each against pypdf's own `Tf` (30 cases). `check()` matched whenever pypdf's rounded size fits.
  - Task 3 passes the planned size as `user_font_size`, so pypdf's auto path, which goes down to 4 pt, never runs.
- **A comb box fits at its start size only,** since its cells are fixed and shrinking can't make room. The escaped length must be at most `max_len`. A comb box with no `max_len` fits anything at its start size; no template has one, so a test reaches it through `dataclasses.replace`.
- **Any other box with a `max_len` refuses a longer value** (R28; an inherited MaxLen counts). The drawn text's length is checked once, before the size loop. Form 101's State box (MaxLen 2) takes "IL" and refuses "ILL", though "ILL" would fit its width.
- **A multi-line value's lines must fit the box's height less two margins (R35).**
  - Each paragraph wraps at spaces with `wrap()` to `w − 4m`.
  - A size fits when no word is wider than that and `len(lines) × size × leading ≤ widget.height − 2 × margin`.
  - Why the two margins: pypdf hangs line 1 with the font's bbox top at h + m, so the widget's BBox cuts the mark off É, Ü, Ñ, Š and Å. At 6.5 pt the reviewer found the mark entirely gone from É, Ñ, Š and Å on line 1.
  - Ruling (b): Task 3 lowers a multi-line box's first baseline by 2 × margin, so the lines get the box's height less 2 × margin.
  - The owner's "nothing is ever cut off" (3a2.Q2) ruled out accepting the cut. Refusing a capital with a mark on line 1 would refuse common names.
  - Before R35 the rule was `≤ widget.height`.
- **`wrap()` splits on U+0020 only.**
  - Runs of spaces stay as typed. A tab is already a space by then.
  - Exactly one space is dropped at each break.
  - `wrap("")` is `[""]`, so a blank line counts toward the height.
  - A word wider than the box at one size fails that size, and the loop tries the next. Only a word too wide at 6 pt is refused.
- **A boundary test pins the height rule** (R37, review finding 2). Before the fix round, loosening the rule by 10% left every T2 test green.
  - The test uses five short lines on A/B line 53, where h = 47.64 pt and m = 1, leaving 45.64 pt of room. 5 × 7.5 × 1.156 = 43.35 fits; 5 × 8.0 × 1.156 = 46.24 overflows. So the lines plan at 7.5 pt; R37's earlier 8.0 came from the rule before R35.
  - The test computes the size from the widget and Helvetica's AFM FontBBox (−225, 931), not from `fit()`.
  - It also reads pypdf's own `Td` offsets at 7.5 and 8.0 pt. Lowered by 2m, the last line's lowest point is 3.29 pt at 7.5, inside the clip bottom of 1, and 0.40 pt at 8.0, outside it.
  - PyMuPDF's `Font("helv").bbox` is a different box (−0.299 to 1.075). So the leading is a constant from the AFM, which `test_pdf_filler.py` pins to pypdf's own `font_descriptor.bbox`.
- **The tests measure widths with PyMuPDF's Helvetica** (`pymupdf.get_text_length(..., fontname="helv")`), a second source of the font's metrics. That way "the first size that fits" isn't checked against `check()`'s own arithmetic.
  - The reviewer found pypdf's widths equal PyMuPDF's within 1 unit for every printable character on all 17 templates. U+007F and U+009F differ, and both are refused as Cc.
  - The auto-size tests read pypdf's own `Tf` from the appearance it builds.
  - The width-limited case uses "rosalind.oyelaran.synthetic@example.org": 7.6 pt on both sides, off the 0.5 grid. The implementer's first candidate gave 6.0 on both sides, which is on the grid, so a mutation that ignored the width stayed green.

_Where to fix it:_

- **`RULE_FIXES` has 78 entries** (R10, R11). They are exactly the derived rules bound to a text or choice box in the 17 schemas: 77 text rules (backend survey §8.1) plus `district_name`, the combo. Comments group them by step. The reviewer checked every entry against §8.1, and a script over the 17 schemas, run for this plan, finds exactly these 78 rules.
  - `fee_waiver_monthly_expenses` → `expense_info` (R10), because 103B line 6 is Schedule J line 22c.
  - `schedule_j_monthly_net_income` has two inputs, so it goes to the earlier step, `income_info` (R11).
  - `family_size` → `debtor_info`, because `DebtorInfoStep.tsx` edits `household_size` (reviewer).
  - The fee-waiver rules go to `/fee-waiver`.
  - Seven rules get `{}`. `district_name` and `line13a_median_income` print DigniFi's own data. The five dead Schedule I rules (occupation and employer address) read fields no model has, so they always print blank.
- **`fix_for(field)` follows spec §4.5's table:**
  - `derived`: a copy of `RULE_FIXES[field.rule]` (review finding 6). Handing out the shared dict would let one caller change it for the whole process.
  - `ingested` and `db_aggregate`: `/documents`. No schema uses `db_aggregate`; the controller accepted it.
  - `answer:<form_type>.<key>`: `/ask/<form_type>`, the form the binding names, not the one being drawn (R9). Form 107 prints Form 101's preparer answer, which is changed on Form 101's questions.
  - `sofa.…`: `/sofa`.
  - `constant` and `signature`: `{}`. A constant that can't print is DigniFi's defect.
  - No production schema has a `sofa.` binding or a text constant (R12). So `/sofa` is proven on a synthetic binding, and `test_every_constant_prints` runs the 4 checkbox constants through `_emit` and `_key`, the path `resolve()` uses.
- **`_failure` treats both refusals as 422s.** They join `PreconditionMissing | IncomeNotSplit | NoTableInForce`: the body carries `str(exc)` and its `step` or `page`, and nothing is logged (G6), so the letter reaches only the 422 body.
  - The view test patches `PDFFormFiller.fill` on Generate, because nothing calls `check()` yet.
  - Task 5 retargets it to `check()` with R14's three tests (tasks.md T5).

_How it was checked:_

- **The implementer's probes ran once `check()` existed** (`t02/probe11.py`, re-run after the fix round).
  - Six seeded personas, 88 forms and 985 text and combo widgets were planned, and none was refused.
  - Exactly 7 widgets shrink, the 7 that spec §4.1 says are cut off today: Form 101's email for James (8.5 pt), DeShawn (9.0) and Andrés (9.5); 122A-1 13C for Maria (9.5); and 122A-1 12B and 13C and 122A-2 `undefined_53` for Priya (9.5 each).
- **The reviewer's letter run.** 588 characters (U+0020–U+024F plus 28 specials) went through `check()` on 7 templates. 229 were accepted, and each read back exactly from an emulated Task 3 draw.
- **Every new test was shown red** (G4).
  - The implementer's `t02/mutate.py` applied 39 mutations one at a time, restoring each, and all 39 turned a test red.
  - The six new fix-round cases failed against the code before the fix round.
  - The pin test, `test_text_is_measured_with_pinned_pypdf_font_internals`, is a version guard, as `test_text_prints_from_a_stored_appearance` is. It goes red only if pypdf changes.
- **The code spells invisible characters as `\N{…}` escapes,** such as `"\N{NO-BREAK SPACE}"` and `"\N{LINE SEPARATOR}"`, never as the literal character. An editor can silently turn such an escape into an invisible character. A scan of the changed files found no NBSP, LSEP, BOM, tab, CR or control byte.
- **Test helpers.**
  - `test_every_constant_prints` imports the private `_emit` and `_key` from `fill_resolver`, so it emits exactly what `resolve()` would. `test_engine_form_agnostic.py` already imports `_scalar_value` the same way.
  - `test_rule_fixes.py` lists the eight `WIZARD_STEPS` keys with a comment naming `frontend/src/pages/IntakeWizard.tsx`. Task 8 moves them to `frontend/src/constants/wizardSteps.ts`, and that comment should follow.
  - Test data is synthetic (G2): the SSNs are in the 900 range, and the names and email addresses are invented.

_Later tasks:_

- **Task 3** applies R32 and R35, and passes `Planned.size` as `user_font_size` and `Planned.value` as `/V`.
- **Task 7's `plan_sheet`** reuses `_as_printed` and `_refused_letter`, not `fit()` alone.

_Left as found:_

- **The five dead Schedule I rules** (backend survey §0.9; a ticket candidate).
- **pypdf's encoding and comb-length warnings log the filer's whole value today** (ticket candidate (7)). This closes once `fill()` runs `check()` first, in Task 3.
- **MuPDF ignores pypdf's inner clip** (review finding 4; `W` without `n`), so after baking, the widget's BBox is what hides text. `check()`'s `w − 4m` rule is the safe side of that. R37 sends the note to `facts-pypdf.md` and Task 4.

- [ ] **Step 1: Write the failing tests**

```python file=backend/apps/forms/tests/test_check.py
"""
check() plans what each box prints, and at what size, without drawing (3a2 spec §4.3).

Today a letter the form's font lacks prints as "?" and a value wider than its box is cut
off at the edge, both silently. check() shrinks a long value in 0.5 pt steps down to
6 pt and refuses what still doesn't fit, or can't be printed, naming the box and where
the filer fixes it.

Widths here are measured with PyMuPDF's Helvetica, a second source of the same font's
metrics, so "the first size that fits" isn't checked against check()'s own arithmetic.
"""

import dataclasses
import re
from pathlib import Path

import pymupdf
import pypdf
import pytest
from django.conf import settings
from pypdf.generic import NameObject, TextStringObject
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.forms.registry import get_all_form_types
from apps.forms.schema import load_schema
from apps.forms.services.fill_resolver import _emit, _key
from apps.forms.services.pdf_filler import (
    InvalidFieldValue,
    PDFFormFiller,
    UnknownField,
    UnprintableLetter,
    ValueTooLong,
)
from apps.forms.services.text_fit import MIN_SIZE, fit, font_for
from apps.forms.services.widgets import field_of, template_widgets, widget_for

LAST_NAME = "Debtor1.Last name"  # Form 101 page 1: derived last_name, label "Last name"
EMAIL = "Debtor1.Email address_2"  # Form 101 page 9: derived email, label "Email address"
SSN = "Debtor1a.SSNum"  # Form 121: an 11-cell comb box, derived ssn_formatted
OTHER_PROPERTY = "53 Examples Season tickets country club membership"  # A/B line 53, multi-line
ASSISTANCE = "3 type"  # Form 103B line 3, multi-line, from the fee-waiver page
DISTRICT = "Bankruptcy District Information"  # a combo box on every form


def _plan(form_type, values):
    (part,) = PDFFormFiller().check(form_type, values)
    assert part.part == {"kind": "form", "values": values}
    return part.widgets


def _widgets(form_type, full_name):
    template = load_schema(form_type).template_filename
    return [w for w in template_widgets(template) if w.full_name == full_name and w.drawn]


def _room(widget):
    """The width pypdf's clip leaves for text: the box less its padding on each side."""
    return widget.width - 4 * widget.margin


def _helvetica(text, size):
    return pymupdf.get_text_length(text, fontname="helv", fontsize=size)


# Helvetica's FontBBox (its AFM), per 1000 em: pypdf spaces lines by its height.
_HELVETICA_BOTTOM, _HELVETICA_TOP = -225, 931
_LEADING = (_HELVETICA_TOP - _HELVETICA_BOTTOM) / 1000


def _pypdf_stream(form_type, widget, value, size=-1):
    """The appearance pypdf builds for one widget holding value, at size or its own."""
    template = load_schema(form_type).template_filename
    writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
    page = writer.pages[widget.page - 1]
    annotation = next(
        a.get_object()
        for a in page["/Annots"]
        if a.get_object().get("/Subtype") == "/Widget"
        and widget_for(template, widget.page, a.get_object(), float(page.mediabox.top)) == widget
    )
    field = field_of(annotation)
    field[NameObject("/V")] = TextStringObject(value)
    appearance = TextStreamAppearance.from_text_annotation(
        writer, page, False, writer.root_object["/AcroForm"], field, annotation, user_font_size=size
    )
    return appearance.get_data()


# ── Letters ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "last_name,letter",
    [
        ("Varée", None),
        ("Peñalta", None),
        ("Grünholt", None),
        ("Łazar", None),
        ("Wąsowicz", "ą"),
        ("Dvořák", "ř"),
        ("Nguyễn", "ễ"),
    ],
)
def test_a_letter_the_form_cannot_print_is_refused(last_name, letter):
    if letter is None:
        (planned,) = _plan("form_101", {LAST_NAME: last_name})
        assert (planned.value, planned.size) == (last_name, 10.0)
        return
    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("form_101", {LAST_NAME: last_name})
    assert refused.value.letter == letter
    assert (refused.value.label, refused.value.step, refused.value.page) == (
        "Last name",
        "debtor_info",
        None,
    )
    assert str(refused.value) == (
        f"The court form can't print the letter “{letter}” in “Last name”. "
        "Change it to a letter without the mark."
    )


@pytest.mark.parametrize(
    "space", ["\t", "\N{NO-BREAK SPACE}", "\N{THIN SPACE}", "\N{NARROW NO-BREAK SPACE}"]
)
def test_a_tab_or_any_other_space_prints_as_a_space(space):
    # The template's font draws U+00A0 as "€" (R34) and has no glyph for the rest (R36).
    (planned,) = _plan("form_101", {LAST_NAME: f"Varée{space}Peñalta"})
    assert planned.value == "Varée Peñalta"


@pytest.mark.parametrize("invisible", ["\N{SOFT HYPHEN}", "\N{ZERO WIDTH SPACE}"])
def test_a_character_that_prints_nothing_is_left_out(invisible):
    # Format characters, pasted along with text, print nothing anyway (R36).
    (planned,) = _plan("form_101", {LAST_NAME: f"Varée{invisible}Peñalta"})
    assert planned.value == "VaréePeñalta"


def test_a_control_character_is_refused():
    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("form_101", {LAST_NAME: "Varée\x07"})
    assert refused.value.letter == "\x07"


@pytest.mark.parametrize("letter", ["(", ")", "\\"])
def test_a_comb_box_refuses_a_character_that_breaks_its_cells(letter):
    # pypdf draws each cell's character as its own string, which these break (R33).
    with pytest.raises(UnprintableLetter) as refused:
        PDFFormFiller().check("form_121", {SSN: f"900-12-345{letter}"})
    assert (refused.value.letter, refused.value.label, refused.value.step) == (
        letter,
        "Debtor 1 SSN",
        "debtor_info",
    )


def test_a_refusal_names_the_box_as_its_binding_does():
    # Bound: the schema's label and fix. The index calls the same box "Running header: …".
    with pytest.raises(UnprintableLetter) as bound:
        PDFFormFiller().check("form_101", {"Debtor1.Name": "Ana Wąsowicz"})
    assert (bound.value.label, bound.value.step) == ("Debtor name", "debtor_info")
    # A key no binding produced, such as one widget of a name bound as a whole, or an
    # unbound box, is named by its index row and links nowhere.
    page_2 = next(w for w in _widgets("form_101", "Debtor1.Name") if w.page == 2)
    for key, label in [
        (page_2.key, "Running header: Debtor 1 (First Name Middle Name Last Name)"),
        ("Suffix Sr Jr II III_2", "Suffix (Sr., Jr., II, III)"),
    ]:
        with pytest.raises(UnprintableLetter) as unbound:
            PDFFormFiller().check("form_101", {key: "Wąsowicz"})
        assert (unbound.value.label, unbound.value.step, unbound.value.page) == (label, None, None)


# ── Fit ───────────────────────────────────────────────────────────────


def test_a_long_value_shrinks_before_it_is_refused():
    (box,) = _widgets("form_101", EMAIL)
    email = "kestrel.wanamaker.okonkwo@example.org"
    assert _helvetica(email, box.size) > _room(box)  # too wide at the box's own 10 pt

    (planned,) = _plan("form_101", {EMAIL: email})
    assert planned.value == email
    assert MIN_SIZE <= planned.size < box.size
    assert planned.size % 0.5 == 0
    # The first size that fits: half a point larger doesn't.
    assert _helvetica(email, planned.size) <= _room(box)
    assert _helvetica(email, planned.size + 0.5) > _room(box)

    too_long = "kestrel.wanamaker.okonkwo.marchetti-oyelaran@example.org"
    assert _helvetica(too_long, MIN_SIZE) > _room(box)
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("form_101", {EMAIL: too_long})
    assert (refused.value.label, refused.value.step, refused.value.page) == (
        "Email address",
        "debtor_info",
        None,
    )
    assert str(refused.value) == (
        "“Email address” is too long to fit on the court form, even in small print. Shorten it."
    )


def test_a_word_too_wide_for_a_multi_line_box_is_refused():
    (box,) = _widgets("form_103b", ASSISTANCE)
    word = "W" * 60
    assert _helvetica(word, MIN_SIZE) > _room(box)  # too wide even at 6 pt, on one line
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("form_103b", {ASSISTANCE: f"SNAP {word}"})
    assert (refused.value.label, refused.value.page) == ("Type of assistance", "/fee-waiver")


def test_a_comb_value_longer_than_its_cells_is_refused_not_shrunk():
    (box,) = _widgets("form_121", SSN)
    assert (box.comb, box.max_len) == (True, 11)
    (planned,) = _plan("form_121", {SSN: "900-12-3456"})
    assert (planned.value, planned.size) == ("900-12-3456", box.size)
    with pytest.raises(ValueTooLong):
        PDFFormFiller().check("form_121", {SSN: "900-12-34567"})


def test_a_box_with_a_maximum_length_refuses_a_longer_value():
    # Form 101's State box takes 2 characters (MaxLen), though 3 would fit its width.
    (planned,) = _plan("form_101", {"Debtor1.State": "IL"})
    assert planned.value == "IL"
    with pytest.raises(ValueTooLong) as refused:
        PDFFormFiller().check("form_101", {"Debtor1.State": "ILL"})
    assert (refused.value.label, refused.value.step) == ("State", "debtor_info")


def test_parentheses_take_the_room_pypdf_gives_them():
    # pypdf measures "(" as "\(" when it places text, so a value that fits only without
    # the backslashes would start left of a right-aligned box's clip (R33).
    (box,) = _widgets("form_101", LAST_NAME)
    count = 1  # as many narrow letters as fit between the parentheses at the box's size
    while _helvetica(f"({'i' * (count + 1)})", box.size) <= _room(box):
        count += 1
    value = f"({'i' * count})"
    assert _helvetica(value, box.size) <= _room(box) < _helvetica(rf"\({'i' * count}\)", box.size)

    (planned,) = _plan("form_101", {LAST_NAME: value})
    assert planned.value == value  # pypdf escapes /V itself
    assert planned.size < box.size


def test_a_multi_line_value_wraps_at_spaces_into_lines_that_fit():
    (box,) = _widgets("schedule_a_b", OTHER_PROPERTY)
    description = (
        "Season tickets to a minor league ballpark, a canoe and two paddles, "
        "and a set of carpentry tools kept in a rented storage unit"
    )
    (planned,) = _plan("schedule_a_b", {OTHER_PROPERTY: description})
    lines = planned.value.split("\n")
    assert len(lines) > 1
    assert " ".join(lines) == description
    assert all(_helvetica(line, planned.size) <= _room(box) for line in lines)


def test_a_multi_line_value_shrinks_to_the_largest_size_its_lines_fit():
    (box,) = _widgets("schedule_a_b", OTHER_PROPERTY)
    items = ["A canoe", "A bicycle", "A tent", "A saddle", "A kiln"]
    assert all(_helvetica(item, 10) <= _room(box) for item in items)  # none wraps at any size
    # T3 lowers line 1 by 2 × margin (R35), so the lines get the box's height less that.
    height = box.height - 2 * box.margin
    sizes = [10 - 0.5 * step for step in range(9)]  # 10, 9.5, …, 6
    expected = max(size for size in sizes if len(items) * size * _LEADING <= height)
    assert len(items) * (expected + 0.5) * _LEADING > height

    (planned,) = _plan("schedule_a_b", {OTHER_PROPERTY: "\n".join(items)})
    assert planned.value.split("\n") == items
    assert planned.size == expected

    # pypdf's own layout: the last line's lowest point, lowered with line 1, stays above the
    # clip's bottom at the planned size and falls below it 0.5 pt larger.
    for size, fits in [(planned.size, True), (planned.size + 0.5, False)]:
        stream = _pypdf_stream("schedule_a_b", box, planned.value, size)
        baseline = sum(float(y) for y in re.findall(rb"-?[0-9.]+ (-?[0-9.]+) Td", stream))
        lowest = baseline + _HELVETICA_BOTTOM * size / 1000 - 2 * box.margin
        assert (lowest >= box.margin) is fits, size


@pytest.mark.parametrize("line_break", ["\r\n", "\r", "\N{LINE SEPARATOR}"])
def test_a_line_break_starts_a_new_line_only_in_a_multi_line_box(line_break):
    (multi_line,) = _plan("schedule_a_b", {OTHER_PROPERTY: f"A canoe{line_break}A bicycle"})
    assert multi_line.value == "A canoe\nA bicycle"
    (single_line,) = _plan("form_101", {LAST_NAME: f"Varée{line_break}Peñalta"})
    assert single_line.value == "Varée Peñalta"


@pytest.mark.parametrize(
    "form_type,name,page,value,limit",
    [
        ("form_101", "Case number1", 1, "24-10001", "height"),
        ("form_107", "Email 16a", 7, "rosalind.oyelaran.synthetic@example.org", "width"),
    ],
)
def test_an_auto_size_box_starts_where_pypdf_would_size_it(form_type, name, page, value, limit):
    # These boxes have no size of their own: pypdf picks one per value, as large as the
    # box's height allows, or its width when the value is long.
    box = next(w for w in _widgets(form_type, name) if w.page == page)
    assert box.size == 0
    stream = _pypdf_stream(form_type, box, value)
    pypdf_size = float(re.search(rb"/Helv ([0-9.]+) Tf", stream)[1])
    by_height = round((box.height - 2 * box.margin) / _LEADING, 1)
    assert (pypdf_size == by_height) is (limit == "height")

    (planned,) = _plan(form_type, {box.key: value})
    assert planned.size == pypdf_size


def test_a_value_pypdf_would_print_below_6_pt_is_refused():
    # pypdf's auto size goes down to 4 pt; the check stops at 6.
    with pytest.raises(ValueTooLong):
        PDFFormFiller().check("form_101", {"Case number1": "24-10001 " * 12})


def test_branches_no_template_has():
    # No template has a multi-line auto-size box or a comb box without a MaxLen.
    (lines,) = _widgets("schedule_a_b", OTHER_PROPERTY)
    font = font_for(load_schema("schedule_a_b").template_filename, lines.font)
    assert fit(dataclasses.replace(lines, size=0.0), font, "A canoe") == ("A canoe", 12.0)
    (cells,) = _widgets("form_121", SSN)
    uncounted = dataclasses.replace(cells, max_len=None)
    assert fit(uncounted, font, "900-12-3456-78") == ("900-12-3456-78", cells.size)


# ── Which widgets a key fills ─────────────────────────────────────────


def test_a_widgets_own_key_fills_only_that_widget():
    first, second = _widgets("schedule_i", "Assistance 8f")
    planned = _plan("schedule_i", {first.key: "SNAP"})
    assert [(p.widget, p.value) for p in planned] == [(first, "SNAP")]
    # It wins over its full name, which still fills the name's other widget.
    planned = _plan("schedule_i", {"Assistance 8f": "Housing aid", second.key: "SNAP"})
    assert [(p.widget, p.value) for p in planned] == [(first, "Housing aid"), (second, "SNAP")]


def test_a_full_name_fills_every_drawn_widget_but_never_a_stacked_one():
    planned = _plan("schedule_i", {"Time employed Debtor 1": "4 years"})
    assert [p.widget for p in planned] == _widgets("schedule_i", "Time employed Debtor 1")
    assert len(planned) == 2
    # Schedule D page 2 lays a second "4_3" over the first; only the first prints.
    (planned,) = _plan("schedule_d", {"4_3": "2.1"})
    assert (planned.widget.tag, planned.widget.stacked) == ("T13", False)


def test_a_key_that_names_no_drawn_widget_is_refused():
    keys = ["4_3@2:T14", "Debtor9.Name", "4_3@2"]  # stacked; no such name; not a key
    with pytest.raises(UnknownField) as refused:
        PDFFormFiller().check("schedule_d", dict.fromkeys(keys, "1"))
    assert refused.value.names == sorted(keys)


def test_a_box_prints_its_state_on_the_widgets_that_have_it():
    planned = _plan("form_101", {"Check Box1": "/Chapter 7"})
    # Chapter 7 is printed on pages 1 and 3; the other options print empty.
    assert sorted(p.value for p in planned) == ["/Chapter 7"] * 2 + ["/Off"] * (len(planned) - 2)
    assert {p.size for p in planned} == {None}
    with pytest.raises(InvalidFieldValue):
        PDFFormFiller().check("form_101", {"Check Box1": "/Chapter 9"})


def test_a_combo_prints_one_of_its_options():
    (planned,) = _plan("form_121", {DISTRICT: "Northern District of Illinois"})
    assert (planned.value, planned.size) == ("Northern District of Illinois", 8.0)
    with pytest.raises(InvalidFieldValue):
        PDFFormFiller().check("form_121", {DISTRICT: "District of Nowhere"})


def test_every_constant_prints():
    constants = [
        (form_type, field)
        for form_type in get_all_form_types()
        for field in load_schema(form_type).fields
        if field.source == "constant"
    ]
    assert constants  # four checkboxes today
    for form_type, field in constants:
        value = _emit(field, field.value)  # what resolve() emits for it
        assert value is not None
        planned = _plan(form_type, {_key(field): value})
        assert value in [p.value for p in planned], (form_type, field.pdf_field)
```

The `check()` tests use real boxes on the real templates.

- **Letters:** names that print and names that don't, every kind of space, format characters, a control character, and the three comb breakers.
- **Fit:** the email that shrinks and the one refused at 6 pt, a word too wide for a multi-line box, the comb SSN, the State box's MaxLen, and parentheses that take room only when escaped.
- **Multi-line boxes:** wrapping, the height boundary checked against pypdf's own stream, and line breaks in both kinds of box.
- **Auto size:** both limits, checked against pypdf's own `Tf`.
- **Keys:** which widgets each key fills, boxes and combos, and every constant in the 17 schemas.

```python file=backend/apps/forms/tests/test_rule_fixes.py
"""
A refused letter or length links the filer to where they change the value (3a2 spec §4.5).

A derived value is fixed where its rule's input is entered (RULE_FIXES), an asked answer
on its form's questions page, a SOFA answer on /sofa and a scanned value on /documents.
A constant links nowhere: a constant that can't print is DigniFi's defect, and
test_check.py's test_every_constant_prints keeps every constant printable.
"""

import pytest

from apps.forms.registry import get_all_form_types
from apps.forms.schema import FieldSpec, load_schema
from apps.forms.services.derivations import DERIVATIONS, RULE_FIXES
from apps.forms.services.fill_resolver import fix_for

# The keys of WIZARD_STEPS in frontend/src/pages/IntakeWizard.tsx: what /intake?step= opens.
WIZARD_STEPS = {
    "debtor_info",
    "income_info",
    "expense_info",
    "assets",
    "debts",
    "contracts",
    "codebtors",
    "review",
}
PAGES = {"/fee-waiver", "/documents", "/sofa"} | {f"/ask/{ft}" for ft in get_all_form_types()}


def _field(source, rule=None, binding=None, ingest_key=None, value=None):
    return FieldSpec(
        pdf_field="Debtor1.Last name",
        type="text",
        source=source,
        page=1,
        label="Last name",
        required=False,
        conditional_on=None,
        value=value,
        rule=rule,
        ingest_key=ingest_key,
        binding=binding,
        repeat=None,
        repeat_capacity=None,
        row=None,
        legal_review=False,
    )


def test_every_refusal_names_where_to_fix_it():
    printed_rules = {
        field.rule
        for form_type in get_all_form_types()
        for field in load_schema(form_type).fields
        if field.source == "derived" and field.type in ("text", "choice")
    }
    assert printed_rules - RULE_FIXES.keys() == set()
    for rule, fix in RULE_FIXES.items():
        assert rule in DERIVATIONS, rule
        assert len(fix) <= 1, rule
        for kind, target in fix.items():
            assert target in {"step": WIZARD_STEPS, "page": PAGES}[kind], rule


@pytest.mark.parametrize(
    "rule,fix",
    [
        ("last_name", {"step": "debtor_info"}),
        ("family_size", {"step": "debtor_info"}),  # household size is asked with the name
        ("cmi", {"step": "income_info"}),
        ("schedule_j_monthly_net_income", {"step": "income_info"}),  # the earlier of two
        ("schedule_j_utilities_label", {"step": "expense_info"}),
        ("fee_waiver_monthly_expenses", {"step": "expense_info"}),  # 103B line 6 is J 22c
        ("other_asset_descriptions", {"step": "assets"}),
        ("total_debts", {"step": "debts"}),
        ("fee_waiver_benefit_types", {"page": "/fee-waiver"}),
        ("district_name", {}),  # the district list is DigniFi's
        ("line13a_median_income", {}),  # the median table is DigniFi's
        ("schedule_i_occupation_debtor1", {}),  # reads a field no model has: always blank
    ],
)
def test_a_rule_links_to_where_its_input_is_entered(rule, fix):
    assert RULE_FIXES[rule] == fix


@pytest.mark.parametrize(
    "field,fix",
    [
        (_field("derived", rule="last_name"), {"step": "debtor_info"}),
        (_field("asked", binding="answer:form_107.gift_description"), {"page": "/ask/form_107"}),
        (_field("asked", binding="sofa.creditor_payments[].creditor_name"), {"page": "/sofa"}),
        (_field("ingested", ingest_key="paystub.employer_name"), {"page": "/documents"}),
        (_field("db_aggregate", ingest_key="paystub.employer_name"), {"page": "/documents"}),
        (_field("constant", value="Individual"), {}),
        (_field("signature"), {}),
    ],
    ids=["derived", "answer", "sofa", "ingested", "db_aggregate", "constant", "signature"],
)
def test_a_refusal_sends_the_filer_to_where_the_value_came_from(field, fix):
    assert fix_for(field) == fix


def test_changing_a_refusals_fix_leaves_the_map_alone():
    fix = fix_for(_field("derived", rule="last_name"))
    fix["step"] = "review"
    assert RULE_FIXES["last_name"] == {"step": "debtor_info"}


def test_an_answer_is_fixed_on_the_form_that_asks_it():
    # Form 107 prints Form 101's preparer answer: the filer changes it on 101's questions.
    preparer = next(
        field
        for field in load_schema("form_107").fields
        if field.binding == "answer:form_101.preparer_name"
    )
    assert fix_for(preparer) == {"page": "/ask/form_101"}
```

The fix-map tests check two things. Every derived rule bound to a text or choice box must link to a wizard step or one of the four pages. Each source kind must link where spec §4.5's table says.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_form_views.py b/backend/apps/forms/tests/test_form_views.py
index bfa22bf..a218195 100644
--- a/backend/apps/forms/tests/test_form_views.py
+++ b/backend/apps/forms/tests/test_form_views.py
@@ -37,6 +37,8 @@ from apps.forms.services.pdf_filler import (
     PDFFormFiller,
     TemplateHasNoForm,
     UnknownField,
+    UnprintableLetter,
+    ValueTooLong,
 )
 from apps.forms.tests.pdf_readback import read_widgets
 from apps.intake.models import (
@@ -351,6 +353,47 @@ class TestGenerateEndpoint:
         assert type(exc).__name__ in caplog.text
         assert "Debtor1.SSNum" not in caplog.text

+    # A letter the form can't print, or a value too long for its box, is the filer's to
+    # change: a 422 naming the box and where to change it. It is no fault, so nothing is
+    # logged, and the filer's letter never reaches the logs (DIG-105).
+    @pytest.mark.parametrize(
+        "exc,refusal",
+        [
+            (
+                UnprintableLetter("form_101", "ą", "Last name", {"step": "debtor_info"}),
+                {
+                    "error": "The court form can't print the letter “ą” in “Last name”. "
+                    "Change it to a letter without the mark.",
+                    "step": "debtor_info",
+                },
+            ),
+            (
+                ValueTooLong("form_101", "Type of assistance", {"page": "/fee-waiver"}),
+                {
+                    "error": "“Type of assistance” is too long to fit on the court form, "
+                    "even in small print. Shorten it.",
+                    "page": "/fee-waiver",
+                },
+            ),
+        ],
+        ids=["unprintable_letter", "value_too_long"],
+    )
+    def test_a_refused_letter_or_length_names_where_to_fix_it(
+        self, api_client, session_with_debtor, caplog, exc, refusal
+    ):
+        caplog.set_level(logging.DEBUG)
+        with patch.object(PDFFormFiller, "fill", side_effect=exc):
+            resp = api_client.post(
+                self.URL,
+                {"session_id": session_with_debtor.id, "form_type": "form_101"},
+                format="json",
+            )
+        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
+        assert resp.data == {"form_type": "form_101", **refusal}
+        assert not [r for r in caplog.records if r.name.startswith("apps.")]
+        assert exc.label not in caplog.text
+        assert "ą" not in caplog.text
+
     def test_unexpected_failure_points_the_filer_to_no_step_or_page(
         self, api_client, session_with_debtor
     ):
PATCH
```

Both refusals must come back from Generate as a 422 with the sentence, the step or page, and nothing in the logs.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_pdf_filler.py b/backend/apps/forms/tests/test_pdf_filler.py
index 828fdff..712f83f 100644
--- a/backend/apps/forms/tests/test_pdf_filler.py
+++ b/backend/apps/forms/tests/test_pdf_filler.py
@@ -10,6 +10,7 @@ from io import BytesIO

 import pypdf
 import pytest
+from pypdf._font import Font

 from apps.forms.services.pdf_filler import (
     InvalidFieldValue,
@@ -17,6 +18,7 @@ from apps.forms.services.pdf_filler import (
     TemplateHasNoForm,
     UnknownField,
 )
+from apps.forms.services.text_fit import font_for
 from apps.forms.tests.pdf_readback import read_widgets


@@ -51,6 +53,18 @@ def test_text_prints_from_a_stored_appearance():
     assert b"Maria" in widget["/AP"]["/N"].get_data()


+def test_text_is_measured_with_pinned_pypdf_font_internals():
+    """check() measures and encodes with pypdf 6.13.1's Font, as the drawing does; this pins it."""
+    assert pypdf.__version__ == "6.13.1"
+    font = font_for("form_b121.pdf", "/Helv")  # Font.from_font_resource
+    assert isinstance(font, Font)
+    reverse_cmap, _ = font._get_typographic_maps()
+    assert font.get_text_width(reverse_cmap["W"]) == 944  # Helvetica's W
+    assert font.can_encode("é") and not font.can_encode("ą")
+    bbox = font.font_descriptor.bbox
+    assert (bbox[1], bbox[3]) == (-225, 931)  # its line spacing
+
+
 def test_checkbox_ticks_only_the_widgets_for_its_state():
     pdf = PDFFormFiller().fill("form_101", {"Check Box1": "/Chapter 7"})
     states = [w.state for w in read_widgets(pdf) if w.full_name == "Check Box1"]
PATCH
```

The pin test fails if pypdf moves the font internals the measuring uses.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
cd backend && $PY -m pytest --tb=line -rfE --continue-on-collection-errors apps/forms/tests/test_check.py apps/forms/tests/test_rule_fixes.py apps/forms/tests/test_form_views.py apps/forms/tests/test_pdf_filler.py -q -p no:cacheprovider 2>&1 | grep -E '^E  |ERROR collecting|^FAILED|^=+ .* in [0-9.]+s'
```

Expected: FAIL — `4 errors in`. None of the four files can be collected, because each imports a name this task adds:

- `test_check.py` and `test_form_views.py` stop on `ImportError: cannot import name 'UnprintableLetter' from 'apps.forms.services.pdf_filler'`.
- `test_rule_fixes.py` stops on `ImportError: cannot import name 'RULE_FIXES' from 'apps.forms.services.derivations'`.
- `test_pdf_filler.py` stops on `ModuleNotFoundError: No module named 'apps.forms.services.text_fit'`.

The 63 tests already in `test_form_views.py` (54) and `test_pdf_filler.py` (9) wait on the same imports, so no test runs.

- [ ] **Step 3: Map every bound rule to where its input is entered**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/derivations.py b/backend/apps/forms/services/derivations.py
index b253e4f..d32a1cb 100644
--- a/backend/apps/forms/services/derivations.py
+++ b/backend/apps/forms/services/derivations.py
@@ -668,6 +668,108 @@ DERIVATIONS: dict[str, Callable[[IntakeSession], str]] = {
 }


+# ---------------------------------------------------------------------------
+# RULE_FIXES — where the filer changes what a rule prints (3a2 spec §4.5)
+# ---------------------------------------------------------------------------
+
+# Every rule bound to a text or choice box, with where a refusal of its value (a letter
+# the form can't print, a value too long for its box) sends the filer: the wizard step
+# ({"step": <a WIZARD_STEPS key>}) or page ({"page": <path>}) that holds the rule's input.
+# {} links nowhere: no filer edits the input. test_rule_fixes.py fails on a bound rule
+# missing here.
+RULE_FIXES: dict[str, dict[str, str]] = {
+    # Your Information
+    "full_name": {"step": "debtor_info"},
+    "first_name": {"step": "debtor_info"},
+    "middle_name": {"step": "debtor_info"},
+    "last_name": {"step": "debtor_info"},
+    "street_address": {"step": "debtor_info"},
+    "city": {"step": "debtor_info"},
+    "state": {"step": "debtor_info"},
+    "zip_code": {"step": "debtor_info"},
+    "phone": {"step": "debtor_info"},
+    "email": {"step": "debtor_info"},
+    "ssn_last_4": {"step": "debtor_info"},
+    "ssn_formatted": {"step": "debtor_info"},
+    "family_size": {"step": "debtor_info"},
+    # Income
+    "cmi": {"step": "income_info"},
+    "line12b_annualized_cmi": {"step": "income_info"},
+    "line1_wages": {"step": "income_info"},
+    "line3_alimony": {"step": "income_info"},
+    "line3_real_property_income": {"step": "income_info"},
+    "line5a_pension_retirement": {"step": "income_info"},
+    "line6a_unemployment": {"step": "income_info"},
+    "line6b_child_support_alimony": {"step": "income_info"},
+    "line7_other_income": {"step": "income_info"},
+    "other_income_label": {"step": "income_info"},
+    "schedule_i_net_wages_debtor1": {"step": "income_info"},
+    "schedule_i_overtime_debtor1": {"step": "income_info"},
+    "schedule_i_gross_income_debtor1": {"step": "income_info"},
+    "schedule_i_unemployment_debtor1": {"step": "income_info"},
+    "schedule_i_social_security_debtor1": {"step": "income_info"},
+    "schedule_i_pension_debtor1": {"step": "income_info"},
+    "schedule_i_child_support_debtor1": {"step": "income_info"},
+    "schedule_i_rental_debtor1": {"step": "income_info"},
+    "schedule_i_other_income_debtor1": {"step": "income_info"},
+    "schedule_i_other_income_total_debtor1": {"step": "income_info"},
+    "schedule_i_income_total": {"step": "income_info"},
+    "schedule_j_total_income": {"step": "income_info"},
+    # Income less expenses: the earlier of its two steps
+    "schedule_j_monthly_net_income": {"step": "income_info"},
+    # Expenses
+    "schedule_j_rent_or_mortgage": {"step": "expense_info"},
+    "schedule_j_utilities": {"step": "expense_info"},
+    "schedule_j_utilities_label": {"step": "expense_info"},
+    "schedule_j_home_maintenance": {"step": "expense_info"},
+    "schedule_j_food_and_groceries": {"step": "expense_info"},
+    "schedule_j_childcare": {"step": "expense_info"},
+    "schedule_j_clothing": {"step": "expense_info"},
+    "schedule_j_medical_expenses": {"step": "expense_info"},
+    "schedule_j_vehicle_maintenance": {"step": "expense_info"},
+    "schedule_j_vehicle_payment": {"step": "expense_info"},
+    "schedule_j_vehicle_insurance": {"step": "expense_info"},
+    "schedule_j_insurance_not_deducted": {"step": "expense_info"},
+    "schedule_j_insurance_label": {"step": "expense_info"},
+    "schedule_j_support_paid": {"step": "expense_info"},
+    "schedule_j_other_expenses": {"step": "expense_info"},
+    "schedule_j_total_expenses": {"step": "expense_info"},
+    "total_monthly_expenses": {"step": "expense_info"},
+    # 103B line 6 is Schedule J line 22c, from the Expenses step
+    "fee_waiver_monthly_expenses": {"step": "expense_info"},
+    # Assets
+    "total_real_property": {"step": "assets"},
+    "total_personal_property": {"step": "assets"},
+    "total_assets": {"step": "assets"},
+    "total_other_assets": {"step": "assets"},
+    "total_vehicles": {"step": "assets"},
+    "total_household_items": {"step": "assets"},
+    "total_financial_assets": {"step": "assets"},
+    "other_asset_descriptions": {"step": "assets"},
+    # Amounts Owed
+    "total_secured_debts": {"step": "debts"},
+    "total_secured_claims": {"step": "debts"},
+    "total_debts": {"step": "debts"},
+    "total_nonpriority_unsecured": {"step": "debts"},
+    "total_student_loans": {"step": "debts"},
+    "total_other_nonpriority": {"step": "debts"},
+    # The fee-waiver application
+    "fee_waiver_household_size": {"page": "/fee-waiver"},
+    "fee_waiver_monthly_income": {"page": "/fee-waiver"},
+    "fee_waiver_benefit_types": {"page": "/fee-waiver"},
+    # No link. The district and its median income table come from DigniFi's own data.
+    # The Schedule I occupation and employer address read fields no model has, so they
+    # always print blank.
+    "district_name": {},
+    "line13a_median_income": {},
+    "schedule_i_occupation_debtor1": {},
+    "schedule_i_employer_street_debtor1": {},
+    "schedule_i_employer_city_debtor1": {},
+    "schedule_i_employer_state_debtor1": {},
+    "schedule_i_employer_zip_debtor1": {},
+}
+
+
 # ---------------------------------------------------------------------------
 # PREDICATES — section-applicability checks
 # ---------------------------------------------------------------------------
PATCH
```

`RULE_FIXES` sits right after `DERIVATIONS`. Each of the 78 rules bound to a text or choice box gets the wizard step or page that holds its input, or `{}` when no filer edits that input (R10, R11).

- [ ] **Step 4: Say where the filer fixes each binding's value**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/fill_resolver.py b/backend/apps/forms/services/fill_resolver.py
index 452a718..f5ffd16 100644
--- a/backend/apps/forms/services/fill_resolver.py
+++ b/backend/apps/forms/services/fill_resolver.py
@@ -10,7 +10,7 @@ ingested/signature). This module resolves ``binding`` references; resolve()
 from __future__ import annotations

 from apps.forms.schema import FieldSpec, FormSchema
-from apps.forms.services.derivations import DERIVATIONS, PREDICATES
+from apps.forms.services.derivations import DERIVATIONS, PREDICATES, RULE_FIXES
 from apps.intake.models import FormAnswer, IntakeSession


@@ -119,6 +119,27 @@ def _key(field: FieldSpec) -> str:
     return f"{field.pdf_field}@{field.page}:{field.tag}"


+def fix_for(field: FieldSpec) -> dict[str, str]:
+    """
+    Where the filer changes a binding's value, for a refusal to link to (3a2 spec §4.5):
+    {"step": <a WIZARD_STEPS key>}, {"page": <path>}, or {} when no filer edits it.
+    """
+    if field.source == "derived":
+        return dict(RULE_FIXES[field.rule])  # a copy: the map is shared by every refusal
+    if field.source in ("ingested", "db_aggregate"):
+        return {"page": "/documents"}
+    binding = (field.binding or "").strip()
+    if binding.startswith("answer:"):
+        # The form the binding names, which isn't always the one printing it: Form 101's
+        # preparer prints on 106Dec and 107 too.
+        form_type, _, _ = binding[len("answer:") :].partition(".")
+        return {"page": f"/ask/{form_type}"}
+    if binding.startswith("sofa."):
+        return {"page": "/sofa"}
+    # A constant or a signature: a refusal there is DigniFi's defect, not the filer's.
+    return {}
+
+
 def _unmapped(field: FieldSpec) -> bool:
     """A checkbox or radio binding whose choices are not mapped yet emits nothing."""
     return field.type in ("checkbox", "radio") and not field.choices
PATCH
```

`fix_for()` turns a binding into its refusal's link, following spec §4.5's table. A derived rule gets a copy of its `RULE_FIXES` entry. An answer goes to the questions page of the form its binding names (R9).

- [ ] **Step 5: Measure text the way pypdf lays it out**

```python file=backend/apps/forms/services/text_fit.py
"""
Fitting a value into a template's text box the way pypdf will draw it.

check() (apps.forms.services.pdf_filler) plans each text and combo box with these
functions, without drawing: whether the box's font can print a letter, and the
largest size, from the box's own down to 6 pt, at which the value fits. They mirror
the layout of pypdf 6.13.1's TextStreamAppearance (pypdf/generic/_appearance_stream.py):
the same font, glyph widths, padding, line spacing and clip.
"""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import pypdf
from django.conf import settings

# pypdf internal, pinned with pypdf==6.13.1; test_pdf_filler.py fails if it moves.
from pypdf._font import Font

from apps.forms.services.widgets import TemplateWidget

MIN_SIZE = 6.0  # the smallest print a value shrinks to
STEP = 0.5  # the size steps from a box's own size down to MIN_SIZE
_MULTILINE_AUTO_SIZE = 12.0  # where pypdf's auto size starts a multi-line box


@lru_cache(maxsize=64)
def font_for(template_filename: str, font_name: str) -> Font:
    """The font a /DA names, from the template's /AcroForm /DR, as pypdf builds it."""
    reader = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template_filename)
    return Font.from_font_resource(reader.root_object["/AcroForm"]["/DR"]["/Font"][font_name])


def printable(font: Font, letter: str) -> bool:
    """The font's encoding has the letter: pypdf draws it, not "?" or another glyph (R7)."""
    return font.can_encode(letter)


def _escaped(text: str) -> str:
    """The text pypdf lays out: from_text_annotation escapes \\, ( and ) before measuring."""
    return text.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")


def _width(font: Font, reverse_cmap: dict[str, str], text: str, size: float) -> float:
    """The width in points pypdf gives text at size: each character's glyph, then its width."""
    glyphs = "".join(reverse_cmap.get(character, character) for character in _escaped(text))
    return font.get_text_width(glyphs) * size / 1000


def _leading(font: Font) -> float:
    """pypdf's line spacing per point of size, from the font's bounding box."""
    bbox = font.font_descriptor.bbox
    return (bbox[3] - bbox[1]) / 1000


def wrap(font: Font, text: str, size: float, width: float) -> list[str] | None:
    """
    One paragraph broken at spaces into lines no wider than width at size, each line
    taking as many words as fit. Spaces are kept as typed, except one at each break.

    Returns None when a word is wider than width.
    """
    reverse_cmap, _ = font._get_typographic_maps()
    lines: list[str] = []
    line: str | None = None
    for word in text.split(" "):
        if _width(font, reverse_cmap, word, size) > width:
            return None
        joined = word if line is None else f"{line} {word}"
        if line is None or _width(font, reverse_cmap, joined, size) <= width:
            line = joined
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def _sizes(start: float) -> list[float]:
    """The start, then each 0.5 pt step below it down to MIN_SIZE: [9.3, 9.0, 8.5, …, 6.0]."""
    sizes = [start]
    size = math.floor(start / STEP) * STEP
    if size == start:
        size -= STEP
    while size >= MIN_SIZE:
        sizes.append(size)
        size -= STEP
    return [size for size in sizes if size >= MIN_SIZE]


def fit(widget: TemplateWidget, font: Font, text: str) -> tuple[str, float] | None:
    """
    The text as the box will draw it and the size to draw it at: the box's own size,
    or the first 0.5 pt step below it at which the text fits, down to 6 pt.

    A line break starts a new line in a multi-line box and is a space in any other
    box. Returns None when the text fits at no size.
    """
    reverse_cmap, _ = font._get_typographic_maps()
    field_width = widget.width - 4 * widget.margin
    paragraphs = text.splitlines()
    text = "\n".join(paragraphs) if widget.multiline else " ".join(paragraphs)
    if widget.max_len is not None and not widget.comb and len(text) > widget.max_len:
        return None

    if widget.size:
        start = widget.size
    elif widget.multiline:
        start = _MULTILINE_AUTO_SIZE
    else:  # pypdf's auto size: as large as the box's height and width both allow
        at_one_point = _width(font, reverse_cmap, text, 1)
        field_height = widget.height - 2 * widget.margin
        start = round(min(field_height / _leading(font), field_width / (at_one_point or 1)), 1)
    sizes = _sizes(start)

    if widget.comb:
        # Each character has its own cell, so a smaller size can't make room.
        if sizes and (widget.max_len is None or len(_escaped(text)) <= widget.max_len):
            return text, sizes[0]
        return None
    for size in sizes:
        if not widget.multiline:
            if _width(font, reverse_cmap, text, size) <= field_width:
                return text, size
            continue
        wrapped = [wrap(font, paragraph, size, field_width) for paragraph in paragraphs]
        if None in wrapped:
            continue
        lines = [line for paragraph in wrapped for line in paragraph]
        # Each line takes one line height below line 1, which T3 lowers by 2 × margin so the
        # font's top sits at the clip's top (R35): the last line then stays above its bottom.
        if len(lines) * size * _leading(font) <= widget.height - 2 * widget.margin:
            return "\n".join(lines), size
    return None
```

`text_fit.py` holds pypdf 6.13.1's layout arithmetic, so the check measures exactly what the drawing will print.

- `font_for()` builds the AcroForm's font once per template and font name (R32).
- `_width()` measures the escaped text through the font's reverse map (R33).
- `fit()` starts at the box's own size, or where pypdf's auto size would, and walks down the 0.5 pt grid to 6 pt.

  - A single-line box is checked on width.
  - A comb box is checked on its cells, at the start size only.
  - A multi-line box is wrapped by `wrap()`, and its lines are checked against the height less two margins (R35).

- [ ] **Step 6: Plan every widget, and refuse what can't print**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
index da43d88..7cf5957 100644
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -7,22 +7,44 @@ update_page_form_field_values also matches a parent's partial /T, which put
 the filer's name and dates in Debtor 2 boxes (DIG-63), so the filler walks the
 widgets itself.

+check() plans what each widget a values dict fills will print, and at what size,
+without drawing. It refuses a letter a box's font can't print and a value too long
+for its box even in small print, naming the box and where the filer fixes the value.
+
 Usage:
     pdf_bytes = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
+    plan = PDFFormFiller().check("form_121", {"Debtor1.First name": "Maria"})
 """

+import unicodedata
+from dataclasses import dataclass
 from io import BytesIO
 from pathlib import Path

 import pypdf
 from django.conf import settings
-from pypdf.generic import DictionaryObject, NameObject, TextStringObject

-# pypdf internal, pinned with pypdf==6.13.1; test_pdf_filler.py fails if it moves.
+# pypdf._font and pypdf.generic._appearance_stream are pypdf internals, pinned with
+# pypdf==6.13.1; test_pdf_filler.py fails if they move.
+from pypdf._font import Font
+from pypdf.generic import DictionaryObject, NameObject, TextStringObject
 from pypdf.generic._appearance_stream import TextStreamAppearance

-from apps.forms.schema import load_schema
-from apps.forms.services.widgets import field_of, qualified_name
+from apps.forms.field_index import load_index
+from apps.forms.schema import FormSchema, load_schema
+from apps.forms.services.fill_resolver import fix_for
+from apps.forms.services.text_fit import fit, font_for, printable
+from apps.forms.services.widgets import (
+    TemplateWidget,
+    field_of,
+    parse_key,
+    qualified_name,
+    template_widgets,
+)
+
+_BOXES = ("CheckBox", "RadioButton")
+# pypdf draws each character of a comb box as its own string, which these break (R33).
+_COMB_BREAKERS = "()\\"


 class UnknownField(Exception):
@@ -51,9 +73,178 @@ class InvalidFieldValue(Exception):
         super().__init__(f"{form_type}: {name!r} can't take this value")


+class UnprintableLetter(Exception):
+    """A value has a letter its box can't print: pypdf would draw "?" or another glyph."""
+
+    def __init__(self, form_type: str, letter: str, label: str, fix: dict[str, str]):
+        self.form_type = form_type
+        self.letter = letter
+        self.label = label
+        self.step = fix.get("step")
+        self.page = fix.get("page")
+        super().__init__(
+            f"The court form can't print the letter “{letter}” in “{label}”. "
+            "Change it to a letter without the mark."
+        )
+
+
+class ValueTooLong(Exception):
+    """A value doesn't fit its box even at the smallest size, 6 pt."""
+
+    def __init__(self, form_type: str, label: str, fix: dict[str, str]):
+        self.form_type = form_type
+        self.label = label
+        self.step = fix.get("step")
+        self.page = fix.get("page")
+        super().__init__(
+            f"“{label}” is too long to fit on the court form, even in small print. Shorten it."
+        )
+
+
+@dataclass(frozen=True)
+class Planned:
+    """What one widget prints."""
+
+    widget: TemplateWidget
+    # Text as drawn (a multi-line box's lines joined by "\n"), a box's state or "/Off",
+    # or a combo's option.
+    value: str
+    size: float | None  # None for a box
+
+
+@dataclass(frozen=True)
+class PlannedPart:
+    """One part of a form's values, and what each widget it fills prints."""
+
+    part: dict  # the part as given: {"kind": "form", "values": {...}}
+    widgets: tuple[Planned, ...]
+
+
+def _source(schema: FormSchema, key: str, widget: TemplateWidget) -> tuple[str, dict[str, str]]:
+    """
+    The box's label and where the filer fixes its value, from the binding that produced
+    the key. A key no binding produced (a test's, the oracle's) gets the index row's
+    label and no fix.
+    """
+    name, page, tag = parse_key(key)
+    for field in schema.fields:
+        if field.pdf_field == name and field.tag == tag and (tag is None or field.page == page):
+            return field.label, fix_for(field)
+    row = next(
+        row
+        for row in load_index(schema.template_filename)[name]
+        if (row.page, row.tag) == (widget.page, widget.tag)
+    )
+    return row.label, {}
+
+
+def _as_printed(text: str) -> str:
+    """
+    The text with every space (a tab, or any Unicode space separator) as a plain space,
+    and format characters such as a soft hyphen left out: the template's font has no
+    glyph for them, and draws U+00A0 as € (R34, R36).
+    """
+    return "".join(
+        " " if letter == "\t" or unicodedata.category(letter) == "Zs" else letter
+        for letter in text
+        if unicodedata.category(letter) != "Cf"
+    )
+
+
+def _refused_letter(widget: TemplateWidget, font: Font, text: str) -> str | None:
+    """
+    The first character the box can't print: one its font can't encode, a control
+    character, or in a comb box ( ) or \\. Line breaks aren't letters (G15).
+    """
+    for letter in "".join(text.splitlines()):
+        if (
+            not printable(font, letter)
+            or unicodedata.category(letter) == "Cc"
+            or (widget.comb and letter in _COMB_BREAKERS)
+        ):
+            return letter
+    return None
+
+
 class PDFFormFiller:
     """Fill AO court PDF templates with field values and return bytes."""

+    def check(self, form_type: str, values: dict) -> tuple[PlannedPart, ...]:
+        """
+        Plan what each widget the values fill prints, without drawing.
+
+        Args:
+            form_type: a registered form type; its schema names the template.
+            values: {key: value}. A key is a full name, which fills every drawn widget
+                of that name, or "<full name>@<page>:<tag>", which fills that one
+                widget and wins over the full name there. A value is text, a combo's
+                option, or a box's export state such as "/Chapter 7".
+
+        Returns:
+            One part, holding every widget a key fills in page and tag order: a text
+            or combo box with its text as drawn and its size, a box with its state or
+            "/Off".
+
+        Raises:
+            UnknownField: a key names no drawn widget, or is neither form of key.
+            InvalidFieldValue: a box state or combo option the template lacks.
+            UnprintableLetter: a letter the box can't print.
+            ValueTooLong: a value too long for its box even at 6 pt.
+        """
+        schema = load_schema(form_type)
+        by_name: dict[str, list[TemplateWidget]] = {}
+        for widget in template_widgets(schema.template_filename):
+            if widget.drawn:
+                by_name.setdefault(widget.full_name, []).append(widget)
+
+        reached: dict[str, list[TemplateWidget]] = {}
+        unknown = []
+        for key in values:
+            try:
+                name, page, tag = parse_key(key)
+            except ValueError:
+                unknown.append(key)
+                continue
+            reached[key] = [
+                widget
+                for widget in by_name.get(name, ())
+                if tag is None or (widget.page, widget.tag) == (page, tag)
+            ]
+            if not reached[key]:
+                unknown.append(key)
+        if unknown:
+            raise UnknownField(form_type, sorted(unknown))
+
+        for key, widgets in reached.items():
+            if widgets[0].kind in _BOXES and not any(values[key] in w.states for w in widgets):
+                raise InvalidFieldValue(form_type, widgets[0].full_name)
+
+        # Full names first, so a widget's own key overrides its name's.
+        filled_by: dict[TemplateWidget, str] = {}
+        for key in sorted(reached, key=lambda key: "@" in key):
+            for widget in reached[key]:
+                filled_by[widget] = key
+
+        planned = []
+        for widget in sorted(filled_by, key=lambda w: (w.page, int(w.tag[1:]))):
+            key = filled_by[widget]
+            value = values[key]
+            if widget.kind in _BOXES:
+                planned.append(Planned(widget, value if value in widget.states else "/Off", None))
+                continue
+            if widget.kind == "ComboBox" and value not in widget.options:
+                raise InvalidFieldValue(form_type, widget.full_name)
+            font = font_for(schema.template_filename, widget.font)
+            text = _as_printed(value)
+            letter = _refused_letter(widget, font, text)
+            if letter is not None:
+                raise UnprintableLetter(form_type, letter, *_source(schema, key, widget))
+            fitted = fit(widget, font, text)
+            if fitted is None:
+                raise ValueTooLong(form_type, *_source(schema, key, widget))
+            planned.append(Planned(widget, *fitted))
+        return (PlannedPart({"kind": "form", "values": values}, tuple(planned)),)
+
     def fill(self, form_type: str, field_values: dict[str, str]) -> bytes:
         """
         Fill the form's template with field_values and return the PDF bytes.
PATCH
```

`check()` resolves each key to its drawn widgets; a widget's own key wins over its full name. It plans boxes as `fill()` ticks them. For each text or combo widget, in page order, it turns every space character into a plain space and drops format characters (R36), refuses a letter the font can't encode, a control character or a comb breaker (R33), and fits the rest. `_source()` names a refused box by its binding's label and fix, or by its index row's label.

- [ ] **Step 7: Make both refusals a 422 that names the fix**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/views.py b/backend/apps/forms/views.py
index 09727ec..46ebf11 100644
--- a/backend/apps/forms/views.py
+++ b/backend/apps/forms/views.py
@@ -36,7 +36,12 @@ from .registry import (
 from .schema import load_schema
 from .serializers import GeneratedFormSerializer
 from .services.fill_resolver import RepeatOverflow, UnmappedChoice
-from .services.pdf_filler import PDFFormFiller, TemplateHasNoForm
+from .services.pdf_filler import (
+    PDFFormFiller,
+    TemplateHasNoForm,
+    UnprintableLetter,
+    ValueTooLong,
+)

 logger = logging.getLogger(__name__)

@@ -58,7 +63,8 @@ class IntakeNotFinished(Exception):
 # Failures a filer can act on: 422 in plain words (spec §5.7). Anything else is a 500.
 # PreconditionMissing, IncomeNotSplit and NoTableInForce carry their own plain reasons
 # (registry.py, eligibility/cmi.py, districts/dated_tables.py, which logs its own
-# refusal). Every other class gets a fixed sentence, because their messages
+# refusal), and so do UnprintableLetter and ValueTooLong (pdf_filler.py), which name the
+# letter and the box. Every other class gets a fixed sentence, because their messages
 # name form keys, repeat groups and PDF widgets. None names the form: the dashboard shows
 # its label beside the error.
 _FAILURE_SENTENCES = {
@@ -84,7 +90,10 @@ def _failure(form_type: str | None, exc: Exception) -> tuple[dict, int]:
     All, the packet list): the body then names no form. A refusal the filer fixes on a
     wizard step or a page also carries that `step` or `page` (forms step 3a1 spec §4.3).
     """
-    if isinstance(exc, PreconditionMissing | IncomeNotSplit | NoTableInForce):
+    if isinstance(
+        exc,
+        PreconditionMissing | IncomeNotSplit | NoTableInForce | UnprintableLetter | ValueTooLong,
+    ):
         error = str(exc)
     else:
         error = _FAILURE_SENTENCES.get(type(exc))
PATCH
```

`_failure` returns the refusal's own sentence with its `step` or `page` and logs nothing, as it already does for `PreconditionMissing`.

- [ ] **Step 8: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
cd backend && $PY -m pytest --tb=line -rfE --continue-on-collection-errors apps/forms/tests/test_check.py apps/forms/tests/test_rule_fixes.py apps/forms/tests/test_form_views.py apps/forms/tests/test_pdf_filler.py -q -p no:cacheprovider 2>&1 | grep -E '^E  |ERROR collecting|^FAILED|^=+ .* in [0-9.]+s'
```

Expected: `126 passed`.

That is this task's 63 new cases (38 in `test_check.py`, 22 in `test_rule_fixes.py`, 2 in `test_form_views.py` and 1 in `test_pdf_filler.py`) and the 63 that Step 2's imports held back.

- [ ] **Step 9: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2261 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  397 passed (397)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

That is 63 more backend cases than after Task 1: 38 in `test_check.py`, 22 in `test_rule_fixes.py`, 2 in `test_form_views.py` and 1 in `test_pdf_filler.py`. The 25 skips are the Postgres-only tests under sqlite. The next command runs them against the Postgres database named by `DATABASE_URL` in `.claude/forms-step3a2.env`, as CI's "Run the Postgres-only tests" step does. This task touches no locking, so they pass unchanged.

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

This task changes no page flow and no drawing, so the journeys don't run.

- [ ] **Step 10: Commit**

```bash
set -eo pipefail
git add \
  backend/apps/forms/services/text_fit.py \
  backend/apps/forms/tests/test_check.py \
  backend/apps/forms/tests/test_rule_fixes.py \
  backend/apps/forms/services/derivations.py \
  backend/apps/forms/services/fill_resolver.py \
  backend/apps/forms/services/pdf_filler.py \
  backend/apps/forms/tests/test_form_views.py \
  backend/apps/forms/tests/test_pdf_filler.py \
  backend/apps/forms/views.py
git commit -F - <<'MSG'
feat(forms): check what each box prints, and refuse what it can't

Today a letter the court form's font lacks prints as "?" and a value
wider than its box is cut off at the edge, both silently.
PDFFormFiller.check() plans what each widget a values dict fills
prints, and at what size, without drawing, so the drawing (next) can
refuse those values first. Nothing calls it yet.

A key is a full name, which fills every drawn widget of that name, or
"<full name>@<page>:<tag>", which fills that one widget and wins over
the full name there. A key that names no drawn widget, or isn't a key
at all, is UnknownField, and a box state or combo option the template
lacks is InvalidFieldValue, as in fill().

For a text or combo box, apps/forms/services/text_fit.py measures as
pypdf 6.13.1 lays text out: the AcroForm's /Helv, its glyph widths on
the string pypdf escapes, its padding, line spacing and clip.
- A letter the font can't encode, or a control character, is
  UnprintableLetter. A comb box also refuses (, ) and \, which break
  pypdf's one-string-per-cell drawing. A tab or any other space
  character prints as a plain space (the form's font draws U+00A0 as
  the euro sign), and a format character such as a soft hyphen, which
  prints nothing, is left out.
- A value starts at the box's own size (an auto-size box where pypdf
  would size it) and shrinks in 0.5 pt steps down to 6 pt. A
  single-line box prints a line break as a space. A multi-line box
  wraps at spaces, since pypdf wraps only auto-size boxes, and its
  lines must fit the box's height less two margins: the drawing will
  lower the first line by that much, so the mark on a capital such as
  É isn't cut off at the top. A comb box fits its cells or nothing,
  and any other box with a MaxLen fits that many characters. A value
  that fits at no size is ValueTooLong.

Each refusal names the box by its schema label, with the sentence the
spec gives, and carries where the filer fixes the value. fix_for()
gives that from the binding: a derived rule from RULE_FIXES, a new map
beside DERIVATIONS of every rule bound to a text or choice box to the
wizard step or page that holds its input; an asked answer from the
questions page of the form it names; SOFA from /sofa; a scanned value
from /documents; a constant nothing. _failure() makes both refusals a
422 with that step or page, and logs nothing.

The six seeded personas' packets pass check() with no refusal; the
seven values cut off today shrink instead. test_pdf_filler pins the
pypdf Font names the measuring uses.
MSG
git status --short
```

### Task 3: Draw each widget's own value and bake it into the page

_Built and verified as commit `e788e43` on `plan/forms-step3a2`._

**Files:**

- Modify: `CLAUDE.md`
- Modify: `backend/apps/forms/services/pdf_filler.py`
- Modify: `backend/apps/forms/tests/pdf_readback.py`
- Modify: `backend/apps/forms/tests/test_consumer_debts_and_paid_help.py`
- Modify: `backend/apps/forms/tests/test_download_action.py`
- Modify: `backend/apps/forms/tests/test_form_101_schema.py`
- Modify: `backend/apps/forms/tests/test_form_103b_answers.py`
- Modify: `backend/apps/forms/tests/test_form_106sum_schema.py`
- Modify: `backend/apps/forms/tests/test_form_107_schema.py`
- Modify: `backend/apps/forms/tests/test_form_views.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier1.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier3.py`
- Modify: `backend/apps/forms/tests/test_pdf_filler.py`
- Modify: `backend/apps/forms/tests/test_schedule_a_b_schema.py`
- Modify: `backend/apps/forms/tests/test_schedules_d_e_f_schema.py`
- Modify: `backend/apps/forms/tests/test_schedules_g_h_schema.py`
- Modify: `backend/apps/forms/tests/test_signing_lines.py`
- Modify: `backend/requirements/base.txt`
- Modify: `docs/superpowers/specs/2026-10-16-forms-step3-design.md`

**Interfaces:**

- Consumes:
  - From Task 1, `backend/apps/forms/services/widgets.py`:
    - `TemplateWidget`. The drawing reads its `page`, `tag`, `kind`, `drawn`, `align`, `comb`, `max_len`, `multiline` and `margin`; `read_drawn` reads `full_name`, `page`, `tag`, `rect`, `kind`, `states` and `comb`; the tests also read `key`, `size` and `drawn`.
    - `template_widgets(template_filename: str) -> tuple[TemplateWidget, ...]` (`@lru_cache(maxsize=32)`, ordered by page then tag number).
    - `widget_for(template_filename: str, page: int, annotation: DictionaryObject, page_top: float) -> TemplateWidget`, called with the page's number (from 1) and `float(page.mediabox.top)`.
    - `field_of(annotation: DictionaryObject) -> DictionaryObject` and, in a test, `parse_key(key: str) -> tuple[str, int | None, str | None]`.
  - From Task 2, `backend/apps/forms/services/pdf_filler.py`:
    - `PDFFormFiller.check(self, form_type: str, values: dict) -> tuple[PlannedPart, ...]`. In this task it returns one part, whose `widgets` are `Planned(widget, value, size)` in page and tag order: a box's `value` is a state or `"/Off"` and its `size` is `None`; a text or combo box's `value` is the text as drawn (a multi-line box's lines joined by `"\n"`) and `size` the size it fits at.
    - The refusals `check()` raises: `UnknownField`, `InvalidFieldValue`, `UnprintableLetter` and `ValueTooLong`. `TemplateHasNoForm(form_type)` predates 3a2.
    - In tests, `ValueTooLong` (tier 1's sentinels).
  - `backend/apps/forms/views.py`: `_fill()` (Generate, Regenerate and Generate All) and Download's filed branch call `PDFFormFiller().fill(form_type, values)` with positional arguments. Task 2's `_failure` turns `UnprintableLetter` and `ValueTooLong` into a 422 with the sentence and the `step` or `page`.
  - pypdf 6.13.1: `PdfWriter(clone_from=...)`, `writer.root_object`, `writer.pages`, `page.mediabox.top`, `writer.write(buffer)` and the pinned internals `TextStreamAppearance.from_text_annotation(writer, page, False, acro_form, field, annotation, user_font_size=size)` (it returns a stream with `get_data()` and `set_data()`) and `PdfWriter._add_object(obj)` (G12). In tests, `PdfReader` and `NullObject`.
  - PyMuPDF 1.27.2.3, imported as `pymupdf`: `pymupdf.open("pdf", data)`, `Document.bake(annots=False, widgets=True)`, `Document.pdf_catalog()`, `Document.xref_set_key(xref, key, value)`, `Document.tobytes()`, and `Page.get_text("rawdict")`, whose blocks hold lines, whose lines hold spans with `font`, `size` and `chars`, and whose chars carry `c`, `bbox` and `origin`.
  - For the tests: `get_all_form_types()` (`apps.forms.registry`), `load_schema`, `test_download_action.py`'s `api_client_authed` and `generated_form_factory` fixtures and its `_rename_filer` helper, and `case_param` (`apps/forms/tests/oracle.py`).
- Produces:
  - `PDFFormFiller.fill(self, form_type: str, values: dict) -> bytes` in `backend/apps/forms/services/pdf_filler.py`. It was `fill(self, form_type: str, field_values: dict[str, str])`. It takes what `check()` takes, runs `check()`, draws the plan, removes the widgets that never print, bakes every other widget into its page and sets `/AcroForm` to null. The PDF it returns has no fillable field.
    - It raises `TemplateHasNoForm` before `check()` runs, then whatever `check()` raises.
    - Private helpers: `_FIRST_MOVE` (the regex for the first `<x> <y> Td`), `_lower_first_line(appearance, by: float) -> None` and `_draw(writer, page, acro_form, annotation, planned: Planned) -> None`.
  - `backend/apps/forms/tests/pdf_readback.py` (rewritten):
    - `@dataclass(frozen=True) class DrawnWidget`: `full_name: str`, `page: int`, `tag: str`, `value: str` (the Helvetica text inside the widget's rect; `""` when none) and `state: str` (a box's on-state when the template's ZapfDingbats check mark is inside it, else `"/Off"`; `""` for a text or combo box).
    - `def read_drawn(form_type: str, pdf_bytes: bytes) -> list[DrawnWidget]`: one entry per index row of the form's template, in page and tag order, undrawn widgets included. Task 6 adds a `parts` argument.
    - `read_widgets` and `FilledWidget` are deleted.
  - `pymupdf==1.27.2.3` in `backend/requirements/base.txt`.
  - Tests:
    - In `test_pdf_filler.py`: `test_the_drawn_form_has_no_fillable_field_left` (it replaces `test_text_prints_from_a_stored_appearance`), `test_a_letter_outside_latin_1_prints_on_every_box`, `test_shared_name_boxes_print_their_own_values` (2 cases), `test_a_tagged_value_prints_only_in_its_own_box` (3), `test_a_tick_reads_back_only_in_its_own_box` (4), `test_nothing_the_blank_template_prints_reads_as_a_value` (17), `test_a_shrunk_value_prints_at_its_planned_size`, `test_a_multi_line_boxs_first_line_keeps_its_capitals_marks`, `test_an_empty_multi_line_box_prints_nothing` and `test_drawing_never_logs_the_filers_text`. That is 31 new cases.
    - In `test_download_action.py`: `test_a_letter_the_form_cannot_print_refuses_the_download`.
    - Every other test that read a PDF now reads it with `read_drawn`: tiers 1 and 3, the rest of `test_pdf_filler.py` and `test_download_action.py`, the DIG-155 test in `test_form_views.py`, and nine per-form test files.

**Decisions already made in this task:**

_Scope:_

- **Every form now prints through `check()` and the drawing.** Generate, Regenerate, Generate All and Download still call `fill()` in this task, and `fill()` runs `check()` first. So a letter the form can't print, or a value too long for its box even at 6 pt, now reaches the filer as Task 2's 422 with its `step` or `page`, instead of "?" or a cut-off value. Task 5 moves Generate, Generate All and Regenerate to `check()` alone; Download keeps drawing.
  - Because the refusals now reach the filer, two `CLAUDE.md` gotchas outside tasks.md's list change too (G8; the controller accepted): "The packet decides which forms a filer gets" names the two 422s, and "Forms need a completed intake" adds their `step` or `page`, from `fix_for`.
- **`fill()`'s second parameter is now `values: dict`, as `check()` takes it.** It was `field_values: dict[str, str]`. Every caller passes it by position, and a grep found no `fill(..., field_values=...)` call anywhere (G5).
- **The clone and the `TemplateHasNoForm` test come before `check()`,** though tasks.md lists `check()` first. A template with no `/AcroForm` has no field index either (the synthetic `form_no_acroform` in `test_template_without_a_form_raises`), so `check()` would raise `FileNotFoundError` from `load_index` before the real error. The order decides only which error such a template gives. A mutation that ran `check()` first turned that test red.

_Drawing one widget (`_draw`):_

- **A box** gets its planned state in the widget's `/AS`, and in the field's `/V` only when ticked, so an `/Off` sibling drawn later never overwrites a ticked state (advisor). The template's own check mark (ZapfDingbats) prints from `/AS`.
  - A box's `/V` is never put back. Boxes carry their own `/AP`, so the bake never builds one from `/V`.
  - The implementer's probe (`t03/probe_box_tags.py`) took every box name with more than one drawn widget, 230 names and 566 widgets, and ticked each widget through its own tagged key (55 draws). Every one ticked, and all 1,218 sibling reads were `/Off`, including Form 101's `Check Box1` "/Chapter 7" on pages 1 and 3.
- **A text or combo box** is drawn in this order:
  1. A combo's stale `/I` is deleted, as before, since it would override `/V`.
  2. The widget annotation's own `/DR` is deleted (R32). On 567 widgets it holds a `/Helv` without the template's encoding, so pypdf encoded with it and printed "?" for Ł, ’ or –. It is never inherited from an ancestor (Task 2's probe 8).
  3. A comb widget without its own `/MaxLen` gets `widget.max_len`, which Task 1 inherited from the parents (R4). pypdf reads a comb box's cell count from the widget alone, so Schedule D's two `account number` boxes printed every digit in the first cell.
  4. The field's `/V` and `/Q` are set to this widget's planned value and `align` (R8, R26). pypdf reads both from the field, which siblings share, and three A/B widgets carry `/Q` on the widget only (`24.2` page 7 T8, `undefined_166` page 10 T34 and T35).
  5. `from_text_annotation(..., user_font_size=planned.size)` builds the appearance at `check()`'s size, so pypdf's own auto-size path, which goes down to 4 pt, never runs.
  6. A multi-line box's first line is lowered by `2 × margin` (R35, below).
  7. `writer._add_object()` adds the stream as the widget's `/AP /N`.
  8. The field's original `/V` is put back, or deleted if it had none (R42, below).
- **Why `/V` is put back (R42, review finding 1).** MuPDF's bake builds an appearance from the field's `/V` for any widget that has no `/AP` of its own. In the templates, 1,426 drawn text and combo widgets have none, and 66 shared fields have at least one such widget.
  - Before the fix round, `fill("form_107", {"Debtor 1@1:T1": ...})` printed the name on all 12 pages. A tagged key on Schedule I's `Time employed Debtor 1` or Schedule D's `account number` also printed in the sibling (the reviewer's probes). A leaked appearance is MuPDF's own: it never went through `check()`.
  - The same leak hid a dropped widget. Under a mutation that drew only the first widget of each shared text name, Form 101's and 107's header tests and the DIG-155 test stayed green, because MuPDF printed the missing widgets from `/V`.
  - `field.get("/V")` keeps the entry as stored, so an indirect reference goes back as one.
  - The restore is straight-line, not `try`/`finally`. The writer is local to `fill()`, so an exception discards a half-restored field (re-reviewer).
  - It doesn't change what a drawn widget prints: MuPDF keeps pypdf's stream even when `/V` no longer matches it, and `test_a_shrunk_value_prints_at_its_planned_size` passes with the restore (reviewer: 916 passed).
- **`_draw` leaves the last-drawn widget's `/Q` on a shared field** (re-review, minor). A sibling with no `/AP` and no `/V` prints nothing, so it has no effect today. If a later task gives such a sibling a value another way, `/Q` is the first thing to re-check.
- **The R35 rewrite works on the decoded stream** (`get_data()`, then `set_data()`). `_FIRST_MOVE` (`^(\S+) (\S+) Td$`, multi-line) finds the first text move, and its y operand is lowered by `2 × margin`.
  - The reviewer read pypdf 6.13.1's `_appearance_stream.py`: the stream is `q /Tx BMC q … re W BT <DA>`, then line 0's `"{x} {y} Td"` before any string. An empty value emits no `Td`, and `/Length` is recomputed on write. So the first match is always line 1's move, and a stream with none (an empty value) is left alone (R39).
  - `"\n"` is encodable in every template's `/Helv`, so the multi-line box's own `can_encode` call in pypdf never warns (reviewer).

_The page:_

- **One clone, one write, one bake** (G14). Each page's `/Annots` is rebuilt in order. Every `/Widget` is matched to its `TemplateWidget` with `widget_for`. A widget that isn't `drawn` (a print button, or the second of a stacked pair) is left out. A planned widget goes through `_draw`. Every other annotation is kept as it was.
  - A drawn widget with no value keeps the template's own appearance, so it prints as the blank form does, and 103B's empty squares stay.
- **The bake.** `pymupdf.open("pdf", ...)` reads the written bytes, `bake(annots=False, widgets=True)` turns every remaining widget into page content, `xref_set_key(pdf_catalog(), "AcroForm", "null")` nulls `/AcroForm` as the spec says, and `tobytes()` returns the PDF.
  - `tobytes()` runs without garbage collection (R41). Outputs are 1.4 to 2.1 times the template's size (Form 101: 978 KB against 720 KB; Form 107: 807 KB against 387 KB). Task 5's `time_packet` decides whether `garbage` or `deflate` fit the download budget.
  - pypdf 6.13.1's `get_fields()` raises `TypeError` on a null `/AcroForm`, so a tool built on that pypdf would crash on the output. Deleting the key would avoid that, but the spec says null. The pin test reads the root directly.
- **`/NeedAppearances` is never set (R39).** No template sets it (the controller's `t03/probe_needapp.py`: all 17 `None`). The old `set_need_appearances_writer(False)` call is gone, since it wrote the key.
  - A mutation that set it to true stayed green, by design. MuPDF 1.27.2.3's bake keeps pypdf's streams either way, and the output has no `/AcroForm` to carry the flag. So no test can guard R39; the code just never sets it.
- **A single-line box still has no height rule (R38, corrected in this task).** The controller's probe (`t03/probe_height.py`) found the right set: 37 single-line widgets where Ç's cedilla dips below the rect. But it printed only 25 of its 37 rows, and its numbers were wrong. Gate 4 below measured them:
  - The largest excess is 0.108 pt, on 11 widgets 13.8 pt high at 12 pt: Form 101's `Debtor1.Name` on pages 2–9, `Attorney.Sig` on page 8 and `Case number1` on page 2, and Form 121's `Case number1`. That is 0.225 × 12 − (1 + (13.8 − 2 − 8.616) / 2) = 0.108.
  - The other 26 dip 0.039 pt (12 widgets, on 106C), 0.02 pt (9) or 0.08 pt (5).
  - The 9 bound widgets among the 37 are Form 101's `Debtor1.Name` headers on pages 2–9 and `Attorney.Sig`.
  - The ruling is unchanged: a hairline of one cedilla, invisible, printed the same before 3a2. Task 4's bottom tolerance for these boxes is 0.11 pt.
  - Task 2's section repeats the controller's first numbers (0.08 pt, 10 pt boxes 11.52–11.64 pt high). These are the corrected ones.
- **PyMuPDF isn't thread-safe, and the bake takes no lock (R47).** Production runs `gunicorn --workers 2` with sync workers (`heroku.yml:13`, `Dockerfile.heroku:76`), one request per process, so no two bakes share a process. `runserver` (development and the journeys) is threaded.
  - After Task 5 only Download bakes, and the journeys download one form at a time. Task 5's `CLAUDE.md` update says the server must stay on sync workers (no `--threads`) unless the bake gets a lock.
  - Pre-existing: the documents app's `fitz` page rendering runs in the upload's worker thread.

_The read-back gates, run before any test was ported (R25, R29):_

- **The implementer proved the read-back first** with a throwaway script (`t03/readback_gates.py`, not committed; results in `t03/gates_pre.txt` and `t03/gates_post.txt`). tasks.md said to stop if a gate changed spec §8's method. None did, but two findings correct §8's wording (errata pending), and one corrected R38's numbers. The script ran four gates over the 17 real templates:
- **Gate 1, ticks.** The templates have 863 checkboxes and 2 radio buttons; 7 are stacked, so 858 box widgets are drawn. Each form was drawn once per state position (56 draws), ticking each box name's k-th state, and baked.
  - Every drawn box was ticked at least once. Each ticked box read exactly one ZapfDingbats character inside it (858 of 858), and none of the 3,127 unticked reads found one. Every drawn box has exactly one on-state.
  - With `get_text(clip=rect)` alone, 4 unticked boxes read a tick: Schedule D page 2's `check 4` T27 and T28, and Form 101 page 1's `Check Box1` T6 and T7. Each pair's rects overlap by about 2 pt (D: T27 spans y 242.88–255.05, T28 252.41–264.58), and MuPDF's clip keeps a glyph that merely touches it. Counting a character only when its bounding box's centre lies inside the rect gives 0 failures (R40).
- **Gate 2, fonts (R29).** Every text box's `/DA` names `/Helv` (2,053 text boxes and 18 combos), and each `/Helv` resolves in `/AcroForm /DR /Font` to `/BaseFont /Helvetica` (2,071 of 2,071).
  - "Hg" was drawn in each of the 2,070 drawn text and combo boxes ("H" where "Hg" was too long; none refused that). Each read back in characters whose span font is exactly `Helvetica`: 0 differences.
  - The templates' own Arial, Times and Calibri words lie inside 1,436 of those rects. They are the template's print, so the read-back ignores every font but Helvetica and ZapfDingbats.
- **Gate 3, the blank baseline.** Each template was baked with its undrawn widgets removed, as `fill()` does. Then 23 widgets print Helvetica text, and none prints ZapfDingbats:
  - the 18 district combos (one per form, two on 103B) print their `/V` default `__________ District of __________` (103B page 4 reads `___________________________ District of _`);
  - Schedule C's `page 2` (page 2 T87) and Schedule G's `fill 2.6` (page 2 T3) print "2";
  - A/B's `19.1`, `19.2` and `19.3 % of ownership` (page 5 T36, T40 and T43) print "0%".
  - So spec §8's "no Helvetica or ZapfDingbats text lies inside any box" is false after the bake, and `read_drawn` subtracts this baseline.
  - Baking the template file with PyMuPDF alone prints each district placeholder twice. Through pypdf's clone and write, the engine's path, it prints once, so the baseline is built that way.
- **Gate 4, geometry, with `fill()` built.** "Åg" went in every drawn single-line text box, "Åg\nÇq" in every multi-line one and a real district in each combo, at `check()`'s sizes, one `fill()` per form. Each character was judged from its origin and size (top = origin − 0.931 × size, bottom = origin + 0.225 × size, in MuPDF's top-down coordinates) against the widget's `/Rect`.
  - Drawn: 1,950 single-line boxes, 94 multi-line boxes and 18 combos.
  - Refused by `check()` as `ValueTooLong` even at 6 pt: 8, Schedule G page 2's entry-number boxes `fill 2.6` to `fill 2.13`.
  - With a character outside their rect: 37, exactly R38's set, rebuilt with the probe's formula. All are single-line, all below the rect only. None is over the top, and no multi-line box is outside, so Task 2's height rule and the R35 lowering agree. `check()` refused none of the 37.
  - `read_drawn` read every planned value back exactly and nothing anywhere else, and every span's size equals the planned size within 0.05 pt.
- **The gates ran on the first round's build** (26f4f32), before the fix round's `/V` restore (R42). The restore changes only what a widget without a planned value prints, and gate 4 planned every text and combo widget. They weren't re-run.

_Reading the page (`read_drawn`, R40):_

- **One `get_text("rawdict")` per page,** keeping only Helvetica and ZapfDingbats characters. A character belongs to a widget when its bounding box's centre lies inside the widget's index rect.
  - tasks.md's Interfaces row first said `get_text("dict", clip=rect)` per widget. A plain clip reads a neighbour's tick on the two overlapping pairs (gate 1). One extraction per page instead of about 700 also keeps tier 1 at about 41 s (implementer). The controller accepted the change (R40).
- **A text widget's value** is its Helvetica characters grouped by MuPDF line, the lines ordered by baseline (rounded to 0.1 pt) and then by x, each line stripped, joined by one space.
  - A comb box's whitespace is removed, since MuPDF reads the gaps between cells as spaces. So a comb value with a real space reads without it, which spec §8 allows.
- **A box's state** is its first on-state when a ZapfDingbats character is inside it, else `"/Off"`. Each drawn box has exactly one on-state (gate 1). A text or combo widget's state is `""`.
- **`read_drawn` returns every index row,** print buttons and stacked seconds included. Tiers 1 and 3 keep only the drawn widgets.
- **`read_drawn` can't tell a baked page from an unbaked one.** MuPDF's text extraction reads a widget's appearance stream as well as the page's content (Step 2 shows it). So a test that only reads the page can pass on an unbaked PDF. `test_the_drawn_form_has_no_fillable_field_left`, which finds no `/Widget` and a null `/AcroForm`, is the test that checks the bake.
- **The blank baseline is built in the test helper, apart from the engine:** a pypdf clone with the undrawn widgets dropped, baked by PyMuPDF. `_blank()` is `@lru_cache(maxsize=32)`, keyed by template filename (G11).
  - A text widget that prints exactly its blank-form text reads `""`. So a value equal to that text would read blank too. Tier 1's sentinels are letters only, so none equals "2" or "0%".
  - The reviewer found the subtraction all-or-nothing on exact text, so it can't make a wrong value read right: a district combo that fails to draw reads `""` and fails its expectation.
  - But a "prints blank" assertion on the 5 unbound boxes with a default passes while the page prints "0%" or "2" (review finding 5). No test asserts one today. `CLAUDE.md`'s tier gotcha now says so (R45).

_Porting the tests:_

- **Against the old filler, every test in the 14 changed test files passes except this task's 15 tests of the drawing** (Step 2's run, made for this plan). MuPDF's text extraction reads a widget's appearance stream even before a bake, and the old filler built an appearance for every widget of a name. So the port changes how each test reads the PDF, not what it proves.
- **Which files are ported:** the 13 test files that imported `read_widgets`, and `test_form_101_schema.py`, which read each widget's `/AP` with pypdf through `field_of` and `qualified_name`.
- **Mechanical changes:** `state is None` became `not state`, and a blank `/V` (`None`) became `""`.
- **Form 101's and 107's header tests** read each page's drawn header. No widget is left to read an `/AP` from.
- **The DIG-155 test** in `test_form_views.py` built `{full_name: value}`, which collapsed shared names. It now checks that every widget of each typed name prints the filed value.
- **Tier 1:**
  - It reads drawn widgets only, on both sides. The expected tick count now counts drawn widgets that have the state, not index rows, so Schedule D's stacked boxes no longer agree by coincidence.
  - Every drawn widget of a binding's full name must print its sentinel (R44), besides the "landed nowhere" and "spill" checks. The new message is `no_widget: the value is missing from widgets [...]`.
  - A text sentinel is `Q###` when `check()` fits it, else the first unused two-letter code that fits, then one letter. 5 of the 510 text sentinels need a code, all on Form 101's MaxLen-2 boxes: `Debtor1.State`, `Debtor1.State_2`, `Business State`, `State_6` and `Attorney.Bar State` get "AA" to "AE". None needs one letter. (The implementer counted these, and a script run on this task's tree for this plan found the same five.)
  - A combo's sentinel is its first option that isn't blank, isn't the template's own `/V` (the placeholder) and fits: "Middle District of Alabama" on all 17 combo bindings (the same script). The first option, " ", prints nothing.
  - `_sentinels()` is not cached. `_text_fill()` and `_box_fill()` stay `@cache`d by form type, as the old helpers were; G11's template key applies to `_blank()`.
- **Tier 3 (R44)** keeps only drawn widgets and records a text widget's value even when it is `""`.
  - An expected blank must show nothing in any widget (`shown <= {""}`).
  - An amount must be the same in every widget; a blank widget is no amount, so it fails.
  - A string must be exactly the expected text in every widget (`shown == {expected}`; it was `expected in shown`).
  - All 179 cases pass, so no widget of an expected box legitimately reads blank (implementer).
- **R44 was shown red** with a mutation that drew only the first widget of each shared text name.
  - In the implementer's run, 28 tests failed: 19 tier 1 text cases (`Debtor 1` on 103B, 106Sum, 107, A/B, C, D, E/F, G, H, I and J; `Debtor1.Name` on 101, 122A-1 and 122A-2; `Debtor.Name1` and the district combo on 103B; 122A-1's `Debto1.Quest6C` and `Quest11`; A/B's `undefined_166`), 6 tier 3 cases (122A-1's `Quest11` for each persona), Form 101's and 107's header tests and the DIG-155 test.
  - The re-reviewer's run, over a different set of files, failed 31.
- **`test_text_prints_from_a_stored_appearance` became `test_the_drawn_form_has_no_fillable_field_left`.** It pins pypdf 6.13.1, `TextStreamAppearance.from_text_annotation`, `PdfWriter._add_object` (R45, G12) and PyMuPDF 1.27.2.3. It checks that the output's `/AcroForm` is null, that no page has a `/Widget`, and that the value is page text. Its version asserts are a guard, like the other pins: they can go red only if a library changes. The rest of it went red under the mutations below.
- **`test_signing_lines.py` is left as found.** Its own `_printed()` keeps only non-empty values (`if widget.value:`), so it can't see a shared name that prints on only some of its widgets, and it stayed green under the draw-once mutation. R44 names tiers 1 and 3; this is a note for Task 4.

_New tests, and how each was shown red (G4):_

- **The implementer's `t03/mutate.py`** applied each mutation, ran the tests and restored the code (outputs `t03/mutate.out`, `t03/mutate-fix1.out` and `t03/mutate-fix1-r44.out`).
- `test_the_drawn_form_has_no_fillable_field_left`: no bake, and `/AcroForm` kept.
- `test_a_letter_outside_latin_1_prints_on_every_box`: the widget's `/DR` kept (R32). The reviewer found each of its four cases reads "?" on its own under that mutation.
  - The name is the invented "Łukasz O’Brien". 122A-2's case prints "Ł. O’Brien": its only two bound boxes with their own `/DR` are amounts 38.5 pt wide, where the whole name is `ValueTooLong` even at 6 pt.
- `test_shared_name_boxes_print_their_own_values` (Schedule I's two "Assistance 8f" widgets and A/B's two "24.1" widgets): `/V` set once per field, and `/V` never set.
- `test_a_tagged_value_prints_only_in_its_own_box` (R42): Form 107's `Debtor 1@1:T1` = "Nadrova Okafor" (an invented name; pages 2–12 read `""`), Schedule I's `Time employed Debtor 1@1:T28` = "3 years" (T29 reads `""`) and Schedule D's `account number@1:T32` = "4417" (page 3's T33 reads `""`). All 3 failed on the code before the fix round, and again with the restore removed.
- `test_a_tick_reads_back_only_in_its_own_box` (R43): each widget is named by `(page, tag)` and ticked through its own tagged key, in both directions of Form 101 page 1's T7 (Chapter 13) and T6 (Chapter 12) and Schedule D page 2's T28 and T27. With `_inside` widened 5 pt on each side, all 4 failed.
  - Its first version keyed widgets by tag alone, so page 3 overwrote page 1 and the Form 101 case compared page 3's T5 and T6, 8 pt apart (review finding 2).
- `test_nothing_the_blank_template_prints_reads_as_a_value` (17 forms): no baseline subtracted (17 red). It builds the same baseline the helper does, so it mostly restates the subtraction (reviewer).
- `test_a_shrunk_value_prints_at_its_planned_size` (Form 101's email box, a value planned below 10 pt): the planned size not passed to pypdf.
- `test_a_multi_line_boxs_first_line_keeps_its_capitals_marks` (A/B line 53, "Åsa Éclair\nÇedric"): the first line not lowered, and lowered by one margin only (top 404.16 against the rect's 404.2, reviewer).
  - MuPDF extracts a partly hidden glyph whole, so the test judges the first line by where it sits, not by its text: the glyph top must be at least the rect's top, and exactly one margin below it (within 0.06 pt, the index rect's rounding).
  - It runs at the box's own size. The 6 pt case is Task 4's pixel test.
- `test_an_empty_multi_line_box_prints_nothing`: a stream with no `Td` rewritten anyway (`TypeError`).
- `test_drawing_never_logs_the_filers_text` (G6): the widget's `/DR` kept, so pypdf logs "Text string '…' contains characters not supported…" with the whole value.
  - The implementer's `t03/probe_warn.py` filled every text box of A/B, 107, 121, 122A-2, C, D and 101 with Ł ’ “ ” – € •, parentheses, a backslash, a tab, multi-line text and full comb values, and no log record at all was emitted. `check()` refuses what pypdf would warn about, and R32 removes the fonts behind the encoding warning. So the test uses the R32 case, which logged the whole value before.
- `test_a_letter_the_form_cannot_print_refuses_the_download` (R45): an unfiled (`generated`) Form 121 whose first name is "Wąsowicz" (invented) gets a 422 with the spec §4.5 sentence and `"step": "debtor_info"`, and no DEBUG record holds the name. Red with `printable` ignored in `check()`: the download succeeds with "?".
  - It checks each record's `getMessage()` only, not `exc_info` or `args` (re-reviewer, minor).
- **Other mutations that went red:** `check()` before the `/AcroForm` test (`test_template_without_a_form_raises`); `/AS` not set (`test_checkbox_ticks_only_the_widgets_for_its_state`); the read-back counting every font as text (tier 1, 488 red); tier 1 without the shorter sentinels (66 red, `ValueTooLong`); a rect widened by 4 to 5 pt (tier 1's E/F `check` cases).
- **R4 and R26 have no test in this task;** Task 4 owns them (`amounts_stay_right_aligned` with A/B's three widget-only `/Q` boxes, and `ssn_digits_fill_their_cells` with Schedule D's `account number`, R45). The reviewer removed both lines and every test stayed green (715 passed), as planned.
  - The implementer observed both in the output (`t03/probe_r4_r26.py`): Schedule D's `account number` prints "4417" one digit per cell, and without R4 all in cell 0. A/B's three boxes end at the right padding within 0.05 pt, and without R26 start at the left padding.

_Docs:_

- **The umbrella spec** (`docs/superpowers/specs/2026-10-16-forms-step3-design.md`) gets one line after its §5.4 method bullets, pointing to the 3a2 spec's §3. Its Appendix A SPIKE row's cell ends "…, replaced by 3a2's spec §3", kept inside the column's width so prettier leaves the table alone; the full path is on the §5.4 line.
- **`CLAUDE.md`:**
  - the Architecture **PDF:** line (`check()` plans, `fill()` draws, PyMuPDF bakes every remaining widget, and the output can't be filled in a viewer);
  - the File Map's `apps/forms/services/` line (`widgets.py`, `text_fit.py`);
  - "Known form defects are strict xfails" (tiers 1 and 3 read the printed page through `read_drawn`, and a box's own template default reads blank);
  - "Schemas are checked at startup" loses "which `fill()` doesn't take yet";
  - "The packet decides which forms a filer gets" and "Forms need a completed intake" (the two new 422s, above).

_Left as found, and notes for later tasks:_

- **Generate still draws until Task 5,** so the backend suite takes about 100 s longer than after Task 2 (the implementer's runs: 449.65 s against 342 s). In one warm process, one `fill()` takes about 1.1 s for Form 107, 0.8 s for A/B and 0.7 s for 101, about half of it the clone, the write and the bake (implementer).
- **A filed form whose stored values `check()` now refuses** gets the same 422, with a `step` that can't change a filed snapshot. Production v31 holds no such row, but a self-hoster's `main` can (R73). Task 5 settles it (R46).
- **A/B line 19's `% of ownership` boxes print the template's "0%"** when the filer leaves them blank (the Blank-not-0.00 class; the template's own behaviour, before and after 3a2; a ticket candidate).
- **Spec §8 errata, pending:** "inside" means the character's centre is inside, and the blank baseline is 23 widgets, not empty.
- **Gate 4's 8 Schedule G entry-number boxes refuse even "Åg",** so Task 4's `test_no_value_is_ever_cut_off` needs a one-character value that just fits there.
- **The commit has no `Refs DIG-…` line.** The spec §12 defects and the ledger's ticket candidates (6) and (7), which this commit closes, aren't filed yet, and no existing ticket is this change's.

- [ ] **Step 1: Write the failing tests**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/pdf_readback.py b/backend/apps/forms/tests/pdf_readback.py
index c6976c5..9a2e48c 100644
--- a/backend/apps/forms/tests/pdf_readback.py
+++ b/backend/apps/forms/tests/pdf_readback.py
@@ -1,38 +1,142 @@
-"""Read a filled PDF back widget by widget, the way a viewer sees it."""
+"""
+Read a drawn PDF back box by box, the way a person reads the printed page (spec §8).
+
+Every value prints in Helvetica and every tick is the template's ZapfDingbats check
+mark, while the templates print their own words in Arial, Wingdings and Times. A
+character belongs to a widget when its centre lies inside the widget's rect from the
+field index: two pairs of boxes overlap by about 2 pt, and a glyph merely touching a
+rect would put a neighbour's tick in it.
+"""

 from dataclasses import dataclass
+from functools import lru_cache
 from io import BytesIO
+from pathlib import Path

+import pymupdf
 import pypdf
+from django.conf import settings
+from pypdf.generic import ArrayObject, NameObject
+
+from apps.forms.schema import load_schema
+from apps.forms.services.widgets import TemplateWidget, template_widgets, widget_for

-from apps.forms.services.widgets import field_of, qualified_name
+_BOXES = ("CheckBox", "RadioButton")
+_TEXT_FONT = "Helvetica"
+_TICK_FONT = "ZapfDingbats"


 @dataclass(frozen=True)
-class FilledWidget:
+class DrawnWidget:
     full_name: str
     page: int
-    value: str | None  # the field's /V
-    state: str | None  # the widget's /AS; what a checkbox shows
-
-
-def read_widgets(pdf_bytes: bytes) -> list[FilledWidget]:
-    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
-    widgets = []
-    for page_number, page in enumerate(reader.pages, start=1):
-        for annot in page.get("/Annots") or []:
-            widget = annot.get_object()
-            if widget.get("/Subtype") != "/Widget":
-                continue
-            field = field_of(widget)
-            value = field.get_inherited("/V")
-            state = widget.get("/AS")
-            widgets.append(
-                FilledWidget(
-                    full_name=qualified_name(field),
-                    page=page_number,
-                    value=None if value is None else str(value),
-                    state=None if state is None else str(state),
-                )
-            )
-    return widgets
+    tag: str
+    value: str  # the Helvetica text inside the widget's rect; "" when none
+    state: str  # a box: its on-state when a check mark is inside, else "/Off"; "" for text
+
+
+@dataclass(frozen=True)
+class _Character:
+    text: str
+    font: str
+    centre: tuple[float, float]
+    line: tuple[int, int]  # MuPDF's (block, line) on the page
+    baseline: float
+
+
+def _characters(page: pymupdf.Page) -> list[_Character]:
+    """Every Helvetica or ZapfDingbats character on the page, with its position."""
+    characters = []
+    for b, block in enumerate(page.get_text("rawdict")["blocks"]):
+        for n, line in enumerate(block.get("lines", [])):
+            for span in line["spans"]:
+                if span["font"] not in (_TEXT_FONT, _TICK_FONT):
+                    continue
+                for char in span["chars"]:
+                    x0, y0, x1, y1 = char["bbox"]
+                    characters.append(
+                        _Character(
+                            char["c"],
+                            span["font"],
+                            ((x0 + x1) / 2, (y0 + y1) / 2),
+                            (b, n),
+                            char["origin"][1],
+                        )
+                    )
+    return characters
+
+
+def _inside(character: _Character, rect: tuple[float, ...]) -> bool:
+    x, y = character.centre
+    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]
+
+
+def _text(widget: TemplateWidget, characters: list[_Character]) -> str:
+    """The Helvetica characters inside the widget, line by line from the top."""
+    lines: dict[tuple[int, int], list[_Character]] = {}
+    for character in characters:
+        if character.font == _TEXT_FONT and _inside(character, widget.rect):
+            lines.setdefault(character.line, []).append(character)
+    ordered = sorted(lines.values(), key=lambda line: (round(line[0].baseline, 1), line[0].centre))
+    text = " ".join(joined for line in ordered if (joined := "".join(c.text for c in line).strip()))
+    # A comb box draws each character in its own cell; MuPDF reads the gaps as spaces.
+    return "".join(text.split()) if widget.comb else text
+
+
+def _read(template: str, document: pymupdf.Document) -> list[DrawnWidget]:
+    characters = [_characters(page) for page in document]
+    drawn = []
+    for widget in template_widgets(template):
+        on_page = characters[widget.page - 1]
+        if widget.kind in _BOXES:
+            ticked = any(c.font == _TICK_FONT and _inside(c, widget.rect) for c in on_page)
+            value, state = "", widget.states[0] if ticked else "/Off"
+        else:
+            value, state = _text(widget, on_page), ""
+        drawn.append(DrawnWidget(widget.full_name, widget.page, widget.tag, value, state))
+    return drawn
+
+
+@lru_cache(maxsize=32)
+def _blank(template: str) -> dict[tuple[int, str], str]:
+    """
+    (page, tag) → the text the blank template prints in a box: a district combo's
+    "__________ District of __________", a default page number or "0%". Built here,
+    apart from the engine, the way it prints a box it draws nothing in: the template
+    less the widgets that never print, baked. (PyMuPDF baking the template file as it
+    stands prints each district placeholder twice.)
+    """
+    writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
+    for number, page in enumerate(writer.pages, start=1):
+        if "/Annots" not in page:
+            continue
+        page[NameObject("/Annots")] = ArrayObject(
+            annot
+            for annot in page["/Annots"]
+            if annot.get_object().get("/Subtype") != "/Widget"
+            or widget_for(template, number, annot.get_object(), float(page.mediabox.top)).drawn
+        )
+    buffer = BytesIO()
+    writer.write(buffer)
+    document = pymupdf.open("pdf", buffer.getvalue())
+    document.bake(annots=False, widgets=True)
+    return {(w.page, w.tag): w.value for w in _read(template, document) if w.value}
+
+
+def read_drawn(form_type: str, pdf_bytes: bytes) -> list[DrawnWidget]:
+    """
+    What the drawn form prints in each widget of its template, one entry per index row
+    in page and tag order. A text box that prints exactly what the blank form prints
+    there reads as "": nothing the template prints passes for a value, so a value equal
+    to that box's blank text reads blank too.
+    """
+    template = load_schema(form_type).template_filename
+    blank = _blank(template)
+    return [
+        (
+            DrawnWidget(w.full_name, w.page, w.tag, "", w.state)
+            if w.value and blank.get((w.page, w.tag)) == w.value
+            else w
+        )
+        for w in _read(template, pymupdf.open("pdf", pdf_bytes))
+    ]
PATCH
```

`read_drawn` replaces `read_widgets`. It reads the printed page the way a person does: the Helvetica text and the template's ZapfDingbats check mark whose centre lies inside each widget's index rect, one extraction per page. What the blank template prints in a box never reads as a value.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_pdf_filler.py b/backend/apps/forms/tests/test_pdf_filler.py
index 712f83f..cb34b80 100644
--- a/backend/apps/forms/tests/test_pdf_filler.py
+++ b/backend/apps/forms/tests/test_pdf_filler.py
@@ -1,17 +1,25 @@
 """
-PDFFormFiller fills exactly the widget a key names, the way a viewer will draw it.
+PDFFormFiller draws exactly the widget a key names, and the page shows what it drew.

 The old filler matched a key against a parent's partial /T, so "Name" filled
 both Debtor 1 and Debtor 2 (DIG-63), and it never ticked a checkbox (DIG-68).
+Since 3a2 each widget is drawn with its own value and baked into the page, so these
+tests read the printed page (pdf_readback.read_drawn), not the fields' /V.
 """

 import json
+import logging
 from io import BytesIO

+import pymupdf
 import pypdf
 import pytest
 from pypdf._font import Font
+from pypdf.generic import NullObject
+from pypdf.generic._appearance_stream import TextStreamAppearance

+from apps.forms.registry import get_all_form_types
+from apps.forms.schema import load_schema
 from apps.forms.services.pdf_filler import (
     InvalidFieldValue,
     PDFFormFiller,
@@ -19,11 +27,39 @@ from apps.forms.services.pdf_filler import (
     UnknownField,
 )
 from apps.forms.services.text_fit import font_for
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.services.widgets import parse_key, template_widgets
+from apps.forms.tests.pdf_readback import read_drawn

+EMAIL = "Debtor1.Email address_2"  # Form 101 page 9, 10 pt
+OTHER_PROPERTY = "53 Examples Season tickets country club membership"  # A/B line 53, multi-line
+# Helvetica's FontBBox top, per 1000 em: the highest mark a capital carries (Å).
+_HELVETICA_TOP = 931

-def _values(pdf_bytes, full_name):
-    return [w.value for w in read_widgets(pdf_bytes) if w.full_name == full_name]
+
+def _values(form_type, pdf_bytes, full_name):
+    return [w.value for w in read_drawn(form_type, pdf_bytes) if w.full_name == full_name]
+
+
+def _widget(form_type, full_name):
+    template = load_schema(form_type).template_filename
+    (widget,) = [w for w in template_widgets(template) if w.full_name == full_name and w.drawn]
+    return widget
+
+
+def _helvetica_in(pdf_bytes, widget):
+    """Every Helvetica character drawn inside the widget's rect: (character, origin y, size)."""
+    page = pymupdf.open("pdf", pdf_bytes)[widget.page - 1]
+    x0, y0, x1, y1 = widget.rect
+    return [
+        (char["c"], char["origin"][1], span["size"])
+        for block in page.get_text("rawdict")["blocks"]
+        for line in block.get("lines", [])
+        for span in line["spans"]
+        if span["font"] == "Helvetica"
+        for char in span["chars"]
+        if x0 <= (char["bbox"][0] + char["bbox"][2]) / 2 <= x1
+        and y0 <= (char["bbox"][1] + char["bbox"][3]) / 2 <= y1
+    ]


 def test_filled_form_is_a_pdf():
@@ -33,24 +69,32 @@ def test_filled_form_is_a_pdf():

 def test_debtor_1_name_never_lands_in_debtor_2_box():
     pdf = PDFFormFiller().fill("form_122a1", {"Debtor1.Name": "Maria Torres"})
-    assert set(_values(pdf, "Debtor1.Name")) == {"Maria Torres"}
-    assert _values(pdf, "Debtor2.Name") == [None]
+    assert set(_values("form_122a1", pdf, "Debtor1.Name")) == {"Maria Torres"}
+    assert _values("form_122a1", pdf, "Debtor2.Name") == [""]


-def test_text_prints_from_a_stored_appearance():
-    """pypdf 6.13.1 internals build and install the appearance; this pins them."""
+def test_the_drawn_form_has_no_fillable_field_left():
+    """
+    pypdf 6.13.1 builds each widget's appearance and adds it to the PDF (the internals
+    TextStreamAppearance and PdfWriter._add_object), and PyMuPDF 1.27.2.3 bakes it into
+    the page; this pins them. The value is page content now, so the PDF has no field a
+    viewer could fill in.
+    """
     assert pypdf.__version__ == "6.13.1"
+    assert callable(TextStreamAppearance.from_text_annotation)
+    assert callable(pypdf.PdfWriter._add_object)
+    assert pymupdf.__version__ == "1.27.2.3"
     pdf = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
     reader = pypdf.PdfReader(BytesIO(pdf))
-    # A BooleanObject is always truthy; its .value is the flag.
-    assert reader.trailer["/Root"]["/AcroForm"]["/NeedAppearances"].value is False
-    widget = next(
-        a.get_object()
-        for a in reader.pages[0]["/Annots"]
-        if a.get_object().get("/T") == "First name"
-        and a.get_object()["/Parent"].get("/T") == "Debtor1"
-    )
-    assert b"Maria" in widget["/AP"]["/N"].get_data()
+    # pypdf's own get_fields() can't read a null /AcroForm, so the root is read directly.
+    assert isinstance(reader.trailer["/Root"]["/AcroForm"], NullObject)
+    assert [
+        a
+        for page in reader.pages
+        for a in page.get("/Annots") or []
+        if a.get_object().get("/Subtype") == "/Widget"
+    ] == []
+    assert "Maria" in pymupdf.open("pdf", pdf)[0].get_text()


 def test_text_is_measured_with_pinned_pypdf_font_internals():
@@ -67,7 +111,7 @@ def test_text_is_measured_with_pinned_pypdf_font_internals():

 def test_checkbox_ticks_only_the_widgets_for_its_state():
     pdf = PDFFormFiller().fill("form_101", {"Check Box1": "/Chapter 7"})
-    states = [w.state for w in read_widgets(pdf) if w.full_name == "Check Box1"]
+    states = [w.state for w in read_drawn("form_101", pdf) if w.full_name == "Check Box1"]
     # Chapter 7 is printed on pages 1 and 3; the other six options stay off.
     assert states.count("/Chapter 7") == 2
     assert states.count("/Off") == len(states) - 2
@@ -81,7 +125,7 @@ def test_state_the_template_lacks_raises_instead_of_printing_nothing():
 def test_district_must_be_one_of_the_templates_options():
     district = "Bankruptcy District Information"
     pdf = PDFFormFiller().fill("form_121", {district: "Northern District of Illinois"})
-    assert _values(pdf, district) == ["Northern District of Illinois"]
+    assert _values("form_121", pdf, district) == ["Northern District of Illinois"]
     with pytest.raises(InvalidFieldValue):
         PDFFormFiller().fill("form_121", {district: "District of Nowhere"})

@@ -108,3 +152,140 @@ def test_template_without_a_form_raises(tmp_path, settings):
     (tmp_path / "form_no_acroform.json").write_text(json.dumps(schema))
     with pytest.raises(TemplateHasNoForm):
         PDFFormFiller().fill("form_no_acroform", {})
+
+
+# ── What the drawing prints ───────────────────────────────────────────
+
+# An invented name: Ł and ’ are outside Latin-1, yet in the template font's encoding.
+_NAME = "Łukasz O’Brien"
+
+
+def test_a_letter_outside_latin_1_prints_on_every_box():
+    # A/B's page-1 header and these three bound boxes carry a /DR of their own whose font
+    # lacks the template's encoding, so pypdf used to print "?" in them (R32).
+    pdf = PDFFormFiller().fill("schedule_a_b", {"Debtor 1": _NAME})
+    headers = {
+        w.page: w.value for w in read_drawn("schedule_a_b", pdf) if w.full_name == "Debtor 1"
+    }
+    assert headers[1] == headers[2] == _NAME
+    for form_type, full_name, value in [
+        # 122A-2's two such boxes are amounts 38.5 pt wide: the whole name won't fit.
+        ("form_122a2", "undefined_51", "Ł. O’Brien"),  # page 5
+        ("schedule_c", "2.2", _NAME),  # page 1, multi-line
+        ("schedule_d", "undefined_24", _NAME),  # page 2
+    ]:
+        pdf = PDFFormFiller().fill(form_type, {full_name: value})
+        assert _values(form_type, pdf, full_name) == [value], form_type
+
+
+@pytest.mark.parametrize(
+    "form_type,full_name",
+    [
+        ("schedule_i", "Assistance 8f"),
+        ("schedule_a_b", "24.1 Interest in an education IRA"),
+    ],
+)
+def test_shared_name_boxes_print_their_own_values(form_type, full_name):
+    template = load_schema(form_type).template_filename
+    first, second = [w for w in template_widgets(template) if w.full_name == full_name]
+    pdf = PDFFormFiller().fill(form_type, {first.key: "Nadrova 1", second.key: "Nadrova 2"})
+    printed = {(w.page, w.tag): w.value for w in read_drawn(form_type, pdf)}
+    assert printed[(first.page, first.tag)] == "Nadrova 1"
+    assert printed[(second.page, second.tag)] == "Nadrova 2"
+
+
+@pytest.mark.parametrize(
+    "form_type,key,value",
+    [
+        ("form_107", "Debtor 1@1:T1", "Nadrova Okafor"),  # one header of 12, a page each
+        ("schedule_i", "Time employed Debtor 1@1:T28", "3 years"),  # T29 beside it
+        ("schedule_d", "account number@1:T32", "4417"),  # page 3's T33 shares the name
+    ],
+)
+def test_a_tagged_value_prints_only_in_its_own_box(form_type, key, value):
+    # Its siblings have no appearance of their own in the template, and one built at the
+    # bake from the field's shared value would print this value in all of them (R42).
+    name, page, tag = parse_key(key)
+    pdf = PDFFormFiller().fill(form_type, {key: value})
+    printed = {(w.page, w.tag): w.value for w in read_drawn(form_type, pdf) if w.full_name == name}
+    assert printed.pop((page, tag)) == value
+    assert printed and set(printed.values()) == {""}
+
+
+@pytest.mark.parametrize(
+    "form_type,full_name,ticked,neighbour",
+    [
+        # Each pair's rects overlap by about 2 pt: a tick in either box must not read as
+        # a tick in the other.
+        ("form_101", "Check Box1", (1, "T7"), (1, "T6")),  # Chapter 13, Chapter 12
+        ("form_101", "Check Box1", (1, "T6"), (1, "T7")),
+        ("schedule_d", "check 4", (2, "T28"), (2, "T27")),  # with another; Debtor 1 and 2
+        ("schedule_d", "check 4", (2, "T27"), (2, "T28")),
+    ],
+)
+def test_a_tick_reads_back_only_in_its_own_box(form_type, full_name, ticked, neighbour):
+    template = load_schema(form_type).template_filename
+    (widget,) = [w for w in template_widgets(template) if (w.page, w.tag) == ticked]
+    pdf = PDFFormFiller().fill(form_type, {widget.key: widget.states[0]})
+    printed = {(w.page, w.tag): w.state for w in read_drawn(form_type, pdf)}
+    assert printed[ticked] == widget.states[0]
+    assert printed[neighbour] == "/Off"
+
+
+@pytest.mark.parametrize("form_type", get_all_form_types())
+def test_nothing_the_blank_template_prints_reads_as_a_value(form_type):
+    # A blank form still prints the template's own defaults: a district combo's
+    # "__________ District of __________", a page number, A/B's "0%". None of them is a
+    # value the filer gave, so none may pass for one.
+    drawn = read_drawn(form_type, PDFFormFiller().fill(form_type, {}))
+    assert [(w.full_name, w.value) for w in drawn if w.value] == []
+    assert {w.state for w in drawn} <= {"", "/Off"}
+
+
+def test_a_shrunk_value_prints_at_its_planned_size():
+    # The bake keeps pypdf's appearance as built; an appearance rebuilt at the box's own
+    # 10 pt would cut the address off (R39).
+    email = "kestrel.wanamaker.okonkwo@example.org"
+    box = _widget("form_101", EMAIL)
+    ((planned,),) = [part.widgets for part in PDFFormFiller().check("form_101", {EMAIL: email})]
+    assert planned.size < box.size
+    drawn = _helvetica_in(PDFFormFiller().fill("form_101", {EMAIL: email}), box)
+    assert "".join(c for c, _, _ in drawn) == email
+    assert all(abs(size - planned.size) <= 0.05 for _, _, size in drawn)
+
+
+def test_a_multi_line_boxs_first_line_keeps_its_capitals_marks():
+    # pypdf hangs line 1 from the font's top at the box's height plus its margin, so the
+    # box cut Å's ring off; the drawing lowers that line by 2 × margin (R35). MuPDF reads a
+    # partly hidden glyph whole, so the line is judged by where it sits, not by its text.
+    box = _widget("schedule_a_b", OTHER_PROPERTY)
+    pdf = PDFFormFiller().fill("schedule_a_b", {OTHER_PROPERTY: "Åsa Éclair\nÇedric"})
+    assert _values("schedule_a_b", pdf, OTHER_PROPERTY) == ["Åsa Éclair Çedric"]
+    drawn = _helvetica_in(pdf, box)
+    first_baseline = min(y for _, y, _ in drawn)
+    size = next(s for _, y, s in drawn if y == first_baseline)
+    top = first_baseline - _HELVETICA_TOP / 1000 * size
+    assert top >= box.rect[1]
+    # pypdf put that top a margin above the box; lowered by 2 × margin, it is a margin below.
+    assert top == pytest.approx(box.rect[1] + box.margin, abs=0.06)
+
+
+def test_an_empty_multi_line_box_prints_nothing():
+    # pypdf's appearance for an empty value has no line, so there is none to lower.
+    pdf = PDFFormFiller().fill("schedule_a_b", {OTHER_PROPERTY: ""})
+    assert _values("schedule_a_b", pdf, OTHER_PROPERTY) == [""]
+
+
+def test_drawing_never_logs_the_filers_text(caplog):
+    # These boxes' own /DR made pypdf log a warning quoting the whole value (DIG-105).
+    # check() now refuses whatever pypdf would still warn about, so nothing is logged.
+    values = {
+        "Debtor 1": _NAME,
+        OTHER_PROPERTY: "Season tickets – “box 4”\n€120 • yearly",
+    }
+    with caplog.at_level(logging.DEBUG):
+        PDFFormFiller().fill("schedule_a_b", values)
+    pieces = [_NAME, "Season tickets – “box 4”", "€120 • yearly"]
+    assert [
+        r.getMessage() for r in caplog.records if any(p in r.getMessage() for p in pieces)
+    ] == []
PATCH
```

The filler tests read the drawn page. The pin test now checks that no fillable field is left. The new tests cover:

- a letter outside Latin-1 on boxes with their own `/DR`;
- shared-name boxes with their own values, and a tagged value printing only in its own box;
- ticks in two overlapping boxes;
- a blank form reading blank;
- a shrunk value at its planned size;
- a multi-line box's first line, and an empty one;
- a draw that logs none of the filer's text.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_oracle_tier1.py b/backend/apps/forms/tests/test_oracle_tier1.py
index 5f067ab..d51f296 100644
--- a/backend/apps/forms/tests/test_oracle_tier1.py
+++ b/backend/apps/forms/tests/test_oracle_tier1.py
@@ -1,25 +1,28 @@
 """
 Oracle tier 1: every binding lands in exactly the widget it names (spec §6).

-Each text and combo binding gets a unique marker, the real filler fills the
-real template, and every widget is read back. A checkbox state is set and read
-from /AS, which is what a viewer draws; /V alone proves nothing (DIG-68).
-No database is needed.
+Each text and combo binding gets a unique sentinel, the real engine draws it on the
+real template, and every widget is read back from the printed page (3a2 spec §8): the
+sentinel prints in every widget of its name and in no other. A tick is the template's own check mark printed inside the box; /V alone proves nothing
+(DIG-68). Only the widgets the engine draws are read: a print button and the second
+widget of a stacked pair never print. No database is needed.
 """

 from functools import cache
+from itertools import product
 from pathlib import Path
+from string import ascii_uppercase

 import pypdf
 import pytest
 from django.conf import settings

-from apps.forms.field_index import export_state, load_index
 from apps.forms.registry import get_all_form_types
 from apps.forms.schema import load_schema
-from apps.forms.services.pdf_filler import PDFFormFiller
+from apps.forms.services.pdf_filler import PDFFormFiller, ValueTooLong
+from apps.forms.services.widgets import template_widgets
 from apps.forms.tests.oracle import case_param
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn

 TIER = "1"

@@ -28,23 +31,65 @@ def _fields(form_type, types):
     return [f for f in load_schema(form_type).fields if f.type in types]


-def _first_option(form_type, pdf_field):
+def _fits(form_type, pdf_field, value):
+    try:
+        PDFFormFiller().check(form_type, {pdf_field: value})
+    except ValueTooLong:
+        return False
+    return True
+
+
+def _option(form_type, pdf_field):
+    """
+    A combo's first option that prints and fits: not a blank one, and not the template's
+    own default, which the blank form prints already.
+    """
     template = Path(settings.PDF_FORMS_DIRECTORY) / load_schema(form_type).template_filename
-    return str(pypdf.PdfReader(template).get_fields()[pdf_field]["/Opt"][0])
+    field = pypdf.PdfReader(template).get_fields()[pdf_field]
+    return next(
+        str(option)
+        for option in field["/Opt"]
+        if str(option).strip()
+        and str(option) != str(field.get("/V"))
+        and _fits(form_type, pdf_field, str(option))
+    )
+
+
+# Shorter sentinels for boxes too small for "Q001": two letters, then one. Letters only,
+# so none equals a box's own blank text ("2", "0%").
+_SHORT = ["".join(pair) for pair in product(ascii_uppercase, repeat=2)] + list(ascii_uppercase)
+
+
+def _sentinels(form_type):
+    """pdf_field → its sentinel: unique on the form, and as short as its box needs."""
+    sentinels = {}
+    short = iter(_SHORT)
+    for i, f in enumerate(_fields(form_type, ("text", "choice"))):
+        if f.type == "choice":
+            sentinels[f.pdf_field] = _option(form_type, f.pdf_field)
+        elif _fits(form_type, f.pdf_field, f"Q{i:03d}"):
+            sentinels[f.pdf_field] = f"Q{i:03d}"
+        else:
+            sentinels[f.pdf_field] = next(s for s in short if _fits(form_type, f.pdf_field, s))
+    return sentinels
+
+
+def _drawn(form_type, values):
+    """What the drawn form prints in each widget the engine draws."""
+    template = load_schema(form_type).template_filename
+    drawn = {(w.page, w.tag) for w in template_widgets(template) if w.drawn}
+    return [
+        w
+        for w in read_drawn(form_type, PDFFormFiller().fill(form_type, values))
+        if (w.page, w.tag) in drawn
+    ]


 @cache
-def _text_landing(form_type):
-    """pdf_field → the full names its marker was read back from."""
-    markers = {
-        f.pdf_field: (_first_option(form_type, f.pdf_field) if f.type == "choice" else f"Q{i:03d}")
-        for i, f in enumerate(_fields(form_type, ("text", "choice")))
-    }
-    widgets = read_widgets(PDFFormFiller().fill(form_type, markers))
-    return {
-        name: {w.full_name for w in widgets if w.value == marker}
-        for name, marker in markers.items()
-    }
+def _text_fill(form_type):
+    """Every text and combo binding's sentinel, and what each drawn widget prints with all of them."""
+    sentinels = _sentinels(form_type)
+    return sentinels, _drawn(form_type, sentinels)


 @cache
@@ -55,7 +100,7 @@ def _box_fill(form_type, position):
         keys = sorted(f.choices or {})
         if position < len(keys):
             values[f.pdf_field] = f.choices[keys[position]]
-    return read_widgets(PDFFormFiller().fill(form_type, values))
+    return _drawn(form_type, values)


 def _text_cases():
@@ -77,9 +122,17 @@ BOX_CASES = list(_box_cases())

 @pytest.mark.parametrize("form_type,pdf_field,case", TEXT_CASES)
 def test_value_lands_only_in_the_box_it_names(form_type, pdf_field, case):
-    landed = _text_landing(form_type)[pdf_field]
+    sentinels, widgets = _text_fill(form_type)
+    landed = {w.full_name for w in widgets if w.value == sentinels[pdf_field]}
     assert landed, "no_widget: the value landed nowhere"
     assert landed == {pdf_field}, f"spill: the value also landed in {sorted(landed - {pdf_field})}"
+    # The value prints in every widget its name has, one page header on each page.
+    missed = [
+        (w.page, w.tag)
+        for w in widgets
+        if w.full_name == pdf_field and w.value != sentinels[pdf_field]
+    ]
+    assert missed == [], f"no_widget: the value is missing from widgets {missed}"


 @pytest.mark.parametrize("form_type,pdf_field,case", BOX_CASES)
@@ -89,8 +142,8 @@ def test_checkbox_ticks_only_the_widgets_for_its_answer(form_type, pdf_field, ca
     template = load_schema(form_type).template_filename
     expected = sum(
         1
-        for w in load_index(template)[pdf_field]
-        if w.on_state and export_state(w.on_state) == state
+        for w in template_widgets(template)
+        if w.full_name == pdf_field and w.drawn and state in w.states
     )
     own = [
         w
diff --git a/backend/apps/forms/tests/test_oracle_tier3.py b/backend/apps/forms/tests/test_oracle_tier3.py
index fb9b9bf..a56f88e 100644
--- a/backend/apps/forms/tests/test_oracle_tier3.py
+++ b/backend/apps/forms/tests/test_oracle_tier3.py
@@ -18,9 +18,11 @@ from django.core.management import call_command

 from apps.districts.models import District
 from apps.forms.registry import build_field_values
+from apps.forms.schema import load_schema
 from apps.forms.services.pdf_filler import PDFFormFiller
+from apps.forms.services.widgets import template_widgets
 from apps.forms.tests.oracle import case_param
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import IntakeSession

 TIER = "3"
@@ -268,12 +270,13 @@ CASES = list(_cases())
 @cache
 def _printed(persona):
     """
-    (form_type, full name) → what the persona's filled forms show there.
+    (form_type, full name) → what the persona's drawn forms print there.

-    A box shows its tick, the /AS of each widget that isn't /Off, and never its /V
-    (spec §6). A text box has no /AS, and shows its /V unless that is empty. Every
-    box in the filled forms has an entry, so an expected blank can't pass on a
-    name that is no box.
+    A box shows its tick: the state of each of its widgets with the check mark printed
+    inside (spec §6, 3a2 spec §8). A text box shows the text printed in each of its
+    drawn widgets, "" for one that prints nothing, so every widget of the name must
+    print the expected text. Every box of the template has an entry, so an expected
+    blank can't pass on a name that is no box.
     """
     if not District.objects.filter(code="ilnd").exists():
         call_command("loaddata", "ilnd_2025_data", verbosity=0)
@@ -282,16 +285,16 @@ def _printed(persona):
     printed = {}
     for form_type in EXPECTED[persona]:
         values = build_field_values(form_type, session)
-        for w in read_widgets(PDFFormFiller().fill(form_type, values)):
+        template = load_schema(form_type).template_filename
+        drawn = {(w.page, w.tag) for w in template_widgets(template) if w.drawn}
+        for w in read_drawn(form_type, PDFFormFiller().fill(form_type, values)):
+            if (w.page, w.tag) not in drawn:
+                continue
             shows = printed.setdefault((form_type, w.full_name), set())
-            if w.state is None:
-                shown = w.value
+            if not w.state:
+                shows.add(w.value)
             elif w.state != "/Off":
-                shown = w.state
-            else:
-                continue
-            if shown:
-                shows.add(shown)
+                shows.add(w.state)
     return printed


@@ -307,14 +310,14 @@ def _amount(text):
 def test_persona_packet_prints_the_right_figure(form_type, pdf_field, case, expected):
     printed = _printed(case)
     shown = printed.get((form_type, pdf_field), set())
-    if expected == "":  # the box shows nothing
+    if expected == "":  # the box shows nothing, in any of its widgets
         assert (form_type, pdf_field) in printed, f"no box named {pdf_field!r} on {form_type}"
-        assert shown == set(), f"wrong_value: prints {sorted(shown)}, expected blank"
+        assert shown <= {""}, f"wrong_value: prints {sorted(shown - {''})}, expected blank"
     elif expected.startswith("/"):  # a box: this tick and no other
         assert shown == {expected}, f"wrong_value: ticks {sorted(shown)}, expected {expected}"
-    elif _amount(expected) is not None:
+    elif _amount(expected) is not None:  # every widget prints it; a blank one is no amount
         assert {_amount(s) for s in shown} == {
             _amount(expected)
         }, f"wrong_value: prints {sorted(shown)}, expected {expected}"
-    else:
-        assert expected in shown, f"wrong_value: prints {sorted(shown)}, expected {expected}"
+    else:  # every widget prints it
+        assert shown == {expected}, f"wrong_value: prints {sorted(shown)}, expected {expected}"
PATCH
```

Tier 1 gives every text binding a sentinel that fits its box, and every combo binding a real district. Each sentinel must print in every drawn widget of its name and nowhere else. Tier 3 requires each persona's expected text in every drawn widget of the box.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_download_action.py b/backend/apps/forms/tests/test_download_action.py
index 19a8996..8552941 100644
--- a/backend/apps/forms/tests/test_download_action.py
+++ b/backend/apps/forms/tests/test_download_action.py
@@ -4,12 +4,13 @@ is filed, and exactly what was filed afterwards (spec §5.5).
 """

 import json
+import logging
 from unittest.mock import patch

 from django.urls import reverse

 from apps.forms.services.fill_resolver import RepeatOverflow
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn


 def _download(client, form):
@@ -17,7 +18,8 @@ def _download(client, form):


 def _printed(response, full_name):
-    return {w.value for w in read_widgets(response.content) if w.full_name == full_name}
+    """What the downloaded Form 121 prints in each widget of that name."""
+    return {w.value for w in read_drawn("form_121", response.content) if w.full_name == full_name}


 def _rename_filer(form, first_name):
@@ -80,6 +82,26 @@ def test_filed_form_without_a_snapshot_is_resolved_once_and_kept(
     assert json.loads(form.field_values)["Debtor1.First name"] == "Maria"


+def test_a_letter_the_form_cannot_print_refuses_the_download(
+    api_client_authed, generated_form_factory, caplog
+):
+    # An invented surname: ą is outside the court form's font, which would print "?".
+    form = generated_form_factory(status="generated")
+    _rename_filer(form, "Wąsowicz")
+
+    with caplog.at_level(logging.DEBUG):
+        response = _download(api_client_authed, form)
+
+    assert response.status_code == 422
+    assert response.data == {
+        "form_type": "form_121",
+        "error": "The court form can't print the letter “ą” in “Debtor 1 first name”. "
+        "Change it to a letter without the mark.",
+        "step": "debtor_info",
+    }
+    assert [r.getMessage() for r in caplog.records if "Wąsowicz" in r.getMessage()] == []
+
+
 def test_form_no_longer_in_the_packet_is_refused(api_client_authed, generated_form_factory):
     form = generated_form_factory(status="generated")
     form.form_type = "form_103b"  # no fee waiver application for this session
diff --git a/backend/apps/forms/tests/test_form_views.py b/backend/apps/forms/tests/test_form_views.py
index a218195..c1051a5 100644
--- a/backend/apps/forms/tests/test_form_views.py
+++ b/backend/apps/forms/tests/test_form_views.py
@@ -40,7 +40,7 @@ from apps.forms.services.pdf_filler import (
     UnprintableLetter,
     ValueTooLong,
 )
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import (
     DebtorInfo,
     ExpenseInfo,
@@ -1034,14 +1034,19 @@ def test_filed_form_survives_leaving_the_packet(api_client, session_with_debtor)
     ] == [(form.id, "filed")]
     form.refresh_from_db()
     assert json.loads(form.field_values) == filed_values
-    # It downloads, and prints what was filed, the old name included.
+    # It downloads, and prints what was filed, the old name included, in every widget of
+    # each name.
     assert download.status_code == status.HTTP_200_OK
-    printed = {w.full_name: w.value for w in read_widgets(download.content)}
+    printed = {}
+    for w in read_drawn("form_122a2", download.content):
+        printed.setdefault(w.full_name, set()).add(w.value)
     typed = {
         name: value for name, value in filed_values.items() if value and not value.startswith("/")
     }
     assert "Jane Doe" in typed.values()
-    assert {name: printed.get(name) for name in typed} == typed
+    assert {name: printed.get(name) for name in typed} == {
+        name: {value} for name, value in typed.items()
+    }


 # ── The snapshot stays on the server (DIG-124) ────────────────────────
PATCH
```

A download for a filer whose name the form can't print must be a 422 that names the letter, the box and the step, with nothing logged. The DIG-155 test checks every widget of each filed name.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_consumer_debts_and_paid_help.py b/backend/apps/forms/tests/test_consumer_debts_and_paid_help.py
index 8911f54..09ddf90 100644
--- a/backend/apps/forms/tests/test_consumer_debts_and_paid_help.py
+++ b/backend/apps/forms/tests/test_consumer_debts_and_paid_help.py
@@ -21,7 +21,7 @@ from apps.districts.models import District
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.forms.services.pdf_filler import PDFFormFiller
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import DebtorInfo, FormAnswer, IncomeInfo, IntakeSession

 User = get_user_model()
@@ -85,12 +85,12 @@ def _answer(session, key, value, form_type="form_101"):


 def _filled(session, form_type):
-    """Box → what a viewer sees in it once the form is filled: the ticked states, or the text."""
+    """Box → what the drawn form prints in it: the ticked states, or the text."""
     values = resolve(load_schema(form_type), session)
     shows = {}
-    for widget in read_widgets(PDFFormFiller().fill(form_type, values)):
+    for widget in read_drawn(form_type, PDFFormFiller().fill(form_type, values)):
         seen = shows.setdefault(widget.full_name, set())
-        if widget.state is not None:
+        if widget.state:
             if widget.state != "/Off":
                 seen.add(widget.state)
         elif widget.value:
diff --git a/backend/apps/forms/tests/test_form_101_schema.py b/backend/apps/forms/tests/test_form_101_schema.py
index 0bac23c..2e0b6b7 100644
--- a/backend/apps/forms/tests/test_form_101_schema.py
+++ b/backend/apps/forms/tests/test_form_101_schema.py
@@ -9,9 +9,7 @@ into a neighbouring box, and a line the intake doesn't ask stays blank (DIG-76,

 from datetime import date
 from decimal import Decimal
-from io import BytesIO

-import pypdf
 import pytest
 from django.contrib.auth import get_user_model

@@ -19,7 +17,7 @@ from apps.districts.models import District
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.forms.services.pdf_filler import PDFFormFiller
-from apps.forms.services.widgets import field_of, qualified_name
+from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import (
     AssetInfo,
     DebtInfo,
@@ -146,16 +144,12 @@ def test_line_19_reads_what_the_filer_owns_and_line_20_what_they_owe(session):

 def test_header_name_prints_on_pages_2_to_9(session):
     pdf = PDFFormFiller().fill("form_101", _petition(session))
-    # A viewer draws each widget's own appearance stream, so every page must have one.
-    pages = []
-    for number, page in enumerate(pypdf.PdfReader(BytesIO(pdf)).pages, start=1):
-        for annot in page.get("/Annots") or []:
-            widget = annot.get_object()
-            if qualified_name(field_of(widget)) != "Debtor1.Name":
-                continue
-            appearance = widget.get("/AP")
-            if appearance is not None and b"Jane Q Doe" in appearance["/N"].get_data():
-                pages.append(number)
+    # Each page's header widget is drawn on its own page.
+    pages = [
+        w.page
+        for w in read_drawn("form_101", pdf)
+        if w.full_name == "Debtor1.Name" and w.value == "Jane Q Doe"
+    ]
     assert pages == list(range(2, 10))


diff --git a/backend/apps/forms/tests/test_form_103b_answers.py b/backend/apps/forms/tests/test_form_103b_answers.py
index 2585130..69ffc49 100644
--- a/backend/apps/forms/tests/test_form_103b_answers.py
+++ b/backend/apps/forms/tests/test_form_103b_answers.py
@@ -21,7 +21,7 @@ from apps.forms.schema import load_schema
 from apps.forms.services.derivations import DERIVATIONS
 from apps.forms.services.fill_resolver import resolve
 from apps.forms.services.pdf_filler import PDFFormFiller
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import (
     DebtInfo,
     DebtorInfo,
@@ -91,11 +91,11 @@ def _apply(session, **answers):


 def _filled(session):
-    """Box → what a viewer sees in it once the form is filled: the ticked states, or the text."""
+    """Box → what the drawn form prints in it: the ticked states, or the text."""
     shows = {}
     for widget in _widgets(session):
         seen = shows.setdefault(widget.full_name, set())
-        if widget.state is not None:
+        if widget.state:
             if widget.state != "/Off":
                 seen.add(widget.state)
         elif widget.value:
@@ -105,7 +105,7 @@ def _filled(session):

 def _widgets(session):
     values = resolve(load_schema("form_103b"), session)
-    return read_widgets(PDFFormFiller().fill("form_103b", values))
+    return read_drawn("form_103b", PDFFormFiller().fill("form_103b", values))


 def test_line_2_prints_take_home_pay_for_you_the_subtotal_and_the_family_total(session):
diff --git a/backend/apps/forms/tests/test_form_106sum_schema.py b/backend/apps/forms/tests/test_form_106sum_schema.py
index 390042c..0ec9381 100644
--- a/backend/apps/forms/tests/test_form_106sum_schema.py
+++ b/backend/apps/forms/tests/test_form_106sum_schema.py
@@ -11,7 +11,7 @@ from apps.eligibility.cmi import IncomeNotSplit
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.forms.services.pdf_filler import PDFFormFiller
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import (
     AssetInfo,
     DebtInfo,
@@ -161,7 +161,7 @@ class TestForm106SumSchema:
     def test_line_6_says_the_filer_is_filing_under_chapter_7_11_or_13(self, populated_session):
         # Every DigniFi filing is Chapter 7, so line 6's Yes ticks and its No stays off.
         values = resolve(load_schema("form_106sum"), populated_session)
-        widgets = read_widgets(PDFFormFiller().fill("form_106sum", values))
+        widgets = read_drawn("form_106sum", PDFFormFiller().fill("form_106sum", values))
         assert sorted(w.state for w in widgets if w.full_name == "check6") == ["/Off", "/yes"]

     def test_cmi(self, populated_session):
diff --git a/backend/apps/forms/tests/test_form_107_schema.py b/backend/apps/forms/tests/test_form_107_schema.py
index 8e1bb55..18ceacb 100644
--- a/backend/apps/forms/tests/test_form_107_schema.py
+++ b/backend/apps/forms/tests/test_form_107_schema.py
@@ -13,9 +13,7 @@ answers stay stored for those steps.
 import json
 from datetime import date
 from decimal import Decimal
-from io import BytesIO

-import pypdf
 import pytest
 from django.contrib.auth import get_user_model

@@ -24,8 +22,7 @@ from apps.forms.field_index import index_path
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.forms.services.pdf_filler import PDFFormFiller
-from apps.forms.services.widgets import field_of, qualified_name
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import DebtorInfo, IntakeSession, SOFAReport

 User = get_user_model()
@@ -87,21 +84,13 @@ def _boxes_on_lines(*lines):


 def test_the_filers_name_heads_every_page(session):
-    pdf = _fill(session)
-
-    # A viewer draws each widget's own appearance stream, so every page must have one.
-    pages = []
-    for number, page in enumerate(pypdf.PdfReader(BytesIO(pdf)).pages, start=1):
-        for annot in page.get("/Annots") or []:
-            widget = annot.get_object()
-            if qualified_name(field_of(widget)) != "Debtor 1":
-                continue
-            appearance = widget.get("/AP")
-            if appearance is not None and b"Jane Q Doe" in appearance["/N"].get_data():
-                pages.append(number)
+    printed = read_drawn("form_107", _fill(session))
+
+    # Each page's header widget is drawn on its own page.
+    pages = [w.page for w in printed if w.full_name == "Debtor 1" and w.value == "Jane Q Doe"]
     assert pages == list(range(1, 13))
     # A single filer's statement: the spouse's line stays blank.
-    assert [w.value for w in read_widgets(pdf) if w.full_name == "Debtor 2"] == [None]
+    assert [w.value for w in printed if w.full_name == "Debtor 2"] == [""]


 def test_saved_sofa_rows_print_nothing_on_lines_4_to_6(session):
@@ -109,9 +98,9 @@ def test_saved_sofa_rows_print_nothing_on_lines_4_to_6(session):

     printed = {
         w.full_name
-        for w in read_widgets(_fill(session))
+        for w in read_drawn("form_107", _fill(session))
         if w.full_name in _boxes_on_lines("4", "5", "6")
-        and (w.value not in (None, "") or w.state not in (None, "/Off"))
+        and (w.value or w.state not in ("", "/Off"))
     }

     assert printed == set()
diff --git a/backend/apps/forms/tests/test_schedule_a_b_schema.py b/backend/apps/forms/tests/test_schedule_a_b_schema.py
index a3a4044..6a43344 100644
--- a/backend/apps/forms/tests/test_schedule_a_b_schema.py
+++ b/backend/apps/forms/tests/test_schedule_a_b_schema.py
@@ -16,7 +16,7 @@ from apps.districts.models import District
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.forms.services.pdf_filler import PDFFormFiller
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import AssetInfo, IncomeInfo, IntakeSession

 User = get_user_model()
@@ -101,12 +101,12 @@ def _asset(session, asset_type, value, description="Item"):


 def _filled(session):
-    """Box → what a viewer sees in it once the form is filled: the ticked states, or the text."""
+    """Box → what the drawn form prints in it: the ticked states, or the text."""
     values = resolve(load_schema("schedule_a_b"), session)
     shows = {}
-    for widget in read_widgets(PDFFormFiller().fill("schedule_a_b", values)):
+    for widget in read_drawn("schedule_a_b", PDFFormFiller().fill("schedule_a_b", values)):
         seen = shows.setdefault(widget.full_name, set())
-        if widget.state is not None:
+        if widget.state:
             if widget.state != "/Off":
                 seen.add(widget.state)
         elif widget.value:
diff --git a/backend/apps/forms/tests/test_schedules_d_e_f_schema.py b/backend/apps/forms/tests/test_schedules_d_e_f_schema.py
index 7978e80..19858dc 100644
--- a/backend/apps/forms/tests/test_schedules_d_e_f_schema.py
+++ b/backend/apps/forms/tests/test_schedules_d_e_f_schema.py
@@ -21,7 +21,7 @@ from apps.districts.models import District
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.forms.services.pdf_filler import PDFFormFiller
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import DebtInfo, DebtorInfo, IncomeInfo, IntakeSession

 User = get_user_model()
@@ -81,16 +81,16 @@ def debts(session):


 def _widgets(session, form_type):
-    """The filled form's widgets, as a viewer sees them."""
+    """What the drawn form prints in each widget."""
     values = resolve(load_schema(form_type), session)
-    return read_widgets(PDFFormFiller().fill(form_type, values))
+    return read_drawn(form_type, PDFFormFiller().fill(form_type, values))


 def _printed(session, form_type):
-    """Each box as a viewer sees it: a text box's value, or the states a checkbox ticks."""
+    """Each box as printed: a text box's value, or the states a checkbox ticks."""
     shown = {}
     for w in _widgets(session, form_type):
-        if w.state is None:
+        if not w.state:
             shown[w.full_name] = w.value
         elif w.state != "/Off":
             shown.setdefault(w.full_name, set()).add(w.state)
@@ -103,7 +103,7 @@ def test_schedule_d_prints_its_secured_total_in_the_grand_total_box(debts):
     widgets = _widgets(debts, "schedule_d")

     assert [(w.page, w.value) for w in widgets if w.full_name == "undefined_24"] == [(2, "3000.00")]
-    assert [w.value for w in widgets if w.full_name == "undefined_27"] == [None]
+    assert [w.value for w in widgets if w.full_name == "undefined_27"] == [""]


 def test_line_6j_totals_every_unsecured_debt_and_6f_the_unsecured_student_loans(debts):
@@ -180,4 +180,4 @@ def test_lines_the_intake_never_asks_print_nothing(debts):

     assert "check1" not in shown
     for box in ("Total_6a", "Total_6b", "Total_6c", "Total_6d", "Total_6e", "Total_6g", "Total_6h"):
-        assert shown[box] is None, box
+        assert shown[box] == "", box
diff --git a/backend/apps/forms/tests/test_schedules_g_h_schema.py b/backend/apps/forms/tests/test_schedules_g_h_schema.py
index d3b1cb4..ee7cd1e 100644
--- a/backend/apps/forms/tests/test_schedules_g_h_schema.py
+++ b/backend/apps/forms/tests/test_schedules_g_h_schema.py
@@ -17,7 +17,7 @@ from apps.districts.models import District
 from apps.forms.schema import load_schema
 from apps.forms.services.fill_resolver import resolve
 from apps.forms.services.pdf_filler import PDFFormFiller
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import Codebtor, DebtorInfo, ExecutoryContract, IntakeSession

 User = get_user_model()
@@ -66,9 +66,9 @@ def session(db):


 def _printed(session, form_type):
-    """The filled form's widgets, as a viewer sees them."""
+    """What the drawn form prints in each widget."""
     values = resolve(load_schema(form_type), session)
-    return read_widgets(PDFFormFiller().fill(form_type, values))
+    return read_drawn(form_type, PDFFormFiller().fill(form_type, values))


 @pytest.mark.parametrize("form_type", LISTS)
@@ -79,7 +79,7 @@ def test_the_filers_name_heads_every_page(session, form_type):
     named = {w.page for w in widgets if w.full_name == "Debtor 1" and w.value == "Jane Doe"}
     assert named == {1, 2}
     # A single filer's packet: the spouse's line stays blank.
-    assert [w.value for w in widgets if w.full_name == "Debtor 2"] == [None]
+    assert [w.value for w in widgets if w.full_name == "Debtor 2"] == [""]


 @pytest.mark.parametrize("listed,ticks", [(True, {"/yes"}), (False, {"/no"})])
diff --git a/backend/apps/forms/tests/test_signing_lines.py b/backend/apps/forms/tests/test_signing_lines.py
index 31a4b88..161adfd 100644
--- a/backend/apps/forms/tests/test_signing_lines.py
+++ b/backend/apps/forms/tests/test_signing_lines.py
@@ -14,7 +14,7 @@ from django.core.management import call_command

 from apps.forms.registry import build_field_values
 from apps.forms.services.pdf_filler import PDFFormFiller
-from apps.forms.tests.pdf_readback import read_widgets
+from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import FormAnswer, IntakeSession

 # Each form's Debtor 1 signature line and signing date that held a binding before Q6.
@@ -41,8 +41,8 @@ STILL_PRINTS = {
 @cache
 def _printed():
     """
-    (form_type, full name) → the text Priya's filled forms show there, once she has given
-    a signing date and named an attorney. Every box in the filled forms has an entry, so a
+    (form_type, full name) → the text Priya's drawn forms print there, once she has given
+    a signing date and named an attorney. Every box of the template has an entry, so a
     box name that is no box can't pass as blank.
     """
     call_command("loaddata", "ilnd_2025_data", verbosity=0)
@@ -58,7 +58,7 @@ def _printed():
     printed = {}
     for form_type in SIGNING_LINES:
         values = build_field_values(form_type, session)
-        for widget in read_widgets(PDFFormFiller().fill(form_type, values)):
+        for widget in read_drawn(form_type, PDFFormFiller().fill(form_type, values)):
             shows = printed.setdefault((form_type, widget.full_name), set())
             if widget.value:
                 shows.add(widget.value)
PATCH
```

The per-form tests read the drawn page with `read_drawn`. A blank box reads `""` instead of `None`, and Form 101's and 107's header tests read each page's printed header.

- [ ] **Step 2: Run them and watch them fail**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
cd backend && $PY -m pytest --tb=line -rfE apps/forms/tests/test_pdf_filler.py apps/forms/tests/test_download_action.py apps/forms/tests/test_form_views.py apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_consumer_debts_and_paid_help.py apps/forms/tests/test_form_101_schema.py apps/forms/tests/test_form_103b_answers.py apps/forms/tests/test_form_106sum_schema.py apps/forms/tests/test_form_107_schema.py apps/forms/tests/test_schedule_a_b_schema.py apps/forms/tests/test_schedules_d_e_f_schema.py apps/forms/tests/test_schedules_g_h_schema.py apps/forms/tests/test_signing_lines.py -q -p no:cacheprovider 2>&1 | grep -E '^/.*\.py:[0-9]+: |^(FAILED|ERROR) |^=+ .* in [0-9.]+s' | sed -E 's#^/.*/backend/##'
```

Expected: FAIL — `15 failed, 1033 passed`. The 15 are this task's tests of the drawing, and the old filler fails each of them, with lines such as `assert 200 == 422`, `assert '?ukasz O?Brien' == 'Łukasz O’Brien'`, `UnknownField: form_107: no widget named ['Debtor 1@1:T1']`, `assert 'kestrel.wanamaker.okonkwo@ex' == 'kestrel.wana...o@example.org'`, `assert 403.1600029964447 >= 404.2` and `assert ["Text string...nerate=True."] == []`.

What each line means:

- The Download refusal test gets a 200: the old `fill()` never runs `check()`, so nothing refuses the "ą".
- The pin test stops on `assert False`, because `/AcroForm` is still a dictionary, not null.
- A/B's page-1 header still carries its own `/DR`, so Ł and ’ print as "?".
- The old `fill()` takes no widget's own key, so all 9 cases that use one stop on `UnknownField`: the two shared-name cases, the three tagged values and the four ticks.
- The email box draws at its own 10 pt, and the value is cut off.
- The multi-line box's first line has its top at y 403.16, above the rect's top at 404.2 (MuPDF's y runs down the page).
- pypdf logs its warning about characters the widget's own font lacks, which quotes the filer's value.

The 1,033 that pass are every other test in these 14 files, the 17 blank-template cases and the empty multi-line box among them. MuPDF's text extraction reads a widget's appearance stream even before a bake, and the old filler built an appearance for every widget of a name. So every ported read-back passes against the old filler: the port keeps what each test proved, and Step 5 runs them against the new one.

- [ ] **Step 3: Pin PyMuPDF**

```bash
git apply <<'PATCH'
diff --git a/backend/requirements/base.txt b/backend/requirements/base.txt
index 6a85f08..a566a16 100644
--- a/backend/requirements/base.txt
+++ b/backend/requirements/base.txt
@@ -12,7 +12,7 @@ pydantic>=2.9.0,<3.0.0
 opendataloader-pdf
 google-genai>=0.8
 openai==1.60.0
-pymupdf
+pymupdf==1.27.2.3
 cryptography==44.0.1
 # WhiteNoiseMiddleware is wired in settings/base.py, so every environment needs it
 whitenoise[brotli]~=6.9.0
PATCH
```

PyMuPDF is already installed, at 1.27.2.3, but `base.txt` left it unpinned (G7). Spec §4.6 pins it at the version the bake was tested with, beside `pypdf==6.13.1`, and the pin test checks both.

- [ ] **Step 4: Draw each planned widget and bake the page**

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
index 7cf5957..659b5cd 100644
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -1,5 +1,5 @@
 """
-PDFFormFiller — fills an AO court PDF template with resolved field values.
+PDFFormFiller — draws resolved field values on an AO court PDF template.

 Keys are index full names (apps.forms.field_index). A key fills only the
 widgets whose qualified name equals it exactly. pypdf's
@@ -11,23 +11,34 @@ check() plans what each widget a values dict fills will print, and at what size,
 without drawing. It refuses a letter a box's font can't print and a value too long
 for its box even in small print, naming the box and where the filer fixes the value.

+fill() draws that plan: pypdf builds each planned widget's own appearance, and
+PyMuPDF bakes every widget into the page, so the PDF has no fillable field left.
+
 Usage:
     pdf_bytes = PDFFormFiller().fill("form_121", {"Debtor1.First name": "Maria"})
     plan = PDFFormFiller().check("form_121", {"Debtor1.First name": "Maria"})
 """

+import re
 import unicodedata
 from dataclasses import dataclass
 from io import BytesIO
 from pathlib import Path

+import pymupdf
 import pypdf
 from django.conf import settings

 # pypdf._font and pypdf.generic._appearance_stream are pypdf internals, pinned with
 # pypdf==6.13.1; test_pdf_filler.py fails if they move.
 from pypdf._font import Font
-from pypdf.generic import DictionaryObject, NameObject, TextStringObject
+from pypdf.generic import (
+    ArrayObject,
+    DictionaryObject,
+    NameObject,
+    NumberObject,
+    TextStringObject,
+)
 from pypdf.generic._appearance_stream import TextStreamAppearance

 from apps.forms.field_index import load_index
@@ -38,13 +49,15 @@ from apps.forms.services.widgets import (
     TemplateWidget,
     field_of,
     parse_key,
-    qualified_name,
     template_widgets,
+    widget_for,
 )

 _BOXES = ("CheckBox", "RadioButton")
 # pypdf draws each character of a comb box as its own string, which these break (R33).
 _COMB_BREAKERS = "()\\"
+# The first text move in pypdf's appearance stream: "<x> <y> Td", before any string.
+_FIRST_MOVE = re.compile(rb"^(\S+) (\S+) Td$", re.MULTILINE)


 class UnknownField(Exception):
@@ -166,6 +179,68 @@ def _refused_letter(widget: TemplateWidget, font: Font, text: str) -> str | None
     return None


+def _lower_first_line(appearance: TextStreamAppearance, by: float) -> None:
+    """
+    Move a multi-line box's first line down by `by` points. pypdf hangs line 1 from the
+    font's bounding box top at the box's height plus its margin, so the box cuts off a
+    capital's mark; 2 × margin lower, that top sits at the clip's top (R35). A stream
+    with no line (an empty value) is left as it is.
+    """
+    data = appearance.get_data()
+    move = _FIRST_MOVE.search(data)
+    if move is None:
+        return
+    y = float(move[2]) - by
+    appearance.set_data(data[: move.start(2)] + str(y).encode() + data[move.end(2) :])
+
+
+def _draw(
+    writer: pypdf.PdfWriter,
+    page: pypdf.PageObject,
+    acro_form: DictionaryObject,
+    annotation: DictionaryObject,
+    planned: Planned,
+) -> None:
+    """Give one widget its planned value: a box its state, a text or combo box its appearance."""
+    widget = planned.widget
+    field = field_of(annotation)
+    if widget.kind in _BOXES:
+        # The template's own check mark prints from /AS; /V keeps the state ticked.
+        if planned.value != "/Off":
+            field[NameObject("/V")] = NameObject(planned.value)
+        annotation[NameObject("/AS")] = NameObject(planned.value)
+        return
+    if "/I" in field:  # a combo's stale selected index would override /V
+        del field["/I"]
+    # A widget's own /DR lacks the template's encoding: pypdf would encode with it and
+    # print "?" for letters the AcroForm font draws (R32).
+    if "/DR" in annotation:
+        del annotation["/DR"]
+    # pypdf reads a comb box's cell count from the widget alone (R4).
+    if widget.comb and widget.max_len is not None and "/MaxLen" not in annotation:
+        annotation[NameObject("/MaxLen")] = NumberObject(widget.max_len)
+    # pypdf reads the value and the alignment from the field, which a widget may share
+    # with its siblings, so both are this widget's own just before it is built (R8, R26).
+    original = field.get("/V")
+    field[NameObject("/V")] = TextStringObject(planned.value)
+    field[NameObject("/Q")] = NumberObject(widget.align)
+    # pypdf internals, pinned: build the text appearance at the planned size, and add it.
+    appearance = TextStreamAppearance.from_text_annotation(
+        writer, page, False, acro_form, field, annotation, user_font_size=planned.size
+    )
+    if widget.multiline:
+        _lower_first_line(appearance, 2 * widget.margin)
+    annotation[NameObject("/AP")] = DictionaryObject(
+        {NameObject("/N"): writer._add_object(appearance)}
+    )
+    # The bake builds an appearance from the field's /V for a sibling that has none of
+    # its own, so the field keeps the value it had: this one prints only here (R42).
+    if original is None:
+        del field["/V"]
+    else:
+        field[NameObject("/V")] = original
+
+
 class PDFFormFiller:
     """Fill AO court PDF templates with field values and return bytes."""

@@ -245,75 +320,49 @@ class PDFFormFiller:
             planned.append(Planned(widget, *fitted))
         return (PlannedPart({"kind": "form", "values": values}, tuple(planned)),)

-    def fill(self, form_type: str, field_values: dict[str, str]) -> bytes:
+    def fill(self, form_type: str, values: dict) -> bytes:
         """
-        Fill the form's template with field_values and return the PDF bytes.
+        Draw the values on the form's template and return a PDF with no fillable field.
+
+        check() plans every widget first. pypdf then builds each planned widget's own
+        appearance at its planned size; the widgets the template doesn't print and the
+        second widget of each stacked pair are removed; and PyMuPDF bakes every other
+        widget into its page. An unfilled widget prints as the blank form shows it.

         Args:
             form_type: a registered form type; its schema names the template.
-            field_values: {full_name: value}. A value is text, an /Opt entry for
-                a combo box, or an export state such as "/Chapter 7" for a button.
+            values: as check() takes them.

         Raises:
-            UnknownField: a key names no widget.
             TemplateHasNoForm: the template has no /AcroForm.
-            InvalidFieldValue: a button state or combo option the template lacks.
+            UnknownField, InvalidFieldValue, UnprintableLetter, ValueTooLong: as check().
         """
-        schema = load_schema(form_type)
-        template_path = Path(settings.PDF_FORMS_DIRECTORY) / schema.template_filename
-        writer = pypdf.PdfWriter(clone_from=str(template_path))
+        template = load_schema(form_type).template_filename
+        writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
         if "/AcroForm" not in writer.root_object:
             raise TemplateHasNoForm(form_type)
+        (part,) = self.check(form_type, values)
+        planned = {(p.widget.page, p.widget.tag): p for p in part.widgets}
         acro_form = writer.root_object["/AcroForm"].get_object()
-        # Viewers draw the appearance streams written here, not their own.
-        writer.set_need_appearances_writer(False)
-
-        filled: set[str] = set()
-        buttons: set[str] = set()
-        ticked: set[str] = set()
-        for page in writer.pages:
-            for annot in page.get("/Annots") or []:
-                widget = annot.get_object()
-                if widget.get("/Subtype") != "/Widget":
-                    continue
-                field = field_of(widget)
-                name = qualified_name(field)
-                if name not in field_values:
-                    continue
-                filled.add(name)
-                value = field_values[name]
-
-                if field.get_inherited("/FT") == "/Btn":
-                    buttons.add(name)
-                    field[NameObject("/V")] = NameObject(value)
-                    if value in widget["/AP"]["/N"]:
-                        widget[NameObject("/AS")] = NameObject(value)
-                        ticked.add(name)
-                    else:
-                        widget[NameObject("/AS")] = NameObject("/Off")
-                    continue
-
-                if field.get_inherited("/FT") == "/Ch":
-                    options = [str(o) for o in field.get_inherited("/Opt", [])]
-                    if value not in options:
-                        raise InvalidFieldValue(form_type, name)
-                    if "/I" in field:  # a stale selected index would override /V
-                        del field["/I"]
-                field[NameObject("/V")] = TextStringObject(value)
-                # pypdf internal, pinned: builds the text appearance from /DA and /V.
-                appearance = TextStreamAppearance.from_text_annotation(
-                    writer, page, False, acro_form, field, widget
-                )
-                widget[NameObject("/AP")] = DictionaryObject(
-                    {NameObject("/N"): writer._add_object(appearance)}
-                )
-
-        unknown = sorted(set(field_values) - filled)
-        if unknown:
-            raise UnknownField(form_type, unknown)
-        for name in sorted(buttons - ticked):
-            raise InvalidFieldValue(form_type, name)

-        buf = BytesIO()
-        writer.write(buf)
-        return buf.getvalue()
+        for number, page in enumerate(writer.pages, start=1):
+            if "/Annots" not in page:
+                continue
+            kept = ArrayObject()
+            for annot in page["/Annots"]:
+                annotation = annot.get_object()
+                if annotation.get("/Subtype") == "/Widget":
+                    widget = widget_for(template, number, annotation, float(page.mediabox.top))
+                    if not widget.drawn:
+                        continue
+                    if (number, widget.tag) in planned:
+                        _draw(writer, page, acro_form, annotation, planned[(number, widget.tag)])
+                kept.append(annot)
+            page[NameObject("/Annots")] = kept
+
+        buffer = BytesIO()
+        writer.write(buffer)
+        document = pymupdf.open("pdf", buffer.getvalue())
+        document.bake(annots=False, widgets=True)
+        document.xref_set_key(document.pdf_catalog(), "AcroForm", "null")
+        return document.tobytes()
PATCH
```

`fill()` clones the template, refuses one with no `/AcroForm`, and runs `check()`. On each page it drops the widgets that never print and hands each planned widget to `_draw()`.

- A box gets its state.
- A text or combo box loses its own `/DR` (R32), and a comb box gets its inherited `/MaxLen` (R4). It is then built at its planned size, with the field's `/V` and `/Q` set to its own (R8, R26) and the `/V` put back right after (R42).
- `_lower_first_line()` moves a multi-line box's first line down by twice its margin (R35).

After one write, PyMuPDF bakes every remaining widget into its page, and `/AcroForm` is set to null.

- [ ] **Step 5: Run the tests again**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
cd backend && $PY -m pytest --tb=line -rfE apps/forms/tests/test_pdf_filler.py apps/forms/tests/test_download_action.py apps/forms/tests/test_form_views.py apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_oracle_tier3.py apps/forms/tests/test_consumer_debts_and_paid_help.py apps/forms/tests/test_form_101_schema.py apps/forms/tests/test_form_103b_answers.py apps/forms/tests/test_form_106sum_schema.py apps/forms/tests/test_form_107_schema.py apps/forms/tests/test_schedule_a_b_schema.py apps/forms/tests/test_schedules_d_e_f_schema.py apps/forms/tests/test_schedules_g_h_schema.py apps/forms/tests/test_signing_lines.py -q -p no:cacheprovider 2>&1 | grep -E '^/.*\.py:[0-9]+: |^(FAILED|ERROR) |^=+ .* in [0-9.]+s' | sed -E 's#^/.*/backend/##'
```

Expected: `1048 passed`.

That is Step 2's 15 failures and 1,033 passes, all passing now.

- [ ] **Step 6: Say in the docs how a form prints now**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 60c06d5..2bf4551 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -28,14 +28,14 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Debt and asset amounts are readable, as strings** — the owner gets `DebtInfo.amount_owed` and `AssetInfo.current_value`/`amount_owed` back (SSN and `account_number` stay write-only). DRF sends decimals as strings (`"2500.00"`), so the wizard converts them with `hydrateAmounts` (`utils/parseAmount.ts`) as session data enters step state; a raw string in a step's `reduce` joins as text (`$02500.00100.50`). A stored amount wider than `DecimalField(12, 2)` makes every read of that session 500, so every write path must bound it (`DraftDebtCreator` stores it as 0; documents `validate` returns 400).
 - **Seed order** — `seed_demo_data` requires `loaddata ilnd_2025_data` first, or means test has no median income data. It reads the median table in force on today's real date, not the tests' pinned one, and when none is (from November 1, 2026 until the November table is loaded) it prints a message naming `docs/REFERENCE_TABLES.md` and changes nothing, so even `--reset` leaves the existing personas. Personas seeded before income was stored by source must be re-created with `seed_demo_data --reset` (migration 0014 leaves their totals unsplit, and a plain re-run skips existing users).
 - **household_size defaults to 1** — `DebtorInfo.household_size` has `default=1`; the means test prefers it over deriving from marital status + dependents. Always set it explicitly.
-- **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 > median_income_threshold`, through `is_above_median` (`apps/eligibility/cmi.py`), the means test's own comparison, so income exactly at the median counts as below (DIG-136). Never read `above_median_calculated`: a row calculated before DIG-128 was fixed can still carry a stale True. 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. Generate All, Generate, Regenerate, the download of an unfiled form and the packet list of a completed intake work the means test out again from the stored intake first (`_recalculate_means_test` in `apps/forms/views.py`), so a stale `MeansTest` row never decides the packet (DIG-160); an unfinished intake's packet list reads the stored row. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words, and so are income not entered by source (`IncomeNotSplit`) and no median table in force on the fill date (`NoTableInForce`, which logs the table, the date and the district); any other failure is a 500 logged by exception type only.
-- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key: no `DebtorInfo` row (the name-and-address sentence; the fields themselves aren't checked) or an SSN that isn't 9 digits (the registry's own `_needs_ssn`, so Complete and Forms 101 and 121 say the same thing), income not entered by source (`IncomeNotSplit`, no income row included), an Expenses step never saved (no `ExpenseInfo` row), and a scanned debt the filer hasn't confirmed (a `DebtInfo` with `is_draft`, step `debts`; see "Document upload sits mid-wizard"). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. A forms refusal also carries the `step` (a wizard step key) or `page` (a route) that fixes it, when the exception names one: `PreconditionMissing.step`, `IncomeNotSplit.step` (`income_info`) and `IntakeNotFinished.page` (`/intake`); "already filed", "not in your packet" and `NoTableInForce` carry neither, and the key is absent, never null. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must lock the session first (see "Saves lock the session") and call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
+- **The packet decides which forms a filer gets** — `apps/forms/registry.py` maps each form to `applies(session)` and `requires(session)`. 103B applies only with a `FeeWaiverApplication`; 122A-2 only when `MeansTest.calculated_cmi × 12 > median_income_threshold`, through `is_above_median` (`apps/eligibility/cmi.py`), the means test's own comparison, so income exactly at the median counts as below (DIG-136). Never read `above_median_calculated`: a row calculated before DIG-128 was fixed can still carry a stale True. 122A-1Supp not until step 4; 122B is gone. A packet holds 14–16 forms. Generate All, Generate, Regenerate, the download of an unfiled form and the packet list of a completed intake work the means test out again from the stored intake first (`_recalculate_means_test` in `apps/forms/views.py`), so a stale `MeansTest` row never decides the packet (DIG-160); an unfinished intake's packet list reads the stored row. `generate` on a form outside the packet, or with a missing precondition (`PreconditionMissing`), is a 422 in plain words, and so are income not entered by source (`IncomeNotSplit`), no median table in force on the fill date (`NoTableInForce`, which logs the table, the date and the district), and a letter the form's font can't print (`UnprintableLetter`) or a value too long for its box even at 6 pt (`ValueTooLong`), whose sentences name the box; any other failure is a 500 logged by exception type only.
+- **Forms need a completed intake** — through the API, only the session's `complete` action sets `status="completed"`: `status` and `current_step` are read-only on `IntakeSessionSerializer`, and `update_step` takes only a whole number from 1 to 8 (anything else is a 400). Complete refuses with a 400 `{message, errors: [{step, message}]}`, one entry per gap in wizard order, each `step` a `WIZARD_STEPS` key: no `DebtorInfo` row (the name-and-address sentence; the fields themselves aren't checked) or an SSN that isn't 9 digits (the registry's own `_needs_ssn`, so Complete and Forms 101 and 121 say the same thing), income not entered by source (`IncomeNotSplit`, no income row included), an Expenses step never saved (no `ExpenseInfo` row), and a scanned debt the filer hasn't confirmed (a `DebtInfo` with `is_draft`, step `debts`; see "Document upload sits mid-wizard"). The forms views refuse any other status with a 422, "Finish your intake before preparing your forms.": Generate All once for the whole call, before it deletes anything; Generate, Regenerate and the download of an unfiled form through `_prepare`. The packet list never refuses an unfinished intake. A forms refusal also carries the `step` (a wizard step key) or `page` (a route) that fixes it, when the exception names one: `PreconditionMissing.step`, `IncomeNotSplit.step` (`income_info`), `IntakeNotFinished.page` (`/intake`) and the `step` or `page` of an `UnprintableLetter` or `ValueTooLong`, from the binding that feeds the box (`fix_for` in `fill_resolver.py`); "already filed", "not in your packet" and `NoTableInForce` carry neither, and the key is absent, never null. The check lives in the views, not in `build_field_values`, so forms view tests need a completed session, with income by source and a district with a median table in force on the fill date, since Generate All, Generate, Regenerate, an unfiled download and a completed intake's packet list work the means test out. Every intake-data write sets a completed session back to `in_progress` through `IntakeSession.reopen()`, so the filer presses Complete again: a session PATCH carrying `debtor_info`, `income_info`, `expense_info`, `debts` or `assets`; the contracts and codebtors endpoints; `DebtViewSet`/`AssetViewSet` writes; an upload that adds a draft debt or pay-stub figures, and a correction to a scanned bill or pay stub. `update_step` (Continue) sets `in_progress` itself. Form answers (`answers/bulk`), SOFA and the fee-waiver application never reopen it; a new intake-data write path must lock the session first (see "Saves lock the session") and call `reopen()`. A failed Complete or means-test call keeps the filer on Review (DIG-150), and the dashboard shows a "Finish your intake" link back to the wizard until the session is complete.
 - **SSN on forms** — Form 101's `Debtor1.SSNum` gets the last 4 digits from the `ssn_last_4` derivation; the full SSN appears only on Form 121.
 - **Means test units** — CMI is monthly, Census median is annual. `MeansTest.calculate()` annualizes CMI ×12 per § 707(b)(7). The original bug passed everyone.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
 - **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
-- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`, which `fill()` doesn't take yet: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
-- **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. It has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
+- **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
+- **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. Tiers 1 and 3 read the printed page, not `/V`: `read_drawn` (`apps/forms/tests/pdf_readback.py`) takes a widget's Helvetica text and the template's ZapfDingbats check mark inside its rect, and reads `""` where a box prints only the blank template's own default (the district combos' placeholder, A/B `19.1`–`19.3 % of ownership` "0%", C `page 2` and G `fill 2.6` "2"), so a blank assertion on such a box can't see that default. It has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
 - **Blank, not 0.00, on the forms** — a derivation must not turn a missing input into 0.00: a line DigniFi never asks (interest, payroll deductions, priority, a spouse's column) and an income source left empty print blank, and a source typed as $0 prints 0.00. A total counts an unasked line as zero and still prints. The 13 expense amounts are stored as $0 when left empty, so an expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0, while the totals (Schedule J 22a and 22c, 106Sum line 5, 103B line 6) still print. One exception remains: with no `ExpenseInfo` row at all, those totals and Schedule J 23b print 0.00, and 23c prints the income less 0.00 (`_total_monthly_expenses`, the one function behind all of them; any other error fails the form). Signature lines and signing dates stay blank for wet ink (`test_signing_lines.py`). No production schema has a repeat group: Form 107's prior-income and creditor-payment rows came off until steps 3–4 ask what they need, and the SOFA answers stay stored. The engine (`repeat`, `RepeatOverflow` and its 422) stays for later steps; only synthetic tests reach it.
 - **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, and the API never returns it. `form_data` is blank; its column is dropped one release after this code is live. A filed form downloads its stored `field_values`; an unfiled one is resolved fresh on every download.
@@ -84,7 +84,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.

 - **Backend:** Django 5.0 + DRF, Python 3.11, PostgreSQL 15, `encrypted-model-fields` (Fernet PII encryption)
 - **Frontend:** React 19 + Vite 7 + TypeScript, Context API (not Redux), react-router-dom v7
-- **PDF:** pypdf fills official AO court templates. Each schema in `data/forms/schemas/` binds a field to a widget's full name in the field index (`data/forms/field_index/<template stem>.index.json`). `build_field_values(form_type, session)` checks the form's preconditions and resolves its schema; `PDFFormFiller().fill(form_type, values)` fills exactly those full names in the template from `data/forms/pdfs/` and raises `UnknownField` for any other name.
+- **PDF:** pypdf and PyMuPDF draw on the official AO court templates. Each schema in `data/forms/schemas/` binds a field to a widget's full name in the field index (`data/forms/field_index/<template stem>.index.json`). `build_field_values(form_type, session)` checks the form's preconditions and resolves its schema; `PDFFormFiller().check(form_type, values)` plans the widgets each key names (a full name, or `<full name>@<page>:<tag>` for one widget) in the template from `data/forms/pdfs/`, and raises `UnknownField` for any other name; `fill()` runs it, then pypdf builds each planned widget's own appearance and PyMuPDF bakes every remaining widget into the page (the print buttons and the second widget of each stacked pair are removed first), so the PDF it returns can't be filled in a viewer.
 - **PDF templates:** 67 official AO court PDFs in `data/forms/pdfs/` (committed). Baked into Heroku image.
 - **Forms:** 17 form types in `apps/forms/registry.py` (`FORM_REGISTRY` / `get_all_form_types()` / `packet(session)`). `generate_all` gives each form its own savepoint.
 - **OCR service:** provider-agnostic. `OCR_PROVIDER` selects `openai` (default, `gpt-4o`, `OPENAI_API_KEY`) or `gemini` (`gemini-2.0-flash`, `GEMINI_API_KEY`); `OCR_MODEL` overrides the model so a model change is a config var, not a deploy. No local model — both call a hosted API directly.
@@ -103,7 +103,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - `apps/eligibility/services/means_test_calculator.py` — `MeansTestCalculator`, which runs and saves `MeansTest.calculate()` (`apps/eligibility/models.py`, where CMI is annualized)
 - `apps/eligibility/cmi.py` — `current_monthly_income` (the one CMI), `IncomeNotSplit`, `is_above_median`
 - `apps/forms/registry.py` — `FORM_REGISTRY` (17 form_type → `PacketForm(applies, requires)`) in filing order, `packet()`, `build_field_values()`
-- `apps/forms/services/` — `pdf_filler.py` (`PDFFormFiller`, exact full names), `fill_resolver.py` + `derivations.py` (schema-driven fill engine)
+- `apps/forms/services/` — `pdf_filler.py` (`PDFFormFiller`: `check()` plans, `fill()` draws and bakes), `widgets.py` (each template widget by page and tag), `text_fit.py` (letters and fit, as pypdf lays text out), `fill_resolver.py` + `derivations.py` (schema-driven fill engine)
 - `apps/forms/field_index.py` + `apps/forms/checks.py` — the field index loader and the schema system check
 - `apps/forms/views.py` — GeneratedFormViewSet (generate, generate_all, download, mark_filed)
 - `apps/documents/services/providers/` — `base.py` (`BaseOCRProvider`), `openai_provider.py`, `gemini.py`, `prompts/`
diff --git a/docs/superpowers/specs/2026-10-16-forms-step3-design.md b/docs/superpowers/specs/2026-10-16-forms-step3-design.md
index ac4b8b2..3e905bd 100644
--- a/docs/superpowers/specs/2026-10-16-forms-step3-design.md
+++ b/docs/superpowers/specs/2026-10-16-forms-step3-design.md
@@ -237,6 +237,8 @@ Two interim choices fall to the 3a1 spec:
 - per widget, PyMuPDF `page.insert_text(Point(rect.x0 + 2, rect.y1 - 0.25 * h), text, fontname="helv")` (`insert_textbox` drew nothing on 14 pt boxes);
 - then `delete_widget` on every widget, and `/AcroForm` set to null.

+This method was replaced in 3a2: pypdf builds each widget's appearance and PyMuPDF bakes it (`docs/superpowers/specs/2026-10-17-forms-step3a2-design.md` §3).
+
 Writing each value at its own widget's rectangle, not by field name, fixes the shared-name boxes:

 - `undefined_19`;
@@ -754,7 +756,7 @@ Every owner answer, controller ruling, ticket and counsel item maps to exactly o
 | CORR.valid_through | 3a1 | `valid_through` per table; irregular tables guarded only by the runbook; tests pin the fill date                                   |
 | CORR.J3            | 3e2 | Schedule J line 3 asked in the form's words on the Expenses step (owner confirmed)                                                 |
 | CORR.J45           | 3c  | A homeowner's J line 4 mortgage payment and J line 5 from the debts linked to "my home"; 3e2 does not ask line 5 (owner confirmed) |
-| SPIKE              | 3a2 | The engine method (PyMuPDF `insert_text` plus `delete_widget`; exact-clip oracle)                                                  |
+| SPIKE              | 3a2 | The engine method (PyMuPDF `insert_text` plus `delete_widget`; exact-clip oracle), replaced by 3a2's spec §3                       |
 | DIG-273            | 3a1 | The id round-trip for assets and debts, and the `useAutoSave` baseline                                                             |
 | DIG-274            | 3a1 | The median fix                                                                                                                     |
 | DIG-275            | 3h  | Line 35's past-due amount ÷ 60 in the one calculator                                                                               |
PATCH
```

`CLAUDE.md` describes the drawing and the read-back, names the two refusals that now reach the filer, and drops the clause that `fill()` doesn't take tagged keys yet. The umbrella spec points from its old method to the 3a2 spec's §3.

- [ ] **Step 7: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2293 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  397 passed (397)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

That is 32 more backend cases than after Task 2: 31 in `test_pdf_filler.py` and 1 in `test_download_action.py`. Every other changed test keeps its cases. The 25 skips are the Postgres-only tests under sqlite. The next command runs them against the Postgres database named by `DATABASE_URL` in `.claude/forms-step3a2.env`, as CI's "Run the Postgres-only tests" step does. This task touches no locking, so they pass unchanged.

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

- [ ] **Step 8: Run the journeys twice**

```bash
set -eo pipefail
zsh .claude/e2e.sh 2
```

Expected: `RUN 1 exit=0: 8 passed` and `RUN 2 exit=0: 8 passed`.

Five persona journeys and the SOFA journey press Generate All, which in this task draws and bakes every form of the packet, and the SOFA journey downloads Form 107, a real drawn PDF.

These results are the implementer's; this plan's own check doesn't run the journeys. The first round's build passed both runs. On the tree committed after the fix round, the full gate run printed `RUN 1 exit=1: 1 failed  7 passed (2.1m)` and then `RUN 2 exit=0: 8 passed (1.5m)`. A rerun printed `RUN 1 exit=0: 8 passed (1.6m)` and `RUN 2 exit=0: 8 passed (1.5m)`.

The one failure was `scanned-bill-journey`: it timed out after 30 s waiting for its upload row's "✓ Done".

- The upload reached the view about 5 s after its preflight, and its `OCRResult` is `failed`, with `failure_reason` `processing_error` and `error_message` `APIConnectionError`. The backend's OpenAI SDK couldn't reach the journey's fake OpenAI server.
- The upload is a PNG, which goes straight to the vision call: no PDF library, no Java and no forms code is on that path.
- In that run, Playwright's 4 workers ran up to 4 Generate Alls at once, each drawing about 16 forms in the one `runserver` process (one took 33 s). That drawing load is new in this task.
- If the journey fails for you the same way, read that upload's `OCRResult.error_message` in a Django shell (it holds only the exception's class) and `.claude/e2e-logs/backend.log` before running again.
- Two ticket candidates come from it: the fake server's reachability under that load, and `OpenAIProvider` building its client with no timeout, so a model call that never answers waits the SDK's 600 s.

- [ ] **Step 9: Commit**

```bash
set -eo pipefail
git add \
  CLAUDE.md \
  backend/apps/forms/services/pdf_filler.py \
  backend/apps/forms/tests/pdf_readback.py \
  backend/apps/forms/tests/test_consumer_debts_and_paid_help.py \
  backend/apps/forms/tests/test_download_action.py \
  backend/apps/forms/tests/test_form_101_schema.py \
  backend/apps/forms/tests/test_form_103b_answers.py \
  backend/apps/forms/tests/test_form_106sum_schema.py \
  backend/apps/forms/tests/test_form_107_schema.py \
  backend/apps/forms/tests/test_form_views.py \
  backend/apps/forms/tests/test_oracle_tier1.py \
  backend/apps/forms/tests/test_oracle_tier3.py \
  backend/apps/forms/tests/test_pdf_filler.py \
  backend/apps/forms/tests/test_schedule_a_b_schema.py \
  backend/apps/forms/tests/test_schedules_d_e_f_schema.py \
  backend/apps/forms/tests/test_schedules_g_h_schema.py \
  backend/apps/forms/tests/test_signing_lines.py \
  backend/requirements/base.txt \
  docs/superpowers/specs/2026-10-16-forms-step3-design.md
git commit -F - <<'MSG'
feat(forms): draw each widget's own value and bake it into the page

PDFFormFiller.fill() returned a fillable PDF: every widget of a shared
name showed one value, a value too wide for its box was cut off, and a
letter outside the font's encoding printed as "?". It now runs check()
and draws its plan, and the PDF it returns has no fillable field left.

- pypdf clones the template once. Each planned text or combo widget
  gets its own appearance from pypdf's TextStreamAppearance at the
  size check() planned: the field's /V and /Q are set to that
  widget's own value and alignment just before it is built, since
  pypdf reads both from a field that siblings share. The field's /V
  is put back right after: the bake builds an appearance from /V for
  any sibling the template left without one, so a value given to one
  widget would print in all of them. The widget's own /DR is deleted
  first, because its /Helv lacks the template's encoding and pypdf
  would print "?" for Ł, ’ or – through it. A comb box whose /MaxLen
  sits on its parent gets it on the widget, so its characters spread
  into their cells.
- A multi-line box's first line is lowered by twice its margin: pypdf
  hangs it from the font's top at the box's height plus the margin,
  which cut off the mark on a capital such as Å. check() already
  leaves that room.
- A box gets its state in /AS and /V, as before, so the template's own
  check mark prints.
- The print buttons and the second widget of each stacked pair are
  removed. PyMuPDF bakes every other widget into its page and
  /AcroForm is set to null. An unfilled widget prints as the blank
  form shows it. /NeedAppearances is never set.
- A template with no /AcroForm is still TemplateHasNoForm, now checked
  before check() runs.

Generate, Generate All and Download still draw, so a letter the form
can't print or a value too long even at 6 pt now reaches the filer as
check()'s 422 with its step or page, instead of "?" or a cut-off value.

The tests read the printed page instead of /V. read_drawn
(apps/forms/tests/pdf_readback.py) takes, for every widget, the
Helvetica text and the template's ZapfDingbats check mark whose centre
lies inside the widget's index rect: two pairs of check boxes overlap
by about 2 pt, and a glyph merely touching a rect would put the
neighbour's tick in it. What the blank template itself prints in a box
(the district combo's placeholder, a page number, A/B's "0%") never
reads as a value. read_widgets and FilledWidget are gone.

Tiers 1 and 3, test_pdf_filler, the download tests, the DIG-155
download read-back and each per-form schema test now read the drawn
page and keep what they proved. A name's widgets no longer share what
they print, so tiers 1 and 3 check every drawn widget of a name: tier
1's sentinel must print in each, and so must tier 3's expected text,
a blank widget failing. Tier
1 gives five Form 101 state boxes two-letter sentinels, since "Q001"
is longer than their MaxLen, and each district combo a real district:
its first options are blank and the template's own placeholder. The
DIG-155 test checks every widget of each name. Form 101's and 107's
page-header tests read each page.

New tests: a value given to one widget prints only there (Form 107's
page-1 header, Schedule I's "Time employed", Schedule D's account
number); a name with Ł and ’ prints in A/B's headers and in bound
boxes of 122A-2, C and D that carry their own /DR; Schedule I's two
"Assistance 8f" and A/B's two "24.1" boxes print their own values; a
shrunk email prints at its planned size; a multi-line box's first line
starts inside the box; a tick in either of two overlapping boxes reads
back only in its own; a blank form reads back blank; one fill() logs
none of the filer's text; and a Form 121 download for a filer whose
name the form can't print is a 422 naming the letter, the box and the
step that fixes it, with nothing logged.

PyMuPDF is pinned at 1.27.2.3, and test_pdf_filler pins it beside
pypdf, with pypdf's PdfWriter._add_object. The umbrella spec's method
bullets and SPIKE row point to the 3a2 spec's section 3. CLAUDE.md's
PDF line, File Map line and its tier and tag gotchas describe the
drawing, the tier gotcha says a box's own template default reads
blank, and its packet and completed-intake gotchas name the two new
refusals.
MSG
git status --short
```

### Task 4: Every widget, and what the printed page shows

_Built and verified as commit `2aaf4b8` on `plan/forms-step3a2`._

**Files:**

- Create: `backend/apps/forms/tests/test_printed_page.py`
- Modify: `CLAUDE.md`
- Modify: `backend/apps/forms/tests/pdf_readback.py`
- Modify: `backend/apps/forms/tests/test_known_defects.py`
- Modify: `backend/apps/forms/tests/test_oracle_tier1.py`
- Modify: `backend/apps/forms/tests/test_signing_lines.py`

**Interfaces:**

- Consumes:
  - From Task 1, `backend/apps/forms/services/widgets.py`:
    - `TemplateWidget`. The tests read its `full_name`, `page`, `tag`, `rect`, `width`, `height`, `kind`, `drawn`, `stacked`, `states`, `font`, `size`, `align`, `comb`, `multiline`, `max_len`, `margin` and `key`.
    - `template_widgets(template_filename: str) -> tuple[TemplateWidget, ...]` (ordered by page, then tag number).
    - `widget_for(template_filename: str, page: int, annotation: DictionaryObject, page_top: float) -> TemplateWidget` and `field_of(annotation: DictionaryObject) -> DictionaryObject`.
  - From Task 2:
    - `PDFFormFiller.check(self, form_type: str, values: dict) -> tuple[PlannedPart, ...]` (`backend/apps/forms/services/pdf_filler.py`). It returns one part, whose `widgets` are `Planned(widget, value, size)`. A widget's own key, `"<full name>@<page>:<tag>"`, wins over its full name on that widget.
    - `UnprintableLetter` and `ValueTooLong`, from the same module.
    - `font_for(template_filename: str, font_name: str) -> Font` (`backend/apps/forms/services/text_fit.py`). The cut-off test reads the font's `font_descriptor.ascent` and `font_descriptor.bbox`.
  - From Task 3:
    - `PDFFormFiller.fill(self, form_type: str, values: dict) -> bytes`.
    - `read_drawn(form_type: str, pdf_bytes: bytes) -> list[DrawnWidget]` and `DrawnWidget` (`full_name`, `page`, `tag`, `value`, `state`), in `backend/apps/forms/tests/pdf_readback.py`.
    - In `test_oracle_tier1.py`: `TIER`, `_SHORT`, `_fits(form_type, pdf_field, value)` (false only on `ValueTooLong`), `_option(form_type, pdf_field)` and `_drawn(form_type, values)` (`fill()`, then `read_drawn`, keeping drawn widgets only). `_text_fill` and `_box_fill` stay `@cache`d by form type.
  - `case_param(form_type, pdf_field, tier, case, *values)` and `DEFECT_CLASSES` (`backend/apps/forms/tests/oracle.py`). A listed case is a strict xfail with `raises=AssertionError`, and tier 1's defect classes are `no_widget`, `collision`, `spill` and `unmapped_choice`.
  - `get_all_form_types()`, `packet(session)` and `build_field_values(form_type, session)` (`apps.forms.registry`); `load_schema(form_type).template_filename`; `PERSONAS` and the `seed_demo_data` command (`apps/intake/management/commands/seed_demo_data.py`); `District` and `IntakeSession`.
  - pypdf 6.13.1: `PdfReader`, `PdfWriter(clone_from=...)`, `NullObject`, and the pinned internals `TextStreamAppearance.from_text_annotation(writer, page, False, acro_form, field, annotation)` and `PdfWriter._add_object(obj)` (G12).
  - PyMuPDF 1.27.2.3: `Page.first_widget`, `Document.bake(annots=False, widgets=True)`, `Document.page_count`, `Page.get_text("rawdict")`, `Page.get_pixmap(dpi=..., clip=..., colorspace=pymupdf.csGRAY)`, and `pymupdf.TOOLS.show_aa_level()`, `set_aa_level(level)`, `mupdf_warnings()` and `reset_mupdf_warnings()`.
- Produces:
  - `read_drawn` raises `ValueError("the PDF still has widgets on pages [...]: it was never baked")` when any page of the PDF still has a widget (R49). Its signature doesn't change; Task 6 adds `parts`.
  - In `backend/apps/forms/tests/test_oracle_tier1.py`:
    - `_TEXT_KINDS = ("Text", "ComboBox")`, `_BOX_KINDS = ("CheckBox", "RadioButton")` and `_shared_names(form_type, kinds) -> dict[str, list[TemplateWidget]]`: each full name that more than one drawn widget of those kinds shares, with those widgets in page and tag order.
    - `_widget_fill(form_type) -> tuple[dict[str, str], list[DrawnWidget]]` and `_widget_box_fill(form_type, k) -> list[DrawnWidget]`, both `@cache`d by their arguments.
    - `_option(form_type, pdf_field, nth=0)`: the nth option that prints and fits.
    - `WIDGET_TEXT_CASES` (73 cases), `WIDGET_BOX_CASES` (230) and `WIDGET_CASES`, their sum, each with case key `"each_widget"`.
    - The tests `test_each_widget_of_a_shared_name_prints_its_own_value` (73) and `test_each_widget_of_a_shared_box_name_ticks_alone` (230).
  - `ORACLE_CASES["1"]` in `test_known_defects.py` includes `WIDGET_CASES`.
  - `backend/apps/forms/tests/test_printed_page.py` (new), 94 cases: `test_no_persona_is_refused` (6), `test_the_packet_has_no_fillable_fields_left` (17), `test_print_buttons_never_print` (17), `test_unticked_boxes_keep_their_squares`, `test_a_stacked_duplicate_prints_once`, `test_amounts_stay_right_aligned` (11), `test_ssn_digits_fill_their_cells`, `test_every_drawn_pdf_opens_cleanly` (17), `test_r38s_cedilla_tolerance_covers_only_its_37_boxes`, `test_no_value_is_ever_cut_off` (17), `test_a_capitals_mark_survives_the_first_line` (4) and `test_check_agrees_with_the_drawing_on_every_letter`.
  - `_printed()` in `test_signing_lines.py` maps (form type, full name) to the texts of every drawn widget of that name, `""` included.
  - No production code changes, and no name in tasks.md's Interfaces table moves.

**Decisions already made in this task:**

_Scope:_

- **The commit changes test files and one `CLAUDE.md` sentence, no production code.** Every new test passes on the parent commit's code, so no test can be red before the change. Steps 2 to 6 show each new test red instead by breaking Task 2's or Task 3's code (G4's "mutate the change and restore"): each block applies a mutation with `git apply`, runs the tests it must break, and restores the file through a `trap` when the block ends, pass or fail. Every mutation here comes from the implementer's or the reviewers' runs.
- **Where the commit goes beyond tasks.md's T4 list,** each accepted at review:
  - `test_r38s_cedilla_tolerance_covers_only_its_37_boxes`, a guard on the cut-off test's one tolerance;
  - the cut-off test's second draw, a short value at each box's own size;
  - the cut-off test leaves out the 18 combo boxes, which take only their own options and so have no boundary to probe.
- **No `Refs DIG-…` line.** The commit closes no filed ticket, as in Tasks 1 to 3.
- **Counts checked for this plan.** A script run on this task's tree with the tests' own helpers found every count below that no step prints: 73 text and combo names (229 widgets) and 230 box names (566 widgets, 55 draws), 37 hanging boxes, 547 right-aligned boxes on 11 forms, 2,052 drawn text boxes in 1,236 layouts, 18 combos, 67 buttons, 103B's 41 checkboxes, and 365 letters on 288 boxes, 215 accepted and 150 refused. Counts from a probe or a mutation run say whose they are.

_Tier 1's engine check (spec §8, R50):_

- **It covers every full name that more than one drawn widget shares,** text, combo and box alike. Stacked and unprinted widgets don't count. tasks.md's first T4 text, "the spike counted 74", read as text and combo names only; the review found spec §8 says "every widget of every shared full name", and R50 added the boxes.
  - The spike's 74 is the 73 text and combo names below plus Schedule D's `4_3`, whose only sibling is its stacked second widget (the implementer's `probe_counts.py`).
- **Text and combo names: 73 names, 229 widgets, one draw per form** (`_widget_fill`). Each widget gets its own sentinel through its own key: `W000`, `W001`, … numbered across the form, or the next unused `_SHORT` code where `W###` doesn't fit. The one shared combo name, 103B's `Bankruptcy District Information`, gets a different district in each widget (`_option(..., nth=k)`). Each widget must print its own sentinel: `no_widget:` when it prints nothing, `collision:` when it prints another's.
- **Box names: 230 names, 566 widgets, 55 draws** (`_widget_box_fill(form_type, k)`), and every widget ticks alone.
  - **Why rounds, not sentinels.** A box can't carry a value of its own. It prints its on-state's check mark, the same ZapfDingbats glyph in every widget, so "its own sentinel" means nothing for a box. Each widget is ticked alone instead.
  - Round `k` ticks the `k`-th drawn widget of every shared box name on the form, through its own key with its first on-state, in one draw. That widget must read its on-state (`no_widget:` otherwise) and every sibling `/Off` (`collision:` otherwise). A name runs only the rounds it has widgets for.
  - A form needs as many rounds as its largest shared box name has widgets: Form 101 12 (`Check Box22`), Form 107 5, A/B 4 (one of its names is a radio button), D 4, E/F 4, 122A-1Supp 4, 122A-1 3, 122A-2 3, each other form 2, and Form 121 0.
  - A name's case stops at its first failing round, so it reports only that round (re-review, accepted).
- **The tagged-key mutation reaches only 3 of the 230 box names; the first-widget mutation reaches all 230** (Step 3).
  - Under "a tagged key fills every widget of its name", only Form 101's `Check Box1`, Form 107's `check3` and Schedule D's `check 5` go red. In the other 227 names each widget has an on-state of its own: they are the options of one question, such as Form 101's `/Chapter 7` and `/Chapter 11`. A key that reaches every widget of such a name still ticks only the widget whose states hold the value and plans the rest `/Off`, so a tagged key and a full-name key draw the same page. Routing by tag shows only where siblings share an on-state, and those are the 3 names. This is the templates, not a weak test.
  - Under "a box's tick lands on its name's first widget, whatever the tag", all 230 go red.
  - The same tagged-key mutation turns all 73 text and combo names red.
- **One case per name, case key `each_widget`,** so `known_defects.json` can list one name. The failure prefixes `no_widget` and `collision` are already tier 1's defect classes. `WIDGET_CASES` joins `ORACLE_CASES["1"]` in `test_known_defects.py`, so an entry keyed on an engine case isn't an orphan.
- **The engine check can't see R42** (the field's `/V` put back after each widget is built). Every sibling gets its own appearance in these draws, so the bake never builds one from `/V`.
  - The reviewer's `probe_r42.py`: of the 19 text or combo names with a `/V` in the template, the only shared one (103B's district) has `/AP` on both widgets, so only the restore's "had no `/V`" branch can show on a page.
  - Task 3's `test_a_tagged_value_prints_only_in_its_own_box` shows that branch on 3 of the 66 shared fields with a widget lacking `/AP`, and went red 3 of 3 with the restore removed. R50 adds no text rounds for it: the spec doesn't ask, and that is as far as the templates allow.
- **Tier 1's caches stay keyed by form type (R48).** `_widget_fill` and `_widget_box_fill` are `@cache`d like `_text_fill` and `_box_fill`, the file's convention since before 3a2. G11 was reworded to say so: it covers caches of template data. The 17 form types name 17 distinct templates, and no tier 1 draw is computed under `schema_copy`, so a synthetic schema can't poison one.

_`read_drawn` proves the bake (R49):_

- **It raises a `ValueError` naming the pages when any page still has a widget** (`page.first_widget`). MuPDF's text extraction reads an unbaked widget's appearance as text, so before this every read-back test, tiers 1 and 3 among them, could pass on a PDF that was never baked.
  - Under "no bake" (Step 2), Task 3's tagged test and tier 3's `form_101:Debtor1.First name:maria` went from `4 passed` on the unbaked PDF without the refusal to 4 `ValueError`s with it (the implementer's fix-round run).
- **Why it raises, not asserts.** `case_param` makes a listed defect a strict xfail with `raises=AssertionError`. A failed assertion about a missing bake would pass as that listed defect; a `ValueError` fails the case.
- **It doesn't also require a null `/AcroForm`.** The letter test's refused half reads `_drawn_without_check` output, a raw PyMuPDF bake, which leaves no `/AcroForm` at all (absent, not null). An unbaked PDF with `/AcroForm` set to null still has 606 widgets that `page.first_widget` finds (the reviewer's `probe_bake_state.py`).
- **Every caller passes `fill()` output, or a download's content, which is `fill()` output** (reviewer's grep, about 20 test modules), so the refusal breaks none.
- `_widget_fill` first asserted the bake itself; that assertion and its `pymupdf` import went once `read_drawn` refuses.
- **The page tests open the drawn PDF through their own `_printed(pdf)`,** which asserts no page has a widget, because several read the page with PyMuPDF directly, not through `read_drawn`. No xfail wraps a page test, so a plain assertion is right there.

_The page tests (spec §9, `test_printed_page.py`):_

- **Each "Red with …" below is a mutation the implementer or a reviewer ran on the built code and restored** (the implementer's `t04/mutate.py`, `t04/mutate_drawing.py` and `t04/mutate_fix1.py`). Steps 2 to 6 repeat six of them.
- **"Every form" means each of the 17 drawn with the first persona whose packet holds it** (`_values`): Maria's 103B, Priya's 122A-2. Form 122A-1Supp is in no packet until step 4, so it takes the first persona's (Maria's).
  - `_seeded()` seeds the six personas once, as tier 3 does (`seed_demo_data --reset`), and keeps each packet and every form's values as plain data, since the rows roll back after the test that seeds them. `_drawn_packet()` draws the 17 once. Both take no argument; `_rects` is keyed by template filename (G11).
  - `seed_demo_data` reads `fill_date()`, which the tests pin to 2026-10-16 (G13), so the seeding has no date bomb (reviewer).
- **`test_no_persona_is_refused`:** each of the six seeded packets passes `check()` (spec §4.3). Red with "`check()` never shrinks below a box's own size": 5 of 6, since Sarah's packet holds no value that needs a smaller size.
- **`test_the_packet_has_no_fillable_fields_left`** reads the root's `/AcroForm` directly and requires a `NullObject`, since pypdf's own `get_fields()` can't read a null `/AcroForm`; then no page may have a `/Widget`.
- **`test_print_buttons_never_print`** asserts that nothing in any font prints inside a button's rect. The labels are Helvetica-Bold, which `read_drawn` ignores. The test first bakes the template as it stands and finds every label printed, so it knows where the labels would be. The templates have 67 buttons.
- **`test_unticked_boxes_keep_their_squares`** compares each of 103B's unticked boxes (Maria's application ticks 2 of its 41 checkboxes, so 39 are compared, the implementer's count) with the blank template: the same count of dark pixels (grey below 128) at 288 dpi.
  - **Anti-aliasing is off** while it counts (`_no_anti_aliasing`, which restores the level in `finally`). At 288 dpi with MuPDF's default anti-aliasing, 103B's `Check 7@2:T4` loses 8 edge pixels when another box on its page is drawn, though `get_drawings()` in its rect is identical (the implementer's `probe_103b_extra.py`). With it off, every unticked box matches the blank form at 288 and 1440 dpi, for Maria, DeShawn and Sarah and for an empty draw (the implementer's `probe_measure.py`).
- **`test_a_stacked_duplicate_prints_once`** draws Schedule D page 2's `4_3` as "Okafor" and ticks `Contingent_3`, then reads the union of each pair's rects: "Okafor" once, one check mark. Red when `TemplateWidget.drawn` ignores `stacked` ("OkaforOkafor").
  - Removing the stacked seconds from `/Annots` is a second guard, not the one this test sees: kept but never planned, they print nothing (page 2's pixels around all 8 pairs are identical with and without them, the implementer's `probe_stacked_pixels.py`). What keeps a value single is `check()` leaving stacked widgets out of the plan.
- **`test_amounts_stay_right_aligned`** covers every drawn right-aligned text box (`align == 2`), 547 on 11 forms. Each gets the first of "1,234.56", "12.00" and "9" that fits, and its last character must end within 1 pt of the right padding (the rect's right edge less 2 × margin, where pypdf puts it).
  - A/B's three widget-only `/Q` boxes, `24.2 Interest in an education IRA@7:T8`, `undefined_166@10:T34` and `undefined_166@10:T35`, must be in the set (R26, R45). Red with R26 off: A/B's `24.2` starts at the left padding.
- **`test_ssn_digits_fill_their_cells`** draws Form 121's `Debtor1a.SSNum@1:T9` with a seeded persona's SSN as the resolver formats it (11 characters, 900 range, the box's `max_len` 11), and Schedule D's `account number@1:T32` and `@3:T33` with "4417" and "5521" (R4). Each character must be centred in its own cell within 0.25 pt. Red with R4 off: D's box reads "417".
- **`test_every_drawn_pdf_opens_cleanly`:** each drawn form opens in pypdf and PyMuPDF with the template's page count, and the MuPDF warnings from drawing it and rendering and reading every page are a subset of the template's own.
  - **"No common ancestor in structure tree" comes from the template.** Form 101's template gives it (twice) when its pages render, with no fill; `get_text` alone and a raw bake give none, and the drawn 101 gives the same lines (the implementer's `probe_warn.py`). No other form warns. PyMuPDF prints the line to stdout as "MuPDF error: format error: …" whenever Form 101's pages render.
  - Red with the last page dropped (`8 == 9`) and with an unknown operator added to each appearance (MuPDF: "unknown keyword: 'nope'"). A mutation that made an appearance name a font it lacks stayed green (the implementer's run).
- **`test_no_value_is_ever_cut_off`** covers every drawn text box, 2,052 on 17 forms, in two draws per form:
  - **Draw 1, the boundary.** In each box the longest run of `ÅgÇq` repeated that `check()` fits (in a multi-line box, as many lines of that run as fit) must read back whole and lie inside; one letter or line more must be refused. Boxes alike in every measure `check()` takes (font, size, width, height, margin, comb, multi-line, `max_len`) share one boundary search, 1,236 layouts, but every box is drawn and judged on its own.
  - **Draw 2, a short value at the box's own size:** "ÅgÇq", or "Åg\nÇq" in a multi-line box. The boundary values mostly print at 6 pt, which never reaches R38's bottoms, so this draw makes Task 3's geometry gate permanent. Eleven Schedule G boxes, each 16.32 pt wide, refuse it even at 6 pt and take their boundary value instead: "Å" in the 8 entry-number boxes `fill 2.6` to `fill 2.13`, and "ÅgÇ" in `fill_27.0`, `fill_27.1.0` and `fill_27.1.1`. The test's comment names only the entry-number boxes; a script run on this task's tree for this plan found the other three.
  - **Each glyph is judged by where it sits, not by its text** (R39): MuPDF extracts a partly hidden glyph whole. A glyph's top is origin − 0.931 × size and its bottom origin + 0.225 × size (Helvetica's bounding box), and its left and right come from its bbox. A glyph belongs to the box whose rect holds its centre (R40).
  - **Against the unrounded `/Rect`,** read from the template (`_rects`), not the index rect, which is rounded to 0.1 pt and would eat most of R38's 0.11.
  - **Spaces are skipped.** MuPDF adds a space where one box's text ends and the next begins; one ran 2.36 pt past Form 107 page 1 T20's right edge (the implementer's `probe_107t20b.py`). It is no glyph, and Task 3's gate skipped spaces too.
  - **The tolerance is 0.001 pt on every side (MuPDF's rounding), plus 0.11 pt at the bottom for R38's 37 boxes.** Those boxes are rebuilt from pypdf's centring (`_hangs_below`: baseline = margin + (height − 2 × margin − ascent × size / 1000) / 2, and the cedilla's bottom is the baseline less 0.225 × size). They are single-line boxes at their own size where Ç's cedilla dips up to 0.108 pt below the rect: 11 boxes 13.8 pt high at 12 pt (Form 101's `Debtor1.Name` on pages 2–9, `Attorney.Sig` on page 8 and `Case number1` on page 2, and Form 121's `Case number1`) and 26 at 10 pt, 11.52–11.64 pt high, on C, 103B, A/B and D, none bound (R38). The ruling stands: a hairline of one cedilla, invisible, printed the same before 3a2.
  - `test_r38s_cedilla_tolerance_covers_only_its_37_boxes` pins that count, so the allowance can't grow with a template or pypdf change. Red when every box's `/DA` size reads a point larger: 130 boxes hang.
  - **The boundary search stops at 1,024 (`assert high < 1024` in `_longest`).** `_longest` doubles `high` while `check()` fits the value, then bisects. If `check()` were broken so that it fits any length, the doubling would never end: each round builds a string twice as long and calls `check()` again. One such run, the implementer's first try of "a value too long at 6 pt is drawn anyway", went 9 hours. With the bound, the same breakage is red in seconds (Step 5). No working box holds 1,024 letters or lines even at 6 pt, so the bound never fires on a sound `check()`. The bisection, `_six_point_value` (`n < 200`) and the letter test's rounds are all bounded (reviewer).
  - **The search goes through `check()`, never `fit()` directly:** spec §9 says "by `check()`" (reviewer).
  - Red with the width rule loosened to the whole rect (121, J: past the right edge), the multi-line height rule loosened (103B, A/B: past the bottom), a too-long value drawn anyway (121, J: the bound), and R35 off (the 8 forms with a multi-line box: past the top).
- **`test_a_capitals_mark_survives_the_first_line` measures pixels, because text can't see the cut.** MuPDF reads É on line 1 whole even when the box hides its accent. On A/B line 53 (`53 Examples Season tickets country club membership`) and 103B's `3 type`, at the box's own size ("ÉÑŠ\nÉÑŠ") and at 6 pt, each mark's ink on line 1 must be at least 0.8 of the same letter's on line 2 (R35).
  - A mark's ink is what the drawing adds over the same page drawn empty, rendered grey at 1440 dpi, in the band 0.735 to 0.95 em above the baseline: clear of the cap height (0.718), up to past the font's top.
  - The 6 pt value is "ÉÑŠ" followed by as many x's as make one word just too wide at 6.5 pt (`_six_point_value`). Lines alone can't force 6.0 on either box. The test asserts `check()` plans each value at the size it names.
  - The implementer measured 0.865–1.039 with R35, at most 0.31 without; rendered at different heights, the same mark varies by up to 14%. Red with R35 off (all 4) and with the first line lowered by one margin only (103B at 6 pt: Ñ 0.323).
- **`test_check_agrees_with_the_drawing_on_every_letter`** tries 365 characters: U+0020–U+017F (U+00A0 and U+00AD among them), `’ ‘ “ ” – — … € •`, U+2009, U+202F, U+200B and a tab, each as "x<letter>x" in Form 107's single-line, unshared, uncombed boxes with no `max_len`, as many per draw as there are boxes.
  - **One form stands for all 17:** the test asserts that every template's `/Helv` has the same `/Encoding`.
  - **An accepted letter** must read back as it prints (a tab, a space separator or a line break as a space; a format character as nothing, R36) and, if it prints a glyph, leave ink alone in its box.
  - **A refused letter** is drawn without `check()` (`_drawn_without_check`: a clone, the widget's `/DR` removed as `fill()` removes it, pypdf's appearance at the box's own size, a raw PyMuPDF bake), not by patching `check()`'s private helpers. It must read back as something else, or leave no ink. `check()` accepts 215 of the 365 and refuses 150. Drawn without `check()`, the implementer found that 118 of the refused print "?", 30 another glyph (C1 bytes hit the encoding's `/Differences` glyphs, such as •, † and …), and U+007F and U+009F read back as themselves but leave no ink.
  - **No tab, space separator or format character may be refused** (R36). Two mutations stayed green at first and shaped this: "a no-break space kept as itself" made `check()` refuse U+00A0, consistent with the drawing but against R36, and "control characters let through" made U+007F and U+009F read back as themselves while drawing nothing. So the test asserts the R36 set is never refused and judges every accepted glyph by its ink as well as its text.
  - Red with every letter printable (ą and kin read "x?x") and with é refused (it draws as itself, with ink).

_`test_signing_lines.py` (R44):_

- **`_printed()` keeps every drawn widget's text, `""` included,** so a signing line must read `{""}` and each neighbour `{value}`: a name blank on one of its widgets fails. Task 3 left it reading only non-empty values, which stayed green under the draw-once mutation (Task 3's note). Red with "draw only the first widget of each shared text name": 4 cases, since 122A-1 and 122A-2 then print Priya's name in the first `Debtor1.Name` widget only (Step 4).
- It reads through `read_drawn`, so since R49 a missing bake fails it too (Step 2). Before R49 it stayed green under "no bake", since an unbaked copy prints the same text.

_Docs:_

- **`CLAUDE.md`'s "Known form defects are strict xfails"** gains: "`read_drawn` refuses a PDF that still has a widget (a `ValueError`, never a listed defect), so it reads only `fill()`'s baked output." The next sentence's "It has been empty" becomes "The list has been empty", since "It" would now point at `read_drawn`.

_Left as found, and notes for later tasks:_

- **Suite time.** The gated backend suite went from 670.8 s (the first round) to 815.6 s (the fix round, under the controller's timing probe's load). The box rounds cost about 55 s, about 1 s per draw, and the cut-off test is most of `test_printed_page.py`.
  - The reviewer's profile of Form 107's cut-off case: `check()` calls cost the most, and pypdf rebuilds `Font._get_typographic_maps()` on every `text_fit.wrap()` call (32,800 calls). One `fill()` of 107 takes 1.11 s, 60% of it `PdfWriter(clone_from=path)` parsing the template again.
  - Re-measured without coverage (ledger): 51.1 s as it stands, 33.5 s with the maps built once per font, 15.3 s with the template parsed once too. The rows under coverage, 73.1, 77.1 and 76.6 s, are unreliable, since the load changed between runs.
  - R51 gives the speed work to Task 5, measured there on a quiet machine. Parked minors: `_cut_off` filters every glyph of the page for each widget (1.8 s of 54 s profiled), and `_seeded()` resolves all 17 forms for each persona.
- **Three backend files fail `black --check`:** `apps/documents/apps.py`, `apps/users/serializers.py` and `manage.py`. This branch hasn't changed them since its base, and they fail there too. Black runs only in pre-commit, never in CI or `gates.sh`. A ticket candidate.
- **A killed mutation run can leave a file mutated.** The implementer's first run, killed in the background, left `text_fit.py` holding a mutation, and its pytest child kept running with it. That is why each mutation block below restores its file through a `trap`.

- [ ] **Step 1: Write the tests**

```python file=backend/apps/forms/tests/test_printed_page.py
"""
What the printed page shows (3a2 spec §9).

fill() builds each widget's value with pypdf and PyMuPDF bakes it into the page, so the
filer gets a page, not a form to fill. These tests look at that page: what prints in each
box, where each character sits, and, where text can't tell, its pixels. MuPDF extracts a
character whole even when the box hides part of it, so a cut is judged from where the
character sits (its origin and size, against Helvetica's bounding box), not from text.
"""

import unicodedata
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from io import BytesIO
from pathlib import Path

import pymupdf
import pypdf
import pytest
from django.conf import settings
from django.core.management import call_command
from pypdf.generic import DictionaryObject, NameObject, NullObject, TextStringObject
from pypdf.generic._appearance_stream import TextStreamAppearance

from apps.districts.models import District
from apps.forms.registry import build_field_values, get_all_form_types, packet
from apps.forms.schema import load_schema
from apps.forms.services.pdf_filler import PDFFormFiller, UnprintableLetter, ValueTooLong
from apps.forms.services.text_fit import font_for
from apps.forms.services.widgets import field_of, template_widgets, widget_for
from apps.forms.tests.pdf_readback import read_drawn
from apps.intake.management.commands.seed_demo_data import PERSONAS
from apps.intake.models import IntakeSession

# Helvetica's bounding box per point of size: a glyph's highest point (Å's ring) sits
# 0.931 above its baseline and its lowest (Ç's cedilla) 0.225 below.
_TOP = 0.931
_BOTTOM = 0.225
_BOXES = ("CheckBox", "RadioButton")


def _template(form_type):
    return load_schema(form_type).template_filename


def _template_path(form_type):
    return Path(settings.PDF_FORMS_DIRECTORY) / _template(form_type)


@dataclass(frozen=True)
class _Glyph:
    text: str
    font: str
    bbox: tuple[float, float, float, float]
    origin: tuple[float, float]
    size: float

    def inside(self, rect):
        """The glyph's centre lies inside rect: a glyph only touching it belongs to a neighbour."""
        x, y = (self.bbox[0] + self.bbox[2]) / 2, (self.bbox[1] + self.bbox[3]) / 2
        return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


def _printed(pdf):
    """
    The drawn PDF, opened once no widget is left on any of its pages. MuPDF reads a
    widget's appearance on a page never baked too, so without this a test could read a
    value from a widget a viewer can still change, not from the printed page.
    """
    document = pymupdf.open("pdf", pdf)
    assert [page.number + 1 for page in document if page.first_widget] == []
    return document


def _glyphs(page):
    """Every character on the page, in any font, as MuPDF extracts it."""
    return [
        _Glyph(char["c"], span["font"], char["bbox"], char["origin"], span["size"])
        for block in page.get_text("rawdict")["blocks"]
        for line in block.get("lines", [])
        for span in line["spans"]
        for char in span["chars"]
    ]


# ── The personas' packets ─────────────────────────────────────────────


@cache
def _seeded():
    """
    persona → (the form types in its packet, every form's values for it), each persona
    seeded as tier 3 seeds it. Kept as plain data: the rows go when the test that
    seeds them ends.
    """
    if not District.objects.filter(code="ilnd").exists():
        call_command("loaddata", "ilnd_2025_data", verbosity=0)
    seeded = {}
    for persona in PERSONAS:
        call_command("seed_demo_data", "--reset", persona=persona, verbosity=0)
        session = IntakeSession.objects.filter(user__username=f"demo_{persona}").latest("id")
        seeded[persona] = (
            packet(session),
            {
                form_type: build_field_values(form_type, session)
                for form_type in get_all_form_types()
            },
        )
    return seeded


def _values(form_type):
    """
    The form's values for the first persona whose packet holds it: Maria's 103B, Priya's
    122A-2. Form 122A-1Supp is in no packet until step 4, so it takes the first persona's.
    """
    seeded = _seeded()
    first = next(iter(seeded))
    persona = next((p for p, (forms, _) in seeded.items() if form_type in forms), first)
    return seeded[persona][1][form_type]


@cache
def _drawn_packet():
    """form_type → the form drawn with its _values()."""
    return {
        form_type: PDFFormFiller().fill(form_type, _values(form_type))
        for form_type in get_all_form_types()
    }


@pytest.mark.django_db
@pytest.mark.parametrize("persona", list(PERSONAS))
def test_no_persona_is_refused(persona):
    # None of the personas' values holds a letter the forms can't print or one too long
    # even at 6 pt (spec §4.3), so check() lets every form of each packet through.
    forms, values = _seeded()[persona]
    refused = {}
    for form_type in forms:
        try:
            PDFFormFiller().check(form_type, values[form_type])
        except (UnprintableLetter, ValueTooLong) as exc:
            refused[form_type] = str(exc)
    assert refused == {}


@pytest.mark.django_db
@pytest.mark.parametrize("form_type", get_all_form_types())
def test_the_packet_has_no_fillable_fields_left(form_type):
    # Every value is page content now: a viewer can't change what DigniFi printed, and a
    # correction goes through a regeneration.
    assert template_widgets(_template(form_type))
    reader = pypdf.PdfReader(BytesIO(_drawn_packet()[form_type]))
    # pypdf's own get_fields() can't read a null /AcroForm, so the root is read directly.
    assert isinstance(reader.trailer["/Root"]["/AcroForm"], NullObject)
    widgets = [
        annot
        for page in reader.pages
        for annot in page.get("/Annots") or []
        if annot.get_object().get("/Subtype") == "/Widget"
    ]
    assert widgets == []


@pytest.mark.django_db
@pytest.mark.parametrize("form_type", get_all_form_types())
def test_print_buttons_never_print(form_type):
    # The Print, Save As, Add Attachment and Reset buttons are for a screen. Baked as the
    # template stands they print their labels; the drawn form prints nothing there.
    buttons = [w for w in template_widgets(_template(form_type)) if w.kind == "Button"]
    as_it_stands = pymupdf.open(_template_path(form_type))
    as_it_stands.bake(annots=False, widgets=True)
    labels = {
        w.key: "".join(g.text for g in _glyphs(as_it_stands[w.page - 1]) if g.inside(w.rect))
        for w in buttons
    }
    assert buttons and all(label.strip() for label in labels.values()), labels
    drawn = _printed(_drawn_packet()[form_type])
    printed = {
        w.key: "".join(g.text for g in _glyphs(drawn[w.page - 1]) if g.inside(w.rect))
        for w in buttons
    }
    assert printed == {w.key: "" for w in buttons}


@contextmanager
def _no_anti_aliasing():
    """
    Render without anti-aliasing: it shades edge pixels differently from one page to the
    next, even where the drawings are the same.
    """
    level = pymupdf.TOOLS.show_aa_level()["graphics"]
    pymupdf.TOOLS.set_aa_level(0)
    try:
        yield
    finally:
        pymupdf.TOOLS.set_aa_level(level)


def _dark_pixels(page, rect):
    pix = page.get_pixmap(dpi=288, clip=pymupdf.Rect(rect), colorspace=pymupdf.csGRAY)
    return sum(1 for value in pix.samples if value < 128)


def _pixels(document, widget):
    """The widget's rect on its page, rendered."""
    return document[widget.page - 1].get_pixmap(dpi=288, clip=pymupdf.Rect(widget.rect)).samples


@pytest.mark.django_db
def test_unticked_boxes_keep_their_squares():
    # Form 103B's empty squares are its boxes' own appearances, so an unticked box must
    # bake as the blank form shows it, or the filer has nothing to tick by hand.
    pdf = _drawn_packet()["form_103b"]  # Maria's fee-waiver application
    ticked = {(w.page, w.tag) for w in read_drawn("form_103b", pdf) if w.state not in ("", "/Off")}
    unticked = [
        w
        for w in template_widgets(_template("form_103b"))
        if w.kind in _BOXES and w.drawn and (w.page, w.tag) not in ticked
    ]
    assert ticked and unticked
    blank = pymupdf.open(_template_path("form_103b"))
    drawn = _printed(pdf)
    with _no_anti_aliasing():
        counts = {
            w.key: (
                _dark_pixels(blank[w.page - 1], w.rect),
                _dark_pixels(drawn[w.page - 1], w.rect),
            )
            for w in unticked
        }
    assert all(on_blank for on_blank, _ in counts.values()), counts
    assert {key: n for key, n in counts.items() if n[0] != n[1]} == {}


def test_a_stacked_duplicate_prints_once():
    # Schedule D page 2 lays a second widget over 4_3 and over each _3 checkbox, 0.6 pt
    # off. Drawn in both, a value would print twice, one copy smudging the other.
    pairs = {
        name: [w for w in template_widgets(_template("schedule_d")) if w.full_name == name]
        for name in ("4_3", "Contingent_3")
    }
    assert all(len(pair) == 2 and pair[1].stacked for pair in pairs.values())
    page = _printed(PDFFormFiller().fill("schedule_d", {"4_3": "Okafor", "Contingent_3": "/On"}))[1]

    def union(pair):
        """The rect the two widgets cover between them."""
        return (
            min(w.rect[0] for w in pair),
            min(w.rect[1] for w in pair),
            max(w.rect[2] for w in pair),
            max(w.rect[3] for w in pair),
        )

    glyphs = _glyphs(page)
    text = [g.text for g in glyphs if g.font == "Helvetica" and g.inside(union(pairs["4_3"]))]
    ticks = [
        g for g in glyphs if g.font == "ZapfDingbats" and g.inside(union(pairs["Contingent_3"]))
    ]
    assert "".join(text) == "Okafor"
    assert len(ticks) == 1


# A/B's three boxes whose right alignment is set on the widget alone (R26).
_WIDGET_ONLY_ALIGNMENT = {
    "24.2 Interest in an education IRA@7:T8",
    "undefined_166@10:T34",
    "undefined_166@10:T35",
}


def _right_aligned(form_type):
    return [
        w
        for w in template_widgets(_template(form_type))
        if w.drawn and w.kind == "Text" and w.align == 2
    ]


@pytest.mark.parametrize("form_type", [f for f in get_all_form_types() if _right_aligned(f)])
def test_amounts_stay_right_aligned(form_type):
    # An amount's digits line up in the form's column only when each ends at the box's
    # right padding (2 × margin from its right edge, where pypdf puts it).
    boxes = _right_aligned(form_type)
    if form_type == "schedule_a_b":
        assert _WIDGET_ONLY_ALIGNMENT <= {w.key for w in boxes}
    values = {w.key: _first_fitting(form_type, w.key, ["1,234.56", "12.00", "9"]) for w in boxes}
    document = _printed(PDFFormFiller().fill(form_type, values))
    on_page = {}
    off = {}
    for w in boxes:
        if w.page not in on_page:
            on_page[w.page] = _glyphs(document[w.page - 1])
        ends = [
            g.bbox[2]
            for g in on_page[w.page]
            if g.font == "Helvetica" and g.text.strip() and g.inside(w.rect)
        ]
        padding_end = w.rect[2] - 2 * w.margin
        if not ends or abs(max(ends) - padding_end) > 1:
            off[w.key] = (max(ends, default=None), round(padding_end, 2))
    assert off == {}


def _first_fitting(form_type, key, candidates):
    return next(value for value in candidates if _fits(form_type, key, value))


def _fits(form_type, key, value):
    try:
        PDFFormFiller().check(form_type, {key: value})
    except ValueTooLong:
        return False
    return True


@pytest.mark.django_db
def test_ssn_digits_fill_their_cells():
    # A comb box prints one character per cell, each centred in it, as the form's printed
    # cells expect. Schedule D's account boxes carry their cell count on the parent, so
    # the drawing copies it onto each widget (R4); without it the digits pile up.
    ssn = _values("form_121")["Debtor1a.SSNum"]  # the full SSN, as the resolver formats it
    for form_type, key, value in [
        ("form_121", "Debtor1a.SSNum@1:T9", ssn),
        ("schedule_d", "account number@1:T32", "4417"),
        ("schedule_d", "account number@3:T33", "5521"),
    ]:
        (box,) = [w for w in template_widgets(_template(form_type)) if w.key == key]
        assert box.comb and len(value) == box.max_len, key
        page = _printed(PDFFormFiller().fill(form_type, {key: value}))[box.page - 1]
        glyphs = sorted(
            (
                g
                for g in _glyphs(page)
                if g.font == "Helvetica" and g.text.strip() and g.inside(box.rect)
            ),
            key=lambda g: g.bbox[0],
        )
        assert "".join(g.text for g in glyphs) == value, key
        cell = box.width / box.max_len
        off_centre = [
            round((g.bbox[0] + g.bbox[2]) / 2 - (box.rect[0] + (i + 0.5) * cell), 2)
            for i, g in enumerate(glyphs)
        ]
        assert all(abs(offset) <= 0.25 for offset in off_centre), (key, off_centre)


def _warnings_while(action):
    """The lines MuPDF warns or errs with while action runs."""
    pymupdf.TOOLS.reset_mupdf_warnings()
    action()
    warned = pymupdf.TOOLS.mupdf_warnings()
    pymupdf.TOOLS.reset_mupdf_warnings()
    return set(warned.splitlines())


def _view(document):
    """Every page rendered and read, as a viewer or a court's system opens it."""
    for page in document:
        page.get_pixmap(dpi=36)
        page.get_text()


@pytest.mark.django_db
@pytest.mark.parametrize("form_type", get_all_form_types())
def test_every_drawn_pdf_opens_cleanly(form_type):
    # A drawn form must open like the template: every page there, and nothing new for a
    # PDF reader to complain about. (Form 101's template already makes MuPDF say "No
    # common ancestor in structure tree" when its pages render: its tagging, not ours.)
    pages = len(pypdf.PdfReader(_template_path(form_type)).pages)
    from_template = _warnings_while(lambda: _view(pymupdf.open(_template_path(form_type))))
    drawn = []

    def draw_and_view():
        drawn.append(PDFFormFiller().fill(form_type, _values(form_type)))
        _view(pymupdf.open("pdf", drawn[0]))

    from_drawing = _warnings_while(draw_and_view)
    assert len(pypdf.PdfReader(BytesIO(drawn[0])).pages) == pages
    assert _printed(drawn[0]).page_count == pages
    assert from_drawing - from_template == set()


# ── Nothing is cut off ────────────────────────────────────────────────

# Å's ring reaches nearly to the font's top, Ç's cedilla to its bottom, g and q below the
# baseline. No digits: a box's blank text ("2") reads as blank.
_CYCLE = "ÅgÇq"


def _cycled(n):
    return (_CYCLE * n)[:n]


def _longest(form_type, key, value_of):
    """The largest n whose value_of(n) check() fits in the box (0 when none does)."""
    low, high = 0, 1
    while _fits(form_type, key, value_of(high)):
        # No box holds 1,024 letters or lines even at 6 pt.
        assert high < 1024, f"check() fits {key} a value of any length"
        low, high = high, high * 2
    while high - low > 1:
        middle = (low + high) // 2
        if _fits(form_type, key, value_of(middle)):
            low = middle
        else:
            high = middle
    return low


def _boundary(form_type, widget):
    """
    A value that just fits the box, and one that just doesn't, by check(): the longest
    run of letters it fits, one letter more; in a multi-line box, as many lines of that
    run as fit, one line more.
    """
    n = _longest(form_type, widget.key, _cycled)
    if not widget.multiline:
        return _cycled(n), _cycled(n + 1)
    word = _cycled(n)
    lines = _longest(form_type, widget.key, lambda k: "\n".join([word] * k))
    return "\n".join([word] * lines), "\n".join([word] * (lines + 1))


def _hangs_below(template, widget):
    """
    Drawn at its own size, the font's lowest point sits below the box (R38): pypdf
    centres a single-line box's ascent in it, and on 37 boxes Ç's cedilla then dips up to
    0.108 pt under the rect, as it always has.
    """
    if widget.multiline or not widget.size:
        return False
    font = font_for(template, widget.font).font_descriptor
    baseline = (
        widget.margin + (widget.height - 2 * widget.margin - font.ascent * widget.size / 1000) / 2
    )
    return baseline + font.bbox[1] * widget.size / 1000 < 0


@cache
def _rects(template):
    """
    (page, tag) → the widget's /Rect, unrounded, measured from the page's top left: what
    the baked value is clipped to. (The field index rounds rects to 0.1 pt.)
    """
    reader = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template)
    rects = {}
    for number, page in enumerate(reader.pages, start=1):
        top = float(page.mediabox.top)
        for annot in page.get("/Annots") or []:
            annotation = annot.get_object()
            if annotation.get("/Subtype") != "/Widget":
                continue
            widget = widget_for(template, number, annotation, top)
            x0, y0, x1, y1 = (float(v) for v in annotation["/Rect"])
            rects[(number, widget.tag)] = (
                min(x0, x1),
                top - max(y0, y1),
                max(x0, x1),
                top - min(y0, y1),
            )
    return rects


def _cut_off(form_type, values):
    """
    Draw the values and return each box whose value reads back other than whole, or with
    a character past its rect: (key, what read back or the side and points past).
    """
    template = _template(form_type)
    pdf = PDFFormFiller().fill(form_type, values)
    printed = {(w.page, w.tag): w.value for w in read_drawn(form_type, pdf)}
    document = _printed(pdf)
    pages = {}
    cut = []
    for widget in template_widgets(template):
        if widget.key not in values:
            continue
        if printed[(widget.page, widget.tag)] != " ".join(values[widget.key].splitlines()):
            cut.append((widget.key, printed[(widget.page, widget.tag)]))
        rect = _rects(template)[(widget.page, widget.tag)]
        allowed = {"top": 0, "bottom": 0.11 if _hangs_below(template, widget) else 0}
        if widget.page not in pages:
            pages[widget.page] = _glyphs(document[widget.page - 1])
        for g in pages[widget.page]:
            # A space prints nothing; MuPDF also adds one where a line's text breaks off.
            if g.font != "Helvetica" or not g.text.strip() or not g.inside(rect):
                continue
            past = {
                "top": rect[1] - (g.origin[1] - _TOP * g.size),
                "bottom": g.origin[1] + _BOTTOM * g.size - rect[3],
                "left": rect[0] - g.bbox[0],
                "right": g.bbox[2] - rect[2],
            }
            cut += [
                (widget.key, side, round(by, 3))
                for side, by in past.items()
                if by > allowed.get(side, 0) + 0.001  # 0.001 pt: MuPDF's rounding
            ]
    return cut


def test_r38s_cedilla_tolerance_covers_only_its_37_boxes():
    # The cut-off test lets these boxes' bottoms hang 0.11 pt under the rect. Should a
    # template or pypdf change make more boxes hang, the allowance must not grow with them.
    hanging = [
        (form_type, w.key)
        for form_type in get_all_form_types()
        for w in template_widgets(_template(form_type))
        if w.drawn and w.kind == "Text" and _hangs_below(_template(form_type), w)
    ]
    assert len(hanging) == 37, hanging


@pytest.mark.parametrize("form_type", get_all_form_types())
def test_no_value_is_ever_cut_off(form_type):
    # The longest value check() lets through prints whole, every character inside its box,
    # and one letter or line more is refused, never drawn cut off (spec §9). A short value
    # at the box's own size stays inside too: there R38's 37 boxes hang Ç's cedilla up to
    # 0.108 pt under the rect, as the template always has. (Combo boxes take only their
    # own options, so they have no boundary to probe.)
    boxes = [w for w in template_widgets(_template(form_type)) if w.drawn and w.kind == "Text"]
    boundaries = {}  # boxes alike in every measure check() takes share a boundary
    just, over, short = {}, {}, {}
    for w in boxes:
        alike = (w.font, w.size, w.width, w.height, w.margin, w.comb, w.multiline, w.max_len)
        if alike not in boundaries:
            boundaries[alike] = _boundary(form_type, w)
        just[w.key], over[w.key] = boundaries[alike]
        short[w.key] = "Åg\nÇq" if w.multiline else "ÅgÇq"
        if not _fits(form_type, w.key, short[w.key]):  # Schedule G's entry-number boxes
            short[w.key] = just[w.key]
    assert all(just.values()), [key for key, value in just.items() if not value]
    assert [key for key in over if _fits(form_type, key, over[key])] == []
    assert _cut_off(form_type, just) == []
    assert _cut_off(form_type, short) == []


# ── A capital's mark on a multi-line box's first line ─────────────────

OTHER_PROPERTY = "53 Examples Season tickets country club membership"  # A/B line 53
# Where Helvetica's accented capitals carry their marks, per point of size: clear of the
# cap height (0.718) up to past the font's top.
_MARK = (0.735, 0.95)


def _planned_size(form_type, key, value):
    ((planned,),) = [part.widgets for part in PDFFormFiller().check(form_type, {key: value})]
    return planned.size


def _six_point_value(form_type, key):
    """
    É Ñ Š on two lines, line 1 one word just too wide for the box at 6.5 pt, so check()
    plans the value at 6 pt, the smallest print.
    """
    for n in range(1, 200):
        value = f"ÉÑŠ{'x' * n}\nÉÑŠ"
        if _planned_size(form_type, key, value) == 6.0:
            return value
    raise AssertionError(f"no value plans {key} at 6 pt")


def _mark_ink(page, empty, glyph):
    """The ink the drawing adds where the glyph's mark sits, rendered at 1440 dpi."""
    rect = pymupdf.Rect(
        glyph.bbox[0],
        glyph.origin[1] - _MARK[1] * glyph.size,
        glyph.bbox[2],
        glyph.origin[1] - _MARK[0] * glyph.size,
    )
    drawn = page.get_pixmap(dpi=1440, clip=rect, colorspace=pymupdf.csGRAY).samples
    blank = empty.get_pixmap(dpi=1440, clip=rect, colorspace=pymupdf.csGRAY).samples
    return sum(max(b - d, 0) for d, b in zip(drawn, blank, strict=True))


@pytest.mark.parametrize(
    "form_type,key", [("schedule_a_b", OTHER_PROPERTY), ("form_103b", "3 type")]
)
@pytest.mark.parametrize("small", [False, True], ids=["own size", "6 pt"])
def test_a_capitals_mark_survives_the_first_line(form_type, key, small):
    # pypdf hangs a multi-line box's first line from the font's top at the box's height
    # plus its margin, so the box cut off part of É's accent, Ñ's tilde and Š's caron on
    # line 1, nearly all of it at 6 pt (R35). MuPDF still reads the letter whole, so the
    # mark is measured in pixels against the same letter on line 2.
    (box,) = [w for w in template_widgets(_template(form_type)) if w.full_name == key]
    value = _six_point_value(form_type, key) if small else "ÉÑŠ\nÉÑŠ"
    assert _planned_size(form_type, key, value) == (6.0 if small else box.size)
    page = _printed(PDFFormFiller().fill(form_type, {key: value}))[box.page - 1]
    empty = _printed(PDFFormFiller().fill(form_type, {}))[box.page - 1]
    glyphs = [g for g in _glyphs(page) if g.font == "Helvetica" and g.inside(box.rect)]
    for letter in "ÉÑŠ":
        line_1, line_2 = sorted((g for g in glyphs if g.text == letter), key=lambda g: g.origin[1])
        assert line_1.origin[1] < line_2.origin[1]
        ink_1, ink_2 = _mark_ink(page, empty, line_1), _mark_ink(page, empty, line_2)
        assert ink_2 > 0
        # Rendered at different heights, the same mark varies by up to 14% in ink; a cut
        # one keeps a third of it at most.
        assert ink_1 >= 0.8 * ink_2, (letter, round(ink_1 / ink_2, 3))


# ── check() and the drawing agree on every letter ─────────────────────

_LETTERS = list(
    dict.fromkeys(
        [chr(c) for c in range(0x20, 0x180)]
        + list("’‘“”–—…€•")
        + ["\N{NO-BREAK SPACE}", "\N{THIN SPACE}", "\N{NARROW NO-BREAK SPACE}"]
        + ["\N{SOFT HYPHEN}", "\N{ZERO WIDTH SPACE}", "\t"]
    )
)


def _as_printed(letter):
    """What "x<letter>x" prints in a single-line box when check() accepts it."""
    if (
        letter == "\t"
        or unicodedata.category(letter) == "Zs"
        or len(f"x{letter}x".splitlines()) > 1
    ):
        return "x x"  # a space, or a line break, which a single-line box prints as one
    if unicodedata.category(letter) == "Cf":
        return "xx"  # a format character prints nothing
    return f"x{letter}x"


def _encoding(template):
    font = pypdf.PdfReader(Path(settings.PDF_FORMS_DIRECTORY) / template).root_object["/AcroForm"][
        "/DR"
    ]["/Font"]["/Helv"]
    encoding = font.get_object()["/Encoding"].get_object()
    return str(encoding.get("/BaseEncoding")), tuple(
        str(entry) for entry in encoding["/Differences"]
    )


def _drawn_without_check(template, texts):
    """
    The template with each box in texts ((page, tag) → text) built as fill() builds it,
    but never checked: pypdf's appearance at the box's own size, from the template's
    font (R32), baked by PyMuPDF.
    """
    writer = pypdf.PdfWriter(clone_from=str(Path(settings.PDF_FORMS_DIRECTORY) / template))
    acro_form = writer.root_object["/AcroForm"].get_object()
    for number, page in enumerate(writer.pages, start=1):
        for annot in page.get("/Annots") or []:
            annotation = annot.get_object()
            if annotation.get("/Subtype") != "/Widget":
                continue
            widget = widget_for(template, number, annotation, float(page.mediabox.top))
            if (number, widget.tag) not in texts:
                continue
            field = field_of(annotation)
            if "/DR" in annotation:
                del annotation["/DR"]
            field[NameObject("/V")] = TextStringObject(texts[(number, widget.tag)])
            appearance = TextStreamAppearance.from_text_annotation(
                writer, page, False, acro_form, field, annotation
            )
            annotation[NameObject("/AP")] = DictionaryObject(
                {NameObject("/N"): writer._add_object(appearance)}
            )
    buffer = BytesIO()
    writer.write(buffer)
    document = pymupdf.open("pdf", buffer.getvalue())
    document.bake(annots=False, widgets=True)
    return document.tobytes()


def test_check_agrees_with_the_drawing_on_every_letter():
    # check() refuses exactly the letters the drawing can't print (spec §4.3): a letter it
    # accepts prints as itself, and one it refuses would print as "?", as another glyph,
    # or as nothing. MuPDF reads back a character's code even where the font draws
    # nothing for it, so whether a letter prints is judged by its ink too. Every
    # template's text font has the same encoding, so one form's boxes stand for all 17.
    assert len({_encoding(_template(form_type)) for form_type in get_all_form_types()}) == 1
    template = _template("form_107")
    names = Counter(w.full_name for w in template_widgets(template) if w.drawn)
    boxes = [
        w
        for w in template_widgets(template)
        if w.drawn
        and w.kind == "Text"
        and not (w.multiline or w.comb)
        and w.max_len is None
        and names[w.full_name] == 1  # its value can't reach a sibling
    ]
    accepted, refused = [], []
    for letter in _LETTERS:
        try:
            PDFFormFiller().check("form_107", {boxes[0].key: f"x{letter}x"})
            accepted.append(letter)
        except UnprintableLetter:
            refused.append(letter)
    assert accepted and refused
    # A tab and every space separator print as a space, a format character as nothing
    # (R36): none of them is refused.
    invisible = [c for c in refused if c == "\t" or unicodedata.category(c) in ("Zs", "Cf")]
    assert [f"U+{ord(c):04X}" for c in invisible] == []

    def in_boxes(letters):
        """The letters, a box each, in as many rounds as the boxes need."""
        rounds = range(0, len(letters), len(boxes))
        return [list(zip(boxes, letters[i : i + len(boxes)], strict=False)) for i in rounds]

    # Accepted: "x<letter>x" reads back as it prints, and a letter that prints a glyph
    # leaves ink, alone in its box.
    empty = _printed(PDFFormFiller().fill("form_107", {}))
    misprinted, no_ink = {}, []
    for pairs in in_boxes(accepted):
        pdf = PDFFormFiller().fill("form_107", {w.key: f"x{c}x" for w, c in pairs})
        _printed(pdf)
        printed = {(w.page, w.tag): w.value for w in read_drawn("form_107", pdf)}
        misprinted |= {
            f"U+{ord(c):04X}": printed[(w.page, w.tag)]
            for w, c in pairs
            if printed[(w.page, w.tag)] != _as_printed(c)
        }
        glyphs = [(w, c) for w, c in pairs if _as_printed(c) == f"x{c}x" and not c.isspace()]
        alone = _printed(PDFFormFiller().fill("form_107", {w.key: c for w, c in glyphs}))
        with _no_anti_aliasing():
            no_ink += [
                f"U+{ord(c):04X}" for w, c in glyphs if _pixels(alone, w) == _pixels(empty, w)
            ]
    assert misprinted == {}
    assert no_ink == []

    # Refused: "x<letter>x" drawn without check() reads back as something else, or the
    # letter leaves no ink, alone in its box.
    empty = pymupdf.open("pdf", _drawn_without_check(template, {}))
    inked = []
    for pairs in in_boxes(refused):
        pdf = _drawn_without_check(template, {(w.page, w.tag): f"x{c}x" for w, c in pairs})
        printed = {(w.page, w.tag): w.value for w in read_drawn("form_107", pdf)}
        as_itself = [(w, c) for w, c in pairs if printed[(w.page, w.tag)] == f"x{c}x"]
        alone = pymupdf.open(
            "pdf", _drawn_without_check(template, {(w.page, w.tag): c for w, c in as_itself})
        )
        with _no_anti_aliasing():
            inked += [
                f"U+{ord(c):04X}" for w, c in as_itself if _pixels(alone, w) != _pixels(empty, w)
            ]
    assert inked == []
```

The page tests read the printed page itself: what prints in each box, where each character sits, and, where text can't tell, its pixels. Each opens a drawn PDF only once no widget is left on its pages.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_known_defects.py b/backend/apps/forms/tests/test_known_defects.py
index 9dbae71..6bcea0f 100644
--- a/backend/apps/forms/tests/test_known_defects.py
+++ b/backend/apps/forms/tests/test_known_defects.py
@@ -18,7 +18,7 @@ from apps.forms.tests import test_oracle_tier3 as tier3
 from apps.forms.tests.oracle import DEFECT_CLASSES, KNOWN_DEFECTS

 ORACLE_CASES = {
-    "1": tier1.TEXT_CASES + tier1.BOX_CASES,
+    "1": tier1.TEXT_CASES + tier1.BOX_CASES + tier1.WIDGET_CASES,
     "2": tier2.CASES,
     "3": tier3.CASES,
 }
diff --git a/backend/apps/forms/tests/test_oracle_tier1.py b/backend/apps/forms/tests/test_oracle_tier1.py
index d51f296..717ee0c 100644
--- a/backend/apps/forms/tests/test_oracle_tier1.py
+++ b/backend/apps/forms/tests/test_oracle_tier1.py
@@ -5,11 +5,13 @@ Each text and combo binding gets a unique sentinel, the real engine draws it on
 real template, and every widget is read back from the printed page (3a2 spec §8): the
 sentinel prints in every widget of its name and in no other. A tick is the template's own check mark printed inside the box; /V alone proves nothing
 (DIG-68). Only the widgets the engine draws are read: a print button and the second
-widget of a stacked pair never print. No database is needed.
+widget of a stacked pair never print. The engine check gives each widget of a shared
+name a sentinel of its own, through its own key, and reads each back; it ticks each
+widget of a shared box name alone, one round per position. No database is needed.
 """

 from functools import cache
-from itertools import product
+from itertools import islice, product
 from pathlib import Path
 from string import ascii_uppercase

@@ -39,20 +41,21 @@ def _fits(form_type, pdf_field, value):
     return True


-def _option(form_type, pdf_field):
+def _option(form_type, pdf_field, nth=0):
     """
-    A combo's first option that prints and fits: not a blank one, and not the template's
-    own default, which the blank form prints already.
+    A combo's first (or nth) option that prints and fits: not a blank one, and not the
+    template's own default, which the blank form prints already.
     """
     template = Path(settings.PDF_FORMS_DIRECTORY) / load_schema(form_type).template_filename
     field = pypdf.PdfReader(template).get_fields()[pdf_field]
-    return next(
+    options = (
         str(option)
         for option in field["/Opt"]
         if str(option).strip()
         and str(option) != str(field.get("/V"))
         and _fits(form_type, pdf_field, str(option))
     )
+    return next(islice(options, nth, None))


 # Shorter sentinels for boxes too small for "Q001": two letters, then one. Letters only,
@@ -103,12 +106,64 @@ def _box_fill(form_type, position):
     return _drawn(form_type, values)


+_TEXT_KINDS = ("Text", "ComboBox")
+_BOX_KINDS = ("CheckBox", "RadioButton")
+
+
+def _shared_names(form_type, kinds):
+    """Full name → its drawn widgets of those kinds, for each name more than one widget has."""
+    widgets = {}
+    for w in template_widgets(load_schema(form_type).template_filename):
+        if w.drawn and w.kind in kinds:
+            widgets.setdefault(w.full_name, []).append(w)
+    return {name: named for name, named in widgets.items() if len(named) > 1}
+
+
+@cache
+def _widget_fill(form_type):
+    """
+    A sentinel for each widget of every shared name, given through the widget's own key
+    (name@page:tag), and what each drawn widget prints with all of them, read once the
+    form has no widget left.
+    """
+    sentinels = {}
+    short = iter(_SHORT)
+    for name, widgets in _shared_names(form_type, _TEXT_KINDS).items():
+        for k, w in enumerate(widgets):
+            sentinel = f"W{len(sentinels):03d}"
+            if w.kind == "ComboBox":  # 103B's two district boxes: a district each
+                sentinel = _option(form_type, name, nth=k)
+            elif not _fits(form_type, w.key, sentinel):
+                sentinel = next(s for s in short if _fits(form_type, w.key, s))
+            sentinels[w.key] = sentinel
+    return sentinels, _drawn(form_type, sentinels)
+
+
+@cache
+def _widget_box_fill(form_type, k):
+    """Tick the k-th widget of every shared box name through its own key, in one draw."""
+    return _drawn(
+        form_type,
+        {
+            widgets[k].key: widgets[k].states[0]
+            for widgets in _shared_names(form_type, _BOX_KINDS).values()
+            if k < len(widgets)
+        },
+    )
+
+
 def _text_cases():
     for form_type in get_all_form_types():
         for f in _fields(form_type, ("text", "choice")):
             yield case_param(form_type, f.pdf_field, TIER, "")


+def _widget_cases(kinds):
+    for form_type in get_all_form_types():
+        for name in _shared_names(form_type, kinds):
+            yield case_param(form_type, name, TIER, "each_widget")
+
+
 def _box_cases():
     for form_type in get_all_form_types():
         for f in _fields(form_type, ("checkbox", "radio")):
@@ -118,6 +173,9 @@ def _box_cases():

 TEXT_CASES = list(_text_cases())
 BOX_CASES = list(_box_cases())
+WIDGET_TEXT_CASES = list(_widget_cases(_TEXT_KINDS))
+WIDGET_BOX_CASES = list(_widget_cases(_BOX_KINDS))
+WIDGET_CASES = WIDGET_TEXT_CASES + WIDGET_BOX_CASES


 @pytest.mark.parametrize("form_type,pdf_field,case", TEXT_CASES)
@@ -135,6 +193,41 @@ def test_value_lands_only_in_the_box_it_names(form_type, pdf_field, case):
     assert missed == [], f"no_widget: the value is missing from widgets {missed}"


+@pytest.mark.parametrize("form_type,pdf_field,case", WIDGET_TEXT_CASES)
+def test_each_widget_of_a_shared_name_prints_its_own_value(form_type, pdf_field, case):
+    # Widgets that share a name (page headers, Schedule D's account boxes, A/B's 24.1) can
+    # each take a value of their own through their own key (3a2 spec §4.2, §8): each must
+    # print its own, not its sibling's, and not nothing.
+    sentinels, widgets = _widget_fill(form_type)
+    printed = {(w.page, w.tag): w.value for w in widgets if w.full_name == pdf_field}
+    own = {
+        (w.page, w.tag): sentinels[w.key] for w in _shared_names(form_type, _TEXT_KINDS)[pdf_field]
+    }
+    blank = sorted(at for at, value in printed.items() if not value)
+    assert blank == [], f"no_widget: widgets {blank} print nothing"
+    crossed = {at: value for at, value in printed.items() if value != own[at]}
+    assert crossed == {}, f"collision: widgets print another widget's value: {crossed}"
+
+
+@pytest.mark.parametrize("form_type,pdf_field,case", WIDGET_BOX_CASES)
+def test_each_widget_of_a_shared_box_name_ticks_alone(form_type, pdf_field, case):
+    # A box carries no value of its own, so each widget of a shared box name (the options
+    # of one question, Form 101's twelve "Check Box22") is ticked alone through its own key,
+    # one round per position (R50): it prints its tick, and no sibling prints one.
+    for k, widget in enumerate(_shared_names(form_type, _BOX_KINDS)[pdf_field]):
+        at = (widget.page, widget.tag)
+        printed = {
+            (w.page, w.tag): w.state
+            for w in _widget_box_fill(form_type, k)
+            if w.full_name == pdf_field
+        }
+        assert printed[at] == widget.states[0], f"no_widget: widget {at} prints no tick"
+        spilled = sorted(
+            other for other, state in printed.items() if other != at and state != "/Off"
+        )
+        assert spilled == [], f"collision: ticking widget {at} also ticks {spilled}"
+
+
 @pytest.mark.parametrize("form_type,pdf_field,case", BOX_CASES)
 def test_checkbox_ticks_only_the_widgets_for_its_answer(form_type, pdf_field, case):
     field = next(f for f in load_schema(form_type).fields if f.pdf_field == pdf_field)
PATCH
```

Tier 1 gains the engine check: each widget of a shared text or combo name gets a sentinel of its own through its own key, in one draw per form, and each widget of a shared box name is ticked alone, one round per position. The cases join the oracle's case keys, so `known_defects.json` can list one.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/pdf_readback.py b/backend/apps/forms/tests/pdf_readback.py
index 9a2e48c..b7f8c92 100644
--- a/backend/apps/forms/tests/pdf_readback.py
+++ b/backend/apps/forms/tests/pdf_readback.py
@@ -129,14 +129,24 @@ def read_drawn(form_type: str, pdf_bytes: bytes) -> list[DrawnWidget]:
     in page and tag order. A text box that prints exactly what the blank form prints
     there reads as "": nothing the template prints passes for a value, so a value equal
     to that box's blank text reads blank too.
+
+    Raises:
+        ValueError: a page still has a widget. MuPDF reads an unbaked widget's appearance
+            as text, and a viewer may rebuild it from the field's one value, so only a
+            baked page shows what prints. Not an assertion, so a listed defect's xfail
+            never takes a missing bake for that defect.
     """
     template = load_schema(form_type).template_filename
     blank = _blank(template)
+    document = pymupdf.open("pdf", pdf_bytes)
+    unbaked = [page.number + 1 for page in document if page.first_widget]
+    if unbaked:
+        raise ValueError(f"the PDF still has widgets on pages {unbaked}: it was never baked")
     return [
         (
             DrawnWidget(w.full_name, w.page, w.tag, "", w.state)
             if w.value and blank.get((w.page, w.tag)) == w.value
             else w
         )
-        for w in _read(template, pymupdf.open("pdf", pdf_bytes))
+        for w in _read(template, document)
     ]
PATCH
```

`read_drawn` refuses a PDF that still has a widget, with a `ValueError` naming its pages, so every read-back test proves the bake.

```bash
git apply <<'PATCH'
diff --git a/backend/apps/forms/tests/test_signing_lines.py b/backend/apps/forms/tests/test_signing_lines.py
index 161adfd..8171898 100644
--- a/backend/apps/forms/tests/test_signing_lines.py
+++ b/backend/apps/forms/tests/test_signing_lines.py
@@ -13,7 +13,9 @@ import pytest
 from django.core.management import call_command

 from apps.forms.registry import build_field_values
+from apps.forms.schema import load_schema
 from apps.forms.services.pdf_filler import PDFFormFiller
+from apps.forms.services.widgets import template_widgets
 from apps.forms.tests.pdf_readback import read_drawn
 from apps.intake.models import FormAnswer, IntakeSession

@@ -41,9 +43,10 @@ STILL_PRINTS = {
 @cache
 def _printed():
     """
-    (form_type, full name) → the text Priya's drawn forms print there, once she has given
-    a signing date and named an attorney. Every box of the template has an entry, so a
-    box name that is no box can't pass as blank.
+    (form_type, full name) → the texts Priya's drawn forms print in each drawn widget of
+    that name, once she has given a signing date and named an attorney; "" for a widget
+    that prints nothing, so a name that prints on only some of its widgets shows it. Every
+    box of the template has an entry, so a box name that is no box can't pass as blank.
     """
     call_command("loaddata", "ilnd_2025_data", verbosity=0)
     call_command("seed_demo_data", persona="priya", verbosity=0)
@@ -58,10 +61,11 @@ def _printed():
     printed = {}
     for form_type in SIGNING_LINES:
         values = build_field_values(form_type, session)
+        template = load_schema(form_type).template_filename
+        drawn = {(w.page, w.tag) for w in template_widgets(template) if w.drawn}
         for widget in read_drawn(form_type, PDFFormFiller().fill(form_type, values)):
-            shows = printed.setdefault((form_type, widget.full_name), set())
-            if widget.value:
-                shows.add(widget.value)
+            if (widget.page, widget.tag) in drawn:
+                printed.setdefault((form_type, widget.full_name), set()).add(widget.value)
     return printed


@@ -73,6 +77,7 @@ def _printed():
 def test_signature_lines_and_signing_dates_stay_blank_for_wet_ink(form_type, box):
     printed = _printed()
     assert (form_type, box) in printed, f"no box named {box!r} on {form_type}"
-    assert printed[(form_type, box)] == set()
+    assert printed[(form_type, box)] == {""}
+    # Every widget of each neighbour prints it: a page header blank on one page fails.
     for neighbour, value in STILL_PRINTS[form_type].items():
         assert printed[(form_type, neighbour)] == {value}
PATCH
```

The signing-lines test reads every drawn widget of each name, blanks included.

- [ ] **Step 2: Watch every read-back fail on a form that is never baked**

```bash
set -eo pipefail
trap 'git checkout -- backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -363,6 +363,5 @@
         buffer = BytesIO()
         writer.write(buffer)
         document = pymupdf.open("pdf", buffer.getvalue())
-        document.bake(annots=False, widgets=True)
         document.xref_set_key(document.pdf_catalog(), "AcroForm", "null")
         return document.tobytes()
PATCH
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --tb=line apps/forms/tests/test_printed_page.py apps/forms/tests/test_signing_lines.py apps/forms/tests/test_pdf_filler.py::test_a_tagged_value_prints_only_in_its_own_box 'apps/forms/tests/test_oracle_tier3.py::test_persona_packet_prints_the_right_figure[form_101:Debtor1.First name:maria]' -q -p no:cacheprovider) 2>&1 | grep -E '^/.*\.py:[0-9]+: |^=+ .* in [0-9.]+s' | sed -E 's#^/.*/backend/##' | awk '!seen[$0]++'
```

Expected: FAIL — `101 failed, 7 passed`, with lines such as `pdf_readback.py:144: ValueError: the PDF still has widgets on pages [1, 2, 3, 4, 5, 6, 7, 8, 9]: it was never baked` and `test_printed_page.py:73: assert [1, 2, 3, 4] == []`.

The mutation deletes `fill()`'s bake and keeps `/AcroForm` nulled, so every widget stays a widget. The trap restores `pdf_filler.py` when the block ends.

- The page tests stop on their own check that no page has a widget (`_printed()`, line 73, or the no-fillable-fields test's list of `/Widget` annotations), or on `read_drawn`'s `ValueError`.
- The signing-lines test, Task 3's tagged test and tier 3's Maria case stop on the `ValueError`. Before this task they passed on the unbaked PDF, because MuPDF reads an unbaked widget's appearance as text.
- The 7 that pass draw nothing: the six persona checks and the R38 count.

- [ ] **Step 3: Watch the engine check fail when a key reaches the wrong widget**

```bash
set -eo pipefail
trap 'git checkout -- backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -283,7 +283,7 @@
             reached[key] = [
                 widget
                 for widget in by_name.get(name, ())
-                if tag is None or (widget.page, widget.tag) == (page, tag)
+                if True
             ]
             if not reached[key]:
                 unknown.append(key)
PATCH
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --tb=line apps/forms/tests/test_oracle_tier1.py::test_each_widget_of_a_shared_name_prints_its_own_value apps/forms/tests/test_oracle_tier1.py::test_each_widget_of_a_shared_box_name_ticks_alone -q -p no:cacheprovider) 2>&1 | grep -E '^/.*\.py:[0-9]+: |^=+ .* in [0-9.]+s' | sed -E 's#^/.*/backend/##' | awk '!seen[$0]++'
```

Expected: FAIL — `76 failed, 227 passed`, with `collision: ticking widget (1, 'T3') also ticks [(3, 'T3')]`.

Here `check()` lets a widget's own key fill every widget of its name. All 73 text and combo names go red, since each widget's sentinel lands in its siblings. Of the 230 box names only 3 go red, Form 101's `Check Box1`, Form 107's `check3` and Schedule D's `check 5`: in every other shared box name each widget has an on-state of its own, so the full name ticks the same widget the key names.

```bash
set -eo pipefail
trap 'git checkout -- backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -305,7 +305,8 @@
             key = filled_by[widget]
             value = values[key]
             if widget.kind in _BOXES:
-                planned.append(Planned(widget, value if value in widget.states else "/Off", None))
+                first = by_name[widget.full_name][0]
+                planned.append(Planned(first, value if value in first.states else "/Off", None))
                 continue
             if widget.kind == "ComboBox" and value not in widget.options:
                 raise InvalidFieldValue(form_type, widget.full_name)
PATCH
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --tb=line apps/forms/tests/test_oracle_tier1.py::test_each_widget_of_a_shared_box_name_ticks_alone -q -p no:cacheprovider) 2>&1 | grep -E '^/.*\.py:[0-9]+: |^=+ .* in [0-9.]+s' | sed -E 's#^/.*/backend/##' | awk '!seen[$0]++'
```

Expected: FAIL — `230 failed`, with `no_widget: widget (1, 'T5') prints no tick`.

Here `check()` puts every box's tick on the first widget of its name, whatever widget the key names. Every box name goes red.

- [ ] **Step 4: Watch the signing lines fail when a shared name prints on one widget only**

```bash
set -eo pipefail
trap 'git checkout -- backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -345,6 +345,7 @@
         planned = {(p.widget.page, p.widget.tag): p for p in part.widgets}
         acro_form = writer.root_object["/AcroForm"].get_object()

+        seen = set()
         for number, page in enumerate(writer.pages, start=1):
             if "/Annots" not in page:
                 continue
@@ -355,7 +356,8 @@
                     widget = widget_for(template, number, annotation, float(page.mediabox.top))
                     if not widget.drawn:
                         continue
-                    if (number, widget.tag) in planned:
+                    if (number, widget.tag) in planned and not (widget.kind not in _BOXES and widget.full_name in seen):
+                        seen.add(widget.full_name)
                         _draw(writer, page, acro_form, annotation, planned[(number, widget.tag)])
                 kept.append(annot)
             page[NameObject("/Annots")] = kept
PATCH
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --tb=line apps/forms/tests/test_signing_lines.py -q -p no:cacheprovider) 2>&1 | grep -E '^/.*\.py:[0-9]+: |^=+ .* in [0-9.]+s' | sed -E 's#^/.*/backend/##' | awk '!seen[$0]++'
```

Expected: FAIL — `4 failed, 6 passed`, with `assert {'', 'Priya Sharma'} == {'Priya Sharma'}`.

Here `fill()` draws only the first widget of each shared text name. Forms 122A-1 and 122A-2 then print Priya's name in their first `Debtor1.Name` widget only. The signing lines of those two forms check that name as a neighbour, and each of their 4 cases now sees the blank widgets.

- [ ] **Step 5: Watch the cut-off test stop when `check()` fits a value of any length**

```bash
set -eo pipefail
trap 'git checkout -- backend/apps/forms/services/text_fit.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/text_fit.py b/backend/apps/forms/services/text_fit.py
--- a/backend/apps/forms/services/text_fit.py
+++ b/backend/apps/forms/services/text_fit.py
@@ -134,4 +134,4 @@
         # font's top sits at the clip's top (R35): the last line then stays above its bottom.
         if len(lines) * size * _leading(font) <= widget.height - 2 * widget.margin:
             return "\n".join(lines), size
-    return None
+    return text, MIN_SIZE
PATCH
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --tb=line 'apps/forms/tests/test_printed_page.py::test_no_value_is_ever_cut_off[form_121]' 'apps/forms/tests/test_printed_page.py::test_no_value_is_ever_cut_off[schedule_j]' -q -p no:cacheprovider) 2>&1 | grep -E '^/.*\.py:[0-9]+: |^=+ .* in [0-9.]+s' | sed -E 's#^/.*/backend/##' | awk '!seen[$0]++'
```

Expected: FAIL — `2 failed`, with `check() fits Case number1@1:T2 a value of any length` and `check() fits Debtor 1@1:T1 a value of any length`, in seconds.

Here `fit()` returns at 6 pt a value it should refuse as too long, so `check()` fits any length. The boundary search stops at its 1,024 bound and fails. Without the bound it would double forever.

- [ ] **Step 6: Watch the capitals test fail when the first line isn't lowered**

```bash
set -eo pipefail
trap 'git checkout -- backend/apps/forms/services/pdf_filler.py' EXIT
git apply <<'PATCH'
diff --git a/backend/apps/forms/services/pdf_filler.py b/backend/apps/forms/services/pdf_filler.py
--- a/backend/apps/forms/services/pdf_filler.py
+++ b/backend/apps/forms/services/pdf_filler.py
@@ -228,7 +228,7 @@
     appearance = TextStreamAppearance.from_text_annotation(
         writer, page, False, acro_form, field, annotation, user_font_size=planned.size
     )
-    if widget.multiline:
+    if False:
         _lower_first_line(appearance, 2 * widget.margin)
     annotation[NameObject("/AP")] = DictionaryObject(
         {NameObject("/N"): writer._add_object(appearance)}
PATCH
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --tb=line apps/forms/tests/test_printed_page.py::test_a_capitals_mark_survives_the_first_line -q -p no:cacheprovider) 2>&1 | grep -E '^/.*\.py:[0-9]+: |^=+ .* in [0-9.]+s' | sed -E 's#^/.*/backend/##' | awk '!seen[$0]++'
```

Expected: FAIL — `4 failed`, with `('É', 0.205)` and `('É', 0.0)`.

Without R35's rewrite, pypdf hangs a multi-line box's first line from the font's top at the box's height plus its margin, and the box cuts off part of each capital's mark. MuPDF still reads the letter whole, so only the pixels show it: at the box's own size line 1's É keeps about a fifth of line 2's ink, and at 6 pt none.

- [ ] **Step 7: Run the tests on the real drawing**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --tb=line apps/forms/tests/test_printed_page.py apps/forms/tests/test_oracle_tier1.py apps/forms/tests/test_signing_lines.py apps/forms/tests/test_known_defects.py -q -p no:cacheprovider) 2>&1 | grep -E '^/.*\.py:[0-9]+: |^=+ .* in [0-9.]+s' | sed -E 's#^/.*/backend/##' | awk '!seen[$0]++'
git status --short
```

Expected: `1068 passed`, and the status lists only the five test files, among them `?? backend/apps/forms/tests/test_printed_page.py`: every mutation above was restored.

That is the 94 page tests, tier 1's 961 cases (the 303 engine cases among them), the 10 signing-lines cases and the 3 tests of `test_known_defects.py`, whose orphan check now knows the engine cases. With `known_defects.json` at `[]`, its orphan and class checks have nothing to check yet; they matter once an entry is listed.

- [ ] **Step 8: Say in `CLAUDE.md` that `read_drawn` reads only baked output**

```bash
git apply <<'PATCH'
diff --git a/CLAUDE.md b/CLAUDE.md
index 2bf4551..29aab59 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -35,7 +35,7 @@ cd backend && ruff check . --fix               # Backend lint (pinned ruff==0.8.
 - **Dated tables and the fill date** — `in_force(rows, on, table, district)` (`apps/districts/dated_tables.py`) takes the newest row whose `effective_date` is on or before `on` (later rows are ignored) and returns it unless its `valid_through` is set and earlier than `on`; when that row has expired, or no row has started yet, it logs one line (the table, the date and the district) and raises `NoTableInForce`, a `ValueError` carrying the filer's sentence, and never looks at an older row. Every lookup of a dated table takes `fill_date()`, the day the forms are filled in America/Chicago, which stands in for the filing date. The root `backend/conftest.py` pins `_today` to 2026-10-16 for every backend test, so a test of a lookup sets its own day with `monkeypatch.setattr("apps.districts.dated_tables._today", ...)`, and no module may import `_today` by name. A scheduled row (`DatedTable`: `effective_date`, `valid_through`, `source_url`) carries `valid_through`, the day before its next scheduled change, and an empty one means open-ended; a test fails on a fixture median row without one. The dev server, the seed and E2E use the real date, so from November 1, 2026 every forms call, the means test, `seed_demo_data` and CI's E2E job refuse until the November median table is loaded. `docs/REFERENCE_TABLES.md` says where each table is posted and how to add a row.
 - **GenerateAll vs single** — `/generate_all` returns `{generated, errors}`; single returns `{form, message}`. A refusal of the whole call is `{error}` with no `form_type` (plus its `step` or `page`, as in "Forms need a completed intake"): Generate All for an unfinished intake (422), and Generate All or a completed intake's packet list for income not entered by source or no median table in force on the fill date (both 422). `generate_all` covers only the packet and deletes the rows of unfiled forms that no longer apply. A form marked filed keeps its stored answers, even after it leaves the packet (DIG-155): `generate_all` leaves it untouched and returns it in `generated`, in its packet position, or after the packet's forms once it has left the packet; its download fills from its stored `field_values` without the packet check; `generate` and `regenerate` return 422 for it, but only after the completion check and the means test, whose refusal comes first. `GET /api/forms/packet/?session=<id>` returns `{session, form_types, tables}` in filing order, `tables` being the median table the means test used (empty with no means test, or one stored before `calculation_details["median_table"]` existed) and the source of the dashboard's notice naming it; the dashboard renders from it, reloads it after every Generate All, and shows a filed form outside it as "Filed, no longer in your current packet".
 - **Schemas are checked at startup** — `apps/forms/checks.py` validates all 17 schemas against the field index (forms.E001–E007: missing schema or index, template hash, full names, widget types and choices, export states and `/Opt` values, duplicate bindings, TBD sources and unknown rules, predicates, namespaces or repeat capacity). `manage.py check`, `runserver` and `migrate` (so the Heroku release) fail on a bad schema; pytest runs no system checks, `test_checks.py` does. A binding with a `tag` names one widget of its full name, the one with that index tag on its `page` (`apps/forms/services/widgets.py` matches each template widget to its index row), and resolves under the key `<full name>@<page>:<tag>`: E003 refuses a tag that isn't a widget of that name on that page, or names one that never prints a value (a print button, or the second of one of Schedule D's stacked pairs), and E006 counts the widgets each binding would fill, so a tagged and an untagged binding of one name conflict. E003 also refuses an index full name containing `@`, which marks a widget's own key. A checkbox or radio binding carries `choices` (answer → export state): `{"true": state}` is one box. Any other map takes only its own keys: a rule or answer feeding it must return one of them or `""` (blank), and any other value raises `UnmappedChoice`, a 422 in plain words. `{}` prints nothing, and tier 1's `test_every_checkbox_binding_maps_its_answers_to_a_box` fails on it.
-- **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. Tiers 1 and 3 read the printed page, not `/V`: `read_drawn` (`apps/forms/tests/pdf_readback.py`) takes a widget's Helvetica text and the template's ZapfDingbats check mark inside its rect, and reads `""` where a box prints only the blank template's own default (the district combos' placeholder, A/B `19.1`–`19.3 % of ownership` "0%", C `page 2` and G `fill 2.6` "2"), so a blank assertion on such a box can't see that default. It has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
+- **Known form defects are strict xfails** — `backend/apps/forms/tests/known_defects.json` lists every oracle case (tiers 1–3) that fails, each with its DIG ticket. Tiers 1 and 3 read the printed page, not `/V`: `read_drawn` (`apps/forms/tests/pdf_readback.py`) takes a widget's Helvetica text and the template's ZapfDingbats check mark inside its rect, and reads `""` where a box prints only the blank template's own default (the district combos' placeholder, A/B `19.1`–`19.3 % of ownership` "0%", C `page 2` and G `fill 2.6` "2"), so a blank assertion on such a box can't see that default. `read_drawn` refuses a PDF that still has a widget (a `ValueError`, never a listed defect), so it reads only `fill()`'s baked output. The list has been empty (`[]`) since forms step 2b: every oracle case passes, and the one xfail pytest still reports is a marker in `apps/intake/tests/test_integration_flow.py`, outside the list. Fixing a defect turns its xfail into a failure until you delete the entry. A tier 2 case is keyed on its box and its binding key, `<source>:<producer>` (for example `derived:schedule_j_vehicle_payment`), so re-ruling or moving a listed binding orphans its entry, and the orphan test fails until you delete it; tier 2 also pins how many cases it asserts (`ASSERTED_CASES` in `test_oracle_tier2.py`), so a binding change that alters coverage updates that number on purpose. Delete cleared entries by hand, not by running the recorder (`data/forms/field_index/tools/record_known_defects.py`, usage in its docstring): a green suite proves the list exact, since a listed case that passes is a strict XPASS and an entry with no case behind it fails the orphan test. Deleting by hand also keeps the recorder's missing tickets for five forms (DIG-143) out of the list.
 - **A new placement needs its addendum row in the same commit** — tier 2 asserts a binding only where a checked row covers its box and key. A binding the audit never judged (step 2's ADD rows) needs a row in `data/forms/field_index/audit/step2_verification.json`, committed with the binding: `verification.json`'s shape plus `producer`, spelled as the whole binding key (`derived:phone`, `constant:yes`), its evidence citing the box's field-index label and any owner answer that decided it. Tier 2 joins it on (box, key) before the audit rows, and `test_every_step2_placement_matches_a_binding` fails on a row no binding matches. A binding moved onto the box an audit row names needs no row: the moved-here join asserts it.
 - **Blank, not 0.00, on the forms** — a derivation must not turn a missing input into 0.00: a line DigniFi never asks (interest, payroll deductions, priority, a spouse's column) and an income source left empty print blank, and a source typed as $0 prints 0.00. A total counts an unasked line as zero and still prints. The 13 expense amounts are stored as $0 when left empty, so an expense line (Schedule J, 122A-2 lines 19 and 21) prints only above $0, while the totals (Schedule J 22a and 22c, 106Sum line 5, 103B line 6) still print. One exception remains: with no `ExpenseInfo` row at all, those totals and Schedule J 23b print 0.00, and 23c prints the income less 0.00 (`_total_monthly_expenses`, the one function behind all of them; any other error fails the form). Signature lines and signing dates stay blank for wet ink (`test_signing_lines.py`). No production schema has a repeat group: Form 107's prior-income and creditor-payment rows came off until steps 3–4 ask what they need, and the SOFA answers stay stored. The engine (`repeat`, `RepeatOverflow` and its 422) stays for later steps; only synthetic tests reach it.
 - **`field_values`, not `form_data`** — `GeneratedForm.field_values` holds the resolved values as encrypted JSON, and the API never returns it. `form_data` is blank; its column is dropped one release after this code is live. A filed form downloads its stored `field_values`; an unfiled one is resolved fresh on every download.
PATCH
```

"Known form defects are strict xfails" now says that `read_drawn` refuses a PDF that still has a widget, with a `ValueError` that a listed defect's xfail never takes.

- [ ] **Step 9: Run every gate**

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && $PY -m pytest --cov=apps --cov=config --cov-fail-under=90 --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -6)
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.development $PY manage.py check)
/Volumes/Containers/DigniFi/backend/.venv/bin/ruff check backend/
(cd frontend && NO_COLOR=1 npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
(cd frontend && npx tsc -p tsconfig.app.json --noEmit && npx tsc -p tsconfig.node.json --noEmit)
(cd frontend && npm run lint --silent && npm run format:check)
```

Expected: `2690 passed, 25 skipped, 1 xfailed`, coverage above 90%, `System check identified no issues (0 silenced).`, `All checks passed!`, `Tests  397 passed (397)`, and no output from tsc, eslint or prettier other than `All matched files use Prettier code style!`.

That is 397 more backend cases than after Task 3: 94 in `test_printed_page.py`, 73 text and 230 box engine cases in tier 1. Every other changed test keeps its cases. The 25 skips are the Postgres-only tests under sqlite. The next command runs them against the Postgres database named by `DATABASE_URL` in `.claude/forms-step3a2.env`, as CI's "Run the Postgres-only tests" step does. This task touches no locking, so they pass unchanged.

```bash
set -eo pipefail
source .claude/forms-step3a2.env
(cd backend && DJANGO_SETTINGS_MODULE=config.settings.test_postgres $PY -m pytest -m postgres --tb=short -q -rs -p no:cacheprovider 2>&1 | tail -4)
```

Expected: `25 passed`.

Task 4 runs no journeys: it changes no code a journey runs.

- [ ] **Step 10: Commit**

```bash
set -eo pipefail
git add \
  CLAUDE.md \
  backend/apps/forms/tests/pdf_readback.py \
  backend/apps/forms/tests/test_known_defects.py \
  backend/apps/forms/tests/test_oracle_tier1.py \
  backend/apps/forms/tests/test_printed_page.py \
  backend/apps/forms/tests/test_signing_lines.py
git commit -F - <<'MSG'
test(forms): prove what the printed page shows, widget by widget

Since 3a2 a form is drawn and baked into its pages, so these tests read the
page itself: its text, where each character sits, and its pixels where the
text can't tell (MuPDF extracts a partly hidden glyph whole). Each page test
reads a drawn PDF only once no widget is left on its pages, since MuPDF
reads an unbaked widget's appearance as text too. read_drawn now refuses a
PDF that still has a widget with a ValueError naming its pages, so every
read-back test, tiers 1 and 3 among them, proves the bake; a ValueError, not
an assertion, so a listed defect's xfail can never take it for that defect.

Tier 1 gains the engine check (3a2 spec §8) over every full name that more
than one drawn widget shares. Each widget of the 73 text and combo names (229
widgets) gets a sentinel of its own through its own key, in one draw per
form, and must print it, not a sibling's and not nothing (a viewer
rebuilding appearances from a field's one value would print it in every
widget). Each widget of the 230 box names (566 widgets) is ticked alone
through its own key, one round per position, 55 draws in all (Form 101's
twelve "Check Box22" take 12), and must print its tick while no sibling
prints one. One case per name; the cases join the oracle's case keys in
test_known_defects.py.

test_printed_page.py holds spec §9's page tests:
- no persona is refused: each of the six seeded packets passes check();
- the packet has no fillable fields left, and the print buttons never print
  (the template baked as it stands prints their labels);
- 103B's unticked boxes keep their squares (dark pixels, counted without
  anti-aliasing, equal the blank form's);
- Schedule D's stacked duplicates print once;
- every right-aligned box (547, A/B's three widget-only /Q boxes among them)
  ends at its right padding;
- Form 121's SSN and Schedule D's account numbers sit one character per comb
  cell, centred (R4);
- every drawn PDF opens with its page count and no MuPDF warning the blank
  template doesn't give (Form 101's "No common ancestor in structure tree"
  comes from the template);
- no value is ever cut off: in every text box the longest value check()
  fits reads back whole with every character inside the box, one letter or
  line more is refused, and a short value at the box's own size stays inside
  too, R38's 37 boxes within 0.11 pt at the bottom;
- a capital's mark survives a multi-line box's first line, at the box's own
  size and at 6 pt (R35, measured in pixels at 1440 dpi);
- check() agrees with the drawing on every letter of U+0020-U+017F and the
  typographic extras: an accepted letter prints as itself and leaves ink, a
  tab, space separator or format character is never refused, and a refused
  letter prints "?", another glyph, or no ink at all.

test_signing_lines.py now reads every drawn widget of each name, blanks
included, so a name that prints on only some of its widgets fails; it stayed
green under the draw-once mutation.

CLAUDE.md's "Known form defects are strict xfails" says read_drawn reads only
fill()'s baked output.
MSG
git status --short
```
